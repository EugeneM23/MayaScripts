"""The pose library's keys: the active animation layer, writable plugs, preview, final-value keys.

The animator: «Поза должна накладываться на текущий активный анимационный слой». A pose is applied
as KEYS on the current frame, and which animation layer takes them is not a guess:

- the **active layer** is the selected non-base layer (several selected: the topmost in the
  stack), else `BaseAnimation`; a scene with no layers at all gets plain keys;
- a LOCKED active layer is refused here, by name - Maya itself lets a script key into a locked
  layer, so nothing else would stop it;
- a plug that is not yet part of a non-base layer is added to it first (`animLayer -e
  -attribute`; a key into a layer that lacks the plug is refused by Maya with a warning and
  returns 0). The base layer needs no adding;
- every key is `setKeyframe(plug, time=frame, value=v, animLayer=L)` with `v` the plug's FINAL
  value: Maya itself writes `v - base` onto an additive layer (and `/weight` at a weight other
  than 1), `v` on an override layer. `animLayer` is ALWAYS passed when any layer exists -
  without it Maya picks its own "best" layer, not the selected one.

An additive layer in QUATERNION accumulation (`rotationAccumulationMode` 1) does not add eulers
per channel, so exact final eulers cannot be keyed there: `quaternion_note` names such a layer
and the apply refuses it for ROTATE channels (translate channels are fine, component mode is
exact). This module only reports it; it never decides for the caller.

`writable(plug)` is the guard for every write, because the failure modes differ (measured in
mayapy, Maya 2027): a locked plug RAISES on `setAttr`, but a plug driven by a constraint takes
`setAttr` WITHOUT an error and is overwritten on the next evaluation - a silent no-op that
reads as a pose which "did not land". A channel is writable when it is free, keyed by a time
curve, or already inside an animation layer; a constraint, a pairBlend, an expression or a
driven-key curve makes it "driven" and it is skipped and named, as the weapon link's
constraint on `weapon_r` has to be. "Driven" includes a connection into the channel's COMPOUND
parent (`decomposeMatrix.outputRotate -> joint.rotate`, `plusMinusAverage.output3D ->
translate`), which `listConnections` on the leaf does not see - `connectionInfo` does.

`write` answers `Written`: the pair (keys made, notes) it always answered, and the plugs that
took a key (`plugs`) - what a status line counts. `input_of` says what feeds a plug (free, a
curve, a layer, driven), for a Blend that has to put back only what holds a value by itself.

`preview` is the live half (the Blend slider, a middle-drag across a card): plain `setAttr`,
which works on layered and keyed channels and holds until the next time change; the last
`current` values put everything back. A scripted `setAttr` KEYS under autoKey, so the caller
holds autoKey off for the length of a preview session, as `write`'s caller does.

Spec: docs/superpowers/specs/2026-10-02-pose-library-design.md ("Keys - the active layer").
"""

from collections import namedtuple

import maya.cmds as cmds

Layer = namedtuple("Layer", "name base additive locked quaternion")

LOCKED = "the animation layer %s is locked - unlock it or pick another"
QUATERNION = ("the additive animation layer %s accumulates rotation as quaternions, which "
              "cannot take exact rotate keys - switch it to component accumulation or pick "
              "another layer (translate channels are fine)")
NOT_KEYED = "%d not keyed (%s): %s"

# plugs named per reason in a note: a whole rig skipped must not print three hundred names
NAMED = 4


def pick_layer(layers):
    """(the Layer to key into or None, refusal) from the scene's layer records.

    `layers` is a list of dicts {name, base, selected, locked, override, quaternion, order};
    `order` is the position in the stack, larger is higher. No layers: (None, "") - plain keys.
    Otherwise the topmost selected non-base layer, else the base; a chosen layer that is
    locked answers (None, refusal). A list with no base layer (Maya always has one) falls back
    to the lowest layer rather than crashing a press.
    """
    if not layers:
        return None, ""
    chosen = [rec for rec in layers if rec["selected"] and not rec["base"]]
    if chosen:
        rec = max(chosen, key=lambda r: r["order"])
    else:
        bases = [r for r in layers if r["base"]]
        rec = bases[0] if bases else min(layers, key=lambda r: r["order"])
    picked = Layer(rec["name"], bool(rec["base"]),
                   not rec["base"] and not rec["override"],
                   bool(rec["locked"]), bool(rec["quaternion"]))
    if picked.locked:
        return None, LOCKED % picked.name
    return picked, ""


