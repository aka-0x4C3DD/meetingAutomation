@echo off
setlocal EnableDelayedExpansion

echo ========================================
echo Meeting Automator Installation
echo ========================================
echo.

:: Clean up any existing files
echo Cleaning up previous installation files...
rmdir /s /q venv dist build __pycache__ 2>nul
del /f /q *.spec 2>nul
echo.

:: Check Python installation
echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed! Please install Python 3.8 or higher.
    pause
    exit /b 1
)
python -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python version must be 3.8 or higher.
    pause
    exit /b 1
)
echo [OK] Python check passed
echo.

:: Create and activate virtual environment
echo Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b 1
)
echo [OK] Virtual environment created and activated
echo.

:: Install dependencies
echo Installing dependencies (this may take several minutes)...
echo Please be patient while downloading and installing packages...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo [OK] Dependencies installed successfully
echo.

:: Install PyInstaller
echo Installing PyInstaller...
pip install pyinstaller
if errorlevel 1 (
    echo [ERROR] Failed to install PyInstaller.
    pause
    exit /b 1
)
echo [OK] PyInstaller installed
echo.

:: Create spec file
echo Creating PyInstaller specification...
echo # -*- mode: python ; coding: utf-8 -*- > meeting_automator.spec
echo. >> meeting_automator.spec
echo block_cipher = None >> meeting_automator.spec
echo. >> meeting_automator.spec
echo a = Analysis( >> meeting_automator.spec
echo     ['main.py'], >> meeting_automator.spec
echo     pathex=[], >> meeting_automator.spec
echo     binaries=[], >> meeting_automator.spec
echo     datas=[], >> meeting_automator.spec
echo     hiddenimports=['keyring.backends.Windows', 'win32timezone', 'darkdetect', 'psutil', 'psutil._pswindows'], >> meeting_automator.spec
echo     hookspath=[], >> meeting_automator.spec
echo     hooksconfig={}, >> meeting_automator.spec
echo     runtime_hooks=[], >> meeting_automator.spec
echo     excludes=[], >> meeting_automator.spec
echo     win_no_prefer_redirects=False, >> meeting_automator.spec
echo     win_private_assemblies=False, >> meeting_automator.spec
echo     cipher=block_cipher, >> meeting_automator.spec
echo     noarchive=False, >> meeting_automator.spec
echo ) >> meeting_automator.spec
echo. >> meeting_automator.spec
echo pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher) >> meeting_automator.spec
echo. >> meeting_automator.spec
echo exe = EXE( >> meeting_automator.spec
echo     pyz, >> meeting_automator.spec
echo     a.scripts, >> meeting_automator.spec
echo     a.binaries, >> meeting_automator.spec
echo     a.zipfiles, >> meeting_automator.spec
echo     a.datas, >> meeting_automator.spec
echo     [], >> meeting_automator.spec
echo     name='MeetingAutomator', >> meeting_automator.spec
echo     debug=False, >> meeting_automator.spec
echo     bootloader_ignore_signals=False, >> meeting_automator.spec
echo     strip=False, >> meeting_automator.spec
echo     upx=True, >> meeting_automator.spec
echo     upx_exclude=[], >> meeting_automator.spec
echo     runtime_tmpdir=None, >> meeting_automator.spec
echo     console=False, >> meeting_automator.spec
echo     disable_windowed_traceback=False, >> meeting_automator.spec
echo     target_arch=None, >> meeting_automator.spec
echo     codesign_identity=None, >> meeting_automator.spec
echo     entitlements_file=None >> meeting_automator.spec
echo ) >> meeting_automator.spec
echo [OK] Specification file created
echo.

:: Build executable
echo Building executable (this may take several minutes)...
echo Please wait while PyInstaller builds the application...
pyinstaller meeting_automator.spec
if errorlevel 1 (
    echo [ERROR] Failed to build executable.
    pause
    exit /b 1
)
echo [OK] Executable built successfully
echo.

:: Clean up build files
echo Cleaning up build files...
rmdir /s /q build 2>nul
del /f /q meeting_automator.spec 2>nul
rmdir /s /q venv 2>nul
echo [OK] Cleanup complete
echo.

echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo The executable has been created successfully:
echo   Location: dist\MeetingAutomator.exe
echo.
echo You can now run the application by double-clicking
echo the executable in the dist folder.
echo.
pause 