"""skeldar_walk.py - the parametric walk in Maya: save a walk cycle, put it on any skeleton, tune it there.

Drop this file into a viewport: the window opens. Select a bone of a walk cycle and press Save walk...:
the cycle goes to a file in walks/ beside this file. Select any skeleton (UE5/UE4, Mixamo, HumanIK, Unity,
Biped ...), pick a walk in the list and press Apply to selection: the walk is keyed onto that skeleton, in
its own proportions, from where it stands. A released slider re-keys it; Pick selection reads a walked
skeleton's walk and knobs back into the window. Each skeleton keeps its own knobs.

The model: walkmodel.py; the saved walk: walkfile.py; the transfer onto a skeleton: walktarget.py (the
Pose Library's posemath plus the legs by IK). The design: docs/superpowers/specs/
2026-10-12-parametric-walk-design.md and 2026-10-12-walk-onto-any-skeleton-design.md.
"""
import importlib.util
import json
import math
import os
import sys
import time

import numpy as np

try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:   # exec'd as text: the caller names the folder
    HERE = globals().get("WALK_HERE", os.getcwd())
PLUGIN = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", "SkeldarAnim"))
WALKS = os.path.join(HERE, "walks")
TEMPLATE = os.path.join(PLUGIN, "assets", "manny_skeleton_template.json")


