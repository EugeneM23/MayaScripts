# AdvancedSkeleton over the UE5 Manny skeleton — design and record

**Date:** 2026-09-04. **Ask:** «В открытой сцене скелет с привязанной геометрией.
У меня установлен плагин AdvancedSkeleton. Изучи документацию … сделай риг
оснастку для управления скелетом в сцене. Скелет в сцене это скелет из Unreal
Engine 5 … есть специальные пресеты под этот скелет. Сделай всё от начала и до
конца». Follow-up the same day: «оси контролов должны соответствовать осям костей
на исходном скелете».

This is a record of decisions made without the user present, and of what was
measured. It is not a plugin change; nothing in `SkeldarAnim/` moved.

## What was in the scene

An untitled scene holding one `SKM_Manny_Simple` (93 joints, `root` at world
level, two skinned meshes with 89 influences each, A-pose, no animation on the
joints), the studio's own colour material, and the DEBRIS of an earlier
AdvancedSkeleton attempt: `Sets`/`AllSet` with 264 orphaned utility nodes,
two display layers, nine `as*` shaders. `Group` and the rig itself had been
deleted by hand. Those nodes collide with a fresh build by name
(`MainScaleMultiplyDivide`, `FKIKBlendArmCondition_L`, …), so they were deleted
first — after checking that none of them connected to anything outside the set.

## AdvancedSkeleton, read rather than remembered

Version **6.797** at `C:/Users/MY PC/Downloads/AdvancedSkeleton/` (85 050 lines
of MEL, one file). The relevant machinery, all confirmed in the source:

- `fitSkeletons/UE5.ma` — a FitSkeleton authored ON the stock UE5 Manny: every
  mapped joint landed within **0.0003 cm** of ours except Neck (4.69) and Head
  (4.01). Two gaps against Manny: no `twistJoints` on the Knee (Manny has
  `calf_twist_01/02`) and `inbetweenJoints = 2` on the Neck (Manny has one
  `neck_02`). It also carries Eye/Jaw joints for which Manny has no bones.
- The **Name Matcher** (`asNameMatcherUI` → `asMappingUI "nameMatcher"`) is the
  vendor's tool for an *existing* skeleton: template `Unreal5` (auto-detected
  from `ik_foot_root` + `spine_05`) maps AS joint names to UE names; *Create +
  Place FitSkeleton* snaps a template to the bones; *Build*; then **Constraint
  to Joints** (`asMappingUIFunction AutoRigConstraint`: point + orient + scale
  constraints, `-mo`, on every deformation joint whose name has a row) **or**
  Transfer Skinning. The Name Matcher's own template `nameMatchers/Unreal5.ma`
  is a 17-unit skeleton scaled by height/17 with a stray `Chest` hanging off
  `Spine3`; `UE5.ma` is the better fit and was used instead.
- `asNameMatcherCheck` compares `joint.bindPose` — measured: the **world**
  matrix at bind time — against `.matrix`, the local one, and puts up "Reset
  joints to Bind-Pose?" on any hierarchy. A modal dialog over the command port
  blocks Maya's idle queue (bridge note 6), so the Check was never called; its
  other conditions (top-level meshes, reserved names, Z-up, non-default skinned
  transforms) were verified programmatically to be absent.
- The **Unreal Joints** section (Create / Transfer Skinning / Rename to Unreal)
  and **Mannequin export** are the *export* direction — they generate a
  mannequin-named skeleton driven by an AS rig. Not our case; the "Read This
  first" text warns they make the rig non-rebuildable.
- `asCreateGameEngineRootMotion` creates a joint literally named `root` and
  errors when one exists; 6.800 renames it `RootMotion_M`.
- **Control Orient**: `asControlOrientDetach` parks each control's DAG children
  (the FKX joint lives UNDER its FK control) in a `CustomOrientReverse…` node,
  the control is turned freely, `asControlOrientAttach` inserts
  `CustomOrient…` above the Extra and hangs the Reverse back under the control,
  so the children keep their world transform. `customAxis` survives ReBuild
  through "keep custom control orient".

## Decisions

1. **Constrain, do not re-skin.** The UE skeleton is what the studio exports
   (`animexport` bakes the `root` hierarchy) and what the UE bridge merges clips
   onto. Transfer Skinning would move the skin onto AS joints and make the
   exported skeleton AS's. Constraints leave names, hierarchy, skin and bind pose
   untouched — measured drift **0.000000000** on all 93 joints after everything.
2. **`UE5.ma` as the FitSkeleton, snapped where it differs**, Knee given
   `twistJoints 2` (the same `addAttr` the UI runs), Neck `inbetweenJoints 1`
   so `NeckPart1_M` ↔ `neck_02` is 1:1, Eye/Jaw deleted (dead controls
   otherwise), Heel pivot moved from 2.3 cm inside the sole to the back of the
   mesh (z = −5.8 against a mesh minimum of −6.26).
