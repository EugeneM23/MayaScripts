"""Our CAT for Maya - a standalone tool (drop this file into a viewport, or exec it).

Select any part of a skeleton (Manny, Creep, Orc D, a Mixamo or UE4 skeleton...), pick a preset,
press Apply: a walk / run cycle is synthesised from the knobs (catmodel.py, CATMotion's idea) and keyed
on the bones. Moving a slider and letting it go keys the same skeleton again. Design:
docs/superpowers/specs/2026-10-23-catwalk-design.md.

Uses the plugin's skeleton reader and curve writer (maya_walk.scene): the installed copy when it is
importable, else this repository's SkeldarAnim."""

import importlib
import json
import math
import os
import sys

import maya.cmds as cmds

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else ""
REPO_PLUGIN = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", "SkeldarAnim")) if HERE else ""
WINDOW = "skeldarCatWindow"
MARKER = "skeldarCatWalk"
KNOBS_VAR = "skeldarCat_knobs"
PRESET_VAR = "skeldarCat_preset"
STATUS = "skeldarCatStatus"


class Refusal(Exception):
    pass


def _modules():
    """(catmodel, maya_walk.scene) - the plugin found or put on sys.path."""
    if HERE and HERE not in sys.path:
        sys.path.insert(0, HERE)
    try:
        import maya_walk.scene                       # noqa: F401
    except ImportError:
        if REPO_PLUGIN and os.path.isdir(REPO_PLUGIN):
            sys.path.insert(0, REPO_PLUGIN)
    import catmodel
    from maya_walk import scene
    return catmodel, scene


def _state():
    if not hasattr(sys, "_skeldar_cat"):
        sys._skeldar_cat = {"target": None}
    return sys._skeldar_cat


def _fps():
    return float(_modules()[1]._fps())


# ---- knobs memory ----

def remembered():
    """The knobs last set in this tool, else the Walk preset (the default walk)."""
    cm = _modules()[0]
    data = None
    if cmds.optionVar(exists=KNOBS_VAR):
        try:
            data = json.loads(cmds.optionVar(query=KNOBS_VAR))
        except ValueError:
            data = None
    if not isinstance(data, dict):
        return cm.preset("Walk", _fps())
    base = cm.preset("Walk", _fps())
    base.update((k, v) for k, v in data.items() if k in cm.DEFAULTS)
    return cm.knobs(base)


def remember(knobs):
    cmds.optionVar(stringValue=(KNOBS_VAR, json.dumps(knobs)))


# ---- the target ----

def selected_root():
    scene = _modules()[1]
    for node in cmds.ls(selection=True, long=True) or []:
        root = scene.skeleton_root_of(node)
        if root:
            return root
    return None


def _driven(path):
    """What drives the bone's rotate other than keys and layers, or None."""
    for ch in ("rotateX", "rotateY", "rotateZ"):
        src = cmds.listConnections(path + "." + ch, source=True, destination=False, skipConversionNodes=True) or []
        for node in src:
            kind = cmds.nodeType(node)
            if not kind.startswith(("animCurve", "animBlendNode")):
                return node
    return None


def _read(root):
    cm, scene = _modules()
    bones, note = scene.read_bones(root)
    skel = cm.Skeleton(bones)
    driver = _driven(bones[skel.pelvis]["path"])
    if driver:
        raise Refusal("%s is driven by %s - a rig's game skeleton; select a bare skeleton"
                      % (bones[skel.pelvis]["path"].split("|")[-1], driver))
    return bones, skel, note


def _memo(root):
    if cmds.attributeQuery(MARKER, node=root, exists=True):
        try:
            return json.loads(cmds.getAttr(root + "." + MARKER) or "{}")
        except ValueError:
            return {}
    return {}


def _set_memo(root, memo):
    if not cmds.attributeQuery(MARKER, node=root, exists=True):
        cmds.addAttr(root, longName=MARKER, dataType="string")
    cmds.setAttr(root + "." + MARKER, json.dumps(memo), type="string")


def place_of(skel, bones):
    """Where the character stands now against its rest: a turn about up and a move on the floor
    (4x4, rows), read off the top joint at the current frame."""
    import numpy as np
    cm = _modules()[0]
    top = skel.order[0]
    rest = skel.rest[top]
    now = np.array(bones[top]["world"], dtype=float).reshape(4, 4)
    relative = np.linalg.inv(rest[:3, :3]) @ now[:3, :3]
    facing = cm.flat(skel.fwd @ relative)
    yaw = 0.0 if np.linalg.norm(facing) < 1e-6 else math.degrees(
        math.atan2(float(np.dot(np.cross(skel.fwd, facing), cm.UP)), float(np.dot(skel.fwd, facing))))
    q = cm.rot(cm.UP, yaw)
    out = np.eye(4)
    out[:3, :3] = q.T
    moved = rest[3, :3] @ q.T
    out[3, :3] = cm.flat(now[3, :3] - moved)
    return out


