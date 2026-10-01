"""SkeldarAnim/assets/Armor/Tech_Limb_Shield.ma out of what export_techlimb_shield_from_unreal.py wrote.

    mayapy make_techlimb_shield_asset.py

mayapy STANDALONE (2026-10-01, the evening; spec docs/superpowers/specs/2026-10-01-armor-techlimb-design.md,
its addendum). The game's skeletal shield, posed as the game poses it in Block Idle, in a group that
STANDS FOR `lowerarm_l`'s space: equipped, the group sits at identity in the bone's armor space and the
shield is where Atone puts it.

Measured, never assumed:
1. N, Unreal `lowerarm_l` axes -> Maya `lowerarm_l` axes (the shield's component space IS the bone's: the
   test techlimb puts the skeletal mesh at identity on the actor root, snapped onto the bone): A^T M R_b
   over Manny's bind and SK_Mannequin_proto's reference (sources/armor/techlimb_ue.json), a signed
   permutation.
2. G, Unreal component space -> where Maya's FBX import put the shield: the signed permutation fitting
   the imported joints onto Unreal's reference component positions.
3. Each joint's MOTION from the reference to the game's Block Idle (Root at its REFERENCE -- the clips
   force root lock -- the rest from the clip), D = T_idle T_ref^-1 in Unreal's component space, mapped
   into lowerarm_l space by N and applied to where the import put that joint (mapped by N G^-1). The
   skin sees only that motion, so no joint's own axis convention enters -- the FBX's are not one
   convention (Root and Main sit under the importer's wrapper, the rim joints carry a 90 deg rotate of
   their own). Written root-down as translate + rotate, jointOrient and rotateAxis zero. The skinned mesh stays bound where the import put it, its transform not
inheriting (the skin alone moves it, never twice). Refuses on any residual over the bounds below; the
asset is read back and every joint checked again.
"""
import json
import os
import re
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
SOURCE = REPO + "/sources/armor/SKM_Techlimb_Shield.fbx"
SHIELD = json.load(open(REPO + "/sources/armor/techlimb_shield_ue.json"))
LIMB = json.load(open(REPO + "/sources/armor/techlimb_ue.json"))
TEMPLATE = json.load(open(REPO + "/SkeldarAnim/assets/manny_skeleton_template.json"))
OUT = REPO + "/SkeldarAnim/assets/Armor/Tech_Limb_Shield.ma"
GROUP = "TechLimbShield"
BONES = SHIELD["bones"]


def refuse(ok, text):
    print(("ok    " if ok else "FAIL  ") + text)
    sys.stdout.flush()
    if not ok:
        raise SystemExit(1)


def axes_of(frame):
    return np.array([frame["x"], frame["y"], frame["z"]]).T


def world(node):
    return np.array(cmds.xform(node, query=True, worldSpace=True, matrix=True)).reshape(4, 4)


def depth(name):
    d, n = 0, name
    while BONES[n]["parent"]:
        n, d = BONES[n]["parent"], d + 1
    return d


# 1. N, as for the plate
joints_t = dict((j["name"], j) for j in TEMPLATE["joints"])
shared = sorted(n for n in LIMB["bones"] if n in joints_t and not n.startswith(("weapon_", "camera_", "ik_")))
M, res = axes.ue_to_maya([LIMB["bones"][n]["t"] for n in shared], [joints_t[n]["world_position"] for n in shared])
A_low, _t = axes.row_world(joints_t[LIMB["socket"]]["world_matrix"])
ub = LIMB["bones"][LIMB["socket"]]
N, dev = axes.round_to_permutation(A_low.T @ M @ np.array([ub["x"], ub["y"], ub["z"]]).T)
refuse(res < 0.1 and dev < 1e-3, "N (lowerarm_l, Unreal -> Maya) rows %s, M over %d bones %.4f cm"
       % (N.astype(int).tolist(), len(shared), res))

# 2. the import, and G
cmds.file(new=True, force=True)
mel.eval("FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;")
mel.eval('FBXImport -f "%s";' % SOURCE)
joints = dict((j.split("|")[-1], j) for j in cmds.ls(type="joint", long=True) or [])
refuse(sorted(joints) == sorted(BONES), "the FBX's joints are the skeleton's %d bones" % len(BONES))
meshes = [cmds.listRelatives(m, parent=True, fullPath=True)[0]
          for m in cmds.ls(type="mesh", long=True, noIntermediate=True) or []]
refuse(len(meshes) == 1, "one mesh (%d)" % len(meshes))
mesh = meshes[0]
skins = cmds.ls(cmds.listHistory(mesh) or [], type="skinCluster") or []
refuse(len(skins) == 1, "one skinCluster on it")
names = sorted(BONES, key=depth)
imp = dict((n, world(joints[n])) for n in names)
G, gres = axes.ue_to_maya([BONES[n]["ref_cs"]["t"] for n in names], [imp[n][3, :3] for n in names])
refuse(gres < 1e-3 and abs(np.linalg.det(N @ np.linalg.inv(G)) - 1) < 1e-9,
       "G (Unreal component -> the import) rows %s, joints to %.2e cm; N G^-1 a proper rotation"
       % (G.astype(int).tolist(), gres))

# 3. every joint's target: the import's world mapped into lowerarm_l space, then Unreal's own motion
R0 = N @ np.linalg.inv(G)
target = {}
for n in names:
    Wq = np.eye(4)
    Wq[:3, :3] = imp[n][:3, :3] @ R0.T
    Wq[3, :3] = imp[n][3, :3] @ R0.T
    A_r, t_r = axes_of(BONES[n]["ref_cs"]), np.array(BONES[n]["ref_cs"]["t"])
    A_i, t_i = axes_of(BONES[n]["idle_cs"]), np.array(BONES[n]["idle_cs"]["t"])
    turn = A_i @ np.linalg.inv(A_r)
    D = np.eye(4)
    D[:3, :3] = (N @ turn @ np.linalg.inv(N)).T
    D[3, :3] = N @ (t_i - turn @ t_r)
    target[n] = Wq @ D