3. **Nine rows added by hand** for the twist and in-between joints. UE numbers
   the lower twists from the far end: `lowerarm_twist_01` is near the wrist, so
   `ElbowPart2 → lowerarm_twist_01`, `ElbowPart1 → lowerarm_twist_02`, same for
   `calf`. Positions matched to 0.10 cm worst (the neck in-between, 0.50 vs
   0.51); `-mo` absorbs the rest.
4. **`root ← Main`** (parentConstraint, no scale) and `ik_hand_gun/ik_hand_r ←
   hand_r`, `ik_hand_l ← hand_l`, `ik_foot_* ← foot_*` — the same pairs AS's own
   mannequin export makes. So **Main is root motion**; in-place animation moves
   `RootX_M` and the IK controls with Main still. AS's dedicated root-motion
   control was not used: it needs the name `root`.
5. **FK control axes = UE bone axes** (the user's ruling). 62 FK controls
   (spine 1–5, neck, neck in-between, head, both arms with all fingers, both
   legs) were detached, given their bone's world rotation
   (`local = R_bone · R_parent⁻¹`, in each control's own rotate order) and
   re-attached with mirror OFF — each side from its own bone. **The six IK end
   controls followed the same evening** («на ИК контролах ног (возможно и рук)
   оси не совпадают»): `IKLeg_L/R` ← `foot_*`, `IKArm_L/R` ← `hand_*`,
   `IKToes_L/R` ← `ball_*`. Nothing moved because the IKX ankle and wrist take
   their orientation from the CHILD nodes `IKFKAlignedLeg/Arm_*` (parked in the
   Reverse node) and AS's Attach re-orients the `AlignIKTo*` nodes that FK↔IK
   alignment reads. The one consumer of an IK control's own rotation — the arm
   pole's follow offset, `PoleOffsetArmMMArm_*.matrixIn[1]` (weight
   `PoleArm.followArm`, 0 by default) — was right-multiplied by D⁻¹, D being
   the control's rotation change, so its product is unchanged (measured
   0.000000000; the leg's `PoleOffsetLegMMLeg_*` is not connected to anything,
   the leg pole follows through an aimMatrix that reads the control's position
   only). `RootX_M` (pelvis) keeps AS's world frame, as AS itself insists;
   pole, roll and FKIK-blend controls were not touched.

## What went wrong on the way, and what it cost

- **Maya crashed at 15:55** — at the first parallel evaluation of the freshly
  wired rig by the verification script (its output file is empty; the crash
  dump is `MayaCrashLog260904.1555.dmp`). The recovered scene held the complete
  S5 state. Every later poke ran with `evaluationManager -mode off` and the mode
  put back; no further crash. Cause not isolated.
- **Attach broke the neck.** `NeckInbetweenMM_M.matrixIn[1]` and
  `NeckPart1InbetweenMM_M.matrixIn[1]` read `FKExtraNeck_M.parentInverseMatrix`;
  after Attach the Extra's parent is the rotated `CustomOrientFKNeck_M`, so
  `FKXNeck_M` came out with local rotate (180, 0, −0.938) = exactly the inverse
  of the custom orient, and `neck_01` flipped (matrix drift 2.0). Those two
  nodes are the only consumers of any `*Extra*.parentInverseMatrix` in the rig;
  reconnecting them to `FKOffsetNeck_M.worldInverseMatrix` (the value they had
  before) restored `FKXNeck_M` to identity. Because the fix came AFTER Attach,
  `CustomOrientFKNeckPart1_M` and the two Reverse nodes had been computed against
  the flipped chain (a stale 0.082 cm translation, −2.852° roll); they were
  normalised analytically — `K = R_bone · R_parent⁻¹`, `Reverse =
  R_parent · R_bone⁻¹`, FKX local identity — and the drift list went empty.
  The procedure script moves the reconnect ahead of Detach.
- **Shoulder/Elbow roll:** rotating `FKShoulder_L` about its X does not roll
  `upperarm_l` (angle 0.0 measured). That is AS's twist design — the roll goes
  to the ShoulderPart joints and the elbow, the shoulder joint stays — and it
  matches how UE's twist bones are meant to carry it. Not a defect.
- **Legs are IK by default** (`FKIKLeg_*.FKIKBlend = 10`), arms FK; FK leg
  controls do nothing until the blend is switched.
- **A Bash call longer than ~8 KB fails** in this harness with "unexpected EOF"
  and runs nothing. Cost the first bridge run, the S7 run and the S13 run.

## Measured, in the final state

- 79 AS deformation joints → 79 UE joints, point + orient + scale, every driver
  the expected one; 6 extra parent constraints; 8 followers unconstrained.
