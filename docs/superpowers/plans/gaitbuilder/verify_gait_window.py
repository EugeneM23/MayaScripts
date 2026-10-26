"""The Gait Builder window driven in a DISPOSABLE GUI Maya (scratch MAYA_APP_DIR, its own port), one phase a send:
a runner execs this file with PHASE = "a".."g" in its globals, a separate send for each (a UI change and its read
need the event loop between them). A grp control's -q -changeCommand answers None in Maya, so a slider or a
radio group is fired through the handler its command calls (the lambda in skeldar_gait._build)."""
import json
import os
import sys

import maya.cmds as cmds

REPO = r"C:/!!!Work/MayaScripts"
for p in (REPO + "/SkeldarAnim", REPO + "/docs/superpowers/plans/gaitbuilder"):
    if p not in sys.path:
        sys.path.insert(0, p)
HERE = os.environ.get("TEMP", ".")          # where the window's picture goes

if PHASE == "a":                   # the tool as it stands in the repo now
    for name in ("skeldar_gait", "aspects", "gaitload", "gaitmodel", "gaitgen"):
        sys.modules.pop(name, None)

import numpy as np                 # noqa: E402
import skeldar_gait as tool        # noqa: E402

G = getattr(sys, "_gait_gui", None)
if G is None:
    G = sys._gait_gui = {"failed": [], "count": 0}


def gate(ok, text):
    G["count"] += 1
    print("gate %2d %s  %s" % (G["count"], "ok  " if ok else "FAIL", text))
    if not ok:
        G["failed"].append(text)


def world(path, t):
    return np.array(cmds.getAttr(path + ".worldMatrix[0]", time=t)).reshape(4, 4)


def status():
    return cmds.text(tool.STATUS, query=True, label=True) if cmds.text(tool.STATUS, exists=True) else None


def pelvis_path():
    from maya_walk import scene as ws
    return ws.read_bones(G["root"])[0]["pelvis"]["path"]


def root_path():
    from maya_walk import scene as ws
    return ws.read_bones(G["root"])[0]["root"]["path"]


def travel():
    memo = tool._memo(G["root"])
    start = int(memo["start"])
    end = int(cmds.playbackOptions(query=True, maxTime=True)) + 1
    a, b = world(root_path(), start)[3, :3], world(root_path(), end)[3, :3]
    return float(np.linalg.norm((b - a)[[0, 2]])), end - start


def command_of(kind, control, flag):
    try:
        return getattr(cmds, kind)(control, query=True, **{flag: True})
    except Exception as exc:
        return "error: %s" % exc


def fire(kind, control, handler, *args):
    """Run the control's own command where Maya answers it, else the handler that command calls."""
    cmd = command_of(kind, control, "changeCommand")
    if callable(cmd):
        cmd(*args)
    else:
        handler(*args)


def phase_a():
    G["failed"], G["count"] = [], 0
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")
    cmds.playbackOptions(minTime=1, maxTime=120)
    before = set(cmds.ls(type="joint", long=True) or [])
    cmds.file(REPO + "/SkeldarAnim/assets/Manny_Skeleton.ma", i=True, namespace="manny", ignoreVersion=True,
              preserveReferences=False)
    new = set(cmds.ls(type="joint", long=True) or []) - before
    def is_top(j):
        above = cmds.listRelatives(j, parent=True, fullPath=True)
        return not above or cmds.nodeType(above[0]) != "joint"
    tops = [j for j in new if is_top(j)]
    G["root"] = min(tops, key=lambda p: (p.count("|"), p))
    cmds.optionVar(stringValue=(tool.STATE_VAR, json.dumps({"source": "cat:Walk"})))
    cmds.select(G["root"])
    tool.show()
    asp = tool._modules()[1]
    gate(cmds.window(tool.WINDOW, exists=True), "the window opens")
    missing = [k.name for k in asp.KNOBS
               if not (cmds.floatSliderGrp("skeldarGait_" + k.name, exists=True)
                       or cmds.checkBox("skeldarGait_" + k.name, exists=True))]
    gate(not missing, "every knob has its control (%d knobs; missing %s)" % (len(asp.KNOBS), missing))
    labels = cmds.optionMenu("skeldarGaitSource", query=True, itemListShort=True) or []
    items = [cmds.menuItem(i, query=True, label=True) for i in labels]
    gate("CAT Walk" in items and "CAT Run" in items, "the source menu lists the CAT presets (%s)" % items)
    gate(cmds.optionMenu("skeldarGaitSource", query=True, value=True) == "CAT Walk", "it shows CAT Walk")
    speed = cmds.floatSliderGrp("skeldarGait_speed", query=True, value=True)
    base = tool._base(tool._source(tool.settings()), tool.settings())
    gate(abs(speed - base["speed"]) < 0.01, "the Speed slider stands at the walk's own %.3f m/s (%.3f)"
         % (base["speed"], speed))
    lo = cmds.floatSliderGrp("skeldarGait_step", query=True, minValue=True)
    hi = cmds.floatSliderGrp("skeldarGait_step", query=True, maxValue=True)
    print("   Step slider %.1f..%.1f" % (lo, hi))
    G["apply_cmd"] = None
    for b in cmds.lsUI(type="button") or []:
        if cmds.button(b, query=True, label=True) == "Apply to selection":
            G["apply_cmd"] = cmds.button(b, query=True, command=True)
    gate(callable(G["apply_cmd"]), "the Apply button carries its command (%r)" % (G["apply_cmd"],))


