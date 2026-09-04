"""Retarget: drive the AdvancedSkeleton rig from a second, animated UE5 skeleton.

The animator imports a clip on an analogous skeleton, this makes the rig follow
it, and the baking stays their own button in AdvancedSkeleton: every constraint
built here registers its `nodeState` on `MoCapConstraints.disableConstraints`
and every helper node is parented under `MoCapConstraints`, which is the whole
contract the vendor's `Bake` and `Disconnect MoCap Skeleton` rely on.

Design: docs/superpowers/specs/2026-09-04-as-retarget-design.md

Run in Maya (Script Editor, Python tab):
    import sys; sys.path.append(r"C:/!!!Work/MayaScripts")
    import maya_asretarget
    print(maya_asretarget.report())      # read-only: what would be driven
    print(maya_asretarget.connect())     # build it, from the selected skeleton
    print(maya_asretarget.disconnect())  # the same as AdvancedSkeleton's button

Then, in AdvancedSkeleton: MoCap Matcher > Bake, then Disconnect MoCap Skeleton.
"""

import collections
import math

import maya.api.OpenMaya as om
import maya.cmds as cmds

# AdvancedSkeleton deform-joint base -> UE bone base.  The rig's own map
# (2026-09-04), minus the twist Part joints: they have no FK controls and the
# rig's twist network recomputes them from the bones we drive.
ROWS = [
    ("Spine1", "spine_01"), ("Spine2", "spine_02"), ("Spine3", "spine_03"),
    ("Spine4", "spine_04"), ("Spine5", "spine_05"),
    ("Neck", "neck_01"), ("NeckPart1", "neck_02"), ("Head", "head"),
    ("Scapula", "clavicle"), ("Shoulder", "upperarm"), ("Elbow", "lowerarm"),
    ("Wrist", "hand"),
    ("IndexFinger0", "index_metacarpal"), ("IndexFinger1", "index_01"),
    ("IndexFinger2", "index_02"), ("IndexFinger3", "index_03"),
    ("MiddleFinger0", "middle_metacarpal"), ("MiddleFinger1", "middle_01"),
    ("MiddleFinger2", "middle_02"), ("MiddleFinger3", "middle_03"),
    ("RingFinger0", "ring_metacarpal"), ("RingFinger1", "ring_01"),
    ("RingFinger2", "ring_02"), ("RingFinger3", "ring_03"),
    ("PinkyFinger0", "pinky_metacarpal"), ("PinkyFinger1", "pinky_01"),
    ("PinkyFinger2", "pinky_02"), ("PinkyFinger3", "pinky_03"),
    ("ThumbFinger1", "thumb_01"), ("ThumbFinger2", "thumb_02"),
    ("ThumbFinger3", "thumb_03"),
    ("Hip", "thigh"), ("Knee", "calf"), ("Ankle", "foot"), ("Toes", "ball"),
]
SIDES = [("_M", ""), ("_L", "_l"), ("_R", "_r")]

# The two controls whose own rest frame is NOT the bone's frame: AdvancedSkeleton
# keeps them world-oriented on purpose (see the rig spec), so they go through an
# offset helper.  Root motion reaches `Main`, which is what the UE `root` bone
# follows -- put it in the pelvis instead and an export loses it.
ROOT_ROWS = [("Main", "root"), ("RootX_M", "pelvis")]
# The IK end controls sit exactly on their bones with matching frames (measured
# 0.0000-0.0095 cm, 0.00000 deg), so they need no offset.  Toes take rotation
# only, as the vendor's own connect does.
IK_ROWS = [("IKArm", "hand", True), ("IKLeg", "foot", True), ("IKToes", "ball", False)]
# The pole rides the UPPER bone's frame: the limb plane is fixed by its roll, and
# a pole point-constrained to the mid joint is degenerate on a straight limb.
POLE_ROWS = [("PoleArm", "upperarm"), ("PoleLeg", "thigh")]

