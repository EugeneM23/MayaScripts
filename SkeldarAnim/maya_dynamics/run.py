"""Dynamics' press (2026-10-26): read the animation, solve, bake one layer per chain.

Which chains: the ones given (the card's picked rows), else the chains of the selection's
characters and the chains the selection is in, else - nothing selected - every chain of the active
tab. The range: the time slider's highlight, else the playback range; Loop takes it as one cycle.

One time walk (`timewalk.Walk`: unrecorded, the animator's tweaks put back, Scene Time Warp off)
reads every member's world frame, parent matrix, rotate pivot and channels, every carrier, every
collider's world matrix and `enabled`, and the wind arrow - with each chain's own Dynamics layer
MUTED, so a re-simulation never reads its own result. The reading is kept on `sys` and reused by a
knob's release (`reuse=True`) until Maya reports a key edit, an undo or redo, a new or opened scene
or a time unit change; Simulate always reads afresh. `model.simulate` solves all the chains
together; `overlap.deltas_for` turns the new frames into rotate / translate deltas;
`layerbake.write_deltas` keys them on the chain's layer `Dynamics_<root leaf>` (marked
`skeldarDynamics` = the chain's UUID), written again in place when it stands (its weight and mute
kept). A highlight puts zero one frame outside it; Loop keys the cycle with its first frame again
at its end and cycles the curves.

One undo chunk a press, autoKey off, the time put back; a refusal changes nothing. Spec:
docs/superpowers/specs/2026-10-26-bone-dynamics-design.md
"""

import math
import sys

import maya.cmds as cmds
import numpy as np

from maya_dynamics import model
from maya_dynamics import setup

SLIDER = "slider"
STATE = "_skeldar_dynamics"

NOTHING = "make a chain first - select a root and press + Chain"
CANCELLED = "Dynamics: cancelled - nothing changed"
BROKEN = "%s's member %d is gone from the scene - Remove the chain and make it again"
SHORT = "Loop needs a cycle of at least 3 frames - %d-%d is too short"


# -------------------------------------------------------------------- state

def _state():
    """The session's reading and its generation, on `sys` (trap 111)."""
    state = getattr(sys, STATE, None)
    if state is None:
        state = {"generation": 0, "cache": None, "callbacks": [], "writing": False}
        setattr(sys, STATE, state)
    return state


def _bump(*_args):
    """A callback: the scene changed under the reading (key edit, undo, redo, a scene)."""
    state = getattr(sys, STATE, None)
    if state is not None and not state.get("writing"):
        state["generation"] = state.get("generation", 0) + 1
        state["cache"] = None


def watch():
    """The callbacks that drop the reading, registered once a session."""
    state = _state()
    if state["callbacks"]:
        return
    try:
        import maya.api.OpenMaya as om
        import maya.api.OpenMayaAnim as oma
    except ImportError:                                        # a test without Maya
        return
    ids = [oma.MAnimMessage.addAnimKeyframeEditedCallback(_bump)]
    for event in ("Undo", "Redo", "timeUnitChanged"):
        ids.append(om.MEventMessage.addEventCallback(event, _bump))
    for kind in (om.MSceneMessage.kAfterOpen, om.MSceneMessage.kAfterNew):
        ids.append(om.MSceneMessage.addCallback(kind, _bump))
    state["callbacks"] = ids


def forget():
    """Drop the reading (Simulate's press)."""
    _state()["cache"] = None


# ------------------------------------------------------------------- targets

def targets(selection=None):
    """The chains a press acts on when the card picks none."""
    from maya_tools import knots
    every = setup.chains()
    selected = knots._selection(selection)
    if not selected:
        return every
    characters = set(setup._character(node) for node in selected)
    characters.discard(None)
    found = [chain for chain in every if setup._character(chain) in characters]
    for node in selected:
        chain = setup.chain_of(node)
        if chain and chain not in found:
            found.append(chain)
    return found


# --------------------------------------------------------------------- range

def window(first, last, loop):
    """The frames read: the range, and with Loop the frame after it (the next cycle's first)."""
    return list(range(first, last + (2 if loop else 1)))


def frame_range(highlight):
    """(first, last, ranged) whole frames: the highlight `[a, b)` as `a..b-1`, else the playback
    range."""
    if highlight and highlight[1] - highlight[0] > 1:
        return int(round(highlight[0])), int(round(highlight[1])) - 1, True
    return (int(math.floor(cmds.playbackOptions(query=True, min=True))),
            int(math.ceil(cmds.playbackOptions(query=True, max=True))), False)


