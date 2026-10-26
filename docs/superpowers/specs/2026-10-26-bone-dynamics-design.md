# Dynamics: secondary motion for joint chains, with colliders, wind and loops (2026-10-26)

The animator: «Давай сделаем свою систему кинематической симуляции для костей чтобы мы могли удобно
анимировать всякие висюльки и ткань на костях. Система должна включать в себя коллайдеры, возможность
зациклить анимацию, ветер и разные настройки гибкости и тд.» The research behind it:
`2026-10-26-bone-dynamics-research.md`.

Asked, and answered (all four the recommendation):
- **any chain by the selection** - bones of a skeleton or FK controls of a rig (Overlap's road);
- **a setup kept in the scene and baked again** - chains, their settings and the colliders stay on
  the character; a released slider re-simulates;
- **colliders automatic on the body plus by hand** - capsules fitted to the skinned mesh, a floor,
  spheres / capsules on any bone;
- **wind as an arrow in the scene** - one for the scene, its channels keyable, each chain its own
  response.

The approach (of three): **our own numpy solver** (the VRM / Dynamic Bone / Kawaii model), not Maya's
nHair and not Overlap with springs.

## 1. Where it lives

- A hub section **Dynamics** (key `dynamics`, group Animation, after Tail Builder, Tabler icon
  `wind`, new in `maya_hubicons`); hotkey rows `window.dynamics`, `dynamics.simulate`,
  `dynamics.add_chain`.
- Package `SkeldarAnim/maya_dynamics/` (a payload row):
  - `model.py` - numpy + stdlib, no Maya (a subprocess test pins it): the solver, wind noise, loop
    machinery, presets, settings;
  - `setup.py` - the scene objects: chains, colliders, the wind arrow, the Dynamics group;
  - `run.py` - the press: reading the animation, solving, writing the layer;
  - `panel.py` - the card.
- The scene half reuses Overlap's (`maya_tools/overlap.py`): `chain_from` (through AdvancedSkeleton's
  FKX joints and offset groups), the member refusals, the frame sampling and `_chain_deltas`'
  conversion of new world frames into rotate / translate deltas; `layerbake.write_deltas` writes them.

## 2. The setup in the scene

- **The Dynamics group**: a locked transform `Dynamics` marked `skeldarDynamicsGroup`, in the
  chain's character group (`chargroup.park`; a chain of no character: at world level). It holds the
  chains, the colliders' spaces group and the floor; Delete character takes it whole.
- **A chain** `<root leaf>_dyn`: a transform with no shape in the Dynamics group, marked
  `skeldarDynChain`, holding:
  - `skeldarDynMembers` - the members' UUIDs, root first;
  - `skeldarDynSettings` - its settings as JSON (`model.settings` fills what is missing);
  - `skeldarDynCarrier` - the UUID of the node whose travel Inertia removes: the rig's `Main`, else
    the skeleton's top joint, else the chain root's top ancestor.
  **+ Chain**: every selected node a root (Overlap's Hierarchy rule: the one node of its kind below,
  step by step; a branch ends it). A root already in a chain selects that chain instead. A chain whose
  root lies under another chain's member is refused (chains on chains are not v1).
