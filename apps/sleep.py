# sleep -- the ghost closes its eyes and the screen goes dark.
# Click the joystick to wake it.

from time import ticks_diff
from apps import App as Screen
import phrases


class App(Screen):
    def enter(self, ctx):
        super().enter(ctx)
        self.t0 = ctx.now()
        ctx.puppet.set_bounds(40, 10, 64, 14)
        ctx.say(phrases.pick('sleep'))

    def update(self, now):
        t = ticks_diff(now, self.t0)
        if t > 900:
            self.ctx.puppet.express('sleep', 500, now)
        if t > 3000:
            self.ctx.home()         # wake up at home, not in the menu
            self.ctx.screen_off()

    def draw(self, r, now):
        ctx = self.ctx
        ctx.puppet.draw(r, now, ctx.ghost.glitch)
        ctx.speech.draw(r, 47, now, ctx.ghost.glitch)
