"""
sort_downloads.py - Move 3D print files from Downloads into the organized library.

Implements five phases:
  1. Pre-process Downloads ZIPs — collapse ZIP + extracted-folder duplicates.
  2. Build library index — collect cleaned names of all existing library projects.
  3. Collect and categorise candidates — identify items to move, skip duplicates.
  4. Move to library — execute moves and log results.
  5. Clean library ZIPs — extract and remove any ZIPs that landed in the library.

Usage:
    python sort_downloads.py           # Dry run: preview all phases, no changes
    python sort_downloads.py --move    # Execute all phases
"""

import argparse
import logging
import re
import shutil
import zipfile
from dataclasses import dataclass
from enum import Enum, auto
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import NamedTuple

logger = logging.getLogger(__name__)

SCRIPT_DIR: Path = Path(__file__).parent
DOWNLOADS: Path = Path(r"C:\Users\dorfm\Downloads")
LIBRARY_ROOT: Path = Path(r"G:\3-D Printing\1 - Objects")
LOG_PATH: Path = SCRIPT_DIR / "sort_downloads.log"

PRINT_EXTENSIONS: frozenset[str] = frozenset({
    ".stl", ".3mf", ".obj", ".step", ".stp",
    ".f3d", ".f3z", ".amf", ".gcode", ".bgcode", ".gco",
})

ZIP_EXTENSIONS: frozenset[str] = frozenset({".zip"})

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "0 - Calibration": [
        "calibration", "calibrate", "benchy", "benchmark",
        "stringing", "overhang", "retraction", "ironing", "tolerance",
        "first layer", "flow rate", "temp tower", "temperature tower",
    ],
    "1 - Machines": [
        "ender", "prusa", "bambu", "creality", "voron", "ratrig",
        "extruder", "hotend", "hot end", "fan duct", "bowden",
        "filament", "nozzle", "heatbreak", "heat break", "bed level",
        "klipper", "marlin", "x1c", "p1s", "a1 mini", "core one",
        "print head", "carriage", "idler", "tensioner",
    ],
    "2 - Home and Household": [
        "kitchen", "bathroom", "planter", "vase", "hook",
        "curtain", "shelf", "door", "toilet", "soap", "toothbrush",
        "towel", "cabinet", "drawer", "furniture",
        "musubi", "sushi", "press", "food", "bento",
    ],
    "3 - Office": [
        "desk", "monitor", "keyboard", "phone stand", "cable",
        "webcam", "speaker", "headphone", "headset", "pen holder",
        "office", "laptop", "tablet", "mousepad",
    ],
    "4 - Tools and Organization": [
        "tool", "wrench", "screwdriver", "storage", "bin",
        "organizer", "pegboard", "peg board", "workshop", "drill",
        "clamp", "jig", "fixture", "workbench", "tray", "sorter",
    ],
    "5 - Repairs and Replacements": [
        "repair", "replacement", "replace", "spare part",
        "bracket", "clip", "snap", "latch",
    ],
    "6 - Electronics": [
        "raspberry pi", "arduino", "esp32", "esp8266",
        "electronics", "iot", "enclosure", "pcb", "sensor",
        "relay", "wemos", "pi zero", "rpi",
        "rak", "wisblock", "heltec", "seeed", "meshtastic",
        "lora", "lorawan", "tracker", "gateway", "t1000", "holster",
    ],
    "7 - Gifts and Toys": [
        "gift", "toy", "fidget", "novelty",
        "kids", "children", "spinner", "puzzle",
    ],
    "8 - Models and Display": [
        "model", "display", "sculpture", "bust", "figurine",
        "decorative", "statue", "diorama",
    ],
    "9 - Tabletop": [
        "tabletop", "dungeon", "terrain", "dnd", "d&d", "warhammer",
        "40k", "pathfinder", "rpg", "scenery", "tiles", "scatter",
    ],
    "10 - RC Flight": [
        "drone", "quadcopter", "fpv", "rc car", "rc truck",
        "remote control", "traxxas", "losi", "arrma",
    ],
    "11 - MultiBoard": [
        "multiboard", "multi-board", "multi board",
    ],
    "12 - MMU": [
        "mmu", "multi material", "multimaterial", "ams", "purge tower",
    ],
    "13 - NERF": [
        "nerf", "blaster", "dart",
    ],
    "14 - Legos": [
        "lego", "legos", "moc", "technic", "duplo",
    ],
    "15 - Cosplay": [
        "cosplay", "costume", "prop", "armor", "helmet",
        "sword", "shield", "gauntlet",
    ],
}

