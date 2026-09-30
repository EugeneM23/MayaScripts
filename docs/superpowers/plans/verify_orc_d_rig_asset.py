"""Standalone gates for the textured Orc D (assets/Orc_D_Rig.ma) going through the plugin.

    mayapy verify_orc_d_rig_asset.py <UE5 clip .fbx, e.g. Animations/Export/LongSword_Attack_Right_Heavy_3P.FBX> <scratch dir>

mayapy STANDALONE, an empty scene (2026-09-28; spec docs/superpowers/specs/2026-09-28-orc-d-textured-design.md).
Add Character twice with «Orc D [rig]» and once with «Creep [rig]» (the untextured «Orc [rig]» left the plugin the same day; a Manny until 2026-09-30, when the Manny became textured too), then everything checked against
the FBX Unreal wrote (sources/orc/SK_Orc_Marauder_D.fbx, imported into a `ref` namespace):

- each orc in its own namespace, marked rotation-only, at its bind, controls at default, no script
  node; the Orc D arriving TEXTURED -- its three materials the one shader, every file node on an
  image in the installed assets/Orc_D/, the palette untouched by it (the Creep still painted);
- the texture the file node samples IS the shipped image's pixels, the right way up;
- D's mesh: Unreal's minus the Skirt_Proxy, vertex for vertex where the FBX has it, its UVs and
  normals the FBX's, its 56 targets the FBX's, and -- the one that matters -- under a real pose
  (a retargeted take) every vertex where the FBX's OWN skin puts it with its joints on the rig's;
- the retarget through the button (rotations, lengths), the other two orcs unmoved;
- Recolour replaces the textures with a colour; the next Add is textured again;
- the export: 95 bones, no mesh.
"""
import ctypes
import json
import math
import os
import re
import sys

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

REPO = "C:/!!!Work/MayaScripts"
sys.path.insert(0, REPO + "/SkeldarAnim")
for p in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass
CLIP = sys.argv[1].replace("\\", "/")
SCRATCH = sys.argv[2].replace("\\", "/")
FBX = REPO + "/sources/orc/SK_Orc_Marauder_D.fbx"
FAILS = []
TOTAL = 22
ONE_P = json.load(open(REPO + "/sources/orc/orc_d_1p_faces.json"))


def gate(n, ok, msg):
    print("%s gate %02d: %s" % ("PASS" if ok else "FAIL", n, msg))
    sys.stdout.flush()
    if not ok:
        FAILS.append(n)


def wm(n):
    return om.MMatrix(cmds.getAttr(n + ".worldMatrix[0]"))


def rot(m):
    return om.MTransformationMatrix(m).rotation(asQuaternion=True)


def ang(a, b):
    q = a.inverse() * b
    return math.degrees(2 * math.acos(max(-1.0, min(1.0, abs(q.w)))))


def mdiff(a, b):
    return max(abs(x - y) for x, y in zip(list(a), list(b)))


def mfn(node):
    sel = om.MSelectionList()
    sel.add(node)
    return om.MFnMesh(sel.getDagPath(0))


def live_shape(transform):
    return [s for s in cmds.listRelatives(transform, shapes=True, fullPath=True) or []
            if not cmds.getAttr(s + ".intermediateObject")][0]


def bones(root):
    return dict((p.split("|")[-1].split(":")[-1], p)
                for p in [root] + cmds.listRelatives(root, ad=True, type="joint", fullPath=True))


def image(path):
    img = om.MImage()
    img.readFromFile(path)
    width, height = img.getSize()
    return width, height, ctypes.string_at(img.pixels(), width * height * img.depth())


def worn(shape):
    """{material: face count} on `shape`."""
    out = {}
    for sg in set(cmds.listConnections(shape, type="shadingEngine") or []):
        mat = (cmds.ls(cmds.listConnections(sg + ".surfaceShader", s=True, d=False) or [], materials=True) or ["?"])[0]
        members = [m for m in cmds.ls(cmds.sets(sg, q=True) or [], flatten=True, long=True)
                   if m.split(".")[0] in (shape, cmds.listRelatives(shape, parent=True, fullPath=True)[0])]
        n = sum(1 for m in members if ".f[" in m)
        if not n and members:
            n = cmds.polyEvaluate(shape, face=True)
        out[mat] = out.get(mat, 0) + n
    return out


