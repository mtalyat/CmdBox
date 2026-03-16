# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

project_root = Path.cwd()

datas = [
    (str(project_root / "default.cmdbox"), "."),
    (str(project_root / "assets" / "Icon.png"), "."),
]

icon_path = project_root / "assets" / "Icon.ico"

icons_dir = project_root / "icons"
if icons_dir.exists() and icons_dir.is_dir():
    datas.append((str(icons_dir), "icons"))


block_cipher = None


a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
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
    name="CmdBox",
    icon=str(icon_path) if icon_path.exists() else None,
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
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="CmdBox",
)
