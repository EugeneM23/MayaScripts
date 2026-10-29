# Walk Builder: Arm overlap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One new Walk Builder parameter, `Arm overlap` in milliseconds, that puts the whole arm late the way an
animator does it by hand - the arm's world motion read that many frames earlier and the arm rebuilt to it by IK
from the current shoulder.

**Architecture:** A post-pass over the already-built cycle (`Walk._arm_overlap`), run from `evaluate`
immediately before the arms' springs so Whip takes the late arm as its target. It reads the hand's world matrix
series `lag` frames earlier (the linear travel taken out for the shift and put back, so the cycle stays a loop)
and hands it to the two-bone IK rebuild that `_grip_motion` already does - that rebuild is factored out into one
shared method both use. Under a pose's grip the held thing is what goes late and both hands keep their hold on
it, exactly as the springs' grip branch does.

**Tech Stack:** Python 2/3-compatible numpy in `SkeldarAnim/maya_walk/` (`model.py` the engine - stdlib and
numpy only, no Maya; `gait.py` the animator's parameters - stdlib and numpy only; `scene.py` the Maya side).
Unit tests: stdlib `unittest` run by mayapy. The live proof: a mayapy standalone verify script.

## Global Constraints

- `SkeldarAnim/maya_walk/model.py` imports no Maya - a subprocess test in `tests/test_walkmodel.py`
  (`PurityTests`) enforces it. Use numpy and the module's own helpers only.
- `SkeldarAnim/maya_walk/gait.py` likewise imports no Maya.
- Run the unit tests with Maya's interpreter; there is no system Python on this machine:
  `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_walk_arm_overlap -v`
  (from the repository root; `tests/__init__.py` puts `SkeldarAnim/` on `sys.path`).
- **Nothing is deleted.** `Arm lag`, `Elbow lag`, `Hand lag`, `Elbow`, `Arms forward` and `Shoulders` stay
  exactly as they are, in the table and in the engine.
- The new parameter's name is `arm_overlap`, its label `Arm overlap`, its unit `ms`, its kind `added`, sided,
  range `-100.0 .. 300.0`, group `MAIN`, placed immediately after `arm_lag` in `gait.PARAMS`.
- The engine's knob is `arm_overlap`, in **frames of the new cycle**, default `0.0`, range `-20.0 .. 60.0`,
  added to `KNOBS` inside the lag block (after `exaggeration`, so it lands in `ENGINE_ONLY`) and to `SIDED`.
- `OVERLAP_QUIET = 1e-6` (frames): below it the pass returns having touched nothing.
- Do not change `model.describe` or any status line. The Pick line is not part of this work.
- Never write into `C:/Users/MY PC/Documents/maya/SkeldarWalks` - the verify copies it to a temp folder and
  points `scene.WALKS` at the copy.
- Never send anything to the animator's Maya on port 7004 except read-only probes.

---

### Task 1: `shifted_cycle` and the engine knob

**Files:**
- Modify: `SkeldarAnim/maya_walk/model.py` (the `KNOBS` tuple's lag block around line 109; `SIDED` around
  line 160; a new module function beside `_resampled`, around line 3400)
- Test: `tests/test_walk_arm_overlap.py` (create)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `maya_walk.model.shifted_cycle(mats, lag)` -> `numpy.ndarray` `(n+1, 4, 4)`; the module constant
  `maya_walk.model.OVERLAP_QUIET` (float); the knob name `"arm_overlap"` in `model.DEFAULTS`,
  `model.RANGES`, `model.SIDED` and `model.SIDE_KNOBS`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_walk_arm_overlap.py`:

```python
"""Walk Builder's Arm overlap: the time shift, the IK rebuild it feeds, and the pass on the cycle."""

import math
import unittest

import numpy as np

from tests.test_walkmodel import positions, rot_y, walk, wm


def cycle(n=8, travel=(0.0, 0.0, 80.0)):
    """A cycle of world matrices (n+1, 4, 4): a full turn about Y, a circle in place, and a travel - the last
    frame the first moved by the travel, as every cycle of the model is."""
    out = np.tile(np.eye(4), (n + 1, 1, 1))
    per = np.array(travel, float) / float(n)
    for f in range(n + 1):
        a = 360.0 * (f % n) / float(n)
        out[f, :3, :3] = rot_y(a)
        out[f, 3, :3] = np.array([10.0 * math.cos(math.radians(a)), 3.0 * math.sin(math.radians(a)),
                                  0.0]) + per * f
    return out


def rel(mats, f, per):
    """A frame's place with the travel taken out."""
    return mats[f, 3, :3] - per * f


class ShiftedCycleTests(unittest.TestCase):

    def test_no_lag_gives_the_input_back(self):
        mats = cycle()
        self.assertTrue(np.array_equal(wm.shifted_cycle(mats, 0.0), mats))

    def test_a_whole_lag_is_the_frame_that_many_earlier(self):
        mats, n = cycle(), 8
        per = (mats[n, 3, :3] - mats[0, 3, :3]) / float(n)
        got = wm.shifted_cycle(mats, 2.0)
        for f in range(n + 1):
            was = (f - 2) % n
            self.assertTrue(np.allclose(got[f, :3, :3], mats[was, :3, :3], atol=1e-9), f)
            self.assertTrue(np.allclose(rel(got, f, per), rel(mats, was, per), atol=1e-9), f)

    def test_a_fractional_lag_falls_between_the_two_frames(self):
        mats = cycle()
        half = wm.shifted_cycle(mats, 2.5)
        early, late = wm.shifted_cycle(mats, 3.0), wm.shifted_cycle(mats, 2.0)
        turn = lambda a, b: math.degrees(float(np.linalg.norm(wm.log_rot(a[:3, :3].T @ b[:3, :3]))))
        self.assertAlmostEqual(turn(early[4], half[4]), turn(half[4], late[4]), places=6)
        self.assertTrue(np.allclose(half[4, 3, :3], 0.5 * (early[4, 3, :3] + late[4, 3, :3]), atol=1e-9))

    def test_the_result_is_a_cycle_again(self):
        mats, n = cycle(), 8
        travel = mats[n, 3, :3] - mats[0, 3, :3]
        for lag in (1.0, 2.5, -3.0):
            got = wm.shifted_cycle(mats, lag)
            self.assertTrue(np.allclose(got[n, :3, :3], got[0, :3, :3], atol=1e-9), lag)
            self.assertTrue(np.allclose(got[n, 3, :3] - got[0, 3, :3], travel, atol=1e-9), lag)

    def test_a_negative_lag_runs_the_other_way(self):
        mats, n = cycle(), 8
        per = (mats[n, 3, :3] - mats[0, 3, :3]) / float(n)
        got = wm.shifted_cycle(mats, -2.0)
        self.assertTrue(np.allclose(rel(got, 0, per), rel(mats, 2, per), atol=1e-9))


class KnobTests(unittest.TestCase):

    def test_the_engine_carries_a_sided_arm_overlap_knob(self):
        self.assertEqual(wm.DEFAULTS["arm_overlap"], 0.0)
        self.assertEqual(wm.RANGES["arm_overlap"], (-20.0, 60.0))
        self.assertIn("arm_overlap", wm.SIDED)
        self.assertEqual(wm.SIDE_KNOBS["arm_overlap_l"], "arm_overlap")
        self.assertIn("arm_overlap", wm.ENGINE_ONLY)
        k = wm.knobs(arm_overlap_l=3.0)
        self.assertEqual(wm.sided(k)["l"]["arm_overlap"], 3.0)
        self.assertEqual(wm.sided(k)["r"]["arm_overlap"], 0.0)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_walk_arm_overlap -v`

Expected: FAIL - `AttributeError: module 'maya_walk.model' has no attribute 'shifted_cycle'` and
`KeyError: 'arm_overlap'`.

- [ ] **Step 3: Add the knob**

In `SkeldarAnim/maya_walk/model.py`, in the `KNOBS` tuple, right after the `("hand_lag", 0.0, -10.0, 15.0),`
line, add:

```python
    # The arms' overlap (2026-10-29): the whole arm late by this many frames of the new cycle - its hand's
    # world motion (the linear travel out) read that much earlier and the arm rebuilt to it by IK from the
    # current shoulder, so what the arm takes from the body (the chest's turn, the shoulder's bob and sway) is
    # late with its own swing. Per side; under a grip the held thing goes late and both hands keep their hold
    ("arm_overlap", 0.0, -20.0, 60.0),
```

In the `SIDED` tuple, add `"arm_overlap"` after `"hand_lag"`:

```python
SIDED = ("stance", "lift", "swing_out", "leg_turn", "knee_foot", "foot_lag", "foot_flex", "foot_flat", "ground_time",
         "arms", "elbow", "arm_drag", "arm_bounce", "arm_fwd_add", "arm_out_add", "elbow_add",
         "elbow_swing_add", "shoulder_add", "toe_add", "knee_bend", "knee_soft", "g_arm", "g_elbow",
         "arm_swing_add", "duty", "push", "heel_strike", "slap", "arm_lag", "elbow_lag", "hand_lag",
         "arm_overlap", "spring_comp")
```

- [ ] **Step 4: Add the constant and `shifted_cycle`**

Beside the other arm constants (`ARM_INERTIA`, `ARM_HARMONICS`, around line 204) add:

```python
OVERLAP_QUIET = 1e-6      # frames: an Arm overlap under this touches nothing
```

Add the module function immediately after `Walk._resampled`'s class ends is wrong - it must be a **module**
function. Put it beside the other module-level helpers, right after the `two_bone` / `meet` block (around
line 600):

```python
def shifted_cycle(mats, lag):
    """A cycle of world matrices (n+1, 4, 4) - its last frame its first moved by the cycle's travel - read
    `lag` frames earlier. The linear travel is taken out for the shift and put back at each frame, so the
    result is a cycle again and a travelling cycle does not leave the shifted thing behind; a fractional lag
    falls between the two frames it lies between (the rotation slerped, the place lerped). lag 0: the input,
    matrix for matrix."""
    if not lag:
        return np.array(mats)
    mats = np.asarray(mats, float)
    n = mats.shape[0] - 1
    per = (mats[n, 3, :3] - mats[0, 3, :3]) / float(n)
    rots = np.array([orthonormal(mats[f, :3, :3]) for f in range(n)])
    place = np.array([mats[f, 3, :3] - per * f for f in range(n)])
    out = np.tile(np.eye(4), (n + 1, 1, 1))
    for f in range(n + 1):
        g = (f - lag) % n
        lo = int(math.floor(g)) % n
        hi = (lo + 1) % n
        a = g - math.floor(g)
        out[f, :3, :3] = rots[lo] @ exp_rot(a * log_rot(rots[lo].T @ rots[hi]))
        out[f, 3, :3] = (1.0 - a) * place[lo] + a * place[hi] + per * f
    return out
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_walk_arm_overlap -v`

Expected: PASS, 7 tests.

- [ ] **Step 6: Run the model's own suite to be sure nothing moved**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_walkmodel -v`

Expected: PASS, every test (the purity test included).

- [ ] **Step 7: Commit**

```bash
git add SkeldarAnim/maya_walk/model.py tests/test_walk_arm_overlap.py
git commit -m "feat(walk): the engine's arm_overlap knob and the cycle's time shift"
```

---

### Task 2: the IK rebuild factored out of `_grip_motion`

**Files:**
- Modify: `SkeldarAnim/maya_walk/model.py` (`Walk._grip_motion`, around lines 3545-3607)
- Test: `tests/test_walk_arm_overlap.py` (append a class)

**Interfaces:**
- Consumes: nothing from Task 1 (independent of it, but shares the file).
- Produces: `Walk._arm_to_hand(self, kin, n, chains, hands)` -> `{joint index: numpy.ndarray (n+1, 4, 4)}`.
  `kin` is the frames as built `(J, n+1, 4, 4)`, `n` the cycle's frames, `chains` what
  `Walk._arm_chains()` returns (`{side: [upperarm, lowerarm, hand] indices}`), `hands`
  `{side: (n+1, 4, 4)}` the wanted hand matrices - a side missing from `hands` is left alone and gets no
  entry in the result.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_walk_arm_overlap.py`:

```python
class ArmToHandTests(unittest.TestCase):
    """The shared two-bone IK rebuild: an arm taken to a wanted hand from the current shoulder."""

    def setUp(self):
        self.w = walk()
        self.r = self.w.evaluate({"balance": 0.0})
        self.kin = np.array(self.r.worlds)
        self.n = self.r.frames
        self.chains = self.w._arm_chains()

    def test_the_arms_own_hands_give_the_arms_back(self):
        hands = dict((side, np.array(self.kin[chain[-1]])) for side, chain in self.chains.items())
        got = self.w._arm_to_hand(self.kin, self.n, self.chains, hands)
        self.assertEqual(len(got), 3 * len(self.chains))
        for j, m in got.items():
            self.assertTrue(np.allclose(m[:, 3, :3], self.kin[j][:, 3, :3], atol=1e-6), self.w.names[j])
            self.assertTrue(np.allclose(m[:, :3, :3], self.kin[j][:, :3, :3], atol=1e-6), self.w.names[j])

    def test_a_moved_hand_is_reached_and_the_bones_keep_their_lengths(self):
        side = sorted(self.chains)[0]
        up_j, low_j, hand_j = self.chains[side]
        want = np.array(self.kin[hand_j])
        want[:, 3, 0] += 2.0
        got = self.w._arm_to_hand(self.kin, self.n, self.chains, {side: want})
        self.assertNotIn(self.chains["r" if side == "l" else "l"][0], got)
        self.assertTrue(np.allclose(got[hand_j][:, 3, :3], want[:, 3, :3], atol=1e-6))
        for a, b in ((up_j, low_j), (low_j, hand_j)):
            was = np.linalg.norm(self.kin[b][:, 3, :3] - self.kin[a][:, 3, :3], axis=1)
            now = np.linalg.norm(got[b][:, 3, :3] - got[a][:, 3, :3], axis=1)
            self.assertLess(float(np.abs(now - was).max()), 1e-6, (a, b))

    def test_a_hand_past_the_arms_reach_is_clamped_on_its_line(self):
        side = sorted(self.chains)[0]
        up_j, _, hand_j = self.chains[side]
        want = np.array(self.kin[hand_j])
        want[:, 3, 0] += 500.0
        got = self.w._arm_to_hand(self.kin, self.n, self.chains, {side: want})
        low_j = self.chains[side][1]
        l1 = float(np.linalg.norm(self.w.lt[low_j].mean(axis=0)))
        l2 = float(np.linalg.norm(self.w.lt[hand_j].mean(axis=0)))
        reach = np.linalg.norm(got[hand_j][:, 3, :3] - got[up_j][:, 3, :3], axis=1)
        self.assertLess(float(np.abs(reach - (l1 + l2)).max()), 1e-6, "clamped at the arm's own length")
        for f in range(self.n):
            to_want = want[f, 3, :3] - got[up_j][f, 3, :3]
            to_got = got[hand_j][f, 3, :3] - got[up_j][f, 3, :3]
            cos = float(np.dot(to_want, to_got) / (np.linalg.norm(to_want) * np.linalg.norm(to_got)))
            self.assertGreater(cos, 1.0 - 1e-9, f)      # clamped along the line to the wanted hand

    def test_the_springs_grip_still_reaches_its_hands(self):
        """_grip_motion keeps working through the shared rebuild: an arm drag with a grip runs and the bones
        keep their lengths (the grip itself is proven on the real cycle by verify_walk_arm_overlap.py)."""
        r = self.w.evaluate({"arm_drag": 2.0, "balance": 0.0})
        for side, chain in self.chains.items():
            for a, b in zip(chain, chain[1:]):
                d = np.linalg.norm(positions(r, self.w.names[b], self.w)
                                   - positions(r, self.w.names[a], self.w), axis=1)
                self.assertLess(float(np.ptp(d)), 1e-9, (side, a, b))
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_walk_arm_overlap.ArmToHandTests -v`

Expected: FAIL - `AttributeError: 'Walk' object has no attribute '_arm_to_hand'` on the first three tests
(the fourth passes already).

- [ ] **Step 3: Add `_arm_to_hand` and have `_grip_motion` call it**

In `SkeldarAnim/maya_walk/model.py`, add the method immediately before `_grip_motion`:

```python
    def _arm_to_hand(self, kin, n, chains, hands):
        """Each arm rebuilt to a wanted hand: `hands` {side: (n+1, 4, 4)} -> {joint: (n+1, 4, 4)} for the upper
        arm, the forearm and the hand (a side not in `hands` is left out). From the CURRENT shoulder - the
        arm's pivot is the body's - the elbow bending the way the frames bend it, the bones keeping their
        lengths (a hand past the arm's reach is clamped along its own line by two_bone). The one IK the
        springs' grip (_grip_motion) and the overlap (_arm_overlap) both reach their hands with."""
        out = {}
        for side, chain in chains.items():
            want = hands.get(side)
            if want is None:
                continue
            up_j, low_j, hand_j = chain
            l1, l2 = (float(np.linalg.norm(self.lt[j].mean(axis=0))) for j in (low_j, hand_j))
            mu, ml, mh = (np.tile(np.eye(4), (n + 1, 1, 1)) for _ in range(3))
            for f in range(n + 1):
                hand = want[f]
                sh, el, wr = kin[up_j, f, 3, :3], kin[low_j, f, 3, :3], kin[hand_j, f, 3, :3]
                e = _unit(wr - sh)
                bend = (el - sh) - np.dot(el - sh, e) * e
                bend = _unit(bend) if np.linalg.norm(bend) > 1e-4 else _any_perpendicular(e)
                knee, reached, _ = two_bone(sh, hand[3, :3], l1, l2, bend, 1.0)
                e2 = _unit(reached - sh)
                bend2 = _unit((knee - sh) - np.dot(knee - sh, e2) * e2)
                normal, normal2 = _unit(_cross3(e, bend)), _unit(_cross3(e2, bend2))
                mu[f, :3, :3] = orthonormal(kin[up_j, f, :3, :3]) @ align(_unit(el - sh), normal,
                                                                          _unit(knee - sh), normal2)
                ml[f, :3, :3] = orthonormal(kin[low_j, f, :3, :3]) @ align(_unit(wr - el), normal,
                                                                           _unit(reached - knee), normal2)
                mu[f, 3, :3], ml[f, 3, :3] = sh, knee
                mh[f, :3, :3], mh[f, 3, :3] = hand[:3, :3], reached
            out[up_j], out[low_j], out[hand_j] = mu, ml, mh
        return out
```

Then replace `_grip_motion`'s whole tail - the block that starts `out = {}` and ends `return out, used` - with:

```python
        hands = {}
        for side, chain in chains.items():
            hand_j = chain[-1]
            hands[side] = np.array([kin[hand_j, f] @ np.linalg.inv(kin[hold, f]) @ held[f]
                                    for f in range(n + 1)])
        return self._arm_to_hand(kin, n, chains, hands), used
```

Nothing else in `_grip_motion` changes: it still builds `held` through its spring and still takes the bend
plane from the frames (that is now inside `_arm_to_hand`). Its docstring's last sentence ("both arms reach
their hands by IK...") still holds.

- [ ] **Step 4: Run the test to verify it passes**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_walk_arm_overlap -v`

Expected: PASS, 11 tests.

- [ ] **Step 5: Run the model's suite - the grip's springs must be unchanged**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_walkmodel -v`

Expected: PASS, every test.

- [ ] **Step 6: Commit**

```bash
git add SkeldarAnim/maya_walk/model.py tests/test_walk_arm_overlap.py
git commit -m "refactor(walk): one IK rebuild for the grip's springs and the overlap"
```

---

### Task 3: the `_arm_overlap` pass

**Files:**
- Modify: `SkeldarAnim/maya_walk/model.py` (a new method after `_arm_to_hand`; `evaluate`'s frame pass around
  line 2759; Balance's `armed()` around line 2710 and its `swinging` line around line 2703)
- Test: `tests/test_walk_arm_overlap.py` (append a class)

**Interfaces:**
- Consumes: `shifted_cycle(mats, lag)` and `OVERLAP_QUIET` (Task 1), `_arm_to_hand(kin, n, chains, hands)`
  (Task 2).
- Produces: `Walk._arm_overlap(self, worlds, n, ctx, only=None)` -> `{"frames": float, "grip": bool}`, which
  `evaluate` puts on `result.info["arms"]["overlap"]`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_walk_arm_overlap.py`:

```python
def body_frame(result, w, f):
    """The root's world matrix at frame f - the body's own space."""
    return result.worlds[w.index["root"], f]


def in_body(result, w, leaf, f):
    """A joint's place in the body's own space at frame f."""
    m = body_frame(result, w, f)
    return (result.worlds[w.index[leaf], f, 3, :3] - m[3, :3]) @ m[:3, :3].T


class OverlapPassTests(unittest.TestCase):
    """The pass itself on the synthetic walker (the grip is proven on the animator's cycle by the verify)."""

    def test_no_overlap_leaves_every_joint_untouched(self):
        w = walk()
        plain = w.evaluate({"arm_drag": 0.0, "balance": 0.0})
        same = w.evaluate({"arm_drag": 0.0, "balance": 0.0, "arm_overlap": 0.0})
        self.assertTrue(np.array_equal(plain.worlds, same.worlds))
        self.assertEqual(same.info["arms"]["overlap"]["frames"], 0.0)

    def test_the_hand_walks_the_lag_0_path_that_many_frames_earlier(self):
        w = walk()
        plain = w.evaluate({"arm_drag": 0.0, "balance": 0.0})
        late = w.evaluate({"arm_drag": 0.0, "balance": 0.0, "arm_overlap": 2.0})
        n = plain.frames
        self.assertEqual(late.info["arms"]["overlap"]["frames"], 2.0)
        self.assertFalse(late.info["arms"]["overlap"]["grip"])
        worst = 0.0
        for side in "lr":
            for f in range(n):
                was = in_body(plain, w, "hand_" + side, (f - 2) % n)
                now = in_body(late, w, "hand_" + side, f)
                worst = max(worst, float(np.linalg.norm(now - was)))
        self.assertLess(worst, 1.0, "the hand is the lag-0 hand two frames earlier, to the IK's clamp")
        moved = float(np.linalg.norm(in_body(late, w, "hand_l", 0) - in_body(plain, w, "hand_l", 0)))
        self.assertGreater(moved, 1.0, "and it did move")

    def test_the_shoulder_does_not_move_and_the_bones_keep_their_lengths(self):
        w = walk()
        plain = w.evaluate({"arm_drag": 0.0, "balance": 0.0})
        late = w.evaluate({"arm_drag": 0.0, "balance": 0.0, "arm_overlap": 3.0})
        for side in "lr":
            self.assertTrue(np.allclose(positions(late, "upperarm_" + side, w),
                                        positions(plain, "upperarm_" + side, w), atol=1e-9), side)
            for a, b in (("upperarm_", "lowerarm_"), ("lowerarm_", "hand_")):
                was = np.linalg.norm(positions(plain, b + side, w) - positions(plain, a + side, w), axis=1)
                now = np.linalg.norm(positions(late, b + side, w) - positions(late, a + side, w), axis=1)
                self.assertLess(float(np.abs(now - was).max()), 1e-6, (side, a, b))

    def test_the_cycle_is_still_a_loop(self):
        w = walk()
        r = w.evaluate({"arm_drag": 0.0, "balance": 0.0, "arm_overlap": 2.5})
        moved = r.worlds[:, -1] - r.worlds[:, 0]
        self.assertLess(float(np.abs(moved[:, :3, :3]).max()), 1e-9)
        self.assertLess(float(np.abs(moved[:, 3, :3] - [0.0, 0.0, 120.0]).max()), 1e-6)

    def test_one_side_alone(self):
        w = walk()
        plain = w.evaluate({"arm_drag": 0.0, "balance": 0.0})
        late = w.evaluate({"arm_drag": 0.0, "balance": 0.0, "arm_overlap_l": 3.0})
        self.assertGreater(float(np.abs(positions(late, "hand_l", w) - positions(plain, "hand_l", w)).max()), 1.0)
        self.assertTrue(np.allclose(positions(late, "hand_r", w), positions(plain, "hand_r", w), atol=1e-9))

    def test_a_lead_puts_the_hand_as_far_the_other_way(self):
        w = walk()
        plain = w.evaluate({"arm_drag": 0.0, "balance": 0.0})
        late = w.evaluate({"arm_drag": 0.0, "balance": 0.0, "arm_overlap": 2.0})
        lead = w.evaluate({"arm_drag": 0.0, "balance": 0.0, "arm_overlap": -2.0})
        back = float(np.abs(positions(late, "hand_l", w) - positions(plain, "hand_l", w)).max())
        ahead = float(np.abs(positions(lead, "hand_l", w) - positions(plain, "hand_l", w)).max())
        self.assertAlmostEqual(back, ahead, delta=0.25 * back)

    def test_whip_takes_the_late_arm_as_its_target(self):
        w = walk()
        plain = w.evaluate({"arm_drag": 0.0, "balance": 0.0})
        lag = w.evaluate({"arm_drag": 0.0, "balance": 0.0, "arm_overlap": 2.0})
        whip = w.evaluate({"arm_drag": 2.0, "arm_bounce": 0.0, "balance": 0.0})
        both = w.evaluate({"arm_drag": 2.0, "arm_bounce": 0.0, "balance": 0.0, "arm_overlap": 2.0})
        off = lambda r: float(np.abs(positions(r, "hand_l", w) - positions(plain, "hand_l", w)).max())
        self.assertGreater(off(both), off(lag))
        self.assertGreater(off(both), off(whip))

    def test_balance_sees_the_overlap_with_no_whip(self):
        """Balance swings the arms before it carries the body - with an overlap set and Arm drag 0 the arms
        still move, so the pass must run inside its rounds too (its `swinging`)."""
        w = walk()
        calls = []
        real = wm.Walk._arm_overlap

        def counted(self, worlds, n, ctx, only=None):
            calls.append(1)
            return real(self, worlds, n, ctx, only)
        wm.Walk._arm_overlap = counted
        try:
            w.evaluate({"arm_drag": 0.0, "balance": 1.0, "arm_overlap": 3.0})
        finally:
            wm.Walk._arm_overlap = real
        self.assertGreater(len(calls), 1, "the pass runs inside Balance's rounds and on the final frames")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_walk_arm_overlap.OverlapPassTests -v`

Expected: FAIL - `KeyError: 'overlap'` and `AttributeError: 'Walk' object has no attribute '_arm_overlap'`.

- [ ] **Step 3: Add the pass**

In `SkeldarAnim/maya_walk/model.py`, immediately after `_arm_to_hand`, add:

```python
    def _arm_overlap(self, worlds, n, ctx, only=None):
        """The arms late by Arm overlap (frames of the new cycle; in place on `worlds`, (J, n+1, 4, 4)): each
        hand's world motion - the linear travel taken out - read that many frames earlier, and the arm rebuilt
        to it by IK from the current shoulder. So everything the arm takes from the body (the chest's turn, the
        shoulder's bob and sway) is late together with its own swing: the animator's hand trick, the IK arms'
        keys shifted. Under a pose's grip the held thing is what goes late (both sides' mean lag) and the two
        hands keep their hold on it. Runs before _arm_dynamics, so Whip takes the late arm as its target.
        Returns what it did (info["arms"]["overlap"])."""
        ks = ctx.get("ks") or {"l": ctx["k"], "r": ctx["k"]}
        chains = self._arm_chains()
        lags = dict((side, float(ks[side]["arm_overlap"])) for side in chains)
        pose = ctx["pose"]
        grip = bool(pose and pose.get("grip") and ctx["alpha"] > 0.0 and len(chains) == 2)
        if grip:                      # hands holding one thing move as one: the two sides' mean
            mean = sum(lags.values()) / float(len(lags))
            lags = dict((side, mean) for side in lags)
        out = {"frames": max([abs(v) for v in lags.values()] or [0.0]), "grip": grip}
        if not chains or out["frames"] < OVERLAP_QUIET:
            out["frames"] = 0.0
            return out
        kin = worlds.copy()
        hands = {}
        if grip:
            hold = chains["r"][-1]
            late = shifted_cycle(kin[hold], lags["r"])
            for side, chain in chains.items():
                hand_j = chain[-1]
                hands[side] = np.array([kin[hand_j, f] @ np.linalg.inv(kin[hold, f]) @ late[f]
                                        for f in range(n + 1)])
        else:
            for side, chain in chains.items():
                if abs(lags[side]) >= OVERLAP_QUIET:
                    hands[side] = shifted_cycle(kin[chain[-1]], lags[side])
        self._reattach(worlds, kin, self._arm_to_hand(kin, n, chains, hands), only)
        return out
```

- [ ] **Step 4: Wire it into `evaluate`**

In `evaluate`, find:

```python
        body = self._body_dynamics(worlds, n, ctx)
        arms = self._arm_dynamics(worlds, n, ctx)
```

and make it:

```python
        body = self._body_dynamics(worlds, n, ctx)
        overlap = self._arm_overlap(worlds, n, ctx)
        arms = self._arm_dynamics(worlds, n, ctx)
        arms["overlap"] = overlap
```

- [ ] **Step 5: Wire it into Balance**

In `evaluate`'s Balance block, find the `swinging` line:

```python
            swinging = (any(ks[s]["arm_drag"] > 0.0 for s in SIDES) and bool(self._arm_chains())) or self._bodies_on(k)
```

and make it:

```python
            moved_arms = any(ks[s]["arm_drag"] > 0.0 or abs(ks[s]["arm_overlap"]) >= OVERLAP_QUIET
                             for s in SIDES)
            swinging = (moved_arms and bool(self._arm_chains())) or self._bodies_on(k)
```

In the same block, inside `armed()`, find:

```python
                self._body_dynamics(frames, n, ctx, only)
                self._arm_dynamics(frames, n, ctx, only)
```

and make it:

```python
                self._body_dynamics(frames, n, ctx, only)
                self._arm_overlap(frames, n, ctx, only)
                self._arm_dynamics(frames, n, ctx, only)
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_walk_arm_overlap -v`

Expected: PASS, 19 tests.

- [ ] **Step 7: Run the model's suite**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_walkmodel -v`

Expected: PASS, every test. (The defaults are unchanged, so every identity test must still hold.)

- [ ] **Step 8: Commit**

```bash
git add SkeldarAnim/maya_walk/model.py tests/test_walk_arm_overlap.py
git commit -m "feat(walk): the arms late by a time shift, before the springs"
```

---

### Task 4: the `Arm overlap` parameter and the output frame rate

**Files:**
- Modify: `SkeldarAnim/maya_walk/gait.py` (`PARAMS` after the `arm_lag` entry around line 128;
  `engine_knobs`'s signature around line 698 and its per-side block around line 793)
- Modify: `SkeldarAnim/maya_walk/scene.py` (`params_knobs` around line 1182)
- Test: `tests/test_walk_arm_overlap.py` (append a class)

**Interfaces:**
- Consumes: the engine knob `arm_overlap` (Task 1).
- Produces: `gait.P["arm_overlap"]` (a `Param`); `gait.engine_knobs(walk, own_values, asked, pins=(),
  physics=True, lift_scale=None, fps_out=None)` - the new last argument, frames a second the keys land at,
  `None` meaning `walk.fps`; `scene.output_fps()` -> float.

- [ ] **Step 1: Write the failing test**

In `tests/test_walk_arm_overlap.py`, extend the file's top import to

```python
from tests.test_walkmodel import load, positions, rot_y, walk, wm

gait = load("gait")
```

and append:

```python
class ParameterTests(unittest.TestCase):
    """Arm overlap as the animator's parameter: milliseconds in, frames of the new cycle out."""

    def setUp(self):
        self.w = walk()
        self.own = gait.own(self.w)

    def test_it_is_a_sided_main_parameter_in_ms(self):
        p = gait.P["arm_overlap"]
        self.assertEqual((p.group, p.label, p.unit, p.kind, p.sided), (gait.MAIN, "Arm overlap", "ms",
                                                                       "added", True))
        self.assertIn("arm_overlap", gait.keys())
        self.assertIn("arm_overlap_l", gait.keys())
        names = [q.name for q in gait.PARAMS if q.group == gait.MAIN]
        self.assertEqual(names[names.index("arm_lag") + 1], "arm_overlap")

    def test_nothing_was_deleted(self):
        for name in ("arm_lag", "elbow_lag", "hand_lag", "elbow", "arms_forward", "shoulders"):
            self.assertIn(name, gait.P, name)

    def test_its_own_is_zero_and_its_range_is_fixed(self):
        self.assertEqual(gait.own_value(self.own, "arm_overlap"), 0.0)
        self.assertEqual(gait.own_value(self.own, "arm_overlap_l"), 0.0)
        self.assertEqual(gait.ranges(self.own, self.w.leg_length, self.w)["arm_overlap"], (-100.0, 300.0))

    def test_an_offset_change_is_the_value_asked(self):
        vals = gait.values(self.own, {"arm_overlap": ("offset", 150.0)})
        self.assertAlmostEqual(vals["arm_overlap"], 150.0)
        self.assertAlmostEqual(vals["arm_overlap_l"], 150.0)
        self.assertAlmostEqual(vals["arm_overlap_r"], 150.0)
        self.assertEqual(gait.stored_change(gait.P["arm_overlap"], 0.0, 150.0), ("offset", 150.0))

    def test_ms_become_frames_at_the_output_rate(self):
        vals = gait.values(self.own, {"arm_overlap": ("offset", 150.0)})
        at30 = gait.engine_knobs(self.w, self.own, vals, fps_out=30.0)
        at24 = gait.engine_knobs(self.w, self.own, vals, fps_out=24.0)
        self.assertAlmostEqual(at30["arm_overlap_l"], 4.5, places=6)
        self.assertAlmostEqual(at30["arm_overlap_r"], 4.5, places=6)
        self.assertAlmostEqual(at24["arm_overlap_l"], 3.6, places=6)

    def test_with_no_rate_given_the_walks_own_is_used(self):
        vals = gait.values(self.own, {"arm_overlap": ("offset", 100.0)})
        e = gait.engine_knobs(self.w, self.own, vals)
        self.assertAlmostEqual(e["arm_overlap_l"], 100.0 * self.w.fps / 1000.0, places=6)

    def test_one_side_alone(self):
        vals = gait.values(self.own, {"arm_overlap_l": ("offset", 90.0)})
        e = gait.engine_knobs(self.w, self.own, vals, fps_out=30.0)
        self.assertAlmostEqual(e["arm_overlap_l"], 2.7, places=6)
        self.assertAlmostEqual(e["arm_overlap_r"], 0.0, places=6)

    def test_zero_asks_the_engine_for_nothing(self):
        e = gait.engine_knobs(self.w, self.own, gait.values(self.own, {}), fps_out=30.0)
        self.assertAlmostEqual(e.get("arm_overlap_l", 0.0), 0.0)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_walk_arm_overlap.ParameterTests -v`

Expected: FAIL - `KeyError: 'arm_overlap'` from `gait.P`.

- [ ] **Step 3: Add the parameter**

In `SkeldarAnim/maya_walk/gait.py`, in `PARAMS`, immediately after the `arm_lag` entry, add:

```python
    Param("arm_overlap", MAIN, "Arm overlap", "ms", "added", sided=True, rule=_fixed(-100.0, 300.0),
          tip="The whole arm late by this many milliseconds - its own swing and everything it takes from the "
              "body (the chest's turn, the shoulder's bob); a hand holding a weapon takes the weapon with it"),
```

- [ ] **Step 4: Convert ms to frames in `engine_knobs`**

Change `engine_knobs`'s signature from

```python
def engine_knobs(walk, own_values, asked, pins=(), physics=True, lift_scale=None):
```

to

```python
def engine_knobs(walk, own_values, asked, pins=(), physics=True, lift_scale=None, fps_out=None):
```

and extend its docstring's last line with:

```
    `fps_out`: frames a second the new cycle's keys land at (the scene's rate), which Arm overlap's
    milliseconds are turned into frames with; None takes the walk's own fps.
```

Just before the `for s in SIDES:` per-side loop, add:

```python
    fps = float(fps_out or getattr(walk, "fps", 30.0) or 30.0)
```

and in the per-side block, right after the `e["arm_lag" + sfx] = sv("arm_lag") - so("arm_lag")` line, add:

```python
        e["arm_overlap" + sfx] = sv("arm_overlap") * fps / 1000.0      # ms -> frames of the new cycle (own 0)
```

- [ ] **Step 5: Pass the scene's rate from `params_knobs`**

In `SkeldarAnim/maya_walk/scene.py`, add above `params_knobs`:

```python
def output_fps():
    """Frames a second the keyed cycle lands at: the scene's own time unit (what Arm overlap's milliseconds
    are counted in), 30 where there is no Maya to ask."""
    try:
        return wcards.fps_of(_cmds().currentUnit(q=True, time=True))
    except Exception:
        return 30.0
```

and in `params_knobs` change

```python
    knobs = gait.engine_knobs(walk, own, vals, pins=params["pins"], physics=params["physics"])
```

to

```python
    knobs = gait.engine_knobs(walk, own, vals, pins=params["pins"], physics=params["physics"],
                              fps_out=output_fps())
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_walk_arm_overlap -v`

Expected: PASS, 27 tests.

- [ ] **Step 7: Run the walk suite and the card's tests**

Run:
```
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_walkmodel tests.test_walkgait tests.test_walk_scene_params tests.test_walk_panel -v
```

Expected: PASS. The panel builds its sliders from `gait.PARAMS` (`MAIN_PARAMS = _names(gait.MAIN)`), so the
new slider appears with no panel change; if a panel test pins the Main group's exact list, update that list
to include `arm_overlap` after `arm_lag` and say so in the commit.

- [ ] **Step 8: Commit**

```bash
git add SkeldarAnim/maya_walk/gait.py SkeldarAnim/maya_walk/scene.py tests/test_walk_arm_overlap.py
git commit -m "feat(walk): Arm overlap in ms, converted at the scene's frame rate"
```

---

### Task 5: the verify on the animator's own cycle

**Files:**
- Create: `docs/superpowers/plans/walkparam/verify_walk_arm_overlap.py`

**Interfaces:**
- Consumes: everything above, through `maya_walk.scene`.
- Produces: nothing other code uses.

- [ ] **Step 1: Write the verify**

Create `docs/superpowers/plans/walkparam/verify_walk_arm_overlap.py`:

```python
"""verify_walk_arm_overlap.py - the arms' overlap, in mayapy standalone (never the animator's scene).

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_arm_overlap.py

On a COPY of the animator's walks folder, with their own walker's settings (2026-10-29: their captured cycle,
the Pose Library card LongSword_Idle_3P at share 1 - a two-handed grip - In place, physics on, tempo pinned),
and the same cycle with DG_Idle (no grip) and with no pose at all: the hand's path is the lag-0 path read that
many frames earlier in the body's space, the shoulder has not moved, the grip is held, the bones keep their
lengths, the cycle is still a loop, 0 ms changes nothing, the milliseconds are counted at the scene's rate,
a lead goes the other way, Whip stacks on top, and Balance sees it.
"""
import os
import shutil
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
MINE = os.environ.get("WALKS_HOME", "C:/Users/MY PC/Documents/maya/SkeldarWalks")
LIBRARY = os.environ.get("POSE_LIBRARY", "C:/Users/MY PC/Documents/maya/scripts/SkeldarAnim/poses")
WALK = os.environ.get("ARM_WALK", "own:7833074715b34c33")
SWORD = os.environ.get("ARM_SWORD_CARD", "LongSword_Idle_3P.pose")
DAGGER = os.environ.get("ARM_DAGGER_CARD", "DG_Idle.pose")
BASE = {"changes": {"tempo": ["ratio", 0.8709677419354839]}, "pins": ["tempo"], "in_place": 1.0,
        "physics": True}

import maya.standalone                                       # noqa: E402
maya.standalone.initialize()
import maya.cmds as cmds                                     # noqa: E402

sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))         # the repository's plugin, never the installed copy
from maya_walk import scene as sw                             # noqa: E402
from maya_walk import cards as wcards                         # noqa: E402
from maya_walk import pose as wp                               # noqa: E402

wm, wt, gait = sw.wm, sw.wt, sw.gait
FAILED, COUNT = [], [0]


def gate(ok, text):
    COUNT[0] += 1
    print("gate %2d %s  %s" % (COUNT[0], "ok  " if ok else "FAIL", text))
    sys.stdout.flush()
    if not ok:
        FAILED.append(COUNT[0])


TEMP = tempfile.mkdtemp(prefix="arm_overlap_")
COPY = os.path.join(TEMP, "SkeldarWalks")
shutil.copytree(MINE, COPY)
sw.WALKS = COPY


def setup(share, card):
    """(walk, the base knobs, the prepared pose or None) of the animator's cycle under a pose card."""
    params = sw.normal_params(dict(BASE, pose=share))
    walk, statics = sw.load_walk(WALK, params["clean"])[:2]
    pose = None
    if share > 0.0 and card:
        bones = wcards.read_card(os.path.join(LIBRARY, card))[1]
        pose = wp.filtered(wp.prepare(walk, statics, bones, wm, wt), sw.ALL_PARTS)
    knobs = sw.params_knobs(walk, params)[0]
    return walk, knobs, pose


def run(walk, knobs, pose, **over):
    ks = dict(knobs)
    ks.update(over)
    return walk.evaluate(ks, pose)


def place(walk, result, leaf, f):
    """A joint's place in the body's own space at frame f."""
    m = result.worlds[walk.index["root"], f]
    return (result.worlds[walk.index[leaf], f, 3, :3] - m[3, :3]) @ m[:3, :3].T


def lengths(walk, result, side):
    out = []
    for a, b in (("upperarm_", "lowerarm_"), ("lowerarm_", "hand_")):
        pa = result.worlds[walk.index[a + side]][:, 3, :3]
        pb = result.worlds[walk.index[b + side]][:, 3, :3]
        out.append(np.linalg.norm(pb - pa, axis=1))
    return out


for label, share, card in (("the sword at 1.0 (a grip)", 1.0, SWORD),
                           ("the dagger at 1.0 (no grip)", 1.0, DAGGER),
                           ("no pose", 0.0, None)):
    print()
    print("=" * 78)
    print(label)
    print("=" * 78)
    walk, knobs, pose = setup(share, card)
    plain = run(walk, knobs, pose, arm_drag=0.0)
    n = plain.frames
    lag_fr = 4.0
    late = run(walk, knobs, pose, arm_drag=0.0, arm_overlap=lag_fr)
    gate(late.info["arms"]["overlap"]["frames"] == lag_fr,
         "%s: the pass reports %g frames (grip %s)" % (label, lag_fr, late.info["arms"]["overlap"]["grip"]))
    gate(late.info["arms"]["overlap"]["grip"] == (share > 0.0 and card == SWORD),
         "%s: the grip branch is %s, as the pose is" % (label, late.info["arms"]["overlap"]["grip"]))

    worst, moved = 0.0, 0.0
    for side in ("l", "r"):
        for f in range(n):
            was = place(walk, plain, "hand_" + side, int((f - lag_fr) % n))
            now = place(walk, late, "hand_" + side, f)
            worst = max(worst, float(np.linalg.norm(now - was)))
            moved = max(moved, float(np.linalg.norm(place(walk, late, "hand_" + side, f)
                                                    - place(walk, plain, "hand_" + side, f))))
    gate(worst < 1.0, "%s: the hand is the lag-0 hand %g frames earlier, worst %.4f cm" % (label, lag_fr, worst))
    gate(moved > 1.0, "%s: and it really moved, worst %.2f cm" % (label, moved))

    shoulder = max(float(np.abs(late.worlds[walk.index["upperarm_" + s]][:, 3, :3]
                                - plain.worlds[walk.index["upperarm_" + s]][:, 3, :3]).max())
                   for s in ("l", "r"))
    gate(shoulder < 1e-9, "%s: the shoulder has not moved (%.2e cm)" % (label, shoulder))

    bones = max(float(np.abs(a - b).max()) for s in ("l", "r")
                for a, b in zip(lengths(walk, late, s), lengths(walk, plain, s)))
    gate(bones < 1e-6, "%s: the bones keep their lengths (%.2e cm)" % (label, bones))

    loop_r = float(np.abs(late.worlds[:, -1, :3, :3] - late.worlds[:, 0, :3, :3]).max())
    travel = plain.worlds[:, -1, 3, :3] - plain.worlds[:, 0, 3, :3]
    loop_x = float(np.abs((late.worlds[:, -1, 3, :3] - late.worlds[:, 0, 3, :3]) - travel).max())
    gate(loop_r < 1e-9 and loop_x < 1e-6, "%s: still a loop (%.2e, %.2e)" % (label, loop_r, loop_x))

    zero = run(walk, knobs, pose, arm_drag=0.0, arm_overlap=0.0)
    gate(np.array_equal(zero.worlds, plain.worlds), "%s: 0 ms changes nothing, matrix for matrix" % label)

    if share > 0.0 and card == SWORD:
        hold_l, hold_r = walk.index["hand_l"], walk.index["hand_r"]
        held = max(float(np.abs(late.worlds[hold_l, f] @ np.linalg.inv(late.worlds[hold_r, f])
                                - plain.worlds[hold_l, f] @ np.linalg.inv(plain.worlds[hold_r, f])).max())
                   for f in range(n + 1))
        gate(held < 1e-6, "%s: the grip is held - the left hand in the right's is unchanged (%.2e)"
             % (label, held))

    lead = run(walk, knobs, pose, arm_drag=0.0, arm_overlap=-lag_fr)
    back = float(np.abs(late.worlds[walk.index["hand_l"]][:, 3, :3]
                        - plain.worlds[walk.index["hand_l"]][:, 3, :3]).max())
    ahead = float(np.abs(lead.worlds[walk.index["hand_l"]][:, 3, :3]
                         - plain.worlds[walk.index["hand_l"]][:, 3, :3]).max())
    gate(abs(back - ahead) < 0.5 * back, "%s: a lead goes as far the other way (%.2f against %.2f cm)"
         % (label, ahead, back))

    whip = run(walk, knobs, pose, arm_drag=2.0, arm_bounce=0.0)
    both = run(walk, knobs, pose, arm_drag=2.0, arm_bounce=0.0, arm_overlap=lag_fr)
    off = lambda r: float(np.abs(r.worlds[walk.index["hand_l"]][:, 3, :3]
                                 - plain.worlds[walk.index["hand_l"]][:, 3, :3]).max())
    gate(off(both) > off(whip) and off(both) > off(late),
         "%s: Whip stacks on the lag (%.2f > %.2f, %.2f cm)" % (label, off(both), off(whip), off(late)))

#  the milliseconds, counted at the scene's own rate
print()
print("=" * 78)
print("milliseconds at the scene's rate")
print("=" * 78)
walk, _, pose = setup(1.0, SWORD)
own = gait.own(walk)
vals = gait.values(own, {"arm_overlap": ("offset", 150.0)})
at30 = gait.engine_knobs(walk, own, vals, fps_out=30.0)["arm_overlap_l"]
at24 = gait.engine_knobs(walk, own, vals, fps_out=24.0)["arm_overlap_l"]
gate(abs(at30 - 4.5) < 1e-6 and abs(at24 - 3.6) < 1e-6,
     "150 ms is %.3f frames at 30 fps and %.3f at 24" % (at30, at24))
for unit, want in (("ntsc", 30.0), ("film", 24.0)):
    cmds.currentUnit(time=unit)
    gate(abs(sw.output_fps() - want) < 1e-6, "the scene at %s reads %g fps" % (unit, sw.output_fps()))
cmds.currentUnit(time="ntsc")
params = sw.normal_params(dict(BASE, pose=1.0, changes=dict(BASE["changes"],
                                                            arm_overlap=["offset", 150.0]),
                               pins=BASE["pins"] + ["arm_overlap"]))
knobs = sw.params_knobs(walk, params)[0]
gate(abs(knobs["arm_overlap_l"] - 4.5) < 1e-6,
     "the card's 150 ms reach the engine as %.3f frames" % knobs["arm_overlap_l"])

#  Balance sees the late arms
print()
print("=" * 78)
print("Balance")
print("=" * 78)
walk, knobs, pose = setup(1.0, SWORD)
flat = run(walk, knobs, pose, arm_drag=0.0, balance=1.0, arm_overlap=0.0)
bent = run(walk, knobs, pose, arm_drag=0.0, balance=1.0, arm_overlap=6.0)
carry = abs(float(flat.info["balance"]["carry"]) - float(bent.info["balance"]["carry"]))
gate(carry > 1e-4, "the carry differs with the arms late (%.4f cm)" % carry)

shutil.rmtree(TEMP, ignore_errors=True)
print()
print("%d of %d gates failed%s" % (len(FAILED), COUNT[0], (": " + ", ".join(map(str, FAILED))) if FAILED else ""))
sys.exit(1 if FAILED else 0)
```

- [ ] **Step 2: Run it**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_arm_overlap.py`

Expected: `0 of N gates failed`. If a gate fails, read its number and its printed numbers, fix the cause in
the code (never the gate's threshold, unless the threshold itself is measured wrong - then say so in the
commit), and run it again.

- [ ] **Step 3: Run the neighbouring verifies - nothing of the walk may have moved**

Run, one at a time:
```
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/walkparam/verify_walk.py
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_gait.py
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_own.py
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_many.py
```

Expected: each the same result it gives on `origin/main` before this work. Some of these are known stale
against the 2026-10-26 parameters (`verify_walk_own.py` gates 10 and 19, `verify_walk_many.py` gates 5, 6
and 8-11): run them on a clean checkout first if any fail, and only call a failure ours when it does not
fail there too.

- [ ] **Step 4: Run the whole unit suite**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v`

Expected: PASS but for the known `tests.test_chat_deploy.Keys` failure (it reads this machine's own saved
Cloudflare keys).

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/plans/walkparam/verify_walk_arm_overlap.py
git commit -m "test(walk): the overlap's verify on the animator's own cycle and pose"
```

---

### Task 6: a playblast, and the notes

**Files:**
- Modify: `CLAUDE.md` (a paragraph at the end of the Walk Builder sections, before
  "## Camera Shake: handheld filming and an impact")
- Modify: `docs/superpowers/specs/2026-10-29-walk-arm-overlap-design.md` (the measured numbers under Proof)

**Interfaces:**
- Consumes: the verify's printed numbers (Task 5).
- Produces: nothing other code uses.

- [ ] **Step 1: Take the picture**

In a disposable GUI Maya (a scratch `MAYA_APP_DIR`, `MAYA_NO_HOME=1`, started minimized and killed
afterwards - never the animator's Maya on port 7004), add a Manny UE5 skeleton, Pick the animator's cycle
with the sword card, and playblast it at `arm_overlap` 0 and at 150 ms. Save the two blasts beside the
verify as `docs/superpowers/plans/walkparam/walk_arm_overlap.png` (the two side by side, one frame each
where the hand moves fastest).

If no GUI Maya can be started (it has failed on this machine before - CLAUDE.md's trap 133), say so and
leave the picture to the animator; do not block the task on it.

- [ ] **Step 2: Write the CLAUDE.md paragraph**

Add, in the Walk Builder run of sections, a paragraph in the house voice: the animator's ask quoted, what was
measured (today's Arm lag moves the hand 0.00 cm under a grip at full share because the grip takes the arm's
own swing to zero, while the body carries that hand 15.12 cm a cycle with no delay), what was built (one
knob `Arm overlap` in ms, sided, MAIN, nothing deleted; the pass before the springs; the IK rebuild shared
with `_grip_motion`), the numbers the verify printed, and the limits (the bones keep their lengths so a lag
past the arm's reach is clamped; a held weapon goes with the hands; `Arm lag` unchanged beside it).

- [ ] **Step 3: Put the verify's real numbers in the spec**

In `docs/superpowers/specs/2026-10-29-walk-arm-overlap-design.md`, under `## Proof`, replace the planned
gate list's bullet points with the gate counts and the measured numbers the run printed (the house habit:
a spec says what was measured, not what will be).

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md docs/superpowers/specs/2026-10-29-walk-arm-overlap-design.md docs/superpowers/plans/walkparam/walk_arm_overlap.png
git commit -m "docs(walk): the arms' overlap, measured"
```

---

## Self-Review

**Spec coverage.** Every section of `2026-10-29-walk-arm-overlap-design.md` has a task:

| spec | task |
|---|---|
| the knob (name, group, unit, kind, sided, range, own 0, ms -> frames at the output rate) | 4 |
| `rule=_fixed(-100.0, 300.0)`; `own` / `of_result` answer 0 | 4 (the kind `added` is what makes `measure` skip it) |
| the pass's steps 1-6, the grip branch, the travel out and back, the fractional lag | 1 (the shift) + 3 (the pass) |
| the IK rebuild factored out of `_grip_motion` | 2 |
| it runs before `_arm_dynamics`, and inside Balance's `armed()` | 3 |
| nothing deleted | the Global Constraints, and Task 4's `test_nothing_was_deleted` |
| the limits (the reach clamp, a held weapon, the travel, `Arm lag` unchanged) | 2 (the clamp test), 5 (the grip gate), 1 (the loop test), 4 (the deletion test) |
| the proof's gates | 5 |
| the playblast | 6 |
| "Not built" | nothing to do |

**Placeholder scan.** No TBD / TODO; every code step carries the code; every test step carries the test.
Task 6 step 2 describes a prose paragraph rather than quoting it - that is deliberate, because it must carry
the numbers the run prints, and the step says exactly which numbers.

**Type consistency.** `shifted_cycle(mats, lag)` (Task 1) is called in Task 3 as
`shifted_cycle(kin[hold], lags["r"])` and `shifted_cycle(kin[chain[-1]], lags[side])` - a `(n+1, 4, 4)`
array and a float, matching. `_arm_to_hand(self, kin, n, chains, hands)` (Task 2) is called in Task 3 as
`self._arm_to_hand(kin, n, chains, hands)` and in `_grip_motion` as `self._arm_to_hand(kin, n, chains,
hands)` - matching. `_arm_overlap(self, worlds, n, ctx, only=None)` (Task 3) is called as
`self._arm_overlap(worlds, n, ctx)` in `evaluate` and `self._arm_overlap(frames, n, ctx, only)` in
`armed()` - matching, and the test's `counted(self, worlds, n, ctx, only=None)` has the same shape.
`engine_knobs(..., fps_out=None)` (Task 4) is called with `fps_out=output_fps()` in `scene.params_knobs`
and `fps_out=30.0` / `fps_out=24.0` in the tests and the verify - matching. `OVERLAP_QUIET` is defined in
Task 1 and used in Task 3. The knob name `arm_overlap` and the parameter name `arm_overlap` are the same
string everywhere.
