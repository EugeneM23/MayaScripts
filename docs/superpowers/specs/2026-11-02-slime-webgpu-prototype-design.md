# Slime in the browser: an MLS-MPM prototype on WebGPU (2026-11-02)

The animator: «сделай прототип симуляции в браузере а потом подумаем как запекать. Мне прежде
всего нужна жидкость похожая на слизь, кисель», and then «Делай как можно лучше я в этом ничего
не понимаю все на твое усмотрение». So every decision below is mine, and the reasons are written
down because nobody else chose them.

Baking is deliberately **out of this spec** — the animator said «а потом подумаем». What is in it
is a design that does not make baking harder later (see "Not built, and what it costs").

## Why a third attempt at slime

This is the third round on the same material, and the first two are in the repo:

- `docs/superpowers/plans/slime/slime_fx.py` (2026-10-28) — nParticles liquid, blobby mesh, baked
  through AbcExport, for `AS_Sword_Finisher_Creep_Disarm_and_Execute_1P`;
- `slime_spray.py`, the same day — its own docstring says why it exists: «nParticles' blobby mesh
  either clumps a spray into sausages or drops sparse particles», so the spray was hand-written as
  strands of points that stretch, tear and splat.

Both failed on the **material**, not on the plumbing: Maya's nParticles has no dial that says
"hold your shape a little, then flow thickly". That is the dial this prototype is built around,
and it is why the prototype is a **sandbox for the material** rather than a rebuild of the shot.
The shot comes back once the material reads right.

## Measured before choosing anything

In the Claude desktop app's own browser pane, served over `http://127.0.0.1` (a `file://` page
renders as a static snapshot there — no JavaScript):

- WebGPU **works**: Chrome 152.0.7977.167, `requestAdapter` and `requestDevice` both fine;
- the adapter is the **Intel Xe-LPG integrated GPU** — this is a hybrid-graphics laptop (the same
  machine whose panel DXGI will not duplicate, trap 314), so every number I measure is a
  pessimistic floor and the animator's own Chrome will be faster. The page asks for
  `powerPreference: "high-performance"` so a machine with a discrete card uses it;
- `atomicAdd` on `atomic<i32>` in a storage buffer compiles with no diagnostics;
- the limits that bound the design: `maxStorageBufferBindingSize` **134217728** (128 MiB per
  binding), `maxBufferSize` 268435456, `maxComputeInvocationsPerWorkgroup` **256**,
  `maxComputeWorkgroupStorageSize` 16384;
- `timestamp-query` is available, so the prototype measures its own GPU time instead of guessing
  from the frame rate.

**That I can drive a WebGPU browser is load-bearing for this build.** A fluid is judged by eye,
and a graphics change I cannot see is a change I cannot verify; here I can open the page,
screenshot it and read its console, so the build is checked the same way every other feature in
this repo is checked, rather than handed over untested.

## The solver: MLS-MPM

Moving Least Squares Material Point Method (Hu et al. 2018): the material lives on particles, a
background grid solves for pressure and self-collision.

Chosen over the two alternatives I considered:

- **Position Based Fluids + Clavet springs** (the 2005 "particle-based viscoelastic fluid" paper,
  which is literally about goo) — simpler, no grid, but the look is "water with a lag", the
  double-density relaxation is fiddly to tune, and viscoelasticity through explicit springs needs
  neighbour lists and gets sticky in a way that is hard to control.
- **FLIP with an implicit viscosity solve** (Batty & Bridson) — the honey look, done properly, but
  the variational viscosity solve is a large piece of work and the surface is harder.

MPM wins on three counts that matter here:

1. **The material is a formula, not a hack.** One solver, and water / honey / kissel / jelly / mud
   are four numbers apart. That is exactly the knob the two Maya attempts lacked.
2. **Incompressibility and self-collision come from the grid** for free — no neighbour search, no
   kernel radius to tune, no sorting.
