"""Property test: Build Independence.

Verifies Windows and macOS build pipelines share no spec files or installer
scripts. Modifying one cannot break the other.

Validates: Requirements 8.4, 10.2
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_spec_files_share_no_datas_paths() -> None:
    """Windows and macOS spec files reference no overlapping platform artifacts."""
    win_spec = (ROOT / "sort_downloads_app.spec").read_text()
    mac_spec = (ROOT / "sort_downloads_app_macos.spec").read_text()

    # macOS spec must not reference Windows artifacts
    assert "app-icon.ico" not in mac_spec, "macOS spec references Windows .ico"
    assert "pystray._win32" not in mac_spec, "macOS spec references _win32"

    # Windows spec must not reference macOS artifacts
    assert ".icns" not in win_spec, "Windows spec references .icns"
    assert "pystray._darwin" not in win_spec, "Windows spec references _darwin"
    assert "BUNDLE(" not in win_spec, "Windows spec uses BUNDLE (macOS only)"


def test_build_scripts_are_platform_independent() -> None:
    """Windows build script has no macOS artifacts and vice versa."""
    win_build = (ROOT / "build_installer.py").read_text()
    mac_build = (ROOT / "build_installer_macos.py").read_text()

    # Windows build must not reference macOS
    assert "hdiutil" not in win_build
    assert "codesign" not in win_build
    assert ".icns" not in win_build
    assert "_macos.spec" not in win_build

    # macOS build must not reference Windows
    assert "ISCC" not in mac_build
    assert "installer.iss" not in mac_build
    assert ".ico" not in mac_build
    assert "sort_downloads_app.spec" not in mac_build
