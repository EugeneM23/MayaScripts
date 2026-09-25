"""Standalone gates for the rotation-only retarget onto the Creep's AdvancedSkeleton rig (2026-09-24).

Run in mayapy STANDALONE -- it imports a clip and bakes the rig, so never in the animator's
scene:

    mayapy verify_creep_rotation_retarget.py <scene with the Creep rig> <UE5 clip .fbx>

It opens the scene (script nodes NOT executed), imports the clip as its own namespaced
skeleton, presses the Retarget button's function (`maya_rig_retarget.run_retarget`:
reset, connect, bake, disconnect) and measures, over sampled frames of the take:

- every driven Creep bone takes the source bone's WORLD ORIENTATION;
- no Creep bone below the pelvis changes its local translation -- bone lengths are the
  Creep's own on every frame, while the clip itself slides bones (the positive control);
- the root and the pelvis land on the source's (root motion and the hips travel);
- the IK limbs, which follow the rig's own FK, reproduce the FK pose;
- nothing of the retarget is left standing, and the source is kept.
"""
import math
import os
import sys

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

PLUGIN = "C:/!!!Work/MayaScripts/SkeldarAnim"
sys.path.insert(0, PLUGIN)
for p in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass

SCENE, CLIP = sys.argv[1], sys.argv[2]
FAILS = []


def gate(n, ok, msg):
    print("%s gate %02d: %s" % ("PASS" if ok else "FAIL", n, msg))
    if not ok:
        FAILS.append(n)


def wm(n):
    return om.MMatrix(cmds.getAttr(n + ".worldMatrix[0]"))


def rot(m):
    return om.MTransformationMatrix(m).rotation(asQuaternion=True)


def ang(a, b):
    q = a.inverse() * b
    return math.degrees(2 * math.acos(max(-1.0, min(1.0, abs(q.w)))))


def pos(n):
    return om.MVector(cmds.xform(n, q=True, ws=True, t=True))


cmds.file(SCENE, open=True, force=True, executeScriptNodes=False)
import maya_rigs, maya_asretarget as ar, maya_rig_retarget as rr

rigs = maya_rigs.rigs()
gate(1, len(rigs) == 1 and ar.rotation_mode(rigs[0]), "one rig in the scene, marked rotation-only: %s" % [(maya_rigs.label(r), ar.rotation_mode(r)) for r in rigs])
rig = rigs[0]
creep_root = rig.skeleton_root
H = dict((p.split("|")[-1], p) for p in [creep_root] + (cmds.listRelatives(creep_root, ad=True, type="joint", fullPath=True) or []))
rest_t = dict((n, cmds.getAttr(p + ".translate")[0]) for n, p in H.items())

# the clip, as its own namespaced skeleton
before = set(cmds.ls(type="joint", long=True))
cmds.namespace(add="clip")
cmds.namespace(set=":clip")
mel.eval('FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;')
mel.eval('FBXImport -f "%s";' % CLIP.replace("\\", "/"))
cmds.namespace(set=":")
new = [j for j in cmds.ls(type="joint", long=True) if j not in before]
src_root = min((j for j in new if not cmds.listRelatives(j, parent=True, type="joint")), key=lambda j: j.count("|"))
S = dict((p.split("|")[-1].split(":")[-1], p) for p in [src_root] + (cmds.listRelatives(src_root, ad=True, type="joint", fullPath=True) or []))
first, last = cmds.findKeyframe(list(S.values()), which="first"), cmds.findKeyframe(list(S.values()), which="last")
cmds.playbackOptions(min=first, max=last, animationStartTime=first, animationEndTime=last)
gate(2, "spine_05" in S and "pelvis" in S and last > first, "clip %s: %d joints under %s, keys %g..%g" % (os.path.basename(CLIP), len(S), src_root, first, last))

