"""The Time Bar's own cost while scrubbing, offscreen (2026-10-16, «такое чувство что фпс
программы проседает когда перетаскиваешь ползунок»): the real strip at 150 % on a fake
link with a dense take - a key on every frame of 300, breakdowns, three bookmarks, a
sound - and every scrub step timed: the timeline's paint, the whole mouse-move handler
(Maya's `currentTime` left out: the fake link answers at once), and the 16 ms motion
tick that lights the keys the playhead reaches.

    $env:QT_QPA_PLATFORM='offscreen'; mayapy docs/superpowers/plans/bench_time_bar.py
"""
import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, REPO)
#  TIMEBAR_PLUGIN: another copy of the plugin to measure (an older build, for a before / after)
sys.path.insert(0, os.environ.get("TIMEBAR_PLUGIN") or os.path.join(REPO, "SkeldarAnim"))

import maya_hubqt                                           # noqa: E402
import maya_hubstyle                                        # noqa: E402
from maya_timebar import bar                                # noqa: E402
from tests.test_timebar_bar import FakeLink                 # noqa: E402

QT = maya_hubqt.qt()
app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])
UI = 1.5


class DenseLink(FakeLink):
    def __init__(self):
        super(DenseLink, self).__init__()
        self.s.update(a0=0.0, a1=300.0, p0=0.0, p1=300.0, now=0.0)
        self.k = ([float(f) for f in range(0, 301)], [float(f) + 0.5 for f in range(0, 300, 8)])
        self.marks = [(0.0, 60.0, (0.5, 0.66, 0.9), "Anticipation"),
                      (60.0, 180.0, (0.88, 0.48, 0.21), "Attack"),
                      (180.0, 300.0, (0.56, 0.82, 0.6), "Recovery")]

    def waveform(self, node, start, end):
        out, f = [], float(start)
        while f <= end:
            out.append((f, abs(((f * 7.3) % 1.0) - 0.5) * 2))
            f += 0.25
        return out


def stats(samples):
    samples = sorted(samples)
    n = len(samples)
    return "median %.2f ms, p95 %.2f ms, max %.2f ms (%d)" % (
        samples[n // 2], samples[int(n * 0.95)], samples[-1], n)


def run(label, motion):
    link = DenseLink()
    strip = bar.make(link, UI, maya_hubstyle.TOKENS, motion=motion)
    strip.resize(int(1400 * UI), int(86 * UI))
    strip.show()
    app.processEvents()
    strip.opened = -1e9
    tl = strip.timeline
    t = tl.track()
    # 1 the timeline's paint alone
    paints = []
    for i in range(200):
        link.s["now"] = strip.state["now"] = float(i % 300)
        t0 = time.perf_counter()
        tl.repaint()
        paints.append((time.perf_counter() - t0) * 1000)
    # 2 the mouse-move handler, frame by frame across the take
    E, Qt = QT.QtCore.QEvent, QT.QtCore.Qt
    moves = []

    def send(kind, x, button, buttons):
        local = QT.QtCore.QPointF(x, tl.height() / 2.0)
        event = QT.QtGui.QMouseEvent(kind, local, QT.QtCore.QPointF(tl.mapToGlobal(local.toPoint())),
                                     button, buttons, Qt.NoModifier)
        t0 = time.perf_counter()
        QT.QtWidgets.QApplication.sendEvent(tl, event)
        return (time.perf_counter() - t0) * 1000

    #  a scrub at 60 steps a second: the strip's clock moves 16.7 ms a step, so the
    #  keys the playhead reached fade as they would (about 36 lit at a time)
    fake = [strip.clock()]
    strip.clock = lambda: fake[0]
    send(E.MouseButtonPress, t.x(0), Qt.LeftButton, Qt.LeftButton)
    lit = []
    for f in range(1, 300):
        fake[0] += 1000.0 / 60
        moves.append(send(E.MouseMove, t.x(f), Qt.NoButton, Qt.LeftButton))
        lit.append(sum(1 for t0 in tl.reached.values() if fake[0] - t0 < bar.KEY_FADE_MS))
    send(E.MouseButtonRelease, t.x(299), Qt.LeftButton, Qt.NoButton)
    # 3 the motion tick while keys fade
    ticks = []
    strip.timeline.reach(0, 5)
    for _ in range(120):
        fake[0] += 1000.0 / 60
        for k in range(0, 108, 3):          # 36 keys lit, as a fast scrub leaves them
            tl.reached[float(k)] = fake[0] - (k / 108.0) * bar.KEY_FADE_MS
        t0 = time.perf_counter()
        strip._animate()
        app.processEvents()
        ticks.append((time.perf_counter() - t0) * 1000)
    print("%s\n  timeline paint:  %s\n  scrub step:      %s  (keys lit: up to %d)\n  motion tick:     %s"
          % (label, stats(paints), stats(moves), max(lit or [0]), stats(ticks)))
    strip.deleteLater()
    app.processEvents()


if __name__ == "__main__":
    run("motion on", True)
    run("motion off", False)
