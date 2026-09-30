"""Live proof of the Graph Overlay - phase by phase, in a disposable Maya or one
the animator lends for it (2026-09-30: theirs on port 7001, an untitled scene).

Never in a scene of theirs: `setup` opens a new one. One send per
phase, because the Qt event loop has to turn between them (the follow
timer aligns the ghost, `frameSwapped` keys the glass; trap 68). The
runner defines PHASE and calls `main(PHASE)`:

    setup  placed  check_time  frame_view  click  check_click  channel
    check_channel  toolbar  check_toolbar  alt  cost
    look  hub  leave  gone

State between phases lives in `sys._skeldar_verify_go`. Maya being the
active application is SIMULATED (`viewport.maya_active` answers True for
the run): a Maya brought to the front would sit over the animator's work,
and the rule itself is unit-tested (`let_through`).

`SKELDAR_VERIFY_PLUGIN` names the plugin folder to prove - the INSTALLED
copy after an install, so the run proves what the animator will press;
the repo's `SkeldarAnim` otherwise. In a Maya whose window is up (the
animator's own), the window is never moved or resized.
"""

import os
import sys
import time

REPO = os.environ.get("SKELDAR_VERIFY_PLUGIN",
                      "C:/!!!Work/MayaScripts/SkeldarAnim").replace("\\", "/")
ASSET = REPO + "/assets/Manny_Skeleton.ma"
OUT_DIR = os.environ.get("SKELDAR_VERIFY_OUT",
                         os.path.join(os.environ.get("TEMP", "."),
                                      "verify_graphoverlay"))

if REPO in sys.path:
    sys.path.remove(REPO)
sys.path.insert(0, REPO)

import maya.cmds as cmds

S = sys.__dict__.setdefault("_skeldar_verify_go", {"gates": []})


def gate(number, ok, text):
    S["gates"].append((number, bool(ok)))
    print("gate %2d %s  %s" % (number, "PASS" if ok else "FAIL", text))


def summary():
    failed = [n for n, ok in S["gates"] if not ok]
    print("%d of %d gates failed so far%s" % (
        len(failed), len(S["gates"]),
        (": " + ", ".join(str(n) for n in failed)) if failed else ""))


def _purge():
    """Our package only. Purging the hub's modules too would split the
    marks between two `maya_hubstyle` objects in a Maya whose hub is open
    (trap 84's shape) - an install already gave it fresh ones."""
    for name in list(sys.modules):
        if name.split(".")[0] == "maya_graphoverlay":
            del sys.modules[name]


def _pump(n=10):
    from PySide6 import QtWidgets
    app = QtWidgets.QApplication.instance()
    for _ in range(n):
        app.processEvents()


def _mode():
    from maya_graphoverlay import mode
    return mode


def _vp_rect():
    from maya_graphoverlay import viewport
    return viewport.gl_rect(_mode()._STATE.model_panel)


def _marker(image):
    """The yellow time marker's columns on the ruler row, or None."""
    for y in (6, 8, 10, 12):
        xs = [x for x in range(image.width())
              if (lambda c: c.red() > 200 and c.green() > 200
                  and c.blue() < 90 and c.alpha() > 200)(image.pixelColor(x, y))]
        if xs:
            return (min(xs), max(xs))
    return None


