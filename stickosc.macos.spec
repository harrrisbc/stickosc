# -*- mode: python ; coding: utf-8 -*-
# macOS-only PyInstaller spec → dist/StickOSC.app
# Prefer: ./tools/build_mac.sh

block_cipher = None

a = Analysis(
    ['gui_app.py'],
    pathex=[],
    binaries=[],
    datas=[('mapping.yaml', '.')],
    hiddenimports=[
        'pygame',
        'yaml',
        'pythonosc',
        'pythonosc.udp_client',
        'mido',
        'rtmidi',
        'stickosc',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='StickOSC',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='StickOSC',
)

app = BUNDLE(
    coll,
    name='StickOSC.app',
    icon=None,
    bundle_identifier='com.stickosc.app',
    info_plist={
        'CFBundleName': 'StickOSC',
        'CFBundleDisplayName': 'StickOSC',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleIdentifier': 'com.stickosc.app',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '11.0',
    },
)
