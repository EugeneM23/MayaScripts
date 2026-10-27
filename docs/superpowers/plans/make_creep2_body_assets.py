"""The second Creep's cut body as a character of its own: assets/Creep2_Body_Rig.ma and Creep2_Body_Skeleton.ma.

    mayapy make_creep2_body_assets.py              both, each in its own mayapy (trap 122)
    mayapy make_creep2_body_assets.py rig          the rig
    mayapy make_creep2_body_assets.py skeleton     the skeleton, from the rig asset

mayapy STANDALONE, 2026-10-27 (the animator: «нам нужно сделать разрезанного персонажа ... насадить
само тело на риг. И для разрезанного сделаем тоже свой риг скелет и карточки»). The body the animator
cut out of Creep 2 (`Animations/Rigs/Characters/Creep_Split/Creep_Body.fbx`: the whole 91-bone
skeleton, the mesh without the right arm and the head) on Creep 2's own rig:

- **rig**: `assets/Creep2_Rig.ma` opened, its whole mesh `Creep2_Body` (skin, history) out; the FBX
  imported into a namespace, its bind checked against the rig's game joints (the weapon sockets
  excepted: Creep 2's are turned into UE's convention, the FBX keeps the creature's); a copy of the cut
  mesh at its bind, `Creep2_BodySplit` under `Group|Geometry`, skinned to the rig's game joints with the
  FBX's weights vertex for vertex, its faces on the rig's own materials by name; one bind pose over
  every joint (traps 79/91); the FBX's namespace out.
- **skeleton**: make_creep2_assets.py's skeleton step on that rig.

Since 2026-10-27 `Creep2_Rig.ma` itself is made of the three cut pieces (`make_creep2_split_rig.py`,
run after this one): this script wants the rig with its WHOLE mesh, so rebuild Creep2_Rig.ma with
make_creep2_assets.py first, then this, then the split.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
ASSETS = os.path.join(REPO, "SkeldarAnim", "assets").replace("\\", "/")
SOURCE = "C:/!!!Work/Animations/Rigs/Characters/Creep_Split/Creep_Body.fbx"
SOURCE_RIG = ASSETS + "/Creep2_Rig.ma"
RIG = ASSETS + "/Creep2_Body_Rig.ma"
SKELETON = ASSETS + "/Creep2_Body_Skeleton.ma"
OLD_MESH = "Creep2_Body"
MESH = "Creep2_BodySplit"
SOCKETS = ("weapon_r", "weapon_l")

if __name__ == "__main__" and len(sys.argv) == 1:
    for step in ("rig", "skeleton"):
        print("=" * 20, step)
        sys.stdout.flush()
        if subprocess.call([sys.executable, os.path.abspath(__file__), step]):
            raise SystemExit("step %s failed" % step)
    raise SystemExit(0)

# make_creep2_assets.py's helpers (standalone, plug-ins, the empty working folder, save_ascii ...)
C2 = os.path.join(HERE, "make_creep2_assets.py")
G = {"__name__": "creep2_assets", "__file__": C2}
exec(compile(open(C2, encoding="utf-8").read(), C2, "exec"), G)
G["RIG"], G["SKELETON"], G["MESH"] = RIG, SKELETON, MESH

import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402
import maya.api.OpenMayaAnim as oma  # noqa: E402

wm, uid, path = G["wm"], G["uid"], G["path"]


def leaf(p):
    return p.split("|")[-1].split(":")[-1]


def dag(node):
    return om.MSelectionList().add(node).getDagPath(0)


def mfn(node):
    return om.MFnMesh(dag(node))


def skin_of(node):
    found = cmds.ls(cmds.listHistory(node, pruneDagObjects=True) or [], type="skinCluster")
    return found[0] if found else None


def unlock(node):
    for a in ("translate", "rotate", "scale", "tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz", "v"):
        if cmds.attributeQuery(a, node=node, exists=True):
            cmds.setAttr(node + "." + a, lock=False)          # trap 298: the compounds too


def weights_of(transform):
    skin = skin_of(transform)
    fn = oma.MFnSkinCluster(om.MSelectionList().add(skin).getDependNode(0))
    shape = cmds.listRelatives(transform, shapes=True, fullPath=True, noIntermediate=True)[0]
    comp = om.MFnSingleIndexedComponent().create(om.MFn.kMeshVertComponent)
    om.MFnSingleIndexedComponent(comp).setCompleteData(mfn(shape).numVertices)
    flat, n = fn.getWeights(dag(shape), comp)
    return [leaf(p.fullPathName()) for p in fn.influenceObjects()], flat, n


def whole_bind_pose(root, skins):
    for pose in cmds.ls(type="dagPose"):
        if cmds.objExists(pose):
            cmds.delete(pose)
    joints = cmds.ls(root, dag=True, type="joint", long=True)
    pose = cmds.dagPose(joints, save=True, bindPose=True, name="skeldarBindPose_new")
    pose = pose[0] if isinstance(pose, (list, tuple)) else pose
    strays = [m for m in cmds.ls(cmds.dagPose(pose, q=True, members=True) or [], long=True)
              if cmds.objectType(m) != "joint"]
    if strays:
        cmds.dagPose(strays, remove=True, name=pose)
    for sc in skins:
        cmds.connectAttr(pose + ".message", sc + ".bindPose", force=True)
    return cmds.rename(pose, "bindPose1")


def face_materials(shape):
    """{material name: [face ids]} of `shape`."""
    out = {}
    for sg in cmds.listConnections(shape, type="shadingEngine") or []:
        mats = cmds.listConnections(sg + ".surfaceShader") or []
        if not mats:
            continue
        faces = []
        for member in cmds.sets(sg, q=True) or []:
            if "." not in member:
                if cmds.ls(member, long=True)[0] in cmds.ls(shape, long=True) + (cmds.listRelatives(shape, parent=True, fullPath=True) or []):
                    faces = list(range(mfn(shape).numPolygons))
            elif leaf(member.split(".")[0]) in (leaf(shape), leaf(cmds.listRelatives(shape, parent=True)[0])):
                for f in cmds.ls(member, flatten=True):
                    faces.append(int(f.rsplit("[", 1)[1][:-1]))
        if faces:
            out.setdefault(leaf(mats[0]), []).extend(faces)
    return out


def build_rig():
    cmds.file(SOURCE_RIG, open=True, force=True, executeScriptNodes=False)
    for node in cmds.ls(type="UsdDefaultSettings") or []:              # trap 121
        if node != "UsdDefaultSettings" and cmds.objExists(node):
            cmds.lockNode(node, lock=False)
            cmds.delete(node)
    root = cmds.ls("|root", type="joint", long=True)[0]
    game = dict((leaf(j), j) for j in cmds.ls(root, dag=True, type="joint", long=True))
    assert len(game) == 93, len(game)
    rig_mats = dict((leaf(m), m) for m in cmds.ls(materials=True))

    old = cmds.ls("|Group|Geometry|" + OLD_MESH, long=True)[0]
    history = [h for h in cmds.listHistory(old) if cmds.nodeType(h) in ("skinCluster", "tweak", "groupParts", "groupId")]
    old_vis = cmds.listConnections(old + ".visibility", s=True, d=False, plugs=True) or []

    # the cut body, in a namespace (FBXImport takes the current one)
    cmds.namespace(add=":cutB")
    cmds.namespace(set=":cutB")
    mel.eval('FBXResetImport; FBXImportMode -v add; FBXImport -f "%s"' % SOURCE)
    cmds.namespace(set=":")
    src_body = [cmds.listRelatives(s, parent=True, fullPath=True)[0]
                for s in cmds.ls("cutB:*", type="mesh", long=True, noIntermediate=True)]
    assert len(src_body) == 1, src_body
    src_body = src_body[0]
    src_skin = skin_of(src_body)
    names, flat, n = weights_of(src_body)
    worst, socket = 0.0, {}
    for idx in cmds.getAttr(src_skin + ".matrix", multiIndices=True):
        joint = leaf(cmds.listConnections("%s.matrix[%d]" % (src_skin, idx), s=True, d=False)[0])
        bind = om.MMatrix(cmds.getAttr("%s.bindPreMatrix[%d]" % (src_skin, idx))).inverse()
        d = max(abs(a - b) for a, b in zip(list(bind), list(wm(game[joint]))))
        if joint in SOCKETS:
            socket[joint] = d
        else:
            worst = max(worst, d)
    print("the rig's game joints on the cut body's bind to %.2e (sockets, turned by Creep 2: %s)" % (worst, socket))
    assert worst < 1e-3, worst
    socket_weight = max([flat[v * n + names.index(s)] for s in SOCKETS if s in names
                         for v in range(len(flat) // n)] + [0.0])
    print("weight on the weapon sockets: %.2e" % socket_weight)
    assert socket_weight < 1e-6, socket_weight
    src_shape = cmds.listRelatives(src_body, shapes=True, fullPath=True, noIntermediate=True)[0]
    src_points = mfn(src_body).getPoints(om.MSpace.kWorld)
    src_faces = face_materials(src_shape)
    print("the cut body's materials:", dict((k, len(v)) for k, v in src_faces.items()))

    # a copy at its bind, world points, no history
    du = cmds.ls(cmds.duplicate(src_body, name=":" + MESH)[0], long=True)[0]
    for shape in cmds.listRelatives(du, shapes=True, fullPath=True) or []:
        if cmds.getAttr(shape + ".intermediateObject"):
            cmds.delete(shape)
    unlock(du)
    du_id = uid(du)
    cmds.parent(du, "|Group|Geometry")
    du = path(du_id)
    shape = cmds.ls(cmds.rename(cmds.listRelatives(du, shapes=True, fullPath=True)[0], MESH + "Shape"), long=True)[0]
    for i in cmds.getAttr(shape + ".gtag", multiIndices=True) or []:              # trap 90
        cmds.removeMultiInstance("%s.gtag[%d]" % (shape, i), b=True)
    cmds.delete(du, constructionHistory=True)
    du = path(du_id)
    cmds.makeIdentity(du, apply=True, translate=True, rotate=True, scale=True)
    cmds.xform(du, pivots=(0, 0, 0), worldSpace=True)
    now = mfn(du).getPoints(om.MSpace.kWorld)
    assert len(now) == len(src_points)
    drift = max(now[i].distanceTo(src_points[i]) for i in range(len(now)))
    assert drift < 1e-4, drift

    # skinned to the rig's joints with the FBX's weights
    skin = cmds.skinCluster([game[x] for x in names], du, toSelectedBones=True, bindMethod=0, normalizeWeights=1,
                            maximumInfluences=8, obeyMaxInfluences=False, name=MESH + "_skinCluster")[0]
    for attr in ("skinningMethod", "maxInfluences", "maintainMaxInfluences", "normalizeWeights"):
        try:
            cmds.setAttr(skin + "." + attr, cmds.getAttr(src_skin + "." + attr))
        except RuntimeError:
            pass
    fn = oma.MFnSkinCluster(om.MSelectionList().add(skin).getDependNode(0))
    dst = [leaf(p.fullPathName()) for p in fn.influenceObjects()]
    order = [dst.index(x) for x in names]
    shape = cmds.listRelatives(du, shapes=True, fullPath=True, noIntermediate=True)[0]
    comp = om.MFnSingleIndexedComponent().create(om.MFn.kMeshVertComponent)
    om.MFnSingleIndexedComponent(comp).setCompleteData(len(src_points))
    fn.setWeights(dag(shape), comp, om.MIntArray(order), om.MDoubleArray(flat), False)
    got, _n = fn.getWeights(dag(shape), comp)
    off = max(abs(got[v * n + order[i]] - flat[v * n + i]) for v in range(0, len(src_points), 7) for i in range(n))
    assert off < 1e-9, off

    # its faces on the rig's own materials, by name
    for mat, faces in src_faces.items():
        target = rig_mats.get(mat)
        sg = cmds.listConnections(target, type="shadingEngine") if target else None
        if not sg:
            print("no %s on the rig: its %d faces stay on the default" % (mat, len(faces)))
            continue
        cmds.sets(["%s.f[%d]" % (du, f) for f in faces], edit=True, forceElement=sg[0])

    # the whole mesh out, the cut one in its place
    cmds.delete(old)
    cmds.delete([h for h in history if cmds.objExists(h)])
    for plug in old_vis:
        cmds.connectAttr(plug, du + ".visibility", force=True)
    pose = whole_bind_pose(root, [skin])
    cmds.namespace(removeNamespace="cutB", deleteNamespaceContent=True)
    du = path(du_id)
    for a in ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"):
        cmds.setAttr(du + "." + a, lock=True)
    deleted = []
    G["unused_shading"](deleted)
    cmds.dgdirty(du)
    now = mfn(du).getPoints(om.MSpace.kWorld)
    still = max(now[i].distanceTo(src_points[i]) for i in range(len(now)))
    print("%s: %d vertices, %d faces, skin off its bind %.2e, every vertex on the FBX's to %.2e cm, %s"
          % (MESH, len(now), mfn(du).numPolygons, G["bind_error"](), still, pose))
    assert still < 1e-3 and G["bind_error"]() < 1e-3
    assert cmds.listRelatives("|Group|Geometry", children=True) == [MESH]
    assert len(cmds.ls(type="skinCluster")) == 1 and cmds.ls(type="dagPose") == ["bindPose1"]
    assert len(cmds.dagPose("bindPose1", q=True, members=True)) == 93
    assert cmds.getAttr("|Group.skeldarRetarget") == "rotation"
    print("deleted shading:", deleted, "assemblies:", cmds.ls(assemblies=True))
    G["save_ascii"](RIG, G["BANNED"] + ("cutB:", "Creep_Split"))


if __name__ == "__main__":
    if sys.argv[1] == "rig":
        build_rig()
    else:
        G["build_skeleton"]()
    import maya.standalone
    maya.standalone.uninitialize()
