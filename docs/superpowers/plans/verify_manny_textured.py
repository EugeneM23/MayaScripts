"""Standalone gates for the textured Manny rig and skeleton going through the plugin.

    mayapy verify_manny_textured.py

mayapy STANDALONE, an empty scene (2026-09-30; spec docs/superpowers/specs/2026-09-30-manny-textured-design.md).
Add Character with «Manny [rig]» and «Manny UE5 [skeleton]», then each checked against what Unreal
itself holds (sources/manny/: the textures as imported, 4096^2):

- both arrive TEXTURED, the palette untouched; two materials, the one shader, marked; every face of
  Skin_3p and Hands_1P in one of them, as many per slot as Unreal's; the file nodes on the installed
  assets/Manny/, colour-managed as decided; the UV set the meshes' own;
- the file node samples the shipped JPG's pixels, the right way up;
- THE SLOT IS RIGHT FACE BY FACE: at every 97th face of each mesh, Maya's sampler at the face's uv
  centre gives what Unreal's D for that face's slot gives there -- and not what the other slot's does;
- the chest logo cyan across its box, where Unreal's D has none; the normal maps Unreal's BN, green
  flipped;
- the skins as far off their bind as the files had them (0.0719, the calf), the rig's controls at default,
  no script node;
- Recolour replaces the textures with a colour; a second Add is textured again.
"""
import ctypes
import json
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
TEX = REPO + "/sources/manny/textures/"
FAILS = []
TOTAL = 12
SLOTS = {"Skin_3p": {"HeadLegs": 38166, "Torso": 54012}, "Hands_1P": {"HeadLegs": 8402, "Torso": 31856}}


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


def worn_faces(shape):
    """{material: [face ids]} on `shape`."""
    fn = mfn(shape)
    engines, per_face = fn.getConnectedShaders(0)
    out = {}
    for k, e in enumerate(engines):
        sg = om.MFnDependencyNode(e).name()
        mat = (cmds.ls(cmds.listConnections(sg + ".surfaceShader", s=True, d=False) or [], materials=True) or ["?"])[0]
        out[mat] = [f for f, x in enumerate(per_face) if x == k]
    unassigned = [f for f, x in enumerate(per_face) if x < 0]
    if unassigned:
        out["<none>"] = unassigned
    return out


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


cmds.file(new=True, force=True)
from maya_scenesetup import catalog, character, colour  # noqa: E402
import maya_rigs  # noqa: E402
import maya_asretarget as ar  # noqa: E402

rig_entry, skel_entry = catalog.character_by_key("Manny_Rig"), catalog.character_by_key("Manny")
maps = dict((n, catalog.asset_path("Manny/Manny_%s.jpg" % n)) for n in
            ("HeadLegs_Color", "HeadLegs_Normal", "Torso_Color", "Torso_Normal"))
sizes = dict((n, Image(p).width) for n, p in maps.items() if os.path.isfile(p))
gate(1, rig_entry.textured and skel_entry.textured and sizes == dict((n, 2048) for n in maps),
     "«%s» and «%s» textured; the four maps shipped at %s" % (rig_entry.label, skel_entry.label, sizes))

free_before = colour.free_colour().name
texts = [character.add_character(rig_entry), character.add_character(skel_entry)]
free_after = colour.free_colour().name
for t in texts:
    print("   ", t.splitlines()[0])
rigs = maya_rigs.rigs()
roots = [r for r in cmds.ls("|root", "|*:root", type="joint", long=True)]
gate(2, [r.namespace for r in rigs] == ["Manny_Rig"] and all("textured" in t for t in texts)
     and free_before == free_after,
     "the rig in %s, the skeleton at %s; both messages say textured; the palette's next free colour %s -> %s"
     % ([r.namespace for r in rigs], roots, free_before, free_after))

characters = {"rig": "Manny_Rig:", "skeleton": ""}
home = catalog.asset_path("Manny/")
unreal = {"HeadLegs": Image(TEX + "T_Manny_01_D.png"), "Torso": Image(TEX + "T_Manny_02_D.png")}
unreal_bn = {"HeadLegs": Image(TEX + "T_Manny_01_BN.png"), "Torso": Image(TEX + "T_Manny_02_BN.png")}
logo_mask = Image(TEX + "T_UE_Logo_M.png")
LOGO = json.load(open(REPO + "/sources/manny/manny_materials.json"))["materials"][
    "/Game/Orc_Marauder/Demo/Characters/Mannequins/Materials/Instances/Manny/MI_Manny_02"]["scalars"]
