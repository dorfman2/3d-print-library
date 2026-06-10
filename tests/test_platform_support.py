"""Tests for the platform abstraction layer factory and methods.

Verifies get_platform() returns the correct class for the current OS,
raises RuntimeError on unsupported platforms, and returns valid values
for default paths and font.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from platform_support import get_platform


def test_get_platform_returns_correct_class() -> None:
    """Factory returns the correct backend for the running OS."""
    p = get_platform()
    if sys.platform == "win32":
        assert type(p).__name__ == "WindowsBackend"
    elif sys.platform == "darwin":
        assert type(p).__name__ == "DarwinBackend"


def test_get_platform_raises_on_unsupported(monkeypatch) -> None:
    """Factory raises RuntimeError on unsupported platforms."""
    monkeypatch.setattr(sys, "platform", "freebsd")
    with pytest.raises(RuntimeError, match="Unsupported platform: freebsd"):
        get_platform()


def test_default_source_path_returns_valid_path() -> None:
    """default_source_path() returns a Path object."""
    p = get_platform()
    result = p.default_source_path()
    assert isinstance(result, Path)
    assert str(result)  # non-empty


def test_default_library_path_returns_valid_path() -> None:
    """default_library_path() returns a Path object."""
    p = get_platform()
    result = p.default_library_path()
    assert isinstance(result, Path)
    assert str(result)  # non-empty


def test_platform_font_returns_nonempty_string() -> None:
    """platform_font() returns a non-empty font family string."""
    p = get_platform()
    result = p.platform_font()
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.skipif(sys.platform != "darwin", reason="Requires macOS: fcntl")
def test_darwin_lock_acquire_release(tmp_path: Path, monkeypatch) -> None:
    """DarwinBackend can acquire and release a lock using tmp_path."""
    import platform_support._darwin as darwin_mod

    monkeypatch.setattr(darwin_mod, "LOCK_DIR", tmp_path)
    monkeypatch.setattr(darwin_mod, "LOCK_FILE", tmp_path / "instance.lock")

    p = get_platform()
    assert p.acquire_instance_lock() is True
    assert (tmp_path / "instance.lock").exists()
    p.release_instance_lock()


@pytest.mark.skipif(sys.platform != "win32", reason="Requires Windows: winreg")
def test_windows_backend_instantiation() -> None:
    """WindowsBackend can be instantiated on Windows."""
    p = get_platform()
    assert type(p).__name__ == "WindowsBackend"
