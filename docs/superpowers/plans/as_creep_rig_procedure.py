"""AdvancedSkeleton rig over the Creep creature's UE5-schema skeleton -- the procedure.

(Named the Hunter -- and in the morning Hanter -- until 2026-09-24; the animator renamed it
Creep that night.  The animator's own source scenes keep the old names: their group `|Hunter` /
`|Hanter`, the layer `Hanter_Skeleton`, the props `Hunter_Sword` / `Hunter_Sword_Low`.)

The Manny procedure (`as_ue5_rig_procedure.py`, 2026-09-04) applied to a skeleton with
Manny's bone NAMES and a creature's proportions: arms 34.8 + 36.0 cm against Manny's
27.8 + 27.3, a neck 7.3 + 7.8 against 5.1 + 4.9, the same legs (43.34 against 43.35).
Built 2026-09-24 in the animator's scene `creep_T-pose_MIX_06_skin.mb`, after the
skeleton's joint scales were removed and its bind pose was re-baked into the UE A-pose
(clavicle, upperarm and lowerarm on the UE bind; the hand keeps its own turn).  The same night
the bind became the pose of the animator's SKM_Manny_Simple (`rebind_creep_pose.py`) and the
rig was rebuilt on it by `rebuild_creep_rig.py`, which runs this module's steps -- the fit puts
every fit joint on its bone, so the rig's build pose is whatever pose the skeleton stands in.

What differs from the Manny procedure, and why:

- **Everything is addressed by LONG PATH.** The scene holds a second skeleton with the
  very same bone names (the UE reference Manny at `|root`), so `cmds.xform("hand_r")`
  and the vendor's Name Matcher (which takes a top node by short name) are ambiguous.
  `bones()` is the one lookup: {UE leaf: long path under the Creep's root}.  The
  constraints are written here, point + orient + scale with maintainOffset -- what the
  vendor's "Constraint to Joints" writes -- as the PlayerMale procedure does.
- **The fit skeleton is put on the bones, all of them**, not only where UE5.ma is off
  (it is authored on Manny, and this is not Manny).  The fit's end joints, which have no
  bone, are placed from the chain: a finger tip continues its last phalanx by the
  preset's own tip/phalanx ratio, HeadEnd sits on the top of the head mesh.
- **The bones take ORIENTATION only** (the pelvis its position too): the Creep keeps its
  own bone lengths rigidly -- see `constrain()` for the measurement that decided it.
- **The IK FOOT controls stand level**, in AdvancedSkeleton's own world frame, drawing and
  axes both (`as_frames(LEVEL_CONTROLS)`, the animator's ask after seeing the rig); every
  other control carries its bone's frame, as on Manny.  `align_ik_target` then turns
  `AlignIKToAnkle_*` onto them, which Attach skips for a control without a CustomOrient.
- The rig is MARKED for the retarget: `Group.skeldarRetarget = "rotation"` -- the
  Creep's retarget copies rotations only (`maya_asretarget`, the animator's rule
  2026-09-24: «ретаргет не должен учитывать растяжение костей»).

Run in a scene holding the Creep skeleton and no AdvancedSkeleton rig (leftover AS
utility nodes from a deleted rig must be removed first -- a new build would get their
names uniquified).  Disables autoKey and switches the evaluation manager to DG while it
works, and puts both back.
"""
import math
import os
import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

AS_MEL = "C:/Users/MY PC/Downloads/AdvancedSkeleton/AdvancedSkeleton.mel"
ROOT = "|Hunter|root"               # the group was renamed from Hanter the same day; bones() finds it either way
HEAD_MESH = "faceShape"
RETARGET_ATTR = "skeldarRetarget"
RETARGET_MODE = "rotation"
LAYER = "Creep_Skeleton"            # renamed from Hanter_Skeleton by tidy()

ROWS = [("Root", "pelvis"), ("Spine1", "spine_01"), ("Spine2", "spine_02"), ("Spine3", "spine_03"), ("Spine4", "spine_04"),
        ("Spine5", "spine_05"), ("Scapula", "clavicle"), ("Shoulder", "upperarm"), ("Elbow", "lowerarm"), ("Wrist", "hand"),
        ("IndexFinger0", "index_metacarpal"), ("IndexFinger1", "index_01"), ("IndexFinger2", "index_02"), ("IndexFinger3", "index_03"),
        ("MiddleFinger0", "middle_metacarpal"), ("MiddleFinger1", "middle_01"), ("MiddleFinger2", "middle_02"), ("MiddleFinger3", "middle_03"),
        ("RingFinger0", "ring_metacarpal"), ("RingFinger1", "ring_01"), ("RingFinger2", "ring_02"), ("RingFinger3", "ring_03"),
        ("PinkyFinger0", "pinky_metacarpal"), ("PinkyFinger1", "pinky_01"), ("PinkyFinger2", "pinky_02"), ("PinkyFinger3", "pinky_03"),
        ("ThumbFinger1", "thumb_01"), ("ThumbFinger2", "thumb_02"), ("ThumbFinger3", "thumb_03"),
        ("Neck", "neck_01"), ("Head", "head"), ("Hip", "thigh"), ("Knee", "calf"), ("Ankle", "foot"), ("Toes", "ball")]
PART_ROWS = [("ShoulderPart1", "upperarm_twist_01"), ("ShoulderPart2", "upperarm_twist_02"),
             ("ElbowPart1", "lowerarm_twist_02"), ("ElbowPart2", "lowerarm_twist_01"),
             ("HipPart1", "thigh_twist_01"), ("HipPart2", "thigh_twist_02"),
             ("KneePart1", "calf_twist_02"), ("KneePart2", "calf_twist_01"), ("NeckPart1", "neck_02")]
