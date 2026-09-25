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
"""

import maya.cmds as cmds

import maya_rigs

SPACE_MARKER = "mayaWeaponSpace"
GROUP_MARKER = "mayaWeaponSpaces"
GROUP_NAME = "WeaponSpaces"


# ------------------------------------------------------------------- pure

def space_name(hand):
    """`hand_r_weaponSpace` for `|ns:root|...|ns:hand_r`. Pure. The name is for the outliner;
    nothing ever looks a space up by it."""
    return hand.split("|")[-1].split(":")[-1] + "_weaponSpace"


# ------------------------------------------------------------------- scene

def _long(node):
    found = cmds.ls(node, long=True) or []
    return found[0] if found else None


def is_space(node):
    return bool(node) and cmds.objExists(node) and cmds.attributeQuery(SPACE_MARKER, node=node, exists=True)


def space_of(hand):
    """The space that follows `hand`, or None -- found through the constraints the hand drives."""
    if not hand or not cmds.objExists(hand):
        return None
    for con in set(cmds.listConnections(hand, type="parentConstraint", source=False,
                                        destination=True) or []):
        parent = cmds.listRelatives(con, parent=True, fullPath=True) or []
        if parent and is_space(parent[0]):
            return parent[0]
    return None


def hand_of(space):
    """The hand `space` follows (its constraint's target), or None."""
    for con in cmds.listRelatives(space, children=True, type="parentConstraint", fullPath=True) or []:
        targets = cmds.parentConstraint(con, query=True, targetList=True) or []
        if targets:
            return _long(targets[0])
    return None


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


def hand_for(path):
    """The hand behind a selected path inside a weapon space, or None -- what lets selecting
    the sword name its character, as selecting it under the hand used to."""
    parts = [p for p in (path or "").split("|") if p]
    for i in range(len(parts), 0, -1):
        node = "|" + "|".join(parts[:i])
        if is_space(node):
            return hand_of(node)
    return None


def _group_under(parent):
    """Our WeaponSpaces group under `parent` (None: world level), made on demand."""
    children = (cmds.listRelatives(parent, children=True, type="transform", fullPath=True) or []) \
        if parent else (cmds.ls(assemblies=True, long=True) or [])
    for child in children:
        if cmds.attributeQuery(GROUP_MARKER, node=child, exists=True):
            return child
    group = cmds.createNode("transform", name=GROUP_NAME, parent=parent, skipSelect=True) if parent \
        else cmds.createNode("transform", name=GROUP_NAME, skipSelect=True)
    group = _long(group)
    cmds.addAttr(group, longName=GROUP_MARKER, attributeType="bool")
    for attr in ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"):
        cmds.setAttr(group + "." + attr, lock=True)
    return group


def group_for(hand):
    """Where `hand`'s space stands: in the rig's own group when the hand is a rig's, else at
    world level -- never inside the skeleton."""
    rig = maya_rigs.rig_of(hand, maya_rigs.rigs())
    return _group_under(maya_rigs.top_of(rig.group) if rig is not None and rig.group else None)


def ensure_space(hand):
    """The space following `hand`, made when there is none: an identity transform in
    `group_for(hand)`, parent-constrained to the hand with NO offset."""
    found = space_of(hand)
    if found:
        return found
    space = _long(cmds.createNode("transform", name=space_name(hand), parent=group_for(hand),
                                  skipSelect=True))
    cmds.addAttr(space, longName=SPACE_MARKER, dataType="string")
    cmds.setAttr(space + "." + SPACE_MARKER, (cmds.ls(hand, uuid=True) or [""])[0], type="string")
    cmds.parentConstraint(hand, space, maintainOffset=False)
    return _long(space)


def prune(space):
    """Delete `space` when nothing but its own constraint is left in it, and its group when
    that was the last space. Returns True when the space went."""
    if not is_space(space):
        return False
    kids = [k for k in cmds.listRelatives(space, children=True, fullPath=True) or []
            if not cmds.objectType(k, isAType="constraint")]
    if kids:
        return False
    group = (cmds.listRelatives(space, parent=True, fullPath=True) or [None])[0]
    cmds.delete(space)
    if group and cmds.objExists(group) and cmds.attributeQuery(GROUP_MARKER, node=group, exists=True) \
            and not cmds.listRelatives(group, children=True):
        for attr in ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"):
            cmds.setAttr(group + "." + attr, lock=False)
        cmds.delete(group)
    return True
