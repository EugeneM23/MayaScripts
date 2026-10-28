"""The aim engine (2026-10-28): a node's rotation aims at two controllers keyed on its own keys
(Aim Mode), and back (Default). Lifted out of `weaponaim` when the camera got the same Aim Mode
(the animator: «такой же aim как для оружия») - an `AimKind` names a user's markers and words.

Spec: docs/superpowers/specs/2026-10-28-connections-camera-tab-design.md
"""

import math
from collections import namedtuple

import maya.api.OpenMaya as om
import maya.cmds as cmds

import maya_timewarp
from maya_scenesetup import fkik

AimKind = namedtuple("AimKind", "marker ctrl_marker con_marker vectors_attr group_name "
                                "target_name up_name enter_chunk leave_chunk")

WORLD = "world"
ROTATE = fkik.ROTATE
TRANSLATE = fkik.TRANSLATE
LOCKED = ("rotateX", "rotateY", "rotateZ", "scaleX", "scaleY", "scaleZ")
TARGET_COLOUR = (1.0, 0.45, 0.12)
UP_COLOUR = (0.25, 0.75, 1.0)
# Default keys the rotation on the keys, then on every frame between them that still turns more than
# this off the aim (2026-10-26: a fast swing between two keys came out 27 degrees off)
TOLERANCE = 0.1         # degrees
FILL_PASSES = 4         # a key added re-shapes its neighbours' auto tangents: checked again


# ------------------------------------------------------------------- pure

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

def long_(node):
    found = cmds.ls(node, long=True) if node else None
    return found[0] if found else None


def uuid(node):
    found = cmds.ls(node, uuid=True) if node else None
    return found[0] if found else None


def leaf(path):
    return (path or "").split("|")[-1].split(":")[-1]


def groups(kind):
    """Every aim group of `kind` in the scene (long paths); none where the scene cannot be asked (a
    fake `cmds` in a test of another module)."""
    try:
        found = cmds.ls("*." + kind.marker, recursive=True, objectsOnly=True, long=True,
                        type="transform") or []
    except (AttributeError, RuntimeError, TypeError):
        return []
    return list(dict.fromkeys(found))


def group_of(node, kind):
    """The aim group of `node`, or None."""
    found = groups(kind)
    if not found:
        return None
    key = uuid(node)
    if not key:
        return None
    for group in found:
        try:
            if cmds.getAttr(group + "." + kind.marker) == key:
                return group
        except (RuntimeError, ValueError):
            continue
    return None


def controllers(group, kind):
    """{"target": path, "up": path} under an aim group."""
    out = {}
    for child in cmds.listRelatives(group, children=True, fullPath=True, type="transform") or []:
        if cmds.attributeQuery(kind.ctrl_marker, node=child, exists=True):
            out[cmds.getAttr(child + "." + kind.ctrl_marker)] = child
    return out


def is_controller(node, kind):
    try:
        return bool(cmds.attributeQuery(kind.ctrl_marker, node=node, exists=True))
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return False


def owner_of_group(group, kind):
    return long_(cmds.getAttr(group + "." + kind.marker))


def stored_vectors(group, kind):
    """(aim vector, up vector, aim distance, up distance) kept on the group."""
    values = [float(v) for v in cmds.getAttr(group + "." + kind.vectors_attr).split()]
    return tuple(values[0:3]), tuple(values[3:6]), values[6], values[7]


def constraint(node, kind):
    for con in cmds.listRelatives(node, children=True, fullPath=True,
                                  type="aimConstraint") or []:
        if cmds.attributeQuery(kind.con_marker, node=con, exists=True):
            return con
    return None


def is_aimed(node, kind):
    group = group_of(node, kind)
    return group is not None and not broken(controllers(group, kind), constraint(node, kind))


def rotate_refusal(node):
    """'' or why the rotate of `node` cannot be aimed: locked, layered or driven."""
    label = leaf(node)
    for ch in ROTATE:
        plug = node + "." + ch
        if cmds.getAttr(plug, lock=True):
            return "%s.%s is locked" % (label, ch)
        if fkik._layered(plug):
            return "%s.%s is on animation layers - bake its layers first" % (label, ch)
        driver = fkik._foreign(plug)
        if driver:
            return "%s.%s is driven by %s" % (label, ch, driver)
    return ""


def span():
    start = cmds.playbackOptions(query=True, min=True)
    end = cmds.playbackOptions(query=True, max=True)
    return (int(math.floor(start)), int(math.ceil(end)), False)


