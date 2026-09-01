"""Melt animation over a group of joints.

Test-mode tool, deliberately minimal (the project's spec/TDD pipeline is
skipped on purpose): select joints - or one root joint, then the joints
under it are taken - and press Apply Melt. Every joint sinks smoothly to
the floor plane (a world height, 0 by default), and the melt front
CONVERGES on the object's middle: the outermost joints - by horizontal
distance from the group's bounding-box centre - start sinking first, the
centre sinks last and lands exactly on the last frame of the playback
range. Each joint's own sink takes Melt frames and eases in and out
(smoothstep), keys on every frame of the range, translateY only.

With a target mesh in the selection the object melts ONTO IT instead of
onto the flat floor: each joint's landing height comes from a ray cast
straight down onto that mesh (the maya_bonemorph projection), a ray
that misses falls back to Floor Y, and the mesh skinned to the selected
bones never counts as the target. Without a mesh the flat floor works
as before. The schedule is the same either way.

Layer delay staggers the group by height - the boundary runs along the
group's vertical axis: the bottom of the object starts sinking first and
the top lags by up to that many frames, so the base melts out from under
the top. With a delay the top-centre joint is the one landing on the
last frame; a range shorter than melt + delay leaves the top unlanded
and the status line says so. Delay 0 melts all layers together (the old
behaviour).

The rest value is stored on the joint under the same geoWaveRest<axis>
marker maya_bonewave uses - deliberately shared, so Wave and Melt can be
applied over each other on the same bones, both always rebuild from the
one true rest, and either Remove puts the exact rest back. A channel
animated by something without the marker is skipped and named.

Run:
    import sys; sys.path.append(r"C:/!!!Work/MayaScripts")
    import maya_bonemelt; maya_bonemelt.show()
"""

import math

import maya.api.OpenMaya as om
import maya.cmds as cmds

WINDOW = "boneMeltWindow"
REST_ATTR = "geoWaveRest"

_melt_frames = None
_floor = None
_layer = None
_status = None


# ---------------------------------------------------------------- pure logic

def melt_progress(frame, start_frame, duration):
    """0 before the joint starts sinking, 1 once it has landed, a
    smoothstep ease in between."""
    if duration <= 0:
        return 1.0 if frame >= start_frame else 0.0
    p = (frame - start_frame) / float(duration)
    p = max(0.0, min(1.0, p))
    return p * p * (3.0 - 2.0 * p)


def start_frame_for(dist, dist_max, start, travel):
    """When a joint begins to sink: the farthest joints at the range
    start, the centre after the whole front has travelled in."""
    if dist_max <= 0.0:
        return float(start)
    return start + (dist_max - dist) / dist_max * travel


def height_fraction(y, y_lo, y_hi):
    """0 at the bottom of the group, 1 at the top; a flat group reads 0
    so no layer lags another."""
    size = y_hi - y_lo
    return (y - y_lo) / size if size > 1e-9 else 0.0


def bbox_center(positions):
    """Centre of the bounding box of the given (x, y, z) positions."""
    lo = [min(p[i] for p in positions) for i in range(3)]
    hi = [max(p[i] for p in positions) for i in range(3)]
    return [(lo[i] + hi[i]) * 0.5 for i in range(3)]


def horizontal_distance(position, center):
    """Distance from the group's central vertical axis, in the floor
    plane (XZ)."""
    dx = position[0] - center[0]
    dz = position[2] - center[2]
    return math.sqrt(dx * dx + dz * dz)


# ---------------------------------------------------------------- scene side

def target_joints():
    """Selected joints; a single selected joint with joint children means
    the group under it (the geobones root gesture)."""
    sel = cmds.ls(selection=True, type="joint", long=True) or []
    if len(sel) == 1:
        kids = cmds.listRelatives(sel[0], allDescendents=True,
                                  type="joint", fullPath=True) or []
        if kids:
            return kids
    return sel


