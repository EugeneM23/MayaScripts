# Pose on clip: our poses onto a locomotion clip (a stop first) - design

2026-10-14. The animator, with `M_Neutral_Sprint_Stop_F_Lfoot` (Unreal's Game Animation Sample) on a Manny
UE5 skeleton in the open Maya: «Давай попробуем сделать инструмент который будет насаживать наши позы на
локомоушен циклы такие как вот стоп. Только давай пока будем это делать отдельным скриптом и не трогать наш
плагин в целом (можешь пока скопировать то что нужно из плагина), но не рисуй интерфейс и не встраивай этот
инструмент в то что уже существует.»

Asked, all three the recommendation:
- the result goes onto **a copy of the character beside** the original, which stays untouched; a second
  run replaces the copy;
- **the pose plus the clip's motion**: the clip's own changes (the sprint's lean, the brake's crouch) ride on
  top of the pose, the pelvis height in proportion;
- **the stop ends in the pose's stance**: each foot's last contact lands where the pose puts that foot; the
  earlier steps stay on the clip's prints, at the pose's width.

The question before it (the same day): Walk Builder's pose machinery works because it puts the pose where
the walk's mean was, keeps the walk's motion about it and solves the constraints again (feet on their
contacts, the pelvis over reachable feet, the centre of mass over the feet, a grip). This is that machinery
for a clip that is not a cycle.

## The clip, measured (read only over the port, then the same FBX in mayapy)

- 91 joints (Manny UE5 without `camera_*`), 143 frames at 30 fps, root motion along +Z, the root never turns.
- Frames 0-16 a sprint (~23 cm a frame), 16-28 the brake (pelvis 84 -> 57 cm), 28-60 standing up into a
  split stance (left foot 15 cm ahead, right 21 cm behind, 41 cm apart), 60-142 idle (pelvis 90.6 cm).
- Contacts (foot still: ankle or ball under ~2 cm a frame, near the floor): left 7-9, 24-40, 48-142 (a
  shuffle 41-47); right 0-2, 15-16, 33-142. **The right foot skids 17-32** (ankle 12-19 cm up, the ball
  3-7 cm, 5-15 cm a frame): the clip's own slide, kept as it is.
- The body is still (every joint under 1.5 cm a frame) from frame ~73.

## Where it lives

`docs/superpowers/plans/poseclip/`, nothing in `SkeldarAnim/` changes:
- `poseclip.py` - the model: numpy + the copied `posemath`; no `maya.cmds`;
- `poseclip_maya.py` - the scene: read the clip and the skeleton, load a pose, make the copy, key it;
- `posemath.py`, `skeletonmap.py` - copied whole from the plugin (`maya_poselib/posemath.py`,
  `maya_skeletonmap.py`) with one import line changed, and `manny_skeleton_template.json` from its assets;
- `verify_poseclip.py` - mayapy standalone on the stop's FBX.

No interface. From the Script Editor, a part of the character carrying the clip selected:

```python
import sys; sys.path.insert(0, r"C:/!!!Work/MayaScripts/docs/superpowers/plans/poseclip")
import poseclip_maya as pc
pc.apply("goblin")                                        # every part, share 1, motion 1
pc.apply("two_handed_sword", share=0.7, motion=0.8, parts=("torso", "pelvis", "arms", "feet"))
```

Poses are Walk Builder's (`<userAppDir>/SkeldarWalks/<name>.wpose.gz`) or a path to one.

## The model

**Frames.** Every bone's world on every frame (row vectors, `world = local . parent`). The heading `H(f)`: the
root's turn about up from its rest (the identity for this stop). "Relative" below means relative to `H(f)`.

**The reference.** The longest run of at least 8 frames where every body bone moves under 1.5 cm a frame
(here ~73-142); none, the whole clip. Per bone its mean relative world rotation, its mean local rotation,
the pelvis's mean height over the floor (the clip's lowest ball), the feet's mean places. `reference=(a, b)`
overrides it.

**The pose** is carried onto the clip's skeleton by `posemath.Transfer` (Walk Builder's `pose.prepare`: the
legs' ratio for the size, 1 for a twin), placed on the root at the reference. Read off it: each bone's
relative world rotation and local rotation, the pelvis's height over its floor (its lower ball), each foot's
place and rotation relative to the two feet's midpoint, the knees' bend, the hands' relation (a grip when
they are under 30 cm apart) and the weapon bones' hold.

