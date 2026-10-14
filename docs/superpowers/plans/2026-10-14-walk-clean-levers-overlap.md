# Walk Builder: clean a raw clip, In place, levers, Overlap - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** the Walk Builder reads a broken raw clip (not looped, floating, jittery, a turned foot, dropped
shoulders, a still spine) and makes a clean walk of it; it can put a walk in place; it gains levers that move the
body on the gait's phase and an Overlap tab (upper body offset, spine wave, shoulder and pelvis drag).

**Architecture:** a new pure module `SkeldarAnim/maya_walk/clean.py` turns a raw `model.Clip` into a clean one
(loop, root, in place, spikes, posture against a reference, seam, smooth, derived bones, floor) and a report;
`scene.py` saves raw clips and analyses `clean(clip)` per (walk file, clean knobs, reference); the model gains the
In place, lever and overlap knobs; the card gains a Clean tab, an Overlap tab and an In place chip.

**Tech Stack:** Python 3 in mayapy (Maya 2027), numpy, stdlib unittest; `maya.api.OpenMaya` only through
`maya_poselib.posemath` (in pose.py, never in clean.py or model.py).

Spec: `docs/superpowers/specs/2026-10-14-walk-clean-levers-overlap-design.md`.

## Global Constraints

- Maya's row vectors: a world matrix is `local . parent`, a position its row 3, `v . R` turns v.
- `clean.py` and `model.py` import numpy and the stdlib only (a subprocess test pins each).
- Clean is identity on a clean cycle: every saved walk (asd, dw, AGS_Sprint, HavyRun, RunFast, sadda,
  Sword_Drunked, TestStrefe, Creep_Drunk) comes out of `clean()` at the default knobs with every world matrix
  within 1e-6 of what went in.
- Every new evaluate knob defaults to identity (0, or 1 for nothing new): `walk.evaluate()` and
  `walk.evaluate(walk.own_knobs())` give exactly what they gave before this work.
