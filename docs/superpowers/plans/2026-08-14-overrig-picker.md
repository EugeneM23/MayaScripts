# OverRig Picker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an anatomical body-map picker panel for the UE5 Manny skeleton that selects joints in the Maya scene when clicked.

**Architecture:** A `maya_overrig/` package split so the Qt view never imports `maya.cmds`. `bodymap.py` holds pure layout data, `naming.py` resolves logical joint names against the scene, `picker_view.py` draws and handles input, `picker_window.py` wires the view to Maya selection. The view talks outward in button ids only.

**Tech Stack:** Python 3.13.9 (Maya 2027), PySide6 6.8.3 / Qt 6.8.3, `maya.cmds`, stdlib `unittest`.

Spec: `docs/superpowers/specs/2026-08-14-overrig-picker-design.md`

## Global Constraints

- Test runner is mayapy — there is no system Python and no pytest. Never `pip install` into the Maya installation.
- Test command, from repo root: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v`
- Qt tests require `$env:QT_QPA_PLATFORM = 'offscreen'` before the runner.
- `picker_view.py` and `bodymap.py` MUST NOT import `maya.cmds`. This is the load-bearing boundary of the design.
- `bodymap.py` MUST import nothing outside the stdlib.
- Body-space canvas is exactly 400 × 620 units.
- Orientation is a FRONT view: the character's left (`_l`) is drawn on the viewer's RIGHT.
- Palette, verbatim from the spec: background `#2b2b2b`, centre `#8a8378`, left limbs `#4a7ea8`, right limbs `#a85a4a`, left fingers `#3f6885`, right fingers `#8a4c40`, group buttons `#3c3c3c` with text `#d8d8d8`, disabled fill `#3a3a3a` outline `#4a4a4a`, hover outline `#cfcfcf` 1 px, selected outline `#ffb648` 2 px with fill lightened ~18%.
- Branch: `feature/overrig-picker`. Commit after every task.

## Deliberate narrowing versus the spec

The spec says name resolution tolerates "namespaces and prefixes". This plan implements
namespace tolerance only. Fuzzy prefix matching is unsafe on this exact skeleton: a
suffix match for `hand_l` also matches the UE export helper `ik_hand_l`, and for `foot_l`
it matches `ik_foot_l`. Resolution is therefore an exact comparison of the leaf name after
stripping any namespace. Prefixed-rig support moves to future work.

## File Structure

| File | Responsibility |
|---|---|
| `maya_overrig/__init__.py` | Re-export `show_picker` |
| `maya_overrig/bodymap.py` | Button table, regions, group derivation. Pure stdlib. |
| `maya_overrig/naming.py` | Resolve logical joint name ↔ scene DAG path |
| `maya_overrig/picker_view.py` | `ButtonItem`, `PickerView`, palette, input handling |
| `maya_overrig/picker_window.py` | `PickerWindow`, toolbar, selection wiring, scriptJob |
| `tests/__init__.py` | Makes `tests` a package so discovery can import it |
| `tests/test_bodymap.py` | Layout invariants |
| `tests/test_naming.py` | Resolution against a stubbed `maya.cmds` |
| `tests/test_picker_view.py` | Scene construction and interaction, headless Qt |

---

### Task 1: Body map data

**Files:**
- Create: `maya_overrig/__init__.py`
- Create: `maya_overrig/bodymap.py`
- Create: `tests/__init__.py`
- Test: `tests/test_bodymap.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `Button = namedtuple("Button", "id joint x y w h region")`
  - `CANVAS_W: int = 400`, `CANVAS_H: int = 620`
  - `REGIONS: tuple[str, ...]`
  - `GROUPS: tuple[str, ...]`
  - `BUTTONS: tuple[Button, ...]` — exactly 64
  - `button_by_id(bid: str) -> Button` — raises `KeyError` if unknown
  - `group_members(group: str) -> tuple[str, ...]` — button ids; raises `KeyError` if unknown

- [ ] **Step 1: Write the failing test**

Create `tests/__init__.py` as an empty file, then `tests/test_bodymap.py`:

```python
import unittest

from maya_overrig import bodymap


