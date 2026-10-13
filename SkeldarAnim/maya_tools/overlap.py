"""The Tools card's Overlap in the scene (2026-10-13): OverRig's overlapper, native.

The chains come from the selection - Hierarchy on: every selected object a root and, step by
step, the one node of its kind below it (a branch ends the chain); off: the selection, top to
bottom. One time walk per chain reads its members' world frames; `overlapplan` computes where
OverRig's construction (a joint chain, a locator ahead of each joint, aimed at and shifted later
by the lag) would turn them; the change is keyed as deltas on a new additive layer `Overlap`
(marked `skeldarOverlap`), so the animation itself is never touched - the layer can be muted,
weighted or deleted - and a second press on the same members replaces the first. One undo chunk;
a refusal changes nothing.

Spec: docs/superpowers/specs/2026-10-13-tools-aim-overlap-design.md
"""

import math

import maya.cmds as cmds
import numpy as np

from maya_tools import knotplan as kplan
from maya_tools import knots
from maya_tools import layerbake
from maya_tools import overlapplan as plan

SLIDER = knots.SLIDER
LAYER_NAME = "Overlap"
LAYER_MARKER = "skeldarOverlap"


# ------------------------------------------------------------------- chains

def _kind(node):
    """What a chain is made of: the node's shape type (a curve control, a mesh), else its own
    type (a joint, a bare transform)."""
    shapes = cmds.listRelatives(node, shapes=True, noIntermediate=True, fullPath=True) or []
    return cmds.nodeType(shapes[0]) if shapes else cmds.nodeType(node)


def _links_below(node, kind):
    """The nodes of `kind` under `node` reached without passing another of that kind (an
    AdvancedSkeleton FK control's next control lies under its FKX joint and offset groups)."""
    found, todo = [], list(knots._children(node))
    while todo:
        child = todo.pop(0)
        if cmds.objectType(child, isAType="constraint"):
            continue
        if _kind(child) == kind:
            found.append(child)
        else:
            todo.extend(knots._children(child))
    return found


def chain_from(root):
    """(chain, note): `root` and, each step, the one node of its kind below; a branch ends it."""
    kind = _kind(root)
    chain, node = [root], root
    while True:
        below = _links_below(node, kind)
        if len(below) != 1:
            note = ("%s branches (%d) - its chain stops there" % (kplan.leaf(node), len(below))
                    if len(below) > 1 else "")
            return chain, note
        node = below[0]
        chain.append(node)


def chains(selection, hierarchy):
    """([chains of long paths], [notes], refusal)."""
    objs = knots._selection(selection)
    if not objs:
        return [], [], plan.NOTHING
    if not hierarchy:
        if len(objs) < 2:
            return [], [], plan.alone_refusal(kplan.leaf(objs[0]), False)
        return [objs], [], ""
    found, notes = [], []
    for root in objs:
        chain, note = chain_from(root)
        found.append(chain)
        if note:
            notes.append(note)
    inner = set(node for chain in found for node in chain[1:])
    kept = [chain for chain in found if chain[0] not in inner]
    for chain in kept:
        if len(chain) < 2:
            return [], [], plan.alone_refusal(kplan.leaf(chain[0]), True)
    return kept, notes, ""


# ----------------------------------------------------------------- refusals

def _allowed(source):
    kind = cmds.nodeType(source)
    return kind in kplan.TIME_CURVES or kind.startswith("animBlendNode")


def _writable(node, channels):
    """(free channels, refusal): a channel is free when unlocked, and refused when something but
    a time curve or an animation layer drives it."""
    free = []
    for ch in channels:
        plug = node + "." + ch
        if cmds.getAttr(plug, lock=True):
            continue
        source = cmds.listConnections(plug, source=True, destination=False,
                                      skipConversionNodes=True) or []
        if source and not _allowed(source[0]):
            return None, ("%s: its %s is driven by %s - an overlap layers over animation; Bake "
                          "or Remove that first" % (kplan.leaf(node), ch, kplan.driver_word(
                              cmds.nodeType(source[0]),
                              cmds.objectType(source[0], isAType="constraint"))))
        free.append(ch)
    return free, ""


