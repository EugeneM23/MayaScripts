"""AdvancedSkeleton rig over the PlayerMale game skeleton -- the procedure.

The skeleton is NOT Unreal's.  57 joints: `Root` at the origin, `Hip`, `Spine1..4`,
`Neck`, `Head`, `Jaw`, `Left_Eye`/`Right_Eye`, clavicles as `*_Shoulder`, arms
`*_Arm`/`*_ForeArm`/`*_Hand`, five fingers of three joints each and no metacarpals
(`*_Finger1..3` is the index), legs `*_Thigh`/`*_Knee`/`*_Ankle`/`*_Toes`.  The side is
a PREFIX (`Right_`, `Left_`), bones run down local X (the left side down -X), there are
no twist joints, the character is 17.5 units tall in a centimetre scene (1:10), faces
+Z and has its right side on -X.  Written 2026-09-05 for `PlayerMale_v6.fbx`
(AdvancedSkeleton 6.797, Maya 2027) after the UE5 Manny procedure of 2026-09-04
(`as_ue5_rig_procedure.py`), whose shape it keeps: the game skeleton is untouched and
every AS deformation joint drives its game twin through point+orient+scale
constraints (`-mo`), `Root` follows `Main`, and every FK control and IK end control
carries the local axes of the bone it drives.

Three things are specific to this skeleton and each is measured in the spec:

- **Its joint names collide with AdvancedSkeleton's fit joints.**  `Root`, `Hip`,
  `Spine1`, `Spine2`, `Neck`, `Head`, `Jaw` (and `Spine3`, which we add to the fit) are
  exactly what the FitSkeleton's joints are called, and AS addresses those by SHORT
  name everywhere (`getAttr Hip.twistJoints`; `asFitModeManualUpdate` runs
  `asUniqueNameAll`, which would rename a non-unique FIT joint to `Hip1`).  So `hold()`
  renames the eight game joints to `PMhold_<name>` for the length of the fit and the
  build and `release()` gives the names back -- constraints, skin and bindPose are
  wired to nodes, not names.  A later ReBuild needs `hold()` first.
- **No twist joints:** the fit's `twistJoints` go to 0 on Shoulder/Elbow/Hip so the
  roll lands on `*_Arm`/`*_ForeArm`/`*_Thigh` themselves; `inbetweenJoints` 0 on
  Root/Spine1/Neck; `Cup` (a metacarpal control) is deleted with its two SDK curves.
- **The fit's end joints have no game counterpart** and are placed from the geometry:
  HeadEnd on the top of the bare head mesh, JawEnd on the chin, EyeEnd in front of the
  eye, finger tips by extrapolating the last phalanx, and the foot pivots (Heel,
  ToesEnd, FootSideInner/Outer) on the bare foot's sole.

Every stage can be run on its own; `run()` does the whole thing.  Nothing here is
found by a scene-wide short name: the game skeleton is resolved through its root and
the hold attribute, the fit through `|FitSkeleton`.
"""
import math
import os
import time

import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

AS_MEL = "C:/Users/MY PC/Downloads/AdvancedSkeleton/AdvancedSkeleton.mel"
FIT_FILE = "biped.ma"
GAME_ROOT_NAME = "Root"
HOLD_PREFIX = "PMhold_"
HOLD_ATTR = "asHeldName"
HEAD_MESH = "|HEAD1|Head1"      # the bare head; the crown and the hair sit higher
FOOT_MESH = "|Body"             # the bare foot; the boots are a little bigger
LAYER = "PlayerMale_Skeleton"
AS_LAYER = "AS_DeformSkeleton"
TIP_FACTOR = 0.8                # a fingertip this far past the last joint, in units of the phalanx before it
EYE_END = 1.0                   # EyeEnd this far in front of the eye (world +Z)

# fit joint -> game joint, without the side prefix.  The fit skeleton is right-side only.
ROWS = [("Root", "Hip"), ("Spine1", "Spine1"), ("Spine2", "Spine2"), ("Spine3", "Spine3"), ("Chest", "Spine4"),
        ("Neck", "Neck"), ("Head", "Head"), ("Jaw", "Jaw"), ("Eye", "Eye"),
        ("Scapula", "Shoulder"), ("Shoulder", "Arm"), ("Elbow", "ForeArm"), ("Wrist", "Hand"),
        ("IndexFinger1", "Finger1"), ("IndexFinger2", "Finger2"), ("IndexFinger3", "Finger3"),
        ("MiddleFinger1", "Middle1"), ("MiddleFinger2", "Middle2"), ("MiddleFinger3", "Middle3"),
        ("RingFinger1", "Ring1"), ("RingFinger2", "Ring2"), ("RingFinger3", "Ring3"),
        ("PinkyFinger1", "Pinky1"), ("PinkyFinger2", "Pinky2"), ("PinkyFinger3", "Pinky3"),
        ("ThumbFinger1", "Thumb1"), ("ThumbFinger2", "Thumb2"), ("ThumbFinger3", "Thumb3"),
        ("Hip", "Thigh"), ("Knee", "Knee"), ("Ankle", "Ankle"), ("Toes", "Toes")]
