# settings -- things you can change from the device itself.
#
# up/down: pick   click: change   hold: back
# (one button: 1 click = next row, 2 clicks = change, 3 clicks = back)

from apps import App as Screen
import halloween
import sprites
import config as C

ROWS = (
    ('halloween', 'halloween', halloween.MODES),
)


class App(Screen):
    protect = (10, 64)

    def enter(self, ctx):
        super().enter(ctx)
        self.sel = 0

    def event(self, ev):
        ctx = self.ctx
        s = ctx.mem.state
        if ev == 'hold':
            ctx.pop()
        elif ev in ('up', 'down'):
            self.sel = (self.sel + (1 if ev == 'down' else -1)) % len(ROWS)
        elif ev in ('click', 'left', 'right'):
            label, key, choices = ROWS[self.sel]
            cur = s.get(key, choices[0])
            i = choices.index(cur) if cur in choices else 0
            s[key] = choices[(i + (-1 if ev == 'left' else 1)) % len(choices)]
            ctx.mem.touch(urgent=True)

    def draw(self, r, now):
        ctx = self.ctx
        s = ctx.mem.state
        r.text("settings", 0, 0)
        y = 12
        for i, (label, key, choices) in enumerate(ROWS):
            if i == self.sel:
                r.sprite(sprites.MINI, 0, y)
            r.text("%s %s" % (label, s.get(key, choices[0])), 12, y)
            y += 10
        # what the season is doing right now
        r.text("spookiness %3d%%" % int(ctx.hw * 100 + 0.5), 0, 46)
        r.text("2 clicks: change" if C.INPUT_ONE_BUTTON else "click: change", 0, 56)
