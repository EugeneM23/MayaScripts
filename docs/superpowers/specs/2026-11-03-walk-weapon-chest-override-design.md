# Walk Builder: the weapon's overlap from the chest, and a two-handed hold (2026-11-03)

The animator, looking for the weapon's overlap modes in Walk Builder and finding only one slider:

> «мы делали функционал для нескольких режимов захлеста для оружия … Но почему этот функционал в
> connection? он должен быть в walk builder во вкладке Weapon и работать без рига»

What they remembered is real and shipped - but it is Connections' Weapon tab, not Walk Builder's:
**2H Weapon** and **Override mode** (2026-11-02, `maya_scenesetup/weaponoverride.py`), asked in the
Walk Builder rig-pose session and handed to a session of its own, which put it where a tab called
`Weapon` already existed. Nothing of the mechanism needs a rig - its own docstring says «it works
beside a bare skeleton too» - only the CARD does: it resolves the chest through `choose_rig`.

Asked, three answers settled the shape:

- **a walk parameter**, not a scene tool reached from another card: the knobs live in the model, a
  Pick recomputes them with the whole walk, nothing is keyed on the weapon, and it works on any
  skeleton with no rig by construction;
- **the hands follow the weapon**: the weapon takes the chest's motion and the holding hand is
  re-solved onto it, so the grip holds exactly and the arm's swing becomes a consequence;
- **beside** today's `Weapon overlap, ms`, not instead of it: two different overlaps that add.

Connections keeps its own tool untouched - it writes keys on any clip, not only on a cycle Walk
Builder processes - and that is said in the card's tooltips rather than removed.

## The parameters

`gait.PARAMS`, group `WEAPON`, all sided like `weapon_overlap` (the `[Both | Left | Right]` row):

| parameter | unit | default | range |
|---|---|---|---|
| `weapon_hold` «2H» | toggle | 0 | 0 / 1 |
| `weapon_chest_rotation` «Chest rotation» | × | 1 | 0 .. 1 |
| `weapon_chest_position` «Chest position» | × | 1 | 0 .. 1 |
| `weapon_chest_lag` «Chest lag, ms» | ms | 0 | `-overlap_cap` .. `overlap_cap` |

Kind `added` with explicit defaults (Whip's shape), so a cycle's own value is the default and
`own_knobs()` gives the cycle back untouched. The lag reaches half the walk's own cycle either way,
the same `gait.overlap_cap` the three arm overlaps use: past half a cycle a lag of a periodic signal
comes back on itself. `engine_knobs` turns the ms into frames of the new cycle at the output rate
(`fps_out`), exactly as `weapon_overlap` is turned, and passes the two strengths and the toggle
through.

Engine knobs of the same names in `model.KNOBS`, `weapon_chest_lag` in frames (-120 .. 120), and the
three in `model.SIDED`. `weapon_hold` is a toggle: sided too, so one hand can be bound while the
other is free (a character holding two weapons).

## The mechanism

In the model a weapon is not a transform: it is two points - its grip and its tip - in the holding
hand's own frame (`scene.weapons_in_hands` → `evaluate(weapons=)`), and `_weapon_swing` already moves
the weapon by moving the HAND. So «the hands follow the weapon» costs nothing: every weapon motion is
a right multiplication on the hand matrices, and `_arm_to_hand` rebuilds the arm by IK to whatever
hand it is handed.

A new pass **`_weapon_chest`**, inside `_arm_overlap`, after the arm cascade has made the late hands
and **before `_weapon_swing`** (so the blade's aim reads the tip path as this pass has left it - the
two overlaps add, in that order):

- **the chest** is the top spine joint the chest knobs already use (`self.chest_share`'s highest
  `spine_NN`), never a hardcoded `spine_03`, with the arm chains' own root parent as the fallback. Its
  world matrices come from `kin`, so they already carry everything the body does this frame.
- **the motion**, with `C` the chest's world and `Clate = shifted_cycle(kin[chest], lag)` - a CYCLIC
  read, not Connections' clamp at a first frame, because the walk's loop must close and every gate
  checks its seam:

      T(f) = inv(C(f)) @ Clate(f)

  The weapon keeps its own pose relative to the chest and the chest's own pose from `lag` frames
  earlier is put back: at `lag` 0 that is `inv(C) @ C = I`.
- **the strengths** are taken at the chest's own pivot, as Connections takes them: `T` is read as a
  rotation `R` and the offset `c_late - c` of the chest's position; the rotation is slerped from the
  identity by `Chest rotation`, the offset scaled by `Chest position`, and the transform rebuilt about
  `c(f)` (`moved_about`, the sibling of `swung_about`).
- **applied** on the right to every hand that holds that weapon and to its riders (the other hand
  under a grip, or under 2H): `hands[s][f] = hands[s][f] @ T(f)`.
- **`1 / 1 / 0` is the identity, matrix for matrix**: the pass early-outs on `OVERLAP_QUIET` when
  every lag is quiet and both strengths are 1.

## 2H

`weapon_hold` on for a side that holds no weapon of its own: that hand is bound to the holder's hand
by the offset it has at the cycle's **first frame**,

    Off = other(0) @ inv(holder(0)),  other(f) = Off @ holder(f)

written before the two weapon passes, after which it is a rider of both - so the hold is kept to
machine precision through the chest override and the blade's aim alike, and both arms are rebuilt by
IK. No new number: the hold is whatever the cycle and the pose already have at frame 0.

A side whose own hand holds a weapon cannot be bound to the other's: the knob is ignored for it and
the Pick line says so.

With 2H on, that arm's own swing stops mattering - it rides the weapon. That is the point («намертво
привяжет руки к оружию») and the tooltip says it.

