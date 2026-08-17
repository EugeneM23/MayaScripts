"""
Maya Controller Shape Orient Tool
Two separate modes:
  1. Shape Mode — rotate CVs of a NURBS controller
  2. Axes Mode — rotate the local rotation axes (rotateAxis)
Run in Maya Script Editor (Python tab).
"""

import maya.cmds as cmds
import math
import maya.api.OpenMaya as om2


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _get_cvs(ctrl):
    shapes = cmds.listRelatives(ctrl, shapes=True, type="nurbsCurve",
                                fullPath=True) or []
    all_cvs = []
    for shape in shapes:
        cvs = cmds.ls("{}.cv[*]".format(shape), flatten=True) or []
        all_cvs.extend(cvs)
    return all_cvs


def _get_ctrl():
    sel = cmds.ls(selection=True)
    if not sel:
        cmds.warning("Select a controller curve.")
        return None
    return sel[0]


def _find_outgoing_constraints(ctrl):
    """Find all constraints that this controller drives (directly or via children)."""
    constraint_types = [
        "parentConstraint", "orientConstraint", "pointConstraint",
        "aimConstraint", "scaleConstraint",
    ]
    found = []

    destinations = cmds.listConnections(ctrl, source=False, destination=True,
                                         type="constraint") or []
    children = cmds.listRelatives(ctrl, allDescendents=True, fullPath=True) or []
    for child in children:
        child_dests = cmds.listConnections(child, source=False, destination=True,
                                            type="constraint") or []
        destinations.extend(child_dests)

    seen = set()
    for node in destinations:
        if node in seen:
            continue
        seen.add(node)
        node_type = cmds.nodeType(node)
        if node_type in constraint_types:
            found.append(node)

    return found


def _record_bone_transforms(constraints):
    """Record world matrices of all bones driven by given constraints."""
    bone_data = {}
    for con in constraints:
        parents = cmds.listRelatives(con, parent=True, fullPath=True)
        if parents:
            bone = parents[0]
            if bone not in bone_data:
                bone_data[bone] = cmds.xform(bone, q=True, ws=True, matrix=True)
    return bone_data


def _fix_drifted_bone(bone, desired_matrix):
    """Fix a bone that drifted by recreating its constraints with maintainOffset."""
    children = cmds.listRelatives(bone, children=True, fullPath=True) or []
    for child in children:
        ntype = cmds.nodeType(child)
        short_name = child.split("|")[-1]

        if ntype == "parentConstraint":
            targets = cmds.parentConstraint(short_name, q=True, targetList=True)
            wal = cmds.parentConstraint(short_name, q=True,
                                         weightAliasList=True) or []
            weights = [cmds.getAttr("{}.{}".format(short_name, wa)) for wa in wal]
            cmds.delete(child)
            cmds.xform(bone, ws=True, matrix=desired_matrix)
            new_con = cmds.parentConstraint(targets, bone, maintainOffset=True)[0]
            new_wal = cmds.parentConstraint(new_con, q=True,
                                             weightAliasList=True) or []
            for wa, w in zip(new_wal, weights):
                cmds.setAttr("{}.{}".format(new_con, wa), w)

        elif ntype == "orientConstraint":
            targets = cmds.orientConstraint(short_name, q=True, targetList=True)
            wal = cmds.orientConstraint(short_name, q=True,
                                         weightAliasList=True) or []
            weights = [cmds.getAttr("{}.{}".format(short_name, wa)) for wa in wal]
            cmds.delete(child)
            cmds.xform(bone, ws=True, matrix=desired_matrix)
            new_con = cmds.orientConstraint(targets, bone, maintainOffset=True)[0]
            new_wal = cmds.orientConstraint(new_con, q=True,
                                             weightAliasList=True) or []
            for wa, w in zip(new_wal, weights):
                cmds.setAttr("{}.{}".format(new_con, wa), w)

        elif ntype == "pointConstraint":
            targets = cmds.pointConstraint(short_name, q=True, targetList=True)
            wal = cmds.pointConstraint(short_name, q=True,
                                        weightAliasList=True) or []
            weights = [cmds.getAttr("{}.{}".format(short_name, wa)) for wa in wal]
            cmds.delete(child)
            cmds.xform(bone, ws=True, matrix=desired_matrix)
            new_con = cmds.pointConstraint(targets, bone, maintainOffset=True)[0]
            new_wal = cmds.pointConstraint(new_con, q=True,
                                            weightAliasList=True) or []
            for wa, w in zip(new_wal, weights):
                cmds.setAttr("{}.{}".format(new_con, wa), w)


