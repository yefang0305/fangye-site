"""
theme.py - UI 主题系统（精简版，供桌面工作台使用）
"""

from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtCore import QSize


class Theme:
    BG_BASE = "#0f0f13"
    BG_SURFACE = "#16161e"
    BG_ELEVATED = "#1c1c28"
    BG_HOVER = "#1e1e2c"
    BG_INPUT = "#141418"
    TEXT_PRIMARY = "#e2e2ed"
    TEXT_SECONDARY = "#888899"
    TEXT_TERTIARY = "#444455"
    TEXT_ON_ACCENT = "#ffffff"
    TEXT_HINT = "#33334a"
    BORDER_LIGHT = "#1e1e26"
    BORDER_MEDIUM = "#252530"
    BORDER_FOCUS = "#7c6af5"
    ACCENT_PRIMARY = "#7c6af5"
    ACCENT_HOVER = "#9080f8"
    ACCENT_PRESSED = "#6858e0"
    ACCENT_LIGHT = "#1c1a38"
    ACCENT_TEXT = "#a89ff8"
    ACTION_PRIMARY = "#7c6af5"
    ACTION_PRIMARY_TEXT = "#ffffff"
    ACTION_HOVER = "#9080f8"
    SUCCESS_BG = "#0d2418"
    SUCCESS_TEXT = "#3ab56a"
    WARNING_BG = "#2a2208"
    WARNING_TEXT = "#e8a838"
    ERROR_BG = "#2a0e0e"
    ERROR_TEXT = "#e85555"
    INFO_BG = "#0d1a38"
    INFO_TEXT = "#7c9af5"
    SIDEBAR_BG = "#09090d"
    SIDEBAR_ITEM_HOVER = "#16161e"
    SIDEBAR_ITEM_ACTIVE = "#1c1a38"
    SIDEBAR_ACTIVE_TEXT = "#e2e2ed"
    TITLEBAR_BG = "#09090d"


class Typography:
    FONT_FAMILY = "Inter, -apple-system, Segoe UI, PingFang SC, Microsoft YaHei, sans-serif"
    SIZE_XS = 11
    SIZE_SM = 12
    SIZE_BASE = 13
    SIZE_MD = 14
    SIZE_LG = 16
    SIZE_XL = 20
    WEIGHT_REGULAR = QFont.Normal
    WEIGHT_MEDIUM = QFont.Medium
    WEIGHT_BOLD = QFont.Bold


class Spacing:
    XS = 4
    SM = 8
    MD = 12
    LG = 16
    XL = 24
    XXL = 32
    CARD_PADDING = 18
    SECTION_GAP = 14
    BORDER_RADIUS_SM = 6
    BORDER_RADIUS_MD = 8
    BORDER_RADIUS_LG = 10


def build_qss() -> str:
    T = Theme
    S = Spacing
    Ty = Typography
    return f"""
QWidget {{
    background-color: {T.BG_BASE};
    color: {T.TEXT_PRIMARY};
    font-family: {Ty.FONT_FAMILY};
    font-size: {Ty.SIZE_BASE}px;
}}
QMainWindow, QDialog {{ background-color: {T.BG_BASE}; }}
QPushButton {{
    background-color: {T.BG_ELEVATED};
    color: {T.TEXT_PRIMARY};
    border: 1px solid {T.BORDER_LIGHT};
    border-radius: {S.BORDER_RADIUS_MD}px;
    padding: 7px 14px;
    font-size: {Ty.SIZE_BASE}px;
    min-height: 20px;
}}
QPushButton:hover {{ background-color: {T.BG_HOVER}; border-color: {T.BORDER_MEDIUM}; }}
QPushButton:pressed {{ background-color: {T.BG_SURFACE}; }}
QPushButton:disabled {{ background-color: {T.BG_SURFACE}; color: {T.TEXT_TERTIARY}; }}
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {{
    background-color: {T.BG_INPUT};
    color: {T.TEXT_PRIMARY};
    border: 1px solid {T.BORDER_LIGHT};
    border-radius: {S.BORDER_RADIUS_MD}px;
    padding: 6px 10px;
    selection-background-color: {T.ACTION_PRIMARY};
}}
QTextEdit, QPlainTextEdit {{ padding: 10px 12px; }}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {T.BORDER_FOCUS};
    background-color: {T.BG_ELEVATED};
}}
QComboBox {{
    background-color: {T.BG_INPUT};
    color: {T.TEXT_PRIMARY};
    border: 1px solid {T.BORDER_MEDIUM};
    border-radius: {S.BORDER_RADIUS_MD}px;
    padding: 6px 10px;
    min-height: 20px;
}}
QComboBox:hover {{ border-color: {T.BORDER_MEDIUM}; }}
QComboBox:focus {{ border-color: {T.BORDER_FOCUS}; background-color: {T.BG_ELEVATED}; }}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{
    background-color: {T.BG_ELEVATED};
    color: {T.TEXT_PRIMARY};
    border: 1px solid {T.BORDER_MEDIUM};
    selection-background-color: {T.ACCENT_LIGHT};
    padding: 4px;
}}
QListWidget, QListView {{
    background-color: {T.BG_ELEVATED};
    color: {T.TEXT_PRIMARY};
    border: 1px solid {T.BORDER_MEDIUM};
    border-radius: {S.BORDER_RADIUS_MD}px;
    outline: none;
    padding: 4px;
}}
QListWidget::item:hover, QListView::item:hover {{ background-color: {T.BG_HOVER}; }}
QListWidget::item:selected, QListView::item:selected {{
    background-color: {T.ACCENT_LIGHT};
    color: {T.TEXT_PRIMARY};
}}
QCheckBox {{ color: {T.TEXT_PRIMARY}; spacing: 8px; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {T.BORDER_MEDIUM}; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {T.TEXT_TERTIARY}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; background: none; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 0; }}
QScrollBar::handle:horizontal {{ background: {T.BORDER_MEDIUM}; border-radius: 5px; min-width: 30px; }}
QScrollBar::handle:horizontal:hover {{ background: {T.TEXT_TERTIARY}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; background: none; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}
QProgressBar {{
    background-color: {T.BG_INPUT};
    border: none;
    border-radius: 4px;
    height: 6px;
    text-align: center;
}}
QProgressBar::chunk {{ background-color: {T.ACCENT_PRIMARY}; border-radius: 4px; }}
QSplitter::handle {{ background: {T.BORDER_LIGHT}; }}
QWidget#titleBar {{ background-color: {T.TITLEBAR_BG}; border: none; }}
QFrame#panelWidget {{
    background-color: {T.BG_SURFACE};
    border: none;
    border-radius: {S.BORDER_RADIUS_MD}px;
}}
"""
