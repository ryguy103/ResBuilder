#!/usr/bin/env python3
"""
ResBuilder Desktop Application Launcher
Starts the FastAPI server and opens the web UI in the default browser.

Does not use Tkinter: PyInstaller's --windowed macOS builds crash when
initializing Tcl/Tk (TkpInit). API keys are configured in the browser at /setup.
"""

import os
import sys
import time
import threading
import webbrowser
import platform
from pathlib import Path


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"))


def _frozen_data_root() -> Path:
    """Where profile, .env, and companies/ live when running the .app build."""
    override = Path.home() / ".resbuilder" / "data_dir"
    if override.exists():
        raw = override.read_text().strip()
        line = raw.splitlines()[0].strip() if raw else ""
        if line:
            custom = Path(line).expanduser().resolve()
            if custom.is_dir():
                return custom
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "ResBuilder"
    if system == "Windows":
        return Path(os.environ.get("APPDATA", str(Path.home()))) / "ResBuilder"
    return Path.home() / ".local" / "share" / "ResBuilder"


def setup_environment():
    """Paths for PyInstaller bundle: writable data dir + bundle resource root."""
    if not _is_frozen():
        return

    bundle_dir = Path(sys._MEIPASS)
    sys.path.insert(0, str(bundle_dir))
    os.environ["RESBUILDER_BUNDLE_RESOURCES"] = str(bundle_dir)

    data_root = _frozen_data_root()
    data_root.mkdir(parents=True, exist_ok=True)
    os.environ["RESBUILDER_DATA_DIR"] = str(data_root.resolve())
    os.chdir(data_root)


def _apply_legacy_api_key_file():
    """~/.resbuilder/config (single line) used to store Anthropic key for the old launcher."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    config_path = Path.home() / ".resbuilder" / "config"
    if config_path.exists():
        key = config_path.read_text().strip()
        if key:
            os.environ["ANTHROPIC_API_KEY"] = key


def has_any_api_key() -> bool:
    return bool(
        os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
    )


def open_browser(path: str = "/"):
    """Open browser after server starts."""
    time.sleep(1.5)
    webbrowser.open(f"http://127.0.0.1:8000{path}")


def run_server():
    import uvicorn
    from web.app import app

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")


def main():
    setup_environment()
    _apply_legacy_api_key_file()

    # First-time users go to /setup (no Tkinter dialog — avoids macOS PyInstaller crash)
    start_path = "/" if has_any_api_key() else "/setup"

    browser_thread = threading.Thread(
        target=open_browser, args=(start_path,), daemon=True
    )
    browser_thread.start()

    run_server()


if __name__ == "__main__":
    main()
