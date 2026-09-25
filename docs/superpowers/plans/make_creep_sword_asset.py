"""The Creep's sword out of the rig into the weapon catalog, and the rig's weapon bones on the convention.

    mayapy make_creep_sword_asset.py

2026-09-24, the animator: «сейчас у нас оружие хантера встроено прямо в риг. Давай это исправим
и сделаем консистентно ... добавлять и удалять оружие и анимация переносилась на вепон бону и
обратно. Также давай добавим меч хантера в список нашего оружия».  mayapy STANDALONE on the
shipped rig, in place:

1. `export_sword` -- `Creep_Sword` (the blade only -- `Creep_Sword_Low` IS the handle and was
   wrongly left out; the fbx is now made by make_creep_sword_fbx.py, both pieces, the animator's
   grip baked) into `assets/Creep_Sword.fbx`, expressed in the frame
   weapon_r will have: blade +Y, guard X, thickness Z, the origin where the Creep held it;
2. `drop_props` -- both swords out of the rig;
3. `weapon_bones` -- weapon_test renamed weapon_r and turned half a turn about its own Z,
   weapon_l created as its mirror under hand_l;
4. the shading networks the swords wore and nothing else does deleted; saved; Maya's own
   configuration script nodes cut from the text; refused if a banned string survives;
5. the fbx read back and its extents printed against the convention.

Then rebuild the clean skeleton from the new rig: make_creep_skeleton_asset.py.
"""
import os
import sys

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

for p in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.abspath(os.path.join(HERE, "..", "..", "..", "SkeldarAnim", "assets"))
RIG = os.path.join(ASSETS, "Creep_Rig.ma").replace("\\", "/")
SWORD = os.path.join(ASSETS, "Creep_Sword.fbx").replace("\\", "/")
BANNED = ("Creep_Sword", "weapon_test", "SKM_Manny_Simple", "createNode script", "vaccine", "breed_gene")

cmds.file(RIG, open=True, force=True, executeScriptNodes=False)
P = os.path.join(HERE, "as_creep_rig_procedure.py")
g = {"__name__": "creep_rig", "__file__": P}
exec(compile(open(P, encoding="utf-8").read(), P, "exec"), g)

ext = g["export_sword"](SWORD)
print("sword exported in weapon_r's frame: X %.2f..%.2f  Y %.2f..%.2f  Z %.2f..%.2f" % (ext[0] + ext[1] + ext[2]))
print("props dropped:", g["drop_props"]())
wr, wl = g["weapon_bones"]()
print("weapon bones:", wr, wl)

KEEP = {"initialShadingGroup", "initialParticleSE", "lambert1", "standardSurface1", "particleCloud1", "openPBR_shader1"}
for _ in range(6):
    doomed = [sg for sg in cmds.ls(type="shadingEngine") if sg not in KEEP and not cmds.sets(sg, query=True)]
    doomed += cmds.ls(cmds.listConnections(doomed, type="materialInfo") or [])
    doomed += [m for m in cmds.ls(materials=True) if m not in KEEP and not cmds.listConnections(m, type="shadingEngine")]
    doomed = [n for n in doomed if cmds.objExists(n)]
    if not doomed:
        break
    cmds.delete(sorted(set(doomed)))

# what must hold
b = g["bones"]()
worst = 0.0
for sc in cmds.ls(type="skinCluster"):
    for idx in cmds.getAttr(sc + ".matrix", multiIndices=True) or []:
        src = cmds.listConnections("%s.matrix[%d]" % (sc, idx), s=True, d=False)
        if src:
            m = om.MMatrix(cmds.getAttr("%s.bindPreMatrix[%d]" % (sc, idx))) * om.MMatrix(cmds.getAttr(src[0] + ".worldMatrix[0]"))
            worst = max(worst, max(abs(m.getElement(r, c) - (r == c)) for r in range(4) for c in range(4)))
assert worst < 1e-4, worst
assert "weapon_r" in b and "weapon_l" in b and "weapon_test" not in b
assert cmds.getAttr("|Group.skeldarRetarget") == "rotation"
print("bind |BPM*WM - I| %.2e; weapon_r under %s, weapon_l under %s" % (worst, b["weapon_r"].split("|")[-2], b["weapon_l"].split("|")[-2]))

cmds.file(rename=RIG)
cmds.file(save=True, type="mayaAscii", force=True)
with open(RIG, encoding="utf-8", errors="surrogateescape") as fh:
    lines = fh.readlines()
kept, skipping = [], False
for line in lines:
    if line.startswith("createNode script "):
        skipping = True
        continue
    if skipping and line[:1] not in ("\t", " "):
        skipping = False
    if not skipping:
        kept.append(line)
with open(RIG, "w", encoding="utf-8", errors="surrogateescape", newline="") as fh:
    fh.writelines(kept)
bad = []
with open(RIG, encoding="utf-8", errors="replace") as fh:
    for n, line in enumerate(fh, 1):
        bad += [(n, w) for w in BANNED if w in line]
if bad:
    raise RuntimeError("banned content in the rebuilt rig (file KEPT for inspection): %s" % bad[:10])
print("rig saved: %s (%.1f MB)" % (RIG, os.path.getsize(RIG) / 1e6))

# the fbx, read back the way Add reads it
cmds.file(new=True, force=True)
sys.path.insert(0, os.path.abspath(os.path.join(ASSETS, "..")))
from maya_scenesetup import attach
roots = attach.import_model(SWORD)
meshes = attach.mesh_transforms(roots)
shape = cmds.listRelatives(meshes[0], shapes=True, fullPath=True, noIntermediate=True)[0]
sel = om.MSelectionList(); sel.add(shape)
pts = om.MFnMesh(sel.getDagPath(0)).getPoints(om.MSpace.kWorld)
e = [(min(p[i] for p in pts), max(p[i] for p in pts)) for i in range(3)]
print("re-import: %s, %d verts, X %.2f..%.2f  Y %.2f..%.2f  Z %.2f..%.2f" % (meshes, len(pts), e[0][0], e[0][1], e[1][0], e[1][1], e[2][0], e[2][1]))
size = [e[i][1] - e[i][0] for i in range(3)]
assert size[1] == max(size) and e[1][1] > -e[1][0] and size[0] > size[2], "not on the convention"
print("DONE: the blade on +Y (tip at +Y), the guard on X, the thickness on Z; %.1f MB fbx" % (os.path.getsize(SWORD) / 1e6))
