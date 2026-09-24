"""Build SkeldarAnim/assets/Hunter_Rig.ma from a saved scene holding the Hunter's rig.

    mayapy make_hunter_rig_asset.py <saved scene .mb> [<out .ma>]

mayapy STANDALONE, never the live scene: it deletes things.  The source is opened with its
script nodes NOT executed.  Since 2026-09-24 (evening) that source is the rig REBUILT on the
re-bound skeleton (`rebind_hunter_pose.py` -> `rebuild_hunter_rig.py`, the bind = the pose of
the animator's SKM_Manny_Simple); the first asset came from the animator's own scene, which is
why the clean-up still knows about its leftovers.  Everything that is not the Hunter's rig goes:

- `Manny_Reference` -- the FBX wrapper that held `SKM_Manny_Simple`, a Manny mesh skinned onto
  the Hunter's bones (the animator: not in the asset), with its skinCluster and curves;
- `camera1`, `materialXStack1` (a MaterialX stack nothing uses);
- every script node (the scene's ui/scene configuration), unknown nodes and the plugin
  requirements they leave behind, and dagPoses that hold no member any more.

What stays is what Add Character imports into its own namespace: `|root` (91 joints, weapon_r
and weapon_l included), `|Group` (the AdvancedSkeleton rig, `skeldarRetarget = "rotation"`, the
five meshes under its Geometry group, no props -- a weapon is the catalog's), the
Hunter_Skeleton layer, the rig's sets and the materials.  Saved as mayaAscii, then read back as
text and refused if anything banned is in it.
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
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "SkeldarAnim", "assets", "Hunter_Rig.ma")
OUT = os.path.abspath(OUT).replace("\\", "/")
BANNED = ("SKM_Manny_Simple", "camera1", "materialXStack", "createNode script", "vaccine", "breed_gene",
          "Hunter_Sword", "Hunter_Props", "weapon_test")

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


# the Manny reference mesh with its skin and its animation
ref = cmds.ls("|Manny_Reference", long=True) or []
skm_skins = []
for shape in cmds.ls(cmds.listRelatives(ref, allDescendents=True, fullPath=True) or [], type="mesh"):
    skm_skins += cmds.ls(cmds.listHistory(shape, pruneDagObjects=True) or [], type="skinCluster")
curves = [c for c in cmds.ls(type="animCurve") if any(
    (cmds.ls(d, long=True) or [""])[0].startswith("|Manny_Reference")
    for d in cmds.listConnections(c, source=False, destination=True) or [])]
drop(sorted(set(skm_skins)) + curves + ref)
drop(cmds.ls("|camera1") + cmds.ls("materialXStack1*"))
drop(cmds.ls(type="script"))
drop(cmds.ls(type="unknown") + cmds.ls(type="unknownDag"))
for plugin in cmds.unknownPlugin(query=True, list=True) or []:
    try:
        cmds.unknownPlugin(plugin, remove=True)
    except Exception:
        pass
drop([p for p in cmds.ls(type="dagPose") if not cmds.dagPose(p, query=True, members=True)])
drop([c for c in cmds.ls(type="animCurve") if not cmds.listConnections(c, source=False, destination=True)])

# the shading networks nothing wears any more (Manny's, mostly): an empty shading group goes with
# its materialInfo, then a material no group uses, then textures that feed nothing -- until stable
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
assert root and len(cmds.listRelatives(root[0], allDescendents=True, type="joint")) == 90, "the Hunter skeleton (weapon_r, weapon_l)"
assert cmds.getAttr("|Group.skeldarRetarget") == "rotation", "the retarget mark"
geo = cmds.listRelatives("|Group|Geometry", children=True) or []
assert {"Hunter_Body", "Hunter_Back", "Hunter_Arm_L", "Hunter_Arm_R", "Hunter_Face"} <= set(geo) and "Hunter_Props" not in geo, geo
print("assemblies:", cmds.ls(assemblies=True))
print("deleted %d nodes: %s" % (len(deleted), deleted[:12]))
print("skinClusters:", cmds.ls(type="skinCluster"), "dagPoses:", cmds.ls(type="dagPose"))

cmds.file(rename=OUT)
cmds.file(save=True, type="mayaAscii", force=True)

# Maya writes its own uiConfiguration/sceneConfiguration script nodes on every save, batch or
# not.  They are cut out of the text, block by block (a node's block runs to the next top-level
# statement), the way the vaccine lines were cut from Manny_Skeleton.ma -- an imported asset
# has no business carrying a script node, and the test pins that it carries none.
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
