"""Standalone gates for the shipped Orc rig (assets/Orc_Rig.ma) going through the plugin.

    mayapy verify_orc_rig_asset.py <UE5 clip .fbx> <scratch dir>

mayapy STANDALONE, an empty scene (2026-09-25).  `verify_creep_rig_asset.py` for the orc: Add
Character twice with "Orc [rig]" and once with "Manny [rig]", then a UE5 clip retargeted onto the
FIRST orc through the Retarget button's own function.  Gates: each orc in its own `Orc_Rig`
namespace, found by `maya_rigs` with its rotation-only mark, tagged with its catalog key, at its
bind with its controls at default, painted, its blendShape and helper bones there, no script
node; the retarget copies the source's orientations and keeps the orc's bone lengths; the second
orc and the Manny do not move; the shoulder pads ride their clavicles through the take.  And the
tools Manny's helper bones exist for (the animator: «все четыре»): the catalog's Long Sword added
at zero grip sits on weapon_r and drives it, the retarget carries the clip's weapon_r relative to
the hand with the sword riding it, Remove Weapon hands the bone its track back; the retarget's
camera stands on camera_root, which follows the clip's; and the export writes 95 bones and no
mesh, under a Null named for the character.
"""
import math
import os
import sys

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
CLIP = sys.argv[1].replace("\\", "/")
SCRATCH = sys.argv[2].replace("\\", "/")
FAILS = []
TOTAL = 16


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


def mdiff(a, b):
    return max(abs(x - y) for x, y in zip(list(a), list(b)))


def rel(bone, parent):
    return wm(bone) * wm(parent).inverse()


cmds.file(new=True, force=True)
from maya_scenesetup import catalog, character, attach, bonedrive, weaponspace, camera
import maya_rigs, maya_asretarget as ar, maya_rig_retarget as rr

orc = catalog.character_by_key("Orc_Rig")
gate(1, orc is not None and orc.label in catalog.character_labels() and catalog.is_rig(orc),
     "the dropdown offers %s" % catalog.character_labels())
texts = [character.add_character(orc), character.add_character(orc), character.add_character(catalog.character_by_key("Manny_Rig"))]
for t in texts:
    print("   ", t.splitlines()[0])
rigs = dict((r.namespace, r) for r in maya_rigs.rigs())
gate(2, set(rigs) == {"Orc_Rig", "Orc_Rig1", "Manny_Rig"}, "three rigs, each in its own namespace: %s" % sorted(rigs))
o, o2, manny = rigs.get("Orc_Rig"), rigs.get("Orc_Rig1"), rigs.get("Manny_Rig")
gate(3, ar.rotation_mode(o) and ar.rotation_mode(o2) and not ar.rotation_mode(manny),
     "rotation-only mark: Orc %s, Orc1 %s, Manny %s" % (ar.rotation_mode(o), ar.rotation_mode(o2), ar.rotation_mode(manny)))


def bones(rig):
    return dict((p.split("|")[-1].split(":")[-1], p)
                for p in [rig.skeleton_root] + cmds.listRelatives(rig.skeleton_root, ad=True, type="joint", fullPath=True))


O, O2, M = bones(o), bones(o2), bones(manny)
tag = cmds.getAttr(o.skeleton_root + ".skeldarCharacter") if cmds.attributeQuery("skeldarCharacter", node=o.skeleton_root, exists=True) else None
#  Blender's Auto-Rig Pro properties came through Unreal on the joints and rode into every export
#  until make_orc_source deleted them; what may stay is Maya's own and our tag
foreign = sorted(set(a for p in O.values() for a in cmds.listAttr(p, userDefined=True) or []
                     if a not in ("filmboxTypeID", "lockInfluenceWeights", "skeldarCharacter")))
gate(4, o.skeleton_root == "|Orc_Rig:root" and len(O) == 95
     and all(n in O for n in ("weapon_r", "weapon_l", "camera_root", "camera_bone", "AB_Armor_Shoulder_L", "AB_Armor_Shoulder_R"))
     and tag in (None, "Orc_Rig") and not foreign,
     "the orc's skeleton at world level: %s, %d joints, helper bones and shoulder pads there, tagged %r, foreign attributes %s"
     % (o.skeleton_root, len(O), tag, foreign))
