"""Rotation algebra for putting controllers on the skeleton's convention.

A joint's world rotation is `rotateAxis * rotate * jointOrient * parent`
(verified against the live rig), and the rotation offset between an OverRig
knot and the bone it drives is constant over time (verified: 1e-14 across
frames). Together those let a controller be re-expressed in a new rest frame
without moving anything: the product the DAG consumes is unchanged by
construction, which is the whole safety argument behind `retarget`.

Pure matrix maths. Imports OpenMaya for its types, never `maya.cmds`.
"""

import math

import maya.api.OpenMaya as om


def _rotation_only(matrix):
    """The rotation part of a matrix, translation dropped."""
    return om.MTransformationMatrix(om.MMatrix(matrix)).rotation(
        asQuaternion=True).asMatrix()


def frame_offset(bone_matrix, knot_matrix):
    """The constant C carrying the knot's frame onto the bone's: C = B * W^-1.

    Constant over time because the knot drives the bone rigidly, which is what
    makes a single static correction enough.
    """
    return _rotation_only(bone_matrix) * _rotation_only(knot_matrix).inverse()


def total_rotation(rotate_axis, rotate, joint_orient):
    """The local rotation the DAG consumes: rotateAxis * rotate * jointOrient.

    Everything here works from this product rather than the rotate channel
    alone, so a controller that already carries an orientation -- from an
    earlier alignment, or from the rig it came out of -- is handled the same
    as a fresh one, and a second pass is a no-op.
    """
    return rotate_axis * rotate * joint_orient


def orient_values(offset, reference):
    """`(rotateAxis, jointOrient)` for a controller re-expressed against
    `reference`, the rotation it holds at the build pose."""
    return offset.inverse(), offset * reference


def axis_on_bone(rotate_axis, offset):
    """`rotateAxis` for a knot turned in place onto its bone's frame.

    The knot's local rotation is `rotateAxis * rotate * jointOrient`, so
    left-multiplying `rotateAxis` by the knot-to-bone offset turns the whole
    knot by that offset and leaves the two channels that carry the animation
    -- `rotate` -- and the rest frame the channels act in -- `jointOrient *
    parent` -- exactly where they were.

    What this moves is the only thing an animator can see of a controller's
    frame: the rotate manipulator, the local rotation axes, the direction a
    dragged handle turns. Working from the measured offset makes the step
    idempotent -- once the knot stands on its bone the offset is identity.
    """
    return offset * rotate_axis


def child_held_still(child_local, offset):
    """A child's local rotation, so its world does not follow the knot's turn.

    The counterpart of `axis_on_bone` and the reason the bone stays put: the
    bone is driven from a locator hanging under the knot, so the knot cannot
    turn unless everything below it is counter-rotated. A right-multiplication,
    which is what makes it absorbable into a child joint's `jointOrient`
    without touching its animation.
    """
    return child_local * offset.inverse()


def child_position_held_still(translation, offset):
    """A child's local translation, so it does not swing with the knot's turn.

    The other half of `child_held_still`, and the half that is easy to miss: a
    child sits at an offset from its knot, so turning the knot swings it
    somewhere else entirely. Local translation is applied after the local
    rotation, so the offset takes the same inverse turn -- correcting only the
    rotation leaves every child facing the right way in the wrong place.
    """
    turned = om.MVector(translation) * offset.inverse()
    return (turned.x, turned.y, turned.z)


def angle_of(matrix):
    """The rotation angle of a rotation matrix, in degrees.

    One number for "how far apart are these two frames", which is what both
    the guard against re-turning an already-turned knot and the live checks
    are asking.
    """
    trace = matrix[0] + matrix[5] + matrix[10]
    return math.degrees(math.acos(max(-1.0, min(1.0, (trace - 1.0) / 2.0))))


def retarget(rotation, offset, reference):
    """One rotate value expressed in the new rest frame.

    C * R * R_ref^-1 * C^-1 -- a conjugation, so the value reads as the motion
    away from the build pose measured in the bone's own axes.
    """
    return offset * rotation * reference.inverse() * offset.inverse()


def euler_degrees(matrix, order=0, previous=None):
    """A matrix as degrees in `order`, nearest to `previous` if given.

    Every rotation has infinitely many euler representations. Picking blindly
    puts 360-degree jumps into a rewritten curve, which reads as the rig
    snapping between two keys.
    """
    rotation = om.MTransformationMatrix(om.MMatrix(matrix)).rotation()
    rotation.reorderIt(order)
    if previous is not None:
        rotation.setToClosestSolution(
            om.MEulerRotation([math.radians(v) for v in previous], order))
    return tuple(math.degrees(v) for v in (rotation.x, rotation.y, rotation.z))


def mirror_signs(left_axes, right_axes, tolerance=0.02):
    """Sign triple relating two frames across the YZ plane, None if unrelated.

    Each entry is `mirror(left_axis) . right_axis` rounded to +-1: the sign of
    each axis after reflecting the left frame. `(-1, -1, -1)` is the classic
    behaviour mirror the UE skeleton uses, and the convention this project
    targets.
    """
    signs = []
    for left, right in zip(left_axes, right_axes):
        mirrored = (-left[0], left[1], left[2])
        dot = sum(a * b for a, b in zip(mirrored, right))
        if abs(abs(dot) - 1.0) > tolerance:
            return None
        signs.append(1 if dot > 0 else -1)
    return tuple(signs)
