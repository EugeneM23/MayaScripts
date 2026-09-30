"""Standalone gates: one weapon socket for every rig (2026-09-30).

    mayapy verify_weapon_socket.py [<Creep_Rig.ma BEFORE the turn>] [<UE5 clip .fbx>]

Run with a scratch MAYA_APP_DIR: it stores and migrates grips. mayapy STANDALONE - it adds
rigs and imports clips, never the animator's scene.

- every catalog weapon at ZERO grip in the right hand of Manny_Rig, Orc_D_Rig and Creep_Rig:
  the blade along the fist's grip line (pinky_01 -> index_01), the thickness along the palm
  normal (both in the standard axes, a row's own frame undone - the Creep Sword's 45 is its
  authored hold), the fields reading 0 0 0;
- the left hand's undialled default (the right grip's mirror) putting the blade along the left
  grip line;
- the Creep Sword standing on the turned Creep exactly where the old asset stood it;
- a UE clip retargeted onto the Creep keeping a zero-grip sword in the fist (was 101.9 deg);
- a remembered (90, 0, 0) migrated to 0 0 0, the weapon where the old grip put it.

Spec: docs/superpowers/specs/2026-09-30-weapon-socket-and-inventory-skin-design.md
"""
import math
import os
import sys

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

sys.path.insert(0, "C:/!!!Work/MayaScripts/SkeldarAnim")
for p in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass
OLD_CREEP = (sys.argv[1] if len(sys.argv) > 1 else
             "C:/Users/MYPC~1/AppData/Local/Temp/claude/C-----Work-MayaScripts/"
             "44cca9df-bb50-4ea4-9958-f12dc6e43aad/scratchpad/creep_backup/Creep_Rig.ma")
CLIP = (sys.argv[2] if len(sys.argv) > 2 else
        "C:/Users/MY PC/AppData/Local/Temp/maya_uebridge/"
        "AS_Longsword_Attack_Back_Light_Combo_1_3P.fbx")
FAILS = []
TOTAL = [0]


def gate(n, ok, msg):
    TOTAL[0] += 1
    print("%s gate %02d: %s" % ("PASS" if ok else "FAIL", n, msg))
    sys.stdout.flush()
    if not ok:
        FAILS.append(n)


def wm(n):
    return om.MMatrix(cmds.getAttr(n + ".worldMatrix[0]"))


def unscaled(m):
    t = om.MTransformationMatrix(m)
    t.setScale((1.0, 1.0, 1.0), om.MSpace.kTransform)
    return t.asMatrix()


def mdiff(a, b):
    return max(abs(x - y) for x, y in zip(list(a), list(b)))


def pos(n):
    return om.MVector(cmds.xform(n, q=True, ws=True, t=True))


def axes(m):
    return [om.MVector(m[4 * i], m[4 * i + 1], m[4 * i + 2]).normal() for i in range(3)]


def ang(a, b):
    return math.degrees(math.acos(max(-1.0, min(1.0, a.normal() * b.normal()))))


def line_ang(a, b):
    """The angle between two LINES (a symmetric width or thickness has no sign)."""
    d = ang(a, b)
    return min(d, 180.0 - d)


def fist(b, s):
    grip = pos(b["index_01_" + s]) - pos(b["pinky_01_" + s])
    forward = pos(b["middle_01_" + s]) - pos(b["hand_" + s])
    return grip, forward, grip ^ forward


def bones_of(rig):
    return dict((p.split("|")[-1].split(":")[-1], p)
                for p in [rig.skeleton_root] + cmds.listRelatives(
                    rig.skeleton_root, ad=True, type="joint", fullPath=True))


def standard_axes(node, entry):
    """The node's axes with the row's own frame undone: R(frame)^-1 . world."""
    frame = om.MMatrix(bonedrive.matrix_of(entry.frame, (0.0, 0.0, 0.0)))
    return axes(frame.inverse() * unscaled(wm(node)))


cmds.file(new=True, force=True)
from maya_scenesetup import attach, bonedrive, catalog, character, equip, grips  # noqa: E402
import maya_rigs  # noqa: E402
import maya_rig_retarget as rr  # noqa: E402

for entry in catalog.WEAPONS:
    for side in ("R", "L"):
        name = grips.optionvar_name(entry.key, side)
        if cmds.optionVar(exists=name):
            cmds.optionVar(remove=name)

RIGS = {}
for key in ("Manny_Rig", "Orc_D_Rig", "Creep_Rig"):
    before = set(r.namespace for r in maya_rigs.rigs())
    character.add_character(catalog.character_by_key(key))
    RIGS[key] = [r for r in maya_rigs.rigs() if r.namespace not in before][0]


# ------------------------------------------------------ zero grip, both hands
# The thickness bound is each rig's own socket roll about the grip line: UE's
# weapon_r stands 8.8 deg off Manny's palm normal, the Creep's (the creature's
# own weapon_test, only turned about its X) 17.0 - the same before the turn.
THICK = {"Manny_Rig": 12.0, "Orc_D_Rig": 12.0, "Creep_Rig": 20.0}


