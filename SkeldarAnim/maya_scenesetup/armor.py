"""Armor on a character: a rigid piece riding one bone, outside the skeleton.

2026-10-01, the animator: «сделаем для него отдельную панель Armor в которой пока будет только
техно лимб но позже мы добавим еще разные варианты одежды и брони ... просто будем выделять
предмет нажимать кнопочку equip и он будет добавляться к нашему персонажу в заранее указанное
место». A catalog row (`catalog.ARMOR`) names the piece's model, the bone it rides and the SLOT it
occupies; its model's points are already in that bone's local axes at its place (the Tech Limb's
by make_techlimb_asset.py, to 6e-6 cm of where Unreal puts it), so Equip stands it at identity in
the bone's ARMOR SPACE and its channels read 0 there -- a nudge by the animator shows as a number.

The space is the weapons' shape (`weaponspace`, 2026-09-24): a transform parent-constrained to the
bone with no offset, in an `ArmorSpaces` group under the rig's own group (at world level beside a
bare skeleton), never inside the skeleton -- so an export stays bones only and a retarget, which
moves the bone, moves the piece. Its markers are its own (`mayaArmorSpace`), so a weapon space is
never taken for an armor space and the other way round.

Found by attribute and connection, never by name: a piece carries `mayaArmor` (its row's key) and
`mayaArmorSlot`; a character's pieces are the ones whose space follows a bone of its skeleton.

A piece may carry a SKELETON of its own (the evening of 2026-10-01, the Tech Limb's shield: «в игре у
нас есть скелет для щита»): its `.ma` holds one group standing for the bone's space, the piece's joints
posed in it and its skinned mesh not inheriting (the skin alone moves it). It is imported into a
namespace of its own (`Tech_Limb`, `Tech_Limb1`, ...) -- the shield's `Root` would otherwise collide
with the next one's, and a namespaced root is never taken for a character by the UE bridge -- and the
whole group is the piece. Its joints have no joint parent, so `maya_overrig.active.character_roots`
leaves everything under an ArmorSpaces group out of the skeletons in the scene. Unequip removes the
namespace with whatever of the piece is left in it (its skin, its bind pose, its own material).
"""

import maya.cmds as cmds

from maya_scenesetup import attach
from maya_scenesetup import catalog
from maya_scenesetup import colour as colouring
from maya_scenesetup import skeleton
from maya_scenesetup import weaponspace

MARKER = "mayaArmor"              # the row's key, on the piece
SLOT = "mayaArmorSlot"            # the slot it occupies
NAMESPACE = "mayaArmorNamespace"  # the namespace a skeletal piece was imported into
SPACE_MARKER = "mayaArmorSpace"   # the space (the bone's UUID, for the record)
GROUP_MARKER = "mayaArmorSpaces"
GROUP_NAME = "ArmorSpaces"
SUFFIX = "_armorSpace"


# ------------------------------------------------------------------- pure

def character_name(root):
    """A rig's namespace, else the root's leaf. Pure."""
    leaf = (root or "").split("|")[-1]
    return leaf.split(":")[0] if ":" in leaf else leaf


def inside(path, root):
    """Whether `path` is `root` or under it. Pure; the separator is the whole test."""
    if not path or not root:
        return False
    return path == root or path.startswith(root + "|")


def slot_plan(worn, entry):
    """What an Equip of `entry` takes off: the keys of `worn` ({key: slot}) in `entry`'s slot,
    and `entry` itself if worn (equipping it again replaces it). Pure, sorted."""
    return sorted(set(key for key, slot in (worn or {}).items()
                      if slot == entry.slot or key == entry.key))


def _bone_leaf(bone):
    return (bone or "").split("|")[-1].split(":")[-1]


def equipped_message(label, bone, root, replaced, colour_name):
    text = "{0} on {1}'s {2}".format(label, character_name(root), _bone_leaf(bone))
    if replaced:
        text += " (replaced {0})".format(", ".join(replaced))
    if colour_name:
        text += ", in " + colour_name
    return text


def unequipped_message(label, root):
    return "{0} taken off {1}".format(label, character_name(root))


def not_worn_message(label, root):
    return "{0} does not wear {1}".format(character_name(root), label)


def no_bone_message(label, bone, root):
    return "{0} rides {1} - {2} has no such bone".format(label, bone, character_name(root))


def missing_message(label, path):
    return "{0}: the model is missing - {1}".format(label, path)


def pick_message(label, bone, worn):
    if worn:
        return ("{0} ({1}) - worn: Equip puts it on again, Unequip takes it off"
                .format(label, bone))
    return "{0} ({1}) - press Equip".format(label, bone)


# ------------------------------------------------------------------- scene

def bone_for(path):
    """The bone behind a selected path inside an armor space, or None -- what lets selecting a
    piece name its character (`skeleton.current_root`)."""
    return weaponspace.owner_for(path, SPACE_MARKER)


def space_of(bone):
    return weaponspace.marked_space_of(bone, SPACE_MARKER)


def _has(node, attr):
    return cmds.attributeQuery(attr, node=node, exists=True)


def _groups():
    """Every ArmorSpaces group: at world level, in a character group, or in a rig's own group (one
    level deeper since the character groups, 2026-10-02)."""
    import maya_rigs
    return maya_rigs.marked_near_top(GROUP_MARKER)


def pieces():
    """Every piece of ours in the scene: [(node, key, slot, bone)]."""
    out = []
    for group in _groups():
        for space in cmds.listRelatives(group, children=True, type="transform",
                                        fullPath=True) or []:
            if not _has(space, SPACE_MARKER):
                continue
            bone = weaponspace.bone_of(space)
            for node in cmds.listRelatives(space, children=True, type="transform",
                                           fullPath=True) or []:
                if _has(node, MARKER):
                    out.append((node, cmds.getAttr(node + "." + MARKER) or "",
                                cmds.getAttr(node + "." + SLOT) if _has(node, SLOT) else "",
                                bone))
    return out


