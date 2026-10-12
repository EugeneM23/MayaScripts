# Physical Stop: Three Poses - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps use checkbox syntax.

**Goal:** The physical stop runs through three keys - A, a breakdown M hit exactly at its frame, B - with the
bottom on an arc through all three, the overshoot along the arc's tangent, the top's lag read off M; and the
controls renamed and grouped.

**Architecture:** The same one file `docs/superpowers/plans/physstop/skeldar_physstop.py` and its four
layers. The model gains a three-key `Path`, a pure `Arc` and `pin_weight`; the geometry gains `path_world`
and `compose` (the lag from M, the pin); the scene reads three keys; the window loses Overlap and gains two
headed groups.

**Tech Stack:** Maya 2027 mayapy, `maya.cmds`, `maya.api.OpenMaya`, stdlib `unittest`; numpy only in
the calibration script.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-10-12-physical-stop-three-poses-design.md`.
- Nothing in `SkeldarAnim/` changes. Units frames / cm / degrees; Maya matrices row-vector;
  `(a*b).asMatrix() == a.asMatrix()*b.asMatrix()` for MQuaternion (measured); `asAxisAngle()` gives
  `(MVector, radians)`.
- The model section stays stdlib; cmds and OpenMaya are imported inside functions.
- Tests: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_physstop -v`.

---

### Task 1: The model - three-key spline, the arc, the pin

**Files:** modify `skeldar_physstop.py` (section 1), `tests/test_physstop.py`.

**Interfaces produced:**
- `DEFAULTS = (("overshoot", 4.5), ("swing", 5.0), ("weight", 1.0), ("sway", 1.0))`; `params(**given)`.
- `Path(t_a, t_m, t_b, s_m, overshoot, swing, zeta)`: `.at(t) -> (p, dp)`, `.v_m`, `.v_b`, `.overshoot`,
  `.clamped`.
- `Arc(a, m, b)` (3-tuples): `.at(s) -> (x, y, z)`, `.s_m`, `.length`, `.tangent`, `.bend()`.
- `pin_weight(t, t_a, t_m, t_b) -> float`.
- `solve(t_a, t_m, t_b, s_m, reach, lateral, height, given=None) -> Transition` with `.rows` (a row at t_m
  even when fractional), `.row_at(t)`, `.lag_share(tilt)`, `.readable`, `.end`, peaks.

- [ ] Tests first: the spline (0 at A at rest, `s_m` at M, 1 at B, continuous speed at M and B, never
  backwards over 2000 samples for even and uneven breakdowns, the first overshoot = the asked one, the swing
  length, heavier rings longer, a long slow move clamped, no overshoot -> still after B); the arc (A, M, B on
  it, `at(s_m) == M`, straight for M on the line, the tangent at B, the run past B along it, length of a
  straight arc = the distance); `pin_weight` (0 / 1 / 0, smooth); `solve` (rows from A frame by frame plus a
  fractional M, ends on B, starts on A, the signs, weight -> sink, sway 0 -> none, heavier settles later,
  `lag_share` 1 at M).
- [ ] Run - fail. Implement. Run - pass. Commit.

### Task 2: The geometry - the path pose on the arc, the lag, the pin

**Files:** modify `skeldar_physstop.py` (section 2), tests.

**Interfaces produced:** `secondary(bottom, lag, yaw, sink, sway, heading)` (`lag` an MQuaternion);
`Setup(poses, times, order, fixed, parent_at, bottom, arc, heading)`; `path_world(setup, t, p) -> (MMatrix,
turn)`; `compose(transition, setup) -> (frames, info)`, frames `[(t, translate, rotate)]`, info
`{"lag_deg", "lag_dir", "bend"}`.

- [ ] Tests: `secondary` (lag rotates the top about the bottom, sink down, sway left, yaw about up);
  `compose` (frame at A = A, at M = M to 1e-6 in channels, last = B; a breakdown tilted 20 deg back reads
  "back" and ~20 deg; tilted sideways reads "left"/"right"; an even, untilted M gives a lag of 0 and a
  straight bottom path).
- [ ] Run - fail. Implement. Run - pass. Commit.

### Task 3: The cube with three keys; the calibration

**Files:** `calibrate_physstop.py`, tests (`CubeTests`).

- [ ] `CubeTests` run the model with A = frame 0, M = frame 5 (its travel `s_m`), B at the frame the cube
  passes its target, the tilt shape scaled to the cube's lag at 5; same tolerances as before.
- [ ] The calibration on the three-key model; constants updated only if the fit moves them.

### Task 4: The scene - three keys, re-apply, restore; the verify

**Files:** `skeldar_physstop.py` (section 3), `verify_physstop.py`.

- [ ] `source` (three keys, the refusals, the marker with tM, an old two-pose marker refused), `plan` (the
  arc from the three world bottoms, the heading from the chord, the setup, `compose`), `_write` (marker
  with tM), `describe` (the breakdown line), `restore` (three keys back; two for an old marker).
- [ ] Verify standalone: the cube from its frames 0 / 5 / final at 9 against the animator's (bottom and top
  rms, tilt peak, sink), M exact, a sideways-bent arc through M with the overshoot along the tangent, a
  sideways-tilted M, re-apply / edit B / undo / Restore, the prop, the spin, the refusals.

### Task 5: The window, the docs

**Files:** `skeldar_physstop.py` (section 4), tests (`WindowTests`), `CLAUDE.md`.

- [ ] Four sliders in two headed groups (Stop: Overshoot, %, Swing length, fr, Weight; Extras: Side sway,
  Up axis), the intro naming the three keys; the window tests on the fake cmds.
- [ ] The whole suite; the CLAUDE.md section rewritten for three poses; commit.