class TestBodyMap(unittest.TestCase):

    def test_has_exactly_64_buttons(self):
        self.assertEqual(len(bodymap.BUTTONS), 64)

    def test_ids_are_unique(self):
        ids = [b.id for b in bodymap.BUTTONS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_region_is_known(self):
        for b in bodymap.BUTTONS:
            self.assertIn(b.region, bodymap.REGIONS, b.id)

    def test_no_rectangles_overlap(self):
        for i, a in enumerate(bodymap.BUTTONS):
            for b in bodymap.BUTTONS[i + 1:]:
                overlap_x = a.x < b.x + b.w and b.x < a.x + a.w
                overlap_y = a.y < b.y + b.h and b.y < a.y + a.h
                self.assertFalse(
                    overlap_x and overlap_y,
                    "{0} overlaps {1}".format(a.id, b.id))

    def test_all_buttons_inside_canvas(self):
        for b in bodymap.BUTTONS:
            self.assertGreaterEqual(b.x, 0, b.id)
            self.assertGreaterEqual(b.y, 0, b.id)
            self.assertLessEqual(b.x + b.w, bodymap.CANVAS_W, b.id)
            self.assertLessEqual(b.y + b.h, bodymap.CANVAS_H, b.id)

    def test_sides_are_mirrored(self):
        by_id = {b.id: b for b in bodymap.BUTTONS}
        left = [b for b in bodymap.BUTTONS if b.id.endswith("_l")]
        self.assertTrue(left)
        for lb in left:
            rb = by_id[lb.id[:-2] + "_r"]
            self.assertEqual(rb.w, lb.w)
            self.assertEqual(rb.h, lb.h)
            self.assertEqual(rb.y, lb.y)
            self.assertEqual(rb.x, bodymap.CANVAS_W - lb.x - lb.w)

    def test_character_left_is_drawn_on_viewer_right(self):
        by_id = {b.id: b for b in bodymap.BUTTONS}
        self.assertGreater(by_id["hand_l"].x, bodymap.CANVAS_W / 2)
        self.assertLess(by_id["hand_r"].x, bodymap.CANVAS_W / 2)

    def test_group_all_covers_every_button(self):
        self.assertEqual(len(bodymap.group_members("all")), 64)

    def test_group_main_excludes_fingers(self):
        main = bodymap.group_members("main")
        self.assertEqual(len(main), 26)
        by_id = {b.id: b for b in bodymap.BUTTONS}
        for bid in main:
            self.assertNotIn(by_id[bid].region, ("hand_l", "hand_r"))

    def test_finger_groups_hold_19_each(self):
        self.assertEqual(len(bodymap.group_members("hand_l")), 19)
        self.assertEqual(len(bodymap.group_members("hand_r")), 19)

    def test_button_by_id_round_trips(self):
        self.assertEqual(bodymap.button_by_id("head").joint, "head")

    def test_button_by_id_rejects_unknown(self):
        with self.assertRaises(KeyError):
            bodymap.button_by_id("no_such_button")

    def test_group_members_rejects_unknown(self):
        with self.assertRaises(KeyError):
            bodymap.group_members("no_such_group")

    def test_joint_names_match_ue5_convention(self):
        names = {b.joint for b in bodymap.BUTTONS}
        for expected in ("root", "pelvis", "spine_01", "spine_05", "neck_01",
                         "head", "clavicle_l", "upperarm_r", "lowerarm_l",
                         "hand_r", "thigh_l", "calf_r", "foot_l", "ball_r",
                         "index_metacarpal_l", "index_03_r", "thumb_01_l",
                         "pinky_metacarpal_r"):
            self.assertIn(expected, names)

    def test_ue_helper_joints_are_absent(self):
        names = {b.joint for b in bodymap.BUTTONS}
        for forbidden in ("ik_foot_root", "ik_foot_l", "ik_hand_root",
                          "ik_hand_gun", "ik_hand_l", "interaction",
                          "center_of_mass", "camera_root", "camera_bone",
                          "weapon_l", "lowerarm_twist_01_l", "calf_twist_02_r"):
            self.assertNotIn(forbidden, names)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd '/c/!!!Work/MayaScripts' && '/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe' -m unittest discover -s tests -t . -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'maya_overrig'`

- [ ] **Step 3: Write the implementation**

Create `maya_overrig/__init__.py`:

```python
"""Python wrapper around the OverRig MEL toolset."""

from maya_overrig.picker_window import show_picker

__all__ = ["show_picker"]
```

Note: this import will fail until Task 4 creates `picker_window.py`. Until then, keep
`__init__.py` empty — write the line above only when Task 4 lands. For Task 1, create
`maya_overrig/__init__.py` as an empty file.

Create `maya_overrig/bodymap.py`:

```python
"""Static body map for the OverRig picker.

Pure data. Imports nothing outside the stdlib -- no Qt, no maya.cmds -- so the
layout can be tested in plain Python.

Coordinates live in a fixed body-space of CANVAS_W x CANVAS_H units which the
view scales to fit, so nothing here depends on window size.

Orientation is a FRONT view of the character: the character's left side (the
`_l` joints) is drawn on the viewer's RIGHT.
"""

from collections import namedtuple

Button = namedtuple("Button", "id joint x y w h region")

CANVAS_W = 400
CANVAS_H = 620

REGIONS = ("root", "spine", "head",
           "arm_l", "arm_r", "hand_l", "hand_r", "leg_l", "leg_r")

GROUPS = ("all", "main") + REGIONS

# Fingers carrying a metacarpal joint, ordered inboard to outboard on the hand.
_FINGERS = ("index", "middle", "ring", "pinky")

_FINGER_W = 20
_FINGER_H = 17
_FINGER_STEP_X = 23
_FINGER_STEP_Y = 20
_FINGER_X0 = 296
_FINGER_Y0 = 286
_THUMB_X = 270


def _centre_buttons():
    """Root, pelvis, spine stack, neck and head -- all on the midline."""
    rows = [
        ("head", 178, 28, 44, 40, "head"),
        ("neck_02", 188, 72, 24, 14, "head"),
        ("neck_01", 188, 90, 24, 14, "head"),
        ("spine_05", 168, 110, 64, 17, "spine"),
        ("spine_04", 168, 131, 64, 17, "spine"),
        ("spine_03", 168, 152, 64, 17, "spine"),
        ("spine_02", 168, 173, 64, 17, "spine"),
        ("spine_01", 168, 194, 64, 17, "spine"),
        ("pelvis", 162, 215, 76, 24, "root"),
        ("root", 178, 560, 44, 20, "root"),
    ]
    return [Button(n, n, x, y, w, h, r) for n, x, y, w, h, r in rows]


def _left_limb_buttons():
    """Character-left arm and leg, drawn on the viewer's right."""
    rows = [
        ("clavicle_l", 236, 110, 34, 16, "arm_l"),
        ("upperarm_l", 252, 130, 28, 58, "arm_l"),
        ("lowerarm_l", 256, 192, 26, 54, "arm_l"),
        ("hand_l", 258, 250, 24, 26, "arm_l"),
        ("thigh_l", 208, 250, 30, 72, "leg_l"),
        ("calf_l", 210, 326, 28, 70, "leg_l"),
        ("foot_l", 212, 400, 26, 28, "leg_l"),
        ("ball_l", 212, 432, 26, 16, "leg_l"),
    ]
    return [Button(n, n, x, y, w, h, r) for n, x, y, w, h, r in rows]


def _left_finger_buttons():
    """Character-left hand: four metacarpal fingers in columns, plus the thumb."""
    out = []
    for col, finger in enumerate(_FINGERS):
        x = _FINGER_X0 + col * _FINGER_STEP_X
        joints = ["{0}_metacarpal_l".format(finger)]
        joints += ["{0}_{1:02d}_l".format(finger, i) for i in (1, 2, 3)]
        for row, joint in enumerate(joints):
            y = _FINGER_Y0 + row * _FINGER_STEP_Y
            out.append(Button(joint, joint, x, y, _FINGER_W, _FINGER_H, "hand_l"))

    for row, i in enumerate((1, 2, 3)):
        joint = "thumb_{0:02d}_l".format(i)
        y = _FINGER_Y0 + (row + 1) * _FINGER_STEP_Y
        out.append(Button(joint, joint, _THUMB_X, y, _FINGER_W, _FINGER_H, "hand_l"))

    return out


def _mirrored(buttons):
    """Mirror character-left buttons into their character-right twins.

    Every input button's id, joint and region must end in `_l`.
    """
    out = []
    for b in buttons:
        out.append(Button(
            b.id[:-2] + "_r",
            b.joint[:-2] + "_r",
            CANVAS_W - b.x - b.w,
            b.y, b.w, b.h,
            b.region[:-2] + "_r",
        ))
    return out


def _build():
    left = _left_limb_buttons() + _left_finger_buttons()
    return tuple(_centre_buttons() + left + _mirrored(left))


BUTTONS = _build()

_BY_ID = {b.id: b for b in BUTTONS}


def button_by_id(bid):
    """Return the Button with this id. Raises KeyError if unknown."""
    return _BY_ID[bid]


def group_members(group):
    """Return the button ids belonging to a group.

    `all` is every button; `main` is everything except fingers; any other name
    must be a region. Raises KeyError for unknown groups.
    """
    if group not in GROUPS:
        raise KeyError(group)
    if group == "all":
        return tuple(b.id for b in BUTTONS)
    if group == "main":
        return tuple(b.id for b in BUTTONS
                     if b.region not in ("hand_l", "hand_r"))
    return tuple(b.id for b in BUTTONS if b.region == group)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd '/c/!!!Work/MayaScripts' && '/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe' -m unittest discover -s tests -t . -v
```

Expected: PASS, 14 tests.

If `test_no_rectangles_overlap` fails, adjust the offending coordinates in
`_centre_buttons` / `_left_limb_buttons` / the finger constants until it passes. The test
is the authority on the layout being sane; do not weaken it.

- [ ] **Step 5: Commit**

```bash
git add maya_overrig tests && git commit -m "feat(overrig): body map data for the picker"
```

---

### Task 2: Name resolution

**Files:**
- Create: `maya_overrig/naming.py`
- Test: `tests/test_naming.py`

**Interfaces:**
- Consumes: nothing from Task 1
- Produces:
  - `leaf(dag_path: str) -> str` — strips DAG path and namespace
  - `resolve(joint: str) -> str | None` — long DAG path, or `None` if absent
  - `resolve_many(joints) -> dict[str, str]` — only entries that resolved

- [ ] **Step 1: Write the failing test**

Create `tests/test_naming.py`:

```python
import sys
import types
import unittest


class FakeCmds(object):
    """Minimal stand-in for maya.cmds covering only what naming.py calls."""

    def __init__(self, joints=(), warnings=None):
        self._joints = list(joints)
        self.warnings = warnings if warnings is not None else []

    def ls(self, *args, **kwargs):
        return list(self._joints)

    def warning(self, message):
        self.warnings.append(message)


def install_fake_cmds(joints):
    """Put a fake maya.cmds on sys.modules and return a fresh naming module."""
    fake = FakeCmds(joints)
    maya_pkg = types.ModuleType("maya")
    maya_pkg.cmds = fake
    sys.modules["maya"] = maya_pkg
    sys.modules["maya.cmds"] = fake
    for name in list(sys.modules):
        if name == "maya_overrig.naming":
            del sys.modules[name]
    from maya_overrig import naming
    return naming, fake


class TestLeaf(unittest.TestCase):

    def setUp(self):
        self.naming, _ = install_fake_cmds([])

    def test_strips_dag_path(self):
        self.assertEqual(self.naming.leaf("|root|pelvis|spine_01"), "spine_01")

    def test_strips_namespace(self):
        self.assertEqual(self.naming.leaf("|char:root|char:hand_l"), "hand_l")

    def test_plain_name_survives(self):
        self.assertEqual(self.naming.leaf("head"), "head")


class TestResolve(unittest.TestCase):

    def test_finds_bare_joint(self):
        naming, _ = install_fake_cmds(["|root|pelvis|spine_01"])
        self.assertEqual(naming.resolve("spine_01"), "|root|pelvis|spine_01")

    def test_finds_namespaced_joint(self):
        naming, _ = install_fake_cmds(["|char:root|char:hand_l"])
        self.assertEqual(naming.resolve("hand_l"), "|char:root|char:hand_l")

    def test_missing_joint_returns_none(self):
        naming, _ = install_fake_cmds(["|root"])
        self.assertIsNone(naming.resolve("hand_l"))

    def test_does_not_match_ue_helper_by_suffix(self):
        """The trap: `ik_hand_l` must never satisfy a request for `hand_l`."""
        naming, _ = install_fake_cmds(["|root|ik_hand_root|ik_hand_l"])
        self.assertIsNone(naming.resolve("hand_l"))

    def test_ambiguous_takes_first_and_warns(self):
        naming, fake = install_fake_cmds(["|a:root|a:head", "|b:root|b:head"])
        self.assertEqual(naming.resolve("head"), "|a:root|a:head")
        self.assertEqual(len(fake.warnings), 1)

    def test_resolve_many_skips_missing(self):
        naming, _ = install_fake_cmds(["|root|head"])
        found = naming.resolve_many(["head", "hand_l"])
        self.assertEqual(found, {"head": "|root|head"})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd '/c/!!!Work/MayaScripts' && '/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe' -m unittest discover -s tests -t . -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'maya_overrig.naming'`

- [ ] **Step 3: Write the implementation**

Create `maya_overrig/naming.py`:

```python
"""Resolve logical joint names to objects in the current Maya scene.

Namespaces are tolerated: `char:hand_l` satisfies a request for `hand_l`.

Fuzzy prefix matching is deliberately NOT supported. On a UE5 skeleton a suffix
match for `hand_l` would also hit the export helper `ik_hand_l`, and `foot_l`
would hit `ik_foot_l`. Resolution is therefore an exact comparison of the leaf
name after any namespace is stripped.
"""

import maya.cmds as cmds


def leaf(dag_path):
    """Strip DAG path and namespace: '|a|ns:hand_l' -> 'hand_l'."""
    return dag_path.split("|")[-1].split(":")[-1]


def resolve(joint):
    """Return the long DAG path of `joint`, or None if it is not in the scene.

    When several joints share the leaf name -- two characters in one scene --
    the first is returned and a warning is issued.
    """
    matches = [j for j in (cmds.ls(type="joint", long=True) or [])
               if leaf(j) == joint]
    if not matches:
        return None
    if len(matches) > 1:
        cmds.warning(
            "OverRig picker: {0} matches for '{1}', using {2}".format(
                len(matches), joint, matches[0]))
    return matches[0]


def resolve_many(joints):
    """Map each name that exists in the scene to its long DAG path.

    Names that do not resolve are simply absent from the result. Walks the joint
    list once rather than calling resolve() per name.
    """
    scene = {}
    for dag in cmds.ls(type="joint", long=True) or []:
        scene.setdefault(leaf(dag), dag)
    return {name: scene[name] for name in joints if name in scene}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd '/c/!!!Work/MayaScripts' && '/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe' -m unittest discover -s tests -t . -v
```

Expected: PASS, 23 tests total.

Note: `resolve_many` does not warn on ambiguity — `setdefault` keeps the first match, matching `resolve`'s choice.

- [ ] **Step 5: Commit**

```bash
git add maya_overrig/naming.py tests/test_naming.py && git commit -m "feat(overrig): namespace-tolerant joint name resolution"
```

---

### Task 3: Picker view — items and painting

**Files:**
- Create: `maya_overrig/picker_view.py`
- Test: `tests/test_picker_view.py`

**Interfaces:**
- Consumes: `bodymap.BUTTONS`, `bodymap.CANVAS_W/H`, `bodymap.button_by_id`
- Produces:
  - `STATE_NEUTRAL = "neutral"`, `STATE_SELECTED = "selected"`
  - `class ButtonItem(QGraphicsRectItem)` with `.button_id`, `.region`, `.state`, `.available`, `.set_state(state)`, `.set_available(flag)`
  - `class PickerView(QGraphicsView)` with `.items_by_id: dict[str, ButtonItem]`, `.set_selected(ids)`, `.set_available(ids)`
  - `region_colour(region) -> QColor`

- [ ] **Step 1: Write the failing test**

Create `tests/test_picker_view.py`:

```python
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets

from maya_overrig import bodymap, picker_view


def _app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


class TestPickerView(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = _app()

    def setUp(self):
        self.view = picker_view.PickerView()

    def test_one_item_per_button(self):
        self.assertEqual(len(self.view.items_by_id), len(bodymap.BUTTONS))

    def test_item_geometry_matches_bodymap(self):
        b = bodymap.button_by_id("head")
        item = self.view.items_by_id["head"]
        rect = item.rect()
        self.assertEqual(rect.width(), b.w)
        self.assertEqual(rect.height(), b.h)
        self.assertEqual(item.pos().x(), b.x)
        self.assertEqual(item.pos().y(), b.y)

    def test_items_start_neutral(self):
        for item in self.view.items_by_id.values():
            self.assertEqual(item.state, picker_view.STATE_NEUTRAL)

    def test_set_selected_marks_only_those_ids(self):
        self.view.set_selected(["head", "hand_l"])
        self.assertEqual(self.view.items_by_id["head"].state,
                         picker_view.STATE_SELECTED)
        self.assertEqual(self.view.items_by_id["hand_l"].state,
                         picker_view.STATE_SELECTED)
        self.assertEqual(self.view.items_by_id["pelvis"].state,
                         picker_view.STATE_NEUTRAL)

    def test_set_selected_clears_previous(self):
        self.view.set_selected(["head"])
        self.view.set_selected(["pelvis"])
        self.assertEqual(self.view.items_by_id["head"].state,
                         picker_view.STATE_NEUTRAL)

    def test_items_start_available(self):
        for item in self.view.items_by_id.values():
            self.assertTrue(item.available)

    def test_set_available_dims_the_rest(self):
        self.view.set_available(["head"])
        self.assertTrue(self.view.items_by_id["head"].available)
        self.assertFalse(self.view.items_by_id["pelvis"].available)

    def test_unavailable_items_do_not_accept_hover(self):
        self.view.set_available(["head"])
        self.assertFalse(
            self.view.items_by_id["pelvis"].acceptHoverEvents())

    def test_left_and_right_get_different_colours(self):
        left = picker_view.region_colour("arm_l")
        right = picker_view.region_colour("arm_r")
        self.assertNotEqual(left.name(), right.name())

    def test_centre_regions_share_one_colour(self):
        self.assertEqual(picker_view.region_colour("spine").name(),
                         picker_view.region_colour("head").name())
        self.assertEqual(picker_view.region_colour("root").name(),
                         picker_view.region_colour("spine").name())

    def test_scene_rect_matches_canvas(self):
        rect = self.view.scene().sceneRect()
        self.assertEqual(rect.width(), bodymap.CANVAS_W)
        self.assertEqual(rect.height(), bodymap.CANVAS_H)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd '/c/!!!Work/MayaScripts' && QT_QPA_PLATFORM=offscreen '/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe' -m unittest discover -s tests -t . -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'maya_overrig.picker_view'`

- [ ] **Step 3: Write the implementation**

Create `maya_overrig/picker_view.py`:

```python
"""Qt view for the OverRig picker.

Deliberately knows nothing about Maya: it draws the body map, handles input,
and reports button ids outward through signals. Everything that touches the
scene lives in picker_window.py.
"""

from PySide6 import QtCore, QtGui, QtWidgets

from maya_overrig import bodymap

STATE_NEUTRAL = "neutral"
STATE_SELECTED = "selected"

BACKGROUND = "#2b2b2b"

_CENTRE = "#8a8378"
_REGION_COLOURS = {
    "root": _CENTRE,
    "spine": _CENTRE,
    "head": _CENTRE,
    "arm_l": "#4a7ea8",
    "leg_l": "#4a7ea8",
    "hand_l": "#3f6885",
    "arm_r": "#a85a4a",
    "leg_r": "#a85a4a",
    "hand_r": "#8a4c40",
}

_DISABLED_FILL = "#3a3a3a"
_DISABLED_LINE = "#4a4a4a"
_HOVER_LINE = "#cfcfcf"
_SELECTED_LINE = "#ffb648"

_CORNER_RADIUS = 3.0


def region_colour(region):
    """Base fill colour for a body region."""
    return QtGui.QColor(_REGION_COLOURS[region])


class ButtonItem(QtWidgets.QGraphicsRectItem):
    """One body-map button. Paints itself from state, availability and hover."""

    def __init__(self, button):
        super(ButtonItem, self).__init__(0.0, 0.0, float(button.w), float(button.h))
        self.button_id = button.id
        self.joint = button.joint
        self.region = button.region
        self.state = STATE_NEUTRAL
        self.available = True
        self._hovered = False

        self.setPos(float(button.x), float(button.y))
        self.setAcceptHoverEvents(True)
        self.setToolTip(button.joint)

    def set_state(self, state):
        if state != self.state:
            self.state = state
            self.update()

    def set_available(self, flag):
        if flag != self.available:
            self.available = flag
            self.setAcceptHoverEvents(flag)
            if not flag:
                self._hovered = False
                self.state = STATE_NEUTRAL
            self.update()

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.update()
        super(ButtonItem, self).hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.update()
        super(ButtonItem, self).hoverLeaveEvent(event)

    def _fill(self):
        if not self.available:
            return QtGui.QColor(_DISABLED_FILL)
        colour = region_colour(self.region)
        if self.state == STATE_SELECTED:
            return colour.lighter(118)
        return colour

    def _pen(self):
        if not self.available:
            return QtGui.QPen(QtGui.QColor(_DISABLED_LINE), 1.0)
        if self.state == STATE_SELECTED:
            return QtGui.QPen(QtGui.QColor(_SELECTED_LINE), 2.0)
        if self._hovered:
            return QtGui.QPen(QtGui.QColor(_HOVER_LINE), 1.0)
        return QtGui.QPen(QtGui.QColor(0, 0, 0, 160), 1.0)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)

        base = self._fill()
        gradient = QtGui.QLinearGradient(self.rect().topLeft(),
                                         self.rect().bottomLeft())
        gradient.setColorAt(0.0, base.lighter(108))
        gradient.setColorAt(1.0, base.darker(112))

        painter.setBrush(QtGui.QBrush(gradient))
        painter.setPen(self._pen())
        painter.drawRoundedRect(self.rect(), _CORNER_RADIUS, _CORNER_RADIUS)


class PickerView(QtWidgets.QGraphicsView):
    """Renders the body map. Emits button ids; never touches Maya."""

    def __init__(self, parent=None):
        super(PickerView, self).__init__(parent)

        scene = QtWidgets.QGraphicsScene(self)
        scene.setSceneRect(0.0, 0.0,
                           float(bodymap.CANVAS_W), float(bodymap.CANVAS_H))
        self.setScene(scene)

        self.setRenderHint(QtGui.QPainter.Antialiasing, True)
        self.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(BACKGROUND)))
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)

        self.items_by_id = {}
        for button in bodymap.BUTTONS:
            item = ButtonItem(button)
            scene.addItem(item)
            self.items_by_id[button.id] = item

    def set_selected(self, ids):
        """Mark exactly these button ids selected; everything else neutral."""
        wanted = set(ids)
        for bid, item in self.items_by_id.items():
            if not item.available:
                continue
            item.set_state(STATE_SELECTED if bid in wanted else STATE_NEUTRAL)

    def set_available(self, ids):
        """Mark these ids interactive; dim every other button."""
        wanted = set(ids)
        for bid, item in self.items_by_id.items():
            item.set_available(bid in wanted)

    def resizeEvent(self, event):
        super(PickerView, self).resizeEvent(event)
        self.fitInView(self.scene().sceneRect(), QtCore.Qt.KeepAspectRatio)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd '/c/!!!Work/MayaScripts' && QT_QPA_PLATFORM=offscreen '/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe' -m unittest discover -s tests -t . -v
