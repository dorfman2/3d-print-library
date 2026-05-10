"""
sort_downloads_app.py - System tray app that runs sort_downloads.py on a schedule.

Provides a lightweight Windows system-tray icon and a control window for
starting/stopping the hourly sync, adjusting the interval, enabling autostart
on Windows login, and running the sync immediately.

Usage:
    python sort_downloads_app.py             # Show window + tray icon
    python sort_downloads_app.py --minimized # Tray icon only (used by autostart)

Dependencies:
    pip install pystray Pillow

Icon credit:
    "3d-modeling" icon by dickprayuda (Flaticon). Master art lives at
    ``3d-modeling.png``; ``app-icon-100.png`` and ``app-icon.ico`` are derived
    from it (white-background composited, multi-size).
"""

import ctypes
import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import tkinter as tk
import winreg

import ttkbootstrap as ttb
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any

import pystray
from PIL import Image, ImageDraw, ImageTk

logger = logging.getLogger(__name__)

# When frozen by PyInstaller: writable files (config, log) go to the install dir
# alongside the .exe; read-only bundled assets come from _MEIPASS.
if getattr(sys, "frozen", False):
    _APP_DIR: Path = Path(sys.executable).parent
    _ASSETS_DIR: Path = Path(sys._MEIPASS)  # type: ignore[attr-defined]
else:
    _APP_DIR = Path(__file__).parent
    _ASSETS_DIR = Path(__file__).parent

SCRIPT_DIR: Path = _APP_DIR
SCRIPT_PATH: Path = _APP_DIR / "sort_downloads.py"   # unused when frozen
CONFIG_PATH: Path = _APP_DIR / "sort_downloads_config.json"
LOG_PATH: Path = _APP_DIR / "sort_downloads.log"
CATEGORIES_PATH: Path = _APP_DIR / "categories.json"
CATEGORIES_DEFAULT: Path = _ASSETS_DIR / "categories.default.json"
ICON_SRC: Path = _ASSETS_DIR / "app-icon-100.png"
AUTOSTART_KEY: str = "3DPrintSync"
AUTOSTART_REG_PATH: str = r"Software\Microsoft\Windows\CurrentVersion\Run"

# Colour palette
CLR_BG: str = "#FFF1D3"
CLR_PEACH: str = "#FFB090"
CLR_PINK: str = "#CA5995"
CLR_PURPLE: str = "#5D1C6A"
CLR_WHITE: str = "#FFFFFF"

# Register custom ttkbootstrap theme using the palette
try:
    from ttkbootstrap.themes.standard import STANDARD_THEMES  # type: ignore[import-untyped]
    STANDARD_THEMES["3dprint"] = {
        "type": "light",
        "colors": {
            "primary": CLR_PURPLE,
            "secondary": CLR_PINK,
            "success": "#198754",
            "info": CLR_PEACH,
            "warning": "#ffc107",
            "danger": CLR_PINK,
            "light": CLR_BG,
            "dark": CLR_PURPLE,
            "bg": CLR_BG,
            "fg": CLR_PURPLE,
            "selectbg": CLR_PINK,
            "selectfg": CLR_WHITE,
            "border": CLR_PEACH,
            "inputfg": CLR_PURPLE,
            "inputbg": CLR_WHITE,
            "active": CLR_PEACH,
        },
    }
    _THEME = "3dprint"
except Exception:
    _THEME = "pulse"  # closest built-in fallback

DEFAULT_CONFIG: dict[str, Any] = {
    "interval_minutes": 60,
    "autostart": False,
    "last_run": None,
    "source_dir": str(Path.home() / "Downloads"),
    "dest_dir": str(Path.home() / "3D Prints"),
}


def _setup_logging() -> None:
    """Configure root logger with a console handler and a 5 MB rotating file handler.

    Shared log file with sort_downloads.py (``sort_downloads.log``).  Rotates at
    5 MB, keeps one backup — up to 10 MB on disk.
    """
    root = logging.getLogger()
    if root.handlers:
        return
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


def load_config() -> dict[str, Any]:
    """Load config from JSON file, creating it with defaults if absent.

    Returns:
        Config dict with ``interval_minutes`` (int) and ``autostart`` (bool).
    """
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, encoding="utf-8") as fh:
                data = json.load(fh)
            # Fill in any missing keys
            for key, val in DEFAULT_CONFIG.items():
                data.setdefault(key, val)
            return data
        except (json.JSONDecodeError, OSError):
            pass
    cfg = dict(DEFAULT_CONFIG)
    save_config(cfg)
    return cfg


def save_config(cfg: dict[str, Any]) -> None:
    """Write *cfg* to the JSON config file.

    Args:
        cfg: Config dict to serialise.
    """
    with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2)


