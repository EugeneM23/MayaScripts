"""The mode: what a press means, and what keeps the overlay honest.

Input is an ordinary `cmds.draggerContext`. That is the whole reason the
camera still works: in a Maya context `alt`+mouse is taken by the camera in
Maya's own event dispatch, so we never see it -- measured, all 1725 drag
events of a recorded session arrived with the modifier `'none'` while the
animator was orbiting.

The gesture rule, in one sentence: **LMB works on keys, and selects objects
when it caught no key.** A click with no key under it click-selects in the
scene, a marquee that caught no key box-selects in the scene, and both
halves are reachable without a modal switch. MMB drags the selected keys, or
a tangent handle when the press landed on one -- the Graph Editor's own
division of labour, which the animator already has in his hands.

`draggerContext` command strings are executed as PYTHON, not MEL (measured:
a MEL-style `python("...")` answered `NameError: name 'python' is not
defined`, which was itself the proof that the callback fires).
"""

import time

import maya.cmds as cmds

from maya_curveview import curves, edits, mapping, overlay, viewport

_real_cmds = cmds
_real_curves = curves
_real_edits = edits
_real_viewport = viewport

CONTEXT = "skeldarCurveViewCtx"
NORMALISE_VAR = "skeldarCurveViewNormalise"

# 10 Hz. Not an event filter: Maya destroys and rebuilds these widgets on a
# layout change, so a filter installed on one dies with it, while a timer
# comparing the rectangle covers the window move, Ctrl+Space, the layout
# switch, a monitor with another DPI and the focus change in one mechanism.
GEOMETRY_MS = 100

PICK_RADIUS = 9.0
THROTTLE = 0.05

# The most curves drawn at once. See `build_scene` for why there is a cap.
MAX_CURVES = 12

HINT = "LMB select  |  MMB drag keys  |  alt+mouse camera"
NO_CURVES = "Curve Overlay - select a control with animation"


class _State(object):

    def __init__(self):
        self.reset()

    def reset(self):
        self.overlay = None
        self.previous_tool = None
        self.timer = None
        self.jobs = []
        self.rect = None
        self.curves = []
        self.gesture = None
        self.anchor = None          # Qt pixels
        self.anchor_raw = None      # Maya screen pixels, Y from the bottom
        self.applied = (0.0, 0.0)
        self.modifier = "none"
        self.drag_time = 0.0
        self.tangent = None
        self.last_evaluated = None
        self.closing = False


_STATE = _State()


# ---------------------------------------------------------------- the state

def is_on():
    return _STATE.overlay is not None


def live_overlay():
    """The standing overlay, or None. The live proof asks for this."""
    return _STATE.overlay


def _normalise():
    try:
        if cmds.optionVar(exists=NORMALISE_VAR):
            return bool(cmds.optionVar(query=NORMALISE_VAR))
    except Exception:
        pass
    return False


def set_normalise(state):
    """One Y window per curve, or one shared axis. Remembered."""
    cmds.optionVar(intValue=(NORMALISE_VAR, 1 if state else 0))
    if is_on():
        refresh()
    return "Normalise: {0}".format("on" if state else "off")


def toggle_normalise():
    return set_normalise(not _normalise())


# --------------------------------------------------------------- the drawing