# ---- the press ----

def apply(root=None, given=None, new_place=False, start=None):
    """Key the cycle on the skeleton of `root` (else the selection, else the last target), from frame
    `start` when given (else where it was keyed before, else the playback start). Answers the status line."""
    import numpy as np
    import maya.api.OpenMaya as om
    cm, scene = _modules()
    state = _state()
    root = root or selected_root() or state.get("target")
    if not root or not cmds.objExists(root):
        raise Refusal("select any part of a skeleton")
    if cmds.currentUnit(query=True, linear=True) != "cm":
        raise Refusal("the scene is not in centimetres")
    knobs = cm.knobs(given if given is not None else remembered())
    bones, skel, note = _read(root)
    memo = _memo(root)
    if memo.get("place") and not new_place:
        place = np.array(memo["place"], dtype=float).reshape(4, 4)
        start = int(memo.get("start", 0)) if start is None else start
    else:
        place = place_of(skel, bones)
        start = int(cmds.playbackOptions(query=True, minTime=True)) if start is None else start
    if start is None:
        start = int(memo.get("start", 0))
    fps = _fps()
    cycle = cm.generate(skel, knobs, fps, place=place)
    frames = [dict((leaf, om.MMatrix([float(x) for x in m.flatten()])) for leaf, m in world.items())
              for world in cycle.frames]
    written = [leaf for leaf in skel.order if leaf in bones]
    translated = set(x for x in (skel.root, skel.pelvis) if x) | set(skel.helpers)
    values, static = scene.channel_values(bones, frames, written, translated)
    cmds.undoInfo(openChunk=True, chunkName="skeldarCat")
    try:
        count, held = scene.write_curves(values, static, start)
        _set_memo(root, {"place": [float(x) for x in place.flatten()], "start": start, "knobs": knobs})
        end = start + cycle.info["frames"]
        cmds.playbackOptions(minTime=start, maxTime=end - 1, animationStartTime=min(start, cmds.playbackOptions(
            query=True, animationStartTime=True)), animationEndTime=max(end, cmds.playbackOptions(
                query=True, animationEndTime=True)))
    finally:
        cmds.undoInfo(closeChunk=True)
    state["target"] = root
    info = cycle.info
    line = ("%s: %s cycle %d fr (%d-%d), %.0f cm/s, step %.0f cm | %s | drop up to %.1f cm%s%s" % (
        root.split("|")[-1].split(":")[-1], "spot" if knobs["on_spot"] >= 0.5 else "line", info["frames"], start,
        end, info["speed"], info["stride"],
        "flight %d fr" % info["flight"] if info["flight"] else "both feet down %d fr" % info["double"],
        info["drop"], " | " + note if note else "",
        " | left to their drivers: " + ", ".join(sorted(held)) if held else ""))
    return line


# ---- matching a reference ----

def read_cycle(root):
    """(Skeleton, frames) of the keyed cycle on the skeleton of `root`: every bone's world on every whole
    frame of its keys (the last frame the first moved by the travel)."""
    import numpy as np
    cm, scene = _modules()
    bones, _ = scene.read_bones(root)
    skel = cm.Skeleton(bones)
    paths = [bones[leaf]["path"] for leaf in skel.order]
    times = cmds.keyframe(paths, query=True, timeChange=True) or []
    if not times:
        raise Refusal("%s carries no keys - select a skeleton playing a walk cycle" % root.split("|")[-1])
    a, b = int(round(min(times))), int(round(max(times)))
    if b - a < 8:
        raise Refusal("%s: keys over %d frames only - a cycle needs at least 8" % (root.split("|")[-1], b - a))
    frames = []
    for t in range(a, b + 1):
        frames.append(dict((leaf, np.array(cmds.getAttr(bones[leaf]["path"] + ".worldMatrix[0]", time=t),
                                           dtype=float).reshape(4, 4)) for leaf in skel.order))
    return skel, frames, (a, b)


