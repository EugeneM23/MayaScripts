"""Take the weapon out of the skeleton and let it drive the hands.

Connect turns the rig inside out. The weapon leaves `weapon_r` for world space
carrying its own baked animation, both arms end up in IK, and each IK hand
control is hung on the weapon -- so animating the weapon animates the arms,
and everything that was animated before still is.

Order is not cosmetic. The arms are brought to IK FIRST, so the weapon is
lifted off a hand motion that will not change afterwards. And "brought to IK"
is not "switched": `switch_limbs` converts to the OPPOSITE type, so calling it
on an arm that is already IK hands back an FK arm.

Only the end groups ride the weapon. The pole keeps answering to the body,
which is the ordinary prop workflow, and hanging the chain base on a prop pins
the shoulder to it.
"""

import maya.cmds as cmds

from maya_overrig import builder
from maya_overrig import fkcontrols
from maya_overrig import overrig

from maya_weapons import attach

ARMS = ("arm_l", "arm_r")


# ------------------------------------------------------------------ policy

def limbs_to_switch(state):
    """Which limbs need a switch to end up in IK. `state` is {limb: is_ik}."""
    return [limb for limb in ARMS if limb in state and not state[limb]]


def marked_ancestor(path, marked):
    """Nearest ancestor of `path` for which `marked(candidate)` is true.

    The node itself never counts -- a marked control would otherwise be read
    as its own carrier -- and ancestry is taken apart at the separator, so
    `|swordExtra` is not inside `|sword`.
    """
    parts = [part for part in path.split("|") if part]
    for depth in range(len(parts) - 1, 0, -1):
        candidate = "|" + "|".join(parts[:depth])
        if marked(candidate):
            return candidate
    return None


def connected_message(switched, hung):
    parts = []
    if switched:
        parts.append("switched " + ", ".join(switched) + " to IK")
    parts.append("{0} hand(s) on the weapon".format(len(hung)))
    return "Connected: " + ", ".join(parts)


def disconnected_message(lifted):
    return "Disconnected: {0} hand(s) back on the root control".format(
        len(lifted))


# ------------------------------------------------------------------- scene

def _is_carrier(path):
    return (cmds.objExists(path)
            and cmds.attributeQuery(attach.MARKER, node=path, exists=True))


def linked_carrier(limbs=ARMS):
    """The weapon the IK hands ride, or None.

    Asked exactly, never by scanning the scene for the marker: the linked
    weapon is the nearest marked ancestor of an IK hand control. Two
    characters holding the same sword stay apart with no extra bookkeeping.
    """
    for limb in limbs:
        node = builder.ik_control(limb, "end")
        if not node or not cmds.objExists(node):
            continue
        found = marked_ancestor(cmds.ls(node, long=True)[0], _is_carrier)
        if found:
            return found
    return None


def connect(carrier, scene_map):
    """Weapon out to world, both arms to IK, hands onto the weapon."""
    if not overrig.ensure_loaded():
        return overrig.NOT_LOADED_MESSAGE

    cmds.undoInfo(openChunk=True, chunkName="Connect arms to weapon")
    try:
        state = {limb: limb in builder.built_limbs() for limb in ARMS}
        switching = limbs_to_switch(state)
        if switching:
            fkcontrols.switch_limbs(scene_map, switching)

        carrier = cmds.ls(carrier, long=True)[0]
        if cmds.listRelatives(carrier, parent=True, fullPath=True):
            overrig.parent_out(carrier)
            # parent_out re-parents, so the recorded path is stale (trap 16).
            carrier = cmds.ls(carrier.split("|")[-1], long=True)[0]

        hung = [limb for limb in ARMS
                if fkcontrols.hang_ik_end_on(limb, carrier)]
        return connected_message(switching, hung)
    finally:
        cmds.undoInfo(closeChunk=True)


def disconnect(carrier, bone):
    """Hands back on the root control, weapon back in the bone.

    The weapon's animation is re-baked into the bone's space rather than
    thrown away: whatever the animator did with it out in the world survives
    the round trip.
    """
    if not overrig.ensure_loaded():
        return overrig.NOT_LOADED_MESSAGE

    cmds.undoInfo(openChunk=True, chunkName="Disconnect arms from weapon")
    try:
        lifted = []
        for limb in ARMS:
            if fkcontrols.lift_ik_end(limb):
                lifted.append(limb)
            fkcontrols.hang_ik_on_root(limb)

        carrier = cmds.ls(carrier, long=True)[0]
        if not cmds.listRelatives(carrier, parent=True, fullPath=True):
            overrig.parent_in(carrier, bone)
        return disconnected_message(lifted)
    finally:
        cmds.undoInfo(closeChunk=True)
