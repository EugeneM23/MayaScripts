# Symmetric FK Control Axes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put every FK controller on the skeleton's mirror convention, so a mirrored pose reads as equal channel values on both sides and Animbot's mirror produces a geometrically correct result.

**Architecture:** A joint's world rotation is `rotateAxis · rotate · jointOrient · parent` (verified against the live rig), and the rotation offset `C` between an OverRig knot and the bone it drives is constant over time (verified: deviation 1e-14). Both facts together let the whole fix be local to each controller: set `rotateAxis = C⁻¹`, `jointOrient = C · R(t0)`, and rewrite each rotate key as `C · R(t) · R(t0)⁻¹ · C⁻¹`. The product `rotateAxis · rotate · jointOrient` is algebraically unchanged, so no world transform moves, no constraint is touched, and no node is created or deleted. The controller then reads zero at the build pose and carries the bone's motion relative to it — which is equal on both sides for a mirrored pose, because the skeleton is behaviour-mirrored.

**Tech Stack:** Python 3.13, `maya.cmds`, `maya.api.OpenMaya` (MMatrix / MEulerRotation / MTransformationMatrix), stdlib `unittest` under `mayapy`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-08-15-fk-control-axes-design.md`.
- Branch `feature/overrig-picker`. Commit after every task.
- Tests run with `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v`. There is no system Python.
- `bodymap.py` imports stdlib only; `picker_view.py` never imports `maya.cmds`. Not affected by this work, but a subprocess test enforces it.
- Fiddly logic lives in pure functions taking the scene as data. Maya-touching wrappers stay thin.
- Zero drift is the gate: no bone's world matrix may change at any frame.
- Do not call `barn_fast_bake_source_obj_and_delete_knots()`. Ever.
- Live verification goes through the command port on `127.0.0.1:7001` (see CLAUDE.md). Unit tests alone have repeatedly passed while the scene was broken.

---

## File Structure

| File | Responsibility | New? |
|---|---|---|
| `maya_overrig/axes.py` | The rotation algebra — offsets, retargeting, orient values, euler continuity, mirror-sign measurement. Pure functions over matrices; **never imports `maya.cmds`**. | create |
| `tests/test_axes.py` | Unit tests for all of the above, including the world-preservation identity. | create |
| `maya_overrig/fkcontrols.py` | Gains `align_controllers(...)`, the thin scene wrapper that reads curves, calls `axes`, and writes back; called at the end of `build_fk`. | modify |
| `tests/test_fkcontrols.py` | Tests for the pure part of the wrapper (key-time union). | modify |
| `docs/superpowers/plans/verify_axes.py` | Live verification sent through the bridge: drift, rest-frame signs, value symmetry, Animbot mirror. | create |
| `CLAUDE.md` | Architecture table gains `axes.py`; the FK section records the convention. | modify |

`axes.py` imports `maya.api.OpenMaya` but not `maya.cmds` — OpenMaya's math types work in `mayapy` without a Maya session, which is what keeps these tests fast and honest.

---

### Task 1: The rotation algebra

**Files:**
- Create: `maya_overrig/axes.py`
- Test: `tests/test_axes.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `frame_offset(bone_matrix, knot_matrix) -> MMatrix` — the constant `C = B · W⁻¹`, rotation only.
  - `orient_values(offset, reference) -> (MMatrix, MMatrix)` — `(rotateAxis, jointOrient)` as `(C⁻¹, C · R_ref)`.
  - `retarget(rotation, offset, reference) -> MMatrix` — `C · R · R_ref⁻¹ · C⁻¹`.
  - All three take and return `maya.api.OpenMaya.MMatrix`.

- [ ] **Step 1: Write the failing test**

