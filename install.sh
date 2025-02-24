#!/bin/bash

# Enable error handling
set -e

echo "========================================"
echo "Meeting Automator Installation"
echo "========================================"
echo

# Clean up any existing files
echo "Cleaning up previous installation files..."
rm -rf venv dist build __pycache__ *.spec
echo "[OK] Cleanup complete"
echo

# Check Python installation
echo "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python is not installed! Please install Python 3.8 or higher."
    exit 1
fi

# Check Python version
python3 -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)" || {
    echo "[ERROR] Python version must be 3.8 or higher."
    exit 1
}
echo "[OK] Python check passed"
echo

# Create and activate virtual environment
echo "Creating virtual environment..."
python3 -m venv venv || {
    echo "[ERROR] Failed to create virtual environment."
    exit 1
}
source venv/bin/activate || {
    echo "[ERROR] Failed to activate virtual environment."
    exit 1
}
echo "[OK] Virtual environment created and activated"
echo

# Install dependencies
echo "Installing dependencies (this may take several minutes)..."
echo "Please be patient while downloading and installing packages..."
python3 -m pip install --upgrade pip > /dev/null
pip install -r requirements.txt || {
    echo "[ERROR] Failed to install dependencies."
    exit 1
}
echo "[OK] Dependencies installed successfully"
echo

# Install PyInstaller
echo "Installing PyInstaller..."
pip install pyinstaller || {
    echo "[ERROR] Failed to install PyInstaller."
    exit 1
}
echo "[OK] PyInstaller installed"
echo

# Create spec file
echo "Creating PyInstaller specification..."
cat > meeting_automator.spec << EOL
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'keyring.backends.SecretService',  # For Linux
        'keyring.backends.macOS',          # For macOS
        'darkdetect',
        'psutil',
        'psutil._psutil_posix',           # For Unix-like systems
        'psutil._psutil_linux',           # For Linux
        'psutil._psutil_osx'              # For macOS
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MeetingAutomator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None
)
EOL
echo "[OK] Specification file created"
echo

# Build executable
echo "Building executable (this may take several minutes)..."
echo "Please wait while PyInstaller builds the application..."
pyinstaller meeting_automator.spec || {
    echo "[ERROR] Failed to build executable."
    exit 1
}
echo "[OK] Executable built successfully"
echo

# Clean up build files
echo "Cleaning up build files..."
rm -rf build meeting_automator.spec venv
echo "[OK] Cleanup complete"
echo

echo "========================================"
echo "Installation Complete!"
echo "========================================"
echo
echo "The executable has been created successfully:"
echo "  Location: dist/MeetingAutomator"
echo
echo "You can now run the application by executing:"
echo "  ./dist/MeetingAutomator"
echo

# Make the executable executable
chmod +x dist/MeetingAutomator

# Exit successfully
exit 0 