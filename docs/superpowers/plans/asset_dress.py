"""Dressing a shipped character .ma in textured materials, IN PLACE -- the machinery two scripts share.

Import it from a mayapy STANDALONE script after `maya.standalone.initialize()`:
make_manny_textured_assets.py (2026-09-30, Unreal's slots per face) and make_creep_textured_assets.py
(the same day, one texture set per mesh). What lives here is everything that does not depend on the
character:

- `begin()`: the plugins, and an empty working folder -- a file node given a relative path that
  RESOLVES from the process's working directory stores it absolute (CLAUDE.md trap 119);
- `open_asset(path)`: the file opened with script nodes NOT executed, the `UsdDefaultRenderSettings`
  mayaUsd makes on every open dropped and the file's own given their names back (trap 121); returns the
  file's text as it was, for the check at the end;
- `material(maps, key, colour_map, normal_map)`: the one shader (`colour.SHADER` wearing `colour.LOOK`,
  `colour.TEXTURE_MARKER`) with the colour map, and the normal map through a bump2d in tangent-space mode;
  every file node naming its image RELATIVELY (`colour.ASSET_IMAGE`, "<maps><file>"), colour sRGB,
  normal Raw, the file rules off -- Add Character points it at the installed copy;
- `ours(maps)` / `network(materials)`: a previous run's materials, to replace (re-runnable);
- `unused_shading()`: everything shading left unused, deleted;
- `check_images(maps, images)`: the file nodes are exactly these, each storing its relative path;
- `save_checked(...)`: saved as `.ma` beside the asset first, the script-node blocks cut from the text
  (trap 74), banned words refused, the header compared (bar the name, the date, the UUID, the requires),
  and every body line `git diff` reports explained -- shading, the meshes' face groups, the shading lists'
  counts, the scene singletons' fresh uuids, the external-content table, Maya's two measured resave
  noises -- or the asset is left untouched and the new file named; then moved over the asset (or into
  `out_dir`, for a proof run that must not touch it);
- `run_each(todo, script)`: one mayapy process per asset (trap 122).
"""
import os
import re
import subprocess
import sys
import tempfile

import maya.cmds as cmds
import maya.api.OpenMaya as om

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
PLUGIN = os.path.join(REPO, "SkeldarAnim")
if PLUGIN not in sys.path:
    sys.path.insert(0, PLUGIN)
from maya_scenesetup import colour  # noqa: E402

ASSETS = os.path.join(PLUGIN, "assets").replace("\\", "/")
KEEP = {"initialShadingGroup", "initialParticleSE", "lambert1", "standardSurface1", "particleCloud1",
        "openPBR_shader1"}
BANNED = ("createNode script", "vaccine", "breed_gene", "C:/", "c:/", "D:/", "d:/", "E:/", "e:/",
          "/Users/Shared", "Unreal Projects", "scratchpad", "skeldarColour")
# Maya's resave noise, measured on an unchanged open + save (2026-09-30): a new mesh default written,
# the constraints' cached last rotation in the last digits
NOISE = (re.compile(r'^\tsetAttr "\.ndt" 0;$'), re.compile(r'^\tsetAttr "\.lr" -type "double3" '))
# the scene's own singletons: Maya gives them new uuids on every open (measured on an unchanged resave)
SINGLETONS = ("lightLinker", "shapeEditorManager", "poseInterpolatorManager", "displayLayerManager",
              "renderLayerManager")
# the lists every shading engine, material, texture and utility is counted in
SHADING_LISTS = ("renderPartition", "defaultShaderList1", "defaultRenderUtilityList1", "defaultTextureList1")
METADATA = (re.compile(r'^dataStructure -fmt "raw" -as "name=externalContentTable:'),
            re.compile(r'^applyMetadata -fmt "raw" -v "channel\\nname externalContentTable\\n'),
            re.compile(r"^\t\t-scn;$"), re.compile(r"^\t\t;$"), re.compile(r"^// End of "))


def begin():
    for plugin in ("matrixNodes", "quatNodes", "fbxmaya"):
        cmds.loadPlugin(plugin, quiet=True)
    os.chdir(tempfile.mkdtemp(prefix="asset_dress_"))


def dag(node):
    sel = om.MSelectionList()
    sel.add(node)
    return sel.getDagPath(0)


def mfn(node):
    return om.MFnMesh(dag(node))


