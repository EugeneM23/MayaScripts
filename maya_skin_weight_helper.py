"""
Maya Skin Weight Helper
Select a joint hierarchy, load it into the UI, then assign weights
to selected vertices per-joint.
Run in Maya Script Editor (Python tab).
"""

import maya.cmds as cmds


# ---------------------------------------------------------------------------
#  State
# ---------------------------------------------------------------------------

_joint_rows = []  # list of (joint_name, weight_field_name)
_skin_cluster_cache = None


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _get_joint_hierarchy():
    """Return all joints in the hierarchy of the selected joint(s)."""
    sel = cmds.ls(selection=True, type="joint")
    if not sel:
        cmds.warning("Select at least one joint.")
        return []

    root = sel[0]
    # Walk up to find the root of the chain
    while True:
        parent = cmds.listRelatives(root, parent=True, type="joint")
        if not parent:
            break
        root = parent[0]

    descendants = cmds.listRelatives(root, allDescendents=True,
                                      type="joint", fullPath=False) or []
    # listRelatives returns bottom-up, reverse for top-down order
    all_joints = [root] + list(reversed(descendants))
    return all_joints


def _find_skin_cluster(mesh):
    """Find the skinCluster deformer on a mesh."""
    if not mesh:
        return None
    history = cmds.listHistory(mesh, pruneDagObjects=True) or []
    for node in history:
        if cmds.nodeType(node) == "skinCluster":
            return node
    return None


def _get_mesh_from_selection():
    """Get the mesh transform from current vertex/face selection."""
    sel = cmds.ls(selection=True, flatten=True)
    if not sel:
        return None
    # Get the transform from component selection
    obj = sel[0].split(".")[0]
    shapes = cmds.listRelatives(obj, shapes=True, type="mesh") or []
    if shapes:
        return obj
    return None


# ---------------------------------------------------------------------------
#  Commands
# ---------------------------------------------------------------------------

def load_hierarchy(*_args):
    """Load selected joint hierarchy into the scroll list."""
    global _joint_rows

    joints = _get_joint_hierarchy()
    if not joints:
        return

    _joint_rows = []

    # Clear the scroll layout
    children = cmds.columnLayout("jointListColumn", query=True,
                                  childArray=True) or []
    for child in children:
        cmds.deleteUI(child)

    for jnt in joints:
        short_name = jnt.split("|")[-1]
        field_name = "wf_{}".format(short_name.replace(":", "_"))

        cmds.rowLayout(numberOfColumns=3,
                       columnWidth3=(180, 60, 70),
                       parent="jointListColumn")
        cmds.text(label=" " + short_name, align="left",
                  font="fixedWidthFont")
        cmds.floatField(field_name, value=1.0, minValue=0.0,
                        maxValue=1.0, precision=3, width=55)
        cmds.button(label="Assign",
                    height=22,
                    backgroundColor=(0.45, 0.75, 0.45),
                    command=lambda *_a, j=jnt, f=field_name: assign_weight(j, f))
        cmds.setParent("..")

        _joint_rows.append((jnt, field_name))

    cmds.headsUpMessage("{} joints loaded".format(len(joints)))


def polys_to_verts(*_args):
    """Convert selected polygons to vertex selection."""
    sel = cmds.ls(selection=True, flatten=True)
    if not sel:
        cmds.warning("Nothing selected.")
        return

    # Check if faces are selected
    faces = cmds.filterExpand(sel, selectionMask=34) or []  # 34 = polygon faces
    if not faces:
        cmds.warning("No polygon faces in selection. Select faces first.")
        return

    cmds.select(faces)
    cmds.ConvertSelectionToVertices()
    vert_count = len(cmds.ls(selection=True, flatten=True))
    cmds.headsUpMessage("{} vertices selected".format(vert_count))


