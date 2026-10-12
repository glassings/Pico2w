# familiars -- the WiFi access points the ghost remembers, most-met first.
# Only nicknames and counts are stored; never names or addresses.
#
# up/down: scroll   click: ask about one   hold: back

from apps import App as Screen
import phrases
import sprites

ROWS = 2
TOP = 11
STEP = 17


class App(Screen):
    def enter(self, ctx):
        super().enter(ctx)
        fam = ctx.mem.state['familiars']
        self.items = sorted(((f[0], f[1]) for f in fam.values()), key=lambda f: -f[1])
        self.sel = 0
        self.top = 0
        ctx.speech.clear()
        if not self.items:
            ctx.puppet.set_bounds(40, 10, 64, 18, snap=True)
            ctx.say(phrases.pick('familiars_empty'))

    def exit(self):
        self.ctx.speech.clear()

    @property
    def protect(self):
        return (TOP, TOP + ROWS * STEP) if self.items else None

    def event(self, ev):
        n = len(self.items)
        if ev == 'hold':
            self.ctx.pop()
        elif not n:
            return
        elif ev == 'up':
            self.sel = (self.sel - 1) % n
        elif ev == 'down':
            self.sel = (self.sel + 1) % n
        elif ev == 'click':
            self.ctx.say(phrases.pick('familiar_pick', name=self.items[self.sel][0]))
        if self.sel < self.top:
            self.top = self.sel
        elif self.sel >= self.top + ROWS:
            self.top = self.sel - ROWS + 1

    def draw(self, r, now):
        ctx = self.ctx
        lvl = ctx.ghost.glitch
        if not self.items:
            r.center("familiars", 0)
            ctx.puppet.draw(r, now, lvl)
            ctx.speech.draw(r, 47, now, lvl)
            return
        r.text("familiars", 0, 0)
        r.text("%d" % len(self.items), 128 - 8 * len(str(len(self.items))), 0)
        for row in range(ROWS):
            i = self.top + row
            if i >= len(self.items):
                break
            y = TOP + row * STEP
            name, seen = self.items[i]
            if i == self.sel:
                r.sprite(sprites.MINI, 1 if (now // 400) & 1 else 0, y)
            r.text(name, 12, y)
            r.text("met %dx" % seen, 20, y + 8)
        if self.top > 0:
            r.text('^', 120, TOP + 8)
        if self.top + ROWS < len(self.items):
            r.text('v', 120, TOP + STEP + 8)
        ctx.speech.draw(r, 47, now, lvl)