- Tests: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v` from the repo
  root (no system Python - it hangs). `$env:QT_QPA_PLATFORM='offscreen'` for Qt tests.
- Commit only your own files (`git add <paths>`), never `-A`: other sessions commit to `main` too.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; write them with `git commit -F`.
- Text written into Python files through the Write/Edit tools (a Bash heredoc halves backslashes, trap 198).

---

### Task 1: clean.py - the frame, the root, the loop, the seam, smooth

**Files:**
- Create: `SkeldarAnim/maya_walk/clean.py`
- Test: `tests/test_walkclean.py`

**Interfaces:**
- Produces:
  - `KNOBS` - `(("despike", 1.0, 0.0, 3.0), ("smooth", 0.0, 0.0, 4.0), ("fix_posture", 1.0, 0.0, 1.0),
    ("floor", 1.0, 0.0, 1.0), ("floor_offset", 0.0, -30.0, 30.0), ("seam", 8.0, 0.0, 30.0))`; `DEFAULTS`.
  - `class Report` - `.lines` [(step, text)], `.changed` bool, `.short()` one-line summary, `.text()` lines.
  - `class Rig` - the clip as locals: `Rig(names, parents, worlds)`; `.rot` (J, F, 3, 3) local rotations (the root's
    world), `.trans` (J, F, 3) local translations (the root's world place), `.worlds()` -> (J, F, 4, 4) by FK.
  - `clean(clip, statics=None, reference=None, knobs=None) -> (model.Clip, Report)`; `statics` {name: {"parent",
    "canonical", "rest" (16)}} or None; `reference` {name: 4x4 world on the walk's skeleton} or None.
  - `is_closed(clip) -> bool`, `loop_window(clip, cycle) -> (i, j, rms_cm)`, `close_seam(rig, frames)`.

- [ ] Step 1: tests (fail first): `IdentityTests` - clean of `walk_clip()` (test_walkmodel's synthetic) returns
  worlds equal to 1e-9 and `report.changed` False; `LoopTests` - 1.6 cycles of the synthetic (P=24 cut from a
  P=24, strides=1 generator run to 38 frames) comes back as 25 frames with residual < 0.01 cm and the root travel
  120 +- 0.5; a cycle without its closing frame (frames 0..23) comes back 25 frames, closed; `SeamTests` - a closed
  cycle whose last 6 frames of `spine_01`'s local rotation carry +8 deg comes back closed in value AND slope
  (the seam step and the slope jump both < 1e-6), frames beyond the seam window untouched; `RootTests` - a root held
  at the origin while the pelvis travels 120 is given the pelvis's ground line (root travel 120 +- 0.5, the pelvis's
  world unchanged); `SmoothTests` - smooth 0 is identity, smooth 2 lowers a frame-to-frame 1-frame noise of 3 deg on
  `head` below 1 deg.
- [ ] Step 2: run them, see them fail (module missing).
- [ ] Step 3: implement:
  - `Rig`: locals from worlds (orthonormal rotations, translations in the parent's frame); FK back.
  - `is_closed`: every BODY joint (not helpers, not `*_twist_*`) at the last frame against the first moved by the
    root's delta (the root's last world . first^-1 applied about the root) within (0.1 cm, 0.002).
  - root carrying: root travel (ground) < 1 cm and pelvis travel > 10 cm a clip: root += the pelvis's ground line
    `(pelvis[f] - pelvis[0]) projected on the floor`, the pelvis's world kept (its local re-read).
  - loop: closing frame (`|q_last - q_first|` within 1.5x the median of `|q_f+1 - q_f|`, q = body positions in the
    root's ground frame) -> append frame `first` carried by the root's per-frame delta; else `loop_window`: pairs
    (i, j), j - i >= 10, cost = RMS over joints and window +-2 of `|q_i+k - q_j+k|` (q in the root's ground frame:
    place on the floor + heading about up); strides whole: each foot's stance onsets (ankle/ball within 2 cm of its
    lowest and slower than 20 % of the clip's mean root speed) counted alike in [i, j); best = least cost, longest of
    those within 1.2x; cut [i, j] then the seam closes the rest.
  - seam (Holden): per joint series x (rotation log about the joint's mean, local translation; the root's
    rotation log and its place off the travel line `root[f] - root[0] - travel f/P`), `d = x[P] - x[0]`,
    `dv = (x[P] - x[P-1]) - (x[1] - x[0])`, B = min(seam, P/4) frames; start side `t = f/B`, `x0 = -d/2`... the
    offsets put `x[0] + o0 = x[P] + oP` and the slopes equal: start `o(t) = a t^3 + b t^2 + c t + x0` with
    `x0 = d/2`, `c = dv/2 . B`, `b = -3 x0 - 2c`, `a = 2 x0 + c`; end side mirrored in time with `x0 = -d/2`,
    `c = dv/2 . B`. The root's place: slope only (d forced 0).
  - smooth: periodic Gaussian of sigma `smooth` frames on the same series (rotation logs about the mean,
    translations that move), the cycle closed after.
- [ ] Step 4: run the tests, pass.
- [ ] Step 5: commit `feat(walk): clean - the root, the loop, the seam, smooth`.

### Task 2: clean.py - spikes

**Files:** Modify `SkeldarAnim/maya_walk/clean.py`; Test `tests/test_walkclean.py`

**Interfaces:**
- Produces: `spike_runs(x, scale=1.0) -> [[frame, ...], ...]` (x: (P, d) periodic series), `despike(rig, scale)`.

- [ ] Step 1: tests: a 1-frame 60 deg spike on `hand_l` and a 3-frame 25 deg plateau on `lowerarm_r` (in their local
  rotations) are found and removed (back within 1 deg of the unbroken walk at every frame); the unbroken walk:
  nothing found; a monotone 40 deg step over one frame (no return) is NOT a spike; `ball_*` never touched; despike 0:
  nothing.
- [ ] Step 2: fail.
- [ ] Step 3: implement: per joint (not ball_*, not helpers) the local rotation log about its mean (degrees) and,
  for root, pelvis and bones whose local translation moves > 0.5 cm, the translation (cm); `s` = median of
  `|x[f+1]-x[f]|`; threshold `max(6, 6 s) / scale`; runs L = 3, 2, 1 (longest first): jump in and jump out both
  above it, opposite (`dot < 0`), `|x[b] - x[a]| <= 0.5 min(|jumps|)`; replaced by the Catmull-Rom of (a-1, a, b, b+1).
  Report "spikes: lowerarm_r 17-19 (73 deg), hand_l 23 (91 deg)".
- [ ] Step 4: pass. Step 5: commit `feat(walk): clean - spikes out and back`.

### Task 3: clean.py - posture against a reference; pose.carried

**Files:** Modify `clean.py`, `SkeldarAnim/maya_walk/pose.py`; Test `tests/test_walkclean.py`

**Interfaces:**
- Produces: `LIMITS` table; `posture(rig, statics_rest, reference, strength, report)`; in pose.py
  `carried(names, first_worlds, statics, pose_bones, target_module) -> {name: 4x4}` (the reference on the walk's
  skeleton at its first frame's root; posemath Transfer, the legs' ratio size rule of `prepare`).

- [ ] Step 1: tests: with rest = reference = the synthetic's standing frame: `foot_l` turned 70 deg about the shin ->
  found ("foot_l 70 deg out"), fixed by the mirrored `foot_r` (its mean back within 2 deg of the unbroken one); both
  clavicles lowered 25 deg -> both found, fixed to the reference, the upper arms' WORLD rotations unchanged
  (1e-9); `clavicle_l`'s translation moved 3 cm -> its opposite's mirrored translation; nothing broken -> nothing
  changed; fix_posture 0 -> nothing changed; 0.5 -> half way.
- [ ] Step 2: fail.
- [ ] Step 3: implement:
  - body axes of the reference: up = the clip's up, side = rest upper arm left - right (on the floor), fwd = side x
    up made to point where the toes do.
  - mirror (posemath's rule, in numpy): root-space rotations `Q`, rest `Rr`, delta `D = Rr^T Q`, mirrored
    `Q' = Rr[x] F D[opposite] F`, `F = I - 2 l l^T`.
  - limits: clavicle elevation (-22, +35), protraction +-30 (the direction clavicle -> upper arm in the chest frame,
    against the reference's, in its body axes, side sign per side); foot pitch +-35 (toe down +), toe-out +-35 (the
    direction foot -> ball in the calf frame).
  - offsets: a pair whose mean local translations differ (mirrored) by > max(1 cm, 10 %): the side farther from rest
    takes the mirrored opposite.
  - fix: new mean = mirrored opposite's mean (opposite within limits) else the reference's local; slerped by
    strength; motion kept `local(t) = exp(log_t) . new`; clavicle's child keeps its world rotation.
  - `pose.carried`: `walk_rest = target.at_rest(statics)`; posemath pairs/Transfer(scale = legs ratio, 1 for a twin);
    `transfer.frame(root_world=transfer.place(first))`; numpy 4x4 out.
