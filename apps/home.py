# home -- the ghost's room.  It drifts, blinks, mutters, naps, and
# sometimes isn't there.  Click to ask it for something.

import random
from time import ticks_diff, ticks_add
from apps import App as Screen
import phrases
import config as C

_DIRS = {'up': (0, -8), 'down': (0, 8), 'left': (-22, 0), 'right': (22, 0)}


class App(Screen):
    def enter(self, ctx):
        super().enter(ctx)
        self.resume()

    def resume(self):
        now = self.ctx.now()
        self.ctx.puppet.set_bounds(0, 0, 104, 22)
        self.next_chat = ticks_add(now, random.randint(5000, 9000))
        self.next_quirk = ticks_add(now, random.randint(8000, 18000))

    def event(self, ev):
        ctx = self.ctx
        p = ctx.puppet
        now = ctx.now()
        if ev == 'click' or (ev == 'down' and C.INPUT_ONE_BUTTON):
            import menu
            ctx.speech.clear()
            ctx.push(menu.Menu())
        elif ev == 'hold':
            p.express('stare', 1600, now)
            ctx.say(phrases.pick('hold_home'))
        elif ev in _DIRS:
            dx, dy = _DIRS[ev]
            p.nudge(dx, dy)
            if random.random() < 0.3 and not ctx.speech.busy:
                p.express(random.choice(('excited', 'stare', 'nervous')), 900, now)
                ctx.say(phrases.pick('poke'))

    def update(self, now):
        ctx = self.ctx
        g = ctx.ghost
        p = ctx.puppet
        lvl = g.glitch
        if g.napping:
            return

        if not ctx.speech.busy and ticks_diff(now, self.next_chat) >= 0:
            if random.random() < 0.05 + 0.08 * lvl:
                ctx.say(phrases.pick('uncanny'))
                p.express('stare', 2200, now)
                import hw
                ctx.chirp(hw.WHISPER)
            else:
                mood = g.mood
                ctx.say(phrases.pick('idle_' + mood if 'idle_' + mood in phrases.POOLS else 'idle_calm'))
            gap = random.randint(C.CHATTER_MIN_S, C.CHATTER_MAX_S) * 1000
            if g.restless > 50:
                gap //= 2
            self.next_chat = ticks_add(now, gap)

        if ticks_diff(now, self.next_quirk) >= 0:
            roll = random.random()
            if roll < 0.25 + 0.3 * lvl:
                p.vanish(now)
            elif roll < 0.55:
                p.go(52, 10)
                p.express('stare', 2500, now)
            elif lvl > 0.45:
                p.express('nervous', 2000, now)
            else:
                p.express('excited', 900, now)
            self.next_quirk = ticks_add(now, random.randint(9000, 24000))

    @property
    def protect(self):
        return (0, 8) if self.ctx.timer.active else None

    def draw(self, r, now):
        ctx = self.ctx
        lvl = ctx.ghost.glitch
        if ctx.timer.active:
            # the ghost is holding your countdown
            import chrono
            t = chrono.fmt(ctx.timer.remaining(now) + 999)
            r.text(t, 128 - 8 * len(t), 0)
        ctx.puppet.draw(r, now, lvl)
        ctx.speech.draw(r, 47, now, lvl)
