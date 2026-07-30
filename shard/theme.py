"""Theme palettes and stylesheet generation for Shard."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush, QColor, QIcon, QLinearGradient, QPainter, QPixmap, QPolygonF,
)
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget


@dataclass(frozen=True)
class Palette:
    name: str
    blurb: str
    bg: str
    panel: str
    panel_alt: str
    border: str
    border_light: str
    text: str
    muted: str
    accent: str
    accent2: str
    accent_hover: str
    accent_dim: str
    ok: str
    warn: str
    err: str
    info: str
    log_bg: str
    head_a: str
    head_b: str
    head_c: str


THEMES: dict[str, Palette] = {
    "Neon Crystal": Palette(
        name="Neon Crystal",
        blurb="Magenta and cyan shards on deep violet-black",
        bg="#08060f", panel="#100d1c", panel_alt="#181334", border="#2a2150",
        border_light="#3d3070", text="#ece9ff", muted="#8b82b8",
        accent="#ff2d95", accent2="#22d3ee", accent_hover="#ff5bab", accent_dim="#7a1449",
        ok="#3ef2a0", warn="#ffb020", err="#ff4d6d", info="#7c8cff",
        log_bg="#05040a", head_a="#1d0b33", head_b="#2d1155", head_c="#0b0818",
    ),
    "Cyber Yellow": Palette(
        name="Cyber Yellow",
        blurb="2077 arcade - acid yellow on gunmetal",
        bg="#0a0e0f", panel="#101719", panel_alt="#172125", border="#203036",
        border_light="#2d4049", text="#e8fbff", muted="#7a969e",
        accent="#fcee0a", accent2="#00f0ff", accent_hover="#ffff5c", accent_dim="#7a7305",
        ok="#00ff9f", warn="#ff9f0a", err="#ff3864", info="#00f0ff",
        log_bg="#05090a", head_a="#12251f", head_b="#1b3a33", head_c="#0a1215",
    ),
    "Synthwave": Palette(
        name="Synthwave",
        blurb="Sunset grid - hot pink over deep purple",
        bg="#150a29", panel="#1e0f3a", panel_alt="#2a1550", border="#3d1f6b",
        border_light="#55299a", text="#ffe9ff", muted="#a98fd0",
        accent="#ff2e97", accent2="#ff9f1c", accent_hover="#ff5cb0", accent_dim="#7d1449",
        ok="#3ef2a0", warn="#ffcf5c", err="#ff4d6d", info="#8b5cf6",
        log_bg="#0d0620", head_a="#2b1055", head_b="#4a1d7a", head_c="#180a2e",
    ),
    "Matrix": Palette(
        name="Matrix",
        blurb="Phosphor green on black",
        bg="#030703", panel="#071007", panel_alt="#0c1c0c", border="#123112",
        border_light="#1d4a1d", text="#c9ffc9", muted="#5f9f5f",
        accent="#39ff14", accent2="#00b140", accent_hover="#6bff52", accent_dim="#1a7a0a",
        ok="#39ff14", warn="#d4ff00", err="#ff4136", info="#00ffa3",
        log_bg="#020502", head_a="#062006", head_b="#0b3d0b", head_c="#040c04",
    ),
    "Tokyo Night": Palette(
        name="Tokyo Night",
        blurb="Soft neon - the calm one",
        bg="#16161e", panel="#1a1b26", panel_alt="#24283b", border="#2f334d",
        border_light="#414868", text="#c0caf5", muted="#7f87a8",
        accent="#bb9af7", accent2="#7dcfff", accent_hover="#cdb4fa", accent_dim="#5a4a7a",
        ok="#9ece6a", warn="#e0af68", err="#f7768e", info="#7aa2f7",
        log_bg="#101018", head_a="#1f2335", head_b="#2c3050", head_c="#16161e",
    ),
    "Deep Freeze": Palette(
        name="Deep Freeze",
        blurb="Ice blue and electric cyan",
        bg="#060b12", panel="#0c141f", panel_alt="#121d2c", border="#1c2c42",
        border_light="#2a4162", text="#dff1ff", muted="#7d9ab8",
        accent="#00d9ff", accent2="#4d7cff", accent_hover="#5ce6ff", accent_dim="#046b80",
        ok="#2ee6a8", warn="#ffc247", err="#ff5d7a", info="#4d7cff",
        log_bg="#04080e", head_a="#0a2033", head_b="#0f3350", head_c="#06101a",
    ),
    "Blood Moon": Palette(
        name="Blood Moon",
        blurb="Crimson on slate - the original",
        bg="#0e1015", panel="#161a22", panel_alt="#1c212b", border="#272d3a",
        border_light="#333b4c", text="#e7eaf0", muted="#8d97ab",
        accent="#ff3d57", accent2="#ff7a52", accent_hover="#ff5a70", accent_dim="#7d1e2b",
        ok="#3ecf8e", warn="#ffb020", err="#ff5d5d", info="#4d8dff",
        log_bg="#0a0c10", head_a="#1a1020", head_b="#16121c", head_c="#101318",
    ),
}

THEME_ORDER = list(THEMES)
DEFAULT_THEME = "Neon Crystal"

DENSITY = {
    "Compact":     {"pad_y": 4, "pad_x": 9,  "gap": 6,  "row": 5,  "tab": 7},
    "Comfortable": {"pad_y": 7, "pad_x": 11, "gap": 9,  "row": 7,  "tab": 10},
    "Spacious":    {"pad_y": 10, "pad_x": 15, "gap": 13, "row": 10, "tab": 13},
}

FONT_CHOICES = [
    "Segoe UI", "Cascadia Mono", "Cascadia Code", "Consolas", "JetBrains Mono",
    "Fira Code", "Inter", "Roboto Mono", "Source Code Pro",
]


def status_colors(p: Palette) -> dict[str, str]:
    return {
        "Queued": p.muted, "Starting": p.info, "Downloading": p.accent,
        "Processing": p.warn, "Done": p.ok, "Error": p.err,
        "Cancelled": p.muted, "Paused": p.warn,
    }


def make_icon(p: Palette, size: int = 128) -> QIcon:
    """Draw the app mark in the current palette - window and tray icon."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0.0, QColor(p.accent))
    grad.setColorAt(1.0, QColor(p.accent2))
    painter.setBrush(QBrush(grad))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(QRectF(0, 0, size, size), size * 0.22, size * 0.22)

    painter.setBrush(QColor(p.bg))
    w, h = size * 0.30, size * 0.34
    cx, cy = size * 0.54, size * 0.5
    painter.drawPolygon(QPolygonF([
        QPointF(cx - w / 2, cy - h / 2),
        QPointF(cx - w / 2, cy + h / 2),
        QPointF(cx + w / 2, cy),
    ]))
    painter.end()
    return QIcon(pm)


