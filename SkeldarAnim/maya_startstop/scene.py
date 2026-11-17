"""maya_startstop.scene - Start/Stop Builder in the scene (2026-11-17).

A skeleton's own keys are its clip - a stop (running, then standing) or a start (standing, then running). The
first Apply keeps them on its top joint (`skeldarStartStopSource`: every joint's translate / rotate on every whole
frame, gzip + base64), so every later Apply rebuilds from the same clip and Restore puts them back. The clip is
rebuilt from that by FK; the poses are Pose Library cards (`maya_walk.cards.read_card`); the result is keyed onto
the skeleton itself by Walk Builder's writer. `skeldarStartStop` on the top joint keeps what was applied.

The model is Pose on clip's (`model`, moved from docs/superpowers/plans/poseclip on 2026-11-17).
Spec: docs/superpowers/specs/2026-11-17-start-stop-builder-design.md (and 2026-10-14-pose-on-clip-design.md).
"""
import base64
import gzip
import json
import math
import os
import sys
import time

import numpy as np

from . import model

SOURCE_ATTR = "skeldarStartStopSource"
MARKER = "skeldarStartStop"
CLIP_LABEL = "skeldarClipLabel"
ROT = ("rotateX", "rotateY", "rotateZ")
TRANS = ("translateX", "translateY", "translateZ")
CHANNELS = TRANS + ROT
PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(PLUGIN, "assets", "manny_skeleton_template.json")
RUN_MODES = ("stand", "clip", "card")      # the run pose: the stand pose all along, the clip's / cycle's, a card

Refusal = model.Refusal


def _cmds():
    import maya.cmds as cmds
    return cmds


def _om():
    import maya.api.OpenMaya as om
    return om


def _state():
    """The session on sys (a reloaded module must find it), started afresh when the model module is not the one
    that filled it (an old entry's methods are the old code's - trap 226)."""
    st = getattr(sys, "_skeldar_startstop", None)
    if st is None or st.get("model") is not model:
        st = {"model": model, "entries": {}, "working": [], "cycle": None}
        sys._skeldar_startstop = st
    return st


def _short(path):
    return path.rsplit("|", 1)[-1]


def _leaf(path):
    return _short(path).split(":")[-1]


# ---- which skeleton ----

def top_of(node):
    """The top joint of the skeleton `node` belongs to (Walk Builder's rule: a bone, a mesh skinned to it, a group
    above it; a rig refused)."""
    from maya_walk import scene as ws
    try:
        return ws.skeleton_root_of(node)
    except ws.Refusal as error:
        raise Refusal(str(error))


def selected_tops():
    """Every skeleton the selection names, each once; nodes that name none are passed over."""
    out = []
    for node in _cmds().ls(selection=True, long=True) or []:
        try:
            top = top_of(node)
        except Refusal:
            continue
        if top and top not in out:
            out.append(top)
    return out


def _joints(root):
    cmds = _cmds()
    joints = [root] + (cmds.listRelatives(root, allDescendents=True, type="joint", fullPath=True) or [])
    joints.sort(key=lambda p: (p.count("|"), p))
    return joints


def _fps():
    from maya_walk import scene as ws
    try:
        return ws._fps()
    except ws.Refusal as error:
        raise Refusal(str(error))


# ---- the source: the skeleton's own keys, kept ----

def _key_times(joints):
    cmds = _cmds()
    times = set()
    for path in joints:
        for ch in CHANNELS:
            times.update(cmds.keyframe(path, attribute=ch, query=True, timeChange=True) or [])
    return times


def capture(root):
    """{start, frames, fps, channels: {leaf: {channel: [values]}}} - the skeleton's keys as they stand, every
    channel on every whole frame of its keys (rotations in degrees)."""
    cmds = _cmds()
    if cmds.currentUnit(query=True, linear=True) != "cm":
        raise Refusal("the scene is not in centimetres")
    joints = _joints(root)
    times = _key_times(joints)
    if not times:
        raise Refusal("%s carries no keys - select a skeleton carrying a start or a stop" % _short(root))
    start = int(math.floor(min(times) + 1e-6))
    end = int(math.ceil(max(times) - 1e-6))
    if end - start < 4:
        raise Refusal("%s carries %d frames - a start or a stop needs more" % (_short(root), end - start + 1))
    channels = {}
    for path in joints:
        row = {}
        for ch in CHANNELS:
            row[ch] = [float(cmds.getAttr(path + "." + ch, time=t)) for t in range(start, end + 1)]
        channels[_leaf(path)] = row
    return {"start": start, "frames": end - start + 1, "fps": _fps(), "channels": channels}