def build_scene(rect):
    """Everything the overlay needs to paint, read out of the scene.

    Sampling comes first and the Y window is fitted to the SAMPLES as well
    as the keys: a curve overshoots between its keys, and a window fitted to
    the keys alone would clip the overshoot -- which is exactly the shape an
    animator is looking at.
    """
    found = curves.visible_curves()
    total = len(found)
    # A cap, and it is not tidiness. Measured on the animator's own scene:
    # a UE clip's root carries 141 animated channels (Pose_0..9, MoveData_*
    # and ~130 pose drivers -- trap 40's game data), and drawn together they
    # crushed the real animation into a flat band. `curves.py` narrows the
    # fallback to the transform channels; this is the backstop, and it says
    # what to do rather than silently drawing twelve of a hundred.
    found = found[:MAX_CURVES]
    _STATE.curves = found
    span = curves.time_range()
    if not found:
        return overlay.Scene(mapping.autoframe(span, None), [],
                             _current_time(), NO_CURVES, None)

    count = mapping.sample_count(rect)
    sampled = [curves.sample(curve.curve, span[0], span[1], count)
               for curve in found]
    series = [points + curve.keys
              for points, curve in zip(sampled, found)]
    shared = mapping.autoframe(span, mapping.value_span(series))
    normalised = _normalise()
    if normalised:
        frames = mapping.normalise(span, series)
    else:
        frames = [shared] * len(found)

    drawn = []
    for curve, points, frame in zip(found, sampled, frames):
        selected = set(curves.selected_indices(curve.curve))
        drawn.append(overlay.Drawn(
            curve.attribute, frame, points, curve.keys, selected,
            curves.tangent_angles(curve.curve, sorted(selected))))
    if total > MAX_CURVES:
        message = ("{0} of {1} channels - pick the ones you want in the "
                   "channel box   {2}".format(len(drawn), total, HINT))
    else:
        message = "{0} curve(s)   {1}".format(len(drawn), HINT)
    return overlay.Scene(shared, drawn, _current_time(), message, None,
                         normalised)


def _current_time():
    try:
        return float(cmds.currentTime(query=True))
    except Exception:
        return None


def refresh():
    """Re-read the scene and repaint. Cheap enough for a selection change."""
    if not is_on():
        return
    rect = _STATE.overlay.rect_size()
    _STATE.overlay.set_scene(build_scene(rect))


# ------------------------------------------------------------------ the mode

def enable():
    if is_on():
        return "Curve Overlay is already on"
    rect = viewport.panel_rect()
    if rect is None:
        return "Curve Overlay: no model panel to draw on"

    window = overlay.CurveOverlay(viewport.maya_main_window())
    window.place(rect)
    _STATE.overlay = window
    _STATE.rect = rect

    _make_context()
    _STATE.previous_tool = cmds.currentCtx()
    cmds.setToolTo(CONTEXT)

    refresh()
    _install_jobs()
    _start_timer()
    return "Curve Overlay ON   -   " + HINT


def disable():
    if not is_on():
        return "Curve Overlay is already off"
    _STATE.closing = True
    try:
        _stop_timer()
        _kill_jobs()
        edits.end()
        try:
            if cmds.draggerContext(CONTEXT, exists=True):
                cmds.deleteUI(CONTEXT)
        except Exception:
            pass
        previous = _STATE.previous_tool
        if previous:
            try:
                cmds.setToolTo(previous)
            except Exception:
                pass
        window = _STATE.overlay
        _STATE.overlay = None
        if window is not None:
            window.close_overlay()
    finally:
        _STATE.reset()
    return "Curve Overlay OFF"


def toggle():
    return disable() if is_on() else enable()


# ------------------------------------------------------------- the plumbing

def _make_context():
    if cmds.draggerContext(CONTEXT, exists=True):
        cmds.deleteUI(CONTEXT)
    body = "import maya_curveview.tool as _cv; _cv.{0}()"
    cmds.draggerContext(
        CONTEXT,
        space="screen",
        cursor="crossHair",
        undoMode="step",
        pressCommand=body.format("on_press"),
        dragCommand=body.format("on_drag"),
        releaseCommand=body.format("on_release"))


def _install_jobs():
    """Installed AFTER `setToolTo`, or our own switch trips the tool job."""
    _STATE.jobs = []
    for event, handler in (("SelectionChanged", _on_selection),
                           ("timeChanged", _on_time),
                           ("ToolChanged", _on_tool)):
        try:
            _STATE.jobs.append(cmds.scriptJob(event=[event, handler],
                                              killWithScene=False))
        except Exception:
            pass


def _kill_jobs():
    for job in _STATE.jobs:
        try:
            cmds.scriptJob(kill=job, force=True)
        except Exception:
            pass
    _STATE.jobs = []


def _on_selection():
    refresh()


def _on_time():
    if is_on():
        _STATE.overlay.set_scene(
            _STATE.overlay.scene()._replace(current_time=_current_time()))


