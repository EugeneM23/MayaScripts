# The rig pose as a top layer — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** the Walk Builder's mean pose rig stands in the mean pose of what the walker SHOWS (the additive pose,
the parameters and the physics in it), and its correction is applied to the evaluated animation as a top layer on
every frame.

**Architecture:** the correction becomes the key poses' fifth entry, `keyposes.CYCLE` ("cycle"), applied at every
frame of the result by `keyposes.correct` — unmirrored, needing no step detection. `meanrig` stands its rig in
`meanpose.mean_pose(anim.rw)` and reads it with `keyposes.measure` / `increment(planted=True)`. Nothing in
`model.py` changes; `meanpose.correct` and `Walk.fix` stay for corrections already dialled.

**Tech Stack:** numpy; `mayapy -m unittest` (no system Python); the verify scripts in mayapy standalone.

## Global Constraints

- The spec is `docs/superpowers/specs/2026-11-02-walk-rig-pose-top-layer-design.md`; read it first.
- The pelvis's move stays **in the layer** (no `split_common`, no Height / Forward parameter).
- An old `.walkfix` correction (`edits["fix"]`) is **left where it is read today** — new edits lay on top.
- `keyposes` imports nothing of Maya (a subprocess test pins it); `meanpose` likewise.
- Tests: new files only, `tests/test_walk_rig_pose_layer.py`. Run with
  `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest <module> -v` from the repo root.
- Commit per task.

---

### Task 1: the cycle entry in `keyposes`

**Files:**
- Modify: `SkeldarAnim/maya_walk/keyposes.py`
- Test: `tests/test_walk_rig_pose_layer.py` (create)

**Interfaces:**
- Produces: `keyposes.CYCLE` = `"cycle"`; `ENTRIES = KEYS + (CYCLE,)`; `cycle_values(entry, walk)` -> the
  `knots` values dict or None; `correct(clip, keys, steps, walk)` taking `steps=None`;
  `increment(key, base, now, walk, frame, knees=None, planted=None)`; `summary(keys, only=None)`;
  `on_result(walk, worlds, keys)` returning `rw` even when the steps cannot be read.

- [ ] **Step 1: the failing tests** — in `tests/test_walk_rig_pose_layer.py`, on the synthetic walker
  (`tests/test_walkmodel.walk()`), one test per promise:

```python
def test_a_cycle_edit_is_the_same_turn_on_every_frame(self):
    Y = wm.exp_rot(np.array([0.0, 0.0, math.radians(20.0)]))
    keys = {kp.CYCLE: self.entry(rot={"spine_02": Y})}
    out = kp.correct(self.w.clip, keys, self.steps, self.w)
    for f in range(self.w.P):
        want = local_at(self.w.clip, self.w, "spine_02", f) @ Y
        self.assertTrue(np.allclose(local_at(out, self.w, "spine_02", f), want, atol=1e-9), f)

def test_a_cycle_edit_is_never_mirrored(self):
    Y = wm.exp_rot(np.array([0.0, 0.0, math.radians(20.0)]))
    out = kp.correct(self.w.clip, {kp.CYCLE: self.entry(rot={"upperarm_l": Y})}, self.steps, self.w)
    for f in range(self.w.P):
        self.assertTrue(np.allclose(local_at(out, self.w, "upperarm_r", f),
                                    local_at(self.w.clip, self.w, "upperarm_r", f), atol=1e-9), f)

def test_a_cycle_edit_needs_no_steps(self):
    Y = wm.exp_rot(np.array([0.0, 0.0, math.radians(20.0)]))
    out = kp.correct(self.w.clip, {kp.CYCLE: self.entry(rot={"spine_02": Y})}, None, self.w)
    want = local_at(self.w.clip, self.w, "spine_02", 0) @ Y
    self.assertTrue(np.allclose(local_at(out, self.w, "spine_02", 0), want, atol=1e-9))

def test_the_file_carries_a_cycle_entry(self):
    keys = {kp.CYCLE: self.entry(pelvis=[0.0, 0.0, 3.0])}
    back = kp.loads(kp.dumps(keys))
    self.assertTrue(np.allclose(back[kp.CYCLE]["pelvis"], [0.0, 0.0, 3.0]))

def test_summary_names_the_keys_apart_from_the_mean_pose(self):
    keys = {kp.CYCLE: self.entry(pelvis=[0.0, 0.0, 3.0])}
    self.assertEqual(kp.summary(keys, only=kp.KEYS), "no key pose edited")

def test_planted_reads_a_foot_s_move_as_its_print(self):
    base = kp.measure(worlds_at(self.w, 0), self.w)
    moved = self.moved_foot("l", (4.0, 0.0, 0.0))           # along the travel, in the air at frame 0
    now = kp.measure(moved, self.w)
    free = kp.increment(kp.CYCLE, base, now, self.w, 0)[0]
    planted = kp.increment(kp.CYCLE, base, now, self.w, 0, planted=True)[0]
    self.assertGreater(float(np.abs(free["foot"]["l"]["t"]).max()), 1.0)
    self.assertTrue(np.allclose(planted["foot"]["l"]["t"], 0.0))
    self.assertGreater(float(np.abs(planted["print"]["l"]["t"]).max()), 1.0)

def test_on_result_gives_the_result_back_as_a_walk_with_no_steps(self):
    # a result whose steps cannot be read still takes the cycle edit
    ...
```

