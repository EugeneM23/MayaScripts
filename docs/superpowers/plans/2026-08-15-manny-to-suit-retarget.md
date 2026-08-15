# Manny → protective-suit retarget Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a constraint rig that drives the referenced protective-suit
skeleton from the UE5 Manny skeleton in the open scene, keeping the suit's own
silhouette on the body and copying Manny's grip absolutely on the fingers.

**Architecture:** One root-level single-file tool, `maya_retarget.py`, in the
flat `maya_*.py` convention (pure `maya.cmds`, no Qt, no package). The bone
mapping is a pure function over two lists of names so it is unit-testable
without a Maya session; everything that touches Maya is a thin wrapper around
it. Created constraints are recorded in an `objectSet` and torn down by
membership, never by name.

**Tech Stack:** Python 3 / `maya.cmds` (Maya 2027), `unittest` under `mayapy`,
live verification over the Maya command port on `127.0.0.1:7001`.

## Global Constraints

- Source skeleton: `SKM_Manny_Simple` (group) → `root` (joint), 93 joints.
- Target skeleton: `Mesh_protective_suit:root` (**group**, not a joint), 67
  joints, a loaded **reference** — never re-parent or rename anything in it.
- Side offset lives on the target group's `translateX` = `145.017` and must
  survive the build.
- Spine map is fixed: `spine_01→spine_02`, `spine_02→spine_04`,
  `spine_03→spine_05` (suit → Manny).
- Finger bones match `^(thumb|index|middle|ring|pinky)_\d+_[lr]$` and default to
  `maintainOffset=False`.
- **No `parentConstraint` on anything carrying the side offset** — it stores its
  offset in the source's space and makes the suit orbit Manny on a turn. Pelvis
  and the two ik roots use `point` + `orient`.
- Test command:
  `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v`
- No `2>&1` on `mayapy` in PowerShell; write git commit messages to a file and
  use `git commit -F`.

## File Structure

| File | Responsibility |
|---|---|
| `maya_retarget.py` (create) | the whole tool: name tables, pure `build_bone_map`, Maya-side build/remove/offset, small `cmds` UI |
| `tests/test_retarget.py` (create) | unit tests for `build_bone_map` and the name tables, including the real 67/93-name fixtures |
| `docs/superpowers/plans/verify_retarget.py` (create) | live proof over the command port |

---

### Task 1: Pure bone mapping

**Files:**
- Create: `maya_retarget.py`
- Test: `tests/test_retarget.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `SPINE_MAP: dict[str, str]`, `IK_HELPERS: tuple[str, ...]`,
  `IK_DRIVEN: tuple[tuple[str, str], ...]`, `FINGER_RE: re.Pattern`,
  `is_finger(name: str) -> bool`,
  `build_bone_map(target_names, source_names, finger_mode="absolute") ->
  (dict[str, tuple[str, str]], list[str])` — mapping is
  `{target_short_name: (source_short_name, mode)}` with mode in
  `{"offset", "absolute"}`; the second return is the sorted list of target names
  with no source.

- [ ] **Step 1: Write the failing test**

Create `tests/test_retarget.py`:

```python
import unittest

import maya_retarget as mr

# The real scene, measured 2026-08-15. Suit joints under Mesh_protective_suit:root.
SUIT = [
    "ik_foot_root", "ik_foot_l", "ik_foot_r",
    "ik_hand_root", "ik_hand_gun", "ik_hand_l", "ik_hand_r",
    "pelvis", "spine_01", "spine_02", "spine_03", "neck_01", "head",
    "thigh_l", "thigh_twist_01_l", "calf_l", "calf_twist_01_l", "foot_l", "ball_l",
    "thigh_r", "thigh_twist_01_r", "calf_r", "calf_twist_01_r", "foot_r", "ball_r",
    "clavicle_l", "upperarm_l", "upperarm_twist_01_l", "lowerarm_l",
    "lowerarm_twist_01_l", "hand_l",
    "clavicle_r", "upperarm_r", "upperarm_twist_01_r", "lowerarm_r",
    "lowerarm_twist_01_r", "hand_r",
]
for _side in ("l", "r"):
    for _f in ("thumb", "index", "middle", "ring", "pinky"):
        for _i in ("01", "02", "03"):
            SUIT.append("%s_%s_%s" % (_f, _i, _side))