def _member_refusal(node):
    name = kplan.leaf(node)
    if knots.constraints_of(node):
        return kplan.riding_refusal(name)
    free, refusal = _writable(node, kplan.ROTATE)
    if refusal:
        return refusal
    if not free:
        return "%s has every rotate channel locked" % name
    return ""


# ------------------------------------------------------------------- layers

def overlap_layers():
    """Our Overlap layers (marked; never found by name)."""
    return [layer for layer in cmds.ls(type="animLayer") or [] if knots._has(layer,
                                                                             LAYER_MARKER)]


def _take_off(members):
    """A previous overlap of ours on `members` out of our layers (an emptied layer deleted).
    True when there was one."""
    wanted = set(members)
    found = False
    for layer in overlap_layers():
        plugs = cmds.animLayer(layer, query=True, attribute=True) or []
        mine = [plug for plug in plugs if knots._long(plug.split(".")[0]) in wanted]
        for plug in mine:
            cmds.animLayer(layer, edit=True, removeAttribute=plug)
            found = True
        if mine and not (cmds.animLayer(layer, query=True, attribute=True) or []):
            cmds.delete(layer)
    return found


def _write(deltas, times, ranged, cycled, roots):
    """The deltas {(node, channel): values over `times`} keyed on a new additive layer
    `Overlap` (`layerbake.write_deltas`); zero one frame outside a highlight; cycled curves
    cycle. The layer's name."""
    tracks = dict((key, (times, values)) for key, values in deltas.items())
    return layerbake.write_deltas(LAYER_NAME, LAYER_MARKER,
                                  " ".join(kplan.leaf(root) for root in roots), tracks,
                                  ranged=ranged, cycled=cycled)


# ------------------------------------------------------------------ reading

def _range(highlight):
    """(first, last, ranged) whole frames: the highlight `[a, b)` as `a..b-1`, else the take."""
    if highlight and highlight[1] - highlight[0] > 1:
        return int(round(highlight[0])), int(round(highlight[1])) - 1, True
    take = kplan.take_range((cmds.playbackOptions(query=True, min=True),
                             cmds.playbackOptions(query=True, max=True)),
                            (cmds.playbackOptions(query=True, animationStartTime=True),
                             cmds.playbackOptions(query=True, animationEndTime=True)))
    return int(math.floor(take[0])), int(math.ceil(take[1])), False


def _matrix(node, attr):
    return np.reshape(cmds.getAttr(node + "." + attr), (4, 4))


def _frame_now(node):
    return plan.frame(_matrix(node, "worldMatrix[0]"),
                      cmds.xform(node, query=True, worldSpace=True, rotatePivot=True))


def _sample(chain, frames):
    """One time walk over `frames`: every member's world matrix, parent matrix, world rotate
    pivot, rotate and translate values."""
    from maya_poselib import timewalk
    count, length = len(chain), len(frames)
    out = dict(world=np.zeros((count, length, 4, 4)), parent=np.zeros((count, length, 4, 4)),
               pivot=np.zeros((count, length, 3)), rotate=np.zeros((count, length, 3)),
               translate=np.zeros((count, length, 3)))
    with timewalk.Walk(fresh=False) as walk:
        for k, frame in enumerate(frames):
            walk.go(frame)
            for i, node in enumerate(chain):
                out["world"][i, k] = _matrix(node, "worldMatrix[0]")
                out["parent"][i, k] = _matrix(node, "parentMatrix[0]")
                out["pivot"][i, k] = cmds.xform(node, query=True, worldSpace=True,
                                                rotatePivot=True)
                out["rotate"][i, k] = cmds.getAttr(node + ".rotate")[0]
                out["translate"][i, k] = cmds.getAttr(node + ".translate")[0]
    return out


def _rides(parent, earlier):
    """The index of the deepest earlier member the DAG `parent` is or lies under, or None."""
    for index in range(len(earlier) - 1, -1, -1):
        member = earlier[index]
        if parent == member or (parent or "").startswith(member + "|"):
            return index
    return None


