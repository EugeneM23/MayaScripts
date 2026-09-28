"""Build SkeldarAnim/assets/Orc_D_Rig.ma: the shipped Orc rig wearing SK_Orc_Marauder_D.

    mayapy make_orc_d_rig_asset.py

mayapy STANDALONE.  2026-09-28 (spec: docs/superpowers/specs/2026-09-28-orc-d-textured-design.md).
Measured first: D's 91 joints stand where F's do -- every rest world matrix and every skin
bindPreMatrix equal to 0.0 (one `SKEL_Orc_Marauder`, one reference pose) -- so D needs no rig of
its own.  This opens `assets/Orc_Rig.ma` (script nodes NOT executed), takes its F mesh out, and puts
D's in, bound to the same game joints:

- `Orc_D_Body` in `Group|Geometry`, in F's shape: its transform the importer's Z-up turn, locked;
  its points, UVs and normals exactly the FBX's at bind -- a copy of the FBX's own output, not a
  rebuild -- **minus the Skirt_Proxy section** (885 faces, 489 vertices, one shell hovering 1.65 cm
  off the skirt: the cage Unreal's clothing asset was made from, not what Unreal draws).  Vertex and
  face ids compact in order; the map is checked by position.  One UV set, `map1` (Unreal's
  DiffuseUV; LightMapUV and the vertex colours are Unreal's business).
- its blendShape `Orc_D_Body_blendShapes` rebuilt with the 56 targets (52 ARKit face shapes, 4 elbow
  correctives), each sampled off the FBX's own blendShape at weight 1 on the bind, weights 0;
- its skinCluster `Orc_D_Body_skinCluster` on the RIG's game joints by name, with the FBX's weights
  vertex for vertex and the rig's whole bindPose1;
- three textured materials, one per Unreal material (body, cloth -- the Skirt_Sim section is cloth --
  and eye), each the one shader (`colour.SHADER` wearing `colour.LOOK`, `colour.TEXTURE_MARKER`),
  built from `assets/Orc_D/` (make_orc_d_textures.py): the colour map; for body and cloth the normal
  map through a bump2d in tangent-space-normals mode; for the cloth the cut-out on `transparency`.
  Every file node names its image RELATIVELY (`colour.ASSET_IMAGE`, "Orc_D/<file>"), and Add
  Character points it at the installed copy: no path of this machine is in the asset.

Then make_orc_rig_asset.py's clean-up, `.ma`, script-node blocks cut from the text (trap 74), and
banned words refused.  Refuses (raises) anything that does not measure right on the way.
"""
import os
import re
import sys

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402
import maya.api.OpenMayaAnim as oma  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
PLUGIN = os.path.join(REPO, "SkeldarAnim")
sys.path.insert(0, PLUGIN)
from maya_scenesetup import colour  # noqa: E402

SRC_RIG = os.path.join(PLUGIN, "assets", "Orc_Rig.ma").replace("\\", "/")
FBX = os.path.join(REPO, "sources", "orc", "SK_Orc_Marauder_D.fbx").replace("\\", "/")
OUT = os.path.join(PLUGIN, "assets", "Orc_D_Rig.ma").replace("\\", "/")
NS = "srcD"
MESH = "Orc_D_Body"
MAPS = "Orc_D/"
PROXY = (885, 489)            # faces, vertices of Unreal's Skirt_Proxy section, measured
BANNED = ("createNode script", "vaccine", "breed_gene", "C:/", "c:/", "Unreal Projects", "scratchpad",
          "Skirt_Proxy", NS + ":", "D:/Characters", "Orc_Low_Body_Normal", "arp_rig_name", "flip_fluid",
          "ori_name", "SK_Orc_Marauder_F_LOD0SG", "MI_Orc_Marauder")

for plugin in ("matrixNodes", "quatNodes", "fbxmaya"):
    cmds.loadPlugin(plugin, quiet=True)


def wm(node):
    return om.MMatrix(cmds.getAttr(node + ".worldMatrix[0]"))


def mdiff(a, b):
    return max(abs(x - y) for x, y in zip(list(a), list(b)))


def dag(node):
    sel = om.MSelectionList()
    sel.add(node)
    return sel.getDagPath(0)


def mfn(node):
    return om.MFnMesh(dag(node))


