# 2H Weapon and Override mode - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Two options in the Connections card's Weapon tab - a `2H` chip that
binds both hands to the weapon in one press, and an `Override` mode that makes
the chest carry the weapon with a rotation strength, a position strength and a
lag in milliseconds.

**Architecture:** 2H is a pure shortcut for the two hand rows' picks - no new
scene state and no new bake path. Override is a new module
(`maya_scenesetup/weaponoverride.py`) holding the formula and the scene work;
`connections.py` gets only the rows, the picks and the presses. The weapon's
original curves are parked on the weapon itself the way a floor drop parks a
bone's track (`bonedrive.park`), so Default is bit-exact.

**Tech Stack:** Maya 2027 `maya.cmds` + `maya.api.OpenMaya`, the repo's own
`fkik` (keys, tangents, refusals), `aimcore` (the time walk, the fill loop),
`maya_poselib.helpers.driver_channels` (a local matrix into channels),
`maya_timewarp` (scene time warp), `maya_hubstyle` / `maya_hubqt` (the card).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-11-02-connections-2h-and-override-design.md`.
- **Pick, then press** (2026-10-29): a press on a chip, a segment or a field
  RECORDS a pick in `pending`; only a row's check or `Apply all · N` bakes. A
  picked control draws `want`, a row with a pick draws `wait`, and a control's
  lit state is always the SCENE's.
- **One orange per section**: the Weapon tab's one primary stays `Apply all`.
- Every press is one undo chunk; every refusal happens before anything changes.
- Keys go to the active animation layer through `fkik._write`; a layered rotate
  or translate on the weapon is a refusal here (the aim's own rule).
- Every frame walk runs inside `maya_timewarp.unwarped()` with
  `fkik._suspend(True)` and puts the time back.
- Tests: new files only, under `tests/`. Run with
  `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v`
  (there is no system Python). Qt tests want `$env:QT_QPA_PLATFORM = 'offscreen'`.
- The animator's Maya is on port 7002; nothing is pushed until they say so.
- The working tree holds another session's uncommitted work (`maya_shutdown.py`,
  `install.py`, `maya_hub.py`, their spec and tests, and 119 lines of
  `CLAUDE.md`). **Commit only the files named in each task**, and stage the
  `CLAUDE.md` section with `git hash-object -w` + `git update-index --cacheinfo`.

## File Structure

| File | Responsibility |
|---|---|
| `SkeldarAnim/maya_scenesetup/weaponoverride.py` | **new.** The Override mode: the formula (pure, OpenMaya), the settings parked on the weapon, `enter` / `leave` / `state` / `refusal`. |
| `SkeldarAnim/maya_scenesetup/pending.py` | one key, `OVERRIDE`, in `TAB["weapon"]`, `_RANK` and `phrase`. |
| `SkeldarAnim/maya_scenesetup/connections.py` | the `2H` chip (two pure functions, a press, the painting), the Override row (chip, three fields, check), their picks, the `apply_weapon` leg and the Default/enter dance in `apply`. |
| `tests/test_pending_override.py` | the new pick key: the tab, the order, the words. |
| `tests/test_weapon_override.py` | the formula and the pure halves; the scene halves on a fake `cmds`. |
| `tests/test_connections_two_hands.py` | the 2H picks, the chip's state, the card's row. |
| `tests/test_connections_override_row.py` | the Override row: the pick, the painting, the apply leg. |
| `docs/superpowers/plans/verify_weapon_override.py` | mayapy standalone, every gate printing its number. |

---

### Task 1: the `OVERRIDE` pick key

**Files:**
- Modify: `SkeldarAnim/maya_scenesetup/pending.py`
- Test: `tests/test_pending_override.py`

**Interfaces:**
- Produces: `pending.OVERRIDE = "override"`; it belongs to `TAB["weapon"]`, sorts
  after `AIM` in `_RANK`, and `phrase(OVERRIDE, (on, rot, pos, lag))` words it.

- [ ] **Step 1: Write the failing test**

```python
"""The Override pick key (2026-11-02): one more pick in the weapon's tab."""
import unittest

from maya_scenesetup import pending


class OverrideKey(unittest.TestCase):
    def test_it_belongs_to_the_weapon_tab(self):
        picks = {pending.OVERRIDE: (True, 1.0, 1.0, 80.0),
                 pending.CAMERA: "Main"}
        self.assertEqual(pending.of_tab(picks, "weapon"),
                         {pending.OVERRIDE: (True, 1.0, 1.0, 80.0)})

    def test_it_is_one_change(self):
        self.assertEqual(pending.count({pending.OVERRIDE: (True, 1.0, 1.0, 80.0)}), 1)

    def test_it_sorts_after_the_aim(self):
        text = pending.text({pending.OVERRIDE: (True, 1.0, 1.0, 80.0),
                             pending.AIM: True})
        self.assertLess(text.index("aim"), text.index("override"))

    def test_on_says_its_numbers(self):
        self.assertEqual(pending.phrase(pending.OVERRIDE, (True, 1.0, 0.5, 80.0)),
                         "the weapon's override on: 1 / 0.5 / 80 ms")

    def test_off_says_off(self):
        self.assertEqual(pending.phrase(pending.OVERRIDE, (False, 1.0, 1.0, 80.0)),
                         "the weapon's override off")
```

- [ ] **Step 2: Run it and watch it fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_pending_override -v`
Expected: FAIL - `module 'maya_scenesetup.pending' has no attribute 'OVERRIDE'`.

- [ ] **Step 3: Add the key**

In `pending.py`, beside `AIM`:

```python
AIM = "aim"
#  Override mode (2026-11-02): the chest carries the weapon. The value is
#  (on, rotation, position, lag ms) - the numbers are part of the pick, so a
#  knob turned while the mode stands is a change to apply.
OVERRIDE = "override"
```

then `TAB["weapon"] = (PARENT, AIM, OVERRIDE)`, `_RANK = (..., AIM, OVERRIDE,
CAMERA, ...)`, and in `phrase`:

```python
    if pick == OVERRIDE:
        on = value[0] if isinstance(value, (tuple, list)) else bool(value)
        if not on:
            return "the weapon's override off"
        return "the weapon's override on: %g / %g / %g ms" % tuple(value[1:4])
```

- [ ] **Step 4: Run it and watch it pass**

Run: the same command. Expected: 5 tests OK.

- [ ] **Step 5: Commit**

```bash
git add SkeldarAnim/maya_scenesetup/pending.py tests/test_pending_override.py
git commit -m "feat(connections): the override pick key"
```

---

### Task 2: `weaponoverride` - the formula

**Files:**
- Create: `SkeldarAnim/maya_scenesetup/weaponoverride.py`
- Test: `tests/test_weapon_override.py`

**Interfaces:**
- Produces:
  - `Settings = namedtuple("Settings", "rotation position lag")`, `DEFAULTS = Settings(1.0, 1.0, 80.0)`
  - `MARKER = "skeldarWeaponOverride"`, `BASE_PREFIX = "skeldarOverrideBase"`, `CHANNELS = fkik.TRANSLATE + fkik.ROTATE`
  - `parse(text) -> Settings | None`, `unparse(settings) -> str`
  - `lag_frames(ms, fps) -> float`
  - `rigid(matrix) -> om.MMatrix`
  - `scaled(ref, late, rotation, position) -> om.MMatrix`
  - `result(own, chest_now, chest_ref, g) -> om.MMatrix`
  - `sampled(mats, t) -> om.MMatrix`
  - `is_identity(settings) -> bool`
  - `pick_value(on, settings) -> tuple`, `state_value(standing, card) -> tuple`
  - `entered_message(label, keys, settings, carrier, held) -> str`, `left_message(label) -> str`

- [ ] **Step 1: Write the failing test**

`tests/test_weapon_override.py` - the formula's five claims, each a number:

