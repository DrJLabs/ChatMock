# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


ROOT = Path(SPECPATH).resolve()

a = Analysis(
    [str(ROOT / 'gui.py')],
    pathex=[],
    binaries=[],
    datas=[
        (str(ROOT / 'prompt.md'), '.'),
        (str(ROOT / 'prompt_gpt5_codex.md'), '.'),
        (str(ROOT / 'build/icons/appicon.png'), '.'),
    ],
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
    [],
    exclude_binaries=True,
    name='ChatMockLinuxSmoke',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ChatMockLinuxSmoke',
)
