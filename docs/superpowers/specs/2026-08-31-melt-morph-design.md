# One mesh melting into another — design

2026-08-31. Built for `AS_TechLimb_MeltMorph_1P_01.ma`: a first-person
techno-limb flowing into a crossbow/ballista as a wave from the fingers to the
elbow over 20 frames, baked to Alembic. Tool: `maya_meltmorph.py`. Workflow:
`.claude/skills/melt-morph/SKILL.md`.

## Why level sets and not a morph

The animator's ask was "перетекает как жидкость". A vertex morph cannot do it:
the two shapes have different topology, different vertex counts, and the
transition has to change genus (a crossbow limb detaches from the arm and
reattaches). A signed distance field has none of those constraints — blend two
fields per point in space and contour the result, and the surface merges,
splits and reforms for free.

Bifrost ships the whole toolkit with Maya, so nothing had to be written: two
`mesh_to_level_set`, one `merge_volumes` in `AlphaBlendLevelSet` mode, a
`contour_dual_marching_cubes` at the end.

## The wave

`merge_volumes.alpha` is documented as "a float value or a field", and it does
accept a `Core::Fields::ScalarField` — the port's type changes from `float` to
`ScalarField` on connect. So the front is a field, not a per-frame number:

```
plane_field(normal = axis)  ->  scale_field(scale = W on that axis)  ->  alpha
```

`plane_field` gives the signed distance to a plane; `scale_field` divides the
domain, so the value becomes `(p·n − F)/W`: **0 at the front, 1 one band-width
behind it**, clamped by the blend into "pure source" and "pure target". Because
`scale_field` divides, the plane itself must be parked at `(F − W/2)/W` — that
factor is the single most confusing line in the tool and it is why
`set_front()` exists rather than the caller writing the attribute.

Volume A is the source and volume B the target, since the blend is
`(1−alpha)·A + alpha·B` and alpha is 1 *behind* the front.

The front is a published `Math::float3` input port, which becomes the Maya
compound attribute `front_pos`. Keying it is ordinary animation, so retiming
the melt is retiming one curve — no bake, no rebuild.

## Decisions

**The sweep axis is read off the geometry.** For the ballista shot the hand's
vertex density along Z settled it: 6094 of 7946 vertices sat in the last two
slices (fingers carry far more vertices than a forearm tube), so fingers were
at high Z and the elbow at low Z. The shot camera's position confirmed the
direction. Guessing from the bounding box alone would have run the wave
backwards.

**Open meshes are closed in Maya, not bridged in the voxeliser.** Both source
meshes were open — 1226 border edges on the hand, 296 on the ballista — and a
solid voxelisation of an open mesh leaks and returns nothing. `mesh_to_level_set`
has `min_hole_radius` for exactly this, and it works: at 6 cm the hand
voxelised into a single clean shell. It also **welded the fingers into a
mitten**, because a radius that caps a sleeve opening also caps the gaps
between fingers. So `prepare()` runs `polyCloseBorder` on a hidden duplicate
(1226 → 0 border edges, one added face per loop) and the voxeliser runs at
radius 0, which keeps the knuckles readable.

**The closing and the smoothing stay small.** `iterations 2 × deviation 3`
(0.9 cm at a 0.3 cm voxel) turned the fist into a smooth club. 1 × 1 keeps the
fingers. The liquid quality comes from the alpha blend itself; the smoothing is
only there to take the voxel stair-stepping off.

**The sweep is calibrated, not guessed.** An SDF alpha blend shows nothing
until the incoming shape's negative distance beats the outgoing shape's
positive one, so a naive sweep from beyond one shape to beyond the other has
dead frames at both ends — measured: with the front running 97 → 22, frames
0–3 and 18–20 were byte-identical. `calibrate()` walks the span, notes where
the output stops matching the pure source and starts matching the pure target,
and hands back the live range; 88 → 30 for this shot, and then every frame of
0–20 changes.

**The end frame is a softened target.** At detail 0.3 the finished ballista
reached z 88.3 against the real mesh's 95.4 and x −0.2 against −10.8: the spike
tip and outer limb ends come up short, because the closing and smoothing erode
thin features. Accepted rather than fixed — a finer voxel costs quadratically
and the softness is on-style. The cure for a cut to the real model is a 2–3
frame cross-fade, and the skill says so.

## Baking

Alembic stores topology per sample, which is exactly what a contour produces,
so the bake CAN be lossless — and on the first shot it was. Verified there:
identical vertex counts on all 21 frames, identical surface areas to three
decimals, and worst closest-point distance **0.000000000** on five sampled
frames.

### But `AbcExport` under-samples a topology-changing mesh (2026-08-31)

On the second shot (frames 5..25, mesh 15k → 32k verts) the same bake came
back wrong: frames 5–12 exact, then progressively behind with repeats. Chased
to a **minimal reproduction with no Bifrost in it at all** — a `polyCube` with
`subdivisionsWidth` keyed 1..41 over the same 21 frames, so the vertex count
changes every frame and costs nothing to evaluate:

```
source : 8 16 24 32 40 48 56 64 68 72 80 88 96 104 108 112 112 116 120 128 136
readback 8 16 24 32 40 48 56 64 64 68 72 80 88  88  96  96 104 104 108 112 112
```

21 frames come back mapped onto **16 archive samples** — exact for the first
eight, then held and repeated. Eliminated, each by measurement:

| Suspect | How it was ruled out |
|---|---|
| constant frame offset | best fit was offset 0 at 8 of 21 frames; no offset explains it |
| fps mismatch (scene is `ntsc`) | a fixed 30/24 ratio would compress from the first frame, not the ninth; and `-step 0.8 / 0.75 / 0.5` all made it *worse*, not right |
| Bifrost async evaluation | `enableAsync 0` changed not one number; two exports were byte-identical, and a race is not deterministic |
| per-frame evaluation cost | a 4× lighter mesh (`mesh_scale 2`, 14680 faces) drifted on exactly the same frames |
| my export flags | identical under no flags at all, `-dataFormat ogawa`, `-worldSpace`, `-stripNamespaces` and explicit `-step 1` |
| the mesh being Bifrost-driven | round-tripping an already-cached, disk-fed mesh drifted the same way |
| the read-back being stale | settled reads (dgdirty + time nudge) matched unsettled ones exactly |

Sub-frame probing of the archive puts its sample boundaries on **non-integer
frames** (18.5, 20.5, 22.75) with uneven gaps averaging 1.294 — consistent with
fewer samples declared uniform across the range, not with any timing effect.

Root cause inside Alembic/AbcExport is **not** identified. What is settled is
that the writer cannot be trusted here, so `bake()` now sweeps EVERY frame's
vertex count (nearly free) instead of spot-checking three, returns
`verified: False` with `drifted_frames`, and prints a loud warning. A
three-frame check would have passed this bake if its samples had landed in the
first third.

Not yet answered: whether `cmds.gpuCache` — a separate writer — survives
varying topology. The obvious test was run and was **badly designed** (a cube's
bounding box is constant, so it proved only that the file reads), so that
question is open, and the note must not be read as validating the GPU path.

Meanwhile the live graph is a perfectly serviceable deliverable: it computes a
frame in about the same time as any cache reads one (see the playback section),
so nothing is actually lost by not baking.

**Verification has to be order-independent.** The first attempt compared vertex
*i* of the sim against vertex *i* of the cache and reported up to 167 cm of
error while the counts matched exactly — the signature of a different vertex
ORDER, not different geometry (the contour is multithreaded and its output
order is not stable between evaluations). `bake()` compares counts, area, bbox
and closest-point distance instead.

After baking, `bake()` disconnects the graph from the output mesh. Nothing
pulls it, so Bifrost stops evaluating; `relink()` puts it back in one line.

**No speed-up was demonstrated, and the tool does not claim one.** Timed over
the bridge, the live graph, the Alembic-driven mesh and a GPU cache all came
out at 0.35–0.38 s per frame — and so did an **empty viewport**. The floor is
the measurement harness (a command-port round trip plus a forced redraw per
frame), well above the cost of any of the three. What the bake does buy is
real but different: the scene no longer needs Bifrost, nothing recomputes when
anything is touched, the JIT compile on the first frame after an edit is gone,
and the result is portable. If playback is genuinely slow the lever is
`mesh_scale` (mean 47322 faces per frame at scale 1).

## Bifrost scripting facts

Every one of these fails **silently** — empty output, or a value that quietly
keeps its old setting. None raise.

| Fact | Consequence if wrong |
|---|---|
| `-addNode` takes `"BifrostGraph,<Namespace::Sub>,<node>"` | the `Namespace::Sub::node` spelling from Bifrost's own graph JSON is rejected |
| a Maya mesh enters through the `pathinfo` port option, `|` → `/` | — |
| one path per `Object` port | two paths in one port outputs nothing |
| several meshes need `array<Object>` | — |
| a fan-in child must be created with `createInputPort("volumes.volume")` before `vnnConnect` | `Object → array<Object>` never connects; children are `volume`, `volume1`, … |
| `volume_to_mesh` is broken for a scripted fan-in | accepts the child port, compiles clean, outputs an EMPTY mesh; `contour_dual_marching_cubes` takes a single `volume` and works |
| float3 defaults must be `"{0,0,1}"` | comma-separated and per-component `normal.x` are accepted and IGNORED — the graph then computes along the wrong axis and never changes |
| `createMayaGeometry` takes the BARE port name | a port path is rejected; and no mesh appearing is the cheapest diagnostic for an empty graph |
| a published float3 port's children are `front_pos.x/.y/.z` | `front_posX` does not exist |
| `queryPortMetaDataValue(port, "pathinfo")` answers empty | the source paths cannot be read back off the port, so the tool stores them as string attributes on the board |
| `serializeGraph` returns int32, not JSON | useless for inspecting your own graph |
| `Core::Math::multiply`/`subtract` have no input ports until you make them, and `createInputPort` ignores the type you ask for | hand-built vector math is a trap; `Modeling::Points::displace_points` does `p + w·s·v` in one node |

Authoritative sources, both on disk and worth reading before guessing:
port names in `$BIFROST_LOCATION/resources/<pack>/docs/ENU/*.md` (the same text
the graph editor's Info tab shows), and graph STRUCTURE — including fan-in port
naming — in the shipped example graphs' JSON under
`$BIFROST_LOCATION/resources/graphs/*/*.json`.

## Not built

- Fixed-topology output for blendshapes / UE morph targets. It was built and
  measured during exploration: a frozen base pushed onto the level set with
  `sample_volume` + `sample_volume_gradient` + `displace_points`, 3–4 Newton
  steps (mean error 0.0004 of a voxel), constant vertex count, and it bakes to
  a real `blendShape` that reproduces the sim to 1.2e-7. But a fixed-topology
  mesh cannot follow a feature that TRAVELS across the surface: even with
  `smooth_mesh` relaxation between projection steps, the surface area ran 25–55 %
  above the truth — folds — and the transition zone carried visibly stretched
  triangles. Usable for a feature that only deflates in place; not for this.
- A curved or noisy wave front. `Core::Fields::fractal_noise_field` and
  `warp_field` are the pieces; a flat plane is what shipped.
- Cross-fade to the real target mesh at the end of the transition.
