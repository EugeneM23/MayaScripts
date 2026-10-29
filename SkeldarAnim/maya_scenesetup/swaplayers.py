"""A character swapped for another keeps its animation layers, or bakes them (2026-10-29).

The animator: «Сейчас наша библеотека умеет переносить аниации по слоям. Нужно реализовать
аткой же функционал при подмене ригов. Если на риге есть слои и мы мняем один риг на другой
каким-то из способов то нужно сделать атк что бы система спросила у нас хотим ли мы сохранить
ключи с лои или запечь всю анимацию. В случе с переносом рига на 1p версию перенос должен
сработать корректно». Asked: 1P is the OLD rig, and «keep the keys and layers» means the stack
AND each layer's own key times.

The question stands before anything is changed (`swap.swap`) and Keep takes one of two roads:

- the general road - the old character's stack CUT at every layer that can be kept
  (`cut_plan`), each cut baked and retargeted onto the new character, the readings written back
  bottom to top: the base's curves as they are (`write_raw` - one call a channel, every tangent
  kept) and each layer's through `keys.write`, which hands Maya a FINAL value and lets Maya
  work out what an additive, override, weighted or scale layer must hold (trap 205). Each layer
  is keyed only where THAT layer of the old character had keys, with its tangent types;
- a rig in 1P - its layers are Tools > 1P Setup's own split of a 3P take, so the 3P take (every
  layer unmuted) is retargeted ONCE and `maya_tools.firstperson.setup` run again on the new
  rig, which gives the two layers, the chest control, the camera, the IK arms and the display
  layers back.

Spec: docs/superpowers/specs/2026-10-29-swap-keep-layers-design.md
"""
from __future__ import absolute_import

from collections import namedtuple

import maya.cmds as cmds

KEEP = "Keep the layers"
BAKE = "Bake the animation"
CANCEL = "Cancel"
BUTTONS = (KEEP, BAKE, CANCEL)
_ANSWERS = {KEEP: "keep", BAKE: "bake", CANCEL: "cancel"}

TOLERANCE = 1e-4                    # two key times this close are one key
TITLE = "Swap: keep the animation layers?"
#  `source_curves`' layer for "the base's curves and every layer's together"
EVERY = "*every*"

KEPT = "layers kept: %s"
EMPTY = "%s is at weight 0 - made, left empty"
SPLIT_AGAIN = "1P Setup run again on %s"
FOLDED_1P = "%s folded into the 1P split"
NOT_KEPT = "%s not kept (%s)"
#  a cut that fails leaves the character playing the cut below it - not the whole take - so the
#  press goes back to the Bake road rather than leaving half an animation on it
BAKED_INSTEAD = "the animation was baked instead"
NOT_BAKED = "and the bake was refused too (%s) - the take on it is not the whole one"

Plan = namedtuple("Plan", "records cuts folds first_person")
#  one cut of the old stack, read off the new character: `index` into `Plan.records`, None for
#  the base; `values` {plug: {time: value}} (read at the union of every cut's times, so a layer
#  can be trimmed against the cut below it); `times` the frames IT keys; `tangents` {time:
#  (in, out)} the types the source keys had there.
Reading = namedtuple("Reading", "index values times tangents")


# ------------------------------------------------------------------ pure

def answer_of(button):
    """"keep" / "bake" / "cancel" - a dialog dismissed answers "cancel". Pure."""
    return _ANSWERS.get(button, "cancel")


def quaternion_layer(record):
    """An ADDITIVE layer accumulating rotation as quaternions: its contribution is no
    per-channel sum, so no cut can be made at it (`keys.quaternion_note`). Pure."""
    return not record.get("override") and record.get("rotation") == "quaternion"


def keepable(records):
    """{layer name: can a cut be made at it}. Pure."""
    return dict((r["name"], not quaternion_layer(r)) for r in records)


def cut_plan(names, keep):
    """[(index into `names`, [the names unmuted for that cut])] bottom to top, the base's cut
    (None, []) first: a cut at every layer that can be kept, and the TOP cut always holding
    every layer, so the whole take is the last thing retargeted (its bake leaves the helper
    bones, the camera and the clip label). [] when no layer can be kept. Pure."""
    kept = [i for i, name in enumerate(names) if keep.get(name, True)]
    if not kept:
        return []
    out = [(None, [])]
    for i in kept:
        out.append((i, list(names[:i + 1])))
    if list(out[-1][1]) != list(names):
        out[-1] = (kept[-1], list(names))
    return out


