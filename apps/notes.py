# notes -- read-only notes from notes.txt (edit it on your PC).
# Separate notes with a line containing only ---
#
# up/down: scroll   left/right: previous/next note   hold: back

from apps import App as Screen
from render import wrap
import phrases
import config as C

LINES = 6
TOP = 10
STEP = 9
MAX_BYTES = 8000


def load():
    try:
        with open(C.NOTES_FILE) as f:
            data = f.read(MAX_BYTES)
    except OSError:
        return []
    notes = []
    cur = []
    for line in data.split('\n'):
        line = line.rstrip('\r')
        if line.strip() == '---':
            notes.append(cur)
            cur = []
            continue
        line = ''.join(c if 32 <= ord(c) < 127 else '?' for c in line.replace('\t', '  '))
        if not line.strip():
            cur.append('')
        else:
            for _, seg in wrap(line, 16, 999):
                cur.append(seg)
    notes.append(cur)
    out = []
    for n in notes:
        while n and not n[-1]:
            n.pop()
        while n and not n[0]:
            n.pop(0)
        if n:
            out.append(n)
    return out


class App(Screen):
    def enter(self, ctx):
        super().enter(ctx)
        self.notes = load()
        self.i = 0
        self.top = 0
        ctx.speech.clear()
        if not self.notes:
            ctx.puppet.set_bounds(40, 10, 64, 18, snap=True)
            ctx.say(phrases.pick('notes_empty'))

    def exit(self):
        self.ctx.speech.clear()

    @property
    def protect(self):
        return (TOP, 64) if self.notes else None

    def event(self, ev):
        if ev == 'hold':
            self.ctx.pop()
            return
        if not self.notes:
            return
        lines = self.notes[self.i]
        if ev == 'down' and self.top + LINES < len(lines):
            self.top += 1
        elif ev == 'up' and self.top > 0:
            self.top -= 1
        elif ev in ('left', 'right'):
            self.i = (self.i + (1 if ev == 'right' else -1)) % len(self.notes)
            self.top = 0

    def draw(self, r, now):
        ctx = self.ctx
        if not self.notes:
            r.center("notes", 0)
            ctx.puppet.draw(r, now, ctx.ghost.glitch)
            ctx.speech.draw(r, 47, now, ctx.ghost.glitch)
            return
        lines = self.notes[self.i]
        n = len(self.notes)
        r.text("notes", 0, 0)
        if n > 1:
            tag = "<%d/%d>" % (self.i + 1, n)
            r.text(tag, 128 - 8 * len(tag), 0)
        r.o.hline(0, 8, 128, 1)
        for k in range(LINES):
            j = self.top + k
            if j >= len(lines):
                break
            r.text(lines[j], 0, TOP + k * STEP)
        # scroll position, a thin bar on the right edge
        if len(lines) > LINES:
            h = 54 * LINES // len(lines)
            y = TOP + (54 - h) * self.top // (len(lines) - LINES)
            r.o.vline(127, y, h, 1)
