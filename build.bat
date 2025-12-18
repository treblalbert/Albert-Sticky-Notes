@echo off
echo ========================================
echo   Albert's Sticky Notes - Build to EXE
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://python.org
    pause
    exit /b 1
)

echo [1/3] Installing dependencies...
pip install PyQt5 pyinstaller

echo.
echo [2/3] Building EXE file...
pyinstaller --onefile --windowed --name "AlbertsStickyNotes" --icon=NONE sticky_notes.py

echo.
echo [3/3] Build complete!
echo.
echo Your EXE file is located at:
echo   dist\AlbertsStickyNotes.exe
echo.
echo To use:
echo   1. Run AlbertsStickyNotes.exe
echo   2. Right-click the tray icon
echo   3. Select "Add to Windows Startup" to auto-start
echo.
pause
