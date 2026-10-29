# Connections: pick, then press - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every row of the Connections card records a pick and bakes nothing; the row's own check button, or the tab's one orange `Apply all · N`, is what bakes - and the card's four tabs read `label · segments · [W] · check`, one limb a row.

**Architecture:** A new pure module `maya_scenesetup/pending.py` holds what is picked but not applied - one set per RIG, keyed by its namespace, so the hub's card and a popup copy of it show the same picks. `connections.py`'s press handlers record into it instead of calling the engines; the engines (`switch_limb`, `toggle_world`, `switch_spine`, `apply`, `camera.set_parent`, `weaponaim`, `cameraaim`) are untouched and are called by the apply presses. Every painter (`_set_fkik`, `_set_spine`, `_set_menus`, `_set_camera`) paints the scene's state first and lays the pending overlay on top, so a refresh never eats a pick. The overlay is one new skin state, `want`, on segments and chips.

**Tech Stack:** Maya 2027 Python (`maya.cmds`), the hub's `maya_hubstyle` / `maya_hubqt` UI, `unittest` under `mayapy`, mayapy-standalone and disposable-GUI-Maya verify scripts.

Spec: `docs/superpowers/specs/2026-10-29-connections-pick-then-apply-design.md`.
Mockups (the animator chose B): https://claude.ai/artifact/M5ZtJhXiuWCDVRFUdHuFC3

## Global Constraints

- Repo `C:\!!!Work\MayaScripts`, branch `main`. The working tree carries the animator's unrelated uncommitted edits (`SkeldarAnim/maya_camshake.py`, `SkeldarAnim/maya_scenetabs/*`, `SkeldarAnim/maya_timebar/bar.py`, several tests, `docs/superpowers/plans/gaitguide/*`, untracked `docs/superpowers/plans/keyflash/`, `slime/`, `chat/`, `tests/hidefakes.py`): **never stage them**. Commit with explicit paths only: `git commit -F <msgfile> -- <paths>`.
- Commit messages: `feat(connections): ...`, `feat(hub): ...`, `test(connections): ...`, written to a file in the scratchpad and committed with `-F` (never a PowerShell here-string with quotes - trap 101), ending with `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- No system Python. Unit tests: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest <module> -v` from the repo root, `$env:QT_QPA_PLATFORM = 'offscreen'` for the Qt ones; never `python`; never `2>&1` on mayapy in PowerShell.
- The whole suite before the last commit: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v`. `tests/test_chat_deploy.py::Keys` fails on this machine for an unrelated reason (the animator's saved Cloudflare keys) - that one failure is expected.
- **Nothing bakes on a pick.** No press that only picks may call `switch_limb`, `switch_spine`, `toggle_world`, `apply`, `camera_parent`, `aim_mode`, `camera_aim`, `bake_across` or `release_across`.
- Pick keys are the strings `pending.py` defines; nothing else may spell them.
- Pending is one set per rig (`rig.namespace`, `""` for a root-namespace rig), dropped when the card reads another rig.
- Every painter writes under its quiet guard (`_FKIK_QUIET`, `_MENU_QUIET`): an edit of a box or a radio must not fire its command (trap 116).
- Every apply press: one undo chunk, opened by the press, closed in a `finally`; the chunks the engines open nest inside it.
- The classic hub (no Qt) has no `want` paint: there the pending picks show in the status line and in the counts only. Never make the classic hub's path raise.
- `maya_hubcopy`: every new control is a plain `cmds` control with a name (`cmds.checkBox`, `cmds.button`, `cmds.iconTextCheckBox`) - never a `*Grp`, which a popup copy cannot rename.
- Code style: match the module around it - its docstring voice (the animator's words quoted where they decided something), `# noqa: BLE001` on broad excepts, the date on a new rule.

---

### Task 1: `pending.py` - what is picked but not applied

**Files:**
- Create: `SkeldarAnim/maya_scenesetup/pending.py`
- Test: `tests/test_scenesetup_pending.py` (new)

