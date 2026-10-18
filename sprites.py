# sprites.py -- hand-drawn 1-bit art.  '#' = lit pixel, '.' = dark.
# Edit the pictures directly; they are packed into framebuffers at import.

import framebuf


class Sprite:
    def __init__(self, w, h, buf):
        self.w = w
        self.h = h
        self.fb = framebuf.FrameBuffer(buf, w, h, framebuf.MONO_HLSB)


def _pack(rows, keep=None):
    h = len(rows)
    w = len(rows[0])
    stride = (w + 7) // 8
    buf = bytearray(stride * h)
    for y in range(h):
        row = rows[y]
        for x in range(w):
            if row[x] == '#' and (keep is None or keep(x, y)):
                buf[y * stride + (x >> 3)] |= 0x80 >> (x & 7)
    return Sprite(w, h, buf)


def _swap(rows, changes):
    # copy of `rows` with some lines replaced: {row_index: "new row"}
    out = list(rows)
    for i in changes:
        out[i] = changes[i]
    return out


def _shift(rows, lo, hi, dx):
    # slide rows lo..hi sideways by dx (the "torn" look)
    out = list(rows)
    w = len(rows[0])
    for i in range(lo, hi + 1):
        r = rows[i]
        out[i] = ('.' * dx + r)[:w] if dx > 0 else (r[-dx:] + '.' * -dx)
    return out


def _outline(rows):
    # keep only edge pixels -> a hollow, half-there ghost
    h = len(rows)
    w = len(rows[0])
    out = []
    for y in range(h):
        line = ''
        for x in range(w):
            c = '.'
            if rows[y][x] == '#':
                for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                    if not (0 <= nx < w and 0 <= ny < h) or rows[ny][nx] != '#':
                        c = '#'
                        break
            line += c
        out.append(line)
    return out


# ---------------------------------------------------------------- the ghost
# 24x24.  Big hollow eyes, a small "o" of a mouth, scalloped hem.
_BASE = [
    "........########........",  # 0
    "......############......",  # 1
    ".....##############.....",  # 2
    "....################....",  # 3
    "...##################...",  # 4
    "...##################...",  # 5
    "..####...######...####..",  # 6  eyes
    "..###.....####.....###..",  # 7
    "..###.....####.....###..",  # 8
    "..###.....####.....###..",  # 9
    "..####...######...####..",  # 10
    "..####################..",  # 11
    "..#########..#########..",  # 12 mouth
    "..########....########..",  # 13
    "..#########..#########..",  # 14
    "..####################..",  # 15
    "..####################..",  # 16
    "..####################..",  # 17
    "..####################..",  # 18
    "..####################..",  # 19
    "..###..####..####..###..",  # 20 hem
    "..##....##....##....##..",  # 21
    "........................",  # 22
    "........................",  # 23
]
_FULL = "..####################.."

_IDLE_B = _swap(_BASE, {
    20: "..####..####..####..##..",
    21: "...##....##....##.......",
})

_BLINK = _swap(_BASE, {
    6: _FULL, 7: _FULL,
    8: "..###.....####.....###..",
    9: _FULL, 10: _FULL,
})

# looking straight out of the screen at you
_STARE = _swap(_BASE, {
    8: "..###..#..####..#..###..",
    12: _FULL,
    13: "..########....########..",
    14: _FULL,
})

_EXCITED = _swap(_BASE, {
    6: _FULL,
    7: "..#####.########.#####..",
    8: "..####.#.######.#.####..",
    9: "..###.###.####.###.###..",
    10: _FULL,
    12: "..######........######..",
    13: "..#######......#######..",
    14: "..########....########..",
})

_NERVOUS = _swap(_BASE, {
    2: ".....##############..#..",
    3: "....################.##.",
    6: _FULL,
    7: "..###..#######..######..",
    8: "..###..#######..######..",
    9: _FULL, 10: _FULL,
    12: _FULL,
    13: "..#######.#.#.#.######..",
    14: "..########.#.#.#######..",
})

