"""Creep 2 Arm R / Head on Manny's whole skeleton, and the Pose Library on them - mayapy standalone.

    mayapy verify_creep_parts_manny.py <clip .fbx> <old asset folder>

`<old asset folder>` holds the four part assets as they were before 2026-10-27's change
(`git show <commit>:SkeldarAnim/assets/<file>`), to compare the controls against. Gates:

  A  each part rig: the same controls as before (every transform with a curve shape, by name);
     93 game joints with Manny's parents; spine_05 parent-constrained to Root_M; every bone the
     rig does not drive carries no constraint
  B  the clip through the Retarget button onto each part rig: the bones the rig does not drive keep
     their local matrices on every sampled frame; spine_05 stays on Root_M's offset
  C  the Pose Library, on the arm rig, the head rig, the arm skeleton and the Body rig:
     - a card saved with nothing selected holds only the driven bones (a part rig) or the body;
     - saved posed, the rig reset, the card applied back: every member on the card's (0.01 cm / deg);
     - a part rig's card onto a Manny rig: Manny's pelvis, spine_01..04 and legs untouched;
     - a Manny card onto the part rig: applied, the bind bones untouched;
     - an animation card from the retargeted arm rig onto a fresh arm rig: every member on the
       source's on every sampled frame.

Spec: docs/superpowers/specs/2026-10-27-creep-parts-manny-skeleton-design.md
"""
import math
import os
import sys

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

PLUGIN = "C:/!!!Work/MayaScripts/SkeldarAnim"
sys.path.insert(0, PLUGIN)
for p in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:                                                   # noqa: BLE001
        pass
cmds.undoInfo(state=True, infinity=True)
cmds.autoKeyframe(state=False)

from maya_scenesetup import catalog, character  # noqa: E402
import maya_rigs  # noqa: E402
import maya_rig_retarget as rr  # noqa: E402
from maya_uebridge import skeletonimport  # noqa: E402
from maya_poselib import animapply, animcapture, apply, capture, scene  # noqa: E402

CLIP, OLD = sys.argv[1].replace("\\", "/"), sys.argv[2]
FAILS = []
TOL = 0.01


def gate(name, ok, msg=""):
    print("%s %s %s" % ("PASS" if ok else "FAIL", name, msg))
    if not ok:
        FAILS.append(name)


def leaf(p):
    return p.split("|")[-1].split(":")[-1]


def wm(n):
    return om.MMatrix(cmds.getAttr(n + ".worldMatrix[0]"))


def lm(n):
    return om.MMatrix(cmds.getAttr(n + ".matrix"))


def evaluate(t):
    cmds.currentTime(t + 1)
    cmds.currentTime(t)


def far(a, b):
    """(cm, deg) between two matrices."""
    pa = om.MVector(a.getElement(3, 0), a.getElement(3, 1), a.getElement(3, 2))
    pb = om.MVector(b.getElement(3, 0), b.getElement(3, 1), b.getElement(3, 2))
    q = om.MTransformationMatrix(a).rotation(asQuaternion=True).inverse() * \
        om.MTransformationMatrix(b).rotation(asQuaternion=True)
    return (pa - pb).length(), math.degrees(2 * math.acos(min(1.0, abs(q.w))))


def bones_of(root):
    return dict((leaf(p), p) for p in
                [root] + (cmds.listRelatives(root, ad=True, type="joint", fullPath=True) or []))


def driven(root):
    return set(leaf(j) for j in bones_of(root).values()
               if cmds.listRelatives(j, children=True, type="constraint"))


def controls(namespace):
    out = set()
    for shape in cmds.ls(namespace + ":*", type="nurbsCurve", long=True) or []:
        out.add(leaf(cmds.listRelatives(shape, parent=True, fullPath=True)[0]))
    return out


def add(key):
    before = set(r.namespace for r in maya_rigs.rigs())
    bare = set(skeletonimport.bare_roots())
    character.add_character(catalog.character_by_key(key))
    cmds.select(clear=True)
    new = [r for r in maya_rigs.rigs() if r.namespace not in before]
    if new:
        return new[0].skeleton_root, new[0]
    return [r for r in skeletonimport.bare_roots() if r not in bare][0], None


def import_fbx(path, ns):
    before = set(cmds.ls(long=True, dag=True))
    cmds.namespace(add=ns)
    cmds.namespace(set=":" + ns)
    mel.eval("FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;")
    mel.eval('FBXImport -f "%s";' % path)
    cmds.namespace(set=":")
    return [n for n in cmds.ls(long=True, dag=True) if n not in before]


MANNY = None


def manny_parents():
    global MANNY
    if MANNY is None:
        import re
        with open(os.path.join(PLUGIN, "assets", "Manny_Skeleton.ma"), encoding="utf-8",
                  errors="replace") as fh:
            MANNY = dict(re.findall(r'createNode joint -n "([^"]+)" -p "([^"]+)"', fh.read()))
    return MANNY