## What follows

- `moved_arms` (the Balance round's `armed()`) counts the new knobs, so the carry balances the arms as
  they move late - the rule every overlap already follows.
- The evaluation cache keys on the weapons already (`scene.weapons_key`); the knobs ride in the knob
  dict, so nothing new is needed there.
- The Pick line gains «the weapon trails the chest N cm» (the most a grip point moved) and names a 2H
  hold; with no weapon in the hands it says so, as `Weapon overlap` already does.
- The Gait Builder prototype (`docs/superpowers/plans/gaitbuilder/gaitmodel.py`) is a fork of the
  model held to it frame for frame by `tests/test_gait_model.ParityTests`: the pass is copied there
  word for word, with the knobs defaulting to off so its own knob table needs nothing.

## Not built

- a strength above 1 (an overshoot of the body's motion - the springs' job);
- the weapon lagging INSIDE the grip (the other answer to the hold question: the hands keep their own
  track and the weapon slides);
- a second grip point for 2H (the offset is the cycle's own at frame 0);
- moving the tool out of Connections: it still writes keys on any clip, which a walk parameter cannot.

## Proof

`docs/superpowers/plans/walkparam/verify_walk_weapon_chest.py`, mayapy standalone, on the animator's
own cycle under the two-handed sword pose and on a cycle with one weapon in one hand:

- the defaults and `own_knobs()` give the cycle back **matrix for matrix**;
- at full strength with a lag, the weapon's pose **relative to the chest** equals the chest's own pose
  `lag` frames earlier (the pass's promise), and the grip point really moves;
- `rotation 0` - the weapon does not take the chest's turn; `position 0` - not its travel; each
  measured against the body's own turn and travel as the control;
- the grip is kept (the weapon's points in the holding hand's frame unchanged), the bones keep their
  lengths, and the loop closes;
- 2H binds the free hand: its offset from the holder is the frame-0 offset on every frame;
- Balance sees the pass (the carry differs with it on);
- and the whole road through `scene.apply` onto a plain **Manny UE5 skeleton with no rig**: the keys
  read back off the joints show the same promise.


## Addendum, the same day: the strengths are absolute, not the lag's share

The animator, with the card in front of them at `2H` on, `Chest rotation` 0, `Chest position` 0 and
`Chest lag` 0:

> «При таких настройках оружия я ожидаю что оно просто будет статично висеть в воздухе а оно сейчас
> наследует движение от тела. Выходит наши ручки Chest rotation и position работают не корректно. Они
> должны контролировать насколько у нас передается анимация с туловища на руки»

They are right, and the fault is in the formula above, not in the knobs. `T(f) = inv(C(f)) · Clate(f)` is
the identity at `lag` 0 whatever the strengths - they scaled only the motion the LAG introduces, so with no
lag there was nothing for them to scale. What the knobs must mean is how much of the chest's own animation
reaches the weapon at all.

**The chest's own cycle is scaled first, then read late** (`Walk.steady_chest`):

- the linear travel is taken out, leaving the chest's periodic deviation;
- its turn is slerped from the cycle's MEAN heading by `rotation`, its place pulled toward the mean by
  `position`;
- the travel is put back at every strength. Without it the weapon is left behind within a cycle and the
  loop does not close - and the travel is the walk's locomotion, not the body's own animation;
- then `want = shifted_cycle(steady, lag)` and `T(f) = inv(C(f)) · want(f)`.

So `1 / 1 / 0` is still the identity matrix for matrix; `0 / 0` hangs the weapon on a chest that only
glides down the travel line - with the arms stilled (a two-handed card) the weapon hangs in the air, which
is what was asked for; a lag at full strength is the overlap as before; and the two compose - the lag
follows the chest the strengths leave.

`moved_about` is gone with the old formula: `T` is now `inv(C) · want`, a rigid transform built from the
chest's own poses, and nothing has to be decomposed about a pivot.

The gates for the strengths moved with the meaning: they are measured with NO lag, against the chest's own
turn and bob as the control, and a thirteenth gate says in the animator's own terms that at `0 / 0` the
weapon wanders 0.000 cm off its straight line while the body carries it 8.24 cm.


## Addendum 2: an arm out of the pose is out of the Weapon tab too

The animator, with the pose's `Arm L` chip off:

> «Фильтр который исключает влияние позы на часть тела на руку должен исключать и обработку руки вкладкой
> weapon»

The chip already means «this arm plays the cycle, the pose does not reach it» (2026-11-02). It now means the
Weapon tab does not reach it either:

- `pose.filtered` records the sides whose chips are on as **`arm_sides`**. A pose that never went through
  `filtered` carries no such key, and that means every side is in - so nothing else had to change.
- `_arm_overlap` reads it (only while a pose is actually on, `alpha > 0`): a side that is out is dropped from
  `held`, so no weapon of its own is processed by the chest override or by the blade's aim; it is never a
  rider of another hand's weapon; and 2H cannot bind it.
- `info["arms"]["overlap"]["out_of_pose"]` names the sides that hold a weapon and are out, and the Pick line
  says «the left arm is out of the pose: the Weapon knobs leave it alone» in place of «no weapon in the
  hands».

The grip needed nothing: `filtered` already ends a two-handed grip when one arm leaves the pose.
