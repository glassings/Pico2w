# wake -- boot sequence: static, a shape forming in it, then a remark.
# Click to skip.

from time import ticks_diff
from apps import App as Screen
import sprites
import config as C


class App(Screen):
    allow_screen_off = False

    def __init__(self, remarks):
        self.remarks = remarks      # said, in order, once it has formed

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
        for s in self.remarks:
            ctx.say(s, queue=True)

    def update(self, now):
        if ticks_diff(now, self.t0) > 2300:
            self._done()

    def draw(self, r, now):
        t = ticks_diff(now, self.t0)
        p = self.ctx.puppet
        if t < 700:
            r.static(2 if t < 350 else 3)
            if t > 450 and (t // 50) & 1:
                r.o.fill_rect(0, (t // 4) % 64, 128, 3, 1)     # rolling bar
        elif t < 1300:
            r.static(4 + (t - 700) // 200)
            r.sprite(sprites.FADE[1] if (t // 90) & 1 else sprites.HOLLOW, p.x, p.y)
        elif t < 1800:
            r.sprite(sprites.GLITCH if (t // 70) % 3 == 0 else sprites.FADE[0], p.x, p.y)
        else:
            r.sprite(sprites.STARE, p.x, p.y)