def reset(rig):
    for ctrl in cmds.sets(rig.control_set, q=True) or []:
        for attr in ("tx", "ty", "tz", "rx", "ry", "rz"):
            plug = "%s.%s" % (ctrl, attr)
            if cmds.objExists(plug) and cmds.getAttr(plug, settable=True):
                cmds.setAttr(plug, 0.0)


def pose_arm(rig):
    for ctrl, attr, v in (("FKShoulder_R", "rz", 25.0), ("FKElbow_R", "rz", -35.0),
                          ("FKWrist_R", "rx", 20.0), ("FKNeck_M", "rx", 15.0), ("FKHead_M", "ry", 20.0),
                          ("RootX_M", "ry", 10.0)):
        plug = "%s:%s.%s" % (rig.namespace, ctrl, attr)
        if cmds.objExists(plug):
            cmds.setAttr(plug, v)


def round_trip(label, root, rig):
    """Save posed, reset, apply back: every member on the card's."""
    data, note = capture.build_pose([root], frame=0)
    members = list(data.get("members") or ())
    if rig is not None and rig.group and cmds.attributeQuery("skeldarPartAnchor", node=rig.group,
                                                             exists=True):
        gate("C %s: nothing selected holds only the driven bones" % label,
             set(members) <= driven(root) and "pelvis" not in members and members,
             "%d members: %s" % (len(members), members[:6]))
    B = bones_of(root)
    saved = dict((m, wm(B[m])) for m in members)
    if rig is not None:
        reset(rig)
    evaluate(0)
    ok, text = apply.apply_onto(data, root)
    evaluate(0)
    worst = max(max(far(wm(B[m]), saved[m])) for m in members)
    gate("C %s: the card applied back lands every member" % label, ok and worst < TOL,
         "%.4f  %s" % (worst, (text or "").splitlines()[0][:140]))
    return data


# ------------------------------------------------------------------ A: structure
cmds.file(new=True, force=True)
for key, old_file in (("Creep2_ArmR_Rig", "Creep2_ArmR_Rig.ma"), ("Creep2_Head_Rig", "Creep2_Head_Rig.ma")):
    root, rig = add(key)
    cmds.file(os.path.join(OLD, old_file).replace("\\", "/"), i=True, namespace="old_" + key,
              executeScriptNodes=False)
    new_c, old_c = controls(rig.namespace), controls("old_" + key)
    gate("A %s: the same controls" % key, new_c == old_c and new_c,
         "%d against %d; added %s, gone %s" % (len(new_c), len(old_c), sorted(new_c - old_c)[:5],
                                              sorted(old_c - new_c)[:5]))
    B = bones_of(root)
    bad = [n for n, p in manny_parents().items() if n not in B or
           leaf(cmds.listRelatives(B[n], parent=True)[0]) != p]
    gate("A %s: 93 joints, Manny's parents" % key, len(B) == 93 and not bad, "%d joints %s" % (len(B), bad[:5]))
    pc = cmds.listRelatives(B["spine_05"], children=True, type="parentConstraint") or []
    targets = [leaf(t) for t in cmds.parentConstraint(pc[0], q=True, targetList=True)] if pc else []
    gate("A %s: spine_05 follows Root_M" % key, targets == ["Root_M"], str(targets))
    part = {"Creep2_ArmR_Rig": "clavicle_r", "Creep2_Head_Rig": "neck_01"}[key]
    expected = set(leaf(j) for j in bones_of(B[part]).values()) | {"root", "spine_05"}
    gate("A %s: only the part, spine_05 and root are driven" % key, driven(root) <= expected,
         "extra %s" % sorted(driven(root) - expected)[:6])

# ------------------------------------------------------------------ B: retarget
cmds.file(new=True, force=True)
arm_root, arm = add("Creep2_ArmR_Rig")
head_root, head = add("Creep2_Head_Rig")
nodes = import_fbx(CLIP, "clip")
src_root = min((j for j in nodes if cmds.nodeType(j) == "joint"
                and not cmds.listRelatives(j, parent=True, type="joint")), key=lambda j: j.count("|"))
S = bones_of(src_root)
first = cmds.findKeyframe(list(S.values()), which="first")
last = cmds.findKeyframe(list(S.values()), which="last")
cmds.playbackOptions(min=first, max=last, animationStartTime=first, animationEndTime=last)
frames = [round(first + (last - first) * k / 5.0) for k in range(6)]
for rig in (arm, head):
    B = bones_of(rig.skeleton_root)
    # a helper on a driven bone (the arm's weapon_r in hand_r) is carried from the clip, as on any rig
    carried = set(rr.HELPER_BONES) - set(rr.part_held(B))
    still = [n for n in B if n not in driven(rig.skeleton_root) and n not in carried]
    rest = dict((n, lm(B[n])) for n in still)
    cmds.currentTime(first)
    cmds.select(rig.main, src_root)
    ok, text = rr.run_retarget()
    print("   ", (text or "").splitlines()[0][:200])
    worst, anchor, moved = 0.0, 0.0, set()
    root_m = "%s:Root_M" % rig.namespace
    evaluate(first)
    off = wm(B["spine_05"]) * wm(root_m).inverse()
    for t in frames:
        evaluate(t)
        worst = max([worst] + [max(far(lm(B[n]), rest[n])) for n in still])
        moved.update(n for n in still if max(far(lm(B[n]), rest[n])) > 1e-4)
        anchor = max(anchor, max(far(wm(B["spine_05"]) * wm(root_m).inverse(), off)))
    gate("B %s: retargeted" % rig.namespace, ok, (text or "")[:120])
    gate("B %s: the %d bones without controls keep their locals" % (rig.namespace, len(still)),
         worst < 1e-4, "%.2e %s" % (worst, sorted(moved)))
    gate("B %s: spine_05 on Root_M" % rig.namespace, anchor < 1e-3, "%.2e" % anchor)