ROW = dict(ROWS)
SIDES = (("_M", ""), ("_R", "Right_"), ("_L", "Left_"))
SIDE = dict(SIDES)
MIDDLE = ("Root", "Spine1", "Spine2", "Spine3", "Chest", "Neck", "Head", "Jaw")
FINGERS = (("Index", "Finger"), ("Middle", "Middle"), ("Ring", "Ring"), ("Pinky", "Pinky"), ("Thumb", "Thumb"))
# the game joints whose names the fit joints also carry
CLASHING = ("Root", "Hip", "Spine1", "Spine2", "Spine3", "Neck", "Head", "Jaw")
IK_END = [("IKLeg_R", "Right_Ankle"), ("IKLeg_L", "Left_Ankle"), ("IKArm_R", "Right_Hand"),
          ("IKArm_L", "Left_Hand"), ("IKToes_R", "Right_Toes"), ("IKToes_L", "Left_Toes")]
SDK_AXIS = "SDKAxis"


# ---------------------------------------------------------------- small algebra

def _wmat(n):
    return om.MMatrix(cmds.getAttr(n + ".worldMatrix[0]"))


def _pos(n):
    return om.MVector(cmds.xform(n, q=True, ws=True, t=True))


def _rot(m):
    return om.MTransformationMatrix(m).rotation(asQuaternion=True)


def _row(m, i):
    return om.MVector(m.getElement(i, 0), m.getElement(i, 1), m.getElement(i, 2))


def _set_rot(node, rmat):
    tm = om.MTransformationMatrix(rmat)
    tm.reorderRotation(cmds.getAttr(node + ".rotateOrder") + 1)   # attr enum + 1 == MTransformationMatrix order
    e = tm.rotation(asQuaternion=False)
    cmds.setAttr(node + ".rotate", math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))


def _set_local(node, local):
    """Write a full local matrix (rotation in the node's order, translation) onto a transform."""
    tm = om.MTransformationMatrix(local)
    tm.reorderRotation(cmds.getAttr(node + ".rotateOrder") + 1)
    e = tm.rotation(asQuaternion=False)
    t = tm.translation(om.MSpace.kTransform)
    cmds.setAttr(node + ".translate", t.x, t.y, t.z)
    cmds.setAttr(node + ".rotate", math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))


def _angle(ma, mb):
    """Angle in degrees between the rotations of two matrices."""
    d = _rot(ma).inverse() * _rot(mb)
    return math.degrees(2 * math.acos(max(-1.0, min(1.0, abs(d.w)))))


def _mesh_points(transform):
    shapes = cmds.listRelatives(transform, shapes=True, noIntermediate=True, fullPath=True, type="mesh")
    sl = om.MSelectionList()
    sl.add(shapes[0])
    return om.MFnMesh(sl.getDagPath(0)).getPoints(om.MSpace.kWorld)


# ---------------------------------------------------------------- the game skeleton

def original_name(path):
    """The name a joint had before hold(); its leaf name otherwise."""
    if cmds.attributeQuery(HOLD_ATTR, node=path, exists=True):
        return cmds.getAttr(path + "." + HOLD_ATTR)
    return path.split("|")[-1]


def game_root():
    """The game skeleton's top joint, held or not -- never the fit skeleton's `Root` or AS's `Root_M`."""
    found = []
    for j in cmds.ls(type="joint", long=True) or []:
        if cmds.listRelatives(j, parent=True, type="joint"):
            continue
        if "|FitSkeleton|" in j or j.startswith("|Group|") or "|DeformationSystem|" in j:
            continue
        if original_name(j) == GAME_ROOT_NAME:
            found.append(j)
    if len(found) != 1:
        raise RuntimeError("expected one game skeleton root named %s, found %s" % (GAME_ROOT_NAME, found))
    return found[0]


def game_joints():
    """{original leaf name: long path} for every joint of the game skeleton."""
    root = game_root()
    joints = [root] + (cmds.listRelatives(root, allDescendents=True, type="joint", fullPath=True) or [])
    return dict((original_name(j), j) for j in joints)


def hold():
    """Rename the game joints whose names the fit joints use; each remembers its name on an attribute."""
    n = 0
    for name in CLASHING:
        path = game_joints().get(name)                  # re-read: renaming a parent changes every path below it
        if not path or path.split("|")[-1] != name:
            continue
        if not cmds.attributeQuery(HOLD_ATTR, node=path, exists=True):
            cmds.addAttr(path, ln=HOLD_ATTR, dt="string")
        cmds.setAttr(path + "." + HOLD_ATTR, name, type="string")
        cmds.rename(path, HOLD_PREFIX + name)
        n += 1
    return n


