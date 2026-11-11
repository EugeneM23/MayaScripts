"""maya_walk.headaim - Head aim: the head looks at a target through the whole walk (2026-11-11).

The animator, after Snap weapon: «Давай для головы сделаем такую-же систему фиксации как и для оружия» - and,
asked which: like Snap weapon, «Где мы как бы будем создавать голове аим и контролировать ручкой насколько она
смотрит туда».

`press(root, rekey)`: on the working walker's mean pose rig a target control `HeadAim_ctrl` is made in front of the
head (under the rig's Main, where it already looks - so nothing moves yet), read, and kept on the walker (scene's
edits, "head"); the walker keyed again. The animator moves the target on the rig and presses Update (the rig pose's
Update reads it again, meanrig) or Head aim again. `remove(root, rekey)` drops it and the target control.

What is kept (`record`, pure): the head's look axis in its own frame (from the head toward the target when it was
read) and the target in the frame of the game ROOT - so the target travels with the walker and ignores the body's
bob, sway and twist, which is what a fixed gaze is.

`apply(walk, worlds, head, share)` (numpy; the scene's animate runs it after Snap weapon, before In place): on every
frame the head turned by the least swing taking its look axis onto the target, times `share` (the gait parameter
Head aim: 1 looks right at it, 0 the walk's own head), about the head's pivot, and everything under the head
carried with it; the roll about the look stays the walk's.

The design: docs/superpowers/specs/2026-11-11-walk-head-aim-design.md.
"""
import math

import numpy as np

VERSION = 1
HEAD = "head"
TARGET = "HeadAim_ctrl"         # the target control on the rig pose, in the rig's namespace
MARKER = "skeldarWalkHeadAim"   # on that control
AHEAD_CM = 150.0                # where a new target stands in front of the head
TARGET_SIZE = 8.0
TARGET_COLOUR = (0.35, 0.95, 0.55)

NO_RIG = "no rig pose for %s - press Create first, then Head aim"
NO_TARGET = "the rig pose's head target is gone - press Head aim to make it again"
NOT_AIMED = "%s's head has no aim"


class Refusal(Exception):
    """What Head aim does not do, and why."""


# ---- the pure half ----

def _unit(v):
    v = np.asarray(v, float)
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-12 else v


def _rigid(m):
    out = np.array(m, float)
    x = _unit(out[0, :3])
    y = _unit(out[1, :3] - np.dot(out[1, :3], x) * x)
    out[0, :3], out[1, :3], out[2, :3] = x, y, np.cross(x, y)
    return out


def _point_in(point, m):
    return (np.asarray(point, float) - m[3, :3]) @ np.linalg.inv(m[:3, :3])


def _point_of(local, m):
    return np.asarray(local, float) @ m[:3, :3] + m[3, :3]


def swing(a, b, share=1.0):
    """The row-vector rotation (3x3) of `share` of the least turn taking the unit `a` onto the unit `b`."""
    a, b = _unit(a), _unit(b)
    axis = np.cross(a, b)
    s = float(np.linalg.norm(axis))
    c = float(np.dot(a, b))
    angle = math.atan2(s, c) * float(share)
    if s < 1e-12:
        if c > 0.0 or abs(angle) < 1e-12:
            return np.eye(3)
        axis = np.cross(a, [1.0, 0.0, 0.0])                # opposite: any axis square to a
        if float(np.linalg.norm(axis)) < 1e-6:
            axis = np.cross(a, [0.0, 1.0, 0.0])
    k = _unit(axis)
    K = np.array([[0.0, -k[2], k[1]], [k[2], 0.0, -k[0]], [-k[1], k[0], 0.0]])
    column = np.eye(3) + math.sin(angle) * K + (1.0 - math.cos(angle)) * (K @ K)
    return column.T                                      # v @ M == column @ v


def record(head, root, target, label="", aim=None):
    """The head aim read off the rig's worlds: `head` and `root` 4x4, `target` the control's world place. `aim`:
    the head's look axis already kept (its own axes) - a target moved later turns the head toward it; None: the
    look is read now, from the head toward the target (a target just made where the head already looks)."""
    head, root = _rigid(head), _rigid(root)
    look = _unit(np.asarray(target, float) - head[3, :3])
    if float(np.linalg.norm(look)) < 1e-9:
        raise Refusal("the head target stands on the head")
    if aim is None:
        aim = look @ head[:3, :3].T                              # the look in the head's own axes
    return {"version": VERSION, "label": label,
            "aim": [float(v) for v in _unit(aim)],
            "target": [float(v) for v in _point_in(target, root)]}


def loads(raw):
    """A stored head aim read back, or None (missing, another version, broken)."""
    if not isinstance(raw, dict) or int(raw.get("version", 0) or 0) != VERSION:
        return None
    try:
        if len(raw["aim"]) != 3 or len(raw["target"]) != 3:
            return None
        [float(v) for v in list(raw["aim"]) + list(raw["target"])]
    except (KeyError, TypeError, ValueError):
        return None
    return dict(raw)


def summary(head):
    """«the head looks 150 cm ahead» - what a head aim holds, for a status line."""
    return "the head looks at a point %.0f cm from the root" % float(np.linalg.norm(head["target"]))


