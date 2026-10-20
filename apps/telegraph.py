# telegraph -- tap Morse on the button; the ghost listens.
#
# The key is read by an IRQ ring buffer (hw.KeyLine), not by the normal
# button polling, so a 60 ms dot is never lost to a slow screen redraw.
# The usual click/hold events are ignored while this screen is open:
# here the button is a telegraph key.
#
#   hold the key 1.5 s: leave (any mode)
#
# Decoded text, timings and symbols sit in the protected band: glitches
# may only touch the decorations around them.

from time import ticks_diff, ticks_us
from apps import App as Screen
import morse
import phrases
import hw
import config as C


class App(Screen):
    protect = (8, 46)

    def enter(self, ctx):
        super().enter(ctx)
        s = ctx.mem.state
        wpm = s.get('tg_wpm', C.TELEGRAPH_WPM)
        self.dec = morse.Decoder(C.TELEGRAPH_WPM if wpm == 'auto' else wpm, auto=wpm == 'auto')
        self.key = hw.KeyLine(ctx.buzzer)
        self.down_at = None
        self.up_at = ticks_us()
        self.last_press = None      # (ms, symbol)
        self.last_gap = None        # (ms, '.' same letter / '|' letter / '/' word)
        self.presses = 0
        self.leaving = False
        ctx.speech.clear()
        ctx.say(phrases.pick('telegraph_start'))

    def exit(self):
        ctx = self.ctx
        self.key.close()
        ctx.joy.rearm()             # the normal button gets its pin back
        ctx.speech.clear()
        if self.presses:
            g = ctx.ghost
            g.content = min(100.0, g.content + 3)   # tapping calms it

    def cover(self):
        # the timer alarm (say) is on top: go quiet, forget the half-keyed letter
        self.key.muted = True
        if self.ctx.buzzer and self.key.level:
            self.ctx.buzzer.key_tone(0)

    def resume(self):
        # back from the alarm: drop the presses that dismissed it
        self.key.events()
        self.key.muted = False
        self.down_at = None
        self.up_at = ticks_us()
        self.dec.flush()

    def event(self, ev):
        # the button is the key here.  A separate back button (3+ buttons
        # or the joystick) still works.
        if ev == 'hold' and not C.INPUT_ONE_BUTTON:
            self.ctx.pop()

    def _leave(self):
        if not self.leaving:
            self.leaving = True
            self.ctx.pop()

    def update(self, now):
        d = self.dec
        u = d.unit
        for t, v in self.key.events():
            if v:                                   # key down
                if self.down_at is None or self.up_at is not None:
                    g = ticks_diff(t, self.up_at) // 1000
                    self.last_gap = (g, '.' if g < 2 * u else '|' if g <= 5 * u else '/')
                self.down_at = t
                self.up_at = None
            elif self.down_at is not None:          # key up
                ms = ticks_diff(t, self.down_at) // 1000
                self.up_at = t
                if ms >= C.TELEGRAPH_EXIT_MS:
                    self._leave()
                    return
                self.last_press = (ms, d.press(ms))
                self.presses += 1
        if self.key.level:
            if self.down_at is not None and \
                    ticks_diff(ticks_us(), self.down_at) >= C.TELEGRAPH_EXIT_MS * 1000:
                self._leave()
        elif self.up_at is not None:
            d.gap(ticks_diff(ticks_us(), self.up_at) // 1000)

    def draw(self, r, now):
        ctx = self.ctx
        d = self.dec
        r.text("telegraph", 0, 0)
        # the key, as a light: the visual twin of the sidetone
        if self.key.level:
            r.o.ellipse(120, 3, 3, 3, 1, True)
        else:
            r.o.ellipse(120, 3, 3, 3, 1)

        r.text(d.pending[-16:] or "_", 0, 10)
        r.text(d.text[-16:], 0, 20)
        p = self.last_press
        g = self.last_gap
        r.text("dn%4s" % (p[0] if p else '-'), 0, 30)
        r.text(p[1] if p else '', 48, 30)
        r.text("up%5s" % (g[0] if g else '-'), 64, 30)
        r.text(g[1] if g else '', 120, 30)
        w = ("auto %d" if d.auto else "%d") % int(d.wpm + 0.5)
        r.text("unit %dms %swpm" % (int(d.unit), w), 0, 38)
        if ctx.speech.busy:
            ctx.speech.draw(r, 47, now, ctx.ghost.glitch)
        else:
            r.text("hold 1.5s: exit", 0, 56)
