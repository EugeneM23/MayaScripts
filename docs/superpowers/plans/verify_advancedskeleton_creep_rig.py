"""Live gates for the AdvancedSkeleton rig over the Creep creature's UE5-schema skeleton.

`verify_advancedskeleton_ue5_rig.py` (the Manny rig, 2026-09-04) adapted to the Creep
(2026-09-24, `as_creep_rig_procedure.py`): every bone is addressed by LONG PATH under
the Creep's group (a scene may hold a second skeleton with the same bone names), the
bind is checked as BPM * WM = I on the Creep's own skinClusters (the joints'
`bindPose` attribute still holds the T-pose the skeleton was first bound in -- the A-pose
bind was re-baked in place), and gate 25 checks the retarget mark on the rig's group.

Every poke is made with autoKey off on channels that carry no keys and put back; the
evaluation manager is DG for the pokes and restored with the frame, autoKey and the
selection.
"""
import maya.cmds as cmds, maya.mel as mel, math
import maya.api.OpenMaya as om

AS_MEL = "C:/Users/MY PC/Downloads/AdvancedSkeleton/AdvancedSkeleton.mel"
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
EXTRAS = {"root": ["Main"], "ik_hand_gun": ["Wrist_R"], "ik_hand_l": ["Wrist_L"], "ik_hand_r": ["Wrist_R"], "ik_foot_l": ["Ankle_L"], "ik_foot_r": ["Ankle_R"]}
EXTRA_SRC = {"root": "Main", "ik_hand_gun": "hand_r", "ik_hand_l": "hand_l", "ik_hand_r": "hand_r", "ik_foot_l": "foot_l", "ik_foot_r": "foot_r"}
FOLLOWERS = ["ik_foot_root", "ik_hand_root", "interaction", "center_of_mass", "weapon_r", "weapon_l"]   # weapon_test -> weapon_r, weapon_l added (weapon_bones)

FAILS = []
def gate(n, ok, msg):
    print("%s gate %02d: %s" % ("PASS" if ok else "FAIL", n, msg))
    if not ok: FAILS.append((n, msg))

# the Creep's root: at world level since the tidy (it stood in the FBX wrapper |Creep before),
# the one `root` that Main drives
roots = [j for j in (cmds.ls("root", type="joint", long=True) or [])
         if "Main" in [x.split("|")[-1] for c in cmds.listRelatives(j, c=True, type="parentConstraint", fullPath=True) or []
                       for x in cmds.listConnections(c + ".target[0].targetParentMatrix", s=True, d=False) or []]]
ROOT = roots[0]
ue = [ROOT] + (cmds.listRelatives(ROOT, ad=True, type="joint", fullPath=True) or [])
B = dict((p.split("|")[-1], p) for p in ue)
def P(n): return B.get(n, n)                   # a Creep bone by leaf, anything else by its own name
def wm(n): return om.MMatrix(cmds.getAttr(P(n) + ".worldMatrix[0]"))
def wpos(n): return cmds.xform(P(n), q=True, ws=True, t=True)
def dist(a, b): return math.sqrt(sum((i - j) ** 2 for i, j in zip(a, b)))
def rot(m): return om.MTransformationMatrix(m).rotation(asQuaternion=True)
def ang(q1, q2):
    d = q1.inverse() * q2
    return math.degrees(2 * math.acos(max(-1.0, min(1.0, abs(d.w)))))
def driver(j):
    tg = set()
    for c in cmds.listRelatives(P(j), c=True, type="constraint", fullPath=True) or []:
        tg.update(cmds.listConnections(c + ".target[0].targetParentMatrix", s=True, d=False) or [])
    return sorted(tg)

mapping = {}
for a, b in ROWS:
    for side, s in (("_M", ""), ("_R", "_r"), ("_L", "_l")):
        if cmds.objExists(a + side) and cmds.nodeType(a + side) == "joint" and (b + s) in B:
            mapping[a + side] = b + s
