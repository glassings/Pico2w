# telegraph -- tap Morse on the button; the ghost listens.
#
# The key is read by an IRQ ring buffer (hw.KeyLine), not by the normal
# button polling, so a 60 ms dot is never lost to a slow screen redraw.
# The usual click/hold events are ignored here: the button is the key.
#
#   tap                      Morse
#   hold 1.0-1.5 s, let go   speed screen (tap: next option, hold 1 s: keep)
#   hold 1.5 s               leave (any mode)
#
# Decoded text and symbols sit in the protected band: glitches may only
# touch the decorations around them.

from time import ticks_diff, ticks_us
from apps import App as Screen
from render import wrap
import morse
import phrases
import hw
import config as C

SPEEDS = (5, 6, 8, 10, 12, 15, 20, 'auto')
MENU_MS = 1000              # a hold this long (but < exit) opens the speed screen
WORDS = ('HELLO', 'GHOST', 'BOO')

SYM_Y = 28                  # symbols of the letter being keyed
TEXT_Y = 37                 # 3 rows of decoded text: 37, 46, 55


class App(Screen):
    protect = (SYM_Y - 1, 64)

    def enter(self, ctx):
        super().enter(ctx)
        self.speed = ctx.mem.state.get('tg_wpm', C.TELEGRAPH_WPM)
        if self.speed not in SPEEDS:
            self.speed = C.TELEGRAPH_WPM
        self.dec = morse.Decoder(8, auto=False)
        self._apply_speed()
        self.key = hw.KeyLine(ctx.buzzer)
        self.mode = 'key'           # 'key' or 'speed'
        self.pick = 0               # index into SPEEDS on the speed screen
        self.down_at = None
        self.up_at = ticks_us()
        self.last_press = None      # (ms, symbol)       for TELEGRAPH_DEBUG
        self.last_gap = None        # (ms, . | /)
        self.presses = 0
        self.reacted_at = 0         # len(text) when we last reacted to a word
        self.leaving = False
        ctx.speech.clear()
        ctx.say(phrases.pick('telegraph_start'))

    def _apply_speed(self):
        d = self.dec
        if self.speed == 'auto':
            d.auto = True
            d.set_wpm(C.TELEGRAPH_WPM)
        else:
            d.auto = False
            d.set_wpm(self.speed)

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

    # ------------------------------------------------------------ input
    def _released(self, ms):
        """A whole press is over: ms long."""
        if ms >= MENU_MS:
            if self.mode == 'key':
                self.mode = 'speed'
                self.pick = SPEEDS.index(self.speed)
                self.dec.flush()
            else:
                self._keep_speed()
            return
        if self.mode == 'speed':
            self.pick = (self.pick + 1) % len(SPEEDS)
            return
        self.last_press = (ms, self.dec.press(ms))
        self.presses += 1

    def _keep_speed(self):
        self.mode = 'key'
        new = SPEEDS[self.pick]
        if new != self.speed:
            self.speed = new
            self._apply_speed()
            s = self.ctx.mem.state
            s['tg_wpm'] = new
            self.ctx.mem.touch(urgent=True)     # saved only because it changed

    def update(self, now):
        d = self.dec
        for t, v in self.key.events():
            if v:                                   # key down
                if self.up_at is not None:
                    g = ticks_diff(t, self.up_at) // 1000
                    u = d.unit
                    self.last_gap = (g, '.' if g < 2 * u else '|' if g <= 5 * u else '/')
                self.down_at = t
                self.up_at = None
            elif self.down_at is not None:          # key up
                ms = ticks_diff(t, self.down_at) // 1000
                self.up_at = t
                self.down_at = None
                if ms >= C.TELEGRAPH_EXIT_MS:
                    self._leave()
                    return
                self._released(ms)
        if self.key.level:
            if self.down_at is not None and \
                    ticks_diff(ticks_us(), self.down_at) >= C.TELEGRAPH_EXIT_MS * 1000:
                self._leave()
        elif self.up_at is not None and self.mode == 'key':
            d.gap(ticks_diff(ticks_us(), self.up_at) // 1000)
            self._react()

    def _react(self):
        """Once per finished word: does the ghost know it?"""
        text = self.dec.text
        if not text.endswith(' ') or len(text) == self.reacted_at:
            return
        self.reacted_at = len(text)
        word = text.rstrip().split(' ')[-1]
        if word == 'SOS':
            key = 'telegraph_sos'
        elif word in WORDS:
            key = 'telegraph_word'
        else:
            return
        ctx = self.ctx
        ctx.speech.clear()
        ctx.say(phrases.pick(key))
        ctx.ghost.content = min(100.0, ctx.ghost.content + 1)

    # ------------------------------------------------------------ drawing
    def _held_ms(self):
        if self.key.level and self.down_at is not None:
            return ticks_diff(ticks_us(), self.down_at) // 1000
        return 0

    def _eye(self, r, x, y):
        # a little ghost eye: open while the key is down, shut otherwise
        if self.key.level:
            r.o.ellipse(x, y, 5, 3, 1)
            r.o.fill_rect(x - 1, y - 1, 3, 3, 1)
        else:
            r.o.hline(x - 5, y, 11, 1)
            r.o.pixel(x - 4, y + 1, 1)
            r.o.pixel(x + 4, y + 1, 1)

    def draw(self, r, now):
        ctx = self.ctx
        d = self.dec
        r.text("telegraph", 0, 0)
        sp = "auto" if self.speed == 'auto' else "%dwpm" % self.speed
        r.text(sp, 112 - 8 * len(sp), 0)
        # the key light: the visual twin of the sidetone
        r.o.ellipse(122, 3, 3, 3, 1, bool(self.key.level))

        if self.mode == 'speed':
            self._draw_speed(r)
            return

        held = self._held_ms()
        if held >= MENU_MS:
            r.text("let go: speed", 0, 9)
            r.text("hold on: leave", 0, 18)
        elif C.TELEGRAPH_DEBUG:
            p, g = self.last_press, self.last_gap
            r.text("dn%4s%s up%5s%s" % (p[0] if p else '-', p[1] if p else ' ',
                                         g[0] if g else '-', g[1] if g else ' '), 0, 9)
            r.text("unit %dms %dwpm" % (int(d.unit), int(d.wpm + 0.5)), 0, 18)
        else:
            ctx.speech.draw(r, 9, now, ctx.ghost.glitch)

        r.text(d.pending[-13:], 0, SYM_Y)
        self._eye(r, 115, SYM_Y + 3)

        lines = [l for _, l in wrap(d.text, 16, 99)] or ['']
        if d.text.endswith(' ') and len(lines[-1]) >= 16:
            lines.append('')
        lines = lines[-3:]
        y = TEXT_Y + 9 * (3 - len(lines))
        for l in lines:
            r.text(l, 0, y)
            y += 9
        # cursor after the last character
        last = lines[-1] + (' ' if d.text.endswith(' ') and lines[-1] else '')
        if (now // 400) & 1:
            cx = min(len(last), 15) * 8
            r.o.hline(cx, y - 2, 7, 1)

    def _draw_speed(self, r):
        r.text("speed", 0, 12)
        v = SPEEDS[self.pick]
        txt = "auto" if v == 'auto' else "%d wpm" % v
        r.big(txt, (128 - len(txt) * 16) // 2, 24, 2)
        r.text("tap: next", 0, 46)
        r.text("hold 1s: keep", 0, 55)
