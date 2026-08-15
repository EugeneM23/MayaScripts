"""Spline-IK spine: three controls, no aim.

The industry-standard hybrid spine (the Advanced Skeleton pattern, see the
2026-08-15 spine spec addendum): an ikSplineSolver runs the five spine bones
along a degree-2 curve whose three CVs are clustered under three controls --
bottom at pelvis height, top at the chest, middle held 50/50 between them by
point/orient constraints on a buffer group, so it follows both ends yet stays
fully animatable on top of the blend. Twist comes from the solver's advanced
twist (Object Rotation Up start/end, up objects = the bottom and top
controls), which is what keeps aim behaviour out of the spine; the chest bone
itself is orient-constrained to the top control, so the animator owns it
exactly.

The whole rig follows the PELVIS BONE through parent constraints on the zero
groups -- never a controller by name -- so it rides whatever drives the
pelvis (the surviving FK pelvis controller, usually) and merely stops
following, instead of dying, if that driver is torn down.

Converting five baked FK rotations into three controls plus distributed
twist is a projection: the chest and the base are matched exactly, the
middle bones follow the curve. Interior drift is bounded by the mid control
carrying spine_03's animation, and that is the accepted trade of every
hybrid spine.
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om

from maya_overrig import overrig

TOP = "IKSpine_top"
MID = "IKSpine_mid"
BOT = "IKSpine_bot"
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
    up objects' spaces, and equal axes on all three controls keep the mid
    blend interpolation sane.
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


def build_spine(joint_paths):
    """Build the spline-IK spine over the spine bones, root to chest.

    The caller (builder.build) wraps this in the undo chunk and records the
    scene diff as the limb manifest; nothing here needs bookkeeping.
    """
    joints = [cmds.ls(j, long=True)[0] for j in joint_paths]
    start, end = joints[0], joints[-1]
    mid_joint = joints[len(joints) // 2]
    pelvis = (cmds.listRelatives(start, parent=True, fullPath=True)
              or [None])[0]

    range_start = cmds.playbackOptions(query=True, minTime=True)
    cmds.currentTime(range_start)

    p_start = _world_pos(start)
    p_mid = _world_pos(mid_joint)
    p_end = _world_pos(end)
    p_bot = _world_pos(pelvis) if pelvis else p_start

    height = abs(p_end[1] - p_bot[1]) or 1.0
    radius = height * 0.42

    grp = cmds.group(empty=True, name=GROUP)

    bot_zero, bot = _buffered(BOT, p_bot, radius)
    top_zero, top = _buffered(TOP, p_end, radius * 0.9)
    bot_zero, top_zero = cmds.parent(bot_zero, top_zero, grp)

    # The rig rides the pelvis bone; constraints, not parenting, so tearing
    # down whatever drives the pelvis cannot take the spine rig with it.
    if pelvis:
        cmds.parentConstraint(pelvis, bot_zero, maintainOffset=True)
        cmds.parentConstraint(pelvis, top_zero, maintainOffset=True)

    # The middle: a blend group holds it 50/50 between bottom and top; the
    # control's own channels ride on top of that, so it stays animatable.
    blend = cmds.group(empty=True, name=MID + "_blend")
    cmds.xform(blend, worldSpace=True, translation=p_mid)
    blend = cmds.parent(blend, grp)[0]
    cmds.pointConstraint(bot, top, blend, maintainOffset=True)
    orient = cmds.orientConstraint(bot, top, blend, maintainOffset=True)[0]
    cmds.setAttr(orient + ".interpType", 2)  # shortest -- no blend flips
    mid_zero, mid = _buffered(MID, p_mid, radius * 0.75)
    mid_zero = cmds.parent(mid_zero, blend)[0]

    # Capture: the controls take over the bones' current animation. Bottom
    # listens to spine_01 (its lower-spine sway relative to the pelvis lands
    # in the control's own channels), middle to spine_03, top to the chest.
    temps = [
        cmds.parentConstraint(start, bot, maintainOffset=True)[0],
        cmds.parentConstraint(mid_joint, mid, maintainOffset=True)[0],
        cmds.parentConstraint(end, top, maintainOffset=True)[0],
    ]
    overrig.fast_bake([bot, mid, top])
    cmds.delete([t for t in temps if cmds.objExists(t)])

    # The bones' rotation curves would fight the solver through pairBlends;
    # the animation lives on the controls now, and a bake puts it back.
    cmds.currentTime(range_start)
    cmds.cutKey(joints, attribute=("rotateX", "rotateY", "rotateZ"),
                clear=True)

    # Drive: curve -> clusters under the controls -> spline solver.
    curve = cmds.curve(degree=2, point=[p_start, p_mid, p_end],
                       name="IKSpine_curve")
    cmds.setAttr(curve + ".inheritsTransform", 0)
    curve = cmds.parent(curve, grp)[0]
    for index, ctrl in ((0, bot), (1, mid), (2, top)):
        handle = cmds.cluster(curve + ".cv[{0}]".format(index),
                              name="IKSpine_cluster{0}".format(index))[1]
        handle = cmds.parent(handle, ctrl)[0]
        cmds.setAttr(handle + ".visibility", 0)

    ik = cmds.ikHandle(solver="ikSplineSolver", startJoint=start,
                       endEffector=end, curve=curve, createCurve=False,
                       parentCurve=False, rootOnCurve=True,
                       name="IKSpine_handle")[0]
    ik = cmds.parent(ik, grp)[0]
    cmds.setAttr(ik + ".visibility", 0)

    # Advanced twist, start/end -- this is what replaces any aim setup: the
    # roll interpolates between the bottom and top controls' rotations.
    up = _joint_up_vector(mid_joint)
    cmds.setAttr(ik + ".dTwistControlEnable", 1)
    cmds.setAttr(ik + ".dWorldUpType", 4)  # object rotation up (start/end)
    cmds.setAttr(ik + ".dForwardAxis", 0)  # bones aim +X on this skeleton
    cmds.setAttr(ik + ".dWorldUpAxis", 3)  # joint-local +Z is "up"
    cmds.setAttr(ik + ".dWorldUpVector", *up)
    cmds.setAttr(ik + ".dWorldUpVectorEnd", *up)
    cmds.connectAttr(bot + ".worldMatrix[0]", ik + ".dWorldUpMatrix",
                     force=True)
    cmds.connectAttr(top + ".worldMatrix[0]", ik + ".dWorldUpMatrixEnd",
                     force=True)

    # The solver orients the chain, not its last joint: the chest itself
    # belongs to the top control, exactly.
    cmds.orientConstraint(top, end, maintainOffset=True)

    cmds.select(clear=True)
    return grp