cmds.file(new=True, force=True)
from maya_scenesetup import catalog, character, colour  # noqa: E402
import maya_rigs  # noqa: E402
import maya_asretarget as ar  # noqa: E402
import maya_rig_retarget as rr  # noqa: E402

orc_d = catalog.character_by_key("Orc_D_Rig")
gate(1, orc_d is not None and orc_d.textured and catalog.is_rig(orc_d) and orc_d.label in catalog.character_labels(),
     "the dropdown offers %s; «Orc D [rig]» textured" % catalog.character_labels())
free_before = colour.free_colour().name
texts = [character.add_character(orc_d, colour.PALETTE[0].rgb), character.add_character(orc_d, colour.PALETTE[0].rgb)]
free_after_d = colour.free_colour().name
texts.append(character.add_character(catalog.character_by_key("Creep_Rig"), colour.PALETTE[0].rgb))
for t in texts:
    print("   ", t.splitlines()[0])
rigs = dict((r.namespace, r) for r in maya_rigs.rigs())
gate(2, set(rigs) == {"Orc_D_Rig", "Orc_D_Rig1", "Creep_Rig"} and all(" - textured" in t for t in texts[:2])
     and " - red" in texts[2] and free_before == free_after_d == "red",
     "three rigs %s; the two D messages say textured, the Creep red; the palette's next free colour %s -> %s after the D adds"
     % (sorted(rigs), free_before, free_after_d))
d, d2, f = rigs.get("Orc_D_Rig"), rigs.get("Orc_D_Rig1"), rigs.get("Creep_Rig")
D, D2, F = bones(d.skeleton_root), bones(d2.skeleton_root), bones(f.skeleton_root)
foreign = sorted(set(a for p in D.values() for a in cmds.listAttr(p, userDefined=True) or []
                     if a not in ("filmboxTypeID", "lockInfluenceWeights")))
scripts = [s for s in cmds.ls(type="script") if s.startswith("Orc_D_Rig")]
gate(3, ar.rotation_mode(d) and ar.rotation_mode(d2) and d.skeleton_root == "|Orc_D_Rig:root" and len(D) == 95
     and all(n in D for n in ("weapon_r", "weapon_l", "camera_root", "camera_bone", "AB_Armor_Shoulder_L"))
     and not foreign and not scripts,
     "rotation-only, 95 joints with the helper bones and pads, foreign attributes %s, script nodes %s" % (foreign, scripts))
skin = [s for s in cmds.ls(type="skinCluster") if s.startswith("Orc_D_Rig:")]
worst = 0.0
for sc in skin:
    for idx in cmds.getAttr(sc + ".matrix", multiIndices=True) or []:
        src = cmds.listConnections("%s.matrix[%d]" % (sc, idx), s=True, d=False)
        if src:
            worst = max(worst, mdiff(om.MMatrix(cmds.getAttr("%s.bindPreMatrix[%d]" % (sc, idx))) * wm(src[0]), om.MMatrix()))
off = ar.posed_controls(rig=d)
gate(4, len(skin) == 2 and worst < 1e-4 and not off, "the two D skins (3P, 1P) at their bind (%.2e), controls at default %s" % (worst, off[:3]))

mesh = "|Orc_D_Rig:Group|Orc_D_Rig:Geometry|Orc_D_Rig:Orc_D_3P"      # «Orc_D_Body» until 2026-09-28
mesh1 = "|Orc_D_Rig:Group|Orc_D_Rig:Geometry|Orc_D_Rig:Orc_D_1P"
shape = live_shape(mesh)
fn = mfn(shape)
bs = [b for b in cmds.ls(type="blendShape") if b.startswith("Orc_D_Rig:")]
gate(5, cmds.listRelatives("|Orc_D_Rig:Group|Orc_D_Rig:Geometry", children=True) == ["Orc_D_Rig:Orc_D_3P", "Orc_D_Rig:Orc_D_1P"]
     and (fn.numVertices, fn.numPolygons) == (27546, 47374) and cmds.polyUVSet(shape, q=True, allUVSets=True) == ["map1"]
     and len(bs) == 1 and len(cmds.blendShape(bs[0], q=True, weight=True)) == 56
     and not cmds.listAttr(mesh, userDefined=True),
     "Geometry holds Orc_D_3P and Orc_D_1P; the 3P: %d vertices, %d faces, uv sets %s, blendShape %s with %d targets"
     % (fn.numVertices, fn.numPolygons, cmds.polyUVSet(shape, q=True, allUVSets=True), bs,
        len(cmds.blendShape(bs[0], q=True, weight=True)) if bs else 0))