def _rest_attr(joint, axis):
    return joint + "." + REST_ATTR + axis


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


def existing_skin(shape):
    """The skinCluster already deforming the shape, or None."""
    history = cmds.listHistory(shape, pruneDagObjects=True) or []
    clusters = cmds.ls(history, type="skinCluster")
    return clusters[0] if clusters else None


def skinned_to(shape, joints):
    """True when the shape's skin is driven by any of the given joints -
    that mesh is the bones' own skin, never the melt target."""
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


def apply_melt(joints, duration, floor_y, start, end, layer_delay=0.0,
               target_shape=None):
    """Per-frame keys on translateY for every joint; returns (keyed
    joints, skipped joint names, missed ray count - always 0 without a
    target). With target_shape every joint lands on the down-ray hit of
    that mesh and floor_y is the miss fallback; without it floor_y is
    the landing height for everyone. Assumes an unrotated parent (the
    geobones root), where local Y offsets are world Y offsets."""
    todo = []
    skipped = []
    for joint in joints:
        plug = joint + ".translateY"
        has_curve = bool(cmds.listConnections(plug, source=True,
                                              destination=False,
                                              type="animCurve"))
        if has_curve and not cmds.objExists(_rest_attr(joint, "Y")):
            skipped.append(joint.split("|")[-1])
            continue
        todo.append(joint)

    # First pass: everything back to rest, so positions and heights are
    # read from the unmelted pose.
    for joint in todo:
        plug = joint + ".translateY"
        rest_attr = _rest_attr(joint, "Y")
        if cmds.objExists(rest_attr):
            rest = cmds.getAttr(rest_attr)
        else:
            rest = cmds.getAttr(plug)
            cmds.addAttr(joint, longName=REST_ATTR + "Y",
                         attributeType="double")
            cmds.setAttr(rest_attr, rest)
        cmds.cutKey(joint, attribute="translateY", clear=True)
        cmds.setAttr(plug, rest)

    positions = {}
    for joint in todo:
        positions[joint] = cmds.xform(joint, query=True, worldSpace=True,
                                      translation=True)
    center = (bbox_center(list(positions.values())) if todo
              else [0.0, 0.0, 0.0])
    dists = {j: horizontal_distance(positions[j], center) for j in todo}
    dist_max = max(dists.values()) if todo else 0.0
    y_lo = min(p[1] for p in positions.values()) if todo else 0.0
    y_hi = max(p[1] for p in positions.values()) if todo else 0.0
    travel = max((end - start) - duration - layer_delay, 0.0)
    fn = _mesh_fn(target_shape) if target_shape else None
    missed = 0

    for joint in todo:
        rest = cmds.getAttr(_rest_attr(joint, "Y"))
        land_y = floor_y
        if fn is not None:
            hit = _ray_down_hit(fn, positions[joint])
            if hit is None:
                missed += 1
            else:
                land_y = hit[1]
        drop = land_y - positions[joint][1]
        begins = (start_frame_for(dists[joint], dist_max, start, travel)
                  + height_fraction(positions[joint][1], y_lo, y_hi)
                  * layer_delay)
        for frame in range(start, end + 1):
            cmds.setKeyframe(joint, attribute="translateY", time=frame,
                             value=rest + drop * melt_progress(frame,
                                                               begins,
                                                               duration))
    return todo, skipped, missed


def remove_melt(joints):
    """Cut our keys, put the stored rest back, drop the markers; returns
    how many joints were cleaned. Same markers as maya_bonewave, so this
    also removes a wave."""
    cleaned = 0
    for joint in joints:
        touched = False
        for axis in ("X", "Y", "Z"):
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
    print("bonemelt: " + message)


def _frame_range():
    start = int(math.floor(cmds.playbackOptions(query=True, min=True)))
    end = int(math.ceil(cmds.playbackOptions(query=True, max=True)))
    return start, end