def release():
    """Give every held joint its name back."""
    held = [cmds.ls(j, uuid=True)[0] for j in cmds.ls(type="joint", long=True) or []
            if cmds.attributeQuery(HOLD_ATTR, node=j, exists=True)]
    n = 0
    for uid in held:
        path = cmds.ls(uid, long=True)[0]
        name = cmds.getAttr(path + "." + HOLD_ATTR)
        cmds.deleteAttr(path + "." + HOLD_ATTR)
        got = cmds.rename(path, name)
        if got.split("|")[-1] != name:
            raise RuntimeError("could not give %s its name back, Maya made it %s" % (name, got))
        n += 1
    return n


def held():
    return [original_name(j) for j in cmds.ls(type="joint", long=True) or []
            if cmds.attributeQuery(HOLD_ATTR, node=j, exists=True)]


# ---------------------------------------------------------------- AdvancedSkeleton

def ensure_as_ui():
    """Source the toolset and open its window -- the vendor's procs read their own controls."""
    if mel.eval('whatIs "asReBuildAdvancedSkeleton"') == "Unknown":
        mel.eval('source "%s";' % AS_MEL)
    if not cmds.optionMenu("asFitFiles", exists=True):
        mel.eval("AdvancedSkeleton;")


def fit_joints():
    """{leaf: long path} of the FitSkeleton's joints -- at |FitSkeleton before the build, under |Group after it."""
    tops = cmds.ls("FitSkeleton", long=True) or []
    if len(tops) != 1:
        raise RuntimeError("expected one FitSkeleton, found %s" % tops)
    return dict((j.split("|")[-1], j) for j in
                cmds.listRelatives(tops[0], allDescendents=True, type="joint", fullPath=True) or [])


def end_positions():
    """World positions for the fit joints that have no game counterpart, from the geometry."""
    game = game_joints()
    P = lambda name: _pos(game[name])
    ends = {}
    head, jaw, eye = P("Head"), P("Jaw"), P("Right_Eye")
    pts = _mesh_points(HEAD_MESH)
    ends["HeadEnd"] = om.MVector(0.0, max(q.y for q in pts), head.z)
    front = [q for q in pts if abs(q.x) < 0.25 and jaw.y - 1.5 < q.y < jaw.y]
    chin = max(front, key=lambda q: q.z - 0.5 * q.y)            # the front-most low point of the face
    ends["JawEnd"] = om.MVector(0.0, chin.y, chin.z)
    ends["EyeEnd"] = eye + om.MVector(0.0, 0.0, EYE_END)
    for as_name, game_name in FINGERS:
        j2, j3 = P("Right_%s2" % game_name), P("Right_%s3" % game_name)
        ends["%sFinger4" % as_name] = j3 + (j3 - j2) * TIP_FACTOR
    ankle, toes = P("Right_Ankle"), P("Right_Toes")
    sole = [q for q in _mesh_points(FOOT_MESH) if q.x < 0 and abs(q.x - ankle.x) < 1.5 and q.y < ankle.y - 0.7]
    floor = min(q.y for q in sole)
    ends["ToesEnd"] = om.MVector(toes.x, floor, max(q.z for q in sole))
    ends["Heel"] = om.MVector(ankle.x, floor, min(q.z for q in sole))
    ends["FootSideInner"] = om.MVector(max(q.x for q in sole), floor, toes.z)
    ends["FootSideOuter"] = om.MVector(min(q.x for q in sole), floor, toes.z)
    return ends


def _snap(path, pos):
    """xform a fit joint in world space, through any locks AS put on its translate channels (trap 51)."""
    locked = [a for a in ("tx", "ty", "tz") if cmds.getAttr(path + "." + a, lock=True)]
    for a in locked:
        cmds.setAttr(path + "." + a, lock=False)
    cmds.xform(path, ws=True, t=(pos.x, pos.y, pos.z))
    for a in locked:
        cmds.setAttr(path + "." + a, lock=True)


def reset_fit():
    """Remove an unbuilt FitSkeleton and the driving-system curves it imported, so fit() can start over.

    asFitSkeletonImport would otherwise ask Replace / Merge / Cancel -- a modal dialog.  Refused
    once a rig exists: a built rig needs its FitSkeleton for every ReBuild.
    """
    if cmds.objExists("Group"):
        raise RuntimeError("a rig exists; its FitSkeleton stays")
    n = 0
    if cmds.objExists("|FitSkeleton"):
        cmds.delete("|FitSkeleton")
        n += 1
    for c in cmds.ls("SDK*", type="animCurve") or []:
        if not cmds.listConnections(c + ".output", s=False, d=True):
            cmds.delete(c)
            n += 1
    return n


