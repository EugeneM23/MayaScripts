"""
Center of Mass Visualizer for Maya
UE Manny / Advanced Skeleton rigs.

Select any joint, skinned mesh, or rig group, then click
"Detect from Selection". A yellow marker (COM_Marker) is driven by a
weighted point constraint to the body's centre of mass.

Because the marker is constraint-driven (a native DG node), it updates
in real time during playback and rig manipulation — and Maya's motion
trail works on it directly, with no baking required.
"""

import maya.cmds as cmds

# ─────────────────────────────────────────────────────────────────────────────
# UE Manny skeleton mass-fraction map
# Based on Winter (2009) body-segment parameters. Total ≈ 1.0.
# Keys are lowercase name fragments; longest matching key wins.
# Joints not in the map contribute 0 mass and are skipped.
# These become the per-target weights of the point constraint, which
# computes Σ(pos·w) / Σ(w) — exactly the centre of mass.
# ─────────────────────────────────────────────────────────────────────────────
MANNY_WEIGHTS = {
    # Pelvis / spine
    'pelvis':     0.142,
    'spine_01':   0.070,
    'spine_02':   0.070,
    'spine_03':   0.070,
    'spine_04':   0.070,
    'spine_05':   0.070,
    # Head / neck
    'neck_01':    0.010,
    'neck_02':    0.010,
    'head':       0.048,
    # Left arm
    'clavicle_l': 0.005,
    'upperarm_l': 0.028,
    'lowerarm_l': 0.016,
    'hand_l':     0.006,
    # Right arm
    'clavicle_r': 0.005,
    'upperarm_r': 0.028,
    'lowerarm_r': 0.016,
    'hand_r':     0.006,
    # Left leg
    'thigh_l':    0.100,
    'calf_l':     0.047,
    'foot_l':     0.015,
    'ball_l':     0.003,
    # Right leg
    'thigh_r':    0.100,
    'calf_r':     0.047,
    'foot_r':     0.015,
    'ball_r':     0.003,
}

COM_MARKER_NAME = 'COM_Marker'
COM_CONSTRAINT_NAME = 'COM_pointConstraint'
COM_TRAIL_NAME = 'COM_Trail'
COM_MARKER_RADIUS = 5  # scene units (Maya default = cm)


# ─────────────────────────────────────────────────────────────────────────────
# Weight lookup
# ─────────────────────────────────────────────────────────────────────────────

def _bare_name(full_path):
    """Strip DAG path separators and namespaces → bare bone name."""
    return full_path.split('|')[-1].split(':')[-1]


def _resolve_weight(joint_full_path):
    """
    Match the bare joint name against MANNY_WEIGHTS.
    Longest matching key wins. Works with prefixes/namespaces because the
    match is a substring test. Returns 0.0 when no key matches.
    """
    low = _bare_name(joint_full_path).lower()
    best_key = ''
    best_w = 0.0
    for key, w in MANNY_WEIGHTS.items():
        if key in low and len(key) > len(best_key):
            best_key = key
            best_w = w
    return best_w


def _weighted_joints(joints):
    """Return [(joint, weight), ...] for joints that matched the map."""
    out = []
    for j in joints:
        w = _resolve_weight(j)
        if w > 0.0:
            out.append((j, w))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Joint hierarchy utilities
# ─────────────────────────────────────────────────────────────────────────────

def _find_root_joint(joint):
    """Walk up the DAG until no parent joint exists."""
    root = joint
    while True:
        parents = cmds.listRelatives(root, parent=True, type='joint')
        if not parents:
            break
        root = parents[0]
    return root


def _collect_joints(root):
    """Return [root] + all joint descendants, top-to-bottom (full paths)."""
    desc = cmds.listRelatives(
        root, allDescendents=True, type='joint', fullPath=True
    ) or []
    return [root] + list(reversed(desc))


def _find_skin_cluster(node):
    """Return the first skinCluster in node's history, or None."""
    for n in (cmds.listHistory(node, pruneDagObjects=True) or []):
        if cmds.nodeType(n) == 'skinCluster':
            return n
    return None


def _resolve_joints_from_selection():
    """
    Inspect the Maya selection and return a joint list.

    Three strategies, tried in order:
      1. Joint selected          → walk to root, collect full hierarchy
      2. Skinned mesh selected   → read skinCluster influences, same walk
      3. Group / transform       → search for joint descendants, same walk
    """
    sel = cmds.ls(selection=True, long=True)
    if not sel:
        return []

    obj = sel[0]

    # ── 1. Direct joint selection ────────────────────────────────────────────
    if cmds.nodeType(obj) == 'joint':
        return _collect_joints(_find_root_joint(obj))

    # ── 2. Skinned mesh ──────────────────────────────────────────────────────
    shapes = cmds.listRelatives(
        obj, shapes=True, noIntermediate=True, fullPath=True
    ) or []
    for sh in shapes:
        skin = _find_skin_cluster(sh)
        if skin:
            influences = cmds.skinCluster(skin, query=True, influence=True) or []
            if influences:
                return _collect_joints(_find_root_joint(influences[0]))

    # ── 3. Group containing joints ───────────────────────────────────────────
    joint_desc = cmds.listRelatives(
        obj, allDescendents=True, type='joint', fullPath=True
    ) or []
    if joint_desc:
        return _collect_joints(_find_root_joint(joint_desc[0]))

    return []


