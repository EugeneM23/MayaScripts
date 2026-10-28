"""Aim Mode for the camera (2026-10-28): `Camera_ctrl`'s rotation aims at two controllers, as the
weapon's (the animator: «В разделе для камеры нужно реализовать такой же aim как для оружия»).

The camera under the control stays locked; the control carries the motion, so the control is what
aims. The vectors are the camera's own: its view (-Z) and its up (+Y) through `AXIS_OFFSET`, the
target `AIM_DISTANCE` ahead and the up `UP_DISTANCE` above. The group repeats the control's
parent (Main, Root_ctrl, the chest, FKHead_M, Camera_follow, ...).

Spec: docs/superpowers/specs/2026-10-28-connections-camera-tab-design.md
"""

import maya.cmds as cmds

from maya_scenesetup import aimcore
from maya_scenesetup import camera

KIND = aimcore.AimKind("skeldarCameraAim", "skeldarCameraAimCtrl", "skeldarCameraAimOf",
                       "skeldarCameraAimVectors", "{0}_aim", "{0}_aimTarget", "{0}_aimUp",
                       "Connections: Camera Aim Mode", "Connections: Camera Default")
AIM_DISTANCE = 300.0     # cm ahead of the lens
UP_DISTANCE = 50.0       # cm above it
CONTROL_SIZE = 8.0       # the target diamond's radius, cm

NO_CAMERA = "no camera with a control - Characters > Camera Setup first"
ALREADY = "%s is in Aim Mode already - Default first"
NOT_AIMED = "%s is not in Aim Mode"
CLEARED = ("%s: its Aim Mode was broken (the controllers or the constraint deleted) - cleared, "
           "the rotation left as it is")


def camera_vectors(offset=camera.AXIS_OFFSET):
    """(aim vector, up vector, aim distance, up distance) in the control's frame: the camera's -Z
    and +Y carried through the row-vector `offset` (camera local = offset · control). Pure."""
    rows = [offset[0:3], offset[4:7], offset[8:11]]

    def through(v):
        return tuple(float(sum(v[i] * rows[i][j] for i in range(3))) + 0.0 for j in range(3))

    return through((0, 0, -1)), through((0, 1, 0)), AIM_DISTANCE, UP_DISTANCE


def home_of(control):
    """The control's own parent, or the world level."""
    parents = cmds.listRelatives(control, parent=True, fullPath=True) or []
    return parents[0] if parents else aimcore.WORLD


def _place(group, control):
    return aimcore.put(group, home_of(control))


def group_of(control):
    return aimcore.group_of(control, KIND)


def controllers(group):
    return aimcore.controllers(group, KIND)


def is_controller(node):
    return aimcore.is_controller(node, KIND)


def stored_vectors(group):
    return aimcore.stored_vectors(group, KIND)


def is_aimed(control):
    return bool(control) and aimcore.is_aimed(control, KIND)


def refusal(control):
    """'' or why the camera's control cannot go into Aim Mode."""
    if not control or not cmds.objExists(control) or not camera.is_control(control):
        return NO_CAMERA
    if is_aimed(control):
        return ALREADY % aimcore.leaf(control)
    return aimcore.rotate_refusal(control)


def enter(control, frames=None, tangents=None, track=None):
    """Aim Mode on the camera's control. The status line. `frames` (and their `tangents`): the
    controllers keyed there instead of on the control's own keys (`aimcore.aim_on`); `track`
    ({frame: world matrix}, the control's before a parent move): then keyed too on the frames
    between where the control would turn off it (`aimcore.fill_controllers`)."""
    why = refusal(control)
    if why:
        return why
    control = aimcore.long_(control)
    label = aimcore.leaf(control)
    auto = cmds.autoKeyframe(query=True, state=True)
    added = 0
    cmds.undoInfo(openChunk=True, chunkName=KIND.enter_chunk)
    try:
        cmds.autoKeyframe(state=False)
        vec = camera_vectors()
        keys, control = aimcore.aim_on(control, KIND, vec, home_of, _place,
                                       size=CONTROL_SIZE, frames=frames, tangents=tangents)
        if track and keys:
            added = aimcore.fill_controllers(control, controllers(group_of(control)), vec,
                                             home_of(control), track, set(keys))
    finally:
        cmds.autoKeyframe(state=auto)
        cmds.undoInfo(closeChunk=True)
    if not keys:
        return "%s in Aim Mode - no keys of its own: the controllers set at the current frame" % label
    return "%s in Aim Mode on %d key%s (%g..%g)%s - animate %s_aimTarget / _aimUp" % (
        label, len(keys), "" if len(keys) == 1 else "s", keys[0], keys[-1],
        " + %d between them to keep its track" % added if added else "", label)


def track(control):
    """The control's world matrix on every frame of the playback span: {frame: matrix}."""
    import maya_timewarp
    from maya_scenesetup import fkik
    window = aimcore.span()
    key = aimcore.uuid(control)
    with maya_timewarp.unwarped():
        fkik._suspend(True)
        try:
            return aimcore.walk(range(window[0], window[1] + 1),
                                lambda: aimcore.world(aimcore.long_(key)))
        finally:
            fkik._suspend(False)


def leave(control):
    """Default on the camera's control. The status line."""
    control = aimcore.long_(control)
    if not control:
        return NO_CAMERA
    label = aimcore.leaf(control)
    group = group_of(control)
    if group is None:
        return NOT_AIMED % label
    made = controllers(group)
    auto = cmds.autoKeyframe(query=True, state=True)
    cmds.undoInfo(openChunk=True, chunkName=KIND.leave_chunk)
    try:
        cmds.autoKeyframe(state=False)
        if aimcore.broken(made, aimcore.constraint(control, KIND)):
            aimcore.clear_broken(control, KIND, group)
            return CLEARED % label
        keys, added = aimcore.aim_off(control, KIND, group, made)
    finally:
        cmds.autoKeyframe(state=auto)
        cmds.undoInfo(closeChunk=True)
    line = ("%s back to Default on %d key%s" % (label, len(keys), "" if len(keys) == 1 else "s")
            if keys else "%s back to Default - no keys: its rotation set at the current frame" % label)
    return line + (" + %d between them where the aim turned faster" % added if added else "")


def controller_keys(control):
    """(frames, tangents): the key times of the aim controllers of `control` inside the playback
    span (their union), with their tangent types; ([], {}) when it is not aimed."""
    from maya_scenesetup import fkik
    import maya_timewarp
    group = group_of(control) if control else None
    made = controllers(group) if group else {}
    nodes = [n for n in (made.get("target"), made.get("up")) if n]
    if not nodes:
        return [], {}
    window = aimcore.span()
    with maya_timewarp.unwarped():
        _sample, keys, tangents = fkik.own_keys(nodes, [], window)
    frames = aimcore.keys_in(keys, window)
    return frames, dict((f, tangents[f]) for f in frames if f in tangents)


def discard(control):
    """The aim on `control` deleted without baking (the control itself is going)."""
    group = group_of(control) if control else None
    if group:
        aimcore.clear_broken(control, KIND, group)
