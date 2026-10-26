"""Gait Builder for Maya - a standalone tool (drop this file into a viewport, or exec it).

Walk Builder's engine (the clip, planted feet, balance, inertia, poses) with our CAT's way of steering it: every
knob is a measured aspect of the walk in its unit - m/s, cm, degrees, % of a cycle - and starts at the walk's own
value; untouched, the walk stays as it is. Pick a source (a Walk cycles card, a saved walk, a CAT preset),
select any part of a skeleton, press Apply; a slider let go keys the same skeleton again.
Design: docs/superpowers/specs/2026-10-26-gait-builder-design.md.

Uses the plugin's maya_walk (sources, the skeleton reader, the retarget, the curve writer) and maya_poselib (the
pose cards): the installed copy when importable, else this repository's SkeldarAnim."""

import importlib
import json
import os
import sys
import time

import maya.cmds as cmds

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else ""
REPO_PLUGIN = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", "SkeldarAnim")) if HERE else ""
WINDOW = "skeldarGaitWindow"
MARKER = "skeldarGait"
STATE_VAR = "skeldarGait_state"
STATUS = "skeldarGaitStatus"
BODY = "skeldarGaitBody"
PARTS = ("torso", "pelvis", "knees", "arms", "feet")
SIDE_MODES = (("both", "Both"), ("l", "Left"), ("r", "Right"))
OPEN_GROUPS = ("Main",)
VERSION = 1


class Refusal(Exception):
    pass


def _modules():
    """(gaitload, aspects, maya_walk.scene, maya_walk.target, maya_walk.pose) - the plugin found or put on
    sys.path, this folder first."""
    if HERE and HERE not in sys.path:
        sys.path.insert(0, HERE)
    try:
        import maya_walk.scene                       # noqa: F401
    except ImportError:
        if REPO_PLUGIN and os.path.isdir(REPO_PLUGIN):
            sys.path.insert(0, REPO_PLUGIN)
    import gaitload
    import aspects
    from maya_walk import scene, target, pose
    return gaitload, aspects, scene, target, pose


def _state():
    if not hasattr(sys, "_skeldar_gait"):
        sys._skeldar_gait = {"target": None, "quiet": False, "poses": {}}
    return sys._skeldar_gait


def _fps():
    return float(_modules()[2]._fps())


# ---- what the window holds (remembered) ----

def settings():
    """{"source", "pose", "share", "parts", "side", "gait", "clean"} last set here (defaults: the first Walk cycles
    card or the CAT Walk, no pose)."""
    data = None
    if cmds.optionVar(exists=STATE_VAR):
        try:
            data = json.loads(cmds.optionVar(query=STATE_VAR))
        except ValueError:
            data = None
    if not isinstance(data, dict):
        data = {}
    out = {"source": data.get("source") or "cat:Walk", "pose": data.get("pose") or "", "share": float(data.get("share", 1.0)),
           "parts": list(data.get("parts") or PARTS), "side": data.get("side") or "both",
           "gait": dict(data.get("gait") or {}), "clean": dict(data.get("clean") or {})}
    return out


def remember(state):
    cmds.optionVar(stringValue=(STATE_VAR, json.dumps(state)))


# ---- sources and poses ----

def sources():
    """[(key, label)]: the Pose Library's Walk cycles cards, the saved walks, the CAT presets."""
    gaitload, _, scene, _, _ = _modules()
    import gaitgen
    out = []
    try:
        from maya_poselib import store
        from maya_walk import cards
        root = cards.library_root(cmds)
        for card in store.cards(root, cards.WALK_FOLDER, recursive=True)[0]:
            path = card.path
            if str(path).endswith(".anim"):
                rel = cards.relative(path, root)
                out.append(("card:" + rel, gaitload.label_of("card:" + rel)))
    except Exception:                                 # no library: the other sources still list
        pass
    try:
        out += [(name, name) for name in scene.walk_names()]
    except Exception:
        pass
    out += [("cat:" + name, "CAT " + name) for name in gaitgen.PRESETS]
    return out


def pose_cards():
    """[(rel, label)] of the Pose Library's pose cards (not animations)."""
    out = []
    try:
        from maya_poselib import store
        from maya_walk import cards
        root = cards.library_root(cmds)
        for card in store.cards(root, "", recursive=True)[0]:
            path = card.path
            if str(path).endswith(".pose"):
                rel = cards.relative(path, root)
                out.append((rel, os.path.splitext(rel)[0]))
    except Exception:
        pass
    return sorted(out, key=lambda r: r[1].lower())


