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
