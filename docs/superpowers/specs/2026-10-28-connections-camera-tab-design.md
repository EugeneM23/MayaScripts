# Connections: a Camera tab - parents, Position only, Aim Mode (2026-10-28)

The animator: «Во вкладке конекшен нужно добавить раздел для камер. В разделе для камеры нужно
реализовать такой же aim как для оружия, и возможность переподвязывания камеры к разным
контроллерам. Подвязывание должно быть с опцией которая может привязать только позицию как поинт
констрейн».

Asked: the parents are a **fixed list** - Main / Root / Chest / World as today plus **Head**; with
Position only the camera's rotation lives **relative to Main**. The rest was proposed and approved
as written here.

## The card

`[Body | Weapon | Camera]` (`TABS`, `TAB_COLUMN["camera"] = "skeldarConnectionsCameraTab"`, the
pick remembered as before). Camera:

- caption «Parent»: segments **Main | Root | Chest | Head | World** (lit on the current parent),
  a check box **Position only**, a small **Apply**;
- caption «Aim»: **Aim Mode** (primary) + **Default** (secondary), as the Weapon tab's;
- the subtitle while the Camera tab shows: `Camera: Head (position) - Aim Mode`, or
  `no camera - Characters > Camera Setup first`.

The camera acted on is the active rig's (`camera.resolve_bone` over the rig's `camera_root`). No
Camera Setup: every press refuses with `no camera with a control on camera_root - press Camera
Setup first`, nothing changed. Hotkey rows `connections.camera_aim` / `connections.camera_default`.

## Parents (`camera.set_parent(bone, choice, position_only=False)`)

`PARENTS` becomes Main / Root / Chest / Head / World. Head is the rig's `FKHead_M`
(`maya_rigs.node(rig, "FKHead_M")`); missing: `Head: no FKHead_M on <rig>`. Chest still needs
1P Setup, Main / Root / Head a rig.

- **Full** (Position only off): as today - `Camera_ctrl` under the chosen node, its world track
  kept on every frame (`move_control` → `reparent._rebake`).
- **Position only**: a transform `<ns>:Camera_follow` (marked `skeldarCameraFollow`) under the
  rig's Main at identity rotation, `pointConstraint` (no offset) to the chosen node, and
  `Camera_ctrl` moved into it with its world track kept. The camera rides the node's position; its
  rotation is relative to Main. Main and World ignore the option (Main already is the rotation
  space; World has no position to follow) - said in the line.
- Leaving a Position only parent (any next choice, `go_home`, teardown): the control moved out
  with its motion kept first, then the follow group and its constraint deleted.
- On the control: `skeldarCameraParent` = the choice, `skeldarCameraPosition` = 1 / 0 (locked
  like the parent marker). `parent_choice` reads both.
- One undo chunk a press, autoKey off (`knots._press`). Tools > 1P's four buttons keep calling
  `set_parent` (full).

## Aim Mode (`maya_scenesetup/cameraaim.py`)

`weaponaim`'s road on `Camera_ctrl` (the keyed node; the camera under it stays locked):

- refused, nothing changed: no camera control, already aimed, a rotate channel locked / layered /
  driven by anything but its own curves;
- the vectors are the camera's, not a model's extents: in the control's frame the view axis is
  the camera's -Z through `AXIS_OFFSET` and the up its +Y the same way (`camera_vectors`, pure);
  target `AIM_DISTANCE` (300 cm) along the view, up `UP_DISTANCE` (50 cm) along the camera's up;
- the group `Camera_ctrl_aim` (marked `skeldarCameraAim` = the control's UUID, the vectors kept)
  repeats the control's parent (Main, Root_ctrl, the chest, `FKHead_M`, `Camera_follow`, the
  character group); diamonds `Camera_ctrl_aimTarget` / `Camera_ctrl_aimUp`, rotate and scale
  locked;
- keyed on the control's OWN key frames (`fkik.own_keys`, their tangents; none: placed at the
  current frame), in the group's parent space; the control's rotate keys cut and `aimConstraint`
  (no offset, worldUpType object) put on - on every keyed frame the camera looks where it looked;
- **Default**: the control's rotation keyed back on the keys of the controllers and of its
  translate, then `_fill_between` (frames turned more than 0.1 deg off the aim), the constraint and
  group deleted;
- a broken aim (controllers or constraint deleted) is cleared, not refused (`weaponaim.broken`);
- a parent change in Aim Mode: Default, the change, Aim Mode again, in the press's chunk;
- one undo chunk each, the warp off, the time put back.

Shared code is lifted out of `weaponaim` rather than copied: the controller making, `_walk`,
`_local`, `_write_series`, `_fill_between`, `broken`, `turn_between` / `frames_off` take a node
and vectors and serve both.

## The Pose Library

- `helpers._camera_carrier`: under `FKHead_M` → `head`; under `Camera_follow` or an aim group
  repeating it → None (the world read per frame), as a non-rigid parent.
- A camera in Aim Mode is entry mode `aimed` like a weapon: the control's translate and the two
  controllers' translate keyed from the wanted matrix's aim and up points; `scene._kind` treats the
  camera aim controllers as CAMERA.

## Verification

- Unit tests (`tests/test_scenesetup_cameraaim.py`, `test_scenesetup_camera` additions):
  `camera_vectors`, the parent targets and refusals, the follow-group choice, the card's tab list.
- `docs/superpowers/plans/verify_camera_tab.py <clip> [rig]`, mayapy standalone on Manny_Rig: a
  keyed camera through Main → Head → Head (position) → Root (position) → World → Main, the camera's
  world track kept to 1e-4 cm / deg on every frame, the follow group gone after; Position only:
  the camera's world rotation equals Main's times its own local on every frame; Aim Mode on a
  keyed camera stands on every key to 1e-6, the controllers keyed on exactly those frames; Default
  back to 1e-4 on every frame; Aim Mode then Head (position) keeps the aim; one Ctrl+Z each press;
  a whole-body card saved with the camera on Head applied back. Re-run: verify_camera_control,
  verify_weapon_aim_mode, verify_1p_setup.
- Not seen in a GUI Maya unless the animator opens port 7001.
