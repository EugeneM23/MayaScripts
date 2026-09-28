"""The shipped Creep assets in the layout of the Creep's own FBX: `Armature` over `root`, in place.

    mayapy make_creep_armature_layout.py [<asset .ma> ...]      (both Creep assets by default)

2026-09-28, the animator: «При добавлении крипа у нас добавляется не последняя версия скелета.
Последняя версия скелета вот тут C:\\!!!Work\\Animations\\Rigs\\Characters\\Creep_Skeleton.fbx» --
asked what differs: «Структура сцены», and why: «Как в файле, единообразно», «И риг крипа тоже».
Measured first: that FBX (export_creep_skeleton_fbx.py's, from assets/Creep_Skeleton.ma) holds
the same 91 bones in the same pose (0.0 cm / 0.0 deg), the same five meshes (points to 0.0001 cm,
uvs 0.0), the same weights (to the FBX's 0.003) -- and a different LAYOUT: Cascadeur's, the
skeleton under a Null `Armature` turned -90 X with `root` at no orientation of its own, the meshes
at the top of the scene beside it. So both assets take that layout:

- `Armature`, a transform at the origin turned -90 X, at the top of the scene; `root` under it
  with the jointOrient `fbxlayout.jo_after` of its own (the -90 moved onto the Null: what is left
  is the FBX's own (2e-5, -4e-5, -3e-5) deg) and, on the clean skeleton, its translate in the
  Null's space (`fbxlayout.swizzled`); the rig's root rides Main by a parentConstraint, which
  re-solves under the Null by itself;
- the clean skeleton's five meshes out of their `|Creep` group to the top, beside `Armature`, as
  the FBX has them (the group goes); the rig's stay in its `Group|Geometry`;
- the bind pose saved again WHOLE over every joint and the Null (trap 79: the exporter drops a pose
  whose chain misses a member -- «Unable to find the bind pose for : / Creep» the day the Null was
  left out), every skin moved onto it.

The world matrix of every joint and every vertex of every mesh is checked unchanged (at the
build pose and, on the rig, under a pose of its Main and RootX_M), the skins at their bind; then
saved as .ma in place, Maya's own script nodes cut out of the text (trap 74), banned words
refused. Idempotent: a root already under its `Armature` is left where it stands.
"""
import os
import sys

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.normpath(os.path.join(HERE, "..", "..", "..", "SkeldarAnim"))
sys.path.insert(0, PLUGIN)
from maya_uebridge import fbxlayout  # noqa: E402

ASSETS = [a.replace("\\", "/") for a in sys.argv[1:]] or [
    os.path.join(PLUGIN, "assets", n).replace("\\", "/") for n in ("Creep_Rig.ma", "Creep_Skeleton.ma")]
BANNED = ("createNode script", "vaccine", "breed_gene", "rpHold_", "cascadeurLayoutNegate")
for p in ("matrixNodes", "quatNodes", "fbxmaya"):
    cmds.loadPlugin(p, quiet=True)


def wm(n):
    return om.MMatrix(cmds.getAttr(n + ".worldMatrix[0]"))


def mdiff(a, b):
    return max(abs(x - y) for x, y in zip(list(a), list(b)))


def meshes():
    out = {}
    for s in cmds.ls(type="mesh", long=True, noIntermediate=True):
        sel = om.MSelectionList()
        sel.add(s)
        out[cmds.ls(s, uuid=True)[0]] = om.MFnMesh(sel.getDagPath(0)).getPoints(om.MSpace.kWorld)
    return out


def snapshot():
    joints = dict((cmds.ls(j, uuid=True)[0], wm(j)) for j in cmds.ls(type="joint", long=True))
    return joints, meshes()


def drift(before):
    joints, pts = before
    dj = max(mdiff(wm(cmds.ls(u, long=True)[0]), m) for u, m in joints.items())
    now = meshes()
    dv = max(max(a.distanceTo(b) for a, b in zip(pts[u], now[u])) for u in pts)
    return dj, dv


def bind_error():
    worst = 0.0
    for sc in cmds.ls(type="skinCluster"):
        for idx in cmds.getAttr(sc + ".matrix", multiIndices=True) or []:
            src = cmds.listConnections("%s.matrix[%d]" % (sc, idx), s=True, d=False)
            if src:
                m = om.MMatrix(cmds.getAttr("%s.bindPreMatrix[%d]" % (sc, idx))) * wm(src[0])
                worst = max(worst, mdiff(m, om.MMatrix()))
    return worst


