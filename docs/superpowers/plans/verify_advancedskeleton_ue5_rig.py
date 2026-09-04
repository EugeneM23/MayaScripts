"""Live gates for the AdvancedSkeleton rig that drives the UE5 Manny skeleton.

Send through the command-port bridge into the ANIMATOR'S OPEN SCENE holding the
rig built on 2026-09-04 (AdvancedSkeleton 6.797, fitSkeletons/UE5.ma, Name Matcher
"Constraint to Joints", FK controls re-oriented onto the UE bone frames).

Read-only in effect: every poke is made with autoKey off, on channels that carry
no keys, and put back before the next gate. The evaluation manager is switched to
DG for the pokes (the 2026-09-04 crash coincided with the first parallel
evaluation of the freshly wired graph) and restored at the end, together with the
frame, autoKey and the selection.
"""
import maya.cmds as cmds, maya.mel as mel, math
import maya.api.OpenMaya as om

AS_MEL = "C:/Users/MY PC/Downloads/AdvancedSkeleton/AdvancedSkeleton.mel"

# AS deformation joint -> UE bone.  Name Matcher "Unreal5" table plus the twist /
# in-between rows added by hand (UE numbers the lower twists from the far end).
ROWS = [("Root", "pelvis"), ("Spine1", "spine_01"), ("Spine2", "spine_02"), ("Spine3", "spine_03"), ("Spine4", "spine_04"),
        ("Spine5", "spine_05"), ("Scapula", "clavicle"), ("Shoulder", "upperarm"), ("Elbow", "lowerarm"), ("Wrist", "hand"),
        ("IndexFinger0", "index_metacarpal"), ("IndexFinger1", "index_01"), ("IndexFinger2", "index_02"), ("IndexFinger3", "index_03"),
        ("MiddleFinger0", "middle_metacarpal"), ("MiddleFinger1", "middle_01"), ("MiddleFinger2", "middle_02"), ("MiddleFinger3", "middle_03"),
        ("RingFinger0", "ring_metacarpal"), ("RingFinger1", "ring_01"), ("RingFinger2", "ring_02"), ("RingFinger3", "ring_03"),
        ("PinkyFinger0", "pinky_metacarpal"), ("PinkyFinger1", "pinky_01"), ("PinkyFinger2", "pinky_02"), ("PinkyFinger3", "pinky_03"),
        ("ThumbFinger1", "thumb_01"), ("ThumbFinger2", "thumb_02"), ("ThumbFinger3", "thumb_03"),
        ("Neck", "neck_01"), ("Head", "head"), ("Hip", "thigh"), ("Knee", "calf"), ("Ankle", "foot"), ("Toes", "ball"),
        ("ShoulderPart1", "upperarm_twist_01"), ("ShoulderPart2", "upperarm_twist_02"),
        ("ElbowPart1", "lowerarm_twist_02"), ("ElbowPart2", "lowerarm_twist_01"),
        ("HipPart1", "thigh_twist_01"), ("HipPart2", "thigh_twist_02"),
        ("KneePart1", "calf_twist_02"), ("KneePart2", "calf_twist_01"), ("NeckPart1", "neck_02")]
EXTRAS = {"root": ["Main"], "ik_hand_gun": ["hand_r"], "ik_hand_l": ["hand_l"], "ik_hand_r": ["hand_r"], "ik_foot_l": ["foot_l"], "ik_foot_r": ["foot_r"]}
FOLLOWERS = ["weapon_l", "weapon_r", "ik_foot_root", "ik_hand_root", "interaction", "center_of_mass", "camera_root", "camera_bone"]

FAILS = []
def gate(n, ok, msg):
    print("%s gate %02d: %s" % ("PASS" if ok else "FAIL", n, msg))
    if not ok: FAILS.append((n, msg))
def wm(n): return om.MMatrix(cmds.getAttr(n + ".worldMatrix[0]"))
def wpos(n): return cmds.xform(n, q=True, ws=True, t=True)
def dist(a, b): return math.sqrt(sum((i - j) ** 2 for i, j in zip(a, b)))
def rot(m): return om.MTransformationMatrix(m).rotation(asQuaternion=True)
def ang(q1, q2):
    d = q1.inverse() * q2
    return math.degrees(2 * math.acos(max(-1.0, min(1.0, abs(d.w)))))
