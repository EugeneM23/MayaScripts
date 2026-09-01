"""Re-expressing FK controllers in their bones' axes.

Two steps, run at the tail of every build. `align_controllers` conjugates
the rotate CHANNELS into the bone's frame, so equal values on both sides
give a mirrored pose. `orient_controllers` then turns each knot's OWN frame
onto its bone -- the frame is everything an animator can see of a
controller -- with every DAG child counter-corrected in rotation AND turned
translation (trap 29: angles are blind to position, and the bone is driven
from a child locator). Both steps are idempotent because they work from the
measured offset, not the channels alone. See CLAUDE.md and the 2026-08-15/16
axis specs for the full argument.
"""

import contextlib
import math

import maya.cmds as cmds
import maya.api.OpenMaya as om

from maya_overrig import axes
from maya_overrig import fkchains


def merge_key_times(per_channel):
    """Sorted union of key times across channels.

    All three rotate channels are rewritten together -- a value is only
    meaningful as part of a whole rotation -- so they need one shared list of
    times. `cmds.keyframe` returns None for an unkeyed channel.
    """
    times = set()
    for channel in per_channel:
        times.update(channel or ())
    return sorted(times)


def is_constant(values, tolerance=1e-6):
    """True when a baked curve never actually changes.

    A driver locator's rotation is the fixed offset between its knot and the
    bone it drives, so OverRig's bake writes the same value into every one of
    its keys (measured: spread 0.000000 over 62). Spotting that turns a
    per-key rewrite into one call per channel.
    """
    if not values:
        return True
    return (max(values) - min(values)) <= tolerance


_ROTATE_CHANNELS = ("rotateX", "rotateY", "rotateZ")
_TRANSLATE_CHANNELS = ("translateX", "translateY", "translateZ")


def _world_rotation(node):
    """A node's world rotation, translation dropped."""
    return axes._rotation_only(
        om.MMatrix(cmds.xform(node, query=True, worldSpace=True, matrix=True)))


def _euler_matrix(values, order=0):
    return om.MEulerRotation([math.radians(v) for v in values],
                             order).asMatrix()


def _local_total(node, rotate_values=None):
    """The local rotation the DAG consumes: rotateAxis * rotate * jointOrient.

    Working from the whole product rather than the rotate channel alone means
    a controller that already carries an orientation is handled correctly, and
    running the alignment twice changes nothing.
    """
    order = cmds.getAttr(node + ".rotateOrder")
    if rotate_values is None:
        rotate_values = cmds.getAttr(node + ".rotate")[0]
    return axes.total_rotation(
        _euler_matrix(cmds.getAttr(node + ".rotateAxis")[0]),
        _euler_matrix(rotate_values, order),
        _euler_matrix(cmds.getAttr(node + ".jointOrient")[0]))


@contextlib.contextmanager
def _unlocked(node, attr):
    """Unlock a rotation triple for the duration of a write, then re-lock it.

    OverRig locks `jointOrient` on its knots. Unlocking before anything is
    written means a refused write cannot leave a controller carrying half a
    change -- and half a change moves the bone.
    """
    locked = [plug for plug in
              ("{0}.{1}{2}".format(node, attr, axis) for axis in "XYZ")
              if cmds.getAttr(plug, lock=True)]
    for plug in locked:
        cmds.setAttr(plug, lock=False)
    try:
        yield
    finally:
        for plug in locked:
            cmds.setAttr(plug, lock=True)


def _plugs(node, attr):
    return ["{0}.{1}{2}".format(node, attr, axis) for axis in "XYZ"]


def _settable(node, attr):
    """True when a rotation triple can be written outright."""
    return not any(cmds.getAttr(plug, lock=True)
                   or cmds.listConnections(plug, source=True,
                                           destination=False)
                   for plug in _plugs(node, attr))


def _curves_on(node, attr):
    """{channel: animCurve} for a triple, or None when something else drives it.

    An empty mapping means the triple is plain static values.
    """
    curves = {}
    for axis in "XYZ":
        plug = "{0}.{1}{2}".format(node, attr, axis)
        if cmds.getAttr(plug, lock=True):
            return None
        sources = cmds.listConnections(plug, source=True,
                                       destination=False) or []
        animated = [s for s in sources
                    if cmds.objectType(s).startswith("animCurve")]
        if len(animated) != len(sources):
            return None  # driven by a constraint, an expression, a pairBlend
        if animated:
            curves[attr + axis] = animated[0]
    if curves and len(curves) != 3:
        return None  # half-keyed; no single value can stand in for a curve
    return curves


def _hold_still_by_orient(child, offset):
    """Writer that absorbs the correction into a child knot's jointOrient."""
    if any(cmds.listConnections(plug, source=True, destination=False)
           for plug in _plugs(child, "jointOrient")):
        return None
    current = cmds.getAttr(child + ".jointOrient")[0]
    held = axes.euler_degrees(
        axes.child_held_still(_euler_matrix(current), offset),
        previous=current)

    def write():
        with _unlocked(child, "jointOrient"):
            cmds.setAttr(child + ".jointOrient", *held)
    return write


