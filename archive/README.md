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

## 2026-09-08

- `maya_curveview/` — the Curve Overlay (the graph editor drawn over the
  viewport, shelf button "Curves", 2026-09-05), with its six test modules
  under `tests/` and `verify_curveview.py`. Removed from the plugin at the
  animator's ask («уберем не только из полки но и из плагина в целом»);
  last shipped at commit `f65be61`. Spec:
  `docs/superpowers/specs/2026-09-05-viewport-curve-overlay-design.md`. The
  tests import `maya_curveview` from the plugin folder and will not run
  from here without putting `archive/maya_curveview/` on `sys.path`.
