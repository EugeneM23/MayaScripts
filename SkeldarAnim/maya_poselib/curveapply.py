"""The Pose Library's paste of ORIGINAL curves (2026-10-28): the card's own keys, layer by layer,
onto its own rig model - `animapply` hands a press here when its options say
`paste_as="curves"` and the card holds curves (`curvedata.has_curves`).

The animator: «...сохранения по слоям и сохранения ключей». The press:
1. the layers: the picked card layers (`curvedata.chosen`, the card's order), each paired with the
   target scene's (`curvedata.layer_target`): the base to the root (the plain curves without
   layers), a namesake of the same mode and rotation accumulation taken, a locked one REFUSED
   before anything is written, the rest made (`keys.make_layer`, inside the chunk);
2. the channels (`groups`, built by the caller): a character of the card's model
   (`character_channels`: the card's nodes paired by leaf name, kept to the card's members on the
   target - 1P upper / lower cut the members first -, Selected only and In place applied), the
   card's objects (`objects_channels`: a plain curve the base's, a layered one its layers);
3. each picked layer's curve clipped to the paste's source range and moved to its time
   (`animapply._object_keys` - At current time and Range as an objects card's);
4. ONE undo chunk (`animapply._chunk`): the layers made, the paste mode's cut / shift on THAT
   layer's curves only (`animapply._ops`), the RAW keys with every tangent, weighting, infinity
   (`keys.write_raw`) and breakdown (`animapply._breakdowns`); Connect on the one layer pasted
   (`_connect`); `progress` stepped once per channel, Esc undoes the chunk.
Nothing is measured: the curves are the source's, key for key. Mirror and Blend change values
and are refused by the caller (`MIRRORED`, `BLENDED`).

Spec: docs/superpowers/specs/2026-10-28-pose-library-curves-and-layers-design.md («Paste»)
"""

from collections import OrderedDict

import maya.cmds as cmds

from maya_poselib import animapply as aa
from maya_poselib import apply as ap
from maya_poselib import curvecapture
from maya_poselib import curvedata
from maya_poselib import keys
from maya_poselib import look
from maya_poselib import scene
from maya_poselib import skelsolve

MIRRORED = "original curves are pasted as they were keyed - turn Mirror off or paste as Retarget"
BLENDED = "original curves are pasted whole - Blend is for Retarget"
UNREAD = "the card's curves cannot be read - retargeted instead"
RETARGETED = "retargeted - not the card's model: %s"
NO_LAYER = "no layer of the card picked"
NOTHING = "nothing to paste: no picked layer holds a curve of the targets"
MISSING = "%d of the card's controls not on %s: %s"
MADE = "%s (made)"
CONNECT_ONE = "Connect skipped - it needs one layer, %d picked"
CONNECT_WEIGHT = "Connect skipped on %s - its weight is 0"
CONNECT_QUAT = "Connect skipped on the rotations of %s - it accumulates as quaternions"
CONNECT_MUTED = "Connect skipped on %s - it is muted"
FLOOR_IN_PLACE = "Main kept at the drop point - original curves carry no travel from a floor drop"


def matches(header, ref):
    """Does `ref` take the card's curves - the same model and kind as the card's character?"""
    who = (header or {}).get("character") or {}
    return bool(who.get("model")) and who.get("model") == getattr(ref, "model", None) \
        and who.get("kind") == getattr(ref, "kind", None)


def target_nodes(ref):
    """The long paths a card's nodes pair with on `ref`: a rig's ControlSet, a skeleton's joints."""
    if ref.kind == "rig" and ref.rig is not None:
        found = cmds.sets(ref.rig.control_set, query=True) or []
        return (cmds.ls(found, long=True) or []) if found else []
    return cmds.ls(ref.root, dag=True, type="joint", long=True) or []


def _root_node(ref, bones):
    """What In place leaves unkeyed: a rig's Main, a skeleton's root joint."""
    if ref.kind == "rig":
        return aa._main_of(ref)
    root = skelsolve.root_leaf(ref, bones)
    return (bones.get(root) or {}).get("path")