```python
"""Override mode's formula (2026-11-02): the chest carries the weapon with a
strength per half and a lag. Run in mayapy - the formula is OpenMaya."""
import math
import unittest

import maya.api.OpenMaya as om

from maya_scenesetup import weaponoverride as wo


def xform(rotate, place):
    tm = om.MTransformationMatrix()
    tm.setRotation(om.MEulerRotation(*[math.radians(v) for v in rotate]))
    tm.setTranslation(om.MVector(*place), om.MSpace.kTransform)
    return tm.asMatrix()


def worst(a, b):
    return max(abs(a[i] - b[i]) for i in range(16))


class Formula(unittest.TestCase):
    def setUp(self):
        self.ref = wo.rigid(xform((0, 10, 0), (0, 100, 0)))
        self.late = wo.rigid(xform((5, 40, -3), (12, 104, 6)))
        self.own = xform((20, 0, 0), (30, 120, 10))

    def test_full_strength_is_the_parents_own_matrix(self):
        g = wo.scaled(self.ref, self.late, 1.0, 1.0)
        self.assertEqual(worst(g, self.ref.inverse() * self.late), 0.0)

    def test_the_identity_leaves_the_weapon_where_it_was(self):
        #  rotation 1, position 1, lag 0: the chest read at f is the chest at f
        g = wo.scaled(self.ref, self.late, 1.0, 1.0)
        out = wo.result(self.own, self.late, self.ref, g)
        self.assertLess(worst(out, self.own), 1e-12)

    def test_no_strength_freezes_the_chest_at_its_reference(self):
        g = wo.scaled(self.ref, self.late, 0.0, 0.0)
        out = wo.result(self.own, self.late, self.ref, g)
        want = om.MMatrix(self.own) * self.late.inverse() * self.ref
        self.assertLess(worst(out, want), 1e-12)

    def test_the_scaled_delta_keeps_no_scale(self):
        g = wo.scaled(self.ref, self.late, 0.5, 0.5)
        scale = om.MTransformationMatrix(g).scale(om.MSpace.kTransform)
        self.assertAlmostEqual(max(abs(v - 1.0) for v in scale), 0.0, places=12)

    def test_half_the_position_is_half_the_travel(self):
        half = wo.scaled(self.ref, self.late, 0.0, 0.5)
        full = wo.scaled(self.ref, self.late, 0.0, 1.0)
        self.assertAlmostEqual(half[13] * 2.0, full[13], places=9)

    def test_rigid_drops_a_chest_scale(self):
        tm = om.MTransformationMatrix(xform((0, 30, 0), (1, 2, 3)))
        tm.setScale([2.0, 2.0, 2.0], om.MSpace.kTransform)
        out = wo.rigid(tm.asMatrix())
        self.assertAlmostEqual(
            max(abs(v - 1.0) for v in
                om.MTransformationMatrix(out).scale(om.MSpace.kTransform)), 0.0, places=12)
        self.assertEqual([out[12], out[13], out[14]], [1.0, 2.0, 3.0])


class Lag(unittest.TestCase):
    def test_ms_into_frames(self):
        self.assertAlmostEqual(wo.lag_frames(100.0, 30.0), 3.0)
        self.assertAlmostEqual(wo.lag_frames(100.0, 24.0), 2.4)

    def test_a_whole_frame_is_that_frames_matrix(self):
        mats = {1: xform((0, 0, 0), (1, 0, 0)), 2: xform((0, 0, 0), (2, 0, 0))}
        self.assertEqual(wo.sampled(mats, 2)[12], 2.0)

    def test_a_fraction_lerps_the_place(self):
        mats = {1: xform((0, 0, 0), (1, 0, 0)), 2: xform((0, 0, 0), (3, 0, 0))}
        self.assertAlmostEqual(wo.sampled(mats, 1.5)[12], 2.0, places=9)

    def test_a_fraction_slerps_the_turn(self):
        mats = {1: xform((0, 0, 0), (0, 0, 0)), 2: xform((0, 90, 0), (0, 0, 0))}
        middle = om.MTransformationMatrix(wo.sampled(mats, 1.5)).rotation()
        self.assertAlmostEqual(math.degrees(middle.y), 45.0, places=6)

    def test_before_the_first_frame_it_holds(self):
        mats = {5: xform((0, 0, 0), (7, 0, 0)), 6: xform((0, 0, 0), (9, 0, 0))}
        self.assertEqual(wo.sampled(mats, 2.0)[12], 7.0)


class Values(unittest.TestCase):
    def test_the_identity_is_full_strength_and_no_lag(self):
        self.assertTrue(wo.is_identity(wo.Settings(1.0, 1.0, 0.0)))
        self.assertFalse(wo.is_identity(wo.Settings(1.0, 1.0, 80.0)))
        self.assertFalse(wo.is_identity(wo.Settings(0.5, 1.0, 0.0)))

    def test_the_settings_round_trip_through_their_string(self):
        s = wo.Settings(0.5, 0.25, 120.0)
        self.assertEqual(wo.parse(wo.unparse(s)), s)

    def test_a_broken_string_is_no_settings(self):
        self.assertIsNone(wo.parse(""))
        self.assertIsNone(wo.parse("1 1"))
        self.assertIsNone(wo.parse("on 1 80"))

    def test_a_turned_knob_is_a_pick_while_the_mode_stands(self):
        card = wo.Settings(1.0, 1.0, 160.0)
        standing = wo.Settings(1.0, 1.0, 80.0)
        self.assertNotEqual(wo.pick_value(True, card),
                            wo.state_value(standing, card))

    def test_a_turned_knob_is_no_pick_while_the_mode_is_off(self):
        card = wo.Settings(1.0, 1.0, 160.0)
        self.assertEqual(wo.pick_value(False, card), wo.state_value(None, card))
```

- [ ] **Step 2: Run it and watch it fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_weapon_override -v`
Expected: FAIL - `No module named 'maya_scenesetup.weaponoverride'`.

- [ ] **Step 3: Write the module's pure half**

`SkeldarAnim/maya_scenesetup/weaponoverride.py` - the docstring names the
animator's ask and the spec, then:

```python
import math
from collections import namedtuple

import maya.api.OpenMaya as om
import maya.cmds as cmds

import maya_timewarp
from maya_scenesetup import aimcore
from maya_scenesetup import fkik

MARKER = "skeldarWeaponOverride"      # on the weapon: "rotation position lag"
BASE_PREFIX = "skeldarOverrideBase"   # + Channel: the weapon's own curve, parked
CHANNELS = fkik.TRANSLATE + fkik.ROTATE
CHEST = "spine_03"

Settings = namedtuple("Settings", "rotation position lag")
DEFAULTS = Settings(1.0, 1.0, 80.0)
IDENTITY = Settings(1.0, 1.0, 0.0)


def parse(text):
    """`Settings` from the string kept on the weapon, or None (nothing, or no
    three numbers). Pure."""
    parts = str(text or "").split()
    if len(parts) != 3:
        return None
    try:
        return Settings(*[float(v) for v in parts])
    except ValueError:
        return None


def unparse(settings):
    return " ".join("%.12g" % float(v) for v in settings)


def is_identity(settings):
    """Full strength and no lag: the mode changes nothing. Pure."""
    return (abs(settings.rotation - 1.0) < 1e-9 and abs(settings.position - 1.0) < 1e-9
            and abs(settings.lag) < 1e-9)


def lag_frames(ms, fps):
    return float(ms) * float(fps) / 1000.0


def rigid(matrix):
    """`matrix` without its scale or shear - its rotation and its place. The chest's
    scale is not inherited: a rig's scale chain leaves 4e-7 on a bone and a partial
    scale means nothing. Pure (OpenMaya)."""
    m = om.MMatrix(matrix)
    out = list(om.MMatrix(om.MTransformationMatrix(m).rotation(asQuaternion=True).asMatrix()))
    return om.MMatrix(out[0:12] + [m[12], m[13], m[14], 1.0])


