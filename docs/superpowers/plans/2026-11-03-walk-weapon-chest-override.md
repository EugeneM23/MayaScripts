# Walk Builder's weapon overlap from the chest - implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended)
> or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** four parameters in Walk Builder's Weapon tab - 2H, Chest rotation, Chest position, Chest lag -
that carry the weapon from the chest, late and scaled, with the hands re-solved onto it, on any skeleton
and with no rig.

**Architecture:** one new pass `Walk._weapon_chest` inside `model._arm_overlap`, before `_weapon_swing`.
In the model a weapon is two points in the holding hand's frame, so every weapon motion is a right
multiplication on the hand matrices and `_arm_to_hand` rebuilds the arm by IK: «the hands follow the
weapon» is free. The chest's own matrices come from `kin`, read `lag` frames earlier with
`shifted_cycle`, so the cycle's loop closes.

**Tech Stack:** `SkeldarAnim/maya_walk/{gait,model,scene}.py` (numpy, stdlib), `tests/` (unittest under
mayapy), `docs/superpowers/plans/walkparam/` (verify scripts, mayapy standalone).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-11-03-walk-weapon-chest-override-design.md`.
- **The defaults change nothing**: `1 / 1 / 0` is the identity matrix for matrix, and `own_knobs()` must
  give the cycle back exactly. Every other walk gate depends on it.
- **The loop must close**: frame `n` is frame 0 moved by the cycle's travel. Read the chest with
  `shifted_cycle`, never with a clamp.
- Row vectors throughout: a point is `p @ m[:3, :3] + m[3, :3]`; a world transform applies on the RIGHT.
- Milliseconds become frames of the new cycle at the output rate, as `weapon_overlap` does
  (`engine_knobs(..., fps_out=)`).
- `tests/test_gait_model.ParityTests` holds the Gait Builder fork
  (`docs/superpowers/plans/gaitbuilder/gaitmodel.py`) to the model frame for frame: the pass is copied
  there word for word.
- Tests run as `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest <module> -v` from the
  repo root.

---

### Task 1: `moved_about` - a world turn and a move about a point

**Files:**
- Modify: `SkeldarAnim/maya_walk/model.py` (beside `swung_about`)
- Test: `tests/test_walk_weapon_chest.py`

**Interfaces:**
- Produces: `moved_about(origin, rot, offset) -> (4, 4)` - `p @ out == (p - o) @ rot + o + offset`.

- [ ] **Step 1: the failing test**

```python
import numpy as np
from maya_walk import model

class MovedAbout(unittest.TestCase):
    def test_the_origin_itself_takes_the_offset_and_nothing_else(self):
        o, d = np.array([3.0, 4.0, 5.0]), np.array([0.0, 2.0, 0.0])
        m = model.moved_about(o, model.exp_rot(np.array([0.0, 0.7, 0.0])), d)
        got = o @ m[:3, :3] + m[3, :3]
        self.assertTrue(np.allclose(got, o + d, atol=1e-12))

    def test_a_point_swings_about_the_origin_and_then_moves(self):
        o, d = np.zeros(3), np.array([1.0, 0.0, 0.0])
        rot = model.exp_rot(np.array([0.0, np.pi / 2.0, 0.0]))
        m = model.moved_about(o, rot, d)
        p = np.array([1.0, 0.0, 0.0])
        self.assertTrue(np.allclose(p @ m[:3, :3] + m[3, :3], p @ rot + d, atol=1e-12))

    def test_identity_rotation_and_no_offset_is_the_identity(self):
        m = model.moved_about(np.array([7.0, -2.0, 1.0]), np.eye(3), np.zeros(3))
        self.assertTrue(np.allclose(m, np.eye(4), atol=1e-12))
```

- [ ] **Step 2: run it, expect `AttributeError: module has no attribute 'moved_about'`**

- [ ] **Step 3: the implementation**

```python
def moved_about(origin, rot, offset):
    """The world turn `rot` (3x3) about the point `origin` followed by the move `offset`, as a 4x4:
    a point p maps to (p - o) . rot + o + offset (row vectors). swung_about with a move, which is how
    the chest's motion is scaled: its turn about its own pivot, its travel as an offset."""
    out = swung_about(origin, rot)
    out[3, :3] = out[3, :3] + np.asarray(offset, float)
    return out