def leaf(path):
    return path.split("|")[-1].split(":")[-1]


def faces_of(engine):
    return sorted(int(f.split("[")[1].rstrip("]"))
                  for f in cmds.ls(cmds.sets(engine, q=True) or [], flatten=True) if ".f[" in f)


def unlock(node):
    locked = [a for a in ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz")
              if cmds.getAttr(node + "." + a, lock=True)]
    for a in locked:
        cmds.setAttr(node + "." + a, lock=False)
    return locked


def bind_error(skin):
    worst = 0.0
    for idx in cmds.getAttr(skin + ".matrix", multiIndices=True) or []:
        src = cmds.listConnections("%s.matrix[%d]" % (skin, idx), s=True, d=False)
        if src:
            m = om.MMatrix(cmds.getAttr("%s.bindPreMatrix[%d]" % (skin, idx))) * wm(src[0])
            worst = max(worst, mdiff(m, om.MMatrix()))
    return worst


def skin_of(shape):
    return cmds.ls(cmds.listHistory(shape, pruneDagObjects=True) or [], type="skinCluster")[0]


def file_node(relative, name, raw):
    """A file node wired to a place2dTexture as Hypershade wires one, naming its image RELATIVELY
    and marked with colour.ASSET_IMAGE; `raw` for data (normals, masks) that must not be decoded
    from sRGB -- and the colour-space file rules off, or Add's relink would re-decide it."""
    node = cmds.shadingNode("file", asTexture=True, isColorManaged=True, name=name)
    place = cmds.shadingNode("place2dTexture", asUtility=True, name=name + "_place2d")
    for attr in colour._PLACE2D:
        cmds.connectAttr(place + "." + attr, node + "." + attr, force=True)
    cmds.connectAttr(place + ".outUV", node + ".uvCoord", force=True)
    cmds.connectAttr(place + ".outUvFilterSize", node + ".uvFilterSize", force=True)
    cmds.setAttr(node + ".fileTextureName", relative, type="string")
    mark(node, relative, raw)
    return node


def mark(node, relative, raw):
    cmds.setAttr(node + ".ignoreColorSpaceFileRules", 1)
    cmds.setAttr(node + ".colorSpace", "Raw" if raw else "sRGB", type="string")
    if not cmds.attributeQuery(colour.ASSET_IMAGE, node=node, exists=True):
        cmds.addAttr(node, longName=colour.ASSET_IMAGE, dataType="string")
    cmds.setAttr(node + "." + colour.ASSET_IMAGE, relative, type="string")


def material(key, colour_map, normal_map=None, cut_map=None):
    """The one shader with Unreal's textures: colour, normal through a bump2d, cut-out."""
    mat, engine = colour.make_textured_material(MAPS + colour_map, key)
    colour_file = cmds.listConnections(mat + ".color", type="file")[0]
    colour_file = cmds.rename(colour_file, key + "_color")
    cmds.rename(cmds.listConnections(colour_file + ".uvCoord")[0], key + "_color_place2d")
    mark(colour_file, MAPS + colour_map, raw=False)
    if normal_map:
        normal = file_node(MAPS + normal_map, key + "_normal", raw=True)
        cmds.setAttr(normal + ".alphaIsLuminance", 1)
        bump = cmds.shadingNode("bump2d", asUtility=True, name=key + "_bump")
        cmds.setAttr(bump + ".bumpInterp", 1)                    # tangent space normals
        cmds.setAttr(bump + ".bumpDepth", 1.0)
        cmds.connectAttr(normal + ".outAlpha", bump + ".bumpValue", force=True)
        cmds.connectAttr(bump + ".outNormal", mat + ".normalCamera", force=True)
    if cut_map:
        cut = file_node(MAPS + cut_map, key + "_cut", raw=True)
        cmds.setAttr(cut + ".alphaIsLuminance", 1)
        cmds.connectAttr(cut + ".outTransparency", mat + ".transparency", force=True)
    return mat, engine