def folds(names, keep):
    """[(the layer no cut is made at, the layer its motion lands on)] - the nearest kept layer
    above it, else the topmost kept one below. Pure."""
    kept = [i for i, name in enumerate(names) if keep.get(name, True)]
    out = []
    for i, name in enumerate(names):
        if keep.get(name, True):
            continue
        above = [j for j in kept if j > i]
        below = [j for j in kept if j < i]
        if above:
            out.append((name, names[above[0]]))
        elif below:
            out.append((name, names[below[-1]]))
    return out


def times_of(times, start, end, tolerance=TOLERANCE):
    """The frames a cut is keyed at: its layer's own key times inside [start, end], deduped and
    sorted; `start` alone when it has none (a layer holding a constant offset). Pure."""
    pool = sorted(float(t) for t in times if start - tolerance <= t <= end + tolerance)
    out = []
    for t in pool:
        if not out or t - out[-1] > tolerance:
            out.append(t)
    return out or [float(start)]


#  a transform channel's whole family: a rotate triple read in part and written in part mixes
#  two eulers of the same rotation (measured 2026-10-29: a finger control 540 deg out, because
#  the retarget's `delete -staticChannels` keyed rotateZ in one cut and rotateX in another)
FAMILIES = (("translateX", "translateY", "translateZ"),
            ("rotateX", "rotateY", "rotateZ"),
            ("scaleX", "scaleY", "scaleZ"))
ROTATES = FAMILIES[1]
TURN = 360.0


def triples(plugs):
    """`plugs` with each transform channel's whole family beside it, in order. Pure."""
    out, seen = [], set()
    for plug in plugs:
        node, _dot, attr = plug.rpartition(".")
        family = [f for f in FAMILIES if attr in f]
        for name in (family[0] if family else (attr,)):
            whole = node + "." + name
            if whole not in seen:
                seen.add(whole)
                out.append(whole)
    return out


def fill_gaps(readings):
    """Every reading given a value for every plug ANY reading holds: a channel a cut left
    static (the retarget's `delete -staticChannels`) carries no key there, and a layer's offset
    is measured against the base's value for that very channel - so a plug the base does not
    hold would be measured against whatever the last cut left. The stand-in is the first
    reading's own value for it, which for a channel no cut animates is that value. Pure."""
    every = []
    for reading in readings:
        for plug in reading.values:
            if plug not in every:
                every.append(plug)
    for reading in readings:
        for plug in every:
            if plug in reading.values:
                continue
            donor = next((r.values[plug] for r in readings if plug in r.values), None)
            if not donor:
                continue
            value = donor[sorted(donor)[0]]
            reading.values[plug] = dict((t, value) for t in reading.times)
    return readings


def align_turns(readings, rotates=ROTATES):
    """Every cut's rotate values snapped onto the turn the FIRST cut's are on: each retarget
    lands on its own turn count (its euler filter makes each curve continuous from its own
    first key), so a later cut's euler can sit a whole turn away - the same rotation written
    with 721 deg where the first cut wrote 1.4. A whole turn added to one channel leaves the
    rotation alone, and the layer's offset comes out small. Pure."""
    if not readings:
        return readings
    first = readings[0].values
    for reading in readings[1:]:
        for plug, per in reading.values.items():
            if plug.rpartition(".")[2] not in rotates or plug not in first:
                continue
            mine, theirs = per, first[plug]
            if not mine or not theirs:
                continue
            turns = round((theirs[sorted(theirs)[0]] - mine[sorted(mine)[0]]) / TURN)
            if turns:
                for t in list(mine):
                    mine[t] += turns * TURN
    return readings


#  a channel whose cut differs from the one below it by less than this is the retarget's own
#  repeatability (measured 2026-10-29: 0.0006 deg over a whole take), not the layer's offset
TRIM = 1e-3