```

- [ ] **Step 4: run the three tests, expect PASS**

- [ ] **Step 5: commit**

```bash
git add SkeldarAnim/maya_walk/model.py tests/test_walk_weapon_chest.py
git commit -m "feat(walk): moved_about - a world turn and a move about a point"
```

---

### Task 2: the engine knobs, inert

**Files:**
- Modify: `SkeldarAnim/maya_walk/model.py` (`KNOBS` after `weapon_overlap`, `SIDED`)
- Test: `tests/test_walk_weapon_chest.py`

**Interfaces:**
- Produces: engine knobs `weapon_hold` (0/1), `weapon_chest_rotation` (default 1), `weapon_chest_position`
  (default 1), `weapon_chest_lag` (frames, default 0), all sided (`<name>_l` / `_r`).

- [ ] **Step 1: the failing test**

```python
class EngineKnobs(unittest.TestCase):
    def test_the_four_knobs_exist_with_their_defaults(self):
        k = model.knobs({})
        self.assertEqual(k["weapon_hold"], 0.0)
        self.assertEqual(k["weapon_chest_rotation"], 1.0)
        self.assertEqual(k["weapon_chest_position"], 1.0)
        self.assertEqual(k["weapon_chest_lag"], 0.0)

    def test_they_are_sided(self):
        for name in ("weapon_hold", "weapon_chest_rotation", "weapon_chest_position",
                     "weapon_chest_lag"):
            self.assertIn(name, model.SIDED, name)
            k = model.knobs({name + "_l": 0.5})
            self.assertEqual(model.sided(k)["l"][name], 0.5)
```

- [ ] **Step 2: run it, expect KeyError on `weapon_hold`**

- [ ] **Step 3: the implementation** - in `KNOBS`, right after the `weapon_overlap` entry:

```python
    # The weapon from the CHEST (2026-11-03): the weapon keeps its own pose relative to the chest and the
    # chest's own pose from `weapon_chest_lag` frames earlier is put back, its turn slerped from the identity
    # by `weapon_chest_rotation` and its travel scaled by `weapon_chest_position`, both about the chest's own
    # pivot - so 1 / 1 / 0 is the identity. Every hand holding the weapon is moved with it (the hands follow
    # the weapon, _arm_to_hand rebuilds the arm). `weapon_hold` binds the free hand to the holder's by the
    # offset it has at frame 0: a two-handed carry with no pose grip. Per side; it needs the weapon the
    # SCENE holds (evaluate's `weapons`)
    ("weapon_hold", 0.0, 0.0, 1.0),
    ("weapon_chest_rotation", 1.0, 0.0, 1.0),
    ("weapon_chest_position", 1.0, 0.0, 1.0),
    ("weapon_chest_lag", 0.0, -120.0, 120.0),
```

and the four names appended to `SIDED`.

- [ ] **Step 4: run the tests, expect PASS**

- [ ] **Step 5: commit**

```bash
git commit -am "feat(walk): the chest override's engine knobs, inert"
```

---

### Task 3: the chest joint

**Files:**
- Modify: `SkeldarAnim/maya_walk/model.py` (a method on `Walk`)
- Test: `tests/test_walk_weapon_chest.py`

**Interfaces:**
- Produces: `Walk._chest_joint() -> int | None` - the joint whose world the weapon inherits.

- [ ] **Step 1: the failing test** (the suite's own walker fixture; `tests/test_walkmodel.py` builds one
  with `walker()` - import the same helper)

```python
class ChestJoint(unittest.TestCase):
    def test_it_is_the_top_spine_joint_the_chest_knobs_use(self):
        walk = _walker()                      # the suite's fixture, UE-named
        j = walk._chest_joint()
        self.assertIsNotNone(j)
        self.assertIn(j, walk.chest_share)
        top = max((int(walk.names[x].split("_")[-1]), x) for x in walk.chest_share)[1]
        self.assertEqual(j, top)

    def test_with_no_spine_it_falls_back_to_the_arm_chains_parent(self):
        walk = _walker()
        walk.chest_share = {}
        j = walk._chest_joint()
        chains = walk._arm_chains()
        self.assertEqual(j, walk._parent(chains["r"][0]))
