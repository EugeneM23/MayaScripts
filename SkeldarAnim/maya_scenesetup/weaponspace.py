"""Where a weapon lives: OUTSIDE the skeleton, in a space that follows the hand.

2026-09-24, the animator: «давай делать всё максимально правильно, так чтобы мы не нарушали
иерархию нашего скелета». Until then Weapons > Add parented the weapon's mesh under the hand
bone, and every export of the skeleton carried it -- measured: an animation FBX of the Creep
held `CreepSwordMesh`, 10890 vertices, its six animation curves and its material, 1.4 MB of
geometry in a file Unreal reads bones from.

Now each hand that holds a weapon has a SPACE: a plain transform parent-constrained to the
hand with no offset, standing in a `WeaponSpaces` group -- under the rig's own group when the
hand belongs to a rig (so the rig's namespace, its selection and its deletion keep it), at
world level for a bare skeleton. The weapon is the space's child, so the weapon's channels
still mean "relative to the hand": the grip fields, the bone link (`bonedrive`, all world
space and constraints), Connections' re-bakes and every key the animator sets on the sword
are what they were. The skeleton holds bones and nothing else.

Identity by connection and attribute, never by name: a space is found FROM its hand, through
the parentConstraint the hand drives (`space_of`), and carries `mayaWeaponSpace` (the hand's
UUID, for the record). A leaf module: maya.cmds and maya_rigs only.

Since 2026-10-01 the machinery is generic over its markers (`marked_space_of`,
`ensure_marked_space`, `prune_marked`, `owner_for`): the Armor card hangs its pieces in spaces of
the same shape on any bone (`armor`, `mayaArmorSpace` in an `ArmorSpaces` group), and each kind
finds only its own -- a weapon space is never an armor space.
"""

import maya.cmds as cmds

import maya_rigs

SPACE_MARKER = "mayaWeaponSpace"
GROUP_MARKER = "mayaWeaponSpaces"
GROUP_NAME = "WeaponSpaces"
SUFFIX = "_weaponSpace"


# ------------------------------------------------------------------- pure

def space_name(hand, suffix=SUFFIX):
    """`hand_r_weaponSpace` for `|ns:root|...|ns:hand_r`. Pure. The name is for the outliner;
    nothing ever looks a space up by it."""
    return hand.split("|")[-1].split(":")[-1] + suffix


# ------------------------------------------------------------------- scene

def _long(node):
    found = cmds.ls(node, long=True) or []
    return found[0] if found else None


def is_marked(node, marker):
    return bool(node) and cmds.objExists(node) and cmds.attributeQuery(marker, node=node, exists=True)


def is_space(node):
    return is_marked(node, SPACE_MARKER)


def marked_space_of(bone, marker):
    """The space carrying `marker` that follows `bone`, or None -- found through the constraints
    the bone drives."""
    if not bone or not cmds.objExists(bone):
        return None
    for con in set(cmds.listConnections(bone, type="parentConstraint", source=False,
                                        destination=True) or []):
        parent = cmds.listRelatives(con, parent=True, fullPath=True) or []
        if parent and is_marked(parent[0], marker):
            return parent[0]
    return None


def space_of(hand):
    """The weapon space that follows `hand`, or None."""
    return marked_space_of(hand, SPACE_MARKER)


def bone_of(space):
    """The bone `space` follows (its constraint's target), or None."""
    for con in cmds.listRelatives(space, children=True, type="parentConstraint", fullPath=True) or []:
        targets = cmds.parentConstraint(con, query=True, targetList=True) or []
        if targets:
            return _long(targets[0])
    return None


hand_of = bone_of


def holding_hand(node):
    """The hand that holds `node`: its space's hand, or -- a file from before 2026-09-24 -- the
    joint it is parented under directly. None for a node out in the world."""
    parent = (cmds.listRelatives(node, parent=True, fullPath=True) or [None])[0]
    if parent is None:
        return None
    if is_space(parent):
        return hand_of(parent)
    if cmds.objectType(parent) == "joint":
        return parent
    return None


def owner_for(path, marker):
    """The bone behind a selected path inside a space carrying `marker`, or None."""
    parts = [p for p in (path or "").split("|") if p]
    for i in range(len(parts), 0, -1):
        node = "|" + "|".join(parts[:i])
        if is_marked(node, marker):
            return bone_of(node)
    return None


def hand_for(path):
    """The hand behind a selected path inside a weapon space, or None -- what lets selecting
    the sword name its character, as selecting it under the hand used to."""
    return owner_for(path, SPACE_MARKER)


def _group_under(parent, group_marker=GROUP_MARKER, group_name=GROUP_NAME):
    """Our group carrying `group_marker` under `parent` (None: world level), made on demand."""
    children = (cmds.listRelatives(parent, children=True, type="transform", fullPath=True) or []) \
        if parent else (cmds.ls(assemblies=True, long=True) or [])
    for child in children:
        if cmds.attributeQuery(group_marker, node=child, exists=True):
            return child
    group = cmds.createNode("transform", name=group_name, parent=parent, skipSelect=True) if parent \
        else cmds.createNode("transform", name=group_name, skipSelect=True)
    group = _long(group)
    cmds.addAttr(group, longName=group_marker, attributeType="bool")
    for attr in ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"):
        cmds.setAttr(group + "." + attr, lock=True)
    return group


def group_for(hand, group_marker=GROUP_MARKER, group_name=GROUP_NAME):
    """Where `hand`'s space stands: in the rig's own group when the hand is a rig's, else at
    world level -- never inside the skeleton."""
    rig = maya_rigs.rig_of(hand, maya_rigs.rigs())
    return _group_under(maya_rigs.top_of(rig.group) if rig is not None and rig.group else None,
                        group_marker, group_name)


def ensure_marked_space(bone, marker, group_marker, group_name, suffix):
    """The space carrying `marker` that follows `bone`, made when there is none: an identity
    transform in `group_for(bone, ...)`, parent-constrained to the bone with NO offset."""
    found = marked_space_of(bone, marker)
    if found:
        return found
    space = _long(cmds.createNode("transform", name=space_name(bone, suffix),
                                  parent=group_for(bone, group_marker, group_name),
                                  skipSelect=True))
    cmds.addAttr(space, longName=marker, dataType="string")
    cmds.setAttr(space + "." + marker, (cmds.ls(bone, uuid=True) or [""])[0], type="string")
    cmds.parentConstraint(bone, space, maintainOffset=False)
    return _long(space)


def ensure_space(hand):
    """The weapon space following `hand`, made when there is none."""
    return ensure_marked_space(hand, SPACE_MARKER, GROUP_MARKER, GROUP_NAME, SUFFIX)


def prune_marked(space, marker, group_marker):
    """Delete `space` when nothing but its own constraint is left in it, and its group when
    that was the last space. Returns True when the space went."""
    if not is_marked(space, marker):
        return False
    kids = [k for k in cmds.listRelatives(space, children=True, fullPath=True) or []
            if not cmds.objectType(k, isAType="constraint")]
    if kids:
        return False
    group = (cmds.listRelatives(space, parent=True, fullPath=True) or [None])[0]
    cmds.delete(space)
    if group and cmds.objExists(group) and cmds.attributeQuery(group_marker, node=group, exists=True) \
            and not cmds.listRelatives(group, children=True):
        for attr in ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"):
            cmds.setAttr(group + "." + attr, lock=False)
        cmds.delete(group)
    return True


def prune(space):
    """The weapon space's `prune_marked`."""
    return prune_marked(space, SPACE_MARKER, GROUP_MARKER)