3. It is **stable at large time steps** with the APIC/MLS transfer, which an explicit particle
   solver is not.

Its cost is written in the limits section: a grid cannot resolve a strand thinner than its own
cells.

## The material: elastic, with a yield point and viscous flow

A particle carries an elastic deformation gradient `F`. Each step `F ← (I + dt·C)·F`, then `F` is
decomposed and projected back toward a yield surface. In the Hencky (logarithmic) strain
`ε = log Σ` of the singular values:

```
eps   = log(S)                            S from the SVD of F
tr    = eps.x + eps.y + eps.z             volumetric part
dev   = eps - tr/3                        shear part
s     = 2·mu·|dev|                        deviatoric stress magnitude

if s > yield:                             von Mises, with viscous relaxation
    dgamma = (s - yield) / (2·mu + visc/dt)      # Herschel-Bulkley
    dev   -= dgamma · dev/|dev|
    eps    = dev + tr/3
    F      = U · diag(exp(eps)) · Vt      # the flow is permanent

P = U · diag((2·mu·eps + lam·tr) / S) · Vt       # first Piola, Hencky StVK
```

The three sliders fall straight out of it, and each one is a thing the animator can see:

| slider | symbol | what it does | water | kissel | jelly |
|---|---|---|---|---|---|
| **Elasticity** | `mu` | the jiggle, how springy | ~0 | low | high |
| **Yield** | `yield` | how much shape it holds before giving in | 0 | **high** | ∞ (never gives) |
| **Viscosity** | `visc` | how slowly it gives in once it does | 0 | high | — |
| Incompressibility | `lam` | how hard it resists being squashed | high | high | high |

**Yield is the kissel slider.** At yield 0 the deviatoric strain is projected away every step and
the material is a pressure-only fluid — water. At a high yield nothing is ever projected and it is
a solid jelly. Kissel is in between: a mound that holds, wobbles, and slumps when pushed.

Two deliberate details:

- the projection is **permanent** (the plastic flow is written back into `F`), which is what makes
  it flow rather than spring back. That is the difference between kissel and jelly, in one line;
- `visc/dt` in the denominator makes the giving-in **rate dependent**: pushed slowly it flows,
  pushed fast it resists. That is the Herschel–Bulkley shape, and it is why real slime snaps when
  you yank it and droops when you don't.

### The SVD is the fragile part, and it degrades instead of exploding

A 3×3 SVD per particle per substep, in WGSL, in f32. The implementation is Jacobi iteration on
`FᵀF` (symmetric, so it converges quickly), six sweeps, with the singular values clamped away from
zero; `U = F·V·Σ⁻¹`.

This is the one place the solver can produce a NaN, and a single NaN in MPM spreads to the whole
grid within a few steps through the P2G scatter. So: **after the update, a particle whose state is
not finite has its `F` reset to the identity and its velocity zeroed, and a counter is
incremented.** A blow-up then shows as "11 particles reset" in the panel instead of the entire
simulation turning to soup, and the counter is how I find out that a slider combination is
unstable rather than guessing from a frozen screen.

## The fixed-point grid, and why it makes the sim reproducible

P2G is a scatter: each particle adds mass and momentum to the 27 grid nodes of its quadratic
B-spline support. That needs an atomic float add, and **WGSL has `atomicAdd` only on `i32` and
`u32`** — there are no float atomics.

So the accumulation grid is `array<atomic<i32>>`, four entries a node (mass, and the three
momentum components), in **Q16.16 fixed point** (`×65536`, rounded). The budget, so the choice is
not a guess: a node is reached by at most 27 cells' worth of particles, ~8 particles a cell, each
with a weight ≤ 1 and a particle mass normalised to 1 — so mass per node ≲ 216 and momentum
≲ 216·v, with v in cells per second bounded by the CFL condition at a few tens. At ×65536 that is
~10⁸ against the 2.1·10⁹ an `i32` holds: an order of magnitude of headroom, and a precision of
1.5·10⁻⁵, which is far below anything visible in a grid accumulation.

