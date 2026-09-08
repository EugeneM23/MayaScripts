"""Live proof for the Curve Overlay. Sent through the command port.

Runs in the animator's OPEN scene, so: everything is resolved by long path
or UUID, every node it creates is registered as it is created and deleted
from that registry, every teardown step is guarded on its own, and the
frame, the playback range, autoKey, the selection and the current tool are
left exactly as they were found.

What it proves that a unit test cannot:

* the window really composites where the viewport is, and the OS really
  hit-tests through it
* the flag combinations this feature guessed are the ones Maya accepts --
  `keyframe(edit, relative, animation="keys")` to move selected keys,
  `keyframe(query, eval, time)` to sample a curve node, `selectKey` with an
  index, `MGlobal.selectFromScreen` in both its forms
* the whole mode goes up and comes down leaving nothing behind

Deliberately NOT proved here: the undo chunk. `cmds.undo()` inside a bridge
script reverts a whole prior chunk of the animator's work -- the script is
itself one command -- so it is forbidden by hard-won project rule. The chunk
is pinned by unit test instead (`tests/test_curveview_edits.py` counts the
open and the close, including when the edit raises).

Also not proved: the channel-box narrowing. `selectedMainAttributes` is
query-only, so the animator's channel-box selection cannot be set from a
script; the live gate covers the fallback (nothing picked there means every
animated channel) and the narrowing is unit-tested.
"""

import sys
import traceback

REPO = "C:/!!!Work/MayaScripts/SkeldarAnim"

# CLAUDE.md note 9: the session imports the INSTALLED copy, and an appended
# path loses to it. Insert at the front and purge the package trees whole --
# package ROOTS included, or `from pkg import mod` hands back the old object.
if REPO in sys.path:
    sys.path.remove(REPO)
sys.path.insert(0, REPO)
for name in list(sys.modules):
    if name.split(".")[0] in ("maya_curveview",):
        del sys.modules[name]

import maya.cmds as cmds                                       # noqa: E402
import maya.api.OpenMaya as om                                 # noqa: E402
import maya.api.OpenMayaUI as omui2                            # noqa: E402

from maya_curveview import (curves, edits, mapping, overlay,    # noqa: E402
                            tool, viewport)

FAILED = []
PASSED = []
SKIPPED = []
CREATED = []          # UUIDs, registered as each node is created


def gate(name, ok, detail=""):
    line = "{0:<62} {1}".format(name, "PASS" if ok else "FAIL")
    if detail:
        line += "   " + detail
    print(line)
    (PASSED if ok else FAILED).append(name)
    return ok


def skip(name, why):
    print("{0:<62} SKIP   {1}".format(name, why))
    SKIPPED.append(name)


def make(kind, name):
    """Create a node and register its UUID in the same breath (trap 47)."""
    node = cmds.createNode(kind, name=name, skipSelect=True)
    node = cmds.ls(node, long=True)[0]
    uuid = cmds.ls(node, uuid=True)
    if uuid:
        CREATED.append(uuid[0])
    return node


# ------------------------------------------------------------------- state

entry = {
    "selection": cmds.ls(selection=True, long=True) or [],
    "time": cmds.currentTime(query=True),
    "autokey": cmds.autoKeyframe(query=True, state=True),
    "min": cmds.playbackOptions(query=True, min=True),
    "max": cmds.playbackOptions(query=True, max=True),
    "tool": cmds.currentCtx(),
    "normalise": (cmds.optionVar(query=tool.NORMALISE_VAR)
                  if cmds.optionVar(exists=tool.NORMALISE_VAR) else None),
}
print("entry state: {0}".format(entry))
print("")