def loop_inputs(frames_list, carriers):
    """A Loop's input from every chain's frames read over the range and the one after it:
    (frames_list, carriers, closes), each cut to one cycle plus its next first frame - decided for
    every chain together, so they share one cycle. When the range's last frame repeats its first
    for every chain (`closes`), that last frame IS the next first; else when the frame after the
    range repeats the first, less the travel, for every chain (cycled curves), that one is; else
    each chain's first frame moved on by its range's travel per frame (an uncycled range)."""
    frames_list = [np.asarray(f, float) for f in frames_list]
    carriers = [np.asarray(c, float) for c in carriers]
    if all(model.repeats_first([f[:, :-1]], c[:-1]) for f, c in zip(frames_list, carriers)):
        return [f[:, :-1] for f in frames_list], [c[:-1] for c in carriers], True
    if all(model.repeats_first([f], c) for f, c in zip(frames_list, carriers)):
        return frames_list, carriers, False
    out, out_carriers = [], []
    for frames, carrier in zip(frames_list, carriers):
        count = len(carrier) - 1                  # the range's frames
        travel = (carrier[count - 1] - carrier[0]) / max(count - 1, 1) * count
        frames = frames.copy()
        frames[:, -1] = frames[:, 0]
        frames[:, -1, 3, :3] += travel
        carrier = carrier.copy()
        carrier[-1] = carrier[0] + travel
        out.append(frames)
        out_carriers.append(carrier)
    return out, out_carriers, False


# ------------------------------------------------------------------- reading

def _matrix(node, attr="worldMatrix[0]"):
    return np.reshape(cmds.getAttr(node + "." + attr), (4, 4))


def _point(node):
    return cmds.xform(node, query=True, worldSpace=True, rotatePivot=True)


def _layers_muted(chains):
    """{layer: its mute} of the chains' own Dynamics layers."""
    out = {}
    for chain in chains:
        layer = setup.layer_of(chain)
        if layer:
            out[layer] = bool(cmds.getAttr(layer + ".mute"))
    return out


def _mute(states, on):
    for layer, was in states.items():
        if cmds.objExists(layer):
            cmds.setAttr(layer + ".mute", True if on else was)


def read(chains, colliders, wind, frames, progress=None):
    """One walk over `frames`: {"members": [per chain: overlap's sample dict], "carriers":
    [(F, 3)], "colliders": [(F, 4, 4)], "enabled": [(F,)], "wind": dict or None}. None when the
    walk was cancelled."""
    from maya_poselib import timewalk
    count = len(frames)
    groups = [setup.members(chain) for chain in chains]
    carriers = [setup.carrier(chain) for chain in chains]
    out = {"members": [], "carriers": [np.zeros((count, 3)) for _ in chains],
           "colliders": [np.zeros((count, 4, 4)) for _ in colliders],
           "enabled": [np.ones(count, bool) for _ in colliders], "wind": None}
    for group in groups:
        n = len(group)
        out["members"].append(dict(
            world=np.zeros((n, count, 4, 4)), parent=np.zeros((n, count, 4, 4)),
            pivot=np.zeros((n, count, 3)), rotate=np.zeros((n, count, 3)),
            translate=np.zeros((n, count, 3))))
    if wind:
        out["wind"] = dict(matrix=np.zeros((count, 4, 4)), seed=int(cmds.getAttr(wind + ".seed")),
                           **dict((attr, np.zeros(count)) for attr, *_r in setup.WIND_CHANNELS))
    with timewalk.Walk(fresh=False) as walk:
        for k, frame in enumerate(frames):
            walk.go(frame)
            for c, group in enumerate(groups):
                data = out["members"][c]
                for i, node in enumerate(group):
                    data["world"][i, k] = _matrix(node)
                    data["parent"][i, k] = _matrix(node, "parentMatrix[0]")
                    data["pivot"][i, k] = _point(node)
                    data["rotate"][i, k] = cmds.getAttr(node + ".rotate")[0]
                    data["translate"][i, k] = cmds.getAttr(node + ".translate")[0]
                out["carriers"][c][k] = _point(carriers[c])
            for j, collider in enumerate(colliders):
                out["colliders"][j][k] = _matrix(collider)
                out["enabled"][j][k] = bool(cmds.getAttr(collider + ".enabled"))
            if wind:
                out["wind"]["matrix"][k] = _matrix(wind)
                for attr, *_rest in setup.WIND_CHANNELS:
                    out["wind"][attr][k] = float(cmds.getAttr(wind + "." + attr))
            if progress is not None and not progress.step("reading frame %d" % frame):
                return None
    return out


