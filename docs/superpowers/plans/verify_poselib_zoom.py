"""verify_poselib_zoom.py - the Pose Library's card growing twice its size under the mouse, in a
DISPOSABLE GUI Maya (2026-10-03).

The animator: «при наведении на карточку позы в библиотеке поз наша карточка увеличивалась в
двое». Spec: docs/superpowers/specs/2026-10-03-pose-card-hover-zoom-design.md

Never the animator's Maya: `guard` refuses a Maya whose prefs are Documents/maya or that has port
7001 open. Sent one phase at a time, as ONE line to the disposable Maya's command port:

    exec(open(r"<this file>", encoding="utf-8").read(),
         {"__name__": "__main__", "__file__": r"<this file>", "PHASE": "<phase>",
          "OUT": r"<a fresh output file>", "PURGE": <bool>})

The file writes everything into OUT, ends with `== END <phase> ==`, guards against the port
running the line twice with an `OUT.ran` marker (bridge notes 5 and 8), and puts the plugin beside
it FIRST on sys.path (PURGE drops our modules first - bridge note 9).

Phases (each re-finds every widget by name - trap 148; Qt mouse events sent to the canvas, no OS
cursor - the animator's desktop is theirs):

    open     a library of 24 cards with 640 px thumbnails in the scratch prefs, the window
             opened floating at 1000 x 640 logical; the hub closed; Interface animations on
    grow     a move onto a card in the middle of the grid: the card grows to 2x through the
             timer in about ZOOM_IN_MS, monotonically, and the timer stops; the grown tile
             holds the card's own and stands inside the viewport; one frame's repaint timed
    photo    DWM's copy of the window (never QWidget.grab of Maya widgets - trap 134) into
             poselib_zoom.png; where the grown card covers a neighbour the window shows the grown
             card's colour, a card far from it its own
    press    the mouse onto the part of a neighbour the grown card covers grows the neighbour
             (which card grows is read off the grid's places alone), a click there picks it,
             a gap between places grows nothing
    move_on  onto a neighbour's uncovered part: it grows while the first shrinks, drawn on top
    edges    the top-left card grows flush with the viewport's corner, the last card of the
             visible bottom row inside the viewport
    scroll   the scroll moved with a card grown: its tile follows into the new view
    leave    the mouse off the canvas: the card shrinks back in about ZOOM_OUT_MS, the timer stops
    off      Interface animations off: grown and shrunk at once, no timer; put back
    thumb    a cube in the viewport and capture.thumbnail: a 640 x 640 JPG
    close    the window closed, Maya minimised
"""

import io
import os
import sys
import time
import traceback

_OUT = globals().get("OUT")
_PHASE = globals().get("PHASE", "")
_MARK = (_OUT or "") + ".ran"
_HERE = os.path.dirname(os.path.abspath(globals().get("__file__") or "."))
_PLUGIN = os.path.normpath(os.path.join(_HERE, "..", "..", "..", "SkeldarAnim")).replace("\\", "/")

RESULTS = []
CARDS = 24
HOVERED = 9                 # the second row, near the middle, at the default card size
PICTURES = os.path.join(_HERE).replace("\\", "/")


def say(*parts):
    print(" ".join(str(p) for p in parts))


def gate(name, ok, value=""):
    RESULTS.append(bool(ok))
    say("%s %s %s" % ("PASS" if ok else "FAIL", name, value))
    return bool(ok)


def qt():
    import maya_hubqt
    return maya_hubqt.qt()


def cmds():
    import maya.cmds as c
    return c


def settle(times=3):
    q = qt()
    for _ in range(times):
        q.QtWidgets.QApplication.processEvents()


def pump(ms):
    """The event loop turned for `ms` of real time (the timers fire in it)."""
    q = qt()
    end = time.time() + ms / 1000.0
    while time.time() < end:
        q.QtWidgets.QApplication.processEvents()
        time.sleep(0.002)


def guard():
    c = cmds()
    app = c.internalVar(userAppDir=True).replace("\\", "/")
    if "Documents/maya" in app or c.commandPort(":7001", query=True):
        raise RuntimeError("this looks like the animator's Maya (%s) - refused" % app)