def cut_material(cloth, key, cut_map):
    """The cloth's CUT-OUT faces' material: the cloth's own colour and normal (the same file
    nodes), plus the cut on `transparency`.

    Only the faces whose uvs touch a cut texel wear it (`faces_touching_cut`). Viewport 2.0's
    default transparency (Object Sorting) draws a material with a transparency input in the
    transparent pass WHOLE, and inside one render item it does not sort by depth: with the cut on
    the whole cloth the vest's leather drew over the shoulder plates, the belt over its buckle,
    the wraps over the knee pads (2026-09-28, the animator: «определенные части орка
    просвечиваются»). The rest of the cloth is opaque and depth-tested like any mesh."""
    mat = cmds.shadingNode(colour.SHADER, asShader=True, name="skeldarTexture_" + key)
    colour.dress(mat)
    colour_file = cmds.listConnections(cloth + ".color", type="file")[0]
    cmds.connectAttr(colour_file + ".outColor", mat + ".color", force=True)
    bump = cmds.listConnections(cloth + ".normalCamera", type="bump2d")[0]
    cmds.connectAttr(bump + ".outNormal", mat + ".normalCamera", force=True)
    cut = file_node(MAPS + cut_map, key + "_cut", raw=True)
    cmds.setAttr(cut + ".alphaIsLuminance", 1)
    cmds.connectAttr(cut + ".outTransparency", mat + ".transparency", force=True)
    cmds.addAttr(mat, longName=colour.TEXTURE_MARKER, dataType="string")
    cmds.setAttr(mat + "." + colour.TEXTURE_MARKER, cmds.getAttr(colour_file + ".fileTextureName"),
                 type="string")
    engine = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=mat + "SG")
    cmds.connectAttr(mat + ".outColor", engine + ".surfaceShader", force=True)
    return mat, engine


def cut_texels(mask_path):
    """The cut-out mask as booleans, rows by v (MImage stores the bottom row first, which is v 0),
    grown by one texel: the viewport's bilinear filter reaches a texel beyond the edge."""
    import ctypes
    import numpy as np
    img = om.MImage()
    img.readFromFile(mask_path)
    w, h = img.getSize()
    px = np.frombuffer(ctypes.string_at(img.pixels(), w * h * img.depth()), np.uint8)
    cut = px.reshape(h, w, img.depth())[..., 0] < 128
    grown = cut.copy()
    grown[1:] |= cut[:-1]
    grown[:-1] |= cut[1:]
    grown[:, 1:] |= cut[:, :-1]
    grown[:, :-1] |= cut[:, 1:]
    return grown


