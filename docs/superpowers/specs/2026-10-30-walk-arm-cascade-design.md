# Walk Builder: the arms' cascade - the elbow and the hand later than the arm (2026-10-30)

The animator, right after `Arm overlap` shipped and they had turned it at 48.9 ms in their own Maya:
«Сделай каскад» - the elbow and the hand later than the arm. They chose to pick the choice up the next day;
asked again today, with both roads and their measured costs, they took **A**.

This continues `docs/superpowers/specs/2026-10-29-walk-arm-overlap-design.md`, whose "Not built" listed
exactly this. Everything that spec settled holds: the pass is a TIME SHIFT, not a reshaping; it runs before
the springs, so Whip takes the late arm as its target; the shoulder is the body's and never moves; the bones
keep their lengths; a grip holds.

## The two roads, and why A

In this framing the arm is rebuilt by IK to a wanted hand (`_arm_to_hand`), so the goal fixes the hand's
PLACE and the elbow's bend ANGLE. What a cascade may lag is therefore what the IK leaves free.

- **A - lag only what the IK leaves free.** Two knobs: the elbow's bend PLANE read later (a late orbit of the
  elbow about the shoulder-wrist line) and the hand's own TURN read later (a late wrist break). It costs
  nothing: at zero it is today's behaviour, and both properties the 2026-10-29 gates stand on - the bones'
  lengths and "the hand is where it stood L frames earlier" - are kept.
- **B - the real per-joint chain lag.** The forearm and the hand take their world orientations each at its own
  time and the whole arm's shape unfolds late. It costs `Arm overlap`'s exactness: the hand lands along the
  direction to its late place but at the LATE arm's own reach, some 3 cm out at 4 frames (the IK wants
  94..109 % of the arm's length over the lag window).

A was the recommendation and is what is built. B is not built and is not half-built: nothing of it is in the
code.

## The two knobs

**`Elbow overlap`** and **`Hand overlap`**, **ms**, **sided**, in the **Arms** group immediately after
`Arm overlap`, so the three read as one family:

| knob | what is read later | by |
|---|---|---|
| `Arm overlap` (2026-10-29) | the hand's PLACE, and everything the arm takes from the body | L |
| `Elbow overlap` | the elbow's bend PLANE | L + e |
| `Hand overlap` | the hand's own TURN | L + h |

Both are `added` parameters whose own value is 0 (as `Arm overlap` is), so the Diagnosis has nothing to say
about them and `own_knobs()` gives the walk back untouched. Each slider reaches **half the walk's own cycle
either way**, the same `gait.overlap_cap` the arm's does and for the same reason - past half a cycle a lag of
a periodic signal comes back on itself. The cap is per knob, not on the sum: a total `L + e` past half a
cycle wraps, exactly as `Arm overlap` alone does at its own end, and that is stated rather than clamped.

The old `Elbow lag` and `Hand lag` (frames) are untouched. They shift a joint's OWN series on the sampling
clock - which a pose's grip takes to zero by design, the very thing `Arm overlap` was built for - so they are
a different tool, and the unit (fr against ms) and the word (lag against overlap) are what tell them apart on
the card.

Engine knobs `elbow_overlap` / `hand_overlap`, frames of the new cycle, `ENGINE_ONLY` and `SIDED`,
`sv(...) * fps / 1000.0` in `engine_knobs` with the output frame rate `Arm overlap` already reads
(`scene.output_fps`: ntsc 30, film 24).

## The one rule

Inside the same pass, `Walk._arm_overlap`, with one change in `_arm_to_hand`:

- **the hand's place at L, its own turn at L + h.** `shifted_cycle` is called twice and the two mixed: the
  place from the lag-L cycle, the rotation from the lag-(L + h) one. With `h` 0 this is one call and today's
  matrix.
- **the elbow's bend plane at L + e.** `_arm_to_hand` reads the bend hint it gives `two_bone` from the
  shoulder, elbow and wrist of the frames at L + e, not at the current frame. The hint is a DIRECTION read
  from differences of three joints at one time, so `shifted_cycle`'s travel term (the same for all three at
  that frame) cancels and the cycle's travel does not enter it.
- **nothing else moves.** The upper arm's and the forearm's own rotations are still the frames' own, corrected
  by the rotation taking the frames' arm (axis + plane normal) onto the rebuilt one - so the bend hint enters
  as a hint only, and the SOURCE description `_arm_to_hand` aligns from stays the frames' (the one trap in
  this change: `bend` is used both as the hint and as the source plane's normal, and the cascade needs them
  split).

`_grip_motion` calls the same `_arm_to_hand` and passes no hint lag, so the springs' grip is unchanged.

## The grip

Under a pose's grip `_arm_overlap` already ties both hands rigidly to the held thing's late transform, with
the two sides' mean lag («hands that hold one thing together HOLD it»). The cascade needs no second rule:

- **`Hand overlap` applies to the HELD THING**, both sides' mean as the arm's lag already is - the weapon's
  own turn lags its travel, and the right hand is the hold, so it reads the same rule as the no-grip case
  (place at L, turn at L + h). Both hands follow the hold rigidly, so **the hold is kept to machine
  precision** and the left hand swings round the late-turned weapon, which is what holding one thing means.
