"""macOS-specific platform backend implementation.

Provides single-instance guard via fcntl advisory locks, autostart via
launchd plist, file-open via subprocess open, and macOS-appropriate defaults.

All platform-specific imports (fcntl, plistlib) are inside methods or the
class body, never at module level.
"""

import logging
import os
import subprocess
from pathlib import Path
from typing import IO

from platform_support._base import PlatformBackend

logger = logging.getLogger(__name__)

LOCK_DIR: Path = Path.home() / "Library" / "Application Support" / "3DPrintSync"
LOCK_FILE: Path = LOCK_DIR / "instance.lock"
PLIST_LABEL: str = "com.3dprintsync.agent"
PLIST_DIR: Path = Path.home() / "Library" / "LaunchAgents"
PLIST_PATH: Path = PLIST_DIR / f"{PLIST_LABEL}.plist"


class DarwinBackend(PlatformBackend):
    """macOS implementation of the platform abstraction layer.

    Uses ``fcntl.flock`` for single-instance guard, ``plistlib`` for
    Launch Agent autostart, ``subprocess.run(["open", "-t", ...])`` for
    file-open, and macOS-appropriate default paths and font.
    """

    def __init__(self) -> None:
        """Initialise the Darwin backend."""
        self._lock_fd: IO[str] | None = None

    def acquire_instance_lock(self) -> bool:
        """Acquire an exclusive fcntl lock on the instance lock file.

        Creates the lock directory and file if missing. Handles stale locks
        by checking PID liveness.

        Returns:
            True if the lock was acquired, False if another instance holds it.
        """
        import fcntl

        try:
            LOCK_DIR.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            logger.error("Cannot create lock directory: %s", LOCK_DIR)
            return False

        try:
            # Open without truncation to preserve existing PID for stale check
            if LOCK_FILE.exists():
                self._lock_fd = open(LOCK_FILE, "r+")
            else:
                self._lock_fd = open(LOCK_FILE, "w")
        except PermissionError:
            logger.error("Cannot open lock file: %s", LOCK_FILE)
            return False

        try:
            fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # Lock acquired — write our PID
            self._lock_fd.seek(0)
            self._lock_fd.truncate()
            self._lock_fd.write(str(os.getpid()))
            self._lock_fd.flush()
            return True
        except OSError:
            # Lock held by another process — check if stale
            self._lock_fd.close()
            self._lock_fd = None
            try:
                pid = int(LOCK_FILE.read_text().strip())
                os.kill(pid, 0)  # Process exists — lock is valid
            except (ValueError, ProcessLookupError, PermissionError):
                # Stale lock — reclaim
                LOCK_FILE.unlink(missing_ok=True)
                try:
                    self._lock_fd = open(LOCK_FILE, "w")
                    fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    self._lock_fd.write(str(os.getpid()))
                    self._lock_fd.flush()
                    return True
                except OSError:
                    return False
            return False

    def release_instance_lock(self) -> None:
        """Release the fcntl lock and remove the lock file."""
        if self._lock_fd is not None:
            self._lock_fd.close()
            self._lock_fd = None
        LOCK_FILE.unlink(missing_ok=True)

    def toggle_autostart(self, enabled: bool, executable_path: str) -> None:
        """Write or remove the Launch Agent plist for login autostart.

        Args:
            enabled: When True, write the plist; when False, remove it.
            executable_path: Path to the app executable.
        """
        import plistlib

        if enabled:
            PLIST_DIR.mkdir(parents=True, exist_ok=True, mode=0o755)
            plist = {
                "Label": PLIST_LABEL,
                "ProgramArguments": [executable_path, "--minimized"],
                "RunAtLoad": True,
            }
            with open(PLIST_PATH, "wb") as f:
                plistlib.dump(plist, f)
            logger.info("Launch Agent plist written: %s", PLIST_PATH)
        else:
            PLIST_PATH.unlink(missing_ok=True)
            logger.info("Launch Agent plist removed")

    def is_autostart_enabled(self) -> bool:
        """Check whether autostart is currently registered via plist.

        Validates plist content and repairs if needed.

        Returns:
            True if a valid plist exists with RunAtLoad set, False otherwise.
        """
        import plistlib

        if not PLIST_PATH.exists():
            return False
        try:
            with open(PLIST_PATH, "rb") as f:
                data = plistlib.load(f)
        except (plistlib.InvalidFileException, OSError):
            PLIST_PATH.unlink(missing_ok=True)
            return False
        # Validate and repair if needed
        needs_repair = (
            data.get("Label") != PLIST_LABEL or data.get("RunAtLoad") is not True
        )
        if needs_repair:
            self.toggle_autostart(True, data.get("ProgramArguments", [""])[0])
        return True

    def open_file_in_editor(self, path: Path) -> bool:
        """Open a file in the default text editor via macOS ``open -t``.

        Args:
            path: Path to the file to open.

        Returns:
            True on success, False if the file does not exist or open fails.
        """
        if not path.exists():
            return False
        result = subprocess.run(["open", "-t", str(path)], check=False)
        return result.returncode == 0

    def default_source_path(self) -> Path:
        """Return ``~/Downloads`` as the default source folder.

        Returns:
            Path to the user's Downloads directory.
        """
        return Path.home() / "Downloads"

    def default_library_path(self) -> Path:
        """Return ``~/3D Prints`` as the default library folder.

        Returns:
            Path to the default 3D prints library directory.
        """
        return Path.home() / "3D Prints"

    def platform_font(self) -> str:
        """Return ``TkDefaultFont`` for macOS Tk resolution.

        Returns:
            The string ``"TkDefaultFont"`` which Tk resolves to the system font.
        """
        return "TkDefaultFont"

    @staticmethod
    def fallback_menubar_icon() -> "Image.Image":
        """Generate a fallback 18x18 monochrome icon if asset not found.

        Returns:
            A PIL Image suitable for the macOS menu bar.
        """
        from PIL import Image, ImageDraw

        img = Image.new("RGBA", (18, 18), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([2, 2, 15, 15], fill=(0, 0, 0, 200))
        return img
