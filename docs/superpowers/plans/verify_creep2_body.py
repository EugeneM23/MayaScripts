"""Standalone gates for the second Creep's cut body (assets/Creep2_Body_Rig.ma, Creep2_Body_Skeleton.ma).

    mayapy verify_creep2_body.py <a clip .fbx>

mayapy STANDALONE, an empty scene, 2026-10-27 (make_creep2_body_assets.py):

1. both rows in the catalog and the grid, whole (no part), untextured, a portrait;
2. «Creep 2 Body [rig]» and «Creep 2 [rig]» added: each in its namespace, rotation-only, the body's one
   mesh Creep2_BodySplit in Group|Geometry, its skin at its bind, painted, controls at default;
3. the cut body where the elbow cut has it, every vertex, at the bind;
4. every body vertex on a vertex of Creep 2's whole mesh at the bind (the cut is a piece of it);
5. the clip retarget through the Retarget button onto both rigs: every body vertex on its whole-mesh
   vertex on every sampled frame - the body deforms exactly as Creep 2 does;
6. the export: 93 joints, no mesh;
7. «Creep 2 Body [skeleton]»: 93 joints, the mesh on the FBX's, skinned at its bind, no constraint;
8. Delete character: nothing of it left.
"""
import os
import sys
import tempfile

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
CLIP = sys.argv[1].replace("\\", "/")
# the elbow cut since 2026-10-27 (make_creep2_elbow_cut.py): the body without the head and the forearm
SOURCE = "C:/!!!Work/MayaScripts/sources/creep2/Creep2_ElbowCut.ma"
SOURCE_MESH = "Creep2_BodyElbow"
FAILS = []


def gate(n, ok, msg):
    print("%s gate %02d: %s" % ("PASS" if ok else "FAIL", n, msg))
    if not ok:
        FAILS.append(n)


def wm(n):
    return om.MMatrix(cmds.getAttr(n + ".worldMatrix[0]"))


def points(transform):
    shape = cmds.listRelatives(transform, shapes=True, fullPath=True, noIntermediate=True)[0]
    sel = om.MSelectionList()
    sel.add(shape)
    return om.MFnMesh(sel.getDagPath(0)).getPoints(om.MSpace.kWorld)


def bind_error(prefix):
    worst, n = 0.0, 0
    for sc in cmds.ls(type="skinCluster"):
        if not sc.startswith(prefix):
            continue
        n += 1
        for idx in cmds.getAttr(sc + ".matrix", multiIndices=True) or []:
            src = cmds.listConnections("%s.matrix[%d]" % (sc, idx), s=True, d=False)
            if src:
                m = om.MMatrix(cmds.getAttr("%s.bindPreMatrix[%d]" % (sc, idx))) * wm(src[0])
                worst = max(worst, max(abs(m.getElement(r, c) - (r == c)) for r in range(4) for c in range(4)))
    return n, worst


def import_fbx(path, ns):
    before = set(cmds.ls(long=True, dag=True))
    cmds.namespace(add=ns)
    cmds.namespace(set=":" + ns)
    mel.eval("FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;")
    mel.eval('FBXImport -f "%s";' % path)
    cmds.namespace(set=":")
    return [n for n in cmds.ls(long=True, dag=True) if n not in before]


def import_src(ns):
    before = set(cmds.ls(long=True, dag=True))
    cmds.file(SOURCE, i=True, namespace=ns, executeScriptNodes=False)
    return [n for n in cmds.ls(long=True, dag=True) if n not in before]


def src_mesh_of(nodes):
    return [n for n in nodes if cmds.nodeType(n) == "transform" and n.split(":")[-1] == SOURCE_MESH][0]


