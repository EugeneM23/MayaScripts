# Build IK Limbs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Rig Picker's `Build` button create IK on both arms and both legs of the bound skeleton through OverRig.

**Architecture:** `overrig.py` is a thin binding to the MEL toolset with no policy in it; `builder.py` holds the limb table, the manifest and the build/teardown orchestration; `picker_window.py` gains only button wiring. Everything the build touches is recorded in our own object set so a rebuild cannot destroy the user's hand-made OverRig work.

**Tech Stack:** Python 3.13.9 (Maya 2027), `maya.cmds`, `maya.mel`, PySide6, stdlib `unittest`.

Spec: `docs/superpowers/specs/2026-08-14-build-ik-limbs-design.md`

## Global Constraints

- Test command, from repo root: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v`
- Qt tests need `$env:QT_QPA_PLATFORM = 'offscreen'` first.
- `bodymap.py` and `picker_view.py` MUST stay free of `maya.cmds`. `builder.py` and `overrig.py` may use it.
- OverRig's IK proc needs exactly three joints selected in order root, middle, end.
- OverRig's IK proc bakes across the timeline range from `timeControl -q -ra`.
- Teardown must remove only nodes recorded in `RigPicker_build`. Never call `barn_fast_bake_source_obj_and_delete_knots()` — it is scene-global.
- The whole build is one undo chunk.
- Branch: `feature/overrig-picker`. Commit after every task.

## File Structure

| File | Responsibility |
|---|---|
| `maya_overrig/overrig.py` | MEL binding: is it loaded, call procs, read sets |
| `maya_overrig/builder.py` | Limb table, manifest, build and teardown |
| `maya_overrig/picker_window.py` | Wire the `Build` button, report the result |
| `tests/test_builder.py` | Limb table and resolution, plain Python |
| `docs/superpowers/plans/verify_build.py` | Live verification through the bridge |

---

### Task 1: Limb table and resolution

**Files:**
- Create: `maya_overrig/builder.py`
- Test: `tests/test_builder.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `LIMBS: tuple[tuple[str, tuple[str, str, str]], ...]`
  - `BUILD_SET = "RigPicker_build"`
  - `BuildResult = namedtuple("BuildResult", "built skipped created removed message")`
  - `limb_joints(scene_map) -> list[tuple[str, list[str]]]`
  - `missing_limbs(scene_map) -> list[str]`

- [ ] **Step 1: Write the failing test**

Create `tests/test_builder.py`:

```python
import unittest

from maya_overrig import bodymap, builder


class TestLimbTable(unittest.TestCase):

    def test_four_limbs(self):
        self.assertEqual(len(builder.LIMBS), 4)

    def test_names_are_the_picker_regions(self):
        self.assertEqual([name for name, _ in builder.LIMBS],
                         ["arm_l", "arm_r", "leg_l", "leg_r"])

    def test_three_joints_each(self):
        for name, joints in builder.LIMBS:
            self.assertEqual(len(joints), 3, name)

    def test_twelve_distinct_joints(self):
        every = [j for _, joints in builder.LIMBS for j in joints]
        self.assertEqual(len(every), 12)
        self.assertEqual(len(set(every)), 12)

    def test_every_joint_exists_in_the_body_map(self):
        known = {b.joint for b in bodymap.BUTTONS}
        for name, joints in builder.LIMBS:
            for joint in joints:
                self.assertIn(joint, known, "{0}: {1}".format(name, joint))

    def test_order_is_root_middle_end(self):
        table = dict(builder.LIMBS)
        self.assertEqual(table["leg_l"], ("thigh_l", "calf_l", "foot_l"))
        self.assertEqual(table["arm_r"], ("upperarm_r", "lowerarm_r", "hand_r"))


class TestLimbJoints(unittest.TestCase):

    @staticmethod
    def _full_map():
        return {j: "|rig|" + j
                for _, joints in builder.LIMBS for j in joints}

    def test_resolves_all_four_limbs(self):
        resolved = builder.limb_joints(self._full_map())
        self.assertEqual(len(resolved), 4)

    def test_keeps_joint_order(self):
        resolved = dict(builder.limb_joints(self._full_map()))
        self.assertEqual(resolved["leg_l"],
                         ["|rig|thigh_l", "|rig|calf_l", "|rig|foot_l"])

    def test_maps_through_the_scene_map(self):
        """Prefixed and namespaced paths come straight from the binding."""
        scene_map = self._full_map()
        scene_map["foot_l"] = "|hero:rig|hero:prefix_foot_l"
        resolved = dict(builder.limb_joints(scene_map))
        self.assertEqual(resolved["leg_l"][2], "|hero:rig|hero:prefix_foot_l")

    def test_skips_a_limb_with_a_missing_joint(self):
        scene_map = self._full_map()
        del scene_map["calf_r"]
        resolved = dict(builder.limb_joints(scene_map))
        self.assertNotIn("leg_r", resolved)
        self.assertIn("leg_l", resolved)

    def test_empty_map_resolves_nothing(self):
        self.assertEqual(builder.limb_joints({}), [])


class TestMissingLimbs(unittest.TestCase):

    def test_nothing_missing_on_a_full_skeleton(self):
        scene_map = {j: "|rig|" + j
                     for _, joints in builder.LIMBS for j in joints}
        self.assertEqual(builder.missing_limbs(scene_map), [])

    def test_reports_the_incomplete_limb(self):
        scene_map = {j: "|rig|" + j
                     for _, joints in builder.LIMBS for j in joints}
        del scene_map["hand_l"]
        self.assertEqual(builder.missing_limbs(scene_map), ["arm_l"])

    def test_empty_map_misses_everything(self):
        self.assertEqual(builder.missing_limbs({}),
                         ["arm_l", "arm_r", "leg_l", "leg_r"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd '/c/!!!Work/MayaScripts' && '/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe' -m unittest tests.test_builder
```

Expected: FAIL — `ImportError: cannot import name 'builder'`

- [ ] **Step 3: Write the implementation**

Create `maya_overrig/builder.py` with only what the tests need for now:

```python
"""Build OverRig setups on the skeleton the picker is bound to.

This module holds the policy -- which joints make up a limb, what gets
recorded, what a rebuild removes. All MEL knowledge lives in overrig.py.
"""

from collections import namedtuple

BUILD_SET = "RigPicker_build"

# Three joints per limb, in the order OverRig's IK proc requires:
# root, middle, end. Any other order produces a wrong chain.
LIMBS = (
    ("arm_l", ("upperarm_l", "lowerarm_l", "hand_l")),
    ("arm_r", ("upperarm_r", "lowerarm_r", "hand_r")),
    ("leg_l", ("thigh_l", "calf_l", "foot_l")),
    ("leg_r", ("thigh_r", "calf_r", "foot_r")),
)

BuildResult = namedtuple("BuildResult", "built skipped created removed message")


def limb_joints(scene_map):
    """Limbs whose joints all exist, as (limb name, [three long DAG paths]).

    `scene_map` is the picker's binding map, so prefixes and namespaces are
    already resolved by the time we get here.
    """
    resolved = []
    for name, joints in LIMBS:
        if all(joint in scene_map for joint in joints):
            resolved.append((name, [scene_map[joint] for joint in joints]))
    return resolved


def missing_limbs(scene_map):
    """Names of limbs that cannot be built because a joint is absent."""
    return [name for name, joints in LIMBS
            if not all(joint in scene_map for joint in joints)]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd '/c/!!!Work/MayaScripts' && '/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe' -m unittest tests.test_builder
```

Expected: PASS, 12 tests.

- [ ] **Step 5: Commit**

```bash
git add maya_overrig/builder.py tests/test_builder.py && git commit -m "feat(build): limb table and joint resolution"
```

---

### Task 2: OverRig MEL binding

