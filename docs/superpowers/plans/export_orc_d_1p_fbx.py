"""The Orc D's first-person skeletal mesh on its own, as an FBX: the skeleton and `Orc_D_1P`, nothing else.

    mayapy export_orc_d_1p_fbx.py [<out .fbx>] [--overwrite]

2026-09-28, the animator: «Отэкспортируй отдельный файл орка для 1p только с новым мешем».
mayapy STANDALONE, the shape of `export_creep_skeleton_fbx.py`: `assets/Orc_D_Rig.ma` imported into
an empty scene (plain names); every game bone's world matrix recorded, the rig's constraints on the
skeleton deleted and each bone re-seated from its matrix (the bind pose, as the rig stands at build
pose); `Orc_D_1P` out of the rig's Geometry group to world level, visible (in the asset `Main.view`
drives it and shows the 3P by default); the 3P and the whole AdvancedSkeleton `Group` deleted. The
file is our export layout -- Cascadeur's, `Armature` rotated -90 X over `root` (maya_uebridge.fbxlayout,
as every FBX of ours since 2026-09-25) -- at 30 fps, the 95 bones (Unreal's 91 plus camera_root,
camera_bone, weapon_r, weapon_l, the rig's own) and the one mesh with its skin at the bind, its
smoothing groups, and its three materials (body, cloth, and the cloth's cut-out worn only where
there is a cut, trap 95) with their images EMBEDDED -- one file, nothing beside it to lose. Our
markers stay home (they would ride in as user properties); the materials take plain names.

Then read back from a copy in a temp folder (the importer extracts embedded images into a `.fbm`
folder beside the file it reads, which must not be the animator's): the header, the tree, the file
holding each image byte for byte and none of the rig or the 3P; and imported: 95 joints under
`Armature`, root with no orientation of its own, one mesh, every vertex where the asset has it, every
weight the asset's, the smoothing, the uvs, the faces per material, a texture on every colour, the
normal maps, the cut.
"""
import collections
import math
import os
import shutil
import struct
import sys
import tempfile
import zlib

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma

for p in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.abspath(os.path.join(HERE, "..", "..", "..", "SkeldarAnim"))
ASSETS = os.path.join(PLUGIN, "assets").replace("\\", "/")
ASSET = ASSETS + "/Orc_D_Rig.ma"
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
OUT = (ARGS[0] if ARGS else "C:/!!!Work/Animations/Rigs/Characters/Orc_D_1P.fbx").replace("\\", "/")
OVERWRITE = "--overwrite" in sys.argv
MESH = "Orc_D_1P"
# the asset's material -> the name it takes in the file
MATERIALS = {"skeldarTexture_Orc_D_Body": "Orc_D_Body_Mat", "skeldarTexture_Orc_D_Cloth": "Orc_D_Cloth_Mat",
             "skeldarTexture_Orc_D_ClothCut": "Orc_D_ClothCut_Mat"}
FACES = {"Orc_D_Body_Mat": 13243, "Orc_D_Cloth_Mat": 20016, "Orc_D_ClothCut_Mat": 106}
sys.path.insert(0, PLUGIN)
from maya_uebridge import fbxlayout
from maya_scenesetup import colour


def uid(n):
    return cmds.ls(n, uuid=True)[0]


def path(u):
    return cmds.ls(u, long=True)[0]


def wm(n):
    return om.MMatrix(cmds.getAttr(n + ".worldMatrix[0]"))


def live(tr):
    return [s for s in cmds.listRelatives(tr, shapes=True, fullPath=True) if not cmds.getAttr(s + ".intermediateObject")][0]


def mfn(shape):
    sel = om.MSelectionList(); sel.add(shape)
    return om.MFnMesh(sel.getDagPath(0))