MANNY = SUIT + [
    "root", "camera_root", "camera_bone", "center_of_mass", "interaction",
    "spine_04", "spine_05", "neck_02", "weapon_l", "weapon_r",
    "thigh_twist_02_l", "thigh_twist_02_r", "calf_twist_02_l", "calf_twist_02_r",
    "upperarm_twist_02_l", "upperarm_twist_02_r",
    "lowerarm_twist_02_l", "lowerarm_twist_02_r",
    "index_metacarpal_l", "index_metacarpal_r",
    "middle_metacarpal_l", "middle_metacarpal_r",
    "ring_metacarpal_l", "ring_metacarpal_r",
    "pinky_metacarpal_l", "pinky_metacarpal_r",
]


class TestFixtures(unittest.TestCase):

    def test_the_fixtures_match_the_measured_scene(self):
        self.assertEqual(len(SUIT), 67)
        self.assertEqual(len(MANNY), 93)


class TestIsFinger(unittest.TestCase):

    def test_finger_bones_are_fingers(self):
        for name in ("thumb_01_l", "index_02_r", "middle_03_l",
                     "ring_01_r", "pinky_03_l"):
            self.assertTrue(mr.is_finger(name), name)

    def test_metacarpals_are_not_fingers(self):
        for name in ("index_metacarpal_l", "pinky_metacarpal_r"):
            self.assertFalse(mr.is_finger(name), name)

    def test_body_bones_are_not_fingers(self):
        for name in ("hand_l", "spine_01", "ball_r", "upperarm_twist_01_l"):
            self.assertFalse(mr.is_finger(name), name)


class TestBuildBoneMap(unittest.TestCase):

    def setUp(self):
        self.mapping, self.unmatched = mr.build_bone_map(SUIT, MANNY)

    def test_every_suit_bone_is_matched(self):
        self.assertEqual(self.unmatched, [])

    def test_ik_helpers_are_not_in_the_mapping(self):
        for name in mr.IK_HELPERS:
            self.assertNotIn(name, self.mapping)

    def test_mapping_covers_the_sixty_body_joints(self):
        self.assertEqual(len(self.mapping), 60)

    def test_spine_uses_the_semantic_map_not_the_name(self):
        self.assertEqual(self.mapping["spine_01"][0], "spine_02")
        self.assertEqual(self.mapping["spine_02"][0], "spine_04")
        self.assertEqual(self.mapping["spine_03"][0], "spine_05")

    def test_non_spine_bones_map_to_their_name_twin(self):
        for name in ("pelvis", "head", "hand_l", "ball_r", "clavicle_l"):
            self.assertEqual(self.mapping[name][0], name)

    def test_fingers_default_to_absolute(self):
        self.assertEqual(self.mapping["index_01_r"][1], "absolute")
        self.assertEqual(self.mapping["thumb_03_l"][1], "absolute")

    def test_body_bones_are_offset_mode(self):
        for name in ("pelvis", "spine_03", "hand_l", "foot_r"):
            self.assertEqual(self.mapping[name][1], "offset")

    def test_finger_mode_offset_switches_all_thirty_fingers(self):
        mapping, _ = mr.build_bone_map(SUIT, MANNY, finger_mode="offset")
        fingers = [n for n in mapping if mr.is_finger(n)]
        self.assertEqual(len(fingers), 30)
        for name in fingers:
            self.assertEqual(mapping[name][1], "offset")

    def test_an_unmatched_target_is_reported_not_mapped(self):
        mapping, unmatched = mr.build_bone_map(["pelvis", "tail_01"], MANNY)
        self.assertEqual(unmatched, ["tail_01"])
        self.assertNotIn("tail_01", mapping)

    def test_a_missing_spine_twin_is_reported(self):
        mapping, unmatched = mr.build_bone_map(["spine_02"], ["spine_02"])
        self.assertEqual(unmatched, ["spine_02"])

    def test_an_unknown_finger_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            mr.build_bone_map(SUIT, MANNY, finger_mode="sideways")


