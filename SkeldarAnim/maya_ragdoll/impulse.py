"""Ragdoll impulses: an arrow on a body part, a hit along it at its own frame (2026-10-16).

Spec `docs/superpowers/specs/2026-10-16-ragdoll-impulse-design.md`. `create` puts an arrow on the
body the selection names (its tip on the body's centre, pointing along the view); it hangs in a
space following the body's first bone, so it rides the take and the fall. `arrows` lists a rig's
arrows; Fall reads them (`hits`) at its first frame and hits each body at its arrow's frame.
"""

import maya.cmds as cmds
import numpy as np

from maya_ragdoll import plan

MARKER = "skeldarRagdollImpulse"
SPACE_MARKER = "skeldarRagdollImpulseSpace"
GROUP_MARKER = "skeldarRagdollImpulses"
GROUP_NAME = "RagdollImpulses"
SPACE_SUFFIX = "_impulseSpace"
UNDO_CHUNK = "skeldarRagdollImpulse"
DEFAULT_SPEED = 5.0                # m/s
HEAD = (3.0, 6.0)                  # the head's half width and length, cm
COLOUR = (1.0, 0.45, 0.1)

NOTHING = "Select a part of a rig - + Impulse puts an arrow on it"


def _long(node):
    return (cmds.ls(node, long=True) or [None])[0]


# ------------------------------------------------------------------ the view

def view_direction():
    """The direction the active view looks along (world), else the persp camera's."""
    camera = None
    try:
        panel = cmds.getPanel(withFocus=True)
        if panel and cmds.getPanel(typeOf=panel) == "modelPanel":
            camera = cmds.modelPanel(panel, query=True, camera=True)
    except Exception:                                    # noqa: BLE001 - no UI
        camera = None
    if not camera or not cmds.objExists(camera):
        camera = "persp"
    m = plan.mat(cmds.xform(camera, query=True, worldSpace=True, matrix=True))
    return -plan.rot(m)[2]


def arrow_matrix(tip, direction):
    """A 4x4 whose +Z is `direction` and whose origin is `tip`, rolled so its X stays level."""
    z = plan._unit(direction)
    x = plan.perpendicular(z, np.cross(np.array([0.0, 1.0, 0.0]), z))
    if np.linalg.norm(x) < 1e-6:
        x = plan.perpendicular(z, np.array([1.0, 0.0, 0.0]))
    y = np.cross(z, x)
    return plan.frame(np.array([x, y, z]), tip)


# ------------------------------------------------------------------ the arrow

def _curve(points, name, parent):
    t = cmds.curve(degree=1, point=points, name=name)
    shape = cmds.listRelatives(t, shapes=True, fullPath=True)[0]
    shape = cmds.parent(shape, parent, relative=True, shape=True)[0]
    cmds.delete(t)
    return shape


def _draw(arrow):
    """The head on the arrow itself, the shaft on a child its `speed` stretches."""
    w, l = HEAD
    for points in (((w, 0, -l), (0, 0, 0), (-w, 0, -l)), ((0, w, -l), (0, 0, 0), (0, -w, -l))):
        _curve(points, "impulseHead", arrow)
    shaft = cmds.createNode("transform", name=arrow.split("|")[-1].split(":")[-1] + "_shaft",
                            parent=arrow, skipSelect=True)
    _curve(((0, 0, 0), (0, 0, -1)), "impulseShaft", shaft)
    length = cmds.createNode("multDoubleLinear", skipSelect=True)
    cmds.setAttr(length + ".input2", plan.SHAFT_CM)
    cmds.connectAttr(arrow + ".speed", length + ".input1")
    cmds.connectAttr(length + ".output", shaft + ".scaleZ")
    cmds.setAttr(shaft + ".overrideEnabled", 1)
    cmds.setAttr(shaft + ".overrideDisplayType", 2)       # reference: the head is what is picked
    cmds.setAttr(arrow + ".overrideEnabled", 1)
    cmds.setAttr(arrow + ".overrideRGBColors", 1)
    cmds.setAttr(arrow + ".overrideColorRGB", *COLOUR)


def _attributes(arrow, key, frame):
    cmds.addAttr(arrow, longName=MARKER, dataType="string")
    cmds.setAttr(arrow + "." + MARKER, key, type="string")
    cmds.addAttr(arrow, longName="frame", attributeType="long", defaultValue=int(frame))
    cmds.addAttr(arrow, longName="speed", attributeType="double", minValue=0.0,
                 defaultValue=DEFAULT_SPEED)
    cmds.addAttr(arrow, longName="enabled", attributeType="bool", defaultValue=True)
    for attr in ("frame", "speed", "enabled"):
        cmds.setAttr(arrow + "." + attr, keyable=False, channelBox=True)
    for attr in ("sx", "sy", "sz"):
        cmds.setAttr(arrow + "." + attr, lock=True, keyable=False, channelBox=False)