# Pose-independent proportions: a joint's local translation does not change with
# the pose, so these lengths compare two skeletons without posing either.
SEGMENTS = [("thigh_l", "calf_l"), ("calf_l", "foot_l"), ("thigh_r", "calf_r"),
            ("calf_r", "foot_r"), ("upperarm_l", "lowerarm_l"),
            ("lowerarm_l", "hand_l"), ("upperarm_r", "lowerarm_r"),
            ("lowerarm_r", "hand_r"), ("pelvis", "spine_01"), ("neck_01", "head")]

# How far a rest offset may sit from the identity before it needs a helper: the
# aligned controls measure ~1e-7 against their bones, the IK end controls stand
# 0.0003-0.0095 cm off theirs, and a pole is nowhere near its bone.
OFFSET_TOL = 1e-5
# A control is at its build pose when these read their defaults.  A pole's offset
# is pose-dependent (a pole is not rigidly linked to its bone), so the rest
# matrices have to be read with the rig at rest.
DEFAULTS = (("tx", 0.0), ("ty", 0.0), ("tz", 0.0), ("rx", 0.0), ("ry", 0.0), ("rz", 0.0))

HOLDER = "MoCapConstraints"      # AdvancedSkeleton's own node name
SWITCH = "disableConstraints"    # ... and its own attribute
DRIVER_PREFIX = "asrtDriver_"
TARGET_PREFIX = "asrtTarget_"

Drive = collections.namedtuple("Drive", "control bone translate rotate")


# ---------------------------------------------------------------- pure policy

def leaf(path):
    """The short name without its namespace: `|clip:root|clip:pelvis` -> `pelvis`."""
    return path.split("|")[-1].split(":")[-1]


def candidates():
    """Every control name the tables can drive, in build order."""
    out = [c for c, _ in ROOT_ROWS]
    for base, _ in ROWS:
        for side, _ in SIDES:
            out.append("FK" + base + side)
    for base, _, _ in IK_ROWS:
        for side, _ in SIDES[1:]:
            out.append(base + side)
    for base, _ in POLE_ROWS:
        for side, _ in SIDES[1:]:
            out.append(base + side)
    return out


def drive_plan(controls, bones):
    """Pure: what to constrain to what.

    controls -- control names that exist in this rig
    bones    -- leaf names that exist in the source skeleton
    Returns (drives, missing), missing being [(control, bone)] rows skipped
    because the source has no such bone.
    """
    controls = set(controls)
    bones = set(bones)
    drives, missing = [], []

    def add(control, bone, translate, rotate):
        if control not in controls:
            return
        if bone not in bones:
            missing.append((control, bone))
            return
        drives.append(Drive(control, bone, translate, rotate))

    for control, bone in ROOT_ROWS:
        add(control, bone, True, True)
    for as_base, ue_base in ROWS:
        for as_side, ue_side in SIDES:
            add("FK" + as_base + as_side, ue_base + ue_side, False, True)
    for as_base, ue_base, translate in IK_ROWS:
        for as_side, ue_side in SIDES[1:]:
            add(as_base + as_side, ue_base + ue_side, translate, True)
    for as_base, ue_base in POLE_ROWS:
        for as_side, ue_side in SIDES[1:]:
            add(as_base + as_side, ue_base + ue_side, True, False)
    return drives, missing


def top_joint(path, joint_paths):
    """Pure: the shallowest joint on `path`, or None.

    A group above the skeleton is not a joint, so `|grp|root|pelvis` answers
    `|grp|root` -- which is what lets the animator select the enclosing group's
    contents, a namespaced import or a plain bone and mean the same skeleton.
    """
    joint_paths = set(joint_paths)
    parts = [p for p in path.split("|") if p]
    for i in range(1, len(parts) + 1):
        candidate = "|" + "|".join(parts[:i])
        if candidate in joint_paths:
            return candidate
    return None


def source_root_of(selection, joint_paths, rig_paths_):
    """Pure: which skeleton the animator means.  Returns (root, refusal)."""
    if not selection:
        return "", "nothing selected - select any joint of the imported skeleton"
    roots = []
    for path in selection:
        root = top_joint(path, joint_paths)
        if root and root not in roots:
            roots.append(root)
    if not roots:
        return "", ("the selection holds no joint - select a bone of the "
                    "imported skeleton")
    if len(roots) > 1:
        return "", ("two skeletons selected (%s) - select bones of one only"
                    % ", ".join(leaf(r) for r in roots))
    root = roots[0]
    for path in rig_paths_:
        if path == root or path.startswith(root + "|"):
            return "", ("%s is the rig's own skeleton - select the imported "
                        "clip's skeleton instead" % root)
    return root, ""