LOGO_UV = (0.5 - LOGO["LogoPosOffset_X"], 1.0 - (0.5 - LOGO["LogoPosOffset_Y"]))   # Maya's uv (v up)
for kind, ns in sorted(characters.items()):
    shapes = {}
    for mesh in SLOTS:
        found = [t for t in cmds.ls(ns + mesh, type="transform", long=True)]
        shapes[mesh] = live_shape(found[0]) if len(found) == 1 else None
    counts, mats, files = {}, set(), set()
    for mesh, shape in shapes.items():
        w = worn_faces(shape) if shape else {}
        counts[mesh] = dict((m.split(":")[-1].replace("skeldarTexture_Manny_", ""), len(fs)) for m, fs in w.items())
        mats.update(w)
    for m in mats:
        files.update(cmds.listConnections(m + ".color", type="file") or [])
        for b in cmds.listConnections(m + ".normalCamera", type="bump2d") or []:
            files.update(cmds.listConnections(b + ".bumpValue", type="file") or [])
    marks = all(cmds.nodeType(m) == colour.SHADER and cmds.attributeQuery(colour.TEXTURE_MARKER, node=m, exists=True)
                and not colour.is_ours(m) for m in mats)
    bumps = [cmds.listConnections(m + ".normalCamera", type="bump2d") for m in mats]
    tangent = all(b and cmds.getAttr(b[0] + ".bumpInterp") == 1 for b in bumps)
    paths = dict((f, cmds.getAttr(f + ".fileTextureName")) for f in files)
    off = [(f, p) for f, p in paths.items() if not (p.startswith(home) and os.path.isfile(p))]
    spaces = dict((f, cmds.getAttr(f + ".colorSpace")) for f in files)
    spaces_ok = all((s == "Raw") == f.endswith("_normal") for f, s in spaces.items())
    gate(3 if kind == "rig" else 4, counts == SLOTS and len(mats) == 2 and marks and tangent and len(files) == 4
         and not off and spaces_ok,
         "%s: faces per material %s (Unreal's %s); the one shader, marked, the normal in tangent space: %s; "
         "4 file nodes on %s, off it %s; colour spaces %s"
         % (kind, counts, SLOTS, marks and tangent, home, off, sorted(set(spaces.values()))))

    uvsets = dict((m, (cmds.polyUVSet(s, q=True, allUVSets=True), cmds.polyUVSet(s, q=True, currentUVSet=True)))
                  for m, s in shapes.items())
    colour_file = dict((m.split("Manny_")[-1], cmds.listConnections(m + ".color", type="file")[0]) for m in mats)
    normal_file = dict((m.split("Manny_")[-1], cmds.listConnections(
        cmds.listConnections(m + ".normalCamera", type="bump2d")[0] + ".bumpValue", type="file")[0]) for m in mats)
    material_of = dict((m.split("Manny_")[-1], m) for m in mats)

    # the file node samples the shipped JPG's own pixels, the right way up
    img = Image(paths[colour_file["Torso"]])
    worst_px, flipped = 0.0, 0.0
    for col, row in ((266, 430), (1065, 983), (1577, 1843), (635, 1351), (1843, 246), (400, 1700)):
        u, v = (col + 0.5) / img.width, (row + 0.5) / img.height
        got = cmds.colorAtPoint(colour_file["Torso"], output="RGB", u=u, v=v)
        worst_px = max(worst_px, max(abs(g - x) for g, x in zip(got, img.texel(col, row))))
        flipped = max(flipped, max(abs(g - x) for g, x in zip(got, img.texel(col, img.height - 1 - row))))

    # the slot, face by face: our sampler at the face's uv centre against Unreal's D for each slot
    own, other, n = [], [], 0
    for mesh, shape in shapes.items():
        fn = mfn(shape)
        engines, per_face = fn.getConnectedShaders(0)
        slot_of_engine = [om.MFnDependencyNode(e).name().replace("SG", "").split("Manny_")[-1] for e in engines]
        for f in range(0, fn.numPolygons, 97):
            slot = slot_of_engine[per_face[f]]
            u, v = uv_centre(fn, f)
            got = cmds.colorAtPoint(colour_file[slot], output="RGB", u=u, v=v)
            if slot == "Torso" and math.hypot(u - LOGO_UV[0], v - LOGO_UV[1]) < 0.05:
                continue                                           # the logo is ours, not Unreal's D
            mine = unreal[slot].at(u, v)
            theirs = unreal["HeadLegs" if slot == "Torso" else "Torso"].at(u, v)
            own.append(sum(abs(g - x) for g, x in zip(got, mine)) / 3.0)
            other.append(sum(abs(g - x) for g, x in zip(got, theirs)) / 3.0)
            n += 1
    m_own, m_other = sum(own) / len(own), sum(other) / len(other)
    gate(5 if kind == "rig" else 6, worst_px < 0.01 and flipped > 0.02 and m_own < 0.03 and m_other > 4 * m_own
         and all(sets == (["DiffuseUV"], ["DiffuseUV"]) for sets in uvsets.values()),
         "%s: the torso's file node samples its JPG to %.4f (flipped rows %.4f); at %d faces our colour against "
         "Unreal's D for the face's own slot: mean %.4f, median %.4f -- against the other slot's: mean %.4f; "
         "uv sets %s" % (kind, worst_px, flipped, n, m_own, median(own), m_other, uvsets))

    # the logo: its box sampled 31 x 31 -- the centre alone is the empty middle of the "U" -- against the
    # pattern Unreal's own maths draws from T_UE_Logo_M there: saturate(brightness * logo * sphereMask)
    # at ScaleUVsByCenter(uv + offset, size), in Unreal's uv (v down). Cyan where that is ~1, not where ~0.
    agree = decided = cyan_ours = cyan_theirs = 0
    size, ox, oy, bright = LOGO["LogoSize"], LOGO["LogoPosOffset_X"], LOGO["LogoPosOffset_Y"], LOGO["LogoLayer0_Brightness"]
    for i in range(31):
        for j in range(31):
            u, v = LOGO_UV[0] + (i - 15) * size / 31.0, LOGO_UV[1] + (j - 15) * size / 31.0
            su, sv = (u + ox - 0.5) / size + 0.5, ((1.0 - v) + oy - 0.5) / size + 0.5
            sphere = max(0.0, min(1.0, (1 - math.hypot(su - 0.5, sv - 0.5) / 0.65) / (1 - 0.75)))
            inside = 0 <= su <= 1 and 0 <= sv <= 1
            want = min(1.0, bright * logo_mask.at(su, 1.0 - sv)[1] * sphere) if inside else 0.0
            got = cmds.colorAtPoint(colour_file["Torso"], output="RGB", u=u, v=v)
            ue = unreal["Torso"].at(u, v)
            cyan = got[0] < 0.25 and got[1] > 0.75 and got[2] > 0.75
            cyan_ours += cyan
            cyan_theirs += ue[0] < 0.25 and ue[1] > 0.75 and ue[2] > 0.75
            if want > 0.95 or want < 0.05:
                decided += 1
                agree += cyan == (want > 0.95)
    angles = []
    for slot in ("HeadLegs", "Torso"):
        for k in range(400):
            u, v = ((k * 0.61803) % 1.0), ((k * 0.7548 + 0.13) % 1.0)
            got = cmds.colorAtPoint(normal_file[slot], output="RGB", u=u, v=v)
            a = [g * 2 - 1 for g in got]
            b = [x * 2 - 1 for x in unreal_bn[slot].at(u, v)]
            b[1] = -b[1]
            la, lb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(x * x for x in b))
            angles.append(math.degrees(math.acos(max(-1, min(1, sum(x * y for x, y in zip(a, b)) / (la * lb))))))
    gate(7 if kind == "rig" else 8, cyan_ours > 20 and cyan_theirs == 0 and agree >= 0.95 * decided
         and median(angles) < 3.0,
         "%s: in the logo's box %d samples cyan on our torso colour (Unreal's D: %d), agreeing with the pattern "
         "Unreal's maths draws from T_UE_Logo_M at %d of %d decided samples; the normal maps against Unreal's BN "
         "with green flipped: median %.2f deg, p90 %.2f over %d samples (the p90 is the 2048 shrink at the bevels)"
         % (kind, cyan_ours, cyan_theirs, agree, decided, median(angles),
            sorted(angles)[int(len(angles) * 0.9)], len(angles)))

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
# Manny's own skins stand 0.0719 off their bind at the left calf -- measured on both files as they were
# before this build (git HEAD, 2026-09-30: 7.18e-02 / 7.19e-02, the calf asymmetry of the skeleton); the
# textures must leave that as it was, not make it better or worse
gate(9, len(cmds.ls(type="skinCluster")) == 4 and abs(worst - 0.0719) < 5e-4 and not off and not scripts,
     "4 skins, off their bind %.2e as the files were before (7.19e-02), the rig's controls at default %s, "
     "script nodes %s" % (worst, off[:3], scripts))

