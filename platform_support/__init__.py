"""Platform abstraction layer for 3D Print Sync.

Provides a factory function that returns the correct platform-specific backend
based on the current operating system. Platform-specific imports are deferred
inside factory branches to avoid importing incompatible modules (e.g., winreg
on macOS or fcntl on Windows).
"""

import sys

from platform_support._base import PlatformBackend


def get_platform() -> PlatformBackend:
    """Return the platform-specific backend for the current OS.

    Returns:
        A concrete ``PlatformBackend`` subclass appropriate for the running OS.

    Raises:
        RuntimeError: On unsupported platforms (neither ``win32`` nor ``darwin``).
    """
    if sys.platform == "win32":
        from platform_support._windows import WindowsBackend

        return WindowsBackend()
    elif sys.platform == "darwin":
        from platform_support._darwin import DarwinBackend

        return DarwinBackend()
    else:
        raise RuntimeError(f"Unsupported platform: {sys.platform}")


__all__ = ["get_platform", "PlatformBackend"]
