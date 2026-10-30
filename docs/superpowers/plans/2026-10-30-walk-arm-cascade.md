# The arms' cascade (Elbow overlap / Hand overlap) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Two knobs in Walk Builder's Arms group - `Elbow overlap` and `Hand overlap`, ms, sided - that read
the elbow's bend plane and the hand's own turn later than `Arm overlap` reads the arm, so the elbow orbits
late and the wrist breaks late while the IK keeps the hand's place and the bones' lengths.

**Architecture:** Road A of the two the 2026-10-29 `Arm overlap` pass left open: lag only what the IK leaves
free. One new pure function `late_bend` (the bend plane a chain gives `lag` frames earlier), one new optional
argument on the shared IK rebuild `_arm_to_hand` (a bend HINT, kept apart from the source plane it aligns
from), and the existing pass `Walk._arm_overlap` mixing two `shifted_cycle` calls for the hand (place at L,
turn at L + h) and asking `late_bend` for the hint at L + e. Two `gait` parameters with the three sites
`arm_overlap` has.

**Tech Stack:** Python 3 + numpy, stdlib `unittest`, Maya 2027's `mayapy` as the interpreter. No Maya needed
for anything in Tasks 1-5 but the verify, which runs in `mayapy` standalone.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-10-30-walk-arm-cascade-design.md`. Its predecessor,
  `2026-10-29-walk-arm-overlap-design.md`, settles everything the pass already does.
- The test runner is Maya's interpreter, never a system Python:
  `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest <target> -v` from the REPO ROOT.
- `SkeldarAnim/maya_walk/model.py` holds the engine; a knob is a row in `KNOBS` and, when two-sided, a name in
  `SIDED`. `SkeldarAnim/maya_walk/gait.py` holds the animator-facing parameters (`PARAMS`), their ranges and
  the ms -> frames conversion.
- Every new engine knob **defaults to no change** (0.0): the walk's own reading must come back untouched.
- `OVERLAP_QUIET` (1e-6 frames) is the threshold a lag must pass to touch anything.
- Milliseconds become frames of the new cycle at the OUTPUT frame rate: `sv(name) * fps / 1000.0` in
  `engine_knobs`, the `fps` argument `engine_knobs` already takes.
- Nothing is deleted or renamed. `Arm lag`, `Elbow lag`, `Hand lag`, `Elbow`, `Arms forward` and `Shoulders`
  stay exactly as they are (the animator's own ruling of 2026-10-29).
- Commit after each task, message in the repo's style (`feat(walk): ...`, `test(walk): ...`), ending with
  `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- The working tree holds other sessions' uncommitted work (`maya_scenetabs/*`, `maya_timebar/bar.py`,
  `docs/.../gaitguide/*`). **Stage only the files each task names.** Never `git add -A`.

---

### Task 1: the two engine knobs

**Files:**
- Modify: `SkeldarAnim/maya_walk/model.py` (the `KNOBS` table near line 116, the `SIDED` tuple near line 169)
- Test: `tests/test_walk_arm_overlap.py` (the existing `KnobTests` class, line 69)

**Interfaces:**
- Consumes: nothing.
- Produces: engine knobs `"elbow_overlap"` and `"hand_overlap"`, floats, frames of the new cycle, default 0.0,
  range -120.0 .. 120.0, both in `SIDED` so `"elbow_overlap_l"` / `"_r"` set one side. Read in the engine as
  `ctx["ks"][side]["elbow_overlap"]`.

- [ ] **Step 1: Write the failing test**

Add to `class KnobTests` in `tests/test_walk_arm_overlap.py`:

```python
    def test_the_engine_carries_the_two_cascade_knobs(self):
        for name in ("elbow_overlap", "hand_overlap"):
            self.assertIn(name, wm.DEFAULTS, name)
            self.assertEqual(wm.DEFAULTS[name], 0.0, name)
            self.assertIn(name, wm.SIDED, name)
            self.assertIn(name, wm.ENGINE_ONLY, name)
            lo, hi = wm.RANGES[name]
            self.assertLessEqual(lo, -120.0, name)
            self.assertGreaterEqual(hi, 120.0, name)
            w = walk()
            ks = w._sided({name + "_l": 3.0})
            self.assertEqual(ks["l"][name], 3.0, name)
            self.assertEqual(ks["r"][name], 0.0, name)
```

If `Walk._sided` is not the helper's name in this build, read `model.sided` / `SIDE_KNOBS` and use whatever
`_arm_overlap` itself uses to read a side's knobs (`ctx["ks"]`), keeping the same two assertions.

- [ ] **Step 2: Run test to verify it fails**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_walk_arm_overlap.KnobTests -v`
Expected: FAIL - `'elbow_overlap' not found in {...}` (the knob does not exist).

- [ ] **Step 3: Write minimal implementation**

In `model.py`'s `KNOBS`, right after the `("arm_overlap", 0.0, -120.0, 120.0)` row:

```python
    ("elbow_overlap", 0.0, -120.0, 120.0),
    ("hand_overlap", 0.0, -120.0, 120.0),