def character_channels(header, curves, ref, only=None, in_place=False):
    """(OrderedDict {plug: {card layer: CURVE}}, notes) of the card's curves on `ref`: each card
    node paired by leaf name (`curvedata.pair_nodes`), kept only when the save's rule keeps it for
    the card's members on this target (`curvecapture.character_nodes` - a card cut to 1P upper /
    lower body pastes that half), Selected only's paths (`only`), In place's Main / root left out;
    a card node the target lacks, and an attribute it lacks, named."""
    bones = scene.skeleton(ref, [])[0]
    allowed = set(curvecapture.character_nodes(ref, bones, header.get("members") or ()))
    nodes = curves.get("nodes") or []
    paired, missing = curvedata.pair_nodes([node["name"] for node in nodes], target_nodes(ref),
                                           scene.leaf)
    skip = _root_node(ref, bones) if in_place else None
    channels, absent = OrderedDict(), []
    for node in nodes:
        path = paired.get(node["name"])
        if path is None or path not in allowed or path == skip:
            continue
        if only is not None and path not in only:
            continue
        for attr, per in node["attrs"].items():
            if cmds.attributeQuery(attr, node=path, exists=True):
                channels[path + "." + attr] = per
            else:
                absent.append(scene.leaf(path) + "." + attr)
    notes = []
    if missing:
        notes.append(MISSING % (len(missing), ap.target_label(ref), ap._named(missing)))
    if absent:
        notes.append(ap.NOT_POSED % (len(absent), "no such attribute", ap._named(absent)))
    return channels, notes


def objects_channels(matched):
    """(OrderedDict {plug: {card layer: CURVE}}, notes, object paths) of the card's objects paired
    with the scene's (`animapply._object_channels`): a plain curve the base's, a layered one its
    layers (`curvedata.per_layer`)."""
    channels, notes, paths = aa._object_channels(matched)
    return OrderedDict((plug, curvedata.per_layer(curve)) for plug, curve in channels.items()), \
        notes, paths


def _planned(groups, names, plan):
    """OrderedDict {(group index, plug): {card layer: (keys in target time, weighted, breakdown
    times, pre, post)}} of the picked layers' curves, each clipped to the paste's source range and
    moved to its time (`animapply._object_keys`); a layer with nothing to key there left out."""
    lo, hi = plan.frames[0][0], plan.frames[-1][0]
    planned = OrderedDict()
    for index, (_label, _noun, channels, _notes) in enumerate(groups):
        for plug, per in channels.items():
            for name in names:
                curve = per.get(name)
                if not isinstance(curve, dict):
                    continue
                stored, weighted = aa._object_keys(curve, lo, hi, plan)
                if not stored:
                    continue
                breaks = aa._breakdown_times(curve, lo, hi, plan, stored) \
                    if curve.get("keys") else []
                planned.setdefault((index, plug), OrderedDict())[name] = (
                    stored, weighted, breaks, curve.get("pre"), curve.get("post"))
    return planned


def _layers(where, records, made):
    """{card layer: target layer name or None}: the layers `where` says to make, made bottom to top
    in the card's order (`keys.make_layer`, each named in `made`); a namesake as found; the base
    the scene's root AFTER the makes (a scene without layers gets its root from the first one) -
    None without layers, the plain curves."""
    out = OrderedDict()
    for name, (kind, target) in where.items():
        if kind == "make":
            target = keys.make_layer(records[name])
            made.append(target)
        out[name] = target
    root = cmds.animLayer(query=True, root=True) or None
    for name, (kind, _target) in where.items():
        if kind == "base":
            out[name] = root
    return out


def _layers_text(names, layer_of, made):
    """The line's «BaseAnimation + AnimLayer2 (made)»."""
    parts = []
    for name in names:
        layer = layer_of.get(name)
        shown = scene.leaf(layer) if layer else curvedata.BASE
        parts.append(MADE % shown if layer in made else shown)
    return " + ".join(parts)


def _connect(planned, before, plan, layer, record):
    """Connect on the ONE layer pasted: each channel's pasted keys on it moved by what it showed
    at `a` before the press minus what it shows now, over the layer's weight
    (`curvedata.connect_offset`) - read AFTER the keys, so what stands above and below the layer
    is in it. A quaternion layer's rotations are no sum of eulers: skipped; weight 0: nothing to
    move. The notes said."""
    notes = []
    if layer is not None and not record.get("base") \
            and cmds.animLayer(layer, query=True, mute=True):
        return [CONNECT_MUTED % record["name"]]
    weight = 1.0 if (layer is None or record.get("base")) else keys._weight(layer)
    for (_index, plug), per in planned.items():
        if record.get("rotation") == "quaternion" and plug.rsplit(".", 1)[-1] in aa.ROTATE:
            notes.append(CONNECT_QUAT % record["name"])
            continue
        offset = curvedata.connect_offset(before[plug], cmds.getAttr(plug, time=plan.a), weight)
        if offset is None:
            return [CONNECT_WEIGHT % record["name"]]
        curve = keys.curve_for(plug, layer)
        if curve is not None and abs(offset) > 1e-12:
            for stored in per.get(record["name"], ((),))[0]:
                cmds.keyframe(curve, edit=True, relative=True, valueChange=offset,
                              time=(stored[0], stored[0]))
    return notes


