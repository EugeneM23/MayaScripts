# Walk Builder: the arms' and the hands' share of the cycle - implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Two sided Walk Builder parameters, `Arms, %` and `Hands, %`, each 100 % by default, saying how much of the cycle's own animation that part of the arm keeps - so a dagger pose can be stilled the way a sword pose's grip stills itself.

**Architecture:** One new engine knob (`hands`) multiplying the hand bone's and every finger's gain in the frame walk, beside the `arms` knob that already multiplies the arm chain; two `"added"` parameters in `gait.PARAMS` mapped onto those two engine knobs by a division by 100; one clause in `describe`. The panel builds its sliders from `gait.PARAMS` by group, so it needs no change.

**Tech Stack:** Python 3 in Maya 2027's mayapy, numpy, stdlib `unittest`.

## Global Constraints

- The spec: `docs/superpowers/specs/2026-11-04-walk-hands-from-the-cycle-design.md`. Read it before Task 1.
- **The defaults change nothing.** Both parameters default to 100 % and both engine knobs to 1.0; at those values every result must be identical **matrix for matrix** (`np.array_equal`), not merely close.
- The new engine knob goes in `KNOBS` **after `("exaggeration", 1.0, 0.0, 2.0)`** (line 60): everything up to and including `exaggeration` is `LEGACY`, read from a pre-2026-10-26 memo.
- **Row vectors.** A joint's own local rotation is `w[j] @ w[parent].T`, never `w[parent].T @ w[j]` (trap 225). Written the other way round a constant local on a moving parent reads as 8-20 deg of motion.
- `from_legacy` is **not** changed: a pre-2026-10-26 memo's engine `arms` still becomes an `arm_swing` ratio.
- `Arm swing` is **not** changed: it is a different quantity (the harmonic swing in degrees) and it is not broken.
- No new name may enter `model.ASPECT_KNOBS`.
- Test runner (there is no system Python; `python` is the Store stub and HANGS):
  `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v`
- Commit messages end with `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`. Write them to a file and use `git commit -F` (a here-string with double quotes breaks in PowerShell 5.1).

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `SkeldarAnim/maya_walk/model.py` | the engine: the knob table, the joint sets, the frame walk, `describe` | modify |
| `SkeldarAnim/maya_walk/gait.py` | the parameters and their mapping onto engine knobs | modify |
| `tests/test_walk_hands.py` | the unit tests for both knobs, both parameters and the line | create |
| `docs/superpowers/plans/walkparam/verify_walk_hands.py` | the proof on the animator's own cycle and cards | create |

---

### Task 1: the engine's `hands` knob

