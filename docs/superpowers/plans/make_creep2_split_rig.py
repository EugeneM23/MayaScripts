"""Creep 2's rig made of its three cut pieces, with Arm R / Head switches on Main: assets/Creep2_Rig.ma.

    mayapy make_creep2_split_rig.py

mayapy STANDALONE, 2026-10-27 (the animator: «для нового крипа нужно добавить тело руку и голову в
основной риг и сделать переключатели на главном контроле которые могут включать или отключать
отрезанные части»). `assets/Creep2_Rig.ma` opened:
- its whole mesh `Creep2_Body` (skin, history) goes;
- each cut FBX of `Creep_Split` is imported into a namespace, its bind checked against the rig's game
  joints (the weapon sockets excepted, and they must carry no weight), and a copy of its mesh at its
  bind is skinned to the rig's game joints with the FBX's weights vertex for vertex, its faces on the
  rig's materials by name;
- `Main.armR` / `Main.head` (bool, keyable, default on) drive the arm's and the head's visibility;
- one bind pose is saved over every joint.

Idempotent through its source: it refuses a rig that already carries the switches. See
`docs/superpowers/specs/2026-10-27-creep2-split-rig-switches-design.md`.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BODY = os.path.join(HERE, "make_creep2_body_assets.py")
G = {"__name__": "creep2_body", "__file__": BODY}
exec(compile(open(BODY, encoding="utf-8").read(), BODY, "exec"), G)

import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402
import maya.api.OpenMayaAnim as oma  # noqa: E402

leaf, dag, mfn, skin_of = G["leaf"], G["dag"], G["mfn"], G["skin_of"]
unlock, weights_of, face_materials, whole_bind_pose = (G["unlock"], G["weights_of"], G["face_materials"],
                                                       G["whole_bind_pose"])
wm, uid, path = G["wm"], G["uid"], G["path"]
C2 = G["G"]
ASSETS = G["ASSETS"]
RIG = ASSETS + "/Creep2_Rig.ma"
SPLIT = "C:/!!!Work/Animations/Rigs/Characters/Creep_Split"
SOCKETS = ("weapon_r", "weapon_l")
# (FBX, mesh name, Main's switch or None for the body)
PIECES = (("Creep_Body.fbx", "Creep2_Body", None),
          ("Creep_Arm_R.fbx", "Creep2_ArmR", ("armR", "Arm R")),
          ("Creep_Head.fbx", "Creep2_Head", ("head", "Head")))


def add_piece(fbx, name, ns, game, rig_mats):
    """A copy of the cut FBX's mesh at its bind under Group|Geometry, skinned to the rig's game joints
    with the FBX's weights. Returns (transform UUID, skinCluster, the FBX's world points)."""
    cmds.namespace(add=":" + ns)
    cmds.namespace(set=":" + ns)
    mel.eval('FBXResetImport; FBXImportMode -v add; FBXImport -f "%s/%s"' % (SPLIT, fbx))
    cmds.namespace(set=":")
    meshes = [cmds.listRelatives(s, parent=True, fullPath=True)[0]
              for s in cmds.ls(ns + ":*", type="mesh", long=True, noIntermediate=True)]
    assert len(meshes) == 1, (fbx, meshes)
    src = meshes[0]
    src_skin = skin_of(src)
    names, flat, n = weights_of(src)
    worst = 0.0
    for idx in cmds.getAttr(src_skin + ".matrix", multiIndices=True):
        joint = leaf(cmds.listConnections("%s.matrix[%d]" % (src_skin, idx), s=True, d=False)[0])
        if joint in SOCKETS:
            continue
        bind = om.MMatrix(cmds.getAttr("%s.bindPreMatrix[%d]" % (src_skin, idx))).inverse()
        worst = max(worst, max(abs(a - b) for a, b in zip(list(bind), list(wm(game[joint])))))
    socket_weight = max([flat[v * n + names.index(s)] for s in SOCKETS if s in names
                         for v in range(len(flat) // n)] + [0.0])
    print("%s: the rig's joints on its bind to %.2e, weight on the sockets %.2e" % (fbx, worst, socket_weight))
    assert worst < 1e-3 and socket_weight < 1e-6, (worst, socket_weight)
    src_shape = cmds.listRelatives(src, shapes=True, fullPath=True, noIntermediate=True)[0]
    points = mfn(src).getPoints(om.MSpace.kWorld)
    faces = face_materials(src_shape)

    du = cmds.ls(cmds.duplicate(src, name=":" + name)[0], long=True)[0]
    for shape in cmds.listRelatives(du, shapes=True, fullPath=True) or []:
        if cmds.getAttr(shape + ".intermediateObject"):
            cmds.delete(shape)
    unlock(du)
    du_id = uid(du)
    cmds.parent(du, "|Group|Geometry")
    du = path(du_id)
    shape = cmds.ls(cmds.rename(cmds.listRelatives(du, shapes=True, fullPath=True)[0], name + "Shape"),
                    long=True)[0]
    for i in cmds.getAttr(shape + ".gtag", multiIndices=True) or []:              # trap 90
        cmds.removeMultiInstance("%s.gtag[%d]" % (shape, i), b=True)
    cmds.delete(du, constructionHistory=True)
    du = path(du_id)
    cmds.makeIdentity(du, apply=True, translate=True, rotate=True, scale=True)
    cmds.xform(du, pivots=(0, 0, 0), worldSpace=True)
    now = mfn(du).getPoints(om.MSpace.kWorld)
    drift = max(now[i].distanceTo(points[i]) for i in range(len(now)))
    assert len(now) == len(points) and drift < 1e-4, drift

    skin = cmds.skinCluster([game[x] for x in names], du, toSelectedBones=True, bindMethod=0,
                            normalizeWeights=1, maximumInfluences=8, obeyMaxInfluences=False,
                            name=name + "_skinCluster")[0]
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
    om.MFnSingleIndexedComponent(comp).setCompleteData(len(points))
    fn.setWeights(dag(shape), comp, om.MIntArray(order), om.MDoubleArray(flat), False)
    for mat, ids in faces.items():
        target = rig_mats.get(mat)
        sg = cmds.listConnections(target, type="shadingEngine") if target else None
        if not sg:
            print("  no %s on the rig: %d faces stay on the default" % (mat, len(ids)))
            continue
        cmds.sets(["%s.f[%d]" % (du, f) for f in ids], edit=True, forceElement=sg[0])
    for node in cmds.ls(ns + ":*") or []:
        try:
            cmds.lockNode(node, lock=False)
        except Exception:                                                 # noqa: BLE001
            pass
    cmds.namespace(removeNamespace=ns, deleteNamespaceContent=True)
    return du_id, skin, points


def build():
    cmds.file(RIG, open=True, force=True, executeScriptNodes=False)
    for node in cmds.ls(type="UsdDefaultSettings") or []:              # trap 121
        if node != "UsdDefaultSettings" and cmds.objExists(node):
            cmds.lockNode(node, lock=False)
            cmds.delete(node)
    main = cmds.ls("|Group|MotionSystem|MainSystem|Main", long=True)[0]
    assert not cmds.attributeQuery("armR", node=main, exists=True), "already split"
    root = cmds.ls("|root", type="joint", long=True)[0]
    game = dict((leaf(j), j) for j in cmds.ls(root, dag=True, type="joint", long=True))
    assert len(game) == 93, len(game)
    rig_mats = dict((leaf(m), m) for m in cmds.ls(materials=True))

    old = cmds.ls("|Group|Geometry|Creep2_Body", long=True)[0]
    history = [h for h in cmds.listHistory(old) if cmds.nodeType(h) in ("skinCluster", "tweak", "groupParts", "groupId")]
    old_vis = cmds.listConnections(old + ".visibility", s=True, d=False, plugs=True) or []
    cmds.rename(old, "Creep2_BodyWhole")
    old = cmds.ls("|Group|Geometry|Creep2_BodyWhole", long=True)[0]

    made = []
    for n, (fbx, name, switch) in enumerate(PIECES):
        made.append((name, switch) + add_piece(fbx, name, "cut%d" % n, game, rig_mats))
    cmds.delete(old)
    cmds.delete([h for h in history if cmds.objExists(h)])
    for name, switch, du_id, skin, points in made:
        du = path(du_id)
        for plug in old_vis:
            if switch is None:
                cmds.connectAttr(plug, du + ".visibility", force=True)
        if switch:
            attr, nice = switch
            cmds.addAttr(main, longName=attr, niceName=nice, attributeType="bool", defaultValue=1,
                         keyable=True)
            cmds.connectAttr(main + "." + attr, du + ".visibility", force=True)
        for a in ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"):
            cmds.setAttr(du + "." + a, lock=True)
    pose = whole_bind_pose(root, [m[3] for m in made])
    deleted = []
    C2["unused_shading"](deleted)
    for name, switch, du_id, skin, points in made:
        du = path(du_id)
        cmds.dgdirty(du)
        now = mfn(du).getPoints(om.MSpace.kWorld)
        off = max(now[i].distanceTo(points[i]) for i in range(len(now)))
        print("%s: %d vertices, every one on its FBX's to %.2e cm, switch %s" % (name, len(now), off, switch))
        assert off < 1e-3
    kids = sorted(cmds.listRelatives("|Group|Geometry", children=True))
    assert kids == sorted(m[0] for m in made), kids
    assert len(cmds.ls(type="skinCluster")) == 3 and cmds.ls(type="dagPose") == ["bindPose1"]
    assert len(cmds.dagPose("bindPose1", q=True, members=True)) == 93
    print("skins off their bind %.2e, %s, deleted shading %s" % (C2["bind_error"](), pose, deleted))
    assert C2["bind_error"]() < 1e-3
    C2["save_ascii"](RIG, C2["BANNED"] + ("cut0:", "cut1:", "cut2:", "Creep_Split", "BodyWhole"))


if __name__ == "__main__":
    build()
    import maya.standalone
    maya.standalone.uninitialize()
