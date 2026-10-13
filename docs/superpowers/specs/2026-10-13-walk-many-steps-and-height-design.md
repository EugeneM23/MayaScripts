# Parametric walk: a cycle of several steps, and the pelvis's height over the feet (2026-10-13)

The animator, with a new walk saved as `dw` and the two-handed sword pose on it: «Тут я попробовал загрузить как
основу другую анимацию походки … 1 - в данном случае фут плейсмент не справился, так из-за того что в исходной
анимации очень сильное проскальзование ног, но возможно нам стоит улучшить наш алгоритм. 2 - в исходной анимации
весь персонаж приподнят над землей, а в нашей позе он как бы стоит ниже из-за этого сейчас он у нас идет как бы в
присяде. Давай добавим параметр который просто будет контролировать расстояние между тазом и ногами».

## What the scene and the walk are (read only)

- The scene: `|root` walked with `dw`, the two-handed sword pose, every part, tempo 90, Stance 0.33, Leg turn 0.45,
  Arm drag 4.07 / bounce 0.47.
- **`dw` is a 90-frame cycle holding TWO steps of each foot**, in an uneven rhythm. Its feet stand still (slower
  than a fifth of the travel a frame) here:

  | foot | first stance | second stance |
  |---|---|---|
  | left | 14-47 | 65-77 |
  | right | 81-14 | 50-62 (sliding 0.7-0.9 cm a frame at 57-61) |

  The stances are 26-34 frames against 13-16, separated by a frame or two of flight.
- **The model reads one stance per foot per cycle**, so:
  - Foot placement held one contact of each foot: the one where the foot stands lowest, the left at 61.6-81.6 and
    the right at 56.5-64.7;
  - its "swing" ran across the other stance, and its lock's swing curve moved that standing foot: the left heel
    1.0-1.7 cm a frame at 12-46, against the source's 0.3-0.5;
  - `foot_target`'s stance (by speed) was the OTHER stance (left 14-47), so the two disagreed;
  - the first harmonics (the hip drop's and the chest's shapes, the arms' smoothing) and the step's length (Twist's
    gain, the stride readout) assumed one stride a cycle.
- **The feet float**: the first stances stand 2-3 cm higher than the second ones (the right foot flat at 3.3 cm
  over its lowest for 13 frames). A contact test by height against the foot's lowest (1.5 cm) cuts those stances
  into pieces.
- **The root is 17 cm below the feet** (−17.04 under the lowest ball): «весь персонаж приподнят». A pose's pelvis
  height was read over the walk's travel line (the root), so the sword pose's 85.3 cm landed 68 cm over `dw`'s feet:
  the legs at 0.53-0.80 of their length (the source 0.87-0.99), the crouch.

## 1. A cycle of several steps

Every per-foot quantity becomes a list, one entry a step; with one step a foot every number is what it was.

- **Steps** (`_steps`, was `_contact`): every run where the slower of the ankle and the ball moves less than
  `CONTACT_SHARE` of the travel a frame. Two runs of one foot merge when the foot stays within `MERGE_HIGH` (4 cm) of
  its lowest across the gap between them (a stance sliding a little faster for a few frames). A run whose middle
  stands higher than that is no step. Both feet must step equally often (a walk alternates): else refused by name.
  `walk.steps[side]` is the list (each a `Foot`), `walk.feet[side]` its longest, and `walk.strides` the count.
- **The local floor**: each step's ankle and ball lows (within the step) are that step's floor, and a swing
  interpolates its two steps' floors. `ground`, `down`, the flights, the pressure and the roll's hold read a foot
  point's height over the floor where it is, not over its lowest of the cycle, so a stance standing 2-3 cm high is
  still down.
- **Contacts** (Foot placement, `_placement`): per step, the run of frames around it where the heel or the ball is
  within `CONTACT_TOL` of that step's floor, at least the step itself. Per contact:
  - its pivot weights;
  - its handoff: the other foot's strike nearest its lift-off, the double support read there;
  - its growth target `DOUBLE_SUPPORT` of a stride (the cycle / strides), at most `EXTEND_MAX` of the swing after it.
- **The foot's clock** (`foot_time`): a periodic monotone C1 cubic through every contact's strike and placed
  lift-off.
- **The lock** (`_locks`): one per contact; the swing cubic runs from a contact's lift-off to the next contact's
  strike, its slopes those two moments' pivot speeds. `planted`, `_just_off`, `_growth`, `_roll_need` and
  `_lock_at` find the contact (or the swing after it) the time is in.
- **`foot_target`**: the footprint of the step the time is in; a swing runs between its step's print and the next
  step's, each moved by its own shift. Stride, Stance, the pose's width and Swing out read per step.
- **The flights**: every stretch with the foot off the ground, not only the longest.
- **Per stride, not per cycle**:
  - the hip drop's cosine and the chest's shapes run on the stride's phase (linear between the left foot's
    strikes);
  - the step's length (Twist's gain, the stride readout) is the travel over 2 x strides;
  - the arms feel `ARM_HARMONICS` harmonics a stride;
  - the reach's drop is blurred over `LOWER_BLUR` of a stride;
  - Weight's clock has two lows a step.

## 2. The pelvis's height over the feet

- **A pose's pelvis height is read over its feet**, not over the travel line: over the lower of its two balls in
  the pose (carried onto the walk's skeleton, so the ball's own height cancels), put over the walk's floor (its
  lowest ball over the cycle). The sword pose's 85.3 cm stands over `dw`'s feet as it does over Manny's.
- **Knob Pelvis height** (`pelvis_height`, cm, default 0, −40..40, group Pelvis): raises or lowers the pelvis
  over the feet, the legs re-solved by IK. The reach still holds: a pelvis raised past the legs' straightest comes
  back down to it (the reach's drop), so the knob cannot lift the feet off the ground.

## Proof

- tests on a synthetic walker with two uneven steps of each foot a cycle (a long and a short stance):
  - its steps found, two each;
  - Foot placement holding every stance (no planted foot sliding);
  - one foot always down;
  - the defaults the source;
  - Twist's gain from the step;
  - the hip drop once a stride.
- tests that a one-step walk gives exactly what it did;
- a pose's height over its feet;
- Pelvis height moving the pelvis by its centimetres and stopping at the reach;
- `verify_walk.py` standalone on `asd` unchanged;
- the new gates on `dw` (from its saved file): both stances of each foot held; the sword pose's pelvis over the
  feet as in the pose.