def _compose_rotate_axis(ctrl, dx, dy, dz):
    """Compose rotation delta into rotateAxis via quaternions.
    Uses MDGModifier for atomic update. Records and restores bone transforms."""

    # 1. Find constrained bones and record world transforms
    constraints = _find_outgoing_constraints(ctrl)
    bone_data = _record_bone_transforms(constraints)

    # 2. Compute new rotateAxis and compensated rotate
    rot = cmds.getAttr(ctrl + ".rotate")[0]
    ra = cmds.getAttr(ctrl + ".rotateAxis")[0]
    ro = cmds.getAttr(ctrl + ".rotateOrder")

    ra_q = om2.MEulerRotation(math.radians(ra[0]), math.radians(ra[1]),
                               math.radians(ra[2])).asQuaternion()
    rot_q = om2.MEulerRotation(math.radians(rot[0]), math.radians(rot[1]),
                                math.radians(rot[2]), ro).asQuaternion()
    delta_q = om2.MEulerRotation(math.radians(dx), math.radians(dy),
                                  math.radians(dz)).asQuaternion()

    # New rotateAxis = delta * old
    ra_new_q = delta_q * ra_q
    # Compensate: R_new * RA_new = R_old * RA_old
    rot_new_q = rot_q * ra_q * ra_new_q.inverse()

    ra_new = ra_new_q.asEulerRotation()
    rot_new = rot_new_q.asEulerRotation().reorder(ro)

    # 3. Apply BOTH values atomically via MDGModifier (no intermediate DG eval)
    sel_list = om2.MSelectionList()
    sel_list.add(ctrl)
    mobj = sel_list.getDependNode(0)
    fn = om2.MFnDependencyNode(mobj)

    ra_plug = fn.findPlug("rotateAxis", True)
    rot_plug = fn.findPlug("rotate", True)

    mod = om2.MDGModifier()
    mod.newPlugValueDouble(ra_plug.child(0), ra_new.x)
    mod.newPlugValueDouble(ra_plug.child(1), ra_new.y)
    mod.newPlugValueDouble(ra_plug.child(2), ra_new.z)
    mod.newPlugValueDouble(rot_plug.child(0), rot_new.x)
    mod.newPlugValueDouble(rot_plug.child(1), rot_new.y)
    mod.newPlugValueDouble(rot_plug.child(2), rot_new.z)
    mod.doIt()

    # 4. Check if any bones drifted, fix by recreating constraints
    for bone, old_mat in bone_data.items():
        cur_mat = cmds.xform(bone, q=True, ws=True, matrix=True)
        drift = max(abs(cur_mat[i] - old_mat[i]) for i in range(16))
        if drift > 0.001:
            _fix_drifted_bone(bone, old_mat)


# ---------------------------------------------------------------------------
#  SHAPE MODE — rotate CVs only
# ---------------------------------------------------------------------------

def shape_select_cvs(*_args):
    """Select CVs for free interactive rotation."""
    ctrl = _get_ctrl()
    if not ctrl:
        return
    cvs = _get_cvs(ctrl)
    if not cvs:
        cmds.warning("{} has no NURBS curve shape.".format(ctrl))
        return
    cmds.select(cvs)
    pivot = cmds.xform(ctrl, query=True, worldSpace=True, rotatePivot=True)
    cmds.manipPivot(p=(pivot[0], pivot[1], pivot[2]))
    cmds.setToolTo("RotateSuperContext")
    cmds.headsUpMessage("Rotate shape CVs, press Done when finished")


def shape_done(*_args):
    """Reselect controller after CV editing."""
    cmds.manipPivot(reset=True)
    # Try to find parent controller from selected CVs
    sel = cmds.ls(selection=True)
    if sel:
        parent = cmds.listRelatives(sel[0], parent=True)
        if parent:
            top = cmds.listRelatives(parent[0], parent=True)
            if top:
                cmds.select(top[0])
                return
    cmds.headsUpMessage("Done")


