"""skeldar_walk.py - the parametric walk in Maya.

Drop this file into a viewport (or exec it): the window opens. Select any bone of a walk cycle, press
Analyse and turn the knobs: a copy beside the cycle re-keys itself from the model (walkmodel.py beside
this file) on every released slider. The cycle itself is never touched.

The design: docs/superpowers/specs/2026-10-12-parametric-walk-design.md.
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


def _load_model():
    spec = importlib.util.spec_from_file_location("skeldar_walkmodel", os.path.join(HERE, "walkmodel.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


wm = _load_model()
Refusal = wm.Refusal

MARKER = "skeldarWalk"
SUFFIX = "_walk"
DEFAULT_OFFSET = 100.0
CHANNELS = ("translateX", "translateY", "translateZ", "rotateX", "rotateY", "rotateZ")
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
    """Per session, on sys (a reloaded module must find it): the analysed walks by source UUID and the
    source the window works on."""
    state = getattr(sys, "_skeldar_walk", None)
    if state is None:
        state = {"walks": {}, "source": None}
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


def _euler_xyz(degrees):
    """jointOrient / rotateAxis as a row-vector matrix (both compose in xyz order)."""
    x, y, z = (math.radians(a) for a in degrees)
    return wm.exp_rot([x, 0.0, 0.0]) @ wm.exp_rot([0.0, y, 0.0]) @ wm.exp_rot([0.0, 0.0, z])


class Source(object):
    """The cycle in the scene: its joints (long paths, parents first), parent indices, the channels that
    carry keys, the first frame, its top node (the root's non-joint parent, or None) and that node's world."""

    def __init__(self, root, joints, parents, curves, start, top, top_world, uuid):
        self.root, self.joints, self.parents, self.curves = root, joints, parents, curves
        self.start, self.top, self.top_world, self.uuid = start, top, top_world, uuid


def read_source(root):
    """The cycle under `root` as a walkmodel.Clip, and where it lives (a Source)."""
    cmds = _cmds()
    if cmds.currentUnit(query=True, linear=True) != "cm":
        raise Refusal("the scene is not in centimetres")
    root = _long(root)
    joints = [root] + (cmds.listRelatives(root, allDescendents=True, type="joint", fullPath=True) or [])
    joints.sort(key=lambda p: p.count("|"))
    index = dict((p, i) for i, p in enumerate(joints))
    parents = []
    for path in joints:
        above = cmds.listRelatives(path, parent=True, fullPath=True)
        parents.append(index.get(above[0], -1) if above else -1)
    curves, times = [], set()
    for path in joints:
        keyed = []
        for ch in CHANNELS:
            found = cmds.keyframe(path, attribute=ch, query=True, timeChange=True)
            if found:
                keyed.append(ch)
                times.update(found)
        curves.append(keyed)
    if not times:
        raise Refusal("%s carries no keys" % _short(root))
    start, end = min(times), max(times)
    if abs(start - round(start)) > 1e-6 or abs(end - round(end)) > 1e-6:
        raise Refusal("the keys run %g-%g: a cycle starts and ends on whole frames" % (start, end))
    start, end = int(round(start)), int(round(end))
    above = cmds.listRelatives(root, parent=True, fullPath=True)
    top = above[0] if above else None
    top_world = np.eye(4)
    if top:
        if cmds.keyframe(top, query=True, keyframeCount=True):
            raise Refusal("%s (above the skeleton) is animated - the cycle must move by its root" % _short(top))
        top_world = np.array(cmds.getAttr(top + ".worldMatrix[0]", time=start)).reshape(4, 4)
    worlds = np.array([[cmds.getAttr(p + ".worldMatrix[0]", time=t) for t in range(start, end + 1)]
                       for p in joints]).reshape(len(joints), end - start + 1, 4, 4)
    up = (0.0, 1.0, 0.0) if cmds.upAxis(query=True, axis=True) == "y" else (0.0, 0.0, 1.0)
    scene = cmds.file(query=True, sceneName=True) or ""
    name = os.path.splitext(os.path.basename(scene))[0] or _short(top or root)
    clip = wm.Clip([_short(p) for p in joints], parents, worlds, _fps(), up, name)
    uuid = cmds.ls(root, uuid=True)[0]
    return clip, Source(root, joints, parents, curves, start, top, top_world, uuid)


def copy_top_of(node):
    """The copy a node belongs to: itself or the ancestor carrying the marker; None for anything else."""
    cmds = _cmds()
    parts = _long(node).split("|")
    for i in range(len(parts), 1, -1):
        path = "|".join(parts[:i])
        if cmds.attributeQuery(MARKER, node=path, exists=True):
            return path
    return None


def memo_of(copy):
    try:
        return json.loads(_cmds().getAttr(copy + "." + MARKER) or "{}")
    except ValueError:
        return {}


def source_root_of(node):
    """(the walk cycle's root joint, the copy the node belongs to or None) for any node of either."""
    cmds = _cmds()
    copy = copy_top_of(node)
    if copy:
        found = cmds.ls(memo_of(copy).get("source", ""), long=True)
        if not found:
            raise Refusal("%s's source cycle is gone from the scene" % _short(copy))
        return found[0], copy
    path = _long(node)
    if cmds.nodeType(path) != "joint":
        below = cmds.listRelatives(path, allDescendents=True, type="joint", fullPath=True) or []
        if not below:
            raise Refusal("%s holds no skeleton - select a bone of the walk cycle" % _short(path))
        path = min(below, key=lambda p: p.count("|"))
    while True:
        above = cmds.listRelatives(path, parent=True, fullPath=True)
        if not above or cmds.nodeType(above[0]) != "joint":
            return path, None
        path = above[0]


def copies_of(uuid):
    """Every copy made from the source with this UUID (by the marker - never a name pattern, trap 70)."""
    cmds = _cmds()
    out = []
    for node in cmds.ls(type="transform", long=True) or []:
        if cmds.attributeQuery(MARKER, node=node, exists=True) and memo_of(node).get("source") == uuid:
            out.append(node)
    return out


def walk_for(root, fresh=False):
    """The analysed walk for this root (cached for the session by UUID) and its Source."""
    state = _state()
    uuid = _cmds().ls(_long(root), uuid=True)[0]
    if fresh or uuid not in state["walks"]:
        clip, source = read_source(root)
        state["walks"][uuid] = (wm.analyse(clip), source)
    return state["walks"][uuid]


def _unlock(node, attrs=("translateX", "translateY", "translateZ")):
    for a in attrs:
        if _cmds().getAttr(node + "." + a, lock=True):
            _cmds().setAttr(node + "." + a, lock=False)


def make_copy(source):
    """A duplicate of the cycle's top (or of the root, under a new group, when it stands at world level),
    with no curves, marked."""
    cmds = _cmds()
    if source.top:
        copy = _long(cmds.duplicate(source.top, name=_short(source.top) + SUFFIX, returnRootsOnly=True)[0])
    else:
        dup = cmds.duplicate(source.root, returnRootsOnly=True)[0]
        copy = _long(cmds.group(empty=True, world=True, name=_short(source.root) + SUFFIX))
        dup = cmds.parent(dup, copy)[0]
        cmds.rename(copy + "|" + _short(dup), _short(source.root))
    cmds.addAttr(copy, longName=MARKER, dataType="string")
    _unlock(copy)
    return copy


def place(copy, source, walk, offset):
    """The copy's top where the source's stands, moved `offset` cm to the character's left."""
    at = source.top_world[3, :3] + walk.side * offset
    _cmds().xform(copy, worldSpace=True, translation=[float(v) for v in at])


def copy_paths(source, copy):
    """Each source joint's counterpart in the copy, in the source's order."""
    if source.top:
        return [copy + p[len(source.top):] for p in source.joints]
    return [copy + "|" + _short(source.root) + p[len(source.root):] for p in source.joints]


def channel_values(source, result, paths):
    """{joint index: {channel: [value a frame]}} for every channel the source keys: the joint's local
    matrix against its parent's new world (the root against the source top's), split into translate and
    rotate (R = RA^-1 . L . JO^-1 in the joint's rotate order, the euler nearest the frame before)."""
    cmds, om = _cmds(), _om()
    worlds = result.worlds
    out = {}
    for j, keyed in enumerate(source.curves):
        if not keyed:
            continue
        node = paths[j]
        order = cmds.getAttr(node + ".rotateOrder")
        ra_inv = _euler_xyz(cmds.getAttr(node + ".rotateAxis")[0]).T
        jo_inv = (_euler_xyz(cmds.getAttr(node + ".jointOrient")[0]).T
                  if cmds.nodeType(node) == "joint" else np.eye(3))
        p = source.parents[j]
        values = dict((ch, []) for ch in keyed)
        near = None
        for f in range(result.frames + 1):
            parent = worlds[p, f] if p >= 0 else source.top_world
            local = worlds[j, f] @ np.linalg.inv(parent)
            r = ra_inv @ wm.orthonormal(local[:3, :3]) @ jo_inv
            euler = om.MEulerRotation.decompose(om.MMatrix(wm.matrix(r, (0.0, 0.0, 0.0)).tolist()), order)
            if near is not None:
                euler = euler.closestSolution(near)
            near = euler
            for i, ch in enumerate(CHANNELS):
                if ch in values:
                    values[ch].append(float(local[3, i]) if i < 3 else (euler.x, euler.y, euler.z)[i - 3])
        out[j] = values
    return out


def write_curves(paths, values, start):
    """Each channel's old curve deleted and a new one keyed on frames start..start+N (auto tangents).
    The nodes go through cmds (Ctrl+Z removes them, and puts the deleted ones back); the keys through
    MFnAnimCurve.addKeys - measured 0.05 s for 540 curves against 0.8 s by setKeyframe."""
    cmds, om, oma = _cmds(), _om(), _oma()
    written = 0
    for j, channels in values.items():
        node = paths[j]
        for ch, vals in channels.items():
            plug = node + "." + ch
            old = cmds.listConnections(plug, source=True, destination=False, type="animCurve") or []
            if old:
                cmds.delete(old)
            if cmds.getAttr(plug, lock=True):
                cmds.setAttr(plug, lock=False)
            curve = cmds.createNode("animCurveTL" if ch.startswith("translate") else "animCurveTA",
                                    name="%s_%s" % (_short(node), ch))
            cmds.connectAttr(curve + ".output", plug)
            times = om.MTimeArray([om.MTime(float(start + f), om.MTime.uiUnit()) for f in range(len(vals))])
            selection = om.MSelectionList()
            selection.add(curve)
            oma.MFnAnimCurve(selection.getDependNode(0)).addKeys(
                times, om.MDoubleArray(vals), oma.MFnAnimCurve.kTangentAuto, oma.MFnAnimCurve.kTangentAuto)
            written += 1
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


def update(root, given=None, offset=None):
    """The copy of the cycle under `root` re-keyed from the knobs `given` (made on the first call), in one
    undo step. Returns (copy, result, the status line)."""
    cmds = _cmds()
    started = time.time()
    walk, source = walk_for(root)
    result = walk.evaluate(given)
    with _Chunk("skeldarWalk"):
        copies = copies_of(source.uuid)
        copy = copies[0] if copies else make_copy(source)
        if offset is None:
            offset = memo_of(copy).get("offset", DEFAULT_OFFSET)
        place(copy, source, walk, offset)
        paths = copy_paths(source, copy)
        write_curves(paths, channel_values(source, result, paths), source.start)
        memo = {"source": source.uuid, "knobs": result.info["knobs"], "offset": offset, "version": wm.VERSION}
        cmds.setAttr(copy + "." + MARKER, json.dumps(memo), type="string")
    line = "%s | %s: %s | %.2f s" % (walk.summary(), _short(copy), wm.describe(result), time.time() - started)
    return copy, result, line


def delete_copies(root):
    """Every copy of this cycle deleted (one undo step); returns how many."""
    walk, source = walk_for(root)
    copies = copies_of(source.uuid)
    if copies:
        with _Chunk("skeldarWalkDelete"):
            _cmds().delete(copies)
    return len(copies)
