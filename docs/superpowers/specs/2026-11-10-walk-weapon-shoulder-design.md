# Walk Builder: Shoulder - the clavicle follows the hand (2026-11-10)

The animator, a walker in a Maya on port 7005: «В анимации которую мы получили с помощью нашего walk builder
перерастягивается локоть при текущих настройках. Нужно сделать доводчик плеча которые будет подкручивать
плече что бы мы избавились от перерастяжения. Сделай пока ручку в weapon».

## What the scene shows (read only)

`|Manny_Skeleton_Character|root` walks its own cycle `own:c1d1b1c8e510aa98` (75 frames, four strides) under
`LongSword_Idle_3P` at share 1, a Long Sword in the right hand, the Weapon tab at Hold on, Inherit 0.67,
Overlap 43.1 ms, Aim target 0.3. Read off the keys:

- the **left** arm's shoulder-to-hand distance runs **0.74 .. 0.94 of the arm's length** four times a
  cycle, its elbow's bend 85 -> 39 deg (0 is straight); the right 0.60 .. 0.77;
- the model rebuilt headless from the walker's memo gives the same numbers to the digit (0.942 at frame 53);
- one knob at a time back at its default: Aim target 0.90, Overlap 0.89, Hold off 0.88, Inherit 1 0.95.
  So it is no one knob: every Weapon knob moves the hand against the chest, the shoulder stays where the
  body has it, and the elbow alone pays for every change of the arm's reach.

## The knob

**Shoulder** (the Weapon tab, last; `gait` param `weapon_shoulder`, sided, "added", 0..1, **default 0**;
engine knob `weapon_shoulder`): the share of the arm's reach changes the clavicle takes.

Per frame, with `d` the distance from the frames' shoulder to the hand everything above has placed, and
`ref` its mean over the cycle:

    d' = ref + (d - ref) (1 - share)

and the clavicle swings about its own pivot - the least turn, in the plane of its bone and the hand - until
the shoulder stands `d'` from the hand (the triangle pivot / shoulder / hand with two sides fixed). Then the
arm is rebuilt to the same hand by the tab's one IK (`_arm_to_hand`).

- **0 is the walk matrix for matrix**; **1** leaves the arm one reach and the elbow one bend.
- Both ways about the mean (the shoulder goes with the hand and comes back with it), so there is no corner
  where it engages and the clavicle's mean stays the cycle's.
- The clavicle turns no further than `SHOULDER_MAX_DEG` 35 off the frames' own, freely to 0.6 of that,
  then eased (`soft_reach`).
- The hand, the weapon and the body do not move. The tab's rule: only where the additive pose holds that
  arm, its share blending it in; it needs no Hold. Balance counts it among the arm moves.
- The line: «the shoulder takes 100 % of the arm's reach (the clavicle turns up to 23 deg, the arm
  stretched 94 -> 81 %)».

## Not built

A one-sided mode (only past a limit); elevation / protraction limits of their own; the knob outside the
Weapon tab (an arm with no additive pose).
