"""Verify: a portrait dropped on a character swaps it (2026-10-17). mayapy standalone.

    mayapy verify_character_swap.py [plugin dir]

A  a Manny UE5 skeleton playing a UE clip, an additive layer on its pelvis (+12 cm), a cube
   parent-constrained to its hand_r, a Long Sword in its right hand - swapped for a Manny rig:
   nothing asked (a twin), every game bone where the old one was on every sampled frame, the layer
   in the take, the cube still on hand_r, the sword carried, the old skeleton gone.
B  that rig, a knot on FKHead_M turned 20 deg, a sphere constrained to FKWrist_R - swapped for a
   Manny UE5 skeleton: the knot's turn in the take, the sphere re-bound to hand_r, the rig gone.
C  that skeleton swapped for a Creep rig: asked once (Keep proportions), every bone pointing as the
   old one, lengths the Creep's.
D  the Creep rig swapped for a Manny rig, the question Cancelled: nothing changed.
"""
import math
import os
import sys

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = (sys.argv[1] if len(sys.argv) > 1 and os.path.isdir(sys.argv[1])
          else os.path.normpath(os.path.join(HERE, "..", "..", "..", "SkeldarAnim")))
sys.path.insert(0, PLUGIN)
for p in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass

HEAVY = "C:/!!!Work/Animations/Export/LongSword_Attack_Right_Heavy_3P.FBX"

import maya_retargetmode as rm
import maya_rigs
from maya_scenesetup import catalog, character, equip, swap
from maya_uebridge import skeletonimport

print("plugin:", os.path.dirname(swap.__file__))
FAILS, ASKED, ANSWER = [], [], [rm.KEEP]


def gate(n, ok, msg):
    print("%s gate %s: %s" % ("PASS" if ok else "FAIL", n, msg))
    sys.stdout.flush()
    if not ok:
        FAILS.append(n)


def answerer(text):
    ASKED.append(text)
    return ANSWER[0]


rm.set_asker(answerer)
rm.set_setting(rm.AUTO)

SKIP = ("ik_", "camera_", "center_of_mass", "interaction")


def leaf(p):
    return p.split("|")[-1].split(":")[-1]


def by_leaf(root):
    js = [root] + (cmds.listRelatives(root, ad=True, type="joint", fullPath=True) or [])
    return dict((leaf(j), j) for j in js)


def world(n):
    return om.MMatrix(cmds.xform(n, q=True, ws=True, m=True))


def pos(m):
    return om.MVector(m[12], m[13], m[14])


def quat(m):
    return om.MTransformationMatrix(m).rotation(asQuaternion=True)


def ang(a, b):
    q = a.inverse() * b
    return math.degrees(2 * math.acos(max(-1.0, min(1.0, abs(q.w)))))


FRAMES = []


def sample(nodes):
    out = {}
    for f in FRAMES:
        cmds.currentTime(f)
        for name, path in nodes.items():
            out[(f, name)] = world(path)
    return out


def compare(before, after, keys=None, angle_only=False):
    worst_d, worst_a, at, at_a = 0.0, 0.0, "", ""
    for key, m in before.items():
        if key not in after:
            continue
        if keys and key[1] not in keys:
            continue
        if "_twist_" in key[1]:
            continue     # AdvancedSkeleton spreads the roll its own way (its twist network)
        roll_free = key[1].startswith(("upperarm_", "lowerarm_", "thigh_", "calf_"))
        d = (pos(m) - pos(after[key])).length()
        a = ang(quat(m), quat(after[key]))
        if d > worst_d and not angle_only:
            worst_d, at = d, key
        if not roll_free and a > worst_a:
            worst_a, at_a = a, key
    return worst_d, worst_a, "%s / %s" % (at, at_a if worst_a else "")


def bones(root):
    return dict((k, v) for k, v in by_leaf(root).items() if not k.startswith(SKIP))