def _source(state):
    gaitload = _modules()[0]
    return gaitload.load(state["source"], state["clean"], _fps())


def _pose(source, state, root=None):
    """The pose carried onto the source's walk, filtered to its parts (None without one)."""
    if not state["pose"] or state["share"] <= 0.0:
        return None
    _, _, scene, target, pose = _modules()
    import gaitmodel
    key = (id(source), state["pose"])
    kept = _state()["poses"]
    if key not in kept:
        _, bones, note, _ = scene.card_pose(state["pose"], None, root)
        if bones is None:
            raise Refusal(note or "the pose card %s cannot be read" % state["pose"])
        kept.clear()
        kept[key] = pose.prepare(source.walk, source.statics, bones, gaitmodel, target)
    return pose.filtered(kept[key], tuple(state["parts"]))


# ---- the target ----

def selected_root():
    scene = _modules()[2]
    for node in cmds.ls(selection=True, long=True) or []:
        root = scene.skeleton_root_of(node)
        if root:
            return root
    return None


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


def _driven(path):
    for ch in ("rotateX", "rotateY", "rotateZ"):
        for node in cmds.listConnections(path + "." + ch, source=True, destination=False,
                                         skipConversionNodes=True) or []:
            if not cmds.nodeType(node).startswith(("animCurve", "animBlendNode")):
                return node
    return None


# ---- the press ----

def apply(root=None, state=None, new_place=False):
    """Key the source under the window's knobs on the skeleton of `root` (else the selection, else the last
    target), from where it was first keyed (else where it stands, from the playback start). Answers the
    status line."""
    gaitload, asp, scene, target, _ = _modules()
    started = time.time()
    state = state or settings()
    root = root or selected_root() or _state().get("target")
    if not root or not cmds.objExists(root):
        raise Refusal("select any part of a skeleton")
    if cmds.currentUnit(query=True, linear=True) != "cm":
        raise Refusal("the scene is not in centimetres")
    source = _source(state)
    bones, note = scene.read_bones(root)
    pelvis = bones.get("pelvis")
    if pelvis is not None and _driven(pelvis["path"]):
        raise Refusal("%s is driven by %s - a rig's game skeleton; select a bare skeleton"
                      % (pelvis["path"].split("|")[-1], _driven(pelvis["path"])))
    memo = {} if new_place else _memo(root)
    place = memo.get("place") if memo.get("source") == state["source"] or memo.get("place") else None
    retarget = target.Retarget(source.walk, source.statics, bones, place)
    pose = _pose(source, state, root)
    result, base, engine = gaitload.evaluate(source, state["gait"], pose, state["share"] if pose is not None else 0.0)
    frames, info = retarget.frames(result)
    written, translated = retarget.written(), set(retarget.translated())
    values, static = scene.channel_values(bones, frames, written, translated)
    start = int(memo["start"]) if memo.get("start") is not None and not new_place else int(
        cmds.playbackOptions(query=True, minTime=True))
    cmds.undoInfo(openChunk=True, chunkName="skeldarGait")
    try:
        _, driven = scene.write_curves(values, static, start)
        _set_memo(root, {"source": state["source"], "pose": state["pose"], "share": state["share"],
                         "parts": state["parts"], "gait": state["gait"], "clean": state["clean"],
                         "place": target.pm.flat(retarget.place), "start": start, "version": VERSION})
        end = start + result.frames
        cmds.playbackOptions(minTime=start, maxTime=end - 1,
                             animationStartTime=min(start, cmds.playbackOptions(query=True, animationStartTime=True)),
                             animationEndTime=max(end, cmds.playbackOptions(query=True, animationEndTime=True)))
    finally:
        cmds.undoInfo(closeChunk=True)
    _state()["target"] = root
    scale = info.get("scale", 1.0)
    now = asp.measure(source.walk, result.worlds)
    line = ("%s on %s x%.2f | %d fr (%d-%d), %.2f m/s, step %.0f cm, %.0f steps/min, ground %.0f %%" % (
        source.label, root.split("|")[-1].split(":")[-1], scale, result.frames, start, start + result.frames,
        now["speed"] * scale, now["step"] * scale, now["cadence"], now["duty"]))
    if pose is not None:
        line += " | pose %s x%.2f" % (os.path.splitext(os.path.basename(state["pose"]))[0], state["share"])
    if max(info.get("drop", [0.0]) or [0.0]) > 0.05:
        line += " | pelvis down %.1f cm where the legs fall short" % max(info["drop"])
    if note:
        line += " | " + note
    if driven:
        line += " | left to their drivers: " + ", ".join(sorted(driven))
    return line + " | %.2f s" % (time.time() - started)