class TestIkTable(unittest.TestCase):

    def test_ik_driven_pairs_stay_inside_the_suit(self):
        self.assertEqual(mr.IK_DRIVEN, (
            ("ik_foot_l", "foot_l"),
            ("ik_foot_r", "foot_r"),
            ("ik_hand_gun", "hand_r"),
            ("ik_hand_l", "hand_l"),
        ))

    def test_ik_hand_r_is_not_driven_it_inherits(self):
        driven = [name for name, _ in mr.IK_DRIVEN]
        self.assertNotIn("ik_hand_r", driven)
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd '/c/!!!Work/MayaScripts' && '/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe' -m unittest tests.test_retarget -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'maya_retarget'`.

- [ ] **Step 3: Write the module's pure half**

Create `maya_retarget.py` with the docstring, tables and pure function only
(the Maya half arrives in Task 2):

```python
"""
Manny -> protective-suit retarget.

Drives the referenced Mesh_protective_suit skeleton from SKM_Manny_Simple with
constraints: the body keeps the suit's own rest pose and receives Manny's
relative world rotation, the fingers copy Manny's grip absolutely.

Design: docs/superpowers/specs/2026-08-15-manny-to-suit-retarget-design.md

Run in Maya (Script Editor, Python tab):
    import sys; sys.path.append(r"C:/!!!Work/MayaScripts")
    import maya_retarget; maya_retarget.build_retarget()
"""

import re

import maya.cmds as cmds

SOURCE_ROOT = "SKM_Manny_Simple"
SOURCE_SKEL = "root"
TARGET_ROOT = "Mesh_protective_suit:root"
RETARGET_SET = "retarget_manny_to_suit"

# The suit hangs clavicles and neck on spine_03, Manny on spine_05: those are
# the same bone. Matching by name instead costs 3.5 / 14.1 / 5.9 degrees of
# rest-pose error against 0.00 / 2.75 / 0.65 for this map.
SPINE_MAP = {
    "spine_01": "spine_02",
    "spine_02": "spine_04",
    "spine_03": "spine_05",
}

# Export helpers. Not retargeted from Manny - driven from the suit's own bones,
# exactly as Manny drives its own.
IK_HELPERS = (
    "ik_foot_root", "ik_foot_l", "ik_foot_r",
    "ik_hand_root", "ik_hand_gun", "ik_hand_l", "ik_hand_r",
)
IK_ROOTS = ("ik_foot_root", "ik_hand_root")
IK_DRIVEN = (
    ("ik_foot_l", "foot_l"),
    ("ik_foot_r", "foot_r"),
    ("ik_hand_gun", "hand_r"),
    ("ik_hand_l", "hand_l"),
)

FINGER_RE = re.compile(r"^(thumb|index|middle|ring|pinky)_\d+_[lr]$")

OFFSET = "offset"
ABSOLUTE = "absolute"
MODES = (OFFSET, ABSOLUTE)


def is_finger(name):
    """True for a suit finger bone such as index_01_l, false for metacarpals."""
    return FINGER_RE.match(name) is not None