**Files:**
- Create: `maya_overrig/overrig.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `MEL_PATH: str`, `KNOT_SET = "OverRig_knots"`, `SOURCE_SET = "OverRig_rig_objects"`, `IK_PROC = "apply_rebike_3_or_more_object_to_IK"`
  - `is_loaded() -> bool`
  - `ensure_loaded() -> bool`
  - `set_members(set_name: str) -> list[str]` — long DAG paths, `[]` if the set is absent
  - `build_ik(joint_paths) -> None`
  - `fast_bake(objects) -> None`
  - `delete_constraint_attributes(objects) -> None`
  - `frame_range() -> tuple[float, float]`

No unit tests: every function needs a live Maya. Task 3's verification script exercises all of them.

- [ ] **Step 1: Write the implementation**

Create `maya_overrig/overrig.py`:

```python
"""Thin binding to the OverRig MEL toolset.

Nothing in here decides anything -- it selects objects, calls global MEL procs
and reads OverRig's bookkeeping sets. Policy lives in builder.py.

Every OverRig proc is driven by the current selection, so each call here
selects first. That is OverRig's interface, not a choice.
"""

import os

import maya.cmds as cmds
import maya.mel as mel

# Where the user's Custom shelf button sources the toolset from. Used only as a
# fallback when the procs are not already in the session.
MEL_PATH = ("C:/!!!Work/Animations/Scripts/base_OverRig_scripts_V10_2_f1/"
            "base_OverRig_scripts.mel")

KNOT_SET = "OverRig_knots"
SOURCE_SET = "OverRig_rig_objects"

IK_PROC = "apply_rebike_3_or_more_object_to_IK"
BAKE_PROC = "apply_Fast_Bake"
CLEAN_PROC = "delete_constraint_attributes_on_objects"


def is_loaded():
    """True when OverRig's procs are available in this Maya session."""
    return bool(mel.eval('exists "{0}"'.format(IK_PROC)))


def ensure_loaded():
    """Source the toolset if it is not already in the session.

    Deliberately does not go looking around the disk: either the procs are
    there, or MEL_PATH is, or the caller reports failure and the user presses
    the OverRig shelf button.
    """
    if is_loaded():
        return True
    if not os.path.isfile(MEL_PATH):
        return False
    mel.eval('source "{0}";'.format(MEL_PATH))
    return is_loaded()


def set_members(set_name):
    """Long DAG paths of an object set's members, or [] if it does not exist."""
    if not cmds.objExists(set_name):
        return []
    members = cmds.sets(set_name, query=True) or []
    return cmds.ls(members, long=True) or []


def build_ik(joint_paths):
    """Run OverRig's FK-to-IK on exactly three joints, root to end.

    The proc takes no arguments and reads the selection, and the order of that
    selection decides the chain.
    """
    cmds.select(list(joint_paths), replace=True)
    mel.eval(IK_PROC)


def fast_bake(objects):
    """Bake the given objects using OverRig's own bake."""
    cmds.select(list(objects), replace=True)
    mel.eval(BAKE_PROC)


def delete_constraint_attributes(objects):
    """Strip the constraint channels OverRig adds to source objects."""
    cmds.select(list(objects), replace=True)
    mel.eval("{0}(`ls -sl`)".format(CLEAN_PROC))


def frame_range():
    """Playback range as (start, end)."""
    return (cmds.playbackOptions(query=True, minTime=True),
            cmds.playbackOptions(query=True, maxTime=True))
```

- [ ] **Step 2: Verify it imports and reports the toolset state**

Send this through the bridge:

```python
import sys
REPO = r"C:/!!!Work/MayaScripts"
if REPO not in sys.path:
    sys.path.append(REPO)
for name in [m for m in list(sys.modules) if m.startswith("maya_overrig")]:
    del sys.modules[name]

