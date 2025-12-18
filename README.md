# Albert's Sticky Notes

A lightweight desktop sticky notes app with multiple pages, custom colors, and system tray support.

## Features

- **Multiple Notes**: Browser-like tabs for organizing different notes
- **Custom Colors**: Pick any color for each note
- **Custom Names**: Name each note tab
- **System Tray**: Runs quietly in the notification area
- **Auto-Save**: Notes save automatically as you type
- **Persistent**: Remembers everything between sessions
- **Auto-Start**: Option to start automatically with Windows
- **Always on Top**: Toggle to keep notes visible

## Quick Setup (Windows)

### Option 1: Use the Build Script

1. Open the folder in File Explorer
2. Double-click `build.bat`
3. Wait for the build to complete
4. Find `AlbertsStickyNotes.exe` in the `dist` folder
5. Run it and right-click the tray icon → "Add to Windows Startup"

### Option 2: Manual Build in VS Code

1. Open VS Code and open this folder
2. Open the integrated terminal (Ctrl+`)
3. Run these commands:

```bash
# Create virtual environment (optional but recommended)
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install PyQt5 pyinstaller

# Build the EXE
pyinstaller --onefile --windowed --name "AlbertsStickyNotes" sticky_notes.py
```

4. The EXE will be in the `dist` folder

## Usage

### Main Interface

- **+ New Note**: Creates a new note (prompts for name and color)
- **⚙ Gear Button**: Edit current note's name and color
- **Tab X Button**: Close/delete a note
- **Drag Tabs**: Reorder your notes

### Tray Icon Menu (Right-Click)

- **Show/Hide**: Toggle the notes window
- **Toggle Always on Top**: Keep notes above other windows
- **New Note**: Quick add from tray
- **Add to Windows Startup**: Auto-start with Windows
- **Remove from Startup**: Disable auto-start
- **Quit**: Close completely

### Tips

- Double-click tray icon to show/hide
- Click X button minimizes to tray (doesn't quit)
- Notes save automatically as you type
- Window position and size are remembered

## File Locations

- **Notes data**: `%APPDATA%\AlbertsStickyNotes\notes.json`
- **Startup entry**: Windows Registry under `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run`

## Customization

Edit `sticky_notes.py` to change:

- **Default colors**: Modify the color presets
- **Font**: Change the `QFont()` parameters
- **Window size**: Adjust `setGeometry()` values
- **App title**: Change the title string

## Building with Custom Icon

To add a custom icon:

1. Create or download a `.ico` file
2. Save it as `icon.ico` in the same folder
3. Build with:
```bash
pyinstaller --onefile --windowed --name "AlbertsStickyNotes" --icon=icon.ico sticky_notes.py
```
