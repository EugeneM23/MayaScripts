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
- `docs/superpowers/plans/verify_fkik_spine_take.py` (the addendum's).

## Addendum, the same day: the spine switch moved the legs

The animator, after the push: «При переключении с ФК на ИК спины у нас ломается анимация. При
использовании стандартного переключения в advanced skeleton все работает корректно».

**Measured** on `LongSword_Attack_Right_Heavy_3P` retargeted onto Manny_Rig (mayapy, every
frame): the spine stood where the FK spine stood, but the **root moved 0.39 cm and 1.16 deg, the
feet 2 cm, on every frame**, the skin up to 2.1 cm. `Root_M` is blended by the SPINE blend - it
reads `FKXRoot_M` and `IKXRoot_M` - and `IKXRoot_M` follows `IKSpine1_M`: the spline's hip control
IS the IK root. The fit turned and moved `IKSpine1_M` to place the spine and took the root, the
pelvis and both legs with it. `verify_fkik_spine.py` measured Spine1..5 alone and passed.

**AdvancedSkeleton's own switch** (`asAlignFKIK`, read in `AdvancedSkeleton.mel` 6.797): FK2IK on
a spline puts `IKSpine1_M` on the root exactly ("also IKSpine1_M to be oriented, since it affect
legs") and the other IK controls on a curve rebuilt through the chain, and prints "Target might
not fully Align". Run on the same take in mayapy (every 6th frame): **root and legs 0.0000 cm,
the spine 0.42-0.81 cm and 3.3-5.3 deg off**. IK2FK sets `.t` and `.r` of every FK control of the
chain, `FKRoot_M` included, from the IKX joints, and its bake keys both.

**The fix** (`fkikspine`):

1. The IK root is in the fit: `IKXRoot_M` is fitted to the shown root with IKX1..4, its residual
   counted `ROOT_WEIGHT` (100) times - where the spline cannot reach the FK spine (the Creep at
   one frame), the spine gives, never the root. Unweighted, the Creep's root gave 0.017 cm and
   0.094 deg there.
2. To FK, the FK spine controls take places AND turns, as AS's switch and our limbs: the IK
   spine stretches (`IKSpine3_M.stretchy` 10). Turns alone, after the hip control was moved 3 cm
   in IK, left every spine joint 0.30 cm off (the same 0.30 on all five: the FK spine's base).
3. To FK, when the IK root stands off the FK root (the hip moved in IK), `FKRoot_M` is put on it
   first (`_root_to_fk`); roots within 0.005 cm / 0.01 deg get no FK root keys.
4. Spine5's FK parent hangs under the DEFORM Spine4 (`FKParentConstraintToSpine4_M`): its piece of
   the FK chain is measured against the joint the spine shows (0.0000 against the deform Spine4;
   against FKX4 in IK 0.0045 cm / 0.014 deg on an unedited take, more on an edited one).
5. The status line says how far the deform root moved: «the root and legs kept to 0.0000 cm», or
   «the root MOVED ... - the legs with it».
6. The mid control `IKSpine2_M`'s rotates join the fit. With the root held, `IKSpine1_M`'s turn
   (which carries the root 1:1) is no longer free, and the spine lost its start twist: on the Orc
   D's strong synthetic bend Spine2 rolled 2.6 deg off and the top 1.6 deg / 0.32 cm. `IKSpine2_M`
   twists the middle and leaves the root alone (measured: rotateY +10 turns IKX1..3 by 5, 10, 5
   deg, the root 0); with it the same pose lands within 0.41 deg of roll, the top 0.30 deg /
   0.012 cm - closer than the root-free first build (0.46 deg, 0.086 cm), and the root held.

**Measured after** - `verify_fkik_spine_take.py` (mayapy, the take retargeted through the button,
the switch pressed through Connections, the game skeleton and the skinned meshes' vertices on
every frame), Manny_Rig, Creep_Rig, Orc_D_Rig:

- keyed on every frame, **36/36**: FK -> IK the root, the pelvis and both legs **0.0000 cm,
  0.0000 deg on every frame** on all three; the spine 0.013 cm / 0.041 deg (Manny), 0.011 / 0.033
  (Orc D), 0.037 cm / 0.513 deg at one frame (the Creep - the spline's twist: its joints roll as
  the controls share it, the FK spine does not); the skin's worst vertex 0.124 / 0.041 / 0.234
  cm. IK -> FK back to the take; IK -> FK after the hip control moved 3 cm: the FK root follows,
  the root and the legs stay where IK put them (0.0000), the spine 0.0000;
- keyed every 8 frames, **45/45**: the same at the keys; between them each chain interpolates its
  own way, the spine up to 0.12 cm / 0.48 deg (the keys-only cost, 2026-10-08); the root and the
  legs 0.0000 on every frame.
- `verify_fkik_spine.py` (synthetic, now gating the root both ways and over a range) **14/14** on
  Manny, Creep and Orc D; `verify_fkik_legs.py` 12/12; the unit suite green.

AS's switch and ours now hold the root alike; ours keeps the spine 30-60 times closer.
