"""The inventory's scene actions: a weapon into a hand, onto the floor, off.

2026-09-29, the weapon inventory. Every path is the Weapons section's own
machinery - `attach` for a hand (with the grip that hand remembers, `grips`),
`floor` for the floor, `attach.detach` to take off - so the inventory and the
panel can never disagree about what "a weapon in the left hand" is. Each
action is ONE undo chunk and answers its status line; a refusal changes
nothing and says why.

A side is "R" or "L"; its bone is the catalog row's bone for the right hand
and its twin for the left (`catalog.side_bone`).
"""

from collections import namedtuple

import maya.cmds as cmds

import maya_rigs
from maya_scenesetup import attach
from maya_scenesetup import bonedrive
from maya_scenesetup import catalog
from maya_scenesetup import colour as colouring
from maya_scenesetup import connections
from maya_scenesetup import floor
from maya_scenesetup import grips
from maya_scenesetup import skeleton

# `where`: "hand" (held, or out in world after a Connections lift - either
# way the hand's), "floor" (lying there, the bone following it), "follows"
# (the hand's IK rides a weapon of the other hand), or None.
Holding = namedtuple("Holding", "where weapon key label")
EMPTY = Holding(None, None, "", "")
SIDE_LABEL = {"R": "right hand", "L": "left hand"}
BONE = "weapon_r"


# ------------------------------------------------------------------- pure

def floor_side(taken):
    """The bone a weapon dropped on the floor takes: the free one, right
    first; both taken -> the right hand's weapon is replaced. Pure."""
    if not taken.get("R"):
        return "R"
    if not taken.get("L"):
        return "L"
    return "R"


def character_name(root):
    """A rig's namespace, else the root's leaf. Pure."""
    leaf = (root or "").split("|")[-1]
    return leaf.split(":")[0] if ":" in leaf else leaf


def into_message(label, root, side):
    return "%s into %s's %s" % (label, character_name(root), SIDE_LABEL[side])


def floor_message(label, root, side):
    return "%s onto the floor - %s's %s follows it" % (
        label, character_name(root), catalog.side_bone(BONE, side))


def off_message(label, root, side):
    return "%s off %s's %s - the bone has its animation back" % (
        label, character_name(root), SIDE_LABEL[side])


# ------------------------------------------------------------------ scene

def bones(root, side):
    """(hand, drive bone) of `side`, either None when the skeleton lacks it."""
    bone = skeleton.resolve_bone(root, catalog.side_bone(BONE, side)) \
        if root else None
    return (attach.parent_bone(bone) if bone else None), bone


def occupant(root, side):
    """(weapon, where) on `side`: held in the hand, or out in world driving
    its bone ("floor" when it lies with a parked track, "hand" when a
    Connections lift took it out); (None, None) when the side is free."""
    hand, bone = bones(root, side)
    if not bone:
        return None, None
    held = (attach.find_attached(hand) if hand else None) \
        or attach.find_attached(bone)
    if held:
        return held, "hand"
    world = bonedrive.driving_weapon(bone)
    if world:
        return world, ("floor" if bonedrive.is_parked(world) else "hand")
    return None, None


def _rig(root):
    return maya_rigs.rig_of(root, maya_rigs.rigs()) if root else None


def _key(weapon):
    if weapon and cmds.objExists(weapon) and cmds.attributeQuery(
            attach.MARKER, node=weapon, exists=True):
        return cmds.getAttr(weapon + "." + attach.MARKER) or ""
    return ""


def holdings(root):
    """{side: Holding} for the paper doll."""
    out = {}
    rig = _rig(root)
    for side in catalog.SIDES:
        weapon, where = occupant(root, side)
        if weapon:
            out[side] = Holding(where, weapon, _key(weapon),
                                connections.weapon_label(weapon))
            continue
        rides = connections.following(rig, side) if rig else None
        out[side] = (Holding("follows", rides, _key(rides),
                             connections.weapon_label(rides))
                     if rides else EMPTY)
    return out


def entry_of(weapon):
    """The catalog row a weapon node came from, else an entry for the file
    it was imported from (`attach.SOURCE`), else None."""
    entry = catalog.by_key(_key(weapon))
    if entry:
        return entry
    if weapon and cmds.attributeQuery(attach.SOURCE, node=weapon, exists=True):
        path = cmds.getAttr(weapon + "." + attach.SOURCE)
        if path:
            return catalog.entry_for_path(path, BONE)
    return None


def _refusal(root, side):
    """Why `side` of `root` cannot take a weapon now, or ""."""
    if not root:
        return "no character there"
    _hand, bone = bones(root, side)
    if not bone:
        return "%s has no bone '%s'" % (character_name(root),
                                        catalog.side_bone(BONE, side))
    if not _hand:
        return "'%s' has no parent bone" % catalog.side_bone(BONE, side)
    rig = _rig(root)
    rides = connections.following(rig, side) if rig else None
    if rides:
        return "the %s follows the %s - release it in Connections first" % (
            SIDE_LABEL[side], connections.weapon_label(rides))
    weapon, _where = occupant(root, side)
    if weapon and connections.followers_of(weapon):
        return "the hands ride the %s - release them in Connections first" % (
            connections.weapon_label(weapon))
    return ""


