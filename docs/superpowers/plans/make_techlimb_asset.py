"""SkeldarAnim/assets/Armor/Tech_Limb.fbx out of what export_techlimb_from_unreal.py wrote.

    mayapy make_techlimb_asset.py

mayapy STANDALONE (2026-10-01; spec docs/superpowers/specs/2026-10-01-armor-techlimb-design.md).
The game's placement BAKED INTO THE POINTS: the plate's points in Manny's `lowerarm_l` local axes
(Maya's), at BP_Techlimb's offset and scale -- so equipped, the plate's node stands at identity in
its armor space and its channels read 0 exactly where Unreal puts it (the weapons' rule since
2026-09-30, «без офсетов»).

Measured, never assumed:
1. M, Unreal component space -> Maya world: the signed permutation fitting SK_Mannequin_proto's
   reference-pose bone positions onto Manny's bind (assets/manny_skeleton_template.json).
2. N, Unreal `lowerarm_l` axes -> Maya `lowerarm_l` axes: A^T M R_b, which must be a signed
   permutation (the two frames agree up to the axis convention).
3. The plate's target points q = N @ (its vertices in Unreal's bone space, the BP's offset applied by
   Unreal itself); A q + t must land on M @ (Unreal's component-space vertices): the reference pose
   IS Manny's bind.
4. The imported FBX's points matched to Unreal's mesh-space vertices through the signed permutation
   the FBX conversion applied (nearest-neighbour fit), then the similarity taking them onto q fitted
   and applied as the node's matrix and frozen -- normals turn with the points (trap 77).
Refuses on any residual over the bounds below. Then the mesh is named TechLimbMesh, wears a plain
lambert in the game's grey, and is exported and read back.
"""
import json
import os
import sys

import numpy as np

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
REPO = os.path.normpath(os.path.join(HERE, "..", "..", "..")).replace("\\", "/")
sys.path.insert(0, HERE)
import ue_maya_axes as axes  # noqa: E402

cmds.loadPlugin("fbxmaya", quiet=True)
SOURCE = REPO + "/sources/armor/SM_Shield_Test.fbx"
UE = json.load(open(REPO + "/sources/armor/techlimb_ue.json"))
TEMPLATE = json.load(open(REPO + "/SkeldarAnim/assets/manny_skeleton_template.json"))
OUT = REPO + "/SkeldarAnim/assets/Armor/Tech_Limb.fbx"
BONE = UE["socket"]


def refuse(ok, text):
    print(("ok    " if ok else "FAIL  ") + text)
    sys.stdout.flush()
    if not ok:
        raise SystemExit(1)


def mesh_points(transform):
    sel = om.MSelectionList()
    sel.add(transform)
    fn = om.MFnMesh(sel.getDagPath(0))
    return np.array([[p.x, p.y, p.z] for p in fn.getPoints(om.MSpace.kWorld)])


def import_one():
    cmds.file(new=True, force=True)
    mel.eval("FBXResetImport; FBXImportMode -v add;")
    before = set(cmds.ls(long=True) or [])
    mel.eval('FBXImport -f "%s";' % SOURCE)
    meshes = [cmds.listRelatives(m, parent=True, fullPath=True)[0]
              for m in cmds.ls(type="mesh", long=True, noIntermediate=True) or []]
    refuse(len(meshes) == 1, "one mesh in Unreal's FBX (%d)" % len(meshes))
    node = meshes[0]
    while cmds.listRelatives(node, parent=True, fullPath=True):
        node = cmds.parent(node, world=True)[0]
        node = cmds.ls(node, long=True)[0]
    cmds.makeIdentity(node, apply=True, translate=True, rotate=True, scale=True)
    junk = [n for n in cmds.ls(assemblies=True, long=True) or []
            if n != node and n not in before and cmds.objExists(n)]
    if junk:
        cmds.delete(junk)
    return node


# 1. Unreal component space -> Maya world, from the bones both skeletons carry. The helper bones
#    are left out: Atone's weapon_r / weapon_l / camera_root / camera_bone stand elsewhere (5.7, 2.4,
#    4.0, 1.0 cm, measured) -- every deforming bone agrees, calf_l to Manny's own 0.07.
joints = dict((j["name"], j) for j in TEMPLATE["joints"])
shared = sorted(n for n in UE["bones"] if n in joints and not n.startswith(("weapon_", "camera_", "ik_")))
M, res = axes.ue_to_maya([UE["bones"][n]["t"] for n in shared],
                         [joints[n]["world_position"] for n in shared])
