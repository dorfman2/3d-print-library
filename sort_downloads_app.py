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
"""

import json
import logging
import subprocess
import sys
import threading
import tkinter as tk
import winreg
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from tkinter import ttk
from typing import Any

import pystray
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)

SCRIPT_DIR: Path = Path(__file__).parent
SCRIPT_PATH: Path = SCRIPT_DIR / "sort_downloads.py"
CONFIG_PATH: Path = SCRIPT_DIR / "sort_downloads_config.json"
LOG_PATH: Path = SCRIPT_DIR / "sort_downloads.log"
ICON_TRAY: Path = SCRIPT_DIR / "icons8-3d-printer-comic-32.png"
ICON_WINDOW: Path = SCRIPT_DIR / "icons8-3d-printer-comic-96.png"
AUTOSTART_KEY: str = "3DPrintSync"
AUTOSTART_REG_PATH: str = r"Software\Microsoft\Windows\CurrentVersion\Run"

DEFAULT_CONFIG: dict[str, Any] = {
    "interval_minutes": 60,
    "autostart": False,
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

    if ICON_TRAY.exists():
        img = Image.open(ICON_TRAY).convert("RGBA")
        w, h = img.size
        r = max(3, w // 8)
        draw = ImageDraw.Draw(img)
        draw.ellipse([w - r * 2 - 1, h - r * 2 - 1, w - 1, h - 1],
                     fill=dot_colour, outline=(255, 255, 255, 180))
        return img

    # Fallback: plain circle
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([2, 2, 30, 30], fill=dot_colour)
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
        self._config = load_config()
        logger.info("sort_downloads_app starting (interval=%d min)", self._config["interval_minutes"])
        self._timer: threading.Timer | None = None
        self._running: bool = False
        self._last_run: datetime | None = None
        self._next_run: datetime | None = None

        # Tkinter root — kept withdrawn until explicitly shown
        self.root = tk.Tk()
        self.root.title("3D Print Library Sync")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._hide_window)
        icon_path = ICON_WINDOW if ICON_WINDOW.exists() else ICON_TRAY
        if icon_path.exists():
            self.root.iconphoto(True, tk.PhotoImage(file=str(icon_path)))
        self.root.withdraw()

        self._build_window()
        self._build_tray()

        # Show window unless --minimized flag was passed
        if "--minimized" not in sys.argv:
            self._show_window()

    # ------------------------------------------------------------------
    # Window
    # ------------------------------------------------------------------

    def _build_window(self) -> None:
        """Construct and lay out all tkinter widgets in the control window."""
        pad: dict[str, Any] = {"padx": 10, "pady": 4}

        frame = ttk.Frame(self.root, padding=12)
        frame.grid(sticky="nsew")

        ttk.Label(frame, text="3D Print Library Sync", font=("Segoe UI", 11, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 8)
        )

        # Status labels
        ttk.Label(frame, text="Status:").grid(row=1, column=0, sticky="w", **pad)
        self._status_var = tk.StringVar(value="Idle")
        ttk.Label(frame, textvariable=self._status_var, width=20).grid(row=1, column=1, columnspan=2, sticky="w")

        ttk.Label(frame, text="Last run:").grid(row=2, column=0, sticky="w", **pad)
        self._last_run_var = tk.StringVar(value="Never")
        ttk.Label(frame, textvariable=self._last_run_var, width=20).grid(row=2, column=1, columnspan=2, sticky="w")

        ttk.Label(frame, text="Next run:").grid(row=3, column=0, sticky="w", **pad)
        self._next_run_var = tk.StringVar(value="Not scheduled")
        ttk.Label(frame, textvariable=self._next_run_var, width=20).grid(row=3, column=1, columnspan=2, sticky="w")

        ttk.Separator(frame, orient="horizontal").grid(row=4, column=0, columnspan=3, sticky="ew", pady=6)

        # Interval
        ttk.Label(frame, text="Interval:").grid(row=5, column=0, sticky="w", **pad)
        self._interval_var = tk.IntVar(value=self._config["interval_minutes"])
        spinbox = ttk.Spinbox(
            frame,
            from_=1,
            to=1440,
            width=6,
            textvariable=self._interval_var,
            command=self._on_interval_change,
        )
        spinbox.grid(row=5, column=1, sticky="w", padx=(10, 2), pady=4)
        spinbox.bind("<FocusOut>", lambda _e: self._on_interval_change())
        spinbox.bind("<Return>", lambda _e: self._on_interval_change())
        ttk.Label(frame, text="minutes").grid(row=5, column=2, sticky="w")

        ttk.Separator(frame, orient="horizontal").grid(row=6, column=0, columnspan=3, sticky="ew", pady=6)

        # Start / Stop buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=7, column=0, columnspan=3, sticky="ew")
        self._start_btn = ttk.Button(btn_frame, text="Start", width=10, command=self.start)
        self._start_btn.pack(side="left", padx=(0, 6))
        self._stop_btn = ttk.Button(btn_frame, text="Stop", width=10, command=self.stop, state="disabled")
        self._stop_btn.pack(side="left")

        # Autostart checkbox
        self._autostart_var = tk.BooleanVar(value=self._config["autostart"])
        ttk.Checkbutton(
            frame,
            text="Start on Boot",
            variable=self._autostart_var,
            command=self._on_autostart_toggle,
        ).grid(row=8, column=0, columnspan=3, sticky="w", padx=10, pady=(8, 2))

        ttk.Separator(frame, orient="horizontal").grid(row=9, column=0, columnspan=3, sticky="ew", pady=6)

        # Run Now / Open Logs
        action_frame = ttk.Frame(frame)
        action_frame.grid(row=10, column=0, columnspan=3, sticky="ew")
        ttk.Button(action_frame, text="Run Now", width=10, command=self._on_run_now).pack(side="left", padx=(0, 6))
        ttk.Button(action_frame, text="Open Logs", width=10, command=self._on_open_logs).pack(side="left")

        ttk.Separator(frame, orient="horizontal").grid(row=11, column=0, columnspan=3, sticky="ew", pady=6)

        ttk.Button(frame, text="Exit", width=10, command=self.on_exit).grid(
            row=12, column=0, columnspan=3, pady=(0, 4)
        )

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
        """Run sort_downloads.py --move as a subprocess and record the timestamp."""
        logger.info("Sync run starting")
        self.root.after(0, lambda: self._status_var.set("Running"))
        try:
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
        except OSError as exc:
            logger.error("Failed to launch sync subprocess: %s", exc)
        finally:
            self._last_run = datetime.now()
            logger.info("Sync run finished")
            self.root.after(0, self._refresh_labels)
            if not self._running:
                self.root.after(0, lambda: self._status_var.set("Idle"))

    # ------------------------------------------------------------------
    # Config callbacks
    # ------------------------------------------------------------------

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
    app = SyncApp()
    app.root.mainloop()