def worn(root):
    """{key: (node, slot)} of the pieces `root`'s skeleton wears."""
    return dict((key, (node, slot)) for node, key, slot, bone in pieces()
                if inside(bone, root))


def _take_off(node):
    space = (cmds.listRelatives(node, parent=True, fullPath=True) or [None])[0]
    namespace = cmds.getAttr(node + "." + NAMESPACE) if _has(node, NAMESPACE) else ""
    cmds.delete(node)
    if space:
        weaponspace.prune_marked(space, SPACE_MARKER, GROUP_MARKER)
    if namespace and cmds.namespace(exists=":" + namespace):
        cmds.namespace(removeNamespace=":" + namespace, deleteNamespaceContent=True)


def has_skeleton(roots):
    """Whether what an import brought holds joints (a skeletal piece)."""
    for root in roots:
        if cmds.objectType(root) == "joint" or cmds.listRelatives(
                root, allDescendents=True, type="joint", fullPath=True):
            return True
    return False


def _import(entry):
    """(the transforms the import brought at world level, the namespace). An FBX through the
    FBX mode guard (trap 33), plain names; a `.ma`/`.mb` into a namespace of its own."""
    if entry.path.lower().endswith(".fbx"):
        return attach.import_model(entry.path), ""
    from maya_scenesetup import character
    namespace = character.free_namespace(entry.key, character.existing_namespaces())
    new = cmds.file(entry.path, i=True, type=character.scene_type(entry.path),
                    returnNewNodes=True, ignoreVersion=True, namespace=namespace) or []
    return attach.outermost(cmds.ls(new, long=True, type="transform") or []), namespace


def _hang(roots, entry, bone, namespace=""):
    """What the import brought, as the piece in `bone`'s armor space. A skeletal piece is its one
    group (the bone's space, its joints posed in it); else one mesh IS the piece (whatever wrapped it
    deleted), several kept in a group of ours. Marked, seated at identity -- the model already stands
    at its place in the bone's axes."""
    space = weaponspace.ensure_marked_space(bone, SPACE_MARKER, GROUP_MARKER, GROUP_NAME, SUFFIX)
    meshes = [] if has_skeleton(roots) else attach.mesh_transforms(roots)
    if has_skeleton(roots):
        if len(roots) != 1:
            cmds.delete(roots)
            raise RuntimeError("{0}: a skeletal piece is one group, the file brought {1}"
                               .format(entry.path, len(roots)))
        piece = cmds.ls(cmds.parent(roots[0], space)[0], long=True)[0]
    elif len(meshes) == 1:
        piece = cmds.ls(cmds.parent(meshes[0], space)[0], long=True)[0]
        leftovers = [path for path in cmds.ls(roots, long=True) or []
                     if cmds.objExists(path) and path != piece]
        if leftovers:
            cmds.delete(leftovers)
    else:
        group = cmds.group(empty=True, world=True, name="{0}_armor".format(entry.key))
        cmds.parent(roots, group)
        piece = cmds.ls(cmds.parent(group, space)[0], long=True)[0]
    cmds.addAttr(piece, longName=MARKER, dataType="string")
    cmds.setAttr(piece + "." + MARKER, entry.key, type="string")
    cmds.addAttr(piece, longName=SLOT, dataType="string")
    cmds.setAttr(piece + "." + SLOT, entry.slot, type="string")
    if namespace:
        cmds.addAttr(piece, longName=NAMESPACE, dataType="string")
        cmds.setAttr(piece + "." + NAMESPACE, namespace, type="string")
    attach.seat(piece, 1.0)
    return piece


def equip(root, entry, rgb=None):
    """`entry` onto `root`'s skeleton. Returns the line.

    Whatever the entry's slot holds on that character comes off first (the same piece again is
    replaced, never doubled). The import flushes Maya's undo queue (trap 115), so what follows it
    runs unrecorded, as Add Character's does: the piece arrives whole or not at all. A plain row
    wears the next free palette colour -- the Colour card repaints a selected piece -- and a
    textured row its image.
    """
    missing = catalog.missing(entry)
    if missing:
        return missing_message(entry.label, missing)
    bone = skeleton.resolve_bone(root, entry.bone)
    if not bone:
        return no_bone_message(entry.label, entry.bone, root)
    current = worn(root)
    replaced = []
    for key in slot_plan(dict((k, v[1]) for k, v in current.items()), entry):
        _take_off(current[key][0])
        row = catalog.armor_by_key(key)
        replaced.append(row.label if row else key)

    texture = getattr(entry, "texture", "")
    if not texture and rgb is None:
        rgb = colouring.free_colour().rgb
    roots, namespace = _import(entry)
    if not roots:
        raise RuntimeError("nothing came out of " + entry.path)
    from maya_scenesetup import character
    with character._unrecorded():
        piece = _hang(roots, entry, bone, namespace)
        if texture:
            colouring.paint_texture_nodes([piece], texture, entry.key)
            name = "its texture"
        else:
            colouring.paint_nodes([piece], rgb, entry.key)
            name = colouring.colour_name(rgb)
    return equipped_message(entry.label, bone, root, replaced, name)


def unequip(root, key):
    """The piece `key` off `root`'s skeleton, its space pruned. One undo chunk."""
    row = catalog.armor_by_key(key)
    label = row.label if row else key
    current = worn(root)
    if key not in current:
        return not_worn_message(label, root)
    cmds.undoInfo(openChunk=True)
    try:
        _take_off(current[key][0])
    finally:
        cmds.undoInfo(closeChunk=True)
    return unequipped_message(label, root)