def _load(name, module_name):
    spec = importlib.util.spec_from_file_location(module_name, os.path.join(HERE, name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _plugin_on_path():
    """The plugin's modules (the Pose Library's transfer) importable: the installed copy when Maya already
    has it, else the repository's own SkeldarAnim beside these scripts."""
    try:
        import maya_poselib.posemath   # noqa: F401
    except ImportError:
        if PLUGIN not in sys.path:
            sys.path.append(PLUGIN)


_plugin_on_path()
wm = _load("walkmodel", "skeldar_walkmodel")
wf = _load("walkfile", "skeldar_walkfile")
wt = _load("walktarget", "skeldar_walktarget")
wp = _load("walkpose", "skeldar_walkpose")


class Refusal(Exception):
    """What a press does not do, and why (the status line shows it)."""


REFUSALS = (Refusal, wm.Refusal, wf.Refusal, wt.Refusal)
NO_POSE = "(none)"
ALL_PARTS = tuple(part for part, keys in wp.PARTS)
MARKER = "skeldarWalk"
VERSION = 2
CHANNELS = ("translateX", "translateY", "translateZ", "rotateX", "rotateY", "rotateZ")
TRANSLATE = CHANNELS[:3]
ROTATE = CHANNELS[3:]
FPS = {"game": 15, "film": 24, "pal": 25, "ntsc": 30, "show": 48, "palf": 50, "ntscf": 60}


def _cmds():
    import maya.cmds as cmds
    return cmds


def _om():
    import maya.api.OpenMaya as om
    return om


def _oma():
    import maya.api.OpenMayaAnim as oma
    return oma


def _state():
    """Per session, on sys (a reloaded module must find it): the loaded walks by file and the skeleton
    the window works on (its root's UUID)."""
    state = getattr(sys, "_skeldar_walk", None)
    if state is None or "loaded" not in state:
        state = {"loaded": {}, "target": None}
        sys._skeldar_walk = state
    return state


def _short(path):
    return path.rsplit("|", 1)[-1]


def _long(node):
    found = _cmds().ls(node, long=True)
    if not found:
        raise Refusal("%s is gone from the scene" % node)
    return found[0]


def _fps():
    unit = _cmds().currentUnit(query=True, time=True)
    if unit in FPS:
        return float(FPS[unit])
    if unit.endswith("fps"):
        return float(unit[:-3])
    raise Refusal("the scene's time unit %s is not a frame rate this tool knows" % unit)


# ---- which skeleton ----

def skeleton_root_of(node):
    """The topmost joint of the skeleton `node` belongs to (a joint, a mesh skinned to it, a group above
    it). A rig of ours is refused: its game skeleton is driven by constraints."""
    cmds = _cmds()
    path = _long(node)
    try:
        import maya_rigs
        if maya_rigs.rig_of(path, maya_rigs.rigs()) is not None:
            raise Refusal("%s belongs to a rig - this version puts a walk on skeletons only" % _short(path))
    except ImportError:
        pass
    if cmds.nodeType(path) != "joint":
        shapes = cmds.listRelatives(path, shapes=True, fullPath=True) or []
        skins = [s for shape in shapes for s in (cmds.listHistory(shape, pruneDagObjects=True) or [])
                 if cmds.nodeType(s) == "skinCluster"]
        if skins:
            path = _long((cmds.skinCluster(skins[0], query=True, influence=True) or [path])[0])
        else:
            below = cmds.listRelatives(path, allDescendents=True, type="joint", fullPath=True) or []
            if not below:
                raise Refusal("%s holds no skeleton - select a bone of a skeleton" % _short(path))
            path = min(below, key=lambda p: p.count("|"))
    while True:
        above = cmds.listRelatives(path, parent=True, fullPath=True)
        if not above or cmds.nodeType(above[0]) != "joint":
            return path
        path = above[0]


def selected_root():
    selection = _cmds().ls(selection=True, long=True)
    if not selection:
        raise Refusal("select a bone of a skeleton first")
    return skeleton_root_of(selection[0])


def read_bones(root):
    """The skeleton as the Pose Library reads it ({leaf: bone}, scene.skeleton) with this tool's rest rule:
    an unskinned skeleton whose bones are Manny's rests at Manny's bind (the plugin's template). Returns
    (bones, a note or "")."""
    from maya_poselib import scene
    cmds = _cmds()
    ref = scene.skeleton_ref(root)
    bones, convention = scene.skeleton(ref)
    skinned = any(cmds.listConnections(b["path"] + ".worldMatrix[0]", source=False, destination=True,
                                       type="skinCluster") for b in bones.values())
    if skinned:
        return bones, ""
    positions = dict((leaf, tuple(b["rest"][12:15])) for leaf, b in bones.items())
    parents = dict((leaf, b["parent"]) for leaf, b in bones.items())
    rests = wf.template_rests(positions, parents, wf.read_template(TEMPLATE)) if os.path.exists(TEMPLATE) else None
    if rests is None:
        return bones, "%s has no skin: its rest is read as it stands" % _short(root)
    for leaf, rest in rests.items():
        bones[leaf]["rest"] = list(rest)
    return bones, ""


# ---- saving a walk ----

def read_clip(root):
    """The cycle under `root` as a walkmodel.Clip: every joint's world on every whole frame of its keys."""
    cmds = _cmds()
    if cmds.currentUnit(query=True, linear=True) != "cm":
        raise Refusal("the scene is not in centimetres")
    joints = [root] + (cmds.listRelatives(root, allDescendents=True, type="joint", fullPath=True) or [])
    joints.sort(key=lambda p: (p.count("|"), p))
    index = dict((p, i) for i, p in enumerate(joints))
    parents = []
    for path in joints:
        above = cmds.listRelatives(path, parent=True, fullPath=True)
        parents.append(index.get(above[0], -1) if above else -1)
    times = set()
    for path in joints:
        for ch in CHANNELS:
            times.update(cmds.keyframe(path, attribute=ch, query=True, timeChange=True) or [])
    if not times:
        raise Refusal("%s carries no keys - select a bone of a walk cycle" % _short(root))
    start, end = min(times), max(times)
    if abs(start - round(start)) > 1e-6 or abs(end - round(end)) > 1e-6:
        raise Refusal("the keys run %g-%g: a cycle starts and ends on whole frames" % (start, end))
    start, end = int(round(start)), int(round(end))
    worlds = np.array([[cmds.getAttr(p + ".worldMatrix[0]", time=t) for t in range(start, end + 1)]
                       for p in joints]).reshape(len(joints), end - start + 1, 4, 4)
    up = (0.0, 1.0, 0.0) if cmds.upAxis(query=True, axis=True) == "y" else (0.0, 0.0, 1.0)
    scene = os.path.splitext(os.path.basename(cmds.file(query=True, sceneName=True) or ""))[0]
    above = cmds.listRelatives(root, parent=True, fullPath=True)
    name = scene or _short(above[0] if above else root)
    return wm.Clip([_short(p).split(":")[-1] for p in joints], parents, worlds, _fps(), up, name), start


def save_walk(root, name=None):
    """The cycle under `root` analysed (the model's refusals first) and saved to walks/<name>.walk.gz.
    Returns (the walk's name, the status line)."""
    clip, start = read_clip(root)
    walk = wm.analyse(clip)
    bones, note = read_bones(root)
    statics = dict((leaf, {"parent": b["parent"], "canonical": b["canonical"], "rest": b["rest"]})
                   for leaf, b in bones.items() if leaf in walk.index)
    missing = [n for n in walk.names if n not in statics]
    if missing:
        raise Refusal("%d bones of the cycle read twice or unnamed: %s" % (len(missing), ", ".join(missing[:4])))
    name = wf.safe_name(name or clip.name)
    clip.name = name
    path = wf.path_for(WALKS, name)
    wf.save(path, clip, statics, start)
    _state()["loaded"].pop(path, None)
    line = "saved %s | %s" % (os.path.basename(path), walk.summary())
    return name, line + (" | " + note if note else "")


def load_walk(name):
    """(Walk, statics, first frame) of a saved walk, cached by its file's time."""
    path = wf.path_for(WALKS, name)
    if not os.path.exists(path):
        raise Refusal("no saved walk named %s" % name)
    stamp = os.path.getmtime(path)
    loaded = _state()["loaded"].get(path)
    if loaded is None or loaded[0] != stamp:
        data = wf.load(path)
        loaded = (stamp, wm.analyse(wf.clip_of(data, wm)), data["statics"], int(data["start"]))
        _state()["loaded"][path] = loaded
    return loaded[1], loaded[2], loaded[3]


def walk_names():
    return wf.names_in(WALKS)


# ---- poses ----

def pose_names():
    return wf.pose_names_in(WALKS)


def save_pose(root, name=None):
    """The skeleton under `root` as it stands at the current frame, saved to walks/<name>.wpose.gz (the
    tool's rest rule). Returns (the pose's name, the status line)."""
    bones, note = read_bones(root)
    name = wf.safe_name(name or _short(root).split(":")[-1] + "_pose")
    path = wf.pose_path_for(WALKS, name)
    wf.save_pose(path, name, bones)
    _state()["loaded"].pop(path, None)
    line = "saved %s: %d bones of %s at frame %g" % (os.path.basename(path), len(bones), _short(root),
                                                     _cmds().currentTime(query=True))
    return name, line + (" | " + note if note else "")


def prepared_pose(walk_name, pose_name):
    """The pose `pose_name` carried onto the walk `walk_name`'s skeleton (walkpose.prepare), cached by the
    two files' times."""
    walk, statics, start = load_walk(walk_name)
    path = wf.pose_path_for(WALKS, pose_name)
    if not os.path.exists(path):
        raise Refusal("no saved pose named %s" % pose_name)
    key = (wf.path_for(WALKS, walk_name), path)
    stamp = (os.path.getmtime(key[0]), os.path.getmtime(path))
    cached = _state()["loaded"].get(key)
    if cached is None or cached[0] != stamp:
        bones = wf.load_pose(path)[1]
        cached = (stamp, wp.prepare(walk, statics, bones, wm, wt))
        _state()["loaded"][key] = cached
    return cached[1]


# ---- the marker on a walked skeleton ----

def memo_of(root):
    cmds = _cmds()
    if not cmds.attributeQuery(MARKER, node=root, exists=True):
        return {}
    try:
        memo = json.loads(cmds.getAttr(root + "." + MARKER) or "{}")
    except ValueError:
        return {}
    return memo if memo.get("version") == VERSION else {}


def _set_memo(root, memo):
    cmds = _cmds()
    if not cmds.attributeQuery(MARKER, node=root, exists=True):
        cmds.addAttr(root, longName=MARKER, dataType="string")
    cmds.setAttr(root + "." + MARKER, json.dumps(memo), type="string")


# ---- the keys ----

def _parent_world(bones, leaf, final):
    """The world the bone's local is read against: its parent bone's new world, or - the top joint - the
    node above it as it stands."""
    parent = bones[leaf]["parent"]
    if parent in final:
        return final[parent]
    above = _cmds().listRelatives(bones[leaf]["path"], parent=True, fullPath=True)
    om = _om()
    return om.MMatrix(_cmds().getAttr(above[0] + ".worldMatrix[0]")) if above else om.MMatrix()


def channel_values(bones, frames, written, translated):
    """{path: {channel: [value a frame]}}: rotate for every written bone, translate for the translated
    ones (radians for rotations - the curves' internal unit), each frame's euler nearest the frame before;
    and {path: (tx, ty, tz)} - the written bones whose translation is static (their rest local)."""
    from maya_poselib import skelsolve
    cmds = _cmds()
    tops = {}
    out, static = {}, {}
    for leaf in written:
        bone = bones[leaf]
        path = bone["path"]
        current = [float(v) for v in cmds.getAttr(path + ".rotate")[0]]
        values = dict((ch, []) for ch in (CHANNELS if leaf in translated else ROTATE))
        for final in frames:
            if bone["parent"] not in final and leaf not in tops:
                tops[leaf] = _parent_world(bones, leaf, final)
            parent = final[bone["parent"]] if bone["parent"] in final else tops[leaf]
            local = final[leaf] * parent.inverse()
            turn = skelsolve.joint_channels(local, bone["jointOrient"], bone["rotateAxis"],
                                            bone["rotateOrder"], current)
            current = list(turn)
            for i, ch in enumerate(ROTATE):
                values[ch].append(math.radians(turn[i]))
            if leaf in translated:
                for i, ch in enumerate(TRANSLATE):
                    values[ch].append(float(local[12 + i]))
        out[path] = values
        if leaf not in translated:
            first = frames[0]
            parent = first[bone["parent"]] if bone["parent"] in first else tops[leaf]
            local = first[leaf] * parent.inverse()
            static[path] = (local[12], local[13], local[14])
    return out, static


def write_curves(values, static, start):
    """Each written channel's old curve deleted and a new one keyed on frames start..start+N (auto
    tangents): nodes through cmds (Ctrl+Z removes them and puts deleted ones back), keys through
    MFnAnimCurve.addKeys (trap 224). A static translate: its curves deleted, the value set."""
    cmds, om, oma = _cmds(), _om(), _oma()
    written = 0
    for path, channels in values.items():
        for ch, vals in channels.items():
            plug = path + "." + ch
            old = cmds.listConnections(plug, source=True, destination=False, type="animCurve") or []
            if old:
                cmds.delete(old)
            if cmds.getAttr(plug, lock=True):
                cmds.setAttr(plug, lock=False)
            curve = cmds.createNode("animCurveTL" if ch in TRANSLATE else "animCurveTA",
                                    name="%s_%s" % (_short(path).split(":")[-1], ch))
            cmds.connectAttr(curve + ".output", plug)
            times = om.MTimeArray([om.MTime(float(start + f), om.MTime.uiUnit()) for f in range(len(vals))])
            selection = om.MSelectionList()
            selection.add(curve)
            oma.MFnAnimCurve(selection.getDependNode(0)).addKeys(
                times, om.MDoubleArray(vals), oma.MFnAnimCurve.kTangentAuto, oma.MFnAnimCurve.kTangentAuto)
            written += 1
    for path, value in static.items():
        for ch, v in zip(TRANSLATE, value):
            plug = path + "." + ch
            old = cmds.listConnections(plug, source=True, destination=False, type="animCurve") or []
            if old:
                cmds.delete(old)
            if cmds.getAttr(plug, lock=True):
                cmds.setAttr(plug, lock=False)
            cmds.setAttr(plug, v)
    return written


class _Chunk(object):
    """One undo step for a press."""

    def __init__(self, name):
        self.name = name

    def __enter__(self):
        _cmds().undoInfo(openChunk=True, chunkName=self.name)

    def __exit__(self, *exc):
        _cmds().undoInfo(closeChunk=True)
        return False


# ---- apply, pick ----

def apply(root, walk_name, given=None, pose_name=None, parts=ALL_PARTS):
    """The saved walk `walk_name` keyed onto the skeleton under `root` with the knobs `given` (and the pose
    `pose_name`'s `parts` - walkpose.PARTS - at the knob `pose`'s share), from the place it stood when a
    walk was first put on it (else where it stands). One undo step. Returns (Result, info, the status line)."""
    started = time.time()
    root = _long(root)
    walk, statics, start = load_walk(walk_name)
    bones, note = read_bones(root)
    memo = memo_of(root)
    retarget = wt.Retarget(walk, statics, bones, memo.get("place"))
    pose = None
    if pose_name and wm.knobs(**(given or {}))["pose"] > 0.0:
        pose = wp.filtered(prepared_pose(walk_name, pose_name), parts)
    result = walk.evaluate(given, pose)
    frames, info = retarget.frames(result)
    written, translated = retarget.written(), set(retarget.translated())
    values, static = channel_values(bones, frames, written, translated)
    with _Chunk("skeldarWalkApply"):
        write_curves(values, static, start)
        _set_memo(root, {"walk": walk_name, "pose": pose_name or "", "parts": list(parts),
                         "knobs": result.info["knobs"],
                         "place": wt.pm.flat(retarget.place), "start": start, "version": VERSION})
    _state()["target"] = _cmds().ls(root, uuid=True)[0]
    target_stride = result.info["stride_cm"] * info["scale"]
    text = ("%s onto %s: %d bones paired, size x%.2f | %d frames (%d-%d), stride %.1f cm, %.2f m/s"
            % (walk_name, _short(root), len(written), info["scale"], result.frames, start, start + result.frames,
               target_stride, result.info["speed"] * info["scale"]))
    if pose is not None:
        text += " | pose %s x%.2f (%s)" % (pose_name, result.info["knobs"]["pose"], ", ".join(parts) or "nothing")
    if max(info["drop"]) > 0.05:
        text += " | pelvis lowered up to %.1f cm where the legs fall short" % max(info["drop"])
    if result.info["lowered"] > 0.05:
        text += " | the walk itself sinks %.1f cm at the contacts" % result.info["lowered"]
    if info["short"] > 0.05:
        text += " | a foot falls %.1f cm short of its step" % info["short"]
    if note:
        text += " | " + note
    return result, info, text + " | %.2f s" % (time.time() - started)


def pick(root):
    """(walk name, knobs, pose name, pose parts) a walked skeleton carries; the window's target becomes it."""
    root = _long(root)
    memo = memo_of(root)
    if not memo.get("walk"):
        raise Refusal("%s carries no walk of this tool - Apply one first" % _short(root))
    _state()["target"] = _cmds().ls(root, uuid=True)[0]
    knobs = wm.knobs(**dict((k, v) for k, v in memo.get("knobs", {}).items() if k in wm.DEFAULTS))
    return memo["walk"], knobs, memo.get("pose") or None, tuple(memo.get("parts", ALL_PARTS))


def target_root():
    uuid = _state().get("target")
    found = _cmds().ls(uuid, long=True) if uuid else []
    if not found:
        raise Refusal("Apply a walk to a skeleton first (select it, press Apply to selection)")
    return found[0]


# ---- the window ----

WINDOW = "skeldarWalkWindow"
STATUS = "skeldarWalkStatus"
WALK_MENU = "skeldarWalkMenu"
POSE_MENU = "skeldarWalkPoseMenu"
PART_LABELS = {"torso": "Torso", "pelvis": "Pelvis", "knees": "Knees", "arms": "Arms", "feet": "Feet"}
TARGET = "skeldarWalkTarget"
INTRO = ("Save walk: a bone of a walk cycle selected (a closed loop with root motion). Save pose: any "
         "skeleton standing in a character pose. Apply: any skeleton selected - the walk is keyed onto it in "
         "its own proportions, from where it stands; every released slider re-keys it. Pick: read a walked "
         "skeleton's walk, pose and knobs back.")
GROUPS = (
    ("Pose", ("pose",)),
    ("Step", ("stride", "tempo", "lift", "width")),
    ("Pelvis", ("bob", "sway", "pelvis_rot")),
    ("Upper body", ("spine", "arms", "head", "overlap")),
    ("Weight", ("weight", "exaggeration")),
)
LABELS = {
    "pose": ("Pose", "how far the pose picked above replaces the walk's own: the spine, the head, the pelvis "
                     "(its height and tilt) and the knees; 0 is the walk, 1 the pose"),
    "stride": ("Stride", "x the step length; the travel follows (a long stride sinks the contacts)"),
    "tempo": ("Tempo (frames)", "frames a cycle of two steps; fewer is faster"),
    "lift": ("Foot lift", "x how high the swinging foot rises above its path"),
    "width": ("Width (cm)", "the feet set this much wider apart (negative: narrower), in the walk's size"),
    "bob": ("Bob", "x the pelvis's up and down"),
    "sway": ("Sway", "x the pelvis's side to side"),
    "pelvis_rot": ("Pelvis turn", "x the pelvis's turns and tilts"),
    "spine": ("Spine", "x the spine's and the neck's motion"),
    "arms": ("Arms", "x the arms' swing"),
    "head": ("Head", "x the head's motion in the world (0 holds it steady)"),
    "overlap": ("Overlap (fr)", "frames the hands lag the pelvis (the spine and the head less)"),
    "weight": ("Weight", "heavier: deeper, longer low poses, a slower rise, more overlap; negative: lighter"),
    "exaggeration": ("Exaggeration", "x every motion around the mean pose at once (not the stride)"),
}


def _control(name):
    return "skeldarWalk_" + name


def _say(text):
    cmds = _cmds()
    if cmds.text(STATUS, exists=True):
        cmds.text(STATUS, edit=True, label=text)
    else:
        print(text)


def _run(action):
    """A press: its line on the status, a refusal or a failure there too (never only the Script Editor)."""
    try:
        _say(action())
    except REFUSALS as refusal:
        _say(str(refusal))
    except Exception as error:   # the status line, not a traceback in a closed editor
        import traceback
        traceback.print_exc()
        _say("failed: %s" % error)


def given_from_window():
    cmds = _cmds()
    out = {}
    for name in wm.DEFAULTS:
        if name == "tempo":
            out[name] = cmds.intSliderGrp(_control(name), query=True, value=True)
        else:
            out[name] = cmds.floatSliderGrp(_control(name), query=True, value=True)
    return out


def chosen_walk():
    cmds = _cmds()
    items = cmds.optionMenu(WALK_MENU, query=True, itemListLong=True) or []
    if not items:
        raise Refusal("no walk saved yet - select a bone of a walk cycle and press Save walk...")
    return cmds.optionMenu(WALK_MENU, query=True, value=True)


def chosen_pose():
    value = _cmds().optionMenu(POSE_MENU, query=True, value=True)
    return None if not value or value == NO_POSE else value


def _part_control(part):
    return "skeldarWalkPart_" + part


def chosen_parts():
    cmds = _cmds()
    return tuple(part for part in ALL_PARTS if cmds.checkBox(_part_control(part), query=True, value=True))


def _set_parts(parts):
    for part in ALL_PARTS:
        _cmds().checkBox(_part_control(part), edit=True, value=part in parts)


def _fill_poses(selected=None):
    cmds = _cmds()
    for item in cmds.optionMenu(POSE_MENU, query=True, itemListLong=True) or []:
        cmds.deleteUI(item)
    cmds.menuItem(label=NO_POSE, parent=POSE_MENU)
    names = pose_names()
    for name in names:
        cmds.menuItem(label=name, parent=POSE_MENU)
    cmds.optionMenu(POSE_MENU, edit=True, value=selected if selected in names else NO_POSE)


def _fill_walks(selected=None):
    cmds = _cmds()
    for item in cmds.optionMenu(WALK_MENU, query=True, itemListLong=True) or []:
        cmds.deleteUI(item)
    names = walk_names()
    for name in names:
        cmds.menuItem(label=name, parent=WALK_MENU)
    if selected in names:
        cmds.optionMenu(WALK_MENU, edit=True, value=selected)


def _set_knobs(knobs, frames):
    cmds = _cmds()
    for name, value in knobs.items():
        if name == "tempo":
            cmds.intSliderGrp(_control(name), edit=True, minValue=max(4, frames // 2), maxValue=2 * frames,
                              fieldMaxValue=4 * frames, value=int(round(value)) if value >= 1 else frames)
        else:
            cmds.floatSliderGrp(_control(name), edit=True, value=value)


def _show_target(root):
    cmds = _cmds()
    if cmds.text(TARGET, exists=True):
        cmds.text(TARGET, edit=True, label="Target: " + (_short(root) if root else "-"))


def walk_changed(*_):
    def act():
        walk, statics, start = load_walk(chosen_walk())
        _set_knobs({"tempo": walk.P}, walk.P)
        return walk.summary()
    _run(act)


def press_save(*_):
    def act():
        cmds = _cmds()
        root = selected_root()
        default = read_clip(root)[0].name
        answer = cmds.promptDialog(title="Save walk", message="Name:", text=default,
                                   button=["Save", "Cancel"], defaultButton="Save", cancelButton="Cancel",
                                   dismissString="Cancel")
        if answer != "Save":
            return "nothing saved"
        name, line = save_walk(root, cmds.promptDialog(query=True, text=True) or default)
        _fill_walks(name)
        walk_changed()
        return line
    _run(act)


def press_save_pose(*_):
    def act():
        cmds = _cmds()
        root = selected_root()
        default = _short(root).split(":")[-1] + "_pose"
        answer = cmds.promptDialog(title="Save pose", message="Name:", text=default,
                                   button=["Save", "Cancel"], defaultButton="Save", cancelButton="Cancel",
                                   dismissString="Cancel")
        if answer != "Save":
            return "nothing saved"
        name, line = save_pose(root, cmds.promptDialog(query=True, text=True) or default)
        _fill_poses(name)
        return line + " - select a walked skeleton, Pick, and raise Pose"
    _run(act)


def press_apply(*_):
    def act():
        root = selected_root()
        line = apply(root, chosen_walk(), given_from_window(), chosen_pose(), chosen_parts())[2]
        _show_target(root)
        return line
    _run(act)


def press_pick(*_):
    def act():
        root = selected_root()
        name, knobs, pose, parts = pick(root)
        if name in walk_names():
            _fill_walks(name)
        _fill_poses(pose)
        _set_parts(parts)
        walk, statics, start = load_walk(name)
        _set_knobs(knobs, walk.P)
        _show_target(root)
        return "%s carries %s - its knobs are in the window; a released slider re-keys it" % (_short(root), name)
    _run(act)


def slider_changed(*_):
    _run(lambda: apply(target_root(), chosen_walk(), given_from_window(), chosen_pose(), chosen_parts())[2])


def press_reset(*_):
    def act():
        walk, statics, start = load_walk(chosen_walk())
        _set_knobs(dict(wm.DEFAULTS), walk.P)
        return apply(target_root(), chosen_walk(), given_from_window(), chosen_pose(), chosen_parts())[2]
    _run(act)


def show():
    """The window: the walks, Save / Apply / Pick, the target, the knobs in four groups, Reset, the status."""
    cmds = _cmds()
    if cmds.window(WINDOW, exists=True):
        cmds.deleteUI(WINDOW)
    if cmds.windowPref(WINDOW, exists=True):
        cmds.windowPref(WINDOW, remove=True)
    cmds.window(WINDOW, title="Parametric Walk", sizeable=True, widthHeight=(440, 700))
    cmds.columnLayout(adjustableColumn=True, rowSpacing=3, columnAttach=("both", 8))
    cmds.text(label=INTRO, align="left", wordWrap=True, height=66)
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1, columnAttach2=("both", "both"))
    cmds.optionMenu(WALK_MENU, label="Walk", changeCommand=walk_changed)
    cmds.button(label="Save walk...", height=26, command=press_save)
    cmds.setParent("..")
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1, columnAttach2=("both", "both"))
    cmds.optionMenu(POSE_MENU, label="Pose", changeCommand=slider_changed)
    cmds.button(label="Save pose...", height=26, command=press_save_pose)
    cmds.setParent("..")
    cmds.rowLayout(numberOfColumns=len(ALL_PARTS) + 1)
    cmds.text(label="Pose takes:", width=72, align="left")
    for part in ALL_PARTS:
        cmds.checkBox(_part_control(part), label=PART_LABELS[part], value=True, changeCommand=slider_changed,
                      annotation="what of the pose replaces the walk's own (Arms: held - the grip kept, the "
                                 "swing fading with Pose; Feet: the width and the toes' turn)")
    cmds.setParent("..")
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1, columnAttach2=("both", "both"))
    cmds.button(label="Apply to selection", height=30, command=press_apply)
    cmds.button(label="Pick selection", height=30, command=press_pick)
    cmds.setParent("..")
    cmds.text(TARGET, label="Target: -", align="left", font="boldLabelFont", height=20)
    for heading, names in GROUPS:
        cmds.text(label=heading, font="boldLabelFont", align="left", height=22)
        for name in names:
            label, tip = LABELS[name]
            if name == "tempo":
                cmds.intSliderGrp(_control(name), label=label, field=True, minValue=4, maxValue=120,
                                  fieldMinValue=4, fieldMaxValue=400, value=31, columnWidth3=(100, 50, 250),
                                  annotation=tip, changeCommand=slider_changed)
            else:
                low, high = wm.RANGES[name]
                cmds.floatSliderGrp(_control(name), label=label, field=True, minValue=low, maxValue=high,
                                    fieldMinValue=low, fieldMaxValue=high, value=wm.DEFAULTS[name], step=0.05,
                                    precision=2, columnWidth3=(100, 50, 250), annotation=tip,
                                    changeCommand=slider_changed)
    cmds.button(label="Reset", height=28, command=press_reset)
    cmds.text(STATUS, label="Save a walk, then select a skeleton and Apply.", align="left", wordWrap=True,
              height=96)
    cmds.showWindow(WINDOW)
    _fill_walks()
    _fill_poses()
    if walk_names():
        walk_changed()


def onMayaDroppedPythonFile(*args):
    """Maya's viewport drop imports this file once and keeps it (trap 220): reload it - which reloads the
    model, the file and the transfer too - so a changed file runs."""
    import importlib
    importlib.reload(sys.modules[__name__]).show()


if __name__ == "__main__":
    show()