def shape_numeric(*_args):
    """Rotate CVs by numeric XYZ values."""
    ctrl = _get_ctrl()
    if not ctrl:
        return
    cvs = _get_cvs(ctrl)
    if not cvs:
        cmds.warning("{} has no NURBS curve shape.".format(ctrl))
        return

    rx = cmds.floatFieldGrp("shapeNumericXYZ", query=True, value1=True)
    ry = cmds.floatFieldGrp("shapeNumericXYZ", query=True, value2=True)
    rz = cmds.floatFieldGrp("shapeNumericXYZ", query=True, value3=True)

    if abs(rx) < 0.0001 and abs(ry) < 0.0001 and abs(rz) < 0.0001:
        cmds.warning("Enter rotation values.")
        return

    pivot = cmds.xform(ctrl, query=True, objectSpace=True, rotatePivot=True)
    cmds.rotate(rx, ry, rz, cvs,
                pivot=(pivot[0], pivot[1], pivot[2]),
                relative=True, objectSpace=True)
    cmds.select(ctrl)
    cmds.headsUpMessage("Shape rotated ({}, {}, {})".format(rx, ry, rz))


def shape_quick(axis, angle, *_args):
    """Quick 90-degree shape rotation."""
    ctrl = _get_ctrl()
    if not ctrl:
        return
    cvs = _get_cvs(ctrl)
    if not cvs:
        return
    rx = angle if axis == "X" else 0
    ry = angle if axis == "Y" else 0
    rz = angle if axis == "Z" else 0
    pivot = cmds.xform(ctrl, query=True, objectSpace=True, rotatePivot=True)
    cmds.rotate(rx, ry, rz, cvs,
                pivot=(pivot[0], pivot[1], pivot[2]),
                relative=True, objectSpace=True)
    cmds.select(ctrl)


# ---------------------------------------------------------------------------
#  AXES MODE — rotate rotateAxis only
# ---------------------------------------------------------------------------

_axes_locator = None
_axes_ctrl = None


def axes_start(*_args):
    """Create a temp locator to preview axis rotation without moving the rig."""
    global _axes_locator, _axes_ctrl
    ctrl = _get_ctrl()
    if not ctrl:
        return

    # Clean up old locator if exists
    if _axes_locator and cmds.objExists(_axes_locator):
        cmds.delete(_axes_locator)

    _axes_ctrl = ctrl

    # Create locator at controller position/orientation
    loc = cmds.spaceLocator(name="axes_orient_helper")[0]
    _axes_locator = loc

    # Match position
    pos = cmds.xform(ctrl, query=True, worldSpace=True, translation=True)
    rot = cmds.xform(ctrl, query=True, worldSpace=True, rotation=True)
    cmds.xform(loc, worldSpace=True, translation=pos)
    cmds.xform(loc, worldSpace=True, rotation=rot)

    # Make it visible
    cmds.setAttr(loc + ".localScaleX", 3)
    cmds.setAttr(loc + ".localScaleY", 3)
    cmds.setAttr(loc + ".localScaleZ", 3)

    cmds.select(loc)
    cmds.setToolTo("RotateSuperContext")
    cmds.headsUpMessage("Rotate the locator to set axes, then click Apply")


def axes_apply(*_args):
    """Apply locator rotation delta to rotateAxis, delete locator."""
    global _axes_locator, _axes_ctrl

    if not _axes_locator or not cmds.objExists(_axes_locator):
        cmds.warning("Click 'Start Axes' first.")
        return
    if not _axes_ctrl or not cmds.objExists(_axes_ctrl):
        cmds.warning("Original controller not found.")
        if _axes_locator and cmds.objExists(_axes_locator):
            cmds.delete(_axes_locator)
        _axes_locator = None
        _axes_ctrl = None
        return

    ctrl = _axes_ctrl

    # Get controller world rotation
    ctrl_rot = cmds.xform(ctrl, query=True, worldSpace=True, rotation=True)
    # Get locator world rotation
    loc_rot = cmds.xform(_axes_locator, query=True, worldSpace=True, rotation=True)

    # Compute delta via quaternions
    ctrl_euler = om2.MEulerRotation(math.radians(ctrl_rot[0]),
                                     math.radians(ctrl_rot[1]),
                                     math.radians(ctrl_rot[2]))
    loc_euler = om2.MEulerRotation(math.radians(loc_rot[0]),
                                    math.radians(loc_rot[1]),
                                    math.radians(loc_rot[2]))

    # delta = loc * ctrl_inverse
    ctrl_quat = ctrl_euler.asQuaternion()
    loc_quat = loc_euler.asQuaternion()
    delta_quat = loc_quat * ctrl_quat.inverse()
    delta_euler = delta_quat.asEulerRotation()

    dx = math.degrees(delta_euler.x)
    dy = math.degrees(delta_euler.y)
    dz = math.degrees(delta_euler.z)

    if abs(dx) > 0.001 or abs(dy) > 0.001 or abs(dz) > 0.001:
        _compose_rotate_axis(ctrl, dx, dy, dz)

    # Cleanup
    cmds.delete(_axes_locator)
    _axes_locator = None
    _axes_ctrl = None

    cmds.select(ctrl)
    cmds.headsUpMessage("Axes updated for {}".format(ctrl))