def driver(j):
    tg = set()
    for c in cmds.listRelatives(j, c=True, type="constraint") or []:
        tg.update(cmds.listConnections(c + ".target[0].targetParentMatrix", s=True, d=False) or [])
    return sorted(tg)

mapping = {}
for a, b in ROWS:
    for side, s in (("_M", ""), ("_R", "_r"), ("_L", "_l")):
        if cmds.objExists(a + side) and cmds.nodeType(a + side) == "joint":
            mapping[a + side] = b + s
ue = ["|root"] + (cmds.listRelatives("|root", ad=True, type="joint", fullPath=True) or [])
rest = {j: cmds.getAttr(j + ".worldMatrix[0]") for j in ue}
def worst_drift():
    w = 0.0; wj = None
    for j, m in rest.items():
        dev = max(abs(a - b) for a, b in zip(m, cmds.getAttr(j + ".worldMatrix[0]")))
        if dev > w: w, wj = dev, j.split("|")[-1]
    return w, wj

saved = {"autoKey": cmds.autoKeyframe(q=True, st=True), "time": cmds.currentTime(q=True), "sel": cmds.ls(sl=True, long=True) or [],
         "em": cmds.evaluationManager(q=True, mode=True)[0], "blends": {c: cmds.getAttr(c + ".FKIKBlend") for c in ("FKIKArm_L", "FKIKArm_R", "FKIKLeg_L", "FKIKLeg_R", "FKIKSpine_M") if cmds.objExists(c)}}
cmds.autoKeyframe(st=False); cmds.select(clear=True); cmds.evaluationManager(mode="off")
if mel.eval('whatIs "asGoToBuildPose"') == "Unknown":
    mel.eval('source "%s";' % AS_MEL)
