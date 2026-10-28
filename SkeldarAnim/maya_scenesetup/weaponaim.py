"""Aim Mode for a weapon (2026-10-21): the weapon's rotation aims at two world controllers.

The animator: «когда мы нажимаем aim у нас должна отработать логика aim из раздела tools только
вместо локаторов мы должны создавать контроллеры. Запекание ключей на эти контроллеры и обратно на
наше оружие нужно сделать умным по ключам а не весь таймлайн сразу ... Делаем 2 кнопки Aim Mode и
Default». Asked: the controllers stand in the WORLD, the aim drives the rotation only.

- `enter` (Aim Mode): a target past the blade's tip and an up on the next longest axis
  (`aim.placement`, the model's own extents), keyed in world on the weapon's OWN key frames
  (`fkik.own_keys`, the FK/IK switch's rule) with their tangents; the weapon's rotate keys cut and
  an `aimConstraint` (no offset) put on. On every keyed frame the weapon stands where it stood.
- `leave` (Default): the weapon's local rotation read on the keys of the controllers and of its
  translate, the controllers and the constraint deleted, the rotate keyed.

The controllers live in a group `<weapon>_aim` marked `MARKER` (the weapon's UUID) in the
character's group. Spec: docs/superpowers/specs/2026-10-21-connections-weapon-aim-design.md
"""

import math

import maya.cmds as cmds

import maya_rigs
from maya_scenesetup import aim as aimplace
from maya_scenesetup import aimcore
from maya_scenesetup.aimcore import (broken, diamond, frames_off, point_of, turn_between,  # noqa: F401
                                     up_axis, TOLERANCE, FILL_PASSES, ROTATE, TRANSLATE, LOCKED,
                                     TARGET_COLOUR, UP_COLOUR)

MARKER = "skeldarWeaponAim"          # on the group: the weapon's UUID
CTRL_MARKER = "skeldarWeaponAimCtrl"  # on a controller: "target" | "up"
CON_MARKER = "skeldarWeaponAimOf"     # on our aimConstraint: the weapon's UUID
VECTORS = "skeldarWeaponAimVectors"   # on the group: aim and up vectors, the distance (JSON-free)
GROUP_NAME = "{0}_aim"
TARGET_NAME = "{0}_aimTarget"
UP_NAME = "{0}_aimUp"
# the up beside the weapon (2026-10-21, after using it: «AIm up должен быть с другой стороны
# оружия и не так далеко от него»): on the other side of the next longest axis. 2026-10-23 «другий
# контрол який ближче до рукоятки дуже часто приводить до крашу ... давай його розмістимо далі від
# предмету і по центру леза»: beside the grip, a quarter out, a small drag put it on the blade's line
# and the aimConstraint's up degenerate; now opposite the blade's middle (UP_ALONG of the tip's
# distance), half the target's distance out
UP_SHARE = 0.5
UP_ALONG = 0.5
LINE_MARKER = "skeldarWeaponAimLine"  # on a line from the weapon to a controller: its role

NO_WEAPON = "no weapon in the scene - Inventory > Equip first"
ALREADY = "%s is in Aim Mode already - Default first"
NOT_AIMED = "%s is not in Aim Mode"
CLEARED = "%s: its Aim Mode was broken (the controllers or the constraint deleted) - cleared, the rotation left as it is"
NO_GEOMETRY = "%s has no geometry to measure - cannot place the aim"


# ------------------------------------------------------------------- pure

def vectors(lo, hi):
    """(aim vector, up vector, aim distance, up distance) in the weapon's own frame from its
    extents, or None (nothing to aim): the directions and distances of the two controllers from
    the weapon's pivot. The aim along the blade to past its tip (`aim.placement`); the up opposite
    the blade's middle, on the OTHER side of the next longest axis, `UP_SHARE` of that distance
    out. The constraint's up axis is `up_axis` of the two."""
    placed = aimplace.placement(lo, hi)
    if placed is None:
        return None
    top, side = placed
    d_top = math.sqrt(sum(v * v for v in top))
    d_side = math.sqrt(sum(v * v for v in side))
    if d_top <= 0 or d_side <= 0:
        return None
    aim_v = tuple(v / d_top for v in top)
    along = d_top / (1.0 + aimplace.MARGIN) * UP_ALONG
    point = [a * along - s / d_side * d_top * UP_SHARE for a, s in zip(aim_v, side)]
    d_up = math.sqrt(sum(v * v for v in point))
    return aim_v, tuple(v / d_up for v in point), d_top, d_up


