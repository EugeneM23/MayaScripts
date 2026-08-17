# Weapon Aim Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One **Add Aim** button in SceneSetup that puts OverRig's aim on the attached weapon with both locators placed automatically, and makes the picker's Bake+Delete resolve the sword or either locator to that aim alone.

**Architecture:** The body of OverRig's `make_aim_from_selected` is repeated in Python, synchronously, so placement and the build happen inside one undo chunk and inside one node diff. The diff becomes an aim manifest — an `objectSet` named `RigPicker_aim_*` carrying the source and handle UUIDs in string attributes — and the picker's Bake+Delete asks a new `maya_overrig/aimrig.py` for it alongside the FK/IK manifests.

**Tech Stack:** Maya 2027, `maya.cmds`, `maya.mel`, `maya.api.OpenMaya`, OverRig v10.2 MEL, stdlib `unittest` under `mayapy`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-08-17-weapon-aim-design.md`. Read it before starting; it records why, not just what.
- Test command: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v`. There is no system Python. Never `pip install` into the Maya tree. Do not use `2>&1` on mayapy in PowerShell.
- `git commit -F <file>`; never a here-string with double quotes. Branch `feature/overrig-picker`.
- `MARGIN = 0.15`. Locator size `1`. Outliner colour `(0.45, 0.7, 0.45)`.
- Set name prefix `RigPicker_aim`, attributes `rigPickerSource` and `rigPickerHandles` (space-separated UUIDs).
- Never identify a rig node by name — manifest membership or UUID only.
- `maya_overrig` must NOT import `maya_scenesetup`. The dependency runs the other way.
- Selection resolution for an aim is **exact match** after normalising shapes to transforms. No descendant walk.

---

### Task 1: OverRig bindings for the aim, and one shared MEL gate

**Files:**
- Modify: `maya_overrig/overrig.py`
- Modify: `maya_overrig/fkcontrols.py:192-209` (make `_mel_gate` delegate)
- Test: `tests/test_overrig.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `overrig.AIM_PROCS` — tuple of the six proc names, in call order.
  - `overrig.missing_aim_procs()` -> `[str]`
  - `overrig.AIM_PROCS_MESSAGE` — format string with one `{0}` for the missing names.
  - `overrig.mel_gate()` -> `str | None`
  - `overrig.add_to_set(objects, set_name)` -> None
  - `overrig.make_aim_locators(source)` -> `(top, side)` long paths
  - `overrig.build_aim()` -> None
  - `overrig.aim_locator_size(objects, size=1.0)` -> None
  - `overrig.aim_outliner_colour()` -> None

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_overrig.py`:

```python
class AimProcs(unittest.TestCase):
    """The aim path leans on four internal, hash-named procs.

    They are global procs and stable inside v10.2, but an OverRig update can
    rename them -- and a renamed proc must reach the status line by name, not
    a traceback out of a Qt slot (trap 20).
    """

    def test_all_six_procs_are_named(self):
        self.assertEqual(len(overrig.AIM_PROCS), 6)
        self.assertIn("make_aim_from_selected", overrig.AIM_PROCS)

    def test_create_comes_before_build(self):
        self.assertLess(overrig.AIM_PROCS.index(overrig.AIM_CREATE_PROC),
                        overrig.AIM_PROCS.index(overrig.AIM_BUILD_PROC))

    def test_missing_procs_are_reported_by_name(self):
        calls = []

        def fake_eval(command):
            calls.append(command)
            return 0 if overrig.AIM_BUILD_PROC in command else 1

        original = overrig.mel.eval
        overrig.mel.eval = fake_eval
        try:
            missing = overrig.missing_aim_procs()
        finally:
            overrig.mel.eval = original
        self.assertEqual(missing, [overrig.AIM_BUILD_PROC])
        self.assertIn(overrig.AIM_BUILD_PROC,
                      overrig.AIM_PROCS_MESSAGE.format(
                          ", ".join(missing)))
```

