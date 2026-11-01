"""Build the Swordman's assets: SkeldarAnim/assets/Swordman_Rig.ma and Swordman_Skeleton.ma.

    mayapy make_swordman_assets.py <built .mb>       both, each in its own mayapy (trap 122)
    mayapy make_swordman_assets.py rig <built .mb>   the rig, from what rebuild_swordman_rig.py saved
    mayapy make_swordman_assets.py skeleton          the skeleton, from the rig asset

mayapy STANDALONE, 2026-11-01. Spec: docs/superpowers/specs/2026-11-01-swordman-design.md.
The pipeline: make_swordman_source.py -> rebuild_swordman_rig.py (LIVE, a disposable Maya)
-> this. make_swordman_texture.py writes the map both steps name.

- **rig**: the built scene opened with its script nodes not run; script nodes, unknown nodes and
  the plugin requirements they leave, memberless dagPoses, animCurves driving nothing and the
  shading nothing wears deleted (make_creep2_assets.py's clean-up). The body's Max material is
  replaced by the ONE textured material naming his atlas RELATIVELY, so Add Character points it
  at the installed copy. Then Creep 2's position-follows, so a translated FK control carries its
  bone. What stays is what Add Character imports into its namespace: `|root` (55 joints: our
  names on his proportions), `|Group` (the rig, `skeldarRetarget = "rotation"`, `Swordman_Body`
  under its Geometry with its skin).
- **skeleton**: the rig asset without its rig, the Creep's and Creep 2's way.

Each step refuses (raises) when a skin is off its bind or a joint moved, saves as .ma, cuts
Maya's script-node blocks from the text (trap 74) and refuses banned words.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
ASSETS = os.path.join(REPO, "SkeldarAnim", "assets").replace("\\", "/")
RIG = ASSETS + "/Swordman_Rig.ma"
SKELETON = ASSETS + "/Swordman_Skeleton.ma"
MESH = "Swordman_Body"
JOINTS = 55
KEY = "Swordman"
MAPS = "Swordman/"
COLOUR_MAP = "Swordman_Color.jpg"
BANNED = ("createNode script", "vaccine", "breed_gene", "C:/", "c:/", "D:/", "E:/",
          "Downloads", "scratchpad", "Telegram", "BaseFBXASC032Human", "Sward Man",
          "Swards Man", "Swardman", "Cylinder003", "Object013", "Object014",
          "FitSkeletonNameMatcherImporting")


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

sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))
from maya_scenesetup import colour  # noqa: E402

import asset_dress  # noqa: E402  (the shared dressing: marks, relative paths, colour space)

for _p in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(_p, quiet=True)
    except Exception:                                                   # noqa: BLE001
        pass
os.chdir(tempfile.mkdtemp(prefix="swordman_assets_"))                   # trap 119


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
                m = om.MMatrix(cmds.getAttr("%s.bindPreMatrix[%d]" % (sc, idx))) \
                    * wm(cmds.ls(src[0], long=True)[0])
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
    bad = [(n, w, line.strip()[:120]) for n, line in enumerate(kept, 1)
           for w in banned if w in line]
    if bad:
        os.rename(out, out + ".rejected")
        raise RuntimeError("banned content (kept as .rejected): %s" % bad[:10])
    print("saved %s (%.1f MB), %d script nodes cut" % (out, os.path.getsize(out) / 1e6, cut))


def unused_shading(deleted):
    # openPBR_shader1 is one of Maya 2027's own undeletable default shaders: it is in
    # every scene, this repo's other assets included, and trying is six error lines.
    keep = {"initialShadingGroup", "initialParticleSE", "lambert1", "standardSurface1",
            "particleCloud1", "openPBR_shader1"}
    for _ in range(6):
        doomed = [sg for sg in cmds.ls(type="shadingEngine")
                  if sg not in keep and not cmds.sets(sg, query=True)]
        doomed += cmds.ls(cmds.listConnections(doomed, type="materialInfo") or [])
        doomed += [m for m in cmds.ls(materials=True)
                   if m not in keep and not cmds.listConnections(m, type="shadingEngine")]
        doomed += [t for t in cmds.ls(textures=True) + cmds.ls(type="place2dTexture")
                   if not [d for d in cmds.listConnections(t, source=False, destination=True) or []
                           if cmds.nodeType(d) not in ("defaultTextureList",
                                                       "defaultRenderUtilityList",
                                                       "nodeGraphEditorInfo")]]
        doomed = [n for n in doomed if cmds.objExists(n)]
        if not doomed:
            break
        drop(sorted(set(doomed)), deleted)


def dress_body():
    """His Max material off the body, our one textured material on.

    One map, no normals: his atlas is a hand-painted 256 px colour map. The file
    node names it RELATIVELY (`colour.ASSET_IMAGE`), so Add Character points it at
    the installed copy and no path of this machine reaches the asset (trap 119).
    """
    shape = cmds.listRelatives(cmds.ls(MESH, long=True)[0], shapes=True,
                               fullPath=True, noIntermediate=True)[0]
    material, engine = colour.make_textured_material(MAPS + COLOUR_MAP, KEY)
    node = cmds.listConnections(material + ".color", type="file")[0]
    node = cmds.rename(node, "skeldarTexture_%s_color" % KEY)
    asset_dress.mark(node, MAPS + COLOUR_MAP, raw=False)
    cmds.sets(shape, edit=True, forceElement=engine)
    stored = cmds.getAttr(node + ".fileTextureName")
    if stored != MAPS + COLOUR_MAP:
        raise RuntimeError("the image went absolute: %r" % stored)
    return material, node


def position_follows():
    """Every game bone that turns with its AdvancedSkeleton joint follows its POSITION too.

    Creep 2's step (2026-10-27, «когда переношу контролы фк рук то они не следуют за
    ригом»): the Creep's procedure binds by orientation only, so a translated FK control
    moved its AS joint and no game bone. Parents first, so whatever rides rigidly carries
    its children; the twists and neck_02 turn with AS's Part joints, which do not stay put
    on their segments, so they ride their parents. Returns (made, worst drift).
    """
    root = cmds.ls("|root", type="joint", long=True)[0]
    joints = [root] + cmds.listRelatives(root, allDescendents=True, type="joint", fullPath=True)
    before = dict((j, wm(j)) for j in joints)
    for j in joints:
        cons = cmds.listRelatives(j, children=True, type="constraint", fullPath=True) or []
        point = [c for c in cons if cmds.nodeType(c) == "pointConstraint"]
        orient = [c for c in cons if cmds.nodeType(c) == "orientConstraint"]
        if len(point) == 1 and len(orient) == 1:
            pt = cmds.pointConstraint(point[0], q=True, targetList=True) or []
            ot = cmds.orientConstraint(orient[0], q=True, targetList=True) or []
            if len(pt) == 1 and pt == ot:
                cmds.delete(point + orient)
                cmds.parentConstraint(pt[0], j, maintainOffset=True)
                print("  %s: point + orient from %s made one parentConstraint"
                      % (j.split("|")[-1], pt[0]))
    made = 0
    placed = set()
    for j in sorted(joints, key=lambda p: p.count("|")):
        cons = cmds.listRelatives(j, children=True, type="constraint", fullPath=True) or []
        kinds = [cmds.nodeType(c) for c in cons]
        if "pointConstraint" in kinds or "parentConstraint" in kinds:
            placed.add(j)
            continue
        if kinds.count("orientConstraint") != 1 or j.rsplit("|", 1)[0] not in placed:
            continue
        orient = cons[kinds.index("orientConstraint")]
        targets = cmds.orientConstraint(orient, q=True, targetList=True) or []
        if len(targets) != 1 or not cmds.ls(targets[0], long=True)[0].startswith("|Group|"):
            continue
        if "Part" in targets[0].split("|")[-1]:
            continue
        cmds.pointConstraint(targets[0], j, maintainOffset=True)
        placed.add(j)
        made += 1
    drift = max(max(abs(a - b) for a, b in zip(list(m), list(wm(j)))) for j, m in before.items())
    assert drift < 1e-4, "the follows moved the skeleton: %.2e" % drift
    return made, drift


# ----------------------------------------------------------------------- rig

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
    material, node = dress_body()
    print("textured material: %s -> %s" % (material, cmds.getAttr(node + ".fileTextureName")))
    drop([p for p in cmds.ls(type="dagPose") if not cmds.dagPose(p, query=True, members=True)],
         deleted)
    drop([c for c in cmds.ls(type="animCurve")
          if not cmds.listConnections(c, source=False, destination=True)], deleted)
    unused_shading(deleted)
    followed, moved = position_follows()
    print("position follows added (game bone <- its AS joint, offset kept): %d, "
          "the skeleton moved %.2e" % (followed, moved))

    root = cmds.ls("|root", type="joint", long=True)
    below = cmds.listRelatives(root[0], allDescendents=True, type="joint") if root else []
    assert root and len(below) == JOINTS - 1, \
        "the skeleton, %d joints (%d below root)" % (JOINTS, len(below or []))
    for n in ("weapon_r", "weapon_l", "camera_root", "camera_bone", "ball_l", "ball_r"):
        assert n in below, n
    assert not [b for b in below if "index_" in b or "thumb_" in b], "a finger bone crept in"
    assert cmds.getAttr("|Group.skeldarRetarget") == "rotation", "the retarget mark"
    geo = cmds.listRelatives("|Group|Geometry", children=True) or []
    assert geo == [MESH], geo
    assert len(cmds.ls(type="skinCluster")) == 1, cmds.ls(type="skinCluster")
    err = bind_error()
    assert err < 1e-3, "the skin is off its bind: %.2e" % err
    images = [cmds.getAttr(f + ".fileTextureName") for f in cmds.ls(type="file") or []]
    assert images == [MAPS + COLOUR_MAP], images
    print("assemblies:", cmds.ls(assemblies=True))
    print("deleted %d nodes: %s" % (len(deleted), deleted[:12]))
    print("skin off its bind %.2e; dagPoses %s; images %s" % (err, cmds.ls(type="dagPose"), images))
    save_ascii(RIG, BANNED)


# ------------------------------------------------------------------ skeleton

def relink_images():
    """Every file node given its RELATIVE path back after the open.

    Opening a shipped textured asset resolves each relative path against the
    .ma's own folder and stores it absolute (trap 284), so a re-save would put
    this machine's path in the file. The relative path is on the node itself,
    under `colour.ASSET_IMAGE`.
    """
    back = []
    for node in cmds.ls(type="file") or []:
        if not cmds.attributeQuery(colour.ASSET_IMAGE, node=node, exists=True):
            continue
        relative = cmds.getAttr(node + "." + colour.ASSET_IMAGE)
        if relative and cmds.getAttr(node + ".fileTextureName") != relative:
            cmds.setAttr(node + ".fileTextureName", relative, type="string")
            back.append(relative)
    return back


def build_skeleton():
    cmds.file(RIG, open=True, force=True, executeScriptNodes=False)
    print("images given their relative paths back:", relink_images())
    for node in cmds.ls(type="UsdDefaultSettings") or []:
        if node != "UsdDefaultSettings" and cmds.objExists(node):
            cmds.lockNode(node, lock=False)
            cmds.delete(node)
    root = cmds.ls("|root", type="joint", long=True)[0]
    joints = sorted([root] + cmds.listRelatives(root, allDescendents=True, type="joint",
                                                fullPath=True),
                    key=lambda j: j.count("|"))
    world = [(uid(j), wm(j)) for j in joints]
    cmds.delete(cmds.listRelatives(root, allDescendents=True, type="constraint",
                                   fullPath=True) or [])
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
    locked = [a for a in ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz")
              if cmds.getAttr(mesh + "." + a, lock=True)]
    for a in locked:
        cmds.setAttr(mesh + "." + a, lock=False)
    cmds.parent(mesh, world=True)
    for a in locked:
        cmds.setAttr(path(mesh_uid) + "." + a, lock=True)
    for _layer in cmds.listConnections(path(mesh_uid) + ".drawOverride",
                                       type="displayLayer") or []:
        cmds.editDisplayLayerMembers("defaultLayer", path(mesh_uid), noRecurse=True)
    cmds.setAttr(path(mesh_uid) + ".visibility", True)
    cmds.delete("|Group")
    kinds = drop_unused(["|root", "|" + MESH])
    print("deleted by type:", sorted(kinds.items(), key=lambda kv: -kv[1])[:16])

    root = cmds.ls("|root", type="joint", long=True)[0]
    assert len(cmds.listRelatives(root, allDescendents=True, type="joint")) == JOINTS - 1
    assert not cmds.listRelatives(root, allDescendents=True, type="constraint")
    err = bind_error()
    images = [cmds.getAttr(f + ".fileTextureName") for f in cmds.ls(type="file") or []]
    assert images == [MAPS + COLOUR_MAP], images
    print("bones re-seated, drift %.2e; skin off its bind %.2e; images %s" % (drift, err, images))
    assert drift < 1e-6 and err < 1e-3 and len(cmds.ls(type="skinCluster")) == 1
    print("assemblies:", cmds.ls(assemblies=True))
    save_ascii(SKELETON, BANNED + ('createNode transform -n "Group"', "ControlSet", "FitSkeleton",
                                   "MoCapConstraints", "skeldarRetarget"))


def drop_unused(keep_dag_roots):
    """Every node nothing kept depends on: the DAG under `keep_dag_roots`, its meshes'
    history and shading, the bind poses and the layers holding something, Maya's own."""
    keep = set(cmds.ls(keep_dag_roots, dag=True, long=True))
    keep |= set(cmds.ls(keep_dag_roots, dag=True))
    history = cmds.listHistory(list(keep), pruneDagObjects=False) or []
    keep |= set(cmds.ls(history, long=True)) | set(cmds.ls(history))
    shading = cmds.listConnections(history, type="shadingEngine") or []
    keep |= set(shading)
    keep |= set(cmds.ls(cmds.listHistory(shading) or []))
    for pose in cmds.ls(type="dagPose") or []:
        if cmds.dagPose(pose, query=True, members=True):
            keep.add(pose)
    for layer in cmds.ls(type="displayLayer") or []:
        if cmds.editDisplayLayerMembers(layer, query=True) or layer == "defaultLayer":
            keep.add(layer)
    keep |= set(cmds.ls(defaultNodes=True) or [])
    kinds = {}
    for _ in range(8):
        doomed = []
        for node in cmds.ls(long=True) or []:
            short = node.split("|")[-1]
            if node in keep or short in keep:
                continue
            if cmds.objectType(node, isAType="dagNode") and \
                    cmds.listRelatives(node, parent=True, fullPath=True):
                continue                    # a child goes with its top
            if cmds.referenceQuery(node, isNodeReferenced=True):
                continue
            doomed.append(node)
        doomed = [n for n in doomed if cmds.objExists(n)]
        if not doomed:
            break
        for node in doomed:
            if not cmds.objExists(node):
                continue
            kind = cmds.nodeType(node)
            try:
                cmds.lockNode(node, lock=False)
                cmds.delete(node)
            except Exception:                                           # noqa: BLE001
                continue
            kinds[kind] = kinds.get(kind, 0) + 1
    return kinds


if __name__ == "__main__":
    if sys.argv[1] == "rig":
        build_rig(sys.argv[2].replace("\\", "/"))
    else:
        build_skeleton()
    maya.standalone.uninitialize()
