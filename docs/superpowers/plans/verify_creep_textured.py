"""Standalone gates for the textured Creep rig and skeleton going through the plugin.

    mayapy verify_creep_textured.py

mayapy STANDALONE, an empty scene (2026-09-30; spec docs/superpowers/specs/2026-09-30-creep-textured-design.md).
Add Character with «Creep [rig]» and «Creep [skeleton]», then each checked against the SOURCE images
(sources/creep/textures/: the animator's and the Cascadeur FBX's own):

- both arrive TEXTURED, the palette untouched; each of the five meshes wears its set's material whole
  (Body, Face, and Limbs for the back and both arms), the one shader, marked; six file nodes on the
  installed assets/Creep/, colour-managed as decided; the UV set `map1`;
- the file node samples the shipped JPG's pixels, the right way up;
- THE SET IS RIGHT MESH BY MESH: at every 29th face of each mesh Maya's sampler at the face's uv centre
  gives, on the mesh's mean, the source colour of that mesh's set -- at most half as far as either of the
  other two sets';
- the normal maps the sources', the head's green flipped (DirectX) and the others' not (OpenGL);
- skins at their bind, the rig's controls at default, no script node;
- Recolour replaces the textures with a colour; a second Add is textured again.
"""
import ctypes
import math
import os
import sys

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

REPO = "C:/!!!Work/MayaScripts"
sys.path.insert(0, REPO + "/SkeldarAnim")
for p in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass
SRC = REPO + "/sources/creep/textures/"
FAILS = []
TOTAL = 12
SETS = {"Body": ("Creep_Body",), "Face": ("Creep_Face",), "Limbs": ("Creep_Back", "Creep_Arm_L", "Creep_Arm_R")}
SOURCE = {"Body": ("creep_body_diff.png", "creep_body_norm.png", False),
          "Face": ("creep_face_diff.jpg", "creep_face_norm.jpg", True),      # the head's green is DirectX
          "Limbs": ("creep_limbs_diff.png", "creep_limbs_norm.png", False)}


def gate(n, ok, msg):
    print("%s gate %02d: %s" % ("PASS" if ok else "FAIL", n, msg))
    sys.stdout.flush()
    if not ok:
        FAILS.append(n)


def mfn(node):
    sel = om.MSelectionList()
    sel.add(node)
    return om.MFnMesh(sel.getDagPath(0))


def live_shape(transform):
    return [s for s in cmds.listRelatives(transform, shapes=True, fullPath=True) or []
            if not cmds.getAttr(s + ".intermediateObject")][0]


class Image(object):
    """An image through MImage: row 0 is the BOTTOM row, which is Maya's v 0."""

    def __init__(self, path):
        img = om.MImage()
        img.readFromFile(path)
        self.width, self.height = img.getSize()
        self.depth = img.depth()
        self.data = ctypes.string_at(img.pixels(), self.width * self.height * self.depth)

    def texel(self, col, row):
        i = (row * self.width + col) * self.depth
        return [self.data[i + k] / 255.0 for k in range(3)]

    def at(self, u, v):
        col = min(self.width - 1, max(0, int(u * self.width)))
        row = min(self.height - 1, max(0, int(v * self.height)))
        return self.texel(col, row)


def worn(shape):
    """[material names] the shape's faces wear, and whether any face wears none."""
    engines, per_face = mfn(shape).getConnectedShaders(0)
    mats = []
    for e in engines:
        sg = om.MFnDependencyNode(e).name()
        mats.append((cmds.ls(cmds.listConnections(sg + ".surfaceShader", s=True, d=False) or [], materials=True) or ["?"])[0])
    return mats, -1 in list(per_face)


def uv_centre(fn, f):
    us, vs = [], []
    for k in range(fn.polygonVertexCount(f)):
        u, v = fn.getPolygonUV(f, k)
        us.append(u)
        vs.append(v)
    return sum(us) / len(us), sum(vs) / len(vs)


def median(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2] if xs else float("nan")


def angle(a, b):
    la, lb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(x * x for x in b))
    return math.degrees(math.acos(max(-1.0, min(1.0, sum(x * y for x, y in zip(a, b)) / (la * lb)))))


cmds.file(new=True, force=True)
from maya_scenesetup import catalog, character, colour  # noqa: E402
import maya_rigs  # noqa: E402
import maya_asretarget as ar  # noqa: E402

rig_entry, skel_entry = catalog.character_by_key("Creep_Rig"), catalog.character_by_key("Creep")
maps = dict(("%s_%s" % (k, kind), catalog.asset_path("Creep/Creep_%s_%s.jpg" % (k, kind)))
            for k in SETS for kind in ("Color", "Normal"))
sizes = dict((n, Image(p).width) for n, p in maps.items() if os.path.isfile(p))
gate(1, rig_entry.textured and skel_entry.textured and sizes == dict((n, 2048) for n in maps),
     "«%s» and «%s» textured; the six maps shipped at %s" % (rig_entry.label, skel_entry.label, sizes))

