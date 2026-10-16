"""Tools > 1P Setup (2026-10-16): a 3P take split for first person, on one press.

The animator: «мы нажимаем кнопку и у нас все распределяется по слоям. Включив слой нижней
анимации мы получим нашу анимацию нижней части и стабилизированый верх, но ... старая анимация
для третего лица на верхней части ... в слое хранится на всякий случай».

One press on any part of a rig, in one undo chunk:
- the rig's geometry to 1P (`Main.view` = 1) where it has the switch;
- a knot on `FKSpine3_M` (Tools > Knot), so the chest lives on its own;
- Tools > Layer: the lower body and the knot onto `_3P_Lower_Body`, the upper body onto
  `_3P_Upper_Body` - the base keeps the first frame's pose - then the knot's turn moved from
  Lower to Upper (both add by component, so the sum is the take exactly);
- Camera Setup on `camera_root`, the camera parented under the knot with no keys of its own.

Maya will not start a node name with a digit (`3P_...` becomes `P_...`), hence the `_`.
Spec: docs/superpowers/specs/2026-10-16-tools-1p-setup-design.md.
"""

import maya.cmds as cmds

from maya_tools import knotplan as plan
from maya_tools import knots
from maya_tools import layerbake

LOWER = "_3P_Lower_Body"
UPPER = "_3P_Upper_Body"
MARKER = "skeldarFirstPerson"            # on both layers: the rig's namespace
KNOT_CONTROL = "FKSpine3_M"
VIEW_ATTR = "view"                       # Main.view: 0 3P, 1 1P (Manny, Orc D)
SPINE_SWITCH = "FKIKSpine_M"
CAMERA_BONE = "camera_root"

#  The lower body: these controls, and every control whose name holds a leg word (2026-10-16,
#  asked: Spine1-2 with the hips - Spine3 rides its knot, so they cannot move the chest).
LOWER_EXACT = frozenset(("Main", "RootX_M", "FKRoot_M", "HipSwinger_M", "FKSpine1_M",
                         "FKSpine2_M"))
LOWER_WORDS = ("Hip_", "Knee", "Ankle", "Toes", "Heel", "Leg", "Foot", "IKSpine")

NO_RIG = "1P Setup: select any part of a rig"
NO_KNOT_CONTROL = "1P Setup: %s has no %s - the setup needs AdvancedSkeleton's spine"
SPINE_IK = ("1P Setup: %s's spine is in IK (%s.FKIKBlend) - switch the spine to FK in "
            "Connections first")
ALREADY = ("1P Setup: %s is set up already (%s) - Ctrl+Z, or delete the layers and the knot "
           "first")


# -------------------------------------------------------------------- pure

def leaf(path):
    """The control's name without its path and namespace."""
    return path.split("|")[-1].split(":")[-1]


def is_lower(name):
    name = leaf(name)
    return name in LOWER_EXACT or any(word in name for word in LOWER_WORDS)


def split(controls):
    """(lower, upper) of `controls` (paths), in their order; the knot's control in neither."""
    lower, upper = [], []
    for path in controls:
        if leaf(path) == KNOT_CONTROL:
            continue
        (lower if is_lower(path) else upper).append(path)
    return lower, upper


def message(rig, view, lower, upper, camera, notes):
    parts = ["1P Setup on %s" % rig,
             "1P mesh on" if view == "on" else ("1P mesh already on" if view == "already"
                                                else "no 1P mesh on this rig"),
             "%s on a knot" % KNOT_CONTROL,
             "%s: %d control%s + the knot's travel" % (LOWER, lower, "" if lower == 1 else "s"),
             "%s: %d control%s + the knot's turn" % (UPPER, upper, "" if upper == 1 else "s"),
             camera]
    return " | ".join(parts + list(notes))


# ------------------------------------------------------------------- scene

def setup_layers(namespace):
    """Our 1P layers standing for the rig in `namespace`."""
    return [layer for layer in cmds.ls(type="animLayer") or []
            if knots._has(layer, MARKER) and knots._get(layer, MARKER) == namespace]


def _controls(rig):
    members = cmds.sets(rig.control_set, query=True) or []
    out = []
    for path in cmds.ls(members, long=True, type="transform") or []:
        if path not in out:
            out.append(path)
    return out


def _spine_in_ik(rig):
    import maya_rigs
    node = maya_rigs.node(rig, SPINE_SWITCH)
    plug = node + ".FKIKBlend"
    if not cmds.objExists(node) or not cmds.attributeQuery("FKIKBlend", node=node,
                                                           exists=True):
        return ""
    values = cmds.keyframe(plug, query=True, valueChange=True) or [cmds.getAttr(plug)]
    return node if max(values) > 1e-6 else ""


def _camera_bone(rig):
    if not rig.skeleton_root:
        return None
    joints = [rig.skeleton_root] + (cmds.listRelatives(rig.skeleton_root, allDescendents=True,
                                                       type="joint", fullPath=True) or [])
    found = [j for j in joints if leaf(j) == CAMERA_BONE]
    return found[0] if len(found) == 1 else None


def _layered(controls, rigs):
    """(controls something animates, refusal): Layer's own plan for each; a still one left."""
    out = []
    for path in controls:
        _info, refusal = layerbake._plan(path, rigs)
        if refusal:
            if refusal.startswith("nothing animates"):
                continue
            return None, "1P Setup: " + refusal
        out.append(path)
    return out, ""