from maya_overrig import overrig
print("is_loaded    :", overrig.is_loaded())
print("ensure_loaded:", overrig.ensure_loaded())
print("frame_range  :", overrig.frame_range())
print("knots        :", len(overrig.set_members(overrig.KNOT_SET)))
print("sources      :", len(overrig.set_members(overrig.SOURCE_SET)))
```

Expected: `is_loaded True`, `frame_range (0.0, 30.0)`, both sets empty.

- [ ] **Step 3: Verify the unit suite still passes**

```bash
cd '/c/!!!Work/MayaScripts' && QT_QPA_PLATFORM=offscreen '/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe' -m unittest discover -s tests -t .
```

Expected: PASS, 79 tests.

- [ ] **Step 4: Commit**

```bash
git add maya_overrig/overrig.py && git commit -m "feat(build): thin binding to the OverRig MEL toolset"
```

---

### Task 3: Build, teardown and button wiring

**Files:**
- Modify: `maya_overrig/builder.py`
- Modify: `maya_overrig/picker_window.py`
- Create: `docs/superpowers/plans/verify_build.py`

**Interfaces:**
- Consumes: `LIMBS`, `limb_joints`, `missing_limbs`, `BUILD_SET`, `BuildResult` from Task 1; all of `overrig` from Task 2
- Produces:
  - `builder.has_build() -> bool`
  - `builder.build(scene_map) -> BuildResult`
  - `builder.teardown(scene_map) -> BuildResult`
  - `PickerWindow.build_rig()` wired to the `Build` button

- [ ] **Step 1: Extend `builder.py`**

Add to the imports at the top of `maya_overrig/builder.py`:

```python
import maya.cmds as cmds

from maya_overrig import overrig
```

Append to `maya_overrig/builder.py`:

```python
def _ensure_build_set():
    if not cmds.objExists(BUILD_SET):
        cmds.sets(name=BUILD_SET, empty=True)
    return BUILD_SET


def has_build():
    """True when this tool has a build recorded in the scene."""
    return bool(overrig.set_members(BUILD_SET))


def teardown(scene_map):
    """Remove only what this tool created, using OverRig's own pieces.

    Never calls barn_fast_bake_source_obj_and_delete_knots(): that is
    scene-global and would take the user's hand-made OverRig setups with it.
    """
    knots = [k for k in overrig.set_members(BUILD_SET) if cmds.objExists(k)]

    sources = [path for _, joints in limb_joints(scene_map) for path in joints]
    sources = [s for s in sources if cmds.objExists(s)]
    if sources:
        overrig.fast_bake(sources)
        overrig.delete_constraint_attributes(sources)

    if knots:
        cmds.delete(knots)
    if cmds.objExists(BUILD_SET):
        cmds.delete(BUILD_SET)

    return BuildResult([], [], 0, len(knots),
                       "Removed {0} node(s)".format(len(knots)))


def build(scene_map):
    """Build IK on every resolvable limb, replacing any previous build."""
    if not overrig.ensure_loaded():
        return BuildResult(
            [], [], 0, 0,
            "OverRig is not loaded - press the OverRig shelf button "
            "(looked for {0})".format(overrig.MEL_PATH))

    resolvable = limb_joints(scene_map)
    if not resolvable:
        return BuildResult([], [name for name, _ in LIMBS], 0, 0,
                           "No limb joints found on the bound skeleton")

    start, end = overrig.frame_range()
    warning = ""
    if end - start < 1:
        warning = "  (timeline is a single frame - nothing to bake over)"

    built = []
    created = []
    removed = 0

    cmds.undoInfo(openChunk=True, chunkName="Rig Picker build")
    try:
        if has_build():
            removed = teardown(scene_map).removed

        for name, joints in resolvable:
            before = set(overrig.set_members(overrig.KNOT_SET))
            overrig.build_ik(joints)
            after = set(overrig.set_members(overrig.KNOT_SET))

            fresh = sorted(after - before)
            if fresh:
                cmds.sets(fresh, addElement=_ensure_build_set())
                created.extend(fresh)
            built.append(name)
    finally:
        cmds.undoInfo(closeChunk=True)

    skipped = missing_limbs(scene_map)
    message = "Built {0} limb(s), {1} node(s) created".format(
        len(built), len(created))
    if removed:
        message += ", {0} replaced".format(removed)
    if skipped:
        message += ". Skipped: " + ", ".join(skipped)
    return BuildResult(built, skipped, len(created), removed, message + warning)
