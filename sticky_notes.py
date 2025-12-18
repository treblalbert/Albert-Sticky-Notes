"""
Customizable Sticky Notes & Calendar
- Customizable app name (double-click to change)
- Multiple note pages with tabs
- Text formatting (bold, italic, underline)
- Size options (small, medium, large)
- Full calendar with daily notes
- Optional GitHub sync across computers
- One-click push/pull to GitHub
- Pins to desktop
- Fully resizable window
- Runs in system tray
"""

import sys
import os
import json
import uuid
import ctypes
import subprocess
from pathlib import Path
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QSystemTrayIcon,
    QMenu, QAction, QMessageBox, QVBoxLayout, QHBoxLayout,
    QWidget, QTabWidget, QTabBar, QPushButton, QDialog,
    QLineEdit, QLabel, QColorDialog, QFormLayout, QDialogButtonBox,
    QToolButton, QCheckBox, QGroupBox, QFileDialog, QCalendarWidget,
    QComboBox, QInputDialog
)
from PyQt5.QtGui import QIcon, QFont, QPixmap, QPainter, QColor, QTextCharFormat, QBrush, QTextCursor
from PyQt5.QtCore import Qt, QTimer, QDate

# Windows API constants
if sys.platform == 'win32':
    user32 = ctypes.windll.user32
    HWND_BOTTOM = 1
    SWP_NOSIZE = 0x0001
    SWP_NOMOVE = 0x0002
    SWP_NOACTIVATE = 0x0010

# Size presets
SIZE_PRESETS = {
    'Small': {'font': 10, 'ui': 0.85, 'icon': 12, 'btn': 22, 'tab_padding': '6px 10px'},
    'Medium': {'font': 12, 'ui': 1.0, 'icon': 14, 'btn': 26, 'tab_padding': '8px 12px'},
    'Large': {'font': 15, 'ui': 1.2, 'icon': 18, 'btn': 32, 'tab_padding': '10px 14px'}
}


class GitHubSync:
    """Handle GitHub repository synchronization"""
    
    def __init__(self, repo_path, data_file_name="notes.json"):
        self.repo_path = Path(repo_path) if repo_path else None
        self.data_file_name = data_file_name
        
    def is_configured(self):
        return self.repo_path and self.repo_path.exists()
    
    def get_notes_file(self):
        return self.repo_path / self.data_file_name if self.repo_path else None
    
    def get_calendar_file(self):
        return self.repo_path / "calendar.json" if self.repo_path else None
        
    def run_git(self, *args):
        if not self.is_configured():
            return False, "No repo configured"
        try:
            result = subprocess.run(
                ['git'] + list(args),
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            return result.returncode == 0, result.stdout + result.stderr
        except FileNotFoundError:
            return False, "Git not found. Install from git-scm.com"
        except Exception as e:
            return False, str(e)
    
    def pull(self):
        return self.run_git('pull', '--rebase')
    
    def push_all(self, message="Update notes"):
        self.run_git('add', '.')
        success, status = self.run_git('status', '--porcelain')
        if not status.strip():
            return True, "No changes to push"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        success, msg = self.run_git('commit', '-m', f'{message} - {timestamp}')
        if not success and "nothing to commit" not in msg:
            return False, msg
        return self.run_git('push')
    
    def clone_repo(self, repo_url, target_path):
        try:
            result = subprocess.run(
                ['git', 'clone', repo_url, str(target_path)],
                capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, str(e)


class SettingsDialog(QDialog):
    """Settings dialog with size options and sync config"""
    
    def __init__(self, parent, current_size="Medium", current_repo="", sync_enabled=False):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(480, 380)
        
        layout = QVBoxLayout(self)
        
        # Display settings
        display_group = QGroupBox("Display")
        display_layout = QFormLayout(display_group)
        
        self.size_combo = QComboBox()
        self.size_combo.addItems(['Small', 'Medium', 'Large'])
        self.size_combo.setCurrentText(current_size)
        display_layout.addRow("Interface Size:", self.size_combo)
        
        layout.addWidget(display_group)
        
        # Sync settings
        sync_group = QGroupBox("GitHub Sync")
        sync_layout = QVBoxLayout(sync_group)
        
        self.enable_check = QCheckBox("Enable GitHub Sync")
        self.enable_check.setChecked(sync_enabled)
        self.enable_check.toggled.connect(self.toggle_sync_options)
        sync_layout.addWidget(self.enable_check)
        
        info = QLabel("Sync notes & calendar across computers.\nWorks with private repos if logged into GitHub.")
        info.setStyleSheet("color: #666; font-size: 11px;")
        info.setWordWrap(True)
        sync_layout.addWidget(info)
        
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("Repo:"))
        self.path_input = QLineEdit(current_repo)
        self.path_input.setPlaceholderText("Path to local git repository...")
        path_layout.addWidget(self.path_input)
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_folder)
        path_layout.addWidget(browse_btn)
        sync_layout.addLayout(path_layout)
        
        clone_layout = QHBoxLayout()
        clone_layout.addWidget(QLabel("Clone:"))
        self.clone_url = QLineEdit()
        self.clone_url.setPlaceholderText("https://github.com/user/repo.git")
        clone_layout.addWidget(self.clone_url)
        clone_btn = QPushButton("Clone")
        clone_btn.clicked.connect(self.clone_repo)
        clone_layout.addWidget(clone_btn)
        sync_layout.addLayout(clone_layout)
        
        self.status_label = QLabel("")
        sync_layout.addWidget(self.status_label)
        
        layout.addWidget(sync_group)
        
        # Store references for toggling
        self.sync_widgets = [info, self.path_input, browse_btn, self.clone_url, clone_btn]
        self.toggle_sync_options(sync_enabled)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def toggle_sync_options(self, enabled):
        for w in self.sync_widgets:
            w.setEnabled(enabled)
            
    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Git Repository")
        if folder:
            self.path_input.setText(folder)
            git_dir = Path(folder) / '.git'
            if git_dir.exists():
                self.status_label.setText("✓ Valid Git repository")
                self.status_label.setStyleSheet("color: green;")
            else:
                self.status_label.setText("⚠ Not a Git repository")
                self.status_label.setStyleSheet("color: orange;")
                
    def clone_repo(self):
        url = self.clone_url.text().strip()
        if not url:
            return
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if not folder:
            return
        repo_name = url.split('/')[-1].replace('.git', '')
        target = Path(folder) / repo_name
        self.status_label.setText("Cloning...")
        self.status_label.setStyleSheet("color: blue;")
        QApplication.processEvents()
        sync = GitHubSync(None)
        success, msg = sync.clone_repo(url, target)
        if success:
            self.path_input.setText(str(target))
            self.status_label.setText("✓ Cloned!")
            self.status_label.setStyleSheet("color: green;")
        else:
            self.status_label.setText("✗ Failed")
            self.status_label.setStyleSheet("color: red;")
            
    def get_values(self):
        return {
            'size': self.size_combo.currentText(),
            'sync_enabled': self.enable_check.isChecked(),
            'repo_path': self.path_input.text().strip()
        }


