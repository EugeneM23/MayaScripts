# Archive

Standalone tools superseded by the packages for the UE5 Manny workflow
(2026-08-17 audit; git history holds every version):

- `maya_rig_controllers`, `maya_ctrl_shape_orient`, `maya_rig_align`,
  `maya_rig_mirror`, `maya_rig_groups` — manual controller shaping and
  aligning; `maya_overrig` now sizes, colours, aligns and orients
  controllers automatically (fkrings, fkalign).
- `maya_cube_weapons`, `maya_cube_shield` — cube blockout spawners;
  `maya_scenesetup` attaches real catalog models. (The blockouts knew five
  weapons; the catalog holds one — kept here in case that gap matters.)
- `maya_rig_constraints` — generic prop constrainer, no package equivalent.
- `verify_fk.py`, `verify_bake.py`, `verify_build.py` — first-generation
  live proofs, stale against the per-chain manifest redesign
  (`verify_build.py` references the removed `builder.BUILD_SET`;
  `verify_fk.py` asserts the legacy flat FK_SET behavior).