**Interfaces:**
- Produces (used by Tasks 3-8):
  - keys: `SPINE = "spine"`, `AIM = "aim"`, `CAMERA = "camera"`, `CAMERA_POSITION = "camera:position"`, `CAMERA_AIM = "camaim"`; builders `limb_key(kind, side)` -> `"limb:Arm:R"`, `world_key(kind, side)` -> `"world:Arm:R"`, `parent_key(row)` -> `"parent:R"`
  - the store, keyed by a rig key (a plain string): `for_rig(key)` -> dict (a copy), `set_for(key, picks)` -> dict, `only(key)` (drops every other rig's), `clear()`
  - pure: `record(picks, pick, value, state)` -> dict, `without(picks, *picks_to_drop)` -> dict, `of_tab(picks, tab)` -> dict, `units(picks)` -> list, `count(picks)` -> int, `phrase(pick, value)` -> str, `text(picks)` -> str
  - `TAB = {"body": (...), "weapon": (...), "camera": (...)}`

- [ ] **Step 1: Write the failing test**

`tests/test_scenesetup_pending.py`:

```python
"""What is picked in the Connections card but not applied yet (2026-10-29).

The animator: «нужно сделать консистентно что бы перепекание происходило по
нажатию кнопки а не по разному в каждом разделе». Pure: the keys, the store
per rig, the count a press makes and the line the status says.

Spec: docs/superpowers/specs/2026-10-29-connections-pick-then-apply-design.md
"""

import os
import subprocess
import sys
import unittest

from maya_scenesetup import pending

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "SkeldarAnim")


class Keys(unittest.TestCase):

    def test_the_keys_are_spelled_once(self):
        self.assertEqual(pending.limb_key("Arm", "R"), "limb:Arm:R")
        self.assertEqual(pending.world_key("Leg", "L"), "world:Leg:L")
        self.assertEqual(pending.parent_key("W"), "parent:W")
        self.assertEqual((pending.SPINE, pending.AIM, pending.CAMERA,
                          pending.CAMERA_POSITION, pending.CAMERA_AIM),
                         ("spine", "aim", "camera", "camera:position", "camaim"))


class Record(unittest.TestCase):

    def test_a_pick_is_kept_and_the_dict_given_back_is_new(self):
        picks = {}
        out = pending.record(picks, "limb:Arm:R", "FK", "IK")
        self.assertEqual(out, {"limb:Arm:R": "FK"})
        self.assertEqual(picks, {})

    def test_a_pick_that_is_already_the_state_is_no_pick(self):
        out = pending.record({"limb:Arm:R": "FK"}, "limb:Arm:R", "IK", "IK")
        self.assertEqual(out, {})

    def test_a_pick_over_a_pick_replaces_it(self):
        out = pending.record({"limb:Arm:R": "FK"}, "limb:Arm:R", "IK", "FK")
        self.assertEqual(out, {"limb:Arm:R": "IK"})

    def test_a_false_pick_against_a_true_state_is_kept(self):
        #  W off while the limb IS in world: False is a pick, not an absence
        out = pending.record({}, "world:Arm:R", False, True)
        self.assertEqual(out, {"world:Arm:R": False})

    def test_without_drops_the_keys_named(self):
        out = pending.without({"a": 1, "b": 2, "c": 3}, "b", "zz")
        self.assertEqual(out, {"a": 1, "c": 3})


class Store(unittest.TestCase):

    def setUp(self):
        pending.clear()
        self.addCleanup(pending.clear)

    def test_one_set_per_rig(self):
        pending.set_for("Manny_Rig", {"spine": "IK"})
        pending.set_for("Creep_Rig", {"aim": True})
        self.assertEqual(pending.for_rig("Manny_Rig"), {"spine": "IK"})
        self.assertEqual(pending.for_rig("Creep_Rig"), {"aim": True})
        self.assertEqual(pending.for_rig("nobody"), {})

    def test_for_rig_hands_back_a_copy(self):
        pending.set_for("", {"spine": "IK"})
        got = pending.for_rig("")
        got["spine"] = "FK"
        self.assertEqual(pending.for_rig(""), {"spine": "IK"})

    def test_an_empty_set_forgets_the_rig(self):
        pending.set_for("Manny_Rig", {"spine": "IK"})
        pending.set_for("Manny_Rig", {})
        self.assertEqual(pending.for_rig("Manny_Rig"), {})

    def test_only_keeps_one_rig_s_picks(self):
        pending.set_for("Manny_Rig", {"spine": "IK"})
        pending.set_for("Creep_Rig", {"aim": True})
        pending.only("Creep_Rig")
        self.assertEqual(pending.for_rig("Manny_Rig"), {})
        self.assertEqual(pending.for_rig("Creep_Rig"), {"aim": True})


class Units(unittest.TestCase):
    """What a press does: a limb's mode and its W are ONE change."""

    def test_a_limb_s_mode_and_its_world_count_once(self):
        picks = {"limb:Arm:R": "IK", "world:Arm:R": True}
        self.assertEqual(pending.count(picks), 1)

    def test_the_camera_s_parent_and_its_position_count_once(self):
        picks = {"camera": "Chest", "camera:position": True}
        self.assertEqual(pending.count(picks), 1)

    def test_every_other_pick_counts_on_its_own(self):
        picks = {"limb:Arm:R": "FK", "limb:Leg:L": "IK", "spine": "IK",
                 "parent:L": "Weapon", "aim": True}
        self.assertEqual(pending.count(picks), 5)


class Tabs(unittest.TestCase):

    def test_each_tab_sees_only_its_own_picks(self):
        picks = {"limb:Arm:R": "FK", "world:Leg:L": True, "spine": "IK",
                 "parent:W": "Hand_L", "aim": True,
                 "camera": "Chest", "camera:position": True, "camaim": False}
        self.assertEqual(sorted(pending.of_tab(picks, "body")),
                         ["limb:Arm:R", "spine", "world:Leg:L"])
        self.assertEqual(sorted(pending.of_tab(picks, "weapon")),
                         ["aim", "parent:W"])
        self.assertEqual(sorted(pending.of_tab(picks, "camera")),
                         ["camaim", "camera", "camera:position"])
        self.assertEqual(pending.of_tab(picks, "object"), {})


class Text(unittest.TestCase):

    def test_a_phrase_a_pick(self):
        self.assertEqual(pending.phrase("limb:Arm:R", "FK"), "Arm R to FK")
        self.assertEqual(pending.phrase("world:Leg:L", True), "Leg L into world")
        self.assertEqual(pending.phrase("world:Leg:L", False), "Leg L out of world")
        self.assertEqual(pending.phrase("spine", "IK"), "the spine to IK")
        self.assertEqual(pending.phrase("parent:L", "Weapon"), "the left hand to Weapon")
        self.assertEqual(pending.phrase("parent:W", "Hand_L"), "the weapon to Hand L")
        self.assertEqual(pending.phrase("aim", True), "the weapon's aim on")
        self.assertEqual(pending.phrase("camera", "Chest"), "the camera to Chest")
        self.assertEqual(pending.phrase("camera:position", True),
                         "the camera's follow position only")
        self.assertEqual(pending.phrase("camaim", False), "the camera's aim off")

    def test_the_line_is_in_a_stable_order(self):
        picks = {"spine": "IK", "limb:Leg:L": "IK", "aim": True, "limb:Arm:R": "FK"}
        self.assertEqual(pending.text(picks),
                         "Arm R to FK, Leg L to IK, the spine to IK, "
                         "the weapon's aim on")

    def test_no_picks_no_line(self):
        self.assertEqual(pending.text({}), "")


class Pure(unittest.TestCase):

    def test_the_module_imports_no_maya(self):
        code = ("import sys; import pending; "
                "print([m for m in sys.modules if m.split('.')[0] == 'maya'])")
        out = subprocess.check_output(
            [sys.executable, "-I", "-c", code],
            cwd=os.path.join(PLUGIN, "maya_scenesetup"))
        self.assertEqual(out.decode().strip(), "[]")
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenesetup_pending -v`
Expected: FAIL - `ModuleNotFoundError: No module named 'maya_scenesetup.pending'`.

- [ ] **Step 3: Write the module**

`SkeldarAnim/maya_scenesetup/pending.py`:

```python
"""pending - what is picked in the Connections card but not applied yet.

The animator's ask (2026-10-29): «предложи несколько вариантов более удобного
разсположения инструментов в вкладке connections и нужно сделать консистентно
что бы перепекание происходило по нажатию кнопки а не по разному в каждом
разделе». Every row of the card records a pick; the row's check button, or
the tab's one Apply all, is what bakes.

This module is that record, stdlib only (a test pins it): the keys, the store
- ONE set per RIG, not per card, so the hub's card and a popup copy of it show
the same picks - what a press counts as one change, and the line the status
says. The resolution between a limb's mode and its W is in `connections.py`,
where both states are already read.

Spec: docs/superpowers/specs/2026-10-29-connections-pick-then-apply-design.md
"""

SPINE = "spine"
AIM = "aim"
CAMERA = "camera"
CAMERA_POSITION = "camera:position"
CAMERA_AIM = "camaim"

LIMB = "limb:"
WORLD = "world:"
PARENT = "parent:"

#  which picks belong to which tab of the card
TAB = {"body": (LIMB, WORLD, SPINE),
       "weapon": (PARENT, AIM),
       "camera": (CAMERA, CAMERA_POSITION, CAMERA_AIM)}

#  the order the status names them in, and the order of the sides inside it
_RANK = (LIMB, WORLD, SPINE, PARENT, AIM, CAMERA, CAMERA_POSITION, CAMERA_AIM)
_KIND_RANK = ("Arm", "Leg")
_SIDE_RANK = ("R", "L")
_ROW_RANK = ("R", "L", "W")

ROW_WORD = {"R": "the right hand", "L": "the left hand", "W": "the weapon"}

#  rig key -> {pick key: value}
PICKS = {}


# ------------------------------------------------------------------- keys

def limb_key(kind, side):
    """The pick of the limb of `kind` ('Arm' / 'Leg') on `side`: FK or IK."""
    return "%s%s:%s" % (LIMB, kind, side)


def world_key(kind, side):
    """The pick of that limb's W: True into world, False out of it."""
    return "%s%s:%s" % (WORLD, kind, side)


def parent_key(row):
    """The pick of the weapon tab's row R / L / W."""
    return "%s%s" % (PARENT, row)


# ------------------------------------------------------------------ store

def for_rig(key):
    """The picks standing for the rig `key` ('' is the root-namespace rig), a
    copy: a caller edits its own dict and hands it back to `set_for`."""
    return dict(PICKS.get(key, {}))


def set_for(key, picks):
    """Keep `picks` for the rig `key`; an empty set forgets the rig."""
    if picks:
        PICKS[key] = dict(picks)
    else:
        PICKS.pop(key, None)
    return for_rig(key)


def only(key):
    """Keep the picks of the rig `key` alone - another character's picks mean
    nothing on this one (the card drops them when it reads another rig)."""
    for other in [k for k in PICKS if k != key]:
        del PICKS[other]


def clear():
    PICKS.clear()


# ------------------------------------------------------------------- pure

def record(picks, pick, value, state):
    """A new dict with `pick` wanting `value` while the scene shows `state` -
    and with the pick dropped when it IS the state (a pick is a change)."""
    out = dict(picks)
    if value == state:
        out.pop(pick, None)
    else:
        out[pick] = value
    return out


def without(picks, *drop):
    """A new dict without the keys named (one that is not there is no error)."""
    return dict((k, v) for k, v in picks.items() if k not in drop)


def of_tab(picks, tab):
    """The picks of one tab of the card."""
    wants = TAB.get(tab, ())
    out = {}
    for key, value in picks.items():
        for want in wants:
            if key == want or (want.endswith(":") and key.startswith(want)):
                out[key] = value
                break
    return out


def units(picks):
    """The picks grouped into what one press does: a limb's mode and its W are
    one change (one `switch_limb`), the camera's parent and its Position only
    are one (one `camera_parent`)."""
    seen = []
    for key in sorted(picks, key=_rank):
        unit = key
        if key.startswith(LIMB) or key.startswith(WORLD):
            unit = LIMB + key.split(":", 1)[1]
        elif key == CAMERA_POSITION:
            unit = CAMERA
        if unit not in seen:
            seen.append(unit)
    return seen


def count(picks):
    """How many changes a press would make - the number on Apply all."""
    return len(units(picks))


def phrase(pick, value):
    """One pick in words, as the status says it."""
    if pick.startswith(LIMB):
        _, kind, side = pick.split(":")
        return "%s %s to %s" % (kind, side, value)
    if pick.startswith(WORLD):
        _, kind, side = pick.split(":")
        return "%s %s %s world" % (kind, side, "into" if value else "out of")
    if pick.startswith(PARENT):
        return "%s to %s" % (ROW_WORD.get(pick.split(":")[1], pick),
                             str(value).replace("_", " "))
    if pick == SPINE:
        return "the spine to %s" % value
    if pick == AIM:
        return "the weapon's aim %s" % ("on" if value else "off")
    if pick == CAMERA:
        return "the camera to %s" % value
    if pick == CAMERA_POSITION:
        return "the camera's follow %s" % ("position only" if value else "whole")
    if pick == CAMERA_AIM:
        return "the camera's aim %s" % ("on" if value else "off")
    return "%s to %s" % (pick, value)


def text(picks):
    """Every pick as one line, in a stable order: «Arm R to FK, Leg L to IK»."""
    return ", ".join(phrase(key, picks[key]) for key in sorted(picks, key=_rank))


def _rank(key):
    """(the pick's place in _RANK, the kind's, the side's) - a stable order."""
    for index, prefix in enumerate(_RANK):
        if key == prefix:
            return (index, 0, 0)
        if prefix.endswith(":") and key.startswith(prefix):
            parts = key.split(":")
            if prefix == PARENT:
                return (index, 0, _place(_ROW_RANK, parts[1]))
            return (index, _place(_KIND_RANK, parts[1]),
                    _place(_SIDE_RANK, parts[2]))
    return (len(_RANK), 0, 0)


def _place(order, value):
    return order.index(value) if value in order else len(order)
```

- [ ] **Step 4: Run the tests and make sure they pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenesetup_pending -v`
Expected: PASS, every test.

- [ ] **Step 5: Commit**

```bash
git add SkeldarAnim/maya_scenesetup/pending.py tests/test_scenesetup_pending.py
git commit -F <msgfile> -- SkeldarAnim/maya_scenesetup/pending.py tests/test_scenesetup_pending.py
```
Message: `feat(connections): pending.py - the picks a press bakes, one set per rig`

---

### Task 2: the skin's `want` state

A picked segment or chip that is not applied yet: the accent tint with an accent border, the hub's own pending language. `set_state` must repolish the control, or the property changes and nothing is redrawn.

**Files:**
- Modify: `SkeldarAnim/maya_hubstyle.py` (`_SHEET`, after the `segment`/`chip` `:checked` rules)
- Modify: `SkeldarAnim/maya_hubqt.py:3552-3570` (`set_state`)
- Test: `tests/test_hubstyle.py`, `tests/test_hubqt.py`

**Interfaces:**
- Produces: the stylesheet rules `QPushButton[skRole="segment"][skState="want"]` and `QCheckBox[skRole="chip"][skState="want"]`; `maya_hubqt.set_state(name, "want")` repolishes any role.

- [ ] **Step 1: Write the failing tests**

In `tests/test_hubstyle.py`, in the class that holds the other `_rule` tests:

```python
    def test_a_picked_segment_waiting_for_apply_is_accent(self):
        rule = self._rule('QPushButton[skRole="segment"][skState="want"]')
        self.assertIn(style.TOKENS["accent_tint"], rule)
        self.assertIn(style.TOKENS["accent"], rule)
        self.assertIn(style.TOKENS["accent_text"], rule)

    def test_a_picked_chip_waiting_for_apply_is_accent(self):
        rule = self._rule('QCheckBox[skRole="chip"][skState="want"]')
        self.assertIn(style.TOKENS["accent_tint"], rule)
        self.assertIn(style.TOKENS["accent"], rule)

    def test_the_want_rules_come_after_the_checked_ones(self):
        #  equal specificity: the later rule wins, and a pick is not the state
        sheet = style.stylesheet(1.0)
        self.assertLess(sheet.index('QPushButton[skRole="segment"]:checked'),
                        sheet.index('QPushButton[skRole="segment"][skState="want"]'))
        self.assertLess(sheet.index('QCheckBox[skRole="chip"]:checked'),
                        sheet.index('QCheckBox[skRole="chip"][skState="want"]'))
```

In `tests/test_hubqt.py`, beside the existing `set_state` test (around line 1350):

```python
    def test_set_state_repolishes_a_role_it_does_not_paint(self):
        from PySide6 import QtWidgets
        button = QtWidgets.QPushButton()
        button.setObjectName("skeldarTestSegment")
        button.setProperty("skRole", "segment")
        polished = []
        real = hubqt.repolish
        hubqt.repolish = lambda w: polished.append(w)
        self.addCleanup(setattr, hubqt, "repolish", real)
        real_find = hubqt.find
        hubqt.find = lambda name: button
        self.addCleanup(setattr, hubqt, "find", real_find)
        self.assertTrue(hubqt.set_state("skeldarTestSegment", "want"))
        self.assertEqual(button.property("skState"), "want")
        self.assertEqual(polished, [button])
```

- [ ] **Step 2: Run them to make sure they fail**

Run:
```
$env:QT_QPA_PLATFORM = 'offscreen'
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_hubstyle tests.test_hubqt -v
```
Expected: FAIL - the `want` rules are not in the sheet (`self._rule` raises or returns nothing), and `polished` is empty.

- [ ] **Step 3: Add the rules and the repolish**

In `maya_hubstyle.py`, straight after the segment's `:checked` rule:

```
QPushButton[skRole="segment"][skState="want"] {{ background: {accent_tint};
    border: {b1}px solid {accent}; color: {accent_text}; font-weight: bold; }}
```

and straight after the chip's `:checked` rule:

```
QCheckBox[skRole="chip"][skState="want"] {{ background: {accent_tint};
    border: {b1}px solid {accent}; color: {accent_text}; }}
```

with the comment the repo's style asks for:

```
/*  picked, not applied (2026-10-29, the Connections card): the thumb stays
    what the scene IS, the pick is outlined in the accent  */
```

In `maya_hubqt.py`, `set_state`:

```python
    widget.setProperty("skState", state or "")
    if widget.property("skRole") in ("toolrow", "subhead"):
        _paint_state(widget)
    else:
        #  2026-10-29: a segment's or a chip's `want` is the stylesheet's -
        #  the property alone changes nothing until the control is repolished
        repolish(widget)
    return True
```

- [ ] **Step 4: Run them and make sure they pass**

Run the same command. Expected: PASS.

- [ ] **Step 5: Commit**

Message: `feat(hub): a want state - a pick outlined in the accent until it is applied`
Paths: `SkeldarAnim/maya_hubstyle.py SkeldarAnim/maya_hubqt.py tests/test_hubstyle.py tests/test_hubqt.py`

---

### Task 3: the limb rows - one limb a row, W a chip, a check a row, no bake on a pick

**Files:**
- Modify: `SkeldarAnim/maya_scenesetup/connections.py` - the constants block (`~line 196`), `_fkik_row` (`1772-1806`), `_press_fkik` (`1590-1602`), `_set_fkik` (`1490-1504`), `refresh` (`1410`, the `_set_fkik` calls)
- Test: `tests/test_scenesetup_connections.py` (the `Panel` and `PanelCompact` classes), `tests/test_scenesetup_connections_pending.py` (new)

**Interfaces:**
- Consumes: `pending.limb_key`, `pending.world_key`, `pending.record`, `pending.without`, `pending.for_rig`, `pending.set_for`, `pending.count`, `pending.of_tab`; `maya_hubqt.set_state`
- Produces (used by Tasks 4-8):
  - `W_BOX = "skeldarConnectionsWorld_{0}_{1}"` (kind, side), a `cmds.checkBox` marked `chip`
  - `LIMB_APPLY = "skeldarConnectionsLimbApply_{0}_{1}"` (kind, side), `SPINE_APPLY = "skeldarConnectionsSpineApply"`
  - `APPLY_ALL = {"body": "skeldarConnectionsApplyBody", "weapon": "skeldarConnectionsApplyWeapon", "camera": "skeldarConnectionsApplyCamera"}`
  - `rig_key(rig)` -> str, `picks(rig=None)` -> dict, `remember(rig, picks)` -> dict, `_settled(rig, picks)` -> dict
  - `apply_limb(rig, kind, side, picks)` -> str, `_press_limb(side, mode, kind)`, `_press_limb_apply(side, kind)`, `_press_world(side, kind)`
  - `_light(name, state)` (the one place this module reaches Qt), `_paint_counts(picks)`, `_paint_pending(picks=None)` (the whole card's overlay; Tasks 4-8 extend it)
  - `NOTHING_PICKED = "nothing picked - press a segment first"`

- [ ] **Step 1: Write the failing test**

`tests/test_scenesetup_connections_pending.py`:

```python
"""Connections: pick, then press (2026-10-29).

The animator: «нужно сделать консистентно что бы перепекание происходило по
нажатию кнопки а не по разному в каждом разделе». A press of a segment, a
chip or a parent menu records a pick and bakes NOTHING; the row's check, or
the tab's Apply all, is what bakes.

Spec: docs/superpowers/specs/2026-10-29-connections-pick-then-apply-design.md
"""

import unittest

from maya_scenesetup import connections as cx
from maya_scenesetup import pending

from tests.test_scenesetup_connections import FakeMenuCmds


class Rig(object):
    namespace = "Manny_Rig"


class LimbPicks(unittest.TestCase):
    """The Body tab: a press records, the check bakes."""

    def setUp(self):
        pending.clear()
        self.addCleanup(pending.clear)
        self.baked = []
        self.real = (cx.cmds, cx.refresh, cx.maya_rigs.current_rig,
                     cx.switch_limb, cx.toggle_world, cx.read_scheme,
                     cx._limb_modes)
        self.fake = FakeMenuCmds()
        cx.cmds = self.fake
        cx.refresh = lambda *a: ""
        cx.maya_rigs.current_rig = lambda: (Rig(), "")
        cx.read_scheme = lambda *a, **k: {"L": None, "R": None}
        #  the scene a press CHANGES: both arms and legs IK, none in world.
        #  A press that is refused leaves it as it was, so the settle rule
        #  (a pick that came true drops, a refused one stays) is testable.
        self.modes = {cx.fkik.ARM: {"R": "IK", "L": "IK"},
                      cx.fkik.LEG: {"R": "IK", "L": "IK"}}
        self.worlds = {cx.fkik.ARM: [], cx.fkik.LEG: []}
        self.refuse = set()

        def limb_modes(rig, kind, worlds=None):
            if worlds is not None:
                worlds.extend(self.worlds[kind])
            return dict(self.modes[kind])

        def switch(side, mode, rig=None, highlight=None, kind=cx.fkik.ARM,
                   world=False):
            self.baked.append(("switch", kind, side, mode, world))
            if (kind, side) in self.refuse:
                return "%s is retargeting" % cx.fkik.LABEL[kind].format(side)
            self.modes[kind][side] = mode
            if world and side not in self.worlds[kind]:
                self.worlds[kind].append(side)
            return "baked"

        def world_toggle(side, rig=None, highlight=None, kind=cx.fkik.ARM):
            self.baked.append(("world", kind, side))
            if side in self.worlds[kind]:
                self.worlds[kind].remove(side)
            else:
                self.worlds[kind].append(side)
                self.modes[kind][side] = cx.fkik.IK
            return "baked"

        cx._limb_modes = limb_modes
        cx.switch_limb = switch
        cx.toggle_world = world_toggle
        cx.hubstyle.take_marks()
        cx.build_panel()
        self.marks = dict((m.name, m) for m in cx.hubstyle.take_marks())

    def tearDown(self):
        (cx.cmds, cx.refresh, cx.maya_rigs.current_rig, cx.switch_limb,
         cx.toggle_world, cx.read_scheme, cx._limb_modes) = self.real

    def test_a_press_of_fk_bakes_nothing_and_records_the_pick(self):
        self.fake.press_box(cx.fkik_box("R", "FK"))
        self.assertEqual(self.baked, [])
        self.assertEqual(cx.picks(Rig()),
                         {pending.limb_key(cx.fkik.ARM, "R"): "FK"})

    def test_a_press_of_the_mode_it_already_is_records_nothing(self):
        self.fake.press_box(cx.fkik_box("R", "IK"))
        self.assertEqual(self.baked, [])
        self.assertEqual(cx.picks(Rig()), {})

    def test_the_row_s_check_bakes_that_limb_only(self):
        self.fake.press_box(cx.fkik_box("R", "FK"))
        self.fake.press_button(cx.LIMB_APPLY.format(cx.fkik.ARM, "R"))
        self.assertEqual(self.baked, [("switch", cx.fkik.ARM, "R", "FK", False)])
        self.assertEqual(cx.picks(Rig()), {})

    def test_the_w_chip_records_and_asks_for_ik(self):
        self.fake.press_check(cx.W_BOX.format(cx.fkik.ARM, "L"), True)
        self.assertEqual(self.baked, [])
        #  the arm IS IK, so only the world pick is a change
        self.assertEqual(cx.picks(Rig()),
                         {pending.world_key(cx.fkik.ARM, "L"): True})

    def test_the_check_of_a_limb_asked_into_world_switches_with_world(self):
        self.fake.press_check(cx.W_BOX.format(cx.fkik.ARM, "L"), True)
        self.fake.press_button(cx.LIMB_APPLY.format(cx.fkik.ARM, "L"))
        self.assertEqual(self.baked, [("world", cx.fkik.ARM, "L")])

    def test_picking_fk_drops_a_pending_w(self):
        self.fake.press_check(cx.W_BOX.format(cx.fkik.ARM, "R"), True)
        self.fake.press_box(cx.fkik_box("R", "FK"))
        self.assertEqual(cx.picks(Rig()),
                         {pending.limb_key(cx.fkik.ARM, "R"): "FK"})

    def test_apply_all_bakes_every_limb_picked_in_the_tab(self):
        self.fake.press_box(cx.fkik_box("R", "FK"))
        self.fake.press_box(cx.fkik_box("L", "FK"))
        self.fake.press_button(cx.APPLY_ALL["body"])
        self.assertEqual(sorted(b[2] for b in self.baked), ["L", "R"])
        self.assertEqual(cx.picks(Rig()), {})

    def test_the_rows_are_one_limb_each_with_a_chip_and_a_check(self):
        self.assertEqual(self.marks[cx.W_BOX.format(cx.fkik.ARM, "R")].role, "chip")
        self.assertEqual(self.marks[cx.LIMB_APPLY.format(cx.fkik.ARM, "R")].role, "tool")
        boxes = [c[1][0] for c in self.fake.calls
                 if c[0] == "iconTextCheckBox" and not c[2].get("edit")]
        self.assertEqual(boxes[:4], [cx.fkik_box("R", "FK"), cx.fkik_box("R", "IK"),
                                     cx.fkik_box("L", "FK"), cx.fkik_box("L", "IK")])

    def test_another_rig_s_picks_are_dropped(self):
        self.fake.press_box(cx.fkik_box("R", "FK"))
        other = Rig()
        other.namespace = "Creep_Rig"
        cx.maya_rigs.current_rig = lambda: (other, "")
        self.assertEqual(cx.picks(other), {})
        self.assertEqual(pending.for_rig("Manny_Rig"), {})

    def test_a_refused_press_keeps_its_pick(self):
        self.refuse.add((cx.fkik.ARM, "R"))
        self.fake.press_box(cx.fkik_box("R", "FK"))
        self.fake.press_button(cx.LIMB_APPLY.format(cx.fkik.ARM, "R"))
        self.assertEqual(self.baked, [("switch", cx.fkik.ARM, "R", "FK", False)])
        self.assertEqual(cx.picks(Rig()),
                         {pending.limb_key(cx.fkik.ARM, "R"): "FK"})
```

`FakeMenuCmds` needs two presses it does not have yet - add them to it in `tests/test_scenesetup_connections.py` (it already has `press_box`):

```python
    def press_check(self, name, value):
        """A `cmds.checkBox` pressed: its value and its changeCommand."""
        box = self.checks[name]
        box["value"] = value
        if box["changeCommand"]:
            box["changeCommand"](value)

    def press_button(self, name):
        command = self.commands.get(name)
        if command:
            command(False)
```

(`FakeUiCmds` already records `checkBox` calls; if `self.checks` / `self.commands` are not there, add them in the same shape as `self.boxes`, and keep `tests/uifakes.py` the one place that knows a control's shape.)

- [ ] **Step 2: Run it to make sure it fails**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenesetup_connections_pending -v`
Expected: FAIL - `AttributeError: module 'maya_scenesetup.connections' has no attribute 'W_BOX'`.

- [ ] **Step 3: Write the implementation**

In the constants block of `connections.py`:

```python
#  pick, then press (2026-10-29): W is a chip beside the modes, every row
#  carries its own check, and each tab one Apply all; nothing bakes on a pick
W_BOX = "skeldarConnectionsWorld_{0}_{1}"
LIMB_APPLY = "skeldarConnectionsLimbApply_{0}_{1}"
SPINE_APPLY = "skeldarConnectionsSpineApply"
APPLY_ALL = {"body": "skeldarConnectionsApplyBody",
             "weapon": "skeldarConnectionsApplyWeapon",
             "camera": "skeldarConnectionsApplyCamera"}
```

and, beside `NOTHING_TO_DO`:

```python
NOTHING_PICKED = "nothing picked - press a segment first"
```

The store and its rig key:

```python
def rig_key(rig):
    """The key a rig's picks are kept under: its namespace ('' for a rig in
    the root namespace), None with no rig."""
    return None if rig is None else getattr(rig, "namespace", "")


def picks(rig=None):
    """What is picked on `rig` and not applied. Reading drops every other
    rig's picks: a pick belongs to the character it was made on."""
    if rig is None:
        rig, _refusal = maya_rigs.current_rig()
    key = rig_key(rig)
    if key is None:
        return {}
    pending.only(key)
    return pending.for_rig(key)


def remember(rig, chosen):
    """Keep `chosen` as this rig's picks and paint the card for them."""
    key = rig_key(rig)
    if key is None:
        return {}
    out = pending.set_for(key, chosen)
    _paint_pending(out)
    return out


def _states(rig):
    """What the scene shows, by pick key - the one reader a pick and a press
    settle against. Tasks 5 and 6 add the parent, aim and camera keys."""
    out = {}
    for kind in (fkik.ARM, fkik.LEG):
        worlds = []
        modes = _limb_modes(rig, kind, worlds)
        for side in SIDES:
            out[pending.limb_key(kind, side)] = modes.get(side)
            out[pending.world_key(kind, side)] = side in worlds
    out[pending.SPINE] = _spine_state(rig)[0]
    return out


def _settled(rig, chosen, *keys):
    """`chosen` after a press: the picks in `keys` (or all of them) re-read
    against the scene - one that came true drops, one a refusal left standing
    stays. Nothing here reads a refusal's text (2026-10-29)."""
    out = dict(chosen)
    states = _states(rig)
    for key in (keys or tuple(out)):
        if key in out and key in states:
            out = pending.record(out, key, out[key], states[key])
    return out


def _light(name, state):
    """The skin's state of control `name` (maya_hubqt.set_state): a picked
    segment or chip "want", a row's check "wait". Nothing without Maya's UI -
    the one place this module reaches Qt (the Tools card's helper)."""
    try:
        import maya_hubqt
        if maya_hubqt.available():
            maya_hubqt.set_state(name, state)
    except Exception:                                        # noqa: BLE001
        pass


def _paint_counts(chosen):
    """Each tab's Apply all reads what it would bake: «Apply all · 2»."""
    for tab, name in APPLY_ALL.items():
        if not cmds.control(name, exists=True):
            continue
        number = pending.count(pending.of_tab(chosen, tab))
        cmds.button(name, edit=True,
                    label="Apply all" if not number
                    else "Apply all · %d" % number)


def _paint_pending(chosen=None):
    """The card's pending overlay. The row painters lay `want` and `wait` on
    their own rows; this is what every other press calls to bring the counts
    (and, from Task 8, the whole card) into step."""
    if chosen is None:
        chosen = picks()
    _paint_counts(chosen)
```

`_fkik_row` becomes one row a limb:

```python
def _fkik_row(kind):
    """One row a limb (2026-10-29, the animator: «более удобного
    разсположения»): `Arm R [FK | IK] (W) check`. Two limbs shared a row
    until then and Maya's one adjustable column gave their tracks 86 and 128
    px, so with W among the segments each was ~28 px wide; one row a limb
    gives the segments the width of the card."""
    for side in SIDES[::-1]:
        label = fkik.LABEL[kind].format(side)
        cmds.rowLayout(numberOfColumns=4, adjustableColumn=2,
                       columnWidth4=(hubstyle.pick(48, 64), 110,
                                     hubstyle.pick(28, 34),
                                     hubstyle.tool_width(66)),
                       columnAttach=[(1, "left", 0), (2, "both", 3),
                                     (3, "both", 2), (4, "right", 0)])
        _row_label(label.replace("_", " "))
        segments = cmds.rowLayout(numberOfColumns=len(fkik.MODES),
                                  columnAttach=[(i + 1, "both", 1)
                                                for i in range(len(fkik.MODES))])
        hubstyle.mark(segments, "segments", layout=True)
        noun = "leg" if kind == fkik.LEG else "arm"
        for mode in fkik.MODES:
            hubstyle.mark(cmds.iconTextCheckBox(
                fkik_box(side, mode, kind), style="textOnly", label=mode,
                height=hubstyle.height("segment", 22), value=False,
                annotation="{0} to {1} - picked, not baked: press the row's "
                           "check, or Apply all. Over the highlighted range, "
                           "else the whole take; the {2} keeps what it "
                           "shows".format(label, mode, noun),
                onCommand=_press_limb(side, mode, kind),
                offCommand=_press_limb(side, mode, kind)), "segment")
        cmds.setParent("..")
        end = "foot" if kind == fkik.LEG else "hand"
        hubstyle.mark(cmds.checkBox(
            W_BOX.format(kind, side), label="W", value=False,
            annotation="{0} in world: the IK {1} on a world control (Tools > "
                       "World x2: a Move box, Rotate rings), keyed on its IK "
                       "keys - it stays in the scene while Main moves. Picked, "
                       "not baked.".format(label, end),
            changeCommand=_press_world(side, kind)), "chip")
        hubstyle.mark(cmds.button(
            LIMB_APPLY.format(kind, side),
            label=hubstyle.tool_label("Apply"),
            width=hubstyle.tool_width(66),
            height=hubstyle.height("small", 24),
            annotation="bake what is picked on %s" % label.replace("_", " "),
            command=_press_limb_apply(side, kind)), "tool", "check")
        cmds.setParent("..")
```

The presses:

```python
def _press_limb(side, mode, kind=fkik.ARM):
    """A mode pressed: a PICK, nothing baked (2026-10-29). FK drops a pending
    W - a limb in FK has no world control (`switch_limb` takes it off)."""
    def go(*_args):
        if _FKIK_QUIET["on"]:
            return None
        rig, refusal = maya_rigs.current_rig()
        if rig is None:
            return _status(refusal)
        worlds = []
        shown = _limb_modes(rig, kind, worlds).get(side)
        chosen = pending.record(picks(rig), pending.limb_key(kind, side),
                                mode, shown)
        if mode == fkik.FK:
            chosen = pending.without(chosen, pending.world_key(kind, side))
        return _status(_picked_text(remember(rig, chosen)))
    return go


def _press_world(side, kind=fkik.ARM):
    """The W chip: a pick. W means "the IK on a world control", so it asks for
    IK too where the limb is not IK yet."""
    def go(*_args):
        if _FKIK_QUIET["on"]:
            return None
        rig, refusal = maya_rigs.current_rig()
        if rig is None:
            return _status(refusal)
        worlds = []
        modes = _limb_modes(rig, kind, worlds)
        wanted = bool(cmds.checkBox(W_BOX.format(kind, side), query=True,
                                    value=True))
        chosen = pending.record(picks(rig), pending.world_key(kind, side),
                                wanted, side in worlds)
        if wanted:
            chosen = pending.record(chosen, pending.limb_key(kind, side),
                                    fkik.IK, modes.get(side))
        return _status(_picked_text(remember(rig, chosen)))
    return go


def apply_limb(rig, kind, side, chosen):
    """Bake what is picked on one limb: its mode and its W are one press."""
    mode = chosen.get(pending.limb_key(kind, side))
    world = chosen.get(pending.world_key(kind, side))
    if mode is None and world is None:
        return NOTHING_TO_DO
    if mode is None:
        return toggle_world(side, rig=rig, kind=kind)
    return switch_limb(side, mode, rig=rig, kind=kind, world=bool(world))


def _press_limb_apply(side, kind=fkik.ARM):
    def go(*_args):
        def act():
            rig, refusal = maya_rigs.current_rig()
            if rig is None:
                return refusal
            chosen = picks(rig)
            text = apply_limb(rig, kind, side, chosen)
            remember(rig, _settled(rig, chosen,
                                   pending.limb_key(kind, side),
                                   pending.world_key(kind, side)))
            return text
        return _run(act)
    return go
```

`_press_fkik` and `_press_spine`'s bake paths go; `switch_arm` / `switch_limb` / `toggle_world` stay as they are.

The painter paints the state, then the pending overlay:

```python
def _set_fkik(modes, kind=fkik.ARM, worlds=(), chosen=None):
    """Light each limb's mode, neither when mixed or missing; its W while it is
    in world. Then the pending overlay (2026-10-29): the picked box and chip
    carry the skin's `want`, the row's label and its check light. Quiet: a
    box's own command must not fire from here (trap 116)."""
    chosen = picks() if chosen is None else chosen
    _FKIK_QUIET["on"] = True
    try:
        for side in SIDES:
            for mode in fkik.MODES:
                name = fkik_box(side, mode, kind)
                if cmds.iconTextCheckBox(name, exists=True):
                    cmds.iconTextCheckBox(name, edit=True,
                                          value=modes.get(side) == mode)
                    _light(name, "want" if chosen.get(
                        pending.limb_key(kind, side)) == mode else "")
            box = W_BOX.format(kind, side)
            if cmds.checkBox(box, exists=True):
                wanted = chosen.get(pending.world_key(kind, side))
                cmds.checkBox(box, edit=True,
                              value=side in worlds if wanted is None else wanted)
                _light(box, "" if wanted is None else "want")
            check = LIMB_APPLY.format(kind, side)
            if cmds.control(check, exists=True):
                _light(check, "wait" if (
                    pending.limb_key(kind, side) in chosen
                    or pending.world_key(kind, side) in chosen) else "")
    finally:
        _FKIK_QUIET["on"] = False
    _paint_counts(chosen)
```

The W chip shows the pick where one stands and the scene otherwise, because a
`cmds.checkBox` has one value - it is the W pick's own mark, and `_light` makes
it accent so it cannot be read as the state. `_light` is this module's only
reach into Qt (`maya_hubqt` imported inside it, as `maya_tools/panel.py` does):
with no Qt it does nothing, which is the classic hub's path - there the picks
show in the status line and in the counts only.

- [ ] **Step 4: Run the tests and make sure they pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenesetup_connections_pending tests.test_scenesetup_connections -v`
Expected: PASS for the new module. `tests.test_scenesetup_connections` will fail where it pins the old shape - `test_three_rows_each_with_segments_and_apply_then_apply_all` (the button labels), the `fkik_box(side, cx.W_MODE)` boxes (`~497-509`), and the `PanelCompact` heights. Update those tests to the new shape in this task: the W box is `cx.W_BOX.format(kind, side)`, each limb row ends in `cx.LIMB_APPLY`, and `W_MODE` is gone from `fkik.MODES + (W_MODE,)` walks. Keep every assertion as strict as it was.

- [ ] **Step 5: Commit**

Message: `feat(connections): the limb rows pick, the row's check bakes; W a chip`
Paths: `SkeldarAnim/maya_scenesetup/connections.py tests/test_scenesetup_connections.py tests/test_scenesetup_connections_pending.py tests/uifakes.py`

---

### Task 4: the spine row and the Body tab's `Apply all · N`

**Files:**
- Modify: `SkeldarAnim/maya_scenesetup/connections.py` - `_spine_row` (`1810-1831`), `_set_spine` (`1460-1470`), `_press_spine` (`1604-1611`), `build_panel` (the body column)
- Test: `tests/test_scenesetup_connections_pending.py`

**Interfaces:**
- Consumes: Task 1's keys, Task 3's `picks` / `remember` / `APPLY_ALL` / `_paint_pending`
- Produces: `apply_body(rig, chosen)` -> str, `_press_apply_body`, `SPINE_APPLY`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_scenesetup_connections_pending.py`:

```python
class SpineAndBody(LimbPicks):
    """The spine's own check, and the tab's Apply all - one undo chunk."""

    def setUp(self):
        LimbPicks.setUp(self)
        self.real_spine = (cx.switch_spine, cx._spine_state)
        cx._spine_state = lambda rig: ("FK", False)
        cx.switch_spine = lambda mode, rig=None, highlight=None: \
            self.baked.append(("spine", mode)) or "baked"
        self.addCleanup(lambda: setattr(cx, "switch_spine", self.real_spine[0]))
        self.addCleanup(lambda: setattr(cx, "_spine_state", self.real_spine[1]))

    def test_a_press_of_the_spine_records_only(self):
        self.fake.press_box(cx.FKIK_BOX_SPINE.format("IK"))
        self.assertEqual(self.baked, [])
        self.assertEqual(cx.picks(Rig()), {pending.SPINE: "IK"})

    def test_the_spine_s_check_bakes_it(self):
        self.fake.press_box(cx.FKIK_BOX_SPINE.format("IK"))
        self.fake.press_button(cx.SPINE_APPLY)
        self.assertEqual(self.baked, [("spine", "IK")])
        self.assertEqual(cx.picks(Rig()), {})

    def test_apply_all_takes_the_limbs_and_the_spine_in_one_chunk(self):
        self.fake.press_box(cx.fkik_box("R", "FK"))
        self.fake.press_box(cx.FKIK_BOX_SPINE.format("IK"))
        self.fake.press_button(cx.APPLY_ALL["body"])
        self.assertEqual(self.baked,
                         [("switch", cx.fkik.ARM, "R", "FK", False), ("spine", "IK")])
        self.assertEqual(cx.picks(Rig()), {})
        chunks = [c[2].get("chunkName") for c in self.fake.calls
                  if c[0] == "undoInfo" and c[2].get("openChunk")]
        self.assertEqual(chunks.count("Connections: Apply all"), 1)

    def test_the_count_is_on_the_button(self):
        self.fake.press_box(cx.fkik_box("R", "FK"))
        self.fake.press_box(cx.FKIK_BOX_SPINE.format("IK"))
        label = [c[2]["label"] for c in self.fake.calls
                 if c[0] == "button" and c[1] == (cx.APPLY_ALL["body"],)
                 and c[2].get("edit")][-1]
        self.assertEqual(label, "Apply all \u00b7 2")

    def test_with_nothing_picked_the_button_reads_plain_and_bakes_nothing(self):
        label = [c[2]["label"] for c in self.fake.calls
                 if c[0] == "button" and c[1] == (cx.APPLY_ALL["body"],)][0]
        self.assertEqual(label, "Apply all")
        self.fake.press_button(cx.APPLY_ALL["body"])
        self.assertEqual(self.baked, [])
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenesetup_connections_pending -v`
Expected: FAIL - no `SPINE_APPLY`, no `APPLY_ALL["body"]` button.

- [ ] **Step 3: Write the implementation**

`_spine_row` gains the check (the same four columns, an empty third), `_press_spine` records (the `_press_limb` shape with `pending.SPINE`), `_set_spine` paints `want` on the picked mode and `wait` on `SPINE_APPLY`, and the body column ends in:

```python
    hubstyle.mark(cmds.button(
        APPLY_ALL["body"], label="Apply all",
        height=hubstyle.height("button", 32),
        annotation="bake every pick in this tab - one undo",
        command=_press_apply_body), "primary", "check")
```

with

```python
def apply_body(rig, chosen):
    """Every limb picked, then the spine - one undo chunk, the notes joined."""
    notes = []
    for kind in (fkik.ARM, fkik.LEG):
        for side in SIDES[::-1]:
            if (pending.limb_key(kind, side) in chosen
                    or pending.world_key(kind, side) in chosen):
                notes.append(apply_limb(rig, kind, side, chosen))
    if pending.SPINE in chosen:
        notes.append(switch_spine(chosen[pending.SPINE], rig=rig))
    return "; ".join(n for n in notes if n) or NOTHING_TO_DO


def _press_apply_body(*_args):
    def act():
        rig, refusal = maya_rigs.current_rig()
        if rig is None:
            return refusal
        chosen = pending.of_tab(picks(rig), "body")
        if not chosen:
            return NOTHING_PICKED
        cmds.undoInfo(openChunk=True, chunkName="Connections: Apply all")
        try:
            return apply_body(rig, chosen)
        finally:
            cmds.undoInfo(closeChunk=True)
            remember(rig, _settled(rig, picks(rig)))
    return _run(act)
```

`NOTHING_PICKED` is Task 3's, beside `NOTHING_TO_DO`. `_paint_counts` (Task 3)
finds the body's button the moment it exists, so the count needs nothing new
here, and `_settled` leaves standing whatever a refusal did not change.

- [ ] **Step 4: Run the tests and make sure they pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenesetup_connections_pending tests.test_scenesetup_connections -v`
Expected: PASS.

- [ ] **Step 5: Commit**

Message: `feat(connections): the spine's check and the Body tab's Apply all · N`
Paths: `SkeldarAnim/maya_scenesetup/connections.py tests/test_scenesetup_connections_pending.py`

---

### Task 5: the Weapon tab - the state stays lit, the pick is `want`, the aim is a row

The three parent rows keep their collections showing **the scene**; the pick lives in `pending` and is painted `want`. `menus()` keeps meaning "what the scene shows"; the presses read `wanted_menus(rig)`.

**Files:**
- Modify: `SkeldarAnim/maya_scenesetup/connections.py` - `menus` (`1367-1384`), `_set_menus` (`1396-1409`), `_menu_changed` (`1554-1564`), `_press_row` (`1566-1576`), `_press_apply_all` (`1578-1580`), `_press_aim` (`1750-1762`), `build_panel` (the weapon column: the Aim caption's buttons become a row)
- Test: `tests/test_scenesetup_connections_pending.py`, `tests/test_scenesetup_connections.py` (the `Panel` labels and the aim tests)

**Interfaces:**
- Produces: `AIM_MENU = "skeldarConnectionsAim"`, `AIM_SEGMENT = "skeldarConnectionsAim_{0}"` (`"Default"` / `"Aim_Mode"`), `AIM_APPLY = "skeldarConnectionsAimApply"`, `ROW_APPLY = "skeldarConnectionsRowApply_{0}"`, `wanted_menus(rig)` -> dict, `apply_weapon(rig, chosen)` -> str

- [ ] **Step 1: Write the failing test**

```python
class WeaponPicks(unittest.TestCase):
    """The parents and the aim: a pick leaves the scene's state lit."""

    def setUp(self):
        pending.clear()
        self.addCleanup(pending.clear)
        self.done = []
        self.real = (cx.cmds, cx.refresh, cx.maya_rigs.current_rig,
                     cx.read_scheme, cx.apply, cx.aim_mode, cx._limb_modes,
                     cx.weapon_of)
        self.fake = FakeMenuCmds()
        cx.cmds = self.fake
        cx.refresh = lambda *a: ""
        cx.maya_rigs.current_rig = lambda: (Rig(), "")
        cx._limb_modes = lambda rig, kind, worlds=None: {}
        #  the scene: the weapon in the right hand, the left hand free
        cx.read_scheme = lambda *a, **k: {"L": None, "R": cx.HOLDS}
        cx.weapon_of = lambda *a, **k: "LongSwordMesh"
        cx.apply = lambda wanted, rig=None, weapon=None: \
            self.done.append(("apply", wanted)) or "applied"
        cx.aim_mode = lambda rig=None, weapon=None, on=True: \
            self.done.append(("aim", on)) or "aimed"
        cx.hubstyle.take_marks()
        cx.build_panel()

    def tearDown(self):
        (cx.cmds, cx.refresh, cx.maya_rigs.current_rig, cx.read_scheme,
         cx.apply, cx.aim_mode, cx._limb_modes, cx.weapon_of) = self.real

    def test_a_parent_pick_bakes_nothing_and_leaves_the_state_lit(self):
        self.fake.press_segment(cx.segment_name("L", cx.WEAPON))
        self.assertEqual(self.done, [])
        self.assertEqual(cx.picks(Rig()), {pending.parent_key("L"): "Weapon"})
        #  the collection still shows the scene: the left hand is Free
        self.assertEqual(cx.menus()["L"], "Free")
        self.assertEqual(cx.wanted_menus(Rig())["L"], "Weapon")

    def test_the_row_s_apply_bakes_that_row_only(self):
        self.fake.press_segment(cx.segment_name("L", cx.WEAPON))
        self.fake.press_button(cx.ROW_APPLY.format("L"))
        self.assertEqual(self.done, [("apply", {"L": cx.FOLLOWS, "R": cx.HOLDS})])
        self.assertEqual(cx.picks(Rig()), {})

    def test_the_aim_is_a_row_and_a_pick(self):
        self.fake.press_segment(cx.AIM_SEGMENT.format("Aim_Mode"))
        self.assertEqual(self.done, [])
        self.assertEqual(cx.picks(Rig()), {pending.AIM: True})
        self.fake.press_button(cx.AIM_APPLY)
        self.assertEqual(self.done, [("aim", True)])

    def test_apply_all_takes_the_parents_then_the_aim_in_one_chunk(self):
        self.fake.press_segment(cx.segment_name("L", cx.WEAPON))
        self.fake.press_segment(cx.AIM_SEGMENT.format("Aim_Mode"))
        self.fake.press_button(cx.APPLY_ALL["weapon"])
        self.assertEqual([d[0] for d in self.done], ["apply", "aim"])
        chunks = [c[2].get("chunkName") for c in self.fake.calls
                  if c[0] == "undoInfo" and c[2].get("openChunk")]
        self.assertEqual(chunks.count("Connections: Apply all"), 1)

    def test_the_aim_buttons_are_gone(self):
        labels = [c[2].get("label") for c in self.fake.calls if c[0] == "button"]
        self.assertNotIn("Aim Mode", labels)
        self.assertNotIn("Default", labels)
```

`FakeMenuCmds` gains `press_segment(name)` (it already keeps `self.on[name]`):

```python
    def press_segment(self, name):
        """A radio segment pressed: its collection's selection and onCommand."""
        self.selected[self.owner[name]] = name
        if self.on[name]:
            self.on[name](True)
```

- [ ] **Step 2: Run it to make sure it fails**

Expected: FAIL - no `AIM_SEGMENT`, no `ROW_APPLY`, `wanted_menus` missing.

- [ ] **Step 3: Write the implementation**

- `menus()` is unchanged in meaning: what the collections show. `_set_menus` keeps writing the scene's state under `_MENU_QUIET`, and then paints `want` on the picked segment of each row plus `wait` on its `ROW_APPLY`.
- `_menu_changed(row)` becomes a recorder: read the pressed segment, resolve a cycle against the WANTED menus, store, re-assert the state in the collections (quiet), paint:

```python
def _menu_changed(row):
    """A parent picked: a pick, not a bake (2026-10-29). A cycle - the weapon
    in Hand_R while Hand_R follows it - is still fixed here (`resolve_menus`),
    and the fix is a pick too."""
    def go(*_args):
        if _MENU_QUIET["on"]:
            return None
        rig, refusal = maya_rigs.current_rig()
        if rig is None:
            return _status(refusal)
        #  the scene's state comes from the SCENE: the collection already holds
        #  the segment just pressed, which is the pick
        shown = menus_from_scheme(read_scheme(rig))
        fixed, note = resolve_menus(menus(), row)
        chosen = picks(rig)
        for each in fixed:
            chosen = pending.record(chosen, pending.parent_key(each),
                                    fixed[each], shown[each])
        chosen = remember(rig, chosen)
        _set_menus(shown, chosen)       # the state back in the collections
        text = _picked_text(chosen)
        return _status((note + "; " + text) if note else text)
    return go
```

`_set_menus(shown)` at the end of the recorder puts the collections back on the scene's state (quiet) and paints `want` on each row's pick, so the lit thumb never stops meaning what the scene is. `wanted_menus(rig)` is that state overlaid with the picks, and every apply reads it:

```python
def wanted_menus(rig):
    """The three rows as a press would set them: the scene's, with the picks
    on top."""
    out = menus()
    chosen = picks(rig)
    for row in _ROW_KEYS:
        value = chosen.get(pending.parent_key(row))
        if value is not None:
            out[row] = value
    return out
```

(`_ROW_KEYS = tuple(row for row, _choices in _ROWS)`.)

- `_press_row(row)` applies `wanted_for_row(read_scheme(rig), row, wanted_menus(rig)[row])` and drops that row's pick.
- The aim row replaces the two buttons:

```python
    _caption("aim", "Aim")
    cmds.rowLayout(numberOfColumns=3, adjustableColumn=2,
                   columnWidth3=(hubstyle.pick(48, 64), 110,
                                 hubstyle.tool_width(66)),
                   columnAttach=[(1, "left", 0), (2, "both", 4), (3, "right", 0)])
    _row_label("Aim")
    segments = cmds.rowLayout(numberOfColumns=2,
                              columnAttach=[(1, "both", 1), (2, "both", 1)])
    hubstyle.mark(segments, "segments", layout=True)
    cmds.iconTextRadioCollection(AIM_MENU)
    for choice, label in ((DEFAULT_AIM, "Default"), (AIM_ON, "Aim Mode")):
        hubstyle.mark(cmds.iconTextRadioButton(
            AIM_SEGMENT.format(choice), style="textOnly", label=label,
            height=hubstyle.height("segment", 22), select=choice == DEFAULT_AIM,
            annotation=AIM_TIPS[choice],
            onCommand=_press_aim_pick(choice)), "segment")
    cmds.setParent("..")
    hubstyle.mark(cmds.button(
        AIM_APPLY, label=hubstyle.tool_label("Apply"),
        width=hubstyle.tool_width(66), height=hubstyle.height("small", 24),
        annotation="enter or leave Aim Mode as picked",
        command=_press_aim_apply), "tool", "check")
    cmds.setParent("..")
```

with

```python
DEFAULT_AIM, AIM_ON = "Default", "Aim_Mode"
#  the two annotations the Aim Mode / Default buttons carried, word for word
AIM_TIPS = {
    AIM_ON: "The weapon's rotation aims at two world controllers (a target past "
            "the tip, an up beside it), keyed on the weapon's own keys - it stands "
            "where it stood on every key. Animate the controllers.",
    DEFAULT_AIM: "The aim baked back onto the weapon's rotation on the controllers' "
                 "keys, the controllers removed",
}
```

`aim_mode(rig, weapon, on)` is untouched; `_press_aim(on)` goes, and the hotkey rows `connections.aim` / `.default` keep calling `aim_mode` directly. `_states` (Task 3) gains this tab's keys, so a pick that came true settles like the limbs':

```python
    for row, value in menus_from_scheme(read_scheme(rig)).items():
        out[pending.parent_key(row)] = value
    weapon = weapon_of(rig)
    out[pending.AIM] = bool(weapon) and weaponaim.is_aimed(weapon)
```
- `apply_weapon(rig, chosen)`: the parents through one `apply(scheme_from_menus(wanted_menus(rig)))` when any `parent:` pick stands, then `aim_mode(on=chosen[pending.AIM])` when the aim is picked; `_press_apply_all` wraps it in the `Connections: Apply all` chunk, as Task 4's body press does.

- [ ] **Step 4: Run the tests and make sure they pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenesetup_connections_pending tests.test_scenesetup_connections -v`
Expected: PASS. The `Panel` test's button-label list (`~303`) and any test naming `AIM_BUTTON` / `DEFAULT_BUTTON` are updated here to the new shape - keep them as strict as they were, and keep a test that the aim's two annotations survived word for word.

- [ ] **Step 5: Commit**

Message: `feat(connections): the weapon rows pick; the aim is a row with its own check`
Paths: `SkeldarAnim/maya_scenesetup/connections.py tests/test_scenesetup_connections.py tests/test_scenesetup_connections_pending.py`

---

### Task 6: the Camera tab - the parent, Position only and the aim as picks

**Files:**
- Modify: `SkeldarAnim/maya_scenesetup/connections.py` - the camera column of `build_panel`, `_set_camera` (`1682-1688`), `_chosen_camera_parent` (`1689-1696`), `_press_camera_parent` (`1697-1700`), `_press_camera_aim_mode` / `_press_camera_default` (`1702-1708`)
- Test: `tests/test_scenesetup_connections_pending.py`, `tests/test_scenesetup_connections_camera.py`

**Interfaces:**
- Produces: `CAMERA_APPLY = "skeldarConnectionsCameraApply"`, `CAMERA_AIM_MENU = "skeldarConnectionsCameraAim"`, `CAMERA_AIM_SEGMENT = "skeldarConnectionsCameraAim_{0}"`, `CAMERA_AIM_APPLY = "skeldarConnectionsCameraAimApply"`, `wanted_camera(rig)` -> `(choice, position)`, `apply_camera(rig, chosen)` -> str

- [ ] **Step 1: Write the failing test**

```python
class CameraPicks(unittest.TestCase):

    def setUp(self):
        pending.clear()
        self.addCleanup(pending.clear)
        self.done = []
        self.real = (cx.cmds, cx.refresh, cx.maya_rigs.current_rig,
                     cx.camera_parent, cx.camera_aim, cx._camera_state,
                     cx._limb_modes, cx.read_scheme)
        self.fake = FakeMenuCmds()
        cx.cmds = self.fake
        cx.refresh = lambda *a: ""
        cx.maya_rigs.current_rig = lambda: (Rig(), "")
        cx._limb_modes = lambda rig, kind, worlds=None: {}
        cx.read_scheme = lambda *a, **k: {"L": None, "R": None}
        #  the scene: the camera under Main, whole, not aimed
        cx._camera_state = lambda: ("Main", False, False)
        cx.camera_parent = lambda choice, position_only=False: \
            self.done.append(("parent", choice, position_only)) or "moved"
        cx.camera_aim = lambda on=True: \
            self.done.append(("aim", on)) or "aimed"
        cx.hubstyle.take_marks()
        cx.build_panel()
        cx.show_tab("camera")

    def tearDown(self):
        (cx.cmds, cx.refresh, cx.maya_rigs.current_rig, cx.camera_parent,
         cx.camera_aim, cx._camera_state, cx._limb_modes,
         cx.read_scheme) = self.real

    def test_a_parent_pick_bakes_nothing(self):
        self.fake.press_segment(cx.camera_segment("Chest"))
        self.assertEqual(self.done, [])
        self.assertEqual(cx.picks(Rig()), {pending.CAMERA: "Chest"})
        self.assertEqual(cx.wanted_camera(Rig()), ("Chest", False))

    def test_position_only_is_a_pick_of_the_same_change(self):
        self.fake.press_segment(cx.camera_segment("Chest"))
        self.fake.press_check(cx.CAMERA_POSITION, True)
        self.assertEqual(self.done, [])
        self.assertEqual(pending.count(cx.picks(Rig())), 1)
        self.fake.press_button(cx.CAMERA_APPLY)
        self.assertEqual(self.done, [("parent", "Chest", True)])
        self.assertEqual(cx.picks(Rig()), {})

    def test_the_camera_aim_is_a_row(self):
        self.fake.press_segment(cx.CAMERA_AIM_SEGMENT.format("Aim_Mode"))
        self.assertEqual(self.done, [])
        self.fake.press_button(cx.CAMERA_AIM_APPLY)
        self.assertEqual(self.done, [("aim", True)])

    def test_apply_all_takes_the_parent_before_the_aim(self):
        self.fake.press_segment(cx.camera_segment("Head"))
        self.fake.press_segment(cx.CAMERA_AIM_SEGMENT.format("Aim_Mode"))
        self.fake.press_button(cx.APPLY_ALL["camera"])
        self.assertEqual([d[0] for d in self.done], ["parent", "aim"])
```

- [ ] **Step 2: Run it to make sure it fails**

Expected: FAIL - no `CAMERA_APPLY`, no camera aim segments.

- [ ] **Step 3: Write the implementation**

The same three shapes as Task 5: the segments record (`_press_camera_pick(choice)`), the `Position only` chip records (`_press_camera_position`), `_set_camera(choice, position, chosen=None)` writes the scene's state quietly and paints `want` + `wait`, `wanted_camera(rig)` overlays the picks, `apply_camera(rig, chosen)` does `camera_parent(choice, position)` when `CAMERA` or `CAMERA_POSITION` is picked and then `camera_aim(on)` when `CAMERA_AIM` is, and `APPLY_ALL["camera"]` wraps both in the `Connections: Apply all` chunk, settling with `_settled` as the other tabs do. The camera's two buttons go; `camera_parent` / `camera_aim` and the hotkey rows `connections.camera_aim` / `.camera_default` are untouched.

`_states` gains this tab's three keys:

```python
    choice, position, aimed = _camera_state()
    out[pending.CAMERA] = choice
    out[pending.CAMERA_POSITION] = position
    out[pending.CAMERA_AIM] = aimed
```

- [ ] **Step 4: Run the tests and make sure they pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenesetup_connections_pending tests.test_scenesetup_connections_camera -v`
Expected: PASS (update the camera test's button assertions to the row's shape here).

- [ ] **Step 5: Commit**

Message: `feat(connections): the camera's parent and aim pick, then Apply`
Paths: `SkeldarAnim/maya_scenesetup/connections.py tests/test_scenesetup_connections_camera.py tests/test_scenesetup_connections_pending.py`

---

### Task 7: the Object tab - BakeAcross and Release out of the Body tab

**Files:**
- Modify: `SkeldarAnim/maya_scenesetup/connections.py` - `TABS`, `TAB_COLUMN`, `TAB_TIPS`, `CAPTION`, `_any_object_rows`, `build_panel`
- Test: `tests/test_scenesetup_connections_pending.py`, `tests/test_scenesetup_connections.py`

**Interfaces:**
- Produces: `TABS` gains `("object", "Object")`; `TAB_COLUMN["object"] = "skeldarConnectionsObjectTab"`

- [ ] **Step 1: Write the failing test**

```python
class ObjectTab(unittest.TestCase):

    def setUp(self):
        self.real = (cx.cmds, cx.refresh)
        self.fake = FakeMenuCmds()
        cx.cmds, cx.refresh = self.fake, (lambda *a: "")
        cx.hubstyle.take_marks()
        cx.build_panel()

    def tearDown(self):
        (cx.cmds, cx.refresh) = self.real

    def test_four_tabs(self):
        self.assertEqual([t[0] for t in cx.TABS],
                         ["body", "weapon", "camera", "object"])
        self.assertIn("object", cx.TAB_COLUMN)

    def test_bake_across_and_release_stand_in_the_object_tab(self):
        columns = [c[1][0] for c in self.fake.calls if c[0] == "columnLayout"
                   and c[1] and c[1][0] in cx.TAB_COLUMN.values()]
        self.assertEqual(columns[-1], cx.TAB_COLUMN["object"])
        after = self.fake.calls[[i for i, c in enumerate(self.fake.calls)
                                 if c[0] == "columnLayout" and c[1]
                                 and c[1][0] == cx.TAB_COLUMN["object"]][0]:]
        labels = [c[2].get("label") for c in after if c[0] == "button"]
        self.assertEqual(labels[:2], ["BakeAcross", "Release"])

    def test_the_object_tab_has_no_apply_all(self):
        self.assertNotIn("object", cx.APPLY_ALL)

    def test_show_tab_knows_it(self):
        cx.show_tab("object")
        self.assertEqual(cx.current_tab(), "object")
```

- [ ] **Step 2: Run it to make sure it fails**

Expected: FAIL - `TABS` has three entries.

- [ ] **Step 3: Write the implementation**

```python
TABS = (("body", "Body"), ("weapon", "Weapon"), ("camera", "Camera"),
        ("object", "Object"))
TAB_COLUMN = {"body": "skeldarConnectionsBodyTab",
              "weapon": "skeldarConnectionsWeaponTab",
              "camera": "skeldarConnectionsCameraTab",
              "object": "skeldarConnectionsObjectTab"}
TAB_TIPS = {"body": "FK / IK of the arms, legs and spine",
            "weapon": "The weapon's parent and its Aim Mode",
            "camera": "The camera's parent and its Aim Mode",
            "object": "Any selected objects across a parent - BakeAcross, Release"}
```

`_any_object_rows()` moves out of the body column into a fourth `cmds.columnLayout(TAB_COLUMN["object"], ...)`; its caption stays (`CAPTION["any"]`). Nothing else changes - `bake_across` / `release_across` and their hotkey rows are untouched.

- [ ] **Step 4: Run the tests and make sure they pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenesetup_connections tests.test_scenesetup_connections_pending -v`
Expected: PASS.

- [ ] **Step 5: Commit**

Message: `feat(connections): an Object tab - BakeAcross and Release out of the body`
Paths: `SkeldarAnim/maya_scenesetup/connections.py tests/test_scenesetup_connections.py tests/test_scenesetup_connections_pending.py`

---

### Task 8: the overlay a refresh cannot eat, the status, and the rig change

**Files:**
- Modify: `SkeldarAnim/maya_scenesetup/connections.py` - `refresh` (`1410-1444`), `_paint_pending`, `_picked_text`, `header_text`
- Test: `tests/test_scenesetup_connections_pending.py`

**Interfaces:**
- Produces: `_paint_pending(chosen)` (every painter plus the counts), `_picked_text(chosen)` -> str

- [ ] **Step 1: Write the failing test**

```python
class RefreshKeepsThePicks(LimbPicks):

    def test_a_refresh_repaints_the_state_and_keeps_the_pick(self):
        cx.refresh = self.real[1]              # the real refresh
        self.fake.press_box(cx.fkik_box("R", "FK"))
        cx.refresh()
        self.assertEqual(cx.picks(Rig()),
                         {pending.limb_key(cx.fkik.ARM, "R"): "FK"})
        #  the thumb is the scene's (IK), the pick is the overlay
        self.assertTrue(self.fake.boxes[cx.fkik_box("R", "IK")]["value"])
        self.assertFalse(self.fake.boxes[cx.fkik_box("R", "FK")]["value"])

    def test_the_status_names_every_pick(self):
        self.fake.press_box(cx.fkik_box("R", "FK"))
        self.fake.press_box(cx.fkik_box("L", "FK"))
        text = [c[2]["label"] for c in self.fake.calls
                if c[0] == "text" and c[1] == (cx.STATUS,)][-1]
        self.assertIn("Arm R to FK", text)
        self.assertIn("press", text.lower())

    def test_reading_another_rig_drops_the_picks(self):
        self.fake.press_box(cx.fkik_box("R", "FK"))
        other = Rig()
        other.namespace = "Creep_Rig"
        cx.maya_rigs.current_rig = lambda: (other, "")
        cx.refresh = self.real[1]
        cx.refresh()
        self.assertEqual(pending.PICKS, {})
```

- [ ] **Step 2: Run it to make sure it fails**

Expected: FAIL - the refresh wipes the pick (the painter has no overlay), or `_picked_text` is missing.

- [ ] **Step 3: Write the implementation**

```python
def _picked_text(chosen):
    """What the status says while picks stand: «Picked: Arm R to FK. Press the
    row's check, or Apply all.»"""
    if not chosen:
        return ""
    return "Picked: %s. Press the row's check, or Apply all." % pending.text(chosen)


def _paint_pending(chosen=None):
    """The whole card's overlay: every painter again with the picks, and each
    tab's Apply all counting them. Called after a pick, after a press and at
    the end of `refresh` - a painter alone would leave the other rows stale."""
    rig, _refusal = maya_rigs.current_rig()
    chosen = picks(rig) if chosen is None else chosen
    _paint_counts(chosen)
```

and `refresh` ends with `_paint_pending(chosen)`, passing the picks it already read into each painter (`_set_fkik(..., chosen=chosen)`, `_set_spine(..., chosen=chosen)`, `_set_menus(..., chosen=chosen)`, `_set_camera(..., chosen=chosen)`) so the scene is read once. `picks()` drops the other rigs' sets, so the rig change needs no extra step - but `refresh` must call `picks(rig)` BEFORE the painters, and the status keeps whatever the last press said unless picks stand, in which case it reads `_picked_text`.

- [ ] **Step 4: Run the tests and make sure they pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenesetup_connections_pending -v`
Expected: PASS.

- [ ] **Step 5: Run every test the card touches, then commit**

Run:
```
$env:QT_QPA_PLATFORM = 'offscreen'
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v
```
Expected: every test passes but the known `tests.test_chat_deploy.Keys`.

Message: `feat(connections): a refresh paints the picks it cannot eat`
Paths: `SkeldarAnim/maya_scenesetup/connections.py tests/test_scenesetup_connections_pending.py`

---

### Task 9: the verify script, and the neighbours re-run

**Files:**
- Create: `docs/superpowers/plans/verify_connections_apply.py`
- Modify: `CLAUDE.md` (the Connections section: the card's shape and the bake rule)

- [ ] **Step 1: Write the verify script**

`docs/superpowers/plans/verify_connections_apply.py`, the house shape (gates printed `PASS`/`FAIL`, a summary line `0 of N gates failed`, the scene left as found), in a disposable GUI Maya on a port of its own: a Manny_Rig with a UE clip retargeted onto it, then

1. pick FK on `Arm R` and IK on `Leg L` through `connections._press_limb(...)()`: read both limbs' blend values unchanged, `connections.picks(rig)` holding both;
2. press `APPLY_ALL["body"]`: both switched, `picks` empty, ONE `cmds.undo()` putting both back;
3. pick a parent on the weapon tab and press that row's `ROW_APPLY`: the scheme changed, the other rows untouched;
4. pick `Chest` + `Position only` on the camera tab and press `CAMERA_APPLY`: the camera control under the chest's follow group, one undo;
5. pick Aim Mode and press `AIM_APPLY`: `weaponaim.is_aimed(weapon)` True, one undo;
6. a refusal: ask `IK` on a limb that is in world, press its check - the status names it and nothing moved.

- [ ] **Step 2: Run it**

Run it in a disposable GUI Maya (scratch `MAYA_APP_DIR`, `MAYA_NO_HOME=1`, its own port, killed after - never the animator's Maya).
Expected: `0 of 6 gates failed`.

- [ ] **Step 3: Re-run the neighbours**

`verify_fkik_switch.py`, `verify_fkik_keys.py`, `verify_ik_world.py`, `verify_weapon_aim_mode.py`, `verify_camera_tab.py` in mayapy standalone: the engines did not change, so their numbers must not move. `verify_connections.py` (40 gates) needs a GUI Maya and a rig-free scene; run it in the same disposable Maya.

- [ ] **Step 4: Write up CLAUDE.md**

One section in the Connections part: the animator's words, the mockups and the pick, the four tabs, the pending rule, the counts, and what is NOT built (variant C's sections; a pick is not greyed at pick time).

- [ ] **Step 5: Commit**

Message: `docs(connections): pick-then-apply - the verify and the write-up`
Paths: `docs/superpowers/plans/verify_connections_apply.py CLAUDE.md`