# textured, from the installed assets, outside the palette
on_d = worn(shape)
files = [x for x in cmds.ls(type="file") if x.startswith("Orc_D_Rig:")]
paths = dict((x, cmds.getAttr(x + ".fileTextureName")) for x in files)
home = catalog.asset_path("Orc_D/")
bad = [(x, p) for x, p in paths.items() if not (p.startswith(home) and os.path.isfile(p))]
marks_ok = all(cmds.attributeQuery(colour.TEXTURE_MARKER, node=m, exists=True) and not colour.is_ours(m)
               and cmds.nodeType(m) == colour.SHADER for m in on_d)
by_name = dict((m.split(":")[-1].replace("skeldarTexture_", ""), n) for m, n in on_d.items())
gate(6, len(on_d) == 4 and marks_ok and by_name.get("Orc_D_Body") == 26292 and by_name.get("Orc_D_Eye") == 960
     and by_name.get("Orc_D_Cloth", 0) + by_name.get("Orc_D_ClothCut", 0) == 20122
     and 0 < by_name.get("Orc_D_ClothCut", 0) < 0.02 * 20122 and len(files) == 6 and not bad,
     "D wears %s; 6 file nodes, all on %s: off it %s" % (by_name, home, bad))
colour_files = dict((m, cmds.listConnections(m + ".color", type="file")[0]) for m in on_d)
marker_ok = all(cmds.getAttr(m + "." + colour.TEXTURE_MARKER) == paths[fl] for m, fl in colour_files.items())
body_mat = [m for m in on_d if m.endswith("Orc_D_Body")][0]
cloth_mat = [m for m in on_d if m.endswith("Orc_D_Cloth")][0]
cut_mat = [m for m in on_d if m.endswith("Orc_D_ClothCut")][0]
bump = cmds.listConnections(body_mat + ".normalCamera", type="bump2d") or []
cut = cmds.listConnections(cut_mat + ".transparency", type="file") or []
see_through = [m for m in on_d if cmds.listConnections(m + ".transparency", s=True, d=False)]
shared = (colour_files[cut_mat] == colour_files[cloth_mat] and
          cmds.listConnections(cut_mat + ".normalCamera") == cmds.listConnections(cloth_mat + ".normalCamera"))
spaces = dict((x, cmds.getAttr(x + ".colorSpace")) for x in files)
gate(7, marker_ok and bump and cmds.getAttr(bump[0] + ".bumpInterp") == 1 and cut and see_through == [cut_mat]
     and shared and all((spaces[x] == "Raw") == (not x.endswith("_color")) for x in files),
     "each marker names its colour image; body normal through %s (tangent space); only %s has a transparency "
     "input (cut by %s), sharing the cloth's colour and normal: %s; colour spaces %s"
     % (bump, see_through, cut, shared, sorted(set(spaces.values()))))

# the file node samples the shipped image's own pixels, the right way up
body_file = colour_files[body_mat]
width, height, pixels = image(paths[body_file])


def texel(col, row):
    index = (row * width + col) * 4
    return [pixels[index + k] / 255.0 for k in range(3)]


worst_px, flipped, varied = 0.0, 0.0, set()
for col, row in ((266, 430), (1065, 983), (1577, 1843), (635, 1351), (1843, 246), (400, 1700)):
    u, v = (col + 0.5) / width, (row + 0.5) / height
    got = cmds.colorAtPoint(body_file, output="RGB", u=u, v=v)
    worst_px = max(worst_px, max(abs(g - x) for g, x in zip(got, texel(col, row))))
    flipped = max(flipped, max(abs(g - x) for g, x in zip(got, texel(col, height - 1 - row))))
    varied.add(tuple(round(g, 2) for g in got))