# ---------------------------------------------------------------------------
# Categories — file management + on-disk helpers
# ---------------------------------------------------------------------------

def ensure_categories_file(
    target: Path = CATEGORIES_PATH,
    default: Path = CATEGORIES_DEFAULT,
) -> None:
    """Copy the bundled *default* categories file to *target* if absent.

    Args:
        target: Destination ``categories.json`` in the writable install dir.
        default: Bundled defaults shipped via PyInstaller datas (``_MEIPASS``).
    """
    if target.exists() or not default.exists():
        return
    shutil.copy(default, target)


def load_categories_dict(path: Path = CATEGORIES_PATH) -> dict[str, list[str]]:
    """Load the GUI's editable categories file.

    Args:
        path: Path to ``categories.json``.

    Returns:
        Dict mapping category name to keyword list (insertion-ordered).  When
        *path* is missing returns the bundled default mapping.
    """
    import sort_downloads
    return sort_downloads.load_categories(path)


def save_categories_dict(
    categories: dict[str, list[str]],
    path: Path = CATEGORIES_PATH,
) -> None:
    """Persist *categories* to *path* using the v1 schema.

    Args:
        categories: Insertion-ordered mapping of category name to keyword list.
        path: Destination JSON file.
    """
    payload = {
        "version": 1,
        "categories": [
            {"name": name, "keywords": list(kws)}
            for name, kws in categories.items()
        ],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)


def rename_category_folder(library_root: Path, old: str, new: str) -> None:
    """Rename ``library_root/old`` -> ``library_root/new`` if the old path exists.

    Tolerant of a missing source (no-ops); raises if *new* already exists so
    the caller can decide whether to merge.

    Args:
        library_root: Root of the on-disk library tree.
        old: Existing category folder name.
        new: Target category folder name.

    Raises:
        FileExistsError: When ``library_root/new`` already exists.
    """
    src = library_root / old
    dst = library_root / new
    if not src.exists():
        return
    if dst.exists():
        raise FileExistsError(str(dst))
    os.rename(src, dst)


def move_category_to_uncategorized(library_root: Path, name: str) -> None:
    """Move every project folder under *name* into ``Uncategorized``.

    Uses :func:`sort_downloads.unique_dest` for collision-safety so existing
    entries in ``Uncategorized`` are never overwritten.  Removes the empty
    source directory afterwards.

    Args:
        library_root: Root of the on-disk library tree.
        name: Category folder to dissolve.
    """
    import sort_downloads
    src = library_root / name
    if not src.exists():
        return
    uncategorized = library_root / "Uncategorized"
    uncategorized.mkdir(parents=True, exist_ok=True)
    for child in list(src.iterdir()):
        target = sort_downloads.unique_dest(uncategorized / child.name)
        shutil.move(str(child), str(target))
    try:
        os.rmdir(src)
    except OSError:
        pass


