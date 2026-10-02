# The IK limbs follow the FK limbs, stretch included (2026-10-02)

## The ask

> «При переносе анимации на риг через нашу систему если у анимации и рига не совпадают пропорции мы
> можем перенести с растяжением костей и тут все хорошо работает, НО есть проблема с IK контролами
> рига если мы перенесли анимацию с растяжением костей то кости при переключении контролов на IK не
> растянулись они остались прежнего размера. Это не верно анимация IK должна соответствовать анимации
> FK это обязательное условие. Нужно разобраться с сжатием и растяжением костей и исправить перенос»

## Measured first

`LongSword_Attack_Right_Heavy_3P` (UE) and `Sweep Fall` (Mixamo), the Retarget button in Squash &
stretch, mayapy standalone; each limb's game bones with the blend at 0 against the blend at 10:

| rig, clip | IK against FK |
|---|---|
| Creep_Rig, Heavy | elbows **11.5 cm** (the arms are -16.7 %), hands 0.000 |
| Orc_D_Rig, Heavy | shoulders **0.91**, elbows **3.4**, balls **0.55**, knees 0.1 |
| Manny_Rig, Sweep Fall | shoulders **4.1** (the clavicle), hips **3.0-3.2**, the foot **2.14 cm longer** in FK |
| Manny_Rig, Heavy (a twin) | elbows **11.4 / 20.0**, knees **9.6 / 17.8 cm** - the IK poles rode the CLIP's upper bones |

What AdvancedSkeleton's IK limb is (read off the rig's network and the vendor's MEL):

- `IKX<mid>.tx = |input2X| * Lenght1 * stretchFactor`, `IKX<end>.tx` the same with `Lenght2` - the
  multiplyDivide on `IK<Limb>.Lenght1`'s output holds the rest length (negative on the left). With
  `stretchy` 0 the factor is 1: the measure runs through an animCurveUU flat at the rest sum below it.
- The chain's root joint `IKX<start>` stands at `t = 0` under `IKXOffset<start>` (the clavicle's, or
  the pelvis's, rest offset) and its translate is free; nothing in the rig follows the FK start
  control's translation.
- The foot: `IKXAnkle` is aimed by an SC handle (`IKAnkleHandle`, under `RollToes`) at the ball;
  `IKXToes.t` is the ball's offset in the ankle; the toe control pivots at the rest ball
  (`IKOffsetToes`). Moving `IKXToes.t` alone re-aims the ankle (6.8 deg for a 2 cm sideways move).
- The vendor's own FK→IK switch (`asAlignFKIK`) sets `Lenght1/2` from the FK lengths (with `stretchy`
  10) - AdvancedSkeleton's own answer to the lengths. It does not move the root.

## The design

1. **The IK ends and poles follow the rig's own FK in every version** (`drive_plan`): the hand on
   `FKXWrist`, the foot on `FKXAnkle`, the toes on `FKXToes`, the pole on the FK plane - the rule the
   rotation-only rigs and the PlayerMale had. The twin no longer rides the clip's hands and upper bones
   (the 20 cm above), and Manny's Rotations no longer stands its IK feet on the clip's footprints with
   FK somewhere else. One rule: what IK shows is what FK shows.
2. **After the bake, the IK chain takes the FK chain's shape** (`maya_ikmatch.carry`), whenever FK took
   position (the twin's exact path, squash & stretch): per limb, over the clip's span, sampled once -
   `IKX<start>.translate` (the FK start joint in `IKXOffset<start>`), `Lenght1/2` (the FK segment
   over `|input2X|` times the chain's world scale), and on a leg the foot: `IKXToes.translate` (the FK
   ball in the FK ankle), the ankle's SC handle and the toe control's offset each moved onto the FK
   ball. Constant series become plain values, a rest series writes nothing. `stretchy` stays 0.
3. **Every reset puts them back** (`maya_ikmatch.restore`, from both retarget modules'
   `reset_build_pose`): curves deleted, `Lenght` at its default, every moved translate at its own
   value, kept on the node the first time it moved (`skeldarIkRest`).
4. **The Connections FK / IK switch carries the same** (`fkik`, arms): to IK writes `Lenght1/2` and
   `IKX<start>.translate` from the shown chain; `stretchy` joins the solve attributes reset over a whole
   take (refused inside a range).
5. The messages say it: the question's and the connect's «a limb in IK keeps its own lengths» are gone;
   the bake names the IK lengths carried.

## Not done, measured

- **An IK knee or elbow is a hinge**: a clip's calf or forearm rolled about its own bone is not an IK
  pose. Measured the same before and after (Creep, Heavy: the calf 30-55 deg, the forearm 33 deg about
  their own axes, every position and direction exact) - in the rotation version too. AdvancedSkeleton's
  own switch has the limit (`fkik` said so on 2026-09-30).
- The pole rig's precision: elbows and knees 0.03-0.05 cm, as before.
- The IK spine is driven by no version.
- The vendor's own Switch FK/IK button: it re-derives `Lenght1/2` (and sets `stretchy` 10) and does not
  move the root.

## Proof

`docs/superpowers/plans/verify_ik_follows_fk.py` **16/16 standalone** (each limb's game bones with the blend
at 0 and at 10, 13 frames): the control with the carry off - elbows 13.99 cm; the Creep 0.0501 cm,
the Orc D 0.0495, Manny under Mixamo 0.0551, the twin 0.0370 (directions <= 0.105 deg); Rotations after
a stretch - every carried channel at rest to 1.8e-15; the Connections switch on a stretched arm 0.019
cm, both ways and over a range; Manny Rotations 0.055. `verify_retarget_modes.py` all phases (b4 and
e rewritten for the rule), `verify_rig_pipeline` 30/30, `verify_many_rigs` 32/32,
`verify_creep_rig_asset` 16/16, `verify_orc_d_rig_asset` 22/22, `verify_skeleton_conventions`
122/122, `verify_fkik_switch` 63/63, `verify_weapon_space` 11/11, `verify_character_groups`
146/146, `verify_clip_labels` 17/17, `verify_import_sources` 27/27; 3822 unit tests
(`tests/test_ikmatch.py` new).
