# timer -- the ghost holds a countdown for you.  It keeps running in the
# background (menus, listening, screen off) and calls you when it's done.
#
# setting:  left/right pick minutes or seconds, up/down change, click starts
# running:  click pauses, hold leaves it running and goes back
# paused:   click resumes, left resets, hold goes back

from apps import App as Screen
import chrono
import phrases
import hw

DIGITS_Y = 12
SCALE = 3


class App(Screen):
    def enter(self, ctx):
        super().enter(ctx)
        self.field = 0          # 0 = minutes, 1 = seconds
        ctx.speech.clear()

    def exit(self):
        self.ctx.speech.clear()

    protect = (DIGITS_Y, DIGITS_Y + 8 * SCALE + 4)

    def event(self, ev):
        ctx = self.ctx
        t = ctx.timer
        now = ctx.now()
        if ev == 'hold':
            ctx.pop()
        elif t.running:
            if ev == 'click':
                t.pause(now)
                ctx.chirp(hw.STOP)
        elif t.paused:
            if ev == 'click':
                t.resume(now)
                ctx.chirp(hw.START)
            elif ev == 'left':
                t.cancel()
                ctx.chirp(hw.BLIP)
        else:
            m, s = divmod(t.set_s, 60)
            if ev in ('left', 'right'):
                self.field ^= 1
            elif ev in ('up', 'down'):
                d = 1 if ev == 'up' else -1
                if self.field == 0:
                    m = (m + d) % 100
                else:
                    s = (s + 5 * d) % 60
                t.set_s = m * 60 + s
            elif ev == 'click' and t.set_s:
                t.start(now)
                ctx.mem.state['timer_s'] = t.set_s
                ctx.mem.touch()
                ctx.chirp(hw.START)
                ctx.say(phrases.pick('timer_start'))

    def draw(self, r, now):
        ctx = self.ctx
        t = ctx.timer
        left = t.remaining(now)
        state = 'running' if t.running else 'paused' if t.paused else 'set'
        r.text("timer", 0, 0)
        r.text(state, 128 - 8 * len(state), 0)

        # always MM:SS here so the fields stay put while setting
        s = (left + 999) // 1000        # round up: never show 0:00 early
        txt = "%02d:%02d" % (s // 60, s % 60)
        if t.paused and (now // 500) & 1:
            pass                        # paused: digits blink
        else:
            r.big_center(txt, DIGITS_Y, SCALE)
        x0 = (128 - len(txt) * 8 * SCALE) // 2
        if not t.active:
            # underline the field being set
            fx = x0 + (0 if self.field == 0 else 3 * 8 * SCALE)
            r.o.fill_rect(fx, DIGITS_Y + 8 * SCALE + 1, 2 * 8 * SCALE - 3, 2, 1)
        elif t.set_s:
            # how much is left, as a thin bar
            w = 128 * left // (t.set_s * 1000)
            r.o.hline(0, DIGITS_Y + 8 * SCALE + 2, min(128, w), 1)

        if ctx.speech.busy:
            ctx.speech.draw(r, 47, now, ctx.ghost.glitch)
        elif t.running:
            r.text("click: pause", 0, 47)
            r.text("hold: keep it", 0, 56)
        elif t.paused:
            r.text("click: resume", 0, 47)
            r.text("left: reset", 0, 56)
        else:
            r.text("<>: m/s  ^v: set", 0, 47)
            r.text("click: start", 0, 56)
