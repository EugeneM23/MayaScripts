"""Live gates for the PlayerMale retarget (maya_pmretarget), in the animator's OPEN scene.

Three sources, each built or imported by the script itself and removed again by UUID:

  A. OWN    -- a copy of the rig's own game skeleton, keyed with a known take (rotations, a
               root travel, and one bone TRANSLATION that a rotation-only retarget must
               ignore); AdvancedSkeleton's own Bake and Disconnect are then pressed through
               MEL and the rig is measured playing the take with the source gone.
  B. UE5    -- a Manny built from the shipped bind-pose template (93 joints), 10x our size,
               keyed with a take; bone DIRECTIONS must match and the travel must be scaled.
  C. MIXAMO -- the animator's own `Sweep Fall.fbx` imported into a throwaway namespace.

Everything is put back: baked keys (on controls that carried none), the build pose, the
FKIK blends, the playback range, the frame, autoKey, the evaluation mode, the selection,
the FBX import mode.  Poses never go through a control that carries the animator's own
constraint (the module skips those and names them; the gates exclude their bones).

Design: docs/superpowers/specs/2026-09-05-pmretarget-design.md
"""
import json
import math
import os
import sys
import traceback

import maya.api.OpenMaya as om
import maya.cmds as cmds
import maya.mel as mel

REPO = "C:/!!!Work/MayaScripts"
MIXAMO_FBX = "C:/Users/MY PC/Downloads/Sweep Fall.fbx"
END = 20.0
SAMPLES = [0.0, 6.0, 13.0, 20.0]
BLENDS = ("FKIKArm_R", "FKIKArm_L", "FKIKLeg_R", "FKIKLeg_L")

if REPO not in sys.path:
    sys.path.insert(0, REPO)
sys.modules.pop("maya_pmretarget", None)          # prove today's code
import maya_pmretarget as pm                       # noqa: E402

# (bone, attribute, delta) keyed at 0 and END off the value the bone holds (trap 30)
OWN_TAKE = [("Root", "translateX", 30.0), ("Root", "rotateY", 25.0), ("Hip", "rotateY", 15.0),
            ("Spine2", "rotateZ", 20.0), ("Spine4", "rotateX", -8.0), ("Neck", "rotateX", 10.0),
            ("Head", "rotateZ", -12.0), ("Jaw", "rotateZ", 15.0), ("Right_Eye", "rotateY", 20.0),
            ("Right_Shoulder", "rotateY", 8.0), ("Right_Arm", "rotateZ", -30.0),
            ("Right_ForeArm", "rotateY", 40.0), ("Right_Hand", "rotateX", 25.0),
            ("Right_Finger1", "rotateY", 30.0), ("Right_Thumb2", "rotateY", -20.0),
            ("Left_Thigh", "rotateZ", 35.0), ("Left_Knee", "rotateZ", -45.0), ("Left_Ankle", "rotateX", 10.0),
            ("Right_Toes", "rotateY", 12.0),
            ("Right_Shoulder", "translateY", 1.0)]          # a bone TRANSLATION: to be ignored
UE_TAKE = [("root", "translateZ", 100.0), ("root", "rotateY", 25.0), ("pelvis", "rotateX", 10.0),
           ("spine_03", "rotateZ", 20.0), ("spine_05", "rotateY", -10.0), ("neck_01", "rotateY", 15.0),
           ("head", "rotateZ", -12.0), ("clavicle_l", "rotateY", 8.0), ("upperarm_r", "rotateY", -30.0),
           ("lowerarm_r", "rotateZ", 40.0), ("hand_r", "rotateX", 25.0), ("index_01_l", "rotateZ", 30.0),
           ("thigh_l", "rotateZ", 35.0), ("calf_l", "rotateZ", -45.0), ("foot_l", "rotateZ", 10.0),
           ("clavicle_l", "translateY", 3.0)]                # ignored too

results, skipped, created = [], [], []


