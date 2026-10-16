"""Drop weapon (2026-10-16): a weapon held in a hand is let go at the fall and lands on the floor.

The weapon ends on the Inventory's floor road (`maya_scenesetup.floor`): out of the hand, in the
character's group, its drive bone parked on it and following its socket (`bonedrive.park` +
`drive_socket`) - so Inventory and Connections read it as a weapon on the floor. Its own keys:
- the BASE layer carries the hand's track over the whole take (sampled before anything changes),
  so with the fall's layer muted the weapon still rides the hand;
- the fall's layer (or the base layer, in that mode) carries the simulated track over the fall.

A weapon the hands ride (Connections) is left in place, said.
"""

import math

import maya.api.OpenMaya as om
import maya.cmds as cmds
import numpy as np

from maya_ragdoll import plan

MASS = 2.0              # kg
WEAPON_PREFIX = "weapon_"


def held(ref):
    """[(side, weapon path, bone path)] of the weapons `ref` holds in its hands, or []."""
    from maya_scenesetup import connections, equip
    out = []
    for side in ("R", "L"):
        weapon, where = equip.occupant(ref.root, side)
        if not weapon or where != "hand":
            continue
        if connections.followers_of(weapon):
            continue
        _hand, bone = equip.bones(ref.root, side)
        out.append((side, (cmds.ls(weapon, long=True) or [weapon])[0], bone))
    return out


def mat_of(node):
    return plan.mat(cmds.xform(node, query=True, worldSpace=True, matrix=True))


def local_box(weapon):
    """(centre, size) of the weapon's shapes in its own axes, scale applied (a box: the body)."""
    lo, hi = np.full(3, 1e18), np.full(3, -1e18)
    for shape in cmds.listRelatives(weapon, shapes=True, fullPath=True) or []:
        if cmds.getAttr(shape + ".intermediateObject"):
            continue
        lo = np.minimum(lo, cmds.getAttr(shape + ".boundingBoxMin")[0])
        hi = np.maximum(hi, cmds.getAttr(shape + ".boundingBoxMax")[0])
    if lo[0] > hi[0]:
        return np.zeros(3), np.ones(3) * 5.0
    scale = np.array(cmds.getAttr(weapon + ".scale")[0])
    return (lo + hi) * 0.5 * scale, np.maximum((hi - lo) * np.abs(scale), 1.0)


def body_frame(weapon_world, centre):
    """The box body's frame: the weapon's own axes, its box's centre."""
    rigid = plan.rigid(weapon_world)
    return plan.frame(plan.rot(weapon_world), plan.pos(plan.frame(np.identity(3), centre) @ rigid))


def sample(weapons, lo, hi):
    """{weapon: {frame: 4x4 world}} over lo..hi, the scene as it stands (no layer of ours yet)."""
    out = dict((w, {}) for w in weapons)
    for t in range(lo, hi + 1):
        cmds.currentTime(t)
        for w in weapons:
            out[w][t] = mat_of(w)
    return out


def _local(world, weapon):
    """translate, rotate (degrees, the weapon's rotate order) of `world` under the weapon's parent."""
    parent = plan.mat(cmds.getAttr(weapon + ".parentInverseMatrix[0]"))
    m = om.MTransformationMatrix(om.MMatrix(plan.flat(world @ parent)))
    order = cmds.getAttr(weapon + ".rotateOrder")
    euler = m.rotation(asQuaternion=False).reorder(order)
    return list(m.translation(om.MSpace.kTransform)), [math.degrees(v) for v in
                                                        (euler.x, euler.y, euler.z)]


def _key_track(weapon, track, layer=None):
    """Key the weapon's translate / rotate on every frame of `track` {frame: 4x4 world}, keeping
    its scale: on `layer` (a name) when given, else plain keys."""
    scale = np.array(cmds.getAttr(weapon + ".scale")[0])
    for t in sorted(track):
        unscaled = track[t].copy()
        unscaled[:3, :3] = plan.rot(track[t])
        translate, rotate = _local(unscaled, weapon)
        for attr, value in zip(("translateX", "translateY", "translateZ", "rotateX", "rotateY",
                                "rotateZ"), translate + rotate):
            kw = {"animLayer": layer} if layer else {}
            cmds.setKeyframe(weapon, attribute=attr, time=t, value=value, **kw)
    del scale


def drop(ref, weapons, hand_tracks, sim_tracks, layer):
    """Every held weapon onto the floor road (`maya_scenesetup.floor`'s state): its bone unlinked
    (the bone's animation back), the weapon out to the character's group, keyed with the hand's
    track on the base and the simulated one over the fall (on `layer` when given), the bone parked
    on it and following its socket. Inside the caller's undo chunk. The line."""
    from maya_scenesetup import bonedrive, chargroup
    names = []
    for side, weapon, bone in weapons:
        uuid = cmds.ls(weapon, uuid=True)[0]
        bonedrive.unlink(bone)
        path = cmds.ls(uuid, long=True)[0]
        path = cmds.parent(path, world=True)[0]
        path = chargroup.park(path, bone) or cmds.ls(uuid, long=True)[0]
        with bonedrive._autokey_off():
            for attr in ("translate", "rotate"):
                for axis in "XYZ":
                    plug = path + "." + attr + axis
                    cmds.setAttr(plug, lock=False)
                    cmds.cutKey(path, attribute=attr + axis, clear=True)
            _key_track(path, hand_tracks[weapon])
            if layer:
                for attr in ("translate", "rotate"):
                    for axis in "XYZ":
                        cmds.animLayer(layer, edit=True, attribute=path + "." + attr + axis)
            _key_track(path, sim_tracks[weapon], layer)
            bonedrive.euler_filter(path)
            bonedrive.park(path, bone)
            bonedrive.drive_socket(path, bone)
        names.append(path.split("|")[-1].split(":")[-1])
    if not names:
        return ""
    return "%s dropped" % ", ".join(names)
