"""Every clip reference into the scene as its own namespaced, keyed skeleton.

2026-10-02, the animator: «хорошо бы было сделать максимальный обхват
форматов которые мы можем прочитать и вытащить из них анимацию». The import
funnel (`rigimport.import_source`) hands a plain FBX path to
`animimport.import_clip` exactly as before; anything else - a take of an
FBX, a Unity clip, another format - comes here, and leaves the scene in the
SAME shape: a namespace holding a keyed joint skeleton, and an info dict
with `namespace`, `joints`, `start`/`end` (frames), `fps` and `warning`. So
the retarget onto a rig, the transfer onto a skeleton and the square of
several work for every format with no road of their own.

What each format is read with, all measured in mayapy 2027 (2026-10-02):

- **FBX** - the FBX plugin (`FBXImport`, trap 22/33/39). A file's takes are
  listed with `FBXRead -f` + `FBXGetTakeCount` / `FBXGetTakeName i` /
  `FBXGetTakeLocalTimeSpan i` (positional index; 1-3 ms a file - the read is
  lazy); one take is imported with `FBXImport -t i`. A Unity clip is a take
  (by name) cut to its `firstFrame..lastFrame`.
- **Collada (.dae)** - the FBX plugin reads it too (`DAE_FBX`): `FBXImport`
  of a .dae brought 603 curves back; it lists no takes (FBXGetTakeCount 0),
  so a file is one clip.
- **Maya (.ma/.mb)** - `file -import` into the namespace with script nodes
  NOT run, and every script node that arrived deleted (the "vaccine"
  malware travels in scene files, CLAUDE.md).
- **USD** - mayaUsd's `mayaUSDImport(readAnimData=True)`: a UsdSkel
  skeleton comes in as keyed joints in the current namespace (93 joints,
  837 curves from a Manny clip, 0.09 s).
- **BVH**, **glTF/GLB**, **Unity .anim** - our own readers (`bvh`, `gltf`,
  `unityfiles`) and one skeleton builder here (`build`): joints made under
  the namespace, keys written through `MFnAnimCurve.addKeys` (thousands of
  `setKeyframe` calls would take minutes), times in SECONDS so a clip plays
  at its own speed whatever the scene's rate.
"""

import math
import os

import maya.cmds as cmds
import maya.mel as mel

from maya_uebridge import animimport
from maya_uebridge import bvh
from maya_uebridge import gltf
from maya_uebridge import sources
from maya_uebridge import unityfiles

NO_FILE = "no file at {0}"
UNREADABLE = "{0} is a {1} file we do not read"
USD_PLUGIN = "mayaUsdPlugin"
#  How close (cm) a converted Unity rest position must come to the model's to
#  trust the units we measured from them.
MODEL_MATCH = 0.9           # share of a clip's bones a model must carry


# ------------------------------------------------------------------ listing

def fbx_takes(path):
    """The takes of an FBX: [(index, name, start, end)], times in the
    scene's frames. [] for a file the plugin cannot read."""
    animimport.ensure_fbx_plugin()
    try:
        mel.eval('FBXRead -f "{0}"'.format(path.replace("\\", "/")))
        count = int(mel.eval("FBXGetTakeCount") or 0)
    except Exception:                                        # noqa: BLE001
        return []
    out = []
    for index in range(1, count + 1):
        try:
            name = mel.eval("FBXGetTakeName {0}".format(index)) or ""
            span = mel.eval("FBXGetTakeLocalTimeSpan {0}".format(index)) or [0, 0]
            out.append((index, name, float(span[0]), float(span[1])))
        except Exception:                                    # noqa: BLE001
            out.append((index, "", None, None))
    return out


def take_index(takes, name):
    """The 1-based index of the take called `name` (exact, then ignoring
    case), or None. Pure."""
    for index, take, _a, _b in takes:
        if take == name:
            return index
    for index, take, _a, _b in takes:
        if take.lower() == (name or "").lower():
            return index
    return None


# ------------------------------------------------------------------ helpers

def _time_curves(namespace):
    nodes = cmds.namespaceInfo(namespace, listOnlyDependencyNodes=True,
                               recurse=True, dagPath=True) or []
    curves = set()
    for node in nodes:
        if cmds.objExists(node) and cmds.nodeType(node) in (
                "joint", "transform"):
            for c in cmds.listConnections(node, source=True, destination=False,
                                          type="animCurve") or []:
                if cmds.nodeType(c) in ("animCurveTL", "animCurveTA",
                                        "animCurveTU", "animCurveTT"):
                    curves.add(c)
    return sorted(curves)


