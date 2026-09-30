"""Standalone gates: two weapons per character, a weapon on the floor, and the
inventory's scene actions (2026-09-29).

    mayapy verify_inventory.py [<UE5 clip .fbx>]

An empty scene, a Manny rig (Add Character), the inventory's own functions
(`equip`): a sword in the right hand and a dagger in the left, both driving
their bones; the left hand's default grip standing a weapon as the world
mirror of the right one; a spear dropped on the floor with both hands taken
(the right hand's weapon replaced), lying flat, the bone on it, the bone's own
track parked and handed back EXACTLY; a retarget with a dagger in the left hand
and the spear on the floor (the spear stays, the fresh clip is parked); the
export bones only; the Creep's geometric sockets. mayapy STANDALONE: it adds
rigs and deletes things - never the animator's scene.

Spec: docs/superpowers/specs/2026-09-29-weapon-inventory-design.md
"""
import os
import sys
import tempfile

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

sys.path.insert(0, "C:/!!!Work/MayaScripts/SkeldarAnim")
for p in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass
CLIP = (sys.argv[1] if len(sys.argv) > 1 else
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


def mdiff(a, b):
    return max(abs(x - y) for x, y in zip(list(a), list(b)))


MX = om.MMatrix([-1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1])


def unscaled(matrix):
    t = om.MTransformationMatrix(matrix)
    t.setScale((1.0, 1.0, 1.0), om.MSpace.kTransform)
    return t.asMatrix()


def mirror_error(left, right):
    """The left weapon node against the world mirror of the right one:
    Mz . W_r . Mx (the model mirrored through its thickness)."""
    from maya_scenesetup import bonedrive
    mz = om.MMatrix(bonedrive.MODEL_MIRROR)
    return mdiff(unscaled(wm(left)), mz * unscaled(wm(right)) * MX)


def bones_of(rig):
    return dict((p.split("|")[-1].split(":")[-1], p)
                for p in [rig.skeleton_root] + cmds.listRelatives(
                    rig.skeleton_root, ad=True, type="joint", fullPath=True))


def lowest_point(node):
    low = None
    for mesh in cmds.listRelatives(node, allDescendents=True, type="mesh",
                                   fullPath=True) or []:
        if cmds.getAttr(mesh + ".intermediateObject"):
            continue
        fn = om.MFnMesh(om.MSelectionList().add(mesh).getDagPath(0))
        ys = [p.y for p in fn.getPoints(om.MSpace.kWorld)]
        low = min(ys) if low is None else min(low, min(ys))
    return low


def curves_of(node):
    out = {}
    for channel in ("translateX", "translateY", "translateZ",
                    "rotateX", "rotateY", "rotateZ"):
        plug = node + "." + channel
        found = cmds.listConnections(plug, source=True, destination=False,
                                     type="animCurve") or []
        if found:
            c = found[0]
            out[channel] = (cmds.ls(c, uuid=True)[0],
                            tuple(cmds.keyframe(c, query=True, timeChange=True)),
                            tuple(round(v, 9) for v in cmds.keyframe(c, query=True, valueChange=True)),
                            tuple(cmds.keyTangent(c, query=True, inTangentType=True)),
                            tuple(cmds.keyTangent(c, query=True, outTangentType=True)))
        else:
            out[channel] = ("value", round(cmds.getAttr(plug), 9))
    return out


cmds.file(new=True, force=True)
from maya_scenesetup import (attach, bonedrive, catalog, character, equip,  # noqa: E402
                             floor, grips, weaponspace)
from maya_uebridge import animexport  # noqa: E402
import maya_rigs  # noqa: E402
import maya_rig_retarget as rr  # noqa: E402

SWORD, DAGGER = catalog.by_key("LongSword_02"), catalog.by_key("Dagger_01")
SPEAR = catalog.by_key("Spear_01")
for key in ("LongSword_02", "Dagger_01", "Spear_01", "Creep_Sword"):
    for side in ("R", "L"):
        name = grips.optionvar_name(key, side)
        if cmds.optionVar(exists=name):
            cmds.optionVar(remove=name)

character.add_character(catalog.character_by_key("Manny_Rig"))
RIG = maya_rigs.rigs()[0]
ROOT = RIG.skeleton_root
B = bones_of(RIG)

# ------------------------------------------------------------ two hands
print(equip.to_hand(ROOT, "R", SWORD))
print(equip.to_hand(ROOT, "L", DAGGER))
sword = attach.find_attached(B["hand_r"])
dagger = attach.find_attached(B["hand_l"])
gate(1, bool(sword) and bool(dagger)
     and weaponspace.hand_of(cmds.listRelatives(sword, parent=True, fullPath=True)[0]) == B["hand_r"]
     and weaponspace.hand_of(cmds.listRelatives(dagger, parent=True, fullPath=True)[0]) == B["hand_l"]
     and bonedrive.driving_weapon(B["weapon_r"]) == sword
     and bonedrive.driving_weapon(B["weapon_l"]) == dagger,
     "a sword in the right hand drives weapon_r, a dagger in the left drives weapon_l: %s / %s"
     % (sword, dagger))
held = equip.holdings(ROOT)
gate(2, held["R"].where == "hand" and held["R"].key == "LongSword_02"
     and held["L"].where == "hand" and held["L"].key == "Dagger_01",
     "the paper doll reads both hands: %s" % (dict((s, (h.where, h.key)) for s, h in held.items()),))

# ------------------------------------------------------------ the mirror
grips.remember("LongSword_02", "R", (10.0, -20.0, 35.0), (1.5, -2.0, 4.0))
print(equip.to_hand(ROOT, "R", SWORD))
name = grips.optionvar_name("LongSword_02", "L")
if cmds.optionVar(exists=name):
    cmds.optionVar(remove=name)
print(equip.to_hand(ROOT, "L", SWORD))
right = attach.find_attached(B["hand_r"])
left = attach.find_attached(B["hand_l"])
err = mirror_error(left, right)
gate(3, err < 2e-3, "Manny at build pose: the left sword against the world mirror of the right one "
     "(grip 10,-20,35 / 1.5,-2,4 on the right, the left undialled): %.2e" % err)
# the frame the node carries (2026-09-30: the socket turn composed in)
zero = bonedrive.mirror_grip((0, 0, 0), (0, 0, 0), bonedrive.socket_frame(SWORD.frame),
                             *grips.sockets(ROOT))
gate(4, abs(abs(zero[0][2]) - 180.0) < 5.0 or abs(abs(zero[0][0]) - 180.0) < 5.0
     or abs(abs(zero[0][1]) - 180.0) < 5.0,
     "Manny's zero right grip mirrors to a half turn on the left (the blade was backwards): %s"
     % (tuple(round(v, 3) for v in zero[0]),))

# ------------------------------------------------------------ the floor
socket_before = grips.socket_of(B["weapon_r"])
print(equip.to_floor(ROOT, SPEAR, (60.0, 0.0, 40.0), (1.0, 0.0, 0.0)))
spear = bonedrive.driving_weapon(B["weapon_r"])
low = lowest_point(spear) if spear else None
up = wm(spear) if spear else None
thick_up = (om.MVector(up[8], up[9], up[10]).normal().y) if spear else 0.0
# the bone on the weapon's SOCKET: its frame undone (2026-09-30: every node carries one)
socket = mdiff(unscaled(wm(B["weapon_r"])), om.MMatrix(bonedrive.matrix_of(
    bonedrive.frame_of(spear), (0, 0, 0))).inverse() * unscaled(wm(spear))) if spear else 9.0
gate(5, spear is not None and not attach.find_attached(B["hand_r"])
     and not cmds.listRelatives(spear, parent=True)
     and cmds.getAttr(spear + "." + attach.MARKER) == "Spear_01",
     "both hands taken: the spear REPLACED the right hand's sword and lies at world level: %s" % spear)
gate(6, low is not None and abs(low) < 1e-4 and thick_up > 0.9999,
     "lying flat: lowest vertex at y = %s, thickness axis up %.6f" % (low, thick_up))
gate(7, socket < 1e-4 and bonedrive.is_parked(spear) and equip.holdings(ROOT)["R"].where == "floor",
     "weapon_r stands on the spear's socket (%.1e), its track parked, the doll says floor" % socket)
socket_after = grips.socket_of(B["weapon_r"])
gate(14, mdiff(socket_before, socket_after) < 1e-6,
     "while weapon_r follows the floor spear its socket is still read from its OWN (parked) track "
     "(%.1e) - the mirror grip must not be computed from the floor (measured live: 134 cm off)"
     % mdiff(socket_before, socket_after))

# the exact round trip on the left bone: a known track, dropped, taken off
print(equip.take_off(ROOT, "L"))
wl = B["weapon_l"]
cmds.cutKey(wl, attribute=["tx", "ty", "tz", "rx", "ry", "rz"], clear=True)
base = [cmds.getAttr(wl + "." + a) for a in ("tx", "ty", "tz", "rx", "ry", "rz")]
for frame, delta in ((0, 0.0), (10, 3.0), (20, -2.0)):
    for attr, value in zip(("tx", "ty", "tz", "rx", "ry", "rz"), base):
        cmds.setKeyframe(wl, attribute=attr, time=frame, value=value + delta)
cmds.keyTangent(wl, attribute="ty", time=(10, 10), inTangentType="linear", outTangentType="step")
before = curves_of(wl)
print(equip.to_floor(ROOT, DAGGER, (-50.0, 0.0, 30.0), (0.0, 0.0, 1.0), "L"))
floor_dagger = bonedrive.driving_weapon(wl)
parked_ok = floor_dagger and bonedrive.is_parked(floor_dagger) and not cmds.listConnections(
    wl + ".translateY", type="animCurve")
print(equip.take_off(ROOT, "L"))
after = curves_of(wl)
gate(8, parked_ok and before == after and not bonedrive.driving_weapon(wl),
     "a dagger on the floor for the left hand parks weapon_l's own 3-key track and hands it back "
     "exactly - the same curve nodes, keys, values, tangents")

# ------------------------------------------------------------ a retarget
print(equip.to_hand(ROOT, "L", DAGGER))
dagger = attach.find_attached(B["hand_l"])
spear_before = wm(spear)
stored_dagger = bonedrive.stored_grip(dagger)
before = set(cmds.ls(type="joint", long=True))
cmds.namespace(add="clip")
cmds.namespace(set=":clip")
mel.eval('FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;')
mel.eval('FBXImport -f "%s";' % CLIP.replace("\\", "/"))
cmds.namespace(set=":")
new = [j for j in cmds.ls(type="joint", long=True) if j not in before]
src = min((j for j in new if not cmds.listRelatives(j, parent=True, type="joint")),
          key=lambda j: j.count("|"))
S = dict((p.split("|")[-1].split(":")[-1], p)
         for p in [src] + cmds.listRelatives(src, ad=True, type="joint", fullPath=True))
f0 = cmds.findKeyframe(list(S.values()), which="first")
f1 = cmds.findKeyframe(list(S.values()), which="last")
cmds.playbackOptions(min=f0, max=f1, animationStartTime=f0, animationEndTime=f1)
ok, text = rr.run_retarget(source_root=src, rig=RIG)
print(text)
spear = cmds.ls(spear, long=True)[0]
frames = list(range(int(f0), int(f1) + 1, max(1, int((f1 - f0) / 6))))
stay = park = grip = 0.0
for t in frames:
    cmds.currentTime(t)
    stay = max(stay, mdiff(wm(spear), spear_before))
    for channel in ("translateX", "translateY", "translateZ"):
        park = max(park, abs(cmds.getAttr(spear + "." + bonedrive.park_attr(channel))
                             - cmds.getAttr(S["weapon_r"] + "." + channel)))
    g = bonedrive.measured_grip(dagger, B["weapon_l"])
    grip = max(grip, max(abs(a - b) for a, b in zip(g[0] + g[1], stored_dagger[0] + stored_dagger[1])))
gate(9, ok and stay < 1e-6 and bonedrive.driving_weapon(B["weapon_r"]) == spear,
     "retargeted: the spear stays on the floor (%.1e) and weapon_r still follows it" % stay)
gate(10, bonedrive.is_parked(spear) and park < 5e-3,
     "the fresh clip's weapon_r track is what is parked on the spear now (%.1e cm)" % park)
gate(11, attach.find_attached(B["hand_l"]) == dagger and grip < 1e-3
     and bonedrive.driving_weapon(B["weapon_l"]) == dagger,
     "the dagger rides the carried weapon_l at its grip over the take (%.1e)" % grip)

# ------------------------------------------------------------ the export
path = os.path.join(tempfile.gettempdir(), "skeldar_inventory_export.fbx").replace("\\", "/")
animexport.export_hierarchy(path, root=ROOT)
expected = len(B)
cmds.file(new=True, force=True)
mel.eval('FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;')
mel.eval('FBXImport -f "%s";' % path)
joints = cmds.ls(type="joint", long=True)
meshes = cmds.ls(type="mesh", long=True)
gate(12, len(joints) == expected and not meshes,
     "the export with a sword, a dagger and a floor spear: %d joints of %d, %d meshes"
     % (len(joints), expected, len(meshes)))

# ------------------------------------------------------------ the Creep
cmds.file(new=True, force=True)
for side in ("R", "L"):
    name = grips.optionvar_name("Creep_Sword", side)
    if cmds.optionVar(exists=name):
        cmds.optionVar(remove=name)
character.add_character(catalog.character_by_key("Creep_Rig"))
CR = maya_rigs.rigs()[0]
CB = bones_of(CR)
creep_sword = catalog.by_key("Creep_Sword")
print(equip.to_hand(CR.skeleton_root, "R", creep_sword))
print(equip.to_hand(CR.skeleton_root, "L", creep_sword))
err = mirror_error(attach.find_attached(CB["hand_l"]), attach.find_attached(CB["hand_r"]))
zero = bonedrive.mirror_grip((0, 0, 0), (0, 0, 0), bonedrive.socket_frame(creep_sword.frame),
                             *grips.sockets(CR.skeleton_root))
turn = om.MEulerRotation(*[om.MAngle(v, om.MAngle.kDegrees).asRadians() for v in zero[0]]).asMatrix()
blade_kept = om.MVector(turn[4], turn[5], turn[6]) * om.MVector(0, 1, 0)
thick_kept = om.MVector(turn[8], turn[9], turn[10]) * om.MVector(0, 0, 1)
# 2026-09-30, one socket for every rig: the Creep's weapon_l is UE's now (the
# grip line along its -Z, as Manny's), so its zero grip mirrors as Manny's
# does (gate 04) - a half turn about the THICKNESS, the blade reversed by the
# left socket and put back by the grip. Before, its weapon_l held the grip
# line along +Y like weapon_r and the half turn was about the blade.
gate(13, err < 0.1 and blade_kept < -0.999 and thick_kept > 0.999
     and max(abs(v) for v in zero[1]) < 0.5,
     "the Creep (framed sword, its own weapon_l): left against the mirror of right %.2e; its zero "
     "grip mirrors to a half turn about the thickness as Manny's does (%s, blade %.4f, thickness "
     "%.4f)" % (err, tuple(round(v, 3) for v in zero[0]), blade_kept, thick_kept))
print("RESULT: %d of %d gates failed %s" % (len(FAILS), TOTAL[0], FAILS))
