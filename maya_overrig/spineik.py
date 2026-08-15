"""Spline-IK spine: three controls, no aim, and the bottom carries the hips.

The hybrid spine (Advanced Skeleton pattern; see the 2026-08-15 spline spine
spec): an ikSplineSolver runs spine_01..spine_04 along a degree-2 curve; the
top control sits at spine_04 -- one bone below the chest tip, by the user's
request -- and owns its orientation outright, while spine_05 rides above it
keeping its own local animation. The middle control is held 50/50 between
the hips and the top through a buffer group and stays fully animatable.
Twist comes from the solver's advanced twist (Object Rotation Up start/end),
which is what keeps aim behaviour out of the spine.

The bottom control moves the pelvis, not just the lower spine: the pelvis's
own FK controller is re-hung INSIDE the bottom node through OverRig's
`apply_Parent_in` (animation re-baked, zero drift), so the general pelvis
control keeps working and everything it carries -- the pelvis bone, FK thigh
chains -- follows the bottom node. The switch lifts it back out before this
rig is torn down.

Two hidden followers close the loops without cycles: `IKSpine_hip` rides the
pelvis BONE and carries the curve's base CV plus the middle blend, so the
spine base tracks the hips wherever their motion comes from; `IKSpine_chest`
rides the spine_05 bone and is what dependent chains (neck, clavicles) hang
from, so spine_05's own local keys keep carrying them. The zero groups
follow the ROOT bone: the chest stays planted while the hips sway, and the
whole rig rides root motion.
"""

import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

from maya_overrig import overrig

TOP = "IKSpine_top"
MID = "IKSpine_mid"
BOT = "IKSpine_bot"
HIP = "IKSpine_hip"
CHEST = "IKSpine_chest"
GROUP = "IKSpine_gr"

# Matches the FK rings' centre colour; small duplication instead of importing
# fkcontrols, which would close an import cycle through builder.
_CENTRE = (1.0, 0.85, 0.25)
_LINE_WIDTH = 2.0
_SECTIONS = 16


def _world_pos(node):
    return cmds.xform(node, query=True, worldSpace=True, translation=True)


def _make_control(name, position, radius):
    """A flat ring at a world position, world-aligned axes.

    World alignment matters twice: the twist up-vectors are expressed in the
    up objects' spaces, and equal axes on the blend targets keep the mid
    interpolation sane.
    """
    ctrl = cmds.circle(name=name, normal=(0, 1, 0), radius=radius,
                       sections=_SECTIONS, constructionHistory=False)[0]
    shape = cmds.listRelatives(ctrl, shapes=True, fullPath=True)[0]
    cmds.setAttr(shape + ".overrideEnabled", 1)
    cmds.setAttr(shape + ".overrideRGBColors", 1)
    cmds.setAttr(shape + ".overrideColorRGB", *_CENTRE)
    if cmds.attributeQuery("lineWidth", node=shape, exists=True):
        cmds.setAttr(shape + ".lineWidth", _LINE_WIDTH)
    cmds.xform(ctrl, worldSpace=True, translation=position)
    return ctrl


def _buffered(name, position, radius):
    """Control under a zero group: the control's own channels start clean."""
    zero = cmds.group(empty=True, name=name + "_zero")
    cmds.xform(zero, worldSpace=True, translation=position)
    ctrl = _make_control(name, position, radius)
    ctrl = cmds.parent(ctrl, zero)[0]
    return zero, ctrl


def _follower(name, position, target):
    """A hidden world-aligned locator riding a bone via constraint.

    World-aligned at rest (the constraint keeps the offset), so vectors
    expressed in its space read as world vectors at the build pose.
    """
    loc = cmds.spaceLocator(name=name)[0]
    cmds.xform(loc, worldSpace=True, translation=position)
    cmds.parentConstraint(target, loc, maintainOffset=True)
    cmds.setAttr(loc + ".visibility", 0)
    return loc