free_before = colour.free_colour().name
texts = [character.add_character(rig_entry), character.add_character(skel_entry)]
free_after = colour.free_colour().name
for t in texts:
    print("   ", t.splitlines()[0])
rigs = maya_rigs.rigs()
gate(2, [r.namespace for r in rigs] == ["Creep_Rig"] and all("textured" in t for t in texts)
     and free_before == free_after,
     "the rig in %s; both messages say textured; the palette's next free colour %s -> %s"
     % ([r.namespace for r in rigs], free_before, free_after))

home = catalog.asset_path("Creep/")
source = dict((k, Image(SRC + d)) for k, (d, _n, _f) in SOURCE.items())
source_n = dict((k, Image(SRC + n)) for k, (_d, n, _f) in SOURCE.items())
for kind, ns in (("rig", "Creep_Rig:"), ("skeleton", "")):
    shapes, wear, loose = {}, {}, []
    for key, meshes in SETS.items():
        for mesh in meshes:
            found = cmds.ls(ns + mesh, type="transform", long=True)
            found = [f for f in found if (":" in f) == bool(ns)]
            shapes[mesh] = live_shape(found[0]) if len(found) == 1 else None
            mats, unassigned = worn(shapes[mesh]) if shapes[mesh] else ([], True)
            wear[mesh] = [m.split(":")[-1] for m in mats]
            if unassigned:
                loose.append(mesh)
    sets_ok = all(wear[m] == ["skeldarTexture_Creep_" + k] for k, ms in SETS.items() for m in ms)
    mats = sorted(set(m for s in shapes.values() if s for m in worn(s)[0]))
    files = set()
    for m in mats:
        files.update(cmds.listConnections(m + ".color", type="file") or [])
        for b in cmds.listConnections(m + ".normalCamera", type="bump2d") or []:
            files.update(cmds.listConnections(b + ".bumpValue", type="file") or [])
    marks = all(cmds.nodeType(m) == colour.SHADER and cmds.attributeQuery(colour.TEXTURE_MARKER, node=m, exists=True)
                and not colour.is_ours(m) for m in mats)
    tangent = all((cmds.listConnections(m + ".normalCamera", type="bump2d") or [None])[0] and
                  cmds.getAttr(cmds.listConnections(m + ".normalCamera", type="bump2d")[0] + ".bumpInterp") == 1
                  for m in mats)
    paths = dict((f, cmds.getAttr(f + ".fileTextureName")) for f in files)
    off = [(f, p) for f, p in paths.items() if not (p.startswith(home) and os.path.isfile(p))]
    spaces = dict((f, cmds.getAttr(f + ".colorSpace")) for f in files)
    spaces_ok = all((s == "Raw") == f.endswith("_normal") for f, s in spaces.items())
    uvsets = dict((m, (cmds.polyUVSet(s, q=True, allUVSets=True), cmds.polyUVSet(s, q=True, currentUVSet=True)))
                  for m, s in shapes.items())
    uv_ok = all(v == (["map1"], ["map1"]) for v in uvsets.values())
    gate(3 if kind == "rig" else 4, sets_ok and not loose and len(mats) == 3 and marks and tangent and len(files) == 6
         and not off and spaces_ok and uv_ok,
         "%s: each mesh wears %s (unassigned faces on %s); the one shader, marked, the normal in tangent space: "
         "%s; 6 file nodes on %s, off it %s; colour spaces %s; uv sets map1: %s"
         % (kind, wear, loose, marks and tangent, home, off, sorted(set(spaces.values())), uv_ok))

    colour_file = dict((m.split("Creep_")[-1], cmds.listConnections(m + ".color", type="file")[0]) for m in mats)
    normal_file = dict((m.split("Creep_")[-1], cmds.listConnections(
        cmds.listConnections(m + ".normalCamera", type="bump2d")[0] + ".bumpValue", type="file")[0]) for m in mats)

    # the file node samples the shipped JPG's own pixels, the right way up
    img = Image(paths[colour_file["Body"]])
    worst_px, flipped = 0.0, 0.0
    for col, row in ((266, 430), (1065, 983), (1577, 1843), (635, 1351), (1843, 246), (400, 1700)):
        u, v = (col + 0.5) / img.width, (row + 0.5) / img.height
        got = cmds.colorAtPoint(colour_file["Body"], output="RGB", u=u, v=v)
        worst_px = max(worst_px, max(abs(g - x) for g, x in zip(got, img.texel(col, row))))
        flipped = max(flipped, max(abs(g - x) for g, x in zip(got, img.texel(col, img.height - 1 - row))))

    # the set, mesh by mesh: our sampler at the face's uv centre against the source colour of EACH set.
    # The three are all the Creep's dark browns and greys, so a single face can land where two sets
    # look alike; what tells the set is the mean over a mesh's faces, its own set's against each other's.
    table, ratios = {}, []
    for key, meshes in SETS.items():
        for mesh in meshes:
            fn = mfn(shapes[mesh])
            sums, n = dict((o, 0.0) for o in SETS), 0
            for f in range(0, fn.numPolygons, 29):
                u, v = uv_centre(fn, f)
                got = cmds.colorAtPoint(colour_file[key], output="RGB", u=u, v=v)
                for o in SETS:
                    sums[o] += sum(abs(g - x) for g, x in zip(got, source[o].at(u, v))) / 3.0
                n += 1
            means = dict((o, sums[o] / n) for o in SETS)
            table[mesh] = "own %.4f, others %s" % (means[key], ", ".join(
                "%s %.4f" % (o, means[o]) for o in SETS if o != key))
            ratios.append(max(means[key] / means[o] for o in SETS if o != key))
            table[mesh] += " (%d faces)" % n
    worst_ratio = max(ratios)
    gate(5 if kind == "rig" else 6, worst_px < 0.01 and flipped > 0.02 and worst_ratio < 0.5,
         "%s: the body's file node samples its JPG to %.4f (flipped rows %.4f); per mesh our colour against each "
         "set's source, mean over its faces: %s -- own / nearest other at worst %.2f"
         % (kind, worst_px, flipped, table, worst_ratio))

    # the normals: ours against the source's, read with and without the green flipped
    report, normals_ok = {}, True
    for key, (_d, _n, directx) in SOURCE.items():
        as_is, turned = [], []
        for k in range(300):
            u, v = ((k * 0.61803) % 1.0), ((k * 0.7548 + 0.13) % 1.0)
            ours_n = [g * 2 - 1 for g in cmds.colorAtPoint(normal_file[key], output="RGB", u=u, v=v)]
            src = [x * 2 - 1 for x in source_n[key].at(u, v)]
            if src[2] > 0.999 and abs(ours_n[2]) > 0.999:
                continue                                         # flat: says nothing about green
            as_is.append(angle(ours_n, src))
            turned.append(angle(ours_n, [src[0], -src[1], src[2]]))
        right, wrong = (median(turned), median(as_is)) if directx else (median(as_is), median(turned))
        report[key] = "%s: %.2f deg as decided, %.2f the other way (%d samples)" % (
            "flipped" if directx else "as is", right, wrong, len(as_is))
        normals_ok = normals_ok and right < 3.0 and right < wrong
    gate(7 if kind == "rig" else 8, normals_ok, "%s: the normal maps against the sources: %s" % (kind, report))

