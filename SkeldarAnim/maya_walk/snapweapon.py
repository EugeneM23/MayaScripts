"""maya_walk.snapweapon - Snap weapon: the weapon lies on the shoulder through the whole walk (2026-11-11).

The animator's example (port 7006): a Manny rig, its Long Sword in Aim Mode, the IK hand and the aim TARGET both
riding the right clavicle (Tools > Across knots inside FKScapula_R), the target moved down the blade onto the
shoulder, the up left in Main - so the sword lies on the shoulder whatever the body does. «сделали такой же
функционал в нашем walk builder ... связать этот функционал с риг позой ... нажать кнопочку snap weapon».

`press(root)`: the working walker's mean pose rig read where it stands (`read`: the weapon in Aim Mode in one of
its hands - refused by name otherwise; the hand in its clavicle's frame, the weapon in the hand's, the target in
the frame of the clavicle nearest it, the up in the game root's, the other hand when it holds the blade too), kept
on the walker (scene's edits, "snap") and the walker keyed again. `unsnap(root)` drops it.

`apply(walk, worlds, snap)` (numpy, the scene's animate runs it LAST - after the parameters, the pose, the physics
and the rig pose / key poses layer, before In place): the hand rides its clavicle at its offset; it is swung about
the grip so the weapon it carries aims its axis at the clavicle's point with its up axis toward the up point
carried by the root (an object-up aim); the other hand rides the holding hand; the arms rebuilt by IK. A weapon on
a walker follows its hand by its own constraint, so the hand takes the blade's roll (in the example the weapon
turns in the hand; on a walker nothing else could turn it).

The design: docs/superpowers/specs/2026-11-11-walk-snap-weapon-design.md.
"""
import math

import numpy as np

VERSION = 1
GRIP_CM = 15.0                  # the other hand holds the weapon when it stands this near the blade
SIDES = ("l", "r")

NO_RIG = "no rig pose for %s - press Create, put the weapon in Aim Mode on it, then Snap weapon"
NO_AIM = ("no weapon in Aim Mode in %s's hands - Connections > Weapon > Aim Mode on the rig pose, move its "
          "target onto the shoulder, then Snap weapon")
SEVERAL = "%d weapons in Aim Mode in %s's hands - one at a time (Default the other)"
NOT_SNAPPED = "%s has no snapped weapon"


class Refusal(Exception):
    """What Snap weapon does not do, and why."""


# ---- the pure half ----

def _m(flat):
    return np.asarray(flat, float).reshape(4, 4)


def _flat(m):
    return [float(v) for v in np.asarray(m, float).reshape(16)]


def _unit(v):
    v = np.asarray(v, float)
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-12 else v


def _rigid(m):
    """`m` with its scale and shear taken out of the rotation rows (row vectors: rows are the axes)."""
    out = np.array(m, float)
    x = _unit(out[0, :3])
    y = out[1, :3] - np.dot(out[1, :3], x) * x
    y = _unit(y)
    out[0, :3], out[1, :3], out[2, :3] = x, y, np.cross(x, y)
    return out


def _point_in(point, m):
    """A world point in the frame of the world matrix `m` (row vectors)."""
    return (np.asarray(point, float) - m[3, :3]) @ np.linalg.inv(m[:3, :3])


def _point_of(local, m):
    return np.asarray(local, float) @ m[:3, :3] + m[3, :3]


def basis(aim, up):
    """Rows (aim, up', side): the aim axis, the up leaned onto the plane square to it, their cross - None where the
    up is parallel to the aim."""
    a = _unit(aim)
    u = np.asarray(up, float) - np.dot(up, a) * a
    if float(np.linalg.norm(u)) < 1e-6:
        return None
    u = _unit(u)
    return np.array([a, u, np.cross(a, u)])


def _segment_distance(p, a, b):
    ab = b - a
    t = 0.0 if float(np.dot(ab, ab)) < 1e-12 else min(max(float(np.dot(p - a, ab) / np.dot(ab, ab)), 0.0), 1.0)
    return float(np.linalg.norm(p - (a + ab * t)))