EXTRAS = [("Main", "root"), ("foot_l", "ik_foot_l"), ("foot_r", "ik_foot_r")]
# The hand helpers, the animator's layout (2026-09-24): ik_hand_r / ik_hand_l stand EXACTLY on their
# hands and follow them with no offset; ik_hand_gun (their parent) is not driven and stays at zero.
# The T-pose file had them where a Manny's hands would be, 15-55 cm off the Creep's.
IK_HANDS = [("hand_r", "ik_hand_r"), ("hand_l", "ik_hand_l")]
IK_GUN = "ik_hand_gun"
IK_END = [("IKLeg_L", "foot_l"), ("IKLeg_R", "foot_r"), ("IKArm_L", "hand_l"), ("IKArm_R", "hand_r"),
          ("IKToes_L", "ball_l"), ("IKToes_R", "ball_r")]
FINGERS = ("Index", "Middle", "Ring", "Pinky", "Thumb")


def skeleton_root():
    """The Creep's `root`: the one top joint named root with a pelvis under it, outside any rig.

    Found rather than written down: the animator renamed the group Hanter -> Hunter while the
    rig was being prepared, and a second UE skeleton may or may not stand in the scene."""
    found = []
    for j in cmds.ls("root", type="joint", long=True) or []:
        parent = cmds.listRelatives(j, parent=True, fullPath=True)
        if parent and cmds.nodeType(parent[0]) == "joint":
            continue
        if any(p.split("|")[-1] == "pelvis" for p in cmds.listRelatives(j, children=True, fullPath=True) or []) \
                and "|Group|" not in j:
            found.append(j)
    creep = [j for j in found if j.split("|")[1] in ("Creep", "Hunter", "Hanter")]
    if len(creep) == 1:
        return creep[0]
    # since the tidy the root stands at world level, driven by Main
    driven = [j for j in found if "Main" in [x.split("|")[-1].split(":")[-1]
              for c in cmds.listRelatives(j, children=True, type="parentConstraint", fullPath=True) or []
              for x in cmds.listConnections(c + ".target[0].targetParentMatrix", s=True, d=False) or []]]
    if len(driven) == 1:
        return driven[0]
    if len(found) == 1:
        return found[0]
    raise RuntimeError("expected one Creep skeleton, found %s" % found)


def bones():
    """{UE leaf: long path} of the Creep skeleton -- the one lookup; short names may be ambiguous."""
    root = ROOT if cmds.objExists(ROOT) else skeleton_root()
    paths = [root] + (cmds.listRelatives(root, allDescendents=True, type="joint", fullPath=True) or [])
    return dict((p.split("|")[-1], p) for p in paths)


def _wmat(n):
    return om.MMatrix(cmds.getAttr(n + ".worldMatrix[0]"))


def _pos(n):
    return om.MVector(cmds.xform(n, q=True, ws=True, t=True))


def _rot(m):
    return om.MTransformationMatrix(m).rotation(asQuaternion=True)


def _set_rot(node, rmat):
    tm = om.MTransformationMatrix(rmat)
    tm.reorderRotation(cmds.getAttr(node + ".rotateOrder") + 1)
    e = tm.rotation(asQuaternion=False)
    cmds.setAttr(node + ".rotate", math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))


def _set_local(node, local):
    tm = om.MTransformationMatrix(local)
    tm.reorderRotation(cmds.getAttr(node + ".rotateOrder") + 1)
    e = tm.rotation(asQuaternion=False)
    t = tm.translation(om.MSpace.kTransform)
    cmds.setAttr(node + ".translate", t.x, t.y, t.z)
    cmds.setAttr(node + ".rotate", math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))


def _row(m, i):
    return om.MVector(m.getElement(i, 0), m.getElement(i, 1), m.getElement(i, 2))


def ensure_as_ui():
    if mel.eval('whatIs "asReBuildAdvancedSkeleton"') == "Unknown":
        mel.eval('source "%s";' % AS_MEL)
    if not cmds.optionMenu("asFitFiles", exists=True):
        mel.eval("AdvancedSkeleton;")


def fit_joints():
    tops = cmds.ls("FitSkeleton", long=True) or []
    if len(tops) != 1:
        raise RuntimeError("expected one FitSkeleton, found %s" % tops)
    return dict((j.split("|")[-1], j) for j in cmds.listRelatives(tops[0], allDescendents=True, type="joint", fullPath=True) or [])


def _snap(path, pos):
    """xform a fit joint in world space, through any locks on its translate channels."""
    locked = [a for a in ("tx", "ty", "tz") if cmds.getAttr(path + "." + a, lock=True)]
    for a in locked:
        cmds.setAttr(path + "." + a, lock=False)
    cmds.xform(path, ws=True, t=(pos.x, pos.y, pos.z))
    for a in locked:
        cmds.setAttr(path + "." + a, lock=True)


NONSYM = "_NonSymmetry"


def _target(fit_leaf, b):
    """The Creep bone a fit joint sits on: middle joints plain, the fit's side is the RIGHT one,
    and its `_NonSymmetry` copy (AdvancedSkeleton's own un-mirrored left side) the LEFT one."""
    left = fit_leaf.endswith(NONSYM)
    row = dict(ROWS).get(fit_leaf[:-len(NONSYM)] if left else fit_leaf)
    if row is None:
        return None
    return b.get(row) or b.get(row + ("_l" if left else "_r"))


