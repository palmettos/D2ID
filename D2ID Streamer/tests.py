import time


class VerboseTrace:

    def __init__(self, bool):
        self.enabled = bool

        if self.enabled:
            self.body = '-'*80+'\n'
            self.start = time.time()
            self.add_line('Begin: ' + str(self.start))
            self.last_timestamp = time.time()

    def add_line(self, line):
        if self.enabled:
            self.body += str(line) + '\n'

    def timestamp(self):
        if self.enabled:
            now = time.time()
            self.body += 'Timestamp: ' + str(now) + '\n'
            self.body += 'Time since last timestamp: ' + str(now - self.last_timestamp) + '\n'
            self.last_timestamp = now

    def finish(self, f):
        if self.enabled:
            self.add_line('End: ' + str(time.time()))
            f.write(self.body + '\n')
            self.body = '-'*80+'\n'
            self.start = time.time()
            self.add_line('Begin: ' + str(self.start))
