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


def orient_values(offset, reference):
    """`(rotateAxis, jointOrient)` for a controller re-expressed against
    `reference`, the rotation it holds at the build pose."""
    return offset.inverse(), offset * reference


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
