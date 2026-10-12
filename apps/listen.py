# listen -- the ghost holds still and listens to the radio around it.
#
# 1. WiFi scan.  network.WLAN.scan() blocks for ~2 s, so a "listening"
#    frame is put on screen first and stays there while it runs.
# 2. Bluetooth scan.  gap_scan() is non-blocking: results arrive through
#    an IRQ while the screen keeps animating.
# 3. Everything is hashed, fed to the ghost, and the raw addresses dropped.
#    SSIDs are shown on screen but never saved.
#
# up/down: flip result pages   click: listen again   hold: back

import random
from time import ticks_diff
from apps import App as Screen
import phrases
import sprites
import trackers
import config as C

_IRQ_SCAN_RESULT = 5
_IRQ_SCAN_DONE = 6
_PER_PAGE = 3


def _ssid(raw):
    try:
        s = raw.decode()
    except Exception:
        s = ''
    s = ''.join(c for c in s if 32 <= ord(c) < 127)
    return s or '(hidden)'


class App(Screen):
    def enter(self, ctx):
        super().enter(ctx)
        self.ble = None
        self.start()

    def exit(self):
        self._stop_ble()

    # ------------------------------------------------------------ scanning
    def start(self):
        ctx = self.ctx
        now = ctx.now()
        self.state = 'intro'
        self.t0 = now
        self.drawn = False
        self.loud = []          # [(ssid, rssi, nickname, is_new)] strongest first
        self.wifi_ids = []
        self.ble_seen = {}
        self.trk = {}           # addr -> [kind, state, rssi, stable] (RAM, this scan)
        self.trackers = []      # after digest: [(kind, state, rssi, id, stable)]
        self.ble_done = False
        self.result = None
        self.page = 0
        self.deaf = 0
        p = ctx.puppet
        p.set_bounds(52, 4, 52, 4, snap=True)
        p.express('stare', 60000, now)
        ctx.say(phrases.pick('listening'))

    def _scan_wifi(self):
        if not C.WIFI_ENABLED:
            self.deaf += 1
            return
        try:
            import network
            w = network.WLAN(network.STA_IF)
            w.active(True)
            res = w.scan()
            w.active(False)
        except Exception as e:
            print("[listen] wifi failed:", e)
            self.deaf += 1
            return
        fam = self.ctx.mem.state['familiars']
        seen = {}
        for r in res:
            h = self.ctx.mem.hash_id(r[1])      # r[1] = BSSID, never kept
            if h not in seen or r[3] > seen[h][1]:
                seen[h] = (_ssid(r[0]), r[3], h not in fam)
        self.wifi_ids = list(seen)
        loud = sorted(seen.items(), key=lambda kv: -kv[1][1])[:12]
        self.loud = [(v[0], v[1], phrases.nickname(h), v[2]) for h, v in loud]

    def _start_ble(self):
        if not C.BLE_ENABLED:
            self.deaf += 1
            return False
        try:
            import bluetooth
            self.ble = bluetooth.BLE()
            self.ble.active(True)
            self.ble.irq(self._irq)
            self.ble.gap_scan(C.BLE_SCAN_MS, 30000, 30000)
            return True
        except Exception as e:
            print("[listen] bluetooth failed:", e)
            self.deaf += 1
            self._stop_ble()
            return False

    def _irq(self, event, data):
        if event == _IRQ_SCAN_RESULT:
            addr = bytes(data[1])
            rssi = data[3]
            t = self.trk.get(addr)
            if t is None:
                c = trackers.classify(data[4])
                if c and len(self.trk) < 40:
                    self.trk[addr] = [c[0], c[1], rssi, c[2]]
            elif rssi > t[2]:
                t[2] = rssi
            prev = self.ble_seen.get(addr)
            if prev is None:
                if len(self.ble_seen) < C.BLE_MAX:
                    self.ble_seen[addr] = rssi
            elif rssi > prev:
                self.ble_seen[addr] = rssi
        elif event == _IRQ_SCAN_DONE:
            self.ble_done = True

    def _stop_ble(self):
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

    def _digest(self, now):
        ctx = self.ctx
        mem = ctx.mem
        ble_ids = [mem.hash_id(a) for a in self.ble_seen]
        found = []
        for a, (kind, state, rssi, stable) in self.trk.items():
            found.append((kind, state, rssi, mem.hash_id(a), stable))
        found.sort(key=lambda t: -t[2])
        self.trackers = found
        if C.TRACKER_DEBUG:
            for kind, state, rssi, h, stable in found:
                print("[trk] %-8s %-4s %4d id=%s data=%s" % (kind, state, rssi, h, trackers.hexs(stable)))
        self.ble_seen = {}                      # raw MACs gone
        self.trk = {}
        self._stop_ble()
        r = ctx.ghost.feed(self.wifi_ids, ble_ids)
        self.result = r
        p = ctx.puppet
        p.set_bounds(100, 6, 104, 20, snap=True)
        if self.deaf >= 2:
            ctx.say(phrases.pick('deaf'))
            p.express('nervous', 2500, now)
            return
        kind = r['kind']
        ctx.say(phrases.pick('heard_' + kind, n=r['ate']))
        p.express({'crowd': 'nervous', 'feast': 'excited', 'snack': 'excited',
                   'silence': 'nervous'}.get(kind, 'stare'), 2500, now)

    def update(self, now):
        t = ticks_diff(now, self.t0)
        if self.state == 'intro':
            if t > 900:
                self.state = 'wifi'
                self.drawn = False
        elif self.state == 'wifi':
            if self.drawn:                      # the frame is on screen; now block
                self._scan_wifi()
                self.state = 'ble'
                self.t0 = self.ctx.now()
                if not self._start_ble():
                    self.ble_done = True
        elif self.state == 'ble':
            if self.ble_done or t > C.BLE_SCAN_MS + 1500:
                self.state = 'results'
                self._digest(now)

    # ------------------------------------------------------------ input
    @property
    def wifi_pages(self):
        return (len(self.loud) + _PER_PAGE - 1) // _PER_PAGE

    @property
    def pages(self):
        return 1 + self.wifi_pages + (len(self.trackers) + _PER_PAGE - 1) // _PER_PAGE

    def event(self, ev):
        if self.state != 'results':
            if ev == 'hold':
                self.ctx.pop()
            return
        if ev == 'down' and self.page < self.pages - 1:
            self.page += 1
        elif ev == 'up' and self.page > 0:
            self.page -= 1
        elif ev == 'click':
            self.start()
        elif ev == 'hold':
            self.ctx.pop()

    @property
    def protect(self):
        if self.state != 'results':
            return None
        return (0, 64) if self.page else (10, 40)

    @property
    def allow_screen_off(self):
        return self.state == 'results'

    # ------------------------------------------------------------ drawing
    def draw(self, r, now):
        ctx = self.ctx
        lvl = ctx.ghost.glitch
        if self.state == 'results':
            if self.page > self.wifi_pages:
                self._draw_trackers(r)
            elif self.page:
                self._draw_list(r)
            else:
                self._draw_summary(r, now, lvl)
            return

        p = ctx.puppet
        cx = int(p.x) + 12
        cy = int(p.y) + 11
        if self.state == 'wifi':
            self.drawn = True
            r.o.ellipse(cx, cy, 22, 22, 1)
            r.o.ellipse(cx, cy, 34, 30, 1)
            p.draw(r, now, lvl)
            r.center("listening...", 47)
            r.center("(the walls)", 56)
            return

        if self.state == 'ble':
            # rings drifting outward, and a live count
            t = ticks_diff(now, self.t0)
            for k in range(3):
                rad = 14 + ((t // 30 + k * 18) % 54)
                r.o.ellipse(cx, cy, rad, rad, 1)
            r.o.fill_rect(cx - 13, cy - 12, 26, 24, 0)
            p.draw(r, now, lvl)
            r.o.fill_rect(0, 46, 128, 18, 0)
            r.text("wifi %d" % len(self.wifi_ids), 0, 47)
            r.text("near %d" % len(self.ble_seen), 0, 56)
            dots = '.' * (1 + (t // 300) % 3)
            r.text(dots, 80, 56)
            if random.random() < 0.15:
                r.glyph(random.choice(sprites.NOISE), random.randint(0, 15) * 8, 47)
            return

        p.draw(r, now, lvl)
        ctx.speech.draw(r, 47, now, lvl)

    def _draw_summary(self, r, now, lvl):
        res = self.result
        r.text("i heard:", 0, 0)
        if self.trackers:
            r.text("%dtrk" % len(self.trackers), 72, 0)
        r.text("wifi %3d +%d" % (res['wifi'], res['wifi_new']), 0, 12)
        r.text("near %3d +%d" % (res['ble'], res['ble_new']), 0, 22)
        r.text("ate  %3d" % res['ate'], 0, 32)
        if self.pages > 1:
            r.text('v', 88, 32)
        self.ctx.puppet.draw(r, now, lvl)
        self.ctx.speech.draw(r, 47, now, lvl)

    def _draw_list(self, r):
        r.text("loudest", 0, 0)
        r.text("%d/%d" % (self.page, self.pages - 1), 96, 0)
        start = (self.page - 1) * _PER_PAGE
        y = 11
        for ssid, rssi, nick, new in self.loud[start:start + _PER_PAGE]:
            r.text(ssid[:11], 0, y)
            r.text("%d" % rssi, 96, y)
            r.text(("* " if new else "~ ") + nick, 0, y + 9)
            y += 18

    def _draw_trackers(self, r):
        # debug view: what the tracker classifier saw in this scan
        r.text("trackers", 0, 0)
        r.text("%d/%d" % (self.page, self.pages - 1), 96, 0)
        start = (self.page - 1 - self.wifi_pages) * _PER_PAGE
        y = 11
        for kind, state, rssi, h, stable in self.trackers[start:start + _PER_PAGE]:
            r.text(trackers.LABEL[kind], 0, y)
            r.text(state, 67, y)
            r.text("%d" % rssi, 104, y)
            r.text("  " + (trackers.hexs(stable, 4) or "-"), 0, y + 9)
            y += 18
