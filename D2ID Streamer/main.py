import Tkinter as tk
from window import MainWindow
import time

root = tk.Tk()
root.resizable(0, 0)
app = MainWindow(root)
# root.protocol('WM_DELETE_WINDOW', app.kill_thread)
# root.bind('<Destroy>', lambda x: app.kill_thread())

with open('error.log', 'a') as log:
    log.write('-' * 80 + '\n')
    log.write(time.strftime('%m-%d-%Y @ %H:%M:%S\n'))
    log.write('-' * 80 + '\n')

app.set_title('d2id')
app.run()