# the skins at their bind, the rig's controls at default, no script node
worst = 0.0
for sc in cmds.ls(type="skinCluster"):
    for idx in cmds.getAttr(sc + ".matrix", multiIndices=True) or []:
        src = cmds.listConnections("%s.matrix[%d]" % (sc, idx), s=True, d=False)
        if src:
            m = om.MMatrix(cmds.getAttr("%s.bindPreMatrix[%d]" % (sc, idx))) * om.MMatrix(
                cmds.getAttr(src[0] + ".worldMatrix[0]"))
            worst = max(worst, max(abs(a - b) for a, b in zip(list(m), list(om.MMatrix()))))
off = ar.posed_controls(rig=rigs[0])
scripts = [s for s in cmds.ls(type="script") if s not in ("sceneConfigurationScriptNode", "uiConfigurationScriptNode")]
gate(9, len(cmds.ls(type="skinCluster")) == 10 and worst < 1e-3 and not off and not scripts,
     "%d skins at their bind (%.2e), the rig's controls at default %s, script nodes %s"
     % (len(cmds.ls(type="skinCluster")), worst, off[:3], scripts))

# Recolour: a colour over the textures, whole shapes; a second Add textured again
rig_meshes = [live_shape(cmds.ls("Creep_Rig:" + m, type="transform", long=True)[0]) for ms in SETS.values() for m in ms]
painted = colour.paint(rig_meshes, colour.PALETTE[2].rgb, "Creep_Rig")
after = dict((s.split("|")[-1], worn(s)[0]) for s in rig_meshes)
gate(10, painted and colour.is_ours(painted) and all(w == [painted] for w in after.values()),
     "Recolour: the rig's five meshes wear %s alone: %s" % (painted, after))
text3 = character.add_character(rig_entry)
print("   ", text3.splitlines()[0])
ns3 = [r.namespace for r in maya_rigs.rigs() if r.namespace != "Creep_Rig"]
w3 = worn(live_shape(cmds.ls(ns3[0] + ":Creep_Body", type="transform", long=True)[0]))[0] if ns3 else []
gate(11, "textured" in text3 and len(w3) == 1 and cmds.attributeQuery(colour.TEXTURE_MARKER, node=w3[0], exists=True),
     "a second Add after the Recolour: %s, its Creep_Body wears %s" % (ns3, w3))
imgs = sorted(set(cmds.getAttr(f + ".fileTextureName") for f in cmds.ls(type="file")))
gate(12, imgs == sorted(maps.values()), "every file node in the scene names one of the six installed images: %s" % imgs)

print("%d of %d gates failed%s" % (len(FAILS), TOTAL, (": %s" % FAILS) if FAILS else ""))
