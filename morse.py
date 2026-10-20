# morse.py -- International Morse (ITU-R M.1677-1) and a live decoder.
#
# Pure logic, no hardware: the telegraph screen feeds it press lengths and
# gap lengths in milliseconds.  Run  import morse; morse.selftest()  in the
# REPL to check it.
#
#   unit = 1200 / WPM ms
#   press  < 2 units           -> dot, otherwise dash
#   gap    < 2 units           -> same letter
#          2..5 units          -> letter break  (committed as soon as the
#          > 5 units           -> word break     gap passes 2 units)

CODE = {
    'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.', 'F': '..-.',
    'G': '--.', 'H': '....', 'I': '..', 'J': '.---', 'K': '-.-', 'L': '.-..',
    'M': '--', 'N': '-.', 'O': '---', 'P': '.--.', 'Q': '--.-', 'R': '.-.',
    'S': '...', 'T': '-', 'U': '..-', 'V': '...-', 'W': '.--', 'X': '-..-',
    'Y': '-.--', 'Z': '--..',
    '0': '-----', '1': '.----', '2': '..---', '3': '...--', '4': '....-',
    '5': '.....', '6': '-....', '7': '--...', '8': '---..', '9': '----.',
    '.': '.-.-.-', ',': '--..--', '?': '..--..', '/': '-..-.', '-': '-....-',
    '(': '-.--.', ')': '-.--.-', '@': '.--.-.', '=': '-...-', '+': '.-.-.',
}
DECODE = {v: k for k, v in CODE.items()}

# prosigns, sent as one run with no letter gaps
SOS = '...---...'
PROSIGNS = (('SOS', SOS), ('error', '........'))

MIN_WPM = 5
MAX_WPM = 20


def unit_ms(wpm):
    return 1200 / wpm


def encode(text):
    """'SOS' -> ['...', '---', '...']; spaces become ' ' (word gaps)."""
    out = []
    for ch in text.upper():
        if ch == ' ':
            out.append(' ')
        elif ch in CODE:
            out.append(CODE[ch])
    return out


class Decoder:
    """Feed press(ms) after each key release, and gap(ms) with the time
    since the last release (as often as you like; it only acts once per
    threshold).  Read .text and .pending."""

    def __init__(self, wpm=8, auto=False):
        self.auto = auto
        self.unit = unit_ms(wpm)
        self.text = ''
        self.pending = ''           # symbols of the letter being keyed
        self._letter_done = True
        self._word_done = True
        self.last = None            # the last thing decoded, for reactions

    @property
    def wpm(self):
        return 1200 / self.unit

    def set_wpm(self, wpm):
        self.unit = unit_ms(wpm)

    def press(self, ms):
        u = self.unit
        sym = '.' if ms < 2 * u else '-'
        if self.auto and sym == '.':
            # track the sender: a running average of their dots
            u = 0.8 * u + 0.2 * ms
            lo, hi = unit_ms(MAX_WPM), unit_ms(MIN_WPM)
            self.unit = lo if u < lo else hi if u > hi else u
        self.pending += sym
        self._letter_done = False
        self._word_done = False
        return sym

    def gap(self, ms):
        u = self.unit
        if not self._letter_done and ms >= 2 * u:
            self._letter_done = True
            self._commit()
        if not self._word_done and ms > 5 * u:
            self._word_done = True
            if self.text and not self.text.endswith(' '):
                self.text += ' '

    def flush(self):
        """End of input: commit whatever is pending."""
        if not self._letter_done:
            self._letter_done = True
            self._commit()

    def _commit(self):
        p = self.pending
        self.pending = ''
        if not p:
            return
        if len(p) >= 8 and p == '.' * len(p):
            # the error prosign: erase the last character
            self.text = self.text.rstrip(' ')[:-1]
            self.last = 'error'
            return
        if p == SOS:
            ch = 'SOS'
        else:
            ch = DECODE.get(p, '?')
        self.text += ch
        self.last = ch
        if len(self.text) > 200:
            self.text = self.text[-200:]

    def clear(self):
        self.text = ''
        self.pending = ''
        self._letter_done = True
        self._word_done = True


def run(events, wpm=10, auto=False):
    """Decode a list of (press_ms, gap_after_ms) pairs."""
    d = Decoder(wpm, auto)
    for press, gap in events:
        d.press(press)
        d.gap(gap)
    d.flush()
    return d.text.strip()


def selftest():
    """Run in the REPL:  import morse; morse.selftest()"""
    dot = lambda gap=120: (120, gap)
    dash = lambda gap=120: (360, gap)
    cases = (
        ("SOS (three letters)", [dot(), dot(), dot(600), dash(), dash(), dash(600),
                                 dot(), dot(), dot(600)], "SOS"),
        ("sloppy HI", [(90, 150), (150, 90), (110, 140), (130, 380),
                       (100, 120), (140, 600)], "HI"),
        ("E, word gap, E", [(120, 840), (120, 600)], "E E"),
        ("A, error, N", [dot(), dash(360)] + [dot()] * 7 + [dot(360)] +
                        [dash(), dot(600)], "N"),
        ("SOS as one run", [dot(), dot(), dot(), dash(), dash(), dash(),
                            dot(), dot(), dot(600)], "SOS"),
        ("every character", None, None),
    )
    bad = 0
    for name, ev, want in cases:
        if ev is None:
            # round-trip the whole table at 10 WPM, perfect timing
            ev = []
            want = ''
            for ch in CODE:
                for i, s in enumerate(CODE[ch]):
                    last = i == len(CODE[ch]) - 1
                    ev.append((120 if s == '.' else 360, 360 if last else 120))
                want += ch
        got = run(ev, 10)
        ok = got == want
        bad += not ok
        print("%s %-20s -> %r" % ("ok  " if ok else "FAIL", name, got if len(got) < 30 else got[:12] + '...'))
    print("all passed" if not bad else "%d FAILED" % bad)
    return not bad