gate(8, worst_px < 0.01 and flipped > 0.02 and len(varied) > 3 and (width, height) == (2048, 2048),
     "the body's file node samples the JPG's pixels to %.4f (flipped rows %.4f), %d distinct"
     % (worst_px, flipped, len(varied)))

# ------------------------------------------------------------------ against Unreal's FBX
before = set(cmds.ls(long=True))
cmds.namespace(add="ref")
cmds.namespace(set=":ref")
mel.eval("FBXResetImport; FBXImportMode -v add;")
mel.eval('FBXImport -f "%s";' % FBX)
cmds.namespace(set=":")
ref = "|ref:SK_Orc_Marauder_D|ref:SK_Orc_Marauder_D"
ref_shape = live_shape(ref)
ref_fn = mfn(ref_shape)
R = bones(cmds.ls("|ref:SK_Orc_Marauder_D|ref:root", long=True)[0])
proxy_sg = [sg for sg in set(cmds.listConnections(ref_shape, type="shadingEngine") or [])
            if re.match(r"^MI_Orc_Marauder_Cloth_Inst_\d+$", (cmds.listConnections(sg + ".surfaceShader") or ["?"])[0].split(":")[-1])]
proxy_faces = set(int(x.split("[")[1].rstrip("]")) for x in cmds.ls(cmds.sets(proxy_sg[0], q=True), flatten=True) if ".f[" in x)
proxy_verts = set(v for x in proxy_faces for v in ref_fn.getPolygonVertices(x))
kept = [v for v in range(ref_fn.numVertices) if v not in proxy_verts]
kept_faces = [x for x in range(ref_fn.numPolygons) if x not in proxy_faces]
ref_bs = cmds.ls(cmds.listHistory(ref_shape, pruneDagObjects=True), type="blendShape")[0]
for i in range(56):
    cmds.setAttr("%s.weight[%d]" % (ref_bs, i), 0.0)


def mapped_distance(a_pts, b_pts):
    return max(a_pts[k].distanceTo(b_pts[v]) for k, v in enumerate(kept))


dist = mapped_distance(fn.getPoints(om.MSpace.kWorld), ref_fn.getPoints(om.MSpace.kWorld))
worst_n = 0.0
for k in range(0, len(kept), 7):
    a = fn.getVertexNormal(k, False, om.MSpace.kWorld)
    b = ref_fn.getVertexNormal(kept[k], False, om.MSpace.kWorld)
    worst_n = max(worst_n, math.degrees(a.angle(b)))
worst_uv = 0.0
for k in range(0, len(kept_faces), 11):
    for j in range(fn.polygonVertexCount(k)):
        a = fn.getPolygonUV(k, j, "map1")
        b = ref_fn.getPolygonUV(kept_faces[k], j, "DiffuseUV")
        worst_uv = max(worst_uv, abs(a[0] - b[0]), abs(a[1] - b[1]))
gate(9, (len(proxy_faces), len(proxy_verts)) == (885, 489) and dist < 1e-4 and worst_n < 0.01 and worst_uv < 1e-6,
     "Unreal's mesh minus its %d-face proxy: every vertex on the FBX's to %.2e cm, normals to %.4f deg, uvs to %.2e"
     % (len(proxy_faces), dist, worst_n, worst_uv))
aliases = cmds.aliasAttr(ref_bs, q=True)
ref_names = dict((aliases[i + 1], aliases[i]) for i in range(0, len(aliases), 2))
worst_t, tested = 0.0, []
for i in (0, 4, 21, 36, 55):
    name = ref_names["weight[%d]" % i]
    cmds.setAttr("%s.weight[%d]" % (ref_bs, i), 1.0)
    cmds.setAttr("%s.%s" % (bs[0], name), 1.0)
    cmds.dgdirty([shape, ref_shape])
    worst_t = max(worst_t, mapped_distance(mfn(shape).getPoints(om.MSpace.kWorld), mfn(ref_shape).getPoints(om.MSpace.kWorld)))
    cmds.setAttr("%s.weight[%d]" % (ref_bs, i), 0.0)
    cmds.setAttr("%s.%s" % (bs[0], name), 0.0)
    tested.append(name)
