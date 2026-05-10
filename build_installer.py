"""build_installer.py — Build the 3D Print Sync Windows installer.

Usage:
    python build_installer.py

Steps:
    1. Verify pyinstaller is available.
    2. Verify Inno Setup 6 (ISCC.exe) is installed.
    3. Run PyInstaller to create dist/3DPrintSync/.
    4. Run ISCC to produce dist/3DPrintSync-Setup.exe.

Requirements:
    pip install pyinstaller
    Inno Setup 6  https://jrsoftware.org/isinfo.php
"""

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
_ISCC_CANDIDATES = [
    Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
    Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
    Path.home() / "AppData" / "Local" / "Programs" / "Inno Setup 6" / "ISCC.exe",
]
ISCC_PATH = next((p for p in _ISCC_CANDIDATES if p.exists()), _ISCC_CANDIDATES[0])
SPEC_FILE = SCRIPT_DIR / "sort_downloads_app.spec"
ISS_FILE = SCRIPT_DIR / "installer.iss"
OUTPUT = SCRIPT_DIR / "dist" / "3DPrintSync-Setup.exe"


def check_prerequisites() -> None:
    """Verify build tools are available; exit with a clear message if not.

    Raises:
        SystemExit: When pyinstaller or ISCC.exe cannot be found.
    """
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("ERROR: PyInstaller not found.  Run:  pip install pyinstaller")
        sys.exit(1)

    if not ISCC_PATH.exists():
        print(f"ERROR: Inno Setup 6 not found at {ISCC_PATH}")
        print("       Download from https://jrsoftware.org/isinfo.php")
        sys.exit(1)


def run_pyinstaller() -> None:
    """Run PyInstaller using the project spec file.

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


def run_inno_setup() -> None:
    """Run the Inno Setup compiler to produce the setup .exe.

    Raises:
        SystemExit: When ISCC exits with a non-zero return code.
    """
    print("=== Step 2: Inno Setup ===")
    result = subprocess.run(
        [str(ISCC_PATH), str(ISS_FILE)],
        cwd=str(SCRIPT_DIR),
    )
    if result.returncode != 0:
        print(f"ERROR: Inno Setup failed (exit {result.returncode})")
        sys.exit(result.returncode)
    print()


def main() -> None:
    """Orchestrate the full installer build."""
    check_prerequisites()
    run_pyinstaller()
    run_inno_setup()
    print(f"Installer ready: {OUTPUT}")


if __name__ == "__main__":
    main()
