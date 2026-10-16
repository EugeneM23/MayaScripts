"""The Tools card's Layer (2026-10-13): everything that animates an object, baked onto a new
additive layer.

The animator: «Теперь давай реализуем функционал запекания на адитивный слой»; asked: any object,
whatever drives it (our knot or anybody's constraint), a new layer per press, a third button in the
bottom row (Bake | Layer | Remove). Then, with a plainly keyed object that the first build refused
(«я выделил объект на котором просто ключи нажал леер и он не запекся»), asked: everything goes
onto the layer and the base holds a still pose. OverRig's `>layer` baked onto an OVERRIDE layer
`BakedAnim`; ours bakes onto an ADDITIVE layer `Baked_<leaf>` (marked `skeldarBakeLayer`): the
object's own keys, its knots and its constraints all move there, the base keeps the pose of the
first frame (over the whole take) - mute the layer and the object stands; with a highlight the
base keeps its keys outside it and bridges the highlight on its own keys. Always from the base
(2026-10-15, «Когда запекаем анимацию на слой то давай будем анимацию с базового слоя удалять»): a
layer selected in the Anim Layer Editor does not choose the source, other layers stay as they are.
A selected knot is an object like any other («сам knot не должен удаляться»): its own keys go onto
its own layer and it goes on driving; an object riding a knot has the knot taken off.

The press: the drivers classified before anything changes - our knots come off as Remove takes
them (riders first), the animator's constraints are deleted, and a constraint of the Retarget, of
another card of ours (a weapon link, a hand proxy, the scene camera, a weapon or armor space) or
of the rig itself refuses the whole press by name. One time walk reads what every object shows,
the drivers come off, the base's own curves go (or are bridged), a second walk reads what is left,
and the difference - the shown rotation made continuous from what is left - is keyed (the
highlight, zero one frame outside it, else the take, anchored at its first frame). By keys, not
baked («переносилась по ключам и мы их не теряли»): over the whole take a channel only its own
keys move is the base curve itself moved onto the layer, every key, tangent and infinity kept;
under a highlight its keys inside it move with their values and slopes less the bridge's (a
stepped curve's as they are) - exact between frames too. A driven channel has no keys of its own
and is keyed on every frame. One undo chunk; a refusal changes nothing. Other animation layers
stay as they are.

`write_deltas` is the layer writer the Overlap uses too.

What it costs (2026-10-16, a colleague: «bake to layer иногда вызывает зависание маи»): a press
froze Maya for minutes on a long take - measured in mayapy on a 692-frame retargeted take, one
constrained control among 65 selected 38 s (all 65 read on every frame of both walks), a highlight
over the 65 92 s (two walks and 1.6 million cmds calls, a bridge read key by key), with the
viewport suspended and nothing on screen. Now each walk reads only the objects it samples
(`knotplan.layer_reads`), a channel that bridges exactly is known before the walk
(`knotplan.bridge_plan`) and needs none, what is left once the drivers are off is read off its
own curves unless a layer stands on it (no second walk), a bridge reads its curve in a few
queries whatever its key count, and a press that walks or bridges much shows Maya's progress
window: Esc undoes it, and so is a press that fails. On the way: Maya's insert past a curve's
keys re-types the key beside it - an edge there is read on every frame and a stepped key keeps
its hold (a blocking curve's base outside the highlight went smooth, 2.98 off).

Spec: docs/superpowers/specs/2026-10-13-tools-bake-to-layer-design.md (read its addenda) and
2026-10-15-layer-knot-and-base-design.md
"""

import math
import re

import maya.cmds as cmds

from maya_tools import knotplan as plan
from maya_tools import knots
from maya_tools import reparent

SLIDER = knots.SLIDER
_CYCLE = 3                     # an animCurve's pre / post infinity: cycle
#  The object itself is ours: a space that follows a hand or a bone (the Weapons and Armor cards).
_OUR_SPACES = ("mayaWeaponSpace", "mayaArmorSpace")
#  A bone following one of these is driven by the plugin (a weapon in the hand or on the floor,
#  the scene camera); a prop the animator constrained to the sword is not.
_BONE_DRIVERS = ("mayaWeapon", "mayaSceneSetupCamera")
#  A constraint's own weight attributes (`<target>W0`) are named for its targets, never ours.
_WEIGHT = re.compile(r"W\d+$")
_BLEND_INPUT2 = {"tx": "inTranslateX2", "ty": "inTranslateY2", "tz": "inTranslateZ2",
                 "rx": "inRotateX2", "ry": "inRotateY2", "rz": "inRotateZ2"}


# ------------------------------------------------------------------- writer

