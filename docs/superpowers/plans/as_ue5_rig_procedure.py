"""AdvancedSkeleton rig over an existing, skinned UE5 Manny skeleton -- the procedure.

This is the sequence that produced the rig on 2026-09-04 (AdvancedSkeleton 6.797,
Maya 2027), written down as one script so it can be repeated on another Manny
scene. It was executed step by step through the command-port bridge; the ONE
reordering here is that the neck in-between network is moved into Offset space
BEFORE the controls are detached (on the day it was fixed afterwards, which left
stale transforms on NeckPart1/Head that then had to be normalised -- see the
spec). Run it in a scene holding exactly one UE5 Manny and no AdvancedSkeleton
rig, with the AdvancedSkeleton window closed or open, autoKey on or off. It
disables autoKey and switches the evaluation manager to DG while it works and
puts both back.

Result: the game skeleton is untouched (names, hierarchy, skin, bind pose), every
deformation joint of AS drives its UE twin through point+orient+scale
constraints, `root` follows `Main`, the ik_* helpers follow the hands and feet,
and every FK control's local axes equal the axes of the UE bone it drives.
"""
import math
import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

AS_MEL = "C:/Users/MY PC/Downloads/AdvancedSkeleton/AdvancedSkeleton.mel"

# Name Matcher "Unreal5" table, as the vendor ships it (right side only in the fit
# skeleton; the build mirrors the left).  Sides are appended as _r/_l, middle none.
ROWS = [("Root", "pelvis"), ("Spine1", "spine_01"), ("Spine2", "spine_02"), ("Spine3", "spine_03"), ("Spine4", "spine_04"),
        ("Spine5", "spine_05"), ("Scapula", "clavicle"), ("Shoulder", "upperarm"), ("Elbow", "lowerarm"), ("Wrist", "hand"),
        ("IndexFinger0", "index_metacarpal"), ("IndexFinger1", "index_01"), ("IndexFinger2", "index_02"), ("IndexFinger3", "index_03"),
        ("MiddleFinger0", "middle_metacarpal"), ("MiddleFinger1", "middle_01"), ("MiddleFinger2", "middle_02"), ("MiddleFinger3", "middle_03"),
        ("RingFinger0", "ring_metacarpal"), ("RingFinger1", "ring_01"), ("RingFinger2", "ring_02"), ("RingFinger3", "ring_03"),
        ("PinkyFinger0", "pinky_metacarpal"), ("PinkyFinger1", "pinky_01"), ("PinkyFinger2", "pinky_02"), ("PinkyFinger3", "pinky_03"),
        ("ThumbFinger1", "thumb_01"), ("ThumbFinger2", "thumb_02"), ("ThumbFinger3", "thumb_03"),
        ("Neck", "neck_01"), ("Head", "head"), ("Hip", "thigh"), ("Knee", "calf"), ("Ankle", "foot"), ("Toes", "ball")]
# The twist and in-between joints have no row in the vendor's table.  UE numbers the
# LOWER twists from the far end (lowerarm_twist_01 sits near the wrist), AS numbers
# its Part joints from the near end -- hence the swapped pairs.
PART_ROWS = [("ShoulderPart1", "upperarm_twist_01"), ("ShoulderPart2", "upperarm_twist_02"),
             ("ElbowPart1", "lowerarm_twist_02"), ("ElbowPart2", "lowerarm_twist_01"),
             ("HipPart1", "thigh_twist_01"), ("HipPart2", "thigh_twist_02"),
             ("KneePart1", "calf_twist_02"), ("KneePart2", "calf_twist_01"), ("NeckPart1", "neck_02")]
# Bones the Name Matcher cannot know about.  Everything else under root (weapon_*,
# camera_*, interaction, center_of_mass, ik_*_root) rides its parent.
EXTRAS = [("Main", "root"), ("hand_r", "ik_hand_gun"), ("hand_l", "ik_hand_l"), ("hand_r", "ik_hand_r"), ("foot_l", "ik_foot_l"), ("foot_r", "ik_foot_r")]