- [ ] **Step 2: Run them and watch them fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_overrig -v`
Expected: FAIL, `AttributeError: module has no attribute 'AIM_PROCS'`.

- [ ] **Step 3: Implement**

In `maya_overrig/overrig.py`, after `CLEAN_PROC`:

```python
# The aim path. `make_aim_from_selected` only creates the locators and arms a
# run-once scriptJob; the build itself is AIM_BUILD_PROC, which that job would
# have called on the next deselect. We call it ourselves so placement and the
# build land in one undo chunk and one node diff -- a build that arrives later
# is outside both, and the job would still be armed to fire again.
AIM_SET_PROC = "BOVER_10_2_4b209c5c00abddc3e3509a14326e2488"
AIM_CREATE_PROC = "BOVER_10_2_c642429ed9a3aabf65a66eefcd97bfbb"
AIM_COLOUR_PROC = "BOVER_10_2_2e50fb684e35f7dc58ab390d98530944"
AIM_SIZE_PROC = "BOVER_10_2_6de8028af587b467034457b4d6349f89"
AIM_BUILD_PROC = "BOVER_10_2_10df34add5a583f84d24608e860c1b4b"

AIM_PROCS = ("make_aim_from_selected", AIM_SET_PROC, AIM_CREATE_PROC,
             AIM_COLOUR_PROC, AIM_SIZE_PROC, AIM_BUILD_PROC)

AIM_PROCS_MESSAGE = ("OverRig has no procedure {0} - this OverRig is not the "
                     "v10.2 the aim was written against")

AIM_COLOUR = (0.45, 0.7, 0.45)
```

and the functions:

```python
def missing_aim_procs():
    """Which of the aim procs are not in this session. [] means proceed."""
    return [p for p in AIM_PROCS if not mel.eval('exists "{0}"'.format(p))]


def mel_gate():
    """The refusal every MEL entry point shares, or None to proceed.

    The toolset must be in the session (trap 20), and the time slider must
    not carry a multi-frame highlight: OverRig reads it before the playback
    range in nineteen bakes, so a bake under one silently clips to the
    highlighted frames and freezes everything outside (trap 36).
    """
    if not ensure_loaded():
        return NOT_LOADED_MESSAGE
    selection = slider_selection()
    if selection:
        return slider_message(selection)
    return None


def add_to_set(objects, set_name):
    """Register objects in one of OverRig's own bookkeeping sets."""
    quoted = ",".join('"{0}"'.format(o) for o in objects)
    mel.eval('{0}({{{1}}}, "{2}")'.format(AIM_SET_PROC, quoted, set_name))


def aim_outliner_colour():
    """OverRig's outliner colour, on whatever is selected.

    Cosmetic and outliner-only -- the proc sets `useOutlinerColor` and
    nothing else. Called where the native button calls it, on the selection
    the create proc leaves behind.
    """
    mel.eval("{0}({{{1}, {2}, {3}}})".format(AIM_COLOUR_PROC, *AIM_COLOUR))


def aim_locator_size(objects, size=1.0):
    """OverRig's locator sizing, on the given objects."""
    cmds.select(list(objects), replace=True)
    mel.eval("{0}({1})".format(AIM_SIZE_PROC, size))


def make_aim_locators(source):
    """Create OverRig's two aim locators on `source`. Returns (top, side).

    The proc returns every top followed by every side, so one source gives
    exactly two names. It also sets the MEL globals the build proc reads.
    """
    cmds.select(source, replace=True)
    created = mel.eval("{0}()".format(AIM_CREATE_PROC)) or []
    if len(created) != 2:
        raise RuntimeError(
            "OverRig returned {0} aim locator(s), expected 2".format(
                len(created)))
    top, side = (cmds.ls(name, long=True)[0] for name in created)
    return top, side


def build_aim():
    """Run the half of OverRig's aim that its scriptJob would have run.

    Driven by the MEL globals `make_aim_locators` set, not by the selection.
    Constrains the locators to the source, bakes, drops the constraints, then
    aim-constrains the source to the locators.
    """
    mel.eval("{0}()".format(AIM_BUILD_PROC))
```

Then replace the body of `fkcontrols._mel_gate` with a delegation, keeping the
name so no call site changes:

```python
def _mel_gate():
    """The refusal every MEL entry point shares, or None to proceed.

    Lives in overrig now: the aim bake needs the same two guards, and one
    wording beats two that drift apart.
    """
    return overrig.mel_gate()
```

- [ ] **Step 4: Run the tests**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_overrig tests.test_fkcontrols -v`
Expected: PASS, and `test_fkcontrols` unchanged.

- [ ] **Step 5: Commit**

```bash
git add maya_overrig/overrig.py maya_overrig/fkcontrols.py tests/test_overrig.py
git commit -F <message file>
```

---

### Task 2: `aimrig.py` — the aim manifest

**Files:**
- Create: `maya_overrig/aimrig.py`
- Test: `tests/test_aimrig.py`

