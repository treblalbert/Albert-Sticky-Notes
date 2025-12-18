"""
Albert's Sticky Notes
- Multiple note pages with tabs
- Custom colors and names per note
- Pins to desktop (stays behind other windows)
- Runs in system tray
- Auto-starts with Windows
- Remembers everything between sessions
"""

import sys
import os
import json
import uuid
import ctypes
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QSystemTrayIcon,
    QMenu, QAction, QMessageBox, QVBoxLayout, QHBoxLayout,
    QWidget, QTabWidget, QTabBar, QPushButton, QDialog,
    QLineEdit, QLabel, QColorDialog, QFormLayout, QDialogButtonBox,
    QToolButton, QSizeGrip
)
from PyQt5.QtGui import QIcon, QFont, QPixmap, QPainter, QColor, QCursor
from PyQt5.QtCore import Qt, QSize, QPoint, QTimer

# Windows API constants for desktop pinning
if sys.platform == 'win32':
    user32 = ctypes.windll.user32
    GWL_EXSTYLE = -20
    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_NOACTIVATE = 0x08000000
    HWND_BOTTOM = 1
    SWP_NOSIZE = 0x0001
    SWP_NOMOVE = 0x0002
    SWP_NOACTIVATE = 0x0010


class NoteSettingsDialog(QDialog):
    """Dialog for editing note name and color"""
    def __init__(self, parent, name="", color="#fff9c4"):
        super().__init__(parent)
        self.setWindowTitle("Note Settings")
        self.setFixedSize(300, 150)
        self.color = color
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.name_input = QLineEdit(name)
        self.name_input.setPlaceholderText("Enter note name...")
        form.addRow("Name:", self.name_input)
        
        color_layout = QHBoxLayout()
        self.color_preview = QLabel()
        self.color_preview.setFixedSize(30, 30)
        self.update_color_preview()
        
        self.color_btn = QPushButton("Choose Color")
        self.color_btn.clicked.connect(self.pick_color)
        color_layout.addWidget(self.color_preview)
        color_layout.addWidget(self.color_btn)
        color_layout.addStretch()
        form.addRow("Color:", color_layout)
        
        layout.addLayout(form)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def update_color_preview(self):
        self.color_preview.setStyleSheet(
            f"background-color: {self.color}; border: 1px solid #999; border-radius: 3px;"
        )
        
    def pick_color(self):
        color = QColorDialog.getColor(QColor(self.color), self, "Choose Note Color")
        if color.isValid():
            self.color = color.name()
            self.update_color_preview()
            
    def get_values(self):
        return self.name_input.text(), self.color


class NoteTab(QWidget):
    """Individual note tab with text editor"""
    def __init__(self, note_id, name="New Note", color="#fff9c4", content=""):
        super().__init__()
        self.note_id = note_id
        self.name = name
        self.color = color
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.text_edit = QTextEdit()
        self.text_edit.setFont(QFont('Segoe UI', 11))
        self.text_edit.setPlaceholderText('Write your notes here...')
        self.text_edit.setPlainText(content)
        layout.addWidget(self.text_edit)
        
        self.apply_color()
        
    def apply_color(self):
        qcolor = QColor(self.color)
        brightness = (qcolor.red() * 299 + qcolor.green() * 587 + qcolor.blue() * 114) / 1000
        text_color = "#333" if brightness > 128 else "#fff"
        
        self.setStyleSheet(f"""
            QWidget {{ background-color: {self.color}; }}
            QTextEdit {{
                background-color: {self.color};
                border: none;
                font-size: 14px;
                padding: 10px;
                color: {text_color};
            }}
        """)
        
    def set_color(self, color):
        self.color = color
        self.apply_color()
        
    def get_content(self):
        return self.text_edit.toPlainText()
    
    def to_dict(self):
        return {
            'id': self.note_id,
            'name': self.name,
            'color': self.color,
            'content': self.get_content()
        }


