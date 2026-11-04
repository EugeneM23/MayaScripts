# Walk Builder: the hands' share of the cycle, and Arm swing below its floor

2026-11-04. The animator, with two skeletons walking in a Maya on port 7002:

> Нужно улучшить walk builder. Мне кажется что сейчас настройки дают разные результат с позхой для
> двуручного меча и для жагера ножа. нужен парамметр который будет контролировать процент анимации
> кистей с оригинального цикла. В сцене по порту 7002 2 скелета с анимацией привязаной к walk builder.
> В позе с ножиком не удается получить статические руки при нулевых значениях ручек в weapon с оружием
> в позе с мечем они почти статические.

Asked, they answered twice: the knob covers **the hand and its fingers** (not the fingers alone, not
the whole arm), and `Arm swing` is to be **fixed** so 0 deg really means a still arm (rather than
widening the new knob to the whole arm, which would overlap it).

Their Maya could not be driven - the port accepted bytes and ran nothing, CPU flat at 0.08 s over 6 s
with Maya responding, which is a modal dialog holding the idle queue (bridge note 6; both sends were
disarmed by deleting their runner files). So every number below is measured headless in mayapy
standalone on **their own cycle** (`own:7833074715b34c33`, 31 frames at 30 fps), their own two pose
cards (`LongSword_Idle_3P.pose`, `DG_Idle.pose`) and their own card state read off
`userPrefs.mel` (2026-11-03 20:48): Chest chip on, Rotation 0, Position 0, 2H on, every pose part in,
share 1.

## What is wrong, measured

The two poses on one cycle with one set of knobs:

| card | the hand's turn against the pelvis | the fingers' own turn |
|---|---|---|
| `LongSword_Idle_3P.pose` | **6.84 deg** | **0.0 deg** |
| `DG_Idle.pose` | **13.15 deg** | **20.7 deg** |

6.84 deg is the floor - the body's own turn, which a hand standing still in the body still shows. The
sword's hands are at it; the dagger's are not.

The cause is the **grip**: `pose.prepare` calls a pose a grip when its two hands hold one thing (within
`GRIP_DIST` 30 cm), and the frame walk then stills both arms and every finger
(`gain *= 1.0 - alpha`, `model.py` ~3928, over `kind in ("arm", "finger")`). A sword pose has one; a
dagger pose does not. Nothing else about the two cards differs: both name all 54 arm joints, all 38
fingers, both sides.

The dagger's 13.15 deg breaks down as:

| what | how much | reachable from the card |
|---|---|---|
| the body's own turn (the floor) | 6.84 deg | - |
| the arm's swing amplitude (the engine's `arms`) | ~4.1 deg | **no** |
| the arms' inertia (`Arm drag` 1.5) | ~2.2 deg | yes |
| the fingers, their own turn | 20.7 deg | **no** |

### Why no knob reaches the hands

- **The fingers are multiplied by a hard 1.0.** `gains = {"spine": ...}` and
  `gain = ks[side]["arms"] * ex if kind == "arm" else gains.get(kind, 1.0)`, so a finger's gain is 1.0
  under every knob there is - no `arms`, no `elbow`, not even `exaggeration`. Only the grip's
  `1 - alpha` and the global `Detail` (through `_sample`'s residual) touch them at all.
- **The hand bone is under `arms`** (`ARM_STEMS` holds "hand"), so `Arm swing` reaches it - but
  `Arm swing` does not land its ask (below).
- **`Detail` is the whole body**, one number for the spine, the legs, the head and the arms together,
  so it is no answer for the hands.

### Why Arm swing does not land its ask

`gait._solved_gain` bisects **`g_arm`** - the regular gain inside `_sample`, which mixes
`mean + gain . (regular - mean) + detail . residual`. The gain scales only the regular part, so the
clip's own residual handwriting survives at `g_arm` 0, and that residual is the floor the knob cannot
go below. Measured on their cycle, the readback (`gait.of_result`) of an asked `arm_swing`:

| asked | no pose, no weapon | dagger pose, no weapon | dagger pose, their 2H + Chest |
|---|---|---|---|
| 0.0 | L 3.60 / R 6.89 | L 7.28 / R 15.40 | L 7.38 / R 15.87 |
| 20.0 | L 16.87 / R 24.44 | L 16.74 / R 33.76 | L 8.28 / R 16.04 |
| 48.4 (its own) | L 44.10 / R 51.66 | L 41.00 / R 60.63 | L 9.82 / R 16.78 |

Two separate facts in that table. Bare, the knob works and has a floor of 3.6 / 6.9 deg - the
residual's own peak to peak. Under their 2H and Chest it is **nearly dead** (0 to 48 deg of ask moves
the measured swing 15.9 to 16.8): both arms are re-solved by IK onto the weapon, whose path the Chest
mode fixes, so the arm cannot swing whatever the knob says. That is the animator's general complaint
about the card («эти ручки часто не сильно влияют») in one measurement.

And the lever that does reach it even under 2H is the amplitude: with the engine's `arms` set to 0
and `Arm drag` 0, the dagger's hand reads **6.84 deg** - the sword's floor exactly. `arms` is never
written by the parameter layer, so the card cannot ask for it.

## The design

### 1. The engine: a `hands` knob (`maya_walk/model.py`)

