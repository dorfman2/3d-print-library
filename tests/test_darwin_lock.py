"""Tests for macOS single-instance guard (DarwinBackend lock).

Tests real lock file operations using tmp_path. Skipped on Windows.

Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin", reason="Requires macOS: fcntl"
)


@pytest.fixture
def darwin_backend(tmp_path: Path, monkeypatch):
    """Create a DarwinBackend with lock paths redirected to tmp_path."""
    import platform_support._darwin as darwin_mod
    from platform_support._darwin import DarwinBackend

    monkeypatch.setattr(darwin_mod, "LOCK_DIR", tmp_path)
    monkeypatch.setattr(darwin_mod, "LOCK_FILE", tmp_path / "instance.lock")
    return DarwinBackend()


def test_lock_acquisition_succeeds(darwin_backend) -> None:
    """First lock acquisition should succeed."""
    assert darwin_backend.acquire_instance_lock() is True


def test_lock_prevents_second_acquisition(darwin_backend, tmp_path: Path) -> None:
    """A second backend instance cannot acquire the lock while the first holds it."""
    import platform_support._darwin as darwin_mod
    from platform_support._darwin import DarwinBackend

    # First acquire succeeds
    assert darwin_backend.acquire_instance_lock() is True

    # Second backend attempt should fail
    backend2 = DarwinBackend()
    assert backend2.acquire_instance_lock() is False


def test_stale_lock_detection(darwin_backend, tmp_path: Path) -> None:
    """A stale lock file (dead PID) is reclaimed."""
    import platform_support._darwin as darwin_mod

    lock_file = darwin_mod.LOCK_FILE
    # Write a dead PID
    lock_file.write_text("999999999")

    assert darwin_backend.acquire_instance_lock() is True


def test_release_removes_lock_file(darwin_backend, tmp_path: Path) -> None:
    """release_instance_lock removes the lock file."""
    import platform_support._darwin as darwin_mod

    darwin_backend.acquire_instance_lock()
    assert darwin_mod.LOCK_FILE.exists()
    darwin_backend.release_instance_lock()
    assert not darwin_mod.LOCK_FILE.exists()


def test_directory_auto_creation(tmp_path: Path, monkeypatch) -> None:
    """Lock directory is created automatically when missing."""
    import platform_support._darwin as darwin_mod
    from platform_support._darwin import DarwinBackend

    nested = tmp_path / "nested" / "dir"
    monkeypatch.setattr(darwin_mod, "LOCK_DIR", nested)
    monkeypatch.setattr(darwin_mod, "LOCK_FILE", nested / "instance.lock")

    backend = DarwinBackend()
    assert backend.acquire_instance_lock() is True
    assert nested.exists()
    backend.release_instance_lock()