# Noise tokens stripped from the end of project names before separator replacement.
# Uses [\s_-] rather than \b because _ is a \w char — word boundaries don't fire
# between _ and letters. The outer (+) strips multiple stacked tokens in one pass.
_NOISE: re.Pattern[str] = re.compile(
    r"(?:[\s_-](?:"
    r"v\d+(?:[._]\d+)*"             # v1, v2, v1.0, v1_2
    r"|stl|3mf|obj|step|gcode"      # file-type tags
    r"|model[\s_-]?files?"          # model_files, model-files, model files
    r"|files?"                       # bare _files suffix
    r"|final"
    r"|remix(?:ed|of)?"
    r"|by[\s_][a-z0-9_]+"           # "by author"
    r"|print(?:ed|able)?"
    r"|update[d]?|fix(?:ed)?"
    r"|free|paid"
    r"))+\s*$",
    re.IGNORECASE,
)

_SMALL_WORDS: frozenset[str] = frozenset({
    "a", "an", "and", "as", "at", "but", "by", "for",
    "in", "nor", "of", "on", "or", "the", "to",
})


class SourceKind(Enum):
    """Type of source item found in the Downloads folder."""

    FOLDER = auto()
    LOOSE_FILE = auto()
    ZIP = auto()


@dataclass
class Candidate:
    """A 3D print item found in Downloads, ready for categorization and moving.

    Attributes:
        source: Original path in Downloads.
        name: Raw project name used for keyword matching.
        clean: Human-readable name used for the destination folder.
        kind: Whether this is a folder, loose file, or ZIP.
        category: Resolved library category folder name.
        dest: Full destination path in the library.
    """

    source: Path
    name: str
    clean: str
    kind: SourceKind
    category: str
    dest: Path


class Phase1Action(NamedTuple):
    """A planned or executed action from Phase 1 (Downloads ZIP pre-processing).

    Attributes:
        action: ``'DELETE-ZIP'`` or ``'EXTRACT'``.
        zip_path: Path to the ZIP file.
        folder_path: Stem folder that exists (DELETE-ZIP) or will be created (EXTRACT).
    """

    action: str
    zip_path: Path
    folder_path: Path


def has_print_files(path: Path) -> bool:
    """Return True if *path* contains any 3D print file (recursive).

    Args:
        path: Directory to search.

    Returns:
        True if at least one file with a recognised print extension exists.
    """
    return any(
        child.suffix.lower() in PRINT_EXTENSIONS
        for child in path.rglob("*")
        if child.is_file()
    )


def categorize(name: str) -> str:
    """Assign a library category to *name* via keyword scoring.

    Normalises *name* to lowercase with spaces, counts keyword hits per
    category, and returns the highest-scoring category. Returns
    ``'Uncategorized'`` when no keywords match.

    Args:
        name: Project folder name or file stem.

    Returns:
        Category folder name, e.g. ``'3 - Office'``, or ``'Uncategorized'``.
    """
    normalized = name.lower().replace("_", " ").replace("-", " ")
    scores: dict[str, int] = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in normalized)
        if score > 0:
            scores[category] = score
    if not scores:
        return "Uncategorized"
    return max(scores, key=lambda c: scores[c])


def unique_dest(path: Path) -> Path:
    """Return *path* unchanged if it does not exist, else append ``_2``, ``_3``, …

    Args:
        path: Desired destination path.

    Returns:
        A path guaranteed not to already exist on the filesystem.
    """
    if not path.exists():
        return path
    counter = 2
    while True:
        candidate = path.with_name(f"{path.name}_{counter}")
        if not candidate.exists():
            return candidate
        counter += 1