The reason this is better than float atomics even if WebGPU had them: **integer addition is
associative and commutative, so the result does not depend on the order the particles land in.**
Two runs from the same seed give the same frame, bit for bit, however the GPU schedules the
workgroups. For a sandbox that is a nicety; for a bake it is the difference between a cache you
can re-render and one you cannot. It costs nothing to have it now.

## Buffers, and the one layout decision made for baking

| buffer | type | bytes/particle | 500k |
|---|---|---|---|
| `pos` | `vec4<f32>` — xyz in cell units, w spare | 16 | 8 MB |
| `vel` | `vec4<f32>` | 16 | 8 MB |
| `defo` | 3 × `vec4<f32>` — `F` | 48 | 24 MB |
| `affine` | 3 × `vec4<f32>` — `C`, the APIC velocity gradient | 48 | 24 MB |
| `jp` | `f32` | 4 | 2 MB |

**Position is a buffer of its own, not a field of one fat particle struct.** It is the one decision
in this spec taken for the bake rather than for the prototype: a contiguous position buffer is a
single `copyBufferToBuffer` + `mapAsync` away from a frame of a point cache, where a field inside a
132-byte struct would have to be de-interleaved on the way out. It also makes the render pass read
less. It costs nothing.

The grid is 16 bytes a node for the atomic accumulation plus a `vec4<f32>` velocity grid: at the
default 96³ that is 14 MB each, at the maximum 128³ 34 MB each — both well inside the 128 MiB
binding limit, which is what caps the grid at 128³.

Positions are in **cell units**, so the B-spline weights need no scaling, and one cell is declared
to be **1 cm**: the default 96³ domain is then about a metre on a side, which is the scale of a
character and a floor — the scale this slime is eventually for.

## The step

Per substep, four dispatches:

1. **clear** — zero the atomic grid.
2. **P2G** — per particle: quadratic B-spline weights over 3×3×3; scatter `w·m` and
   `w·(m·v + (stress + m·C)·dx)` where `stress = -dt·vol·4·P·Fᵀ` is the MLS-MPM affine force term.
3. **grid** — per node with mass: `v = p/m`, gravity, then the boundary conditions — floor, walls,
   the obstacle sphere and the mouse sphere — and write the float velocity.
4. **G2P** — per particle: gather `v`, build the new `C`, advect, update `F`, run the return
   mapping above, guard against NaN.

Substeps a frame are a slider (default 8) because the step size is what trades stability for speed,
and a prototype whose job is to be tuned should expose it rather than hide it.

**Wall stickiness is a slider too**, not a constant: a sticky boundary (velocity driven to zero at
the wall) is what makes slime cling to a floor and drag down a wall, and it is one of the most
visible parts of the look for the least code.

## What it looks like: screen-space fluid rendering

A cloud of points tells you nothing about whether a material reads as kissel, so the rendering is
part of the deliverable, not a garnish. The standard screen-space approach (van der Laan 2009):

1. particles as sprites writing an **analytic sphere depth**, and a second additive pass for
   **thickness**;
2. a **narrow-range filter** on the depth, separable, two passes — this smooths the surface without
   bleeding across silhouettes, which a plain blur does;
3. **normals from the filtered depth** by screen-space derivatives;
4. composite: Fresnel, a specular highlight, Beer–Lambert absorption through the thickness (so a
   thin film is pale and a deep pool is saturated), and a refracted background.

Behind it a floor with a grid, so the spread of a puddle and the height of a mound are readable.

Two debug views ship with it — **points** and **depth/normals** — because they are how a problem
gets diagnosed without the animator's eyes, and they cost a branch in one shader.

## The sandbox

What is in it is what is needed to judge the material and nothing else:

- a **blob** you can drop, and a **nozzle** you can hold open to pour a stream. A poured stream is
  the single most diagnostic thing on the list: a thick fluid landing on a floor coils into a rope,
  and if it coils, the viscosity is right;