def _wmat(n):
    return om.MMatrix(cmds.getAttr(n + ".worldMatrix[0]"))


def _rot(m):
    return om.MTransformationMatrix(m).rotation(asQuaternion=True)


def _set_rot(node, rmat):
    tm = om.MTransformationMatrix(rmat)
    tm.reorderRotation(cmds.getAttr(node + ".rotateOrder") + 1)   # attr enum + 1 == MTransformationMatrix order
    e = tm.rotation(asQuaternion=False)
    cmds.setAttr(node + ".rotate", math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))


def ensure_as_ui():
    """Source the toolset and open its window -- the vendor's procs read their own controls."""
    if mel.eval('whatIs "asReBuildAdvancedSkeleton"') == "Unknown":
        mel.eval('source "%s";' % AS_MEL)
    if not cmds.optionMenu("asFitFiles", exists=True):
        mel.eval("AdvancedSkeleton;")


def fit(heel_z=-5.8):
    """Import the vendor's UE5 FitSkeleton and put it exactly on the bones.

    UE5.ma is authored on this very skeleton (0.0003 cm everywhere except the neck,
    4.7 cm), so only what differs is snapped.  The preset gives the Knee no twist
    joints and the Neck two in-betweens; Manny has two calf twists and one neck_02.
    Eye and Jaw have no UE bone and would build dead controls.
    """
    cmds.optionMenu("asFitFiles", e=True, v="UE5.ma")
    mel.eval("asFitSkeletonImport;")
    fit = {f.split("|")[-1]: f for f in cmds.listRelatives("FitSkeleton", ad=True, type="joint", fullPath=True)}
    moved = 0
    for a, b in ROWS:                                   # parents come before children within a branch
        if a not in fit:
            continue
        x = cmds.xform(fit[a], q=True, ws=True, t=True)[0]
        ue = b if abs(x) < 0.001 else b + "_r"
        if not cmds.objExists(ue):
            continue
        pu = cmds.xform(ue, q=True, ws=True, t=True)
        if max(abs(i - j) for i, j in zip(cmds.xform(fit[a], q=True, ws=True, t=True), pu)) > 0.01:
            cmds.xform(fit[a], ws=True, t=pu)
            moved += 1
    knee = fit["Knee"]
    if not cmds.attributeQuery("twistJoints", node=knee, exists=True):
        cmds.addAttr(knee, k=True, ln="twistJoints", at="long", min=0, dv=2)
        cmds.addAttr(knee, k=True, ln="bendyCtrls", at="long", min=0, dv=0)
    cmds.setAttr(fit["Neck"] + ".inbetweenJoints", 1)
    for n in ("Eye", "Jaw"):
        if n in fit and cmds.objExists(fit[n]):
            cmds.delete(fit[n])
    pos = cmds.xform(fit["Heel"], q=True, ws=True, t=True)      # the preset's heel pivot sits 2 cm inside the sole
    cmds.xform(fit["Heel"], ws=True, t=[pos[0], 0.0, heel_z])
    if moved:
        mel.eval("asFitModeManualUpdate;")
    return moved


def build():
    mel.eval("asReBuildAdvancedSkeleton;")                       # first build; 6 s on Manny
    assert cmds.objExists("Group") and cmds.objExists("DeformSet"), "build did not complete"


def mapping():
    out = {}
    for a, b in ROWS + PART_ROWS:
        for side, s in (("_M", ""), ("_R", "_r"), ("_L", "_l")):
            if cmds.objExists(a + side) and cmds.nodeType(a + side) == "joint":
                out[a + side] = b + s
    return out


