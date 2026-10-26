# Gait Builder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status (2026-10-26, paused and handed over):** Tasks 1-5 done; 7 implemented without its unit test; 8 written but never run; 6 and 9 open. Read the spec's "Status at the pause" (docs/superpowers/specs/2026-10-26-gait-builder-design.md) first: what exists, the gate results, the diagnoses and the ordered next steps. Task 2's 0.35 s became "<= 0.35 s or <= 45 % of Walk Builder's CPU time in the same run" (reached: 43-45 %).
**Second session (paused again):** "Next" 1-2 done - readback 172/172; see the spec's "Second session" section for
what changed and what is open (the calibration's cost first).

**Goal:** One standalone walk tool whose knobs are measured aspects of the clip in physical units (CAT's
language) over Walk Builder's engine (clip, planted feet, balance, inertia, poses), faster and without knee
clicks.

**Architecture:**
- `gaitmodel.py` is a fork of `SkeldarAnim/maya_walk/model.py`: the same model, faster, with operators for the
  new aspects. Every new internal knob defaults to "no change", so the fork with Walk Builder's knobs is Walk
  Builder.
- `aspects.py` measures a cycle in units, holds the knob table, and turns the animator's units into the fork's
  knobs.
- `gaitgen.py` makes a CAT preset into a clip.
- `skeldar_gait.py` is the Maya window.

**Tech Stack:** Python 3 in mayapy (Maya 2027), numpy, maya.cmds; unittest. The plugin's `maya_walk` (files,
clean, meanpose, pose, target, scene readers and writer) and `maya_poselib` are used as they are.

## Global Constraints

