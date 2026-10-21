# Pose Library: bones first, the same on 3P and 1P, the upper body stabilized (2026-10-21)

## The ask

The animator, after a day of 1P transfers (43ab1fa, 152124b):

> «Нам нужно пересмотреть всю нашу систему переноса анимаций и поз, взаимодействие плагина с 1P
> модом рига. Суть такая что мы не должны опираться на анимацию рига когда сохраняем позу или
> анимацию ... спуститься на уровень костной анимации ... Если я сохранил позу то не важно в каком
> режиме я ее загружаю в 3p или 1p режиме для рига поза должна быть одинаковой. Тоже правило работает
> и для анимаций. ... 1 - когда риг в [1P] и я загружаю анимацию на риг как upper body то анимация
> загружается не верно на нее начинает действовать нижняя часть. 2 - наша система не распознает
> контроллер chest (который создается при переходе в режим 1p) как часть нашего рига. Если я
> сохранил анимацию верхней части тела которая стабилизирована то даже на риге с анимацией в которой
> есть провороты она должна остаться стабилизированой. Переносы должны быть точными.»

Asked once: when should the chest load stabilized - «Всегда»: whenever a card poses the chest
without the spine under it, with the «1P upper body» option or not.

## Measured first (mayapy standalone, the shipped Manny_Rig)

A: Manny_Rig + `AS_Dg_Atk_Cmb_R_Lt_HoleCombo` (the Retarget button), then Tools > 1P Setup (Upper
muted: the chest stabilized); an animation card saved off A, 0-40. B: a second Manny_Rig +
`AS_Dg_Atk_Cmb_L_Lt_2_3P` (a combo whose torso twists).

- **The card holds bones** - every bone's world on every frame - as the animator thought. In the
  card the chest (spine_03) against the root is still to 0.000 deg over the take while it turns
  109.4 deg against its own spine_02: that is the stabilization, in bone data.
- **The target's mode already changes nothing**: the card onto B in 3P and onto B after its own 1P
  Setup lands the same bones to 0.0006 cm (1P upper body on) and 0.0065 cm / 0.0001 deg (off).
- **Problem 1 is the rule for the chest**: under 1P upper body the chest takes its turn against
  the target's spine_02 (`posemath.Transfer`: each member against its nearest paired ancestor), so
  B's lower spine twists come up into the whole upper body - B's chest against its root 78.09 deg
  off the card's, turning 112.74 deg over the take, in 3P and in 1P alike; against spine_02 it was
  the card's to 0.00 deg. `verify_poselib_upper_1p.py` gated exactly that rule («every member (the
  chest too) on its parent as the card's»).
- **Problem 2 is the classification**: `scene.is_body` calls 1P Setup's `Chest_1P_ctrl` an OBJECT
  (a Tools knot is "an object beside" the character). Saved alone it makes an objects card («1
  object») of its raw world-space curves, no bones; saved with the shoulders and the head the card's
  members are the arms and the head - spine_03 is no member - and the chest's raw curves ride along
  as an object.
- The chest's PLACE cannot come from the card: HoleCombo carries its 2.16 m of travel in the pelvis
  with the root standing still, B carries its travel in the root - the card's chest against the root
  is up to 216.5 cm from B's. The stabilization is the TURN, as 1P Setup's own (the knot's turn on
  Upper, its travel on Lower).