def build_bone_map(target_names, source_names, finger_mode=ABSOLUTE):
    """Map suit bone -> (Manny bone, mode), plus the target names with no source.

    Pure: takes the two skeletons as lists of short names, touches no scene.
    """
    if finger_mode not in MODES:
        raise ValueError(
            "finger_mode must be one of %s, got %r" % (list(MODES), finger_mode))

    available = set(source_names)
    mapping = {}
    unmatched = []
    for name in target_names:
        if name in IK_HELPERS:
            continue
        source = SPINE_MAP.get(name, name)
        if source not in available:
            unmatched.append(name)
            continue
        mapping[name] = (source, finger_mode if is_finger(name) else OFFSET)
    return mapping, sorted(unmatched)
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd '/c/!!!Work/MayaScripts' && '/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe' -m unittest tests.test_retarget -v
```

Expected: PASS, 16 tests.

- [ ] **Step 5: Commit**

```bash
git add maya_retarget.py tests/test_retarget.py docs/superpowers/specs/2026-08-15-manny-to-suit-retarget-design.md docs/superpowers/plans/2026-08-15-manny-to-suit-retarget.md
git commit -F commit-msg.txt
```

with `commit-msg.txt` holding:

```
feat(retarget): pure Manny->suit bone map with the semantic spine

The suit is a UE4-schema skeleton, Manny a UE5 one: matching spine bones
by name costs up to 14 degrees of rest-pose error because the suit's
chest is spine_03 and Manny's is spine_05. SPINE_MAP fixes the three
pairs and drops the error to 2.75 degrees at worst.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

### Task 2: Build and remove the constraint rig

**Files:**
- Modify: `maya_retarget.py` (append after `build_bone_map`)

**Interfaces:**
- Consumes: `build_bone_map`, `IK_HELPERS`, `IK_ROOTS`, `IK_DRIVEN`,
  `SOURCE_ROOT`, `SOURCE_SKEL`, `TARGET_ROOT`, `RETARGET_SET`, `OFFSET`,
  `ABSOLUTE`.
- Produces: `joints_under(root) -> dict[str, str]`,
  `build_retarget(source_root=..., target_root=..., finger_mode="absolute",
  include_ik_helpers=True) -> dict`, `remove_retarget(retarget_set=...) -> int`.

The returned dict has keys `constraints` (int), `bones` (int),
`unmatched` (list), `side_offset` (float).

- [ ] **Step 1: Add the Maya half**

Append to `maya_retarget.py`:

```python
def joints_under(root):
    """{short name, namespace stripped: full DAG path} for joints under root."""
    found = {}
    for path in cmds.ls(root, dag=True, type="joint", long=True) or []:
        found[path.split("|")[-1].split(":")[-1]] = path
    return found


def _record(created, nodes):
    created.extend(n for n in (nodes or []) if n)


def build_retarget(source_root=SOURCE_ROOT, target_root=TARGET_ROOT,
                   finger_mode=ABSOLUTE, include_ik_helpers=True,
                   retarget_set=RETARGET_SET):
    """Constrain the suit skeleton to Manny's. Returns a summary dict."""
    for node in (source_root, target_root):
        if not cmds.objExists(node):
            raise RuntimeError("not in the scene: %s" % node)
    if cmds.objExists(retarget_set):
        raise RuntimeError(
            "%s already exists - run remove_retarget() first" % retarget_set)

    source = joints_under(source_root)
    target = joints_under(target_root)
    if SOURCE_SKEL not in source:
        raise RuntimeError("no %r joint under %s" % (SOURCE_SKEL, source_root))

    mapping, unmatched = build_bone_map(sorted(target), sorted(source),
                                        finger_mode)
    side_offset = cmds.getAttr(target_root + ".translateX")
    created = []

    cmds.undoInfo(openChunk=True, chunkName="build_retarget")
    try:
        # Pelvis carries the world position. point + orient, never parent:
        # a parent constraint stores its offset in the source's space and
        # swings the suit through an arc when Manny turns on the spot.
        _record(created, cmds.pointConstraint(
            source["pelvis"], target["pelvis"], maintainOffset=True))

        for name in sorted(mapping):
            src_name, mode = mapping[name]
            _record(created, cmds.orientConstraint(
                source[src_name], target[name],
                maintainOffset=(mode == OFFSET)))

        if include_ik_helpers:
            for name in IK_ROOTS:
                if name not in target:
                    continue
                _record(created, cmds.pointConstraint(
                    source[SOURCE_SKEL], target[name], maintainOffset=True))
                _record(created, cmds.orientConstraint(
                    source[SOURCE_SKEL], target[name], maintainOffset=True))
            # Both ends live inside the suit, so no side offset is involved
            # and parentConstraint is safe here - it is what Manny uses.
            for name, driver in IK_DRIVEN:
                if name in target and driver in target:
                    _record(created, cmds.parentConstraint(
                        target[driver], target[name], maintainOffset=True))

        cmds.sets(created, name=retarget_set)
        cmds.addAttr(retarget_set, longName="retargetSideOffset",
                     attributeType="double")
        cmds.setAttr(retarget_set + ".retargetSideOffset", side_offset)
    finally:
        cmds.undoInfo(closeChunk=True)

    summary = {"constraints": len(created), "bones": len(mapping),
               "unmatched": unmatched, "side_offset": side_offset}
    print("retarget: %d constraints over %d bones, side offset %.3f cm"
          % (summary["constraints"], summary["bones"], side_offset))
    if unmatched:
        print("retarget: UNMATCHED target bones: %s" % ", ".join(unmatched))
    return summary


def remove_retarget(retarget_set=RETARGET_SET):
    """Delete every node this tool created. Returns how many were deleted."""
    if not cmds.objExists(retarget_set):
        print("retarget: nothing to remove")
        return 0
    members = cmds.sets(retarget_set, query=True) or []
    alive = [m for m in members if cmds.objExists(m)]
    cmds.undoInfo(openChunk=True, chunkName="remove_retarget")
    try:
        if alive:
            cmds.delete(alive)
        cmds.delete(retarget_set)
    finally:
        cmds.undoInfo(closeChunk=True)
    print("retarget: removed %d constraint node(s)" % len(alive))
    return len(alive)
```