def record(mats, side, weapon, aim_vector, up_vector, target, up, label=""):
    """The snap, read off the rig's worlds: `mats` {leaf: 4x4} holding hand_<s>, clavicle_l / _r, root and (for a
    two-handed hold) the other hand; `weapon` its world, `aim_vector` / `up_vector` its constraint's axes in its own
    frame, `target` / `up` the controllers' world places. Plain numbers (kept on the walker)."""
    hand = _rigid(mats["hand_" + side])
    clav = dict((s, _rigid(mats["clavicle_" + s])) for s in SIDES if "clavicle_" + s in mats)
    if ("clavicle_" + side) not in mats:
        raise Refusal("the rig has no clavicle_%s" % side)
    target, up = np.asarray(target, float), np.asarray(up, float)
    anchor = min(clav, key=lambda s: float(np.linalg.norm(clav[s][3, :3] - target)))
    in_hand = _rigid(weapon) @ np.linalg.inv(hand)
    grip = in_hand[3, :3]
    aim = _unit(np.asarray(aim_vector, float) @ in_hand[:3, :3])
    upax = _unit(np.asarray(up_vector, float) @ in_hand[:3, :3])
    root = _rigid(mats["root"])
    out = {"version": VERSION, "side": side, "anchor": anchor, "label": label,
           "offset": _flat(hand @ np.linalg.inv(clav[side])),
           "grip": [float(v) for v in grip], "aim": [float(v) for v in aim], "up_axis": [float(v) for v in upax],
           "target": [float(v) for v in _point_in(target, clav[anchor])],
           "up": [float(v) for v in _point_in(up, root)], "other": None}
    other = "l" if side == "r" else "r"
    if ("hand_" + other) in mats:
        o = _rigid(mats["hand_" + other])
        g = _point_of(grip, hand)
        far = g + (target - g) * 2.0                   # the blade runs on past the shoulder point
        if _segment_distance(o[3, :3], g, far) <= GRIP_CM:
            out["other"] = _flat(o @ np.linalg.inv(hand))
    return out


def loads(raw):
    """A stored snap read back, or None (missing, another version, broken)."""
    if not isinstance(raw, dict) or int(raw.get("version", 0) or 0) != VERSION:
        return None
    try:
        if raw["side"] not in SIDES or raw["anchor"] not in SIDES:
            return None
        for key, size in (("offset", 16), ("grip", 3), ("aim", 3), ("up_axis", 3), ("target", 3), ("up", 3)):
            if len(raw[key]) != size:
                return None
        if raw.get("other") is not None and len(raw["other"]) != 16:
            return None
    except (KeyError, TypeError):
        return None
    return dict(raw)


def summary(snap):
    """«Long Sword 02 on the right shoulder, right hand» - what a snap holds, for a status line."""
    word = {"l": "left", "r": "right"}
    text = "%s on the %s shoulder, %s hand" % (snap.get("label") or "the weapon", word[snap["anchor"]],
                                              word[snap["side"]])
    return text + (" + the other" if snap.get("other") else "")


def apply(walk, worlds, snap):
    """(worlds, info): `worlds` (J, n+1, 4, 4, a walk's frames - never changed) with the snap on (the module
    docstring). info: {"deg": the most the hand rolled off its rigid offset, "off": the most a hand stood off where
    it was asked (cm: an arm too short), "note": why nothing was done}."""
    idx = walk.index
    s, a, o = snap["side"], snap["anchor"], ("l" if snap["side"] == "r" else "r")
    names = ["hand_" + s, "clavicle_" + s, "clavicle_" + a, "root"]
    chains = walk._arm_chains()
    missing = [n for n in names if n not in idx] + ([] if s in chains else ["the %s arm" % s])
    if missing:
        return worlds, {"deg": 0.0, "off": 0.0, "note": "no " + ", ".join(missing)}
    worlds = np.asarray(worlds, float)
    n = worlds.shape[1] - 1
    kin = worlds.copy()
    out = worlds.copy()
    offset, grip = _m(snap["offset"]), np.asarray(snap["grip"], float)
    aim, upax = np.asarray(snap["aim"], float), np.asarray(snap["up_axis"], float)
    target, up = np.asarray(snap["target"], float), np.asarray(snap["up"], float)
    Cs, Ca, R = kin[idx["clavicle_" + s]], kin[idx["clavicle_" + a]], kin[idx["root"]]
    H = np.array([offset @ _rigid(Cs[f]) for f in range(n + 1)])
    deg, last = 0.0, None
    for f in range(n + 1):
        G = _point_of(grip, H[f])
        T = _point_of(target, _rigid(Ca[f]))
        U = _point_of(up, _rigid(R[f]))
        B0 = basis(aim @ H[f, :3, :3], upax @ H[f, :3, :3])
        B1 = basis(T - G, U - G)
        if B1 is None:                                   # the up on the blade's line: keep the last roll
            B1 = last if last is not None else B0
        last = B1
        rot = B0.T @ B1
        swing = np.eye(4)
        swing[:3, :3] = rot
        swing[3, :3] = G - G @ rot
        H[f] = H[f] @ swing
        cos = (float(np.trace(rot)) - 1.0) / 2.0
        deg = max(deg, math.degrees(math.acos(min(max(cos, -1.0), 1.0))))
    hands = {s: H}
    if snap.get("other") is not None and o in chains:
        hands[o] = np.array([_m(snap["other"]) @ H[f] for f in range(n + 1)])
    new = walk._arm_to_hand(kin, n, dict((k, chains[k]) for k in hands), hands)
    walk._reattach(out, kin, new)
    off = 0.0
    for side, want in hands.items():
        got = out[chains[side][-1]]
        off = max(off, float(np.max(np.linalg.norm(got[:, 3, :3] - want[:, 3, :3], axis=1))))
    return out, {"deg": deg, "off": off, "note": ""}


