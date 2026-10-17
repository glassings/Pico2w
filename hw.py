# hw.py -- the ghost's body: display, joystick, buzzer.
# (glow arrives in phase 4)

from machine import Pin, I2C, ADC, PWM
from time import ticks_ms, ticks_diff, ticks_add
import config as C


def make_display():
    i2c = I2C(C.I2C_ID, sda=Pin(C.PIN_SDA), scl=Pin(C.PIN_SCL), freq=C.I2C_FREQ)
    found = i2c.scan()
    if C.OLED_ADDR in found:
        addr = C.OLED_ADDR
    elif 0x3D in found:
        addr = 0x3D
    else:
        raise OSError("no OLED on I2C%d (scan=%s). check SDA->GP%d, SCL->GP%d, 3.3V, GND"
                      % (C.I2C_ID, [hex(a) for a in found], C.PIN_SDA, C.PIN_SCL))
    import ssd1306
    oled = ssd1306.SSD1306_I2C(C.OLED_W, C.OLED_H, i2c, addr=addr)
    oled.contrast(C.OLED_CONTRAST)
    return oled


class Joystick:
    """Analog stick + push switch, turned into discrete events.

    poll() returns a list drawn from:
      'up' 'down' 'left' 'right'  -- on push, then auto-repeat while held
      'click'                     -- short press, fired on release
      'hold'                      -- fired once, while still pressed, after BTN_HOLD_MS
    """

    def __init__(self):
        self.ax = ADC(Pin(C.PIN_JOY_X))
        self.ay = ADC(Pin(C.PIN_JOY_Y))
        self.sw = Pin(C.PIN_JOY_SW, Pin.IN, Pin.PULL_UP)
        self.cx = self._center(self.ax, "X")
        self.cy = self._center(self.ay, "Y")
        self.dir = None
        self.next_rep = 0
        self.pressed = False        # debounced
        self._raw = False
        self._raw_t = ticks_ms()
        self._press_t = 0
        self._held = False
        self._dbg_t = 0

    @staticmethod
    def _center(adc, name):
        # Assumes nobody is touching the stick at boot.
        tot = 0
        for _ in range(16):
            tot += adc.read_u16()
        c = tot // 16
        if not 20000 < c < 45000:
            print("[joy] %s centre reads %d -- stick touched at boot, or not wired?" % (name, c))
            c = 32768
        return c

    @staticmethod
    def _norm(raw, c):
        # -1..+1, with each half scaled separately (centres are rarely exactly mid-rail)
        if raw >= c:
            return (raw - c) / (65535 - c)
        return (raw - c) / c

    def read(self):
        x = self._norm(self.ax.read_u16(), self.cx)
        y = self._norm(self.ay.read_u16(), self.cy)
        if C.JOY_SWAP_XY:
            x, y = y, x
        if C.JOY_INVERT_X:
            x = -x
        if C.JOY_INVERT_Y:
            y = -y
        return x, y

    def poll(self, now):
        ev = []
        x, y = self.read()

        if C.JOY_DEBUG and ticks_diff(now, self._dbg_t) > 200:
            self._dbg_t = now
            print("[joy] x=%+.2f y=%+.2f sw=%d" % (x, y, self.sw.value()))

        # --- direction, with hysteresis so a stick resting near the edge doesn't chatter
        on = C.JOY_DEADZONE
        off = on * 0.6
        d = self.dir
        keep = ((d == 'left' and x < -off) or (d == 'right' and x > off) or
                (d == 'up' and y < -off) or (d == 'down' and y > off))
        if not keep:
            d = None
            if abs(x) >= abs(y):
                if abs(x) > on:
                    d = 'right' if x > 0 else 'left'
            elif abs(y) > on:
                d = 'down' if y > 0 else 'up'
        if d != self.dir:
            self.dir = d
            if d:
                ev.append(d)
                self.next_rep = ticks_add(now, C.JOY_REPEAT_DELAY_MS)
        elif d and ticks_diff(now, self.next_rep) >= 0:
            ev.append(d)
            self.next_rep = ticks_add(now, C.JOY_REPEAT_MS)

        # --- button: debounce, then split into click / hold
        raw = not self.sw.value()
        if raw != self._raw:
            self._raw = raw
            self._raw_t = now
        if raw != self.pressed and ticks_diff(now, self._raw_t) >= C.BTN_DEBOUNCE_MS:
            self.pressed = raw
            if raw:
                self._press_t = now
                self._held = False
            elif not self._held:
                ev.append('click')
        if self.pressed and not self._held and ticks_diff(now, self._press_t) >= C.BTN_HOLD_MS:
            self._held = True
            ev.append('hold')
        return ev


