"""build_installer_macos.py — Build the 3D Print Sync macOS installer.

Usage:
    python build_installer_macos.py

Steps:
    1. Verify prerequisites (pytest, pyinstaller).
    2. Run pytest — abort on failure.
    3. Run PyInstaller with macOS spec — abort on failure.
    4. Optionally codesign if CODESIGN_IDENTITY env var is set.
    5. Create DMG via hdiutil.

Requirements:
    pip install pyinstaller pytest
    Xcode Command Line Tools (for hdiutil, codesign)
"""

import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SPEC_FILE = SCRIPT_DIR / "sort_downloads_app_macos.spec"
APP_BUNDLE = SCRIPT_DIR / "dist" / "3DPrintSync.app"
VERSION = "1.2.0"
DMG_OUTPUT = SCRIPT_DIR / "dist" / f"3DPrintSync-{VERSION}.dmg"


def check_prerequisites() -> None:
    """Verify build tools are available; exit with a clear message if not.

    Raises:
        SystemExit: When pyinstaller or pytest cannot be found.
    """
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("ERROR: PyInstaller not found.  Run:  pip install pyinstaller")
        sys.exit(1)

    try:
        import pytest  # noqa: F401
    except ImportError:
        print("ERROR: pytest not found.  Run:  pip install -r requirements-dev.txt")
        sys.exit(1)


def run_pytest() -> None:
    """Run the test suite; abort the build on any failure.

    Raises:
        SystemExit: When pytest exits with a non-zero return code.
    """
    print("=== Step 0: pytest ===")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests"],
        cwd=str(SCRIPT_DIR),
    )
    if result.returncode != 0:
        print(f"ERROR: pytest failed (exit {result.returncode})")
        sys.exit(result.returncode)
    print()


def run_pyinstaller() -> None:
    """Run PyInstaller using the macOS spec file.

    Raises:
        SystemExit: When PyInstaller exits with a non-zero return code.
    """
    print("=== Step 1: PyInstaller ===")
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(SPEC_FILE), "--noconfirm"],
        cwd=str(SCRIPT_DIR),
    )
    if result.returncode != 0:
        print(f"ERROR: PyInstaller failed (exit {result.returncode})")
        sys.exit(result.returncode)
    print()


def codesign_if_available() -> None:
    """Sign the .app bundle if CODESIGN_IDENTITY is set; skip otherwise.

    Full notarization (notarytool submit) is a follow-up task. Without signing,
    users must right-click → Open on first launch to bypass Gatekeeper.
    """
    identity = os.environ.get("CODESIGN_IDENTITY")
    if not identity:
        print("CODESIGN_IDENTITY not set — skipping code signing")
        return
    print("=== Step 2: codesign ===")
    subprocess.run(
        [
            "codesign",
            "--deep",
            "--force",
            "--sign",
            identity,
            str(APP_BUNDLE),
        ],
        check=True,
    )
    print()


def create_dmg() -> None:
    """Create a DMG disk image containing the .app bundle via hdiutil.

    Raises:
        SystemExit: When hdiutil exits with a non-zero return code.
    """
    print("=== Step 3: DMG ===")
    # Remove existing DMG if present
    if DMG_OUTPUT.exists():
        DMG_OUTPUT.unlink()
    result = subprocess.run(
        [
            "hdiutil",
            "create",
            "-volname",
            "3DPrintSync",
            "-srcfolder",
            str(APP_BUNDLE),
            "-ov",
            "-format",
            "UDZO",
            str(DMG_OUTPUT),
        ],
        cwd=str(SCRIPT_DIR),
    )
    if result.returncode != 0:
        print(f"ERROR: hdiutil failed (exit {result.returncode})")
        sys.exit(result.returncode)
    print(f"DMG ready: {DMG_OUTPUT}")


def main() -> None:
    """Orchestrate the full macOS build (pytest -> PyInstaller -> codesign -> DMG)."""
    check_prerequisites()
    run_pytest()
    run_pyinstaller()
    codesign_if_available()
    create_dmg()


if __name__ == "__main__":
    main()