def apply(walk, worlds, head, share=1.0):
    """(worlds, info): `worlds` (J, n+1, 4, 4, never changed) with the head aimed (the module docstring). info:
    {"deg": the most the head turned off the walk's, "note": why nothing was done}."""
    idx = walk.index
    missing = [n for n in (HEAD, "root") if n not in idx]
    if missing:
        return worlds, {"deg": 0.0, "note": "no " + ", ".join(missing)}
    worlds = np.asarray(worlds, float)
    share = min(max(float(share), 0.0), 1.0)
    if share <= 1e-9:
        return worlds, {"deg": 0.0, "note": ""}
    out = worlds.copy()
    kids = dict((j, []) for j in range(len(walk.parents)))
    for j, p in enumerate(walk.parents):
        if p >= 0:
            kids[p].append(j)
    below, stack = [], [idx[HEAD]]
    while stack:
        k = stack.pop()
        below.append(k)
        stack.extend(kids[k])
    aim, target = np.asarray(head["aim"], float), np.asarray(head["target"], float)
    deg = 0.0
    for f in range(worlds.shape[1]):
        H = _rigid(worlds[idx[HEAD], f])
        P = H[3, :3]
        T = _point_of(target, _rigid(worlds[idx["root"], f]))
        M = swing(aim @ H[:3, :3], T - P, share)
        X = np.eye(4)
        X[:3, :3] = M
        X[3, :3] = P - P @ M
        for k in below:
            out[k, f] = worlds[k, f] @ X
        deg = max(deg, math.degrees(math.acos(min(max((float(np.trace(M)) - 1.0) / 2.0, -1.0), 1.0))))
    return out, {"deg": deg, "note": ""}


def line(head, share, info):
    """The status line's piece: «head aimed x1.00 (turned up to 7 deg)»."""
    if info.get("note"):
        return "head not aimed: " + info["note"]
    return "head aimed x%.2f (turned up to %.0f deg)" % (float(share), info.get("deg", 0.0))


# ---- the Maya half ----

def _cmds():
    import maya.cmds as cmds
    return cmds


def _world(node):
    return np.array(_cmds().xform(node, query=True, worldSpace=True, matrix=True), float).reshape(4, 4)


def target_of(rig):
    """The rig pose's head target control (its long path), or None - found by its marker among the children of
    the rig's Main, never by name."""
    cmds = _cmds()
    for child in cmds.listRelatives(rig.main, children=True, type="transform", fullPath=True) or []:
        if cmds.attributeQuery(MARKER, node=child, exists=True):
            return child
    return None


def ahead(head, clav_l, clav_r, up=(0.0, 1.0, 0.0)):
    """A point AHEAD_CM in front of the head: forward is the chest's facing (left = the clavicles' line, flat)."""
    up = _unit(up)
    left = np.asarray(clav_l, float)[3, :3] - np.asarray(clav_r, float)[3, :3]
    left = _unit(left - np.dot(left, up) * up)
    forward = _unit(np.cross(left, up))
    return np.asarray(head, float)[3, :3] + forward * AHEAD_CM


def ensure_target(rig):
    """The rig pose's head target: the standing one, else a new one in front of the head under the rig's Main."""
    import maya_rigs
    from maya_scenesetup import aimcore
    cmds = _cmds()
    found = target_of(rig)
    if found:
        return found
    head = _world(maya_rigs.node(rig, HEAD))
    point = ahead(head, _world(maya_rigs.node(rig, "clavicle_l")), _world(maya_rigs.node(rig, "clavicle_r")))
    ctrl = aimcore.control(maya_rigs.node(rig, TARGET), rig.main, aimcore.diamond(TARGET_SIZE), TARGET_COLOUR)
    uuid = cmds.ls(ctrl, uuid=True)[0]
    cmds.rename(ctrl, ":" + maya_rigs.node(rig, TARGET).lstrip(":"))     # in the rig's namespace (trap 254)
    ctrl = cmds.ls(uuid, long=True)[0]
    cmds.addAttr(ctrl, longName=MARKER, attributeType="bool")
    cmds.setAttr(ctrl + "." + MARKER, True)
    cmds.xform(ctrl, worldSpace=True, translation=[float(v) for v in point])
    return cmds.ls(uuid, long=True)[0]


def read(rig, aim=None):
    """The head aim off the rig pose `rig` as it stands (`aim`: the look axis kept, record's). Refusal without its
    target control."""
    import maya_rigs
    target = target_of(rig)
    if target is None:
        raise Refusal(NO_TARGET)
    cmds = _cmds()
    for leaf in (HEAD, "root"):
        if not cmds.objExists(maya_rigs.node(rig, leaf)):
            raise Refusal("%s has no %s" % (rig.namespace, leaf))
    return record(_world(maya_rigs.node(rig, HEAD)), _world(maya_rigs.node(rig, "root")),
                  _world(target)[3, :3], "head", aim)


def press(root, rekey):
    """Head aim: the walker `root`'s rig pose head target made (when missing) and read, kept on the walker,
    `rekey(root)` -> a tail."""
    from . import meanrig, scene
    rig = meanrig.find(root)
    if rig is None:
        raise Refusal(NO_RIG % scene.walker_label(root))
    made = target_of(rig) is None
    ensure_target(rig)
    memo = scene.memo_of(root)
    edits = scene.walker_edits(root, memo["walk"])[0]
    standing = edits.get("head")
    head = read(rig, None if made or not standing else standing["aim"])
    edits["head"] = head
    scene.set_edits(root, edits)
    said = ("the head target made on %s - move it, then Update" % rig.namespace) if made else summary(head)
    return "%s: %s%s" % (scene.walker_label(root), said, rekey(root))


def remove(root, rekey):
    """Remove: the walker's head aim dropped (and the rig pose's target control), the walker keyed again."""
    from . import meanrig, scene
    memo = scene.memo_of(root)
    edits = scene.walker_edits(root, memo.get("walk") or "")[0]
    rig = meanrig.find(root)
    target = target_of(rig) if rig is not None else None
    if not edits.get("head") and target is None:
        raise Refusal(NOT_AIMED % scene.walker_label(root))
    if target is not None:
        _cmds().delete(target)
    edits["head"] = None
    scene.set_edits(root, edits)
    return "%s: the head aim removed%s" % (scene.walker_label(root), rekey(root))
