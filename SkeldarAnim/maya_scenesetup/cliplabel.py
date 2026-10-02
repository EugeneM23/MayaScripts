"""The animation's name written on the floor under the character it went onto.

2026-10-02, the animator: «при групповом импорте в сцену в том числе и при
переноси мышкой драгом давай внизу под каждым скелетом или ригом персонажем
будем писать имя анимации а то сейчас не понятно». A 2 x 2 square of four
Mannys after a batch import was four identical figures; which clip played on
which one was nowhere to be read.

**One rule for every road**: whatever puts a clip on a character - the
Import Animation button in every mode, a drag onto a rig, a skeleton or the
floor, a batch square - ends in `rigimport.retarget_imported` (a rig) or
`skeletonimport.onto_skeleton` / `onto_existing` (a skeleton), and those
three call `label_rig` / `label_skeleton`. One label per character: a later
import onto the same one REPLACES its text. **A label names the take the
character plays, so whatever clears the take clears the label**: the rig
reset in front of every import (`rigimport.ready_rig`) and the Retarget
button's (`maya_rig_retarget.run_retarget`, which labels the rig afterwards
with its source's name when it has one - `clip_name_from`).

**What it is, measured in a GUI Maya 2027 before choosing** (spec:
docs/superpowers/specs/2026-10-02-clip-labels-design.md):

- an `annotationShape` under a transform of its own, `displayArrow` off. Its
  text is drawn at a FIXED SCREEN SIZE, centred on its point, always facing
  the camera and over every mesh (an annotation 40 cm behind a 40 cm-wide
  body read whole); a playblast draws it. Text curves were measured beside
  it: 115 nodes for one name and illegible at 16 m.
- **unselectable, and still in our colour**: the TRANSFORM in reference
  display (a marquee over the whole view does not take it), the SHAPE's own
  override back to normal with RGB on - the shape's override is what the
  draw reads, the parent's reference what the pick reads. Reference alone,
  on either node, draws the text BLACK whatever its colour (invisible on a
  dark backdrop); template draws a dim grey.
- it FOLLOWS the character on the floor, in WORLD space: four DG nodes
  (`_follow`) take the root bone's world X and Z, put Y on the floor and
  FRONT ahead on world +Z, and bring that point into the label's parent
  space through the label's own `parentInverseMatrix`. A walking clip's name
  walks with it, exactly, and moving or turning the group the label hangs
  in moves nothing (a `pointConstraint`'s offset - the first build - is in
  the constrained node's PARENT space, so it turned and rose with the
  group). The four nodes are linked to the label by message (`PART_LINK`).

**Never in an export, never in the skeleton**: the label is not under the
root (the exporter takes a selected node's children along, trap 76); for a
rig it hangs under the rig's top group (in the rig's namespace, so it dies
with it), for a bare skeleton at world level, linked to the root by message
(`deletion` takes it as one of the skeleton's parts). Where it lives is ONE
function, `home_for`.

Identity by attribute, never by name: `MARKER` (the clip's name) on the
transform, `ROOT_LINK` fed by the root's message.
"""

import os
import re
import traceback

import maya.cmds as cmds

MARKER = "skeldarClipLabel"          # string, on the label transform: the clip's name
ROOT_LINK = "skeldarClipLabelRoot"   # message, fed by the character root's .message
PART_LINK = "skeldarClipLabelOf"     # message on each follow node, fed by the label's .message
LEAF = "clipLabel"                   # the transform's name (never searched for)
# cm ahead of the root on world +Z (every rig faces +Z): just past Main's ring (radius 40.52),
# so the name stands on clear floor and not on the feet or the ring.
FRONT = 50.0
FLOOR = 0.0                          # world Y of the label
MAX_CHARS = 48
# maya_hubstyle.TOKENS["accent"] (a test pins it). Measured behind the labels of a 2 x 2 square
# of textured Mannys (WCAG ratio, the worst tenth of the ink): muted 2.10, accent 2.14 (2.27 on
# a dark backdrop), text 1.35 - no luminance beats ~2.3 against a grey background AND white
# bodies at once, so the hue decides: orange stands apart from every neutral behind it.
COLOUR = "#e07a36"
# The translate is DRIVEN by the follow network; rotate and scale are locked.
LOCKED = ("rotateX", "rotateY", "rotateZ", "scaleX", "scaleY", "scaleZ")
TRANSLATE = ("translateX", "translateY", "translateZ")
# Top nodes whose name says nothing about the clip (an FBX importer's or a
# DCC's wrapper, a bare root): a source under one of them gives no name.
GENERIC = ("armature", "root", "skeleton", "group", "scene", "rootnode", "hips",
           "reference", "skel", "rig", "world", "null", "bip001", "bip01")
