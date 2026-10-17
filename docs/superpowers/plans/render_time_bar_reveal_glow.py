"""The Time Bar's reveal glow (2026-10-17, mockup B: the racing edges), drawn offscreen
frame by frame into time_bar_reveal_glow.png: the real BottomEdge and strip on a fake
window, the cursor at 40 % across, at 150 %. Run:

    $env:QT_QPA_PLATFORM='offscreen'; mayapy docs/superpowers/plans/render_time_bar_reveal_glow.py
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))
sys.path.insert(0, REPO)

import maya_hubqt                                           # noqa: E402
import maya_hubstyle                                        # noqa: E402
from maya_timebar import bar, edge, look                    # noqa: E402
from tests.test_timebar_bar import FakeLink                 # noqa: E402

QT = maya_hubqt.qt()
app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])
fonts = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
for name in ("segoeui.ttf", "segoeuib.ttf", "consola.ttf", "consolab.ttf"):
    if os.path.exists(os.path.join(fonts, name)):
        QT.QtGui.QFontDatabase.addApplicationFont(os.path.join(fonts, name))
app.setFont(QT.QtGui.QFont("Segoe UI", 9))

UI = 1.5
W = int(1400 * UI)
window = (0, 0, W, 600)
link = FakeLink()
link.s.update(a0=-10.0, a1=120.0, p0=0.0, p1=95.0, now=30.0)
link.k = ([0.0, 6.0, 12.0, 18.0, 24.0, 31.0, 40.0, 48.0, 56.0, 64.0, 72.0, 80.0, 88.0, 95.0], [9.0, 27.0, 44.0, 68.0])
cursor = [int(W * 0.4), 590]
ctl = edge.BottomEdge(lambda parent: bar.make(link, UI, maya_hubstyle.TOKENS, parent=parent, motion=True),
                      window_rect=lambda: window, cursor=lambda: tuple(cursor), buttons=lambda: False,
                      app_active=lambda: True, motion=True, over_maya=lambda: True)
ctl.strip.opened = -1e9
ctl.reveal()
app.processEvents()
glows = [i for i in ctl.strip.fx.items if i["kind"] == "reveal"]
assert len(glows) == 1, "the reveal started no glow"


def frame_at(ms):
    now = ctl.strip.clock()
    for d in (ctl._slide, ctl.strip.entrance):
        if d is not None:
            d["t0"] = now - ms
    for i in glows:
        i["t0"] = now - ms
    ctl.slide_tick()
    ctl.strip._fade()
    image = QT.QtGui.QImage(ctl.host.size(), QT.QtGui.QImage.Format_ARGB32)
    image.fill(QT.QtGui.QColor("#3a2a26"))
    p = QT.QtGui.QPainter(image)
    p.setClipRegion(ctl.host.mask())
    p.drawImage(0, 0, ctl.strip.grab().toImage())
    p.end()
    return image


times = [0, 40, 90, 160, 288, 450, 700]
shots = [frame_at(t) for t in times]
pad, label = 10, 26
out = QT.QtGui.QImage(W + 2 * pad, sum(s.height() + label for s in shots) + pad, QT.QtGui.QImage.Format_ARGB32)
out.fill(QT.QtGui.QColor("#141517"))
p = QT.QtGui.QPainter(out)
font = QT.QtGui.QFont("Segoe UI")
font.setPixelSize(16)
p.setFont(font)
y = pad
for t, shot in zip(times, shots):
    p.setPen(QT.QtGui.QColor("#9a9ca3"))
    p.drawText(pad, y + 18, "%d ms" % t)
    y += label
    p.drawImage(pad, y, shot)
    p.setPen(QT.QtGui.QColor("#ffffff"))
    p.drawEllipse(QT.QtCore.QPointF(pad + cursor[0], y + shot.height() - 6), 6, 6)
    y += shot.height()
p.end()
target = os.path.join(HERE, "time_bar_reveal_glow.png")
out.save(target)
print(target)
