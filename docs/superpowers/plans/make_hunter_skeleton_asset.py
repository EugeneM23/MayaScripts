"""Build SkeldarAnim/assets/Hunter_Skeleton.ma -- the Hunter WITHOUT its rig -- from Hunter_Rig.ma.

    mayapy make_hunter_skeleton_asset.py [<Hunter_Rig.ma>] [<out .ma>]

2026-09-24, the animator: «добавим возможность загрузить не только риг хантера, а и чистый
скелет».  The Manny has had both rows since 2026-09-07; this is the Hunter's second.

mayapy STANDALONE.  From the shipped rig, in this order:

1. every bone's world matrix recorded, every constraint on the skeleton deleted, each bone's
   local transform written back from its world matrix (parents first) -- the bind pose held
   exactly, not whatever the channels last read;
2. the meshes and the props out of `Group|Geometry` into `|Hunter` at world level (the props
   keep their constraint to weapon_test: they are the skeleton's, not the rig's);
3. `|Group` deleted, then every node nothing we keep depends on: the kept set is the DAG under
   `|root` and `|Hunter`, the meshes' and the props' whole history (skinClusters, Orig shapes,
   groupParts, the bind pose), their shading networks, the skeleton's display layer and
   Maya's default nodes; AdvancedSkeleton's utility network, its sets, its driven-key curves
   go, whatever their type;
4. saved as mayaAscii, Maya's configuration script nodes cut from the text, and the file
   refused if anything of the rig or anything banned survived in it.
"""
import os
import sys

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds
import maya.api.OpenMaya as om

for p in ("matrixNodes", "quatNodes"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.abspath(os.path.join(HERE, "..", "..", "..", "SkeldarAnim", "assets"))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ASSETS, "Hunter_Rig.ma")
OUT = (sys.argv[2] if len(sys.argv) > 2 else os.path.join(ASSETS, "Hunter_Skeleton.ma")).replace("\\", "/")
BANNED = ('createNode transform -n "Group"', 'createNode objectSet -n "ControlSet"', "FitSkeleton",
          "MoCapConstraints", "skeldarRetarget", "SKM_Manny_Simple", "Hunter_Sword", "Hunter_Props",
          "weapon_test", "createNode script", "vaccine", "breed_gene")

cmds.file(SRC, open=True, force=True, executeScriptNodes=False)


def wm(n):
    return om.MMatrix(cmds.getAttr(n + ".worldMatrix[0]"))


def uid(n):
    return cmds.ls(n, uuid=True)[0]


def path(u):
    return cmds.ls(u, long=True)[0]


root = cmds.ls("|root", type="joint", long=True)[0]
joints = sorted([root] + cmds.listRelatives(root, allDescendents=True, type="joint", fullPath=True), key=lambda j: j.count("|"))
world = [(uid(j), wm(j)) for j in joints]
skins = [sc for sc in cmds.ls(type="skinCluster")]

# 1. the bones free of the rig, held at the bind
cons = [c for c in cmds.listRelatives(root, allDescendents=True, type="constraint", fullPath=True) or []]
cmds.delete(cons)
for u, m in world:
    j = path(u)
    for a in ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"):
        cmds.setAttr(j + "." + a, lock=False)
    cmds.xform(j, worldSpace=True, matrix=list(m))
drift = max(max(abs(a - b) for a, b in zip(list(m), list(wm(path(u))))) for u, m in world)

# 2. the meshes and the props to |Hunter
geo = cmds.ls("|Group|Geometry", long=True)[0]
kids = cmds.listRelatives(geo, children=True, fullPath=True) or []
kid_ids = [uid(k) for k in kids]
holder = cmds.createNode("transform", name="Hunter")
for u in kid_ids:
    cmds.parent(path(u), "|Hunter")

# 3. the rig, and everything nothing kept depends on
cmds.delete("|Group")
keep_dag = set(cmds.ls("|root", "|Hunter", dag=True, long=True))
meshes = cmds.ls("|Hunter", dag=True, type="mesh", long=True)
keep = set(keep_dag)
for m in meshes:
    keep.update(cmds.ls(cmds.listHistory(m) or [], long=True))
    for sg in cmds.listConnections(m, type="shadingEngine") or []:
        keep.add(sg)
        keep.update(cmds.ls(cmds.listHistory(sg) or [], long=True))
        keep.update(cmds.ls(cmds.listConnections(sg, type="materialInfo") or []))
