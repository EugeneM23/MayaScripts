"""Build the second Creep's assets: SkeldarAnim/assets/Creep2_Rig.ma and Creep2_Skeleton.ma.

    mayapy make_creep2_assets.py                     both, each in its own mayapy (trap 122)
    mayapy make_creep2_assets.py rig <built .mb>     the rig, from the scene rebuild_creep2_rig.py saved
    mayapy make_creep2_assets.py skeleton            the skeleton, from the rig asset

mayapy STANDALONE, 2026-10-27 (spec: docs/superpowers/specs/2026-10-27-creep2-design.md). The pipeline:
make_creep2_source.py (the FBX in Manny's shape) -> rebuild_creep2_rig.py (LIVE, a disposable Maya: the
AdvancedSkeleton build) -> this.

- **rig**: the built scene opened with its script nodes not run; script nodes, unknown nodes and the
  plugin requirements they leave, dagPoses with no member, animCurves driving nothing and the shading
  nothing wears deleted (make_orc_rig_asset.py's clean-up). What stays is what Add Character imports
  into its namespace: `|root` (93 joints: Manny's names, the camera bones on Manny's values, the weapon
  sockets in UE's convention), `|Group` (the rig, `skeldarRetarget = "rotation"`, `Creep2_Body` under
  its Geometry with its skin), the `Creep2_Skeleton` layer, the rig's sets, the mesh's three materials
  (Add paints a palette colour over them).
- **skeleton**: the rig asset without its rig, the Creep's and Playerchar's way: every bone's world
  matrix recorded, the constraints deleted, the bones re-seated from their world matrices, the mesh out
  of `Group|Geometry` to the top beside `|root`, `|Group` and everything nothing kept depends on deleted.

Each step refuses (raises) when a skin is off its bind or a joint moved, saves as .ma, cuts Maya's
script-node blocks from the text (trap 74) and refuses banned words.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
ASSETS = os.path.join(REPO, "SkeldarAnim", "assets").replace("\\", "/")
RIG = ASSETS + "/Creep2_Rig.ma"
SKELETON = ASSETS + "/Creep2_Skeleton.ma"
MESH = "Creep2_Body"
JOINTS = 93
BANNED = ("createNode script", "vaccine", "breed_gene", "C:/", "c:/", "D:/", "Downloads", "scratchpad",
          "SK_Creep_skinned", "MI_Creep_Outfit", "FitSkeletonNameMatcherImporting", "creep_textures")


def drive(built):
    for step in (["rig", built], ["skeleton"]):
        print("=" * 20, " ".join(step))
        sys.stdout.flush()
        code = subprocess.call([sys.executable, os.path.abspath(__file__)] + step)
        if code:
            raise SystemExit("step %s failed (%d)" % (step[0], code))


if __name__ == "__main__" and (len(sys.argv) == 1 or sys.argv[1] not in ("rig", "skeleton")):
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    drive(sys.argv[1])
    raise SystemExit(0)

import tempfile  # noqa: E402

import maya.standalone  # noqa: E402
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

for _p in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(_p, quiet=True)
    except Exception:                                                   # noqa: BLE001
        pass
os.chdir(tempfile.mkdtemp(prefix="creep2_assets_"))                    # trap 119


def wm(node):
    return om.MMatrix(cmds.getAttr(node + ".worldMatrix[0]"))


def uid(node):
    return cmds.ls(node, uuid=True)[0]


def path(u):
    return cmds.ls(u, long=True)[0]


def bind_error():
    worst = 0.0
    for sc in cmds.ls(type="skinCluster"):
        for idx in cmds.getAttr(sc + ".matrix", multiIndices=True) or []:
            src = cmds.listConnections("%s.matrix[%d]" % (sc, idx), s=True, d=False)
            if src:
                m = om.MMatrix(cmds.getAttr("%s.bindPreMatrix[%d]" % (sc, idx))) * wm(cmds.ls(src[0], long=True)[0])
                worst = max(worst, max(abs(a - b) for a, b in zip(list(m), list(om.MMatrix()))))
    return worst


def drop(nodes, deleted):
    for n in nodes:
        if cmds.objExists(n):
            try:
                cmds.lockNode(n, lock=False)
            except Exception:                                           # noqa: BLE001
                pass
            cmds.delete(n)
            deleted.append(n)


def save_ascii(out, banned):
    cmds.file(rename=out)
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
    bad = [(n, w, line.strip()[:120]) for n, line in enumerate(kept, 1) for w in banned if w in line]
    if bad:
        os.rename(out, out + ".rejected")
        raise RuntimeError("banned content (kept as .rejected): %s" % bad[:10])
    print("saved %s (%.1f MB), %d script nodes cut" % (out, os.path.getsize(out) / 1e6, cut))


def unused_shading(deleted):
    keep = {"initialShadingGroup", "initialParticleSE", "lambert1", "standardSurface1", "particleCloud1", "openPBR_shader1"}
    for _ in range(6):
        doomed = [sg for sg in cmds.ls(type="shadingEngine") if sg not in keep and not cmds.sets(sg, query=True)]
        doomed += cmds.ls(cmds.listConnections(doomed, type="materialInfo") or [])
        doomed += [m for m in cmds.ls(materials=True) if m not in keep and not cmds.listConnections(m, type="shadingEngine")]
        doomed += [t for t in cmds.ls(textures=True) + cmds.ls(type="place2dTexture")
                   if not [d for d in cmds.listConnections(t, source=False, destination=True) or []
                           if cmds.nodeType(d) not in ("defaultTextureList", "defaultRenderUtilityList", "nodeGraphEditorInfo")]]
        doomed = [n for n in doomed if cmds.objExists(n)]
        if not doomed:
            break
        drop(sorted(set(doomed)), deleted)


# ------------------------------------------------------------------ rig
def build_rig(built):
    cmds.file(built, open=True, force=True, executeScriptNodes=False)
    deleted = []
    drop(cmds.ls(type="script"), deleted)
    drop(cmds.ls(type="unknown") + cmds.ls(type="unknownDag"), deleted)
    for plugin in cmds.unknownPlugin(query=True, list=True) or []:
        try:
            cmds.unknownPlugin(plugin, remove=True)
        except Exception:                                               # noqa: BLE001
            pass
    drop([p for p in cmds.ls(type="dagPose") if not cmds.dagPose(p, query=True, members=True)], deleted)
    drop([c for c in cmds.ls(type="animCurve") if not cmds.listConnections(c, source=False, destination=True)], deleted)
    unused_shading(deleted)
    # the importer named the slots' shading groups after the FBX (SK_Creep_skinnedSG, SG1, SG2):
    # each takes its material's name
    for sg in cmds.ls(type="shadingEngine"):
        mats = cmds.listConnections(sg + ".surfaceShader") or []
        if sg.startswith("SK_Creep_skinned") and mats:
            cmds.rename(sg, mats[0] + "SG")
    root = cmds.ls("|root", type="joint", long=True)
    below = cmds.listRelatives(root[0], allDescendents=True, type="joint") if root else []
    assert root and len(below) == JOINTS - 1, "the skeleton, %d joints (%d below root)" % (JOINTS, len(below or []))
    for n in ("weapon_r", "weapon_l", "camera_root", "camera_bone"):
        assert n in below, n
    assert cmds.getAttr("|Group.skeldarRetarget") == "rotation", "the retarget mark"
    geo = cmds.listRelatives("|Group|Geometry", children=True) or []
    assert geo == [MESH], geo
    assert len(cmds.ls(type="skinCluster")) == 1, cmds.ls(type="skinCluster")
    err = bind_error()
    assert err < 1e-3, "the skin is off its bind: %.2e" % err
    print("assemblies:", cmds.ls(assemblies=True))
    print("deleted %d nodes: %s" % (len(deleted), deleted[:16]))
    print("skin off its bind %.2e; dagPoses %s; materials %s" % (
        err, cmds.ls(type="dagPose"), [m for m in cmds.ls(materials=True)
                                       if m not in ("lambert1", "standardSurface1", "particleCloud1", "openPBR_shader1")]))
    save_ascii(RIG, BANNED)


# ------------------------------------------------------------------ skeleton
def build_skeleton():
    cmds.file(RIG, open=True, force=True, executeScriptNodes=False)
    for node in cmds.ls(type="UsdDefaultSettings") or []:
        if node != "UsdDefaultSettings" and cmds.objExists(node):
            cmds.lockNode(node, lock=False)
            cmds.delete(node)
    root = cmds.ls("|root", type="joint", long=True)[0]
    joints = sorted([root] + cmds.listRelatives(root, allDescendents=True, type="joint", fullPath=True),
                    key=lambda j: j.count("|"))
    world = [(uid(j), wm(j)) for j in joints]
    cmds.delete(cmds.listRelatives(root, allDescendents=True, type="constraint", fullPath=True) or [])
    cmds.delete(cmds.listRelatives(root, children=True, type="constraint", fullPath=True) or [])
    for u, m in world:
        j = path(u)
        for a in ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"):
            cmds.setAttr(j + "." + a, lock=False)
        cmds.xform(j, worldSpace=True, matrix=list(m))
    drift = max(max(abs(a - b) for a, b in zip(list(m), list(wm(path(u))))) for u, m in world)
    mesh = cmds.ls("|Group|Geometry|" + MESH, long=True)[0]
    mesh_uid = uid(mesh)
    for plug in cmds.listConnections(mesh + ".visibility", s=True, d=False, plugs=True) or []:
        cmds.disconnectAttr(plug, mesh + ".visibility")
    locked = [a for a in ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz") if cmds.getAttr(mesh + "." + a, lock=True)]
    for a in locked:
        cmds.setAttr(mesh + "." + a, lock=False)
    cmds.parent(mesh, world=True)
    for a in locked:
        cmds.setAttr(path(mesh_uid) + "." + a, lock=True)
    for layer in cmds.listConnections(path(mesh_uid) + ".drawOverride", type="displayLayer") or []:
        cmds.editDisplayLayerMembers("defaultLayer", path(mesh_uid), noRecurse=True)
    cmds.setAttr(path(mesh_uid) + ".visibility", True)
    cmds.delete("|Group")
    kinds = drop_unused(["|root", "|" + MESH])
    print("deleted by type:", sorted(kinds.items(), key=lambda kv: -kv[1])[:20])
    root = cmds.ls("|root", type="joint", long=True)[0]
    assert len(cmds.listRelatives(root, allDescendents=True, type="joint")) == JOINTS - 1
    assert not cmds.listRelatives(root, allDescendents=True, type="constraint")
    err = bind_error()
    print("bones re-seated, drift %.2e; skin off its bind %.2e" % (drift, err))
    assert drift < 1e-6 and err < 1e-3 and len(cmds.ls(type="skinCluster")) == 1
    print("assemblies:", cmds.ls(assemblies=True))
    save_ascii(SKELETON, BANNED + ('createNode transform -n "Group"', "ControlSet", "FitSkeleton",
                                   "MoCapConstraints", "skeldarRetarget"))


def drop_unused(keep_dag_roots):
    """Every node nothing kept depends on: the DAG under `keep_dag_roots`, its meshes' history and
    shading, the bind poses and the layers holding something, Maya's own nodes."""
    keep = set(cmds.ls(keep_dag_roots, dag=True, long=True))
    for shape in cmds.ls(keep_dag_roots, dag=True, type="mesh", long=True):
        keep.update(cmds.ls(cmds.listHistory(shape) or [], long=True))
        for sg in cmds.listConnections(shape, type="shadingEngine") or []:
            keep.add(sg)
            keep.update(cmds.ls(cmds.listHistory(sg) or [], long=True))
            keep.update(cmds.ls(cmds.listConnections(sg, type="materialInfo") or []))
    keep.update(cmds.ls(type="dagPose"))
    keep.update(l for l in cmds.ls(type="displayLayer") if l == "defaultLayer" or cmds.editDisplayLayerMembers(l, q=True))
    default = set(cmds.ls(defaultNodes=True)) | set(cmds.ls(readOnly=True)) | set(cmds.ls(cameras=True, long=True))
    default |= set(cmds.listRelatives(cmds.ls(cameras=True, long=True), parent=True, fullPath=True) or [])
    skip = ("displayLayerManager", "renderLayerManager", "renderLayer", "lightLinker", "shapeEditorManager",
            "poseInterpolatorManager", "nodeGraphEditorInfo", "hyperGraphInfo", "time", "script",
            "UsdDefaultSettings")
    doomed = [n for n in cmds.ls(long=True) if n not in keep and n not in default and cmds.nodeType(n) not in skip]
    kinds = {}
    for n in doomed:
        if cmds.objExists(n):
            kinds[cmds.nodeType(n)] = kinds.get(cmds.nodeType(n), 0) + 1
            try:
                cmds.lockNode(n, lock=False)
                cmds.delete(n)
            except Exception as exc:                                  # noqa: BLE001
                print("kept (could not delete)", n, exc)
    cmds.delete(cmds.ls(type="script") or [])
    for p in cmds.ls(type="dagPose"):
        if cmds.objExists(p) and not cmds.dagPose(p, q=True, members=True):
            cmds.delete(p)
    return kinds


if __name__ == "__main__":
    if sys.argv[1] == "rig":
        build_rig(sys.argv[2].replace("\\", "/"))
    else:
        build_skeleton()
    maya.standalone.uninitialize()
