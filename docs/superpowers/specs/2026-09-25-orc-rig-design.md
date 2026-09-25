# The Orc rig — SK_Orc_Marauder_F as a third rig row (2026-09-25)

## The ask

«В открытом проекте в Unreal есть персонаж SK_Orc_Marauder_F его скелет совпадает с нашим
manny rig давай перенесем его из анрила и добавим к нам в проект еще один риг "ORC". я так
понимаю что у нас все готово просто нужно перенести».

The asset lives in the animator's `MyProject2` (`/Game/Orc_Marauder/Meshes/SK_Orc_Marauder_F`,
skeleton `SKEL_Orc_Marauder`). Remote Execution was off in that project, so the animator
exported the FBX by hand (`Desktop/SK_Orc_Marauder_F.FBX`, 5.3 MB); a copy is kept at
`C:/!!!Work/Animations/Sources/SK_Orc_Marauder_F.FBX` so the pipeline re-runs.

## What was measured first

- **Names and hierarchy are Manny's**: 91 joints; every shared bone has Manny's parent.
  Extra: `AB_Armor_Shoulder_L/R` (shoulder-pad bones under the clavicles, 860 vertex-weights
  each). Missing: `weapon_r`, `weapon_l`, `camera_root`, `camera_bone`.
- **Proportions are not Manny's**: root, pelvis, the whole spine, the legs, the forearms and
  the hands stand exactly on Manny's (0.000 cm; the hands' world positions too), but the neck
  is 1.39× (spine_05→neck_01 16.48 against 11.89; the head 5.16 cm higher), the upper arm 1.07×
  (+2 cm), the clavicle 1.05×, the fingers up to 2.3 cm off, bones turned up to 7°.
- One skinned mesh in 5 LODs (LOD0 43152 vertices, 5 material slots, 81 of 91 joints weighted,
  8 influences max), 56 morph targets (52 ARKit face shapes, 4 elbow correctives
  `LoweArm_65/90_L/R`), real smoothing (18127 hard of 108380 edges), no textures in the file
  (one normal map pointing at `D:/Characters/...`), the importer's Z-up wrapper, and Blender
  Auto-Rig Pro properties on the joints (`flip_fluid`, `set`, `binded`, `arp_rig_name`, `ori_name`).
- The twist bones stand at exactly 1/3 and 2/3 of their segments — AdvancedSkeleton's own spacing.

## Decisions

1. **Not Manny's rig with the orc's mesh.** Manny's AdvancedSkeleton stands on Manny's bones;
   binding the orc's skin to them would tear the neck (5 cm). The orc gets its own rig, built
   by the **Creep's procedure** (`as_creep_rig_procedure.py`), which is exactly "an AS rig over a
   skeleton with Manny's names and its own proportions": fit on the bones by long path, bones
   orientation-constrained (pelvis point+orient), controls on the bones' frames, IK feet level,
   `Group.skeldarRetarget = "rotation"`. So the retarget copies rotations only — the orc keeps
   its neck and arms, and root motion, pelvis and legs land exactly because those bones match.
2. **The four helper bones are added** (the animator's answer: «все четыре»): `camera_root`,
   `camera_bone` under root, `weapon_r` under hand_r, `weapon_l` under hand_l, each with Manny's
   LOCAL values from `manny_skeleton_template.json` — so every catalog weapon sits in the orc's
   hand as in Manny's, Connections works, the retarget carries the weapon and camera bones, and
   the retarget's Camera Setup has its bone. Cost, accepted: an export carries 4 bones
   `SKEL_Orc_Marauder` does not have (Unreal skips them, or they are added to the skeleton there).
3. **The shoulder pads ride their clavicles** (the animator's answer): no control; in Unreal they
   are presumably driven by `ABP_Orc_Marauder_PostProces`.
4. **The ik_hand helpers follow Manny's rule, not the Creep's**: `ik_hand_gun` and `ik_hand_r`
   follow hand_r, `ik_hand_l` hand_l, from where the file has them (ik_hand_gun ON hand_r) — the
   Creep's rule zeroed ik_hand_gun because that animator's file had them off the creature's hands.
5. **LOD0 only**, as `Orc_Body`; the blendShape keeps its 56 targets as deltas (weights 0, nothing
   driving the correctives); the morph-target meshes, LOD1-4, the dead texture and the Blender
   properties go (the last rode into every animation export — `Orc|root.flip_fluid` in the first).
6. Names: key `Orc_Rig`, label «Orc [rig]», the third row (rigs first), namespace `Orc_Rig`,
   `Orc_Rig1`, …; the export wrapper (Cascadeur layout) is `Orc`.

## Pipeline (re-runnable)

1. `make_orc_source.py` (mayapy): the FBX → `|root` at world level in Manny's shape (jointOrient
   −90 X, rotate 0), `|Orc_Body`, the helper bones, the bind pose whole over 95 joints, layer
   `Orc_Skeleton`. Refuses a moved joint, a moved mesh, a skin off its bind, lost smoothing.
2. `rebuild_orc_rig.py` (LIVE, a disposable Maya on its own port — AS reads its own UI): the Creep
   procedure's fit → build → place_parts → constrain → orient_controls → align_shapes →
   finger_sdk_axes → as_frames(IK feet) → mark, with the orc's HEAD_MESH/ROOT/LAYER and Manny's
   ik_hand rule; the mesh into `Group|Geometry`.
3. `make_orc_rig_asset.py` (mayapy): clean-up, `.ma`, script nodes cut from the text, banned words
   refused → `SkeldarAnim/assets/Orc_Rig.ma` (22.1 MB).

## Proof

- `verify_advancedskeleton_orc_rig.py` — **29 of 29, live** (disposable Maya): fit on the bones
  0.000000 cm, rig joints on the skeleton's to 0.0001 cm, controls on the bones' frames 0.00000°,
  IK↔FK align 1e-6, fingers about their +Z, feet level, build pose round trip 0.000000000, the
  helper bones on Manny's local values to 2.8e-14, the pads riding their clavicles to 1.7e-13,
  the 56 blend targets.
- `verify_orc_rig_asset.py` — **16 of 16, standalone** on `LongSword_Attack_Right_Heavy_3P.FBX`
  (the clip's weapon_r and camera_root given a move of their own at mid-take: no clip on disk
  moves either): two orcs and a Manny added, each in its namespace, marked, tagged, at their
  bind, painted; the button retargets the first orc to 0.00127° with bone lengths 0.000000 cm and
  limb bones pointing as the clip's to 0.062°; the other two unmoved 0.000000000; the pads ride
  through the take; the Long Sword at zero grip on weapon_r, weapon_r carried relative to the
  hand to 2e-6 while moving 0.43, the retarget's camera on camera_root with camera_root on the
  clip's to 3e-16 while moving 20 cm; Remove Weapon hands the bone back its track; the export
  reads back 95 joints, 0 meshes, under `Orc`.
- `verify_connections.py` with `VERIFY_RIG = "Orc_Rig"` — **40 of 40, live** (disposable Maya).
- 2254 unit tests.

## Not built

A clean «Orc [skeleton]» row; the orc's own sword (`SM_Orc_Marauder_Sword`) as a catalog weapon;
driving the elbow correctives; the fur's alpha (the fur cards read dark in the viewport under
our colour blinn — the asset has no opacity map).
