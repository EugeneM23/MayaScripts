"""Tools > Floor in the scene (2026-11-02): the character's feet put on the floor, contact by
contact.

One press on any part of a character: its feet's floor points (the ankle and the ball, each
against its own BIND height - the bind stands on y = 0, so the ball's own bind height is the
sole's thickness) are read over the span in ONE time walk; then, frame by frame, the body is
moved vertically so the LOWER foot stands exactly on the floor - every frame but a flight, where
both feet are a swing's height over their own nearby low and there is nothing to stand on
(`floorplan.airborne`; there is no contact detection, and trap 326 says why). As DELTAS on a new
additive layer `Floor` - so the animation itself is never touched, the layer can be muted,
weighted or deleted, and a second press rewrites it in place. One undo chunk; a refusal changes
nothing, and after writing the feet are read once more so the line can say whether they followed.

The carrier is the rig's `Main` (root motion), else the skeleton's top joint - never a Cascadeur
wrapper above it. Its parent may be turned (the Creep's root hangs under a -90 X `Armature`), so
the centimetre of world rise is written in the channels that really carry it, read per frame.

Spec: docs/superpowers/specs/2026-11-02-tools-floor-design.md
"""

import math

import maya.cmds as cmds
import numpy as np

from maya_tools import floorplan as plan
from maya_tools import knotplan as kplan
from maya_tools import knots
from maya_tools import layerbake

SLIDER = knots.SLIDER
LAYER_NAME = "Floor"
LAYER_MARKER = "skeldarFloor"
ANKLES = {"l": "foot_l", "r": "foot_r"}
BALLS = {"l": "ball_l", "r": "ball_r"}
CHECK_TOL = 0.1       # cm: past this the feet did not follow the body, and the line says so
CHANNELS = ("tx", "ty", "tz")


# ------------------------------------------------------------------ the scene

def _leaf(path):
    return path.split("|")[-1].split(":")[-1]


def _joints(root):
    return [knots._long(root)] + (cmds.listRelatives(root, allDescendents=True, type="joint",
                                                     fullPath=True) or [])


def feet_of(root):
    """{side: [the floor points, ankle first]} of the character at `root` - the ankle always, the
    ball when the skeleton has one (every shipped character does; a bare foot still works)."""
    by_leaf = {}
    for path in _joints(root):
        by_leaf.setdefault(_leaf(path), path)
    out = {}
    for side in plan.SIDES:
        points = [by_leaf[name] for name in (ANKLES[side], BALLS[side]) if name in by_leaf]
        if points:
            out[side] = points
    return out


def carrier_of(root):
    """What moves the whole character: the rig's `Main`, else the skeleton's top joint (`root`
    itself as `current_root` answers it) - never a wrapper above it, which would stop being
    Cascadeur's layout the moment it moved."""
    import maya_rigs
    path = knots._long(root)
    rig = maya_rigs.rig_of(path, maya_rigs.rigs())
    if rig is not None:
        main = knots._long(maya_rigs.node(rig, "Main"))
        if main:
            return main
    return path


def floor_layers():
    """Our Floor layers (marked; never found by name)."""
    return [layer for layer in cmds.ls(type="animLayer") or []
            if knots._has(layer, LAYER_MARKER)]


def layer_for(carrier):
    """The Floor layer already holding this carrier, else None - rewritten in place, so its
    place in the stack, its weight and its mute are kept (`layerbake.write_deltas(layer=)`)."""
    for layer in floor_layers():
        for plug in cmds.animLayer(layer, query=True, attribute=True) or []:
            if knots._long(plug.split(".")[0]) == carrier:
                return layer
    return None


# ------------------------------------------------- what a standing layer already holds

def weight_of(layer):
    """(weight, muted) of a standing Floor layer - 1.0 and False for none. Only a share `weight` of
    its curve reaches the body, so the correction a press means to add is written as `want / weight`
    (and on top of what the curve holds already: `standing_values`)."""
    if not layer:
        return 1.0, False
    try:
        return float(cmds.getAttr(layer + ".weight")), bool(cmds.getAttr(layer + ".mute"))
    except Exception:                                           # noqa: BLE001
        return 1.0, False


