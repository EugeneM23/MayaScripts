"""maya_idle.scene - Idle Builder in the scene (2026-11-06, a draft).

A skeleton's own keys are its idle. The first Apply keeps them on its top joint (`skeldarIdleSource`: every
joint's rotate / translate channels on every frame, gzip + base64), so every later Apply rebuilds from the
same clip and Restore puts them back. The pose is a Pose Library card, carried onto the skeleton by
Walk Builder's road (maya_walk.pose._onto). Keys are written with Walk Builder's writer (base layer, auto
tangents). The knobs and the card are the card's (optionVars); `skeldarIdle` on the top joint keeps what was
applied.
"""
import base64
import gzip
import json
import math
import time

import numpy as np

from . import model as im

SOURCE_ATTR = "skeldarIdleSource"
MARKER = "skeldarIdle"
ROT = ("rotateX", "rotateY", "rotateZ")
TRANS = ("translateX", "translateY", "translateZ")
CHANNELS = TRANS + ROT


class Refusal(Exception):
    pass


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
    import sys
    st = getattr(sys, "_skeldar_idle", None)
    if st is None:
        st = sys._skeldar_idle = {"idles": {}, "working": []}
    return st


def _short(path):
    return path.rsplit("|", 1)[-1]


def _leaf(path):
    return _short(path).split(":")[-1]


# ---- which skeleton ----

def top_of(node):
    from maya_walk import scene as ws
    try:
        return ws.skeleton_root_of(node)
    except Exception:                                   # noqa: BLE001
        return None


def selected_tops():
    cmds = _cmds()
    out = []
    for node in cmds.ls(selection=True, long=True) or []:
        top = top_of(node)
        if top and top not in out:
            out.append(top)
    return out


def _joints(root):
    cmds = _cmds()
    joints = [root] + (cmds.listRelatives(root, allDescendents=True, type="joint", fullPath=True) or [])
    joints.sort(key=lambda p: (p.count("|"), p))
    return joints


# ---- the source ----

def _fps():
    from maya_walk import scene as ws
    return ws._fps()


def _curve_of(plug):
    cmds = _cmds()
    src = cmds.listConnections(plug, source=True, destination=False, skipConversionNodes=True) or []
    if src and cmds.nodeType(src[0]).startswith("animCurve"):
        return src[0]
    return None


def _capture(root):
    """{start, frames, channels: {leaf: {channel: [values]}}} - the skeleton's keys as they stand."""
    cmds, om, oma = _cmds(), _om(), _oma()
    joints = _joints(root)
    times = set()
    curves = {}
    for path in joints:
        for ch in CHANNELS:
            c = _curve_of(path + "." + ch)
            if c:
                curves[(path, ch)] = c
                times.update(cmds.keyframe(c, query=True, timeChange=True) or [])
    if not times:
        raise Refusal("%s carries no keys" % _short(root))
    start = int(math.floor(min(times) + 1e-6))
    end = int(math.ceil(max(times) - 1e-6))
    unit = om.MTime.uiUnit()
    mt = [om.MTime(float(t), unit) for t in range(start, end + 1)]
    channels = {}
    for path in joints:
        leaf = _leaf(path)
        row = {}
        for ch in CHANNELS:
            c = curves.get((path, ch))
            if c:
                sel = om.MSelectionList()
                sel.add(c)
                fn = oma.MFnAnimCurve(sel.getDependNode(0))
                vals = [fn.evaluate(t) for t in mt]
                if ch in ROT:
                    vals = [math.degrees(v) for v in vals]
            else:
                v = cmds.getAttr(path + "." + ch)
                vals = [float(v)] * len(mt)
            row[ch] = [float(v) for v in vals]
        channels[leaf] = row
    return {"start": start, "frames": end - start + 1, "fps": _fps(), "channels": channels}


def _pack(data):
    return base64.b64encode(gzip.compress(json.dumps(data).encode("utf-8"))).decode("ascii")


def _unpack(text):
    return json.loads(gzip.decompress(base64.b64decode(text)).decode("utf-8"))


def has_source(root):
    return bool(_cmds().attributeQuery(SOURCE_ATTR, node=root, exists=True))


def keep_source(root):
    """The source on the skeleton: kept from its keys the first time, then read from the attribute."""
    cmds = _cmds()
    if has_source(root):
        return _unpack(cmds.getAttr(root + "." + SOURCE_ATTR))
    data = _capture(root)
    cmds.addAttr(root, longName=SOURCE_ATTR, dataType="string")
    cmds.setAttr(root + "." + SOURCE_ATTR, _pack(data), type="string")
    return data


# ---- source -> model ----