```

- [ ] **Step 2: Wire the button in `picker_window.py`**

Add to the imports:

```python
from maya_overrig import builder
```

Replace the disabled-stub loop in `_build_toolbar`:

```python
        for label in ("Build", "Bake+Delete"):
            button = QtWidgets.QPushButton(label, bar)
            button.setStyleSheet(_BUTTON_STYLE)
            button.setEnabled(False)
            button.setToolTip("Not implemented yet")
            row.addWidget(button)
```

with:

```python
        self.build_button = QtWidgets.QPushButton("Build", bar)
        self.build_button.setStyleSheet(_BUTTON_STYLE)
        self.build_button.setToolTip(
            "Create IK on both arms and both legs.\n"
            "Pressing again rebuilds from scratch.")
        self.build_button.clicked.connect(lambda _checked=False: self.build_rig())
        row.addWidget(self.build_button)

        teardown_button = QtWidgets.QPushButton("Bake+Delete", bar)
        teardown_button.setStyleSheet(_BUTTON_STYLE)
        teardown_button.setEnabled(False)
        teardown_button.setToolTip("Not implemented yet")
        row.addWidget(teardown_button)
```

Add this method to `PickerWindow`, next to `apply_selection`:

```python
    def build_rig(self):
        """Create IK on both arms and both legs of the bound skeleton."""
        if not self._scene_map:
            self.status.showMessage(_UNBOUND_MESSAGE)
            return

        self.build_button.setEnabled(False)
        try:
            result = builder.build(self._scene_map)
        finally:
            self.build_button.setEnabled(True)

        self.status.showMessage(result.message)
        self.sync_from_scene()
```

- [ ] **Step 3: Run the unit suite**

```bash
cd '/c/!!!Work/MayaScripts' && QT_QPA_PLATFORM=offscreen '/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe' -m unittest discover -s tests -t .
```

Expected: PASS, 79 tests. The new code needs Maya and is covered by Step 4.

- [ ] **Step 4: Write the live verification script**

Create `docs/superpowers/plans/verify_build.py`:

```python
"""Live checks for Build. Run inside Maya.

Creates a decoy OverRig knot outside our manifest and proves a rebuild leaves
it alone -- that is the check that justifies not using OverRig's global
teardown.
"""

import sys

REPO = r"C:/!!!Work/MayaScripts"
if REPO not in sys.path:
    sys.path.append(REPO)

for name in [m for m in list(sys.modules) if m.startswith("maya_overrig")]:
    del sys.modules[name]

import maya.cmds as cmds

import maya_overrig
from maya_overrig import builder, overrig

failures = []


def check(label, condition, detail=""):
    print("%-54s %s %s" % (label, "OK" if condition else "FAIL", detail))
    if not condition:
        failures.append(label)


check("OverRig available", overrig.ensure_loaded())

window = maya_overrig.show_picker()
check("picker bound", bool(window._scene_map), str(window.bound_root()))

joints_before = len(cmds.ls(type="joint"))

# A knot the user "made by hand", deliberately outside our manifest.
decoy = cmds.spaceLocator(name="decoy_manual_knot")[0]
if not cmds.objExists(overrig.KNOT_SET):
    cmds.sets(name=overrig.KNOT_SET, empty=True)
cmds.sets(decoy, addElement=overrig.KNOT_SET)

result = builder.build(window._scene_map)
print("\n  build says: %s\n" % result.message)

check("all four limbs built", sorted(result.built) ==
      ["arm_l", "arm_r", "leg_l", "leg_r"], str(result.built))
check("nodes were created", result.created > 0, str(result.created))
check("manifest set exists", cmds.objExists(builder.BUILD_SET))

manifest = overrig.set_members(builder.BUILD_SET)
check("manifest is not empty", len(manifest) > 0, str(len(manifest)))
check("decoy is NOT in our manifest",
      not any(decoy in m for m in manifest))