def phase_b():
    cmds.select(G["root"])
    G["apply_cmd"]()
    line = status()
    gate(line and line.startswith("CAT Walk on root"), "Apply keys it: %s" % line)
    curves = cmds.listConnections(pelvis_path() + ".rotateY", source=True, destination=False) or []
    gate(bool(curves), "the pelvis is keyed (%s)" % curves)
    G["walk_travel"] = travel()
    print("   travel %.1f cm over %d frames" % G["walk_travel"])


def phase_c():
    # two decimals: the slider shows a step under 0.1 at precision 2 (skeldar_gait._build)
    asked = round(cmds.floatSliderGrp("skeldarGait_speed", query=True, value=True) * 1.2, 2)
    G["asked_speed"] = asked
    cmds.floatSliderGrp("skeldarGait_speed", edit=True, value=asked)
    took = cmds.floatSliderGrp("skeldarGait_speed", query=True, value=True)
    gate(abs(took - asked) < 1e-6, "the Speed slider takes %.2f (%.3f)" % (asked, took))
    fire("floatSliderGrp", "skeldarGait_speed", tool._knob_changed, "speed", asked)


def phase_d():
    line = status()
    gate(line and "CAT Walk on root" in line, "the slider let go keys it again: %s" % line)
    dist, frames = travel()
    fps = 30.0
    gate(abs(dist / (frames / fps) / 100.0 - G["asked_speed"]) <= 0.05 * G["asked_speed"],
         "the keyed speed %.3f m/s against %.3f asked" % (dist / (frames / fps) / 100.0, G["asked_speed"]))
    step = cmds.floatSliderGrp("skeldarGait_step", query=True, value=True)
    gate(abs(step - dist / 2.0) < 1.0, "the Step slider follows the speed: %.1f cm (keyed %.1f)" % (step, dist / 2.0))
    # Left alone
    cmds.radioButtonGrp("skeldarGaitSide", edit=True, select=2)
    tool._side_changed("l")
    own = cmds.floatSliderGrp("skeldarGait_arm_swing", query=True, value=True)
    G["left_swing"] = own + 8.0
    cmds.floatSliderGrp("skeldarGait_arm_swing", edit=True, value=own + 8.0)
    fire("floatSliderGrp", "skeldarGait_arm_swing", tool._knob_changed, "arm_swing", own + 8.0)


def phase_e():
    gait = tool.settings()["gait"]
    gate("arm_swing_l" in gait and "arm_swing_r" not in gait,
         "Left sets the left arm alone (%s)" % dict((k, round(v, 2)) for k, v in gait.items()))
    cmds.radioButtonGrp("skeldarGaitSide", edit=True, select=1)
    tool._side_changed("both")
    label = cmds.floatSliderGrp("skeldarGait_arm_swing", query=True, label=True)
    gate(label.endswith("*"), "Both marks the knob whose sides differ: %r" % label)
    # another source through the menu
    cmds.optionMenu("skeldarGaitSource", edit=True, value="CAT Run")
    fire("optionMenu", "skeldarGaitSource", tool._source_chosen, "CAT Run")


def phase_f():
    line = status()
    gate(line and line.startswith("CAT Run on root"), "the menu's CAT Run keys the same skeleton: %s" % line)
    gait = tool.settings()["gait"]
    gate("speed" not in gait and "arm_swing_l" not in gait,
         "a new walk starts at its own values (measured knobs dropped: %s)" % sorted(gait))
    dist, frames = travel()
    gate(frames == 15, "the run's cycle: %d frames" % frames)
    speed = cmds.floatSliderGrp("skeldarGait_speed", query=True, value=True)
    print("   Run speed slider %.2f" % speed)
    for b in cmds.lsUI(type="button") or []:
        if cmds.button(b, query=True, label=True) == "Reset":
            cmds.button(b, query=True, command=True)()
    line = status()
    gate(line and line.startswith("Reset to the walk's own"), "Reset: %s" % line)
    # CAT Run's own feet lift 55.214 / 55.214 cm (they differ in the fifth digit): one value, no mark
    label = cmds.floatSliderGrp("skeldarGait_lift", query=True, label=True)
    gate(not label.endswith("*"), "a knob whose sides agree at its shown digits is not marked: %r" % label)


def phase_g():
    # the picture, from DWM's copy of the window (no Qt grab of Maya's widgets: trap 134)
    from maya import OpenMayaUI as omui
    from shiboken6 import wrapInstance
    from PySide6 import QtWidgets, QtGui
    from maya_graphoverlay import winstyle
    w = wrapInstance(int(omui.MQtUtil.findWindow(tool.WINDOW)), QtWidgets.QWidget)
    w.raise_()
    w.activateWindow()
    QtWidgets.QApplication.processEvents()
    hwnd = int(w.winId())
    ratio = w.devicePixelRatioF()
    width, height = int(w.width() * ratio), int(w.height() * ratio)
    data = winstyle.capture(hwnd, width, height)
    if data:
        img = QtGui.QImage(data, width, height, QtGui.QImage.Format_RGB32).copy()
        img.save(HERE + "/gait_window.png")
    gate(bool(data), "the window photographed (%dx%d)" % (width, height))
    # dropped again: the walked skeleton's memo read back into the window
    cmds.select(G["root"])
    tool.onMayaDroppedPythonFile()
    import skeldar_gait as again
    gate(cmds.window(again.WINDOW, exists=True), "the window again after a re-drop")
    gate(cmds.optionMenu("skeldarGaitSource", query=True, value=True) == "CAT Run",
         "the walked skeleton's source read back")
    print("%d gates, %d failed" % (G["count"], len(G["failed"])))


globals()["phase_" + PHASE]()
