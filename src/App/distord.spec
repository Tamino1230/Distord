# -*- mode: python ; coding: utf-8 -*-

import os
import sys

BASE_DIR = SPECPATH

if sys.platform == "win32":
    ICON_PATH = os.path.abspath(
        os.path.join(BASE_DIR, '..', 'Assets', 'icons', 'icon.ico')
    )
else:
    # linux
    ICON_PATH = os.path.abspath(
        os.path.join(BASE_DIR, '..', 'Assets', 'icons', 'icon.png')
    )

a = Analysis(
    ['distord.py'],
    pathex=[],
    binaries=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Distord',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON_PATH
)