on_ue = max(float(np.linalg.norm(target[n][3, :3] - N @ np.array(BONES[n]["idle_cs"]["t"]))) for n in names)
refuse(on_ue < 1e-4, "every joint's target where the game puts it (N t_idle) to %.2e cm" % on_ue)

# 4. the group standing for lowerarm_l's space; the skinned mesh outside the inherited chain
group = cmds.ls(cmds.createNode("transform", name=GROUP), long=True)[0]
root = cmds.ls(cmds.parent(joints["Root"], group)[0], long=True)[0]
geom = np.array(cmds.getAttr(skins[0] + ".geomMatrix")).reshape(4, 4)
mesh_world = world(mesh)
# the FBX importer locks a skinned mesh's transform, and a locked plug makes the re-parent's
# compensation a silent no-op (CLAUDE.md trap 51): unlocked for good, nothing should key it
for attr in ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"):
    cmds.setAttr(mesh + "." + attr, lock=False)
if cmds.listRelatives(mesh, parent=True):
    mesh = cmds.ls(cmds.parent(mesh, world=True)[0], long=True)[0]
mesh = cmds.ls(cmds.parent(mesh, group)[0], long=True)[0]
cmds.setAttr(mesh + ".inheritsTransform", False)
refuse(float(np.abs(world(mesh) - mesh_world).max()) < 1e-9 and float(np.abs(world(mesh) - geom).max()) < 1e-6,
       "the mesh in the group, not inheriting, still at its bind matrix")
junk = [n for n in cmds.ls(assemblies=True, long=True) or [] if n != group and not n.startswith("|persp")
        and n not in ("|top", "|front", "|side")]
if junk:
    cmds.delete(junk)

# 5. every joint posed at the game's Block Idle, root-down
joints = dict((j.split("|")[-1], j) for j in cmds.ls(type="joint", long=True) or [])
for n in names:
    j = joints[n]
    parent = BONES[n]["parent"]
    local = target[n] @ np.linalg.inv(target[parent]) if parent else target[n]
    tm = om.MTransformationMatrix(om.MMatrix([float(v) for v in local.flatten()]))
    for attr in ("jointOrient", "rotateAxis"):
        cmds.setAttr(j + "." + attr, 0, 0, 0, type="double3")
    cmds.setAttr(j + ".rotateOrder", 0)
    euler = tm.rotation()
    cmds.setAttr(j + ".rotate", *[om.MAngle(a).asDegrees() for a in (euler.x, euler.y, euler.z)], type="double3")
    cmds.setAttr(j + ".translate", *tm.translation(om.MSpace.kTransform), type="double3")
    cmds.setAttr(j + ".scale", 1, 1, 1, type="double3")
posed = max(float(np.abs(world(joints[n]) - target[n]).max()) for n in names)
refuse(posed < 1e-6, "all %d joints on the game's Block Idle in lowerarm_l space to %.2e" % (len(names), posed))
main = world(joints["Main"])[3, :3]
print("      Main stands at %s in lowerarm_l space (%.1f cm from the elbow)"
      % (np.round(main, 2).tolist(), float(np.linalg.norm(main))))

# 6. a plain material, named; then exported and read back
mat = cmds.shadingNode("lambert", asShader=True, name="TechLimbShield_Mat")
sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name="TechLimbShield_MatSG")
cmds.connectAttr(mat + ".outColor", sg + ".surfaceShader")
cmds.sets(mesh, edit=True, forceElement=sg)
mesh = cmds.ls(cmds.rename(mesh, "TechLimbShieldMesh"), long=True)[0]
os.makedirs(os.path.dirname(OUT), exist_ok=True)
cmds.select(group)
cmds.file(OUT, force=True, exportSelected=True, type="mayaAscii", preserveReferences=False,
          constructionHistory=True, channels=True, shader=True, expressions=False)
text = open(OUT, encoding="utf-8", errors="replace").read()
cut = re.sub(r'createNode script -n "(uiConfigurationScriptNode|sceneConfigurationScriptNode)";\n(\t[^\n]*\n)*', "", text)
banned = [w for w in ("C:/Users", "Desktop", "Downloads", "createNode script", "vaccine", "breed_gene")
          if w in cut]
refuse(not banned, "no path of this machine, no script node in the asset (%s)" % banned)
if cut != text:
    open(OUT, "w", encoding="utf-8", newline="\n").write(cut)

cmds.file(new=True, force=True)
cmds.file(OUT, i=True, type="mayaAscii", ignoreVersion=True)
back = dict((j.split("|")[-1], j) for j in cmds.ls(type="joint", long=True) or [])
again = max(float(np.abs(world(back[n]) - target[n]).max()) for n in names)
mesh_back = cmds.ls("TechLimbShieldMesh", long=True)
refuse(again < 1e-6 and len(mesh_back) == 1 and not cmds.getAttr(mesh_back[0] + ".inheritsTransform"),
       "read back: %d joints on the game's Block Idle to %.2e, the mesh not inheriting, %.1f KB"
       % (len(back), again, os.path.getsize(OUT) / 1e3))
pts = np.array([[p.x, p.y, p.z] for p in om.MFnMesh(om.MSelectionList().add(mesh_back[0]).getDagPath(0))
                .getPoints(om.MSpace.kWorld)])
print("      the deformed shield in lowerarm_l space: %s .. %s" % (np.round(pts.min(axis=0), 1).tolist(),
                                                               np.round(pts.max(axis=0), 1).tolist()))
