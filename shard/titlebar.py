"""Frameless window chrome: a slim title bar with the app's actions built in."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QToolButton, QWidget,
)

from . import APP_NAME
from .icons import icon, shard_mark
from .theme import Palette

BAR_HEIGHT = 40
RESIZE_MARGIN = 5

# key, icon, tooltip
ACTIONS: list[tuple[str, str, str]] = [
    ("add", "plus", "Add the URLs to the queue Ctrl+Enter"),
    ("start", "play", "Start downloading Ctrl+D"),
    ("pause", "pause", "Pause every running download"),
    ("stop", "stop", "Stop everything"),
    ("|", "", ""),
    ("formats", "search", "Inspect the available formats Ctrl+I"),
    ("command", "terminal", "Preview the exact yt-dlp command Ctrl+K"),
    ("|", "", ""),
    ("folder", "folder", "Open the download folder Ctrl+O"),
    ("clear", "trash", "Clear finished rows"),
    ("|", "", ""),
    ("prefs", "sliders", "Preferences Ctrl+,"),
]

WINDOW_BUTTONS: list[tuple[str, str, str]] = [
    ("minimize", "minimize", "Minimize"),
    ("maximize", "maximize", "Maximize"),
    ("close", "close", "Close"),
]


class ResizeGrip(QWidget):
    """A thin invisible strip that hands resizing back to the OS."""

    def __init__(self, window: QWidget, edges: Qt.Edge, cursor: Qt.CursorShape):
        super().__init__(window)
        self._window = window
        self._edges = edges
        self.setCursor(cursor)
        self.setAttribute(Qt.WidgetAttribute.WA_NoMousePropagation, True)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self._window.windowHandle()
            if handle is not None:
                handle.startSystemResize(self._edges)


def install_resize_grips(window: QWidget) -> list[ResizeGrip]:
    """Create the eight edge/corner grips and return them for layout."""
    E = Qt.Edge
    specs = [
        (E.TopEdge, Qt.CursorShape.SizeVerCursor),
        (E.BottomEdge, Qt.CursorShape.SizeVerCursor),
        (E.LeftEdge, Qt.CursorShape.SizeHorCursor),
        (E.RightEdge, Qt.CursorShape.SizeHorCursor),
        (E.TopEdge | E.LeftEdge, Qt.CursorShape.SizeFDiagCursor),
        (E.BottomEdge | E.RightEdge, Qt.CursorShape.SizeFDiagCursor),
        (E.TopEdge | E.RightEdge, Qt.CursorShape.SizeBDiagCursor),
        (E.BottomEdge | E.LeftEdge, Qt.CursorShape.SizeBDiagCursor),
    ]
    return [ResizeGrip(window, edges, cursor) for edges, cursor in specs]


def layout_resize_grips(grips: list[ResizeGrip], width: int, height: int) -> None:
    m = RESIZE_MARGIN
    geoms = [
        (m, 0, width - 2 * m, m),                       # top
        (m, height - m, width - 2 * m, m),              # bottom
        (0, m, m, height - 2 * m),                      # left
        (width - m, m, m, height - 2 * m),              # right
        (0, 0, m, m),                                   # top-left
        (width - m, height - m, m, m),                  # bottom-right
        (width - m, 0, m, m),                           # top-right
        (0, height - m, m, m),                          # bottom-left
    ]
    for grip, geom in zip(grips, geoms):
        grip.setGeometry(*geom)
        grip.raise_()


class TitleBar(QWidget):
    """Slim chrome holding the identity, the app's actions and window controls."""

    action_triggered = Signal(str)

    def __init__(self, window: QWidget):
        super().__init__(window)
        self._window = window
        self.setObjectName("TitleBar")
        self.setFixedHeight(BAR_HEIGHT)

        self.buttons: dict[str, QToolButton] = {}
        self._specs: dict[str, str] = {}
        self._separators: list[QFrame] = []

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 0, 0, 0)
        lay.setSpacing(0)

        self.mark = QLabel()
        self.mark.setFixedSize(22, 22)
        lay.addWidget(self.mark)

        self.name = QLabel(APP_NAME.upper())
        self.name.setObjectName("BrandName")
        lay.addSpacing(8)
        lay.addWidget(self.name)
        lay.addSpacing(12)
        self._separators.append(self._separator(lay))
        lay.addSpacing(6)

        for key, glyph, tip in ACTIONS:
            if key == "|":
                lay.addSpacing(5)
                self._separators.append(self._separator(lay))
                lay.addSpacing(5)
                continue
            button = QToolButton()
            button.setObjectName("BarButton")
            button.setFixedSize(30, 28)
            button.setIconSize(QSize(18, 18))
            button.setToolTip(tip)
            button.setCursor(Qt.CursorShape.ArrowCursor)
            button.clicked.connect(lambda _=False, k=key: self.action_triggered.emit(k))
            self.buttons[key] = button
            self._specs[key] = glyph
            lay.addWidget(button)

        lay.addStretch(1)

        self.status_chip = QLabel("")
        self.status_chip.setObjectName("BarChip")
        lay.addWidget(self.status_chip)
        lay.addSpacing(10)

        for key, glyph, tip in WINDOW_BUTTONS:
            button = QToolButton()
            button.setObjectName("WinClose" if key == "close" else "WinButton")
            button.setFixedSize(46, BAR_HEIGHT)
            button.setIconSize(QSize(18, 18))
            button.setToolTip(tip)
            button.setCursor(Qt.CursorShape.ArrowCursor)
            button.clicked.connect(lambda _=False, k=key: self.action_triggered.emit(k))
            self.buttons[key] = button
            self._specs[key] = glyph
            lay.addWidget(button)

    # ------------------------------------------------------------------
    def _separator(self, lay: QHBoxLayout) -> QFrame:
        line = QFrame()
        line.setObjectName("BarSep")
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFixedWidth(1)
        line.setFixedHeight(18)
        lay.addWidget(line)
        return line

    def retheme(self, palette: Palette) -> None:
        self.mark.setPixmap(shard_mark(palette.accent, palette.accent2, 22))
        for key, glyph in self._specs.items():
            if not glyph:
                continue
            hover = "#ffffff" if key == "close" else palette.accent
            self.buttons[key].setIcon(icon(glyph, palette.muted, hover))

    def set_maximized(self, maximized: bool) -> None:
        button = self.buttons.get("maximize")
        if button is None:
            return
        self._specs["maximize"] = "restore" if maximized else "maximize"
        button.setToolTip("Restore" if maximized else "Maximize")

    def set_status(self, text: str) -> None:
        self.status_chip.setText(text)

    # ------------------------------------------------------------------
    def _is_drag_area(self, pos) -> bool:
        child = self.childAt(pos)
        return child is None or isinstance(child, QLabel)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._is_drag_area(event.position().toPoint()):
            handle = self._window.windowHandle()
            if handle is not None:
                handle.startSystemMove()
                return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._is_drag_area(event.position().toPoint()):
            self.action_triggered.emit("maximize")
            return
        super().mouseDoubleClickEvent(event)