def input_kind(source_type):
    """What feeds a plug, from the TYPE of its source node: free | curve | layer | driven.

    None (nothing connected) is free; a time curve (`animCurveT*`) is a curve; an animation
    layer's blend node (`animBlendNode*`) is a layer; anything else - a constraint, a
    pairBlend, an expression, a driven-key curve (`animCurveU*`, whose x axis is a driver's
    value, not time) - is driven.
    """
    if not source_type:
        return "free"
    if source_type.startswith("animCurveT"):
        return "curve"
    if source_type.startswith("animBlendNode"):
        return "layer"
    return "driven"


def _walk(name):
    """`name` and every layer below it, depth first - the order is the stack position.

    `animLayer -q -children` lists bottom to top (measured), so in the preorder a nested layer
    comes right after its parent and before the parent's next sibling.
    """
    found = [name]
    for child in cmds.animLayer(name, query=True, children=True) or []:
        found.extend(_walk(child))
    return found


def _quaternion(name):
    """True when the layer accumulates rotation as quaternions (`rotationAccumulationMode` 1)."""
    try:
        return cmds.getAttr(name + ".rotationAccumulationMode") == 1
    except (ValueError, RuntimeError):
        return False


def active_layer():
    """(Layer | None, refusal): the layer a pose is keyed into, read off the scene."""
    root = cmds.animLayer(query=True, root=True)
    if not root:
        return None, ""
    records = []
    for order, name in enumerate(_walk(root)):
        records.append({
            "name": name,
            "base": name == root,
            "selected": bool(cmds.animLayer(name, query=True, selected=True)),
            "locked": bool(cmds.animLayer(name, query=True, lock=True)),
            "override": bool(cmds.animLayer(name, query=True, override=True)),
            "quaternion": _quaternion(name),
            "order": order,
        })
    return pick_layer(records)


def _compound_feed(plug):
    """[the node feeding `plug` through its COMPOUND parent], or [] - what `listConnections` misses.

    `decomposeMatrix.outputRotate -> joint.rotate` (and `outputTranslate -> translate`,
    `plusMinusAverage.output3D`, a motion path's position) connects the PARENT of the channel.
    Measured in mayapy 2027: `listConnections(joint.rotateX)` answers None, `setAttr` takes the
    value without an error and the next evaluation overwrites it (`getAttr(settable=True)` is
    False) - the silent pose that "did not land" this module exists to refuse. `connectionInfo`
    sees through the compound. A double3 into an angle compound has Maya put a `unitConversion`
    in the path and `connectionInfo` names THAT; it is looked through, so the note names the real
    driver. Free plugs answer [] after one cheap query, and a plug with a connection of its own
    never gets here.
    """
    if not cmds.connectionInfo(plug, isDestination=True):
        return []
    source = cmds.connectionInfo(plug, sourceFromDestination=True)
    if not source:
        return []
    node = source.split(".")[0]
    if cmds.objectType(node) == "unitConversion":
        behind = cmds.listConnections(node + ".input", source=True, destination=False,
                                      skipConversionNodes=True)
        if behind:
            node = behind[0]
    return [node]


def _feeds(plug):
    """[the node feeding `plug`] - through the plug itself, else its compound parent; [] when
    nothing does. Raises on a missing plug, as the queries do."""
    nodes = cmds.listConnections(plug, source=True, destination=False,
                                 skipConversionNodes=True) or []
    return nodes or _compound_feed(plug)


def writable(plug):
    """(True, "") when a value can be set and keyed on `plug`, else (False, why).

    locked -> "locked"; a missing plug -> "missing"; driven by a constraint or the like ->
    "driven by <node>", whether the node feeds the plug itself or its compound parent
    (`_compound_feed`). A free plug, one keyed by a time curve and one inside an animation
    layer are writable. Lock is asked first - a locked plug is locked whatever drives it.
    """
    try:
        if cmds.getAttr(plug, lock=True):
            return False, "locked"
        nodes = _feeds(plug)
    except (ValueError, RuntimeError):
        return False, "missing"
    if nodes and input_kind(cmds.objectType(nodes[0])) == "driven":
        return False, "driven by " + nodes[0]
    return True, ""