def fit(heel_y=0.0):
    """Import UE5.ma, give it the Creep's twist/in-between shape and put every joint on its bone.

    Returns (fit joints placed, worst mapped-joint distance from its bone)."""
    if cmds.objExists("|FitSkeleton") or cmds.objExists("Group"):
        raise RuntimeError("a FitSkeleton or an AdvancedSkeleton rig already exists")
    for n in ("Group", "Main", "MotionSystem", "DeformationSystem", "Geometry"):
        if cmds.objExists(n):
            raise RuntimeError("%s already exists; the build needs the name" % n)
    b = bones()
    ensure_as_ui()
    cmds.optionMenu("asFitFiles", e=True, v="UE5.ma")
    guard = cmds.createNode("transform", n="FitSkeletonNameMatcherImporting")
    try:
        mel.eval("asFitSkeletonImport;")
    finally:
        if cmds.objExists(guard):
            cmds.delete(guard)
    fj = fit_joints()
    for n in ("Eye", "Jaw"):
        if n in fj and cmds.objExists(fj[n]):
            cmds.delete(fj[n])
    fj = fit_joints()
    knee = fj["Knee"]
    if not cmds.attributeQuery("twistJoints", node=knee, exists=True):
        cmds.addAttr(knee, k=True, ln="twistJoints", at="long", min=0, dv=2)
        cmds.addAttr(knee, k=True, ln="bendyCtrls", at="long", min=0, dv=0)
    cmds.setAttr(fj["Neck"] + ".inbetweenJoints", 1)
    if _pos(fj["Shoulder"]).x > 0:
        raise RuntimeError("the fit skeleton's side is on +X; this procedure expects the right side on -X")
    # AdvancedSkeleton builds the LEFT side as the mirror of the right fit.  The Creep's pose is
    # not symmetric (2026-09-24: SKM_Manny_Simple's fingers bend differently on each hand, 1-3 cm),
    # so the left side gets its own chain -- the vendor's "create non-symmetry joints": every side
    # chain under a middle joint mirrored into `<joint>_NonSymmetry` fit joints (noMirror on the
    # right) that the build turns into the `_L` joints, fitted onto the LEFT bones.
    mel.eval("asCreateNonSymmetryJoints;")
    fj = fit_joints()
    if not any(k.endswith(NONSYM) for k in fj):
        raise RuntimeError("asCreateNonSymmetryJoints made no _NonSymmetry fit joints")
    for leaf in [k for k in fj if not k.endswith(NONSYM) and k + NONSYM in fj]:   # the Knee's twists, above
        for attr in ("twistJoints", "bendyCtrls", "inbetweenJoints"):
            if cmds.attributeQuery(attr, node=fj[leaf], exists=True):
                other = fj[leaf + NONSYM]
                if not cmds.attributeQuery(attr, node=other, exists=True):
                    cmds.addAttr(other, k=True, ln=attr, at="long", min=0, dv=0)
                cmds.setAttr(other + "." + attr, cmds.getAttr(fj[leaf] + "." + attr))
    sides = [""] + ([NONSYM] if "Shoulder" + NONSYM in fj else [])
    # the preset's own tip-to-last-phalanx ratios, read before anything moves
    tip = {}
    for f in FINGERS:
        for sd in sides:
            j2, j3, j4 = (_pos(fj["%sFinger%d%s" % (f, i, sd)]) for i in (2, 3, 4))
            tip[f + sd] = (j4 - j3).length() / max((j3 - j2).length(), 1e-6)
    heel_off = dict((sd, _pos(fj["Heel" + sd]) - _pos(fj["Ankle" + sd])) for sd in sides)
    placed = 0
    for path in sorted(fj.values(), key=lambda p: p.count("|")):      # parents first: a move carries the children
        leaf = path.split("|")[-1]
        bone = _target(leaf, b)
        if bone:
            _snap(path, _pos(bone))
            placed += 1
    fj = fit_joints()
    for f in FINGERS:                                                  # a tip continues its last phalanx
        for sd in sides:
            j2, j3 = _pos(fj["%sFinger2%s" % (f, sd)]), _pos(fj["%sFinger3%s" % (f, sd)])
            _snap(fj["%sFinger4%s" % (f, sd)], j3 + (j3 - j2) * tip[f + sd])
            placed += 1
    head = _pos(b["head"])
    sel = om.MSelectionList(); sel.add(HEAD_MESH)
    top = max(p.y for p in om.MFnMesh(sel.getDagPath(0)).getPoints(om.MSpace.kWorld))
    _snap(fj["HeadEnd"], om.MVector(head.x, top, head.z))
    for sd in sides:
        heel = _pos(fj["Ankle" + sd]) + heel_off[sd]
        _snap(fj["Heel" + sd], om.MVector(heel.x, heel_y, heel.z))
    placed += 1 + len(sides)
    mel.eval("asFitModeManualUpdate;")
    fj = fit_joints()
    worst = max((_pos(fj[leaf]) - _pos(_target(leaf, b))).length() for leaf in fj if _target(leaf, b))
    return placed, worst


def build():
    mel.eval("asReBuildAdvancedSkeleton;")
    if not (cmds.objExists("Group") and cmds.objExists("DeformSet")):
        raise RuntimeError("the build did not complete")


# the twist segments: (AS joint, the game segment's start and end, its twist bones nearest the
# start first, the AS child joint the last Part carries)
TWIST_SEGMENTS = [("Shoulder", "upperarm", "lowerarm", ("upperarm_twist_01", "upperarm_twist_02"), "Elbow"),
                  ("Elbow", "lowerarm", "hand", ("lowerarm_twist_02", "lowerarm_twist_01"), "Wrist"),
                  ("Hip", "thigh", "calf", ("thigh_twist_01", "thigh_twist_02"), "Knee"),
                  ("Knee", "calf", "foot", ("calf_twist_02", "calf_twist_01"), "Ankle")]


