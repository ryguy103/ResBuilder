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
    
    if not main_script.exists():
        print("ERROR: launcher.py not found in project root. Cannot build.")
        sys.exit(1)
    
    # PyInstaller arguments (--windowed + Tkinter crashes on macOS; launcher has no Tk)
    args = [
        "pyinstaller",
        "--name=ResBuilder",
        "--onefile",
        "--windowed",
        "--exclude-module=tkinter",
        "--exclude-module=_tkinter",
        "--exclude-module=matplotlib",
        "--add-data=web/templates:web/templates",
        "--add-data=web/static:web/static",
        "--add-data=profile.yaml.example:.",
        "--add-data=resume.md.example:.",
        "--hidden-import=uvicorn.logging",
        "--hidden-import=uvicorn.protocols.http",
        "--hidden-import=uvicorn.protocols.http.h11_impl",
        "--hidden-import=uvicorn.protocols.websockets",
        "--hidden-import=uvicorn.lifespan.on",
        "--hidden-import=uvicorn.lifespan.off",
        "--hidden-import=fastapi",
        "--hidden-import=starlette",
        "--hidden-import=jinja2",
        "--hidden-import=docx",
        "--hidden-import=yaml",
        "--hidden-import=anthropic",
        "--hidden-import=openai",
        "--hidden-import=google.generativeai",
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


if __name__ == "__main__":
    print("=" * 50)
    print("ResBuilder Desktop App Builder")
    print("=" * 50)
    print()
    
    if not check_pyinstaller():
        install_pyinstaller()
    
    build_app()
