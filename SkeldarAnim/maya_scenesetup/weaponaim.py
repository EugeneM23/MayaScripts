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

import maya.api.OpenMaya as om
import maya.cmds as cmds

import maya_rigs
import maya_timewarp
from maya_scenesetup import aim as aimplace
from maya_scenesetup import fkik

MARKER = "skeldarWeaponAim"          # on the group: the weapon's UUID
CTRL_MARKER = "skeldarWeaponAimCtrl"  # on a controller: "target" | "up"
CON_MARKER = "skeldarWeaponAimOf"     # on our aimConstraint: the weapon's UUID
VECTORS = "skeldarWeaponAimVectors"   # on the group: aim and up vectors, the distance (JSON-free)
GROUP_NAME = "{0}_aim"
TARGET_NAME = "{0}_aimTarget"
UP_NAME = "{0}_aimUp"
TARGET_COLOUR = (1.0, 0.45, 0.12)
UP_COLOUR = (0.25, 0.75, 1.0)
ROTATE = fkik.ROTATE
TRANSLATE = fkik.TRANSLATE
LOCKED = ("rotateX", "rotateY", "rotateZ", "scaleX", "scaleY", "scaleZ")
# the up beside the weapon (2026-10-21, after using it: «AIm up должен быть с другой стороны
# оружия и не так далеко от него»): on the other side of the next longest axis. 2026-10-23 «другий
# контрол який ближче до рукоятки дуже часто приводить до крашу ... давай його розмістимо далі від
# предмету і по центру леза»: beside the grip, a quarter out, a small drag put it on the blade's line
# and the aimConstraint's up degenerate; now opposite the blade's middle (UP_ALONG of the tip's
# distance), half the target's distance out
UP_SHARE = 0.5
UP_ALONG = 0.5
LINE_MARKER = "skeldarWeaponAimLine"  # on a line from the weapon to a controller: its role
# Default keys the rotation on the keys, then on every frame between them that still turns more than
# this off the aim (2026-10-26: a fast swing between two keys came out 27 degrees off)
TOLERANCE = 0.1         # degrees
FILL_PASSES = 4         # a key added re-shapes its neighbours' auto tangents: checked again

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


def up_axis(aim_v, up_v):
    """The weapon's own axis the aimConstraint turns toward the up controller: `up_v` without its
    part along the blade (the controller stands opposite the blade's middle, not beside the grip),
    so the weapon stands as it stood. Pure."""
    dot = sum(a * u for a, u in zip(aim_v, up_v))
    perp = [u - dot * a for a, u in zip(aim_v, up_v)]
    n = math.sqrt(sum(v * v for v in perp))
    return tuple(v / n for v in perp) if n > 1e-9 else tuple(up_v)


def point_of(matrix, direction, distance):
    """The world point `direction · distance` in the frame of the row-vector `matrix`."""
    p = om.MPoint(*[v * distance for v in direction]) * om.MMatrix(matrix)
    return (p.x, p.y, p.z)


def diamond(r):
    """A three-ring diamond (an octahedron's edges), degree 1."""
    return [(r, 0, 0), (0, r, 0), (-r, 0, 0), (0, -r, 0), (r, 0, 0), (0, 0, r), (-r, 0, 0),
            (0, 0, -r), (r, 0, 0), (0, r, 0), (0, 0, r), (0, -r, 0), (0, 0, -r), (0, r, 0)]


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


def turn_between(a, b, order=0):
    """Degrees between two rotations given as Euler angles (degrees) in rotate order `order`, however
    each is written (173 and -187 are one turn)."""
    qa = om.MEulerRotation(*([math.radians(v) for v in a] + [int(order)])).asQuaternion()
    qb = om.MEulerRotation(*([math.radians(v) for v in b] + [int(order)])).asQuaternion()
    dot = abs(qa.x * qb.x + qa.y * qb.y + qa.z * qb.z + qa.w * qb.w)
    return math.degrees(2.0 * math.acos(min(1.0, dot)))


def frames_off(aimed, baked, tolerance=TOLERANCE, order=0):
    """The frames of `baked` ({frame: euler}) turned more than `tolerance` off `aimed`, in order."""
    return sorted(f for f, rotate in baked.items()
                  if f in aimed and turn_between(aimed[f], rotate, order) > tolerance)


def broken(made, constraint):
    """An aim group whose controllers ({role: path}) or constraint are gone (2026-10-27, «Aim не
    працює»: in a tab the dagger was keyed in Aim Mode, then its controllers and constraint deleted -
    the empty group left made Aim Mode refuse and Default bake nothing). Pure."""
    return not constraint or "target" not in made or "up" not in made


