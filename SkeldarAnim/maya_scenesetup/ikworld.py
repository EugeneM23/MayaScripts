"""An IK hand or foot on a world control (2026-10-28).

The animator: «во вкладке connection там где мы перепекаем руки в IK сделаем возможность
поставить галочку WORLD. при простановке этой галочки мы должны не просто переключиться в ик а
переподвязаться еще на новый контрол который будет привязан как knot world инструмент во
вкладке tools». Asked: Tools' Double knot World (the card's «World ×2»), keyed only on the keys
the IK switch keys, for the arms and the legs.

An AdvancedSkeleton IK control lives in Main's space (`followMain 10`). Under a Double knot
World - an outer `_dknotMove` carrying its place, an inner `_dknotRotate` its turn, in the
character's Knots group - it stays where it is in the scene while Main and the body move. The
control is a Tools knot like any other: Tools' Bake / Remove, its attach blend and Delete
character work on it unchanged.

A limb is IN WORLD when a `double_world` knot drives its IK control (`knot_of`); one the
animator made in Tools counts too. `enter` makes it (`knots.create_keyed`: sampled and keyed on
the IK's keys, not baked on every frame), `leave` takes the limb back into Main's space keyed on
the world control's keys, `drop` takes the control off. Connections' `switch_limb` and
`toggle_world` (the rows' W) decide which.

The same day, after using it («вместо локатора мы будем создавать контроллер», and a W toggle
beside each limb's IK in place of one World chip): the knot's two locators are made CONTROLS
(`curvectrl.reshape`, as 1P Setup's chest) - the Move a box in world axes, the Rotate three rings
- named `<ik>_worldMove_ctrl` / `<ik>_worldRotate_ctrl`; still a knot to Tools.

Spec: docs/superpowers/specs/2026-10-28-connections-ik-world-design.md
"""

import math

import maya.cmds as cmds

from maya_scenesetup import curvectrl
from maya_scenesetup import fkik
from maya_tools import knotplan
from maya_tools import knots

KIND = "double_world"
ALREADY = "%s is already IK in world (%s)"
IN_WORLD_IK = "%s is already IK, in world - W takes it back into Main's space"
IN_WORLD = "%s is IK in world - press its W first"
LEFT_OVER = ("%s shows FK with a world control left on %s - press FK to take it off "
             "first")
# the controls (2026-10-28, «вместо локатора мы будем создавать контроллер»)
MOVE_NAME = "{0}_worldMove_ctrl"
ROTATE_NAME = "{0}_worldRotate_ctrl"
MOVE_COLOUR = knotplan.kind(KIND).colour
ROTATE_COLOUR = knotplan.kind(KIND).inner_colour
BOX_GROW = 1.6            # the Move box's half side over the IK control's drawing's half extent
RING_GROW = 1.3           # the Rotate rings' radius over it
LEAST = 6.0               # cm: the half extent when the IK control draws nothing
RING_SIDES = 24


# ------------------------------------------------------------------- pure

def _leaf(path):
    return (path or "").split("|")[-1]


def _keys_words(keys):
    if not keys:
        return None
    count = "%d key%s" % (len(keys), "" if len(keys) == 1 else "s")
    first, last = fkik._frame_text(keys[0]), fkik._frame_text(keys[-1])
    return "%s (%s)" % (count, first if len(keys) == 1 else "%s..%s" % (first, last))


def box(half):
    """A cube of half side `half` about the origin, one degree-1 line through its 12 edges.
    Pure."""
    h = half
    return [(-h, -h, -h), (h, -h, -h), (h, h, -h), (-h, h, -h), (-h, -h, -h),
            (-h, -h, h), (h, -h, h), (h, h, h), (-h, h, h), (-h, -h, h),
            (-h, h, h), (-h, h, -h), (h, h, -h), (h, h, h), (h, -h, h), (h, -h, -h)]