def _orange_keys(image):
    """Centres of the orange key diamonds: (x, y) per cluster, top first."""
    import numpy as np
    w, h = image.width(), image.height()
    arr = np.frombuffer(image.constBits(), np.uint8).reshape(
        h, image.bytesPerLine() // 4, 4)[:, :w]
    b, g, r, a = arr[..., 0], arr[..., 1], arr[..., 2], arr[..., 3]
    mask = (r > 220) & (g > 110) & (g < 210) & (b < 80) & (a > 200)
    mask[:30, :] = False                               # the ruler band
    ys, xs = np.nonzero(mask)
    clusters = []
    for x, y in zip(xs.tolist(), ys.tolist()):
        for c in clusters:
            if abs(c[0] - x) <= 6 and abs(c[1] - y) <= 6:
                c[2].append((x, y))
                break
        else:
            clusters.append([x, y, [(x, y)]])
    centres = [(sum(p[0] for p in c[2]) / len(c[2]),
                sum(p[1] for p in c[2]) / len(c[2])) for c in clusters]
    return sorted(centres, key=lambda p: p[1])


def _topmost(hwnd, on):
    import ctypes
    from ctypes import wintypes as wt
    ctypes.windll.user32.SetWindowPos(
        wt.HWND(hwnd), wt.HWND(-1 if on else -2), 0, 0, 0, 0,
        0x0001 | 0x0002 | 0x0010)


# ---------------------------------------------------------------- the phases

def setup():
    S.clear()
    S["gates"] = []
    _purge()
    from maya import OpenMayaUI as omui
    from PySide6 import QtWidgets
    import shiboken6
    app = QtWidgets.QApplication.instance()
    main_win = shiboken6.wrapInstance(int(omui.MQtUtil.mainWindow()),
                                      QtWidgets.QWidget)
    if not main_win.isVisible():            # a fresh MAYA_APP_DIR: trap 105
        for w in app.topLevelWidgets():
            if w.isVisible() and (w.objectName() == "MayaAppHomeWindow"
                                  or "WebEngine" in type(w).__name__):
                w.hide()
        main_win.setVisible(True)
        main_win.setGeometry(120, 120, 1500, 950)
        _pump()
    S["hub_open"] = bool(cmds.workspaceControl("skeldarAnimHub", exists=True)
                         and cmds.workspaceControl("skeldarAnimHub",
                                                   query=True, visible=True))
    cmds.file(new=True, force=True)
    cmds.file(ASSET, i=True, ignoreVersion=True)
    cube = cmds.polyCube(name="probeCube")[0]
    for t, v in ((1, 0), (12, 6), (24, -4)):
        cmds.setKeyframe(cube, attribute="translateX", time=t, value=v)
        cmds.setKeyframe(cube, attribute="translateY", time=t,
                         value=v * 0.5 + 2)
        cmds.setKeyframe(cube, attribute="rotateZ", time=t, value=v * 10)
    cmds.playbackOptions(minTime=1, maxTime=24,
                         animationStartTime=1, animationEndTime=24)
    cmds.currentTime(1)
    cmds.select(cube)
    try:
        cmds.setFocus("modelPanel4")
    except Exception:                                         # noqa: BLE001
        pass
    S["background"] = cmds.displayRGBColor("modernGraphEditorBackground",
                                           query=True, alpha=True)
    import maya_graphoverlay
    from maya_graphoverlay import viewport
    if _mode().is_on():                       # one state per session
        print("already on - off first:", _mode().disable())
    from maya_graphoverlay import ghost
    S["ge_home"] = ghost.home_of(ghost.BORROWED)
    S["ge_stacked"] = cmds.animCurveEditor(ghost.BORROWED + "GraphEd",
                                           query=True, stackedCurves=True)
    print("graphEditor1 lives in", S["ge_home"], "stacked", S["ge_stacked"])
    S["maya_active"] = viewport.maya_active
    viewport.maya_active = lambda: True               # simulated, see top
    print("toggle:", maya_graphoverlay.toggle())


def placed():
    from maya_graphoverlay import winstyle
    mode = _mode()
    st = mode._STATE
    ghost, glass = st.ghost, st.glass
    vp = _vp_rect()
    print("viewport", vp, "canvas", ghost.canvas_rect(),
          "glass", (glass.x(), glass.y(), glass.width(), glass.height()))
    gate(1, winstyle.layered_alpha(ghost.hwnd()) == 1,
         "the ghost's layered alpha is 1 (%s)"
         % winstyle.layered_alpha(ghost.hwnd()))
    canvas = ghost.canvas_rect()
    inside = (canvas is not None and canvas[0] >= vp[0] and canvas[1] >= vp[1]
              and canvas[0] + canvas[2] <= vp[0] + vp[2]
              and canvas[1] + canvas[3] <= vp[1] + vp[3])
    gate(2, ghost.host_rect() == vp and inside,
         "the whole Graph Editor lies on the viewport, its curve area "
         "inside (%s)" % (canvas,))
    gate(3, (glass.x(), glass.y(), glass.width(), glass.height()) == vp,
         "the glass lies on it too")
    gate(4, winstyle.is_click_through(int(glass.winId())),
         "the glass is click-through")
    gate(5, st.frames >= 1, "frames keyed: %d, background tones %s"
         % (st.frames, st.keys))
    image = glass.frame()
    import numpy as np
    ok = image is not None and (image.width(), image.height()) == canvas[2:]
    if ok:
        arr = np.frombuffer(image.constBits(), np.uint8).reshape(
            image.height(), image.bytesPerLine() // 4, 4)
        alpha = arr[..., 3]
        clear, solid = (alpha == 0).mean(), int((alpha == 255).sum())
        ok = clear > 0.5 and solid > 50
        print("glass alpha: %.1f%% clear, %d opaque pixels" % (clear * 100,
                                                               solid))
        image.save(os.path.join(OUT_DIR, "glass_placed.png"))
    gate(6, ok, "the glass shows the graph with its background out")
    from maya_graphoverlay import geometry
    picture = glass.picture()
    picture.save(os.path.join(OUT_DIR, "glass_picture.png"))
    parr = np.frombuffer(picture.constBits(), np.uint8).reshape(
        picture.height(), picture.bytesPerLine() // 4, 4)[..., 3]
    ox, oy = ghost.canvas_offset()
    bands = geometry.chrome_bands((picture.width(), picture.height()),
                                  (ox, oy, canvas[2], canvas[3]))
    solid = [float((parr[y:y + h, x:x + w] == 255).mean())
             for x, y, w, h in bands]
    print("chrome bands", bands, "opaque", ["%.3f" % s for s in solid],
          "grabs", st.chrome_grabs, "watched", len(st.watched))
    gate(21, bands and min(solid) > 0.99 and st.chrome_grabs >= 1,
         "the menus, the toolbar and the channel list stand opaque on the "
         "glass")
    S["frames"] = st.frames
    S["marker"] = _marker(image) if image is not None else None
    print("marker at frame 1:", S["marker"])
    cmds.currentTime(12)


def check_time():
    mode = _mode()
    image = mode._STATE.glass.frame()
    now = _marker(image)
    print("marker at frame 12:", now, "frames", mode._STATE.frames)
    gate(7, now is not None and S.get("marker") is not None
         and now[0] > S["marker"][0] + 20
         and mode._STATE.frames > S["frames"],
         "a time change reached the glass (the marker moved)")


def _keys():
    return dict((attr, list(zip(
        cmds.keyframe("probeCube." + attr, query=True, timeChange=True),
        cmds.keyframe("probeCube." + attr, query=True, valueChange=True))))
        for attr in ("translateX", "translateY", "rotateZ"))


def _post_click(hwnd, x, y):
    """A left click the way Windows delivers one, at client (x, y): posted,
    so Qt meets it in its own message loop after this send returns. Maya's
    PySide6 ships no QtTest, and the real cursor is never moved.

    Measured 2026-09-30: the Graph Editor takes the press at the posted
    pixel but reads the REAL cursor while the button is down, so it drags
    the grabbed key towards wherever the animator's mouse happens to be
    (60 -> 80.46 on the first run). A posted click proves WHICH key the
    invisible graph grabbed - the one under the pixel - not a clean click;
    the phase after it puts the value back."""
    import ctypes
    from ctypes import wintypes as wt
    post = ctypes.windll.user32.PostMessageW
    post.argtypes = [wt.HWND, ctypes.c_uint, wt.WPARAM, wt.LPARAM]
    where = (int(y) << 16) | (int(x) & 0xFFFF)
    for message, buttons in ((0x0200, 0), (0x0201, 0x0001), (0x0202, 0)):
        post(wt.HWND(hwnd), message, buttons, where)   # MOVE, LDOWN, LUP


def frame_view():
    """A known view and no key selected, one send before the click: the
    graph redraws in the event loop, not inside this send."""
    mode = _mode()
    editor = mode._STATE.ghost.panel + "GraphEd"
    try:
        cmds.selectKey(clear=True)
    except Exception:                                         # noqa: BLE001
        pass
    cmds.animView(editor, startTime=-1, endTime=27, minValue=-55,
                  maxValue=75)
    print("view framed on", editor)


def click():
    mode = _mode()
    st = mode._STATE
    st.pending = False
    mode._update()
    st.glass.frame().save(os.path.join(OUT_DIR, "glass_click.png"))
    keys = _orange_keys(st.glass.frame())
    print("key diamonds (top first):", [(round(x), round(y)) for x, y in keys])
    if not keys:
        gate(8, False, "no key found in the glass to click")
        return
    x, y = keys[0]                                     # rotateZ's 60 at 12
    S["clicked"] = (x, y)
    S["keys_before"] = _keys()
    _post_click(int(st.ghost.canvas().winId()), round(x), round(y))


def check_click():
    before, after = S.get("keys_before", {}), _keys()
    moved = [(attr, b, a) for attr in after
             for b, a in zip(before.get(attr, []), after[attr]) if b != a]
    selected = cmds.keyframe("probeCube", query=True, selected=True,
                             name=True) or []
    print("keys that changed:", moved, "selected curves:", selected)
    grabbed_rz = (selected == ["probeCube_rotateZ"]
                  or [m[0] for m in moved] == ["rotateZ"])
    others_still = all(m[0] == "rotateZ" for m in moved)
    gate(8, grabbed_rz and others_still,
         "the INVISIBLE graph took the press on the key under the pixel "
         "(rotateZ at 12) and on no other curve")
    for attr, keys in before.items():                  # put every key back
        for index, (t, v) in enumerate(keys):
            cmds.keyframe("probeCube." + attr, edit=True, index=(index, index),
                          timeChange=t, valueChange=v, absolute=True)
    print("put back:", _keys() == before)


def alt():
    from maya_graphoverlay import winstyle
    mode = _mode()
    st = mode._STATE
    ghost = st.ghost
    canvas_hwnd = int(ghost.canvas().winId())
    cx, cy, cw, ch = ghost.canvas_rect()
    centre = (cx + cw // 2, cy + ch // 2)
    st.active = True
    mode._poll_alt(alt=True)
    gate(9, winstyle.is_click_through(ghost.hwnd()),
         "alt held: the ghost lets the mouse through")
    _topmost(ghost.hwnd(), True)                       # it is invisible
    hit = winstyle.window_at(*centre)
    _topmost(ghost.hwnd(), False)
    gate(10, hit not in (canvas_hwnd, ghost.hwnd()),
         "a click there reaches what is below (%s)" % hit)
    mode._poll_alt(alt=False)
    gate(11, not winstyle.is_click_through(ghost.hwnd()),
         "alt released: the ghost takes clicks again")
    _topmost(ghost.hwnd(), True)
    hit = winstyle.window_at(*centre)
    _topmost(ghost.hwnd(), False)
    gate(12, hit == canvas_hwnd, "a click there reaches the graph (%s)" % hit)


def _host_child(name):
    """A widget of OUR Graph Editor by object name (the animator's own
    graphEditor1 carries the same toolbar names)."""
    from PySide6 import QtWidgets
    host = _mode()._STATE.ghost.host
    for widget in host.findChildren(QtWidgets.QWidget):
        try:
            if widget.objectName() == name and widget.isVisible():
                return widget
        except RuntimeError:
            continue
    return None


def _post_to_host(widget, x=None, y=None):
    from PySide6 import QtCore
    host = _mode()._STATE.ghost.host
    local = QtCore.QPoint(widget.width() // 2 if x is None else x,
                          widget.height() // 2 if y is None else y)
    at = widget.mapTo(host, local)
    _post_click(int(host.winId()), at.x(), at.y())
    return (at.x(), at.y())


def _outliner_selection():
    mode = _mode()
    outliner = mode._STATE.ghost.panel + "OutlineEd"
    connection = cmds.outlinerEditor(outliner, query=True,
                                     selectionConnection=True)
    return cmds.selectionConnection(connection, query=True, object=True) or []


def channel():
    """Click the "Rotate Z" row of OUR channel list - found by its blue text
    in the glass's picture of the chrome - posted to the invisible host."""
    import numpy as np
    mode = _mode()
    st = mode._STATE
    mode._update_chrome()
    picture = st.glass.picture()
    ox, oy = st.ghost.canvas_offset()
    arr = np.frombuffer(picture.constBits(), np.uint8).reshape(
        picture.height(), picture.bytesPerLine() // 4, 4)[:, :ox]
    b, g, r = arr[..., 0].astype(int), arr[..., 1].astype(int), arr[..., 2].astype(int)
    blue = (b > 180) & (r < 140) & (b - r > 80)
    ys, xs = np.nonzero(blue)
    S["channels_before"] = _outliner_selection()
    print("selected channels before:", S["channels_before"])
    if not len(xs):
        gate(22, False, "no blue 'Rotate Z' text found in the channel list")
        return
    x, y = int(np.median(xs)), int(np.median(ys))
    print("Rotate Z text around", (x, y))
    import ctypes
    _post_click(int(st.ghost.host.winId()), x, y)


def check_channel():
    now = _outliner_selection()
    print("selected channels after:", now)
    gate(22, any(item.endswith("rotateZ") for item in now)
         and not any(item.endswith(("translateX", "translateY"))
                     for item in now),
         "a click on the channel list's Rotate Z selected that channel alone")


def toolbar():
    mode = _mode()
    editor = mode._STATE.ghost.panel + "GraphEd"
    S["stacked_before"] = cmds.animCurveEditor(editor, query=True,
                                               stackedCurves=True)
    button = _host_child("graphEditorStackedViewIconButton")
    if button is None:
        gate(23, False, "no Stacked View button in our toolbar")
        return
    print("stacked before:", S["stacked_before"], "button at",
          _post_to_host(button))


def check_toolbar():
    mode = _mode()
    editor = mode._STATE.ghost.panel + "GraphEd"
    now = cmds.animCurveEditor(editor, query=True, stackedCurves=True)
    theirs = [p for p in (cmds.getPanel(scriptType="graphEditor") or [])
              if p != mode._STATE.ghost.panel]
    others = [cmds.animCurveEditor(p + "GraphEd", query=True,
                                   stackedCurves=True)
              for p in theirs if cmds.animCurveEditor(p + "GraphEd",
                                                      exists=True)]
    print("stacked after:", now, "the animator's own Graph Editors:", others)
    gate(23, now != S.get("stacked_before"),
         "a click on the toolbar's Stacked View switched OUR Graph Editor")
    cmds.animCurveEditor(editor, edit=True,
                         stackedCurves=bool(S.get("stacked_before")))


def cost():
    """At the viewport's own size - never a window moved to make it bigger."""
    mode = _mode()
    st = mode._STATE
    runs, grabs = [], []
    for _ in range(10):
        st.pending = False
        started = time.perf_counter()
        mode._update()
        runs.append((time.perf_counter() - started) * 1000)
        started = time.perf_counter()
        st.ghost.grab()
        grabs.append((time.perf_counter() - started) * 1000)
    size = st.glass.frame().width(), st.glass.frame().height()
    mean = sum(runs) / len(runs)
    print("one frame at %dx%d: %.1f ms (min %.1f, max %.1f); the grab "
          "alone %.1f ms" % (size + (mean, min(runs), max(runs),
                                     sum(grabs) / len(grabs))))
    gate(13, mean < 40.0, "grab + key + show under 40 ms (%.1f)" % mean)


def look():
    from PySide6 import QtGui
    mode = _mode()
    st = mode._STATE
    st.pending = False
    mode._update()
    image = st.glass.frame()
    path = os.path.join(OUT_DIR, "viewport_frame")
    cmds.playblast(frame=[cmds.currentTime(query=True)], format="image",
                   compression="png", completeFilename=path + ".png",
                   viewer=False, showOrnaments=False, percent=100,
                   widthHeight=(image.width(), image.height()),
                   offScreen=True, forceOverwrite=True, clearCache=True)
    back = QtGui.QImage(path + ".png").convertToFormat(
        QtGui.QImage.Format_ARGB32_Premultiplied)
    painter = QtGui.QPainter(back)
    painter.drawImage(0, 0, image)
    painter.end()
    back.save(os.path.join(OUT_DIR, "graph_overlay_look.png"))
    image.save(os.path.join(OUT_DIR, "glass_full.png"))
    print("saved", os.path.join(OUT_DIR, "graph_overlay_look.png"))
    import numpy as np
    alpha = np.frombuffer(image.constBits(), np.uint8).reshape(
        image.height(), image.bytesPerLine() // 4, 4)[..., 3]
    clear = float((alpha == 0).mean())
    gate(20, len(st.keys) >= 2 and clear > 0.85,
         "both background tones out (in range and out of it): %.1f%% of "
         "the frame clear, tones %s" % (clear * 100, st.keys))


def hub():
    import maya_hub
    mode = _mode()
    maya_hub.show(mode.HUB_SECTION)
    _pump()
    exists = cmds.control(mode.BUTTON, exists=True)
    label = cmds.button(mode.BUTTON, query=True, label=True) if exists else ""
    gate(14, exists and label == "Graph Overlay: ON",
         "the hub section is built and says ON (%r)" % label)


def leave():
    import maya_graphoverlay
    mode = _mode()
    S["panel"] = mode._STATE.ghost.panel
    print("toggle:", maya_graphoverlay.toggle())
    gate(15, not mode.is_on() and not mode._STATE.timers,
         "off: no state, no timers")
    from maya_graphoverlay import ghost
    if S["panel"] == ghost.BORROWED:
        home = ghost.home_of(ghost.BORROWED)
        gate(16, home == S.get("ge_home") and not ghost.in_host(S["panel"])
             and cmds.animCurveEditor(ghost.BORROWED + "GraphEd", query=True,
                                      stackedCurves=True) == S.get("ge_stacked"),
             "Maya's graphEditor1 is back where it lived (%s), its view "
             "mode as it was" % home)
    else:
        gate(16, not cmds.scriptedPanel(S["panel"], exists=True),
             "our Graph Editor panel is gone")
    label = cmds.button(mode.BUTTON, query=True, label=True) \
        if cmds.control(mode.BUTTON, exists=True) else ""
    gate(17, label == "Graph Overlay: OFF", "the button says OFF (%r)" % label)


def gone():
    from PySide6 import QtWidgets
    from maya_graphoverlay import ghost, glass, viewport
    names = [w.objectName() for w in QtWidgets.QApplication.topLevelWidgets()]
    gate(18, ghost.HOST not in names and glass.NAME not in names,
         "no host and no glass left among the top-level windows")
    after = cmds.displayRGBColor("modernGraphEditorBackground", query=True,
                                 alpha=True)
    gate(19, after == S.get("background"),
         "the Graph Editor's background preference untouched (%s)" % after)
    if "maya_active" in S:
        viewport.maya_active = S.pop("maya_active")
    if not S.get("hub_open") and cmds.workspaceControl("skeldarAnimHub",
                                                       exists=True):
        cmds.workspaceControl("skeldarAnimHub", edit=True, close=True)
        print("the hub was closed before the run - closed again")


PHASES = {"setup": setup, "placed": placed, "check_time": check_time,
          "frame_view": frame_view, "channel": channel,
          "check_channel": check_channel, "toolbar": toolbar,
          "check_toolbar": check_toolbar,
          "click": click, "check_click": check_click, "alt": alt,
          "cost": cost, "look": look, "hub": hub, "leave": leave,
          "gone": gone, "time": lambda: None}


def main(phase):
    os.makedirs(OUT_DIR, exist_ok=True)
    print("phase", phase)
    PHASES[phase]()
    summary()
