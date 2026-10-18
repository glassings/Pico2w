# clockface -- the real time, when the ghost knows it.
# click: sync now   hold: back
#
# The digits sit in the protected band: decorations may glitch, the time
# never does.

from apps import App as Screen
import clock
import phrases

DIGITS_Y = 9
SCALE = 3


class App(Screen):
    protect = (DIGITS_Y - 1, DIGITS_Y + 8 * SCALE + 1)

    def enter(self, ctx):
        super().enter(ctx)
        ctx.speech.clear()
        self._remark()

    def exit(self):
        self.ctx.speech.clear()

    def _remark(self):
        lt = clock.localtime()
        if lt is None:
            key = 'clock_unknown'
        elif clock.in_quiet(lt):
            key = 'clock_night'
        elif clock.daypart(lt) == 'morning':
            key = 'clock_morning'
        else:
            key = 'clock_synced'
        self.ctx.say(phrases.pick(key))

    def event(self, ev):
        ctx = self.ctx
        if ev == 'hold':
            ctx.pop()
        elif ev == 'click' and not ctx.clock.busy:
            ctx.clock.request(ctx.now())

    def draw(self, r, now):
        ctx = self.ctx
        clk = ctx.clock
        lt = clock.localtime()
        if lt is None:
            r.text("time?", 0, 0)
            r.big_center("--:--", DIGITS_Y, SCALE)
        else:
            r.text(clock.fmt_date(lt), 0, 0)
            r.text(clock.ampm(lt), 112, 0)
            r.big_center(clock.fmt_time(lt), DIGITS_Y, SCALE)
            # seconds, as a creeping line under the digits
            r.o.hline(4, DIGITS_Y + 8 * SCALE + 1, lt[5] * 2, 1)

        ago = clk.ago_s(now)
        if clk.busy:
            line = "syncing" + "." * (1 + (now // 400) % 3)
        elif ago is not None:
            line = ("synced %dm ago" % (ago // 60)) if ago < 3600 else ("synced %dh ago" % (ago // 3600))
        else:
            line = clk.why or "never synced"
        r.text(line[:16], 0, DIGITS_Y + 8 * SCALE + 4)
        ctx.speech.draw(r, 47, now, ctx.ghost.glitch)