# ------------------------------------------------------------------- scene

def _long(node):
    found = cmds.ls(node, long=True) if node else None
    return found[0] if found else None


def _uuid(node):
    found = cmds.ls(node, uuid=True) if node else None
    return found[0] if found else None


def _leaf(path):
    return (path or "").split("|")[-1].split(":")[-1]


def groups():
    """Every aim group in the scene (long paths); none where the scene cannot be asked (a fake
    `cmds` in a test of another module)."""
    try:
        found = cmds.ls("*." + MARKER, recursive=True, objectsOnly=True, long=True,
                        type="transform") or []
    except (AttributeError, RuntimeError, TypeError):
        return []
    return list(dict.fromkeys(found))


def group_of(weapon):
    """The aim group of `weapon`, or None."""
    found = groups()
    if not found:
        return None
    uuid = _uuid(weapon)
    if not uuid:
        return None
    for group in found:
        try:
            if cmds.getAttr(group + "." + MARKER) == uuid:
                return group
        except (RuntimeError, ValueError):
            continue
    return None


def is_aimed(weapon):
    group = group_of(weapon)
    return group is not None and not broken(controllers(group), _constraint(weapon))


def _clear_broken(weapon, group):
    """What is left of a broken Aim Mode on `weapon` deleted: our constraint, the group."""
    con = _constraint(weapon)
    if con:
        cmds.delete(con)
    _drop_lines(group)
    if cmds.objExists(group):
        cmds.delete(group)


def controllers(group):
    """{"target": path, "up": path} under an aim group."""
    out = {}
    for child in cmds.listRelatives(group, children=True, fullPath=True, type="transform") or []:
        if cmds.attributeQuery(CTRL_MARKER, node=child, exists=True):
            out[cmds.getAttr(child + "." + CTRL_MARKER)] = child
    return out


def is_controller(node):
    try:
        return bool(cmds.attributeQuery(CTRL_MARKER, node=node, exists=True))
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return False


def weapon_of_group(group):
    uuid = cmds.getAttr(group + "." + MARKER)
    return _long(uuid)


def stored_vectors(group):
    """(aim vector, up vector, aim distance, up distance) kept on the group."""
    values = [float(v) for v in cmds.getAttr(group + "." + VECTORS).split()]
    return tuple(values[0:3]), tuple(values[3:6]), values[6], values[7]


def _constraint(weapon):
    for con in cmds.listRelatives(weapon, children=True, fullPath=True,
                                  type="aimConstraint") or []:
        if cmds.attributeQuery(CON_MARKER, node=con, exists=True):
            return con
    return None


def refusal(weapon):
    """'' or why `weapon` cannot go into Aim Mode."""
    if not weapon or not cmds.objExists(weapon):
        return NO_WEAPON
    label = _leaf(weapon)
    if is_aimed(weapon):
        return ALREADY % label
    for ch in ROTATE:
        plug = weapon + "." + ch
        if cmds.getAttr(plug, lock=True):
            return "%s.%s is locked" % (label, ch)
        if fkik._layered(plug):
            return "%s.%s is on animation layers - bake its layers first" % (label, ch)
        driver = fkik._foreign(plug)
        if driver:
            return "%s.%s is driven by %s" % (label, ch, driver)
    return ""


def _span():
    start = cmds.playbackOptions(query=True, min=True)
    end = cmds.playbackOptions(query=True, max=True)
    return (int(math.floor(start)), int(math.ceil(end)), False)


def _walk(frames, read):
    """{frame: read()} over the frames, the time put back."""
    now = cmds.currentTime(query=True)
    out = {}
    try:
        for frame in frames:
            fkik._goto(frame)
            out[frame] = read()
    finally:
        fkik._goto(now)
    return out


def _world(node):
    return om.MMatrix(cmds.getAttr(node + ".worldMatrix[0]"))


def _control(name, parent, points, colour):
    """A curve control: a transform under `parent` with one degree-1 curve through `points`,
    coloured through the shape's RGB override, 2 px wide. Its long path."""
    temp = cmds.curve(degree=1, point=list(points))
    uuid = _uuid(temp)
    cmds.parent(temp, parent, relative=True)
    node = cmds.rename(_long(uuid), name.split(":")[-1])
    node = _long(uuid)
    shape = cmds.listRelatives(node, shapes=True, fullPath=True)[0]
    cmds.rename(shape, _leaf(node) + "Shape")
    shape = cmds.listRelatives(node, shapes=True, fullPath=True)[0]
    cmds.setAttr(shape + ".overrideEnabled", 1)
    cmds.setAttr(shape + ".overrideRGBColors", 1)
    cmds.setAttr(shape + ".overrideColorRGB", *colour)
    try:
        cmds.setAttr(shape + ".lineWidth", 2.0)
    except Exception:                                        # noqa: BLE001 - an older Maya
        pass
    return node


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


