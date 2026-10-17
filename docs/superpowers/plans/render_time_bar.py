"""The Time Bar drawn offscreen at 150 % into time_bar.png (2026-10-16): the real strip
on an example take - no Maya. Run:

    $env:QT_QPA_PLATFORM='offscreen'; mayapy docs/superpowers/plans/render_time_bar.py
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
from maya_timebar import bar                                # noqa: E402
from test_timebar_bar import FakeLink                       # noqa: E402

QT = maya_hubqt.qt()
app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])
fonts = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
for name in ("segoeui.ttf", "segoeuib.ttf", "consola.ttf", "consolab.ttf"):
    if os.path.exists(os.path.join(fonts, name)):
        QT.QtGui.QFontDatabase.addApplicationFont(os.path.join(fonts, name))
app.setFont(QT.QtGui.QFont("Segoe UI", 9))

UI = 1.5
shots = []
for label, change in (("rest", {}),
                      ("highlight", {"highlight": (24, 41), "now": 31.0}),
                      ("playing", {"playing": True, "now": 47.0, "auto": False})):
    link = FakeLink()
    link.s.update(a0=-10.0, a1=120.0, p0=0.0, p1=95.0, now=30.0)
    link.k = ([0.0, 6.0, 12.0, 18.0, 24.0, 31.0, 34.5, 40.0, 48.0, 56.0, 64.0, 72.0, 80.0, 88.0, 95.0],
              [9.0, 27.0, 44.0, 68.0])
    link.marks = [(0.0, 14.0, (0.5, 0.66, 0.9), "Anticipation"), (14.0, 40.0, (0.88, 0.48, 0.21), "Attack"),
                  (40.0, 95.0, (0.56, 0.82, 0.6), "Recovery")]
    link.x["character"] = ""
    link.s.update(change)
    strip = bar.make(link, UI, maya_hubstyle.TOKENS, motion=True)
    strip.resize(int(1400 * UI), int(86 * UI))
    strip.show()
    app.processEvents()
    strip.opened = -100000.0                     # past the opening
    if label == "highlight":
        strip.transport["play"].hover = strip.transport["play"].goal = 1.0
        strip.timeline.key_lift[40.0] = 1.0
    if label == "playing":
        strip.timeline.reached[40.0] = strip.clock() - 150
        strip.timeline.reached[44.0] = strip.clock() - 30
        strip.loop.hover = 1.0
    shots.append(strip.grab().toImage())

pad = 12
out = QT.QtGui.QImage(shots[0].width() + 2 * pad, sum(s.height() + pad for s in shots) + pad,
                      QT.QtGui.QImage.Format_ARGB32)
out.fill(QT.QtGui.QColor("#141517"))
p = QT.QtGui.QPainter(out)
y = pad
for shot in shots:
    p.drawImage(pad, y, shot)
    y += shot.height() + pad
p.end()
target = os.path.join(HERE, "time_bar.png")
out.save(target)
print(target)
