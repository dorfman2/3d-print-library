# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for 3D Print Sync.

Build with:
    pyinstaller sort_downloads_app.spec --noconfirm

Output: dist/3DPrintSync/   (onedir bundle)
"""

a = Analysis(
    ["sort_downloads_app.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("app-icon-100.png",        "."),
        ("app-icon.ico",            "."),
        ("categories.default.json", "."),
    ],
    hiddenimports=[
        "sort_downloads",
        "pystray._win32",
        "ttkbootstrap",
        "ttkbootstrap.themes",
        "ttkbootstrap.themes.standard",
        "PIL._tkinter_finder",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    collect_submodules=["ttkbootstrap"],
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="3DPrintSync",
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
    icon="app-icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="3DPrintSync",
)