# the arm rig's animation card, onto a fresh arm rig
header, frames_data, note = animcapture.build_animation([arm.skeleton_root], start=frames[0], end=frames[2])
fresh_root, fresh = add("Creep2_ArmR_Rig")
cmds.currentTime(frames[0])
ok, text = animapply.apply_onto(header, frames_data, fresh_root)
members = list(header.get("members") or ())
SA, SF = bones_of(arm.skeleton_root), bones_of(fresh_root)
worst = 0.0
for t in range(int(frames[0]), int(frames[2]) + 1, max(1, int((frames[2] - frames[0]) / 6))):
    evaluate(t)
    worst = max([worst] + [max(far(wm(SF[m]) * wm(SF["root"]).inverse(),
                                   wm(SA[m]) * wm(SA["root"]).inverse())) for m in members])
gate("C arm animation card onto a fresh arm rig", ok and members and "pelvis" not in members and worst < TOL,
     "%d members, %.4f  %s" % (len(members), worst, (text or "").splitlines()[0][:120]))

# ------------------------------------------------------------------ C: poses
cmds.file(new=True, force=True)
cmds.playbackOptions(min=0, max=10)
for key in ("Creep2_ArmR_Rig", "Creep2_Head_Rig", "Creep2_Body_Rig"):
    root, rig = add(key)
    pose_arm(rig)
    evaluate(0)
    data = round_trip(key, root, rig)
    if key == "Creep2_ArmR_Rig":
        manny_root, manny = add("Manny_Rig")
        M = bones_of(manny_root)
        body = ["pelvis", "spine_01", "spine_02", "spine_03", "spine_04", "thigh_l", "calf_r", "foot_l"]
        before = dict((n, wm(M[n])) for n in body)
        ok, text = apply.apply_onto(data, manny_root)
        evaluate(0)
        worst = max(max(far(wm(M[n]), before[n])) for n in body)
        gate("C the arm card onto Manny_Rig leaves Manny's body", ok and worst < 1e-4,
             "%.2e  %s" % (worst, (text or "").splitlines()[0][:120]))
        pose_arm(manny)
        evaluate(0)
        mdata, _ = capture.build_pose([manny_root], frame=0)
        reset(rig)
        evaluate(0)
        B = bones_of(root)
        still = [n for n in B if n not in driven(root)]
        before = dict((n, lm(B[n])) for n in still)
        hand0 = wm(B["hand_r"])
        ok, text = apply.apply_onto(mdata, root)
        evaluate(0)
        worst = max(max(far(lm(B[n]), before[n])) for n in still)
        gate("C a Manny card onto the arm rig: applied, the bind bones untouched",
             ok and worst < 1e-4 and max(far(wm(B["hand_r"]), hand0)) > 1.0,
             "%.2e, the hand moved %.2f  %s" % (worst, max(far(wm(B["hand_r"]), hand0)),
                                                (text or "").splitlines()[0][:120]))
# the arm skeleton: a card off it, applied back
root, _ = add("Creep2_ArmR")
B = bones_of(root)
for name, attr, v in (("clavicle_r", "rz", 10.0), ("upperarm_r", "rz", 30.0), ("hand_r", "rx", 25.0)):
    cmds.setAttr("%s.%s" % (B[name], attr), cmds.getAttr("%s.%s" % (B[name], attr)) + v)
evaluate(0)
data, _ = capture.build_pose([B["hand_r"], B["upperarm_r"], B["clavicle_r"]], frame=0)
saved = dict((m, wm(B[m])) for m in data["members"])
for name, attr, v in (("clavicle_r", "rz", 10.0), ("upperarm_r", "rz", 30.0), ("hand_r", "rx", 25.0)):
    cmds.setAttr("%s.%s" % (B[name], attr), cmds.getAttr("%s.%s" % (B[name], attr)) - v)
ok, text = apply.apply_onto(data, root)
evaluate(0)
worst = max(max(far(wm(B[m]), saved[m])) for m in data["members"])
gate("C Creep2_ArmR skeleton: a card applied back", ok and worst < TOL, "%.4f" % worst)

print("%d failed: %s" % (len(FAILS), FAILS))