def _apply_pressed(*_):
    try:
        duration = cmds.floatFieldGrp(_melt_frames, query=True,
                                      value1=True)
        floor_y = cmds.floatFieldGrp(_floor, query=True, value1=True)
        layer_delay = cmds.floatFieldGrp(_layer, query=True, value1=True)
        joints = target_joints()
        if not joints:
            _say("Select joints first.")
            return
        if duration <= 0:
            _say("Melt frames must be positive.")
            return
        if layer_delay < 0:
            _say("Layer delay must be zero or positive.")
            return
        meshes = selected_meshes()
        own = [m for m in meshes if skinned_to(m, joints)]
        targets = [m for m in meshes if m not in own]
        if len(targets) > 1:
            _say("Select at most one target mesh with the bones "
                 "(%d selected; the bones' own skin does not count)."
                 % len(targets))
            return
        target = targets[0] if targets else None
        start, end = _frame_range()
        cmds.undoInfo(openChunk=True)
        try:
            keyed, skipped, missed = apply_melt(joints, duration, floor_y,
                                                start, end, layer_delay,
                                                target)
        finally:
            cmds.undoInfo(closeChunk=True)
        if target:
            message = ("Melt on %d joint(s) onto %s, frames %d..%d."
                       % (len(keyed), target.split("|")[-2], start, end))
            if missed:
                message += (" %d ray(s) missed - dropped to floor %g."
                            % (missed, floor_y))
        else:
            message = ("Melt on %d joint(s), frames %d..%d, floor %g."
                       % (len(keyed), start, end, floor_y))
        if own:
            message += " Own skin mesh ignored."
        if layer_delay > 0:
            message += " Layer delay %g." % layer_delay
        if (end - start) < duration + layer_delay:
            message += " Range shorter than melt + delay - the top does " \
                       "not land."
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
        joints = target_joints()
        if not joints:
            _say("Select joints first.")
            return
        cmds.undoInfo(openChunk=True)
        try:
            cleaned = remove_melt(joints)
        finally:
            cmds.undoInfo(closeChunk=True)
        if cleaned:
            _say("Melt removed from %d joint(s)." % cleaned)
        else:
            _say("No melt on the selection.")
    except Exception as exc:
        _say("Failed: %s" % exc)
        raise


def show():
    global _melt_frames, _floor, _layer, _status
    if cmds.window(WINDOW, exists=True):
        cmds.deleteUI(WINDOW)
    cmds.window(WINDOW, title="Bone Melt", sizeable=False)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=6,
                      columnOffset=("both", 10))
    cmds.text(label="Select joints (or their root), press Apply Melt: "
                    "the edges sink first,",
              align="left")
    cmds.text(label="the middle melts last, everything lands by the end "
                    "of the range.",
              align="left")
    cmds.text(label="Add one target mesh to the selection to melt onto "
                    "it instead of the floor.",
              align="left")
    _melt_frames = cmds.floatFieldGrp(
        label="Melt frames", value1=10.0, precision=1,
        annotation="How many frames one joint takes to sink from its "
                   "rest height to the floor.")
    _floor = cmds.floatFieldGrp(
        label="Floor Y", value1=0.0, precision=3,
        annotation="World height the joints land on.")
    _layer = cmds.floatFieldGrp(
        label="Layer delay", value1=10.0, precision=1,
        annotation="Extra frames the top of the object waits behind the "
                   "bottom - the lower layers sink first. 0 melts all "
                   "layers together.")
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1,
                   columnAttach=[(1, "both", 0), (2, "both", 0)])
    cmds.button(label="Apply Melt", height=34, command=_apply_pressed)
    cmds.button(label="Remove Melt", height=34, width=110,
                command=_remove_pressed)
    cmds.setParent("..")
    cmds.text(label="Keys land on every frame of the playback range.",
              align="left", enable=False)
    _status = cmds.text(label="", align="left")
    cmds.separator(height=4, style="none")
    cmds.showWindow(WINDOW)