def scaled(ref, late, rotation, position):
    """`G`: the chest's motion from `ref` to `late` (world matrices), its turn slerped
    from identity by `rotation` and its travel scaled by `position`, both about the
    chest's own pivot - the translation of a bare `ref⁻¹ · late` carries the lever to
    the world origin, and scaling that would throw the weapon off the body. Row
    vectors: a world point p maps to p · G. At full strength it IS `ref⁻¹ · late`,
    exactly. Pure (OpenMaya)."""
    ref, late = om.MMatrix(ref), om.MMatrix(late)
    if rotation == 1.0 and position == 1.0:
        return ref.inverse() * late
    turn = om.MQuaternion.slerp(
        om.MQuaternion(),
        om.MTransformationMatrix(ref).rotation(asQuaternion=True).inverse() *
        om.MTransformationMatrix(late).rotation(asQuaternion=True), float(rotation))
    pivot = [ref[12], ref[13], ref[14]]
    travel = [(late[12 + i] - pivot[i]) * float(position) for i in range(3)]
    return (_translate([-v for v in pivot]) * om.MMatrix(turn.asMatrix()) *
            _translate([pivot[i] + travel[i] for i in range(3)]))


def _translate(v):
    return om.MMatrix([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, v[0], v[1], v[2], 1])


def result(own, chest_now, chest_ref, g):
    """The weapon's world under the mode: `W = W_own · C(f)⁻¹ · C(ref) · G` - its own
    pose relative to the chest kept, the chest's own motion put back scaled and late.
    Pure (OpenMaya)."""
    return (om.MMatrix(own) * om.MMatrix(chest_now).inverse() *
            om.MMatrix(chest_ref) * om.MMatrix(g))


def sampled(mats, t):
    """The world matrix at the fractional frame `t` from `mats` ({frame: matrix}): its
    turn slerped and its place lerped between the two whole frames around it, clamped
    to the frames it holds. Pure (OpenMaya)."""
    frames = sorted(mats)
    if not frames:
        return om.MMatrix()
    if t <= frames[0]:
        return om.MMatrix(mats[frames[0]])
    if t >= frames[-1]:
        return om.MMatrix(mats[frames[-1]])
    low = max(f for f in frames if f <= t)
    high = min(f for f in frames if f >= t)
    if high == low:
        return om.MMatrix(mats[low])
    share = (t - low) / float(high - low)
    a, b = om.MMatrix(mats[low]), om.MMatrix(mats[high])
    turn = om.MQuaternion.slerp(om.MTransformationMatrix(a).rotation(asQuaternion=True),
                                om.MTransformationMatrix(b).rotation(asQuaternion=True),
                                share)
    place = [a[12 + i] + (b[12 + i] - a[12 + i]) * share for i in range(3)]
    out = list(om.MMatrix(turn.asMatrix()))
    return om.MMatrix(out[0:12] + place + [1.0])


def pick_value(on, settings):
    """A pick's value: what the press would make stand. Pure."""
    return (bool(on),) + tuple(float(v) for v in settings)


def state_value(standing, card):
    """What the scene shows: the settings standing, else off with the CARD's own
    numbers - so a knob turned with the mode off is no pick, and one turned with it
    on is. Pure."""
    return pick_value(True, standing) if standing else pick_value(False, card)
```

- [ ] **Step 4: Run it and watch it pass**

Run: the same command. Expected: 17 tests OK. If `test_half_the_position_is_half_the_travel` fails, the pivot decomposition is wrong - print `scaled(ref, late, 0, 1)[12:15]` against `late[12:15] - ref[12:15]`.

- [ ] **Step 5: Commit**

```bash
git add SkeldarAnim/maya_scenesetup/weaponoverride.py tests/test_weapon_override.py
git commit -m "feat(connections): the override formula"
```

---

### Task 3: `weaponoverride` - the scene half

**Files:**
- Modify: `SkeldarAnim/maya_scenesetup/weaponoverride.py`
- Test: `tests/test_weapon_override.py` (add classes; the fake `cmds` pattern of
  `tests/test_scenesetup_weaponaim.py`)

**Interfaces:**
- Consumes: Task 2's pure half.
- Produces:
  - `state(weapon) -> Settings | None`, `is_overridden(weapon) -> bool`
  - `chest_of(rig) -> str | None`
  - `refusal(weapon, chest) -> str`
  - `park(weapon)`, `unpark(weapon)`, `drop(weapon)`
  - `enter(weapon, chest, settings) -> str`, `leave(weapon) -> str`
  - words: `NO_WEAPON`, `NO_CHEST`, `AIMED`, `NOT_OVERRIDDEN`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_weapon_override.py` - the halves a fake `cmds` can prove
(the parked base, the state, the refusals, the words). `enter` / `leave` over a
real rig belong to the verify script.

```python
class FakeCmds(object):
    """Just enough of cmds for the parked base: attributes, connections, values."""

    def __init__(self):
        self.attrs = {}          # "node.attr" -> value
        self.added = []          # (node, longName, kind)
        self.connections = {}    # "node.attr" -> "curve.output"
        self.cut = []

    def objExists(self, path):
        return path in self.attrs or "." not in path

    def attributeQuery(self, name, node=None, exists=False):
        return (node + "." + name) in self.attrs

    def addAttr(self, node, longName=None, dataType=None, attributeType=None, keyable=None):
        self.added.append((node, longName, dataType or attributeType))
        self.attrs[node + "." + longName] = "" if dataType == "string" else 0.0

    def deleteAttr(self, plug):
        self.attrs.pop(plug, None)

    def getAttr(self, plug, **kwargs):
        if kwargs.get("lock"):
            return False
        return self.attrs.get(plug, 0.0)

    def setAttr(self, plug, *values, **kwargs):
        self.attrs[plug] = values[0]

    def listConnections(self, plug, **kwargs):
        found = self.connections.get(plug)
        return [found] if found else []

    def connectAttr(self, source, target, force=False):
        self.connections[target] = source

    def disconnectAttr(self, source, target):
        self.connections.pop(target, None)

    def cutKey(self, plug, **kwargs):
        self.cut.append(plug)
        self.connections.pop(plug, None)

    def ls(self, *args, **kwargs):
        return [args[0]] if args and args[0] else []


class ParkedBase(unittest.TestCase):
    def setUp(self):
        self.fake = FakeCmds()
        self.weapon = "|Sword"
        for channel in wo.CHANNELS:
            self.fake.attrs[self.weapon + "." + channel] = 0.0
        #  a curve on rotateY, a plain value on translateX
        self.fake.connections[self.weapon + ".rotateY"] = "swingCurve.output"
        self.fake.attrs[self.weapon + ".translateX"] = 7.5
        self.old, wo.cmds = wo.cmds, self.fake

    def tearDown(self):
        wo.cmds = self.old

    def test_park_takes_the_curve_off_the_weapon(self):
        wo.park(self.weapon)
        self.assertNotIn(self.weapon + ".rotateY", self.fake.connections)
        self.assertEqual(self.fake.connections[self.weapon + ".skeldarOverrideBaseRotateY"],
                         "swingCurve.output")

    def test_park_copies_a_plain_value(self):
        wo.park(self.weapon)
        self.assertEqual(self.fake.attrs[self.weapon + ".skeldarOverrideBaseTranslateX"], 7.5)

    def test_a_rotate_is_parked_as_an_angle(self):
        wo.park(self.weapon)
        kinds = dict((name, kind) for _n, name, kind in self.fake.added)
        self.assertEqual(kinds["skeldarOverrideBaseRotateY"], "doubleAngle")
        self.assertEqual(kinds["skeldarOverrideBaseTranslateX"], "doubleLinear")

    def test_unpark_puts_the_curve_back_and_leaves_nothing(self):
        wo.park(self.weapon)
        wo.unpark(self.weapon)
        self.assertEqual(self.fake.connections[self.weapon + ".rotateY"], "swingCurve.output")
        self.assertEqual(self.fake.attrs[self.weapon + ".translateX"], 7.5)
        self.assertNotIn(self.weapon + ".skeldarOverrideBaseRotateY", self.fake.attrs)

    def test_unpark_cuts_the_overrides_own_curve_first(self):
        wo.park(self.weapon)
        self.fake.connections[self.weapon + ".rotateY"] = "overrideCurve.output"
        wo.unpark(self.weapon)
        self.assertIn(self.weapon + ".rotateY", self.fake.cut)
        self.assertEqual(self.fake.connections[self.weapon + ".rotateY"], "swingCurve.output")


class State(unittest.TestCase):
    def setUp(self):
        self.fake = FakeCmds()
        self.weapon = "|Sword"
        self.old, wo.cmds = wo.cmds, self.fake

    def tearDown(self):
        wo.cmds = self.old

    def test_no_marker_is_no_state(self):
        self.assertIsNone(wo.state(self.weapon))
        self.assertFalse(wo.is_overridden(self.weapon))

    def test_the_marker_reads_back_its_numbers(self):
        self.fake.attrs[self.weapon + "." + wo.MARKER] = "0.5 0.25 120"
        self.assertEqual(wo.state(self.weapon), wo.Settings(0.5, 0.25, 120.0))
        self.assertTrue(wo.is_overridden(self.weapon))

    def test_a_broken_marker_is_no_state(self):
        self.fake.attrs[self.weapon + "." + wo.MARKER] = "oops"
        self.assertIsNone(wo.state(self.weapon))


class Words(unittest.TestCase):
    def test_entered_names_the_keys_and_the_chest(self):
        line = wo.entered_message("Sword", [0.0, 12.0, 24.0],
                                  wo.Settings(1.0, 1.0, 80.0), "spine_03", None)
        self.assertIn("3 keys", line)
        self.assertIn("spine_03", line)
        self.assertIn("80", line)

    def test_entered_says_when_the_numbers_change_nothing(self):
        line = wo.entered_message("Sword", [0.0], wo.IDENTITY, "spine_03", None)
        self.assertIn("the identity", line)

    def test_entered_warns_about_a_held_weapon(self):
        line = wo.entered_message("Sword", [0.0], wo.Settings(1.0, 1.0, 80.0),
                                  "spine_03", "R")
        self.assertIn("slides in the grip", line)

    def test_left_names_the_weapon(self):
        self.assertIn("Sword", wo.left_message("Sword"))
```

