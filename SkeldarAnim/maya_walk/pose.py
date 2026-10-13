"""maya_walk.pose - a character pose (any skeleton's) carried onto a walk's skeleton and read the way the model
takes it: the spine's and neck's local rotations, the head's and the pelvis's world rotations, the pelvis's
height over its feet (put over the walk's floor, as a height over the walk's travel line), the knees' turn from
the walk's mean heading.

The pose is posemath bones ({leaf: {parent, canonical, rest, world}}, `world` = the pose); the walk's
skeleton stands at its rest on the walk's root frame at its first frame; the size is the legs' ratio (1 for
a twin, walktarget's rule). numpy and maya.api.OpenMaya (through posemath) - no maya.cmds.
The design: docs/superpowers/specs/2026-10-12-walk-pose-design.md.
"""
import math

import numpy as np

from maya_poselib import posemath as pm

SIDES = ("l", "r")


def _np(m):
    return np.array(pm.flat(m)).reshape(4, 4)


def _heading(bend, walk):
    """A knee's bend direction as an angle about up, from forward toward the character's left (radians)."""
    return math.atan2(float(np.dot(bend, walk.side)), float(np.dot(bend, walk.fwd)))


def _bend(hip, knee, ankle):
    e = (ankle - hip) / np.linalg.norm(ankle - hip)
    b = (knee - hip) - np.dot(knee - hip, e) * e
    n = np.linalg.norm(b)
    return b / n if n > 1e-9 else None


def walk_floor(walk):
    """The walk's floor, up (cm): its feet's lowest - the lower ball over the cycle (else the lower ankle)."""
    names = ["ball_" + s for s in SIDES] if all("ball_" + s in walk.index for s in SIDES) else ["foot_" + s for s in SIDES]
    return float(min((walk.pos[walk.index[n]] @ walk.up).min() for n in names))


def pose_floor_gap(out, walk):
    """The pose's pelvis over its floor (cm up): over the lower of its two balls (else ankles)."""
    names = ["ball_" + s for s in SIDES] if all("ball_" + s in out for s in SIDES) else ["foot_" + s for s in SIDES]
    floor = min(float(np.dot(_np(out[n])[3, :3], walk.up)) for n in names)
    return float(np.dot(_np(out["pelvis"])[3, :3], walk.up)) - floor


def mean_knee_headings(walk):
    """{side: the walk's mean knee heading} - its bend directions over the cycle, averaged."""
    out = {}
    for side in SIDES:
        bends = []
        for f in range(walk.P):
            hip, knee, ankle = (walk.pos[walk.index["%s_%s" % (b, side)]][f] for b in ("thigh", "calf", "foot"))
            bend = _bend(hip, knee, ankle)
            if bend is not None:
                bends.append(bend)
        out[side] = _heading(np.mean(bends, axis=0), walk)
    return out


def _wrapped(angle):
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