```python
import unittest

import maya.api.OpenMaya as om

from maya_overrig import axes


def _rot(x, y, z):
    """A rotation matrix from degrees, XYZ order."""
    import math
    return om.MEulerRotation(math.radians(x), math.radians(y),
                             math.radians(z)).asMatrix()


def _close(a, b, tol=1e-9):
    return max(abs(a[i] - b[i]) for i in range(16)) < tol


class TestFrameOffset(unittest.TestCase):

    def test_offset_maps_the_knot_frame_onto_the_bone(self):
        knot = _rot(10.0, 20.0, 30.0)
        bone = _rot(-5.0, 45.0, 12.0)
        offset = axes.frame_offset(bone, knot)
        self.assertTrue(_close(offset * knot, bone))

    def test_identical_frames_give_identity(self):
        frame = _rot(3.0, 4.0, 5.0)
        self.assertTrue(_close(axes.frame_offset(frame, frame), om.MMatrix()))

    def test_translation_is_ignored(self):
        knot = _rot(10.0, 20.0, 30.0)
        bone = _rot(-5.0, 45.0, 12.0)
        moved = om.MMatrix(bone)
        moved[12], moved[13], moved[14] = 100.0, -50.0, 7.0
        self.assertTrue(_close(axes.frame_offset(moved, knot),
                               axes.frame_offset(bone, knot)))


class TestRetarget(unittest.TestCase):

    def test_reference_frame_retargets_to_identity(self):
        """At the reference pose the controller reads zero."""
        reference = _rot(11.0, -22.0, 33.0)
        offset = _rot(90.0, 0.0, 0.0)
        self.assertTrue(_close(axes.retarget(reference, offset, reference),
                               om.MMatrix()))

    def test_world_is_preserved(self):
        """rotateAxis * retargeted * jointOrient == the original rotation.

        This identity is the whole safety argument: nothing in the scene can
        move, because the product the DAG consumes is unchanged.
        """
        offset = _rot(90.0, 15.0, -40.0)
        reference = _rot(11.0, -22.0, 33.0)
        rotate_axis, joint_orient = axes.orient_values(offset, reference)
        for pose in (_rot(0.0, 0.0, 0.0), _rot(5.0, 0.0, 0.0),
                     _rot(-30.0, 60.0, 120.0), reference):
            retargeted = axes.retarget(pose, offset, reference)
            self.assertTrue(
                _close(rotate_axis * retargeted * joint_orient, pose),
                "world moved for pose {0}".format(pose))

    def test_identity_offset_is_a_plain_rebase(self):
        pose = _rot(10.0, 0.0, 0.0)
        reference = _rot(4.0, 0.0, 0.0)
        self.assertTrue(_close(
            axes.retarget(pose, om.MMatrix(), reference),
            pose * reference.inverse()))


class TestOrientValues(unittest.TestCase):

    def test_rotate_axis_is_the_inverse_offset(self):
        offset = _rot(90.0, 15.0, -40.0)
        rotate_axis, _ = axes.orient_values(offset, om.MMatrix())
        self.assertTrue(_close(rotate_axis, offset.inverse()))

    def test_joint_orient_carries_the_reference(self):
        offset = _rot(90.0, 15.0, -40.0)
        reference = _rot(11.0, -22.0, 33.0)
        _, joint_orient = axes.orient_values(offset, reference)
        self.assertTrue(_close(joint_orient, offset * reference))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_axes -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'maya_overrig.axes'`.

- [ ] **Step 3: Write the minimal implementation**

```python
"""Rotation algebra for putting controllers on the skeleton's convention.

A joint's world rotation is `rotateAxis * rotate * jointOrient * parent`
(verified against the live rig), and the rotation offset between an OverRig
knot and the bone it drives is constant over time (verified: 1e-14 across
frames). Together those let a controller be re-expressed in a new rest frame
without moving anything: the product the DAG consumes is unchanged by
construction, so the identity in `retarget` is the whole safety argument.

Pure matrix maths. Imports OpenMaya for its types, never `maya.cmds`.
"""

import maya.api.OpenMaya as om


def _rotation_only(matrix):
    """The rotation part of a matrix, translation dropped."""
    return om.MTransformationMatrix(om.MMatrix(matrix)).rotation(
        asQuaternion=True).asMatrix()


def frame_offset(bone_matrix, knot_matrix):
    """The constant C carrying the knot's frame onto the bone's: C = B * W^-1.

    Constant over time because the knot drives the bone rigidly, which is what
    makes a single static correction enough.
    """
    return _rotation_only(bone_matrix) * _rotation_only(knot_matrix).inverse()


def orient_values(offset, reference):
    """`(rotateAxis, jointOrient)` for a controller re-expressed against
    `reference`, the rotation it holds at the build pose."""
    return offset.inverse(), offset * reference


def retarget(rotation, offset, reference):
    """One rotate value expressed in the new rest frame.

    C * R * R_ref^-1 * C^-1 -- a conjugation, so the value is the motion away
    from the build pose measured in the bone's own axes.
    """
    return offset * rotation * reference.inverse() * offset.inverse()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_axes -v`