def _bodies_now(ref):
    from maya_poselib import scene
    bones, _convention = scene.skeleton(ref)
    worlds = dict((leaf, plan.mat(bone["world"])) for leaf, bone in bones.items())
    return bones, worlds


def create(selection=None):
    """(arrow path, line): an arrow on the body the first selected node is nearest."""
    from maya_ragdoll import fall as rd
    from maya_scenesetup import weaponspace
    import maya_rigs
    from maya_scenetabs import scope
    if selection is None:
        selection = cmds.ls(selection=True, long=True) or []
    if not selection:
        raise rd.Refused(NOTHING)
    ref = rd._ref(selection)
    bones, worlds = _bodies_now(ref)
    missing = plan.missing_bodies(bones)
    if missing:
        raise rd.Refused(rd.MISSING % (ref.label, ", ".join(missing)))
    keys = [row[0] for row in plan.BODIES]
    axes = dict((key, plan.axis_points(key, worlds)) for key in keys)
    pivot = cmds.xform(selection[0], query=True, worldSpace=True, rotatePivot=True)
    key = plan.nearest_body(pivot, axes)
    first = [row for row in plan.BODIES if row[0] == key][0][1][0]
    a, b = axes[key]
    world = arrow_matrix((a + b) * 0.5, view_direction())
    frame = int(round(cmds.currentTime(query=True)))
    cmds.undoInfo(openChunk=True, chunkName=UNDO_CHUNK)
    try:
        space = weaponspace.ensure_marked_space(bones[first]["path"], SPACE_MARKER, GROUP_MARKER,
                                                GROUP_NAME, SPACE_SUFFIX)
        name = scope.as_created(maya_rigs.node(ref.rig, "impulse1"))
        arrow = _long(cmds.createNode("transform", name=name, parent=space, skipSelect=True))
        _attributes(arrow, key, frame)
        _draw(arrow)
        cmds.xform(arrow, worldSpace=True, matrix=plan.flat(world))
        cmds.select(arrow, replace=True)
    finally:
        cmds.undoInfo(closeChunk=True)
    line = "%s on %s's %s at frame %d, %.0f m/s - move and turn it; Frame, Speed in the Channel Box" \
        % (arrow.split("|")[-1].split(":")[-1], ref.label, key, frame, DEFAULT_SPEED)
    return arrow, line


# ------------------------------------------------------------------ reading them

def arrows(rig):
    """The rig's arrows (long paths)."""
    found = cmds.ls("*." + MARKER, recursive=True, objectsOnly=True, long=True) or []
    group = getattr(rig, "group", None)
    import maya_rigs
    return sorted(p for p in found if group and maya_rigs.under(p, group))


def read(arrow):
    """{"name", "key", "frame", "speed", "enabled"} of one arrow."""
    return {"path": arrow, "name": arrow.split("|")[-1].split(":")[-1],
            "key": cmds.getAttr(arrow + "." + MARKER),
            "frame": int(cmds.getAttr(arrow + ".frame")),
            "speed": float(cmds.getAttr(arrow + ".speed")),
            "enabled": bool(cmds.getAttr(arrow + ".enabled"))}


def hits(rig, body_first, a, b):
    """(hits, notes): every enabled arrow of the rig read now (the fall's first frame) as
    {"name", "key", "at", "speed", "tip", "direction"} in its body's frame; `notes` names the
    arrows that do nothing (after the fall, a body the rig has none of, a speed of 0)."""
    out, notes = [], []
    for path in arrows(rig):
        arrow = read(path)
        if not arrow["enabled"]:
            continue
        if arrow["key"] not in body_first:
            notes.append("%s names no body (%s)" % (arrow["name"], arrow["key"]))
            continue
        at = plan.hit_frame(arrow["frame"], a, b)
        if at is None:
            notes.append("%s at %d is after the fall (ends %d)" % (arrow["name"], arrow["frame"], b))
            continue
        if arrow["speed"] <= 0:
            continue
        world = plan.mat(cmds.xform(path, query=True, worldSpace=True, matrix=True))
        tip, direction = plan.in_body(world, body_first[arrow["key"]])
        out.append(dict(arrow, at=at, tip=tip, direction=direction))
    return out, notes


def summary(done):
    """«2 impulses: head 6 m/s at 12, pelvis 3 m/s at 4»."""
    if not done:
        return ""
    parts = ["%s %g m/s at %d" % (h["key"], round(h["speed"], 2), h["frame"]) for h in done]
    return "%d impulse%s: %s" % (len(done), "" if len(done) == 1 else "s", ", ".join(parts))