- [ ] **Step 2: Run them and watch them fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_weapon_override -v`
Expected: FAIL - `module ... has no attribute 'park'`.

- [ ] **Step 3: Write the scene half**

Append to `weaponoverride.py`. `park` / `unpark` follow `bonedrive.park` word
for word (doubleLinear / doubleAngle so no `unitConversion` is spliced in -
trap 42):

```python
NO_WEAPON = "no weapon in the scene - Inventory > Equip first"
NO_CHEST = "%s has no %s bone - Override needs the chest"
AIMED = "%s is in Aim Mode - it writes the rotation too: Default first"
NOT_OVERRIDDEN = "%s is not in Override mode"
IDENTITY_NOTE = "the identity (nothing changed) - dial the Lag or drop a strength"
HELD_NOTE = "in the %s hand - it slides in the grip by the lag; Weapon -> World with 2H keeps the hands on it"


def base_attr(channel):
    return BASE_PREFIX + channel[0].upper() + channel[1:]


def state(weapon):
    """The settings standing on `weapon`, or None."""
    if not weapon or not cmds.objExists(weapon) or not cmds.attributeQuery(
            MARKER, node=weapon, exists=True):
        return None
    return parse(cmds.getAttr(weapon + "." + MARKER))


def is_overridden(weapon):
    return state(weapon) is not None


def park(weapon):
    """The weapon's own curves off it and onto our attributes - the base a re-write
    reads and Default puts back; a channel with no curve keeps its value."""
    drop(weapon)
    for channel in CHANNELS:
        attr = base_attr(channel)
        kind = "doubleLinear" if channel.startswith("translate") else "doubleAngle"
        cmds.addAttr(weapon, longName=attr, attributeType=kind, keyable=False)
        plug = weapon + "." + channel
        curves = cmds.listConnections(plug, source=True, destination=False,
                                      type="animCurve", plugs=True) or []
        if curves:
            cmds.connectAttr(curves[0], weapon + "." + attr)
            cmds.disconnectAttr(curves[0], plug)
        else:
            cmds.setAttr(weapon + "." + attr, cmds.getAttr(plug))


def unpark(weapon):
    """The base back on the weapon, exactly: the override's own curve cut first (an
    emptied curve node goes with it - trap 210), then the parked curve reconnected or
    the plain value written. False when nothing was parked."""
    if not cmds.attributeQuery(base_attr(CHANNELS[0]), node=weapon, exists=True):
        return False
    for channel in CHANNELS:
        attr = weapon + "." + base_attr(channel)
        if not cmds.objExists(attr):
            continue
        plug = weapon + "." + channel
        cmds.cutKey(plug, clear=True)
        curves = cmds.listConnections(attr, source=True, destination=False,
                                      plugs=True) or []
        if curves:
            cmds.connectAttr(curves[0], plug, force=True)
            cmds.disconnectAttr(curves[0], attr)
        else:
            try:
                cmds.setAttr(plug, cmds.getAttr(attr))
            except RuntimeError:
                pass
    drop(weapon)
    return True


def drop(weapon):
    """Our attributes off `weapon`, the curves still parked on them deleted."""
    for channel in CHANNELS:
        attr = weapon + "." + base_attr(channel)
        if cmds.objExists(attr):
            for curve in cmds.listConnections(attr, source=True, destination=False) or []:
                if cmds.objExists(curve):
                    cmds.delete(curve)
            cmds.deleteAttr(attr)
    if cmds.attributeQuery(MARKER, node=weapon, exists=True):
        cmds.deleteAttr(weapon + "." + MARKER)
```

then the words, the chest, the refusal and the two presses:

```python
def entered_message(label, keys, settings, carrier, held):
    parts = ["%s on %s: %g / %g / %g ms" % (label, carrier, settings.rotation,
                                            settings.position, settings.lag)]
    parts.append("%d key%s" % (len(keys), "" if len(keys) == 1 else "s") if keys
                 else "no keys of its own: set at the current frame")
    if is_identity(settings):
        parts.append(IDENTITY_NOTE)
    if held:
        parts.append(HELD_NOTE % ("right" if held == "R" else "left"))
    return " - ".join(parts[:1]) + " (" + ", ".join(parts[1:]) + ")"


def left_message(label):
    return "%s back to Default - its own animation restored" % label


def chest_of(rig):
    """The rig's chest bone (`spine_03`), long path, or None. In 1P the chest control
    drives that bone through Tools' knot, so reading the bone reads the control's
    motion - one road for both modes."""
    from maya_scenesetup import skeleton
    root = getattr(rig, "skeleton_root", None) if rig is not None else None
    return skeleton.resolve_bone(root, CHEST) if root else None


def refusal(weapon, chest):
    """'' or why `weapon` cannot go into Override mode."""
    from maya_scenesetup import weaponaim
    if not weapon or not cmds.objExists(weapon):
        return NO_WEAPON
    if weaponaim.is_aimed(weapon):
        return AIMED % aimcore.leaf(weapon)
    if not chest:
        return NO_CHEST % (aimcore.leaf(weapon), CHEST)
    label = aimcore.leaf(weapon)
    for channel in CHANNELS:
        plug = weapon + "." + channel
        if cmds.getAttr(plug, lock=True):
            return "%s.%s is locked" % (label, channel)
        if fkik._layered(plug):
            return "%s.%s is on animation layers - bake its layers first" % (label, channel)
        driver = fkik._foreign(plug)
        if driver:
            return "%s.%s is driven by %s" % (label, channel, driver)
    return ""
```

- [ ] **Step 4: Run them and watch them pass**

Run: the same command. Expected: 29 tests OK.

- [ ] **Step 5: Write `enter` and `leave`**

The engine. Read first, park second, write third - the walk needs the base
connected.

```python
def _fps():
    from maya_poselib import look
    return look.fps_of(cmds.currentUnit(query=True, time=True))


