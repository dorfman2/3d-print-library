"""PyInstaller runtime hook: isolate the frozen interpreter from any host Python.

Purpose:
    A target machine that defines ``PYTHONPATH`` / ``PYTHONHOME`` (for example,
    pointing at a separately installed Python 3.14) can cause this frozen
    interpreter to import the *host's* ``_tkinter.pyd`` instead of the bundled
    one. That host extension links against a different ``pythonXX.dll`` and the
    import fails with:

        ImportError: Module use of python314.dll conflicts with this version

    This hook runs after interpreter initialization but before the application's
    ``import tkinter`` (and any other imports), so it can neutralize the leak by:

    1. Removing host-Python environment variables from ``os.environ``.
    2. Restricting ``sys.path`` to the PyInstaller bundle directory so a host
       Python's ``DLLs`` / ``site-packages`` can never shadow bundled extension
       modules such as ``_tkinter``.

Notes:
    - Frozen applications resolve all of their own modules from within the
      bundle, so pruning non-bundle ``sys.path`` entries is safe.
    - This file is referenced from ``sort_downloads_app.spec`` via
      ``runtime_hooks`` and is executed automatically by the bootloader.
"""

import os
import sys

# 1. Drop host-Python environment variables that leak into the frozen process.
for _var in ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP"):
    os.environ.pop(_var, None)

# 2. Restrict module search to the frozen bundle so a host Python installation
#    cannot shadow bundled extension modules (e.g. _tkinter).
_meipass = getattr(sys, "_MEIPASS", None)
if _meipass:
    _bundle_root = os.path.normcase(os.path.abspath(_meipass))
    sys.path = [
        _entry
        for _entry in sys.path
        if os.path.normcase(os.path.abspath(_entry)).startswith(_bundle_root)
    ]