def _new_layer(before):
    made = [layer for layer in cmds.ls(type="animLayer") or [] if layer not in before]
    return made[-1] if made else None


def _empty_layer(name):
    layer = cmds.animLayer(name)
    cmds.setAttr(layer + ".rotationAccumulationMode", 0)
    cmds.setAttr(layer + ".scaleAccumulationMode", 0)
    return layer


def move_curve(plug, source, target):
    """`plug`'s curve on additive layer `source` moved onto additive layer `target` - the same
    curve node, every key kept. False when `source` holds none for it."""
    curve = (cmds.animLayer(source, query=True, findCurveForPlug=plug) or [None])[0]
    if not curve:
        return False
    for dest in cmds.listConnections(curve + ".output", source=False, destination=True,
                                     plugs=True) or []:
        cmds.disconnectAttr(curve + ".output", dest)
    cmds.animLayer(source, edit=True, removeAttribute=plug)
    cmds.animLayer(target, edit=True, attribute=plug)
    node, attr = plug.split(".", 1)
    cmds.setKeyframe(node, attribute=attr, animLayer=target, identity=True,
                     time=cmds.keyframe(curve, query=True, timeChange=True)[0])
    temporary = cmds.animLayer(target, query=True, findCurveForPlug=plug)[0]
    dests = cmds.listConnections(temporary + ".output", source=False, destination=True,
                                 plugs=True) or []
    cmds.delete(temporary)
    for dest in dests:
        cmds.connectAttr(curve + ".output", dest, force=True)
    return True


def _view_on(rig):
    plug = rig.main + "." + VIEW_ATTR
    if not cmds.attributeQuery(VIEW_ATTR, node=rig.main, exists=True):
        return "none"
    if cmds.getAttr(plug) == 1:
        return "already"
    cmds.setAttr(plug, 1)
    return "on"


def _camera(bone, knot):
    """Camera Setup on `bone`, then the camera into `knot`, standing where it stood at the take's
    first frame, no keys of its own. The words for the line."""
    from maya_scenesetup import bonedrive, camera
    keys = cmds.keyframe(bone, query=True, timeChange=True) or []
    start, end = bonedrive.union_range(cmds.playbackOptions(query=True, min=True),
                                       cmds.playbackOptions(query=True, max=True), keys)
    camera.setup(bone, start, end)
    cam = camera.camera_for(bone)
    if not cam:
        return "no camera made"
    cmds.currentTime(start)
    matrix = cmds.xform(cam, query=True, matrix=True, worldSpace=True)
    cmds.cutKey(cam, attribute=list(camera.CHANNELS), clear=True)
    cam = cmds.ls(cmds.parent(cam, knot)[0], long=True)[0]
    cmds.xform(cam, matrix=matrix, worldSpace=True)
    return "camera %s in the knot, %s follows it" % (leaf(cam), CAMERA_BONE)


def setup(selection=None):
    """The 1P Setup press. The line."""
    import maya_rigs
    rig, refusal = maya_rigs.current_rig(selection)
    if refusal or rig is None:
        return ("1P Setup: " + refusal) if refusal else NO_RIG
    name = maya_rigs.label(rig)
    standing = setup_layers(rig.namespace)
    if standing:
        return ALREADY % (name, ", ".join(standing))
    control = maya_rigs.node(rig, KNOT_CONTROL)
    if not cmds.objExists(control):
        return NO_KNOT_CONTROL % (name, KNOT_CONTROL)
    control = cmds.ls(control, long=True)[0]
    switch = _spine_in_ik(rig)
    if switch:
        return SPINE_IK % (name, leaf(switch))
    rigs = maya_rigs.rigs()
    lower, upper = split(_controls(rig))
    lower, refusal = _layered(lower, rigs)
    if refusal:
        return refusal
    upper, refusal = _layered(upper, rigs)
    if refusal:
        return refusal
    _info, refusal = knots._plan_object(control, "knot")
    if refusal:
        return "1P Setup: " + refusal
    bone = _camera_bone(rig)
    notes = []
    with knots._press("skeldar1PSetup"):
        view = _view_on(rig)
        knots.create("knot", [control], highlight=None)
        knot = knots._knots_driving(control)[0]
        before = set(cmds.ls(type="animLayer") or [])
        line = layerbake.bake(lower + [knot], highlight=None, name=LOWER)
        lower_layer = _new_layer(before)
        if not lower_layer:
            raise RuntimeError("the lower body did not bake: %s" % line)
        before = set(cmds.ls(type="animLayer") or [])
        if upper:
            line = layerbake.bake(upper, highlight=None, name=UPPER)
            upper_layer = _new_layer(before)
            if not upper_layer:
                raise RuntimeError("the upper body did not bake: %s" % line)
        else:
            upper_layer = _empty_layer(UPPER)
            notes.append("nothing animates the upper body")
        for ch in ("rotateX", "rotateY", "rotateZ"):
            move_curve(knot + "." + ch, lower_layer, upper_layer)
        for layer in (lower_layer, upper_layer):
            knots._set_string(layer, MARKER, rig.namespace)
        if bone:
            words = _camera(bone, knot)
        else:
            words = "no %s on this rig - no camera" % CAMERA_BONE
        cmds.select(knot, replace=True)
    return message(name, view, len(lower), len(upper), words, notes)
