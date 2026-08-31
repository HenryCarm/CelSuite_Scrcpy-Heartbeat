"""
Centralized QSS stylesheet for ScrcpyUltimateLink.

All widget styling is defined here so the entire application has a
consistent look. Widgets reference styles via ``setObjectName()``
and the global stylesheet applies automatically.

Color Palette — "Royal Nebula"
"""

from __future__ import annotations

# ── Color Palette ─────────────────────────────────────────────────────────────

COLORS = {
    # Backgrounds — deep obsidian layers
    "bg_deep": "#08060D",
    "bg_primary": "#0D0A14",      # Much darker main background
    "bg_secondary": "#130F1D",
    "bg_card": "#241D35",         # Much lighter card background
    "bg_card_hover": "#2F2647",
    "bg_card_glass": "rgba(36, 29, 53, 180)",
    "bg_input": "#1B1629",
    "bg_button": "#2F2647",
    "bg_button_hover": "#3F345D",

    # Accents — Royal Purple / Indigo / Violet
    "accent": "#7C3AED",
    "accent_light": "#A855F7",
    "accent_indigo": "#6366F1",
    "accent_glow": "#8B5CF6",
    "accent_dim": "#6D28D9",

    # Borders
    "border": "#2a2a52",
    "border_accent": "#7C3AED",
    "border_glow": "rgba(124, 58, 237, 80)",

    # Text
    "text": "#F0F0F5",
    "text_dim": "#9CA3AF",
    "text_on_accent": "#FFFFFF",
    "text_dark": "#0a0a14",

    # Status
    "success": "#10B981",
    "warning": "#F59E0B",
    "error": "#EF4444",

    # Components
    "tab_inactive": "#151528",
    "tab_active": "#1a1a35",
    "progress_bg": "#1a1a2e",
    "progress_fill": "#7C3AED",
    "scrollbar_bg": "#0f0f1e",
    "scrollbar_handle": "#2a2a52",
}

# ── Global Stylesheet ─────────────────────────────────────────────────────────

