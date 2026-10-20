"""Steel keys (2026-10-20): a key set on the Time Bar, glowing hot and cooling into steel,
drawn offscreen at 150 % into time_bar_steel.png - a crop round the key at nine moments;
under it a highlight of frames 16..26 keyed at once: one plate cooling (time_bar_steel_plate.png).
No Maya. Run:

    $env:QT_QPA_PLATFORM='offscreen'; mayapy docs/superpowers/plans/render_time_bar_steel.py
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
strip.set_steel(True)
start = strip.clock()
strip.clock = (lambda: start)
link.k = ([0.0, 6.0, 12.0, 20.0, 30.0, 40.0], [])
strip.keys_edited = True
strip.refresh(keys=True)

tl = strip.timeline
t = tl.track()
cx = tl.mapTo(strip, QT.QtCore.QPoint(int(t.x(20.0) + t.scale / 2), 0)).x()
w, h = int(150 * UI), strip.height()
moments = (0, 80, 200, 400, 650, 900, 1200, 1500, 1900)
shots = []
for ms in moments:
    strip.clock = (lambda m=ms: start + m)
    shots.append((ms, strip.grab(QT.QtCore.QRect(cx - w // 2, 0, w, h)).toImage()))

pad = 10
out = QT.QtGui.QImage(len(shots) * (w + pad) + pad, h + 2 * pad + 22, QT.QtGui.QImage.Format_ARGB32)
out.fill(QT.QtGui.QColor("#141517"))
p = QT.QtGui.QPainter(out)
p.setPen(QT.QtGui.QColor("#c8cbd2"))
for i, (ms, img) in enumerate(shots):
    x = pad + i * (w + pad)
    p.drawImage(x, pad, img)
    p.drawText(QT.QtCore.QRect(x, pad + h + 2, w, 20), QT.QtCore.Qt.AlignCenter, "%d ms" % ms)
p.end()
target = os.path.join(HERE, "time_bar_steel.png")
out.save(target)
print("saved", target, look.cooling(0), look.cooling(look.COOL_MS))


# a highlight keyed at once: one plate (2026-10-20)
link.k = ([0.0, 6.0, 12.0] + [float(f) for f in range(16, 27)] + [30.0, 40.0], [])
strip.clock = (lambda: start)
strip.keys_edited = True
strip.mark_set(16, 26)
strip.refresh(keys=True)
t = tl.track()
cx = tl.mapTo(strip, QT.QtCore.QPoint(int(t.x(21.0) + t.scale / 2), 0)).x()
w = int(260 * UI)
shots = []
for ms in moments:
    strip.clock = (lambda m=ms: start + m)
    shots.append((ms, strip.grab(QT.QtCore.QRect(cx - w // 2, 0, w, h)).toImage()))
out = QT.QtGui.QImage(len(shots) * (w + pad) + pad, h + 2 * pad + 22, QT.QtGui.QImage.Format_ARGB32)
out.fill(QT.QtGui.QColor("#141517"))
p = QT.QtGui.QPainter(out)
p.setPen(QT.QtGui.QColor("#c8cbd2"))
for i, (ms, img) in enumerate(shots):
    x = pad + i * (w + pad)
    p.drawImage(x, pad, img)
    p.drawText(QT.QtCore.QRect(x, pad + h + 2, w, 20), QT.QtCore.Qt.AlignCenter, "%d ms" % ms)
p.end()
target = os.path.join(HERE, "time_bar_steel_plate.png")
out.save(target)
print("saved", target)
