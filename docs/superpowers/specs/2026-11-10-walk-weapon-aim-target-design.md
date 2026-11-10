# Walk Builder: Aim target - the weapon's tip keeps less of the animation (2026-11-10)

## The ask

The animator, with an example on port 7005: «В сцене риг и цикл бега который был получен при помощи
нашего Walk builder ... Здесь я сделал aim mode для нашего оружия и сгладил анимацию аим таргета,
сделал я это для придания веса оружию. Давай мы повторим тот же эффект в нашем walk builder во
вкладке weapon. Сделай ручку которая будет имитировать этот эффект 1 - вся анимация 0 - аим таргет
полностью статичен».

## The example, measured (read only)

`Manny_Rig`, a run in place, frames 0..76, four strides of 19 frames, every control keyed on every
frame.

- The Long Sword is out of the hands (`|Manny_Rig_Character|LongSwordMesh`, Connections' World), both
  IK hands follow it through their proxies. Its **translate is keyed on every frame** (77 keys): the
  grip's own travel, untouched.
- Its rotate is the **Aim Mode** constraint: target `LongSwordMesh_aimTarget` 133.3 cm along the blade
  (1.15 x the 115.9 cm tip), up `LongSwordMesh_aimUp`.
- **The up keeps all 77 keys. The target keeps 5**: frames 0, 20, 40, 60, 76, auto tangents. The
  animator deleted the keys between.
- The FK arm controls still carry the take, so the target's track from before is known: the FK
  wrist's world turn times a constant (the same constant at all five kept keys to 0.000 deg), and the
  kept keys sit on that track to 0.0 cm.
- Before: the target swings **67 cm** across the body, 30 cm of amplitude at the stride's own
  frequency (the blade whipping side to side with every step). After: 43 x 11 x 12 cm, a slow drift
  with nothing left at the stride's frequency - the drift itself is what a key every 20 frames reads
  off a 19-frame stride. The blade stands up to 23 deg (9 on average) off where the animation had it,
  while the grip moves exactly as before.

So the effect is: **the grip plays the whole animation, and the blade points at a target that plays
less of it** - the heavy end stays put by its inertia and the hands move the handle under it.

## The knob

**`Aim target`**, the Weapon tab, after Overlap. Sided, 0..1, **1 by default**.

- **1**: the whole animation - nothing changes, matrix for matrix.
- **0**: the aim target is static. Static in the frame the cycle travels in (the linear travel taken
  out and put back, as every overlap of this tab reads a cycle), at the target's own mean place. In
  place that is a point standing still in front of the character.
- Between: `T'(f) = mean + k (T(f) - mean)` - the target's own motion scaled about its mean. The
  animator's own words define the two ends, and an amplitude is the one reading that is predictable
  between them (0.5 is half the swing). A low-pass was considered: on a cycle nearly all of the
  target's motion is at the stride's frequency, so a filter below it is the same static target, and
  above it nothing.

## The mechanism

One more step in the arms pass (`model._arm_overlap`), after Hold / Overlap and before the arms are
rebuilt by IK, so it sees the hand where the tab's other two knobs left it and Whip takes the result
as its target:

1. the lever, in the holding hand's own frame: the grip `g` and the aim point `a = g + (tip - g) x
   1.15` (Aim Mode's own distance);
2. per frame the grip `G(f) = g . H(f)` and the target `T(f) = a . H(f)`;
3. the target damped: `T'(f)` above (`model.damped_points`), `k_eff = 1 - share (1 - k)` with the
   additive pose's share;
4. the hand swung about the grip by the minimal turn taking `T - G` onto `T' - G`
   (`aim_swing`, `swung_about`): the grip does not move, the blade points at the damped target, the
   roll about the blade stays the animation's (the example's up target keeps every key);
5. the arm rebuilt to the hand (`_arm_to_hand`).

Hands holding one thing (a pose's two-handed grip) take the carrier's swing together, so the hold is
kept exactly; the carrier is the hand the scene's weapon is in, else the right. The knob then reads
the two sides' mean, as Overlap does.

**The lever.** A weapon the scene holds in that hand (`scene.weapons_in_hands`: its grip and its tip).
With **no weapon in the scene at all**, the right hand's weapon bone stands for one: the grip on
`weapon_r`, the blade 100 cm along its +Z (UE's socket, which every catalog weapon lies along at zero
grip). The tab works with no weapon in the scene since 2026-11-05, and the example's own road puts the
sword on the rig after the walk is built. A skeleton with no weapon bone has no lever: the knob does
nothing and the line says so.

**Where it acts**: the tab's rule - only where the additive pose holds that arm (Pose share above 0,
the arm's chip on). It does not need Hold.

Balance counts it among the arm moves it carries. The line: «the blade aims at a target keeping 30 %
of its motion (swung up to 12 deg)».

## What it costs

- The hand turns with the weapon, so the wrist takes what the blade no longer does; an arm at full
  stretch is clamped on its line by the IK, as with every knob of this tab.
- With In place the root's own per-frame shift comes out after the pass (trap 318), so a target
  static in the travelling cycle moves by the root's surge on the keys. Root sway is 0 by default.

## Not built

A smoothing (low-pass) of the target; the up target damped; the knob in Idle Builder; a weapon out in
the world.

## Proof

- `tests/test_walk_weapon_aim.py`: `damped_points`; the knob declared; 1 the identity; 0 the target
  static with the grip unmoved; a half; the hold of two hands; a side out of the pose; the gait
  parameter and its engine knob; the line.
- `docs/superpowers/plans/walkparam/verify_walk_weapon_aim.py`, mayapy standalone, on the animator's
  own cycle and two-handed card: the same promises on real data, the whole road through `scene.apply`
  onto a Manny skeleton with a Long Sword, and the example's own track (`weapon_aim_example.json.gz`)
  put through `damped_points`.