try:
    cmds.autoKeyframe(state=False)

    # A standing overlay from an earlier run would make every gate read the
    # previous state -- the vpstudio lesson: capture the entry state AFTER
    # clearing what a previous run left up.
    if tool.is_on():
        print("an overlay was already up - taking it down first")
        tool.disable()

    # --------------------------------------------------------- the sandbox
    #
    # A locator placed in front of the viewing camera, so it is genuinely
    # pickable on screen: the selection gates below click on it.

    panel = viewport.active_panel()
    if not panel:
        raise RuntimeError("no visible model panel - open one and re-send")
    print("model panel: {0}".format(panel))

    camera = cmds.modelEditor(panel, query=True, camera=True)
    camera_path = cmds.ls(camera, long=True)[0]
    matrix = cmds.xform(camera_path, query=True, worldSpace=True,
                        matrix=True)
    eye = (matrix[12], matrix[13], matrix[14])
    forward = (-matrix[8], -matrix[9], -matrix[10])       # a camera looks -Z
    REACH = 60.0
    spot = [eye[i] + forward[i] * REACH for i in range(3)]

    sandbox = make("transform", "curveViewVerifySandbox")
    shape = cmds.createNode("locator", parent=sandbox, skipSelect=True)
    shape_uuid = cmds.ls(cmds.ls(shape, long=True)[0], uuid=True)
    if shape_uuid:
        CREATED.append(shape_uuid[0])
    cmds.setAttr(shape + ".localScaleX", 12.0)
    cmds.setAttr(shape + ".localScaleY", 12.0)
    cmds.setAttr(shape + ".localScaleZ", 12.0)
    cmds.xform(sandbox, worldSpace=True, translation=spot)

    base = cmds.getAttr(sandbox + ".translateY")
    for frame, offset in ((0.0, 0.0), (50.0, 25.0), (100.0, 0.0)):
        cmds.setKeyframe(sandbox + ".translateY", time=frame,
                         value=base + offset)
    for frame, offset in ((0.0, 0.0), (100.0, 10.0)):
        cmds.setKeyframe(sandbox + ".rotateZ", time=frame, value=offset)
    for frame, offset in ((0.0, 1.0), (100.0, 2.0)):
        cmds.setKeyframe(sandbox + ".scaleX", time=frame, value=offset)
    print("sandbox: {0} at {1}".format(
        sandbox, ", ".join("{0:.2f}".format(v) for v in spot)))
    print("")

    # ------------------------------------------------- 1. the mode goes up

    message = tool.enable()
    gate("1  enable() reports the mode on", "ON" in message, message)
    window = tool.live_overlay()
    gate("2  an overlay window exists", window is not None)

    gl_rect = viewport.panel_rect(panel)
    if window is not None and gl_rect:
        geometry = window.geometry()
        got = (geometry.x(), geometry.y(), geometry.width(),
               geometry.height())
        gate("3  the window sits on the GL rect to the pixel", got == gl_rect,
             "{0} vs {1}".format(got, gl_rect))
    else:
        skip("3  the window sits on the GL rect to the pixel", "no rect")

    gate("4  the ex-style carries LAYERED and TRANSPARENT",
         overlay.is_click_through(window))

    # WindowFromPoint takes the same decision a real click would: the docs
    # say it skips a window carrying WS_EX_TRANSPARENT.
    try:
        import ctypes
        from ctypes import wintypes

        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.WindowFromPoint.argtypes = [POINT]
        user32.WindowFromPoint.restype = wintypes.HWND
        # A HIDDEN window is skipped by WindowFromPoint anyway, so the
        # visibility half is part of the gate -- otherwise it cannot fail.
        centre = window.geometry().center()
        under = user32.WindowFromPoint(POINT(centre.x(), centre.y()))
        under = int(under) if under else 0
        gate("5  the OS hit-tests through the VISIBLE overlay",
             window.isVisible() and under != int(window.winId()),
             "visible={0} hwnd under the point: {1}".format(
                 window.isVisible(), under))
    except Exception as error:
        skip("5  the OS hit-tests through the overlay", str(error))

    gate("6  the dragger context is the current tool",
         cmds.currentCtx() == tool.CONTEXT, cmds.currentCtx())
    press = cmds.draggerContext(tool.CONTEXT, query=True, pressCommand=True)
    gate("7  its command is Python, not MEL",
         "maya_curveview.tool" in (press or "") and "python(" not in
         (press or ""), press)
    gate("8  the previous tool was remembered",
         tool._STATE.previous_tool == entry["tool"],
         "{0!r}".format(tool._STATE.previous_tool))

    # --------------------------------------------------- 9. what is drawn

    cmds.select(sandbox, replace=True)
    tool.refresh()
    scene = window.scene()
    attributes = sorted(drawn.attribute for drawn in scene.curves)
    gate("9  the sandbox's three channels are drawn",
         attributes == ["rotateZ", "scaleX", "translateY"], str(attributes))

    # The Qt event loop does not turn while this script holds the main
    # thread, so the window has never been exposed and `repaint()` is a
    # NO-OP -- measured, paint_count stayed 0. `render()` into an image
    # forces paintEvent synchronously, and that is the half worth proving: a
    # namedtuple field renamed in one module raises in there and Qt
    # swallows it into the Script Editor, leaving the animator with an
    # empty viewport and no error.
    from PySide6 import QtGui
    canvas = QtGui.QImage(window.width(), window.height(),
                          QtGui.QImage.Format_ARGB32)
    canvas.fill(0)
    window.render(canvas)
    raw = bytes(canvas.constBits())
    painted = len(raw) - raw.count(0)
    gate("10 painting a real scene runs and does not raise",
         window.paint_count > 0,
         "paintEvent ran {0}x".format(window.paint_count))
    gate("10b and it actually put ink on the canvas", painted > 0,
         "{0} non-zero bytes of {1}".format(painted, len(raw)))

    cmds.select(clear=True)
    tool.refresh()
    gate("11 nothing selected means no curves",
         window.scene().curves == [] and
         window.scene().message == tool.NO_CURVES)

    cmds.select(sandbox, replace=True)
    tool.refresh()
    scene = window.scene()
    drawn = [d for d in scene.curves if d.attribute == "translateY"][0]
    order = [i for i, d in enumerate(scene.curves)
             if d.attribute == "translateY"][0]
    curve_node = tool._STATE.curves[order].curve

    gate("12 sampling the curve NODE answers values",
         len(drawn.samples) > 50 and
         all(isinstance(v, float) for _t, v in drawn.samples),
         "{0} samples".format(len(drawn.samples)))

    gate("13 the window holds the whole key range",
         drawn.frame.v0 < base and drawn.frame.v1 > base + 25.0,
         "v0={0:.3f} v1={1:.3f} keys {2:.3f}..{3:.3f}".format(
             drawn.frame.v0, drawn.frame.v1, base, base + 25.0))

    # ---------------------------------------------- 14. the pixel mapping

    rect = window.rect_size()
    key = drawn.keys[1]                    # frame 50, the peak
    px, py = mapping.to_pixels(drawn.frame, rect, key[0], key[1])
    back_t, back_v = mapping.to_curve(drawn.frame, rect, px, py)
    gate("14 a key round-trips through the pixel mapping",
         abs(back_t - key[0]) < 1e-9 and abs(back_v - key[1]) < 1e-9,
         "dt={0:.12f} dv={1:.12f}".format(back_t - key[0], back_v - key[1]))

    gate("15 the key lands inside the overlay",
         0 <= px <= rect.width and 0 <= py <= rect.height,
         "({0:.1f}, {1:.1f}) in {2}x{3}".format(px, py, rect.width,
                                                rect.height))

    found = tool.hit_key(scene, rect, px + 2, py - 2)
    gate("16 hit_key finds the key at its own drawn position",
         found == (order, 1), str(found))
    gate("17 and misses it 40 px away",
         tool.hit_key(scene, rect, px + 40, py) is None)

    flipped = mapping.flip_y(rect, py)
    gate("18 flip_y is its own inverse",
         abs(mapping.flip_y(rect, flipped) - py) < 1e-9)

    # ------------------------------------------- 19. Maya's own key select

    tool.select_keys({order: [1]}, "replace")
    chosen = cmds.keyframe(curve_node, query=True, selected=True,
                           timeChange=True) or []
    gate("19 selectKey with an index selects exactly that key",
         chosen == [50.0], str(chosen))
    gate("20 and selected_indices reads it back as a position",
         curves.selected_indices(curve_node) == [1],
         str(curves.selected_indices(curve_node)))

    tool.select_keys({order: [1]}, "toggle")
    gate("21 toggle takes it off again",
         (cmds.keyframe(curve_node, query=True, selected=True,
                        timeChange=True) or []) == [])

    # --------------------------------------------------- 22. moving a key

    tool.select_keys({order: [1]}, "replace")
    before_time = cmds.keyframe(curve_node, query=True, index=(1, 1),
                                timeChange=True)[0]
    before_value = cmds.keyframe(curve_node, query=True, index=(1, 1),
                                 valueChange=True)[0]
    edits.apply_delta(3.0, 1.5)
    after_time = cmds.keyframe(curve_node, query=True, index=(1, 1),
                               timeChange=True)[0]
    after_value = cmds.keyframe(curve_node, query=True, index=(1, 1),
                                valueChange=True)[0]
    gate("22 the relative keyframe edit moves the SELECTED key",
         abs((after_time - before_time) - 3.0) < 1e-9 and
         abs((after_value - before_value) - 1.5) < 1e-9,
         "dt={0:.9f} dv={1:.9f}".format(after_time - before_time,
                                        after_value - before_value))

    edits.apply_delta(-3.0, -1.5)
    gate("23 and it is exactly reversible",
         abs(cmds.keyframe(curve_node, query=True, index=(1, 1),
                           timeChange=True)[0] - before_time) < 1e-9 and
         abs(cmds.keyframe(curve_node, query=True, index=(1, 1),
                           valueChange=True)[0] - before_value) < 1e-9)

    edits.apply_delta(0.0, 0.0)
    gate("24 a zero delta is a no-op",
         abs(cmds.keyframe(curve_node, query=True, index=(1, 1),
                           timeChange=True)[0] - before_time) < 1e-9)

    # ------------------------------------------------- 25. tangent angles

    angles = curves.tangent_angles(curve_node, [1])
    gate("25 tangent angles come back as a pair of floats",
         set(angles) == {1} and len(angles[1]) == 2 and
         all(isinstance(a, float) for a in angles[1]),
         str(angles))

    before_out = angles[1][1]
    edits.set_tangent(curve_node, 1, "out", before_out + 20.0)
    after = curves.tangent_angles(curve_node, [1])[1][1]
    gate("26 setting a tangent angle takes",
         abs(after - (before_out + 20.0)) < 0.5,
         "{0:.4f} -> {1:.4f}".format(before_out, after))
    edits.set_tangent(curve_node, 1, "out", before_out)

    # ------------------------------------------------------ 27. the throttle

    cmds.currentTime(10.0, edit=True)
    stamp = None
    moved = []
    for step in range(100):
        now = 1000.0 + step * 0.0001         # 10 ms of wall clock, all told
        new_stamp = edits.follow_time(20.0 + step, now, stamp,
                                      tool.THROTTLE)
        if new_stamp != stamp:
            moved.append(step)
        stamp = new_stamp
    gate("27 the throttle lets one of 100 calls through",
         len(moved) == 1, "evaluated on call(s) {0}".format(moved))

    # ------------------------------------------- 28. viewport object select

    view = omui2.M3dView.getM3dViewFromModelPanel(panel)
    world = cmds.xform(sandbox, query=True, worldSpace=True,
                       translation=True)
    screen = view.worldToView(om.MPoint(world[0], world[1], world[2]))
    sx, sy = int(screen[0]), int(screen[1])
    print("sandbox projects to screen ({0}, {1})".format(sx, sy))

    # Maya's pick runs through the viewport's own draw pass, so a node that
    # has never been DRAWN cannot be found -- measured: an unrefreshed
    # locator at screen centre picked nothing at all under every
    # adjustment. Trap 14's family. Real use always has a drawn viewport;
    # this run does not, so it asks for one.
    cmds.refresh()

    cmds.select(clear=True)
    tool.select_from_screen(sx, sy, sx, sy, "none")
    picked = cmds.ls(selection=True, long=True) or []
    gate("28 selectFromScreen picks the object under the point",
         sandbox in picked, str(picked))

    tool.select_from_screen(sx, sy, sx, sy, "shift")
    gate("29 shift toggles it back off",
         sandbox not in (cmds.ls(selection=True, long=True) or []),
         str(cmds.ls(selection=True) or []))

    # The positive control for why gate 29's path exists at all: the API's
    # own kXORWithList, in its CLICK form, changes nothing. If this gate
    # ever starts failing, Maya has been fixed and the workaround in
    # `select_from_screen` can be reconsidered.
    cmds.select(sandbox, replace=True)
    om.MGlobal.selectFromScreen(sx, sy, om.MGlobal.kXORWithList,
                                om.MGlobal.kWireframeSelectMethod)
    gate("29b kXORWithList's CLICK form is measured to be a no-op",
         sandbox in (cmds.ls(selection=True, long=True) or []),
         "which is why the pick is a replace and cmds.select does the rest")

    cmds.select(clear=True)
    tool.select_from_screen(sx - 60, sy - 60, sx + 60, sy + 60, "none")
    gate("30 and the box form picks it too",
         sandbox in (cmds.ls(selection=True, long=True) or []),
         str(cmds.ls(selection=True) or []))

    tool.select_from_screen(sx - 60, sy - 60, sx + 60, sy + 60, "ctrl")
    gate("30b ctrl removes it again",
         sandbox not in (cmds.ls(selection=True, long=True) or []))

    # ------------------------------------------------- 31. insert a key

    cmds.select(sandbox, replace=True)
    tool.refresh()
    cmds.currentTime(37.0, edit=True)
    counts_before = cmds.keyframe(curve_node, query=True,
                                  keyframeCount=True)
    tool.insert_key_at_time()
    # insert_key_at_time refreshes, which rebuilds _STATE.curves -- so the
    # order index has to be re-derived before it is used again.
    scene = window.scene()
    order = [i for i, d in enumerate(scene.curves)
             if d.attribute == "translateY"][0]
    curve_node = tool._STATE.curves[order].curve
    counts_after = cmds.keyframe(curve_node, query=True, keyframeCount=True)
    gate("31 insert_key_at_time plants one key per curve",
         counts_after == counts_before + 1,
         "{0} -> {1}".format(counts_before, counts_after))

    times = cmds.keyframe(curve_node, query=True, timeChange=True) or []
    gate("32 the inserted key is at the current frame", 37.0 in times,
         str(times))

    tool.select_keys({order: [times.index(37.0)]}, "replace")
    gone = tool.delete_selected_keys()
    gate("33 delete_selected_keys removes it",
         (cmds.keyframe(curve_node, query=True, keyframeCount=True)
          == counts_before), gone)
    # `cutKey(clear=True)` answers 0 even when it worked, so the count is
    # taken before the cut -- and the status line has to say 1, not 0.
    gate("33b and it reports the key it actually removed", "1 key" in gone,
         gone)

    # ---------------------------------------------------- 34. normalise

    was = tool._normalise()
    tool.set_normalise(True)
    scene = window.scene()
    frames = set(drawn.frame for drawn in scene.curves)
    gate("34 normalise gives each curve its own Y window",
         len(frames) == len(scene.curves) and len(scene.curves) > 1,
         "{0} frames for {1} curves".format(len(frames),
                                            len(scene.curves)))
    tool.set_normalise(False)
    frames = set(drawn.frame for drawn in window.scene().curves)
    gate("35 and the shared axis is one window for all of them",
         len(frames) == 1, "{0} frame(s)".format(len(frames)))
    tool.set_normalise(bool(was))

    # ------------------------------------------------ 36. the mode goes down

    message = tool.disable()
    gate("36 disable() reports the mode off", "OFF" in message, message)
    gate("37 the window is gone", tool.live_overlay() is None)
    gate("38 the dragger context is deleted",
         not cmds.draggerContext(tool.CONTEXT, exists=True))
    gate("39 the previous tool is restored",
         cmds.currentCtx() == entry["tool"], cmds.currentCtx())
    gate("40 a second disable is refused, not a traceback",
         "already off" in tool.disable())