def faces_touching_cut(shape, faces, mask_path):
    """Which of `faces` has a cut texel inside its uv polygon (map1): a summed-area table rules
    out the faces whose uv bounding box holds none, texel centres are tested inside the fan
    triangles of the rest."""
    import numpy as np
    cut = cut_texels(mask_path)
    h, w = cut.shape
    table = np.pad(cut.astype(np.int32).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    fn_ = mfn(shape)
    touching = []
    for f in faces:
        uv = [fn_.getPolygonUV(f, j, "map1") for j in range(fn_.polygonVertexCount(f))]
        xs = [u * w - 0.5 for u, _v in uv]
        ys = [v * h - 0.5 for _u, v in uv]
        x0, x1 = max(0, int(np.floor(min(xs)))), min(w - 1, int(np.ceil(max(xs))))
        y0, y1 = max(0, int(np.floor(min(ys)))), min(h - 1, int(np.ceil(max(ys))))
        if x1 < x0 or y1 < y0:
            continue
        if table[y1 + 1, x1 + 1] - table[y0, x1 + 1] - table[y1 + 1, x0] + table[y0, x0] == 0:
            continue
        gy, gx = np.nonzero(cut[y0:y1 + 1, x0:x1 + 1])
        px, py = gx + x0, gy + y0
        for k in range(1, len(uv) - 1):
            (ax, ay), (bx, by), (cx, cy) = (xs[0], ys[0]), (xs[k], ys[k]), (xs[k + 1], ys[k + 1])
            d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
            if abs(d) < 1e-12:
                continue
            l1 = ((by - cy) * (px - cx) + (cx - bx) * (py - cy)) / d
            l2 = ((cy - ay) * (px - cx) + (ax - cx) * (py - cy)) / d
            if np.any((l1 >= -0.02) & (l2 >= -0.02) & (1 - l1 - l2 >= -0.02)):
                touching.append(f)
                break
        else:
            # a face smaller than a texel: its own corners and centre sampled
            if len(uv) and any(cut[min(h - 1, max(0, int(round(y)))), min(w - 1, max(0, int(round(x))))]
                               for x, y in list(zip(xs, ys)) + [(sum(xs) / len(xs), sum(ys) / len(ys))]):
                touching.append(f)
    return touching


# ------------------------------------------------------------------ the shipped rig, F out
cmds.file(SRC_RIG, open=True, force=True, executeScriptNodes=False)
root = cmds.ls("|root", type="joint", long=True)[0]
game = dict((leaf(j), j) for j in cmds.ls(root, dag=True, type="joint", long=True))
assert len(game) == 95, len(game)
f_mesh = "|Group|Geometry|Orc_Body"
f_shape = cmds.listRelatives(f_mesh, shapes=True, fullPath=True, noIntermediate=True)[0]
f_skin = skin_of(f_shape)
print("Orc_Rig.ma: 95 game joints, F's skin off its bind %.2e" % bind_error(f_skin))
assert bind_error(f_skin) < 1e-4, "the rig is not at its build pose"
f_history = [h for h in cmds.listHistory(f_shape) if cmds.nodeType(h) in
             ("skinCluster", "blendShape", "tweak", "groupParts", "groupId")]
f_engines = cmds.listConnections(f_shape, type="shadingEngine") or []
cmds.delete(f_mesh)
cmds.delete([n for n in f_history if cmds.objExists(n)])

# ------------------------------------------------------------------ D's FBX in a namespace
cmds.namespace(add=NS)
cmds.namespace(set=NS)
mel.eval("FBXResetImport")
mel.eval("FBXImportMode -v add")
mel.eval('FBXImport -f "%s"' % FBX)
cmds.namespace(set=":")
src = cmds.ls("|%s:SK_Orc_Marauder_D|%s:SK_Orc_Marauder_D" % (NS, NS), long=True)
assert len(src) == 1, cmds.ls(NS + ":*", assemblies=True)[:6]
src = src[0]
src_shape = cmds.listRelatives(src, shapes=True, fullPath=True, noIntermediate=True)[0]
src_skin = skin_of(src_shape)
src_bs = cmds.ls(cmds.listHistory(src_shape, pruneDagObjects=True), type="blendShape")[0]

# every source influence is a game joint of the rig, standing where the FBX's bind has it
src_infl = cmds.skinCluster(src_skin, q=True, influence=True)
worst = 0.0
for idx in cmds.getAttr(src_skin + ".matrix", multiIndices=True):
    joint = cmds.listConnections("%s.matrix[%d]" % (src_skin, idx), s=True, d=False)[0]
    bind = om.MMatrix(cmds.getAttr("%s.bindPreMatrix[%d]" % (src_skin, idx))).inverse()
    worst = max(worst, mdiff(bind, wm(game[leaf(joint)])))
print("D: %d influences, the rig's game joints on the FBX's bind to %.2e" % (len(src_infl), worst))
assert worst < 1e-3, worst

# the sections, by the FBX's materials
engines = {}
for sg in sorted(set(cmds.listConnections(src_shape, type="shadingEngine") or [])):
    mat = leaf((cmds.listConnections(sg + ".surfaceShader") or ["?"])[0])
    if re.match(r"^MI_Orc_Marauder_Cloth_Inst_\d+$", mat):
        engines.setdefault("proxy", []).append(sg)
    elif mat == "MI_Orc_Marauder_Cloth_Inst":
        engines.setdefault("cloth", []).append(sg)
    elif mat.startswith("MI_Orc_Marauder_Body"):
        engines.setdefault("body", []).append(sg)
    elif mat.startswith("MI_Orc_Marauder_Eye"):
        engines.setdefault("eye", []).append(sg)
    else:
        raise RuntimeError("a section this was not measured on: %s (%s)" % (sg, mat))
assert all(len(engines.get(k, [])) == 1 for k in ("proxy", "cloth", "body", "eye")), engines
section = dict((k, faces_of(v[0])) for k, v in engines.items())
fn = mfn(src_shape)
n_faces, n_verts = fn.numPolygons, fn.numVertices
assert sum(len(v) for v in section.values()) == n_faces, "a face in no section"
proxy_faces = set(section["proxy"])
proxy_verts = set(v for f in proxy_faces for v in fn.getPolygonVertices(f))
other_verts = set(v for f in range(n_faces) if f not in proxy_faces for v in fn.getPolygonVertices(f))
assert (len(proxy_faces), len(proxy_verts)) == PROXY, (len(proxy_faces), len(proxy_verts))
assert not proxy_verts & other_verts, "the proxy shares vertices with the mesh"
kept_verts = [v for v in range(n_verts) if v not in proxy_verts]
kept_faces = [f for f in range(n_faces) if f not in proxy_faces]
print("D: %d vertices, %d faces; the proxy's %d faces / %d vertices go" % ((n_verts, n_faces) + PROXY))

# ------------------------------------------------------------------ the samples, at bind
weights = cmds.blendShape(src_bs, q=True, weight=True) or []
aliases = cmds.aliasAttr(src_bs, q=True) or []
alias_of = dict((aliases[i + 1], aliases[i]) for i in range(0, len(aliases), 2))
names = [alias_of["weight[%d]" % i] for i in range(len(weights))]
assert len(names) == 56, len(names)
for i in range(len(weights)):
    cmds.setAttr("%s.weight[%d]" % (src_bs, i), 0.0)
cmds.dgdirty(src_shape)
base_world = fn.getPoints(om.MSpace.kWorld)
targets = []
for i in range(len(weights)):
    cmds.setAttr("%s.weight[%d]" % (src_bs, i), 1.0)
    cmds.dgdirty(src_shape)
    targets.append(mfn(src_shape).getPoints(om.MSpace.kObject))
    cmds.setAttr("%s.weight[%d]" % (src_bs, i), 0.0)
cmds.dgdirty(src_shape)
moved = max(max(t[v].distanceTo(mfn(src_shape).getPoints(om.MSpace.kObject)[v]) for v in range(0, n_verts, 97))
            for t in targets[:4])
assert moved > 1e-3, "the blendShape samples did not move"

# the FBX's own weights, vertex by vertex, and its skinning settings
src_fn = oma.MFnSkinCluster(om.MSelectionList().add(src_skin).getDependNode(0))
src_path = dag(src_shape)
comp = om.MFnSingleIndexedComponent().create(om.MFn.kMeshVertComponent)
om.MFnSingleIndexedComponent(comp).setCompleteData(n_verts)
src_weights, n_infl = src_fn.getWeights(src_path, comp)
src_names = [leaf(p.fullPathName()) for p in src_fn.influenceObjects()]
skin_settings = dict((a, cmds.getAttr(src_skin + "." + a))
                     for a in ("skinningMethod", "maxInfluences", "maintainMaxInfluences", "normalizeWeights"))

# ------------------------------------------------------------------ Orc_D_Body
dup = cmds.duplicate(src, name=":" + MESH)[0]
dup = cmds.ls(dup, long=True)[0]
for shape in cmds.listRelatives(dup, shapes=True, fullPath=True) or []:
    if cmds.getAttr(shape + ".intermediateObject"):
        cmds.delete(shape)
unlock(dup)
# the properties Unreal's FBX carries on the mesh from its author's Blender (`*_HG`, `*_retopoflow`):
# nothing of ours, and an export would write them
for node in [dup] + (cmds.listRelatives(dup, shapes=True, fullPath=True) or []):
    for attr in cmds.listAttr(node, userDefined=True) or []:
        if cmds.attributeQuery(attr, node=node, exists=True):
            cmds.setAttr(node + "." + attr, lock=False)
            cmds.deleteAttr(node + "." + attr)
dup = cmds.parent(dup, world=True)[0]
dup = cmds.ls(dup, long=True)[0]
shape = cmds.listRelatives(dup, shapes=True, fullPath=True)[0]
shape = cmds.ls(cmds.rename(shape, ":" + MESH + "Shape"), long=True)[0]
dup_uid = cmds.ls(dup, uuid=True)[0]
# the component tags the copy carries from the FBX's shape name ITS deformers ("srcD:skinCluster1");
# ours make their own
for i in cmds.getAttr(shape + ".gtag", multiIndices=True) or []:
    cmds.removeMultiInstance("%s.gtag[%d]" % (shape, i), b=True)
cmds.delete(["%s.f[%d]" % (dup, f) for f in sorted(proxy_faces)])
cmds.delete(dup, constructionHistory=True)
dup = cmds.ls(dup_uid, long=True)[0]
shape = cmds.listRelatives(dup, shapes=True, fullPath=True)[0]
new_fn = mfn(shape)
assert (new_fn.numVertices, new_fn.numPolygons) == (len(kept_verts), len(kept_faces))
new_world = new_fn.getPoints(om.MSpace.kWorld)
drift = max(new_world[k].distanceTo(base_world[v]) for k, v in enumerate(kept_verts))
print("Orc_D_Body: %d vertices, %d faces; each where the FBX has its vertex to %.2e cm"
      % (new_fn.numVertices, new_fn.numPolygons, drift))
assert drift < 1e-5, "the vertex map is wrong: %.3e" % drift
for f in (0, len(kept_faces) // 2, len(kept_faces) - 1):
    old = [kept_verts.index(v) for v in fn.getPolygonVertices(kept_faces[f])]
    assert list(new_fn.getPolygonVertices(f)) == old, "the face map is wrong at %d" % f

uvsets = cmds.polyUVSet(shape, q=True, allUVSets=True)
assert uvsets[0] == "DiffuseUV", uvsets
for extra in uvsets[1:]:
    cmds.polyUVSet(shape, delete=True, uvSet=extra)
cmds.polyUVSet(shape, rename=True, uvSet="DiffuseUV", newUVSet="map1")
cmds.polyUVSet(shape, currentUVSet=True, uvSet="map1")
for cs in cmds.polyColorSet(shape, q=True, allColorSets=True) or []:
    cmds.polyColorSet(shape, delete=True, colorSet=cs)
cmds.setAttr(shape + ".displayColors", 0)
cmds.delete(dup, constructionHistory=True)
dup = cmds.ls(dup_uid, long=True)[0]
dup = cmds.ls(cmds.parent(dup, "|Group|Geometry")[0], long=True)[0]
shape = cmds.listRelatives(dup, shapes=True, fullPath=True)[0]
print("  uv sets %s, colour sets %s, under %s" % (cmds.polyUVSet(shape, q=True, allUVSets=True),
                                                  cmds.polyColorSet(shape, q=True, allColorSets=True), dup))

# the materials, per face
cmds.select(clear=True)
made = {"body": material("Orc_D_Body", "Orc_D_Body_Color.jpg", "Orc_D_Body_Normal.jpg"),
        "cloth": material("Orc_D_Cloth", "Orc_D_Cloth_Color.jpg", "Orc_D_Cloth_Normal.jpg"),
        "eye": material("Orc_D_Eye", "Orc_D_Eye_Color.jpg")}
made["cut"] = cut_material(made["cloth"][0], "Orc_D_ClothCut", "Orc_D_Cloth_Mask.png")
new_face = dict((f, k) for k, f in enumerate(kept_faces))
cloth_ids = [new_face[f] for f in section["cloth"]]
cut_ids = set(faces_touching_cut(shape, cloth_ids, os.path.join(PLUGIN, "assets", MAPS, "Orc_D_Cloth_Mask.png")))
faces_for = {"body": [new_face[f] for f in section["body"]], "eye": [new_face[f] for f in section["eye"]],
             "cloth": [i for i in cloth_ids if i not in cut_ids], "cut": sorted(cut_ids)}
for key in ("body", "cloth", "cut", "eye"):
    cmds.sets(["%s.f[%d]" % (dup, i) for i in faces_for[key]], edit=True, forceElement=made[key][1])
    print("  %-5s %s: %d faces" % (key, made[key][0], len(faces_for[key])))

# the blendShape: the 56 targets as meshes of the new topology, then gone (the deltas stay)
target_meshes = []
for name, pts in zip(names, targets):
    t = cmds.duplicate(dup, name=":" + name)[0]
    om.MFnMesh(dag(t)).setPoints(om.MPointArray([pts[v] for v in kept_verts]), om.MSpace.kObject)
    target_meshes.append(t)
blend = cmds.blendShape(target_meshes + [dup], name=MESH + "_blendShapes", frontOfChain=True)[0]
cmds.delete(target_meshes)
check = [0, 23, 55]
worst = 0.0
for i in check:
    cmds.setAttr("%s.weight[%d]" % (blend, i), 1.0)
    got = mfn(shape).getPoints(om.MSpace.kObject)
    worst = max(worst, max(got[k].distanceTo(targets[i][v]) for k, v in enumerate(kept_verts)))
    cmds.setAttr("%s.weight[%d]" % (blend, i), 0.0)
new_aliases = cmds.aliasAttr(blend, q=True)
print("  blendShape %s: %d targets, targets %s on the FBX's to %.2e" %
      (blend, len(cmds.blendShape(blend, q=True, weight=True)), check, worst))
assert worst < 1e-4 and len(cmds.blendShape(blend, q=True, weight=True)) == 56

# the skin: the rig's game joints, the FBX's weights
joints = [game[n] for n in src_names]
skin = cmds.skinCluster(joints, dup, toSelectedBones=True, bindMethod=0, normalizeWeights=1,
                        maximumInfluences=8, obeyMaxInfluences=False, name=MESH + "_skinCluster")[0]
for attr, value in skin_settings.items():
    try:
        cmds.setAttr(skin + "." + attr, value)
    except RuntimeError as exc:
        print("  (the FBX's %s = %s does not take: %s)" % (attr, value, str(exc).strip()))
# the bind pose saved again, WHOLE, over all 95 joints (trap 79: the FBX exporter drops a bind pose
# over one bad member) -- F's went with F's skin; dagPose -save takes the joints' constraint children
# too, and those come out again
made_pose = cmds.listConnections(skin + ".bindPose", type="dagPose") or []
for pose in set(made_pose + cmds.ls("bindPose*", type="dagPose")):
    if cmds.objExists(pose) and not pose.startswith(NS + ":"):
        cmds.delete(pose)
all_joints = cmds.ls("|root", dag=True, type="joint", long=True)
bind_pose = cmds.dagPose(all_joints, save=True, bindPose=True, name="skeldarBindPose_new")
bind_pose = bind_pose[0] if isinstance(bind_pose, (list, tuple)) else bind_pose
strays = [m for m in cmds.ls(cmds.dagPose(bind_pose, q=True, members=True) or [], long=True)
          if cmds.objectType(m) != "joint"]
if strays:
    cmds.dagPose(strays, remove=True, name=bind_pose)
cmds.connectAttr(bind_pose + ".message", skin + ".bindPose", force=True)
bind_pose = cmds.rename(bind_pose, "bindPose1")
dst_fn = oma.MFnSkinCluster(om.MSelectionList().add(skin).getDependNode(0))
dst_names = [leaf(p.fullPathName()) for p in dst_fn.influenceObjects()]
order = [dst_names.index(n) for n in src_names]
weights = om.MDoubleArray()
for v in kept_verts:
    for i in range(n_infl):
        weights.append(src_weights[v * n_infl + i])
dst_comp = om.MFnSingleIndexedComponent().create(om.MFn.kMeshVertComponent)
om.MFnSingleIndexedComponent(dst_comp).setCompleteData(len(kept_verts))
dst_fn.setWeights(dag(shape), dst_comp, om.MIntArray(order), weights, False)
got, _n = dst_fn.getWeights(dag(shape), dst_comp)
wdiff = max(abs(got[k * n_infl + order[i]] - src_weights[v * n_infl + i])
            for k in range(0, len(kept_verts), 53) for v in (kept_verts[k],) for i in range(n_infl))
print("  skin settings from the FBX: %s" % skin_settings)
print("  skin %s: %d influences, weights as the FBX's to %.2e, off its bind %.2e, bindPose %s"
      % (skin, len(dst_names), wdiff, bind_error(skin), cmds.listConnections(skin + ".bindPose")))
assert wdiff < 1e-9 and bind_error(skin) < 1e-4
cmds.dgdirty(shape)
posed = mfn(shape).getPoints(om.MSpace.kWorld)
still = max(posed[k].distanceTo(base_world[v]) for k, v in enumerate(kept_verts))
print("  at bind every vertex where the FBX has it to %.2e cm" % still)
assert still < 1e-3
for a in ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"):
    cmds.setAttr(dup + "." + a, lock=True)

# ------------------------------------------------------------------ the FBX out, the leftovers
cmds.namespace(removeNamespace=NS, deleteNamespaceContent=True)
deleted = []


def drop(nodes):
    for n in nodes:
        if cmds.objExists(n):
            try:
                cmds.lockNode(n, lock=False)
            except Exception:
                pass
            cmds.delete(n)
            deleted.append(n)


drop(cmds.ls(type="script"))
drop(cmds.ls(type="unknown") + cmds.ls(type="unknownDag"))
for plugin in cmds.unknownPlugin(query=True, list=True) or []:
    try:
        cmds.unknownPlugin(plugin, remove=True)
    except Exception:
        pass
drop([p for p in cmds.ls(type="dagPose") if not cmds.dagPose(p, query=True, members=True)])
drop([c for c in cmds.ls(type="animCurve") if not cmds.listConnections(c, source=False, destination=True)])
KEEP = {"initialShadingGroup", "initialParticleSE", "lambert1", "standardSurface1", "particleCloud1", "openPBR_shader1"}
for _ in range(8):
    doomed = [sg for sg in cmds.ls(type="shadingEngine") if sg not in KEEP and not cmds.sets(sg, query=True)]
    doomed += cmds.ls(cmds.listConnections(doomed, type="materialInfo") or [])
    doomed += [m for m in cmds.ls(materials=True) if m not in KEEP and not cmds.listConnections(m, type="shadingEngine")]
    doomed += [t for t in cmds.ls(textures=True) + cmds.ls(type="place2dTexture") + cmds.ls(type="bump2d")
               if not [d for d in cmds.listConnections(t, source=False, destination=True) or []
                       if cmds.nodeType(d) not in ("defaultTextureList", "defaultRenderUtilityList", "nodeGraphEditorInfo")]]
    doomed = [n for n in doomed if cmds.objExists(n)]
    if not doomed:
        break
    drop(sorted(set(doomed)))

# ------------------------------------------------------------------ what must be there
below = cmds.listRelatives("|root", allDescendents=True, type="joint")
assert len(below) == 94, len(below)
assert cmds.getAttr("|Group.skeldarRetarget") == "rotation"
assert cmds.listRelatives("|Group|Geometry", children=True) == [MESH], cmds.listRelatives("|Group|Geometry", children=True)
assert len(cmds.ls(type="skinCluster")) == 1 and len(cmds.ls(type="blendShape")) == 1
assert cmds.ls(type="dagPose") == ["bindPose1"], cmds.ls(type="dagPose")
assert len(cmds.dagPose("bindPose1", q=True, members=True)) == 95
assert not cmds.listAttr("|Group|Geometry|" + MESH, userDefined=True), cmds.listAttr("|Group|Geometry|" + MESH, userDefined=True)
assert not cmds.namespace(exists=NS)
ours = [m for m in cmds.ls(materials=True) if m not in KEEP]
assert sorted(ours) == sorted(m for m, _e in made.values()), ours
files = cmds.ls(type="file")
assert sorted(cmds.getAttr(f + "." + colour.ASSET_IMAGE) for f in files) == sorted(
    MAPS + n for n in ("Orc_D_Body_Color.jpg", "Orc_D_Body_Normal.jpg", "Orc_D_Cloth_Color.jpg",
                       "Orc_D_Cloth_Normal.jpg", "Orc_D_Cloth_Mask.png", "Orc_D_Eye_Color.jpg"))
final_shape = cmds.listRelatives("|Group|Geometry|" + MESH, shapes=True, fullPath=True)
print("component tags:", [(s_, [cmds.getAttr("%s.gtag[%d].gtagnm" % (s_, i)) for i in cmds.getAttr(s_ + ".gtag", multiIndices=True) or []]) for s_ in final_shape])
print("assemblies:", cmds.ls(assemblies=True))
print("deleted %d nodes (F's shading, the FBX's leftovers): %s ..." % (len(deleted), deleted[:10]))
print("materials:", ours, "files:", [(f, cmds.getAttr(f + ".fileTextureName"), cmds.getAttr(f + ".colorSpace")) for f in files])

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
print("script nodes cut from the text: %d" % cut)
bad = []
with open(OUT, encoding="utf-8", errors="replace") as fh:
    for n, line in enumerate(fh, 1):
        for word in BANNED:
            if word in line:
                bad.append((n, word, line.strip()[:120]))
if bad:
    os.rename(OUT, OUT + ".rejected")
    raise RuntimeError("banned content in the asset (kept as .rejected): %s" % bad[:10])
print("saved %s (%.1f MB)" % (OUT, os.path.getsize(OUT) / 1e6))