def write_deltas(name, marker, value, tracks, ranged=False, cycled=False, moves=None, step=None):
    """`tracks` {(node, channel): (times, values[, {time: (in, out)}])} keyed on a new additive
    layer `name` (marked `marker` = `value`, rotation by component) - a tangent type None is
    Maya's default; zero one frame outside when `ranged`; cycled curves cycle. `moves`
    {(node, channel): (curve, value)}: the base curve itself moved onto the layer (`_move`), the
    base left on `value`. `step(text)` after each channel (the press's progress). The layer's
    name."""
    moves = moves or {}
    layer = cmds.animLayer(name)
    knots._set_string(layer, marker, value)
    cmds.setAttr(layer + ".rotationAccumulationMode", 0)          # by component
    #  scale ADDED, not multiplied (Maya's default, 1): the layer holds the difference, 0 its
    #  identity - set before the first key, or the identity key is 1
    cmds.setAttr(layer + ".scaleAccumulationMode", 0)
    plugs = ["%s.%s" % (node, plan.LONG[ch]) for node, ch in list(tracks) + list(moves)]
    cmds.animLayer(layer, edit=True, attribute=plugs)
    for (node, ch), track in tracks.items():
        times, values = track[0], track[1]
        tangents = track[2] if len(track) > 2 else {}
        plug = "%s.%s" % (node, plan.LONG[ch])
        cmds.setKeyframe(node, attribute=plan.LONG[ch], animLayer=layer, time=times[0],
                         identity=True)
        curve = (cmds.animLayer(layer, query=True, findCurveForPlug=plug) or [None])[0]
        for time, number in zip(times, values):
            kind = tangents.get(time, (None, None))
            edit = dict((flag, k) for flag, k in zip(
                ("inTangentType", "outTangentType"), kind[:2]) if k)
            if len(kind) > 2:                  # an exact key: its slopes, as angles a frame
                edit.update(inAngle=kind[2], outAngle=kind[3])
            #  the types through keyTangent: setKeyframe takes no "fixed", and on a key already
            #  there (the identity key at the first time) it leaves the types as they were. One
            #  edit sets the types and the angles together, exactly as two did (measured)
            cmds.setKeyframe(curve, time=time, value=float(number))
            if edit:
                cmds.keyTangent(curve, time=(time, time), lock=False, **edit)
        if ranged:
            for edge in (times[0] - 1, times[-1] + 1):
                cmds.setKeyframe(curve, time=edge, value=0.0, inTangentType="flat",
                                 outTangentType="flat")
        if cycled:
            cmds.setAttr(curve + ".preInfinity", _CYCLE)
            cmds.setAttr(curve + ".postInfinity", _CYCLE)
        if step is not None:
            step("keying %s.%s" % (plan.leaf(node), plan.LONG[ch]))
    for (node, ch), (curve, held) in moves.items():
        _move(node, ch, curve, held)
        if step is not None:
            step("moving %s.%s" % (plan.leaf(node), plan.LONG[ch]))
    return layer


def _move(node, ch, curve, held):
    """The base curve of `node.ch` moved onto the layer just added on top of it: off the base
    (the plug it feeds under every layer's blend), onto that layer's blend input B, its values
    shifted by `held`, which the base then holds - every key, tangent, weight and infinity
    kept (measured: the layer finds it as its own curve)."""
    plug = "%s.%s" % (node, plan.LONG[ch])
    base_plug, _curve, _word, _layered = _base(plug, ch)
    real = cmds.listConnections(base_plug, source=True, destination=False, plugs=True) or []
    if real:
        cmds.disconnectAttr(real[0], base_plug)
    top, attr = _source_plug(plug).split(".", 1)
    cmds.connectAttr(curve + ".output", "%s.inputB%s" % (top, attr[len("output"):]))
    cmds.setAttr(base_plug, held)
    if abs(held) > 1e-12:
        cmds.keyframe(curve, edit=True, relative=True, valueChange=-held)


def bake_layers():
    """Our Layer presses' layers (marked; never found by name)."""
    return [layer for layer in cmds.ls(type="animLayer") or []
            if knots._has(layer, plan.LAYER_MARKER)]


# ------------------------------------------------------------------ objects

def _sources(plug):
    return cmds.listConnections(plug, source=True, destination=False,
                                skipConversionNodes=True) or []


def _object_of(node):
    """What a selected node names: a constraint the object it constrains, a waiting pivot nothing
    (None), anything else itself - a knot's node too (its top, a double knot's inner, an aim's
    target or up, a snapshot): a knot is baked as an object like any other and stays (2026-10-15,
    «сам knot не должен удаляться»)."""
    if knots.pending_of(node):
        return None
    if cmds.objectType(node, isAType="constraint"):
        parent = knots._parent(node)
        return parent if parent and cmds.objectType(parent, isAType="transform") else None
    return node


def _objects(selection):
    """(objects, skipped pivots) the selection names, long paths, no repeats."""
    out, pivots = [], 0
    for node in knots._selection(selection):
        obj = _object_of(node)
        if obj is None:
            pivots += 1
            continue
        if obj not in out:
            out.append(obj)
    return out, pivots