scripts = [s for s in cmds.ls(type="script") if s.startswith("Orc_Rig")]
gate(5, not scripts, "script nodes the orc asset brought: %s" % scripts)
worst, skins = 0.0, []
for sc in cmds.ls(type="skinCluster"):
    if not sc.startswith("Orc_Rig:"):
        continue
    skins.append(sc)
    for idx in cmds.getAttr(sc + ".matrix", multiIndices=True) or []:
        src = cmds.listConnections("%s.matrix[%d]" % (sc, idx), s=True, d=False)
        if src:
            worst = max(worst, mdiff(om.MMatrix(cmds.getAttr("%s.bindPreMatrix[%d]" % (sc, idx))) * wm(src[0]), om.MMatrix()))
off = ar.posed_controls(rig=o)
gate(6, len(skins) == 1 and worst < 1e-4 and not off,
     "%d orc skin at its bind (|BPM*WM - I| %.2e), controls at default %s" % (len(skins), worst, off[:4]))
geo = cmds.listRelatives("|Orc_Rig:Group|Orc_Rig:Geometry", children=True) or []
shape = [m for m in cmds.ls("Orc_Rig:Orc_BodyShape", type="mesh") if not cmds.getAttr(m + ".intermediateObject")]
colours = set()
for m in shape:
    for sg in cmds.listConnections(m, type="shadingEngine") or []:
        colours.update(x for x in cmds.ls(cmds.listConnections(sg + ".surfaceShader", s=True, d=False) or [], materials=True)
                       if cmds.attributeQuery("skeldarColour", node=x, exists=True))
bs = [b for b in cmds.ls(type="blendShape") if b.startswith("Orc_Rig:")]
gate(7, geo == ["Orc_Rig:Orc_Body"] and len(shape) == 1 and len(colours) == 1 and len(bs) == 1
     and len(cmds.blendShape(bs[0], q=True, weight=True)) == 56,
     "Geometry %s painted with %s; blendShape %s with %d targets"
     % (geo, sorted(colours), bs, len(cmds.blendShape(bs[0], q=True, weight=True)) if bs else 0))

# the clip, in its own namespace
before = set(cmds.ls(type="joint", long=True))
cmds.namespace(add="clip"); cmds.namespace(set=":clip")
mel.eval('FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;')
mel.eval('FBXImport -f "%s";' % CLIP)
cmds.namespace(set=":")
new = [j for j in cmds.ls(type="joint", long=True) if j not in before]
src = min((j for j in new if not cmds.listRelatives(j, parent=True, type="joint")), key=lambda j: j.count("|"))
S = dict((p.split("|")[-1].split(":")[-1], p) for p in [src] + cmds.listRelatives(src, ad=True, type="joint", fullPath=True))
first, last = cmds.findKeyframe(list(S.values()), which="first"), cmds.findKeyframe(list(S.values()), which="last")
cmds.playbackOptions(min=first, max=last, animationStartTime=first, animationEndTime=last)
print("    clip %s: %d joints, frames %s..%s, weapon_r %s, camera_root %s"
      % (os.path.basename(CLIP), len(S), first, last, "weapon_r" in S, "camera_root" in S))
# No clip on this disk moves weapon_r in the hand or camera_root at all (measured on five), and a
# gate about carrying them would pass on a bone that stands still.  So the clip's own copy gets a
# move of each at mid-take: weapon_r turned 25 deg in the hand, camera_root 20 cm up and 15 deg round.
mid = float(int((first + last) / 2))
for bone, plug, delta in (("weapon_r", "rotateZ", 25.0), ("camera_root", "translateZ", 20.0), ("camera_root", "rotateY", 15.0)):
    if bone in S:
        p = S[bone] + "." + plug
        for t in (first, last):
            cmds.setKeyframe(p, time=t, value=cmds.getAttr(p, time=t))
        cmds.setKeyframe(p, time=mid, value=cmds.getAttr(p, time=mid) + delta)
