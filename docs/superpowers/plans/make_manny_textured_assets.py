"""Dress SkeldarAnim/assets/Manny_Rig.ma and Manny_Skeleton.ma in Unreal's own textures, in place.

    mayapy make_manny_textured_assets.py [Manny_Rig.ma] [Manny_Skeleton.ma]

mayapy STANDALONE.  2026-09-30 (spec: docs/superpowers/specs/2026-09-30-manny-textured-design.md),
the Orc D's road.  For each asset: open it (script nodes NOT executed), import
`sources/manny/SKM_Manny_Simple.fbx` into a namespace to learn which face wears which of Unreal's two
slots, and dress both meshes:

- `Skin_3p` IS that mesh index for index (every uv equal, measured 0.000000): each face is found by
  its three vertex ids -- all 92178 must be found, the slot counts must be Unreal's 38166 / 54012;
- `Hands_1P` is a cut of it (arms, shoulders, hands): its vertices are matched to Unreal's by
  position and uv, a face by its three matched vertices, and a face the cut made new (a vertex
  matching nothing) takes the slot of the Unreal face closest to its centre;
- two materials, `skeldarTexture_Manny_HeadLegs` and `skeldarTexture_Manny_Torso`, the one shader
  (`colour.SHADER` wearing `colour.LOOK`, `colour.TEXTURE_MARKER`) with the colour map and the
  normal map through a bump2d in tangent-space mode (make_manny_textures.py's maps), every file node
  naming its image RELATIVELY (`colour.ASSET_IMAGE`, "Manny/<file>") -- Add Character points it at
  the installed copy.

Then everything shading left unused is deleted (the meshes' old material, the dead `MI_Manny_*`
networks naming `D:/dev/...` and `/Users/Shared/...`, the MaterialX `Maya_Blinn1/3`, ...), the
`UsdDefaultRenderSettings` mayaUsd makes on every open is dropped (the file keeps its own), the
scene's time unit is put back if the FBX importer moved it (trap 80), the file saved as `.ma`, the
script-node blocks cut from the text (trap 74), banned words refused -- and the text compared with
the file before: outside the shading blocks, the two meshes' face-group lines and Maya's known resave
noise, not one line may differ.  Re-runnable: a second run replaces its own materials.
"""

import os
import re
import sys

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
PLUGIN = os.path.join(REPO, "SkeldarAnim")
sys.path.insert(0, PLUGIN)
from maya_scenesetup import colour  # noqa: E402

ASSETS = os.path.join(PLUGIN, "assets").replace("\\", "/")
FBX = os.path.join(REPO, "sources", "manny", "SKM_Manny_Simple.fbx").replace("\\", "/")
NS = "ueManny"
MAPS = "Manny/"
MESHES = ("Skin_3p", "Hands_1P")
SLOT_OF = {"MI_Manny_01": "HeadLegs", "MI_Manny_02": "Torso"}
UNREAL_SLOTS = {"HeadLegs": 38166, "Torso": 54012}
IMAGES = ("Manny_HeadLegs_Color.jpg", "Manny_HeadLegs_Normal.jpg", "Manny_Torso_Color.jpg",
          "Manny_Torso_Normal.jpg")
KEEP = {"initialShadingGroup", "initialParticleSE", "lambert1", "standardSurface1", "particleCloud1",
        "openPBR_shader1"}
BANNED = ("createNode script", "vaccine", "breed_gene", "C:/", "c:/", "D:/", "d:/", "/Users/Shared",
          "Unreal Projects", "scratchpad", NS + ":", "MI_Manny", "T_Manny_0", "skeldarColour",
          "EnvSamplerTex", "Maya_Blinn")
# Maya's resave noise, measured on an unchanged open + save (2026-09-30): the header, the requires
# lines' order, a new mesh default written, the constraints' cached last rotation in the last digits
NOISE = (re.compile(r'^\tsetAttr "\.ndt" 0;$'), re.compile(r'^\tsetAttr "\.lr" -type "double3" '))

for plugin in ("matrixNodes", "quatNodes", "fbxmaya"):
    cmds.loadPlugin(plugin, quiet=True)

