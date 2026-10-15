"""The Tools card on animation layers (2026-10-15).

The animator: «Bake to layer должна создавать новый слой и перекидывать туда анимацию с текущего
выбранного слоя ... опция смены парента не работает если на объекте уже есть слой ... To world тоже
... Давай проверим все инструменты на работоспособность в случае если у нас есть анимационный
слой». Every tool refused a channel an animation layer feeds as «driven by an animation layer».

Measured in mayapy 2027 before this was written:

- a constraint on a layered channel splices Maya's pairBlend in AFTER the top layer's blend node
  (input 1 = the layers' result, input 2 = the constraint) and deleting the constraint gives the
  channel back to the blend node - so a knot rides a layered object as it rides a keyed one;
- `bakeResults` on such a channel bakes into the pairBlend's input 1, a blend node, and lands
  wrong (9.9 cm off on a two-layer cube) - so anything that bakes an object's channels reads what
  the object SHOWS on every frame and keys it as a FINAL value on one layer
  (`setKeyframe -animLayer L -value v`: Maya writes what L needs for the channel to show v -
  measured exact on the base under an additive layer and on an additive layer, at any time);
- a layer's blend node is linked to its layer by `.message -> layer.blendNodes[]`; its own value
  is `inputB` (`inputBX`.. on a rotation blend), what is below it `inputA`.

The layer a tool keys into is the active one, as the Pose Library's (`maya_poselib.keys`): the
selected non-base layer, else BaseAnimation. Other layers keep their curves; the active one takes
whatever the object must show.
"""

import maya.cmds as cmds

from maya_tools import knotplan as plan


def _source_plug(plug):
    found = cmds.listConnections(plug, source=True, destination=False, plugs=True,
                                 skipConversionNodes=True) or []
    return found[0] if found else None


def layer_of(blend):
    """The animation layer a blend node belongs to, or None."""
    found = cmds.listConnections(blend + ".message", source=False, destination=True,
                                 type="animLayer") or []
    return found[0] if found else None


def _suffix(attr):
    """A blend node's output attribute's suffix: '' for `output`, 'X' for `outputX`."""
    return attr[len("output"):] if attr.startswith("output") else ""


_PAIR_INPUT = {"tx": "inTranslateX1", "ty": "inTranslateY1", "tz": "inTranslateZ1",
               "rx": "inRotateX1", "ry": "inRotateY1", "rz": "inRotateZ1"}


def walk(plug, ch, layer=None):
    """(plug, curve, word, layered) for one channel: the plug the value of `layer` lives on
    (None / BaseAnimation: the base - every blend's inputA; another layer: that layer's blend
    inputB), through Maya's pairBlend (input 1) - the time curve feeding it, what else drives
    the channel in words ('' for nothing, a time curve or a constraint), and whether any layer
    stands on it. A layer that does not hold the channel answers (None, None, '', layered)."""
    base = layer is None or layer == cmds.animLayer(query=True, root=True)
    target, layered = plug, False
    for _ in range(64):
        src = _source_plug(target)
        if not src:
            return (target, None, "", layered) if base else (None, None, "", layered)
        node, attr = src.split(".", 1)
        kind = cmds.nodeType(node)
        if kind.startswith("animBlendNode"):
            layered = True
            if not base and layer_of(node) == layer:
                target = "%s.inputB%s" % (node, _suffix(attr))
                found = _source_plug(target)
                if not found:
                    return target, None, "", True
                fnode = found.split(".", 1)[0]
                ftype = cmds.nodeType(fnode)
                if ftype in plan.TIME_CURVES:
                    return target, fnode, "", True
                return target, None, plan.driver_word(ftype, False), True
            target = "%s.inputA%s" % (node, _suffix(attr))
            continue
        if kind == "pairBlend":
            target = "%s.%s" % (node, _PAIR_INPUT[ch])
            continue
        if not base:
            return None, None, "", layered
        if kind in plan.TIME_CURVES:
            return target, node, "", layered
        if cmds.objectType(node, isAType="constraint"):
            return target, None, "", layered
        return target, None, plan.driver_word(kind, False), layered
    return target, None, "", layered


def stack_word(plug):
    """'' when every input of the layers on `plug` is a time curve or a value, else what drives
    one of them, in words: an expression or a driven key inside a layer still refuses."""
    src = _source_plug(plug)
    seen = 0
    while src and seen < 64:
        seen += 1
        node, attr = src.split(".", 1)
        kind = cmds.nodeType(node)
        if not kind.startswith("animBlendNode"):
            if kind in plan.TIME_CURVES:
                return ""
            return plan.driver_word(kind, cmds.objectType(node, isAType="constraint"))
        suffix = _suffix(attr)
        b = _source_plug("%s.inputB%s" % (node, suffix))
        if b:
            btype = cmds.nodeType(b.split(".", 1)[0])
            if btype not in plan.TIME_CURVES and not btype.startswith("animBlendNode"):
                return plan.driver_word(btype, False)
        src = _source_plug("%s.inputA%s" % (node, suffix))
    return ""


def is_layered(obj, channels=plan.CHANNELS):
    """True when an animation layer feeds one of the object's channels (through a knot's
    pairBlend too)."""
    return any(walk(obj + "." + ch, ch)[3] for ch in channels)


