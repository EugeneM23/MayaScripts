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

A piece may be CLOTHING (2026-10-21, the Playerchar's helmet, body armor, shield and pants: «сделать
броню шлем щит штаны как одежду»): a row of kind `catalog.SKINNED`, its `.ma` a group of meshes skinned
to a copy of the game skeleton at the bind they were skinned on. Equip refuses a wearer whose skeleton
lacks a bone the skins use, or whose bones at its bind are not the piece's lengths (`fit_refusal`: the
median within 1 % - the animator's pick, «same skeleton only»); else every skinCluster's `matrix[i]`
is reconnected to the wearer's joint of the same name - the bindPreMatrix stays the piece's, and a
twin's joints at their bind stand where the piece's did, wherever the character stands - the piece's
own skeleton and bind pose go, and the group hangs in the row's bone's armor space like any piece.
Each mesh has `inheritsTransform` off (the asset sets it): the skin already places it, the space's
motion must not be added on top.
"""

import maya.cmds as cmds

from maya_scenetabs import scope

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
    """A rig's namespace, else the root's leaf - as the active scene tab shows it."""
    leaf = scope.local(root or "", cmds).split("|")[-1]
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


FIT_TOLERANCE = 0.01   # the median bone within 1 % of the piece's: the skeleton it was skinned on
SHORTEST = 1.0         # cm: shorter bones do not vote


def bone_lengths(bones):
    """{bone: length to its parent} of `bones` ({leaf: (parent leaf or None, (x, y, z))}). Pure."""
    out = {}
    for name, (parent, point) in (bones or {}).items():
        if parent and parent in bones:
            other = bones[parent][1]
            out[name] = sum((a - b) ** 2 for a, b in zip(point, other)) ** 0.5
    return out


def fit_refusal(label, wearer, needed, piece_bones, wearer_bones,
                tolerance=FIT_TOLERANCE, shortest=SHORTEST):
    """Why `wearer` cannot wear the clothing `label`, or "". `needed` are the bones its skins use;
    the two skeletons as `bone_lengths` takes them, each at its bind. Pure.

    A missing bone is named; else the median relative difference of the bones both carry, longer
    than `shortest`, must be within `tolerance` - the piece fits the skeleton it was skinned on."""
    missing = sorted(set(needed or []) - set(wearer_bones or {}))
    if missing:
        shown = ", ".join(missing[:4]) + (" ..." if len(missing) > 4 else "")
        return "{0} needs {1} - {2} has no such bone".format(label, shown, wearer)
    mine, theirs = bone_lengths(piece_bones), bone_lengths(wearer_bones)
    diffs = sorted(abs(mine[b] - theirs[b]) / max(mine[b], theirs[b]) for b in mine
                   if b in theirs and max(mine[b], theirs[b]) > shortest)
    if not diffs:
        return "{0}: {1} shares no bone with it".format(label, wearer)
    median = diffs[len(diffs) // 2]
    if median > tolerance:
        return ("{0} is made for another body - {1}'s bones differ from its skeleton by {2:.0f} % "
                "(median)".format(label, wearer, median * 100.0))
    return ""


def rewire_plan(influences, wearer):
    """[(matrix index, the wearer's joint)] for a skin's `influences` ([(index, leaf)]), and the
    leaves the wearer lacks. `wearer` is {leaf: path}. Pure."""
    plan, missing = [], []
    for index, name in influences:
        if name in wearer:
            plan.append((index, wearer[name]))
        else:
            missing.append(name)
    return plan, missing


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
    #  the piece's namespace as it stood when worn: in a scene tab's while tabs are on
    #  (2026-10-15), else at the root
    for name in ([scope.absolute(namespace, cmds), ":" + namespace] if namespace else []):
        if cmds.namespace(exists=name):
            cmds.namespace(removeNamespace=name, deleteNamespaceContent=True)
            break


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


def _discard(roots, namespace):
    """What an import brought, and its namespace, gone (a refused piece)."""
    for node in roots:
        if cmds.objExists(node):
            cmds.delete(node)
    for name in ([scope.absolute(namespace, cmds), ":" + namespace] if namespace else []):
        if cmds.namespace(exists=name):
            cmds.namespace(removeNamespace=name, deleteNamespaceContent=True)
            break


def _skins_of(nodes):
    shapes = cmds.ls(nodes, dag=True, type="mesh", long=True, noIntermediate=True) or []
    return sorted(set(cmds.ls(cmds.listHistory(shapes, pruneDagObjects=True) or [],
                              type="skinCluster") or []))


def _influences(skin):
    """[(matrix index, the influence's leaf)] of `skin`."""
    out = []
    for index in cmds.getAttr(skin + ".matrix", multiIndices=True) or []:
        source = cmds.listConnections("{0}.matrix[{1}]".format(skin, index), source=True,
                                      destination=False)
        if source:
            out.append((index, _bone_leaf(source[0])))
    return out


def _bones(joints, world):
    """{leaf: (parent leaf or None, (x, y, z))} of `joints`, placed by `world(joint)` (16 floats)."""
    paths = set(joints)
    out = {}
    for joint in joints:
        parent = cmds.listRelatives(joint, parent=True, type="joint", fullPath=True)
        matrix = world(joint)
        out[_bone_leaf(joint)] = (_bone_leaf(parent[0]) if parent and parent[0] in paths else None,
                                  (matrix[12], matrix[13], matrix[14]))
    return out


def _split_clothing(roots, entry):
    """(the piece's group, its skeleton's root) out of what a clothing file brought."""
    tops = [r for r in roots if cmds.objectType(r) == "joint"]
    groups = [r for r in roots if cmds.objectType(r) != "joint"]
    if len(tops) != 1 or len(groups) != 1:
        raise RuntimeError("{0}: clothing is one group and one skeleton, the file brought {1}"
                           .format(entry.path, roots))
    return groups[0], tops[0]


def clothing_refusal(roots, entry, root):
    """Why `root`'s skeleton cannot wear the imported clothing, or ""."""
    import maya_retargetmode
    group, top = _split_clothing(roots, entry)
    needed = sorted(set(name for skin in _skins_of([group]) for _i, name in _influences(skin)))
    piece_joints = cmds.ls(top, dag=True, type="joint", long=True) or []
    wearer_joints = cmds.ls(root, dag=True, type="joint", long=True) or []
    return fit_refusal(entry.label, character_name(root), needed,
                       _bones(piece_joints, lambda j: cmds.getAttr(j + ".worldMatrix[0]")),
                       _bones(wearer_joints, maya_retargetmode.rest_world))


def _wear(roots, entry, bone, root, namespace):
    """The imported clothing's skins onto `root`'s bones by name, its own skeleton and bind pose
    gone, its group hung in `bone`'s armor space and marked. Returns the piece."""
    group, top = _split_clothing(roots, entry)
    wearer = dict((_bone_leaf(j), j) for j in cmds.ls(root, dag=True, type="joint", long=True) or [])
    poses = set()
    group_id = cmds.ls(group, uuid=True)[0]
    for skin in _skins_of([group]):
        plan, missing = rewire_plan(_influences(skin), wearer)
        if missing:
            raise RuntimeError("{0}: {1} has no {2}".format(entry.label, character_name(root),
                                                             ", ".join(missing)))
        for index, joint in plan:
            cmds.connectAttr(joint + ".worldMatrix[0]", "{0}.matrix[{1}]".format(skin, index),
                             force=True)
        poses.update(cmds.listConnections(skin + ".bindPose", source=True, destination=False) or [])
    cmds.delete(top)
    for pose in poses:
        if cmds.objExists(pose):
            cmds.delete(pose)
    group = cmds.ls(group_id, long=True)[0]
    for mesh in cmds.ls(group, dag=True, type="transform", long=True) or []:
        if mesh != group:
            cmds.setAttr(mesh + ".inheritsTransform", 0)
    space = weaponspace.ensure_marked_space(bone, SPACE_MARKER, GROUP_MARKER, GROUP_NAME, SUFFIX)
    piece = cmds.ls(cmds.parent(group, space)[0], long=True)[0]
    for attr, value in ((MARKER, entry.key), (SLOT, entry.slot), (NAMESPACE, namespace)):
        if value:
            cmds.addAttr(piece, longName=attr, dataType="string")
            cmds.setAttr(piece + "." + attr, value, type="string")
    attach.seat(piece, 1.0)
    return piece


def _take_off_slot(root, entry):
    """The pieces `entry`'s slot holds on `root` taken off (and `entry` itself); their labels."""
    current = worn(root)
    replaced = []
    for key in slot_plan(dict((k, v[1]) for k, v in current.items()), entry):
        _take_off(current[key][0])
        row = catalog.armor_by_key(key)
        replaced.append(row.label if row else key)
    return replaced


def _paint(piece, entry, rgb):
    texture = getattr(entry, "texture", "")
    if texture:
        colouring.paint_texture_nodes([piece], texture, entry.key)
        return "its texture"
    colouring.paint_nodes([piece], rgb, entry.key)
    return colouring.colour_name(rgb)


def _equip_clothing(root, entry, bone, rgb):
    """A skinned row onto `root`: imported, checked against the wearer's skeleton (a refusal
    leaves the scene as it was: nothing taken off), the slot emptied, worn."""
    roots, namespace = _import(entry)
    if not roots:
        raise RuntimeError("nothing came out of " + entry.path)
    from maya_scenesetup import character
    with character._unrecorded():
        refusal = clothing_refusal(roots, entry, root)
        if refusal:
            _discard(roots, namespace)
            return refusal
        replaced = _take_off_slot(root, entry)
        piece = _wear(roots, entry, bone, root, namespace)
        name = _paint(piece, entry, rgb)
    return equipped_message(entry.label, bone, root, replaced, name)


def equip(root, entry, rgb=None):
    """`entry` onto `root`'s skeleton. Returns the line.

    Whatever the entry's slot holds on that character comes off first (the same piece again is
    replaced, never doubled). The import flushes Maya's undo queue (trap 115), so what follows it
    runs unrecorded, as Add Character's does: the piece arrives whole or not at all. A plain row
    wears the next free palette colour -- the Colour card repaints a selected piece -- and a
    textured row its image. A clothing row (`catalog.SKINNED`) is checked against the wearer's
    skeleton first, and a refusal changes nothing.
    """
    missing = catalog.missing(entry)
    if missing:
        return missing_message(entry.label, missing)
    bone = skeleton.resolve_bone(root, entry.bone)
    if not bone:
        return no_bone_message(entry.label, entry.bone, root)
    if not getattr(entry, "texture", "") and rgb is None:
        rgb = colouring.free_colour().rgb
    if getattr(entry, "kind", catalog.RIGID) == catalog.SKINNED:
        return _equip_clothing(root, entry, bone, rgb)
    replaced = _take_off_slot(root, entry)
    roots, namespace = _import(entry)
    if not roots:
        raise RuntimeError("nothing came out of " + entry.path)
    from maya_scenesetup import character
    with character._unrecorded():
        piece = _hang(roots, entry, bone, namespace)
        name = _paint(piece, entry, rgb)
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