def pack(data):
    return base64.b64encode(gzip.compress(json.dumps(data).encode("utf-8"))).decode("ascii")


def unpack(text):
    return json.loads(gzip.decompress(base64.b64decode(text)).decode("utf-8"))


def has_source(root):
    return bool(_cmds().attributeQuery(SOURCE_ATTR, node=root, exists=True))


def source_text(root):
    return _cmds().getAttr(root + "." + SOURCE_ATTR) if has_source(root) else None


def keep_source(root):
    """The source on the skeleton: kept from its keys the first time, then read from the attribute."""
    cmds = _cmds()
    if has_source(root):
        return unpack(cmds.getAttr(root + "." + SOURCE_ATTR))
    data = capture(root)
    cmds.addAttr(root, longName=SOURCE_ATTR, dataType="string")
    cmds.setAttr(root + "." + SOURCE_ATTR, pack(data), type="string")
    return data


# ---- the source -> the model's clip ----

def euler_matrices(x, y, z, order):
    """(N, 3, 3) row-vector rotations from degree arrays in Maya's rotate order 0..5 (xyz, yzx, zxy, xzy, yxz,
    zyx)."""
    x, y, z = (np.radians(np.atleast_1d(np.asarray(v, float))) for v in (x, y, z))
    n = x.shape[0]

    def turn(a, i, j):
        c, s = np.cos(a), np.sin(a)
        m = np.tile(np.eye(3), (n, 1, 1))
        m[:, i, i], m[:, i, j], m[:, j, i], m[:, j, j] = c, s, -s, c
        return m

    mats = {"x": turn(x, 1, 2), "y": turn(y, 2, 0), "z": turn(z, 0, 1)}
    letters = ("xyz", "yzx", "zxy", "xzy", "yxz", "zyx")[int(order)]
    return mats[letters[0]] @ mats[letters[1]] @ mats[letters[2]]


def joint_statics(path):
    """A joint's jointOrient, rotateAxis (xyz degrees) and rotateOrder."""
    cmds = _cmds()
    jo = cmds.getAttr(path + ".jointOrient")[0] if cmds.attributeQuery("jointOrient", node=path, exists=True) \
        else (0.0, 0.0, 0.0)
    return {"jointOrient": tuple(float(v) for v in jo),
            "rotateAxis": tuple(float(v) for v in cmds.getAttr(path + ".rotateAxis")[0]),
            "rotateOrder": int(cmds.getAttr(path + ".rotateOrder"))}


def fk_worlds(parents, locals_, top):
    """(J, F, 4, 4) worlds from locals (J, F, 4, 4) down `parents` (parents first), the root's parent `top`
    (4, 4)."""
    out = np.empty_like(locals_)
    for j, p in enumerate(parents):
        out[j] = locals_[j] @ (out[p] if p >= 0 else top[None])
    return out


def locals_of(data, names, statics):
    """(J, F, 4, 4) local matrices from the source's channels: rotateAxis . R . jointOrient, the translate."""
    F = int(data["frames"])
    L = np.zeros((len(names), F, 4, 4))
    L[:, :, 3, 3] = 1.0
    for j, leaf in enumerate(names):
        ch = data["channels"].get(leaf)
        if ch is None:
            raise Refusal("the kept clip has no %s - Restore, then Apply again" % leaf)
        st = statics[j]
        R = euler_matrices(ch["rotateX"], ch["rotateY"], ch["rotateZ"], st["rotateOrder"])
        ra = euler_matrices(*st["rotateAxis"], order=0)[0]
        jo = euler_matrices(*st["jointOrient"], order=0)[0]
        L[j, :, :3, :3] = ra[None] @ R @ jo[None]
        L[j, :, 3, :3] = np.stack([ch["translateX"], ch["translateY"], ch["translateZ"]], -1)
    return L