def clean_name(name: str) -> str:
    """Return a human-readable version of a raw project name.

    Applies these transforms in order:
    1. Strip trailing noise tokens (version numbers, file-type tags, ``final``,
       ``remix``, ``model_files``, etc.) before replacing separators — so patterns
       like ``v1_2`` are matched before ``_`` becomes a space.
    2. Replace ``_`` and ``-`` with spaces.
    3. Collapse repeated whitespace.
    4. Title-case each word that is fully lowercase, leaving mixed-case words
       (e.g. ``3DBenchy``, ``RPi``) and acronyms (e.g. ``NERF``) untouched.
    5. Downcase small conjunctions/prepositions that are not the first word.

    Args:
        name: Raw folder name or file stem.

    Returns:
        Cleaned name, or the original *name* if cleaning produces an empty string.

    Examples:
        >>> clean_name("Ender_3_Fan_Duct_v3_FINAL_STL")
        'Ender 3 Fan Duct'
        >>> clean_name("case-for-rak-wisblock-1-watt-starter-kit-model_files")
        'Case for Rak Wisblock 1 Watt Starter Kit'
        >>> clean_name("3DBenchy")
        '3DBenchy'
    """
    s = name
    prev: str | None = None
    while prev != s:
        prev = s
        s = _NOISE.sub("", s).strip()
    s = s.replace("_", " ").replace("-", " ")
    s = re.sub(r"\s+", " ", s).strip()
    if not s:
        return name
    words = s.split()
    result: list[str] = []
    for i, word in enumerate(words):
        if word.islower():
            word = word[0].upper() + word[1:]
        if i > 0 and word.lower() in _SMALL_WORDS and word == word.capitalize():
            word = word.lower()
        result.append(word)
    return " ".join(result)


def zip_contains_print_files(zip_path: Path) -> bool:
    """Return True if the ZIP archive contains at least one print file.

    Args:
        zip_path: Path to the ZIP file.

    Returns:
        True if a recognised print extension is found among the ZIP members.
    """
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            return any(
                Path(name).suffix.lower() in PRINT_EXTENSIONS
                for name in zf.namelist()
            )
    except zipfile.BadZipFile:
        logger.warning("Skipping bad ZIP: %s", zip_path.name)
        return False


def zip_project_name(zip_path: Path) -> str:
    """Infer a project name from a ZIP's contents.

    If all members share a common top-level folder, that folder name is used.
    Otherwise the ZIP file stem is used.

    Args:
        zip_path: Path to the ZIP file.

    Returns:
        Project name string.
    """
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            top_dirs = {Path(name).parts[0] for name in zf.namelist() if name}
            if len(top_dirs) == 1:
                return top_dirs.pop()
    except zipfile.BadZipFile:
        pass
    return zip_path.stem


def extract_zip_flat(zip_path: Path, dest_dir: Path) -> None:
    """Extract a ZIP into *dest_dir* / zip_path.stem, stripping any common root.

    If all ZIP members share a single top-level directory, that prefix is
    stripped and files land directly in *dest_dir* / zip_path.stem.  Otherwise
    the ZIP is extracted as-is into that folder.  Existing files are skipped.

    Args:
        zip_path: Path to the source ZIP archive.
        dest_dir: Directory that will contain the new project subfolder.
    """
    target = dest_dir / zip_path.stem
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        members = zf.namelist()
        top_dirs = {Path(m).parts[0] for m in members if m}
        if len(top_dirs) == 1:
            prefix = top_dirs.pop() + "/"
            for member in members:
                if member.startswith(prefix) and not member.endswith("/"):
                    rel = member[len(prefix):]
                    if not rel:
                        continue
                    out = target / rel
                    if out.exists():
                        continue
                    out.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as src, open(out, "wb") as dst:
                        shutil.copyfileobj(src, dst)
        else:
            for member in members:
                if member.endswith("/"):
                    continue
                out = target / member
                if out.exists():
                    continue
                out.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as src, open(out, "wb") as dst:
                    shutil.copyfileobj(src, dst)


# ---------------------------------------------------------------------------
# Phase 1
# ---------------------------------------------------------------------------