def prepare(walk, statics, pose_bones, model, target_module):
    """The pose as walkmodel.Walk.evaluate takes it (its docstring). `model` the walkmodel module,
    `target_module` walktarget (its at_rest, leg lengths and twin rule)."""
    walk_rest = target_module.at_rest(dict((leaf, dict(b)) for leaf, b in statics.items()))
    first = {}
    for j, name in enumerate(walk.names):
        bone = dict(statics[name])
        bone["world"] = [float(v) for v in walk.clip.worlds[j, 0].reshape(16)]
        first[name] = bone
    pairs = pm.pairs(pose_bones, walk_rest)
    members = set(s for t, s in pairs.items() if not pm.is_helper(t))
    legs = ("thigh", "calf", "foot")
    missing = [n for n in ("pelvis", "head") + tuple("%s_%s" % (b, s) for s in SIDES for b in legs)
               if n not in pairs]
    if missing:
        raise target_module.Refusal("the pose's skeleton has nothing for the walk's %s" % ", ".join(missing))
    ratios = []
    for side in SIDES:
        walk_leaves = tuple("%s_%s" % (b, side) for b in legs)
        pose_leaves = tuple(pairs[leaf] for leaf in walk_leaves)
        ratios.append(sum(target_module._leg_lengths(walk_rest, walk_leaves)) /
                      max(sum(target_module._leg_lengths(pose_bones, pose_leaves)), 1e-9))
    legs_ratio = float(np.mean(ratios))
    same = pm.twin(pairs, pose_bones, walk_rest) and abs(legs_ratio - 1.0) <= target_module.LEG_TWIN
    transfer = pm.Transfer(pose_bones, walk_rest, pairs, members, scale=1.0 if same else legs_ratio)
    out = transfer.frame(root_world=transfer.place(first))
    rot = lambda name: model.orthonormal(_np(out[name])[:3, :3])
    spine = {}
    for j, name in enumerate(walk.names):
        parent = walk.parents[j]
        if walk.kind[j] == "spine" and name in out and parent >= 0:
            spine[j] = rot(name) @ rot(walk.names[parent]).T
    means = mean_knee_headings(walk)
    turn = {}
    for side in SIDES:
        hip, knee, ankle = (_np(out["%s_%s" % (b, side)])[3, :3] for b in legs)
        bend = _bend(hip, knee, ankle)
        turn[side] = 0.0 if bend is None else _wrapped(_heading(bend, walk) - means[side])
    # the pelvis over its feet, not over a root: over the lower of the pose's balls (its floor; the ball's own
    # height cancels - the pose stands on the walk's skeleton), put over the walk's floor (its lowest ball)
    height = (pose_floor_gap(out, walk) + walk_floor(walk)
              - float(np.dot(walk.origin, walk.up)))
    scale = 1.0 if same else legs_ratio
    arms = {}
    for j, name in enumerate(walk.names):
        parent = walk.parents[j]
        if walk.kind[j] in ("arm", "finger") and name in out and parent >= 0:
            arms[j] = rot(name) @ rot(walk.names[parent]).T
    weapons = {}
    for h, (body, rel) in walk.follows.items():
        name, body_name = walk.names[h], walk.names[body]
        if name.startswith("weapon_") and name in pairs and body_name in pairs:
            held = _np(pose_bones[pairs[name]]["world"]) @ np.linalg.inv(_np(pose_bones[pairs[body_name]]["world"]))
            held[:3, :3] = model.orthonormal(held[:3, :3])
            held[3, :3] *= scale
            weapons[h] = held
    ankle = dict((side, _np(out["foot_" + side])[3, :3]) for side in SIDES)
    width = float(np.dot(ankle["l"] - ankle["r"], walk.side)) - (walk.side_print("l") - walk.side_print("r"))
    toe = {}
    for side in SIDES:
        ball = "ball_" + side
        if ball not in out:
            continue
        mid = walk.feet[side].mid
        walk_toe = walk.wpos(walk.index[ball], mid) - walk.wpos(walk.index["foot_" + side], mid)
        pose_toe = _np(out[ball])[3, :3] - ankle[side]
        toe[side] = _wrapped(_heading(pose_toe, walk) - _heading(walk_toe, walk))
    # hands this near each other hold one thing together (a two-handed grip): it sways as one, they keep it
    hands = [_np(out["hand_" + side])[3, :3] for side in SIDES if "hand_" + side in out]
    grip = len(hands) == 2 and float(np.linalg.norm(hands[0] - hands[1])) < model.GRIP_DIST
    return {"spine": spine, "head": rot("head"), "pelvis": rot("pelvis"), "height": height, "knee_turn": turn,
            "arms": arms, "weapons": weapons, "grip": grip, "width": width, "toe": toe if len(toe) == 2 else {"l": 0.0, "r": 0.0},
            "scale": scale}


# what each of the window's checkboxes takes from a pose
PARTS = (("torso", ("spine", "head")), ("pelvis", ("pelvis", "height")), ("knees", ("knee_turn",)),
         ("arms", ("arms", "weapons", "grip")), ("feet", ("width", "toe")))


def filtered(pose, parts):
    """The prepared pose with only the parts named in `parts` (PARTS' names)."""
    keep = set(key for part, keys in PARTS if part in parts for key in keys)
    return dict((key, value) for key, value in pose.items() if key in keep or key == "scale")
