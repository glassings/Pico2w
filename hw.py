# hw.py -- the ghost's body: display and joystick.
# (buzzer arrives in phase 3, glow in phase 4)

from machine import Pin, I2C, ADC
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
