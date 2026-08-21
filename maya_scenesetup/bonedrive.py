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