def axes_cancel(*_args):
    """Cancel axes adjustment, delete locator."""
    global _axes_locator, _axes_ctrl
    if _axes_locator and cmds.objExists(_axes_locator):
        cmds.delete(_axes_locator)
    ctrl = _axes_ctrl
    _axes_locator = None
    _axes_ctrl = None
    if ctrl and cmds.objExists(ctrl):
        cmds.select(ctrl)
    cmds.headsUpMessage("Axes adjustment cancelled")


def axes_numeric(*_args):
    """Rotate axes by numeric XYZ values."""
    ctrl = _get_ctrl()
    if not ctrl:
        return

    rx = cmds.floatFieldGrp("axesNumericXYZ", query=True, value1=True)
    ry = cmds.floatFieldGrp("axesNumericXYZ", query=True, value2=True)
    rz = cmds.floatFieldGrp("axesNumericXYZ", query=True, value3=True)

    if abs(rx) < 0.0001 and abs(ry) < 0.0001 and abs(rz) < 0.0001:
        cmds.warning("Enter rotation values.")
        return

    _compose_rotate_axis(ctrl, rx, ry, rz)
    cmds.select(ctrl)
    cmds.headsUpMessage("Axes rotated ({}, {}, {})".format(rx, ry, rz))


def axes_quick(axis, angle, *_args):
    """Quick 90-degree axes rotation."""
    ctrl = _get_ctrl()
    if not ctrl:
        return
    rx = angle if axis == "X" else 0
    ry = angle if axis == "Y" else 0
    rz = angle if axis == "Z" else 0
    _compose_rotate_axis(ctrl, rx, ry, rz)
    cmds.select(ctrl)


def axes_reset(*_args):
    """Reset rotateAxis to 0,0,0."""
    ctrl = _get_ctrl()
    if not ctrl:
        return
    cmds.setAttr(ctrl + ".rotateAxis", 0, 0, 0, type="double3")
    cmds.select(ctrl)
    cmds.headsUpMessage("Axes reset to (0, 0, 0)")


# ---------------------------------------------------------------------------
#  UI
# ---------------------------------------------------------------------------