def constrain():
    """The vendor's 'Constraint to Joints' with the twist rows added, plus root and ik_*."""
    mel.eval("asNameMatcherUI;")
    cmds.optionMenu("asMappingUIFiles", e=True, v="Unreal5")
    mel.eval('asMappingUIFileOptionMenuChanged "nameMatcher";')
    cmds.textField("asMappingUITopNodeTextFieldB1", e=True, tx="root")
    cmds.textField("asMappingUINameSpacesTextFieldB1", e=True, tx="")
    for a, b in PART_ROWS:
        mel.eval("asMappingUIAddJoint;")
        nr = len(cmds.columnLayout("asMappingUIJointsColumnLayout", q=True, ca=True))
        cmds.textField("asMappingUIJointsTextFieldA%d" % nr, e=True, tx=a)
        cmds.textField("asMappingUIJointsTextFieldB%d" % nr, e=True, tx=b)
    mel.eval('asMappingUIFunction "AutoRigConstraint";')       # point+orient+scale, maintainOffset
    for src, dst in EXTRAS:
        if not cmds.listRelatives(dst, c=True, type="constraint"):
            cmds.parentConstraint(src, dst, mo=True)


IK_END = [("IKLeg_L", "foot_l"), ("IKLeg_R", "foot_r"), ("IKArm_L", "hand_l"), ("IKArm_R", "hand_r"), ("IKToes_L", "ball_l"), ("IKToes_R", "ball_r")]


def orient_controls():
    """Every FK and IK-end control's frame becomes its UE bone's frame; RootX (pelvis) keeps AS's world frame.

    The neck in-between network multiplies by FKExtraNeck_M.parentInverseMatrix, which
    Attach turns into the rotated CustomOrient -- move it to Offset space first (these
    two multMatrix nodes are its only consumers).  The IKX ankle/wrist read the CHILD
    IKFKAligned* nodes, so the IK controls can turn freely; the arm pole's follow
    offset is the one consumer of an IK control's own rotation and is compensated.
    """
    for mm in ("NeckInbetweenMM_M", "NeckPart1InbetweenMM_M"):
        if cmds.objExists(mm):
            cmds.connectAttr("FKOffsetNeck_M.worldInverseMatrix[0]", mm + ".matrixIn[1]", force=True)
    targets = [("FK" + asj, ue) for asj, ue in mapping().items()
               if asj != "Root_M" and not ("Part" in asj and not asj.startswith("NeckPart")) and cmds.objExists("FK" + asj)]
    targets += [(c, ue) for c, ue in IK_END if cmds.objExists(c)]
    w_old = {c: _wmat(c) for c, _ in IK_END if cmds.objExists(c)}
    mel.eval("asControlOrientDetach;")
    for c, ue in targets:
        Rb = _rot(_wmat(ue)).asMatrix()
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
    worst = max(math.degrees(2 * math.acos(min(1.0, abs((_rot(_wmat(c)).inverse() * _rot(_wmat(ue))).w)))) for c, ue in targets)
    return len(targets), worst


def run():
    state = {"autoKey": cmds.autoKeyframe(q=True, st=True), "em": cmds.evaluationManager(q=True, mode=True)[0]}
    cmds.autoKeyframe(st=False)
    cmds.evaluationManager(mode="off")
    try:
        ensure_as_ui()
        joints = cmds.ls(type="joint", long=True)
        rest = {j: cmds.getAttr(j + ".worldMatrix[0]") for j in joints}
        print("// fit: %d joints snapped" % fit())
        build()
        constrain()
        n, worst = orient_controls()
        drift = max(max(abs(a - b) for a, b in zip(m, cmds.getAttr(j + ".worldMatrix[0]"))) for j, m in rest.items())
        print("// %d FK controls oriented, worst frame angle %.5f deg; bind-pose drift %.9f" % (n, worst, drift))
        lay = cmds.createDisplayLayer(name="UE5_Skeleton", empty=True)
        cmds.editDisplayLayerMembers(lay, joints, noRecurse=True)
    finally:
        cmds.evaluationManager(mode=state["em"])
        cmds.autoKeyframe(st=state["autoKey"])


if __name__ == "__main__":
    run()
