# AdvancedSkeleton over the PlayerMale game skeleton — design and record

**Date:** 2026-09-05. **Ask:** «В открытой сцене в мая есть новый скелет это не
unreal engine. Давай для этого скелета соберем риг на базе advanced skeleton.»
Design presented, one question asked (control axes as on Manny, or AS's own);
the answer was «делай» — the Manny ruling stands: every FK control and IK end
control carries the local axes of the bone it drives.

This is a record of decisions and measurements, the sibling of
`2026-09-04-advancedskeleton-ue5-rig-design.md`. Not a plugin change; nothing in
`SkeldarAnim/` moved. Procedure: `docs/superpowers/plans/as_playermale_rig_procedure.py`.
Proof: `docs/superpowers/plans/verify_advancedskeleton_playermale_rig.py` —
**green live 2026-09-05, all 27 gates passed** (after the evening follow-up below).

## What was in the scene

`C:/!!!Work/work/Assets/Game/3d/Characters/Male Character/PlayerMale_v6.fbx`,
opened as an FBX (so there is no `.ma` to save into — the animator's Save As is
theirs). One skeleton of **57 joints**: `Root` at the origin, `Hip`, `Spine1..4`,
`Neck`, `Head`, `Jaw`, `Right_Eye`/`Left_Eye`, clavicles as `*_Shoulder`,
`*_Arm`/`*_ForeArm`/`*_Hand`, five fingers of three joints each and no
metacarpals (`*_Finger1..3` is the index), `*_Thigh`/`*_Knee`/`*_Ankle`/`*_Toes`.
The side is a **prefix** (`Right_`, `Left_`); bones run down local X, the left
side down **−X** (mirror-behaviour skeleton: identical `jointOrient`, negated
translations); rotate orders mixed (41 zyx, 8 xyz, 6 zxy, 2 yzx); bind rotation
partly in the rotate channels (arms 6.7°, thighs −5.7°, hands ~4°); no twist
joints. **17.5 units tall in a centimetre scene** — the file is at 1:10 (a
`Assets/Game/...` project, Unity-style), hip at y = 11.207, head top at 20.063.
Right side on −X, facing +Z, A-pose with the arms **99.4 % extended** and the
legs 99.9 %. Current pose = bind pose (worst matrix element 2.3e-5 against
`bindPose1`). **70 skinClusters** — every outfit, head and hair variant on the
same joints; the Body has 55 influences (all but the eyes). No animation, no
rig, `VPStudio` from the Viewport Studio tool standing by.

The scene is 1:10, and it happens to be the scale AdvancedSkeleton's own
templates are drawn at (`biped.ma`: pelvis at y = 9.83, the Name Matcher scales
by height/17), so nothing had to be rescaled.

## AdvancedSkeleton, read rather than remembered

- `fitSkeletons/biped.ma`: 43 joints, spine **`Root > Spine1 > Chest`** (no
  Spine2 — the first fit attempt died on exactly that KeyError), `Cup` under the
  wrist holding Ring and Pinky, `Heel`/`FootSideInner`/`FootSideOuter`/`ToesEnd`,
  `HeadEnd`, `Eye`+`EyeEnd`, `Jaw`+`JawEnd`; `twistJoints 2` on Shoulder/Elbow/Hip,
  `inbetweenJoints 2` on Root/Spine1/Neck, `Neck.unTwister` on, `Ankle.worldOrient`,
  `Eye.aim`. Its finger driving system is 34 `SDK*` animCurves connected to
  `FitSkeleton.drivingSystem`, two of them for `Cup`. `bipedGame.ma` is a 170-unit
  variant with `twistJoints 1` and no Cup/FootSide; not used.
- **The Name Matcher's own placement (`asNameMatcherCheckAndAutoRigFit`) is the
  vendor's tool for exactly this**, and it was read for its heuristics but not
  called: it starts with `asNameMatcherCheck` (the "Reset joints to Bind-Pose?"
  modal — bridge note 6), turns `segmentScaleCompensate` off on EVERY joint in
  the scene, and answers a name clash by moving the other skeleton into a
  `NameMatcher:` namespace for good. Its useful facts: it scales the fit by
  height/17, places mapped joints with `xform -ws`, calls `asFitModeManualUpdate`,
  and zeroes the `jointOrient` of a finger joint whose tip was not placed.
- **`asFitSkeletonImport` ends in `asImportMatcherScan`**, which for a `biped*`
  template looks for ANY joint named `*Hip*`/`*hip*`/`*pelvis*` and asks "External
  skeleton detected. Align joints with this skeleton?" — a modal, which over the
  command port is a blocked idle queue. The vendor suppresses it with a node named
  **`FitSkeletonNameMatcherImporting`** (the proc returns early while it exists);
  the procedure creates it around the import and deletes it.
- **`asFitModeManualUpdate` runs `asUniqueNameAll`**, which RENAMES any fit joint
  whose short name is not unique in the scene (`Hip` → `Hip1`), and `asLabel`
  errors on a non-unique name. Together with `getAttr Hip.twistJoints`-style
  access throughout the toolset, this is why the game skeleton's clashing names
  must be out of the way for the fit and the build (below).
- `asReBuildAdvancedSkeleton` refuses only the names `Group`, `MotionSystem`,
  `DeformationSystem`, `Geometry`, `Main`; needs cm units; the first build took
  **4.6 s**. `bodySetup` is a UI name, not a node — `buildPose` is the node.

## Decisions

1. **Constrain, do not re-skin** — as on Manny. The game skeleton is what the
   game imports; every one of AS's 56 deformation joints drives its twin through
   point + orient + scale constraints (`-mo`), written by long path in Python (the
   vendor's "Constraint to Joints" resolves targets by short name, and with the
   names restored `Hip` would be ambiguous). `Root ← Main` (parentConstraint) so
   **Main is root motion**; `RootX_M` moves the hip and leaves `Root` alone
   (gate 20). 169 constraints.
2. **Mapping, 1:1 spine.** `Root_M ↔ Hip`, `Spine1..3_M ↔ Spine1..3`,
   `Chest_M ↔ Spine4` (Chest keeps its name so AS's IK spine and every
   Chest-special-case build as the vendor intends; two joints, `Spine2` and
   `Spine3`, are duplicated in from `Spine1` and chained), `Neck`, `Head`, `Jaw`,
   `Eye ↔ *_Eye`, `Scapula ↔ *_Shoulder`, `Shoulder/Elbow/Wrist ↔ *_Arm/*_ForeArm/
   *_Hand`, `IndexFinger1..3 ↔ *_Finger1..3`, Middle/Ring/Pinky/Thumb 1:1,
   `Hip/Knee/Ankle/Toes ↔ *_Thigh/*_Knee/*_Ankle/*_Toes`. Side rule:
   `_R → Right_`, `_L → Left_`, `_M → no prefix`.
3. **The clashing names are HELD, not renamed for good.** `Root`, `Hip`, `Spine1`,
   `Spine2`, `Spine3`, `Neck`, `Head`, `Jaw` are the fit joints' own names.
   `hold()` renames those eight game joints to `PMhold_<name>` and writes the
   original onto a string attribute `asHeldName`; `release()` reads it back.
   Constraints, skin and both bindPose nodes are wired to nodes, not names, so the
   round trip is free (gate 23: hold 8, unique during the hold, the drive
   following to 0.00000°, release 8). Cost, stated: after `release()` the fit's
   `Hip` and the game's `Hip` share a short name again, so **any ReBuild needs
   `hold()` first**, and AS's fit-mode buttons complain until then. A permanent
   `NameMatcher:` namespace on the game skeleton — the vendor's answer — was
   rejected: it would ride into every exported bone name.
4. **`twistJoints 0` on Shoulder, Elbow, Hip; `inbetweenJoints 0` everywhere.**
   The skeleton has no twist bones, so the roll must land on `*_Arm`/`*_ForeArm`/
   `*_Thigh` themselves — on Manny AS sent it to the Part joints and the main bone
   did not roll. Measured after: `FKShoulder_R.rotateX 25` rolls `Right_Arm`
   **25.00000°** about its own X with the forearm's local rotate untouched
   (gate 13). `Cup` deleted with its two SDK curves (no metacarpals); Ring and
   Pinky re-parented to the wrist first.
5. **End joints from the geometry** (`end_positions`): HeadEnd on the top of the
   bare head mesh (`|HEAD1|Head1`, y 20.063 — the crown and the hair sit higher),
   JawEnd on the chin (front-most low midline vertex, (0, 17.72, 1.11)), EyeEnd
   1.0 in front of the eye, fingertips at J3 + 0.8·(J3 − J2), and the foot pivots
   on the bare foot's sole in the Body mesh: ToesEnd (−2.319, 0.169, 2.363), Heel
   (−2.240, 0.169, −0.475), FootSideInner/Outer at x −1.774/−2.839. Every mapped
   fit joint landed **0.000000** from its bone (44 placed, parents first).
6. **FK control axes = bone axes** (55 FK controls; `RootX_M` keeps AS's frame as
   before). Worst frame angle **0.000003°**; 25° on any of twenty controls' axes
   turns its bone 25° about the bone's own axis, worst **0.00000°** (gate 14).
   Curves redrawn axis-aligned in the bone frame. **The six IK end controls keep
   AdvancedSkeleton's own world-aligned frames** — they were put on the bones'
   axes first, like on Manny, and taken off again the same evening (below).
7. **Finger SDK axes measured, not assumed.** On this skeleton the knuckle line is
   a phalanx's local **Y** and the palm normal its **Z** (both hands), so AS's curl
   channel (`rotateY`) wants the bone's Y and spread (`rotateZ`) its Z — the SDK
   group's frame is the bone frame itself, the same formula on both hands.
   `calibrate_finger_axes` measures each hand and flips y or z independently if a
   channel goes the wrong way; here neither does.

## What went wrong on the way, and what it cost

- **The first probe misread the left hand.** It took the palm to be the side the
  cross product `(index − hand) × (pinky − hand)` points to; that is the palm on
  one hand and the back of the other. It then "fixed" the left hand by turning
  its SDK frame 180° about the bone, which reversed both curl and spread there
  (curl +0.676 to the back, spread gap −0.497). The rule that stands: **the palm
  is the side the thumb sits on** (`finger_probe`). With it both hands read curl
  +0.4972 toward the palm and spread +0.4623, and equal curl on both hands puts
  the index tips at mirrored positions to **8e-6**.
- **`cmds.exactWorldBoundingBox` did not follow the skin.** With `Main.tx 3` every
  joint and every vertex of the Body had moved 3.000 (`pointPosition`), and the
  bounding box answered **0.00002** — in DG mode, after `refresh`, and in parallel.
  The mesh transform is locked by the FBX importer, which may or may not be the
  reason; either way a gate about skin must read a vertex.
- **The arm is 99.4 % extended at rest**, so an IK test that pushed the hand 1.0
  forward got 0.928 — out of reach, not a broken IK. The test lifts the hand.
- **The skeleton is not perfectly symmetric**: the forearm frames differ by
  0.156° between sides (rotate channels −2.35/1.83 against −2.50/1.87), so equal
  values on both arms put the hands 0.003 apart in mirror — the skeleton's own
  asymmetry, the gate says so and allows 0.01.
- The biped template has no `Spine2`; a KeyError one line into the shape edit.
  `reset_fit()` (deletes the unbuilt fit and its orphaned SDK curves, refused once
  `Group` exists) is what lets a fit start over without the vendor's
  Replace/Merge dialog.

## Evening follow-up: «оси контролов руки не совпадают с осями костей и стоят криво»

Minutes after the rig was handed over, with the legs next: «Контролы ног тоже
выглядят криво». Measured, every FK control and IK end control carried its game
bone's frame to **0.00000°**, with no scale or shear anywhere and every FK ring's
plane exactly perpendicular to its bone — so the crookedness had two other causes,
both real:

- **The bones' own axes are crooked on this skeleton.** `Right_Ankle`'s X points
  at the ball joint, 26° below horizontal; `Right_Hand` is rolled 34° against AS's
  wrist frame. An IK foot control carrying the ankle's axes stood nose-down with
  its box reaching into the floor; the hand cube sat on the rolled hand axes. On
  Manny the UE bone frames were nearly world-aligned (the foot boxes turned
  8.71°), so the same rule looked right there and wrong here.
- **AS's deformation skeleton was drawn exactly on the game bones**, with axes of
  its own — `Ankle_R` 64.43° off `Right_Ankle`, `Wrist_R` 34.06° off
  `Right_Hand`, `Head_M` 85.23° off `Head`. A click on "the bone" in the viewport
  landed on it as readily as on the game joint, and against its axes the controls
  did not match.

Three options were put to the animator — (A) IK ends back to AS's frames, FK on
the bones, AS skeleton hidden; (B) everything back to AS's frames; (C) hide the AS
skeleton only — with A recommended; the answer was «давай А попробуем».

**What A did** (`as_frames()` in the procedure, live): the six IK end controls'
drawings put back to AS's CVs (the axis permutation undone while still known),
Detach, each control's world rotation set to the frame of the node above its
CustomOrient (`IKOffsetLeg_R`, `IKOffsetArm_R`, …), Attach with mirror off, the
arm pole's follow offset compensated the same way as before. Measured: all six
**0.000000°** from AS's frame, `IKLeg_R` and `IKArm_R` world axes the identity,
no CustomOrient left on them, the FK controls untouched, the fingers unchanged
(curl 0.4972 / spread 0.4623 both hands), the game skeleton's drift still
2.1e-7. AS's 72 deformation joints went into a display layer `AS_DeformSkeleton`,
hidden; the game skeleton stays in the visible `PlayerMale_Skeleton`. The
procedure's `orient_controls(ik_ends=False)` now builds this state directly, and
the verify gained gates for the AS frames and the layers (27 gates).

Consequence for the IK controls: `IKLeg_R.rotateY 20` turns the foot about the
CONTROL's Y, which is world up — the gate says so — rather than about the ankle
bone's tilted Y. That is what a flat foot box promises.

## Later that evening: the hand frame, from the animator's locators

«locator10 - для правой руки! locator9 - для левой. Давай контролы рук
сориентируем по этим локаторам я сделал их как подсказку для тебя». Two locators
on the hand joints (0.07 and 0.02 away), mirrored the way the skeleton mirrors
its joints (locator9 is the point-mirror of locator10 to 0.02–0.16°): X along the
fingers (0.995 with the middle-finger direction), Z the palm normal, **29.28° off
the hand BONE's frame** — whose X points at the middle finger's root, not along
the fingers — and 7.9° off AS's wrist. So neither of the earlier answers (bone
axes, AS axes) was the hand frame the animator wanted; the locators are it.