def walk(frames, read):
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


def world(node):
    return om.MMatrix(cmds.getAttr(node + ".worldMatrix[0]"))


def control(name, parent, points, colour):
    """A curve control: a transform under `parent` with one degree-1 curve through `points`,
    coloured through the shape's RGB override, 2 px wide. Its long path."""
    temp = cmds.curve(degree=1, point=list(points))
    key = uuid(temp)
    cmds.parent(temp, parent, relative=True)
    node = cmds.rename(long_(key), name.split(":")[-1])
    node = long_(key)
    shape = cmds.listRelatives(node, shapes=True, fullPath=True)[0]
    cmds.rename(shape, leaf(node) + "Shape")
    shape = cmds.listRelatives(node, shapes=True, fullPath=True)[0]
    cmds.setAttr(shape + ".overrideEnabled", 1)
    cmds.setAttr(shape + ".overrideRGBColors", 1)
    cmds.setAttr(shape + ".overrideColorRGB", *colour)
    try:
        cmds.setAttr(shape + ".lineWidth", 2.0)
    except Exception:                                        # noqa: BLE001 - an older Maya
        pass
    return node


def clear_broken(node, kind, group, cleanup=None):
    """What is left of a broken Aim Mode on `node` deleted: our constraint, the group."""
    con = constraint(node, kind)
    if con:
        cmds.delete(con)
    if cleanup:
        cleanup(group)
    if cmds.objExists(group):
        cmds.delete(group)


def make_controls(node, kind, size_target, size_up):
    """The aim group and its two controllers (world space) for `node`, with `kind`'s names and
    markers; (group, {role: path})."""
    label = leaf(node)
    group = cmds.createNode("transform", name=kind.group_name.format(label), skipSelect=True)
    key = uuid(group)
    group = long_(key)
    cmds.addAttr(group, longName=kind.marker, dataType="string")
    cmds.setAttr(group + "." + kind.marker, uuid(node), type="string")
    cmds.addAttr(group, longName=kind.vectors_attr, dataType="string")
    made = {}
    for role, name, points, colour in (
            ("target", kind.target_name, diamond(size_target), TARGET_COLOUR),
            ("up", kind.up_name, diamond(size_up), UP_COLOUR)):
        ctrl = control(name.format(label), group, points, colour)
        cmds.addAttr(ctrl, longName=kind.ctrl_marker, dataType="string")
        cmds.setAttr(ctrl + "." + kind.ctrl_marker, role, type="string")
        for attr in LOCKED:
            cmds.setAttr(ctrl + "." + attr, lock=True, keyable=False, channelBox=False)
        made[role] = uuid(ctrl)
    return long_(key), dict((r, long_(u)) for r, u in made.items())


def put(group, home):
    """`group` under `home` (WORLD: the world level; None: where it stands), relative. Its path."""
    if not home:
        return group
    key = uuid(group)
    parents = cmds.listRelatives(group, parent=True, fullPath=True) or []
    if home == WORLD:
        if parents:
            cmds.parent(group, world=True, relative=True)
    elif not parents or parents[0] != home:
        cmds.parent(group, home, relative=True)
    return long_(key)


def local(point, spaces, frame):
    """A world point in the group's space at `frame` (the group stands at identity under Main,
    whose world `spaces` holds per frame); as it is without one."""
    if not spaces:
        return point
    p = om.MPoint(*point) * spaces[frame].inverse()
    return (p.x, p.y, p.z)


def write_series(node, frames, points, window, tangents):
    for axis, ch in enumerate(TRANSLATE):
        plug = node + "." + ch
        fkik._write(plug, frames, [p[axis] for p in points], window, False, tangents)


def fill_between(node, aimed, keyed, order):
    """Keys added on the frames between the keys where the baked rotation turns off the aim
    (`aimed` {frame: euler} on every frame), until none does. How many."""
    added = 0
    for _ in range(FILL_PASSES):
        baked = dict((f, [cmds.getAttr(node + "." + ch, time=f) for ch in ROTATE])
                     for f in aimed if f not in keyed)
        missed = frames_off(aimed, baked, TOLERANCE, order)
        if not missed:
            break
        for f in missed:
            for axis, ch in enumerate(ROTATE):
                cmds.setKeyframe(node, attribute=ch, time=f, value=aimed[f][axis])
            keyed.add(f)
        added += len(missed)
    return added