_SLEEP = _swap(_BASE, {
    6: _FULL, 7: _FULL, 8: _FULL,
    9: "..###.###.####.###.###..",
    10: "..####...######...####..",
    12: _FULL,
    13: "..#########..#########..",
    14: _FULL,
})

# torn: slices of the body slid sideways, one scanline missing
_GLITCH = _shift(_shift(_BASE, 3, 6, 3), 13, 16, -2)
_GLITCH[9] = "." * 24

_checker = lambda x, y: (x + y) & 1 == 0
_sparse = lambda x, y: (x & 1) == 0 and (y & 1) == 0

IDLE = (_pack(_BASE), _pack(_IDLE_B))
BLINK = _pack(_BLINK)
STARE = _pack(_STARE)
EXCITED = _pack(_EXCITED)
NERVOUS = _pack(_NERVOUS)
SLEEP = _pack(_SLEEP)
GLITCH = _pack(_GLITCH)
HOLLOW = _pack(_outline(_BASE))
# fading in/out of existence: solid -> half -> quarter -> gone
FADE = (_pack(_BASE, _checker), _pack(_BASE, _sparse))

EXPR = {
    'stare': STARE,
    'excited': EXCITED,
    'nervous': NERVOUS,
    'sleep': SLEEP,
    'blink': BLINK,
    'glitch': GLITCH,
    'hollow': HOLLOW,
}

# ------------------------------------------------- tiny ghost: menu cursor
MINI = _pack([
    "..####..",
    ".######.",
    "##.##.##",
    "##.##.##",
    "########",
    "########",
    "########",
    "#.##.##.",
])

# ------------------------------------------- 8x8 noise glyphs for corruption
def _glyph(*rows):
    return Sprite(8, 8, bytearray(rows))


NOISE = (
    _glyph(0xAA, 0x55, 0xAA, 0x55, 0xAA, 0x55, 0xAA, 0x55),
    _glyph(0x7E, 0x7E, 0x7E, 0x7E, 0x7E, 0x7E, 0x7E, 0x00),
    _glyph(0xFF, 0x00, 0xFF, 0x00, 0x7E, 0x00, 0xFF, 0x00),
    _glyph(0x5A, 0xE7, 0x3C, 0x99, 0x66, 0xC3, 0x7E, 0x18),
    _glyph(0xF0, 0xF0, 0xF0, 0xF0, 0x0F, 0x0F, 0x0F, 0x0F),
    _glyph(0x00, 0x3C, 0x42, 0x5A, 0x5A, 0x42, 0x3C, 0x00),
)


# ---------------------------------------------------------------- halloween
# A witch hat that sits on the ghost's head (16x9; dark band above the brim)
HAT = _pack([
    ".........##.....",
    "........###.....",
    ".......####.....",
    "......#####.....",
    ".....######.....",
    ".....#.....#....",
    "....########....",
    "################",
    ".##############.",
])

# A jack-o'-lantern for the corner of the room (12x11)
PUMPKIN = _pack([
    ".....#......",
    "....##......",
    "..###.####..",
    ".##########.",
    "###.####.###",
    "##..####..##",
    "############",
    "##.#.##.#.##",
    "###.#..#.###",
    ".##########.",
    "..########..",
])

# A bat, wings up / wings down (12x6)
BAT = (
    _pack([
        "#..........#",
        "##..#..#..##",
        "###.####.###",
        ".##########.",
        "....####....",
        ".....##.....",
    ]),
    _pack([
        "....#..#....",
        "....####....",
        "..########..",
        ".###.##.###.",
        "##........##",
        "#..........#",
    ]),
)

# Eyes in the dark (7x2): open, and mid-blink
EYES = (
    _pack(["##...##", "##...##"]),
    _pack([".......", "##...##"]),
)