def _joints(namespace):
    nodes = cmds.namespaceInfo(namespace, listOnlyDependencyNodes=True,
                               recurse=True, dagPath=True) or []
    return [n for n in nodes if cmds.objExists(n) and cmds.nodeType(n) == "joint"]


def _info(namespace, start, end, fps=None, warning="", set_timeline=True):
    if set_timeline and start is not None:
        cmds.playbackOptions(minTime=start, maxTime=end,
                             animationStartTime=start, animationEndTime=end)
    return {"namespace": namespace, "merged": False, "target": "",
            "joints": len(_joints(namespace)), "start": start, "end": end,
            "fps": fps, "warning": warning, "relinked": [], "stale": [],
            "notes": []}


def _range_of(namespace):
    curves = _time_curves(namespace)
    times = cmds.keyframe(curves, query=True, timeChange=True) or [] if curves else []
    return (min(times), max(times)) if times else (None, None)


def _in_namespace(namespace):
    if not cmds.namespace(exists=":" + namespace):
        cmds.namespace(addNamespace=namespace)
    cmds.namespace(setNamespace=":" + namespace)


# ------------------------------------------------------------------ funnel

def import_clip(ref, namespace, set_timeline=True, clip_fps=None):
    """The clip `ref` names into `namespace` as its own keyed skeleton.
    Returns the info dict `animimport.import_clip` returns. Raises with a
    sentence the status line can show."""
    path, clip = sources.split_ref(ref)
    if not os.path.isfile(path):
        raise RuntimeError(NO_FILE.format(path))
    fmt = sources.fmt_of(path)
    if fmt in ("fbx", "dae"):
        return _import_fbx(path, clip, namespace, set_timeline, clip_fps)
    if fmt in ("ma", "mb"):
        return _import_maya(path, namespace, set_timeline)
    if fmt == "usd":
        return _import_usd(path, namespace, set_timeline)
    if fmt == "bvh":
        return _import_bvh(path, namespace, set_timeline)
    if fmt == "gltf":
        return _import_gltf(path, int(clip.get("anim") or 0), namespace,
                            set_timeline)
    if fmt == "anim":
        return _import_unity_anim(path, namespace, set_timeline)
    raise RuntimeError(UNREADABLE.format(os.path.basename(path), fmt or "?"))


def _import_fbx(path, clip, namespace, set_timeline, clip_fps):
    take = clip.get("take")
    if not take and clip.get("take_name"):
        take = take_index(fbx_takes(path), clip["take_name"])
    info = animimport.import_clip(path, namespace, set_timeline=False,
                                  clip_fps=clip_fps, merge=False,
                                  take=int(take) if take else None)
    start, end = info.get("start"), info.get("end")
    if "first" in clip and "last" in clip:
        start, end = trim(namespace, float(clip["first"]), float(clip["last"]))
    info["start"], info["end"] = start, end
    if set_timeline and start is not None:
        cmds.playbackOptions(minTime=start, maxTime=end,
                             animationStartTime=start, animationEndTime=end)
    return info


def trim(namespace, first, last):
    """Cut a namespace's keys to `first..last` (a Unity clip of a take),
    keys inserted on both edges first so the clip keeps its pose there."""
    curves = _time_curves(namespace)
    if not curves:
        return first, last
    for at in (first, last):
        cmds.setKeyframe(curves, insert=True, time=at)
    times = cmds.keyframe(curves, query=True, timeChange=True) or []
    lo, hi = min(times), max(times)
    if lo < first:
        cmds.cutKey(curves, time=(lo, first - 1e-4), clear=True)
    if hi > last:
        cmds.cutKey(curves, time=(last + 1e-4, hi), clear=True)
    return first, last


def _import_maya(path, namespace, set_timeline):
    kind = "mayaAscii" if path.lower().endswith(".ma") else "mayaBinary"
    flags = dict(i=True, type=kind, namespace=namespace, ignoreVersion=True,
                 mergeNamespacesOnClash=False, preserveReferences=False,
                 returnNewNodes=True, options="v=0;")
    try:
        new = cmds.file(path, executeScriptNodes=False, **flags) or []
    except TypeError:
        new = cmds.file(path, **flags) or []
    scripts = [n for n in new if cmds.objExists(n) and cmds.nodeType(n) == "script"]
    if scripts:
        cmds.delete(scripts)
    start, end = _range_of(namespace)
    warning = ("{0} script node(s) in the file deleted, never run".format(
        len(scripts)) if scripts else "")
    return _info(namespace, start, end, None, warning, set_timeline)


