"""Give Manny's two assets the first-person mesh Skin_1p, skinned like Skin_3p (2026-10-09).

    mayapy make_manny_1p_assets.py <asset.ma> [--out DIR]    build (writes DIR/<asset>, or beside it)
    mayapy make_manny_1p_assets.py --check <asset.ma>        reopen a built file and prove it

mayapy STANDALONE. Skin_1p is the exact cut of Skin_3p named in sources/manny/manny_1p_faces.json: the
duplicate of Skin_3p with the faces outside the cut deleted, its weights copied through the vertex map
(manny_1p_lib), its bind matrices copied from Skin_3p. The rig asset gets the view switch on Main
(`view`, enum 3P:1P, not keyable, 3P by default), like Orc_D_Rig's. Hands_1P (the old arms, wholly inside
Skin_1p) is hidden in both, not deleted.
"""
import json
import os
import sys

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds
import maya.api.OpenMaya as om

HERE =os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import asset_dress as dress
import manny_1p_lib as L

REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
FACES_JSON = os.path.join(REPO, "sources", "manny", "manny_1p_faces.json")
MESH3, MESH1, HANDS = "Skin_3p", "Skin_1p", "Hands_1P"
MAIN = "|Group|MotionSystem|MainSystem|Main"
VIEW = "view"


def one(name):
    found = cmds.ls(name, type="transform", long=True)
    assert len(found) == 1, (name, found)
    return found[0]


def shape_of(transform):
    return dress.live_shape(transform)


def rest_of(transform):
    """The rest geometry (Orig) of a skinned mesh: the bind shape the skin deforms. The deformed shape
    stands off it wherever the joints do not sit in their bind pose (the file's own pose, 0.07 cm here)."""
    found = [s for s in cmds.listRelatives(transform, shapes=True, fullPath=True) or []
             if cmds.getAttr(s + ".intermediateObject")]
    assert len(found) == 1, found
    return found[0]


def face_shading(shape):
    """The shading group of every face of `shape` (None where none)."""
    n = cmds.polyEvaluate(shape, face=True)
    out = [None] * n
    leaf = shape.split("|")[-1]
    for sg in cmds.listConnections(shape, type="shadingEngine") or []:
        for m in cmds.ls(cmds.sets(sg, q=True) or [], flatten=True):
            if m.split(".")[0].split("|")[-1] != leaf:
                continue
            if ".f[" in m:
                out[int(m.split(".f[")[1].rstrip("]"))] = sg
            else:
                out = [sg if o is None else o for o in out]
    return out


def bind_check(skin3, skin1):
    """Largest difference between the two skins' bind matrices, joint by joint."""
    n3 = [d.partialPathName() for d in L.skin_of(skin3).influenceObjects()]
    n1 = [d.partialPathName() for d in L.skin_of(skin1).influenceObjects()]
    worst = 0.0
    for k, name in enumerate(n3):
        a = cmds.getAttr("%s.bindPreMatrix[%d]" % (skin3, k))
        b = cmds.getAttr("%s.bindPreMatrix[%d]" % (skin1, n1.index(name)))
        worst = max(worst, max(abs(x - y) for x, y in zip(a, b)))
    return worst


