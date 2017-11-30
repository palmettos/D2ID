# -*- mode: python -*-

# specify pygubu modules
hidden_imports = [
    'pygubu.builder.tkstdwidgets',
    'pygubu.builder.ttkstdwidgets',
    'pygubu.builder.widgets.dialog',
    'pygubu.builder.widgets.editabletreeview',
    'pygubu.builder.widgets.scrollbarhelper',
    'pygubu.builder.widgets.scrolledframe',
    'pygubu.builder.widgets.tkscrollbarhelper',
    'pygubu.builder.widgets.tkscrolledframe',
    'pygubu.builder.widgets.pathchooserinput',
]

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['C:\\Python27\\Lib\\site-packages\\'],
    binaries=[],
    datas=[],
    hiddenimports=hidden_imports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='d2id',
    debug=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=False
)