```

Expected: PASS, 34 tests total.

- [ ] **Step 5: Commit**

```bash
git add maya_overrig/picker_view.py tests/test_picker_view.py && git commit -m "feat(overrig): picker view items and painting"
```

---

### Task 4: Picker view — interaction

**Files:**
- Modify: `maya_overrig/picker_view.py`
- Modify: `tests/test_picker_view.py`

**Interfaces:**
- Consumes: `ButtonItem`, `PickerView` from Task 3
- Produces, added to `PickerView`:
  - `selection_requested = QtCore.Signal(list, str)` — ids, mode in `("replace", "add", "toggle")`
  - `hovered = QtCore.Signal(str)` — button id, or `""` when leaving
  - `ids_in_rect(rect: QtCore.QRectF) -> list[str]`
  - `MODE_REPLACE = "replace"`, `MODE_ADD = "add"`, `MODE_TOGGLE = "toggle"`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_picker_view.py`, before the `if __name__` block:

```python
class TestInteraction(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = _app()

    def setUp(self):
        self.view = picker_view.PickerView()
        self.view.resize(400, 620)
        self.emitted = []
        self.view.selection_requested.connect(
            lambda ids, mode: self.emitted.append((list(ids), mode)))

    def test_ids_in_rect_finds_a_whole_finger_column(self):
        b = bodymap.button_by_id("index_metacarpal_l")
        rect = QtCore.QRectF(b.x - 1, b.y - 1, b.w + 2, 4 * 20 + 2)
        found = self.view.ids_in_rect(rect)
        for expected in ("index_metacarpal_l", "index_01_l",
                         "index_02_l", "index_03_l"):
            self.assertIn(expected, found)

    def test_ids_in_rect_skips_unavailable(self):
        self.view.set_available(["index_01_l"])
        b = bodymap.button_by_id("index_metacarpal_l")
        rect = QtCore.QRectF(b.x - 1, b.y - 1, b.w + 2, 4 * 20 + 2)
        found = self.view.ids_in_rect(rect)
        self.assertEqual(found, ["index_01_l"])

    def test_ids_in_rect_empty_outside_the_body(self):
        self.assertEqual(self.view.ids_in_rect(QtCore.QRectF(0, 600, 4, 4)), [])

    def test_modifier_mapping(self):
        from PySide6.QtCore import Qt
        self.assertEqual(picker_view.mode_for(Qt.NoModifier),
                         picker_view.MODE_REPLACE)
        self.assertEqual(picker_view.mode_for(Qt.ShiftModifier),
                         picker_view.MODE_ADD)
        self.assertEqual(picker_view.mode_for(Qt.ControlModifier),
                         picker_view.MODE_TOGGLE)

    def test_click_emits_replace_for_that_button(self):
        self.view.emit_click("head", picker_view.MODE_REPLACE)
        self.assertEqual(self.emitted, [(["head"], "replace")])

    def test_marquee_emits_every_covered_id(self):
        b = bodymap.button_by_id("index_metacarpal_l")
        rect = QtCore.QRectF(b.x - 1, b.y - 1, b.w + 2, 4 * 20 + 2)
        self.view.emit_marquee(rect, picker_view.MODE_ADD)
        ids, mode = self.emitted[0]
        self.assertEqual(mode, "add")
        self.assertIn("index_03_l", ids)

    def test_marquee_covering_nothing_emits_nothing(self):
        self.view.emit_marquee(QtCore.QRectF(0, 600, 4, 4),
                               picker_view.MODE_REPLACE)
        self.assertEqual(self.emitted, [])
```

