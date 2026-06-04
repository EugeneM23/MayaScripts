"""
Maya Center of Mass Tool
Creates a CoM marker based on assigned rig controllers and body part weights.
Includes a floor projection (support axis) indicator.
Run in Maya Script Editor (Python tab).
"""
import maya.cmds as cmds
import maya.api.OpenMaya as om

WINDOW_NAME = "centerOfMassTool"
COM_LOCATOR  = "COM_Marker"
AXIS_CURVE   = "COM_SupportAxis"
SCRIPT_JOB_ATTR = "COM_Marker.scriptJobId"

# Body segments with default biomechanical mass percentages (De Leva, 1996)
BODY_SEGMENTS = [
    ("Head",         8.1),
    ("Chest",       20.1),
    ("Mid Trunk",   14.9),
    ("Pelvis",      14.2),
    ("Upper Arm L",  2.55),
    ("Upper Arm R",  2.55),
    ("Forearm L",    1.38),
    ("Forearm R",    1.38),
    ("Hand L",       0.56),
    ("Hand R",       0.56),
    ("Thigh L",     10.0),
    ("Thigh R",     10.0),
    ("Lower Leg L",  4.65),
    ("Lower Leg R",  4.65),
    ("Foot L",       1.45),
    ("Foot R",       1.45),
]

# Store controller assignments: {segment_name: controller_name}
_assignments = {}


# -------------------------
# MATH
# -------------------------

def get_world_position(node):
    """Get world-space position of a node."""
    pos = cmds.xform(node, query=True, worldSpace=True, translation=True)
    return om.MVector(pos[0], pos[1], pos[2])


def compute_com():
    """Compute center of mass from assigned controllers and their weights."""
    total_weight = 0.0
    weighted_pos = om.MVector(0, 0, 0)

    for seg, default_weight in BODY_SEGMENTS:
        ctrl = _assignments.get(seg)
        if not ctrl or not cmds.objExists(ctrl):
            continue

        # Read weight from UI field (user may have tweaked it)
        field_name = "comWeight_{}".format(seg.replace(" ", "_"))
        try:
            weight = cmds.floatField(field_name, query=True, value=True)
        except Exception:
            weight = default_weight

        pos = get_world_position(ctrl)
        weighted_pos += pos * weight
        total_weight  += weight

    if total_weight < 0.001:
        return None, 0.0

    return weighted_pos / total_weight, total_weight


def get_foot_bounds():
    """Return XZ bounding box of assigned feet for stability check."""
    foot_names = ["Foot L", "Foot R"]
    positions = []
    for seg in foot_names:
        ctrl = _assignments.get(seg)
        if ctrl and cmds.objExists(ctrl):
            pos = get_world_position(ctrl)
            positions.append(pos)
    return positions


def is_com_stable(com_pos, margin=20.0):
    """
    Simple stability: CoM XZ within margin of feet midpoint.
    Returns True if balanced.
    """
    feet = get_foot_bounds()
    if not feet:
        return True  # can't determine

    mid_x = sum(p.x for p in feet) / len(feet)
    mid_z = sum(p.z for p in feet) / len(feet)
    dist = ((com_pos.x - mid_x) ** 2 + (com_pos.z - mid_z) ** 2) ** 0.5
    return dist < margin


# -------------------------
# SCENE OBJECTS
# -------------------------

def create_com_marker():
    """Create or get the CoM locator."""
    if cmds.objExists(COM_LOCATOR):
        return COM_LOCATOR

    loc = cmds.spaceLocator(name=COM_LOCATOR)[0]

    # Scale locator shape for visibility
    cmds.setAttr("{}.localScaleX".format(loc), 10)
    cmds.setAttr("{}.localScaleY".format(loc), 10)
    cmds.setAttr("{}.localScaleZ".format(loc), 10)

    # Yellow color
    cmds.setAttr("{}.overrideEnabled".format(loc), 1)
    cmds.setAttr("{}.overrideColor".format(loc), 17)  # yellow

    # Lock & hide rotate/scale so it's clear this is read-only
    for attr in ["rx", "ry", "rz", "sx", "sy", "sz"]:
        cmds.setAttr("{}.{}".format(loc, attr), lock=True, keyable=False)

    cmds.addAttr(loc, longName="scriptJobId", attributeType="long", defaultValue=-1)

    return loc


