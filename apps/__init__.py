# apps -- one screen per file.  Every screen subclasses App.


class App:
    protect = None      # (y0, y1): rows glitches must leave alone
    glitch = None       # force a glitch level (else the ghost's mood decides)
    allow_screen_off = True

    def enter(self, ctx):
        self.ctx = ctx

    def resume(self):
        """Called when a screen above this one closes."""
        pass

    def exit(self):
        pass

    def event(self, ev):
        if ev == 'hold':
            self.ctx.pop()

    def update(self, now):
        pass

    def draw(self, r, now):
        pass


def load(name):
    """Import apps/<name>.py and return its App class, or None if that
    part of the ghost hasn't been built yet."""
    try:
        mod = __import__('apps.' + name, None, None, ('App',))
    except ImportError as e:
        print("[apps] %s not available: %s" % (name, e))
        return None
    return mod.App