```

- [ ] **Step 2: run it, expect `AttributeError: '_chest_joint'`**

- [ ] **Step 3: the implementation**

```python
    def _chest_joint(self):
        """The joint the weapon inherits its motion from under the chest override: the TOP spine joint the
        chest knobs already use (`chest_share`), so no name is hardcoded here; with no spine of its own, the
        parent of an arm chain's first joint, which is what the arms hang from either way. None with neither."""
        if self.chest_share:
            return max((int(re.match(r".*?(\d+)$", self.names[j]).group(1)), j)
                       for j in self.chest_share)[1]
        chains = self._arm_chains()
        for side in sorted(chains):
            parent = self._parent(chains[side][0])
            if parent is not None and parent >= 0:
                return parent
        return None
```

(check the real spelling of the parent lookup in `model.py` - `self._parent(j)` or `self.parent[j]` -
and use the one that is there.)

- [ ] **Step 4: run the tests, expect PASS**

- [ ] **Step 5: commit**

```bash
git commit -am "feat(walk): the chest joint the weapon inherits from"
```

---

### Task 4: the pass - the chest carries the weapon

**Files:**
- Modify: `SkeldarAnim/maya_walk/model.py` (`_weapon_chest`, called from `_arm_overlap`)
- Test: `tests/test_walk_weapon_chest.py`

**Interfaces:**
- Consumes: `moved_about` (Task 1), the knobs (Task 2), `_chest_joint` (Task 3).
- Produces: `Walk._weapon_chest(kin, n, chains, hands, settings, held, riders) -> float` (the most a grip
  point moved, cm), and `info["arms"]["overlap"]["chest"]` / `["chest_cm"]` / `["hold"]`.

- [ ] **Step 1: the failing tests**

```python
class ChestOverride(unittest.TestCase):
    def test_the_defaults_are_the_identity_matrix_for_matrix(self):
        plain = _result(_walker(), {})
        same = _result(_walker(), {"weapon_chest_rotation": 1.0, "weapon_chest_position": 1.0,
                                   "weapon_chest_lag": 0.0})
        self.assertTrue(np.allclose(plain, same, atol=0.0))

    def test_at_full_strength_the_weapon_takes_the_chests_pose_from_lag_frames_back(self):
        # the weapon's pose relative to the chest, under a lag, equals the chest's own `lag` frames earlier
        ...

    def test_rotation_zero_keeps_the_weapons_turn(self):
        ...

    def test_position_zero_keeps_the_weapons_place(self):
        ...

    def test_the_grip_is_kept(self):
        # the weapon's two points in the holding hand's frame are unchanged by the pass
        ...

    def test_the_loop_closes(self):
        ...
```

(Write them against the fixture the walk suite already uses, measuring the GAME joints of the result,
as `tests/test_walk_weapon_overlap.py` does for `Weapon overlap` - follow that file's shape.)

- [ ] **Step 2: run them, expect failures (nothing moves under the knobs)**

- [ ] **Step 3: the implementation** - the pass:

```python
    def _weapon_chest(self, kin, n, chains, hands, settings, held, riders):
        """The chest carries the weapon, late and scaled (in place on `hands`). For every weapon in a hand,
        with C the chest's world and Clate the same cycle read `lag` frames earlier (shifted_cycle, so the
        loop closes): T(f) = inv(C(f)) . Clate(f) - the weapon keeps its own pose relative to the chest and
        the chest's own pose from `lag` frames earlier is put back. The turn is slerped from the identity by
        `rotation` and the travel scaled by `position`, both about the chest's own pivot, so 1 / 1 / 0 is the
        identity. Every hand holding that weapon - and its riders - takes the same T, so the grip is kept to
        machine precision and `_arm_to_hand` rebuilds the arm. Returns the most a grip point moved, cm."""
        chest = self._chest_joint()
        if chest is None:
            return 0.0
        moved = 0.0
        for side, (rotation, position, lag) in sorted(settings.items()):
            C = kin[chest]
            late = shifted_cycle(C, lag)
            for s in riders[side]:
                if s not in hands:
                    hands[s] = np.array(kin[chains[s][-1]])
            grip_p = np.asarray(held[side]["grip"], float)
            place = lambda p, m: p @ m[:3, :3] + m[3, :3]
            for f in range(n + 1):
                rot = np.linalg.inv(C[f]) @ late[f]
                r = rot[:3, :3]
                if rotation < 1.0:
                    r = exp_rot(log_rot(r) * rotation)
                c, c_late = C[f][3, :3], late[f][3, :3]
                T = moved_about(c, r, (c_late - c) * position)
                before = place(grip_p, hands[side][f])
                for s in riders[side]:
                    hands[s][f] = hands[s][f] @ T
                moved = max(moved, float(np.linalg.norm(place(grip_p, hands[side][f]) - before)))
        return moved