# A scene OPENED from one of these is a clip; a .ma / .mb is a working file.
CLIP_FILES = (".fbx", ".bvh", ".dae", ".abc", ".htr", ".trc", ".c3d", ".asf",
              ".amc", ".glb", ".gltf", ".usd", ".usda", ".usdc", ".usdz")

# What a clip's name may still carry when it came from a file (a folder of
# FBX, a BVH): the extension goes, the name stays.
EXTENSIONS = (".fbx", ".bvh", ".anim", ".atom", ".ma", ".mb", ".dae", ".abc",
              ".usd", ".usda", ".usdc", ".usdz", ".glb", ".gltf", ".htr",
              ".trc", ".c3d", ".asf", ".amc")


# ------------------------------------------------------------------- pure

def label_text(name, limit=MAX_CHARS):
    """What the label reads for the clip `name`. Pure.

    A path keeps its file's name, a known extension goes, runs of whitespace
    become one space, and a name longer than `limit` keeps its head and its
    tail around an ellipsis - the tail is where `_1P` / `_3P` / `_02` live."""
    text = str(name or "").replace("\\", "/").split("/")[-1].strip()
    stem, ext = os.path.splitext(text)
    if stem and ext.lower() in EXTENSIONS:
        text = stem
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit > 3:
        tail = (limit - 3) // 3
        head = limit - 3 - tail
        text = text[:head] + "..." + text[len(text) - tail:]
    return text


def node_name(namespace, owner=""):
    """The new label transform's name: the rig's namespace's `clipLabel`, or
    for a skeleton at world level its root's name and `_clipLabel` - so the
    outliner pairs `Manny_Skeleton_root` with `Manny_Skeleton_root_clipLabel`.
    Maya uniquifies it; nothing searches for it. Pure."""
    if namespace:
        return "{0}:{1}".format(namespace, LEAF)
    owner = (owner or "").split("|")[-1].split(":")[-1]
    return "{0}_{1}".format(owner, LEAF) if owner else LEAF


def home_for(kind, group=None, character=None):
    """Where a character's label hangs: in the character's own outliner group
    when it has one (2026-10-02, `chargroup` - rig or skeleton alike, so the
    character's layer hides it too), else under the rig's top group (it dies
    with the rig's namespace), else at world level (None) beside a bare
    skeleton added before the groups. The one place that decides it. Pure."""
    if character:
        return character
    if kind == "rig" and group:
        return group
    return None


def plan(existing, text):
    """What one import does to a character's labels. Pure.

    `existing` is [(path, current text)] - the labels linked to the
    character's root, in the scene's order. Answers (action, keep, extra):
    "create" with nothing standing; "keep" when the one standing already
    reads `text`; "update" when it reads something else. `extra` are labels
    beyond the first (a character has one) - they go."""
    existing = list(existing or [])
    if not existing:
        return "create", None, []
    keep, current = existing[0]
    extra = [path for path, _text in existing[1:]]
    return ("keep" if current == text else "update"), keep, extra


