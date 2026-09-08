# A second catalog weapon: the spear, on the sword's axes

**Date:** 2026-09-08
**Status:** built the same day (see the verify script)

The animator's ask: «В открытой сцене есть Spear1 эту модель нужно
использовать в качестве оружия и добавить в список так же как и sword. Так
же нужно выровнять оси этой модели чтобы совпадали с осями sword».

## What is in the scene (measured, read-only, 2026-09-08)

`|Spear1`, a 3ds Max export (`UDP3DSMAX`), 198 vertices, identity transform,
pivot at the origin, one mesh, material `Spear:default1` (a black phong with a
file texture, in a `Spear` namespace the import left behind). Local extents:
**X −206.74..+59.44** (the long axis, 266 cm), Y −6.39..+6.87, Z −14.71..+7.11.
Sliced along X: the **head is at −X** — from x = −118 to the tip at −206.7 the
blade is 15–22 cm wide in **Z** and 4–11 cm thin in **Y**; the +X end is the
butt cap (13 × 13 cm at x = 37..59); the shaft's cylinder carries vertices
only at its ends. The origin lies on the shaft, 59 cm above the butt and
207 cm below the tip.

The sword's convention (measured 2026-08-17 on `LongSword_02.fbx`): the blade
along **+Y** with the tip at +115.9, the crossguard on **X**, the thickness
on **Z**, the origin in the grip. Everything downstream reads that frame
from the geometry rather than assuming it — `aim.placement` takes the
longest local axis and its further end — so a spear on the same frame gets
the same aim, the same grip fields and the same Add.

## The asset

`assets/Spear_01.fbx`, exported from the animator's scene over the command
port from a **duplicate** of `Spear1` (the original is never touched):

- the duplicate is turned by the rotation **R: spear −X → +Y (tip up),
  spear Z → X (blade width across, the crossguard axis), spear Y → −Z
  (thickness)** — a proper rotation (det +1; mapping Y → +Z would be a
  mirror, and a mirror is not "aligning axes"), then frozen
  (`makeIdentity`) so the mesh's own frame IS the new frame, the pivot left
  at the origin, history deleted;
- **the origin's HEIGHT along the shaft stays where the model's author put
  it** — 59 cm above the butt, a two-handed lower grip. The sword's origin
  is likewise its author's. Add Weapon puts the origin on `weapon_r`, and
  the grip fields dial whatever the animator wants from there; guessing a
  "better" grip point is not this tool's business. **Transversely the shaft
  is centred on the origin**: measured after the turn, the butt cap's
  centroid sat 3.81 cm off the Y axis (the author's pivot is the 3ds Max
  scene origin, beside the shaft), while the sword's origin is on its own
  axis (X ±15.58, Z ±1.57, symmetric) — so the mesh is shifted by that
  centroid before freezing, and both end centroids then lie on the axis;
- a fresh plain material `Spear_01_material` replaces the namespaced
  textured phong for the export (the black phong is the 3ds Max import's;
  `colour.paint_nodes` recolours every weapon on Add anyway, and a `Spear:`
  namespace inside the FBX would arrive as clutter);
- exported with `FBXExport -s` after `FBXResetExport`, input connections
  off, the mesh transform named `SpearMesh` (the sword's is
  `LongSwordMesh`), 1.0 scale — the model is 266 cm, a real spear.

## The catalog

`catalog.WEAPONS` gains `Weapon("Spear_01", "Spear 01",
_asset_path("Spear_01.fbx"), "weapon_r", 1.0)`; `_sword_path` becomes the
general `_asset_path(name, legacy="")` (the sword keeps its legacy fallback,
the spear has none). Nothing else changes: `attach`, `bonedrive`, `aim`,
the window's dropdown and the offset optionVars are all table-driven.

## Proof

`docs/superpowers/plans/verify_spear_weapon.py`, mayapy standalone: the FBX
imports to exactly one mesh transform; its longest local axis is Y with the
tip at +Y, the blade width on X, the thickness on Z — the same ordering the
shipped sword measures in the same run, so the gate compares the two rather
than asserting numbers; the origin lies inside the shaft; `aim.placement`
puts the top locator on +Y for both; a real Add onto the rig lands the spear
under the hand driving `weapon_r`, and the sword and the spear both come
from the dropdown by label. Nothing in the animator's scene is changed by
the export.