def _on_tool():
    """Leaving the tool leaves the mode.

    Press W and the context is no longer ours, so an overlay still hanging
    there lies: curves are drawn and nothing can grab them. Measured in the
    first probe, which is where the idea came from.
    """
    if _STATE.closing or not is_on():
        return
    try:
        current = cmds.currentCtx()
    except Exception:
        return
    if current != CONTEXT:
        disable()


def _start_timer():
    try:
        from PySide6 import QtCore
    except ImportError:
        return
    timer = QtCore.QTimer()
    timer.setInterval(GEOMETRY_MS)
    timer.timeout.connect(_follow_viewport)
    timer.start()
    _STATE.timer = timer


def _stop_timer():
    timer = _STATE.timer
    _STATE.timer = None
    if timer is not None:
        try:
            timer.stop()
            timer.timeout.disconnect()
        except (RuntimeError, TypeError):
            pass


def _follow_viewport():
    """Keep the window on the viewport, and out of the way of other apps."""
    if not is_on():
        return
    window = _STATE.overlay
    if not viewport.maya_has_focus():
        if window.isVisible():
            window.hide()
        return
    rect = viewport.panel_rect()
    if rect is None:
        if window.isVisible():
            window.hide()
        return
    if rect != _STATE.rect or not window.isVisible():
        _STATE.rect = rect
        window.place(rect)
        refresh()          # the pixel mapping changed with the rectangle


# ------------------------------------------------------------- the gestures

def _raw_point(flag):
    point = cmds.draggerContext(CONTEXT, query=True, **{flag: True}) or []
    if len(point) < 2:
        return (0.0, 0.0)
    return (float(point[0]), float(point[1]))


def _button():
    try:
        return int(cmds.draggerContext(CONTEXT, query=True, button=True))
    except Exception:
        return 1


def _modifier():
    try:
        return cmds.draggerContext(CONTEXT, query=True, modifier=True)
    except Exception:
        return "none"


def _qt_point(raw, rect):
    return (raw[0], mapping.flip_y(rect, raw[1]))


def hit_key(scene, rect, x, y):
    """(curve index, key index) under the point, or None."""
    best = None
    best_distance = PICK_RADIUS ** 2
    for order, drawn in enumerate(scene.curves):
        index = mapping.pick_key(drawn.frame, rect, drawn.keys, x, y,
                                 radius=PICK_RADIUS)
        if index is None:
            continue
        kx, ky = mapping.to_pixels(drawn.frame, rect, *drawn.keys[index])
        distance = (kx - x) ** 2 + (ky - y) ** 2
        if distance <= best_distance:
            best, best_distance = (order, index), distance
    return best


def hit_tangent(scene, rect, x, y):
    """(curve index, key index, side) under the point, or None."""
    for order, drawn in enumerate(scene.curves):
        found = mapping.pick_tangent(drawn.frame, rect, drawn.keys,
                                     drawn.tangents, drawn.selected, x, y,
                                     radius=PICK_RADIUS)
        if found is not None:
            return (order, found[0], found[1])
    return None


def _selected_pairs(scene):
    """[(curve index, key index)] for every selected key on screen."""
    return [(order, index) for order, drawn in enumerate(scene.curves)
            for index in sorted(drawn.selected)]


def on_press():
    state = _STATE
    if not is_on():
        return
    rect = state.overlay.rect_size()
    raw = _raw_point("anchorPoint")
    point = _qt_point(raw, rect)
    state.anchor_raw = raw
    state.anchor = point
    state.applied = (0.0, 0.0)
    state.last_evaluated = None
    state.modifier = _modifier()
    state.tangent = None
    scene = state.overlay.scene()

    if _button() == 2:
        handle = hit_tangent(scene, rect, point[0], point[1])
        if handle is not None:
            state.gesture = "tangent"
            state.tangent = handle
            edits.begin()
            return
        pairs = _selected_pairs(scene)
        if not pairs:
            state.gesture = None
            return
        state.gesture = "drag"
        state.drag_time = _drag_anchor_time(scene, rect, point, pairs)
        edits.begin()
        return

    state.gesture = "select"


