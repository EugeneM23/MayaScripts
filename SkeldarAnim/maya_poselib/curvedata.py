"""maya_poselib.curvedata - the pure rules of an animation card's ORIGINAL curves (2026-10-28).
Stdlib only.

The animator: «А мы можем так сделать что бы наша библеотека поз потдерживала сохранения по слоям
и сохранения ключей?». A card keeps, beside its bones' frames, the source's own curves layer by
layer: the LAYERS in its header (`anim.json`'s `curves`: `summary`), the controls' curves in
`curves.json.gz` (`check`), an objects card's layered channels in the header beside their sampled
keys (`per_layer`). `curvecapture` reads them, `curveapply` pastes them. This module holds what
needs no scene: the records, the check, the picks, which controls a card keeps, where each card
layer goes on the target, Connect's one-layer rule.

A layer is named by its LEAF (no namespace: a scene tab puts its layers in one); the base is
always `BASE`, whatever the scene's root is called (a scene tabs session's root is
`skeldarTabsLayerRoot`).

Spec: docs/superpowers/specs/2026-10-28-pose-library-curves-and-layers-design.md
"""

import math

VERSION = 1
BASE = "BaseAnimation"
WHOLE = "whole"                        # `scene._WHOLE`: a control that names the whole body
#  an animLayer's accumulation enums (measured, task 1's probe)
ROTATION = {0: "component", 1: "quaternion"}
SCALE = {0: "additive", 1: "multiply"}

BROKEN = "%s: not a card's curves"


def _finite(value):
    """Is `value` a finite number (a bool is not one: JSON's true would key as 1)?"""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _leaf(name):
    """The leaf of a scene name: the part after the last `|` and the last `:`."""
    return (name or "").split("|")[-1].split(":")[-1]


def layer_record(name, base=False, override=False, weight=1.0, mute=False,
                 rotation="component", scale="multiply"):
    """One card layer as the header keeps it: its leaf name, mode, weight, own mute and
    accumulation modes. The base is `BASE` with the base's settings whatever it is called."""
    if base:
        return {"name": BASE, "base": True, "override": False, "weight": 1.0, "mute": False,
                "rotation": "component", "scale": "multiply"}
    return {"name": _leaf(name), "base": False, "override": bool(override),
            "weight": float(weight), "mute": bool(mute), "rotation": rotation, "scale": scale}


def _curve_ok(curve):
    """A CURVE a paste can key: `{"static": number}` or `{"keys": [[t, v, ...]...]}`, every time
    and value a finite number (JSON's NaN never reaches a key)."""
    if not isinstance(curve, dict):
        return False
    if "static" in curve:
        return _finite(curve["static"])
    stored = curve.get("keys")
    return isinstance(stored, list) and all(
        isinstance(key, list) and len(key) >= 2 and _finite(key[0]) and _finite(key[1])
        for key in stored)


def check(data, names, where="curves"):
    """`data` (a `curves.json.gz` read back) when whole, else ValueError(BROKEN): a dict whose
    `nodes` is a list of {name: str, attrs: {attr: {layer: CURVE}}}, every layer one of `names`
    (the header's) and every CURVE keyable - a broken card is refused before a press writes
    anything, never half pasted."""
    names = set(names or ())
    if not (isinstance(data, dict) and isinstance(data.get("nodes"), list)):
        raise ValueError(BROKEN % where)
    for node in data["nodes"]:
        if not (isinstance(node, dict) and isinstance(node.get("name"), str)
                and isinstance(node.get("attrs"), dict)):
            raise ValueError(BROKEN % where)
        for per in node["attrs"].values():
            if not isinstance(per, dict) or not per:
                raise ValueError(BROKEN % where)
            for name, curve in per.items():
                if name not in names or not _curve_ok(curve):
                    raise ValueError(BROKEN % where)
    return data


def summary(records, count):
    """The header's `curves` block: the layer `records` bottom to top (the base first) and how
    many nodes keep curves."""
    return {"layers": [dict(record) for record in records], "nodes": int(count)}


