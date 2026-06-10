# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for 3D Print Sync (macOS).

Build with:
    pyinstaller sort_downloads_app_macos.spec --noconfirm

Output: dist/3DPrintSync.app
"""

a = Analysis(
    ["sort_downloads_app.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("app-icon-100.png", "."),
        ("assets/app-icon.icns", "."),
        ("assets/app-icon-menubar.png", "."),
        ("assets/app-icon-menubar@2x.png", "."),
        ("categories.default.json", "."),
    ],
    hiddenimports=[
        "sort_downloads",
        "platform_support",
        "platform_support._darwin",
        "pystray._darwin",
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
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,  # native arch (arm64 on Apple Silicon, x86_64 on Intel)
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/app-icon.icns",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="3DPrintSync",
)

app = BUNDLE(
    coll,
    name="3DPrintSync.app",
    icon="assets/app-icon.icns",
    bundle_identifier="com.3dprintsync.app",
    info_plist={
        "CFBundleShortVersionString": "1.2.0",
        "LSUIElement": "1",
    },
)