- A prototype (a monkeypatch: the chest's paired ancestor replaced by the root frame) on the same
  scene: B's chest against its root equal to the card's to 0.0000 deg and turning 0.0000 deg over
  the take, the upper body on the chest as the card's 0.0010 cm / 0.0001 deg, the lower body
  untouched (0.00000), 3P against 1P 0.0006 cm.

## The design

### 1. The torso keeps the card's own relations (`posemath.Transfer`)

A member bone of the TORSO - the target bone playing `pelvis` or a `spine_*` (by its canonical
name, else its leaf) - takes its turn against the nearest torso bone BELOW it that is also a member
(its nearest member ancestor among the pelvis and the spine), else against the ROOT FRAME (the
target's root, or a rootless target's ground). Its place is unchanged: its own local translation on
its parent, the card's on a twin (`places`), the pelvis's offset from the root frame.

- A full card: every torso bone's member ancestor is its paired ancestor - nothing changes.
- An upper-body card (the chest and above - saved so in 1P, or cut by «1P upper body»): the chest's
  turn is the card's against the root - stabilized whatever the target's pelvis and lower spine do
  (Unreal's Layered blend per bone with mesh-space rotation) - the chest standing on the target's
  own spine_02; everything above it on the chest as the card's.
- A card with the pelvis and the chest but not spine_01/02 (the animator's `DG_Idle_1P`): the chest
  against the card's pelvis, so the card's torso whatever the target's spine between.
- Limbs, the neck, the head and the fingers keep the old rule: a hand card still lands on the arm
  as it stands.
- The target's mode never enters: the solve writes the chest through `Chest_1P_ctrl` in 1P
  (`rigsolve`'s knot redirect, 152124b) and through FKSpine3_M in 3P - the same bones.

### 2. The camera rides the chest in an upper-body card (`upper.anchors_for`)

`camera_root` is anchored on the chest (its turn AND place against it, `Transfer`'s `anchors`)
whenever the card is an upper-body card - the chest a member, no torso bone below it - not only
when the option cut it. Derived from the card's members at every press (`apply._plan`,
`animapply._Target`), so a card saved before this needs nothing. Elsewhere the camera stays on the
root as it was.

### 3. Our nodes on the rig are the rig (`scene`)

What the animator selects is mapped to what it STANDS FOR before anything is classified
(`scene.stand_in`):

- a Tools knot of ours (its top node, or a double knot's / an aim's inner node, or a waiting pivot
  or its space) stands for the OBJECT it drives (`skeldarKnotSource`, followed down a knot on a
  knot) - `Chest_1P_ctrl` for FKSpine3_M, so spine_03; a knot on FKWrist_R for hand_r; an across
  knot riding a prop for the prop (an object, as before); a snapshot drives nothing and stays itself;
- the Camera Setup control (and an older camera of ours) names the camera bones, `camera_root`
  and `camera_bone` - kind `camera` (was an accessory naming nothing), so a card saved with the
  camera control selected carries the camera.

So `Chest_1P_ctrl` alone saves a character card of spine_03 (its riders), never «1 object»; with the
shoulders and the head, spine_03 is a member and no object is stored. Every caller of
`scene.resolve` / `split` / `characters` (Save, Apply, Selected only, the objects pairing, the save
panel's label and chips, Ragdoll) gets it for free.

### 4. Selected only reaches the chest (`apply.selected_nodes`)

The set Selected only keeps is the selection plus, for each selected control a plain knot drives
(`rigsolve.knot_driver`), the knot - the solve writes the knot in its place, and FKSpine3_M selected
in 1P kept nothing - and, for each selected knot, the object it stands for.

### Not changed

The card's format (it holds every bone's world, as before); `upper.restrict` (the option still cuts
a full card to the chest and above, the camera and the weapon bones with it); the solve; the keys and
their layer; 1P Setup itself (its camera keeps its own motion, the animator's «Делай без слоя»).

## Proof

- unit tests: the torso rule (an upper-body card's chest against the root, a twisted target lower
  spine reaching nothing above, a full card unchanged, the pelvis-and-chest card, a hand card
  unchanged, a rootless target), `anchors_for`, `stand_in` and the camera kind, `selected_nodes`;
- `verify_poselib_1p_transfer.py`, standalone: a stabilized 1P card onto a twisting target in 3P
  and in 1P (the chest against the root as the card's, still over the take; the upper body on the
  chest; the lower body untouched; 3P = 1P), the same full card (unchanged, 3P = 1P), `Chest_1P_ctrl`
  saved alone and with the shoulders, Selected only with FKSpine3_M in 1P, the camera control;
- `verify_poselib_upper_1p.py` rewritten for the new rule; `verify_poselib_apply`, `_solve`,
  `_anim`, `verify_camera_weapon_bones` green again;
- the same scenario in the Maya the animator opened on port 7003.

## Addendum: what the build found

**1P Setup put part of the lower body on the upper layer** (`firstperson.is_lower`). The verify's
first run moved the lower body 155-175 cm under «1P upper body»: the card saved off A with the
upper-body controls selected named the pelvis and spine_01/02. 1P Setup's split reads names, and
AdvancedSkeleton's extra groups (`FKExtraRoot_M`, `FKExtraSpine1_M`, `RootExtraX_M`) and the IK
spine's controls (`IKhybridSpine*`, `IKcvSpine*`, `IKExtraSpine*`) were read as upper. An extra
group is now read as the control it carries (`EXTRA`), and the IK spine's controls are lower
(`LOWER_PREFIXES`). The verify selects the controls DRAWN in the upper display layer.

**An animation paste left a placed bone's translate unkeyed on the frames it already stood right.**
`Combo_3.anim` onto the verify's 1P rig: every frame exact but 9-16, where clavicle_r went up to
3.1 cm off its card's place on spine_05 (0.56 cm at the verify's frame 12), the same on the
committed build. The rig solve skips a placed member within `PLACE_TOL` (no translate key for a
bone the turns put there - right for a pose). In a walk, a frame that writes no value takes no key,
and the curve carries the keys either side across it: the card's clavicle stood still over 9-16
while the cut curve interpolated from the key at 8 to the key at 17. Fixed twice over:

- the solves in a walk are `steady` (`rigsolve.Solver(steady=True)`, `skelsolve.solve(steady=True)`):
  a placed member on its place still writes its translate, and so does 1P Setup's chest knot;
- `animapply._Target.key` keys every plug the dry solve planned on every frame, a plug this frame's
  solve left where it stands at what it shows.

A pose press is unchanged.

**A card with a gap in its spine** (the same evening, after the push: «записали анимацию с рига
который был в 1p моде и ставим ее без галочки ... с отклонениями ... в груди и голове»). The
animator's scene: a clean Manny_Rig and a Manny_Rig1 in 1P. Their cards off Manny_Rig1 held 75
bones: the pelvis, the chest, the legs, the arms, the head, but not spine_01/02/04/05 (FKSpine1/2
hidden in 1P Setup's lower layer). With the option off, the clean rig's spine_04/05 stayed at rest
between the card's chest and its head: the head and the arms 15.7 deg off. With the option on,
`restrict` takes every bone above the chest, so it worked. `posemath.with_torso` now poses, at every
press, a torso bone the members leave out between a posed bone and a posed torso bone under it -
the card holds it. Measured on a copy of their scene: both cards to 0.0002 deg.

## Not built

A stabilized chest's PLACE (the place is the target's); 1P Setup's world-constant stabilization of a
take whose root turns (relative to the root it then turns against the character); old cards that
stored `Chest_1P_ctrl` as an object get nothing from that object (a knot is body now, never an
object to find).
