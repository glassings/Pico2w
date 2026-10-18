# knock -- Oct 31, evening: someone is at the door.
#
#   treat: click (or down / right)      trick: left (one button: long press)
#   do nothing for 20 s and they leave.
#
# The trick is a harmless glitch show.  It never plays the alarm or shows
# anything that looks like the timer.

from time import ticks_diff
import random
from apps import App as Screen
import phrases
import hw
import config as C

WAIT_MS = 20000
SHOW_MS = 4200


class App(Screen):
    allow_screen_off = False

    def enter(self, ctx):
        super().enter(ctx)
        self.t0 = ctx.now()
        self.phase = 'knock'        # knock -> treat | trick | missed
        self.t1 = 0
        ctx.speech.clear()
        ctx.ghost.napping = False
        ctx.ghost.last_input = self.t0
        ctx.chirp(hw.KNOCK)
        ctx.puppet.set_bounds(100, 8, 100, 8, snap=True)
        ctx.puppet.express('stare', 3000, self.t0)
        ctx.say(phrases.pick('knock'))

    def exit(self):
        self.ctx.speech.clear()

    @property
    def glitch(self):
        if self.phase == 'trick' and ticks_diff(self.ctx.now(), self.t1) < 1700:
            return 1.0
        return None

    def event(self, ev):
        if self.phase != 'knock':
            return
        ctx = self.ctx
        now = ctx.now()
        if ev in ('click', 'down', 'right'):
            self.phase = 'treat'
            g = ctx.ghost
            g.content = min(100.0, g.content + 8)
            ctx.puppet.express('excited', 2500, now)
            ctx.speech.clear()
            ctx.say(phrases.pick('treat_given'))
            ctx.chirp(hw.ROLLED)
        elif ev in ('left', 'up'):
            self.phase = 'trick'
            ctx.r.burst(14)
            ctx.speech.clear()
        elif ev == 'hold':
            self._missed(now)
            return
        self.t1 = now

    def _missed(self, now):
        ctx = self.ctx
        self.phase = 'missed'
        self.t1 = now
        g = ctx.ghost
        g.restless = min(100.0, g.restless + 10)    # it sulks
        ctx.puppet.express('nervous', 3500, now)
        ctx.speech.clear()
        ctx.say(phrases.pick('knock_missed'))

    def update(self, now):
        ctx = self.ctx
        if self.phase == 'knock':
            if ticks_diff(now, self.t0) > WAIT_MS:
                self._missed(now)
            return
        t = ticks_diff(now, self.t1)
        if self.phase == 'trick' and t > 1700 and not ctx.speech.busy and not getattr(self, '_said', False):
            self._said = True
            ctx.puppet.express('excited', 2000, now)
            ctx.say(phrases.pick('trick_played'))
        if t > SHOW_MS:
            ctx.pop()

    def draw(self, r, now):
        ctx = self.ctx
        t0 = ticks_diff(now, self.t0)
        if self.phase == 'knock':
            # the words shudder with each knock
            jx = random.randint(-2, 2) if (t0 // 250) % 4 == 0 else 0
            r.big("knock", 2 + jx, 2, 2)
            r.big("knock", 2 - jx, 20, 2)
            if not ctx.speech.busy:
                one = C.INPUT_ONE_BUTTON
                r.text("1 click: treat" if one else "click: treat", 0, 40)
                r.text("long: trick" if one else "left: trick", 0, 49)
        elif self.phase == 'trick':
            t = ticks_diff(now, self.t1)
            if t < 600:
                r.static(2)
            elif t < 1700:
                # a fake fault that very obviously isn't one
                r.text("ERR 0x31 BOO", 8, 10)
                r.text("ghost.exe has", 8, 24)
                r.text("stopped hiding", 8, 34)
            else:
                r.text("...fixed.", 40, 20)
        ctx.puppet.draw(r, now, ctx.ghost.glitch)
        ctx.speech.draw(r, 47, now, ctx.ghost.glitch)