def rigid(matrix):
    """Pure: the same transform with its scale and shear thrown away.

    Both matrices going into an offset have to be rigid, or the offset carries a
    scale that the helper's driver -- a plain transform following the bone by
    point+orient, scale 1 -- cannot reproduce: measured, the rig's own scale
    chain leaves ~4e-7 on a bone, and 85 cm out at the pole that came back as
    33 microns of error.
    """
    tm = om.MTransformationMatrix(om.MMatrix(matrix))
    out = om.MTransformationMatrix()
    out.setRotation(tm.rotation(asQuaternion=True))
    out.setTranslation(tm.translation(om.MSpace.kWorld), om.MSpace.kWorld)
    return list(out.asMatrix())


def offset_local(control_world, bone_world):
    """Pure: the rest offset as a LOCAL matrix, C_rest * B_rest^-1.

    Maya is row-vector (world = local * parent), so a helper carrying this as its
    local matrix, under a parent holding the source bone's world matrix, stands
    exactly where the control stands at rest -- whatever pose the clip is in.
    """
    return list(om.MMatrix(rigid(control_world))
                * om.MMatrix(rigid(bone_world)).inverse())


def is_identity(matrix, tol=1e-6):
    """Pure: is this 16-float matrix the identity within tol?"""
    return all(abs(a - b) <= tol
               for a, b in zip(list(om.MMatrix(matrix)), list(om.MMatrix())))


def rotation_only(matrix):
    """Pure: the same matrix with its translation row zeroed."""
    m = list(matrix)
    m[12] = m[13] = m[14] = 0.0
    return m


def needs_offset(local, translate, tol=OFFSET_TOL):
    """Pure: must this drive go through the offset helper?

    Measured, never tabulated: whether a control stands on its bone is a fact
    about the rig, and a rotation-only drive does not care where the bone is.
    """
    return not is_identity(local if translate else rotation_only(local), tol)


def segment_lengths(positions):
    """Pure: {first bone of the pair: distance} for every SEGMENTS pair present."""
    out = {}
    for a, b in SEGMENTS:
        if a in positions and b in positions:
            pa, pb = positions[a], positions[b]
            out[a] = math.sqrt(sum((x - y) ** 2 for x, y in zip(pa, pb)))
    return out


def scale_warning(source_lengths, rig_lengths, tol=0.02):
    """Pure: name the segments whose length differs by more than tol, or ""."""
    bad = []
    for name in sorted(rig_lengths):
        if name not in source_lengths:
            continue
        rig, src = rig_lengths[name], source_lengths[name]
        if rig > 1e-6 and abs(src - rig) / rig > tol:
            bad.append("%s %.1f vs %.1f" % (name, src, rig))
    if not bad:
        return ""
    return ("the source's proportions differ (source vs rig): " + ", ".join(bad)
            + " - a rotation copy will not land the feet; scale the source first")


# ------------------------------------------------------------- scene wrappers

def source_bones(root):
    """{leaf name without namespace: long path} for the source subtree."""
    paths = [root] + (cmds.listRelatives(root, allDescendents=True, type="joint",
                                        fullPath=True) or [])
    return dict((leaf(p), p) for p in paths)


def rig_paths():
    """Long paths that belong to the rig: everything under `Group` (the rig's own
    internals) plus the UE skeleton our DeformationSystem drives -- those joints
    carry our constraints, which is what tells them apart from an imported clip."""
    out = []
    for j in cmds.ls(type="joint", long=True) or []:
        if j == "|Group" or j.startswith("|Group|"):
            out.append(j)
        elif cmds.listRelatives(j, children=True, type="constraint"):
            out.append(j)
    return out