**Knobs:** `share` (0..1, the pose), `motion` (0..2, the clip's motion about its reference), `parts`
(`torso`, `pelvis`, `knees`, `arms`, `feet`, Walk Builder's five).

**Per frame:**
- *Root:* the clip's (root motion is the clip's).
- *Torso and head* (pelvis, spine, neck, head): each bone's relative world rotation `Rel(f) = Ref . G(f)` -
  `G` the clip's motion in WORLD axes - becomes `T . G(f)^motion`, `T = toward(Ref, Pose, share)`. A lean in
  the sprint turns the posed body about the same world axis (trap 229). Positions down the chain from the
  pelvis with the clip's own bone offsets.
- *Pelvis height* over the floor: `h' = T_h . (1 + motion (h / h_ref - 1))`, `T_h = h_ref + share (h_pose -
  h_ref)`. The brake's 57 of 90 cm is 43 under a pose standing at 68.
- *Arms and fingers:* locals, `L(f) = D(f) . Lref` -> `D(f)^gain . toward(Lref, Lpose, share)`, the gain
  `motion` (and `x (1 - share)` for hands that hold one thing together). The left hand of a grip is put
  back on its relation to the right one by two-bone IK. Weapon bones take the pose's hold.
- *Feet:* each contact moves the clip's foot by ONE rigid motion of space `E_k` (a turn about the contact's
  pivot and a shift), so a planted foot stays planted and anything the clip's foot does on the ground (a
  heel rising) is carried with it. Earlier contacts: a shift sideways by half the pose's extra width. The
  LAST contact of each foot: the motion taking the clip's foot (its mean over the contact) onto the pose's
  foot about the clip's final midpoint - the stance, the toe turn, a raised heel. Between contacts `E`
  blends (smoothstep), so a skid or a step carries the foot from one to the next. All `x share`.
- *Legs:* two-bone IK from the hip to the new ankle with the clip's own lengths a frame; the knee on the
  clip's bend plane turned about the hip-ankle line by the pose's knee turn; thigh and calf rotated from
  the clip's by the turn taking (bone, plane) onto the new ones (Walk Builder's `align`); the leg twist
  bones and the toes ride.
- *Balance:* the centre of mass (de Leva's table, Walk Builder's `_masses`) keeps its place relative to the
  feet that hold it: `C' = C + (S' - S) + share (pose_offset - ref_offset)`, `S` the load centre of the
  feet that are down (interpolated across a flight), `offset = C - S` at the reference and in the pose.
  The pelvis (and the body on it) is carried horizontally until the CoM is there; the legs follow by IK.
- *Reach:* where a foot that is down cannot be reached, the pelvis sinks - per frame, then a smooth cover
  over the clip with its ends held (Walk Builder's `smooth_cover`, not periodic).
- *Helpers* (`ik_*`, `interaction`, `center_of_mass`, `camera_*`): each keeps the relation the clip gives it
  to the body bone it follows most rigidly.

`share 0` is the clip: every bone within 1e-4 cm (the legs are solved again by IK on the clip's own feet).

## The scene

- **Read**: the clip under the selection's top joint, every joint's world on every whole key frame
  (`getAttr(time=)`: the clip's skeleton is plainly keyed); the rest from the skinCluster's bind, else
  Manny's template, else as it stands (Walk Builder's rule).
- **The copy**: the character's group duplicated with its upstream graph (`duplicate -upstreamNodes`:
  measured, the copy's skins follow the copy's joints, the original does not move, the group's link to its
  root goes to the copy's root); its curves deleted; the new ones keyed on every frame (`MFnAnimCurve.addKeys`,
  trap 224), the eulers continuous. It stands 150 cm to the character's right (`offset=`). The copy's group is
  marked `skeldarPoseClip` (JSON: the source root's UUID, the pose, the knobs) and lists every node the
  duplicate made; the next run for the same source deletes those first. The clip label, when there is one,
  reads «<clip> + <pose>».
- One undo chunk. The status line says the pose, the knobs, the reference, the contacts moved, the pelvis's
  sink and the balance's carry.
- Refused, by name: nothing selected, no keys, a rig (this version is skeletons), a pose missing the legs
  or the pelvis.

## Proof

`verify_poseclip.py`, mayapy standalone, the plugin's Manny skeleton asset keyed with the stop through this
tool's own writer:
1. share 0: the copy plays the clip (every joint within 1e-4 cm);
2. share 1, motion 0, in the reference: the body is the pose (torso and head to 0.01 deg relative, the
   pelvis height to 0.01 cm, the feet on the pose's stance to 0.1 cm);
3. goblin and two-handed sword at share 1: no planted foot moves more than the clip's own foot did (0.05 cm a
   frame over it), bone lengths the clip's, the CoM's offset from the support the clip's (+ the pose's) to
   0.1 cm where a foot is down, the grip held to 1e-3 cm, the pelvis's height as the rule asks above any sink;
4. the copy: its own group, its mesh on its joints, the original's curves untouched, one undo removes it, a
   second run replaces it;
5. pictures: side-view sheets of the clip, the goblin and the sword at the brake and in the idle.

Unit tests (`tests/test_poseclip.py`) on the pure pieces: contacts, the still run, the cover with held ends,
the contacts' rigid motions and their blend, the height rule, `share 0` identities.

## Not in this version

Rigs as targets; turning clips beyond the heading; the arms' inertia (Walk Builder's springs); a pose share
that changes over the clip; non-UE skeletons as the clip (the pose may be any skeleton); a pose's split
stance on the earlier steps.