def forget_grips():
    for entry in catalog.WEAPONS:
        for side in ("R", "L"):
            name = grips.optionvar_name(entry.key, side)
            if cmds.optionVar(exists=name):
                cmds.optionVar(remove=name)


n = 1
for key, rig in RIGS.items():
    forget_grips()
    b = bones_of(rig)
    worst_blade = worst_thick = worst_field = 0.0
    left_worst = 0.0
    rows = []
    for entry in catalog.WEAPONS:
        equip.to_hand(rig.skeleton_root, "R", entry)
        node = attach.find_attached(b["hand_r"])
        grip, forward, palm = fist(b, "r")
        x, y, z = standard_axes(node, entry)
        blade, thick = ang(y, grip), line_ang(z, palm)
        rotate, translate = bonedrive.measured_grip(node, b["weapon_r"])
        field = max(abs(v) for v in tuple(rotate) + tuple(translate))
        worst_blade, worst_thick = max(worst_blade, blade), max(worst_thick, thick)
        worst_field = max(worst_field, field)
        equip.to_hand(rig.skeleton_root, "L", entry)
        left = attach.find_attached(b["hand_l"])
        lgrip = fist(b, "l")[0]
        lblade = ang(standard_axes(left, entry)[1], lgrip)
        left_worst = max(left_worst, lblade)
        rows.append("%s %.1f/%.1f L %.1f" % (entry.key, blade, thick, lblade))
        equip.take_off(rig.skeleton_root, "L")
    stored_after = [e.key for e in catalog.WEAPONS for s in ("R", "L")
                    if cmds.optionVar(exists=grips.optionvar_name(e.key, s))]
    print("   %s: %s" % (key, "; ".join(rows)))
    print("   %s left fields (undialled Long Sword, its own sockets): %s" % (key, tuple(
        tuple(round(v, 2) for v in part) for part in
        grips.for_hand(catalog.by_key("LongSword_02"), "L", rig.skeleton_root))))
    gate(n, worst_blade < 15.0 and worst_thick < THICK[key] and worst_field < 1e-6,
         "%s: every weapon at ZERO grip in the right fist - blade off the grip line <= %.1f deg, "
         "thickness off the palm normal <= %.1f deg (the socket's own roll, bound %.0f), fields %.1e"
         % (key, worst_blade, worst_thick, THICK[key], worst_field))
    gate(n + 1, left_worst < 20.0 and not stored_after,
         "%s: the left hand's undialled default (the right grip's mirror through THIS rig's "
         "sockets) - blade off the left grip line <= %.1f deg; the inventory stored no grip: %s"
         % (key, left_worst, stored_after or "none"))
    n += 2
forget_grips()

# ------------------------------------------------ the Creep Sword where it stood
creep = RIGS["Creep_Rig"]
cb = bones_of(creep)
sword_entry = catalog.by_key("Creep_Sword")
equip.to_hand(creep.skeleton_root, "R", sword_entry)
new_sword = attach.find_attached(cb["hand_r"])
cmds.file(OLD_CREEP, i=True, namespace="oldCreep")
old_bone = [j for j in cmds.ls("oldCreep:weapon_r", long=True, type="joint")]
old_place = om.MMatrix(bonedrive.framed((0.0, 45.0, 0.0), tuple(wm(old_bone[0])))) if old_bone else None
err = mdiff(unscaled(wm(new_sword)), old_place) if old_place is not None else 9.0
gate(n, err < 1e-6,
     "the Creep Sword at zero grip on the turned Creep stands where the old asset stood it: %.2e"
     % err)
n += 1
cmds.delete([x for x in cmds.ls("oldCreep:*", assemblies=True, long=True)])
try:
    cmds.namespace(removeNamespace="oldCreep", deleteNamespaceContent=True)
except Exception:
    pass

# ------------------------------------------------------------ the migration
manny = RIGS["Manny_Rig"]
mb = bones_of(manny)
long_sword = catalog.by_key("LongSword_02")
if cmds.optionVar(exists=grips.MIGRATED):
    cmds.optionVar(remove=grips.MIGRATED)
grips.remember("LongSword_02", "R", (90.0, 0.0, 0.0), (0.0, 0.0, 0.0))
expected = om.MMatrix(bonedrive.matrix_of((90.0, 0.0, 0.0), (0.0, 0.0, 0.0))) * wm(mb["weapon_r"])
got = grips.stored("LongSword_02", "R")
equip.to_hand(manny.skeleton_root, "R", long_sword)
node = attach.find_attached(mb["hand_r"])
err = mdiff(unscaled(wm(node)), unscaled(expected))
field = max(abs(v) for v in tuple(got[0]) + tuple(got[1]))
gate(n, err < 1e-6 and field < 1e-9 and cmds.optionVar(exists=grips.MIGRATED),
     "a remembered (90, 0, 0) migrates to 0 0 0 (%.1e) and the Long Sword stands where the old grip "
     "put it (%.2e)" % (field, err))
n += 1
forget_grips()