def rig_skeleton_root(paths):
    """The rig's UE skeleton root: the shallowest path outside `Group`."""
    outside = [p for p in paths if not (p == "|Group" or p.startswith("|Group|"))]
    if not outside:
        return ""
    return sorted(outside, key=lambda p: (p.count("|"), p))[0]


def _set_local(node, matrix):
    """Write a local matrix onto a transform as translate + rotate.

    Only those two are needed: a point constraint reads the target's world
    position and an orient constraint its world rotation, and the offset between
    two rigid frames carries no shear.
    """
    tm = om.MTransformationMatrix(om.MMatrix(matrix))
    tm.reorderRotation(cmds.getAttr(node + ".rotateOrder") + 1)
    e = tm.rotation(asQuaternion=False)
    t = tm.translation(om.MSpace.kTransform)
    cmds.setAttr(node + ".translate", t.x, t.y, t.z)
    cmds.setAttr(node + ".rotate", math.degrees(e.x), math.degrees(e.y),
                 math.degrees(e.z))


def _holder():
    """AdvancedSkeleton's own holder node, created the way its connect does."""
    if not cmds.objExists(HOLDER):
        cmds.createNode("transform", name=HOLDER, skipSelect=True)
        for attr in ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"):
            cmds.setAttr(HOLDER + "." + attr, lock=True)
    if not cmds.attributeQuery(SWITCH, node=HOLDER, exists=True):
        cmds.addAttr(HOLDER, longName=SWITCH, attributeType="bool", keyable=True)
    return HOLDER


def _register(constraints):
    """The contract: the vendor's Bake walks these, its Disconnect deletes them."""
    for c in constraints:
        cmds.connectAttr(HOLDER + "." + SWITCH, c + ".nodeState", force=True)


def _helper(control, source_path, local):
    """Driver (follows the source bone 1:1) + target (holds the rest offset)."""
    driver = cmds.createNode("transform", name=DRIVER_PREFIX + control,
                             parent=HOLDER, skipSelect=True)
    made = [cmds.pointConstraint(source_path, driver)[0],
            cmds.orientConstraint(source_path, driver)[0]]
    target = cmds.createNode("transform", name=TARGET_PREFIX + control,
                             parent=driver, skipSelect=True)
    _set_local(target, local)
    return target, made


NECK_BIAS = ("FKNeck_M", "bias", 10.0)   # measured: 0 -> neck_01 takes half, 10 -> all


def has_neck_inbetween():
    """Does this rig's neck distribute its control's bend across two joints?"""
    control, attr, _ = NECK_BIAS
    return bool(cmds.objExists("NeckInbetweenMM_M")
                and cmds.attributeQuery(attr, node=control, exists=True))


def neck_note():
    """What the neck's in-between costs a retarget, and the knob that removes it.

    Measured 2026-09-04: `FKNeck_M.bias` (keyable, soft range 0..10, default 0)
    feeds the in-between's blend weight linearly -- 0 gives 0.5 and 10 gives
    1.0, where 30 deg on the control turns neck_01 by exactly 30.0000.  So at
    the default the retargeted neck lands half as bent as the source's.
    """
    if not has_neck_inbetween():
        return ""
    control, attr, full = NECK_BIAS
    return ("note: the neck's in-between hands neck_01 HALF of its control's "
            "bend, so the neck lands softer than the source (the head's "
            "orientation is exact, its position a few mm off at a 15 deg bend). "
            "For an exact neck set %s.%s to %g -- by hand, or "
            "connect(exact_neck=True)." % (control, attr, full))


def set_exact_neck():
    """Turn the neck's in-between off by its own bias attribute.  Writes."""
    if not has_neck_inbetween():
        return ""
    control, attr, full = NECK_BIAS
    was = cmds.getAttr(control + "." + attr)
    cmds.setAttr(control + "." + attr, full)
    return ("neck: %s.%s %g -> %g, so neck_01 takes its control's bend 1:1. "
            "LEAVE IT THERE - it decides how the baked neck keys distribute, and "
            "putting it back to %g afterwards would halve the neck again."
            % (control, attr, was, full, was))