- the **mouse as a sphere** that pushes and drags, so a strand can be pulled up out of a pool and
  let go. Ten seconds of that says more than any number;
- a **floor, walls and one sphere** to drape over;
- **presets** — Water, Honey, **Kissel**, Slime, Jelly, Mud — so the axis can be felt before the
  sliders are touched;
- **readouts**: fps, GPU ms (from `timestamp-query`), particle count, NaN resets, total mass.

Total mass and the NaN count are the self-test: mass is conserved by construction, so a drift says
the transfer is wrong, and both are visible on screen rather than buried in a console.

## Where it lives, and how it is opened

`docs/superpowers/plans/slime/web/`, beside the two Maya scripts that came before — which is where
somebody looking for the slime work will look. The repo's own rule puts a one-off here and not at
the root.

Plain `<script src>` tags and no ES modules, and the WGSL inlined in the JavaScript as template
literals, for one measured reason: in Chrome a `file://` page cannot `fetch` its own siblings and
cannot load `type="module"` scripts. A `serve.py` ships beside it (the pattern the chat page's own
folder already uses), and that is the supported road, but the page is written so that it has a
chance of working from a double-click too.

The files split by job, so each is small enough to hold in one piece:

| file | what it is |
|---|---|
| `index.html` | the page, the canvas, the panel |
| `sim.js` | the solver: buffers, the four dispatches, the step |
| `shaders.sim.js` | the WGSL for clear / P2G / grid / G2P, and the SVD |
| `render.js` | the screen-space passes |
| `shaders.render.js` | the WGSL for depth / thickness / filter / composite |
| `ui.js` | sliders, presets, readouts, mouse |
| `serve.py` | `python serve.py`, then open the address it prints |

## Not built, and what it costs

- **The bake.** The animator asked for the prototype first. The position buffer is laid out for it
  (above) and nothing else needs to change; the road I would take is the one I recommended in the
  conversation — the page writes a compact per-frame point cache, and a Maya-side importer builds
  the mesh and runs `AbcExport`, so Alembic is written by the library that already works rather
  than by hand in JavaScript.
- **Thin strands.** The grid cannot resolve a strand below ~2 cells (~2 cm at this scale). The
  surface is built from particles so strands *render* thinner than they simulate, but a hair-thin
  thread is not something this solver will do. An adaptive grid is the real answer and it is a
  feature of its own.
- **An implicit solver.** Explicit stepping with a substep slider instead. Implicit MPM would take
  larger steps on a stiff jelly, and it is a much larger piece of work.
- **Two-way coupling with a moving collider**, foam and spray, a marching-cubes mesh in the browser,
  Safari and mobile. Chrome only, and the page says so when `navigator.gpu` is missing.

## How it gets judged

By eye, on screenshots I take myself, against four behaviours that separate kissel from everything
else — and if it fails one of them the material model is wrong, not the tuning:

1. a poured stream **coils** on the floor instead of splashing;
2. a dropped blob **wobbles and holds a mound**, then slumps slowly, instead of flattening at once;
3. a pulled strand **thins and snaps**, and the pool it came from **heals**;
4. the fluid **clings** to a wall on the way down instead of sliding off it.

Plus mass conserved to a fraction of a percent over a thousand frames, zero NaN resets at the
preset settings, and a frame time the panel reports honestly on the integrated GPU it is being
measured on.

## Addendum: what was measured (2026-11-03)