def trim_layers(readings, tolerance=TRIM):
    """Each layer's reading kept to the channels whose values differ from the cut BELOW it at
    its own key times: a layer then carries the offset its own layer carried (and whatever the
    retarget spreads from it - a spine offset moves the IK hands too), not every channel of the
    take. Every reading must cover the other's times (`_arrive` captures them all). Pure."""
    out = []
    for position, reading in enumerate(readings):
        if reading.index is None or position == 0:
            out.append(reading)
            continue
        below = readings[position - 1].values
        kept = {}
        for plug, per in reading.values.items():
            under = below.get(plug) or {}
            for frame in reading.times:
                if frame not in per:
                    continue
                if frame not in under or abs(per[frame] - under[frame]) > tolerance:
                    kept[plug] = per
                    break
        out.append(Reading(reading.index, kept, reading.times, reading.tangents))
    return out


def tangent_flags(in_type, out_type):
    """The `keyTangent` flags for one key's types: Maya refuses `step` / `stepnext` as an IN
    type (`keys._NO_IN_TYPES`), so that one is left to Maya. Pure."""
    flags = {}
    if in_type and in_type not in ("step", "stepnext"):
        flags["inTangentType"] = in_type
    if out_type:
        flags["outTangentType"] = out_type
    return flags


def stored_keys(per_time, times, tangents):
    """[[time, value, in type, out type]] of one channel - what `keys.write_raw` takes. Pure."""
    out = []
    for frame in times:
        if frame not in per_time:
            continue
        in_type, out_type = tangents.get(frame, (None, None))
        out.append([frame, per_time[frame], in_type or "auto", out_type or "auto"])
    return out


def times_word(count):
    """«once» / «twice» / «4 times» - the dialog says how often the retarget runs. Pure."""
    return {1: "once", 2: "twice"}.get(count, "%d times" % count)


def question(old_label, new_label, records, first_person, cuts, folded):
    """The dialog's text. Pure."""
    names = ", ".join(r["name"] for r in records)
    lines = []
    if first_person:
        lines.append("{0} stands in 1P (Tools > 1P Setup): its take lives on {1}.".format(
            old_label, names))
        lines.append("")
        lines.append("{0}: the whole take is retargeted onto {1} and 1P Setup is run again on"
                     " it - the two layers, the chest control, the camera and the display"
                     " layers come back.".format(KEEP, new_label))
    else:
        lines.append("{0} carries {1} animation layer{2}: {3}.".format(
            old_label, len(records), "" if len(records) == 1 else "s", names))
        lines.append("")
        lines.append("{0}: {1} gets the same stack, each layer retargeted in turn, and keys"
                     " only where {2} had them. The retarget runs {3}.".format(
                         KEEP, new_label, old_label, times_word(len(cuts))))
    for name, into in folded:
        lines.append("    {0} cannot be kept on its own - its motion lands on {1}.".format(
            name, into))
    lines.append("")
    if first_person:
        lines.append("{0}: one take on the base layer, as the scene shows it now (the chest"
                     " stabilized), and no 1P setup.".format(BAKE))
    else:
        lines.append("{0}: one take on the base layer, a key on every frame - what the scene"
                     " shows now.".format(BAKE))
    return "\n".join(lines)


def nothing_kept(records):
    """The notes for a stack no road can keep - its layers named with the reason, so a press
    that quietly baked them says why (a quaternion layer: its contribution is no per-channel
    sum). [] when something could be kept. Pure."""
    keep = keepable(records)
    if not records or any(keep.values()):
        return []
    return [NOT_KEPT % (r["name"], "it accumulates rotation as quaternions")
            for r in records if not keep[r["name"]]]


def rename_layers(made, records):
    """The layers we made given their records' own names, once the old character (and its
    layers) is gone: Maya's `animLayer` answers `Fix1` while the old rig's `Fix` still stands,
    and the animator's layer should keep the name it had. The names we end up with, in order; a
    name still taken is left as it is."""
    out = []
    for name in made:
        wanted = wanted_name(name, records)
        if wanted is None or not cmds.objExists(name) or cmds.objExists(wanted):
            out.append(name)
            continue
        try:
            out.append(cmds.rename(name, wanted))
        except RuntimeError:
            out.append(name)
    return out