def span_for(weapon, chest):
    """(start, end, False): the playback range ∪ the weapon's keys ∪ the chest's, whole
    frames."""
    start = cmds.playbackOptions(query=True, min=True)
    end = cmds.playbackOptions(query=True, max=True)
    keys = []
    for node in (weapon, chest):
        keys.extend(cmds.keyframe(node, query=True, timeChange=True) or [])
    if keys:
        start, end = min(start, min(keys)), max(end, max(keys))
    return (int(math.floor(start)), int(math.ceil(end)), False)


def _read(weapon, chest, frames):
    """{frame: (the weapon's world, the chest's rigid world, the weapon's parent
    inverse)} over `frames` - one walk, the time put back."""
    out = {}
    with maya_timewarp.unwarped():
        fkik._suspend(True)
        try:
            now = cmds.currentTime(query=True)
            try:
                for frame in frames:
                    fkik._goto(frame)
                    out[frame] = (aimcore.world(weapon), rigid(aimcore.world(chest)),
                                  om.MMatrix(cmds.getAttr(weapon + ".parentInverseMatrix[0]")))
            finally:
                fkik._goto(now)
        finally:
            fkik._suspend(False)
    return out


def wanted(read, settings, fps):
    """{frame: the weapon's world under the mode} over every frame `read` holds. The
    chest's time is clamped to the first frame, so that frame is bit-exact and the lag
    eases in. Pure but for `read`."""
    frames = sorted(read)
    chests = dict((f, read[f][1]) for f in frames)
    ref = chests[frames[0]]
    lag = lag_frames(settings.lag, fps)
    out = {}
    for frame in frames:
        late = sampled(chests, max(frames[0], frame - lag))
        g = scaled(ref, late, settings.rotation, settings.position)
        out[frame] = result(read[frame][0], chests[frame], ref, g)
    return out


def enter(weapon, chest, settings):
    """Override mode on `weapon` (the caller holds the undo chunk and autoKey): the
    weapon's own track read, parked, and its channels keyed to what the chest carries.
    The status line."""
    from maya_poselib import helpers
    label = aimcore.leaf(weapon)
    window = span_for(weapon, chest)
    frames = list(range(window[0], window[1] + 1))
    read = _read(weapon, chest, frames)
    want = wanted(read, settings, _fps())
    attrs = helpers._attrs(weapon)
    previous = [cmds.getAttr(weapon + "." + ch) for ch in fkik.ROTATE]
    values = {}
    for frame in frames:
        rotate, translate = helpers.driver_channels(want[frame] * read[frame][2], attrs,
                                                    previous)
        values[frame] = tuple(translate) + tuple(rotate)
        previous = list(rotate)
    sample, keys, tangents = fkik.own_keys([weapon, chest], [], window)
    if not keys:
        sample = [min(frames, key=lambda f: abs(f - cmds.currentTime(query=True)))]
    unpark(weapon)                       # a re-write: the base back before it is parked again
    park(weapon)
    cmds.addAttr(weapon, longName=MARKER, dataType="string")
    cmds.setAttr(weapon + "." + MARKER, unparse(settings), type="string")
    for index, channel in enumerate(CHANNELS):
        fkik._write(weapon + "." + channel, sample,
                    [values[f][index] for f in sample], window, False, tangents)
    added = _fill(weapon, want, set(sample), frames)
    held = _held(weapon)
    line = entered_message(label, keys, settings, aimcore.leaf(chest), held)
    return line + (" + %d frame(s) between the keys" % added if added else "")


def _fill(weapon, want, keyed, frames):
    """Keys added on the frames between the keys where the result stands off `want`
    (`aimcore.track_off`: 0.1 deg / 0.01 cm), until none does. How many."""
    from maya_poselib import helpers
    attrs = helpers._attrs(weapon)

    def missed(todo):
        return aimcore.track_off(want, aimcore.walk(todo, lambda: aimcore.world(weapon)))

    def key(frame):
        local = om.MMatrix(want[frame]) * om.MMatrix(
            cmds.getAttr(weapon + ".parentInverseMatrix[0]", time=frame))
        rotate, translate = helpers.driver_channels(local, attrs,
                                                   [cmds.getAttr(weapon + "." + ch, time=frame)
                                                    for ch in fkik.ROTATE])
        for value, channel in zip(tuple(translate) + tuple(rotate), CHANNELS):
            cmds.setKeyframe(weapon, attribute=channel, time=frame, value=value)

    with maya_timewarp.unwarped():
        fkik._suspend(True)
        try:
            return aimcore.fill_passes([f for f in frames if f not in keyed], missed, key)
        finally:
            fkik._suspend(False)


def _held(weapon):
    """The side of the hand holding `weapon`, or None."""
    from maya_scenesetup import weaponspace
    hand = weaponspace.holding_hand(weapon)
    if not hand:
        return None
    leaf = aimcore.leaf(hand)
    return "R" if leaf.endswith("_r") else ("L" if leaf.endswith("_l") else None)


def leave(weapon):
    """Default on `weapon`: its own animation back, exactly. The status line."""
    label = aimcore.leaf(weapon)
    if state(weapon) is None:
        return NOT_OVERRIDDEN % label
    if not unpark(weapon):
        drop(weapon)
    return left_message(label)
```

- [ ] **Step 6: Run the whole file's tests again**

Run: the same command. Expected: 29 tests OK (the new code is not unit-tested -
it is the verify script's, Task 6).

- [ ] **Step 7: Commit**

```bash
git add SkeldarAnim/maya_scenesetup/weaponoverride.py tests/test_weapon_override.py
git commit -m "feat(connections): override mode - the parked base and the two presses"
```

---

### Task 4: the `2H` chip

**Files:**
- Modify: `SkeldarAnim/maya_scenesetup/connections.py`
- Test: `tests/test_connections_two_hands.py`

**Interfaces:**
- Produces: `connections.two_hands_state(scheme) -> bool`,
  `connections.two_hands_picks(scheme, on) -> {row: choice}`,
  `TWO_HANDS_CHIP = "skeldarConnectionsTwoHands"`, `_press_two_hands`.

- [ ] **Step 1: Write the failing test**

```python
"""2H Weapon (2026-11-02): one chip binds both hands to the weapon.

«намертво» means the hand FOLLOWS the weapon (the animator's own words), with
today's proxy road kept - so the chip is a shortcut for the two hand rows'
picks and nothing else.
"""
import unittest

from maya_scenesetup import connections as con


class TwoHandsState(unittest.TestCase):
    def test_both_following_is_2h(self):
        self.assertTrue(con.two_hands_state({"R": con.FOLLOWS, "L": con.FOLLOWS}))

    def test_one_holding_and_one_following_is_2h(self):
        self.assertTrue(con.two_hands_state({"R": con.HOLDS, "L": con.FOLLOWS}))

    def test_a_free_hand_is_not(self):
        self.assertFalse(con.two_hands_state({"R": con.HOLDS, "L": None}))
        self.assertFalse(con.two_hands_state({"R": None, "L": None}))


class TwoHandsPicks(unittest.TestCase):
    def test_in_world_both_hands_go_on_it(self):
        self.assertEqual(con.two_hands_picks({"R": None, "L": None}, True),
                         {"R": con.WEAPON, "L": con.WEAPON})

    def test_a_holding_hand_is_left_holding(self):
        #  it travels with the weapon already, and releasing it would move the weapon
        self.assertEqual(con.two_hands_picks({"R": con.HOLDS, "L": None}, True),
                         {"L": con.WEAPON})

    def test_nothing_to_ask_when_both_are_bound(self):
        self.assertEqual(con.two_hands_picks({"R": con.HOLDS, "L": con.FOLLOWS}, True), {})

    def test_unticking_frees_the_followers_only(self):
        self.assertEqual(con.two_hands_picks({"R": con.HOLDS, "L": con.FOLLOWS}, False),
                         {"L": con.FREE})

    def test_unticking_frees_both_followers(self):
        self.assertEqual(con.two_hands_picks({"R": con.FOLLOWS, "L": con.FOLLOWS}, False),
                         {"R": con.FREE, "L": con.FREE})

    def test_the_weapon_row_is_never_touched(self):
        for on in (True, False):
            for scheme in ({"R": con.HOLDS, "L": None}, {"R": None, "L": con.FOLLOWS}):
                self.assertNotIn("W", con.two_hands_picks(scheme, on))
