"""Standalone gates: a PART portrait (Creep 2 Arm R / Head) dropped on a character keeps it.

    mayapy verify_part_drop.py <clip .fbx>

2026-10-27 («Для рига головы и руки крипа нужно сделать исключение ... старый скелет должен остаться»).
In a new scene: a Creep 2 rig retargeted with the clip and a Manny UE5 skeleton keyed by the same clip;
then `swap.swap` - what the portrait's drop calls - with each part row (rig and skeleton) onto each:

1. the character is still there, its keys and every game bone's world matrix as before;
2. the part arrived, and its top bone / the anchor stands where that body part of the character is,
   over the take (a Creep 2 is the arm's twin: every arm bone on the character's own to a hair);
3. the head turns as the character's head does.
"""
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
    except Exception:                                                   # noqa: BLE001
        pass
FAILS = []


def gate(n, ok, msg):
    print("%s %s: %s" % ("PASS" if ok else "FAIL", n, msg))
    if not ok:
        FAILS.append(n)


def wm(n, t=None):
    if t is None:
        return om.MMatrix(cmds.getAttr(n + ".worldMatrix[0]"))
    return om.MMatrix(cmds.getAttr(n + ".worldMatrix[0]", time=t))


def at(n, f):
    cmds.currentTime(f)
    return wm(n)


def pos(m):
    return om.MVector(m[12], m[13], m[14])


def ang(a, b):
    q = om.MTransformationMatrix(a).rotation(asQuaternion=True)
    r = om.MTransformationMatrix(b).rotation(asQuaternion=True)
    d = abs(q.x * r.x + q.y * r.y + q.z * r.z + q.w * r.w)
    import math
    return math.degrees(2 * math.acos(min(1.0, d)))


def bones_of(root):
    return dict((p.split("|")[-1].split(":")[-1], p)
                for p in [root] + (cmds.listRelatives(root, ad=True, type="joint", fullPath=True) or []))


from maya_scenesetup import catalog, character, swap  # noqa: E402
import maya_rigs  # noqa: E402
import maya_rig_retarget as rr  # noqa: E402
from maya_uebridge import skeletonimport  # noqa: E402

CLIP = sys.argv[1].replace("\\", "/")
cmds.file(new=True, force=True)
print(character.add_character(catalog.character_by_key("Creep2_Rig")).splitlines()[0])
print(character.add_character(catalog.character_by_key("Manny")).splitlines()[0])
creep = [r for r in maya_rigs.rigs() if r.namespace.startswith("Creep2_Rig")][0]
manny = [r for r in skeletonimport.bare_roots() if "Manny" in skeletonimport.skeleton_label(r)][0]

cmds.namespace(add="clip")
cmds.namespace(set=":clip")
mel.eval("FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;")
mel.eval('FBXImport -f "%s";' % CLIP)
cmds.namespace(set=":")
src = [j for j in cmds.ls("clip:*", type="joint", long=True) if not cmds.listRelatives(j, parent=True, type="joint")][0]
S = bones_of(src)
first = cmds.findKeyframe(list(S.values()), which="first")
last = cmds.findKeyframe(list(S.values()), which="last")
cmds.playbackOptions(min=first, max=last, animationStartTime=first, animationEndTime=last)
cmds.currentTime(first)
cmds.select(creep.main, src)
print("retarget:", rr.run_retarget()[1].splitlines()[0][:160])
print("onto Manny:", skeletonimport.transfer(src, manny, first, last))
cmds.namespace(removeNamespace=":clip", deleteNamespaceContent=True)
frames = [int(round(first + (last - first) * k / 6.0)) for k in range(7)]

for label, root in (("Creep2_Rig", creep.skeleton_root), ("Manny skeleton", manny)):
    B = bones_of(root)
    before = dict((n, [at(p, f) for f in frames]) for n, p in B.items())
    keys = len(cmds.keyframe(list(B.values()) + ([] if label != "Creep2_Rig" else
                                                cmds.sets(creep.control_set, q=True)), q=True) or [])
    for key, word in (("Creep2_ArmR_Rig", "hand_r"), ("Creep2_Head", "head"),
                      ("Creep2_Head_Rig", "head"), ("Creep2_ArmR", "hand_r")):
        rigs0 = set(r.namespace for r in maya_rigs.rigs())
        bare0 = set(skeletonimport.bare_roots())
        cmds.currentTime(first)
        line = swap.swap(catalog.character_by_key(key), root)
        print("   ", key, "->", line[:200])
        gate("1-%s-%s" % (label, key), cmds.objExists(root) and all(
            max(abs(a - b) for a, b in zip(list(m), list(at(B[n], f)))) < 1e-6
            for n in before for m, f in zip(before[n], frames)) and len(cmds.keyframe(
                list(B.values()), q=True) or []) <= keys and "kept" in line,
             "%s still there, every bone as before" % label)
        new = [r for r in maya_rigs.rigs() if r.namespace not in rigs0]
        newroot = new[0].skeleton_root if new else ([r for r in skeletonimport.bare_roots() if r not in bare0] or [None])[0]
        if not newroot:
            gate("2-%s-%s" % (label, key), False, "the part did not arrive")
            continue
        P = bones_of(newroot)
        off = max((pos(at(P[word], f)) - pos(at(B[word], f))).length() for f in frames)
        turn = max(ang(at(B[word], frames[0]).inverse() * at(B[word], f),
                       at(P[word], frames[0]).inverse() * at(P[word], f)) for f in frames)
        twin = label == "Creep2_Rig"
        gate("2-%s-%s" % (label, key), (off < 0.2 if twin else off < 15.0) and turn < 0.5,
             "%s stands on the character's to %.3f cm, turns as it to %.3f deg" % (word, off, turn))

print("\n%d failed: %s" % (len(FAILS), FAILS) if FAILS else "\nall gates passed")
