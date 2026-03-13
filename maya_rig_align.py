"""
Maya Rig CV Orient Tool
Rotates CVs of a NURBS curve controller to visually match a target's orientation,
without changing the controller's transform values (translate/rotate stay at zero).
Select: controller curve first, then target (joint/object).
Run in Maya Script Editor (Python tab).
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om


def get_world_matrix(obj):
    """Return the world matrix of an object as MMatrix."""
    sel = om.MSelectionList()
    sel.add(obj)
    dag = sel.getDagPath(0)
    return dag.inclusiveMatrix()


def orient_cvs_to_target(*_args):
    """Rotate CVs of the first selected curve to match the second selected object's orientation."""
    sel = cmds.ls(selection=True)
    if len(sel) < 2:
        cmds.warning("Select controller curve, then target object/joint.")
        return

    ctrl = sel[0]
    target = sel[1]

    shapes = cmds.listRelatives(ctrl, shapes=True, type="nurbsCurve") or []
    if not shapes:
        cmds.warning("{} has no NURBS curve shape.".format(ctrl))
        return

    # Get world matrices
    ctrl_matrix = get_world_matrix(ctrl)
    target_matrix = get_world_matrix(target)

    # Rotation difference: from ctrl space to target space
    # offset = ctrl_inverse * target  (in world space)
    offset_matrix = ctrl_matrix.inverse() * target_matrix

    # Extract rotation only (zero out translation, keep scale at 1)
    offset_transform = om.MTransformationMatrix(offset_matrix)
    offset_transform.setTranslation(om.MVector(0, 0, 0), om.MSpace.kTransform)
    offset_transform.setScale([1, 1, 1], om.MSpace.kTransform)
    rot_matrix = offset_transform.asMatrix()

    # Rotate all CVs of all shapes
    for shape in shapes:
        num_cvs = cmds.getAttr("{}.controlPoints".format(shape), size=True)
        for i in range(num_cvs):
            pos = cmds.getAttr("{}.cv[{}]".format(shape, i))[0]
            pt = om.MPoint(pos[0], pos[1], pos[2])
            pt_rotated = pt * rot_matrix
            cmds.setAttr("{}.cv[{}]".format(shape, i),
                         pt_rotated.x, pt_rotated.y, pt_rotated.z, type="double3")

    cmds.select(ctrl)
    cmds.headsUpMessage("Oriented CVs of {} to match {}".format(ctrl, target))


def show_orient_ui():
    """Open the CV Orient Tool window."""
    win_id = "rigCvOrientWin"

    if cmds.window(win_id, exists=True):
        cmds.deleteUI(win_id)

    cmds.window(win_id, title="CV Orient Tool", widthHeight=(320, 120), sizeable=True)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=6, columnOffset=("both", 10))

    cmds.separator(height=8, style="none")
    cmds.text(label="Select: Controller -> Target joint", font="boldLabelFont", align="center")
    cmds.separator(height=4, style="none")

    cmds.button(label="Orient CVs to Target", height=36,
                backgroundColor=(0.6, 0.5, 0.8),
                command=orient_cvs_to_target)

    cmds.separator(height=4, style="none")
    cmds.text(label="Rotates shape CVs only, transform stays clean",
              font="smallFixedWidthFont", align="center")

    cmds.showWindow(win_id)


show_orient_ui()