```

In `SIDED`, in the line that already holds `"arm_overlap"`:

```python
         "arm_overlap", "elbow_overlap", "hand_overlap", "spring_comp")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_walk_arm_overlap -v`
Expected: PASS, every test in the file (the knobs are inert until Task 3, so nothing else may change).

Then the whole walk suite, which must be unchanged:
Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_walkmodel tests.test_walkgait -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add SkeldarAnim/maya_walk/model.py tests/test_walk_arm_overlap.py
git commit -m "feat(walk): the cascade's two engine knobs, inert"
```

---

### Task 2: `late_bend`, and the IK rebuild's hint

**Files:**
- Modify: `SkeldarAnim/maya_walk/model.py` (a new module function beside `shifted_cycle`, near line 614; the
  method `Walk._arm_to_hand`, near line 3580)
- Test: `tests/test_walk_arm_overlap.py` (a new `LateBendTests` class after `ShiftedCycleTests`; two tests
  added to `ArmToHandTests`)

**Interfaces:**
- Consumes: `shifted_cycle(mats, lag)`, `_unit`, `_any_perpendicular`, `two_bone` - all already in `model.py`.
- Produces:
  - `model.late_bend(up, low, hand, lag)` -> `(n + 1, 3)` unit vectors. `up`, `low`, `hand` are the chain's
    three world-matrix cycles `(n + 1, 4, 4)`; `lag` is in frames. At `lag` 0 it returns exactly the hint
    `_arm_to_hand` computes for itself today.
  - `Walk._arm_to_hand(kin, n, chains, hands, hints=None)`. `hints` is `{side: (n + 1, 3)}`; a side without an
    entry (or `hints` None) keeps today's behaviour. The hint is given to `two_bone` ONLY; the source plane
    `_arm_to_hand` aligns the frames' arm from is untouched.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_walk_arm_overlap.py`, after `class ShiftedCycleTests`:

```python
class LateBendTests(unittest.TestCase):
    """The bend plane a chain gives `lag` frames earlier - the hint the cascade's elbow rides."""

    def chain(self, n=8):
        """Three cycles: a shoulder in place, a wrist out along +X, and an elbow whose offset from that line
        turns about X with the phase - so the bend plane is a different one at every frame."""
        up = np.tile(np.eye(4), (n + 1, 1, 1))
        low = np.tile(np.eye(4), (n + 1, 1, 1))
        hand = np.tile(np.eye(4), (n + 1, 1, 1))
        per = np.array([0.0, 0.0, 80.0]) / float(n)
        for f in range(n + 1):
            a = math.radians(360.0 * (f % n) / float(n))
            up[f, 3, :3] = per * f
            hand[f, 3, :3] = np.array([20.0, 0.0, 0.0]) + per * f
            low[f, 3, :3] = np.array([10.0, 4.0 * math.cos(a), 4.0 * math.sin(a)]) + per * f
        return up, low, hand

    def test_no_lag_is_the_frames_own_plane(self):
        up, low, hand = self.chain()
        got = wm.late_bend(up, low, hand, 0.0)
        for f in range(got.shape[0]):
            want = low[f, 3, :3] - up[f, 3, :3]
            e = wm._unit(hand[f, 3, :3] - up[f, 3, :3])
            want = wm._unit(want - np.dot(want, e) * e)
            self.assertTrue(np.allclose(got[f], want, atol=1e-9), f)

    def test_a_lag_is_the_plane_that_many_frames_earlier(self):
        up, low, hand = self.chain()
        got = wm.late_bend(up, low, hand, 2.0)
        now = wm.late_bend(up, low, hand, 0.0)
        n = up.shape[0] - 1
        for f in range(n):
            self.assertTrue(np.allclose(got[f], now[(f - 2) % n], atol=1e-9), f)

    def test_the_travel_does_not_enter_it(self):
        """The hint is read from differences at one frame, so a travelling cycle gives the same planes as a
        cycle standing still."""
        moving = wm.late_bend(*self.chain(), lag=2.5)
        still = [m.copy() for m in self.chain()]
        for m in still:
            m[:, 3, 2] = 0.0
        standing = wm.late_bend(still[0], still[1], still[2], 2.5)
        self.assertTrue(np.allclose(moving, standing, atol=1e-9))

    def test_every_hint_is_a_unit_vector_perpendicular_to_the_arms_line(self):
        up, low, hand = self.chain()
        got = wm.late_bend(up, low, hand, 1.5)
        for f in range(got.shape[0]):
            self.assertAlmostEqual(float(np.linalg.norm(got[f])), 1.0, places=9, msg=f)
```

Add to `class ArmToHandTests`:

```python
    def test_a_hint_bends_the_elbow_its_way_and_keeps_the_hand_and_the_bones(self):
        side = sorted(self.chains)[0]
        up_j, low_j, hand_j = self.chains[side]
        hands = dict((s, np.array(self.kin[c[-1]])) for s, c in self.chains.items())
        hint = wm.late_bend(self.kin[up_j], self.kin[low_j], self.kin[hand_j], 2.0)
        got = self.w._arm_to_hand(self.kin, self.n, self.chains, hands, {side: hint})
        # the hand is still its own, the bones still their own lengths
        self.assertTrue(np.allclose(got[hand_j][:, 3, :3], hands[side][:, 3, :3], atol=1e-6))
        for a, b in ((up_j, low_j), (low_j, hand_j)):
            was = np.linalg.norm(self.kin[b][:, 3, :3] - self.kin[a][:, 3, :3], axis=1)
            now = np.linalg.norm(got[b][:, 3, :3] - got[a][:, 3, :3], axis=1)
            self.assertLess(float(np.abs(now - was).max()), 1e-6, (a, b))
        # the elbow moved, and the other side did not take the hint
        moved = np.abs(got[low_j][:, 3, :3] - self.kin[low_j][:, 3, :3]).max()
        self.assertGreater(float(moved), 1e-3)

    def test_the_frames_own_hint_changes_nothing(self):
        hands = dict((s, np.array(self.kin[c[-1]])) for s, c in self.chains.items())
        plain = self.w._arm_to_hand(self.kin, self.n, self.chains, hands)
        hints = dict((s, wm.late_bend(self.kin[c[0]], self.kin[c[1]], self.kin[c[2]], 0.0))
                     for s, c in self.chains.items())
        same = self.w._arm_to_hand(self.kin, self.n, self.chains, hands, hints)
        for j in plain:
            self.assertTrue(np.allclose(plain[j], same[j], atol=1e-9), self.w.names[j])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_walk_arm_overlap.LateBendTests tests.test_walk_arm_overlap.ArmToHandTests -v`
Expected: FAIL - `module ... has no attribute 'late_bend'`, and `_arm_to_hand() takes 5 positional arguments but 6 were given`.

- [ ] **Step 3: Write minimal implementation**

In `model.py`, right after `shifted_cycle`:

```python
def late_bend(up, low, hand, lag):
    """The bend plane's hint (n+1, 3) an arm chain gives `lag` frames earlier: the elbow's offset from the
    shoulder-wrist line, unit, read from the three joints' cycles shifted that far (Elbow overlap). It is a
    direction read from differences at ONE frame, so shifted_cycle's travel term - the same for all three
    there - cancels and a travelling cycle does not enter it. lag 0: the frames' own plane, which is what
    _arm_to_hand computes for itself."""
    u, l, h = (shifted_cycle(m, lag) for m in (up, low, hand))
    n = u.shape[0] - 1
    out = np.zeros((n + 1, 3))
    for f in range(n + 1):
        sh, el, wr = u[f, 3, :3], l[f, 3, :3], h[f, 3, :3]
        e = _unit(wr - sh)
        b = (el - sh) - np.dot(el - sh, e) * e
        out[f] = _unit(b) if np.linalg.norm(b) > 1e-4 else _any_perpendicular(e)
    return out
```

In `Walk._arm_to_hand`, change the signature and the one `two_bone` call. The method's docstring gains the
hint's sentence:

```python
    def _arm_to_hand(self, kin, n, chains, hands, hints=None):
        """Each arm rebuilt to a wanted hand: `hands` {side: (n+1, 4, 4)} -> {joint: (n+1, 4, 4)} for the upper
        arm, the forearm and the hand (a side not in `hands` is left out). From the CURRENT shoulder - the
        arm's pivot is the body's - the elbow bending the way the frames bend it, the bones keeping their
        lengths (a hand past the arm's reach is clamped along its own line by two_bone). The one IK the
        springs' grip (_grip_motion) and the overlap (_arm_overlap) both reach their hands with.
        `hints` {side: (n+1, 3)} replaces the bend plane the elbow is sent toward (Elbow overlap's late
        plane); the SOURCE plane this aligns the frames' arm from is the frames' own either way."""
        out = {}
        for side, chain in chains.items():
            want = hands.get(side)
            if want is None:
                continue
            hint = (hints or {}).get(side)
            up_j, low_j, hand_j = chain
```

and inside the frame loop, the `two_bone` line alone:

```python
                knee, reached, _ = two_bone(sh, hand[3, :3], l1, l2,
                                            bend if hint is None else hint[f], 1.0)
```

Leave `e`, `bend`, `normal` and both `align` calls exactly as they are: they describe the FRAMES' arm, which
the rebuilt rotations are aligned from.