# ---- the window ----

def _say(text):
    if cmds.text(STATUS, exists=True):
        cmds.text(STATUS, edit=True, label=text)
    print("Gait Builder: " + text)


def _run(fn, *args):
    try:
        _say(fn(*args))
    except Refusal as exc:
        _say(str(exc))
    except Exception as exc:                          # the line, never the Script Editor alone
        import traceback
        traceback.print_exc()
        _say("failed: %s" % exc)


def _rekey(state):
    remember(state)
    t = _state().get("target")
    if t and cmds.objExists(t):
        _run(apply, t, state)
    else:
        _say("Set for the next Apply.")


def _quiet():
    return _state().get("quiet", False)


def _display(asp, base, state, name):
    """(value, marked) a knob's slider shows on the window's side: the asked or the walk's own; a sided knob
    in Both its sides' mean, marked when they differ."""
    gait, side = state["gait"], state["side"]
    if name in ("speed", "step"):
        step, cadence = asp.timing(gait, base)
        return (step * cadence / 6000.0 if name == "speed" else step), False
    if name == "hip_drop" and "hip_drop" not in gait and "hips" in gait and abs(base["hips"]) > 0.5:
        return base["hip_drop"] * float(gait["hips"]) / base["hips"], False
    knob = asp.BY_NAME[name]
    if knob.sided:
        if side in ("l", "r"):
            return asp.value(gait, base, name, side), False
        l, r = asp.value(gait, base, name, "l"), asp.value(gait, base, name, "r")
        return 0.5 * (l + r), abs(l - r) > 1e-6
    return asp.value(gait, base, name), False


def _knob_changed(name, value):
    if _quiet():
        return
    asp = _modules()[1]
    state = settings()
    gait = state["gait"]
    knob = asp.BY_NAME[name]
    if name == "speed":                      # the law sets the step and the cadence
        gait.pop("step", None)
        gait["speed"] = float(value)
    elif name == "step":                     # the cadence kept, the speed follows
        source = _source(state)
        base = _modules()[0].baseline(source, *_pose_and_share(source, state))
        _, cadence = asp.timing(gait, base)
        gait["step"] = float(value)
        gait["speed"] = float(value) * cadence / 6000.0
    elif knob.sided and state["side"] in ("l", "r"):
        gait[name + "_" + state["side"]] = float(value)
    else:
        gait[name] = float(value)
        for side in ("l", "r"):              # Both links the sides again
            gait.pop(name + "_" + side, None)
    state["gait"] = gait
    _rekey(state)
    _refresh_values(state)


def _pose_and_share(source, state):
    pose = _pose(source, state)
    return (pose, state["share"] if pose is not None else 0.0)


def _refresh_values(state=None):
    """Every slider to what it means now (Speed and Step move each other; Hip drop follows Hips)."""
    gaitload, asp = _modules()[:2]
    state = state or settings()
    try:
        source = _source(state)
        base = gaitload.baseline(source, *_pose_and_share(source, state))
    except Exception:
        return
    _state()["quiet"] = True
    try:
        for knob in asp.KNOBS:
            control = "skeldarGait_" + knob.name
            value, marked = _display(asp, base, state, knob.name)
            if knob.kind == "toggle":
                if cmds.checkBox(control, exists=True):
                    cmds.checkBox(control, edit=True, value=value >= 0.5)
            elif cmds.floatSliderGrp(control, exists=True):
                lo = cmds.floatSliderGrp(control, query=True, minValue=True)
                hi = cmds.floatSliderGrp(control, query=True, maxValue=True)
                cmds.floatSliderGrp(control, edit=True, value=min(max(value, lo), hi),
                                    label=_label(knob) + (" *" if marked else ""))
    finally:
        _state()["quiet"] = False


def _label(knob):
    return knob.label + (", " + knob.unit if knob.unit else "")


def _source_chosen(label):
    if _quiet():
        return
    state = settings()
    for key, name in sources():
        if name == label:
            state["source"] = key
    asp = _modules()[1]                     # a new walk: its own values; the added knobs and toggles stay

    def kept(name):
        knob = asp.BY_NAME.get(name) or asp.BY_NAME.get(name[:-2] if name.endswith(("_l", "_r")) else name)
        return knob is not None and knob.kind != "measured"
    state["gait"] = dict((k, v) for k, v in state["gait"].items() if kept(k))
    remember(state)
    _rebuild()
    _rekey(state)


