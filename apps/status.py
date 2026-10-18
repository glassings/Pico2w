# status -- the ghost's own readout of itself.  Cryptic labels, true numbers.
#
# up/down: switch page   hold: back

from apps import App as Screen


def _bar(r, x, y, w, v):
    r.o.rect(x, y, w, 7, 1)
    r.o.fill_rect(x + 1, y + 1, int((w - 2) * v / 100), 5, 1)


class App(Screen):
    def enter(self, ctx):
        super().enter(ctx)
        self.page = 0

    protect = (10, 64)

    def event(self, ev):
        if ev == 'hold':
            self.ctx.pop()
        elif ev in ('up', 'down'):
            self.page ^= 1

    def draw(self, r, now):
        ctx = self.ctx
        g = ctx.ghost
        s = ctx.mem.state
        if self.page == 0:
            r.text("what i am", 0, 0)
            r.text("1/2", 104, 0)
            a = int(g.alive_s)
            rows = (
                ("alive", "%dd %02dh %02dm" % (a // 86400, a // 3600 % 24, a // 60 % 60)),
                ("woken", "%d times" % s['boots']),
                ("eaten", "%d" % s['fed']),
                ("named", "%d" % len(s['familiars'])),
                ("felt", "%d near" % s['presences']),
                ("feels", g.mood),
            )
            y = 10
            for label, val in rows:
                r.text(label, 0, y)
                r.text(val, 48, y)
                y += 9
        else:
            r.text("inside me", 0, 0)
            r.text("2/2", 104, 0)
            rows = (
                ("hunger", g.hunger),
                ("unrest", g.restless),
                ("calm", g.content),
                ("static", g.glitch * 100),
            )
            y = 12
            for label, v in rows:
                r.text(label, 0, y)
                _bar(r, 52, y, 48, v)
                r.text("%3d" % int(v + 0.5), 104, y)
                y += 13