Add `from PySide6 import QtCore` to the imports at the top of the test file.

- [ ] **Step 2: Run test to verify it fails**

```bash
cd '/c/!!!Work/MayaScripts' && QT_QPA_PLATFORM=offscreen '/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe' -m unittest discover -s tests -t . -v
```

Expected: FAIL — `AttributeError: 'PickerView' object has no attribute 'selection_requested'`

- [ ] **Step 3: Write the implementation**

Add near the top of `picker_view.py`, after the state constants:

```python
MODE_REPLACE = "replace"
MODE_ADD = "add"
MODE_TOGGLE = "toggle"

_CLICK_SLOP = 3.0  # a drag shorter than this is treated as a click


def mode_for(modifiers):
    """Map Qt keyboard modifiers to a selection mode."""
    if modifiers & QtCore.Qt.ControlModifier:
        return MODE_TOGGLE
    if modifiers & QtCore.Qt.ShiftModifier:
        return MODE_ADD
    return MODE_REPLACE
```

Add these signals as class attributes on `PickerView`, directly under the class docstring:

```python
    selection_requested = QtCore.Signal(list, str)
    hovered = QtCore.Signal(str)
```

Add to `PickerView.__init__`, after the item loop:

```python
        self.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)
        self.setMouseTracking(True)
        self._press_pos = None
        for item in self.items_by_id.values():
            item.view = self
```