def _settle():
    t = cmds.currentTime(q=True)
    cmds.currentTime(t + 1)
    cmds.currentTime(t)


def place_parts():
    """AdvancedSkeleton's twist and in-between joints onto the Creep's own twist bones.  At the build pose.

    AS spaces a segment's Part joints evenly -- `<joint>PartBM<side>` blends the joint's world matrix
    toward the child's by 1/(n+1), and every Part takes that same step -- while the Creep's upper-arm
    twists stand at 0.266 and 0.532 of the bone (measured 2026-09-24: 2.35 / 4.70 cm off, both sides,
    in every build since the first).  Where the game twists are evenly stepped too, the BM weight takes
    their step and the child joint (whose translate is static) is put back where it was.  The neck
    in-between `NeckPart1_M` is point-constrained by AS onto the line neck->head, and neck_02 stands off
    it: its constraint's offset (in Neck_M's space, the frame neck_02 is rigid in) moves it on.  The
    Creep's bones take orientation only, so none of this moves the skeleton; it is so that the rig's
    joints stand ON the skeleton's.  Returns {what: worst distance left}."""
    b = bones()
    done = {}
    for asj, start, end, twists, child in TWIST_SEGMENTS:
        for S, s in (("_R", "_r"), ("_L", "_l")):
            bm = "%sPartBM%s" % (asj, S)
            if not cmds.objExists(bm) or not all(t + s in b for t in twists):
                continue
            A, E = _pos(b[start + s]), _pos(b[end + s])
            L = E - A
            fr = [((_pos(b[t + s]) - A) * L) / (L * L) for t in twists]
            step = fr[0]
            if any(abs(f - step * (i + 1)) > 1e-3 for i, f in enumerate(fr)):
                raise RuntimeError("%s: the twist bones are not evenly stepped (%s) -- one BM weight cannot place them"
                                   % (start + s, ["%.4f" % f for f in fr]))
            if abs(cmds.getAttr(bm + ".target[0].weight") - step) > 1e-6:
                # the child (Elbow, Wrist, Knee, Ankle) is point-constrained by AS onto its FK/IK
                # twin, so it holds its place under the moved Part by itself (measured 2026-09-24);
                # a static child is put back by hand, a driven one that moved is refused
                c = child + S
                keep = _pos(c)
                cmds.setAttr(bm + ".target[0].weight", step)
                _settle()
                if (_pos(c) - keep).length() > 1e-4:
                    if any(cmds.listConnections("%s.%s" % (c, a), s=True, d=False) for a in ("tx", "ty", "tz")):
                        raise RuntimeError("%s moved with the Part step and its translate is driven" % c)
                    local = om.MPoint(keep) * _wmat(cmds.listRelatives(c, p=True, fullPath=True)[0]).inverse()
                    cmds.setAttr(c + ".translate", local.x, local.y, local.z)
                    _settle()
                if (_pos(c) - keep).length() > 1e-4:
                    raise RuntimeError("%s did not keep its place under the Part step" % c)
            done[asj + S] = max((_pos("%sPart%d%s" % (asj, i + 1, S)) - _pos(b[t + s])).length() for i, t in enumerate(twists))
    pc = "NeckPart1_M_pointConstraint1"
    if cmds.objExists(pc) and "neck_02" in b:
        parent = _wmat(cmds.listRelatives("NeckPart1_M", p=True, fullPath=True)[0]).inverse()
        goal = om.MPoint(_pos(b["neck_02"])) * parent
        now = om.MPoint(_pos("NeckPart1_M")) * parent
        off = om.MVector(cmds.getAttr(pc + ".offset")[0]) + (goal - now)
        cmds.setAttr(pc + ".offset", off.x, off.y, off.z)
        _settle()
        done["NeckPart1_M"] = (_pos("NeckPart1_M") - _pos(b["neck_02"])).length()
    return done


def mapping():
    """{AS deformation joint (short, unique): Creep bone long path}."""
    b = bones()
    out = {}
    for a, ue in ROWS + PART_ROWS:
        for side, s in (("_M", ""), ("_R", "_r"), ("_L", "_l")):
            if cmds.objExists(a + side) and cmds.nodeType(a + side) == "joint" and (ue + s) in b:
                out[a + side] = b[ue + s]
    return out


POSITIONED = ("pelvis",)          # the one deformation bone that takes AS's POSITION as well


def constrain():
    """Every Creep bone takes its AS twin's ORIENTATION (maintainOffset), by long path; the pelvis also
    its position; root follows Main and the ik_* helpers the hands and feet.

    Not the vendor's point + orient + scale (the Manny rig's): the Creep's bones keep their OWN
    lengths, rigidly (the animator's rule for this character, 2026-09-24).  Measured with point
    constraints: AS mirrors the left side from the right fit while the Creep is 0.045 cm asymmetric,
    and a -mo point constraint keeps that offset in the bone's PARENT space, so the left arm's
    lengths wandered 0.01-0.07 cm with the bends and neck_02->head sat 0.035 cm short (the
    in-between joint is not on the bone).  Orientation only: lengths exact on every frame, no
    translation keys below the pelvis in an export, and AS's own stretch never reaches the skeleton.
    """
    b = bones()
    made = 0
    for d, g in sorted(mapping().items()):
        if cmds.listRelatives(g, children=True, type="constraint"):
            continue
        if g.split("|")[-1] in POSITIONED:
            cmds.pointConstraint(d, g, maintainOffset=True)
            made += 1
        cmds.orientConstraint(d, g, maintainOffset=True)
        made += 1
    for src, dst in EXTRAS:
        src_path = "Main" if src == "Main" else b[src]
        if dst in b and not cmds.listRelatives(b[dst], children=True, type="constraint"):
            cmds.parentConstraint(src_path, b[dst], maintainOffset=True)
            made += 1
    return made + place_ik_helpers()