try:
    # 1 the game skeleton is intact
    ns = [n for n in (cmds.namespaceInfo(lon=True, r=True) or []) if n not in ("UI", "shared")]
    gate(1, len(ue) == 93 and cmds.listRelatives("root", p=True) is None and not ns,
         "%d UE joints under |root, root at world level, no namespaces %s" % (len(ue), ns))
    # 2 the AS rig is present
    deform = cmds.sets("DeformSet", q=True) if cmds.objExists("DeformSet") else []
    gate(2, all(cmds.objExists(n) for n in ("Group", "MotionSystem", "DeformationSystem", "Main", "ControlSet")) and len(deform) == 79 and len(mapping) == 79,
         "Group/MotionSystem/DeformationSystem/Main present, DeformSet %d, mapped %d" % (len(deform), len(mapping)))
    # 3 every mapped bone is driven by its AS twin with point+orient+scale
    bad = []
    for asj, uej in mapping.items():
        cons = cmds.listRelatives(uej, c=True, type="constraint") or []
        kinds = sorted(cmds.nodeType(c) for c in cons)
        if kinds != ["orientConstraint", "pointConstraint", "scaleConstraint"] or driver(uej) != [asj]: bad.append((uej, kinds, driver(uej)))
    gate(3, not bad, "79 UE joints point+orient+scale constrained to their AS twin; bad=%s" % bad[:5])
    # 4 root and the ik helpers; the rest follow their parents
    gate(4, all(driver(j) == d for j, d in EXTRAS.items()) and all(not driver(j) for j in FOLLOWERS),
         "root<-Main, ik_hand_gun/r<-hand_r, ik_hand_l<-hand_l, ik_foot_*<-foot_*, 8 followers unconstrained")
    # 5 the zero pose is the bind pose (joint.bindPose is the world matrix at bind; Manny's own calf_l is 0.07 off)
    infl = set(cmds.ls(cmds.skinCluster("skinCluster1", q=True, inf=True), long=True))
    wb = 0.0; wbj = None
    for j in ue:
        if j not in infl: continue
        dev = max(abs(a - b) for a, b in zip(cmds.getAttr(j + ".bindPose"), rest[j]))
        if dev > wb: wb, wbj = dev, j.split("|")[-1]
    off = [c for c in cmds.sets("ControlSet", q=True) for a in ("tx", "ty", "tz", "rx", "ry", "rz") if cmds.getAttr(c + "." + a, settable=True) and abs(cmds.getAttr(c + "." + a)) > 1e-3]
    gate(5, wb < 0.1 and not off, "influence joints vs joint.bindPose: worst %.4f cm (%s); controls off default: %s" % (wb, wbj, off[:5]))
    # 6 FK control frames == UE bone frames (RootX / FKRoot stay in AS's world frame by design)
    fk = [("FK" + asj, uej) for asj, uej in mapping.items() if asj != "Root_M" and not ("Part" in asj and not asj.startswith("NeckPart")) and cmds.objExists("FK" + asj)]
    frame = max((ang(rot(wm(c)), rot(wm(u))), c) for c, u in fk)
    gate(6, frame[0] < 0.01, "%d FK controls, worst frame angle vs bone %.5f deg (%s)" % (len(fk), frame[0], frame[1]))
    # 7 rotating a control about its X/Y/Z turns the bone about ITS X/Y/Z
    def axis_test(c, uej, axis, deg=25.0):
        W0 = wm(uej); cmds.setAttr(c + ".rotate" + axis, deg); W1 = wm(uej); cmds.setAttr(c + ".rotate" + axis, 0)
        q = rot(W1 * W0.inverse()); a = math.degrees(2 * math.acos(max(-1.0, min(1.0, q.w)))); s = math.sin(math.radians(a) / 2.0)
        ax = (q.x / s, q.y / s, q.z / s) if abs(s) > 1e-9 else (0, 0, 0)
        return a, ax
    cmds.setAttr("FKIKLeg_L.FKIKBlend", 0)
    tests = [("FKShoulder_L", "upperarm_l", "YZ", 25), ("FKElbow_R", "lowerarm_r", "YZ", 25), ("FKWrist_L", "hand_l", "XYZ", 25),
             ("FKIndexFinger1_L", "index_01_l", "XYZ", 25), ("FKThumbFinger2_R", "thumb_02_r", "XYZ", 25), ("FKPinkyFinger3_L", "pinky_03_l", "XYZ", 25),
             ("FKHip_L", "thigh_l", "YZ", 25), ("FKKnee_L", "calf_l", "YZ", 25), ("FKAnkle_L", "foot_l", "XYZ", 25),
             ("FKSpine3_M", "spine_03", "XYZ", 25), ("FKHead_M", "head", "XYZ", 25), ("FKNeck_M", "neck_01", "XYZ", None)]
    bad = []
    for c, uej, axes, expect in tests:
        for i, axis in enumerate("XYZ"):
            if axis not in axes: continue
            a, ax = axis_test(c, uej, axis)
            ok = (abs(abs(ax[i]) - 1) < 1e-3) and (a > 5 if expect is None else abs(a - expect) < 0.05)
            if not ok: bad.append((c, axis, round(a, 3), [round(v, 3) for v in ax]))
    cmds.setAttr("FKIKLeg_L.FKIKBlend", saved["blends"]["FKIKLeg_L"])
    gate(7, not bad, "control axis == bone axis on %d control/axis pairs (Hip/Knee/Shoulder/Elbow X roll goes to the twist joints by AS design, measured 0.0 on the joint itself); bad=%s" % (sum(len(t[2]) for t in tests), bad[:6]))
    # 8 equal values on both sides give a mirrored pose
    cmds.setAttr("FKShoulder_L.rotateZ", 30); cmds.setAttr("FKShoulder_R.rotateZ", 30)
    hl = wpos("hand_l"); hr = wpos("hand_r")
    cmds.setAttr("FKShoulder_L.rotateZ", 0); cmds.setAttr("FKShoulder_R.rotateZ", 0)
    mir = max(abs(hl[0] + hr[0]), abs(hl[1] - hr[1]), abs(hl[2] - hr[2]))
    gate(8, mir < 0.05 and dist(hl, wpos("hand_l")) > 10, "FKShoulder_L/R rz=30: hands mirrored to %.4f cm, moved %.1f cm" % (mir, dist(hl, wpos("hand_l"))))
    # 9 IK leg, 10 Main, 11 FK/IK switch on the arm
    f0 = wpos("foot_l"); p0 = wpos("pelvis"); cmds.setAttr("IKLeg_L.translateY", 10); f1 = wpos("foot_l"); p1 = wpos("pelvis"); cmds.setAttr("IKLeg_L.translateY", 0)
    gate(9, dist(f0, f1) > 5 and dist(p0, p1) < 1e-3, "IKLeg_L ty=10: foot_l moved %.2f cm, pelvis %.6f" % (dist(f0, f1), dist(p0, p1)))
    r0 = wpos("root"); h0 = wpos("hand_r"); cmds.setAttr("Main.translateX", 10)
    dr = [wpos("root")[0] - r0[0], wpos("hand_r")[0] - h0[0]]; cmds.setAttr("Main.translateX", 0)
    gate(10, all(abs(d - 10) < 1e-3 for d in dr), "Main tx=10 moves root and hand_r by %s" % ["%.4f" % d for d in dr])
    cmds.setAttr("FKIKArm_L.FKIKBlend", 10); h0 = wpos("hand_l"); cmds.setAttr("IKArm_L.translateY", -10); h1 = wpos("hand_l")
    cmds.setAttr("IKArm_L.translateY", 0); cmds.setAttr("FKIKArm_L.FKIKBlend", saved["blends"]["FKIKArm_L"])
    gate(11, dist(h0, h1) > 5, "FKIKArm_L to IK, IKArm_L ty=-10 moved hand_l %.2f cm" % dist(h0, h1))
    # 12 finger curl attribute, 13 forearm twist distribution
    m0 = wm("index_02_l"); cmds.setAttr("Fingers_L.indexCurl", 5); a = ang(rot(m0), rot(wm("index_02_l"))); cmds.setAttr("Fingers_L.indexCurl", 0)
    gate(12, a > 10, "Fingers_L.indexCurl=5 turned index_02_l by %.2f deg" % a)
    def roll(t): return ang(rot(wm("lowerarm_l")), rot(wm(t)))
    t1a, t2a = roll("lowerarm_twist_01_l"), roll("lowerarm_twist_02_l"); cmds.setAttr("FKWrist_L.rotateX", 60)
    t1b, t2b = roll("lowerarm_twist_01_l"), roll("lowerarm_twist_02_l"); cmds.setAttr("FKWrist_L.rotateX", 0)
    gate(13, abs(t1b - t1a) > abs(t2b - t2a) + 5 and abs(t1b - t1a) > 20, "FKWrist_L rx=60: lowerarm_twist_01_l (near wrist) %.1f deg, twist_02 (near elbow) %.1f deg" % (abs(t1b - t1a), abs(t2b - t2a)))
    # 14 skin and rest, 15 no keys, 16 export shape, 17 neck network, 18 build pose
    sk = {sc: len(cmds.skinCluster(sc, q=True, inf=True) or []) for sc in ("skinCluster1", "skinCluster9")}
    w, wj = worst_drift()
    gate(14, sk == {"skinCluster1": 89, "skinCluster9": 89} and w < 1e-3, "skin %s; drift after all pokes %.9f (%s)" % (sk, w, wj))
    keyed = [j for j in ue if cmds.listConnections(j, type="animCurve", s=True, d=False)] + [c for c in cmds.sets("ControlSet", q=True) if cmds.listConnections(c, type="animCurve", s=True, d=False)]
    gate(15, not keyed, "no animCurves on UE joints or controls (%d)" % len(keyed))
    odd = sorted(set(cmds.nodeType(k) for k in (cmds.listRelatives("|root", ad=True, fullPath=True) or []) if cmds.nodeType(k) != "joint"))
    gate(16, all(o.endswith("Constraint") for o in odd), "non-joint nodes under root: %s" % odd)
    src = {mm: cmds.listConnections(mm + ".matrixIn[1]", s=True, d=False, p=True) for mm in ("NeckInbetweenMM_M", "NeckPart1InbetweenMM_M")}
    gate(17, all(v == ["FKOffsetNeck_M.worldInverseMatrix"] for v in src.values()) and max(abs(v) for v in cmds.getAttr("FKXNeck_M.r")[0]) < 1e-3,
         "neck in-between network in Offset space %s, FKXNeck_M local rotate %s" % (src, [round(v, 4) for v in cmds.getAttr("FKXNeck_M.r")[0]]))
    cmds.setAttr("FKSpine3_M.rotateZ", 20); cmds.setAttr("RootX_M.translateY", 5); mel.eval("asGoToBuildPose bodySetup;")
    w, wj = worst_drift()
    if w >= 1e-3: cmds.setAttr("FKSpine3_M.rotateZ", 0); cmds.setAttr("RootX_M.translateY", 0)
    gate(18, w < 1e-3, "asGoToBuildPose after posing spine+root: drift %.9f (%s)" % (w, wj))
    # 19 IK control frames == bone frames (2026-09-04 evening, «на ИК контролах ног ... оси не совпадают»)
    ik = [("IKLeg_L", "foot_l"), ("IKLeg_R", "foot_r"), ("IKArm_L", "hand_l"), ("IKArm_R", "hand_r"), ("IKToes_L", "ball_l"), ("IKToes_R", "ball_r")]
    frame = max((ang(rot(wm(c)), rot(wm(u))), c) for c, u in ik)
    gate(19, frame[0] < 0.01 and all(cmds.attributeQuery("CustomOrient", node="AlignIKTo%s_%s" % (j, s), exists=True) for j in ("Ankle", "Wrist") for s in "LR"),
         "6 IK controls, worst frame angle vs bone %.5f deg (%s); AlignIKToAnkle/Wrist carry CustomOrient (IKToes only positions an ikHandle)" % (frame[0], frame[1]))
    # 20 rotating an IK end control about its X/Y/Z turns the bone about ITS X/Y/Z
    bad = []
    cmds.setAttr("FKIKArm_L.FKIKBlend", 10)
    for c, uej in (("IKLeg_L", "foot_l"), ("IKLeg_R", "foot_r"), ("IKArm_L", "hand_l")):
        for i, axis in enumerate("XYZ"):
            a, ax = axis_test(c, uej, axis)
            if not (abs(a - 25) < 0.05 and abs(abs(ax[i]) - 1) < 1e-3): bad.append((c, axis, round(a, 3), [round(v, 3) for v in ax]))
    cmds.setAttr("FKIKArm_L.FKIKBlend", saved["blends"]["FKIKArm_L"])
    gate(20, not bad, "IK control axis == bone axis on 9 pairs; bad=%s" % bad)
    # 21 FK->IK align on the arm and IK->FK align on the leg still land (the AlignIKTo update)
    cmds.setAttr("FKIKArm_L.FKIKBlend", 0); cmds.setAttr("FKShoulder_L.rotateZ", 30); cmds.setAttr("FKElbow_L.rotateZ", -40); cmds.setAttr("FKWrist_L.rotateX", 20)
    hfk = wm("hand_l"); mel.eval('asAlignIK2FK "" {"FKIKArm_L"};'); cmds.setAttr("FKIKArm_L.FKIKBlend", 10); d_arm = max(abs(a - b) for a, b in zip(list(hfk), list(wm("hand_l"))))
    cmds.setAttr("FKIKLeg_L.FKIKBlend", 10); cmds.setAttr("IKLeg_L.translateY", 12); cmds.setAttr("IKLeg_L.rotateZ", 20); cmds.setAttr("IKLeg_L.rotateX", 15)
    fik = wm("foot_l"); mel.eval('asAlignFK2IK "" {"FKIKLeg_L"};'); cmds.setAttr("FKIKLeg_L.FKIKBlend", 0); d_leg = max(abs(a - b) for a, b in zip(list(fik), list(wm("foot_l"))))
    mel.eval("asGoToBuildPose bodySetup;")
    for c, v in saved["blends"].items(): cmds.setAttr(c + ".FKIKBlend", v)
    w, wj = worst_drift()
    gate(21, d_arm < 0.01 and d_leg < 0.01 and w < 1e-3, "align FK->IK arm %.6f, IK->FK leg %.6f (world-matrix max diff); back to build pose drift %.9f" % (d_arm, d_leg, w))
finally:
    for c, v in saved["blends"].items(): cmds.setAttr(c + ".FKIKBlend", v)
    cmds.evaluationManager(mode=saved["em"]); cmds.autoKeyframe(st=saved["autoKey"]); cmds.currentTime(saved["time"])
    if saved["sel"]: cmds.select(saved["sel"])
    else: cmds.select(clear=True)
    print("restored: em %s autoKey %s time %s sel %s" % (cmds.evaluationManager(q=True, mode=True)[0], cmds.autoKeyframe(q=True, st=True), cmds.currentTime(q=True), cmds.ls(sl=True)))
print("RESULT: %d of 21 gates failed %s" % (len(FAILS), FAILS))