def create_support_axis():
    """Create or get the vertical support axis curve (CoM to floor)."""
    if cmds.objExists(AXIS_CURVE):
        return AXIS_CURVE

    curve = cmds.curve(
        name=AXIS_CURVE,
        degree=1,
        point=[(0, 0, 0), (0, 0, 0)]
    )

    # Cyan color
    cmds.setAttr("{}.overrideEnabled".format(curve), 1)
    cmds.setAttr("{}.overrideColor".format(curve), 18)  # cyan

    # Not selectable in viewport — just visual
    cmds.setAttr("{}.template".format(curve), 1)

    return curve


def update_support_axis(com_pos, stable):
    """Update the support axis curve from CoM straight down to floor (Y=0)."""
    if not cmds.objExists(AXIS_CURVE):
        return

    # Update curve CVs
    cmds.move(com_pos.x, com_pos.y, com_pos.z,
              "{}.cv[0]".format(AXIS_CURVE), absolute=True, worldSpace=True)
    cmds.move(com_pos.x, 0, com_pos.z,
              "{}.cv[1]".format(AXIS_CURVE), absolute=True, worldSpace=True)

    # Color: green = stable, red = unstable
    color = 14 if stable else 13  # 14=green, 13=red
    cmds.setAttr("{}.overrideColor".format(AXIS_CURVE), color)


# -------------------------
# UPDATE LOOP
# -------------------------

def update_com(*args):
    """Called every frame change — recompute CoM and update scene objects."""
    if not cmds.objExists(COM_LOCATOR):
        return

    com_pos, total_weight = compute_com()
    if com_pos is None:
        return

    # Move locator
    cmds.move(com_pos.x, com_pos.y, com_pos.z,
              COM_LOCATOR, absolute=True, worldSpace=True)

    # Update support axis
    stable = is_com_stable(com_pos)
    update_support_axis(com_pos, stable)

    # Update CoM locator color: yellow=stable, red=unstable
    color = 17 if stable else 13
    cmds.setAttr("{}.overrideColor".format(COM_LOCATOR), color)

    # Update status label in UI
    if cmds.window(WINDOW_NAME, exists=True):
        status = "STABLE" if stable else "UNSTABLE"
        color_val = (0.2, 0.8, 0.2) if stable else (0.9, 0.2, 0.2)
        try:
            cmds.text("comStatusText", edit=True, label=status,
                      backgroundColor=color_val)
        except Exception:
            pass


def start_update_job():
    """Register scriptJob to update CoM on every frame change."""
    stop_update_job()

    job_id = cmds.scriptJob(
        event=["timeChanged", update_com],
        protected=True
    )

    if cmds.objExists(COM_LOCATOR):
        cmds.setAttr("{}.scriptJobId".format(COM_LOCATOR), job_id)

    cmds.inViewMessage(
        amg="<hl>CoM Tracker:</hl> started (job {})".format(job_id),
        pos="topCenter", fade=True
    )
    return job_id


def stop_update_job():
    """Kill the existing scriptJob if any."""
    if not cmds.objExists(COM_LOCATOR):
        return

    job_id = cmds.getAttr("{}.scriptJobId".format(COM_LOCATOR))
    if job_id > 0:
        try:
            cmds.scriptJob(kill=job_id, force=True)
        except Exception:
            pass
        cmds.setAttr("{}.scriptJobId".format(COM_LOCATOR), -1)


# -------------------------
# UI ACTIONS
# -------------------------

def assign_selected(segment, *args):
    """Assign currently selected object to a body segment."""
    sel = cmds.ls(selection=True)
    if not sel:
        cmds.warning("Select a controller first.")
        return

    ctrl = sel[0]
    _assignments[segment] = ctrl

    field_name = "comCtrl_{}".format(segment.replace(" ", "_"))
    try:
        cmds.textField(field_name, edit=True, text=ctrl)
    except Exception:
        pass

    cmds.inViewMessage(
        amg="<hl>{}</hl> → {}".format(segment, ctrl),
        pos="topCenter", fade=True
    )


def clear_assignment(segment, *args):
    """Clear assignment for a segment."""
    if segment in _assignments:
        del _assignments[segment]
    field_name = "comCtrl_{}".format(segment.replace(" ", "_"))
    try:
        cmds.textField(field_name, edit=True, text="")
    except Exception:
        pass


def build_com(*args):
    """Create markers and start tracking."""
    create_com_marker()
    create_support_axis()
    update_com()
    start_update_job()


def add_motion_trail(*args):
    """Add Maya motion trail to the CoM locator."""
    if not cmds.objExists(COM_LOCATOR):
        cmds.warning("Build CoM first.")
        return

    cmds.select(COM_LOCATOR)

    start = int(cmds.playbackOptions(query=True, minTime=True))
    end   = int(cmds.playbackOptions(query=True, maxTime=True))

    try:
        cmds.snapshot(
            name="COM_Trail",
            constructionHistory=True,
            startTime=start,
            endTime=end,
            increment=1,
            update="animCurve"
        )
        cmds.inViewMessage(
            amg="<hl>Motion Trail</hl> added to CoM",
            pos="topCenter", fade=True
        )
    except Exception as e:
        cmds.warning("Motion trail error: {}".format(e))