def _drivers(obj):
    """{constraint: [channels]}: the constraints driving the object's free translate, rotate and
    scale channels, directly or through Maya's pairBlend (never on scale). A locked channel is left alone: Knot Orient's
    kept point constraint rides its locked translate and is the knot's own."""
    constraints = {}
    for ch in _free(obj):
        found = _sources(obj + "." + ch)
        if not found:
            continue
        node = found[0]
        if cmds.nodeType(node) == "pairBlend" and ch in _BLEND_INPUT2:
            upstream = _sources(node + "." + _BLEND_INPUT2[ch])
            if upstream and cmds.objectType(upstream[0], isAType="constraint"):
                constraints.setdefault(_long(upstream[0]), []).append(ch)
            continue
        if cmds.objectType(node, isAType="constraint"):
            constraints.setdefault(_long(node), []).append(ch)
    return constraints


def _source_plug(plug):
    found = cmds.listConnections(plug, source=True, destination=False, plugs=True,
                                 skipConversionNodes=True) or []
    return found[0] if found else None


def _base(plug, ch):
    """(plug, curve or None, word, layered) for one channel: the plug the base's value lives on
    (through Maya's pairBlend, input 1, and every layer's blend node, input A, trap 235;
    `layered.walk`), the time curve feeding it, what else drives it in words ('' for nothing or a
    constraint), and whether a layer stands on it."""
    from maya_tools import layered
    return layered.walk(plug, ch, None)


def _moves(curve):
    values = cmds.keyframe(curve, query=True, valueChange=True) or []
    return not plan.is_constant(values)


def _long(node):
    return knots._long(node) or node


def _targets(constraint):
    try:
        found = getattr(cmds, cmds.nodeType(constraint))(constraint, query=True,
                                                         targetList=True) or []
    except Exception:                                           # noqa: BLE001
        found = [n for n in cmds.listConnections(constraint + ".target", source=True,
                                                 destination=False) or []
                 if n != constraint.split("|")[-1]]
    return [p for p in (knots._long(t) for t in found) if p]


def _ours(constraint):
    """True when the constraint carries one of our attributes (Connections' link, the
    Retarget's stretch follow) - its weight attributes, named for its targets, aside."""
    for attr in cmds.listAttr(constraint, userDefined=True) or []:
        if not _WEIGHT.search(attr) and attr.startswith(reparent.OUR_PREFIXES):
            return True
    return False


def _plugins_own(constraint, obj, targets):
    """True for a constraint one of our cards made: marked; driving a weapon or armor space; or
    a bone following a weapon or the scene camera."""
    if _ours(constraint) or any(knots._has(obj, m) for m in _OUR_SPACES):
        return True
    if cmds.objectType(obj, isAType="joint"):
        return any(knots._has(t, m) for t in targets for m in _BONE_DRIVERS)
    return False


def _held(constraint):
    """True when the Retarget's holder switches the constraint (its `disableConstraints`)."""
    plugs = cmds.listConnections(constraint + ".nodeState", source=True, destination=False,
                                 plugs=True) or []
    return any(p.endswith(".disableConstraints") for p in plugs)


def _in_rig(path, rig):
    import maya_rigs
    return maya_rigs.under(path, rig.group) or maya_rigs.under(path, rig.skeleton_root)


def _rigs_own(constraint, obj, targets, rigs):
    """True for the rig's own constraint: in a rig's namespace; for a root-namespace rig, the
    object and every target under its group or skeleton."""
    import maya_rigs
    namespace = maya_rigs.namespace_of(constraint)
    for rig in rigs:
        if rig.namespace:
            if namespace == rig.namespace:
                return True
        elif _in_rig(obj, rig) and targets and all(_in_rig(t, rig) for t in targets):
            return True
    return False


def _plan(obj, rigs):
    """(plan, refusal) for one object. The plan: the knots and the foreign constraints on it,
    the channels they drive (`held`: those a foreign constraint drives - an unkeyed one keeps
    nothing of its old value, trap 238; a knot gives its back), the free channels whose own (base)
    curve moves, what else drives a channel, in words."""
    name = obj.split("|")[-1]
    free = _free(obj)
    tops, foreign, driven, held = [], {}, set(), set()
    for con, channels in _drivers(obj).items():
        if knots._has(con, plan.OF_MARKER):
            #  our knot's - or, its knot deleted by hand, an orphan of ours: deleted
            top = knots._by_uuid(knots._get(con, plan.OF_MARKER))
            kind = "knot" if top else "foreign"
        else:
            targets = _targets(con)
            kind = plan.driver_kind(False, _held(con), _plugins_own(con, obj, targets),
                                    _rigs_own(con, obj, targets, rigs))
        refusal = plan.driver_refusal(kind, name, con.split("|")[-1])
        if refusal:
            return None, refusal
        if kind == "knot":
            if top not in tops:
                tops.append(top)
        else:
            foreign[con] = channels
            held.update(channels)
        driven.update(channels)
    moving, words, layered, curves = [], {}, False, {}
    for ch in free:
        _plug, curve, word, on_layer = _base(obj + "." + ch, ch)
        layered = layered or on_layer
        if curve:
            curves[ch] = curve
        if word:
            words[ch] = word
        elif curve and _moves(curve):
            if cmds.referenceQuery(curve, isNodeReferenced=True):
                return None, ("%s: its %s keys come from a reference (%s) - Layer cannot move "
                              "them" % (name, ch, curve))
            moving.append(ch)
    if not tops and not foreign and not moving:
        return None, plan.undriven_refusal(name, list(words.values()), layered)
    return dict(obj=obj, tops=tops, foreign=foreign, driven=driven, held=held, moving=moving,
                words=words, curves=curves), ""