def _make_controls(weapon, group_parent, size_target, size_up):
    """The aim group and its two controllers (world space) for `weapon`."""
    label = _leaf(weapon)
    group = cmds.createNode("transform", name=GROUP_NAME.format(label), skipSelect=True)
    uuid = _uuid(group)
    if group_parent:
        cmds.parent(group, group_parent, relative=True)
    group = _long(uuid)
    cmds.addAttr(group, longName=MARKER, dataType="string")
    cmds.setAttr(group + "." + MARKER, _uuid(weapon), type="string")
    cmds.addAttr(group, longName=VECTORS, dataType="string")
    made = {}
    for role, name, points, colour in (
            ("target", TARGET_NAME, diamond(size_target), TARGET_COLOUR),
            ("up", UP_NAME, diamond(size_up), UP_COLOUR)):
        ctrl = _control(name.format(label), group, points, colour)
        cmds.addAttr(ctrl, longName=CTRL_MARKER, dataType="string")
        cmds.setAttr(ctrl + "." + CTRL_MARKER, role, type="string")
        for attr in LOCKED:
            cmds.setAttr(ctrl + "." + attr, lock=True, keyable=False, channelBox=False)
        made[role] = _uuid(ctrl)
    return _long(uuid), dict((r, _long(u)) for r, u in made.items())


WORLD = "world"          # home_of's answer for the world level


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


def _put(group, home):
    """`group` under `home` (WORLD: the world level; None: where it stands), relative. Its path."""
    if not home:
        return group
    uuid = _uuid(group)
    parents = cmds.listRelatives(group, parent=True, fullPath=True) or []
    if home == WORLD:
        if parents:
            cmds.parent(group, world=True, relative=True)
    elif not parents or parents[0] != home:
        cmds.parent(group, home, relative=True)
    return _long(uuid)


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


def _local(point, spaces, frame):
    """A world point in the group's space at `frame` (the group stands at identity under Main,
    whose world `spaces` holds per frame); as it is without one."""
    if not spaces:
        return point
    p = om.MPoint(*point) * spaces[frame].inverse()
    return (p.x, p.y, p.z)


def _write_series(node, frames, points, span, tangents):
    for axis, ch in enumerate(TRANSLATE):
        plug = node + "." + ch
        fkik._write(plug, frames, [p[axis] for p in points], span, False, tangents)


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
    aim_v, up_v, d_aim, d_up = vec
    span = _span()
    weapon_uuid = _uuid(weapon)
    auto = cmds.autoKeyframe(query=True, state=True)
    cmds.undoInfo(openChunk=True, chunkName="Connections: Aim Mode")
    try:
        cmds.autoKeyframe(state=False)
        stale = group_of(weapon)
        if stale:
            _clear_broken(weapon, stale)
        with maya_timewarp.unwarped():
            sample, keys, tangents = fkik.own_keys([weapon], [], span)
            fkik._suspend(True)
            try:
                home = home_of(_long(weapon_uuid))
                worlds = _walk(sample, lambda: _world(_long(weapon_uuid)))
                spaces = (_walk(sample, lambda: _world(home)) if home and home != WORLD
                          else None)
            finally:
                fkik._suspend(False)
            size = max(d_aim, d_up) * 0.06
            group, made = _make_controls(weapon, None, size, size * 0.8)
            cmds.setAttr(group + "." + VECTORS, " ".join(
                "%.12g" % v for v in tuple(aim_v) + tuple(up_v) + (d_aim, d_up)), type="string")
            group = _park(group, weapon)
            made = controllers(group)
            frames = list(sample)
            if keys:
                targets = [_local(point_of(worlds[f], aim_v, d_aim), spaces, f) for f in frames]
                ups = [_local(point_of(worlds[f], up_v, d_up), spaces, f) for f in frames]
                _write_series(made["target"], frames, targets, span, tangents)
                _write_series(made["up"], frames, ups, span, tangents)
            else:
                now = frames[0]
                for role, direction, distance in (("target", aim_v, d_aim), ("up", up_v, d_up)):
                    cmds.xform(made[role], worldSpace=True,
                               translation=point_of(worlds[now], direction, distance))
            weapon = _long(weapon_uuid)
            for ch in ROTATE:
                cmds.cutKey(weapon + "." + ch, clear=True)
            con = cmds.aimConstraint(made["target"], weapon, maintainOffset=False,
                                     aimVector=aim_v, upVector=up_axis(aim_v, up_v), worldUpType="object",
                                     worldUpObject=made["up"])[0]
            cmds.addAttr(con, longName=CON_MARKER, dataType="string")
            cmds.setAttr(con + "." + CON_MARKER, weapon_uuid, type="string")
            #  a rig in 1P (Tools > 1P Setup, 2026-10-21): the controllers ride its chest
            in_1p = _into_1p(_long(weapon_uuid))
    finally:
        cmds.autoKeyframe(state=auto)
        cmds.undoInfo(closeChunk=True)
    line = entered_message(label, keys)
    return line + (" | " + in_1p if in_1p else "")


