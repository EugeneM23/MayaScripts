# Temporary hotkey map — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A sixth SkeldarAnim shelf button that switches Maya to a hotkey set of its own for as long as it is on, with every one of our panel buttons and every one-press OverRig procedure registered as a named command the animator can bind in Maya's own Hotkey Editor.

**Architecture:** One shipped file, `SkeldarAnim/maya_hotkeys.py` (`maya.cmds` only; Qt and our packages imported lazily behind four one-line seams the tests replace). It holds a table of 107 rows — `(key, category, label, annotation, action)` — where an action is either a Python callable of ours or a MEL string for OverRig. `register()` turns every row into a `runTimeCommand`, whose body is a one-liner calling back into `run("<key>")`. `toggle()` registers, then switches `hotkeySet` and paints the shelf button.

**Tech Stack:** Python 2/3-compatible-style `maya.cmds` (the repo's house style), `maya.mel` for OverRig, PySide6 only behind the picker seam. Tests: stdlib `unittest` under `mayapy`, with a fake `cmds` object.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-02-hotkey-map-design.md`. Read it before Task 1; it records why each decision is what it is.
- Test runner, always from the repo root: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v`. There is no system Python. Never `pip install` into the Maya tree. In PowerShell never append `2>&1` to `mayapy` — unittest writes to stderr and 5.1 turns that into `NativeCommandError` noise.
- `SkeldarAnim/` is the plugin: everything in it ships to a colleague. Repo-root files do not. The new module goes in the plugin folder.
- `SkeldarAnim/maya_hotkeys.py` imports **only** `maya.cmds`, `maya.mel` and the stdlib at module level. Qt (`picker_window`) and our packages are imported inside functions. A `Maya` before 2025 has PySide2 and must still load this module.
- Never resolve a Maya node, set or command **by a name we did not just create**; nothing in this feature touches scene nodes at all, which is the point — it touches **prefs**.
- `git commit -F <file>` with the message in a file: PowerShell here-strings containing double quotes break `-m`. End every commit message with `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- Commit after every task. Branch is `feature/overrig-picker`; do not push.
- Measured API facts this plan depends on (all probed in `mayapy` 2027, do not re-derive):
  - `hotkeySet` needs a UI: `hotkeySet(query=True, current=True)` raises `RuntimeError: Maya command error` in `mayapy`. Its flags are `-current -source -exists -delete -rename -hotkeySetArray -import -export`.
  - `runTimeCommand` works headless. `query=True, exists=True` answers `False` for an unknown name. `edit=True` accepts `command`, `category`, `label`, `annotation`, `commandLanguage` (verified by querying them back). `edit=True, delete=True` removes one. A command we create reports `default` as `False`, so Maya saves it to `userRunTimeCommands.mel`.
  - Categories nest with a **dot** (`Editors.Time Editor.Clip`); 272 exist in a stock 2027.
  - The Hotkey Editor is opened by the runTimeCommand **`HotkeyPreferencesWindow`**.
  - `shelfButton` carries `-enableBackground` and `-backgroundColor`, plus `-imageOverlayLabel`, `-label` and `-runTimeCommand`.
  - `maya_overshoot.SHAPES` is a `collections.OrderedDict`; `SHAPE_ORDER` is `["Snap", "Spring", "Elastic", "Recoil", "Bounce"]`.

---

## File Structure

| File | Responsibility |
|---|---|
| `SkeldarAnim/maya_hotkeys.py` | **Create.** The whole feature: the seams, the reporting, the two tables, `run`, `register`, the hotkey set, the button paint. |
| `SkeldarAnim/maya_overrig/picker_window.py` | **Modify.** Add module-level `live_window()`; rename `_select_group` to `select_group`. |
| `SkeldarAnim/maya_overshoot.py` | **Modify.** Promote the window id `"animOvershootWin"` from a local to a module constant `WINDOW`. |
| `SkeldarAnim/install.py` | **Modify.** `maya_hotkeys.py` into `_PAYLOAD`, a sixth row in `_PYTHON_BUTTONS`. |
| `SkeldarAnim/icons/make_icons.py` | **Modify.** `draw_hotkeys` + a `DRAWERS` row. |
| `SkeldarAnim/icons/hotkeys.png` | **Create** (generated, committed beside its generator). |
| `tests/test_hotkeys.py` | **Create.** The fake `cmds`, the table's contract, `run`, `register`, `toggle`, the paint. |
| `tests/test_install.py` | **Modify.** Six buttons, the new icon, the new payload entry. |
| `docs/superpowers/plans/verify_hotkeys.py` | **Create.** The live proof, sent through the bridge. |
| `CLAUDE.md` | **Modify.** A section for the feature; the shelf is described as five buttons in three places. |

---

## Task 1: The module's spine — seams, reporting, our 23 rows, `run()`

**Files:**
- Create: `SkeldarAnim/maya_hotkeys.py`
- Create: `tests/test_hotkeys.py`
- Modify: `SkeldarAnim/maya_overrig/picker_window.py` (add `live_window()`, rename `_select_group`)
- Modify: `SkeldarAnim/maya_overshoot.py` (promote `WINDOW`)

**Interfaces:**
- Consumes: nothing.
- Produces: `COMMANDS` (tuple of `(key, category, label, annotation, action)`), `_INDEX` (dict key→row), `row(key)`, `run(key)`, `_report(message) -> str`, the four seams `_picker_module()`, `_scene_module()`, `_overshoot_module()`, `_overrig_module()`, and the action helpers `_show(module_name, func)`, `_picker(method, *args)`, `_scene(func, *args)`, `_overshoot(shape)`. Task 2 appends to the table, Task 3 reads `COMMANDS`, Tasks 4–5 add `toggle()`/`paint()` and one more row.

- [ ] **Step 1: Write the failing test file**

Create `tests/test_hotkeys.py`:

```python
"""Tests for the hotkey map: the table's contract and the dispatcher.

`hotkeySet` needs a UI -- it raises "Maya command error" in mayapy -- so
every gate about the SET itself runs against FakeCmds here and for real in
docs/superpowers/plans/verify_hotkeys.py. What is testable without Maya is
all the policy: which rows exist, what a row's body says, which panel a key
presses, and what happens when the panel is closed.
"""

import os
import sys
import types
import unittest


def _install_fake_maya():
    """Let maya_hotkeys import without a Maya. See CLAUDE.md on rebinding.

    Real modules win when they are importable -- under mayapy they always
    are. Guarding on `"maya.cmds" in sys.modules` alone is not enough: run on
    its own, this module would install a fake `maya` that is not a package and
    shadow the real one.
    """
    try:
        import maya.cmds  # noqa: F401
        import maya.mel  # noqa: F401
        return
    except ImportError:
        pass

    maya = types.ModuleType("maya")
    cmds = types.ModuleType("maya.cmds")
    mel = types.ModuleType("maya.mel")
    maya.cmds = cmds
    maya.mel = mel
    sys.modules.setdefault("maya", maya)
    sys.modules["maya.cmds"] = cmds
    sys.modules["maya.mel"] = mel


_install_fake_maya()

import maya_hotkeys  # noqa: E402

PLUGIN = os.path.dirname(os.path.abspath(maya_hotkeys.__file__))


class FakeCmds(object):
    """Everything of `cmds` this module touches, and nothing else.

    Hotkey sets are modelled as a list plus a current name, because that is
    exactly what the real command exposes: create with a source, switch with
    edit, ask with query.
    """

    def __init__(self, current="Maya_Default", sets=("Maya_Default",),
                 shelves=None, buttons=None, windows=()):
        self.current = current
        self.sets = list(sets)
        self.sources = {}
        self.optionvars = {}
        self.runtime = {}
        self.creates = []
        self.edits = []
        self.messages = []
        self.painted = []
        self.shelves = dict(shelves or {})
        self.buttons = dict(buttons or {})
        self.windows = set(windows)
        self.evaluated = []

    # -- hotkey sets -----------------------------------------------------
    def hotkeySet(self, name=None, query=False, edit=False, current=False,
                  exists=False, hotkeySetArray=False, source=None,
                  delete=False):
        if query and current:
            return self.current
        if query and exists:
            return name in self.sets
        if query and hotkeySetArray:
            return list(self.sets)
        if delete:
            self.sets.remove(name)
            if self.current == name:
                self.current = "Maya_Default"
            return None
        if edit and current:
            if name not in self.sets:
                raise RuntimeError("no such hotkey set: " + str(name))
            self.current = name
            return name
        if name in self.sets:
            raise RuntimeError("hotkey set exists: " + str(name))
        self.sets.append(name)
        self.sources[name] = source
        if current:
            self.current = name
        return name

    # -- runtime commands ------------------------------------------------
    def runTimeCommand(self, name=None, query=False, edit=False, exists=False,
                       command=False, category=False, label=False,
                       annotation=False, commandLanguage=None, default=None,
                       delete=False):
        if query and exists:
            return name in self.runtime
        if query:
            row = self.runtime[name]
            for flag, value in (("command", command), ("category", category),
                                ("label", label), ("annotation", annotation)):
                if value:
                    return row[flag]
            raise RuntimeError("unhandled query")
        row = {"command": command, "category": category, "label": label,
               "annotation": annotation}
        if edit and delete:
            self.runtime.pop(name, None)
            return None
        if edit:
            self.runtime[name] = row
            self.edits.append(name)
            return name
        self.runtime[name] = row
        self.creates.append(name)
        return name

    # -- odds and ends ---------------------------------------------------
    def optionVar(self, exists=None, query=None, stringValue=None,
                  remove=None):
        if exists is not None:
            return exists in self.optionvars
        if query is not None:
            return self.optionvars.get(query, "")
        if stringValue is not None:
            self.optionvars[stringValue[0]] = stringValue[1]
            return None
        if remove is not None:
            self.optionvars.pop(remove, None)
            return None

    def shelfLayout(self, name, exists=False, query=False, childArray=False):
        if exists:
            return name in self.shelves
        if query and childArray:
            return list(self.shelves.get(name, []))
        return None

    def shelfButton(self, name, query=False, edit=False, label=False,
                    enableBackground=None, backgroundColor=None):
        if query and label:
            return self.buttons.get(name, "")
        if edit:
            self.painted.append((name, enableBackground, backgroundColor))
        return None

    def control(self, name, query=False, exists=False):
        if query and exists:
            return name in self.buttons
        return None

    def window(self, name, exists=False):
        if exists:
            return name in self.windows
        return None

    def inViewMessage(self, assistMessage="", **kwargs):
        self.messages.append(assistMessage)
        return None


class FakeMel(object):

    def __init__(self, fake_cmds):
        self.cmds = fake_cmds

    def eval(self, script):
        self.cmds.evaluated.append(script)
        return None


def use(fake):
    """Point maya_hotkeys at a fake cmds (and mel) and hand it back."""
    maya_hotkeys.cmds = fake
    maya_hotkeys.mel = FakeMel(fake)
    return maya_hotkeys


class SeamCase(unittest.TestCase):
    """A fake cmds, and the four lazy seams put back afterwards.

    The seams are module attributes, so a test that hands in a fake panel
    and walks away leaves it there for whatever runs next -- the same
    class of staleness CLAUDE.md's note about module objects is about.
    """

    SEAMS = ("_picker_module", "_scene_module", "_overshoot_module",
             "_overrig_module")

    def setUp(self):
        self._seams = dict((name, getattr(maya_hotkeys, name))
                           for name in self.SEAMS)
        self.fake = FakeCmds()
        use(self.fake)

    def tearDown(self):
        for name, seam in self._seams.items():
            setattr(maya_hotkeys, name, seam)


class FakeWindow(object):
    """A stand-in panel that records which of its methods was pressed."""

    def __init__(self):
        self.pressed = []

    def __getattr__(self, name):
        def press(*args):
            self.pressed.append((name,) + args)
            return name
        return press


class FakePicker(object):

    def __init__(self, window=None):
        self.window = window
        self.shown = 0

    def live_window(self):
        return self.window

    def show_picker(self):
        self.shown += 1
        return None


class FakePanelModule(object):
    """Scene Setup / Overshoot: a module id plus recorded calls."""

    WINDOW = "fakePanelWindow"

    def __init__(self):
        self.calls = []
        self.shown = 0

    def show_window(self):
        self.shown += 1

    def show_overshoot_ui(self):
        self.shown += 1

    def apply_overshoot(self, shape):
        self.calls.append(("apply_overshoot", shape))

    def __getattr__(self, name):
        def call(*args):
            self.calls.append((name,) + args)
        return call


class TheTable(unittest.TestCase):
    """The table is the contract: 107 rows, no two alike."""

    def test_every_key_is_unique(self):
        keys = [row[0] for row in maya_hotkeys.COMMANDS]
        self.assertEqual(len(keys), len(set(keys)))

    def test_every_category_is_ours(self):
        for key, category, _label, _note, _action in maya_hotkeys.COMMANDS:
            root = "OverRig." if key.startswith("overrig.") \
                else "SkeldarAnim."
            self.assertTrue(category.startswith(root),
                            "{0} -> {1}".format(key, category))

    def test_labels_and_annotations_are_filled_in(self):
        for key, _cat, label, note, _action in maya_hotkeys.COMMANDS:
            self.assertTrue(label.strip(), key)
            self.assertTrue(note.strip(), key)

    def test_the_index_answers_every_row(self):
        for row in maya_hotkeys.COMMANDS:
            self.assertIs(maya_hotkeys.row(row[0]), row)

    def test_an_unknown_key_is_not_in_the_index(self):
        self.assertIsNone(maya_hotkeys.row("no.such.key"))


class OurRows(unittest.TestCase):
    """Ours: the window openers, six picker, seven scene, five overshoot.
    The map's own toggle joins the Windows group in Task 4, once there is a
    `toggle` for it to name."""

    def _keys(self, prefix):
        return [row[0] for row in maya_hotkeys.COMMANDS
                if row[0].startswith(prefix)]

    def test_the_four_openers(self):
        self.assertEqual(sorted(self._keys("window.")),
                         ["window.overshoot", "window.picker",
                          "window.scenesetup", "window.uebridge"])

    def test_the_picker_rows(self):
        self.assertEqual(sorted(self._keys("picker.")),
                         ["picker.all", "picker.bake", "picker.build",
                          "picker.connect", "picker.fk", "picker.ik"])

    def test_the_scene_setup_rows(self):
        self.assertEqual(sorted(self._keys("scene.")),
                         ["scene.aim", "scene.camera", "scene.character",
                          "scene.connect_arms", "scene.disconnect_arms",
                          "scene.remove_weapon", "scene.weapon"])

    def test_one_row_per_overshoot_shape(self):
        import maya_overshoot
        shapes = [row[4].args[0] for row in maya_hotkeys.COMMANDS
                  if row[0].startswith("shoot.")]
        self.assertEqual(sorted(shapes), sorted(maya_overshoot.SHAPE_ORDER))


class OurRowsNameRealMethods(unittest.TestCase):
    """A row that names a method the panel no longer has is a hotkey that
    fails at the worst moment. The check reads the target module's SOURCE
    rather than importing it -- an import would drag Qt into a plain-Python
    test.
    """

    def _methods(self, helper):
        return [row[4].args[0] for row in maya_hotkeys.COMMANDS
                if getattr(row[4], "func", None) is helper]

    def _source(self, *parts):
        with open(os.path.join(PLUGIN, *parts), encoding="utf-8") as handle:
            return handle.read()

    def test_picker_methods_exist(self):
        source = self._source("maya_overrig", "picker_window.py")
        methods = self._methods(maya_hotkeys._picker)
        self.assertEqual(len(methods), 6)
        for name in methods:
            self.assertIn("def {0}(".format(name), source)

    def test_scene_setup_callbacks_exist(self):
        source = self._source("maya_scenesetup", "window.py")
        methods = self._methods(maya_hotkeys._scene)
        self.assertEqual(len(methods), 7)
        for name in methods:
            self.assertIn("def {0}(".format(name), source)

    def test_the_openers_name_importable_modules(self):
        import importlib.util
        names = [row[4].args[0] for row in maya_hotkeys.COMMANDS
                 if getattr(row[4], "func", None) is maya_hotkeys._show]
        self.assertEqual(len(names), 4)
        for name in names:
            self.assertIsNotNone(importlib.util.find_spec(name), name)


class RunPressesThePanel(SeamCase):

    def test_build_presses_the_open_picker(self):
        window = FakeWindow()
        maya_hotkeys._picker_module = lambda: FakePicker(window)
        maya_hotkeys.run("picker.build")
        self.assertEqual(window.pressed, [("build_rig",)])

    def test_fk_and_ik_pass_the_direction(self):
        window = FakeWindow()
        maya_hotkeys._picker_module = lambda: FakePicker(window)
        maya_hotkeys.run("picker.fk")
        maya_hotkeys.run("picker.ik")
        self.assertEqual(window.pressed,
                         [("convert_selected_limbs", False),
                          ("convert_selected_limbs", True)])

    def test_a_closed_picker_is_opened_and_reported(self):
        picker = FakePicker(None)
        maya_hotkeys._picker_module = lambda: picker
        maya_hotkeys.run("picker.build")
        self.assertEqual(picker.shown, 1)
        self.assertIn("Rig Picker", self.fake.messages[-1])

    def test_scene_setup_presses_its_callback(self):
        panel = FakePanelModule()
        self.fake.windows.add(panel.WINDOW)
        maya_hotkeys._scene_module = lambda: panel
        maya_hotkeys.run("scene.camera")
        self.assertEqual(panel.calls, [("camera_setup",)])

    def test_a_closed_scene_setup_is_opened_and_reported(self):
        panel = FakePanelModule()
        maya_hotkeys._scene_module = lambda: panel
        maya_hotkeys.run("scene.weapon")
        self.assertEqual(panel.shown, 1)
        self.assertEqual(panel.calls, [])
        self.assertIn("Scene Setup", self.fake.messages[-1])

    def test_overshoot_passes_the_shape(self):
        panel = FakePanelModule()
        self.fake.windows.add(panel.WINDOW)
        maya_hotkeys._overshoot_module = lambda: panel
        maya_hotkeys.run("shoot.bounce")
        self.assertEqual(panel.calls, [("apply_overshoot", "Bounce")])

    def test_an_unknown_key_reports_instead_of_raising(self):
        maya_hotkeys.run("picker.nonsense")
        self.assertIn("picker.nonsense", self.fake.messages[-1])

    def test_a_failing_action_lands_on_the_message_not_the_traceback(self):
        def explode():
            raise RuntimeError("boom")
        maya_hotkeys._INDEX["test.explode"] = (
            "test.explode", "SkeldarAnim.Windows", "Explode", "note",
            explode)
        try:
            maya_hotkeys.run("test.explode")
        finally:
            del maya_hotkeys._INDEX["test.explode"]
        self.assertIn("boom", self.fake.messages[-1])
        self.assertIn("Explode", self.fake.messages[-1])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_hotkeys -v`

Expected: collection error — `ModuleNotFoundError: No module named 'maya_hotkeys'`.

- [ ] **Step 3: Write the module's spine**

Create `SkeldarAnim/maya_hotkeys.py`:

```python
"""The temporary hotkey map: one shelf button that switches Maya's set.

Press `Hotkeys` on the SkeldarAnim shelf and Maya switches to a hotkey set
of our name; press it again and the animator's own set comes back. The map's
CONTENTS are theirs to lay out, in Maya's own Hotkey Editor -- what this
module adds is the switch, plus a command list worth binding: every button
of our panels, and every one-press procedure OverRig's author published in
`function_for_hotkeys.TXT`.

Design: docs/superpowers/specs/2026-09-02-hotkey-map-design.md

`maya.cmds` and `maya.mel` only at module level. Qt lives below the four
`_*_module()` seams: `picker_window` imports PySide6 when it loads, and four
of the five shelf buttons have to keep working on a Maya that has PySide2.
The seams are also where the tests hand in a fake panel.
"""

import importlib
import os
import traceback
from functools import partial

import maya.cmds as cmds
import maya.mel as mel

SET = "SkeldarAnim"
SHELF = "SkeldarAnim"
BUTTON_LABEL = "Hotkeys"
PREVIOUS_VAR = "skeldarAnimPreviousHotkeySet"
FALLBACK_SET = "Maya_Default"
PREFIX = "skeldarAnim"
EDITOR_COMMAND = "HotkeyPreferencesWindow"
ON_COLOUR = (0.27, 0.38, 0.48)


# --------------------------------------------------------------- reporting

def _report(message):
    """Say it where a keypress can be seen, and hand the text back.

    A hotkey has no status bar of its own. An exception out of a
    runTimeCommand goes to the Script Editor and nowhere else, which is
    exactly how "I press it and nothing happens" happened before (trap 20).
    """
    cmds.inViewMessage(assistMessage=message, position="midCenterTop",
                       fade=True)
    return message


# ------------------------------------------------------------------- seams

def _picker_module():
    """Lazy, and the seam the tests replace. Qt lives below this line."""
    from maya_overrig import picker_window
    return picker_window


def _scene_module():
    from maya_scenesetup import window
    return window


def _overshoot_module():
    import maya_overshoot
    return maya_overshoot


def _overrig_module():
    """The MEL binding. cmds and mel only -- no Qt below here either."""
    from maya_overrig import overrig
    return overrig


# ----------------------------------------------------------------- actions

def _show(module_name, func):
    """Open a tool's window; its own module knows how."""
    module = importlib.import_module(module_name)
    return getattr(module, func)()


def _picker(method, *args):
    """Press a Rig Picker button.

    With the panel closed there is nothing to press: the picker's binding is
    the character the animator can SEE, and re-deriving one to act on is how
    two characters got rigged onto each other. So we open it and say so.
    """
    module = _picker_module()
    window = module.live_window()
    if window is None:
        module.show_picker()
        return _report(
            "Rig Picker opened - connect a character and press again")
    return getattr(window, method)(*args)


def _scene(func, *args):
    """Press a Scene Setup button. Its callbacks read their own window."""
    module = _scene_module()
    if not cmds.window(module.WINDOW, exists=True):
        module.show_window()
        return _report("Scene Setup opened - press again")
    return getattr(module, func)(*args)


def _overshoot(shape):
    """Apply one overshoot preset. Strength and Frames come from the panel."""
    module = _overshoot_module()
    if not cmds.window(module.WINDOW, exists=True):
        module.show_overshoot_ui()
        return _report("Overshoot opened - press again")
    return module.apply_overshoot(shape)


def _mel(script):
    """Run one OverRig procedure, sourcing the toolset first.

    Without the source, a fresh Maya with the OverRig shelf button unpressed
    answers a keypress with `Cannot find procedure` in the Script Editor
    (trap 20 from the hotkey side). Deliberately NOT gated on the time
    slider's highlight the way our own MEL entry points are (trap 36): half
    of these procedures are ABOUT the highlighted range.
    """
    overrig = _overrig_module()
    if not overrig.ensure_loaded():
        return _report(overrig.NOT_LOADED_MESSAGE)
    return mel.eval(script)


# --------------------------------------------------------------- the table

def row(key):
    """The row for `key`, or None."""
    return _INDEX.get(key)


def run(key):
    """Run one command. The body of every runTimeCommand we register.

    Every failure is reported where the animator is looking and the full
    traceback still goes to the Script Editor -- the panels' own `_run`,
    for a button that has no panel.

    Deliberately NO undo chunk of our own: `rebuild` already builds in one
    undo step and OverRig's procedures manage theirs, so wrapping a chunk
    in another chunk buys nothing and nests. A hotkey inherits whatever its
    target does, which is what the shelf buttons already do.
    """
    found = row(key)
    if found is None:
        return _report("Unknown hotkey command '{0}' - re-drag the "
                       "installer".format(key))
    label, action = found[2], found[4]
    try:
        return action()
    except Exception as error:  # noqa: BLE001 - the message is the report
        traceback.print_exc()
        return _report("{0} failed: {1}".format(label, error))


_OURS = (
    # key, category leaf, label, annotation, action
    ("window.picker", "Windows", "Rig Picker",
     "Open the Rig Picker panel",
     partial(_show, "maya_overrig", "show_picker")),
    ("window.uebridge", "Windows", "UE Bridge",
     "Open the UE animation bridge",
     partial(_show, "maya_uebridge", "show_window")),
    ("window.scenesetup", "Windows", "Scene Setup",
     "Open Scene Setup: character, weapon, camera",
     partial(_show, "maya_scenesetup", "show_window")),
    ("window.overshoot", "Windows", "Overshoot",
     "Open the Overshoot panel",
     partial(_show, "maya_overshoot", "show_overshoot_ui")),

    ("picker.connect", "Rig Picker", "Connect",
     "Bind the picker to the selected character",
     partial(_picker, "connect_to_selection")),
    ("picker.build", "Rig Picker", "Build",
     "Build the hybrid rig on the connected character",
     partial(_picker, "build_rig")),
    ("picker.fk", "Rig Picker", "FK Limbs",
     "Bring the selected limbs to FK",
     partial(_picker, "convert_selected_limbs", False)),
    ("picker.ik", "Rig Picker", "IK Limbs",
     "Bring the selected limbs to IK",
     partial(_picker, "convert_selected_limbs", True)),
    ("picker.bake", "Rig Picker", "Bake+Delete",
     "Bake what the selection touches back onto clean bones",
     partial(_picker, "bake_selected_limbs")),
    ("picker.all", "Rig Picker", "Select All",
     "Select every controller on the body map",
     partial(_picker, "select_group", "all")),

    ("scene.character", "Scene Setup", "Add Character",
     "Import the chosen skeleton into this scene",
     partial(_scene, "add_character")),
    ("scene.weapon", "Scene Setup", "Add Weapon",
     "Import the chosen weapon and drive its bone from it",
     partial(_scene, "add_weapon")),
    ("scene.remove_weapon", "Scene Setup", "Remove Weapon",
     "Bake the bone back off the weapon and delete it",
     partial(_scene, "remove_weapon")),
    ("scene.connect_arms", "Scene Setup", "Connect Arms To Weapon",
     "Both arms to IK, the weapon out to world, the hands onto it",
     partial(_scene, "connect_arms")),
    ("scene.disconnect_arms", "Scene Setup", "Disconnect Arms",
     "Lift the hands off the weapon and put it back in the hand",
     partial(_scene, "disconnect_arms")),
    ("scene.aim", "Scene Setup", "Add Aim",
     "OverRig's aim on the weapon, both locators placed",
     partial(_scene, "add_aim")),
    ("scene.camera", "Scene Setup", "Camera Setup",
     "A camera on camera_bone, the bone driven from it",
     partial(_scene, "camera_setup")),

    ("shoot.snap", "Overshoot", "Overshoot Snap",
     "One tight swing out of the pose", partial(_overshoot, "Snap")),
    ("shoot.spring", "Overshoot", "Overshoot Spring",
     "Three decaying swings", partial(_overshoot, "Spring")),
    ("shoot.elastic", "Overshoot", "Overshoot Elastic",
     "Six slowly decaying swings", partial(_overshoot, "Elastic")),
    ("shoot.recoil", "Overshoot", "Overshoot Recoil",
     "Two hard swings", partial(_overshoot, "Recoil")),
    ("shoot.bounce", "Overshoot", "Overshoot Bounce",
     "Arcs under gravity", partial(_overshoot, "Bounce")),
)

_OVERRIG = ()


def _prefixed(root, table):
    return tuple((key, root + "." + category, label, note, action)
                 for key, category, label, note, action in table)


COMMANDS = _prefixed("SkeldarAnim", _OURS) + _prefixed("OverRig", _OVERRIG)

_INDEX = dict((command[0], command) for command in COMMANDS)
```

- [ ] **Step 4: Add the two accessors the table names**

In `SkeldarAnim/maya_overrig/picker_window.py`, add beside `bound_root()`:

```python
def live_window():
    """The open picker, or None. The public name of what tools ask for.

    `show_picker` REPLACES the window, so a caller that wants to press a
    button on the panel already up has to be able to tell "open" from
    "closed" first.
    """
    return _open_window()
```

In the same file rename the group-selection method — it has a second caller now, so it is no longer private. `def _select_group(self, group):` becomes `def select_group(self, group):`, and the lambda in `_build_groups` becomes:

```python
            button.clicked.connect(
                lambda _checked=False, g=group: self.select_group(g))
```

Confirm nothing else refers to the old name:

```bash
grep -rn "_select_group" --include=*.py .
```

Expected: no hits.

In `SkeldarAnim/maya_overshoot.py`, promote the window id. Next to `STATUS_WIDTH`, add:

```python
WINDOW = "animOvershootWin"      # also read by maya_hotkeys
```

and in `show_overshoot_ui` replace `win_id = "animOvershootWin"` with `win_id = WINDOW`.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_hotkeys -v`

Expected: PASS, ~20 tests. `test_one_row_per_overshoot_shape` proves the five shapes match `SHAPE_ORDER`; `test_picker_methods_exist` proves the six method names are really in `picker_window.py` (it will fail if Step 4's rename was missed, which is the point).

- [ ] **Step 6: Run the whole suite — the rename must not have broken the picker**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v`

Expected: everything that passed before still passes (1316 + the new ones). A failure in `tests/test_picker_view.py` or elsewhere means something else called `_select_group`.

- [ ] **Step 7: Commit**

```bash
git add SkeldarAnim/maya_hotkeys.py tests/test_hotkeys.py SkeldarAnim/maya_overrig/picker_window.py SkeldarAnim/maya_overshoot.py
git commit -F commit-msg.txt
```

with `commit-msg.txt`:

```
feat(hotkeys): the command table and the dispatcher

Every action of ours is a panel button, so a hotkey command presses one:
the panels already report on their own status line, refresh themselves and
trap their own exceptions. With the panel closed there is nothing to press
- the command opens it and says so, rather than re-deriving a character to
act on.

Qt lives below four one-line `_*_module()` seams, so the module loads on a
Maya with PySide2 and a plain-Python test can hand in a fake panel.

picker_window grows a public `live_window()` (show_picker REPLACES the
window, so a caller has to tell open from closed) and `_select_group`
becomes `select_group` now that it has a second caller. maya_overshoot's
window id is a module constant.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

## Task 2: The OverRig rows

**Files:**
- Modify: `SkeldarAnim/maya_hotkeys.py` (fill `_OVERRIG`)
- Modify: `tests/test_hotkeys.py` (append the OverRig gates)

**Interfaces:**
- Consumes: `_mel`, `_prefixed`, `COMMANDS` from Task 1.
- Produces: 84 more rows in `COMMANDS`, each with a MEL string as its action wrapped in `partial(_mel, "<script>")`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_hotkeys.py`:

```python
class OverRigRows(SeamCase):
    """The author's own list, grouped as the author grouped it."""

    def _rows(self):
        return [row for row in maya_hotkeys.COMMANDS
                if row[0].startswith("overrig.")]

    def test_the_whole_list_is_there(self):
        self.assertEqual(len(self._rows()), 84)

    def test_every_row_is_a_mel_script(self):
        for row in self._rows():
            self.assertIs(row[4].func, maya_hotkeys._mel, row[0])
            script = row[4].args[0]
            self.assertTrue(script.endswith(";"), script)

    def test_the_categories_are_the_authors_headings(self):
        wanted = set([
            "OverRig.Menu", "OverRig.Rotation order", "OverRig.Smart object",
            "OverRig.Knot", "OverRig.Parent", "OverRig.Aim",
            "OverRig.Key tools", "OverRig.Selector", "OverRig.Double knots",
            "OverRig.Snapshot", "OverRig.Hierarchy", "OverRig.IK",
            "OverRig.Bake", "OverRig.Sword", "OverRig.Physics",
            "OverRig.Misc", "OverRig.Finger"])
        self.assertEqual(set(row[1] for row in self._rows()), wanted)

    def test_a_row_sources_overrig_before_running(self):
        class Loader(object):
            NOT_LOADED_MESSAGE = "OverRig is not loaded"

            def __init__(self):
                self.asked = 0

            def ensure_loaded(self):
                self.asked += 1
                return True

        loader = Loader()
        maya_hotkeys._overrig_module = lambda: loader
        maya_hotkeys.run("overrig.parent_in")
        self.assertEqual(loader.asked, 1)
        self.assertEqual(self.fake.evaluated, ["apply_Parent_in();"])

    def test_a_missing_overrig_is_reported_and_nothing_runs(self):
        class Missing(object):
            NOT_LOADED_MESSAGE = "OverRig is not loaded - press the button"

            def ensure_loaded(self):
                return False

        maya_hotkeys._overrig_module = lambda: Missing()
        maya_hotkeys.run("overrig.bake")
        self.assertEqual(self.fake.evaluated, [])
        self.assertIn("not loaded", self.fake.messages[-1])


class TheDestructiveProceduresStayOut(unittest.TestCase):
    """A gone-test. These two are the only procedures in
    function_for_hotkeys.TXT that ignore the selection and work on the whole
    scene: they select all of OverRig_rig_objects, bake, and delete every
    knot. On a key that is one mis-press from taking down hand-made setups
    the tool never built. Excluded on purpose -- if they are ever wanted,
    that is the animator's explicit call and this test is the record of it.
    """

    FORBIDDEN = (
        "barn_fast_bake_source_obj_and_delete_knots",
        "barn_fast_bake_min_max_or_range_source_obj_and_delete_knots",
    )

    def test_no_row_runs_them(self):
        scripts = " ".join(
            row[4].args[0] for row in maya_hotkeys.COMMANDS
            if getattr(row[4], "func", None) is maya_hotkeys._mel)
        for name in self.FORBIDDEN:
            self.assertNotIn(name, scripts)

    def test_the_module_never_mentions_them(self):
        with open(maya_hotkeys.__file__.replace(".pyc", ".py"),
                  encoding="utf-8") as handle:
            source = handle.read()
        for name in self.FORBIDDEN:
            self.assertEqual(source.count(name), 1,
                             "only the comment saying why may name " + name)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_hotkeys -v`

Expected: `test_the_whole_list_is_there` fails with `0 != 84`.

- [ ] **Step 3: Fill in the table**

In `SkeldarAnim/maya_hotkeys.py` replace `_OVERRIG = ()` with the following. Arguments are the author's own, as written in `SkeldarAnim/overrig/function_for_hotkeys.TXT`; where one procedure takes a named mode, each mode is its own row, because on a keyboard each of those IS a separate key.

```python
# Pavel Barnev's own list of procedures meant for hotkeys, from
# overrig/function_for_hotkeys.TXT, with his headings as the categories and
# his arguments as written there. Two procedures are deliberately absent:
# barn_fast_bake_source_obj_and_delete_knots and its min_max twin are the
# only ones that ignore the selection and bake-and-delete the whole scene's
# knots, which is not a thing to put one keypress away. The ones needing
# real arguments (execute_overlap_command, motion trail, ribbon) are here as
# their windows instead: for those, the window IS the one-press command.
_OVERRIG = (
    ("overrig.panel", "Menu", "OverRig panel",
     "The native OverRig panel", partial(_mel, "base_OverRig_scripts(1);")),

    ("overrig.rotate_order_xyz", "Rotation order", "Convert to xyz",
     "Convert the selection's rotation order to xyz",
     partial(_mel, 'barn_execute_convert_rotation_order("xyz");')),

    ("overrig.smart_knot", "Smart object", "Smart knot",
     "Bake the animation onto a smart locator",
     partial(_mel, "apply_smart_parentConstrAnim(1);")),
    ("overrig.smart_pivot", "Smart object", "Smart pivot knot",
     "Bake the animation onto a smart offset locator",
     partial(_mel, "apply_smart_PivotParentAnimation(1.5);")),
    ("overrig.smart_orient", "Smart object", "Smart orient knot",
     "Bake the animation onto a smart orient locator",
     partial(_mel, "apply_smart_Knot_Orient_Point(1.5);")),
    ("overrig.smart_bake_object", "Smart object", "Smart bake (object keys)",
     "Bake with this object's keyframes",
     partial(_mel, "apply_Smart_Bake(0);")),
    ("overrig.smart_bake_knot", "Smart object", "Smart bake (knot keys)",
     "Bake with the smart knot's keyframes",
     partial(_mel, "apply_Smart_Bake(1);")),

    ("overrig.knot_orient", "Knot", "Knot orient",
     "Create an orient knot on the selection",
     partial(_mel, "apply_Knot_Orient_Point(1);")),
    ("overrig.knot_pivot", "Knot", "Pivot knot",
     "Create a pivot knot on the selection",
     partial(_mel, "apply_PivotParentAnimation(1);")),
    ("overrig.knot", "Knot", "Knot",
     "Create a knot on the selection",
     partial(_mel, "apply_parentConstrAnim(1);")),

    ("overrig.parent_out", "Parent", "Parent to world",
     "Lift the selection to world, animation re-baked",
     partial(_mel, "apply_Parent_out();")),
    ("overrig.parent_in", "Parent", "Parent inside",
     "Hang the child on the parent - select child first, parent last",
     partial(_mel, "apply_Parent_in();")),
    ("overrig.parent_swap", "Parent", "Swap parent",
     "Swap the parent", partial(_mel, "apply_Swap_parent();")),
    ("overrig.parent_across", "Parent", "Parent across knot",
     "Create a parent-across knot",
     partial(_mel, "apply_parent_anim_across(1);")),

    ("overrig.aim", "Aim", "Create aim",
     "Create the aim locators on the selection",
     partial(_mel, "make_aim_from_selected(1);")),
    ("overrig.overlap_window", "Aim", "Overlapper window",
     "Open the overlapper window",
     partial(_mel, "bar_tail_overlap_window;")),
    ("overrig.attach_on", "Aim", "Key attach 1",
     "Key the attach attribute at 1",
     partial(_mel, "setKey_on_attach_attr(1);")),
    ("overrig.attach_off", "Aim", "Key attach 0",
     "Key the attach attribute at 0",
     partial(_mel, "setKey_on_attach_attr(0);")),

    ("overrig.lag_key", "Key tools", "Lag key",
     "Lag the keys by 1.2 frames", partial(_mel, "Lag_Key(1.2);")),
    ("overrig.infinity_cycle", "Key tools", "Infinity: cycle",
     "Pre/post infinity to cycle",
     partial(_mel, 'set_infinity_graphEditor("cycle");')),
    ("overrig.infinity_oscillate", "Key tools", "Infinity: oscillate",
     "Pre/post infinity to oscillate",
     partial(_mel, 'set_infinity_graphEditor("oscillate");')),
    ("overrig.infinity_linear", "Key tools", "Infinity: linear",
     "Pre/post infinity to linear",
     partial(_mel, 'set_infinity_graphEditor("linear");')),
    ("overrig.infinity_constant", "Key tools", "Infinity: constant",
     "Pre/post infinity to constant",
     partial(_mel, 'set_infinity_graphEditor("constant");')),
    ("overrig.oscillate", "Key tools", "Oscillate keys",
     "Oscillate the period taken from the time slider",
     partial(_mel, "double_oscillate_keys(2);")),
    ("overrig.first_to_last", "Key tools", "Copy first frame to last",
     "For cycling animation", partial(_mel, "copy_start_frame_to_end();")),
    ("overrig.keys_first_last", "Key tools", "Key first and last frame",
     "Set keys on the first and last frame",
     partial(_mel, "set_start_end_key();")),
    ("overrig.key_range_all", "Key tools", "Key range: all",
     "The same keyframe across the selected time range",
     partial(_mel, 'set_key_time_range("all");')),
    ("overrig.key_range_translate", "Key tools", "Key range: translate",
     "Translate keys across the selected time range",
     partial(_mel, 'set_key_time_range("translate");')),
    ("overrig.key_range_rotate", "Key tools", "Key range: rotate",
     "Rotate keys across the selected time range",
     partial(_mel, 'set_key_time_range("rotate");')),
    ("overrig.key_range_channelbox", "Key tools", "Key range: channel box",
     "The channel box's channels across the selected time range",
     partial(_mel, 'set_key_time_range("channelbox");')),
    ("overrig.select_keys_range", "Key tools", "Select keys in range",
     "Select the current key or the selected frame range",
     partial(_mel, "selKeys_by_timerange();")),
    ("overrig.delete_keys", "Key tools", "Delete keys",
     "Delete the selected frames on every channel of every selection",
     partial(_mel, "delete_keys_from_selected_or_timeslider();")),
    ("overrig.slider_range", "Key tools", "Toggle slider range",
     "Toggle the time slider range by 24",
     partial(_mel, "time_slider_range(24);")),
    ("overrig.time_to_mid", "Key tools", "Time to mid selection",
     "Move the time slider to the middle of the selection",
     partial(_mel, "set_currenttime_to_mid_selection();")),
    ("overrig.copy_keys", "Key tools", "Copy keys",
     "Copy the selected single-curve frames",
     partial(_mel, "barn_copy_keys();")),
    ("overrig.paste_scaled", "Key tools", "Paste scaled keys",
     "Paste, scaled to the selected frames",
     partial(_mel, "barn_past_scaled_keys();")),
    ("overrig.offset_half_period", "Key tools", "Offset by half period",
     "Shift the keys by half a period",
     partial(_mel, "offset_keys_by_period(2);")),
    ("overrig.mirror_keys", "Key tools", "Mirror keys in X",
     "Inverse-mirror the selected keys about X",
     partial(_mel, 'double_inv_oscillate_or_mirror(2, "x", "x");')),
    ("overrig.noise_window", "Key tools", "Noise window",
     "Open the noise window", partial(_mel, "overRig_noise_window;")),
    ("overrig.tween_window", "Key tools", "Tween window",
     "Tween, overshoot and curve push",
     partial(_mel, "overRig_tween_window();")),
    ("overrig.tween_left", "Key tools", "Tween 0%",
     "All the way to the left-side key",
     partial(_mel, "bar_tween_machine(0, `ls -sl`);")),
    ("overrig.tween_right", "Key tools", "Tween 100%",
     "All the way to the right-side key",
     partial(_mel, "bar_tween_machine(1, `ls -sl`);")),

    ("overrig.select_constrained", "Selector", "Select constrained object",
     "From a knot to the object it drives",
     partial(_mel, "return_constrained_object(1);")),
    ("overrig.select_sources", "Selector", "Select rig sources",
     "Every object OverRig's rigs drive",
     partial(_mel, 'barn_sel_set_member("OverRig_rig_objects");')),
    ("overrig.select_knots", "Selector", "Select knots",
     "Every OverRig knot in the scene",
     partial(_mel, 'barn_sel_set_member("OverRig_knots");')),

    ("overrig.double_global", "Double knots", "Double global knot",
     "Create a double global knot",
     partial(_mel, "apply_DoubleUzelGlobal(1);")),
    ("overrig.double_local", "Double knots", "Double local knot",
     "Create a double local knot",
     partial(_mel, "apply_DoubleUzelLocal(1);")),

    ("overrig.snapshot_object", "Snapshot", "Object snapshot",
     "Create an object snapshot", partial(_mel, "apply_LOH_Fast(1);")),
    ("overrig.snapshot_component", "Snapshot", "Component snapshot",
     "Create a component snapshot",
     partial(_mel, "apply_LOH_Component(1);")),

    ("overrig.forward_hierarchy", "Hierarchy", "Forward hierarchy",
     "Create a forward hierarchy over the selection",
     partial(_mel, "apply_ForwHierarhy(1);")),
    ("overrig.reverse_hierarchy", "Hierarchy", "Reverse hierarchy",
     "Create a reverse hierarchy over the selection",
     partial(_mel, "apply_ReverseHierarhy(1);")),
    ("overrig.spine_menu", "Hierarchy", "Vertebra system menu",
     "Bake to the easy vertebra system",
     partial(_mel, "create_recalc_spine_rig_menue();")),

    ("overrig.to_ik", "IK", "Bake FK to IK",
     "Three or more selected joints to IK",
     partial(_mel, "apply_rebike_3_or_more_object_to_IK;")),
    ("overrig.spline_ik", "IK", "Bake to spline IK",
     "Two or more selected to spline IK",
     partial(_mel, "apply_objects_spline_IK(0);")),
    ("overrig.spline_ik_depend", "IK", "Bake to depend spline IK",
     "Two or more selected to dependent spline IK",
     partial(_mel, "apply_objects_spline_IK(1);")),

    ("overrig.bake", "Bake", "Bake",
     "Bake the selection", partial(_mel, "apply_Fast_Bake();")),
    ("overrig.bake_range", "Bake", "Bake range",
     "Bake min-max or the selected range, keys outside kept",
     partial(_mel, "apply_range_Fast_Bake();")),
    ("overrig.bake_layer", "Bake", "Bake to layer",
     "Bake the selection to an anim layer",
     partial(_mel, "apply_Bake_to_layer();")),
    ("overrig.bake_range_layer", "Bake", "Bake range to override layer",
     "Bake min-max or the selected range to an override layer",
     partial(_mel, "apply_range_Bake_to_Over_layer();")),
    ("overrig.strip_constraints", "Bake", "Delete constraint channels",
     "Strip the constraint channels from the selection",
     partial(_mel, "delete_constraint_attributes_on_objects(`ls -sl`);")),
    ("overrig.euler_filter", "Bake", "Euler filter",
     "Fast euler filter from zero",
     partial(_mel, "euler_filter_on_selected();")),
    ("overrig.viewport_on", "Bake", "Enable viewport",
     "Turn the viewport back on after a bake",
     partial(_mel, "OVR_en_viewport();")),

    ("overrig.arc_tool", "Sword", "Arc polish tool",
     "Open the arc polish tool", partial(_mel, "BP_arc_tool_menue();")),
    ("overrig.sword_reverse", "Sword", "Sword reverse system",
     "Assign the sword reverse system",
     partial(_mel, "assign_Sword_pivot_System(1);")),
    ("overrig.sword_system", "Sword", "Sword system",
     "Assign the sword system", partial(_mel, "assign_Sw_System;")),

    ("overrig.jiggle", "Physics", "Jiggle point",
     "Assign a physical point on the selection",
     partial(_mel, "assign_jiggle_bone_soft(1);")),
    ("overrig.chain_menu", "Physics", "Physic chain menu",
     "Open the physics chain window",
     partial(_mel, "dyn_tail_tool_window();")),

    ("overrig.locators_on_selected", "Misc", "Locators on selected",
     "Create locators on the selection",
     partial(_mel, "create_normalised_locators_on_selected();")),
    ("overrig.locators_inside", "Misc", "Locators inside",
     "Create locators inside the selection",
     partial(_mel, "mocup_parent_locators_inside();")),
    ("overrig.color_menu", "Misc", "Colour menu",
     "Override the display colour", partial(
         _mel, "small_DisplayColorOverrideUI();")),
    ("overrig.shape_menu", "Misc", "Shape menu",
     "Override the control shape",
     partial(_mel, "small_Shape_OverrideUI();")),
    ("overrig.scale_up", "Misc", "Scale locator or joint 1.5",
     "Locally scale the selected locator or joint",
     partial(_mel, "scale_selected_lock_or_joint(1.5);")),
    ("overrig.anim_pivot_last", "Misc", "Anim pivot (last selected)",
     "Animated pivot at the last selected position",
     partial(_mel, "move_and_rotate_total_pivot(0);")),
    ("overrig.anim_pivot_average", "Misc", "Anim pivot (average)",
     "Animated pivot at the average position",
     partial(_mel, "move_and_rotate_total_pivot(1);")),
    ("overrig.isolate_toggle", "Misc", "Isolate selection toggle",
     "Toggle isolate-select in the current viewport",
     partial(_mel, "apply_bar_isolate_selection_toggler(0);")),
    ("overrig.translate_axis", "Misc", "Translate tool axis",
     "Change the translate tool's axis",
     partial(_mel, "bar_translate_toggler();")),
    ("overrig.rotate_axis", "Misc", "Rotate tool axis",
     "Change the rotate tool's axis",
     partial(_mel, "bar_rotate_toggler();")),
    ("overrig.xray", "Misc", "X-ray toggle",
     "Toggle x-ray in the current viewport",
     partial(_mel, "bar_x_ray_toggler();")),

    ("overrig.finger_pivot_window", "Finger", "Finger pivot window",
     "Open the finger pivot window",
     partial(_mel, "brn_apply_finger_pivot_window();")),
    ("overrig.finger_bend", "Finger", "Finger bend",
     "Finger bend tool",
     partial(_mel, 'brn_apply_finger_bend_tool("bend");')),
    ("overrig.finger_3ik", "Finger", "Finger 3IK",
     "Finger three-joint IK",
     partial(_mel, 'brn_apply_finger_bend_tool("3IK");')),
    ("overrig.finger_4ik", "Finger", "Finger 4IK",
     "Finger four-joint IK variant",
     partial(_mel, 'brn_apply_finger_bend_tool("4IK_var");')),
    ("overrig.finger_rot_pivot", "Finger", "Finger rotate pivot",
     "Finger rotate-pivot tool",
     partial(_mel, 'brn_apply_finger_bend_tool("rot_piv");')),
    ("overrig.finger_twist", "Finger", "Finger twist",
     "Finger twist tool",
     partial(_mel, 'brn_apply_finger_bend_tool("twist");')),
)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_hotkeys -v`

Expected: PASS. If `test_the_whole_list_is_there` reports a number other than 84, count the rows against `function_for_hotkeys.TXT` rather than editing the expected number — the count is the test's whole point.

- [ ] **Step 5: Commit**

```bash
git add SkeldarAnim/maya_hotkeys.py tests/test_hotkeys.py
git commit -F commit-msg.txt
```

```
feat(hotkeys): OverRig's own hotkey list, grouped as its author grouped it

84 rows out of overrig/function_for_hotkeys.TXT with his arguments as
written there, his headings as the categories, and a row per named mode -
four for set_infinity_graphEditor, four for set_key_time_range, five for
brn_apply_finger_bend_tool - because on a keyboard each of those is a
separate key.

Each row sources OverRig first: in a fresh Maya with the OverRig shelf
button unpressed, MEL answers a keypress with "Cannot find procedure" in
the Script Editor, where nobody is looking (trap 20 from the hotkey side).
Deliberately NOT gated on the time slider's highlight the way our own MEL
entry points are - apply_range_Fast_Bake, selKeys_by_timerange and
double_oscillate_keys are ABOUT that range.

The two scene-global bake-and-delete-knots procedures are excluded and a
gone-test names both: they ignore the selection, and one keypress from
taking down hand-made setups is not where they belong. The ones needing
real arguments are in as their windows instead.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

## Task 3: `register()` — the table into Maya's command list

**Files:**
- Modify: `SkeldarAnim/maya_hotkeys.py`
- Modify: `tests/test_hotkeys.py`

**Interfaces:**
- Consumes: `COMMANDS`, `PREFIX`.
- Produces: `install_dir() -> str`, `command_name(key) -> str`, `command_body(key, dest=None) -> str`, `register(dest=None) -> (created, updated)`. Task 4's `toggle()` calls `register()`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_hotkeys.py`:

```python
class CommandNames(unittest.TestCase):

    def test_a_key_becomes_a_camel_case_name(self):
        self.assertEqual(maya_hotkeys.command_name("picker.build"),
                         "skeldarAnimPickerBuild")
        self.assertEqual(maya_hotkeys.command_name("overrig.parent_in"),
                         "skeldarAnimOverrigParentIn")

    def test_every_name_is_unique(self):
        names = [maya_hotkeys.command_name(row[0])
                 for row in maya_hotkeys.COMMANDS]
        self.assertEqual(len(names), len(set(names)))

    def test_every_name_is_legal_for_maya(self):
        for row in maya_hotkeys.COMMANDS:
            name = maya_hotkeys.command_name(row[0])
            self.assertTrue(name[0].isalpha(), name)
            self.assertTrue(name.replace("_", "").isalnum(), name)


class CommandBodies(unittest.TestCase):
    """The body is a one-liner into the table. A stale copy in the
    animator's prefs then still resolves through the current table, and an
    unknown key reports itself."""

    DEST = "C:/Users/Some Body/Documents/maya/scripts/SkeldarAnim"

    def test_the_body_bootstraps_and_dispatches(self):
        body = maya_hotkeys.command_body("picker.build", self.DEST)
        self.assertIn('_p = "{0}"'.format(self.DEST), body)
        self.assertIn("sys.path.insert(0, _p)", body)
        self.assertIn("import maya_hotkeys", body)
        self.assertIn('maya_hotkeys.run("picker.build")', body)

    def test_backslashes_never_reach_a_body(self):
        body = maya_hotkeys.command_body(
            "picker.build",
            "C:\\Users\\Some Body\\Documents\\maya\\scripts\\SkeldarAnim")
        self.assertNotIn("\\", body)

    def test_the_default_dest_is_where_the_module_lives(self):
        self.assertEqual(maya_hotkeys.install_dir(),
                         PLUGIN.replace("\\", "/"))
        self.assertIn(maya_hotkeys.install_dir(),
                      maya_hotkeys.command_body("picker.build"))


class Register(unittest.TestCase):

    DEST = "C:/prefs/SkeldarAnim"

    def setUp(self):
        self.fake = FakeCmds()
        use(self.fake)

    def test_it_creates_one_command_per_row(self):
        created, updated = maya_hotkeys.register(self.DEST)
        self.assertEqual(created, len(maya_hotkeys.COMMANDS))
        self.assertEqual(updated, 0)
        self.assertEqual(len(self.fake.runtime), len(maya_hotkeys.COMMANDS))

    def test_a_second_pass_edits_and_creates_nothing(self):
        maya_hotkeys.register(self.DEST)
        self.fake.creates = []
        created, updated = maya_hotkeys.register(self.DEST)
        self.assertEqual(created, 0)
        self.assertEqual(updated, len(maya_hotkeys.COMMANDS))
        self.assertEqual(self.fake.creates, [])

    def test_a_row_arrives_whole(self):
        maya_hotkeys.register(self.DEST)
        row = self.fake.runtime["skeldarAnimPickerBuild"]
        self.assertEqual(row["category"], "SkeldarAnim.Rig Picker")
        self.assertEqual(row["label"], "Build")
        self.assertIn('run("picker.build")', row["command"])

    def test_re_registration_refreshes_a_moved_install(self):
        maya_hotkeys.register("C:/old/SkeldarAnim")
        maya_hotkeys.register("C:/new/SkeldarAnim")
        body = self.fake.runtime["skeldarAnimPickerBuild"]["command"]
        self.assertIn("C:/new/SkeldarAnim", body)
        self.assertNotIn("C:/old/SkeldarAnim", body)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_hotkeys -v`

Expected: `AttributeError: module 'maya_hotkeys' has no attribute 'command_name'`.

- [ ] **Step 3: Implement**

Add to `SkeldarAnim/maya_hotkeys.py`, above the tables:

```python
# ------------------------------------------------------------ registration

def install_dir():
    """The folder this module was installed into.

    The path a command's body has to put on `sys.path`: a key pressed
    before any shelf button in a fresh Maya has nothing of ours there. Read
    from our own location, so the installed copy knows where it lives and a
    move is picked up by the next registration.
    """
    return os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")


def command_name(key):
    """`picker.build` -> `skeldarAnimPickerBuild`.

    Maya wants an identifier; the readable name is the row's `label`, which
    is what the Hotkey Editor shows.
    """
    parts = [chunk[:1].upper() + chunk[1:]
             for chunk in key.replace(".", "_").split("_") if chunk]
    return PREFIX + "".join(parts)


def command_body(key, dest=None):
    """The runTimeCommand's body: bootstrap, then dispatch through us.

    Deliberately a one-liner into the table rather than real logic. Maya
    SAVES a user runTimeCommand into userRunTimeCommands.mel (measured:
    `default` comes back False), so a body is a copy that outlives the
    installed plugin -- and this one keeps resolving through whatever table
    is current, or reports an unknown key instead of raising.
    """
    dest = install_dir() if dest is None \
        else dest.replace("\\", "/").rstrip("/")
    return ("import sys\n"
            "_p = \"{0}\"\n"
            "if _p not in sys.path:\n"
            "    sys.path.insert(0, _p)\n"
            "import maya_hotkeys\n"
            "maya_hotkeys.run(\"{1}\")\n").format(dest, key)


def register(dest=None):
    """Create or refresh every command. Returns (created, updated).

    Called from `toggle()` in both directions, which is the only moment
    registration happens: a press that turns the map OFF refreshes the
    commands too, so an updated plugin's rows -- and the path baked inside
    them -- come into step with what is on disk.
    """
    created = updated = 0
    for key, category, label, annotation, _action in COMMANDS:
        name = command_name(key)
        body = command_body(key, dest)
        if cmds.runTimeCommand(name, query=True, exists=True):
            cmds.runTimeCommand(name, edit=True, command=body,
                                category=category, label=label,
                                annotation=annotation,
                                commandLanguage="python")
            updated += 1
        else:
            cmds.runTimeCommand(name, command=body, category=category,
                                label=label, annotation=annotation,
                                commandLanguage="python", default=False)
            created += 1
    return created, updated
```

Note the ordering constraint: `register` reads `COMMANDS`, which is defined at the bottom of the file, and that is fine — the name is resolved when `register` runs, not when it is defined.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_hotkeys -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add SkeldarAnim/maya_hotkeys.py tests/test_hotkeys.py
git commit -F commit-msg.txt
```

```
feat(hotkeys): register the table as Maya runTimeCommands

One command per row, so the animator finds them in the Hotkey Editor's own
tree and drags them onto keys - categories nest with a dot (measured), and
the readable name is the row's label.

Every body is a one-liner into the table: bootstrap sys.path with the path
read from our own location, then run("<key>"). Maya saves a user
runTimeCommand into userRunTimeCommands.mel (measured: default comes back
False), so a body outlives the plugin - and a stale one still resolves
through whatever table is current instead of carrying dead logic.

Re-registration uses edit=True, which accepts command, category, label and
annotation (measured by querying them back), so it cannot disturb a binding
the way delete-and-recreate might.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

## Task 4: `toggle()` — the hotkey set and the way back

**Files:**
- Modify: `SkeldarAnim/maya_hotkeys.py`
- Modify: `tests/test_hotkeys.py`

**Interfaces:**
- Consumes: `register()`, `SET`, `PREVIOUS_VAR`, `FALLBACK_SET`, `_report`.
- Produces: `current_set()`, `is_active()`, `previous_set()`, `activate()`, `deactivate()`, `toggle()`, `open_editor()`. Task 5 adds `paint()` and calls it from `activate`/`deactivate`; Task 1's `window.hotkeys` row will be pointed at `toggle`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_hotkeys.py`:

```python
class TheSet(unittest.TestCase):
    """Created once as a copy of whatever is active, and never rebuilt --
    rebuilding would destroy the keys the animator assigned in it, which is
    the whole content of the feature."""

    def setUp(self):
        self.fake = FakeCmds(current="Maya_Default")
        use(self.fake)

    def test_the_first_activation_creates_it_from_the_current_set(self):
        maya_hotkeys.activate()
        self.assertIn("SkeldarAnim", self.fake.sets)
        self.assertEqual(self.fake.sources["SkeldarAnim"], "Maya_Default")
        self.assertEqual(self.fake.current, "SkeldarAnim")

    def test_a_second_activation_switches_without_recreating(self):
        maya_hotkeys.activate()
        maya_hotkeys.deactivate()
        self.fake.sources["SkeldarAnim"] = "TOUCHED"
        maya_hotkeys.activate()
        self.assertEqual(self.fake.current, "SkeldarAnim")
        self.assertEqual(self.fake.sources["SkeldarAnim"], "TOUCHED")
        self.assertEqual(self.fake.sets.count("SkeldarAnim"), 1)

    def test_it_copies_the_animators_own_set_when_that_is_current(self):
        self.fake.sets.append("Eugene")
        self.fake.current = "Eugene"
        maya_hotkeys.activate()
        self.assertEqual(self.fake.sources["SkeldarAnim"], "Eugene")

    def test_deactivate_returns_to_what_was_remembered(self):
        self.fake.sets.append("Eugene")
        self.fake.current = "Eugene"
        maya_hotkeys.activate()
        maya_hotkeys.deactivate()
        self.assertEqual(self.fake.current, "Eugene")

    def test_activating_while_already_ours_keeps_the_memory(self):
        """Or the way out would lead back in and the animator would be stuck
        in a map with no exit but the Hotkey Editor."""
        self.fake.sets.append("Eugene")
        self.fake.current = "Eugene"
        maya_hotkeys.activate()
        maya_hotkeys.activate()
        maya_hotkeys.deactivate()
        self.assertEqual(self.fake.current, "Eugene")

    def test_a_vanished_memory_falls_back_to_maya_default(self):
        self.fake.sets.append("Eugene")
        self.fake.current = "Eugene"
        maya_hotkeys.activate()
        self.fake.sets.remove("Eugene")
        maya_hotkeys.deactivate()
        self.assertEqual(self.fake.current, "Maya_Default")

    def test_no_memory_at_all_falls_back_to_maya_default(self):
        self.fake.sets.append("SkeldarAnim")
        self.fake.current = "SkeldarAnim"
        maya_hotkeys.deactivate()
        self.assertEqual(self.fake.current, "Maya_Default")

    def test_the_memory_survives_in_an_optionvar(self):
        self.fake.sets.append("Eugene")
        self.fake.current = "Eugene"
        maya_hotkeys.activate()
        self.assertEqual(
            self.fake.optionvars[maya_hotkeys.PREVIOUS_VAR], "Eugene")

    def test_our_set_is_never_remembered_as_the_way_back(self):
        self.fake.optionvars[maya_hotkeys.PREVIOUS_VAR] = "SkeldarAnim"
        self.fake.sets.append("SkeldarAnim")
        self.assertEqual(maya_hotkeys.previous_set(), "Maya_Default")


class TheState(unittest.TestCase):
    """Read from Maya at every press, never cached: the animator can switch
    sets by hand in the editor between two presses."""

    def setUp(self):
        self.fake = FakeCmds()
        use(self.fake)

    def test_is_active_reads_the_current_set(self):
        self.assertFalse(maya_hotkeys.is_active())
        self.fake.sets.append("SkeldarAnim")
        self.fake.current = "SkeldarAnim"
        self.assertTrue(maya_hotkeys.is_active())

    def test_toggle_switches_both_ways(self):
        maya_hotkeys.toggle()
        self.assertEqual(self.fake.current, "SkeldarAnim")
        maya_hotkeys.toggle()
        self.assertEqual(self.fake.current, "Maya_Default")

    def test_toggle_registers_in_both_directions(self):
        maya_hotkeys.toggle()
        self.assertEqual(len(self.fake.runtime), len(maya_hotkeys.COMMANDS))
        self.fake.runtime.clear()
        maya_hotkeys.toggle()
        self.assertEqual(len(self.fake.runtime), len(maya_hotkeys.COMMANDS))

    def test_a_hand_switch_to_a_third_set_is_respected(self):
        """Ours is not current, so the press must turn the map ON, not off."""
        maya_hotkeys.toggle()
        self.fake.sets.append("Somebody Else")
        self.fake.current = "Somebody Else"
        maya_hotkeys.toggle()
        self.assertEqual(self.fake.current, "SkeldarAnim")


class TheEditorOnFirstPress(unittest.TestCase):
    """A set that is a copy of the current one behaves exactly like it until
    keys are assigned in it -- so without this the first press looks like a
    button that does nothing."""

    def setUp(self):
        self.fake = FakeCmds()
        use(self.fake)

    def test_creation_opens_the_hotkey_editor(self):
        maya_hotkeys.activate()
        self.assertIn(maya_hotkeys.EDITOR_COMMAND + ";", self.fake.evaluated)

    def test_later_presses_do_not(self):
        maya_hotkeys.activate()
        maya_hotkeys.deactivate()
        self.fake.evaluated = []
        maya_hotkeys.activate()
        self.assertEqual(self.fake.evaluated, [])

    def test_the_creation_message_names_both_sets(self):
        self.fake.sets.append("Eugene")
        self.fake.current = "Eugene"
        message = maya_hotkeys.activate()
        self.assertIn("SkeldarAnim", message)
        self.assertIn("Eugene", message)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_hotkeys -v`

Expected: `AttributeError: module 'maya_hotkeys' has no attribute 'activate'`.

- [ ] **Step 3: Implement**

Add to `SkeldarAnim/maya_hotkeys.py`, after `register`:

```python
# ------------------------------------------------------------ the hotkey set

def current_set():
    """Maya's active hotkey set."""
    return cmds.hotkeySet(query=True, current=True)


def is_active():
    """True when the map is on.

    Asked at every press and never cached: the animator can switch sets by
    hand in the Hotkey Editor between two presses, and a stored boolean
    would then lie -- the same reason `picker_window._resolution`
    re-asserts its binding on every sync.
    """
    return current_set() == SET


def previous_set():
    """The set to come back to.

    Ours is never an answer: it would make the way out lead back in. A
    remembered set that has since been deleted is not one either, so both
    fall back to `Maya_Default`, which always exists and cannot be deleted.
    """
    remembered = ""
    if cmds.optionVar(exists=PREVIOUS_VAR):
        remembered = cmds.optionVar(query=PREVIOUS_VAR) or ""
    if remembered and remembered != SET \
            and cmds.hotkeySet(remembered, query=True, exists=True):
        return remembered
    return FALLBACK_SET


def open_editor():
    """Maya's own Hotkey Editor -- the editor for this map."""
    mel.eval(EDITOR_COMMAND + ";")


def activate():
    """Switch to our set, creating it if this is its first press.

    The set is created ONCE, as a copy of whatever is active at that
    moment, and never rebuilt: rebuilding it on every press would keep the
    copy in step with the base set and destroy every key the animator
    assigned in it.
    """
    base = current_set()
    fresh = not cmds.hotkeySet(SET, query=True, exists=True)
    if base != SET:
        cmds.optionVar(stringValue=(PREVIOUS_VAR, base))
    if fresh:
        cmds.hotkeySet(SET, source=base, current=True)
    else:
        cmds.hotkeySet(SET, edit=True, current=True)
    if fresh:
        open_editor()
        return _report("Hotkeys: {0} created from {1} - assign your "
                       "keys".format(SET, base))
    return _report("Hotkeys: " + SET)


def deactivate():
    """Put the animator's own set back."""
    back = previous_set()
    cmds.hotkeySet(back, edit=True, current=True)
    return _report("Hotkeys: " + back)


def toggle():
    """The shelf button. Registers first, in both directions."""
    register()
    return deactivate() if is_active() else activate()
```

Then point the `window.hotkeys` row at it — add to `_OURS`, after `window.overshoot`:

```python
    ("window.hotkeys", "Windows", "Hotkey map on/off",
     "Switch between the SkeldarAnim hotkey set and your own", toggle),
```

The table sits at the bottom of the file, below every function, so `toggle`
is a plain name here rather than a lambda.

And widen Task 1's opener test, which now has a fifth key to expect:

```python
    def test_the_four_openers_and_the_toggle(self):
        self.assertEqual(sorted(self._keys("window.")),
                         ["window.hotkeys", "window.overshoot",
                          "window.picker", "window.scenesetup",
                          "window.uebridge"])
```

(rename `test_the_four_openers` to this and replace its body; the class
docstring's "joins the Windows group in Task 4" note comes out too).

- [ ] **Step 4: Run the tests to verify they pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_hotkeys -v`

Expected: PASS. `OurRows.test_the_four_windows_and_the_toggle` now finds its fifth key.

- [ ] **Step 5: Commit**

```bash
git add SkeldarAnim/maya_hotkeys.py tests/test_hotkeys.py
git commit -F commit-msg.txt
```

```
feat(hotkeys): the set, and the way back out of it

Created once as a copy of whatever is active - so Ctrl+Z, Q/W/E/R and the
animator's own keys keep working and only what they assign is different -
and never rebuilt, because rebuilding would destroy exactly those
assignments.

The previous set is remembered in an optionVar rather than a module
variable: the map is sticky by choice, so the session that turns it off is
often not the one that turned it on. Ours is never an answer to "where do I
go back to" (the way out would lead back in), a deleted memory falls back to
Maya_Default, and activating while already ours keeps the memory.

State is read from `hotkeySet -q -current` at every press and never cached -
the animator can switch sets by hand in the editor between two presses.

The first press in the map's life opens the Hotkey Editor: a copy of the
current set behaves exactly like it until keys are assigned, so without
that the press looks like a button that does nothing.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

## Task 5: The shelf button's paint

**Files:**
- Modify: `SkeldarAnim/maya_hotkeys.py`
- Modify: `tests/test_hotkeys.py`

**Interfaces:**
- Consumes: `SHELF`, `BUTTON_LABEL`, `ON_COLOUR`, `activate()`, `deactivate()`.
- Produces: `shelf_button(shelf=SHELF, label=BUTTON_LABEL)`, `paint(active)`; `activate`/`deactivate` call `paint`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_hotkeys.py`:

```python
class ThePaint(unittest.TestCase):
    """A shelf button's command runs with no widget context, so the button
    has to find itself. Not finding it is not an error: the set still
    switches and only the paint is skipped."""

    def setUp(self):
        self.fake = FakeCmds(
            shelves={"SkeldarAnim": ["btn1", "btn2", "btn3"]},
            buttons={"btn1": "Rig Picker", "btn2": "Hotkeys",
                     "btn3": "OverRig"})
        use(self.fake)

    def test_it_finds_itself_by_label(self):
        self.assertEqual(maya_hotkeys.shelf_button(), "btn2")

    def test_no_shelf_is_not_an_error(self):
        self.fake.shelves = {}
        self.assertIsNone(maya_hotkeys.shelf_button())
        self.assertFalse(maya_hotkeys.paint(True))

    def test_no_button_of_ours_is_not_an_error(self):
        self.fake.buttons["btn2"] = "Something Else"
        self.assertIsNone(maya_hotkeys.shelf_button())

    def test_activate_lights_it_and_deactivate_puts_it_out(self):
        maya_hotkeys.activate()
        self.assertEqual(self.fake.painted[-1],
                         ("btn2", True, maya_hotkeys.ON_COLOUR))
        maya_hotkeys.deactivate()
        self.assertEqual(self.fake.painted[-1],
                         ("btn2", False, maya_hotkeys.ON_COLOUR))

    def test_a_missing_button_does_not_stop_the_switch(self):
        self.fake.shelves = {}
        maya_hotkeys.activate()
        self.assertEqual(self.fake.current, "SkeldarAnim")
```

- [ ] **Step 2: Run them to verify they fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_hotkeys.ThePaint -v`

Expected: `AttributeError: module 'maya_hotkeys' has no attribute 'shelf_button'`.

- [ ] **Step 3: Implement**

Add to `SkeldarAnim/maya_hotkeys.py`, before `activate`:

```python
# --------------------------------------------------------------- the button

def shelf_button(shelf=SHELF, label=BUTTON_LABEL):
    """Our shelf button, or None.

    A shelf button's command runs with no widget context, so there is no
    `self` to edit -- the button is found by walking the shelf's children
    and matching the label we gave it. Not finding it is a normal outcome
    (the module called from the Script Editor, the shelf renamed): the set
    still switches and only the paint is skipped.
    """
    if not cmds.shelfLayout(shelf, exists=True):
        return None
    for child in cmds.shelfLayout(shelf, query=True, childArray=True) or []:
        if not cmds.control(child, query=True, exists=True):
            continue
        if cmds.shelfButton(child, query=True, label=True) == label:
            return child
    return None


def paint(active):
    """Light the button while the map is on. True when it was painted."""
    button = shelf_button()
    if not button:
        return False
    cmds.shelfButton(button, edit=True, enableBackground=bool(active),
                     backgroundColor=ON_COLOUR)
    return True
```

and add the calls: `paint(True)` as the last statement before the two `return _report(...)` lines in `activate()`, and `paint(False)` before the `return` in `deactivate()`:

```python
    if fresh:
        cmds.hotkeySet(SET, source=base, current=True)
    else:
        cmds.hotkeySet(SET, edit=True, current=True)
    paint(True)
    if fresh:
```

```python
    back = previous_set()
    cmds.hotkeySet(back, edit=True, current=True)
    paint(False)
    return _report("Hotkeys: " + back)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_hotkeys -v`

Expected: PASS, the whole file.

- [ ] **Step 5: Commit**

```bash
git add SkeldarAnim/maya_hotkeys.py tests/test_hotkeys.py
git commit -F commit-msg.txt
```

```
feat(hotkeys): the shelf button lights while the map is on

Maya shows the active hotkey set nowhere but the Hotkey Editor's own
dropdown, so a toggle with no feedback is a toggle you lose track of.
shelfButton carries -enableBackground and -backgroundColor (measured).

A shelf button's command runs with no widget context, so the button finds
itself by walking the shelf's childArray and matching its label. Not
finding it is a normal outcome - the module run from the Script Editor, the
shelf renamed - and the switch still happens.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

## Task 6: The installer — payload, sixth button, icon

**Files:**
- Modify: `SkeldarAnim/install.py`
- Modify: `SkeldarAnim/icons/make_icons.py`
- Create: `SkeldarAnim/icons/hotkeys.png` (generated)
- Modify: `tests/test_install.py`

**Interfaces:**
- Consumes: `maya_hotkeys.toggle` as the button's function name.
- Produces: `install.payload()` containing `"maya_hotkeys.py"`; `install.button_specs(dest)` returning six specs, `Hotkeys` fifth and `OverRig` last.

- [ ] **Step 1: Write the failing tests**

In `tests/test_install.py`, change `ButtonSpecs.test_five_buttons_in_shelf_order` to:

```python
    def test_six_buttons_in_shelf_order(self):
        labels = [s["label"] for s in self._specs()]
        self.assertEqual(labels, ["Rig Picker", "UE Bridge", "Scene Setup",
                                  "Overshoot", "Hotkeys", "OverRig"])
```

and update the three tests that slice `[:4]` or index `[4]` — the Python buttons are now five and OverRig is `[5]`:

```python
    def test_python_buttons_bootstrap_and_call(self):
        wanted = {
            "Rig Picker": ("maya_overrig", "show_picker"),
            "UE Bridge": ("maya_uebridge", "show_window"),
            "Scene Setup": ("maya_scenesetup", "show_window"),
            "Overshoot": ("maya_overshoot", "show_overshoot_ui"),
            "Hotkeys": ("maya_hotkeys", "toggle"),
        }
        for spec in self._specs()[:5]:
            module, func = wanted[spec["label"]]
            self.assertEqual(spec["sourceType"], "python")
            self.assertIn(self.DEST, spec["command"])
            self.assertIn("sys.path.insert(0, _p)", spec["command"])
            self.assertIn("import {0}".format(module), spec["command"])
            self.assertIn("{0}.{1}()".format(module, func), spec["command"])

    def test_python_buttons_use_our_icons(self):
        icons = [s["image"] for s in self._specs()[:5]]
        self.assertEqual(icons, [
            self.DEST + "/icons/picker.png",
            self.DEST + "/icons/uebridge.png",
            self.DEST + "/icons/scenesetup.png",
            self.DEST + "/icons/overshoot.png",
            self.DEST + "/icons/hotkeys.png"])
```

In `test_overrig_button_replays_the_native_installer`, change `spec = self._specs()[4]` to `spec = self._specs()[5]`.

Add to the `Payload` class:

```python
    def test_the_hotkey_map_ships(self):
        self.assertIn("maya_hotkeys.py", install.payload())

    def test_every_icon_a_button_names_exists(self):
        """A missing icon is a shelf button with a blank square on it."""
        for spec in install.button_specs(PLUGIN):
            self.assertTrue(os.path.exists(spec["image"]), spec["image"])
```

- [ ] **Step 2: Run them to verify they fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_install -v`

Expected: FAIL — five labels against six expected, and `maya_hotkeys.py` not in the payload.

- [ ] **Step 3: Wire the installer**

In `SkeldarAnim/install.py`, add to `_PAYLOAD` after `"maya_overshoot.py"`:

```python
    "maya_hotkeys.py",
```

and to `_PYTHON_BUTTONS` after the Overshoot row:

```python
    ("Hotkeys", "Temporary hotkey map on/off - assign keys in Maya's "
     "Hotkey Editor", "maya_hotkeys", "toggle", "hotkeys.png"),
```

- [ ] **Step 4: Draw the icon**

In `SkeldarAnim/icons/make_icons.py`, add before `DRAWERS`:

```python
def draw_hotkeys(path):
    """A keycap with a spark: the map switches on."""
    image, painter = _canvas()
    painter.setPen(_pen("#ba68c8", 2.0))
    painter.setBrush(Qt.NoBrush)
    painter.drawRoundedRect(QRectF(6.5, 8.5, 14, 14), 3, 3)
    painter.setPen(_pen("#ba68c8", 1.6))
    painter.drawLine(QPointF(10, 19), QPointF(17, 19))
    painter.setPen(_pen("#ba68c8", 2.2))
    painter.drawLine(QPointF(13.5, 12), QPointF(13.5, 16))
    painter.setPen(_pen("#f06292", 2.2))
    painter.drawLine(QPointF(23, 10), QPointF(25.5, 15))
    painter.drawLine(QPointF(25.5, 15), QPointF(22, 15))
    painter.drawLine(QPointF(22, 15), QPointF(24.5, 21))
    painter.end()
    image.save(path)
```

and a row to `DRAWERS`:

```python
    "hotkeys.png": draw_hotkeys,
```

Then generate and eyeball it:

```bash
QT_QPA_PLATFORM=offscreen "C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe" SkeldarAnim/icons/make_icons.py
```

Expected: `wrote hotkeys.png` among the five. Open `SkeldarAnim/icons/hotkeys.png` and look at it — it is a 32×32 icon on a dark plate and it has to read at that size. The other four are the reference for weight and colour.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_install tests.test_make_build -v`

Expected: PASS. `test_make_build` reads the payload from the installer, so it follows on its own — if it fails, its expectation was hardcoded somewhere and that is the bug to fix.

- [ ] **Step 6: Run the whole suite**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v`

Expected: everything passes.

- [ ] **Step 7: Commit**

```bash
git add SkeldarAnim/install.py SkeldarAnim/icons/make_icons.py SkeldarAnim/icons/hotkeys.png tests/test_install.py
git commit -F commit-msg.txt
```

```
feat(hotkeys): the sixth shelf button

maya_hotkeys.py into the payload and `Hotkeys` into the button table, ahead
of OverRig. A toggle has the same call shape as an opener, so the row goes
into _PYTHON_BUTTONS unchanged: bootstrap sys.path, import, call.

The icon is drawn by icons/make_icons.py like the other four and committed
beside its generator. A new test asserts every icon a button names exists
on disk - a missing one is a shelf button with a blank square on it, which
no existing test would have caught.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

## Task 7: `verify_hotkeys.py` — the live proof

**Files:**
- Create: `docs/superpowers/plans/verify_hotkeys.py`

**Interfaces:**
- Consumes: the installed `maya_hotkeys` module.
- Produces: nothing importable; a script sent through the command-port bridge.

This task writes the script and does not run it — running it needs the animator's Maya with the command port open. Its gates are the only proof of the `hotkeySet` half, which no unit test can reach.

- [ ] **Step 1: Write the script**

Create `docs/superpowers/plans/verify_hotkeys.py`:

```python
"""Live verification of the temporary hotkey map, run inside Maya.

`hotkeySet` needs a UI -- it raises "Maya command error" in mayapy -- so
everything about the SET itself is proved here and nowhere else.

This script touches PREFS, not the scene, which changes the hygiene rules:
the current set name and the whole set list are recorded first, every
restore step stands on its own (trap 42: one raising teardown step abandons
the rest), and our set is deleted only if THIS RUN created it. An animator
who already has a SkeldarAnim set with their own keys in it must find it
exactly as they left it -- those gates skip themselves and say why, the way
phase 2 of verify_two_characters.py steps aside when it finds manifests
that are not its own.

Sent through the command-port bridge. Bridge hygiene lives in the runner
(if-guarded marker, no SystemExit, unique output file); this script only
has to avoid modal dialogs.
"""

import sys

import maya.cmds as cmds
import maya.mel as mel

REPO = "C:/!!!Work/MayaScripts/SkeldarAnim"

if REPO not in sys.path:
    sys.path.insert(0, REPO)
for name in [n for n in list(sys.modules)
             if n == "maya_hotkeys" or n.split(".")[0] in
             ("maya_overrig", "maya_scenesetup", "maya_uebridge")]:
    del sys.modules[name]

import maya_hotkeys  # noqa: E402

RESULTS = []
TEST_SET = "SkeldarAnim_verify_base"
TEST_KEY = "F12"


def gate(number, name, passed, detail=""):
    RESULTS.append("GATE {0} {1} {2}{3}".format(
        number, "PASS" if passed else "FAIL", name,
        " - " + str(detail) if detail else ""))


def skip(number, name, why):
    RESULTS.append("GATE {0} SKIP {1} - {2}".format(number, name, why))


# ---- what we found, so we can put it back ---------------------------
set_before = cmds.hotkeySet(query=True, current=True)
sets_before = sorted(cmds.hotkeySet(query=True, hotkeySetArray=True) or [])
ours_existed = maya_hotkeys.SET in sets_before
# Gate 13 runs a real OverRig row, and that one selects: the animator's
# selection is theirs, and a verify run gives it back (CLAUDE.md's rule).
selection_before = cmds.ls(selection=True, long=True) or []
var_before = cmds.optionVar(query=maya_hotkeys.PREVIOUS_VAR) \
    if cmds.optionVar(exists=maya_hotkeys.PREVIOUS_VAR) else None
created = []

RESULTS.append("BEFORE current={0} sets={1} ours_existed={2}".format(
    set_before, sets_before, ours_existed))

try:
    # ---- Gate 1: registration lands in Maya's command list ----------
    try:
        result = maya_hotkeys.register()
        name = maya_hotkeys.command_name("picker.build")
        exists = cmds.runTimeCommand(name, query=True, exists=True)
        category = cmds.runTimeCommand(name, query=True, category=True) \
            if exists else ""
        gate(1, "every row registered",
             exists and category == "SkeldarAnim.Rig Picker",
             "{0} created/updated, {1} -> {2}".format(
                 result, name, category))
    except Exception as exc:
        gate(1, "every row registered", False, repr(exc))

    # ---- Gate 2: all 107 of them are really there -------------------
    try:
        missing = [maya_hotkeys.command_name(row[0])
                   for row in maya_hotkeys.COMMANDS
                   if not cmds.runTimeCommand(
                       maya_hotkeys.command_name(row[0]),
                       query=True, exists=True)]
        gate(2, "no row missing", not missing,
             "{0} rows, missing {1}".format(
                 len(maya_hotkeys.COMMANDS), missing[:5]))
    except Exception as exc:
        gate(2, "no row missing", False, repr(exc))

    # ---- Gate 3: re-registration is an edit, not a duplicate --------
    try:
        again = maya_hotkeys.register()
        gate(3, "re-registration edits", again[0] == 0, str(again))
    except Exception as exc:
        gate(3, "re-registration edits", False, repr(exc))

    # ---- Gate 4: a base set of our own, so nothing of theirs moves --
    try:
        if TEST_SET in (cmds.hotkeySet(query=True, hotkeySetArray=True) or []):
            cmds.hotkeySet(TEST_SET, edit=True, delete=True)
        cmds.hotkeySet(TEST_SET, source=set_before, current=True)
        created.append(TEST_SET)
        gate(4, "sandbox base set is current",
             cmds.hotkeySet(query=True, current=True) == TEST_SET, TEST_SET)
    except Exception as exc:
        gate(4, "sandbox base set is current", False, repr(exc))

    # ---- Gate 5: a sample key in the base set -----------------------
    # A hotkey binds a nameCommand, not a runTimeCommand: the Hotkey Editor
    # makes one when a command is dragged onto a key, and with no editor in
    # the loop we make it ourselves. Every key this script binds is bound
    # while the SANDBOX set is current, so the animator's own set is never
    # written to -- and the sandbox is deleted whole at the end.
    if cmds.hotkeySet(query=True, current=True) != TEST_SET:
        skip(5, "sample key bound in the base set",
             "the sandbox set is not current - refusing to bind a key in "
             "the animator's own set")
    else:
        try:
            key_before = cmds.hotkey(keyShortcut=TEST_KEY, query=True,
                                     name=True) or ""
            cmds.nameCommand("skeldarAnimVerifyProbe",
                             annotation="verify probe",
                             command="skeldarAnimPickerBuild",
                             sourceType="mel")
            cmds.hotkey(keyShortcut=TEST_KEY,
                        name="skeldarAnimVerifyProbe")
            sample = cmds.hotkey(keyShortcut=TEST_KEY, query=True,
                                 name=True) or ""
            gate(5, "sample key bound in the base set",
                 sample == "skeldarAnimVerifyProbe",
                 "{0}, was {1}".format(sample, key_before or "unbound"))
        except Exception as exc:
            gate(5, "sample key bound in the base set", False, repr(exc))

    # ---- Gates 6-9: create ours as a copy of that base ---------------
    if ours_existed:
        for number, name in ((6, "created from the current set"),
                             (7, "the copy inherited the sample key"),
                             (8, "the editor opened on creation")):
            skip(number, name,
                 "a SkeldarAnim set already exists - not touching the "
                 "animator's own keys")
    else:
        try:
            message = maya_hotkeys.activate()
            created.append(maya_hotkeys.SET)
            gate(6, "created from the current set",
                 cmds.hotkeySet(query=True, current=True)
                 == maya_hotkeys.SET and TEST_SET in message, message)
        except Exception as exc:
            gate(6, "created from the current set", False, repr(exc))
        try:
            inherited = cmds.hotkey(keyShortcut=TEST_KEY, query=True,
                                    name=True) or ""
            gate(7, "the copy inherited the sample key",
                 inherited == "skeldarAnimVerifyProbe", inherited)
        except Exception as exc:
            gate(7, "the copy inherited the sample key", False, repr(exc))
        try:
            # The editor's window id is not documented, so ask Maya what is
            # up rather than guessing a name. It is non-modal, which is what
            # makes it safe to open over the command port at all (bridge
            # note 6: a modal dialog blocks the idle queue).
            windows = [w for w in (cmds.lsUI(windows=True) or [])
                       if "otkey" in w]
            gate(8, "the editor opened on creation", bool(windows),
                 "windows: " + str(windows))
        except Exception as exc:
            gate(8, "the editor opened on creation", False, repr(exc))

    # ---- Gate 9: the way back is the recorded name -------------------
    try:
        cmds.optionVar(stringValue=(maya_hotkeys.PREVIOUS_VAR, TEST_SET))
        if not maya_hotkeys.is_active():
            cmds.hotkeySet(maya_hotkeys.SET, edit=True, current=True)
        maya_hotkeys.deactivate()
        gate(9, "toggle back lands on the remembered set",
             cmds.hotkeySet(query=True, current=True) == TEST_SET,
             cmds.hotkeySet(query=True, current=True))
    except Exception as exc:
        gate(9, "toggle back lands on the remembered set", False, repr(exc))

    # ---- Gate 10: a hand-switch between presses is respected ---------
    try:
        maya_hotkeys.activate()
        cmds.hotkeySet(TEST_SET, edit=True, current=True)   # by hand
        maya_hotkeys.toggle()
        gate(10, "a hand-switch turns the map ON, not off",
             cmds.hotkeySet(query=True, current=True) == maya_hotkeys.SET,
             cmds.hotkeySet(query=True, current=True))
    except Exception as exc:
        gate(10, "a hand-switch turns the map ON, not off", False, repr(exc))

    # ---- Gate 11: the command body reaches run() ---------------------
    # The chain a keypress travels is key -> nameCommand -> runTimeCommand
    # -> body -> run(). A keypress cannot be sent over the port and a
    # nameCommand cannot be QUERIED (it has no -q flag at all, measured),
    # so the two halves are proved separately: gate 5 bound the key to a
    # nameCommand, and this runs a runTimeCommand the way Maya runs one --
    # by its own name, as MEL -- with a probe row standing in for a real
    # one so nothing in the scene moves.
    try:
        maya_hotkeys._REACHED = []
        maya_hotkeys._INDEX["verify.probe"] = (
            "verify.probe", "SkeldarAnim.Windows", "Probe", "probe",
            lambda: maya_hotkeys._REACHED.append(1))
        if cmds.runTimeCommand("skeldarAnimVerifyReach", query=True,
                               exists=True):
            cmds.runTimeCommand("skeldarAnimVerifyReach", edit=True,
                                delete=True)
        cmds.runTimeCommand(
            "skeldarAnimVerifyReach", command=maya_hotkeys.command_body(
                "verify.probe"), commandLanguage="python", default=False)
        mel.eval("skeldarAnimVerifyReach;")
        target = cmds.runTimeCommand("skeldarAnimPickerBuild", query=True,
                                     exists=True)
        gate(11, "a command body reaches run()",
             maya_hotkeys._REACHED == [1] and target,
             "reached {0}, gate 5's nameCommand target exists: {1}".format(
                 maya_hotkeys._REACHED, target))
    except Exception as exc:
        gate(11, "a command body reaches run()", False, repr(exc))
    finally:
        maya_hotkeys._INDEX.pop("verify.probe", None)

    # ---- Gate 12: the shelf button paints both ways ------------------
    try:
        button = maya_hotkeys.shelf_button()
        if not button:
            skip(12, "the shelf button paints",
                 "no Hotkeys button on the shelf - re-drag install.py")
        else:
            maya_hotkeys.paint(True)
            on = cmds.shelfButton(button, query=True,
                                  enableBackground=True)
            maya_hotkeys.paint(False)
            off = cmds.shelfButton(button, query=True,
                                   enableBackground=True)
            gate(12, "the shelf button paints", on and not off,
                 "{0}: on={1} off={2}".format(button, on, off))
    except Exception as exc:
        gate(12, "the shelf button paints", False, repr(exc))

    # ---- Gate 13: an OverRig row sources the toolset -----------------
    # Only honest in a FRESH Maya, where the OverRig shelf button has not
    # been pressed: that is the whole trap-20 case. Run it there.
    try:
        from maya_overrig import overrig
        was_loaded = overrig.is_loaded()
        maya_hotkeys.run("overrig.select_knots")
        gate(13, "an OverRig row sources the toolset",
             overrig.is_loaded(),
             "loaded before: {0} (only proves trap 20 in a fresh "
             "Maya)".format(was_loaded))
    except Exception as exc:
        gate(13, "an OverRig row sources the toolset", False, repr(exc))

finally:
    # Each step on its own: one raising teardown abandons the rest.
    #
    # The key does not need unbinding: every binding this script made was
    # made while the SANDBOX set was current, and the sandbox is deleted
    # below. `skeldarAnimVerifyProbe` is left behind on purpose -- Maya has
    # no flag that deletes a nameCommand -- named so it is recognisable in
    # the Hotkey Editor's list, and inert with nothing bound to it.
    try:
        if cmds.runTimeCommand("skeldarAnimVerifyReach", query=True,
                               exists=True):
            cmds.runTimeCommand("skeldarAnimVerifyReach", edit=True,
                                delete=True)
    except Exception:
        pass
    try:
        if set_before in (cmds.hotkeySet(query=True, hotkeySetArray=True)
                          or []):
            cmds.hotkeySet(set_before, edit=True, current=True)
    except Exception:
        pass
    for name in created:
        try:
            if cmds.hotkeySet(name, query=True, exists=True):
                cmds.hotkeySet(name, edit=True, delete=True)
        except Exception:
            pass
    try:
        if var_before is None:
            cmds.optionVar(remove=maya_hotkeys.PREVIOUS_VAR)
        else:
            cmds.optionVar(stringValue=(maya_hotkeys.PREVIOUS_VAR,
                                        var_before))
    except Exception:
        pass
    try:
        alive = [node for node in selection_before if cmds.objExists(node)]
        if alive:
            cmds.select(alive, replace=True)
        else:
            cmds.select(clear=True)
    except Exception:
        pass

    sets_after = sorted(cmds.hotkeySet(query=True, hotkeySetArray=True)
                        or [])
    current_after = cmds.hotkeySet(query=True, current=True)
    RESULTS.append("AFTER current={0} sets={1}".format(
        current_after, sets_after))
    RESULTS.append("HYGIENE sets restored: {0}, current restored: {1}".format(
        sets_after == sets_before, current_after == set_before))

    failed = len([line for line in RESULTS if " FAIL " in line])
    print("\n".join(RESULTS))
    print("VERIFY hotkeys: {0} of {1} gates failed".format(
        failed, len([line for line in RESULTS if line.startswith("GATE")])))
```

- [ ] **Step 2: Syntax-check it without running it**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m py_compile docs/superpowers/plans/verify_hotkeys.py`

Expected: no output, exit 0. (Do not *run* it under `mayapy` — `hotkeySet` needs a UI and the first gate would die.)

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/plans/verify_hotkeys.py
git commit -F commit-msg.txt
```

```
test(hotkeys): the live proof of the set half

hotkeySet needs a UI, so 13 gates that no unit test can reach: registration
lands in Maya's command list with the right category, all 107 rows are
there, re-registration edits rather than duplicates, the set is created as a
copy of a sandbox base and inherits its sample key, the editor opens on
creation, the toggle back lands on the remembered name, a hand-switch
between presses turns the map ON rather than off, a bound key reaches run(),
the button paints both ways, and an OverRig row sources the toolset.

It touches prefs rather than the scene, so it records the current set and
the whole set list first, restores each step on its own (trap 42), and
deletes our set only if the run created it: an animator who already has a
SkeldarAnim set finds it untouched and those gates skip themselves.

A keypress cannot be sent over the port, so the bound nameCommand's body is
run the way Maya would run it. Not run yet - it needs the animator's Maya
with the command port open.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

## Task 8: CLAUDE.md, and the whole suite green

**Files:**
- Modify: `CLAUDE.md`

**Interfaces:** none.

- [ ] **Step 1: Run the whole suite and record the number**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v`

Expected: PASS. Note the total — CLAUDE.md's "1316 tests at time of writing" line needs the new figure.

- [ ] **Step 2: Write the section**

In `CLAUDE.md`, add a section after the `install.py` one, and fix the three places that say the shelf has five buttons (the `## What is here` tree comment is not one of them; search for "five buttons"):

```markdown
## `maya_hotkeys` — the temporary hotkey map

The sixth shelf button, `Hotkeys` (2026-09-02, the animator's ask: «кнопочка
которая на время активации включала бы временную карту горячих клавишь»).
One press switches Maya to a hotkey set named `SkeldarAnim`; the next press
puts their own set back. Design:
`docs/superpowers/specs/2026-09-02-hotkey-map-design.md`, proof:
`docs/superpowers/plans/verify_hotkeys.py` (13 gates, **not run yet** — it
needs a live Maya with the command port open).

**The map's contents are the animator's, laid out in Maya's own Hotkey
Editor.** A map file, a panel of ours and a cheat sheet were all offered and
declined, so there is no editor and no map format here. What the module adds
is the switch plus **107 runTimeCommands** worth binding, in the editor's own
category tree (categories nest with a **dot** — measured, Maya ships
`Editors.Time Editor.Clip`).

**The set is created once as a copy of whatever is active** and never
rebuilt: rebuilding would keep the copy in step with the base set and
destroy every key assigned in it. So their Ctrl+Z and Q/W/E/R keep working
and only what they assign is different. **It is sticky by choice** — Maya
saves the active set itself and we do nothing at exit — which is why the
previous set is remembered in the optionVar `skeldarAnimPreviousHotkeySet`
rather than in a module variable: the session that turns the map off is
often not the one that turned it on. Ours is never an answer to "where do I
go back to" (the way out would lead back in) and a deleted memory falls back
to `Maya_Default`. State is read from `hotkeySet -q -current` at **every**
press and never cached — the animator can switch sets by hand between two
presses, the same reason `picker_window._resolution` re-asserts its binding
on every sync.

**Every command's body is a one-liner into a table in the module**
(`maya_hotkeys.run("picker.build")`, preceded by the shelf buttons' own
`sys.path` bootstrap with the path read from `__file__`). Maya SAVES a user
runTimeCommand into `userRunTimeCommands.mel` — measured: `default` comes
back `False` — which is what makes the sticky map fire after a restart
before the button is pressed, and also means a body outlives the plugin. So
the body carries no logic: a stale one still resolves through the current
table, and an unknown key reports itself. `toggle()` **registers first, in
both directions**, so a press that turns the map off also brings the rows
and the baked path into step with what is on disk; the installer registers
nothing.

**Ours are 23 rows, and each one presses a panel button.** Every action of
ours already is one — `picker_window.live_window()` hands back the live
picker and `build_rig()` is the Build button; Scene Setup's and Overshoot's
module-level callbacks read their own windows' controls — so a hotkey
inherits the status line, the refresh and the exception trap for free. With
the panel closed **there is nothing to press**: the command opens it and
says so, rather than re-deriving a character to act on. Two small public
names were added for this: `picker_window.live_window()` (`show_picker`
REPLACES the window, so a caller must be able to tell open from closed) and
`PickerWindow.select_group` (was `_select_group`; it has a second caller
now). `maya_overshoot.WINDOW` is a module constant for the same reason.

**OverRig's are 84 rows** — every one-press procedure in
`overrig/function_for_hotkeys.TXT`, with the author's own arguments and his
headings as the categories, a row per named mode (four for
`set_infinity_graphEditor`, five for `brn_apply_finger_bend_tool`). Each
sources the toolset first (`overrig.ensure_loaded()`, then `mel.eval`) —
without it a keypress in a fresh Maya answers `Cannot find procedure` in the
Script Editor, which is **trap 20 from the hotkey side** — and deliberately
**not** gated on the time-slider highlight the way our own MEL entry points
are (trap 36): `apply_range_Fast_Bake`, `selKeys_by_timerange` and
`double_oscillate_keys` are *about* that range.

**Two procedures are excluded and a gone-test names both:**
`barn_fast_bake_source_obj_and_delete_knots` and its `min_max` twin are the
only ones in the file that ignore the selection and bake-and-delete the
whole scene's knots. One mis-press away is not where they belong. The ones
needing real arguments (`execute_overlap_command`, the motion trail, the
ribbon) are registered as their windows instead.

Qt lives below four one-line `_*_module()` seams, so the module loads on a
Maya with PySide2 and a plain-Python test can hand in a fake panel. The
button finds itself on the shelf by label (a shelf button's command runs
with no widget context) and lights its background while the map is on;
not finding it skips the paint and still switches. `hotkeySet` **needs a
UI** (measured: `RuntimeError: Maya command error` in mayapy), so the set
half is fake-`cmds` tests plus the live script and nothing else.

A door left open: `hotkeySet` has `-export`/`-import` for `.mhk`, so handing
the finished map to a colleague — the one thing living in prefs costs us —
is one flag each whenever it is asked for.
```

- [ ] **Step 3: Update the installer section's button count**

In the `## install.py` section, `five buttons` becomes `six buttons` and the list gains Hotkeys:

```markdown
a shelf named
**SkeldarAnim** with six buttons — Rig Picker, UE Bridge, Scene Setup,
Overshoot, Hotkeys, and the native OverRig panel.
```

Check for others:

```bash
grep -n "five buttons\|five shelf icons\|four buttons" CLAUDE.md SkeldarAnim/README_INSTALL.txt SkeldarAnim/icons/make_icons.py
```

Fix each hit: `make_icons.py`'s docstring says "the four SkeldarAnim shelf icons" (now five), `README_INSTALL.txt` lists the buttons for a colleague, and `test_install.py` may carry the phrase in a docstring.

- [ ] **Step 4: Update the test count line**

In `## Running tests`, replace the count with the number from Step 1.

- [ ] **Step 5: Run the whole suite one last time**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v`

Expected: PASS, and the count matches what CLAUDE.md now claims.

- [ ] **Step 6: Commit**

```bash
git add CLAUDE.md SkeldarAnim/README_INSTALL.txt SkeldarAnim/icons/make_icons.py
git commit -F commit-msg.txt
```

```
docs(hotkeys): the temporary hotkey map in CLAUDE.md

What it is, why the set is a copy created once and never rebuilt, why the
memory is an optionVar, why every command body is a one-liner into the
table, and the two procedures that stay out. Plus the measured Maya facts a
fresh session would otherwise re-derive: hotkeySet needs a UI, a user
runTimeCommand is saved to prefs, categories nest with a dot, and the editor
is HotkeyPreferencesWindow.

The shelf is six buttons now, in CLAUDE.md, README_INSTALL.txt and the icon
generator's own docstring.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

## After the plan: the live run

`verify_hotkeys.py` has never been run. It needs the animator's Maya with the
command port open:

```python
import maya.cmds as cmds
if not cmds.commandPort(":7001", query=True):
    cmds.commandPort(name=":7001", sourceType="python", echoOutput=False)
```

Bridge rules that apply (CLAUDE.md's "Driving the user's live Maya" section is
the full list, and every one of them has been paid for): write the script to a
file and send `exec(open(...).read())`; the runner must pass an explicit
globals dict (trap 17); guard idempotence with an `if`, **never** a
`SystemExit` (note 8 — it kills the port for the rest of the session and only
a Maya restart brings it back); write the runner file without a BOM (note 7);
poll for the script's last line, not for the file's existence (note 9); and
`sys.path.insert(0, REPO)` plus purging our packages, which this script already
does at the top.

Gate 13 is only honest in a **fresh** Maya, where the OverRig shelf button has
not been pressed. Gates 6–8 skip themselves if a `SkeldarAnim` hotkey set
already exists, so the first run is the one that proves creation — if the
animator has already pressed the button, delete the set by hand in the Hotkey
Editor first, or accept the skips.
