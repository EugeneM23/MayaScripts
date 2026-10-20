# The camera and the weapon are part of the character (2026-10-20)

The animator: «Давай улучшим наши риги и работу с позами в плагине. Наша библиотека поз должна
воспринимать камеру и оружие как часть рига и анимация должна сохраняться для камеры и оружия
автоматически. Если у нас в каких-то ригах нету камеры то ее нужно добавить. Нужно переносить анимацию
camera root и camera bone между скелетами и ригами и переподвязывать камеру если это нужно. То же самое
для оружия, мы не должны запоминать какое именно оружие у нас в руках и записывать анимацию для него мы
должны все делать через наши weapon_bone».

Asked, and answered:
- what "add a camera" means: **the bones and the camera**. The Creep rig and the Creep skeleton get
  `camera_root` / `camera_bone`. A card that carries the camera, applied onto a character with no
  Camera Setup, sets one up;
- the UE4 Mannequin: **left alone** (Epic's own skeleton, its clips go to an SK_Mannequin without
  those bones);
- a card on part of the body: **the helpers go with their part**. `weapon_r` goes with `hand_r`,
  `weapon_l` with `hand_l`, and `camera_root` / `camera_bone` only with a whole-body card;
- the road: **A - key what drives the bone** (over B, unlink / key / relink as the retarget does).

## What was there

- **The cards already hold the four bones.** A character card holds every bone of its skeleton, and
  an animation card every bone on every frame. But the helpers were never members
  (`posemath.is_helper`), so no Apply wrote them: onto a rig they read «driven», onto a skeleton
  nobody asked for them.
- **A helper's rest was its pose at Save** (`scene.rests`: an unskinned joint under another took its
  parent's bind with its own local AS IT STOOD). So a weapon bone's motion in its hand read as no
  motion.
- **A weapon in a hand drives its bone.** `bonedrive.link`: `weapon_r` is parent-constrained to
  the mesh with the grip's inverse as offset, and Camera Setup constrains `camera_root` to
  `SceneSetup_camera` the same way. A key on such a bone does not hold.
- **The Camera Setup camera was an OBJECT of a card** (keyed by its own channels beside the rig), so
  its motion and `camera_root`'s were two records of one thing.
- **The Creep had no camera bones** (91 joints; Manny 93, the Orc D 95). The shipped bind poses list
  the helpers. Manny's `camera_bone` is the exception, listed in none.
- **The skeleton road** (`skeletonimport.transfer`):
  - it refuses a skeleton carrying a Camera Setup («a camera: press Camera Setup again»);
  - onto another body it turns `weapon_*` / `camera_*` by their WORLD orientation, which leaves the
    camera at the target's own head height under a body of another size.

## The design

### 1. The Creep gets camera bones

`docs/superpowers/plans/make_creep_camera_bones.py`:
- runs in mayapy, in place, on `Creep_Rig.ma` and `Creep_Skeleton.ma`, and is idempotent (an asset
  that already has them is left alone);
- adds `camera_root` under the game root with Manny's local, translate (0, 0, 164), rotate,
  jointOrient and rotateAxis zero, xyz. The Creep's root frame stands like Manny's (Z up, under
  `Armature` at -90 X), so `camera.AXIS_OFFSET` holds;
