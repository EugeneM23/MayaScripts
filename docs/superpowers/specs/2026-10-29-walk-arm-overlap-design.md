# Walk Builder: the arms' overlap as a time shift (2026-10-29)

The animator: «Давай поработаем над захлестами рук в walk builder. Сейчас мало пользы от наших ручек при
настройке рук персонажа в walk builder. 1 - Elbow deg, arms forward deg, shoulders deg давай удалим они
бесполезны. 2 - давай сделаем анимационных захлест рук. грубо говоря нам нужно сделать так что бы наши руки
отставали на указанное количество милисекунд. если бы я делал это в ручную в анимации я бы призвязал руки
айкеями а потом сдвинул юы их рут на то количество кадров которое мне нужно и получил бы захлест движения».

Then, after the measurement below: «Ладно давай не удалять ручки просто сделаем захлесты». So **nothing is
deleted** - Elbow, Arms forward, Shoulders, Arm lag, Elbow lag and Hand lag all stay as they are - and one
knob is added.

## What was measured first (and what it decided)

Headless, on a copy of the animator's own walks folder, with their walker's own settings read off their
Maya over port 7004: their captured cycle (`own:7833074715b34c33`, 31 source frames at 30 fps, one stride),
tempo pinned at 0.871 (27 frames out), In place, physics on, the pose card `LongSword_Idle_3P` at share 1.

**Today's `Arm lag` moves nothing in the case they work in.** It shifts a joint's OWN series in time, and a
two-handed grip at full share takes the arm's own swing to zero by design (`gain *= 1.0 - alpha` where the
pose has a grip - «hands that hold one thing together HOLD it»), so there is no series left to shift:

| pose | hand_r's own path over the cycle | Arm lag +2 fr | +4 fr |
|---|---|---|---|
| none | 64.38 cm | **16.37 cm** | 32.18 cm |
| LongSword_Idle_3P @ 1.0 (a grip) | 15.12 cm | **0.00 cm** | 0.00 cm |
| LongSword_Idle_3P @ 0.5 | 35.16 cm | 6.82 cm | 12.86 cm |
| DG_Idle @ 1.0 (no grip) | 40.77 cm | 9.89 cm | 17.80 cm |

Under the grip the hand still travels 15.12 cm over the cycle - **the body carries it** - and the body's
carry is never lagged: over 4 frames `spine_03` moves 6.86 cm and turns 3.99 deg, `clavicle_r` 7.29 cm and
9.03 deg, `upperarm_r` 8.09 cm and 8.86 deg. So a knob that reaches only the arm's own series cannot read as
overlap at all there.

**The manual trick does reach it.** A prototype on the same cycle and pose - the arm's whole motion taken
from frame `f - lag` in the body's own space and mounted on the current shoulder:

| lag | hand_r late by | the shoulder would be late by (the IK holds it) | the IK reach wants |
|---|---|---|---|
| 2 fr (67 ms) | 4.96 cm | 4.26 cm | 96 % .. 105 % of the arm's 37.5 cm |
| 4 fr (133 ms) | 9.18 cm | 8.09 cm | 94 % .. 109 % |
| 6 fr (200 ms) | 11.90 cm | 10.66 cm | 91 % .. 110 % |

The lag-0 path read `lag` frames earlier differs from today's knob's result by 4.96 cm at 2 frames and
9.18 at 4 - today's knob is not a time shift of the hand's path, and the new one is.

Two readings follow from this and are settled by it:

- **everything the arm inherits from the body lags with it** (the chest's turn, the shoulder's bob and
  sway), not only the arm's own swing: under a grip that is the only motion there is;
- **the arm needs IK**: the true late hand sits up to 10 % of the arm's length away from where a rigid arm
  on the current shoulder would put it (the shoulder's own displacement over the lag window, 8.09 cm at 4
  frames), and that displacement - the hand not bobbing with the body but bobbing late - is a good part of
  what reads as overlap.

## The knob

**`Arm overlap`, ms, sided**, in the Main group right after `Arm lag`. An added lag: 0 is the clip as it
stands, so it is an offset parameter and never a measured feature of the walk.

- range **-100 .. 300 ms** (negative: the hand leads the body, which is occasionally wanted on a hit), as
  `rule=_fixed(-100.0, 300.0)`: the walk has no own value to measure it from;
- `gait.own` and `gait.of_result` answer **0** for it, so the slider reads back exactly what was asked and
  the Diagnosis never has anything to say about it;
- ms -> frames of the new cycle with the **output** frame rate - the rate the keys land at.
  `gait.engine_knobs` takes `fps_out` (default `walk.fps`, which is what every verify and every caller
  outside Maya gets) and `scene.params_knobs` passes the scene's own rate (`cards.fps_of` of the time
  unit). A 100 ms overlap is 3.0 frames at 30 fps and 2.4 at 24, and a fractional lag is interpolated
  (below);
- `sided=True`, so `arm_overlap_l` / `arm_overlap_r` work through the machinery the other sided parameters
  already use, and the `[Both | Left | Right]` row drives it with no new code;
- the engine's knob is `arm_overlap` (frames of the new cycle, per side), default 0.