def delete_all(*args):
    """Stop tracking and remove scene objects."""
    stop_update_job()
    for obj in [COM_LOCATOR, AXIS_CURVE, "COM_Trail"]:
        if cmds.objExists(obj):
            cmds.delete(obj)
    cmds.inViewMessage(amg="<hl>CoM</hl> removed", pos="topCenter", fade=True)


# -------------------------
# UI
# -------------------------

def show_ui():
    if cmds.window(WINDOW_NAME, exists=True):
        cmds.deleteUI(WINDOW_NAME)

    cmds.window(WINDOW_NAME, title="Center of Mass Tool", widthHeight=(460, 640),
                sizeable=True)

    cmds.columnLayout(adjustableColumn=True, rowSpacing=4)

    # ----- Header -----
    cmds.text(label="CENTER OF MASS TRACKER", height=28,
              backgroundColor=(0.2, 0.2, 0.2), font="boldLabelFont")

    # ----- Status -----
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(120, 320),
                   adjustableColumn=2)
    cmds.text(label="Balance status:", align="right")
    cmds.text("comStatusText", label="---",
              backgroundColor=(0.3, 0.3, 0.3), height=22)
    cmds.setParent("..")

    cmds.separator(height=8, style="in")

    # ----- Body segments -----
    cmds.text(label="Assign controllers to body segments:",
              align="left", font="boldLabelFont")
    cmds.separator(height=4, style="none")

    # Column headers
    cmds.rowLayout(numberOfColumns=4,
                   columnWidth4=(115, 160, 60, 36),
                   columnAlign4=("right", "left", "center", "center"))
    cmds.text(label="Segment",    font="boldLabelFont")
    cmds.text(label="Controller", font="boldLabelFont")
    cmds.text(label="Mass %",     font="boldLabelFont")
    cmds.text(label="")
    cmds.setParent("..")

    cmds.separator(height=4, style="in")

    cmds.scrollLayout("comScrollLayout", height=360, childResizable=True)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=1)

    for seg, default_weight in BODY_SEGMENTS:
        safe = seg.replace(" ", "_")

        cmds.rowLayout(numberOfColumns=5,
                       columnWidth5=(115, 130, 34, 60, 34),
                       columnAlign5=("right", "left", "center", "center", "center"),
                       height=24)

        cmds.text(label=seg + "  ", align="right")

        cmds.textField("comCtrl_{}".format(safe),
                       text="-- none --",
                       editable=False,
                       width=128,
                       backgroundColor=(0.25, 0.25, 0.25))

        cmds.button(label="Set", width=32,
                    backgroundColor=(0.25, 0.4, 0.25),
                    command=lambda _, s=seg: assign_selected(s),
                    annotation="Assign selected controller to this segment")

        cmds.floatField("comWeight_{}".format(safe),
                        value=default_weight,
                        precision=2,
                        minValue=0.0,
                        maxValue=100.0,
                        width=58,
                        annotation="Body segment mass percentage")

        cmds.button(label="X", width=32,
                    backgroundColor=(0.4, 0.25, 0.25),
                    command=lambda _, s=seg: clear_assignment(s),
                    annotation="Clear this assignment")

        cmds.setParent("..")

    cmds.setParent("..")  # columnLayout
    cmds.setParent("..")  # scrollLayout

    cmds.separator(height=8, style="in")

    # ----- Controls -----
    cmds.gridLayout(numberOfColumns=2, cellWidthHeight=(224, 32))
    cmds.button(label="BUILD / START TRACKING", height=32,
                backgroundColor=(0.2, 0.5, 0.2),
                command=build_com)
    cmds.button(label="Add Motion Trail", height=32,
                command=add_motion_trail)
    cmds.button(label="Update Once", height=32,
                command=update_com)
    cmds.button(label="Remove All", height=32,
                backgroundColor=(0.5, 0.2, 0.2),
                command=delete_all)
    cmds.setParent("..")

    cmds.separator(height=6, style="none")
    cmds.text(label="Tip: '<' assigns selected ctrl  |  weight = body mass %",
              align="center", font="smallObliqueLabelFont",
              backgroundColor=(0.18, 0.18, 0.18))

    cmds.showWindow(WINDOW_NAME)


show_ui()
