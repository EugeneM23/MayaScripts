# Our CAT for Maya: a procedural walk / run cycle on any skeleton (standalone)

2026-10-23. The animator, after the CATMotion research (`2026-10-23-catmotion-research.md`):
«давай попробуем написать наш кат для маи (пока отдельным инструментом) и посмотрим что получится».
Asked, all three the recommendation:
- **any skeleton**: keys on the game bones, no rig;
- **a cycle on the spot and along a line** (Walk On Spot / Walk On Line, Direction, Gradient); no Path Node;
- **a window with knobs**, presets, a re-key when a slider is let go.

Outside the plugin, like the physical stop and the parametric walk before it:
`docs/superpowers/plans/catwalk/`. Nothing in `SkeldarAnim/` changes.

## What it is

CATMotion's idea on our skeletons. A cycle is **synthesised from parameters**, not read from a clip:
- one cycle = two steps, phase u ∈ [0, 1);
- each limb has its own phase offset (LimbPhases);
- each leg spends `duty` of the cycle on the ground (LiftPlantMod) and swings the rest;
- the body is driven by curves of the phase (Lift, Push, WeightShift, Twist, Roll, Pitch).

The result is an ordinary keyed cycle on the bones: frames 0..T, frame T = frame 0 + the travel,
the shape Walk Builder reads. So a generated walk can be saved as a walk and tuned there later.

## Files

| file | does | imports |
|---|---|---|
| `catmodel.py` | the model: `Skeleton` (rest worlds, roles by canonical name), `PRESETS`, `KNOBS`, `generate(skel, knobs, fps)` → frames `[{leaf: 4x4}]` + info | numpy only |
| `skeldar_cat.py` | Maya: the target skeleton (`maya_walk.scene.read_bones`), the place, the keys (`channel_values` + `write_curves`), the window, the drop handler | cmds + the plugin |
| `verify_cat.py` | mayapy standalone on the plugin's Manny UE5 and Creep skeletons | |
| `render_cat.py` | offscreen filmstrip of the model on Manny's template | Qt |

## The model

Character frame from the rest: `up` +Y; `left` = the thighs' flat difference; `fwd` = left × up.
Leg length L = thigh + calf. CATUnits is L: lengths in presets are shares of L, so a preset fits any body.

- **Timing**:
  - `step_time` (frames, a cycle is two);
  - `stride` (× L, one step);
  - speed = 2·stride / cycle.
