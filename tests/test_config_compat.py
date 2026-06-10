"""Property tests: Config Backwards-Compatibility and Cross-Platform Config Safety.

Property 3: Existing ``sort_downloads_config.json`` files load without error on
either platform; missing keys filled from platform-appropriate defaults.
Validates: Requirements 4.4, 10.1

Property 6: Windows drive-letter paths are detected and reset on macOS;
POSIX paths are detected and reset on Windows.
Validates: Requirements 4.7, 10.1
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import sort_downloads_app as sda


def test_old_config_loads_without_error(tmp_path: Path, monkeypatch) -> None:
    """An old config (missing source_dir/dest_dir) loads and fills defaults."""
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps({
        "interval_minutes": 45,
        "autostart": False,
        "last_run": None,
    }))
    monkeypatch.setattr(sda, "CONFIG_PATH", cfg_path)

    cfg = sda.load_config()

    assert cfg["interval_minutes"] == 45
    assert "source_dir" in cfg
    assert "dest_dir" in cfg


def test_config_with_all_keys_loads_unchanged(tmp_path: Path, monkeypatch) -> None:
    """A complete config preserves all user values."""
    home = str(Path.home())
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps({
        "interval_minutes": 30,
        "autostart": True,
        "last_run": None,
        "source_dir": f"{home}/Downloads",
        "dest_dir": f"{home}/3D Prints",
    }))
    monkeypatch.setattr(sda, "CONFIG_PATH", cfg_path)

    cfg = sda.load_config()

    assert cfg["interval_minutes"] == 30
    assert cfg["autostart"] is True


def test_windows_paths_reset_on_macos(tmp_path: Path, monkeypatch) -> None:
    """Windows drive-letter paths in config are reset to defaults on macOS."""
    if sys.platform != "darwin":
        return  # Only meaningful on macOS

    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps({
        "interval_minutes": 60,
        "autostart": False,
        "last_run": None,
        "source_dir": "C:\\Users\\user\\Downloads",
        "dest_dir": "G:\\3-D Printing\\1 - Objects",
    }))
    monkeypatch.setattr(sda, "CONFIG_PATH", cfg_path)

    cfg = sda.load_config()

    # Paths should be reset to macOS defaults
    assert not cfg["source_dir"].startswith("C:\\")
    assert not cfg["dest_dir"].startswith("G:\\")
    assert cfg["source_dir"] == str(Path.home() / "Downloads")
    assert cfg["dest_dir"] == str(Path.home() / "3D Prints")
    # Non-path keys preserved
    assert cfg["interval_minutes"] == 60


def test_posix_paths_reset_on_windows(tmp_path: Path, monkeypatch) -> None:
    """POSIX paths in config are reset to defaults on Windows."""
    if sys.platform != "win32":
        return  # Only meaningful on Windows

    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps({
        "interval_minutes": 60,
        "autostart": False,
        "last_run": None,
        "source_dir": "/Users/user/Downloads",
        "dest_dir": "/Users/user/3D Prints",
    }))
    monkeypatch.setattr(sda, "CONFIG_PATH", cfg_path)

    cfg = sda.load_config()

    # Paths should be reset to Windows defaults
    assert not cfg["source_dir"].startswith("/")
    assert not cfg["dest_dir"].startswith("/")


def test_cross_platform_reset_only_affects_paths(
    tmp_path: Path, monkeypatch
) -> None:
    """Cross-platform path reset does not affect non-path config keys."""
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps({
        "interval_minutes": 120,
        "autostart": True,
        "last_run": "2025-01-01T00:00:00",
        "source_dir": "C:\\Users\\user\\Downloads" if sys.platform == "darwin" else "/tmp",
        "dest_dir": "G:\\Lib" if sys.platform == "darwin" else "/home/x",
    }))
    monkeypatch.setattr(sda, "CONFIG_PATH", cfg_path)

    cfg = sda.load_config()

    assert cfg["interval_minutes"] == 120
    assert cfg["autostart"] is True
    assert cfg["last_run"] == "2025-01-01T00:00:00"
