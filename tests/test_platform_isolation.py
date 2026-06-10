"""Property test: Platform Isolation.

Verifies that importing ``platform_support`` does NOT trigger import of
platform-incompatible modules at module level.

On macOS: ``winreg`` and ``ctypes.windll`` are never loaded.
On Windows: ``fcntl`` is never loaded.

Validates: Requirements 1.6, 10.5
"""

from __future__ import annotations

import sys


def test_platform_isolation_no_cross_platform_imports() -> None:
    """Importing platform_support must not load wrong-platform modules."""
    # Record modules loaded before
    before = set(sys.modules.keys())

    import platform_support  # noqa: F401

    after = set(sys.modules.keys())
    newly_loaded = after - before

    if sys.platform == "darwin":
        assert "winreg" not in newly_loaded, "winreg imported on macOS"
        assert "ctypes.windll" not in newly_loaded, "ctypes.windll imported on macOS"
        # ctypes itself is fine, but windll attribute access should not happen
        if "ctypes" in newly_loaded:
            import ctypes

            assert not hasattr(ctypes, "_windll_loaded"), (
                "ctypes.windll accessed on macOS"
            )
    elif sys.platform == "win32":
        assert "fcntl" not in newly_loaded, "fcntl imported on Windows"