class NoteSettingsDialog(QDialog):
    def __init__(self, parent, name="", color="#fff9c4"):
        super().__init__(parent)
        self.setWindowTitle("Note Settings")
        self.setFixedSize(300, 150)
        self.color = color
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.name_input = QLineEdit(name)
        form.addRow("Name:", self.name_input)
        
        color_layout = QHBoxLayout()
        self.color_preview = QLabel()
        self.color_preview.setFixedSize(30, 30)
        self.update_color_preview()
        self.color_btn = QPushButton("Choose")
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
        self.color_preview.setStyleSheet(f"background-color: {self.color}; border: 1px solid #999; border-radius: 3px;")
        
    def pick_color(self):
        color = QColorDialog.getColor(QColor(self.color), self)
        if color.isValid():
            self.color = color.name()
            self.update_color_preview()
            
    def get_values(self):
        return self.name_input.text(), self.color


class NoteTab(QWidget):
    def __init__(self, note_id, name="New Note", color="#fff9c4", content="", font_size=12):
        super().__init__()
        self.note_id = note_id
        self.name = name
        self.color = color
        self.font_size = font_size
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Formatting toolbar
        self.toolbar = QWidget()
        self.toolbar.setFixedHeight(28)
        self.toolbar.setStyleSheet("background-color: rgba(0,0,0,0.2); border: none;")
        tb_layout = QHBoxLayout(self.toolbar)
        tb_layout.setContentsMargins(4, 2, 4, 2)
        tb_layout.setSpacing(2)
        
        self.bold_btn = QPushButton("B")
        self.bold_btn.setFixedSize(24, 24)
        self.bold_btn.setFont(QFont("Arial", 10, QFont.Bold))
        self.bold_btn.setToolTip("Bold (Ctrl+B)")
        self.bold_btn.clicked.connect(self.toggle_bold)
        tb_layout.addWidget(self.bold_btn)
        
        self.italic_btn = QPushButton("I")
        self.italic_btn.setFixedSize(24, 24)
        self.italic_btn.setFont(QFont("Arial", 10, QFont.Normal, True))
        self.italic_btn.setToolTip("Italic (Ctrl+I)")
        self.italic_btn.clicked.connect(self.toggle_italic)
        tb_layout.addWidget(self.italic_btn)
        
        self.underline_btn = QPushButton("U")
        self.underline_btn.setFixedSize(24, 24)
        font = QFont("Arial", 10)
        font.setUnderline(True)
        self.underline_btn.setFont(font)
        self.underline_btn.setToolTip("Underline (Ctrl+U)")
        self.underline_btn.clicked.connect(self.toggle_underline)
        tb_layout.addWidget(self.underline_btn)
        
        tb_layout.addStretch()
        layout.addWidget(self.toolbar)
        
        # Text editor
        self.text_edit = QTextEdit()
        self.text_edit.setFont(QFont('Segoe UI', font_size))
        self.text_edit.setPlaceholderText('Write your notes here...')
        if content:
            if content.startswith('<!') or content.startswith('<'):
                self.text_edit.setHtml(content)
            else:
                self.text_edit.setPlainText(content)
        layout.addWidget(self.text_edit)
        
        self.apply_color()
        
    def toggle_bold(self):
        fmt = self.text_edit.currentCharFormat()
        fmt.setFontWeight(QFont.Normal if fmt.fontWeight() == QFont.Bold else QFont.Bold)
        self.text_edit.mergeCurrentCharFormat(fmt)
        
    def toggle_italic(self):
        fmt = self.text_edit.currentCharFormat()
        fmt.setFontItalic(not fmt.fontItalic())
        self.text_edit.mergeCurrentCharFormat(fmt)
        
    def toggle_underline(self):
        fmt = self.text_edit.currentCharFormat()
        fmt.setFontUnderline(not fmt.fontUnderline())
        self.text_edit.mergeCurrentCharFormat(fmt)
        
    def apply_color(self):
        qcolor = QColor(self.color)
        brightness = (qcolor.red() * 299 + qcolor.green() * 587 + qcolor.blue() * 114) / 1000
        text_color = "#333" if brightness > 128 else "#fff"
        btn_bg = "rgba(255,255,255,0.3)" if brightness > 128 else "rgba(0,0,0,0.3)"
        
        self.setStyleSheet(f"""
            QWidget {{ background-color: {self.color}; }}
            QTextEdit {{
                background-color: {self.color};
                border: none;
                padding: 8px;
                color: {text_color};
            }}
            QPushButton {{
                background-color: {btn_bg};
                color: {text_color};
                border: none;
                border-radius: 3px;
            }}
            QPushButton:hover {{ background-color: rgba(128,128,128,0.4); }}
        """)
        
    def set_color(self, color):
        self.color = color
        self.apply_color()
        
    def set_font_size(self, size):
        self.font_size = size
        self.text_edit.setFont(QFont('Segoe UI', size))
        
    def get_content(self):
        return self.text_edit.toHtml()
    
    def to_dict(self):
        return {
            'id': self.note_id,
            'name': self.name,
            'color': self.color,
            'content': self.get_content()
        }


