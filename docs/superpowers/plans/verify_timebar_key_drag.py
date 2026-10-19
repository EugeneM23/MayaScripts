"""The Time Bar's key drag end to end, standalone (2026-10-19): the REAL strip,
offscreen, on a real scene, driven by mouse events - press on the highlight (its
body or an edge) or on a key, drag a frame at a time, let go. On every step the
scene's curves are checked against what the block should hold, then the strip's
keys, then that ONE undo puts every curve back.

Why: «ключи просто изчезают при переносе по таймлайну» - the live drag cut a curve's
keys before putting them down again, and Maya deletes a curve a cut empties (trap
210), so a channel whose every key was dragged lost its curve. And a key drag moves
the highlight with the keys: the highlight was its own undo step, so the first
Ctrl+Z put back the highlight and left the keys moved.

    mayapy docs/superpowers/plans/verify_timebar_key_drag.py

The QApplication is made BEFORE maya.standalone: standalone makes a QGuiApplication
of its own, and a widget built on that kills mayapy (0xC0000409, no output at all).
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("VERIFY_REPO") or os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))

from PySide6 import QtCore, QtGui, QtWidgets                  # noqa: E402
APP = QtWidgets.QApplication([])
import maya.standalone                                       # noqa: E402
maya.standalone.initialize()
import maya.cmds as cmds                                     # noqa: E402

from maya_timebar import bar, look, scene                    # noqa: E402

FAILED = []
CHANNELS = ("tx", "ty", "tz", "rx")


def gate(name, ok, detail=""):
    print("%s  %s%s" % ("PASS" if ok else "FAIL", name, ("  - " + detail) if detail else ""))
    if not ok:
        FAILED.append(name)


def curves_of(nodes):
    out = {}
    for n in nodes:
        for a in CHANNELS:
            ts = cmds.keyframe(n + "." + a, q=True, timeChange=True) or []
            vs = cmds.keyframe(n + "." + a, q=True, valueChange=True) or []
            out[n + "." + a] = [(round(t, 4), round(v, 4)) for t, v in zip(ts, vs)]
    return out


def expect(initial, selection, target):
    out = {}
    for plug, keys in initial.items():
        got = dict((t, v) for t, v in keys if not look.inside(t, selection))
        for t, v in keys:
            if look.inside(t, selection):
                got[round(float(look.mapped(t, selection, target)), 4)] = v
        out[plug] = sorted(got.items())
    return out


def differ(now, want):
    return dict((k, (now[k], want[k])) for k in now if now[k] != want[k])


def setup():
    """Two cubes: tx / ty keyed every 5 frames, tz keyed only inside the block
    (every key of that curve is dragged), rx one lone key inside it."""
    cmds.file(new=True, force=True)
    cmds.playbackOptions(edit=True, animationStartTime=-20, animationEndTime=80, minTime=-20, maxTime=60)
    nodes = []
    for i in range(2):
        n = cmds.polyCube(name="drag%d" % i)[0]
        nodes.append(n)
        for t in (0, 5, 10, 15, 20, 25, 30):
            cmds.setKeyframe(n, attribute="tx", time=t, value=t * 0.5 + i)
            cmds.setKeyframe(n, attribute="ty", time=t, value=(t % 10) + i * 2)
        for t in (5, 10, 15):
            cmds.setKeyframe(n, attribute="tz", time=t, value=t + 0.25 + i)
        cmds.setKeyframe(n, attribute="rx", time=10, value=45.0 + i)
    cmds.select(nodes)
    cmds.currentTime(50)                       # off every key: a press on a key drags it
    return nodes


def send(widget, kind, x):
    p = QtCore.QPointF(x, widget.height() / 2.0)
    g = QtCore.QPointF(widget.mapToGlobal(p.toPoint()))
    left, none = QtCore.Qt.LeftButton, QtCore.Qt.NoButton
    event_type, button, buttons = {
        "press": (QtCore.QEvent.MouseButtonPress, left, left),
        "move": (QtCore.QEvent.MouseMove, none, left),
        "release": (QtCore.QEvent.MouseButtonRelease, left, none)}[kind]
    QtWidgets.QApplication.sendEvent(
        widget, QtGui.QMouseEvent(event_type, p, g, button, buttons, QtCore.Qt.NoModifier))
    APP.processEvents()


def grip_x(tl, part, selection):
    """An x the strip reads as `part` of the highlight - its middle such x."""
    t = tl.track()
    lo, hi = t.x(selection[0]) - 30, t.end(selection[1]) + 30
    xs = [lo + i * 0.25 for i in range(int((hi - lo) / 0.25))]
    hits = [x for x in xs if look.highlight_hit(t, x, selection, tl.strip.ui) == part]
    return hits[len(hits) // 2] if hits else None


def drag(name, part, selection, frames):
    nodes = setup()
    initial = curves_of(nodes)
    strip = bar.make(motion=False)
    strip.resize(1600, 110)
    strip.show()
    APP.processEvents()
    tl = strip.timeline
    if part == "key":
        scene.set_highlight(None)
        strip.refresh(keys=True, force=True)
        x = tl.track().x(selection[0]) + tl.track().scale / 2.0       # the key's cell
    else:
        scene.set_highlight(selection)
        strip.refresh(keys=True, force=True)
        gate("%s: the highlight read" % name,
             tuple(strip.state.get("highlight") or ()) == tuple(selection))
        x = grip_x(tl, part, selection)
    scale = tl.track().scale
    send(tl, "press", x)
    bad = []
    step = 1 if frames > 0 else -1
    for i in range(step, frames + step, step):
        send(tl, "move", x + i * scale)
        if tl.preview:
            want = expect(initial, selection, tl.preview)
            now = curves_of(nodes)
            if now != want:
                bad.append((i, tl.preview, differ(now, want)))
    target = tl.preview
    gate("%s: every step of the drag holds every key" % name, not bad,
         str(bad[:1]) if bad else "%d steps" % abs(frames))
    send(tl, "release", x + frames * scale)
    want = expect(initial, selection, target)
    final = curves_of(nodes)
    gate("%s: let go on %s, every curve as it should be" % (name, target), final == want,
         "" if final == want else str(differ(final, want)))
    shown = set(strip.keys) | set(strip.breakdowns)
    gate("%s: the strip shows the keys" % name,
         shown == set(t for keys in want.values() for t, _v in keys), str(sorted(shown)))
    cmds.undo()
    gate("%s: ONE undo puts every curve back" % name, curves_of(nodes) == initial)
    strip.close()
    strip.deleteLater()
    APP.processEvents()


drag("block +7 over a key", "hmove", (5, 15), 7)
drag("block -8 over a key", "hmove", (5, 15), -8)
drag("block +20 past every key", "hmove", (5, 15), 20)
drag("right edge +10 (stretch)", "h1", (5, 15), 10)
drag("left edge +8 (squeeze)", "h0", (5, 15), 8)
drag("left edge -6 (stretch back)", "h0", (5, 15), -6)
drag("the whole take +3", "hmove", (0, 30), 3)
drag("a key pressed and dragged +3, no highlight", "key", (10, 10), 3)

print("\n%d failed: %s" % (len(FAILED), FAILED) if FAILED else "\nALL PASSED")
maya.standalone.uninitialize()
os._exit(1 if FAILED else 0)
