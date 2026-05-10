"""End-to-end tests for the five sync phases in :mod:`sort_downloads`.

Uses real files and ZIP archives on the temporary filesystem (no mocks).
Each test calls :func:`sort_downloads.run` with explicit ``downloads`` and
``library_root`` paths so the module-level constants are not touched.
"""

from __future__ import annotations

from pathlib import Path

import sort_downloads as sd


# ---------------------------------------------------------------------------
# Phase 1 — Downloads ZIP pre-processing
# ---------------------------------------------------------------------------


def test_phase1_extracts_zip_when_no_sibling_folder(downloads: Path, make_zip) -> None:
    zip_path = downloads / "calibration-cube.zip"
    make_zip(zip_path, {"calibration-cube/cube.stl": b"solid empty"})

    actions = sd.preprocess_downloads_zips(downloads, dry_run=False)

    assert not zip_path.exists(), "ZIP should be removed after extraction"
    assert (downloads / "calibration-cube" / "cube.stl").exists()
    assert any(a.action == "EXTRACT" for a in actions)


def test_phase1_deletes_redundant_zip_when_folder_exists(downloads: Path, make_zip) -> None:
    zip_path = downloads / "fan-duct.zip"
    make_zip(zip_path, {"fan-duct/duct.stl": b"solid"})
    # Pre-create the sibling folder (containing print files) so phase 1 deletes the ZIP.
    folder = downloads / "fan-duct"
    folder.mkdir()
    (folder / "duct.stl").write_bytes(b"solid")

    actions = sd.preprocess_downloads_zips(downloads, dry_run=False)

    assert not zip_path.exists()
    assert any(a.action == "DELETE-ZIP" for a in actions)


def test_phase1_dry_run_makes_no_changes(downloads: Path, make_zip) -> None:
    zip_path = downloads / "thing.zip"
    make_zip(zip_path, {"thing/x.stl": b"solid"})

    sd.preprocess_downloads_zips(downloads, dry_run=True)

    assert zip_path.exists(), "Dry run must leave ZIPs alone"
    assert not (downloads / "thing").exists()


# ---------------------------------------------------------------------------
# Phase 2 — library index
# ---------------------------------------------------------------------------


def test_build_library_index_collects_clean_names(library_root: Path) -> None:
    (library_root / "1 - Machines" / "Ender_3_Fan_Duct").mkdir(parents=True)
    (library_root / "Uncategorized" / "Mystery").mkdir(parents=True)

    index = sd.build_library_index(library_root)

    assert "Ender 3 Fan Duct" in index
    assert "Mystery" in index


def test_build_library_index_handles_missing_root(tmp_path: Path) -> None:
    assert sd.build_library_index(tmp_path / "missing") == set()


# ---------------------------------------------------------------------------
# End-to-end run() — Phases 1 + 2 + 3 + 4 together
# ---------------------------------------------------------------------------


def test_run_moves_loose_stl_to_matching_category(
    downloads: Path, library_root: Path,
) -> None:
    (downloads / "Ender 3 Fan Duct.stl").write_bytes(b"solid empty\nendsolid empty\n")

    sd.run(move=True, downloads=downloads, library_root=library_root)

    target = library_root / "1 - Machines" / "Ender 3 Fan Duct" / "Ender 3 Fan Duct.stl"
    assert target.exists()
    assert not (downloads / "Ender 3 Fan Duct.stl").exists()


def test_run_extracts_zip_with_print_files(
    downloads: Path, library_root: Path, make_zip,
) -> None:
    zip_path = downloads / "dragon-cosplay-helmet.zip"
    make_zip(zip_path, {"dragon-cosplay-helmet/helmet.stl": b"solid"})

    sd.run(move=True, downloads=downloads, library_root=library_root)

    target = library_root / "15 - Cosplay" / "Dragon Cosplay Helmet" / "helmet.stl"
    assert target.exists()
    assert not zip_path.exists()


def test_run_skips_duplicates_already_in_library(
    downloads: Path, library_root: Path,
) -> None:
    # Existing project in the library
    (library_root / "1 - Machines" / "Ender 3 Fan Duct").mkdir(parents=True)
    # Same project showing up in Downloads
    src = downloads / "Ender 3 Fan Duct"
    src.mkdir()
    (src / "duct.stl").write_bytes(b"solid")

    sd.run(move=True, downloads=downloads, library_root=library_root)

    assert src.exists(), "Duplicate should be left in Downloads, not moved"


def test_run_routes_unknown_to_uncategorized(
    downloads: Path, library_root: Path,
) -> None:
    (downloads / "zzz mystery thing.stl").write_bytes(b"solid")

    sd.run(move=True, downloads=downloads, library_root=library_root)

    assert (
        library_root / "Uncategorized" / "Zzz Mystery Thing" / "zzz mystery thing.stl"
    ).exists()


def test_run_uses_custom_categories_file(
    downloads: Path, library_root: Path, tmp_path: Path,
) -> None:
    """A custom categories.json overrides the bundled defaults end-to-end."""
    import json
    cats = tmp_path / "cats.json"
    cats.write_text(json.dumps({
        "version": 1,
        "categories": [
            {"name": "X - Custom", "keywords": ["wibble"]},
        ],
    }))

    (downloads / "wibble plate.stl").write_bytes(b"solid")
    sd.run(
        move=True,
        downloads=downloads,
        library_root=library_root,
        categories_path=cats,
    )

    assert (library_root / "X - Custom" / "Wibble Plate" / "wibble plate.stl").exists()


# ---------------------------------------------------------------------------
# Phase 5 — clean_library_zips
# ---------------------------------------------------------------------------


def test_clean_library_zips_extracts_and_deletes(
    library_root: Path, make_zip,
) -> None:
    project = library_root / "9 - Tabletop" / "DragonProject"
    project.mkdir(parents=True)
    zp = project / "models.zip"
    make_zip(zp, {"models/dragon.stl": b"solid"})

    extracted = sd.clean_library_zips(library_root, dry_run=False)

    assert zp in extracted
    assert not zp.exists()
    assert (project / "models" / "dragon.stl").exists()


def test_clean_library_zips_dry_run_makes_no_changes(
    library_root: Path, make_zip,
) -> None:
    project = library_root / "9 - Tabletop" / "DragonProject"
    project.mkdir(parents=True)
    zp = project / "models.zip"
    make_zip(zp, {"models/dragon.stl": b"solid"})

    sd.clean_library_zips(library_root, dry_run=True)

    assert zp.exists()