def assign_weight(joint, field_name, *_args):
    """Assign the specified weight to selected vertices for the given joint."""
    weight = cmds.floatField(field_name, query=True, value=True)

    sel = cmds.ls(selection=True, flatten=True)
    if not sel:
        cmds.warning("No vertices selected.")
        return

    verts = cmds.filterExpand(sel, selectionMask=31) or []  # 31 = vertices
    if not verts:
        cmds.warning("Selection does not contain vertices.")
        return

    mesh = _get_mesh_from_selection()
    if not mesh:
        cmds.warning("Cannot determine mesh from selection.")
        return

    skin = _find_skin_cluster(mesh)
    if not skin:
        cmds.warning("No skinCluster found on {}.".format(mesh))
        return

    # Check that the joint is an influence in the skinCluster
    influences = cmds.skinCluster(skin, query=True, influence=True) or []
    joint_short = joint.split("|")[-1]
    if joint_short not in influences and joint not in influences:
        cmds.warning("{} is not an influence in {}.".format(joint_short, skin))
        return

    # Assign weight using transformValue
    tv_list = [(joint, weight)]
    cmds.skinPercent(skin, verts, transformValue=tv_list)

    cmds.headsUpMessage("Weight {:.3f} assigned to {} ({} verts)".format(
        weight, joint_short, len(verts)))


def assign_all_weights(*_args):
    """Assign weights from ALL rows at once to selected vertices."""
    sel = cmds.ls(selection=True, flatten=True)
    if not sel:
        cmds.warning("No vertices selected.")
        return

    verts = cmds.filterExpand(sel, selectionMask=31) or []
    if not verts:
        cmds.warning("Selection does not contain vertices.")
        return

    mesh = _get_mesh_from_selection()
    if not mesh:
        cmds.warning("Cannot determine mesh from selection.")
        return

    skin = _find_skin_cluster(mesh)
    if not skin:
        cmds.warning("No skinCluster found on {}.".format(mesh))
        return

    tv_list = []
    for jnt, field_name in _joint_rows:
        if not cmds.floatField(field_name, exists=True):
            continue
        w = cmds.floatField(field_name, query=True, value=True)
        if w > 0.0:
            tv_list.append((jnt, w))

    if not tv_list:
        cmds.warning("All weights are zero.")
        return

    cmds.skinPercent(skin, verts, transformValue=tv_list)
    cmds.headsUpMessage("Weights assigned to {} verts".format(len(verts)))


# ---------------------------------------------------------------------------
#  UI
# ---------------------------------------------------------------------------

def show_skin_weight_helper():
    win_id = "skinWeightHelperWin"

    if cmds.window(win_id, exists=True):
        cmds.deleteUI(win_id)

    cmds.window(win_id, title="Skin Weight Helper",
                widthHeight=(340, 500), sizeable=True)

    main_col = cmds.columnLayout(adjustableColumn=True, rowSpacing=4,
                                  columnOffset=("both", 6))

    cmds.separator(height=6, style="none")
    cmds.text(label="Skin Weight Helper", font="boldLabelFont",
              align="center")
    cmds.separator(height=6, style="in")

    # --- Load hierarchy ---
    cmds.button(label="Load Joint Hierarchy",
                height=30,
                backgroundColor=(0.45, 0.55, 0.85),
                annotation="Select any joint, click to load full hierarchy",
                command=load_hierarchy)

    cmds.separator(height=4, style="none")

    # --- Scroll area for joints ---
    cmds.scrollLayout("jointScrollLayout", height=300,
                       childResizable=True)
    cmds.columnLayout("jointListColumn", adjustableColumn=True,
                       rowSpacing=2)
    cmds.text(label="  Select a joint and click 'Load Joint Hierarchy'",
              font="obliqueLabelFont", align="left")
    cmds.setParent("..")  # jointListColumn
    cmds.setParent("..")  # scrollLayout

    cmds.separator(height=6, style="in")

    # --- Polygon to Vertices ---
    cmds.button(label="Polygons -> Vertices",
                height=28,
                backgroundColor=(0.75, 0.55, 0.35),
                annotation="Convert selected faces to vertex selection",
                command=polys_to_verts)

    cmds.separator(height=4, style="none")

    # --- Assign all ---
    cmds.button(label="Assign All Weights",
                height=28,
                backgroundColor=(0.45, 0.75, 0.45),
                annotation="Assign weights from all rows to selected vertices",
                command=assign_all_weights)

    cmds.separator(height=6, style="none")
    cmds.text(label="1. Select joint -> Load Hierarchy",
              font="smallFixedWidthFont", align="left")
    cmds.text(label="2. Select polys -> Polygons->Vertices",
              font="smallFixedWidthFont", align="left")
    cmds.text(label="3. Set weight -> Assign per joint",
              font="smallFixedWidthFont", align="left")

    cmds.showWindow(win_id)


show_skin_weight_helper()
