# Walk Builder: a straight stance leg at the passing phase — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** a `Passing knee` knob (deg, sided) that brings a cycle's stance knee to the asked bend at the passing
phase by lifting the hips there — and a `Leg stretch` knob (%, sided, default 0) that buys what the legs cannot
reach.

**Architecture:** the pelvis's vertical offset is already one number a frame (`_lowering`'s `drop`, subtracted
in `_body`). The straightening is the same quantity with the other sign: a per-frame lift computed after the
drop, bounded by what every leg allows, under a reach cap that gives way only around the middle of a contact.
Everything downstream (the leg solve, Balance, the bob, the body) reads that one offset and follows for
nothing.

**Tech Stack:** Python 2/3-compatible numpy inside `SkeldarAnim/maya_walk` (stdlib + numpy only, no Maya);
`mayapy -m unittest` for the unit tests; headless `mayapy` verify scripts for the real cycles.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-11-02-walk-straight-passing-leg-design.md`.
- **Nothing is automatic**: both knobs default to off (0), and a cycle's own value for `passing_knee` is what
  it measures, so an untouched card changes nothing — `own_knobs()` and the gait defaults must give the source
  back bit for bit.
- The fork `docs/superpowers/plans/gaitbuilder/gaitmodel.py` is held to the plugin's model frame for frame by
  `tests/test_gait_model.ParityTests`: every change to `maya_walk/model.py` goes into it word for word.
- Run the tests with
  `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v` from the repo
  root (never `python`: the Store stub hangs).
- `STRAIGHT_EDGE = 0.3`, `STRAIGHT_LIFT_MAX = 15.0` cm, `DIAG_PASSING = 18.0` deg, `LEG_STRETCH_MAX = 0.25`.

## File structure

| file | what it gains |
|---|---|
| `SkeldarAnim/maya_walk/model.py` | the four pure helpers (`straight_ratio`, `knee_bend_at`, `passing_share`, `smooth_under`, `lift_to`), the engine knobs `passing_knee` / `leg_stretch` (sided), the cap in `_leg_reach` / `_soft_from`, the lift and the stretch in `_lowering`, the stretch in `_leg`, `info["passing"]` |
| `SkeldarAnim/maya_walk/gait.py` | `_passing_knee` measure, the two `Param`s, `engine_knobs`' mappings, the diagnosis |
| `docs/superpowers/plans/gaitbuilder/gaitmodel.py` | the same model change, word for word (parity) |
| `tests/test_walk_straight_leg.py` | the new unit tests (one file, no edits to existing test files) |
| `docs/superpowers/plans/walkparam/verify_walk_straight_leg.py` | the headless verify over the animator's cycles |

---

### Task 1: the pure helpers

**Files:**
- Modify: `SkeldarAnim/maya_walk/model.py` (beside `smooth_cover`, ~line 503; the constants beside
  `STRAIGHT_SOFT`, ~line 190)
- Test: `tests/test_walk_straight_leg.py`

**Interfaces:**
- Produces: `straight_ratio(bend_deg, l1, l2) -> float`, `knee_bend_at(ratio, l1, l2) -> float`,
  `passing_share(r, length, edge=STRAIGHT_EDGE) -> float`, `smooth_under(room, sigma) -> np.ndarray`,
  `lift_to(q, up, target) -> float or None` (`q` = ankle − hip, `+` = the hip rises).

- [ ] **Step 1: the failing tests** — `straight_ratio`/`knee_bend_at` round trip (5 deg on an 85.6 cm leg of
  two equal bones reads back 5; 0 deg is exactly 1.0); `passing_share` 0 at r=0 and r=length, 1 at the middle,
  monotone in and out, smooth (no step over 0.2 between neighbouring tenths); `smooth_under` under its input
  everywhere, periodic, zero where the room is zero, and smooth (|second difference| ≤ its own max / 4 on a
  square room); `lift_to` on a hand-worked case (q = (0, −80, 0), up = +Y, target 85 → 5.0) and None where the
  target is shorter than |q| projected.
- [ ] **Step 2: run them, see them fail** (`mayapy -m unittest tests.test_walk_straight_leg -v`).
- [ ] **Step 3: implement the five helpers.**
- [ ] **Step 4: run them, see them pass.**
- [ ] **Step 5: commit** (`feat(walk): the straight-passing helpers`).

### Task 2: the knob, the cap and the lift

**Files:**
- Modify: `SkeldarAnim/maya_walk/model.py` — `KNOBS` (+`("passing_knee", 0.0, 0.0, 90.0)`), `SIDED`,
  `_leg_reach`, `_soft_from`, `evaluate` (`ctx["straight"]`), `_lowering` (`_passing_lift`), `info`
- Test: `tests/test_walk_straight_leg.py`

**Interfaces:**
- Consumes: Task 1's helpers.
- Produces: `ctx["straight"] = {side: target_ratio}` (absent = off), `Walk._passing_lift(times, legs, ctx,
  drop) -> np.ndarray or None`, `Walk.straight_share(side, t, ctx) -> float`,
  `info["passing"] = {"asked": {side: deg}, "got": {side: deg}, "lift": cm, "short": {side: cm}}`.

- [ ] **Step 1: the failing tests** on a synthetic walker (the fixture of `tests/test_walkmodel.py`, imported,
  with Manny's own leg signs): `passing_knee` 0 changes nothing (the worlds bit-identical to the knob absent);
  asked 5 deg straightens the stance knee at the passing to within 1 deg; the contacts' knees move by less
  than 2 deg (the window is local); no planted foot moves more than 1e-6 cm (no slide); the loop closes; the
  lift is 0 at the double supports; `info["passing"]["got"]` reads the asked value back.
- [ ] **Step 2: run them, see them fail.**
- [ ] **Step 3: implement** — `evaluate` fills `ctx["straight"]` from the sided knob (only where the ask is
  straighter than the walk's own `reach`); `straight_share` reads `_contact_at` and `passing_share`;
  `_leg_reach` and `_soft_from` raise their answers to the share-interpolated target for a planted leg;
  `_lowering` computes the lift after the drop (need from the geometry, allowance from every leg's own limit,
  `smooth_under` with `LOWER_BLUR`), returns `drop - lift`, and fills `info["passing"]`.
- [ ] **Step 4: run them, see them pass; run the whole walk suite** (`mayapy -m unittest discover -s tests
  -t . -p "test_walk*.py"`) and `tests/test_gait_model.py` — the parity test will fail until Task 4.
- [ ] **Step 5: commit** (`feat(walk): the passing knee straightened by a local hip lift`).

### Task 3: Leg stretch

**Files:**
- Modify: `SkeldarAnim/maya_walk/model.py` — `KNOBS` (+`("leg_stretch", 0.0, 0.0, 0.5)`), `SIDED`,
  `_lowering` (the limits × (1 + stretch), `ctx["stretch"]`), `_leg_source` / `_leg` (the scaled lengths),
  `info["passing"]["stretch"]`
- Test: `tests/test_walk_straight_leg.py`

**Interfaces:**
- Consumes: Task 2's `ctx`.
- Produces: `ctx["stretch"] = {side: np.ndarray (n,)}` (the factor a frame, 1.0 where the leg reaches),
  `Walk._stretch_of(side, tau, ctx) -> float`.

- [ ] **Step 1: the failing tests**: `leg_stretch` 0 changes nothing (bit-identical); at 10 % on a cycle whose
  pelvis is raised past the legs' reach, the drop falls and no bone grows by more than 10 %; the stretched
  frames are the contacts (the factor is 1.0 at the passing); every planted foot still stands exactly on its
  print.
- [ ] **Step 2: run them, see them fail.**
- [ ] **Step 3: implement.**
- [ ] **Step 4: run them and the walk suite.**
- [ ] **Step 5: commit** (`feat(walk): Leg stretch buys what the legs cannot reach`).

### Task 4: the fork's parity

**Files:**
- Modify: `docs/superpowers/plans/gaitbuilder/gaitmodel.py` (the same hunks, word for word)
- Test: `tests/test_gait_model.py` (unchanged, it is the gate)

- [ ] **Step 1: run `mayapy -m unittest tests.test_gait_model -v`** and see the parity tests fail.
- [ ] **Step 2: copy the hunks into the fork** (the helpers, the knobs, `_leg_reach`, `_soft_from`,
  `_lowering`, `_leg`, `info`).
- [ ] **Step 3: run it again, see it pass; run `docs/superpowers/plans/gaitbuilder/verify_gait.py`.**
- [ ] **Step 4: commit** (`chore(gait): the fork takes the passing-knee straightening`).

### Task 5: the parameters and the diagnosis

**Files:**
- Modify: `SkeldarAnim/maya_walk/gait.py` — `_passing_knee`, `measure`'s sided dict, `PARAMS` (two rows after
  `knee_bend`), `engine_knobs`, `diagnose`, `DIAG_PASSING`
- Test: `tests/test_walk_straight_leg.py`

**Interfaces:**
- Consumes: Task 2 and 3's engine knobs.
- Produces: the parameters `passing_knee` / `passing_knee_l` / `passing_knee_r` and `leg_stretch*`;
  `measure` gains `passing_knee_l` / `passing_knee_r`.

- [ ] **Step 1: the failing tests**: the measure reads a synthetic walker's passing bend (the crossing instant,
  the contact's middle without one); `engine_knobs` passes the ask through only when it is straighter than the
  own by more than 0.25 deg; `leg_stretch` 10 (%) becomes the engine's 0.10; `values`/`ranges` give the range
  0..own; `diagnose` names a walk whose passing knee is past `DIAG_PASSING` with the fix `passing_knee` 8, says
  nothing for a run, and is silent about «a planted knee within 5 deg of straight» for a side the animator
  asked.
- [ ] **Step 2: run them, see them fail.**
- [ ] **Step 3: implement.**
- [ ] **Step 4: run them; run the whole suite** (`mayapy -m unittest discover -s tests -t .`), expecting only
  the repo's known failure (`test_chat_deploy.Keys`).
- [ ] **Step 5: commit** (`feat(gait): Passing knee and Leg stretch as parameters`).

### Task 6: the headless verify

**Files:**
- Create: `docs/superpowers/plans/walkparam/verify_walk_straight_leg.py`

- [ ] **Step 1: write it** — the animator's cycles (asd, dw, TestStrefe, TestDraaft, HavyRun, AGS_Sprint) read
  as Walk Builder reads them, and both poses; the gates of the spec's Verification section, each printed with
  its measured number, `0 of N gates failed` at the end.
- [ ] **Step 2: run it** (`mayapy verify_walk_straight_leg.py`) and fix what it finds.
- [ ] **Step 3: run every neighbouring verify** — `verify_walk.py`, `verify_walk_gait.py`,
  `verify_walk_own.py`, `verify_walk_many.py`, `verify_walk_keys_changed.py`, `verify_walk_arm_overlap.py`,
  `verify_walk_weapon_overlap.py` — and compare each failure against a clean worktree of the commit before.
- [ ] **Step 4: commit** (`test(walk): verify_walk_straight_leg.py`).

### Task 7: the retarget, and the animator's Maya

- [ ] **Step 1:** gate the straightened knee through `target.Retarget` onto a real Manny skeleton in the
  verify (`fix_pops` must not bend it back).
- [ ] **Step 2:** in the animator's Maya on port 7006 (read-only first: their scene, time, selection and
  modified flag unchanged afterwards), Pick a walk on a skeleton of our own, dial `Passing knee`, read the keys
  back and measure the game skeleton's knee at the passing.
- [ ] **Step 3:** the CLAUDE.md section, then commit and push.