```

- [ ] **Step 2: Run it and watch it fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_connections_two_hands -v`
Expected: FAIL - `module ... has no attribute 'two_hands_state'`.

- [ ] **Step 3: Write the two pure functions**

In `connections.py`, in the pure section after `wanted_for_row`:

```python
def two_hands_state(scheme):
    """Whether both hands are bound to the weapon - a hand that HOLDS it counts: it
    travels with the weapon by construction. The 2H chip's lit state. Pure."""
    return all(scheme.get(side) in (HOLDS, FOLLOWS) for side in SIDES)


def two_hands_picks(scheme, on):
    """{row: choice} the 2H chip records over `scheme`, the two hand rows only - the
    chip never moves the weapon («оружие остаётся там, где стоит»), so a hand that
    holds it is left holding and, unticked, only the followers are freed. Pure."""
    out = {}
    for side in SIDES:
        standing = scheme.get(side)
        if on and standing is None:
            out[side] = WEAPON
        elif not on and standing == FOLLOWS:
            out[side] = FREE
    return out
```

- [ ] **Step 4: Run it and watch it pass**

Run: the same command. Expected: 9 tests OK.

- [ ] **Step 5: Add the chip to the card**

The constant beside `W_BOX`:

```python
#  2H (2026-11-02): one chip for a two-handed grip - it records the two hand rows'
#  picks, so the rows light up and Apply all counts them. No new state, no new bake.
TWO_HANDS_CHIP = "skeldarConnectionsTwoHands"
TWO_HANDS_TIP = ("Both hands bound to the weapon: a hand that holds it travels with it "
                 "already, so the other goes onto it. Picked, not baked - press a row's "
                 "check, or Apply all.")
```

the press, beside `_press_row`:

```python
def _press_two_hands(value, *_args):
    """The 2H chip: the two hand rows' picks (2026-11-02). A PICK."""
    if _MENU_QUIET["on"]:
        return None
    rig, refusal = maya_rigs.current_rig()
    if rig is None:
        return _status(refusal)
    scheme = read_scheme(rig)
    chosen = picks(rig)
    menus_now = menus_from_scheme(scheme)
    for row, choice in two_hands_picks(scheme, bool(value)).items():
        chosen = pending.record(chosen, pending.parent_key(row), choice,
                                menus_now.get(row))
    chosen = remember(rig, chosen)
    _set_menus(wanted_menus(rig), chosen)
    return _status(_picked_text(chosen) or NOTHING_PICKED)
```

the chip in `build_panel`, right after the three parent rows and before
`Apply all`:

```python
    hubstyle.mark(cmds.checkBox(
        TWO_HANDS_CHIP, label="2H", value=False, annotation=TWO_HANDS_TIP,
        changeCommand=_press_two_hands), "chip")
```

and the painting, at the end of `_set_menus` (which every refresh calls):

```python
    if cmds.control(TWO_HANDS_CHIP, exists=True):
        scheme = read_scheme(rig) if rig is not None else {}
        standing = two_hands_state(scheme)
        _MENU_QUIET["on"] = True
        try:
            cmds.checkBox(TWO_HANDS_CHIP, edit=True, value=standing)
        finally:
            _MENU_QUIET["on"] = False
        asked = two_hands_picks(scheme, not standing)
        wants = asked and all(
            chosen.get(pending.parent_key(row)) == choice
            for row, choice in asked.items())
        _light(TWO_HANDS_CHIP, "want" if wants else "")
```

(read `_set_menus`'s own signature first - it takes `(values, chosen=None)` and
already holds `_MENU_QUIET`; the rig comes from `maya_rigs.current_rig()` there,
as `_set_aim` reads it.)

- [ ] **Step 6: Add the card test**

Append to `tests/test_connections_two_hands.py` a build test on the card's fake
`cmds` (copy the fixture of `tests/test_scenesetup_connections_pending.py` -
read it first and follow it exactly): the chip exists, is marked `chip`, stands
after the `Weapon` row and before `Apply all`, and its `changeCommand` is
`_press_two_hands`.

- [ ] **Step 7: Run the card's whole suite**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_connections_two_hands tests.test_scenesetup_connections_pending tests.test_scenesetup_connections -v`
Expected: every test OK.

- [ ] **Step 8: Commit**

```bash
git add SkeldarAnim/maya_scenesetup/connections.py tests/test_connections_two_hands.py
git commit -m "feat(connections): the 2H chip binds both hands in one press"
```

---

### Task 5: the Override row, its pick and its press

**Files:**
- Modify: `SkeldarAnim/maya_scenesetup/connections.py`
- Test: `tests/test_connections_override_row.py`

**Interfaces:**
- Consumes: `weaponoverride` (Tasks 2-3), `pending.OVERRIDE` (Task 1).
- Produces: `override_mode(rig=None, weapon=None, settings=None) -> str`,
  `card_settings() -> wo.Settings`, `_press_override_pick`,
  `_press_override_apply`, the `apply_weapon` leg, the `apply()` dance.

- [ ] **Step 1: Write the failing test**

`tests/test_connections_override_row.py`, on the card's fake `cmds`:

```python
"""The Override row in the Weapon tab (2026-11-02): a chip, three numbers, a check."""
import unittest

from maya_scenesetup import connections as con
from maya_scenesetup import pending
from maya_scenesetup import weaponoverride as wo


class CardSettings(unittest.TestCase):
    """The three fields while the card stands, else the optionVars, else the
    defaults - so a hotkey row works with the card closed (the Tools card's rule)."""

    def test_the_defaults_without_a_card(self):
        self.assertEqual(con.card_settings(), wo.DEFAULTS)


class TheRow(unittest.TestCase):
    def test_the_section_is_after_the_aim(self):
        order = con.build_order()          # the control names in the order built
        self.assertLess(order.index(con.AIM_APPLY), order.index(con.OVERRIDE_CHIP))

    def test_the_tabs_one_orange_is_still_apply_all(self):
        self.assertEqual(con.primary_controls("weapon"), [con.APPLY_ALL["weapon"]])

    def test_the_check_is_a_tool_not_a_primary(self):
        self.assertIn("tool", con.marks_of(con.OVERRIDE_APPLY))


class ThePick(unittest.TestCase):
    def test_a_knob_turned_with_the_mode_off_is_no_pick(self):
        card = wo.Settings(1.0, 1.0, 160.0)
        self.assertEqual(wo.pick_value(False, card), wo.state_value(None, card))

    def test_the_pick_carries_the_numbers(self):
        value = wo.pick_value(True, wo.Settings(0.5, 1.0, 40.0))
        self.assertEqual(value, (True, 0.5, 1.0, 40.0))
        self.assertIn("0.5", pending.phrase(pending.OVERRIDE, value))
```

The three `TheRow` tests want small read-only helpers in `connections.py`
(`build_order`, `primary_controls`, `marks_of`) - if the card's existing test
fixture already offers an equivalent (read `tests/test_scenesetup_connections_pending.py`
first), use that instead of adding new seams, and keep the assertions.

- [ ] **Step 2: Run it and watch it fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_connections_override_row -v`
Expected: FAIL - `module ... has no attribute 'card_settings'`.

- [ ] **Step 3: The constants, the row and the painting**

Constants beside the aim's:

```python
#  Override mode (2026-11-02): the chest carries the weapon, with a strength per half
#  and a lag in ms. A pick like every other; the section's check bakes it.
OVERRIDE_CHIP = "skeldarConnectionsOverride"
OVERRIDE_NAMES = "skeldarConnectionsOverrideNames"
OVERRIDE_FIELDS = "skeldarConnectionsOverrideFields"
OVERRIDE_FIELD = {"rotation": "skeldarConnectionsOverrideRot",
                  "position": "skeldarConnectionsOverridePos",
                  "lag": "skeldarConnectionsOverrideLag"}
