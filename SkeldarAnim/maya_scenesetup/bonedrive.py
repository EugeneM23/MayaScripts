"""A bone that follows a marked node.

The Camera Setup pattern generalised: the animator's thing (the weapon)
carries the animation and the export bone is parent-constrained to it,
`maintainOffset=True` -- the weapon plays the clip WITH the dialled grip on
top, the captured offset is the grip's inverse, and the bone keeps playing
exactly the animation it always had (the user's 2026-08-25 ruling: «главное
чтобы наша анимация сохранилась в исходном виде» -- the grip is a Maya-side
model correction and never reaches the export bone). With no grip the offset
is the identity and the bone rides the node 1:1. `attach` builds the link at
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

# The dialled grip, stored on the marked node itself -- BONE-relative since
# 2026-08-25 (zeros mean exactly on weapon_r), the same space as the fields
# and the optionVar the window keeps. It lives HERE so `relink` can put the
# sword back on its grip after a clip import rewrote the bone -- the
# optionVar is window policy, out of this module's reach, and an attribute
# travels with the scene file where an optionVar does not.
GRIP_ROTATE = "mayaWeaponGripRotate"
GRIP_TRANSLATE = "mayaWeaponGripTranslate"

# The weapon's own FRAME on its bone (2026-09-24, the Creep Sword; the
# animator: «сейчас у меча развёрнута геометрия, а оси стоят ровно ... чтобы
# оси соответствовали направлению геометрии, но при этом меч сохранил свою
# позу в руке»). A model whose rest in the hand is turned against the bone's
# axes used to carry that turn in its POINTS, so the node's axes stood on the
# bone while the blade stood 45 deg off them. Now the points are the model's
# own (guard on X, like every catalog weapon) and the turn is the catalog's,
# written on the marked node at Add: zero grip stands the node IN that frame
# -- its axes on the geometry -- and every grip is measured from it,
# world = grip x frame x bone. A node without it has the identity, exactly
# as before.
FRAME_ROTATE = "mayaWeaponFrameRotate"

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


def composed_grip(rotate, translate, frame16):
    """A bone-relative grip composed onto a frame, as (rotate, translate).

    Feed it the bone's WORLD matrix and the answer is where the sword
    stands in world; feed it a local matrix and the answer is local. Row
    vectors, so the grip multiplies from the left.
    """
    product = (om.MMatrix(matrix_of(rotate, translate))
               * om.MMatrix(frame16))
    frame = om.MTransformationMatrix(product)
    euler = frame.rotation(asQuaternion=False).reorder(om.MEulerRotation.kXYZ)
    shift = frame.translation(om.MSpace.kTransform)
    return (tuple(math.degrees(v) for v in (euler.x, euler.y, euler.z)),
            (shift.x, shift.y, shift.z))


def framed(frame_rotate, bone16):
    """`bone16` turned into a weapon's frame: frame x bone, 16 floats. Pure.

    Where zero grip stands a weapon whose frame is `frame_rotate` (XYZ
    degrees) -- the frame multiplies from the left, in the bone's own axes.
    """
    return tuple(om.MMatrix(matrix_of(frame_rotate, (0.0, 0.0, 0.0)))
                 * om.MMatrix(bone16))


def unframing(frame_rotate, rotate_order=0):
    """The frame undone, as an euler in `rotate_order` (degrees). Pure.

    What a parentConstraint's target offset holds to put a bone on the
    SOCKET of a weapon standing in that frame: W_bone = frame^-1 x W_weapon
    (a constraint's target offset is O in W = O x W_target, its euler in the
    constrained node's rotate order -- measured 2026-09-05).
    """
    inverse = om.MMatrix(matrix_of(frame_rotate, (0.0, 0.0, 0.0))).inverse()
    euler = (om.MTransformationMatrix(inverse).rotation(asQuaternion=False)
             .reorder(rotate_order))
    return tuple(math.degrees(v) for v in (euler.x, euler.y, euler.z))


def grip_between(child16, parent16):
    """The bone-relative grip that takes `parent16` to `child16`. Pure.

    The inverse of `composed_grip`: measured between the sword's and the
    bone's world matrices it answers the grip the fields should show.
    """
    product = om.MMatrix(child16) * om.MMatrix(parent16).inverse()
    return _as_grip(product)


# The model's thickness mirror (every catalog weapon lies with its thickness
# on Z) and the hands' behaviour mirror (UE's left hand: the three axes of the
# mirrored right hand negated - 0.0003 cm on Manny, 0.045 on the Creep).
MODEL_MIRROR = (1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0,
                0.0, 0.0, -1.0, 0.0, 0.0, 0.0, 0.0, 1.0)
BEHAVIOUR_MIRROR = (-1.0, 0.0, 0.0, 0.0, 0.0, -1.0, 0.0, 0.0,
                    0.0, 0.0, -1.0, 0.0, 0.0, 0.0, 0.0, 1.0)


def _as_grip(product):
    """A matrix as grip channels: (XYZ degrees, translate)."""
    frame = om.MTransformationMatrix(product)
    euler = frame.rotation(asQuaternion=False).reorder(om.MEulerRotation.kXYZ)
    shift = frame.translation(om.MSpace.kTransform)
    return (tuple(math.degrees(v) for v in (euler.x, euler.y, euler.z)),
            (shift.x, shift.y, shift.z))


def mirror_grip(rotate, translate, frame_rotate, socket_r16, socket_l16):
    """The left hand's grip standing a weapon as the world mirror of where the
    right grip (`rotate`, `translate`) stands it. Pure.

    Wanted: G_l . Fr . B_l = Mz . G_r . Fr . B_r . Mx, with B = S . H (the
    weapon bone's LOCAL matrix in its hand, the hand) and H_l = F . H_r . Mx.
    So G_l = Mz . G_r . Fr . S_r . F . S_l^-1 . Fr^-1 - the sockets decide it,
    which is why Manny (weapon_l 6.9 cm off the mirror of weapon_r, the blade
    backwards at zero grip) and the Creep (a geometric pair, zero is right)
    come out differently from the same numbers (measured 2026-09-29). Row
    vectors, as everywhere here.
    """
    frame = om.MMatrix(matrix_of(frame_rotate, (0.0, 0.0, 0.0)))
    product = (om.MMatrix(MODEL_MIRROR)
               * om.MMatrix(matrix_of(rotate, translate))
               * frame * om.MMatrix(socket_r16) * om.MMatrix(BEHAVIOUR_MIRROR)
               * om.MMatrix(socket_l16).inverse() * frame.inverse())
    return _as_grip(product)


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

    Bone-relative, the same six numbers the window keeps in its optionVar --
    but on the node, so `relink` can re-apply them after a merge without
    reaching into window policy, and so they travel with the scene file.
    """
    for attr, values in ((GRIP_ROTATE, rotate), (GRIP_TRANSLATE, translate)):
        if not cmds.attributeQuery(attr, node=weapon, exists=True):
            cmds.addAttr(weapon, longName=attr, dataType="double3")
        cmds.setAttr("{0}.{1}".format(weapon, attr), *values, type="double3")


def store_frame(weapon, rotate):
    """The weapon's own frame on its bone, on the node (see FRAME_ROTATE).

    The identity writes nothing on a node that has none: a weapon on the
    bone's axes keeps looking exactly as it always did.
    """
    exists = cmds.attributeQuery(FRAME_ROTATE, node=weapon, exists=True)
    if not exists and not any(rotate):
        return
    if not exists:
        cmds.addAttr(weapon, longName=FRAME_ROTATE, dataType="double3")
    cmds.setAttr("{0}.{1}".format(weapon, FRAME_ROTATE), *rotate,
                 type="double3")


def frame_of(weapon):
    """The frame stored on `weapon` (XYZ degrees), the identity when none."""
    if not cmds.attributeQuery(FRAME_ROTATE, node=weapon, exists=True):
        return (0.0, 0.0, 0.0)
    return tuple(cmds.getAttr(weapon + "." + FRAME_ROTATE)[0])


def _seat_of(weapon, bone):
    """Where zero grip stands `weapon`: its frame on the bone's world."""
    return framed(frame_of(weapon),
                  cmds.xform(bone, query=True, matrix=True, worldSpace=True))


def place_at_grip(weapon, bone, rotate, translate):
    """Stand `weapon` at the grip: world = grip x its frame x the BONE's world.

    Zeros put the sword exactly on `weapon_r` -- the game's own grip -- in
    the model's own frame (FRAME_ROTATE; the identity for most). Two
    channel-shaped writes like `snap`, so scale stays the catalog's and the
    weapon's DAG parent (the hand) never enters the math.
    """
    world_rotate, world_translate = composed_grip(
        rotate, translate, _seat_of(weapon, bone))
    cmds.xform(weapon, worldSpace=True, translation=world_translate)
    cmds.xform(weapon, worldSpace=True, rotation=world_rotate)


def apply_grip(weapon, bone, rotate, translate):
    """Place `weapon` at the grip and remember it on a marked node.

    The one grip-application everything shares: attach on Add, relink after
    a merge (through the stored copy), regrip on a live dial. Unmarked
    nodes -- sandboxes, plain locators -- are placed but store nothing.
    autoKey is held off around the writes (trap 14); nesting inside a
    caller's guard restores the caller's state.
    """
    with _autokey_off():
        place_at_grip(weapon, bone, rotate, translate)
        if cmds.attributeQuery(MARKER, node=weapon, exists=True):
            store_grip(weapon, rotate, translate)


def measured_grip(weapon, bone):
    """The grip the scene currently holds, from world matrices.

    What the fields show for an attached, unanimated weapon: a sword the
    animator nudged by hand in the viewport reads back as its real
    bone-relative offset.
    """
    return grip_between(
        cmds.xform(weapon, query=True, matrix=True, worldSpace=True),
        _seat_of(weapon, bone))


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
    the bridge's relink transfer verbatim. mo=False on the temp is how the
    2026-08-25 report happened: the transfer flattened the grip whenever
    the bone brought animation, which in a scene with a UE clip is always.

    The final constraint is mo=True as well -- the user's ruling the same
    day: «главное чтобы наша анимация сохранилась в исходном виде». The
    weapon plays grip-then-clip, the captured offset is the grip's inverse,
    so the BONE keeps playing exactly the clip it always had -- the grip is
    a Maya-side model correction and never reaches the export bone. With no
    grip the offset is the identity and the bone rides the weapon 1:1. The
    camera drives its bone through the same flag.

    After a transfer the offset is captured ON A SAMPLED FRAME (the range
    start, time put back): the weapon is a baked curve now, and a capture
    at a fractional currentTime would compare an interpolated weapon
    against the bone's exact cut value, riding that error on every frame.

    And the bone is SETTLED on that frame by hand (2026-09-07): `cutKey`
    leaves a channel holding whatever value was last EVALUATED, and
    `currentTime(start)` evaluates nothing by itself in a session with no
    viewport pulling the joint -- measured in mayapy: the bone kept its
    frame-24 values through a cut "at frame 0", the capture compared them
    against the sword's exact frame-0 key, and the bone rode the sword
    0.319 cm off for the whole take. The live proofs passed because the
    viewport happened to evaluate the joint (trap 14's family). So the
    frame-`start` values are read off the curves before the cut and written
    back after it, and the capture no longer depends on what got drawn.
    """
    start, end = bake_range(bone)
    frames = 0
    parked = None
    with _autokey_off():
        if moves(bone):
            temporary = cmds.parentConstraint(bone, weapon,
                                              maintainOffset=True)[0]
            _bake(weapon, start, end)
            cmds.delete(temporary)
            frames = int(round(end - start)) + 1
            parked = cmds.currentTime(query=True)
            cmds.currentTime(start)
        try:
            settled = _keyed_values_at(bone, start)
            _cut(bone)
            for plug, value in settled:
                cmds.setAttr(plug, value)
            cmds.parentConstraint(weapon, bone, maintainOffset=True)
        finally:
            if parked is not None:
                cmds.currentTime(parked)
    return frames


def _keyed_values_at(node, time):
    """[(plug, value)] of the node's keyed transform channels at `time`,
    read off the curves themselves -- exact, whatever the DG last evaluated."""
    out = []
    for channel in CHANNELS:
        plug = "{0}.{1}".format(node, channel)
        if cmds.listConnections(plug, source=True, destination=False,
                                type="animCurve"):
            out.append((plug, cmds.getAttr(plug, time=time)))
    return out


def regrip(weapon, bone, rotate, translate):
    """Move the weapon to a new grip without moving the bone.

    The bone plays its own animation through the constraint's captured
    offset, so placing the weapon under a live constraint would drag the
    bone along by the OLD offset. Our constraint is dropped first (the bone
    freezes exactly where the invariant held it), the weapon placed at the
    new grip relative to the bone (`apply_grip`, which also updates the
    stored copy on a marked node), and the constraint remade capturing the
    new offset -- the weapon moves, the bone does not.

    A bone with no constraint, or somebody else's, gets a plain placement
    and its constraint is left standing: a legacy sword still takes
    offsets, and a foreign rig is not ours to rehook.
    """
    ours = driving_weapon(bone)
    rehook = bool(ours) and (cmds.ls(ours, long=True)
                             == cmds.ls(weapon, long=True))
    with _autokey_off():
        if rehook:
            cmds.delete(_constraints_on(bone))
        apply_grip(weapon, bone, rotate, translate)
        if rehook:
            cmds.parentConstraint(weapon, bone, maintainOffset=True)


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
    on its dialled pose relative to the bone, and the transfer keeps that
    offset (`link`, mo=True). A legacy sword with none stored goes to zero
    grip -- onto the bone in its own frame, which for a frameless weapon is
    the old snap exactly.
    """
    with _autokey_off():
        _cut(weapon)
        grip = stored_grip(weapon) or ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
        place_at_grip(weapon, bone, grip[0], grip[1])
        return link(weapon, bone)
