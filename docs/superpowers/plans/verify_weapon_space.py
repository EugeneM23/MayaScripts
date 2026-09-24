"""Standalone gates: the weapon lives OUTSIDE the skeleton, and the export writes bones only (2026-09-24).

    mayapy verify_weapon_space.py <UE5 clip .fbx>

The animator: «давай делать всё максимально правильно, так чтобы мы не нарушали иерархию нашего
скелета». An empty scene, a Hunter rig and a Manny rig (Add Character), a weapon on each (Weapons >
Add's own function), the clip retargeted onto both, both exported through the bridge's exporter
and the files read back. Plus the two old shapes: a sword a file from before holds directly
under the hand (still found, still comes off) and a mesh somebody parented under a bone by hand
(still kept out of the export). mayapy STANDALONE: it adds rigs and deletes things.
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
CLIP = sys.argv[1]
FAILS = []


def gate(n, ok, msg):
    print("%s gate %02d: %s" % ("PASS" if ok else "FAIL", n, msg))
    if not ok:
        FAILS.append(n)


def wm(n):
    return om.MMatrix(cmds.getAttr(n + ".worldMatrix[0]"))


def mdiff(a, b):
    return max(abs(x - y) for x, y in zip(list(a), list(b)))


def not_bones(root):
    return [n.split("|")[-1] for n in cmds.listRelatives(root, allDescendents=True, fullPath=True) or []
            if cmds.objectType(n) != "joint" and not cmds.objectType(n, isAType="constraint")]


cmds.file(new=True, force=True)
from maya_scenesetup import attach, bonedrive, catalog, character, skeleton, weaponspace
from maya_uebridge import animexport
import maya_rigs, maya_rig_retarget as rr

character.add_character(catalog.character_by_key("Hunter_Rig"))
character.add_character(catalog.character_by_key("Manny_Rig"))
rigs = dict((r.namespace, r) for r in maya_rigs.rigs())
H_RIG, M_RIG = rigs["Hunter_Rig"], rigs["Manny_Rig"]


def bones(rig):
    return dict((p.split("|")[-1].split(":")[-1], p) for p in [rig.skeleton_root] + cmds.listRelatives(rig.skeleton_root, ad=True, type="joint", fullPath=True))


H, M = bones(H_RIG), bones(M_RIG)
hs, _ = attach.attach(catalog.by_key("Hunter_Sword"), H["hand_r"], H["weapon_r"], (0, 0, 0), (0, 0, 0))
ms, _ = attach.attach(catalog.by_key("LongSword_02"), M["hand_r"], M["weapon_r"], (0, 0, 0), (0, 0, 0))
hs, ms = cmds.ls(hs, long=True)[0], cmds.ls(ms, long=True)[0]
hspace, mspace = [cmds.listRelatives(w, parent=True, fullPath=True)[0] for w in (hs, ms)]
gate(1, weaponspace.is_space(hspace) and weaponspace.is_space(mspace)
     and weaponspace.hand_of(hspace) == H["hand_r"] and weaponspace.hand_of(mspace) == M["hand_r"],
     "each sword is the child of its hand's SPACE: %s, %s" % (hspace, mspace))
gate(2, hspace.startswith(H_RIG.group + "|") and mspace.startswith(M_RIG.group + "|")
     and not hspace.startswith(H_RIG.skeleton_root) and not mspace.startswith(M_RIG.skeleton_root),
     "the spaces stand in each rig's own group, outside its skeleton")
gate(3, not not_bones(H_RIG.skeleton_root) and not not_bones(M_RIG.skeleton_root),
     "both skeletons hold bones and constraints only: %s / %s" % (not_bones(H_RIG.skeleton_root), not_bones(M_RIG.skeleton_root)))
gate(4, bonedrive.driving_weapon(H["weapon_r"]) == hs and bonedrive.driving_weapon(M["weapon_r"]) == ms
     and mdiff(wm(hs), wm(H["weapon_r"])) < 1e-4 and mdiff(wm(ms), wm(M["weapon_r"])) < 1e-4,
     "each sword drives its weapon_r and sits on it at zero grip (%.1e, %.1e)" % (mdiff(wm(hs), wm(H["weapon_r"])), mdiff(wm(ms), wm(M["weapon_r"]))))
cmds.setAttr(maya_rigs.node(H_RIG, "FKShoulder_R") + ".rotateZ", 40)
follow = mdiff(wm(hspace), wm(H["hand_r"]))
on_bone = mdiff(wm(hs), wm(H["weapon_r"]))
cmds.setAttr(maya_rigs.node(H_RIG, "FKShoulder_R") + ".rotateZ", 0)
gate(5, follow < 1e-4 and on_bone < 1e-4, "posed: the space stays on the hand (%.1e) and the sword on the bone (%.1e)" % (follow, on_bone))
cmds.select(hs, replace=True)
picked = skeleton.current_root()
gate(6, picked == H_RIG.skeleton_root, "selecting the Hunter's sword names the Hunter: %s" % picked)
cmds.select(clear=True)

# the clip onto both rigs
before = set(cmds.ls(type="joint", long=True))
cmds.namespace(add="clip"); cmds.namespace(set=":clip")
mel.eval('FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;')
mel.eval('FBXImport -f "%s";' % CLIP.replace("\\", "/"))
cmds.namespace(set=":")
new = [j for j in cmds.ls(type="joint", long=True) if j not in before]
src = min((j for j in new if not cmds.listRelatives(j, parent=True, type="joint")), key=lambda j: j.count("|"))
S = dict((p.split("|")[-1].split(":")[-1], p) for p in [src] + cmds.listRelatives(src, ad=True, type="joint", fullPath=True))
f0, f1 = cmds.findKeyframe(list(S.values()), which="first"), cmds.findKeyframe(list(S.values()), which="last")
cmds.playbackOptions(min=f0, max=f1, animationStartTime=f0, animationEndTime=f1)
ok_h, _ = rr.run_retarget(source_root=src, rig=H_RIG)
ok_m, _ = rr.run_retarget(source_root=src, rig=M_RIG)
hs, ms = cmds.ls(hs, long=True)[0], cmds.ls(ms, long=True)[0]
frames = list(range(int(f0), int(f1) + 1, max(1, int((f1 - f0) / 8))))
grip_h = grip_m = 0.0
for t in frames:
    cmds.currentTime(t)
    grip_h = max(grip_h, mdiff(wm(hs), wm(H["weapon_r"])))
    grip_m = max(grip_m, mdiff(wm(ms), wm(M["weapon_r"])))
gate(7, ok_h and ok_m and grip_h < 1e-3 and grip_m < 1e-3 and weaponspace.is_space(cmds.listRelatives(hs, parent=True, fullPath=True)[0])
     and not not_bones(H_RIG.skeleton_root) and not not_bones(M_RIG.skeleton_root),
     "both retargeted; each sword rides its weapon_r over the take (%.1e, %.1e), still in its space, the skeletons still bones only" % (grip_h, grip_m))
track = {}
for t in frames:
    cmds.currentTime(t)
    track[t] = wm(H["weapon_r"]) * wm(H["hand_r"]).inverse()      # matrices: an euler read comes back 360 off (trap 31)

# a mesh parented under a bone by hand -- the export must keep it out too
stray = cmds.polyCube(name="strayUnderBone")[0]
stray = cmds.parent(stray, M["hand_l"])[0]


def exported(rig, name):
    path = os.path.join(tempfile.gettempdir(), name).replace("\\", "/")
    info = animexport.export_hierarchy(path, root=rig.skeleton_root)
    return path, info


h_fbx, h_info = exported(H_RIG, "skeldar_weapon_space_hunter.fbx")
m_fbx, m_info = exported(M_RIG, "skeldar_weapon_space_manny.fbx")


def read_back(path):
    cmds.file(new=True, force=True)
    mel.eval('FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;')
    mel.eval('FBXImport -f "%s";' % path)
    joints = cmds.ls(type="joint", long=True)
    meshes = [m for m in cmds.ls(type="mesh", long=True)]
    return joints, meshes


# keep what the scene needs before it goes
h_joints_expected, m_joints_expected = len(H), len(M)
hj, hm = read_back(h_fbx)
wr = [j for j in hj if j.endswith("|weapon_r")]
hr = [j for j in hj if j.endswith("|hand_r")]
kept = 0.0
if wr and hr:
    for t in frames:
        cmds.currentTime(t)
        kept = max(kept, mdiff(wm(wr[0]) * wm(hr[0]).inverse(), track[t]))
gate(8, len(hj) == h_joints_expected and not hm and wr and kept < 1e-2,
     "the Hunter's FBX: %d joints, %d meshes; its weapon_r carries the sword's track to %.4f" % (len(hj), len(hm), kept))
mj, mm = read_back(m_fbx)
gate(9, len(mj) == m_joints_expected and not mm,
     "the Manny's FBX, with a stray cube parented under hand_l by hand: %d joints, %d meshes %s" % (len(mj), len(mm), mm[:2]))

# Remove, and the old shape
cmds.file(new=True, force=True)
character.add_character(catalog.character_by_key("Manny_Rig"))
rig = maya_rigs.rigs()[0]
B = bones(rig)
w, _ = attach.attach(catalog.by_key("LongSword_02"), B["hand_r"], B["weapon_r"], (0, 0, 0), (0, 0, 0))
space = cmds.listRelatives(w, parent=True, fullPath=True)[0]
group = cmds.listRelatives(space, parent=True, fullPath=True)[0]
removed = attach.detach(B["hand_r"], B["weapon_r"])
gate(10, removed and not cmds.objExists(space) and not cmds.objExists(group) and not bonedrive.driving_weapon(B["weapon_r"]),
     "Remove Weapon: the sword, its emptied space and the emptied WeaponSpaces group all gone")
legacy = cmds.polyCube(name="oldSword")[0]
legacy = cmds.ls(cmds.parent(legacy, B["hand_r"])[0], long=True)[0]
cmds.addAttr(legacy, longName=bonedrive.MARKER, dataType="string")
cmds.setAttr(legacy + "." + bonedrive.MARKER, "LongSword_02", type="string")
bonedrive.snap(legacy, B["weapon_r"])
bonedrive.link(legacy, B["weapon_r"])
found = attach.find_attached(B["hand_r"])
removed = attach.detach(B["hand_r"], B["weapon_r"])
gate(11, found == legacy and removed == legacy and not cmds.objExists(legacy) and not bonedrive.driving_weapon(B["weapon_r"]),
     "a sword a file from before holds UNDER the hand is still found and still comes off")
print("RESULT: %d of 11 gates failed %s" % (len(FAILS), FAILS))
