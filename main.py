# main.py -- Pocket Ghost.  Boot, main loop, scheduling.
#
# A single cooperative loop: read the stick, let the ghost's needs drift,
# update + draw the top screen, glitch it, push it to the OLED, sleep out
# the rest of the frame.  Nothing in here blocks for long.

import gc
import sys
from time import ticks_ms, ticks_diff, sleep_ms

import config as C
import hw
import phrases
from memory import Memory
from ghost import Ghost
from render import Renderer, Speech, Puppet, wrap
from chrono import Countdown, Stopwatch


class Ctx:
    """Everything a screen might need, passed around as one object."""

    def __init__(self, oled, joy, buzzer, mem, ghost):
        self.oled = oled
        self.joy = joy
        self.buzzer = buzzer
        self.timer = Countdown(mem.state.get('timer_s', 300))
        self.watch = Stopwatch()
        self.mem = mem
        self.ghost = ghost
        self.r = Renderer(oled)
        self.speech = Speech()
        self.puppet = Puppet()
        self.stack = []
        self.awake = True
        self._queue = []

    @staticmethod
    def now():
        return ticks_ms()

    # ---- screen stack
    @property
    def top(self):
        return self.stack[-1]

    def push(self, app):
        self.stack.append(app)
        app.enter(self)

    def pop(self):
        if len(self.stack) > 1:
            self.stack.pop().exit()
            self.top.resume()

    def home(self):
        while len(self.stack) > 1:
            self.pop()

    # ---- voice
    def say(self, phrase, queue=False):
        if queue and (self.speech.busy or self._queue):
            self._queue.append(phrase)
        else:
            self.speech.say(phrase, ticks_ms(), self.ghost.glitch)

    def update_speech(self, now):
        self.speech.update(now)
        if self._queue and not self.speech.busy:
            self.speech.say(self._queue.pop(0), now, self.ghost.glitch)

    def chirp(self, tune):
        """A small UI sound (not alarms), if those are switched on."""
        if C.BUZZER_CLICKS and not self.buzzer.busy:
            self.buzzer.play(tune)

    def alarm(self, now):
        """The countdown ran out: wake up and say so, whatever is on screen."""
        if not self.awake:
            self.awake = True
            self.oled.poweron()
        self.ghost.poke(now)
        import apps.alarm
        self.push(apps.alarm.App())

    # ---- screen power
    def screen_off(self):
        if not self.awake:
            return
        self.awake = False
        self.speech.clear()
        self._queue = []
        self.r.clear()
        self.oled.show()
        self.oled.poweroff()
        self.mem.save()            # a natural moment to checkpoint

    def screen_on(self, now):
        self.awake = True
        self.oled.poweron()
        p = self.puppet
        p.vanish_t = now - 1000     # starts hidden, materialises somewhere
        p.hidden = True
        self.say(phrases.pick('screen_woke'))


def boot_remarks(ghost, situation, days):
    out = [phrases.pick('wake_' + situation, n=days)]
    if ghost.hunger > 60:
        out.append(phrases.pick('wake_hungry'))
    return out


def loop(ctx):
    joy = ctx.joy
    ghost = ctx.ghost
    mem = ctx.mem
    r = ctx.r
    oled = ctx.oled
    gc_t = ticks_ms()

    while True:
        now = ticks_ms()
        evs = joy.poll(now)
        ctx.buzzer.update(now)
        ctx.watch.tick(now)
        if ctx.timer.check(now):
            ctx.alarm(now)

        # ---- screen off: just keep time and wait for a click
        if not ctx.awake:
            if 'click' in evs:
                ghost.poke(now)
                ctx.screen_on(now)
            ghost.tick(now)
            mem.maybe_save(now)
            sleep_ms(C.SLEEP_POLL_MS)
            continue

        if evs:
            if ghost.poke(now):
                # the first touch only wakes it from its nap
                ctx.puppet.express('stare', 900, now)
                ctx.say(phrases.pick('nap_woke'))
            else:
                for ev in evs:
                    ctx.top.event(ev)

        ghost.tick(now)
        app = ctx.top
        if ghost.idle_s(now) >= C.SCREEN_OFF_AFTER_S and app.allow_screen_off:
            ctx.screen_off()
            continue

        app.update(now)
        app = ctx.top               # update() may have switched screens
        if not ctx.awake:
            continue
        ctx.update_speech(now)
        lvl = ghost.glitch if app.glitch is None else app.glitch
        ctx.puppet.asleep = ghost.napping
        ctx.puppet.update(now, lvl)

        r.clear()
        app.draw(r, now)
        r.glitch_pass(lvl, app.protect)
        oled.show()

        mem.maybe_save(now)
        if ticks_diff(now, gc_t) > 2000:
            gc_t = now
            gc.collect()
        dt = ticks_diff(ticks_ms(), now)
        if dt < C.FRAME_MS:
            sleep_ms(C.FRAME_MS - dt)


def show_crash(oled, e):
    try:
        oled.poweron()
        oled.invert(0)
        oled.fill(0)
        oled.text("i broke.", 0, 0)
        y = 12
        for _, line in wrap("%s: %s" % (type(e).__name__, e), 16, 5):
            oled.text(line, 0, y)
            y += 10
        oled.show()
    except Exception:
        pass


def run():
    try:
        oled = hw.make_display()
    except Exception as e:
        print("[boot] display failed:", e)
        raise
    joy = hw.Inputs()
    buzzer = hw.Buzzer()
    mem = Memory()
    ghost = Ghost(mem)
    situation, days = ghost.on_boot()
    print("[boot] boot #%d, %s, alive %.2f days, mood=%s"
          % (mem.state['boots'], situation, ghost.days_alive, ghost.mood))

    ctx = Ctx(oled, joy, buzzer, mem, ghost)
    import apps.home
    import apps.wake
    ctx.push(apps.home.App())
    ctx.push(apps.wake.App(boot_remarks(ghost, situation, days)))
    try:
        loop(ctx)
    except KeyboardInterrupt:
        buzzer.stop()
        mem.save()
        oled.fill(0)
        oled.show()
        print("[main] stopped")
    except Exception as e:
        sys.print_exception(e)
        buzzer.stop()
        mem.save()
        show_crash(oled, e)


run()