def _pose_chosen(label):
    if _quiet():
        return
    state = settings()
    state["pose"] = ""
    for rel, name in pose_cards():
        if name == label:
            state["pose"] = rel
    remember(state)
    _rebuild()
    _rekey(state)


def _share_changed(value):
    if _quiet():
        return
    state = settings()
    state["share"] = float(value)
    remember(state)
    _rebuild()
    _rekey(state)


def _part_changed(*_):
    if _quiet():
        return
    state = settings()
    state["parts"] = [p for p in PARTS if cmds.checkBox("skeldarGaitPart_" + p, query=True, value=True)]
    remember(state)
    _rebuild()
    _rekey(state)


def _side_changed(mode):
    if _quiet():
        return
    state = settings()
    state["side"] = mode
    remember(state)
    _refresh_values(state)


def _clean_changed(name, value):
    if _quiet():
        return
    state = settings()
    state["clean"][name] = float(value)
    remember(state)
    _rebuild()
    _rekey(state)


def reset(target=None):
    """Every knob back to the walk's own (the source, the pose and the clean kept)."""
    state = settings()
    state["gait"] = {}
    remember(state)
    _refresh_values(state)
    target = target or _state().get("target")
    if target and cmds.objExists(target):
        return "Reset to the walk's own | " + apply(target, state)
    return "Reset to the walk's own - select a skeleton and press Apply"


def show():
    if cmds.window(WINDOW, exists=True):
        cmds.deleteUI(WINDOW)
    if cmds.windowPref(WINDOW, exists=True):
        cmds.windowPref(WINDOW, remove=True)
    root = selected_root()
    if root and _memo(root).get("source"):           # a walked skeleton selected: its walk and knobs
        memo = _memo(root)
        state = settings()
        state.update(dict((k, memo[k]) for k in ("source", "pose", "share", "parts", "gait", "clean") if k in memo))
        remember(state)
        _state()["target"] = root
    _state()["quiet"] = True
    try:
        cmds.window(WINDOW, title="Gait Builder", widthHeight=(440, 820), sizeable=True)
        cmds.columnLayout("skeldarGaitRoot", adjustableColumn=True)
        cmds.setParent("..")
    finally:
        _state()["quiet"] = False
    _rebuild()
    cmds.showWindow(WINDOW)


def _rebuild():
    """The window's content again: the sliders' ranges follow the source, the pose and the clean."""
    if not cmds.columnLayout("skeldarGaitRoot", exists=True):
        return
    for child in cmds.columnLayout("skeldarGaitRoot", query=True, childArray=True) or []:
        cmds.deleteUI(child)
    cmds.setParent("skeldarGaitRoot")
    _state()["quiet"] = True
    try:
        _build(settings())
    finally:
        _state()["quiet"] = False