## Addendum: three rules the real stop asked for (the same day)

The first run on the stop with the goblin (pelvis 68 cm, trunk 54 deg forward, feet 85 cm apart, its centre of
mass 15 cm right of its feet) came out broken in three ways no unit test could see:

- **The width on a sprint.** The earlier steps took the pose's extra width (50 cm) at full speed: the pelvis
  swung 43 cm a step to stay over the feet and sank to 7 cm over the floor at the brake. A stance is how a
  body STANDS: each earlier contact now takes the width by the body's stillness on it (`Analysis.stillness`:
  1 - the centre of mass's speed / 240 cm/s, blurred over 3 frames). On this stop the sprint's steps take 0,
  the brake's 0.7, the last contact the pose's stance whole.
- **The pose's balance on a sprint.** The pose's centre of mass against its feet (15 cm aside for the goblin)
  is a stance's too: it comes in by the same stillness. Before, the goblin ran with its hips carried 14 cm
  sideways for the whole sprint.
- **A lean past horizontal.** The clip's forward lean added to the pose's: the sprint's +29 deg on the
  goblin's 54 made 80, the brake's fold 94 - the trunk past horizontal, the head 37 cm over the floor. The
  clip's FORWARD lean now takes the room the pose leaves to horizontal: `x (90 - pose lean) / (90 - the clip's
  idle lean)` on the forward component (about the character's side axis) of every torso bone's motion -
  x0.41 for the goblin, x0.95 for the sword; backward, the twist and the sway unscaled. The pelvis's height
  already took its rule in proportion; this is the same idea for the trunk.

Measured after (`verify_poseclip.py` 17/17): the goblin's trunk at most 70 deg forward, the head at least
45 cm up, the pelvis sunk 0.6 cm at most for reach (5.4 before the stillness rule, 39 before the width rule).

## Addendum 2: one tool, a window (the same day)

«Собери все скрипты в один инструмент что бы я его открыл потом выделил нужный мне цикл бега и дальше мог работать
применять позы и парамметры коррекции.» Asked, all the recommendation: **dropped into a viewport**
(`poseclip_tool.py`), **re-keyed when a slider is let go**, and four groups of correction knobs.

- **The window** (plain `cmds`, `skeldarPoseClipTool`): the clip's line and **Use selected** (a bone, a mesh, the
  label, nothing - the only keyed character), the pose menu (+ Refresh), **Pose share** (Torso, Pelvis, Knees,
  Arms, Feet), **Clip motion** (Torso, Arms), **Pelvis, cm** (Height, Forward), **Stance and lean** (Width x,
  Stance at cm/s, Lean limit deg), **Copy** (Offset), Apply / Reset knobs / Delete copy, the status. Every value
  remembered (`skeldarPoseClipTool_*`). Errors land on the status line.
- **One copy for the window** (`<base>_posed_Character`, memo `tool: true`), re-keyed IN PLACE and relabelled on
  every change - the script's `apply()` keeps its one copy a pose.
- **A session** (`poseclip_maya.Session`, on `sys._skeldar_poseclip`): the clip read, analysed and its skeleton's
  rests read once; each pose prepared once. Use selected reads again.
- **The model's knobs** (`poseclip.KNOBS`, `knobs()`, `knobs_from()` for the first version's three): each part's
  share replaces the parts on/off; `motion_torso` (the trunk's leans and sways and the pelvis's bob) and
  `motion_arms`; `pelvis_height` (cm over the rule); `pelvis_forward` (cm ahead of where the balance puts the
  hips: the CoM target moves by what moving them there moves); `width` (the pose's stance x, its earlier width
  `(pose spread x width) - clip spread`); `stance_speed`; `lean_limit`.
- **Faster**: the body above the legs is built once a frame (`_upper`); the balance's carry and the reach's sink
  only move it and solve the legs (`_assemble`); one-rotation exp/log in plain floats. 0.3-0.8 s an evaluate
  against 2.4-7 s, the result the same to 1e-13. A re-key standalone 1.4 s; the first copy with the clip read 5.5 s.
- **A cycle** (no still stretch): no final stance, the reach's cover wraps.

Proof: `verify_poseclip.py` **22/22** (three new: a slider re-keys the one copy in place with the pelvis +8.00 cm
in the idle for 8 asked; another pose relabels the same copy; Delete copy leaves the script's copies);
`tests/test_poseclip.py` 28. Opened in the animator's Maya: the clip read on opening (3.7 s), the window
photographed. Its live sliders are theirs to try.

## Addendum 3: overlap, a start and a final pose, the stop starting on the cycle (the same day)

«Давай сделаем такую же оверлеп систему как и walk builder. Так же нам нужна возможность определить стартовую позу
и финальную. Нужна возможность делать так что бы персонаж начинал анимацию остановки в цикле а заканчивал уже в
указанной позе.» Asked, all the recommendation: the stop starts **exactly on a frame of a cycle** the animator
names (a Walk Builder skeleton or any looping clip in the scene); the start pose goes over to the final one **as
the body stops** (the stillness the stance already uses); **the knees take the start pose's turn on the run**.

- **Two poses.** `Start pose` (or "same as final") and `Final pose`. Per frame `e(f)` = the stillness at
  `final_speed` (cm/s, default 240): the trunk's, pelvis's and arms' targets slerped start -> final by `e`, the
  pelvis's height, the knees' turn, the lean's room, the grip (its relation and its weight) and the weapon holds
  likewise. The stance (the last contacts onto the stance, the width before, the balance offset) is the final
  pose's, as before.
- **Overlap, Walk Builder's springs, not periodic.** The trunk (the chest's world turn through `torso_drag` /
  `torso_bounce`, feeling spine_01's acceleration on the upper body's lever, spread up the spine), the head (its
  gaze through `head_drag`, feeling neck_01's, the necks taking 0.3 / 0.55), the arms (each limb through
  `arm_drag` / `arm_bounce`, feeling its pivot's acceleration on its lever, the hand's lever its farthest finger;
  a grip: the right hand carries the held thing through the spring, both arms reach it by IK). Integrated from
  the first frame at rest, ARM_SUBSTEPS a frame; the pivots' accelerations from their paths blurred over 2 frames
  (a second difference of raw frames shakes a hand - trap 234). Defaults Walk Builder's. Drags at 0: no overlap.
- **Start on the cycle.** `Use selected as cycle` reads a looping clip on a skeleton with the same bone names (its
  period found: the last frame the first moved by the travel, or a repeated end frame dropped). Its frames are
  sampled at the stop's frame rate. The phase is the one whose first `W` frames match the posed stop's first `W`
  best (each bone's local turn, the pelvis's height, which foot is down). The cycle is placed by one turn about up
  and one shift that put its planted foot (else its pelvis) on the stop's at frame 0, its facing on the stop's.
  Over `from_cycle` frames (default 8) the stop goes from the cycle to itself: local turns slerped, the root and
  pelvis blended in the world, the legs by IK to blended ankles (a foot planted in both stays where both have it).
  Frame 0 is the cycle's frame. The status line names the phase.

Proof: `verify_poseclip.py` 25/25 (the stop's first frame on RunFast's frame 26.50 to 4e-10, no planted foot
sliding into the stop, the copy labelled «two_handed_sword > goblin»); `tests/test_poseclip.py` 36.

## Addendum 4: Walk Builder's tools, and the cycle's posture as the start (the same day)

«Проанализируй walk builder он сейчас работает хорошо! Мне бы хотелось тут иметь такие же инструменты которые бы
контролировали веса позы и все остальное. Так же нужно добавить опцию которая будет за основу для старта брать
позу исходного цикла.» Asked, all three the recommendation: **everything of Walk Builder that a stop has a use
for**; the cycle's pose is **its posture read off its frames** (whatever made it - Walk Builder's pose and knobs, or
hands); each pose's weight is **a share and its parts' chips**, as Walk Builder's.

**The window** is Walk Builder's card in a window: the clip; Start pose (menu, Share, chips Torso / Pelvis /
Knees / Arms / Feet), Final pose (the same); the cycle; Apply / Reset knobs / Delete copy; the knobs in six
groups, one shown at a time, `[Stop | Legs | Pelvis | Chest | Arms | Weight]`; `[Both | Left | Right]` for the
knobs a side has; the copy's offset; the status. A part whose chip is lit takes the pose's share, the others 0
(the model keeps a knob a part: the final's `share_<part>`, the start's `start_<part>`). The start's Feet chip is
its toes' turn on the run's steps (the stance is the final's).

**The knobs** (Walk Builder's names and meanings; defaults keep the stop as it was but where Walk Builder's own
default says otherwise):

| group | knob | the stop |
|---|---|---|
| Stop | Final pose at, Stance at (cm/s), From the cycle (fr) | as before |
| Legs | Stance x (sided, was Width) | each foot's offset from the stance's middle x |
| | Foot lift x (sided) | between two contacts, the ankle's height over the line from takeoff to landing x |
| | Swing out cm (sided) | the same stretch bowed `sin(pi u)` out along the heading's side |
| | Leg match 0..1 | running, a side-on pose's turn about up (`hips_yaw`) goes from the pelvis to the lumbar spine (0.4 / 0.35 / 0.25) and the knees' and toes' turns keep their symmetric splay x `1 / (1 + Fr)`, Fr = v^2 / (g L) of the centre of mass; matched x (1 - the stillness at Stance at): standing, the pose stands as it is |
| | Leg turn x (sided) | the poses' knee turns and toe turns x |
| | Knee <-> foot 0..1 (sided) | Walk Builder's `meet`: past 15 deg of knee against toe the two meet |
| | Foot lag fr, Foot flex x (sided) | between contacts the foot hangs in its new calf as the clip's foot did `lag` frames earlier, its turn there x flex, eased in over the first quarter and out over the last (the toes 1.5 x the lag) |
| Pelvis | Pelvis height, Pelvis forward | as before |
| | Bob x | the height rule's motion (was in the trunk's motion) |
| | Pelvis motion x | the pelvis's turns over the reference |
| Chest | Spine x | the spine's and the necks' motion (was Torso motion) |
| | Gait lean 0..1 | x the forward lean the clip's motion keeps (in the room the pose leaves) |
| | Lean limit, Torso drag, Torso bounce, Head drag | as before |
| | Head x | the head's own motion in the world (0 keeps the pose's gaze) |
| Arms | Arms x (sided, was Arms motion), Elbow x (sided), Arm drag, Arm bounce (sided) | the forearm's own motion x Elbow on top of Arms; each arm its own spring (a grip: the two sides' mean) |
| Weight | Balance 0..1 | how far the pelvis is carried to put the centre of mass on its target |
| | Exaggeration x | every motion above x |

`knobs_from` (the script's `apply`) keeps the first version: the motions its `motion`, Leg match and the springs 0.

**The cycle's posture as the start** - the Start pose menu's `(the cycle's)`, chosen by itself when a cycle is
picked with the start on `(same as final)` (and given back when the cycle is cleared). The cycle's frames carry
a posture (a goblin's crouch and lean, a sword held, Walk Builder's pelvis height and stance), and the stop's
run frames carry the sprint's own; the start takes the DIFFERENCE, so the stop runs in the cycle's posture with
its own motion over it and no lean twice:
- the run's weights `r(f) = 1 - e(f)` (e the stillness at Final pose at); a clip that never runs is refused;
- `mean_posture(clip, weights, statics)`: each joint's weighted chordal mean local turn and mean offset in its
  parent, the root at the origin - a pose (Walk Builder's pose file's bones);
- `C = prepare(cycle's mean posture over a period)`, `M = prepare(the stop's mean posture over r)` - both read the
  same way against the stop's reference;
- the start's targets: torso and pelvis `C.rel . M.rel^T . rel_ref` (the posed run's mean is then C's: `T .
  exp(w-bar) = C`); arms and fingers `(M.local . local_ref^T)^-g . C.local` (g the arms' gain on the run);
  height `h_ref . C.height / M.height`; knee and toe turns `C - M`; `hips_yaw` `C - M`; the lean the
  reference's (the room rule then leaves the run's lean alone); the grip and the weapon holds C's.
A cycle that is the stop's own run gives the reference back (the start is the clip as it is).

Not built: Stride, Tempo, Ground time, Twist, Hip drop, Chest twist / sway, Surge, Sway, Weight (Walk Builder's
cycle knobs: a stop's timing and its pelvis's place are the clip's and the balance's).

**What the build changed** (each measured on the real stop, a goblin run from Walk Builder's RunFast as the cycle):
- **The trunk's mean is taken in the world** (`mean_posture(..., world=trunk)`): each pelvis, spine and neck
  bone's mean world turn - what the eye averages - for C and M alike; the arms keep their mean local turns
  (they are carried in their parents). With the springs off, each trunk bone's mean over the run sits off C
  exactly as the clip's sits off its own run mean (pelvis 4.7 / 4.7, neck_01 9.0 / 9.0 deg).
- **The knees, toes, hips and height come from the GAIT, not the mean posture** (`gait`): a running foot is
  kicked up behind half the time, so the mean posture's foot pointed back (-150 deg). Each foot's knee line and
  toe line are read over the frames it is down, the hip line over every frame, each against the clip's travel
  heading (the cycle's loop travel; the stop's own heading); the height is the pelvis over the gait's own floor
  (the cycle's at the stop's size). The stop's gait is read where it runs at speed (at least `RUN_SHARE` 0.75 of
  its top speed, the start more than half shown): its brake plants the right foot turned 105-133 deg across.
- **Leg match leaves the cycle's start alone** (x e): the cycle already runs; matching it turned its hips 22 deg.
- **The toes' turn is a rigid motion of the whole foot** (all toe turns, not only the cycle's): the turn over the
  contact motion's own is held still through a contact (`spread` of the EXTRA, not the total) and turns the
  foot about the contact's point (its load's mean place), so a planted foot rolling onto its ball does not
  slide (the goblin's ball moved 0.55 cm a frame); in the air about the foot itself (`pivot_weight`: 0 on a
  contact, `sin(pi u)` through a stretch), or a foot a metre from its next contact swings wide.
- `knobs_from` sets Knee <-> foot 0: the first version's feet are the pose's (the knee meets the foot).
- **The window**: the start menu's `(the cycle's posture)` with no cycle read falls back to the final pose and
  says so (it refused every Apply - the animator's «после применения не меняется поза»); a reload of the code
  keeps the character the window had; a channel something else drives (a weapon put in the copy's hand
  constrains `weapon_r`) is left to it and named on the status line (the re-key died on it).

Proof: `verify_poseclip.py` **30/30 mayapy standalone** - the earlier 25 plus the cycle's posture with the
clip's motion off (the trunk on C to 3e-10 deg) and on (each trunk bone off C as the clip off its run mean, worst
0.00 deg), Foot lift L 2.5 (the left foot up to 84 cm higher, the right 2e-13), Leg match (the sword start's hips
25 deg to the run, 0 with it off), a weapon-driven bone left to its constraint; 58 unit tests (a foot rolling onto
its ball under a toe turn, a foot in the air turning about itself, the gait read on the ground against the
travel). Picture `poseclip_cycle_posture.png`. The window reopened in the animator's Maya and photographed; no
cycle character in their scene, so the cycle's posture was not seen there.

**The left arm's flip** (the animator, minutes after: «на 15 кадре происходит взрыв левой руки»): the sword's
two-handed grip under Arm drag 2.74 carried the held hand 3-8 % past the left arm's reach on frames 15-17; the
IK straightened the arm, the knee on the line, and the plane read back off it flipped the arm 98-171 deg a frame.
Every IK reads the plane from the hint now (`bend_side`). A unit test holds a hand 10 cm past reach (the old rule:
168 deg a frame; now under 30, the fixture's own straightening).

**The cycle's posture with no cycle loaded is the clip's own run** (the animator: «the cycle posture не работает» -
their scene held only the stop): `OWN_RUN`, no pose on the run (the clip's own reference as the start's targets),
the final as it stops, Leg match left to the final. The window keeps the choice whether a cycle is loaded or not.
The status line names the frames the start holds («the start pose holds frames 0-19, the final from 20 on»).
Verify gate: the trunk on the clip's own over the 24 run frames to 2e-13 deg.