def _parent_world(root):
    cmds = _cmds()
    above = cmds.listRelatives(root, parent=True, fullPath=True)
    return np.array(cmds.getAttr(above[0] + ".worldMatrix[0]"), float).reshape(4, 4) if above else np.eye(4)


def clip_name(root):
    """The clip's name: the character's clip label when it has one, else the scene's name, else the root."""
    cmds = _cmds()
    top = root
    while True:
        above = cmds.listRelatives(top, parent=True, fullPath=True)
        if not above:
            break
        top = above[0]
    for t in cmds.listRelatives(top, allDescendents=True, type="transform", fullPath=True) or []:
        if cmds.attributeQuery(CLIP_LABEL, node=t, exists=True):
            value = cmds.getAttr(t + "." + CLIP_LABEL)
            if value:
                return value.split(" + ")[0]
    try:
        from maya_scenetabs import scope
        scene_path = scope.scene_name(cmds)
    except Exception:                                   # noqa: BLE001
        scene_path = cmds.file(query=True, sceneName=True) or ""
    return os.path.splitext(os.path.basename(scene_path or ""))[0] or _short(root)


def _rest_world(joint):
    """The joint's bind: the inverse of a skinCluster's bindPreMatrix for it, else None."""
    cmds, om = _cmds(), _om()
    for plug in cmds.listConnections(joint + ".worldMatrix[0]", source=False, destination=True, plugs=True,
                                     type="skinCluster") or []:
        node, attr = plug.split(".", 1)
        if not attr.startswith("matrix["):
            continue
        index = attr[len("matrix["):].split("]")[0]
        bpm = cmds.getAttr("{0}.bindPreMatrix[{1}]".format(node, index))
        if bpm:
            return list(om.MMatrix(bpm).inverse())
    return None


def rest_statics(joints, clip, frame):
    """{leaf: {"parent", "canonical", "rest"}} of the clip's skeleton: a skinned joint rests at its bind; an
    unskinned one under a rested parent keeps its local (at `frame`) on its parent's rest; a skeleton with no
    skin rests at Manny's bind for the bones the template names; anything else as it stands at `frame`. Returns
    (statics, a note or "")."""
    binds = dict((p, _rest_world(p)) for p in joints)
    note = ""
    template = {}
    if not any(binds.values()) and os.path.exists(TEMPLATE):
        with open(TEMPLATE) as handle:
            template = dict((j["name"], j["world_matrix"]) for j in json.load(handle)["joints"])
        note = "no skin: the rest is Manny's bind (the template)"
    statics, rests = {}, {}
    for i, path in enumerate(joints):
        leaf, p = clip.names[i], clip.parents[i]
        now = clip.worlds[i, frame]
        if binds.get(path):
            rest = np.array(binds[path]).reshape(4, 4)
        elif leaf in template:
            rest = np.array(template[leaf], float).reshape(4, 4)
        elif p >= 0 and p in rests:
            rest = now @ np.linalg.inv(clip.worlds[p, frame]) @ rests[p]
        else:
            rest = now
        rests[i] = rest
        statics[leaf] = {"parent": clip.names[p] if p >= 0 else None, "canonical": leaf,
                         "rest": [float(v) for v in rest.reshape(16)]}
    return statics, note


