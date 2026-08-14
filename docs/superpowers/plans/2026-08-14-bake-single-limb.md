# Bake Single Limb Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `Bake+Delete` bake back to FK only the limbs the current selection touches, leaving the rest of the rig alone.

**Architecture:** The manifest splits from one flat set into one set per limb. The fiddly part — turning a selection into a list of limbs — becomes a pure function taking the manifest as data, so it is fully testable without Maya. `bake_limbs` runs OverRig's selection-scoped primitives per limb inside one undo chunk.

**Tech Stack:** Python 3.13.9 (Maya 2027), `maya.cmds`, `maya.mel`, PySide6, stdlib `unittest`.

Spec: `docs/superpowers/specs/2026-08-14-bake-single-limb-design.md`

## Global Constraints

- Test command: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v`, with `$env:QT_QPA_PLATFORM = 'offscreen'` for Qt tests.
- Bake uses `apply_Fast_Bake` (full timeline). Never `apply_range_Fast_Bake` here.
- Never call `barn_fast_bake_source_obj_and_delete_knots()`.
- Manifest sets are named `RigPicker_build_<limb>`.
- An empty or irrelevant selection must never mean "bake everything".
- Branch: `feature/overrig-picker`. Commit after every task.

## File Structure

| File | Responsibility |
|---|---|
| `maya_overrig/builder.py` | Per-limb manifest, `resolve_limbs`, `bake_limbs` |
| `maya_overrig/picker_window.py` | Wire `Bake+Delete` |
| `tests/test_builder.py` | Manifest naming and selection resolution, plain Python |
| `docs/superpowers/plans/verify_bake.py` | Live per-limb bake verification |

---

### Task 1: Per-limb manifest and selection resolution

**Files:**
- Modify: `maya_overrig/builder.py`
- Modify: `tests/test_builder.py`

**Interfaces:**
- Consumes: `LIMBS`, `BuildResult`, `limb_joints`, `missing_limbs` (already present)
- Produces:
  - `BUILD_SET_PREFIX = "RigPicker_build_"`
  - `limb_set(limb: str) -> str`
  - `resolve_limbs(nodes, limb_members, scene_map) -> list[str]`
  - `built_limbs() -> list[str]`
  - `limbs_in_selection(scene_map) -> list[str]`
  - `bake_limbs(scene_map, limbs) -> BuildResult`
  - `has_build()` now means "any limb set has members"
  - `build()` records into per-limb sets; `teardown()` delegates to `bake_limbs`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_builder.py`, before the `if __name__` block:

```python
class TestLimbSet(unittest.TestCase):

    def test_name_is_prefixed(self):
        self.assertEqual(builder.limb_set("leg_l"), "RigPicker_build_leg_l")

    def test_every_limb_gets_a_distinct_set(self):
        names = [builder.limb_set(name) for name, _ in builder.LIMBS]
        self.assertEqual(len(set(names)), 4)


class TestResolveLimbs(unittest.TestCase):

    SCENE_MAP = {
        "upperarm_l": "|rig|upperarm_l", "lowerarm_l": "|rig|lowerarm_l",
        "hand_l": "|rig|hand_l",
        "upperarm_r": "|rig|upperarm_r", "lowerarm_r": "|rig|lowerarm_r",
        "hand_r": "|rig|hand_r",
        "thigh_l": "|rig|thigh_l", "calf_l": "|rig|calf_l",
        "foot_l": "|rig|foot_l",
        "thigh_r": "|rig|thigh_r", "calf_r": "|rig|calf_r",
        "foot_r": "|rig|foot_r",
    }

    MEMBERS = {
        "leg_l": ["|thigh_l_IK_strech_gr", "|foot_l_IK_feet",
                  "|calf_l_IK_knee"],
        "leg_r": ["|thigh_r_IK_strech_gr", "|foot_r_IK_feet",
                  "|calf_r_IK_knee"],
    }

    def resolve(self, nodes):
        return builder.resolve_limbs(nodes, self.MEMBERS, self.SCENE_MAP)

    def test_recorded_node_resolves(self):
        self.assertEqual(self.resolve(["|foot_l_IK_feet"]), ["leg_l"])

    def test_descendant_of_a_recorded_node_resolves(self):
        self.assertEqual(
            self.resolve(["|thigh_l_IK_strech_gr|base_IK_strech3|fin_jnt11"]),
            ["leg_l"])

    def test_shape_under_a_control_resolves(self):
        self.assertEqual(
            self.resolve(["|foot_l_IK_feet|foot_l_IK_feetShape"]), ["leg_l"])

    def test_source_joint_resolves(self):
        """Lets the picker's own limb buttons drive the bake."""
        self.assertEqual(self.resolve(["|rig|calf_l"]), ["leg_l"])

    def test_source_joint_resolves_without_any_manifest(self):
        self.assertEqual(
            builder.resolve_limbs(["|rig|hand_r"], {}, self.SCENE_MAP),
            ["arm_r"])

    def test_unrelated_node_resolves_to_nothing(self):
        self.assertEqual(self.resolve(["|persp"]), [])

    def test_two_limbs_give_both(self):
        self.assertEqual(
            self.resolve(["|foot_l_IK_feet", "|foot_r_IK_feet"]),
            ["leg_l", "leg_r"])

    def test_duplicates_collapse(self):
        self.assertEqual(
            self.resolve(["|foot_l_IK_feet", "|calf_l_IK_knee", "|rig|thigh_l"]),
            ["leg_l"])

    def test_results_come_back_in_limb_table_order(self):
        found = self.resolve(["|foot_r_IK_feet", "|rig|hand_l",
                              "|foot_l_IK_feet"])
        self.assertEqual(found, ["arm_l", "leg_l", "leg_r"])

    def test_a_prefix_that_is_not_a_path_boundary_does_not_match(self):
        """`|foot_l_IK_feet_extra` is a different node, not a descendant."""
        self.assertEqual(self.resolve(["|foot_l_IK_feet_extra"]), [])

    def test_empty_selection_resolves_to_nothing(self):
        self.assertEqual(self.resolve([]), [])
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd '/c/!!!Work/MayaScripts' && '/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe' -m unittest tests.test_builder
```