def _ring(radius, axes, start, sides):
    """A closed circle in the plane of `axes`, from the angle step `start` round to it. Pure."""
    out = []
    for i in range(sides + 1):
        a = 2.0 * math.pi * (start + i) / sides
        p = [0.0, 0.0, 0.0]
        p[curvectrl.AXES[axes[0]]] = radius * math.cos(a)
        p[curvectrl.AXES[axes[1]]] = radius * math.sin(a)
        out.append(tuple(p))
    return out


def rings(radius, sides=RING_SIDES):
    """Three rings about the origin (XY, XZ, YZ) as ONE degree-1 line with no chord between
    them: the XY ring, then the XZ ring as far as +Z, the YZ ring whole from there, the rest of
    the XZ ring. `sides` a multiple of 4. Pure."""
    quarter = sides // 4
    xy = _ring(radius, ("x", "y"), 0, sides)                      # +X round to +X
    xz = _ring(radius, ("x", "z"), 0, sides)                      # +X, +Z at a quarter
    yz = _ring(radius, ("y", "z"), quarter, sides)                # +Z round to +Z
    return xy + xz[1:quarter + 1] + yz[1:] + xz[quarter + 1:]


def control_half(extent_box):
    """The IK control's drawing's largest half extent ((min, max) of its CVs, or None). Pure."""
    if not extent_box:
        return LEAST
    lo, hi = extent_box
    return max(max(hi[i] - lo[i] for i in range(3)) / 2.0, 1e-3)


def entered_message(control, top, keys):
    """What `enter` did: the IK control, its world control, the keys. Pure."""
    where = _keys_words(keys)
    text = "%s in world on %s" % (_leaf(control), _leaf(top))
    return text + (", " + where if where else ", no keys - set at the current frame")


def left_message(label, control, keys, m, kind=fkik.ARM):
    """What `leave` did, measured (`fkik.Measure`). Pure."""
    what = fkik.ROLL_WORDS[kind]["what"]
    where = _keys_words(keys) or "the current frame"
    text = "%s back from world on %s - %s in Main's space again" % (label, where, _leaf(control))
    if m.cm <= fkik.TOLERANCE_CM and m.hand <= fkik.TOLERANCE_DEG:
        return text + ", the %s kept to %.4f cm, %.3f deg" % (what, m.cm, max(m.hand, m.roll))
    return text + ", the %s moved up to %.2f cm (frame %s)" % (what, m.cm, m.cm_frame)


# ------------------------------------------------------------------ scene

def knot_of(control):
    """The Double knot World that drives the IK control, or None."""
    if not control or not cmds.objExists(control):
        return None
    for top in knots.driving(control):
        if knots.kind_of(top) == KIND:
            return top
    return None


def limb_knot(limb):
    """The world control a limb's IK control rides (`knot_of`), or None."""
    return knot_of(limb.ik)


def nodes_of(top):
    """The world control's own nodes (Move and Rotate): their keys are the limb's."""
    return knots.nodes_of(top)


def key_times(top):
    """Every key time on the world control's nodes."""
    return cmds.keyframe(nodes_of(top), query=True, timeChange=True) or []


def refusal(limb):
    """Why the limb's IK control cannot go onto a world control, or ''."""
    return knots.knot_refusal(KIND, limb.ik)


def enter(limb, frames, tangents, highlight):
    """The IK control onto a new world control keyed on `frames` with the switch's `tangents`;
    the span a knot's (`highlight` as the slider answers it, else the whole take). The line."""
    top, line = knots.create_keyed(KIND, limb.ik, frames, tangents, highlight=highlight)
    if top is None:
        return "World: " + line
    top = make_controls(top, limb.ik)
    #  a whole take's still channel is a plain value, as the switch writes it: no keys at all
    keyed = bool(cmds.keyframe(nodes_of(top), query=True, keyframeCount=True))
    return entered_message(limb.ik, top, sorted(frames) if keyed else [])