refuse(res < 0.1, "M over %d deforming bones, worst bone %.4f cm: rows %s"
       % (len(shared), res, M.astype(int).tolist()))

# 2. the bone's axes: Unreal's -> Maya's
A, t = axes.row_world(joints[BONE]["world_matrix"])
ub = UE["bones"][BONE]
R_b = np.array([ub["x"], ub["y"], ub["z"]]).T
N, dev = axes.round_to_permutation(A.T @ M @ R_b)
refuse(dev < 1e-3, "N (%s axes, Unreal -> Maya) a signed permutation to %.2e: rows %s"
       % (BONE, dev, N.astype(int).tolist()))
bone_off = float(np.linalg.norm(M @ np.array(ub["t"]) - t))
refuse(bone_off < 0.01, "%s stands where Unreal's does to %.5f cm" % (BONE, bone_off))

# 3. the target points, and the two routes agreeing
q = np.array(UE["verts_bone"]) @ N.T
world_q = q @ A.T + t
world_ue = np.array(UE["verts_cs"]) @ M.T
both = float(np.linalg.norm(world_q - world_ue, axis=1).max())
refuse(both < 0.01, "bone-local route against component space: %.5f cm" % both)

# 4. the FBX's points matched to Unreal's, and the similarity onto q
node = import_one()
pts = mesh_points(node)
P, worst = axes.best_map(pts, np.array(UE["verts_mesh"]))
refuse(worst < 1e-3, "the FBX conversion is the signed permutation %s, %d points to %.2e cm"
       % (P.astype(int).tolist(), len(pts), worst))
index, _dist = axes.nearest(pts @ P.T, np.array(UE["verts_mesh"]))
s, R, tr, fit = axes.similarity(pts, q[index])
refuse(fit < 1e-3 and np.linalg.det(R) > 0,
       "similarity onto q: scale %.6f (BP %.6f), worst %.2e cm" % (s, UE["placement"]["scale"][0], fit))
X = np.eye(4)
X[:3, :3] = (s * R).T
X[3, :3] = tr
cmds.xform(node, matrix=[float(v) for v in X.flatten()])
cmds.makeIdentity(node, apply=True, translate=True, rotate=True, scale=True)
cmds.xform(node, pivots=(0, 0, 0))
now = mesh_points(node)
placed = float(np.linalg.norm(now - q[index], axis=1).max())
refuse(placed < 1e-3, "the points on q after the freeze: %.2e cm" % placed)

# 5. named, one plain lambert, exported
node = cmds.ls(cmds.rename(node, "TechLimbMesh"), long=True)[0]
mat = cmds.shadingNode("lambert", asShader=True, name="TechLimb_Mat")
cmds.setAttr(mat + ".color", *UE["colour"], type="double3")
sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name="TechLimb_MatSG")
cmds.connectAttr(mat + ".outColor", sg + ".surfaceShader")
cmds.sets(node, edit=True, forceElement=sg)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
cmds.select(node)
mel.eval("FBXResetExport; FBXExportInAscii -v false; FBXExportSmoothingGroups -v true; "
         "FBXExportCameras -v false; FBXExportLights -v false;")
mel.eval('FBXExport -f "%s" -s;' % OUT)

# 6. read back, the way an Equip reads it
cmds.file(new=True, force=True)
mel.eval("FBXResetImport; FBXImportMode -v add;")
mel.eval('FBXImport -f "%s";' % OUT)
meshes = cmds.ls(type="mesh", long=True, noIntermediate=True) or []
refuse(len(meshes) == 1, "read back: one mesh (%d)" % len(meshes))
back = cmds.listRelatives(meshes[0], parent=True, fullPath=True)[0]
ident = np.abs(np.array(cmds.xform(back, query=True, matrix=True, worldSpace=True)) -
               np.eye(4).flatten()).max()
again = mesh_points(back)
_i, d = axes.nearest(again, q)
refuse(ident < 1e-9 and float(d.max()) < 1e-3,
       "read back: %s at identity (%.1e), every point on q to %.2e cm, %.1f KB"
       % (back.split("|")[-1], ident, float(d.max()), os.path.getsize(OUT) / 1e3))
print("bbox in %s space: %s .. %s" % (BONE, np.round(again.min(axis=0), 2).tolist(),
                                     np.round(again.max(axis=0), 2).tolist()))
