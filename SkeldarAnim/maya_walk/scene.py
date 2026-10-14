"""maya_walk.scene - the parametric walk in Maya: save a walk cycle, put it on any skeleton, tune it there.

Save walk: a bone of a walk cycle selected - the cycle goes to a file in the walks folder (`folder()`). Apply:
any skeleton selected (UE5/UE4, Mixamo, HumanIK, Unity, Biped ...) - the walk is keyed onto it, in its own
proportions, from where it stands; a released knob re-keys it. A walked skeleton carries its walk, pose and
knobs (`MARKER`), so selecting it reads them back. The hub card is maya_walk.panel.

The model: maya_walk.model; the saved walk: maya_walk.files; the transfer onto a skeleton: maya_walk.target
(the Pose Library's posemath plus the legs by IK); a character pose under the walk: maya_walk.pose. The design:
docs/superpowers/specs/2026-10-12-parametric-walk-design.md, 2026-10-12-walk-onto-any-skeleton-design.md and
2026-10-13-walk-builder-card-design.md.
"""
import json
import math
import os
import sys
import time

import numpy as np

from . import model as wm
from . import files as wf
from . import target as wt
from . import pose as wp
from . import clean as wc

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(PLUGIN, "assets", "manny_skeleton_template.json")
#  The reference a raw clip's posture and floor are judged against (2026-10-14): the UE5 idle M_Neutral_Stand_Idle_Loop's
#  mean pose over its 302 frames, shipped; else a saved pose; else none (the skeleton's rest then)
BUILT_IN_REFERENCE = "UE5 idle (built in)"
NO_REFERENCE = "(none)"
REFERENCE_FILE = os.path.join(PLUGIN, "assets", "walk_reference_ue5.wpose.gz")
#  Every knob the card holds and a walked skeleton remembers: the model's and the clean's (the model never sees the
#  clean's - apply hands each its own)
ALL_DEFAULTS = dict(wm.DEFAULTS, **wc.DEFAULTS)
ALL_RANGES = dict(wm.RANGES, **wc.RANGES)
#  Where the walks and the poses live: this override (a verify's temporary folder), else the optionVar, else
#  <userAppDir>/SkeldarWalks - outside the plugin folder, which an install replaces.
WALKS = None
FOLDER_OPTIONVAR = "skeldarWalkFolder"
FOLDER_NAME = "SkeldarWalks"


