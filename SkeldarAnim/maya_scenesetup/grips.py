"""The grip a hand gives a weapon, remembered per weapon AND per hand.

Bone-relative, as since 2026-08-25: zeros mean exactly on the drive bone. The
right hand keeps the names it always had (`mayaSceneSetup_offset_<key>`, the
pre-rename `mayaWeapons_offset_<key>` read second); the left hand (2026-09-29,
two weapons per character) has `..._L`. A left grip nobody has dialled is the
MIRROR of the right one through the rig's own sockets (`bonedrive.mirror_grip`
- on Manny zero grip turns the left blade backwards, on the Creep it is
already right), recomputed each time, so it follows the right grip until the
left one is dialled.

Window policy the Weapons section and the inventory share, so both put the
same weapon into the same hand the same way.
"""

import math

import maya.api.OpenMaya as om
import maya.cmds as cmds

from maya_scenesetup import bonedrive
from maya_scenesetup import catalog
from maya_scenesetup import skeleton

_OPTIONVAR = "mayaSceneSetup_offset_{0}"
_LEGACY_OPTIONVAR = "mayaWeapons_offset_{0}"
ZERO = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))


def optionvar_name(key, side="R"):
    """Where `side`'s grip of weapon `key` is remembered."""
    name = _OPTIONVAR.format(key)
    return name if side == "R" else name + "_L"


def pack(rotate, translate):
    return [float(value) for value in tuple(rotate) + tuple(translate)]


def unpack(values):
    """Six stored numbers -> (rotate, translate). Anything else -> zeros.

    Maya answers a missing optionVar with 0 or an empty list, and a stored
    value of the wrong length can only come from an older version of this
    tool; half a grip is worse than none.
    """
    try:
        numbers = [float(value) for value in values]
    except (TypeError, ValueError):
        return ZERO
    if len(numbers) != 6:
        return ZERO
    return tuple(numbers[:3]), tuple(numbers[3:])


def stored(key, side="R"):
    """The remembered grip, or None when there is none - zeros are a real
    grip (exactly on the bone), so they cannot mean "nothing"."""
    names = [optionvar_name(key, side)]
    if side == "R":
        names.append(_LEGACY_OPTIONVAR.format(key))
    for name in names:
        if cmds.optionVar(exists=name):
            return unpack(cmds.optionVar(query=name))
    return None


def remember(key, side, rotate, translate):
    name = optionvar_name(key, side)
    cmds.optionVar(clearArray=name)
    for value in pack(rotate, translate):
        cmds.optionVar(floatValueAppend=(name, value))


def _parked_local(bone, weapon):
    """The bone's own local matrix from the track parked on `weapon` (a floor
    drop): its channels there, its own rotate order, jointOrient and
    rotateAxis. Joint order, row vectors: RA . R . JO, then the translation."""
    def value(channel):
        return cmds.getAttr(weapon + "." + bonedrive.park_attr(channel))

    order = cmds.getAttr(bone + ".rotateOrder")
    rotate = om.MEulerRotation(*[math.radians(value("rotate" + a)) for a in "XYZ"],
                               order=order).asMatrix()
    orient = om.MEulerRotation(*[math.radians(v) for v in
                                 cmds.getAttr(bone + ".jointOrient")[0]]).asMatrix() \
        if cmds.attributeQuery("jointOrient", node=bone, exists=True) else om.MMatrix()
    axis = om.MEulerRotation(*[math.radians(v) for v in
                               cmds.getAttr(bone + ".rotateAxis")[0]]).asMatrix()
    local = om.MTransformationMatrix(axis * rotate * orient)
    local.setTranslation(om.MVector(*[value("translate" + a) for a in "XYZ"]),
                         om.MSpace.kTransform)
    return tuple(local.asMatrix())


def socket_of(bone):
    """A drive bone's own LOCAL matrix in its hand. Its channels, or - while
    it follows a weapon lying on the floor, whose pose is not the bone's -
    the track parked on that weapon (measured live 2026-09-29: read the other
    way, weapon_l stood 134 cm off its hand and the mirror grip with it)."""
    weapon = bonedrive.driving_weapon(bone)
    if weapon and bonedrive.is_parked(weapon):
        return _parked_local(bone, weapon)
    return tuple(cmds.xform(bone, query=True, matrix=True, objectSpace=True))


def sockets(root, bone="weapon_r"):
    """The two drive bones' LOCAL matrices in their hands (right, left), or
    None when the skeleton lacks one. Read at the current frame: no clip on
    this disk moves them in the hand (trap 83)."""
    paths = [skeleton.resolve_bone(root, catalog.side_bone(bone, side))
             for side in catalog.SIDES]
    if not all(paths):
        return None
    return tuple(socket_of(path) for path in paths)


def for_hand(entry, side, root):
    """The grip `side`'s hand gives `entry`: the dialled one, else - the left
    hand - the right one's mirror through `root`'s sockets."""
    got = stored(entry.key, side)
    if got is not None:
        return got
    right = stored(entry.key, "R") or ZERO
    if side == "R":
        return right
    pair = sockets(root, entry.bone) if root else None
    if not pair:
        return ZERO
    # the frame the node will carry - the socket turn composed in (2026-09-30)
    return bonedrive.mirror_grip(right[0], right[1],
                                 bonedrive.socket_frame(
                                     getattr(entry, "frame", (0.0, 0.0, 0.0))),
                                 pair[0], pair[1])
