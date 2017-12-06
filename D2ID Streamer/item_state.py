import json
import time
import struct
import pywintypes
from ctypes import sizeof, c_int
from win32file import *
from win32pipe import *
from threading import Thread
from tests import VerboseTrace
import traceback

DI_PIPE_BUF_SIZE = 1024
SIZEOF_INT = sizeof(c_int)
LOGGING = True

err = VerboseTrace(False)

class PipeHandler:

    def __init__(self, registry):
        self.registry = registry
        self.pipe_name = r'\\.\pipe\DiabloInterfaceItems'

    def _construct_query(self, json_dict):
        s = json.dumps(json_dict, encoding='utf-8')
        return struct.pack('i', len(s)) + s

    def _transact(self, query):
        err.add_line('Constructing packet')
        packet = self._construct_query(query)
        retries = 0

        while True:
            if retries > 10:
                raise

            err.add_line('Beginning pipe connection loop')
            try:
                err.add_line('Getting handle to DI pipe')
                err.timestamp()
                handle = CreateFile(
                    self.pipe_name,
                    GENERIC_READ|GENERIC_WRITE,
                    0,
                    None,
                    OPEN_EXISTING,
                    0,
                    None
                )
                err.add_line('Got handle to pipe')
                err.timestamp()
            except pywintypes.error as e:
                err.add_line('pywintypes error: ' + str(e))
                err.timestamp()
                error = e[0]
                if error == 231:
                    err.add_line('Error code 231, waiting for busy pipe')
                    err.timestamp()
                    try:
                        if WaitNamedPipe(self.pipe_name, 1000):
                            err.add_line('Pipe connection timed out')
                            err.timestamp()
                    except pywintypes.error as wfpe:
                        err.add_line('Error waiting for pipe: ' + str(wfpe))
                        time.sleep(0.1)
                        retries += 1
                        continue
                elif error == 2:
                    err.add_line('Error code 2, pipe isn\'t yet reopened, sleep/retry')
                    time.sleep(0.1)
                    retries += 1
                    continue
                else:
                    raise
            else:
                err.add_line('Breaking out of pipe connection loop')
                err.timestamp()
                break

        err.add_line('Writing to pipe')
        err.timestamp()
        WriteFile(handle, packet)
        err.add_line('Returned from writing to pipe')
        err.timestamp()

        err.add_line('Reading length of pipe response')
        out = ReadFile(handle, DI_PIPE_BUF_SIZE)[1]
        length = struct.unpack('i', out[:SIZEOF_INT])[0]
        err.add_line('Length: ' + str(out))
        err.timestamp()

        err.add_line('Reading pipe payload')
        err.timestamp()
        while len(out) < length + SIZEOF_INT:
            out += ReadFile(handle, DI_PIPE_BUF_SIZE)[1]
        err.add_line('Finished reading payload')
        err.timestamp()
        err.add_line('Closing pipe handle')
        err.timestamp()
        CloseHandle(handle)
        err.add_line('Closed pipe handle')
        err.timestamp()

        err.add_line('Parsing and returning JSON data')
        data = json.loads(out[SIZEOF_INT:], encoding='utf-8')
        return data

    def get_items(self):
        err.add_line('At beginning of PipeHandler.get_items')
        slots = [
            'helm',
            'armor',
            'amulet',
            'rings',
            'belt',
            'gloves',
            'boots',
            'weapon',
            'shield',
            'weapon2',
            'shield2'
        ]
        responses = []
        err.add_line('Making requests...')
        err.timestamp()
        for slot in slots:
            err.add_line('Making pipe transaction')
            response = self._transact({'EquipmentSlot': slot})
            err.add_line('Got pipe response')
            if response['Success']:
                for item in response['Items']:
                    responses.append(item)
        err.add_line('Finished making requests, returning responses')
        err.timestamp()
        # response = self._transact({u'Resource': u'items', u'Payload': u''})[u'Payload']
        err.add_line('Responses: ' + str(responses))
        return responses


class Diff:

    def __init__(self, added, removed):
        self.added = added
        self.removed = removed

    def length(self):
        return len(self.added + self.removed)

    def to_dict(self):
        return {u'added': self.added, u'removed': self.removed}

    def to_json(self):
        payload = {'added': self.added, 'removed': self.removed}
        return json.dumps(json.dumps(payload))