# ─────────────────────────────────────────────────────────────────────────────
# COM marker
#
# The marker is a JOINT, not a NURBS sphere. Reason: Maya's only reliable
# no-plugin "always draw on top" mechanism is X-Ray Joints, which forces
# joints to render over all geometry. A joint draws as a sphere of its
# .radius, so we get a clean yellow sphere that is never occluded.
# ─────────────────────────────────────────────────────────────────────────────

def _enable_joint_xray():
    """Turn on X-Ray Joints in every model panel so the marker draws on top."""
    for panel in (cmds.getPanel(type='modelPanel') or []):
        try:
            cmds.modelEditor(panel, edit=True, jointXray=True)
        except Exception:
            pass


def _ensure_com_marker():
    """Create the COM_Marker joint if it doesn't exist yet (return its name)."""
    # Migrate any pre-existing non-joint marker (e.g. an old NURBS sphere).
    if cmds.objExists(COM_MARKER_NAME):
        if cmds.nodeType(COM_MARKER_NAME) == 'joint':
            _enable_joint_xray()
            return COM_MARKER_NAME
        cmds.delete(COM_MARKER_NAME)

    # Create the joint at the origin, unparented from any selected node.
    cmds.select(clear=True)
    jnt = cmds.joint(name=COM_MARKER_NAME, radius=COM_MARKER_RADIUS)

    # Bright yellow display colour (Maya index 17)
    cmds.setAttr(jnt + '.overrideEnabled', 1)
    cmds.setAttr(jnt + '.overrideColor', 17)

    # Draw on top of all geometry.
    _enable_joint_xray()

    cmds.select(clear=True)
    return jnt


# ─────────────────────────────────────────────────────────────────────────────
# Constraint
# ─────────────────────────────────────────────────────────────────────────────

def _remove_com_constraint():
    """Delete the point constraint driving the marker, if present."""
    if cmds.objExists(COM_CONSTRAINT_NAME):
        cmds.delete(COM_CONSTRAINT_NAME)
    # Catch any stray point constraints parented under the marker.
    if cmds.objExists(COM_MARKER_NAME):
        for c in (cmds.listRelatives(
                COM_MARKER_NAME, type='pointConstraint', fullPath=True) or []):
            cmds.delete(c)


def _build_com_constraint(weighted):
    """
    Drive the marker with a single weighted point constraint.

    A point constraint positions its object at Σ(target·weight) / Σ(weight),
    so feeding the mass fractions as per-target weights yields the centre
    of mass — evaluated natively by the DG every frame.
    """
    targets = [j for j, _ in weighted]

    con = cmds.pointConstraint(targets, COM_MARKER_NAME, maintainOffset=False)[0]

    # Set each target's weight to its mass fraction. weightAliasList comes
    # back in the same order the targets were added.
    aliases = cmds.pointConstraint(con, query=True, weightAliasList=True) or []
    for alias, (_, w) in zip(aliases, weighted):
        cmds.setAttr(con + '.' + alias, w)

    if con != COM_CONSTRAINT_NAME:
        con = cmds.rename(con, COM_CONSTRAINT_NAME)
    return con


# ─────────────────────────────────────────────────────────────────────────────
# Commands
# ─────────────────────────────────────────────────────────────────────────────

def detect_from_selection(*_args):
    joints = _resolve_joints_from_selection()
    if not joints:
        cmds.warning(
            '[COM] Nothing usable selected. '
            'Select a joint, skinned mesh, or rig group.'
        )
        return

    weighted = _weighted_joints(joints)
    if not weighted:
        sample = [_bare_name(j) for j in joints[:8]]
        cmds.warning(
            '[COM] No joints matched the Manny weight map. '
            'Sample bone names found: {}'.format(', '.join(sample))
        )
        return

    _ensure_com_marker()
    _remove_com_constraint()          # rebuild cleanly if re-detecting
    _build_com_constraint(weighted)

    total_w = sum(w for _, w in weighted)
    msg = 'COM constraint built  |  {}/{} joints matched  |  {:.0f}% mass coverage'.format(
        len(weighted), len(joints), total_w * 100
    )
    cmds.headsUpMessage(msg)
    print('[COM] ' + msg)


