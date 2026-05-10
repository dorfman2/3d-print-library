"""Shared pytest fixtures for the 3D Print Sync test suite.

All fixtures use real files on the temporary filesystem (per project rules
``no mock/patch``).  Project root is prepended to ``sys.path`` so that tests
can import ``sort_downloads`` and ``sort_downloads_app`` directly.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import pytest

ROOT: Path = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def library_root(tmp_path: Path) -> Path:
    """Create and return an empty library root directory inside ``tmp_path``."""
    root = tmp_path / "library"
    root.mkdir()
    return root


@pytest.fixture
def downloads(tmp_path: Path) -> Path:
    """Create and return an empty downloads directory inside ``tmp_path``."""
    d = tmp_path / "downloads"
    d.mkdir()
    return d


@pytest.fixture
def make_zip(tmp_path: Path):
    """Factory fixture: build a real ZIP archive at *path* with given members.

    Returns a callable ``(path: Path, members: dict[str, bytes]) -> Path`` where
    *members* maps archive-internal paths (use forward slashes) to byte
    content.
    """

    def _make(path: Path, members: dict[str, bytes]) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path, "w") as zf:
            for arcname, data in members.items():
                zf.writestr(arcname, data)
        return path

    return _make
