"""Build the Playerchar assets: the rig, the skeleton and the four clothing pieces.

    mayapy make_playerchar_assets.py              every step, each in its own mayapy (trap 122)
    mayapy make_playerchar_assets.py rig          SkeldarAnim/assets/Playerchar_Rig.ma
    mayapy make_playerchar_assets.py skeleton     SkeldarAnim/assets/Playerchar_Skeleton.ma (from the rig)
    mayapy make_playerchar_assets.py armor <key>  SkeldarAnim/assets/Armor/<key>.ma

mayapy STANDALONE, 2026-10-21 (spec: docs/superpowers/specs/2026-10-21-playerchar-and-clothing-design.md).
The source is sources/playerchar/Playerchar_Proxy.mb (make_playerchar_source.py): the draft body and its
outfit skinned onto a bare copy of Manny's game skeleton at the rig's build pose.

- **rig**: the shipped Manny_Rig.ma (opened with asset_dress, script nodes not run) with Manny's meshes,
  their lod group, Main's 1P/3P `view` switch and Manny's materials out, and `SKM_Playerchar|Body` in:
  the source's Body copied at its bind, bound to the rig's game joints with the source's weights vertex
  for vertex, the bind pose saved again whole (traps 79/91), one textured material naming the atlas
  relatively ("Playerchar/Playerchar_Color.jpg", colour.ASSET_IMAGE).
- **1P** (2026-10-22, «1P версию точно так же как и для менни»): `Body_1P`, the body's arms and legs -
  the cut Manny's `Skin_1p` is (the torso and head out): a face kept when any of its vertices weighs at
  least ONE_P_SHARE on the arm and leg bones (fitted on Manny: that rule gives his own cut back to 1.9 %
  of its faces). Skinned with the body's weights vertex for vertex, the same material; `Main.view`
  (enum 3P:1P, not keyable, 3P by default) switches the two as on Manny's and the Orc D's rig. In the
  skeleton asset `Body_1P` stays, hidden, as Manny's skeleton keeps `Skin_1p`.
- **skeleton**: the rig asset without its rig, the Creep skeleton's way: the bones re-seated from their
  world matrices, `|Group` and everything nothing kept depends on deleted.
- **armor**: one clothing piece - a group `<key>` of skinned meshes at identity (`inheritsTransform`
  off on each: equipped they hang in an armor space that moves, and the skin already places them) and
  the source's game skeleton at its bind, which Equip rewires onto the wearer's bones by name and
  deletes. No material: the catalog row's texture is painted at Equip. `accessoires` (one mesh of 19
  shells) is split by shell - the shells weighted to `head` are the helmet. The source's two HIDDEN
  meshes (`chains_Beard`, a chain veil, and `Fabrics`, a cloak: unskinned, not in the artist's FBX) are
  not clothing.

Every mesh keeps one UV set, `map1` (the source's `DiffuseUV`, which the atlas is laid on). Each step
refuses (raises) when a mesh is not where the source's skin puts it or a skin is off its bind, saves
as .ma, cuts Maya's script-node blocks from the text (trap 74) and refuses banned words.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
PLUGIN = os.path.join(REPO, "SkeldarAnim")
ASSETS = os.path.join(PLUGIN, "assets").replace("\\", "/")
SOURCE = os.path.join(REPO, "sources", "playerchar", "Playerchar_Proxy.mb").replace("\\", "/")
RIG = ASSETS + "/Playerchar_Rig.ma"
SKELETON = ASSETS + "/Playerchar_Skeleton.ma"
MAPS = "Playerchar/"
ATLAS = "Playerchar_Color.jpg"
GROUP = "SKM_Playerchar"
BODY = "Body"
BODY_1P = "Body_1P"
VIEW = "view"
# Manny's 1P (`Skin_1p`) is his body's limbs: a face of the body is the 1P's when any of its vertices
# weighs at least this on these bones (fitted on Manny's Skin_3p against his own cut: 1726 of 92178 off)
LIMB_BONES = ("upperarm", "lowerarm", "hand", "thumb", "index", "middle", "ring", "pinky",
              "thigh", "calf", "foot", "ball")
ONE_P_SHARE = 0.35
BANNED = ("createNode script", "vaccine", "breed_gene", "C:/", "c:/", "D:/", "E:/", "e:/", "Downloads",
          "scratchpad", "Basechar_proxy_mat", "Merged_bodyLow", "skeldarColour", "srcP:")

# the clothing pieces: (source mesh, which of its shells: None = every one, "head" = those weighted to
# the head, "rest" = the others). The source's `chains_Beard` (a chain veil) and `Fabrics` (a cloak) are
# left out: HIDDEN in the animator's scene, unskinned, and not in the artist's FBX -- leftovers.
PIECES = {
    "Playerchar_Helmet": [("polySurface9", "head")],
    "Playerchar_Armor": [("TorsoCloth_", None), ("chains_Shoulders", None), ("chains_Legs", None),
                         ("polySurface9", "rest")],
    "Playerchar_Shield": [("Shield", None)],
    "Playerchar_Pants": [("Pants", None)],
}
NAMES = {"polySurface9": {"head": "Helmet", "rest": "Gear"}, "TorsoCloth_": "Tunic",
         "chains_Shoulders": "Shoulder_Chains", "chains_Legs": "Belt_Chains", "Shield": "Shield",
         "Pants": "Pants"}


def drive():
    mayapy = sys.executable
    steps = [["rig"], ["skeleton"]] + [["armor", key] for key in PIECES]
    for step in steps:
        print("=" * 20, " ".join(step))
        sys.stdout.flush()
        code = subprocess.call([mayapy, os.path.abspath(__file__)] + step)
        if code:
            raise SystemExit("step %s failed (%d)" % (" ".join(step), code))


if __name__ == "__main__" and len(sys.argv) == 1:
    drive()
    raise SystemExit(0)

import maya.standalone  # noqa: E402
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402
import maya.api.OpenMayaAnim as oma  # noqa: E402

sys.path.insert(0, HERE)
sys.path.insert(0, PLUGIN)
import asset_dress  # noqa: E402
from maya_scenesetup import colour  # noqa: E402


def wm(node):
    return om.MMatrix(cmds.getAttr(node + ".worldMatrix[0]"))


def dag(node):
    sel = om.MSelectionList()
    sel.add(node)
    return sel.getDagPath(0)


def mfn(node):
    return om.MFnMesh(dag(node))


def leaf(path):
    return path.split("|")[-1].split(":")[-1]


def uid(node):
    return cmds.ls(node, uuid=True)[0]


def path(u):
    return cmds.ls(u, long=True)[0]


def skin_of(transform):
    found = cmds.ls(cmds.listHistory(transform, pruneDagObjects=True) or [], type="skinCluster")
    return found[0] if found else None


def bind_error(skin):
    worst = 0.0
    for idx in cmds.getAttr(skin + ".matrix", multiIndices=True) or []:
        src = cmds.listConnections("%s.matrix[%d]" % (skin, idx), s=True, d=False)
        if src:
            m = om.MMatrix(cmds.getAttr("%s.bindPreMatrix[%d]" % (skin, idx))) * wm(src[0])
            worst = max(worst, max(abs(m.getElement(r, c) - (r == c)) for r in range(4) for c in range(4)))
    return worst


def shells(transform):
    """[(vertex ids, face ids)] of the mesh's connected pieces."""
    fn = mfn(transform)
    parent = list(range(fn.numVertices))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    faces = [list(fn.getPolygonVertices(f)) for f in range(fn.numPolygons)]
    for vs in faces:
        for v in vs[1:]:
            a, b = find(vs[0]), find(v)
            if a != b:
                parent[a] = b
    groups = {}
    for f, vs in enumerate(faces):
        g = groups.setdefault(find(vs[0]), (set(), []))
        g[0].update(vs)
        g[1].append(f)
    return [(sorted(v), f) for v, f in groups.values()]


