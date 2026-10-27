"""The Creep's right arm and head as shipped assets: a rig and a skeleton each.

    mayapy make_creep_part_assets.py rig <part> <built scene .mb>
    mayapy make_creep_part_assets.py skeleton <part>

mayapy STANDALONE, one asset per process (trap 122).  `rig` cleans a scene that
`as_creep_part_procedure.build` saved (script nodes, unknown nodes, curves feeding nothing,
shading nothing wears) and writes `assets/<Model>_Rig.ma`; `skeleton` reads the part's FBX from
`Creep_Split` into the shipped shape (`Armature` > root, the mesh at world level) and writes
`assets/<Model>_Skeleton.ma`.  Either refuses a file holding a script node or a path of this
machine.  See `docs/superpowers/specs/2026-10-27-creep-arm-head-parts-design.md`.
"""
import os
import sys

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds

for p in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.abspath(os.path.join(HERE, "..", "..", "..", "SkeldarAnim", "assets"))
MODEL = {"arm": "Creep2_ArmR", "head": "Creep2_Head"}
JOINTS = {"arm": 29, "head": 4}
BANNED = ("createNode script", "vaccine", "breed_gene", "C:/", "C:\\\\", "E:/", "Downloads", "MY PC")

KIND, PART = sys.argv[1], sys.argv[2]
model = MODEL[PART]
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


if KIND == "rig":
    cmds.file(sys.argv[3], open=True, force=True, executeScriptNodes=False)
    out = os.path.join(ASSETS, model + "_Rig.ma")
else:
    P = os.path.join(HERE, "as_creep_part_procedure.py")
    G = {"__name__": "part", "__file__": P}
    exec(compile(open(P, encoding="utf-8").read(), P, "exec"), G)
    cmds.file(new=True, force=True)
    G["_fbx"](G["SPLIT"] + "/" + G["PARTS"][PART]["fbx"])
    spec = G["PARTS"][PART]
    cmds.rename("|" + spec["group"], "Armature")
    mesh = [t for t in cmds.listRelatives("|Armature", children=True, fullPath=True) if cmds.nodeType(t) == "transform"][0]
    m = cmds.rename(G["out_of_group"](mesh), spec["mesh"])
    print("weapon_r onto the UE socket: turned %.3f deg" % G["weapon_socket"]())
    shp = [s for s in cmds.listRelatives("|" + m, shapes=True, fullPath=True) if not cmds.getAttr(s + ".io")][0]
    cmds.rename(shp, spec["mesh"] + "Shape")
    out = os.path.join(ASSETS, model + "_Skeleton.ma")

# the part is one of Creep 2's: its mesh and layer carry the model's name
old = {"arm": "Creep_ArmR", "head": "Creep_Head"}[PART]
for t in cmds.ls(old, type="transform", long=True) or []:
    shp = [x for x in cmds.listRelatives(t, shapes=True, fullPath=True) if not cmds.getAttr(x + ".io")]
    t = cmds.rename(t, model)
    if shp:
        cmds.rename(cmds.listRelatives(cmds.ls(t, long=True)[0], shapes=True, fullPath=True)[0], model + "Shape")
if cmds.objExists(old + "_Skeleton"):
    cmds.rename(old + "_Skeleton", model + "_Skeleton")
drop(cmds.ls(type="script"))
drop(cmds.ls(type="unknown") + cmds.ls(type="unknownDag"))
for plugin in cmds.unknownPlugin(query=True, list=True) or []:
    try:
        cmds.unknownPlugin(plugin, remove=True)
    except Exception:
        pass
drop([c for c in cmds.ls(type="animCurve") if not cmds.listConnections(c, source=False, destination=True)])
KEEP = {"initialShadingGroup", "initialParticleSE", "lambert1", "standardSurface1", "particleCloud1", "openPBR_shader1"}
for _ in range(6):
    doomed = [sg for sg in cmds.ls(type="shadingEngine") if sg not in KEEP and not cmds.sets(sg, query=True)]
    doomed += cmds.ls(cmds.listConnections(doomed, type="materialInfo") or [])
    doomed += [x for x in cmds.ls(materials=True) if x not in KEEP and not cmds.listConnections(x, type="shadingEngine")]
    doomed = [n for n in doomed if cmds.objExists(n)]
    if not doomed:
        break
    drop(sorted(set(doomed)))
# a texture's path is this machine's: the part wears the palette (Add paints it)
drop(cmds.ls(type="file"))
for f in list(cmds.fileInfo(query=True) or [])[::2]:
    if f not in ("application", "product", "version", "cutIdentifier", "osv", "UUID", "license"):
        cmds.fileInfo(remove=f)

root = cmds.ls("|Armature|root", type="joint", long=True)
assert root and len(cmds.listRelatives(root[0], allDescendents=True, type="joint")) + 1 == JOINTS[PART], root
if KIND == "rig":
    assert cmds.getAttr("|Group.skeldarPartAnchor") == "spine_05"
    assert cmds.objExists("|Group|PartAnchor")
    assert model in (cmds.listRelatives("|Group|Geometry", children=True) or [])
    assert not cmds.ls("*_L", type="joint"), "a left side"
else:
    assert cmds.objExists("|" + model) and not cmds.objExists("|Group")
    lay = cmds.createDisplayLayer(name=model + "_Skeleton", empty=True)
    cmds.editDisplayLayerMembers(lay, cmds.ls("|Armature|root", dag=True, type="joint", long=True), noRecurse=True)
print("assemblies:", cmds.ls(assemblies=True), "deleted", len(deleted))
cmds.file(rename=out.replace("\\", "/"))
cmds.file(save=True, type="mayaAscii", force=True)

with open(out, encoding="utf-8", errors="surrogateescape") as fh:
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
with open(out, "w", encoding="utf-8", errors="surrogateescape", newline="") as fh:
    fh.writelines(kept)
bad = []
with open(out, encoding="utf-8", errors="replace") as fh:
    for n, line in enumerate(fh, 1):
        for word in BANNED:
            if word in line:
                bad.append((n, word, line.strip()[:120]))
if bad:
    os.remove(out)
    raise RuntimeError("banned content in the asset, deleted: %s" % bad[:10])
print("saved %s (%.1f MB), script nodes cut %d" % (out, os.path.getsize(out) / 1e6, cut))
