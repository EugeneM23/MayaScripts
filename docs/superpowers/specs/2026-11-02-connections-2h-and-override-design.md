# Connections, Weapon tab: 2H Weapon, and Override mode

2026-11-02. The animator, two features in the card's Weapon tab:

> «1 - 2H Weapon. Опция (чип/сегмент) в этой же вкладке: "намертво" привяжет
> обе руки к оружию, то есть двуручный хват.»
>
> «2 - Override mode. Галочка в той же вкладке. В этом режиме оружие
> привязывается к груди (spine_03; в 1P-режиме рига грудь - это контрол-кнот
> Chest_1P_ctrl) и даются три настройки: сила наследования вращения, сила
> наследования смещения по позиции и отставание в миллисекундах - так
> получается захлёст оружия.»

Asked, three answers, and they decide the shape:

- **«намертво» means the hand FOLLOWS the weapon** - «Рука следует за оружием»,
  their own words in place of my options - and the mechanics stay what they are
  today: «Прокси, одной кнопкой» (the proxy inside the weapon, the hand's track
  kept, animated on the proxy afterwards; the weapon stays where it stands).
- **Override writes keys, and remembers its settings**: «Ключи, настройки
  помним» - the Aim Mode road, with the three numbers kept on the weapon so a
  knob turned re-writes, as a Walk Builder parameter does.
- **What Override acts on: no preference** - mine to choose, stated below.

## What the tab does today

Read off `maya_scenesetup/connections.py` as it stands (2026-10-29, pick then
press): one caption «Weapon in hands», the `Acts on` chooser, three parent rows
`Hand R [Free|Weapon] v`, `Hand L [Free|Weapon] v`, `Weapon [World|Hand R|Hand L] v`,
one orange `Apply all · N`, then a caption «Aim» with `Aim [Default|Aim Mode] v`.

The model is three nodes and two links: a hand **holds** the weapon (it hangs in
that hand's weapon space; at most one hand), **follows** it (its IK control rides
a proxy inside the weapon's geometry), or neither. A hand holds XOR follows, so a
two-handed grip today is two presses: the weapon into the right hand, then
`Hand L → Weapon`.

Nothing in the tab says anything about the body carrying the weapon. The parent
row's choices are the two hands and the world.

## 1 - 2H Weapon

A chip `2H` in the «Weapon in hands» section, under the three rows.

**It is a shortcut for the two hand rows' picks, and nothing else.** Ticking it
records the picks the animator would set by hand; the rows light `want` at once;
the row's own check or `Apply all` bakes, one undo, down the proxy road that has
been proved since 2026-09-18. There is no new state in the scene, no new bake
path, and no new refusal: 2H is a word for a scheme the model already has.

Which picks, read off the scheme the weapon stands in (`two_hands_picks`, pure):

| the weapon stands | ticked | unticked |
|---|---|---|
| in world | both hands → Weapon | the following hands → Free |
| in the right hand | `Hand L → Weapon` (the right hand carries it already) | `Hand L → Free` |
| with one hand following | the other hand → Weapon | both → Free |

A hand that **holds** the weapon is left holding: it travels with the weapon by
construction, and releasing it would mean moving the weapon out of the hand -
which the animator ruled out («оружие остаётся там, где стоит»). So 2H never
changes the `Weapon` row, and «both hands bound» is true in both readings of the
word: one hand carries, the other rides.

The chip's own lit state is the SCENE (the pick/press rule: a thumb is the state,
a pick is an outline) - lit when every hand is bound to the weapon, `holds` or
`follows` (`two_hands_state`, pure). Ticked as a pick it draws `want`.

## 2 - Override mode

A section «Override» after «Aim»: the chip `Override`, a row of names over a row
of fields - `Rotation` (×), `Position` (×), `Lag` (ms), the Tools card's
`columns` shape - and the section's check at its right. The tab's one orange
stays `Apply all`.

### What it computes

The chest carries the weapon, with an inheritance strength per half and a lag.
For every frame `f` of the span, with `C` the chest's world matrix, `W_own` the
weapon's world track BEFORE the mode (its base), `ref` the span's first frame:

```
W(f) = W_own(f) · C(f)⁻¹ · C(ref) · G(f)
```

`G(f)` is the chest's motion from `ref` to `f − lag`, scaled about the chest's
own pivot:

```
q  = the chest's position at ref
Q  = R(ref)⁻¹ · R(f − lag)            the chest's turn since ref, in world axes
d  = c(f − lag) − c(ref)              the chest's travel since ref
G: p ↦ (p − q) · slerp(I, Q, rotation) + q + d · position
```

The decomposition is about the chest's own pivot on purpose: the translation of
a bare `C(ref)⁻¹ · C(f)` carries the lever arm to the world origin, and scaling
that would throw the weapon off the body.

What the three knobs mean falls out of the formula:

- `rotation 1, position 1, lag 0` → `W(f) = W_own(f)`, **the identity**: the mode
  changes nothing. The repository's own rule - the defaults are the source.
- `lag > 0` at full strength → `W(f) = W_own(f) · C(f)⁻¹ · C(f − lag)`: the weapon
  keeps its pose relative to the chest and takes the chest's pose from earlier.
  That is the overlap the animator asked for.
- `rotation 0` → the weapon does not inherit the body's turn at all; it hangs in
  the chest's reference frame.
- `position 0` → it does not inherit the body's travel.
- Past 1 a strength exaggerates. The fields take any value at or above 0.

**At the start the chest is held**: the read of `C(f − lag)` clamps its time to
`ref`, so the span's first frame is bit-exact and the lag eases in over its
first `lag` frames. A take whose body moves before the span is not read before
it: the weapon starts where it started.

Field defaults: `1 / 1 / 80` ms - a visible overlap on the first press. The line
says when the numbers are the identity.

### Which chest

The rig's `spine_03` bone, resolved in the rig's own skeleton
(`skeleton.resolve_bone`). In 1P the chest control (`Chest_1P_ctrl`) drives that
bone through Tools' knot, so reading the bone reads the control's motion - one
road for both modes, and it works beside a bare skeleton too. With the upper
animation layer muted (1P Setup's own state) the bone is the stabilized chest,
which is exactly what a weapon should inherit there.

### Where the keys go, and on which frames

On the weapon's own `translate` / `rotate` channels, in whatever parent it has -
`helpers.driver_channels` turns each frame's local matrix into (rotate,
translate) honouring the node's rotate order, rotate axis, pivots, shear and
scale, the same writer the Pose Library and `aimcore.aim_off` use, with one Euler
path through the frames in time order so no neighbour is a turn apart.