class ItemState:

    def __init__(self, registry):
        self.registry = registry
        self.current_state = {}
        for i in range(1, 13):
            self.current_state[i] = None

    def diff(self, item_set):
        err.add_line('In ItemState.diff, processing changes')
        err.add_line('Item set: ' + str(item_set))
        err.timestamp()
        assert type(item_set) is list, 'diff requires list'

        item_set = {item[u'Location']: item for item in item_set if item}
        equipped = set([key for key in self.current_state.keys() if self.current_state[key]])
        new_equipped = set(item_set.keys())

        added_slots   = new_equipped.difference(equipped)
        removed_slots = equipped.difference(new_equipped)
        updated_slots = new_equipped.intersection(equipped)

        added, removed = [], []

        for slot in added_slots:
            added.append(item_set[slot])
            self.current_state[slot] = item_set[slot]

        for slot in removed_slots:
            removed.append(slot)
            self.current_state[slot] = None

        for slot in updated_slots:
            if self.current_state[slot] != item_set[slot]:
                added.append(item_set[slot])
                self.current_state[slot] = item_set[slot]

        err.add_line('Returning Diff object')
        err.timestamp()
        return Diff(added, removed)


class DirtyItemState(ItemState):

    def __init__(self, registry):
        ItemState.__init__(self, registry)
        self.last_change = time.time()

    def diff(self, item_set):
        err.add_line('In DirtyState.diff, checking for changes')
        if ItemState.diff(self, item_set).length() > 0:
            err.add_line('Item change detected')
            err.timestamp()
            self.last_change = time.time()
            err.add_line('Last change at: ' + str(self.last_change))
        self.time_since_change = time.time() - self.last_change
        err.add_line('Time since last change: ' + str(self.time_since_change))


class CleanItemState(ItemState):

    def __init__(self, registry):
        ItemState.__init__(self, registry)

    def diff(self, dirty_state):
        err.add_line('In CleanState.diff, checking DirtyState')
        if dirty_state.time_since_change > 1:
            err.add_line('DirtyState idle for longer than 2 seconds, diffing')
            err.timestamp()
            diff = ItemState.diff(self, dirty_state.current_state.values())
            err.add_line('Diff body: ' + str(diff.added + diff.removed))
            err.add_line('Diff length: ' + str(diff.length()))
            if diff.length() > 0:
                err.add_line('Diff length > 0, returning current state')
                print str(self.current_state)
                return self.current_state
        err.add_line('No changes, returning None')
        err.timestamp()
        return None


class InventoryComparator():

    def __init__(self, registry):
        self.registry = registry
        self.registry.register('start diff loop', self.connect)
        self.registry.register('stop diff loop', self.disconnect)

    def connect(self):
        self.keep_running = True

        def diff_loop():
            self.registry.emit(
                'log',
                'Inventory state reading has begun. ' +\
                'Please ensure that DiabloInterface ' +\
                'is running, or data cannot be transmitted.'
            )
            err.add_line('Creating/clearing verbose log')
            with open('verbose.log', 'w') as f:
                pass
            err.add_line('Starting IC.diff_loop')

            pipe = PipeHandler(self.registry)
            dirty_state = DirtyItemState(self.registry)
            clean_state = CleanItemState(self.registry)

            def update(item_set):
                err.add_line('Starting item comparison')
                err.timestamp()
                dirty_state.diff(item_set)
                return clean_state.diff(dirty_state)

            while self.keep_running:
                try:
                    err.add_line('At beginning of diff loop try block')
                    err.add_line('Calling pipe.get_items')
                    err.timestamp()
                    items    = pipe.get_items()
                    err.timestamp()
                    snapshot = update(items)
                    err.timestamp()
                    if snapshot is None:
                        err.add_line('Got None as snapshot')
                        err.timestamp()
                        with open('verbose.log', 'a') as verbose:
                            err.finish(verbose)
                        continue
                    else:
                        err.add_line('Got Diff, escaping and sending')
                        err.timestamp()
                        escaped = json.dumps(json.dumps((time.time(), snapshot)))
                        err.add_line('Escaped snapshot: ' + escaped)
                        err.add_line('Emitting update signal')
                        err.timestamp()
                        self.registry.emit('update', escaped)
                except Exception as e:
                    err.add_line('An exception occurred')
                    err.timestamp()
                    if LOGGING:
                        with open('error.log', 'a') as log:
                            log.write(str(time.time()) + '\n')
                            traceback.print_exc(file=log)
                finally:
                    with open('verbose.log', 'a') as verbose:
                        err.finish(verbose)
                    time.sleep(0.1)
            self.registry.emit('log', 'Exiting read loop...')

        self.loop = Thread(target=diff_loop)
        self.loop.daemon = True
        self.loop.start()

    def disconnect(self):
        self.keep_running = False