class ClosableTabBar(QTabBar):
    """Custom tab bar with close buttons"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setExpanding(False)


class StickyNotesApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.data_file = self.get_data_path()
        self.notes = []
        self.pinned_to_desktop = True
        self.drag_position = None
        
        self.init_ui()
        self.init_tray()
        self.load_notes()
        
        # Apply desktop pinning after window is shown
        QTimer.singleShot(100, self.apply_desktop_mode)
        
    def get_data_path(self):
        app_data = os.environ.get('APPDATA', os.path.expanduser('~'))
        data_dir = Path(app_data) / 'AlbertsStickyNotes'
        data_dir.mkdir(exist_ok=True)
        return data_dir / 'notes.json'
    
    def init_ui(self):
        self.setWindowTitle("Albert's Sticky Notes")
        self.setGeometry(100, 100, 400, 450)
        self.setMinimumSize(300, 200)
        
        # Frameless window
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        
        # Main style
        self.setStyleSheet("""
            QMainWindow { background-color: #2d2d2d; border-radius: 8px; }
            QTabWidget::pane { border: none; background-color: transparent; }
            QTabBar::tab {
                background-color: #444; color: #ddd;
                padding: 8px 12px; margin-right: 2px;
                border-top-left-radius: 4px; border-top-right-radius: 4px;
                min-width: 80px; max-width: 150px;
            }
            QTabBar::tab:selected { background-color: #666; color: #fff; }
            QTabBar::tab:hover { background-color: #555; }
            QPushButton {
                background-color: #444; color: #ddd; border: none;
                padding: 6px 12px; border-radius: 3px;
            }
            QPushButton:hover { background-color: #555; }
            QToolButton {
                background-color: transparent; border: none;
                padding: 4px; border-radius: 3px;
            }
            QToolButton:hover { background-color: #444; }
        """)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Custom title bar
        self.title_bar = QWidget()
        self.title_bar.setFixedHeight(36)
        self.title_bar.setStyleSheet("""
            QWidget { background-color: #1a1a1a; border-top-left-radius: 8px; border-top-right-radius: 8px; }
            QLabel { color: #fff; font-size: 13px; font-weight: bold; padding-left: 10px; }
        """)
        
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(5, 0, 5, 0)
        
        title_label = QLabel("Albert's Sticky Notes")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # New note button
        self.add_btn = QPushButton("+ New")
        self.add_btn.setFixedHeight(24)
        self.add_btn.clicked.connect(self.add_new_note)
        title_layout.addWidget(self.add_btn)
        
        # Settings button
        self.settings_btn = QToolButton()
        self.settings_btn.setText("⚙")
        self.settings_btn.setFixedSize(28, 28)
        self.settings_btn.setStyleSheet("font-size: 16px; color: #ddd;")
        self.settings_btn.setToolTip("Edit note settings")
        self.settings_btn.clicked.connect(self.edit_current_note)
        title_layout.addWidget(self.settings_btn)
        
        # Pin button
        self.pin_btn = QToolButton()
        self.pin_btn.setText("📌")
        self.pin_btn.setFixedSize(28, 28)
        self.pin_btn.setStyleSheet("font-size: 14px; color: #ddd;")
        self.pin_btn.setToolTip("Toggle desktop/floating mode")
        self.pin_btn.clicked.connect(self.toggle_desktop_mode)
        title_layout.addWidget(self.pin_btn)
        
        # Minimize button
        min_btn = QToolButton()
        min_btn.setText("—")
        min_btn.setFixedSize(28, 28)
        min_btn.setStyleSheet("font-size: 14px; color: #ddd;")
        min_btn.setToolTip("Minimize to tray")
        min_btn.clicked.connect(self.hide)
        title_layout.addWidget(min_btn)
        
        layout.addWidget(self.title_bar)
        
        # Content area
        content = QWidget()
        content.setStyleSheet("background-color: #2d2d2d;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(5, 5, 5, 5)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setTabBar(ClosableTabBar())
        self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        content_layout.addWidget(self.tabs)
        
        # Size grip for resizing
        grip_layout = QHBoxLayout()
        grip_layout.addStretch()
        self.size_grip = QSizeGrip(self)
        self.size_grip.setStyleSheet("background: transparent;")
        grip_layout.addWidget(self.size_grip)
        content_layout.addLayout(grip_layout)
        
        layout.addWidget(content)
        
    def create_tray_icon(self):
        pixmap = QPixmap(64, 64)
        pixmap.fill(QColor('#ffd600'))
        painter = QPainter(pixmap)
        painter.setPen(QColor('#333'))
        painter.setFont(QFont('Arial', 24, QFont.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, 'A')
        painter.end()
        return QIcon(pixmap)
        
    def init_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.create_tray_icon())
        self.tray_icon.setToolTip("Albert's Sticky Notes")
        
        tray_menu = QMenu()
        
        show_action = QAction('Show/Hide', self)
        show_action.triggered.connect(self.toggle_visibility)
        tray_menu.addAction(show_action)
        
        desktop_action = QAction('Toggle Desktop/Floating', self)
        desktop_action.triggered.connect(self.toggle_desktop_mode)
        tray_menu.addAction(desktop_action)
        
        tray_menu.addSeparator()
        
        new_action = QAction('New Note', self)
        new_action.triggered.connect(self.add_new_note)
        tray_menu.addAction(new_action)
        
        tray_menu.addSeparator()
        
        startup_action = QAction('Add to Startup', self)
        startup_action.triggered.connect(self.add_to_startup)
        tray_menu.addAction(startup_action)
        
        remove_action = QAction('Remove from Startup', self)
        remove_action.triggered.connect(self.remove_from_startup)
        tray_menu.addAction(remove_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction('Quit', self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_clicked)
        self.tray_icon.show()
        
    def pin_to_desktop(self):
        """Pin window to desktop using Windows API"""
        if sys.platform != 'win32':
            return
            
        hwnd = int(self.winId())
        
        # Find the Program Manager (desktop) window
        progman = user32.FindWindowW("Progman", None)
        
        # Send message to spawn WorkerW behind desktop icons
        user32.SendMessageTimeoutW(progman, 0x052C, 0, 0, 0, 1000, None)
        
        # Find the WorkerW window
        def enum_windows_callback(hwnd_found, lParam):
            shell_view = user32.FindWindowExW(hwnd_found, None, "SHELLDLL_DefView", None)
            if shell_view:
                # Found the right WorkerW, get the one behind it
                worker_w = user32.FindWindowExW(None, hwnd_found, "WorkerW", None)
                if worker_w:
                    ctypes.windll.user32.SetParent(hwnd, worker_w)
            return True
        
        # Try simple approach first - just send to bottom
        user32.SetWindowPos(hwnd, HWND_BOTTOM, 0, 0, 0, 0, 
                           SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
        
    def unpin_from_desktop(self):
        """Restore window to normal floating mode"""
        if sys.platform != 'win32':
            return
            
        hwnd = int(self.winId())
        # Restore parent to desktop (0)
        user32.SetParent(hwnd, 0)
        
    def apply_desktop_mode(self):
        """Apply current desktop/floating mode"""
        if self.pinned_to_desktop:
            self.pin_btn.setText("📌")
            self.pin_btn.setToolTip("Pinned to desktop. Click for floating mode.")
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnBottomHint)
            self.show()
            # Use timer to ensure window is ready
            QTimer.singleShot(50, self.pin_to_desktop)
        else:
            self.unpin_from_desktop()
            self.pin_btn.setText("📍")
            self.pin_btn.setToolTip("Floating mode. Click to pin to desktop.")
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
            self.show()
            self.raise_()
            self.activateWindow()
            
    def toggle_desktop_mode(self):
        self.pinned_to_desktop = not self.pinned_to_desktop
        self.apply_desktop_mode()
        self.auto_save()
        
    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            if not self.pinned_to_desktop:
                self.raise_()
                self.activateWindow()
            else:
                QTimer.singleShot(50, self.pin_to_desktop)
                
    def tray_clicked(self, reason):
        if reason in (QSystemTrayIcon.DoubleClick, QSystemTrayIcon.Trigger):
            self.toggle_visibility()
            
    # Title bar dragging
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.title_bar.geometry().contains(event.pos()):
                self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()
                
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_position:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
            
    def mouseReleaseEvent(self, event):
        self.drag_position = None
        if self.pinned_to_desktop:
            QTimer.singleShot(50, self.pin_to_desktop)
            
    def add_new_note(self):
        note_id = str(uuid.uuid4())[:8]
        note_num = self.tabs.count() + 1
        name = f"Note {note_num}"
        
        dialog = NoteSettingsDialog(self, name)
        if dialog.exec_() == QDialog.Accepted:
            name, color = dialog.get_values()
            if not name.strip():
                name = f"Note {note_num}"
        else:
            return
            
        note = NoteTab(note_id, name, color)
        note.text_edit.textChanged.connect(self.auto_save)
        self.notes.append(note)
        index = self.tabs.addTab(note, name)
        self.tabs.setCurrentIndex(index)
        self.auto_save()
        
    def close_tab(self, index):
        if self.tabs.count() <= 1:
            QMessageBox.information(self, "Info", "You need at least one note!")
            return
            
        reply = QMessageBox.question(self, "Delete Note",
            "Delete this note?", QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            note = self.tabs.widget(index)
            self.notes.remove(note)
            self.tabs.removeTab(index)
            self.auto_save()
            
    def edit_current_note(self):
        if self.tabs.count() == 0:
            return
        current = self.tabs.currentWidget()
        if not current:
            return
            
        dialog = NoteSettingsDialog(self, current.name, current.color)
        if dialog.exec_() == QDialog.Accepted:
            name, color = dialog.get_values()
            if name.strip():
                current.name = name
                self.tabs.setTabText(self.tabs.currentIndex(), name)
            current.set_color(color)
            self.auto_save()
            
    def load_notes(self):
        try:
            if self.data_file.exists():
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    if 'geometry' in data:
                        g = data['geometry']
                        self.setGeometry(g['x'], g['y'], g['w'], g['h'])
                        
                    self.pinned_to_desktop = data.get('pinned_to_desktop', True)
                    
                    for note_data in data.get('notes', []):
                        note = NoteTab(
                            note_data.get('id', str(uuid.uuid4())[:8]),
                            note_data.get('name', 'Note'),
                            note_data.get('color', '#fff9c4'),
                            note_data.get('content', '')
                        )
                        note.text_edit.textChanged.connect(self.auto_save)
                        self.notes.append(note)
                        self.tabs.addTab(note, note.name)
                        
                    active = data.get('active_tab', 0)
                    if 0 <= active < self.tabs.count():
                        self.tabs.setCurrentIndex(active)
        except Exception as e:
            print(f'Error loading: {e}')
            
        if self.tabs.count() == 0:
            note = NoteTab(str(uuid.uuid4())[:8], "Welcome", "#fff9c4",
                "Welcome to Albert's Sticky Notes!\n\n"
                "• Click '+ New' to add notes\n"
                "• Click ⚙ to change name/color\n"
                "• Click 📌 to toggle desktop/floating mode\n"
                "• Notes save automatically!")
            note.text_edit.textChanged.connect(self.auto_save)
            self.notes.append(note)
            self.tabs.addTab(note, note.name)
            
    def auto_save(self):
        try:
            data = {
                'geometry': {
                    'x': self.x(), 'y': self.y(),
                    'w': self.width(), 'h': self.height()
                },
                'active_tab': self.tabs.currentIndex(),
                'pinned_to_desktop': self.pinned_to_desktop,
                'notes': [note.to_dict() for note in self.notes]
            }
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f'Error saving: {e}')
            
    def add_to_startup(self):
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\CurrentVersion\Run', 0, winreg.KEY_SET_VALUE)
            exe_path = sys.executable if getattr(sys, 'frozen', False) else f'"{sys.executable}" "{os.path.abspath(__file__)}"'
            winreg.SetValueEx(key, 'AlbertsStickyNotes', 0, winreg.REG_SZ, exe_path)
            winreg.CloseKey(key)
            QMessageBox.information(self, 'Success', 'Added to Windows startup!')
        except Exception as e:
            QMessageBox.warning(self, 'Error', f'Could not add to startup: {e}')
            
    def remove_from_startup(self):
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\CurrentVersion\Run', 0, winreg.KEY_SET_VALUE)
            try:
                winreg.DeleteValue(key, 'AlbertsStickyNotes')
                QMessageBox.information(self, 'Success', 'Removed from startup!')
            except FileNotFoundError:
                QMessageBox.information(self, 'Info', 'Not in startup.')
            winreg.CloseKey(key)
        except Exception as e:
            QMessageBox.warning(self, 'Error', f'Could not remove: {e}')
    
    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage("Albert's Sticky Notes",
            'Running in tray. Double-click to open.', QSystemTrayIcon.Information, 2000)
        
    def quit_app(self):
        self.auto_save()
        QApplication.quit()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    window = StickyNotesApp()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
