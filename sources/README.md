# sources — what the plugin's assets are built from

Moved here on 2026-09-28 (the animator: «все нужные файлы для работы нашего
плагина давай перенесем в папку плагина»). **Beside** `SkeldarAnim/`, not in it:
everything in `SkeldarAnim/` ships to every colleague, and these files are only
needed to REBUILD an asset. The plugin itself reads nothing outside its own
folder. Copied, not moved — the originals are still where they were.

| File | Where it came from | What reads it |
|---|---|---|
| `weapons/Spear_03.fbx` | the animator's Downloads (Blender 2.83 FBX from a Unity project) | `docs/superpowers/plans/make_spear03_asset.py` → `assets/Spear_03.fbx` |
| `weapons/Halberd_A.tga` | the same, the spear's texture (2048², 24-bit) | `make_spear03_asset.py` → `assets/Spear_03.png`; `verify_spear03_weapon.py` |
| `weapons/Dagger.fbx` | `C:/!!!Work/Animations/Sources/Dagger.fbx` | `make_dagger_asset.py` → `assets/Dagger_01.fbx` |
| `orc/SK_Orc_Marauder_F.FBX` | `C:/!!!Work/Animations/Sources/`, the animator's export of `/Game/Orc_Marauder/Meshes/SK_Orc_Marauder_F` from Unreal | `make_orc_source.py` → the source scene of `rebuild_orc_rig.py` → `orc/Orc_Rig.ma` |
| `orc/Orc_Rig.ma` | built here by the F orc's pipeline (`make_orc_source.py` → `rebuild_orc_rig.py` → `make_orc_rig_asset.py`); shipped as `SkeldarAnim/assets/Orc_Rig.ma`, «Orc [rig]», from 2026-09-25 until it left the plugin on 2026-09-28 («орка без текстур уберем из плагина») | `make_orc_d_rig_asset.py` → `assets/Orc_D_Rig.ma` (D's mesh on this rig) |
| `orc/SK_Orc_Marauder_D.fbx` | exported from the animator's Unreal (`MyProject2`, `/Game/Orc_Marauder/Meshes/SK_Orc_Marauder_D`, LOD0 + its 56 morph targets) by `docs/superpowers/plans/export_orc_d_from_unreal.py` through Remote Execution, 2026-09-28 | `make_orc_d_rig_asset.py` → `assets/Orc_D_Rig.ma`; `verify_orc_d_rig_asset.py` |
| `orc/textures/*.png` | the same export: the seven Texture2Ds the Orc D's maps are made from (body colour/normal/tattoo mask, cloth colour — its alpha the opacity mask — and normal, the eye's sclera and iris), from each texture's SOURCE data at its own size (4096² / 2048² / 512²) | `make_orc_d_textures.py` → `assets/Orc_D/*` |
| `orc/orc_d_materials.json` | the same export: every parameter the maps are baked with, read off the material instances D wears (intensity, contrast, tattoo colour and power, the eye's radii and brightnesses, the cloth's opacity clip) and the 64 samples of the `CA_Mannequin` curve atlas the body's tattoo colour is multiplied by | `make_orc_d_textures.py` |
| `orc/orc_d_1p_faces.json` | read over the port off the animator's own `Orc_D_1P` (2026-09-28): which faces of the Orc D's 3P mesh the first-person mesh keeps (`faces_3p`, in order) and which 3P vertex each of its vertices is (`vertices_3p`) | `make_orc_d_rig_asset.py` → `Orc_D_1P` in `assets/Orc_D_Rig.ma`; `verify_orc_d_rig_asset.py` |
| `creep/creep_T-pose_draft.fbx` | Downloads, `creep_T-pose_draft (1).fbx` (byte-identical to `creep_T-pose_draft.fbx`): Cascadeur 2024.1's export of the creature, its textures embedded | `make_creep_sword_fbx.py` → `assets/Creep_Sword.fbx`; `dump_creep_bind_normals.py`; `verify_creep_skeleton_fbx_cascadeur.py` |
| `creep/textures/*` | the Creep's texture sets, 2048², 2026-09-30: `creep_body_diff.png` / `creep_body_norm.png` / `creep_face_diff.jpg` the animator's (Downloads; the first two byte for byte what the Cascadeur FBX embeds as `8.png` / `9.png`, the third its `0.jpg` re-encoded), `creep_face_norm.jpg` / `creep_limbs_diff.png` / `creep_limbs_norm.png` out of that FBX's embedded `1.jpg` / `2.png` / `3.png` (the head's normal; the set the back and both arms share) | `make_creep_textures.py` → `assets/Creep/*`; `verify_creep_textured.py` |
| `manny/Manny_rig_02.ma` | `C:/!!!Work/Animations/Rigs/Characters/`, the animator's final Manny rig | `assets/Manny_Rig.ma` was this file minus its leftover `camera1` (15 lines cut by line range, textually); since 2026-09-30 the asset is also dressed in Manny's textures, in place, by `make_manny_textured_assets.py` |
| `manny/SKM_Manny_Simple.fbx` | exported from the animator's Unreal (`MyProject2`, the Orc Marauder pack's demo copy of the UE5 mannequin, `/Game/Orc_Marauder/Demo/Characters/Mannequins/Meshes/SKM_Manny_Simple`, LOD0) by `docs/superpowers/plans/export_manny_from_unreal.py` through Remote Execution, 2026-09-30: our `Skin_3p` index for index, `Hands_1P` a cut of it | `make_manny_textured_assets.py` (which face wears which of Unreal's two slots) |
| `manny/textures/*.png` | the same export: `T_Manny_01_D`/`_BN` (M_HeadLegs), `T_Manny_02_D`/`_BN` (M_Torso), 4096², and the logo mask `T_UE_Logo_M`, 1024², from each texture's SOURCE data | `make_manny_textures.py` → `assets/Manny/*`; `verify_manny_textured.py` |
| `manny/manny_materials.json` | the same export: the slots, both instances' parameters (the ones the base colour collapses to `D` at, the logo's place, size, colour and brightness), the master's blend mode and shading model, the textures' sizes | `make_manny_textures.py` |
| `armor/SM_Shield_Test.fbx` | exported from the animator's Unreal (`Atone`, `/Game/Prototype/Meshes/SM_Shield_Test` — the plate `BP_Techlimb` shows on the left forearm; its own source a `S3.obj` on the Desktop) by `docs/superpowers/plans/export_techlimb_from_unreal.py` through Remote Execution, 2026-10-01 | `make_techlimb_asset.py` → `assets/Armor/Tech_Limb.fbx` |
| `armor/techlimb_ue.json` | the same export: `DA_Techlimb`'s equip socket (`lowerarm_l`), `BP_Techlimb`'s offset of the plate, `M_TechLimb_Test`'s colour, the plate's 1526 vertices in mesh space, in the bone's space and in component space on `SK_Mannequin_proto`'s reference pose, and every bone's reference position and axes | `make_techlimb_asset.py`; `verify_armor.py` (where Unreal puts the plate) |
| `AdvancedSkeleton/` | Downloads, AdvancedSkeleton 6.797 | the `as_*_procedure.py` rig builds and the `verify_advancedskeleton_*` / `verify_asretarget*` scripts |

**`AdvancedSkeleton/` is not in git** (`.gitignore`): its licence says «You may
not resell, redistribute, or sublicense the software itself», and this
repository is public. On a fresh clone, unpack AdvancedSkeleton 6.797 here
(`sources/AdvancedSkeleton/AdvancedSkeleton.mel`) before running a rig build.

Importing the Creep FBX extracts its embedded textures into
`creep/creep_T-pose_draft.fbm/` — also ignored; the FBX already holds them.

Not here: the animator's creature scenes (`creep_T-pose_MIX_06_skin*.mb`) — the
Creep rig was built from the live scene, and its bind pose is recorded in
`docs/superpowers/plans/creep_bind_pose.json.gz` — and the infected original
`Manny_Sckeleton.ma` (`assets/Manny_Skeleton.ma` is its vaccine-cut copy).