except Exception:
    print("")
    print("THE RUN ITSELF FAILED")
    traceback.print_exc()
    FAILED.append("the run")

# ---------------------------------------------------------------- teardown
#
# Every step guarded on its own: a failure in one must not take the rest of
# the restore with it (CLAUDE.md trap 42).

print("")
print("--- teardown ---")

try:
    if tool.is_on():
        tool.disable()
        print("overlay taken down")
except Exception as error:
    print("overlay teardown failed: {0}".format(error))

try:
    if cmds.draggerContext(tool.CONTEXT, exists=True):
        cmds.deleteUI(tool.CONTEXT)
        print("context deleted")
except Exception as error:
    print("context teardown failed: {0}".format(error))

for uuid in reversed(CREATED):
    try:
        found = cmds.ls(uuid, long=True) or []
        if found:
            cmds.delete(found[0])
    except Exception as error:
        print("could not delete {0}: {1}".format(uuid, error))
print("{0} created node(s) removed by UUID".format(len(CREATED)))

for step, action in (
        ("selection", lambda: cmds.select(
            [n for n in entry["selection"] if cmds.objExists(n)],
            replace=True) if entry["selection"] else cmds.select(clear=True)),
        ("time", lambda: cmds.currentTime(entry["time"], edit=True)),
        ("autoKey", lambda: cmds.autoKeyframe(state=entry["autokey"])),
        ("range", lambda: cmds.playbackOptions(minTime=entry["min"],
                                               maxTime=entry["max"])),
        ("tool", lambda: cmds.setToolTo(entry["tool"]))):
    try:
        action()
    except Exception as error:
        print("could not restore {0}: {1}".format(step, error))

try:
    if entry["normalise"] is None:
        if cmds.optionVar(exists=tool.NORMALISE_VAR):
            cmds.optionVar(remove=tool.NORMALISE_VAR)
    else:
        cmds.optionVar(intValue=(tool.NORMALISE_VAR,
                                 int(entry["normalise"])))
except Exception as error:
    print("could not restore the optionVar: {0}".format(error))

print("")
print("exit state: selection={0} time={1} autokey={2} range={3}..{4} "
      "tool={5}".format(len(cmds.ls(selection=True) or []),
                        cmds.currentTime(query=True),
                        cmds.autoKeyframe(query=True, state=True),
                        cmds.playbackOptions(query=True, min=True),
                        cmds.playbackOptions(query=True, max=True),
                        cmds.currentCtx()))
print("")
print("=" * 72)
print("{0} of {1} gates failed{2}".format(
    len(FAILED), len(FAILED) + len(PASSED),
    "   ({0} skipped)".format(len(SKIPPED)) if SKIPPED else ""))
for name in FAILED:
    print("   FAILED: " + name)
print("=" * 72)
