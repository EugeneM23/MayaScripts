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