- [ ] **Step 4: Run test to verify it passes**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_walk_arm_overlap -v`
Expected: PASS, the whole file - `test_the_springs_grip_still_reaches_its_hands` included (`_grip_motion`
passes no hints, so it is untouched).

- [ ] **Step 5: Commit**

```bash
git add SkeldarAnim/maya_walk/model.py tests/test_walk_arm_overlap.py
git commit -m "feat(walk): late_bend, and the IK rebuild's bend hint"
```

---

### Task 3: the pass - the hand's turn at L + h, the elbow's plane at L + e

**Files:**
- Modify: `SkeldarAnim/maya_walk/model.py` (`Walk._arm_overlap`, near line 3613; the `moved_arms` line in the
  Balance path, near line 2731)
- Test: `tests/test_walk_arm_overlap.py` (a new `CascadePassTests` class after `OverlapPassTests`)

**Interfaces:**
- Consumes: `late_bend`, `_arm_to_hand(..., hints=)` (Task 2), the engine knobs (Task 1).
- Produces: `Walk._arm_overlap` returns `{"frames": float, "elbow": float, "hand": float, "grip": bool}` - the
  two new entries the largest absolute cascade lag of either side, in frames. `info["arms"]["overlap"]` carries
  it, as it already does.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_walk_arm_overlap.py`:

```python
class CascadePassTests(unittest.TestCase):
    """Elbow overlap and Hand overlap on the synthetic walker (the grip is the verify's, on the animator's
    own cycle)."""

    def setUp(self):
        self.w = walk()
        self.chains = self.w._arm_chains()
        self.side = sorted(self.chains)[0]
        self.up_j, self.low_j, self.hand_j = self.chains[self.side]

    def run_at(self, **knobs):
        knobs.setdefault("balance", 0.0)
        knobs.setdefault("arm_drag", 0.0)
        knobs.setdefault("whip", 0.0)
        return self.w.evaluate(knobs)

    def test_no_cascade_leaves_every_joint_untouched(self):
        plain = self.run_at()
        same = self.run_at(elbow_overlap=0.0, hand_overlap=0.0)
        self.assertTrue(np.array_equal(np.array(plain.worlds), np.array(same.worlds)))

    def test_the_elbows_plane_is_the_frames_plane_that_many_frames_earlier(self):
        """The rebuilt arm's bend plane at lag e is the plane the lag-0 arm gives e frames earlier."""
        lag = 2.0
        plain = self.run_at()
        kin = np.array(plain.worlds)
        want = wm.late_bend(kin[self.up_j], kin[self.low_j], kin[self.hand_j], lag)
        got = np.array(self.run_at(**{"elbow_overlap_" + self.side: lag}).worlds)
        n = plain.frames
        worst = 0.0
        for f in range(n):
            sh, el, wr = (got[j, f, 3, :3] for j in (self.up_j, self.low_j, self.hand_j))
            e = wm._unit(wr - sh)
            have = wm._unit((el - sh) - np.dot(el - sh, e) * e)
            # the wanted plane projected onto the rebuilt arm's own line, which is the hand's and so unchanged
            aim = wm._unit(want[f] - np.dot(want[f], e) * e)
            worst = max(worst, math.degrees(math.acos(min(1.0, max(-1.0, float(np.dot(have, aim)))))))
        self.assertLess(worst, 1e-3, "the late plane is the frames' plane at that lag")

    def test_the_elbow_orbits_and_the_hand_and_the_bones_stay(self):
        lag = 2.0
        plain = self.run_at()
        got = self.run_at(**{"elbow_overlap_" + self.side: lag})
        a, b = np.array(plain.worlds), np.array(got.worlds)
        self.assertGreater(float(np.abs(b[self.low_j, :, 3, :3] - a[self.low_j, :, 3, :3]).max()), 1e-3)
        self.assertLess(float(np.abs(b[self.hand_j, :, 3, :3] - a[self.hand_j, :, 3, :3]).max()), 1e-4)
        self.assertLess(float(np.abs(b[self.up_j, :, 3, :3] - a[self.up_j, :, 3, :3]).max()), 1e-9)
        for x, y in ((self.up_j, self.low_j), (self.low_j, self.hand_j)):
            was = np.linalg.norm(a[y][:, 3, :3] - a[x][:, 3, :3], axis=1)
            now = np.linalg.norm(b[y][:, 3, :3] - b[x][:, 3, :3], axis=1)
            self.assertLess(float(np.abs(now - was).max()), 1e-5, (x, y))

    def test_the_hands_turn_is_its_turn_that_many_frames_later_and_its_place_is_not(self):
        lag = 2.0
        plain = self.run_at()
        kin = np.array(plain.worlds)
        late = wm.shifted_cycle(kin[self.hand_j], lag)
        got = np.array(self.run_at(**{"hand_overlap_" + self.side: lag}).worlds)
        n = plain.frames
        for f in range(n):
            self.assertTrue(np.allclose(got[self.hand_j, f, :3, :3], late[f, :3, :3], atol=1e-6), f)
            self.assertTrue(np.allclose(got[self.hand_j, f, 3, :3], kin[self.hand_j, f, 3, :3], atol=1e-4), f)

    def test_the_cascade_rides_on_top_of_the_arms_own_lag(self):
        """Arm overlap L with Hand overlap h turns the hand as the frames turn it at L + h."""
        L, h = 2.0, 1.0
        kin = np.array(self.run_at().worlds)
        want = wm.shifted_cycle(kin[self.hand_j], L + h)
        got = np.array(self.run_at(**{"arm_overlap_" + self.side: L,
                                      "hand_overlap_" + self.side: h}).worlds)
        for f in range(self.w.evaluate({"balance": 0.0}).frames):
            self.assertTrue(np.allclose(got[self.hand_j, f, :3, :3], want[f, :3, :3], atol=1e-6), f)

    def test_one_side_alone(self):
        other = "r" if self.side == "l" else "l"
        plain = np.array(self.run_at().worlds)
        got = np.array(self.run_at(**{"elbow_overlap_" + self.side: 2.0,
                                      "hand_overlap_" + self.side: 2.0}).worlds)
        for j in self.chains[other]:
            self.assertTrue(np.allclose(got[j], plain[j], atol=1e-9), self.w.names[j])

    def test_a_lead_puts_the_elbow_the_other_way(self):
        plain = np.array(self.run_at().worlds)
        late = np.array(self.run_at(**{"elbow_overlap_" + self.side: 2.0}).worlds)
        lead = np.array(self.run_at(**{"elbow_overlap_" + self.side: -2.0}).worlds)
        a = late[self.low_j, :, 3, :3] - plain[self.low_j, :, 3, :3]
        b = lead[self.low_j, :, 3, :3] - plain[self.low_j, :, 3, :3]
        self.assertGreater(float(np.abs(a).max()), 1e-3)
        self.assertGreater(float(np.abs(b).max()), 1e-3)
        self.assertFalse(np.allclose(a, b, atol=1e-4))

    def test_the_cycle_is_still_a_loop(self):
        got = np.array(self.run_at(**{"elbow_overlap_" + self.side: 2.0,
                                      "hand_overlap_" + self.side: 1.5}).worlds)
        n = self.w.evaluate({"balance": 0.0}).frames
        travel = got[self.up_j, n, 3, :3] - got[self.up_j, 0, 3, :3]
        for j in self.chains[self.side]:
            self.assertTrue(np.allclose(got[j, n, :3, :3], got[j, 0, :3, :3], atol=1e-7), self.w.names[j])
            self.assertTrue(np.allclose(got[j, n, 3, :3] - got[j, 0, 3, :3], travel, atol=1e-6),
                            self.w.names[j])

    def test_the_pass_says_what_it_did(self):
        r = self.run_at(**{"elbow_overlap_" + self.side: 2.0, "hand_overlap_" + self.side: 1.5})
        said = r.info["arms"]["overlap"]
        self.assertAlmostEqual(said["elbow"], 2.0, places=6)
        self.assertAlmostEqual(said["hand"], 1.5, places=6)

    def test_balance_sees_a_cascade_with_no_arm_lag(self):
        """The carry balances a late arm, cascade and all: the Balance path must count the new knobs."""
        off = self.run_at(balance=1.0)
        on = self.run_at(balance=1.0, **{"elbow_overlap_" + self.side: 3.0,
                                         "hand_overlap_" + self.side: 3.0})
        self.assertNotAlmostEqual(off.info["balance"]["carry"], on.info["balance"]["carry"], places=6)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_walk_arm_overlap.CascadePassTests -v`