Applied to `IKArm_R/L` and `FKWrist_R/L` by `frame_controls()`: the standing
shape alignment undone first (while its permutation is still known), Detach /
set / Attach with mirror off, the arm pole's follow offset compensated, the
curves re-aligned on the nearest axes of the new frame. Measured: all four
**0.000000°** from their locator, the game skeleton's drift still 2.1e-7, every
other control and the fingers unchanged, `FKWrist_R.rx 25` turning the hand
25.000° about the control's X. The frame is recorded as `HAND_FRAME_IN_BONE`
(the locator's axes in the hand bone's coordinates — the same numbers on both
sides), so `run()` reproduces it in a scene without the locators; `hand_frames()`
prefers the locators when they exist.

**The animator works in the scene while the bridge does.** Measuring the two
wrists' mirror, the left one did not move at all: `FKShoulder_L`, `FKElbow_L`
and `FKWrist_L` carried the animator's own parentConstraints to `locator1/2/3`,
beside an OverRig `base_IK_strech1` — a test in progress on the left arm, made
between two of our runs, and left alone. The verify now **skips, and says so**,
every pose that would go through a control holding a constraint whose target
lies outside `|Group` (`foreign_constraints`), instead of reporting the rig
broken.

## Measured, in the final state

- Game skeleton whole: 57 joints, their own names, no `asHeldName` left; world
  matrices on `bindPose1` to **2.3e-5** at build pose and again after every poke
  (gates 1, 9, 26).
