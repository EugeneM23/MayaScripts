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
took a key (`plugs`) - what a status line counts. `feed_of` / `input_of` say what feeds a plug
(free, a curve, a layer, driven) and through which node, for a Blend that has to put back only
what holds a value by itself and have the rest evaluated afresh (its feeding node dirtied).

`preview` is the live half (the Blend slider, a middle-drag across a card): plain `setAttr`,
which works on layered and keyed channels and holds until the next time change; the last
`current` values put everything back. A scripted `setAttr` KEYS under autoKey, so the caller
holds autoKey off for the length of a preview session, as `write`'s caller does.

Spec: docs/superpowers/specs/2026-10-02-pose-library-design.md ("Keys - the active layer").
"""

from collections import OrderedDict, namedtuple

import maya.cmds as cmds

Layer = namedtuple("Layer", "name base additive locked quaternion muted weight",
                   defaults=(False, 1.0))
TIME_CURVES = ("animCurveTA", "animCurveTL", "animCurveTT", "animCurveTU")
# nodes a time curve feeds that are no channel the animator sets: a layer's blend node is looked
# through (its output is the channel), these are left alone
_NOT_A_CHANNEL = ("pairBlend", "character", "clipScheduler", "clipLibrary", "expression")
TWEAK_TOL = 1e-9

LOCKED = "the animation layer %s is locked - unlock it or pick another"
MUTED = "%s is muted - the keys are in it, the pose shows when it is on"
NO_WEIGHT = "%s is at weight 0 - the keys are in it, the pose shows at its weight"
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
                   bool(rec["locked"]), bool(rec["quaternion"]),
                   bool(rec.get("muted", False)), float(rec.get("weight", 1.0)))
    if picked.locked:
        return None, LOCKED % picked.name
    return picked, ""


def layer_note(layer):
    """Why a pose keyed into `layer` will not show, or "": a MUTED layer (or one under a muted
    parent) and a layer at WEIGHT 0 take the keys - `setKeyframe(value=)` writes them as if the
    layer were on, at full weight - while the scene keeps showing what is under it, and the
    press read as «23 controls keyed» with a large unexplained worst (the final review). Keyed
    anyway, and said: muting a layer is a way of LOOKING at the take - unlike a lock, which the
    animator sets to protect a layer and which is refused (`LOCKED`) - and the keys are right
    the moment the layer is on again."""
    if layer is None or layer.base:
        return ""
    if layer.muted:
        return MUTED % layer.name
    if abs(layer.weight) < 1e-9:
        return NO_WEIGHT % layer.name
    return ""


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
    records, muted = [], {}
    for order, name in enumerate(_walk(root)):
        base = name == root
        records.append({
            "name": name,
            "base": base,
            "selected": bool(cmds.animLayer(name, query=True, selected=True)),
            "locked": bool(cmds.animLayer(name, query=True, lock=True)),
            "override": bool(cmds.animLayer(name, query=True, override=True)),
            "quaternion": _quaternion(name),
            "muted": False if base else _muted(name, root, muted),
            "weight": 1.0 if base else _weight(name),
            "order": order,
        })
    return pick_layer(records)


def _muted(name, root, known):
    """Is the layer muted, itself or through a muted parent (a parent's mute silences what is
    under it)? `known` caches the answers of one walk."""
    if name in known:
        return known[name]
    try:
        own = bool(cmds.animLayer(name, query=True, mute=True))
        parent = cmds.animLayer(name, query=True, parent=True)
    except (RuntimeError, TypeError, ValueError):
        own, parent = False, None
    if isinstance(parent, (list, tuple)):
        parent = parent[0] if parent else None
    known[name] = own or bool(parent and parent != root and _muted(parent, root, known))
    return known[name]


def _weight(name):
    try:
        return float(cmds.animLayer(name, query=True, weight=True))
    except (RuntimeError, TypeError, ValueError):
        return 1.0


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


def feed_of(plug):
    """(kind, node): what feeds `plug` now - "free" | "curve" | "layer" | "driven"
    (`input_kind` of its source, the compound parent's included), "missing" for a plug that is
    not there - and the node feeding it (None when free or missing).

    A Blend cancelled after the time moved asks it: a FREE channel holds whatever was set on it
    and has to be set back; a keyed or layered one is given back by evaluating the frame shown
    with its feeding node DIRTIED first - setting the start's value there would leave the OLD
    frame's value holding, and a same-time `currentTime` alone leaves a blend node that does not
    depend on time clean (a static channel in a layer kept the preview's value through every
    later time change: measured, in DG and in parallel evaluation)."""
    try:
        nodes = _feeds(plug)
    except (ValueError, RuntimeError):
        return "missing", None
    if not nodes:
        return "free", None
    return input_kind(cmds.objectType(nodes[0])), nodes[0]


def input_of(plug):
    """`feed_of`'s kind alone: "free" | "curve" | "layer" | "driven" | "missing"."""
    return feed_of(plug)[0]


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


# ------------------------------------------------------------------ the animator's tweaks

def time_fed():
    """Every channel in the scene a TIME curve feeds - straight, through a unit conversion, or
    through an animation layer's blend nodes (looked through to the channel they drive) - as
    `node.attr` plugs, each once. Nodes that are no channel (`_NOT_A_CHANNEL`: a pairBlend under
    a constraint, a character set) are left out."""
    curves = cmds.ls(type=TIME_CURVES) or []
    out, seen, frontier, kinds = OrderedDict(), set(), curves, {}
    while frontier:
        pairs = cmds.listConnections(frontier, source=False, destination=True, plugs=True,
                                     connections=True, skipConversionNodes=True) or []
        frontier = []
        for plug in pairs[1::2]:
            node = plug.split(".")[0]
            if node not in kinds:
                kinds[node] = cmds.nodeType(node)
            kind = kinds[node]
            if kind.startswith("animBlendNode"):
                if node not in seen:
                    seen.add(node)
                    frontier.append(node)
            elif kind not in _NOT_A_CHANNEL and not kind.startswith("animCurve"):
                out[plug] = True
    return list(out)


def _identity(plug):
    """(the node's UUID, the attribute) of a plug however its node is spelled; None for a plug
    whose node is not one node."""
    node, _dot, attr = plug.rpartition(".")
    found = cmds.ls(node, uuid=True) or []
    return (found[0], attr) if len(found) == 1 else None


class Tweaks(object):
    """What every time-fed channel of the scene SHOWS (`time_fed`), read once, and put back.

    A same-frame `currentTime`, and switching the evaluation manager (the solve reads under DG,
    `rigsolve._fresh`), re-evaluate every time curve in the scene - and an unkeyed TWEAK on a
    keyed channel (a value set with autoKey off, which holds until the next time change) snaps
    back to its curve: on another character, on a prop, on the very channels a press leaves
    alone (the final review, 2026-10-03: a hand card applied, the body posed by hand snapped to
    its keys; Esc after a blend put back the curves' values, not the animator's). So a press
    reads them first and, after anything that re-evaluates the scene, `restore` sets back every
    one that moved - but the plugs it keyed itself, which show their new key. Measured: 4224
    keyed channels on three rigs read in a few hundredths of a second."""

    def __init__(self):
        self.values = OrderedDict()
        for plug in time_fed():
            try:
                value = cmds.getAttr(plug)
            except (RuntimeError, ValueError, TypeError):
                continue
            if isinstance(value, (bool, int, float)):
                self.values[plug] = float(value)

    def moved(self):
        """The captured plugs whose value is not what it was."""
        out = []
        for plug, value in self.values.items():
            try:
                now = float(cmds.getAttr(plug))
            except (RuntimeError, ValueError, TypeError):
                continue
            if abs(now - value) > TWEAK_TOL:
                out.append(plug)
        return out

    def restore(self, skip=()):
        """Every captured plug that moved, set back to what it showed (autoKey off: a scripted
        `setAttr` keys under it) - but those `skip` names (any spelling of the node): the plugs
        a press keyed. The plugs set back."""
        moved = self.moved()
        if not moved:
            return []
        skipped = set(filter(None, (_identity(p) for p in skip or ())))
        auto = cmds.autoKeyframe(query=True, state=True)
        cmds.autoKeyframe(state=False)
        back = []
        try:
            for plug in moved:
                if skipped and _identity(plug) in skipped:
                    continue
                try:
                    cmds.setAttr(plug, self.values[plug])
                    back.append(plug)
                except RuntimeError:
                    pass
        finally:
            cmds.autoKeyframe(state=auto)
        return back