def _import_usd(path, namespace, set_timeline):
    if not cmds.pluginInfo(USD_PLUGIN, query=True, loaded=True):
        cmds.loadPlugin(USD_PLUGIN, quiet=True)
    _in_namespace(namespace)
    try:
        cmds.mayaUSDImport(file=path.replace("\\", "/"), readAnimData=True,
                           primPath="/")
    finally:
        cmds.namespace(setNamespace=":")
    start, end = _range_of(namespace)
    return _info(namespace, start, end, None, "", set_timeline)


# ------------------------------------------------------------------ builder

def legal(name):
    """A Maya node name for a joint called `name` in another program.
    A `prefix:` stays a namespace (Mixamo's `mixamorig:`), the way the FBX
    plugin brings it. Pure."""
    parts = (name or "joint").split(":")
    out = []
    for part in parts:
        clean = "".join(c if (c.isalnum() or c == "_") else "_" for c in part)
        if not clean or clean[0].isdigit():
            clean = "_" + clean
        out.append(clean)
    return ":".join(out)


def _plug(path, attr):
    import maya.api.OpenMaya as om
    sel = om.MSelectionList()
    sel.add(path)
    return om.MFnDependencyNode(sel.getDependNode(0)).findPlug(attr, False)


def _write_curve(path, attr, mtimes, values):
    import maya.api.OpenMaya as om
    import maya.api.OpenMayaAnim as oma
    fn = oma.MFnAnimCurve()
    fn.create(_plug(path, attr))
    fn.addKeys(mtimes, om.MDoubleArray(values),
               oma.MFnAnimCurve.kTangentLinear, oma.MFnAnimCurve.kTangentLinear)


def _euler_from(q, jo_q, order, previous):
    """The rotate channels (radians) that give local rotation `q` under a
    jointOrient `jo_q` (local = R·JO, row vectors), nearest `previous`."""
    import maya.api.OpenMaya as om
    local = om.MQuaternion(*q).asMatrix()
    if jo_q is not None:
        local = local * om.MQuaternion(*jo_q).asMatrix().inverse()
    euler = om.MTransformationMatrix(local).rotation(asQuaternion=False)
    euler = euler.reorder(order)
    if previous is not None:
        euler = euler.closestSolution(previous)
    return euler


def build(namespace, joints, tracks, times, set_timeline=True, fps=None,
          warning=""):
    """Make `joints` under `namespace` and key them.

    `joints`: dicts in parent-first order - `name`, `parent` (index or
    None), `t` (rest translation, cm), `q` (rest rotation (x, y, z, w) or
    None: it becomes the jointOrient, so rotate reads 0 at rest), `order`
    (Maya's rotateOrder name). `tracks`: one dict a joint (or None) -
    `t` [(x, y, z) cm], `q` [(x, y, z, w)] or `e` [(rx, ry, rz) degrees in
    the joint's order], `s` [(sx, sy, sz)], one value per `times` entry
    (seconds). Returns the info dict."""
    import maya.api.OpenMaya as om
    orders = ("xyz", "yzx", "zxy", "xzy", "yxz", "zyx")
    _in_namespace(namespace)
    paths = []
    try:
        for joint in joints:
            name = legal(joint["name"])
            if ":" in name:
                nested = name.rsplit(":", 1)[0]
                full = namespace + ":" + nested
                if not cmds.namespace(exists=":" + full):
                    cmds.namespace(addNamespace=":" + full)
            parent = paths[joint["parent"]] if joint.get("parent") is not None else None
            kwargs = {"name": name}
            if parent:
                kwargs["parent"] = parent
            node = cmds.createNode("joint", **kwargs)
            path = cmds.ls(node, long=True)[0]
            paths.append(path)
            order = joint.get("order") or "xyz"
            cmds.setAttr(path + ".rotateOrder", orders.index(order))
            cmds.setAttr(path + ".translate", *joint.get("t", (0, 0, 0)))
            if joint.get("q") is not None:
                euler = om.MQuaternion(*joint["q"]).asEulerRotation()
                cmds.setAttr(path + ".jointOrient", *[math.degrees(v) for v in
                                                       (euler.x, euler.y, euler.z)])
    finally:
        cmds.namespace(setNamespace=":")
    mtimes = om.MTimeArray([om.MTime(t, om.MTime.kSeconds) for t in times])
    for joint, path, track in zip(joints, paths, tracks):
        if not track or not times:
            continue
        order = orders.index(joint.get("order") or "xyz")
        if track.get("t"):
            for axis, attr in enumerate(("translateX", "translateY", "translateZ")):
                _write_curve(path, attr, mtimes, [v[axis] for v in track["t"]])
        if track.get("q"):
            previous, eulers = None, []
            for q in track["q"]:
                previous = _euler_from(q, joint.get("q"), order, previous)
                eulers.append(previous)
            for attr, key in (("rotateX", "x"), ("rotateY", "y"), ("rotateZ", "z")):
                _write_curve(path, attr, mtimes, [getattr(e, key) for e in eulers])
        elif track.get("e"):
            for axis, attr in enumerate(("rotateX", "rotateY", "rotateZ")):
                _write_curve(path, attr, mtimes,
                             [math.radians(v[axis]) for v in track["e"]])
        if track.get("s") and any(abs(c - 1.0) > 1e-6 for v in track["s"] for c in v):
            for axis, attr in enumerate(("scaleX", "scaleY", "scaleZ")):
                _write_curve(path, attr, mtimes, [v[axis] for v in track["s"]])
    start = end = None
    if times:
        unit = om.MTime.uiUnit()
        start = om.MTime(times[0], om.MTime.kSeconds).asUnits(unit)
        end = om.MTime(times[-1], om.MTime.kSeconds).asUnits(unit)
    return _info(namespace, start, end, fps, warning, set_timeline)