# A file node given a relative path that RESOLVES from the process's working directory stores it
# absolute (measured 2026-09-30: run from SkeldarAnim/assets/, "Manny/..." came back
# "C:/!!!Work/.../assets/Manny/..."). Work from an empty folder, so the paths stay the asset's own.
import tempfile  # noqa: E402
os.chdir(tempfile.mkdtemp(prefix="manny_textured_"))


def dag(node):
    sel = om.MSelectionList()
    sel.add(node)
    return sel.getDagPath(0)


def mfn(node):
    return om.MFnMesh(dag(node))


def leaf(path):
    return path.split("|")[-1].split(":")[-1]


def file_node(relative, name, raw):
    """A file node wired to a place2dTexture as Hypershade wires one, naming its image RELATIVELY."""
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
    """colour.ASSET_IMAGE, and the colour space fixed with the file rules off, or Add's relink would
    re-decide it: Raw for the normal map's data, sRGB for colour."""
    cmds.setAttr(node + ".ignoreColorSpaceFileRules", 1)
    cmds.setAttr(node + ".colorSpace", "Raw" if raw else "sRGB", type="string")
    if not cmds.attributeQuery(colour.ASSET_IMAGE, node=node, exists=True):
        cmds.addAttr(node, longName=colour.ASSET_IMAGE, dataType="string")
    cmds.setAttr(node + "." + colour.ASSET_IMAGE, relative, type="string")


def material(key, colour_map, normal_map):
    """The one shader with Unreal's textures: the colour, the normal through a bump2d."""
    mat, engine = colour.make_textured_material(MAPS + colour_map, key)
    colour_file = cmds.listConnections(mat + ".color", type="file")[0]
    colour_file = cmds.rename(colour_file, key + "_color")
    cmds.rename(cmds.listConnections(colour_file + ".uvCoord")[0], key + "_color_place2d")
    mark(colour_file, MAPS + colour_map, raw=False)
    normal = file_node(MAPS + normal_map, key + "_normal", raw=True)
    cmds.setAttr(normal + ".alphaIsLuminance", 1)
    bump = cmds.shadingNode("bump2d", asUtility=True, name=key + "_bump")
    cmds.setAttr(bump + ".bumpInterp", 1)                    # tangent space normals
    cmds.setAttr(bump + ".bumpDepth", 1.0)
    cmds.connectAttr(normal + ".outAlpha", bump + ".bumpValue", force=True)
    cmds.connectAttr(bump + ".outNormal", mat + ".normalCamera", force=True)
    return mat, engine


def ours():
    """Our Manny materials from an earlier run of this script, by their marker."""
    found = []
    for m in cmds.ls(materials=True) or []:
        if cmds.attributeQuery(colour.TEXTURE_MARKER, node=m, exists=True) and \
                (cmds.getAttr(m + "." + colour.TEXTURE_MARKER) or "").startswith(MAPS):
            found.append(m)
    return found


def network(materials):
    """A material with its engine, materialInfo, file, place2d and bump nodes."""
    nodes = set(materials)
    for m in materials:
        nodes.update(cmds.listConnections(m, type="shadingEngine") or [])
        nodes.update(cmds.ls(cmds.listHistory(m) or [], type=("file", "place2dTexture", "bump2d")))
    for sg in [n for n in nodes if cmds.nodeType(n) == "shadingEngine"]:
        nodes.update(cmds.listConnections(sg, type="materialInfo") or [])
    return sorted(nodes)


