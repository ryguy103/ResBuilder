#!/bin/bash
#
# ResBuilder One-Click Installer for macOS
# 
# Users can double-click this file in Finder to install.
# No terminal knowledge required!
#

clear
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                                                          ║"
echo "║           🚀 ResBuilder Installer                            ║"
echo "║           AI-Powered Job Application Tool                ║"
echo "║                                                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    echo ""
    echo "Please install Python from: https://www.python.org/downloads/"
    echo ""
    echo "Press any key to open the download page..."
    read -n 1
    open "https://www.python.org/downloads/"
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"
echo ""

# Navigate to the script's directory
cd "$(dirname "$0")"
INSTALL_DIR="$(pwd)"

echo "📦 Installing dependencies..."
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate and install
source venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo "✓ Dependencies installed"
echo ""

# API Key setup
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔑 API Key Setup"
echo ""
echo "ResBuilder uses Claude AI to generate resumes and cover letters."
echo "You'll need an Anthropic API key."
echo ""

CONFIG_DIR="$HOME/.resbuilder"
CONFIG_FILE="$CONFIG_DIR/config"

if [ -f "$CONFIG_FILE" ]; then
    echo "✓ API key already configured"
else
    echo "Get your free API key at: https://console.anthropic.com/"
    echo ""
    read -p "Enter your Anthropic API key (or press Enter to skip): " API_KEY
    
    if [ -n "$API_KEY" ]; then
        mkdir -p "$CONFIG_DIR"
        echo "$API_KEY" > "$CONFIG_FILE"
        chmod 600 "$CONFIG_FILE"
        echo "✓ API key saved"
    else
        echo "⚠ Skipped - you can add it later in the app"
    fi
fi

echo ""

# Create launch script
echo "📝 Creating launcher..."

LAUNCH_SCRIPT="$INSTALL_DIR/ResBuilder.command"
cat > "$LAUNCH_SCRIPT" << 'LAUNCHER'
#!/bin/bash
cd "$(dirname "$0")"

# Load API key if saved
CONFIG_FILE="$HOME/.resbuilder/config"
if [ -f "$CONFIG_FILE" ]; then
    export ANTHROPIC_API_KEY="$(cat "$CONFIG_FILE")"
fi

# Activate virtual environment
source venv/bin/activate

# Open browser after short delay
(sleep 2 && open http://localhost:8000) &

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  ResBuilder is running at http://localhost:8000              ║"
echo "║  Press Ctrl+C or close this window to stop               ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Run the server
python -m uvicorn web.app:app --host 127.0.0.1 --port 8000
LAUNCHER

chmod +x "$LAUNCH_SCRIPT"

echo "✓ Launcher created"
echo ""

# Create Applications alias (optional)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
read -p "Add ResBuilder to your Applications folder? (y/n): " ADD_TO_APPS

if [[ "$ADD_TO_APPS" =~ ^[Yy]$ ]]; then
    ln -sf "$LAUNCH_SCRIPT" "/Applications/ResBuilder.command"
    echo "✓ Added to Applications"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ Installation complete!"
echo ""
echo "To start ResBuilder:"
echo "  • Double-click 'ResBuilder.command' in this folder"
if [[ "$ADD_TO_APPS" =~ ^[Yy]$ ]]; then
    echo "  • Or find 'ResBuilder' in your Applications"
fi
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
read -p "Start ResBuilder now? (y/n): " START_NOW

if [[ "$START_NOW" =~ ^[Yy]$ ]]; then
    exec "$LAUNCH_SCRIPT"
fi