def verify(t3, t1, faces):
    """The 1P is the cut: its vertices, weights, bind and shading as Skin_3p's; the 3P untouched in count."""
    s3, s1 = shape_of(t3), shape_of(t1)
    skin3 = cmds.ls(cmds.listHistory(s3, pruneDagObjects=True), type="skinCluster")[0]
    skin1 = cmds.ls(cmds.listHistory(s1, pruneDagObjects=True), type="skinCluster")[0]
    d3, d1 = L.dag_of(s3), L.dag_of(s1)
    r3 = L.dag_of(rest_of(t3))
    assert cmds.polyEvaluate(s1, face=True) == len(faces)
    vmap = L.vertex_map(r3, L.dag_of(rest_of(t1)))
    assert len(set(vmap)) == cmds.polyEvaluate(s1, vertex=True) == len(vmap)
    worst_w, sums = L.check_copy(L.skin_of(skin3), d3, L.skin_of(skin1), d1, vmap)
    # both as they stand in the file, deformed: the 1P must deform where the 3P does, vertex for vertex
    p1 = om.MFnMesh(d1).getPoints(om.MSpace.kWorld)
    p3 = om.MFnMesh(d3).getPoints(om.MSpace.kWorld)
    off = max((p1[i] - p3[j]).length() for i, j in enumerate(vmap))
    bind = bind_check(skin3, skin1)
    shade3, shade1 = face_shading(s3), face_shading(s1)
    shade_bad = sum(1 for p, f in enumerate(faces) if shade1[p] != shade3[f])
    print("CHECK %s: %d faces %d verts, points off the 3P's by %.9f cm, weights off by %.2e (sums %.1e), "
          "bind off by %.2e, faces on another material than the 3P's: %d"
          % (cmds.ls(t1, long=False)[0], cmds.polyEvaluate(s1, face=True), len(vmap), off, worst_w, sums, bind, shade_bad))
    assert off < 1e-6 and worst_w < 1e-9 and sums < 1e-9 and bind < 1e-6 and shade_bad == 0
    return skin1


