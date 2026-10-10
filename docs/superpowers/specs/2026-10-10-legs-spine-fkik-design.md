# FK / IK for the legs and the spine (Connections), 2026-10-10

The animator: «во вкладке connections добавим переключение FK IK для ног и спины». Arms
already switch (`fkik`, 2026-09-30); this adds the same press for each leg and for the spine,
keeping what the limb shows, over the highlighted range or the whole take, keys only where
the source is keyed (2026-10-08 rule). Taken alone (the animator was away): one row per leg
under the arms, one Spine row under the legs, the same FK / IK check boxes.

## What the rig is (measured on `SkeldarAnim/assets/Manny_Rig.ma`, mayapy)

**Legs** (`FKIKLeg_<side>`, startJoint Hip, middleJoint Knee, endJoint Ankle). Each deform
joint blends `FKX*` and `IKX*` through `Hip/Knee/Ankle` constraints and `ToesBM_<side>`.
The IK leg is an `ikRPsolver` (`IKLegHandle_<side>`) with `PoleLeg_<side>`, its ankle end
is `IKLeg_<side>` aligned by `AlignIKToAnkle_<side>`, and the toes are an `ikHandle`
(`IKToesHandle_<side>`) from `IKXToes` under the `IKToes_<side>` control. The FK knee bends
about its local **Y** (`rotateY`); `rotateX` is the bone's own roll (the bones run along
local X), and the FK hip's swing is `rotateY` too.

**Spine** (`FKIKSpine_M`). Deform `Spine1..4_M` blend `FKXSpine*` and `IKXSpine*` through
`Spine<n>BM_M`; `Spine5_M` point-constrains to `FKXSpine5_M` only, but the FK top chain
hangs under the deform Spine4 (`FKParentConstraintToSpine4_M`), so Spine5 moves when Spine4
turns. The IK spine is an `ikSplineSolver` (`IKSpineHandle_M`) on `IKSpineCurve_M`, whose
five CVs are the `IKSpineLocator0..4_M`, parented to `IKSpine1_M`, `IKcvSpine1..3_M` and
`IKSpine3_M`. The IKX joints sit **on the curve, not on the CVs** (moving CV2 by 6.7 cm moved
IKX2 by 3.2 cm), so the spine cannot be copied onto the controls.

## The switch

**Arms and legs** share `fkik`. The chain is the arm's (three joints; a leg adds the toes as
a fourth joint, `Limb.tip` is its IK control). To FK: the FK controls take the shown joints
through the rigid FK chain (unchanged). To IK, in this order (the order is the fix):

1. the IK end control on the shown ankle / wrist through the align (unchanged for arms);
2. the **pole**: on the bend side of the shown knee, **read from the shown knee of each
   frame** (`bend_side`, `pole_on_side`). A straight leg has no bend, and falls back to the
   rest pole (`_pole_refusal` checks that before anything is written);
3. the pole's parent is read **after** the IK control is written. A leg's pole rides the IK
   leg (`followLeg`): read before, the pole stood 31 cm off what was aimed (measured);
4. the **toes**: a per-frame Newton solve of the toes control's three rotates
   (`_fit_toes`), the Jacobian measured by small probes. The toes control's rest frame is
   its FK control's, not the toes joint's, so no fixed relation holds (the rest pose read
   177 deg off with the wrist's relation). Its rotate turns the IK toes joint by the same
   angle (1:1), so the solve converges in a few steps - after a units fix (radians per
   degree; the first version took 1/57 of each step).

**Spine** (`fkikspine`). To IK: the blended joints Spine1..4 are FIT to the shown FK joints,
places and turns (`fkik.joint_residual`), with a damped Gauss-Newton step per frame
(`fkik.gauss_newton_step`). The unknowns are the CVs' translates and the rotates of the two
end controls (`IKSpine1_M`, `IKSpine3_M`), fifteen plus six numbers. The turn of the top
(IKX4) carries Spine5 through the FK chain - a position-only fit left Spine5 6 to 9 cm off
(measured) - so the orientation is in the fit. The sensitivities are measured by probes
(`FIT_STEP`), the controls' keys are cut first and written back as keys on the keyed frames.
To FK: the FK controls take the shown joints (`fkik.fk_locals`, as the limbs).

## Measured (verify scripts, mayapy standalone, the shipped rigs)

- `verify_fkik_legs.py`: **12/12 on Manny and on Creep**. At the keys the hip, knee, ankle and
  toes stand where the FK leg stood to **0.0000 cm and 0.0000 deg**; IK -> FK returns the leg
  to 0.0000; a range keeps the leg.
- `verify_fkik_spine.py`: **11/11 on Manny and on Creep**. FK -> IK keeps Spine1..5 to
  **0.009 cm and 0.01 deg** at the keys (Spine5 0.004 cm); IK -> FK to 0.001 cm; a range to
  0.009 cm.
- `tests/test_scenesetup_legs_spine.py` (22 new), the existing `fkik`, Connections and ikmatch
  tests (161, updated for the leg and spine rows); the whole suite 5843 green.
- The arm switch is unchanged: the same synthetic probe on HEAD and on the working tree gives
  **0.0431 cm** at the keys, the same forearm roll (31.5 deg).

## Limits, stated rather than hidden

- **The knee's roll is not held.** Positions and bend are exact at the keys, but the IK knee's
  joint frame rolls about **84 deg** against the FK knee's when the knee is bent (world X
  axis, not the bone's: it is the IK knee's own frame; the hip swing is not the cause - it is
  84 deg with the hip at 0). Moving the pole out of the bend plane to fix it breaks the
  places (tried 2026-10-10: the fit traded 23 cm of knee for the turn). The message says it.
  Visible on the skin? Not checked - the animator's eye decides.
- **The spine's turns are fitted for the four blended joints only.** The fit is within
  0.01 deg at the keys on the synthetic poses; a clip whose spine twists about its own bones
  is not in these verifies.
- **Keys are the source's keys** (2026-10-08): between them each chain interpolates its own
  way, as for the arms.
- **Not run in the animator's Maya.** Live checks are theirs (CLAUDE.md, 2026-10-09). The
  shipped rigs were verified standalone; a live press is the next check.
- Orc D's leg and spine were not run (same AS build family, not verified here).

## Files

- `SkeldarAnim/maya_scenesetup/fkik.py`: the leg (`kind`, `Tip`, the toes fit, the pole on the
  bend side, the pole after the IK control), the Gauss-Newton helpers and `joint_residual`
  (shared with the spine), the words per kind (`ROLL_WORDS`).
- `SkeldarAnim/maya_scenesetup/fkikspine.py` (new): the spine.
- `SkeldarAnim/maya_scenesetup/connections.py`: `switch_limb`, `switch_spine`, the leg row and
  the spine row, their lighting and the header's mixed notes.
- `tests/test_scenesetup_connections.py`: the card's layout counts (two rows of arms and legs,
  the spine's row, nine segment rows).
- `tests/test_scenesetup_legs_spine.py` (new).
- `docs/superpowers/plans/verify_fkik_legs.py`, `verify_fkik_spine.py` (new).
