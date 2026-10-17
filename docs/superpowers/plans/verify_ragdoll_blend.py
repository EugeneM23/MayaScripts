"""Ragdoll > Blend, standalone (2026-10-17).

    mayapy verify_ragdoll_blend.py <UE5 clip .fbx> [rig key, default Manny_Rig]

A rig added, the clip retargeted through the button, then Blend over the middle of the take:
- All follow at strength 1: the game bones stay on the take;
- Hit reaction with a head impulse: the legs are the take exactly, the head knocked off it and back;
- the take before and after the span untouched, bone lengths kept, one undo, no Bullet node left.
"""

import os
import sys

import maya.standalone
maya.standalone.initialize()

import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402

REPO = "C:/!!!Work/MayaScripts"
sys.path.insert(0, os.environ.get("RAGDOLL_PLUGIN", REPO + "/SkeldarAnim"))
for p in ("matrixNodes", "quatNodes", "fbxmaya", "bullet"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass
CLIP = sys.argv[1].replace("\\", "/")
RIG_KEY = sys.argv[2] if len(sys.argv) > 2 else "Manny_Rig"

import numpy as np  # noqa: E402
from maya_scenesetup import catalog, character  # noqa: E402
import maya_rigs  # noqa: E402
import maya_rig_retarget as rr  # noqa: E402
from maya_ragdoll import blend as bl, fall as rd, impulse, plan  # noqa: E402
from maya_poselib import animdata  # noqa: E402

FAILS = []
COUNT = [0]


def gate(ok, msg):
    COUNT[0] += 1
    print("%s %2d %s" % ("PASS" if ok else "FAIL", COUNT[0], msg))
    if not ok:
        FAILS.append(msg)


cmds.file(new=True, force=True)
cmds.undoInfo(state=True, infinity=True)
character.add_character(catalog.character_by_key(RIG_KEY))
rig = maya_rigs.rigs()[0]
N = lambda leaf: cmds.ls(maya_rigs.node(rig, leaf), long=True)[0]  # noqa: E731
cmds.namespace(add="clip")
cmds.namespace(set=":clip")
mel.eval("FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;")
before = set(cmds.ls(type="joint", long=True))
mel.eval('FBXImport -f "%s";' % CLIP)
cmds.namespace(set=":")
new = [j for j in cmds.ls(type="joint", long=True) if j not in before]
src = min((j for j in new if not cmds.listRelatives(j, parent=True, type="joint")),
          key=lambda j: j.count("|"))
keys = cmds.keyframe(new, query=True, timeChange=True) or [0, 24]
first, last = int(min(keys)), int(max(keys))
cmds.playbackOptions(min=first, max=last, animationStartTime=first, animationEndTime=last)
cmds.select(N("Main"), src)
ok, rtext = rr.run_retarget()
cmds.namespace(removeNamespace="clip", deleteNamespaceContent=True)
cmds.playbackOptions(min=first, max=last, animationStartTime=first, animationEndTime=last)
gate(ok, "clip retargeted onto %s (%d..%d)" % (rig.namespace, first, last))

REF = rd._ref([N("Main")])
A = first + (last - first) // 4
LENGTH = min(40, (last - first) // 2)
B = A + LENGTH
BONES = ["pelvis", "spine_03", "head", "hand_l", "hand_r", "lowerarm_l", "upperarm_r",
         "thigh_l", "calf_l", "foot_l", "foot_r", "calf_r"]
LENGTHS = [("thigh_l", "calf_l"), ("calf_l", "foot_l"), ("upperarm_r", "lowerarm_r"),
           ("lowerarm_r", "hand_r"), ("spine_03", "neck_01"), ("pelvis", "spine_01")]


def wp(leaf):
    return np.array(cmds.xform(N(leaf), query=True, translation=True, worldSpace=True))


def track(frames, names):
    out = {}
    for f in frames:
        cmds.currentTime(f)
        out[f] = dict((b, wp(b)) for b in names)
    return out


ALL = sorted(set(BONES + [x for p in LENGTHS for x in p]))
take = track(range(first, last + 1), ALL)


def zones(state, strength):
    return dict((z, [state, strength]) for z in plan.ZONES)


def strays(run, _zones=None):
    """The worst distance of a body from the take over the run, per zone."""
    out = {}
    for t in run["bodies"]:
        for key, m in run["bodies"][t].items():
            if key not in run["target"][t]:
                continue
            d = float(np.linalg.norm(plan.pos(m) - plan.pos(run["target"][t][key])))
            z = plan.zone_of(key)
            out[z] = max(out.get(z, 0.0), d)
    return out


# ---------------------------------------------------------------- 1: all follow, strength 1
cmds.currentTime(A)
cmds.select(N("FKElbow_R"))
ok, line = bl.blend(given={"length": LENGTH, "zones": zones("follow", 1.0),
                           "blend_in": 4, "blend_out": 8})
print("   ", line)
gate(ok, "Blend pressed (All follow, strength 1)")
layer = bl.layer_name(A)
gate(cmds.objExists(layer), "layer %s made" % layer)
cmds.undo()
gate(not cmds.objExists(layer), "one undo takes the blend away")
cmds.redo()
gate(cmds.objExists(layer), "redo brings it back")
gate(len(cmds.ls(type=("bulletSolverShape", "bulletRigidBodyShape",
                       "bulletRigidBodyConstraintShape")) or []) == 0
     and not cmds.ls("skeldarRagdoll*"), "no Bullet node left")
after = track(range(first, last + 1), ALL)
outside = max(float(np.linalg.norm(after[f][b] - take[f][b]))
              for f in after if f < A or f > B for b in ALL)
gate(outside < 1e-3, "the take before and after the span untouched (%.6f cm)" % outside)
inside = max((float(np.linalg.norm(after[f][b] - take[f][b])), b, f) for f in range(A, B + 1)
             for b in BONES)
_s1 = strays(bl.LAST["run"])
print("    bodies off the take:", ", ".join("%s %.2f" % (z, _s1[z]) for z in plan.ZONES))
gate(inside[0] < 4.0, "strength 1: every bone on the take within 4 cm (worst %.3f cm, %s at %d)"
     % inside)
worst_len = 0.0
for f in range(A, B + 1):
    for p in LENGTHS:
        l0 = np.linalg.norm(take[f][p[0]] - take[f][p[1]])
        worst_len = max(worst_len, abs(np.linalg.norm(after[f][p[0]] - after[f][p[1]]) - l0))
gate(worst_len < 0.5, "bone lengths kept (worst %.4f cm)" % worst_len)
for L in rd.layers():
    cmds.delete(L)

# ---------------------------------------------------------------- 2: hit reaction + head impulse
cmds.currentTime(A)
arrow, _l = impulse.create([N("FKHead_M")])
HIT = A + 6
cmds.setAttr(arrow + ".frame", HIT)
cmds.setAttr(arrow + ".speed", 4.0)
HIT_GIVEN = {"length": LENGTH, "zones": dict(plan.preset("hit")), "blend_in": 4, "blend_out": 10}
cmds.setAttr(arrow + ".enabled", 0)          # the same blend without the hit, to measure it against
cmds.select(N("FKElbow_R"))
ok, line = bl.blend(given=HIT_GIVEN)
cmds.undo()                                  # straight after the press (trap 222)
calm_frames = bl.LAST["frames"]
cmds.setAttr(arrow + ".enabled", 1)
cmds.currentTime(A)
cmds.select(N("FKElbow_R"))
ok, line = bl.blend(given=HIT_GIVEN)
print("   ", line)
gate(ok and "1 impulse" in line, "Blend with Hit reaction and a head impulse at %d" % HIT)
run = bl.LAST["run"]
legs = max(float(np.linalg.norm(plan.pos(run["bodies"][t][k]) - plan.pos(run["target"][t][k])))
           for t in run["bodies"] for k in run["bodies"][t] if plan.zone_of(k) in ("leg_l", "leg_r"))
gate(legs < 5.0, "the legs' (Anim) bodies held near the take - they carry the pelvis, the bones play the take (%.2f cm)" % legs)
after = track(range(A, B + 1), ALL)
leg_bones = max(float(np.linalg.norm(after[f][b] - take[f][b]))
                for f in range(A, B + 1) for b in ("foot_l", "foot_r", "calf_l", "calf_r"))
gate(leg_bones < 0.05, "the leg bones play the take (%.4f cm)" % leg_bones)


def card_at(frames, leaf, i):
    k = frames["bones"].index(leaf)
    return np.array(animdata.decode(frames["world"][i][7 * k:7 * k + 7])[12:15])


head = [float(np.linalg.norm(card_at(bl.LAST["frames"], "head", f - A) - card_at(calm_frames, "head", f - A)))
        for f in range(A, B + 1)]
peak = max(range(len(head)), key=lambda i: head[i])
print("    head off the blend without the hit:", " ".join("%.1f" % h for h in head))
gate(max(head[:HIT - A]) < 0.05 and head[peak] > 4.0,
     "the head as without the hit before it (%.3f) and knocked off it (%.1f cm at %d)"
     % (max(head[:HIT - A]), head[peak], A + peak))
back = float(np.linalg.norm(after[B]["head"] - take[B]["head"]))
gate(back < 1.0, "and back on the take by the span's end (%.2f cm)" % back)
cmds.undo()

print("")
print("%d of %d gates failed" % (len(FAILS), COUNT[0]))
for f in FAILS:
    print("  FAILED:", f)
