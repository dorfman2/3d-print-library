"""
sort_downloads.py - Move 3D print files from Downloads into the organized library.

Scans the Downloads folder for project folders, loose print files, and ZIPs
containing print files. Categorizes each via keyword matching and moves them
into the appropriate category subfolder under the library.

Usage:
    python sort_downloads.py           # Dry run: preview moves, no changes made
    python sort_downloads.py --move    # Execute moves
"""

import argparse
import logging
import re
import shutil
import zipfile
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DOWNLOADS: Path = Path(r"C:\Users\dorfm\Downloads")
LIBRARY_ROOT: Path = Path(r"G:\3-D Printing\1 - Objects")

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

# Noise suffixes stripped from the end of project names.
# Uses a single separator char ([\s_-]) rather than \b because _ is a \w char
# and word boundaries don't fire between _ and letters. The outer (+) lets one
# pass strip multiple stacked tokens, e.g. _v3_FINAL_STL in one shot.
_NOISE: re.Pattern[str] = re.compile(
    r"(?:[\s_-](?:"
    r"v\d+(?:[._]\d+)*"           # v1, v2, v1.0, v1_2
    r"|stl|3mf|obj|step|gcode"    # file-type tags
    r"|final"
    r"|remix(?:ed|of)?"
    r"|by[\s_][a-z0-9_]+"         # "by author"
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
    1. Replace ``_`` and ``-`` with spaces.
    2. Strip trailing noise tokens (version numbers, file-type tags, "final",
       "remix", etc.) in a loop until stable.
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
        >>> clean_name("basic_stringing_test")
        'Basic Stringing Test'
        >>> clean_name("3DBenchy")
        '3DBenchy'
    """
    # Strip noise before replacing separators so patterns like v1_2 still match
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


def collect(downloads: Path) -> list[Candidate]:
    """Scan *downloads* and return all categorised 3D print candidates.

    Identifies project folders, loose print files, and ZIPs containing print
    files. Each candidate is assigned a category and a unique destination path.

    Args:
        downloads: Path to the Downloads folder.

    Returns:
        List of :class:`Candidate` objects, sorted by source name.

    Raises:
        FileNotFoundError: If *downloads* does not exist.
    """
    if not downloads.exists():
        raise FileNotFoundError("Downloads folder not found: %s" % downloads)

    candidates: list[Candidate] = []

    for item in sorted(downloads.iterdir()):
        if item.is_dir():
            if has_print_files(item):
                _add_candidate(candidates, item, item.name, SourceKind.FOLDER)
        elif item.is_file():
            suffix = item.suffix.lower()
            if suffix in PRINT_EXTENSIONS:
                _add_candidate(candidates, item, item.stem, SourceKind.LOOSE_FILE)
            elif suffix in ZIP_EXTENSIONS and zip_contains_print_files(item):
                name = zip_project_name(item)
                _add_candidate(candidates, item, name, SourceKind.ZIP)

    return candidates


def _add_candidate(
    candidates: list[Candidate],
    source: Path,
    name: str,
    kind: SourceKind,
) -> None:
    """Build a Candidate and append it to *candidates*.

    Args:
        candidates: List to append to.
        source: Original path.
        name: Raw project name for keyword matching.
        kind: Source type.
    """
    category = categorize(name)
    cleaned = clean_name(name)
    dest = unique_dest(LIBRARY_ROOT / category / cleaned)
    candidates.append(Candidate(source=source, name=name, clean=cleaned, kind=kind, category=category, dest=dest))


def execute_move(candidate: Candidate) -> None:
    """Move a single candidate into the library.

    - FOLDER: moves the whole directory.
    - LOOSE_FILE: creates a named subfolder and moves the file into it.
    - ZIP: extracts into the destination folder then deletes the ZIP.

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
            # Strip the common top-level folder if one exists
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


def print_plan(candidates: list[Candidate]) -> None:
    """Print a dry-run summary table showing name cleanup and destination.

    Args:
        candidates: Candidates that would be moved.
    """
    if not candidates:
        print("Nothing to move — no 3D print files found in Downloads.")
        return

    print(f"\nFound {len(candidates)} item(s) to move:\n")
    name_col = max(len(c.name) for c in candidates)
    clean_col = max(len(c.clean) for c in candidates)
    for c in candidates:
        tag = "[ZIP]" if c.kind == SourceKind.ZIP else "[DIR]" if c.kind == SourceKind.FOLDER else "[FILE]"
        renamed = f"{c.name:<{name_col}}  ->  {c.clean:<{clean_col}}" if c.name != c.clean else f"{c.name:<{name_col}}     {'':>{clean_col}}"
        print(f"  {tag} {renamed}  [{c.category}]")
    print("\nRun with --move to execute.\n")


def main() -> None:
    """Entry point: parse arguments, collect candidates, dry-run or move."""
    parser = argparse.ArgumentParser(
        description="Move 3D print files from Downloads into the library."
    )
    parser.add_argument(
        "--move",
        action="store_true",
        help="Execute moves (default is dry run).",
    )
    args = parser.parse_args()

    candidates = collect(DOWNLOADS)

    if not args.move:
        print_plan(candidates)
        return

    if not candidates:
        logger.info("Nothing to move.")
        return

    errors: list[tuple[Candidate, Exception]] = []
    for candidate in candidates:
        try:
            execute_move(candidate)
        except OSError as exc:
            logger.error("Failed to move %s: %s", candidate.name, exc)
            errors.append((candidate, exc))

    moved = len(candidates) - len(errors)
    logger.info("Done: %d moved, %d failed.", moved, len(errors))


if __name__ == "__main__":
    main()