- adds `camera_bone` under it at identity, both in the root's display layer at `weapon_r`'s radius;
- saves the bind pose again WHOLE over every joint and the `Armature` Null (trap 79's rule);
- checks that every other joint, every vertex and the skins at their bind are unchanged. On the rig
  it also checks that the bones follow Main / RootX_M;
- cuts Maya's script nodes and refuses banned words, as `make_creep_weapon_sockets.py` does. It is
  the Creep pipeline's last step, after `make_creep_textured_assets.py`;
- `assets/character_skeletons.json` is written again (`make_character_skeletons.py`).

### 2. A helper's rest is its bind (`scene.rests`)

An unskinned joint under another, listed with its parent in the bind pose, rests at its parent's
rest times its BIND-POSE local (`posed[path] · posed[parent]⁻¹`). Unlisted, it keeps the old rule (its
local as it stands): Manny's `camera_bone`, which no shipped bind pose lists and which every asset
holds at identity in `camera_root`.

### 3. Which helpers a card applies (`maya_poselib/helpers.py`, pure)

`HELPERS = ("weapon_r", "weapon_l", "camera_root", "camera_bone")`. `members_with(members, bones)`
on the card's (source) members:
- `weapon_r` when `hand_r` is a member;
- `weapon_l` when `hand_l` is;
- `camera_root` and `camera_bone` when the members hold every bone of the whole body
  (`scene.whole_body`).

Only bones the card's skeleton holds are added. It runs at APPLY, so every card made before applies
them too; Save changes nothing in a card but the helpers' rests. `ik_*`, `interaction` and
`center_of_mass` stay what they were.

### 4. The transfer (`posemath.Transfer.frame`)

A helper member's turn follows every member's rule: relative to its paired parent through the two
rests, with the parent's alignment, since a helper has no direction child. So at the card's rest the
target's helper stands on its OWN socket.

Its place:
- onto a twin with `places`: the card's place, exactly (the 2026-10-20 rule);
- otherwise: the target's rest local, plus the card's displacement from its own rest, carried into
  the target parent's axes and scaled: `t = t_rest_target + (t_s - t_rest_s) · rot(O_parent)⁻¹ ·
  scale`, where the source locals are read in the source parent's rigid frame and `O_parent` is the
  parent's offset.

### 5. Writing a helper (`helpers.Writer`)

The body solvers no longer see helper members: `rigsolve` / `skelsolve` get the members without
them. A `Writer`, prepared once per target, answers each helper member's plugs for a frame's
`wanted`. Per bone:
- **free**: its own joint channels, rotate (`skelsolve.joint_channels`, nearest the seed or the
  current value) and translate, its local read against its PARENT'S `wanted` (the parent's solve
  may land a hair off; the relation is what is kept);
- **our weapon drives it** (`bonedrive.driving_weapon`: in a hand, or out on the floor): the WEAPON is
  keyed. With `K = W_bone · W_weapon⁻¹` measured when the press begins (constant: the constraint's
  offset), the weapon must stand at `K⁻¹ · W_bone_wanted`.
  - Its parent's new world is its current one carried by the hand its weapon space follows
    (`P · W_hand_now⁻¹ · W_hand_wanted`), or its current one when nothing carries it (the floor).
  - The channels: rotate in its own order, nearest; translate with its pivots, shear and scale kept.
  - Nothing of WHICH weapon is written into a card: the card holds `weapon_r`; whatever is in the
    hand follows it;
- **our camera drives it** (`camera.camera_for`): the camera is keyed, the same way (its parent the
  character group: still);
- **the hands ride that weapon** (Connections, `followers_of`): skipped and said - keying it would
  move the hands;
- **anything else drives it**: skipped and named (`keys.writable`).

Apply, Blend (its preview sets the same plugs), Mirror (`posemath.mirror` swaps `weapon_r` /
`weapon_l`), Selected only (a weapon or camera is kept only when selected) and an animation paste
(every frame, the plugs planned for Replace / Insert like the others) all take these values. Notes
are said once: «weapon_r keyed through LongSwordMesh», «camera_root keyed through
SceneSetup_camera», «weapon_l skipped: the hands ride SpearMesh».

### 6. The camera set up after the keys

After a press that keyed `camera_root` on a character with no Camera Setup (and a `camera_root`),
Camera Setup runs on it (`camera.setup` over the playback range and the bone's keys, as the button).
This happens inside the press's undo chunk, said «camera set up on camera_root». It runs on the
Blend's finish, never on its preview.

### 7. The Camera Setup camera is no object

`scene.is_body`: a transform carrying `camera.MARKER` is the character's body (it names its
character, as a weapon does). An old card's object record that is such a camera is dropped at apply,
the helper road keys it.

### 8. The skeleton road

`maya_uebridge.skeletonimport`:
- `drive_for`: onto another body, `weapon_*` / `camera_*` follow the clip's bone RELATIVE TO THEIR
  PARENT (the rig retarget's `relative` rule: a driver standing at the clip bone's pose relative to
  its parent, carried by the target bone's parent). `ik_*` stay at rest;
- `onto_refusal` no longer refuses our camera. `onto_existing` tears a standing Camera Setup down
  first (`camera.teardown`) and sets it up again after the transfer;
- after the transfer onto any skeleton (onto, a new one, the square), a clip that carries a
  `camera_root` onto a skeleton that has one ends with Camera Setup, as the rig retarget always did.
  The line says «camera set up on camera_root».

The rig retarget already carries the four bones (`maya_rig_retarget.carry_helpers`). With the Creep's
new bones it gives the Creep its camera, relative to its root, as every rotation-only rig carries
them.

## Not built

- `ik_*` helpers on a card;
- the UE4 Mannequin's bones;
- a weapon's own shape on a card;
- Manny's `camera_bone` added to its bind pose (no shipped asset is resaved for it);
- the camera's lens.

## Proof

- unit tests:
  - `helpers.members_with`;
  - the Writer on fake scenes (free, weapon, floor weapon, camera, followers, foreign);
  - `Transfer` with helper members (twin exact; another body: socket kept, displacement carried and
    scaled);
  - `rests` with a bind-pose helper;
  - `is_body` of our camera;
  - `drive_for`.
- `docs/superpowers/plans/verify_camera_weapon_bones.py`, mayapy standalone:
  - a Manny skeleton with a UE clip, a Long Sword in the right hand and Camera Setup;
  - a whole-body card and a right-hand card saved from it;
  - applied onto Manny_Rig (no camera; a Spear in its right hand), Creep_Rig and a bare Manny skeleton;
  - checks:
    - every helper where the card puts it;
    - the swords following;
    - the cameras set up;
    - the hand card leaving the camera alone;
    - Mirror putting the right hand's weapon on `weapon_l`;
    - one Ctrl+Z;
    - an animation card the same on every frame;
    - the Creep asset's new bones and the skeleton road with a standing camera.

Live checks are the animator's after Check update.