# ------------------------------------------------------------------- engine

def aim_on(node, kind, vec, home_of, place, size=None):
    """Aim Mode's work on `node` (the caller holds the undo chunk and autoKey): controllers keyed on
    the node's own keys in `home_of(node)`'s space, `place(group, node)` putting the group there,
    the rotate keys cut and an aimConstraint (no offset) on. (keys, the node's long path)."""
    aim_v, up_v, d_aim, d_up = vec
    window = span()
    key = uuid(node)
    stale = group_of(node, kind)
    if stale:
        clear_broken(node, kind, stale)
    with maya_timewarp.unwarped():
        sample, keys, tangents = fkik.own_keys([long_(key)], [], window)
        fkik._suspend(True)
        try:
            home = home_of(long_(key))
            worlds = walk(sample, lambda: world(long_(key)))
            spaces = walk(sample, lambda: world(home)) if home and home != WORLD else None
        finally:
            fkik._suspend(False)
        size = size or max(d_aim, d_up) * 0.06
        group, made = make_controls(long_(key), kind, size, size * 0.8)
        cmds.setAttr(group + "." + kind.vectors_attr, " ".join(
            "%.12g" % v for v in tuple(aim_v) + tuple(up_v) + (d_aim, d_up)), type="string")
        group = place(group, long_(key))
        made = controllers(group, kind)
        frames = list(sample)
        if keys:
            targets = [local(point_of(worlds[f], aim_v, d_aim), spaces, f) for f in frames]
            ups = [local(point_of(worlds[f], up_v, d_up), spaces, f) for f in frames]
            write_series(made["target"], frames, targets, window, tangents)
            write_series(made["up"], frames, ups, window, tangents)
        else:
            now = frames[0]
            for role, direction, distance in (("target", aim_v, d_aim), ("up", up_v, d_up)):
                cmds.xform(made[role], worldSpace=True,
                           translation=point_of(worlds[now], direction, distance))
        node = long_(key)
        for ch in ROTATE:
            cmds.cutKey(node + "." + ch, clear=True)
        con = cmds.aimConstraint(made["target"], node, maintainOffset=False,
                                 aimVector=aim_v, upVector=up_axis(aim_v, up_v),
                                 worldUpType="object", worldUpObject=made["up"])[0]
        cmds.addAttr(con, longName=kind.con_marker, dataType="string")
        cmds.setAttr(con + "." + kind.con_marker, key, type="string")
    return keys, long_(key)


def aim_off(node, kind, group, made, cleanup=None):
    """Default's work on `node` (the caller holds the chunk): the rotation keyed back on the keys of
    the controllers and of its translate, then between them (`fill_between`), the constraint and the
    group deleted. (keys, how many keys were added between them)."""
    from maya_poselib import helpers
    window = span()
    key = uuid(node)
    with maya_timewarp.unwarped():
        nodes = [n for n in (made.get("target"), made.get("up"), node) if n]
        sample, keys, tangents = fkik.own_keys(nodes, [], window)
        attrs = helpers._attrs(node)

        def read():
            w = long_(key)
            return world(w) * om.MMatrix(cmds.getAttr(w + ".parentInverseMatrix[0]"))

        every = list(range(window[0], window[1] + 1)) if keys else []
        fkik._suspend(True)
        try:
            locals_ = walk(sorted(set(sample) | set(every)), read)
        finally:
            fkik._suspend(False)
        frames = list(sample)
        #  one Euler path through every frame in time order: the keys and the frames between
        #  them on the same turn (no 360 between neighbours)
        previous = [cmds.getAttr(node + "." + ch) for ch in ROTATE]
        aimed = {}
        for f in sorted(locals_):
            rotate, _t = helpers.driver_channels(locals_[f], attrs, previous)
            aimed[f] = list(rotate)
            previous = list(rotate)
        values = [aimed[f] for f in frames]
        con = constraint(node, kind)
        if con:
            cmds.delete(con)
        if cleanup:
            cleanup(group)
        cmds.delete(group)
        node = long_(key)
        for axis, ch in enumerate(ROTATE):
            plug = node + "." + ch
            if keys:
                fkik._write(plug, frames, [v[axis] for v in values], window, False, tangents)
            else:
                cmds.setAttr(plug, values[0][axis])
        added = 0
        if keys:
            added = fill_between(node, dict((f, aimed[f]) for f in every), set(frames),
                                 int(attrs.get("rotateOrder", 0)))
    return keys, added
