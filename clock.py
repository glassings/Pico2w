# clock.py -- the ghost learns the real time from home WiFi + NTP.
#
# Everything here is a small state machine polled once per loop, so the
# UI never stalls on WiFi:  idle -> connecting -> asking -> idle.
#
# The clock only counts as "known" after a sync in THIS power-on.  (Thonny
# sets the RTC too when it connects, but to your PC's local time, not UTC,
# so the RTC alone can't be trusted.)
#
# Times are kept as Unix seconds (UTC, since 1970) whatever the firmware
# epoch is.  localtime() is the only place that turns UTC into local time.

import time
from time import ticks_ms, ticks_diff, ticks_add
import config as C

_EPOCH_OFFSET = 946684800 if time.gmtime(0)[0] == 2000 else 0
_NTP_DELTA = 2208988800                 # 1900 -> 1970

DAYS = ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')
MONTHS = ('jan', 'feb', 'mar', 'apr', 'may', 'jun',
          'jul', 'aug', 'sep', 'oct', 'nov', 'dec')

# name -> (standard UTC offset in hours, follows US daylight saving)
ZONES = {
    'US_EASTERN': (-5, True), 'US_CENTRAL': (-6, True),
    'US_MOUNTAIN': (-7, True), 'US_PACIFIC': (-8, True),
    'US_ARIZONA': (-7, False), 'UTC': (0, False),
}


# ------------------------------------------------------------ calendar maths
# Pure integer arithmetic (Howard Hinnant's civil-date algorithms), so the
# result never depends on the firmware's epoch or RTC.

def days_from_civil(y, m, d):
    y -= m <= 2
    era = (y if y >= 0 else y - 399) // 400
    yoe = y - era * 400
    doy = (153 * (m + (-3 if m > 2 else 9)) + 2) // 5 + d - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    return era * 146097 + doe - 719468