def standing_values(layer, carrier, channel, frames):
    """What a standing Floor layer's own curve holds for this channel at `frames` (0 where it holds
    nothing). The press reads the feet as they SHOW, so that reading already carries this layer's
    share: the curve it must end up holding is `old + want / weight`, not `want` - a rewrite REPLACES
    the curve, and writing `want` alone would take the old correction away again (measured
    2026-11-02: a second press left the feet 5 cm off)."""
    if not layer:
        return [0.0] * len(frames)
    plug = "%s.%s" % (carrier, kplan.LONG[channel])
    curve = (cmds.animLayer(layer, query=True, findCurveForPlug=plug) or [None])[0]
    if not curve:
        return [0.0] * len(frames)
    return [float(cmds.getAttr(curve + ".output", time=f)) for f in frames]


# ------------------------------------------------------------------ refusals

def _carrier_refusal(carrier, channels):
    """'' or why the body cannot be moved: a locked translate channel, or one driven by anything
    but time curves and animation layers (a constraint wins over the layer we would write)."""
    name = _leaf(carrier)
    refusal = kplan.uneven_parent(name, cmds.getAttr(carrier + ".parentMatrix[0]"))
    if refusal:
        return refusal
    longs = [kplan.LONG[ch] for ch in channels]
    locked, drivers = knots._channels(carrier, longs, layers=True)
    for ch, attr in zip(channels, longs):
        if locked.get(attr):
            return "%s.%s is locked - the body cannot be moved" % (name, attr)
        word = drivers.get(attr)
        if word:
            return "%s.%s is driven by %s - a layer would not move it" % (name, attr, word)
    return ""


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


def _height(node):
    return cmds.getAttr(node + ".worldMatrix[0]")[13]


def bind_heights(feet):
    """{point: its world Y at the BIND} - `maya_retargetmode.rest_world`, the one reader that is
    not fooled by a stale dagPose (trap 176). The bind stands on the floor, so this is how high
    that point is when the foot is flat on it."""
    import maya_retargetmode
    out = {}
    for points in feet.values():
        for point in points:
            out[point] = maya_retargetmode.rest_world(point)[13]
    return out


def _axis(carrier):
    """The LOCAL displacement one centimetre of world rise costs the carrier now: row vectors,
    so `v . parent3 = (0, 1, 0)`."""
    parent = np.reshape(cmds.getAttr(carrier + ".parentMatrix[0]"), (4, 4))[:3, :3]
    try:
        return tuple(np.dot(np.array([0.0, 1.0, 0.0]), np.linalg.inv(parent)))
    except np.linalg.LinAlgError:                               # a degenerate parent
        return (0.0, 1.0, 0.0)


def read(feet, binds, frames, carrier=None, step=None):
    """One time walk: ({side: {frame: how far that foot is above the floor}}, {frame: the local
    axis}, cancelled). The foot's clearance is the LOWER of its ankle's and its ball's; the axis
    is read only for a `carrier`, and only where the press is about to key it."""
    from maya_poselib import timewalk
    low = dict((side, {}) for side in feet)
    axes = {}
    with timewalk.Walk(fresh=False) as walk:
        for frame in frames:
            walk.go(frame)
            for side, points in feet.items():
                low[side][frame] = min(_height(p) - binds[p] for p in points)
            if carrier:
                axes[frame] = _axis(carrier)
            if step is not None and not step("frame %d" % frame):
                return low, axes, True
    return low, axes, False


