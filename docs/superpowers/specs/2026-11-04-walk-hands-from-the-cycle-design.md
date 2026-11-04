# Walk Builder: the arms' and the hands' share of the cycle

2026-11-04. The animator, with two skeletons walking in a Maya on port 7002:

> Нужно улучшить walk builder. Мне кажется что сейчас настройки дают разные результат с позхой для
> двуручного меча и для жагера ножа. нужен парамметр который будет контролировать процент анимации
> кистей с оригинального цикла. В сцене по порту 7002 2 скелета с анимацией привязаной к walk builder.
> В позе с ножиком не удается получить статические руки при нулевых значениях ручек в weapon с оружием
> в позе с мечем они почти статические.

Asked, they answered three times: the knob covers **the hand and its fingers** (not the fingers alone,
not the whole arm); then, once the measurement had corrected my first reading of `Arm swing`, **two
knobs in one unit** - `Arms, %` and `Hands, %` - rather than a fix of `Arm swing` (which turned out
not to be broken) or one knob over the whole arm.

Their Maya could not be driven - the port accepted bytes and ran nothing, CPU flat at 0.08 s over 6 s
with Maya responding, which is a modal dialog holding the idle queue (bridge note 6; both sends were
disarmed by deleting their runner files). So every number below is measured headless in mayapy
standalone on **their own cycle** (`own:7833074715b34c33`, 31 frames at 30 fps), their own two pose
cards (`LongSword_Idle_3P.pose`, `DG_Idle.pose`) and their own card state read off `userPrefs.mel`
(2026-11-03 20:48): Chest chip on, Rotation 0, Position 0, 2H on, every pose part in, share 1.

## What is wrong, measured

Two quantities say what the eye reads as "static hands": how far the hand turns **in the pelvis's own
frame** (a hand standing still in a walking body still shows the body's own turn - 6.84 deg on this
cycle, the floor), and each finger's **own local turn** (0 is still).

| | hand in the pelvis's frame (R / L) | the fingers' own turn |
|---|---|---|
| `LongSword_Idle_3P.pose`, their settings | **6.84 / 6.84 deg** | **0.0 deg** |
| `DG_Idle.pose`, their settings | 16.25 / 14.01 deg | 11.07 / 12.80 deg |
| the dagger + the engine's `arms` 0 | 13.16 / 11.15 deg | 11.07 / 12.80 deg |
| the dagger + `arms` 0 + the springs off | **6.84 / 6.84 deg** | 11.07 / 12.80 deg |
| the dagger + a forced grip | 13.16 / 11.15 deg | **0.0 deg** |

The cause is the **grip**: `pose.prepare` calls a pose a grip when its two hands hold one thing (within
`GRIP_DIST` 30 cm), and the frame walk then stills both arms and every finger with
`gain *= 1.0 - alpha` (`model.py` ~3928, over `kind in ("arm", "finger")`). A sword pose has one; a
dagger pose does not. Nothing else about the two cards differs: both name all 54 arm joints, all 38
fingers, both sides.

Which lever is worth what, measured on the dagger card at their own settings (the hand in the pelvis's
frame, R / L):

| | with their weapon, 2H and Chest | with no weapon and no 2H |
|---|---|---|
| as it is | 16.25 / 14.01 deg | 42.43 / 54.04 deg |
| `Arms` 0 % alone | 13.16 / 11.15 deg | **15.81 / 19.45 deg** |
| `Whip` 0 alone | **6.84 / 6.84 deg** | 36.78 / 49.31 deg |
| both | 6.84 / 6.84 deg | 15.73 / 15.73 deg |

So the two columns need different levers, and both are real:

- **with a weapon in the hand** the hand is IK-solved onto it and the Chest mode holds the weapon
  still, so what moves the hand is the **springs**: `Whip` 0 reaches the floor by itself. `Arms` is
  worth 3.1 / 2.9 deg there.
- **with a free hand** the hand's motion is the arm's own swing: `Arms` 0 % takes 26.6 / 34.6 deg off
  it, `Whip` 5.6 / 4.7.
- **the fingers**, either way, are reached by the grip alone and by nothing else at all (below).

`Whip` is a parameter already (Physics, default 0.3) and nothing needs building for it - but it is
**all three springs at once**, the trunk's and the head's with the arms'; there is no per-part drag
knob on the card, and this work does not add one.

### The fingers are multiplied by a hard 1.0

