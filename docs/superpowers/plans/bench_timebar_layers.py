"""What the Time Bar's layer panel costs (2026-10-18): a column of 12 animation layers
with the lanes out (40 keys each), at 150 %, offscreen. Median and p95 of 200 runs.
Budget (docs/interface-motion.md section 5): a hover step and on_time under 1 ms
median; the still picture not drawn again during the sweep. Run:

    $env:QT_QPA_PLATFORM='offscreen'; mayapy docs/superpowers/plans/bench_timebar_layers.py
"""
import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))

import maya_hubqt                                           # noqa: E402
import maya_hubstyle                                        # noqa: E402
from maya_timebar import layerlook as L, layerpanel, look   # noqa: E402

QT = maya_hubqt.qt()
app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])
UI = 1.5
N = 200


class Link(object):
    def __init__(self):
        self.opts = {layerpanel.LANES_VAR: 1}
        self.anim = [{"name": "L%d" % i, "label": "Layer_%d" % i, "mode": "add" if i % 2 else "ovr",
                      "weight": 0.5 + (i % 5) / 10.0, "weight_keyed": False, "mute": i == 3,
                      "solo": False, "lock": False, "active": i == 0, "base": False} for i in range(11)]
        self.anim.append({"name": "Base", "label": "BaseAnimation", "mode": "base", "weight": 1.0,
                          "weight_keyed": False, "mute": False, "solo": False, "lock": False,
                          "active": False, "base": True})

    def anim_layers(self):
        return [dict(r) for r in self.anim]

    def display_layers(self):
        return []

    def keys_by_layer(self, names):
        return {n: [i * 2.0 for i in range(40)] for n in names}

    def option(self, name, default):
        return self.opts.get(name, default)

    def set_option(self, name, value):
        self.opts[name] = value

    def __getattr__(self, name):
        return lambda *a: (True, "")


class Strip(object):
    ui = UI

    def strip_rect(self):
        return (0, 900, 1500, int(84 * UI))

    def timeline_rect(self):
        return (6, 940, 1000, 40)

    def top_room(self):
        return 880

    def track(self):
        return look.Track(16, 990, 0, 95, cells=True)

    def now(self):
        return 30.0


panel = layerpanel.Panel(Strip(), Link(), UI, maya_hubstyle.TOKENS, False)
panel.column.move(4000, 0)
panel.lanes.move(4000, 0)
panel.open((1380, 940))
app.processEvents()
col, lanes = panel.column, panel.lanes
assert lanes.isVisible()


def timed(fn):
    out = []
    fn()
    for _ in range(N):
        t = time.perf_counter()
        fn()
        out.append((time.perf_counter() - t) * 1000.0)
    out.sort()
    return out[len(out) // 2], out[int(len(out) * 0.95)]


def report(name, res):
    print("%-34s median %.3f ms   p95 %.3f ms" % (name, res[0], res[1]))
    return res


def repaint_col():
    col.invalidate()
    col.repaint()


def repaint_lanes():
    lanes.invalidate()
    lanes.repaint()


report("column, full repaint (still too)", timed(repaint_col))
report("lanes, full repaint (still too)", timed(repaint_lanes))
col.repaint()
lanes.repaint()
base = col.rebuilds

lay = col.layout_()
spots = []
for i in range(len(lay.rows)):
    r = lay.row_at(i, panel.scroll)
    spots.append((r[0] + 40, r[1] + r[3] / 2.0))
for _name, r in lay.foot:
    spots.append((r[0] + r[2] / 2.0, r[1] + r[3] / 2.0))
Qt = QT.QtCore.Qt


def move(x, y):
    p = QT.QtCore.QPointF(x, y)
    ev = QT.QtGui.QMouseEvent(QT.QtCore.QEvent.MouseMove, p, QT.QtCore.QPointF(col.mapToGlobal(p.toPoint())),
                              Qt.NoButton, Qt.NoButton, Qt.NoModifier)
    QT.QtWidgets.QApplication.sendEvent(col, ev)
    col.repaint()


state = [0]


def sweep_step():
    x, y = spots[state[0] % len(spots)]
    state[0] += 1
    move(x, y)


report("hover step (move + repaint)", timed(sweep_step))
print("picture rebuilds during the sweep: %d" % (col.rebuilds - base))
report("Panel.on_time() (lanes playhead)", timed(panel.on_time))
panel.destroy()
