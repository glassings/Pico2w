# stub -- stands in for parts of the ghost that haven't been built yet.

from apps import App as Screen
import phrases


class App(Screen):
    def __init__(self, label):
        self.label = label

    def enter(self, ctx):
        super().enter(ctx)
        ctx.puppet.set_bounds(40, 12, 64, 14, snap=True)
        ctx.say(phrases.pick('stub'))

    def event(self, ev):
        if ev == 'click':
            self.ctx.say(phrases.pick('stub'))
        super().event(ev)

    def draw(self, r, now):
        ctx = self.ctx
        r.center(self.label, 0)
        ctx.puppet.draw(r, now, ctx.ghost.glitch)
        ctx.speech.draw(r, 47, now, ctx.ghost.glitch)

    def exit(self):
        self.ctx.speech.clear()
