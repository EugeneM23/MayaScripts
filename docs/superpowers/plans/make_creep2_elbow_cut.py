"""Creep 2's right arm cut at the ELBOW, the upper arm back on the body (2026-10-27).

    mayapy make_creep2_elbow_cut.py             every step, each in its own mayapy (trap 122)
    mayapy make_creep2_elbow_cut.py cut         sources/creep2/Creep2_ElbowCut.ma from Creep2_Rig.ma
    mayapy make_creep2_elbow_cut.py swap <asset> <old mesh> <new mesh>

The animator: «мы отрезали руку по плече а нужно по локоть давай переделаем и руку и меш тело без
головы и руки». Asked: a plane through the elbow joint, across the arm (the bisector of the upper arm
and the forearm), every asset on the new cut, the cut made here.

- **cut** opens `assets/Creep2_Rig.ma` (the three pieces of the shoulder cut, make_creep2_split_rig.py)
  and, at the bind:
  - copies the arm piece twice and cuts each with `polyCut -deleteFaces` on the elbow plane: the
    forearm and hand (`Creep2_Forearm`) and the upper arm;
  - skins both to the rig's joints, the arm piece's weights copied by closest point (exact on its own
    vertices, the new ones along the cut interpolated);
  - unites the upper arm with a copy of the body (`polyUniteSkinned`): `Creep2_BodyElbow`. The two
    meet along the old shoulder seam vertex for vertex (the animator's cut made both sides);
  - saves the two meshes, skinned, with the skeleton, as `sources/creep2/Creep2_ElbowCut.ma`.
- **swap** opens a shipped asset, imports that file into a namespace and puts `<new mesh>` in place of
  `<old mesh>` under the old one's name: a copy at its bind, skinned to the asset's game joints with
  the source's weights vertex for vertex, its faces on the asset's materials by name (else the old
  mesh's), the old one's parent, visibility input, display layer and locks; one bind pose over every
  joint.

Not idempotent by design: run `cut` after make_creep2_split_rig.py, then every `swap`.
See `docs/superpowers/specs/2026-10-27-creep2-elbow-cut-design.md`.
"""
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SOURCE = os.path.join(REPO, "sources", "creep2", "Creep2_ElbowCut.ma").replace("\\", "/")
SWAPS = (("Creep2_Rig.ma", "Creep2_Body", "Creep2_BodyElbow"),
         ("Creep2_Rig.ma", "Creep2_ArmR", "Creep2_Forearm"),
         ("Creep2_Body_Rig.ma", "Creep2_BodySplit", "Creep2_BodyElbow"),
         ("Creep2_Body_Skeleton.ma", "Creep2_BodySplit", "Creep2_BodyElbow"),
         ("Creep2_ArmR_Rig.ma", "Creep2_ArmR", "Creep2_Forearm"),
         ("Creep2_ArmR_Skeleton.ma", "Creep2_ArmR", "Creep2_Forearm"))

if __name__ == "__main__" and len(sys.argv) == 1:
    for args in [["cut"]] + [["swap"] + list(s) for s in SWAPS]:
        print("=" * 20, " ".join(args))
        sys.stdout.flush()
        if subprocess.call([sys.executable, os.path.abspath(__file__)] + args):
            raise SystemExit("step %s failed" % " ".join(args))
    raise SystemExit(0)

BODY = os.path.join(HERE, "make_creep2_body_assets.py")
G = {"__name__": "creep2_body", "__file__": BODY}
exec(compile(open(BODY, encoding="utf-8").read(), BODY, "exec"), G)

import maya.cmds as cmds  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402
import maya.api.OpenMayaAnim as oma  # noqa: E402

leaf, dag, mfn, skin_of, unlock = G["leaf"], G["dag"], G["mfn"], G["skin_of"], G["unlock"]
weights_of, face_materials, uid, path = G["weights_of"], G["face_materials"], G["uid"], G["path"]
C2 = G["G"]
ASSETS = G["ASSETS"]
TRANSFORM_ATTRS = ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz")