def input_of(plug):
    """What feeds `plug` now: "free" | "curve" | "layer" | "driven" (`input_kind` of its
    source, the compound parent's included), "missing" for a plug that is not there.

    A Blend cancelled after the time moved asks it: a FREE channel holds whatever was set on it
    and has to be set back, a keyed or layered one shows the new frame once time is evaluated -
    setting the start's value there would leave a stale value holding until the next time
    change."""
    try:
        nodes = _feeds(plug)
    except (ValueError, RuntimeError):
        return "missing"
    return input_kind(cmds.objectType(nodes[0])) if nodes else "free"


def current(plugs):
    """{plug: float} - what each channel shows now (a layered channel's composite)."""
    return {plug: float(cmds.getAttr(plug)) for plug in plugs}


def preview(values):
    """Set every writable plug to its value, live; skip the others without a word.

    `setAttr` holds on keyed and layered channels until the next evaluation of time, which is
    the whole point of a preview - nothing is keyed, `current` puts it back. A constrained plug
    would take the value and lose it at the next evaluation, so `writable` filters first.
    """
    for plug, value in values.items():
        if not writable(plug)[0]:
            continue
        try:
            cmds.setAttr(plug, value)
        except RuntimeError:
            pass


def _key(plug, value, frame, layer):
    """One final-value key, on the layer when there is one; the number of keys Maya made."""
    if layer is None:
        return cmds.setKeyframe(plug, time=frame, value=value)
    return cmds.setKeyframe(plug, time=frame, value=value, animLayer=layer.name)


def _why(error):
    """The first line of a Maya error, short enough for a status line."""
    lines = str(error).strip().splitlines()
    return (lines[0] if lines else type(error).__name__)[:80]


def _note(reason, plugs):
    """One note for the plugs skipped for one reason - the first few named, the rest counted."""
    shown = ", ".join(plugs[:NAMED])
    if len(plugs) > NAMED:
        shown += " and %d more" % (len(plugs) - NAMED)
    return NOT_KEYED % (len(plugs), reason, shown)


class Written(tuple):
    """What `write` answers: the pair (keys made, notes) it always answered - it unpacks and
    compares as that pair - plus `plugs`, the plugs that took a key, in their order (a status
    line counts what was KEYED, not what was planned)."""

    def __new__(cls, count, notes, plugs=()):
        self = tuple.__new__(cls, (count, notes))
        self.plugs = list(plugs)
        return self

    @property
    def count(self):
        return self[0]

    @property
    def notes(self):
        return self[1]


def write(values, frame, layer):
    """Key `values` ({plug: FINAL value}) on `frame`; `Written` (keys made, notes) with `.plugs`
    the plugs keyed.

    With a non-base `layer` each plug is added to it first (the layer refuses a key for a plug
    it does not hold); the base needs no adding and `layer=None` means a scene with no layers
    - plain keys, no `animLayer` flag at all. A plug that is not writable, that Maya refuses
    the key for (it answers 0) or that raises is skipped, and the notes name the skipped plugs
    grouped by reason, so one constraint holding twenty channels is one line.
    """
    added = layer is not None and not layer.base
    count = 0
    keyed = []
    skipped = {}
    for plug, value in values.items():
        ok, reason = writable(plug)
        if not ok:
            skipped.setdefault(reason, []).append(plug)
            continue
        try:
            if added:
                cmds.animLayer(layer.name, edit=True, attribute=plug)
            made = _key(plug, value, frame, layer) or 0
        except RuntimeError as error:
            skipped.setdefault(_why(error), []).append(plug)
            continue
        if made:
            count += int(made)
            keyed.append(plug)
        else:
            skipped.setdefault("no key made" if layer is None else
                               "layer %s took no key" % layer.name, []).append(plug)
    return Written(count, [_note(reason, plugs) for reason, plugs in skipped.items()], keyed)


def quaternion_note(layer):
    """Why this layer cannot take rotate keys exactly, or "" when it can.

    Non-empty for an additive layer in quaternion accumulation only; an override layer and the
    base take final eulers as they are.
    """
    if layer is None or not (layer.quaternion and layer.additive):
        return ""
    return QUATERNION % layer.name
