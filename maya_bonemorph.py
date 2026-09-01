"""Morph a group of joints onto another object's mesh.

Test-mode tool, deliberately minimal (the project's spec/TDD pipeline is
skipped on purpose): select the joints - or one root joint, then the
joints under it are taken - together with ONE target mesh, press Apply
Morph. Two mappings decide where each joint goes, both against the
target's current pose:

Project down (rays), the default: a ray is cast from the joint's rest
position straight down; the joint flies to the hit point on the target,
and a ray that misses drops the joint to Y 0 (the test floor). X and Z
never change, so the joints keep their own spread and land evenly -
the drape. Project to nearest (rays): the ray is aimed at the target
instead - at the nearest point of its surface, and the first thing such
a ray hits IS that nearest point (anything hit earlier would be closer),
so it is computed directly and can never miss: a joint beside the target
lands on its side instead of falling to the floor. Stretch to surface,
the original mapping: the rest position is normalised inside the group's
bounding box, carried over into the target's bounding box, then snapped
to the closest point on the target's surface - the cloud takes the
target's overall shape.

Timing: Constant speed, the default, sends every joint off at the same
speed - Speed units per frame, linear - so a joint ten metres out lands
long after one a centimetre out, each exactly when its own distance is
covered. Fixed frames is the original schedule: every joint flies for
Morph frames (smoothstep).

The melt wave staggers the DEPARTURES the way maya_bonemelt does: the
outermost joints - by horizontal distance from the group's bounding-box
centre - leave first and the start front converges on the middle over
Wave travel frames; Layer delay makes the bottom of the group leave
before the top. Both at 0 start every joint together (the original
behaviour). Keys land on every frame from the playback range start to
each joint's own landing, translate XYZ, holding the rest pose until
the joint's turn comes.

The mesh skinned to the selected bones never counts as the target: a
marquee that grabs the bones together with their own skin still
resolves the one remaining mesh, and rays only ever see that target.

The rest values are stored under the same geoWaveRest<axis> markers
maya_bonewave and maya_bonemelt use - deliberately shared, so any of the
three tools rebuilds from the one true rest and any Remove restores it.
A joint animated by something without the marker is skipped and named.
The joints' parent is assumed static while the morph plays (true for the
geobones root).

Run:
    import sys; sys.path.append(r"C:/!!!Work/MayaScripts")
    import maya_bonemorph; maya_bonemorph.show()
"""

import math

import maya.api.OpenMaya as om
import maya.cmds as cmds

WINDOW = "boneMorphWindow"
REST_ATTR = "geoWaveRest"
AXES = ("X", "Y", "Z")
MISS_FLOOR_Y = 0.0
MODES = {"Project down (rays)": "project",
         "Project to nearest (rays)": "nearest",
         "Stretch to surface": "stretch"}
TIMINGS = {"Constant speed": "speed",
           "Fixed frames": "fixed"}

_frames = None
_mode = None
_timing = None
_speed = None
_wave = None
_layer = None
_status = None


# ---------------------------------------------------------------- pure logic

def morph_progress(frame, start_frame, duration):
    """0 at the start of the flight, 1 on landing, smoothstep between."""
    if duration <= 0:
        return 1.0 if frame >= start_frame else 0.0
    p = (frame - start_frame) / float(duration)
    p = max(0.0, min(1.0, p))
    return p * p * (3.0 - 2.0 * p)


def normalized_in_box(position, lo, hi):
    """Position as 0..1 fractions of a bounding box; a degenerate axis
    reads as the middle."""
    out = []
    for i in range(3):
        size = hi[i] - lo[i]
        out.append((position[i] - lo[i]) / size if size > 1e-9 else 0.5)
    return out


def box_point(fractions, lo, hi):
    return [lo[i] + fractions[i] * (hi[i] - lo[i]) for i in range(3)]


def horizontal_distance(position, center):
    """Distance from the group's central vertical axis, in the floor
    plane (XZ)."""
    dx = position[0] - center[0]
    dz = position[2] - center[2]
    return math.sqrt(dx * dx + dz * dz)


def height_fraction(y, y_lo, y_hi):
    """0 at the bottom of the group, 1 at the top; a flat group reads 0
    so no layer lags another."""
    size = y_hi - y_lo
    return (y - y_lo) / size if size > 1e-9 else 0.0


def start_frame_for(dist, dist_max, start, travel):
    """When a joint departs: the farthest joints at the range start, the
    centre after the whole front has travelled in."""
    if dist_max <= 0.0:
        return float(start)
    return start + (dist_max - dist) / dist_max * travel


# ---------------------------------------------------------------- scene side