def _build(state):
    gaitload, asp = _modules()[:2]
    cmds.scrollLayout(BODY, childResizable=True, height=780)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=4)
    cmds.text(label="Select any part of a skeleton, press Apply. Every knob starts at the walk's own value;\n"
                    "a slider let go keys the same skeleton again.", align="left", height=32)
    listed = sources()
    cmds.optionMenu("skeldarGaitSource", label="Walk", changeCommand=_source_chosen)
    for key, label in listed:
        cmds.menuItem(label=label)
    for key, label in listed:
        if key == state["source"]:
            cmds.optionMenu("skeldarGaitSource", edit=True, value=label)
    poses = pose_cards()
    cmds.optionMenu("skeldarGaitPose", label="Pose", changeCommand=_pose_chosen)
    cmds.menuItem(label="(none)")
    for rel, label in poses:
        cmds.menuItem(label=label)
    for rel, label in poses:
        if rel == state["pose"]:
            cmds.optionMenu("skeldarGaitPose", edit=True, value=label)
    if state["pose"]:
        cmds.floatSliderGrp("skeldarGaitShare", label="Pose share", field=True, minValue=0.0, maxValue=1.0,
                            value=state["share"], step=0.05, precision=2, columnWidth3=(120, 60, 200),
                            changeCommand=_share_changed)
        cmds.rowLayout(numberOfColumns=len(PARTS))
        for p in PARTS:
            cmds.checkBox("skeldarGaitPart_" + p, label=p.capitalize(), value=p in state["parts"],
                          changeCommand=_part_changed)
        cmds.setParent("..")
    cmds.rowLayout(numberOfColumns=3, adjustableColumn=1, columnAttach3=("both", "both", "both"))
    cmds.button(label="Apply to selection", height=30, backgroundColor=(0.88, 0.48, 0.21),
                command=lambda *_: _run(apply, selected_root() or _state().get("target")))
    cmds.button(label="Here again", height=30, annotation="Key it again starting where the character stands now",
                command=lambda *_: _run(apply, selected_root() or _state().get("target"), None, True))
    cmds.button(label="Reset", height=30, annotation="Every knob back to the walk's own", command=lambda *_: _run(reset))
    cmds.setParent("..")
    cmds.radioButtonGrp("skeldarGaitSide", label="Arms and legs", labelArray3=[l for _, l in SIDE_MODES],
                        numberOfRadioButtons=3, columnWidth4=(110, 60, 60, 60),
                        select=[m for m, _ in SIDE_MODES].index(state["side"]) + 1,
                        changeCommand=lambda *_: _side_changed(SIDE_MODES[cmds.radioButtonGrp(
                            "skeldarGaitSide", query=True, select=True) - 1][0]))
    try:
        source = _source(state)
        base = gaitload.baseline(source, *_pose_and_share(source, state))
    except Exception as exc:
        cmds.text(label="The walk cannot be read: %s" % exc, align="left", wordWrap=True, height=60)
        cmds.text(STATUS, label="", align="left", wordWrap=True, height=60)
        return
    ranges = asp.ranges(base, source.walk.leg_length)
    for group in asp.GROUPS:
        cmds.frameLayout(label=group, collapsable=True, collapse=group not in OPEN_GROUPS, marginWidth=4)
        cmds.columnLayout(adjustableColumn=True)
        for knob in asp.KNOBS:
            if knob.group != group:
                continue
            control = "skeldarGait_" + knob.name
            value, marked = _display(asp, base, state, knob.name)
            if knob.kind == "toggle":
                cmds.checkBox(control, label=knob.label, value=value >= 0.5, annotation=knob.tip,
                              changeCommand=lambda v, n=knob.name: _knob_changed(n, 1.0 if v else 0.0))
                continue
            lo, hi = ranges[knob.name]
            span = hi - lo
            step = 0.01 if span < 3.0 else (0.1 if span < 30.0 else 0.5)
            cmds.floatSliderGrp(control, label=_label(knob) + (" *" if marked else ""), field=True,
                                minValue=lo, maxValue=hi, fieldMinValue=lo, fieldMaxValue=hi,
                                value=min(max(value, lo), hi), step=step, precision=2 if step < 0.1 else 1,
                                columnWidth3=(130, 60, 190), annotation=knob.tip,
                                changeCommand=lambda v, n=knob.name: _knob_changed(n, v))
        cmds.setParent("..")
        cmds.setParent("..")
    cmds.frameLayout(label="Clean", collapsable=True, collapse=True, marginWidth=4)
    cmds.columnLayout(adjustableColumn=True)
    from maya_walk import clean as wc
    knobs = wc.knobs(state["clean"])
    for name, label, hi in (("seam", "Seam, fr", 20.0), ("smooth", "Smooth, fr", 6.0)):
        cmds.floatSliderGrp("skeldarGaitClean_" + name, label=label, field=True, minValue=0.0, maxValue=hi,
                            value=knobs.get(name, 0.0), step=0.5, precision=1, columnWidth3=(130, 60, 190),
                            changeCommand=lambda v, n=name: _clean_changed(n, v))
    cmds.setParent("..")
    cmds.setParent("..")
    cmds.text(STATUS, label="", align="left", wordWrap=True, height=64)


def onMayaDroppedPythonFile(*_):
    """Maya's drop handler: the modules read again (a re-dropped file must not run the old code), then the
    window."""
    if HERE and HERE not in sys.path:
        sys.path.insert(0, HERE)
    for name in ("gaitmodel", "aspects", "gaitgen", "gaitload"):
        if name in sys.modules:
            importlib.reload(sys.modules[name])
    if hasattr(sys, "_skeldar_gait_cache"):
        sys._skeldar_gait_cache.clear()
    me = sys.modules.get(__name__)
    if me is not None and getattr(me, "__file__", None):
        importlib.reload(me)                          # trap 220: a re-dropped file keeps the old module
    sys.modules[__name__].show()


if __name__ == "__main__":
    show()