Expected: PASS, 8 tests.

- [ ] **Step 5: Commit**

```bash
git add maya_overrig/axes.py tests/test_axes.py && git commit -m "feat(axes): rotation algebra for re-expressing controllers"
```

---

### Task 2: Euler continuity and mirror measurement

**Files:**
- Modify: `maya_overrig/axes.py`
- Test: `tests/test_axes.py`

**Interfaces:**
- Consumes: `frame_offset`, `retarget` from Task 1.
- Produces:
  - `euler_degrees(matrix, order=0, previous=None) -> (float, float, float)` — matrix to degrees, picking the solution nearest `previous` so a rewritten curve does not flip.
  - `mirror_signs(left_axes, right_axes, tolerance=0.02) -> tuple | None` — the sign triple relating two frames across the YZ plane, `None` when they are not mirror-related at all. `left_axes`/`right_axes` are 3-tuples of 3-tuples (the X, Y, Z axes in world).

- [ ] **Step 1: Write the failing test**

```python
class TestEulerDegrees(unittest.TestCase):

    def test_round_trips_a_rotation(self):
        values = axes.euler_degrees(_rot(10.0, 20.0, 30.0))
        for got, want in zip(values, (10.0, 20.0, 30.0)):
            self.assertAlmostEqual(got, want, places=6)

    def test_identity_is_zero(self):
        for value in axes.euler_degrees(om.MMatrix()):
            self.assertAlmostEqual(value, 0.0, places=9)

    def test_stays_near_the_previous_value(self):
        """A baked curve must not flip by 360 between neighbouring keys."""
        matrix = _rot(170.0, 0.0, 0.0)
        near = axes.euler_degrees(matrix, previous=(530.0, 0.0, 0.0))
        self.assertAlmostEqual(near[0], 530.0, places=6)

    def test_the_flipped_solution_describes_the_same_rotation(self):
        matrix = _rot(170.0, 0.0, 0.0)
        near = axes.euler_degrees(matrix, previous=(530.0, 0.0, 0.0))
        self.assertTrue(_close(_rot(*near), matrix, tol=1e-6))


class TestMirrorSigns(unittest.TestCase):

    IDENTITY = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))

    def test_behaviour_mirror_reads_all_negative(self):
        """What the UE skeleton uses: mirror, then negate every axis."""
        right = ((1.0, 0.0, 0.0), (0.0, -1.0, 0.0), (0.0, 0.0, -1.0))
        self.assertEqual(axes.mirror_signs(self.IDENTITY, right),
                         (-1, -1, -1))

    def test_the_convention_our_knots_used_to_have(self):
        right = ((-1.0, 0.0, 0.0), (0.0, -1.0, 0.0), (0.0, 0.0, 1.0))
        self.assertEqual(axes.mirror_signs(self.IDENTITY, right),
                         (1, -1, 1))

    def test_unrelated_frames_give_none(self):
        right = ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0))
        self.assertIsNone(axes.mirror_signs(self.IDENTITY, right))

    def test_tolerates_a_small_measurement_error(self):
        right = ((0.999, 0.01, 0.0), (0.0, -1.0, 0.0), (0.0, 0.0, -1.0))
        self.assertEqual(axes.mirror_signs(self.IDENTITY, right),
                         (-1, -1, -1))

    def test_skewed_frames_are_handled(self):
        """Real bones are not axis-aligned; the measure must not assume it."""
        left = ((0.576, -0.817, 0.023), (-0.033, -0.052, -0.998),
                (0.817, 0.574, -0.056))
        right = tuple(tuple(-c for c in (-a[0], a[1], a[2])) for a in left)
        self.assertEqual(axes.mirror_signs(left, right), (-1, -1, -1))
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_axes -v`
Expected: FAIL — `AttributeError: module 'maya_overrig.axes' has no attribute 'euler_degrees'`.

- [ ] **Step 3: Write the minimal implementation**

Append to `maya_overrig/axes.py`:

```python
import math


def euler_degrees(matrix, order=0, previous=None):
    """A matrix as XYZ-ordered degrees, nearest to `previous` if given.

    Every rotation has infinitely many euler representations. Picking blindly
    puts 360-degree jumps into a rewritten curve, which reads as the rig
    snapping between two keys.
    """
    rotation = om.MTransformationMatrix(om.MMatrix(matrix)).rotation()
    rotation.reorderIt(order)
    if previous is not None:
        rotation.setToClosestSolution(
            om.MEulerRotation([math.radians(v) for v in previous], order))
    return tuple(math.degrees(v) for v in (rotation.x, rotation.y, rotation.z))


def mirror_signs(left_axes, right_axes, tolerance=0.02):
    """Sign triple relating two frames across the YZ plane, None if unrelated.

    Each entry is `mirror(left_axis) . right_axis` rounded to +-1: the sign of
    each axis after reflecting the left frame. `(-1, -1, -1)` is the classic
    behaviour mirror the UE skeleton uses, and the convention this project
    targets.
    """
    signs = []
    for left, right in zip(left_axes, right_axes):
        mirrored = (-left[0], left[1], left[2])
        dot = sum(a * b for a, b in zip(mirrored, right))
        if abs(abs(dot) - 1.0) > tolerance:
            return None
        signs.append(1 if dot > 0 else -1)
    return tuple(signs)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_axes -v`
Expected: PASS, 17 tests.

- [ ] **Step 5: Commit**

```bash
git add maya_overrig/axes.py tests/test_axes.py && git commit -m "feat(axes): euler continuity and mirror-sign measurement"
```

---

### Task 3: Key-time collection

**Files:**
- Modify: `maya_overrig/fkcontrols.py`
- Test: `tests/test_fkcontrols.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `merge_key_times(per_channel) -> list[float]` — the sorted union of key times across channels, so all three rotate channels are rewritten at the same times. Takes a list of per-channel time lists, which keeps it pure and testable.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_fkcontrols.py`, before the `if __name__` block:

```python
class TestMergeKeyTimes(unittest.TestCase):

    def test_union_of_channels_sorted(self):
        self.assertEqual(
            fkcontrols.merge_key_times([[3.0, 1.0], [2.0], [1.0]]),
            [1.0, 2.0, 3.0])

    def test_duplicates_collapse(self):
        self.assertEqual(
            fkcontrols.merge_key_times([[1.0, 2.0], [1.0, 2.0]]),
            [1.0, 2.0])

    def test_empty_channels_are_skipped(self):
        self.assertEqual(
            fkcontrols.merge_key_times([[], None, [5.0]]), [5.0])

    def test_no_keys_at_all(self):
        self.assertEqual(fkcontrols.merge_key_times([None, None]), [])
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_fkcontrols -v`
Expected: FAIL — `AttributeError: module 'maya_overrig.fkcontrols' has no attribute 'merge_key_times'`.

- [ ] **Step 3: Write the minimal implementation**

Add to `maya_overrig/fkcontrols.py`, next to the other pure helpers (after `radius_from`):

```python
def merge_key_times(per_channel):
    """Sorted union of key times across channels.

    All three rotate channels are rewritten together -- a value is only
    meaningful as part of a whole rotation -- so they need one shared list of
    times. `cmds.keyframe` returns None for an unkeyed channel.
    """
    times = set()
    for channel in per_channel:
        times.update(channel or ())
    return sorted(times)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_fkcontrols -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add maya_overrig/fkcontrols.py tests/test_fkcontrols.py && git commit -m "feat(fk): key-time union helper"
```

---

### Task 4: Align the controllers, wired into Build FK

**Files:**
- Modify: `maya_overrig/fkcontrols.py`
- Test: exercised live in Task 5; the maths it leans on is already covered.

**Interfaces:**
- Consumes: `axes.frame_offset`, `axes.orient_values`, `axes.retarget`, `axes.euler_degrees` (Tasks 1–2), `merge_key_times` (Task 3).
- Produces: `align_controllers(scene_map, only=None) -> int` — realigns every built FK controller, returns how many were changed. Called at the end of `build_fk`, inside its undo chunk.

- [ ] **Step 1: Write the implementation**

Add to `maya_overrig/fkcontrols.py` after `_dress_knots`, and import `axes` at the top (`from maya_overrig import axes, bodymap, builder, naming, overrig`):

