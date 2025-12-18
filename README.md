# Albert's Sticky Notes

A lightweight desktop sticky notes app with GitHub sync for sharing notes across computers.
Microsoft's sticky notes suck, so I created my own sticky notes software.
The .exe is already included in the dist folder.

## Features

- **GitHub Sync**: Automatically sync notes between all your computers
- **Multiple Notes**: Browser-like tabs for organizing different notes
- **Custom Colors**: Pick any color for each note
- **Custom Names**: Name each note tab
- **Desktop Pinned**: Stays on desktop behind other windows (like a widget)
- **System Tray**: Runs quietly in the notification area
- **Auto-Save**: Notes save automatically as you type
- **Auto-Start**: Option to start automatically with Windows

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

## GitHub Sync Setup

### Prerequisites
1. Install Git from https://git-scm.com (required for sync)
2. Create a GitHub account if you don't have one

### Setup Steps

1. **Create a Private Repository on GitHub**
   - Go to https://github.com/new
   - Name it something like `my-sticky-notes`
   - Select **Private** (important for privacy!)
   - Click "Create repository"
   - Copy the HTTPS URL (e.g., `https://github.com/yourusername/my-sticky-notes.git`)

2. **Configure the App**
   - Right-click the tray icon → "GitHub Settings..."
   - Check "Enable GitHub Sync"
   - Paste your repository URL
   - Click "Test Connection"
   - Set sync interval (default: 5 minutes)
   - Click "Save"

3. **On Your Other Computers**
   - Install the app the same way
   - Use the exact same repository URL
   - Notes will automatically sync!

### Authentication

The app uses Git's built-in credential management:
- **Windows**: Git Credential Manager will prompt for login on first sync
- You can use a Personal Access Token instead of password
- Credentials are saved securely by Git

### How Sync Works

- **On startup**: Pulls latest notes from GitHub
- **Auto-sync**: Every X minutes (configurable)
- **Manual sync**: Click 🔄 button
- **On quit**: Pushes final changes
- **Merge**: Notes from different computers are merged automatically

### Sync Status Indicator

The colored dot next to the title shows sync status:
- 🟢 Green: Sync enabled and working
- 🟡 Yellow: Sync in progress
- 🔴 Red: Sync error (hover for details)
- ⚫ Gray: Sync disabled

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
