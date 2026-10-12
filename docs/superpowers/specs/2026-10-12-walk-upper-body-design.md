# Parametric walk: the chest and the arms — amplitudes, a pose's arms, and the body's inertia (2026-10-12)

The animator, after the legs: «Точно так же как у нас отрабатывает таз мы должны уметь параметрически изменять
анимацию груди и рук. Увеличивать и уменьшать амплитуду. Сейчас наша поза полностью перетирает анимацию рук … данные
позы должны обеспечивать корректное поведение и захлесты рук … важно что бы это все было универсально … изначальная
анимация нашей походки влияла на нашу позу НО делала это корректно в зависимости от захлеста с туловищем и не ломая
позу персонажа». A reference was loaded into their scene: a Creep skeleton under `Creep_Skeleton_Character`, keyed
0–121 «вот тут руки работают так как я бы хотел».

Asked, both the recommendation:
- **a two-handed grip holds**: the weapon and both hands sway and trail as one object, the arms reach it by IK;
- **the overlap is physical inertia**, not a time delay.

## The reference, measured (read only)

- **A fast gait**: a cycle of 20.2 frames, 1200 cm over 121 frames (~3 m/s), the pelvis at 73–88 cm, the torso
  leaning ~45°.
- **The arms are a stylised creature pose**:
  - the left held out to the side, 75° from hanging;
  - the right hanging back.
- **The arms swing 20–25° fore-aft**:
  - the forearm and hand wider than the upper arm (×1.3–1.5);
  - in phase within a frame at the first harmonic.
- **The shoulders turn ±7° in the world against the hips (±9.5° relative)**, and tilt ±8°.
- **`asd` (our walk) reads alike**: shoulders ±6.9° and tilt ±5.1°, the hips ±6.0°.

So what generalises is the motion's sizes and how the limbs carry it, not this creature's posture; the
reference's look comes from its pose.

## The chest: degrees, like the pelvis

- **Knobs Chest twist (deg, default 7) and Chest sway (deg, default 5)**:
  - the shoulder line's turn about up each way (per a normal step, × the step's gain as Twist's);
  - and its tilt about forward;
  - group Chest, with Spine and Head.
- **`Walk._chest`**:
  - the walk's own amplitudes and shapes: first harmonics of the shoulder line's yaw and tilt;
  - a walk whose chest hardly turns takes the pelvis's shapes, opposite;
  - shares (`CHEST_SHARES` 0.25 / 0.35 / 0.4) on the top three spine joints.
- **`chest_extra` adds the difference as a world turn**. The difference is measured under the current knobs and
  pose (`_chest_own`: the spine and shoulders alone over the cycle, then once more with the turn added). So a
  pose's bent spine still lands on the knob, within 0.5°.
- **The neck rides the chest; the head keeps its own world turn.**
- **`own_knobs()` gives the walk's own**; `chest_fit` reads a cycle back; the status line says «chest twists +-x
  deg, sways +-y».

## The arms: a pose's arms are a mean, the walk swings about it

- **A pose's Arms part was HELD**: its swing faded with the pose share. Now it is the mean posture the walk's swing
  (Arms) runs about.
- **Knob Elbow** (× the forearm's own swing, on top of Arms).
- **Only hands that hold one thing together are held** (`grip`):
  - `walkpose.prepare` sets it when the pose's hands stand within `GRIP_DIST` (30 cm, the walk's size);
  - it is part of the Arms part.

## The body's inertia (`Walk._arm_dynamics`)

**The frames are the arms' target.** Each limb (upper arm, forearm, hand) turns toward its own target — its
motion on the joint above as that joint actually moves — through a damped spring. It also feels the acceleration
of the point it hangs from:

```
alpha = -w0^2 . err - 2 zeta w0 . omega + 1.5 / L^2 . (lever x -a_pivot)
```

- `w0 = 2 zeta / drag`: a damped spring lags `2 zeta / w0` frames behind its target. Knob **Arm drag** (frames,
  default 1.5, `own_knobs` 0).
- `zeta = 1 - 0.75 bounce`. Knob **Arm bounce** (default 0.3).
- The pivot's acceleration is carried down the chain: `a + alpha x r + omega x (omega x r)`.
- So the arms trail the body's bob, sway and twist and whip through. Against the chest they move even with Arms 0.
- **Integration**: semi-implicit, at `max(4, 4 w0)` steps a frame. It runs cycle after cycle until a cycle starts
  where the last did (`ARM_SETTLED`), and the seam's remainder is spread over the cycle. The rotations are written
  in plain floats (`_exp3`, `_log3`, `_cross3`).
- **The bones' lengths are the walk's own** (`self.lt`): a pose turns bones, it does not lengthen them. The hand's
  lever is its farthest finger.
- **Everything hanging off a changed joint is carried along**: fingers, twist bones, the helpers that follow it
  such as the weapon bones (`_reattach`).
- **A grip** (`_grip_motion`):
  - the right hand carries the held thing; its world turn and place trail the target through the same spring,
    with the travel taken out;
  - the left hand keeps its hold on the right;
  - both arms reach by two-bone IK, the elbows bent the way the frames bend them.