def _into_1p(weapon):
    try:
        from maya_tools import firstperson
    except ImportError:
        return ""
    return firstperson.aim_into_chest(weapon)


def _fill_between(weapon, aimed, keyed, order):
    """Keys added on the frames between the keys where the baked rotation turns off the aim
    (`aimed` {frame: euler} on every frame), until none does. How many."""
    added = 0
    for _ in range(FILL_PASSES):
        baked = dict((f, [cmds.getAttr(weapon + "." + ch, time=f) for ch in ROTATE])
                     for f in aimed if f not in keyed)
        missed = frames_off(aimed, baked, TOLERANCE, order)
        if not missed:
            break
        for f in missed:
            for axis, ch in enumerate(ROTATE):
                cmds.setKeyframe(weapon, attribute=ch, time=f, value=aimed[f][axis])
            keyed.add(f)
        added += len(missed)
    return added


def leave(weapon):
    """Default on `weapon`: its rotation keyed back on the keys of the controllers and of its
    translate, then on every frame between them the keys alone would miss (`_fill_between`), the
    controllers and the constraint deleted. The status line."""
    weapon = _long(weapon)
    if not weapon:
        return NO_WEAPON
    label = _leaf(weapon)
    group = group_of(weapon)
    if group is None:
        return NOT_AIMED % label
    made = controllers(group)
    if broken(made, _constraint(weapon)):
        cmds.undoInfo(openChunk=True, chunkName="Connections: Default")
        try:
            _clear_broken(weapon, group)
        finally:
            cmds.undoInfo(closeChunk=True)
        return CLEARED % label
    from maya_poselib import helpers
    span = _span()
    weapon_uuid = _uuid(weapon)
    auto = cmds.autoKeyframe(query=True, state=True)
    cmds.undoInfo(openChunk=True, chunkName="Connections: Default")
    try:
        cmds.autoKeyframe(state=False)
        with maya_timewarp.unwarped():
            nodes = [n for n in (made.get("target"), made.get("up"), weapon) if n]
            sample, keys, tangents = fkik.own_keys(nodes, [], span)
            attrs = helpers._attrs(weapon)

            def read():
                w = _long(weapon_uuid)
                return _world(w) * om.MMatrix(cmds.getAttr(w + ".parentInverseMatrix[0]"))

            every = list(range(span[0], span[1] + 1)) if keys else []
            fkik._suspend(True)
            try:
                locals_ = _walk(sorted(set(sample) | set(every)), read)
            finally:
                fkik._suspend(False)
            frames = list(sample)
            #  one Euler path through every frame in time order: the keys and the frames between
            #  them on the same turn (no 360 between neighbours)
            previous = [cmds.getAttr(weapon + "." + ch) for ch in ROTATE]
            aimed = {}
            for f in sorted(locals_):
                rotate, _t = helpers.driver_channels(locals_[f], attrs, previous)
                aimed[f] = list(rotate)
                previous = list(rotate)
            values = [aimed[f] for f in frames]
            con = _constraint(weapon)
            if con:
                cmds.delete(con)
            _drop_lines(group)
            cmds.delete(group)
            weapon = _long(weapon_uuid)
            for axis, ch in enumerate(ROTATE):
                plug = weapon + "." + ch
                if keys:
                    fkik._write(plug, frames, [v[axis] for v in values], span, False, tangents)
                else:
                    cmds.setAttr(plug, values[0][axis])
            added = 0
            if keys:
                added = _fill_between(weapon, dict((f, aimed[f]) for f in every), set(frames),
                                      int(attrs.get("rotateOrder", 0)))
    finally:
        cmds.autoKeyframe(state=auto)
        cmds.undoInfo(closeChunk=True)
    line = left_message(label, keys)
    return line + (" + %d between them where the aim turned faster" % added if added else "")

