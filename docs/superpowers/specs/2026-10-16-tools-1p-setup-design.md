# Tools > 1P Setup: a 3P take split for first person (2026-10-16)

The animator: «Необходимо реализовать новый инструмент во вкладке tools который будет называться
1P Setup ... мы выделяем любую часть рига ... 1 - переключить геометрию на 1P ... 2 - для
контроллера spine3 создать knot ... 3 - перенести на слой 3P_Lower_Body всю анимацию lower body
... 4 - анимацию изменения позиции с knot ... в слой lower body, а вращение ... в слой
3P_Upper_Body ... анимации всех контроллеров из верхней части ... в 3P_Upper_Body ... 5 -
настроить камеру по нашим правилам, камеру поместим в парент knot».

Asked: Spine1-2 go to **Lower**; the camera stands in the knot **with no animation of its own**;
a rig with no 1P switch is **done without it, said**; a second press on a set-up rig is
**refused**.

## What one press does (one undo chunk)

1. **Which rig**: the selection's (`maya_rigs.current_rig`), else the only one.
2. **Refusals first, nothing changed**: no rig / several; a layer of ours for this rig already
   stands; no `FKSpine3_M`; the spine in IK (`FKIKSpine_M.FKIKBlend` above 0 on any frame or
   keyed); a control Layer would refuse (constrained by the retarget, already on layers, ...);
   a knot refusal on `FKSpine3_M`.
3. **1P geometry**: `Main.view` = 1 where the rig has the switch (Manny, Orc D); else said.
4. **Knot** on `FKSpine3_M` over the whole take (Tools > Knot, unchanged).
5. **Layers** (Tools > Layer, unchanged, the whole take): the lower controls plus the knot onto a
   new additive layer `_3P_Lower_Body`, the upper controls onto `_3P_Upper_Body`. The base keeps
   the pose of the first frame. Then the knot's rotate curves move from Lower to Upper (exact:
   both layers add by component). Maya will not start a node name with a digit, hence the `_`.
   Both layers are marked `skeldarFirstPerson` = the rig's namespace.
   - **Lower**: `Main`, `RootX_M`, `FKRoot_M`, `HipSwinger_M`, `FKSpine1_M`, `FKSpine2_M`, the IK
     spine controls, and every leg control (Hip / Knee / Ankle / Toes / Leg / Heel / Foot in the
     name).
   - **Upper**: every other control of the rig's `ControlSet` but `FKSpine3_M` (the knot drives it).
   - Only controls something animates go onto a layer; still ones are left.
   - Mute both and the rig stands in the first frame's pose; Lower alone gives the legs and hips
     with the chest following the body's travel at the first frame's turn (a stable top); both
     give the 3P take exactly.
6. **Camera**: Camera Setup on the rig's `camera_root` (the game's lens, the camera drives the
   bone), then the camera's keys cut and it is parented under the knot, standing where it stood
   at the take's first frame. It has no animation of its own: it rides the knot.

Line: «1P Setup on Manny_Rig: 1P mesh on | FKSpine3_M on a knot | _3P_Lower_Body: 22 controls +
the knot's travel | _3P_Upper_Body: 48 controls + the knot's turn | camera in the knot».

## Where

`SkeldarAnim/maya_tools/firstperson.py` (the pure split and line at the top; the press below);
`layerbake.bake(..., name=)`; a fourth Tools subsection **1P** with the row **1P Setup**; hotkey
row `tools.fp_setup`.

## Proof

Unit tests for the split and the refusals on a fake; `docs/superpowers/plans/verify_1p_setup.py`
in mayapy standalone on a Manny rig retargeted with a UE clip: the rig as before at every frame
with both layers on, the first frame's pose with both muted, Lower alone: legs and pelvis as
before and the chest's world turn constant, the knot's turn only on Upper, `Main.view` 1, the
camera a child of the knot with no keys and `camera_root` following it, one undo, a second press
refused.
