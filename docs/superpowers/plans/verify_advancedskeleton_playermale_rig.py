"""Live verification of the AdvancedSkeleton rig over the PlayerMale game skeleton.

Runs in the animator's OPEN scene after `as_playermale_rig_procedure` has built the rig
(any time later too).  Every poke is undone through AdvancedSkeleton's own Go To Build
Pose with the FKIKBlend values put back AFTER it (asGoToBuildPose writes the values the
rig was built with); the frame, autoKey, the evaluation manager and the selection are
restored in a finally; nothing is keyed.  Read-only wherever it can be.  Prints one line
per gate and ends with `N of M gates failed` or `all M gates passed`.

Sent through the command-port bridge (runner with a marker file, explicit globals).
"""
import math
import sys
import traceback

import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

PLANS = "C:/!!!Work/MayaScripts/docs/superpowers/plans"
if PLANS not in sys.path:
    sys.path.insert(0, PLANS)
sys.modules.pop("as_playermale_rig_procedure", None)
import as_playermale_rig_procedure as pr  # noqa: E402

CANON = ["Root", "Hip", "Spine1", "Spine2", "Spine3", "Spine4", "Neck", "Head", "Jaw", "Right_Eye", "Left_Eye"]
for _side in ("Right_", "Left_"):
    CANON += [_side + n for n in ("Shoulder", "Arm", "ForeArm", "Hand", "Thigh", "Knee", "Ankle", "Toes")]
    for _f in ("Finger", "Middle", "Ring", "Pinky", "Thumb"):
        CANON += ["%s%s%d" % (_side, _f, i) for i in (1, 2, 3)]
BLENDS = ("FKIKArm_R", "FKIKArm_L", "FKIKLeg_R", "FKIKLeg_L")
# (control, bone, the FKIK blend that must be FK for the control to drive it)
AXIS_TESTS = [("FKSpine1_M", "Spine1", None), ("FKSpine2_M", "Spine2", None), ("FKChest_M", "Spine4", None),
              ("FKNeck_M", "Neck", None), ("FKHead_M", "Head", None), ("FKJaw_M", "Jaw", None),
              ("FKEye_R", "Right_Eye", None), ("FKScapula_R", "Right_Shoulder", None),
              ("FKShoulder_R", "Right_Arm", None), ("FKElbow_R", "Right_ForeArm", None), ("FKWrist_R", "Right_Hand", None),
              ("FKShoulder_L", "Left_Arm", None), ("FKWrist_L", "Left_Hand", None),
              ("FKIndexFinger1_R", "Right_Finger1", None), ("FKThumbFinger2_L", "Left_Thumb2", None),
              ("FKPinkyFinger3_R", "Right_Pinky3", None),
              ("FKHip_R", "Right_Thigh", "FKIKLeg_R"), ("FKKnee_L", "Left_Knee", "FKIKLeg_L"),
              ("FKAnkle_R", "Right_Ankle", "FKIKLeg_R"), ("FKToes_R", "Right_Toes", "FKIKLeg_R")]

results = []
skipped = []