def clip_name_from(source_root, top_is_joint=True, scene_file=""):
    """The clip's name a hand-imported source skeleton gives, or "" when it
    gives none. Pure.

    The Retarget button takes any skeleton the animator imported, and its
    name is rarely written anywhere: a namespace is the bridge's own spelling
    (its «as a new skeleton» import names it for the clip, `namespace_for`),
    so the OUTERMOST namespace of the source's top node wins; else that top
    node when it is not a joint and not a generic wrapper (`GENERIC`: an
    importer's `Armature`, a bare `root`); else the scene's own file when the
    scene was OPENED from a clip file (`CLIP_FILES` - never a .ma / .mb, the
    animator's working file). Nothing else: a wrong name is worse than none,
    so "" means the label goes."""
    parts = [p for p in str(source_root or "").split("|") if p]
    if parts:
        top = parts[0]
        if ":" in top:
            return top.split(":")[0]
        if not top_is_joint and top.lower() not in GENERIC:
            return top
    if scene_file:
        leaf = str(scene_file).replace("\\", "/").split("/")[-1]
        stem, ext = os.path.splitext(leaf)
        if stem and ext.lower() in CLIP_FILES:
            return stem
    return ""


def follows_plan(translate_from, root_from, parts):
    """Is a label's follow network whole? Pure.

    `translate_from` the node driving its translateX, `root_from` the
    network's decomposeMatrix that reads THIS root, `parts` the nodes linked
    to the label by `PART_LINK`. Whole means the translate comes from one of
    OUR parts and one part reads the root - a label whose network was
    deleted, or which still carries the first build's pointConstraint, is
    rebuilt."""
    parts = set(parts or ())
    return (bool(translate_from) and translate_from in parts
            and bool(root_from) and root_from in parts)


