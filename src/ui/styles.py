"""
Centralized QSS stylesheet for ScrcpyUltimateLink.

All widget styling is defined here so the entire application has a
consistent look. Widgets reference styles via ``setObjectName()``
and the global stylesheet applies automatically.

Color Palette — "Midnight Emerald"
"""

from __future__ import annotations

# ── Color Palette ─────────────────────────────────────────────────────────────

COLORS = {
    "bg_primary": "#0d0d1a",        # Deepest background
    "bg_secondary": "#121228",      # Main window / tab pane
    "bg_panel": "#181838",          # Cards, group boxes
    "bg_input": "#1a1a3a",          # Text inputs, spinboxes
    "bg_button": "#1e1e4a",         # Button default
    "bg_button_hover": "#00d9a5",   # Button hover
    "border": "#1f1f4e",            # Subtle borders
    "border_accent": "#00d9a5",     # Accent borders
    "accent": "#00d9a5",            # Primary accent (emerald green)
    "accent_dim": "#00a87e",        # Dimmer accent
    "text": "#e0e0e0",              # Primary text
    "text_dim": "#888888",          # Secondary text
    "text_dark": "#0d0d1a",         # Text on accent backgrounds
    "success": "#00d9a5",           # Success status
    "warning": "#f0a030",           # Warning status
    "error": "#ff5555",             # Error status
    "tab_inactive": "#1a1a3a",      # Inactive tab
    "tab_active": "#1e1e4a",        # Active tab
    "progress_bg": "#1a1a2e",       # Progress bar track
    "progress_fill": "#00d9a5",     # Progress bar chunk
    "scrollbar_bg": "#121228",      # Scrollbar track
    "scrollbar_handle": "#2a2a5a",  # Scrollbar handle
}

# ── Global Stylesheet ─────────────────────────────────────────────────────────