# --------------------------------------------------------------------- span

def _keys(nodes):
    return cmds.keyframe(nodes, query=True, timeChange=True) or [] if nodes else []


def _span(obj, tops, targets, highlight):
    """(first, last, ranged) whole frames: the highlight `[a, b)` as `a..b-1`; else the take -
    the playback and animation ranges with the keys of the object, of everything above it, of
    its constraints' targets (and theirs) and of its knots."""
    if highlight and highlight[1] - highlight[0] > 1:
        return int(round(highlight[0])), int(round(highlight[1])) - 1, True
    nodes = knots._chain(obj)
    for target in targets:
        nodes += [n for n in knots._chain(target) if n not in nodes]
    times = _keys(nodes)
    for top in tops:
        times += knots._knot_keys(top)
    take = plan.take_range((cmds.playbackOptions(query=True, min=True),
                            cmds.playbackOptions(query=True, max=True)),
                           (cmds.playbackOptions(query=True, animationStartTime=True),
                            cmds.playbackOptions(query=True, animationEndTime=True)))
    span = plan.span_for(take, times, None)
    return int(math.floor(span[0])), int(math.ceil(span[1])), False


# ------------------------------------------------------------------ reading

class _Cancelled(Exception):
    """Esc in the press's progress window."""


def _read(reads, step=None):
    """({obj: {frame: (tx, ty, tz, rx, ry, rz, sx, sy, sz)}}, the walk's `keys.Tweaks` or None):
    each object read on its own frames only (`reads` {obj: frames}, `knotplan.layer_reads`) - one
    time walk over their union, unrecorded; no walk when nothing is to be read. `step(text)`
    after each frame; it raises `_Cancelled` on Esc, and the walk puts the time back first."""
    from maya_poselib import timewalk
    out = dict((obj, {}) for obj in reads)
    by_frame = {}
    for obj, frames in reads.items():
        for frame in frames:
            by_frame.setdefault(frame, []).append(obj)
    if not by_frame:
        return out, None
    frames = sorted(by_frame)
    with timewalk.Walk(fresh=False) as walk:
        for count, frame in enumerate(frames):
            walk.go(frame)
            for obj in by_frame[frame]:
                out[obj][frame] = (tuple(cmds.getAttr(obj + ".translate")[0])
                                   + tuple(cmds.getAttr(obj + ".rotate")[0])
                                   + tuple(cmds.getAttr(obj + ".scale")[0]))
            if step is not None:
                step("frame %g (%d of %d)" % (frame, count + 1, len(frames)))
        tweaks = walk.tweaks
    return out, tweaks


def _free(obj):
    return [ch for ch in plan.LAYER_CHANNELS if not cmds.getAttr(obj + "." + ch, lock=True)]


#  The time curve a channel's own keys are, by the channel's kind.
_CURVE_KIND = dict([(ch, "animCurveTL") for ch in ("tx", "ty", "tz")]
                   + [(ch, "animCurveTA") for ch in ("rx", "ry", "rz")]
                   + [(ch, "animCurveTU") for ch in ("sx", "sy", "sz")])


def _plain_left(path, channels):
    """{channel: (curve, None) or (None, value)} when what is left on each of `channels`, once
    the drivers are off, is its own time curve wired straight to it, or a plain value - else None
    (a layer stands on it, a conversion sits between, something else drives it): then the second
    walk reads the scene. Read off the curves it costs no walk (2026-10-16)."""
    out = {}
    for ch in channels:
        plug = path + "." + ch
        found = cmds.listConnections(plug, source=True, destination=False, plugs=True) or []
        if not found:
            out[ch] = (None, cmds.getAttr(plug))
            continue
        node = found[0].split(".", 1)[0]
        if cmds.nodeType(node) != _CURVE_KIND[ch]:
            return None
        out[ch] = (node, None)
    return out