def colour_of(hex_colour):
    """(r, g, b) in 0..1 of a "#rrggbb" colour. Pure."""
    value = hex_colour.lstrip("#")
    return tuple(int(value[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


# ------------------------------------------------------------------ scene

def _long(node):
    found = cmds.ls(node, long=True) if node else None
    return found[0] if found else None


def _marked(node):
    return bool(node) and cmds.attributeQuery(MARKER, node=node, exists=True)


def labels_of(root):
    """The label transforms linked to `root` (long paths), by their marker."""
    out = []
    if not root or not cmds.objExists(root):
        return out
    for node in cmds.listConnections(root + ".message", source=False,
                                     destination=True) or []:
        path = _long(node)
        if path and _marked(path) and path not in out:
            out.append(path)
    return out


def all_labels():
    """Every clip label in the scene: by type then marker (a `*.attr` pattern
    does not cross a namespace, trap 70)."""
    out = []
    for shape in cmds.ls(type="annotationShape", long=True) or []:
        parent = (cmds.listRelatives(shape, parent=True, fullPath=True) or [None])[0]
        if parent and _marked(parent) and parent not in out:
            out.append(parent)
    return out


def shape_of(label):
    shapes = cmds.listRelatives(label, shapes=True, type="annotationShape",
                                fullPath=True) or []
    return shapes[0] if shapes else None


def text_of(label):
    """What a label reads on screen."""
    shape = shape_of(label)
    return (cmds.getAttr(shape + ".text") or "") if shape else ""


def clip_of(label):
    """The clip's name a label records."""
    if not _marked(label):
        return ""
    return cmds.getAttr(label + "." + MARKER) or ""


def _write(label, name, text):
    plug = label + "." + MARKER
    cmds.setAttr(plug, lock=False)
    cmds.setAttr(plug, name, type="string")
    cmds.setAttr(plug, lock=True)
    shape = shape_of(label)
    if shape:
        cmds.setAttr(shape + ".text", text, type="string")


def _dress(label, shape):
    """Unselectable and in our colour: the transform in reference display (the
    pick reads it), the shape's own override normal with RGB (the draw reads
    that). Measured, both halves - see the module's notes."""
    cmds.setAttr(shape + ".displayArrow", 0)
    cmds.setAttr(label + ".overrideEnabled", 1)
    cmds.setAttr(label + ".overrideDisplayType", 2)
    cmds.setAttr(shape + ".overrideEnabled", 1)
    cmds.setAttr(shape + ".overrideDisplayType", 0)
    cmds.setAttr(shape + ".overrideRGBColors", 1)
    cmds.setAttr(shape + ".overrideColorRGB", *colour_of(COLOUR))


def _make(root, namespace, home, name, text):
    """A new label for `root`, on the floor under it, following it."""
    label = cmds.createNode("transform", name=node_name(namespace, root),
                            skipSelect=True)
    if home and cmds.objExists(home):
        label = cmds.parent(label, home)[0]
    label = _long(label)
    shape = cmds.createNode("annotationShape", name=label.split("|")[-1] + "Shape",
                            parent=label, skipSelect=True)
    shape = _long(shape)
    _dress(label, shape)
    cmds.addAttr(label, longName=MARKER, dataType="string")
    cmds.addAttr(label, longName=ROOT_LINK, attributeType="message")
    cmds.connectAttr(root + ".message", label + "." + ROOT_LINK)
    _write(label, name, text)
    _follow(label, root)
    for attr in LOCKED:
        cmds.setAttr(label + "." + attr, lock=True)
    return label


def parts_of(label):
    """The follow nodes linked to `label` (by `PART_LINK`)."""
    out = []
    if not label or not cmds.objExists(label):
        return out
    for node in cmds.listConnections(label + ".message", source=False,
                                     destination=True) or []:
        if (cmds.attributeQuery(PART_LINK, node=node, exists=True)
                and node not in out):
            out.append(node)
    return out


def _follow(label, root):
    """The label on the floor FRONT ahead of `root`, in world space, on every
    frame: root.worldMatrix -> decompose (its world X, Z) -> compose (Y on
    the floor) -> mult (FRONT on world +Z - two pure translations add in
    either order - then the label's parentInverseMatrix) -> decompose ->
    label.translate. The parent's inverse is what keeps the point a WORLD
    point however the group above the label stands."""
    base = label.split("|")[-1]
    made = []

    def part(kind, suffix):
        node = cmds.createNode(kind, name="{0}_{1}".format(base, suffix),
                               skipSelect=True)
        cmds.addAttr(node, longName=PART_LINK, attributeType="message")
        cmds.connectAttr(label + ".message", node + "." + PART_LINK)
        made.append(node)
        return node

    at_root = part("decomposeMatrix", "rootAt")
    floor = part("composeMatrix", "floorAt")
    total = part("multMatrix", "labelAt")
    local = part("decomposeMatrix", "labelLocal")
    cmds.connectAttr(root + ".worldMatrix[0]", at_root + ".inputMatrix")
    cmds.connectAttr(at_root + ".outputTranslateX", floor + ".inputTranslateX")
    cmds.connectAttr(at_root + ".outputTranslateZ", floor + ".inputTranslateZ")
    cmds.setAttr(floor + ".inputTranslateY", FLOOR)
    cmds.connectAttr(floor + ".outputMatrix", total + ".matrixIn[0]")
    ahead = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0,
             0.0, 0.0, 1.0, 0.0, 0.0, 0.0, FRONT, 1.0]
    cmds.setAttr(total + ".matrixIn[1]", ahead, type="matrix")
    cmds.connectAttr(label + ".parentInverseMatrix[0]", total + ".matrixIn[2]")
    cmds.connectAttr(total + ".matrixSum", local + ".inputMatrix")
    for attr in TRANSLATE:
        cmds.setAttr(label + "." + attr, lock=False)
    cmds.connectAttr(local + ".outputTranslate", label + ".translate", force=True)
    return made


def _unfollow(label):
    """Whatever made `label` follow, gone: our follow nodes, a pointConstraint
    the first build hung under it, any input left on its translate."""
    nodes = parts_of(label)
    nodes += cmds.listRelatives(label, children=True, type="constraint",
                                fullPath=True) or []
    nodes = [n for n in nodes if cmds.objExists(n)]
    if nodes:
        cmds.delete(nodes)
    for attr in ("translate",) + TRANSLATE:
        for plug in cmds.listConnections(label + "." + attr, source=True,
                                         destination=False, plugs=True) or []:
            try:
                cmds.disconnectAttr(plug, label + "." + attr)
            except RuntimeError:
                pass
    for attr in TRANSLATE:
        cmds.setAttr(label + "." + attr, lock=False)


def follows(label, root):
    """Does `label` still follow `root` through a whole follow network?"""
    parts = parts_of(label)
    driver = None
    for attr in ("translate", "translateX"):        # the compound, or a child wired alone
        found = cmds.listConnections(label + "." + attr, source=True,
                                     destination=False) or []
        if found:
            driver = found[0]
            break
    root_long = _long(root)
    root_from = None
    for node in parts:
        if cmds.nodeType(node) != "decomposeMatrix":
            continue
        for src in cmds.listConnections(node + ".inputMatrix", source=True,
                                        destination=False) or []:
            if _long(src) == root_long:
                root_from = node
    return follows_plan(driver, root_from, parts)


def ensure(root, name, namespace="", home=None):
    """The one label of the character whose root is `root`, reading the clip
    `name`: made when there is none, its text replaced when there is.
    Returns its long path."""
    root = _long(root)
    if root is None:
        return None
    text = label_text(name)
    found = [(path, clip_of(path)) for path in labels_of(root)]
    action, keep, extra = plan(found, name)
    for path in extra:
        if cmds.objExists(path):
            cmds.delete(path)
    if action == "create":
        return _make(root, namespace, home, name, text)
    if action == "update":
        _write(keep, name, text)
    if not follows(keep, root):
        # Its network was deleted, or it is the first build's constraint:
        # make it follow again rather than leave it frozen where it stands.
        _unfollow(keep)
        _follow(keep, root)
    return keep


def clear(root):
    """Every label of the character whose root is `root`, gone with its
    follow nodes. How many went."""
    root = _long(root)
    if root is None:
        return 0
    labels = labels_of(root)
    nodes = []
    for label in labels:
        nodes += parts_of(label) + [label]
    nodes = [n for n in nodes if cmds.objExists(n)]
    if nodes:
        cmds.delete(nodes)
    return len(labels)


def clear_rig(rig):
    """The rig's label gone - its take was cleared, so the name would lie.
    Never raises (see `label_rig`)."""
    try:
        return clear(rig.skeleton_root or rig.main)
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
        return 0


def clip_name_of(source_root):
    """`clip_name_from` over the scene: the source's top node and the scene's
    own file."""
    path = _long(source_root) or ""
    parts = [p for p in path.split("|") if p]
    top_is_joint = True
    if parts:
        top_is_joint = cmds.objectType("|" + parts[0]) == "joint"
    scene = cmds.file(query=True, sceneName=True) or ""
    return clip_name_from(path, top_is_joint, scene)


def relabel_rig(rig, source_root):
    """After the Retarget button's bake: the rig labelled with its source's
    clip name, or its label gone when the source gives none. Never raises."""
    try:
        name = clip_name_of(source_root) if source_root else ""
        if name:
            return label_rig(rig, name)
        clear_rig(rig)
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
    return None


def label_rig(rig, name):
    """The clip's name under the rig `rig` (a `maya_rigs.Rig`). Following its
    game skeleton's root (root motion), else its Main. Never raises: a label
    that cannot be made must not fail an import - it says why in the Script
    Editor and answers None."""
    try:
        root = rig.skeleton_root or rig.main
        return ensure(root, name, rig.namespace,
                      home_for("rig", rig.group, _character_group(rig)))
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
        return None


def label_skeleton(root, name):
    """The clip's name under the bare skeleton whose root is `root`. Never
    raises (see `label_rig`)."""
    try:
        return ensure(root, name, "", home_for("skeleton", None,
                                               _character_group(root)))
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
        return None


def _character_group(owner):
    """The character's outliner group (`chargroup.group_of`), or None - a
    legacy character, or a Maya without the module."""
    try:
        from maya_scenesetup import chargroup   # lazy: a leaf stays a leaf
        return chargroup.group_of(owner)
    except Exception:                                        # noqa: BLE001
        return None
