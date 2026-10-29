# Pose Library — original curves and layers in animation cards (2026-10-28)

The animator: «А мы можем так сделать что бы наша библеотека поз потдерживала сохранения по слоям и
сохранения ключей?» — then, on the design below, «давай сделаем» and «Да, пиши спек».

Asked and answered:

| question | answer |
|---|---|
| what «по слоям» means | the question was cut off; the design answers both readings: a card holds EVERY layer the character's channels sit in, and the paste picks which of them go in (all by default) — the whole stack, or one layer's correction laid over another take |
| what «ключи» means | the source's OWN keys — times, values, tangents (angles and weights), breakdowns, infinity — not the solved frames the card holds today |
| onto which targets | the same rig model only (controls paired by name); every other target is pasted as today, through the bones |

Read the animation spec first (`2026-10-03-pose-library-animation-design.md`): every rule there holds
unless this spec says otherwise.

## What exists, and what is missing

A CHARACTER animation card holds each bone's world on every frame (`frames.json.gz`) — what the scene
SHOWED, every layer summed — and the source's key times (`key_times`). A paste solves those bones onto
any rig or skeleton and keys the active layer: on every frame, or («Source keys») at the source's key
times with values solved there and Maya's tangents between. The source's own curves, their tangents and
its layers are lost.

An OBJECTS card already holds a plainly keyed channel's curve with its tangents (`_copied`), but a
channel in animation layers is sampled on every frame (`_sampled`) — flattened.

«Layer creation for the paste» is in the animation spec's «Not built». This spec builds it.

## What a card gains

**Save always reads the curves** when the character (or object) has any — no option, no checkbox.
The bones' frames, `key_times`, the still and the preview are read exactly as today: they are what a
paste onto another rig, and an older build, still use.

`curves.json.gz` — a new file in the `.anim` card, beside `frames.json.gz`, written before `anim.json`
through `.part` + `os.replace` like every other card file; read only by Apply (cached by path + mtime,
one entry, as `read_frames`):

```
{"version": 1,
 "nodes": [{"name": leaf without namespace, "attrs": {attr: {layer name: CURVE}}}]}
```

The LAYERS live in the header (`anim.json`'s `curves.layers`, below) — the controls' and the objects'
layered curves name the same records, and the window lists them without opening the file.

- `LAYER` = `{"name", "base": bool, "override": bool, "weight": float, "mute": bool,
  "rotation": "component" | "quaternion", "scale": "multiply" | "additive"}` — the layer's name without
  its namespace (a scene tab puts its layers in one), its mode, its weight at the frame the save stood
  on, its own mute, and its accumulation modes. The base is ALWAYS `{"name": "BaseAnimation", "base":
  true}`, whatever the scene's root is called (a scene tabs session's root is `skeldarTabsLayerRoot`);
  a scene with no layers has that one record — the plain curves are the base.