def apply_glow(widget: QWidget, color: str, radius: int = 18) -> None:
    """Neon bloom behind a widget - QSS has no box-shadow, so use an effect."""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(radius)
    effect.setColor(QColor(color))
    effect.setOffset(0, 0)
    widget.setGraphicsEffect(effect)


def build_stylesheet(
    p: Palette,
    *,
    font: str = "Segoe UI",
    font_size: int = 13,
    density: str = "Comfortable",
    radius: int = 8,
    uppercase_tabs: bool = True,
) -> str:
    d = DENSITY.get(density, DENSITY["Comfortable"])
    r = radius
    r_sm = max(3, radius - 3)
    tab_case = "uppercase" if uppercase_tabs else "none"

    return f"""
QWidget {{
    background-color: {p.bg};
    color: {p.text};
    font-family: "{font}", "Segoe UI", sans-serif;
    font-size: {font_size}px;
}}

QToolTip {{
    background-color: {p.panel_alt};
    color: {p.text};
    border: 1px solid {p.accent};
    padding: 6px 9px;
    border-radius: {r_sm}px;
}}

/* ---------------- Title bar ---------------- */
#TitleBar {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {p.head_a}, stop:0.5 {p.head_b}, stop:1 {p.head_c});
    border-bottom: 1px solid {p.border};
}}
#BrandName {{
    font-size: {font_size + 1}px;
    font-weight: 800;
    color: {p.text};
    letter-spacing: 3px;
}}
#BarSep {{
    background-color: {p.border_light};
    border: none;
}}
#BarChip {{
    color: {p.muted};
    font-size: {font_size - 3}px;
    letter-spacing: 0.6px;
    padding: 0 4px;
}}
QToolButton#BarButton {{
    background: transparent;
    border: none;
    border-radius: {r_sm}px;
    margin: 0 1px;
}}
QToolButton#BarButton:hover {{ background-color: {p.panel_alt}; }}
QToolButton#BarButton:pressed {{ background-color: {p.bg}; }}
QToolButton#BarButton:disabled {{ background: transparent; }}
QToolButton#WinButton, QToolButton#WinClose {{
    background: transparent;
    border: none;
    border-radius: 0;
}}
QToolButton#WinButton:hover {{ background-color: {p.panel_alt}; }}
QToolButton#WinClose:hover {{ background-color: {p.err}; }}

/* ---------------- Cards ---------------- */
#Card {{
    background-color: {p.panel};
    border: 1px solid {p.border};
    border-radius: {r + 2}px;
}}
#SectionTitle {{
    font-size: {font_size - 2}px;
    font-weight: 800;
    color: {p.accent};
    letter-spacing: 2.5px;
}}
#Hint {{
    color: {p.muted};
    font-size: {font_size - 2}px;
}}

QGroupBox {{
    background-color: {p.panel};
    border: 1px solid {p.border};
    border-radius: {r + 2}px;
    margin-top: 16px;
    padding: {d['gap'] + 5}px {d['gap'] + 3}px {d['gap']}px {d['gap'] + 3}px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 3px 10px;
    color: {p.bg};
    background-color: {p.accent};
    border-radius: {r_sm}px;
    font-size: {font_size - 3}px;
    font-weight: 800;
    letter-spacing: 1.5px;
}}

/* ---------------- Inputs ---------------- */
QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QComboBox {{
    background-color: {p.panel_alt};
    border: 1px solid {p.border};
    border-radius: {r_sm}px;
    padding: {d['pad_y']}px {d['pad_x'] - 2}px;
    selection-background-color: {p.accent};
    selection-color: {p.bg};
}}
QLineEdit:hover, QPlainTextEdit:hover, QSpinBox:hover, QComboBox:hover {{
    border: 1px solid {p.border_light};
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus,
QSpinBox:focus, QComboBox:focus {{
    border: 1px solid {p.accent};
    background-color: {p.panel};
}}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QPlainTextEdit:disabled {{
    color: {p.muted};
    background-color: {p.bg};
    border-color: {p.border};
}}

QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {p.accent2};
    margin-right: 9px;
}}
QComboBox QAbstractItemView {{
    background-color: {p.panel_alt};
    border: 1px solid {p.accent};
    border-radius: {r_sm}px;
    selection-background-color: {p.accent};
    selection-color: {p.bg};
    padding: 4px;
    outline: none;
}}

QSpinBox::up-button, QSpinBox::down-button {{
    background-color: {p.border};
    border: none;
    width: 16px;
    border-radius: 3px;
    margin: 1px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background-color: {p.accent};
}}

/* ---------------- Buttons ---------------- */
QPushButton {{
    background-color: {p.panel_alt};
    border: 1px solid {p.border_light};
    border-radius: {r_sm}px;
    padding: {d['pad_y'] + 1}px {d['pad_x'] + 4}px;
    color: {p.text};
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: {p.panel};
    border-color: {p.accent2};
    color: {p.accent2};
}}
QPushButton:pressed {{ background-color: {p.bg}; }}
QPushButton:disabled {{
    color: {p.muted};
    background-color: {p.bg};
    border-color: {p.border};
}}

QPushButton#Primary {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {p.accent}, stop:1 {p.accent2});
    border: 1px solid {p.accent};
    color: {p.bg};
    font-weight: 800;
    letter-spacing: 0.8px;
    padding: {d['pad_y'] + 2}px {d['pad_x'] + 8}px;
}}
QPushButton#Primary:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {p.accent_hover}, stop:1 {p.accent2});
    color: {p.bg};
}}
QPushButton#Primary:disabled {{
    background: {p.accent_dim};
    border-color: {p.accent_dim};
    color: {p.muted};
}}
QPushButton#Ghost {{
    background-color: transparent;
    border: 1px solid {p.border_light};
}}
QPushButton#Ghost:hover {{
    background-color: {p.panel_alt};
    border-color: {p.accent};
    color: {p.accent};
}}
QPushButton#Danger:hover {{
    border-color: {p.err};
    color: {p.err};
}}

/* ---------------- Section nav ---------------- */
#NavList {{
    background-color: {p.panel};
    border: 1px solid {p.border};
    border-radius: {r + 2}px;
    padding: 5px;
    outline: none;
}}
#NavList::item {{
    padding: {d['row'] + 2}px 10px;
    border-radius: {r_sm}px;
    border-left: 3px solid transparent;
    color: {p.muted};
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: {tab_case};
}}
#NavList::item:hover {{
    background-color: {p.panel_alt};
    color: {p.text};
}}
#NavList::item:selected {{
    background-color: {p.panel_alt};
    border-left: 3px solid {p.accent};
    color: {p.accent};
}}

/* ---------------- Tabs (dialogs) ---------------- */
QTabWidget::pane {{
    border: 1px solid {p.border};
    border-radius: {r + 2}px;
    background-color: {p.panel};
    top: -1px;
}}
QTabBar::tab {{
    background-color: transparent;
    color: {p.muted};
    padding: {d['tab']}px 15px;
    margin-right: 2px;
    border-bottom: 2px solid transparent;
    font-weight: 700;
    letter-spacing: 1px;
}}
QTabBar::tab:hover {{ color: {p.text}; }}
QTabBar::tab:selected {{
    color: {p.accent};
    border-bottom: 2px solid {p.accent};
}}

/* ---------------- Table ---------------- */
QTableWidget, QTableView {{
    background-color: {p.panel};
    alternate-background-color: {p.panel_alt};
    border: 1px solid {p.border};
    border-radius: {r + 2}px;
    gridline-color: {p.border};
    selection-background-color: {p.accent_dim};
    selection-color: {p.text};
    outline: none;
}}
QTableWidget::item, QTableView::item {{ padding: {d['row']}px 8px; border: none; }}
QTableWidget::item:selected {{ background-color: {p.accent_dim}; }}
QHeaderView::section {{
    background-color: {p.panel_alt};
    color: {p.accent2};
    padding: 8px;
    border: none;
    border-right: 1px solid {p.border};
    border-bottom: 1px solid {p.accent};
    font-weight: 800;
    font-size: {font_size - 2}px;
    letter-spacing: 1.2px;
}}
QHeaderView::section:last {{ border-right: none; }}
QTableCornerButton::section {{ background-color: {p.panel_alt}; border: none; }}

/* ---------------- Progress ---------------- */
QProgressBar {{
    background-color: {p.bg};
    border: 1px solid {p.border};
    border-radius: {r_sm}px;
    height: 16px;
    text-align: center;
    color: {p.text};
    font-size: {font_size - 3}px;
    font-weight: 800;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {p.accent}, stop:1 {p.accent2});
    border-radius: {max(2, r_sm - 1)}px;
}}

/* ---------------- Checks ---------------- */
QCheckBox, QRadioButton {{ spacing: 8px; padding: 2px 0; }}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 15px; height: 15px;
    border: 1px solid {p.border_light};
    background-color: {p.panel_alt};
}}
QCheckBox::indicator {{ border-radius: 4px; }}
QRadioButton::indicator {{ border-radius: 8px; }}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{ border-color: {p.accent}; }}
QCheckBox::indicator:checked {{
    background-color: {p.accent};
    border-color: {p.accent};
}}
QRadioButton::indicator:checked {{
    background-color: {p.accent};
    border: 4px solid {p.panel_alt};
}}
QCheckBox:disabled, QRadioButton:disabled {{ color: {p.muted}; }}

/* ---------------- Log ---------------- */
#LogView {{
    background-color: {p.log_bg};
    border: 1px solid {p.border};
    border-radius: {r + 2}px;
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: {font_size - 2}px;
    color: {p.muted};
    padding: 8px;
    selection-background-color: {p.accent};
    selection-color: {p.bg};
}}

/* ---------------- Scrollbars ---------------- */
QScrollBar:vertical {{ background: transparent; width: 11px; margin: 2px; }}
QScrollBar::handle:vertical {{
    background: {p.border_light};
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {p.accent}; }}
QScrollBar:horizontal {{ background: transparent; height: 11px; margin: 2px; }}
QScrollBar::handle:horizontal {{
    background: {p.border_light};
    border-radius: 5px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{ background: {p.accent}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}

/* ---------------- Frameless shell ---------------- */
#RootFrame {{
    background-color: {p.bg};
    border: 1px solid {p.border_light};
}}
#EmptyState {{
    color: {p.muted};
    font-size: {font_size}px;
    background: transparent;
}}

/* ---------------- Misc ---------------- */
QSplitter::handle {{ background-color: transparent; }}
QSplitter::handle:hover {{ background-color: {p.accent}; }}
QStatusBar {{
    background-color: {p.panel};
    border-top: 1px solid {p.border};
    color: {p.muted};
}}
QStatusBar::item {{ border: none; }}
QMenu {{
    background-color: {p.panel_alt};
    border: 1px solid {p.accent};
    border-radius: {r_sm}px;
    padding: 5px;
}}
QMenu::item {{ padding: 7px 24px 7px 12px; border-radius: 4px; }}
QMenu::item:selected {{ background-color: {p.accent}; color: {p.bg}; }}
QMenu::separator {{ height: 1px; background: {p.border}; margin: 4px 8px; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QLabel {{ background: transparent; }}
QMessageBox, QInputDialog, QFileDialog {{ background-color: {p.panel}; }}
QDialog {{ background-color: {p.bg}; }}
"""