A new sided knob `("hands", 1.0, 0.0, 3.0)` in `KNOBS` **after `exaggeration`** (everything before it
is `LEGACY`, read from a pre-2026-10-26 memo), and `"hands"` added to `SIDED`.

In the frame walk's `else` branch:

- the hand bone (`kind == "arm"` whose stem is `hand`): `gain = ks[side]["arms"] * ex * ks[side]["hands"]`;
- a finger (`kind == "finger"`): `gain = ks[side]["hands"]` where it is 1.0 today;
- the grip's `gain *= 1.0 - alpha` keeps multiplying on top, so a sword pose's hands stay still at
  100 % and the knob scales what the grip leaves. A gripped hand cannot be given its cycle animation
  back - that is today's behaviour and nobody asked to change it.

At 1.0 every path is what it is today **bit for bit**: the factor is an exact float 1.0, so
`_sample`'s fast path (`np.all(gain == 1.0)`) still fires and the Catmull-Rom series is returned
untouched.

0 % holds the hand and its fingers where their centre is: the pose's own hand pose at share 1, the
cycle's own mean with no pose - the same meaning `Arm swing` 0 has for the arm.

`Hand lag`, `Hand overlap` and the weapon's own passes are untouched: they shift a series in time and
at 0 % there is no series left to shift.

### 2. The engine knob behind Arm swing (`maya_walk/gait.py`)

`_swing_of(walk, kind, side, gain, detail)` gains an amplitude factor that scales the whole sample the
way the frame walk's `arms` does - `exp_rot(amp . (mean + gain . (regular - mean) + detail . residual))`,
the mean included, so `amp` 0 stands the arm at its centre exactly as the grip's `1 - alpha` does.
`_solved_gain` then continues below the branch's floor with it: where the asked swing is under what
`g_arm` 0 can give, `g_arm` stays at its floor and `arms<side>` is bisected on the same measure to
land the rest (clamped to 0..1 - the knob only ever takes swing away below the floor, it never adds).
`engine_knobs` writes `e["arms" + sfx]` only then.

On a walk's own value the guard `abs(guess - 1.0) < 1e-12 and detail == 1.0` returns 1.0 before any
of this, so `g_arm` 1 and `arms` 1: **nothing changes for a walker already processed** unless its
`Arm swing` is set away from the cycle's own, where today's answer is simply wrong.

### 3. The parameter and the card (`maya_walk/gait.py`, `panel.py`)

```python
Param("hands", ARMS, "Hands", "%", "added", sided=True, rule=_fixed(0.0, 100.0), default=100.0,
      tip="How much of the cycle's own hand and finger animation the hands keep; 0 % holds them in "
          "the pose. A pose whose two hands hold one thing stills them on its own")
```

First in the **Arms** group - it is the strongest knob there. `engine_knobs` writes
`e["hands" + sfx] = sv("hands") / 100.0`. Kind `"added"`, so its own value is the default and the
Diagnosis has nothing to say about it; sided, like every arm parameter.

The Pick line names it where it is set away from 100 %, per side, the way the arm knobs' notes read.

## What it costs, stated

- **Under 2H or a grip the arm is the weapon's.** `Arm swing` under them means "how much of the
  cycle's swing reaches the arm", not a landed degree figure: the measured swing still reads ~15.9 deg
  at an ask of 0 on their right arm, because what is measured is the IK's arm. What the fix buys is
  that the amplitude now reaches 0, and with it the floor.
- **A gripped hand cannot be unstilled.** `Hands` multiplies the grip's own stilling; 100 % on a sword
  pose is still still.
- **The hand's world pose under 2H is the weapon's.** `Hands` 0 % stills the hand's own turn and its
  fingers; what the hand then does in the world is the weapon's path. The ~4 deg of arm swing is
  `Arm swing`'s to take away and the ~2.2 deg of whip is `Arm drag`'s.

## What this gives them

On their own cycle and cards, the dagger pose with `Hands` 0 %, `Arm swing` 0 and `Arm drag` 0 comes
to the sword's floor - 6.84 deg of hand against the pelvis and 0.0 deg of finger - with the sword
pose unchanged at every default.

## Proof

- `tests/test_walk_hands.py`: the knob's own value changing nothing matrix for matrix; 0 % stilling
  the hand's own turn and every finger on each side alone; the grip's stilling multiplying; the
  parameter's unit, range, default and group; `engine_knobs`' division by 100; `_solved_gain` landing
  an ask below the floor and leaving `arms` at 1 above it.
- `docs/superpowers/plans/walkparam/verify_walk_hands.py`, mayapy standalone on their own cycle and
  both cards: the defaults bit for bit; `Hands` 0 % per side (the other side untouched); the dagger
  reaching the sword's floor with the three knobs; the readback of an `Arm swing` ask below the floor;
  the loop still closed and the bones still their own lengths. Every geometric gate carries the
  pre-fix code as its control, as the walk verifies do.
- The existing walk verifies re-run, each compared against a clean worktree of the commit before this
  work (several of them fail there already and must fail identically).

## Not built

- A knob per finger, or the thumb apart from the fingers.
- `Detail` per body part (the hands' residual is covered by `Hands`; the spine's, the legs' and the
  head's are still one global number).
- Making `Arm swing` land its ask under 2H or a grip - the arm there is the IK's, and a knob that
  claims degrees it cannot hold would be worse than one that says so.
- Anything about the Chest mode, 2H or the weapon's own overlap: they are measured here only to say
  what they override.