**Interfaces:**
- Consumes: `overrig.mel_gate`, `overrig.set_members`, `overrig.fast_bake`, `overrig.delete_constraint_attributes`, `builder._scene_nodes`, `builder._fresh_paths`, `builder._recordable`.
- Produces:
  - `aimrig.SET_PREFIX`, `aimrig.SOURCE_ATTR`, `aimrig.HANDLES_ATTR`
  - `aimrig.set_name(key)` -> str
  - `aimrig.normalise(selected)` -> `[str]` (pure)
  - `aimrig.sets_hit(selected, table)` -> `[str]` (pure; table is `[(name, handles, members)]`)
  - `aimrig.aim_sets()` -> `[str]`
  - `aimrig.aim_table()` -> `[(name, handles, members)]`
  - `aimrig.aim_for(handle)` -> `str | None`
  - `aimrig.aim_targets()` -> `[str]`
  - `aimrig.record(key, source, handles, before)` -> str (set name)
  - `aimrig.bake_aims(names)` -> str (message)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_aimrig.py`. Reuse the `_install_fake_maya` helper pattern
from `tests/test_scenesetup_connect.py` verbatim (real modules win when
importable), then:

```python
from maya_overrig import aimrig  # noqa: E402


class Normalise(unittest.TestCase):
    """A viewport click on the sword gives its transform; the outliner can
    give the shape. Both must mean the same aim."""

    def test_a_shape_becomes_its_transform(self):
        self.assertEqual(
            aimrig.normalise(["|carrier|sword|swordShape"],
                             shapes={"|carrier|sword|swordShape":
                                     "|carrier|sword"}),
            ["|carrier|sword"])

    def test_a_transform_is_left_alone(self):
        self.assertEqual(aimrig.normalise(["|carrier|sword"], shapes={}),
                         ["|carrier|sword"])

    def test_duplicates_collapse(self):
        self.assertEqual(
            aimrig.normalise(["|a|s", "|a"], shapes={"|a|s": "|a"}), ["|a"])


class SetsHit(unittest.TestCase):
    """Exact match, never a descendant walk: after Connect the IK hand
    controls are DAG children of the sword geometry, and 'descendant of the
    source' would resolve a hand-control click into the aim (trap 34)."""

    TABLE = [("RigPicker_aim_LongSword_02",
              ["|c|sword", "|c"],
              ["|sword_top", "|sword_side", "|c|sword|aimConstraint1"])]

    def test_the_source_hits(self):
        self.assertEqual(aimrig.sets_hit(["|c|sword"], self.TABLE),
                         ["RigPicker_aim_LongSword_02"])

    def test_the_carrier_hits(self):
        self.assertEqual(aimrig.sets_hit(["|c"], self.TABLE),
                         ["RigPicker_aim_LongSword_02"])

    def test_a_locator_hits(self):
        self.assertEqual(aimrig.sets_hit(["|sword_top"], self.TABLE),
                         ["RigPicker_aim_LongSword_02"])

    def test_the_constraint_hits(self):
        self.assertEqual(
            aimrig.sets_hit(["|c|sword|aimConstraint1"], self.TABLE),
            ["RigPicker_aim_LongSword_02"])

    def test_an_ik_hand_riding_the_sword_does_not_hit(self):
        self.assertEqual(
            aimrig.sets_hit(["|c|sword|hand_r_IK_feet"], self.TABLE), [])

    def test_an_unrelated_node_does_not_hit(self):
        self.assertEqual(aimrig.sets_hit(["|root|pelvis"], self.TABLE), [])

    def test_two_aims_stay_apart(self):
        table = self.TABLE + [("RigPicker_aim_LongSword_021",
                               ["|c2|sword", "|c2"], ["|sword_top1"])]
        self.assertEqual(aimrig.sets_hit(["|sword_top1"], table),
                         ["RigPicker_aim_LongSword_021"])

    def test_nothing_selected_hits_nothing(self):
        self.assertEqual(aimrig.sets_hit([], self.TABLE), [])
```

- [ ] **Step 2: Run them and watch them fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_aimrig -v`
Expected: FAIL, `ModuleNotFoundError: maya_overrig.aimrig`.

- [ ] **Step 3: Implement `maya_overrig/aimrig.py`**