def posed_controls(tol=1e-3):
    """Controls off their default translate/rotate: the rig is not at build pose."""
    out = []
    for control in cmds.sets("ControlSet", query=True) or []:
        for attr, default in DEFAULTS:
            plug = control + "." + attr
            if not cmds.objExists(plug) or not cmds.getAttr(plug, settable=True):
                continue
            if abs(cmds.getAttr(plug) - default) > tol:
                out.append(control)
                break
    return out


def _key_range(paths):
    """The source's own key range, as text -- the animator has to match the
    playback range to it before the vendor's Bake, which reads only that."""
    if not paths:
        return "no keys"
    count = cmds.keyframe(paths, query=True, keyframeCount=True) or 0
    if not count:
        return "no keys"
    return "%g..%g" % (cmds.findKeyframe(paths, which="first"),
                       cmds.findKeyframe(paths, which="last"))


Plan = collections.namedtuple("Plan", "root drives missing warn bones rig_bones refusal")


def _plan(source_root=None):
    """Everything connect() needs, computed without touching the scene."""
    empty = Plan("", [], [], "", {}, {}, "")
    if not cmds.objExists("ControlSet") or not cmds.objExists("Main"):
        return empty._replace(
            refusal="no AdvancedSkeleton rig in this scene (ControlSet/Main missing)")
    joints = cmds.ls(type="joint", long=True) or []
    rig = rig_paths()
    if source_root is None:
        source_root, refusal = source_root_of(
            cmds.ls(selection=True, long=True) or [], joints, rig)
        if refusal:
            return empty._replace(refusal=refusal)
    elif not cmds.objExists(source_root):
        return empty._replace(refusal="%s not found" % source_root)
    ue_root = rig_skeleton_root(rig)
    if not ue_root:
        return empty._replace(
            refusal="the rig drives no skeleton - is this rig constrained to UE bones?")
    rig_bones = dict((leaf(p), p) for p in [ue_root] + (
        cmds.listRelatives(ue_root, allDescendents=True, type="joint",
                           fullPath=True) or []))
    bones = source_bones(source_root)
    controls = [c for c in candidates() if cmds.objExists(c)]
    drives, missing = drive_plan(controls, list(bones))
    drives = [d for d in drives if d.bone in rig_bones]
    if not drives:
        return empty._replace(
            refusal="no bone of %s matches this rig - is it a UE5 skeleton?"
                    % leaf(source_root))
    warn = scale_warning(
        segment_lengths(dict((n, cmds.xform(p, query=True, worldSpace=True,
                                            translation=True))
                             for n, p in bones.items())),
        segment_lengths(dict((n, cmds.xform(p, query=True, worldSpace=True,
                                            translation=True))
                             for n, p in rig_bones.items())))
    return Plan(source_root, drives, missing, warn, bones, rig_bones, "")


def report(source_root=None):
    """Read-only: what connect() would build, and from what."""
    plan = _plan(source_root)
    if plan.refusal:
        return plan.refusal
    lines = ["source: %s (%d bones, keys %s)"
             % (plan.root, len(plan.bones), _key_range(list(plan.bones.values())))]
    offsets = [d.control for d in plan.drives
               if needs_offset(offset_local(
                   cmds.getAttr(d.control + ".worldMatrix[0]"),
                   cmds.getAttr(plan.rig_bones[d.bone] + ".worldMatrix[0]")),
                   d.translate)]
    lines.append("would drive %d controls: %d rotation only, %d with position; "
                 "%d need a rest offset (%s)"
                 % (len(plan.drives),
                    len([d for d in plan.drives if not d.translate]),
                    len([d for d in plan.drives if d.translate]),
                    len(offsets), ", ".join(offsets)))
    posed = posed_controls()
    if posed:
        lines.append("the rig is posed (%s%s) - connect() will refuse until it is "
                     "at its build pose" % (", ".join(posed[:4]),
                                            " ..." if len(posed) > 4 else ""))
    if plan.missing:
        lines.append("no source bone for: "
                     + ", ".join("%s (%s)" % (c, b) for c, b in plan.missing))
    if plan.warn:
        lines.append(plan.warn)
    lines.append(neck_note())
    if cmds.objExists(HOLDER):
        lines.append("%s already exists - disconnect first" % HOLDER)
    return "\n".join(line for line in lines if line)