def leaf(path):
    return path.split("|")[-1].split(":")[-1]


def live_shape(transform):
    """The one shape of `transform` that is not an intermediate object."""
    s = cmds.listRelatives(transform, shapes=True, fullPath=True, noIntermediate=True) or []
    if len(s) != 1:
        raise RuntimeError("%s has %d live shapes" % (transform, len(s)))
    return s[0]


def mark(node, relative, raw):
    """colour.ASSET_IMAGE, and the colour space fixed with the file rules off, or Add's relink would
    re-decide it: Raw for the normal map's data, sRGB for colour."""
    cmds.setAttr(node + ".ignoreColorSpaceFileRules", 1)
    cmds.setAttr(node + ".colorSpace", "Raw" if raw else "sRGB", type="string")
    if not cmds.attributeQuery(colour.ASSET_IMAGE, node=node, exists=True):
        cmds.addAttr(node, longName=colour.ASSET_IMAGE, dataType="string")
    cmds.setAttr(node + "." + colour.ASSET_IMAGE, relative, type="string")


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


def material(maps, key, colour_map, normal_map):
    """The one shader with its textures: the colour, the normal through a bump2d. (material, engine)."""
    mat, engine = colour.make_textured_material(maps + colour_map, key)
    colour_file = cmds.listConnections(mat + ".color", type="file")[0]
    colour_file = cmds.rename(colour_file, key + "_color")
    cmds.rename(cmds.listConnections(colour_file + ".uvCoord")[0], key + "_color_place2d")
    mark(colour_file, maps + colour_map, raw=False)
    normal = file_node(maps + normal_map, key + "_normal", raw=True)
    cmds.setAttr(normal + ".alphaIsLuminance", 1)
    bump = cmds.shadingNode("bump2d", asUtility=True, name=key + "_bump")
    cmds.setAttr(bump + ".bumpInterp", 1)                    # tangent space normals
    cmds.setAttr(bump + ".bumpDepth", 1.0)
    cmds.connectAttr(normal + ".outAlpha", bump + ".bumpValue", force=True)
    cmds.connectAttr(bump + ".outNormal", mat + ".normalCamera", force=True)
    return mat, engine


def ours(maps):
    """Our materials from an earlier run, by their marker: its image under `maps`."""
    found = []
    for m in cmds.ls(materials=True) or []:
        if cmds.attributeQuery(colour.TEXTURE_MARKER, node=m, exists=True) and \
                (cmds.getAttr(m + "." + colour.TEXTURE_MARKER) or "").startswith(maps):
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


def worn_network(shapes):
    """Everything shading the `shapes` wear now -- their engines, the materials, textures, utilities and
    materialInfos -- by name, taken BEFORE they are re-dressed (Maya deletes an engine's materialInfo
    with the engine, and the text check must know that name was shading)."""
    engines = sorted(set(e for s in shapes for e in cmds.listConnections(s, type="shadingEngine") or []))
    nodes = set(engines)
    for e in engines:
        nodes.update(cmds.listConnections(e, type="materialInfo") or [])
        mats = cmds.listConnections(e + ".surfaceShader") or []
        nodes.update(mats)
        for m in mats:
            nodes.update(cmds.ls(cmds.listHistory(m) or [], type=("file", "place2dTexture", "bump2d")))
    return sorted(n for n in nodes if n not in KEEP)


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


def check_images(maps, images):
    """Every file node in the scene is one of `images` under `maps`, storing its relative path."""
    files = cmds.ls(type="file")
    got = sorted(cmds.getAttr(f + "." + colour.ASSET_IMAGE) for f in files)
    if got != sorted(maps + i for i in images):
        raise RuntimeError("the file nodes are %s, not %s" % (got, sorted(maps + i for i in images)))
    for f in files:
        if cmds.getAttr(f + ".fileTextureName") != cmds.getAttr(f + "." + colour.ASSET_IMAGE):
            raise RuntimeError("%s stores %s, not its relative image" % (f, cmds.getAttr(f + ".fileTextureName")))
    return [(f, cmds.getAttr(f + ".fileTextureName"), cmds.getAttr(f + ".colorSpace")) for f in files]


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