STYLESHEET = f"""
/* ── Base ──────────────────────────────────────────────────────────── */

QMainWindow {{
    background-color: {COLORS["bg_secondary"]};
}}

QWidget {{
    font-family: "Segoe UI", "Inter", "Roboto", "Noto Sans", sans-serif;
    font-size: 13px;
    color: {COLORS["text"]};
}}

/* ── Tab Widget ────────────────────────────────────────────────────── */

QTabWidget::pane {{
    background-color: {COLORS["bg_secondary"]};
    border: none;
    border-top: 2px solid {COLORS["border"]};
}}

QTabBar::tab {{
    background: {COLORS["tab_inactive"]};
    color: {COLORS["text_dim"]};
    padding: 10px 22px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 2px;
    font-size: 13px;
}}

QTabBar::tab:selected {{
    background: {COLORS["tab_active"]};
    color: {COLORS["accent"]};
    font-weight: bold;
}}

QTabBar::tab:hover:!selected {{
    background: {COLORS["bg_panel"]};
    color: {COLORS["text"]};
}}

/* ── Labels ────────────────────────────────────────────────────────── */

QLabel {{
    color: {COLORS["text"]};
    background: transparent;
}}

QLabel#title {{
    font-size: 24px;
    font-weight: bold;
    color: {COLORS["accent"]};
}}

QLabel#status {{
    font-size: 15px;
    font-weight: bold;
    color: {COLORS["accent"]};
    padding: 4px 0;
}}

QLabel#status-error {{
    font-size: 15px;
    font-weight: bold;
    color: {COLORS["error"]};
}}

QLabel#status-warning {{
    font-size: 15px;
    font-weight: bold;
    color: {COLORS["warning"]};
}}

QLabel#subtitle {{
    font-size: 14px;
    color: {COLORS["text_dim"]};
}}

QLabel#section-title {{
    font-size: 18px;
    font-weight: bold;
    color: {COLORS["accent"]};
}}

/* ── Buttons ───────────────────────────────────────────────────────── */

QPushButton {{
    background-color: {COLORS["bg_button"]};
    color: {COLORS["accent"]};
    border: 2px solid {COLORS["border_accent"]};
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: bold;
    min-height: 20px;
}}

QPushButton:hover {{
    background-color: {COLORS["bg_button_hover"]};
    color: {COLORS["text_dark"]};
}}

QPushButton:pressed {{
    background-color: {COLORS["accent_dim"]};
    color: {COLORS["text_dark"]};
}}

QPushButton:disabled {{
    background-color: {COLORS["bg_primary"]};
    color: #555555;
    border-color: #333333;
}}

QPushButton#action-primary {{
    background-color: {COLORS["accent"]};
    color: {COLORS["text_dark"]};
    border: none;
    font-size: 14px;
    padding: 10px 20px;
}}

QPushButton#action-primary:hover {{
    background-color: {COLORS["accent_dim"]};
}}

QPushButton#action-danger {{
    border-color: {COLORS["error"]};
    color: {COLORS["error"]};
}}

QPushButton#action-danger:hover {{
    background-color: {COLORS["error"]};
    color: {COLORS["text"]};
}}

QPushButton#control-btn {{
    padding: 6px 10px;
    font-size: 12px;
    border-radius: 6px;
}}

/* ── Input Widgets ─────────────────────────────────────────────────── */

QLineEdit, QSpinBox, QComboBox {{
    background-color: {COLORS["bg_input"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 6px;
    padding: 6px 10px;
    color: {COLORS["accent"]};
    font-size: 13px;
    min-height: 20px;
}}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border-color: {COLORS["accent"]};
}}

QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS["bg_panel"]};
    color: {COLORS["text"]};
    selection-background-color: {COLORS["accent"]};
    selection-color: {COLORS["text_dark"]};
    border: 1px solid {COLORS["border"]};
}}

/* ── Text Edit (Log Panel) ─────────────────────────────────────────── */

QTextEdit {{
    background-color: {COLORS["bg_input"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 8px;
    padding: 8px;
    color: {COLORS["text"]};
    font-family: "JetBrains Mono", "Cascadia Code", "Fira Code", "Consolas", monospace;
    font-size: 11px;
    selection-background-color: {COLORS["accent"]};
    selection-color: {COLORS["text_dark"]};
}}

/* ── Check Box ─────────────────────────────────────────────────────── */

QCheckBox {{
    color: {COLORS["text"]};
    font-size: 13px;
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {COLORS["accent"]};
    border-radius: 4px;
    background: {COLORS["bg_input"]};
}}

QCheckBox::indicator:checked {{
    background: {COLORS["accent"]};
}}

QCheckBox::indicator:hover {{
    border-color: {COLORS["accent_dim"]};
}}

/* ── Group Box ─────────────────────────────────────────────────────── */

QGroupBox {{
    color: {COLORS["accent"]};
    font-weight: bold;
    font-size: 13px;
    border: 2px solid {COLORS["border"]};
    border-radius: 10px;
    margin-top: 14px;
    padding: 14px 10px 10px 10px;
    background-color: {COLORS["bg_panel"]};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}}

/* ── Progress Bar ──────────────────────────────────────────────────── */

QProgressBar {{
    border: 1px solid {COLORS["border"]};
    border-radius: 6px;
    text-align: center;
    color: white;
    font-weight: bold;
    height: 22px;
    background-color: {COLORS["progress_bg"]};
    font-size: 11px;
}}

QProgressBar::chunk {{
    background-color: {COLORS["progress_fill"]};
    border-radius: 5px;
}}

/* ── List Widget ───────────────────────────────────────────────────── */

QListWidget {{
    background-color: {COLORS["bg_input"]};
    color: {COLORS["text"]};
    border: 2px solid {COLORS["border"]};
    border-radius: 8px;
    font-size: 13px;
    outline: none;
}}

QListWidget::item {{
    padding: 8px 10px;
    border-bottom: 1px solid {COLORS["border"]};
}}

QListWidget::item:selected {{
    background-color: {COLORS["bg_button"]};
    color: {COLORS["accent"]};
}}

QListWidget::item:hover:!selected {{
    background-color: {COLORS["bg_panel"]};
}}

/* ── Scroll Area ───────────────────────────────────────────────────── */

QScrollArea {{
    border: none;
    background: transparent;
}}

/* ── Scrollbar ─────────────────────────────────────────────────────── */

QScrollBar:vertical {{
    background: {COLORS["scrollbar_bg"]};
    width: 10px;
    border-radius: 5px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: {COLORS["scrollbar_handle"]};
    border-radius: 5px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: {COLORS["accent_dim"]};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background: {COLORS["scrollbar_bg"]};
    height: 10px;
    border-radius: 5px;
}}

QScrollBar::handle:horizontal {{
    background: {COLORS["scrollbar_handle"]};
    border-radius: 5px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {COLORS["accent_dim"]};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ── Tooltip ───────────────────────────────────────────────────────── */

QToolTip {{
    background-color: {COLORS["bg_panel"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["accent"]};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}}

/* ── Status Bar ────────────────────────────────────────────────────── */

QStatusBar {{
    background-color: {COLORS["bg_primary"]};
    color: {COLORS["text_dim"]};
    font-size: 11px;
    border-top: 1px solid {COLORS["border"]};
}}

QStatusBar::item {{
    border: none;
}}

/* ── Menu Bar ──────────────────────────────────────────────────────── */

QMenuBar {{
    background-color: {COLORS["bg_primary"]};
    color: {COLORS["text"]};
    border-bottom: 1px solid {COLORS["border"]};
    padding: 2px 0;
}}

QMenuBar::item {{
    padding: 4px 12px;
    border-radius: 4px;
}}

QMenuBar::item:selected {{
    background-color: {COLORS["bg_panel"]};
}}

QMenu {{
    background-color: {COLORS["bg_panel"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 6px;
    padding: 4px;
}}

QMenu::item {{
    padding: 6px 24px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {COLORS["accent"]};
    color: {COLORS["text_dark"]};
}}

QMenu::separator {{
    height: 1px;
    background: {COLORS["border"]};
    margin: 4px 8px;
}}

/* ── Drop Zone (File Transfer) ─────────────────────────────────────── */

QFrame#drop-zone {{
    border: 2px dashed {COLORS["accent"]};
    border-radius: 12px;
    background-color: {COLORS["bg_panel"]};
}}

QFrame#drop-zone-active {{
    border: 2px solid {COLORS["accent"]};
    background-color: {COLORS["bg_button"]};
    border-radius: 12px;
}}
"""