Expected: FAIL — `AttributeError: module 'maya_overrig.builder' has no attribute 'limb_set'`

- [ ] **Step 3: Implement**

In `maya_overrig/builder.py`, replace `BUILD_SET = "RigPicker_build"` with:

```python
BUILD_SET_PREFIX = "RigPicker_build_"
```

Add after `missing_limbs`:

```python
def limb_set(limb):
    """Name of the object set recording one limb's created nodes."""
    return BUILD_SET_PREFIX + limb


def resolve_limbs(nodes, limb_members, scene_map):
    """Which limbs the given nodes touch, in LIMBS order.

    A node counts for a limb when it is one of that limb's recorded nodes, a
    descendant of one, or one of the limb's three source joints. The source
    joint route is what lets the picker's own limb buttons drive a bake.

    Pure on purpose: `limb_members` is a {limb: [paths]} mapping supplied by the
    caller, so all of this is testable without Maya.
    """
    owner_of_joint = {}
    for name, joints in LIMBS:
        for joint in joints:
            path = scene_map.get(joint)
            if path:
                owner_of_joint[path] = name

    hit = set()
    for node in nodes:
        if node in owner_of_joint:
            hit.add(owner_of_joint[node])
            continue
        for name, members in limb_members.items():
            if any(node == m or node.startswith(m + "|") for m in members):
                hit.add(name)
                break

    return [name for name, _ in LIMBS if name in hit]


def built_limbs():
    """Limbs that currently have nodes recorded against them."""
    return [name for name, _ in LIMBS
            if overrig.set_members(limb_set(name))]


def limbs_in_selection(scene_map):
    """Limbs touched by the current Maya selection."""
    members = {name: overrig.set_members(limb_set(name))
               for name, _ in LIMBS}
    selected = cmds.ls(selection=True, long=True) or []
    return resolve_limbs(selected, members, scene_map)
```

Replace `_ensure_build_set`, `has_build` and `teardown` with:

```python
def _ensure_limb_set(limb):
    name = limb_set(limb)
    if not cmds.objExists(name):
        cmds.sets(name=name, empty=True)
    return name


def has_build():
    """True when this tool has anything recorded in the scene."""
    return bool(built_limbs())


def bake_limbs(scene_map, limbs):
    """Bake the given limbs back to FK and remove their OverRig setup.

    Uses OverRig's own selection-scoped primitives, so its structures come
    apart the way it expects. Never touches limbs that were not asked for.
    """
    resolved = dict(limb_joints(scene_map))
    baked = []
    skipped = []
    removed = 0

    cmds.undoInfo(openChunk=True, chunkName="Rig Picker bake")
    try:
        for limb in limbs:
            members = [m for m in overrig.set_members(limb_set(limb))
                       if cmds.objExists(m)]
            joints = [j for j in resolved.get(limb, []) if cmds.objExists(j)]
            if not members and not joints:
                skipped.append(limb)
                continue

            if joints:
                overrig.fast_bake(joints)
                overrig.delete_constraint_attributes(joints)
            if members:
                cmds.delete(members)
                removed += len(members)
            if cmds.objExists(limb_set(limb)):
                cmds.delete(limb_set(limb))
            baked.append(limb)
    finally:
        cmds.undoInfo(closeChunk=True)

    message = "Baked {0} - {1} node(s) removed".format(
        ", ".join(baked) if baked else "nothing", removed)
    if skipped:
        message += ". Nothing recorded for: " + ", ".join(skipped)
    return BuildResult(baked, skipped, 0, removed, message)


def teardown(scene_map):
    """Bake and remove every limb this tool built."""
    return bake_limbs(scene_map, built_limbs())
```

In `build`, replace the manifest write:

```python
            fresh = sorted(after - before)
            if fresh:
                cmds.sets(fresh, addElement=_ensure_build_set())
                created.extend(fresh)
```

with:

```python
            fresh = sorted(after - before)
            if fresh:
                cmds.sets(fresh, addElement=_ensure_limb_set(name))
                created.extend(fresh)
```

And in `character_roots`, nothing changes.

- [ ] **Step 4: Run the suite**

```bash
cd '/c/!!!Work/MayaScripts' && QT_QPA_PLATFORM=offscreen '/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe' -m unittest discover -s tests -t .
```

Expected: PASS, 99 tests.

- [ ] **Step 5: Commit**

```bash
git add maya_overrig/builder.py tests/test_builder.py && git commit -m "feat(bake): per-limb manifest and selection resolution"
```

---

### Task 2: Wire the button and verify live

**Files:**
- Modify: `maya_overrig/picker_window.py`
- Create: `docs/superpowers/plans/verify_bake.py`

**Interfaces:**
- Consumes: `builder.limbs_in_selection`, `builder.bake_limbs`, `builder.built_limbs`
- Produces: `PickerWindow.bake_selected_limbs()`

- [ ] **Step 1: Wire the button**

In `_build_toolbar`, replace the disabled teardown button:

```python
        teardown_button = QtWidgets.QPushButton("Bake+Delete", bar)
        teardown_button.setStyleSheet(_BUTTON_STYLE)
        teardown_button.setEnabled(False)
        teardown_button.setToolTip("Not implemented yet")
        row.addWidget(teardown_button)
```

with:

```python
        self.bake_button = QtWidgets.QPushButton("Bake+Delete", bar)
        self.bake_button.setStyleSheet(_BUTTON_STYLE)
        self.bake_button.setToolTip(
            "Bake the selected limbs back to FK and remove their IK.\n"
            "Select an IK control, or use a limb button above.\n"
            "Main selects all four limbs.")
        self.bake_button.clicked.connect(
            lambda _checked=False: self.bake_selected_limbs())
        row.addWidget(self.bake_button)
```

Add this method next to `build_rig`:

```python
    def bake_selected_limbs(self):
        """Bake back to FK whichever limbs the current selection touches."""
        if not self._scene_map:
            self.status.showMessage(_UNBOUND_MESSAGE)
            return

        limbs = builder.limbs_in_selection(self._scene_map)
        if not limbs:
            self.status.showMessage(
                "Select an IK control or a limb in the picker first")
            return

        self.bake_button.setEnabled(False)
        try:
            result = builder.bake_limbs(self._scene_map, limbs)
        finally:
            self.bake_button.setEnabled(True)

        self.status.showMessage(result.message)
        self.sync_from_scene()
```

- [ ] **Step 2: Run the suite**

```bash
cd '/c/!!!Work/MayaScripts' && QT_QPA_PLATFORM=offscreen '/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe' -m unittest discover -s tests -t .
```

Expected: PASS, 99 tests.

- [ ] **Step 3: Write the live verification**

Create `docs/superpowers/plans/verify_bake.py`:

```python
"""Live checks for per-limb baking. Run inside Maya."""

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


def constraints_on(joint):
    return cmds.listRelatives(joint, children=True, type="constraint") or []


# Clear the stale flat set from the previous design.
if cmds.objExists("RigPicker_build"):
    cmds.delete("RigPicker_build")

window = maya_overrig.show_picker()
check("picker bound", bool(window._scene_map), str(window.bound_root()))

# Start from a known state: everything on IK.
if builder.has_build():
    builder.teardown(window._scene_map)
result = builder.build(window._scene_map)
check("four limbs built", len(result.built) == 4, str(result.built))
check("four manifest sets exist", len(builder.built_limbs()) == 4,
      str(builder.built_limbs()))

leg_l = [window._scene_map[j] for j in ("thigh_l", "calf_l", "foot_l")]
leg_r = [window._scene_map[j] for j in ("thigh_r", "calf_r", "foot_r")]

check("left leg is IK-driven before baking",
      any(constraints_on(j) for j in leg_l))

# --- bake ONE limb by selecting its control -----------------------------
control = [m for m in overrig.set_members(builder.limb_set("leg_l"))
           if m.endswith("_IK_feet")]
cmds.select(control, replace=True)
found = builder.limbs_in_selection(window._scene_map)
check("selecting the IK control resolves to leg_l", found == ["leg_l"],
      str(found))

baked = builder.bake_limbs(window._scene_map, found)
print("\n  bake says: %s\n" % baked.message)

check("leg_l reported baked", baked.built == ["leg_l"], str(baked.built))
check("leg_l set is gone", not cmds.objExists(builder.limb_set("leg_l")))
check("leg_l joints freed of constraints",
      all(not constraints_on(j) for j in leg_l))
check("leg_l kept its animation",
      all(cmds.keyframe(j, query=True, keyframeCount=True) > 0 for j in leg_l))
check("the other three limbs remain", len(builder.built_limbs()) == 3,
      str(builder.built_limbs()))
check("right leg still IK-driven", any(constraints_on(j) for j in leg_r))

# --- the picker's own limb button as the selector ------------------------
window.apply_selection(["thigh_r", "calf_r", "foot_r"], "replace")
found = builder.limbs_in_selection(window._scene_map)
check("selecting source joints resolves to leg_r", found == ["leg_r"],
      str(found))

# --- and an irrelevant selection must do nothing ------------------------
cmds.select("persp", replace=True)
check("irrelevant selection resolves to nothing",
      builder.limbs_in_selection(window._scene_map) == [])

# --- bake the rest ------------------------------------------------------
rest = builder.built_limbs()
builder.bake_limbs(window._scene_map, rest)
check("no manifest sets left", builder.built_limbs() == [],
      str(builder.built_limbs()))
check("no build recorded", not builder.has_build())

cmds.select(clear=True)
window.close()
print("\n%s" % ("ALL CHECKS PASSED" if not failures
                else "FAILURES: %s" % failures))
```

- [ ] **Step 4: Run it through the bridge**

Expected: every line `OK`.

- [ ] **Step 5: Commit**

```bash
git add maya_overrig/picker_window.py docs/superpowers/plans/verify_bake.py && git commit -m "feat(bake): bake selected limbs back to FK from the picker"
```

---

## Self-Review

**Spec coverage**

| Spec requirement | Task |
|---|---|
| Bake every limb the selection touches | 1 (`resolve_limbs`, `bake_limbs`), 2 (button) |
| Control, descendant, or source joint counts as a hit | 1, four separate tests |
| Per-limb manifest sets | 1 (`limb_set`, `_ensure_limb_set`, `build`) |
| One undo step | 1 (`bake_limbs` chunk in `finally`) |
| Full-timeline bake, never range | 1 — `overrig.fast_bake` only |
| Never the global OverRig teardown | 1 — absent by construction |
| Nothing selected does nothing | 2 (`bake_selected_limbs`) |
| Selection touching no limb does nothing | 2, and checked live |
| Unbuilt or already-baked limb skipped and named | 1 (`skipped`) |
| Not bound refuses | 2 |
| `teardown` reuses the same path | 1 |
| Stale flat set removed | 2 (verification script) |

No gaps.

**Placeholder scan:** none.

**Type consistency:** `limb_set` / `resolve_limbs` / `built_limbs` /
`limbs_in_selection` / `bake_limbs` / `has_build` / `teardown` /
`_ensure_limb_set` are spelled identically throughout. `BuildResult` keeps its
`built skipped created removed message` fields; `bake_limbs` returns `created`
as `0` because it creates nothing, and reports removals in `removed`.

One consistency note: `build()` calls `teardown()`, which now routes through
`bake_limbs`, so a rebuild bakes each limb exactly the way a manual bake does —
one code path, not two.
