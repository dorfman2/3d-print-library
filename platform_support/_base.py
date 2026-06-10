"""Abstract base class defining the cross-platform API contract.

All platform-specific backends (Windows, macOS) implement this interface.
"""

from abc import ABC, abstractmethod
from pathlib import Path


class PlatformBackend(ABC):
    """Abstract base defining the platform-specific API contract.

    Concrete subclasses implement OS-specific behaviour for single-instance
    guards, autostart registration, file-open, default paths, and font
    selection.
    """

    @abstractmethod
    def acquire_instance_lock(self) -> bool:
        """Acquire a single-instance lock.

        Returns:
            True if the lock was acquired successfully, False if another
            instance already holds it.
        """
        ...

    @abstractmethod
    def release_instance_lock(self) -> None:
        """Release the single-instance lock on normal exit."""
        ...

    @abstractmethod
    def toggle_autostart(self, enabled: bool, executable_path: str) -> None:
        """Register or unregister the app for autostart on login.

        Args:
            enabled: When True, register autostart; when False, remove it.
            executable_path: Path to the executable to launch on login.
        """
        ...

    @abstractmethod
    def is_autostart_enabled(self) -> bool:
        """Check whether autostart is currently registered.

        Returns:
            True if autostart is active, False otherwise.
        """
        ...

    @abstractmethod
    def open_file_in_editor(self, path: Path) -> bool:
        """Open a file in the default editor.

        Args:
            path: Path to the file to open.

        Returns:
            True on success, False on failure.
        """
        ...

    @abstractmethod
    def default_source_path(self) -> Path:
        """Return the platform-appropriate default source folder.

        Returns:
            Path to the default downloads/source directory.
        """
        ...

    @abstractmethod
    def default_library_path(self) -> Path:
        """Return the platform-appropriate default library folder.

        Returns:
            Path to the default 3D prints library directory.
        """
        ...

    @abstractmethod
    def platform_font(self) -> str:
        """Return the preferred UI font family for this platform.

        Returns:
            Font family name string suitable for Tk widgets.
        """
        ...
