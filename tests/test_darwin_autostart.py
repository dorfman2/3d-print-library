"""Tests for macOS autostart via Launch Agent plist.

Tests real plist read/write operations using tmp_path. Skipped on Windows.

Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5
"""

from __future__ import annotations

import plistlib
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin", reason="Requires macOS: plistlib/launchd"
)


@pytest.fixture
def darwin_backend(tmp_path: Path, monkeypatch):
    """Create a DarwinBackend with plist paths redirected to tmp_path."""
    import platform_support._darwin as darwin_mod
    from platform_support._darwin import DarwinBackend

    plist_dir = tmp_path / "LaunchAgents"
    monkeypatch.setattr(darwin_mod, "PLIST_DIR", plist_dir)
    monkeypatch.setattr(
        darwin_mod, "PLIST_PATH", plist_dir / "com.3dprintsync.agent.plist"
    )
    # Also redirect lock paths to avoid touching real files
    monkeypatch.setattr(darwin_mod, "LOCK_DIR", tmp_path / "locks")
    monkeypatch.setattr(darwin_mod, "LOCK_FILE", tmp_path / "locks" / "instance.lock")
    return DarwinBackend()


def test_toggle_autostart_writes_valid_plist(
    darwin_backend, tmp_path: Path, monkeypatch
) -> None:
    """toggle_autostart(True, ...) writes a valid plist with correct keys."""
    import platform_support._darwin as darwin_mod

    darwin_backend.toggle_autostart(True, "/usr/local/bin/3DPrintSync")

    plist_path = darwin_mod.PLIST_PATH
    assert plist_path.exists()

    with open(plist_path, "rb") as f:
        data = plistlib.load(f)

    assert data["Label"] == "com.3dprintsync.agent"
    assert data["ProgramArguments"] == ["/usr/local/bin/3DPrintSync", "--minimized"]
    assert data["RunAtLoad"] is True


def test_toggle_autostart_removes_plist(darwin_backend, monkeypatch) -> None:
    """toggle_autostart(False, ...) removes the plist file."""
    import platform_support._darwin as darwin_mod

    # First enable
    darwin_backend.toggle_autostart(True, "/usr/local/bin/3DPrintSync")
    assert darwin_mod.PLIST_PATH.exists()

    # Then disable
    darwin_backend.toggle_autostart(False, "/usr/local/bin/3DPrintSync")
    assert not darwin_mod.PLIST_PATH.exists()


def test_is_autostart_enabled_validation_and_repair(
    darwin_backend, monkeypatch
) -> None:
    """is_autostart_enabled() validates and repairs a corrupted plist."""
    import platform_support._darwin as darwin_mod

    plist_dir = darwin_mod.PLIST_DIR
    plist_dir.mkdir(parents=True, exist_ok=True)
    plist_path = darwin_mod.PLIST_PATH

    # Write a plist with wrong Label
    bad_plist = {
        "Label": "wrong.label",
        "ProgramArguments": ["/usr/local/bin/3DPrintSync", "--minimized"],
        "RunAtLoad": True,
    }
    with open(plist_path, "wb") as f:
        plistlib.dump(bad_plist, f)

    # is_autostart_enabled should repair it
    assert darwin_backend.is_autostart_enabled() is True

    # Verify repair
    with open(plist_path, "rb") as f:
        data = plistlib.load(f)
    assert data["Label"] == "com.3dprintsync.agent"


def test_directory_auto_creation(tmp_path: Path, monkeypatch) -> None:
    """LaunchAgents directory is created when missing."""
    import platform_support._darwin as darwin_mod
    from platform_support._darwin import DarwinBackend

    nested = tmp_path / "new" / "LaunchAgents"
    monkeypatch.setattr(darwin_mod, "PLIST_DIR", nested)
    monkeypatch.setattr(
        darwin_mod, "PLIST_PATH", nested / "com.3dprintsync.agent.plist"
    )
    monkeypatch.setattr(darwin_mod, "LOCK_DIR", tmp_path / "locks")
    monkeypatch.setattr(darwin_mod, "LOCK_FILE", tmp_path / "locks" / "instance.lock")

    backend = DarwinBackend()
    backend.toggle_autostart(True, "/path/to/app")

    assert nested.exists()
    assert (nested / "com.3dprintsync.agent.plist").exists()