def target():
    """(layer name or None, refusal): the layer the press keys into - the active one (the
    selected non-base layer, else BaseAnimation); None with no layers in the scene."""
    from maya_poselib import keys
    layer, refusal = keys.active_layer()
    if refusal:
        return None, refusal
    return (layer.name if layer is not None else None), ""


def check_target(layer, channels):
    """'' or why `layer` cannot take these channels' final values: an additive layer in
    quaternion accumulation cannot take exact rotate keys."""
    if not layer or not any(ch in plan.ROTATE for ch in channels):
        return ""
    if cmds.animLayer(query=True, root=True) == layer:
        return ""
    try:
        quaternion = cmds.getAttr(layer + ".rotationAccumulationMode") == 1
    except (ValueError, RuntimeError):
        quaternion = False
    if quaternion and not cmds.animLayer(layer, query=True, override=True):
        return ("the animation layer %s adds rotation as quaternions - switch it to component "
                "accumulation, or select another layer" % layer)
    return ""


def read(objs, channels, frames):
    """{obj: {frame: {channel: what it shows}}} - one time walk, unrecorded."""
    from maya_poselib import timewalk
    out = dict((obj, {}) for obj in objs)
    with timewalk.Walk(fresh=False) as w:
        for frame in frames:
            w.go(frame)
            for obj in objs:
                out[obj][frame] = dict((ch, cmds.getAttr(obj + "." + ch)) for ch in channels)
    return out


def _continuous(rows, channels, anchor, order):
    """Each frame's rotation the euler nearest the one before (from `anchor`, the frame before
    the span): all three rotates the other solution too, else whole turns."""
    rotates = [ch for ch in plan.ROTATE if ch in channels]
    if not rotates:
        return rows
    if rotates == list(plan.ROTATE):
        made = plan.continuous_eulers(
            tuple(anchor[ch] for ch in plan.ROTATE) if anchor else None,
            [tuple(row[ch] for ch in plan.ROTATE) for row in rows], order)
        for row, euler in zip(rows, made):
            for index, ch in enumerate(plan.ROTATE):
                row[ch] = euler[index]
        return rows
    for ch in rotates:
        made = plan.continuous_channel(anchor[ch] if anchor else None, [row[ch] for row in rows])
        for row, value in zip(rows, made):
            row[ch] = value
    return rows


def key_shown(obj, channels, first, last, shown, layer, ranged=False):
    """`obj`'s channels keyed on `layer` on every frame first..last as FINAL values (`shown`
    {frame: {channel: value}}, read before the drivers came off), the layer's keys inside the
    span replaced. `ranged`: what the layer plays outside the span kept - a key inserted one
    frame outside each end of its curve (the shape kept, those keys and their outer neighbours
    pinned, trap 221), else - the layer had no curve there - the frames outside keyed with what
    the object showed (flat). The number of keys made."""
    from maya_poselib import keys
    from maya_tools import knots
    frames = list(range(int(first), int(last) + 1))
    order = cmds.getAttr(obj + ".rotateOrder")
    anchor = shown.get(frames[0] - 1)
    rows = _continuous([dict(shown[f]) for f in frames], channels, anchor, order)
    lay = layer or None
    made = 0
    for ch in channels:
        plug = obj + "." + ch
        curve = keys.curve_for(plug, lay) if lay else _plain_curve(plug)
        edges = []
        state = keys.curve_state([plug], lay)
        if curve:
            times = cmds.keyframe(curve, query=True, timeChange=True) or []
            if ranged:
                for edge in (first - 1.0, last + 1.0):
                    if not any(abs(t - edge) < 1e-6 for t in times):
                        cmds.setKeyframe(curve, time=edge, insert=True)
                    knots._pin(curve, edge)
                    outer = [t for t in times if (t < edge if edge < first else t > edge)]
                    if outer:
                        knots._pin(curve, max(outer) if edge < first else min(outer))
            inside = [t for t in times if first - 1e-6 <= t <= last + 1e-6]
            if inside:
                cmds.cutKey(curve, time=(first, last), clear=True)
        elif ranged:
            edges = [f for f in (frames[0] - 1, frames[-1] + 1) if f in shown]
        for frame, row in zip(frames, rows):
            made += _key(plug, row[ch], frame, lay)
        for frame in edges:
            made += _key(plug, shown[frame][ch], frame, lay, flat=True)
        if state:
            keys.put_curve_state(state, lay)
    return made


def _plain_curve(plug):
    found = cmds.listConnections(plug, source=True, destination=False,
                                 skipConversionNodes=True) or []
    if found and cmds.nodeType(found[0]) in plan.TIME_CURVES:
        return found[0]
    return None


def _key(plug, value, frame, layer, flat=False):
    kwargs = dict(time=frame, value=float(value))
    if flat:
        kwargs.update(inTangentType="flat", outTangentType="flat")
    if layer:
        if layer != cmds.animLayer(query=True, root=True):
            cmds.animLayer(layer, edit=True, attribute=plug)
        kwargs["animLayer"] = layer
    return int(cmds.setKeyframe(plug, **kwargs) or 0)