```python
"""The aim manifest: what one aim rig is made of, and how to take it apart.

An aim is recorded the way limbs and chains are -- a UUID diff of every node
in the scene across the build, minus animCurves. Nothing smaller works:
OverRig's aim leaves a constraint node parented under the source, and a
manifest assembled from `OverRig_knots` records only the locators and leaves
that constraint live, driven by nothing (traps 3 and 4).

This module knows nothing about weapons. The picker's Bake+Delete has to
resolve an aim, and maya_overrig importing maya_scenesetup would invert the
layering that already runs the other way.
"""

import maya.cmds as cmds

from maya_overrig import builder, overrig

SET_PREFIX = "RigPicker_aim_"
# The source is NOT a member: members get deleted, and the sword must not.
SOURCE_ATTR = "rigPickerSource"
HANDLES_ATTR = "rigPickerHandles"


def set_name(key):
    return SET_PREFIX + key


# ------------------------------------------------------------------- pure

def normalise(selected, shapes):
    """Selected paths with shapes replaced by their transforms.

    `shapes` maps a shape path to its transform path. Order is kept and
    duplicates collapse, so clicking a mesh and its transform is one hit.
    """
    out = []
    for path in selected:
        out.append(shapes.get(path, path))
    return list(dict.fromkeys(out))


def sets_hit(selected, table):
    """Which aim sets the selection touches. `table` is [(name, handles,
    members)].

    Exact match on purpose. A descendant walk would resolve an IK hand
    control -- a DAG child of the sword geometry after Connect -- into the
    aim, and the safe direction of failure here is "nothing happens", not
    "the wrong rig gets baked".
    """
    wanted = set(selected)
    hit = []
    for name, handles, members in table:
        if wanted.intersection(set(handles) | set(members)):
            hit.append(name)
    return hit


# ------------------------------------------------------------------ scene

def aim_sets():
    """Every aim manifest in the scene, found by prefix.

    Never by exact name: Maya uniquifies, so two characters holding the same
    sword give `RigPicker_aim_LongSword_02` and `...021`.
    """
    return sorted(s for s in (cmds.ls(type="objectSet") or [])
                  if s.startswith(SET_PREFIX))


def _uuid_paths(text):
    """Long paths for a space-separated UUID list, skipping what is gone."""
    out = []
    for uuid in (text or "").split():
        paths = cmds.ls(uuid, long=True) or []
        if paths:
            out.append(paths[0])
    return out


def aim_handles(name):
    """The nodes whose selection means this aim. Never deleted."""
    if not cmds.attributeQuery(HANDLES_ATTR, node=name, exists=True):
        return []
    return _uuid_paths(cmds.getAttr(name + "." + HANDLES_ATTR))


def aim_source(name):
    """The node whose animation gets baked, or None if it is gone."""
    if not cmds.attributeQuery(SOURCE_ATTR, node=name, exists=True):
        return None
    paths = _uuid_paths(cmds.getAttr(name + "." + SOURCE_ATTR))
    return paths[0] if paths else None


def aim_table():
    """[(set name, handles, members)] for every aim in the scene."""
    return [(name, aim_handles(name), overrig.set_members(name))
            for name in aim_sets()]


def _shape_map(selected):
    """{shape path: transform path} for the shapes among `selected`."""
    out = {}
    for path in selected:
        if cmds.objectType(path, isAType="shape"):
            parents = cmds.listRelatives(path, parent=True,
                                         fullPath=True) or []
            if parents:
                out[path] = parents[0]
    return out


def aim_targets():
    """Aim sets the current selection touches."""
    selected = cmds.ls(selection=True, long=True) or []
    if not selected:
        return []
    return sets_hit(normalise(selected, _shape_map(selected)), aim_table())


def aim_for(handle):
    """The aim set `handle` belongs to, or None."""
    hit = sets_hit([handle], aim_table())
    return hit[0] if hit else None


def record(key, source, handles, before):
    """Record everything created since `before` as one aim manifest.

    `before` is a UUID snapshot (trap 8): a path diff records re-parented
    nodes as fresh. Returns the set's name, which Maya may have uniquified.
    """
    fresh = [n for n in builder._fresh_paths(before, builder._scene_nodes())
             if builder._recordable(n)]
    name = cmds.sets(fresh, name=set_name(key))
    cmds.addAttr(name, longName=SOURCE_ATTR, dataType="string")
    cmds.setAttr(name + "." + SOURCE_ATTR,
                 cmds.ls(source, uuid=True)[0], type="string")
    cmds.addAttr(name, longName=HANDLES_ATTR, dataType="string")
    cmds.setAttr(name + "." + HANDLES_ATTR,
                 " ".join(cmds.ls(h, uuid=True)[0] for h in handles),
                 type="string")
    return name


def bake_aims(names):
    """Bake each aim onto its source and delete the rig. Returns a message."""
    message = overrig.mel_gate()
    if message:
        return message

    baked = []
    cmds.undoInfo(openChunk=True, chunkName="Rig Picker aim bake")
    try:
        for name in names:
            if not cmds.objExists(name):
                continue
            source = aim_source(name)
            members = [m for m in overrig.set_members(name)
                       if cmds.objExists(m)]
            # Bake while the constraint still drives, exactly as the FK
            # teardown does. A source deleted by hand leaves orphaned
            # locators, and those still get cleaned up.
            if source:
                overrig.fast_bake([source])
                overrig.delete_constraint_attributes([source])
            if members:
                cmds.delete(members)
            # Maya deletes a set together with its last member (trap 18), so
            # the set may already be gone and deleting it would raise.
            if cmds.objExists(name):
                cmds.delete(name)
            baked.append(name)
    finally:
        cmds.undoInfo(closeChunk=True)

    if not baked:
        return "No aim to bake"
    return "{0} aim(s) baked and removed".format(len(baked))
```