def library_root():
    app = cmds().internalVar(userAppDir=True).replace("\\", "/")
    return app.rstrip("/") + "/poselib_zoom_library"


def window():
    import maya_hubqt
    from maya_poselib import window as w
    host = maya_hubqt.find(w.CONTROL)
    if host is None:
        return None
    for child in host.findChildren(qt().QtWidgets.QWidget):
        if child.objectName() == w.ROOT:
            return child
    return None


def canvas():
    from maya_poselib import cardgrid
    win = window()
    if win is None:
        return None
    for child in win.findChildren(qt().QtWidgets.QWidget):
        if child.objectName() == cardgrid.CANVAS_NAME:
            return child
    return None


def top_level():
    import maya_hubqt
    from maya_poselib import window as w
    host = maya_hubqt.find(w.CONTROL)
    top = host.window() if host is not None else None
    if top is not None and top.objectName() == "MayaWindow":
        return None
    return top


def maya_window():
    for top in qt().QtWidgets.QApplication.topLevelWidgets():
        if top.objectName() == "MayaWindow":
            return top
    return None


def mouse(widget, kind, local, button=None, buttons=None):
    q = qt()
    QtCore, QtGui = q.QtCore, q.QtGui
    Qt = QtCore.Qt
    types = {"move": QtCore.QEvent.MouseMove, "press": QtCore.QEvent.MouseButtonPress,
             "release": QtCore.QEvent.MouseButtonRelease}
    button = Qt.NoButton if button is None else button
    buttons = (button if kind == "press" else Qt.NoButton) if buttons is None else buttons
    event = QtGui.QMouseEvent(types[kind], QtCore.QPointF(local),
                              QtCore.QPointF(widget.mapToGlobal(local)), button, buttons,
                              Qt.NoModifier)
    q.QtWidgets.QApplication.sendEvent(widget, event)


def centre(cv, index):
    x, y, w, h = cv.rects()[index]
    return qt().QtCore.QPoint(x + w // 2, y + h // 2)


def inside(tile, view, slack=0.5):
    x, y, w, h = tile
    vx, vy, vw, vh = view
    return (vx - slack <= x and y >= vy - slack and x + w <= vx + vw + slack
            and y + h <= vy + vh + slack)


def holds(outer, inner, slack=0.5):
    ox, oy, ow, oh = outer
    ix, iy, iw, ih = inner
    return (ox - slack <= ix and oy - slack <= iy and ix + iw <= ox + ow + slack
            and iy + ih <= oy + oh + slack)


def hue_of(index):
    return int(round(index * 360.0 / CARDS)) % 360


def animations(on):
    import maya_hubmotion
    maya_hubmotion.set_enabled(on)


# ------------------------------------------------------------------ phases

def phase_open():
    import shutil
    import maya_hub
    from maya_poselib import look, store
    from maya_poselib import window as w
    guard()
    c = cmds()
    q = qt()
    QtCore, QtGui = q.QtCore, q.QtGui
    c.file(new=True, force=True)
    root = library_root()
    if os.path.isdir(root):
        shutil.rmtree(root)
    os.makedirs(root)
    scratch = root + "_pictures"
    if not os.path.isdir(scratch):
        os.makedirs(scratch)
    for index in range(CARDS):
        image = QtGui.QImage(640, 640, QtGui.QImage.Format_RGB32)
        image.fill(QtGui.QColor.fromHsv(hue_of(index), 190, 200))
        p = QtGui.QPainter(image)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255), 1))
        for x in range(0, 640, 4):                  # a fine comb: is the grown card sharp?
            p.drawLine(x, 0, x, 60)
        p.setBrush(QtGui.QColor(255, 255, 255, 230))
        p.setPen(QtCore.Qt.NoPen)
        p.drawEllipse(QtCore.QPointF(320, 190), 70, 70)               # a figure: head ...
        p.drawRoundedRect(QtCore.QRectF(235, 280, 170, 280), 50, 50)  # ... and body
        f = QtGui.QFont()
        f.setPixelSize(120)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QtGui.QColor(20, 20, 20))
        p.drawText(QtCore.QRectF(0, 330, 640, 200), QtCore.Qt.AlignCenter, str(index))
        p.end()
        picture = scratch + "/%02d.jpg" % index
        image.save(picture, "JPG", 92)
        data = {"kind": "character", "character": {"label": "Manny [rig]"},
                "members": ["pelvis"] * 5, "author": "verify"}
        store.write(root, "", "Pose %02d" % index, data, thumbnail=picture)
    c.optionVar(stringValue=(store.ROOT_VAR, root))
    for var in (w.SORT_VAR, w.SIZE_VAR):
        if c.optionVar(exists=var):
            c.optionVar(remove=var)
    animations(True)
    if c.workspaceControl(maya_hub.CONTROL, exists=True):
        c.workspaceControl(maya_hub.CONTROL, edit=True, close=True)
    if c.workspaceControl(w.CONTROL, exists=True):
        c.deleteUI(w.CONTROL)
    w.show_window()
    settle(6)
    win = window()
    gate("open the window standing", win is not None)
    if win is None:
        return
    top = top_level()
    k = float(win.k)
    want = (int(round(1000 * k)), int(round(640 * k)))
    for _ in range(5):
        win = window()
        dw, dh = want[0] - win.width(), want[1] - win.height()
        if not dw and not dh:
            break
        top.resize(top.width() + dw, top.height() + dh)
        settle()
    cv = canvas()
    gate("open the canvas lists the run's 24 cards", cv is not None and len(cv.cards) == CARDS,
         len(cv.cards) if cv else None)
    gate("open the cards at the default size", cv is not None and cv.cell == look.CELL_DEFAULT,
         "cell %s, window %dx%d, view %s, k %.2f" % (cv.cell, window().width(),
                                                    window().height(), cv.view(), k))


