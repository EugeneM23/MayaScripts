"""verify_character_fire.py - the Characters cards catch fire under the
mouse: live.

Run in a DISPOSABLE Maya (scratch MAYA_APP_DIR, MAYA_NO_HOME) on the REPO's
hub, floated to the animator's dock width, sent through its command port.
The send turns the event loop itself (processEvents + processIdleEvents +
4 ms sleeps), so the fire burns on a real clock. The mouse is a real Qt
QMouseEvent sent to the grid.

    1  the hub open on Animation Setup, the portrait grid standing in it
    2  a mouse move onto the Creep portrait lights it: its fire, the timer on
    3  after a second: the overlay stands in the hub's scrolled content,
       mouse-transparent, over the grid and past its edges, drawing the Creep
       card (the grid skips it); the card grown, its fire hot
    4  the fire is the Creep's own: blue in the overlay's picture, none in
       the grid's; moved onto the Orc D, it burns green
    5  the cost: the paints of a burning second (p95), a turn of the loop
    6  the mouse off the grid: everything burns out, the timer stops, the
       overlay hides
    7  Interface animations off: no fire, the old hover
    8  a hub rebuild leaves no overlay behind, and the new grid burns again
    9  a picture of the hub with a card burning (DWM's copy of the window)

UI only: no scene node is touched; the switch's optionVar is put back.

Spec: docs/superpowers/specs/2026-10-02-character-card-fire-design.md
"""
import os
import time

import maya.cmds as cmds
import maya.utils

import maya_hub
import maya_hubmotion
import maya_hubqt

FAILED = []
PASSED = []
OUT = os.environ.get("SKELDAR_FIRE_OUT", "")
PORTRAITS = "mayaSceneSetupPortraits"


def gate(n, name, ok, detail=""):
    (PASSED if ok else FAILED).append(n)
    print("%s %2s %s%s" % ("ok  " if ok else "FAIL", n, name,
                           (" - " + str(detail)) if detail else ""))


q = maya_hubqt.qt()
QtCore, QtGui, QtWidgets = q.QtCore, q.QtGui, q.QtWidgets
app = QtWidgets.QApplication.instance()
COST = []


def turn():
    t0 = time.perf_counter()
    app.processEvents()
    maya.utils.processIdleEvents()
    COST.append((time.perf_counter() - t0) * 1000.0)


def run(seconds=None, until=None, timeout=6.0, record=None):
    t0 = time.perf_counter()
    while True:
        spent = time.perf_counter() - t0
        if seconds is not None and spent >= seconds:
            break
        if seconds is None and spent >= timeout:
            break
        turn()
        if record:
            record()
        if until is not None and until():
            break
        time.sleep(0.004)
    return time.perf_counter() - t0


def grid_now():
    """The grid standing right now, found again by its placeholder (never a
    wrapper kept across a rebuild - trap 148)."""
    import maya_chargrid
    return maya_chargrid.live(PORTRAITS)


def keys(grid):
    return [m.key for m in grid.models]


def centre(grid, model):
    x, y, w, h = grid.rects()[keys(grid).index(model)]
    return QtCore.QPointF(x + w / 2.0, y + h / 2.0)


def move(grid, local):
    g = grid.mapToGlobal(local.toPoint())
    event = QtGui.QMouseEvent(QtCore.QEvent.MouseMove, local,
                              QtCore.QPointF(g), QtCore.Qt.NoButton,
                              QtCore.Qt.NoButton, QtCore.Qt.NoModifier)
    QtWidgets.QApplication.sendEvent(grid, event)


def leave(grid):
    QtWidgets.QApplication.sendEvent(grid, QtCore.QEvent(QtCore.QEvent.Leave))


def render(widget):
    image = QtGui.QImage(widget.size(), QtGui.QImage.Format_ARGB32)
    image.fill(0)
    widget.render(image)
    return image