- [ ] **Step 4: Run the tests**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_aimrig -v`
Expected: PASS, 11 tests.

- [ ] **Step 5: Commit**

---

### Task 3: `maya_scenesetup/aim.py` — placement and the press

**Files:**
- Create: `maya_scenesetup/aim.py`
- Test: `tests/test_scenesetup_aim.py`

**Interfaces:**
- Consumes: `attach.model_root`, `attach.MARKER`, `overrig.*` from Task 1, `aimrig.*` from Task 2.
- Produces:
  - `aim.MARGIN = 0.15`
  - `aim.placement(lo, hi, margin=MARGIN)` -> `((x,y,z), (x,y,z))` (pure)
  - `aim.NO_GEOMETRY_MESSAGE`, `aim.ALREADY_MESSAGE`
  - `aim.added_message(label, top)` -> str (pure)
  - `aim.local_extents(model)` -> `(lo, hi)` or `None`
  - `aim.add_aim(entry, carrier)` -> str (message)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_scenesetup_aim.py` with the same `_install_fake_maya`
helper, then:

```python
from maya_scenesetup import aim  # noqa: E402

# The real LongSword_02, measured in the user's scene: 1382 points.
SWORD_LO = (-15.576, -31.119, -1.570)
SWORD_HI = (15.576, 115.925, 1.570)


class Placement(unittest.TestCase):

    def test_the_real_sword_puts_top_past_the_tip_on_y(self):
        top, _side = aim.placement(SWORD_LO, SWORD_HI)
        self.assertEqual(top[0], 0.0)
        self.assertEqual(top[2], 0.0)
        self.assertAlmostEqual(top[1], 115.925 * 1.15, places=3)

    def test_side_goes_on_the_crossguard_axis_at_the_same_distance(self):
        top, side = aim.placement(SWORD_LO, SWORD_HI)
        self.assertEqual(side[1], 0.0)
        self.assertEqual(side[2], 0.0)
        self.assertAlmostEqual(abs(side[0]), abs(top[1]), places=6)

    def test_a_symmetric_axis_ties_positive(self):
        _top, side = aim.placement(SWORD_LO, SWORD_HI)
        self.assertGreater(side[0], 0.0)

    def test_a_model_authored_down_negative_y_points_the_other_way(self):
        top, _side = aim.placement((-15.0, -115.925, -1.0),
                                   (15.0, 31.119, 1.0))
        self.assertAlmostEqual(top[1], -115.925 * 1.15, places=3)

    def test_a_flat_model_has_no_placement(self):
        self.assertIsNone(aim.placement((0.0, 0.0, 0.0), (0.0, 0.0, 0.0)))

    def test_margin_is_fifteen_percent(self):
        self.assertEqual(aim.MARGIN, 0.15)
```

- [ ] **Step 2: Run them and watch them fail**

Expected: FAIL, `ModuleNotFoundError: maya_scenesetup.aim`.

- [ ] **Step 3: Implement `maya_scenesetup/aim.py`**