def _joint_up_vector(joint):
    """The joint's local +Z in world space -- the twist up reference.

    The bones aim along local X on this skeleton (measured; CLAUDE.md), so
    either perpendicular axis works as "up"; Z is picked and the world
    vector handed to the solver so the pose cannot roll at rest.
    """
    m = om.MMatrix(cmds.xform(joint, query=True, worldSpace=True,
                              matrix=True))
    up = om.MVector(m[8], m[9], m[10]).normal()
    return (up.x, up.y, up.z)


def _pelvis_driver_knot(pelvis):
    """The OverRig knot driving the pelvis, or None.

    Constraint -> driver -> first self-or-ancestor that is an OverRig knot.
    Taking the first knot (not the topmost ancestor) matters: the pelvis
    controller usually hangs inside the root controller, and the root
    controller must NOT be the one re-hung under the bottom node.
    """
    knots = set(overrig.set_members(overrig.KNOT_SET))
    for con in cmds.listRelatives(pelvis, children=True, type="constraint",
                                  fullPath=True) or []:
        for driver in cmds.listConnections(con + ".target", source=True,
                                           destination=False) or []:
            if cmds.objectType(driver).endswith("Constraint"):
                continue
            paths = cmds.ls(driver, long=True) or []
            node = paths[0] if paths else None
            while node:
                if node in knots:
                    return node
                trimmed = node.rsplit("|", 1)[0]
                node = trimmed if trimmed else None
    return None