def count(image, rect, test, dx=0, dy=0):
    x0, y0, w, h = [int(v) for v in rect]
    hits = 0
    for x in range(x0 + dx, x0 + dx + w, 2):
        for y in range(y0 + dy, y0 + dy + h, 2):
            if 0 <= x < image.width() and 0 <= y < image.height():
                c = image.pixelColor(x, y)
                if test(c.red(), c.green(), c.blue()):
                    hits += 1
    return hits


def blue(r, g, b):
    return b > r + 50 and b > 90


def green(r, g, b):
    return g > r + 50 and g > b + 30 and g > 90


def overlays():
    import maya_chargrid
    return [w for w in app.allWidgets()
            if w.objectName() == maya_chargrid.FIRE_NAME
            and q.shiboken.isValid(w)]


saved_switch = maya_hubmotion.enabled()
maya_hub.set_animations(True)
try:
    # ------------------------------------------------- 1 the hub, the grid
    maya_hub.show("characters")
    cmds.workspaceControl(maya_hub.CONTROL, edit=True, floating=True)
    run(0.3)
    skin = maya_hub._SKIN
    for c in skin.cards.values():
        c.set_collapsed(True)
    skin.cards["characters"].set_collapsed(False)
    run(0.6)
    window = skin.root.window()
    view = skin.scroll.viewport()
    for _ in range(8):                    # the animator's dock: 510 px
        if abs(view.width() - 510) <= 2:
            break
        window.resize(window.width() + (510 - view.width()),
                      max(window.height(), 900))
        run(0.2)
    skin.scroll.verticalScrollBar().setValue(0)
    run(0.3)
    grid = grid_now()
    gate(1, "the hub open on Animation Setup, the grid standing in it",
         grid is not None and grid.isVisible(),
         "viewport %d px, %s" % (view.width(),
                                 keys(grid) if grid else None))

    # --------------------------------------------------------- 2 a hover
    move(grid, centre(grid, "Creep"))
    fx = grid.fx.get("Creep")
    gate(2, "a mouse move onto the Creep lights it",
         fx is not None and fx.hover and grid.fire_timer.isActive(),
         "fx %s, timer %s" % (sorted(grid.fx), grid.fire_timer.isActive()))

    # ------------------------------------------- 3 the overlay draws it
    paints = []
    run(1.2, record=lambda: paints.append(
        (grid.paint_ms, grid.overlay.paint_ms if grid.overlay else 0.0)))
    overlay = grid.overlay
    content = skin.content
    spot = QtCore.QRect(grid.mapTo(content, QtCore.QPoint(0, 0)), grid.size())
    ok = (overlay is not None and q.shiboken.isValid(overlay)
          and overlay.isVisible()
          and maya_hubqt.qt().shiboken.getCppPointer(overlay.parentWidget())
          == q.shiboken.getCppPointer(content)
          and overlay.testAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
          and overlay.geometry().contains(spot)
          and overlay.geometry().top() < spot.top()
          and grid.overlaid == {"Creep"})
    fx = grid.fx.get("Creep")
    gate(3, "the overlay in the hub's content, past the grid's edges, "
            "drawing the Creep",
         ok and fx is not None and fx.power > 0.9 and fx.grow > 0.9,
         "overlay %s around grid %s, overlaid %s, power %.2f, grow %.2f"
         % (overlay.geometry() if overlay else None, spot,
            sorted(grid.overlaid), fx.power if fx else -1,
            fx.grow if fx else -1))

    # -------------------------------------------------- 4 its own colour
    rect = grid.rects()[keys(grid).index("Creep")]
    o = overlay.origin if overlay else QtCore.QPoint(0, 0)
    lifted = render(overlay) if overlay else QtGui.QImage()
    in_overlay = count(lifted, rect, blue, o.x(), o.y())
    in_grid = count(render(grid), rect, blue)
    if OUT:
        lifted.save(os.path.join(OUT, "fire_overlay_creep.png"))
    move(grid, centre(grid, "Orc_D"))
    run(1.2)
    rect_o = grid.rects()[keys(grid).index("Orc_D")]
    overlay = grid.overlay
    o = overlay.origin if overlay else QtCore.QPoint(0, 0)
    in_green = count(render(overlay), rect_o, green, o.x(), o.y()) \
        if overlay else 0
    gate(4, "the Creep burns blue in the overlay (none in the grid), the "
            "Orc D green",
         in_overlay > 60 and in_grid < 5 and in_green > 15,
         "blue %d in the overlay, %d in the grid; green %d"
         % (in_overlay, in_grid, in_green))

    # ---------------------------------------------------------- 5 the cost
    both = sorted(a + b for a, b in paints if a or b)
    p95 = both[int(len(both) * 0.95)] if both else -1
    burning_turns = sorted(COST[-200:])
    turn99 = burning_turns[int(len(burning_turns) * 0.99) - 1] \
        if burning_turns else -1
    gate(5, "a burning frame's paints (grid + overlay) p95 under 8 ms",
         0 < p95 < 8.0,
         "p95 %.2f ms over %d frames, a loop turn p99 %.1f ms"
         % (p95, len(both), turn99))

    # ------------------------------------------------- 6 the mouse leaves
    leave(grid)
    spent = run(until=lambda: not grid.fx, timeout=6.0)
    overlay = grid.overlay
    gate(6, "the mouse off: it burns out, the timer stops, the overlay "
            "hides",
         not grid.fx and not grid.fire_timer.isActive()
         and (overlay is None or not overlay.isVisible()),
         "cold after %.2f s" % spent)

    # --------------------------------------------- 7 animations switched off
    maya_hub.set_animations(False)
    run(0.2)
    grid = grid_now()
    move(grid, centre(grid, "Creep"))
    run(0.3)
    gate(7, "Interface animations off: no fire, the old hover",
         not grid.fx and grid._hover == "Creep",
         "fx %s, hover %s" % (sorted(grid.fx), grid._hover))
    leave(grid)
    maya_hub.set_animations(True)
    run(0.3)

    # ----------------------------------------------- 8 a rebuild, again
    grid = grid_now()
    move(grid, centre(grid, "Creep"))
    run(0.4)
    before = len(overlays())
    maya_hub.rebuild()
    run(0.8)
    left = len(overlays())
    skin = maya_hub._SKIN
    skin.cards["characters"].set_collapsed(False)
    run(0.6)
    grid = grid_now()
    move(grid, centre(grid, "Manny"))
    run(1.0)
    again = grid is not None and "Manny" in grid.fx and len(overlays()) == 1
    gate(8, "a hub rebuild leaves no overlay behind; the new grid burns",
         before == 1 and left == 0 and again,
         "overlays %d before, %d after the rebuild, then %d; fx %s"
         % (before, left, len(overlays()), sorted(grid.fx) if grid else None))

    # --------------------------------------------------------- 9 a picture
    shot = ""
    if OUT:
        try:
            from maya_graphoverlay import winstyle
            import numpy as np
            top = skin.root.window()
            run(0.3)
            w, h = top.width(), top.height()
            data = winstyle.capture(int(top.winId()), w, h)
            if data:
                image = QtGui.QImage(data, w, h, w * 4,
                                     QtGui.QImage.Format_RGB32).copy()
                shot = os.path.join(OUT, "fire_hub.png")
                image.save(shot)
        except Exception as exc:                             # noqa: BLE001
            print("picture failed:", exc)
    gate(9, "a picture of the hub with a card burning", bool(shot), shot)
    leave(grid)
    run(until=lambda: not grid.fx, timeout=6.0)
finally:
    maya_hub.set_animations(saved_switch)

print("SUMMARY %d passed, %d failed %s" % (len(PASSED), len(FAILED), FAILED))
