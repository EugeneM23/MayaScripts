"""Draw the SkeldarAnim shelf icons (ten: nine on the shelf plus the picker's).

32x32 PNG on a dark rounded plate so they read on Maya's shelf: flat
glyphs, ~2 px strokes, one accent colour per tool. Regenerate with:

    $env:QT_QPA_PLATFORM = 'offscreen'
    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' icons/make_icons.py
"""

import os
import sys

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QGuiApplication, QImage, QPainter,
                           QPainterPath, QPen)

SIZE = 32
PLATE = QColor("#262626")
EDGE = QColor("#4a4a4a")


def _canvas():
    image = QImage(SIZE, SIZE, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QPen(EDGE, 1))
    painter.setBrush(PLATE)
    painter.drawRoundedRect(QRectF(0.5, 0.5, SIZE - 1, SIZE - 1), 6, 6)
    return image, painter


def _pen(colour, width):
    return QPen(QColor(colour), width, Qt.SolidLine, Qt.RoundCap,
                Qt.RoundJoin)


def draw_picker(path):
    """A miniature of the body map: circle head, dot buttons."""
    image, painter = _canvas()
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#4fc3f7"))
    painter.drawEllipse(QPointF(16, 7.5), 3.0, 3.0)
    dots = [(16, 13.5), (16, 17), (16, 20.5),                    # spine
            (11.5, 13.5), (8.5, 17), (20.5, 13.5), (23.5, 17),   # arms
            (13.5, 24), (12.5, 27.5), (18.5, 24), (19.5, 27.5)]  # legs
    for x, y in dots:
        painter.drawEllipse(QPointF(x, y), 1.7, 1.7)
    painter.end()
    image.save(path)


def draw_uebridge(path):
    """A clip plate with frame ticks and an arrow coming into the scene."""
    image, painter = _canvas()
    painter.setPen(_pen("#ffa726", 2.0))
    painter.setBrush(Qt.NoBrush)
    painter.drawRoundedRect(QRectF(7, 6, 18, 8), 2, 2)
    painter.setPen(_pen("#ffa726", 1.3))
    for x in (11, 14.5, 18, 21.5):
        painter.drawLine(QPointF(x, 8), QPointF(x, 12))
    painter.setPen(_pen("#ffa726", 2.4))
    painter.drawLine(QPointF(16, 17), QPointF(16, 26.5))
    painter.drawLine(QPointF(11.5, 22), QPointF(16, 26.5))
    painter.drawLine(QPointF(20.5, 22), QPointF(16, 26.5))
    painter.end()
    image.save(path)


def draw_scenesetup(path):
    """A gear: the scene's settings (2026-09-07 - «шестеренку вместо меча»)."""
    import math
    image, painter = _canvas()
    centre = QPointF(16, 16)
    painter.setPen(_pen("#cfd8dc", 3.2))
    for i in range(8):
        angle = math.radians(i * 45.0)
        inner = QPointF(16 + 7.6 * math.cos(angle), 16 + 7.6 * math.sin(angle))
        outer = QPointF(16 + 11.2 * math.cos(angle),
                        16 + 11.2 * math.sin(angle))
        painter.drawLine(inner, outer)
    painter.setPen(_pen("#cfd8dc", 3.0))
    painter.setBrush(Qt.NoBrush)
    painter.drawEllipse(centre, 6.8, 6.8)
    painter.setPen(Qt.NoPen)
    painter.setBrush(PLATE)
    painter.drawEllipse(centre, 3.2, 3.2)
    painter.end()
    image.save(path)


def _figure(painter, x, colour):
    """A stick figure standing on x: head, spine, arms, legs."""
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(colour))
    painter.drawEllipse(QPointF(x, 8.0), 2.4, 2.4)
    painter.setPen(_pen(colour, 1.8))
    painter.drawLine(QPointF(x, 10.5), QPointF(x, 19.5))
    painter.drawLine(QPointF(x - 3.5, 13.0), QPointF(x + 3.5, 13.0))
    painter.drawLine(QPointF(x, 19.5), QPointF(x - 3.0, 26.0))
    painter.drawLine(QPointF(x, 19.5), QPointF(x + 3.0, 26.0))


def draw_retarget(path):
    """Two figures and an arrow: the clip's skeleton onto the rig."""
    image, painter = _canvas()
    _figure(painter, 8.0, "#90a4ae")
    _figure(painter, 24.0, "#7bd88f")
    painter.setPen(_pen("#7bd88f", 2.0))
    painter.drawLine(QPointF(12.5, 16.5), QPointF(19.5, 16.5))
    painter.drawLine(QPointF(17.0, 14.0), QPointF(19.5, 16.5))
    painter.drawLine(QPointF(17.0, 19.0), QPointF(19.5, 16.5))
    painter.end()
    image.save(path)