cmds.dgdirty([shape, ref_shape])
gate(10, worst_t < 1e-4, "targets %s at weight 1 on the FBX's to %.2e cm" % (tested, worst_t))

# ------------------------------------------------------------------ the retarget
cmds.namespace(add="clip")
cmds.namespace(set=":clip")
mel.eval("FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;")
joints_before = set(cmds.ls(type="joint", long=True))
mel.eval('FBXImport -f "%s";' % CLIP)
cmds.namespace(set=":")
new = [j for j in cmds.ls(type="joint", long=True) if j not in joints_before]
src = min((j for j in new if not cmds.listRelatives(j, parent=True, type="joint")), key=lambda j: j.count("|"))
S = bones(src)
first, last = cmds.findKeyframe(list(S.values()), which="first"), cmds.findKeyframe(list(S.values()), which="last")
cmds.playbackOptions(min=first, max=last, animationStartTime=first, animationEndTime=last)
rest_t = dict((n, cmds.getAttr(p + ".translate")[0]) for n, p in D.items())
still = dict((p, wm(p)) for p in list(D2.values()) + list(F.values()))
cmds.select(cmds.ls("Orc_D_Rig:Main")[0], src)
ok, text = rr.run_retarget()
print("   ", text.splitlines()[0][:200])
frames = list(range(int(first), int(last) + 1, max(1, int((last - first) / 8))))
worst_rot, worst_len, moved = (0.0, ""), 0.0, 0.0
for t in frames:
    cmds.currentTime(t)
    for b in ("pelvis", "spine_03", "spine_05", "head", "clavicle_l", "hand_l", "hand_r", "foot_l", "ball_r"):
        if b in S:
            worst_rot = max(worst_rot, (ang(rot(wm(S[b])), rot(wm(D[b]))), b))
    for n, p in D.items():
        if n not in ("root", "pelvis", "weapon_r", "weapon_l", "camera_root", "camera_bone") and not n.startswith("ik_"):
            worst_len = max(worst_len, (om.MVector(cmds.getAttr(p + ".translate")[0]) - om.MVector(rest_t[n])).length())
    moved = max(moved, max(mdiff(m, wm(p)) for p, m in still.items()))
gate(11, ok and "ROTATIONS ONLY" in text and worst_rot[0] < 0.05 and worst_len < 1e-3,
     "the button onto Orc D: orientations on the clip's to %.5f deg (%s), bone lengths kept to %.6f cm" % (worst_rot[0], worst_rot[1], worst_len))
gate(12, moved < 1e-6, "the second Orc D and the Creep did not move: %.9f" % moved)