- 56 deformation joints, 56 mapped, `Root` ← Main; 169 constraints, each game
  joint's three targets the expected twin (gate 5). No animation, no pairBlend on
  the skeleton; 70 skinClusters and both bindPose nodes intact.
- 53 FK controls on their bones' frames; `FKWrist_R/L` and `IKArm_R/L` on the
  animator's hand frame (0.000000° from the locators); `IKLeg`/`IKToes` on AS's
  world-aligned frames (0.00000°); AS's skeleton hidden in `AS_DeformSkeleton`.
- Legs IK (`FKIKLeg_* 10`), arms FK; IK leg lifts the ankle **1.0000** with the
  thigh planted (0.0000000) and turns the foot 20° about the control's world Y
  (0.00000° off); IK arm the same for the hand once the blend is 10.
- Main carries Root, head and a Body vertex **3.000000** and yaws Root
  0.00000° off; the eye aim turns both eyes 40.6° and the head 0.0°; the jaw
  control turns `Jaw` 20.0000°.
- The run keyed nothing (42 animCurves before and after — the fit's SDK curves).
- Skeleton in the display layer `PlayerMale_Skeleton`; FitSkeleton hidden under
  `Group`. Backups in `Documents/maya/projects/default/scenes/`:
  `PlayerMale_v6_before_AdvancedSkeleton_20260905_2248.mb`,
  `PlayerMale_v6_AdvancedSkeleton_rig_20260905_2255.mb` (IK ends still on the
  bones) and `PlayerMale_v6_AdvancedSkeleton_rig_final_*.mb` (the state above).

## Not done, deliberately or not yet

- `RootX_M` keeps AS's frame; pole, roll and FKIK-blend controls too (as on Manny),
  and since the follow-up the IK end controls as well.
- `Neck.unTwister` and `Ankle.worldOrient` stay at the vendor's defaults.
- A ReBuild has not been exercised. The sequence it needs: `hold()` →
  `asReBuildAdvancedSkeleton` → delete the constraints on the game joints whose
  targets died with the old rig → `constrain()` → `orient_controls()` →
  `align_shapes()` → `calibrate_finger_axes()` → `release()`.
- The scene is still the opened FBX; saving it as `.ma`/`.mb` is the animator's.
- Twist joints: none in the skeleton, none built; the roll stays on the bones, and
  a game that expects twist bones would need them added to the skeleton first.