`gains = {"spine": k["spine"] * ex}` and
`gain = ks[side]["arms"] * ex if kind == "arm" else gains.get(kind, 1.0)`, so a finger's gain is 1.0
under every knob there is - no `arms`, no `elbow`, not even `exaggeration`. Only the grip's
`1 - alpha` and the global `Detail` (through `_sample`'s residual) touch them, and `Detail` is one
number for the spine, the legs, the head and the arms together. Measured: with the engine's `arms` at
0 the fingers do not move at all (11.1 / 12.8 either way); with a forced grip they go to 0.0.

### Arm swing is not broken - the card lost the amplitude

My first reading was that `Arm swing` fails to land its ask. It does not. `arm_swing` is defined as the
peak to peak of the arm's forward angle's **stride-harmonic part** (`Cycle.p2p` is
`ptp(regular(y))`, and `_swing_of` returns the same quantity), and `gait._solved_gain` bisects `g_arm`
to land it: measured on this cycle, `_swing_of` at `g_arm` 0 reads **0.003 deg**. There is no floor in
its own measure to continue below. What stays behind at `g_arm` 0 is the series' mean and its residual,
which that measure does not see by design (the residual is `Detail`'s).

The lever that removes mean, harmonics and residual together is the amplitude - `exp_rot(arms . ex .
sample)`, which is what the grip scales. **The parameter layer has no way to write it**: `engine_knobs`
never assigns `e["arms"]`, and the only mention of the name is `from_legacy`, which turns a
pre-2026-10-26 memo's engine `arms` into an `arm_swing` ratio. Their own `userPrefs.mel` still holds
`skeldarWalk_knob_arms 1` from the old build, where the card could set it.

The readback, for the record (`gait.of_result` of an asked `arm_swing`, their cycle):

| asked | no pose, no weapon | dagger pose, no weapon | dagger pose, their 2H + Chest |
|---|---|---|---|
| 0.0 | L 3.60 / R 6.89 | L 7.28 / R 15.40 | L 7.38 / R 15.87 |
| 20.0 | L 16.87 / R 24.44 | L 16.74 / R 33.76 | L 8.28 / R 16.04 |
| 48.4 (its own) | L 44.10 / R 51.66 | L 41.00 / R 60.63 | L 9.82 / R 16.78 |

Bare, the knob works; the 3.6 / 6.9 deg left at an ask of 0 is the body carrying a still arm, which no
arm knob can or should remove. Under their 2H and Chest it is **nearly dead** - 0 to 48 deg of ask
moves the measured swing from 15.9 to 16.8 - because both arms are re-solved by IK onto the weapon,
whose path the Chest mode fixes. That is the animator's general complaint about the card
(«эти ручки часто не сильно влияют») in one measurement, and it is why the amplitude, not the degrees,
is what reaches the floor under 2H.

## The design

Two parameters in one unit, each **100 % by default**, each sided: how much of the cycle's own
animation that part of the arm keeps. Both at 0 % is exactly what a pose's grip does.

### 1. The engine: a `hands` knob (`maya_walk/model.py`)

A new sided knob `("hands", 1.0, 0.0, 3.0)` in `KNOBS` **after `exaggeration`** - everything before it
is `LEGACY`, read from a pre-2026-10-26 memo - and `"hands"` added to `SIDED`. `DEFAULTS`, `RANGES` and
`SIDE_KNOBS` are all derived from those two, so nothing else is declared.

A set of the hand bones beside `self.forearms`:
`self.hand_bones = set(j for j, n in enumerate(self.names) if _stem(n) == "hand")`.

In the frame walk's `else` branch, right after the forearm's `elbow` factor:

```python
if j in self.hand_bones or kind == "finger":
    gain *= ks[self._side(j)]["hands"]
```

So the hand bone carries `arms . ex . hands` (the shape the forearm already has with `arms . elbow`)
and a finger carries `hands` where it carries a hard 1.0 today. `_side` answers "l" or "r" for every
joint, so the lookup is always safe.

The existing `arms` knob needs no engine change: it already multiplies the clavicle, the upper arm, the
forearm and the hand bone.

At 1.0 every path is what it is today **bit for bit**: the factor is an exact float 1.0, and
`exp_rot(1.0 * turn)` is `exp_rot(turn)` for finite floats.

0 % holds the part where its centre is: the pose's own at share 1, the cycle's own mean with no pose.

`Hand lag`, `Hand overlap`, `Arm overlap` and the weapon's own passes are untouched - they shift a
series in time, and at 0 % there is no series left to shift.

### 2. The two parameters (`maya_walk/gait.py`)

```python
Param("arms", ARMS, "Arms", "%", "added", sided=True, rule=_fixed(0.0, 100.0), default=100.0,
      tip="How much of the cycle's own arm swing the upper arm and the forearm keep; 0 % holds them "
          "in the pose. A pose whose two hands hold one thing holds them on its own"),
Param("hands", ARMS, "Hands", "%", "added", sided=True, rule=_fixed(0.0, 100.0), default=100.0,
      tip="How much of the cycle's own hand and finger animation the hands keep; 0 % holds them in "
          "the pose. Under 2H or a grip the hand itself rides the weapon, so this is its fingers"),
```

First in the **Arms** group, `Arms` then `Hands`. In `engine_knobs`' sided loop:

```python
e["arms" + sfx] = sv("arms") / 100.0
e["hands" + sfx] = sv("hands") / 100.0
```

Kind `"added"`, so each own value is its default and the Diagnosis has nothing to say about them;
sided, like every arm parameter. Neither name is in `ASPECT_KNOBS`, so `aspects_on` is untouched.

The panel needs no change: it builds a group's sliders from `gait.PARAMS` by `p.group`.

**`from_legacy` is left as it is.** A pre-2026-10-26 memo's engine `arms` still becomes an `arm_swing`
ratio rather than the new `arms` parameter: that translation has stood since October, every walker it
concerns was translated long ago, and changing it would move those walkers.

### 3. The line (`maya_walk/model.py`)

`describe` names each part held away from 100 %, per side, reading `info["knobs"]` (which is the
`asked` dict, so a sided key may be absent - read `k.get("arms_" + s, k.get("arms", 1.0))`):

> `| the arms keep 0 % of the cycle, the hands 0 %`

## What it costs, stated

- **Under 2H or a grip the hand rides the weapon.** `Hands` then stills the fingers and nothing else:
  the hand's world pose is the weapon's, and `Arms` is what moves it (to the floor) by moving the IK's
  target. Measured: with the engine's `arms` 0 the hand's own turn still reads 19.7 deg, because
  `_arm_to_hand` rebuilds it.
- **A gripped hand cannot be unstilled.** Both knobs multiply the grip's own stilling, so 100 % on a
  sword pose is still still. That is today's behaviour and nobody asked to change it.
- **`Arms` and `Arm swing` are different quantities**, not two dials on one thing: `Arm swing` sets the
  harmonic swing in degrees and leaves the clip's handwriting, `Arms %` scales the whole series
  including its mean. Both are kept, and their tooltips say which is which.
- **The springs stay `Whip`'s**, and `Whip` is all three of them. Under their own 2H and Chest the
  springs are most of what moves the hand (9.4 deg of its 16.25), so the dagger wants `Whip` 0 as well
  - and that switches the trunk's and the head's springs off with the arms'. A per-part drag knob is
  not built.

## What this gives them

On their own cycle and cards, the dagger pose with `Hands` 0 % and `Whip` 0 comes to the sword's floor
- 6.84 deg of hand in the pelvis's frame and 0.0 deg of finger - with the sword pose unchanged at every
default. `Arms` 0 % adds nothing measurable there (the hand is on the weapon); it is the lever for a
free hand, where it takes 26.6 / 34.6 deg off the hand's turn.

## Proof

- `tests/test_walk_hands.py`: each knob's own value changing nothing matrix for matrix; `hands` 0 %
  stilling the hand's own turn and every finger on one side with the other untouched; `arms` 0 %
  stilling the upper arm and the forearm; the grip's stilling multiplying; each parameter's unit,
  range, default, group and order; `engine_knobs`' division by 100 on both sides; the line.
- `docs/superpowers/plans/walkparam/verify_walk_hands.py`, mayapy standalone on their own cycle and
  both their cards: the defaults bit for bit; each knob 0 % per side; the dagger reaching the sword's
  floor with the three knobs; the fingers at 0.0; the loop still closed and the bones still their own
  lengths; and the control that the code before this cannot reach it.
- The existing walk verifies re-run, each compared against a clean worktree of the commit before this
  work (several fail there already and must fail identically).

## Not built

- A knob per finger, or the thumb apart from the fingers.
- `Detail` per body part: the arms' and the hands' residual is covered by the two knobs now, the
  spine's, the legs' and the head's are still one global number.
- Anything about `Arm swing`, the Chest mode, 2H or the weapon's own overlap: they are measured here
  only to say what they override.

## A measuring trap, for whoever reads the numbers again

These matrices are **row-vector** (Maya's own order): a joint's own local rotation is
`w[j] @ w[parent].T`, never `w[parent].T @ w[j]`. Written the other way round it is the local
**conjugated** by the parent's world, so a perfectly constant local on a moving parent reads as 8-20
deg of motion - which sent my first reading of this bug down a false trail (the grip "not reaching the
fingers") and nearly bought a fix for a defect that does not exist. Trap 225, met from the measuring
side.