```python
"""OverRig's aim on the attached weapon, with the locators placed for you.

The two locators are placed from the model's OWN measured extents, not from
any axis convention: the longest local axis is the blade, its further end is
the tip. On the user's LongSword that reads Y=+115.925 with the crossguard on
X, and a model authored down -Y works with no special case.

That is correct even though OverRig hardcodes `aimVector 1 0 0`. The
constraint is built with `-mo`, so the direction that tracks the target
afterwards is whichever direction pointed at it when the offset was measured
-- the blade, not the local +X. Placing by geometry is the thing that makes
the aim intuitive rather than a workaround for it.

The aim goes on the GEOMETRY, not on our carrier: the animator grabs the
geometry (trap 34), the IK hands ride it after Connect, and the grip offsets
live on the carrier and have to stay writable -- setAttr into a constrained
channel raises.
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om

from maya_overrig import aimrig, overrig

from maya_scenesetup import attach

MARGIN = 0.15
LOCATOR_SIZE = 1.0

NO_GEOMETRY_MESSAGE = "no geometry to measure - cannot place the aim"
ALREADY_MESSAGE = ("aim is already on this weapon - Bake+Delete in the "
                   "picker removes it")
ROTATE_INERT_NOTE = "Rotate is now driven by the aim"


# ------------------------------------------------------------------ policy

def placement(lo, hi, margin=MARGIN):
    """Local offsets for the two locators, or None if there is nothing to
    measure.

    `lo`/`hi` are the model's extents in its own frame. Returns
    (top_offset, side_offset) as triples.
    """
    extents = [hi[axis] - lo[axis] for axis in range(3)]
    # Ties broken by axis order, so the answer never depends on sort
    # stability.
    order = sorted(range(3), key=lambda a: (-extents[a], a))
    blade, side = order[0], order[1]
    if extents[blade] <= 0.0:
        return None

    def further(axis):
        """The end of the box further from the origin, signed. The origin
        sits in the grip, because the carrier seats the model on the bone."""
        return hi[axis] if abs(hi[axis]) >= abs(lo[axis]) else lo[axis]

    distance = further(blade) * (1.0 + margin)
    side_sign = 1.0 if further(side) >= 0.0 else -1.0

    top = [0.0, 0.0, 0.0]
    top[blade] = distance
    side_offset = [0.0, 0.0, 0.0]
    side_offset[side] = abs(distance) * side_sign
    return tuple(top), tuple(side_offset)


def added_message(label, top, note=ROTATE_INERT_NOTE):
    return "Aim on {0} - drag {1} to point the blade ({2})".format(
        label, top.split("|")[-1], note)


# ------------------------------------------------------------------- scene

def local_extents(model):
    """The model's mesh extents in its own local frame, or None.

    Points rather than a bounding-box query: the model may hold several
    meshes under nested transforms, and what is wanted is the box in the
    MODEL's frame, which no world-space AABB gives.
    """
    meshes = cmds.listRelatives(model, allDescendents=True, type="mesh",
                               fullPath=True) or []
    if not meshes:
        return None

    selection = om.MSelectionList()
    selection.add(model)
    inverse = selection.getDagPath(0).inclusiveMatrix().inverse()

    lo = [None, None, None]
    hi = [None, None, None]
    for shape in meshes:
        one = om.MSelectionList()
        one.add(shape)
        for point in om.MFnMesh(one.getDagPath(0)).getPoints(om.MSpace.kWorld):
            local = point * inverse
            for axis in range(3):
                if lo[axis] is None or local[axis] < lo[axis]:
                    lo[axis] = local[axis]
                if hi[axis] is None or local[axis] > hi[axis]:
                    hi[axis] = local[axis]
    if lo[0] is None:
        return None
    return tuple(lo), tuple(hi)


def _place(locator, model, offset):
    """Put a locator at a point given in the model's local frame."""
    matrix = om.MMatrix(cmds.xform(model, query=True, worldSpace=True,
                                   matrix=True))
    world = om.MPoint(offset[0], offset[1], offset[2]) * matrix
    cmds.xform(locator, worldSpace=True,
               translation=(world[0], world[1], world[2]))


def add_aim(entry, carrier):
    """Put OverRig's aim on the weapon in `carrier`. Returns a message.

    Not gated on the time slider highlight, deliberately: this path's bake
    reads `playbackOptions -ast/-aet` and never `timeControl -q -ra`, so
    trap 36 does not reach it. The aim BAKE is gated, because
    `apply_Fast_Bake` is one of the nineteen that do read it.
    """
    if not overrig.ensure_loaded():
        return overrig.NOT_LOADED_MESSAGE
    absent = overrig.missing_aim_procs()
    if absent:
        return overrig.AIM_PROCS_MESSAGE.format(", ".join(absent))

    model = attach.model_root(carrier)
    if aimrig.aim_for(model) or aimrig.aim_for(carrier):
        return ALREADY_MESSAGE

    extents = local_extents(model)
    if extents is None:
        return NO_GEOMETRY_MESSAGE
    offsets = placement(*extents)
    if offsets is None:
        return NO_GEOMETRY_MESSAGE
    top_offset, side_offset = offsets

    # autoKey is on in this user's session, and a scripted poke at a keyed
    # channel writes real keys (trap 14). The locators are fresh and
    # unkeyed, but the cost of being wrong here is keys in the animator's
    # curves.
    state = cmds.autoKeyframe(query=True, state=True)
    cmds.autoKeyframe(state=False)
    cmds.undoInfo(openChunk=True, chunkName="Add weapon aim")
    try:
        before = builder_scene_nodes()
        overrig.add_to_set([model], "OverRig_rig_objects")
        top, side = overrig.make_aim_locators(model)
        overrig.aim_outliner_colour()
        overrig.aim_locator_size([top, side], LOCATOR_SIZE)

        _place(top, model, top_offset)
        _place(side, model, side_offset)

        overrig.add_to_set([top], overrig.KNOT_SET)
        overrig.add_to_set([side], overrig.KNOT_SET)
        overrig.build_aim()

        aimrig.record(entry.key, model, [model, carrier], before)
        return added_message(entry.label, top)
    finally:
        cmds.undoInfo(closeChunk=True)
        cmds.autoKeyframe(state=state)


def builder_scene_nodes():
    """The UUID snapshot the manifest diff runs on. Imported lazily so this
    module's import does not pull the whole builder in."""
    from maya_overrig import builder
    return builder._scene_nodes()
```