Expected: FAIL - the knobs are inert, so the elbow does not move and `said["elbow"]` raises `KeyError`.

- [ ] **Step 3: Write minimal implementation**

Replace the body of `Walk._arm_overlap` down to the `self._reattach(...)` line with this. The docstring gains
the cascade's two sentences:

```python
    def _arm_overlap(self, worlds, n, ctx, only=None):
        """The arms late by Arm overlap (frames of the new cycle; in place on `worlds`, (J, n+1, 4, 4)): each
        hand's world motion - the linear travel taken out - read that many frames earlier, and the arm rebuilt
        to it by IK from the current shoulder. So everything the arm takes from the body (the chest's turn, the
        shoulder's bob and sway) is late together with its own swing: the animator's hand trick, the IK arms'
        keys shifted. Under a pose's grip the held thing is what goes late (both sides' mean lag) and the two
        hands keep their hold on it. Runs before _arm_dynamics, so Whip takes the late arm as its target.
        The cascade (2026-10-30) lags what the IK leaves free, on top of that L: Hand overlap reads the hand's
        own TURN at L + h while its place stays at L (under a grip it is the held thing's turn, so the hold is
        kept), and Elbow overlap reads the elbow's bend PLANE at L + e (per arm, and free under a grip).
        Returns what it did (info["arms"]["overlap"])."""
        ks = ctx.get("ks") or {"l": ctx["k"], "r": ctx["k"]}
        chains = self._arm_chains()
        lags = dict((side, float(ks[side]["arm_overlap"])) for side in chains)
        elbows = dict((side, float(ks[side]["elbow_overlap"])) for side in chains)
        turns = dict((side, float(ks[side]["hand_overlap"])) for side in chains)
        pose = ctx["pose"]
        grip = bool(pose and pose.get("grip") and ctx["alpha"] > 0.0 and len(chains) == 2)
        if grip:                      # hands holding one thing move as one: the two sides' mean
            for table in (lags, turns):
                mean = sum(table.values()) / float(len(table))
                table.update(dict((side, mean) for side in table))
        biggest = lambda table: max([abs(v) for v in table.values()] or [0.0])
        out = {"frames": biggest(lags), "elbow": biggest(elbows), "hand": biggest(turns), "grip": grip}
        if not chains or max(out["frames"], out["elbow"], out["hand"]) < OVERLAP_QUIET:
            out["frames"] = out["elbow"] = out["hand"] = 0.0
            return out
        kin = worlds.copy()

        def wanted(mats, lag, turn):
            """A cycle read `lag` frames earlier, its rotation read `lag + turn` earlier (Hand overlap)."""
            want = shifted_cycle(mats, lag)
            if abs(turn) >= OVERLAP_QUIET:
                want = np.array(want)
                want[:, :3, :3] = shifted_cycle(mats, lag + turn)[:, :3, :3]
            return want
        hands = {}
        if grip:
            hold = chains["r"][-1]
            late = wanted(kin[hold], lags["r"], turns["r"])
            for side, chain in chains.items():
                hand_j = chain[-1]
                hands[side] = np.array([kin[hand_j, f] @ np.linalg.inv(kin[hold, f]) @ late[f]
                                        for f in range(n + 1)])
        else:
            for side, chain in chains.items():
                if max(abs(lags[side]), abs(turns[side]), abs(elbows[side])) >= OVERLAP_QUIET:
                    hands[side] = wanted(kin[chain[-1]], lags[side], turns[side])
        hints = {}
        for side, chain in chains.items():
            if side in hands and abs(elbows[side]) >= OVERLAP_QUIET:
                hints[side] = late_bend(kin[chain[0]], kin[chain[1]], kin[chain[2]],
                                        lags[side] + elbows[side])
        self._reattach(worlds, kin, self._arm_to_hand(kin, n, chains, hands, hints), only)
        return out
```

