from signals import SignalRegistry
from threading import Thread, Lock
from ebs import EBSConnection
from item_state import InventoryComparator
import pygubu
import Tkinter
import time


class MainWindow(pygubu.TkApplication):

    def _init_after(self):
        self.registry = SignalRegistry()
        self.registry.register('log', self.log_message)
        self.registry.register('ebs connecting', self.on_connecting)
        self.registry.register('ebs connected', self.on_connected)
        self.registry.register('logged in', self.on_logged_in)
        self.registry.register('logged in', self.save_if_remember)
        self.registry.register('ws thread join', self.on_disconnected)
        self.registry.register('ws thread return', self.on_disconnected)

        self.logging_lock = Lock()

        self.registry.emit('log', 'Welcome to D2ID!', False)
        self.registry.emit(
            'log',
            'Please enter your Twitch username ' +\
            'and the extension key from your ' +\
            'D2ID config panel, then click Connect.'
        )

        try:
            with open('config', 'r') as conf:
                self.window_vars['remember'].set(1)
                self.window_vars['username'].set(conf.readline().strip('\n'))
        except:
            pass

        self.ebs = EBSConnection(self.registry)
        self.comparator = InventoryComparator(self.registry)

    def _create_ui(self):
        builder = pygubu.Builder()
        builder.add_from_file('window.ui')

        self.elements = dict(
            frame          = builder.get_object('frame', self.master),
            credentials    = builder.get_object('credentials', self.master),
            label_username = builder.get_object('label_username', self.master),
            text_username  = builder.get_object('text_username', self.master),
            chk_rem_uname  = builder.get_object('check_remember_username', self.master),
            label_key      = builder.get_object('label_key', self.master),
            text_key       = builder.get_object('text_key', self.master),
            button_connect = builder.get_object('button_connect', self.master),
            message_log    = builder.get_object('message_log', self.master)
        )

        self.elements['chk_rem_uname'].deselect()
        self.elements['message_log'].tag_config('ts', foreground='#999999')

        self.window_vars = dict(
            username = builder.get_variable('username'),
            remember = builder.get_variable('remember_username'),
            password = builder.get_variable('key')
        )
        self.window_vars['username'].trace('w', self.on_text_change)
        self.window_vars['password'].trace('w', self.on_text_change)

        builder.connect_callbacks(self)

    def on_text_change(self, *args):
        u_len = len(self.window_vars['username'].get())
        p_len = len(self.window_vars['password'].get())

        if u_len >= 4:
            self.elements['chk_rem_uname'].config(state=Tkinter.NORMAL)
        else:
            self.elements['chk_rem_uname'].config(state=Tkinter.DISABLED)
            self.elements['chk_rem_uname'].deselect()

        if u_len >= 4 and p_len >= 16:
            self.elements['button_connect'].config(state=Tkinter.NORMAL)
        else:
            self.elements['button_connect'].config(state=Tkinter.DISABLED)

    def on_disconnected(self, message=None):
        self.elements['text_username'].config(state=Tkinter.NORMAL)
        self.elements['chk_rem_uname'].config(state=Tkinter.NORMAL)
        self.elements['text_key'].config(state=Tkinter.NORMAL)
        self.elements['button_connect'].config(
            state=Tkinter.NORMAL, text='Connect', command=self.connect
        )
        if message:
            self.registry.emit('log', message)
        self.registry.emit('stop diff loop')

    def on_connecting(self):
        self.elements['text_username'].config(state=Tkinter.DISABLED)
        self.elements['chk_rem_uname'].config(state=Tkinter.DISABLED)
        self.elements['text_key'].config(state=Tkinter.DISABLED)
        self.elements['button_connect'].config(
            state=Tkinter.DISABLED, text='Connecting...', command=self.disconnect
        )
        self.registry.emit('log', 'Attempting to connect to the d2id EBS...')

    def on_connected(self):
        self.elements['button_connect'].config(
            state=Tkinter.NORMAL, text='Disconnect', command=self.disconnect
        )

    def on_logged_in(self):
        self.registry.emit('start diff loop')

    def connect(self):
        username = self.window_vars['username'].get()
        password = self.window_vars['password'].get()
        self.registry.emit('ebs connect', username, password)

    def disconnect(self):
        self.registry.emit('stop diff loop')
        self.registry.emit('ebs disconnect')

    def log_message(self, message, leading_newline=True):
        with self.logging_lock:
            timestamp = time.strftime('\n' * leading_newline + '[%H:%M:%S] ')
            self.elements['message_log'].config(state=Tkinter.NORMAL)
            self.elements['message_log'].insert(Tkinter.END, timestamp, 'ts')
            self.elements['message_log'].insert(Tkinter.END, message)
            self.elements['message_log'].config(state=Tkinter.DISABLED)
            self.elements['message_log'].see(Tkinter.END)

    def save_if_remember(self):
        if self.window_vars['remember'].get():
            with open('config', 'w') as conf:
                conf.write(self.window_vars['username'].get())