def _missing(entry):
    absent = catalog.missing(entry)
    return ("file not found: " + absent) if absent else ""


def to_hand(root, side, entry):
    """`entry`'s weapon into `side`'s hand of `root` - Add's rule: whatever
    that hand held or that bone followed is taken off first."""
    refusal = _refusal(root, side) or _missing(entry)
    if refusal:
        return refusal
    hand, bone = bones(root, side)
    cmds.undoInfo(openChunk=True, chunkName="Inventory: into a hand")
    try:
        attach.detach(hand, bone)
        # the grip AFTER the old weapon is off: a bone that followed a weapon
        # on the floor stands on its own track only now (the mirror of the
        # right grip is read from the sockets). Nothing is remembered: the
        # inventory dials nothing, and a stored copy of the mirror would stop
        # the left hand following the right grip and each rig's own sockets
        # (2026-09-30 - the next rig got Manny's numbers).
        rotate, translate = grips.for_hand(entry, side, root)
        _weapon, note = attach.attach(entry, hand, bone, rotate, translate)
    finally:
        cmds.undoInfo(closeChunk=True)
    if getattr(entry, "texture", ""):
        colouring.show_textures()
    text = into_message(entry.label, root, side)
    return text + (" - " + note if note else "")


def to_floor(root, entry, point, heading, side=None):
    """`entry`'s weapon lying on the floor at `point`, `root`'s bone of
    `side` (the free one, right first, when None) following it."""
    if side is None:
        side = floor_side(dict((s, bool(occupant(root, s)[0]))
                               for s in catalog.SIDES))
    refusal = _refusal(root, side) or _missing(entry)
    if refusal:
        return refusal
    hand, bone = bones(root, side)
    cmds.undoInfo(openChunk=True, chunkName="Inventory: onto the floor")
    try:
        attach.detach(hand, bone)
        _weapon, note = floor.drop(entry, bone, point, heading)
    finally:
        cmds.undoInfo(closeChunk=True)
    if getattr(entry, "texture", ""):
        colouring.show_textures()
    text = floor_message(entry.label, root, side)
    return text + (" - " + note if note else "")


def _take_off(root, side):
    """(done, text) - `take_off`'s body, telling a refusal from a success."""
    weapon, _where = occupant(root, side)
    if not weapon:
        return False, "nothing in the %s" % SIDE_LABEL[side]
    label = connections.weapon_label(weapon)
    if connections.followers_of(weapon):
        return False, ("the hands ride the %s - release them in Connections "
                       "first" % label)
    hand, bone = bones(root, side)
    cmds.undoInfo(openChunk=True, chunkName="Inventory: take off")
    try:
        attach.detach(hand, bone)
    finally:
        cmds.undoInfo(closeChunk=True)
    return True, off_message(label, root, side)


def take_off(root, side):
    """The weapon `side`'s hand holds, or its bone follows, off - the bone
    gets its animation back."""
    return _take_off(root, side)[1]


def move(root, side, target):
    """The weapon of `side` taken off and the same weapon put at `target`:
    ("hand", root2, side2) or ("floor", root2, point, heading)."""
    weapon, _where = occupant(root, side)
    if not weapon:
        return "nothing in the %s" % SIDE_LABEL[side]
    entry = entry_of(weapon)
    if entry is None:
        return ("cannot tell which file %s came from - Weapons > Add it again"
                % weapon.split("|")[-1])
    #  Everything the target could refuse is asked BEFORE the weapon comes
    #  off: a refusal after it would leave the weapon gone.
    to_root = target[1]
    if target[0] == "hand":
        to_side = target[2]
        if to_root == root and to_side == side:
            return "the %s is already in the %s" % (entry.label,
                                                    SIDE_LABEL[side])
        refusal = _refusal(to_root, to_side)
    else:
        taken = dict((s, bool(occupant(to_root, s)[0])
                      and not (to_root == root and s == side))
                     for s in catalog.SIDES)
        to_side = floor_side(taken)
        refusal = ("" if to_root == root and to_side == side
                   else _refusal(to_root, to_side))
    refusal = refusal or _missing(entry)
    if refusal:
        return refusal
    cmds.undoInfo(openChunk=True, chunkName="Inventory: move")
    try:
        done, text = _take_off(root, side)
        if not done:
            return text
        if target[0] == "hand":
            return to_hand(to_root, to_side, entry)
        return to_floor(to_root, entry, target[2], target[3], to_side)
    finally:
        cmds.undoInfo(closeChunk=True)