- **Balance**: the carry is solved with the arms as they move, recomputed under each round's carry. The centre of
  mass still lands within 0.05 cm.

**Measured on `asd`:**
- At the default Drag 1.5 / bounce 0.3 the forearms swing 2.2 frames late, the wrists up to ~11 cm off where
  they'd be without it.
- Drag 3: 4.8 frames, ~20–24 cm.
- Bounce 0.7: the forearm swings 1.4–1.6× as far (the whip).
- The two-handed sword trails 3.6 cm at the default, 10 cm at Drag 5, both hands on it (0.0000).
- Bone lengths are exact and the loop closes (1e-15).
- An evaluate takes 0.6–0.8 s (0.3 s without drag).

## Proof

- **`tests/test_walkmodel.py`, 126 tests:**
  - ChestTests: twist/sway in degrees without and under a pose; the walk's own is its own; the chest turns alone,
    the pelvis and the head untouched;
  - ArmTests:
    - drag lags the hands 1.5–6 frames, bones whole, the loop closed;
    - bounce whips the forearm through;
    - the body moves still arms;
    - drag 0 is the frames;
    - a held thing trails as one;
    - balance holds with the arms moving.
- **Older tests updated:**
  - those about the arms' kinematics name Arm drag 0;
  - the grip fixture carries `grip`;
  - "a bent body turns about the walk's world axes" checks the spine with the chest's turn left alone;
  - "the chest keeps its turn" keeps the walk's own Chest knobs.
- **`verify_walk.py` standalone, on Manny's keys:**
  - Chest twist 10 / sway 7 measured;
  - Arm drag 3 / bounce 0.6: the forearms late, bones whole, the loop closed;
  - the two-handed sword under drag: both hands keep the grip and the sword in it, the sword trails, the arms whole;
  - gate 51 keeps the walk's own chest;
  - 70 of 70. Chest twist 10 / sway 7: the shoulders turn ±12.92 (asked 12.92) and tilt ±7.00. Arm drag 3 /
    bounce 0.6: the forearms 5.9 / 5.8 frames late (×1.28), the bones whole (1.3e-5), the seam 0. The sword
    under drag 3: the grip held to 4.4e-5, the sword in it to 0, the sword trailing up to 7.9 cm, the arms whole.
- **Picture:** `walkparam/walk_upper_body.png`: the goblin pose at the defaults and at Drag 3 / bounce 0.7, the
  sword at Drag 3; thin, the same without drag.

## Addendum: the goblin's hands and elbows shook

The animator, the same night: «В позе гоблина у них сильное дрожание в захлесте как у кистей так и у локтей».

- **Reproduced standalone** from the knobs in the scene's marker (the rebuild equal to the scene's keys,
  0.0000°): the hands turned 0.6 → 33 → 8° a frame in turn, against 4–9 for their target. Arm drag 0 took it
  away, and so did the pivot term alone (`ARM_INERTIA` 0).
- **Cause 1, the shoulder's acceleration**: it was the second difference of the frames, so a frame's wobble in
  the shoulder's path was a kick. Now `_smooth_accel` takes the path's first `ARM_HARMONICS` (6) harmonics a cycle
  and differentiates them analytically at every substep: the body's bob, sway and twist.
- **Cause 2, the hand's lever**: it was its metacarpals' base, 4.2 cm. The pendulum term goes as 1/L, so the hand
  was a stiff 4 cm pendulum. Now `_hand_lever` gives its farthest finger joint (13.4 cm on `asd`).
- **Measured on the goblin**, Arm drag 1.5 / bounce 0.3 (motion above harmonic 8 of the cycle, deg rms;
  [before, either fix alone, both, no drag]):

  | joint | before | smoothing only | lever only | both | no drag |
  |---|---|---|---|---|---|
  | hand_l | 5.33 | 1.56 | 1.83 | 0.55 | 0.49 |
  | hand_r | 3.20 | 2.43 | 1.25 | 0.82 | 0.54 |
  | lowerarm_l | 0.66 | 0.20 | 0.66 | 0.20 | 0.57 |
  | lowerarm_r | 0.50 | 0.33 | 0.50 | 0.33 | 0.94 |

  The frame-to-frame turn change of the hands went from 37 / 22° to 6.6 / 6.9 (the target's 4.2 / 3.9).
- **What is left is the source's own**: `asd`'s keyed forearms carry 0.4–0.9° above harmonic 8, the drag
  springs filter it out of the forearms, and the hand whips the rest on. Low-passing the targets as well was
  tried: a hard cut at the measuring harmonic makes the metric read zero by construction, and a looser one rings
  between the frames (worse). Not taken.
- **Tests**: `test_the_hand_swings_whole`; `test_frame_noise_in_the_shoulder_does_not_shake_the_arm` - the left
  arm jolted ±0.5 cm on alternate frames swings its hand exactly as smoothly as without the jolt (0.131°), while
  every harmonic (the old way) shook it 2.5× as much. Picture `walkparam/walk_arm_jitter.png`.

## Not built

- gravity on the arms (the target already holds them; muscles carry the pose);
- a held weapon swinging with the walk's own arm swing (it sways by inertia only);
- the clavicle under inertia;
- per-arm knobs;
- calibrating the defaults to a reference automatically.
