"""One outliner group and one display layer per character.

2026-10-02, the animator: «Сейчас каждый персонаж в сцене создает кучу мусора если это не повредит
нам то давай сделаем так чтобы все части которые относятся к одному персонажу ригу были в одной
группе, важно что бы пользователь открыл аутлайнер и сразу все понял. Так же каждый риг должен иметь
свою группу слой что бы его можно было включать и отключать в сцене.» Spec:
docs/superpowers/specs/2026-10-02-character-groups-design.md.

**The group** (`make`): a transform at WORLD level, `<base>_Character` -- a rig's base is its
namespace (`Manny_Rig1_Character`), a skeleton's its asset's file stem made free
(`Manny_Skeleton_Character`, `Manny_Skeleton1_Character`). Not the namespace's own name: measured,
Maya will not give a node a namespace's name (it answered `Manny_Rig1`), and a namespace cannot be
made over a node's name at all (silently: `namespace -exists` False after `namespace -add`). It is
MARKED `skeldarCharacterGroup` (the catalog label) with a message link `skeldarCharacterRoot` from
the character's root, found by the marker and never by name (`maya_rigs.group_of`), and its
translate / rotate / scale are LOCKED at identity: it is a folder, not a control -- a rig moves by
`Main`, a skeleton by its `root`, and an identity parent is what makes every re-parent here exact
(`relative=True` keeps every world matrix, a skinned mesh's included).

**What goes in it**: everything the Add brought at world level (a rig's AdvancedSkeleton `Group`,
its game skeleton, the asset's stray tops; a skeleton's root or its `Armature` Null, its meshes, the
`camera1` an asset carries), and since then everything parked for the character (`park`): a bare
skeleton's weapon / armor spaces, a weapon on the floor, the Camera Setup camera, the centre of mass,
a weapon Connections lifts out to world -- and any future part (one call: `park(node, owner)`).

**The layer** (`<base>_Layer`): one per character, its one member the group (`noRecurse`), so its V
hides and shows the whole character. Measured: a mesh in a VISIBLE layer of its own under the hidden
group is hidden too (`MDagPath.isVisible` False), so the assets' own layers (`Creep_Skeleton`, the
rig's) cannot fight it. It goes with the character on Delete (a DG node touching only the group --
the displayLayerManager is a hub) and comes back with Ctrl+Z.

**The FBX exporter writes the selected bones' ANCESTORS** (measured: `|CharGrp|root|pelvis`
exported with `-s` and `IncludeChildren false` came back as `|CharGrp|root|pelvis`), so an export
takes the character's top out to world for its length (`lifted`) and puts it back by UUID.

A character added before 2026-10-02 has no group: every lookup answers None for it and every road
behaves exactly as before. A leaf module: maya.cmds and maya_rigs only.
"""

import contextlib
import re

import maya.cmds as cmds

import maya_rigs

MARKER = maya_rigs.CHARACTER_MARKER
ROOT_LINK = maya_rigs.CHARACTER_ROOT
GROUP_SUFFIX = "_Character"
LAYER_SUFFIX = "_Layer"
LOCKED = tuple(a + x for a in "trs" for x in "xyz")

_ILLEGAL = re.compile(r"[^A-Za-z0-9_]")


# ------------------------------------------------------------------- pure

def legal(base):
    """A Maya-legal node name stem from `base`. Pure."""
    name = _ILLEGAL.sub("_", base or "") or "Character"
    return "_" + name if name[0].isdigit() else name


def group_name(base):
    return legal(base) + GROUP_SUFFIX


def layer_name(base):
    return legal(base) + LAYER_SUFFIX


def free_base(base, taken):
    """`base`, else `base1`, `base2`, ... -- the first whose group AND layer names are free of
    `taken` (root-namespace node names). Pure. Two Manny skeletons read `Manny_Skeleton_Character`
    and `Manny_Skeleton1_Character`, the way two rigs read `Manny_Rig_Character` /
    `Manny_Rig1_Character`."""
    stem = legal(base)
    taken = set(taken or ())
    index = 0
    while True:
        candidate = stem if not index else "{0}{1}".format(stem, index)
        if group_name(candidate) not in taken and layer_name(candidate) not in taken:
            return candidate
        index += 1