def records(header):
    """The header's layer records, bottom to top - [] when it holds no `curves` block or a broken
    one (a list of dicts with str names, the first the base)."""
    block = (header or {}).get("curves")
    if not isinstance(block, dict):
        return []
    layers = block.get("layers")
    if not (isinstance(layers, list) and layers
            and all(isinstance(r, dict) and isinstance(r.get("name"), str) for r in layers)
            and layers[0].get("base")):
        return []
    return [dict(record) for record in layers]


def has_curves(header):
    """Does the card hold original curves a paste can take?"""
    return bool(records(header))


def layer_names(header):
    """The header's layer names, bottom to top."""
    return [record["name"] for record in records(header)]


def has_keys(per_layer_dicts):
    """Does any {layer: CURVE} of `per_layer_dicts` hold a curve with keys? Statics alone say
    nothing the bones' frames do not."""
    return any(isinstance(curve, dict) and curve.get("keys")
               for per in per_layer_dicts for curve in per.values())


def chosen(card_names, wanted):
    """The card's layers a paste writes, in the card's order: every one when `wanted` is None,
    else those `wanted` names (a name the card does not hold dropped)."""
    if wanted is None:
        return list(card_names)
    wanted = set(wanted)
    return [name for name in card_names if name in wanted]


def keeps_control(named, members, whole):
    """Does a card keep a control's curves? `named` is what the control names (`scene.
    _control_bones`: its bones, or `WHOLE`), `members` the card's member bones, `whole` - the
    card is the whole body. A control naming the whole body (Main) only with a whole-body card."""
    if named == WHOLE:
        return bool(whole)
    return bool(set(named or ()) & set(members or ()))


def pair_nodes(card_names, target_paths, leaf):
    """({card name: target path}, [card names the target lacks]): the card's nodes paired with
    the target's by `leaf` name (namespace and path ignored); the first target of a leaf wins."""
    by_leaf = {}
    for path in target_paths:
        by_leaf.setdefault(leaf(path), path)
    paired, missing = {}, []
    for name in card_names:
        if name in by_leaf:
            paired[name] = by_leaf[name]
        else:
            missing.append(name)
    return paired, missing


def layer_target(record, existing):
    """Where a card layer's keys go: ("base", None) for the card's base; ("layer", name) for the
    target's first layer of the same leaf name, mode and rotation accumulation; ("refused", name)
    when that layer is locked; ("make", None) when there is none - a namesake of another mode
    included: raw values mean nothing on a layer that sums them differently. `existing` is
    `keys.existing_layers()`: [{name, override, rotation, locked}] bottom to top."""
    if record.get("base"):
        return "base", None
    leaf = _leaf(record["name"])
    for layer in existing:
        if _leaf(layer["name"]) != leaf:
            continue
        if bool(layer.get("override")) != bool(record.get("override")):
            continue
        if layer.get("rotation", "component") != record.get("rotation", "component"):
            continue
        if layer.get("locked"):
            return "refused", layer["name"]
        return "layer", layer["name"]
    return "make", None


def per_layer(curve):
    """{layer: CURVE} of an objects card's channel: its `layers` when it sat in layers, else the
    channel's own curve as the base's."""
    if isinstance(curve, dict) and isinstance(curve.get("layers"), dict):
        return dict(curve["layers"])
    return {BASE: curve}


def connect_ok(names):
    """Connect works when the paste writes ONE layer: with two, which of them takes the offset
    is no rule but a guess."""
    return len(names) == 1


def connect_offset(before, now, weight):
    """How far Connect moves one channel's pasted keys on its layer: what it showed before the
    press minus what it shows now, over the layer's weight (an additive or override layer at
    weight w moves the shown value w times its own move); None at weight 0 - nothing moves it."""
    if abs(float(weight)) < 1e-9:
        return None
    return (float(before) - float(now)) / float(weight)