Add these methods to `PickerView`:

```python
    def ids_in_rect(self, rect):
        """Ids of available buttons intersecting a rect in scene coordinates."""
        found = []
        for item in self.scene().items(rect):
            if isinstance(item, ButtonItem) and item.available:
                found.append(item.button_id)
        return found

    def emit_click(self, button_id, mode):
        """Emit a single-button selection request. Separated out for testing."""
        self.selection_requested.emit([button_id], mode)

    def emit_marquee(self, rect, mode):
        """Emit a rect selection request, unless it covers nothing."""
        ids = self.ids_in_rect(rect)
        if ids:
            self.selection_requested.emit(ids, mode)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MiddleButton:
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
        elif event.button() == QtCore.Qt.LeftButton:
            self._press_pos = event.position().toPoint()
        super(PickerView, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.MiddleButton:
            super(PickerView, self).mouseReleaseEvent(event)
            self.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)
            return

        if event.button() != QtCore.Qt.LeftButton or self._press_pos is None:
            super(PickerView, self).mouseReleaseEvent(event)
            return

        release = event.position().toPoint()
        travelled = (release - self._press_pos)
        is_click = (abs(travelled.x()) < _CLICK_SLOP
                    and abs(travelled.y()) < _CLICK_SLOP)
        mode = mode_for(event.modifiers())

        if is_click:
            item = self.itemAt(release)
            if isinstance(item, ButtonItem) and item.available:
                self.emit_click(item.button_id, mode)
        else:
            rect = QtCore.QRectF(self.mapToScene(self._press_pos),
                                 self.mapToScene(release)).normalized()
            self.emit_marquee(rect, mode)

        self._press_pos = None
        super(PickerView, self).mouseReleaseEvent(event)

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1.0 / 1.15
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.scale(factor, factor)
```