STYLESHEET = f"""
/* ── Base ──────────────────────────────────────────────────────────── */

QMainWindow {{
    background-color: {COLORS["bg_primary"]};
}}

QWidget {{
    font-family: "Inter", "Segoe UI", "Roboto", "Noto Sans", sans-serif;
    font-size: 13px;
    color: {COLORS["text"]};
}}

/* ── Tab Widget ────────────────────────────────────────────────────── */

QTabWidget::pane {{
    background-color: {COLORS["bg_secondary"]};
    border: none;
    border-top: 2px solid {COLORS["border"]};
}}

QTabBar {{
    background: {COLORS["bg_primary"]};
    qproperty-drawBase: 0;
}}

QTabBar::tab {{
    background: {COLORS["tab_inactive"]};
    color: {COLORS["text_dim"]};
    padding: 12px 28px;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    margin-right: 3px;
    font-size: 13px;
    font-weight: 500;
    border-bottom: 3px solid transparent;
}}

QTabBar::tab:selected {{
    background: {COLORS["tab_active"]};
    color: {COLORS["accent_light"]};
    font-weight: bold;
    border-bottom: 3px solid {COLORS["accent"]};
}}

QTabBar::tab:hover:!selected {{
    background: {COLORS["bg_card"]};
    color: {COLORS["text"]};
    border-bottom: 3px solid {COLORS["accent_glow"]};
}}

/* ── Labels ────────────────────────────────────────────────────────── */

QLabel {{
    color: {COLORS["text"]};
    background: transparent;
}}

QLabel#title {{
    font-size: 26px;
    font-weight: bold;
    color: {COLORS["accent_light"]};
    letter-spacing: 0.5px;
}}

QLabel#status {{
    font-size: 15px;
    font-weight: bold;
    color: {COLORS["success"]};
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
    font-size: 16px;
    font-weight: bold;
    color: {COLORS["text"]};
    letter-spacing: 0.3px;
    padding-bottom: 2px;
}}

QLabel#stat-value {{
    font-size: 16px;
    font-weight: bold;
    color: {COLORS["text"]};
}}

QLabel#stat-label {{
    font-size: 11px;
    color: {COLORS["text_dim"]};
    text-transform: uppercase;
}}

QLabel#hero-title {{
    font-size: 32px;
    font-weight: bold;
    color: {COLORS["accent_light"]};
}}

/* ── Buttons ───────────────────────────────────────────────────────── */

QPushButton {{
    background-color: {COLORS["bg_button"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 16px;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: bold;
    min-height: 34px;
}}

QPushButton:hover {{
    background-color: {COLORS["bg_button_hover"]};
    border-color: {COLORS["accent"]};
    color: {COLORS["text"]};
}}

QPushButton:pressed {{
    background-color: {COLORS["accent_dim"]};
    color: {COLORS["text_on_accent"]};
}}

QPushButton:disabled {{
    background-color: {COLORS["bg_deep"]};
    color: #444455;
    border-color: #222244;
}}

QPushButton#action-primary {{
    background-color: {COLORS["accent"]};
    color: {COLORS["text_on_accent"]};
    border: none;
    font-size: 14px;
    padding: 10px 24px;
    border-radius: 20px;
    min-height: 40px;
}}

QPushButton#action-primary:hover {{
    background-color: {COLORS["accent_light"]};
}}

QPushButton#action-primary:pressed {{
    background-color: {COLORS["accent_dim"]};
}}

QPushButton#action-danger {{
    border-color: {COLORS["error"]};
    color: {COLORS["error"]};
}}

QPushButton#action-danger:hover {{
    background-color: {COLORS["error"]};
    color: {COLORS["text_on_accent"]};
    border-color: {COLORS["error"]};
}}

QPushButton#control-btn {{
    padding: 8px 14px;
    font-size: 12px;
    border-radius: 8px;
    background-color: {COLORS["bg_card"]};
    border: 1px solid {COLORS["border"]};
}}

QPushButton#control-btn:hover {{
    background-color: {COLORS["bg_button"]};
    border-color: {COLORS["accent_glow"]};
}}

QPushButton#control-btn:pressed {{
    background-color: {COLORS["accent"]};
    color: {COLORS["text_on_accent"]};
}}

/* ── Input Widgets ─────────────────────────────────────────────────── */

QLineEdit, QSpinBox, QComboBox {{
    background-color: {COLORS["bg_input"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 8px;
    padding: 8px 12px;
    color: {COLORS["text"]};
    font-size: 13px;
    min-height: 22px;
    selection-background-color: {COLORS["accent"]};
    selection-color: {COLORS["text_on_accent"]};
}}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border-color: {COLORS["accent"]};
    border-width: 2px;
}}

QComboBox::drop-down {{
    border: none;
    padding-right: 10px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS["bg_card"]};
    color: {COLORS["text"]};
    selection-background-color: {COLORS["accent"]};
    selection-color: {COLORS["text_on_accent"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 8px;
    outline: none;
}}

/* ── Text Edit (Log Panel) ─────────────────────────────────────────── */

QTextEdit {{
    background-color: {COLORS["bg_input"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 10px;
    padding: 10px;
    color: {COLORS["text"]};
    font-family: "JetBrains Mono", "Cascadia Code", "Fira Code", "Consolas", monospace;
    font-size: 11px;
    selection-background-color: {COLORS["accent"]};
    selection-color: {COLORS["text_on_accent"]};
}}

/* ── Check Box ─────────────────────────────────────────────────────── */

QCheckBox {{
    color: {COLORS["text"]};
    font-size: 13px;
    spacing: 10px;
}}

QCheckBox::indicator {{
    width: 20px;
    height: 20px;
    border: 2px solid {COLORS["accent"]};
    border-radius: 5px;
    background: {COLORS["bg_input"]};
}}

QCheckBox::indicator:checked {{
    background: {COLORS["accent"]};
    border-color: {COLORS["accent_light"]};
}}

QCheckBox::indicator:hover {{
    border-color: {COLORS["accent_light"]};
}}

/* ── Group Box ─────────────────────────────────────────────────────── */

QGroupBox {{
    color: {COLORS["accent_light"]};
    font-weight: bold;
    font-size: 13px;
    border: 1px solid {COLORS["border"]};
    border-radius: 16px;
    margin-top: 16px;
    padding: 24px 16px 16px 16px;
    background-color: {COLORS["bg_card"]};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 8px;
    color: {COLORS["accent_light"]};
}}

/* ── Section Card & Collapsible Card (Custom Containers) ───────────── */

QFrame#section-card, QFrame#collapsible-card, QFrame#hero-card {{
    background-color: {COLORS["bg_card"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 16px;
}}

QFrame#hero-card {{
    background-color: {COLORS["bg_card"]};
    border: 1px solid {COLORS["border_accent"]};
    border-radius: 20px;
    padding: 12px;
}}

QPushButton#hero-button {{
    background-color: {COLORS["accent"]};
    color: {COLORS["text_on_accent"]};
    border: none;
    font-size: 16px;
    font-weight: bold;
    padding: 14px 28px;
    border-radius: 24px;
    min-height: 48px;
}}

QPushButton#hero-button:hover {{
    background-color: {COLORS["accent_light"]};
}}

QPushButton#collapsible-header {{
    border: none;
    background: transparent;
    text-align: left;
    padding: 4px 0px;
}}

QPushButton#collapsible-header:hover {{
    background: transparent;
}}

QLabel#collapsible-arrow {{
    color: {COLORS["accent_light"]};
    font-size: 14px;
    font-weight: bold;
}}

QFrame#section-separator {{
    background-color: {COLORS["border"]};
}}

/* ── Progress Bar ──────────────────────────────────────────────────── */

QProgressBar {{
    border: 1px solid {COLORS["border"]};
    border-radius: 8px;
    text-align: center;
    color: {COLORS["text_on_accent"]};
    font-weight: bold;
    height: 24px;
    background-color: {COLORS["progress_bg"]};
    font-size: 11px;
}}

QProgressBar::chunk {{
    background-color: {COLORS["accent"]};
    border-radius: 7px;
}}

/* ── List Widget ───────────────────────────────────────────────────── */

QListWidget {{
    background-color: {COLORS["bg_input"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 10px;
    font-size: 14px;
    outline: none;
    padding: 8px;
}}

QListWidget#sidebar {{
    background-color: transparent;
    border: none;
}}

QListWidget::item {{
    padding: 14px 16px;
    border-radius: 8px;
    margin: 4px 8px;
    font-weight: 500;
}}

QListWidget::item:selected {{
    background-color: {COLORS["accent"]};
    color: {COLORS["text_on_accent"]};
    border: none;
}}

QListWidget::item:hover:!selected {{
    background-color: {COLORS["bg_card"]};
}}

/* ── Scroll Area ───────────────────────────────────────────────────── */

QScrollArea {{
    border: none;
    background: transparent;
}}

/* ── Scrollbar ─────────────────────────────────────────────────────── */

QScrollBar:vertical {{
    background: {COLORS["scrollbar_bg"]};
    width: 8px;
    border-radius: 4px;
    margin: 2px;
}}

QScrollBar::handle:vertical {{
    background: {COLORS["scrollbar_handle"]};
    border-radius: 4px;
    min-height: 40px;
}}

QScrollBar::handle:vertical:hover {{
    background: {COLORS["accent_glow"]};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background: {COLORS["scrollbar_bg"]};
    height: 8px;
    border-radius: 4px;
    margin: 2px;
}}

QScrollBar::handle:horizontal {{
    background: {COLORS["scrollbar_handle"]};
    border-radius: 4px;
    min-width: 40px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {COLORS["accent_glow"]};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ── Tooltip ───────────────────────────────────────────────────────── */

QToolTip {{
    background-color: {COLORS["bg_card"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["accent"]};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}}

/* ── Status Bar ────────────────────────────────────────────────────── */

QStatusBar {{
    background-color: {COLORS["bg_deep"]};
    color: {COLORS["text_dim"]};
    font-size: 11px;
    border-top: 1px solid {COLORS["border"]};
    min-height: 28px;
}}

QStatusBar::item {{
    border: none;
}}

/* ── Menu Bar ──────────────────────────────────────────────────────── */

QMenuBar {{
    background-color: {COLORS["bg_deep"]};
    color: {COLORS["text"]};
    border-bottom: 1px solid {COLORS["border"]};
    padding: 2px 0;
}}

QMenuBar::item {{
    padding: 6px 14px;
    border-radius: 6px;
}}

QMenuBar::item:selected {{
    background-color: {COLORS["bg_card"]};
    color: {COLORS["accent_light"]};
}}

QMenu {{
    background-color: {COLORS["bg_card"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 8px;
    padding: 6px;
}}

QMenu::item {{
    padding: 8px 28px;
    border-radius: 6px;
}}

QMenu::item:selected {{
    background-color: {COLORS["accent"]};
    color: {COLORS["text_on_accent"]};
}}

QMenu::separator {{
    height: 1px;
    background: {COLORS["border"]};
    margin: 4px 10px;
}}

/* ── Drop Zone (File Transfer) ─────────────────────────────────────── */

QFrame#drop-zone {{
    border: 2px dashed {COLORS["accent_glow"]};
    border-radius: 14px;
    background-color: {COLORS["bg_card"]};
}}

QFrame#drop-zone-active {{
    border: 2px solid {COLORS["accent"]};
    background-color: {COLORS["bg_button"]};
    border-radius: 14px;
}}

/* ── Stat Card ─────────────────────────────────────────────────────── */

QFrame#stat-card {{
    background-color: {COLORS["bg_card"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 12px;
    padding: 12px;
}}

QFrame#stat-card-glow {{
    background-color: {COLORS["bg_card"]};
    border: 1px solid {COLORS["accent"]};
    border-radius: 12px;
    padding: 12px;
}}
"""