def _euler_matrix(x, y, z, order):
    """(N, 3, 3) row-vector rotations from degree arrays, Maya's rotate order 0..5."""
    x, y, z = (np.radians(np.asarray(v, float)) for v in (x, y, z))
    n = x.shape[0]

    def rx(a):
        c, s = np.cos(a), np.sin(a)
        m = np.zeros((n, 3, 3)); m[:, 0, 0] = 1; m[:, 1, 1] = c; m[:, 1, 2] = s; m[:, 2, 1] = -s; m[:, 2, 2] = c
        return m

    def ry(a):
        c, s = np.cos(a), np.sin(a)
        m = np.zeros((n, 3, 3)); m[:, 1, 1] = 1; m[:, 0, 0] = c; m[:, 0, 2] = -s; m[:, 2, 0] = s; m[:, 2, 2] = c
        return m

    def rz(a):
        c, s = np.cos(a), np.sin(a)
        m = np.zeros((n, 3, 3)); m[:, 2, 2] = 1; m[:, 0, 0] = c; m[:, 0, 1] = s; m[:, 1, 0] = -s; m[:, 1, 1] = c
        return m

    mats = {"x": rx(x), "y": ry(y), "z": rz(z)}
    letters = ("xyz", "yzx", "zxy", "xzy", "yxz", "zyx")[int(order)]
    out = mats[letters[0]] @ mats[letters[1]] @ mats[letters[2]]
    return out


def _statics(path):
    cmds = _cmds()
    jo = cmds.getAttr(path + ".jointOrient")[0] if cmds.attributeQuery("jointOrient", node=path, exists=True) else (0, 0, 0)
    ra = cmds.getAttr(path + ".rotateAxis")[0]
    ro = cmds.getAttr(path + ".rotateOrder")
    return {"jointOrient": tuple(jo), "rotateAxis": tuple(ra), "rotateOrder": int(ro)}


def build_idle(root, data):
    cmds = _cmds()
    joints = _joints(root)
    index = dict((p, i) for i, p in enumerate(joints))
    parents = []
    for p in joints:
        above = cmds.listRelatives(p, parent=True, fullPath=True)
        parents.append(index.get(above[0], -1) if above else -1)
    names = [_leaf(p) for p in joints]
    N = int(data["frames"])
    L = np.zeros((len(joints), N, 4, 4))
    L[:, :, 3, 3] = 1.0
    statics = []
    for j, path in enumerate(joints):
        st = _statics(path)
        statics.append(st)
        ch = data["channels"].get(names[j])
        if ch is None:
            raise Refusal("the kept clip has no %s - Restore, then Apply again" % names[j])
        R = _euler_matrix(ch["rotateX"], ch["rotateY"], ch["rotateZ"], st["rotateOrder"])
        ra = _euler_matrix([st["rotateAxis"][0]], [st["rotateAxis"][1]], [st["rotateAxis"][2]], 0)[0]
        jo = _euler_matrix([st["jointOrient"][0]], [st["jointOrient"][1]], [st["jointOrient"][2]], 0)[0]
        L[j, :, :3, :3] = ra[None] @ R @ jo[None]
        L[j, :, 3, :3] = np.stack([ch["translateX"], ch["translateY"], ch["translateZ"]], -1)
    above = cmds.listRelatives(root, parent=True, fullPath=True)
    top = np.array(cmds.getAttr(above[0] + ".worldMatrix[0]"), float).reshape(4, 4) if above else np.eye(4)
    clip = im.Clip(names, parents, L, top)
    idle = im.Idle(clip)
    idle.paths = joints
    idle.statics = statics
    idle.start = int(data["start"])
    return idle


def idle_of(root):
    """The Idle read for `root`, cached by its source attribute."""
    cmds = _cmds()
    data = keep_source(root)
    text = cmds.getAttr(root + "." + SOURCE_ATTR)
    uuid = (cmds.ls(root, uuid=True) or [root])[0]
    cache = _state()["idles"]
    hit = cache.get(uuid)
    if hit and hit[0] == hash(text):
        return hit[1]
    idle = build_idle(root, data)
    cache[uuid] = (hash(text), idle)
    return idle


# ---- the pose ----

def card_bones(card_path):
    from maya_walk import cards as wcards
    return wcards.read_card(card_path)


