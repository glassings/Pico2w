# halloween.py -- the season creeps in, peaks on Oct 31, and lets go.
#
# level() is 0 before Oct 24, ramps to 1.0 on Oct 31, and is 0 again from
# Nov 1 (which gets one 'halloween_over').  The setting 'auto/on/off' is
# persisted; 'on' forces 1.0 for testing, 'auto' with no clock means off.
#
# Everything else asks ctx.hw (the level, refreshed once a second).

import random
from time import ticks_diff, ticks_add
import clock
import config as C

MODES = ('auto', 'on', 'off')


def level(mode, lt):
    if mode == 'on':
        return 1.0
    if mode == 'off':
        return 0.0
    if C.HALLOWEEN_PRETEND_OCT31:
        return 1.0
    if lt is None:
        return 0.0
    m, d = lt[1], lt[2]
    if m == 10 and d >= 24:
        return (d - 24) / 7
    return 0.0


def is_oct31(lt):
    if C.HALLOWEEN_PRETEND_OCT31:
        return True
    return lt is not None and (lt[1], lt[2]) == (10, 31)


def knock_window(lt):
    if C.HALLOWEEN_PRETEND_OCT31:
        return True
    return is_oct31(lt) and C.KNOCK_FROM <= lt[3] < C.KNOCK_UNTIL


class Season:
    def __init__(self):
        self.next_knock = None
        self.bat_x = None           # a bat crossing the room, if any
        self.bat_y = 0

    def _gap_ms(self):
        lo, hi = C.KNOCK_GAP_MIN
        if C.HALLOWEEN_PRETEND_OCT31:
            lo, hi = 1, 3           # testing: knocks come quickly
        return random.randint(lo * 60, hi * 60) * 1000

    def tick(self, ctx, now):
        """Once a second."""
        import phrases
        s = ctx.mem.state
        lt = clock.localtime()
        hw = level(s.get('halloween', 'auto'), lt)
        ctx.hw = hw
        ctx.ghost.hw = hw
        ctx.puppet.hat = hw >= 0.3

        # a bat now and then
        if self.bat_x is None and hw > 0 and random.random() < 0.02 * hw:
            self.bat_x = -12
            self.bat_y = random.randint(2, 18)

        if not (ctx.awake and ctx.booted):
            return

        # Nov 1: once
        if lt is not None and (lt[1], lt[2]) == (11, 1) and s.get('hw_over') != lt[0] \
                and not C.HALLOWEEN_PRETEND_OCT31:
            s['hw_over'] = lt[0]
            ctx.mem.touch()
            ctx.say(phrases.pick('halloween_over'), queue=True)

        # Oct 31 evening: knocks
        if not knock_window(lt):
            self.next_knock = None
            return
        if self.next_knock is None:
            self.next_knock = ticks_add(now, self._gap_ms() // 3)
            return
        if ticks_diff(now, self.next_knock) < 0:
            return
        day = 0 if lt is None else clock.day_number(lt)
        k = s.get('knocks') or [day, 0]
        if k[0] != day:
            k = [day, 0]
        if k[1] >= C.KNOCK_MAX:
            return
        import apps.home
        if not isinstance(ctx.top, apps.home.App):
            # don't barge into the timer or a game; try again shortly
            self.next_knock = ticks_add(now, 20000)
            return
        k[1] += 1
        s['knocks'] = k
        ctx.mem.touch()
        self.next_knock = ticks_add(now, self._gap_ms())
        import apps.knock
        ctx.push(apps.knock.App())

    def draw_room(self, r, ctx, now):
        """Decorations for the home screen (drawn before the ghost)."""
        import sprites
        hw = ctx.hw
        if hw <= 0:
            return
        r.sprite(sprites.PUMPKIN, 114, 34)
        if hw >= 0.5 and not ctx.ghost.napping:
            # eyes in the dark corner, blinking now and then
            blink = (now // 120) % 37 == 0
            r.sprite(sprites.EYES[1 if blink else 0], 3, 3)
        if self.bat_x is not None:
            r.sprite(sprites.BAT[(now // 150) & 1], self.bat_x, self.bat_y)
            self.bat_x += 3
            self.bat_y += random.randint(-1, 1)
            if self.bat_x > 128:
                self.bat_x = None