def world_copy(src, name, parent=None):
    """An unskinned copy of `src`'s mesh at its bind, its shading kept: a transform UUID."""
    du = cmds.ls(cmds.duplicate(src, name=":" + name)[0], long=True)[0]
    for shape in cmds.listRelatives(du, shapes=True, fullPath=True) or []:
        if cmds.getAttr(shape + ".intermediateObject"):
            cmds.delete(shape)
    unlock(du)
    du_id = uid(du)
    if parent:
        cmds.parent(du, parent)
    elif cmds.listRelatives(du, parent=True):
        cmds.parent(du, world=True)
    du = path(du_id)
    shape = cmds.listRelatives(du, shapes=True, fullPath=True)[0]
    for i in cmds.getAttr(shape + ".gtag", multiIndices=True) or []:              # trap 90
        cmds.removeMultiInstance("%s.gtag[%d]" % (shape, i), b=True)
    cmds.delete(du, constructionHistory=True)
    du = path(du_id)
    cmds.makeIdentity(du, apply=True, translate=True, rotate=True, scale=True)
    cmds.xform(du, pivots=(0, 0, 0), worldSpace=True)
    cmds.rename(cmds.listRelatives(du, shapes=True, fullPath=True)[0], name + "Shape")
    return du_id


def skin_with(du_id, names, flat, n, game, src_skin=None, name=None):
    """Skin the copy to `game` joints with `flat` weights in `names`' order, vertex for vertex."""
    du = path(du_id)
    skin = cmds.skinCluster([game[x] for x in names], du, toSelectedBones=True, bindMethod=0,
                            normalizeWeights=1, maximumInfluences=8, obeyMaxInfluences=False,
                            name=(name or leaf(du)) + "_skinCluster")[0]
    if src_skin:
        for attr in ("skinningMethod", "maxInfluences", "maintainMaxInfluences", "normalizeWeights"):
            try:
                cmds.setAttr(skin + "." + attr, cmds.getAttr(src_skin + "." + attr))
            except RuntimeError:
                pass
    fn = oma.MFnSkinCluster(om.MSelectionList().add(skin).getDependNode(0))
    dst = [leaf(p.fullPathName()) for p in fn.influenceObjects()]
    order = [dst.index(x) for x in names]
    shape = cmds.listRelatives(du, shapes=True, fullPath=True, noIntermediate=True)[0]
    count = mfn(shape).numVertices
    comp = om.MFnSingleIndexedComponent().create(om.MFn.kMeshVertComponent)
    om.MFnSingleIndexedComponent(comp).setCompleteData(count)
    fn.setWeights(dag(shape), comp, om.MIntArray(order), om.MDoubleArray(flat), False)
    return skin


def game_of(mesh):
    """{leaf: long path} of the game skeleton `mesh` is skinned to."""
    skin = skin_of(mesh)
    joint = cmds.ls(cmds.skinCluster(skin, q=True, influence=True)[0], long=True)[0]
    top = joint
    while True:
        parent = cmds.listRelatives(top, parent=True, type="joint", fullPath=True)
        if not parent:
            break
        top = parent[0]
    return top, dict((leaf(j), j) for j in cmds.ls(top, dag=True, type="joint", long=True))


def elbow_plane(game):
    up, lo, ha = (om.MVector(cmds.xform(game[b], q=True, ws=True, t=True))
                  for b in ("upperarm_r", "lowerarm_r", "hand_r"))
    normal = ((lo - up).normal() + (ha - lo).normal()).normal()
    return lo, normal


def cut(du_id, centre, normal):
    """Keep the side `normal` points to (polyCut -deleteFaces deletes the other one)."""
    e = om.MVector(0, 0, 1).rotateTo(normal).asEulerRotation()
    du = path(du_id)
    cmds.polyCut(du + ".f[*]", cutPlaneCenter=(centre.x, centre.y, centre.z),
                 cutPlaneRotate=[math.degrees(a) for a in (e.x, e.y, e.z)], deleteFaces=True)
    cmds.delete(du, constructionHistory=True)
    pts = mfn(du).getPoints(om.MSpace.kWorld)
    side = min((om.MVector(p) - centre) * normal for p in pts)
    assert side > -1e-3, side
    return len(pts)