def _unscaled(m):
    rows = []
    for r in range(3):
        v = _row(m, r).normal()
        rows += [v.x, v.y, v.z, 0.0]
    return om.MMatrix(rows + [m.getElement(3, 0), m.getElement(3, 1), m.getElement(3, 2), 1.0])


def place_ik_helpers():
    """ik_hand_gun at zero and undriven; ik_hand_r / ik_hand_l exactly on the hands, following them.

    Run at the build pose.  These joints are skin influences with zero weight; their bindPreMatrix
    is re-expressed anyway (BPM' = BPM * WM_old * WM_new^-1) so every skin stays at its bind, and
    bindPose1 is reset for them.  Returns the constraints made."""
    b = bones()
    moved = [b[n] for n in [IK_GUN] + [h for _, h in IK_HANDS] if n in b]
    old = dict((j, _wmat(j)) for j in moved)
    for j in moved:
        for c in cmds.listRelatives(j, children=True, type="constraint", fullPath=True) or []:
            cmds.delete(c)
    if IK_GUN in b:
        cmds.setAttr(b[IK_GUN] + ".translate", 0, 0, 0)
        cmds.setAttr(b[IK_GUN] + ".rotate", 0, 0, 0)
    made = 0
    for hand, helper in IK_HANDS:
        if hand in b and helper in b:
            cmds.xform(b[helper], ws=True, matrix=list(_unscaled(_wmat(b[hand]))))
            cmds.parentConstraint(b[hand], b[helper], maintainOffset=False)
            made += 1
    for sc in cmds.ls(type="skinCluster"):
        for idx in cmds.getAttr(sc + ".matrix", multiIndices=True) or []:
            src = cmds.ls(cmds.listConnections("%s.matrix[%d]" % (sc, idx), s=True, d=False) or [], long=True)
            if src and src[0] in old:
                bpm = om.MMatrix(cmds.getAttr("%s.bindPreMatrix[%d]" % (sc, idx)))
                cmds.setAttr("%s.bindPreMatrix[%d]" % (sc, idx), list(bpm * old[src[0]] * _wmat(src[0]).inverse()), type="matrix")
    for pose in cmds.ls(type="dagPose"):
        members = [m for m in cmds.ls(cmds.dagPose(pose, q=True, members=True) or [], long=True) if m in old]
        if members and cmds.getAttr(pose + ".bindPose"):
            cmds.dagPose(members, reset=True, name=pose)
    return made


def orient_controls():
    """Every FK and IK-end control's frame becomes its bone's frame (the Manny procedure, by long path)."""
    b = bones()
    for mm in ("NeckInbetweenMM_M", "NeckPart1InbetweenMM_M"):
        if cmds.objExists(mm):
            cmds.connectAttr("FKOffsetNeck_M.worldInverseMatrix[0]", mm + ".matrixIn[1]", force=True)
    targets = [("FK" + asj, ue) for asj, ue in mapping().items()
               if asj != "Root_M" and not ("Part" in asj and not asj.startswith("NeckPart")) and cmds.objExists("FK" + asj)]
    targets += [(c, b[ue]) for c, ue in IK_END if cmds.objExists(c)]
    w_old = {c: _wmat(c) for c, _ in IK_END if cmds.objExists(c)}
    mel.eval("asControlOrientDetach;")
    for c, ue in targets:
        Rb = _rot(_wmat(ue)).asMatrix()
        Pr = _rot(om.MMatrix(cmds.getAttr(c + ".parentMatrix[0]"))).asMatrix()
        _set_rot(c, Rb * Pr.inverse())
    cmds.checkBox("asControlOrientAttachMirrorCheckBox", e=True, v=0)
    mel.eval("asControlOrientAttach;")
    for s in "LR":
        c, mm = "IKArm_%s" % s, "PoleOffsetArmMMArm_%s" % s
        if c in w_old and cmds.objExists(mm):
            d = _wmat(c) * w_old[c].inverse()
            m1 = om.MMatrix(cmds.getAttr(mm + ".matrixIn[1]"))
            cmds.setAttr(mm + ".matrixIn[1]", list(m1 * d.inverse()), type="matrix")
    worst = max(math.degrees(2 * math.acos(min(1.0, abs((_rot(_wmat(c)).inverse() * _rot(_wmat(ue))).w)))) for c, ue in targets)
    return len(targets), worst


def _nearest_perm(m):
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
    """Redraw every custom-oriented control's curve axis-aligned in its own frame (the Manny procedure)."""
    n = 0
    for c in cmds.sets("ControlSet", q=True):
        k = "CustomOrient" + c
        if not cmds.objExists(k):
            continue
        as_frame = cmds.listRelatives(k, p=True)[0] if c.startswith("IK") else c[2:]
        m = _rot(_wmat(as_frame)).asMatrix() * _rot(_wmat(c)).asMatrix().inverse()
        perm = _nearest_perm(m) or om.MMatrix()
        for s in cmds.listRelatives(c, s=True, type="nurbsCurve", fullPath=True) or []:
            sl = om.MSelectionList(); sl.add(s)
            fn = om.MFnNurbsCurve(sl.getDagPath(0))
            fn.setCVPositions(om.MPointArray([om.MPoint(pt) * perm for pt in fn.cvPositions(om.MSpace.kObject)]), om.MSpace.kObject)
            fn.updateCurve()
            n += 1
    return n