- Nothing in `SkeldarAnim/` changes.
- The files live in `docs/superpowers/plans/gaitbuilder/`.
- Unit tests in `tests/test_gait_*.py` run with: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -p "test_gait*"`.
- Identity: aspects at their measured values with the physics off give the clip (≤ 1e-4 cm).
- Parity: the fork with Walk Builder's knobs gives Walk Builder's result (≤ 1e-6) before a helper fix.
- Speed: ≤ 0.35 s for one evaluation of asd at the defaults, best of three, mayapy.
- Knee clicks (the knee's second difference within 25° of straight) ≤ max(1.5 × the clip's own, 12 deg/frame²)
  over the main knobs' ranges.
- Read-back: within 15 % of the asked change, or 1 unit.
- Effect: ≥ 5° or 3 cm rms on its body part over the range.
- Redundancy: no two knobs' signed effects correlated above 0.85.

## File Structure

| file | responsibility |
|---|---|
| `docs/superpowers/plans/gaitbuilder/gaitmodel.py` | the fork: analyse a clip, evaluate knobs into a cycle |
| `docs/superpowers/plans/gaitbuilder/aspects.py` | the knob table, `measure`, `engine_knobs`, the speed law |
| `docs/superpowers/plans/gaitbuilder/gaitgen.py` | a CAT preset → (Clip, statics) |
| `docs/superpowers/plans/gaitbuilder/gaitload.py` | a source (saved walk, card, preset) → analysed walk + statics; the baseline cache |
| `docs/superpowers/plans/gaitbuilder/skeldar_gait.py` | Maya window and presses |
| `docs/superpowers/plans/gaitbuilder/verify_gait.py` | mayapy standalone verification |
| `docs/superpowers/plans/gaitbuilder/gates.py` | the measured gates on real walks (identity, read-back, effect, redundancy, helpers, speed) |
| `tests/test_gait_model.py`, `tests/test_gait_aspects.py` | unit tests on the synthetic walker |

### Task 1: The fork, at parity

**Files:**
- Create: `docs/superpowers/plans/gaitbuilder/gaitmodel.py` (a copy of `SkeldarAnim/maya_walk/model.py`, its
  docstring saying it is the fork)
- Test: `tests/test_gait_model.py`

**Interfaces:**
- Produces: `gaitmodel.analyse(clip) -> Walk`, `Walk.evaluate(given, pose) -> Result`, `gaitmodel.KNOBS`,
  `knobs()`, `Clip`. Identical API to `maya_walk.model`.

- [x] Step 1: Copy the module.
- [x] Step 2: Test: the synthetic walker of `tests/test_walkmodel.py` evaluated by both modules at the defaults,
  at `own_knobs()`, at stride 1.3 and at ground time 1.2 is the same to 1e-9.
- [x] Step 3: Run, pass, commit.

### Task 2: Speed

**Files:** Modify `gaitmodel.py`. Test `tests/test_gait_model.py`.

- [x] Step 1: `exp_rot` takes `_exp3` for a single vector.
- [x] Step 2: Profile asd with `prof.py` against the fork.
- [x] Step 3: Optimise the top entries, keeping the parity test at 1e-9:
  - `_skew` / `align` / `_frame` in plain floats;
  - `periodic_cr` on precomputed coefficient tables;
  - the balance rounds running the arms' springs again only when the carry moved by more than `CARRY_TOL`.
- [x] Step 4: Gate: ≤ 0.35 s on asd at the defaults. Where an approximation is needed (the arms between
  rounds), name it and measure it on asd, dw, HavyRun against the exact fork (≤ 0.05 cm, ≤ 0.1°).
- [x] Step 5: Commit.

### Task 3: Aspect measurement

**Files:** Create `aspects.py`. Test `tests/test_gait_aspects.py`.

**Interfaces:**
- Produces: `measure(walk, worlds) -> dict` (units below) where `walk` is an analysed `gaitmodel.Walk` and
  `worlds` (J, n+1, 4, 4) a closed cycle laid on its strides by `f * walk.P / n`. Keys:
  - `speed` m/s, `step` cm, `cadence` steps/min, `duty` %;
  - `bob`, `sway`, `surge` cm;
  - `hips`, `hip_drop`, `lean`, `chest_twist`, `chest_sway`, `chest_bounce` deg;
  - per side `{"l": ..., "r": ...}`: `arm_swing`, `elbow`, `elbow_swing`, `arms_forward`, `arm_out` deg,
    `width_half` cm, `lift` cm, `toe_out` deg, `swing_out` cm, `knee_bend` deg.
  - `width` cm is the two sides' sum.
- A swing amplitude is its gait harmonic's (order `strides` for once-a-stride, `2 * strides` for twice)
  amplitude over the cycle; phases kept as `_phase` keys for the operators.

- [x] Step 1: Tests on the synthetic walker. Each quantity is built into the synthetic cycle at a known value
  and read back within 2 %: a pelvis bob of 3 cm at twice a stride, sway 2 cm, the arm swing, the elbow, the
  width, the lift, the stance duty. Also a two-stride cycle reads the same.
- [x] Step 2: Implement with the definitions above (the hips and chest through the fork's `pelvis_fit` and
  `chest_fit`, so they agree with the engine).
- [x] Step 3: Pass, commit.

### Task 4: Operators in the fork

**Files:** Modify `gaitmodel.py`. Test `tests/test_gait_model.py`.

**Interfaces:**
- Produces new internal knobs, every default "no change":
  - `bob_gain`, `sway_gain`, `surge_gain` (× the pelvis component's gait harmonic);
  - `bob_add`, `sway_add`, `surge_add` (cm of a norm-phase cosine added, for a quiet clip);
  - `arm_gain` and `elbow_gain` (× the arm chain's and forearm's gait harmonic; sided);
  - `lean_add`, `chest_bounce`, `nod_add` deg;
  - `elbow_add`, `arm_fwd_add`, `arm_out_add`, `shoulder_add` deg (sided);
  - `toe_add` deg and `knee_bend` deg (sided; 0 = off);
  - `arm_lag_add` frames.

- [x] Step 1: Tests, one per operator, on the synthetic walker: the change it makes reads back through
  `aspects.measure`, and at its default the result equals the parity result to 1e-9.
- [x] Step 2: Implement:
  - precomputed harmonic tables (the pelvis's along / aside / height, each arm joint's log) at the clip's
    samples;
  - the turns at their joints in `_frame`: lean shared over the spine joints, the head's nod, the forearm's
    hinge, the upper arm's world turns, the clavicle's;
  - `knee_bend` as the planted leg's reach;
  - the arm chain's lag.
- [x] Step 3: Pass, commit.

### Task 5: The knob table and the mapping

**Files:** Modify `aspects.py`. Test `tests/test_gait_aspects.py`.

**Interfaces:**
- Produces:
  - `KNOBS`: tuples (name, group, label, unit, kind "measured" | "added", default for added, range rule, sided);
  - `defaults(base)`: the gait knob values of a walk, base = `measure` of the baseline;
  - `engine_knobs(base, gait, P)` → the fork's knob dict;
  - `speed_law(base, speed)` → (step, cadence).

- [x] Step 1: Tests:
  - `engine_knobs(base, defaults(base))` is the fork's defaults with gains 1 and adds 0;
  - Speed ×2 at the walk ratio gives step and cadence × √2;
  - past the longest step the cadence takes the rest;
  - Weight, Follow-through and Whip spread as the spec says;
  - side knobs give `_l` / `_r` engine knobs.
- [x] Step 2: Implement, pass, commit.

### Task 6: Knee clicks and the knee bend

**Files:** Modify `gaitmodel.py`. Gates in `gates.py`.

- [ ] Step 1: `gates.py clicks`: asd, dw, HavyRun at Stride ×1.4, ×0.6, Ground time ×1.3, pelvis +10 / −15,
  lift ×2 against the acceptance. Record the before numbers.
- [ ] Step 2: Find where the clicks come from by frame (the leg's distance against its reach, the roll), fix in
  `_lowering` / `_leg`.
- [ ] Step 3: Test: the synthetic walker at stride 1.4 keeps its knee's second difference within the acceptance.
- [ ] Step 4: Pass, commit.

### Task 7: Sources and CAT presets

**Files:** Create `gaitgen.py`, `gaitload.py`.

**Interfaces:**
- `gaitgen.preset_clip(name, fps)` → (Clip, statics).
- `gaitload.source(kind, name)` → `Source` (walk, statics, start, base measure, label), cached. `kind` is
  "walk" (a saved walk file), "card" (a Walk cycles card) or "preset".
- `gaitload.evaluate(source, gait, pose)` → Result.

- [ ] Step 1: Test: a preset clip analyses, closes, and its measure's stride and duty are the preset's.
- [x] Step 2: Implement, commit. (gaitgen.py and gaitload.py; checked by hand: the four presets analyse; the unit test of Step 1 is not written)

### Task 8: The Maya window

**Files:** Create `skeldar_gait.py`.

- [x] Step 1: WRITTEN, compiles, never run
  - the window: source menu, pose menu + share + parts, main knobs, details in collapsed frames, Both / Left /
    Right, Apply / Reset, the status;
  - `skeldarGait` memo on the top joint;
  - re-key on slider release;
  - follow `skeldar_cat.py`'s structure.
- [ ] Step 2: `verify_gait.py` in mayapy standalone: a walk on the plugin's Manny UE5 skeleton reproduces the
  model, closes, one undo, a re-key from the stored place, a CAT preset applied.
- [ ] Step 3: Commit.

### Task 9: Gates on real walks

- [ ] `gates.py all`: identity, parity, read-back, effect, redundancy, helpers, speed on asd, dw, HavyRun and a
  CAT Walk.
- [ ] Write the numbers into the spec's addendum and CLAUDE.md.
- [ ] Commit.