def match(reference=None, target=None):
    """The knobs fitted to the cycle on `reference` (else the selection), remembered and shown; the last
    target skeleton (else `target`) keyed with them. Answers the status line."""
    import numpy as np
    cm, _ = _modules()
    import catmatch
    importlib.reload(catmatch)
    reference = reference or selected_root()
    if not reference:
        raise Refusal("select any part of the reference skeleton")
    target = target or _state().get("target")
    if target and target == reference:
        raise Refusal("%s is the skeleton our CAT keys - select the reference walk (the other skeleton) "
                      "and press Match again" % reference.split("|")[-1].split(":")[-1])
    skel, frames, (a, b) = read_cycle(reference)
    seam = max(float(np.abs(frames[-1][l][:3, :3] - frames[0][l][:3, :3]).max()) for l in skel.order)
    knobs, ref, ours, rows = catmatch.fit(skel, frames, _fps(), rounds=30)
    pose = catmatch.compare(skel, frames, cm.generate(skel, knobs, _fps()).frames, ref,
                            catmatch.measure(skel, cm.generate(skel, knobs, _fps()).frames))
    # in step with the reference: travelling as it does, from its first frame, its left foot landing on
    # the same frame
    knobs["cycle_offset"] = float(-ref["left_contact"])
    remember(knobs)
    _show_preset(CUSTOM)
    _fill(knobs)
    line = ("matched %s (%d-%d, %d fr, %.0f cm a step): pose off by %s" % (
        reference.split("|")[-1].split(":")[-1], a, b, ref["frames"], ref["stride"] * skel.leg,
        ", ".join("%s %.0f" % (g, v) for g, v in pose.items())))
    if seam > 0.02:
        line += " | its last frame is not its first turned on: matched as if it were a cycle"
    if target and cmds.objExists(target):
        line += " | " + apply(target, knobs, start=a)
    else:
        line += " | select your skeleton and press Apply"
    return line


# ---- the window ----

def _say(text):
    if cmds.text(STATUS, exists=True):
        cmds.text(STATUS, edit=True, label=text)
    print("Skeldar CAT: " + text)


def _run(fn, *args):
    try:
        _say(fn(*args))
    except Refusal as exc:
        _say(str(exc))
    except Exception as exc:                          # the line, never the Script Editor alone
        import traceback
        traceback.print_exc()
        _say("failed: %s" % exc)


def _rekey():
    if _state().get("target") and cmds.objExists(_state()["target"]):
        _run(apply, _state()["target"])
    else:
        _say("Set for the next Apply.")


def _quiet():
    """True while the window is being filled by code: a control set by code may fire its command."""
    return _state().get("quiet", False)


def _knob_changed(name, value):
    if _quiet():
        return
    knobs = remembered()
    knobs[name] = float(value)
    remember(knobs)
    _rekey()


def _fill(knobs):
    cm = _modules()[0]
    _state()["quiet"] = True
    try:
        for name, *_ in cm.KNOBS:
            control = "skeldarCat_" + name
            if name == "on_spot":
                if cmds.radioButtonGrp("skeldarCatMode", exists=True):
                    cmds.radioButtonGrp("skeldarCatMode", edit=True, select=2 if knobs[name] < 0.5 else 1)
            elif cmds.floatSliderGrp(control, exists=True):
                cmds.floatSliderGrp(control, edit=True, value=knobs[name])
    finally:
        _state()["quiet"] = False


def _preset_chosen(name):
    if _quiet() or name == CUSTOM:
        return
    cm = _modules()[0]
    cmds.optionVar(stringValue=(PRESET_VAR, name))
    knobs = cm.preset(name, _fps())
    knobs["on_spot"] = remembered()["on_spot"]
    remember(knobs)
    _fill(knobs)
    _rekey()


def _show_preset(name):
    """The preset list showing `name`, without it counting as a choice."""
    cmds.optionVar(stringValue=(PRESET_VAR, name))
    if cmds.optionMenu("skeldarCatPreset", exists=True):
        _state()["quiet"] = True
        try:
            cmds.optionMenu("skeldarCatPreset", edit=True, value=name)
        finally:
            _state()["quiet"] = False


def reset(target=None):
    """Every knob back to the default walk (the Walk preset) - the mode, on the spot or along a line, kept -
    shown in the window and keyed on the last skeleton (else `target`). Answers the status line."""
    cm = _modules()[0]
    knobs = cm.preset("Walk", _fps())
    knobs["on_spot"] = remembered()["on_spot"]
    remember(knobs)
    _show_preset("Walk")
    _fill(knobs)
    target = target or _state().get("target")
    if target and cmds.objExists(target):
        return "Reset to the default walk | " + apply(target, knobs)
    return "Reset to the default walk - select a skeleton and press Apply"