rest_t = dict((n, cmds.getAttr(p + ".translate")[0]) for n, p in O.items())
pads = dict((s, rel(O["AB_Armor_Shoulder_" + s], O["clavicle_" + s.lower()])) for s in "LR")
still = dict((p, wm(p)) for p in list(O2.values()) + list(M.values()))

# the catalog's Long Sword on the orc, as on Manny: Add at zero grip, before the take
sword = catalog.by_key("LongSword_02")
cmds.currentTime(first)
weapon, wnote = attach.attach(sword, O["hand_r"], O["weapon_r"], (0, 0, 0), (0, 0, 0))
weapon = cmds.ls(weapon, long=True)[0]
FRAME = om.MMatrix(bonedrive.matrix_of(sword.frame, (0, 0, 0)))
seat = mdiff(wm(weapon), FRAME * wm(O["weapon_r"]))
gate(8, weaponspace.holding_hand(weapon) == O["hand_r"] and not weapon.startswith(O["root"] + "|")
     and bonedrive.driving_weapon(O["weapon_r"]) and seat < 1e-4,
     "Add 'Long Sword 02': %s in hand_r's space drives weapon_r, on the bone to %.2e at zero grip %s"
     % (weapon.split("|")[-1], seat, wnote))

cmds.select(cmds.ls("Orc_Rig:Main")[0], src)
ok, text = rr.run_retarget()
print("   ", text.splitlines()[0][:240])
gate(9, ok and "ROTATIONS ONLY" in text and not cmds.objExists(ar.holder_of(o)), "the button, with an orc control and the clip selected: ok=%s" % ok)
frames = list(range(int(first), int(last) + 1, max(1, int((last - first) / 10))))
def direction(bone, child, B):
    return (om.MVector(cmds.xform(B[child], q=True, ws=True, t=True)) - om.MVector(cmds.xform(B[bone], q=True, ws=True, t=True))).normal()


worst_rot, worst_len, moved, worst_pad, worst_dir = (0.0, ""), 0.0, 0.0, 0.0, (0.0, "")
for t in frames:
    cmds.currentTime(t)
    for b in ("pelvis", "spine_03", "spine_05", "neck_01", "head", "clavicle_l", "hand_l", "hand_r", "foot_l", "ball_r", "middle_02_r"):
        if b in S:                     # a 3P clip may carry fewer bones (this one: no neck_01)
            worst_rot = max(worst_rot, (ang(rot(wm(S[b])), rot(wm(O[b]))), b))
    # AdvancedSkeleton's Shoulder/Elbow/Hip/Knee never roll -- the roll lives in the twist joints --
    # so the limb bones are judged by where they POINT (the Creep's rule, CLAUDE.md)
    for b, c in (("upperarm_r", "lowerarm_r"), ("lowerarm_l", "hand_l"), ("thigh_l", "calf_l"), ("calf_r", "foot_r")):
        if b not in S or c not in S:
            continue
        a = math.degrees(direction(b, c, S).angle(direction(b, c, O)))
        worst_dir = max(worst_dir, (a, b))
    for n, p in O.items():
        if n not in ("root", "pelvis", "weapon_r", "weapon_l", "camera_root", "camera_bone") and not n.startswith("ik_"):
            worst_len = max(worst_len, (om.MVector(cmds.getAttr(p + ".translate")[0]) - om.MVector(rest_t[n])).length())
    moved = max(moved, max(mdiff(m, wm(p)) for p, m in still.items()))
    worst_pad = max(worst_pad, max(mdiff(rel(O["AB_Armor_Shoulder_" + s], O["clavicle_" + s.lower()]), pads[s]) for s in "LR"))
gate(10, worst_rot[0] < 0.05 and worst_dir[0] < 0.5 and worst_len < 1e-3,
     "the orc on the clip's orientations to %.5f deg (%s), limb bones pointing as the clip's to %.4f deg (%s), "
     "its bone lengths kept to %.6f cm" % (worst_rot[0], worst_rot[1], worst_dir[0], worst_dir[1], worst_len))
gate(11, moved < 1e-6, "the second orc and the Manny did not move: %.9f" % moved)
gate(12, worst_pad < 1e-6, "the shoulder pads rode their clavicles through the take to %.2e" % worst_pad)