class Entry(object):
    """One skeleton's clip read once (its kept source): the clip, its analysis, its statics, the poses prepared
    against it and the cycle's posture."""

    def __init__(self, root, data):
        cmds = _cmds()
        joints = _joints(root)
        index = dict((p, i) for i, p in enumerate(joints))
        parents = []
        for path in joints:
            above = cmds.listRelatives(path, parent=True, fullPath=True)
            parents.append(index.get(above[0], -1) if above else -1)
        names = [_leaf(p) for p in joints]
        self.joint_statics = [joint_statics(p) for p in joints]
        worlds = fk_worlds(parents, locals_of(data, names, self.joint_statics), _parent_world(root))
        self.clip = model.Clip(names, parents, worlds, float(data.get("fps") or _fps()), clip_name(root))
        self.start = int(data["start"])
        self.joints = joints
        self.uuid = (cmds.ls(root, uuid=True) or [root])[0]
        self.analysis = model.Analysis(self.clip)
        self.statics, self.note = rest_statics(joints, self.clip, self.analysis.mid)
        self.poses = {}
        self.postures = {}

    def pose(self, card):
        """(the card's name, `model.prepare`'s) - prepared once a card and its time."""
        from maya_walk import cards as wcards
        try:
            stamp = os.path.getmtime(os.path.join(card, "pose.json"))
        except OSError:
            stamp = 0.0
        key = (card, stamp)
        if key not in self.poses:
            try:
                name, bones = wcards.read_card(card)
            except wcards.Refusal as error:
                raise Refusal(str(error))
            self.poses[key] = (name, model.prepare(self.analysis, self.statics, bones))
        return self.poses[key]

    def posture(self, cycle):
        """The cycle's posture against this clip (`model.CyclePosture`), once a cycle."""
        if cycle["uuid"] not in self.postures:
            self.postures[cycle["uuid"]] = model.CyclePosture(self.analysis, self.statics, cycle["cycle"],
                                                              cycle["statics"], cycle["clip"].name)
        return self.postures[cycle["uuid"]]


def entry_of(root):
    """The Entry for `root`, cached by its kept source (the first call keeps it)."""
    keep_source(root)
    text = source_text(root)
    cmds = _cmds()
    uuid = (cmds.ls(root, uuid=True) or [root])[0]
    cache = _state()["entries"]
    hit = cache.get(uuid)
    if hit and hit[0] == hash(text):
        return hit[1]
    entry = Entry(root, unpack(text))
    cache[uuid] = (hash(text), entry)
    return entry


# ---- the cycle a stop starts on / a start ends on ----

def read_worlds(root):
    """The clip under `root` as it stands: every joint's world on every whole frame of its keys, (Clip, start,
    joints)."""
    cmds = _cmds()
    joints = _joints(root)
    index = dict((p, i) for i, p in enumerate(joints))
    parents = []
    for path in joints:
        above = cmds.listRelatives(path, parent=True, fullPath=True)
        parents.append(index.get(above[0], -1) if above else -1)
    times = _key_times(joints)
    if not times:
        raise Refusal("%s carries no keys - select a skeleton carrying a looping clip" % _short(root))
    start, end = int(math.floor(min(times) + 1e-6)), int(math.ceil(max(times) - 1e-6))
    worlds = np.array([[cmds.getAttr(p + ".worldMatrix[0]", time=t) for t in range(start, end + 1)]
                       for p in joints]).reshape(len(joints), end - start + 1, 4, 4)
    return model.Clip([_leaf(p) for p in joints], parents, worlds, _fps(), clip_name(root)), start, joints


def use_cycle(node):
    """The looping clip on the skeleton `node` belongs to as the card's cycle. Returns its line."""
    root = top_of(node)
    clip, _start, joints = read_worlds(root)
    cycle = model.Cycle(clip)
    statics, _note = rest_statics(joints, clip, 0)
    cmds = _cmds()
    uuid = (cmds.ls(root, uuid=True) or [root])[0]
    above = cmds.listRelatives(root, parent=True, fullPath=True)
    owner = _short(above[0]) if above else _short(root)
    name = "%s on %s (%d frames a loop at %g fps)" % (clip.name, owner, cycle.period, clip.fps)
    _state()["cycle"] = {"uuid": uuid, "name": name, "cycle": cycle, "statics": statics, "clip": clip}
    return name


def clear_cycle():
    _state()["cycle"] = None


def cycle():
    """The card's cycle while its skeleton stands, else None."""
    current = _state().get("cycle")
    if current is None:
        return None
    if not _cmds().ls(current["uuid"]):
        _state()["cycle"] = None
        return None
    return current


# ---- writing ----

