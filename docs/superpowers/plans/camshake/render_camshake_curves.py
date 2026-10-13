"""Draws every preset's shake - tilt, pan and roll over time - into camshake_curves.png.

  $env:QT_QPA_PLATFORM = "offscreen"
  & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/camshake/render_camshake_curves.py
"""

import importlib.util
import os

import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "skeldar_camshake_render", os.path.join(HERE, "..", "..", "..", "..", "SkeldarAnim", "maya_camshake.py"))
cs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cs)

FPS = 30.0
WIDTH, HEIGHT = 1500, 980
BACK = QtGui.QColor(30, 31, 34)
PANEL = QtGui.QColor(41, 43, 48)
GRID = QtGui.QColor(70, 72, 80)
TEXT = QtGui.QColor(220, 220, 225)
MUTED = QtGui.QColor(150, 152, 160)
COLOURS = (QtGui.QColor(110, 170, 255), QtGui.QColor(255, 160, 70), QtGui.QColor(120, 210, 130))
NAMES = ("tilt", "pan", "roll")


def chart(painter, rect, frames, rot, title, scale):
    painter.fillRect(rect, PANEL)
    inner = rect.adjusted(46, 26, -12, -18)
    painter.setPen(QtGui.QPen(GRID, 1))
    mid = inner.center().y()
    painter.drawLine(inner.left(), mid, inner.right(), mid)
    for value in (-scale, scale):
        y = mid - value / scale * inner.height() / 2.0
        painter.drawLine(inner.left(), int(y), inner.right(), int(y))
        painter.setPen(MUTED)
        painter.drawText(QtCore.QRectF(rect.left() + 2, y - 8, 40, 16), QtCore.Qt.AlignRight, "%+g" % value)
        painter.setPen(QtGui.QPen(GRID, 1))
    painter.setPen(TEXT)
    peak = float(np.abs(rot).max())
    painter.drawText(QtCore.QRectF(rect.left() + 8, rect.top() + 4, rect.width() - 16, 18), QtCore.Qt.AlignLeft,
                     "%s  -  peak %.2f deg, %d frames at 30 fps" % (title, peak, len(frames)))
    span = float(frames[-1] - frames[0]) or 1.0
    for axis in range(3):
        path = QtGui.QPainterPath()
        for i, f in enumerate(frames):
            x = inner.left() + (f - frames[0]) / span * inner.width()
            y = mid - rot[i, axis] / scale * inner.height() / 2.0
            path.moveTo(x, y) if i == 0 else path.lineTo(x, y)
        painter.setPen(QtGui.QPen(COLOURS[axis], 1.6))
        painter.drawPath(path)


def main():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    # Offscreen Qt has no font of its own: take Windows'.
    family = None
    loaded = QtGui.QFontDatabase.addApplicationFont(r"C:\Windows\Fonts\segoeui.ttf")
    if loaded >= 0:
        family = QtGui.QFontDatabase.applicationFontFamilies(loaded)[0]
    image = QtGui.QImage(WIDTH, HEIGHT, QtGui.QImage.Format_RGB32)
    image.fill(BACK)
    painter = QtGui.QPainter(image)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    font = QtGui.QFont(family) if family else painter.font()
    font.setPixelSize(13)
    painter.setFont(font)
    painter.setPen(TEXT)
    painter.drawText(QtCore.QRectF(16, 8, WIDTH - 32, 24), QtCore.Qt.AlignLeft,
                     "Camera Shake - every preset, seed 1: tilt (about X), pan (about Y), roll (about Z), degrees")
    for axis in range(3):
        painter.setPen(COLOURS[axis])
        painter.drawText(QtCore.QRectF(WIDTH - 260 + axis * 80, 8, 80, 24), QtCore.Qt.AlignLeft, NAMES[axis])
    column = (WIDTH - 48) / 2.0
    top = 40
    hand_rows = cs.PRESETS["handheld"]
    hit_rows = cs.PRESETS["impact"]
    tall = (HEIGHT - top - 16) / len(hand_rows)
    for row, (label, _) in enumerate(hand_rows):
        s = cs.preset("handheld", label, {"ease": 6.0})
        frames = np.arange(0, 301)
        rot, _ = cs.handheld(frames, 0, 300, FPS, s)
        rect = QtCore.QRect(16, int(top + row * tall), int(column), int(tall - 10))
        chart(painter, rect, frames, rot, "Handheld: " + label, 3.0)
    short = (HEIGHT - top - 16) / len(hit_rows)
    for row, (label, _) in enumerate(hit_rows):
        s = cs.preset("impact", label, {"direction": "Left"})
        frames = np.arange(0, 61)
        rot, _ = cs.impact(frames, 0, 60, FPS, s)
        rect = QtCore.QRect(int(32 + column), int(top + row * short), int(column), int(short - 10))
        chart(painter, rect, frames, rot, "Impact: %s (from %s, waves of %g fr, %s)" % (
            label, cs.SIDES[s["direction"]], s["wave"], s["decay"].lower()), 10.0)
    painter.end()
    out = os.path.join(HERE, "camshake_curves.png")
    image.save(out)
    print(out)


main()