The four behaviours above, judged on the integrated Xe at 13k particles on a 64 cell grid, the
Kissel preset. The mounds are read off the position buffer (every particle buffer is `COPY_SRC`,
which is the bake's own read path) rather than by eye.

1. **The stream coils** — but only after the nozzle was moved. It poured from 0.82 of the domain
   at 0.75 of it a second: the fluid arrives at the speed the CFL cap allows and splats into a
   flat torn puddle. From 30 cm at 6 cm/s the same kissel lays itself down in stacked folds. The
   height and the flow are sliders now; how far it falls is a thing about the shot.
2. **The mound holds**, by number — 98th-percentile height above the floor, and the radius holding
   90 % of the material: water **0.15 cm / 36 cm**, kissel **3.0 cm / 16 cm**, jelly
   **5.7 cm / 5.9 cm**.
3. **The strand snaps and the pool heals**: at hand radius 5, strength 0.75, the lift gave two
   lumps (an occupancy flood fill) at 33 cm, and one lump back at its settled spread 5 s after
   letting go. The hand is a sphere that drags, so the regime matters: wide and gentle carries the
   whole pool up without tearing, narrow and hard shreds it into patches that stay torn — which is
   what a yielded material does.
4. **It clings, and it does not hang.** Thrown at a wall, 31 % of it is still against the wall 6 s
   later at stickiness 0.6 against 0 % at 0.02; nothing stays above 12 cm either way. Hanging on a
   vertical wall wants the yield to beat gravity in a thin film — a much higher yield than a 3 cm
   mound holds.

And the one thing that was wrong with the page rather than with the fluid: the loop ran one more
time on every displayed frame (two `requestAnimationFrame` chains), so a minute in a single frame
carried thousands of solver steps. It never showed in the pane it was built in, where rAF does not
fire at all. The driver, the back pressure, the honest readout and the governor are written up in
CLAUDE.md with the numbers; after them it is 45 fps, 23 ms a frame, 9.2 ms of it the solver.

## Addendum: the sandbox after it was played with (2026-11-03)

Four things the animator asked for after using it, and what each cost:

- **the hand lands on the fluid.** It sat on a plane through the camera's target — almost never
  where the slime is — so a grab usually caught the air above a puddle. One texel of the filtered
  surface depth is read back on the press, and the hand goes to that distance along the cursor's
  ray; off the fluid it falls to the floor under the cursor. The grab profile is full through the
  middle of the hand and falls off over its outer third, instead of falling off from the very
  centre, which let the fluid slide out of a hand that was moving;
- **drag on exposed particles.** A splash threw spray to the ceiling and left it there, because
  nothing here slows a drop flying through air. G2P gathers the node masses alongside the
  velocities, so each particle knows how much material is around it, and the drag is scaled by how
  exposed it is: the body of the fluid is untouched. Water's splash peaks at 27 cm where it peaked
  at 93;
- **the obstacle is draggable, and it pushes.** A press is tested against the sphere before the
  fluid; the ball moves in the plane it was grabbed in, and its velocity goes to the solver, which
  is the difference between shoving the fluid (15.77 cm) and teleporting through it (0.02);
- **the domain is 96 cm by default, 128 available.** The grid passes skip the 4×4×4 blocks the
  fluid is nowhere near, and the separate clear pass is gone — solveGrid zeroes what it reads. A
  128³ domain now costs what 64³ did. What is left of the domain's cost is one thread and one flag
  read per node; removing that wants an indirect dispatch over a compacted block list, which is
  the real sparse MPM and is not built.

## Addendum 3: a character out of an FBX, holding the emitter (2026-11-03)

The animator: «и нужно добавить возможность настраивать эмитор. Вставлять fbx сцены и крепить
эммитор например к костям в фбиксе». Asked two questions before building:

- **how to read the FBX** — through Maya (their answer), rather than a JS reader or a hand-made
  format. The browser has no FBX reader; writing one is weeks for a format every exporter writes
  differently; Maya is on the machine this prototype is for and reads FBX for a living.
- **what a character is for** — «крепление + столкновения»: the bones both hold the emitter and
  push the fluid.

### The shape

```
the page  --POST /fbx/<name>-->  serve.py  --mayapy fbxread.py-->  Maya
                                     |
                                  <-- JSON: bones, capsules, a frame a frame
```

`fbxread.py` writes only what the sandbox can use, in centimetres (one cell):

| field | what |
|---|---|
| `bones` | name, parent, the capsule's radius, the tip in the bone's own frame, its length |
| `colliders` | which bones are worth colliding with: the 24 biggest by `radius² · length` |
| `frames` | a bone a row: its world place and the three columns of its rotation |

A UE walk is 91 bones × 84 frames = 770 KB of JSON, read in **5.4 s through the page's own
loader** — Maya's start is most of it.

`rig.js` plays it (two frames and a blend, the rotation columns left unnormalised: over a sixtieth
of a second the drift is nothing, and they only point the emitter and place a capsule's far end),
packs the capsules for the solver, and asks the server for a file.

### The decisions, and what each cost

- **Capsules in the uniform, not a storage buffer.** WebGPU promises eight storage buffers a stage
  and the solver uses every one of them; 24 capsules are three vec4 each, which the params buffer
  had room for. The solve projects a node out of the nearest point of the segment — the sphere
  code with the centre moved — and carries the bone's velocity, so a swing pushes.
  **Measured: 49.1 ms a frame with the capsules on and 49.1 with them off** (15k particles, grid
  96): the loop runs only on nodes that carry mass.
- **The character moves on the fluid's clock**, inside the fixed step, so a swing lands in the same
  place whatever the frame rate.
- **Fitted to the room on load.** A game character is 170 cm and the room is as many centimetres as
  the grid has cells. The clip's own height sets the scale (0.458 in a 96 room) and its first frame
  the place; the two sliders move both afterwards.
- **The emitter leaves the bone's far end, not its root** (trap 333): the root of a hand is inside
  the torso's capsule while the arm is down, and a jet seeded inside a collider dies there — a
  thousand particles a second went into the hip and a handful came out.
- **The capsules are drawn whether or not the fluid feels them**: «Столкновения» off means the
  solver is handed none, not that the character disappears.

### Measuring a limb with no skin

An animation clip carries no skin, so `_capsule`'s measurement (the vertices whose heaviest
influence is that bone, at the 70th percentile of their distance from the bone's axis) has nothing
to work on and the radius is a guess. The guess has to come off the skeleton, and two readings were
tried before the one that works — both wrong for the same reason, that they let a bone far from the
body decide how wide the body is:

| reading | pelvis | chest | why it is wrong |
|---|---|---|---|
| the bone's own length × 0.22 | 1.6 | 4.3 | a spine joint is 8 cm long and a chest is 30 across |
| the nearest left/right PAIR by height | 30.4 | 30.9 | at frame 0 of a walk the hands hang at hip height |
| the nearest sided bone in 3D | 11.3 | 18.0 | the same hands, nearer than the clavicles |
| **its own limbs, sideways** | **12.8** | **11.8** | only a limb the bone carries can say |

The last one: a midline bone is as wide as the horizontal gap to the limbs that grow out of it —
the pelvis to the hips, the chest to the clavicles — measured against the limb's middle as well as
its root, and a spine joint between them inherits from below. Sideways only, because a thigh's
middle is 20 cm DOWN the leg and the three-dimensional distance said the hips were 43 cm across.

A tip bone (a toe, a head) is as thick as the bone it hangs off; half its parent's LENGTH, which it
was first, made a toe an 8 cm ball on a 4 cm foot.

A **Толщина костей** slider scales every capsule, because all of this is a guess and the animator
can see what it should have been.

### Seen

- A blob dropped on the chest with the collisions ON breaks over the body and lands off-centre;
  with them OFF it falls as a clean column into a round puddle.
- The hand pours a streak along the floor as the character walks (`shots/rig_hand_pour.png`).
- The pour sees the hand moving **8–30 cells a second** and adds it to the jet.

### Not built

A mesh (the capsules are the character), more than 24 colliders, a character that the fluid can
push back, and the file picker's own dialog — which is the animator's to press.