- `CURVE` is the objects card's CURVE (`{"keys": [[t, v, inType, outType, inAngle, inWeight,
  outAngle, outWeight]...], "weighted", "breakdown"}` or `{"static": v}`), with two additions:
  `"pre"` / `"post"` — the curve's infinity in `setInfinity`'s spelling (`keys._INFINITY`).
- the values are the LAYER CURVE's own (an additive layer's offset, an override layer's value), never
  the final value — that is what lets the tangents travel whole (today a key written as a final value
  onto a layer keeps only its tangent TYPES, `keys.write_keys`).

`anim.json` gains `"curves": {"layers": [LAYER...], "nodes": n}` — the layers bottom to top, the base
first, holding only the layers some saved curve sits in; `nodes` the controls / joints / objects whose
curves the card keeps. A character card writes it (and `curves.json.gz`) whenever a channel of its
controls or joints holds a curve; an objects card writes it (and no `curves.json.gz`: its curves stay in
the header) only when a channel sits in a non-base layer — its plain curves are pasted exactly today
already. An older build ignores the key and the file;
the installer moves a card folder file by file (`install.card_files`), so the new file travels with no
change there.

### Which channels

- **A rig**: the ControlSet's controls whose bones (`scene._control_bones`, the rule a selected control
  already follows) meet the card's members; `Main` (`_WHOLE`) only with a whole-body card. Each
  control's keyable unlocked scalar channels (`objects.channel_names`).
- **A skeleton**: the member joints' channels.
- **Objects** (an objects card, and the objects saved beside a character): each channel the card holds
  today. A plain curve keeps today's CURVE in the header; a LAYERED channel keeps today's sampled
  CURVE (an older build, and the default paste, still read it) and gains `"layers": {layer name:
  CURVE}` beside its keys.
- Per channel and layer: the curve `keys.curve_for(plug, layer)` answers (the base falls back to the
  plug's own curve), read off a DUPLICATE with a shape-keeping key inserted at each end of the range
  (`_copied`'s road, unrecorded); a layer that holds the plug without a curve answers nothing and is left
  out; a channel no curve feeds on any layer is `{"static": v}` on the base. A channel a constraint, an
  expression or a driven key feeds holds no curve to copy: left out of the curves and named in the
  save's line (the bones' frames still carry what it did).
- A layer enters the card only when it holds a curve of one of the card's channels: each layer above the
  base is asked for the plugs it holds (`animLayer -q -attribute`, one query a layer) and only those
  plugs are looked up on it — another character's layers, and another scene tab's, never enter the
  card. A scene tab's root (`keys._tab_root`) is no layer of the card; the session root's curves are
  the base.

**Cost**: one duplicate per curve per layer. The plan measures Manny_Rig, whole body, three layers,
100 frames; past 2 s the read moves to `OpenMayaAnim.MFnAnimCurve` (no duplicates) with the end keys
computed from the curve's own evaluation.

## Paste

A new option under Apply, shown only for a card that holds curves, remembered as the others
(`skeldarPoseLibraryPasteAs`):

| option | values | default |
|---|---|---|
| **Paste as** | character card: `Retarget` · `Original curves`; objects card: `Active layer` · `Original curves` | `Retarget` / `Active layer` — today's paste, untouched |

Under `Original curves`, a checklist of the card's layers (`anim.json`'s `curves.layers`), every one on;
at least one must stay on. While `Original curves` is chosen, **Keys**, **Mirror** and **Blend** are
greyed with a tooltip that says why: the curves carry their own keys, and a mirror or a blend changes
values, which is exactly what this paste exists not to do. Blend's slider stays at 100 %.

### Which target takes the curves

- A character target takes them when it is the SAME MODEL and kind as the card's character
  (`character.model`, `character.kind`); its controls (a rig) or joints (a skeleton) are paired by leaf
  name without namespace. A control the target lacks is skipped and named.
- Any other target in the same press is pasted by `Retarget` (with the window's Keys choice) and the
  line says so — one press can hold both. Such a mixed press is TWO undo steps (the curves' chunk, then
  the retarget's own): the retarget's cancel undoes its own chunk, and a chunk inside a chunk would
  undo the other's work with it.
- Objects pair as today (`_objects_pairs`); under `Original curves` a plain channel's curve goes to the
  base (not the active layer) and a layered one's to its layers, by the rules below.
- **Selected only** keeps the selected controls' channels; **In place** leaves the target's `Main` (a
  rig) or root joint (a skeleton) unkeyed — the pose rule.

### Which layer takes each card layer

- The card's base goes to the target's base: `BaseAnimation` when the scene has layers, the plain
  curves when it has none.
- Every other checked card layer goes to the target layer of the SAME NAME (namespace ignored) when
  that layer has the same mode and rotation accumulation; else a NEW layer is made with the card's mode,
  weight, mute and accumulations, under Maya's next free name when the name is taken (the line names it).
  It is made as the Tools' layer bake makes its own (`cmds.animLayer(name)`, on top of the stack); with
  scene tabs on, the tabs' layer hook moves it under the current tab's root one idle later
  (`maya_scenetabs.hooks.on_layer` → `layers.adopt`) — as for every layer the Tools make.
  Layers are made bottom to top in the card's order, so the stack reads as it did.
- An existing layer keeps the weight and mute the animator gave it — only a layer the paste MAKES takes
  the card's.
- A locked target layer refuses its card layer before anything is written (`keys.LOCKED`), as today.
- A nested source stack is pasted flat, in its order (nesting is not stored).

### The keys

Per pasted channel and card layer, on that layer's curve of the target plug:
- the paste mode first, on THAT layer's curve only (`keys.cut` / `keys.shift` take the layer today):
  Replace cuts `[a, b]`, Replace all every key, Insert moves every key at or after `a` by the clip's
  length, Merge cuts nothing. A card layer left unchecked, and every target layer the card does not
  name, is never cut or moved — as today «Other layers' curves are never touched»;
- the keys: the CURVE clipped to the paste's source range and moved to the paste's time
  (`animapply._object_keys` — At current time and Range work as for objects), the plug added to a
  non-base layer first (`animLayer -e -attribute`), then each key written as the LAYER CURVE'S value with
  every tangent, weight, breakdown and the curve's infinity and weighting. The writing road (keying the
  layer's curve node, or `MFnAnimCurve`, rather than `setKeyframe -value`, which takes a final value) is
  measured first in the plan: a raw value onto an additive, an override and a quaternion layer, and onto
  the base under a layer, each read back key for key;
- `{"static": v}`: one key at `a`, on the base.

**Connect** works when the paste writes ONE layer (a card with only a base, or one layer checked):
after the keys, each channel's pasted keys on that layer move by `(shown before the press − shown now)`
at `a`, over the layer's weight on an additive or override layer (weight 0: no Connect, said). A
quaternion layer's rotate channels take no Connect (said). With two or more layers checked, Connect is
greyed.

**The press** keeps the animation spec's order and its undo rules: one chunk (the layers it makes
inside it), autoKey off, refusals before anything is written (a locked layer, an empty range, no
layer picked), the paste mode, the keys, Cancel undoes the chunk. A `curves.json.gz` that is missing
or broken (`curvedata.check` against the header's layers) is never half pasted: every target goes
through the bones, and the line says the card's curves could not be read. No time walk is needed for the
curves; the progress window steps once per channel.

The status line: «Original curves onto Manny_Rig1: 73 controls, BaseAnimation + AnimLayer1 (made),
frames 12-59 (replace) | Orc_Rig1: retargeted, every frame | notes». Nothing is measured — the curves
are the source's, key for key.

## The window

- The details of a card with curves add a line under its frames: «original curves · BaseAnimation,
  AnimLayer1».
- The options block gains **Paste as** and, under it, the layer checklist, both shown only for a card
  with curves; the greying above follows the choice.

## Not built

Curves and layers for POSE cards (a pose is one frame), mirroring original curves, pasting original
curves onto another rig model, a layer's keyed WEIGHT (its value at the save is kept), nested layers
(pasted flat), retiming.

## Verification

- unit tests (`tests/test_poselib_*.py`, the fake `cmds`): the curves file's shape and its reading
  (a broken file is a broken card, never a half paste), which channels a card keeps for a member list,
  the layer pairing (same name and mode; a different mode makes a new one; a locked one refused), the
  options and their greying, Connect's single-layer rule;
- mayapy (`docs/superpowers/plans/verify_poselib_curves.py`): Manny_Rig with a base take, an additive
  and an override layer (weighted tangents, a breakdown, a fixed tangent, cycle post-infinity) saved
  whole body and as one arm; pasted onto Manny_Rig1 with no layers, with an AnimLayer1 of the other
  mode, with only AnimLayer1 checked, under Replace / Insert / Merge, At current time and Range — every
  curve key for key (time, value, tangents, weights, breakdowns, infinity) on every layer, and every
  layer's mode, weight and mute; the same card onto a skeleton retargeted with the note; an objects card
  of a layered locator pasted per layer (gated as made and keyed, not key for key); one Ctrl+Z takes each paste back, layers made included; the curves
  read on the whole rig (every control keyed, three layers, every curve cut by the range) measured against
  the 2 s budget - the bone walk's per-frame cost is the animation cards' own, unchanged here.

## Measured

The plan's probe (`docs/superpowers/plans/probe_poselib_raw_layer_keys.py`, 27/27, mayapy standalone):
- **The raw road**: keying the curve node, `setKeyframe <curve> -time t -value v`, writes `v` as the
  layer curve's own value on an additive, an override and a quaternion layer and on the base under a
  layer, in UI units (degrees for rotate); a key standing at `t` is replaced; fixed tangent angles and
  weights set after the keys hold. No `MFnAnimCurve` fallback was needed. Rotation values come back with
  float noise (`-29.999999999999996`), so readers compare with a tolerance.
- **The plug spelling**: `animLayer -q -attribute` answers `node.longAttr` (`probe.translateX`),
  measured on a root-level node with a unique short name only.
- **The enums**: `rotationAccumulationMode` is `By Component:By Layer` (0 / 1), `scaleAccumulationMode`
  is `Additive:Multiply` (0 / 1), and a new layer's scale mode is 1 (Multiply).

The end-to-end verify (`verify_poselib_curves.py`, 45/45) and the older ones:
- the 0..30 whole-rig save: 1.46 s (under the 2 s budget);
- the curves read on a whole keyed rig (every control keyed, 188 nodes, three layers, 101 frames, every
  curve cut by the range): 0.50 s - inside the budget, so the
  `MFnAnimCurve` read was not built;
- the whole 101-frame save: 4.57 s, of which ~4 s is the pre-existing per-frame bone walk (~40 ms a
  frame; 2.11 s was measured over the 51-frame 5..55 save) and 0.50 s the curves read; the 2 s budget
  does not cover the walk; a faster walk is a separate follow-up;
- `verify_poselib_anim.py` 113/113; unit suite 12005 tests, one unrelated failure (`test_chat_deploy`);
  `verify_poselib_objects.py` 2/6 on main b4a91cd as well (`SceneSetup_camera` locked translateX).

## Amended 2026-10-29: what a paste lands

The animator reported three bugs the day after: the layers missing after the card's character was
deleted and a new one added, a layered 3P card wrong on a rig in 1P, and the rig's controls twisting
«when objects are added to an animation layer ... on Merge». Measured on the BONES (each bone of the
target, relative to the root, against the card's frames), six causes; the rules they amend:

- **Which target takes the curves** (amends «Which target takes the curves»): a rig in 1P (Tools > 1P
  Setup: a chest knot marked with its namespace) is retargeted, said - its take is split over the 1P
  layers and the chest knot, raw curves stood the upper body 110-120 deg off. A card saved off a rig in
  1P (its `curves` block's `first_person`, or an older card's `_3P_Lower_Body` / `_3P_Upper_Body`
  layers) takes no curves anywhere (180 deg on a 3P rig): Paste as is not offered for it and a press
  asked for curves retargets and says so.
- **Which channels** (amends «Which channels»): a layer that holds a channel WITHOUT a curve - what Add
  Selected Objects leaves - keeps its static value on the card (`{"static": v}` for that layer: 0 on
  an additive layer, the value at the add on an override one, which hides the base); the base keeps
  its static under keyed layers too. An override layer's frozen channels twisted an arm 73 deg.
- **The keys** (amends «The keys»): over the paste range the card's channels show what the card
  showed. A namesake layer the paste writes is cleared on the card channels its card layer did not
  hold; with the base pasted, every other unmuted layer of the target holding a card channel is
  cleared over the range too (Replace / Replace all / Insert: the mode's ops, then identity keys at
  both ends; said). **Merge clears nothing** and says which layers still add; an override layer cannot
  be cleared by a key and is named. With the base unticked no other layer of the target is touched.
- The range is held against the target's keys outside it: a curve shorter than the range gets a
  stepped hold key at the end, an end key beside a target key keeps the tangent angles it showed, and a
  layer curve the paste makes is bounded to the range (identity a frame either side) where the channel
  moves outside it - its last offset held over the rest of the take.
- **Characters > Delete in a scene tab** keeps the tab's layer root and the tab's current namespace (a
  delete left the root namespace current and the next Add Character landed outside the tab).
- The current frame is re-evaluated after the paste (it kept the old pose until the time moved).

Proof: `docs/superpowers/plans/verify_poselib_curves_layers.py` 51/51.
