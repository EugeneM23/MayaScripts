# Ragdoll: a character falls by physics, baked into its rig's controls (2026-10-16)

The animator: «Ты можешь настроить регдол для наших ригов? что бы персонажи падали по физике».
Asked, in order:
- **what for**: a death or a knockdown out of the animation, the body keeping its momentum;
- **baked into the rig's controls**, and the rigs must not cost more («наши риги не должны начать
  есть больше ресурсов ... авто присет или отдельные риги»);
- **muscles that fade**: the joints hold the pose of the fall's first frame and let go over N
  frames;
- **colliders**: a floor plus the meshes selected with the character;
- **the weapon**: a «Drop weapon» check, on by default;
- **where the keys go**: a new override layer or the base layer, a switch, the layer by default;
- **the span**: the time slider's highlight, else the current frame for «Length» frames.

## What exists (measured 2026-10-16, mayapy standalone)

- Maya 2027 ships **Bullet** (`plug-ins/bullet.mll`, `maya.app.mayabullet`); Ragdoll Dynamics is not
  installed, and a third-party plug-in on every colleague's machine is against the zero-setup rule.
- `RigidBody.CreateRigidBody.command(transformName=, colliderShapeType=3 capsule, axis=0 X,
  length=, radius=, bodyType=2 dynamic / 0 static, mass=, bAttachSelected=False)` and
  `RigidBodyConstraint.CreateRigidBodyConstraint.command(constraintType=, rigidBodyA=, rigidBodyB=)`
  work headless; the body starts where its transform stands (the command writes
  `initialTranslate/Rotate` and the pairBlend's input 1 from it). Stepping `currentTime` one
  frame at a time simulates.
- The solver's `gravity` is (0, -9.8, 0) - metres, in a cm scene: a body falls 19 cm in two
  seconds. **-980** for cm.
- `constraintType` 4 (`SixDOF`) takes angular LIMITS - **in degrees**, per axis, in the
  constraint transform's frame (a 30 deg limit held a hanging arm at 30.9) - and ignores the
  angular springs. **`SixDOF2` (5)** takes both: a spring of stiffness 1e6 held a 5 kg arm level on
  a 25 cm lever and let it fall once a keyed stiffness reached 0 (frame 20); 1e4 did nothing.
  The spring's rest is the pose at the start.

## The press

`maya_ragdoll` (a package, a payload row), hub card **Ragdoll** (Animation, after Camera Shake,
Tabler `skull`), hotkey rows `window.ragdoll` and `ragdoll.fall`. One press **Fall**, any part of a
rig selected, plus any meshes to collide with:

1. **The span** `a..b`: the highlight's frames (its own `a`, its last `b`), else `a` = the current
   frame and `b = a + Length`. The playback range is widened to `b` when shorter. Refused: no rig,
   two rigs, a span under 2 frames, a rig in the middle of a retarget (`MoCapConstraints`).
2. **The bodies** (`plan.BODIES`): pelvis, spine_lo (spine_01-02), spine_hi (spine_03-05 and both
   clavicles), head (neck_01, neck_02, head), and per side upperarm, lowerarm, hand, thigh, calf,
   foot (foot, ball) - 16 capsules. Every other game bone (fingers, twist, helpers) rides the body
   of its nearest grouped ancestor, rigidly as at frame `a`; the root stays where it stands. A
   body's capsule runs along its first bone to the next body's first bone (the hand to
   `middle_01`, the foot to past `ball` by half its length, the head 1.3 x neck-to-head up). Its
   radius is the median (it was the 70th percentile; the Creep's calves came out 14.5 cm and sank into the floor) of the distance from the axis of the skinned vertices whose
   heaviest influence is one of its bones, at frame `a` (a bone with none: a share of the length);
   its mass a share of 75 kg (de Leva).
3. **The joints**: each body to its parent body by a `SixDOF2` at the child's first bone, its frame
   built at frame `a`. A **hinge** (elbow, knee) puts its X on the bend axis - the normal of the
   plane the two bones make when bent more than 10 deg, else the body's left-right (knee) / the
   arm's own right-angle to the chest's forward (elbow) - and allows flexion from straight to 150
   deg only, other axes +-5. A **ball** (hip, shoulder, wrist, ankle, spine, neck) allows its own
   symmetric range about the pose at `a`: hip 70, shoulder 90, wrist 60, ankle 35, spine 25, neck
   40, twist about the bone half of it. The capsules do not collide with each other (their filter
   group), only with the floor and the colliders.
4. **The muscles**: every joint's three angular springs, rest = the pose at `a`, stiffness `S x m x
   g x L` (S = `Strength`, m the mass the joint carries, L its lever) keyed from full at `a` to 0
   at `a + Muscle fade` (eased), damping 0.5.
5. **The start**: each body's initial velocity and spin from the motion of its bones between
   `a-1` and `a` (per second at the scene's rate).
6. **The colliders**: a static box under the floor at the lowest foot's sole at `a` (the floor is
   where the character stands, not world zero), and a static mesh body on a DUPLICATE of each
   selected mesh - never the animator's mesh (a rigid body rewires its transform).
7. **The weapon** (Drop weapon on, a weapon held in a hand): its own body (a box of its points,
   2 kg), let go at `a`, colliding with the floor; after the bake it lies on the floor's road
   (`maya_scenesetup.floor`): out of the hand, its drive bone following it, keyed with the
   simulated track.
8. **The simulation**: the solver starts at `a` and the time steps `a..b` one frame at a time;
   each frame every body's world matrix is read.
9. **The bake**: the per-frame world matrix of every game bone (and the unrolled limb bones'
   drive) is a Pose Library animation card in memory - the rig's own skeleton is its source, a
   twin, exact - pasted onto the rig with `animapply` (Replace, every frame, In place: Main is not
   keyed). The layer: `Ragdoll_<a>` (override, weight keyed 0 at `a-1` and 1 from `a`, stepped -
   the take plays until the fall), made active for the paste; or the base layer, every layer
   deselected for the paste. A second Fall on the same frame replaces its layer.
10. **Clean up**: every Bullet node, the duplicates, the solver - gone. Nothing is left on the rig.

The whole press is one undo chunk; the physics part runs unrecorded (nothing of it survives).

## The card

Subtitle (the rig and the span the press would take); sliders **Length** (fr, 60), **Muscle fade**
(fr, 8), **Strength** (x, 1), **Mass** (kg, 75), **Friction** (0.8), **Bounce** (0.1); the check
**Drop weapon**; segments **[New layer | Base layer]**; **Fall** (primary); the status line.
Remembered in `skeldarRagdoll_*`.

## Not in this version

The muscles hold the fall's first pose, never the animation after it; fingers ride their hand;
self-collision between limbs; IK arms or legs are baked as FK values onto the controls the solver
keys (the limbs' blends are read, never written - a limb in IK takes its IK controls).

## Proof

`docs/superpowers/plans/verify_ragdoll.py`, mayapy standalone, Manny_Rig, Creep_Rig, Orc_D_Rig with a
UE run clip retargeted: the keys before `a` untouched; the bake's bones on the simulated bodies;
bone lengths kept; every capsule above the floor at every frame; the body at `a+1` moving as the
clip did; at rest by `b`; the base-layer mode; a selected box stopping the fall; the weapon on the
floor; Undo; nothing of Bullet in the scene after the press.

## Addendum: Cached Playback switched off while it simulates (2026-10-17)

The animator, the day Blend was built: «после того как мы сделали бленд у нас вообще весь регдолл
сломался теперь и фол не работает хотя до этого фол работал отлично». Asked, «Персонаж стоит»: the
layer is made and the character stands.

- **Not the Blend code**: `verify_ragdoll.py` gave the same numbers on HEAD and on the build before
  Blend (b6c0bbb, `Run_Fwd.fbx` on Manny_Rig), and every headless verify fell.
- **Reproduced in a disposable GUI Maya** (port 7027, a scratch `MAYA_APP_DIR`). With Cached Playback
  on, Bullet does not step at all, with the refresh on or suspended: a capsule fell 0.0 cm over 10
  frames, against 85.3 cm with the cache off and the refresh on. Fall pressed with the cache on left the
  pelvis at 86.5 cm at the end (the take's 83.3); with the cache off the same press brought it to 23.5.
- **Why no verify saw it**: a fresh Maya 2027 has the cache on, and the Time Bar has a chip for it.
  mayapy has no cache evaluator, so no headless verify could see it.
- **The fix**: `sim.Scene` switches the cache off before it makes its first node, when it was on. It
  switches it back on once `delete` has taken the nodes; a build that fails puts it back at once. The
  cache flushes and fills again after the press, as after any edit. Fall and Blend both build through
  `sim.Scene`.

Measured after, in the GUI Maya with the cache on:
- **Fall** falls: the pelvis at 23.7 cm at the end, up to 245 cm off the take. The cache is on again
  after the press, and no Bullet node is left.
- **Blend** with Free arms hangs them 71-77 cm off the take mid-span; the legs and pelvis stay on it
  (0.00). The same Blend on the build before: 2-5 cm off mid-span. The arms stood frozen in the first
  frame's direction.

Tests: `tests/test_ragdoll_sim.py`, 5 tests; two of them fail on the build before. 7121 unit tests;
`verify_ragdoll.py` (`AS_Longs_SprintLoop.fbx`) 39/39 and `verify_ragdoll_blend.py`
(`AS_Longsword_Attack_Back_Light_Combo_1_3P.fbx`) 14/14 on Manny_Rig, Creep_Rig and Orc_D_Rig.
