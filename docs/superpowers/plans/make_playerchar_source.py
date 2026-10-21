"""Write sources/playerchar/Playerchar_Proxy.mb: the draft character's meshes on a bare game skeleton.

    mayapy make_playerchar_source.py [<Playerchar_Proxy.mb>]

mayapy STANDALONE, 2026-10-21 (spec: docs/superpowers/specs/2026-10-21-playerchar-and-clothing-design.md).
The animator's scene (`Downloads/T_Playerchar_proxy/Playerchar_Proxy.mb`, 69 MB) is the draft body and
its outfit skinned onto a stock Manny_Rig added through Add Character. Copied to a temp folder and
opened there with script nodes NOT executed (the original is never opened in place), this keeps what
the Playerchar assets are built from and nothing of the rig:

1. the game skeleton (`Manny_Rig:root`, 93 joints) taken off the rig: every bone's world matrix
   recorded, its constraints deleted, its local transform written back from that matrix (parents first)
   -- the bind held exactly -- and put at world level;
2. Manny's own meshes (`SKM_Manny_Simple`), the rig (`Group`) and the character group deleted, then
   every node nothing kept depends on (the kept set: the DAG under `|root` and `|MESH`, the meshes'
   whole history, Maya's default nodes);
3. the materials and textures deleted (they named this machine's Downloads and an `E:` drive): every
   mesh on `initialShadingGroup` -- the atlas is copied beside the file as `T_Playerchar_proxy_bc.jpg`;
4. the namespace merged into the root (plain bone names), saved as mayaBinary -- in git, never in a build.

Refuses (raises) when a mesh is not where the original's skin puts it, or a skin is off its bind.
"""
import os
import shutil
import sys
import tempfile

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
ORIGINAL = sys.argv[1] if len(sys.argv) > 1 else "C:/Users/MY PC/Downloads/T_Playerchar_proxy/Playerchar_Proxy.mb"
ATLAS = os.path.join(os.path.dirname(ORIGINAL), "T_Playerchar_proxy_bc.jpg")
OUT_DIR = os.path.join(REPO, "sources", "playerchar")
OUT = os.path.join(OUT_DIR, "Playerchar_Proxy.mb").replace("\\", "/")
NS = "Manny_Rig"
MESHES = ("Body", "Pants", "Shield", "TorsoCloth_", "Fabrics", "chains_Beard", "chains_Legs",
          "chains_Shoulders", "polySurface9")

for plugin in ("matrixNodes", "quatNodes", "fbxmaya"):
    cmds.loadPlugin(plugin, quiet=True)
work = tempfile.mkdtemp(prefix="playerchar_src_")
copy = os.path.join(work, os.path.basename(ORIGINAL)).replace("\\", "/")
shutil.copy(ORIGINAL, copy)
os.chdir(work)
cmds.file(copy, open=True, force=True, executeScriptNodes=False)


def wm(node):
    return om.MMatrix(cmds.getAttr(node + ".worldMatrix[0]"))


def uid(node):
    return cmds.ls(node, uuid=True)[0]


def path(u):
    return cmds.ls(u, long=True)[0]


def mesh_points(transform):
    sel = om.MSelectionList()
    sel.add(transform)
    return om.MFnMesh(sel.getDagPath(0)).getPoints(om.MSpace.kWorld)


def bind_error(skin):
    worst = 0.0
    for idx in cmds.getAttr(skin + ".matrix", multiIndices=True) or []:
        src = cmds.listConnections("%s.matrix[%d]" % (skin, idx), s=True, d=False)
        if src:
            m = om.MMatrix(cmds.getAttr("%s.bindPreMatrix[%d]" % (skin, idx))) * wm(src[0])
            worst = max(worst, max(abs(m.getElement(r, c) - (r == c)) for r in range(4) for c in range(4)))
    return worst


# what the original's skin shows, to compare at the end
meshes = dict((name, cmds.ls(name, type="transform", long=True)) for name in MESHES)
assert all(len(v) == 1 for v in meshes.values()), meshes
mesh_ids = dict((name, uid(v[0])) for name, v in meshes.items())
before = dict((name, mesh_points(path(u))) for name, u in mesh_ids.items())

# 1. the game skeleton off the rig
root = cmds.ls(NS + ":root", type="joint", long=True)
assert len(root) == 1, root
root = root[0]
joints = sorted([root] + cmds.listRelatives(root, allDescendents=True, type="joint", fullPath=True),
                key=lambda j: j.count("|"))
