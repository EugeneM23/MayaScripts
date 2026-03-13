"""
Maya Rig Constraint Tool
Applies parentConstraint + scaleConstraint from driver to driven.
Select driver first, then driven (one or more), and click the button.
Run in Maya Script Editor (Python tab).
"""

import maya.cmds as cmds


def apply_parent_scale_constraint(*_args):
    """Apply parentConstraint + scaleConstraint from first selected to the rest."""
    sel = cmds.ls(selection=True)
    if len(sel) < 2:
        cmds.warning("Select driver first, then one or more driven objects.")
        return

    driver = sel[0]
    driven_list = sel[1:]

    for driven in driven_list:
        cmds.parentConstraint(driver, driven, maintainOffset=True)
        cmds.scaleConstraint(driver, driven, maintainOffset=True)

    cmds.select(sel)
    cmds.headsUpMessage("Constrained {} object(s) to {}".format(len(driven_list), driver))


def show_constraint_ui():
    """Open the Rig Constraint Tool window."""
    win_id = "rigConstraintWin"

    if cmds.window(win_id, exists=True):
        cmds.deleteUI(win_id)

    cmds.window(win_id, title="Rig Constraint Tool", widthHeight=(300, 120), sizeable=True)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=6, columnOffset=("both", 10))

    cmds.separator(height=8, style="none")
    cmds.text(label="Select: Driver -> Driven(s)", font="boldLabelFont", align="center")
    cmds.separator(height=4, style="none")

    cmds.button(label="Parent + Scale Constraint", height=36,
                backgroundColor=(0.5, 0.65, 0.85),
                command=apply_parent_scale_constraint)

    cmds.separator(height=4, style="none")
    cmds.text(label="First selected = driver, rest = driven",
              font="smallFixedWidthFont", align="center")

    cmds.showWindow(win_id)


show_constraint_ui()