- Zero pose vs the pre-build snapshot: **0.000000000** on all 93 joints.
- FK control frame vs bone frame: **0.00000°** on all 62 (was 180° on 58).
- Axis tests (25° on a control axis → bone turns 25.000° about ITS same axis):
  fingers, wrist, spine, head, neck in-between all three axes; `FKNeck_M` gives
  12.5° on `neck_01` and 25° on `head` (the in-between start bias — AS design).
- Mirror: `FKShoulder_L/R rz=30` → hands at ±48.06 / 101.44 / −10.98,
  error **0.0003 cm**. `Fingers_L.indexCurl` still curls (89.8° on
  `index_02_l` at 5) because the SDK groups sit above the custom orient.
- Skin: 89/89 influences, both `bindPose` nodes, meshes unmoved at rest.
- IK control frame vs bone frame: **0.0°** on all six; `IKLeg_L/R` and
  `IKArm_L` about X/Y/Z turn the bone 25.000° about its own X/Y/Z; the four
  poles unmoved at rest, `PoleArm.followArm=10` lands where it did before
  (0.000000). FK→IK align on the arm (`asAlignIK2FK`) matches the hand's
  world matrix to 1e-6 with the hand 12.6 cm from rest; IK→FK on the leg
  (`asAlignFK2IK`) matches foot and calf to 0.000000.

## Evening follow-ups: the finger curl and the IK foot shapes

The user, after using the rig: «Fingers_L сгибает пальцы по ложным осям, не по
осям костей изначального скелета. ИК контролы ног теперь имеют правильные оси
поворотов, но визуально перевернуты».

- **Fingers.** The curl/spread set-driven keys drive the `SDKFK<Finger><n>_<S>`
  groups (`rotateY` = curl, +90° at curl 10; `rotateZ` = spread, index +40 /
  pinky −60 at spread 10), and those groups sit ABOVE `CustomOrient` — so they
  still turned about AS's axes. Measured: `indexCurl` bent `index_01_l` about
  (0, 0.237, 0.971) in the bone's frame, 14° off the UE bend axis Z; spread
  about (0, 0.971, −0.237). Fix: each of the 28 groups was re-parented under a
  `UEAxis<group>` node (attribute `ueAxisFor` = the bone) whose frame is
  **y = bone Z, z = bone Y, x = y × z** — the curl channel then turns about the
  UE bend axis and spread about the UE spread axis, wiring untouched — and the
  `CustomOrient` below was recomputed (`K.local = K.world · G.world⁻¹`) so the
  rest pose did not move (K world error 0.000000000). Signs were chosen by
  measurement, first try: curl now turns **all 28 phalanges about exactly
  (0, 0, +1)** — the UE convention where positive Z curls inward on both hands
  (the bind values are +23.4°/+14.9°/+12.5° on the index) — 45/90/135° at
  curl 5; spread +5 opens the index–pinky tips by **+4.76 cm on both hands**.
- **IK shapes.** A control's curve is drawn in its local space, so turning the
  frame turned the drawing; the FK rings are symmetric about the bone axis and
  never showed it, the IK foot boxes (open degree-1 curves, 15 spans) did. AS's
  own Set Axis has "keep curve unaffected"; Detach/Attach does not. For all 64
  custom-oriented controls the CVs were multiplied by `R_old · R_new⁻¹` (R_old =
  the frame of `CustomOrient`'s parent, where AS drew the curve): every curve is
  back where AS drew it to **0.000000000 cm**, the axes unchanged (0.000002°).
- Both steps are in `as_ue5_rig_procedure.py` (`restore_shapes`,
  `finger_sdk_axes`) and gated (22, 23) in the verify script.

## Not done, deliberately or not yet

- Pole, roll and FKIK-blend controls keep AS's orientation. `IKToes` was
  re-oriented for consistency, but its rotation drives nothing (it positions
  an ikHandle), so that frame is cosmetic.
- `RootX_M` keeps AS's world frame.
- ReBuild re-generates the neck network with the vendor's
  `Extra.parentInverseMatrix` reading; after any ReBuild run
  `as_ue5_rig_procedure.orient_controls()` again (it reconnects first).
- The UE bridge's import guard (trap 37) refuses a merge onto constrained
  joints; with this rig the character receives clips through AS's MoCap Matcher
  or after disconnecting. Export through `animexport` (bake on export) is
  unaffected.
- The scene lives at the crash-recovery path
  (`%TEMP%/UE5[Recovered-…15.55].ma`); a Save As is the user's.
- Backup of the pre-rig state:
  `Documents/maya/projects/default/scenes/Manny_before_AdvancedSkeleton_20260904_1548.mb`.

## Files

- `docs/superpowers/plans/as_ue5_rig_procedure.py` — the sequence, re-runnable.
- `docs/superpowers/plans/verify_advancedskeleton_ue5_rig.py` — 23 live gates, **green live 2026-09-04, 0 of 23 gates failed**.