assert len(joints) == 93, len(joints)
world = [(uid(j), wm(j)) for j in joints]
root_id = uid(root)
cmds.delete(cmds.listRelatives(root, allDescendents=True, type="constraint", fullPath=True) or [])
cmds.parent(root, world=True)
for u, m in world:
    j = path(u)
    for a in ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"):
        cmds.setAttr(j + "." + a, lock=False)
    for a in ("rotateAxis", "jointOrient"):
        pass
    cmds.xform(j, worldSpace=True, matrix=list(m))
drift = max(max(abs(a - b) for a, b in zip(list(m), list(wm(path(u))))) for u, m in world)
print("game skeleton off the rig: 93 joints re-seated, drift %.2e" % drift)
assert drift < 1e-6

# 2. Manny's meshes, the rig, the character group; then what nothing kept needs
for gone in cmds.ls(NS + ":SKM_Manny_Simple", NS + ":Group", NS + ":materialXStack1", "Manny_Rig_Character",
                    long=True) or []:
    if cmds.objExists(gone):
        cmds.delete(gone)
keep_dag = set(cmds.ls(path(root_id), "|MESH", dag=True, long=True))
keep = set(keep_dag)
for shape in cmds.ls("|MESH", dag=True, type="mesh", long=True):
    keep.update(cmds.ls(cmds.listHistory(shape) or [], long=True))
default = set(cmds.ls(defaultNodes=True)) | set(cmds.ls(readOnly=True)) | set(cmds.ls(cameras=True, long=True))
default |= set(cmds.listRelatives(cmds.ls(cameras=True, long=True), parent=True, fullPath=True) or [])
SKIP = ("displayLayerManager", "renderLayerManager", "renderLayer", "lightLinker", "shapeEditorManager",
        "poseInterpolatorManager", "nodeGraphEditorInfo", "hyperGraphInfo", "time")
doomed = [n for n in cmds.ls(long=True) if n not in keep and n not in default and cmds.nodeType(n) not in SKIP]
for n in doomed:
    if cmds.objExists(n):
        try:
            cmds.lockNode(n, lock=False)
            cmds.delete(n)
        except Exception as exc:                                  # noqa: BLE001
            print("kept (could not delete)", n, exc)
cmds.delete(cmds.ls(type="script") or [])

# 3. the materials: every mesh on the default shader
for shape in cmds.ls("|MESH", dag=True, type="mesh", long=True, noIntermediate=True):
    cmds.sets(shape, edit=True, forceElement="initialShadingGroup")
for n in cmds.ls(materials=True) + cmds.ls(textures=True) + cmds.ls(type="shadingEngine") + \
        cmds.ls(type="place2dTexture") + cmds.ls(type="materialInfo"):
    if n in default or n in ("lambert1", "initialShadingGroup", "initialParticleSE", "particleCloud1",
                             "standardSurface1", "openPBR_shader1"):
        continue
    if cmds.objExists(n):
        cmds.delete(n)

# 4. plain names
for name in cmds.namespaceInfo(":", listOnlyNamespaces=True) or []:
    if name not in ("UI", "shared"):
        cmds.namespace(removeNamespace=name, mergeNamespaceWithRoot=True)
for p in cmds.ls(type="dagPose"):
    if not cmds.dagPose(p, q=True, members=True):
        cmds.delete(p)

# what must be true
assert cmds.ls(assemblies=True) == ["persp", "top", "front", "side", "MESH", "root"] or \
    sorted(cmds.ls(assemblies=True)) == sorted(["persp", "top", "front", "side", "MESH", "root"]), cmds.ls(assemblies=True)
assert len(cmds.ls("|root", dag=True, type="joint")) == 93
worst_bind = max(bind_error(sc) for sc in cmds.ls(type="skinCluster"))
moved = 0.0
for name, u in mesh_ids.items():
    now = mesh_points(path(u))
    moved = max(moved, max(now[i].distanceTo(before[name][i]) for i in range(len(now))))
print("%d skins, off their bind %.2e; every vertex where the original showed it to %.2e cm"
      % (len(cmds.ls(type="skinCluster")), worst_bind, moved))
assert worst_bind < 1e-4 and moved < 1e-4
print("assemblies:", cmds.ls(assemblies=True))
print("left by type:", sorted(set(cmds.nodeType(n) for n in cmds.ls() if n not in default)))

if not os.path.isdir(OUT_DIR):
    os.makedirs(OUT_DIR)
cmds.file(rename=OUT)
cmds.file(save=True, type="mayaBinary", force=True)
shutil.copy(ATLAS, os.path.join(OUT_DIR, "T_Playerchar_proxy_bc.jpg"))
print("saved %s (%.1f MB) and the atlas" % (OUT, os.path.getsize(OUT) / 1e6))