def _left_rows(left, frames):
    """{frame: row} of what `_plain_left` found - the curves evaluated at `frames` (one query a
    curve), the plain values as they are; a channel not asked for is 0 (`layer_deltas` reads only
    the channels it keys)."""
    columns = {}
    for ch, (curve, value) in left.items():
        columns[ch] = _evs(curve, frames) if curve else None
    rows = {}
    for frame in frames:
        rows[frame] = tuple((columns[ch][frame] if columns[ch] is not None else left[ch][1])
                            if ch in left else 0.0 for ch in plan.LAYER_CHANNELS)
    return rows


# -------------------------------------------------------------------- press

def _knots_off(tops):
    """Our knots taken off as Remove takes them (riders first): constraints deleted, the static
    keys we set cut, the knots deleted. How many."""
    count = 0
    for uuid in knots._ordered(knots._with_riders(tops)):
        top = knots._by_uuid(uuid)
        if not top:
            continue
        obj = knots.source_of(top)
        if obj:
            mine = [c for c in knots.constraints_of(obj) if knots._get(c, plan.OF_MARKER) == uuid]
            if mine:
                cmds.delete(mine)
            for ch, value in plan.decode_keyed(knots._get(top, plan.KEYED_MARKER)).items():
                knots._unkey(obj, ch, value)
        knots._delete_knot(top)
        count += 1
    knots._prune()
    return count


def _ev(curve, time):
    return cmds.keyframe(curve, query=True, eval=True, time=(time, time))[0]


def _evs(curve, times):
    """{time: value} of the curve at `times`, UI units - ONE query (`keyframe -eval` takes many
    times, measured equal to one query a time)."""
    times = sorted(set(times))
    if not times:
        return {}
    values = cmds.keyframe(curve, query=True, eval=True, time=[(t, t) for t in times]) or []
    if len(values) != len(times):
        raise RuntimeError("%s answered %d values for %d times" % (curve, len(values),
                                                                    len(times)))
    return dict(zip(times, values))


def _slopes(curve, time):
    """(in, out) slope of a key, UI units a frame (its tangent angle's tangent - measured)."""
    angles = [cmds.keyTangent(curve, time=(time, time), query=True, **{flag: True})[0]
              for flag in ("inAngle", "outAngle")]
    return tuple(math.tan(math.radians(a)) for a in angles)


def _keys_in(curve, window):
    """[(time, in slope, out slope)] of the curve's keys in `window`, in order - three queries
    whatever the number of keys (slopes as `_slopes`)."""
    times = cmds.keyframe(curve, query=True, timeChange=True, time=window) or []
    ins = cmds.keyTangent(curve, query=True, inAngle=True, time=window) or []
    outs = cmds.keyTangent(curve, query=True, outAngle=True, time=window) or []
    return [(t, math.tan(math.radians(a)), math.tan(math.radians(b)))
            for t, a, b in zip(times, ins, outs)]


def _insert(curve, time, times, outs):
    """A key inserted at `time`, the shape kept (Maya's insert) - and a stepped key beside it
    given its hold back: inserted before the first key, Maya turns that key's `step` fixed
    (measured in 2027), and the segment after it, which may lie outside the highlight, smooth -
    2.98 off over a 0..5 blocking curve. `times` / `outs` the keys as they stood."""
    cmds.setKeyframe(curve, time=time, insert=True)
    before = [i for i, t in enumerate(times) if t < time]
    after = [i for i, t in enumerate(times) if t > time]
    for i in before[-1:] + after[:1]:
        if outs[i] in ("step", "stepnext"):
            at = (times[i], times[i])
            if cmds.keyTangent(curve, time=at, query=True, outTangentType=True)[0] != outs[i]:
                cmds.keyTangent(curve, time=at, outTangentType=outs[i])


def _bridge_kind(curve, first, last):
    """How `curve` bridges a highlight `first..last` - "smooth", "stepped" or None (keyed on
    every frame instead) - read off it as it stands, before anything changes
    (`knotplan.bridge_plan`): told before the walk, a channel that bridges exactly needs none,
    and `_bridge` goes by the same answer."""
    times = cmds.keyframe(curve, query=True, timeChange=True) or []
    outs = cmds.keyTangent(curve, query=True, outTangentType=True) or []
    default = (cmds.keyTangent(query=True, g=True, outTangentType=True) or ["auto"])[0]
    weighted = bool((cmds.keyTangent(curve, query=True, weightedTangents=True) or [False])[0])
    return plan.bridge_plan(times, outs, weighted, first, last, default)