- [ ] **Step 4: Run the tests**

Expected: PASS, 6 tests.

- [ ] **Step 5: Commit**

---

### Task 4: The **Add Aim** button, and Add's new refusal

**Files:**
- Modify: `maya_scenesetup/window.py`
- Test: `tests/test_scenesetup_window.py`

**Interfaces:**
- Consumes: `aim.add_aim`, `aim.ALREADY_MESSAGE`, `aimrig.aim_for`.
- Produces: `window.AIMED_NO_ADD`, `window.add_aim()` callback.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_scenesetup_window.py`:

```python
class AimRefusals(unittest.TestCase):
    """Add deletes the carrier whole. Without this refusal it takes the aim
    with it and leaves two locators driving a deleted node -- the same
    reasoning that already makes Add refuse while the hands are connected."""

    def test_add_has_a_refusal_naming_the_cure(self):
        self.assertIn("Bake+Delete", window.AIMED_NO_ADD)

    def test_the_two_refusals_are_different(self):
        self.assertNotEqual(window.AIMED_NO_ADD, window.LINKED_NO_ADD)
```

- [ ] **Step 2: Run it and watch it fail**

Expected: FAIL, `AttributeError: AIMED_NO_ADD`.

- [ ] **Step 3: Implement**

In `maya_scenesetup/window.py`, add the import and constant:

```python
from maya_scenesetup import aim as weaponaim
from maya_overrig import aimrig
```

```python
AIMED_NO_ADD = ("the weapon has an aim - Bake+Delete in the picker first")
```

Add the callback next to `connect_arms`:

```python
def add_aim():
    """Put OverRig's aim on the attached weapon, locators placed for you."""
    entry = _entry()
    located = _locate(entry)
    if located is None:
        return
    _root, _bone, carrier, _linked = located
    if not carrier:
        _status(NO_WEAPON)
        return
    _status(weaponaim.add_aim(entry, carrier))
```

In `add_weapon`, after the `linked` check:

```python
    if carrier_now and aimrig.aim_for(attach.model_root(carrier_now)):
        # Add deletes the carrier whole, and the aim's locators drive its
        # geometry: this press would leave them pointing at a deleted node.
        _status(AIMED_NO_ADD)
        return
```

(rename the unpacked `_carrier_now` to `carrier_now` in `add_weapon`.)

Add the button after "Disconnect Arms":

```python
    cmds.button(label="Add Aim", height=28,
                annotation="OverRig's aim on the weapon: one locator a little "
                           "past the tip, one out to the side at the same "
                           "distance. Drag them to aim the blade. Remove it "
                           "with Bake+Delete in the picker.",
                command=lambda *_args: _run(add_aim))
```

- [ ] **Step 4: Run the tests**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenesetup_window -v`
Expected: PASS.

- [ ] **Step 5: Commit**

---

### Task 5: Bake+Delete resolves the aim

**Files:**
- Modify: `maya_overrig/picker_window.py:369-389`
- Test: none new — the behaviour is a live gate (Task 6). The pure resolution is already covered by `tests/test_aimrig.py`.