class ClosableTabBar(QTabBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setExpanding(False)


class ClickableLabel(QLabel):
    """Label that can be double-clicked to edit"""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.main_window = parent
        
    def mouseDoubleClickEvent(self, event):
        if self.main_window:
            self.main_window.change_app_name()


class CalendarWindow(QDialog):
    def __init__(self, parent, calendar_data, save_callback, font_size=12):
        super().__init__(parent)
        self.calendar_data = calendar_data
        self.save_callback = save_callback
        self.current_date_str = None
        self.font_size = font_size
        
        self.setWindowTitle("Calendar")
        self.setMinimumSize(650, 450)
        self.resize(750, 550)
        self.init_ui()
        
    def init_ui(self):
        self.setStyleSheet(f"""
            QDialog {{ background-color: #2d2d2d; }}
            QCalendarWidget {{ background-color: #3d3d3d; color: #fff; }}
            QCalendarWidget QToolButton {{
                color: #fff; background-color: #444;
                border-radius: 4px; padding: 5px; margin: 2px;
            }}
            QCalendarWidget QToolButton:hover {{ background-color: #555; }}
            QCalendarWidget QMenu {{ background-color: #444; color: #fff; }}
            QCalendarWidget QSpinBox {{ background-color: #444; color: #fff; border: none; }}
            QCalendarWidget QTableView {{
                background-color: #3d3d3d;
                selection-background-color: #ffd600;
                selection-color: #333;
            }}
            QTextEdit {{
                background-color: #3d3d3d; color: #fff;
                border: none; border-radius: 4px;
                padding: 10px; font-size: {self.font_size}px;
            }}
            QLabel {{ color: #fff; font-size: {self.font_size + 2}px; font-weight: bold; }}
            QPushButton {{
                background-color: #444; color: #ddd;
                border: none; padding: 8px 16px; border-radius: 4px;
            }}
            QPushButton:hover {{ background-color: #555; }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Left - Calendar
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.calendar.clicked.connect(self.on_date_selected)
        self.calendar.setMinimumWidth(320)
        self.highlight_dates()
        left_layout.addWidget(self.calendar)
        
        today_btn = QPushButton("Go to Today")
        today_btn.clicked.connect(self.go_to_today)
        left_layout.addWidget(today_btn)
        layout.addWidget(left)
        
        # Right - Note
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.date_label = QLabel("Select a date")
        right_layout.addWidget(self.date_label)
        
        self.day_note = QTextEdit()
        self.day_note.setPlaceholderText("Notes for this day...")
        self.day_note.textChanged.connect(self.on_note_changed)
        right_layout.addWidget(self.day_note)
        
        btn_layout = QHBoxLayout()
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_day)
        btn_layout.addWidget(clear_btn)
        btn_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        right_layout.addLayout(btn_layout)
        
        layout.addWidget(right, 1)
        self.go_to_today()
        
    def highlight_dates(self):
        fmt = QTextCharFormat()
        fmt.setBackground(QBrush(QColor("#5c6bc0")))
        fmt.setForeground(QBrush(QColor("#fff")))
        for date_str, text in self.calendar_data.items():
            if text.strip():
                try:
                    y, m, d = map(int, date_str.split('-'))
                    self.calendar.setDateTextFormat(QDate(y, m, d), fmt)
                except:
                    pass
                    
    def go_to_today(self):
        today = QDate.currentDate()
        self.calendar.setSelectedDate(today)
        self.on_date_selected(today)
        
    def on_date_selected(self, qdate):
        self.current_date_str = qdate.toString("yyyy-MM-dd")
        self.date_label.setText(f"{qdate.toString('dddd, MMMM d, yyyy')}")
        self.day_note.blockSignals(True)
        self.day_note.setPlainText(self.calendar_data.get(self.current_date_str, ""))
        self.day_note.blockSignals(False)
        
    def on_note_changed(self):
        if self.current_date_str:
            self.calendar_data[self.current_date_str] = self.day_note.toPlainText()
            self.save_callback()
            self.highlight_dates()
            
    def clear_day(self):
        if self.current_date_str:
            self.day_note.clear()
            self.calendar_data.pop(self.current_date_str, None)
            self.save_callback()
            self.highlight_dates()


class StickyNotesApp(QMainWindow):
    
    def __init__(self):
        super().__init__()
        self.notes = []
        self.calendar_data = {}
        self.pinned_to_desktop = True
        self.drag_position = None
        self.resize_edge = None
        self.resize_margin = 8
        
        # Customizable settings
        self.app_name = "Albert's Sticky Notes"
        self.size_preset = "Medium"
        
        # GitHub sync
        self.github_sync = None
        self.sync_enabled = False
        self.sync_repo_path = ""
        
        self.calendar_window = None
        
        self.init_ui()
        self.init_tray()
        self.load_notes()
        
        QTimer.singleShot(100, self.apply_desktop_mode)
        QTimer.singleShot(500, self.startup_sync)
        
    def get_data_dir(self):
        app_data = os.environ.get('APPDATA', os.path.expanduser('~'))
        data_dir = Path(app_data) / 'AlbertsStickyNotes'
        data_dir.mkdir(exist_ok=True)
        return data_dir
    
    def get_size(self):
        return SIZE_PRESETS.get(self.size_preset, SIZE_PRESETS['Medium'])
    
    def init_ui(self):
        self.setWindowTitle(self.app_name)
        self.setGeometry(100, 100, 420, 480)
        self.setMinimumSize(280, 200)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.setMouseTracking(True)
        
        self.apply_styles()
        
        central = QWidget()
        central.setMouseTracking(True)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(0)
        
        # Title bar
        self.title_bar = QWidget()
        self.title_bar.setMouseTracking(True)
        self.title_bar.setObjectName("titleBar")
        
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(8, 0, 4, 0)
        title_layout.setSpacing(3)
        
        # Clickable title label
        self.title_label = ClickableLabel(self.app_name, self)
        self.title_label.setObjectName("titleLabel")
        self.title_label.setToolTip("Double-click to change name")
        title_layout.addWidget(self.title_label)
        
        self.sync_indicator = QLabel("")
        title_layout.addWidget(self.sync_indicator)
        
        title_layout.addStretch()
        
        # Buttons
        self.add_btn = QPushButton("+")
        self.add_btn.setToolTip("New Note")
        self.add_btn.clicked.connect(self.add_new_note)
        title_layout.addWidget(self.add_btn)
        
        self.settings_btn = QToolButton()
        self.settings_btn.setText("⚙")
        self.settings_btn.setToolTip("Note settings")
        self.settings_btn.clicked.connect(self.edit_current_note)
        title_layout.addWidget(self.settings_btn)
        
        self.calendar_btn = QToolButton()
        self.calendar_btn.setText("📅")
        self.calendar_btn.setToolTip("Calendar")
        self.calendar_btn.clicked.connect(self.toggle_calendar)
        title_layout.addWidget(self.calendar_btn)
        
        self.pull_btn = QToolButton()
        self.pull_btn.setText("⬇")
        self.pull_btn.setToolTip("Pull from GitHub")
        self.pull_btn.clicked.connect(self.pull_from_github)
        title_layout.addWidget(self.pull_btn)
        
        self.push_btn = QToolButton()
        self.push_btn.setText("⬆")
        self.push_btn.setToolTip("Push to GitHub")
        self.push_btn.clicked.connect(self.push_to_github)
        title_layout.addWidget(self.push_btn)
        
        self.config_btn = QToolButton()
        self.config_btn.setText("☰")
        self.config_btn.setToolTip("Settings")
        self.config_btn.clicked.connect(self.show_settings)
        title_layout.addWidget(self.config_btn)
        
        self.pin_btn = QToolButton()
        self.pin_btn.setText("📌")
        self.pin_btn.setToolTip("Toggle desktop/floating")
        self.pin_btn.clicked.connect(self.toggle_desktop_mode)
        title_layout.addWidget(self.pin_btn)
        
        min_btn = QToolButton()
        min_btn.setText("—")
        min_btn.setToolTip("Minimize")
        min_btn.clicked.connect(self.hide)
        title_layout.addWidget(min_btn)
        
        layout.addWidget(self.title_bar)
        
        # Content
        content = QWidget()
        content.setMouseTracking(True)
        content.setObjectName("content")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(4, 4, 4, 4)
        
        self.tabs = QTabWidget()
        self.tabs.setMouseTracking(True)
        self.tabs.setTabBar(ClosableTabBar())
        self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        content_layout.addWidget(self.tabs)
        
        layout.addWidget(content)
        
    def apply_styles(self):
        s = self.get_size()
        btn_size = s['btn']
        icon_size = s['icon']
        
        self.setStyleSheet(f"""
            QMainWindow {{ background-color: #2d2d2d; }}
            #titleBar {{
                background-color: #1a1a1a;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                min-height: {btn_size + 6}px;
                max-height: {btn_size + 6}px;
            }}
            #titleLabel {{
                color: #fff;
                font-size: {s['font']}px;
                font-weight: bold;
            }}
            #content {{ background-color: #2d2d2d; }}
            QTabWidget::pane {{ border: none; }}
            QTabBar::tab {{
                background-color: #444; color: #ddd;
                padding: {s['tab_padding']}; margin-right: 2px;
                border-top-left-radius: 4px; border-top-right-radius: 4px;
                font-size: {s['font'] - 1}px;
                min-width: 50px; max-width: 110px;
            }}
            QTabBar::tab:selected {{ background-color: #666; color: #fff; }}
            QTabBar::tab:hover {{ background-color: #555; }}
            QPushButton, QToolButton {{
                background-color: #444; color: #ddd; border: none;
                border-radius: 3px;
                font-size: {icon_size}px;
                min-width: {btn_size}px; min-height: {btn_size}px;
                max-width: {btn_size}px; max-height: {btn_size}px;
            }}
            QPushButton:hover, QToolButton:hover {{ background-color: #555; }}
        """)
        
        # Update title bar height
        if hasattr(self, 'title_bar'):
            self.title_bar.setFixedHeight(int(btn_size + 6))
            
    def change_app_name(self):
        name, ok = QInputDialog.getText(self, "Change Name", "Enter new app name:", text=self.app_name)
        if ok and name.strip():
            self.app_name = name.strip()
            self.title_label.setText(self.app_name)
            self.setWindowTitle(self.app_name)
            self.tray_icon.setToolTip(self.app_name)
            self.save_config()
        
    def create_tray_icon(self):
        pixmap = QPixmap(64, 64)
        pixmap.fill(QColor('#ffd600'))
        painter = QPainter(pixmap)
        painter.setPen(QColor('#333'))
        painter.setFont(QFont('Arial', 24, QFont.Bold))
        # Use first letter of app name
        letter = self.app_name[0].upper() if self.app_name else 'N'
        painter.drawText(pixmap.rect(), Qt.AlignCenter, letter)
        painter.end()
        return QIcon(pixmap)
        
    def init_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.create_tray_icon())
        self.tray_icon.setToolTip(self.app_name)
        
        tray_menu = QMenu()
        
        tray_menu.addAction("Show/Hide", self.toggle_visibility)
        tray_menu.addAction("Calendar", self.toggle_calendar)
        tray_menu.addSeparator()
        tray_menu.addAction("Pull from GitHub", self.pull_from_github)
        tray_menu.addAction("Push to GitHub", self.push_to_github)
        tray_menu.addAction("Settings...", self.show_settings)
        tray_menu.addSeparator()
        tray_menu.addAction("Desktop/Floating", self.toggle_desktop_mode)
        tray_menu.addAction("New Note", self.add_new_note)
        tray_menu.addSeparator()
        tray_menu.addAction("Add to Startup", self.add_to_startup)
        tray_menu.addAction("Remove from Startup", self.remove_from_startup)
        tray_menu.addSeparator()
        tray_menu.addAction("Quit", self.quit_app)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_clicked)
        self.tray_icon.show()
    
    # === Settings ===
    
    def show_settings(self):
        dialog = SettingsDialog(self, self.size_preset, self.sync_repo_path, self.sync_enabled)
        if dialog.exec_() == QDialog.Accepted:
            values = dialog.get_values()
            
            # Size change
            if values['size'] != self.size_preset:
                self.size_preset = values['size']
                self.apply_styles()
                self.update_notes_font_size()
                
            # Sync settings
            self.sync_enabled = values['sync_enabled']
            self.sync_repo_path = values['repo_path']
            
            if self.sync_enabled and self.sync_repo_path:
                self.github_sync = GitHubSync(self.sync_repo_path)
                self.update_sync_indicator("☁", "#888", "Sync enabled")
            else:
                self.github_sync = None
                self.update_sync_indicator("", "", "")
                
            self.save_config()
            
            if self.sync_enabled:
                self.pull_from_github()
                
    def update_notes_font_size(self):
        s = self.get_size()
        for note in self.notes:
            note.set_font_size(s['font'])
    
    # === Calendar ===
    
    def toggle_calendar(self):
        if self.calendar_window and self.calendar_window.isVisible():
            self.calendar_window.close()
            self.calendar_window = None
        else:
            s = self.get_size()
            self.calendar_window = CalendarWindow(None, self.calendar_data, self.save_calendar, s['font'])
            self.calendar_window.setWindowTitle(f"{self.app_name} - Calendar")
            self.calendar_window.show()
            
    def save_calendar(self):
        try:
            with open(self.get_data_dir() / 'calendar.json', 'w', encoding='utf-8') as f:
                json.dump(self.calendar_data, f, ensure_ascii=False, indent=2)
            if self.sync_enabled and self.github_sync:
                cal_file = self.github_sync.get_calendar_file()
                if cal_file:
                    with open(cal_file, 'w', encoding='utf-8') as f:
                        json.dump(self.calendar_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving calendar: {e}")
            
    def load_calendar(self):
        try:
            cal_path = self.get_data_dir() / 'calendar.json'
            if cal_path.exists():
                with open(cal_path, 'r', encoding='utf-8') as f:
                    self.calendar_data = json.load(f)
        except:
            self.calendar_data = {}
        
    # === GitHub Sync ===
    
    def update_sync_indicator(self, icon, color, tooltip):
        self.sync_indicator.setText(icon)
        self.sync_indicator.setStyleSheet(f"font-size: 12px; color: {color};")
        self.sync_indicator.setToolTip(tooltip)
        
    def startup_sync(self):
        if self.sync_enabled and self.github_sync and self.github_sync.is_configured():
            self.pull_from_github(show_message=False)
            
    def push_to_github(self):
        if not self.sync_enabled or not self.github_sync:
            QMessageBox.information(self, "Push", "Sync not enabled. Go to Settings.")
            return
        if not self.github_sync.is_configured():
            QMessageBox.warning(self, "Push", "Repository not configured.")
            return
            
        self.update_sync_indicator("⬆", "#ffd600", "Pushing...")
        QApplication.processEvents()
        
        try:
            self.save_notes_to_repo()
            self.save_calendar_to_repo()
            success, msg = self.github_sync.push_all("Update notes & calendar")
            
            if success or "No changes" in msg:
                self.update_sync_indicator("☁", "#4caf50", f"Pushed {datetime.now().strftime('%H:%M')}")
                self.tray_icon.showMessage("Push Complete", "Changes pushed!", QSystemTrayIcon.Information, 2000)
            else:
                self.update_sync_indicator("☁", "#f44336", "Push failed")
                QMessageBox.warning(self, "Push Failed", msg)
        except Exception as e:
            self.update_sync_indicator("☁", "#f44336", str(e))
            QMessageBox.warning(self, "Error", str(e))
            
    def pull_from_github(self, show_message=True):
        if not self.sync_enabled or not self.github_sync:
            if show_message:
                QMessageBox.information(self, "Pull", "Sync not enabled.")
            return
        if not self.github_sync.is_configured():
            if show_message:
                QMessageBox.warning(self, "Pull", "Repository not configured.")
            return
            
        self.update_sync_indicator("⬇", "#ffd600", "Pulling...")
        QApplication.processEvents()
        
        try:
            success, msg = self.github_sync.pull()
            
            if success or "Already up to date" in msg:
                self.load_notes_from_repo()
                self.load_calendar_from_repo()
                self.update_sync_indicator("☁", "#4caf50", f"Synced {datetime.now().strftime('%H:%M')}")
                if show_message:
                    self.tray_icon.showMessage("Pull Complete", "Latest loaded!", QSystemTrayIcon.Information, 2000)
            else:
                self.update_sync_indicator("☁", "#f44336", "Pull failed")
                if show_message:
                    QMessageBox.warning(self, "Pull Failed", msg)
        except Exception as e:
            self.update_sync_indicator("☁", "#f44336", str(e))
            if show_message:
                QMessageBox.warning(self, "Error", str(e))
                
    def save_notes_to_repo(self):
        if not self.github_sync or not self.github_sync.is_configured():
            return
        notes_file = self.github_sync.get_notes_file()
        if notes_file:
            data = {'notes': [n.to_dict() for n in self.notes]}
            with open(notes_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
    def save_calendar_to_repo(self):
        if not self.github_sync or not self.github_sync.is_configured():
            return
        cal_file = self.github_sync.get_calendar_file()
        if cal_file:
            with open(cal_file, 'w', encoding='utf-8') as f:
                json.dump(self.calendar_data, f, ensure_ascii=False, indent=2)
                
    def load_notes_from_repo(self):
        if not self.github_sync or not self.github_sync.is_configured():
            return
        notes_file = self.github_sync.get_notes_file()
        if notes_file and notes_file.exists():
            try:
                with open(notes_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                repo_notes = data.get('notes', [])
                if repo_notes:
                    while self.tabs.count() > 0:
                        self.tabs.removeTab(0)
                    self.notes.clear()
                    s = self.get_size()
                    for nd in repo_notes:
                        note = NoteTab(nd.get('id', str(uuid.uuid4())[:8]),
                                      nd.get('name', 'Note'),
                                      nd.get('color', '#fff9c4'),
                                      nd.get('content', ''),
                                      s['font'])
                        note.text_edit.textChanged.connect(self.auto_save)
                        self.notes.append(note)
                        self.tabs.addTab(note, note.name)
            except Exception as e:
                print(f"Error loading from repo: {e}")
                
    def load_calendar_from_repo(self):
        if not self.github_sync or not self.github_sync.is_configured():
            return
        cal_file = self.github_sync.get_calendar_file()
        if cal_file and cal_file.exists():
            try:
                with open(cal_file, 'r', encoding='utf-8') as f:
                    self.calendar_data.update(json.load(f))
            except:
                pass
    
    def save_config(self):
        config = {
            'app_name': self.app_name,
            'size_preset': self.size_preset,
            'sync_enabled': self.sync_enabled,
            'sync_repo_path': self.sync_repo_path,
            'pinned_to_desktop': self.pinned_to_desktop
        }
        try:
            with open(self.get_data_dir() / 'config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
        except:
            pass
            
    def load_config(self):
        try:
            config_path = self.get_data_dir() / 'config.json'
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                    self.app_name = cfg.get('app_name', "Albert's Sticky Notes")
                    self.size_preset = cfg.get('size_preset', 'Medium')
                    self.sync_enabled = cfg.get('sync_enabled', False)
                    self.sync_repo_path = cfg.get('sync_repo_path', '')
                    self.pinned_to_desktop = cfg.get('pinned_to_desktop', True)
                    
                    if self.sync_enabled and self.sync_repo_path:
                        self.github_sync = GitHubSync(self.sync_repo_path)
                        self.update_sync_indicator("☁", "#888", "Sync enabled")
        except:
            pass

    # === Window Management ===
    
    def pin_to_desktop(self):
        if sys.platform != 'win32':
            return
        hwnd = int(self.winId())
        user32.SetWindowPos(hwnd, HWND_BOTTOM, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
        
    def apply_desktop_mode(self):
        if self.pinned_to_desktop:
            self.pin_btn.setText("📌")
            self.pin_btn.setToolTip("Pinned to desktop")
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnBottomHint)
            self.show()
            QTimer.singleShot(50, self.pin_to_desktop)
        else:
            self.pin_btn.setText("📍")
            self.pin_btn.setToolTip("Floating")
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
            self.show()
            self.raise_()
            
    def toggle_desktop_mode(self):
        self.pinned_to_desktop = not self.pinned_to_desktop
        self.apply_desktop_mode()
        self.save_config()
        
    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            if not self.pinned_to_desktop:
                self.raise_()
            else:
                QTimer.singleShot(50, self.pin_to_desktop)
                
    def tray_clicked(self, reason):
        if reason in (QSystemTrayIcon.DoubleClick, QSystemTrayIcon.Trigger):
            self.toggle_visibility()
            
    # === Resize & Drag ===
    
    def get_resize_edge(self, pos):
        rect = self.rect()
        x, y = pos.x(), pos.y()
        m = self.resize_margin
        edges = []
        if x < m: edges.append('left')
        if x > rect.width() - m: edges.append('right')
        if y < m: edges.append('top')
        if y > rect.height() - m: edges.append('bottom')
        return '-'.join(edges) if edges else None
        
    def update_cursor(self, edge):
        cursors = {
            'left': Qt.SizeHorCursor, 'right': Qt.SizeHorCursor,
            'top': Qt.SizeVerCursor, 'bottom': Qt.SizeVerCursor,
            'top-left': Qt.SizeFDiagCursor, 'bottom-right': Qt.SizeFDiagCursor,
            'top-right': Qt.SizeBDiagCursor, 'bottom-left': Qt.SizeBDiagCursor,
            'left-top': Qt.SizeFDiagCursor, 'right-bottom': Qt.SizeFDiagCursor,
            'right-top': Qt.SizeBDiagCursor, 'left-bottom': Qt.SizeBDiagCursor,
        }
        self.setCursor(cursors.get(edge, Qt.ArrowCursor))
            
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            edge = self.get_resize_edge(event.pos())
            if edge:
                self.resize_edge = edge
                self.resize_start_pos = event.globalPos()
                self.resize_start_geo = self.geometry()
            elif self.title_bar.geometry().contains(event.pos()):
                self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
                
    def mouseMoveEvent(self, event):
        if self.resize_edge and event.buttons() == Qt.LeftButton:
            self.do_resize(event.globalPos())
        elif self.drag_position and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
        else:
            self.update_cursor(self.get_resize_edge(event.pos()))
            
    def mouseReleaseEvent(self, event):
        self.drag_position = None
        self.resize_edge = None
        self.auto_save()
        if self.pinned_to_desktop:
            QTimer.singleShot(50, self.pin_to_desktop)
            
    def do_resize(self, gpos):
        geo = self.resize_start_geo
        dx = gpos.x() - self.resize_start_pos.x()
        dy = gpos.y() - self.resize_start_pos.y()
        x, y, w, h = geo.x(), geo.y(), geo.width(), geo.height()
        min_w, min_h = self.minimumWidth(), self.minimumHeight()
        
        if 'right' in self.resize_edge: w = max(min_w, geo.width() + dx)
        if 'bottom' in self.resize_edge: h = max(min_h, geo.height() + dy)
        if 'left' in self.resize_edge:
            nw = max(min_w, geo.width() - dx)
            if nw != geo.width(): x, w = geo.x() + geo.width() - nw, nw
        if 'top' in self.resize_edge:
            nh = max(min_h, geo.height() - dy)
            if nh != geo.height(): y, h = geo.y() + geo.height() - nh, nh
        self.setGeometry(x, y, w, h)
            
    # === Note Management ===
    
    def add_new_note(self):
        note_id = str(uuid.uuid4())[:8]
        name = f"Note {self.tabs.count() + 1}"
        
        dialog = NoteSettingsDialog(self, name)
        if dialog.exec_() != QDialog.Accepted:
            return
        name, color = dialog.get_values()
        if not name.strip():
            name = f"Note {self.tabs.count() + 1}"
            
        s = self.get_size()
        note = NoteTab(note_id, name, color, "", s['font'])
        note.text_edit.textChanged.connect(self.auto_save)
        self.notes.append(note)
        self.tabs.addTab(note, name)
        self.tabs.setCurrentIndex(self.tabs.count() - 1)
        self.auto_save()
        
    def close_tab(self, index):
        if self.tabs.count() <= 1:
            QMessageBox.information(self, "Info", "Need at least one note!")
            return
        if QMessageBox.question(self, "Delete", "Delete this note?") == QMessageBox.Yes:
            self.notes.remove(self.tabs.widget(index))
            self.tabs.removeTab(index)
            self.auto_save()
            
    def edit_current_note(self):
        if not self.tabs.count():
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
            
    # === Save/Load ===
    
    def load_notes(self):
        self.load_config()
        self.load_calendar()
        
        # Apply loaded settings
        self.title_label.setText(self.app_name)
        self.setWindowTitle(self.app_name)
        self.apply_styles()
        
        try:
            data_file = self.get_data_dir() / 'notes.json'
            if data_file.exists():
                with open(data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    if 'geometry' in data:
                        g = data['geometry']
                        self.setGeometry(g['x'], g['y'], g['w'], g['h'])
                    
                    s = self.get_size()
                    for nd in data.get('notes', []):
                        note = NoteTab(nd.get('id', str(uuid.uuid4())[:8]),
                                      nd.get('name', 'Note'),
                                      nd.get('color', '#fff9c4'),
                                      nd.get('content', ''),
                                      s['font'])
                        note.text_edit.textChanged.connect(self.auto_save)
                        self.notes.append(note)
                        self.tabs.addTab(note, note.name)
                        
                    active = data.get('active_tab', 0)
                    if 0 <= active < self.tabs.count():
                        self.tabs.setCurrentIndex(active)
        except Exception as e:
            print(f'Load error: {e}')
            
        if not self.tabs.count():
            s = self.get_size()
            note = NoteTab(str(uuid.uuid4())[:8], "Welcome", "#fff9c4",
                "Welcome!\n\n"
                "• Double-click title to rename app\n"
                "• + Add notes | ⚙ Settings\n"
                "• 📅 Calendar | ⬇ Pull | ⬆ Push\n"
                "• ☰ App settings (size, sync)\n"
                "• B/I/U for text formatting\n"
                "• Drag edges to resize", s['font'])
            note.text_edit.textChanged.connect(self.auto_save)
            self.notes.append(note)
            self.tabs.addTab(note, note.name)
            
    def auto_save(self):
        try:
            data = {
                'geometry': {'x': self.x(), 'y': self.y(), 'w': self.width(), 'h': self.height()},
                'active_tab': self.tabs.currentIndex(),
                'notes': [n.to_dict() for n in self.notes]
            }
            with open(self.get_data_dir() / 'notes.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            if self.sync_enabled and self.github_sync:
                self.save_notes_to_repo()
        except:
            pass
            
    # === Startup ===
    
    def add_to_startup(self):
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\CurrentVersion\Run', 0, winreg.KEY_SET_VALUE)
            exe = sys.executable if getattr(sys, 'frozen', False) else f'"{sys.executable}" "{os.path.abspath(__file__)}"'
            winreg.SetValueEx(key, 'StickyNotesApp', 0, winreg.REG_SZ, exe)
            winreg.CloseKey(key)
            QMessageBox.information(self, 'Done', 'Added to startup!')
        except Exception as e:
            QMessageBox.warning(self, 'Error', str(e))
            
    def remove_from_startup(self):
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\CurrentVersion\Run', 0, winreg.KEY_SET_VALUE)
            try:
                winreg.DeleteValue(key, 'StickyNotesApp')
                QMessageBox.information(self, 'Done', 'Removed!')
            except FileNotFoundError:
                QMessageBox.information(self, 'Info', 'Not in startup.')
            winreg.CloseKey(key)
        except Exception as e:
            QMessageBox.warning(self, 'Error', str(e))
    
    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(self.app_name, 'Running in tray.', QSystemTrayIcon.Information, 2000)
        
    def quit_app(self):
        self.auto_save()
        self.save_calendar()
        if self.sync_enabled and self.github_sync:
            self.save_notes_to_repo()
            self.save_calendar_to_repo()
            self.github_sync.push_all("Auto-save")
        QApplication.quit()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = StickyNotesApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