def _bridge(curve, first, last):
    """A highlight `first..last` taken off a base curve: a key one frame outside each end
    (inserted, the shape kept, its tangents and its outer neighbour's pinned so nothing outside
    moves, trap 221), the keys between them cut - the curve then bridges the highlight on those
    two keys' tangents. The layer's keys that give back exactly what it showed over the highlight
    ([(time, value, (in type, out type[, in angle, out angle]))]: a smooth curve's keys with their
    slopes minus the bridge's, a stepped curve's as they are with the bridge holding still), or
    None (weighted, steps mixed in) - then it is keyed on every frame of the highlight.

    Its curve is read in a handful of queries whatever its key count (2026-10-16: key by key it
    was ten calls a key, 44 s for 65 controls' dense keys over 670 frames). How it bridges is
    told before a key is inserted (`_bridge_kind`, the answer the press planned its walk by):
    an edge past the curve's keys is never bridged from them - Maya's insert there re-types the
    key beside it."""
    kind = _bridge_kind(curve, first, last)
    edges = (first - 1.0, last + 1.0)
    times = cmds.keyframe(curve, query=True, timeChange=True) or []
    outs = cmds.keyTangent(curve, query=True, outTangentType=True) or []
    for edge in edges:
        if not any(abs(t - edge) < 1e-6 for t in times):
            _insert(curve, edge, times, outs)
        knots._pin(curve, edge)
        outer = [t for t in times if (t < edge if edge < first else t > edge)]
        if outer:
            knots._pin(curve, max(outer) if edge < first else min(outer))
    window = (edges[0] - 1e-6, edges[1] + 1e-6)
    keys = _keys_in(curve, window)
    span = [t for t, _si, _so in keys]
    values = _evs(curve, span)
    original = [(t, values[t], si, so) for t, si, so in keys]
    if plan.bridged(span, first, last):
        cmds.cutKey(curve, time=(edges[0] + 1e-3, edges[1] - 1e-3), clear=True)
    if kind == "stepped":
        cmds.keyTangent(curve, time=(edges[0], edges[0]), outTangentType="step")
        still = _ev(curve, edges[0])
        return [(t, (v - still) if edges[0] < t < edges[1] else 0.0, (None, "step"))
                for t, v, _si, _so in original]
    if kind != "smooth":
        return None
    h = 1e-3
    inner = [t for t in span if edges[0] < t < edges[1]]
    at = _evs(curve, span + [t + h for t in inner] + [t - h for t in inner])
    ends = _keys_in(curve, window)                      # the cut leaves the two edge keys

    def end_slopes(t):
        found = [(si, so) for k, si, so in ends if abs(k - t) < 1e-6]
        if not found:
            raise RuntimeError("%s lost its key at %g bridging %g-%g" % (curve, t, first, last))
        return found[0]

    bridge = []
    for t in span:
        if edges[0] < t < edges[1]:
            slope = (at[t + h] - at[t - h]) / (2.0 * h)
            bridge.append((at[t], slope, slope))
        else:
            bridge.append((at[t],) + end_slopes(t))
    return [(t, v, ("fixed", "fixed", math.degrees(math.atan(si)), math.degrees(math.atan(so))))
            for t, v, si, so in plan.bridge_keys(original, bridge)]


def _shift(path, ch, amount):
    """The base of one channel moved by `amount` (its curve's keys, else its static value)."""
    base_plug, curve, word, _layered = _base(path + "." + ch, ch)
    if word:
        return False
    if curve:
        cmds.keyframe(curve, edit=True, relative=True, valueChange=amount)
    else:
        cmds.setAttr(base_plug, cmds.getAttr(base_plug) + amount)
    return True


def _shared(curve):
    """True when the curve feeds more than one plug (moving it would take it from the others)."""
    return len(cmds.listConnections(curve + ".output", source=False, destination=True,
                                    plugs=True) or []) > 1


def _sorting(info, span):
    """(moved, sampled, exact): the channels whose base curve moves onto the layer whole - over
    the whole take, a channel only its own keys move (not driven, its curve feeding nothing else);
    under a highlight those a plain curve of its own bridges exactly (`_bridge_kind`, told before
    anything changes) - and the rest, read off the scene on every frame of the span: a driven
    channel (it has no keys of its own: a knot is keyed on every frame itself, and a constraint's
    turns between its targets' keys would be lost), a plain one whose bridge cannot be exact."""
    free = set(_free(info["obj"]))
    wanted = (set(info["moving"]) | info["driven"]) & free
    if span[2]:
        exact = set(ch for ch in info["moving"] if ch in free and ch not in info["driven"]
                    and _bridge_kind(info["curves"][ch], span[0], span[1]) is not None)
        return set(), wanted - exact, exact
    moved = set(ch for ch in info["moving"] if ch not in info["driven"] and ch in free
                and not _shared(info["curves"][ch]))
    return moved, wanted - moved, set()


