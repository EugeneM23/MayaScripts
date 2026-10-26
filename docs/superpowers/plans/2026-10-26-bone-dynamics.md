# Dynamics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** a hub card Dynamics that keeps joint chains, colliders and a wind arrow in the scene and bakes
their secondary motion onto one additive layer per chain, looped when asked.

**Architecture:** a pure numpy solver (`maya_dynamics/model.py`: tail particles, Verlet, lengths by
construction, sphere / capsule / plane colliders, harmonic wind, periodic steady state) under a scene
half that reuses Overlap's chain discovery and frame-to-delta conversion and `layerbake.write_deltas`.
Spec: `docs/superpowers/specs/2026-10-26-bone-dynamics-design.md`.

**Tech Stack:** Maya 2027 Python 3, numpy, `maya.cmds`, OpenMaya 2.0 callbacks; tests with stdlib
`unittest` under `mayapy` (`& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v`, from the repo root).

## Global Constraints

- `model.py` imports numpy and the stdlib only (a subprocess test pins it).
- Units cm, s, degrees; gravity and wind strength in g (1 = 980 cm/s²).
- Row vectors (Maya's): `world = local @ parent`, a frame's rotation in rows 0-2, its pivot in row 3.
- A press is one undo chunk (`knots._press`), autoKey off, the time put back; a refusal changes nothing.
- Names a scene node or attribute carries start with `skeldar` (Delete character's prefix rule).
- Every new scene lookup goes through `maya_scenetabs.scope.active_only`.
- Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; stage only this work's
  files (other sessions have uncommitted changes in the tree).

---

### Task 1: the solver's pieces (`model.py`, part 1)

**Files:** Create `SkeldarAnim/maya_dynamics/__init__.py`, `SkeldarAnim/maya_dynamics/model.py`;
Test `tests/test_dynamics_model.py`.

**Produces:**
- `G = 980.0`; `KNOBS` (key, low, high, default, has_tip); `DEFAULTS` dict; `PRESETS` {name: dict};
- `settings(given=None) -> dict` (defaults filled, values clamped, tips `<key>_tip`);
- `ramp(root, tip, n) -> ndarray (n,)` (`root * (1 + (tip - 1) * i / (n - 1))`);
- `spring_k(stiffness) -> float` (`(2π · 0.3 · 20^s)²`, 0 at 0);
- `turn_between(a, b) -> (..., 3, 3)` row-vector rotations taking unit `a` onto unit `b`;
- `clamp_cone(d, axis, limit_rad) -> d'`;
- `sphere_push(p, r, centre, cr)`, `capsule_push(p, r, a, b, cr)`, `plane_push(p, r, origin, normal)`
  each `-> (pushed p, touching mask, normal)`;
- `noise(t, phase, freq, period, seed, channel) -> ndarray`.

- [x] **Step 1: tests** - `settings({})` equals `DEFAULTS`; a stiffness of 7 clamps to 1; `ramp(2, 0.5, 3)` is
  `[2, 1.25, 0.5]`; `turn_between` maps a to b for random pairs and opposite pairs; `clamp_cone` leaves a
  direction inside the cone alone and puts one outside on its edge; each push moves a point inside to the
  surface plus its radius and leaves one outside alone; `noise` with `period` P is periodic in t and has RMS
  ≈ 1 over a period; the module imports nothing but numpy / stdlib (subprocess).
- [ ] **Step 2: run, see them fail.**
- [ ] **Step 3: implement** (Rodrigues for `turn_between`: `v = a×b, c = a·b`, column form `I + [v]× + [v]×² /(1+c)`,
  transposed for rows; `c < -1 + 1e-9`: a half turn about any perpendicular).
- [ ] **Step 4: run, see them pass. Step 5: commit.**

### Task 2: the simulation (`model.simulate`, no loop)

**Produces:**
- `ChainInput(frames (n,T,4,4), carrier (T,3), settings dict)`;
- `Collider(kind "sphere"|"capsule"|"plane", a (T,3), b (T,3), radius (T,), normal (T,3), enabled (T,))`;
- `WindInput(direction (T,3), strength (T,), turbulence (T,), gust (T,), frequency (T,), seed int)`;
- `simulate(chains, colliders=(), wind=None, fps=30.0, substeps=4, loop=False, preroll=0) -> (outs, info)`
  where `outs[c]` is the chain's new frames (n, T, 4, 4) and `info` {"cycles", "settled", "ignored"}.

The step (every tail at once, flattened over the chains, a parent index per joint):
1. `v = (p - prev) * (1 - damping) ** (30 * dt)`; `p += inertia * dc; prev += inertia * dc`;
2. `q = p + v + (gravity + wind * exposure) * dt²`, exposure `1 - |dot(dir, wind dir)|`;
3. target `t = parent_q + L * (d_anim @ T_parent)`; `q += (t - q) * (1 - exp(-k dt²))`;
4. `dir = normalize(q - parent_q)`, cone-clamped about the target direction;
5. positions rebuilt root to tip from the pinned pivot and `L * dir` (cumulative, per chain);
6. two passes: colliders push (skipping the pairs inside at the first frame), friction moves `prev`
   toward `p` along the surface, the positions rebuilt again.

Out: `R_new = R_anim @ turn_between(d_anim, d_sim)`, the pivot of member i>0 at the simulated tail of
member i-1. Inputs interpolated linearly between frames for the substeps.

- [ ] **Step 1: tests** - (a) a chain with gravity 0, wind none, a still animation stays on the animation to
  1e-9; (b) gravity 1, stiffness 0, a horizontal chain hangs straight down after 300 frames (every direction
  within 1° of -Y); (c) lengths equal the animation's on every frame to 1e-6; (d) stiffness 1 keeps a
  gravity-1 chain within 15° of its pose, stiffness 0 lets it hang; (e) limit 20 keeps every joint within
  20.5° of its animated direction; (f) damping 0 still swings after 120 frames where 0.5 has stopped;
  (g) a sphere under a hanging chain: no tail inside it; the floor plane: no tail below it; a capsule the
  same; (h) 4 and 16 substeps agree within 1 cm of a 30 cm chain's tip; (i) wind along +X pushes the tip
  toward +X; a chain pointing along the wind is not pushed; (j) a root that jumps 50 cm along X: with
  inertia 1 the chain keeps its shape, with 0 it lags; (k) preroll 30 lets a chain start sagged; (l) a tail
  inside a collider at the first frame ignores it (`info["ignored"]`).
- [ ] **Steps 2-5** as Task 1.

### Task 3: Loop

**Produces:** `repeats_first(frames_list, carrier, tol=1e-3) -> bool`; `cycle_travel(carrier, repeats) -> (3,)`;
`simulate(..., loop=True, travel=None)` runs the cycle until the tails at its start move less than
`SETTLE_CM` 0.01 between cycles (≤ `MAX_CYCLES` 8), records one more, spreads the miss
(`exp(-miss * f / T)` on every direction), `info["cycles"]`, `info["settled"]`.

- [ ] **Step 1: tests** - a pendulum chain under a swinging root, Loop: the step from the last frame to the
  first (directions) no larger than the largest step inside the cycle × 1.5; `info["settled"]` True within
  8 cycles at damping 0.2; damping 0 reports not settled when it does not; wind is periodic (noise at t and
  t + P equal); a closed range (last = first + travel) is detected; travel extrapolated otherwise.
- [ ] **Steps 2-5** as Task 1.

### Task 4: shared writers (`overlap.deltas_for`, `layerbake.write_deltas(layer=)`)

**Files:** Modify `SkeldarAnim/maya_tools/overlap.py` (`_chain_deltas` split), `SkeldarAnim/maya_tools/layerbake.py`;
tests in `tests/test_tools_overlap.py` / `tests/test_tools_layerbake.py` (existing modules).

**Produces:**
- `overlap.deltas_for(chain, data, frames, new, out, weights) -> {(node, ch): values}` - `_chain_deltas`'
  body after the solve, unchanged behaviour;
- `layerbake.write_deltas(..., layer=None)`: an existing layer's curves for `tracks`' plugs cleared
  (`cutKey`) and keyed again, its weight / mute untouched; plugs of the layer not in `tracks` removed
  from it.

- [ ] Steps: the existing Overlap tests stay green; a fake-cmds test that `layer=` reuses the layer and
  clears its keys; commit.

### Task 5: the setup (`setup.py`)

**Produces** (markers as in the spec): `group_for(node)`, `chains()`, `chain_of(node)`, `members(chain)`,
`read_settings(chain)`, `write_settings(chain, s)`, `add_chains(selection) -> (chains, notes, refusal)`,
`remove(chain) -> layer name or None`, `colliders(group)`, `add_collider(kind, bone) -> path`,
`auto_body(node) -> (paths, refusal)`, `add_floor(node) -> path`, `wind()`, `add_wind() -> path`,
`redraw(collider)`, `layer_of(chain)`, `layers_of(chains)`, `carrier_of(node)`.

- [ ] Steps: fake-cmds unit tests for names, the settings round trip and refusals; the scene behaviour
  is proven in Task 8's verify; commit.

### Task 6: the press (`run.py`)

**Produces:** `simulate(chains=None, highlight=SLIDER, given=None, progress=None) -> line`;
`read(chains, frames) -> data` (one walk, our layers muted, cached on `sys._skeldar_dynamics` and
dropped by the key-edit / undo / redo / scene callbacks); `inputs(...)` to the model; the layer written
per chain (`Dynamics_<root leaf>`, `skeldarDynamics` = the chain's UUID, reused when standing).

- [ ] Steps: fake-cmds tests for the range, the line and the refusals; the bake proven in Task 8; commit.

### Task 7: the card and the hub

**Files:** Create `SkeldarAnim/maya_dynamics/panel.py`; Modify `SkeldarAnim/maya_hub.py` (section),
`SkeldarAnim/maya_hotkeys.py` (rows), `SkeldarAnim/maya_hubicons.py` (`wind`), `SkeldarAnim/install.py`
(payload row); Test `tests/test_dynamics_panel.py`, the hub / hotkeys / payload tests.

- [ ] Steps: the card builds on a fake cmds with every control the spec lists; a released knob writes the
  picked chains' settings and calls `run.simulate` for the baked ones; presses call through; commit.

### Task 8: proof and record

**Files:** Create `docs/superpowers/plans/verify_dynamics.py`; Modify `CLAUDE.md`.

- [ ] mayapy standalone: a prop chain under a keyed parent, an FK finger chain on Manny_Rig, a capsule, a
  floor, the wind; the layer plays the solver's frames to 0.001°; base untouched; a re-simulation keeps the
  layer and its weight; Loop's seam; one undo; Remove; Delete character takes the group.
- [ ] the whole unit suite; CLAUDE.md section; commit.

## What the build changed in Tasks 1-3 (2026-10-26)

Done and committed: `maya_dynamics/__init__.py`, `model.py`, `tests/test_dynamics_model.py` (35 tests).
The step differs from the plan's in three places, each measured:

- **Lengths are solved root to tip, not Jacobi.** Each direction was read from the parent's
  UNPROJECTED point, so points falling together kept their shape: a horizontal chain under gravity
  hung by its first joint only, the rest held horizontal for ever. `project` now walks member index
  by member index (vectorised across chains): pull toward the animated direction from the parent's
  NEW place, cone, length.
- **`RELAX` (4) equal-mass length passes before it.** Plain follow-the-leader moves only the child of
  every bone: measured, a dropped chain gained energy at 16 substeps (1.6e6 against a start of 0) and
  4 against 16 substeps differed by 44 cm over 2 s. Mueller 2012's velocity fix was tried and damped
  a gentle swing harder than no fix. With the passes: stable at every substep count, 6.7 cm.
- **Contacts are solved exactly inside that walk.** A push followed by the length took most of the
  push back (0.055 cm left in a resting contact after 3 passes); `_onto` puts the tail on the circle
  where the bone's length sphere meets the collider's sphere (round the capsule's nearest axis point)
  or plane, nearest to where it was: 0.0 cm, lengths to 5e-15.
- The damping test measures a hanging chain given one push (Damping 0 still swings 5 cm at 7 s, 0.5
  is still): a chain dropped from horizontal loses most of its energy in the snap at the bottom, as
  every position-based solver does.
- `turned(v, a, b)` applies the least rotation without building its matrix (the parent's turn on the
  child's goal, every member index of every substep). 10 chains x 8 joints x 230 frames x 4
  substeps with a capsule and wind: ~2.5 s.

Next: Tasks 4-8 as written above.