def weights_of(transform):
    """(names, flat weights, influence count) of the mesh's skin, every vertex."""
    skin = skin_of(transform)
    fn = oma.MFnSkinCluster(om.MSelectionList().add(skin).getDependNode(0))
    shape = cmds.listRelatives(transform, shapes=True, fullPath=True, noIntermediate=True)[0]
    comp = om.MFnSingleIndexedComponent().create(om.MFn.kMeshVertComponent)
    om.MFnSingleIndexedComponent(comp).setCompleteData(mfn(shape).numVertices)
    flat, n = fn.getWeights(dag(shape), comp)
    return [leaf(p.fullPathName()) for p in fn.influenceObjects()], flat, n


def head_shells(transform):
    """The shells of `transform` whose weight sits mostly on `head`."""
    names, flat, n = weights_of(transform)
    head = names.index("head")
    out = []
    for verts, faces in shells(transform):
        on_head = sum(flat[v * n + head] for v in verts) / float(len(verts))
        out.append((on_head > 0.5, verts, faces))
    return out


def first_person_faces(transform):
    """The faces of `transform` its first-person cut keeps: a face with a vertex weighing ONE_P_SHARE
    or more on the arm and leg bones (Manny's Skin_1p rule)."""
    names, flat, n = weights_of(transform)
    limb = [i for i, x in enumerate(names) if x.startswith(LIMB_BONES)]
    share = [sum(flat[v * n + i] for i in limb) for v in range(len(flat) // n)]
    fn = mfn(transform)
    return [f for f in range(fn.numPolygons)
            if max(share[v] for v in fn.getPolygonVertices(f)) >= ONE_P_SHARE]


def one_uv_set(shape):
    """The source's `DiffuseUV` as the shape's only set, `map1`."""
    sets = cmds.polyUVSet(shape, q=True, allUVSets=True) or []
    if "DiffuseUV" not in sets:
        raise RuntimeError("%s has no DiffuseUV: %s" % (shape, sets))
    if sets[0] != "DiffuseUV":
        cmds.polyCopyUV(shape, uvSetNameInput="DiffuseUV", uvSetName=sets[0], createNewMap=False)
        cmds.polyUVSet(shape, currentUVSet=True, uvSet=sets[0])
        for extra in sets[1:]:
            cmds.polyUVSet(shape, delete=True, uvSet=extra)
        if sets[0] != "map1":
            cmds.polyUVSet(shape, rename=True, uvSet=sets[0], newUVSet="map1")
    else:
        cmds.polyUVSet(shape, currentUVSet=True, uvSet="DiffuseUV")
        for extra in sets[1:]:
            cmds.polyUVSet(shape, delete=True, uvSet=extra)
        cmds.polyUVSet(shape, rename=True, uvSet="DiffuseUV", newUVSet="map1")
    cmds.polyUVSet(shape, currentUVSet=True, uvSet="map1")
    for cs in cmds.polyColorSet(shape, q=True, allColorSets=True) or []:
        cmds.polyColorSet(shape, delete=True, colorSet=cs)
    cmds.setAttr(shape + ".displayColors", 0)


def copy_mesh(src, name, faces=None):
    """A copy of `src` at its bind under world, only `faces` (None = every one), plain `name`, no
    history, one UV set. Returns (transform, the source vertex of each new vertex) - vertex ids compact
    in order when faces are deleted, checked by position."""
    fn_src = mfn(src)
    points = fn_src.getPoints(om.MSpace.kWorld)
    du = cmds.ls(cmds.duplicate(src, name=":" + name)[0], long=True)[0]
    for shape in cmds.listRelatives(du, shapes=True, fullPath=True) or []:
        if cmds.getAttr(shape + ".intermediateObject"):
            cmds.delete(shape)
    for a in ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz", "v"):
        cmds.setAttr(du + "." + a, lock=False)
    for node in [du] + (cmds.listRelatives(du, shapes=True, fullPath=True) or []):
        for attr in cmds.listAttr(node, userDefined=True) or []:
            if cmds.attributeQuery(attr, node=node, exists=True):
                cmds.setAttr(node + "." + attr, lock=False)
                cmds.deleteAttr(node + "." + attr)
    du_id = uid(du)
    if cmds.listRelatives(du, parent=True):
        cmds.parent(du, world=True)
    du = path(du_id)
    shape = cmds.listRelatives(du, shapes=True, fullPath=True)[0]
    shape = cmds.ls(cmds.rename(shape, ":" + name + "Shape"), long=True)[0]
    for i in cmds.getAttr(shape + ".gtag", multiIndices=True) or []:
        cmds.removeMultiInstance("%s.gtag[%d]" % (shape, i), b=True)
    if faces is not None:
        keep = set(faces)
        cmds.delete(["%s.f[%d]" % (du, f) for f in range(fn_src.numPolygons) if f not in keep])
        kept = sorted(set(v for f in faces for v in fn_src.getPolygonVertices(f)))
    else:
        kept = list(range(fn_src.numVertices))
    cmds.delete(du, constructionHistory=True)
    du = path(du_id)
    shape = cmds.listRelatives(du, shapes=True, fullPath=True)[0]
    one_uv_set(shape)
    cmds.delete(du, constructionHistory=True)
    du = path(du_id)
    # the transform at identity, its world in the points
    cmds.makeIdentity(du, apply=True, translate=True, rotate=True, scale=True)
    cmds.xform(du, pivots=(0, 0, 0), worldSpace=True)
    new = mfn(du).getPoints(om.MSpace.kWorld)
    assert len(new) == len(kept), (name, len(new), len(kept))
    drift = max(new[k].distanceTo(points[v]) for k, v in enumerate(kept))
    assert drift < 1e-5, "%s: the vertex map is off by %.3e" % (name, drift)
    return du, kept


def bind_like(mesh, kept, src, joints, name):
    """`mesh` skinned to `joints` ({leaf: path}) with `src`'s weights at the vertices `kept`, and its
    skinning settings."""
    names, flat, n = weights_of(src)
    src_skin = skin_of(src)
    settings = dict((a, cmds.getAttr(src_skin + "." + a))
                    for a in ("skinningMethod", "maxInfluences", "maintainMaxInfluences", "normalizeWeights"))
    skin = cmds.skinCluster([joints[x] for x in names], mesh, toSelectedBones=True, bindMethod=0,
                            normalizeWeights=1, maximumInfluences=8, obeyMaxInfluences=False,
                            name=name + "_skinCluster")[0]
    for attr, value in settings.items():
        try:
            cmds.setAttr(skin + "." + attr, value)
        except RuntimeError:
            pass
    fn = oma.MFnSkinCluster(om.MSelectionList().add(skin).getDependNode(0))
    dst_names = [leaf(p.fullPathName()) for p in fn.influenceObjects()]
    order = [dst_names.index(x) for x in names]
    weights = om.MDoubleArray()
    for v in kept:
        for i in range(n):
            weights.append(flat[v * n + i])
    shape = cmds.listRelatives(mesh, shapes=True, fullPath=True, noIntermediate=True)[0]
    comp = om.MFnSingleIndexedComponent().create(om.MFn.kMeshVertComponent)
    om.MFnSingleIndexedComponent(comp).setCompleteData(len(kept))
    fn.setWeights(dag(shape), comp, om.MIntArray(order), weights, False)
    got, _n = fn.getWeights(dag(shape), comp)
    worst = max(abs(got[k * n + order[i]] - flat[v * n + i])
                for k, v in enumerate(kept) if k % 7 == 0 for i in range(n))
    assert worst < 1e-9, "%s: weights off by %.2e" % (name, worst)
    return skin


def save_ascii(out, banned=BANNED):
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
    bad = []
    with open(out, encoding="utf-8", errors="replace") as fh:
        for n, line in enumerate(fh, 1):
            for word in banned:
                if word in line:
                    bad.append((n, word, line.strip()[:120]))
    if bad:
        os.rename(out, out + ".rejected")
        raise RuntimeError("banned content (kept as .rejected): %s" % bad[:10])
    print("saved %s (%.1f MB), %d script nodes cut" % (out, os.path.getsize(out) / 1e6, cut))


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


def whole_bind_pose(root, skins):
    """One bind pose over every joint of `root`, the skins on it (traps 79/91)."""
    for pose in set(p for sc in skins for p in cmds.listConnections(sc + ".bindPose", type="dagPose") or []):
        if cmds.objExists(pose):
            cmds.delete(pose)
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


def atlas_material(key):
    mat, engine = colour.make_textured_material(MAPS + ATLAS, key)
    colour_file = cmds.listConnections(mat + ".color", type="file")[0]
    colour_file = cmds.rename(colour_file, key + "_color")
    cmds.rename(cmds.listConnections(colour_file + ".uvCoord")[0], key + "_color_place2d")
    asset_dress.mark(colour_file, MAPS + ATLAS, raw=False)
    return mat, engine


# ------------------------------------------------------------------ rig
def build_rig():
    asset_dress.begin()
    asset_dress.open_asset(ASSETS + "/Manny_Rig.ma")
    root = cmds.ls("|root", type="joint", long=True)[0]
    game = dict((leaf(j), j) for j in cmds.ls(root, dag=True, type="joint", long=True))
    assert len(game) == 93, len(game)
    # Manny out: the meshes, their skins and history, the lod group, Main's view switch
    manny = cmds.ls("|SKM_Manny_Simple", long=True)[0]
    history = []
    for shape in cmds.listRelatives(manny, allDescendents=True, type="mesh", fullPath=True) or []:
        history += [h for h in cmds.listHistory(shape) if cmds.nodeType(h) in
                    ("skinCluster", "blendShape", "tweak", "groupParts", "groupId")]
    main = cmds.ls("|Group|MotionSystem|MainSystem|Main", long=True)[0]
    conds = [c for c in cmds.listConnections(main + ".view", source=False, destination=True) or []
             if cmds.nodeType(c) == "condition"]
    cmds.delete(manny)
    cmds.delete([n for n in history + conds if cmds.objExists(n)])
    cmds.deleteAttr(main + ".view")
    for lod in cmds.ls(type="lodGroup"):
        cmds.delete(lod)

    # the source, in a namespace
    cmds.file(SOURCE, i=True, type="mayaBinary", namespace="srcP", ignoreVersion=True)
    src_root = cmds.ls("srcP:root", type="joint", long=True)[0]
    src_body = cmds.ls("srcP:Body", type="transform", long=True)[0]
    src_skin = skin_of(src_body)
    worst = 0.0
    for idx in cmds.getAttr(src_skin + ".matrix", multiIndices=True):
        joint = cmds.listConnections("%s.matrix[%d]" % (src_skin, idx), s=True, d=False)[0]
        bind = om.MMatrix(cmds.getAttr("%s.bindPreMatrix[%d]" % (src_skin, idx))).inverse()
        worst = max(worst, max(abs(a - b) for a, b in zip(list(bind), list(wm(game[leaf(joint)])))))
    print("the rig's game joints on the source's bind to %.2e" % worst)
    assert worst < 1e-3, worst
    src_points = mfn(src_body).getPoints(om.MSpace.kWorld)

    body, kept = copy_mesh(src_body, BODY)
    group = cmds.createNode("transform", name=GROUP, skipSelect=True)
    body = cmds.ls(cmds.parent(body, "|" + GROUP)[0], long=True)[0]
    skin = bind_like(body, kept, src_body, game, BODY)
    faces_1p = first_person_faces(src_body)
    body1, kept1 = copy_mesh(src_body, BODY_1P, faces_1p)
    body1 = cmds.ls(cmds.parent(body1, "|" + GROUP)[0], long=True)[0]
    skin1 = bind_like(body1, kept1, src_body, game, BODY_1P)
    pose = whole_bind_pose(root, [skin, skin1])
    for mesh, keep, sc in ((body, kept, skin), (body1, kept1, skin1)):
        cmds.dgdirty(mesh)
        now = mfn(mesh).getPoints(om.MSpace.kWorld)
        still = max(now[k].distanceTo(src_points[v]) for k, v in enumerate(keep))
        print("%s: %d vertices, %d faces, skin off its bind %.2e, every vertex where the source's skin has "
              "it to %.2e cm, %s" % (leaf(mesh), len(keep), mfn(mesh).numPolygons, bind_error(sc), still, pose))
        assert still < 1e-3 and bind_error(sc) < 1e-4
    cmds.namespace(removeNamespace="srcP", deleteNamespaceContent=True)

    for shape in cmds.ls(cmds.ls(materials=True), long=True):
        pass
    mat, engine = atlas_material("Playerchar_Body")
    cmds.sets([body, body1], edit=True, forceElement=engine)
    for mesh in (body, body1):
        for a in ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"):
            cmds.setAttr(mesh + "." + a, lock=True)
    # Main's switch between the two, as Manny's and the Orc D's: 3P by default, not keyable
    cmds.addAttr(main, longName=VIEW, attributeType="enum", enumName="3P:1P", defaultValue=0, keyable=False)
    cmds.setAttr(main + "." + VIEW, channelBox=True)
    for mesh, value in ((body, 0), (body1, 1)):
        cond = cmds.createNode("condition", name=leaf(mesh) + "_viewCondition", skipSelect=True)
        cmds.connectAttr(main + "." + VIEW, cond + ".firstTerm")
        cmds.setAttr(cond + ".secondTerm", value)
        cmds.setAttr(cond + ".colorIfTrueR", 1.0)
        cmds.setAttr(cond + ".colorIfFalseR", 0.0)
        cmds.connectAttr(cond + ".outColorR", mesh + ".visibility", force=True)
    for value, shown, hidden in ((1, body1, body), (0, body, body1)):
        cmds.setAttr(main + "." + VIEW, value)
        assert cmds.getAttr(shown + ".visibility") and not cmds.getAttr(hidden + ".visibility"), value
    gone = asset_dress.unused_shading()
    print("shading taken out:", sorted(set(t for _n, t in gone)))
    print("left of Manny:", cmds.ls("*Manny*"))
    assert sorted(cmds.ls(type="skinCluster")) == sorted([skin, skin1]), cmds.ls(type="skinCluster")
    assert cmds.ls(type="dagPose") == ["bindPose1"], cmds.ls(type="dagPose")
    assert len(cmds.dagPose("bindPose1", q=True, members=True)) == 93
    assert cmds.attributeQuery(VIEW, node=main, exists=True) and not cmds.getAttr(main + "." + VIEW)
    print("images:", asset_dress.check_images(MAPS, [ATLAS]))
    print("assemblies:", cmds.ls(assemblies=True))
    save_ascii(RIG)


# ------------------------------------------------------------------ skeleton
def build_skeleton():
    asset_dress.begin()
    cmds.file(RIG, open=True, force=True, executeScriptNodes=False)
    for node in cmds.ls(type="UsdDefaultSettings") or []:
        if node != "UsdDefaultSettings" and cmds.objExists(node):
            cmds.lockNode(node, lock=False)
            cmds.delete(node)
    # an open resolves the asset's relative images and stores them absolute (trap 284): give them back
    for node in cmds.ls(type="file"):
        if cmds.attributeQuery(colour.ASSET_IMAGE, node=node, exists=True):
            space = cmds.getAttr(node + ".colorSpace")
            cmds.setAttr(node + ".fileTextureName", cmds.getAttr(node + "." + colour.ASSET_IMAGE), type="string")
            cmds.setAttr(node + ".colorSpace", space, type="string")
    root = cmds.ls("|root", type="joint", long=True)[0]
    joints = sorted([root] + cmds.listRelatives(root, allDescendents=True, type="joint", fullPath=True),
                    key=lambda j: j.count("|"))
    world = [(uid(j), wm(j)) for j in joints]
    cmds.delete(cmds.listRelatives(root, allDescendents=True, type="constraint", fullPath=True) or [])
    for u, m in world:
        j = path(u)
        for a in ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"):
            cmds.setAttr(j + "." + a, lock=False)
        cmds.xform(j, worldSpace=True, matrix=list(m))
    drift = max(max(abs(a - b) for a, b in zip(list(m), list(wm(path(u))))) for u, m in world)
    cmds.delete("|Group")
    kinds = drop_unused(["|root", "|" + GROUP])
    # the 1P stays in the file hidden, as Manny's skeleton keeps Skin_1p (its switch went with Main)
    for mesh, shown in ((BODY, True), (BODY_1P, False)):
        node = "|%s|%s" % (GROUP, mesh)
        for plug in cmds.listConnections(node + ".visibility", s=True, d=False, plugs=True) or []:
            cmds.disconnectAttr(plug, node + ".visibility")
        cmds.setAttr(node + ".visibility", shown)
    print("deleted by type:", sorted(kinds.items(), key=lambda kv: -kv[1])[:20])
    root = cmds.ls("|root", type="joint", long=True)[0]
    assert len(cmds.listRelatives(root, allDescendents=True, type="joint")) == 92
    assert not cmds.listRelatives(root, allDescendents=True, type="constraint")
    skins = cmds.ls(type="skinCluster")
    worst = max(bind_error(sc) for sc in skins)
    print("bones re-seated, drift %.2e; skins %s off their bind %.2e" % (drift, skins, worst))
    assert worst < 1e-4 and len(skins) == 2
    print("images:", asset_dress.check_images(MAPS, [ATLAS]))
    print("assemblies:", cmds.ls(assemblies=True))
    save_ascii(SKELETON, BANNED + ('createNode transform -n "Group"', "ControlSet", "FitSkeleton", "MoCapConstraints"))


# ------------------------------------------------------------------ armor
def build_armor(key):
    asset_dress.begin()
    cmds.file(SOURCE, open=True, force=True, executeScriptNodes=False)
    root = cmds.ls("|root", type="joint", long=True)[0]
    joints = dict((leaf(j), j) for j in cmds.ls(root, dag=True, type="joint", long=True))
    made = []
    for src_name, which in PIECES[key]:
        src = cmds.ls(src_name, type="transform", long=True)[0]
        name = NAMES[src_name][which] if isinstance(NAMES[src_name], dict) else NAMES[src_name]
        if which is None:
            faces = None
        else:
            picked = [(h, v, f) for h, v, f in head_shells(src) if h == (which == "head")]
            faces = sorted(f for _h, _v, fs in picked for f in fs)
            print("  %s: %d of its shells (%s)" % (src_name, len(picked), which))
            if which == "head":
                tops = [min(mfn(src).getPoint(v, om.MSpace.kWorld).y for v in vs) for _h, vs, _f in picked]
                assert len(picked) == 2 and min(tops) > 155.0, tops
        mesh, kept = copy_mesh(src, name, faces)
        assert cmds.getAttr(src + ".visibility"), "%s is hidden in the source" % src_name
        skin = bind_like(mesh, kept, src, joints, name)
        made.append((uid(mesh), uid(skin), src, kept, name))
        print("  %-16s %6d vertices from %s, %d influences" % (
            name, len(kept), src_name, len(cmds.skinCluster(skin, q=True, influence=True))))
    # the source's meshes and their history out, the piece's group in
    cmds.delete("|MESH")
    # the copies took a number while the source's mesh of the same name stood (`Pants2`): their names
    for mesh_id, skin_id, _src, _kept, name in made:
        mesh = cmds.rename(path(mesh_id), name)
        cmds.rename(cmds.listRelatives(path(mesh_id), shapes=True, fullPath=True, noIntermediate=True)[0],
                    name + "Shape")
        cmds.rename(cmds.ls(skin_id)[0], name + "_skinCluster")
        assert leaf(path(mesh_id)) == name, (mesh, name)
    group = cmds.createNode("transform", name=key, skipSelect=True)
    for mesh_id, _skin_id, _src, _kept, _name in made:
        cmds.parent(path(mesh_id), "|" + key)
        cmds.setAttr(path(mesh_id) + ".inheritsTransform", 0)
        for a in ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"):
            cmds.setAttr(path(mesh_id) + "." + a, lock=True)
    for shape in cmds.ls("|" + key, dag=True, type="mesh", long=True, noIntermediate=True):
        cmds.sets(shape, edit=True, forceElement="initialShadingGroup")
    kinds = drop_unused(["|root", "|" + key])
    print("  deleted by type:", sorted(kinds.items(), key=lambda kv: -kv[1])[:12])
    skins = [cmds.ls(s)[0] for _m, s, _src, _k, _n in made]
    pose = whole_bind_pose(cmds.ls("|root", long=True)[0], skins)
    worst = max(bind_error(sc) for sc in skins)
    assert worst < 1e-4, worst
    assert cmds.ls(assemblies=True) == ["persp", "top", "front", "side", "root", key] or \
        sorted(cmds.ls(assemblies=True)) == sorted(["persp", "top", "front", "side", "root", key]), cmds.ls(assemblies=True)
    assert not cmds.ls(type="file"), cmds.ls(type="file")
    print("  %d skins off their bind %.2e, %s; assemblies %s" % (len(skins), worst, pose, cmds.ls(assemblies=True)))
    out = ASSETS + "/Armor/" + key + ".ma"
    save_ascii(out)


if __name__ == "__main__":
    step = sys.argv[1]
    if step == "rig":
        build_rig()
    elif step == "skeleton":
        build_skeleton()
    elif step == "armor":
        build_armor(sys.argv[2])
    else:
        raise SystemExit("unknown step " + step)
    maya.standalone.uninitialize()