def _clear_base(info, path, span, shown, now, moved=(), exact=None, step=None):
    """The base's own animation off one object, inside the press: whole take - each curve that
    moves deleted, the channel (and each channel a driver held) left on its first-frame value;
    a highlight - each such curve bridged (the exact layer keys of a channel nothing drives kept in
    `exact`), an unkeyed channel a foreign constraint drove kept at the current frame's pose (trap
    238; a knot's channels have their own value back). `step(text)` after each bridge. The
    channels held that way."""
    first, last, ranged = span
    held = []
    for ch in sorted(set(info["moving"]) | (info["driven"] & set(_free(path)))):
        if ch in moved:
            continue                       # the curve itself goes onto the layer, after the walk
        base_plug, curve, word, _layered = _base(path + "." + ch, ch)
        if word:
            continue
        index = plan.LAYER_CHANNELS.index(ch)
        if ranged:
            if curve and ch in info["moving"]:
                keys = _bridge(curve, first, last)
                if keys is not None and exact is not None and ch not in info["driven"]:
                    exact[ch] = keys
                if step is not None:
                    step("bridging %s.%s" % (plan.leaf(path), plan.LONG[ch]))
            elif not curve and ch in info["held"]:
                cmds.setAttr(base_plug, shown[now][index])
                held.append(ch)
            continue
        if curve and ch in info["moving"]:
            value = cmds.keyframe(curve, query=True, eval=True, time=(first, first))[0]
            if _shared(curve):              # it animates another plug too: only let go of this one
                real = cmds.listConnections(base_plug, source=True, destination=False,
                                            plugs=True) or []
                if real:
                    cmds.disconnectAttr(real[0], base_plug)
            else:
                cmds.delete(curve)
            cmds.setAttr(base_plug, value)
        elif not curve:
            cmds.setAttr(base_plug, shown[first][index])
    cmds.dgdirty(path)
    return held


def _plans(objs, rigs):
    plans = []
    for obj in objs:
        info, refusal = _plan(obj, rigs)
        if refusal:
            return None, refusal
        plans.append(info)
    return plans, ""


#  A press with fewer steps than this (frames walked, curves bridged, channels keyed) shows no
#  progress window: it is over before one would be read.
PROGRESS_MIN = 60
PROGRESS_TITLE = "Layer"
#  The chunk's first step, so a cancel or a failure undoes the press and never the step before it.
_CHUNK = "skeldarBakeLayer"


class _Silent(object):
    """No progress window: every step goes on."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def step(self, _text=""):
        return True


def _progress(total):
    """Maya's progress window (Esc stops it, `timewalk.Progress`) for a press of `total` steps -
    none below `PROGRESS_MIN`."""
    if total < PROGRESS_MIN:
        return _Silent()
    from maya_poselib import timewalk
    return timewalk.Progress(PROGRESS_TITLE, total)


def _union(reads):
    return set(f for frames in reads.values() for f in frames)


def bake(selection=None, highlight=SLIDER, name=None, cancellable=True):
    """The Layer press. The line. `name`: the layer's (1P Setup's), else `Baked_<first leaf>`.

    `cancellable`: a long press shows Maya's progress window and Esc undoes it (`LAYER_CANCELLED`),
    a press that fails is undone before its error goes on. False inside another press's chunk -
    1P Setup's - which no Ctrl+Z from here can take apart: no window, nothing undone (as before)."""
    import maya_rigs
    objs, pivots = _objects(selection)
    if not objs:
        return plan.LAYER_NOTHING
    plans, refusal = _plans(objs, maya_rigs.rigs())
    if refusal:
        return refusal
    window = knots._highlight(highlight)
    spans, sorts = {}, {}
    for info in plans:
        obj = info["obj"]
        targets = [t for con in info["foreign"] for t in _targets(con)]
        spans[obj] = _span(obj, info["tops"], targets, window)
        sorts[obj] = _sorting(info, spans[obj])
    now = cmds.currentTime(query=True)
    reads, reads_after = plan.layer_reads(dict((o, spans[o]) for o in objs),
                                          set(o for o in objs if sorts[o][1]), now)
    bridges = sum(len(info["moving"]) for info in plans if spans[info["obj"]][2])
    channels = sum(len(sorts[o][0]) + len(sorts[o][1]) + len(sorts[o][2]) for o in objs)
    total = len(_union(reads)) + len(_union(reads_after)) + bridges + channels
    with (_progress(total) if cancellable else _Silent()) as progress:
        def step(text):
            if not progress.step("Layer: " + text):
                raise _Cancelled()
            return True
        try:
            shown, tweaks = _read(reads, step)           # nothing has changed yet
        except _Cancelled:
            return plan.LAYER_CANCELLED
        recording = cancellable and bool(cmds.undoInfo(query=True, state=True))
        #  with undo off a press that has begun cannot be taken back: Esc goes unheard then
        inside = step if recording else (lambda text: progress.step("Layer: " + text))
        begun = []                         # the chunk holds a step of the press: undo takes it
        try:
            return _press(plans, objs, spans, sorts, shown, reads_after, now, pivots, name,
                          inside, recording, begun)
        except _Cancelled:
            _take_back(begun, tweaks)
            return plan.LAYER_CANCELLED
        except Exception:
            _take_back(begun, tweaks)
            raise


def _take_back(begun, tweaks):
    """A press cancelled or failed inside its chunk: the chunk undone - only once it holds a
    step of the press, never the animator's step before it - and the tweaks the first walk
    found set back."""
    if not begun:
        return
    cmds.undo()
    if tweaks is not None:
        tweaks.restore()


