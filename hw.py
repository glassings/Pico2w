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