def fit():
    """Import the biped FitSkeleton, give it this skeleton's shape and put every joint on its bone.

    Returns (joints placed, worst distance of a mapped fit joint from its game joint).
    """
    if cmds.objExists("|FitSkeleton"):
        raise RuntimeError("a FitSkeleton already exists")
    if cmds.objExists("Group"):
        raise RuntimeError("an AdvancedSkeleton rig (Group) already exists")
    game = game_joints()
    loose = [n for n in CLASHING if n in game and game[n].split("|")[-1] == n]
    if loose:
        raise RuntimeError("hold() first: %s still carry the names the fit joints need" % loose)
    ensure_as_ui()
    cmds.optionMenu("asFitFiles", e=True, v=FIT_FILE)
    # asFitSkeletonImport ends in asImportMatcherScan, which for a biped template looks for any
    # joint named *Hip*/*hip*/*pelvis* and asks "Align joints with this skeleton?" -- a modal
    # dialog, which over the command port is a blocked idle queue.  The vendor's own Name
    # Matcher suppresses it with exactly this node.
    guard = cmds.createNode("transform", n="FitSkeletonNameMatcherImporting")
    try:
        mel.eval("asFitSkeletonImport;")
    finally:
        if cmds.objExists(guard):
            cmds.delete(guard)
    fj = fit_joints()
    # the shape: four spine joints (biped.ma has Root > Spine1 > Chest), no Cup, no twist or
    # in-between joints anywhere
    below = fj["Spine1"]
    for name in ("Spine2", "Spine3"):
        j = cmds.duplicate(below, parentOnly=True, name=name)[0]
        below = cmds.parent(j, below)[0]
    cmds.parent(fj["Chest"], below)
    fj = fit_joints()
    for f in ("RingFinger1", "PinkyFinger1"):
        cmds.parent(fj[f], fj["Wrist"])
    fj = fit_joints()
    cmds.delete(fj["Cup"])
    for c in cmds.ls("SDK1FKCup_*", type="animCurve") or []:      # the `cup` driving system has nothing to drive
        cmds.delete(c)
    fj = fit_joints()
    for path in fj.values():
        for attr in ("twistJoints", "inbetweenJoints"):
            if cmds.attributeQuery(attr, node=path, exists=True):
                cmds.setAttr(path + "." + attr, 0)
    if _pos(fj["Shoulder"]).x > 0:
        raise RuntimeError("the fit skeleton's side is on +X; this procedure expects the right side on -X")
    # place: parents first (a parent's move carries its children), mapped joints on their bones,
    # the ends from the geometry
    ends = end_positions()
    placed = 0
    for path in sorted(fj.values(), key=lambda p: p.count("|")):
        leaf = path.split("|")[-1]
        if leaf in ROW:
            target = _pos(game[SIDE["_M" if leaf in MIDDLE else "_R"] + ROW[leaf]])
        elif leaf in ends:
            target = ends[leaf]
        else:
            raise RuntimeError("fit joint %s has neither a game joint nor a measured end" % leaf)
        _snap(path, target)
        placed += 1
    mel.eval("asFitModeManualUpdate;")
    fj = fit_joints()
    worst = max((_pos(fj[leaf]) - _pos(game[SIDE["_M" if leaf in MIDDLE else "_R"] + ROW[leaf]])).length()
                for leaf in fj if leaf in ROW)
    return placed, worst


def build():
    """The first build.  Nothing in the scene may be called Group, Main, MotionSystem, DeformationSystem, Geometry."""
    t0 = time.time()
    mel.eval("asReBuildAdvancedSkeleton;")
    if not (cmds.objExists("Group") and cmds.objExists("DeformSet")):
        raise RuntimeError("the build did not complete")
    return time.time() - t0


def mapping():
    """{AS deformation joint: game joint long path} -- every deform joint that has a row."""
    game = game_joints()
    out = {}
    for fit_name, game_name in ROWS:
        for suffix, prefix in SIDES:
            d = fit_name + suffix
            g = game.get(prefix + game_name)
            if g and cmds.objExists(d) and cmds.nodeType(d) == "joint":
                out[cmds.ls(d, long=True)[0]] = g
    return out


def constrain():
    """The vendor's 'Constraint to Joints' (point + orient + scale, -mo) written by long path, plus Root <- Main."""
    made = 0
    for d, g in sorted(mapping().items()):
        if cmds.listRelatives(g, children=True, type="constraint"):
            continue
        cmds.pointConstraint(d, g, maintainOffset=True)
        cmds.orientConstraint(d, g, maintainOffset=True)
        cmds.scaleConstraint(d, g, maintainOffset=True)
        made += 3
    root = game_root()
    if not cmds.listRelatives(root, children=True, type="constraint"):
        cmds.parentConstraint("Main", root, maintainOffset=True)
        made += 1
    return made


