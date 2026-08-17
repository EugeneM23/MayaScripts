"""
Maya Rig Group Builder
Scans selected joint hierarchy and creates aligned groups for each named joint.
Groups match joint position and orientation — ready for parenting controllers.
Run in Maya Script Editor (Python tab).
"""

import maya.cmds as cmds


def create_groups_for_joints():
    """Create aligned empty groups mirroring the joint hierarchy."""
    sel = cmds.ls(selection=True, type="joint")
    if not sel:
        cmds.warning("Select a root joint.")
        return []

    root = sel[0]
    all_joints = cmds.listRelatives(root, allDescendents=True, type="joint") or []
    all_joints.append(root)

    # Map: joint -> created group (only for named joints)
    jnt_to_grp = {}

    # First pass: create groups only for named joints
    for jnt in all_joints:
        jnt_name = jnt.split("|")[-1]
        if not jnt_name or jnt_name.startswith("joint"):
            continue

        grp_name = jnt_name.replace("_jnt", "").replace("_JNT", "") + "_grp"
        grp = cmds.group(empty=True, name=grp_name)

        matrix = cmds.xform(jnt, query=True, worldSpace=True, matrix=True)
        cmds.xform(grp, worldSpace=True, matrix=matrix)

        jnt_to_grp[jnt] = grp

    # Second pass: find closest named ancestor for hierarchy
    for jnt, grp in jnt_to_grp.items():
        # Walk up the joint chain until we find a parent that has a group
        parent = cmds.listRelatives(jnt, parent=True, type="joint")
        while parent:
            if parent[0] in jnt_to_grp:
                cmds.parent(grp, jnt_to_grp[parent[0]])
                break
            parent = cmds.listRelatives(parent[0], parent=True, type="joint")

    cmds.select(clear=True)
    cmds.headsUpMessage(f"Created {len(jnt_to_grp)} group(s)")
    return list(jnt_to_grp.values())


def show_groups_ui():
    """Open the Rig Group Builder window."""
    win_id = "rigGrpBuilderWin"

    if cmds.window(win_id, exists=True):
        cmds.deleteUI(win_id)

    cmds.window(win_id, title="Rig Group Builder", widthHeight=(300, 120), sizeable=True)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=6, columnOffset=("both", 10))

    cmds.separator(height=8, style="none")
    cmds.text(label="Select root joint, then click:", font="boldLabelFont", align="center")
    cmds.separator(height=4, style="none")

    cmds.button(label="Create Groups for Joints", height=36,
                backgroundColor=(0.4, 0.7, 0.5), command=lambda *_: create_groups_for_joints())

    cmds.separator(height=4, style="none")
    cmds.text(label="Groups aligned to joints (not parented)",
              font="smallFixedWidthFont", align="center")

    cmds.showWindow(win_id)


show_groups_ui()