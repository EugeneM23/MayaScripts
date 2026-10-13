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
base keeps its keys outside it and bridges the highlight on its own keys.

The press: the drivers classified before anything changes - our knots come off as Remove takes
them (riders first), the animator's constraints are deleted, and a constraint of the Retarget, of
another card of ours (a weapon link, a hand proxy, the scene camera, a weapon or armor space) or
of the rig itself refuses the whole press by name. One time walk reads what every object shows,
the drivers come off, the base's own curves go (or are bridged), a second walk reads what is left,
and the difference - the shown rotation made continuous from what is left - is keyed on every
frame of the span (the highlight, zero one frame outside it, else the take, anchored at its first
frame). One undo chunk; a refusal changes nothing. Other animation layers stay as they are.

`write_deltas` is the layer writer the Overlap uses too.

Spec: docs/superpowers/specs/2026-10-13-tools-bake-to-layer-design.md (read its addenda)
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

def write_deltas(name, marker, value, tracks, ranged=False, cycled=False):
    """`tracks` {(node, channel): (times, values)} keyed on a new additive layer `name` (marked
    `marker` = `value`, rotation by component); zero one frame outside when `ranged`; cycled
    curves cycle. The layer's name."""
    layer = cmds.animLayer(name)
    knots._set_string(layer, marker, value)
    cmds.setAttr(layer + ".rotationAccumulationMode", 0)          # by component
    plugs = ["%s.%s" % (node, plan.LONG[ch]) for node, ch in tracks]
    cmds.animLayer(layer, edit=True, attribute=plugs)
    for (node, ch), (times, values) in tracks.items():
        plug = "%s.%s" % (node, plan.LONG[ch])
        cmds.setKeyframe(node, attribute=plan.LONG[ch], animLayer=layer, time=times[0],
                         identity=True)
        curve = (cmds.animLayer(layer, query=True, findCurveForPlug=plug) or [None])[0]
        for time, number in zip(times, values):
            cmds.setKeyframe(curve, time=time, value=float(number))
        if ranged:
            for edge in (times[0] - 1, times[-1] + 1):
                cmds.setKeyframe(curve, time=edge, value=0.0, inTangentType="flat",
                                 outTangentType="flat")
        if cycled:
            cmds.setAttr(curve + ".preInfinity", _CYCLE)
            cmds.setAttr(curve + ".postInfinity", _CYCLE)
    return layer


def bake_layers():
    """Our Layer presses' layers (marked; never found by name)."""
    return [layer for layer in cmds.ls(type="animLayer") or []
            if knots._has(layer, plan.LAYER_MARKER)]


# ------------------------------------------------------------------ objects

def _sources(plug):
    return cmds.listConnections(plug, source=True, destination=False,
                                skipConversionNodes=True) or []


def _object_of(node):
    """What a selected node names: a knot (or a node inside one) the object it drives - through a
    knot riding a knot - a constraint the object it constrains, else the node itself; None for a
    waiting pivot."""
    seen = set()
    while True:
        top = knots.top_of(node)
        if not top or top in seen:
            break
        seen.add(top)
        source = knots.source_of(top)
        if not source:
            return None
        node = source
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
    """{constraint: [channels]}: the constraints driving the object's translate and rotate,
    directly or through Maya's pairBlend."""
    constraints = {}
    for ch in plan.CHANNELS:
        found = _sources(obj + "." + ch)
        if not found:
            continue
        node = found[0]
        if cmds.nodeType(node) == "pairBlend":
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
    """(base plug, base curve or None, word, layered) for one channel: the plug the BASE value
    lives on - through Maya's pairBlend (input 1, the object's own) and any animation layer's
    blend node (input A, trap 235) - the time curve feeding it, what else drives it in words
    ('' for nothing or a constraint), and whether a layer stands on it."""
    target, layered = plug, False
    for _ in range(32):
        src = _source_plug(target)
        if not src:
            return target, None, "", layered
        node, attr = src.split(".", 1)
        kind = cmds.nodeType(node)
        if kind.startswith("animBlendNode"):
            layered = True
            target = "%s.inputA%s" % (node, attr[len("output"):])
            continue
        if kind == "pairBlend":
            target = "%s.%s" % (node, knots._BLEND_INPUT[ch])
            continue
        if kind in plan.TIME_CURVES:
            return target, node, "", layered
        if cmds.objectType(node, isAType="constraint"):
            return target, None, "", layered
        return target, None, plan.driver_word(kind, False), layered
    return target, None, "", layered


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
    moving, words, layered = [], {}, False
    for ch in free:
        _plug, curve, word, on_layer = _base(obj + "." + ch, ch)
        layered = layered or on_layer
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
                words=words), ""


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