def make_controls(top, ik):
    """The knot's two locators made controls: the Move (`top`, no rotation) a box in world axes,
    the Rotate three rings in its own axes, both sized from the IK control's drawing; renamed.
    The Move's long path."""
    half = control_half(curvectrl.local_box(ik))
    leaf = _leaf(ik).split(":")[-1]
    uuid = cmds.ls(top, uuid=True)[0]
    inner = cmds.ls([n for n in nodes_of(top) if n != top][0], uuid=True)[0]
    #  by UUID: renaming the Move renames the path of the Rotate under it (trap 16)
    for node_uuid, points, colour, name in (
            (uuid, box(half * BOX_GROW), MOVE_COLOUR, MOVE_NAME),
            (inner, rings(half * RING_GROW), ROTATE_COLOUR, ROTATE_NAME)):
        curvectrl.reshape(cmds.ls(node_uuid, long=True)[0], points, colour)
        node = cmds.rename(cmds.ls(node_uuid, long=True)[0], name.format(leaf))
        node = cmds.ls(node_uuid, long=True)[0]
        for shape in cmds.listRelatives(node, shapes=True, fullPath=True) or []:
            cmds.rename(shape, node.split("|")[-1].split(":")[-1] + "Shape")
    return cmds.ls(uuid, long=True)[0]


def drop(top):
    """The world control taken off (Tools' Remove: the IK control's own curves back), the
    animator's selection kept. The line."""
    selection = cmds.ls(selection=True, long=True) or []
    knots.remove([top])
    kept = [s for s in selection if cmds.objExists(s)]
    if kept:
        cmds.select(kept, replace=True)
    else:
        cmds.select(clear=True)
    return "the world control %s removed" % _leaf(top)


def _span_of(top):
    """(start, end, ranged) the IK is written over: a ranged knot's full span `a..b-1` (its
    attach is 1 there), else the whole take it was made over."""
    span = knots.span_of(top)
    if not span:
        start = cmds.playbackOptions(query=True, min=True)
        end = cmds.playbackOptions(query=True, max=True)
        return int(math.floor(start)), int(math.ceil(end)), False
    start, end, ranged = span
    if ranged:
        return int(round(start)) + 1, int(round(end)) - 1, True
    return int(math.floor(start)), int(math.ceil(end)), False


def leave(limb, top):
    """The limb back in Main's space: the IK control keyed, on the world control's keys, with
    what it shows there; the world control removed. The caller holds the undo chunk. The line."""
    span = _span_of(top)
    frames, keys, tangents = fkik.own_keys(nodes_of(top), [], span)
    ik = limb.ik
    parent = fkik._parent(ik)
    order = cmds.getAttr(ik + ".rotateOrder")
    now = cmds.currentTime(query=True)
    auto = cmds.autoKeyframe(query=True, state=True)
    cmds.autoKeyframe(state=False)
    fkik._suspend(True)
    try:
        #  the euler each new key starts from: what the control shows a frame before a range,
        #  else on the first key (read after a real time change: the knot's constraint drives it)
        fkik._goto(frames[0] - 1 if span[2] else frames[0])
        previous = [cmds.getAttr(ik + "." + ch) for ch in fkik.ROTATE]
        values = dict((ch, []) for ch in fkik.CHANNELS)
        before = {}
        for frame in frames:
            fkik._goto(frame)
            local = fkik._world(ik) * fkik._world(parent).inverse()
            t, r = fkik.local_channels(local, order, previous)
            previous = r
            for ch, v in zip(fkik.CHANNELS, t + r):
                values[ch].append(v)
            before[frame] = [fkik._world(n) for n in limb.deform]
        drop(top)
        for ch in fkik.CHANNELS:
            plug = ik + "." + ch
            fkik._write(plug, frames, values[ch], span, cmds.getAttr(plug, lock=True), tangents)
        after = {}
        for frame in frames:
            fkik._goto(frame)
            after[frame] = [fkik._world(n) for n in limb.deform]
        moved = fkik.measure(before, after)
    finally:
        fkik._goto(now)
        cmds.autoKeyframe(state=auto)
        fkik._suspend(False)
    label = fkik.LABEL[limb.kind].format(limb.side)
    return left_message(label, ik, keys, moved, kind=limb.kind)