def preprocess_downloads_zips(downloads: Path, dry_run: bool) -> list[Phase1Action]:
    """Phase 1 — remove or extract ZIP files in the Downloads root.

    For each ZIP that contains print files:
    - If a folder with the same stem already exists alongside it → delete ZIP.
    - Otherwise → extract the ZIP in-place, then delete it.

    Args:
        downloads: Path to the Downloads folder.
        dry_run: When True, log planned actions but make no filesystem changes.

    Returns:
        List of :class:`Phase1Action` describing each ZIP processed.
    """
    actions: list[Phase1Action] = []
    for item in sorted(downloads.iterdir()):
        if not item.is_file() or item.suffix.lower() not in ZIP_EXTENSIONS:
            continue
        if not zip_contains_print_files(item):
            continue
        stem_folder = downloads / item.stem
        if stem_folder.exists():
            actions.append(Phase1Action("DELETE-ZIP", item, stem_folder))
            if not dry_run:
                item.unlink()
                logger.info("Deleted redundant ZIP: %s", item.name)
        else:
            actions.append(Phase1Action("EXTRACT", item, stem_folder))
            if not dry_run:
                extract_zip_flat(item, downloads)
                item.unlink()
                logger.info("Extracted and removed ZIP: %s", item.name)
    return actions


# ---------------------------------------------------------------------------
# Phase 2
# ---------------------------------------------------------------------------

def build_library_index(library: Path) -> set[str]:
    """Phase 2 — collect cleaned names of all existing library projects.

    Scans ``library/*/*`` (category / project) and returns the cleaned name of
    every project folder as a set, used for duplicate detection in Phase 3.

    Args:
        library: Path to the library root (``LIBRARY_ROOT``).

    Returns:
        Set of cleaned project names already in the library.
    """
    index: set[str] = set()
    if not library.exists():
        return index
    for category in library.iterdir():
        if not category.is_dir():
            continue
        for project in category.iterdir():
            if project.is_dir():
                index.add(clean_name(project.name))
    return index


# ---------------------------------------------------------------------------
# Phase 3
# ---------------------------------------------------------------------------

def collect(
    downloads: Path,
    library_index: set[str],
) -> tuple[list[Candidate], list[str]]:
    """Phase 3 — scan Downloads and return categorised candidates plus skips.

    Identifies project folders, loose print files, and ZIPs containing print
    files. Checks each against *library_index* to skip duplicates. Each
    non-duplicate is assigned a category and a unique destination path.

    Args:
        downloads: Path to the Downloads folder.
        library_index: Set of cleaned names already in the library (Phase 2).

    Returns:
        A tuple of (candidates, skipped_names) where *candidates* is a list of
        :class:`Candidate` objects sorted by source name and *skipped_names* is
        a list of raw source names that were already in the library.

    Raises:
        FileNotFoundError: If *downloads* does not exist.
    """
    if not downloads.exists():
        raise FileNotFoundError("Downloads folder not found: %s" % downloads)

    candidates: list[Candidate] = []
    skipped: list[str] = []

    for item in sorted(downloads.iterdir()):
        if item.is_dir():
            if has_print_files(item):
                _add_candidate(candidates, skipped, item, item.name, SourceKind.FOLDER, library_index)
        elif item.is_file():
            suffix = item.suffix.lower()
            if suffix in PRINT_EXTENSIONS:
                _add_candidate(candidates, skipped, item, item.stem, SourceKind.LOOSE_FILE, library_index)
            elif suffix in ZIP_EXTENSIONS and zip_contains_print_files(item):
                name = zip_project_name(item)
                _add_candidate(candidates, skipped, item, name, SourceKind.ZIP, library_index)

    return candidates, skipped


def _add_candidate(
    candidates: list[Candidate],
    skipped: list[str],
    source: Path,
    name: str,
    kind: SourceKind,
    library_index: set[str],
) -> None:
    """Build a Candidate or record a skip, then append to the appropriate list.

    Args:
        candidates: List to append non-duplicate candidates to.
        skipped: List to append duplicate source names to.
        source: Original path.
        name: Raw project name for keyword matching.
        kind: Source type.
        library_index: Set of cleaned names already in the library.
    """
    cleaned = clean_name(name)
    if cleaned in library_index:
        skipped.append(name)
        return
    category = categorize(name)
    dest = unique_dest(LIBRARY_ROOT / category / cleaned)
    candidates.append(Candidate(source=source, name=name, clean=cleaned, kind=kind, category=category, dest=dest))