def square(half):
    """A closed square of half side `half` on X and Z, degree 1."""
    return [(-half, 0, -half), (half, 0, -half), (half, 0, half), (-half, 0, half),
            (-half, 0, -half)]


def entered_message(label, keys):
    if not keys:
        return ("%s in Aim Mode - it has no keys of its own: the controllers set at the current "
                "frame" % label)
    return ("%s in Aim Mode on %d key%s (%g..%g) - animate %s_aimTarget / _aimUp"
            % (label, len(keys), "" if len(keys) == 1 else "s", keys[0], keys[-1], label))


def left_message(label, keys):
    if not keys:
        return "%s back to Default - no keys: its rotation set at the current frame" % label
    return "%s back to Default on %d key%s (%g..%g)" % (
        label, len(keys), "" if len(keys) == 1 else "s", keys[0], keys[-1])


def _drop_lines(group):
    """A group made by 45012f1..2026-10-21 holds two lines (gone since: «векторы ... не нужны»):
    their decomposeMatrix nodes deleted (the group takes the lines themselves)."""
    for child in cmds.listRelatives(group, children=True, fullPath=True, type="transform") or []:
        if not cmds.attributeQuery(LINE_MARKER, node=child, exists=True):
            continue
        for shape in cmds.listRelatives(child, shapes=True, fullPath=True) or []:
            for node in cmds.listConnections(shape, source=True, destination=False,
                                             type="decomposeMatrix") or []:
                if cmds.objExists(node):
                    cmds.delete(node)




def home_of(weapon, chest=True):
    """Where the weapon's aim group lives (2026-10-21): it repeats the weapon's parent (the
    animator: «если мы делаем перенос оружия в world в нашем connection то и контроллеры aim mode
    тоже должны быть в world они всегда должны повторять парент оружия»).
    - out of the hands (Connections' World, the floor): the weapon's own parent - its character
      group, the 1P chest - or WORLD;
    - in a hand: the rig's Main («в паранте главного контрола если мы не в 1P моде»), its 1P
      chest when it has one and `chest`; a hand of no rig: the weapon's character group.
    The rig is found from the weapon or from the hand holding it."""
    try:
        from maya_scenesetup import weaponspace
        hand = weaponspace.holding_hand(weapon)
        if not hand:
            parents = cmds.listRelatives(weapon, parent=True, fullPath=True) or []
            return parents[0] if parents else WORLD
        rigs = maya_rigs.rigs()
        for node in (weapon, hand):
            rig = maya_rigs.rig_of(node, rigs) if node else None
            if rig is not None and rig.main and cmds.objExists(rig.main):
                if chest:
                    from maya_tools import firstperson
                    found = firstperson.chest_of(rig)
                    if found:
                        return found
                return _long(rig.main)
    except Exception:                                        # noqa: BLE001 - a bare skeleton
        pass
    return None


def _park(group, weapon):
    try:
        from maya_scenesetup import chargroup
        rig = maya_rigs.rig_of(weapon, maya_rigs.rigs())
        owner = rig if rig is not None else weapon
        group = chargroup.park(group, owner) or group
        return _put(group, home_of(weapon))
    except Exception:                                        # noqa: BLE001 - legacy: stays
        return group