- **`Elbow overlap` is per arm and free under a grip**: it moves no hand at all, only where the elbow stands
  off the shoulder-wrist line. This is the animator's own case (`LongSword_Idle_3P` at share 1), and the one
  half of the cascade that reads there at all.

## Zero, and the cascade alone

The pass's early-out counts all three lags of both sides, so **0 / 0 / 0 changes nothing, matrix for matrix**,
and the Balance path's `moved_arms` counts them too (the carry balances a late arm, cascade and all).

`Arm overlap` 0 with a cascade alone is a real setting: the arm is rebuilt to its OWN hand - the place the
frames' own - with the elbow orbiting late and the hand turning late. The rebuild is not bit-exact there (it
takes each bone's mean length over the cycle, which is what keeps the lengths constant), so a lone cascade
moves the bones by the same ~6e-06 cm the arm's own gates already measure, and the hand's place is the frames'
to that tolerance.

## What it costs, stated

- A late bend plane is a late ORBIT of the elbow, not a late bend ANGLE: the angle is the IK's, fixed by the
  hand's place and the bones. The angle's own timing is `Elbow lag`'s and `Elbow swing`'s.
- Past half a cycle each lag comes back on itself (the slider's own cap says so).
- A lead (a negative value) is allowed and means the elbow or the hand runs AHEAD of the arm, as
  `Arm overlap`'s own lead does.

## The proof

`docs/superpowers/plans/walkparam/verify_walk_arm_overlap.py` - **0 of 101 gates failed**, mayapy standalone
on a COPY of the animator's own walks folder: the 2026-10-29 arm gates beside 57 new cascade ones, on their
own cycle under the sword's grip, under `DG_Idle` (no grip) and with no pose, at **4 frames**, with Balance
and In place off for the geometry (both move the body an expectation is computed against - the 2026-10-29
lesson). The arms hang 0.36 .. 0.99 of their length across the three cases, so the bend plane is a real one
in all of them (a straight arm's is degenerate: `two_bone`'s elbow sits on the line, and an orbit of it would
measure as noise - the gate prints the extension, and the unit tests bend the synthetic walker's elbows 70 deg
for the same reason).

- **the elbow's late plane IS the frames' plane at L + e**: **1.21e-06 deg**, all three cases;
- **the elbow really orbited**: **2.40 cm** under the grip, 5.46 under the dagger, 2.63 with no pose;
- **the hand did not move with it**: **2.8e-14 cm** under the grip, 3.6e-15 otherwise;
- **the held thing's turn is its turn at L + h** (**1.4e-15** under the grip, **0.00e+00** without it) while
  **its place is where the arm's own lag left it** (1.4e-14 / 0.00e+00 cm), and it really turned (0.145 under
  the grip, 0.588 .. 0.647 without);
- **the hold is kept while the weapon turns late**: **8.97e-14**, and the other hand swings round it
  (**1.17 cm**) - which is what holding one thing means;
- **the turn rides on top of the arm's own lag**, at L + h: 1.4e-15 / 0.00e+00, the place where L alone puts
  it (3.6e-15 cm);
- **the bones keep their lengths** 5.63e-06 cm, the **shoulder is bit-exact** (< 1e-09), the **cycle is still
  a loop**;
- **0 / 0 is matrix for matrix**, all three cases;
- **a lead orbits the other way**: 1.45 against 1.39 cm under the grip, 4.69 against 5.46, 2.74 against 2.42;
- **Whip takes the cascaded arm as its target**: the two together are 1.70 cm from the springs alone and 2.98
  from the cascade alone (grip), 4.91 / 2.08, 2.29 / 1.24;
- **the milliseconds**: 150 ms is **4.500** frames at 30 fps and **3.600** at 24 for both knobs, the card's
  own 150 ms reach the engine as 4.500 / 4.500, and each slider reaches **516.7 ms** either way - half the
  animator's own cycle;
- **Balance sees a cascade with no arm lag at all**: the carry differs by **0.0064 cm**.

Unit tests: `tests/test_walk_arm_overlap.py`, 50 (was 29) - `LateBendTests` (the plane at a lag, the travel
cancelling, every hint a unit vector), the hint/source split and "the frames' own hint changes nothing" in
`ArmToHandTests`, `CascadePassTests` (11 on the synthetic walker: the orbit, the turn, the cascade on top of
L, the cascade alone, one side, a lead, the loop, what the pass says, and Balance's `moved_arms` counting the
new knobs), and the parameters in `ParameterTests`. The whole walk suite is **935 tests, OK** (its one
expected failure is the pre-existing `restore_source` question).

The walk's neighbours (`verify_walk.py`, `verify_walk_gait.py`, `verify_walk_own.py`, `verify_walk_many.py`)
were run on this tree AND on a clean worktree of `50dfa14d`, the commit before this work: they fail
identically there, exactly as the 2026-10-29 pass recorded.

## Not built

- **Road B**, the real per-joint chain lag. Offered, measured, declined today.
- The clavicle lagging (the shoulder girdle is the body; `Arm lag`'s own clavicle share still moves its
  series).
- A cascade for the legs, the spine or the head.
- A playblast. The animator looks at the slider in their own Maya after Check update.