def finger_sdk_axes():
    """The Fingers curl/spread SDK groups re-framed on the bones: y = bone Z (curl), z = bone Y (spread)."""
    table = mapping()
    n = 0
    for g in sorted(cmds.ls("SDKFK*", type="transform")):
        ue = table.get(g[len("SDKFK"):])
        parent = cmds.listRelatives(g, p=True)[0]
        if not ue or parent.startswith("UEAxis"):
            continue
        kids = {k: _wmat(k) for k in (cmds.listRelatives(g, c=True, type="transform") or [])}
        bm = _rot(_wmat(ue)).asMatrix()
        y, z = _row(bm, 2), _row(bm, 1)
        x = y ^ z
        d = om.MMatrix()
        for r, v in enumerate((x, y, z)):
            for col in range(3):
                d.setElement(r, col, v[col])
        node = cmds.createNode("transform", n="UEAxis" + g, p=parent)
        cmds.addAttr(node, ln="ueAxisFor", dt="string")
        cmds.setAttr(node + ".ueAxisFor", ue.split("|")[-1], type="string")
        _set_rot(node, d * _rot(_wmat(parent)).asMatrix().inverse())
        cmds.parent(g, node, r=True)
        gw = _wmat(g)
        for k, kw in kids.items():
            _set_local(k, kw * gw.inverse())
        n += 1
    return n


def _angle(a, b):
    q = _rot(a).inverse() * _rot(b)
    return math.degrees(2 * math.acos(min(1.0, abs(q.w))))


def as_frames(controls):
    """Give controls AdvancedSkeleton's OWN orientation back -- the frame of the node above their
    CustomOrient (IKOffsetLeg_R: level, world-aligned) -- and AS's own drawing.

    The Creep's IK FOOT controls (2026-09-24, the animator, after seeing the rig: the leg
    controls stand a little tilted, taken from the foot bones' turn -- right in general, but here
    make them level, axes and drawing both).  The PlayerMale procedure's `as_frames`: the axis
    permutation align_shapes applied is undone while it is still known, then Detach / set /
    Attach; the arm pole's follow offset is compensated for an IKArm.  Nothing moves.  Returns
    the worst angle left between a control and AS's frame.
    """
    controls = [c for c in controls if cmds.objExists("CustomOrient" + c)]
    frames = {}
    for c in controls:
        k = "CustomOrient" + c
        as_frame = cmds.listRelatives(k, p=True)[0] if c.startswith("IK") else c[2:]
        frames[c] = _rot(_wmat(as_frame)).asMatrix()
        perm = _nearest_perm(frames[c] * _rot(_wmat(c)).asMatrix().inverse())
        if perm is not None:
            inv = perm.transpose()
            for s in cmds.listRelatives(c, s=True, type="nurbsCurve", fullPath=True) or []:
                sl = om.MSelectionList(); sl.add(s)
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
    for c in controls:
        align_ik_target(c)
    return max(_angle(_wmat(c), R) for c, R in frames.items()) if frames else 0.0


def align_ik_target(control):
    """Turn the FK->IK align target (AlignIKToAnkle_L, ...) onto the IK control, as Attach does.

    asControlOrientAttach re-orients `AlignIKTo<end><side>` -- `delete orientConstraint ctrl
    alignTo` -- only for a control that ends up custom-oriented.  A control put back on AS's
    own frame gets no CustomOrient, so its align target kept the bone-frame turn: measured
    2026-09-24, asAlignIK2FK then put IKLeg_L on the right place turned 117.93 deg (exactly
    the old frame's angle).  Run at the build pose.
    """
    side, name = control[-2:], control[2:-2]
    end = {"IKLeg": "Ankle", "IKArm": "Wrist"}.get(control[:-2])
    target = "AlignIKTo" + name + side if cmds.objExists("AlignIKTo" + name + side) else \
        ("AlignIKTo" + end + side if end else "")
    if target and cmds.objExists(target):
        cmds.delete(cmds.orientConstraint(control, target))


LEVEL_CONTROLS = ("IKLeg_L", "IKLeg_R")

# The shape the plugin ships (2026-09-24, the animator: «приведем все в порядок, назовем
# правильно и сгруппируем, чтобы геометрия не валялась непонятно где»): the skeleton at world
# level with the FBX wrapper's turn in root's jointOrient (Manny_Rig.ma's shape), the meshes
# named for the character in the rig's own Geometry group, the props out of the skeleton in
# Geometry|Creep_Props riding weapon_test by constraint (a mesh under a bone rides into every
# animation export).  The wrapper keeps only the Manny reference mesh and is renamed.
MESH_NAMES = {"body": "Creep_Body", "back": "Creep_Back", "arm_l": "Creep_Arm_L", "arm_r": "Creep_Arm_R",
              "face": "Creep_Face"}
PROP_NAMES = {"SwordPacked": "Hunter_Sword", "Sword_LowFBXASC046001": "Hunter_Sword_Low"}   # the source scene's names
PROP_BONE = "weapon_test"


def _rename_with_shapes(uuid, name):
    cmds.rename(cmds.ls(uuid, long=True)[0], name)
    for s in cmds.listRelatives(cmds.ls(uuid, long=True)[0], shapes=True, fullPath=True) or []:
        cmds.rename(s, name + ("ShapeOrig" if s.endswith("Orig") else "Shape"))