def orient_controls(ik_ends=False):
    """Every FK control's frame becomes its bone's frame; RootX_M keeps AS's; the IK end controls
    keep AS's too unless `ik_ends` is True.

    Same as the Manny procedure: Detach, write each control's world rotation
    (`local = R_bone * R_parent^-1`, in the control's own rotate order), Attach with mirror
    OFF so each side reads its own bone.  The neck in-between reconnect is kept for the day
    the fit gets an in-between again (it is a no-op without one); the arm pole's follow
    offset is the one consumer of an IK control's own rotation and is compensated.

    `ik_ends` is False here by the animator's call (2026-09-05, «давай А попробуем»): on this
    skeleton the ankle bone points 26 deg down at the ball and the hand is rolled 34 deg
    against AS's wrist, so IK controls on the bones' axes stood crooked, foot boxes nose-down
    into the floor.  AS's own IK frames are world-aligned and read right.
    """
    for mm in ("NeckInbetweenMM_M", "NeckPart1InbetweenMM_M"):
        if cmds.objExists(mm) and cmds.objExists("FKOffsetNeck_M"):
            cmds.connectAttr("FKOffsetNeck_M.worldInverseMatrix[0]", mm + ".matrixIn[1]", force=True)
    game = game_joints()
    targets = []
    for d, g in mapping().items():
        leaf = d.split("|")[-1]
        if leaf == "Root_M" or not cmds.objExists("FK" + leaf):
            continue
        targets.append(("FK" + leaf, g))
    if ik_ends:
        targets += [(c, game[b]) for c, b in IK_END if cmds.objExists(c)]
    w_old = dict((c, _wmat(c)) for c, _ in IK_END if ik_ends and cmds.objExists(c))
    mel.eval("asControlOrientDetach;")
    for c, g in targets:
        Rb = _rot(_wmat(g)).asMatrix()
        Pr = _rot(om.MMatrix(cmds.getAttr(c + ".parentMatrix[0]"))).asMatrix()
        _set_rot(c, Rb * Pr.inverse())                          # row vectors: world = local * parent
    cmds.checkBox("asControlOrientAttachMirrorCheckBox", e=True, v=0)
    mel.eval("asControlOrientAttach;")
    for s in "LR":                                              # matrixSum = M0 * M1 * ctrl.worldMatrix; keep it
        c, mm = "IKArm_%s" % s, "PoleOffsetArmMMArm_%s" % s
        if c in w_old and cmds.objExists(mm):
            d = _wmat(c) * w_old[c].inverse()
            m1 = om.MMatrix(cmds.getAttr(mm + ".matrixIn[1]"))
            cmds.setAttr(mm + ".matrixIn[1]", list(m1 * d.inverse()), type="matrix")
    worst = max(_angle(_wmat(c), _wmat(g)) for c, g in targets)
    return len(targets), worst


def as_frames(controls=None):
    """Give controls AdvancedSkeleton's OWN orientation back -- the frame of the node above their
    CustomOrient (IKOffsetLeg_R, or the deformation joint for an FK control).

    Written for the IK end controls after the animator saw them standing crooked: on this
    skeleton the ankle bone points 26 deg down at the ball and the hand is rolled 34 deg
    against AS's wrist, so a control that carries the bone's axes tilts with it, box and all.
    The drawing goes back to AS's CVs (the axis permutation align_shapes applied is undone
    while it is still known), then Detach / set / Attach as in orient_controls, with the
    arm pole's follow offset compensated.  Nothing moves.  Returns the worst angle left
    between a control and AS's frame.
    """
    controls = [c for c in (controls or [c for c, _ in IK_END]) if cmds.objExists("CustomOrient" + c)]
    frames = {}
    for c in controls:
        k = "CustomOrient" + c
        as_frame = cmds.listRelatives(k, p=True)[0] if c.startswith("IK") else c[2:]
        frames[c] = _rot(_wmat(as_frame)).asMatrix()
        perm = _nearest_perm(frames[c] * _rot(_wmat(c)).asMatrix().inverse())
        if perm is not None:
            inv = perm.transpose()
            for s in cmds.listRelatives(c, s=True, type="nurbsCurve", fullPath=True) or []:
                sl = om.MSelectionList()
                sl.add(s)
                fn = om.MFnNurbsCurve(sl.getDagPath(0))
                fn.setCVPositions(om.MPointArray([om.MPoint(pt) * inv for pt in fn.cvPositions(om.MSpace.kObject)]), om.MSpace.kObject)
                fn.updateCurve()
    w_old = dict((c, _wmat(c)) for c in controls if c.startswith("IKArm"))
    mel.eval("asControlOrientDetach;")
    for c, R in frames.items():
        Pr = _rot(om.MMatrix(cmds.getAttr(c + ".parentMatrix[0]"))).asMatrix()
        _set_rot(c, R * Pr.inverse())
    cmds.checkBox("asControlOrientAttachMirrorCheckBox", e=True, v=0)
    mel.eval("asControlOrientAttach;")
    for c in w_old:
        mm = "PoleOffsetArmMMArm_" + c[-1]
        if cmds.objExists(mm):
            d = _wmat(c) * w_old[c].inverse()
            m1 = om.MMatrix(cmds.getAttr(mm + ".matrixIn[1]"))
            cmds.setAttr(mm + ".matrixIn[1]", list(m1 * d.inverse()), type="matrix")
    return max(_angle(_wmat(c), R) for c, R in frames.items()) if frames else 0.0


