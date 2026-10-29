# A rig swapped for another keeps its layers, or bakes them (2026-10-29)

The animator: «Сейчас наша библеотека умеет переносить аниации по слоям. Нужно реализовать
аткой же функционал при подмене ригов. Если на риге есть слои и мы мняем один риг на другой
каким-то из способов то нужно сделать атк что бы система спросила у нас хотим ли мы сохранить
ключи с лои или запечь всю анимацию. В случе с переносом рига на 1p версию перенос должен
сработать корректно»

Asked, and answered:

- **1P is the OLD rig**: «Старый риг в 1P» - the character being swapped has been through
  Tools > 1P Setup (its take on `_3P_Lower_Body` / `_3P_Upper_Body`, Upper muted, the chest on a
  knot, the camera in it), and the new one must come out in 1P too.
- **«Keep the keys and layers» = the layers AND their own key times**: «Слои + свои ключи» - the
  new character gets the same stack (name, mode, weight, mute), each layer retargeted in turn,
  and keys only where that layer of the old character had them. A take blocked on 5 keys stays 5
  keys; a dense take stays dense. Between keys the new rig interpolates on its own, as the
  Connections FK/IK switch does.

Then «делай все до конца я вернусь через час», so every decision below was taken alone.

## What is wrong today

`maya_scenesetup/swap.py` has ONE road for every pair (the 2026-10-17 spec): the old character's
game skeleton is baked into a plain copy, the new character added, the copy retargeted onto it.
The bake reads what the scene SHOWS, so:

- every animation layer is flattened into one dense take on the base layer - the stack, the
  weights, the mutes and the key times are gone;
- a rig in 1P is baked as it looks (Upper muted: the chest stabilized), and the new rig comes out
  with no 1P setup at all - no two layers, no chest control, no camera in the chest, no display
  layers. That is the animator's «перенос рига на 1p версию» not working.

## The question

Asked once, before anything is changed, when the old character's channels are fed by any
non-base animation layer (`layers_of`). Three buttons, `maya_retargetmode`'s pattern (an asker
seam `set_asker` for the verifies, `can_ask`, batch mode answers Bake and the line says so):

| button | what it does |
|---|---|
| **Keep the layers** (default) | the road below |
| **Bake the animation** | today's road, unchanged: one dense take on the base, the scene as it shows now |
| **Cancel** | nothing changed (`swap.CANCELLED`) |

The text names the layers and what each button gives, and for a rig in 1P it says 1P Setup will
be run again. A character with no layers is never asked - today's road, as before.

## Keep: the general road (`swaplayers.keep`)

The layers of the old character, bottom to top, are the CUTS of its stack:

- cut 0 is the base alone (every kept layer muted), cut *i* the base plus layers 1..*i*;
- for each cut the old skeleton is baked into a copy and retargeted onto the new character -
  `swap`'s own `bake_copy` and the bridge's `ready_rig` (which clears the previous take) +
  `retarget_imported`. The proportions question (`decide_bones`) is asked on cut 0 and its answer
  reused for the rest;
- after each retarget the new character's channels are read at THAT layer's own key times
  (`times_of`: the union of the key times of that layer's own curves, clamped to the take and
  snapped to whole frames; the base's own times for cut 0; no key of its own - the range's
  start), with `getAttr(plug, time=t)` off the fresh curves;
- the last cut is the whole stack, so the helper bones, the camera and the clip label that
  `retarget_imported` leaves are the whole take's;
