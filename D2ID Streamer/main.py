import Tkinter as tk
from window import MainWindow
import time

root = tk.Tk()
root.resizable(0, 0)
icon = tk.PhotoImage(file='./d2id.ico')
root.tk.call('wm', 'iconphoto', root._w, icon)
app = MainWindow(root)

with open('error.log', 'w') as log:
    log.write('-' * 80 + '\n')
    log.write(time.strftime('%m-%d-%Y @ %H:%M:%S\n'))
    log.write('-' * 80 + '\n')

app.set_title('D2ID')
app.run()
