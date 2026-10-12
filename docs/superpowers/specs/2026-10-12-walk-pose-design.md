# A character pose under the parametric walk - the goblin (2026-10-12, the third step)

The animator, with a skeleton in the scene posed as a hunched goblin: «Давай теперь сделаем позу гоблина.
В открытой сцене стоит скелет в нужной позе попробуй теперь сделать адаптацию этой позы под нашу походку».
Asked, and answered: take **the torso and head, the pelvis (its height and tilt) and the knees' direction**
from the pose - not its arms, not its feet; keep the pose's **asymmetry as it is**; the pose is **saved from
the selected skeleton (Save pose...) and dialled in by a "Pose" knob 0..1**. Built on
`2026-10-12-parametric-walk-design.md` and `2026-10-12-walk-onto-any-skeleton-design.md`.

## The pose, measured (read only, the open scene)

The Manny skeleton keyed at frame 0: the pelvis at 68.3 cm (the walk's mean 95.1) and turned 37.4 deg from
the walk's mean pelvis; the torso leaning 60.2 deg from up (32 cm forward, 25 cm to the right); spine_01..05
locally 11-21 deg off the walk's means, neck_01 17; the head 29.5 deg off the walk's in the world; the left
foot far out to the side and on its toes, the feet 85 cm apart; the left hand low in front, the right raised
behind; **the left knee bending 31 deg INWARD of forward, the right 46 deg outward** (the walk's: 8-10 deg
outward both) - a lunge more than a stance. Kept as it is, by the animator's choice: the goblin walks with
the torso leaned right and the left knee in.

## The model

The walk is the mean pose plus the motion around it; the pose replaces the mean, `α` = the knob `pose`
(0..1, default 0 - at 0 the walk is exactly what it was):

- **spine and neck** (`spine_*`, `neck_*`): each local mean slerped to the pose's local rotation,
  `mean' = exp(α · log(pose · mean⁻¹)) · mean`; the walk's local deviation applied over it as before;
- **head** (world): its world mean slerped to the pose's head;
- **pelvis**: its world-rotation mean slerped to the pose's; its height (over the travel line) lerped to the
  pose's - the legs bend by the IK, the reach drop as before; its sideways and forward offsets stay the
  walk's (the pose's 16 cm shift onto one leg is no walk);
- **knees**: each leg's bend direction turned about the leg's hip-ankle line by `α · Δ` - `Δ` the angle,
  about up, from the walk's mean knee heading to the pose's;
- **upper arms hang in the WORLD** (every walk, pose or not): an upper arm's world rotation is its world
  mean and world deviation (`exp(g · ω_world) · mean_world`), so on a hunched torso the arms still hang and
  swing by gravity from the shoulder; the forearm, the hand and the fingers stay local. At the defaults this
  is the source exactly (the same world rotation); it changes what Spine and Arms do: the arms no longer turn
  with the chest.

**Into the walk's skeleton**: the pose is saved from any skeleton (`Save pose...`: its bones as the Pose
Library reads them, the current frame, the walk tool's rest rule) and carried onto the walk's skeleton by
`posemath.Transfer` (the walk's skeleton at rest, standing on the walk's root frame at its first frame; the
size the legs' ratio, 1 for a twin) - `walkpose.prepare(walk, statics, pose_bones)` hands the model numpy
data: the spine/neck locals, the head's and the pelvis's world rotations, the pelvis height, the two knee
turns. The model stays numpy-only.

**Files**: `walks/<name>.wpose.gz` (gzip JSON `skeldar.walkpose` 1: name, bones {leaf: parent, canonical,
rest, world}). **The window**: a Pose list ("(none)" + saved poses) beside **Save pose...**, the knob
**Pose** at the top of the knobs; the marker on a walked skeleton gains `pose` (the name); Pick reads it.

## Proof

- unit: the pose amount 0 with a pose given = the walk; with the motion off (exaggeration 0) and α = 1 the
  spine locals, the head and the pelvis rotation ARE the pose's and the pelvis height is; the knees turned by
  Δ; arms hanging in the world under a spine knob; the pose file round trip; `prepare` on a twin recovers
  the pose.
- `verify_walk.py`: a hunched pose built on Manny (and the animator's goblin when saved in walks/) applied
  at Pose 1: the pelvis at the pose's height (over the drop), the torso leaning as the pose's, the knees'
  headings turned, the stance feet as still, lengths kept, the seam; Pose 0 = the walk.

## Addendum (2026-10-12, the build)

- Built as designed. `walkpose.prepare(walk, statics, pose_bones, model, target_module)` (it takes the two
  modules so the model stays numpy-only); the knob `pose` is the first of the model's knobs.
- The animator's pose was saved through the tool (`save_pose`) over the port, read only, as
  `walks/goblin.wpose.gz` - 93 bones at frame 0.
- Measured (`verify_walk.py` 20/20): Pose 1 puts the pelvis at the pose's 68.28 cm exactly (over the drop),
  the torso at the pose's 60.2 deg lean, the knees turned by the pose (-43.5 / -38.5 deg against -41.2 /
  -38.2 at mid-stance - the leg's line is not vertical there); Pose 0.5 is half way (81.71 cm); the stance
  feet, the bone lengths and the seam are untouched by the pose.
- The pose's asymmetry shows as the animator chose: the goblin walks leaned to its right with the left knee in
  (`walk_goblin.png`, side and front).