def step_cut():
    cmds.file(ASSETS + "/Creep2_Rig.ma", open=True, force=True, executeScriptNodes=False)
    for node in cmds.ls(type="UsdDefaultSettings") or []:              # trap 121
        if node != "UsdDefaultSettings" and cmds.objExists(node):
            cmds.lockNode(node, lock=False)
            cmds.delete(node)
    body, arm = cmds.ls("Creep2_Body", long=True)[0], cmds.ls("Creep2_ArmR", long=True)[0]
    root, game = game_of(arm)
    centre, normal = elbow_plane(game)
    arm_skin = skin_of(arm)
    arm_influences = [leaf(j) for j in cmds.skinCluster(arm_skin, q=True, influence=True)]

    pieces = {}
    for name, sign in (("Creep2_Forearm", 1.0), ("Creep2_UpperArm", -1.0)):
        du_id = world_copy(arm, name)
        count = cut(du_id, centre, normal * sign)
        skin = cmds.skinCluster([game[x] for x in arm_influences], path(du_id), toSelectedBones=True,
                                bindMethod=0, normalizeWeights=1, maximumInfluences=8,
                                obeyMaxInfluences=False, name=name + "_skinCluster")[0]
        cmds.copySkinWeights(sourceSkin=arm_skin, destinationSkin=skin, noMirror=True,
                             surfaceAssociation="closestPoint", influenceAssociation="name")
        pieces[name] = du_id
        print("%s: %d vertices" % (name, count))
    names, flat, n = weights_of(body)
    body_id = world_copy(body, "Creep2_BodyCopy")
    skin_with(body_id, names, flat, n, game, skin_of(body))
    united = cmds.polyUniteSkinned(path(body_id), path(pieces["Creep2_UpperArm"]),
                                   constructionHistory=False, mergeUVSets=1, centerPivot=False)
    united = cmds.ls(united[0], long=True)[0]
    united = cmds.rename(united, "Creep2_BodyElbow")
    united = cmds.ls(united, long=True)[0]
    for old in (body_id, pieces["Creep2_UpperArm"]):
        node = cmds.ls(old, long=True)
        if node:
            cmds.delete(node)
    if cmds.listRelatives(united, parent=True):
        cmds.parent(united, world=True)
    forearm = path(pieces["Creep2_Forearm"])
    print("Creep2_BodyElbow: %d vertices; skins off their bind %.2e"
          % (mfn(cmds.ls("Creep2_BodyElbow", long=True)[0]).numVertices, C2["bind_error"]()))
    cmds.select([cmds.ls("Creep2_BodyElbow", long=True)[0], forearm, root], replace=True)
    cmds.file(SOURCE, force=True, exportSelected=True, type="mayaAscii", constructionHistory=True,
              channels=True, constraints=False, expressions=False, shader=True,
              preserveReferences=False)
    print("saved", SOURCE, "%.1f MB" % (os.path.getsize(SOURCE) / 1e6))