**Files:**
- Modify: `SkeldarAnim/maya_walk/model.py:60` (the `KNOBS` table), `:195-200` (`SIDED`), `:1396` (the joint sets), `:3930` (the frame walk's gain)
- Test: `tests/test_walk_hands.py` (create)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: the engine knob `"hands"` (sided, default 1.0, range 0.0-3.0) and `Walk.hand_bones` (a `set` of joint indices whose `_stem(name) == "hand"`). Task 2 writes `e["hands" + sfx]`; Task 3 reads `info["knobs"].get("hands_" + side, ...)`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_walk_hands.py`:

```python
"""Walk Builder's Arms % and Hands %: each part's share of the cycle's own animation (2026-11-04).

The spec: docs/superpowers/specs/2026-11-04-walk-hands-from-the-cycle-design.md. The synthetic walker is
tests.test_walkmodel's: its upper arm turns 25.000 deg on its own, its forearm 8.000, its hand 5.000 and
its one finger 5.000, so every gate below can fail.
"""

import math
import unittest

import numpy as np

from tests import test_walkmodel as T

wm = T.wm
gait = T.load("gait")


def own_turn(result, walk, name):
    """A joint's own local rotation over the cycle (deg, the most it stands off its mean).

    Row vectors: the local is w[j] @ w[parent].T, never the other way round (trap 225) - written
    backwards a constant local on a moving parent reads as degrees of motion that are not there."""
    j = walk.index[name]
    p = walk.parents[j]
    R = result.worlds[:, :, :3, :3]
    rots = [wm.orthonormal(R[j, f]) @ wm.orthonormal(R[p, f]).T
            for f in range(result.worlds.shape[1])]
    mean = wm.orthonormal(np.mean(rots, axis=0))
    return max(math.degrees(float(np.linalg.norm(wm.log_rot(mean.T @ r)))) for r in rots)


def run(walk, **over):
    """The walker's own cycle with `over` on top, travelling (In place off, so nothing hides a turn)."""
    return walk.evaluate(dict(walk.own_knobs(), in_place=0.0, **over), None)


class KnobTests(unittest.TestCase):
    """The engine knob itself."""

    def test_the_hands_knob_is_declared_sided_at_one(self):
        self.assertEqual(wm.DEFAULTS["hands"], 1.0)
        self.assertEqual(wm.RANGES["hands"], (0.0, 3.0))
        self.assertIn("hands", wm.SIDED)
        self.assertEqual(wm.SIDE_KNOBS["hands_l"], "hands")
        self.assertEqual(wm.SIDE_KNOBS["hands_r"], "hands")

    def test_it_is_not_a_legacy_knob_and_not_an_aspect(self):
        self.assertNotIn("hands", wm.LEGACY)
        self.assertNotIn("hands", wm.ASPECT_KNOBS)

    def test_the_hand_bones_are_found(self):
        walk = T.walk()
        self.assertEqual(sorted(walk.names[j] for j in walk.hand_bones), ["hand_l", "hand_r"])

    def test_its_own_value_changes_nothing_matrix_for_matrix(self):
        walk = T.walk()
        plain = run(walk)
        same = run(walk, hands=1.0, hands_l=1.0, hands_r=1.0)
        self.assertTrue(np.array_equal(plain.worlds, same.worlds))


class HandsTests(unittest.TestCase):
    """Hands %: the hand bone and every finger, per side."""

    def setUp(self):
        self.walk = T.walk()
        self.plain = run(self.walk)

    def test_the_walker_s_hand_and_finger_move_at_all(self):
        self.assertAlmostEqual(own_turn(self.plain, self.walk, "hand_l"), 5.0, delta=0.5)
        self.assertAlmostEqual(own_turn(self.plain, self.walk, "index_01_l"), 5.0, delta=0.5)

    def test_zero_stills_the_hand_and_its_finger(self):
        res = run(self.walk, hands=0.0, hands_l=0.0, hands_r=0.0)
        for name in ("hand_l", "index_01_l", "hand_r", "index_01_r"):
            self.assertLess(own_turn(res, self.walk, name), 1e-6, msg=name)

    def test_one_side_alone_leaves_the_other_untouched(self):
        res = run(self.walk, hands_l=0.0)
        self.assertLess(own_turn(res, self.walk, "hand_l"), 1e-6)
        self.assertLess(own_turn(res, self.walk, "index_01_l"), 1e-6)
        self.assertAlmostEqual(own_turn(res, self.walk, "hand_r"),
                               own_turn(self.plain, self.walk, "hand_r"), places=6)
        self.assertAlmostEqual(own_turn(res, self.walk, "index_01_r"),
                               own_turn(self.plain, self.walk, "index_01_r"), places=6)

    def test_half_keeps_half_of_the_finger_s_turn(self):
        res = run(self.walk, hands=0.5, hands_l=0.5, hands_r=0.5)
        self.assertAlmostEqual(own_turn(res, self.walk, "index_01_l"),
                               0.5 * own_turn(self.plain, self.walk, "index_01_l"), delta=0.05)

    def test_it_leaves_the_upper_arm_and_the_forearm_alone(self):
        res = run(self.walk, hands=0.0, hands_l=0.0, hands_r=0.0)
        for name in ("upperarm_l", "lowerarm_l", "upperarm_r", "lowerarm_r"):
            self.assertAlmostEqual(own_turn(res, self.walk, name),
                                   own_turn(self.plain, self.walk, name), places=6, msg=name)


class ArmsTests(unittest.TestCase):
    """Arms %: the knob that was already there, and what it reaches."""

    def setUp(self):
        self.walk = T.walk()
        self.plain = run(self.walk)

    def test_zero_stills_the_upper_arm_and_the_forearm(self):
        res = run(self.walk, arms=0.0, arms_l=0.0, arms_r=0.0)
        for name in ("upperarm_l", "lowerarm_l", "upperarm_r", "lowerarm_r"):
            self.assertLess(own_turn(res, self.walk, name), 1e-6, msg=name)

    def test_it_reaches_the_hand_bone_but_not_the_fingers(self):
        res = run(self.walk, arms=0.0, arms_l=0.0, arms_r=0.0)
        self.assertLess(own_turn(res, self.walk, "hand_l"), 1e-6)
        self.assertAlmostEqual(own_turn(res, self.walk, "index_01_l"),
                               own_turn(self.plain, self.walk, "index_01_l"), places=6)

    def test_one_side_alone_leaves_the_other_untouched(self):
        res = run(self.walk, arms_l=0.0)
        self.assertLess(own_turn(res, self.walk, "upperarm_l"), 1e-6)
        self.assertAlmostEqual(own_turn(res, self.walk, "upperarm_r"),
                               own_turn(self.plain, self.walk, "upperarm_r"), places=6)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_walk_hands -v`

Expected: `KnobTests` fail with `KeyError: 'hands'` / `AssertionError: 'hands' not found in (...)` and `AttributeError: 'Walk' object has no attribute 'hand_bones'`; `HandsTests` fail with `ValueError: unknown knob(s): hands, hands_l, hands_r`. `ArmsTests` should already PASS - `arms` exists today; if one of them fails, stop and say so before touching anything.

- [ ] **Step 3: Declare the knob**

In `SkeldarAnim/maya_walk/model.py`, after line 60 (`("exaggeration", 1.0, 0.0, 2.0),`) and before the `# Operators` comment, add:

```python
    #  Arms % and Hands % (2026-11-04): how much of the cycle's own animation a part of the arm keeps -
    #  the lever a pose's grip pulls (gain *= 1 - alpha), as a knob. `arms` is above; `hands` is the hand
    #  bone and its fingers, which carried a hard 1.0 under every knob there was
    ("hands", 1.0, 0.0, 3.0),
```

In `SIDED` (line 195-200), add `"hands"` to the arm run - change

```python
         "arms", "elbow", "arm_drag", "arm_bounce", "arm_fwd_add", "arm_out_add", "elbow_add",
```

to

```python
         "arms", "hands", "elbow", "arm_drag", "arm_bounce", "arm_fwd_add", "arm_out_add", "elbow_add",
```

- [ ] **Step 4: Find the hand bones**

In `_kinds`, after line 1396 (`self.forearms = set(...)`), add:

```python
        self.hand_bones = set(j for j, n in enumerate(self.names) if _stem(n) == "hand")
```

- [ ] **Step 5: Apply the factor in the frame walk**

In the frame walk, before line 3930 (`if j in self.forearms:`), insert:

```python
                    if j in self.hand_bones or kind == "finger":
                        gain *= ks[self._side(j)]["hands"]
```

so the block reads:

```python
                    if j in self.hand_bones or kind == "finger":
                        gain *= ks[self._side(j)]["hands"]
                    if j in self.forearms:
                        gain *= ks[self._side(j)]["elbow"]
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_walk_hands -v`

Expected: PASS, every test.

- [ ] **Step 7: Run the model's own suite for regressions**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_walkmodel tests.test_walkgait tests.test_walk_one_arm tests.test_walk_arm_overlap tests.test_walk_weapon_chest -v`

Expected: PASS. The `ParityTests` of `tests/test_gait_model.py` hold the Gait Builder fork frame for frame against this model, so run them too:
`& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_gait_model -v` - expected PASS (the fork has no `hands` knob and the default is 1.0, so nothing of it moves).

- [ ] **Step 8: Commit**

Write the message to a file (a PowerShell here-string with double quotes breaks `git commit -m`), then commit:

```bash
printf 'feat(walk): the engine hands knob - the hand bone and its fingers\n\nA finger carried a hard 1.0 under every knob there was: gains.get("finger", 1.0),\nso no arms, no elbow, not even exaggeration reached it - only a pose grip and the\nglobal Detail. The hand bone was under arms alone.\n\nThe new sided knob multiplies both, 1.0 by default, so every cycle is what it was\nbit for bit.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n' > "$TMP/msg1.txt"
git add SkeldarAnim/maya_walk/model.py tests/test_walk_hands.py
git commit -F "$TMP/msg1.txt"
```

(`$TMP` is this session's scratchpad folder; any path outside the repository will do.)

---

### Task 2: the two parameters

**Files:**
- Modify: `SkeldarAnim/maya_walk/gait.py:209` (`PARAMS`, the arms block), `:887` (`engine_knobs`' sided loop)
- Test: `tests/test_walk_hands.py` (add a class)

**Interfaces:**
- Consumes: the engine knobs `arms` and `hands`, both sided, both 1.0 by default (Task 1).
- Produces: the parameters `"arms"` and `"hands"` in `gait.PARAMS`, group `gait.ARMS`, unit `"%"`, kind `"added"`, `sided=True`, `default=100.0`. Task 3 reads neither; the panel reads them through `gait.PARAMS`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_walk_hands.py`:

```python
class ParamTests(unittest.TestCase):
    """The card's two parameters and their mapping onto the engine."""

    def setUp(self):
        self.walk = T.walk()
        self.own = gait.own(self.walk)

    def param(self, name):
        return dict((p.name, p) for p in gait.PARAMS)[name]

    def test_both_are_a_percent_added_sided_at_a_hundred(self):
        for name, label in (("arms", "Arms"), ("hands", "Hands")):
            p = self.param(name)
            self.assertEqual(p.group, gait.ARMS, msg=name)
            self.assertEqual(p.label, label)
            self.assertEqual(p.unit, "%", msg=name)
            self.assertEqual(p.kind, "added", msg=name)
            self.assertTrue(p.sided, msg=name)
            self.assertEqual(p.default, 100.0, msg=name)
            self.assertEqual(p.rule(0.0, 80.0), (0.0, 100.0), msg=name)
            self.assertTrue(p.tip, msg=name)

    def test_they_come_first_in_the_arms_group(self):
        names = [p.name for p in gait.PARAMS if p.group == gait.ARMS]
        self.assertEqual(names[:2], ["arms", "hands"])

    def test_their_own_value_is_a_hundred(self):
        #  gait.own() carries no "added" parameter at all (detail, arm_drag and arm_overlap are all
        #  absent from it); own_value falls back to the Param's default, which is what engine_knobs
        #  reads. So ask own_value, never own[...] - that would KeyError.
        for name in ("arms", "hands"):
            self.assertEqual(gait.own_value(self.own, name), 100.0, msg=name)
            for side in ("l", "r"):
                self.assertEqual(gait.own_value(self.own, name + "_" + side), 100.0, msg=name + side)

    def test_a_legacy_memo_s_engine_arms_still_becomes_an_arm_swing_ratio(self):
        """from_legacy is deliberately unchanged: a pre-2026-10-26 memo's `arms` is an Arm swing ratio,
        not the new Arms % parameter (the spec's reason - every walker it concerns was translated in
        October, and changing it would move them)."""
        changes, pins, macros = gait.from_legacy(self.walk, {"arms": 0.5})   # it returns a 3-tuple
        self.assertEqual(changes.get("arm_swing"), ("ratio", 0.5))
        self.assertNotIn("arms", changes)
        self.assertIn("arm_swing", pins)

    def test_the_own_values_write_no_engine_knob(self):
        e = gait.engine_knobs(self.walk, self.own, self.own, pins=set(), physics=False)
        for key in ("arms", "arms_l", "arms_r", "hands", "hands_l", "hands_r"):
            self.assertNotIn(key, e, msg=key)

    def test_a_percent_becomes_a_share_on_both_sides(self):
        asked = dict(self.own, arms=25.0, arms_l=25.0, arms_r=25.0,
                     hands=0.0, hands_l=0.0, hands_r=0.0)
        e = gait.engine_knobs(self.walk, self.own, asked, pins={"arms", "hands"}, physics=False)
        self.assertAlmostEqual(e["arms_l"], 0.25, places=9)
        self.assertAlmostEqual(e["arms_r"], 0.25, places=9)
        self.assertAlmostEqual(e["hands_l"], 0.0, places=9)
        self.assertAlmostEqual(e["hands_r"], 0.0, places=9)

    def test_one_side_asked_leaves_the_other_at_its_own(self):
        asked = dict(self.own, hands_l=0.0)
        e = gait.engine_knobs(self.walk, self.own, asked, pins={"hands_l"}, physics=False)
        self.assertAlmostEqual(e["hands_l"], 0.0, places=9)
        self.assertNotIn("hands_r", e)

    def test_the_card_s_road_stills_the_fingers(self):
        """The whole way through: a percent asked of the parameter layer reaches the frame walk."""
        asked = dict(self.own, hands=0.0, hands_l=0.0, hands_r=0.0)
        e = gait.engine_knobs(self.walk, self.own, asked, pins={"hands"}, physics=False)
        res = self.walk.evaluate(dict(e, in_place=0.0), None)
        self.assertLess(own_turn(res, self.walk, "index_01_l"), 1e-6)
        self.assertLess(own_turn(res, self.walk, "index_01_r"), 1e-6)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_walk_hands.ParamTests -v`

Expected: FAIL with `KeyError: 'arms'` out of `self.param("arms")`.

- [ ] **Step 3: Declare the two parameters**

In `SkeldarAnim/maya_walk/gait.py`, in the `# the arms` block, immediately **before** line 209 (`Param("arms_forward", ...)`), insert:

```python
    #  2026-11-04: how much of the cycle's own animation each part of the arm keeps - the lever a pose's
    #  grip pulls, as two knobs. Both at 0 % is exactly what a grip does; the hands alone keep a quiet
    #  hand on a swinging arm. Arm swing is a different quantity (the harmonic swing in degrees)
    Param("arms", ARMS, "Arms", "%", "added", sided=True, rule=_fixed(0.0, 100.0), default=100.0,
          tip="How much of the cycle's own arm swing the upper arm and the forearm keep; 0 % holds them "
              "in the pose. A pose whose two hands hold one thing holds them on its own"),
    Param("hands", ARMS, "Hands", "%", "added", sided=True, rule=_fixed(0.0, 100.0), default=100.0,
          tip="How much of the cycle's own hand and finger animation the hands keep; 0 % holds them in "
              "the pose. Under 2H or a grip the hand itself rides the weapon, so this is its fingers"),
```

- [ ] **Step 4: Map them onto the engine**

In `engine_knobs`' sided loop, after line 887 (`e["arm_lag" + sfx] = sv("arm_lag") - so("arm_lag")`), insert:

```python
        if abs(sv("arms") - 100.0) > 1e-9:          # % -> the engine's share (own 100: nothing written)
            e["arms" + sfx] = sv("arms") / 100.0
        if abs(sv("hands") - 100.0) > 1e-9:
            e["hands" + sfx] = sv("hands") / 100.0
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_walk_hands -v`

Expected: PASS, every test.

- [ ] **Step 6: Run the gait and panel suites**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_walkgait tests.test_walk_panel tests.test_walk_scene_params tests.test_walk_cards tests.test_walk_cycle_cards -v`

Expected: PASS. A test that counts the parameters or a group's sliders may need its number raised by two - raise it, do not weaken it.

- [ ] **Step 7: Commit**

```bash
printf 'feat(walk): Arms %% and Hands %% in the card Arms group\n\nTwo sided parameters, 100 %% by default: how much of the cycle own animation each\npart of the arm keeps. Both at 0 is exactly what a pose grip does.\n\nThe parameter layer had no way to write the arms amplitude at all since\n2026-10-26: engine_knobs never assigned e["arms"], and the only mention of the\nname was from_legacy, which turns an old memo arms into an arm_swing ratio.\nThat translation is left as it is.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n' > "$TMP/msg2.txt"
git add SkeldarAnim/maya_walk/gait.py tests/test_walk_hands.py
git commit -F "$TMP/msg2.txt"
```

---

### Task 3: the Pick line

**Files:**
- Modify: `SkeldarAnim/maya_walk/model.py:4718` (`describe`)
- Test: `tests/test_walk_hands.py` (add a class)

**Interfaces:**
- Consumes: `info["knobs"]` (the `asked` dict - a sided key is absent where the parameter was not asked, so every read is `.get`).
- Produces: nothing other tasks read.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_walk_hands.py`:

```python
class LineTests(unittest.TestCase):
    """What the Pick line says."""

    def setUp(self):
        self.walk = T.walk()

    def test_the_defaults_say_nothing_about_them(self):
        text = wm.describe(run(self.walk))
        self.assertNotIn("of the cycle", text)

    def test_both_held_are_named(self):
        text = wm.describe(run(self.walk, arms=0.0, arms_l=0.0, arms_r=0.0,
                               hands=0.0, hands_l=0.0, hands_r=0.0))
        self.assertIn("the arms keep 0 %", text)
        self.assertIn("the hands keep 0 %", text)
        self.assertIn("of the cycle", text)

    def test_one_side_is_named_as_that_side_alone(self):
        text = wm.describe(run(self.walk, hands_l=0.0))
        self.assertIn("the left hand keeps 0 % of the cycle", text)
        self.assertNotIn("the arms keep", text)

    def test_two_different_sides_are_both_named(self):
        text = wm.describe(run(self.walk, hands_l=0.0, hands_r=0.5))
        self.assertIn("the left hand keeps 0 %", text)
        self.assertIn("the right hand keeps 50 %", text)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_walk_hands.LineTests -v`

Expected: `test_the_defaults_say_nothing_about_them` PASSES; the other three FAIL with `AssertionError: 'the arms keep 0 % of the cycle' not found in ...`.

- [ ] **Step 3: Write the clause**

In `SkeldarAnim/maya_walk/model.py`, add this helper immediately above `def describe(result):`:

```python
def share_line(info):
    """What Arms % and Hands % hold back, for a status line ("" at their own 100 %). `info["knobs"]` is
    the asked dict and engine_knobs writes a key only where the parameter was asked, so every read
    falls back - the side's own value, then the knob's, then 1.0 (2026-11-04)."""
    k = info.get("knobs") or {}
    out = []
    for knob, many, one in (("arms", "arms", "arm"), ("hands", "hands", "hand")):
        both = float(k.get(knob, 1.0))
        per = dict((s, float(k.get("%s_%s" % (knob, s), both))) for s in SIDES)
        if abs(per["l"] - per["r"]) < 1e-9:
            if abs(per["l"] - 1.0) > 1e-9:
                out.append("the %s keep %.0f %%" % (many, 100.0 * per["l"]))
        else:
            for s, word in (("l", "left"), ("r", "right")):
                if abs(per[s] - 1.0) > 1e-9:
                    out.append("the %s %s keeps %.0f %%" % (word, one, 100.0 * per[s]))
    return (" | " + ", ".join(out) + " of the cycle") if out else ""
```

Then change `describe`'s last line - the only other edit in this task - from

```python
    return text + placement_line(info) + balance_line(info)
```

to

```python
    return text + share_line(info) + placement_line(info) + balance_line(info)
```

Nothing inside `describe`'s body moves: the clause is a helper beside `placement_line` and `balance_line`, which is how every other note of that line is written.

- [ ] **Step 4: Run the test to verify it passes**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_walk_hands -v`

Expected: PASS, every test. If `test_two_different_sides_are_both_named` fails on the wording, fix the TEST's expected strings to the wording the helper produces and keep the helper - but each string must still name the side, the part and the percent.

- [ ] **Step 5: Commit**

```bash
printf 'feat(walk): the Pick line names a part held back from the cycle\n\nshare_line reads info["knobs"], which is the asked dict - engine_knobs writes a\nkey only where the parameter was asked, so every read falls back to the side own\nvalue, then the knob, then 1.0.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n' > "$TMP/msg3.txt"
git add SkeldarAnim/maya_walk/model.py tests/test_walk_hands.py
git commit -F "$TMP/msg3.txt"
```

---

### Task 4: the proof on the animator's own cycle

**Files:**
- Create: `docs/superpowers/plans/walkparam/verify_walk_hands.py`

**Interfaces:**
- Consumes: the engine knob `hands` (Task 1), the parameters `arms` / `hands` (Task 2).
- Produces: nothing other tasks read.

- [ ] **Step 1: Write the verify script**

Create `docs/superpowers/plans/walkparam/verify_walk_hands.py`:

```python
"""verify_walk_hands.py - Arms % and Hands % on the animator's own cycle, in mayapy standalone.

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_hands.py

The animator (2026-11-04): «нужен парамметр который будет контролировать процент анимации кистей с
оригинального цикла ... В позе с ножиком не удается получить статические руки при нулевых значениях
ручек в weapon». The design: docs/superpowers/specs/2026-11-04-walk-hands-from-the-cycle-design.md.

Their own cycle under their own two pose cards and their own card state (read off userPrefs.mel): the
sword card's grip stills its hands by itself (6.84 deg of hand in the pelvis's frame, 0.0 deg of
finger); the dagger card's do not (16.25 / 14.01 and 11.1 / 12.8). Every gate measures what the eye
reads: the hand in the PELVIS's frame and each finger's own local turn.

Row vectors: a local is w[j] @ w[parent].T, never the other way round (trap 225).
"""
import math
import os
import shutil
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
LIBRARY = os.environ.get("POSE_LIBRARY", "C:/Users/MY PC/Documents/maya/scripts/SkeldarAnim/poses")
WALK = os.environ.get("HANDS_WALK", "own:7833074715b34c33")
SWORD = os.environ.get("HANDS_SWORD", "LongSword_Idle_3P.pose")
DAGGER = os.environ.get("HANDS_DAGGER", "DG_Idle.pose")
#  their card, read off userPrefs.mel 2026-11-03 20:48: the Chest chip on, Rotation 0, Position 0, 2H on
THEIRS = {"changes": {"weapon_chest": ["offset", 1.0], "weapon_chest_rotation": ["offset", -1.0],
                      "weapon_chest_position": ["offset", -1.0], "weapon_hold": ["offset", 1.0]},
          "pins": ["weapon_chest", "weapon_chest_position", "weapon_chest_rotation", "weapon_hold"],
          "physics": True}
HELD = {"r": {"grip": (2.0, -3.0, 1.0), "tip": (2.0, -3.0, 116.0)}}   # the Long Sword's own blade
FLOOR = 6.84          # deg: a still hand in the pelvis's frame on this cycle - the body's own turn
STILL = 0.05          # deg: what counts as a still finger

import maya.standalone                                        # noqa: E402
maya.standalone.initialize()
import maya.cmds as cmds                                      # noqa: E402

sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))          # the repository's plugin, never the installed copy
from maya_walk import scene as sw                              # noqa: E402
from maya_walk import cards as wcards                          # noqa: E402
from maya_walk import pose as wp                               # noqa: E402

wm, gait = sw.wm, sw.gait
FAILED, COUNT = [], [0]


def gate(ok, text):
    COUNT[0] += 1
    print("gate %2d %s  %s" % (COUNT[0], "ok  " if ok else "FAIL", text))
    sys.stdout.flush()
    if not ok:
        FAILED.append(COUNT[0])


TEMP = tempfile.mkdtemp(prefix="walk_hands_")
COPY = os.path.join(TEMP, "SkeldarWalks")
shutil.copytree(sw.folder(), COPY)                             # never the animator's own folder
sw.WALKS = COPY
cmds.optionVar(stringValue=("skeldarPoseLibraryRoot", LIBRARY))
if not sw.walk_exists(WALK):
    print("no walk %s in %s - nothing to verify" % (WALK, sw.folder()))
    raise SystemExit(1)

walk, statics = sw.load_walk(WALK, sw.normal_params(THEIRS)["clean"])[:2]
chains = walk._arm_chains()
PELVIS = walk.index["pelvis"]
print("walk %s: %d frames at %.1f fps" % (WALK, walk.P, walk.fps))


def fingers(side):
    hand = chains[side][-1]
    out, queue = [], [hand]
    while queue:
        p = queue.pop(0)
        for j, par in enumerate(walk.parents):
            if par == p:
                if walk.kind[j] == "finger":
                    out.append(j)
                queue.append(j)
    return out


def spread(rots):
    mean = wm.orthonormal(np.mean(rots, axis=0))
    return max(math.degrees(float(np.linalg.norm(wm.log_rot(mean.T @ r)))) for r in rots)


def own_turn(res, j):
    w, p = res.worlds, walk.parents[j]
    return spread([w[j, f, :3, :3] @ w[p, f, :3, :3].T for f in range(w.shape[1])])


def in_pelvis(res, j):
    w = res.worlds
    return spread([w[j, f, :3, :3] @ w[PELVIS, f, :3, :3].T for f in range(w.shape[1])])


def read(res):
    """{side: (the hand in the pelvis's frame, the most any finger turns)} in degrees."""
    out = {}
    for side in ("l", "r"):
        fing = fingers(side)
        out[side] = (in_pelvis(res, chains[side][-1]),
                     max([own_turn(res, j) for j in fing] or [0.0]))
    return out


def card(name):
    path = os.path.join(LIBRARY, name)
    if not os.path.isdir(path):
        return None
    bones = wcards.read_card(path)[1]
    return wp.filtered(wp.prepare(walk, statics, bones, wm, sw.wt), sw.ALL_PARTS)


def run(pose, changes=(), engine=()):
    p = dict(THEIRS)
    p["changes"] = dict(THEIRS["changes"], **dict(changes))
    p["pins"] = sorted(set(THEIRS["pins"]) | set(dict(changes)))
    ks = dict(sw.params_knobs(walk, sw.normal_params(dict(p, pose=1.0)))[0], in_place=0.0, **dict(engine))
    return walk.evaluate(ks, pose, weapons=HELD)


sword, dagger = card(SWORD), card(DAGGER)
if sword is None or dagger is None:
    print("missing a card in %s - nothing to verify" % LIBRARY)
    raise SystemExit(1)
own = gait.own(walk)
ZERO = {"arms": ("offset", -100.0), "hands": ("offset", -100.0), "arm_drag": ("offset", -1.5)}

# ---- 1-2: the two cards as they are, the problem the animator reported
s, d = read(run(sword)), read(run(dagger))
gate(abs(s["r"][0] - FLOOR) < 0.2 and abs(s["l"][0] - FLOOR) < 0.2 and max(s["r"][1], s["l"][1]) < STILL,
     "the sword card's hands are still: %.2f / %.2f deg in the pelvis, fingers %.2f / %.2f"
     % (s["r"][0], s["l"][0], s["r"][1], s["l"][1]))
gate(min(d["r"][0], d["l"][0]) > FLOOR + 3.0 and min(d["r"][1], d["l"][1]) > 5.0,
     "the dagger card's are not: %.2f / %.2f deg, fingers %.2f / %.2f"
     % (d["r"][0], d["l"][0], d["r"][1], d["l"][1]))

# ---- 3: the defaults change nothing at all
plain = run(dagger)
same = run(dagger, [("arms", ("offset", 0.0)), ("hands", ("offset", 0.0))])
gate(np.array_equal(plain.worlds, same.worlds),
     "Arms 100 % and Hands 100 % are the cycle itself, matrix for matrix")

# ---- 4-5: Hands 0 % stills the fingers, per side
both = read(run(dagger, [("hands", ("offset", -100.0))]))
gate(max(both["r"][1], both["l"][1]) < STILL,
     "Hands 0 %%: the dagger's fingers stand still (%.3f / %.3f deg)" % (both["r"][1], both["l"][1]))
one = read(run(dagger, [("hands_l", ("offset", -100.0))]))
gate(one["l"][1] < STILL and abs(one["r"][1] - d["r"][1]) < 0.01,
     "Hands_l 0 %%: the left fingers still (%.3f), the right as they were (%.2f against %.2f)"
     % (one["l"][1], one["r"][1], d["r"][1]))

# ---- 6: the whole ask together reaches the sword's floor
held = read(run(dagger, list(ZERO.items())))
gate(abs(held["r"][0] - FLOOR) < 0.2 and abs(held["l"][0] - FLOOR) < 0.2
     and max(held["r"][1], held["l"][1]) < STILL,
     "Arms 0 %% + Hands 0 %% + Arm drag 0 bring the dagger to the sword's floor: %.2f / %.2f deg, "
     "fingers %.3f / %.3f" % (held["r"][0], held["l"][0], held["r"][1], held["l"][1]))

# ---- 7: the control - nothing but Hands reaches the fingers
drag_only = read(run(dagger, [("arm_drag", ("offset", -1.5))]))
gate(min(drag_only["r"][1], drag_only["l"][1]) > 5.0,
     "the control: with Arm drag 0 alone the fingers still turn (%.2f / %.2f deg) - nothing but "
     "Hands reaches them" % (drag_only["r"][1], drag_only["l"][1]))

# ---- 8: the sword card is untouched by the new knobs at their own value
s2 = read(run(sword, [("arms", ("offset", 0.0)), ("hands", ("offset", 0.0))]))
gate(abs(s2["r"][0] - s["r"][0]) < 1e-6 and abs(s2["l"][0] - s["l"][0]) < 1e-6,
     "the sword card reads the same at the defaults (%.2f / %.2f deg)" % (s2["r"][0], s2["l"][0]))

# ---- 9-10: the cycle still closes and the bones keep their lengths
res = run(dagger, list(ZERO.items()))
w = res.worlds
seam = max(float(np.max(np.abs(w[j, -1, :3, :3] - w[j, 0, :3, :3]))) for j in range(len(walk.names)))
gate(seam < 2e-3, "the loop still closes (worst rotation element %.2e)" % seam)
worst = 0.0
for side in ("l", "r"):
    chain = chains[side]
    for a, b in zip(chain[:-1], chain[1:]):
        lens = [float(np.linalg.norm(w[b, f, 3, :3] - w[a, f, 3, :3])) for f in range(w.shape[1])]
        worst = max(worst, max(lens) - min(lens))
gate(worst < 1e-4, "the arm bones keep their lengths (worst %.2e cm)" % worst)

print("\n%d gate(s) failed%s" % (len(FAILED), (": " + ", ".join(map(str, FAILED))) if FAILED else ""))
shutil.rmtree(TEMP, ignore_errors=True)
raise SystemExit(1 if FAILED else 0)
```

- [ ] **Step 2: Run it**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_hands.py`

Expected: `0 gate(s) failed`. Numbers to expect, from the spec's table: gate 1 reads 6.84 / 6.84 and 0.0 / 0.0; gate 2 reads 16.25 / 14.01 and 11.1 / 12.8; gate 6 reads 6.84 / 6.84 and ~0.

If a gate fails, do NOT widen its bound. Read the number it prints and find out why - the spec's table is what the code has to reproduce.

- [ ] **Step 3: Run it again against the code before this work, as the control**

Tasks 1-3 are committed by now, so `git stash` would hide nothing. Use a worktree at `20bc6f12` - this work's spec commit, documentation only, so its tree holds the code as it was - and run the NEW script against the OLD code by pointing it at the script in this tree:

```bash
git worktree add ../MayaScripts-before 20bc6f12
cd ../MayaScripts-before
cp ../MayaScripts/docs/superpowers/plans/walkparam/verify_walk_hands.py docs/superpowers/plans/walkparam/
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_hands.py
cd ../MayaScripts
git worktree remove --force ../MayaScripts-before
```

Expected: it FAILS - gates 3 to 6 at least, with `ValueError: unknown knob(s): hands` out of the parameter road or the fingers still turning at 11.1 / 12.8 deg. That failure is the proof the gates are real; a verify that passes on the code it is meant to test is worth nothing.

- [ ] **Step 4: Commit**

```bash
printf 'test(walk): verify Arms %% and Hands %% on the animator own cycle\n\nTheir own cycle under their own two cards and their own card state: the sword\ngrip stills its hands by itself (6.84 deg of hand in the pelvis frame, 0.0 of\nfinger), the dagger does not (16.25 / 14.01 and 11.1 / 12.8). With Arms 0 %%,\nHands 0 %% and Arm drag 0 the dagger comes to the same floor.\n\nEvery gate carries the code before this work as its control.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n' > "$TMP/msg4.txt"
git add docs/superpowers/plans/walkparam/verify_walk_hands.py
git commit -F "$TMP/msg4.txt"
```

Replace the numbers in the message with the ones the run actually printed.

---

### Task 5: the neighbours, and CLAUDE.md

**Files:**
- Modify: `CLAUDE.md` (the Walk Builder section)

**Interfaces:**
- Consumes: everything above.
- Produces: nothing.

- [ ] **Step 1: Run the whole unit suite**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v 2>&1 | Select-Object -Last 40`

Expected: OK but for `tests/test_chat_deploy.Keys`, which fails on this machine because it reads the animator's own saved Cloudflare keys. Any other failure is this work's and must be fixed.

- [ ] **Step 2: Run the walk verifies that touch the arms**

Run each, and record its result:

```
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_arm_overlap.py
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_weapon_overlap.py
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_weapon_chest.py
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_one_arm.py
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_gait.py
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_keys_changed.py
```

Expected: `0 of N gates failed` for the first four and the last. `verify_walk_gait.py` has four known failures (dw's `foot_lift`, sadda's `swing_out` x3) and `verify_walk.py` / `verify_walk_own.py` / `verify_walk_many.py` fail on a clean tree too.

- [ ] **Step 3: Prove every failure is not ours**

For any verify that fails, run the same script in a clean worktree of the commit before this work and compare the failing gate numbers digit for digit:

`20bc6f12` is this work's spec commit - documentation only, so its tree holds the code as it was before any of this:

```bash
git worktree add ../MayaScripts-before 20bc6f12
cd ../MayaScripts-before
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_gait.py
cd ../MayaScripts
git worktree remove ../MayaScripts-before
```

Expected: the same gate numbers and the same digits. If a failure is new, it is ours - fix it.

- [ ] **Step 4: Write the CLAUDE.md section**

Append to the Walk Builder run of sections in `CLAUDE.md` (after the 2026-11-02 one-arm paragraph), in the file's own voice: the animator's words, what was measured on their own cycle (the table's two rows, the grip as the cause, the fingers' hard 1.0, the amplitude the parameter layer lost), the two knobs and their defaults, the cost (under 2H the hand rides the weapon; `Arms` and `Arm swing` are different quantities), the proof (the unit tests, the verify's gate count, the neighbours), and what is not built. Add trap 225's measuring side as a one-line note if it is not already there under that number.

- [ ] **Step 5: Commit**

```bash
printf 'docs(walk): Arms %% and Hands %% in the working notes\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n' > "$TMP/msg5.txt"
git add CLAUDE.md
git commit -F "$TMP/msg5.txt"
```

- [ ] **Step 6: Report, do not push**

Report to the animator: the gate counts, the measured before/after on their own cycle, and that their Maya on 7002 still has a modal dialog holding its idle queue, so the live check is theirs after a Check update. Ask before pushing.
