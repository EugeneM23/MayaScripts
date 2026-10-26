# Walk Builder as an editable gait model - implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Walk Builder's knobs become named gait parameters in units over a decomposed clip (regular part + Detail),
with macros, pins, physics helpers (the step chain, balance) and a Diagnosis panel - the spec
`docs/superpowers/specs/2026-10-26-walk-builder-editable-model-design.md`.

**Architecture:** The engine (`SkeldarAnim/maya_walk/model.py`) keeps every knob it has, with the same meaning, and
gains new engine knobs that default to no change (so the engine reads exactly as before for every old caller,
Gait Builder's parity tests included). A new pure module `SkeldarAnim/maya_walk/gait.py` holds the parameters:
`measure` (one function for the clip and the result), the table, `engine_knobs` (parameters -> engine knobs), the
stored changes (ratio / offset), pins, macros, characters, `diagnose`, `from_legacy`. `scene.apply` and the card call
`gait`; the memo goes to version 3.

**Tech Stack:** Python 3 in mayapy (Maya 2027), numpy, maya.cmds for the card; unittest.

## Global Constraints

- Tests: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v` from the repo
  root (no system Python; never `pip install`). One module: `mayapy -m unittest tests.test_walkgait -v`.
- `maya_walk/model.py` and `maya_walk/gait.py` import numpy and the stdlib only (a subprocess test pins it).
- Every new engine knob defaults to no change: `wm.evaluate(given)` with only old knob names gives exactly today's
  result (≤ 1e-9 cm).
- Row vectors (Maya's): a world matrix is local . parent; a rotation turns v as v . R.
- The walks on disk (`C:/Users/MY PC/Documents/maya/SkeldarWalks/*.walk.gz`) are the animator's data: read only, never
  committed; verify scripts read them.
- Live checks in the animator's Maya are theirs; everything here is proven headless (mayapy standalone).
- Peer sessions commit to `main`: stage only this work's files (`git add <files>`), never `git add -A`; never push
  without the animator.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

---

### Task 1: the engine takes Gait Builder's speed-ups and knee limits

**Files:**
- Modify: `SkeldarAnim/maya_walk/model.py`
- Test: `tests/test_walkmodel.py` (unchanged must pass), `tests/test_gait_model.py` (parity must pass)

**Interfaces:**
- Produces: engine knobs `knee_soft` (0..0.2, default 0), `knee_bend` (deg, 0..90, default 0, SIDED),
  `toe_add`, `lean_add`, `chest_bounce_add`, `nod_add`, `arm_fwd_add`, `arm_out_add`, `elbow_add`,
  `elbow_swing_add`, `shoulder_add` (all default 0; arm ones and `toe_add` SIDED); `Walk.lift_profile(side)`,
  `Walk.leg_parts`, `Walk.aspect_phase`, `Walk.lean_gain`, `soft_reach(d, soft, hard)`, `two_bone(..., soft=None)`.

- [ ] **Step 1:** Copy from `docs/superpowers/plans/gaitbuilder/gaitmodel.py` into `model.py` the hunks of
  `git diff --no-index SkeldarAnim/maya_walk/model.py docs/superpowers/plans/gaitbuilder/gaitmodel.py` that are
  (a) speed: `_units`, the one-vector paths of `_unit` / `exp_rot`, `periodic_cr`'s `uu`, `_frame`'s `_cross3`,
  `LT_STILL` + `_lt_const` + `lt_at`, `_foot_free`'s per-evaluation cache, the roll search's `cost1`,
  `ARM_RECARRY` in the balance rounds, `_cross3` in the arms' IK and `_leg_source`; (b) `soft_reach`, `two_bone(soft)`,
  `_leg_reach`, `own_stretch`, `_soft_from`, ctx `pose_lower`, `stance_reach`, `knee_soft`, `knee_bend`; (c) the
  aspect operators `_aspect_shapes`, `_lean_gain`, `aspect_turns`, `aspects_on`, `ASPECT_KNOBS` (without
  `bob_add` / `sway_add` / `surge_add` / `arm_swing_add` / `arm_lag_add`: Task 2 and 4 make those by the regular
  gains and lags), `toe_add` in `ctx["turns"]`, `lift_profile`, `_harmonic`. Not `weight_lag` / `weight_dip`.
- [ ] **Step 2:** Run `mayapy -m unittest tests.test_walkmodel tests.test_walktarget tests.test_gait_model -v`.
  Expected: all pass (parity ≤ 1e-6 cm with ARM_RECARRY 0).
- [ ] **Step 3:** Add to `tests/test_walkmodel.py`:

```python
class EngineKnobTests(unittest.TestCase):

    def test_new_engine_knobs_default_to_no_change(self):
        w = walk()
        base = w.evaluate({})
        again = w.evaluate(dict((k, wm.DEFAULTS[k]) for k in ("knee_soft", "knee_bend", "lean_add", "toe_add")))
        self.assertLess(float(np.abs(base.worlds - again.worlds).max()), 1e-9)

    def test_lean_add_leans_the_trunk(self):
        w = walk()
        a, b = w.evaluate({}), w.evaluate({"lean_add": 10.0})
        ia = w.index["neck_01"]
        lean = lambda r: np.degrees(np.arctan2((r.worlds[ia, :-1, 3] - r.worlds[w.index["pelvis"], :-1, 3])[:, :3] @ w.ahead,
                                               (r.worlds[ia, :-1, 3] - r.worlds[w.index["pelvis"], :-1, 3])[:, :3] @ w.up)).mean()
        self.assertAlmostEqual(lean(b) - lean(a), 10.0, delta=0.5)
```

- [ ] **Step 4:** Run the three modules again. Expected: pass.
- [ ] **Step 5:** Commit `perf(walk): the engine takes Gait Builder's speed-ups, soft knee limit and operators`.

### Task 2: the decomposition, Detail and the regular gains

**Files:**
- Modify: `SkeldarAnim/maya_walk/model.py`
- Test: `tests/test_walkmodel.py`

**Interfaces:**
- Produces: `HARMONICS = 4`; `Walk.decomposed` {(series, j): (regular (P,3), residual (P,3), mean (3,))} for series
  "pdev" (root, pelvis), "wlog" (pelvis, head, world arms), "llog" (spine, neck, clavicles, arms, fingers, local);
  `Walk.regular_amp(series, j, axis)`; engine knobs `detail` (1), `g_bob`, `g_sway`, `g_surge`, `g_head`,
  `g_arm` (SIDED), `g_elbow` (SIDED), `g_spine` (all 1).

- [ ] **Step 1: failing tests**

```python
class DecompositionTests(unittest.TestCase):

    def test_regular_plus_residual_is_the_series(self):
        w = walk()
        for (series, j), (reg, res, mean) in w.decomposed.items():
            src = getattr(w, series)[j]
            self.assertLess(float(np.abs(reg + res - src).max()), 1e-9, (series, w.names[j]))

    def test_the_residual_is_orthogonal_to_the_harmonics(self):
        w = walk(strides=2)
        B = w.harmonic_basis()
        for (series, j), (reg, res, mean) in w.decomposed.items():
            self.assertLess(float(np.abs(B.T @ res).max()), 1e-6)

    def test_detail_one_and_gains_one_are_today(self):
        w = walk()
        base = w.evaluate({})
        same = w.evaluate({"detail": 1.0, "g_bob": 1.0, "g_arm": 1.0})
        self.assertLess(float(np.abs(base.worlds - same.worlds).max()), 1e-9)

    def test_g_bob_scales_the_regular_bob_exactly(self):
        w = walk()
        pel = w.index["pelvis"]
        own = w.evaluate(w.own_knobs())
        big = w.evaluate(dict(w.own_knobs(), g_bob=2.0))
        amp = lambda r: w.regular_p2p(r.worlds[pel, :-1, 3, :3] @ w.up)
        self.assertAlmostEqual(amp(big), 2.0 * amp(own), delta=1e-3 * amp(own))

    def test_detail_zero_leaves_the_regular_part(self):
        w = walk(strides=2, spans=tw_TWO_STEPS)     # uneven strides: a real residual
        pel = w.index["pelvis"]
        r = w.evaluate(dict(w.own_knobs(), detail=0.0))
        y = r.worlds[pel, :-1, 3, :3] @ w.up
        self.assertLess(w.residual_rms(y), 0.05)
```

(`tw_TWO_STEPS` = this module's `TWO_STEPS`.)

- [ ] **Step 2:** Run; expected FAIL (no `decomposed`).
- [ ] **Step 3: implement** in `Walk.__init__` after `self.strides` is known:

```python
HARMONICS = 4

    def harmonic_basis(self, taus=None):
        """(P, 1 + 2K): 1, cos k a, sin k a of the stride phase a at source frames (or `taus`)."""
        taus = np.arange(self.P, dtype=float) if taus is None else np.asarray(taus, float)
        a = np.array([self.stride_phase(float(t)) for t in taus])
        cols = [np.ones_like(a)]
        for k in range(1, HARMONICS + 1):
            cols += [np.cos(k * a), np.sin(k * a)]
        return np.stack(cols, axis=1)

    def _decompose(self):
        B = self.harmonic_basis()
        self._pinv = np.linalg.pinv(B)
        self.decomposed = {}
        for series, kinds in (("pdev", ("root", "pelvis")), ("wlog", ("pelvis", "head")),
                              ("llog", ("spine", "head", "arm", "finger", "local"))):
            data = getattr(self, series)
            for j, kind in enumerate(self.kind):
                if kind not in kinds and not (series == "wlog" and j in self.world_arms):
                    continue
                x = data[j]
                reg = B @ (self._pinv @ x)
                self.decomposed[(series, j)] = (reg, x - reg, x.mean(axis=0))
```

  and `regular_p2p(y, taus=None)` / `residual_rms(y)` (fit on the basis, peak-to-peak of the fit on a fine grid of 8
  samples a frame / rms of what is left). The engine samples a series through one method:

```python
    def series_at(self, series, j, tau, ctx, gains=None, shift=0.0):
        """The series' sample at source time tau: mean + g . (R - mean) + detail . E (R sampled `shift` frames
        earlier); `gains` (3,) per axis in the series' own coordinates, else 1."""
        got = self.decomposed.get((series, j))
        x = getattr(self, series)[j]
        d = ctx["k"].get("detail", 1.0) if ctx else 1.0
        if got is None or (d == 1.0 and gains is None and shift == 0.0):
            return periodic_cr(x, tau)
        reg, res, mean = got
        r = periodic_cr(reg, tau - shift) - mean
        if gains is not None:
            r = r * gains
        return mean + r + d * periodic_cr(res, tau)
```

  `_body` samples the root's and the pelvis's `pdev` through it with `gains` in travel coordinates (rotate the
  deviation into `self.basis`, scale (g_surge, g_sway, g_bob), rotate back) - the pelvis's height also takes
  `bob_shift` (Task 4); the pelvis's `wlog` with `detail` only; `_frame` samples the head's `wlog` with `g_head`, the
  world arms' `wlog` and the upper arms' `llog` with `g_arm[side]`, the forearms' `llog` with `g_elbow[side]`, the spine
  and neck `llog` with `g_spine`, the rest with `detail` only. A step's print: `Foot.coords` against the mean of the
  side's steps, x `detail` in `foot_target.shift`.
- [ ] **Step 4:** Run `tests.test_walkmodel tests.test_gait_model`. Expected: pass.
- [ ] **Step 5:** Commit `feat(walk): the clip decomposed - regular part, residual, Detail, regular gains`.

### Task 3: timing - Ground time, Push-off, Heel strike, Foot flat

**Files:** Modify `SkeldarAnim/maya_walk/model.py`; Test `tests/test_walkmodel.py`

**Interfaces:**
- Produces: engine knobs `duty` (share of the cycle a contact lasts, 0 = the engine's own; SIDED), `push` (deg,
  SIDED), `heel_strike` (deg, SIDED), `slap` (frames, SIDED, default 0 = the source's own); `info["contacts"]`
  {side: [(strike, lift-off)] in the new cycle's frames}.

- [ ] **Step 1: failing tests**

```python
class TimingTests(unittest.TestCase):

    def test_duty_sets_each_contact_directly(self):
        w = walk()
        r = w.evaluate({"duty": 0.68})
        for side in "lr":
            for hs, to in r.info["contacts"][side]:
                self.assertAlmostEqual((to - hs) / float(r.frames), 0.68, delta=1.0 / LOCK)

    def test_push_lifts_the_heel_at_the_toe_off(self):
        w = walk()
        a, b = w.evaluate({}), w.evaluate({"push": 15.0})
        self.assertAlmostEqual(heel_up_at_off(w, b, "l") - heel_up_at_off(w, a, "l"), 15.0, delta=1.5)

    def test_heel_strike_lifts_the_toes_at_the_contact(self):
        w = walk()
        a, b = w.evaluate({}), w.evaluate({"heel_strike": 10.0})
        self.assertAlmostEqual(toes_up_at_on(w, b, "r") - toes_up_at_on(w, a, "r"), 10.0, delta=1.0)
```

  with helpers `heel_up_at_off(w, r, side)` / `toes_up_at_on` measuring the sole's pitch (the foot's `sole_up`
  against world up, about the foot's side) at the contacts' ends from `r.info["contacts"]` (these helpers move to
  `gait.py` in Task 5 and the tests then import them).
- [ ] **Step 2:** Run; FAIL.
- [ ] **Step 3: implement.**
  - `duty`: in `_growth`, after Foot placement's `e` and before Ground time: `if duty > 0: e = clamp(duty * P -
    (to - hs), floor, GROUND_ROOM * swing_len)` (floor as Ground time's). `info["contacts"]` = `placed_contact` with
    `ctx["grown"]` in new frames (x n / P).
  - `push` and `heel_strike` (radians of a signed roll, + heel up): in `_lowering`, after the needs' release /
    rate limit, add per frame a profile: `push` x smoothstep over the contact from `PUSH_FROM` (0.55) of it to its
    lift-off, then fading over the first `SWING_EASE` of the swing; `heel_strike` (negative) x (1 - smoothstep(r /
    slap_frames)) from the strike, ramped in over the last `SWING_EASE` of the swing before it; `slap_frames` = the
    source's own frames to a flat foot (`Walk.flat_after[side]`, measured at analysis: the first frame after the
    strike where the sole stands within 3 deg of the floor) + `slap`. These rolls bypass Foot flat (they are asked).
    `ctx["rolls"]` is set even when Foot placement is off when either is asked.
- [ ] **Step 4:** Run; pass. **Step 5:** Commit `feat(walk): Ground time, Push-off and Heel strike set directly`.

### Task 4: lags, the bob's timing, double bounce, chest timing

**Files:** Modify `SkeldarAnim/maya_walk/model.py`; Test `tests/test_walkmodel.py`

**Interfaces:**
- Produces: engine knobs `arm_lag` (SIDED, frames), `elbow_lag`, `hand_lag` (SIDED), `torso_lag`, `head_lag`,
  `bob_shift` (frames), `double_bounce` (cm), `chest_phase` (deg); all 0.

- [ ] **Step 1: failing tests**

```python
class LagTests(unittest.TestCase):

    def test_arm_lag_shifts_the_arm_exactly(self):
        w = walk()
        a, b = w.evaluate({}), w.evaluate({"arm_lag": 2.0})
        up = w.index["upperarm_l"]
        ra, rb = rotations(a, "upperarm_l", w), rotations(b, "upperarm_l", w)
        for f in range(24):
            self.assertLess(angle(ra[(f - 2) % 24].T @ rb[f]), 0.05)

    def test_bob_shift_moves_the_low_point(self):
        w = walk()
        pel = w.index["pelvis"]
        low = lambda r: int(np.argmin(r.worlds[pel, :-1, 3, :3] @ w.up))
        self.assertEqual((low(w.evaluate({"bob_shift": 2.0})) - low(w.evaluate({}))) % 12, 2)

    def test_double_bounce_adds_two_lows_a_step(self):
        w = walk()
        r = w.evaluate({"double_bounce": 3.0})
        y = r.worlds[w.index["pelvis"], :-1, 3, :3] @ w.up
        self.assertGreater(w.harmonic_amp(y, 4), 1.2)
```

- [ ] **Step 2:** FAIL. **Step 3:** in `_frame`, a joint's sample time `t` also loses `ctx["frame"]` x (its level's
  lags: clavicle 0.6 arm_lag, upper arm arm_lag, forearm + elbow_lag, hand and fingers + hand_lag; spine joint i of N
  `torso_lag` x (i + 1) / N; neck as the chest; head `head_lag`); in `_body`, the pelvis height's regular part sampled
  `bob_shift` frames earlier (`series_at(..., shift=)`) plus `-double_bounce / 2 . cos(4 a)` (a the stride phase:
  lows at the left strike and every quarter stride); `chest_extra` adds the chest's twist at its phase turned by
  `chest_phase` (`target cos(a - p - d) - own cos(a - p)`).
- [ ] **Step 4:** pass. **Step 5:** Commit `feat(walk): lags in frames, the bob's low point, double bounce, chest timing`.

### Task 5: `gait.measure` - every parameter read off a cycle

**Files:** Create `SkeldarAnim/maya_walk/gait.py`; Test `tests/test_walkgait.py`

**Interfaces:**
- Consumes: `Walk` (Task 2-4: `decomposed`, `harmonic_basis`, `stride_phase`, `pelvis_fit`, `chest_fit`, `contact`,
  `steps`, `sole_up`, `foot_side`, `across`, `lside`, `ahead`, `up`).
- Produces: `PARAMS` (tuple of `Param(name, group, unit, kind ("size" | "offset"), sided, low_rule, high_rule,
  label, tip)`), `measure(walk, worlds, taus, contacts) -> {name: value}` (sided: `name_l` / `name_r` and `name` their
  mean), `own(walk) -> measure of the clip`.

- [ ] **Step 1: failing tests** (`tests/test_walkgait.py`, the synthetic walker from `tests.test_walkmodel`):

```python
class MeasureTests(unittest.TestCase):

    def test_the_clip_reads_its_known_motion(self):
        w = tw.walk()
        m = gait.own(w)
        self.assertAlmostEqual(m["step"], 60.0, places=3)
        self.assertAlmostEqual(m["tempo"], 12.0, places=6)
        self.assertAlmostEqual(m["bounce"], 6.0, delta=0.05)       # 3 cos(2w + .3): 6 cm peak to peak
        self.assertAlmostEqual(m["sway"], 4.0, delta=0.05)
        self.assertAlmostEqual(m["width"], 20.0, delta=0.5)

    def test_the_same_function_reads_a_result(self):
        w = tw.walk()
        r = w.evaluate(w.own_knobs())
        a, b = gait.own(w), gait.of_result(w, r)
        for name in ("step", "bounce", "sway", "hips_twist", "arm_swing"):
            self.assertAlmostEqual(a[name], b[name], delta=1e-3)
```

- [ ] **Step 2:** FAIL. **Step 3:** implement `measure` per the spec's "Measured as" column (fine grid of 8 samples a
  frame for peaks; harmonics on the stride phase of each frame's source time; contacts from `walk.contact` for the
  clip and `info["contacts"]` for a result) and `of_result(walk, result)`.
- [ ] **Step 4:** pass. **Step 5:** Commit `feat(walk): gait.measure - the parameters read off a cycle`.

### Task 6: `gait.engine_knobs` - parameters onto the engine, exact read-back

**Files:** Modify `gait.py`; Test `tests/test_walkgait.py`

**Interfaces:**
- Produces: `Changes` = {name: ("ratio" | "offset", value)} (the stored form); `asked(own, changes, macros, pins,
  linked) -> {name: value}`; `engine_knobs(walk, own, asked, pins, pose=None) -> dict` for `wm.evaluate`;
  `PHYSICS` defaults (Foot placement 1, Balance 1, knee_soft 0.04).

- [ ] **Step 1: failing tests** - for each of step, tempo, width, bounce, low_point, lean, arm_swing, arm_lag,
  sway (pinned), surge (pinned), hips_twist, hip_drop, chest_twist, chest_sway, chest_bounce, head_motion, elbow,
  elbow_swing, arm_out, arms_forward, toe_out, ground_time, push, heel_strike, foot_lift, knee_bend, height:

```python
    def test_every_parameter_reads_back(self):
        w = tw.walk()
        own = gait.own(w)
        for name, delta in READBACK:          # (name, the change asked)
            want = own[name] + delta
            k = gait.engine_knobs(w, own, dict(own, **{name: want}), pins={name}, physics=False)
            got = gait.of_result(w, w.evaluate(k))[name]
            self.assertAlmostEqual(got, want, delta=max(0.1 * abs(delta), 0.3), msg=name)

    def test_own_values_give_the_clip(self):
        w, c = tw.walk(), tw.clip()
        own = gait.own(w)
        r = w.evaluate(gait.engine_knobs(w, own, own, pins=set(), physics=False))
        self.assertLess(float(np.abs(r.worlds - c.worlds).max()), 1e-4)
```

- [ ] **Step 2:** FAIL. **Step 3:** implement the mapping (the spec's "Engine" column): step -> `stride`, tempo ->
  `tempo` (frames a cycle = 2 x strides x frames a step), width -> `stance` (/ the width with the pose's spread),
  bounce -> `g_bob` (an own bounce under `QUIET` 0.5 cm: `bob_add`-style canonical cosine at the guide's low 5 % of a
  step), low point -> `bob_shift`, sway / surge -> `g_sway` / `g_surge` with `balance_sway` / `balance_surge` 0 when
  pinned (new engine knobs in `_balance_target`'s swing term, default 1), hips twist -> `pelvis_twist` (pinned: T /
  (twist_gain x stride); unpinned: the walk's own, so it grows with the step), hip drop -> `pelvis_list`, chest twist /
  sway the same way, arm swing -> `g_arm`, elbow swing -> `g_elbow`, head motion -> `g_head`, the offsets to their
  `*_add` / lag / `duty` / `push` / `heel_strike` / `slap` knobs, foot lift through `lift_profile`, the legacy
  multipliers left at 1 (bob, sway, surge, arms, elbow, head, spine, pelvis_rot, exaggeration), `weight` 0, the springs
  per Whip (Task 8).
- [ ] **Step 4:** pass. **Step 5:** Commit `feat(walk): gait.engine_knobs - each parameter onto the engine, read back`.

### Task 7: stored changes, pins, links, macros, characters

**Files:** Modify `gait.py`; Test `tests/test_walkgait.py`

**Interfaces:**
- Produces: `stored_change(param, own_value, value) -> (kind, x)`; `apply_change(param, own_value, change) -> value`;
  `LINKS` (arm swing with the speed; push-off and heel strike with the step: `PUSH_PER_STEP` 40 deg, `HEEL_PER_STEP`
  25 deg per +100 % of the step); `MACROS` (`speed`, `weight`) and `CHARACTERS` {name: {param: (kind, x)}};
  `values(own, changes, pins, macros, character, strength) -> {name: value}`.

- [ ] **Step 1: failing tests**

```python
    def test_a_ratio_applies_to_another_cycle(self):
        c = gait.stored_change(gait.P["step"], 60.0, 72.0)
        self.assertEqual(c, ("ratio", 1.2))
        self.assertAlmostEqual(gait.apply_change(gait.P["step"], 50.0, c), 60.0)

    def test_a_quiet_amplitude_is_an_offset(self):
        self.assertEqual(gait.stored_change(gait.P["bounce"], 0.2, 3.0)[0], "offset")

    def test_unpinned_arm_swing_follows_the_speed(self):
        own = {"arm_swing": 40.0, "speed": 1.4, "step": 70.0, "tempo": 15.0}
        v = gait.values(own, {"step": ("ratio", 1.3)}, pins=set(), macros={})
        self.assertGreater(v["arm_swing"], 40.0)

    def test_weight_moves_its_parameters_and_back(self):
        own = gait.own(tw.walk())
        heavy = gait.values(own, {}, set(), {"weight": 1.0})
        self.assertAlmostEqual(heavy["bounce"], own["bounce"] * 1.6, places=6)
        self.assertEqual(gait.values(own, {}, set(), {"weight": 0.0}), gait.values(own, {}, set(), {}))

    def test_speed_keeps_the_walk_ratio(self):
        own = {"speed": 1.4, "step": 70.0, "tempo": 15.0}
        v = gait.values(own, {}, set(), {"speed": 2.0})
        self.assertAlmostEqual(v["step"] / own["step"], math.sqrt(2.0 / 1.4), places=6)
```

- [ ] **Step 2:** FAIL. **Step 3:** implement. **Step 4:** pass. **Step 5:** Commit
  `feat(walk): parameters stored as changes, pins, physics links, macros and characters`.

### Task 8: Whip - springs that keep the stride's swing

**Files:** Modify `model.py` (`_body_motion`, `_limb_motion`), `gait.py`; Test `tests/test_walkmodel.py`

**Interfaces:** engine knob `spring_comp` (0 = today, 1 = the target advanced by the spring's phase delay at the stride
frequency and its deviation scaled by 1 / gain there); gait's `whip` (0..1) -> `arm_drag` / `torso_drag` / `head_drag`
= `WHIP_DRAG` (1.5) and the bounces = whip, `spring_comp` 1; whip 0 -> drags 0.

- [ ] **Step 1: failing test** - at `spring_comp` 1 and arm_drag 1.5 the upper arm's forward swing's first harmonic
  keeps its amplitude within 5 % and its phase within 0.3 frame of the drag-0 result.
- [ ] **Step 2:** FAIL. **Step 3:** the delay `atan2(2 zeta w0 w, w0^2 - w^2) / w` frames, the gain
  `w0^2 / sqrt((w0^2 - w^2)^2 + (2 zeta w0 w)^2)`, `w = 2 pi strides / n`; the target series resampled `delay` ahead
  (`np.roll` of the substeps) and its log about its mean / gain. **Step 4:** pass. **Step 5:** Commit
  `feat(walk): Whip - springs whose stride swing is compensated`.

### Task 9: the complaints measured on real walks; the step chain and balance fixed by the numbers

**Files:** Create `docs/superpowers/plans/walkparam/verify_walk_gait.py` (mayapy standalone, phases); Modify `model.py`
/ `gait.py` per the numbers; spec addendum.

- [ ] **Step 1:** write phase `complaints`: asd, dw, HavyRun, sadda, plain and under `goblin` / `two_handed_sword`
  (`maya_walk.pose.prepare` as `verify_walk.py` does): at step x1, 1.15, 1.3 - the pelvis drop, the straightest planted
  knee, the knee clicks (second difference within 25 deg of straight), the trailing heel's lift at the toe-off, the
  leading knee at the contact; the balance's side sway against `b (1 - sech(omega T / 2))` and the extrapolated CoM's
  margin to the support; the arms' swing kept and their lag under the springs.
- [ ] **Step 2:** run, read, decide each fix (the link constants of Task 7, the soft limit, the push profile, the
  balance's side term); implement; re-run until the spec's physics gates hold.
- [ ] **Step 3:** addendum in the spec with the numbers. **Step 4:** Commit `fix(walk): the step chain and the
  balance, by measurement`.

### Task 10: `gait.diagnose` and `gait.from_legacy`

**Files:** Modify `gait.py`; Test `tests/test_walkgait.py`

**Interfaces:** `diagnose(measured, own, info, run) -> [Finding(key, text, fix: {name: value})]` (the spec's table);
`from_legacy(walk, knobs) -> (changes, pins, macros)`.

- [ ] **Step 1: failing tests** - arms in step (arm_lag 0.2) -> a finding whose fix is arm_lag 3; a flat walk
  (bounce 1) -> its finding; a v2 memo `{"stride": 1.2, "bob": 1.5, "weight": 0.5, "overlap": 2}` -> step ratio 1.2,
  bounce ratio 1.5, macros weight 0.5, arm_lag offset 1.6 (0.8 share).
- [ ] **Step 2-4:** FAIL, implement, pass. **Step 5:** Commit `feat(walk): the Diagnosis and the legacy translation`.

### Task 11: `scene.apply` on parameters, memo version 3

**Files:** Modify `SkeldarAnim/maya_walk/scene.py`; Test `tests/test_walk_cycle_cards.py`, `tests/test_walk_panel.py`
(their fakes)

**Interfaces:** `scene.apply(root, walk_name, given=None, ..., params=None)` where `params` = {"changes", "pins",
"macros", "character", "strength", "whip", "detail", "physics"}; `given` (old knobs) still accepted (translated by
`from_legacy`); memo v3 `{"params": ..., "engine": engine knobs, ...}`; `memo_params(root)` reads v2 and v3.

- [ ] **Step 1-4:** tests on the fake cmds that a v2 memo is read as params, a v3 memo written, the engine knobs passed
  are `gait.engine_knobs`' (a mock walk). **Step 5:** Commit `feat(walk): scene keys parameters; the memo v3`.

### Task 12: the card

**Files:** Modify `SkeldarAnim/maya_walk/panel.py`; Test `tests/test_walk_panel.py`

**Interfaces:** Main rows (tempo, step, width, bounce, low_point, lean, arm_swing, arm_lag, detail), macro row (speed,
weight, character dropdown, strength), tabs (timing, pelvis, legs, trunk, head, arms, physics, clean, rigpose), the
Both / Left / Right row, pinned marks and their popup (Follow physics, Reset to the clip's), the Diagnosis rows with
Fix buttons; optionVars `skeldarWalk_param_*`, `skeldarWalk_pin_*`, `skeldarWalk_macro_*`, `skeldarWalk_character`,
`skeldarWalk_strength`; the old `skeldarWalk_knob_*` translated once.

- [ ] **Step 1-4:** the panel's tests rewritten for the rows (a slider's release stores a change and re-keys; a pin
  mark; a macro; a Fix sets its parameters; the side mode). **Step 5:** Commit `feat(walk): the card - parameters,
  macros, pins, Diagnosis`.

### Task 13: proof on real walks, docs

**Files:** `verify_walk_gait.py` phases `identity`, `readback`, `effect`, `physics`, `poses`, `maya`; CLAUDE.md
section; the spec's addendum.

- [ ] **Step 1:** run every phase on asd, dw, HavyRun, sadda, TestStrefe (+ goblin / sword): the spec's gates.
- [ ] **Step 2:** run the existing verifies (`verify_walk.py`, `verify_walk_sprint.py`, `verify_walk_own.py`,
  `verify_walk_clean.py`, `verify_walk_meanpose.py`, `verify_walk_many.py`) and the whole unit suite; fix what broke.
- [ ] **Step 3:** CLAUDE.md: a section "Walk Builder as an editable gait model (2026-10-26)"; the spec addendum with
  the final numbers. **Step 4:** Commit `docs(walk): the editable model, its numbers`.