def folder():
    """The walks folder (made on the first save)."""
    if WALKS:
        return WALKS
    cmds = _cmds()
    if cmds.optionVar(exists=FOLDER_OPTIONVAR):
        chosen = cmds.optionVar(query=FOLDER_OPTIONVAR)
        if chosen:
            return chosen
    return os.path.join(cmds.internalVar(userAppDir=True), FOLDER_NAME)


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
    the card works on (its root's UUID)."""
    state = getattr(sys, "_skeldar_walk", None)
    if state is None or "loaded" not in state:
        state = {"loaded": {}, "target": None}
        sys._skeldar_walk = state
    if state.get("model") is not wm or state.get("clean") is not wc:
        # the walks and poses read by a model loaded earlier: their methods are the old code's (an install
        # purges and reloads the package, and an old Walk's evaluate() took no pose) - read them again
        state["loaded"] = {}
        state["model"] = wm
        state["clean"] = wc
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


def reference_names():
    """The references a walk's posture and floor can be judged against: the built-in idle, the saved poses,
    none."""
    return [BUILT_IN_REFERENCE] + pose_names() + [NO_REFERENCE]


def _reference_path(name):
    if not name or name == NO_REFERENCE:
        return None
    if name == BUILT_IN_REFERENCE:
        return REFERENCE_FILE if os.path.exists(REFERENCE_FILE) else None
    path = wf.pose_path_for(folder(), name)
    if not os.path.exists(path):
        raise Refusal("no saved pose named %s for the reference - pick another in Clean" % name)
    return path


def _clean_data(data, knobs, ref_path):
    """(the clean clip, its Report) of a walk's data (files.load's dict) under the clean knobs and the reference
    pose file `ref_path` (None: none) carried onto the walk's skeleton."""
    ref, why = None, None
    if ref_path:
        bones = wf.load_pose(ref_path)[1]
        try:
            ref = wp.carried(data["names"], np.asarray(data["worlds"])[:, 0], data["statics"], bones, wt)
        except wt.Refusal as error:          # a skeleton the reference cannot stand on: judged by its rest
            why = "the reference was not used (%s) - judged against the rest" % error
    clip, report = wc.clean(wf.clip_of(data, wm), data["statics"], ref, knobs)
    if why:
        report.note(why)
    return clip, report


def _cleaned(path, stamp, data, given, reference):
    """_clean_data of a loaded walk file, cached by the file's time, the knobs and the reference file's time."""
    knobs = wc.knobs(given)
    ref_path = _reference_path(reference)
    key = ("clean", path, stamp, tuple(sorted(knobs.items())), ref_path,
           os.path.getmtime(ref_path) if ref_path else None)
    cached = _state()["loaded"].get(key)
    if cached is None:
        cached = _clean_data(data, knobs, ref_path)
        _cache(key, cached)
    return cached


CACHED_READINGS = 6       # a walk's readings kept (each knob value released is one - the oldest goes)


def _cache(key, value):
    """A reading of a walk (`key` = (kind, path, ...)) kept, at most CACHED_READINGS of its kind and path."""
    loaded = _state()["loaded"]
    same = [k for k in loaded if isinstance(k, tuple) and k[:2] == key[:2]]
    for old in same[:max(0, len(same) - CACHED_READINGS + 1)]:
        del loaded[old]
    loaded[key] = value


def save_walk(root, name=None, reference=BUILT_IN_REFERENCE):
    """The clip under `root` saved to the walks folder as <name>.walk.gz AS IT STANDS - a cycle or not, floating,
    jittery: it is cleaned when it is read (maya_walk.clean) - after reading it the way it will be read (the
    clean at its defaults against `reference`, then the model's refusals). Returns (the walk's name, the status
    line)."""
    clip, start = read_clip(root)
    bones, note = read_bones(root)
    statics = dict((leaf, {"parent": b["parent"], "canonical": b["canonical"], "rest": b["rest"]})
                   for leaf, b in bones.items() if leaf in clip.names)
    missing = [n for n in clip.names if n not in statics]
    if missing:
        raise Refusal("%d bones of the cycle read twice or unnamed: %s" % (len(missing), ", ".join(missing[:4])))
    data = {"names": clip.names, "parents": clip.parents, "worlds": clip.worlds, "fps": clip.fps, "up": clip.up,
            "name": clip.name, "statics": statics, "start": start}
    cleaned, report = _clean_data(data, wc.knobs(), _reference_path(reference))
    walk = wm.analyse(cleaned)
    name = wf.safe_name(name or clip.name)
    clip.name = name
    path = wf.path_for(folder(), name)
    wf.save(path, clip, statics, start)
    _forget(path)
    line = "saved %s | %s" % (os.path.basename(path), walk.summary())
    if report.changed:
        line += " | " + report.short()
    return name, line + (" | " + note if note else "")


def _forget(path):
    """Every cached reading of a walk file (a fresh save replaces it)."""
    loaded = _state()["loaded"]
    for key in list(loaded):
        if key == path or (isinstance(key, tuple) and path in key[:2]):
            loaded.pop(key, None)


def load_walk(name, given=None, reference=BUILT_IN_REFERENCE):
    """(Walk, statics, first frame, clean Report) of a saved walk read under the clean knobs in `given` and the
    reference named `reference`, cached by the file's time, the knobs and the reference."""
    path = wf.path_for(folder(), name)
    if not os.path.exists(path):
        raise Refusal("no saved walk named %s" % name)
    stamp = os.path.getmtime(path)
    loaded = _state()["loaded"].get(path)
    if loaded is None or loaded[0] != stamp:
        loaded = (stamp, wf.load(path))
        _state()["loaded"][path] = loaded
    data = loaded[1]
    knobs = wc.knobs(given)
    ref_path = _reference_path(reference)
    key = ("walk", path, stamp, tuple(sorted(knobs.items())), ref_path,
           os.path.getmtime(ref_path) if ref_path else None)
    walk = _state()["loaded"].get(key)
    report = _cleaned(path, stamp, data, knobs, reference)[1]
    if walk is None:
        walk = wm.analyse(_cleaned(path, stamp, data, knobs, reference)[0])
        _cache(key, walk)
    return walk, data["statics"], int(data["start"]), report


def walk_names():
    return wf.names_in(folder())


# ---- poses ----

def pose_names():
    return wf.pose_names_in(folder())


def save_pose(root, name=None):
    """The skeleton under `root` as it stands at the current frame, saved to the walks folder as <name>.wpose.gz (the
    tool's rest rule). Returns (the pose's name, the status line)."""
    bones, note = read_bones(root)
    name = wf.safe_name(name or _short(root).split(":")[-1] + "_pose")
    path = wf.pose_path_for(folder(), name)
    wf.save_pose(path, name, bones)
    _state()["loaded"].pop(path, None)
    line = "saved %s: %d bones of %s at frame %g" % (os.path.basename(path), len(bones), _short(root),
                                                     _cmds().currentTime(query=True))
    return name, line + (" | " + note if note else "")


def prepared_pose(walk_name, pose_name, given=None, reference=BUILT_IN_REFERENCE):
    """The pose `pose_name` carried onto the walk `walk_name`'s skeleton (walkpose.prepare) - the walk read under
    the clean knobs in `given` and `reference` - cached by the two files' times and the walk's reading."""
    walk = load_walk(walk_name, given, reference)[0]
    statics = load_walk(walk_name, given, reference)[1]
    path = wf.pose_path_for(folder(), pose_name)
    if not os.path.exists(path):
        raise Refusal("no saved pose named %s" % pose_name)
    key = ("pose", wf.path_for(folder(), walk_name), path, id(walk))
    stamp = (os.path.getmtime(key[1]), os.path.getmtime(path))
    cached = _state()["loaded"].get(key)
    if cached is None or cached[0] != stamp or cached[2] is not walk:   # an id is reused once a walk is evicted
        bones = wf.load_pose(path)[1]
        cached = (stamp, wp.prepare(walk, statics, bones, wm, wt), walk)
        _cache(key, cached)
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


_BLEND_INPUT = {"outputX": "inputAX", "outputY": "inputAY", "outputZ": "inputAZ", "output": "inputA"}


def base_input(plug):
    """(the plug the walk's curve drives, the curve standing there or None): the channel itself, or - under
    animation layers - the base layer's input at the bottom of its blend chain, so a layer the animator keys
    corrections on stays on top of every re-key. A channel driven by anything else (a constraint, an
    expression) is refused by name."""
    cmds = _cmds()
    dest = plug
    for _ in range(64):
        source = cmds.listConnections(dest, source=True, destination=False, plugs=True,
                                      skipConversionNodes=True) or []
        if not source:
            return dest, None
        node, attr = source[0].split(".", 1)
        kind = cmds.nodeType(node)
        if kind.startswith("animCurve"):
            return dest, node
        if not kind.startswith("animBlendNode") or attr not in _BLEND_INPUT:
            raise Refusal("%s is driven by %s (%s) - the walk keys only channels that are free, keyed or under "
                          "animation layers" % (_short(plug), node, kind))
        dest = node + "." + _BLEND_INPUT[attr]
    raise Refusal("%s: an animation layer chain this tool cannot follow" % _short(plug))


def write_curves(values, static, start):
    """Each written channel's old curve deleted and a new one keyed on frames start..start+N (auto
    tangents): nodes through cmds (Ctrl+Z removes them and puts deleted ones back), keys through
    MFnAnimCurve.addKeys (trap 224). Under animation layers the base layer is what is re-keyed (base_input):
    the layers above it - an animator's corrections - stay. A static translate: its curves deleted, the value
    set."""
    cmds, om, oma = _cmds(), _om(), _oma()
    written = 0
    plans = dict(((path, ch), base_input(path + "." + ch)) for path, channels in values.items() for ch in channels)
    plans.update(((path, ch), base_input(path + "." + ch)) for path in static for ch in TRANSLATE)
    for path, channels in values.items():
        for ch, vals in channels.items():
            plug = path + "." + ch
            dest, old = plans[(path, ch)]
            if old:
                cmds.delete(old)
            if dest == plug and cmds.getAttr(plug, lock=True):
                cmds.setAttr(plug, lock=False)
            curve = cmds.createNode("animCurveTL" if ch in TRANSLATE else "animCurveTA",
                                    name="%s_%s" % (_short(path).split(":")[-1], ch))
            cmds.connectAttr(curve + ".output", dest)
            times = om.MTimeArray([om.MTime(float(start + f), om.MTime.uiUnit()) for f in range(len(vals))])
            selection = om.MSelectionList()
            selection.add(curve)
            oma.MFnAnimCurve(selection.getDependNode(0)).addKeys(
                times, om.MDoubleArray(vals), oma.MFnAnimCurve.kTangentAuto, oma.MFnAnimCurve.kTangentAuto)
            written += 1
    for path, value in static.items():
        for ch, v in zip(TRANSLATE, value):
            plug = path + "." + ch
            dest, old = plans[(path, ch)]
            if old:
                cmds.delete(old)
            if dest == plug and cmds.getAttr(plug, lock=True):
                cmds.setAttr(plug, lock=False)
            cmds.setAttr(dest, v)
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

def model_knobs(given):
    """The model's share of the card's knobs (a side's own values included): what evaluate() takes."""
    return dict((k, v) for k, v in (given or {}).items() if k in wm.DEFAULTS or k in wm.SIDE_KNOBS)


def apply(root, walk_name, given=None, pose_name=None, parts=ALL_PARTS, reference=BUILT_IN_REFERENCE):
    """The saved walk `walk_name` - read under the clean knobs in `given` against `reference` - keyed onto the
    skeleton under `root` with the model's knobs in `given` (and the pose `pose_name`'s `parts` - walkpose.PARTS
    - at the knob `pose`'s share), from the place it stood when a walk was first put on it (else where it
    stands). One undo step. Returns (Result, info, the status line)."""
    started = time.time()
    root = _long(root)
    walk, statics, start, report = load_walk(walk_name, given, reference)
    bones, note = read_bones(root)
    memo = memo_of(root)
    retarget = wt.Retarget(walk, statics, bones, memo.get("place"))
    pose = None
    knobs = model_knobs(given)
    if pose_name and wm.knobs(**knobs)["pose"] > 0.0:
        pose = wp.filtered(prepared_pose(walk_name, pose_name, given, reference), parts)
    result = walk.evaluate(knobs, pose)
    frames, info = retarget.frames(result)
    written, translated = retarget.written(), set(retarget.translated())
    values, static = channel_values(bones, frames, written, translated)
    with _Chunk("skeldarWalkApply"):
        write_curves(values, static, start)
        _set_memo(root, {"walk": walk_name, "pose": pose_name or "", "parts": list(parts),
                         "knobs": dict(result.info["knobs"], **wc.knobs(given)),
                         "reference": reference or NO_REFERENCE,
                         "place": wt.pm.flat(retarget.place), "start": start, "version": VERSION})
    _state()["target"] = _cmds().ls(root, uuid=True)[0]
    target_stride = result.info["stride_cm"] * info["scale"]
    #  short: the card's status line holds three lines (2026-10-13, «интерфейс рисуй компактным»)
    text = ("%s on %s, %d bones x%.2f | %d fr (%d-%d), stride %.0f cm, %.2f m/s"
            % (walk_name, _short(root), len(written), info["scale"], result.frames, start, start + result.frames,
               target_stride, result.info["speed"] * info["scale"]))
    if pose is not None:
        text += " | pose %s x%.2f%s" % (pose_name, result.info["knobs"]["pose"],
                                         "" if tuple(parts) == ALL_PARTS else " (%s)" % (", ".join(parts) or "no part"))
    matched = result.info.get("leg_match") or {}
    if pose is not None and matched.get("on"):
        text += " | legs matched x%.2f" % matched["keep"]
        if abs(matched.get("hips_deg", 0.0)) >= 1.0:
            text += ", hips %.0f deg to the spine" % abs(matched["hips_deg"])
    if max(info["drop"]) > 0.05:
        text += " | pelvis down %.1f cm where the legs fall short" % max(info["drop"])
    if result.info["lowered"] > 0.05:
        text += " | the walk sinks %.1f cm at the contacts" % result.info["lowered"]
    if info["short"] > 0.05:
        text += " | a foot falls %.1f cm short" % info["short"]
    held = [got for steps in (result.info.get("ground") or {}).values() for asked, got in steps]
    asked = result.info["knobs"]["ground_time"]
    if held and max(abs(g - asked) for g in held) > 0.02:       # the swing's room or both feet up stopped it
        text += " | feet down x%.2f-%.2f of x%.2f asked" % (min(held), max(held), asked)
    balance = result.info.get("balance") or {}
    if balance.get("note"):
        text += " | no balance: " + balance["note"]
    elif balance.get("carry", 0.0) > 0.1:
        text += " | balance carries the pelvis %.1f cm" % balance["carry"]
    used = result.info["knobs"]
    if used.get("in_place", 0.0) >= 0.5:
        text += " | in place"
    if abs(used.get("upper_offset", 0.0)) > 1e-9:
        text += " | the upper body %.1f fr %s" % (abs(used["upper_offset"]),
                                                  "late" if used["upper_offset"] > 0 else "early")
    if report.changed:
        text += " | " + report.short()
    if note:
        text += " | " + note
    info["clean"] = report
    return result, info, text + " | %.1f s" % (time.time() - started)


def selected_top():
    """The topmost joint of what the first selected node belongs to (a joint, a mesh skinned to a skeleton),
    else None - cheap, for the card's selection job (no rig check: Apply makes it)."""
    cmds = _cmds()
    selection = cmds.ls(selection=True, long=True) or []
    if not selection:
        return None
    path = selection[0]
    if cmds.nodeType(path) != "joint":
        shapes = cmds.listRelatives(path, shapes=True, fullPath=True, noIntermediate=True) or []
        skins = [s for shape in shapes for s in (cmds.listHistory(shape, pruneDagObjects=True) or [])
                 if cmds.nodeType(s) == "skinCluster"]
        if not skins:
            return None
        found = cmds.ls((cmds.skinCluster(skins[0], query=True, influence=True) or [None])[0], long=True)
        if not found:
            return None
        path = found[0]
    while True:
        above = cmds.listRelatives(path, parent=True, fullPath=True)
        if not above or cmds.nodeType(above[0]) != "joint":
            return path
        path = above[0]


def set_target(root):
    """The skeleton a released knob re-keys."""
    _state()["target"] = _cmds().ls(root, uuid=True)[0] if root else None


def pick(root):
    """(walk name, knobs, pose name, pose parts) a walked skeleton carries; the card's target becomes it."""
    root = _long(root)
    memo = memo_of(root)
    if not memo.get("walk"):
        raise Refusal("%s carries no walk of this tool - Apply one first" % _short(root))
    _state()["target"] = _cmds().ls(root, uuid=True)[0]
    stored = memo.get("knobs", {})
    knobs = wm.knobs(**model_knobs(stored))      # a side's own values too
    old = dict(stored)
    if "reference" not in memo:                  # put on before the clean: kept as it was keyed (no floor, no posture)
        old.update(floor=0.0, fix_posture=0.0)
    knobs.update(wc.knobs(old))                  # the clean's
    return memo["walk"], knobs, memo.get("pose") or None, tuple(memo.get("parts", ALL_PARTS))


def reference_of(root):
    """The reference a walked skeleton's walk was read against (a walk put on before 2026-10-14: the built-in)."""
    reference = memo_of(_long(root)).get("reference")
    return reference if reference else BUILT_IN_REFERENCE


def target_root():
    uuid = _state().get("target")
    found = _cmds().ls(uuid, long=True) if uuid else []
    if not found:
        raise Refusal("select a skeleton and press Apply first")
    return found[0]


