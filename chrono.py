# chrono.py -- the countdown and stopwatch the ghost holds for you.
# They live on Ctx, not in their screens, so they keep running while you
# browse the menu, listen, or with the screen off.  Pure ticks_ms maths.

from time import ticks_diff, ticks_add


def fmt(ms, tenths=False):
    """ms -> 'M:SS', 'H:MM:SS', or 'MM:SS.t'"""
    s = ms // 1000
    h = s // 3600
    m = (s // 60) % 60
    s %= 60
    if h:
        return "%d:%02d:%02d" % (h, m, s)
    if tenths:
        return "%02d:%02d.%d" % (m, s, (ms // 100) % 10)
    return "%d:%02d" % (m, s)


class Countdown:
    def __init__(self, set_s=300):
        self.set_s = set_s
        self.end = None         # ticks when it rings (running)
        self.left = None        # ms left (paused)

    @property
    def running(self):
        return self.end is not None

    @property
    def paused(self):
        return self.left is not None

    @property
    def active(self):
        return self.end is not None or self.left is not None

    def start(self, now):
        self.end = ticks_add(now, self.set_s * 1000)
        self.left = None

    def pause(self, now):
        self.left = max(0, ticks_diff(self.end, now))
        self.end = None

    def resume(self, now):
        self.end = ticks_add(now, self.left)
        self.left = None

    def cancel(self):
        self.end = None
        self.left = None

    def remaining(self, now):
        if self.end is not None:
            return max(0, ticks_diff(self.end, now))
        if self.left is not None:
            return self.left
        return self.set_s * 1000

    def check(self, now):
        """True exactly once, when it runs out."""
        if self.end is not None and ticks_diff(now, self.end) >= 0:
            self.end = None
            return True
        return False


class Stopwatch:
    def __init__(self):
        self.acc = 0            # ms banked
        self.t0 = None          # ticks of last bank while running
        self.laps = []          # newest first, ms

    @property
    def running(self):
        return self.t0 is not None

    def tick(self, now):
        # bank elapsed time often so ticks_ms wrap-around never bites
        if self.t0 is not None:
            self.acc += ticks_diff(now, self.t0)
            self.t0 = now

    def elapsed(self, now):
        self.tick(now)
        return self.acc

    def toggle(self, now):
        if self.t0 is None:
            self.t0 = now
        else:
            self.tick(now)
            self.t0 = None

    def lap(self, now):
        self.laps.insert(0, self.elapsed(now))
        del self.laps[3:]

    def reset(self):
        self.acc = 0
        self.t0 = None
        self.laps = []
