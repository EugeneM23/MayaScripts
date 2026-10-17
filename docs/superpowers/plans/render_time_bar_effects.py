"""The Time Bar's effects (2026-10-17, the mockup carried into the strip): each one
rendered offscreen at a few moments of its life, on a fake link, into one sheet.

    $env:QT_QPA_PLATFORM='offscreen'; mayapy docs/superpowers/plans/render_time_bar_effects.py
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))

import maya_hubqt                                           # noqa: E402
import maya_hubstyle                                        # noqa: E402
from maya_timebar import bar                                # noqa: E402
from tests.test_timebar_bar import FakeLink                 # noqa: E402

QT = maya_hubqt.qt()
app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])
#  offscreen Qt has no font family: Windows' own, or every letter is a box
for name in ("segoeui.ttf", "segoeuib.ttf", "consola.ttf", "consolab.ttf"):
    QT.QtGui.QFontDatabase.addApplicationFont(os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts", name))
app.setFont(QT.QtGui.QFont("Segoe UI"))
UI = 1.5
OUT = os.path.join(HERE, "time_bar_effects.png")


class Clock(object):
    t = 1000.0

    def __call__(self):
        return self.t


def strip():
    link = FakeLink()
    s = bar.make(link, UI, maya_hubstyle.TOKENS, motion=True)
    s.resize(int(1500 * UI / 1.5 * 1.0), int(84 * UI))
    s.show()
    app.processEvents()
    clock = Clock()
    s.clock = clock
    s.opened = -10000.0
    return s, link, clock


def shots(label, start, ages):
    """[(label, image)] of one effect at `ages` ms after `start(strip, link)`."""
    s, link, clock = strip()
    clock.t = 1000.0
    start(s, link)
    out = []
    for age in ages:
        clock.t = 1000.0 + age
        for widget in s.moving:
            widget.step(16)
        s.fx.busy(clock.t)
        app.processEvents()
        out.append(("%s  +%d ms" % (label, age), s.grab().toImage()))
    s.deleteLater()
    return out


def set_key(s, link):
    link.k = (link.k[0] + [20.0], link.k[1])
    s.refresh(keys=True)


def delete_key(s, link):
    link.k = ([k for k in link.k[0] if k != 30.0], link.k[1])
    s.refresh(keys=True)


def press(s, link):
    E, Qt = QT.QtCore.QEvent, QT.QtCore.Qt
    b = s.play
    pos = QT.QtCore.QPointF(b.width() / 2.0, b.height() / 2.0)
    event = QT.QtGui.QMouseEvent(E.MouseButtonPress, pos, QT.QtCore.QPointF(b.mapToGlobal(pos.toPoint())),
                                 Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    QT.QtWidgets.QApplication.sendEvent(b, event)
    link.s["playing"] = True
    s.refresh()


def glide(s, link):
    s._go("end")
    s.on_time()                 # Maya's timeChanged job, which the fake link has not


def bookmark(s, link):
    link.marks.append((30.0, 45.0, (0.9, 0.5, 0.2), "Hit"))
    s._add_bookmark()


rows = [shots("Set key", set_key, (60, 180, 360)),
        shots("Delete key", delete_key, (60, 200, 420)),
        shots("Play", press, (40, 140, 300)),
        shots("Glide to end", glide, (60, 130, 220)),
        shots("Add bookmark", bookmark, (60, 160, 320))]

#  each shot cropped round its subject: the left two thirds of the strip
w = min(rows[0][0][1].width(), int(1040 * UI))
h = rows[0][0][1].height()
crop = QT.QtCore.QRect(0, 0, w, h)
cols = max(len(r) for r in rows)
label_h = 22
sheet = QT.QtGui.QImage(w, (h + label_h) * len(rows) * cols, QT.QtGui.QImage.Format_ARGB32)
sheet.fill(QT.QtGui.QColor("#1b1c20"))
p = QT.QtGui.QPainter(sheet)
font = QT.QtGui.QFont("Segoe UI")
font.setPixelSize(14)
p.setFont(font)
y = 0
for row in rows:
    for label, image in row:
        p.setPen(QT.QtGui.QColor("#d8d8dc"))
        p.drawText(8, y + 16, label)
        p.drawImage(0, y + label_h, image.copy(crop))
        y += h + label_h
p.end()
sheet.save(OUT)
print("saved", OUT)