def _apply_pressed(*_):
    _run(apply, selected_root() or _state().get("target"))


def _new_place(*_):
    _run(apply, selected_root() or _state().get("target"), None, True)


def show():
    cm = _modules()[0]
    if cmds.window(WINDOW, exists=True):
        cmds.deleteUI(WINDOW)
    if cmds.windowPref(WINDOW, exists=True):
        cmds.windowPref(WINDOW, remove=True)
    knobs = remembered()
    _state()["quiet"] = True                       # nothing the build sets is a press
    try:
        _build(cm, knobs)
    finally:
        _state()["quiet"] = False
    cmds.showWindow(WINDOW)


CUSTOM = "(custom)"


def _build(cm, knobs):
    cmds.window(WINDOW, title="Skeldar CAT - procedural walk", widthHeight=(420, 760), sizeable=True)
    cmds.scrollLayout(childResizable=True)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=4)
    cmds.text(label="Select any part of a skeleton, pick a preset, press Apply.\n"
                    "A slider let go keys the same skeleton again.", align="left", height=32)
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1, columnAttach2=("both", "both"))
    cmds.optionMenu("skeldarCatPreset", label="Preset", changeCommand=_preset_chosen)
    cmds.menuItem(label=CUSTOM)
    for name in cm.PRESET_ORDER:
        cmds.menuItem(label=name)
    if cmds.optionVar(exists=PRESET_VAR) and cmds.optionVar(query=PRESET_VAR) in cm.PRESET_ORDER:
        cmds.optionMenu("skeldarCatPreset", edit=True, value=cmds.optionVar(query=PRESET_VAR))
    cmds.button("skeldarCatReset", label="Reset", width=70,
                annotation="Every knob back to the default walk (the mode is kept) and the skeleton keyed again",
                command=lambda *_: _run(reset))
    cmds.setParent("..")
    cmds.radioButtonGrp("skeldarCatMode", label="Mode", labelArray2=("On spot", "Along a line"),
                        numberOfRadioButtons=2, columnWidth3=(80, 90, 110),
                        select=1 if knobs["on_spot"] >= 0.5 else 2,
                        changeCommand=lambda *_: _knob_changed(
                            "on_spot", 1.0 if cmds.radioButtonGrp("skeldarCatMode", query=True, select=True) == 1
                            else 0.0))
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1, columnAttach2=("both", "both"))
    cmds.button(label="Apply to selection", height=30, backgroundColor=(0.88, 0.48, 0.21), command=_apply_pressed)
    cmds.button(label="Here again", height=30, annotation="Key it again starting where the character stands now",
                command=_new_place)
    cmds.setParent("..")
    cmds.button(label="Match reference (select a skeleton playing a walk)", height=26,
                annotation="Reads the cycle on the selected skeleton, fits every knob to it and keys your last "
                           "skeleton with them",
                command=lambda *_: _run(match))
    for group in cm.GROUPS:
        cmds.frameLayout(label=group, collapsable=True, collapse=group not in ("Timing",), marginWidth=4)
        cmds.columnLayout(adjustableColumn=True)
        for name, default, lo, hi, grp, label in cm.KNOBS:
            if grp != group or name == "on_spot":
                continue
            step = 0.5 if name == "step_time" else (1.0 if hi - lo > 10 else 0.01)
            cmds.floatSliderGrp("skeldarCat_" + name, label=label, field=True, minValue=lo, maxValue=hi,
                                fieldMinValue=lo, fieldMaxValue=hi, value=knobs[name], step=step,
                                precision=1 if step >= 0.5 else 3,
                                columnWidth3=(130, 60, 180),
                                changeCommand=lambda value, n=name: _knob_changed(n, value))
        cmds.setParent("..")
        cmds.setParent("..")
    cmds.text(STATUS, label="", align="left", wordWrap=True, height=60)


def onMayaDroppedPythonFile(*_):
    """Maya's drop handler: the modules read again (a re-dropped file must not run the old code), then
    the window."""
    if HERE and HERE not in sys.path:
        sys.path.insert(0, HERE)
    import catmodel
    importlib.reload(catmodel)
    import catmatch
    importlib.reload(catmatch)
    me = sys.modules.get(__name__)
    if me is not None and getattr(me, "__file__", None):
        importlib.reload(me)                          # trap 220: a re-dropped file keeps the old module
    sys.modules[__name__].show()


if __name__ == "__main__":
    show()