def child_on_path(path, group):
    """The child of `group` on `path`'s way down (`|G|Armature|root` -> `|G|Armature`), or None
    when `path` is not under `group`. Pure."""
    if not group or not path or not path.startswith(group + "|"):
        return None
    rest = path[len(group) + 1:].split("|")[0]
    return group + "|" + rest


# ------------------------------------------------------------------ scene

def _long(node):
    found = cmds.ls(node, long=True) if node else []
    return found[0] if found else None


def _uuid(node):
    found = cmds.ls(node, uuid=True) if node else []
    return found[0] if found else None


def group_of(thing):
    """The character group of a Rig, or of a path inside a character, or None (a legacy
    character, anything of nobody's). THE question every module asks before parking a part."""
    if isinstance(thing, maya_rigs.Rig):
        if thing.character and cmds.objExists(thing.character):
            return thing.character
        thing = thing.group or thing.skeleton_root
    return maya_rigs.group_of(thing) if thing else None


def root_of(group):
    """The character root the group's message link names, or None."""
    return maya_rigs.group_root(group)


def layer_of(group):
    """The display layer whose member the group is, or None."""
    if not group or not cmds.objExists(group):
        return None
    found = cmds.listConnections(group + ".drawOverride", source=True, destination=False,
                                 type="displayLayer") or []
    return found[0] if found else None


def taken_names():
    """Root-namespace node names in the scene (what a new group or layer must not collide with)."""
    return set(n for n in (cmds.ls() or []) if ":" not in n and "|" not in n)


def make(base, label, root, tops):
    """The character's group and layer: the group at world level, `tops` parented under it
    unmoved (relative to an identity parent), its transform locked, the layer holding it.
    Returns (group long path, layer). Runs inside Add Character's unrecorded block (trap 115: the
    import flushed the undo queue anyway)."""
    base = free_base(base, taken_names())
    group = cmds.createNode("transform", name=":" + group_name(base), skipSelect=True)
    group = _long(group)
    cmds.addAttr(group, longName=MARKER, dataType="string")
    cmds.setAttr(group + "." + MARKER, label or "", type="string")
    cmds.addAttr(group, longName=ROOT_LINK, attributeType="message")
    if root and cmds.objExists(root):
        cmds.connectAttr(root + ".message", group + "." + ROOT_LINK)
    uuid = _uuid(group)
    moving = [u for u in (_uuid(t) for t in tops or []) if u]
    for item in moving:
        path = _long(item)
        if path and not maya_rigs.under(path, _long(uuid)):
            cmds.parent(path, _long(uuid), relative=True)
    group = _long(uuid)
    for attr in LOCKED:
        cmds.setAttr(group + "." + attr, lock=True)
    layer = cmds.createDisplayLayer(name=":" + layer_name(base), empty=True, noRecurse=True)
    cmds.editDisplayLayerMembers(layer, group, noRecurse=True)
    return group, layer


def park(node, owner):
    """`node` (a world-level part: a camera, a floor weapon, a space group, a CoM group) into the
    character group of `owner` (a Rig, or a path of the character), unmoved. Returns its long
    path -- unchanged when the owner has no group (a legacy character) or it is in it already."""
    path = _long(node)
    group = group_of(owner) if owner is not None else None
    if not path or not group or maya_rigs.under(path, group):
        return path
    uuid = _uuid(path)
    cmds.parent(path, group, relative=True)
    return _long(uuid)


@contextlib.contextmanager
def lifted(node):
    """`node`'s character top out at world level for the length of the block (an FBX export:
    the exporter writes a selected bone's ancestors into the file), put back by UUID with the name
    it had. Yields `node`'s long path while lifted. No group: nothing moves."""
    path = _long(node)
    group = maya_rigs.group_of(path) if path else None
    top = child_on_path(path, group) if group else None
    if not top:
        yield path
        return
    node_uuid, top_uuid, group_uuid = _uuid(path), _uuid(top), _uuid(group)
    name = top.split("|")[-1]
    moved = False
    try:
        cmds.parent(top, world=True, relative=True)
        moved = True
        yield _long(node_uuid)
    finally:
        now, home = _long(top_uuid), _long(group_uuid)
        if moved and now and home:
            cmds.parent(now, home, relative=True)
            now = _long(top_uuid)
            if now and now.split("|")[-1] != name:
                try:
                    cmds.rename(now, name)
                except RuntimeError:
                    pass
