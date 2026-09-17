# A third catalog weapon: the dagger, on the sword's axes

**Date:** 2026-09-17
**Status:** built the same day (asset script + verify below)

The animator's ask: «по пути C:\!!!Work\Animations\Sources\Dagger.fbx лежит
геометрия ножа. По аналогии с мечем и копьем нужно добавить нож в наш
плагин». The spear's design (`2026-09-08-spear-weapon-design.md`) is the
template; this records what is different about the dagger.

## What is in the file (measured in mayapy standalone, 2026-09-17)

One mesh `|Dagger`, 7292 vertices, 7695 faces, identity transform, pivot at
the origin, one untextured `openPBRSurface` material, no namespace. Local
extents **X −3.02..+2.67, Y −11.60..+13.05, Z −84.24..+30.02** — the long
axis is **Z**, 114.3 cm. Sliced along Z: the **tip is at −Z** (from −84 to
about −27 the blade is 8–21 cm wide in Y and 1–2 cm thin in X), the guard
sits around −27..+1.5 (5.7 cm thick, 21 cm wide), the grip +1.5..+20
(5 × 3.5 cm), the pommel +20..+30. So the origin lies between guard and
grip, exactly where the sword's does (sword: guard −6..18 on Y, grip below
it to −31, blade to +115.9).

**It is 114 cm long as the model came.** A dagger of that length is a
short sword on Manny; the catalog scale is a fact about the model and was
left at 1.0, as the sword's (147 cm) and the spear's (266 cm) are. If the
animator wants it smaller, the row's scale is the one number to change.

## The asset

`assets/Dagger_01.fbx`, written by
`docs/superpowers/plans/make_dagger_asset.py` (mayapy standalone,
re-runnable, the source never written):

- the turn takes **source Z → −Y** (so the tip, at −Z, lands at +Y and the
  grip at −Y like the sword's), **source Y → −X** (the blade's width onto
  the guard axis), **source X → +Z** (the thickness). Determinant **+1**:
  a rotation, not a mirror — sending Y to +X with the other two would
  have been one. The mesh is frozen (`makeIdentity`) so its own frame IS
  the new frame, history deleted, pivot at the origin;
- **the grip is centred on the origin transversely** (the spear's rule):
  its centroid sat at x −0.444, z −0.172 after the turn and is
  **0.0000 / 0.0000** after the shift. The origin's height along the
  blade stays where the author put it;
- a plain lambert `Dagger_01_material` replaces the `openPBRSurface` for
  the export (no textures to lose; that node type does not exist in every
  Maya the README admits; Add recolours every weapon anyway);
- exported with `FBXExport -s` after `FBXResetExport`, input connections
  off, the transform named `DaggerMesh` (`LongSwordMesh`, `SpearMesh`).
  Read back: **X −12.60..12.04, Y −30.02..84.24, Z −2.85..2.84** — blade
  on Y with the tip at +Y, width on X, thickness on Z. 452 KB.

## The catalog

`catalog.WEAPONS` gains `Weapon("Dagger_01", "Dagger 01",
_asset_path("Dagger_01.fbx"), "weapon_r", 1.0)` as the third row. Nothing
else changes: `attach`, `bonedrive`, `aim`, the window's dropdown and the
offset optionVars are table-driven.

## Proof

`docs/superpowers/plans/verify_dagger_weapon.py`, mayapy standalone (it
adds a rig): the dagger imports to one mesh transform; its frame is
measured against the sword's in the same run (longest axis, tip sign, the
order of the other two) rather than typed; the grip's centroid lies on the
axis; `aim.placement` puts the top locator on +Y for both; a real Add onto
the rig lands the dagger under the hand driving `weapon_r` at the zero
grip; the sword replaces it. The shipped zip grows by the asset's 452 KB.