def _frames(data):
    """The members' frames for the model: (n, F, 4, 4) - rotation rows at the rotate pivot."""
    from maya_tools import overlapplan as oplan
    n, count = data["world"].shape[:2]
    return np.array([[oplan.frame(data["world"][i, k], data["pivot"][i, k])
                      for k in range(count)] for i in range(n)])


def collider_input(kind, matrices, enabled, radius, length):
    """A `model.Collider` from a collider's world matrices (F, 4, 4): a capsule's segment along its
    local X, centred, `length` times its world X scale, its radius times the mean of its Y and Z
    scales; a plane through its origin, its local Y the normal."""
    m = np.asarray(matrices, float)
    origin = m[:, 3, :3]
    if kind == "plane":
        return model.Collider("plane", origin, None, None, normal=m[:, 1, :3], enabled=enabled)
    half = 0.0 if kind == "sphere" else 0.5 * float(length)
    a = origin - half * m[:, 0, :3]
    b = origin + half * m[:, 0, :3]
    scale = 0.5 * (np.linalg.norm(m[:, 1, :3], axis=1) + np.linalg.norm(m[:, 2, :3], axis=1))
    return model.Collider("capsule" if half else "sphere", a, b, float(radius) * scale,
                          enabled=enabled)


def wind_input(wind):
    """A `model.WindInput` from the arrow's reading, or None: its local +Z the direction."""
    if not wind:
        return None
    direction = wind["matrix"][:, 2, :3]
    return model.WindInput(direction, wind["strength"], wind["turbulence"], wind["gust"],
                           wind["frequency"], wind["seed"])


# --------------------------------------------------------------------- lines

def message(chains, joints, first, last, substeps, colliders, wind, layers, info, loop, notes):
    """The press's line: «hair_01: 6 joints, frames 0-60, 4 substeps, 3 colliders, wind -
    Dynamics_hair_01 | Loop settled in 3 cycles»."""
    names = [setup.leaf(setup.root_of(c) or c) for c in chains]
    head = names[0] if len(names) == 1 else "%d chains (%s)" % (len(names), ", ".join(names))
    words = ["%d joints" % joints, "frames %d-%d" % (first, last), "%d substeps" % substeps]
    if colliders:
        words.append("%d collider%s" % (colliders, "" if colliders == 1 else "s"))
    if wind:
        words.append("wind")
    line = "%s: %s - %s" % (head, ", ".join(words), ", ".join(layers))
    if loop:
        cycles = info.get("cycles", 0)
        line += (" | Loop settled in %d cycles" % cycles if info.get("settled")
                 else " | Loop did not settle in %d cycles - more Damping closes it" % cycles)
    if info.get("ignored"):
        line += " | %d joint-collider pairs start inside and ignore each other" % info["ignored"]
    for note in notes:
        line += " | " + note
    return line


# --------------------------------------------------------------------- press

def _refusal(chains):
    from maya_tools import overlap
    if not chains:
        return NOTHING
    for chain in chains:
        group = setup.members(chain)
        for index, member in enumerate(group):
            if member is None:
                return BROKEN % (setup.leaf(chain), index + 1)
        for member in group:
            refusal = overlap._member_refusal(member)
            if refusal:
                return refusal
    return ""


def _highlight(highlight):
    from maya_tools import knots
    return knots._highlight(highlight)


def _fps():
    import maya.api.OpenMaya as om
    return float(om.MTime(1.0, om.MTime.kSeconds).asUnits(om.MTime.uiUnit()))