def add_skeleton(key):
    before = set(cmds.ls(type="joint", long=True))
    character.add_character(catalog.character_by_key(key))
    fresh = [j for j in cmds.ls(type="joint", long=True) if j not in before]
    return min(fresh, key=lambda p: (p.count("|"), p))


def import_clip(path, ns):
    before = set(cmds.ls(type="joint", long=True))
    cmds.namespace(add=ns)
    cmds.namespace(set=":" + ns)
    mel.eval('FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;')
    mel.eval('FBXImport -f "%s";' % path)
    cmds.namespace(set=":")
    new = [j for j in cmds.ls(type="joint", long=True) if j not in before]
    return min((j for j in new if not cmds.listRelatives(j, parent=True, type="joint")),
               key=lambda j: j.count("|"))


def roots_now():
    from maya_scenesetup import deletion
    return [c.root for c in deletion.characters()]


# ---------------------------------------------------------------- A
cmds.file(new=True, force=True)
skel = add_skeleton("Manny")
if skel is None:
    skel = add_skeleton(catalog.default_character().key)
clip = import_clip(HEAVY, "clipA")
s0 = cmds.findKeyframe(list(by_leaf(clip).values()), which="first")
s1 = cmds.findKeyframe(list(by_leaf(clip).values()), which="last")
cmds.playbackOptions(min=s0, max=s1, animationStartTime=s0, animationEndTime=s1)
skeletonimport.transfer(clip, skel, s0, s1)
cmds.namespace(removeNamespace=":clipA", deleteNamespaceContent=True)
FRAMES[:] = [round(s0 + (s1 - s0) * i / 6.0) for i in range(7)]
old = bones(skel)
pelvis = old["pelvis"]
layer = cmds.animLayer("SwapTestLayer")
cmds.animLayer(layer, edit=True, attribute=pelvis + ".translateY")
cmds.setKeyframe(pelvis, attribute="translateY", animLayer=layer, time=s0,
                 value=cmds.getAttr(pelvis + ".ty", time=s0) + 12.0)
cmds.setKeyframe(pelvis, attribute="translateY", animLayer=layer, time=s1,
                 value=cmds.getAttr(pelvis + ".ty", time=s1) + 12.0)
cube = cmds.polyCube(name="swapCube")[0]
cmds.xform(cube, ws=True, t=pos(world(old["hand_r"])) + om.MVector(5, 0, 0))
cmds.parentConstraint(old["hand_r"], cube, maintainOffset=True)
sword = catalog.WEAPONS[0]
print("   ", equip.to_hand(skel, "R", sword))
before = sample(old)
cube_before = sample({"cube": cube})
ASKED[:] = []
text = swap.swap(catalog.character_for("Manny", "rig"), skel)
print("   ", text)
rig = maya_rigs.rigs()[-1] if maya_rigs.rigs() else None
gate("A1", rig is not None and not cmds.objExists(skel), "a rig in, the skeleton gone")
gate("A2", not ASKED, "a twin is not asked (%d questions)" % len(ASKED))
new = bones(rig.skeleton_root)
d, a, at = compare(before, sample(new))
gate("A3", d < 0.25 and a < 0.5, "every bone where the old one was (the limb bones' roll is the twist joints'): %.4f cm, %.4f deg %s" % (d, a, at))
cd, ca, _ = compare(cube_before, sample({"cube": cube}))
gate("A4", cd < 0.25, "the cube still rides hand_r: %.4f cm" % cd)
cons = cmds.listRelatives(cube, type="parentConstraint") or []
tl = cmds.parentConstraint(cons[0], q=True, targetList=True) if cons else []
gate("A5", tl and leaf(tl[0]) == "hand_r" and maya_rigs.namespace_of(
    cmds.ls(tl[0], long=True)[0]) == rig.namespace, "re-bound to the rig's hand_r: %s" % tl)
held, _w = equip.occupant(rig.skeleton_root, "R")
gate("A6", bool(held), "the sword carried: %s" % held)