Then the Balance path's `moved_arms`, near line 2731 - the carry must balance a late arm whatever lagged it:

```python
            moved_arms = any(ks[s]["arm_drag"] > 0.0
                             or abs(ks[s]["arm_overlap"]) >= OVERLAP_QUIET
                             or abs(ks[s]["elbow_overlap"]) >= OVERLAP_QUIET
                             or abs(ks[s]["hand_overlap"]) >= OVERLAP_QUIET
                             for s in SIDES)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_walk_arm_overlap -v`
Expected: PASS, the whole file.

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_walkmodel tests.test_walkgait tests.test_walk_panel -v`
Expected: PASS (the engine's own suite must not move).

- [ ] **Step 5: Commit**

```bash
git add SkeldarAnim/maya_walk/model.py tests/test_walk_arm_overlap.py
git commit -m "feat(walk): the cascade pass - the hand's turn at L+h, the elbow's plane at L+e"
```

---

### Task 4: the two parameters on the card

**Files:**
- Modify: `SkeldarAnim/maya_walk/gait.py` (the `PARAMS` table's Arms block, after the `arm_overlap` row near
  line 213; `engine_knobs` near line 806; `ranges`' cap loop near line 1169)
- Test: `tests/test_walk_arm_overlap.py` (the existing `ParameterTests` class, line 261)

**Interfaces:**
- Consumes: the engine knobs `elbow_overlap` / `hand_overlap` (Task 1), `gait.overlap_cap(walk)`.
- Produces: `gait.P["elbow_overlap"]` and `gait.P["hand_overlap"]` - `ARMS` group, label `Elbow overlap` /
  `Hand overlap`, unit `ms`, kind `added`, `sided=True`, own value 0, the slider half the cycle either way.
  `gait.engine_knobs(...)` converts both to frames at the output rate.

- [ ] **Step 1: Write the failing test**

Add to `class ParameterTests` in `tests/test_walk_arm_overlap.py` (it already has a `walk()`-based `setUp`
and an `own` / `values` helper - reuse whatever the neighbouring `arm_overlap` tests use):

```python
    def test_the_two_cascade_parameters_sit_with_the_arm_in_ms(self):
        names = [p.name for p in gait.PARAMS]
        self.assertEqual(names[names.index("arm_overlap") + 1], "elbow_overlap")
        self.assertEqual(names[names.index("arm_overlap") + 2], "hand_overlap")
        for name, label in (("elbow_overlap", "Elbow overlap"), ("hand_overlap", "Hand overlap")):
            p = gait.P[name]
            self.assertEqual(p.group, gait.ARMS, name)
            self.assertEqual(p.label, label)
            self.assertEqual(p.unit, "ms", name)
            self.assertEqual(p.kind, "added", name)
            self.assertTrue(p.sided, name)

    def test_the_old_lag_knobs_are_still_there(self):
        for name in ("arm_lag", "elbow_lag", "hand_lag", "elbow", "arms_forward", "shoulders", "arm_overlap"):
            self.assertIn(name, gait.P, name)

    def test_their_own_is_zero_and_the_slider_reaches_half_the_cycle(self):
        w = walk()
        own = gait.own(w)
        rng = gait.ranges(own, w.leg_length, w)
        cap = gait.overlap_cap(w)
        for name in ("elbow_overlap", "hand_overlap"):
            for key in (name, name + "_l", name + "_r"):
                self.assertAlmostEqual(gait.own_value(own, key), 0.0, places=9, msg=key)
                self.assertEqual(rng[key], (-cap, cap), key)

    def test_ms_become_frames_at_the_output_rate(self):
        w = walk()
        own = gait.own(w)
        for name in ("elbow_overlap", "hand_overlap"):
            e30 = gait.engine_knobs(w, gait.values(own, {name: 150.0}), fps_out=30.0)
            e24 = gait.engine_knobs(w, gait.values(own, {name: 150.0}), fps_out=24.0)
            self.assertAlmostEqual(e30[name + "_r"], 4.5, places=6, msg=name)
            self.assertAlmostEqual(e24[name + "_r"], 3.6, places=6, msg=name)

    def test_zero_asks_the_engine_for_nothing(self):
        w = walk()
        e = gait.engine_knobs(w, gait.values(gait.own(w), {}), fps_out=30.0)
        for name in ("elbow_overlap", "hand_overlap"):
            for s in ("l", "r"):
                self.assertAlmostEqual(e[name + "_" + s], 0.0, places=9, msg=name)