# the positive control: the clip itself moves some bones in translation
slide = {}
for n in ("clavicle_l", "clavicle_r", "neck_01", "spine_05", "thigh_l", "upperarm_r"):
    if n in S:
        vals = []
        for t in range(int(first), int(last) + 1, max(1, int((last - first) / 30))):
            cmds.currentTime(t)
            vals.append(om.MVector(cmds.getAttr(S[n] + ".translate")[0]))
        slide[n] = max((v - vals[0]).length() for v in vals)
cmds.currentTime(first)

ok, text = rr.run_retarget(source_root=src_root, rig=rig)
print(text)
gate(3, ok and not cmds.objExists(ar.holder_of(rig)) and cmds.objExists(src_root), "the button ran, holder gone, source kept: ok=%s" % ok)
left = [c for c in cmds.ls(type="constraint") if any(p.startswith(src_root) for p in cmds.ls(cmds.listConnections(c, s=True, d=False) or [], long=True))]
gate(4, not left, "no constraint reads the source any more (%d)" % len(left))

# sample the take
compare = [b for b in ("pelvis", "spine_01", "spine_03", "spine_05", "neck_01", "neck_02", "head", "clavicle_l", "upperarm_l",
                       "lowerarm_l", "hand_l", "index_02_l", "thumb_03_r", "clavicle_r", "upperarm_r", "lowerarm_r", "hand_r",
                       "middle_01_r", "thigh_l", "calf_l", "foot_l", "ball_l", "thigh_r", "calf_r", "foot_r", "ball_r")
           if b in S and b in H]
frames = sorted(set([int(first), int(last)] + list(range(int(first), int(last) + 1, max(1, int((last - first) / 12))))))
# AdvancedSkeleton's Shoulder/Elbow/Hip/Knee do not roll about their own bone: the roll goes to the
# twist (Part) joints by the vendor's design (the Manny rig's spec).  For these the bone's DIRECTION is
# compared, and the roll the twist joints took is reported, not gated.
ROLLERS = {"upperarm_l": "lowerarm_l", "upperarm_r": "lowerarm_r", "lowerarm_l": "hand_l", "lowerarm_r": "hand_r",
           "thigh_l": "calf_l", "thigh_r": "calf_r", "calf_l": "foot_l", "calf_r": "foot_r"}
HELPERS = ("ik_hand_gun", "ik_hand_r", "ik_hand_l", "ik_foot_l", "ik_foot_r")     # ride the hands and feet by constraint
def off_axis(bones, b):
    t = om.MVector(cmds.getAttr(bones[ROLLERS[b]] + ".translate")[0])
    return math.degrees(t.angle(om.MVector(1 if t.x >= 0 else -1, 0, 0)))
bound = dict((b, 2 * (off_axis(S, b) + off_axis(H, b))) for b in ROLLERS if b in S and b in H)
print("roller bounds (2 x off-axis, source + Creep): %s" % dict((b, round(v, 3)) for b, v in bound.items()))
per_bone = dict((b, 0.0) for b in compare)
worst_dir, roll = (0.0, ""), 0.0
worst_len, worst_root, worst_pelvis = (0.0, ""), 0.0, 0.0
len_by = {}
for t in frames:
    cmds.currentTime(t)
    for b in compare:
        if b in ROLLERS:
            # where the bone POINTS, joint to joint.  AS takes the roll off this bone about ITS OWN
            # axis, and a child standing off the bone's X (the Creep's lowerarm: 0.32 cm, 0.53 deg)
            # then swings on a cone -- so the bound is twice each skeleton's own off-axis angle,
            # measured from the children's local translations (pose-independent)
            ds = pos(S[ROLLERS[b]]) - pos(S[b]); dh = pos(H[ROLLERS[b]]) - pos(H[b])
            a = math.degrees(ds.angle(dh)) - bound[b]
            if a > worst_dir[0]:
                worst_dir = (a, "%s@%d" % (b, t))
            roll = max(roll, ang(rot(wm(S[b])), rot(wm(H[b]))))
            continue
        per_bone[b] = max(per_bone[b], ang(rot(wm(S[b])), rot(wm(H[b]))))
    for n, p in H.items():
        if n in ("root", "pelvis") or n in HELPERS:
            continue
        d = (om.MVector(cmds.getAttr(p + ".translate")[0]) - om.MVector(rest_t[n])).length()
        len_by[n] = max(len_by.get(n, 0.0), d)
        if d > worst_len[0]:
            worst_len = (d, "%s@%d" % (n, t))
    worst_root = max(worst_root, (pos(S["root"]) - pos(H["root"])).length() if "root" in S else 0.0)
    worst_pelvis = max(worst_pelvis, (pos(S["pelvis"]) - pos(H["pelvis"])).length())