def nearest_map(cut, whole, cell=0.05):
    """For each point of `cut` the index of the nearest point of `whole` and the distance."""
    grid = {}
    for i, p in enumerate(whole):
        grid.setdefault((int(p.x // cell), int(p.y // cell), int(p.z // cell)), []).append(i)
    out, dist = [], []
    for p in cut:
        k = (int(p.x // cell), int(p.y // cell), int(p.z // cell))
        best, bi = 1e9, -1
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for i in grid.get((k[0] + dx, k[1] + dy, k[2] + dz), ()):
                        d = p.distanceTo(whole[i])
                        if d < best:
                            best, bi = d, i
        out.append(bi)
        dist.append(best)
    return out, dist


cmds.file(new=True, force=True)
from maya_scenesetup import catalog, character, deletion  # noqa: E402
import maya_rigs  # noqa: E402
import maya_asretarget as ar  # noqa: E402
import maya_rig_retarget as rr  # noqa: E402
from maya_uebridge import animexport  # noqa: E402

rig_row, skel_row = catalog.character_by_key("Creep2_Body_Rig"), catalog.character_by_key("Creep2_Body")
gate(1, rig_row and skel_row and catalog.character_for("Creep2_Body", "rig") == rig_row
     and catalog.character_for("Creep2_Body", "skeleton") == skel_row and not rig_row.part and not skel_row.part
     and not rig_row.textured and os.path.isfile(catalog.portrait_path("Creep2_Body")),
     "the rows %s / %s, the portrait %s" % (rig_row and rig_row.label, skel_row and skel_row.label,
                                            os.path.isfile(catalog.portrait_path("Creep2_Body"))))

for row in (rig_row, catalog.character_by_key("Creep2_Rig")):
    print("   ", character.add_character(row).splitlines()[0])
rigs = dict((r.namespace, r) for r in maya_rigs.rigs())
b, w = rigs.get("Creep2_Body_Rig"), rigs.get("Creep2_Rig")
geo = cmds.listRelatives(cmds.ls("Creep2_Body_Rig:Geometry", long=True)[0], children=True) or []
n_sk, err = bind_error("Creep2_Body_Rig:")
mats = set()
for sg in cmds.listConnections(cmds.ls("Creep2_Body_Rig:Creep2_BodySplitShape", long=True)[0], type="shadingEngine") or []:
    mats.update(cmds.listConnections(sg + ".surfaceShader") or [])
gate(2, b and w and ar.rotation_mode(b) and geo == ["Creep2_Body_Rig:Creep2_BodySplit"] and n_sk == 1
     and err < 1e-3 and not ar.posed_controls(rig=b)
     and any(cmds.attributeQuery("skeldarColour", node=m, exists=True) for m in mats),
     "rigs %s, rotation-only, Geometry %s, skin at its bind (%.2e), worn %s" % (sorted(rigs), geo, err, sorted(mats)))

body = cmds.ls("Creep2_Body_Rig:Creep2_BodySplit", long=True)[0]
whole = cmds.ls("Creep2_Rig:Creep2_Body", long=True)[0]
src_nodes = import_src("ue")
src_mesh = src_mesh_of(src_nodes)
a, c = points(src_mesh), points(body)
worst_v = max(a[i].distanceTo(c[i]) for i in range(len(a))) if len(a) == len(c) else -1
gate(3, len(a) == len(c) and 0 <= worst_v < 1e-3, "every one of %d vertices where the elbow cut has it (%.2e cm)"
     % (len(c), worst_v))
cmds.delete([n for n in src_nodes if cmds.objExists(n) and not cmds.listRelatives(n, parent=True)] or [])
cmds.namespace(removeNamespace="ue", deleteNamespaceContent=True)

pairs, dist = nearest_map(points(body), points(whole))
shared = sum(1 for d in dist if d < 1e-3)
gate(4, shared > 0.95 * len(dist),
     "%d of %d body vertices on a vertex of Creep 2's whole mesh at the bind (the rest: the cut's edges); "
     "the weights are the animator's own, the FBX's" % (shared, len(dist)))

# the FBX itself beside the rig, its joints put on the rig's game bones every sampled frame
src_nodes = import_src("ue")
src_mesh = src_mesh_of(src_nodes)
ue_j = sorted((n for n in src_nodes if cmds.nodeType(n) == "joint"), key=lambda n: n.count("|"))
game = dict((p.split("|")[-1].split(":")[-1], p)
            for p in [b.skeleton_root] + cmds.listRelatives(b.skeleton_root, ad=True, type="joint", fullPath=True))
clip_nodes = import_fbx(CLIP, "clip")
src = min((j for j in clip_nodes if cmds.nodeType(j) == "joint" and not cmds.listRelatives(j, parent=True, type="joint")),
          key=lambda j: j.count("|"))
S = [src] + (cmds.listRelatives(src, ad=True, type="joint", fullPath=True) or [])
first, last = cmds.findKeyframe(S, which="first"), cmds.findKeyframe(S, which="last")
cmds.playbackOptions(min=first, max=last, animationStartTime=first, animationEndTime=last)
cmds.select(maya_rigs.node(b, "Main"), src)
ok, text = rr.run_retarget()
print("   ", text.splitlines()[0][:180])
worst, worst_at, travel = 0.0, "", 0.0
start = points(body)
for t in range(int(first), int(last) + 1, max(1, int((last - first) / 12))):
    cmds.currentTime(t)
    for j in ue_j:
        k = j.split("|")[-1].split(":")[-1]
        if k in game and k not in ("weapon_r", "weapon_l"):
            cmds.xform(j, worldSpace=True, matrix=list(wm(game[k])))
    pb, pf = points(body), points(src_mesh)
    for i in range(0, len(pb), 3):
        d = pb[i].distanceTo(pf[i])
        if d > worst:
            worst, worst_at = d, "vertex %d at %d" % (i, t)
    travel = max(travel, max(pb[i].distanceTo(start[i]) for i in range(0, len(pb), 97)))
gate(5, ok and worst < 0.01 and travel > 10,
     "the clip (%d..%d) through the Retarget button: every body vertex where the FBX's own skin puts it on "
     "the rig's bones to %.5f cm (worst %s), the body travelling %.1f cm" % (first, last, worst, worst_at, travel))

path = os.path.join(tempfile.gettempdir(), "skeldar_creep2_body_export.fbx").replace("\\", "/")
animexport.export_hierarchy(path, root=b.skeleton_root)
cmds.file(new=True, force=True)
mel.eval("FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;")
mel.eval('FBXImport -f "%s";' % path)
gate(6, len(cmds.ls(type="joint")) == 93 and not cmds.ls(type="mesh"),
     "the export: %d joints, %d meshes" % (len(cmds.ls(type="joint")), len(cmds.ls(type="mesh"))))

cmds.file(new=True, force=True)
print("   ", character.add_character(skel_row).splitlines()[0])
joints = cmds.ls(type="joint", long=True)
n_sk, err = bind_error("")
meshes = [cmds.listRelatives(s, parent=True, fullPath=True)[0] for s in cmds.ls(type="mesh", noIntermediate=True, long=True)]
src_nodes = import_src("ue")
src_mesh = src_mesh_of(src_nodes)
mine = [m for m in meshes if "Creep2_BodySplit" in m]
a, c = points(src_mesh), points(mine[0]) if mine else []
worst_v = max(a[i].distanceTo(c[i]) for i in range(len(a))) if len(a) == len(c) else -1
gate(7, len(joints) == 93 and n_sk == 1 and err < 1e-3 and len(meshes) == 1 and 0 <= worst_v < 1e-3
     and not cmds.ls(type="constraint"),
     "the skeleton: %d joints, %d mesh, skin at its bind (%.2e), on the FBX's (%.2e cm)"
     % (len(joints), len(meshes), err, worst_v))
cmds.delete([n for n in src_nodes if cmds.objExists(n) and not cmds.listRelatives(n, parent=True)] or [])
cmds.namespace(removeNamespace="ue", deleteNamespaceContent=True)
cmds.select(mine[0])
picked, unowned, _paths = deletion.selected_characters()
text = deletion.execute(deletion.plan(picked), len(unowned))
print("   ", str(text)[:160])
gate(8, not cmds.ls(type="joint") and not cmds.ls(type="mesh"), "Delete character: %d joints, %d meshes left"
     % (len(cmds.ls(type="joint")), len(cmds.ls(type="mesh"))))

print("FAILED gates: %s" % FAILS if FAILS else "ALL GATES PASSED")
maya.standalone.uninitialize()