# ---------------------------------------------------------------------------
# Phase 4
# ---------------------------------------------------------------------------

def execute_move(candidate: Candidate) -> None:
    """Phase 4 — move a single candidate into the library.

    - FOLDER: moves the whole directory.
    - LOOSE_FILE: creates a named subfolder and moves the file into it.
    - ZIP: extracts into the destination folder, then deletes the ZIP.

    Args:
        candidate: The candidate to move.

    Raises:
        OSError: If the move or extraction fails.
    """
    candidate.dest.parent.mkdir(parents=True, exist_ok=True)

    if candidate.kind == SourceKind.FOLDER:
        shutil.move(str(candidate.source), str(candidate.dest))

    elif candidate.kind == SourceKind.LOOSE_FILE:
        candidate.dest.mkdir(parents=True, exist_ok=True)
        shutil.move(str(candidate.source), str(candidate.dest / candidate.source.name))

    elif candidate.kind == SourceKind.ZIP:
        candidate.dest.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(candidate.source, "r") as zf:
            members = zf.namelist()
            top_dirs = {Path(m).parts[0] for m in members if m}
            if len(top_dirs) == 1:
                prefix = top_dirs.pop() + "/"
                for member in members:
                    if member.startswith(prefix) and not member.endswith("/"):
                        rel = member[len(prefix):]
                        if rel:
                            target = candidate.dest / rel
                            target.parent.mkdir(parents=True, exist_ok=True)
                            with zf.open(member) as src, open(target, "wb") as dst:
                                shutil.copyfileobj(src, dst)
            else:
                zf.extractall(candidate.dest)
        candidate.source.unlink()

    logger.info("Moved '%s'  ->  %s / %s", candidate.source.name, candidate.category, candidate.clean)


# ---------------------------------------------------------------------------
# Phase 5
# ---------------------------------------------------------------------------

def clean_library_zips(library: Path, dry_run: bool) -> list[Path]:
    """Phase 5 — extract and remove all ZIP files remaining in the library tree.

    For each ZIP found under *library* that contains print files: extract its
    contents into the ZIP's parent directory (skipping files that already exist),
    then delete the ZIP.

    Args:
        library: Path to the library root (``LIBRARY_ROOT``).
        dry_run: When True, log planned actions but make no filesystem changes.

    Returns:
        List of ZIP paths that were (or would be) processed.
    """
    found: list[Path] = []
    for zip_path in sorted(library.rglob("*.zip")):
        if not zip_contains_print_files(zip_path):
            continue
        found.append(zip_path)
        if not dry_run:
            extract_zip_flat(zip_path, zip_path.parent)
            zip_path.unlink()
            logger.info("Extracted library ZIP: %s", zip_path)
    return found


# ---------------------------------------------------------------------------
# Dry-run output
# ---------------------------------------------------------------------------