prefix = window._prefix
for suffix in ("_IK_feet", "_IK_knee"):
    hits = cmds.ls("*" + suffix, long=True) or []
    check("created %s nodes" % suffix, len(hits) >= 4,
          "%d found" % len(hits))

first_count = len(cmds.ls(long=True))
second = builder.build(window._scene_map)
check("second Build rebuilt rather than doubled",
      second.removed > 0, "removed %d" % second.removed)
check("node count did not run away",
      abs(len(cmds.ls(long=True)) - first_count) < 5,
      "%d -> %d" % (first_count, len(cmds.ls(long=True))))

check("decoy survived the rebuild", cmds.objExists(decoy))

builder.teardown(window._scene_map)
check("teardown removed the manifest set",
      not cmds.objExists(builder.BUILD_SET))
check("decoy still alive after teardown", cmds.objExists(decoy))

if cmds.objExists(decoy):
    cmds.delete(decoy)
if cmds.objExists(overrig.KNOT_SET) and not (cmds.sets(overrig.KNOT_SET, query=True) or []):
    cmds.delete(overrig.KNOT_SET)

check("joint count unchanged", len(cmds.ls(type="joint")) == joints_before,
      "before %d after %d" % (joints_before, len(cmds.ls(type="joint"))))

window.close()
print("\n%s" % ("ALL CHECKS PASSED" if not failures
                else "FAILURES: %s" % failures))
```

- [ ] **Step 5: Run it through the bridge**

Copy into the bridge's `code.py` and send. Expected: every line `OK`.

If a limb fails inside OverRig, read the traceback before changing anything —
the most likely causes are a selection order mistake or a timeline range of zero
length, both of which are recorded in the spec.

- [ ] **Step 6: Screenshot the result and commit**

Grab the picker with `window.grab().save(path)` and confirm the status line
reports four limbs. Then:

```bash
git add maya_overrig docs/superpowers/plans/verify_build.py && git commit -m "feat(build): create IK arms and legs from the Build button"
```

---

## Self-Review

**Spec coverage**

| Spec requirement | Task |
|---|---|
| Build covers all four limbs, ignores selection | 1 (table), 3 (`build`) |
| Three joints per limb, root-middle-end order | 1, enforced by `test_order_is_root_middle_end` |
| Names resolved through the picker's `_scene_map` | 1 (`limb_joints`), 3 (window passes it) |
| Repeat press rebuilds | 3 (`build` calls `teardown` when `has_build()`) |
| Teardown scoped to our manifest | 3 (`teardown`), proven by the decoy check |
| Never call the global OverRig teardown | 3 — absent by construction, decoy check proves it |
| Manifest built by diffing `OverRig_knots` | 3 (`build`) |
| Single undo chunk | 3 (`undoInfo openChunk`/`closeChunk` in `finally`) |
| Refuse when not bound | 3 (`build_rig`) |
| Refuse when OverRig unavailable, name the path | 3 (`build`) |
| Skip limbs with missing joints, report them | 1 (`missing_limbs`), 3 (message) |
| Refuse when no limb resolvable | 3 (`build`) |
| Warn on a single-frame timeline | 3 (`build`) |
| Abort cleanly if a limb raises | 3 — `finally` closes the chunk, so `Ctrl+Z` unwinds |
| `Bake+Delete` stays disabled | 3 (Step 2) |

No gaps.

**Placeholder scan:** none — every step carries real code or a real command.

**Type consistency:** `limb_joints` / `missing_limbs` / `has_build` / `build` /
`teardown` / `set_members` / `build_ik` / `fast_bake` /
`delete_constraint_attributes` / `frame_range` / `ensure_loaded` / `is_loaded`
are spelled identically everywhere. `BuildResult` fields are
`built skipped created removed message` throughout; `built` and `skipped` are
lists of limb names, `created` and `removed` are counts.

One note carried into Task 3: `teardown` returns a `BuildResult` whose `removed`
field is the count `build` reports, so the two agree on what "replaced" means.
