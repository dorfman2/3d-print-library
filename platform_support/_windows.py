"""Windows-specific platform backend implementation.

Provides single-instance guard via kernel32 mutex, autostart via winreg,
file-open via os.startfile, and Windows-appropriate defaults.

All platform-specific imports (winreg, ctypes) are inside the class body,
never at module level.
"""

import logging
import os
from pathlib import Path

from platform_support._base import PlatformBackend

logger = logging.getLogger(__name__)


class WindowsBackend(PlatformBackend):
    """Windows implementation of the platform abstraction layer.

    Uses ``ctypes.windll.kernel32.CreateMutexW`` for single-instance guard,
    ``winreg`` for autostart registry management, and ``os.startfile`` for
    file-open operations.

    Raises:
        RuntimeError: If ``winreg`` is not available on this system.
    """

    def __init__(self) -> None:
        """Initialise the Windows backend and verify winreg availability."""
        try:
            import winreg  # noqa: F401
        except ImportError:
            raise RuntimeError("Required Windows module 'winreg' not available")
        self._mutex_handle: int | None = None

    def acquire_instance_lock(self) -> bool:
        """Acquire a named mutex to prevent duplicate instances.

        Returns:
            True if this is the first instance, False if another holds the mutex.
        """
        import ctypes

        self._mutex_handle = ctypes.windll.kernel32.CreateMutexW(
            None, False, "Global\\3DPrintSync"
        )
        if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            return False
        return True

    def release_instance_lock(self) -> None:
        """No-op on Windows; mutex is released on process exit."""
        pass

    def toggle_autostart(self, enabled: bool, executable_path: str) -> None:
        """Write or remove the autostart registry entry.

        Args:
            enabled: When True, write the registry value; when False, remove it.
            executable_path: Path to the executable (pythonw.exe or frozen .exe).
        """
        import winreg

        reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key_name = "3DPrintSync"
        pythonw = executable_path.replace("python.exe", "pythonw.exe")
        value = f'"{pythonw}" --minimized'
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                reg_path,
                0,
                winreg.KEY_SET_VALUE,
            )
            with key:
                if enabled:
                    winreg.SetValueEx(key, key_name, 0, winreg.REG_SZ, value)
                else:
                    try:
                        winreg.DeleteValue(key, key_name)
                    except FileNotFoundError:
                        pass
        except OSError as exc:
            logger.error("Registry operation failed: %s", exc)

    def is_autostart_enabled(self) -> bool:
        """Check whether the autostart registry key exists.

        Returns:
            True if the registry value exists, False otherwise.
        """
        import winreg

        reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key_name = "3DPrintSync"
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                reg_path,
                0,
                winreg.KEY_READ,
            )
            with key:
                winreg.QueryValueEx(key, key_name)
                return True
        except (FileNotFoundError, OSError):
            return False

    def open_file_in_editor(self, path: Path) -> bool:
        """Open a file using the Windows default handler via os.startfile.

        Args:
            path: Path to the file to open.

        Returns:
            True on success, False if the file does not exist.
        """
        if not path.exists():
            return False
        os.startfile(str(path))  # type: ignore[attr-defined]
        return True

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
        """Return ``Segoe UI`` as the Windows platform font.

        Returns:
            The string ``"Segoe UI"``.
        """
        return "Segoe UI"