- [ ] **Step 2: Re-run the unit tests — the pure half must be untouched**

```bash
cd '/c/!!!Work/MayaScripts' && '/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe' -m unittest tests.test_retarget -v
```

Expected: PASS, still 16 tests.

- [ ] **Step 3: Build it for real in the user's open scene**

Send over the bridge:

```python
import sys
if r"C:/!!!Work/MayaScripts" not in sys.path:
    sys.path.append(r"C:/!!!Work/MayaScripts")
import maya_retarget
try:
    import importlib
    importlib.reload(maya_retarget)
except Exception:
    pass
maya_retarget.remove_retarget()
print(maya_retarget.build_retarget())
```

Expected: `60 bones`, `unmatched: []`, `side offset 145.017 cm`, and a
constraint count of 60 orient + 1 point + 4 (ik roots) + 4 (ik driven) = 69.

- [ ] **Step 4: Commit**

```bash
git add maya_retarget.py
git commit -F commit-msg.txt
```

with `commit-msg.txt` holding:

```
feat(retarget): build and tear down the Manny->suit constraint rig

Pelvis and the ik roots go through point + orient rather than a parent
constraint: a parent constraint stores its offset in the source's space,
so with the suit held 145 cm to the side Manny turning on the spot would
swing it through an arc instead of turning it in place.

Teardown is by objectSet membership, never by name.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

### Task 3: Side offset control and UI

**Files:**
- Modify: `maya_retarget.py` (append after `remove_retarget`)

**Interfaces:**
- Consumes: `RETARGET_SET`, `build_retarget`, `remove_retarget`.
- Produces: `set_side_offset(x, retarget_set=RETARGET_SET) -> float`,
  `show_retarget_ui() -> str`.

- [ ] **Step 1: Add the offset control and the UI**

Append to `maya_retarget.py`:

```python
def set_side_offset(x, retarget_set=RETARGET_SET):
    """Move the suit sideways relative to Manny. 0 puts it exactly inside him.

    Rewrites the world offset held by every point constraint, so it costs no
    rebuild and keeps each bone's own rest delta in Y and Z.
    """
    if not cmds.objExists(retarget_set):
        raise RuntimeError("no retarget in the scene - run build_retarget()")
    current = cmds.getAttr(retarget_set + ".retargetSideOffset")
    delta = x - current
    moved = 0
    for member in cmds.sets(retarget_set, query=True) or []:
        if not cmds.objExists(member):
            continue
        if cmds.nodeType(member) != "pointConstraint":
            continue
        attr = member + ".offsetX"
        cmds.setAttr(attr, cmds.getAttr(attr) + delta)
        moved += 1
    cmds.setAttr(retarget_set + ".retargetSideOffset", x)
    print("retarget: side offset %.3f -> %.3f cm on %d constraint(s)"
          % (current, x, moved))
    return x