def print_plan(
    phase1_actions: list[Phase1Action],
    candidates: list[Candidate],
    skipped: list[str],
    lib_zips: list[Path],
) -> None:
    """Print a structured dry-run summary of all five phases.

    Args:
        phase1_actions: Actions planned for Phase 1 (Downloads ZIP cleanup).
        candidates: Items that would be moved to the library (Phase 3).
        skipped: Raw names skipped as duplicates (Phase 3).
        lib_zips: Library ZIPs that would be extracted (Phase 5).
    """
    # Phase 1
    print("\n=== Phase 1: Downloads ZIPs ===")
    if phase1_actions:
        for act in phase1_actions:
            if act.action == "DELETE-ZIP":
                print(f"  [DELETE-ZIP] {act.zip_path.name}  (folder already extracted)")
            else:
                print(f"  [EXTRACT]    {act.zip_path.name}  ->  {act.folder_path.name}/")
    else:
        print("  (no print ZIPs found in Downloads)")

    # Phase 3
    print("\n=== Phase 3: Import to Library ===")
    if not candidates and not skipped:
        print("  (nothing to import)")
    else:
        name_col = max(
            (len(c.name) for c in candidates),
            default=0,
        )
        name_col = max(name_col, *(len(s) for s in skipped), 0)
        for name in skipped:
            print(f"  [SKIP-DUP]  {name:<{name_col}}  (already in library)")
        for c in candidates:
            tag = "[DIR] " if c.kind == SourceKind.FOLDER else "[FILE]" if c.kind == SourceKind.LOOSE_FILE else "[ZIP] "
            arrow = f"-> {c.clean}" if c.name != c.clean else ""
            print(f"  {tag}  {c.name:<{name_col}}  {arrow}  [{c.category}]")

    # Phase 5
    print("\n=== Phase 5: Library ZIP Cleanup ===")
    if lib_zips:
        for zp in lib_zips:
            try:
                rel = zp.relative_to(LIBRARY_ROOT.parent)
            except ValueError:
                rel = zp
            print(f"  [ZIP] {rel}")
    else:
        print("  (no ZIPs in library)")

    print("\nRun with --move to execute.\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _setup_logging() -> None:
    """Configure root logger with a console handler and a 5 MB rotating file handler.

    The file rotates at 5 MB and keeps one backup (up to 10 MB total on disk).
    Both handlers share the same timestamped format; the console uses a shorter
    format to stay readable in terminal output.
    """
    root = logging.getLogger()
    if root.handlers:
        return  # Already configured (e.g. called twice)
    root.setLevel(logging.INFO)

    file_fmt = logging.Formatter("%(asctime)s %(levelname)-8s %(name)s %(message)s")
    console_fmt = logging.Formatter("%(levelname)s %(message)s")

    fh = RotatingFileHandler(
        LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=1, encoding="utf-8"
    )
    fh.setFormatter(file_fmt)
    root.addHandler(fh)

    sh = logging.StreamHandler()
    sh.setFormatter(console_fmt)
    root.addHandler(sh)


# ---------------------------------------------------------------------------

def run(move: bool = True) -> None:
    """Execute all five phases programmatically.

    Called directly by the frozen GUI app (``sort_downloads_app.exe``) so it can
    invoke the sync without launching a subprocess.  Also used by ``main()`` after
    argument parsing.

    Args:
        move: When ``True`` (default) execute all phases for real.
              When ``False`` perform a dry-run and print the plan to stdout.
    """
    _setup_logging()
    dry_run = not move

    # Phase 1
    phase1_actions = preprocess_downloads_zips(DOWNLOADS, dry_run=dry_run)

    # Phase 2
    library_index = build_library_index(LIBRARY_ROOT)

    # Phase 3
    candidates, skipped = collect(DOWNLOADS, library_index)

    # Phase 5 preview (needed for dry-run output regardless of mode)
    lib_zips = clean_library_zips(LIBRARY_ROOT, dry_run=True)

    if dry_run:
        print_plan(phase1_actions, candidates, skipped, lib_zips)
        return

    # Phase 4 — execute moves
    if not candidates:
        logger.info("Nothing to move.")
    else:
        errors: list[tuple[Candidate, Exception]] = []
        for candidate in candidates:
            try:
                execute_move(candidate)
            except OSError as exc:
                logger.error("Failed to move %s: %s", candidate.name, exc)
                errors.append((candidate, exc))
        moved = len(candidates) - len(errors)
        logger.info("Done: %d moved, %d failed.", moved, len(errors))

    for name in skipped:
        logger.info("Skipped (duplicate): %s", name)

    # Phase 5 — clean library ZIPs
    clean_library_zips(LIBRARY_ROOT, dry_run=False)


def main() -> None:
    """CLI entry point: parse ``--move`` flag and delegate to :func:`run`.

    Raises:
        SystemExit: On argument parsing errors (standard argparse behaviour).
    """
    _setup_logging()
    parser = argparse.ArgumentParser(
        description="Move 3D print files from Downloads into the library."
    )
    parser.add_argument(
        "--move",
        action="store_true",
        help="Execute moves (default is dry run).",
    )
    args = parser.parse_args()
    run(move=args.move)


if __name__ == "__main__":
    main()