- **Travel**:
  - `direction` (deg, + is the character's left) turns the travel, never the facing;
  - `gradient` (deg) lifts the travel and the ground along it;
  - `mode` spot subtracts the travel from everything.
- **Feet** (the CAT FootPlatform):
  - footprint k of a leg is laid at the body's place at mid-stance, the rest ankle's lateral
    offset × `stance`, turned out `toe_out`, on the ground plane;
  - in stance the platform stands on it;
  - in swing it goes to the next footprint with `step_shape` easing, `lift` (height, peak at
    `lift_peak`), `foot_push` (forward) and `swerve` (outward);
  - pitch: toes up `heel_strike` about the HEEL at the contact, flat, heel up `toe_off` about the
    BALL before lift-off. The ball stays on the ground, the toes stay flat while the heel is up;
  - on a gradient the platform is tilted to the slope.
- **Pelvis**:
  - rest height − `crouch`;
  - `bob` (twice a cycle, lowest at `bob_phase` of a step), `push`, `weight_shift` (toward the
    stance foot);
  - `twist` (the forward leg's hip forward), `roll` (the swing hip drops), `lean` + `pitch`;
  - lowered per frame where a planted leg cannot reach: a smooth periodic cover over the need, the
    CAT retargeting's "weight".
- **Legs**: two-bone IK with the rest lengths, the knee toward the facing; the thigh's and calf's
  roll carried from the rest by the bone-and-hint frames. A swing foot out of reach is drawn in.
- **Spine**: counter-twist (`counter`) and the roll cancelled over the spine joints, `spine_lean`
  added. **Head**: kept on its rest facing by `head_stabilize`, plus `nod`.
- **Arms**:
  - hang `arm_out` from vertical;
  - swing `swing` opposite the same-side leg, late by `arm_lag`;
  - `cross_swing` across the body;
  - elbow `elbow` + `elbow_swing` with the forward swing;
  - clavicle forward / back `clavicle`, the hand flops `hand_flop`.
- **Phases**: legs 0 / 0.5 + `phase_l` / `phase_r` (a limp); arms with the opposite leg.
- **Helpers** (`ik_*`) that stand on a body bone at rest keep that relation; the rest of the skeleton
  (fingers, twists, weapon / camera bones) follows by FK.
- **Presets**: Walk, Run, Jog, Sneak, Strafe L, Strafe R, Backward. Times are kept in seconds and
  turned into frames at the scene's rate.

## The press

- **Apply to selection**: any part of a skeleton. A rig's constrained game skeleton is refused.
- **The place**: where the root stands on the first apply, kept on the top joint as
  `skeldarCatWalk` (JSON {place, knobs}). A re-key does not drift.
- **The writing**:
  - rotate on every bone, translate on the root, the pelvis and the helpers;
  - keys on frames start..start+T, one undo chunk;
  - the playback range set to the cycle.
- **The window**: preset, mode, then the knob groups (Timing, Feet, Pelvis, Spine & Head, Arms,
  Phases). A released slider re-keys the target, and the status line names the cycle, the speed
  and the deepest drop.

## Proof

- **`tests/test_catmodel.py`**, on Manny's template:
  - lengths kept;
  - the cycle closes with the travel (spot: equal);
  - a planted foot's pivot still;
  - run has flight frames, walk double support;
  - the knee bends forward;
  - the signs (left hip forward at left contact, the left arm forward at the right contact, the
    swing hip low);
  - Direction moves sideways and keeps the facing;
  - Gradient climbs.
- **`verify_cat.py`**, mayapy standalone on Manny UE5 and Creep skeletons: the keys reproduce the
  model, lengths, the loop, the stance, one undo.

## Addendum: matched to a reference (the same day)

The animator, with a reference walk beside a CAT skeleton in the third scene tab: «проанализировал
референсную анимацию и сделал возможным настройку нашего плагина для достижения такой походки».

**The reference**, read over port 7003, read only: `asd`-like, a 31-frame closed cycle, 173 cm a
cycle, the stance 0.5. Its knee:
- 33° at the plant, 40° in the loading, 14° mid-stance, 40° at lift-off, 70° in the swing;
- held at 20-30° just before the strike.

Its posture: spine_01 back 12°, spine_03 and spine_05 forward 17° and 13°, shoulders down 8°,
forearms turned in 19°.

**`catmatch.py`** (numpy):
- `measure(skel, frames)`: the same numbers read off any closed cycle - ours or a reference;
- `compare`: per-group bone-turn error in each cycle's facing;
- `fit`: knobs read off the reference, then each knob corrected by its own measurement on what
  catmodel makes. The best by pose error is kept, the step shrinking when a round is worse.

**Knobs added because the reference needed them:**
- feet: step shape below 0 (a fast start), late lift, heel-up hold, toes up late in the swing,
  reach past the print, where in the stance the foot is under the hip, foot height;
- crouch below 0;
- arms forward, forearms in, wrist bend;
- Posture: each spine joint's and the neck's bend, shoulders up;
- **Knees** (CATMotion's KneeAngle + LegWeight): with `knee_drive` the pelvis height is set so the
  planted knee bends as `knee_plant` / `load` / `mid` / `lift` say, the planting leg having the
  priority;
- `swing_knee` draws a swinging foot in toward its hip so the knee keeps its bend, fading to the
  strike.

The reach drop is local now: a deficit is spread over its own neighbourhood, not lifted from the
whole cycle. A foot about to land must be reached too.

**Result**, mean degrees of the bones' turns against the reference:

| group | the CAT walk in the scene | matched |
|---|---|---|
| pelvis | 5.5 | 2.2 |
| spine | 10.6 | 2.6 |
| head | 4.9 | 3.0 |
| legs | 18.2 | 10.8 |
| feet | 21.4 | 12.9 |
| arms | 17.0 | 13.8 |
| hands | 24.0 | 14.5 |

What is left is mostly the reference's own left / right asymmetry (one forearm rolled 14° the other
way), which a symmetric CAT cannot make.

The window gained **Match reference**: select the reference skeleton, press it. The knobs are fitted
(the mode, spot or line, is kept) and the last skeleton keyed is keyed again.

## Addendum: the matched walk is the default; fingers; an in-place reference (the same day)

The animator: «Настроенную походку сделай походкой по умолчанию в плагине», then «У меня не выходит
получить на нашем плагине походку как референс», then «открыл маю с портом 7001 перенеси туда наши
походки и давай будем там разрабатывать».

**What had gone wrong in their Maya:**
- The window, opened again after a match, could fire its preset list and key the old Walk preset
  over the matched cycle. That cycle (on the spot, 32 frames) is what they saw.
- The window is now filled quietly (`_state()["quiet"]`), and a `(custom)` entry stands at the
  top of the preset list, selected after a match.
- A later Match was pressed with our own CAT skeleton selected. The fit then measured an on-the-spot
  cycle as a standing one (stride 0, ground time 0.2) and remembered that.
- Match now refuses the skeleton the tool keys («select the reference walk»).
- `catmatch.walked` takes a cycle walked on the spot off its treadmill: the median velocity of the
  feet while they are down, every frame moved against it. So an in-place reference reads as the walk
  it is (a test checks it against the same cycle travelling).

**Fingers** (CAT's digit controls), a new group:
- `knuckle_curl`, `finger_curl`, `tip_curl`: about each phalanx's own Z, inward on both hands;
- `curl_fan`: more toward the pinky;
- `finger_flop`: with the arm's swing;
- `thumb_01`, `thumb_02`.

They were the largest difference on screen: the reference's middle phalanges are curled 55-80°,
ours stood straight. Matched: knuckles 22°, fingers 56°, fan 0.16, flop 7°. What is left is the
reference's left fingers also rolled sideways, which the right ones are not.

**The Walk preset is the matched walk** (31 frames at 30 fps, 87 cm a step). The reference's place
(direction, cycle offset) is left out. Ground time is 0.52 with the legs in even phase, not the
fit's 0.4923 and −0.0161: those kept both feet down only through half a frame of rounding, and had
a frame in the air at 60 fps. The cost is 0.3° of pose. With no memory, the tool starts on it.
`preset()` rounds a step time to half frames, so a 31-frame cycle stays 31.

**Match keys in step with the reference**:
- travelling as it does, or on the spot when it was on the spot;
- from its first frame;
- `cycle_offset` (CAT's Start) puts our left foot down on the reference's frame.

**Maya on port 7001**:
- Its own Manny rig was left as it stood.
- The reference was rebuilt as a Manny UE5 skeleton keyed from the world matrices read in the 7003
  Maya, all 92 bones on frames 3-34. It matches to 0.00000 cm.
- Our CAT skeleton stands beside it at x = 300 and is matched to it.

Proof:
- `verify_cat.py` 53/53. The walk gates are by name now: a walk never has both feet in the air
  and has both down for a moment; a run has flight.
- 21 unit tests.

## Addendum: the pelvis bobs like the reference's (the same day)

The animator: «та походка которая у нас получилась имеет очень странный бобинг в области таза совсем
не похоже на референс».

**Measured** (the pelvis height over the cycle, from the left contact):

| | 2nd harmonic | 4th | 6th | jerk max (cm a frame²) |
|---|---|---|---|---|
| the reference | 3.58 cm | 0.20 | 0.02 | 0.89 |
| the Walk preset | 3.18 | 1.71 | 0.90 | 4.87 |

The reference is one sine a step: lowest just before a foot lands, highest at mid-stance. Ours fell
7 cm in 3 frames at every contact and stood flat late in the stance.

**Two causes:**
- **The model.** The knee drive sets the pelvis from one planted leg at a time, the planting leg first,
  and at a contact the new leg takes over within a frame. Its plant knee (46°) wants the hip 7 cm lower
  than the old leg did a frame earlier. Only a 0.8-frame blur smoothed it.
- **The fit.** It counted 1 cm of bob as 0.05° of pose and never saw the bob's shape or timing. So it
  bent the pelvis to make the legs score better.

**The fix:**
- The knee drive's height is cut to the cycle's low harmonics (`_low_pass`): kept whole to the 2nd,
  gone by the 5th. It is per cycle, so the same at any frame rate.
- The fit (`catmatch.fit`, which has no knee mode now) sets the pelvis by `crouch`, `bob` and
  `bob_phase` (CAT's Pelvis Lift); the knees follow by IK. The knee drive is off and its knobs are not
  fitted (`FIT_FIXED`, `FIT_SKIP`).
- The pelvis height is judged frame by frame: `pelvis_track` is the rms against the reference plus the
  mean's difference, in percent of the leg, × `TRACK_WEIGHT` 3.
- The bob knobs end as what the cycle shows. A planted leg reaches only 0.99 of its length, so the cover
  cut the cosine's top, and the loops pushed the knob on into the cut: 0.0657 asked to show 0.0403.

**Three fits, compared** (smoothed knee drive throughout):

| pelvis by | track error | jerk | 4th harmonic | pose sum |
|---|---|---|---|---|
| the knee knobs | 1.43 cm | 1.10 | 0.95 (a flat top) | 86.8 |
| knees + bob | 0.91 cm | 0.87 | 0.64 | 86.3 |
| bob, crouch, phase | 1.13 cm | 0.65 | 0.05 | 85.4 |

**The Walk preset is refitted.** Ground time 0.52 and the legs' even phase are held from the start.
- Pose sum 83.9, down from 86.8: pelvis 1.7, spine 2.5, head 2.9, legs 10.3, feet 12.2, arms 13.6,
  hands 14.3, fingers 26.5.
- Its bob: 2nd harmonic 3.85 cm, 4th 0.06, nothing above, the same at 24, 30 and 60 fps.
- The knee knobs hold the reference's measured knee angles. They act only when Knee drive is raised.

**What is left:**
- The whole curve stands about 1 cm lower than the reference's.
- At mid-stance the reference's foot is 2° heel-up, its hip sits 0.3 cm lower on its pelvis, and its
  leg is 0.993 straight, against our 0.99. That is a few millimetres each.
- The reference rises from its low faster than it falls; a cosine is symmetric.

**Maya on port 7001**: the CAT skeleton carried the old Walk (Reset), knee drive on. It is matched to the
reference again: harmonics 0.06, 3.60, 0.05, 0.04 (the reference's 0.28, 3.58, 0.41, 0.20), jerk 0.60.

Proof:
- 24 unit tests. Three are new, each failing on the old behaviour: the hard knee drive above the 4th
  harmonic (52% of the bob with the blur), the default walk at 24/30/60, and a matched cycle's track and
  honest knobs (1.51% under the knee-mode fit).
- `verify_cat.py` 55/55.

## Addendum: the chest's own knobs, and a sprint matched beside the walk (the same day)

The animator: «Некоторые ручки влияют на нашу анимацию почти незаметно, особенно это видно на груди» and
«я добавил в сцену скелет со спринтом ... добиться такой анимации нашими настройками ... при этом походка
тоже должна остаться».

**The chest.** A scan from the Walk preset swept each knob over its range and recorded how far the chest
(spine_05) moved against the travel line. The chest's knobs were shares of the pelvis's motion, and the
spine took the pelvis's motion back:
- Pitch ±10° moved the chest 0.4°.
- Roll ±20° moved it 1.3°.
- Shoulders level (`roll_cancel`), over its whole range, moved it 1.1°.
- Chest counter-twist (`counter`) moved it 8°.

On the sprint, the measurement came out as counter −2.96 and roll_cancel 2.56, both outside their ranges.

The chest now has its own motion in degrees, in the world, on the pelvis's timing: **Chest twist**,
**Chest roll** and **Chest bounce** (`chest_twist`, `chest_roll`, `chest_pitch`). The spine carries the
chest from the pelvis to that motion, so the pelvis's twist and roll no longer move the chest. Over their
ranges the three move the chest 42°, 24.5° and 20°. `catmodel.knobs` turns old saved `counter` /
`roll_cancel` into the same motion (`_legacy`), and every preset moves as before, to 1.4e-5. The matcher
reads the three straight off the chest.

**A take of several cycles.** The sprint (`|Sprint|root`, keys 12–73) holds four cycles over 61 frames.
Each cycle differs (mocap) and only the whole take closes, so cutting one cycle out fails; read as one
cycle, it measured a ground time of 0.07 and a stride of 8 legs. `catmatch.mean_cycle` averages the take
into one cycle:
- `cycles_in` counts the cycles from the strongest harmonic of the left ankle's height.
- Each phase is sampled in every cycle, places less the take's straight travel, rotations averaged and
  projected back onto a rotation, on round(period) frames.

A one-cycle take comes back as it is. Match fits the mean cycle, and Apply keys our cycle as many times as
the take holds (`apply(cycles=)`, kept in the marker).

**Fixed and added on the sprint's evidence:**
- **The shin flipped 180° about its own bone** whenever the knee folded past ~70°. Each leg bone took its
  roll from its own direction crossed with the knee hint, and as the heel kicks up behind, the shin points
  along the hint's opposite, so the cross product changed sign. Now one bend plane serves the whole leg:
  the hip-to-ankle line's normal toward the hint.
- **The swinging foot.** **Foot hangs off the shin** (`foot_follow`, 0..1): mid-swing the foot blends from
  its level platform to the rest foot carried by the shin (`follow_shape`). **Toes pointed off the shin**
  (`swing_point`, degrees) points it from there. The fit holds `foot_follow` at 0, ½ and 1 in turn (fed
  back together, the two run away) and keeps the best: 1 for the sprint.
- **The clavicle.** The reference holds its shoulders forward (−13/+15°) and rolls them 17° once a cycle;
  ours stood still. New knobs: **Shoulders forward** (`clavicle_forward`), **Shoulders roll**
  (`clavicle_roll`) and **Shoulders pump** (`clavicle_pump`, rolling with the arm swing). The existing
  `clavicle` swing is fitted too. The walk's clavicle error was the same: 16° on every frame.
- **The wrist** twists about the forearm: **Wrist twist** (`hand_twist`) and **Wrist twist swing**
  (`hand_twist_swing`).
- `lift` reaches 1.0 of the leg (the sprint's 0.68 was past the old 0.6).

**The Run preset is the fit on the mean cycle** (the animator: «Сделай только бег референсным пресетом»; the
hand-made Run and a separate Sprint row are gone): 15 frames at 30 fps, 6.9 m/s,
2.05 legs a step, ground time 0.23, foot lift 0.66 leg, lean 21°, flight 7 frames a cycle. The pose is off
the reference by 154 summed group degrees: pelvis 7, spine 6, head 11, legs 18, feet 21, arms 19, hands 34,
fingers 38. Before the fixes it was 217: legs 43, feet 53, arms 23, hands 36. What is left:
- the elbow opens about 2 frames later than the reference's, which no cosine can shape;
- the hand's flexion about its own Z;
- the thumb's turn about its own X.

**The walk stays.** The Walk preset, its knobs, and the walk keyed on `Manny_Skeleton1` beside the
reference are unchanged.

**Maya on port 7001**: a new Manny UE5 skeleton (`Manny_Skeleton3`, at (−150, −111)) was matched to the
sprint. It runs it four times (12–72) at the sprint's speed and stride; the averaged reference measures
duty 0.233 against our 0.267, and stride 2.045, lift 0.676/0.669, lean 21.5/21.5 and swing 47.1/46.8 on
both. The window was rebuilt with the new knobs.

Proof:
- 30 unit tests. Six are new:
  - each chest knob turns the chest by its degrees;
  - the pelvis no longer takes the chest with it;
  - old saved knobs give the same chest;
  - the Run flies, and its shins never turn more than 30° a frame about their bone (this one fails
    with the old roll rule);
  - a swinging foot hangs off its shin pointed as set;
  - a three-cycle take is averaged back to its cycle to 1e-6.
- `verify_cat.py` 55/55, the Run on Manny and on the Creep.
- The chest knobs are read back on the upright Jog to 2.5° of 15° (under the Run's 21° lean the read-back is
  an euler of a tilted chest: 13.7°).

## Not built

- Path Node;
- layers with weights;
- footprint editing and Pick Ground;
- curve editors;
- KneeAngle by phase;
- tails and digits;
- rigs as targets;
- the hub card.
