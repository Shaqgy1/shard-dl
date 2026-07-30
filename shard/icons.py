"""Runtime-drawn vector icons, so every glyph recolours with the theme."""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush, QColor, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap,
    QPolygonF,
)

# All shapes are authored on a 24x24 grid and scaled to the requested size.
GRID = 24.0


def _pen(painter: QPainter, color: str, width: float) -> None:
    pen = QPen(QColor(color), width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)


def _fill(painter: QPainter, color: str) -> None:
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor(color)))


def _poly(*pts: tuple[float, float]) -> QPolygonF:
    return QPolygonF([QPointF(x, y) for x, y in pts])


def _draw(name: str, painter: QPainter, color: str, w: float) -> None:
    if name == "plus":
        _pen(painter, color, w)
        painter.drawLine(QPointF(12, 5.5), QPointF(12, 18.5))
        painter.drawLine(QPointF(5.5, 12), QPointF(18.5, 12))

    elif name == "play":
        _fill(painter, color)
        painter.drawPolygon(_poly((8.5, 5.5), (8.5, 18.5), (19, 12)))

    elif name == "pause":
        _fill(painter, color)
        painter.drawRoundedRect(QRectF(8, 5.5, 3.2, 13), 1.2, 1.2)
        painter.drawRoundedRect(QRectF(13.8, 5.5, 3.2, 13), 1.2, 1.2)

    elif name == "stop":
        _fill(painter, color)
        painter.drawRoundedRect(QRectF(7.5, 7.5, 9, 9), 1.6, 1.6)

    elif name == "folder":
        _pen(painter, color, w)
        path = QPainterPath()
        path.moveTo(3.5, 18.5)
        path.lineTo(3.5, 6)
        path.lineTo(9, 6)
        path.lineTo(11, 8.5)
        path.lineTo(20.5, 8.5)
        path.lineTo(20.5, 18.5)
        path.closeSubpath()
        painter.drawPath(path)

    elif name == "search":
        _pen(painter, color, w)
        painter.drawEllipse(QPointF(10.8, 10.8), 5.3, 5.3)
        painter.drawLine(QPointF(14.8, 14.8), QPointF(19, 19))

    elif name == "terminal":
        _pen(painter, color, w)
        painter.drawPolyline(_poly((5.5, 7.5), (10, 12), (5.5, 16.5)))
        painter.drawLine(QPointF(12, 16.5), QPointF(18.5, 16.5))

    elif name == "trash":
        _pen(painter, color, w)
        painter.drawLine(QPointF(4.5, 7), QPointF(19.5, 7))
        painter.drawLine(QPointF(9.5, 4.5), QPointF(14.5, 4.5))
        path = QPainterPath()
        path.moveTo(6.5, 7)
        path.lineTo(7.4, 19)
        path.lineTo(16.6, 19)
        path.lineTo(17.5, 7)
        painter.drawPath(path)

    elif name == "sliders":
        # A solid gear silhouette - thin strokes turn to mush at 18px.
        teeth = 8
        outline = QPainterPath()
        for i in range(teeth * 2):
            radius = 9.4 if i % 2 == 0 else 7.0
            angle = math.radians(i * (180.0 / teeth) - 90)
            point = QPointF(12 + radius * math.cos(angle), 12 + radius * math.sin(angle))
            if i == 0:
                outline.moveTo(point)
            else:
                outline.lineTo(point)
        outline.closeSubpath()
        hole = QPainterPath()
        hole.addEllipse(QPointF(12, 12), 3.5, 3.5)
        _fill(painter, color)
        painter.drawPath(outline.subtracted(hole))

    elif name == "clipboard":
        _pen(painter, color, w)
        painter.drawRoundedRect(QRectF(6, 5.5, 12, 14), 2, 2)
        painter.drawLine(QPointF(9.5, 5.5), QPointF(14.5, 5.5))

    elif name == "minimize":
        _pen(painter, color, w)
        painter.drawLine(QPointF(6.5, 12), QPointF(17.5, 12))

    elif name == "maximize":
        _pen(painter, color, w)
        painter.drawRect(QRectF(6.8, 6.8, 10.4, 10.4))

    elif name == "restore":
        _pen(painter, color, w)
        painter.drawRect(QRectF(5.8, 8.8, 9, 9))
        painter.drawPolyline(_poly((8.6, 8.4), (8.6, 5.8), (18.2, 5.8), (18.2, 15.2), (15.6, 15.2)))

    elif name == "close":
        _pen(painter, color, w)
        painter.drawLine(QPointF(7, 7), QPointF(17, 17))
        painter.drawLine(QPointF(17, 7), QPointF(7, 17))

    elif name == "chevron":
        _pen(painter, color, w)
        painter.drawPolyline(_poly((8.5, 10), (12, 13.8), (15.5, 10)))


def pixmap(name: str, color: str, size: int = 18, width: float = 1.9,
           dpr: float = 2.0) -> QPixmap:
    pm = QPixmap(int(size * dpr), int(size * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    # QPainter already works in logical units on a pixmap that carries a DPR,
    # so scale by the grid ratio only - multiplying by dpr here draws at 2x.
    scale = size / GRID
    painter.scale(scale, scale)
    _draw(name, painter, color, width / scale)
    painter.end()
    return pm


def icon(name: str, normal: str, active: str | None = None, size: int = 18,
         width: float = 1.9) -> QIcon:
    """Normal + hover (Active) states, so buttons light up without extra code."""
    result = QIcon()
    result.addPixmap(pixmap(name, normal, size, width), QIcon.Mode.Normal)
    result.addPixmap(pixmap(name, active or normal, size, width), QIcon.Mode.Active)
    result.addPixmap(pixmap(name, active or normal, size, width), QIcon.Mode.Selected)
    disabled = QColor(normal)
    disabled.setAlpha(90)
    result.addPixmap(pixmap(name, disabled.name(QColor.NameFormat.HexArgb), size, width),
                     QIcon.Mode.Disabled)
    return result


def shard_mark(accent: str, accent2: str, size: int = 22, dpr: float = 2.0) -> QPixmap:
    """The app logo: an angular crystal shard in the theme gradient."""
    pm = QPixmap(int(size * dpr), int(size * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(size / GRID, size / GRID)

    grad = QLinearGradient(0, 0, GRID, GRID)
    grad.setColorAt(0.0, QColor(accent))
    grad.setColorAt(1.0, QColor(accent2))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(grad))
    painter.drawPolygon(_poly((12, 1.5), (18.6, 9.2), (14.6, 22.5), (9.4, 22.5), (5.4, 9.2)))

    # Inner facet for a bit of depth.
    painter.setBrush(QBrush(QColor(255, 255, 255, 52)))
    painter.drawPolygon(_poly((12, 1.5), (18.6, 9.2), (14.6, 22.5), (12, 22.5)))
    painter.end()
    return pm


def app_icon(accent: str, accent2: str, bg: str) -> QIcon:
    """Window / tray / taskbar icon at several sizes."""
    result = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        grad = QLinearGradient(0, 0, size, size)
        grad.setColorAt(0.0, QColor(accent))
        grad.setColorAt(1.0, QColor(accent2))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(grad))
        painter.drawRoundedRect(QRectF(0, 0, size, size), size * 0.22, size * 0.22)

        painter.scale(size / GRID, size / GRID)
        painter.setBrush(QBrush(QColor(bg)))
        painter.drawPolygon(_poly((12, 3.0), (17.6, 9.6), (14.2, 21.0), (9.8, 21.0), (6.4, 9.6)))
        painter.end()
        result.addPixmap(pm)
    return result