def weights(shape):
    """{vertex: {joint leaf: weight}} of the one skinCluster on `shape`"""
    sc = cmds.ls(cmds.listHistory(shape) or [], type="skinCluster")[0]
    sel = om.MSelectionList(); sel.add(sc); sel.add(shape)
    fn = oma.MFnSkinCluster(sel.getDependNode(0))
    dag = sel.getDagPath(1)
    comp = om.MFnSingleIndexedComponent().create(om.MFn.kMeshVertComponent)
    om.MFnSingleIndexedComponent(comp).setCompleteData(mfn(shape).numVertices)
    flat, n = fn.getWeights(dag, comp)
    names = [p.partialPathName().split("|")[-1].split(":")[-1] for p in fn.influenceObjects()]
    return [dict((names[i], flat[v * n + i]) for i in range(n) if flat[v * n + i] > 1e-9)
            for v in range(len(flat) // n)], sc


def hard(shape):
    """(the INTERIOR hard edges by their vertex pair, interior edges, border edges). A border edge
    has one face and its flag shades nothing, and the importer brings every border back hard; the
    mesh Unreal exported is split along its normal seams, so its 5345 hard edges ARE borders, every
    interior edge smooth -- and the 1P's neck, where the head was cut off the 3P, kept the 3P's
    smooth flag on its 8 new border edges (measured 2026-09-28)."""
    fn = mfn(shape)
    it = om.MItMeshEdge(om.MSelectionList().add(shape).getDagPath(0))
    out, interior, border = set(), 0, 0
    while not it.isDone():
        if it.onBoundary():
            border += 1
        else:
            interior += 1
            if not fn.isEdgeSmooth(it.index()):
                a, b = it.vertexId(0), it.vertexId(1)
                out.add((min(a, b), max(a, b)))
        it.next()
    return out, interior, border


def faces_by_material(shape):
    out = {}
    for sg in set(cmds.listConnections(shape, type="shadingEngine") or []):
        mats = cmds.listConnections(sg + ".surfaceShader") or []
        members = cmds.ls(cmds.sets(sg, q=True) or [], flatten=True)
        count = 0
        for m in members:
            if ".f[" in m:
                count += 1
            elif cmds.ls(m, long=True)[0] in (shape, cmds.listRelatives(shape, parent=True, fullPath=True)[0]):
                count += mfn(shape).numPolygons
        out[mats[0] if mats else sg] = count
    return out


# ------------------------------------------------------------------ the asset, reduced to the 1P
cmds.file(new=True, force=True)
cmds.file(ASSET, i=True, executeScriptNodes=False)
root = cmds.ls("|root", type="joint", long=True)[0]
joints = sorted([root] + cmds.listRelatives(root, allDescendents=True, type="joint", fullPath=True), key=lambda j: j.count("|"))
world = [(uid(j), wm(j)) for j in joints]
cons = cmds.listRelatives(root, allDescendents=True, type="constraint", fullPath=True) or []
cmds.delete(cons)
for u, m in world:
    j = path(u)
    for a in ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"):
        cmds.setAttr(j + "." + a, lock=False)
    cmds.xform(j, worldSpace=True, matrix=list(m))
drift = max(max(abs(a - b) for a, b in zip(list(m), list(wm(path(u))))) for u, m in world)
print("skeleton: %d joints, %d of the rig's constraints deleted, re-seated to %.1e" % (len(joints), len(cons), drift))

tr = cmds.ls("|Group|Geometry|" + MESH, type="transform", long=True)[0]
mesh_uuid = uid(tr)
world_before = wm(tr)
for plug in cmds.listConnections(tr + ".visibility", source=True, destination=False, plugs=True) or []:
    cmds.disconnectAttr(plug, tr + ".visibility")
cmds.setAttr(tr + ".visibility", True)
cmds.parent(tr, world=True, relative=True)          # Group and Geometry stand at identity
tr = path(mesh_uuid)
assert max(abs(a - b) for a, b in zip(list(world_before), list(wm(tr)))) < 1e-9, "the mesh moved leaving the group"
cmds.delete(cmds.ls("|Group|Geometry|Orc_D_3P", long=True))
cmds.delete("|Group")
shape = live(tr)
fn = mfn(shape)
pts_before = fn.getPoints(om.MSpace.kWorld)
w_before, skin = weights(shape)
hard_before = hard(shape)
uv_before = [fn.getPolygonUV(f, k, "map1") for f in range(0, fn.numPolygons, 11) for k in range(fn.polygonVertexCount(f))]
print("%s: %d vertices, %d faces, %d influences; edges: %d interior (%d of them hard), %d border; skin %s at bind pose %s" % (
    MESH, fn.numVertices, fn.numPolygons, len(cmds.skinCluster(skin, q=True, influence=True)), hard_before[1],
    len(hard_before[0]), hard_before[2], skin, cmds.listConnections(skin + ".bindPose")))
assert (fn.numVertices, fn.numPolygons) == (19458, 33365) and hard_before[1] > 0
assert not cmds.ls(type="blendShape") or not cmds.ls(cmds.listHistory(shape) or [], type="blendShape")

# the materials: plain names, our markers out, the images the shipped ones
images = {}
for old, new in MATERIALS.items():
    assert cmds.objExists(old), old
    if cmds.attributeQuery(colour.TEXTURE_MARKER, node=old, exists=True):
        cmds.deleteAttr(old + "." + colour.TEXTURE_MARKER)
    sg = (cmds.listConnections(old + ".outColor", type="shadingEngine") or [None])[0]
    cmds.rename(old, new)
    if sg:
        cmds.rename(sg, new + "SG")
for f in cmds.ls(type="file"):
    if cmds.attributeQuery(colour.ASSET_IMAGE, node=f, exists=True):
        image = ASSETS + "/" + cmds.getAttr(f + "." + colour.ASSET_IMAGE)
        cmds.setAttr(f + ".fileTextureName", image, type="string")
        cmds.deleteAttr(f + "." + colour.ASSET_IMAGE)
        images[f] = image
worn_before = faces_by_material(shape)
print("materials on the 1P: %s" % worn_before)
assert worn_before == FACES, worn_before
used = set()
for mat in FACES:
    for h in cmds.listHistory(mat) or []:
        if cmds.nodeType(h) == "file":
            used.add(images[h])
assert used and all(os.path.isfile(i) for i in used), used
print("images: %s" % sorted(os.path.basename(i) for i in used))

# 30 fps, the project's and Cascadeur's (trap 80); a skeletal mesh has no keys to retime
cmds.currentUnit(time="ntsc", updateAnimation=False)

if os.path.exists(OUT) and not OVERWRITE:
    raise RuntimeError("%s exists -- not overwriting it (--overwrite)" % OUT)
if not os.path.isdir(os.path.dirname(OUT)):
    os.makedirs(os.path.dirname(OUT))
mel.eval("FBXResetExport")
for option in ("FBXExportSkins -v true", "FBXExportShapes -v true", "FBXExportSmoothingGroups -v true", "FBXExportHardEdges -v false",
               "FBXExportSmoothMesh -v false", "FBXExportTangents -v false", "FBXExportInputConnections -v false",
               "FBXExportConstraints -v false", "FBXExportCameras -v false", "FBXExportLights -v false",
               "FBXExportBakeComplexAnimation -v false", "FBXExportEmbeddedTextures -v true",
               "FBXExportSkeletonDefinitions -v true", "FBXExportUpAxis y", "FBXExportInAscii -v false"):
    mel.eval(option)
with fbxlayout.wrapped(root, fbxlayout.WRAPPER_NAME) as (wrapper, note):
    assert wrapper, note
    # the bind pose again over the wrapper and every joint, the skin on it (trap 79)
    members = [wrapper] + cmds.ls(wrapper, dag=True, type="joint", long=True)
    pose = cmds.dagPose(members, save=True, bindPose=True, name="exportBindPose")
    pose = pose[0] if isinstance(pose, (list, tuple)) else pose
    strays = [m for m in cmds.ls(cmds.dagPose(pose, q=True, members=True) or [], long=True) if m not in members]
    if strays:
        cmds.dagPose(strays, remove=True, name=pose)
    cmds.connectAttr(pose + ".message", skin + ".bindPose", force=True)
    cmds.select([wrapper, path(mesh_uuid)], replace=True)
    mel.eval('FBXExport -f "%s" -s' % OUT)
print("exported %s (%.1f MB)" % (OUT, os.path.getsize(OUT) / 1e6))

# ------------------------------------------------------------------ the file, as any FBX reader sees it
Node = collections.namedtuple("Node", "name props children")


def parse(file_path):
    data = open(file_path, "rb").read()
    wide = struct.unpack_from("<I", data, 23)[0] >= 7500

    def prop(pos):
        t = chr(data[pos]); pos += 1
        sc = {"Y": "<h", "C": "<?", "I": "<i", "F": "<f", "D": "<d", "L": "<q"}
        if t in sc:
            return struct.unpack_from(sc[t], data, pos)[0], pos + struct.calcsize(sc[t])
        if t in "fdlib":
            n, enc, clen = struct.unpack_from("<III", data, pos); pos += 12
            raw = data[pos:pos + clen]; pos += clen
            if enc:
                raw = zlib.decompress(raw)
            return list(struct.unpack("<%d%s" % (n, {"f": "f", "d": "d", "l": "q", "i": "i", "b": "?"}[t]), raw)), pos
        n = struct.unpack_from("<I", data, pos)[0]; pos += 4
        raw = data[pos:pos + n]
        return (raw.decode("utf-8", "replace") if t == "S" else raw), pos + n

    def node(pos):
        if wide:
            end, np_, _ = struct.unpack_from("<QQQ", data, pos); pos += 24
        else:
            end, np_, _ = struct.unpack_from("<III", data, pos); pos += 12
        nl = data[pos]; pos += 1
        if end == 0:
            return None, pos
        name = data[pos:pos + nl].decode(); pos += nl
        props = [None] * np_
        for i in range(np_):
            props[i], pos = prop(pos)
        kids = []
        while pos < end:
            if data[pos:end].strip(b"\0") == b"":
                break
            k, pos = node(pos)
            if k is None:
                break
            kids.append(k)
        return Node(name, props, kids), end

    pos, top = 27, []
    while pos < len(data) - 200:
        n, pos = node(pos)
        if n is None:
            break
        top.append(n)
    return Node("", [], top), data


def kid(n, name):
    return next((c for c in n.children if c.name == name), None)


def p70(n):
    block = kid(n, "Properties70")
    return dict((p.props[0], p.props[4:]) for p in (block.children if block else []))


doc, data = parse(OUT)
g = p70(kid(doc, "GlobalSettings"))
v = lambda k: (g.get(k) or [None])[0]
header = ("%s%s" % ("+" if v("UpAxisSign") == 1 else "-", "XYZ"[v("UpAxis")]),
          "%s%s" % ("+" if v("FrontAxisSign") == 1 else "-", "XYZ"[v("FrontAxis")]), v("UnitScaleFactor"), v("TimeMode"))
objects = kid(doc, "Objects").children
models = dict((m.props[0], m) for m in objects if m.name == "Model")
parent = dict((c.props[1], c.props[2]) for c in kid(doc, "Connections").children
              if c.props[0] == "OO" and c.props[1] in models and (c.props[2] in models or c.props[2] == 0))
name = lambda u: models[u].props[1].split("\x00")[0] if u else ""
tops = sorted((name(u), models[u].props[2]) for u in models if not parent.get(u))
limbs = [u for u in models if models[u].props[2] in ("Root", "LimbNode")]      # `root` is written a Root
meshes = [name(u) for u in models if models[u].props[2] == "Mesh"]
arm = [u for u in models if name(u) == "Armature"]
file_materials = sorted(m.props[1].split("\x00")[0] for m in objects if m.name == "Material")
videos = [m for m in objects if m.name == "Video"]
embedded = dict((os.path.basename(i), data.find(open(i, "rb").read()) >= 0) for i in sorted(used))
print("header (up, front, unit, time mode): %s" % (header,))
print("top of the tree: %s; %d bones, meshes %s; Armature Lcl Rotation %s" % (
    tops, len(limbs), meshes, p70(models[arm[0]]).get("Lcl Rotation") if arm else None))
print("materials in the file: %s; %d embedded images, each shipped image in the file byte for byte: %s" % (
    file_materials, len(videos), embedded))
leaks = [w for w in (b"skeldar", b"Orc_D_3P", b"Orc_D_Eye", b"FitSkeleton", b"MotionSystem", b"Main", b"viewCondition") if w in data]
print("the rig / the 3P / our markers in the file: %s" % leaks)
assert header == ("+Y", "+Z", 1.0, 6), header
assert tops == [("Armature", "Null"), (MESH, "Mesh")] and meshes == [MESH] and len(limbs) == len(joints)
assert file_materials == sorted(FACES) and all(embedded.values()) and not leaks

# ------------------------------------------------------------------ imported back
scratch = tempfile.mkdtemp(prefix="orc_d_1p_")
copy = os.path.join(scratch, os.path.basename(OUT)).replace("\\", "/")
shutil.copyfile(OUT, copy)
cmds.file(new=True, force=True)
mel.eval('FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;')
mel.eval('FBXImport -f "%s";' % copy)
back_root = cmds.ls("root", type="joint", long=True)[0]
up = cmds.listRelatives(back_root, parent=True, fullPath=True) or []
jo = cmds.getAttr(back_root + ".jointOrient")[0]
print("read back: %d joints, root under %s turned %s, root jointOrient %s" % (
    len(cmds.ls(type="joint")), up, [round(x, 3) for x in cmds.getAttr(up[0] + ".rotate")[0]] if up else None,
    [round(x, 5) for x in jo]))
tr = cmds.ls(MESH, type="transform", long=True)[0]
shape = live(tr)
fn = mfn(shape)
pts = fn.getPoints(om.MSpace.kWorld)
worst_p = max(a.distanceTo(b) for a, b in zip(pts, pts_before))
w_back, _ = weights(shape)
worst_w = max(abs(a.get(j, 0.0) - b.get(j, 0.0)) for a, b in zip(w_back, w_before) for j in set(a) | set(b))
uv_back = [fn.getPolygonUV(f, k, "map1" if "map1" in fn.getUVSetNames() else fn.getUVSetNames()[0])
           for f in range(0, fn.numPolygons, 11) for k in range(fn.polygonVertexCount(f))]
worst_uv = max(max(abs(a[0] - b[0]), abs(a[1] - b[1])) for a, b in zip(uv_back, uv_before))
hard_back = hard(shape)
worn = faces_by_material(shape)
print("%s: %d vertices, %d faces, visible %s; every vertex where the asset has it: worst %.2e cm; "
      "weights: worst %.2e; uvs: worst %.2e; edges (interior hard, interior, border) %s, the asset's %s" % (
          MESH, fn.numVertices, fn.numPolygons, cmds.getAttr(tr + ".visibility"), worst_p, worst_w, worst_uv,
          (len(hard_back[0]),) + hard_back[1:], (len(hard_before[0]),) + hard_before[1:]))
print("faces per material read back: %s" % worn)
wiring = {}
for mat in worn:
    fed = {}
    for attr in ("color", "normalCamera", "transparency"):
        src = cmds.listConnections(mat + "." + attr, source=True, destination=False) or []
        if src and cmds.nodeType(src[0]) == "bump2d":
            files = cmds.listConnections(src[0] + ".bumpValue", source=True, destination=False) or []
            fed[attr] = ("bump2d interp %d" % cmds.getAttr(src[0] + ".bumpInterp"),
                         [os.path.basename(cmds.getAttr(f + ".fileTextureName")) for f in files])
        elif src and cmds.nodeType(src[0]) == "file":
            fed[attr] = os.path.basename(cmds.getAttr(src[0] + ".fileTextureName"))
    wiring[mat] = (cmds.nodeType(mat), fed)
    print("   %-20s %s %s" % (mat, cmds.nodeType(mat), fed))
extracted = [os.path.join(dp, f) for dp, _, fs in os.walk(scratch) for f in fs if not f.endswith(".fbx")]
same = dict((os.path.basename(i), any(open(e, "rb").read() == open(i, "rb").read() for e in extracted)) for i in sorted(used))
print("images the import extracted, each equal to the shipped one: %s" % same)
assert up and up[0] == "|" + fbxlayout.WRAPPER_NAME and max(abs(x) for x in jo) < 1e-3
assert len(cmds.ls(type="joint")) == len(joints) and cmds.ls(type="mesh", noIntermediate=True) == [shape.split("|")[-1]]
assert worst_p < 1e-3 and worst_w < 1e-4 and worst_uv < 1e-5 and hard_back == hard_before and cmds.getAttr(tr + ".visibility")
assert worn == FACES and all(same.values())
assert all(w[0] == colour.SHADER and "color" in w[1] for w in wiring.values())
assert all("normalCamera" in wiring[m][1] for m in FACES) and "transparency" in wiring["Orc_D_ClothCut_Mat"][1]
shutil.rmtree(scratch, ignore_errors=True)
print("OK")
