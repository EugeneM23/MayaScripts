"""Build SkeldarAnim/assets/Orc_Rig.ma from the scene `rebuild_orc_rig.py` saved.

    mayapy make_orc_rig_asset.py <built rig .mb> [<out .ma>]

mayapy STANDALONE, never the live scene: it deletes things.  The source is opened with its
script nodes NOT executed.  `make_creep_rig_asset.py`'s clean-up (2026-09-24) for the orc
(2026-09-25): every script node, unknown nodes and the plugin requirements they leave, dagPoses
with no member, animCurves driving nothing, and the shading networks nothing wears any more --
the importer made one per LOD, and only LOD0 is kept.

What stays is what Add Character imports into its own namespace: `|root` (95 joints: Manny's
93 names -- weapon_r, weapon_l, camera_root, camera_bone added on Manny's local values -- and
the shoulder pads AB_Armor_Shoulder_L/R), `|Group` (the AdvancedSkeleton rig,
`skeldarRetarget = "rotation"`, `Orc_Body` under its Geometry group with its skin and its
56-target blendShape), the Orc_Skeleton layer, the rig's sets and the orc's five materials.
Saved as mayaAscii, script-node blocks cut from the text (trap 74), then read back and refused
if anything banned is in it.
"""
import os
import sys

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds

for p in ("matrixNodes", "quatNodes"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass

SRC = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "SkeldarAnim", "assets", "Orc_Rig.ma")
OUT = os.path.abspath(OUT).replace("\\", "/")
BANNED = ("createNode script", "vaccine", "breed_gene", "SK_Orc_Marauder_F_LOD1", "SK_Orc_Marauder_F_LodGroup",
          "D:/Characters", "Orc_Low_Body_Normal", "FitSkeletonNameMatcherImporting",
          "arp_rig_name", "flip_fluid", "ori_name")

cmds.file(SRC, open=True, force=True, executeScriptNodes=False)
deleted = []


def drop(nodes):
    for n in nodes:
        if cmds.objExists(n):
            try:
                cmds.lockNode(n, lock=False)
            except Exception:
                pass
            cmds.delete(n)
            deleted.append(n)


drop(cmds.ls(type="script"))
drop(cmds.ls(type="unknown") + cmds.ls(type="unknownDag"))
for plugin in cmds.unknownPlugin(query=True, list=True) or []:
    try:
        cmds.unknownPlugin(plugin, remove=True)
    except Exception:
        pass
drop([p for p in cmds.ls(type="dagPose") if not cmds.dagPose(p, query=True, members=True)])
drop([c for c in cmds.ls(type="animCurve") if not cmds.listConnections(c, source=False, destination=True)])

# the shading networks nothing wears any more (LOD1-4's): an empty shading group goes with its
# materialInfo, then a material no group uses, then textures that feed nothing -- until stable
KEEP = {"initialShadingGroup", "initialParticleSE", "lambert1", "standardSurface1", "particleCloud1", "openPBR_shader1"}
for _ in range(6):
    doomed = [sg for sg in cmds.ls(type="shadingEngine") if sg not in KEEP and not cmds.sets(sg, query=True)]
    doomed += cmds.ls(cmds.listConnections(doomed, type="materialInfo") or [])
    doomed += [m for m in cmds.ls(materials=True) if m not in KEEP and not cmds.listConnections(m, type="shadingEngine")]
    doomed += [t for t in cmds.ls(textures=True) + cmds.ls(type="place2dTexture")
               if not [d for d in cmds.listConnections(t, source=False, destination=True) or []
                       if cmds.nodeType(d) not in ("defaultTextureList", "defaultRenderUtilityList", "nodeGraphEditorInfo")]]
    doomed = [n for n in doomed if cmds.objExists(n)]
    if not doomed:
        break
    drop(sorted(set(doomed)))

# what must be there
root = cmds.ls("|root", type="joint", long=True)
below = cmds.listRelatives(root[0], allDescendents=True, type="joint") if root else []
assert root and len(below) == 94, "the orc skeleton, 95 joints (%d below root)" % len(below or [])
for n in ("weapon_r", "weapon_l", "camera_root", "camera_bone", "AB_Armor_Shoulder_L", "AB_Armor_Shoulder_R"):
    assert n in below, n
assert cmds.getAttr("|Group.skeldarRetarget") == "rotation", "the retarget mark"
geo = cmds.listRelatives("|Group|Geometry", children=True) or []
assert geo == ["Orc_Body"], geo
assert len(cmds.ls(type="skinCluster")) == 1 and len(cmds.ls(type="blendShape")) == 1, (cmds.ls(type="skinCluster"), cmds.ls(type="blendShape"))
print("assemblies:", cmds.ls(assemblies=True))
print("deleted %d nodes: %s" % (len(deleted), deleted[:16]))
print("skinClusters:", cmds.ls(type="skinCluster"), "dagPoses:", cmds.ls(type="dagPose"),
      "materials:", [m for m in cmds.ls(materials=True) if m not in KEEP])

cmds.file(rename=OUT)
cmds.file(save=True, type="mayaAscii", force=True)

# Maya writes its own uiConfiguration/sceneConfiguration script nodes on every save (trap 74):
# cut out of the text, block by block (a node's block runs to the next top-level statement)
with open(OUT, encoding="utf-8", errors="surrogateescape") as fh:
    lines = fh.readlines()
kept, skipping, cut = [], False, 0
for line in lines:
    if line.startswith("createNode script "):
        skipping, cut = True, cut + 1
        continue
    if skipping and line[:1] not in ("\t", " "):
        skipping = False
    if not skipping:
        kept.append(line)
with open(OUT, "w", encoding="utf-8", errors="surrogateescape", newline="") as fh:
    fh.writelines(kept)
print("script nodes cut from the text: %d" % cut)
bad = []
with open(OUT, encoding="utf-8", errors="replace") as fh:
    for n, line in enumerate(fh, 1):
        for word in BANNED:
            if word in line:
                bad.append((n, word))
if bad:
    os.remove(OUT)
    raise RuntimeError("banned content in the asset, deleted: %s" % bad[:10])
print("saved %s (%.1f MB)" % (OUT, os.path.getsize(OUT) / 1e6))