def _as_drawing_frame(control):
    """The frame AS drew a control's curve in: the deformation joint for an FK control, the
    node above the CustomOrient (IKOffset*) -- or the control's own parent when there is none -- for an IK one."""
    if control.startswith("IK"):
        k = "CustomOrient" + control
        return cmds.listRelatives(k if cmds.objExists(k) else control, p=True)[0]
    return control[2:]


def _turn_cvs(control, m):
    for s in cmds.listRelatives(control, s=True, type="nurbsCurve", fullPath=True) or []:
        sl = om.MSelectionList()
        sl.add(s)
        fn = om.MFnNurbsCurve(sl.getDagPath(0))
        fn.setCVPositions(om.MPointArray([om.MPoint(pt) * m for pt in fn.cvPositions(om.MSpace.kObject)]), om.MSpace.kObject)
        fn.updateCurve()


def frame_controls(frames):
    """Give each control in `frames` ({control: world rotation matrix}) that frame, and redraw
    its curve axis-aligned in the new frame.  The rest of the rig keeps its frames.

    The same Detach / set / Attach as orient_controls, for a chosen few: the standing shape
    alignment is undone first (a CustomOrient on the control means align_shapes ran on it),
    the arm pole's follow offset is compensated, and the curve is re-aligned on the nearest
    signed permutation of AS's drawing axes -- identity when no axis dominates.  Returns the
    worst angle left between a control and its asked frame.
    """
    drawing = dict((c, _rot(_wmat(_as_drawing_frame(c))).asMatrix()) for c in frames)
    for c in frames:
        if cmds.objExists("CustomOrient" + c):
            perm = _nearest_perm(drawing[c] * _rot(_wmat(c)).asMatrix().inverse())
            if perm is not None:
                _turn_cvs(c, perm.transpose())
    w_old = dict((c, _wmat(c)) for c in frames if c.startswith("IKArm"))
    mel.eval("asControlOrientDetach;")
    for c, R in frames.items():
        Pr = _rot(om.MMatrix(cmds.getAttr(c + ".parentMatrix[0]"))).asMatrix()
        _set_rot(c, R * Pr.inverse())
    cmds.checkBox("asControlOrientAttachMirrorCheckBox", e=True, v=0)
    mel.eval("asControlOrientAttach;")
    for c in w_old:
        mm = "PoleOffsetArmMMArm_" + c[-1]
        if cmds.objExists(mm):
            d = _wmat(c) * w_old[c].inverse()
            m1 = om.MMatrix(cmds.getAttr(mm + ".matrixIn[1]"))
            cmds.setAttr(mm + ".matrixIn[1]", list(m1 * d.inverse()), type="matrix")
    for c in frames:
        perm = _nearest_perm(drawing[c] * _rot(_wmat(c)).asMatrix().inverse())
        if perm is not None:
            _turn_cvs(c, perm)
    return max(_angle(_wmat(c), R) for c, R in frames.items())


# The hand frame the animator asked for (2026-09-05, «locator10 - для правой руки, locator9 - для
# левой»): X along the fingers, Z the palm normal, 29.3 deg off the hand BONE's frame (whose X
# points at the middle finger's root, not along the fingers) and 7.9 deg off AS's wrist.
# Rows = the frame's axes in the hand bone's own coordinates; the same numbers on both sides,
# because the animator mirrored the locator the way the skeleton mirrors its joints.
HAND_LOCATORS = {"_R": "locator10", "_L": "locator9"}
# Per side, because the animator's left locator was not the exact mirror of the right one
# (0.16 deg apart) and the rig carries what each locator gave; a fresh run reproduces both.
HAND_FRAME_IN_BONE = {
    "_R": [0.873138, -0.440331, 0.209138, 0.0,     # locator10 against Right_Hand, 2026-09-05
           0.448993, 0.893510, 0.006729, 0.0,
           -0.189830, 0.088026, 0.977863, 0.0,
           0.0, 0.0, 0.0, 1.0],
    "_L": [0.873199, -0.440355, 0.208831, 0.0,     # locator9 against Left_Hand, 2026-09-05
           0.449502, 0.893270, 0.004080, 0.0,
           -0.188339, 0.090308, 0.977943, 0.0,
           0.0, 0.0, 0.0, 1.0]}


def hand_frames():
    """{control: world rotation} for IKArm/FKWrist on both sides -- from the animator's hint
    locators when they are in the scene, else from the recorded HAND_FRAME_IN_BONE."""
    game = game_joints()
    out = {}
    for suffix, loc in HAND_LOCATORS.items():
        bone = game[SIDE[suffix] + "Hand"]
        if cmds.objExists(loc):
            R = _rot(_wmat(loc)).asMatrix()
        else:
            R = om.MMatrix(HAND_FRAME_IN_BONE[suffix]) * _rot(_wmat(bone)).asMatrix()
        for c in ("IKArm" + suffix, "FKWrist" + suffix):
            if cmds.objExists(c):
                out[c] = R
    return out