```

and its wiring in `_arm_overlap`, after `hands` is built and BEFORE `_weapon_swing`:

```python
        chest_set = {}
        for side in held:
            rotation = float(ks[side]["weapon_chest_rotation"])
            position = float(ks[side]["weapon_chest_position"])
            lag = float(ks[side]["weapon_chest_lag"])
            if abs(lag) >= OVERLAP_QUIET or rotation < 1.0 or position < 1.0:
                chest_set[side] = (rotation, position, lag)
        riders = dict((side, [side] + [s for s in sorted(chains)
                                       if s != side and s not in held
                                       and (grip or float(ks[s]["weapon_hold"]) > 0.5)])
                      for side in held)
        out["chest"] = sorted(chest_set)
        out["chest_cm"] = 0.0
        if chest_set:
            out["chest_cm"] = self._weapon_chest(kin, n, chains, hands, chest_set, held, riders)
```

with `out["weapon"]`'s early-out widened so a chest setting alone still runs the pass, and
`_weapon_swing` given the same `riders` so 2H rides the aim too.

- [ ] **Step 4: run the tests, expect PASS**

- [ ] **Step 5: commit**

```bash
git commit -am "feat(walk): the chest carries the weapon, late and scaled"
```

---

### Task 5: 2H - the free hand bound to the holder's

**Files:**
- Modify: `SkeldarAnim/maya_walk/model.py` (`_arm_overlap`)
- Test: `tests/test_walk_weapon_chest.py`

**Interfaces:**
- Consumes: the knobs (Task 2), `riders` (Task 4).
- Produces: `info["arms"]["overlap"]["hold"]` - the sides bound.

- [ ] **Step 1: the failing test**

```python
class TwoHands(unittest.TestCase):
    def test_the_free_hand_keeps_the_frame_zero_offset_on_every_frame(self):
        ...   # other(f) @ inv(holder(f)) equal to its value at f = 0, every frame

    def test_a_hand_holding_its_own_weapon_is_not_bound(self):
        ...

    def test_off_it_changes_nothing(self):
        ...
```

- [ ] **Step 2: run them, expect failure**

- [ ] **Step 3: the implementation** - in `_arm_overlap`, right before the weapon passes:

```python
        hold = sorted(s for s in chains
                      if float(ks[s]["weapon_hold"]) > 0.5 and s not in held
                      and any(s in riders[w] for w in riders))
        out["hold"] = hold
        for s in hold:
            holder = [w for w in riders if s in riders[w]][0]
            for who in (holder, s):
                if who not in hands:
                    hands[who] = np.array(kin[chains[who][-1]])
            off = hands[s][0] @ np.linalg.inv(hands[holder][0])
            for f in range(n + 1):
                hands[s][f] = off @ hands[holder][f]
```

- [ ] **Step 4: run the tests, expect PASS**

- [ ] **Step 5: commit**

```bash
git commit -am "feat(walk): 2H binds the free hand to the one holding the weapon"
```

---

### Task 6: Balance sees it, and the line says it

**Files:**
- Modify: `SkeldarAnim/maya_walk/model.py:3020-3030` (`moved_arms`),
  `SkeldarAnim/maya_walk/scene.py:1462` (the Pick line)
- Test: `tests/test_walk_weapon_chest.py`

- [ ] **Step 1: the failing tests**

```python
class Reported(unittest.TestCase):
    def test_balance_carries_the_hips_differently_with_the_pass_on(self):
        ...

    def test_the_line_names_the_trail_and_the_hold(self):
        ...