def pose_for(root, idle, card_path):
    """pose_targets for the card on this skeleton, or None (no card)."""
    if not card_path:
        return None, ""
    from maya_walk import scene as ws, pose as wp, target as wt
    name, pose_bones = card_bones(card_path)
    statics, note = ws.read_bones(root)
    W = im.fk(idle.clip.names, idle.clip.parents,
              _mean_locals(idle), idle.clip.top_parent)[:, 0]
    names = [n for n in idle.clip.names if n in statics]
    worlds = [W[idle.clip.index[n]] for n in names]
    out = wp._onto(names, worlds, statics, pose_bones, wt, head=("head" in statics))[0]
    out = dict((leaf, wp._np(m)) for leaf, m in out.items())
    return im.pose_targets(idle, out), name


def _mean_locals(idle):
    L = np.zeros((len(idle.clip.names), 1, 4, 4))
    L[:, 0] = np.eye(4)
    for j in range(len(idle.clip.names)):
        L[j, 0, :3, :3] = idle.rot_mean[j]
        L[j, 0, 3, :3] = idle.trans[j].mean(0)
    return L


# ---- writing ----

def _channels(idle, L):
    """{path: {channel: values}} for every joint but the top: rotate (radians), translate for the pelvis and
    the helpers riding a bone."""
    from maya_poselib import skelsolve
    om = _om()
    cmds = _cmds()
    values = {}
    moved = set(idle.followers) | ({idle.pelvis} if idle.pelvis is not None else set())
    moved |= set(j for j in range(len(idle.paths)) if float(np.ptp(idle.trans[j], axis=0).max()) > 1e-4)
    for j, path in enumerate(idle.paths):
        st = idle.statics[j]
        current = [float(v) for v in cmds.getAttr(path + ".rotate")[0]]
        rows = dict((ch, []) for ch in (CHANNELS if j in moved else ROT))
        for t in range(L.shape[1]):
            m = om.MMatrix([float(v) for v in L[j, t].reshape(16)])
            turn = skelsolve.joint_channels(m, st["jointOrient"], st["rotateAxis"], st["rotateOrder"], current)
            current = list(turn)
            for i, ch in enumerate(ROT):
                rows[ch].append(math.radians(turn[i]))
            if j in moved:
                for i, ch in enumerate(TRANS):
                    rows[ch].append(float(L[j, t, 3, i]))
        values[path] = rows
    return values


def apply(root, given, card_path, parts):
    from maya_walk import scene as ws
    cmds = _cmds()
    began = time.time()
    idle = idle_of(root)
    pose, name = pose_for(root, idle, card_path) if card_path else (None, "")
    given = dict(given or {}, fps=_fps())
    L, info = im.evaluate(idle, given, pose, parts)
    values = _channels(idle, L)
    with ws._Chunk("Idle Builder"):
        written, held = ws.write_curves(values, {}, idle.start)
        if not cmds.attributeQuery(MARKER, node=root, exists=True):
            cmds.addAttr(root, longName=MARKER, dataType="string")
        cmds.setAttr(root + "." + MARKER, json.dumps({"knobs": im.knobs(given), "card": card_path or "",
                                                      "parts": list(parts)}), type="string")
    short = max(info["short"].values()) if info["short"] else 0.0
    line = "%s: %d frames%s, %.1f s" % (_short(root), info["frames"],
                                       (" on %s" % name) if name else "", time.time() - began)
    if short > 0.5:
        line += " | a foot %.1f cm out of reach" % short
    if info.get("held"):
        line += " | hands on the chest: " + ", ".join("%s %.1f cm" % (s.upper(), v) for s, v in sorted(info["held"].items()))
    if held:
        line += " | left to their drivers: %s" % ", ".join(sorted(held))
    return line


def restore(root):
    """The kept keys written back, the source attribute and the marker removed."""
    from maya_walk import scene as ws
    cmds = _cmds()
    if not has_source(root):
        raise Refusal("%s was not built by Idle Builder" % _short(root))
    data = _unpack(cmds.getAttr(root + "." + SOURCE_ATTR))
    values = {}
    for path in _joints(root):
        ch = data["channels"].get(_leaf(path))
        if not ch:
            continue
        values[path] = dict((c, [math.radians(v) if c in ROT else v for v in ch[c]]) for c in CHANNELS)
    with ws._Chunk("Idle Builder restore"):
        ws.write_curves(values, {}, int(data["start"]))
        cmds.deleteAttr(root + "." + SOURCE_ATTR)
        if cmds.attributeQuery(MARKER, node=root, exists=True):
            cmds.deleteAttr(root + "." + MARKER)
    _state()["idles"].pop((cmds.ls(root, uuid=True) or [root])[0], None)
    return "%s: its own keys back" % _short(root)


def memo(root):
    cmds = _cmds()
    if not cmds.attributeQuery(MARKER, node=root, exists=True):
        return None
    try:
        return json.loads(cmds.getAttr(root + "." + MARKER) or "{}")
    except ValueError:
        return None
