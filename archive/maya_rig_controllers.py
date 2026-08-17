"""
Maya Rig Controller Builder
Creates standard NURBS curve controllers for character rigging.
Run in Maya Script Editor (Python tab).
"""

import sys
import math
import functools
import maya.cmds as cmds


def create_circle_ctrl(name="circle_ctrl"):
    """Circle — universal controller (FK joints, head, chest, etc.)."""
    ctrl = cmds.circle(name=name, normal=(0, 1, 0), radius=1, ch=False)[0]
    cmds.select(clear=True)
    return ctrl


def create_square_ctrl(name="square_ctrl"):
    """Square — often used for hips, COG, foot."""
    points = [
        (-1, 0, -1), (-1, 0, 1), (1, 0, 1), (1, 0, -1), (-1, 0, -1)
    ]
    ctrl = cmds.curve(name=name, degree=1, point=points)
    cmds.select(clear=True)
    return ctrl


def create_cube_ctrl(name="cube_ctrl"):
    """Cube (box) — for IK handles, switches, settings."""
    points = [
        (-0.5, 0.5, -0.5), (-0.5, 0.5, 0.5), (0.5, 0.5, 0.5), (0.5, 0.5, -0.5), (-0.5, 0.5, -0.5),
        (-0.5, -0.5, -0.5), (-0.5, -0.5, 0.5), (-0.5, 0.5, 0.5), (-0.5, -0.5, 0.5),
        (0.5, -0.5, 0.5), (0.5, 0.5, 0.5), (0.5, -0.5, 0.5),
        (0.5, -0.5, -0.5), (0.5, 0.5, -0.5), (0.5, -0.5, -0.5),
        (-0.5, -0.5, -0.5)
    ]
    ctrl = cmds.curve(name=name, degree=1, point=points)
    cmds.select(clear=True)
    return ctrl


def create_arrow_ctrl(name="arrow_ctrl"):
    """Arrow — for pole vectors, direction indicators."""
    points = [
        (0, 0, -2), (1, 0, -1), (0.5, 0, -1), (0.5, 0, 1),
        (-0.5, 0, 1), (-0.5, 0, -1), (-1, 0, -1), (0, 0, -2)
    ]
    ctrl = cmds.curve(name=name, degree=1, point=points)
    cmds.select(clear=True)
    return ctrl


def create_cross_ctrl(name="cross_ctrl"):
    """Cross (plus) — for COG, world control, global mover."""
    points = [
        (-0.3, 0, -1), (0.3, 0, -1), (0.3, 0, -0.3), (1, 0, -0.3),
        (1, 0, 0.3), (0.3, 0, 0.3), (0.3, 0, 1), (-0.3, 0, 1),
        (-0.3, 0, 0.3), (-1, 0, 0.3), (-1, 0, -0.3), (-0.3, 0, -0.3),
        (-0.3, 0, -1)
    ]
    ctrl = cmds.curve(name=name, degree=1, point=points)
    cmds.select(clear=True)
    return ctrl


def create_lollipop_ctrl(name="lollipop_ctrl"):
    """Lollipop (stick + circle on top) — for FK fingers, eyes, tweakers."""
    stick = cmds.curve(name=name, degree=1, point=[(0, 0, 0), (0, 2, 0)])
    circle = cmds.circle(name="{}_circle_tmp".format(name), normal=(0, 1, 0), radius=0.4, ch=False)[0]
    circle_shape = cmds.listRelatives(circle, shapes=True)[0]
    cmds.parent(circle_shape, stick, relative=True, shape=True)
    cmds.delete(circle)
    circle_shape = cmds.rename(circle_shape, "{}Shape2".format(name))
    num_cvs = cmds.getAttr("{}.controlPoints".format(circle_shape), size=True)
    cv_list = ["{}.cv[{}]".format(circle_shape, i) for i in range(num_cvs)]
    cmds.move(0, 2, 0, cv_list, relative=True)
    cmds.select(clear=True)
    return stick


def create_gear_ctrl(name="gear_ctrl"):
    """Gear (cog wheel) — for settings, visibility switches, attributes."""
    points = []
    teeth = 8
    outer_r = 1.0
    inner_r = 0.75
    for i in range(teeth):
        a1 = math.radians(i * 360.0 / teeth)
        a2 = math.radians((i + 0.3) * 360.0 / teeth)
        a3 = math.radians((i + 0.5) * 360.0 / teeth)
        a4 = math.radians((i + 0.8) * 360.0 / teeth)
        points.append((math.sin(a1) * inner_r, 0, math.cos(a1) * inner_r))
        points.append((math.sin(a2) * outer_r, 0, math.cos(a2) * outer_r))
        points.append((math.sin(a3) * outer_r, 0, math.cos(a3) * outer_r))
        points.append((math.sin(a4) * inner_r, 0, math.cos(a4) * inner_r))
    points.append(points[0])
    ctrl = cmds.curve(name=name, degree=1, point=points)
    cmds.select(clear=True)
    return ctrl


