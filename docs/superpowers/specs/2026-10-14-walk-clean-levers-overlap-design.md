# Walk Builder reads a raw clip: clean, In place, levers, Overlap - design

2026-10-14. The animator, with two Mannys in the scene - `Manny_Skeleton_Character` a walk they broke on purpose
(«анимация сломаной походки»), `Manny_Skeleton1_Character` the reference idle `M_Neutral_Stand_Idle_Loop`:

«Давай улучшим алгоритмы работы нашего motionbuilder ... мы должны научить наш билдер исправлением такой анимации
... 1 - Походка сейчас не зациклена, мы должны научиться зацикливать анимацию ... 2 - ... ставить галочку INPlace
... 3 - в анимации есть джитеринг и артифакты нам нужны какие-то фильтры ... 4 - в сцене расположена эталонная
анимация айдла для понимания корректных позиций костей. В анимации сломаны плечи и левая стопа. Мы должны
научиться определять такие вещи и исправлять их ... 5 - выравнивать анимацию по уровню пола. 6 - У костей спины
нету сейчас анимации ... рычаги которые будут вращать части нашего тела даже если анимации у нас нету. 7 -
инструменты которые позволят делать захлесты частей тела. 8 - смещать анимацию верхней части тела относительно
нижней на указанное количество кадров.»

"Motionbuilder" is the Walk Builder (`SkeldarAnim/maya_walk/`). Asked, and answered:
- the clip is fixed **when the walk is read, with live knobs** (a Clean tab), not by a separate button that rekeys
  the skeleton;
- the reference is **a saved pose, plus a built-in UE5 idle** shipped with the plugin;
- new levers: **pelvis tilt and chest pitch, head nod, shoulders (swing and bob), an arm swing from nothing**;
- overlap: **one Overlap tab**, **shoulder and pelvis drag**, **a spine wave** (and the upper body offset);
- then «Давай пуш + сборка и я проверю потом».

The loop method comes from the animator's research note (`Downloads/Перенос стиля движения для запекания.md`):
loop points by the Kovar-Gleicher metric (point clouds aligned about up), the seam closed by Holden's two-sided
cubic offsets (C1: value and slope), the root's velocity alone corrected.

## What the clip is (measured, read only)

`Walking (1).fbx` (Mixamo) transferred onto the Manny skeleton by the bridge, 32 frames 0..31, ntsc. Against
`asd.walk.gz` - the same Mixamo walk saved 2026-10-12, its fingers identical to the degree - the animator broke:
- **the loop**: the body closes (frame 31 = frame 0 moved by the travel), but every twist bone and IK helper keys
  only 0..22, holding the last value after (lowerarm_twist_01_l -41 -> -72 deg at 18, then held): Save walk refused
  «not a closed loop: 56.738 cm»;
- **the floor**: the pelvis 53.7 cm higher (143-151 cm against 89-97), the feet 55-64 cm over the floor;
- **the shoulders**: both clavicles turned down 15 deg more (elevation -26 / -25 deg against the idle, the original
  -11 / -12), and clavicle_l moved 2.4 cm off its joint (its bone 8.27 cm against 5.85);
- **the left foot**: turned 71.5 deg out against its shin (the right foot 11, every other walk on disk under 20);
- **spikes**: hand_l at frame 23 (91 deg out and back), lowerarm_r 17-19 (73 deg, three frames, one key deleted);
- **the spine**: spine_02..05 and neck_02 one key each (still).

## Part 1 - Clean: a raw clip made a walk (`maya_walk/clean.py`, numpy only)

Save walk stores the clip as it stands (no loop refusal: the loop is found when the walk is read). `clean.clean(clip,
statics, reference, knobs)` returns `(clip, report)`; `model.analyse` reads the result. The clean knobs are knobs
like any other (the marker keeps them, a released one re-reads and re-keys: an analysis costs 0.03 s). Steps, in
this order:

1. **Root carrying**: a root that stays (under 1 cm a cycle) while the pelvis travels (over 10 cm) takes the
   pelvis's ground line: the root moves with it, the pelvis's world stays.