# ------------------------------------------------------------------ buzzer
# A tune is a tuple of (start_hz, end_hz, ms) steps.  start_hz 0 = silence;
# a different end_hz glides between the two (passive buzzers only).

BOOT = ((220, 330, 260), (0, 0, 70), (330, 233, 420))
ALARM = ((880, 880, 120), (0, 0, 70), (880, 880, 120), (0, 0, 70),
         (660, 520, 420), (0, 0, 700))
TICK = ((1400, 1400, 15),)
BLIP = ((990, 990, 40),)
START = ((520, 780, 120),)
STOP = ((780, 520, 120),)
ROLLED = ((523, 523, 70), (0, 0, 30), (784, 784, 140))
HIGH = ((400, 1600, 450),)
LOW = ((600, 150, 600),)
WHISPER = ((1900, 1700, 40),)


class Buzzer:
    """Non-blocking: play() starts a tune, update() (every loop) advances it."""

    def __init__(self):
        self.enabled = C.BUZZER_ENABLED
        self.seq = None
        self._f = 0
        self.pwm = None
        self.pin = None
        if not self.enabled:
            return
        if C.BUZZER_ACTIVE:
            self.pin = Pin(C.PIN_BUZZER, Pin.OUT, value=0)
        else:
            self.pwm = PWM(Pin(C.PIN_BUZZER))
            self.pwm.duty_u16(0)

    @property
    def busy(self):
        return self.seq is not None

    def play(self, seq, loop=False):
        if not self.enabled:
            return
        now = ticks_ms()
        self.seq = seq
        self.loop = loop
        self.i = -1
        self.t_end = now
        self.update(now)

    def stop(self):
        self.seq = None
        self._out(0)

    def _out(self, f):
        f = int(f)
        if f == self._f:
            return
        self._f = f
        if self.pwm:
            if f:
                self.pwm.freq(f)
                self.pwm.duty_u16(int(65535 * C.BUZZER_DUTY))
            else:
                self.pwm.duty_u16(0)
        elif self.pin:
            self.pin.value(1 if f else 0)

    def update(self, now):
        if self.seq is None:
            return
        while ticks_diff(now, self.t_end) >= 0:
            self.i += 1
            if self.i >= len(self.seq):
                if not self.loop:
                    self.stop()
                    return
                self.i = 0
            self.t0 = self.t_end
            self.t_end = ticks_add(self.t_end, self.seq[self.i][2])
        f0, f1, ms = self.seq[self.i]
        if f0 and f1 != f0:
            f0 += (f1 - f0) * ticks_diff(now, self.t0) / ms
        self._out(f0)


# ------------------------------------------------------- other controls
# Buttons and the rotary encoder produce exactly the same events as the
# joystick, so no screen needs to know which one you're holding.

class _Key:
    """One debounced push button wired between a GPIO and GND."""

    def __init__(self, pin):
        self.pin = Pin(pin, Pin.IN, Pin.PULL_UP)
        self.down = False           # debounced
        self._raw = False
        self._t = ticks_ms()

    def update(self, now):
        """-> 'press', 'release' or None"""
        raw = not self.pin.value()
        if raw != self._raw:
            self._raw = raw
            self._t = now
        if raw != self.down and ticks_diff(now, self._t) >= C.BTN_DEBOUNCE_MS:
            self.down = raw
            return 'press' if raw else 'release'
        return None


class _Select:
    """Click/hold logic for an 'ok' button.  While it is held, other inputs
    can 'use' it (a chord), and then it produces neither click nor hold."""

    def __init__(self, key):
        self.key = key
        self.t = 0
        self.held = False
        self.used = False

    def poll(self, now, ev):
        k = self.key
        e = k.update(now)
        if e == 'press':
            self.t = now
            self.held = False
            self.used = False
        elif e == 'release' and not self.held and not self.used:
            ev.append('click')
        if k.down and not self.held and not self.used and ticks_diff(now, self.t) >= C.BTN_HOLD_MS:
            self.held = True
            ev.append('hold')