rest = {j: cmds.getAttr(j + ".worldMatrix[0]") for j in ue}
def worst_drift():
    w = 0.0; wj = None
    for j, m in rest.items():
        dev = max(abs(a - b) for a, b in zip(m, cmds.getAttr(j + ".worldMatrix[0]")))
        if dev > w: w, wj = dev, j.split("|")[-1]
    return w, wj
def skins():
    out = []
    for sc in cmds.ls(type="skinCluster"):
        if any(i.startswith("|" + ROOT.split("|")[1] + "|") for i in cmds.ls(cmds.skinCluster(sc, q=True, inf=True) or [], long=True)):
            out.append(sc)
    return out

saved = {"autoKey": cmds.autoKeyframe(q=True, st=True), "time": cmds.currentTime(q=True), "sel": cmds.ls(sl=True, long=True) or [],
         "em": cmds.evaluationManager(q=True, mode=True)[0], "blends": {c: cmds.getAttr(c + ".FKIKBlend") for c in ("FKIKArm_L", "FKIKArm_R", "FKIKLeg_L", "FKIKLeg_R", "FKIKSpine_M") if cmds.objExists(c)}}
cmds.autoKeyframe(st=False); cmds.select(clear=True); cmds.evaluationManager(mode="off")
if mel.eval('whatIs "asGoToBuildPose"') == "Unknown":
    mel.eval('source "%s";' % AS_MEL)
