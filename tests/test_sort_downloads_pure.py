"""Tests for the pure helpers in :mod:`sort_downloads`.

Covers ``clean_name``, ``categorize``, and ``unique_dest`` — functions that
have no I/O dependency beyond optional filesystem checks via ``tmp_path``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import sort_downloads as sd


# ---------------------------------------------------------------------------
# clean_name
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("raw, expected", [
    ("Ender_3_Fan_Duct_v3_FINAL_STL", "Ender 3 Fan Duct"),
    ("case-for-rak-wisblock-1-watt-starter-kit-model_files",
     "Case for Rak Wisblock 1 Watt Starter Kit"),
    ("3DBenchy", "3DBenchy"),
    ("simple-toy", "Simple Toy"),
    ("Helmet v2", "Helmet"),
    ("planter_final", "Planter"),
    ("nerf-blaster-grip", "Nerf Blaster Grip"),
])
def test_clean_name_examples(raw: str, expected: str) -> None:
    assert sd.clean_name(raw) == expected


def test_clean_name_empty_returns_original() -> None:
    """All-noise without a leading separator is preserved (no leading sep means
    the noise regex doesn't strip), then title-cased word-by-word."""
    # "v1" has no leading separator, so _NOISE doesn't strip it; then it
    # passes through the lowercase-word title-case rule -> "V1".
    assert sd.clean_name("v1") == "V1"


# ---------------------------------------------------------------------------
# categorize
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name, expected", [
    ("Ender 3 Fan Duct", "1 - Machines"),
    ("Toilet Roll Holder", "2 - Home and Household"),
    ("Webcam Mount", "3 - Office"),
    ("Pegboard Tool Holder", "4 - Tools and Organization"),
    ("Raspberry Pi Case", "6 - Electronics"),
    ("Fidget Spinner", "7 - Gifts and Toys"),
    ("Dragon Cosplay Helmet", "15 - Cosplay"),
    ("MultiBoard tile", "11 - MultiBoard"),
    ("Calibration Cube", "0 - Calibration"),
])
def test_categorize_keywords(name: str, expected: str) -> None:
    assert sd.categorize(name) == expected


def test_categorize_no_match_returns_uncategorized() -> None:
    assert sd.categorize("zzz random thing zzz") == "Uncategorized"


def test_categorize_uses_custom_categories_argument() -> None:
    """An explicit categories dict overrides the module-level defaults.

    Keywords are matched after ``categorize`` normalises hyphens/underscores
    to spaces, so test tokens here use plain words to avoid surprises.
    """
    custom = {"X - Test": ["wibble"]}
    assert sd.categorize("Item with wibble here", custom) == "X - Test"
    assert sd.categorize("Ender 3 Fan Duct", custom) == "Uncategorized"


# ---------------------------------------------------------------------------
# unique_dest
# ---------------------------------------------------------------------------


def test_unique_dest_returns_path_when_absent(tmp_path: Path) -> None:
    target = tmp_path / "Foo"
    assert sd.unique_dest(target) == target


def test_unique_dest_increments_when_present(tmp_path: Path) -> None:
    (tmp_path / "Foo").mkdir()
    assert sd.unique_dest(tmp_path / "Foo").name == "Foo_2"


def test_unique_dest_skips_existing_increments(tmp_path: Path) -> None:
    (tmp_path / "Foo").mkdir()
    (tmp_path / "Foo_2").mkdir()
    (tmp_path / "Foo_3").mkdir()
    assert sd.unique_dest(tmp_path / "Foo").name == "Foo_4"