def unused_shading():
    """The shading nodes nothing uses: an engine holding nothing, a material in no engine, a texture
    or utility feeding nothing but Maya's default lists -- repeated until nothing more goes."""
    gone = []
    for _ in range(8):
        doomed = [sg for sg in cmds.ls(type="shadingEngine") if sg not in KEEP and not cmds.sets(sg, query=True)]
        doomed += cmds.ls(cmds.listConnections(doomed, type="materialInfo") or [])
        doomed += [m for m in cmds.ls(materials=True) if m not in KEEP and not cmds.listConnections(m, type="shadingEngine")]
        doomed += [t for t in cmds.ls(textures=True) + cmds.ls(type="place2dTexture") + cmds.ls(type="bump2d")
                   if not [d for d in cmds.listConnections(t, source=False, destination=True) or []
                           if cmds.nodeType(d) not in ("defaultTextureList", "defaultRenderUtilityList",
                                                       "nodeGraphEditorInfo", "materialInfo")]]
        doomed = sorted(set(n for n in doomed if cmds.objExists(n)))
        if not doomed:
            break
        for n in doomed:
            if cmds.objExists(n):
                gone.append((n, cmds.nodeType(n)))
                cmds.delete(n)
    return gone


def blocks(lines):
    """{line index: (node type, node name)} for every line of a createNode block, and
    ("select", name) for the lines under a `select -ne :name`."""
    owner, current = {}, None
    for i, line in enumerate(lines):
        m = re.match(r'^createNode (\w+) (?:-s )?-n "([^"]+)"', line)
        s = re.match(r"^select -ne :(\w+);", line)
        if m:
            current = (m.group(1), m.group(2))
        elif s:
            current = ("select", s.group(1))
        elif line[:1] not in ("\t", " "):
            current = None
        if current:
            owner[i] = current
    return owner


# the scene's own singletons: Maya gives them new uuids on every open (measured on an unchanged resave)
SINGLETONS = ("lightLinker", "shapeEditorManager", "poseInterpolatorManager", "displayLayerManager",
              "renderLayerManager")
# the lists every shading engine, material, texture and utility is counted in
SHADING_LISTS = ("renderPartition", "defaultShaderList1", "defaultRenderUtilityList1", "defaultTextureList1")
METADATA = (re.compile(r'^dataStructure -fmt "raw" -as "name=externalContentTable:'),
            re.compile(r'^applyMetadata -fmt "raw" -v "channel\\nname externalContentTable\\n'),
            re.compile(r"^\t\t-scn;$"), re.compile(r"^\t\t;$"), re.compile(r"^// End of "))


def unexplained(before_lines, after_lines, shading_names):
    """The diff lines not explained by the shading, the meshes' face groups, or the resave noise."""
    names = set(shading_names)
    after_all = "\n".join(after_lines)

    def explained(line, owner):
        if owner and (owner[1] in names or owner[0] in ("groupId", "groupParts", "UsdDefaultSettings")):
            return True
        if owner and owner[0] in SINGLETONS and (line.startswith("\trename -uid ") or
                                                 re.match(r'^\tsetAttr -s \d+ "\.s?lnk";$', line)):
            return True
        if owner and owner[0] == "select" and owner[1] in SHADING_LISTS and \
                re.match(r'^\tsetAttr -s \d+ "\.\w+";$', line):
            return True
        if any(p.match(line) for p in METADATA):
            return True
        # a mesh's input now through the groupParts its face groups need: A -> groupParts .. -> shape
        m = re.match(r'^connectAttr "([^"]+)" "((%s)Shape)\.i";$' % "|".join(MESHES), line)
        if m and re.search(r'connectAttr "%s" "groupParts\d+\.ig";' % re.escape(m.group(1)), after_all) and \
                re.search(r'connectAttr "groupParts\d+\.og" "%s\.i";' % re.escape(m.group(2)), after_all):
            return True
        if owner and owner[1] in [m + "Shape" for m in MESHES] and (".iog" in line or ".ndt" in line):
            return True
        if line.startswith("connectAttr ") or line.startswith("relationship "):
            quoted = re.findall(r'"([^"]+)"', line)
            for q in quoted:
                node = q.split(".")[0].lstrip(":").split("|")[-1]
                if node in names or re.match(r"^groupId\d+$|^groupParts\d+$", node) or \
                        q.split(".")[0] in [m + "Shape" for m in MESHES] and ".iog" in q or \
                        node.startswith("UsdDefaultRenderSettings"):
                    return True
            return False
        if line.startswith("lockNode") or line.startswith("select -ne") or line.startswith("\trename -uid") and owner and owner[0] == "UsdDefaultSettings":
            return True
        return any(p.match(line) for p in NOISE)

    ob, oa = blocks(before_lines), blocks(after_lines)
    bad = []
    for sign, index in diff_lines(before_lines, after_lines):
        lines, owners = (before_lines, ob) if sign == "-" else (after_lines, oa)
        if not explained(lines[index], owners.get(index)):
            bad.append("%s%d: %s" % (sign, index + 1, lines[index][:140]))
    return bad