def paste(header, groups, options=None, progress=None):
    """(ok, line): the card's original curves of `groups` - [(target label, noun, OrderedDict
    {plug: {card layer: CURVE}}, notes)], one a character (or the card's objects) - pasted with
    `options` (the module's press). Refusals before anything is written: no layer picked, an
    empty range, a locked namesake layer."""
    options = aa._options(options)
    names = curvedata.chosen(curvedata.layer_names(header), options.layers)
    if not names:
        return False, NO_LAYER
    try:
        plan = aa._plan(header, options)
    except ValueError as error:
        return False, str(error)
    records = dict((record["name"], record) for record in curvedata.records(header))
    existing = keys.existing_layers()
    where = OrderedDict()
    for name in names:
        kind, target = curvedata.layer_target(records[name], existing)
        if kind == "refused":
            return False, keys.LOCKED % target
        where[name] = (kind, target)
    if any(kind == "base" for kind, _target in where.values()):
        root = cmds.animLayer(query=True, root=True)
        if root and cmds.animLayer(root, query=True, lock=True):
            return False, keys.LOCKED % scene.leaf(root)
    planned = _planned(groups, names, plan)
    if not planned:
        return False, NOTHING
    said = OrderedDict()
    connect = bool(options.connect) and curvedata.connect_ok(names)
    if options.connect and not connect:
        text = CONNECT_ONE % len(names)
        said[text] = text
    before = dict((plug, float(cmds.getAttr(plug, time=plan.a)))
                  for (_index, plug) in planned) if connect else {}
    title = header.get("name") or "Animation"
    recording = bool(cmds.undoInfo(query=True, state=True))
    steps = aa._Steps()
    keyed = [set() for _group in groups]
    made, done = [], []
    reached = [0] * len(plan.ops)
    cancelled = False
    layer_of = {}
    try:
        with aa._chunk(steps):
            layer_of = _layers(where, records, made)
            for name in names:
                plugs = [plug for (_index, plug), per in planned.items() if name in per]
                if plugs:
                    reached = [n + m for n, m in zip(reached, aa._ops(plan.ops, plugs,
                                                                      layer_of[name]))]
            for (index, plug), per in planned.items():
                for name, (stored, weighted, breaks, pre, post) in per.items():
                    layer = layer_of[name]
                    written = keys.write_raw(plug, layer, stored, weighted, pre, post)
                    for text in written.notes:
                        said.setdefault(text, text)
                    if written.plugs:
                        keyed[index].add(ap._owner(plug.rsplit(".", 1)[0]))
                        for text in (aa._breakdowns(plug, layer, breaks) if breaks else ()):
                            said.setdefault(text, text)
                done.append(plug)
                if progress is not None and not progress.step(
                        aa.STEP % (title, scene.leaf(plug))):
                    cancelled = True
                    break
            if connect and not cancelled:
                for text in _connect(planned, before, plan, layer_of[names[0]],
                                     records[names[0]]):
                    said.setdefault(text, text)
    except BaseException:
        aa._undo_failed(recording and steps.recorded)
        raise
    if cancelled:
        if recording:
            cmds.undo()
            return False, aa.CANCELLED
        return False, aa._kept(ap._counted(len(done), "channels"), plan, "channels", reached)
    text = _layers_text(names, layer_of, made)
    rows = []
    for index, (label, noun, _channels, notes) in enumerate(groups):
        last = index == len(groups) - 1
        rows.append({"name": "%s (original curves)" % title, "target": label,
                     "count": len(keyed[index]), "noun": noun, "layer": text,
                     "a": plan.a, "b": plan.b, "frames": plan.b - plan.a + 1,
                     "mode": options.mode, "worst": None, "worst_frame": None,
                     "notes": list(notes) + (list(said.values()) if last else []),
                     "alpha": 1.0, "mirror": False})
    return any(keyed), look.anim_status(rows)