def scene_units():
    """Centimetres per metre in the scene's linear unit (100 for cm)."""
    unit = cmds.currentUnit(query=True, linear=True)
    return {"mm": 1000.0, "cm": 100.0, "m": 1.0, "km": 0.001, "in": 39.3700787,
            "ft": 3.2808399, "yd": 1.0936133}.get(unit, 100.0)


# ------------------------------------------------------------------ BVH

def bvh_plan(motion):
    """(joints, tracks, times) for `build` from a parsed BVH: rest offsets,
    no jointOrient (a BVH's rest is its zero rotations), the channels'
    own rotation order. Pure."""
    joints = [{"name": j.name, "parent": j.parent, "t": j.offset, "q": None,
               "order": bvh.rotate_order(j.channels)} for j in motion.joints]
    tracks = bvh.joint_tracks(motion)
    for joint, track in zip(motion.joints, tracks):
        if not any(c in bvh.POSITION for c in joint.channels):
            track["t"] = None           # the offset alone, unkeyed
    times = [i * motion.frame_time for i in range(len(motion.frames))]
    return joints, tracks, times


def _import_bvh(path, namespace, set_timeline):
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        motion = bvh.parse(handle.read())
    joints, tracks, times = bvh_plan(motion)
    return build(namespace, joints, tracks, times, set_timeline,
                 fps=bvh.fps_of(motion.frame_time))


# ------------------------------------------------------------------ glTF

def gltf_plan(doc, buffers, clip_index, units=100.0):
    """(joints, tracks, times) for `build` from a glTF document: the
    skeleton's nodes at their rest TRS (rotation the jointOrient), one
    animation sampled at its keys, metres scaled to the scene. Pure."""
    nodes = gltf.nodes_of(doc)
    wanted = gltf.skeleton_nodes(doc)
    where = dict((index, k) for k, index in enumerate(wanted))
    times, by_node = gltf.tracks(doc, buffers, clip_index)
    joints, tracks = [], []
    for index in wanted:
        node = nodes[index]
        parent = node.parent if node.parent in where else None
        joints.append({"name": node.name,
                       "parent": where[parent] if parent is not None else None,
                       "t": tuple(c * units for c in node.t), "q": node.r,
                       "order": "xyz"})
        raw = by_node.get(index) or {}
        track = {}
        if times:
            track["t"] = [tuple(c * units for c in v) for v in raw["t"]] \
                if "t" in raw else [tuple(c * units for c in node.t)] * len(times)
            track["q"] = raw.get("r") or [node.r] * len(times)
            if "s" in raw:
                track["s"] = raw["s"]
        tracks.append(track)
    return joints, tracks, times


