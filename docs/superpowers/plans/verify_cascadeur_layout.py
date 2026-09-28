"""Standalone gates for exporting in Cascadeur's layout (2026-09-25).

    mayapy verify_cascadeur_layout.py <a Cascadeur clip of the Creep, e.g. Downloads/creep_attack_forward.fbx>

mayapy STANDALONE: it adds rigs and skeletons and exports files.
- A Cascadeur clip retargeted onto a fresh Creep_Rig and exported through the bridge's own
  export (`animexport.export_hierarchy`). The file then carries Cascadeur's layout: a Null
  `Armature` at -90 X (one name for every character since 2026-09-25's evening) over a `root`
  with no orientation, whose LOCAL values equal the ones in Cascadeur's own file of the same clip.
- The same for a bare keyed skeleton (a node of the animator's called `Armature` held aside
  meanwhile), a static one and a Manny rig.
- A root the layout cannot move without editing keys (a pairBlend) falls back to the plain
  file with a note; `layout="plain"` writes the old file.
- Every case leaves the scene exactly as it found it.

Spec: docs/superpowers/specs/2026-09-25-cascadeur-export-layout-design.md
"""
import math
import os
import sys
import tempfile

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

sys.path.insert(0, "C:/!!!Work/MayaScripts/SkeldarAnim")
for p in ("fbxmaya", "matrixNodes", "quatNodes"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass
from maya_scenesetup import catalog, character
from maya_uebridge import animexport, animimport
import maya_rigs
import maya_rig_retarget as rr

CLIP = sys.argv[1].replace("\\", "/")
OUT = tempfile.mkdtemp(prefix="cascadeur_layout_").replace("\\", "/")
FAILS = []


def gate(n, ok, msg):
    print("%s gate %02d: %s" % ("PASS" if ok else "FAIL", n, msg))
    if not ok:
        FAILS.append(n)


def wm(n):
    return om.MMatrix(cmds.getAttr(n + ".worldMatrix[0]"))


def lm(n):
    return om.MMatrix(cmds.getAttr(n + ".matrix"))


def ang(a, b):
    qa = om.MTransformationMatrix(a).rotation(asQuaternion=True)
    qb = om.MTransformationMatrix(b).rotation(asQuaternion=True)
    q = qa.inverse() * qb
    return math.degrees(2 * math.acos(max(-1.0, min(1.0, abs(q.w)))))


def pos(m):
    return om.MVector(m.getElement(3, 0), m.getElement(3, 1), m.getElement(3, 2))


def mdiff(a, b):
    return max(abs(x - y) for x, y in zip(list(a), list(b)))


def bones(root):
    return dict((p.split("|")[-1].split(":")[-1], p)
                for p in [root] + (cmds.listRelatives(root, ad=True, type="joint", fullPath=True) or []))


def fresh():
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")


def snapshot(root, frames):
    """What an export must leave exactly as it was."""
    uuid = cmds.ls(root, uuid=True)[0]
    worlds = []
    for t in frames:
        cmds.currentTime(t)
        worlds.append(wm(root))
    return {"uuid": uuid, "worlds": worlds,
            "nodes": set(cmds.ls(cmds.ls(), uuid=True)),
            "conns": sorted(cmds.listConnections(root, source=True, destination=False, plugs=True,
                                                 connections=True) or []),
            "jo": tuple(cmds.getAttr(root + ".jointOrient")[0]),
            "parent": cmds.listRelatives(root, parent=True),
            "names": sorted(cmds.ls(long=True) or [])}


def restored(before, frames):
    root = cmds.ls(before["uuid"], long=True)[0]
    worst = 0.0
    for t, w in zip(frames, before["worlds"]):
        cmds.currentTime(t)
        worst = max(worst, mdiff(wm(root), w))
    now = set(cmds.ls(cmds.ls(), uuid=True))
    conns = sorted(cmds.listConnections(root, source=True, destination=False, plugs=True,
                                        connections=True) or [])
    same = (worst < 1e-9 and now == before["nodes"] and conns == before["conns"]
            and tuple(cmds.getAttr(root + ".jointOrient")[0]) == before["jo"]
            and cmds.listRelatives(root, parent=True) == before["parent"]
            and sorted(cmds.ls(long=True) or []) == before["names"])
    return same, ("root world %.1e, nodes %+d/-%d, connections %s, jointOrient %s, parent %s, names %s"
                  % (worst, len(now - before["nodes"]), len(before["nodes"] - now),
                     "same" if conns == before["conns"] else "CHANGED",
                     "same" if tuple(cmds.getAttr(root + ".jointOrient")[0]) == before["jo"] else "CHANGED",
                     cmds.listRelatives(root, parent=True),
                     "same" if sorted(cmds.ls(long=True) or []) == before["names"] else "CHANGED"))


def read(path, namespace):
    """An FBX into its own namespace, the importer's way; returns its root."""
    cmds.namespace(add=namespace)
    cmds.namespace(set=":" + namespace)
    try:
        mel.eval("FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;")
        mel.eval('FBXImport -f "%s";' % path)
    finally:
        cmds.namespace(set=":")
    return cmds.ls(namespace + ":root", type="joint", long=True)[0]


def export(root, name, **kwargs):
    path = "%s/%s.fbx" % (OUT, name)
    cmds.select(clear=True)
    return path, animexport.export_hierarchy(path, root=root, **kwargs)


# ------------------------------------------------ A: the Creep rig on a Cascadeur clip
fresh()
print(character.add_character(catalog.character_by_key("Creep_Rig")))
rig = maya_rigs.find("Creep_Rig")
animimport.import_clip(CLIP, namespace="casc", merge=False)
src = cmds.ls("casc:root", type="joint", long=True)[0]
first, last = cmds.playbackOptions(q=True, min=True), cmds.playbackOptions(q=True, max=True)
cmds.select(cmds.ls("Creep_Rig:Main")[0], src)
ok, text = rr.run_retarget()
print("retarget:", ok, text.splitlines()[0][:120])
frames = list(range(int(first), int(last) + 1, 3))
root = rig.skeleton_root
# a root tagged by the one day's build that wrote the tag (2026-09-25): held out of the file, put back
cmds.addAttr(root, longName="skeldarCharacter", dataType="string")
cmds.setAttr(root + ".skeldarCharacter", "Creep_Rig", type="string")
before = snapshot(root, frames)
path_a, info = export(root, "creep_rig")
tag_in_file = b"skeldarCharacter" in open(path_a, "rb").read()
gate(1, info["layout"] == "cascadeur" and info["wrapper"] == "Armature" and not info["notes"] and not tag_in_file
     and cmds.attributeQuery("skeldarCharacter", node=root, exists=True),
     "Creep_Rig on the Cascadeur clip exported in Cascadeur's layout, wrapper %r, notes %s; our tag in the file: %s, "
     "back on the root: %s" % (info["wrapper"], info["notes"], tag_in_file,
                               cmds.attributeQuery("skeldarCharacter", node=root, exists=True)))
same, text = restored(before, frames)
gate(4, same, "the scene after the export: " + text)

fresh()
a_root = read(CLIP, "A")            # Cascadeur's own file
b_root = read(path_a, "B")          # ours
wrapper = cmds.listRelatives(b_root, parent=True, fullPath=True) or [None]
A, B = bones(a_root), bones(b_root)
worst_t = worst_r = 0.0
worst_bone = worst_limb = 0.0
LIMB = ("upperarm", "lowerarm", "thigh", "calf")
for t in frames:
    cmds.currentTime(t)
    la, lb = lm(A["root"]), lm(B["root"])
    worst_t = max(worst_t, (pos(la) - pos(lb)).length())
    worst_r = max(worst_r, ang(la, lb))
    for n, pa in A.items():
        if n not in B or n == "root" or n.startswith("ik_") or "twist" in n:
            continue
        if any(n.startswith(l + "_") for l in LIMB):
            kids = [c for c in (cmds.listRelatives(pa, children=True, type="joint", fullPath=True) or [])
                    if "twist" not in c]
            if kids:
                k = kids[0].split("|")[-1].split(":")[-1]
                da = (pos(wm(A[k])) - pos(wm(pa))).normal()
                db = (pos(wm(B[k])) - pos(wm(B[n]))).normal()
                worst_limb = max(worst_limb, math.degrees(da.angle(db)))
        else:
            worst_bone = max(worst_bone, ang(wm(pa), wm(B[n])))
gate(2, wrapper[0] == "|B:Armature" and mdiff(lm(wrapper[0]) if wrapper[0] else om.MMatrix(),
                                           om.MEulerRotation(math.radians(-90), 0, 0).asMatrix()) < 1e-9
     and max(abs(v) for v in cmds.getAttr(b_root + ".jointOrient")[0]) < 1e-3
     and worst_t < 1e-3 and worst_r < 0.01,
     "the file: root under %s at -90 X, root jointOrient %s; root LOCAL against Cascadeur's own file: "
     "translation %.2e cm, rotation %.4f deg over %d frames"
     % (wrapper[0], [round(v, 4) for v in cmds.getAttr(b_root + ".jointOrient")[0]], worst_t, worst_r, len(frames)))
gate(3, worst_bone < 0.01 and worst_limb < 0.05,
     "every other bone on Cascadeur's: orientation %.4f deg, limbs pointing %.4f deg (twists: the rig's own share)"
     % (worst_bone, worst_limb))

# ------------------------------------------------ B: a bare keyed skeleton, a node of the animator's holding the name
fresh()
print(character.add_character(catalog.character_by_key("Creep")))
root = [r for r in cmds.ls("root", type="joint", long=True) if not cmds.listRelatives(r, parent=True, type="joint")][0]
tx, ty, tz = cmds.getAttr(root + ".translate")[0]
for t, dx, dz, ry in ((0, 0, 0, 0), (10, 20, 50, 30)):
    cmds.setKeyframe(root, attribute="translateX", time=t, value=tx + dx)
    cmds.setKeyframe(root, attribute="translateZ", time=t, value=tz + dz)
    cmds.setKeyframe(root, attribute="rotateY", time=t, value=ry)
cmds.playbackOptions(min=0, max=10, animationStartTime=0, animationEndTime=10)
kframes = [0, 3, 7, 10]
# since 2026-09-28 the Creep arrives under its own `Armature`; here it is called what a second Creep's
# is called on arrival, and the animator's own node holds the name the file needs
creep_null = cmds.listRelatives(root, parent=True, fullPath=True)[0]
root_uuid = cmds.ls(root, uuid=True)[0]
cmds.rename(creep_null, "Creep_Skeleton_Armature")
root = cmds.ls(root_uuid, long=True)[0]
cmds.parent(cmds.spaceLocator(name="animatorsLocator")[0], cmds.group(empty=True, name="Armature"))
group = cmds.ls("|Armature", uuid=True)[0]
before = snapshot(root, kframes)
path_b, info = export(root, "creep_keyed")
same, text = restored(before, kframes)
group_ok = cmds.ls(group, long=True) == ["|Armature"] and bool(cmds.listRelatives("|Armature", children=True))
fresh()
b_root = read(path_b, "B")
back = []
for t in kframes:
    cmds.currentTime(t)
    back.append(wm(b_root))
worst = max(mdiff(x, y) for x, y in zip(back, before["worlds"]))
gate(5, info["layout"] == "cascadeur" and info["wrapper"] == "Armature" and same and group_ok
     and [p.split(":")[-1] for p in cmds.listRelatives(b_root, parent=True) or []] == ["Armature"] and worst < 1e-4
     and b"skeldarCharacter" not in open(path_b, "rb").read(),
     "a keyed Creep skeleton: wrapper %r while the animator's |Armature held the name (back: %s); the file's root world on the "
     "scene's %.1e; the scene after: %s" % (info["wrapper"], group_ok, worst, text))

# ------------------------------------------------ C: a static skeleton
fresh()
character.add_character(catalog.character_by_key("Creep"))
root = [r for r in cmds.ls("root", type="joint", long=True) if not cmds.listRelatives(r, parent=True, type="joint")][0]
before = snapshot(root, [0])
path_c, info = export(root, "creep_static", start=0, end=1)
same, text = restored(before, [0])
fresh()
c_root = read(path_c, "C")
t_local = cmds.getAttr(c_root + ".translate")[0]
gate(6, info["layout"] == "cascadeur" and same
     and max(abs(a - b) for a, b in zip(t_local, (0.002, -2.401, 0.0))) < 2e-3,
     "a static Creep skeleton: root's translate in the file %s (Cascadeur writes (0.002, -2.401, 0)); the scene: %s"
     % ([round(v, 4) for v in t_local], text))

# ------------------------------------------------ D: Manny
fresh()
character.add_character(catalog.character_by_key("Manny_Rig"))
root = maya_rigs.find("Manny_Rig").skeleton_root
before = snapshot(root, [0])
path_d, info = export(root, "manny_rig", start=0, end=1)
same, text = restored(before, [0])
gate(7, info["layout"] == "cascadeur" and info["wrapper"] == "Armature" and same,
     "Manny_Rig: wrapper %r; the scene: %s" % (info["wrapper"], text))

# ------------------------------------------------ B2: the same keyed Creep, layout="plain": out of its Armature and back
fresh()
character.add_character(catalog.character_by_key("Creep"))
root = [r for r in cmds.ls("root", type="joint", long=True) if not cmds.listRelatives(r, parent=True, type="joint")][0]
tx, ty, tz = cmds.getAttr(root + ".translate")[0]
for t, dx, dy, ry in ((0, 0, 0, 0), (10, 20, -50, 30)):
    cmds.setKeyframe(root, attribute="translateX", time=t, value=tx + dx)
    cmds.setKeyframe(root, attribute="translateY", time=t, value=ty + dy)
    cmds.setKeyframe(root, attribute="rotateY", time=t, value=ry)
cmds.playbackOptions(min=0, max=10, animationStartTime=0, animationEndTime=10)
parent_before = cmds.listRelatives(root, parent=True, fullPath=True)
before = snapshot(root, kframes)
path_b2, info = export(root, "creep_keyed_plain", layout="plain")
same, text = restored(before, kframes)
parent_after = cmds.listRelatives(cmds.ls(cmds.ls(root, uuid=True)[0], long=True)[0], parent=True, fullPath=True)
fresh()
p_root = read(path_b2, "P")
back = []
for t in kframes:
    cmds.currentTime(t)
    back.append(wm(p_root))
worst = max(mdiff(x, y) for x, y in zip(back, before["worlds"]))
jo = cmds.getAttr(p_root + ".jointOrient")[0]
gate(10, info["layout"] == "plain" and not info["notes"] and not cmds.listRelatives(p_root, parent=True)
     and abs(jo[0] + 90) < 1e-2 and worst < 1e-4 and same and parent_after == parent_before,
     'a keyed Creep standing under its Armature, layout="plain": the root in the file at world level (jointOrient %s), '
     "its world on the scene's %.1e; the scene after: %s, back under %s"
     % ([round(v, 3) for v in jo], worst, text, parent_after))

# ------------------------------------------------ E: a pairBlend on root, and layout="plain"
def pairblended(key):
    fresh()
    character.add_character(catalog.character_by_key(key))
    r = [j for j in cmds.ls("root", type="joint", long=True) if not cmds.listRelatives(j, parent=True, type="joint")][0]
    cmds.setKeyframe(r, attribute="translateX", time=0)
    cmds.pointConstraint(cmds.spaceLocator(name="layoutProbeDriver")[0], r, maintainOffset=True)
    return r, bool(cmds.listConnections(r + ".translateX", type="pairBlend"))


# a root at world level (Manny's skeleton): it cannot be moved under the wrapper -- the plain file, said
root, blended = pairblended("Manny")
before = snapshot(root, [0])
path_e, info = export(root, "manny_pairblend", start=0, end=1)
same, text = restored(before, [0])
ok_world = blended and info["layout"] == "plain" and any("pairBlend" in n for n in info["notes"]) and same
report = ["at world: layout %s, notes %s, scene %s" % (info["layout"], info["notes"], "same" if same else text)]
# a root standing under its Armature (the Creep since 2026-09-28): Cascadeur's file is it as it stands --
# nothing to move -- and the plain file, which would have to move it, goes out in the layout it stands in
root, blended2 = pairblended("Creep")
before = snapshot(root, [0])
path_e2, info2 = export(root, "creep_pairblend", start=0, end=1)
same2, text2 = restored(before, [0])
path_e3, info3 = export(root, "creep_pairblend_plain", start=0, end=1, layout="plain")
same3, text3 = restored(before, [0])
ok_standing = (blended2 and info2["layout"] == "cascadeur" and not info2["notes"] and same2
               and info3["layout"] == "cascadeur" and any("pairBlend" in n for n in info3["notes"]) and same3)
report.append("under its Armature: cascadeur %s %s, plain asked -> %s %s; scene %s / %s"
              % (info2["layout"], info2["notes"], info3["layout"], info3["notes"],
                 "same" if same2 else text2, "same" if same3 else text3))
gate(8, ok_world and ok_standing, "a pairBlend on root -- " + "; ".join(report))

fresh()
character.add_character(catalog.character_by_key("Creep"))
root = [r for r in cmds.ls("root", type="joint", long=True) if not cmds.listRelatives(r, parent=True, type="joint")][0]
path_f, info = export(root, "creep_plain", start=0, end=1, layout="plain")
fresh()
f_root = read(path_f, "F")
jo = cmds.getAttr(f_root + ".jointOrient")[0]
gate(9, info["layout"] == "plain" and not cmds.listRelatives(f_root, parent=True) and abs(jo[0] + 90) < 1e-3,
     'layout="plain": root at world level, jointOrient %s' % [round(v, 3) for v in jo])

print("RESULT: %d of 10 gates failed %s" % (len(FAILS), sorted(FAILS)))