```

Copy the exact spellings of `gait.own`, `gait.values`, `gait.own_value` and `engine_knobs`' keyword from the
`arm_overlap` tests that already pass in this class - this plan's names follow them, but the file is the
authority.

- [ ] **Step 2: Run test to verify it fails**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_walk_arm_overlap.ParameterTests -v`
Expected: FAIL - `KeyError: 'elbow_overlap'` in `gait.P`.

- [ ] **Step 3: Write minimal implementation**

In `gait.py`'s `PARAMS`, immediately after the `arm_overlap` row:

```python
    Param("elbow_overlap", ARMS, "Elbow overlap", "ms", "added", sided=True,
          rule=_fixed(-OVERLAP_MAX, OVERLAP_MAX),
          tip="The elbow's orbit about the shoulder-wrist line late by this many milliseconds, on top of Arm "
              "overlap - the hand stays where Arm overlap puts it and the bones keep their lengths, so this "
              "is a late orbit, not a late bend. Free under a two-handed grip"),
    Param("hand_overlap", ARMS, "Hand overlap", "ms", "added", sided=True,
          rule=_fixed(-OVERLAP_MAX, OVERLAP_MAX),
          tip="The hand's own turn late by this many milliseconds, on top of Arm overlap - its place stays "
              "where Arm overlap puts it, so this is the wrist breaking late. Under a two-handed grip it is "
              "the weapon's own turn that lags its travel, and the hold is kept"),
```

In `engine_knobs`, right after the `arm_overlap` line:

```python
        e["elbow_overlap" + sfx] = sv("elbow_overlap") * fps / 1000.0  # ms -> frames of the new cycle (own 0)
        e["hand_overlap" + sfx] = sv("hand_overlap") * fps / 1000.0    # ms -> frames (own 0)
```

In `ranges`, the cap loop - the cascade's sliders reach as far as the arm's, and for the same reason:

```python
        cap = overlap_cap(walk)       # Arm overlap and the cascade: half the cycle either way
        for name in ("arm_overlap", "elbow_overlap", "hand_overlap"):
            for key in [name + "_" + s for s in SIDES] + [name]:
                out[key] = (-cap, cap)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_walk_arm_overlap -v`
Expected: PASS.

Run the whole walk suite:
`& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -p "test_walk*.py" -v`
Expected: PASS. If a Gait Builder or panel test counts the Arms group's sliders, read it and update the count
- that is a real consequence of two new knobs, not a failure to work around.

- [ ] **Step 5: Commit**

```bash
git add SkeldarAnim/maya_walk/gait.py tests/test_walk_arm_overlap.py
git commit -m "feat(walk): Elbow overlap and Hand overlap on the card, ms, half the cycle"
```

---

### Task 5: the verify on the animator's own cycle

**Files:**
- Modify: `docs/superpowers/plans/walkparam/verify_walk_arm_overlap.py` (a new phase, `cascade`)

**Interfaces:**
- Consumes: the finished feature. The script already loads the animator's walks folder, builds the walker,
  reads a pose card and runs `evaluate` with Balance and In place off for the geometry gates - reuse its own
  helpers, do not write new ones.
- Produces: gates printed in its own format, `0 of N gates failed` on success.

- [ ] **Step 1: Read the script and find its shape**

Run: `sed -n '1,80p' docs/superpowers/plans/walkparam/verify_walk_arm_overlap.py`
and `grep -n "def phase\|PHASES\|def gate\|def main" docs/superpowers/plans/walkparam/verify_walk_arm_overlap.py`

Note the gate helper's name and signature, how a phase is registered, and how the three cases (the grip's
pose, `DG_Idle`, no pose) are set up.

- [ ] **Step 2: Add the phase**

A new phase `cascade`, for each of the three cases, with `balance` 0 and In place off:

1. **the elbow's late plane** - run at `elbow_overlap` 133 ms; against the lag-0 run, the rebuilt arm's bend
   plane equals `model.late_bend(up, low, hand, L + e)` projected on the arm's own line, to under 1e-3 deg
   (print the worst);
2. **the elbow really orbited** - the elbow's own place moved by more than 1 cm (print it);
3. **the hand did not** - its place within the 2026-10-29 tolerance of the lag-0 run, its turn equal to the
   frames' turn at L + h for a `hand_overlap` run;
4. **the bones are kept** - every arm bone's length constant to 1e-5 cm;
5. **the shoulder is bit-exact** - `np.array_equal` against the lag-0 run;
6. **the loop is closed** - the last frame's rotation equals the first's to 1e-7, its place to the cycle's
   travel;
7. **the grip is held** (the sword case only) - the left hand's transform in the right's unchanged to 1e-12
   on every frame, with `hand_overlap` 133 ms set;
8. **0/0/0 is matrix for matrix** - `np.array_equal` of the whole `worlds`;
9. **a cascade with Arm overlap 0** keeps the hand's place to 1e-4 cm while the elbow moves;
10. **a lead** (-133 ms) moves the elbow the other way from +133;
11. **Whip takes it** - at `whip` 0.3 the result is neither the whip alone nor the cascade alone (print all
    three distances).

- [ ] **Step 3: Run it**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_arm_overlap.py cascade`
Expected: `0 of N gates failed`. Every number printed, so the spec's "The proof" section can be filled with
real figures rather than promises.

- [ ] **Step 4: Run the whole script, and the neighbours**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_arm_overlap.py`
Expected: `0 of N gates failed` - the 2026-10-29 gates still green beside the new ones.

Then, for each of `verify_walk.py`, `verify_walk_gait.py`, `verify_walk_own.py`, `verify_walk_many.py`: run it
on this worktree AND on a clean worktree of the commit before this work, and compare. They fail identically
there (the 2026-10-29 pass recorded the same). Record which, with their counts.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/plans/walkparam/verify_walk_arm_overlap.py
git commit -m "test(walk): the cascade's gates on the animator's own cycle"
```

---

### Task 6: the spec's measured numbers, and CLAUDE.md

**Files:**
- Modify: `docs/superpowers/specs/2026-10-30-walk-arm-cascade-design.md` (the "The proof" section)
- Modify: `CLAUDE.md` (the walk section's `Arm overlap` bullet, which today ends with the OPEN cascade note)

- [ ] **Step 1: Fill the spec's proof with the real figures**

Replace each promised tolerance in "The proof" with the number the run printed, and add the unit-test count.
Remove the OPEN wording - it is built now.

- [ ] **Step 2: Rewrite CLAUDE.md's cascade note**

The bullet that today reads "**OPEN, asked for and not built: the cascade**" becomes the built record: the two
knobs, the one rule, the grip, what it costs, the proof's figures, and "Not seen in a GUI Maya: after Check
update". Road B stays named as offered, measured and declined, so nobody re-proposes it.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md docs/superpowers/specs/2026-10-30-walk-arm-cascade-design.md
git commit -m "docs(walk): the arms' cascade, built and measured"
```

---

## Self-Review

**Spec coverage:**

| Spec section | Task |
|---|---|
| The two roads, and why A | - (decided; B explicitly not built, recorded in Task 6) |
| The two knobs (ms, sided, Arms, after `Arm overlap`, half the cycle) | 1 (engine), 4 (card) |
| Engine knobs, `ENGINE_ONLY`, `SIDED`, the ms conversion | 1, 4 |
| The hand's place at L, its turn at L + h | 3 |
| The elbow's bend plane at L + e | 2 (`late_bend`, the hint), 3 (the pass) |
| The hint/source split trap | 2 |
| `_grip_motion` unchanged | 2 (its test) |
| The grip: `Hand overlap` on the held thing, the mean; `Elbow overlap` per arm | 3, 5 (gate 7) |
| Zero is matrix for matrix; the Balance path counts the new knobs | 3 |
| The cascade alone, with `Arm overlap` 0 | 3, 5 (gate 9) |
| A lead | 3, 5 (gate 10) |
| The proof's gates, the neighbours compared against a clean worktree | 5 |

**Placeholder scan:** none - every code step carries the code, every run step the command and the expected
result. Task 5 names its eleven gates and their tolerances; it does not carry their code, because the script's
own gate helper is the authority and Step 1 is to read it. Task 1 and Task 4 each say that the test file's own
spellings win over this plan's if they differ.

**Type consistency:** `late_bend(up, low, hand, lag) -> (n+1, 3)` is defined in Task 2 and used in Tasks 2, 3
and 5. `_arm_to_hand(kin, n, chains, hands, hints=None)` with `hints` `{side: (n+1, 3)}` is defined in Task 2
and used in Task 3. The engine knob names `elbow_overlap` / `hand_overlap` are the same string in Tasks 1, 3
and 4. `_arm_overlap`'s return gains `"elbow"` and `"hand"` in Task 3 and is read in Task 3's test.