def line(snap, info):
    """The status line's piece: «weapon snapped: Long Sword 02 on the right shoulder (rolled up to 7 deg)»."""
    if info.get("note"):
        return "weapon not snapped: " + info["note"]
    text = "weapon snapped: %s (rolled up to %.0f deg)" % (summary(snap), info.get("deg", 0.0))
    if info.get("off", 0.0) > 0.5:
        text += ", the hand %.1f cm short - the arm cannot reach" % info["off"]
    return text


# ---- the Maya half ----

def _cmds():
    import maya.cmds as cmds
    return cmds


def _world(node):
    return np.array(_cmds().xform(node, query=True, worldSpace=True, matrix=True), float).reshape(4, 4)


def read(rig):
    """The snap off the mean pose rig `rig` (a maya_rigs.Rig) as it stands: its one weapon in Aim Mode held in one of
    its hands. Refusal otherwise."""
    import maya_rigs
    from maya_scenesetup import weaponaim, weaponspace
    cmds = _cmds()
    found = []
    for group in weaponaim.groups():
        weapon = weaponaim.weapon_of_group(group)
        if not weapon or not cmds.objExists(weapon):
            continue
        hand = weaponspace.holding_hand(weapon)
        if not hand:
            continue
        for side in SIDES:
            if cmds.objExists(maya_rigs.node(rig, "hand_" + side)) and \
                    cmds.ls(maya_rigs.node(rig, "hand_" + side), long=True)[0] == cmds.ls(hand, long=True)[0]:
                found.append((side, weapon, group))
    if not found:
        raise Refusal(NO_AIM % rig.namespace)
    if len(found) > 1:
        raise Refusal(SEVERAL % (len(found), rig.namespace))
    side, weapon, group = found[0]
    con = weaponaim._constraint(weapon)
    ctrls = weaponaim.controllers(group)
    if not con or "target" not in ctrls or "up" not in ctrls:
        raise Refusal("%s's Aim Mode is broken - Default, then Aim Mode again" % weapon.rsplit("|", 1)[-1])
    mats = {}
    for leaf in ("hand_l", "hand_r", "clavicle_l", "clavicle_r", "root"):
        node = maya_rigs.node(rig, leaf)
        if cmds.objExists(node):
            mats[leaf] = _world(node)
    if "root" not in mats:
        raise Refusal("%s has no game root" % rig.namespace)
    label = weapon.rsplit("|", 1)[-1].split(":")[-1]
    try:
        from maya_scenesetup import bonedrive
        if cmds.attributeQuery(bonedrive.MARKER, node=weapon, exists=True):
            key = cmds.getAttr(weapon + "." + bonedrive.MARKER) or ""
            from maya_scenesetup import catalog
            label = next((w.label for w in catalog.WEAPONS if w.key == key), key or label)
    except Exception:                                    # noqa: BLE001 - a label is a nicety
        pass
    return record(mats, side, _world(weapon), cmds.getAttr(con + ".aimVector")[0],
                  cmds.getAttr(con + ".upVector")[0], _world(ctrls["target"])[3, :3], _world(ctrls["up"])[3, :3],
                  label)


def press(root, rekey):
    """Snap weapon: the walker `root`'s mean pose rig read, the snap kept on the walker, `rekey(root)` -> a tail."""
    from . import meanrig, scene
    rig = meanrig.find(root)
    if rig is None:
        raise Refusal(NO_RIG % scene.walker_label(root))
    snap = read(rig)
    memo = scene.memo_of(root)
    edits = scene.walker_edits(root, memo["walk"])[0]
    edits["snap"] = snap
    scene.set_edits(root, edits)
    return "%s: %s%s" % (scene.walker_label(root), summary(snap), rekey(root))


def unsnap(root, rekey):
    """Unsnap: the walker's snap dropped, the walker keyed again."""
    from . import scene
    memo = scene.memo_of(root)
    edits = scene.walker_edits(root, memo.get("walk") or "")[0]
    if not edits.get("snap"):
        raise Refusal(NOT_SNAPPED % scene.walker_label(root))
    edits["snap"] = None
    scene.set_edits(root, edits)
    return "%s: the weapon unsnapped%s" % (scene.walker_label(root), rekey(root))