def _rewrite_triple(node, channels, convert):
    """Writer putting `convert(values, previous)` on a triple, or None.

    Covers the three ways OverRig leaves a channel. Plain static values are
    set outright. A baked curve that never actually changes -- every driver
    locator, whose rotation is the fixed knot-to-bone offset -- is rewritten
    with one call per channel. A curve that really varies is walked key by
    key, nearest-solution, so nothing flips by 360 between two keys.
    """
    attr = channels[0][:-1]
    curves = _curves_on(node, attr)
    if curves is None:
        return None

    if not curves:
        held = convert(cmds.getAttr(node + "." + attr)[0], None)
        return lambda: cmds.setAttr(node + "." + attr, *held)

    per_channel = {name: cmds.keyframe(curve, query=True, valueChange=True)
                   or [] for name, curve in curves.items()}
    if all(is_constant(values) for values in per_channel.values()):
        held = convert([per_channel[name][0] for name in channels], None)

        def write_flat():
            for name, value in zip(channels, held):
                cmds.keyframe(node, attribute=name, valueChange=value,
                              absolute=True)
        return write_flat

    times = merge_key_times([
        cmds.keyframe(curve, query=True, timeChange=True)
        for curve in curves.values()])
    poses = []
    for time in times:
        values = [cmds.keyframe(node, attribute=name, query=True,
                                time=(time, time), valueChange=True)
                  for name in channels]
        if any(not v for v in values):
            return None  # a channel is missing this key
        poses.append((time, [v[0] for v in values]))

    retimed = []
    previous = None
    for time, values in poses:
        previous = convert(values, previous)
        retimed.append((time, previous))

    def write_keys():
        for time, values in retimed:
            for name, value in zip(channels, values):
                cmds.keyframe(node, attribute=name, time=(time, time),
                              valueChange=value, absolute=True)
    return write_keys


def _hold_still(child, offset):
    """Writer keeping `child` where it is while its knot turns, or None.

    Two corrections, and both are needed: the rotation keeps the child facing
    the same way, the translation keeps it in the same place. A child sits at
    an offset from its knot, so a turn swings it somewhere else entirely --
    correcting only the rotation moved bones by 21 cm in a live run.

    None means this child cannot be held still, and then the knot must not
    turn at all.
    """
    if cmds.attributeQuery("jointOrient", node=child, exists=True):
        turn = _hold_still_by_orient(child, offset)
    else:
        # The driver locator has no `jointOrient` to hide a correction in, so
        # the correction goes into its rotate -- which OverRig has baked.
        order = cmds.getAttr(child + ".rotateOrder")
        turn = _rewrite_triple(
            child, _ROTATE_CHANNELS,
            lambda values, previous: axes.euler_degrees(
                axes.child_held_still(_euler_matrix(values, order), offset),
                order, values if previous is None else previous))
    if turn is None:
        return None

    swing = _rewrite_triple(
        child, _TRANSLATE_CHANNELS,
        lambda values, _previous: axes.child_position_held_still(values,
                                                                 offset))
    if swing is None:
        return None

    def write():
        turn()
        swing()
    return write


# Degrees. A knot closer than this to its bone's frame is already there, which
# is what makes the step idempotent and what skips `root` and `pelvis`.
_ON_BONE = 1e-4


def _turn_onto_bone(ctrl, offset):
    """Turn one knot in place onto its bone's frame. True when changed.

    The knot's own frame is the only part of a controller an animator can
    read -- the rotate manipulator, the local rotation axes, the way a dragged
    handle turns -- and OverRig leaves it rolled about 90 degrees about the
    bone. `rotateAxis` carries the turn; every DAG child is counter-rotated so
    that the driver locator, and therefore the bone, does not move with it.

    Everything that can refuse is decided before anything is written: a knot
    turned with one child left behind drags the bone with it.
    """
    if axes.angle_of(offset) <= _ON_BONE:
        return False
    if not _settable(ctrl, "rotateAxis"):
        return False

    writers = []
    for child in cmds.listRelatives(ctrl, children=True, fullPath=True,
                                    type="transform") or []:
        # A constraint node parks under the object it constrains and never
        # reads its own transform. OverRig leaves a dead aimConstraint under
        # every knot it builds.
        if cmds.objectType(child).endswith("Constraint"):
            continue
        writer = _hold_still(child, offset)
        if writer is None:
            return False
        writers.append(writer)

    for writer in writers:
        writer()
    cmds.setAttr(ctrl + ".rotateAxis", *axes.euler_degrees(
        axes.axis_on_bone(_euler_matrix(cmds.getAttr(ctrl + ".rotateAxis")[0]),
                          offset)))
    return True