def unlock(node):
    locked = [a for a in ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz") if cmds.getAttr(node + "." + a, lock=True)]
    for a in locked:
        cmds.setAttr(node + "." + a, lock=False)
    return locked


def whole_bind_pose(joints, null):
    skins = cmds.ls(type="skinCluster") or []
    old = set(p for sc in skins for p in cmds.listConnections(sc + ".bindPose", s=True, d=False) or []
              if cmds.objectType(p) == "dagPose")
    old.update(cmds.ls(type="dagPose"))
    new = cmds.dagPose(joints + [null], save=True, bindPose=True, name="skeldarBindPose_new")
    new = new[0] if isinstance(new, (list, tuple)) else new
    keep = set(cmds.ls(joints + [null], long=True))
    strays = [m for m in cmds.ls(cmds.dagPose(new, q=True, members=True) or [], long=True) if m not in keep]
    if strays:
        cmds.dagPose(strays, remove=True, name=new)
    for sc in skins:
        cmds.connectAttr(new + ".message", sc + ".bindPose", force=True)
    for pose in old:
        if cmds.objExists(pose):
            cmds.delete(pose)
    new = cmds.rename(new, "bindPose1")
    return new, len(cmds.dagPose(new, q=True, members=True) or [])


def cut_and_check(path):
    with open(path, encoding="utf-8", errors="surrogateescape") as fh:
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
    with open(path, "w", encoding="utf-8", errors="surrogateescape", newline="") as fh:
        fh.writelines(kept)
    bad = [(n, w) for n, line in enumerate(kept, 1) for w in BANNED if w in line]
    if bad:
        raise RuntimeError("banned content in %s: %s" % (path, bad[:10]))
    return cut


for asset in ASSETS:
    print("=== " + asset)
    cmds.file(asset, open=True, force=True, executeScriptNodes=False)
    roots = cmds.ls("|root", type="joint", long=True) or cmds.ls("|Armature|root", type="joint", long=True)
    assert len(roots) == 1, roots
    root = roots[0]
    before = snapshot()
    standing, parent = fbxlayout.root_in_layout(root)
    if standing:
        print("  root already stands under %s" % parent)
        null = parent
    else:
        assert not cmds.listRelatives(root, parent=True), root
        assert not cmds.objExists("|Armature"), "an Armature is already there"
        null = cmds.createNode("transform", name="Armature", skipSelect=True)
        null = cmds.ls(null, long=True)[0]
        assert null == "|Armature", null
        cmds.setAttr(null + ".rotate", *fbxlayout.WRAP_ROTATE, type="double3")
        root_uuid = cmds.ls(root, uuid=True)[0]
        driven = fbxlayout.root_state(root)[1]
        mode, reason = fbxlayout.layout_plan("", driven)
        assert mode in ("constrained", "static"), (mode, reason)
        jo = tuple(cmds.getAttr(root + ".jointOrient")[0])
        t = tuple(cmds.getAttr(root + ".translate")[0])
        cmds.parent(root, null, relative=True)
        root = cmds.ls(root_uuid, long=True)[0]
        cmds.setAttr(root + ".jointOrient", *fbxlayout.jo_after(jo), type="double3")
        if mode == "static":
            cmds.setAttr(root + ".translate", *fbxlayout.swizzled(t), type="double3")
        print("  root (%s) under %s: jointOrient %s -> %s" % (mode, null, [round(v, 6) for v in jo],
              [round(v, 6) for v in cmds.getAttr(root + ".jointOrient")[0]]))
    # the clean skeleton's meshes to the top, beside the Null, as the FBX has them
    group = cmds.ls("|Creep", type="transform", long=True)
    if group:
        assert mdiff(wm(group[0]), om.MMatrix()) < 1e-9, "the |Creep group is not at the origin"
        for child in cmds.listRelatives(group[0], children=True, fullPath=True) or []:
            locks = unlock(child)
            moved = cmds.parent(child, world=True)[0]
            for a in locks:
                cmds.setAttr(moved + "." + a, lock=True)
        if not cmds.listRelatives(group[0], children=True):
            cmds.delete(group[0])
    pose, members = whole_bind_pose(cmds.ls(root, dag=True, type="joint", long=True), null)
    dj, dv = drift(before)
    print("  bind pose %s over %d members; joints moved %.2e, vertices %.2e cm, skins off their bind %.2e"
          % (pose, members, dj, dv, bind_error()))
    assert dj < 1e-6 and dv < 1e-4 and bind_error() < 1e-4, (dj, dv, bind_error())
    # the rig: the same world under a pose of the controls that move root (its Main) and the hips
    main = cmds.ls("Main", type="transform")
    if main:
        posed = []
        for node, plug, value in (("Main", "translateX", 25.0), ("Main", "rotateY", 30.0), ("RootX_M", "translateY", -7.0)):
            if cmds.objExists(node + "." + plug):
                posed.append((node + "." + plug, cmds.getAttr(node + "." + plug)))
                cmds.setAttr(node + "." + plug, value)
        cmds.dgdirty(allPlugs=True)
        moved_root = mdiff(wm(root), before[0][cmds.ls(root, uuid=True)[0]])
        for plug, value in posed:
            cmds.setAttr(plug, value)
        cmds.dgdirty(allPlugs=True)
        back = drift(before)
        print("  posed through Main/RootX_M: root moved %.2f, back at build pose to %.2e / %.2e" % ((moved_root,) + back))
        assert moved_root > 1.0 and back[0] < 1e-6 and back[1] < 1e-4
    print("  assemblies:", cmds.ls(assemblies=True))
    cmds.file(rename=asset)
    cmds.file(save=True, type="mayaAscii", force=True)
    print("  saved; script nodes cut: %d; %.1f MB" % (cut_and_check(asset), os.path.getsize(asset) / 1e6))