def build(path, out_dir):
    dress.begin()
    dress.open_asset(path)
    faces = json.load(open(FACES_JSON))["faces"]
    t3 = one(MESH3)
    s3 = shape_of(t3)
    assert cmds.polyEvaluate(s3, face=True) == json.load(open(FACES_JSON))["faces_3p"]
    skin3 = cmds.ls(cmds.listHistory(s3, pruneDagObjects=True), type="skinCluster")[0]
    assert not cmds.ls(MESH1), "%s already in this asset" % MESH1
    dagposes = set(cmds.ls(type="dagPose"))

    # the duplicate: history gone (the copied skin and its Orig shapes), the faces outside the cut deleted
    r3 = om.MFnMesh(L.dag_of(rest_of(t3)))
    rest_points = r3.getPoints(om.MSpace.kObject)
    t1 = cmds.ls(cmds.duplicate(t3, name=MESH1)[0], long=True)[0]
    uid = cmds.ls(t1, uuid=True)[0]
    cmds.delete(t1, constructionHistory=True)
    t1 = cmds.ls(uid, long=True)[0]
    for s in cmds.listRelatives(t1, shapes=True, fullPath=True) or []:
        if cmds.getAttr(s + ".intermediateObject"):
            cmds.delete(s)  # the duplicate's own rest shape: the skin makes its one
    t1 = cmds.ls(uid, long=True)[0]
    # the rest geometry, not the deformed one: the skin deforms it back into place
    om.MFnMesh(L.dag_of(shape_of(t1))).setPoints(rest_points, om.MSpace.kObject)
    keep = set(faces)
    cmds.delete(["%s.f[%d]" % (t1, f) for f in range(cmds.polyEvaluate(t1, face=True)) if f not in keep])
    t1 = cmds.ls(uid, long=True)[0]
    s1 = shape_of(t1)
    assert cmds.polyEvaluate(s1, face=True) == len(faces), cmds.polyEvaluate(s1, face=True)

    # the skin: Skin_3p's joints, its bind matrices and weights through the vertex map
    joints = cmds.skinCluster(skin3, q=True, influence=True)
    skin1 = cmds.skinCluster(joints, t1, toSelectedBones=True, bindMethod=0, normalizeWeights=1,
                             maximumInfluences=8, obeyMaxInfluences=False, name=MESH1 + "_skinCluster")[0]
    n3 = [d.partialPathName() for d in L.skin_of(skin3).influenceObjects()]
    n1 = [d.partialPathName() for d in L.skin_of(skin1).influenceObjects()]
    for k, name in enumerate(n3):
        cmds.setAttr("%s.bindPreMatrix[%d]" % (skin1, n1.index(name)),
                     *cmds.getAttr("%s.bindPreMatrix[%d]" % (skin3, k)), type="matrix")
    bp = cmds.listConnections(skin3 + ".bindPose")[0]
    if cmds.listConnections(skin1 + ".bindPose") != [bp]:
        cmds.connectAttr(bp + ".message", skin1 + ".bindPose", force=True)
    for dp in set(cmds.ls(type="dagPose")) - dagposes:
        if not cmds.listConnections(dp, source=False, destination=True):
            cmds.delete(dp)
    # the new skin deforms the duplicate at the file's pose at once, so compare rest with rest (its Orig)
    vmap = L.vertex_map(L.dag_of(rest_of(t3)), L.dag_of(rest_of(t1)))
    L.copy_weights(L.skin_of(skin3), L.dag_of(s3), L.skin_of(skin1), L.dag_of(s1), vmap)

    # the shading the duplicate carries is Skin_3p's, face for face (the cut keeps their order)
    verify(t3, t1, faces)

    # Hands_1P is inside Skin_1p: hidden, not deleted
    cmds.setAttr(one(HANDS) + ".visibility", 0)
    # Skin_1p itself hidden in the asset (the rig's switch shows it; the skeleton file stays as it was)
    cmds.setAttr(t1 + ".visibility", 0)

    if cmds.objExists(MAIN):
        cmds.addAttr(MAIN, longName=VIEW, attributeType="enum", enumName="3P:1P", defaultValue=0, keyable=False)
        cmds.setAttr(MAIN + "." + VIEW, channelBox=True)
        for mesh, value in ((t3, 0), (t1, 1)):
            cond = cmds.createNode("condition", name=MESH1 if mesh == t1 else MESH3 + "_viewCondition", skipSelect=True)
            cmds.connectAttr(MAIN + "." + VIEW, cond + ".firstTerm")
            cmds.setAttr(cond + ".secondTerm", value)
            cmds.setAttr(cond + ".colorIfTrueR", 1.0)
            cmds.setAttr(cond + ".colorIfFalseR", 0.0)
            cmds.connectAttr(cond + ".outColorR", mesh + ".visibility", force=True)
        print("view switch on", MAIN)

    # the textures stay RELATIVE in the file (the marker names them; a save here makes them absolute, trap 119)
    for f in cmds.ls(type="file"):
        if cmds.attributeQuery("skeldarAssetImage", node=f, exists=True):
            cmds.setAttr(f + ".ftn", cmds.getAttr(f + ".skeldarAssetImage"), type="string")

    os.makedirs(out_dir, exist_ok=True)
    target = os.path.join(out_dir, os.path.basename(path)).replace("\\", "/")
    new = target[:-3] + ".new.ma"
    cmds.file(rename=new)
    cmds.file(save=True, type="mayaAscii", force=True)
    lines = dress.text_without_scripts(new)
    bad = [(n, w) for n, line in enumerate(lines, 1) for w in dress.BANNED if w in line]
    assert not bad, bad[:10]
    with open(new, "w", encoding="utf-8", errors="surrogateescape", newline="") as fh:
        fh.write("\n".join(lines))
    os.replace(new, target)
    print("saved %s (%.1f MB)" % (target, os.path.getsize(target) / 1e6))


def check(path):
    dress.begin()
    dress.open_asset(path)
    faces = json.load(open(FACES_JSON))["faces"]
    t3, t1 = one(MESH3), one(MESH1)
    verify(t3, t1, faces)
    if cmds.objExists(MAIN):
        for value, shown, hidden in ((0, t3, t1), (1, t1, t3)):
            cmds.setAttr(MAIN + "." + VIEW, value)
            assert cmds.getAttr(shown + ".visibility") and not cmds.getAttr(hidden + ".visibility"), value
        cmds.setAttr(MAIN + "." + VIEW, 0)
        print("view switch: 3P shows Skin_3p, 1P shows Skin_1p - both ways")
    print("CHECKED", path)


if __name__ == "__main__":
    if sys.argv[1] == "--check":
        check(os.path.abspath(sys.argv[2]).replace("\\", "/"))
    else:
        args = sys.argv[1:]
        out = os.path.dirname(os.path.abspath(args[0]))
        if "--out" in args:
            out = args[args.index("--out") + 1]
        build(os.path.abspath(args[0]).replace("\\", "/"), out)