def apply_color(ctrl, color_index):
    """Override display color on the controller curve."""
    shapes = cmds.listRelatives(ctrl, shapes=True) or []
    for shape in shapes:
        cmds.setAttr("{}.overrideEnabled".format(shape), 1)
        cmds.setAttr("{}.overrideColor".format(shape), color_index)


def scale_ctrl_shape(ctrl, factor):
    """Scale CVs of a curve so the visual size changes but transform.scale stays 1."""
    shapes = cmds.listRelatives(ctrl, shapes=True, type="nurbsCurve") or []
    for shape in shapes:
        num_cvs = cmds.getAttr("{}.controlPoints".format(shape), size=True)
        cv_list = ["{}.cv[{}]".format(shape, i) for i in range(num_cvs)]
        cmds.scale(factor, factor, factor, cv_list, relative=True, objectCenterPivot=True)


# ─── Color constants (Maya color index) ───
COLOR_YELLOW = 17
COLOR_BLUE = 6
COLOR_RED = 13
COLOR_GREEN = 14
COLOR_CYAN = 18
COLOR_PINK = 20
COLOR_WHITE = 16


def _btn_create(create_func, color, *_args):
    """Button callback: create controller and apply color."""
    ctrl = create_func()
    apply_color(ctrl, color)
    cmds.headsUpMessage("Created: {}".format(ctrl))


def _btn_scale(*_args):
    """Button callback: scale CVs of selected controllers."""
    factor = cmds.floatField("rigCtrl_scaleField", query=True, value=True)
    sel = cmds.ls(selection=True)
    if not sel:
        cmds.warning("Select at least one controller curve.")
        return
    for obj in sel:
        shapes = cmds.listRelatives(obj, shapes=True, type="nurbsCurve") or []
        if not shapes:
            cmds.warning("{} is not a NURBS curve, skipping.".format(obj))
            continue
        scale_ctrl_shape(obj, factor)
    cmds.headsUpMessage("Scaled {} controller(s) by {}".format(len(sel), factor))


def show_controller_ui():
    """Open the Rig Controller Builder window."""
    win_id = "rigCtrlBuilderWin"

    if cmds.window(win_id, exists=True):
        cmds.deleteUI(win_id)

    cmds.window(win_id, title="Rig Controller Builder", widthHeight=(300, 500), sizeable=True)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=6, columnOffset=("both", 10))

    cmds.separator(height=8, style="none")
    cmds.text(label="Rig Controllers", font="boldLabelFont", align="center")
    cmds.separator(height=8, style="in")

    buttons = [
        ("Circle  (FK / Universal)",    create_circle_ctrl,   COLOR_YELLOW, (0.9, 0.8, 0.2)),
        ("Square  (Hips / Foot)",       create_square_ctrl,   COLOR_BLUE,   (0.3, 0.5, 0.8)),
        ("Cube  (IK / Settings)",       create_cube_ctrl,     COLOR_RED,    (0.8, 0.3, 0.3)),
        ("Arrow  (Pole Vector)",        create_arrow_ctrl,    COLOR_GREEN,  (0.3, 0.75, 0.3)),
        ("Cross  (COG / Global)",       create_cross_ctrl,    COLOR_CYAN,   (0.3, 0.75, 0.8)),
        ("Lollipop  (FK Finger / Eye)", create_lollipop_ctrl, COLOR_PINK,   (0.85, 0.45, 0.6)),
        ("Gear  (Settings / Visibility)", create_gear_ctrl,   COLOR_WHITE,  (0.7, 0.7, 0.7)),
    ]

    # Store callbacks on the module to prevent garbage collection
    _callbacks = []
    for label, func, color, bg in buttons:
        cb = functools.partial(_btn_create, func, color)
        _callbacks.append(cb)
        cmds.button(label=label, height=32, backgroundColor=bg, command=cb)

    # Keep references alive by attaching to module
    sys.modules[__name__]._ui_callbacks = _callbacks

    cmds.separator(height=12, style="in")
    cmds.text(label="Scale Controller Shape", font="boldLabelFont", align="center")
    cmds.separator(height=4, style="none")

    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1, columnWidth2=(180, 80))
    cmds.floatField("rigCtrl_scaleField", value=1.5, minValue=0.01, maxValue=100.0, precision=2)
    cmds.button(label="Scale CVs", height=26, command=_btn_scale)
    cmds.setParent("..")

    cmds.separator(height=4, style="none")
    cmds.text(label="Select ctrl(s), set multiplier, click Scale CVs",
              font="smallFixedWidthFont", align="center")

    cmds.showWindow(win_id)


show_controller_ui()