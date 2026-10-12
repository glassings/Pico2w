# ghost.py -- the ghost's inner life: needs, mood drift, reactions.
#
#   hunger      0..100  rises slowly with time; feeding (phase 2) lowers it
#   restless    0..100  rises when ignored, falls when you touch the stick
#   content     0..100  slowly follows how well the other two are going
#
# Everything is driven by ticks_ms, so it keeps working with no RTC.

import time
from time import ticks_ms, ticks_diff
import config as C


def _clamp(v, lo=0.0, hi=100.0):
    return lo if v < lo else hi if v > hi else v


def wall_clock():
    """Seconds since 1970 if the RTC looks set (Thonny/mpremote set it when
    connected to a PC), else 0."""
    try:
        if time.localtime()[0] >= 2025:
            return int(time.time())
    except Exception:
        pass
    return 0


class Ghost:
    def __init__(self, mem):
        self.mem = mem
        m = mem.state['mood']
        self.hunger = float(m['hunger'])
        self.restless = float(m['restless'])
        self.content = float(m['content'])
        now = ticks_ms()
        self.boot_t = now
        self.last_input = now
        self._last_tick = now
        self.napping = False

    # ------------------------------------------------------------ boot
    def on_boot(self):
        """Account for the time spent off.  Returns (situation, days_off)
        where situation is one of 'first', 'short', 'medium', 'long',
        'unknown'."""
        s = self.mem.state
        first = s['boots'] == 0
        s['boots'] += 1
        off_s = None
        wall = wall_clock()
        if wall and s['last_wall']:
            off_s = wall - s['last_wall']
            if off_s < 0:
                off_s = None
        if off_s:
            self.hunger = _clamp(self.hunger + C.HUNGER_OFF_PER_HOUR * off_s / 3600)
        self.mem.touch(urgent=True)
        if first:
            return 'first', 0
        if off_s is None:
            return 'unknown', 0
        if off_s < 600:
            return 'short', 0
        if off_s < 86400:
            return 'medium', 0
        return 'long', off_s // 86400

    # ------------------------------------------------------------ time
    def tick(self, now):
        """Call every loop; does its work about once a second."""
        dt = ticks_diff(now, self._last_tick)
        if dt < 1000:
            return
        self._last_tick = now
        sec = dt / 1000
        idle = self.idle_s(now)

        self.hunger = _clamp(self.hunger + C.HUNGER_PER_HOUR * sec / 3600)
        self.napping = idle >= C.NAP_AFTER_S
        if self.napping:
            self.restless -= C.RESTLESS_NAP_DECAY_PER_MIN * sec / 60
        elif idle >= C.RESTLESS_AFTER_S:
            self.restless += C.RESTLESS_PER_MIN * sec / 60
        self.restless = _clamp(self.restless)

        target = 100 - (0.6 * self.hunger + 0.4 * self.restless)
        k = sec / C.CONTENT_TAU_S
        self.content = _clamp(self.content + (target - self.content) * (k if k < 1 else 1))

        s = self.mem.state
        s['alive_s'] += sec
        s['last_session_s'] = ticks_diff(now, self.boot_t) // 1000
        s['last_wall'] = wall_clock()
        m = s['mood']
        m['hunger'] = round(self.hunger, 2)
        m['restless'] = round(self.restless, 2)
        m['content'] = round(self.content, 2)
        self.mem.touch()

    def idle_s(self, now):
        return ticks_diff(now, self.last_input) / 1000

    # ------------------------------------------------------------ reactions
    def poke(self, now):
        """Any joystick input.  Returns True if this woke it from a nap."""
        self.last_input = now
        self.restless = _clamp(self.restless - C.RESTLESS_PER_INPUT)
        woke = self.napping
        self.napping = False
        return woke

    # ------------------------------------------------------------ readouts
    @property
    def glitch(self):
        """0.05 (calm) .. 1.0 (falling apart)."""
        g = 0.15 + (0.55 * self.hunger + 0.6 * self.restless - 0.35 * self.content) / 100
        return _clamp(g, 0.05, 1.0)

    @property
    def mood(self):
        if self.napping:
            return 'drowsy'
        if self.hunger > 75:
            return 'starving'
        if self.restless > 60:
            return 'restless'
        if self.hunger > 50:
            return 'hungry'
        if self.content > 65:
            return 'content'
        if self.glitch > 0.5:
            return 'uneasy'
        return 'calm'

    @property
    def days_alive(self):
        return self.mem.state['alive_s'] / 86400
