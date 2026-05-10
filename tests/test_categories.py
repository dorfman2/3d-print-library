"""Tests for the categories file helpers and on-disk rename / delete actions.

Covers :func:`sort_downloads.load_categories` round-trips and the GUI helpers
``rename_category_folder`` / ``move_category_to_uncategorized`` defined in
:mod:`sort_downloads_app`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import sort_downloads as sd
import sort_downloads_app as sda


# ---------------------------------------------------------------------------
# load_categories / save_categories_dict round-trip
# ---------------------------------------------------------------------------


def test_load_categories_returns_defaults_when_missing(tmp_path: Path) -> None:
    cats = sd.load_categories(tmp_path / "missing.json")
    assert cats == sd.CATEGORY_KEYWORDS


def test_load_categories_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "cats.json"
    payload = {
        "version": 1,
        "categories": [
            {"name": "0 - Test",  "keywords": ["foo", "bar"]},
            {"name": "1 - Other", "keywords": []},
        ],
    }
    p.write_text(json.dumps(payload))

    cats = sd.load_categories(p)

    assert cats == {"0 - Test": ["foo", "bar"], "1 - Other": []}


def test_save_categories_dict_writes_v1_schema(tmp_path: Path) -> None:
    p = tmp_path / "cats.json"
    sda.save_categories_dict({"A": ["x"], "B": ["y", "z"]}, p)
    written = json.loads(p.read_text())
    assert written["version"] == 1
    assert written["categories"][0] == {"name": "A", "keywords": ["x"]}
    assert written["categories"][1] == {"name": "B", "keywords": ["y", "z"]}


def test_save_load_roundtrip_preserves_order(tmp_path: Path) -> None:
    original = {"Z - Last": ["one"], "0 - First": ["two", "three"]}
    p = tmp_path / "cats.json"
    sda.save_categories_dict(original, p)
    assert list(sd.load_categories(p).keys()) == ["Z - Last", "0 - First"]


# ---------------------------------------------------------------------------
# ensure_categories_file
# ---------------------------------------------------------------------------


def test_ensure_categories_file_copies_default(tmp_path: Path) -> None:
    default = tmp_path / "defaults.json"
    default.write_text('{"version": 1, "categories": []}')
    target = tmp_path / "categories.json"

    sda.ensure_categories_file(target=target, default=default)

    assert target.exists()
    assert target.read_text() == default.read_text()


def test_ensure_categories_file_does_not_overwrite_existing(tmp_path: Path) -> None:
    default = tmp_path / "defaults.json"
    default.write_text('{"version": 1, "categories": [{"name": "FROM_DEFAULT", "keywords": []}]}')
    target = tmp_path / "categories.json"
    target.write_text('{"version": 1, "categories": [{"name": "USER_EDITED", "keywords": []}]}')

    sda.ensure_categories_file(target=target, default=default)

    assert "USER_EDITED" in target.read_text()


def test_ensure_categories_file_skips_when_default_missing(tmp_path: Path) -> None:
    target = tmp_path / "categories.json"
    sda.ensure_categories_file(target=target, default=tmp_path / "nope.json")
    assert not target.exists()


# ---------------------------------------------------------------------------
# rename_category_folder
# ---------------------------------------------------------------------------


def test_rename_category_folder_moves_existing_directory(library_root: Path) -> None:
    (library_root / "Old" / "ProjA").mkdir(parents=True)

    sda.rename_category_folder(library_root, "Old", "New")

    assert not (library_root / "Old").exists()
    assert (library_root / "New" / "ProjA").exists()


def test_rename_category_folder_noop_when_source_missing(library_root: Path) -> None:
    """No source dir means there's nothing to do — must not error."""
    sda.rename_category_folder(library_root, "Missing", "Whatever")
    assert not (library_root / "Whatever").exists()


def test_rename_category_folder_raises_on_collision(library_root: Path) -> None:
    (library_root / "Old").mkdir()
    (library_root / "New").mkdir()
    with pytest.raises(FileExistsError):
        sda.rename_category_folder(library_root, "Old", "New")


# ---------------------------------------------------------------------------
# move_category_to_uncategorized
# ---------------------------------------------------------------------------


def test_move_category_to_uncategorized_moves_children(library_root: Path) -> None:
    (library_root / "ToDelete" / "ProjA").mkdir(parents=True)
    (library_root / "ToDelete" / "ProjB").mkdir(parents=True)

    sda.move_category_to_uncategorized(library_root, "ToDelete")

    assert not (library_root / "ToDelete").exists()
    assert (library_root / "Uncategorized" / "ProjA").is_dir()
    assert (library_root / "Uncategorized" / "ProjB").is_dir()


def test_move_category_to_uncategorized_avoids_collisions(library_root: Path) -> None:
    """Existing entries in Uncategorized must not be overwritten."""
    (library_root / "ToDelete" / "ProjA").mkdir(parents=True)
    (library_root / "Uncategorized" / "ProjA").mkdir(parents=True)
    (library_root / "Uncategorized" / "ProjA" / "marker").write_text("keep")

    sda.move_category_to_uncategorized(library_root, "ToDelete")

    assert (library_root / "Uncategorized" / "ProjA" / "marker").read_text() == "keep"
    assert (library_root / "Uncategorized" / "ProjA_2").is_dir()


def test_move_category_to_uncategorized_handles_missing_source(library_root: Path) -> None:
    sda.move_category_to_uncategorized(library_root, "NeverExisted")
    # Must not raise; Uncategorized may or may not have been created