def _drag_anchor_time(scene, rect, point, pairs):
    """The time to follow while dragging: the selected key nearest the press.

    Following the pose being edited is the whole feature, and with several
    keys selected "the pose" is the one the hand is on.
    """
    best, best_distance = None, None
    for order, index in pairs:
        drawn = scene.curves[order]
        kx, ky = mapping.to_pixels(drawn.frame, rect, *drawn.keys[index])
        distance = (kx - point[0]) ** 2 + (ky - point[1]) ** 2
        if best_distance is None or distance < best_distance:
            best, best_distance = drawn.keys[index][0], distance
    return float(best if best is not None else 0.0)


def on_drag():
    state = _STATE
    if not is_on() or state.gesture is None:
        return
    rect = state.overlay.rect_size()
    raw = _raw_point("dragPoint")
    point = _qt_point(raw, rect)

    if state.gesture == "select":
        state.overlay.set_marquee((state.anchor[0], state.anchor[1],
                                   point[0], point[1]))
        return

    scene = state.overlay.scene()
    if state.gesture == "tangent":
        order, index, side = state.tangent
        drawn = scene.curves[order]
        angle = mapping.tangent_angle(drawn.frame, rect, drawn.keys[index],
                                      point[0], point[1], side)
        edits.set_tangent(state.curves[order].curve, index, side, angle)
        _throttled_refresh()
        return

    if state.gesture == "drag":
        frame = scene.curves[0].frame if scene.curves else scene.frame
        t0, v0 = mapping.to_curve(frame, rect, *state.anchor)
        t1, v1 = mapping.to_curve(frame, rect, point[0], point[1])
        total = (mapping.snap(t1 - t0), v1 - v0)
        edits.apply_delta(total[0] - state.applied[0],
                          total[1] - state.applied[1])
        state.applied = total
        _throttled_follow(state.drag_time + total[0])


def _throttled_follow(at_time):
    """Move the current time with the key, then repaint -- both gated.

    One gate for both, because the expensive half is the rig evaluation and
    a repaint needs a re-sample anyway. At 20 Hz it reads as smooth and the
    animator's 10 fps scene is not asked for 860 evaluations.
    """
    state = _STATE
    now = time.time()
    stamp = edits.follow_time(at_time, now, state.last_evaluated, THROTTLE)
    if stamp != state.last_evaluated:
        state.last_evaluated = stamp
        refresh()


def _throttled_refresh():
    state = _STATE
    now = time.time()
    if mapping.should_evaluate(now, state.last_evaluated, THROTTLE):
        state.last_evaluated = now
        refresh()


def on_release():
    state = _STATE
    if not is_on():
        return
    gesture = state.gesture
    state.gesture = None
    rect = state.overlay.rect_size()
    raw = _raw_point("dragPoint")
    point = _qt_point(raw, rect)

    if gesture == "select":
        state.overlay.set_marquee(None)
        _finish_select(rect, point, raw)
        refresh()
        return

    if gesture in ("drag", "tangent"):
        if gesture == "drag":
            scene = state.overlay.scene()
            frame = scene.curves[0].frame if scene.curves else scene.frame
            t0, v0 = mapping.to_curve(frame, rect, *state.anchor)
            t1, v1 = mapping.to_curve(frame, rect, point[0], point[1])
            total = (mapping.snap(t1 - t0), v1 - v0)
            edits.apply_delta(total[0] - state.applied[0],
                              total[1] - state.applied[1])
            state.applied = total
            edits.settle(state.drag_time + total[0])
        edits.end()
        refresh()
        return


def _finish_select(rect, point, raw):
    """LMB: keys first, and the scene when no key was caught."""
    state = _STATE
    scene = state.overlay.scene()
    adjust = mapping.adjustment(state.modifier)
    marquee = mapping.is_marquee(state.anchor[0], state.anchor[1],
                                 point[0], point[1])

    caught = {}
    if marquee:
        for order, drawn in enumerate(scene.curves):
            indices = mapping.keys_in_box(drawn.frame, rect, drawn.keys,
                                          state.anchor[0], state.anchor[1],
                                          point[0], point[1])
            if indices:
                caught[order] = indices
    else:
        found = hit_key(scene, rect, point[0], point[1])
        if found is not None:
            caught[found[0]] = [found[1]]

    if caught:
        select_keys(caught, adjust)
        return

    if marquee:
        select_from_screen(state.anchor_raw[0], state.anchor_raw[1],
                           raw[0], raw[1], state.modifier)
    else:
        select_from_screen(raw[0], raw[1], raw[0], raw[1], state.modifier)