def tidy():
    """The shipped shape, at the build pose.  Everything is held by UUID: re-parenting the root
    invalidates every long path below it (CLAUDE.md trap 16 -- paid again on 2026-09-24).  Nothing
    moves: the joints keep their world matrices (their bindPreMatrix is untouched), the meshes go
    under an identity group, the props keep their world matrices under their constraint."""
    root = bones()["root"]
    wrapper = cmds.listRelatives(root, parent=True, fullPath=True)
    props = [cmds.ls(p, uuid=True)[0] for p in cmds.ls(list(PROP_NAMES), long=True, type="transform")]
    prop_names = dict((cmds.ls(p, uuid=True)[0], PROP_NAMES[p.split("|")[-1]]) for p in cmds.ls(list(PROP_NAMES), long=True, type="transform"))
    if wrapper:
        W = _wmat(root)
        root = cmds.ls(cmds.parent(root, world=True)[0], long=True)[0]
        e = om.MTransformationMatrix(W).rotation(asQuaternion=False)
        cmds.setAttr(root + ".jointOrient", math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))
        cmds.rename(wrapper[0], "Manny_Reference")
    geo = "|Group|Geometry"
    for old, new in MESH_NAMES.items():
        if cmds.objExists("|" + old):
            uid = cmds.ls("|" + old, uuid=True)[0]
            cmds.parent("|" + old, geo)
            _rename_with_shapes(uid, new)
    holder = geo + "|Creep_Props"
    if props and not cmds.objExists(holder):
        cmds.createNode("transform", name="Creep_Props", parent=geo)
    for uid in props:
        cmds.parent(cmds.ls(uid, long=True)[0], holder)
        _rename_with_shapes(uid, prop_names[uid])
        cmds.parentConstraint(bones()[PROP_BONE], cmds.ls(uid, long=True)[0], maintainOffset=True)
    if cmds.objExists("Hanter_Skeleton"):
        cmds.rename("Hanter_Skeleton", LAYER)
    cmds.dagPose(list(bones().values()), reset=True, name="bindPose1")


SWORD_MESH = "CreepSwordMesh"          # the catalog's weapons are LongSwordMesh, SpearMesh, DaggerMesh
SWORD_FBX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "SkeldarAnim", "assets", "Creep_Sword.fbx") if "__file__" in globals() else ""


def export_sword(target, source="Creep_Sword"):
    """The Creep's sword out of the rig as a catalog weapon: `assets/Creep_Sword.fbx`.

    The mesh is expressed in the frame weapon_r WILL have (`FLIP_Z` times weapon_test's; weapon_r's
    own once `weapon_bones` has run): the blade along +Y with the tip at +Y, the guard's width on X,
    the thickness on Z -- the sword's, spear's and dagger's convention -- and the origin where the
    Creep held it, so Add at zero grip puts it back exactly there.  Frozen, history deleted, a plain
    lambert (Add recolours anyway), exported alone.  Must run BEFORE `weapon_bones`: the sword rides
    its bone by constraint, and turning the bone first would turn the sword with it."""
    b = bones()
    bone = b.get("weapon_test")
    frame = FLIP_Z * _wmat(bone) if bone else _wmat(b["weapon_r"])
    src = [t for t in cmds.ls(source, "*:" + source, long=True, type="transform")][0]
    dup = cmds.duplicate(src, name=SWORD_MESH)[0]
    dup = cmds.ls(cmds.parent(dup, world=True)[0], long=True)[0]
    for c in cmds.listRelatives(dup, children=True, type="constraint", fullPath=True) or []:
        cmds.delete(c)
    for a in ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"):
        cmds.setAttr(dup + "." + a, lock=False)
    cmds.xform(dup, worldSpace=True, matrix=list(_wmat(src) * frame.inverse()))
    cmds.makeIdentity(dup, apply=True, translate=True, rotate=True, scale=True, normal=0)
    cmds.xform(dup, pivots=(0.0, 0.0, 0.0), objectSpace=True)
    cmds.delete(dup, constructionHistory=True)
    shape = cmds.listRelatives(dup, shapes=True, fullPath=True, noIntermediate=True)[0]
    mat = cmds.shadingNode("lambert", asShader=True, name="CreepSwordMat")
    cmds.setAttr(mat + ".color", 0.55, 0.55, 0.58, type="double3")
    sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name="CreepSwordMatSG")
    cmds.connectAttr(mat + ".outColor", sg + ".surfaceShader", force=True)
    cmds.sets(shape, edit=True, forceElement=sg)
    sel = om.MSelectionList(); sel.add(shape)
    pts = om.MFnMesh(sel.getDagPath(0)).getPoints(om.MSpace.kObject)
    ext = [(min(p[i] for p in pts), max(p[i] for p in pts)) for i in range(3)]
    if os.path.exists(target):
        os.remove(target)
    mel.eval("FBXResetExport")
    mel.eval("FBXExportInputConnections -v false")
    mel.eval("FBXExportSmoothingGroups -v true")
    mel.eval("FBXExportInAscii -v false")
    cmds.select(dup, replace=True)
    mel.eval('FBXExport -f "%s" -s' % target.replace("\\", "/"))
    cmds.delete(dup)
    for n in (mat, sg):
        if cmds.objExists(n):
            cmds.delete(n)
    return ext


def drop_props():
    """The swords out of the rig: a weapon is the catalog's business now, added and removed like on
    every other rig.  Returns what was deleted."""
    gone = cmds.ls("|Group|Geometry|Creep_Props", "|*:Group|*:Geometry|*:Creep_Props", long=True) or []
    if gone:
        cmds.delete(gone)
    return gone


