# stopwatch -- counts up.  Keeps running if you leave the screen.
#
# click: start / stop   up: lap (while running)   left: reset (while stopped)
# hold: back

from apps import App as Screen
import chrono
import hw

DIGITS_Y = 14


class App(Screen):
    protect = (DIGITS_Y, 56)

    def event(self, ev):
        ctx = self.ctx
        w = ctx.watch
        now = ctx.now()
        if ev == 'hold':
            ctx.pop()
        elif ev == 'click':
            w.toggle(now)
            ctx.chirp(hw.START if w.running else hw.STOP)
        elif ev == 'up' and w.running:
            w.lap(now)
            ctx.chirp(hw.BLIP)
        elif ev == 'left' and not w.running:
            w.reset()
            ctx.chirp(hw.BLIP)

    def draw(self, r, now):
        w = self.ctx.watch
        ms = w.elapsed(now)
        r.text("stopwatch", 0, 0)
        if w.running:
            # a tiny spinning tick, so you can see it's alive
            r.text("-\\|/"[(now // 150) % 4], 120, 0)
        r.big_center(chrono.fmt(ms, tenths=True), DIGITS_Y, 2)
        y = 36
        for i, lap in enumerate(w.laps[:2]):
            r.text("lap%d %s" % (len(w.laps) - i, chrono.fmt(lap, tenths=True)), 8, y)
            y += 9
        if w.running:
            r.text("click stop ^lap", 0, 56)
        elif ms:
            r.text("click go <reset", 0, 56)
        else:
            r.text("click: start", 0, 56)
