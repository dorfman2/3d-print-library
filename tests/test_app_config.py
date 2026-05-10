"""Tests for the JSON config loader/saver in :mod:`sort_downloads_app`.

Verifies that older configs (missing the new ``source_dir``/``dest_dir`` keys
introduced in 1.0.0) are upgraded transparently via ``DEFAULT_CONFIG`` merge.
"""

from __future__ import annotations

import json
from pathlib import Path

import sort_downloads_app as sda


def test_load_config_creates_default_file_when_missing(
    tmp_path: Path, monkeypatch,
) -> None:
    cfg_path = tmp_path / "cfg.json"
    monkeypatch.setattr(sda, "CONFIG_PATH", cfg_path)

    cfg = sda.load_config()

    assert cfg["interval_minutes"] == sda.DEFAULT_CONFIG["interval_minutes"]
    assert "source_dir" in cfg
    assert "dest_dir" in cfg
    assert cfg_path.exists()


def test_load_config_preserves_user_values(tmp_path: Path, monkeypatch) -> None:
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps({"interval_minutes": 30, "autostart": True}))
    monkeypatch.setattr(sda, "CONFIG_PATH", cfg_path)

    cfg = sda.load_config()

    assert cfg["interval_minutes"] == 30
    assert cfg["autostart"] is True


def test_load_config_merges_missing_defaults_into_old_config(
    tmp_path: Path, monkeypatch,
) -> None:
    """An old 0.x config (no source_dir/dest_dir) gets the new defaults filled in."""
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps({
        "interval_minutes": 45,
        "autostart": False,
        "last_run": None,
    }))
    monkeypatch.setattr(sda, "CONFIG_PATH", cfg_path)

    cfg = sda.load_config()

    assert cfg["interval_minutes"] == 45         # preserved
    assert cfg["source_dir"]                     # added from DEFAULT_CONFIG
    assert cfg["dest_dir"]


def test_save_config_writes_indented_json(tmp_path: Path, monkeypatch) -> None:
    cfg_path = tmp_path / "cfg.json"
    monkeypatch.setattr(sda, "CONFIG_PATH", cfg_path)

    sda.save_config({"interval_minutes": 10, "autostart": False, "last_run": None,
                     "source_dir": "C:\\src", "dest_dir": "C:\\dst"})

    written = json.loads(cfg_path.read_text())
    assert written["interval_minutes"] == 10
    assert written["source_dir"] == "C:\\src"
