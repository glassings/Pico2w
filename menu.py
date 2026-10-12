# menu.py -- asking the ghost for things.
# up/down to move, click to choose, hold to go back.

import apps
import sprites
import config as C

ITEMS = (
    ('listen', 'listen'),
    ('familiars', 'familiars'),
    ('timer', 'timer'),
    ('stopwatch', 'stopwatch'),
    ('dice', 'dice'),
    ('notes', 'notes'),
    ('status', 'status'),
    ('sleep', 'sleep'),
)
ROWS = 5            # visible at once
TOP = 12            # y of first row
STEP = 10           # row pitch


class Menu(apps.App):
    def __init__(self):
        self.sel = 0
        self.scroll = 0

    def enter(self, ctx):
        super().enter(ctx)
        self.resume()

    def resume(self):
        self.ctx.puppet.set_bounds(100, 14, 104, 36, snap=True)

    @property
    def protect(self):
        y = TOP + (self.sel - self.scroll) * STEP
        return (y, y + 8)

    def event(self, ev):
        n = len(ITEMS)
        if ev == 'up':
            self.sel = (self.sel - 1) % n
        elif ev == 'down':
            self.sel = (self.sel + 1) % n
        elif ev == 'click':
            label, mod = ITEMS[self.sel]
            cls = apps.load(mod)
            if cls is None:
                from apps import stub
                self.ctx.push(stub.App(label))
            else:
                self.ctx.push(cls())
        elif ev == 'hold':
            self.ctx.pop()
        if self.sel < self.scroll:
            self.scroll = self.sel
        elif self.sel >= self.scroll + ROWS:
            self.scroll = self.sel - ROWS + 1

    def draw(self, r, now):
        ctx = self.ctx
        r.text("ask me:", 0, 0)
        for row in range(ROWS):
            i = self.scroll + row
            if i >= len(ITEMS):
                break
            y = TOP + row * STEP
            if i == self.sel:
                r.sprite(sprites.MINI, 1 if (now // 400) & 1 else 0, y)
            r.text(ITEMS[i][0], 12, y)
        # scroll hints
        if self.scroll > 0:
            r.text('^', 88, TOP)
        if self.scroll + ROWS < len(ITEMS):
            r.text('v', 88, TOP + (ROWS - 1) * STEP)
        ctx.puppet.draw(r, now, ctx.ghost.glitch)