def channel_values(entry, worlds):
    """{path: {channel: values}} for every joint: rotate in radians (nearest the frame before), translate."""
    from maya_poselib import skelsolve
    om = _om()
    cmds = _cmds()
    J, F = worlds.shape[:2]
    top = _parent_world(entry.joints[0])
    values = {}
    for j, path in enumerate(entry.joints):
        st = entry.joint_statics[j]
        p = entry.clip.parents[j]
        parent = worlds[p] if p >= 0 else np.tile(top, (F, 1, 1))
        current = [float(v) for v in cmds.getAttr(path + ".rotate")[0]]
        rows = dict((ch, []) for ch in CHANNELS)
        for f in range(F):
            local = worlds[j, f] @ np.linalg.inv(parent[f])
            m = om.MMatrix([float(v) for v in local.reshape(16)])
            turn = skelsolve.joint_channels(m, st["jointOrient"], st["rotateAxis"], st["rotateOrder"], current)
            current = list(turn)
            for i, ch in enumerate(ROT):
                rows[ch].append(math.radians(turn[i]))
            for i, ch in enumerate(TRANS):
                rows[ch].append(float(local[3, i]))
        values[path] = rows
    return values


def _weapon_links(entry):
    try:
        from maya_scenesetup import bonedrive
    except ImportError:
        return None, []
    bones = [p for p in entry.joints if _leaf(p) in ("weapon_r", "weapon_l")]
    return bonedrive, (bonedrive.find_links(bones) if bones else [])


def write(entry, worlds, memo):
    """The worlds keyed onto the skeleton (one undo step): a weapon driving its bone lets go for the write and
    takes the new track back; `memo` kept on the top joint. Returns {bone: what drives it} left alone."""
    from maya_walk import scene as ws
    cmds = _cmds()
    root = entry.joints[0]
    values = channel_values(entry, worlds)
    bonedrive, links = _weapon_links(entry)
    with ws._Chunk("Start/Stop Builder"):
        for bone, _weapon in links:
            bonedrive.unlink(bone)
        _written, held = ws.write_curves(values, {}, entry.start)
        for bone, weapon in links:
            bonedrive.relink(weapon, bone)
        if not cmds.attributeQuery(MARKER, node=root, exists=True):
            cmds.addAttr(root, longName=MARKER, dataType="string")
        cmds.setAttr(root + "." + MARKER, json.dumps(memo), type="string")
    return held, links


# ---- the press ----

def start_pose(entry, run_mode, run_card):
    """The model's start pose for the run mode: None (the stand pose all along), the cycle's posture or the clip's
    own run (OWN_RUN), or a card's; and how the line names it."""
    if run_mode == "stand":
        return None, None
    if run_mode == "clip":
        current = cycle()
        if current is not None:
            return entry.posture(current), "the cycle's posture"
        return model.OWN_RUN, "the clip's own run"
    if not run_card:
        raise Refusal("Run pose is Card: drop a pose card into the run well (or pick Stand or Clip)")
    name, pose = entry.pose(run_card)
    return pose, name


def apply(root, k, stand_card, run_mode="stand", run_card=None):
    """`root`'s clip rebuilt with the stand pose (a card's path or None), the run pose (`run_mode`) and the knobs
    `k`, keyed onto `root`. Returns the line."""
    began = time.time()
    current = cycle()
    if current is not None and current["uuid"] == (_cmds().ls(root, uuid=True) or [None])[0]:
        raise Refusal("%s is the cycle - clear the cycle or pick another skeleton" % label(root))
    entry = entry_of(root)
    pose, pose_name = (None, None)
    if stand_card:
        pose_name, pose = entry.pose(stand_card)
    begin, begin_name = start_pose(entry, run_mode, run_card)
    from maya_walk import scene as ws
    weapons = ws.weapons_in_hands(root)        # the hands the scene gives a weapon (Hold, Aim target's lever)
    result = model.evaluate(entry.analysis, pose, k=k, start=begin, cycle=current["cycle"] if current else None,
                            weapons=weapons)
    memo = {"stand": stand_card or "", "run_mode": run_mode, "run": run_card or "", "knobs": dict(k),
            "cycle": current["uuid"] if current else "", "transition": entry.analysis.transition}
    held, links = write(entry, result.worlds, memo)
    return status(entry, result, root, pose_name, begin_name, held, links, time.time() - began)