def gate(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print("%s %2d  %s%s" % ("ok  " if ok else "FAIL", len(results), name, (" -- " + detail) if detail else ""))


def skip(name, why):
    skipped.append((name, why))
    print("skip     %s -- %s" % (name, why))


def foreign_constraints(ctrl):
    """Constraints on a control whose targets lie outside the rig: the animator's own work in
    progress (measured 2026-09-05: FKShoulder_L/FKElbow_L/FKWrist_L parent-constrained to
    locator1/2/3 beside an OverRig setup). A verify run poses around them, never through them."""
    q = {"parentConstraint": cmds.parentConstraint, "orientConstraint": cmds.orientConstraint,
         "pointConstraint": cmds.pointConstraint, "scaleConstraint": cmds.scaleConstraint}
    out = []
    for con in cmds.listRelatives(ctrl, c=True, type="constraint", fullPath=True) or []:
        fn = q.get(cmds.nodeType(con))
        targets = fn(con, q=True, targetList=True) if fn else []
        if any(not cmds.ls(t, long=True)[0].startswith("|Group|") for t in targets):
            out.append("%s <- %s" % (con.split("|")[-1], targets))
    return out


def W(path):
    return om.MVector(cmds.xform(path, q=True, ws=True, t=True))


def M(path):
    return om.MMatrix(cmds.getAttr(path + ".worldMatrix[0]"))


def R(m):
    return om.MTransformationMatrix(m).rotation(asQuaternion=True).asMatrix()


def ang(ma, mb):
    return pr._angle(ma, mb)


def settle():
    cmds.dgdirty(allPlugs=True)


def axis_matrix(axis, deg):
    """Rotation of `deg` about a local axis, as the row-vector matrix W1 = Rl * W0 needs."""
    e = [0.0, 0.0, 0.0]
    e["xyz".index(axis)] = math.radians(deg)
    return om.MEulerRotation(*e).asMatrix()


def bbox(path):
    return cmds.exactWorldBoundingBox(path)


state = {"autoKey": cmds.autoKeyframe(q=True, st=True), "em": cmds.evaluationManager(q=True, mode=True)[0],
         "time": cmds.currentTime(q=True), "sel": cmds.ls(sl=True, long=True) or [],
         "blends": dict((c, cmds.getAttr(c + ".FKIKBlend")) for c in BLENDS if cmds.objExists(c))}
cmds.autoKeyframe(st=False)
cmds.evaluationManager(mode="off")


def build_pose():
    mel.eval("asGoToBuildPose bodySetup;")
    for c, v in state["blends"].items():            # AFTER: asGoToBuildPose writes the build values
        cmds.setAttr(c + ".FKIKBlend", v)
    settle()


try:
    curves_before = len(cmds.ls(type="animCurve") or [])
    game = pr.game_joints()
    root = pr.game_root()

    # ------------------------------------------------------------ what is there
    leaves = sorted(p.split("|")[-1] for p in game.values())
    gate("the game skeleton is whole and wears its own names",
         leaves == sorted(CANON) and root == "|Root" and not pr.held(),
         "%d joints, root %s, held %s" % (len(leaves), root, pr.held()))
    gate("the rig is there", all(cmds.objExists(n) for n in ("Group", "Main", "RootX_M", "DeformSet", "ControlSet", "buildPose")),
         "%d deformation joints, %d controls" % (len(cmds.sets("DeformSet", q=True) or []), len(cmds.sets("ControlSet", q=True) or [])))
    fit = pr.fit_joints()
    fit_top = cmds.ls("FitSkeleton", long=True)
    gate("the FitSkeleton lives under Group, hidden, with this skeleton's shape",
         fit_top == ["|Group|FitSkeleton"] and not cmds.getAttr("FitSkeleton.v") and "Cup" not in fit
         and all(n in fit for n in ("Spine2", "Spine3", "Chest", "Jaw", "Eye", "Heel", "ToesEnd"))
         and all(cmds.getAttr(fit[n] + ".twistJoints") == 0 for n in ("Shoulder", "Elbow", "Hip"))
         and all(cmds.getAttr(fit[n] + ".inbetweenJoints") == 0 for n in ("Root", "Spine1", "Neck")),
         "%s, %d fit joints" % (fit_top, len(fit)))
    mapping = pr.mapping()
    deform = cmds.sets("DeformSet", q=True) or []
    gate("every deformation joint has a game twin and every game joint but Root a driver",
         len(deform) == 56 and len(mapping) == 56 and set(mapping.values()) == set(p for n, p in game.items() if n != "Root")
         and not [d for d in deform if "Part" in d or d.startswith("Cup")],
         "%d deform joints, %d mapped" % (len(deform), len(mapping)))
    bad = []
    total = 0
    for d, g in mapping.items():
        cons = cmds.listRelatives(g, children=True, type="constraint", fullPath=True) or []
        total += len(cons)
        kinds = dict((cmds.nodeType(c), c) for c in cons)
        if set(kinds) != set(["pointConstraint", "orientConstraint", "scaleConstraint"]) or len(cons) != 3:
            bad.append((g.split("|")[-1], sorted(kinds)))
            continue
        for kind, q in (("pointConstraint", cmds.pointConstraint), ("orientConstraint", cmds.orientConstraint), ("scaleConstraint", cmds.scaleConstraint)):
            if q(kinds[kind], q=True, targetList=True) != [d.split("|")[-1]]:
                bad.append((g.split("|")[-1], kind, q(kinds[kind], q=True, targetList=True)))
    root_cons = cmds.listRelatives(root, children=True, type="constraint") or []
    total += len(root_cons)
    gate("each game joint is point+orient+scale constrained to its AS twin, Root parent-constrained to Main",
         not bad and len(root_cons) == 1 and cmds.nodeType(root_cons[0]) == "parentConstraint"
         and cmds.parentConstraint(root_cons[0], q=True, targetList=True) == ["Main"] and total == 169,
         "%d constraints; off: %s" % (total, bad[:4]))
    gate("no animation and no pairBlend on the game skeleton",
         not [n for n, p in game.items() if cmds.listConnections(p, s=True, d=False, type="animCurve")
              or cmds.listConnections(p, s=True, d=False, type="pairBlend")])
    gate("legs are IK by default, arms FK", state["blends"] == {"FKIKArm_R": 0.0, "FKIKArm_L": 0.0, "FKIKLeg_R": 10.0, "FKIKLeg_L": 10.0},
         str(state["blends"]))
    gate("Hip and its friends are short names shared with the fit joints (documented; hold() clears it for a ReBuild)",
         all(len(cmds.ls(n) or []) == 2 for n in pr.CLASHING), str(dict((n, len(cmds.ls(n) or [])) for n in pr.CLASHING)))

    # ------------------------------------------------------------ the rest pose
    build_pose()
    bind = {}
    for i in range(cmds.getAttr("bindPose1.members", size=True)):
        src = cmds.listConnections("bindPose1.members[%d]" % i, s=True, d=False) or []
        if src and cmds.nodeType(src[0]) == "joint":
            bind[cmds.ls(src[0], long=True)[0]] = om.MMatrix(cmds.getAttr("bindPose1.worldMatrix[%d]" % i))

    def bind_drift():
        return max(max(abs(a - b) for a, b in zip(list(bind[p]), list(M(p)))) for p in game.values() if p in bind)
    d0 = bind_drift()
    gate("at build pose every game joint stands on its bindPose1 world matrix", len(bind) == 57 and d0 < 1e-3, "%d joints, worst element %.9f" % (len(bind), d0))
    skin = list(set(cmds.ls(type="skinCluster")))
    gate("the 70 skins and both bindPose nodes are intact", len(skin) == 70 and cmds.objExists("bindPose1") and cmds.objExists("bindPose2"), "%d skinClusters" % len(skin))

    # ------------------------------------------------------------ the frames
    off = []
    for d, g in mapping.items():
        c = "FK" + d.split("|")[-1]
        if d.split("|")[-1] != "Root_M" and cmds.objExists(c):
            a = ang(M(c), M(g))
            if a > 1e-3:
                off.append((c, round(a, 4)))
    off = [o for o in off if not o[0].startswith("FKWrist")]
    gate("every FK control but the wrists carries its bone's frame", not off, "off: %s" % off[:5])
    ik_off = []
    for c, b in pr.IK_END:
        if c.startswith("IKArm"):
            continue
        parent = cmds.listRelatives(c, p=True)[0]
        a = ang(M(c), M(parent))                     # AS's own frame: zero rotation under the IK offset
        if a > 1e-3 or cmds.objExists("CustomOrient" + c):
            ik_off.append((c, round(a, 4)))
    world = ang(M("IKLeg_R"), om.MMatrix())
    gate("the IK leg and toe controls keep AS's own frames (feet world-aligned), no CustomOrient on them",
         not ik_off and world < 1e-3, "off: %s; IKLeg_R vs world %.5f deg" % (ik_off[:4], world))
    # the hands: the frame the animator gave as locators (X along the fingers, Z the palm normal),
    # 29 deg off the hand bone, on both the FK wrist and the IK arm control
    hand = pr.hand_frames()
    hand_off = [(c, round(ang(M(c), R), 4)) for c, R in hand.items() if ang(M(c), R) > 1e-3]
    Mx = om.MMatrix([-1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1])
    lr = max(math.degrees(math.acos(max(-1.0, min(1.0, abs(pr._row(M("FKWrist_R"), i).normal() * pr._row(Mx * M("FKWrist_L") * Mx, i).normal())))))
             for i in range(3))
    along = pr._row(M("FKWrist_R"), 0).normal() * (W(game["Right_Middle1"]) - W(game["Right_Hand"])).normal()
    gate("IKArm and FKWrist on both sides carry the animator's hand frame (locator10 / locator9): X along the fingers, mirrored L/R",
         len(hand) == 4 and not hand_off and lr < 0.5 and along > 0.98,
         "off: %s; L/R mirror %.3f deg; X . fingers %.3f" % (hand_off, lr, along))
    asj = cmds.listRelatives("DeformationSystem", allDescendents=True, type="joint", fullPath=True) or []
    in_layer = set(cmds.editDisplayLayerMembers("AS_DeformSkeleton", q=True, fullNames=True) or []) if cmds.objExists("AS_DeformSkeleton") else set()
    gate("AS's deformation skeleton sits in the hidden layer AS_DeformSkeleton, the game skeleton in the visible PlayerMale_Skeleton",
         cmds.objExists("AS_DeformSkeleton") and not cmds.getAttr("AS_DeformSkeleton.visibility") and set(asj) <= in_layer
         and cmds.objExists("PlayerMale_Skeleton") and cmds.getAttr("PlayerMale_Skeleton.visibility")
         and set(game.values()) <= set(cmds.editDisplayLayerMembers("PlayerMale_Skeleton", q=True, fullNames=True) or []),
         "%d AS joints, %d in the layer" % (len(asj), len(set(asj) & in_layer)))

    worst = 0.0
    worst_at = ""
    tested = 0
    for ctrl, bone, blend in AXIS_TESTS:
        held_by = foreign_constraints(ctrl)
        if held_by:
            skip("axis test on %s" % ctrl, "it carries the animator's own %s" % held_by)
            continue
        tested += 1
        for axis in "xyz":
            build_pose()
            if blend:
                cmds.setAttr(blend + ".FKIKBlend", 0)
                settle()
            m0 = M(game[bone])
            axis_world = pr._row(M(ctrl), "xyz".index(axis)).normal()   # == the bone's own axis wherever the frames match
            cmds.setAttr(ctrl + ".rotate" + axis.upper(), 25.0)
            settle()
            a = ang(R(m0) * om.MQuaternion(math.radians(25.0), axis_world).asMatrix(), M(game[bone]))
            if a > worst:
                worst, worst_at = a, "%s.%s" % (ctrl, axis)
            cmds.setAttr(ctrl + ".rotate" + axis.upper(), 0.0)
            if blend:
                cmds.setAttr(blend + ".FKIKBlend", state["blends"][blend])
    gate("25 deg on a control's axis turns its bone 25 deg about that axis, which is the bone's own wherever the frames match (%d controls x 3 axes)" % tested,
         worst < 0.01 and tested >= 12, "worst %.5f deg at %s" % (worst, worst_at))

    build_pose()
    m0, fore0 = M(game["Right_Arm"]), cmds.getAttr(game["Right_ForeArm"] + ".rotate")[0]
    cmds.setAttr("FKShoulder_R.rotateX", 25.0)
    settle()
    roll = ang(axis_matrix("x", 25.0) * R(m0), M(game["Right_Arm"]))
    fore = max(abs(a - b) for a, b in zip(fore0, cmds.getAttr(game["Right_ForeArm"] + ".rotate")[0]))
    cmds.setAttr("FKShoulder_R.rotateX", 0.0)
    gate("the shoulder's roll lands on Right_Arm itself (no twist joints to take it), the forearm's local rotate untouched",
         roll < 0.01 and fore < 1e-4, "roll error %.5f deg, forearm local change %.7f" % (roll, fore))

    # ------------------------------------------------------------ mirror
    build_pose()
    # the skeleton's own asymmetry: the left frames seen in a mirror against the right ones
    Mx = om.MMatrix([-1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1])
    asym = 0.0
    for b in ("Arm", "ForeArm", "Hand"):
        wr, wl = M(game["Right_" + b]), Mx * M(game["Left_" + b]) * Mx
        for i in range(3):
            d = abs(pr._row(wr, i).normal() * pr._row(wl, i).normal())
            asym = max(asym, math.degrees(math.acos(max(-1.0, min(1.0, d)))))
    arm_ctrls = ("FKShoulder_R", "FKShoulder_L", "FKElbow_R", "FKElbow_L")
    held_by = [h for c in arm_ctrls for h in foreign_constraints(c)]
    if held_by:
        skip("equal values on both arms give a mirrored pose", "the animator's own %s hold the left arm" % held_by)
    else:
        cmds.setAttr("FKShoulder_R.rotateZ", 30.0)
        cmds.setAttr("FKShoulder_L.rotateZ", 30.0)
        cmds.setAttr("FKElbow_R.rotateY", 40.0)
        cmds.setAttr("FKElbow_L.rotateY", 40.0)
        settle()
        r, l = W(game["Right_Hand"]), W(game["Left_Hand"])
        mirror = max(abs(r.x + l.x), abs(r.y - l.y), abs(r.z - l.z))
        gate("equal values on both arms give a mirrored pose, to within the skeleton's own asymmetry", mirror < 0.01,
             "hands at %.4f/%.4f/%.4f, mirror error %.6f; the game skeleton's own arm frames are %.3f deg asymmetric" % (r.x, r.y, r.z, mirror, asym))
        for c in arm_ctrls:
            cmds.setAttr(c + ".rotate", 0, 0, 0)

    # ------------------------------------------------------------ fingers
    build_pose()
    probes = dict((s, pr.finger_probe(s)) for s in "RL")
    gate("indexCurl curls toward the palm and spread parts the fingers, on both hands",
         all(c > 0.1 and s > 0.1 for c, s in probes.values()), str(dict((k, (round(c, 4), round(s, 4))) for k, (c, s) in probes.items())))
    cmds.setAttr("Fingers_R.indexCurl", 5)
    cmds.setAttr("Fingers_L.indexCurl", 5)
    settle()
    r, l = W(game["Right_Finger3"]), W(game["Left_Finger3"])
    mirror = max(abs(r.x + l.x), abs(r.y - l.y), abs(r.z - l.z))
    m1 = M(game["Right_Finger2"])
    cmds.setAttr("Fingers_R.indexCurl", 0)
    cmds.setAttr("Fingers_L.indexCurl", 0)
    settle()
    q = om.MTransformationMatrix(R(M(game["Right_Finger2"])).inverse() * R(m1)).rotation(asQuaternion=True)
    axis = om.MVector(q.x, q.y, q.z).normal()
    b = R(M(game["Right_Finger2"]))
    local = om.MVector(*[axis * pr._row(b, i) for i in range(3)])
    gate("the curl mirrors and turns the phalanx about its own Y (the knuckle line)",
         mirror < 1e-3 and abs(abs(local.y) - 1.0) < 0.01,
         "mirror error %.6f, curl axis in the bone frame (%.3f, %.3f, %.3f), %.2f deg" % (mirror, local.x, local.y, local.z, math.degrees(2 * math.acos(min(1.0, abs(q.w))))))

    # ------------------------------------------------------------ IK
    build_pose()
    a0, t0 = W(game["Right_Ankle"]), W(game["Right_Thigh"])
    cmds.setAttr("IKLeg_R.translateY", cmds.getAttr("IKLeg_R.translateY") + 1.0)
    settle()
    moved, thigh = (W(game["Right_Ankle"]) - a0).length(), (W(game["Right_Thigh"]) - t0).length()
    build_pose()
    m0 = M(game["Right_Ankle"])
    cmds.setAttr("IKLeg_R.rotateY", 20.0)
    settle()
    # the control's frame is AS's (world): the ankle turns 20 deg about the CONTROL's Y axis, in world
    ctrl_y = pr._row(M("IKLeg_R"), 1).normal()
    turn = ang(R(m0) * om.MQuaternion(math.radians(20.0), ctrl_y).asMatrix(), M(game["Right_Ankle"]))
    gate("IK leg: the control lifts the ankle 1.0 with the thigh planted, and turns the foot about the control's (world) axes",
         abs(moved - 1.0) < 0.02 and thigh < 1e-6 and turn < 0.01, "ankle moved %.4f, thigh %.7f, turn error %.5f deg" % (moved, thigh, turn))
    build_pose()
    cmds.setAttr("FKIKArm_R.FKIKBlend", 10)
    settle()
    h0, s0 = W(game["Right_Hand"]), W(game["Right_Arm"])
    pos = cmds.xform("IKArm_R", q=True, ws=True, t=True)         # the arm stands 99.4% extended: lift the hand, within reach
    cmds.xform("IKArm_R", ws=True, t=(pos[0], pos[1] + 1.0, pos[2]))
    settle()
    moved, shoulder = (W(game["Right_Hand"]) - h0).length(), (W(game["Right_Arm"]) - s0).length()
    build_pose()
    cmds.setAttr("FKIKArm_R.FKIKBlend", 10)
    settle()
    m0 = M(game["Right_Hand"])
    cmds.setAttr("IKArm_R.rotateX", 20.0)
    settle()
    ctrl_x = pr._row(M("IKArm_R"), 0).normal()
    turn = ang(R(m0) * om.MQuaternion(math.radians(20.0), ctrl_x).asMatrix(), M(game["Right_Hand"]))
    cmds.setAttr("FKIKArm_R.FKIKBlend", state["blends"]["FKIKArm_R"])
    gate("IK arm: the control moves the hand 1.0 with the shoulder planted, and turns the hand about the control's (world) axes",
         abs(moved - 1.0) < 0.02 and shoulder < 1e-6 and turn < 0.01, "hand moved %.4f, shoulder %.7f, turn error %.5f deg" % (moved, shoulder, turn))

    # ------------------------------------------------------------ Main, pelvis, eyes
    build_pose()
    r0, h0, v0 = W(root), W(game["Head"]), cmds.pointPosition("|Body.vtx[100]", w=True)
    cmds.setAttr("Main.translateX", 3.0)
    settle()
    dr, dh = (W(root) - r0).x, (W(game["Head"]) - h0).x
    # a VERTEX, not exactWorldBoundingBox: measured, the bbox of this locked skinned mesh answered
    # 0.00002 while every vertex had moved 3.0
    dbb = cmds.pointPosition("|Body.vtx[100]", w=True)[0] - v0[0]
    cmds.setAttr("Main.translateX", 0.0)
    cmds.setAttr("Main.rotateY", 90.0)
    settle()
    yaw = ang(axis_matrix("y", 90.0) * R(om.MMatrix()), R(M(root)))
    cmds.setAttr("Main.rotateY", 0.0)
    gate("Main carries the whole character: Root, head and skin travel 3.0 with it, and it yaws Root",
         abs(dr - 3.0) < 1e-4 and abs(dh - 3.0) < 1e-4 and abs(dbb - 3.0) < 1e-3 and yaw < 0.01,
         "Root %.6f, Head %.6f, Body bbox %.6f, yaw error %.5f deg" % (dr, dh, dbb, yaw))
    build_pose()
    r0, p0 = W(root), W(game["Hip"])
    cmds.setAttr("RootX_M.translateY", cmds.getAttr("RootX_M.translateY") + 1.0)
    settle()
    gate("the pelvis control moves Hip and leaves the game Root where Main put it",
         abs((W(game["Hip"]) - p0).length() - 1.0) < 1e-3 and (W(root) - r0).length() < 1e-6,
         "Hip moved %.5f, Root %.7f" % ((W(game["Hip"]) - p0).length(), (W(root) - r0).length()))
    build_pose()
    e0 = dict((n, M(game[n])) for n in ("Right_Eye", "Left_Eye", "Head"))
    cmds.setAttr("AimEye_M.translateX", cmds.getAttr("AimEye_M.translateX") + 2.0)
    settle()
    turned = dict((n, ang(e0[n], M(game[n]))) for n in e0)
    gate("the eye aim turns both eye joints and not the head", turned["Right_Eye"] > 5 and turned["Left_Eye"] > 5 and turned["Head"] < 1e-4,
         str(dict((n, round(a, 3)) for n, a in turned.items())))
    build_pose()
    j0 = M(game["Jaw"])
    cmds.setAttr("FKJaw_M.rotateZ", 20.0)
    settle()
    jaw = ang(j0, M(game["Jaw"]))
    cmds.setAttr("FKJaw_M.rotateZ", 0.0)
    gate("the jaw control turns the Jaw joint", abs(jaw - 20.0) < 0.01, "%.4f deg" % jaw)

    # ------------------------------------------------------------ hold / release, the ReBuild helper
    build_pose()
    held = pr.hold()
    unique = dict((n, len(cmds.ls(n) or [])) for n in pr.CLASHING)
    m0 = M(pr.game_joints()["Spine2"])
    cmds.setAttr("FKSpine2_M.rotateX", 20.0)
    settle()
    follows = ang(axis_matrix("x", 20.0) * R(m0), M(pr.game_joints()["Spine2"]))
    cmds.setAttr("FKSpine2_M.rotateX", 0.0)
    released = pr.release()
    game = pr.game_joints()
    build_pose()
    gate("hold() frees the eight fit-joint names and release() gives them back, the drive rename-invariant",
         held == 8 and released == 8 and all(v == 1 for v in unique.values()) and follows < 0.01 and not pr.held()
         and sorted(p.split("|")[-1] for p in game.values()) == sorted(CANON),
         "held %d, unique during hold %s, drive error %.5f deg, released %d" % (held, all(v == 1 for v in unique.values()), follows, released))

    # ------------------------------------------------------------ back at rest
    build_pose()
    d1 = bind_drift()
    fingers = [cmds.getAttr("Fingers_%s.%s" % (s, a)) for s in "RL" for a in ("indexCurl", "spread")]
    gate("Go To Build Pose puts every game joint back on its bind pose after all that",
         d1 < 1e-3 and not any(fingers) and dict((c, cmds.getAttr(c + ".FKIKBlend")) for c in BLENDS) == state["blends"],
         "worst element %.9f" % d1)
    gate("the run keyed nothing", len(cmds.ls(type="animCurve") or []) == curves_before,
         "%d animCurves before, %d after" % (curves_before, len(cmds.ls(type="animCurve") or [])))
except Exception:
    traceback.print_exc()
    gate("the script ran to the end", False, "see the traceback")
finally:
    for step in (lambda: mel.eval("asGoToBuildPose bodySetup;"),
                 lambda: [cmds.setAttr(c + ".FKIKBlend", v) for c, v in state["blends"].items()],
                 lambda: cmds.evaluationManager(mode=state["em"]),
                 lambda: cmds.autoKeyframe(st=state["autoKey"]),
                 lambda: cmds.currentTime(state["time"]),
                 lambda: cmds.select([s for s in state["sel"] if cmds.objExists(s)]) if state["sel"] else cmds.select(clear=True)):
        try:
            step()
        except Exception as exc:
            print("restore step failed:", exc)
    failed = [r for r in results if not r[1]]
    print("restored: EM %s, autoKey %s, time %s, blends %s" % (cmds.evaluationManager(q=True, mode=True)[0], cmds.autoKeyframe(q=True, st=True),
                                                               cmds.currentTime(q=True), dict((c, cmds.getAttr(c + ".FKIKBlend")) for c in BLENDS)))
    if skipped:
        print("%d check(s) skipped around the animator's own constraints: %s" % (len(skipped), [s[0] for s in skipped]))
    if failed:
        print("%d of %d gates failed: %s" % (len(failed), len(results), [r[0] for r in failed]))
    else:
        print("all %d gates passed" % len(results))