def target_joints_from(selection_joints):
    """A single joint with joint children means the group under it (the
    geobones root gesture); anything else is taken literally."""
    if len(selection_joints) == 1:
        kids = cmds.listRelatives(selection_joints[0], allDescendents=True,
                                  type="joint", fullPath=True) or []
        if kids:
            return kids
    return selection_joints


def selected_meshes():
    """Mesh shapes of the current selection, transforms or shapes alike."""
    shapes = []
    for node in cmds.ls(selection=True, long=True, objectsOnly=True) or []:
        if cmds.objectType(node, isAType="mesh"):
            found = [node]
        else:
            found = cmds.listRelatives(node, shapes=True, fullPath=True,
                                       type="mesh") or []
        for shape in found:
            if cmds.getAttr(shape + ".intermediateObject"):
                continue
            if shape not in shapes:
                shapes.append(shape)
    return shapes


def _rest_attr(joint, axis):
    return joint + "." + REST_ATTR + axis


def existing_skin(shape):
    """The skinCluster already deforming the shape, or None."""
    history = cmds.listHistory(shape, pruneDagObjects=True) or []
    clusters = cmds.ls(history, type="skinCluster")
    return clusters[0] if clusters else None


def skinned_to(shape, joints):
    """True when the shape's skin is driven by any of the given joints -
    that mesh is the bones' own skin, never a morph target."""
    skin = existing_skin(shape)
    if not skin:
        return False
    influences = cmds.ls(cmds.skinCluster(skin, query=True,
                                          influence=True) or [],
                         long=True)
    joint_set = set(joints)
    return any(i in joint_set for i in influences)


def _mesh_fn(shape):
    sel = om.MSelectionList()
    sel.add(shape)
    return om.MFnMesh(sel.getDagPath(0))


def _ray_down_hit(fn, point):
    """Where a ray cast straight down from the point first meets the
    mesh, or None when it never does."""
    res = fn.closestIntersection(
        om.MFloatPoint(point[0], point[1], point[2]),
        om.MFloatVector(0.0, -1.0, 0.0),
        om.MSpace.kWorld, 1e6, False)
    if not res or res[2] == -1:
        return None
    hit = res[0]
    return (hit.x, hit.y, hit.z)


def _world_to_local(point, joint):
    """A world position expressed in the joint's parent space (row-vector
    convention: p_local = p_world * parentInverse)."""
    parent = cmds.listRelatives(joint, parent=True, fullPath=True)
    if not parent:
        return list(point)
    m = cmds.getAttr(parent[0] + ".worldInverseMatrix[0]")
    return [point[0] * m[0] + point[1] * m[4] + point[2] * m[8] + m[12],
            point[0] * m[1] + point[1] * m[5] + point[2] * m[9] + m[13],
            point[0] * m[2] + point[1] * m[6] + point[2] * m[10] + m[14]]