def _make_icon_image(running: bool) -> Image.Image:
    """Return a PIL image for the system tray icon.

    Loads the bundled 32×32 PNG when available, then draws a small status dot
    in the bottom-right corner (green = scheduled/running, grey = idle).
    Falls back to a plain coloured circle if the PNG is missing.

    Args:
        running: When True the status dot is green; grey when stopped.

    Returns:
        RGBA PIL image sized for the system tray.
    """
    dot_colour = (40, 167, 69, 255) if running else (108, 117, 125, 220)

    if ICON_SRC.exists():
        src = Image.open(ICON_SRC).convert("RGBA")
        bg = Image.new("RGBA", src.size, (255, 255, 255, 255))
        bg.paste(src, mask=src.split()[3])
        img = bg.resize((32, 32), Image.Resampling.LANCZOS)
    else:
        img = Image.new("RGBA", (32, 32), (255, 255, 255, 255))

    w, h = img.size
    r = max(3, w // 8)
    draw = ImageDraw.Draw(img)
    draw.ellipse([w - r * 2 - 1, h - r * 2 - 1, w - 1, h - 1],
                 fill=dot_colour, outline=(180, 180, 180, 200))
    return img


class SyncApp:
    """System-tray application for scheduling sort_downloads.py runs.

    Attributes:
        root: Hidden tkinter root window used as the event loop.
        _config: Loaded configuration dict.
        _timer: Active :class:`threading.Timer`, or None when stopped.
        _tray: Active :class:`pystray.Icon`.
        _running: Whether the scheduler is active.
        _last_run: Datetime of the last completed sync, or None.
        _next_run: Datetime of the next scheduled sync, or None.
    """

    def __init__(self) -> None:
        """Initialise config, tkinter root, control window, and tray icon."""
        _setup_logging()
        ensure_categories_file()
        self._config = load_config()
        logger.info("sort_downloads_app starting (interval=%d min)", self._config["interval_minutes"])
        self._timer: threading.Timer | None = None
        self._running: bool = False
        raw = self._config.get("last_run")
        self._last_run: datetime | None = datetime.fromisoformat(raw) if raw else None
        self._next_run: datetime | None = None

        # ttkbootstrap Window handles DPI awareness and theming automatically
        self.root = ttb.Window(themename=_THEME)
        self.root.title("3D Print Library Sync")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._hide_window)
        if ICON_SRC.exists():
            src = Image.open(ICON_SRC).convert("RGBA")
            bg = Image.new("RGBA", src.size, (255, 255, 255, 255))
            bg.paste(src, mask=src.split()[3])
            self._window_icon = ImageTk.PhotoImage(bg)
            self.root.iconphoto(True, self._window_icon)  # type: ignore[arg-type]
        self.root.withdraw()

        self._build_window()
        self._refresh_labels()  # populate labels from persisted state
        self._build_tray()

        # Show window unless --minimized flag was passed
        if "--minimized" not in sys.argv:
            self._show_window()

    # ------------------------------------------------------------------
    # Window
    # ------------------------------------------------------------------

    def _build_window(self) -> None:
        """Construct the control window using ttkbootstrap themed widgets."""
        # ── header banner (plain tk for guaranteed palette colours) ──────────
        header = tk.Frame(self.root, bg=CLR_PURPLE)
        header.pack(fill="x")
        tk.Label(
            header, text="3D Print Library Sync",
            bg=CLR_PURPLE, fg=CLR_WHITE,
            font=("Segoe UI", 14, "bold"), pady=40,
        ).pack()

        # ── body ─────────────────────────────────────────────────────────────
        body = ttb.Frame(self.root, padding=(56, 40))
        body.pack(fill="both", expand=True)

        # Status section
        self._status_var = tk.StringVar(value="Idle")
        self._last_run_var = tk.StringVar(value="Never")
        self._next_run_var = tk.StringVar(value="Not scheduled")

        status_frame = ttb.Frame(body)
        status_frame.pack(fill="x")
        for i, (label_text, var) in enumerate([
            ("Status:", self._status_var),
            ("Last run:", self._last_run_var),
            ("Next run:", self._next_run_var),
        ]):
            ttb.Label(status_frame, text=label_text, width=10, anchor="w").grid(
                row=i, column=0, sticky="w", pady=12)
            ttb.Label(status_frame, textvariable=var, bootstyle="secondary",  # type: ignore[call-arg]
                      anchor="w").grid(row=i, column=1, sticky="w", pady=12)

        ttb.Separator(body, bootstyle="secondary").pack(fill="x", pady=28)  # type: ignore[call-arg]

        # Folders
        folders_frame = ttb.Frame(body)
        folders_frame.pack(fill="x")

        self._source_var = tk.StringVar(value=self._config["source_dir"])
        self._dest_var = tk.StringVar(value=self._config["dest_dir"])

        for row, (label_text, var, on_save) in enumerate([
            ("Source folder:", self._source_var, self._on_source_change),
            ("Library folder:", self._dest_var, self._on_dest_change),
        ]):
            ttb.Label(folders_frame, text=label_text, width=14, anchor="w").grid(
                row=row, column=0, sticky="w", pady=8)
            entry = ttb.Entry(folders_frame, textvariable=var, width=48)
            entry.grid(row=row, column=1, sticky="ew", padx=8, pady=8)
            entry.bind("<FocusOut>", lambda _e, fn=on_save: fn())
            entry.bind("<Return>", lambda _e, fn=on_save: fn())
            ttb.Button(
                folders_frame, text="Browse…", bootstyle="secondary",  # type: ignore[call-arg]
                command=lambda v=var, fn=on_save: self._browse_folder(v, fn),
            ).grid(row=row, column=2, pady=8)

        folders_frame.columnconfigure(1, weight=1)

        ttb.Separator(body, bootstyle="secondary").pack(fill="x", pady=28)  # type: ignore[call-arg]

        # Interval
        interval_row = ttb.Frame(body)
        interval_row.pack(fill="x", pady=(0, 8))
        ttb.Label(interval_row, text="Interval:").pack(side="left")
        self._interval_var = tk.IntVar(value=self._config["interval_minutes"])
        spinbox = ttb.Spinbox(
            interval_row, from_=1, to=1440, width=5,
            textvariable=self._interval_var, command=self._on_interval_change,
            bootstyle="primary",  # type: ignore[call-arg]
        )
        spinbox.pack(side="left", padx=24)
        spinbox.bind("<FocusOut>", lambda _e: self._on_interval_change())
        spinbox.bind("<Return>", lambda _e: self._on_interval_change())
        ttb.Label(interval_row, text="minutes").pack(side="left")

        ttb.Separator(body, bootstyle="secondary").pack(fill="x", pady=28)  # type: ignore[call-arg]

        # Start / Stop
        row1 = ttb.Frame(body)
        row1.pack(fill="x", pady=(0, 20))
        self._start_btn = ttb.Button(
            row1, text="Start", bootstyle="primary",  # type: ignore[call-arg]
            padding=(32, 16), command=self.start,
        )
        self._start_btn.pack(side="left", padx=(0, 20))
        self._stop_btn = ttb.Button(
            row1, text="Stop", bootstyle="secondary",  # type: ignore[call-arg]
            padding=(32, 16), command=self.stop, state="disabled",
        )
        self._stop_btn.pack(side="left")

        # Run Now / Open Logs / Categories
        row2 = ttb.Frame(body)
        row2.pack(fill="x")
        ttb.Button(
            row2, text="Run Now", bootstyle="primary",  # type: ignore[call-arg]
            padding=(32, 16), command=self._on_run_now,
        ).pack(side="left", padx=(0, 20))
        ttb.Button(
            row2, text="Open Logs", bootstyle="info",  # type: ignore[call-arg]
            padding=(32, 16), command=self._on_open_logs,
        ).pack(side="left", padx=(0, 20))
        self._categories_btn = ttb.Button(
            row2, text="Categories…", bootstyle="info",  # type: ignore[call-arg]
            padding=(32, 16), command=self._on_open_categories,
        )
        self._categories_btn.pack(side="left")

        ttb.Separator(body, bootstyle="secondary").pack(fill="x", pady=28)  # type: ignore[call-arg]

        # Footer: toggle + Exit
        footer = ttb.Frame(body)
        footer.pack(fill="x")
        self._autostart_var = tk.BooleanVar(value=self._config["autostart"])
        ttb.Checkbutton(
            footer, text="Start on Boot",
            variable=self._autostart_var, command=self._on_autostart_toggle,
            bootstyle="secondary-round-toggle",  # type: ignore[call-arg]
        ).pack(side="left")
        ttb.Button(
            footer, text="Exit", bootstyle="secondary",  # type: ignore[call-arg]
            padding=(32, 16), command=self.on_exit,
        ).pack(side="right")

    def _show_window(self) -> None:
        """Raise and deiconify the control window."""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _hide_window(self) -> None:
        """Hide the control window without stopping the scheduler."""
        self.root.withdraw()

    def _refresh_labels(self) -> None:
        """Update status, last-run, and next-run labels from current state."""
        if self._running:
            self._status_var.set("Scheduled")
        else:
            self._status_var.set("Idle")

        self._last_run_var.set(
            self._last_run.strftime("%Y-%m-%d %H:%M") if self._last_run else "Never"
        )
        self._next_run_var.set(
            self._next_run.strftime("%Y-%m-%d %H:%M") if self._next_run else "Not scheduled"
        )

        self._start_btn.config(state="disabled" if self._running else "normal")
        self._stop_btn.config(state="normal" if self._running else "disabled")

    # ------------------------------------------------------------------
    # Tray
    # ------------------------------------------------------------------

    def _build_tray(self) -> None:
        """Create and start the pystray icon in a daemon background thread."""
        menu = pystray.Menu(
            pystray.MenuItem("Show Window", self._on_tray_show, default=True),
            pystray.MenuItem("Run Now", self._on_tray_run_now),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self._on_tray_exit),
        )
        self._tray = pystray.Icon(
            AUTOSTART_KEY,
            _make_icon_image(False),
            "3D Print Sync",
            menu,
        )
        t = threading.Thread(target=self._tray.run, daemon=True)
        t.start()

    def _update_tray_icon(self) -> None:
        """Redraw the tray icon to reflect current running state."""
        self._tray.icon = _make_icon_image(self._running)

    def _on_tray_show(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        """Tray menu: Show Window."""
        self.root.after(0, self._show_window)

    def _on_tray_run_now(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        """Tray menu: Run Now — execute sync immediately outside the schedule."""
        threading.Thread(target=self._run_sync, daemon=True).start()

    def _on_tray_exit(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        """Tray menu: Exit."""
        self.root.after(0, self.on_exit)

    # ------------------------------------------------------------------
    # Scheduler
    # ------------------------------------------------------------------

    @property
    def _interval_seconds(self) -> float:
        """Return the current interval in seconds."""
        return float(self._config["interval_minutes"] * 60)

    def start(self) -> None:
        """Start the recurring sync scheduler.

        Has no effect if the scheduler is already running.
        """
        if self._running:
            return
        self._running = True
        logger.info("Scheduler started (interval=%d min)", self._config["interval_minutes"])
        self._schedule_next()
        self._update_tray_icon()
        self._refresh_labels()

    def stop(self) -> None:
        """Stop the recurring sync scheduler and cancel any pending timer."""
        self._running = False
        self._next_run = None
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
        logger.info("Scheduler stopped")
        self._update_tray_icon()
        self.root.after(0, self._refresh_labels)

    def _schedule_next(self) -> None:
        """Schedule the next sync run after the configured interval."""
        self._next_run = datetime.now() + timedelta(seconds=self._interval_seconds)
        self.root.after(0, self._refresh_labels)
        self._timer = threading.Timer(self._interval_seconds, self._run_and_reschedule)
        self._timer.daemon = True
        self._timer.start()

    def _run_and_reschedule(self) -> None:
        """Execute sync then schedule the next run (called by the timer thread)."""
        self._run_sync()
        if self._running:
            self._schedule_next()

    def _run_sync(self) -> None:
        """Run the sync and record the timestamp.

        When running as a frozen PyInstaller bundle, imports and calls
        :func:`sort_downloads.run` directly (no subprocess needed).
        When running as a plain Python script, launches a subprocess so that
        a crash in the sync logic cannot take down the GUI process.
        """
        logger.info("Sync run starting")
        self.root.after(0, lambda: self._status_var.set("Running"))
        self.root.after(0, lambda: self._categories_btn.config(state="disabled"))
        try:
            if getattr(sys, "frozen", False):
                import sort_downloads  # bundled as a hidden import
                sort_downloads.run(
                    move=True,
                    downloads=Path(self._config["source_dir"]).expanduser(),
                    library_root=Path(self._config["dest_dir"]).expanduser(),
                    categories_path=CATEGORIES_PATH,
                )
            else:
                result = subprocess.run(
                    [sys.executable, str(SCRIPT_PATH), "--move"],
                    capture_output=True,
                    check=False,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                if result.returncode != 0:
                    logger.warning("Sync exited with code %d", result.returncode)
                    if result.stderr:
                        logger.warning("stderr: %s", result.stderr.strip())
        except Exception as exc:
            logger.error("Sync failed: %s", exc)
        finally:
            self._last_run = datetime.now()
            self._config["last_run"] = self._last_run.isoformat()
            save_config(self._config)
            logger.info("Sync run finished")
            self.root.after(0, self._refresh_labels)
            self.root.after(0, lambda: self._categories_btn.config(state="normal"))
            if not self._running:
                self.root.after(0, lambda: self._status_var.set("Idle"))

    # ------------------------------------------------------------------
    # Config callbacks
    # ------------------------------------------------------------------

    def _browse_folder(self, var: tk.StringVar, on_save: "Any") -> None:
        """Open a folder picker; update *var* and persist via *on_save* on selection.

        Args:
            var: StringVar bound to the entry that should receive the chosen path.
            on_save: Callback invoked after a folder is chosen to persist the change.
        """
        chosen = filedialog.askdirectory(
            initialdir=var.get() or str(Path.home()),
            parent=self.root,
        )
        if chosen:
            var.set(chosen)
            on_save()

    def _on_source_change(self) -> None:
        """Persist the source folder; warn (don't block) if it does not exist."""
        p = Path(self._source_var.get()).expanduser()
        if not p.exists():
            logger.warning("Source folder does not exist yet: %s", p)
        self._config["source_dir"] = str(p)
        save_config(self._config)

    def _on_dest_change(self) -> None:
        """Persist the destination folder, creating it if missing."""
        p = Path(self._dest_var.get()).expanduser()
        try:
            p.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.error("Could not create destination folder %s: %s", p, exc)
        self._config["dest_dir"] = str(p)
        save_config(self._config)

    def _on_interval_change(self) -> None:
        """Persist the new interval value when the spinbox changes."""
        try:
            minutes = int(self._interval_var.get())
        except (tk.TclError, ValueError):
            return
        minutes = max(1, min(1440, minutes))
        self._interval_var.set(minutes)
        self._config["interval_minutes"] = minutes
        save_config(self._config)

    def _on_autostart_toggle(self) -> None:
        """Write or remove the Windows Registry autostart entry."""
        enabled = bool(self._autostart_var.get())
        self._config["autostart"] = enabled
        save_config(self._config)
        toggle_autostart(enabled)

    def _on_run_now(self) -> None:
        """Button: run a single sync immediately in a background thread."""
        threading.Thread(target=self._run_sync, daemon=True).start()

    def _on_open_categories(self) -> None:
        """Button: open the Categories editor.

        Operates on a working copy of ``categories.json``.  When the dialog is
        saved, the file is rewritten and any disk-affecting actions (renames,
        deletes) are applied against the configured library root.
        """
        library_root = Path(self._config["dest_dir"]).expanduser()
        dialog = CategoriesDialog(self.root, CATEGORIES_PATH, library_root)
        dialog.show()

    def _on_open_logs(self) -> None:
        """Button: open the log file in the default text editor."""
        import os
        if LOG_PATH.exists():
            os.startfile(str(LOG_PATH))
        else:
            logger.info("Log file does not exist yet: %s", LOG_PATH)

    # ------------------------------------------------------------------
    # Exit
    # ------------------------------------------------------------------

    def on_exit(self) -> None:
        """Cleanly stop the scheduler, remove the tray icon, and quit."""
        logger.info("sort_downloads_app exiting")
        self._running = False
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
        self._tray.stop()
        self.root.destroy()
        sys.exit(0)


# ---------------------------------------------------------------------------
# Categories editor dialog
# ---------------------------------------------------------------------------

class CategoriesDialog:
    """Modal dialog for editing the editable category list and per-category keywords.

    Operates on a working copy of the categories dict so Cancel discards changes.
    Save writes ``categories.json`` and applies any disk-affecting operations
    (rename or delete of the matching folder under *library_root*) for category
    names that changed since the dialog was opened.

    Attributes:
        parent: The Tk root window that owns this modal.
        categories_path: Destination JSON file for persisted edits.
        library_root: On-disk library root used for rename / delete operations.
    """

    UNCATEGORIZED: str = "Uncategorized"

    def __init__(
        self,
        parent: tk.Misc,
        categories_path: Path,
        library_root: Path,
    ) -> None:
        """Build the dialog widgets and load the current categories file.

        Args:
            parent: Parent Tk window — the dialog is modal relative to it.
            categories_path: ``categories.json`` location.
            library_root: Library root used for on-disk rename/delete actions.
        """
        self.parent = parent
        self.categories_path = categories_path
        self.library_root = library_root

        self._original: dict[str, list[str]] = load_categories_dict(categories_path)
        self._working: dict[str, list[str]] = {
            name: list(kws) for name, kws in self._original.items()
        }
        self._original_names: list[str] = list(self._original.keys())
        # Track renames as ordered pairs of (original_name, current_name).  When
        # the user renames "0 - Cal" to "00 - Cal" we record ("0 - Cal", "00 - Cal").
        self._renamed: dict[str, str] = {}
        # Categories the user has deleted from the working copy.
        self._deleted: set[str] = set()
        self._selected: str | None = None
        self._dirty: bool = False
        self._suppress_keyword_save: bool = False

        self.top = tk.Toplevel(parent)
        self.top.title("Edit Categories")
        self.top.transient(parent)
        self.top.resizable(True, True)
        self.top.minsize(640, 460)
        self.top.protocol("WM_DELETE_WINDOW", self._on_cancel)

        self._build()
        self._reload_listbox()
        if self._working:
            self._listbox.selection_set(0)
            self._on_select()

    def _build(self) -> None:
        """Lay out the listbox, keyword editor, and action buttons."""
        body = ttb.Frame(self.top, padding=16)
        body.pack(fill="both", expand=True)

        cats_frame = ttb.LabelFrame(body, text="Categories", padding=8)
        cats_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        self._listbox = tk.Listbox(cats_frame, exportselection=False, height=14, width=28)
        self._listbox.pack(side="left", fill="both", expand=True)
        self._listbox.bind("<<ListboxSelect>>", lambda _e: self._on_select())
        sb = ttb.Scrollbar(cats_frame, orient="vertical", command=self._listbox.yview)
        sb.pack(side="right", fill="y")
        self._listbox.config(yscrollcommand=sb.set)

        kw_frame = ttb.LabelFrame(body, text="Keywords (one per line)", padding=8)
        kw_frame.grid(row=0, column=1, sticky="nsew")

        self._kw_text = tk.Text(kw_frame, width=36, height=14, wrap="none", undo=True)
        self._kw_text.pack(side="left", fill="both", expand=True)
        kwsb = ttb.Scrollbar(kw_frame, orient="vertical", command=self._kw_text.yview)
        kwsb.pack(side="right", fill="y")
        self._kw_text.config(yscrollcommand=kwsb.set)
        self._kw_text.bind("<FocusOut>", lambda _e: self._save_keywords_for_selection())
        self._kw_text.bind("<<Modified>>", self._on_text_modified)

        body.columnconfigure(0, weight=0)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        # Action row beneath the lists
        actions = ttb.Frame(self.top, padding=(16, 0))
        actions.pack(fill="x")
        ttb.Button(actions, text="Add",    command=self._on_add).pack(side="left", padx=4)
        ttb.Button(actions, text="Rename", command=self._on_rename).pack(side="left", padx=4)
        ttb.Button(actions, text="Delete", command=self._on_delete).pack(side="left", padx=4)
        ttb.Button(actions, text="↑",      command=lambda: self._on_move(-1)).pack(side="left", padx=4)
        ttb.Button(actions, text="↓",      command=lambda: self._on_move(1)).pack(side="left", padx=4)

        footer = ttb.Frame(self.top, padding=16)
        footer.pack(fill="x")
        ttb.Button(footer, text="Save",   bootstyle="primary",   # type: ignore[call-arg]
                   command=self._on_save).pack(side="right", padx=4)
        ttb.Button(footer, text="Cancel", bootstyle="secondary",  # type: ignore[call-arg]
                   command=self._on_cancel).pack(side="right", padx=4)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def show(self) -> dict[str, list[str]] | None:
        """Run the dialog modally; return the saved categories dict or ``None``.

        Returns:
            The updated categories dict when Save was clicked, otherwise
            ``None`` (Cancel/closed).
        """
        self.top.grab_set()
        self.top.wait_window()
        return self._working if self._dirty and self._saved else None

    _saved: bool = False

    # ------------------------------------------------------------------
    # Listbox helpers
    # ------------------------------------------------------------------

    def _reload_listbox(self, select: str | None = None) -> None:
        """Repopulate the listbox from the working dict, restoring selection."""
        self._listbox.delete(0, tk.END)
        for name in self._working.keys():
            self._listbox.insert(tk.END, name)
        if select is not None and select in self._working:
            idx = list(self._working.keys()).index(select)
            self._listbox.selection_set(idx)
            self._listbox.see(idx)
            self._selected = select
        else:
            self._selected = None

    def _on_select(self) -> None:
        """When the listbox selection changes, swap the keyword editor's contents."""
        self._save_keywords_for_selection()
        sel = self._listbox.curselection()
        if not sel:
            self._selected = None
            self._suppress_keyword_save = True
            self._kw_text.delete("1.0", tk.END)
            self._kw_text.edit_modified(False)
            self._suppress_keyword_save = False
            return
        name = self._listbox.get(sel[0])
        self._selected = name
        self._suppress_keyword_save = True
        self._kw_text.delete("1.0", tk.END)
        self._kw_text.insert("1.0", "\n".join(self._working.get(name, [])))
        self._kw_text.edit_modified(False)
        self._suppress_keyword_save = False

    def _on_text_modified(self, _event: object) -> None:
        """Mark the working copy dirty as the user types in the keyword editor."""
        if self._suppress_keyword_save:
            return
        if self._kw_text.edit_modified():
            self._dirty = True

    def _save_keywords_for_selection(self) -> None:
        """Persist the keyword editor's contents to the working dict."""
        if self._selected is None:
            return
        raw = self._kw_text.get("1.0", tk.END)
        keywords = [line.strip() for line in raw.splitlines() if line.strip()]
        if self._working.get(self._selected) != keywords:
            self._working[self._selected] = keywords
            self._dirty = True
        self._kw_text.edit_modified(False)

    # ------------------------------------------------------------------
    # Action handlers
    # ------------------------------------------------------------------

    def _on_add(self) -> None:
        """Prompt for a new category name; reject blanks, duplicates, and Uncategorized."""
        from tkinter import simpledialog
        name = simpledialog.askstring("Add Category", "Category name:", parent=self.top)
        if not name:
            return
        name = name.strip()
        if not name or name == self.UNCATEGORIZED or name in self._working:
            messagebox.showerror("Add Category", f"Invalid or duplicate name: {name!r}", parent=self.top)
            return
        self._working[name] = []
        self._dirty = True
        self._reload_listbox(select=name)
        self._on_select()

    def _on_rename(self) -> None:
        """Rename the selected category, refusing to clobber Uncategorized."""
        if not self._selected:
            return
        from tkinter import simpledialog
        old = self._selected
        new = simpledialog.askstring(
            "Rename Category", f"New name for {old!r}:",
            initialvalue=old, parent=self.top,
        )
        if not new:
            return
        new = new.strip()
        if not new or new == old:
            return
        if new == self.UNCATEGORIZED or new in self._working:
            messagebox.showerror("Rename Category", f"Name already in use: {new!r}", parent=self.top)
            return
        # Preserve insertion order
        self._working = {
            (new if k == old else k): v for k, v in self._working.items()
        }
        # Track rename through whatever original name this category started as
        for orig, cur in list(self._renamed.items()):
            if cur == old:
                self._renamed[orig] = new
                break
        else:
            if old in self._original_names:
                self._renamed[old] = new
        self._dirty = True
        self._reload_listbox(select=new)
        self._on_select()

    def _on_delete(self) -> None:
        """Delete the selected category after confirmation."""
        if not self._selected:
            return
        target = self._selected
        if not messagebox.askyesno(
            "Delete Category",
            f"Delete category {target!r}?\n\nProjects already inside this folder will be moved to {self.UNCATEGORIZED!r} when you click Save.",
            parent=self.top,
        ):
            return
        # If this name (or its original) was tracked as a rename, drop it
        for orig, cur in list(self._renamed.items()):
            if cur == target:
                self._deleted.add(orig)
                del self._renamed[orig]
                break
        else:
            if target in self._original_names:
                self._deleted.add(target)
        self._working.pop(target, None)
        self._dirty = True
        self._reload_listbox()
        self._on_select()

    def _on_move(self, direction: int) -> None:
        """Move the selected category up (-1) or down (+1) in the order."""
        if not self._selected:
            return
        names = list(self._working.keys())
        try:
            idx = names.index(self._selected)
        except ValueError:
            return
        new_idx = idx + direction
        if new_idx < 0 or new_idx >= len(names):
            return
        names[idx], names[new_idx] = names[new_idx], names[idx]
        self._working = {n: self._working[n] for n in names}
        self._dirty = True
        self._reload_listbox(select=self._selected)

    # ------------------------------------------------------------------
    # Save / Cancel
    # ------------------------------------------------------------------

    def _on_save(self) -> None:
        """Apply renames + deletions on disk, then write ``categories.json``."""
        self._save_keywords_for_selection()

        # Apply on-disk renames first (failure here aborts before any deletes).
        for orig, new in self._renamed.items():
            try:
                rename_category_folder(self.library_root, orig, new)
            except FileExistsError as exc:
                merge = messagebox.askyesno(
                    "Rename clash",
                    f"Library already has a folder named {new!r}.\n\nMerge contents from {orig!r} into it?",
                    parent=self.top,
                )
                if not merge:
                    messagebox.showinfo(
                        "Save aborted",
                        f"Rename of {orig!r} -> {new!r} skipped; resolve manually and Save again.",
                        parent=self.top,
                    )
                    return
                self._merge_category_folders(orig, new)
            except OSError as exc:
                messagebox.showerror(
                    "Rename failed",
                    f"Could not rename {orig!r} -> {new!r}: {exc}",
                    parent=self.top,
                )
                return

        for name in self._deleted:
            move_category_to_uncategorized(self.library_root, name)

        save_categories_dict(self._working, self.categories_path)
        self._saved = True
        self.top.grab_release()
        self.top.destroy()

    def _merge_category_folders(self, src_name: str, dst_name: str) -> None:
        """Move children of ``library_root/src_name`` into ``library_root/dst_name``."""
        import sort_downloads
        src = self.library_root / src_name
        dst = self.library_root / dst_name
        for child in list(src.iterdir()):
            target = sort_downloads.unique_dest(dst / child.name)
            shutil.move(str(child), str(target))
        try:
            os.rmdir(src)
        except OSError:
            pass

    def _on_cancel(self) -> None:
        """Discard pending changes and close the dialog."""
        self.top.grab_release()
        self.top.destroy()


# ---------------------------------------------------------------------------
# Registry helpers
# ---------------------------------------------------------------------------

def toggle_autostart(enabled: bool) -> None:
    """Write or remove the autostart registry entry for this app.

    Uses ``pythonw.exe`` so no console window appears on login.

    Args:
        enabled: When True, write the registry value; when False, remove it.
    """
    pythonw = sys.executable.replace("python.exe", "pythonw.exe")
    value = f'"{pythonw}" "{SCRIPT_PATH}" --minimized'
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            AUTOSTART_REG_PATH,
            0,
            winreg.KEY_SET_VALUE,
        )
        with key:
            if enabled:
                winreg.SetValueEx(key, AUTOSTART_KEY, 0, winreg.REG_SZ, value)
            else:
                try:
                    winreg.DeleteValue(key, AUTOSTART_KEY)
                except FileNotFoundError:
                    pass
    except OSError as exc:
        logger.error("Registry operation failed: %s", exc)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Named mutex prevents a second instance from launching.
    # The handle must stay alive for the lifetime of the process.
    _mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Global\\3DPrintSync")
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        ctypes.windll.user32.MessageBoxW(
            0, "3D Print Sync is already running.", "Already Running", 0x40
        )
        sys.exit(0)

    app = SyncApp()
    app.root.mainloop()