def _import_gltf(path, clip_index, namespace, set_timeline):
    doc, buffers = gltf.load(path)
    joints, tracks, times = gltf_plan(doc, buffers, clip_index, scene_units())
    if not joints:
        raise RuntimeError("{0} holds no skeleton".format(os.path.basename(path)))
    return build(namespace, joints, tracks, times, set_timeline)


# ------------------------------------------------------------------ Unity

def unity_samples(curves, summary):
    """(times, {path: {"t"/"q"/"s": [Unity values per time]}}) of a generic
    clip, sampled at its own rate over its own span. Pure."""
    rate = summary.get("rate") or 30.0
    keys = [row[0] for track in curves.values() for rows in track.values()
            for row in rows]
    start = summary.get("start")
    stop = summary.get("stop")
    if start is None or stop is None or stop <= start:
        start, stop = (min(keys), max(keys)) if keys else (0.0, 0.0)
    count = int(round((stop - start) * rate)) + 1
    times = [start + i / rate for i in range(count)]
    out = {}
    for path, track in curves.items():
        sampled = {}
        if track.get("t"):
            sampled["t"] = [unityfiles.hermite(track["t"], at) for at in times]
        if track.get("r"):
            sampled["q"] = [unityfiles.hermite(track["r"], at) for at in times]
        elif track.get("e"):
            sampled["q"] = [unityfiles.unity_euler_quat(unityfiles.hermite(
                track["e"], at)) for at in times]
        if track.get("s"):
            sampled["s"] = [unityfiles.hermite(track["s"], at) for at in times]
        out[path] = sampled
    return times, out


def model_for(anim_path, leaves, levels=3):
    """The model file beside a Unity clip whose bytes name at least
    MODEL_MATCH of the clip's bones: its folder, then up to `levels`
    parents - never above the project's Assets folder, and only its own
    folder for a clip outside any project (the verify's first run climbed
    out of its sandbox into %TEMP% and took another tool's FBX)."""
    folder = os.path.dirname(anim_path)
    parts = [p.lower() for p in folder.replace("\\", "/").split("/")]
    if "assets" not in parts:
        levels = 0
    for _level in range(levels + 1):
        try:
            names = sorted(os.listdir(folder))
        except OSError:
            names = []
        for name in names:
            if os.path.splitext(name)[1].lower() not in (".fbx",):
                continue
            path = os.path.join(folder, name)
            try:
                with open(path, "rb") as handle:
                    data = handle.read()
            except (OSError, IOError):
                continue
            if leaves and unityfiles.leaves_in_bytes(data, leaves) >= \
                    MODEL_MATCH * len(leaves):
                return path.replace("\\", "/")
        parent = os.path.dirname(folder)
        if parent == folder or os.path.basename(folder).lower() == "assets":
            break
        folder = parent
    return None


