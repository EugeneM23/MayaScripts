# Creep 2: a second Creep as a rig, a skeleton and a portrait (2026-10-27)

The animator, with `Downloads/SK_Creep_skinned.FBX` imported into a Maya on port 7003: «новый крип
его нужно встроить в наш пайплайн, риг скелет, карточки». Asked, two decisions:

- **a second Creep** beside the shipped one (not a replacement): its own model card, «Creep 2»;
- **a palette colour for now**: its textures are not on this machine (the FBX's normal maps name a
  colleague's `C:/Users/User/Downloads/creep_textures/`, and there are no colour maps at all).

## What it is (measured, the scene read only)

- An Unreal export: materials `MI_Creep_Body` / `_Chainmail` / `_Head` (and an unused `_Outfit`),
  one skinned mesh of 102822 vertices / 196837 faces in three slots, `DiffuseUV`, 5 influences.
- 91 joints on Manny's names and hierarchy under the FBX importer's -90 X wrapper `SK_Creep_skinned`
  (root at (0.0017, -2.4012, 0), Cascadeur's numbers): the shipped Creep's names, no camera bones.
- **Not the shipped Creep re-posed**: the pelvis 5.3 cm lower, the calves 3.3 cm and the forearms
  2.2 cm shorter, the hands 1.8 cm and spine_05 2.2 cm longer; the fingers the same lengths.
- Its midline stands **0.32 cm off x = 0** (pelvis, spine, head; the hands' centre too).
- The weapon bones hold the fist's grip line along +Y - the convention the shipped Creep had before
  2026-09-30's one socket standard - and are zero-weight influences of the skin.
- ik_hand_gun, ik_hand_r on hand_r and ik_hand_l on hand_l: Manny's layout (Unreal's file).
- Twists at 1/3, 2/3 but the upper arms' (0.266 / 0.532, the first Creep's).

## The pipeline (docs/superpowers/plans/)

1. `make_creep2_source.py` (mayapy) -> `sources/creep2/Creep2_Source.mb`: the FBX (copied to
   `sources/creep2/SK_Creep_skinned.FBX`) in Manny's shape (the wrapper out, its turn in root's
   jointOrient), the mesh `Creep2_Body`, camera_root / camera_bone on Manny's local values, the weapon
   sockets turned a quarter about their own X into UE's convention (bindPreMatrix re-expressed: no
   vertex moves), the dead-path normal maps dropped, the bind pose whole over 93 joints, the joints in
   `Creep2_Skeleton`.
2. `rebuild_creep2_rig.py` (LIVE, a disposable GUI Maya: AdvancedSkeleton reads its own UI) - the
   Creep's procedure as the Orc's build runs it: fit (non-symmetric left) -> build -> place_parts ->
   constrain (orientation only, the pelvis its position too) -> orient_controls -> align_shapes ->
   finger_sdk_axes -> level IK feet -> the rotation-only mark -> Main at Manny's size -> the clavicle /
   shoulder drawings; Manny's rule for the ik_hand helpers (they follow the hands from where they
   stand). **The midline fit joints go onto x = 0**: AdvancedSkeleton calls a fit joint past 1 % of its
   scale on +X a left-side joint and refuses the build; the rig's middle joints then stand 0.32 cm
   beside their bones, which keep their places (they follow by orientation with offsets).
3. `make_creep2_assets.py` (mayapy) -> `SkeldarAnim/assets/Creep2_Rig.ma` (the built scene cleaned as
   the Orc's) and `Creep2_Skeleton.ma` (the rig without its rig, the bones re-seated, the mesh at the
   top beside `|root`). Manny's layout (root at world level), as the Orc D and Playerchar.
4. The catalog: «Creep 2 [rig]» (`Creep2_Rig`) after Playerchar's rig, «Creep 2 [skeleton]»
   (`Creep2`) after Playerchar's skeleton, model `Creep2` after the Creep in the grid; untextured (a
   palette colour on Add); fire «blood»; the portrait by `make_character_portraits.py`; the Auto card's
   template by `make_character_skeletons.py`.

## Not built

Its textures (to come from the animator), a 1P mesh, its own weapon, Cascadeur's `Armature` layout.