# ------------------------------------------------------------- the selecting

def _clear_key_selection():
    """CLAUDE.md trap 43: `selectKey(clear=True)` RAISES when nothing is
    selected -- it wants objects to resolve its defaults against, even
    though clearing needs none. The failure is exactly the case with
    nothing to clear, so it is swallowed."""
    try:
        cmds.selectKey(clear=True)
    except Exception:
        pass


def select_keys(caught, adjust):
    """`caught` is {curve order: [key indices]} against `_STATE.curves`."""
    if adjust == "replace":
        _clear_key_selection()
        mode = {"add": True}
    elif adjust == "add":
        mode = {"add": True}
    elif adjust == "toggle":
        mode = {"toggle": True}
    else:
        mode = {"remove": True}
    for order, indices in caught.items():
        if order >= len(_STATE.curves):
            continue
        curve = _STATE.curves[order].curve
        for index in indices:
            try:
                cmds.selectKey(curve, index=(index, index), **mode)
            except Exception:
                pass


def apply_adjustment(before, picked, adjust):
    """Put `before` back and fold `picked` into it the way `adjust` says.

    Split out from the pick so the half with the decisions in it is
    testable without an OpenMaya in the room.
    """
    if adjust == "replace":
        return                       # the pick already IS the selection
    if before:
        cmds.select(before, replace=True)
    else:
        cmds.select(clear=True)
    if not picked:
        return
    if adjust == "add":
        cmds.select(picked, add=True)
    elif adjust == "toggle":
        cmds.select(picked, toggle=True)
    else:
        cmds.select(picked, deselect=True)


def select_from_screen(x0, y0, x1, y1, modifier):
    """Maya's own viewport selection, done by us because LMB is ours.

    The coordinates are Maya's SCREEN space -- Y from the bottom -- which is
    exactly what `draggerContext` handed over, so nothing is flipped on this
    path. Flipping it would select whatever is mirrored about the middle of
    the viewport, which looks like a broken pick rather than a wrong Y.

    **The pick is always a REPLACE, and the modifier is applied afterwards
    by us.** Measured live 2026-09-05: the CLICK form of `kXORWithList` is a
    NO-OP -- from an empty selection it selects nothing, from a held one it
    changes nothing -- while the BOX form of the same value toggles
    correctly. So a shift-click routed through the API's own adjustment
    silently did nothing, which is the worst kind of wrong: the animator
    shift-clicks, sees no change, and blames their own aim. `kReplaceList`
    is the one value measured to behave identically in both forms, and
    `cmds.select` is exact for all four behaviours.
    """
    import maya.api.OpenMaya as om
    adjust = mapping.adjustment(modifier)
    method = om.MGlobal.kWireframeSelectMethod
    before = cmds.ls(selection=True, long=True) or []
    if abs(x1 - x0) < 1.0 and abs(y1 - y0) < 1.0:
        om.MGlobal.selectFromScreen(int(x0), int(y0),
                                    om.MGlobal.kReplaceList, method)
    else:
        om.MGlobal.selectFromScreen(int(min(x0, x1)), int(min(y0, y1)),
                                    int(max(x0, x1)), int(max(y0, y1)),
                                    om.MGlobal.kReplaceList, method)
    picked = cmds.ls(selection=True, long=True) or []
    apply_adjustment(before, picked, adjust)


# ---------------------------------------------------------------- the extras

def insert_key_at_time():
    """A key on every drawn curve at the current frame."""
    if not is_on():
        return "Curve Overlay is off"
    at_time = _current_time()
    made = 0
    for curve in _STATE.curves:
        try:
            edits.insert_key(curve.curve, at_time)
            made += 1
        except Exception:
            pass
    refresh()
    return "Key inserted on {0} curve(s) at frame {1:g}".format(made,
                                                                at_time)


def delete_selected_keys():
    if not is_on():
        return "Curve Overlay is off"
    edits.begin()
    try:
        gone = edits.delete_selected()
    finally:
        edits.end()
    refresh()
    return "Deleted {0} key(s)".format(gone)
