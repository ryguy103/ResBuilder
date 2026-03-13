#!/usr/bin/env python3
"""
build_app.py - Build standalone ResBuilder application

This script creates a distributable desktop application that users can
run without installing Python or using the terminal.

Usage:
    python build_app.py

Requirements:
    pip install pyinstaller

Output:
    dist/ResBuilder.app (macOS)
    dist/ResBuilder.exe (Windows)
"""

import subprocess
import sys
import platform
from pathlib import Path

def check_pyinstaller():
    """Check if PyInstaller is installed"""
    try:
        import PyInstaller
        return True
    except ImportError:
        return False

def install_pyinstaller():
    """Install PyInstaller"""
    print("Installing PyInstaller...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

def build_app():
    """Build the standalone application"""
    
    # Paths
    base_dir = Path(__file__).parent
    main_script = base_dir / "launcher.py"
    icon_path = base_dir / "assets" / "icon.icns"
    
    # Create launcher if it doesn't exist
    if not main_script.exists():
        print("Creating launcher script...")
        create_launcher()
    
    # PyInstaller arguments
    args = [
        "pyinstaller",
        "--name=ResBuilder",
        "--onefile",
        "--windowed",
        "--add-data=web/templates:web/templates",
        "--add-data=web/static:web/static",
        "--add-data=resume.md:.",
        "--add-data=resume.txt:.",
        "--hidden-import=uvicorn.logging",
        "--hidden-import=uvicorn.protocols.http",
        "--hidden-import=uvicorn.protocols.http.h11_impl",
        "--hidden-import=uvicorn.protocols.websockets",
        "--hidden-import=uvicorn.lifespan.on",
        "--hidden-import=uvicorn.lifespan.off",
        "--hidden-import=fastapi",
        "--hidden-import=starlette",
        "--hidden-import=jinja2",
        "--hidden-import=anthropic",
        "--hidden-import=docx",
        "--hidden-import=yaml",
        "--hidden-import=requests",
        "--hidden-import=bs4",
        "--clean",
        str(main_script),
    ]
    
    # Add icon if it exists
    if icon_path.exists():
        args.insert(3, f"--icon={icon_path}")
    
    # Add platform-specific options
    if platform.system() == "Darwin":
        args.extend([
            "--osx-bundle-identifier=com.resbuilder.app",
        ])
    
    print("Building application...")
    print(f"Running: {' '.join(args)}")
    
    subprocess.check_call(args)
    
    print("\n" + "=" * 50)
    print("Build complete!")
    print("=" * 50)
    
    if platform.system() == "Darwin":
        print("\nYour app is at: dist/ResBuilder.app")
        print("\nTo distribute:")
        print("  1. Zip the .app file")
        print("  2. Share the zip file")
        print("\nUsers can then:")
        print("  1. Unzip and drag to Applications")
        print("  2. Double-click to run")
    else:
        print("\nYour app is at: dist/ResBuilder.exe")
        print("\nUsers can just double-click to run!")


def create_launcher():
    """Create the launcher script that PyInstaller will bundle"""
    
    launcher_code = '''\
#!/usr/bin/env python3
"""
ResBuilder Desktop Application Launcher
Opens the web UI in the default browser and manages the server.
"""

import os
import sys
import time
import threading
import webbrowser
from pathlib import Path

def get_resource_path(relative_path):
    """Get path to resource, works for dev and PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / relative_path
    return Path(__file__).parent / relative_path

def setup_environment():
    """Set up paths for bundled resources"""
    if hasattr(sys, '_MEIPASS'):
        # Running as bundled app
        bundle_dir = Path(sys._MEIPASS)
        os.chdir(bundle_dir)
        
        # Add bundle dir to path
        sys.path.insert(0, str(bundle_dir))

def check_api_key():
    """Check if API key is set, prompt if not"""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return True
    
    # Try to load from config file
    config_path = Path.home() / ".resbuilder" / "config"
    if config_path.exists():
        key = config_path.read_text().strip()
        if key:
            os.environ["ANTHROPIC_API_KEY"] = key
            return True
    
    return False

def show_api_key_dialog():
    """Show a dialog to enter API key (cross-platform)"""
    import tkinter as tk
    from tkinter import simpledialog, messagebox
    
    root = tk.Tk()
    root.withdraw()
    
    key = simpledialog.askstring(
        "ResBuilder Setup",
        "Enter your Anthropic API Key:\\n\\n"
        "(Get one at console.anthropic.com)",
        show='*'
    )
    
    if key:
        # Save for future use
        config_dir = Path.home() / ".resbuilder"
        config_dir.mkdir(exist_ok=True)
        (config_dir / "config").write_text(key)
        os.environ["ANTHROPIC_API_KEY"] = key
        
        messagebox.showinfo(
            "Success",
            "API key saved! ResBuilder will now open in your browser."
        )
        return True
    else:
        messagebox.showwarning(
            "API Key Required",
            "You can still use ResBuilder, but AI features won't work.\\n\\n"
            "Set your API key later in the Profile page."
        )
        return False
    
    root.destroy()

def open_browser():
    """Open browser after server starts"""
    time.sleep(1.5)
    webbrowser.open("http://localhost:8000")

def run_server():
    """Run the FastAPI server"""
    import uvicorn
    from web.app import app
    
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

def main():
    setup_environment()
    
    if not check_api_key():
        show_api_key_dialog()
    
    # Open browser in background thread
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    print("Starting ResBuilder...")
    print("Opening http://localhost:8000 in your browser")
    print("Close this window to stop the server")
    
    run_server()

if __name__ == "__main__":
    main()
'''
    
    launcher_path = Path(__file__).parent / "launcher.py"
    launcher_path.write_text(launcher_code)
    print(f"Created: {launcher_path}")


if __name__ == "__main__":
    print("=" * 50)
    print("ResBuilder Desktop App Builder")
    print("=" * 50)
    print()
    
    if not check_pyinstaller():
        install_pyinstaller()
    
    build_app()
