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

SCALES = ("scaleX", "scaleY", "scaleZ")
#  Tools > 1P Setup's layers (`maya_tools.firstperson.LOWER` / `UPPER`, spelled here; a second
#  rig's get Maya's digit)
FIRST_PERSON = ("_3P_Lower_Body", "_3P_Upper_Body")
EPS = 1e-6

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


def summary(records, count, first_person=False):
    """The header's `curves` block: the layer `records` bottom to top (the base first), how many
    nodes keep curves and, saved off a rig in 1P, `first_person` (`saved_in_first_person`)."""
    block = {"layers": [dict(record) for record in records], "nodes": int(count)}
    if first_person:
        block["first_person"] = True
    return block


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


def saved_in_first_person(header):
    """Was the card saved off a rig in 1P (Tools > 1P Setup)? Its `curves` block says so (since
    2026-10-29), or - a card saved before - its layers are the 1P Setup's. Its curves are that
    rig's split (the take on `FIRST_PERSON`'s layers, the chest on a knot no card keeps): pasted
    raw onto a 3P rig they twisted the upper body 180 deg, so a paste retargets it."""
    block = (header or {}).get("curves")
    if isinstance(block, dict) and block.get("first_person"):
        return True
    return any(name.startswith(FIRST_PERSON) for name in layer_names(header))


def takes_curves(header):
    """Can a paste of «Original curves» take the card's curves - it holds them, and was not saved
    off a rig in 1P (`saved_in_first_person`: such a card retargets, and the window does not offer
    it the choice)?"""
    return has_curves(header) and not saved_in_first_person(header)


def identity(attr, scale="multiply"):
    """The value an additive layer adds nothing with on `attr`: 1 for a scale channel of a layer
    accumulating scale by multiply, else 0."""
    return 1.0 if attr in SCALES and scale == "multiply" else 0.0


#  tangent types whose angle Maya computes from the NEIGHBOURING keys - a target key beside the
#  pasted range changes them; the rest keep their shape whatever stands beside them
_STABLE = ("linear", "flat", "step", "stepnext", "fixed")


def _held_shape(key):
    """A card key beside a key of the target's: its neighbour-computed tangents turned fixed at
    the angles the source showed (a stored key carries them, `[..., in angle, in weight, out
    angle, out weight]`) - an auto key next to a target key bent the range's first segment 2 deg
    (measured 2026-10-29). A key saved without angles keeps its types."""
    if len(key) < 8:
        return
    for index in (2, 3):
        if key[index] not in _STABLE:
            key[index] = "fixed"


def pinned(stored, a, b, before=True, after=True):
    """`stored` keys (target time, `[t, v, in type, out type, ...]`) held at the paste range's
    ends where the target keeps a key outside them (`before` / `after`), which would otherwise
    bend the range: the end key's tangents held as the source showed them (`_held_shape`); a
    curve that starts after `a` a key there holding its first value (out tangent "step": exact up
    to the first key), one that ends before `b` a key there holding its last value, the last
    key's out tangent "step". A curve's tangent past its ends shaped nothing in the source
    (constant infinity), so the range shows what the card did. Copies; pure."""
    out = [list(key) for key in stored]
    if not out:
        return out
    if before:
        _held_shape(out[0])
        if out[0][0] > a + EPS:
            out.insert(0, [float(a), out[0][1], "flat", "step"])
    if after:
        _held_shape(out[-1])
        if out[-1][0] < b - EPS:
            last = out[-1]
            last.extend([None] * (4 - len(last)))
            last[3] = "step"
            out.append([float(b), last[1], "flat", "flat"])
    return out


def bounded(stored, a, b, value, before=True, after=True):
    """`stored` - a layer curve the paste MAKES - adding `value` (`identity`: nothing) outside
    the paste range where the target animates the channel there: held at both ends (`pinned`),
    then a stepped key a frame before `a` when `before`, one a frame after `b` (the end key
    stepped) when `after`. Without them the card's last offset held over the rest of the take
    (2026-10-29: frame 90 of a take pasted at 40-75 moved 32 deg). Copies; pure."""
    out = pinned(stored, a, b, before, after)
    if not out:
        return out
    if before:
        out.insert(0, [float(a) - 1.0, value, "flat", "step"])
    if after:
        last = out[-1]
        last.extend([None] * (4 - len(last)))
        last[3] = "step"
        out.append([float(b) + 1.0, value, "flat", "flat"])
    return out


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
