"""Standalone gates for the shipped clean Creep skeleton (assets/Creep_Skeleton.ma) through Add Character.

    mayapy verify_creep_skeleton_asset.py

An empty scene: «Creep [skeleton]», then «Creep [rig]» beside it, then a second skeleton.
The skeleton arrives with plain names (no namespace, like every skeleton row), 91 joints at
world level, five skins at their bind, painted, with no constraint on a bone, no node of
AdvancedSkeleton's network and no script node, weapon_r and weapon_l and no sword; the rig beside it
is still the only rig and still drives its own skeleton; a second press renames only the top
node, as the Manny skeleton's does.
"""
import sys

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds
import maya.api.OpenMaya as om

sys.path.insert(0, "C:/!!!Work/MayaScripts/SkeldarAnim")
for p in ("matrixNodes", "quatNodes"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass
FAILS = []


def gate(n, ok, msg):
    print("%s gate %02d: %s" % ("PASS" if ok else "FAIL", n, msg))
    if not ok:
        FAILS.append(n)


def wm(n):
    return om.MMatrix(cmds.getAttr(n + ".worldMatrix[0]"))


cmds.file(new=True, force=True)
from maya_scenesetup import catalog, character
import maya_rigs

entry = catalog.character_by_key("Creep")
before = set(cmds.ls())
text = character.add_character(entry)
print("   ", text.splitlines()[0])
new = [n for n in cmds.ls() if n not in before]
gate(1, entry.label in catalog.character_labels() and text.startswith("Creep [skeleton] added"), "the row and the press: %s" % text.splitlines()[0])
#  since 2026-09-28 in the layout of the Creep's own FBX: `root` under the Null `Armature`, the meshes at the top
root = cmds.ls("|Creep_Skeleton_Character|Armature|root", type="joint", long=True)
joints = ([root[0]] + cmds.listRelatives(root[0], ad=True, type="joint", fullPath=True)) if root else []
gate(2, len(joints) == 91 and not [n for n in new if ":" in n], "91 joints under |Armature|root, plain names (%d namespaced nodes)" % len([n for n in new if ":" in n]))
worst, skins = 0.0, cmds.ls(type="skinCluster")
for sc in skins:
    for idx in cmds.getAttr(sc + ".matrix", multiIndices=True) or []:
        src = cmds.listConnections("%s.matrix[%d]" % (sc, idx), s=True, d=False)
        if src:
            p = om.MMatrix(cmds.getAttr("%s.bindPreMatrix[%d]" % (sc, idx))) * wm(src[0])
            worst = max(worst, max(abs(p.getElement(r, c) - (r == c)) for r in range(4) for c in range(4)))
gate(3, len(skins) == 5 and worst < 1e-4, "%d skins at their bind: |BPM*WM - I| worst %.2e" % (len(skins), worst))
as_types = ("multiplyDivide", "blendTwoAttr", "setRange", "blendColors", "composeMatrix", "condition", "plusMinusAverage",
            "ikHandle", "ikRPsolver", "expression", "animCurveUU", "animCurveUA", "blendMatrix", "curveInfo", "nurbsCurve")
rigish = [n for n in new if cmds.nodeType(n) in as_types]
on_bones = cmds.listRelatives(root[0], ad=True, type="constraint") or []
gate(4, not rigish and not on_bones and not maya_rigs.rigs() and not [n for n in new if cmds.nodeType(n) == "script"],
     "nothing of the rig came along: %d rig-type nodes, %d constraints on bones, rigs %s, script nodes %s"
     % (len(rigish), len(on_bones), maya_rigs.rigs(), [n for n in new if cmds.nodeType(n) == "script"]))
# beside the Armature: at the top of the scene before 2026-10-02, in the character's group since
_beside = maya_rigs.group_of(root[0]) if root else None
geo = [t.split("|")[-1] for t in (cmds.listRelatives(_beside, children=True, fullPath=True)
                                   if _beside else cmds.ls(assemblies=True, long=True)) or []
       if t.split("|")[-1].startswith("Creep_")]
wr = [j for j in joints if j.endswith("|hand_r|weapon_r")]
wl = [j for j in joints if j.endswith("|hand_l|weapon_l")]
gate(5, {"Creep_Body", "Creep_Back", "Creep_Arm_L", "Creep_Arm_R", "Creep_Face"} <= set(geo) and "Creep_Props" not in geo
     and wr and wl and not [j for j in joints if j.endswith("weapon_test")],
     "the top of the scene holds %s beside the Armature, no swords (a weapon is the catalog's); weapon_r under hand_r, weapon_l under hand_l: %s %s"
     % (geo, bool(wr), bool(wl)))
painted = [m for m in cmds.ls("Creep_*", type="mesh") if not cmds.getAttr(m + ".intermediateObject")]
colours = set()
for m in painted:
    for sg in cmds.listConnections(m, type="shadingEngine") or []:
        # textured since 2026-09-30 (verify_creep_textured.py): the materials our textured marker names
        colours.update(x for x in cmds.ls(cmds.listConnections(sg + ".surfaceShader", s=True, d=False) or [], materials=True)
                       if cmds.attributeQuery("skeldarTexture", node=x, exists=True))
gate(6, len(painted) == 5 and len(colours) == 3, "%d meshes textured with %s" % (len(painted), sorted(colours)))
# beside the rig
rig_text = character.add_character(catalog.character_by_key("Creep_Rig"))
rigs = maya_rigs.rigs()
gate(7, len(rigs) == 1 and rigs[0].namespace == "Creep_Rig" and rigs[0].skeleton_root == "|Creep_Rig_Character|Creep_Rig:Armature|Creep_Rig:root" and cmds.objExists("|Creep_Skeleton_Character|Armature|root"),
     "the rig added beside it is the only rig and drives its own skeleton: %s" % [(r.namespace, r.skeleton_root) for r in rigs])
rest = dict((j, wm(j)) for j in joints)
cmds.setAttr("Creep_Rig:FKShoulder_L.rotateZ", 30)
moved = max(max(abs(a - b) for a, b in zip(list(m), list(wm(j)))) for j, m in rest.items())
cmds.setAttr("Creep_Rig:FKShoulder_L.rotateZ", 0)
gate(8, moved < 1e-9, "posing the rig moves the clean skeleton by %.9f" % moved)
second = character.add_character(entry)
print("   ", second.splitlines()[0])
# Since 2026-10-02 each skeleton stands in a character group of its own, so the second one's Null no
# longer clashes on arrival: two groups, each holding an `Armature` with its `root`.
import maya_rigs  # noqa: E402
nulls = [c for g in maya_rigs.character_groups()
         for c in cmds.listRelatives(g, children=True, fullPath=True, type="transform") or []
         if [j for j in cmds.listRelatives(c, children=True, fullPath=True, type="joint") or []
             if j.endswith("|root")]]
gate(9, len(nulls) == 2 and all(n.endswith("|Armature") for n in nulls),
     "a second skeleton: its own group, each holding an Armature with its `root`: %s" % nulls)
print("RESULT: %d of 9 gates failed %s" % (len(FAILS), FAILS))
