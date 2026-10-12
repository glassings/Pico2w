# alarm -- the countdown ran out.  Pushed over whatever screen was open
# (and the screen is woken if it was off).  Any input dismisses it.

from time import ticks_diff
from apps import App as Screen
import phrases
import hw
import config as C


class App(Screen):
    allow_screen_off = False

    def enter(self, ctx):
        super().enter(ctx)
        self.t0 = ctx.now()
        self.ringing = True
        ctx.speech.clear()
        ctx.buzzer.play(hw.ALARM, loop=True)
        ctx.puppet.set_bounds(2, 4, 30, 12, snap=True)
        ctx.puppet.express('excited', 3000, self.t0)
        ctx.say(phrases.pick('timer_done'))

    def exit(self):
        self.ctx.buzzer.stop()
        self.ctx.speech.clear()

    def event(self, ev):
        self.ctx.pop()

    def update(self, now):
        if self.ringing and ticks_diff(now, self.t0) > C.ALARM_MAX_S * 1000:
            self.ringing = False
            self.ctx.buzzer.stop()

    def draw(self, r, now):
        ctx = self.ctx
        ctx.puppet.draw(r, now, ctx.ghost.glitch)
        if (now // 400) & 1:
            r.big("0:00", 128 - 4 * 16 - 2, 4, 2)
        r.text("time.", 74, 28)
        ctx.speech.draw(r, 47, now, ctx.ghost.glitch)