def _read(objs, frames):
    """{obj: {frame: (tx, ty, tz, rx, ry, rz)}} - one time walk, unrecorded."""
    from maya_poselib import timewalk
    out = dict((obj, {}) for obj in objs)
    with timewalk.Walk(fresh=False) as walk:
        for frame in frames:
            walk.go(frame)
            for obj in objs:
                out[obj][frame] = (tuple(cmds.getAttr(obj + ".translate")[0])
                                   + tuple(cmds.getAttr(obj + ".rotate")[0]))
    return out


def _free(obj):
    return [ch for ch in plan.CHANNELS if not cmds.getAttr(obj + "." + ch, lock=True)]


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


def _bridge(curve, first, last):
    """A highlight `first..last` taken off a base curve: a key one frame outside each end
    (inserted, the shape kept), the keys between them cut - the curve then bridges the
    highlight on those two keys' own tangents."""
    times = cmds.keyframe(curve, query=True, timeChange=True) or []
    for edge in (first - 1.0, last + 1.0):
        if not any(abs(t - edge) < 1e-6 for t in times):
            cmds.setKeyframe(curve, time=edge, insert=True)
    if plan.bridged(times, first, last):
        cmds.cutKey(curve, time=(first - 1.0 + 1e-3, last + 1.0 - 1e-3), clear=True)


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


def _clear_base(info, path, span, shown, now):
    """The base's own animation off one object, inside the press: whole take - each curve that
    moves deleted, the channel (and each channel a driver held) left on its first-frame value;
    a highlight - each such curve bridged, an unkeyed channel a foreign constraint drove kept at
    the current frame's pose (trap 238; a knot's channels have their own value back). The
    channels held that way."""
    first, last, ranged = span
    held = []
    for ch in sorted(set(info["moving"]) | (info["driven"] & set(_free(path)))):
        base_plug, curve, word, _layered = _base(path + "." + ch, ch)
        if word:
            continue
        index = plan.CHANNELS.index(ch)
        if ranged:
            if curve and ch in info["moving"]:
                _bridge(curve, first, last)
            elif not curve and ch in info["held"]:
                cmds.setAttr(base_plug, shown[now][index])
                held.append(ch)
            continue
        if curve and ch in info["moving"]:
            value = cmds.keyframe(curve, query=True, eval=True, time=(first, first))[0]
            cmds.delete(curve)
            cmds.setAttr(base_plug, value)
        elif not curve:
            cmds.setAttr(base_plug, shown[first][index])
    cmds.dgdirty(path)
    return held


def bake(selection=None, highlight=SLIDER):
    """The Layer press. The line."""
    import maya_rigs
    objs, pivots = _objects(selection)
    if not objs:
        return plan.LAYER_NOTHING
    rigs = maya_rigs.rigs()
    plans = []
    for obj in objs:
        info, refusal = _plan(obj, rigs)
        if refusal:
            return refusal
        plans.append(info)
    window = knots._highlight(highlight)
    spans = {}
    for info in plans:
        targets = [t for con in info["foreign"] for t in _targets(con)]
        spans[info["obj"]] = _span(info["obj"], info["tops"], targets, window)
    now = cmds.currentTime(query=True)
    frames = sorted(set(f for first, last, _r in spans.values() for f in range(first, last + 1))
                    | {now})
    uuids = dict((info["obj"], knots._uuid(info["obj"])) for info in plans)
    notes = []
    with knots._press("skeldarBakeLayer"):
        shown = _read(objs, frames)
        knots_off = _knots_off([t for info in plans for t in info["tops"]])
        constraints_off = 0
        for info in plans:
            for con in info["foreign"]:
                if cmds.objExists(con):
                    cmds.delete(con)
                    constraints_off += 1
        live = dict((obj, knots._by_uuid(uuids[obj])) for obj in objs)
        statics = []
        for info in plans:
            path = live[info["obj"]]
            held = _clear_base(info, path, spans[info["obj"]], shown[info["obj"]], now)
            statics += [plan.leaf(path) + "." + ch for ch in held]
        own = _read([live[o] for o in objs], frames)
        tracks, first, last, ranged = {}, None, None, False
        for info in plans:
            obj = info["obj"]
            path = live[obj]
            start, end, ranged = spans[obj]
            times = list(range(start, end + 1))
            minimum = plan.LAYER_MIN if ranged else -1.0
            deltas = plan.layer_deltas([shown[obj][f] for f in times],
                                       [own[path][f] for f in times],
                                       cmds.getAttr(path + ".rotateOrder"), _free(path),
                                       minimum=minimum)
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
        if tracks:
            leaves = [plan.leaf(live[o]) for o in objs]
            layer = write_deltas(plan.layer_name(leaves), plan.LAYER_MARKER, " ".join(leaves),
                                 tracks, ranged=ranged)
        cmds.select([live[o] for o in objs if live[o]], replace=True)
    starts = set(spans[o][0] for o in objs)
    keyed = sum(1 for info in plans if info["moving"])
    return plan.layer_message([plan.leaf(live[o]) for o in objs], keyed, knots_off,
                              constraints_off, first, last, ranged, layer, notes,
                              pose_frame=starts.pop() if len(starts) == 1 else None)