def step_swap(asset, old_name, new_name):
    out = ASSETS + "/" + asset
    cmds.file(out, open=True, force=True, executeScriptNodes=False)
    for node in cmds.ls(type="UsdDefaultSettings") or []:              # trap 121
        if node != "UsdDefaultSettings" and cmds.objExists(node):
            cmds.lockNode(node, lock=False)
            cmds.delete(node)
    old = [t for t in cmds.ls(old_name, long=True) if cmds.listRelatives(t, shapes=True, type="mesh")]
    assert len(old) == 1, old
    old = old[0]
    root, game = game_of(old)
    parent = (cmds.listRelatives(old, parent=True, fullPath=True) or [None])[0]
    vis = cmds.listConnections(old + ".visibility", s=True, d=False, plugs=True) or []
    layers = cmds.listConnections(old, type="displayLayer") or []
    old_sg = (cmds.listConnections(cmds.listRelatives(old, shapes=True, fullPath=True, noIntermediate=True)[0],
                                   type="shadingEngine") or [None])[0]
    history = [h for h in cmds.listHistory(old) if cmds.nodeType(h) in ("skinCluster", "tweak", "groupParts", "groupId")]
    rig_mats = dict((leaf(m), m) for m in cmds.ls(materials=True))

    cmds.file(SOURCE, i=True, namespace="elbow", executeScriptNodes=False)
    src = [t for t in cmds.ls("elbow:" + new_name, long=True) if cmds.listRelatives(t, shapes=True, type="mesh")][0]
    src_root, src_game = game_of(src)
    worst = max(max(abs(a - b) for a, b in zip(cmds.xform(src_game[k], q=True, ws=True, m=True),
                                                cmds.xform(game[k], q=True, ws=True, m=True)))
                for k in src_game if k in game and k not in ("weapon_r", "weapon_l"))
    assert worst < 1e-3, worst
    names, flat, n = weights_of(src)
    faces = face_materials(cmds.listRelatives(src, shapes=True, fullPath=True, noIntermediate=True)[0])
    points = [om.MVector(p.x, p.y, p.z) for p in mfn(src).getPoints(om.MSpace.kWorld)]

    cmds.rename(old, old_name + "_Old")
    old = cmds.ls(old_name + "_Old", long=True)[0]
    du_id = world_copy(src, old_name, parent=parent)
    skin = skin_with(du_id, names, flat, n, game, skin_of(src), name=old_name)
    du = path(du_id)
    placed = 0
    for mat, ids in faces.items():
        sg = cmds.listConnections(rig_mats[mat], type="shadingEngine") if mat in rig_mats else None
        if sg:
            cmds.sets(["%s.f[%d]" % (du, f) for f in ids], edit=True, forceElement=sg[0])
            placed += len(ids)
    if not placed and old_sg:
        cmds.sets(du, edit=True, forceElement=old_sg)
    cmds.delete(old)
    cmds.delete([h for h in history if cmds.objExists(h)])
    du = path(du_id)
    for plug in vis:
        cmds.connectAttr(plug, du + ".visibility", force=True)
    for layer in layers:
        cmds.editDisplayLayerMembers(layer, du, noRecurse=True)
    for a in TRANSFORM_ATTRS:
        cmds.setAttr(du + "." + a, lock=True)
    for node in cmds.ls("elbow:*") or []:
        try:
            cmds.lockNode(node, lock=False)
        except Exception:                                                 # noqa: BLE001
            pass
    try:
        cmds.namespace(removeNamespace="elbow", deleteNamespaceContent=True)
    except RuntimeError:                                                  # trap 158
        for node in cmds.ls("elbow:*") or []:
            try:
                cmds.delete(node)
            except Exception:                                             # noqa: BLE001
                pass
        cmds.namespace(removeNamespace="elbow", mergeNamespaceWithRoot=True)
    skins = cmds.ls(type="skinCluster")
    G["whole_bind_pose"](root, skins)
    deleted = []
    C2["unused_shading"](deleted)
    du = path(du_id)
    cmds.dgdirty(du)
    now = mfn(du).getPoints(om.MSpace.kWorld)
    off = max(om.MVector(now[i].x, now[i].y, now[i].z).__sub__(points[i]).length() for i in range(len(now)))
    print("%s: %s now %s, %d vertices on the cut's to %.2e cm, %d faces on named materials, skins off "
          "their bind %.2e" % (asset, old_name, new_name, len(now), off, placed, C2["bind_error"]()))
    assert off < 1e-3 and C2["bind_error"]() < 1e-3
    C2["save_ascii"](out, C2["BANNED"] + ("elbow:", "_Old\"", "Creep2_BodyCopy", "Creep2_UpperArm"))


if __name__ == "__main__":
    if sys.argv[1] == "cut":
        step_cut()
    else:
        step_swap(*sys.argv[2:5])
    import maya.standalone
    maya.standalone.uninitialize()