# ---------------------------------------------------------------- B
from maya_tools import knots
head = maya_rigs.node(rig, "FKHead_M")
knots.create("knot", [head], highlight=None)
knot = [k for k in knots.knots() if knots.source_of(k) and leaf(knots.source_of(k)) == "FKHead_M"]
if knot:
    cmds.setAttr(knot[0] + ".rotateX", lock=False)
    for f in FRAMES:
        cmds.setKeyframe(knot[0], attribute="rotateX", time=f,
                         value=cmds.getAttr(knot[0] + ".rotateX", time=f) + 20.0)
sphere = cmds.polySphere(name="swapSphere")[0]
wrist = maya_rigs.node(rig, "FKWrist_R")
cmds.xform(sphere, ws=True, t=pos(world(wrist)) + om.MVector(0, 8, 0))
cmds.parentConstraint(wrist, sphere, maintainOffset=True)
old = bones(rig.skeleton_root)
before = sample(old)
sphere_before = sample({"sphere": sphere})
rig_ns = rig.namespace
text = swap.swap(catalog.character_for("Manny", "skeleton"), rig.skeleton_root)
print("   ", text)
gate("B1", maya_rigs.find(rig_ns) is None, "the rig gone")
skel = [r for r in roots_now() if not maya_rigs.rig_of(r, maya_rigs.rigs())][-1]
d, a, at = compare(before, sample(bones(skel)))
gate("B2", d < 0.25 and a < 0.5, "the knot's turn and the take on the skeleton: %.4f cm, %.4f deg %s"
     % (d, a, at))
sd, _sa, _ = compare(sphere_before, sample({"sphere": sphere}))
cons = cmds.listRelatives(sphere, type="parentConstraint") or []
tl = cmds.parentConstraint(cons[0], q=True, targetList=True) if cons else []
gate("B3", tl and leaf(tl[0]) == "hand_r" and sd < 0.5,
     "the sphere re-bound to hand_r: %s, %.4f cm" % (tl, sd))

# ---------------------------------------------------------------- C
old = bones(skel)
before = sample(old)
ASKED[:] = []
ANSWER[0] = rm.KEEP
text = swap.swap(catalog.character_for("Creep", "rig"), skel)
print("   ", text)
creep = [r for r in maya_rigs.rigs() if r.namespace.startswith("Creep")]
gate("C1", len(ASKED) == 1 and creep and not cmds.objExists(skel),
     "asked once, a Creep in, the skeleton gone (%d)" % len(ASKED))
if creep:
    new = bones(creep[0].skeleton_root)
    after = sample(new)
    worst, at = 0.0, ""
    for f in FRAMES:
        for a_, b_ in (("upperarm_l", "lowerarm_l"), ("lowerarm_r", "hand_r"),
                       ("thigh_l", "calf_l"), ("calf_r", "foot_r"),
                       ("neck_01", "neck_02")):
            u = pos(before[(f, b_)]) - pos(before[(f, a_)])
            v = pos(after[(f, b_)]) - pos(after[(f, a_)])
            x = math.degrees(u.angle(v))
            if x > worst:
                worst, at = x, (f, a_)
    gate("C2", worst < 1.0, "every limb pointing as the old one: %.4f deg %s" % (worst, at))

# ---------------------------------------------------------------- D
count = len(cmds.ls())
ANSWER[0] = rm.CANCEL
text = swap.swap(catalog.character_for("Manny", "rig"), creep[0].skeleton_root)
print("   ", text)
gate("D1", text == swap.CANCELLED and maya_rigs.find(creep[0].namespace) is not None,
     "Cancel: the Creep kept")
gate("D2", abs(len(cmds.ls()) - count) <= 4, "Cancel: nothing left (%d -> %d nodes)"
     % (count, len(cmds.ls())))

rm.set_asker(None)
print("RESULT: %d failed %s" % (len(FAILS), FAILS))
