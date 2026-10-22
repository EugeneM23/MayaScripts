"""The Play glow (2026-10-22, mockup B): Play pressed, a soft accent glow fills the
timeline in from its edge and fades - the whole strip drawn offscreen at 150 % at seven
moments into time_bar_play_glow.png. No Maya. Run:

    $env:QT_QPA_PLATFORM='offscreen'; mayapy docs/superpowers/plans/render_time_bar_play_glow.py
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))
sys.path.insert(0, os.path.join(REPO, "tests"))

import maya_hubqt                                           # noqa: E402
import maya_hubstyle                                        # noqa: E402
from maya_timebar import bar, look                          # noqa: E402
from test_timebar_bar import FakeLink                       # noqa: E402

QT = maya_hubqt.qt()
app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])
UI = 1.5

link = FakeLink()
link.s.update(a0=0.0, a1=48.0, p0=0.0, p1=48.0, now=10.0)
link.k = ([0.0, 6.0, 12.0, 30.0, 40.0], [])
strip = bar.make(link, UI, maya_hubstyle.TOKENS, motion=True)
strip.resize(int(900 * UI), int(86 * UI))
strip.show()
app.processEvents()
strip.opened = -100000.0
strip.refresh(keys=True)
tl = strip.timeline
tl.played()
start = tl.play_at
top = tl.mapTo(strip, QT.QtCore.QPoint(0, 0)).y()
area = QT.QtCore.QRect(0, max(0, top - 4), strip.width(), tl.height() + 8)
shots = []
for ms in (0, 40, 84, 180, 320, 500, 700):
    strip.clock = (lambda m=ms: start + m)
    shots.append((ms, strip.grab(area).toImage()))

pad = 10
w, h = area.width(), area.height()
out = QT.QtGui.QImage(w + 2 * pad + 70, len(shots) * (h + pad) + pad, QT.QtGui.QImage.Format_ARGB32)
out.fill(QT.QtGui.QColor("#141517"))
p = QT.QtGui.QPainter(out)
p.setPen(QT.QtGui.QColor("#c8cbd2"))
for i, (ms, img) in enumerate(shots):
    y = pad + i * (h + pad)
    p.drawText(QT.QtCore.QRect(pad, y, 64, h), QT.QtCore.Qt.AlignVCenter, "%d ms" % ms)
    p.drawImage(pad + 70, y, img)
p.end()
target = os.path.join(HERE, "time_bar_play_glow.png")
out.save(target)
print("saved", target, [round(look.play_glow(m / float(look.EFFECT_MS["play"])), 3) for m, _ in shots])