def _nearest_perm(m):
    """The signed axis permutation closest to rotation m, or None when no row has a dominant axis."""
    perm = om.MMatrix()
    used = []
    for i in range(3):
        r = _row(m, i)
        j = max(range(3), key=lambda k: abs(r[k]))
        if abs(r[j]) < 0.7 or j in used:
            return None
        used.append(j)
        for k in range(3):
            perm.setElement(i, k, (1.0 if r[j] >= 0 else -1.0) if k == j else 0.0)
    return perm


def align_shapes():
    """Redraw every custom-oriented control's curve axis-aligned in its own (= bone) frame.

    Turning a control's frame turns its drawing with it; the Manny rule (see that spec) is to
    put the extents on the nearest signed permutation of the frame AS drew in -- identity when
    no axis dominates, e.g. the IK hand cube.  Run once, right after Attach.
    """
    n = 0
    for c in cmds.sets("ControlSet", q=True):
        k = "CustomOrient" + c
        if not cmds.objExists(k):
            continue
        as_frame = cmds.listRelatives(k, p=True)[0] if c.startswith("IK") else c[2:]   # IKOffset*, or the deform joint
        if not cmds.objExists(as_frame):
            continue
        m = _rot(_wmat(as_frame)).asMatrix() * _rot(_wmat(c)).asMatrix().inverse()
        perm = _nearest_perm(m) or om.MMatrix()
        for s in cmds.listRelatives(c, s=True, type="nurbsCurve", fullPath=True) or []:
            sl = om.MSelectionList()
            sl.add(s)
            fn = om.MFnNurbsCurve(sl.getDagPath(0))
            fn.setCVPositions(om.MPointArray([om.MPoint(pt) * perm for pt in fn.cvPositions(om.MSpace.kObject)]), om.MSpace.kObject)
            fn.updateCurve()
            n += 1
    return n


def finger_sdk_axes(signs=None):
    """Frame the finger curl/spread SDK groups on the bones' own axes.

    The Fingers curl/spread set-driven keys drive the `SDKFK*` groups, which sit ABOVE
    `CustomOrient` and so keep AS's axes after a control re-orient.  On this skeleton the
    knuckle line (index -> pinky) is a phalanx's local Y and the palm normal its local Z --
    measured, both hands -- so AS's curl channel (`rotateY`) wants the bone's Y and its
    spread channel (`rotateZ`) the bone's Z: the group's frame is the bone's frame itself.
    `signs` maps a side suffix to (y sign, z sign); flipping y reverses that hand's curl,
    flipping z its spread, and x follows as y cross z so the frame stays a rotation.
    Measured 2026-09-05: (1, 1) on both hands is right (`calibrate_finger_axes`).
    Idempotent: an existing axis node is re-framed.  The CustomOrient below is recomputed
    so nothing moves at rest.
    """
    signs = dict(signs or {})
    table = dict((d.split("|")[-1], g) for d, g in mapping().items())
    n = 0
    for g in sorted(cmds.ls("SDKFK*", type="transform")):
        bone = table.get(g[len("SDKFK"):])
        if not bone:
            continue
        parent = cmds.listRelatives(g, p=True)[0]
        kids = dict((k, _wmat(k)) for k in (cmds.listRelatives(g, c=True, type="transform") or []))
        ys, zs = signs.get(g[-2:], (1.0, 1.0))
        b = _rot(_wmat(bone)).asMatrix()
        y, z = _row(b, 1) * ys, _row(b, 2) * zs
        x = y ^ z
        d = om.MMatrix()
        for r, v in enumerate((x, y, z)):
            for col in range(3):
                d.setElement(r, col, v[col])
        if parent.startswith(SDK_AXIS):
            node = parent
        else:
            node = cmds.createNode("transform", n=SDK_AXIS + g, p=parent)
            cmds.addAttr(node, ln="sdkAxisFor", dt="string")
            cmds.setAttr(node + ".sdkAxisFor", bone.split("|")[-1], type="string")
            cmds.parent(g, node, r=True)
        grand = cmds.listRelatives(node, p=True)[0]
        _set_rot(node, d * _rot(_wmat(grand)).asMatrix().inverse())
        gw = _wmat(g)
        for k, kw in kids.items():
            _set_local(k, kw * gw.inverse())
        n += 1
    return n


def finger_probe(side):
    """(curl, spread) for one hand: how far +5 indexCurl moves the index tip TOWARD THE PALM,
    and how much +5 spread widens the index-pinky gap.  Both should be positive.

    The palm side is the side of the hand plane the thumb sits on -- a cross product alone
    points to the palm on one hand and to the back of the other, which is how the first
    probe misread the left hand.  Leaves the Fingers attributes at 0.
    """
    game = game_joints()
    pre = SIDE["_" + side]
    W = lambda n: _pos(game[pre + n])
    f = "Fingers_" + side
    hand, f1, pk, thumb = W("Hand"), W("Finger1"), W("Pinky1"), W("Thumb1")
    n = ((f1 - hand) ^ (pk - hand)).normal()
    if (thumb - hand) * n < 0:
        n = -n
    tip0, gap0 = W("Finger3"), (W("Finger3") - W("Pinky3")).length()
    try:
        cmds.setAttr(f + ".indexCurl", 5)
        cmds.dgdirty(allPlugs=True)
        curl = (W("Finger3") - tip0) * n
        cmds.setAttr(f + ".indexCurl", 0)
        cmds.setAttr(f + ".spread", 5)
        cmds.dgdirty(allPlugs=True)
        spread = (W("Finger3") - W("Pinky3")).length() - gap0
    finally:
        cmds.setAttr(f + ".indexCurl", 0)
        cmds.setAttr(f + ".spread", 0)
        cmds.dgdirty(allPlugs=True)
    return curl, spread


