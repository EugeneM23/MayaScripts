# Walk Builder: the walk's mean pose on a Manny rig, edited for the whole cycle (2026-10-15)

The animator: «Мы можем сделать кнопочку которая рядом с нашей походкой будет создавать manny rig на котором будет
наша средняя поза и меняя анимацию на этом риге мы будем менять нашу позу для всего цикла». Asked, and answered:

- the pose may be abstract (each bone's mean is taken alone - «я понимаю что поза будет абстрактной это нормально»);
- **A**: the edit is a correction of the WALK itself (kept beside its file, Reset drops it); the Pose dropdown
  still lays its pose over the corrected walk;
- an edit reaches the walk **by itself**, a short pause after the mouse is let go (Ctrl+Z on the rig too);
- the correction is **the walk's** (every skeleton the walk is put on gets it), not one target's;
- **a**: the upper body's correction rewrites the cycle's frames before the analysis.

## What the animator sees

- A button **Mean pose** beside the Walk dropdown (icon `man`). A press adds a Manny [rig] (Add Character, its own
  group and layer, 150 cm to the side of the target, else at the origin), marked `skeldarWalkMean` = the walk's
  name, and stands it in the walk's mean pose with every correction already made. No keys on the rig: its controls
  hold plain values. One such rig in a scene: a second press, or another walk, re-poses it.
- Moving any control of it (FK or IK, the spine, the arms, the pelvis, the knees, the feet) and letting go: about
  0.4 s later the correction is written beside the walk's file and the card's target (when it walks this walk) is
  keyed again. The line says what moved: «mean pose of asd: upperarm_l 12.0, spine_03 8.0 deg, pelvis -3.0 cm ->
  target keyed again».
- **Reset mean pose** (the right click of the button) drops the walk's correction and stands the rig back in the
  plain mean pose.

## What is read off the rig

Each as a DIFFERENCE between the rig as it stands and as it stood the last time it was read (the "base"), both
carried onto the walk's skeleton the same way (`pose._onto`, the Pose Library's transfer) - so an abstract pose and
a walk that is not Manny's cost nothing: an untouched rig reads no change.

| Part | Read | Goes to |
|---|---|---|
| pelvis, spine, neck, head, clavicles, arms, fingers | each bone's local rotation (twists, helpers, legs, root left out) | the cycle's frames, before the analysis |
| pelvis height | the pelvis over the root, along up | the model's pelvis height (as Pelvis height adds) |
| width | the ankles apart along the walk's side axis | the model's spread (as a pose's width) |
| knees | each knee's bend heading about up | the model's knee turns (as a pose's) |
| feet | each foot's heading (ankle to ball) about up | the model's toe turns (as a pose's) |

Correction file `<walk>.walkfix.json` beside `<walk>.walk.gz`: `{"format": "skeldar.walkfix", "version": 1,
"rot": {bone: 9 floats}, "height": cm, "width": cm, "knee": {"l", "r"} rad, "toe": {"l", "r"} rad}`. A rotation
`C` per bone: the corrected mean local is `C . lmean`.

## Into the model

- `meanpose.correct(clip, fix)` (numpy, pure): every frame's local `L` of a corrected bone becomes
  `L . lmean^T . C . lmean` (the motion about the mean kept, the mean turned); the body is rebuilt by FK; each
  leg is solved again from the new hip onto its old ankle (two-bone, its lengths, its plane turned the least),
  the foot and everything under it kept in the world, so the feet stay where the cycle plants them; a helper that
  followed a body bone rigidly follows it again. A walk read under a correction is cached by the file's time.
- `Walk.fix` (`{"height", "width", "knee", "toe"}`, zeros by default): `evaluate` adds the height to the pelvis's
  mean height, the width to the feet's spread, the knee and toe turns to the turns - each giving way to a pose's
  own at the Pose share, as the corrected mean does (Pose over the corrected walk).
- The mean pose shown on the rig (`meanpose.mean_pose(walk)`): the root at its mean frame on the walk's line,
  every bone by FK of its local means (rotation and translation), the legs then given the fix's height, width,
  knees and feet. Onto the rig through `maya_poselib.apply.plan_for` (Main never written), the values set with no
  keys.

## The live update

`MNodeMessage.addAttributeChangedCallback` on every control of the rig's ControlSet and Undo/Redo scriptJobs
restart a 0.4 s single-shot QTimer; it waits while a mouse button is down. The update reads the rig, writes the
file, keys the target again UNRECORDED (Ctrl+Z belongs to the rig: the target's curves are rewritten in place, no
node made or deleted, so an older undo step still finds them), re-bases. Nothing changed: nothing written. The
callbacks die with the rig (and are dropped on a new scene).

## Not built

Reading the legs' own angles (IK builds them), a mean pose of a pose (the rig shows the walk's mean, the Pose
dropdown stays on top), several mean rigs at once, a rig other than Manny's.

## Addendum - what the build changed

- **The rig's limb bones are read in their drive.** AdvancedSkeleton's shoulder, elbow, hip and knee do not roll - the
  roll lives in the twist joints - so the game upperarm / lowerarm / thigh / calf read bare came back 8-14 deg off the
  mean pose on the arms. `meanrig._read` reads each in its `drive` (`rigsolve.drive_matrices`): 0.0001 deg.
- **A knee is read as a turn, not as a heading.** An absolute heading of the bend about up read 16 deg for a 20 deg
  turn once the width and the height had moved the leg's line; `knee_turn(base, now)` lays the old bend across the
  new line and measures the turn about it - the axis the model turns a knee about - so a leg that only moved reads
  none.
- **Out of reach, the shin stretches.** A hip the correction raises over a straight leg cannot reach its old ankle;
  lifting the foot would break the stance, so the leg stands straight at the ankle with its shin stretched, and the
  target's own reach takes the pelvis down where it falls short.
- **The rig's legs come out in FK** (the Pose Library's solve sets both and the blend stays FK); a knee is turned on
  the rig by its FK controls, or the leg switched to IK (its IK was solved to match: no change read) and its pole moved.
- **The label** «<walk> - mean pose» under the rig (`cliplabel.label_rig`).
