---
name: melt-morph
description: Use when the user asks to make one mesh flow, melt, pour or transform into another in Maya — «перетекает как жидкость», «превращается в», «морф», liquid or molten-metal transition between two models, a wave running along a limb into a weapon, techno-limb transformations, and when such a transition has to end up baked to Alembic.
---

# One mesh melting into another (Bifrost level sets → Alembic)

## Overview

Drive `maya_meltmorph.py` over the command-port bridge. It blends two signed
distance fields with a scalar field that sweeps along one axis: ahead of the
front you see the source, behind it the target, and in the band between them
the material genuinely reforms. Topology changes freely every frame — that is
what reads as liquid, and it is why this is NOT a blendshape.

You orchestrate and judge the look; the tool does the voxel work. Bridge
mechanics: CLAUDE.md notes 2, 5–9 and trap 17 apply to every send.

## When NOT to use

- **The result must be blendshapes or UE morph targets.** Those need constant
  topology and a marching-cubes contour has none. There is a fixed-topology
  route (project a frozen base onto the level set with `displace_points`), but
  it crumples wherever the shape's features TRAVEL across the surface — see the
  spec. Say so before promising it.
- Two shapes in completely different places. The blend is per-point in space,
  so with no overlap the source dissolves here and the target grows there
  instead of flowing.
- A rigid mechanical transform (parts folding, sliding) — that is animation,
  not a fluid blend.

## The workflow

1. **Probe** (read-only): `mm.probe()`. Report the meshes, their **border
   edges** and their extents before touching anything. Border edges > 0 is the
   headline: an open mesh cannot be voxelised solid.
2. **Part of the model must survive?** If the user says some of it should not
   change — and especially if they have SELECTED faces — **read the selection
   before anything else and stash it in an objectSet**, because almost any
   command drops it. Then `mm.split(shape, faces_or_setname, grow=2)`:
   `keep` is those faces with their ORIGINAL polygons, UVs and shader, out of
   the simulation entirely; `melt` is the rest, grown a couple of face rings so
   its cut edge tucks under `keep`, and closed. This beats masking the alpha
   field: the boundary follows the actual selection rather than an iso-surface,
   and nothing textured ever enters the voxeliser. Feed `melt` to `build()`.
3. **Prepare** (only if you did NOT split): `mm.prepare(shape)` for every open
   mesh — a hidden closed duplicate. Check `border_after == 0` in the reply.
3. **Decide the sweep axis from the geometry, not from the eye.** Slice the
   source along each axis and look at where the vertices are: fine detail
   (fingers, teeth) carries far more vertices than a smooth tube, so the dense
   end is the detailed end. Confirm against the shot camera's position before
   choosing `axis` / `start`.
4. **Build**: `mm.build(source, target, axis=, start=)`. No mesh in the reply
   means an empty graph — the message names the two usual causes.
5. **Calibrate**: `mm.calibrate()`. It returns `live_range`, the part of the
   sweep that actually changes the shape. Use it; do not guess the front
   positions.
6. **Key**: `mm.key_range(first, last)` — defaults to the calibrated range, so
   the flow fills the frames the user asked for instead of idling at the ends.
7. **Checkpoint — the look**: screenshot 5–6 frames from a 3/4 view AND from
   the shot camera, send the PNGs. This is the only way to judge it; every
   number can be right while the shape is wrong.
8. **Tune** against what the user says, `mm.tune(...)`, and re-shoot. The
   levers are in the table below.
9. **Bake**: `mm.bake(first, last)` → Alembic (+ GPU cache), verified
   order-independently, and the graph is left disconnected so nothing
   recomputes. `verified: True` in the reply is the proof; relay it. The
   reply's `relink` string is how to make the sim live again.

## The levers

| Want | Change | Notes |
|---|---|---|
| finer shape | `detail_size` ↓ | cost is roughly quadratic; 0.3 on a 75 cm arm keeps fingers |
| longer, softer wave | `width` ↑ | the transition band in scene units |
| lighter mesh for playback | `mesh_scale` ↑ | contour triangles only, voxels untouched — 2 quarters the face count |
| more molten / gloopy | `smooth_iterations` ↑ | **1–2 max**: `iterations 2 × deviation 3` erased a hand's fingers |
| weld near-touching bits | `fillet` ↑ | dilate +r then erode −r, a morphological closing |
| retime | move the two keys | it is an ordinary animCurve on `meltGraphShape.front_pos.<axis>` |

`smooth_deviation` is in VOXELS: its world size is `deviation × detail_size`.
Setting it to 1 is nearly a no-op, which reads as "smoothing does nothing".

## Sharp edges

- **The end frame is a SOFTENED target, not the target mesh.** Measured on a
  crossbow: the spike came ~7 cm short and the limb span ~5 cm. If the shot
  cuts to the real model afterwards there will be a pop — cross-fade over 2–3
  frames, or lower `detail_size`. Tell the user this before they discover it.
- **Never cap holes with a big `min_hole_radius`.** 6 cm closed a hand's mesh
  and welded the fingers into a mitten. `prepare()` then radius 0 is the fix.
- **Do not verify a bake by comparing vertex i to vertex i.** The contour's
  vertex order is not stable between evaluations; that comparison reported
  167 cm of error on geometry that was bit-identical. `bake()` already checks
  area, bbox and closest-point distance.
- **You cannot measure playback speed over the bridge.** An empty viewport
  timed the same as every cached and live variant (~0.38 s/frame) — the floor
  is the harness. If the user reports slow playback, hand them `mesh_scale`
  and ask them to judge; do not claim a speed-up you cannot see.
- Bifrost JIT-compiles the graph on first evaluation, so frame one after any
  edit is slow and the rest are not. That is not a bug to chase.

## Design and every measured trap

`docs/superpowers/specs/2026-08-31-melt-morph-design.md`. Read it before
changing `maya_meltmorph.py` — the Bifrost scripting facts in there (addNode
spelling, fan-in child ports, the `volume_to_mesh` trap, brace-form float3
defaults) each cost a debugging round and none of them raise an error.
