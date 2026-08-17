"""
Maya Rig CV Mirror Tool
Mirrors CVs of a NURBS curve controller across a chosen axis,
without changing the controller's transform values.
Run in Maya Script Editor (Python tab).
"""

import maya.cmds as cmds


def mirror_cvs(axis="X", *_args):
    """Mirror CVs of selected curve(s) across the given local axis."""
    sel = cmds.ls(selection=True)
    if not sel:
        cmds.warning("Select at least one controller curve.")
        return

    flip = {"X": (-1, 1, 1), "Y": (1, -1, 1), "Z": (1, 1, -1)}
    mx, my, mz = flip[axis]

    for ctrl in sel:
        shapes = cmds.listRelatives(ctrl, shapes=True, type="nurbsCurve", fullPath=True) or []
        if not shapes:
            cmds.warning("{} has no NURBS curve shape, skipping.".format(ctrl))
            continue
        for shape in shapes:
            cvs = cmds.ls("{}.cv[*]".format(shape), flatten=True) or []
            for cv in cvs:
                pos = cmds.pointPosition(cv, local=True)
                cmds.setAttr(cv, pos[0] * mx, pos[1] * my, pos[2] * mz, type="double3")

    cmds.select(sel)
    cmds.headsUpMessage("Mirrored {} ctrl(s) across {}".format(len(sel), axis))


def show_mirror_ui():
    """Open the CV Mirror Tool window."""
    win_id = "rigCvMirrorWin"

    if cmds.window(win_id, exists=True):
        cmds.deleteUI(win_id)

    cmds.window(win_id, title="CV Mirror Tool", widthHeight=(300, 160), sizeable=True)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=6, columnOffset=("both", 10))

    cmds.separator(height=8, style="none")
    cmds.text(label="Mirror Controller CVs", font="boldLabelFont", align="center")
    cmds.separator(height=8, style="in")

    cmds.button(label="Mirror X", height=32, backgroundColor=(0.85, 0.45, 0.45),
                command=lambda *_: mirror_cvs("X"))
    cmds.button(label="Mirror Y", height=32, backgroundColor=(0.45, 0.75, 0.45),
                command=lambda *_: mirror_cvs("Y"))
    cmds.button(label="Mirror Z", height=32, backgroundColor=(0.45, 0.55, 0.85),
                command=lambda *_: mirror_cvs("Z"))

    cmds.separator(height=4, style="none")
    cmds.text(label="Select ctrl(s), click axis to mirror CVs",
              font="smallFixedWidthFont", align="center")

    cmds.showWindow(win_id)


show_mirror_ui()