def update_motion_trail(*_args):
    """
    Build a lightweight, static motion trail for the COM.

    The heavy rig evaluation happens ONCE here: we step through the
    playback range, read the marker's world position per frame, then draw
    a single degree-1 curve through those points. The curve evaluates
    nothing afterwards, so it displays instantly — click again to refresh
    it after the animation changes.
    """
    if not cmds.objExists(COM_MARKER_NAME):
        cmds.warning('[COM] Click "Detect from Selection" first.')
        return

    start = int(cmds.playbackOptions(query=True, minTime=True))
    end = int(cmds.playbackOptions(query=True, maxTime=True))
    if end <= start:
        cmds.warning('[COM] Playback range is empty.')
        return

    original_time = cmds.currentTime(query=True)

    # Sample the marker position at every frame (one fast offline pass).
    points = []
    cmds.refresh(suspend=True)
    try:
        for frame in range(start, end + 1):
            cmds.currentTime(frame, edit=True)
            p = cmds.xform(
                COM_MARKER_NAME, query=True, worldSpace=True, translation=True
            )
            points.append((p[0], p[1], p[2]))
    finally:
        cmds.refresh(suspend=False)
        cmds.currentTime(original_time, edit=True)

    if len(points) < 2:
        cmds.warning('[COM] Not enough frames to build a trail.')
        return

    # Rebuild the trail curve from scratch.
    if cmds.objExists(COM_TRAIL_NAME):
        cmds.delete(COM_TRAIL_NAME)

    crv = cmds.curve(degree=1, point=points, name=COM_TRAIL_NAME)

    # Bright light-blue wireframe. Kept on normal display type so the colour
    # actually shows (reference/template display would override it with grey).
    cmds.setAttr(crv + '.overrideEnabled', 1)
    cmds.setAttr(crv + '.overrideColor', 18)   # light blue

    msg = 'COM trail updated  ({}-{}, {} frames)'.format(start, end, len(points))
    cmds.headsUpMessage(msg)
    print('[COM] ' + msg)


def remove_com(*_args):
    """Delete the marker, its constraint, and the trail — clean scene."""
    _remove_com_constraint()
    for node in (COM_MARKER_NAME, COM_TRAIL_NAME):
        if cmds.objExists(node):
            cmds.delete(node)
    cmds.headsUpMessage('COM_Marker removed')


# ─────────────────────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────────────────────

def show_com_visualizer():
    win_id = 'comVisualizerWin'
    if cmds.window(win_id, exists=True):
        cmds.deleteUI(win_id)

    cmds.window(
        win_id,
        title='Center of Mass',
        widthHeight=(300, 260),
        sizeable=True,
    )

    # Wrap everything in a scroll layout so the buttons are always reachable,
    # no matter how the window gets resized by the OS / Maya.
    form = cmds.formLayout()
    scroll = cmds.scrollLayout(childResizable=True)
    cmds.formLayout(
        form, edit=True,
        attachForm=[
            (scroll, 'top', 0), (scroll, 'bottom', 0),
            (scroll, 'left', 0), (scroll, 'right', 0),
        ],
    )

    cmds.columnLayout(adjustableColumn=True, rowSpacing=6, columnOffset=('both', 10))
    cmds.separator(height=8, style='none')
    cmds.text(label='Center of Mass Visualizer', font='boldLabelFont', align='center')
    cmds.separator(height=6, style='in')

    cmds.button(
        label='Detect from Selection',
        height=42,
        backgroundColor=(0.35, 0.65, 0.95),
        annotation=(
            'Select any joint, skinned mesh, or rig group.\n'
            'A yellow marker (COM_Marker) is point-constrained to the\n'
            'weighted centre of mass and updates live — no baking.'
        ),
        command=detect_from_selection,
    )

    cmds.separator(height=4, style='none')
    cmds.text(
        label='Select joint / mesh / group  →  click the button',
        font='smallFixedWidthFont',
        align='center',
    )
    cmds.separator(height=6, style='in')

    cmds.button(
        label='Update Motion Trail',
        height=32,
        backgroundColor=(0.45, 0.75, 0.45),
        annotation=(
            'Sample the COM over the playback range and draw a lightweight\n'
            'curve through it. Static and instant to display — click again\n'
            'to refresh after the animation changes.'
        ),
        command=update_motion_trail,
    )

    cmds.button(
        label='Remove COM',
        height=28,
        backgroundColor=(0.7, 0.45, 0.35),
        annotation='Delete the marker and its constraint.',
        command=remove_com,
    )

    cmds.separator(height=6, style='none')
    cmds.showWindow(win_id)


show_com_visualizer()