def residual(feet, binds, want, step=None):
    """The worst distance the lowest planted point still stands from the floor, over the frames
    `want` aimed at - a second walk, so the press's own line can be trusted. A foot held in world
    (Connections > W, a 1P arm's road, a knot) does not move with the body, and this is what
    says so; None when the walk was stopped."""
    frames = sorted(want)
    if not frames:
        return 0.0
    low, _, cancelled = read(feet, binds, frames, step=step)
    if cancelled:
        return None
    worst = 0.0
    for frame in frames:
        here = [low[side][frame] for side in low if frame in low[side]]
        if here:
            worst = max(worst, abs(min(here)))
    return worst


# ------------------------------------------------------------------- the press

def run(root=None, highlight=SLIDER, check=True):
    """The Floor press. The line."""
    from maya_scenesetup import skeleton
    root = root or skeleton.current_root()
    if not root:
        return ("select any part of the character to stand on the floor - a bone, a control or "
                "its mesh")
    feet = feet_of(root)
    missing = [side for side in plan.SIDES if side not in feet]
    if missing:
        return "%s has no %s - the floor needs a pair of feet" % (
            _leaf(root), " and no ".join(ANKLES[side] for side in missing))
    carrier = carrier_of(root)
    #  only the channels the rise really needs: a locked translateX on a rig's Main is no reason to
    #  refuse a body that rises in its own Y (the axis is read where the press starts; a parent that
    #  turns mid-take could want another channel, and a locked one would raise inside the chunk)
    needed = [ch for ch, value in zip(CHANNELS, _axis(carrier))
              if abs(value) > plan.AXIS_DEAD] or list(CHANNELS)
    refusal = _carrier_refusal(carrier, needed)
    if refusal:
        return refusal
    first, last, ranged = _range(knots._highlight(highlight))
    frames = list(range(first, last + 1))
    binds = bind_heights(feet)
    with layerbake._progress(len(frames) * (2 if check else 1)) as bar:
        low, axes, cancelled = read(feet, binds, frames, carrier=carrier, step=bar.step)
        if cancelled:
            return "Floor: cancelled - nothing changed"
        down = dict((side, plan.down_frames(low[side])) for side in low)
        want = plan.wanted(low, plan.airborne(low))
        refusal = plan.refusal(want, first, last)
        if refusal:
            return refusal
        keys = plan.keys_for(want)
        standing = layer_for(carrier)
        weight, muted = weight_of(standing)
        if standing and abs(weight) < 1e-4:
            return ("the standing %s layer's weight is 0 - give it a weight, or delete it, and press "
                    "again" % LAYER_NAME)
        tracks = {}
        for ch, (times, values) in plan.tracks_for(want, keys, axes).items():
            #  a MUTED standing layer shows nothing, so the reading does not carry it and the curve
            #  must hold the whole correction; an unmuted one is already in what the feet show
            old = ([0.0] * len(times) if muted
                   else standing_values(standing, carrier, ch, times))
            tracks[(carrier, ch)] = (times, [o + v / weight for o, v in zip(old, values)])
        if not tracks:
            return ("%s cannot be moved up from here - its parent turns world up to nothing"
                    % _leaf(carrier))
        with knots._press("skeldarFloor"):
            layer = layerbake.write_deltas(LAYER_NAME, LAYER_MARKER, _leaf(carrier), tracks,
                                           ranged=ranged, layer=standing)
        left = residual(feet, binds, want, step=bar.step) if check else None
    message = plan.line(_leaf(root), _leaf(carrier), want, keys, down)
    message += " | %s%s" % (layer, " (replaced)" if standing else "")
    if standing and abs(weight - 1.0) > 1e-4:
        message += " at weight %.2f" % weight
    if muted:
        message += " - muted, so it shows nothing until you unmute it"
    if ranged:
        message += " | %d-%d only" % (first, last)
    #  a muted layer shows nothing, so the second walk reads the take unchanged - saying the feet
    #  did not follow would blame the carrier for the mute the same line already names
    if left is not None and left > CHECK_TOL and not muted:
        message += (" | the feet did not follow %s: still %.1f cm off - a leg held in world "
                    "(Connections > W, 1P, a knot) does not move with the body"
                    % (_leaf(carrier), left))
    return message