def wanted_name(made, records):
    """The record `made` was made for - its own name, or that name with the digits Maya added
    when it was taken (`Fix` -> `Fix1`); None for a name no record asked for. Pure."""
    for record in records:
        name = record["name"]
        if made == name:
            return None                      # it already has it
        if made.startswith(name) and made[len(name):].isdigit():
            return name
    return None


def extra_1p(records):
    """The layer names of a rig in 1P that are NOT the 1P Setup's own
    (`curvedata.FIRST_PERSON`) - a layer of the animator's, whose motion the 1P road folds into
    the split and which the line names. Pure."""
    from maya_poselib import curvedata
    return [r["name"] for r in records
            if not r["name"].startswith(curvedata.FIRST_PERSON)]


def plan_of(records, first_person, new_is_rig):
    """The Plan for a swap: `first_person` only when the old rig is in 1P AND the new character
    is a rig (a skeleton cannot be 1P set up, so it takes the cuts); else the cuts. Pure."""
    if not records:
        return Plan([], [], [], False)
    if first_person and new_is_rig:
        return Plan(list(records), [], [], True)
    keep = keepable(records)
    names = [r["name"] for r in records]
    return Plan(list(records), cut_plan(names, keep), folds(names, keep), False)


def line_of(made, notes):
    """What the status line says about the layers, "" when none were made and nothing said."""
    parts = []
    if made:
        parts.append(KEPT % ", ".join(made))
    parts.extend(n for n in notes if n)
    return "  |  ".join(parts)


# ------------------------------------------------------------------ the question

_ASKER = None


class Cancelled(Exception):
    """The animator pressed Cancel in the layers question."""


def set_asker(fn):
    """Install (or clear, with None) the answerer the dialog defers to - the verifies' seam."""
    global _ASKER
    _ASKER = fn


def can_ask():
    """A dialog can stand: an answerer is installed, or Maya has a UI."""
    if _ASKER is not None:
        return True
    try:
        return not cmds.about(batch=True)
    except Exception:                                        # noqa: BLE001
        return False


def ask(text):
    """The animator's button."""
    if _ASKER is not None:
        return _ASKER(text)
    return cmds.confirmDialog(title=TITLE, message=text, button=list(BUTTONS),
                              defaultButton=KEEP, cancelButton=CANCEL, dismissString=CANCEL)


def choose(plan, old_label, new_label):
    """"keep" or "bake"; `Cancelled` for Cancel. A character with no layer, or with no road to
    keep what it has, is never asked - "bake", which is the swap's own road."""
    if not plan.records or not (plan.cuts or plan.first_person):
        return "bake"
    if not can_ask():
        return "bake"
    answer = answer_of(ask(question(old_label, new_label, plan.records, plan.first_person,
                                    plan.cuts, plan.folds)))
    if answer == "cancel":
        raise Cancelled(old_label)
    return answer


# ------------------------------------------------------------------ scene: reading

def base_layer():
    """The `keys.Layer` of Maya's own root layer, or None in a scene with no layers. A scene
    tab's root holds no curves of its own (trap 279): the root Maya answers is the base."""
    from maya_poselib import keys
    root = cmds.animLayer(query=True, root=True)
    if not root:
        return None
    return keys.Layer(root, True, False, False, False)


def base_name():
    """Maya's root layer's name, or None - what `keys.write_raw` takes for the base."""
    return cmds.animLayer(query=True, root=True) or None


def layers_of(nodes):
    """[layer name] above the base, bottom to top, holding any channel of `nodes` - the old
    character's own layers, the ones a swap has to carry."""
    from maya_poselib import keys
    wanted = set()
    for node in nodes:
        found = cmds.ls(node, long=True) or []
        wanted.add(found[0] if found else node)
    out = []
    for name in keys.layer_stack()[1:]:
        for plug in keys.layer_plugs(name):
            if plug.rsplit(".", 1)[0] in wanted:
                out.append(name)
                break
    return out


def records_of(names):
    """[`curvedata.layer_record`] of `names`, in order."""
    from maya_poselib import keys
    return [keys.layer_record(name) for name in names]