def civil_from_days(z):
    z += 719468
    era = (z if z >= 0 else z - 146096) // 146097
    doe = z - era * 146097
    yoe = (doe - doe // 1460 + doe // 36524 - doe // 146096) // 365
    y = yoe + era * 400
    doy = doe - (365 * yoe + yoe // 4 - yoe // 100)
    mp = (5 * doy + 2) // 153
    d = doy - (153 * mp + 2) // 5 + 1
    m = mp + (3 if mp < 10 else -9)
    return y + (m <= 2), m, d


def _weekday(days):
    return (days + 3) % 7               # 0 = Monday (1970-01-01 was a Thursday)


def _nth_sunday(y, m, n):
    """Day number of the n-th Sunday of a month."""
    first = days_from_civil(y, m, 1)
    to_sun = (6 - _weekday(first)) % 7
    return first + to_sun + 7 * (n - 1)


def is_dst(utc, std=None):
    """US rules: from the 2nd Sunday of March, 2:00 local standard time,
    to the 1st Sunday of November, 2:00 local daylight time."""
    if std is None:
        std = ZONES[C.TZ][0]
    y = civil_from_days(utc // 86400)[0]
    start = _nth_sunday(y, 3, 2) * 86400 + (2 - std) * 3600
    end = _nth_sunday(y, 11, 1) * 86400 + (1 - std) * 3600
    return start <= utc < end


def localtime(utc=None):
    """UTC unix seconds (default: now) -> (year, month, day, hour, minute,
    second, weekday 0=Mon, is_dst).  None if the clock isn't known."""
    if utc is None:
        utc = now_utc()
        if utc is None:
            return None
    std, uses_dst = ZONES[C.TZ]
    dst = uses_dst and is_dst(utc, std)
    t = utc + (std + (1 if dst else 0)) * 3600
    days = t // 86400
    s = t % 86400
    y, m, d = civil_from_days(days)
    return (y, m, d, s // 3600, s // 60 % 60, s % 60, _weekday(days), dst)


def fmt_time(lt, seconds=False):
    h = lt[3]
    if not C.CLOCK_24H:
        h = h % 12 or 12
    if seconds:
        return "%d:%02d:%02d" % (h, lt[4], lt[5])
    return "%d:%02d" % (h, lt[4])


def ampm(lt):
    return '' if C.CLOCK_24H else ('am' if lt[3] < 12 else 'pm')


def fmt_date(lt):
    return "%s %s %d" % (DAYS[lt[6]], MONTHS[lt[1] - 1], lt[2])


def fmt_when(utc):
    """For letters: 'today 9:41', 'last night 2:14', 'tue 18:03'."""
    lt = localtime(utc)
    nowl = localtime()
    if lt is None or nowl is None:
        return None
    t = fmt_time(lt) + ampm(lt)
    ago = days_from_civil(*nowl[:3]) - days_from_civil(*lt[:3])
    night = lt[3] < 5 or lt[3] >= 20
    if ago == 0:
        return ("last night " if lt[3] < 5 and nowl[3] >= 5 else "today ") + t
    if ago == 1:
        return ("last night " if night else "yesterday ") + t
    if ago < 7:
        return DAYS[lt[6]] + " " + t
    return "%s %d" % (MONTHS[lt[1] - 1], lt[2])


def selftest():
    """Run in the REPL:  import clock; clock.selftest()"""
    cases = (
        ((2026, 11, 1, 6, 59), (1, 59, True)),
        ((2026, 11, 1, 7, 0), (1, 0, False)),
        ((2027, 3, 14, 7, 59), (1, 59, False)),
        ((2027, 3, 14, 8, 0), (3, 0, True)),
    )
    bad = 0
    for (y, mo, d, h, mi), (eh, em, edst) in cases:
        utc = days_from_civil(y, mo, d) * 86400 + h * 3600 + mi * 60
        std = ZONES['US_CENTRAL'][0]
        dst = is_dst(utc, std)
        t = utc + (std + (1 if dst else 0)) * 3600
        got = (t % 86400 // 3600, t % 3600 // 60, dst)
        ok = got == (eh, em, edst)
        bad += not ok
        print("%s %04d-%02d-%02d %02d:%02d UTC -> %02d:%02d %s" % (
            "ok  " if ok else "FAIL", y, mo, d, h, mi, got[0], got[1],
            "CDT" if got[2] else "CST"))
    print("all passed" if not bad else "%d FAILED" % bad)
    return not bad


# ------------------------------------------------------------ the RTC

_known = False


def now_utc():
    """Unix seconds (UTC), or None if we haven't synced this power-on."""
    if not _known:
        return None
    return int(time.time()) + _EPOCH_OFFSET


def _set_rtc(utc):
    import machine
    tm = time.gmtime(utc - _EPOCH_OFFSET)
    machine.RTC().datetime((tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0))


# ------------------------------------------------------------ syncing

def _load_secrets():
    try:
        import secrets
        return secrets.WIFI_SSID, secrets.WIFI_PASSWORD
    except (ImportError, AttributeError):
        return None, None


class Clock:
    """Owns the STA interface while syncing, and gives it back afterwards."""

    def __init__(self):
        self.state = 'idle'
        self.why = ''               # last failure, for the clock screen
        self.synced_at = None       # ticks_ms of last good sync
        self.next_try = ticks_ms()  # first attempt: right away
        self.just_synced = False    # set once after each sync, for callers
        self._wlan = None
        self._sock = None
        self._t0 = 0
        self._sent = 0

    @property
    def known(self):
        return _known

    @property
    def busy(self):
        return self.state != 'idle'

    def ago_s(self, now):
        return None if self.synced_at is None else ticks_diff(now, self.synced_at) // 1000

    def request(self, now):
        """Sync as soon as the radio is free."""
        self.next_try = now

    def abort(self):
        """Something else needs the radio right now (a WiFi scan)."""
        if self.busy:
            self._finish(False, 'interrupted', ticks_ms(), retry_s=60)

    def poll(self, now, radio_free=True):
        st = self.state
        if st == 'idle':
            if radio_free and C.CLOCK_ENABLED and ticks_diff(now, self.next_try) >= 0:
                self._start(now)
            return
        if ticks_diff(now, self._t0) > C.CLOCK_SYNC_BUDGET_MS:
            self._finish(False, 'no answer' if st == 'asking' else 'no wifi', now)
            return
        try:
            if st == 'connecting':
                if self._wlan.isconnected():
                    self._ask()
                elif self._wlan.status() < 0:           # wrong password, no AP...
                    self._finish(False, 'no wifi', now)
            elif st == 'asking':
                self._listen(now)
        except Exception as e:
            print("[clock] sync error:", e)
            self._finish(False, 'error', now)

    def _start(self, now):
        ssid, pw = _load_secrets()
        if not ssid:
            self.why = 'no secrets.py'
            self.next_try = ticks_add(now, 3600 * 1000)
            return
        try:
            import network
            self._wlan = network.WLAN(network.STA_IF)
            self._wlan.active(True)
            self._wlan.connect(ssid, pw)
        except Exception as e:
            print("[clock] wifi error:", e)
            self._finish(False, 'no wifi', now)
            return
        self.state = 'connecting'
        self._t0 = now
        print("[clock] syncing...")

    def _ask(self):
        import socket
        addr = socket.getaddrinfo(C.NTP_HOST, 123)[0][-1]
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setblocking(False)
        q = bytearray(48)
        q[0] = 0x1B                     # SNTP v3, client
        s.sendto(q, addr)
        self._sock = s
        self.state = 'asking'

    def _listen(self, now):
        try:
            msg = self._sock.recv(48)
        except OSError:
            return                      # nothing yet (EAGAIN)
        if not msg or len(msg) < 48:
            return
        secs = int.from_bytes(msg[40:44], 'big')
        if secs < 3913056000:           # before 2024: the 2036 wrap
            secs += 0x100000000
        global _known
        _set_rtc(secs - _NTP_DELTA)
        _known = True
        self._finish(True, '', now)

    def _finish(self, ok, why, now, retry_s=None):
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
        if self._wlan:
            try:
                self._wlan.disconnect()
                self._wlan.active(False)
            except Exception:
                pass
            self._wlan = None
        self.state = 'idle'
        self.why = why
        if ok:
            self.synced_at = now
            self.just_synced = True
            self.next_try = ticks_add(now, C.CLOCK_RESYNC_H * 3600 * 1000)
            print("[clock] synced:", fmt_date(localtime()), fmt_time(localtime(), True))
        else:
            if retry_s is None:
                retry_s = C.CLOCK_RETRY_MIN * 60
            self.next_try = ticks_add(now, retry_s * 1000)
            print("[clock] sync failed:", why)


# ------------------------------------------------------------ rhythms

def daypart(lt):
    if lt is None:
        return None
    h = lt[3]
    if h < 5:
        return 'night'
    if h < 11:
        return 'morning'
    if h < 18:
        return 'day'
    return 'evening' if h < 23 else 'night'


def in_quiet(lt):
    if lt is None:
        return False
    a, b, h = C.QUIET_START, C.QUIET_END, lt[3]
    return (h >= a or h < b) if a > b else (a <= h < b)


def day_number(lt):
    return days_from_civil(lt[0], lt[1], lt[2])


def behave(ctx, now):
    """Once a second: everything the real time changes about the ghost."""
    import phrases
    clk = ctx.clock
    g = ctx.ghost
    s = ctx.mem.state
    utc = now_utc()

    if clk.just_synced:
        clk.just_synced = False
        s['last_real'] = utc
        if not s['first_real']:
            # the first boot was roughly this long ago
            s['first_real'] = utc - int(s['alive_s'])
        ctx.mem.touch(urgent=True)
        if ctx.booted and not ctx.said_synced:
            ctx.said_synced = True
            ctx.say(phrases.pick('clock_synced'), queue=True)

    lt = localtime(utc) if utc else None
    g.daypart = daypart(lt)
    quiet = in_quiet(lt)
    if quiet != g.quiet:
        g.quiet = quiet
        ctx.oled.contrast(C.QUIET_CONTRAST if quiet else C.OLED_CONTRAST)
    if lt is None or not ctx.awake or not ctx.booted:
        return
    today = day_number(lt)

    # first time it's awake after quiet hours end
    if (not quiet and not g.napping and C.QUIET_END <= lt[3] < 12
            and s['morning_day'] != today):
        s['morning_day'] = today
        ctx.mem.touch()
        ctx.say(phrases.pick('clock_morning'), queue=True)

    # its minute
    if (lt[3], lt[4]) == C.WITCHING and s['witch_day'] != today:
        s['witch_day'] = today
        ctx.mem.touch()
        g.last_input = now                  # it is very much awake now
        g.napping = False
        ctx.speech.clear()
        ctx.say(phrases.pick('clock_witching'))
        ctx.puppet.express('stare', 4000, now)
        ctx.r.burst(40)
        import hw
        ctx.chirp(hw.WHISPER)