def _mirror_x(m):
    """A world matrix mirrored across the character's YZ plane, behaviour style: S * M * S."""
    s = om.MMatrix([-1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1])
    return s * m * s


FLIP_Z = om.MMatrix([-1, 0, 0, 0, 0, -1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1])   # a half turn about the bone's own Z


def weapon_bones():
    """The Creep's weapon bones on the plugin's convention (2026-09-24, the animator: weapons added
    and removed as on the other rigs, «анимация переносилась на вепон бону и обратно»).

    `weapon_test` (the animator's own attachment point under hand_r, where the Creep's sword sat)
    becomes `weapon_r`, turned half a turn about its own Z: the sword lay along the bone's -Y, and
    every weapon of the catalog lies along +Y -- so the Creep's sword, exported in the new bone's
    frame, sits exactly where it sat at zero grip.  `weapon_l` is created under hand_l, its world
    matrix the mirror of weapon_r's.  Both are skin influences of zero weight at most; their
    bindPreMatrix is re-expressed (BPM' = BPM * WM_old * WM_new^-1) and bindPose1 reset.  Run at the
    build pose.  Returns (weapon_r, weapon_l) long paths."""
    b = bones()
    moved = {}
    if "weapon_test" in b and "weapon_r" not in b:
        old = _wmat(b["weapon_test"])
        uid = cmds.ls(b["weapon_test"], uuid=True)[0]
        cmds.rename(b["weapon_test"], "weapon_r")
        j = cmds.ls(uid, long=True)[0]
        cmds.xform(j, worldSpace=True, matrix=list(FLIP_Z * old))
        moved[uid] = old
    b = bones()
    if "weapon_l" not in b:
        j = cmds.createNode("joint", name="weapon_l", parent=b["hand_l"], skipSelect=True)
        j = cmds.ls(j, long=True)[0]
        cmds.setAttr(j + ".radius", cmds.getAttr(b["weapon_r"] + ".radius"))
        cmds.xform(j, worldSpace=True, matrix=list(_mirror_x(_wmat(b["weapon_r"]))))
        if cmds.objExists(LAYER):
            cmds.editDisplayLayerMembers(LAYER, j, noRecurse=True)
    for sc in cmds.ls(type="skinCluster"):
        for idx in cmds.getAttr(sc + ".matrix", multiIndices=True) or []:
            src = cmds.listConnections("%s.matrix[%d]" % (sc, idx), s=True, d=False)
            u = cmds.ls(src[0], uuid=True)[0] if src else None
            if u in moved:
                bpm = om.MMatrix(cmds.getAttr("%s.bindPreMatrix[%d]" % (sc, idx)))
                cmds.setAttr("%s.bindPreMatrix[%d]" % (sc, idx),
                             list(bpm * moved[u] * _wmat(cmds.ls(u, long=True)[0]).inverse()), type="matrix")
    b = bones()
    for pose in cmds.ls(type="dagPose"):
        if cmds.getAttr(pose + ".bindPose"):
            members = [m for m in cmds.ls(cmds.dagPose(pose, q=True, members=True) or [], long=True) if m in b.values()]
            if members:
                cmds.dagPose(members, reset=True, name=pose)
    return b["weapon_r"], b["weapon_l"]


def mark():
    """The retarget reads this: the Creep's rig takes rotations only."""
    if not cmds.attributeQuery(RETARGET_ATTR, node="Group", exists=True):
        cmds.addAttr("Group", longName=RETARGET_ATTR, dataType="string")
    cmds.setAttr("Group." + RETARGET_ATTR, RETARGET_MODE, type="string")


def run():
    state = {"autoKey": cmds.autoKeyframe(q=True, st=True), "em": cmds.evaluationManager(q=True, mode=True)[0],
             "sel": cmds.ls(sl=True, long=True)}
    cmds.autoKeyframe(st=False)
    cmds.evaluationManager(mode="off")
    try:
        joints = list(bones().values())
        rest = {j: cmds.getAttr(j + ".worldMatrix[0]") for j in joints}
        placed, worst_fit = fit()
        print("// fit: %d joints placed, mapped joints on their bones to %.6f cm" % (placed, worst_fit))
        build()
        print("// twist / in-between joints on the Creep's: %s" % dict((k, round(v, 4)) for k, v in place_parts().items()))
        print("// constraints: %d" % constrain())
        n, worst = orient_controls()
        shapes = align_shapes()
        sdk = finger_sdk_axes()
        print("// IK foot controls level (AS's frame): worst %.5f deg" % as_frames(LEVEL_CONTROLS))
        mark()
        drift = max(max(abs(a - c) for a, c in zip(m, cmds.getAttr(j + ".worldMatrix[0]"))) for j, m in rest.items())
        tidy()                                          # re-parents the root: the paths above are stale after it
        print("// the sword out as a catalog weapon: %s" % (export_sword(SWORD_FBX),))
        drop_props()
        weapon_bones()
        print("// %d controls oriented (worst frame angle %.5f deg), %d curves aligned, %d finger SDK groups re-framed; "
              "bind-pose drift %.9f" % (n, worst, shapes, sdk, drift))
        if not cmds.objExists(LAYER):
            lay = cmds.createDisplayLayer(name=LAYER, empty=True)
            cmds.editDisplayLayerMembers(lay, list(bones().values()), noRecurse=True)
    finally:
        cmds.evaluationManager(mode=state["em"])
        cmds.autoKeyframe(st=state["autoKey"])
        cmds.select(state["sel"]) if state["sel"] else cmds.select(clear=True)


if __name__ == "__main__":
    run()