def mutes_of(names):
    """{layer name: its own mute} - what `restore_mutes` puts back."""
    out = {}
    for name in names:
        try:
            out[name] = bool(cmds.animLayer(name, query=True, mute=True))
        except RuntimeError:
            pass
    return out


def set_mutes(names, on):
    """Every layer of `names` muted but those in `on` - the stack cut for one bake."""
    wanted = set(on)
    for name in names:
        try:
            cmds.animLayer(name, edit=True, mute=name not in wanted)
        except RuntimeError:
            pass


def restore_mutes(saved):
    """The mutes `mutes_of` read, put back - a layer the old character shares with somebody
    else was muted for our bakes only."""
    for name, mute in saved.items():
        try:
            cmds.animLayer(name, edit=True, mute=mute)
        except RuntimeError:
            pass


def curves_on(name, plugs, keys_module=None):
    """The curve nodes the layer `name` (None: the base) holds for `plugs`."""
    if keys_module is None:
        from maya_poselib import keys as keys_module
    out = []
    for plug in plugs:
        try:
            curve = keys_module.curve_for(plug, name)
        except RuntimeError:
            continue
        if curve and curve not in out:
            out.append(curve)
    return out


def source_curves(layer, nodes):
    """The curve nodes the old character's layer `layer` holds - `None` the base's: every curve
    feeding `nodes` whose output is not a layer's own input (`inputB*` of a blend node), which
    is one `listConnections` a curve rather than one `curve_for` a channel. `EVERY` is the base's
    and every layer's together, which is what the 1P road's one cut is keyed at - a rig in 1P
    keeps one pose on its base and the take itself on the two layers."""
    if layer == EVERY:
        return list(cmds.keyframe(nodes, query=True, name=True) or [])
    if layer is not None:
        from maya_poselib import keys
        wanted = set()
        for node in nodes:
            found = cmds.ls(node, long=True) or []
            wanted.add(found[0] if found else node)
        plugs = [p for p in keys.layer_plugs(layer) if p.rsplit(".", 1)[0] in wanted]
        return curves_on(layer, plugs)
    out = []
    for curve in cmds.keyframe(nodes, query=True, name=True) or []:
        where = cmds.listConnections(curve + ".output", source=False, destination=True,
                                     plugs=True) or []
        if any(plug.rsplit(".", 1)[-1].startswith("inputB") for plug in where):
            continue
        if curve not in out:
            out.append(curve)
    return out


def times_and_tangents(curves, start, end):
    """([times], {time: (in, out)}) of `curves`' keys inside [start, end]: the frames a cut is
    keyed at (`times_of`) and the tangent types the source keys had there, where they agree
    (`fkik.tangents_at`'s rule - never `fixed`)."""
    from maya_scenesetup import fkik
    rows = []
    for curve in curves:
        times = cmds.keyframe(curve, query=True, timeChange=True) or []
        ins = cmds.keyTangent(curve, query=True, inTangentType=True) or [None] * len(times)
        outs = cmds.keyTangent(curve, query=True, outTangentType=True) or [None] * len(times)
        rows.append(list(zip(times, ins, outs)))
    times = times_of([t for row in rows for t, _i, _o in row], start, end)
    tangents = dict((t, fkik.tangents_at(rows, rows, t)) for t in times)
    return times, tangents


def animated_plugs(nodes, keyed_only=True):
    """The keyable channels of `nodes`, those carrying keys when `keyed_only` - what a cut's
    reading covers (the new character's take) and what the old character's layers are read
    for."""
    out = []
    for node in nodes:
        for plug in cmds.listAnimatable(node) or []:
            if not keyed_only or cmds.keyframe(plug, query=True, keyframeCount=True):
                out.append(plug)
    return out


def capture(plugs, times):
    """{plug: {time: value}} read off the curves a retarget has just left. The controls carry
    no constraint once the retarget's bake has disconnected its holder, so a context read is
    the curve's own value."""
    out = {}
    for plug in plugs:
        try:
            out[plug] = dict((t, cmds.getAttr(plug, time=t)) for t in times)
        except RuntimeError:
            continue
    return out


# ------------------------------------------------------------------ scene: writing