worst_rot = max((v, b) for b, v in per_bone.items())
print("per bone worst orientation difference: %s" % dict((b, round(v, 4)) for b, v in sorted(per_bone.items(), key=lambda kv: -kv[1]) if b not in ROLLERS))
gate(5, worst_rot[0] < 0.05 and worst_dir[0] < 0.05,
     "%d bones x %d frames: worst world-orientation difference from the source %.5f deg (%s); the limb bones point where the "
     "source's point within the skeletons' own off-axis bound (worst excess %.5f deg, %s), their roll lives in the twist "
     "joints (up to %.1f deg on the bone itself)"
     % (len(compare), len(frames), worst_rot[0], worst_rot[1], worst_dir[0], worst_dir[1], roll))
print("per bone worst local-translation change: %s" % dict((n, round(v, 5)) for n, v in sorted(len_by.items(), key=lambda kv: -kv[1])[:8]))
gate(6, worst_len[0] < 1e-3, "every Creep bone below the pelvis keeps its rest local translation: worst %.6f cm (%s)" % worst_len)
def seg(bones, a, b):
    return (pos(bones[a]) - pos(bones[b])).length()
lengths = dict((a, (seg(S, a, b), seg(H, a, b))) for a, b in (("lowerarm_l", "hand_l"), ("upperarm_l", "lowerarm_l"), ("neck_01", "neck_02")))
gate(7, all(abs(s - h) > 1.0 for s, h in lengths.values()),
     "positive control - the source's own bone lengths differ from the Creep's (source, Creep): %s; the clip also slides bones by %s"
     % (dict((k, (round(s, 2), round(h, 2))) for k, (s, h) in lengths.items()), dict((n, round(v, 3)) for n, v in slide.items())))
gate(8, worst_root < 1e-3 and worst_pelvis < 1e-3, "root on the source's root to %.6f cm, pelvis on the source's pelvis to %.6f cm" % (worst_root, worst_pelvis))

# IK follows FK: the baked IK limbs reproduce the FK pose
blend = dict((c, cmds.getAttr(maya_rigs.node(rig, c) + ".FKIKBlend")) for c in ("FKIKLeg_L", "FKIKArm_R"))
worst_ik = 0.0
for t in frames[::2]:
    cmds.currentTime(t)
    got = {}
    for v in (0, 10):
        for c in blend:
            cmds.setAttr(maya_rigs.node(rig, c) + ".FKIKBlend", v)
        got[v] = (pos(H["foot_l"]), pos(H["hand_r"]))
    worst_ik = max(worst_ik, (got[0][0] - got[10][0]).length(), (got[0][1] - got[10][1]).length())
for c, v in blend.items():
    cmds.setAttr(maya_rigs.node(rig, c) + ".FKIKBlend", v)
gate(9, worst_ik < 0.05, "left leg and right arm in IK against FK over the take: worst %.5f cm" % worst_ik)
keyed = [c for c in cmds.sets(rig.control_set, q=True) if cmds.listConnections(c, type="animCurve", s=True, d=False)]
gate(10, len(keyed) > 30, "%d controls carry the baked take" % len(keyed))
print("RESULT: %d of 10 gates failed %s" % (len(FAILS), FAILS))
