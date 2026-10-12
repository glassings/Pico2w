# dice -- the ghost rolls the bones.
#
# left/right: pick the die   click: roll   hold: back
#
# The real result is chosen the moment you click; the tumbling numbers
# before it are just for show, and the result itself is never glitched.

import random
from time import ticks_diff, ticks_add
from apps import App as Screen
import phrases
import hw

DICE = (4, 6, 8, 10, 12, 20)
ROLL_MS = 1000
NUM_Y = 13
SCALE = 4


class App(Screen):
    def enter(self, ctx):
        super().enter(ctx)
        self.die = 5                # d20
        self.result = None
        self.rolling = None         # ticks when the roll started
        self.shown = None
        self.next_flip = 0
        self.history = []
        ctx.speech.clear()

    def exit(self):
        self.ctx.speech.clear()

    @property
    def glitch(self):
        return 0.85 if self.rolling is not None else None

    @property
    def protect(self):
        if self.rolling is None and self.result is not None:
            return (NUM_Y, NUM_Y + 8 * SCALE)
        return None

    def event(self, ev):
        ctx = self.ctx
        if ev == 'hold':
            ctx.pop()
            return
        if self.rolling is not None:
            return
        if ev == 'left':
            self.die = (self.die - 1) % len(DICE)
            self.result = None
        elif ev == 'right':
            self.die = (self.die + 1) % len(DICE)
            self.result = None
        elif ev in ('click', 'up', 'down'):
            if self.result is not None:
                self.history.insert(0, self.result)
                del self.history[3:]
            self.result = random.randint(1, DICE[self.die])
            self.rolling = ctx.now()
            ctx.speech.clear()

    def update(self, now):
        if self.rolling is None:
            return
        if ticks_diff(now, self.next_flip) >= 0:
            self.shown = random.randint(1, DICE[self.die])
            # slows down as it settles
            self.next_flip = ticks_add(now, 40 + ticks_diff(now, self.rolling) // 6)
            self.ctx.chirp(hw.TICK)
        if ticks_diff(now, self.rolling) >= ROLL_MS:
            self.rolling = None
            ctx = self.ctx
            n = DICE[self.die]
            ctx.buzzer.stop()           # cut off the rattle
            if self.result == n and n > 2:
                ctx.chirp(hw.HIGH)
                ctx.say(phrases.pick('dice_max'))
            elif self.result == 1:
                ctx.chirp(hw.LOW)
                ctx.say(phrases.pick('dice_min'))
            else:
                ctx.chirp(hw.ROLLED)

    def draw(self, r, now):
        ctx = self.ctx
        r.center("< d%d >" % DICE[self.die], 0)
        if self.rolling is not None:
            jx = random.randint(-3, 3)
            jy = random.randint(-2, 2)
            s = str(self.shown)
            r.big(s, (128 - len(s) * 8 * SCALE) // 2 + jx, NUM_Y + jy, SCALE)
        elif self.result is not None:
            r.big_center(str(self.result), NUM_Y, SCALE)
        else:
            r.center("click to roll", 26)

        if ctx.speech.busy:
            ctx.speech.draw(r, 47, now, ctx.ghost.glitch)
        elif self.history:
            r.text("was: " + ' '.join(str(h) for h in self.history), 0, 56)
