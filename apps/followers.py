# followers -- (step 1: raw view) live Bluetooth tracker detections.
#
# Scans continuously while open, showing every advertisement the tracker
# classifier recognises.  Receive-only: nothing is ever connected to.
# Addresses stay in RAM, only for as long as this screen is open.
#
# up/down: scroll   hold: back

from time import ticks_diff
from apps import App as Screen
import trackers
import config as C

_IRQ_SCAN_RESULT = 5
_IRQ_SCAN_DONE = 6
ROWS = 3


class App(Screen):
    allow_screen_off = False

    def enter(self, ctx):
        super().enter(ctx)
        self.seen = {}          # addr -> [kind, state, rssi, stable, last_ticks]
        self.n_ble = 0
        self._all = set()
        self.top = 0
        self.ble = None
        self.err = None
        ctx.speech.clear()
        try:
            import bluetooth
            self.ble = bluetooth.BLE()
            self.ble.active(True)
            self.ble.irq(self._irq)
            self.ble.gap_scan(0, 30000, 30000)      # 0 = until stopped
        except Exception as e:
            print("[followers] bluetooth failed:", e)
            self.err = str(e)
            self._stop()

    def exit(self):
        self._stop()

    def _stop(self):
        if self.ble:
            try:
                self.ble.gap_scan(None)
            except Exception:
                pass
            try:
                self.ble.active(False)
            except Exception:
                pass
            self.ble = None
        self.seen = {}
        self._all = set()

    def _irq(self, event, data):
        if event != _IRQ_SCAN_RESULT:
            return
        addr = bytes(data[1])
        if len(self._all) < 300:
            self._all.add(addr)
        rssi = data[3]
        s = self.seen.get(addr)
        if s is None:
            c = trackers.classify(data[4])
            if c is None or len(self.seen) >= 40:
                return
            if C.TRACKER_DEBUG:
                print("[trk] new %-8s %-4s %4d adv=%s" % (c[0], c[1], rssi, trackers.hexs(data[4], 31)))
            self.seen[addr] = [c[0], c[1], rssi, c[2], 0]
            s = self.seen[addr]
        s[2] = rssi
        s[4] = self.ctx.now()

    protect = (10, 64)

    def event(self, ev):
        n = len(self.seen)
        if ev == 'hold':
            self.ctx.pop()
        elif ev == 'down' and self.top + ROWS < n:
            self.top += 1
        elif ev == 'up' and self.top > 0:
            self.top -= 1

    def draw(self, r, now):
        r.text("raw trackers", 0, 0)
        if self.err:
            r.text("no bluetooth:", 0, 20)
            r.text(self.err[:16], 0, 30)
            return
        rows = sorted(self.seen.values(), key=lambda s: -s[2])
        r.text("%d" % len(rows), 128 - 8 * len(str(len(rows))), 0)
        if not rows:
            r.text("listening for", 0, 20)
            r.text("little things...", 0, 30)
            r.text("ble seen: %d" % len(self._all), 0, 50)
            return
        y = 10
        for kind, state, rssi, stable, last in rows[self.top:self.top + ROWS]:
            age = ticks_diff(now, last) // 1000
            r.text(trackers.LABEL[kind], 0, y)
            r.text(state, 67, y)
            r.text("%d" % rssi, 104, y)
            r.text("  %s" % (trackers.hexs(stable, 3) or "-"), 0, y + 9)
            r.text("%2ds" % min(age, 99), 96, y + 9)
            y += 18