def _ui_build(*_args):
    fingers = ABSOLUTE if cmds.checkBox("retargetFingerAbs", query=True,
                                        value=True) else OFFSET
    remove_retarget()
    build_retarget(finger_mode=fingers)


def _ui_overlay(*_args):
    set_side_offset(0.0)


def _ui_apart(*_args):
    set_side_offset(cmds.getAttr(TARGET_ROOT + ".translateX"))


def show_retarget_ui():
    """Open the retarget window."""
    win = "mannyToSuitRetargetWin"
    if cmds.window(win, exists=True):
        cmds.deleteUI(win)

    cmds.window(win, title="Manny -> Suit Retarget",
                widthHeight=(320, 200), sizeable=True)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=6,
                      columnOffset=("both", 10))
    cmds.separator(height=8, style="none")
    cmds.text(label="SKM_Manny_Simple  ->  Mesh_protective_suit",
              font="boldLabelFont", align="center")
    cmds.separator(height=4, style="none")
    cmds.checkBox("retargetFingerAbs",
                  label="Fingers copy Manny absolutely (grip transfers)",
                  value=True)
    cmds.button(label="Build Retarget", height=36,
                backgroundColor=(0.5, 0.75, 0.5), command=_ui_build)
    cmds.button(label="Remove Retarget", height=28,
                backgroundColor=(0.8, 0.55, 0.5),
                command=lambda *a: remove_retarget())
    cmds.separator(height=6, style="in")
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1,
                   columnWidth2=(150, 150))
    cmds.button(label="Overlay on Manny", command=_ui_overlay)
    cmds.button(label="Stand Apart", command=_ui_apart)
    cmds.setParent("..")
    cmds.showWindow(win)
    return win


if __name__ == "__main__":
    show_retarget_ui()
```

- [ ] **Step 2: Re-run the unit tests**

```bash
cd '/c/!!!Work/MayaScripts' && '/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe' -m unittest discover -s tests -t . -v
```

Expected: PASS, the whole suite (265 existing + 16 new = 281).

- [ ] **Step 3: Exercise the offset live**

Send over the bridge: read the suit pelvis world X, call `set_side_offset(0.0)`,
wiggle time to settle, read it again, then `set_side_offset(145.017)` and read a
third time.

Expected: the pelvis X moves to Manny's pelvis X (0.0 ± 0.01) and back to
145.017 ± 0.01.

- [ ] **Step 4: Commit**

```bash
git add maya_retarget.py
git commit -F commit-msg.txt
```

with `commit-msg.txt` holding:

```
feat(retarget): side-offset control and the tool window

set_side_offset rewrites the point constraints' world offsets, so putting
the suit inside Manny for a bone-by-bone check and moving it back out
costs no rebuild and preserves each bone's own rest delta in Y and Z.

The UI auto-opens only under __main__, so the module stays importable by
the unit tests.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

### Task 4: Live verification

**Files:**
- Create: `docs/superpowers/plans/verify_retarget.py`

**Interfaces:**
- Consumes: the built retarget rig in the open scene.
- Produces: nothing importable — it prints a PASS/FAIL table.

The two predicates are exact, not approximate, and that is what makes this
worth running:

- **offset mode:** `orientConstraint(mo=True)` gives
  `target_after · target_before⁻¹ == source_after · source_before⁻¹` — the
  world rotation *delta* transfers identically.
- **absolute mode:** `target_world == source_world`.
- **no arc:** with Manny turned 90° on the spot, the suit's pelvis world
  position must stay at Manny's pelvis plus the *unrotated* world offset.

- [ ] **Step 1: Write the verify script**

Create `docs/superpowers/plans/verify_retarget.py`:

```python
"""Live proof that the Manny -> suit retarget transfers motion exactly.

Send through the command port. Bridge hygiene (CLAUDE.md): never cmds.undo()
here, disable autoKey around pokes, wiggle time before reading, and restore
what was read rather than writing literal rest values.
"""
import math
from contextlib import contextmanager

import maya.cmds as cmds
import maya.api.OpenMaya as om

NS = "Mesh_protective_suit:"
TOL_DEG = 0.01
TOL_CM = 0.01

results = []


def check(label, ok, detail):
    results.append((label, ok, detail))
    print("%-46s %s  %s" % (label, "PASS" if ok else "FAIL", detail))


def wmat(obj):
    sel = om.MSelectionList()
    sel.add(obj)
    return sel.getDagPath(0).inclusiveMatrix()


def rot_only(m):
    t = om.MTransformationMatrix(m)
    t.setTranslation(om.MVector(0, 0, 0), om.MSpace.kTransform)
    t.setScale([1, 1, 1], om.MSpace.kTransform)
    return t.asMatrix()


def angle_between(a, b):
    d = rot_only(a).inverse() * rot_only(b)
    tr = d[0] + d[5] + d[10]
    return math.degrees(math.acos(max(-1.0, min(1.0, (tr - 1.0) / 2.0)))) 


def settle():
    """Interactive reads lie without a time change (CLAUDE.md trap 14)."""
    now = cmds.currentTime(query=True)
    cmds.currentTime(now + 1, update=True)
    cmds.currentTime(now, update=True)
    cmds.refresh()


@contextmanager
def posed(pokes):
    """Apply {node.attr: delta}, restore exactly what was read. autoKey off."""
    auto = cmds.autoKeyframe(query=True, state=True)
    cmds.autoKeyframe(state=False)
    before = {}
    try:
        for attr, delta in pokes.items():
            before[attr] = cmds.getAttr(attr)
            cmds.setAttr(attr, before[attr] + delta)
        settle()
        yield
    finally:
        for attr, value in before.items():
            cmds.setAttr(attr, value)
        settle()
        cmds.autoKeyframe(state=auto)


OFFSET_BONES = ["pelvis", "spine_03", "clavicle_l", "upperarm_l", "lowerarm_l",
                "hand_l", "thigh_r", "calf_r", "foot_r", "head"]
FINGER_BONES = ["index_01_r", "index_02_r", "thumb_01_l", "pinky_03_r",
                "middle_02_l"]
MAP = {"spine_03": "spine_05"}

POKES = {
    "pelvis.rotateY": 12.0,
    "spine_02.rotateZ": 9.0,
    "spine_04.rotateZ": 11.0,
    "clavicle_l.rotateY": 8.0,
    "upperarm_l.rotateZ": 25.0,
    "lowerarm_l.rotateZ": -30.0,
    "thigh_r.rotateZ": 18.0,
    "calf_r.rotateZ": -22.0,
    "neck_01.rotateZ": 7.0,
    "index_01_r.rotateZ": 20.0,
    "thumb_01_l.rotateY": 15.0,
}

print("=== RETARGET VERIFY ===")
if not cmds.objExists("retarget_manny_to_suit"):
    print("FAIL: no retarget rig in the scene")
else:
    settle()
    rest = {}
    for bone in OFFSET_BONES:
        rest[bone] = (wmat(MAP.get(bone, bone)), wmat(NS + bone))

    with posed(POKES):
        print()
        print("--- offset mode: world rotation DELTA must transfer exactly ---")
        for bone in OFFSET_BONES:
            src_rest, tgt_rest = rest[bone]
            src_now, tgt_now = wmat(MAP.get(bone, bone)), wmat(NS + bone)
            src_delta = rot_only(src_now) * rot_only(src_rest).inverse()
            tgt_delta = rot_only(tgt_now) * rot_only(tgt_rest).inverse()
            err = angle_between(src_delta, tgt_delta)
            check("delta  %s" % bone, err < TOL_DEG, "err %.5f deg" % err)

        print()
        print("--- absolute mode: fingers must match Manny outright ---")
        for bone in FINGER_BONES:
            err = angle_between(wmat(bone), wmat(NS + bone))
            check("absolute  %s" % bone, err < TOL_DEG, "err %.5f deg" % err)

        print()
        print("--- pelvis translation follows ---")
        pm = cmds.xform("pelvis", q=True, ws=True, t=True)
        ps = cmds.xform(NS + "pelvis", q=True, ws=True, t=True)
        off = cmds.getAttr("retarget_manny_to_suit.retargetSideOffset")
        dx = ps[0] - pm[0]
        check("pelvis side offset held", abs(dx - off) < TOL_CM,
              "dx %.4f vs %.4f" % (dx, off))

    print()
    print("--- no arc: a 90 deg turn on the spot must not orbit the suit ---")
    with posed({"pelvis.rotateY": 90.0}):
        pm = cmds.xform("pelvis", q=True, ws=True, t=True)
        ps = cmds.xform(NS + "pelvis", q=True, ws=True, t=True)
        off = cmds.getAttr("retarget_manny_to_suit.retargetSideOffset")
        check("suit stays beside, not orbiting", abs(ps[0] - pm[0] - off) < TOL_CM,
              "dx %.4f vs %.4f" % (ps[0] - pm[0], off))

    print()
    failed = [r for r in results if not r[1]]
    print("=== %d/%d PASS ===" % (len(results) - len(failed), len(results)))
    for label, _, detail in failed:
        print("  FAILED:", label, detail)
```

