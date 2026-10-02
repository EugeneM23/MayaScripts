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
import onto the same one REPLACES its text.

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
- it FOLLOWS the character on the floor: a `pointConstraint` to the root
  bone, Y skipped and the label's own Y on 0, so a walking clip's name walks
  with it, exactly, and costs one constraint.

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
LOCKED = ("translateY", "rotateX", "rotateY", "rotateZ", "scaleX", "scaleY", "scaleZ")

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


def home_for(kind, group=None):
    """Where a character's label hangs: under the rig's top group (it dies
    with the rig's namespace), at world level (None) beside a bare skeleton.
    The one place that decides it. Pure."""
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
    # The floor height first, in world space (the home is static); then the
    # constraint takes X and Z from the root on every frame.
    at = cmds.xform(root, query=True, worldSpace=True, translation=True)
    cmds.xform(label, worldSpace=True, translation=(at[0], FLOOR, at[2] + FRONT))
    cmds.pointConstraint(root, label, skip="y", maintainOffset=False,
                         offset=(0.0, 0.0, FRONT))
    for attr in LOCKED:
        cmds.setAttr(label + "." + attr, lock=True)
    return label


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
    return keep


def label_rig(rig, name):
    """The clip's name under the rig `rig` (a `maya_rigs.Rig`). Following its
    game skeleton's root (root motion), else its Main. Never raises: a label
    that cannot be made must not fail an import - it says why in the Script
    Editor and answers None."""
    try:
        root = rig.skeleton_root or rig.main
        return ensure(root, name, rig.namespace, home_for("rig", rig.group))
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
        return None


def label_skeleton(root, name):
    """The clip's name under the bare skeleton whose root is `root`. Never
    raises (see `label_rig`)."""
    try:
        return ensure(root, name, "", home_for("skeleton"))
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
        return None