def restore(root):
    """The kept keys written back, the source attribute and the marker removed (one undo step)."""
    from maya_walk import scene as ws
    cmds = _cmds()
    if not has_source(root):
        raise Refusal("%s was not built by Start/Stop Builder" % label(root))
    data = unpack(cmds.getAttr(root + "." + SOURCE_ATTR))
    values = {}
    for path in _joints(root):
        ch = data["channels"].get(_leaf(path))
        if not ch:
            continue
        values[path] = dict((c, [math.radians(v) if c in ROT else v for v in ch[c]]) for c in CHANNELS)
    with ws._Chunk("Start/Stop Builder restore"):
        ws.write_curves(values, {}, int(data["start"]))
        cmds.deleteAttr(root + "." + SOURCE_ATTR)
        if cmds.attributeQuery(MARKER, node=root, exists=True):
            cmds.deleteAttr(root + "." + MARKER)
    _state()["entries"].pop((cmds.ls(root, uuid=True) or [root])[0], None)
    return "%s: its own keys back" % label(root)


def memo(root):
    cmds = _cmds()
    if not cmds.attributeQuery(MARKER, node=root, exists=True):
        return None
    try:
        return json.loads(cmds.getAttr(root + "." + MARKER) or "{}")
    except ValueError:
        return None


def built():
    """Every skeleton Start/Stop Builder has built in the scene (its top joint keeps the source)."""
    cmds = _cmds()
    found = cmds.ls("*." + SOURCE_ATTR, recursive=True, objectsOnly=True, long=True, type="joint") or []
    try:
        from maya_scenetabs import scope
        found = scope.active_only(found)
    except Exception:                                   # noqa: BLE001
        pass
    return sorted(set(found))


def label(root):
    """A skeleton as the list names it: its character group without _Character, else its parent, else root."""
    cmds = _cmds()
    above = cmds.listRelatives(root, parent=True, fullPath=True)
    if above:
        name = _short(above[0])
        return name[:-len("_Character")] if name.endswith("_Character") else name
    return _short(root)


# ---- the line ----

KIND = {"stop": "a stop", "start": "a start", "cycle": "a cycle (no still stretch)"}


def status(entry, result, root, pose_name, start_name, held, links, seconds):
    """The line an Apply leaves: what it is, the poses, what the rules did."""
    info = result.info
    a = entry.analysis
    r0, r1 = a.reference
    s = entry.start
    poses = pose_name or "no stand pose"
    if start_name:
        poses = "%s > %s" % (start_name, poses) if a.transition != "start" else "%s > %s" % (poses, start_name)
    text = "%s: %s, %s | standing %d-%d" % (label(root), KIND.get(a.transition, a.transition), poses, s + r0, s + r1)
    stance = [v for v in info["final"].values() if v is not None]
    if stance:
        text += " | the %s steps on the stand pose's stance" % ("first" if a.transition == "start" else "last")
    if info["drop"] > 0.05:
        text += " | sunk %.1f cm where a planted foot was out of reach" % info["drop"]
    if info["short"] > 0.05:
        text += " | a planted foot %.1f cm short" % info["short"]
    if info["forward"] < 0.99:
        text += " | the clip's forward lean x%.2f" % info["forward"]
    if start_name:
        frames = info.get("start_frames")
        if frames is None:
            text += " | the run pose holds no frame (the body never runs past Stand pose at)"
        else:
            text += " | the run pose holds %d-%d" % (s + frames[0], s + frames[1])
    if info["grip"]:
        text += " | two-handed grip held"
    from . import weapon
    text += weapon.line(info.get("weapon") or {})
    cyc = info.get("cycle") or {}
    if cyc:
        current = cycle()
        name = current["name"].split(" (")[0] if current else "the cycle"
        if cyc.get("end"):
            text += " | ends on %s's frame %.2f, over its last %d frames" % (name, cyc["phase"], cyc["frames"])
        else:
            text += " | starts on %s's frame %.2f, over %d frames" % (name, cyc["phase"], cyc["frames"])
    if links:
        text += " | weapon re-seated"
    if held:
        text += " | left to what drives them: %s" % ", ".join(sorted(held))
    if entry.note:
        text += " | " + entry.note
    return text + " | %.1f s" % seconds