def _control_path(joint, controls):
    """One bone's controller path, or None.

    `controls` is the per-character index {bone: controller UUID} the
    build assembles -- with a second character in the scene the knot is
    called `upperarm_l_FK_ctrl1` and the name lookup below resolves the
    WRONG character's controller, which would rewrite its rotate axes.
    Left as None the name lookup stands, which is what a single-character
    scene (and every verify script calling these two directly) needs.
    """
    if controls is not None:
        uuid = controls.get(joint)
        if not uuid:
            return None
        found = cmds.ls(uuid, long=True) or []
        return found[0] if found else None
    name = fkchains.controller_name(joint)
    return name if cmds.objExists(name) else None


def orient_controllers(scene_map, only=None, controls=None):
    """Turn every built FK controller onto its bone's frame. Bones do not move.

    The half of "on the bone's axes" that `align_controllers` cannot buy: it
    puts the rotate CHANNELS in the bone's axes but has to leave the knot's own
    frame where OverRig put it, about 90 degrees rolled about the bone (about
    180 on the right hand). This turns the knot itself, so what the animator
    grabs matches what the finger does.

    Every offset is measured before anything is written -- a knot's world is
    unchanged by its parent's turn, so the readings stay good, and no
    measurement can be taken from a half-written scene.
    """
    plan = []
    for chain_name, chain in fkchains.CHAINS:
        if only is not None and chain_name not in only:
            continue
        for joint in chain:
            ctrl = _control_path(joint, controls)
            bone = scene_map.get(joint)
            if not (ctrl and bone and cmds.objExists(bone)):
                continue
            plan.append((ctrl, axes.frame_offset(_world_rotation(bone),
                                                 _world_rotation(ctrl))))

    turned = 0
    for ctrl, offset in plan:
        if _turn_onto_bone(ctrl, offset):
            turned += 1
    return turned


def _align_one(ctrl, bone):
    """Re-express one controller in its bone's axes. True when changed.

    `rotateAxis` takes the inverse of the knot-to-bone offset, `jointOrient`
    takes what the controller holds at the build pose, and every rotate key is
    conjugated into the new frame. The product the DAG consumes --
    rotateAxis * rotate * jointOrient -- is unchanged by construction, so
    nothing in the scene moves.
    """
    # A plain transform has no jointOrient, and rotateAxis alone cannot carry
    # the change: the leftover would have to vary with time. The `root`
    # controller is the only one -- built by apply_parentConstrAnim rather
    # than ForwHierarhy -- and being a lone centre control it has no mirror
    # partner to be symmetric with anyway.
    if not cmds.attributeQuery("jointOrient", node=ctrl, exists=True):
        return False

    offset = axes.frame_offset(_world_rotation(bone), _world_rotation(ctrl))
    reference = _local_total(ctrl)
    rotate_axis, joint_orient = axes.orient_values(offset, reference)
    order = cmds.getAttr(ctrl + ".rotateOrder")

    times = merge_key_times([
        cmds.keyframe(ctrl, attribute=attr, query=True, timeChange=True)
        for attr in _ROTATE_CHANNELS])

    # Read every key before writing any: the curves are the input.
    poses = []
    for time in times:
        values = [cmds.keyframe(ctrl, attribute=attr, query=True,
                                time=(time, time), valueChange=True)
                  for attr in _ROTATE_CHANNELS]
        if any(not v for v in values):
            return False  # a channel is missing this key; leave it alone
        poses.append((time, _local_total(ctrl, [v[0] for v in values])))

    retargeted = []
    previous = None
    for time, total in poses:
        previous = axes.euler_degrees(
            axes.retarget(total, offset, reference), order, previous)
        retargeted.append((time, previous))

    # OverRig locks jointOrient on its knots. Unlock before touching anything,
    # so a refused write cannot leave a controller carrying half the change --
    # a rotateAxis without its jointOrient moves the bone it drives.
    with _unlocked(ctrl, "jointOrient"):
        cmds.setAttr(ctrl + ".rotateAxis", *axes.euler_degrees(rotate_axis))
        cmds.setAttr(ctrl + ".jointOrient", *axes.euler_degrees(joint_orient))
        for time, values in retargeted:
            for attr, value in zip(_ROTATE_CHANNELS, values):
                cmds.keyframe(ctrl, attribute=attr, time=(time, time),
                              valueChange=value, absolute=True)
        if not times:
            cmds.setAttr(ctrl + ".rotate", *axes.euler_degrees(
                axes.retarget(reference, offset, reference), order))
    return True


def align_controllers(scene_map, only=None, controls=None):
    """Re-express every built FK controller in its bone's axes. Nothing moves.

    Puts the controllers on the skeleton's own mirror convention, so a
    mirrored pose reads as equal channel values on both sides -- which is what
    Animbot's mirror and plain copy-paste between sides both need.

    Order does not matter: every input is read from world transforms this
    operation provably leaves alone.
    """
    aligned = 0
    for chain_name, chain in fkchains.CHAINS:
        if only is not None and chain_name not in only:
            continue
        for joint in chain:
            ctrl = _control_path(joint, controls)
            bone = scene_map.get(joint)
            if not (ctrl and bone and cmds.objExists(bone)):
                continue
            if _align_one(ctrl, bone):
                aligned += 1
    return aligned