- then the take is cleared once more (`ready_rig`) and the reading WRITTEN bottom to top:
  cut 0's values as plain keys (no layer exists yet), then each layer made
  (`keys.make_layer` with the old record's mode, weight and accumulation modes) and its cut's
  values keyed on it with `keys.write` - **Maya's own arithmetic**: `setKeyframe -animLayer
  -value <final>` writes `final - what the stack below shows`, over the layer's weight (trap
  205), so an additive layer, an override layer and a scale channel each come out right with no
  formula of ours;
- a layer is made UNMUTED and its mute set after its keys: a muted layer shows nothing, so
  `final` would mean nothing while writing it;
- every key's tangent types are then set to what that layer's own curves had on that frame
  (`fkik.tangents_at`'s rule, where the source keys agree, never `fixed`), so stepped blocking
  stays stepped;
- what the new character shows with every layer on is the whole stack retargeted - the same as
  the Bake road at the keys. Mute a layer on the new character and it shows what muting it on the
  old one showed.

Named in the line, never guessed at:

- a layer whose rotation accumulation is **quaternion** cannot be written per channel
  (`keys.quaternion_note`): no cut is made there, so its motion folds into the next kept layer;
- a layer at **weight 0** contributes nothing and is made empty;
- a layer the old character shares with somebody else is muted and unmuted for the bakes only,
  and restored in a `finally`;
- the retarget runs once per cut: the text says how many times before the animator presses.

## Keep: a rig in 1P (`swaplayers.keep_1p`)

A rig in 1P (`firstperson.chest_of`) is not cut layer by layer: its layers are 1P Setup's own
split of a 3P take, and half a split (two layers with no chest control, no camera, no display
layers) would be wrong. Instead:

- every layer of the old rig is unmuted, so the bake reads the **3P** take;
- it is retargeted ONCE onto the new character, with the keys-only rule above (the union of every
  layer's own key times);
- **Tools > 1P Setup is run again on the new rig** (`firstperson.setup`): the two layers, the
  chest knot, the camera in it, the IK arms, the display layers, the crosshair and `Main.view`
  come back from the tool that makes them. The animator's own keys on the upper layer are part of
  the 3P take and are split onto it again by the tool's own rule;
- a third layer of the animator's own is folded into the split and named;
- the new character must be a RIG for this road; a skeleton takes the general road, said.

**Bake** on a rig in 1P stays today's road: the scene as it looks (Upper muted, the chest
stabilized), one dense take, no 1P setup - and the text says exactly that, so the animator is
never surprised by it.

## Where it lives

- **`SkeldarAnim/maya_scenesetup/swaplayers.py`** (new): the pure rules (the layer records, the
  cuts, the times, the question's text, the buttons) and the scene road (the mutes, the capture,
  the write, the 1P press). `swap.py` gains the question and the two calls and nothing else.
- `swap.attach_part` is NOT asked: a part keeps the character and is a fresh rig with no layers.

## Proof

- unit tests for every pure rule (`tests/test_scenesetup_swaplayers.py`), the fake-`cmds`
  pattern of `test_scenesetup_pending.py`, plus a subprocess test that the pure half imports no
  Maya;
- `docs/superpowers/plans/verify_swap_keep_layers.py`, mayapy standalone, a UE clip retargeted
  onto a Manny_Rig:
  - a correction layer keyed on 3 frames, swapped for another model with Keep: the new rig's
    stack holds a layer of the same name, mode and weight; its keys stand on exactly those 3
    frames; with every layer on the new character's bones are where the Bake road puts them (at
    the keys); with the layer muted they are where muting it on the old one put them;
  - stepped keys stay stepped;
  - a dense layer: every frame;
  - an override layer and a weighted layer (0.5) come out right;
  - a quaternion layer folded and named;
  - Bake: today's result, unchanged;
  - Cancel: nothing changed, the old character still playing its layers;
  - 1P: a rig through 1P Setup swapped for another rig with Keep - the new rig in 1P (both
    layers, the chest knot marked with its namespace, the camera in it, the display layers,
    `Main.view` 1), its bones under both layers where the old rig's 3P take put them, and with
    Upper muted where the old rig's 1P look was;
  - no layers: never asked, today's road.

## Not built

- the swap's own road for a PART row (`attach_part`) keeping layers;
- a setting to stop being asked (the animator asked for a question);
- a layer kept by its own curves key for key (raw values across two models put the hands
  elsewhere, and the same model and kind is a no-op swap - that road is the Pose Library's);
- the Connections links the swap already does not carry.
