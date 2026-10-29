"""Draws Camera Shake's Loop (2026-10-29) over three cycles into camshake_loop.png: a plain handheld shake cycled
as it is (it jumps at every seam), the same settings looped, and a looped walk and run.

  $env:QT_QPA_PLATFORM = "offscreen"
  & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/camshake/render_camshake_loop.py
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
CYCLES = 3
WIDTH, HEIGHT = 1500, 900
BACK = QtGui.QColor(30, 31, 34)
PANEL = QtGui.QColor(41, 43, 48)
GRID = QtGui.QColor(70, 72, 80)
SEAM = QtGui.QColor(224, 122, 54)
TEXT = QtGui.QColor(220, 220, 225)
MUTED = QtGui.QColor(150, 152, 160)
COLOURS = (QtGui.QColor(110, 170, 255), QtGui.QColor(255, 160, 70), QtGui.QColor(120, 210, 130),
           QtGui.QColor(230, 230, 235))
NAMES = ("tilt / nod", "pan / turn", "roll", "up, cm")


def chart(painter, rect, frames, series, title, scale, cycle):
    painter.fillRect(rect, PANEL)
    inner = rect.adjusted(46, 26, -12, -18)
    mid = inner.center().y()
    span = float(frames[-1] - frames[0]) or 1.0
    painter.setPen(QtGui.QPen(GRID, 1))
    painter.drawLine(inner.left(), mid, inner.right(), mid)
    for value in (-scale, scale):
        y = mid - value / scale * inner.height() / 2.0
        painter.drawLine(inner.left(), int(y), inner.right(), int(y))
        painter.setPen(MUTED)
        painter.drawText(QtCore.QRectF(rect.left() + 2, y - 8, 40, 16), QtCore.Qt.AlignRight, "%+g" % value)
        painter.setPen(QtGui.QPen(GRID, 1))
    pen = QtGui.QPen(SEAM, 1, QtCore.Qt.DashLine)
    painter.setPen(pen)
    for k in range(1, CYCLES):
        x = inner.left() + k * cycle / span * inner.width()
        painter.drawLine(int(x), inner.top(), int(x), inner.bottom())
    painter.setPen(TEXT)
    painter.drawText(QtCore.QRectF(rect.left() + 8, rect.top() + 4, rect.width() - 16, 18), QtCore.Qt.AlignLeft,
                     "%s  -  a cycle of %d frames at 30 fps, %d cycles, the seams dashed" % (title, cycle, CYCLES))
    for axis, values in enumerate(series):
        if values is None:
            continue
        path = QtGui.QPainterPath()
        for i, f in enumerate(frames):
            x = inner.left() + (f - frames[0]) / span * inner.width()
            y = mid - values[i] / scale * inner.height() / 2.0
            path.moveTo(x, y) if i == 0 else path.lineTo(x, y)
        painter.setPen(QtGui.QPen(COLOURS[axis], 1.6))
        painter.drawPath(path)


def cycled(rot, cycle):
    """A shake made over one cycle, played again and again as Maya's cycle infinity would."""
    one = rot[:cycle]
    return np.concatenate([one] * CYCLES + [rot[:1]])


def main():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])  # noqa: F841
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
                     "Camera Shake - Loop: the range is one cycle, its last frame shows its first; degrees")
    for axis in range(4):
        painter.setPen(COLOURS[axis])
        painter.drawText(QtCore.QRectF(WIDTH - 420 + axis * 100, 8, 100, 24), QtCore.Qt.AlignLeft, NAMES[axis])

    rows = []
    hand = cs.preset("handheld", "Nervous", {"ease": 0.0, "seed": 4})
    cycle = 60
    frames = np.arange(0, CYCLES * cycle + 1)
    plain, _ = cs.handheld(np.arange(0, cycle + 1), 0, cycle, FPS, hand)
    rows.append((frames, list(cycled(plain, cycle).T), "Handheld: Nervous, Loop off, cycled as it is", 4.0, cycle))
    looped, _ = cs.handheld(frames, 0, cycle, FPS, dict(hand, loop=True))
    rows.append((frames, list(looped.T), "Handheld: Nervous, Loop on", 4.0, cycle))
    for label, cycle in (("Walk", 60), ("Run", 45)):
        s = cs.preset("bobbing", label, {"loop": True, "seed": 2, "ease": 0.0})
        frames = np.arange(0, CYCLES * cycle + 1)
        rot, off = cs.bobbing(frames, 0, cycle, FPS, s)
        tempo, strides = cs.loop_tempo(s["tempo"], cycle, FPS)
        rows.append((frames, list(rot.T) + [off[:, 1]],
                     "Bobbing: %s, Loop on - %d strides at %g steps/min (Tempo %g)" % (
                         label, strides, round(tempo, 1), round(s["tempo"], 1)), 6.0, cycle))
    top = 40
    tall = (HEIGHT - top - 16) / len(rows)
    for row, (frames, series, title, scale, cycle) in enumerate(rows):
        rect = QtCore.QRect(16, int(top + row * tall), WIDTH - 32, int(tall - 10))
        chart(painter, rect, frames, series, title, scale, cycle)
    painter.end()
    out = os.path.join(HERE, "camshake_loop.png")
    image.save(out)
    print(out)


main()