def draw_overshoot(path):
    """A curve overshooting a dashed target line and settling."""
    image, painter = _canvas()
    dashed = QPen(QColor(129, 199, 132, 150), 1.3, Qt.DashLine)
    painter.setPen(dashed)
    painter.drawLine(QPointF(5, 13), QPointF(27, 13))
    curve = QPainterPath(QPointF(5.5, 26.5))
    curve.cubicTo(QPointF(9, 26.5), QPointF(10, 8.5), QPointF(13.5, 8.5))
    curve.cubicTo(QPointF(16.5, 8.5), QPointF(16, 16), QPointF(18.5, 16))
    curve.cubicTo(QPointF(20.5, 16), QPointF(20.5, 12), QPointF(22.5, 12))
    curve.cubicTo(QPointF(24.5, 12), QPointF(24.5, 13), QPointF(26.5, 13))
    painter.setPen(_pen("#81c784", 2.2))
    painter.setBrush(Qt.NoBrush)
    painter.drawPath(curve)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#81c784"))
    painter.drawEllipse(QPointF(5.5, 26.5), 2.0, 2.0)
    painter.end()
    image.save(path)


def draw_hotkeys(path):
    """A keycap with a spark: the map switches on."""
    image, painter = _canvas()
    painter.setPen(_pen("#ba68c8", 2.0))
    painter.setBrush(Qt.NoBrush)
    painter.drawRoundedRect(QRectF(6.5, 8.5, 14, 14), 3, 3)
    painter.setPen(_pen("#ba68c8", 1.6))
    painter.drawLine(QPointF(10, 19), QPointF(17, 19))
    painter.setPen(_pen("#ba68c8", 2.2))
    painter.drawLine(QPointF(13.5, 12), QPointF(13.5, 16))
    painter.setPen(_pen("#f06292", 2.2))
    painter.drawLine(QPointF(23, 10), QPointF(25.5, 15))
    painter.drawLine(QPointF(25.5, 15), QPointF(22, 15))
    painter.drawLine(QPointF(22, 15), QPointF(24.5, 21))
    painter.end()
    image.save(path)


def draw_vpstudio(path):
    """A lit sphere over its own shadow: the studio, in one glyph."""
    image, painter = _canvas()
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(255, 255, 255, 26))
    painter.drawEllipse(QRectF(6.0, 21.0, 20.0, 5.0))
    painter.setBrush(QColor("#4dd0e1"))
    painter.drawEllipse(QPointF(15.0, 15.5), 7.0, 7.0)
    painter.setBrush(QColor(0, 0, 0, 90))
    painter.drawEllipse(QPointF(17.4, 17.6), 6.4, 6.4)
    painter.setBrush(QColor("#fff59d"))
    painter.drawEllipse(QPointF(24.5, 7.5), 2.6, 2.6)
    painter.setPen(_pen("#fff59d", 1.2))
    for a, b in (((22.2, 4.6), (21.0, 3.2)), ((27.0, 4.6), (28.2, 3.2)),
                 ((22.2, 10.4), (21.0, 11.8))):
        painter.drawLine(QPointF(*a), QPointF(*b))
    painter.end()
    image.save(path)


def draw_colour(path):
    """Four palette chips: the swatch grid, in one glyph."""
    image, painter = _canvas()
    painter.setPen(Qt.NoPen)
    chips = (((7.5, 7.5), "#cc4038"), ((17.0, 7.5), "#e6bf33"),
             ((7.5, 17.0), "#59ad52"), ((17.0, 17.0), "#4085d9"))
    for (x, y), hue in chips:
        painter.setBrush(QColor(hue))
        painter.drawRoundedRect(QRectF(x, y, 7.5, 7.5), 1.6, 1.6)
    painter.setBrush(QColor("#e6e6e6"))
    painter.drawEllipse(QPointF(22.5, 22.5), 4.2, 4.2)
    painter.setBrush(QColor("#9b59d0"))
    painter.drawEllipse(QPointF(22.5, 22.5), 2.4, 2.4)
    painter.end()
    image.save(path)



DRAWERS = {
    "picker.png": draw_picker,
    "hotkeys.png": draw_hotkeys,
    "uebridge.png": draw_uebridge,
    "scenesetup.png": draw_scenesetup,
    "retarget.png": draw_retarget,
    "overshoot.png": draw_overshoot,
    "vpstudio.png": draw_vpstudio,
    "colour.png": draw_colour,
}


def main(out_dir=None):
    out_dir = out_dir or os.path.dirname(os.path.abspath(__file__))
    QGuiApplication.instance() or QGuiApplication([sys.argv[0]])
    for name, draw in sorted(DRAWERS.items()):
        draw(os.path.join(out_dir, name))
        print("wrote " + name)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