Wire hover reporting by adding to `ButtonItem.__init__`:

```python
        self.view = None
```

and extending the hover handlers:

```python
    def hoverEnterEvent(self, event):
        self._hovered = True
        self.update()
        if self.view is not None:
            self.view.hovered.emit(self.button_id)
        super(ButtonItem, self).hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.update()
        if self.view is not None:
            self.view.hovered.emit("")
        super(ButtonItem, self).hoverLeaveEvent(event)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd '/c/!!!Work/MayaScripts' && QT_QPA_PLATFORM=offscreen '/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe' -m unittest discover -s tests -t . -v
```

Expected: PASS, 41 tests total.

- [ ] **Step 5: Commit**

```bash
git add maya_overrig/picker_view.py tests/test_picker_view.py && git commit -m "feat(overrig): picker click, marquee, zoom and pan"
```

---

### Task 5: Window shell and Maya selection wiring

**Files:**
- Create: `maya_overrig/picker_window.py`
- Modify: `maya_overrig/__init__.py`

**Interfaces:**
- Consumes: `PickerView`, `bodymap`, `naming`
- Produces:
  - `class PickerWindow(QtWidgets.QMainWindow)` with `.view`, `.status`, `.refresh_availability()`, `.apply_selection(ids, mode)`, `.sync_from_scene()`
  - `show_picker() -> PickerWindow`
  - `WINDOW_OBJECT_NAME = "overRigPickerWindow"`

This task has no unit tests — every path needs a live Maya session. It is verified in
Task 6 through the command-port bridge.

- [ ] **Step 1: Write the implementation**

Create `maya_overrig/picker_window.py`:

```python
"""Maya-facing shell for the OverRig picker.

Owns every interaction with the scene. The view below it stays Maya-free.
"""

import maya.cmds as cmds
import maya.OpenMayaUI as omui
from PySide6 import QtCore, QtWidgets
from shiboken6 import wrapInstance

from maya_overrig import bodymap, naming
from maya_overrig.picker_view import (MODE_ADD, MODE_TOGGLE, PickerView)

WINDOW_OBJECT_NAME = "overRigPickerWindow"
WINDOW_TITLE = "OverRig Picker"

_GROUP_BUTTONS = (
    ("All", "all"), ("Main", "main"), ("Spine", "spine"), ("Head", "head"),
    ("Arm L", "arm_l"), ("Arm R", "arm_r"),
    ("Hand L", "hand_l"), ("Hand R", "hand_r"),
    ("Leg L", "leg_l"), ("Leg R", "leg_r"),
)


def maya_main_window():
    """Return Maya's main window as a QWidget so dialogs parent correctly."""
    pointer = omui.MQtUtil.mainWindow()
    return wrapInstance(int(pointer), QtWidgets.QWidget)


class PickerWindow(QtWidgets.QMainWindow):

    def __init__(self, parent=None):
        super(PickerWindow, self).__init__(parent or maya_main_window())
        self.setObjectName(WINDOW_OBJECT_NAME)
        self.setWindowTitle(WINDOW_TITLE)
        self.setWindowFlags(QtCore.Qt.Window)
        self.resize(420, 720)

        # Guards against the selection feedback loop: we set the scene
        # selection, Maya fires SelectionChanged, we would repaint and could
        # loop. The callback returns early while this is set.
        self._applying = False
        self._script_job = None

        self.view = PickerView(self)
        self.view.selection_requested.connect(self.apply_selection)
        self.view.hovered.connect(self._on_hover)

        central = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        layout.addWidget(self._build_toolbar())
        layout.addWidget(self._build_groups())
        layout.addWidget(self.view, 1)
        self.setCentralWidget(central)

        self.status = self.statusBar()
        self.status.showMessage("")

        self.refresh_availability()
        self.sync_from_scene()
        self._install_script_job()

    def _build_toolbar(self):
        bar = QtWidgets.QWidget(self)
        row = QtWidgets.QHBoxLayout(bar)
        row.setContentsMargins(0, 0, 0, 0)

        refresh = QtWidgets.QPushButton("Refresh", bar)
        refresh.clicked.connect(self.refresh_availability)
        row.addWidget(refresh)
        row.addStretch(1)

        for label in ("Build", "Bake+Delete"):
            button = QtWidgets.QPushButton(label, bar)
            button.setEnabled(False)
            button.setToolTip("Not implemented yet")
            row.addWidget(button)

        return bar

    def _build_groups(self):
        box = QtWidgets.QWidget(self)
        grid = QtWidgets.QGridLayout(box)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(3)
        for index, (label, group) in enumerate(_GROUP_BUTTONS):
            button = QtWidgets.QPushButton(label, box)
            button.setStyleSheet(
                "QPushButton { background: #3c3c3c; color: #d8d8d8; "
                "border: none; padding: 4px; border-radius: 3px; }"
                "QPushButton:hover { background: #4a4a4a; }")
            button.clicked.connect(
                lambda _checked=False, g=group: self._select_group(g))
            grid.addWidget(button, index // 5, index % 5)
        return box

    def _select_group(self, group):
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        from maya_overrig.picker_view import mode_for
        self.apply_selection(list(bodymap.group_members(group)),
                             mode_for(modifiers))

    def _on_hover(self, button_id):
        self.status.showMessage(button_id)

    def refresh_availability(self):
        """Dim buttons whose joint is not in the scene."""
        wanted = [b.joint for b in bodymap.BUTTONS]
        found = naming.resolve_many(wanted)
        joint_to_id = {b.joint: b.id for b in bodymap.BUTTONS}
        available = [joint_to_id[j] for j in found]
        self.view.set_available(available)

        missing = len(bodymap.BUTTONS) - len(available)
        if not available:
            self.status.showMessage(
                "No matching skeleton in the scene - every button disabled")
        elif missing:
            self.status.showMessage("{0} joint(s) missing".format(missing))

    def apply_selection(self, ids, mode):
        """Translate a picker request into a Maya selection change."""
        joint_to_id = {b.joint: b.id for b in bodymap.BUTTONS}
        wanted_joints = [bodymap.button_by_id(i).joint for i in ids]
        resolved = naming.resolve_many(wanted_joints)
        paths = [resolved[j] for j in wanted_joints if j in resolved]
        if not paths:
            return

        self._applying = True
        try:
            if mode == MODE_ADD:
                cmds.select(paths, add=True)
            elif mode == MODE_TOGGLE:
                cmds.select(paths, toggle=True)
            else:
                cmds.select(paths, replace=True)
        finally:
            self._applying = False

        self.sync_from_scene()

    def sync_from_scene(self):
        """Repaint button states from the current Maya selection."""
        selected = cmds.ls(selection=True, long=True) or []
        leaves = {naming.leaf(node) for node in selected}
        joint_to_id = {b.joint: b.id for b in bodymap.BUTTONS}
        ids = [joint_to_id[j] for j in leaves if j in joint_to_id]
        self.view.set_selected(ids)

    def _on_scene_selection_changed(self):
        if self._applying:
            return
        self.sync_from_scene()

    def _install_script_job(self):
        self._script_job = cmds.scriptJob(
            event=["SelectionChanged", self._on_scene_selection_changed],
            protected=False)

    def _kill_script_job(self):
        if self._script_job is not None and cmds.scriptJob(exists=self._script_job):
            cmds.scriptJob(kill=self._script_job, force=True)
        self._script_job = None

    def closeEvent(self, event):
        # Left alive, the job keeps firing into a dead widget and spams errors.
        self._kill_script_job()
        super(PickerWindow, self).closeEvent(event)


def show_picker():
    """Open the picker, replacing any window left from a previous call."""
    for widget in QtWidgets.QApplication.topLevelWidgets():
        if widget.objectName() == WINDOW_OBJECT_NAME:
            widget.close()
            widget.deleteLater()

    window = PickerWindow()
    window.show()
    return window
```

Replace `maya_overrig/__init__.py` with:

```python
"""Python wrapper around the OverRig MEL toolset."""

from maya_overrig.picker_window import show_picker

__all__ = ["show_picker"]
```

- [ ] **Step 2: Verify the unit suite still passes**

