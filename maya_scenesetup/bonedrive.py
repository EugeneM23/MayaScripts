"""A bone that follows a marked node.

The Camera Setup pattern generalised: the animator's thing (the weapon)
carries the animation and the export bone is parent-constrained to it,
`maintainOffset=False` -- the bone lives in the node's frame, so wherever the
sword is, the bone is, and the export is honest. `attach` builds the link at
Add, and the UE bridge unlinks/relinks around a merge (the constraint would
otherwise trip the rigged-skeleton refusal, trap 37).

A leaf module on purpose: maya.cmds and OpenMaya only, so `attach` can depend
on it and the bridge can import it lazily without dragging a window in.
"""

import math
from contextlib import contextmanager

import maya.api.OpenMaya as om
import maya.cmds as cmds

# The weapon marker. Defined here (the leaf) and re-exported by `attach`, so
# every existing `attach.MARKER` reader keeps working.
MARKER = "mayaWeapon"

# The dialled grip, stored on the marked node itself (raw under-hand
# channels, same space as the optionVar the window keeps). It lives HERE so
# `relink` can put the sword back on its grip after a clip import rewrote
# the bone -- the optionVar is window policy, out of this module's reach,
# and an attribute travels with the scene file where an optionVar does not.
GRIP_ROTATE = "mayaWeaponGripRotate"
GRIP_TRANSLATE = "mayaWeaponGripTranslate"

CHANNELS = tuple(channel + axis
                 for channel in ("translate", "rotate") for axis in "XYZ")


# ------------------------------------------------------------------- pure

def union_range(start, end, times):
    """The playback range widened to cover `times`.

    Trap 38 from the export side: a bake narrower than the keys silently
    truncates them, so every bake here covers both ranges.
    """
    if times:
        start = min(start, min(times))
        end = max(end, max(times))
    return start, end


def matrix_of(rotate, translate):
    """Grip channels (XYZ degrees, no scale) as a local matrix, 16 floats."""
    matrix = om.MTransformationMatrix()
    matrix.setRotation(om.MEulerRotation(*[math.radians(v) for v in rotate]))
    matrix.setTranslation(om.MVector(*translate), om.MSpace.kTransform)
    return tuple(matrix.asMatrix())


def composed_grip(rotate, translate, bone_local):
    """An old-scheme grip (channels under weapon_r) as under-hand channels.

    The sword's world position is identical in both schemes by construction:
    the old channels rode `weapon_r`, so composing them onto the bone's local
    matrix relative to the hand is the same world placement, expressed where
    the channels now live.
    """
    product = (om.MMatrix(matrix_of(rotate, translate))
               * om.MMatrix(bone_local))
    frame = om.MTransformationMatrix(product)
    euler = frame.rotation(asQuaternion=False).reorder(om.MEulerRotation.kXYZ)
    shift = frame.translation(om.MSpace.kTransform)
    return (tuple(math.degrees(v) for v in (euler.x, euler.y, euler.z)),
            (shift.x, shift.y, shift.z))


# ------------------------------------------------------------------- scene

@contextmanager
def _autokey_off():
    """Trap 14: the user works with autoKey ON; scripted pokes must not key."""
    state = cmds.autoKeyframe(query=True, state=True)
    cmds.autoKeyframe(state=False)
    try:
        yield
    finally:
        cmds.autoKeyframe(state=state)


def bake_range(node):
    """The playback range widened to `node`'s own keys."""
    start = cmds.playbackOptions(query=True, minTime=True)
    end = cmds.playbackOptions(query=True, maxTime=True)
    return union_range(start, end,
                       cmds.keyframe(node, query=True, timeChange=True) or [])


def local_matrix(node, parent):
    """`node`'s matrix relative to `parent`, from world matrices.

    World matrices rather than the local channels: a joint's local matrix
    hides jointOrient and rotateAxis, and this module must not care.
    """
    child = om.MMatrix(cmds.xform(node, query=True, matrix=True,
                                  worldSpace=True))
    above = om.MMatrix(cmds.xform(parent, query=True, matrix=True,
                                  worldSpace=True))
    return tuple(child * above.inverse())


def _constraints_on(bone):
    return cmds.listRelatives(bone, children=True, type="parentConstraint",
                              fullPath=True) or []


def driving_weapon(bone):
    """The marked node whose parentConstraint drives `bone`, or None.

    Found through the constraint's target list and the marker, never by
    name: a constraint whose driver carries no marker is somebody else's
    rig, and this module must not touch it.
    """
    for constraint in _constraints_on(bone):
        for target in cmds.parentConstraint(constraint, query=True,
                                            targetList=True) or []:
            paths = cmds.ls(target, long=True) or []
            if paths and cmds.attributeQuery(MARKER, node=paths[0],
                                             exists=True):
                return paths[0]
    return None


def find_links(joints):
    """[(bone, weapon)] for the joints our marked nodes drive. Read-only."""
    found = []
    for joint in joints:
        weapon = driving_weapon(joint)
        if weapon:
            found.append((joint, weapon))
    return found


def moves(node):
    """Whether any transform channel carries keys that actually change.

    "Has animCurves" is not "has animation" (trap 30): builds leave constant
    baked curves behind, and transferring a constant is worse than nothing --
    the weapon's channels end up keyed and the grip fields go quiet.
    """
    for channel in CHANNELS:
        values = cmds.keyframe("{0}.{1}".format(node, channel), query=True,
                               valueChange=True) or []
        if values and (max(values) - min(values)) > 1e-9:
            return True
    return False


