# The camera stands on `camera_root`, and Camera Setup is a button again

**Date:** 2026-09-18
**Ask:** «В наш риг нужно добавить камеру так же, как мы делаем при
ретаргете. Только давай будем не camera bone привязывать к камере, а
camera root, и в механизм ретаргета тоже внесём эту правку».

## What changes

- **`maya_scenesetup.camera.BONE` is `camera_root`.** Measured on the rig
  before changing it: `camera_root` (a child of `root`) and `camera_bone`
  (its child) stand in the SAME world transform at rest — world matrices
  equal to 0.000000, both at (0, 164, 0) with world rotation (−90, 0, 0),
  local rotates and jointOrients zero — so the axis turn `AXIS_OFFSET`
  measured against `camera_bone` on 2026-08-17 holds for `camera_root`
  unchanged. Everything else in the module was already written against
  `BONE`: the leaf-name resolution, the per-rig camera name, `camera_for`,
  `our_constraints`, setup and teardown.
- **The retarget's bake sets the camera up on `camera_root`**
  (`maya_rig_retarget.carry_helpers`). Both helper bones are still carried
  from the source (`HELPER_BONES` unchanged), so `camera_bone` keeps its own
  baked track as `camera_root`'s child. Before the transfer the bake tears
  down a standing camera on `camera_root` AND on `camera_bone` — a camera an
  older build left on the bone would otherwise meet the transfer's
  constraint and splice a pairBlend (trap 37's mechanism).
- **Camera Setup is a button in the Characters section again** (it left the
  panel on 2026-09-07 when the camera moved into the retarget's bake): the
  retarget's own step by hand, on the current character's `camera_root`,
  over the playback range ∪ the bone's keys. A second press tears it down —
  the bone baked back from the camera first, then the camera deleted (the
  order `camera.teardown` has always kept). `window.camera_setup`; the
  status goes to the Characters line.

## Proof

- `verify_rig_pipeline.py` (mayapy standalone, adds a rig, retargets a
  twin, bakes): **0 of 30 gates failed, 2026-09-18** with the camera gates
  on `camera_root` — one camera of ours in the rig's namespace driving
  `camera_root`, sitting in its transform to **0.000000**, `camera_root`
  and `camera_bone` both carried to 0.000000, the second retarget leaving
  one camera again.
- `verify_many_rigs.py`'s two-rig camera gates were pointed at
  `camera_root` the same way (not re-run today).
- Live, on the animator's rig: the button pressed twice over the port —
  the camera created on `camera_root` and driving it, then removed with the
  bone baked back (see the session's smoke below in CLAUDE.md).
- Unit: `camera.BONE == "camera_root"`, the refusal texts name it, the
  Characters section carries the button after Add Character,
  `window.camera_setup` is callable again (the 2026-09-07 gone-test updated
  to say so).