```python
def _world_rotation(node):
    """A node's world rotation, translation dropped."""
    return axes._rotation_only(
        om.MMatrix(cmds.xform(node, query=True, worldSpace=True, matrix=True)))


def _local_rotation(node):
    """A node's `rotate` channel as a matrix, in its own rotate order."""
    values = cmds.getAttr(node + ".rotate")[0]
    return om.MEulerRotation(
        [v * math.pi / 180.0 for v in values],
        cmds.getAttr(node + ".rotateOrder")).asMatrix()


def align_controllers(scene_map, only=None):
    """Re-express every FK controller in its bone's axes. Nothing moves.

    `rotateAxis` takes the inverse of the knot-to-bone offset, `jointOrient`
    takes what the controller reads at the build pose, and every rotate key is
    conjugated into the new frame. The product the DAG consumes --
    rotateAxis * rotate * jointOrient -- is unchanged by construction, so no
    bone moves and no constraint is disturbed.

    Order does not matter: each controller's inputs are read from world
    transforms that this operation provably leaves alone.
    """
    aligned = 0
    for chain_name, chain in CHAINS:
        if only is not None and chain_name not in only:
            continue
        for joint in chain:
            ctrl = controller_name(joint)
            bone = scene_map.get(joint)
            if not (cmds.objExists(ctrl) and bone and cmds.objExists(bone)):
                continue
            if _align_one(ctrl, bone):
                aligned += 1
    return aligned


def _align_one(ctrl, bone):
    """Realign one controller. True when it was changed."""
    offset = axes.frame_offset(_world_rotation(bone), _world_rotation(ctrl))
    reference = _local_rotation(ctrl)
    rotate_axis, joint_orient = axes.orient_values(offset, reference)

    times = merge_key_times([
        cmds.keyframe(ctrl, attribute=attr, query=True, timeChange=True)
        for attr in ("rotateX", "rotateY", "rotateZ")])
    order = cmds.getAttr(ctrl + ".rotateOrder")

    # Read every key before writing any: the curves are the input.
    poses = []
    for time in times:
        values = [cmds.keyframe(ctrl, attribute=attr, query=True,
                                time=(time, time), valueChange=True)
                  for attr in ("rotateX", "rotateY", "rotateZ")]
        if any(v is None for v in values):
            return False  # a channel is missing this key; leave it alone
        poses.append((time, [v[0] for v in values]))

    retargeted = []
    previous = None
    for time, values in poses:
        rotation = om.MEulerRotation(
            [v * math.pi / 180.0 for v in values], order).asMatrix()
        new = axes.retarget(rotation, offset, reference)
        previous = axes.euler_degrees(new, order, previous)
        retargeted.append((time, previous))

    cmds.setAttr(ctrl + ".rotateAxis", *axes.euler_degrees(rotate_axis))
    cmds.setAttr(ctrl + ".jointOrient", *axes.euler_degrees(joint_orient))
    for time, values in retargeted:
        for attr, value in zip(("rotateX", "rotateY", "rotateZ"), values):
            cmds.keyframe(ctrl, attribute=attr, time=(time, time),
                          valueChange=value, absolute=True)
    if not times:
        cmds.setAttr(ctrl + ".rotate",
                     *axes.euler_degrees(
                         axes.retarget(reference, offset, reference), order))
    return True
```

Add `import math` to the imports at the top of `fkcontrols.py`.

- [ ] **Step 2: Wire it into `build_fk`**

In `build_fk`, immediately after the `for chain_name, chain in CHAINS:` loop ends and before `finally:`, add:

```python
        aligned = align_controllers(scene_map, only)
```

and extend the message after the `finally` block:

```python
    message = "Built {0} FK controller(s), {1} chain(s) coupled, " \
              "{2} node(s) recorded, {3} aligned to bone axes".format(
                  created, attached, recorded, aligned)
```

