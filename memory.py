# memory.py -- what the ghost remembers between power-offs.
#
# Flash wear: the state is only written when something important happened
# (and at least SAVE_MIN_GAP_S since the last write), or as a routine
# checkpoint every SAVE_INTERVAL_S.  Never every loop.
#
# Privacy: radio identifiers are only ever stored as salted hashes (hash_id).

import json
import os
from time import ticks_ms, ticks_diff
import config as C

try:
    import hashlib
except ImportError:
    hashlib = None
from binascii import hexlify

VERSION = 1


def _fresh():
    return {
        'v': VERSION,
        'salt': hexlify(os.urandom(8)).decode(),
        'alive_s': 0,           # total powered-on seconds ("days alive")
        'boots': 0,
        'last_session_s': 0,    # how long it was on last time
        'last_real': 0,         # real UTC time at last save (0 = never known)
        'first_real': 0,        # real UTC time of (roughly) the first boot
        'morning_day': 0,       # day number of the last "good morning"
        'witch_day': 0,         # day number of the last witching minute
        'fed': 0,               # new signals eaten, all time
        'presences': 0,         # BLE presences sensed, all time
        'familiars': {},        # hash -> [nickname, times_seen]
        'mood': {'hunger': 40.0, 'restless': 10.0, 'content': 50.0},
        'timer_s': 300,         # last countdown you set
        'halloween': 'auto',    # auto / on / off
        'hw_over': 0,           # year we last said 'halloween_over'
        'knocks': [0, 0],       # [day number, knocks that night]
        'tg_wpm': 8,            # telegraph speed: 5..20 or 'auto'
    }


class Memory:
    def __init__(self, path=C.STATE_FILE):
        self.path = path
        self.tmp = path + '.tmp'
        self.state, self.is_new = self._load()
        self.dirty = self.is_new
        self.urgent = self.is_new
        self.last_save = ticks_ms()
        self._salt = self.state['salt'].encode()

    def _load(self):
        loaded = None
        # the .tmp copy only matters if power died mid-save
        for p in (self.path, self.tmp):
            try:
                with open(p) as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    break
                loaded = None
            except (OSError, ValueError):
                loaded = None
        state = _fresh()
        if loaded is None:
            return state, True
        for k in state:
            if k in loaded:
                if k == 'mood':
                    state[k].update(loaded[k])
                else:
                    state[k] = loaded[k]
        return state, False

    def touch(self, urgent=False):
        """Note that the state changed.  urgent=True for significant events."""
        self.dirty = True
        if urgent:
            self.urgent = True

    def maybe_save(self, now):
        if not self.dirty:
            return
        age = ticks_diff(now, self.last_save)
        if age >= C.SAVE_INTERVAL_S * 1000 or (self.urgent and age >= C.SAVE_MIN_GAP_S * 1000):
            self.save(now)

    def save(self, now=None):
        try:
            with open(self.tmp, 'w') as f:
                json.dump(self.state, f)
            try:
                os.rename(self.tmp, self.path)
            except OSError:
                os.remove(self.path)
                os.rename(self.tmp, self.path)
            print("[mem] saved")
        except OSError as e:
            print("[mem] save failed:", e)
        self.dirty = False
        self.urgent = False
        self.last_save = ticks_ms() if now is None else now

    def hash_id(self, raw):
        """Salted, truncated hash of a MAC/BSSID.  The raw value is never stored."""
        if isinstance(raw, str):
            raw = raw.encode()
        if hashlib:
            return hexlify(hashlib.sha256(self._salt + raw).digest()[:6]).decode()
        # fallback: FNV-1a, 48 bits
        h = 0xcbf29ce484222325
        for b in self._salt + raw:
            h = ((h ^ b) * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF
        return '%012x' % (h >> 16)
