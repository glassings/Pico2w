# wake -- boot sequence: static, a shape forming in it, then a remark.
# Click to skip.

from time import ticks_diff
from apps import App as Screen
import sprites
import config as C


class App(Screen):
    allow_screen_off = False

    def __init__(self, remarks):
        self.remarks = remarks      # fn(ctx) -> lines to say once it has formed

    def enter(self, ctx):
        super().enter(ctx)
        self.t0 = ctx.now()
        ctx.puppet.set_bounds(52, 12, 52, 12, snap=True)
        if C.BUZZER_BOOT_CHIME:
            import hw
            ctx.buzzer.play(hw.BOOT)

    @property
    def glitch(self):
        return 1.0

    def event(self, ev):
        if ev == 'click':
            self._done()

    def _done(self):
        ctx = self.ctx
        ctx.pop()
        ctx.booted = True
        for s in self.remarks(ctx):
            ctx.say(s, queue=True)

    def update(self, now):
        # after the animation, wait (up to the sync budget) for the clock,
        # so the first remark can know how long it was really gone
        t = ticks_diff(now, self.t0)
        if t > 2300 and (not self.ctx.clock.busy or t > 2300 + C.CLOCK_SYNC_BUDGET_MS):
            self._done()

    def draw(self, r, now):
        t = ticks_diff(now, self.t0)
        p = self.ctx.puppet
        heavy = 1 if self.ctx.hw > 0.5 else 0     # thicker static in season
        if t < 700:
            r.static((2 if t < 350 else 3) - heavy)
            if t > 450 and (t // 50) & 1:
                r.o.fill_rect(0, (t // 4) % 64, 128, 3, 1)     # rolling bar
        elif t < 1300:
            r.static(4 + (t - 700) // 200)
            r.sprite(sprites.FADE[1] if (t // 90) & 1 else sprites.HOLLOW, p.x, p.y)
        elif t < 1800:
            r.sprite(sprites.GLITCH if (t // 70) % 3 == 0 else sprites.FADE[0], p.x, p.y)
        else:
            r.sprite(sprites.STARE, p.x, p.y)
            if t > 2300:
                # still asking the air what time it is
                r.center("." * (1 + (t // 400) % 3), 52)