- [ ] **Step 3: Run the whole suite**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t .`
Expected: PASS, no regressions. (These tests do not exercise the scene path; Task 5 is where this is really tested.)

- [ ] **Step 4: Commit**

```bash
git add maya_overrig/fkcontrols.py && git commit -m "feat(fk): align controllers to their bones' axes at build time"
```

---

### Task 5: Live verification — the real gate

**Files:**
- Create: `docs/superpowers/plans/verify_axes.py`

**Interfaces:**
- Consumes: everything above.
- Produces: a script sent through the command port that prints a verdict per check.

This is the task that decides whether the work is done. Unit tests in this project have repeatedly passed while the scene was broken.

- [ ] **Step 1: Write the verification script**

`docs/superpowers/plans/verify_axes.py` must check, in this order, writing results to a file the sender reads back:

1. **Drift.** Record every bone's world matrix at every frame of the timeline *before* `align_controllers` runs, then again after, and report the maximum deviation. **Gate: below 1e-4.** This runs on a rig built by `Build FK` and is the first thing to check — a mirror that costs the animation is worth nothing.
2. **Rest-frame signs.** For each left/right controller pair, compute the rest frame `rotateAxis · jointOrient · parentWorld` and feed the two frames to `axes.mirror_signs`. **Gate: `(-1, -1, -1)` for every pair.**
3. **Value symmetry.** At the build frame every controller reads `(0, 0, 0)`. Then pose the left arm, mirror the pose onto the right by hand through world matrices, and confirm the two sides' rotate values match to 1e-3.
4. **Animbot.** Pose the left arm and key it, select both arms, call `CORE.mirror.mirrorAllKeys_click()` (reached via `from animBot._api.core import CORE` — *not* the tool button, whose `click()` never arrives), flush the idle queue with `QtWidgets.QApplication.processEvents()` and `maya.utils.processIdleEvents()`, then check the right arm's joints land within 0.5 of the mirror of where the left arm's joints were, measured in root space. Undo afterwards.

Every step runs inside an undo chunk and restores what it changed. `autoKeyframe` is disabled for the duration and restored.

- [ ] **Step 2: Rebuild FK in the live scene and run it**

Send `Bake+Delete` then `Build FK` through the bridge, then the verification script. Report every gate's number, not just "passed".

- [ ] **Step 3: If Animbot still mirrors wrongly**

Do not paper over it. Animbot caches what it learns per controller, so first clear its data (`CORE.mirror.clearMirrorSettingsData_click()`) and re-run. If it still fails, the fallback recorded in the spec is Animbot's own `snapshotMirrorSettings` — teach it once, verify again, and write down which was needed.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/verify_axes.py && git commit -m "test(fk): live verification for controller axis alignment"
```

---

### Task 6: Documentation

**Files:**
- Modify: `CLAUDE.md`
- Modify: `docs/superpowers/specs/2026-08-15-fk-control-axes-design.md`

- [ ] **Step 1: Update the architecture table**

Add to the `maya_overrig` table in `CLAUDE.md`:

| `axes.py` | Rotation algebra for controller axes, pure | `maya.api.OpenMaya` |

- [ ] **Step 2: Record the convention in the Build FK paragraph**

State that controllers are re-expressed in their bones' axes at build time, that the operation is world-preserving by construction (`rotateAxis · rotate · jointOrient` is unchanged), that controllers read zero at the build pose, and that a mirrored pose therefore reads as equal values on both sides. Add the Animbot entry point (`CORE.mirror.mirrorAllKeys_click()` via `animBot._api.core`; the tool button's `click()` silently does nothing) to the traps list — it cost most of a session.

- [ ] **Step 3: Correct the spec**

The spec's implementation sketch calls for a root-down walk. The world-preserving formulation makes ordering irrelevant, because each controller's inputs are read from transforms the operation provably leaves alone. Replace that step and note why.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md docs/superpowers/specs/2026-08-15-fk-control-axes-design.md && git commit -m "docs(fk): record the controller axis convention"
```

---

## Self-Review

**Spec coverage:** target convention → Tasks 1–4; alignment of all 17 chains → `align_controllers` walks `CHAINS`; animation preserved → the world-preservation identity, tested in Task 1 and measured in Task 5; ring geometry unchanged → nothing in this plan touches `_dress_knots`; verification (drift, frames, Animbot) → Task 5; Animbot's cache hazard → Task 5 Step 3.

**Deviation from the spec, deliberate:** the spec's root-down ordering requirement is dropped, and Task 6 Step 3 corrects the spec. It was written for a formulation that moved world transforms; this one does not.

**Placeholders:** none. Every code step carries its code. Task 5 describes checks rather than final source because it is written against whatever the scene holds at that moment; its four gates and their thresholds are stated exactly.

**Type consistency:** `frame_offset`, `orient_values`, `retarget` take and return `MMatrix` throughout; `euler_degrees` is the only place matrices become degrees, and it is the only thing `cmds.setAttr` is fed. `merge_key_times` takes a list of per-channel lists and returns a sorted list of floats, matching what `cmds.keyframe(..., timeChange=True)` returns, including its `None` for unkeyed channels.