# Recolour: a colour over the textures, whole shapes; a second Add textured again
rig_meshes = [live_shape(cmds.ls("Manny_Rig:" + m, type="transform", long=True)[0]) for m in SLOTS]
painted = colour.paint(rig_meshes, colour.PALETTE[2].rgb, "Manny_Rig")
after = dict((s, worn_faces(s)) for s in rig_meshes)
one = all(len(w) == 1 and list(w)[0] == painted for w in after.values())
gate(10, painted and one and colour.is_ours(painted),
     "Recolour: both rig meshes wear %s alone: %s" % (painted, dict((s.split("|")[-1], list(w)) for s, w in after.items())))
text3 = character.add_character(rig_entry)
print("   ", text3.splitlines()[0])
ns3 = [r.namespace for r in maya_rigs.rigs() if r.namespace not in ("Manny_Rig",)]
shape3 = live_shape(cmds.ls(ns3[0] + ":Skin_3p", type="transform", long=True)[0]) if ns3 else None
w3 = worn_faces(shape3) if shape3 else {}
gate(11, "textured" in text3 and len(w3) == 2 and all(cmds.attributeQuery(colour.TEXTURE_MARKER, node=m, exists=True)
                                                      for m in w3),
     "a second Add after the Recolour: %s, its Skin_3p wears %s" % (ns3, dict((m, len(f)) for m, f in w3.items())))
# the images the second Manny's file nodes name are the first's, both on the installed copy
imgs = sorted(set(cmds.getAttr(f + ".fileTextureName") for f in cmds.ls(type="file")))
gate(12, imgs == sorted(maps.values()), "every file node in the scene names one of the four installed images: %s" % imgs)

print("%d of %d gates failed%s" % (len(FAILS), TOTAL, (": %s" % FAILS) if FAILS else ""))