OVERRIDE_VAR = {"rotation": "skeldarOverrideRotation",
                "position": "skeldarOverridePosition",
                "lag": "skeldarOverrideLag"}
OVERRIDE_APPLY = "skeldarConnectionsOverrideApply"
OVERRIDE_LABEL = {"rotation": "Rotation", "position": "Position", "lag": "Lag, ms"}
OVERRIDE_TIPS = {
    "chip": "The chest carries the weapon: its own pose relative to the chest kept, the "
            "chest's motion put back scaled and late. Picked, not baked.",
    "rotation": "How much of the chest's TURN the weapon inherits. 1 as a parent would, "
                "0 not at all.",
    "position": "How much of the chest's TRAVEL the weapon inherits.",
    "lag": "How late the weapon takes the chest's pose, in milliseconds - the overlap. "
           "1 / 1 / 0 is the identity.",
}
```

`CAPTION["override"] = "skeldarConnectionsCapOverride"`.

The section in `build_panel`, after the aim row and before the weapon tab's
`cmds.setParent("..")`:

```python
    _caption("override", "Override")
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1,
                   columnAttach=[(1, "both", 0), (2, "right", 0)])
    hubstyle.mark(cmds.checkBox(
        OVERRIDE_CHIP, label="Override", value=False,
        annotation=OVERRIDE_TIPS["chip"],
        changeCommand=_press_override_pick), "chip")
    hubstyle.mark(cmds.button(
        OVERRIDE_APPLY, label=hubstyle.tool_label("Apply"),
        width=hubstyle.tool_width(66), height=hubstyle.height("small", 24),
        annotation="enter, re-write or leave Override mode as picked",
        command=_press_override_apply), "tool", "check")
    cmds.setParent("..")
    row = cmds.rowLayout(OVERRIDE_NAMES, numberOfColumns=3,
                         columnAttach=[(1, "both", 0)] + [(i, "both", 4) for i in (2, 3)])
    hubstyle.mark(row, "columns", layout=True)
    for key in ("rotation", "position", "lag"):
        hubstyle.mark(cmds.text(label=OVERRIDE_LABEL[key], align="left",
                                annotation=OVERRIDE_TIPS[key]), "caption")
    cmds.setParent("..")
    row = cmds.rowLayout(OVERRIDE_FIELDS, numberOfColumns=3,
                         columnAttach=[(1, "both", 0)] + [(i, "both", 4) for i in (2, 3)])
    hubstyle.mark(row, "columns", layout=True)
    for key, default in (("rotation", weaponoverride.DEFAULTS.rotation),
                         ("position", weaponoverride.DEFAULTS.position),
                         ("lag", weaponoverride.DEFAULTS.lag)):
        cmds.floatField(OVERRIDE_FIELD[key], value=_override_number(key, default),
                        precision=2, minValue=0.0,
                        height=hubstyle.height("field", 20),
                        annotation=OVERRIDE_TIPS[key],
                        changeCommand=_press_override_pick)
    cmds.setParent("..")
```

the readers and the painting:

```python
def _override_number(key, default):
    """A remembered number: the card's field while it stands (and remembered), else the
    optionVar, else `default` - the Tools card's rule, so a press works with the card
    closed."""
    name, var = OVERRIDE_FIELD[key], OVERRIDE_VAR[key]
    if cmds.floatField(name, exists=True):
        value = float(cmds.floatField(name, query=True, value=True))
        cmds.optionVar(floatValue=(var, value))
        return value
    if cmds.optionVar(exists=var):
        return float(cmds.optionVar(query=var))
    return default


def card_settings():
    """The three numbers the card (or the memory) holds."""
    d = weaponoverride.DEFAULTS
    return weaponoverride.Settings(_override_number("rotation", d.rotation),
                                   _override_number("position", d.position),
                                   _override_number("lag", d.lag))


def _set_override(standing, chosen=None):
    """Light the mode's state, then its pick. `standing` is the Settings on the weapon,
    or None."""
    chosen = picks() if chosen is None else chosen
    wanted = chosen.get(pending.OVERRIDE)
    _MENU_QUIET["on"] = True
    try:
        if cmds.control(OVERRIDE_CHIP, exists=True):
            cmds.checkBox(OVERRIDE_CHIP, edit=True, value=standing is not None)
        if standing is not None:
            for key, value in zip(("rotation", "position", "lag"), standing):
                if cmds.floatField(OVERRIDE_FIELD[key], exists=True):
                    cmds.floatField(OVERRIDE_FIELD[key], edit=True, value=value)
    finally:
        _MENU_QUIET["on"] = False
    _light(OVERRIDE_CHIP, "want" if wanted is not None else "")
    if cmds.control(OVERRIDE_APPLY, exists=True):
        _light(OVERRIDE_APPLY, "wait" if wanted is not None else "")
```

`refresh` calls `_set_override(weaponoverride.state(weapon), chosen)` beside its
`_set_aim(...)` call.

- [ ] **Step 4: The pick, the press and the apply leg**

```python
def _press_override_pick(*_args):
    """The Override chip and its three fields: a PICK."""
    if _MENU_QUIET["on"]:
        return None
    rig, refusal = maya_rigs.current_rig()
    if rig is None:
        return _status(refusal)
    weapon = weapon_of(rig)
    standing = weaponoverride.state(weapon) if weapon else None
    on = bool(cmds.checkBox(OVERRIDE_CHIP, query=True, value=True))
    chosen = remember(rig, pending.record(
        picks(rig), pending.OVERRIDE,
        weaponoverride.pick_value(on, card_settings()),
        weaponoverride.state_value(standing, card_settings())))
    _set_override(standing, chosen)
    return _status(_picked_text(chosen) or NOTHING_PICKED)


def override_mode(rig=None, weapon=None, settings=None, on=True):
    """Override mode on the rig's weapon, or Default - the hotkey rows' and the
    section check's one road. Its own undo chunk."""
    rig, refusal = _rig(rig)
    if rig is None:
        return refusal
    weapon = weapon or weapon_of(rig)
    if not weapon:
        return NO_WEAPON
    if cmds.objExists(maya_rigs.node(rig, "MoCapConstraints")):
        return RETARGETING
    chest = weaponoverride.chest_of(rig)
    if on:
        text = weaponoverride.refusal(weapon, chest)
        if text:
            return text
    auto = cmds.autoKeyframe(query=True, state=True)
    cmds.undoInfo(openChunk=True, chunkName="Connections: Override")
    try:
        cmds.autoKeyframe(state=False)
        if not on:
            return weaponoverride.leave(weapon)
        return weaponoverride.enter(weapon, chest, settings or card_settings())
    finally:
        cmds.autoKeyframe(state=auto)
        cmds.undoInfo(closeChunk=True)


def _press_override_apply(*_args):
    """The Override section's check: enter, re-write or leave as picked."""
    def act():
        rig, refusal = maya_rigs.current_rig()
        if rig is None:
            return refusal
        chosen = picks(rig)
        wanted = chosen.get(pending.OVERRIDE)
        if wanted is None:
            return NOTHING_PICKED
        text = override_mode(rig=rig, on=wanted[0],
                             settings=weaponoverride.Settings(*wanted[1:4]))
        remember(rig, _settled(rig, chosen, pending.OVERRIDE))
        return text
    return _run(act)
```

`_states`' leg, beside the `pending.AIM` one:

```python
        elif key == pending.OVERRIDE:
            weapon = weapon_of(rig)
            out[key] = weaponoverride.state_value(
                weaponoverride.state(weapon) if weapon else None, card_settings())