def units_from(pairs):
    """The scale from Unity's positions to the model's (cm per Unity unit),
    the median ratio of their lengths. Pure; 100 with nothing to measure."""
    ratios = sorted(abs(b) / abs(a) for a, b in pairs if abs(a) > 1e-5 and abs(b) > 1e-5)
    if not ratios:
        return 100.0
    return ratios[len(ratios) // 2]


def _import_unity_anim(path, namespace, set_timeline):
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        text = handle.read()
    summary = unityfiles.anim_summary(text)
    if summary["kind"] == "humanoid":
        raise RuntimeError("{0}: {1}".format(summary["name"], unityfiles.HUMANOID))
    if summary["kind"] == "compressed":
        raise RuntimeError("{0}: {1}".format(summary["name"], unityfiles.COMPRESSED))
    curves = dict((p, t) for p, t in unityfiles.anim_curves(text).items() if p)
    if not curves:
        raise RuntimeError("{0}: no transform curves".format(summary["name"]))
    times, samples = unity_samples(curves, summary)
    leaves = sorted(set(p.split("/")[-1] for p in curves))
    model = model_for(path, leaves)
    if model is None:
        return _unity_without_model(summary, samples, times, namespace,
                                    set_timeline)
    return _unity_on_model(summary, samples, times, model, namespace,
                           set_timeline)


def _unity_without_model(summary, samples, times, namespace, set_timeline):
    """No model carries the bones: build them from the paths, each rest at
    its first position - which every animated path must have."""
    missing = sorted(p for p, s in samples.items() if not s.get("t"))
    if missing:
        raise RuntimeError(
            "{0}: no model beside it carries its bones, and {1} have no "
            "position curve to stand them on ({2})".format(
                summary["name"], len(missing), ", ".join(missing[:3])))
    paths = sorted(samples, key=lambda p: (p.count("/"), p))
    index = {}
    joints, tracks = [], []
    units = 100.0
    for path in paths:
        parent = path.rsplit("/", 1)[0] if "/" in path else None
        index[path] = len(joints)
        s = samples[path]
        joints.append({"name": path.split("/")[-1],
                       "parent": index.get(parent), "q": None, "order": "xyz",
                       "t": unityfiles.to_maya_position(s["t"][0], units)})
        tracks.append({"t": [unityfiles.to_maya_position(v, units) for v in s["t"]],
                       "q": [unityfiles.to_maya_rotation(q) for q in s["q"]]
                       if s.get("q") else None})
    return build(namespace, joints, tracks, [t - times[0] for t in times],
                 set_timeline, fps=summary.get("rate"),
                 warning="no model found: bones stood on the clip's own positions")


def _unity_on_model(summary, samples, times, model, namespace, set_timeline):
    """The clip onto the model's own skeleton: the model imported into the
    namespace, its bones keyed with the clip's local values in Maya's frame
    (rotate = RA⁻¹·Q·JO⁻¹, translate scaled by the measured units)."""
    import maya.api.OpenMaya as om
    animimport.import_clip(model, namespace, set_timeline=False, merge=False)
    by_leaf = {}
    for joint in _joints(namespace) + [
            n for n in (cmds.namespaceInfo(namespace, listOnlyDependencyNodes=True,
                                           recurse=True, dagPath=True) or [])
            if cmds.objExists(n) and cmds.nodeType(n) == "transform"]:
        by_leaf.setdefault(joint.split("|")[-1].split(":")[-1], joint)
    pairs = []
    for path, s in samples.items():
        node = by_leaf.get(path.split("/")[-1])
        if node and s.get("t"):
            rest = cmds.getAttr(node + ".translate")[0]
            pairs.extend(zip(s["t"][0], rest))
    units = units_from([(a, b) for a, b in pairs])
    mtimes = om.MTimeArray([om.MTime(t - times[0], om.MTime.kSeconds) for t in times])
    keyed, missing = 0, []
    for path, s in sorted(samples.items()):
        node = by_leaf.get(path.split("/")[-1])
        if node is None:
            missing.append(path.split("/")[-1])
            continue
        old = cmds.listConnections(node, source=True, destination=False,
                                   type="animCurve") or []
        if old:
            cmds.delete(old)
        if s.get("t"):
            for axis, attr in enumerate(("translateX", "translateY", "translateZ")):
                _write_curve(node, attr, mtimes,
                             [unityfiles.to_maya_position(v, units)[axis]
                              for v in s["t"]])
        if s.get("q"):
            jo = om.MEulerRotation([math.radians(v) for v in cmds.getAttr(
                node + ".jointOrient")[0]]) if cmds.nodeType(node) == "joint" \
                else om.MEulerRotation()
            ra = om.MEulerRotation([math.radians(v) for v in cmds.getAttr(
                node + ".rotateAxis")[0]])
            order = cmds.getAttr(node + ".rotateOrder")
            previous, eulers = None, []
            for q in s["q"]:
                local = om.MQuaternion(*unityfiles.to_maya_rotation(q)).asMatrix()
                rmat = ra.asMatrix().inverse() * local * jo.asMatrix().inverse()
                euler = om.MTransformationMatrix(rmat).rotation(asQuaternion=False)
                euler = euler.reorder(order)
                if previous is not None:
                    euler = euler.closestSolution(previous)
                previous = euler
                eulers.append(euler)
            for attr, key in (("rotateX", "x"), ("rotateY", "y"), ("rotateZ", "z")):
                _write_curve(node, attr, mtimes, [getattr(e, key) for e in eulers])
        keyed += 1
    unit = om.MTime.uiUnit()
    end = om.MTime(times[-1] - times[0], om.MTime.kSeconds).asUnits(unit)
    note = "on {0}'s skeleton ({1} bones keyed)".format(
        os.path.basename(model), keyed)
    if missing:
        note += "; not in the model: " + ", ".join(missing[:4])
    return _info(namespace, 0.0, end, summary.get("rate"), note, set_timeline)