def phase_grow():
    from maya_poselib import look
    from maya_poselib import cardgrid
    cv = canvas()
    q = qt()
    cv.leaveEvent(q.QtCore.QEvent(q.QtCore.QEvent.Leave))
    pump(400)
    own = look.tile_rect(cv.rects()[HOVERED], cv.k)
    start = time.time()
    mouse(cv, "move", centre(cv, HOVERED))
    zs, stamps, timer_on = [], [], cv.zoom_timer.isActive()
    while time.time() - start < 0.6:
        q.QtWidgets.QApplication.processEvents()
        zs.append(cv.shown(HOVERED)[1])
        stamps.append(time.time() - start)
        time.sleep(0.004)
    first_full = next((t for z, t in zip(zs, stamps) if z >= look.ZOOM - 1e-9), None)
    rising = all(b >= a - 1e-9 for a, b in zip(zs, zs[1:]))
    gate("grow the timer starts on the hover", timer_on)
    gate("grow the card reaches 2x, monotonically", zs[-1] == look.ZOOM and rising,
         "z %.3f -> %.3f over %d samples" % (zs[0], zs[-1], len(zs)))
    gate("grow it takes about ZOOM_IN_MS (%d ms)" % look.ZOOM_IN_MS,
         first_full is not None and look.ZOOM_IN_MS / 1000.0 - 0.02 <= first_full <= 0.35,
         "full at %.0f ms" % (1000 * (first_full or -1)))
    gate("grow the timer stopped once grown", not cv.zoom_timer.isActive())
    tile, z = cv.shown(HOVERED)
    view = cv.view()
    gate("grow the grown tile holds the card's own and stands in the viewport",
         holds(tile, own) and inside(tile, view),
         "own %s grown %s view %s" % (own, tuple(round(v, 1) for v in tile), view))
    # one frame's repaint of what a growing card covers, mid-way, timed
    times = []
    real_now = cv._now
    try:
        for step in range(30):
            frozen = real_now()
            cv._zooms[cv.cards[HOVERED].path].to(0.0, frozen, False)
            cv._zooms[cv.cards[HOVERED].path].to(1.0, frozen - 70, True)  # half way in
            cv._now = lambda frozen=frozen: frozen
            reach = cv._reach(HOVERED)
            clock = q.QtCore.QElapsedTimer()
            clock.start()
            cv.repaint(reach)
            times.append(clock.nsecsElapsed() / 1e6)
    finally:
        cv._now = real_now
        cv._zooms[cv.cards[HOVERED].path].to(1.0, real_now(), False)
    times.sort()
    p95 = times[int(len(times) * 0.95) - 1]
    gate("grow a frame's repaint is cheap (p95 under 8 ms)", p95 < 8.0,
         "median %.2f ms, p95 %.2f ms, reach %dx%d" % (times[len(times) // 2], p95,
                                                     reach.width(), reach.height()))
    gate("grow the picture is read at twice the card's side",
         (cv.cards[HOVERED].thumbnail, cardgrid.zoom_side(cv.rects()[HOVERED][2]))
         in cv.pixmaps, cardgrid.zoom_side(cv.rects()[HOVERED][2]))


def _dwm(path):
    from maya_graphoverlay import winstyle
    q = qt()
    top = top_level()
    width, height = top.width(), top.height()
    data = winstyle.capture(int(top.winId()), width, height)
    if not data:
        return None, top
    image = q.QtGui.QImage(data, width, height, width * 4, q.QtGui.QImage.Format_RGB32).copy()
    if path:
        image.save(path)
    return image, top


def phase_photo():
    q = qt()
    cv = canvas()
    pump(150)
    image, top = _dwm(PICTURES + "/poselib_zoom.png")
    gate("photo DWM's copy of the window", image is not None)
    if image is None:
        return
    (gx, gy, gw, gh), z = cv.shown(HOVERED)
    rects = cv.rects()
    # a point of the right-hand neighbour's square that the grown card covers
    nx, ny, nw, nh = rects[HOVERED + 1]
    over = q.QtCore.QPoint(int(nx + 6), int(ny + nh * 0.75))
    covered = gx <= over.x() < gx + gw and gy <= over.y() < gy + gw
    far = rects[0] if HOVERED > 4 else rects[-1]
    away = q.QtCore.QPoint(int(far[0] + far[2] * 0.15), int(far[1] + far[3] * 0.85))  # its ground

    def hue(point):
        at = cv.mapTo(top, point)
        colour = image.pixelColor(at.x(), at.y())
        return colour.hsvHue(), colour

    h_over, c_over = hue(over)
    h_away, c_away = hue(away)

    def near(a, b):
        return min(abs(a - b), 360 - abs(a - b)) <= 12

    gate("photo where the grown card covers its neighbour, the grown card's colour",
         covered and near(h_over, hue_of(HOVERED)) and not near(h_over, hue_of(HOVERED + 1)),
         "hue %d (card %d is %d, its neighbour %d) %s" % (h_over, HOVERED, hue_of(HOVERED),
                                                          hue_of(HOVERED + 1), c_over.name()))
    far_index = 0 if HOVERED > 4 else CARDS - 1
    gate("photo a card far from it keeps its own colour", near(h_away, hue_of(far_index)),
         "hue %d (card %d is %d)" % (h_away, far_index, hue_of(far_index)))
    say("picture", PICTURES + "/poselib_zoom.png", image.width(), image.height())


def phase_press():
    """Which card grows is read off the grid's places alone (2026-10-03, the animator: «всегда
    на основе границ изначальной карточки»): the mouse onto the part of a neighbour the grown
    card covers grows the NEIGHBOUR, drawn on top, and a press there picks it; a gap grows
    nothing."""
    from maya_poselib import look
    q = qt()
    Qt = q.QtCore.Qt
    cv = canvas()
    mouse(cv, "move", centre(cv, HOVERED))
    pump(350)
    (gx, gy, gw, _gh), _z = cv.shown(HOVERED)
    nx, ny, nw, nh = cv.rects()[HOVERED + 1]
    over = q.QtCore.QPoint(int(nx + 6), int(ny + nh * 0.75))
    covered = gx <= over.x() < gx + gw and gy <= over.y() < gy + gw
    mouse(cv, "move", over)
    pump(350)
    order = [os.path.basename(path) for path, _zoom in cv.lifted_order()]
    gate("press the mouse onto the covered part of a neighbour grows the neighbour",
         covered and cv.shown(HOVERED + 1)[1] == look.ZOOM and cv.shown(HOVERED)[1] == 1.0
         and order == [os.path.basename(cv.cards[HOVERED + 1].path)],
         "covered %s, neighbour %.3f, first %.3f, lifted %s" % (
             covered, cv.shown(HOVERED + 1)[1], cv.shown(HOVERED)[1], order))
    mouse(cv, "press", over, Qt.LeftButton, Qt.LeftButton)
    mouse(cv, "release", over, Qt.LeftButton, Qt.NoButton)
    settle()
    win = window()
    gate("press a click there picks the card on top - the neighbour",
         win.picked == cv.cards[HOVERED + 1].path, os.path.basename(win.picked or ""))
    x, y, w, _h = cv.rects()[HOVERED]
    gap = q.QtCore.QPoint(int((x + w + nx) // 2), int(y + 40))
    mouse(cv, "move", gap)
    pump(350)
    gate("press the gap between two places grows nothing",
         cv.card_at(gap.x(), gap.y()) is None and cv._zooms == {}
         and not cv.zoom_timer.isActive(), "at x %d" % gap.x())
    mouse(cv, "move", centre(cv, HOVERED))
    pump(350)


def phase_move_on():
    from maya_poselib import look
    q = qt()
    cv = canvas()
    (gx, gy, gw, gh), _z = cv.shown(HOVERED)
    nx, ny, nw, nh = cv.rects()[HOVERED + 1]
    point = q.QtCore.QPoint(int(nx + nw - 4), int(ny + nh // 2))
    uncovered = point.x() >= gx + gw
    mouse(cv, "move", point)
    pump(40)
    z1, z2 = cv.shown(HOVERED)[1], cv.shown(HOVERED + 1)[1]
    order = [os.path.basename(path) for path, _zoom in cv.lifted_order()]
    gate("move_on onto the neighbour's uncovered part: it grows while the first shrinks",
         uncovered and 1.0 < z1 < look.ZOOM and 1.0 < z2 < look.ZOOM,
         "first %.3f, neighbour %.3f" % (z1, z2))
    gate("move_on the growing one is drawn on top",
         order[-1:] == [os.path.basename(cv.cards[HOVERED + 1].path)], order)
    pump(400)
    gate("move_on settled: the neighbour 2x, the first back, the timer stopped",
         cv.shown(HOVERED + 1)[1] == look.ZOOM and cv.shown(HOVERED)[1] == 1.0
         and not cv.zoom_timer.isActive())


def phase_edges():
    from maya_poselib import look
    cv = canvas()
    view = cv.view()
    mouse(cv, "move", centre(cv, 0))
    pump(350)
    tile, z = cv.shown(0)
    gate("edges the top-left card grows flush with the viewport's corner",
         z == look.ZOOM and abs(tile[0] - view[0]) < 0.5 and abs(tile[1] - view[1]) < 0.5,
         "tile %s view %s" % (tuple(round(v, 1) for v in tile), view))
    shown = [i for i, rect in enumerate(cv.rects())
             if holds(view, look.tile_rect(rect, cv.k))]
    last = shown[-1]
    mouse(cv, "move", centre(cv, last))
    pump(350)
    tile, z = cv.shown(last)
    gate("edges the last card of the visible bottom row grows inside the viewport",
         inside(tile, view) and holds(tile, look.tile_rect(cv.rects()[last], cv.k)),
         "card %d tile %s view %s z %.3f" % (last, tuple(round(v, 1) for v in tile), view, z))


def phase_scroll():
    cv = canvas()
    win = window()
    mouse(cv, "move", centre(cv, HOVERED))
    pump(350)
    bar = win.scroll.verticalScrollBar()
    before = cv.view()
    bar.setValue(min(bar.maximum(), bar.value() + cv.rects()[HOVERED][3] // 2))
    settle()
    after = cv.view()
    tile, z = cv.shown(HOVERED)
    gate("scroll the view moved and the grown card stands inside the new one",
         after[1] != before[1] and inside(tile, after),
         "view %s -> %s tile %s z %.3f" % (before, after, tuple(round(v, 1) for v in tile), z))
    bar.setValue(0)
    settle()


def phase_leave():
    from maya_poselib import look
    q = qt()
    cv = canvas()
    mouse(cv, "move", centre(cv, HOVERED))
    pump(350)
    start = time.time()
    cv.leaveEvent(q.QtCore.QEvent(q.QtCore.QEvent.Leave))
    zs, stamps = [], []
    while time.time() - start < 0.6:
        q.QtWidgets.QApplication.processEvents()
        zs.append(cv.shown(HOVERED)[1])
        stamps.append(time.time() - start)
        time.sleep(0.004)
    back = next((t for z, t in zip(zs, stamps) if z <= 1.0), None)
    falling = all(b <= a + 1e-9 for a, b in zip(zs, zs[1:]))
    gate("leave the card shrinks back, monotonically, in about ZOOM_OUT_MS (%d ms)"
         % look.ZOOM_OUT_MS,
         falling and back is not None and look.ZOOM_OUT_MS / 1000.0 - 0.02 <= back <= 0.4,
         "back at %.0f ms" % (1000 * (back or -1)))
    gate("leave nothing lifted, the timer stopped", cv._zooms == {} and not
         cv.zoom_timer.isActive())


def phase_off():
    from maya_poselib import look
    q = qt()
    cv = canvas()
    animations(False)
    try:
        mouse(cv, "move", centre(cv, HOVERED))
        grown = cv.shown(HOVERED)[1]
        timer = cv.zoom_timer.isActive()
        cv.leaveEvent(q.QtCore.QEvent(q.QtCore.QEvent.Leave))
        back = cv.shown(HOVERED)[1]
        gate("off Interface animations off: grown and shrunk at once, no timer",
             grown == look.ZOOM and back == 1.0 and not timer and not cv.zoom_timer.isActive(),
             "grown %.3f, back %.3f, timer %s" % (grown, back, timer))
    finally:
        animations(True)


def phase_thumb():
    from maya_poselib import capture
    c = cmds()
    top = maya_window()
    if top is not None and (top.isMinimized() or not top.isVisible()):
        top.showNormal()
    settle(5)
    c.polyCube(name="zoomCube")
    c.viewFit("persp")
    settle(5)
    path = library_root() + "_pictures/thumb_check.jpg"
    ok, note = capture.thumbnail(path)
    image = qt().QtGui.QImage(path) if ok else None
    gate("thumb a new thumbnail is 640 x 640", ok and image is not None
         and (image.width(), image.height()) == (640, 640),
         "%s %s %s" % (ok, note, (image.width(), image.height()) if image else None))


def phase_close():
    from maya_poselib import window as w
    c = cmds()
    if c.workspaceControl(w.CONTROL, exists=True):
        c.deleteUI(w.CONTROL)
    top = maya_window()
    if top is not None:
        top.showMinimized()
    gate("close", True)


PHASES = {"open": phase_open, "grow": phase_grow, "photo": phase_photo, "press": phase_press,
          "move_on": phase_move_on, "edges": phase_edges, "scroll": phase_scroll,
          "leave": phase_leave, "off": phase_off, "thumb": phase_thumb, "close": phase_close}


if _OUT and not os.path.exists(_MARK):
    with open(_MARK, "w") as _handle:
        _handle.write(_PHASE)
    _stream = io.open(_OUT, "w", encoding="utf-8", buffering=1)
    _old = (sys.stdout, sys.stderr)
    sys.stdout = sys.stderr = _stream
    try:
        if _PLUGIN in sys.path:
            sys.path.remove(_PLUGIN)
        sys.path.insert(0, _PLUGIN)
        if globals().get("PURGE"):
            _gone = 0
            for _name, _module in list(sys.modules.items()):
                _file = (getattr(_module, "__file__", None) or "").replace("\\", "/")
                if _file.startswith(_PLUGIN + "/"):
                    del sys.modules[_name]
                    _gone += 1
            print("purged %d modules of the plugin" % _gone)
        guard()
        PHASES[_PHASE]()
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
        RESULTS.append(False)
    finally:
        print("SUMMARY %d/%d" % (sum(RESULTS), len(RESULTS)))
        print("== END %s ==" % _PHASE)
        sys.stdout, sys.stderr = _old
        _stream.close()