def _cut(node):
    """Drop any animCurves on the transform channels.

    Before constraining, always: a constraint over a still-connected channel
    splices a pairBlend in (the camera's trap), and a pairBlend is a rig
    nobody recorded.
    """
    for channel in CHANNELS:
        plug = "{0}.{1}".format(node, channel)
        if cmds.listConnections(plug, source=True, destination=False,
                                type="animCurve"):
            cmds.cutKey(node, attribute=channel, clear=True)


def _bake(node, start, end):
    cmds.bakeResults(node, time=(start, end), attribute=list(CHANNELS),
                     simulation=False, sampleBy=1,
                     disableImplicitControl=True, preserveOutsideKeys=False,
                     sparseAnimCurveBake=False)


def snap(node, target):
    """Put `node`'s world translate/rotate on `target`'s.

    Scale untouched -- the weapon's scale is the catalog's business, not the
    bone's, which is also why this is two channel writes and not a matrix.
    """
    cmds.xform(node, worldSpace=True, translation=cmds.xform(
        target, query=True, worldSpace=True, translation=True))
    cmds.xform(node, worldSpace=True, rotation=cmds.xform(
        target, query=True, worldSpace=True, rotation=True))


def store_grip(weapon, rotate, translate):
    """Remember the dialled grip on the weapon node itself.

    Raw under-hand channels, the same six numbers the window keeps in its
    optionVar -- but on the node, so `relink` can re-apply them after a
    merge without reaching into window policy, and so they travel with the
    scene file.
    """
    for attr, values in ((GRIP_ROTATE, rotate), (GRIP_TRANSLATE, translate)):
        if not cmds.attributeQuery(attr, node=weapon, exists=True):
            cmds.addAttr(weapon, longName=attr, dataType="double3")
        cmds.setAttr("{0}.{1}".format(weapon, attr), *values, type="double3")


def stored_grip(weapon):
    """The grip stored on `weapon`, as (rotate, translate) -- or None.

    None, not zeros: zeros are a real grip (the sword exactly on the bone),
    and a legacy sword that never had one stored must keep the snap-only
    relink instead of being yanked to the hand origin.
    """
    for attr in (GRIP_ROTATE, GRIP_TRANSLATE):
        if not cmds.attributeQuery(attr, node=weapon, exists=True):
            return None
    return (tuple(cmds.getAttr(weapon + "." + GRIP_ROTATE)[0]),
            tuple(cmds.getAttr(weapon + "." + GRIP_TRANSLATE)[0]))


def link(weapon, bone):
    """Move the bone's animation onto the weapon, then drive the bone from it.

    Returns the number of frames baked across (0: the bone had nothing that
    moves, so the weapon's channels stay clean and the grip fields stay
    live). The transfer keeps the weapon's CURRENT offset from the bone
    (mo=True) -- that offset is the dialled grip the caller placed, and the
    identity when the weapon stands on the bone, so a grip-less attach and
    the bridge's relink behave exactly as if it were mo=False. mo=False on
    the temp is how the 2026-08-25 report happened: the transfer flattened
    the grip whenever the bone brought animation, which in a scene with a
    UE clip is always.

    The final constraint stays mo=False -- that one is the design in one
    flag: the bone lives in the weapon's frame, wherever the animator (and
    the grip) takes it.
    """
    start, end = bake_range(bone)
    frames = 0
    with _autokey_off():
        if moves(bone):
            temporary = cmds.parentConstraint(bone, weapon,
                                              maintainOffset=True)[0]
            _bake(weapon, start, end)
            cmds.delete(temporary)
            frames = int(round(end - start)) + 1
        _cut(bone)
        cmds.parentConstraint(weapon, bone, maintainOffset=False)
    return frames


def unlink(bone):
    """Bake the bone back from the weapon driving it, drop the constraint.

    Returns the weapon it was riding, or None when nothing of ours drives
    the bone. Bake first, delete second -- the animation lives on the weapon
    while the link stands, and the camera already paid for the other order.
    """
    weapon = driving_weapon(bone)
    if not weapon:
        return None
    start, end = bake_range(weapon)
    with _autokey_off():
        _bake(bone, start, end)
        cmds.delete(_constraints_on(bone))
    return weapon


def relink(weapon, bone):
    """After a merge rewrote the bone: the fresh animation back onto the weapon.

    The weapon's own curves are stale by definition here -- the merge's
    contract is "the scene plays this clip" -- so they are cut, the weapon is
    snapped onto the bone (a clip with no weapon_r keys leaves the bone at
    its cleared pose, and the weapon must stand there too), and the link is
    rebuilt.

    The GRIP is not the clip's to flatten: a stored grip puts the sword back
    on its dialled pose after the snap, and the transfer keeps that offset
    (`link`, mo=True). A legacy sword with none stored keeps the snap.
    """
    with _autokey_off():
        _cut(weapon)
        snap(weapon, bone)
        grip = stored_grip(weapon)
        if grip:
            for channel, values in zip(("rotate", "translate"), grip):
                cmds.setAttr("{0}.{1}".format(weapon, channel), *values,
                             type="double3")
        return link(weapon, bone)