```

- [ ] **Step 2: run them, expect failure**

- [ ] **Step 3: the implementation** - `moved_arms` gains, per side:

```python
                             or (s in (ctx.get("weapons") or {})
                                 and (abs(ks[s]["weapon_chest_lag"]) >= OVERLAP_QUIET
                                      or ks[s]["weapon_chest_rotation"] < 1.0
                                      or ks[s]["weapon_chest_position"] < 1.0))
                             or ks[s]["weapon_hold"] > 0.5
```

and the line, beside the existing weapon clause:

```python
        if over.get("chest"):
            text += " | the weapon trails the chest %.1f cm" % over["chest_cm"]
        if over.get("hold"):
            text += " | 2H: both hands on the weapon"
```

- [ ] **Step 4: run the tests, expect PASS**

- [ ] **Step 5: commit**

```bash
git commit -am "feat(walk): Balance sees the chest override, the line names it"
```

---

### Task 7: the four parameters in the Weapon tab

**Files:**
- Modify: `SkeldarAnim/maya_walk/gait.py` (`PARAMS` after `weapon_overlap`, `engine_knobs`'s sided loop,
  `ranges`' overlap list)
- Test: `tests/test_walk_weapon_chest.py`

**Interfaces:**
- Produces: parameters `weapon_hold`, `weapon_chest_rotation`, `weapon_chest_position`,
  `weapon_chest_lag`; `engine_knobs` writing the four engine knobs per side.

- [ ] **Step 1: the failing tests**

```python
class Parameters(unittest.TestCase):
    def test_the_weapon_tab_holds_the_four_beside_the_overlap(self):
        names = [p.name for p in gait.PARAMS if p.group == gait.WEAPON]
        self.assertEqual(names, ["weapon_overlap", "weapon_hold", "weapon_chest_rotation",
                                 "weapon_chest_position", "weapon_chest_lag"])

    def test_the_lag_is_ms_turned_into_frames_at_the_output_rate(self):
        e = gait.engine_knobs(walk, {"weapon_chest_lag": ("offset", 150.0)}, fps_out=30.0)
        self.assertAlmostEqual(e["weapon_chest_lag_r"], 4.5, places=6)

    def test_the_lag_reaches_half_the_cycle_either_way(self):
        ...   # gait.ranges()["weapon_chest_lag"] == (-cap, cap)

    def test_the_defaults_read_back_as_the_cycles_own(self):
        ...   # own(walk) gives 1 / 1 / 0 and `measure` does not read them
```

- [ ] **Step 2: run them, expect failure**

- [ ] **Step 3: the implementation** - the four `Param`s after the `weapon_overlap` entry:

```python
    Param("weapon_hold", WEAPON, "2H", "", "toggle", sided=True, default=0.0,
          tip="Binds the free hand to the one holding the weapon - it keeps the offset it has at the "
              "cycle's first frame and rides the weapon from then on, so a two-handed carry holds "
              "without a pose's own grip. That arm's own swing becomes a consequence. A hand holding "
              "its own weapon is left alone"),
    Param("weapon_chest_rotation", WEAPON, "Chest rotation", "", "added", sided=True,
          rule=_fixed(0.0, 1.0), default=1.0,
          tip="How much of the chest's TURN the weapon inherits: 1 as the body turns it (the default, "
              "nothing changes), 0 and the weapon keeps its own heading while the body turns under it"),
    Param("weapon_chest_position", WEAPON, "Chest position", "", "added", sided=True,
          rule=_fixed(0.0, 1.0), default=1.0,
          tip="How much of the chest's own TRAVEL the weapon inherits: 1 as the body carries it, 0 and "
              "it keeps its place while the chest sways and bobs under it"),
    Param("weapon_chest_lag", WEAPON, "Chest lag", "ms", "added", sided=True,
          rule=_fixed(-OVERLAP_MAX, OVERLAP_MAX),
          tip="The weapon takes the chest's pose from this many milliseconds ago - the body leads and "
              "the weapon follows late, with the holding hand re-solved onto it so the grip holds. It "
              "adds to Weapon overlap, which lags the blade's own aim. The slider reaches half the "
              "cycle either way"),