- [ ] **Step 2: Run it over the bridge**

Expected: every check PASS. A finger FAIL means the absolute mode is fighting a
bind-axis convention rather than a pose — rebuild with `finger_mode="offset"`
and report that to the user.

- [ ] **Step 3: Look at the result**

Screenshot the viewport, or ask the user to look. The numbers prove the transfer
is exact; only the eye proves the suit's hand is not inside-out. This is the
repo's standing rule — every serious bug here survived a green test run.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/verify_retarget.py
git commit -F commit-msg.txt
```

with `commit-msg.txt` holding:

```
test(retarget): live proof of exact transfer and the no-arc property

Asserts the two exact predicates the design rests on: an offset-mode bone
reproduces Manny's world rotation delta identically, and an absolute-mode
finger matches Manny's world orientation outright. Also pins the reason
pelvis uses point+orient by turning Manny 90 degrees on the spot and
checking the suit turns beside him instead of orbiting.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

## Self-Review

**Spec coverage:** hybrid offset policy → Task 1 (`build_bone_map` modes) and
Task 2 (`maintainOffset` per mode). Semantic spine map → Task 1 `SPINE_MAP`,
tested. No-parentConstraint rule → Task 2 wiring, proved in Task 4. Wiring table
→ Task 2. Set-membership teardown → Task 2 `remove_retarget`. `set_side_offset`
→ Task 3. Module shape and public surface → Tasks 1–3. Unit tests → Task 1.
Live verification → Task 4. Known limits are accepted, not implemented.

**Placeholders:** none — every step carries its code or its exact command.

**Type consistency:** `build_bone_map` returns `(mapping, unmatched)` in Tasks 1
and 2 alike; `OFFSET`/`ABSOLUTE` constants are used for the mode in both;
`RETARGET_SET` names the same set in Tasks 2, 3 and 4;
`retargetSideOffset` is written in Task 2 and read in Tasks 3 and 4.