def _press(plans, objs, spans, sorts, shown, reads_after, now, pivots, name, step, recording,
           begun):
    """The press's changes, in its undo chunk (its first step a select when `recording`, told
    in `begun`, so a cancel or a failure undoes the press alone). The line."""
    uuids = dict((info["obj"], knots._uuid(info["obj"])) for info in plans)
    notes = []
    with knots._press(_CHUNK):
        if recording:
            cmds.select(objs, replace=True)
            begun.append(True)
        knots_off = _knots_off([t for info in plans for t in info["tops"]])
        constraints_off = 0
        for info in plans:
            for con in info["foreign"]:
                if cmds.objExists(con):
                    cmds.delete(con)
                    constraints_off += 1
        live = dict((obj, knots._by_uuid(uuids[obj])) for obj in objs)
        statics, exacts = [], {}
        for info in plans:
            path = live[info["obj"]]
            exact = exacts.setdefault(info["obj"], {})
            held = _clear_base(info, path, spans[info["obj"]], shown.get(info["obj"], {}), now,
                               sorts[info["obj"]][0], exact, step)
            statics += [plan.leaf(path) + "." + ch for ch in held]
            lost = sorted(sorts[info["obj"]][2] - set(exact))
            if lost:            # told exact before the walk, not exact now: nothing read for it
                raise RuntimeError("Layer: %s %s did not bridge as its keys said" % (
                    plan.leaf(path), ", ".join(lost)))
        #  what is left: off its own curves where nothing else stands on the channels, else a
        #  second walk of the scene
        own, walk = {}, {}
        for o, frames in reads_after.items():
            left = _plain_left(live[o], sorted(sorts[o][1] - set(exacts.get(o, {}))))
            if left is None:
                walk[live[o]] = frames
                continue
            own[live[o]] = _left_rows(left, frames)
            step("reading what is left of %s" % plan.leaf(live[o]))
        walked, _tweaks = _read(walk, step)
        own.update(walked)
        tracks, moves, first, last, ranged = {}, {}, None, None, False
        for info in plans:
            obj = info["obj"]
            path = live[obj]
            start, end, ranged = spans[obj]
            moved, sampled, _exact = sorts[obj]
            for ch in moved:
                curve = info["curves"][ch]
                moves[(path, ch)] = (curve, cmds.keyframe(curve, query=True, eval=True,
                                                          time=(start, start))[0])
            for ch, keys in exacts.get(obj, {}).items():
                values = [v for _t, v, _k in keys]
                slopes = [abs(k[2]) + abs(k[3]) for _t, _v, k in keys if len(k) > 2]
                if max([abs(v) for v in values] + slopes) > plan.LAYER_MIN:
                    tracks[(path, ch)] = ([t for t, _v, _k in keys], values,
                                          dict((t, k) for t, _v, k in keys))
            sampled = sampled - set(exacts.get(obj, {}))
            if sampled:
                times = list(range(start, end + 1))
                minimum = plan.LAYER_MIN if ranged else -1.0
                deltas = plan.layer_deltas([shown[obj][f] for f in times],
                                           [own[path][f] for f in times],
                                           cmds.getAttr(path + ".rotateOrder"),
                                           [ch for ch in plan.LAYER_CHANNELS if ch in sampled],
                                           minimum=minimum, channels=plan.LAYER_CHANNELS)
                if not ranged:
                    deltas, shifts = plan.anchored(deltas)
                    for ch, amount in shifts.items():
                        if abs(amount) > 1e-9:
                            _shift(path, ch, amount)
                for ch, values in deltas.items():
                    tracks[(path, ch)] = (times, values)
            first = start if first is None else min(first, start)
            last = end if last is None else max(last, end)
            if info["words"]:
                notes.append("%s: %s left as %s" % (
                    plan.leaf(path), ", ".join(sorted(info["words"])),
                    " / ".join(sorted(set(info["words"].values())))))
        if statics:
            notes.append("%s had no keys of %s own - held at frame %s under the layer" % (
                ", ".join(statics), "its" if len(statics) == 1 else "their", "%g" % now))
        if pivots:
            notes.append("a waiting pivot is not baked - press Finish or Remove it")
        layer = ""
        if tracks or moves:
            leaves = [plan.leaf(live[o]) for o in objs]
            layer = write_deltas(name or plan.layer_name(leaves), plan.LAYER_MARKER, " ".join(leaves),
                                 tracks, ranged=ranged, moves=moves, step=step)
        cmds.select([live[o] for o in objs if live[o]], replace=True)
    starts = set(spans[o][0] for o in objs)
    keyed = sum(1 for info in plans if info["moving"])
    return plan.layer_message([plan.leaf(live[o]) for o in objs], keyed, knots_off,
                              constraints_off, first, last, ranged, layer, notes,
                              pose_frame=starts.pop() if len(starts) == 1 else None)