**One slider, not three.** In the IK framing the HAND is the thing that goes late and the elbow falls out
of the IK; a separate elbow knob would move only the bend plane. `Elbow lag` and `Hand lag` keep doing what
they do today (the measured phases of the elbow's bend and the hand against the arm's swing).

## The pass

A post-pass over the built cycle, run from `evaluate` immediately **before** `_arm_dynamics` (and from the
same place inside Balance's `armed()`, so the carry balances the late arms).

`Walk._arm_overlap(worlds, n, ctx, only=None)`:

1. nothing asked (every side's `arm_overlap` is 0) or no arm chain: return, `worlds` untouched;
2. `kin = worlds.copy()` - the frames as built, which is what the arm is rebuilt from;
3. the thing that goes late:
   - **a grip** (the pose has one, alpha > 0 and both chains are there): the held thing - the right hand's
     world turn and place, the linear travel taken out exactly as `_grip_motion` takes it out, the series
     closed over the cycle. Both sides take the two sides' mean lag, so the two hands stay on one object;
   - **no grip**: each side's own hand, its own lag, the travel taken out the same way;
4. the late series: frame `f - lag` modulo the cycle, the rotation slerped and the place lerped between the
   two neighbouring frames, the travel put back at `f` (so the cycle is a loop by construction and a
   travelling cycle does not leave its hands behind);
5. the arm rebuilt per side from the current shoulder to that late hand by two-bone IK, the bend plane the
   late arm's, the bone lengths kept;
6. `_reattach(worlds, kin, new, only)` carries everything below the hand (the fingers, a held weapon's
   helper) as the frames had it on its anchor - the call the springs already make.

**The IK rebuild is factored out of `_grip_motion`** into one unit both use
(`_arm_to_hand(kin, n, chains, hands)`: given each side's wanted hand matrix series, the arms rebuilt and
returned as `{joint: (n+1, 4, 4)}`). `_grip_motion` keeps its spring and hands its result to it; the
overlap hands its time shift to it. One implementation of the IK, one of the grip's rule.

**It composes with Whip by running first**: `_arm_dynamics` copies `worlds` into its own `kin` at its
start, so the springs take the already-late arm as their target - late, then trailing and overshooting.
Whip at 0 leaves the pure time shift.

## The limits, stated

- The bones keep their lengths, so an overlap that asks the hand past the arm's reach is clamped by the
  IK's own reach (`two_bone`'s `reach`). On the animator's cycle at 200 ms nothing clamps (91 .. 110 % of
  the arm); a fast run with a big swing at 300 ms can clamp, and then the hand simply does not reach its
  full lag. Nothing is said on the line about it - the picture shows it.
- A hand holding a weapon takes the weapon with it. That is the point, not a cost.
- The lag takes the linear travel out and leaves the rest in world, as `_grip_motion` does. A cycle whose
  root YAWS within the cycle would have the arm lag that yaw in world rather than in the body's frame; our
  cycles travel along a line (the model's travel is a vector), so there is nothing there to get wrong
  today.
- `Arm lag` (frames, the measured phase) stays and is unchanged. The two can be set together: they are
  different quantities - one moves the arm's own swing in the cycle, the other puts the whole arm late.
  The Pick line is not changed by this work.

## Proof

`docs/superpowers/plans/walkparam/verify_walk_arm_overlap.py`, mayapy standalone, on a COPY of the
animator's walks folder and their own walker's settings (their cycle, the sword pose at share 1, In place,
tempo pinned) and, as the no-grip case, the same cycle with `DG_Idle` and with no pose:

- **the hand's path is the lag-0 path read `lag` frames earlier** in the body's space, to the IK's reach
  clamp - the gate that says it is a time shift and not a reshaping;
- **the shoulder has not moved** (the arm's pivot is the body's);
- **the grip is held**: the left hand's transform in the right's is what it was at lag 0, every frame;
- **the bone lengths are kept**, every frame, both arms;
- **the cycle is still a loop**: frame n equals frame 0 moved by the travel;
- **a control at 0 ms**: every joint of the whole body unchanged to 0.0 against the build before this work;
- **the ms conversion**: the same ms asks for a different frame count at 24 and at 30 fps, measured on the
  hand's lag;
- **a lead** (-67 ms) puts the hand ahead by the same distance it falls behind at +67;
- **Whip on top**: the lag alone, the springs alone and both, each read off the hand - both together are
  later than either;
- **Balance sees it**: the carry differs between 0 and 200 ms (the late arms move the centre of mass).

And a playblast in a disposable GUI Maya (a scratch `MAYA_APP_DIR`, killed after) of the walker at 0 and at
150 ms, to look at.

## Not built

- A per-joint cascade of its own (the elbow and the hand lagging further than the arm): the IK gives the
  elbow, and `Elbow lag` / `Hand lag` already move those phases.
- The clavicle lagging. The shoulder girdle is the body; `Arm lag`'s own clavicle share (0.6) still moves
  the clavicle's series if it is wanted.
- Overlap for the legs, the spine or the head. `torso_lag` and `head_lag` stay as they are.
- A line about the IK clamping.