def calibrate_finger_axes():
    """Frame the SDK groups on the bones, measure each hand, flip whichever axis sends a channel the wrong way.

    Returns ({side: (y sign, z sign)}, {side: (curl, spread) after}).
    """
    finger_sdk_axes()
    signs = {}
    for side in "RL":
        if cmds.objExists("Fingers_" + side):
            curl, spread = finger_probe(side)
            signs["_" + side] = (1.0 if curl > 0 else -1.0, 1.0 if spread > 0 else -1.0)
    finger_sdk_axes(signs)
    return signs, dict((s, finger_probe(s[1])) for s in signs)


def skeleton_layer():
    """The game skeleton in a visible layer of its own."""
    root = game_root()
    joints = [root] + (cmds.listRelatives(root, allDescendents=True, type="joint", fullPath=True) or [])
    if not cmds.objExists(LAYER):
        cmds.createDisplayLayer(name=LAYER, empty=True)
    cmds.editDisplayLayerMembers(LAYER, joints, noRecurse=True)
    return len(joints)


def as_skeleton_layer():
    """AS's deformation skeleton in a HIDDEN layer.

    It is drawn exactly on the game bones with axes of its own (Ankle_R 64 deg, Wrist_R 34 deg,
    Head_M 85 deg off the game joints' frames), so a click on "the bone" in the viewport landed
    on it and its axes were read as the bone's.  Only the game skeleton stays visible.
    """
    joints = cmds.listRelatives("DeformationSystem", allDescendents=True, type="joint", fullPath=True) or []
    if not cmds.objExists(AS_LAYER):
        cmds.createDisplayLayer(name=AS_LAYER, empty=True)
    cmds.editDisplayLayerMembers(AS_LAYER, joints, noRecurse=True)
    cmds.setAttr(AS_LAYER + ".visibility", 0)
    return len(joints)


def backup(tag):
    """Export the whole scene as .mb into the project's scenes folder (the open file is an FBX)."""
    scenes = os.path.join(cmds.workspace(q=True, rootDirectory=True), "scenes")
    if not os.path.isdir(scenes):
        os.makedirs(scenes)
    stem = os.path.splitext(os.path.basename(cmds.file(q=True, sceneName=True) or "scene"))[0]
    path = os.path.join(scenes, "%s_%s_%s.mb" % (stem, tag, time.strftime("%Y%m%d_%H%M"))).replace("\\", "/")
    cmds.file(path, exportAll=True, type="mayaBinary", force=True, preserveReferences=True)
    return path


def run():
    state = {"autoKey": cmds.autoKeyframe(q=True, st=True), "em": cmds.evaluationManager(q=True, mode=True)[0]}
    cmds.autoKeyframe(st=False)
    cmds.evaluationManager(mode="off")
    try:
        ensure_as_ui()
        joints = list(game_joints().values())
        rest = dict((j, cmds.getAttr(j + ".worldMatrix[0]")) for j in joints)
        print("// backup: %s" % backup("before_AdvancedSkeleton"))
        print("// hold: %d joints renamed" % hold())
        placed, worst = fit()
        print("// fit: %d joints placed, worst %.6f from its bone" % (placed, worst))
        print("// build: %.1f s" % build())
        print("// constraints: %d" % constrain())
        n, worst = orient_controls()
        shapes = align_shapes()
        signs, probes = calibrate_finger_axes()
        print("// %d controls oriented (worst frame angle %.5f deg), %d curves aligned, finger axes %s -> curl/spread %s"
              % (n, worst, shapes, signs, probes))
        print("// hand frames (IKArm, FKWrist) on the animator's frame: worst %.6f deg" % frame_controls(hand_frames()))
        print("// release: %d names given back" % release())
        # the names are back, so the pre-build paths resolve again
        drift = max(max(abs(a - b) for a, b in zip(m, cmds.getAttr(j + ".worldMatrix[0]"))) for j, m in rest.items())
        print("// bind-pose drift %.9f" % drift)
        print("// skeleton layer: %d joints; AS deformation skeleton hidden: %d joints" % (skeleton_layer(), as_skeleton_layer()))
    finally:
        cmds.evaluationManager(mode=state["em"])
        cmds.autoKeyframe(st=state["autoKey"])


if __name__ == "__main__":
    run()
