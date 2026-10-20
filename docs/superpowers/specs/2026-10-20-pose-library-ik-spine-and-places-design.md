# The Pose Library: a pose lands on the same rig as it was made (2026-10-20)

The animator, with two scene tabs open in a Maya on port 7003: «Я делаю позу через нашу библиотеку
поз в первом кадре в сцене Idle_Dagger, переношу её на персонажа во вкладке Hold_Combo тоже в 1
кадр и в итоге позы не совпадают. Нужно понять, почему так происходит, и устранить проблему.»

Both characters are Manny_Rig (Idle_Dagger's in a nested namespace pasted from another tab,
`tab_AS_Dagger_Attack_Cbm_L_L_1p_0007_fast_0002:Manny_Rig1`). Nothing in the animator's scene was
changed: the scene was read over the port, the press reproduced in mayapy standalone on the tab's
own file (`SkeldarStash/Hold_Combo_P1 (2).ma`) with the tab's FK/IK state set.

## What was measured

The card applied at frame 0 (relative to each character's root):

- the target's spine SHOWN IN IK (`FKIKSpine_M` 10): the library posed its FK half only
  (`rigsolve`: «the spine shows IK - its FK took the pose») - spine_01..03 14-32 deg off and
  everything above them 6 cm off;
- the target's right leg in IK with `IKLeg_R.stretchy` 10: the IK half was left unposed
  («leg_r: the IK half is not posed - IKLeg_R.stretchy off the default») - ball_r 177 deg off;
- the card's bone PLACES were never carried: «every bone keeps the target's own length». Both takes
  come from twin retargets that slide FK controls: Idle_Dagger's left clavicle 15.8 cm, Hold_Combo's
  7.8 cm, and Hold_Combo's spine 5 cm longer (`FKSpine1..4_M` 0.6-2.0 cm, the IK spline stretched).
  With the spine and the leg fixed, the chest still stood 9 cm off;
- the newest card, `Dagger/Pose`, was saved from a bare Manny UE5 skeleton (`tab_Idle_Dagger:root`,
  13:52, gone from the scene since); the cards before it (`L4`, `L3`, `I2`, `Dagger_Idle_1P`) are rig
  cards. A skeleton card holds no drive, so on a rig the forearms', calves' and twist bones' roll comes
  out 7-20 deg off. A card saved from the rig now (read-only over the port) is a rig card.

## What changed

1. **The IK spine takes the pose** (`rigsolve._Job._ik_spine`): the spine shown in IK (any of it)
   with a bone the spline carries posed (spine_01..04), the spline's controls are fitted as
   Connections' FK -> IK switch fits a frame - `fkikspine.fit_pose`, the switch's one-frame fit
   pulled out of `_fit_ik` (`_fit_frame`, its behaviour unchanged): the IK root on the deformation
   root's target, IKXSpine1..4 on the deformation joints'. After RootX_M (the IK root rides it),
   before the level walk (Spine5 and all above hang below the deformation Spine4). Its channels are
   recorded in the solve's session first (put back, keyed with the rest); `controls_for` names the IK
   spine's controls. The FK half is posed as before, so a switch shows the same pose.
   The spline cannot take an FK spine's twist vertebra by vertebra: the root and the top land exact,
   the middle as near as the fit gets (the animator's take: 3.5, 7, 17.4 deg at spine_01..03; the
   turns weighted ten times changed nothing - a hard limit, AdvancedSkeleton's own switch: «Target
   might not fully Align»). Said: «the IK spine is a spline and cannot hold the pose's twist: 17.4 deg
   at spine_03 (shown in FK it lands)».
2. **`stretchy` no longer keeps an IK half unposed** (`rigsolve.IK_GUARD` = `antiPop` only): the end
   goes where the FK chain the pose turned puts it, within its reach, and a stretchy chain stretches
   only past it. `antiPop`, the pole's `follow*` and `lock` still keep it, named.
3. **Onto the same body the card's places come too** (`posemath.Transfer(places=True)`, used by
   `apply._plan` only): onto a `twin` a member takes the card's local translation on its parent,
   `local_translation(rigid(P[s]) . rigid(P[s_parent])^-1) . W[parent]`, named in `placed` (the
   pelvis keeps its own rule). Not for a rig whose game bones take orientation only (the Creep, the
   Orc D: `maya_asretarget.rotation_mode`), and not mirrored (`posemath.mirror` reflects turns and
   the pelvis, not places). Animations keep the old rule.
   - on a rig (`rigsolve`, `placed=`) a placed member's FK control is MOVED after its turn until its
     GAME bone stands on its target's place (`_place`, measured on the bone: a target's model of
     the place wanders - Manny_Rig's game calf, point-constrained with an offset, 0.06 cm from pose
     to pose - and a move aimed at the model put a twin's calf that far off and keyed a translate
     for it). Within `PLACE_TOL` (0.005 cm) nothing moves, no translate key; the neck's in-between
     follows by the bias's share, so a move is scaled by the response measured; a half shown in IK
     is placed by the IK (`_shows_fk`); the measure (`_rows`) reads the placed members' places;
   - on a skeleton (`skelsolve`, `placed=`) a placed member's translate is written when it differs
     from the joint's own by more than `PLACE_TOL`.

## Proof

- `verify_poselib_solve.py` - new phases `ik-spine` (the target as Hold_Combo stood) and `places`
  (Idle_Dagger's and Hold_Combo's slides, through `apply.apply`): the IK spine's top and every other
  member to 0.0001 deg / 0.0001 cm, the spine's middle 0.03 / 0.94 / 1.80 deg on the synthetic pose,
  the stretchy IK leg 0.0001 deg, switched to FK the same pose 0.0001; every member's place and turn
  on the rig and on the skeleton to 0.0001 cm, mirrored the target's slides kept. Before the change
  `ik-spine` failed 5 of 9 (the spine 55 deg, the leg 64 deg). All phases: 122/122.
- The animator's own case (their card, their target file, their FK/IK state): 78 of 79 members off
  (6-9 cm, up to 177 deg) became 8: the spine's middle (the spline's twist, said) and the right calf's
  roll (an IK knee is a hinge, said). With the `Dagger/Pose` skeleton card also the forearms' and
  the left calf's roll (no drive in a skeleton card).
- `tests/test_poselib_posemath.Places`.

## Not built

- Places for animation cards (`animapply`): the plug set is fixed by the first frame's dry solve,
  and a translate keyed only where the first frame needed it would leave the others unkeyed.
- A skeleton card's roll onto a rig: the four unrolled limb bones take a skeleton bone as their drive;
  a card from a rig's game skeleton saved as a skeleton loses the twist network's roll.
- The IK half's start (`IKXHip`/`IKXShoulder` translate) and `Lenght1/2` for a slid FK limb shown in
  IK (`maya_ikmatch` does it after a retarget): the measure says what is left.