**Interfaces:**
- Consumes: `aimrig.aim_targets`, `aimrig.bake_aims`.
- Produces: nothing new.

- [ ] **Step 1: Implement**

Add `from maya_overrig import aimrig` to the imports, then replace
`bake_selected_limbs`:

```python
    def bake_selected_limbs(self):
        """Bake ONLY what the selection touches back to clean bones.

        Everything else in the scene keeps its rig. IK limbs take their
        riding finger chains down with them; FK chains bake per chain,
        expanding to whatever rides inside them; a weapon aim bakes onto its
        sword and goes.

        An aim needs no scene_map, so a selected aim is bakeable with no
        skeleton bound -- the sword is not part of the body map.
        """
        aims = aimrig.aim_targets()
        if not self._scene_map:
            if not aims:
                self.status.showMessage(_UNBOUND_MESSAGE)
                return
            self._run("Bake+Delete", self.bake_button,
                      lambda: aimrig.bake_aims(aims))
            return

        ik_limbs, fk_chains = fkcontrols.bake_targets(self._scene_map)
        if not ik_limbs and not fk_chains and not aims:
            self.status.showMessage(
                "Select a rigged element - a controller, a bone, a picker "
                "button, or a weapon with an aim")
            return

        def run():
            messages = []
            # The aim first: it is the smaller teardown, and nothing in it
            # depends on the FK/IK work either way -- the aim drives the
            # sword, not the arm.
            if aims:
                messages.append(aimrig.bake_aims(aims))
            if ik_limbs or fk_chains:
                messages.append(fkcontrols.bake_selection(
                    self._scene_map, ik_limbs, fk_chains))
            return " | ".join(messages)

        self._run("Bake+Delete", self.bake_button, run)
```

- [ ] **Step 2: Run the whole suite**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v`
Expected: every test passes, count up by 17 from the 564 baseline.

- [ ] **Step 3: Commit**

---

### Task 6: The live proof, and the notes

**Files:**
- Create: `docs/superpowers/plans/verify_weapon_aim.py`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Write the verify script**

Ten gates, in the spec's order. Bridge hygiene is mandatory: never
`cmds.undo()` (the whole bridge script is one command, so undo reverts a prior
chunk), never write a literal rest value into a keyed or constrained channel
(read it, write it back), autoKey off around any poke, and wiggle time before
measuring (trap 14). Gate 1 compares world matrices element-wise across
**every** frame including the first and last — an edge-clipping bake is what
trap 12 was, and only a full-range comparison sees it.

- [ ] **Step 2: Run it through the bridge and fix what it finds**

The user must have the command port open. Send with the scratchpad bridge:
write the code to a file, send a one-line `exec(open(...).read())`, let an
idempotent runner capture stdout into an output file, and poll for that file
while draining the socket. The runner MUST write a `.ran` marker and
`SystemExit` when it already exists — the port executes one sent line twice.

- [ ] **Step 3: Record it in CLAUDE.md**

Add the aim to the SceneSetup section: what the button does, the placement
rule with the measured numbers, why `-mo` makes geometry-based placement
correct, the manifest and its two attributes, the exact-match resolution rule
and why it is not a descendant walk, and the gate split (build not gated on
the slider highlight, bake gated). Add the module rows for `aimrig.py` and
`aim.py`. Number any new trap after 37.

- [ ] **Step 4: Commit**

---

## Self-Review

**Spec coverage.** The ask → Tasks 3, 4, 5. OverRig's deferred build → Task 1
(`build_aim`) and Task 3 (call order). Placement → Task 3 (`placement`,
`local_extents`). Aim on the geometry → Task 3. Manifest and resolution →
Task 2. Gate split → Task 1 (`mel_gate`), Task 2 (bake gated), Task 3 (build
not gated). Module table → Tasks 1-5. Animator-visible messages → Tasks 3, 4.
Testing → the test steps plus Task 6. Out of scope → nothing built for it.

**Placeholders.** None: every code step carries the actual code, every test
step the actual assertions.

**Type consistency.** `sets_hit(selected, table)` takes `[(name, handles,
members)]` in Task 2's tests, its implementation, and `aim_table`'s return.
`normalise(selected, shapes)` takes the shape map in both. `placement`
returns `None` or a pair of triples in both the tests and `add_aim`'s use.
`aimrig.record(key, source, handles, before)` matches Task 3's call.
`aim.add_aim(entry, carrier)` matches Task 4's call. `aimrig.aim_targets()`
and `bake_aims(names)` match Task 5's use.