def diff_lines(before_lines, after_lines):
    """[(sign, line index)] of every line removed ("-", in before) or added ("+", in after), by
    `git diff --no-index` -- difflib's SequenceMatcher took more than half an hour on the skeleton's
    1.2 million lines; git's Myers diff takes seconds."""
    import subprocess
    import tempfile
    folder = tempfile.mkdtemp(prefix="manny_diff_")
    paths = []
    for name, lines in (("before.ma", before_lines), ("after.ma", after_lines)):
        path = os.path.join(folder, name)
        with open(path, "w", encoding="utf-8", errors="surrogateescape", newline="\n") as fh:
            fh.write("\n".join(lines) + "\n")
        paths.append(path)
    run = subprocess.run(["git", "diff", "--no-index", "--no-color", "--text", "-U0", "--minimal"] + paths,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if run.returncode not in (0, 1):
        raise RuntimeError("git diff failed: %s" % run.stderr.decode("utf-8", "replace"))
    out, old, new, in_hunks = [], 0, 0, False
    for raw in run.stdout.split(b"\n"):
        line = raw.decode("utf-8", "surrogateescape")
        m = re.match(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
        if m:
            in_hunks = True
            old, new = int(m.group(1)), int(m.group(3))
            # a zero-length side names the line BEFORE the change
            old = old if (m.group(2) or "1") != "0" else old + 1
            new = new if (m.group(4) or "1") != "0" else new + 1
            continue
        if not in_hunks or line[:1] not in ("-", "+"):     # git's own header, "\ No newline", ...
            continue

        if line[0] == "-":
            out.append(("-", old - 1))
            old += 1
        else:
            out.append(("+", new - 1))
            new += 1
    return out


def text_without_scripts(path):
    with open(path, encoding="utf-8", errors="surrogateescape") as fh:
        lines = fh.read().split("\n")
    kept, skipping = [], False
    for line in lines:
        if line.startswith("createNode script "):
            skipping = True
            continue
        if skipping and line[:1] not in ("\t", " "):
            skipping = False
        if not skipping:
            kept.append(line)
    return kept


def unreal_slots():
    """Unreal's mesh in NS: its shape, points, uvs, the slot of each face, {sorted vertex ids: face}."""
    time_unit = cmds.currentUnit(query=True, time=True)
    cmds.namespace(add=NS)
    cmds.namespace(set=NS)
    mel.eval("FBXResetImport")
    mel.eval("FBXImportMode -v add")
    mel.eval('FBXImport -f "%s"' % FBX)
    cmds.namespace(set=":")
    if cmds.currentUnit(query=True, time=True) != time_unit:        # trap 80: the importer moves it
        print("  (the FBX importer moved the time unit to %s; back to %s)"
              % (cmds.currentUnit(query=True, time=True), time_unit))
        cmds.currentUnit(time=time_unit, updateAnimation=False)
    shapes = [m for m in cmds.ls(NS + ":*", type="mesh", long=True) if not cmds.getAttr(m + ".intermediateObject")]
    assert len(shapes) == 1, shapes
    fn = mfn(shapes[0])
    engines, per_face = fn.getConnectedShaders(0)
    slot_of_engine = []
    for e in engines:
        mat = leaf((cmds.listConnections(om.MFnDependencyNode(e).name() + ".surfaceShader") or ["?"])[0])
        if mat not in SLOT_OF:
            raise RuntimeError("Unreal's mesh wears %s, measured on %s" % (mat, sorted(SLOT_OF)))
        slot_of_engine.append(SLOT_OF[mat])
    slots = [slot_of_engine[k] for k in per_face]
    counts = dict((s, slots.count(s)) for s in UNREAL_SLOTS)
    if counts != UNREAL_SLOTS:
        raise RuntimeError("Unreal's slots %s, measured %s" % (counts, UNREAL_SLOTS))
    _counts, verts = fn.getVertices()
    face_of = dict((tuple(sorted(verts[3 * f:3 * f + 3])), f) for f in range(fn.numPolygons))
    return shapes[0], fn, slots, face_of


def dress_skin_3p(shape, ufn, slots, face_of):
    fn = mfn(shape)
    if (fn.numVertices, fn.numPolygons) != (ufn.numVertices, ufn.numPolygons):
        raise RuntimeError("Skin_3p is %d/%d, Unreal's %d/%d" % (fn.numVertices, fn.numPolygons,
                                                                 ufn.numVertices, ufn.numPolygons))
    u, v = fn.getUVs()
    uu, uv = ufn.getUVs()
    duv = max(max(abs(a - b) for a, b in zip(u, uu)), max(abs(a - b) for a, b in zip(v, uv)))
    if duv > 1e-6:
        raise RuntimeError("Skin_3p's uvs are not Unreal's index for index: %.2e" % duv)
    _c, verts = fn.getVertices()
    out = {}
    for f in range(fn.numPolygons):
        uf = face_of.get(tuple(sorted(verts[3 * f:3 * f + 3])))
        if uf is None:
            raise RuntimeError("Skin_3p face %d is no face of Unreal's" % f)
        out.setdefault(slots[uf], []).append(f)
    counts = dict((k, len(v)) for k, v in out.items())
    print("  Skin_3p: uvs Unreal's to %.1e, every face found by its vertex ids: %s" % (duv, counts))
    if counts != UNREAL_SLOTS:
        raise RuntimeError("Skin_3p's slots %s, Unreal's %s" % (counts, UNREAL_SLOTS))
    return out


def dress_hands_1p(shape, ushape, ufn, slots, face_of):
    fn = mfn(shape)
    pts, upts = fn.getPoints(om.MSpace.kWorld), ufn.getPoints(om.MSpace.kWorld)
    u, v = fn.getUVs()
    uu, uv = ufn.getUVs()
    q = 0.05

    def key(p, a, b):
        return (int(round(p.x / q)), int(round(p.y / q)), int(round(p.z / q)),
                int(round(a * 2000)), int(round(b * 2000)))

    table = {}
    for i in range(ufn.numVertices):
        table.setdefault(key(upts[i], uu[i], uv[i]), []).append(i)
    vmap, worst = [], 0.0
    for i in range(fn.numVertices):
        k = key(pts[i], u[i], v[i])
        cands = table.get(k, [])
        if not cands:                                        # a quantum boundary: the neighbours
            cands = [c for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1)
                     for du in (-1, 0, 1) for dv in (-1, 0, 1)
                     for c in table.get((k[0] + dx, k[1] + dy, k[2] + dz, k[3] + du, k[4] + dv), [])]
        cands = [c for c in cands if pts[i].distanceTo(upts[c]) < 0.01 and
                 abs(u[i] - uu[c]) < 1e-3 and abs(v[i] - uv[c]) < 1e-3]
        if len(set(cands)) == 1:
            vmap.append(cands[0])
            worst = max(worst, pts[i].distanceTo(upts[cands[0]]))
        else:
            vmap.append(None)
    _c, verts = fn.getVertices()
    intersector = om.MMeshIntersector()
    udag = dag(ushape)
    intersector.create(udag.node(), udag.inclusiveMatrix())
    out, by_ids, by_near = {}, 0, 0
    for f in range(fn.numPolygons):
        ids = [vmap[x] for x in verts[3 * f:3 * f + 3]]
        uf = face_of.get(tuple(sorted(ids))) if None not in ids else None
        if uf is None:
            c = om.MPoint()
            for x in verts[3 * f:3 * f + 3]:
                c += om.MVector(pts[x])
            c = om.MPoint(c.x / 3.0, c.y / 3.0, c.z / 3.0)
            uf = intersector.getClosestPoint(c, 1000.0).face
            by_near += 1
        else:
            by_ids += 1
        out.setdefault(slots[uf], []).append(f)
    lost = sum(1 for x in vmap if x is None)
    print("  Hands_1P: %d of %d vertices Unreal's (to %.4f cm, position and uv), %d faces by their vertex "
          "ids, %d by the closest Unreal face: %s" % (fn.numVertices - lost, fn.numVertices, worst, by_ids,
                                                    by_near, dict((k, len(v)) for k, v in out.items())))
    if by_near > 200 or lost > 50:
        raise RuntimeError("Hands_1P is not the cut this was measured on (%d vertices unmatched)" % lost)
    return out


def dress(name):
    path = ASSETS + "/" + name
    before_text = text_without_scripts(path)
    usd_own = set(re.findall(r'createNode UsdDefaultSettings -n "([^"]+)";\n\trename -uid "([^"]+)"',
                             "\n".join(before_text)))
    cmds.file(path, open=True, force=True, executeScriptNodes=False)
    print("== %s" % name)
    time_unit = cmds.currentUnit(query=True, time=True)

    # mayaUsd makes a UsdDefaultRenderSettings on every open, beside the file's own (and renames the
    # file's, which it found in the way): drop what the open made, give the file's their names back
    own_uids = dict((uid, n) for n, uid in usd_own)
    for node in cmds.ls(type="UsdDefaultSettings") or []:
        uid = cmds.ls(node, uuid=True)[0]
        if uid not in own_uids:
            cmds.lockNode(node, lock=False)
            cmds.delete(node)
    for node in cmds.ls(type="UsdDefaultSettings") or []:
        want = own_uids[cmds.ls(node, uuid=True)[0]]
        if node != want:
            locked = cmds.lockNode(node, q=True, lock=True)[0]
            cmds.lockNode(node, lock=False)
            node = cmds.rename(node, want)
            cmds.lockNode(node, lock=locked)

    shapes = {}
    for mesh in MESHES:
        found = cmds.ls(mesh, type="transform", long=True)
        assert len(found) == 1, (mesh, found)
        s = cmds.listRelatives(found[0], shapes=True, fullPath=True, noIntermediate=True)
        assert len(s) == 1, s
        shapes[mesh] = s[0]
    worn_before = dict((m, sorted(set(cmds.listConnections(s, type="shadingEngine") or [])))
                       for m, s in shapes.items())
    print("  worn before:", worn_before)
    old_ours, doomed = ours(), []
    if old_ours:
        doomed = network(old_ours)
        print("  our own materials from an earlier run go: %s" % old_ours)
        cmds.delete(doomed)

    ushape, ufn, slots, face_of = unreal_slots()
    faces = {"Skin_3p": dress_skin_3p(shapes["Skin_3p"], ufn, slots, face_of),
             "Hands_1P": dress_hands_1p(shapes["Hands_1P"], ushape, ufn, slots, face_of)}
    cmds.namespace(removeNamespace=NS, deleteNamespaceContent=True)
    cmds.select(clear=True)
    made = {"HeadLegs": material("Manny_HeadLegs", "Manny_HeadLegs_Color.jpg", "Manny_HeadLegs_Normal.jpg"),
            "Torso": material("Manny_Torso", "Manny_Torso_Color.jpg", "Manny_Torso_Normal.jpg")}
    for mesh in MESHES:
        transform = cmds.listRelatives(shapes[mesh], parent=True, fullPath=True)[0]
        for slot in ("HeadLegs", "Torso"):
            ids = faces[mesh].get(slot, [])
            if ids:
                cmds.sets(["%s.f[%d]" % (transform, i) for i in ids], edit=True, forceElement=made[slot][1])
    if cmds.currentUnit(query=True, time=True) != time_unit:
        cmds.currentUnit(time=time_unit, updateAnimation=False)

    gone = unused_shading()
    print("  unused shading deleted (%d): %s" % (len(gone), sorted(set(t for _n, t in gone))))
    print("    %s" % [n for n, _t in gone])

    # what must be there
    for mesh in MESHES:
        s = shapes[mesh]
        n_faces = mfn(s).numPolygons
        engines, per_face = mfn(s).getConnectedShaders(0)
        names = [om.MFnDependencyNode(e).name() for e in engines]
        worn = dict((names[k], list(per_face).count(k)) for k in range(len(names)))
        assert sorted(worn) == sorted(e for _m, e in made.values()), (mesh, worn)
        assert -1 not in list(per_face) and sum(worn.values()) == n_faces, (mesh, worn)
        want = dict((made[k][1], len(v)) for k, v in faces[mesh].items())
        assert worn == want, (mesh, worn, want)
        print("  %s wears %s" % (mesh, worn))
    materials = sorted(m for m in cmds.ls(materials=True) if m not in KEEP)
    files = cmds.ls(type="file")
    images = sorted(cmds.getAttr(f + "." + colour.ASSET_IMAGE) for f in files)
    assert images == sorted(MAPS + i for i in IMAGES), images
    for f in files:
        if cmds.getAttr(f + ".fileTextureName") != cmds.getAttr(f + "." + colour.ASSET_IMAGE):
            raise RuntimeError("%s stores %s, not its relative image" % (f, cmds.getAttr(f + ".fileTextureName")))
    print("  materials:", materials)
    print("  files:", [(f, cmds.getAttr(f + ".fileTextureName"), cmds.getAttr(f + ".colorSpace")) for f in files])
    assert not cmds.namespace(exists=NS)

    shading_names = set(n for n, _t in gone) | set(network([m for m, _e in made.values()]))
    shading_names |= set(n for sgs in worn_before.values() for n in sgs) | set(doomed)
    new = path[:-3] + ".new.ma"
    cmds.file(rename=new)
    cmds.file(save=True, type="mayaAscii", force=True)
    after_text = text_without_scripts(new)
    with open(new, "w", encoding="utf-8", errors="surrogateescape", newline="") as fh:
        fh.write("\n".join(after_text))
    bad = []
    for n, line in enumerate(after_text, 1):
        for word in BANNED:
            if word in line:
                bad.append((n, word, line.strip()[:120]))
    if bad:
        raise RuntimeError("banned content in %s (left as %s): %s" % (name, new, bad[:10]))
    head_b, body_b = split_header(before_text)
    head_a, body_a = split_header(after_text)
    if head_b != head_a:
        raise RuntimeError("the header changed (left as %s): %s -> %s" % (new, head_b, head_a))
    strange = unexplained(body_b, body_a, shading_names)
    print("  text against the file before: the header the same (%d lines), %d body lines differ that are "
          "not shading, face groups or resave noise" % (len(head_a), len(strange)))
    for s in strange[:60]:
        print("    " + s)
    if strange:
        raise RuntimeError("%s changed beyond its shading: %d lines (above; left as %s)" % (name, len(strange), new))
    os.replace(new, path)
    print("  saved %s (%.1f MB)" % (path, os.path.getsize(path) / 1e6))


def split_header(lines):
    """The lines before the first createNode, minus what a resave rewrites (the name, the date, the
    file's UUID, the requires statements and their continuation lines); and the rest."""
    first = next(i for i, line in enumerate(lines) if line.startswith("createNode "))
    head = [line for line in lines[:first]
            if not re.match(r"^(//Name: |//Last modified: |requires |fileInfo \"UUID\"|\t)", line)]
    return head, lines[first:]


# One asset per mayapy session: a second file opened in the same session comes back with its
# shapeEditorManager / poseInterpolatorManager renamed "...1" (the scene's own were already there) --
# measured 2026-09-30 on the skeleton after the rig. Several asked for, each gets a process of its own.
todo = sys.argv[1:] or ["Manny_Rig.ma", "Manny_Skeleton.ma"]
if len(todo) == 1:
    dress(todo[0])
else:
    import subprocess
    for asset in todo:
        code = subprocess.call([sys.executable, os.path.abspath(__file__), asset])
        if code:
            raise SystemExit("%s failed (%d)" % (asset, code))