The frames: the weapon's own keys ∪ the chest's keys inside the span
(`fkik.own_keys`, with their tangents), then the frames between them where the
result stands more than `0.1°` or `0.01 cm` off what the formula wants, until
none does (`aimcore.fill_passes` / `track_off`, Default's own loop). A blocked
take stays blocked; a retargeted take, whose chest is keyed on every frame, is
keyed on every frame.

The span is the playback range ∪ the weapon's keys ∪ the chest's keys, whole
frames. The time walk runs under `maya_timewarp.unwarped()` (scene time warp)
with the viewport suspended.

### The base, and the settings

Both live on the weapon, the way a floor drop parks a bone's track
(`bonedrive.park`, the precedent) - no node of our own:

- `skeldarWeaponOverride` (string): the three numbers, space-joined, as
  `weaponaim`'s `VECTORS` keeps its vectors.
- `skeldarOverrideBase<Channel>` × 6 (`doubleLinear` for a translate,
  `doubleAngle` for a rotate - so no `unitConversion` is spliced in, trap 42):
  the weapon's ORIGINAL animCurves, disconnected from it and connected here, or
  its plain value for a channel that had no curve.

So:

- **enter**: read `W_own` and `C` over the span with the base still connected,
  park the base, write the keys, record the numbers.
- **a knob turned** (the mode stands): the base reconnected, read again, parked
  again, written with the new numbers. The result is derived, the base is the
  source - Walk Builder's rule.
- **Default**: the override's own curves cut, the base reconnected exactly, the
  attributes removed. The round trip is bit-exact, and that is a gate.

A hand edit of the result does not survive a knob turn - it is derived data. The
animator was offered exactly this shape and chose it.

### Where it acts

Wherever the weapon stands. The useful combination, and the one the two features
were asked for together, is `Weapon → World` + `2H`: the chest carries the weapon
late, and both hands ride it, so the whole assembly trails the body - the game's
weapon sway, in two picks and one undo.

In a hand it still computes, and the cost is stated on the line: the holding hand
does not move, so the weapon slides in its grip by the lag. The press says
«in the right hand - it slides in the grip; Weapon → World with 2H keeps the
hands on it».

### Refusals, before anything changes

- no weapon in the scene; the weapon's rotate or translate locked, on animation
  layers, or driven by anything but a time curve - `aimcore.rotate_refusal`'s
  own rule (locked / `fkik._layered` / `fkik._foreign`) over both channel sets,
  since Override writes the translate too;
- **Aim Mode stands** - both write the weapon's rotation: «Default first»;
- the rig has no `spine_03` (or there is no rig for the weapon);
- a retarget standing on the rig (`MoCapConstraints`), as every press of the tab.

### Beside the rest of the card

- **A parent change while Override stands** does what it already does for Aim
  Mode: Default, the steps, Override again, inside the one undo chunk of
  `connections.apply`. So the hands that go onto the weapon take its un-swayed
  track, and the re-entered mode then drags them.
- **Aim Mode's own press** refuses while Override stands, and the other way
  round.
- **The Pose Library** needs nothing: keys on the weapon's own channels are its
  existing `driver` entry, so a card saves and applies the result as it does any
  driven weapon.
- **The export** needs nothing: the drive bone is constrained to the weapon's
  socket, so `weapon_r` takes the sway.

## Modules

- `maya_scenesetup/weaponoverride.py` - new. The pure half (`scaled`, `delayed`,
  `frames_for`, the words) and the scene half (`enter`, `leave`, `state`,
  `park` / `unpark`). `connections.py` is 2660 lines already; the engine does not
  belong in it.
- `maya_scenesetup/pending.py` - one key, `OVERRIDE`, in `TAB["weapon"]`, `_RANK`
  and `phrase`.
- `maya_scenesetup/connections.py` - the `2H` chip (two pure functions and a
  press), the Override row, its pick and its press, the Override leg of
  `apply_weapon` / `Apply all`, and the Default/enter dance in `apply`.

## Proof

`docs/superpowers/plans/verify_weapon_override.py`, mayapy standalone, every gate
printing its number - a Manny rig, a UE clip retargeted onto it, a Long Sword in
the right hand:

1. **the identity**: `1 / 1 / 0` leaves every frame's world matrix as it was
   (target 1e-12);
2. **the lag**: at `1 / 1 / 100 ms` (3 frames at 30 fps), on every frame,
   `W(f) · C(f − 3)⁻¹ = W_own(f) · C(f)⁻¹` - the weapon's pose in the DELAYED
   chest's frame is its base's pose in the chest's frame at `f`. Read from the
   scene's own chest matrices and the two weapon tracks, so it measures the
   claim rather than re-deriving the formula; the control is that the same
   reading at lag 0 differs by the chest's own motion over three frames;
3. **the first frame** is bit-exact whatever the lag;
4. `rotation 0`: the weapon's own world turn over the take falls by the chest's
   contribution - `max angle(R(W(f)), R(W(ref)))` printed at strength 1 and at
   0 beside the chest's own turn over the same take, the three numbers in one
   line;
5. `position 0`: the same reading in cm for the travel;
6. **the keys**: a blocked weapon (3 keys) and a dense chest give keys on the
   union plus the filled frames, with the tangents of the source keys;
7. **Default**: every curve back key for key, value for value, tangent for
   tangent; the attributes gone;
8. **a knob turned** re-writes from the base, not from the previous result (two
   presses at 80 then 160 ms equal one press at 160);
9. **one Ctrl+Z** per press;
10. **the refusals** change nothing (Aim Mode standing, a layered rotate, no
    chest);
11. **a parent change** while Override stands keeps it, and the hands that
    follow are dragged by the sway;
12. **2H**: one press on a world weapon puts both hands on it; on a held weapon
    it puts the other hand on it and leaves the weapon in the hand; the chip's
    lit state reads the scene; unticking releases the followers and leaves the
    holder;
13. **the Pose Library** saves a card off the result and applies it back onto a
    second rig.

Unit tests, new files only: `tests/test_weapon_override.py` (the pure half, the
scene half on a fake `cmds`), `tests/test_connections_two_hands.py` (the picks,
the chip, the card's row), `tests/test_pending_override.py`.

## Not built

- a separate lag for the rotation and the position (one lag was asked for);
- a spring or a damping curve (the lag is a pure delay - the overlap the animator
  described);
- Override on the camera (its own tab has its own parent row);
- a live node rig (offered and declined: a lag in milliseconds needs the chest's
  past, which no Maya node reads).