# weapon_r took the clip's grip RELATIVE TO THE HAND, the sword riding it
has_src = "weapon_r" in S
worst_rel, worst_grip, track = 0.0, 0.0, {}
for t in frames:
    cmds.currentTime(t)
    if has_src:
        worst_rel = max(worst_rel, mdiff(rel(O["weapon_r"], O["hand_r"]), rel(S["weapon_r"], S["hand_r"])))
    worst_grip = max(worst_grip, mdiff(wm(weapon), FRAME * wm(O["weapon_r"])))
    track[t] = rel(O["weapon_r"], O["hand_r"])
motion = max(mdiff(track[frames[0]], m) for m in track.values())
gate(13, has_src and motion > 0.1 and worst_rel < 1e-3 and worst_grip < 1e-3 and bonedrive.driving_weapon(O["weapon_r"]),
     "weapon_r on the clip's weapon_r relative to the hand to %.2e (it moves %.2f in the hand); the sword on it to %.2e"
     % (worst_rel, motion, worst_grip))

# the retarget's camera, on camera_root, which follows the clip's
cam = camera.camera_for(O["camera_root"])
worst_cam, worst_croot, croot_moves = 0.0, 0.0, 0.0
croot0 = None
offset = camera.rotation_only(camera.AXIS_OFFSET)
for t in frames:
    cmds.currentTime(t)
    if cam:
        worst_cam = max(worst_cam, mdiff(wm(cam), om.MMatrix(camera.placed_matrix(list(wm(O["camera_root"])), offset))))
    if "camera_root" in S:
        worst_croot = max(worst_croot, mdiff(rel(O["camera_root"], O["root"]), rel(S["camera_root"], S["root"])))
        croot0 = rel(O["camera_root"], O["root"]) if croot0 is None else croot0
        croot_moves = max(croot_moves, mdiff(croot0, rel(O["camera_root"], O["root"])))
gate(14, cam is not None and cam.split("|")[-1] == "Orc_Rig:SceneSetup_camera" and worst_cam < 1e-3 and worst_croot < 1e-3 and croot_moves > 1.0,
     "camera %s drives camera_root, in the bone's transform to %.2e; camera_root on the clip's (relative to root) to %.2e while moving %.2f"
     % (cam, worst_cam, worst_croot, croot_moves))

# Remove Weapon: the bone takes its animation back and the sword goes
removed = attach.detach(O["hand_r"], O["weapon_r"])
back = 0.0
for t in frames:
    cmds.currentTime(t)
    back = max(back, mdiff(rel(O["weapon_r"], O["hand_r"]), track[t]))
gate(15, not cmds.objExists(weapon) and not bonedrive.driving_weapon(O["weapon_r"]) and back < 1e-3,
     "Remove Weapon %s: the sword gone, weapon_r free and keyed on its own track to %.2e" % (removed, back))

# the export: bones only, 95 of them, under a Null named for the character
from maya_uebridge import animexport
fbx = SCRATCH + "/orc_export_check.fbx"
if os.path.exists(fbx):
    os.remove(fbx)
result = animexport.export_hierarchy(fbx, root=O["root"], start=first, end=last)
print("    export:", str(result)[:240])
before = set(cmds.ls(long=True))
cmds.namespace(add="chk"); cmds.namespace(set=":chk")
mel.eval('FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;')
mel.eval('FBXImport -f "%s";' % fbx)
cmds.namespace(set=":")
back_in = [n for n in cmds.ls(long=True) if n not in before]
j_in = [n for n in back_in if cmds.nodeType(n) == "joint"]
m_in = [n for n in back_in if cmds.nodeType(n) == "mesh"]
tops = sorted(set(n.split("|")[1] for n in back_in if n.startswith("|chk:")))
gate(16, len(j_in) == 95 and not m_in and (tops == ["chk:Orc"] or tops == ["chk:root"]),
     "the FBX read back: %d joints, %d meshes, top node(s) %s" % (len(j_in), len(m_in), tops))
print("RESULT: %d of %d gates failed %s" % (len(FAILS), TOTAL, FAILS))