def _orient_matrices(node):
    rotate_axis = plan.matrix_from_euler(cmds.getAttr(node + ".rotateAxis")[0], 0)
    joint = None
    if cmds.objectType(node, isAType="joint"):
        joint = plan.matrix_from_euler(cmds.getAttr(node + ".jointOrient")[0], 0)
    return rotate_axis, joint


def _chain_deltas(chain, settings, first, last):
    """{(node, channel): delta values over first..last} for one chain."""
    lag = plan.link_lag(settings, len(chain))
    if settings.cycled:
        window = list(range(first, last + 1))
    else:
        reach = plan.pad(lag, len(chain))
        window = list(range(first - reach, last + reach + 1))
    rest = np.array([_frame_now(node) for node in chain])
    data = _sample(chain, window)
    frames = np.array([[plan.frame(data["world"][i, k], data["pivot"][i, k])
                        for k in range(len(window))] for i in range(len(chain))])
    new = plan.simulate(frames, rest, lag, settings.softness, settings.easing, settings.cycled)
    out = slice(window.index(first), window.index(last) + 1)
    count = last - first + 1
    weights = (plan.edge_weights(count) if settings.edges else np.ones(count))[:, None]
    deltas = {}
    for i, node in enumerate(chain):
        index = _rides(knots._parent(node), chain[:i])
        parent_new = (plan.carried(data["parent"][i], frames[index], new[index])
                      if index is not None else data["parent"][i])
        rotate_axis, joint = _orient_matrices(node)
        rotations = [plan.rotate_values(new[i, k, :3, :3], parent_new[k], rotate_axis, joint)
                     for k in range(out.start, out.stop)]
        base = data["rotate"][i, out]
        turned = (np.array(plan.eulers(rotations, cmds.getAttr(node + ".rotateOrder"), base))
                  - base) * weights
        moved = plan.translate_delta(data["pivot"][i, out], data["parent"][i, out],
                                     new[i, out, 3, :3], parent_new[out]) * weights
        free_rotate, _refusal = _writable(node, kplan.ROTATE)
        for c, ch in enumerate(kplan.ROTATE):
            if ch in free_rotate and float(np.abs(turned[:, c]).max()) > plan.CHANGED:
                deltas[(node, ch)] = turned[:, c]
        if float(np.abs(moved).max()) > plan.CHANGED:
            free_move, refusal = _writable(node, kplan.TRANSLATE)
            for c, ch in enumerate(kplan.TRANSLATE):
                if not refusal and ch in free_move:
                    deltas[(node, ch)] = moved[:, c]
    return deltas


# -------------------------------------------------------------------- press

def run(selection=None, settings=plan.DEFAULTS, highlight=SLIDER):
    """The Overlap press. The line."""
    refusal = plan.settings_refusal(settings)
    if refusal:
        return refusal
    found, notes, refusal = chains(selection, settings.hierarchy)
    if refusal:
        return refusal
    members = [node for chain in found for node in chain]
    if len(set(members)) != len(members):
        return "a member stands in two chains - select each chain once"
    for node in members:
        refusal = _member_refusal(node)
        if refusal:
            return refusal
    for chain in found:
        try:
            plan.rest(np.array([_frame_now(node) for node in chain]))
        except ValueError as exc:
            index = exc.args[0]
            return "%s and %s stand in one place - a chain needs length" % (
                kplan.leaf(chain[index]), kplan.leaf(chain[index + 1]))
    first, last, ranged = _range(knots._highlight(highlight))
    times = list(range(first, last + 1))
    with knots._press("skeldarOverlap"):
        replaced = _take_off(members)
        deltas = {}
        for chain in found:
            deltas.update(_chain_deltas(chain, settings, first, last))
        if not deltas:
            return "the chain does not move over %d-%d - nothing to overlap" % (first, last)
        layer = _write(deltas, times, ranged, settings.cycled, [c[0] for c in found])
        cmds.select(members, replace=True)
    return plan.overlap_message(found, settings, plan.link_lag(settings, len(found[0])), first,
                                last, ranged, layer, replaced, notes)
