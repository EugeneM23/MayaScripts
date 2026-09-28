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
| `orc/SK_Orc_Marauder_F.FBX` | `C:/!!!Work/Animations/Sources/`, the animator's export of `/Game/Orc_Marauder/Meshes/SK_Orc_Marauder_F` from Unreal | `make_orc_source.py` → the source scene of `rebuild_orc_rig.py` → `assets/Orc_Rig.ma` |
| `orc/SK_Orc_Marauder_D.fbx` | exported from the animator's Unreal (`MyProject2`, `/Game/Orc_Marauder/Meshes/SK_Orc_Marauder_D`, LOD0 + its 56 morph targets) by `docs/superpowers/plans/export_orc_d_from_unreal.py` through Remote Execution, 2026-09-28 | `make_orc_d_rig_asset.py` → `assets/Orc_D_Rig.ma`; `verify_orc_d_rig_asset.py` |
| `orc/textures/*.png` | the same export: the seven Texture2Ds the Orc D's maps are made from (body colour/normal/tattoo mask, cloth colour — its alpha the opacity mask — and normal, the eye's sclera and iris), from each texture's SOURCE data at its own size (4096² / 2048² / 512²) | `make_orc_d_textures.py` → `assets/Orc_D/*` |
| `orc/orc_d_materials.json` | the same export: every parameter the maps are baked with, read off the material instances D wears (intensity, contrast, tattoo colour and power, the eye's radii and brightnesses, the cloth's opacity clip) and the 64 samples of the `CA_Mannequin` curve atlas the body's tattoo colour is multiplied by | `make_orc_d_textures.py` |
| `creep/creep_T-pose_draft.fbx` | Downloads, `creep_T-pose_draft (1).fbx` (byte-identical to `creep_T-pose_draft.fbx`): Cascadeur 2024.1's export of the creature, its textures embedded | `make_creep_sword_fbx.py` → `assets/Creep_Sword.fbx`; `dump_creep_bind_normals.py`; `verify_creep_skeleton_fbx_cascadeur.py` |
| `manny/Manny_rig_02.ma` | `C:/!!!Work/Animations/Rigs/Characters/`, the animator's final Manny rig | `assets/Manny_Rig.ma` is this file minus its leftover `camera1` (15 lines cut by line range, textually — never an open-and-resave) |
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