- **A collider** `<bone leaf>_dynSphere1` / `_dynCapsule1` / `Floor`, marked `skeldarDynCollider`
  = its kind:
  - a sphere or capsule hangs in a **dynamics space** of its bone (`weaponspace.ensure_marked_space`,
    marker `skeldarDynSpace`, group `DynamicsSpaces` (marked) in the Dynamics group, suffix
    `_dynSpace`): a transform following the bone with no offset, so the collider's own t / r / s are
    its offset in the bone's axes and the animator may move it;
  - attributes `radius` (cm) and `length` (cm, a capsule's segment, 0 a sphere), in the Channel Box;
    the segment runs along the collider's local X, centred; the radius is multiplied by the mean of its
    world Y / Z scale, the length by its world X scale;
  - drawn as curves (three rings and the cap arcs, the Tools palette's teal), redrawn when the card
    changes its radius or length and at every press (`setup.redraw`);
  - a plane (`Floor`): a transform in the Dynamics group, its local Y the normal, drawn as a square;
  - `enabled` (bool, keyable).
- **Auto body**: on the selected character (any convention through `maya_skeletonmap.recognize`):
  capsules for pelvis, spine low, spine high, head, upper arms, forearms, thighs, calves - Ragdoll's
  `BODIES` axes (`plan.axis_points`) and radii (`plan.radius` over `sim.skinned_points`), a second
  press replacing the ones it made (marked `skeldarDynAuto`), the floor at the lowest skinned sole
  point when none stands.
- **Which colliders a chain uses**: every enabled collider of its Dynamics group and every plane at
  world level. A joint whose tail starts INSIDE a collider at the first simulated frame ignores that
  collider (a skirt root inside the pelvis capsule is authored there; the Ragdoll's rule for bodies
  already touching).
- **The wind** `Wind`: one transform at world level (in the active scene tab), marked `skeldarDynWind`,
  an arrow along its local +Z; keyable `strength` (in g: 1 = as strong as gravity), `turbulence`
  (0..1), `gust` (0..1), `frequency` (Hz), `seed`. **+ Wind** makes it in front of the camera, or
  selects it. Read per frame with `getAttr(time=)` (plain curves) and its world matrix in the walk.

## 3. A chain's knobs

| Knob | Unit, range, default | Meaning | Tip |
|---|---|---|---|
| Stiffness | 0..1, 0.3 | the pull back to the animated direction: a spring of `0.3 x 20^s` Hz (0: none) | × |
| Damping | 0..1, 0.2 | the share of a tail's velocity lost each 1/30 s | × |
| Limit | deg 0..180, 180 | the most a joint swings off its animated direction (the cage) | × |
| Gravity | g, -2..4, 1 | gravity, 1 = 980 cm/s² | - |
| Inertia | 0..1, 0 | how much of the carrier's travel the chain does not feel | - |
| Wind | 0..4, 1 | the chain's response to the wind arrow | × |
| Radius | cm 0..50, 1 | each joint's sphere against the colliders | × |
| Friction | 0..1, 0.3 | velocity lost along a collider while touching | - |

- **Tip ×** (a field after the slider): the knob at the chain's last joint is its value times the tip;
  the joints between get the root's value times `1 + (tip - 1) * (i / (n - 1))`.
- **Presets**: Hair, Cloth, Chain, Tail, Stiff (values in `model.PRESETS`).
- Chain-wide: **Substeps** 4 (1..16), **Tip joint** on (a virtual joint past the last, so the last
  joint swings too: the bone before it carried in the last joint's axes).

## 4. The solver (`model.py`)

- Points: each joint's TAIL (the next member's pivot; the last's the virtual tip). The root's pivot is
  pinned to the animation. Units cm, s; `dt = 1 / (fps * substeps)`; all chains of a press batched
  (padded arrays) and vectorised over joints and chains.
- A substep, every tail at once:
  1. inertia: `v = (p - prev) * (1 - d)^(30 dt)`; carrier travel (`i * Δc`) added to `p` and `prev`;
  2. forces: gravity and wind as accelerations, `p += v + a * dt²`; the wind times the bone's exposure
     `1 - |dot(bone, wind dir)|` (a bone along the wind is not pushed);
  3. stiffness: toward the target `t = P_parent + L * d_anim @ T_parent` (the animated direction
     carried by the parent's correction, VRM's rule) by the exact share `1 - exp(-k dt²)` with
     `k = (2π f)²`;
  4. limit: the direction clamped into the cone of `limit` degrees about the target direction;
  5. lengths: directions from the parents' positions this substep, positions rebuilt root to tip by
     cumulative sums of `L * dir` (lengths exact by construction);
  6. colliders, 2 iterations: sphere, capsule (closest point on the segment), plane; a tail inside
     pushed out along the normal by the overlap, then the lengths again; a touching tail's velocity
     along the surface reduced by Friction (through `prev`).
- Out: each member's new world rotation = its animated rotation turned by the least rotation from its
  animated direction onto its simulated one (`anim @ T`); twist about the bone stays the animation's;
  the pivot stays animated (lengths kept). Translate deltas only where a member is not the DAG child of
  the member above (Overlap's rule).
- Colliders and the carrier are read per frame and interpolated linearly (positions, axes) between
  frames for the substeps.

## 5. Wind

- `wind(t, p)` = strength × [dir × (1 + gust × n_slow) + turbulence × (n_x, n_y, n_z) across dir],
  in g, times 980.
- The noise: a sum of seeded harmonics of a period P, from 0.5 to 2 × `frequency`, the phase shifted
  by `dot(p, dir) / c` (c = 300 cm/s: gusts sweep along the wind) plus a per-joint phase from its rest
  position, so strands do not wave in lockstep. `n_slow` the same at a fifth of the frequency.
- P is the loop's cycle in Loop mode (so the wind is periodic), else the whole simulated span.
- The arrow's channels are read on every frame (a keyed strength ramps the wind).

## 6. Range, pre-roll, loop

- The range: the time slider's highlight, else the playback range (`knots._highlight`).
- **Pre-roll** (frames, 30): without Loop the simulation starts that many frames early holding the
  range's first frame, at rest (zero velocity), so frame 1 is a settled chain, not a snap.
- **Loop** (a chip): the range is one cycle, frame `last + 1` ≡ `first`. When the range's last frame
  repeats its first (every sampled matrix equal, less the carrier's travel) the period is
  `last - first` and the last frame is written as the first. The solver:
  1. runs the cycle again and again from the animated pose, moving the state back by the cycle's
     travel at each wrap, until the tails at the cycle's start move less than 0.01 cm between cycles
     (at most 8 cycles; the line says when it did not settle);
  2. records one more cycle and spreads what is left between its end and its start linearly over the
     cycle (per joint, the rotation's log - Walk Builder's `miss * f / n`), so the last frame flows into
     the first;
  3. the layer's curves cycle (pre / post infinity).

## 7. The bake

- One additive layer per chain, `Dynamics_<root leaf>` (marked `skeldarDynamics` = the chain's UUID,
  rotation by component), written by `layerbake.write_deltas` - extended to take an existing `layer`
  whose curves it clears first, so a re-simulation keeps the layer's place, weight and mute.
- Every frame of the range keyed (spline); a range inside the take zero one frame outside it
  (Overlap's rule); the members' other layers untouched.
- **Reading**: one `timewalk.Walk` over the range (+ pre-roll) per press, with every Dynamics layer of
  the chains being simulated MUTED for the walk and put back - a re-simulation must not read its own
  result. The walk is cached per chain set and range on `sys` and dropped when Maya reports a key edit
  (`MAnimMessage` callback, ignored while we write), an undo / redo or a new scene - so a slider
  release re-solves in a fraction of a second.
- **Simulate**: the chains picked in the card's list, else the chains of the selection's character,
  else the selection's chains. **Remove**: the picked chains' layers and setups (their colliders stay).
  One undo chunk a press, autoKey off, the time put back, Scene Time Warp handled by the walk.
- Refused before anything changes: a member constrained or driven by anything but time curves and
  animation layers (Overlap's `_member_refusal`), every rotate locked, a member chain with no length,
  nothing to simulate.
- The line: «hair_01: 6 joints, frames 0-60, 4 substeps, 3 colliders, wind - Dynamics_hair_01 | Loop
  settled in 3 cycles».

## 8. The card

Top down, the hub's marks:
- the subtitle (what Simulate would act on);
- heading **Chains**: the list of the active tab's chains (`textScrollList`, multi-select; a row
  «hair_01 · 6 · baked»), picking one selects its root and shows its knobs; **+ Chain**, **Remove**;
- the presets as a fill row; the knob rows (label, slider + field, Tip × field); a released knob
  writes every picked chain's settings and re-simulates those already baked;
- heading **Colliders**: **Auto body**, **+ Sphere**, **+ Capsule**, **+ Floor**; with a collider
  selected its **Radius** and **Length** fields;
- heading **Wind**: **+ Wind**; Strength, Turbulence, Gust, Frequency edit the arrow's channels at the
  current frame (a key there when they are keyed);
- heading **Bake**: Loop chip, Pre-roll, Substeps; **Simulate** (the one orange); the status (3 lines).
- Without Qt it is the classic hub's plain controls. The hidden card refreshes when shown
  (`maya_hubqt.seen_only`); its jobs (SelectionChanged, Undo, Redo) per card, parented to its status
  line.

Interface checklist (docs/interface-motion.md §8) - the card is cmds controls under the hub's skin:
- [x] Colours from `TOKENS` only, one orange per section, lengths × `ui` - the hub's marks.
- [x] The data changes at once; nothing on the card animates on its own.
- [x] Hover / press / toggle - the hub's own on its controls.
- [x] Interface animations off - nothing of ours to switch.
- [x] Unit tests offscreen on a fake cmds; «not seen in a GUI Maya» until the animator tries it.

## 9. Proof

- `tests/test_dynamics_model.py`: a chain hangs straight down under gravity from any start; lengths
  exact on every substep; Stiffness 1 holds the animated pose, 0 lets it hang; Limit caps the swing;
  damping 0 rings longer than 0.5; a sphere, a capsule and the floor push a tail out and it rests on
  them; the friction; the same result within 1 % at 4 and 16 substeps and at 24 and 30 fps; wind
  pushes along its arrow, a bone along the wind is not pushed, the noise is periodic in Loop; Loop's
  frame `last` flows into `first` (the step across the seam no larger than the cycle's largest);
  Inertia 1 removes the carrier's travel; a chain at rest under a still animation stays at rest.
- `tests/test_dynamics_setup.py`, `test_dynamics_panel.py` on fake cmds.
- `docs/superpowers/plans/verify_dynamics.py` (mayapy standalone): a prop chain under a moving parent
  and a rig's FK chain (a tail made of FK controls on Manny_Rig is not shipped: an FK finger chain
  stands in), a capsule on a bone the chain swings into, a floor, the wind; the baked layer plays what
  the solver said to 0.001 deg; the base untouched; a second Simulate replaces the curves and keeps the
  layer's weight; Loop's seam; one undo; Remove; Delete character takes the group.

## Addendum: what the build changed (2026-10-26)

- **The step (§4, 5-6) is not Jacobi.** Read from the parents' UNPROJECTED points, the directions of
  points falling together never turned: a horizontal chain hung by its first joint only. The lengths
  are now four equal-mass Gauss-Seidel passes (`RELAX`), then the exact follow-the-leader projection
  root to tip, one member index at a time across every chain (pull, cone, length from the parent's
  NEW place). Plain follow-the-leader gained energy at 16 substeps and differed by 44 cm between 4 and
  16 substeps over 2 s; Mueller 2012's velocity fix was tried and damped a gentle swing harder than
  nothing. With the passes: stable, 6.7 cm.
- **Contacts are solved inside that walk, exactly**: the tail onto the circle where its bone's length
  sphere meets the collider's sphere (round the capsule's nearest axis point) or plane, nearest where
  it was (`_onto`). A push and then the length took most of the push back (0.055 cm left in a resting
  contact after 3 passes); now 0.0 cm, the lengths to 5e-15.
- **Dynamics spaces stand where the weapon spaces do** (`weaponspace.ensure_marked_space`): in the
  rig's AdvancedSkeleton group, else the character group, else at world level - not in the Dynamics
  group. Delete character takes them either way. **A chain collides with its character's colliders
  and those of no character.**
- **The carrier**: a rig's Main, else the top joint ABOVE the chain's root, else the root's top
  ancestor - a joint chain hanging from a prop took its own root (the topmost joint) and Inertia would
  have removed the chain's whole motion.
- **The reading**: Simulate always reads afresh; a released knob re-solves the last reading
  (`reuse=True`). It is dropped by a key edit, an undo, a redo, a new or opened scene, a time unit change.
- **Loop's input** is decided for every chain together: a range whose last frame repeats its first
  (that frame is the next cycle's first), else the frame after the range when it repeats the first less
  the travel (cycled curves), else the first frame moved on by the range's travel. The layer keys the
  cycle's first frame again at its end, so its curves cycle with the right period.
- **The range** is the highlight, else the playback range (not the animation range).
- **Remove** also deletes Maya's BaseAnimation when it was left empty (Scene Tabs' roots never).
- Proof: 78 unit tests (`test_dynamics_model` 35, `_setup` 18, `_run` 11, `_panel` 10, `_writers` 4);
  `docs/superpowers/plans/verify_dynamics.py` **39/39 mayapy standalone**. Not seen in a GUI Maya.