def build_spine(joint_paths):
    """Build the spline-IK spine over the spine bones.

    `joint_paths` is the full spine chain (spine_01..spine_05); the solver
    runs to the second-to-last bone, the last one rides it. The caller
    (builder.build) wraps this in the undo chunk and records the scene diff
    as the limb manifest; nothing here needs bookkeeping.
    """
    joints = [cmds.ls(j, long=True)[0] for j in joint_paths]
    driven = joints[:-1]              # spine_01 .. spine_04
    start, end = driven[0], driven[-1]
    chest_bone = joints[-1]           # spine_05: follows, keeps its keys
    mid_joint = driven[len(driven) // 2]
    pelvis = (cmds.listRelatives(start, parent=True, fullPath=True)
              or [None])[0]
    root_bone = (cmds.listRelatives(pelvis, parent=True, fullPath=True)
                 or [None])[0] if pelvis else None

    range_start = cmds.playbackOptions(query=True, minTime=True)
    cmds.currentTime(range_start)

    p_start = _world_pos(start)
    p_mid = _world_pos(mid_joint)
    p_end = _world_pos(end)
    p_bot = _world_pos(pelvis) if pelvis else p_start

    height = abs(_world_pos(chest_bone)[1] - p_bot[1]) or 1.0
    radius = height * 0.45

    grp = cmds.group(empty=True, name=GROUP)

    bot_zero, bot = _buffered(BOT, p_bot, radius)
    top_zero, top = _buffered(TOP, p_end, radius * 0.9)
    bot_zero, top_zero = cmds.parent(bot_zero, top_zero, grp)

    # The zero groups ride the ROOT bone: the chest stays planted while the
    # hips sway, and the whole rig follows root motion.
    if root_bone:
        cmds.parentConstraint(root_bone, bot_zero, maintainOffset=True)
        cmds.parentConstraint(root_bone, top_zero, maintainOffset=True)

    # Followers: the curve base and the middle blend must track the hips'
    # ACTUAL motion -- which, once the pelvis controller hangs inside the
    # bottom node, happens below that node, not at it.
    hip = _follower(HIP, p_start, pelvis or start)
    hip = cmds.parent(hip, grp)[0]
    chest = _follower(CHEST, _world_pos(chest_bone), chest_bone)
    chest = cmds.parent(chest, grp)[0]

    # The middle: held 50/50 between hips and chest control, animatable on
    # top of the blend through its buffer.
    blend = cmds.group(empty=True, name=MID + "_blend")
    cmds.xform(blend, worldSpace=True, translation=p_mid)
    blend = cmds.parent(blend, grp)[0]
    cmds.pointConstraint(hip, top, blend, maintainOffset=True)
    orient = cmds.orientConstraint(hip, top, blend, maintainOffset=True)[0]
    cmds.setAttr(orient + ".interpType", 2)  # shortest -- no blend flips
    mid_zero, mid = _buffered(MID, p_mid, radius * 0.7)
    mid_zero = cmds.parent(mid_zero, blend)[0]

    # Capture: the controls take over the bones' current animation -- the
    # middle from spine_03, the top from spine_04 (its driven bone). The
    # bottom stays clean: the hip animation lives on the pelvis controller
    # that is about to hang inside it.
    temps = [
        cmds.parentConstraint(mid_joint, mid, maintainOffset=True)[0],
        cmds.parentConstraint(end, top, maintainOffset=True)[0],
    ]
    overrig.fast_bake([mid, top])
    cmds.delete([t for t in temps if cmds.objExists(t)])

    # The driven bones' rotation curves would fight the solver through
    # pairBlends; their animation lives on the controls now, and a bake
    # puts it back. spine_05 keeps its keys -- nothing drives it.
    cmds.currentTime(range_start)
    cmds.cutKey(driven, attribute=("rotateX", "rotateY", "rotateZ"),
                clear=True)

    # Drive: curve -> clusters (hip follower, mid, top) -> spline solver.
    curve = cmds.curve(degree=2, point=[p_start, p_mid, p_end],
                       name="IKSpine_curve")
    cmds.setAttr(curve + ".inheritsTransform", 0)
    curve = cmds.parent(curve, grp)[0]
    for index, carrier in ((0, hip), (1, mid), (2, top)):
        handle = cmds.cluster(curve + ".cv[{0}]".format(index),
                              name="IKSpine_cluster{0}".format(index))[1]
        handle = cmds.parent(handle, carrier)[0]
        cmds.setAttr(handle + ".visibility", 0)

    ik = cmds.ikHandle(solver="ikSplineSolver", startJoint=start,
                       endEffector=end, curve=curve, createCurve=False,
                       parentCurve=False, rootOnCurve=True,
                       name="IKSpine_handle")[0]
    ik = cmds.parent(ik, grp)[0]
    cmds.setAttr(ik + ".visibility", 0)

    # Advanced twist, start/end -- this is what replaces any aim setup: the
    # roll interpolates from the hips (wherever their motion comes from) to
    # the top control.
    up = _joint_up_vector(mid_joint)
    cmds.setAttr(ik + ".dTwistControlEnable", 1)
    cmds.setAttr(ik + ".dWorldUpType", 4)  # object rotation up (start/end)
    cmds.setAttr(ik + ".dForwardAxis", 0)  # bones aim +X on this skeleton
    cmds.setAttr(ik + ".dWorldUpAxis", 3)  # joint-local +Z is "up"
    cmds.setAttr(ik + ".dWorldUpVector", *up)
    cmds.setAttr(ik + ".dWorldUpVectorEnd", *up)
    cmds.connectAttr(hip + ".worldMatrix[0]", ik + ".dWorldUpMatrix",
                     force=True)
    cmds.connectAttr(top + ".worldMatrix[0]", ik + ".dWorldUpMatrixEnd",
                     force=True)

    # The solver orients the chain, not its last driven joint: spine_04
    # belongs to the top control, exactly. spine_05 rides it.
    cmds.orientConstraint(top, end, maintainOffset=True)

    # The bottom node carries the hips: the pelvis's own controller is
    # re-hung inside it, animation re-baked -- the general pelvis control
    # keeps working, and moving the bottom node now moves the pelvis and
    # everything it carries. Without a pelvis controller (bare-skeleton
    # builds) the bottom node simply has no passenger.
    passenger = _pelvis_driver_knot(pelvis) if pelvis else None
    if passenger:
        cmds.select([passenger, bot], replace=True)
        mel.eval("apply_Parent_in()")

    cmds.select(clear=True)
    return grp
