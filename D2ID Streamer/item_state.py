import json
import time
import struct
import pywintypes
from ctypes import sizeof, c_int
from win32file import *
from win32pipe import *
from threading import Thread
import traceback

DI_PIPE_BUF_SIZE = 1024
SIZEOF_INT = sizeof(c_int)
LOGGING = False


class PipeHandler:

    def __init__(self, registry):
        self.registry = registry

        # develop branch pipe name
        self.pipe_name = r'\\.\pipe\DiabloInterfaceItems'
        # master branch pipe name
        # self.pipe_name = r'\\.\pipe\DiabloInterfaceItems'

    def _construct_query(self, json_dict):
        s = json.dumps(json_dict, encoding='utf-8')
        return struct.pack('i', len(s)) + s

    def _transact(self, query):
        packet = self._construct_query(query)

        while True:
            try:
                handle = CreateFile(
                    self.pipe_name,
                    GENERIC_READ|GENERIC_WRITE,
                    0,
                    None,
                    OPEN_EXISTING,
                    0,
                    None
                )
            except:
                if WaitNamedPipe(self.pipe_name, 1000):
                    print 'waiting for pipe timed out'
                    raise
            else:
                break

        WriteFile(handle, packet)

        out = ReadFile(handle, DI_PIPE_BUF_SIZE)[1]
        length = struct.unpack('i', out[:SIZEOF_INT])[0]

        while len(out) < length + SIZEOF_INT:
            out += ReadFile(handle, DI_PIPE_BUF_SIZE)[1]
        CloseHandle(handle)

        data = json.loads(out[SIZEOF_INT:], encoding='utf-8')
        return data

    def get_items(self):
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
        for slot in slots:
            response = self._transact({'EquipmentSlot': slot})
            if response['Success']:
                for item in response['Items']:
                    responses.append(item)
        # response = self._transact({u'Resource': u'items', u'Payload': u''})[u'Payload']
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

    def __init__(self):
        self.current_state = {}
        for i in range(1, 13):
            self.current_state[i] = None

    def diff(self, item_set):
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

        return Diff(added, removed)


class DirtyItemState(ItemState):

    def __init__(self):
        ItemState.__init__(self)
        self.last_change = time.clock()

    def diff(self, item_set):
        if ItemState.diff(self, item_set).length() > 0:
            self.last_change = time.clock()
        self.time_since_change = time.clock() - self.last_change


class CleanItemState(ItemState):

    def diff(self, dirty_state):
        if dirty_state.time_since_change > 0.25:
            diff = ItemState.diff(self, dirty_state.current_state.values())
            if diff.length() > 0:
                return self.current_state
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

            pipe = PipeHandler(self.registry)
            dirty_state = DirtyItemState()
            clean_state = CleanItemState()

            def update(item_set):
                dirty_state.diff(item_set)
                return clean_state.diff(dirty_state)

            while self.keep_running:
                try:
                    items    = pipe.get_items()
                    snapshot = update(items)
                    if snapshot is None:
                        continue
                    else:
                        escaped = json.dumps(json.dumps((time.time(), snapshot)))
                        print 'sending update'
                        self.registry.emit('update', escaped)
                except Exception as e:
                    if LOGGING:
                        with open('error.log', 'a') as log:
                            traceback.print_exc(file=log)
                finally:
                    time.sleep(0.05)
            self.registry.emit('log', 'Exiting read loop...')

        self.loop = Thread(target=diff_loop)
        self.loop.daemon = True
        self.loop.start()

    def disconnect(self):
        self.keep_running = False