```

`apply_weapon`'s leg, after the aim's:

```python
    if pending.OVERRIDE in chosen:
        value = chosen[pending.OVERRIDE]
        notes.append(override_mode(rig=rig, on=value[0],
                                   settings=weaponoverride.Settings(*value[1:4])))
```

`aim_mode` gains the other half of the refusal (read it first - it is at
`connections.py:1997`):

```python
    if on and weaponoverride.is_overridden(weapon):
        return ("%s is in Override mode - it writes the rotation too: Override off "
                "first" % weapon.split("|")[-1])
```

and `apply()`'s Aim Mode dance gains Override's, beside it (read
`connections.py:1960-1990`): read `over = weaponoverride.state(weapon)` with
`aimed`, `weaponoverride.leave(weapon)` before the steps when it stands, and
`weaponoverride.enter(cmds.ls(uuid, long=True)[0], weaponoverride.chest_of(rig), over)`
after them, appending «Override kept» to the notes.

- [ ] **Step 5: Run the card's suites**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_connections_override_row tests.test_connections_two_hands tests.test_scenesetup_connections_pending tests.test_scenesetup_connections tests.test_weapon_override tests.test_pending_override -v`
Expected: every test OK.

- [ ] **Step 6: Commit**

```bash
git add SkeldarAnim/maya_scenesetup/connections.py tests/test_connections_override_row.py
git commit -m "feat(connections): the Override row, its pick and its press"
```

---

### Task 6: the verify script

**Files:**
- Create: `docs/superpowers/plans/verify_weapon_override.py`

**Interfaces:**
- Consumes: everything above.
- Produces: a mayapy standalone run, `0 of N gates failed`, every gate printing
  its measured number. Phases so it can be run in parts:
  `identity,lag,strength,keys,default,reknob,undo,refusals,parent,twohands,poselib`.

- [ ] **Step 1: Write the script**

Copy the frame of `docs/superpowers/plans/verify_weapon_aim_mode.py` (read it
first): `maya.standalone.initialize`, `sys.path.insert(0, <the plugin folder>)`,
`loadPlugin` for `matrixNodes` / `quatNodes` (mayapy does not auto-load them),
a `gate(name, value, want, tolerance)` that prints every number, the rig from
`character.add_character(catalog.character_for("Manny", "rig"))`, a UE clip
retargeted through `maya_rig_retarget.run_retarget`, a Long Sword through
`equip.to_hand`.

The gates, in the spec's order:

1. `identity`: `override_mode(on=True, settings=Settings(1, 1, 0))`, then every
   frame's `weapon.worldMatrix` against the track read before - worst element
   `< 1e-12`.
2. `lag`: `Settings(1, 1, 100)` at 30 fps (`cmds.currentUnit(time="ntsc")`), on
   every frame: `W(f) · C(f-3)⁻¹` against `W_own(f) · C(f)⁻¹`, worst element;
   the control at lag 0 differing by the chest's own three frames of motion.
3. `first frame` bit-exact at lag 100.
4. `strength`: `max angle(R(W(f)), R(W(ref)))` printed at rotation 1 and 0
   beside the chest's own turn; the 0 reading smaller by at least half the
   chest's turn.
5. the same in cm for `position`.
6. `keys`: a weapon keyed on 3 frames with a chest keyed on every frame - the
   written key times are the union plus the filled frames, and a weapon keyed
   on 3 frames with a chest keyed on 3 keys the union of the two (6 or fewer).
7. `default`: every curve's key times, values and tangent types against the
   base read before `enter`; the marker and the six base attributes gone.
8. `reknob`: `80` then `160` ms equals one press at `160` (worst element over
   every frame `< 1e-9`).
9. `undo`: one `cmds.undo()` after each press puts the weapon's curves back.
10. `refusals`: Aim Mode standing, a locked rotateX, a layered translate, no
    chest - each changes nothing (the scene's node count and the weapon's key
    times equal before and after) and names itself.
11. `parent`: Override standing, then `apply(scheme_from_menus({"W": "World", ...}))` -
    the mode still stands, its settings the same, and the hands that follow are
    dragged by the sway (their IK controls' world moves with the weapon).
12. `twohands`: `two_hands_picks` + `apply` on a world weapon puts both hands on
    it; on a held weapon it puts the other hand on it and the weapon is still in
    the hand; `two_hands_state` reads the scene; unticking releases the
    followers and leaves the holder.
13. `poselib`: a card saved off the result (`maya_poselib.capture`) and applied
    onto a second rig - the weapon bone's world on the card's to `1e-4` cm.

- [ ] **Step 2: Run it**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs\superpowers\plans\verify_weapon_override.py <a UE clip .fbx>`
Expected: `0 of 13 gates failed`. Fix the code, not the gate, unless the gate
itself is measuring the wrong thing - and say so in the commit if it was.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/plans/verify_weapon_override.py
git commit -m "test(connections): 2H and Override, 0 of 13 gates standalone"
```

---

### Task 7: the whole suite, the CLAUDE.md section

**Files:**
- Modify: `CLAUDE.md` (one new section; **stage only that hunk**)

- [ ] **Step 1: Run the whole suite**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . 2>$null`
Expected: every test passes but the known `test_chat_deploy.Keys` (this
machine's own saved Cloudflare keys).

- [ ] **Step 2: Re-run the neighbours the change can reach**

Run each, expecting what the section above records for it:
`verify_weapon_aim_mode.py`, `verify_connections_apply.py`,
`verify_ik_world.py`, `verify_camera_weapon_bones.py`,
`verify_poselib_apply.py`. A gate that fails must be checked against a clean
worktree of the commit before this work - if it fails there too, say so.

- [ ] **Step 3: Write the CLAUDE.md section**

A section «Connections: 2H Weapon, and the chest's Override (2026-11-02)» after
the camera tab's, holding: the animator's words and the three answers; what 2H
is (a shortcut for two picks, a holding hand left holding); Override's formula
and what each knob means; the parked base; where the keys go; the refusals; the
Aim Mode / parent-change dance; what it costs in a hand; the proof's numbers;
and «Not seen in a GUI Maya» until the animator presses it.

- [ ] **Step 4: Stage only that hunk and commit**

```bash
git hash-object -w CLAUDE.md          # the blob of the file as it stands
# ...then stage it with update-index --cacheinfo 100644,<sha>,CLAUDE.md
git commit -m "docs: 2H Weapon and the chest's Override in Connections"
```

**The other session's uncommitted work must not be in any commit** - check
`git show --stat HEAD` after each one.

- [ ] **Step 5: Report to the animator**

Say what was built, the verify's number, and that the live press is theirs. Do
not push until they say so.

## Self-Review

**Spec coverage.** 2H - Task 4 (the picks, the chip, the painting) and gate 12.
Override's formula - Task 2 and gates 1-5. The keys and the frames - Task 3's
`enter` and gate 6. The base and the settings - Task 3's `park`/`unpark` and
gates 7-8. The chest - Task 3's `chest_of`. The refusals - Task 3's `refusal`
plus `aim_mode`'s half in Task 5, gate 10. The card - Task 5. The parent dance -
Task 5, gate 11. The Pose Library - nothing to build, gate 13. Modules - the
File Structure table. Not built - nothing to do.

**Placeholders.** None: every step carries its code or the exact file and line
to read first. Task 5's three `TheRow` helpers are named with a fallback
instruction, and Task 6's gates name their measurement rather than their code -
the script is one file whose frame is an existing script.

**Type consistency.** `Settings(rotation, position, lag)` everywhere;
`pick_value` / `state_value` return a 4-tuple `(on, rotation, position, lag)`,
which `pending.phrase`, `_states`, `_press_override_apply` and `apply_weapon`
all unpack as `value[0]` / `value[1:4]`. `scaled(ref, late, rotation, position)`
and `result(own, chest_now, chest_ref, g)` are used only by `wanted`.
`two_hands_picks` returns `{side: choice}` keyed by `"R"` / `"L"`, which
`pending.parent_key` takes as a row.