try:
    jo = cmds.getAttr(ROOT + ".jointOrient")[0]
    gate(1, len(ue) == 91 and "weapon_r" in B and "weapon_l" in B and not cmds.listRelatives(ROOT, parent=True) and abs(jo[0] + 90) < 1e-3,
         "%d Creep joints under %s, at world level with the Z-up turn in its jointOrient %s (Manny_Rig's shape)"
         % (len(ue), ROOT, [round(v, 4) for v in jo]))
    deform = cmds.sets("DeformSet", q=True) if cmds.objExists("DeformSet") else []
    gate(2, all(cmds.objExists(n) for n in ("Group", "MotionSystem", "DeformationSystem", "Main", "ControlSet")) and len(deform) == 79 and len(mapping) == 79,
         "Group/MotionSystem/DeformationSystem/Main present, DeformSet %d, mapped %d" % (len(deform), len(mapping)))
    # the Creep keeps its own bone lengths rigidly: orientation only, the pelvis position too
    bad = []
    for asj, uej in mapping.items():
        cons = cmds.listRelatives(P(uej), c=True, type="constraint") or []
        kinds = sorted(cmds.nodeType(c) for c in cons)
        want = ["orientConstraint", "pointConstraint"] if uej == "pelvis" else ["orientConstraint"]
        if kinds != want or driver(uej) != [asj]: bad.append((uej, kinds, driver(uej)))
    gate(3, not bad, "79 Creep joints orient-constrained to their AS twin (pelvis point+orient), lengths their own; bad=%s" % bad[:5])
    # the animator's layout (2026-09-24): ik_hand_r/l exactly ON the hands, ik_hand_gun undriven at zero
    ex = dict((j, driver(j)) for j in EXTRAS if j != "ik_hand_gun")
    def on(a, b): return (om.MVector(wpos(a)) - om.MVector(wpos(b))).length(), ang(rot(wm(a)), rot(wm(b)))
    placed = [on("ik_hand_r", "hand_r"), on("ik_hand_l", "hand_l")]
    gun = [v for v in cmds.getAttr(P("ik_hand_gun") + ".t")[0] + cmds.getAttr(P("ik_hand_gun") + ".r")[0]]
    gate(4, all(ex[j] == EXTRAS[j] or ex[j] == [EXTRA_SRC[j]] for j in ex) and all(not driver(j) for j in FOLLOWERS + ["ik_hand_gun"])
         and all(d < 1e-4 and a < 1e-3 for d, a in placed) and max(abs(v) for v in gun) < 1e-6,
         "root<-Main, ik_foot_* <- the feet, ik_hand_r/l ON the hands (%s), ik_hand_gun undriven at zero %s, %d followers unconstrained"
         % (["%.6f cm %.6f deg" % p for p in placed], gun, len(FOLLOWERS)))
    worst_bind = 0.0; wbn = None
    for sc in skins():
        for idx in cmds.getAttr(sc + ".matrix", multiIndices=True) or []:
            src = cmds.listConnections("%s.matrix[%d]" % (sc, idx), s=True, d=False)
            if not src: continue
            p = om.MMatrix(cmds.getAttr("%s.bindPreMatrix[%d]" % (sc, idx))) * om.MMatrix(cmds.getAttr(src[0] + ".worldMatrix[0]"))
            dev = max(abs(p.getElement(r, c) - (r == c)) for r in range(4) for c in range(4))
            if dev > worst_bind: worst_bind, wbn = dev, "%s/%s" % (sc, src[0])
    off = [c for c in cmds.sets("ControlSet", q=True) for a in ("tx", "ty", "tz", "rx", "ry", "rz") if cmds.getAttr(c + "." + a, settable=True) and abs(cmds.getAttr(c + "." + a)) > 1e-3]
    gate(5, worst_bind < 1e-4 and not off, "the zero pose IS the bind: |BPM*WM - I| worst %.2e (%s) on %d skins; controls off default: %s" % (worst_bind, wbn, len(skins()), off[:5]))
    fk = [("FK" + asj, uej) for asj, uej in mapping.items() if asj != "Root_M" and not ("Part" in asj and not asj.startswith("NeckPart")) and cmds.objExists("FK" + asj)]
    frame = max((ang(rot(wm(c)), rot(wm(u))), c) for c, u in fk)
    gate(6, frame[0] < 0.01, "%d FK controls, worst frame angle vs bone %.5f deg (%s)" % (len(fk), frame[0], frame[1]))
    def axis_test(c, uej, axis, deg=25.0):
        W0 = wm(uej); cmds.setAttr(c + ".rotate" + axis, deg); W1 = wm(uej); cmds.setAttr(c + ".rotate" + axis, 0)
        q = rot(W1 * W0.inverse()); a = math.degrees(2 * math.acos(max(-1.0, min(1.0, q.w)))); s = math.sin(math.radians(a) / 2.0)
        ax = (q.x / s, q.y / s, q.z / s) if abs(s) > 1e-9 else (0, 0, 0)
        return a, ax
    for c in ("FKIKLeg_L", "FKIKArm_L", "FKIKArm_R"): cmds.setAttr(c + ".FKIKBlend", 0)
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
    cmds.setAttr("FKIKLeg_L.FKIKBlend", 10)
    gate(7, not bad, "control axis == bone axis on %d control/axis pairs; bad=%s" % (sum(len(t[2]) for t in tests), bad[:6]))
    cmds.setAttr("FKShoulder_L.rotateZ", 30); cmds.setAttr("FKShoulder_R.rotateZ", 30)
    hl = wpos("hand_l"); hr = wpos("hand_r")
    cmds.setAttr("FKShoulder_L.rotateZ", 0); cmds.setAttr("FKShoulder_R.rotateZ", 0)
    rl, rr = wpos("hand_l"), wpos("hand_r")
    asym = max(abs(rl[0] + rr[0]), abs(rl[1] - rr[1]), abs(rl[2] - rr[2]))       # the skeleton's own left/right difference at rest
    mir = max(abs(hl[0] + hr[0]), abs(hl[1] - hr[1]), abs(hl[2] - hr[2]))
    gate(8, mir < asym + 0.05 and dist(hl, rl) > 10, "FKShoulder_L/R rz=30: hands mirrored to %.4f cm (the skeleton's own rest asymmetry %.4f), moved %.1f cm" % (mir, asym, dist(hl, rl)))
    f0 = wpos("foot_l"); p0 = wpos("pelvis"); cmds.setAttr("IKLeg_L.translateY", 10); f1 = wpos("foot_l"); p1 = wpos("pelvis"); cmds.setAttr("IKLeg_L.translateY", 0)
    gate(9, dist(f0, f1) > 5 and dist(p0, p1) < 1e-3, "IKLeg_L ty=10: foot_l moved %.2f cm, pelvis %.6f" % (dist(f0, f1), dist(p0, p1)))
    r0 = wpos("root"); h0 = wpos("hand_r"); cmds.setAttr("Main.translateX", 10)
    dr = [wpos("root")[0] - r0[0], wpos("hand_r")[0] - h0[0]]; cmds.setAttr("Main.translateX", 0)
    gate(10, all(abs(d - 10) < 1e-3 for d in dr), "Main tx=10 moves root and hand_r by %s" % ["%.4f" % d for d in dr])
    cmds.setAttr("FKIKArm_L.FKIKBlend", 10); h0 = wpos("hand_l"); cmds.setAttr("IKArm_L.translateY", -10); h1 = wpos("hand_l")
    cmds.setAttr("IKArm_L.translateY", 0); cmds.setAttr("FKIKArm_L.FKIKBlend", 0)
    gate(11, dist(h0, h1) > 5, "FKIKArm_L to IK, IKArm_L ty=-10 moved hand_l %.2f cm" % dist(h0, h1))
    m0 = wm("index_02_l"); cmds.setAttr("Fingers_L.indexCurl", 5); a = ang(rot(m0), rot(wm("index_02_l"))); cmds.setAttr("Fingers_L.indexCurl", 0)
    gate(12, a > 10, "Fingers_L.indexCurl=5 turned index_02_l by %.2f deg" % a)
    # the Creep's twist joints REST turned against the forearm (lowerarm_twist_01 by 26.7 deg), so a
    # difference of angles to the forearm is not the twist; measure each joint's turn in the forearm's frame
    def rel(t): return rot(wm(t) * wm("lowerarm_l").inverse())
    t1a, t2a = rel("lowerarm_twist_01_l"), rel("lowerarm_twist_02_l"); cmds.setAttr("FKWrist_L.rotateX", 60)
    t1, t2 = ang(t1a, rel("lowerarm_twist_01_l")), ang(t2a, rel("lowerarm_twist_02_l")); cmds.setAttr("FKWrist_L.rotateX", 0)
    gate(13, t1 > t2 + 5 and t1 > 20, "FKWrist_L rx=60: lowerarm_twist_01_l (near wrist) turns %.1f deg in the forearm's frame, twist_02 (near elbow) %.1f deg" % (t1, t2))
    w, wj = worst_drift()
    gate(14, len(skins()) >= 5 and w < 1e-3, "%d Creep skins; drift after all pokes %.9f (%s)" % (len(skins()), w, wj))
    keyed = [j for j in ue if cmds.listConnections(j, type="animCurve", s=True, d=False)] + [c for c in cmds.sets("ControlSet", q=True) if cmds.listConnections(c, type="animCurve", s=True, d=False)]
    gate(15, not keyed, "no animCurves on Creep joints or controls (%d)" % len(keyed))
    # nothing but joints and the rig's constraints under root (a mesh under a bone rides into every
    # animation export), the meshes named for the character in the rig's Geometry group, and no sword
    # in the rig at all since 2026-09-24 -- a weapon is the catalog's, added and removed as on any rig
    odd = sorted(set((cmds.nodeType(k), k.split("|")[-1]) for k in (cmds.listRelatives(ROOT, ad=True, fullPath=True) or [])
                     if cmds.nodeType(k) != "joint" and not cmds.nodeType(k).endswith("Constraint")))
    geo = cmds.ls("|Group|Geometry", long=True)[0]
    kids = cmds.listRelatives(geo, children=True) or []
    gate(16, not odd and {"Creep_Body", "Creep_Back", "Creep_Arm_L", "Creep_Arm_R", "Creep_Face"} <= set(kids) and "Creep_Props" not in kids,
         "under root only joints and constraints %s; Geometry %s, no props" % (odd, kids))
    src = {mm: cmds.listConnections(mm + ".matrixIn[1]", s=True, d=False, p=True) for mm in ("NeckInbetweenMM_M", "NeckPart1InbetweenMM_M")}
    gate(17, all(v == ["FKOffsetNeck_M.worldInverseMatrix"] for v in src.values()) and max(abs(v) for v in cmds.getAttr("FKXNeck_M.r")[0]) < 1e-3,
         "neck in-between network in Offset space %s, FKXNeck_M local rotate %s" % (src, [round(v, 4) for v in cmds.getAttr("FKXNeck_M.r")[0]]))
    cmds.setAttr("FKSpine3_M.rotateZ", 20); cmds.setAttr("RootX_M.translateY", 5); mel.eval("asGoToBuildPose bodySetup;")
    w, wj = worst_drift()
    if w >= 1e-3: cmds.setAttr("FKSpine3_M.rotateZ", 0); cmds.setAttr("RootX_M.translateY", 0)
    gate(18, w < 1e-3, "asGoToBuildPose after posing spine+root: drift %.9f (%s)" % (w, wj))
    # the IK hands and toes carry their bone's frame; the IK FEET stand LEVEL in AS's own world frame
    # (the animator, 2026-09-24: the foot bones' small turn made the foot controls stand tilted)
    ik = [("IKArm_L", "hand_l"), ("IKArm_R", "hand_r"), ("IKToes_L", "ball_l"), ("IKToes_R", "ball_r")]
    frame = max((ang(rot(wm(c)), rot(wm(u))), c) for c, u in ik)
    level = max(ang(rot(wm(c)), om.MQuaternion()) for c in ("IKLeg_L", "IKLeg_R"))
    aligned = max(ang(rot(wm("IKLeg_" + s)), rot(wm("AlignIKToAnkle_" + s))) for s in "LR")
    gate(19, frame[0] < 0.01 and level < 1e-4 and aligned < 1e-4,
         "IK hands/toes on their bones' frames (worst %.5f deg, %s); IK feet level: %.6f deg off world, align targets %.6f deg off them" % (frame[0], frame[1], level, aligned))
    bad = []
    cmds.setAttr("FKIKArm_L.FKIKBlend", 10)
    world_axes = {"X": (1, 0, 0), "Y": (0, 1, 0), "Z": (0, 0, 1)}
    for c, uej in (("IKLeg_L", "foot_l"), ("IKLeg_R", "foot_r"), ("IKArm_L", "hand_l")):
        for i, axis in enumerate("XYZ"):
            if c.startswith("IKLeg"):          # a level control turns the foot about the WORLD axis
                W0 = wm(uej); cmds.setAttr(c + ".rotate" + axis, 25); W1 = wm(uej); cmds.setAttr(c + ".rotate" + axis, 0)
                qq = rot(W0.inverse() * W1); a = math.degrees(2 * math.acos(max(-1.0, min(1.0, qq.w)))); s = math.sin(math.radians(a) / 2.0)
                ax = (qq.x / s, qq.y / s, qq.z / s) if abs(s) > 1e-9 else (0, 0, 0)
            else:
                a, ax = axis_test(c, uej, axis)
            if not (abs(a - 25) < 0.05 and abs(abs(ax[i]) - 1) < 1e-3): bad.append((c, axis, round(a, 3), [round(v, 3) for v in ax]))
    cmds.setAttr("FKIKArm_L.FKIKBlend", saved["blends"]["FKIKArm_L"])
    gate(20, not bad, "IKArm turns the hand about the hand's axes, IKLeg the foot about the world's, 9 pairs; bad=%s" % bad)
    cmds.setAttr("FKIKArm_L.FKIKBlend", 0); cmds.setAttr("FKShoulder_L.rotateZ", 30); cmds.setAttr("FKElbow_L.rotateZ", -40); cmds.setAttr("FKWrist_L.rotateX", 20)
    hfk = wm("hand_l"); mel.eval('asAlignIK2FK "" {"FKIKArm_L"};'); cmds.setAttr("FKIKArm_L.FKIKBlend", 10); d_arm = max(abs(a - b) for a, b in zip(list(hfk), list(wm("hand_l"))))
    cmds.setAttr("FKIKLeg_L.FKIKBlend", 10); cmds.setAttr("IKLeg_L.translateY", 12); cmds.setAttr("IKLeg_L.rotateZ", 20); cmds.setAttr("IKLeg_L.rotateX", 15)
    fik = wm("foot_l"); mel.eval('asAlignFK2IK "" {"FKIKLeg_L"};'); cmds.setAttr("FKIKLeg_L.FKIKBlend", 0); d_leg = max(abs(a - b) for a, b in zip(list(fik), list(wm("foot_l"))))
    mel.eval("asGoToBuildPose bodySetup;")
    cmds.setAttr("FKIKLeg_L.FKIKBlend", 0); cmds.setAttr("FKHip_L.rotateZ", 20); cmds.setAttr("FKKnee_L.rotateZ", -30); cmds.setAttr("FKAnkle_L.rotateY", 10)
    ffk = wm("foot_l"); mel.eval('asAlignIK2FK "" {"FKIKLeg_L"};'); cmds.setAttr("FKIKLeg_L.FKIKBlend", 10)
    d_leg2 = max(abs(a - b) for a, b in zip(list(ffk), list(wm("foot_l")))); d_leg2r = ang(rot(ffk), rot(wm("foot_l")))
    mel.eval("asGoToBuildPose bodySetup;")
    for c, v in saved["blends"].items(): cmds.setAttr(c + ".FKIKBlend", v)
    w, wj = worst_drift()
    gate(21, d_arm < 0.01 and d_leg < 0.01 and d_leg2 < 0.01 and d_leg2r < 0.01 and w < 1e-3,
         "align FK->IK arm %.6f, IK->FK leg %.6f, FK->IK leg %.6f (%.5f deg); back to build pose drift %.9f" % (d_arm, d_leg, d_leg2, d_leg2r, w))
    badf = []
    sp0 = {h: cmds.getAttr("Fingers_%s.spread" % h) for h in "LR"}
    for hand, S in (("L", "l"), ("R", "r")):
        for finger, bones in (("index", ["index_01", "index_02", "index_03"]), ("middle", ["middle_01", "middle_02", "middle_03"]), ("ring", ["ring_01", "ring_02", "ring_03"]), ("pinky", ["pinky_01", "pinky_02", "pinky_03"]), ("thumb", ["thumb_02", "thumb_03"])):
            # each phalanx's turn against ITS PARENT, in its own frame: the Creep's right pinky_02 rests rolled
            # 16 deg against pinky_01, so the world delta (its own curl composed with the parent's) is not about its Z
            def local(b): return wm(b) * wm(cmds.listRelatives(P(b), parent=True, fullPath=True)[0]).inverse()
            W = {b: local(b + "_" + S) for b in bones}
            cmds.setAttr("Fingers_%s.%sCurl" % (hand, finger), 5)
            for b in bones:
                q = rot(local(b + "_" + S) * W[b].inverse()); a = math.degrees(2 * math.acos(max(-1.0, min(1.0, q.w)))); s = math.sin(math.radians(a) / 2.0)
                az = q.z / s if abs(s) > 1e-9 else 0.0
                if not (a > 5 and abs(az - 1.0) < 0.01): badf.append((hand, finger, b, round(a, 2), round(az, 3)))
            cmds.setAttr("Fingers_%s.%sCurl" % (hand, finger), 0)
        d0 = dist(wpos("index_03_" + S), wpos("pinky_03_" + S)); cmds.setAttr("Fingers_%s.spread" % hand, sp0[hand] + 5)
        d1 = dist(wpos("index_03_" + S), wpos("pinky_03_" + S)); cmds.setAttr("Fingers_%s.spread" % hand, sp0[hand])
        if d1 - d0 < 2: badf.append((hand, "spread", round(d1 - d0, 2)))
    gate(22, not badf, "Fingers curl turns all 28 phalanges about their bone +Z and spread opens both hands; bad=%s" % badf[:6])
    sdk = cmds.ls("SDKFK*", type="transform")
    gate(23, len(sdk) == 28 and all((cmds.listRelatives(g, p=True) or [""])[0].startswith("UEAxis") for g in sdk), "%d SDK groups, each under its UEAxis frame node" % len(sdk))
    def levels(c, i, space=om.MSpace.kObject):
        s = cmds.listRelatives(c, s=True, type="nurbsCurve", fullPath=True)[0]
        sl = om.MSelectionList(); sl.add(s)
        return sorted(set(round(q[i], 1) for q in om.MFnNurbsCurve(sl.getDagPath(0)).cvPositions(space)))
    cubes = all(len(levels(c, i)) == 2 and abs(sum(levels(c, i))) < 0.05 for c in ("IKArm_L", "IKArm_R") for i in range(3))
    feet = all(len(levels(c, 1, om.MSpace.kWorld)) == 2 for c in ("IKLeg_L", "IKLeg_R"))
    gate(24, cubes and feet, "IK hand cubes axis-aligned on the hand frame (x levels %s), foot boxes LEVEL - two world heights %s / %s"
         % (levels("IKArm_L", 0), levels("IKLeg_L", 1, om.MSpace.kWorld), levels("IKLeg_R", 1, om.MSpace.kWorld)))
    mode = cmds.getAttr("Group.skeldarRetarget") if cmds.attributeQuery("skeldarRetarget", node="Group", exists=True) else None
    gate(25, mode == "rotation", "Group.skeldarRetarget = %r (the retarget copies rotations only onto this rig)" % mode)
    # 2026-09-24, the animator: «кости скелета и кости рига не совпадают, как минимум на левой руке» --
    # the left side was AS's mirror of the right fit while the pose is not symmetric (fingers 1-3 cm),
    # and AS's twist / in-between joints stood at its own even spacing (upper-arm twists 2.35 / 4.70 cm).
    # Now: every deformation joint ON its bone, both sides; the twists as close as their bones' own
    # distance off the bone line allows (the Creep's upper-arm twists stand 0.07-0.17 cm off it).
    cmds.currentTime(saved["time"])
    offs = sorted((((om.MVector(wpos(a)) - om.MVector(wpos(g))).length(), a, g) for a, g in mapping.items()), reverse=True)
    parts = [o for o in offs if "Part" in o[1] and not o[1].startswith("NeckPart")]
    rest_ = [o for o in offs if not ("Part" in o[1] and not o[1].startswith("NeckPart"))]
    gate(26, rest_[0][0] < 0.002 and parts[0][0] < 0.2,
         "rig joints ON the skeleton's: worst %.4f cm (%s), twist parts worst %.4f cm (%s); left hand worst %.4f"
         % (rest_[0][0], rest_[0][1], parts[0][0], parts[0][1],
            max(o[0] for o in offs if o[1].endswith("_L") and ("Finger" in o[1] or o[1].startswith("Wrist")))))
finally:
    for c, v in saved["blends"].items(): cmds.setAttr(c + ".FKIKBlend", v)
    cmds.evaluationManager(mode=saved["em"]); cmds.autoKeyframe(st=saved["autoKey"]); cmds.currentTime(saved["time"])
    if saved["sel"]: cmds.select(saved["sel"])
    else: cmds.select(clear=True)
    print("restored: em %s autoKey %s time %s" % (cmds.evaluationManager(q=True, mode=True)[0], cmds.autoKeyframe(q=True, st=True), cmds.currentTime(q=True)))
print("RESULT: %d of 26 gates failed %s" % (len(FAILS), FAILS))