- [ ] Step 4: pass. Step 5: commit `feat(walk): clean - posture against a reference`.

### Task 4: clean.py - in place, derived bones, floor

**Files:** Modify `clean.py`; Test `tests/test_walkclean.py`

- [ ] Step 1: tests: the synthetic with its travel taken off (in place) -> travel restored 120 +- 3, its stance feet
  still (slide < 0.5 cm a frame); `ik_foot_l` keyed garbage -> back on `foot_l` at its rest relation (1e-9);
  `thigh_twist_01_l` keyed short (frames 18.. held) -> rebuilt (its local within 1e-6 of the rule); a good twist kept;
  the whole body raised 30 cm -> lowered back within 0.5 cm, the root unmoved; raised 1 cm -> left (dead zone);
  floor 0 -> left; floor_offset 5 -> 5 cm higher.
- [ ] Step 2: fail.
- [ ] Step 3: implement per spec Part 1 steps 3, 8, 9 (twist rule: follow `t` of the far bone's roll for lowerarm /
  calf, counter `-(1-t)` of the bone's own roll against its parent for upperarm / thigh, roll = the twist about the
  parent's bone axis of the driver's local delta from rest; rebuild when the source is > 20 deg off it at any frame).
- [ ] Step 4: pass. Step 5: commit `feat(walk): clean - in place, derived bones, floor`.

### Task 5: model - In place and the levers

**Files:** Modify `SkeldarAnim/maya_walk/model.py`; Test `tests/test_walkmodel.py`

**Interfaces:**
- Produces knobs: `in_place` (0, 0..1), `pelvis_tilt` (0, -15..15), `chest_pitch` (0, -15..15), `head_nod`
  (0, -20..20), `shoulder_swing` (0, -25..25), `shoulder_bob` (0, -15..15), `arm_swing` (0, -60..60); `SIDED` +=
  shoulder_swing, shoulder_bob, arm_swing. `LEVERS` table; `Walk.lever_shape(name, tau, side=None)`. The clean knobs
  stay in `clean.KNOBS` (model never imports clean): `scene.ALL_DEFAULTS = dict(wm.DEFAULTS, **wc.DEFAULTS)` and
  `scene.ALL_RANGES` are what the card and the marker use; `scene.apply` hands `evaluate` the model's share only.

- [ ] Step 1: tests: every new knob at 0 -> identity with before (worlds equal); in_place 1 -> the root's place equals
  its first frame's (Root sway 0) at every frame, every joint's place relative to the root unchanged; pelvis_tilt
  4 -> the pelvis's world pitch about the side axis gains a twice-a-stride wave of amplitude 4 deg (fit within 0.1),
  spine_03's world pitch unchanged by it within 0.5 deg (the lumbar takes it back); chest_pitch 3 -> spine top pitch
  wave 3 deg; head_nod 5 -> head pitch wave 5; shoulder_swing 6 -> each clavicle's yaw about up a once-a-stride wave
  of 6 deg, left and right opposite; shoulder_bob 3 -> clavicles' lateral end up wave; arm_swing 20 on a walker
  whose arms are held still -> each upper arm swings 20 deg about the side axis, left opposite right; sided arm_swing_l
  only moves the left.