# the skin, under that real pose: the FBX's own skin, its joints put where the rig's stand
worst_skin, worst_j = 0.0, 0.0
for t in (frames[len(frames) // 3], frames[2 * len(frames) // 3]):
    cmds.currentTime(t)
    for name in sorted(R, key=lambda n: R[n].count("|")):
        if name in D:
            cmds.xform(R[name], worldSpace=True, matrix=list(wm(D[name])))
    worst_j = max(worst_j, max(mdiff(wm(R[n]), wm(D[n])) for n in R if n in D))
    cmds.dgdirty([shape, ref_shape])
    ours = mfn(shape).getPoints(om.MSpace.kWorld)
    worst_skin = max(worst_skin, mapped_distance(ours, mfn(ref_shape).getPoints(om.MSpace.kWorld)))
gate(13, worst_j < 1e-4 and worst_skin < 1e-3,
     "under the take, D's mesh where Unreal's own skin puts it to %.2e cm (the FBX's joints on the rig's to %.2e)"
     % (worst_skin, worst_j))

# the 1P (2026-09-28): the 3P without its head, the 3P's vertices and weights one for one --
# under the retargeted take every 1P vertex where its 3P vertex is, and the switch on Main
shape1 = live_shape(mesh1)
fn1 = mfn(shape1)
vmap = ONE_P["vertices_3p"]
worst_1p = 0.0
for t in (frames[len(frames) // 3], frames[2 * len(frames) // 3]):
    cmds.currentTime(t)
    cmds.dgdirty([shape, shape1])
    a1, a3 = mfn(shape1).getPoints(om.MSpace.kWorld), mfn(shape).getPoints(om.MSpace.kWorld)
    worst_1p = max(worst_1p, max(a1[k].distanceTo(a3[j]) for k, j in enumerate(vmap)))
bs1 = cmds.ls(cmds.listHistory(shape1, pruneDagObjects=True) or [], type="blendShape")
gate(20, (fn1.numVertices, fn1.numPolygons) == (19458, 33365) and worst_1p < 1e-5 and not bs1
     and cmds.polyUVSet(shape1, q=True, allUVSets=True) == ["map1"],
     "Orc_D_1P: %d vertices, %d faces, no blendShape; under the take every vertex on its 3P vertex to %.2e cm"
     % (fn1.numVertices, fn1.numPolygons, worst_1p))
on_1p = dict((m.split(":")[-1].replace("skeldarTexture_", ""), n) for m, n in worn(shape1).items())
gate(21, on_1p == {"Orc_D_Body": 13243, "Orc_D_Cloth": 20016, "Orc_D_ClothCut": 106},
     "the 1P wears the 3P's materials, no eye: %s" % on_1p)
main = cmds.ls("Orc_D_Rig:Main", type="transform", long=True)[0]
states = []
for value in (0, 1, 0):
    cmds.setAttr(main + ".view", value)
    states.append((value, bool(cmds.getAttr(mesh + ".visibility")), bool(cmds.getAttr(mesh1 + ".visibility"))))
keyed = cmds.listConnections(main + ".view", source=True, destination=False, type="animCurve")
gate(22, states == [(0, True, False), (1, False, True), (0, True, False)]
     and not cmds.getAttr(main + ".view", keyable=True) and cmds.getAttr(main + ".view", channelBox=True)
     and cmds.attributeQuery("view", node=main, listEnum=True) == ["3P:1P"] and not keyed,
     "Main.view (view, 3P, 1P): %s; keyable %s, in the channel box %s, keyed by the retarget %s"
     % (states, cmds.getAttr(main + ".view", keyable=True), cmds.getAttr(main + ".view", channelBox=True), bool(keyed)))

# ------------------------------------------------------------------ Recolour, then Add again
d2_shapes = colour.character_meshes(d2.skeleton_root)
cmds.undoInfo(openChunk=True)
try:
    painted = colour.paint(d2_shapes, colour.PALETTE[4].rgb, "Orc_D_Rig1")
finally:
    cmds.undoInfo(closeChunk=True)
d2_worn = worn(live_shape("|Orc_D_Rig1:Group|Orc_D_Rig1:Geometry|Orc_D_Rig1:Orc_D_3P"))
d2_worn_1p = worn(live_shape("|Orc_D_Rig1:Group|Orc_D_Rig1:Geometry|Orc_D_Rig1:Orc_D_1P"))
d1_worn = worn(shape)
gate(14, painted and list(d2_worn) == [painted] and list(d2_worn_1p) == [painted] and colour.is_ours(painted)
     and d1_worn == on_d,
     "Recolour on the second Orc D: it wears %s only (teal, ours); the first still %s" % (d2_worn, sorted(d1_worn)))
text = character.add_character(orc_d, colour.PALETTE[0].rgb)
third = live_shape("|Orc_D_Rig2:Group|Orc_D_Rig2:Geometry|Orc_D_Rig2:Orc_D_3P") if cmds.objExists("Orc_D_Rig2:Orc_D_3P") else None
third_worn = worn(third) if third else {}
gate(15, third and " - textured" in text and len(third_worn) == 4
     and all(cmds.attributeQuery(colour.TEXTURE_MARKER, node=m, exists=True) for m in third_worn),
     "the next Add: %s -> %s" % (text.splitlines()[0][:120], sorted(third_worn)))

# the cloth's cut: where the mask is black the cloth is transparent, where white it is not
mw, mh, mpx = image(paths[cut[0]])
depth = len(mpx) // (mw * mh)
cut_at = next(((c, r) for r in range(0, mh, 3) for c in range(0, mw, 3) if mpx[(r * mw + c) * depth] == 0), None)
kept_at = next(((c, r) for r in range(0, mh, 3) for c in range(0, mw, 3) if mpx[(r * mw + c) * depth] == 255), None)
seen = [cmds.colorAtPoint(cut[0], output="A", u=(c + 0.5) / mw, v=(r + 0.5) / mh) for c, r in (cut_at, kept_at)]
gate(16, cut_at and kept_at and seen[0][0] < 0.01 and seen[1][0] > 0.99,
     "the cloth's cut mask: alpha %.3f at a cut texel %s, %.3f at a kept one %s (transparency = 1 - alpha)"
     % (seen[0][0], cut_at, seen[1][0], kept_at))
# the opaque cloth never lies on the cut (2026-09-28: the viewport's Object Sorting draws a material
# with a transparency input whole in the transparent pass, and the vest's leather drew over the
# shoulder plates) -- Maya's own sampler, at every opaque cloth face's centre and near its corners
cloth_sg = cmds.listConnections(cloth_mat + ".outColor", type="shadingEngine")[0]
opaque_faces = sorted(int(x.split("[")[1].rstrip("]")) for x in cmds.ls(cmds.sets(cloth_sg, q=True), flatten=True)
                      if ".f[" in x and x.split(".")[0].endswith("Orc_D_3P"))
us, vs = [], []
for fi in opaque_faces:
    uv = [fn.getPolygonUV(fi, j, "map1") for j in range(fn.polygonVertexCount(fi))]
    cu, cv = sum(p[0] for p in uv) / len(uv), sum(p[1] for p in uv) / len(uv)
    for pu, pv in [(cu, cv)] + [(cu + 0.8 * (p[0] - cu), cv + 0.8 * (p[1] - cv)) for p in uv]:
        us.append(pu)
        vs.append(pv)
alphas = []
for k in range(0, len(us), 2000):
    got = cmds.colorAtPoint(cut[0], output="A", u=us[k:k + 2000], v=vs[k:k + 2000])
    alphas.extend(got if isinstance(got, list) else [got])
holes = sum(1 for a in alphas if a < 0.99)
gate(19, len(opaque_faces) > 19000 and len(alphas) == len(us) and holes == 0,
     "the %d opaque cloth faces: %d samples on the cut mask, %d of them in a cut" % (len(opaque_faces), len(alphas), holes))

# nothing of Unreal's FBX, or of the clip, is needed after: the reference goes
cmds.delete(cmds.ls("|ref:*", assemblies=True))

# ------------------------------------------------------------------ the export: bones only
from maya_uebridge import animexport  # noqa: E402
fbx = SCRATCH + "/orc_d_export_check.fbx"
if os.path.exists(fbx):
    os.remove(fbx)
result = animexport.export_hierarchy(fbx, root=D["root"], start=first, end=last)
print("    export:", str(result)[:200])
before = set(cmds.ls(long=True))
cmds.namespace(add="chk")
cmds.namespace(set=":chk")
mel.eval("FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;")
mel.eval('FBXImport -f "%s";' % fbx)
cmds.namespace(set=":")
back_in = [n for n in cmds.ls(long=True) if n not in before]
j_in = [n for n in back_in if cmds.nodeType(n) == "joint"]
m_in = [n for n in back_in if cmds.nodeType(n) == "mesh"]
tops = sorted(set(n.split("|")[1] for n in back_in if n.startswith("|chk:")))
gate(17, len(j_in) == 95 and not m_in and tops in (["chk:Armature"], ["chk:root"]),
     "the FBX read back: %d joints, %d meshes, top node(s) %s" % (len(j_in), len(m_in), tops))
text_ok = True
with open(catalog.character_file(orc_d), encoding="utf-8", errors="replace") as handle:
    for line in handle:
        if "C:/" in line or "c:/" in line or "createNode script" in line:
            text_ok = False
gate(18, text_ok, "the asset's text holds no absolute path and no script node")
print("RESULT: %d of %d gates failed %s" % (len(FAILS), TOTAL, FAILS))
