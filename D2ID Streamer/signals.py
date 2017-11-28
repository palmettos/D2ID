from collections import defaultdict


class SignalRegistry:

    def __init__(self):
        self.signals = defaultdict(list)

    def register(self, signal, callback):
        if callback not in self.signals[signal]:
            self.signals[signal].append(callback)

    def unregister(self, signal, callback):
        if callback in self.signals[signal]:
            self.signals[signal].remove(callback)

    def emit(self, signal, *args):
        for callback in self.signals[signal]:
            callback(*args)