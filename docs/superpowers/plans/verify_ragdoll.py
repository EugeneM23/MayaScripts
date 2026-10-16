"""Ragdoll > Fall, standalone (2026-10-16).

    mayapy verify_ragdoll.py <UE5 clip .fbx> [rig key, default Manny_Rig]

A rig added, the clip retargeted through the button, then Fall from the middle of the take:
- keys before the fall untouched, the layer weighted 0 there;
- the game bones' lengths kept on every frame;
- the body leaves the fall's frame moving as the clip did;
- no bone below the floor (by more than its body's radius) on any frame;
- at rest by the end, lying (the pelvis low);
- every Bullet node gone; one undo takes the fall back;
- the base-layer mode; a selected box stopping the fall; a second Fall replacing its layer.
"""

import math
import sys

import maya.standalone
maya.standalone.initialize()

import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

REPO = "C:/!!!Work/MayaScripts"
sys.path.insert(0, REPO + "/SkeldarAnim")
for p in ("matrixNodes", "quatNodes", "fbxmaya", "bullet"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass
CLIP = sys.argv[1].replace("\\", "/")
RIG_KEY = sys.argv[2] if len(sys.argv) > 2 else "Manny_Rig"

from maya_scenesetup import catalog, character  # noqa: E402
import maya_rigs  # noqa: E402
import maya_rig_retarget as rr  # noqa: E402
from maya_ragdoll import fall as rd  # noqa: E402

FAILS = []
COUNT = [0]


def gate(ok, msg):
    COUNT[0] += 1
    print("%s %2d %s" % ("PASS" if ok else "FAIL", COUNT[0], msg))
    if not ok:
        FAILS.append(msg)


def wp(n):
    return om.MVector(*cmds.xform(n, query=True, translation=True, worldSpace=True))


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

BONES = ["thigh_r", "foot_l", "pelvis", "spine_03", "head", "hand_l", "hand_r", "foot_l", "foot_r", "calf_l", "calf_r",
         "lowerarm_l", "upperarm_r", "thigh_l"]
LENGTHS = [("thigh_l", "calf_l"), ("calf_l", "foot_l"), ("upperarm_r", "lowerarm_r"),
           ("lowerarm_r", "hand_r"), ("spine_03", "neck_01"), ("pelvis", "spine_01")]


def track(frames):
    out = {}
    for f in frames:
        cmds.currentTime(f)
        out[f] = dict((b, wp(N(b))) for b in set(BONES + [x for p in LENGTHS for x in p]))
    return out


A = first + (last - first) // 2
LENGTH = 50
raw_before = track(range(first, A))
rest = track([A])[A]
lengths0 = dict((p, (rest[p[0]] - rest[p[1]]).length()) for p in LENGTHS)
bullet_before = len(cmds.ls(type=("bulletSolverShape", "bulletRigidBodyShape",
                                  "bulletRigidBodyConstraintShape")) or [])

cmds.currentTime(A)
cmds.select(N("FKElbow_R"))
ok, line = rd.fall(given={"length": LENGTH})
print("   ", line)
gate(ok, "Fall pressed")
B = A + LENGTH
layer = rd.layer_name(A)
gate(cmds.objExists(layer), "layer %s made" % layer)
cmds.undo()
gate(not cmds.objExists(layer), "one undo takes the fall away")
cmds.redo()
gate(cmds.objExists(layer), "redo brings it back")
gate(len(cmds.ls(type=("bulletSolverShape", "bulletRigidBodyShape",
                       "bulletRigidBodyConstraintShape")) or []) == bullet_before
     and not cmds.ls("skeldarRagdoll*"), "no Bullet node left")

after = track(range(first, B + 1))
worst_before = max((after[f][b] - raw_before[f][b]).length() for f in raw_before for b in BONES)
gate(worst_before < 1e-3, "the take before the fall untouched (%.6f cm)" % worst_before)

worst_len = 0.0
for f in range(A, B + 1):
    for p in LENGTHS:
        worst_len = max(worst_len, abs((after[f][p[0]] - after[f][p[1]]).length() - lengths0[p]))
gate(worst_len < 0.5, "bone lengths kept (worst %.4f cm)" % worst_len)

v_clip = (rest["pelvis"] - raw_before[A - 1]["pelvis"]).length()
v_fall = (after[A + 1]["pelvis"] - after[A]["pelvis"]).length()
print("    pelvis per frame: clip %.3f, fall %.3f" % (v_clip, v_fall))
gate(abs(v_fall - v_clip) < max(1.5, 0.35 * v_clip), "the fall starts with the clip's motion")

floor = float(line.split("floor at ")[1].split(" cm")[0])
lowest = min(after[f][b].y for f in range(A, B + 1) for b in BONES)
low_at = min(((after[f][b].y, b, f) for f in range(A, B + 1) for b in BONES))
print("    lowest", low_at)
gate(lowest > floor - 3.0, "nothing under the floor (lowest bone %.2f, floor %.2f)" % (lowest, floor))

for f in range(A, B + 1, 5):
    print("    %3d pelvis %s head y %.1f" % (f, [round(v, 1) for v in after[f]["pelvis"]],
                                              after[f]["head"].y))
settle = (after[B]["pelvis"] - after[B - 3]["pelvis"]).length()
gate(after[B]["pelvis"].y < rest["pelvis"].y * 0.5, "lying at the end (pelvis %.1f, was %.1f)"
     % (after[B]["pelvis"].y, rest["pelvis"].y))
gate(settle < 3.0, "at rest by the end (pelvis moved %.2f cm over the last 3 frames)" % settle)

print("")
print("%d of %d gates failed" % (len(FAILS), COUNT[0]))
for f in FAILS:
    print("  FAILED:", f)


def knee(f, side):
    p = after[f]
    thigh = p["calf_" + side] - p["thigh_" + side]
    calf = p["foot_" + side] - p["calf_" + side]
    left = after[f]["thigh_l"] - after[f]["thigh_r"]
    c = (thigh ^ calf)
    ang = math.degrees(thigh.angle(calf))
    return ang if c * left >= 0 else -ang


worst_knee = min(knee(f, s) for f in range(A, B + 1) for s in ("l", "r"))
gate(worst_knee > -8.0, "no knee bends backward (worst %.1f deg)" % worst_knee)
print("")
print("%d of %d gates failed" % (len(FAILS), COUNT[0]))

from maya_poselib import animdata  # noqa: E402
hdr, frm = rd.LAST["header"], rd.LAST["frames"]
order = frm["bones"]
worst_bake = (0.0, None, None)
for i, f in enumerate(range(A, B + 1)):
    cmds.currentTime(f)
    row = frm["world"][i]
    for b in BONES:
        k = order.index(b)
        m = animdata.decode(row[7 * k:7 * k + 7])
        d = (wp(N(b)) - om.MVector(m[12], m[13], m[14])).length()
        if d > worst_bake[0]:
            worst_bake = (d, b, f)
print("    bake worst", worst_bake)
gate(worst_bake[0] < 3.0, "the rig plays the simulation (worst %.3f cm, %s at %s)" % worst_bake)
print("%d of %d gates failed" % (len(FAILS), COUNT[0]))


# ---------------------------------------------------------------- phase 2: base layer + a sword
from maya_scenesetup import equip  # noqa: E402

cmds.undo()                                   # the first fall away (the measures above moved time,
while cmds.objExists(layer):                  # which mayapy records: undo until the layer goes)
    cmds.undo()
gate(not cmds.objExists(layer), "back to the take before the second press")
sword = catalog.WEAPONS[0]
print("   ", equip.to_hand(rig.skeleton_root, "R", sword))
weapon, where = equip.occupant(rig.skeleton_root, "R")
gate(where == "hand", "%s in the right hand" % sword.label)
cmds.currentTime(A)
cmds.select(N("FKElbow_R"))
ok, line = rd.fall(given={"length": LENGTH, "layer": "base"})
print("   ", line)
gate(ok and not rd.layers(), "Fall onto the base layer, no layer made")
weapon, where = equip.occupant(rig.skeleton_root, "R")
gate(where == "floor", "the sword is on the floor road after the fall (%s)" % where)
wr = N("weapon_r")
worst_follow = 0.0
low_sword = 1e9
for f in range(A, B + 1, 2):
    cmds.currentTime(f)
    box = cmds.exactWorldBoundingBox(weapon)
    low_sword = min(low_sword, box[1])
cmds.currentTime(B)
end_box = cmds.exactWorldBoundingBox(weapon)
floor = rd.LAST["run"]["floor"]
gate(low_sword > floor - 3.0, "the sword never under the floor (lowest %.2f, floor %.2f)"
     % (low_sword, floor))
gate(end_box[1] < floor + 15.0, "the sword lies on the floor at the end (%.2f)" % end_box[1])
cmds.currentTime(A - 3)
hand_before = wp(N("hand_r"))
sword_before = om.MVector(*cmds.xform(weapon, query=True, translation=True, worldSpace=True))
gate((hand_before - sword_before).length() < 40.0, "before the fall the sword is still in the hand "
     "(%.1f cm from it)" % (hand_before - sword_before).length())

# ---------------------------------------------------------------- phase 3: a box in the way
while equip.occupant(rig.skeleton_root, "R")[1] == "floor":
    cmds.undo()
cmds.currentTime(A)
box = cmds.polyCube(width=200, height=60, depth=120, name="obstacle")[0]
cmds.xform(box, worldSpace=True, translation=(0, 30, 300))
cmds.select(N("FKElbow_R"), box)
ok, line = rd.fall(given={"length": LENGTH})
print("   ", line)
gate(ok and "1 collider" in line, "Fall with a box selected")
cmds.currentTime(B)
pelvis_end = wp(N("pelvis"))
print("    pelvis at the end", [round(v, 1) for v in pelvis_end])
free_end = after[B]["pelvis"]
gate(pelvis_end.z < 240.0 or pelvis_end.y > 45.0, "the box stops the body (pelvis ends at z %.1f y %.1f; "
     "with nothing in the way z %.1f)" % (pelvis_end.z, pelvis_end.y, free_end.z))
gate(not cmds.listConnections(box + ".translateX", source=True, destination=False),
     "the box itself untouched")

# ---------------------------------------------------------------- phase 4: again on the same frame
cmds.currentTime(A)
cmds.select(N("FKElbow_R"))
ok, line = rd.fall(given={"length": 20})
gate(ok and rd.layers() == [rd.layer_name(A)], "a second Fall on the frame replaces its layer (%s)"
     % rd.layers())

# ---------------------------------------------------------------- phase 5: the card's press, closed
from maya_ragdoll import panel  # noqa: E402
cmds.optionVar(stringValue=(panel.OPTION, '{"length": 15, "layer": "new"}'))
cmds.currentTime(A + 2)
cmds.select(N("FKWrist_L"))
line = panel.press_fall()
print("   ", line)
gate("falls from frame %d to %d" % (A + 2, A + 17) in line, "the card's press with the card closed")


# ---------------------------------------------------------------- phase 6: impulses
from maya_ragdoll import impulse, plan  # noqa: E402
import numpy as np  # noqa: E402
for L in rd.layers():
    cmds.delete(L)
cmds.currentTime(A)
arrow, iline = impulse.create([N("FKHead_M")])
print("   ", iline)
gate(cmds.getAttr(arrow + "." + impulse.MARKER) == "head" and cmds.getAttr(arrow + ".frame") == A,
     "+ Impulse on FKHead_M: an arrow on the head at frame %d" % A)
cmds.undo()
gate(not cmds.objExists(arrow), "one undo takes the arrow away")
cmds.redo()
gate(cmds.objExists(arrow), "redo brings it back")
gate(maya_rigs.under(arrow, rig.group), "the arrow is under the rig's group (Delete takes it)")
REF = rd._ref([N("Main")])
S = rd.settings({"length": 30})
T = 30
fps = rd._fps()


def sim(**kw):
    return rd.simulate(REF, A, A + T, S, **kw)["bodies"]


cmds.setAttr(arrow + ".enabled", 0)
base = sim()
off = sim()
same = max(np.abs(base[t]["head"] - off[t]["head"]).max() for t in base)
gate(same < 1e-6, "a disabled arrow changes nothing (%.2e)" % same)
centre = plan.pos(base[A]["head"])


def aim(tip, direction, frame, speed=6.0):
    cmds.setAttr(arrow + ".enabled", 1)
    cmds.setAttr(arrow + ".frame", frame)
    cmds.setAttr(arrow + ".speed", speed)
    cmds.currentTime(A)
    cmds.xform(arrow, worldSpace=True, matrix=plan.flat(impulse.arrow_matrix(tip, direction)))


aim(centre, (1, 0, 0), A)
hit = sim()
dv = ((plan.pos(hit[A + 1]["head"]) - plan.pos(hit[A]["head"]))
      - (plan.pos(base[A + 1]["head"]) - plan.pos(base[A]["head"]))) * fps
print("    head dv on the hit step (cm/s)", np.round(dv, 1))
along = dv[0]
gate(along > 150 and abs(dv[0]) > 2 * max(abs(dv[1]), abs(dv[2])),
     "a 6 m/s hit along +X knocks the head along +X (%.0f cm/s)" % along)


def turned(bodies, t):
    r = plan.rot(bodies[t]["head"]) @ plan.rot(bodies[A]["head"]).T
    return math.degrees(math.acos(max(-1, min(1, (np.trace(r) - 1) / 2))))


aim(centre + np.array([0, 0, 0.0]) + plan.rot(base[A]["head"])[0] * 12.0, (1, 0, 0), A)
spun = sim()
def apart(one, two, t):
    r = plan.rot(one[t]["head"]) @ plan.rot(two[t]["head"]).T
    return math.degrees(math.acos(max(-1, min(1, (np.trace(r) - 1) / 2))))


gate(apart(spun, hit, A + 2) > 3.0,
     "a hit off the head's axis turns it (%.1f deg from the hit through its centre at +2; that "
     "one swung it %.1f on its neck)" % (apart(spun, hit, A + 2), apart(hit, base, A + 2)))
aim(centre, (1, 0, 0), A + 10)
mid = sim()
before = max(np.abs(mid[t]["head"] - base[t]["head"]).max() for t in range(A, A + 10))
after_ = (plan.pos(mid[A + 14]["head"]) - plan.pos(base[A + 14]["head"]))[0]
gate(before < 1e-6 and after_ > 3.0, "a hit at %d changes nothing before it (%.1e) and moves the head "
     "after (%.1f cm)" % (A + 10, before, after_))
aim(centre, (1, 0, 0), A + T + 5)
run = rd.simulate(REF, A, A + T, S)
gate(any("after the fall" in n for n in run["impulse_notes"]) and not run["impulses"],
     "an arrow after the fall is named: %s" % run["impulse_notes"])
aim(centre, (1, 0, 0), A)
cmds.select(N("FKElbow_R"))
ok, line = rd.fall(given={"length": T})
print("   ", line)
gate(ok and "1 impulse: head 6 m/s at %d" % A in line, "Fall names the hit")

print("")
print("%d of %d gates failed" % (len(FAILS), COUNT[0]))
for f in FAILS:
    print("  FAILED:", f)