def apply_morph(joints, target_shape, duration, start, mode="stretch",
                speed=None, wave_travel=0.0, layer_delay=0.0):
    """Keys on translate XYZ carrying every joint from its rest position
    onto the target surface; returns (keyed joints, skipped names,
    missed ray count - always 0 outside project mode, longest schedule
    in frames). With speed set, every joint flies linearly at that many
    units per frame and lands when its own distance is covered; without
    it, every joint flies for `duration` frames (smoothstep).
    wave_travel staggers the departures melt-style - edges first, the
    front converging on the middle - and layer_delay holds the top of
    the group back behind the bottom; both 0 start everyone together."""
    todo = []
    skipped = []
    for joint in joints:
        foreign = False
        for axis in AXES:
            plug = joint + ".translate" + axis
            has_curve = bool(cmds.listConnections(plug, source=True,
                                                  destination=False,
                                                  type="animCurve"))
            if has_curve and not cmds.objExists(_rest_attr(joint, axis)):
                foreign = True
        if foreign:
            skipped.append(joint.split("|")[-1])
        else:
            todo.append(joint)

    # First pass: everything back to rest, so the source box is measured
    # on the unmorphed pose.
    for joint in todo:
        for axis in AXES:
            plug = joint + ".translate" + axis
            rest_attr = _rest_attr(joint, axis)
            if cmds.objExists(rest_attr):
                rest = cmds.getAttr(rest_attr)
            else:
                rest = cmds.getAttr(plug)
                cmds.addAttr(joint, longName=REST_ATTR + axis,
                             attributeType="double")
                cmds.setAttr(rest_attr, rest)
            cmds.cutKey(joint, attribute="translate" + axis, clear=True)
            cmds.setAttr(plug, rest)

    positions = {}
    for joint in todo:
        positions[joint] = cmds.xform(joint, query=True, worldSpace=True,
                                      translation=True)
    if not todo:
        return todo, skipped, 0, 0
    src_lo = [min(p[i] for p in positions.values()) for i in range(3)]
    src_hi = [max(p[i] for p in positions.values()) for i in range(3)]
    box = cmds.exactWorldBoundingBox(target_shape)
    tgt_lo, tgt_hi = box[:3], box[3:]
    center = [(src_lo[i] + src_hi[i]) * 0.5 for i in range(3)]
    dists = {j: horizontal_distance(positions[j], center) for j in todo}
    dist_max = max(dists.values())
    y_lo = min(p[1] for p in positions.values())
    y_hi = max(p[1] for p in positions.values())

    fn = _mesh_fn(target_shape)
    missed = 0
    longest = 0
    for joint in todo:
        if mode == "project":
            target_world = _ray_down_hit(fn, positions[joint])
            if target_world is None:
                missed += 1
                target_world = (positions[joint][0], MISS_FLOOR_Y,
                                positions[joint][2])
        elif mode == "nearest":
            snapped, _ = fn.getClosestPoint(om.MPoint(positions[joint]),
                                            om.MSpace.kWorld)
            target_world = (snapped.x, snapped.y, snapped.z)
        else:
            fractions = normalized_in_box(positions[joint], src_lo,
                                          src_hi)
            stretched = box_point(fractions, tgt_lo, tgt_hi)
            snapped, _ = fn.getClosestPoint(om.MPoint(stretched),
                                            om.MSpace.kWorld)
            target_world = (snapped.x, snapped.y, snapped.z)
        target_local = _world_to_local(target_world, joint)
        rest_local = [cmds.getAttr(_rest_attr(joint, axis))
                      for axis in AXES]
        delta = [target_local[i] - rest_local[i] for i in range(3)]
        begins = (start_frame_for(dists[joint], dist_max, start,
                                  wave_travel)
                  + height_fraction(positions[joint][1], y_lo, y_hi)
                  * layer_delay)
        if speed:
            flight = math.sqrt(sum(d * d for d in delta)) / speed
        else:
            flight = float(duration)
        total = (begins - start) + flight
        frames_i = int(math.ceil(total)) if total > 0 else 0
        longest = max(longest, frames_i)
        for frame in range(start, start + frames_i + 1):
            if speed:
                s = (1.0 if flight <= 0
                     else min(1.0, max(0.0, (frame - begins) / flight)))
            else:
                s = morph_progress(frame, begins, duration)
            for i, axis in enumerate(AXES):
                value = rest_local[i] + delta[i] * s
                cmds.setKeyframe(joint, attribute="translate" + axis,
                                 time=frame, value=value)
    return todo, skipped, missed, longest


def remove_morph(joints):
    """Cut our keys, put the stored rest back, drop the markers; returns
    how many joints were cleaned. Same markers as the wave and melt
    tools, so this also removes those."""
    cleaned = 0
    for joint in joints:
        touched = False
        for axis in AXES:
            rest_attr = _rest_attr(joint, axis)
            if not cmds.objExists(rest_attr):
                continue
            channel = "translate" + axis
            cmds.cutKey(joint, attribute=channel, clear=True)
            cmds.setAttr(joint + "." + channel, cmds.getAttr(rest_attr))
            cmds.deleteAttr(joint, attribute=REST_ATTR + axis)
            touched = True
        if touched:
            cleaned += 1
    return cleaned


# ------------------------------------------------------------------- window

def _say(message):
    if _status and cmds.text(_status, exists=True):
        cmds.text(_status, edit=True, label=message)
    print("bonemorph: " + message)


def _frame_range():
    start = int(math.floor(cmds.playbackOptions(query=True, min=True)))
    end = int(math.ceil(cmds.playbackOptions(query=True, max=True)))
    return start, end