The Qt and bodymap tests must not have regressed. `picker_window` is not imported by them.

```bash
cd '/c/!!!Work/MayaScripts' && QT_QPA_PLATFORM=offscreen '/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe' -m unittest discover -s tests -t . -v
```

Expected: PASS, 41 tests.

- [ ] **Step 3: Verify the Maya-free boundary still holds**

```bash
cd '/c/!!!Work/MayaScripts' && grep -n "maya" maya_overrig/picker_view.py maya_overrig/bodymap.py
```

Expected: only the `from maya_overrig import bodymap` line in `picker_view.py`. Any
`import maya.cmds` here is a design violation — fix it rather than accepting it.

- [ ] **Step 4: Commit**

```bash
git add maya_overrig && git commit -m "feat(overrig): picker window and Maya selection wiring"
```

---

### Task 6: Live verification in the scene

**Files:**
- Create: `docs/superpowers/plans/verify_picker.py` (scratch verification script, committed so it can be rerun)

**Interfaces:**
- Consumes: everything above

Run inside the live Maya session through the command-port bridge described in the spec.

- [ ] **Step 1: Write the verification script**

Create `docs/superpowers/plans/verify_picker.py`:

```python
"""Live checks for the OverRig picker. Run inside Maya."""

import sys

REPO = r"C:/!!!Work/MayaScripts"
if REPO not in sys.path:
    sys.path.append(REPO)

for name in [m for m in list(sys.modules) if m.startswith("maya_overrig")]:
    del sys.modules[name]

import maya.cmds as cmds

from maya_overrig import bodymap, naming
from maya_overrig.picker_view import MODE_REPLACE
import maya_overrig

failures = []


def check(label, condition, detail=""):
    print("%-46s %s %s" % (label, "OK" if condition else "FAIL", detail))
    if not condition:
        failures.append(label)


resolved = naming.resolve_many([b.joint for b in bodymap.BUTTONS])
check("all 64 joints resolve in this scene", len(resolved) == 64,
      "resolved %d" % len(resolved))
check("hand_l does not resolve to ik_hand_l",
      resolved.get("hand_l", "").endswith("|hand_l"),
      resolved.get("hand_l", "<missing>"))

jobs_before = len(cmds.scriptJob(listJobs=True))
window = maya_overrig.show_picker()
check("window opened", window.isVisible())

cmds.select(clear=True)
window.apply_selection(["thigh_l"], MODE_REPLACE)
selection = cmds.ls(selection=True, long=True) or []
check("click selects the right joint",
      len(selection) == 1 and naming.leaf(selection[0]) == "thigh_l",
      str(selection))

window.apply_selection(list(bodymap.group_members("hand_r")), MODE_REPLACE)
check("hand group selects 19 joints",
      len(cmds.ls(selection=True) or []) == 19,
      str(len(cmds.ls(selection=True) or [])))

cmds.select("spine_03", replace=True)
window.sync_from_scene()
check("scene selection syncs back to the picker",
      window.view.items_by_id["spine_03"].state == "selected")

check("no button left dimmed on a full skeleton",
      all(i.available for i in window.view.items_by_id.values()))

window.close()
jobs_after = len(cmds.scriptJob(listJobs=True))
check("scriptJob cleaned up on close", jobs_after == jobs_before,
      "before %d after %d" % (jobs_before, jobs_after))

cmds.select(clear=True)
print("\n%s" % ("ALL CHECKS PASSED" if not failures
                else "FAILURES: %s" % failures))
```

- [ ] **Step 2: Run it in the live scene through the bridge**

Copy the script into the bridge's `code.py` and send it. Expected: every line `OK` and
`ALL CHECKS PASSED`.

- [ ] **Step 3: Screenshot the panel and tune the layout**

Capture the screen, crop the picker, and compare against the intent: a readable body
silhouette, fingers legible, left blue on the viewer's right, right red on the viewer's
left, nothing clipped. Adjust coordinates in `bodymap.py` and rerun the Task 1 tests after
any change — `test_no_rectangles_overlap` and `test_all_buttons_inside_canvas` must stay
green.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/verify_picker.py maya_overrig && git commit -m "test(overrig): live verification of the picker in Maya"
```

---

## Self-Review

**Spec coverage**

| Spec requirement | Task |
|---|---|
| 64-button animator joint set | 1 |
| Group buttons incl. Main/All | 1 (derivation), 5 (UI) |
| Hand-authored layout, UE5 names | 1 |
| Front view, left drawn on viewer right | 1 (`test_character_left_is_drawn_on_viewer_right`) |
| Namespace-tolerant resolution | 2 |
| Missing joint dims the button | 3 (`set_available`), 5 (`refresh_availability`) |
| No skeleton at all → all dimmed + status | 5 |
| Ambiguous match → first + warning | 2 |
| Palette, rounded rects, gradient | 3 |
| `state` enum extensible to knot/IK/baked | 3 |
| Hover outline + status line | 3, 4, 5 |
| Click / shift / ctrl | 4 |
| Marquee, shift-marquee | 4 |
| Zoom, pan | 4 |
| Scene → picker sync | 5 |
| Reentrancy guard | 5 (`_applying`) |
| scriptJob killed on close | 5, verified in 6 |
| Re-`show_picker()` destroys the old window | 5 |
| Build / Bake+Delete disabled stubs | 5 |
| View never imports maya.cmds | enforced in 5 step 3 |
| Entry point `maya_overrig.show_picker()` | 5 |

No gaps.

**Placeholder scan:** none — every code step carries real code, every run step a real command.

**Type consistency:** `set_available` / `set_selected` / `ids_in_rect` / `emit_click` /
`emit_marquee` / `mode_for` / `region_colour` / `resolve` / `resolve_many` / `leaf` /
`button_by_id` / `group_members` are spelled identically everywhere they appear. Mode
constants are `MODE_REPLACE` / `MODE_ADD` / `MODE_TOGGLE` throughout; state constants are
`STATE_NEUTRAL` / `STATE_SELECTED`.

One ordering note carried into Task 1 Step 3: `maya_overrig/__init__.py` starts empty and
only gains its `show_picker` import in Task 5, because importing it earlier would drag
`maya.cmds` into the plain-Python bodymap tests.
