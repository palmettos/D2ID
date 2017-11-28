from threading import Thread, Event
from websocket import WebSocketApp
import traceback
import logging

CLIENT_VERSION = '1.0.0'

BASE_URL = 'wss://d2id.multilurk.tv'
UPDATE = '/update'

logging.basicConfig()
sslopt_ca_certs = {'ca_certs': './cacert.pem'}


class EBSConnection():

    def __init__(self, registry):
        self.registry = registry

        self.ping_interval      = 120.0
        self.ping_timeout       = 10.0

        self.registry.register('ebs connect', self.connect)
        self.registry.register('ebs disconnect', self.disconnect)
        self.registry.register('update', self.send_update)

    def connect(self, username, password):
        def on_open(ws):
            self.registry.emit('ebs connected')
            self.registry.emit('log', 'Connection to EBS established.')

        def on_error(ws, e):
            self.registry.emit('log', 'An error occurred: ' + str(e))
            traceback.print_exc()

        def on_close(ws):
            self.registry.emit('log', 'Connection to EBS lost.')

        def on_msg(ws, msg):
            self.registry.emit('log', 'EBS > ' + msg)
            if msg.encode('utf-8') == u'SUCCESS':
                self.registry.emit('logged in')

        def on_pong(ws, data):
            self.registry.emit('log', 'PONG!')

        def ws_main_loop(username, password):
            ws = WebSocketApp(
                BASE_URL + UPDATE,
                header = [
                    'X-User: ' + username,
                    'X-Pass: ' + password,
                    'X-Client-Version: ' + CLIENT_VERSION
                ],
                on_open    = on_open,
                on_close   = on_close,
                on_message = on_msg,
                on_error   = on_error,
                on_pong    = on_pong
            )
            self.ws = ws
            ws.run_forever(
                ping_interval=self.ping_interval,
                ping_timeout=self.ping_timeout,
                sslopt=sslopt_ca_certs
            )
            self.registry.emit('ws thread return')

        self.sock = Thread(target=ws_main_loop, args=(username, password))
        self.sock.daemon = True
        self.sock.start()
        self.registry.emit('ebs connecting')

    def disconnect(self, message=None):
        if self.ws.keep_running:
            self.ws.close()
        if self.sock.is_alive():
            self.sock.join()
            self.registry.emit('ws thread join', message)

    def send_update(self, update):
        #print update
        if self.sock.is_alive():
            self.ws.send(update)