def _apply_pressed(*_):
    try:
        duration = cmds.floatFieldGrp(_frames, query=True, value1=True)
        sel_joints = cmds.ls(selection=True, type="joint",
                             long=True) or []
        if not sel_joints:
            _say("Select joints and the target mesh.")
            return
        joints = target_joints_from(sel_joints)
        meshes = selected_meshes()
        own = [m for m in meshes if skinned_to(m, joints)]
        targets = [m for m in meshes if m not in own]
        if len(targets) != 1:
            _say("Select exactly one target mesh with the bones "
                 "(%d selected; the bones' own skin does not count)."
                 % len(targets))
            return
        timing = TIMINGS.get(cmds.optionMenu(_timing, query=True,
                                             value=True), "speed")
        speed_val = cmds.floatFieldGrp(_speed, query=True, value1=True)
        if timing == "fixed" and duration <= 0:
            _say("Morph frames must be positive.")
            return
        if timing == "speed" and speed_val <= 0:
            _say("Speed must be positive.")
            return
        wave_val = cmds.floatFieldGrp(_wave, query=True, value1=True)
        layer_val = cmds.floatFieldGrp(_layer, query=True, value1=True)
        if wave_val < 0 or layer_val < 0:
            _say("Wave travel and Layer delay must be zero or positive.")
            return
        speed_arg = speed_val if timing == "speed" else None
        mode = MODES.get(cmds.optionMenu(_mode, query=True, value=True),
                         "project")
        start, end = _frame_range()
        cmds.undoInfo(openChunk=True)
        try:
            keyed, skipped, missed, longest = apply_morph(
                joints, targets[0], duration, start, mode, speed_arg,
                wave_val, layer_val)
        finally:
            cmds.undoInfo(closeChunk=True)
        message = ("Morph on %d joint(s) onto %s (%s), frames %d..%d."
                   % (len(keyed), targets[0].split("|")[-2], mode,
                      start, start + longest))
        if speed_arg is not None:
            message += " Constant speed %g/frame." % speed_arg
        if wave_val > 0:
            message += " Melt wave %g." % wave_val
        if layer_val > 0:
            message += " Layer delay %g." % layer_val
        if start + longest > end:
            message += " Ends past the range end."
        if own:
            message += " Own skin mesh ignored."
        if missed:
            message += (" %d ray(s) missed - dropped to Y %g."
                        % (missed, MISS_FLOOR_Y))
        if skipped:
            names = ", ".join(skipped[:4])
            if len(skipped) > 4:
                names += " +%d more" % (len(skipped) - 4)
            message += " Skipped (own animation): %s." % names
        _say(message)
    except Exception as exc:
        _say("Failed: %s" % exc)
        raise


def _remove_pressed(*_):
    try:
        sel_joints = cmds.ls(selection=True, type="joint", long=True) or []
        if not sel_joints:
            _say("Select joints first.")
            return
        joints = target_joints_from(sel_joints)
        cmds.undoInfo(openChunk=True)
        try:
            cleaned = remove_morph(joints)
        finally:
            cmds.undoInfo(closeChunk=True)
        if cleaned:
            _say("Morph removed from %d joint(s)." % cleaned)
        else:
            _say("No morph on the selection.")
    except Exception as exc:
        _say("Failed: %s" % exc)
        raise


def show():
    global _frames, _mode, _timing, _speed, _wave, _layer, _status
    if cmds.window(WINDOW, exists=True):
        cmds.deleteUI(WINDOW)
    cmds.window(WINDOW, title="Bone Morph", sizeable=False)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=6,
                      columnOffset=("both", 10))
    cmds.text(label="Select bones (or their root) AND one target mesh,",
              align="left")
    cmds.text(label="press Apply Morph - the bones lay out over its "
                    "surface.",
              align="left")
    _frames = cmds.floatFieldGrp(
        label="Morph frames", value1=20.0, precision=1,
        annotation="How many frames the flight from the rest shape to "
                   "the target surface takes, starting at the playback "
                   "range start.")
    _mode = cmds.optionMenu(
        label="Mode",
        annotation="Project down: a ray straight down from each bone - "
                   "the bone lands where the ray hits the target, or on "
                   "Y 0 when it misses. Project to nearest: the ray aims "
                   "at the target itself and lands on the nearest point "
                   "of its surface - never misses. Stretch: the old "
                   "bounding-box fit plus closest-point snap.")
    for label in ("Project down (rays)", "Project to nearest (rays)",
                  "Stretch to surface"):
        cmds.menuItem(label=label)
    _timing = cmds.optionMenu(
        label="Timing",
        annotation="Constant speed: bones fly linearly at Speed units "
                   "per frame - near bones land early, far bones later. "
                   "Fixed frames: every bone takes Morph frames and all "
                   "land together.")
    for label in ("Constant speed", "Fixed frames"):
        cmds.menuItem(label=label)
    _speed = cmds.floatFieldGrp(
        label="Speed (units/frame)", value1=10.0, precision=2,
        annotation="How far a bone travels each frame under Constant "
                   "speed timing.")
    _wave = cmds.floatFieldGrp(
        label="Wave travel", value1=20.0, precision=1,
        annotation="Melt-style stagger: the outermost bones leave first "
                   "and the start front converges on the middle over "
                   "this many frames. 0 starts everyone together.")
    _layer = cmds.floatFieldGrp(
        label="Layer delay", value1=0.0, precision=1,
        annotation="Extra start lag for the top of the group - the "
                   "bottom leaves first. 0 keeps the layers together.")
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1,
                   columnAttach=[(1, "both", 0), (2, "both", 0)])
    cmds.button(label="Apply Morph", height=34, command=_apply_pressed)
    cmds.button(label="Remove Morph", height=34, width=110,
                command=_remove_pressed)
    cmds.setParent("..")
    _status = cmds.text(label="", align="left")
    cmds.separator(height=4, style="none")
    cmds.showWindow(WINDOW)