for c in cmds.ls("|Hunter", dag=True, type="constraint", long=True):
    keep.update(cmds.ls(cmds.listHistory(c) or [], long=True))
keep.update(cmds.ls(type="dagPose"))
keep.update(l for l in cmds.ls(type="displayLayer") if l == "defaultLayer" or cmds.editDisplayLayerMembers(l, q=True))
default = set(cmds.ls(defaultNodes=True)) | set(cmds.ls(readOnly=True)) | set(cmds.ls(cameras=True, long=True))
default |= set(cmds.listRelatives(cmds.ls(cameras=True, long=True), parent=True, fullPath=True) or [])
doomed = []
for n in cmds.ls(long=True):
    if n in keep or n in default or cmds.lockNode(n, q=True, lock=True)[0] and n in default:
        continue
    t = cmds.nodeType(n)
    if t in ("displayLayerManager", "renderLayerManager", "renderLayer", "lightLinker", "nodeGraphEditorInfo",
             "hyperGraphInfo", "hyperLayout", "objectSet") and n in ("defaultObjectSet", "defaultLightSet"):
        continue
    if t in ("displayLayerManager", "renderLayerManager", "renderLayer", "lightLinker", "shapeEditorManager",
             "poseInterpolatorManager", "nodeGraphEditorInfo", "hyperGraphInfo", "time", "script"):
        continue
    doomed.append(n)
kinds = {}
for n in doomed:
    kinds[cmds.nodeType(n)] = kinds.get(cmds.nodeType(n), 0) + 1
for n in doomed:
    if cmds.objExists(n):
        try:
            cmds.lockNode(n, lock=False)
            cmds.delete(n)
        except Exception as exc:
            print("kept (could not delete)", n, exc)
print("deleted %d nodes by type: %s" % (len(doomed), sorted(kinds.items(), key=lambda kv: -kv[1])[:25]))
cmds.delete(cmds.ls(type="script") or [])

# what must be true
root = cmds.ls("|root", type="joint", long=True)[0]
assert len(cmds.listRelatives(root, allDescendents=True, type="joint")) == 90, "the Hunter skeleton (weapon_l added 2026-09-24)"
assert not cmds.listRelatives(root, allDescendents=True, type="constraint"), "constraints left on the skeleton"
worst = 0.0
for sc in cmds.ls(type="skinCluster"):
    for idx in cmds.getAttr(sc + ".matrix", multiIndices=True) or []:
        src = cmds.listConnections("%s.matrix[%d]" % (sc, idx), s=True, d=False)
        if src:
            p = om.MMatrix(cmds.getAttr("%s.bindPreMatrix[%d]" % (sc, idx))) * wm(src[0])
            worst = max(worst, max(abs(p.getElement(r, c) - (r == c)) for r in range(4) for c in range(4)))
print("bones re-seated from their world matrices: drift %.9f; %d skins, |BPM*WM - I| worst %.2e" % (drift, len(cmds.ls(type="skinCluster")), worst))
assert worst < 1e-4 and len(cmds.ls(type="skinCluster")) == 5, "the skin is not at its bind"
print("assemblies:", cmds.ls(assemblies=True), "| Hunter:", cmds.listRelatives("|Hunter", children=True))
print("left by type:", sorted(set(cmds.nodeType(n) for n in cmds.ls() if n not in default)))

cmds.file(rename=OUT)
cmds.file(save=True, type="mayaAscii", force=True)
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
bad = []
with open(OUT, encoding="utf-8", errors="replace") as fh:
    for n, line in enumerate(fh, 1):
        for word in BANNED:
            if word in line:
                bad.append((n, word))
if bad:
    os.remove(OUT)
    raise RuntimeError("banned content in the skeleton asset, deleted: %s" % bad[:10])
print("script nodes cut: %d; saved %s (%.1f MB)" % (cut, OUT, os.path.getsize(OUT) / 1e6))