def write_base(values, times, tangents, keys_module=None):
    """The base's cut written as the curves it is: one `keys.write_raw` a channel, so every key
    time and tangent type travels in one call whatever the take's length. (plugs keyed, notes)."""
    if keys_module is None:
        from maya_poselib import keys as keys_module
    layer = base_name()
    keyed, notes = [], []
    for plug, per in values.items():
        stored = stored_keys(per, times, tangents)
        if not stored:
            continue
        written = keys_module.write_raw(plug, layer, stored)
        notes.extend(written.notes)
        keyed.extend(written.plugs)
    return keyed, notes


def write_layer(record, values, times, tangents, keys_module=None):
    """One made layer carrying its cut: `keys.write` hands Maya the FINAL value at each frame
    and Maya works out what the layer must hold (trap 205), then the source's tangent types are
    set on the keys that landed. (the made layer's name, plugs keyed, notes).

    The layer is made UNMUTED - a muted layer shows nothing, so a final value would mean
    nothing while writing it - and its own mute set after its keys."""
    if keys_module is None:
        from maya_poselib import keys as keys_module
    wanted = dict(record)
    wanted["mute"] = False
    name = keys_module.make_layer(wanted)
    notes, keyed = [], set()
    if abs(float(record.get("weight", 1.0))) < 1e-9:
        notes.append(EMPTY % name)
    else:
        layer = keys_module.Layer(name, False, not record.get("override"), False,
                                  record.get("rotation") == "quaternion", False,
                                  float(record.get("weight", 1.0)))
        for frame in times:
            at = dict((plug, per[frame]) for plug, per in values.items() if frame in per)
            if not at:
                continue
            written = keys_module.write(at, frame, layer)
            notes.extend(written.notes)
            keyed.update(written.plugs)
            flags = tangent_flags(*tangents.get(frame, (None, None)))
            if not flags or not written.plugs:
                continue
            curves = curves_on(name, written.plugs, keys_module)
            if curves:
                try:
                    cmds.keyTangent(curves, time=(frame, frame), **flags)
                except RuntimeError:
                    pass
    if record.get("mute"):
        try:
            cmds.animLayer(name, edit=True, mute=True)
        except RuntimeError:
            pass
    return name, sorted(keyed), notes


def write_stack(readings, records, progress=None, keys_module=None):
    """The cuts' readings written onto the new character bottom to top: the base's curves
    first (no layer stands above them yet), then each layer made and keyed.
    (made layer names, notes)."""
    if keys_module is None:
        from maya_poselib import keys as keys_module
    made, notes = [], []
    by_index = dict((r.index, r) for r in readings)
    base = by_index.get(None)
    if base is not None:
        _keyed, said = write_base(base.values, base.times, base.tangents, keys_module)
        notes.extend(said)
    for index, record in enumerate(records):
        reading = by_index.get(index)
        if reading is None:
            continue
        if progress is not None and not progress.step("the %s layer" % record["name"]):
            break
        name, _keyed, said = write_layer(record, reading.values, reading.times,
                                         reading.tangents, keys_module)
        made.append(name)
        notes.extend(said)
    return made, notes


# ------------------------------------------------------------------ scene: 1P

def in_1p(rig, module=None):
    """Is `rig` standing in 1P - Tools > 1P Setup's chest knot marked with its namespace?"""
    if rig is None:
        return False
    if module is None:
        try:
            from maya_tools import firstperson as module
        except ImportError:
            return False
    try:
        return bool(module.chest_of(rig))
    except Exception:                                        # noqa: BLE001
        return False


def split_again(rig, module=None):
    """Tools > 1P Setup run again on the new `rig` - its take is the old rig's 3P one, so the
    tool's own split gives the two layers, the chest control, the camera, the IK arms and the
    display layers back. (line, failure)."""
    if module is None:
        from maya_tools import firstperson as module
    try:
        line = module.setup(selection=[rig.main])
    except Exception as error:                               # noqa: BLE001
        return "", (str(error).strip().splitlines() or ["1P Setup failed"])[0]
    text = (line or "").strip()
    lowered = text.lower()
    if lowered.startswith("1p setup:") or lowered.startswith("no ") or " refused" in lowered:
        return "", text
    return SPLIT_AGAIN % (rig.namespace or "the new rig"), ""