class Buttons:
    """3 to 6 push buttons.  Only up, down and ok are required.

    Without left/right buttons: hold ok and press up/down = left/right.
    Without a back button: hold ok = back (as with the joystick).
    """

    def __init__(self):
        self.ok = _Select(_Key(C.PIN_BTN_OK))
        self.back = _Key(C.PIN_BTN_BACK) if C.PIN_BTN_BACK is not None else None
        self.dirs = []              # [key, name, current_event, next_repeat]
        for name, pin in (('up', C.PIN_BTN_UP), ('down', C.PIN_BTN_DOWN),
                          ('left', C.PIN_BTN_LEFT), ('right', C.PIN_BTN_RIGHT)):
            if pin is not None:
                self.dirs.append([_Key(pin), name, None, 0])
        self.chord = C.PIN_BTN_LEFT is None or C.PIN_BTN_RIGHT is None

    def poll(self, now):
        ev = []
        ok = self.ok
        for d in self.dirs:
            key, name = d[0], d[1]
            e = key.update(now)
            if e == 'press':
                out = name
                if self.chord and ok.key.down and not ok.held and name in ('up', 'down'):
                    out = 'left' if name == 'up' else 'right'
                    ok.used = True
                d[2] = out
                d[3] = ticks_add(now, C.JOY_REPEAT_DELAY_MS)
                ev.append(out)
            elif e == 'release':
                d[2] = None
            elif key.down and d[2] and ticks_diff(now, d[3]) >= 0:
                d[3] = ticks_add(now, C.JOY_REPEAT_MS)
                ev.append(d[2])
        ok.poll(now, ev)
        if self.back and self.back.update(now) == 'press':
            ev.append('hold')
        return ev


class OneButton:
    """Everything with one button, by counting clicks.

      1 click  = down (next)      2 clicks = click (confirm)
      3 clicks = hold (back)      4+ clicks = up
      long press = left (switch field / previous / reset)
    """

    def __init__(self):
        self.key = _Key(C.PIN_ONE_BTN)
        self.n = 0              # clicks counted so far
        self.t = 0              # press time while down, release time after
        self.long = False

    def poll(self, now):
        ev = []
        k = self.key
        e = k.update(now)
        if e == 'press':
            self.t = now
            self.long = False
        elif e == 'release' and not self.long:
            self.n += 1
            self.t = now
        if k.down and not self.long and ticks_diff(now, self.t) >= C.BTN_HOLD_MS:
            self.long = True
            self.n = 0
            ev.append('left')
        elif self.n and not k.down and ticks_diff(now, self.t) >= C.MULTI_CLICK_MS:
            ev.append(('down', 'click', 'hold')[self.n - 1] if self.n <= 3 else 'up')
            self.n = 0
        return ev


# quadrature state table: (previous AB << 2 | new AB) -> step
_QUAD = (0, -1, 1, 0, 1, 0, 0, -1, -1, 0, 0, 1, 0, 1, -1, 0)


class Encoder:
    """Rotary encoder with push switch (KY-040 / EC11).
    Turn = up/down.  Press = click, long press = back.
    Press and turn = left/right."""

    def __init__(self):
        self.a = Pin(C.PIN_ENC_CLK, Pin.IN, Pin.PULL_UP)
        self.b = Pin(C.PIN_ENC_DT, Pin.IN, Pin.PULL_UP)
        self.sel = _Select(_Key(C.PIN_ENC_SW))
        self.state = (self.a.value() << 1) | self.b.value()
        self.acc = 0
        trig = Pin.IRQ_RISING | Pin.IRQ_FALLING
        self.a.irq(self._irq, trig)
        self.b.irq(self._irq, trig)

    def _irq(self, pin):
        s = (self.a.value() << 1) | self.b.value()
        self.acc += _QUAD[(self.state << 2) | s]
        self.state = s

    def poll(self, now):
        ev = []
        step = C.ENC_STEPS_PER_DETENT
        sel = self.sel
        self.sel.poll(now, ev)
        while self.acc >= step or self.acc <= -step:
            cw = self.acc > 0
            self.acc += -step if cw else step
            if C.ENC_INVERT:
                cw = not cw
            if sel.key.down and not sel.held:
                sel.used = True
                ev.append('right' if cw else 'left')
            else:
                ev.append('down' if cw else 'up')
        return ev


class Inputs:
    """Every enabled control, merged into one stream of events."""

    def __init__(self):
        self.srcs = []
        if C.INPUT_JOYSTICK:
            self.srcs.append(Joystick())
        if C.INPUT_BUTTONS:
            self.srcs.append(Buttons())
        if C.INPUT_ONE_BUTTON:
            self.srcs.append(OneButton())
        if C.INPUT_ENCODER:
            self.srcs.append(Encoder())
        if not self.srcs:
            print("[input] no controls enabled in config.py!")

    def poll(self, now):
        ev = []
        for s in self.srcs:
            ev += s.poll(now)
        return ev