- [ ] Step 2: fail. Step 3: implement (spec Part 2, Part 3). Step 4: pass. Step 5: commit
  `feat(walk): In place and the levers on the gait's phase`.

### Task 6: model - Overlap

**Files:** Modify `model.py`; Test `tests/test_walkmodel.py`

**Interfaces:**
- Produces knobs: `upper_offset` (0, -10..10 frames), `spine_wave` (0, 0..6), `shoulder_drag` (0, 0..8),
  `pelvis_drag` (0, 0..8).

- [ ] Step 1: tests (Balance 0, drags 0 where not tested): upper_offset 3 -> every joint from spine_01 up, in the
  pelvis's frame, at frame f equals the no-offset result's at f-3 (1e-9, whole frames); the legs and pelvis
  unchanged; -3 the other way; spine_wave 2 -> the top spine joint's own motion 2 frames late, spine_01's
  2/N; shoulder_drag 3 -> the clavicles' motion lags (cross-correlation peak 1..4 frames), the arms attached
  (upperarm origin on the clavicle's tip, 1e-9); pelvis_drag 3 -> the pelvis's twist lags 1..4 frames, the feet still
  planted (Foot placement 1 slide < 0.2 cm).
- [ ] Step 2: fail. Step 3: implement (spec Part 4). Step 4: pass. Step 5: commit
  `feat(walk): Overlap - upper body offset, spine wave, shoulder and pelvis drag`.

### Task 7: scene, files, the built-in reference

**Files:** Modify `SkeldarAnim/maya_walk/scene.py`, `files.py`; Create `SkeldarAnim/assets/walk_reference_ue5.wpose.gz`;
Test `tests/test_walktarget.py` / a new `tests/test_walk_scene.py` (fake cmds where needed).

**Interfaces:**
- Produces: `scene.BUILT_IN_REFERENCE = "UE5 idle (built in)"`, `scene.NO_REFERENCE = "(none)"`,
  `scene.reference_names()`, `scene.load_walk(name, clean_knobs=None, reference=None) -> (Walk, statics, start,
  Report)`; `save_walk` stores the raw clip (no loop refusal) and reports the clean at the defaults; `apply(...,
  reference=...)` cleans with the knobs' clean subset, keeps `reference` in the marker; `pick` returns it.

- [ ] Steps: tests first (load_walk caches per (file stamp, clean tuple, reference); a raw broken synthetic saves);
  implement; the built-in asset written from the idle's mean pose (scratch `ue5_idle_reference.wpose.gz`); a payload
  test that the asset ships; commit `feat(walk): a raw clip saved, cleaned when read; the built-in reference`.

### Task 8: the card

**Files:** Modify `SkeldarAnim/maya_walk/panel.py`; Test `tests/test_walk_panel.py`

- [ ] Steps: tests first (GROUPS in two rows; the Clean group's knobs; the Reference menu remembered; In place chip
  re-keys; the report text written after an apply); implement: groups `clean, step, legs, pelvis / chest, arms,
  overlap, weight`; Clean: Reference menu, Despike, Smooth, Fix posture, Floor, Floor offset, Seam, a report text
  (`skeldarWalkCleanReport`, wordWrap, height 80); In place checkbox (`skeldarWalkInPlace`) beside Apply / Reset; the
  new knobs' labels and tips; commit `feat(walk): the card - Clean and Overlap tabs, In place`.

### Task 9: verify, docs, ship

- [ ] `docs/superpowers/plans/walkparam/verify_walk_clean.py` (mayapy standalone): the broken clip (walks/
  Walking_broken.walk.gz) cleaned against the built-in reference: the loop closed, spikes lowerarm_r and hand_l
  found, foot_l and both clavicles fixed, clavicle_l's bone back, the floor lowered ~54 cm, twists and helpers
  rebuilt; against asd: foot_l within 15 deg, spikes within 3 deg, the pelvis within 5 cm; every saved walk unchanged;
  Apply onto a Manny skeleton (template) with In place and levers; Save walk -> Apply on the same skeleton.
- [ ] `verify_walk.py` and `verify_walk_sprint.py` green again.
- [ ] CLAUDE.md section; full unit suite; commit; push (CI builds the release).