```

`engine_knobs`, in the sided loop beside `weapon_overlap`:

```python
        e["weapon_hold" + sfx] = 1.0 if sv("weapon_hold") >= 0.5 else 0.0
        e["weapon_chest_rotation" + sfx] = sv("weapon_chest_rotation")
        e["weapon_chest_position" + sfx] = sv("weapon_chest_position")
        e["weapon_chest_lag" + sfx] = sv("weapon_chest_lag") * fps / 1000.0   # ms -> frames
```

and `"weapon_chest_lag"` added to `ranges`' overlap-cap list.

- [ ] **Step 4: run the tests, expect PASS**

- [ ] **Step 5: commit**

```bash
git commit -am "feat(walk): the chest override's four parameters in the Weapon tab"
```

---

### Task 8: the Gait Builder fork keeps parity

**Files:**
- Modify: `docs/superpowers/plans/gaitbuilder/gaitmodel.py`
- Test: `tests/test_gait_model.py` (`ParityTests`, already there)

- [ ] **Step 1: run the parity tests, expect failures**

Run: `mayapy -m unittest tests.test_gait_model -v`

- [ ] **Step 2: copy `moved_about`, `_chest_joint`, `_weapon_chest`, the `_arm_overlap` wiring and the
  four `KNOBS` entries into the fork, word for word**

- [ ] **Step 3: run the parity tests, expect PASS**

- [ ] **Step 4: commit**

```bash
git commit -am "chore(gait): the fork takes the chest override, parity kept"
```

---

### Task 9: the verify, on the animator's own cycle and on a bare skeleton

**Files:**
- Create: `docs/superpowers/plans/walkparam/verify_walk_weapon_chest.py`

- [ ] **Step 1: write it** on `verify_walk_weapon_overlap.py`'s shape: phase `model` (the promise in the
  model, on their cycle under the two-handed sword pose and with one weapon in one hand) and phase
  `scene` (the whole road through `scene.apply` onto a plain Manny UE5 skeleton, the keys read back).
  Gates, each printing its number:

  1. the defaults matrix for matrix against the walk with the knobs never set;
  2. `own_knobs()` likewise;
  3. at full strength, lag L: the weapon's pose relative to the chest equals the chest's own `L` frames
     earlier (`shifted_cycle`), to 1e-6;
  4. the grip point really moves (a positive control, cm);
  5. `rotation 0`: the weapon's turn over the cycle against the body's own turn as the control;
  6. `position 0`: its travel likewise;
  7. the weapon's two points unchanged in the holding hand's frame (the grip kept);
  8. every bone's length unchanged;
  9. the loop closed (frame n = frame 0 + travel);
  10. 2H: the free hand's offset from the holder equal to its frame-0 offset on every frame;
  11. Balance: the carry differs with the pass on;
  12. `scene.apply` onto a bare Manny UE5 skeleton: the joints' keys show gate 3's promise;
  13. the Pick line names the trail and the hold.

- [ ] **Step 2: run it**

```bash
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_weapon_chest.py
```

Expected: `0 of 13 gates failed`.

- [ ] **Step 3: run the neighbours and compare with the commit before this work**

`verify_walk_weapon_overlap.py`, `verify_walk_arm_overlap.py`, `verify_walk_keys_changed.py`, and the
walk unit suite. Any failure must be identical on a worktree of the commit before.

- [ ] **Step 4: commit**

```bash
git add docs/superpowers/plans/walkparam/verify_walk_weapon_chest.py
git commit -m "test(walk): the chest override, 0 of 13 gates standalone"
```

---

### Task 10: CLAUDE.md and the push

**Files:**
- Modify: `CLAUDE.md` (a subsection under the Walk Builder weapon-overlap section)

- [ ] **Step 1: write the section** - what was asked and in whose words, where the modes already lived
  and why, the four parameters with their defaults, the formula, 2H's frame-0 offset, what is not built,
  and the proof with its numbers.

- [ ] **Step 2: commit and push**

```bash
git add CLAUDE.md
git commit -m "docs(walk): the weapon's overlap from the chest, and a two-handed hold"
git push origin main
```

- [ ] **Step 3: wait for the release** and read `releases/latest/download/version.json` - the payload
  changed, so the build must carry this commit.