def open_asset(path):
    """Open the asset (no script node executed) and undo what mayaUsd's open did; its text before."""
    before_text = text_without_scripts(path)
    usd_own = set(re.findall(r'createNode UsdDefaultSettings -n "([^"]+)";\n\trename -uid "([^"]+)"',
                             "\n".join(before_text)))
    cmds.file(path, open=True, force=True, executeScriptNodes=False)
    # mayaUsd makes a UsdDefaultRenderSettings on every open, beside the file's own (and renames the
    # file's, which it found in the way): drop what the open made, give the file's their names back
    own_uids = dict((uid, n) for n, uid in usd_own)
    for node in cmds.ls(type="UsdDefaultSettings") or []:
        if cmds.ls(node, uuid=True)[0] not in own_uids:
            cmds.lockNode(node, lock=False)
            cmds.delete(node)
    for node in cmds.ls(type="UsdDefaultSettings") or []:
        want = own_uids[cmds.ls(node, uuid=True)[0]]
        if node != want:
            locked = cmds.lockNode(node, q=True, lock=True)[0]
            cmds.lockNode(node, lock=False)
            node = cmds.rename(node, want)
            cmds.lockNode(node, lock=locked)
    return before_text


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


def diff_lines(before_lines, after_lines):
    """[(sign, line index, hunk)] of every line removed ("-", in before) or added ("+", in after), by
    `git diff --no-index` -- difflib's SequenceMatcher took more than half an hour on a 1.2-million-line
    .ma (trap 123); git's Myers diff takes seconds."""
    folder = tempfile.mkdtemp(prefix="asset_diff_")
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
    out, old, new, in_hunks, hunk = [], 0, 0, False, -1
    for raw in run.stdout.split(b"\n"):
        line = raw.decode("utf-8", "surrogateescape")
        m = re.match(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
        if m:
            in_hunks, hunk = True, hunk + 1
            old, new = int(m.group(1)), int(m.group(3))
            # a zero-length side names the line BEFORE the change
            old = old if (m.group(2) or "1") != "0" else old + 1
            new = new if (m.group(4) or "1") != "0" else new + 1
            continue
        if not in_hunks or line[:1] not in ("-", "+"):     # git's own header, "\ No newline", ...
            continue
        if line[0] == "-":
            out.append(("-", old - 1, hunk))
            old += 1
        else:
            out.append(("+", new - 1, hunk))
            new += 1
    return out


def unexplained(before_lines, after_lines, shading_names, meshes):
    """The diff lines not explained by the shading, the meshes' face groups, or the resave noise.
    `meshes`: the transforms' leaf names whose shapes ("<leaf>Shape") were dressed."""
    names = set(shading_names)
    shapes = [m + "Shape" for m in meshes]
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
        m = re.match(r'^connectAttr "([^"]+)" "((%s))\.i";$' % "|".join(re.escape(s) for s in shapes), line)
        if m and re.search(r'connectAttr "%s" "groupParts\d+\.ig";' % re.escape(m.group(1)), after_all) and \
                re.search(r'connectAttr "groupParts\d+\.og" "%s\.i";' % re.escape(m.group(2)), after_all):
            return True
        if owner and owner[1] in shapes and (".iog" in line or ".ndt" in line):
            return True
        if line.startswith("connectAttr ") or line.startswith("relationship "):
            for q in re.findall(r'"([^"]+)"', line):
                node = q.split(".")[0].lstrip(":").split("|")[-1]
                if node in names or re.match(r"^groupId\d+$|^groupParts\d+$", node) or \
                        q.split(".")[0] in shapes and ".iog" in q or node.startswith("UsdDefaultRenderSettings"):
                    return True
            return False
        if line.startswith("lockNode") or line.startswith("select -ne") or \
                line.startswith("\trename -uid") and owner and owner[0] == "UsdDefaultSettings":
            return True
        return any(p.match(line) for p in NOISE)

    ob, oa = blocks(before_lines), blocks(after_lines)
    changes = diff_lines(before_lines, after_lines)
    # a hunk that replaces lines one for one with the same text but for numbers equal to 1e-5 is
    # float noise: a constrained joint's cached rotate re-evaluated (1e-6 deg), a double printed with
    # other digits ("5.497270456626897e-05" / "5.4972704566268963e-05")
    by_hunk = {}
    for sign, index, hunk in changes:
        by_hunk.setdefault(hunk, ([], []))[0 if sign == "-" else 1].append(index)
    noise = set()
    for hunk, (gone, came) in by_hunk.items():
        if len(gone) == len(came) and all(same_but_digits(before_lines[i], after_lines[j])
                                          for i, j in zip(gone, came)):
            noise.add(hunk)
    bad = []
    for sign, index, hunk in changes:
        if hunk in noise:
            continue
        lines, owners = (before_lines, ob) if sign == "-" else (after_lines, oa)
        if not explained(lines[index], owners.get(index)):
            bad.append("%s%d: %s" % (sign, index + 1, lines[index][:140]))
    return bad


NUMBER = re.compile(r"-?\d+\.?\d*(?:e[-+]?\d+)?")


def same_but_digits(a, b, tolerance=1e-5):
    """`a` and `b` the same text but for numbers, each pair within `tolerance`."""
    if NUMBER.sub("#", a) != NUMBER.sub("#", b):
        return False
    xs, ys = NUMBER.findall(a), NUMBER.findall(b)
    return len(xs) == len(ys) and all(abs(float(x) - float(y)) <= tolerance for x, y in zip(xs, ys))


def split_header(lines):
    """The lines before the first createNode, minus what a resave rewrites (the name, the date, the
    file's UUID, the requires statements and their continuation lines); and the rest."""
    first = next(i for i, line in enumerate(lines) if line.startswith("createNode "))
    head = [line for line in lines[:first]
            if not re.match(r"^(//Name: |//Last modified: |requires |fileInfo \"UUID\"|\t)", line)]
    return head, lines[first:]


def save_checked(path, before_text, shading_names, meshes, banned=(), out_dir=None, drop_info=()):
    """Save beside `path`, check (see the module), and move over `path` -- or into `out_dir`.
    `drop_info`: fileInfo keys removed on the way (the Creep's carried `exportedFrom`, a path of the
    animator's machine); the header check then expects exactly those lines gone."""
    name = os.path.basename(path)
    for key in drop_info:
        if cmds.fileInfo(key, query=True):
            cmds.fileInfo(remove=key)
            print("  fileInfo %r removed" % key)
    before_text = [line for line in before_text
                   if not any(line.startswith('fileInfo "%s" ' % key) for key in drop_info)]
    new = path[:-3] + ".new.ma"
    cmds.file(rename=new)
    cmds.file(save=True, type="mayaAscii", force=True)
    after_text = text_without_scripts(new)
    with open(new, "w", encoding="utf-8", errors="surrogateescape", newline="") as fh:
        fh.write("\n".join(after_text))
    bad = []
    for n, line in enumerate(after_text, 1):
        for word in tuple(BANNED) + tuple(banned):
            if word in line:
                bad.append((n, word, line.strip()[:120]))
    if bad:
        raise RuntimeError("banned content in %s (left as %s): %s" % (name, new, bad[:10]))
    head_b, body_b = split_header(before_text)
    head_a, body_a = split_header(after_text)
    if head_b != head_a:
        raise RuntimeError("the header changed (left as %s): %s -> %s" % (new, head_b, head_a))
    strange = unexplained(body_b, body_a, shading_names, meshes)
    print("  text against the file before: the header the same (%d lines), %d body lines differ that are "
          "not shading, face groups or resave noise" % (len(head_a), len(strange)))
    for s in strange[:60]:
        print("    " + s)
    if strange:
        raise RuntimeError("%s changed beyond its shading: %d lines (above; left as %s)" % (name, len(strange), new))
    target = os.path.join(out_dir, name).replace("\\", "/") if out_dir else path
    os.replace(new, target)
    print("  saved %s (%.1f MB)" % (target, os.path.getsize(target) / 1e6))
    return target


def out_dir_arg(argv):
    """`--out DIR` among the arguments: (the other arguments, DIR or None)."""
    args, out = list(argv), None
    if "--out" in args:
        i = args.index("--out")
        out = args[i + 1]
        del args[i:i + 2]
    return args, out


def run_each(todo, script, out_dir=None):
    """One mayapy process per asset: a second file opened in the same session comes back with its
    shapeEditorManager / poseInterpolatorManager renamed "...1" (trap 122)."""
    for asset in todo:
        extra = ["--out", out_dir] if out_dir else []
        code = subprocess.call([sys.executable, os.path.abspath(script), asset] + extra)
        if code:
            raise SystemExit("%s failed (%d)" % (asset, code))
