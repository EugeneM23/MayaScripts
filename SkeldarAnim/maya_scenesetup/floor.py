"""A weapon on the floor: the character's, its hand's bone following it.

2026-09-29, the animator's inventory («оружие ... как вставлялось в руку или
выпадало на пол»), and asked: a weapon dropped on the floor is the
CHARACTER's - it lies there and its hand's weapon bone follows it, the
Connections "World" state, so a pickup is animated from there and the export
carries it through the bone. The bone's own track is PARKED on the weapon
(`bonedrive.park`) and handed back if the weapon is taken off while it still
lies there (`attach.detach`).

The weapon lies flat - its thickness (model Z) straight up, its blade (model
Y) along a heading the caller gives (the camera's right: it reads along the
view it was dropped in), its box's middle over the point, its lowest point on
the floor. Every catalog weapon is authored that way round (blade +Y, guard
X, thickness Z).
"""

import math

import maya.api.OpenMaya as om
import maya.cmds as cmds

from maya_scenesetup import attach
from maya_scenesetup import bonedrive


# ------------------------------------------------------------------- pure

def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def lying_pose(bbox, scale, point, heading):
    """(rotate XYZ degrees, translate) laying a model flat. Pure.

    `bbox` is the unscaled model's (xmin, ymin, zmin, xmax, ymax, zmax) in
    its own axes. The thickness stands straight up, the blade runs along
    `heading` projected on the floor (world X when the heading is vertical),
    the box's middle is over `point` and its lowest point at `point`'s
    height. Always a rotation: X = Y x Z.
    """
    hx, hz = float(heading[0]), float(heading[2])
    length = math.hypot(hx, hz)
    if length < 1e-9:
        hx, hz, length = 1.0, 0.0, 1.0
    y_axis = (hx / length, 0.0, hz / length)
    z_axis = (0.0, 1.0, 0.0)
    x_axis = _cross(y_axis, z_axis)
    middle = [(bbox[i] + bbox[i + 3]) * 0.5 * scale for i in range(3)]
    tx = point[0] - (middle[0] * x_axis[0] + middle[1] * y_axis[0])
    tz = point[2] - (middle[0] * x_axis[2] + middle[1] * y_axis[2])
    ty = point[1] - bbox[2] * scale
    rotation = om.MMatrix([x_axis[0], x_axis[1], x_axis[2], 0.0,
                           y_axis[0], y_axis[1], y_axis[2], 0.0,
                           z_axis[0], z_axis[1], z_axis[2], 0.0,
                           0.0, 0.0, 0.0, 1.0])
    euler = om.MTransformationMatrix(rotation).rotation(asQuaternion=False)
    euler = euler.reorder(om.MEulerRotation.kXYZ)
    return (tuple(math.degrees(v) for v in (euler.x, euler.y, euler.z)),
            (tx, ty, tz))


# ------------------------------------------------------------------ scene

def model_box(weapon, scale):
    """The unscaled model's box: right after `attach.import_weapon` the
    weapon stands seated at world level (rotate and translate zero, the
    catalog scale), so its world box divided by the scale is the model's."""
    box = cmds.exactWorldBoundingBox(weapon)
    return tuple(value / scale for value in box)


def drop(entry, bone, point, heading, rgb=None):
    """`entry`'s weapon lying at `point`, `bone` following it, the bone's own
    track parked on the weapon. Returns (weapon, note).

    One undo chunk, autoKey off (trap 14). The bone must be free: the caller
    takes off whatever it followed first (`attach.detach`) - refusing here
    rather than stacking a second constraint on it.
    """
    if bonedrive.driving_weapon(bone):
        raise RuntimeError("%s already follows a weapon" % bone.split("|")[-1])
    cmds.undoInfo(openChunk=True, chunkName="Weapon onto the floor")
    autokey = cmds.autoKeyframe(query=True, state=True)
    cmds.autoKeyframe(state=False)
    try:
        weapon, note = attach.import_weapon(entry, None, rgb)
        scale = float(getattr(entry, "scale", 1.0) or 1.0)
        rotate, translate = lying_pose(model_box(weapon, scale), scale, point,
                                       heading)
        cmds.xform(weapon, worldSpace=True, translation=translate)
        cmds.xform(weapon, worldSpace=True, rotation=rotate)
        bonedrive.park(weapon, bone)
        bonedrive.drive_socket(weapon, bone)
        return weapon, note
    finally:
        cmds.autoKeyframe(state=autokey)
        cmds.undoInfo(closeChunk=True)