def simulate(chains=None, highlight=SLIDER, reuse=False, progress=None):
    """The Simulate press (a knob's release with `reuse`). The line."""
    from maya_poselib import timewalk
    from maya_tools import knots
    from maya_tools import layerbake
    from maya_tools import overlap
    watch()
    chains = [c for c in (chains if chains is not None else targets()) if cmds.objExists(c)]
    refusal = _refusal(chains)
    if refusal:
        return refusal
    for chain in chains:
        for collider in setup.colliders(chain):
            setup.redraw(collider)
    settings = [setup.read_settings(chain) for chain in chains]
    loop = any(s["loop"] for s in settings)
    first, last, ranged = frame_range(_highlight(highlight))
    if loop and last - first < 2:
        return SHORT % (first, last)
    colliders = sorted(set(c for chain in chains for c in setup.colliders(chain)))
    wind = setup.wind()
    frames = window(first, last, loop)
    key = (tuple(chains), tuple(tuple(m for m in setup.members(c)) for c in chains),
           tuple(colliders), wind, tuple(frames), _fps())
    state = _state()
    with knots._press("skeldarDynamics"):
        reading = state["cache"][1] if (reuse and state["cache"] and state["cache"][0] == key) \
            else None
        if reading is None:
            muted = _layers_muted(chains)
            _mute(muted, True)
            try:
                with timewalk.Progress("Dynamics", len(frames)) as walk_progress:
                    reading = read(chains, colliders, wind, frames, progress or walk_progress)
            finally:
                _mute(muted, False)
            if reading is None:
                return CANCELLED
            state["cache"] = (key, reading)
        inputs, carriers, joints = [], [], 0
        for c, chain in enumerate(chains):
            inputs.append(_frames(reading["members"][c]))
            carriers.append(reading["carriers"][c])
            joints += len(setup.members(chain))
        closes = False
        if loop:
            inputs, carriers, closes = loop_inputs(inputs, carriers)
        collider_inputs = []
        for j, collider in enumerate(colliders):
            kind = setup.kind_of(collider)
            m = reading["colliders"][j][:inputs[0].shape[1]]
            on = reading["enabled"][j][:inputs[0].shape[1]]
            collider_inputs.append(collider_input(kind, m, on, setup._get(collider, "radius", 0.0),
                                                  setup._get(collider, "length", 0.0)))
        wind_in = wind_input(reading["wind"])
        if wind_in is not None:
            span = inputs[0].shape[1]
            wind_in = model.WindInput(*([np.asarray(v)[:span] for v in wind_in[:5]]
                                        + [wind_in.seed]))
        outs, info = model.simulate(
            [model.ChainInput(f, car, s) for f, car, s in zip(inputs, carriers, settings)],
            colliders=collider_inputs, wind=wind_in, fps=_fps(), loop=loop)
        T = outs[0].shape[1]
        times = list(range(first, first + T))
        if loop:
            times.append(first + T)                       # the first frame again: the cycle closes
        layers, notes = [], []
        state["writing"] = True
        try:
            for c, chain in enumerate(chains):
                data = dict((k, v[:, :T]) for k, v in reading["members"][c].items())
                deltas = overlap.deltas_for(setup.members(chain), data, inputs[c][:, :T], outs[c],
                                            slice(0, T), np.ones((T, 1)))
                if loop:
                    deltas = dict((k, np.append(v, v[0])) for k, v in deltas.items())
                if not deltas:
                    notes.append("%s does not move" % setup.leaf(setup.root_of(chain)))
                    continue
                tracks = dict((k, (times, v)) for k, v in deltas.items())
                layer = layerbake.write_deltas(
                    setup.layer_name(chain), setup.LAYER_MARKER, setup._uuid(chain), tracks,
                    ranged=ranged and not loop, cycled=loop, layer=setup.layer_of(chain))
                layers.append(layer)
        finally:
            state["writing"] = False
    if not layers:
        return "the chains do not move over %d-%d - nothing to bake" % (first, last)
    if loop and closes:
        notes.append("the range closes on itself: its last frame is its first")
    return message(chains, joints, first, last, max(s["substeps"] for s in settings),
                   len(colliders), wind is not None, layers, info, loop, notes)


def remove(chains):
    """Remove: the chains' layers and setups (their colliders stay). The line."""
    from maya_tools import knots
    chains = [c for c in chains or [] if cmds.objExists(c)]
    if not chains:
        return "pick a chain to Remove"
    names = [setup.leaf(setup.root_of(c) or c) for c in chains]
    with knots._press("skeldarDynamicsRemove"):
        layers = [setup.remove(chain) for chain in chains]
    forget()
    gone = [layer for layer in layers if layer]
    return "Removed %s%s" % (", ".join(names),
                             (" and %s" % ", ".join(gone)) if gone else "")
