"""A filmstrip of Space's tap flown in and out (maya_panezoom), offscreen, on drawn stand-ins.

mayapy render_pane_zoom.py  ->  pane_zoom.png beside this file.
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "SkeldarAnim"))

from PySide6 import QtCore, QtGui, QtWidgets       # noqa: E402

import maya_panezoom                               # noqa: E402
import maya_panezoom_rules as rules                # noqa: E402

W, H = 480, 300
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def view(painter, rect, name, top, bottom):
    g = QtGui.QLinearGradient(rect.topLeft(), rect.bottomLeft())
    g.setColorAt(0, QtGui.QColor(top))
    g.setColorAt(1, QtGui.QColor(bottom))
    painter.fillRect(rect, g)
    painter.fillRect(QtCore.QRectF(rect.x(), rect.y(), rect.width(), 16), QtGui.QColor("#2a2c30"))
    painter.setPen(QtGui.QColor("#d8d8d8"))
    painter.drawText(rect.adjusted(6, 1, 0, 0), QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop, name)
    c = rect.center()
    painter.setBrush(QtGui.QColor("#c9a36a"))
    painter.setPen(QtCore.Qt.NoPen)
    painter.drawEllipse(c, rect.width() * 0.08, rect.height() * 0.2)


def quad():
    img = QtGui.QImage(W, H, QtGui.QImage.Format_ARGB32)
    img.fill(QtGui.QColor("#1b1c1f"))
    p = QtGui.QPainter(img)
    names = (("top", "#5f6c78", "#3b434b"), ("persp", "#7a8794", "#2e3238"),
             ("front", "#5f6c78", "#3b434b"), ("side", "#5f6c78", "#3b434b"))
    for i, (n, a, b) in enumerate(names):
        x, y = (i % 2) * W / 2, (i // 2) * H / 2
        view(p, QtCore.QRectF(x + 1, y + 1, W / 2 - 2, H / 2 - 2), n, a, b)
    p.end()
    return img


def single():
    img = QtGui.QImage(W, H, QtGui.QImage.Format_ARGB32)
    p = QtGui.QPainter(img)
    view(p, QtCore.QRectF(0, 0, W, H), "persp", "#7a8794", "#2e3238")
    p.end()
    return img


QUARTER = (W / 2 + 1, 1.0, W / 2 - 2, H / 2 - 2)
FULL = (0.0, 0.0, float(W), float(H))
TIMES = (0, 40, 90, 160, 260, 360, 420)


def strip(kind):
    out = []
    for ms in TIMES:
        clock = {"t": ms / 1000.0}
        if kind == rules.IN:
            z = maya_panezoom.Zoom(kind, quad(), None, None, None, "p", clock=lambda: clock["t"])
            z.setup(single(), QUARTER, FULL)
        else:
            z = maya_panezoom.Zoom(kind, single(), None, None, None, "p", clock=lambda: clock["t"])
            z.setup(quad(), FULL, QUARTER)
        z.started = 0.0
        live = single() if kind == rules.IN else quad()       # what stands under the overlay
        img = QtGui.QImage(live)
        p = QtGui.QPainter(img)
        z.paint(p, QtCore.QRectF(0, 0, W, H))
        p.end()
        out.append((ms, img))
    return out


rows = [strip(rules.IN), strip(rules.OUT)]
cell_w, cell_h = W // 2, H // 2 + 18
sheet = QtGui.QImage(cell_w * len(TIMES), cell_h * 2, QtGui.QImage.Format_ARGB32)
sheet.fill(QtGui.QColor("#111214"))
p = QtGui.QPainter(sheet)
p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
for r, row in enumerate(rows):
    for c, (ms, img) in enumerate(row):
        p.drawImage(QtCore.QRectF(c * cell_w + 2, r * cell_h + 16, cell_w - 4, H / 2), img)
        p.setPen(QtGui.QColor("#e07a36" if c == 0 else "#9aa0a8"))
        p.drawText(c * cell_w + 6, r * cell_h + 12, ("IN " if r == 0 else "OUT ") + "%d ms" % ms)
p.end()
path = os.path.join(HERE, "pane_zoom.png")
sheet.save(path)
print(path)