def show_shape_orient_ui():
    win_id = "ctrlShapeOrientWin"

    if cmds.window(win_id, exists=True):
        cmds.deleteUI(win_id)

    cmds.window(win_id, title="Shape & Axes Orient",
                widthHeight=(330, 500), sizeable=True)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=4,
                      columnOffset=("both", 10))

    cmds.separator(height=8, style="none")
    cmds.text(label="Controller Orient Tool", font="boldLabelFont",
              align="center")

    # ==== SHAPE MODE ====
    cmds.separator(height=8, style="in")
    cmds.text(label="SHAPE (CVs)", font="boldLabelFont", align="center",
              backgroundColor=(0.28, 0.28, 0.35))
    cmds.separator(height=4, style="none")

    # Interactive
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(155, 155))
    cmds.button(label="Select CVs & Rotate", height=28,
                backgroundColor=(0.45, 0.75, 0.45),
                command=shape_select_cvs)
    cmds.button(label="Done", height=28,
                backgroundColor=(0.45, 0.55, 0.85),
                command=shape_done)
    cmds.setParent("..")

    # Numeric
    cmds.floatFieldGrp("shapeNumericXYZ", numberOfFields=3,
                       label="X  Y  Z  ",
                       value1=0, value2=0, value3=0,
                       columnWidth4=(60, 70, 70, 70))
    cmds.button(label="Rotate Shape", height=26,
                backgroundColor=(0.65, 0.55, 0.85),
                command=shape_numeric)

    # Quick 90
    cmds.text(label="Quick 90", font="smallBoldLabelFont", align="left")
    cmds.rowLayout(numberOfColumns=6, columnWidth6=(50, 50, 50, 50, 50, 50))
    cmds.button(label="X+", height=24, backgroundColor=(0.85, 0.5, 0.5),
                command=lambda *_: shape_quick("X", 90))
    cmds.button(label="X-", height=24, backgroundColor=(0.7, 0.4, 0.4),
                command=lambda *_: shape_quick("X", -90))
    cmds.button(label="Y+", height=24, backgroundColor=(0.5, 0.75, 0.5),
                command=lambda *_: shape_quick("Y", 90))
    cmds.button(label="Y-", height=24, backgroundColor=(0.4, 0.6, 0.4),
                command=lambda *_: shape_quick("Y", -90))
    cmds.button(label="Z+", height=24, backgroundColor=(0.5, 0.55, 0.85),
                command=lambda *_: shape_quick("Z", 90))
    cmds.button(label="Z-", height=24, backgroundColor=(0.4, 0.45, 0.7),
                command=lambda *_: shape_quick("Z", -90))
    cmds.setParent("..")

    # ==== AXES MODE ====
    cmds.separator(height=8, style="in")
    cmds.text(label="AXES (rotateAxis)", font="boldLabelFont", align="center",
              backgroundColor=(0.35, 0.28, 0.28))
    cmds.separator(height=4, style="none")

    # Interactive
    cmds.rowLayout(numberOfColumns=3, columnWidth3=(103, 103, 103))
    cmds.button(label="Start Axes", height=28,
                backgroundColor=(0.75, 0.55, 0.35),
                command=axes_start)
    cmds.button(label="Apply", height=28,
                backgroundColor=(0.45, 0.75, 0.45),
                command=axes_apply)
    cmds.button(label="Cancel", height=28,
                backgroundColor=(0.7, 0.4, 0.4),
                command=axes_cancel)
    cmds.setParent("..")

    cmds.separator(height=4, style="none")

    # Numeric
    cmds.floatFieldGrp("axesNumericXYZ", numberOfFields=3,
                       label="X  Y  Z  ",
                       value1=0, value2=0, value3=0,
                       columnWidth4=(60, 70, 70, 70))
    cmds.button(label="Rotate Axes", height=26,
                backgroundColor=(0.85, 0.65, 0.45),
                command=axes_numeric)

    # Quick 90
    cmds.text(label="Quick 90", font="smallBoldLabelFont", align="left")
    cmds.rowLayout(numberOfColumns=6, columnWidth6=(50, 50, 50, 50, 50, 50))
    cmds.button(label="X+", height=24, backgroundColor=(0.85, 0.6, 0.5),
                command=lambda *_: axes_quick("X", 90))
    cmds.button(label="X-", height=24, backgroundColor=(0.7, 0.5, 0.4),
                command=lambda *_: axes_quick("X", -90))
    cmds.button(label="Y+", height=24, backgroundColor=(0.6, 0.75, 0.5),
                command=lambda *_: axes_quick("Y", 90))
    cmds.button(label="Y-", height=24, backgroundColor=(0.5, 0.6, 0.4),
                command=lambda *_: axes_quick("Y", -90))
    cmds.button(label="Z+", height=24, backgroundColor=(0.5, 0.6, 0.75),
                command=lambda *_: axes_quick("Z", 90))
    cmds.button(label="Z-", height=24, backgroundColor=(0.4, 0.5, 0.6),
                command=lambda *_: axes_quick("Z", -90))
    cmds.setParent("..")

    cmds.separator(height=4, style="none")
    cmds.button(label="Reset Axes to 0", height=24,
                backgroundColor=(0.6, 0.4, 0.4),
                command=axes_reset)

    cmds.separator(height=4, style="none")
    cmds.text(label="Select controller, use Shape or Axes",
              font="smallFixedWidthFont", align="center")

    cmds.showWindow(win_id)


show_shape_orient_ui()