def gate(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print("%s %2d  %s%s" % ("ok  " if ok else "FAIL", len(results), name, (" -- " + detail) if detail else ""))


def skip(name, why):
    skipped.append((name, why))
    print("skip     %s -- %s" % (name, why))


def register(nodes):
    for n in nodes:
        for uid in cmds.ls(n, uuid=True) or []:
            if uid not in created:
                created.append(uid)


def M(node):
    return om.MMatrix(cmds.getAttr(node + ".worldMatrix[0]"))


def W(node):
    return om.MVector(cmds.xform(node, q=True, ws=True, t=True))


def ang(a, b):
    qa = om.MTransformationMatrix(om.MMatrix(a)).rotation(asQuaternion=True)
    qb = om.MTransformationMatrix(om.MMatrix(b)).rotation(asQuaternion=True)
    d = qa.inverse() * qb
    return math.degrees(2 * math.acos(max(-1.0, min(1.0, abs(d.w)))))


def settle(t=None):
    if t is not None:
        cmds.currentTime(t)
    cmds.dgdirty(allPlugs=True)


def direction_error(our_pairs, src_pairs):
    """Worst angle between our bone directions and the source's, over pairs of (bone, child) paths."""
    worst = (0.0, "")
    for (a, b), (c, d) in zip(our_pairs, src_pairs):
        u, v = (W(b) - W(a)), (W(d) - W(c))
        if u.length() < 1e-6 or v.length() < 1e-6:
            continue
        e = math.degrees(math.acos(max(-1.0, min(1.0, u.normal() * v.normal()))))
        if e > worst[0]:
            worst = (e, a.split("|")[-1])
    return worst


state = {"autoKey": cmds.autoKeyframe(q=True, st=True), "em": cmds.evaluationManager(q=True, mode=True)[0],
         "time": cmds.currentTime(q=True), "sel": cmds.ls(sl=True, long=True) or [],
         "range": (cmds.playbackOptions(q=True, min=True), cmds.playbackOptions(q=True, max=True),
                   cmds.playbackOptions(q=True, animationStartTime=True), cmds.playbackOptions(q=True, animationEndTime=True)),
         "blends": dict((c, cmds.getAttr(c + ".FKIKBlend")) for c in BLENDS if cmds.objExists(c)),
         "fbx_mode": mel.eval("FBXImportMode -q"), "fbx_fps": mel.eval("FBXImportSetMayaFrameRate -q"),
         "keyed": set(c for c in (cmds.sets("ControlSet", q=True) or [])
                      if cmds.listConnections(c, type="animCurve", s=True, d=False))}
cmds.autoKeyframe(st=False)
cmds.evaluationManager(mode="off")
cmds.playbackOptions(e=True, min=0, max=END, animationStartTime=0, animationEndTime=END)


def build_pose():
    mel.eval("asGoToBuildPose bodySetup;")
    for c, v in state["blends"].items():
        cmds.setAttr(c + ".FKIKBlend", v)
    settle()


def strip_bake():
    """Remove the keys the vendor's Bake left on controls that carried none before."""
    for c in cmds.sets("ControlSet", q=True) or []:
        if c not in state["keyed"] and cmds.listConnections(c, type="animCurve", s=True, d=False):
            cmds.cutKey(c, clear=True)
    build_pose()


def key_take(bones, take):
    for bone, attr, delta in take:
        plug = bones[bone] + "." + attr
        base = cmds.getAttr(plug)
        cmds.setKeyframe(plug, time=0.0, value=base)
        cmds.setKeyframe(plug, time=END, value=base + delta)
    register(cmds.listConnections(list(bones.values()), type="animCurve", s=True, d=False) or [])


def cleanup():
    for uid in list(created):
        for path in cmds.ls(uid, long=True) or []:
            if cmds.objExists(path):
                try:
                    cmds.delete(path)
                except Exception:
                    pass
    for ns in ("pmrtVerify", "pmrtUE", "pmrtMx"):
        if cmds.namespace(exists=ns):
            try:
                cmds.namespace(removeNamespace=ns, mergeNamespaceWithRoot=True)
            except Exception as exc:
                print("namespace %s: %s" % (ns, exc))


try:
    rig = pm.rig_paths()
    game_root = pm.rig_skeleton_root(rig)
    game = dict((pm.leaf(p), p) for p in [game_root] + (cmds.listRelatives(game_root, ad=True, type="joint", fullPath=True) or []))
    gate("the rig and its game skeleton are found", cmds.objExists("Main") and game_root == "|Root" and len(game) == 57,
         "root %s, %d joints" % (game_root, len(game)))
    gate("no retarget is connected yet", not cmds.objExists(pm.HOLDER))
    build_pose()

    # ================================================================ A. the own skeleton
    dup = cmds.ls(cmds.duplicate(game_root, returnRootsOnly=True)[0], long=True)[0]
    register([dup])
    joints = [dup] + (cmds.listRelatives(dup, ad=True, type="joint", fullPath=True) or [])
    register(joints)
    junk = cmds.listRelatives(dup, ad=True, fullPath=True) or []
    junk = [n for n in junk if cmds.nodeType(n) != "joint"]
    if junk:
        cmds.delete(junk)                                # the copied constraints and their like
    if not cmds.namespace(exists="pmrtVerify"):
        cmds.namespace(add="pmrtVerify")
    plan = [(cmds.ls(j, uuid=True)[0], "Root" if j == dup else pm.leaf(j)) for j in joints]
    for uid, name in plan:                                # rename by uuid: paths go stale (trap 48)
        path = cmds.ls(uid, long=True)
        if path:
            cmds.rename(path[0], "pmrtVerify:" + name)
    own_root = cmds.ls("pmrtVerify:Root", long=True)[0]
    own = pm.source_bones(own_root)
    cmds.xform(own_root, ws=True, t=(0, 0, 0))            # a copy stands where the original stands
    key_take(own, OWN_TAKE)
    text = pm.report(own_root)
    gate("A: the copy is recognised as the skeleton itself, scale 1", "schema own" in text and "scaled by 1.0000" in text, text.split("\n")[1][:120])
    plan_a = pm._plan(own_root)                       # BEFORE connect: afterwards every control carries our constraint
    msg = pm.connect(own_root)
    ok = msg.startswith("retarget connected")
    gate("A: connect builds the retarget", ok, msg.split("\n")[0])
    busy = dict(plan_a.busy)
    if busy:
        skip("A: bones under the animator's own constraints are not measured", str(busy))
    driven = dict((d.control, d) for d in plan_a.drives)
    fk_bones = [pm.our_bone(c) for c, d in driven.items() if d.kind == "fk"]

    def all_fk(on):
        for c in BLENDS:
            cmds.setAttr(c + ".FKIKBlend", 0 if on else state["blends"][c])
        settle()

    def worst_orientation(src):
        worst = (0.0, "")
        for t in SAMPLES:
            settle(t)
            for bone in fk_bones:
                e = ang(M(game[bone]), M(src[bone]))
                if e > worst[0]:
                    worst = (e, "%s@%g" % (bone, t))
        return worst
    all_fk(True)
    worst = worst_orientation(own)
    gate("A: in FK every driven bone carries the source bone's orientation at every sample (%d bones)" % len(fk_bones),
         worst[0] < 0.02 and len(fk_bones) >= 40, "worst %.5f deg at %s" % worst)
    all_fk(False)
    worst = worst_orientation(own)
    # the IK legs land their knees on the FK knees (8e-5) and point the same way (0.001 deg); what
    # is left is ROLL: this skeleton's knee hinge stands 0.36 deg off its own rest bend plane, and
    # an IK solver bends about the plane's normal where FK bends about the hinge
    gate("A: in IK (legs, the rig's default) the bones match to the skeleton's own hinge-vs-plane skew, the poles in the FK planes",
         worst[0] < 0.5, "worst %.5f deg at %s" % worst)
    settle(END)
    travel = (W(game_root) - W(own_root)).length()
    yaw = ang(M(game_root), M(own_root))
    pelvis = (W(game["Hip"]) - W(own["Hip"])).length()
    gate("A: the root travel and yaw and the pelvis position are reproduced 1:1 (scale 1)",
         travel < 1e-3 and yaw < 0.01 and pelvis < 1e-3, "root off by %.6f, yaw %.5f deg, pelvis off by %.6f" % (travel, yaw, pelvis))
    ours = (W(game["Right_Arm"]) - W(game["Right_Shoulder"]))
    theirs = (W(own["Right_Arm"]) - W(own["Right_Shoulder"]))
    slid = (W(own["Right_Arm"]) - W(game["Right_Arm"])).length()
    gate("A: the source's bone TRANSLATION is ignored: the clavicle keeps our length while the copy's slid 1.0",
         abs(ours.length() - 0.954) < 1e-3 and slid > 0.5 and ang(M(game["Right_Arm"]), M(own["Right_Arm"])) < 0.02,
         "our clavicle %.4f long, the copy's arm root %.4f away from ours, orientation off %.5f deg"
         % (ours.length(), slid, ang(M(game["Right_Arm"]), M(own["Right_Arm"]))))
    settle(13.0)
    fk_hand = W(game["Right_Hand"])
    fk_hand_m = M(game["Right_Hand"])
    cmds.setAttr("FKIKArm_R.FKIKBlend", 10)
    settle(13.0)
    ik_hand = W(game["Right_Hand"])
    ik_err = (ik_hand - fk_hand).length()
    ik_ang = ang(fk_hand_m, M(game["Right_Hand"]))
    cmds.setAttr("FKIKArm_R.FKIKBlend", state["blends"]["FKIKArm_R"])
    gate("A: the IK arm follows our own FK: switching the arm to IK leaves the hand where FK put it",
         ik_err < 1e-3 and ik_ang < 0.05, "hand moved %.6f, turned %.5f deg" % (ik_err, ik_ang))
    settle(13.0)
    leg = [b for b in ("Left_Thigh", "Left_Knee", "Left_Ankle") if b in fk_bones]
    leg_ik = [ang(M(game[b]), M(own[b])) for b in leg] or [999.0]
    cmds.setAttr("FKIKLeg_L.FKIKBlend", 0)
    settle(13.0)
    leg_fk = [ang(M(game[b]), M(own[b])) for b in leg] or [999.0]
    cmds.setAttr("FKIKLeg_L.FKIKBlend", state["blends"]["FKIKLeg_L"])
    gate("A: the leg matches the source in FK exactly and in IK to the hinge skew (the pole in the FK plane)",
         max(leg_fk) < 0.02 and max(leg_ik) < 0.5, "FK worst %.5f deg, IK worst %.4f deg over %s" % (max(leg_fk), max(leg_ik), leg))
    n_cons = len(set(cmds.listConnections(pm.HOLDER + "." + pm.SWITCH, s=False, d=True) or []))
    gate("A: every constraint is registered on MoCapConstraints.disableConstraints and every helper sits under it",
         n_cons >= len(driven) and all(n.startswith("|" + pm.HOLDER) for n in cmds.ls("pmrt*", type="transform", long=True)),
         "%d constraints, %d helper transforms" % (n_cons, len(cmds.ls("pmrt*", type="transform"))))
    # the vendor's own Bake and Disconnect
    settle(0.0)
    mel.eval("asMoCapMatcherBake;")
    mel.eval("asMoCapMatcherDisconnect;")
    gone = not cmds.objExists(pm.HOLDER) and not cmds.ls("pmrt*", type="transform")
    keyed = [c for c in driven if cmds.listConnections(c, type="animCurve", s=True, d=False)]
    settle(13.0)
    after_ik = [ang(M(game[b]), M(own[b])) for b in fk_bones]
    all_fk(True)
    settle(13.0)
    after_fk = [ang(M(game[b]), M(own[b])) for b in fk_bones]
    all_fk(False)
    gate("A: AdvancedSkeleton's Bake keys the driven controls and its Disconnect removes every node of ours",
         gone and len(keyed) >= 10, "holder gone %s, %d driven controls keyed" % (gone, len(keyed)))
    gate("A: with the source unplugged the rig still plays the take, in FK exactly and in IK to the hinge skew",
         max(after_fk) < 0.02 and max(after_ik) < 0.5, "worst %.5f deg (FK) / %.5f deg (IK) at frame 13" % (max(after_fk), max(after_ik)))
    strip_bake()
    cmds.delete(own_root)
    build_pose()

    # ================================================================ B. UE5 from the template
    tpl = json.load(open(os.path.join(pm.ASSETS, pm.UE5.template)))
    if not cmds.namespace(exists="pmrtUE"):
        cmds.namespace(add="pmrtUE")
    made = {}
    for j in tpl["joints"]:
        parent = made.get(j["parent"])
        node = cmds.createNode("joint", name="pmrtUE:" + j["name"], parent=parent, skipSelect=True)
        cmds.xform(node, ws=True, matrix=j["world_matrix"])
        made[j["name"]] = cmds.ls(node, long=True)[0]
    register(list(made.values()))
    ue_root = cmds.ls("pmrtUE:root", long=True)[0]
    ue = pm.source_bones(ue_root)
    rest_err = max((W(ue[n]) - om.MVector(*pm.position(tpl_j["world_matrix"]))).length() for n, tpl_j in ((j["name"], j) for j in tpl["joints"]))
    gate("B: a Manny stands in the scene at the template's bind pose", len(ue) == 93 and rest_err < 1e-3, "%d joints, worst %.6f off the template" % (len(ue), rest_err))
    key_take(ue, UE_TAKE)
    text = pm.report(ue_root)
    s_expected = (W(game["Hip"]).y - W(game_root).y) / (W(ue["pelvis"]).y - W(ue["root"]).y)
    gate("B: recognised as UE5 with the Manny template and the size ratio",
         "schema ue5" in text and "manny_skeleton_template" in text and ("scaled by %.4f" % s_expected) in text,
         text.split("\n")[1][:140])
    plan_b = pm._plan(ue_root)
    msg = pm.connect(ue_root)
    gate("B: connect builds the retarget", msg.startswith("retarget connected"), msg.split("\n")[0])
    driven = dict((d.control, d) for d in plan_b.drives)
    pairs_ours, pairs_theirs = [], []
    for c, d in driven.items():
        if d.kind != "fk":
            continue
        ours = pm.our_bone(c)
        kid_ours = [pm.our_bone(k) for k, e in driven.items() if e.kind == "fk" and pm.parents_of(game).get(pm.our_bone(k)) == ours]
        kid_theirs = [e.source for k, e in driven.items() if e.kind == "fk" and pm.parents_of(ue).get(e.source) == d.source]
        if kid_ours and kid_theirs and pm.our_bone(c) not in ("Right_Hand", "Left_Hand", "Spine4", "Spine3"):
            pairs_ours.append((game[ours], game[kid_ours[0]]))
            pairs_theirs.append((ue[d.source], ue[kid_theirs[0]]))
    def worst_direction(samples):
        worst = (0.0, "")
        for t in samples:
            settle(t)
            e = direction_error(pairs_ours, pairs_theirs)
            if e[0] > worst[0]:
                worst = (e[0], "%s@%g" % (e[1], t))
        return worst
    settle(0.0)
    rest_root, rest_root_m, rest_hip = W(game_root), M(game_root), W(game["Hip"])
    src_rest_root_m, src_rest_pelvis = M(ue_root), W(ue["pelvis"])
    all_fk(True)
    worst = worst_direction(SAMPLES)
    gate("B: in FK every mapped bone with a mapped child POINTS where the Manny's bone points, at every sample (%d bones)" % len(pairs_ours),
         worst[0] < 0.15, "worst %.4f deg at %s" % worst)
    all_fk(False)
    worst = worst_direction(SAMPLES)
    gate("B: in IK the legs point the same way, the poles standing in the FK planes", worst[0] < 0.2, "worst %.4f deg at %s" % worst)
    settle(END)
    root_pos = W(game_root)
    our_yaw = ang(rest_root_m, M(game_root))
    src_yaw = ang(src_rest_root_m, M(ue_root))
    gate("B: Main carries the Manny's 100 cm root travel scaled to our size (%.4f), and turns by the root's 25 deg" % s_expected,
         abs(root_pos.z - 100.0 * s_expected) < 1e-3 and abs(root_pos.x) < 1e-3 and abs(our_yaw - src_yaw) < 0.02 and abs(src_yaw - 25.0) < 0.01,
         "our Root at z %.4f (expected %.4f), turned %.4f deg against the source's %.4f" % (root_pos.z, 100.0 * s_expected, our_yaw, src_yaw))
    hip_delta = W(game["Hip"]) - rest_hip
    src_delta = (W(ue["pelvis"]) - src_rest_pelvis) * s_expected
    gate("B: the pelvis moves as the Manny's pelvis moves, scaled", (hip_delta - src_delta).length() < 1e-3,
         "pelvis moved %.4f vs scaled source %.4f, difference %.6f" % (hip_delta.length(), src_delta.length(), (hip_delta - src_delta).length()))
    clav = (W(game["Left_Arm"]) - W(game["Left_Shoulder"])).length()
    gate("B: the Manny's clavicle translation is ignored, our clavicle keeps its length", abs(clav - 0.954) < 1e-3, "%.4f" % clav)
    gate("B: the size difference is reported, not scaled away", any("of the source's" in n for n in plan_b.notes), "; ".join(plan_b.notes)[:160])
    pm.disconnect()
    cmds.delete(ue_root)
    build_pose()
    gate("B: disconnect leaves nothing of ours", not cmds.objExists(pm.HOLDER) and not cmds.ls("pmrt*"))

    # ================================================================ C. the animator's Mixamo clip
    if not os.path.exists(MIXAMO_FBX):
        skip("C: Mixamo", "%s not found" % MIXAMO_FBX)
    else:
        before = set(cmds.ls(cmds.ls(), uuid=True) or [])
        cur_ns = cmds.namespaceInfo(currentNamespace=True)
        if not cmds.namespace(exists="pmrtMx"):
            cmds.namespace(add="pmrtMx")
        cmds.namespace(set="pmrtMx")
        try:
            mel.eval("FBXImportMode -v add")
            mel.eval("FBXImportSetMayaFrameRate -v false")
            mel.eval('FBXImport -f "%s"' % MIXAMO_FBX)
        finally:
            cmds.namespace(set=cur_ns)
            mel.eval("FBXImportMode -v %s" % state["fbx_mode"])
            mel.eval("FBXImportSetMayaFrameRate -v %s" % ("true" if state["fbx_fps"] else "false"))
        new_uids = set(cmds.ls(cmds.ls(), uuid=True) or []) - before
        created.extend(new_uids)
        cmds.playbackOptions(e=True, min=0, max=END, animationStartTime=0, animationEndTime=END)
        # the clip's joints arrive as pmrtMx:mixamorig:Hips -- a NESTED namespace, which `ls("pmrtMx:*")` does not reach
        new_joints = [p for uid in new_uids for p in (cmds.ls(uid, long=True) or []) if cmds.nodeType(p) == "joint"]
        roots = [j for j in new_joints if not cmds.listRelatives(j, parent=True, type="joint")]
        gate("C: the clip imports as one Mixamo skeleton", len(roots) == 1 and roots[0].endswith("Hips"), str(roots))
        mx_root = roots[0]
        mx = pm.source_bones(mx_root)
        text = pm.report(mx_root)
        gate("C: recognised as Mixamo, rest from jointOrient, aligned", "schema mixamo" in text and "aligned bone by bone" in text, text.split("\n")[1][:140])
        plan_c = pm._plan(mx_root)
        msg = pm.connect(mx_root)
        gate("C: connect builds the retarget", msg.startswith("retarget connected"), msg.split("\n")[0])
        driven = dict((d.control, d) for d in plan_c.drives)
        s_mx = plan_c.scale
        pairs_ours, pairs_theirs = [], []
        for c, d in driven.items():
            if d.kind != "fk":
                continue
            ours = pm.our_bone(c)
            kid_ours = [pm.our_bone(k) for k, e in driven.items() if e.kind == "fk" and pm.parents_of(game).get(pm.our_bone(k)) == ours]
            kid_theirs = [e.source for k, e in driven.items() if e.kind == "fk" and pm.parents_of(mx).get(e.source) == d.source]
            if kid_ours and kid_theirs and ours not in ("Right_Hand", "Left_Hand", "Spine4", "Spine2", "Head"):
                pairs_ours.append((game[ours], game[kid_ours[0]]))
                pairs_theirs.append((mx[d.source], mx[kid_theirs[0]]))
        all_fk(True)
        worst = worst_direction((2.0, 10.0, 18.0))
        all_fk(False)
        gate("C: in FK every mapped bone with a mapped child points where the Mixamo bone points (%d bones)" % len(pairs_ours),
             worst[0] < 0.5, "worst %.4f deg at %s" % worst)
        settle(10.0)
        hips = W(mx["Hips"])
        hips_rest = om.MVector(*pm.position(plan_c.src_rest["Hips"]))     # the T-pose hips: where Main reads zero
        root_pos = W(game_root)
        gate("C: Main takes the hips' horizontal travel from their rest, scaled by %.4f, and stays on the ground" % s_mx,
             abs(root_pos.x - (hips.x - hips_rest.x) * s_mx) < 1e-3 and abs(root_pos.z - (hips.z - hips_rest.z) * s_mx) < 1e-3
             and abs(root_pos.y) < 1e-6,
             "Root at (%.4f, %.4f, %.4f), hips at (%.3f, %.3f, %.3f), rest hips (%.3f, %.3f, %.3f)"
             % (root_pos.x, root_pos.y, root_pos.z, hips.x, hips.y, hips.z, hips_rest.x, hips_rest.y, hips_rest.z))
        hip_expected = om.MVector(0, 11.2074, 0) + (hips - hips_rest) * s_mx
        gate("C: the pelvis moves as the hips move, scaled (our rest hip plus the scaled travel)",
             (W(game["Hip"]) - hip_expected).length() < 1e-3,
             "Hip at (%.4f, %.4f, %.4f), expected (%.4f, %.4f, %.4f)" % (W(game["Hip"]).x, W(game["Hip"]).y, W(game["Hip"]).z, hip_expected.x, hip_expected.y, hip_expected.z))
        pm.disconnect()
        build_pose()
        gate("C: disconnect leaves nothing of ours", not cmds.objExists(pm.HOLDER) and not cmds.ls("pmrt*"))

    cleanup()
    build_pose()
    left = [uid for uid in created if cmds.ls(uid)]
    gate("nothing the run created is left in the scene, no namespace either",
         not left and not any(cmds.namespace(exists=ns) for ns in ("pmrtVerify", "pmrtUE", "pmrtMx")), "%d nodes left" % len(left))
    keyed_now = set(c for c in (cmds.sets("ControlSet", q=True) or []) if cmds.listConnections(c, type="animCurve", s=True, d=False))
    gate("the controls carry exactly the keys they carried before", keyed_now == state["keyed"], "%d before, %d after" % (len(state["keyed"]), len(keyed_now)))
except Exception:
    traceback.print_exc()
    gate("the script ran to the end", False, "see the traceback")
finally:
    for step in (lambda: pm.disconnect() if cmds.objExists(pm.HOLDER) else None,
                 cleanup, strip_bake,
                 lambda: cmds.playbackOptions(e=True, min=state["range"][0], max=state["range"][1],
                                              animationStartTime=state["range"][2], animationEndTime=state["range"][3]),
                 lambda: cmds.evaluationManager(mode=state["em"]),
                 lambda: cmds.autoKeyframe(st=state["autoKey"]),
                 lambda: cmds.currentTime(state["time"]),
                 lambda: cmds.select([s for s in state["sel"] if cmds.objExists(s)]) if state["sel"] else cmds.select(clear=True)):
        try:
            step()
        except Exception as exc:
            print("restore step failed:", exc)
    failed = [r for r in results if not r[1]]
    print("restored: range %s, EM %s, autoKey %s, time %s, blends %s" % (
        (cmds.playbackOptions(q=True, min=True), cmds.playbackOptions(q=True, max=True)), cmds.evaluationManager(q=True, mode=True)[0],
        cmds.autoKeyframe(q=True, st=True), cmds.currentTime(q=True), dict((c, cmds.getAttr(c + ".FKIKBlend")) for c in BLENDS)))
    if skipped:
        print("%d check(s) skipped: %s" % (len(skipped), [s[0] for s in skipped]))
    if failed:
        print("%d of %d gates failed: %s" % (len(failed), len(results), [r[0] for r in failed]))
    else:
        print("all %d gates passed" % len(results))