def connect(source_root=None, require_build_pose=True, exact_neck=False):
    """Make the rig follow the source skeleton, in AdvancedSkeleton's own shape."""
    if cmds.objExists(HOLDER):
        return ("%s already exists - press \"Disconnect MoCap Skeleton\" in "
                "AdvancedSkeleton first, or run disconnect()" % HOLDER)
    plan = _plan(source_root)
    if plan.refusal:
        return plan.refusal
    posed = posed_controls()
    if posed and require_build_pose:
        return ("the rig is posed (%s%s) - press \"Go To BuildPose\" in "
                "AdvancedSkeleton first, or connect(require_build_pose=False). "
                "The rest offsets are read from the pose the rig stands in, and "
                "a pole's offset is pose-dependent."
                % (", ".join(posed[:4]), " ..." if len(posed) > 4 else ""))

    # Read every rest matrix BEFORE building anything: the first constraints move
    # controls that later ones measure against (a pole follows the IK control it
    # rides, so its offset came out 0.022 cm wrong when read mid-build).
    rest_control = dict((d.control, cmds.getAttr(d.control + ".worldMatrix[0]"))
                        for d in plan.drives)
    rest_bone = dict((d.bone, cmds.getAttr(plan.rig_bones[d.bone] + ".worldMatrix[0]"))
                     for d in plan.drives)

    auto = cmds.autoKeyframe(query=True, state=True)
    cmds.autoKeyframe(state=False)
    cmds.undoInfo(openChunk=True, chunkName="AS retarget connect")
    made = []
    offsets = 0
    try:
        _holder()
        for drive in plan.drives:
            target = plan.bones[drive.bone]
            local = offset_local(rest_control[drive.control], rest_bone[drive.bone])
            if needs_offset(local, drive.translate):
                target, helpers = _helper(drive.control, target, local)
                made += helpers
                offsets += 1
            if drive.translate:
                made.append(cmds.pointConstraint(target, drive.control)[0])
            if drive.rotate:
                made.append(cmds.orientConstraint(target, drive.control)[0])
        _register(made)
    finally:
        cmds.undoInfo(closeChunk=True)
        cmds.autoKeyframe(state=auto)

    lines = ["retarget connected: %d controls driven from %s (%d through a rest "
             "offset)" % (len(plan.drives), leaf(plan.root), offsets)]
    if plan.missing:
        lines.append("no source bone for: "
                     + ", ".join(c for c, _ in plan.missing))
    if plan.warn:
        lines.append(plan.warn)
    lines.append("playback range %g..%g, the source's keys run %s - the vendor's"
                 " Bake reads the RANGE, so match it to the clip first"
                 % (cmds.playbackOptions(query=True, min=True),
                    cmds.playbackOptions(query=True, max=True),
                    _key_range(list(plan.bones.values()))))
    lines.append(set_exact_neck() if exact_neck else neck_note())
    lines.append("now in AdvancedSkeleton: MoCap Matcher > Bake, then "
                 "Disconnect MoCap Skeleton")
    return "\n".join(line for line in lines if line)


def disconnect():
    """What AdvancedSkeleton's own \"Disconnect MoCap Skeleton\" button does."""
    if not cmds.objExists(HOLDER):
        return "nothing connected (%s not found)" % HOLDER
    doomed = []
    if cmds.attributeQuery(SWITCH, node=HOLDER, exists=True):
        doomed = cmds.listConnections(HOLDER + "." + SWITCH, source=False,
                                      destination=True) or []
    cmds.undoInfo(openChunk=True, chunkName="AS retarget disconnect")
    try:
        for node in sorted(set(doomed)):
            if cmds.objExists(node):
                cmds.delete(node)
        if cmds.objExists(HOLDER):     # its children, our helpers, go with it
            cmds.delete(HOLDER)
    finally:
        cmds.undoInfo(closeChunk=True)
    return "retarget disconnected (%d constraints)" % len(set(doomed))