def rehome(weapon):
    """The weapon's aim group moved where `home_of` says, its controllers' world motion kept
    (`firstperson.carry_into`). The words, "" when it stands there already or there is none."""
    group = group_of(weapon)
    if not group:
        return ""
    home = home_of(weapon)
    parents = cmds.listRelatives(group, parent=True, fullPath=True) or []
    here = parents[0] if parents else WORLD
    if not home or here == home:
        return ""
    from maya_tools import firstperson
    uuid = _uuid(group)
    firstperson.carry_into(list(controllers(group).values()), None if home == WORLD else home,
                           lambda: _put(_long(uuid), home))
    return "the aim follows %s" % ("the world" if home == WORLD else _leaf(home))


def _into_1p(weapon):
    try:
        from maya_tools import firstperson
    except ImportError:
        return ""
    return firstperson.aim_into_chest(weapon)



KIND = aimcore.AimKind(MARKER, CTRL_MARKER, CON_MARKER, VECTORS, GROUP_NAME, TARGET_NAME, UP_NAME,
                       "Connections: Aim Mode", "Connections: Default")
WORLD = aimcore.WORLD          # home_of's answer for the world level
_long, _uuid, _leaf, _put = aimcore.long_, aimcore.uuid, aimcore.leaf, aimcore.put


def groups():
    """Every aim group in the scene (long paths)."""
    return aimcore.groups(KIND)


def group_of(weapon):
    """The aim group of `weapon`, or None."""
    return aimcore.group_of(weapon, KIND)


def is_aimed(weapon):
    return aimcore.is_aimed(weapon, KIND)


def controllers(group):
    """{"target": path, "up": path} under an aim group."""
    return aimcore.controllers(group, KIND)


def is_controller(node):
    return aimcore.is_controller(node, KIND)


def weapon_of_group(group):
    return aimcore.owner_of_group(group, KIND)


def stored_vectors(group):
    """(aim vector, up vector, aim distance, up distance) kept on the group."""
    return aimcore.stored_vectors(group, KIND)


def _constraint(weapon):
    return aimcore.constraint(weapon, KIND)


def refusal(weapon):
    """'' or why `weapon` cannot go into Aim Mode."""
    if not weapon or not cmds.objExists(weapon):
        return NO_WEAPON
    if is_aimed(weapon):
        return ALREADY % _leaf(weapon)
    return aimcore.rotate_refusal(weapon)


def enter(weapon):
    """Aim Mode on `weapon` (refusals first; nothing changed on one). The status line."""
    why = refusal(weapon)
    if why:
        return why
    weapon = _long(weapon)
    label = _leaf(weapon)
    extents = aimplace.local_extents(weapon)
    vec = vectors(*extents) if extents else None
    if vec is None:
        return NO_GEOMETRY % label
    auto = cmds.autoKeyframe(query=True, state=True)
    cmds.undoInfo(openChunk=True, chunkName=KIND.enter_chunk)
    try:
        cmds.autoKeyframe(state=False)
        keys, weapon = aimcore.aim_on(weapon, KIND, vec, home_of, _park)
        #  a rig in 1P (Tools > 1P Setup, 2026-10-21): the controllers ride its chest
        in_1p = _into_1p(weapon)
    finally:
        cmds.autoKeyframe(state=auto)
        cmds.undoInfo(closeChunk=True)
    line = entered_message(label, keys)
    return line + (" | " + in_1p if in_1p else "")


def leave(weapon):
    """Default on `weapon` (`aimcore.aim_off`). The status line."""
    weapon = _long(weapon)
    if not weapon:
        return NO_WEAPON
    label = _leaf(weapon)
    group = group_of(weapon)
    if group is None:
        return NOT_AIMED % label
    made = controllers(group)
    auto = cmds.autoKeyframe(query=True, state=True)
    cmds.undoInfo(openChunk=True, chunkName=KIND.leave_chunk)
    try:
        cmds.autoKeyframe(state=False)
        if broken(made, _constraint(weapon)):
            aimcore.clear_broken(weapon, KIND, group, _drop_lines)
            return CLEARED % label
        keys, added = aimcore.aim_off(weapon, KIND, group, made, _drop_lines)
    finally:
        cmds.autoKeyframe(state=auto)
        cmds.undoInfo(closeChunk=True)
    line = left_message(label, keys)
    return line + (" + %d between them where the aim turned faster" % added if added else "")