# ---------------------------------------------- a UE clip: the Creep as Manny
# A UE take turns weapon_r IN the hand (measured on the Longsword combo: its
# local rotation walks from (-23, -36, 11) to (-41, -7, 54)), so the promise is
# not a fixed angle - it is that the Creep holds the take's weapon as Manny
# does, frame for frame (before the turn it stood 101.9 deg off the fist).
equip.to_hand(creep.skeleton_root, "R", long_sword)
equip.to_hand(manny.skeleton_root, "R", long_sword)
before = set(cmds.ls(type="joint", long=True))
cmds.namespace(add="clip")
cmds.namespace(set=":clip")
mel.eval('FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;')
mel.eval('FBXImport -f "%s";' % CLIP.replace("\\", "/"))
cmds.namespace(set=":")
new = [j for j in cmds.ls(type="joint", long=True) if j not in before]
src = min((j for j in new if not cmds.listRelatives(j, parent=True, type="joint")),
          key=lambda j: j.count("|"))
S = [src] + cmds.listRelatives(src, ad=True, type="joint", fullPath=True)
f0 = cmds.findKeyframe(S, which="first")
f1 = cmds.findKeyframe(S, which="last")
cmds.playbackOptions(min=f0, max=f1, animationStartTime=f0, animationEndTime=f1)
results = []
for rig in (manny, creep):
    ok, text = rr.run_retarget(source_root=src, rig=rig)
    results.append(ok)
    print("   " + text[:120])
frames = [float(t) for t in range(int(f0), int(f1) + 1)]      # whole frames: the keys


def in_hand(b):
    """The sword's rotation in its hand's frame."""
    sword = attach.find_attached(b["hand_r"])
    return rotation(unscaled(wm(sword)) * unscaled(wm(b["hand_r"])).inverse())


def rotation(m):
    t = om.MTransformationMatrix(m)
    t.setTranslation(om.MVector(0, 0, 0), om.MSpace.kTransform)
    return t.asMatrix()


def turn_between(a, b):
    """The angle of the rotation taking `a` to `b` (degrees)."""
    q = om.MTransformationMatrix(a * b.inverse()).rotation(asQuaternion=True)
    return math.degrees(2.0 * math.acos(min(1.0, abs(q.w))))


rows, worst_turn = [], 0.0
for f in frames:
    cmds.currentTime(f - 1)
    cmds.currentTime(f)
    held = [in_hand(bones_of(rig)) for rig in (manny, creep)]
    worst_turn = max(worst_turn, turn_between(held[0], held[1]))
    knuckles = []
    for rig in (manny, creep):
        b = bones_of(rig)
        sword = attach.find_attached(b["hand_r"])
        knuckles.append(ang(standard_axes(sword, long_sword)[1], fist(b, "r")[0]))
    rows.append("%.0f: %.1f/%.1f" % (f, knuckles[0], knuckles[1]))
steps = {}
for rig in (manny, creep):
    b = bones_of(rig)
    for node in (b["weapon_r"], attach.find_attached(b["hand_r"])):
        jumps = []
        for axis in "XYZ":
            curves = cmds.listConnections(node + ".rotate" + axis, source=True,
                                          destination=False, type="animCurve") or []
            values = cmds.keyframe(curves[0], q=True, valueChange=True) if curves else []
            jumps.append(max([abs(a - c) for a, c in zip(values, values[1:])] or [0.0]))
        print("   (information) %s: largest rotate step between keys %s" % (
            node.split("|")[-1], [round(v, 1) for v in jumps]))
        if node != b["weapon_r"]:
            steps[rig.namespace] = max(jumps)
print("   (information) blade off the knuckle line, Manny/Creep - the metacarpals animate, and "
      "the Creep's hand is proportioned its own way: " + "  ".join(rows))
gate(n, all(results) and worst_turn < 0.05,
     "a UE clip on the Creep holds its zero-grip Long Sword IN THE HAND exactly as Manny does: the "
     "two swords' rotations in their hands differ by <= %.4f deg at every key (%d frames) - with "
     "gate 05 the Creep is right at its bind AND in a UE take; before its bones turned, the one "
     "excluded the other (bind 5.8 deg, the take 101.9)" % (worst_turn, len(frames)))
n += 1
half = 0.0
for f in frames[:-1]:
    cmds.currentTime(f)
    cmds.currentTime(f + 0.5)
    held = [in_hand(bones_of(rig)) for rig in (manny, creep)]
    half = max(half, turn_between(held[0], held[1]))
gate(n, steps.get("Creep_Rig", 999.0) < 60.0 and half < 2.0,
     "...and BETWEEN the keys: the Creep sword's largest rotate step from key to key %.1f deg "
     "(Manny's %.1f; unfiltered 538), the two swords in their hands at every half frame within "
     "%.3f deg - the bakes are euler-filtered" % (steps.get("Creep_Rig", 999.0),
                                                   steps.get("Manny_Rig", 999.0), half))
cmds.currentTime(f0)

print("\nverify_weapon_socket: %d of %d gates failed %s" % (len(FAILS), TOTAL[0], FAILS or ""))
