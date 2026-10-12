# render.py -- drawing, glitches, and the ghost's voice.
#
# Rule: glitches are applied in one pass AFTER a screen is drawn
# (Renderer.glitch_pass), and screens name a `protect` band of rows that
# tearing and noise must not touch.  Useful numbers live in that band, so
# they can flicker (a hardware invert for a frame) but never become wrong.

import random
import os
from time import ticks_ms, ticks_diff, ticks_add
import sprites

W = 128
H = 64


def _chance(p):
    return random.random() < p


class Renderer:
    def __init__(self, oled):
        self.o = oled
        self.buf = oled.buffer      # SSD1306: 8 pages x 128 bytes, MONO_VLSB
        self._burst = 0
        self._kind = 0
        self._inverted = False

    # ------------------------------------------------------------ basics
    def clear(self):
        self.o.fill(0)

    def text(self, s, x, y, c=1):
        self.o.text(s, x, y, c)

    def center(self, s, y, c=1):
        self.o.text(s, (W - len(s) * 8) // 2, y, c)

    def sprite(self, spr, x, y):
        self.o.blit(spr.fb, int(x), int(y), 0)      # dark pixels transparent

    def glyph(self, spr, x, y):
        self.o.blit(spr.fb, int(x), int(y))         # opaque

    def static(self, density=2):
        """Fill the screen with TV snow.  density 1=50%, 2=25%, 3=12%..."""
        b = self.buf
        n = len(b)
        noise = os.urandom(n)
        if density <= 1:
            b[:] = noise
            return
        more = os.urandom(n)
        for i in range(n):
            b[i] = noise[i] & more[i]
        for _ in range(density - 2):
            more = os.urandom(n)
            for i in range(n):
                b[i] &= more[i]

    # ------------------------------------------------------------ glitches
    def _tear(self, page, dx):
        a = page * W
        row = bytes(self.buf[a:a + W])
        self.buf[a:a + W] = row[-dx:] + row[:-dx]

    def glitch_pass(self, level, protect=None):
        """level 0..1.  protect=(y0, y1) rows that must stay readable."""
        if self._inverted:
            self.o.invert(0)
            self._inverted = False
        if self._burst <= 0:
            if not _chance(0.01 + 0.12 * level * level):
                return
            self._burst = random.randint(1, 2 + int(level * 4))
            self._kind = random.randint(0, 9)
        self._burst -= 1

        # pages (8-row bands) we are allowed to damage
        free = []
        for p in range(8):
            if protect is None or p * 8 >= protect[1] or p * 8 + 8 <= protect[0]:
                free.append(p)

        k = self._kind
        if k <= 4:                          # horizontal tearing
            if free:
                for _ in range(random.randint(1, 1 + int(level * 3))):
                    self._tear(random.choice(free), random.randint(2, 6 + int(level * 20)))
        elif k <= 6:                        # scanline flicker
            for _ in range(random.randint(1, 4)):
                if free:
                    p = random.choice(free)
                    y = p * 8 + random.randint(0, 7)
                    self.o.hline(0, y, W, 0)
                    if _chance(0.3):
                        self.o.hline(random.randint(0, 64), y, random.randint(8, 64), 1)
        elif k <= 8:                        # snow specks
            for _ in range(int(10 + level * 50)):
                if free:
                    p = random.choice(free)
                    self.o.pixel(random.randint(0, W - 1), p * 8 + random.randint(0, 7), 1)
        elif _chance(0.5 + level * 0.5):    # inverted flash (still readable)
            self.o.invert(1)
            self._inverted = True
            self._burst = 0


# ---------------------------------------------------------------- speech

def parse(phrase):
    """'i [ate>met] you' -> ('i ate you', 'i met you')"""
    first = ''
    final = ''
    i = 0
    n = len(phrase)
    while i < n:
        c = phrase[i]
        j = phrase.find(']', i) if c == '[' else -1
        k = phrase.find('>', i, j) if j > 0 else -1
        if k > 0:
            first += phrase[i + 1:k]
            final += phrase[k + 1:j]
            i = j + 1
        else:
            first += c
            final += c
            i += 1
    return first.strip(), final.strip()


def wrap(s, width=16, lines=2):
    """-> [(start_index, text), ...] broken at spaces."""
    out = []
    start = 0
    n = len(s)
    while start < n and len(out) < lines:
        if n - start <= width:
            out.append((start, s[start:]))
            break
        cut = s.rfind(' ', start, start + width + 1)
        if cut <= start:
            cut = start + width
            nxt = cut
        else:
            nxt = cut + 1
        out.append((start, s[start:cut]))
        start = nxt
    return out


_LEET = {'a': '4', 'e': '3', 'i': '1', 'o': '0', 's': '5', 't': '7', 'l': '1', 'g': '9'}
_CHAR_MS = 38       # typewriter speed


class Speech:
    """One utterance at a time: typed out, maybe corrupted, maybe retracted."""

    def __init__(self):
        self.text = None

    @property
    def busy(self):
        return self.text is not None

    def say(self, phrase, now, level=0.0, hold_ms=0):
        a, b = parse(phrase)
        self.text = a
        self.final = b
        self.t0 = now
        self.instant = False
        self.bad = {}           # index -> [expire_ticks, replacement or None]
        self.dying = None
        typed = _CHAR_MS * len(a)
        self.swap = ticks_add(now, typed + 900) if a != b else None
        extra = typed + 900 if a != b else 0
        self.end = ticks_add(now, extra + max(hold_ms, typed + 1600 + 45 * len(b)))
        if _chance(0.12 + level * 0.6):
            self._corrupt_word(now)

    def clear(self):
        self.text = None

    def _corrupt_word(self, now):
        s = self.text
        words = []
        i = 0
        for w in s.split(' '):
            if len(w) >= 3:
                words.append((i, w))
            i += len(w) + 1
        if not words:
            return
        i, w = random.choice(words)
        for j in range(len(w)):
            if _chance(0.45):
                ch = w[j]
                rep = _LEET.get(ch) if _chance(0.5) else None
                # stays wrong until a little after it is typed, then corrects
                t = ticks_add(now, _CHAR_MS * (i + j) + random.randint(250, 900))
                self.bad[i + j] = [t, rep]

    def update(self, now):
        if self.text is None:
            return
        if self.swap is not None and ticks_diff(now, self.swap) >= 0:
            self.text = self.final
            self.swap = None
            self.instant = True
            self.bad = {}
        if self.dying is None and ticks_diff(now, self.end) >= 0:
            # dissolve into noise instead of just vanishing
            self.dying = now
            t = ticks_add(now, 220)
            for i in range(len(self.text)):
                if _chance(0.7):
                    self.bad[i] = [t, None]
        if self.dying is not None and ticks_diff(now, self.dying) > 240:
            self.text = None
            return
        for i in list(self.bad):
            if ticks_diff(now, self.bad[i][0]) >= 0:
                del self.bad[i]

    def draw(self, r, y, now, level=0.0):
        s = self.text
        if s is None:
            return
        shown = len(s) if self.instant else ticks_diff(now, self.t0) // _CHAR_MS
        if level > 0.3 and _chance(level * 0.04) and shown > 0:
            # a letter blinks into a block for a frame or two
            self.bad[random.randint(0, min(shown, len(s)) - 1)] = [ticks_add(now, 90), None]
        ly = y
        for start, line in wrap(s):
            vis = shown - start
            if vis <= 0:
                break
            if vis < len(line):
                line = line[:vis]
            r.text(line, 0, ly)
            for i in self.bad:
                k = i - start
                if 0 <= k < len(line):
                    x = k * 8
                    r.o.fill_rect(x, ly, 8, 8, 0)
                    rep = self.bad[i][1]
                    if rep:
                        r.text(rep, x, ly)
                    else:
                        r.glyph(random.choice(sprites.NOISE), x, ly)
            ly += 9


# ---------------------------------------------------------------- the body

_BOB = (0, 0, 1, 1, 1, 0, 0, -1, -1, -1)


class Puppet:
    """The ghost's on-screen body: drifting, blinking, napping, staring,
    vanishing and stuttering.  Screens decide WHEN; this decides HOW."""

    def __init__(self):
        now = ticks_ms()
        self.x = 52.0
        self.y = 12.0
        self.tx = self.x
        self.ty = self.y
        self.bounds = (0, 0, W - 24, 22)
        self.expr = None
        self.expr_until = now
        self.blink_at = ticks_add(now, 2500)
        self.blink_until = now
        self.next_wander = now
        self.vanish_t = None
        self.stutter = 0
        self.ghost_xy = None
        self.asleep = False
        self.hidden = False

    def set_bounds(self, x0, y0, x1, y1, snap=False):
        self.bounds = (x0, y0, x1, y1)
        self.tx = min(max(self.tx, x0), x1)
        self.ty = min(max(self.ty, y0), y1)
        if snap:
            self.x = self.tx
            self.y = self.ty

    def express(self, name, ms, now):
        self.expr = name
        self.expr_until = ticks_add(now, ms)

    def go(self, x, y):
        x0, y0, x1, y1 = self.bounds
        self.tx = min(max(x, x0), x1)
        self.ty = min(max(y, y0), y1)

    def nudge(self, dx, dy):
        self.go(self.tx + dx, self.ty + dy)

    def vanish(self, now):
        if self.vanish_t is None:
            self.vanish_t = now

    @property
    def vanishing(self):
        return self.vanish_t is not None

    def update(self, now, level):
        x0, y0, x1, y1 = self.bounds
        if self.expr and ticks_diff(now, self.expr_until) >= 0:
            self.expr = None

        if ticks_diff(now, self.blink_at) >= 0:
            self.blink_until = ticks_add(now, 130)
            self.blink_at = ticks_add(now, random.randint(1800, 6000))
            if _chance(0.15):       # double blink
                self.blink_at = ticks_add(now, 300)

        if self.asleep:
            self.go((x0 + x1) // 2, y1)
        elif ticks_diff(now, self.next_wander) >= 0 and self.expr != 'stare':
            self.go(random.randint(x0, x1), random.randint(y0, y1))
            self.next_wander = ticks_add(now, random.randint(2500, int(9000 - 6000 * level)))

        k = 0.025 if self.asleep else 0.04 + 0.08 * level
        self.x += (self.tx - self.x) * k
        self.y += (self.ty - self.y) * k

        if self.vanish_t is not None:
            t = ticks_diff(now, self.vanish_t)
            if 300 < t < 1100:
                self.hidden = True
            if t >= 1100 and self.hidden:
                # reappear somewhere else, instantly
                self.hidden = False
                self.x = self.tx = random.randint(x0, x1)
                self.y = self.ty = random.randint(y0, y1)
            if t >= 1400:
                self.vanish_t = None

        if self.stutter > 0:
            self.stutter -= 1
        elif _chance(0.004 + 0.05 * level * level):
            self.stutter = random.randint(2, 5)
            self.ghost_xy = (self.x + random.choice((-5, -3, 3, 5)), self.y + random.randint(-1, 1))

    def _frame(self, now):
        if self.asleep:
            return sprites.SLEEP
        if ticks_diff(now, self.blink_until) < 0 and self.expr != 'excited':
            return sprites.BLINK
        if self.expr:
            return sprites.EXPR[self.expr]
        return sprites.IDLE[(now // 380) & 1]

    def draw(self, r, now, level=0.0):
        bob = _BOB[(now // (260 if self.asleep else 120)) % len(_BOB)]
        x = self.x
        y = self.y + bob
        if level > 0.55 and _chance(level * 0.15):
            x += random.randint(-1, 1)      # jitter when it's falling apart
        spr = self._frame(now)

        if self.vanish_t is not None:
            t = ticks_diff(now, self.vanish_t)
            if self.hidden:
                if _chance(0.06):           # a flicker of it, mid-vanish
                    r.sprite(sprites.FADE[1], x, y)
                return
            if t < 150 or t > 1250:
                spr = sprites.FADE[0]
            elif t < 300 or t > 1100:
                spr = sprites.FADE[1]

        if self.stutter > 0:
            gx, gy = self.ghost_xy
            r.sprite(sprites.HOLLOW if _chance(0.5) else sprites.FADE[0], gx, gy + bob)
            if _chance(0.4):
                spr = sprites.GLITCH
        r.sprite(spr, x, y)

        if self.asleep:
            # little z's rising off it
            ph = (now // 450) % 4
            if ph:
                r.text('z', int(x) + 20 + ph * 2, int(y) - ph * 3 + 2)