- [ ] **Step 2: run them, see them fail** —
  `mayapy -m unittest tests.test_walk_rig_pose_layer -v`; expected: AttributeError (no `kp.CYCLE`).

- [ ] **Step 3: implement** in `keyposes.py`:
  `CYCLE`/`ENTRIES`/`LABELS[CYCLE]`; `loads` accepting `ENTRIES`; `cycle_values`; `_zero_values` and `_plus`;
  `correct` taking `steps=None` and adding the cycle to every frame; `stance_prints` taking the cycle
  unmirrored; `increment(..., planted=None)` reading every foot as planted; `summary(keys, only=None)`;
  `on_result` splitting the `result_walk` and the `find` so a refused `find` still returns `rw` and still
  applies the cycle.

- [ ] **Step 4: run the tests and the neighbours** —
  `mayapy -m unittest tests.test_walk_rig_pose_layer tests.test_walk_keyposes tests.test_walk_keyrig -v`;
  expected: all pass.

- [ ] **Step 5: commit** — `git add SkeldarAnim/maya_walk/keyposes.py tests/test_walk_rig_pose_layer.py`.

---

### Task 2: the two Resets stop sweeping each other

**Files:**
- Modify: `SkeldarAnim/maya_walk/keyrig.py` (`reset`), `SkeldarAnim/maya_walk/meanrig.py` (`reset`)
- Test: `tests/test_walk_rig_pose_layer.py`

- [ ] **Step 1: the failing tests** — Reset key poses keeps a standing cycle entry; Reset rig pose drops the
  cycle entry and the old `fix` and keeps the four keys.

- [ ] **Step 2: run, see fail** (`keyrig.reset` sets `edits["keys"] = kp.empty()`).

- [ ] **Step 3: implement** — `keyrig.reset` keeps `keys[CYCLE]` and reads `had` off the four keys;
  `meanrig.reset` drops `keys[CYCLE]` and the old `fix`.

- [ ] **Step 4: run** the three walk rig test modules.

- [ ] **Step 5: commit.**

---

### Task 3: the rig stands in the result's mean and writes the cycle entry

**Files:**
- Modify: `SkeldarAnim/maya_walk/meanrig.py` (`press`, `update`, the lines)
- Test: `tests/test_walk_rig_pose_layer.py`

- [ ] **Step 1: the failing tests** (the `FakedTest` harness of `tests/test_walk_meanrig.py`): press asks for
  the animation **with its steps** and stands the rig in the mean pose of `anim.rw`; a control turned on the rig
  and Update writes `edits["keys"][CYCLE]`, not `edits["fix"]`; the walker is re-keyed unrecorded; nothing moved
  writes nothing; a walker whose steps cannot be read still takes a correction.

- [ ] **Step 2: run, see fail.**

- [ ] **Step 3: implement** — `press`: `anim = scene.walker_animation(root)`, `rw = anim.rw or
  kp.result_walk(anim.walk, anim.moving)`, `worlds = mp.mean_pose(rw)`; `update`: `kp.measure` against `rw`,
  `kp.increment(kp.CYCLE, ..., frame=0, planted=True)`, `kp.add` into `edits["keys"]`; the press line's summary.

- [ ] **Step 4: run** `tests.test_walk_rig_pose_layer tests.test_walk_meanrig tests.test_walk_keyrig
  tests.test_walk_panel` and the whole walk suite.

- [ ] **Step 5: commit.**

---

### Task 4: the proof

**Files:**
- Create: `docs/superpowers/plans/walkparam/verify_walk_rig_pose_layer.py`

- [ ] **Step 1: write the verify** — the spec's "Proof" list, mayapy standalone on a Manny UE5 skeleton with a
  pose card at share 1, each gate measuring the walker's own keys; the control is the old road (the correction
  put in `edits["fix"]` instead), which must read ~0 at share 1.

- [ ] **Step 2: run it** —
  `mayapy docs/superpowers/plans/walkparam/verify_walk_rig_pose_layer.py <clip>`; expected: 0 gates failed.

- [ ] **Step 3: run the neighbours** — `verify_walk_keyposes.py`, `verify_walk_meanpose.py`,
  `verify_walk_working.py`, `verify_walk_many.py`, `verify_walk_straight_leg.py`, each compared with the commit
  before this where it already fails.

- [ ] **Step 4: the unit suite** — `mayapy -m unittest discover -s tests -t .`.

- [ ] **Step 5: commit, then CLAUDE.md's own section, then live on port 7002.**