2. **Loop**: a cycle is a clip whose last frame stands on its first moved by the root's delta (body joints, helpers
   and twists left out: they are rebuilt). Else:
   - a loop **missing its closing frame** (the last frame as far from the first as one frame's motion): the
     closing frame is added (the first moved by the root's delta, the root extrapolated a frame);
   - else the **best loop** is cut out: every pair (i, j), j - i >= 10, scored by the Kovar-Gleicher distance -
     the body joints' positions in the root's ground frame (its place on the floor and its heading), RMS over a
     window of +-2 frames; only pairs holding whole strides (each foot steps as often); the least distance, the
     longest of those within 1.2x of it. The report says the frames and the distance in cm.
3. **In place**: a cycle whose root and pelvis travel under 1 cm while a foot on the ground moves steadily
   backward: the travel is restored, every joint moved forward by the planted feet's median speed.
4. **Spikes** (Despike): per joint, its local rotation (log about its mean) and - root, pelvis, any bone with
   moving translation - its translation, periodic: an **out-and-back** run of 1..3 frames - the jump into it and
   the jump out of it both larger than max(6 deg or cm, 6 x the joint's median frame step) / Despike, opposite in
   direction, the frames before and after it nearer each other than half the smaller jump. Runs searched longest
   first. Replaced by the Catmull-Rom from the frames around. Toes (ball_*) are left out (a toe's flick at the
   push-off is out-and-back: every run of AGS_Sprint, RunFast, the drunk walks has one). Measured: on the broken
   clip exactly lowerarm_r 17-19 and hand_l 23; on nine saved walks nothing.
5. **Posture** (Fix posture, against the Reference carried onto the walk's skeleton):
   - **bone offsets**: a bone of a left/right pair (not root, pelvis, helpers) whose mean local translation stands
     more than max(1 cm, 10 % of its length) off its opposite's mirrored one: the side farther from the rest takes
     the opposite's mirrored translation (clavicle_l);
   - **anatomical limits**, each joint's MEAN over the cycle against the reference, read as the direction of its
     child in its parent's frame, in the reference's body axes (forward, side, up) - limits from nine clips on disk
     plus margin:
     | joint | measured | limit |
     |---|---|---|
     | clavicle | elevation (lateral end up +) | -22 .. +35 deg |
     |  | protraction (forward +) | +-30 |
     | foot (toe vector in the calf) | pitch (toe down +) | +-35 |
     |  | toe out (+) | +-35 |
   - a joint out of its limits: if its opposite is within them, it takes the opposite's **mirrored** mean (the
     walk's own posture: the left foot), else the **reference's** (the clavicles); its own motion about the mean is
     kept (`local(t) = exp(log(t)) . new mean`); x Fix posture. A clavicle's child (the upper arm) keeps its WORLD
     rotation - the arm hangs from the raised shoulder; a foot's child (the toes) keeps its local.
   - mirror: posemath's rule - deltas from the rest in the root's frame, reflected by `F = I - 2 l l^T` (`l` the rest
     upper arms' right-to-left direction).
6. **Seam** (Seam, frames; default 8, at most a quarter of the cycle): per joint the seam's residual in value `d`
   and slope `dv` (local rotation logs, local translations; the root's rotation and its place off the travel line:
   slope only) taken off with two cubic offsets, `offset(t) = a t^3 + b t^2 + c t + x`, `t = 0..1` over the seam's
   frames from each end, `b = -3x - 2c`, `a = 2x + c` - `x = +-d/2`, `c = dv/2 x frames`: zero value and zero slope
   where they end (Holden).
7. **Smooth** (frames, default 0): a periodic Gaussian on the same series.
8. **Derived bones**: helpers (ik_*, weapon_*, camera_*, interaction, center_of_mass) that do not follow their
   bone rigidly are put back on it at their rest relation (ik_foot_X - foot_X; ik_hand_gun, ik_hand_r, weapon_r -
   hand_r; ik_hand_l, weapon_l - hand_l; ik_foot_root, ik_hand_root, interaction, center_of_mass, camera_root -
   root; camera_bone - camera_root). A twist bone (`*_twist_NN_*`) more than 20 deg off the UE twist rule at any
   frame is rebuilt by it: its rest relation rolled about its parent's bone axis by a share of the limb's roll -
   upper arm and thigh counter `-(1 - t)` of their own roll against their parent, forearm and calf follow `t` of
   the hand's / foot's roll (t = the twist bone's place along its parent bone).
9. **Floor** (Floor 0..1 + Floor offset cm): each foot's mid-stance ankle and ball heights over the root against
   the reference's (else the rest's) standing heights; the median of the lower of the two differences moves every
   joint but the root down. Under 1.5 cm it is left alone (a walk on the floor stays exact).

Every step reports what it found; nothing found = nothing changed (identity, gated on every saved walk). The report
stands in the Clean tab (a few lines), a short form on the status line.

**The reference**: a dropdown in the Clean tab - «UE5 idle (built in)» (`assets/walk_reference_ue5.wpose.gz`: the
idle's mean pose over its 302 frames, read from the animator's scene), the saved poses, «(none)» (posture and floor
then use the skeleton's rest). Carried onto the walk's skeleton with posemath (`pose.carried`).

## Part 2 - In place

A knob `in_place` (0/1, a chip **In place** beside Apply): the travel line's progress taken off every joint of the
result - the root stays on its place (weaving only with Root sway), the body moves about it, the planted feet slide
back at the walk's speed (what an in-place clip is). The stride and speed on the status line stay the walk's.

## Part 3 - Levers on the gait's phase

Each ADDS degrees (default 0) on a shape of the stride's phase (`stride_phase`: 0 at the left heel strike, 2 pi a
stride), whatever the clip holds there; the shape's phase is the clip's own on that axis where it moves more than
0.5 deg there, else the table's.

| knob | where | axis | per stride | default peak |
|---|---|---|---|---|
| pelvis_tilt (Pelvis) | pelvis, the lumbar takes it back (COUNTER_SHARES) | side: + top forward | 2 | 20 % of a stride after a strike |
| chest_pitch (Chest) | the chest joints (CHEST_SHARES) | side: + forward | 2 | 5 % |
| head_nod (Chest) | head (world) | side: + down | 2 | 7.5 % |
| shoulder_swing (Arms) | clavicles | up: + forward | 1 | left at the right strike, right at the left |
| shoulder_bob (Arms) | clavicles | forward: + up | 2 | 15 % |
| arm_swing (Arms) | upper arms (world) | side: + forward | 1 | left at the right strike, right at the left |

Shoulder swing and bob and Arm swing are sided (Both / Left / Right). "Head holds its gaze" exists: Head 0.

## Part 4 - Overlap

A tab gathering Upper body offset, Spine wave, Pelvis drag, Torso drag / bounce, Head drag, Shoulder drag, Arm drag
/ bounce and Overlap (the arms' lag).
- **upper_offset** (frames, -10..10): spine_01 and everything above it (spine, neck, head, arms, fingers, the chest's
  added turn and every lever on them) sampled that many frames later than the legs and the pelvis; the lumbar's
  counter-turn of the pelvis stays with the pelvis.
- **spine_wave** (frames, 0..6): each spine and neck joint's own motion later by its share of the chain (the top
  by the whole), the chest's added turn with it.
- **shoulder_drag** (frames, 0..8): each clavicle's turn against the chest through the arms' spring (Arm bounce),
  feeling the chest's acceleration at the shoulder; the arm re-attached.
- **pelvis_drag** (frames, 0..8): the pelvis's world turn through the trunk's spring (Torso bounce) over the cycle,
  before the legs are solved: the legs reach from the late hips.

## Part 5 - The card

Groups in two rows: [Clean | Step | Legs | Pelvis] / [Chest | Arms | Overlap | Weight]. Clean: Reference, Despike,
Smooth, Fix posture, Floor, Floor offset, Seam and the report. In place: a chip by Apply.

## Testing

- `tests/test_walkclean.py` on the synthetic walker of `test_walkmodel`: identity at the defaults; each breakage
  made and found and undone (spikes of 1 and 3 frames, a foot turned 70 deg, both clavicles down 25 deg, a bone
  moved, the body 30 cm up, twists and helpers keyed short, 1.6 cycles, a loop missing its closing frame, in place,
  a root that stays).
- `tests/test_walkmodel.py`: each lever's amplitude on a still source, 0 = identity; In place; Upper body offset an
  exact time shift (Balance 0); Spine wave; Shoulder and Pelvis drag lag.
- `docs/superpowers/plans/walkparam/verify_walk_clean.py` (mayapy standalone): the animator's broken clip
  (`walks/Walking_broken.walk.gz`, read from the scene, git-ignored) cleaned against the UE5 idle - every breakage
  found, the result against the original (asd); every saved walk unchanged by the clean at the defaults; Apply onto
  a Manny skeleton with In place and the levers.

## Addendum: what the build and the final review changed

- **The floor** is measured as the feet's lowest point over the cycle: the lowest ball (else ankle) over the root,
  against the REST's lowest ball over its root (the reference only when there is no rest), left within
  FLOOR_DEAD 5 cm. The first build's median at mid-stance against the reference left floating walks 3.5 cm under
  the floor. Measured on every saved walk: grounded ones -3.7..+2.1 cm (left alone), the six floating ones
  +15.1..+16.8 (put on the floor), the broken clip +54.
- **The loop of a long take**: of the pairs within LOOP_TIE x the least distance + LOOP_SLACK (0.5 cm), the fewest
  strides, the longest of those - the longest alone cut a take of 20 cycles into all 20. The pair search is
  vectorised (20 cycles: under 3 s with the analysis and an evaluate). A cut cycle's root climb is taken off as a
  ramp (one floor at both ends).
- **A reference the walk cannot stand on** (a headless 1P walk; a pose missing legs) is not a refusal: the reference
  is carried without asking for a head; if it still cannot be, the clean judges against the rest and the report
  says so as a NOTE (not a change).
- **A skeleton walked before the clean** (a marker with no `reference`) is picked with Floor 0 and Fix posture 0, so a
  re-key keeps what was keyed.
- **The mirror replaces the whole motion** of a clavicle or a foot out of its limits (half a stride on), not only its
  mean; **the offset fix sets the rest**; **the seam runs before Despike**; **In place also takes the root's surge off**.
- The report's height follows its text (a fixed height clipped it); a clean knob released with no target reads the
  walk again into the report. A walk's readings are cached per file, at most six.
