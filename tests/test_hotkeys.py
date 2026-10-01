"""Tests for the hotkey map: the table's contract and the dispatcher.

`hotkeySet` needs a UI -- it raises "Maya command error" in mayapy -- so
every gate about the SET itself runs against FakeCmds here and for real in
docs/superpowers/plans/verify_hotkeys.py. What is testable without Maya is
all the policy: which rows exist, what a row's body says, which panel a key
presses, and what happens when the panel is closed.
"""

import contextlib
import io
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

# What ships: the table under skeldar_features' own flags. Kept for the
# FeatureFlags tests; every other test here reads the WHOLE table -- the
# picker's and OverRig's rows are switched off since 2026-09-07, not gone,
# and their contract (methods that exist, MEL that ends in a semicolon) is
# still worth pinning -- so the full table is installed for the run.
SHIPPED = tuple(maya_hotkeys.COMMANDS)
maya_hotkeys.COMMANDS = maya_hotkeys.commands(
    types.SimpleNamespace(PICKER=True, OVERRIG_HOTKEYS=True, OVERSHOOT=True))
maya_hotkeys._INDEX = dict((row[0], row) for row in maya_hotkeys.COMMANDS)


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
        # The timeline half: a tiny curve model. `curves` is curve -> key
        # times, `curve_types` is what objectType answers (the four
        # time-based types move, animCurveUU and friends must not), and
        # `driving` is object -> its curves, which is what
        # `keyframe -q -name` answers for a selection.
        self.time = 1.0
        self.curves = {}
        self.curve_types = {}
        self.driving = {}
        self.selected = []
        self.chunks = []
        self.namecommands = {}
        self.bindings = {}
        # The editors: `workspace` is workspaceControl name -> visible, and
        # `panels` is layout panel -> visible, because the Graph Editor is
        # the first kind and the Outliner is the second (measured).
        self.workspace = {}
        self.panels = {}

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
        if edit and delete:
            self.runtime.pop(name, None)
            return None
        row = {"command": command, "category": category, "label": label,
               "annotation": annotation}
        if edit:
            self.runtime[name] = row
            self.edits.append(name)
            return name
        self.runtime[name] = row
        self.creates.append(name)
        return name

    # -- odds and ends ---------------------------------------------------
    def optionVar(self, exists=None, query=None, stringValue=None,
                  intValue=None, remove=None):
        if exists is not None:
            return exists in self.optionvars
        if query is not None:
            return self.optionvars.get(query, "")
        for pair in (stringValue, intValue):
            if pair is not None:
                self.optionvars[pair[0]] = pair[1]
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

    # -- the editors -----------------------------------------------------
    def workspaceControl(self, name, exists=False, query=False, edit=False,
                         visible=None, close=False, **kwargs):
        if exists:
            return name in self.workspace
        if query and visible:
            return self.workspace.get(name, False)
        if edit and close:
            self.workspace.pop(name, None)
            return None
        return None

    def getPanel(self, visiblePanels=False, type=None, scriptType=None,
                 **kwargs):
        if visiblePanels:
            return [p for p, shown in sorted(self.panels.items()) if shown]
        if type or scriptType:
            return sorted(self.panels)
        return []

    # -- the timeline ----------------------------------------------------
    def currentTime(self, value=None, query=False, edit=False):
        if query:
            return self.time
        self.time = float(value)
        return self.time

    def ls(self, *args, **kwargs):
        if kwargs.get("selection"):
            return list(self.selected)
        wanted = kwargs.get("type")
        if wanted:
            wanted = (wanted,) if isinstance(wanted, str) else tuple(wanted)
            return [c for c, kind in sorted(self.curve_types.items())
                    if kind in wanted]
        return []

    def objectType(self, node):
        return self.curve_types.get(node, "transform")

    def _named(self, nodes):
        """Curve names for whatever was passed: curves, or their objects."""
        found = []
        for node in (nodes or []):
            if node in self.curves:
                found.append(node)
            else:
                found.extend(self.driving.get(node, []))
        return found

    def keyframe(self, nodes=None, query=False, edit=False, name=False,
                 relative=False, timeChange=None, time=None,
                 timeChange_query=False):
        curves = self._named(nodes)
        if query and name:
            return list(curves)
        if query:
            times = []
            for curve in curves:
                times.extend(self.curves[curve])
            return sorted(times)
        moved = 0
        low, high = time
        for curve in curves:
            keys = self.curves[curve]
            for index, key in enumerate(keys):
                if low <= key <= high:
                    keys[index] = key + timeChange
                    moved += 1
            keys.sort()
        return moved

    def cutKey(self, nodes=None, time=None, clear=False):
        low, high = time
        cut = 0
        for curve in self._named(nodes):
            keep = [k for k in self.curves[curve] if not low <= k <= high]
            cut += len(self.curves[curve]) - len(keep)
            self.curves[curve][:] = keep
        return cut

    def findKeyframe(self, nodes=None, which=None, **kwargs):
        times = []
        for curve in self._named(nodes):
            times.extend(self.curves[curve])
        if not times:
            return None
        return max(times) if which == "last" else min(times)

    def undoInfo(self, openChunk=False, closeChunk=False, **kwargs):
        if openChunk:
            self.chunks.append("open")
        if closeChunk:
            self.chunks.append("close")
        return None

    # -- name commands and bindings --------------------------------------
    def nameCommand(self, name, command=None, annotation=None,
                    sourceType=None):
        self.namecommands[name] = command
        return name

    def hotkey(self, key=None, query=False, name=None, keyShortcut=None,
               altModifier=False, ctrlModifier=False, shiftModifier=False,
               **kwargs):
        """As strict as the real command about which form takes the key.

        Maya reverses itself: READING is `hotkey("a", query=True,
        name=True)` -- with `keyShortcut=` under query it raises "must be
        passed a boolean argument" -- and WRITING is
        `hotkey(keyShortcut="a", name=...)`, which raises "Please specify a
        key" if the key comes in positionally. Both measured live, and a
        fake that accepted either form is exactly what let the wrong one
        ship: the unit tests passed and the live run failed.
        """
        if query:
            if keyShortcut is not None and not isinstance(keyShortcut, bool):
                raise RuntimeError(
                    "Flag 'keyShortcut' must be passed a boolean argument "
                    "when query flag is set")
            if key is None:
                raise RuntimeError("Please specify a key")
            return self.bindings.get((key, bool(altModifier)), "")
        if keyShortcut is None:
            raise RuntimeError("Please specify a key")
        self.bindings[(keyShortcut, bool(altModifier))] = name
        return None


class FakeMel(object):
    """Records what was evaluated, and models the one command whose EFFECT
    the module reads back: `ToggleOutliner` flips the layout's outliner,
    measured live."""

    def __init__(self, fake_cmds):
        self.cmds = fake_cmds

    def eval(self, script):
        self.cmds.evaluated.append(script)
        if script == "ToggleOutliner;":
            for panel in list(self.cmds.panels):
                if "outliner" in panel.lower():
                    self.cmds.panels[panel] = not self.cmds.panels[panel]
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
             "_overrig_module", "_retarget_module")

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
    """Scene Setup / Overshoot: a module id plus recorded calls.

    Scene Setup answers `is_open()` (it lives in the hub since 2026-09-17);
    Overshoot still has a window of its own, hence WINDOW.
    """

    WINDOW = "fakePanelWindow"

    def __init__(self, open_=False):
        self.calls = []
        self.shown = 0
        self.open = open_

    def is_open(self):
        return self.open

    def show_window(self):
        self.shown += 1

    def show_weapons(self):
        self.shown += 1
        self.calls.append(("show_weapons",))

    def show_overshoot_ui(self):
        self.shown += 1

    def apply_overshoot(self, shape):
        self.calls.append(("apply_overshoot", shape))

    def __getattr__(self, name):
        def call(*args):
            self.calls.append((name,) + args)
        return call


class TheTable(unittest.TestCase):
    """The table is the contract: no two rows alike."""

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
    """26 of ours with every flag on: four openers plus the map's own toggle,
    four timeline, two editors, six picker, three scene, one retarget, five
    overshoot. The curve overlay's four and Bake's one left 2026-09-08."""

    def _keys(self, prefix):
        return [row[0] for row in maya_hotkeys.COMMANDS
                if row[0].startswith(prefix)]

    def test_the_count(self):
        ours = [row for row in maya_hotkeys.COMMANDS
                if not row[0].startswith("overrig.")]
        #  + window.inventory (2026-09-29), + graph.overlay (2026-09-30),
        #  + window.shared (2026-09-30), + window.com (2026-10-01), + window.armor (2026-10-01)
        self.assertEqual(len(ours), 36)

    def test_the_graph_overlay_row(self):
        """Maya's Graph Editor over the viewport, see-through (2026-09-30)."""
        found = maya_hotkeys.row("graph.overlay")
        self.assertIsNotNone(found)
        self.assertEqual(found[1], "SkeldarAnim.Editors")
        self.assertEqual(found[2], "Graph Overlay")

    def test_the_timeline_rows(self):
        self.assertEqual(sorted(self._keys("time.")),
                         ["time.insert", "time.next", "time.prev",
                          "time.remove"])

    def test_the_six_openers_and_the_toggle(self):
        self.assertEqual(sorted(self._keys("window.")),
                         ["window.armor", "window.com", "window.connections",
                          "window.hotkeys", "window.hub", "window.inventory",
                          "window.overshoot", "window.picker",
                          "window.scenesetup", "window.shared",
                          "window.uebridge", "window.weapons"])

    def test_the_picker_rows(self):
        self.assertEqual(sorted(self._keys("picker.")),
                         ["picker.all", "picker.bake", "picker.build",
                          "picker.connect", "picker.fk", "picker.ik"])

    def test_the_scene_setup_rows(self):
        """Connect Arms, Disconnect Arms, Add Aim and Camera Setup left the
        panel on 2026-09-07; a row pressing a button that is not there is a
        hotkey that fails at the worst moment."""
        self.assertEqual(sorted(self._keys("scene.")),
                         ["scene.character", "scene.remove_weapon",
                          "scene.weapon"])

    def test_the_retarget_row(self):
        """One row since 2026-09-08: Retarget and Bake are one button."""
        self.assertEqual(self._keys("retarget."), ["retarget.run"])


class FeatureFlags(unittest.TestCase):
    """The shipped table follows skeldar_features (2026-09-07): the picker's
    and OverRig's rows are off, and the whole table -- what every other test
    here reads -- comes back with both flags on."""

    def _flags(self, picker, overrig, overshoot=True):
        return types.SimpleNamespace(PICKER=picker, OVERRIG_HOTKEYS=overrig,
                                     OVERSHOOT=overshoot)

    def test_the_shipped_flags_are_off(self):
        """2026-09-19: the OverRig shelf BUTTON is on; its 84 hotkey rows
        ride a flag of their own and stay off."""
        import skeldar_features
        self.assertFalse(skeldar_features.PICKER)
        self.assertFalse(skeldar_features.OVERRIG_HOTKEYS)
        self.assertFalse(skeldar_features.OVERSHOOT)
        self.assertTrue(skeldar_features.OVERRIG)

    def test_the_overrig_button_flag_does_not_register_the_rows(self):
        flags = types.SimpleNamespace(PICKER=False, OVERRIG=True,
                                      OVERRIG_HOTKEYS=False, OVERSHOOT=False)
        keys = [r[0] for r in maya_hotkeys.commands(flags)]
        self.assertFalse([k for k in keys if k.startswith("overrig.")])

    def test_the_shipped_table_has_no_picker_overrig_or_overshoot_rows(self):
        keys = [row[0] for row in SHIPPED]
        self.assertFalse([k for k in keys if k.startswith("picker.")])
        self.assertFalse([k for k in keys if k.startswith("overrig.")])
        self.assertFalse([k for k in keys if k.startswith("shoot.")])
        self.assertNotIn("window.overshoot", keys)
        self.assertIn("retarget.run", keys)
        self.assertIn("scene.weapon", keys)

    def test_the_overshoot_flag_brings_its_six_rows_back(self):
        keys = [r[0] for r in maya_hotkeys.commands(self._flags(False, False, True))]
        self.assertEqual(len([k for k in keys if k.startswith("shoot.")]), 5)
        self.assertIn("window.overshoot", keys)
        off = [r[0] for r in maya_hotkeys.commands(self._flags(False, False, False))]
        self.assertFalse([k for k in off if k.startswith("shoot.")])

    def test_the_curve_overlay_rows_are_gone(self):
        """2026-09-08: the tool left the plugin; a row pressing it would fail
        at the worst moment."""
        for key in [r[0] for r in maya_hotkeys.COMMANDS]:
            self.assertFalse(key.startswith("curve."), key)
            self.assertNotEqual(key, "window.curveview")
        self.assertFalse(hasattr(maya_hotkeys, "_curveview_module"))

    def test_each_flag_brings_its_rows_back(self):
        picker_only = [r[0] for r in maya_hotkeys.commands(self._flags(True, False))]
        self.assertEqual(len([k for k in picker_only if k.startswith("picker.")]), 6)
        self.assertFalse([k for k in picker_only if k.startswith("overrig.")])
        overrig_only = [r[0] for r in maya_hotkeys.commands(self._flags(False, True))]
        self.assertEqual(len([k for k in overrig_only if k.startswith("overrig.")]), 84)
        self.assertFalse([k for k in overrig_only if k.startswith("picker.")])

    def test_the_full_table_is_the_two_tables_prefixed(self):
        full = maya_hotkeys.commands(self._flags(True, True))
        self.assertEqual(len(full), len(maya_hotkeys._OURS) + len(maya_hotkeys._OVERRIG))
        self.assertEqual(full, maya_hotkeys.COMMANDS)

    def test_the_retarget_row_presses_the_shelf_button(self):
        saved = maya_hotkeys._retarget_module
        calls = []
        maya_hotkeys._retarget_module = lambda: types.SimpleNamespace(
            retarget_button=lambda: calls.append("retarget") or "r")
        try:
            self.assertEqual(maya_hotkeys.run("retarget.run"), "r")
        finally:
            maya_hotkeys._retarget_module = saved
        self.assertEqual(calls, ["retarget"])

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
        self.assertEqual(len(methods), 3)
        for name in methods:
            self.assertIn("def {0}(".format(name), source)

    def test_the_openers_name_importable_modules(self):
        import importlib.util
        names = [row[4].args[0] for row in maya_hotkeys.COMMANDS
                 if getattr(row[4], "func", None) is maya_hotkeys._show]
        self.assertEqual(len(names), 12)
        self.assertIn("maya_hub", names)
        self.assertIn("maya_scenesetup.armorpanel", names)
        self.assertIn("maya_com.panel", names)
        self.assertIn("maya_share", names)
        self.assertIn("maya_inventory", names)
        self.assertIn("maya_graphoverlay", names)
        self.assertIn("maya_scenesetup.connections", names)
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
        panel = FakePanelModule(open_=True)
        maya_hotkeys._scene_module = lambda: panel
        maya_hotkeys.run("scene.weapon")
        self.assertEqual(panel.calls, [("add_weapon",)])

    def test_a_closed_scene_setup_is_opened_and_reported(self):
        """A weapon hotkey opens the WEAPONS section, a character one the
        Characters section; neither presses anything on the way."""
        panel = FakePanelModule()
        maya_hotkeys._scene_module = lambda: panel
        maya_hotkeys.run("scene.weapon")
        self.assertEqual(panel.shown, 1)
        self.assertEqual(panel.calls, [("show_weapons",)])
        self.assertIn("Weapons", self.fake.messages[-1])
        panel = FakePanelModule()
        maya_hotkeys._scene_module = lambda: panel
        maya_hotkeys.run("scene.character")
        self.assertEqual(panel.shown, 1)
        self.assertEqual(panel.calls, [])
        self.assertIn("Characters", self.fake.messages[-1])

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
        # run() prints the trace to stderr on purpose -- the Script Editor
        # is where the detail belongs. Swallowed here so a passing test
        # does not spit a traceback into every suite run.
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                maya_hotkeys.run("test.explode")
        finally:
            del maya_hotkeys._INDEX["test.explode"]
        self.assertIn("boom", self.fake.messages[-1])
        self.assertIn("Explode", self.fake.messages[-1])


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
        with open(os.path.join(PLUGIN, "maya_hotkeys.py"),
                  encoding="utf-8") as handle:
            source = handle.read()
        for name in self.FORBIDDEN:
            self.assertEqual(source.count(name), 1,
                             "only the comment saying why may name " + name)


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
            r"C:\Users\Some Body\Documents\maya\scripts\SkeldarAnim")
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


class FramePlans(unittest.TestCase):
    """Pure: which keys move and by how much.

    Insert makes room after the current frame; remove takes that frame back
    out, keys and all. They are exact inverses on purpose -- press one then
    the other and the timeline is where it started.
    """

    def test_insert_shifts_everything_after_now(self):
        self.assertEqual(maya_hotkeys.insert_plan(1.0, 10.0),
                         (2.0, 10.0, 1.0))

    def test_insert_needs_something_after_now(self):
        self.assertIsNone(maya_hotkeys.insert_plan(10.0, 10.0))
        self.assertIsNone(maya_hotkeys.insert_plan(20.0, 10.0))
        self.assertIsNone(maya_hotkeys.insert_plan(1.0, None))

    def test_remove_clears_the_next_frame_and_pulls_the_rest_back(self):
        self.assertEqual(maya_hotkeys.remove_plan(1.0, 10.0),
                         (2.0, (3.0, 10.0), -1.0))

    def test_remove_with_only_one_frame_left_just_clears_it(self):
        self.assertEqual(maya_hotkeys.remove_plan(1.0, 2.0),
                         (2.0, None, -1.0))

    def test_remove_needs_something_after_now(self):
        self.assertIsNone(maya_hotkeys.remove_plan(10.0, 10.0))
        self.assertIsNone(maya_hotkeys.remove_plan(1.0, None))

    def test_the_two_are_inverses(self):
        start, end, delta = maya_hotkeys.insert_plan(1.0, 10.0)
        clear, shift, back = maya_hotkeys.remove_plan(1.0, end + delta)
        self.assertEqual(clear, start)
        self.assertEqual(shift, (start + 1.0, end + delta))
        self.assertEqual(back, -delta)


class FrameCommands(unittest.TestCase):

    def setUp(self):
        self.fake = FakeCmds()
        self.fake.time = 1.0
        self.fake.curves = {"loc_translateX": [0.0, 1.0, 2.0, 10.0],
                            "driven_translateY": [0.0, 5.0]}
        self.fake.curve_types = {"loc_translateX": "animCurveTL",
                                 "driven_translateY": "animCurveUU"}
        self.fake.driving = {"|loc": ["loc_translateX"],
                             "|driven": ["driven_translateY"]}
        use(self.fake)

    def test_step_moves_the_time(self):
        maya_hotkeys.run("time.next")
        self.assertEqual(self.fake.time, 2.0)
        maya_hotkeys.run("time.prev")
        maya_hotkeys.run("time.prev")
        self.assertEqual(self.fake.time, 0.0)

    def test_insert_makes_room_after_the_current_frame(self):
        maya_hotkeys.run("time.insert")
        self.assertEqual(self.fake.curves["loc_translateX"],
                         [0.0, 1.0, 3.0, 11.0])

    def test_remove_is_the_exact_inverse(self):
        maya_hotkeys.run("time.insert")
        maya_hotkeys.run("time.remove")
        self.assertEqual(self.fake.curves["loc_translateX"],
                         [0.0, 1.0, 2.0, 10.0])

    def test_a_driven_key_curve_is_never_touched(self):
        """`ls(type="animCurve")` answers the DRIVEN curves too, and their
        x-axis is a driver's value, not time. Measured live: the animator's
        scene holds animCurveUU right now."""
        maya_hotkeys.run("time.insert")
        self.assertEqual(self.fake.curves["driven_translateY"], [0.0, 5.0])

    def test_the_selection_narrows_it(self):
        self.fake.curves["other_translateX"] = [0.0, 4.0]
        self.fake.curve_types["other_translateX"] = "animCurveTL"
        self.fake.driving["|other"] = ["other_translateX"]
        self.fake.selected = ["|loc"]
        maya_hotkeys.run("time.insert")
        self.assertEqual(self.fake.curves["loc_translateX"],
                         [0.0, 1.0, 3.0, 11.0])
        self.assertEqual(self.fake.curves["other_translateX"], [0.0, 4.0])

    def test_no_animation_is_reported_not_raised(self):
        self.fake.curves = {}
        self.fake.curve_types = {}
        self.fake.driving = {}
        maya_hotkeys.run("time.insert")
        self.assertIn("no ", self.fake.messages[-1].lower())

    def test_nothing_after_the_current_frame_is_reported(self):
        self.fake.time = 99.0
        maya_hotkeys.run("time.insert")
        self.assertIn("99", self.fake.messages[-1])

    def test_remove_is_one_undo_step(self):
        """Two commands (clear, then shift) must undo together."""
        maya_hotkeys.run("time.remove")
        self.assertEqual(self.fake.chunks, ["open", "close"])


class TheDefaultKeys(unittest.TestCase):
    """The four keys the animator asked for, bound in OUR set only.

    Every one of them was already taken by a Maya default -- measured:
    alt+a CycleDisplayMode, alt+s HIKSetFullBodyKey, alt+4
    ImagePlaneOption, alt+5 WireframeOnShaded -- and the animator's call
    was to overwrite them. Inside our set, so their own set keeps them.
    """

    def setUp(self):
        self.fake = FakeCmds()
        use(self.fake)

    def test_every_default_key_names_a_real_row(self):
        for _key, _mods, row in maya_hotkeys.DEFAULT_KEYS:
            self.assertIsNotNone(maya_hotkeys.row(row), row)

    def test_they_are_all_alt(self):
        for _key, mods, _row in maya_hotkeys.DEFAULT_KEYS:
            self.assertEqual(mods, {"altModifier": True})

    def test_binding_creates_a_namecommand_per_row(self):
        maya_hotkeys.bind_defaults()
        for _key, _mods, row in maya_hotkeys.DEFAULT_KEYS:
            wanted = maya_hotkeys.name_command(row)
            self.assertIn(wanted, self.fake.namecommands)
            self.assertEqual(self.fake.namecommands[wanted],
                             maya_hotkeys.command_name(row))

    def test_binding_binds_the_keys_with_alt(self):
        maya_hotkeys.bind_defaults()
        self.assertEqual(
            self.fake.bindings[("a", True)],
            maya_hotkeys.name_command("time.prev"))
        self.assertEqual(
            self.fake.bindings[("-", True)],
            maya_hotkeys.name_command("time.remove"))

    def test_it_reports_what_it_displaced(self):
        self.fake.bindings[("a", True)] = "NameCom_CycleDisplayMode"
        displaced = maya_hotkeys.bind_defaults()
        self.assertEqual(displaced, [("alt+a", "NameCom_CycleDisplayMode")])

    def test_a_fresh_set_gets_them(self):
        maya_hotkeys.activate()
        self.assertEqual(
            self.fake.bindings[("a", True)],
            maya_hotkeys.name_command("time.prev"))

    def test_an_existing_set_gets_them_once(self):
        """The animator's set already exists, so "only on creation" would
        never reach it."""
        self.fake.sets.append("SkeldarAnim")
        maya_hotkeys.activate()
        self.assertIn(("a", True), self.fake.bindings)
        del self.fake.bindings[("a", True)]
        maya_hotkeys.deactivate()
        maya_hotkeys.activate()
        self.assertNotIn(("a", True), self.fake.bindings)

    def test_a_re_created_set_gets_them_again(self):
        maya_hotkeys.activate()
        maya_hotkeys.deactivate()
        self.fake.sets.remove("SkeldarAnim")
        self.fake.bindings.clear()
        maya_hotkeys.activate()
        self.assertIn(("a", True), self.fake.bindings)


class EditorToggles(unittest.TestCase):
    """Two editors, two different mechanisms -- measured, not assumed.

    The Graph Editor opens as a workspaceControl of its own
    (`graphEditor1Window`), and closing that control removes it entirely.
    The Outliner does not: in a normal layout it is a PANEL of the layout,
    so `outlinerPanel1Window` never exists and Maya's own ToggleOutliner is
    the whole mechanism.
    """

    def setUp(self):
        self.fake = FakeCmds()
        use(self.fake)

    def test_a_closed_graph_editor_is_opened_by_mayas_command(self):
        maya_hotkeys.run("editor.graph")
        self.assertEqual(self.fake.evaluated, ["GraphEditor;"])

    def test_an_open_graph_editor_is_closed(self):
        self.fake.workspace["graphEditor1Window"] = True
        maya_hotkeys.run("editor.graph")
        self.assertEqual(self.fake.evaluated, [])
        self.assertNotIn("graphEditor1Window", self.fake.workspace)

    def test_a_hidden_graph_editor_is_raised_not_closed(self):
        """Behind a tab it exists but is not visible: the animator pressing
        the key wants to SEE it, so Maya's own opener runs."""
        self.fake.workspace["graphEditor1Window"] = False
        maya_hotkeys.run("editor.graph")
        self.assertEqual(self.fake.evaluated, ["GraphEditor;"])
        self.assertIn("graphEditor1Window", self.fake.workspace)

    def test_the_graph_editor_never_sources_overrig(self):
        """`_mel` loads the rigging toolset first, and pressing alt+g has no
        business doing that."""
        asked = []

        class Loader(object):
            NOT_LOADED_MESSAGE = "not loaded"

            def ensure_loaded(self):
                asked.append(1)
                return True

        maya_hotkeys._overrig_module = lambda: Loader()
        try:
            maya_hotkeys.run("editor.graph")
        finally:
            maya_hotkeys._overrig_module = \
                maya_hotkeys.__dict__["_overrig_module"]
        self.assertEqual(asked, [])

    def test_the_outliner_goes_through_mayas_own_toggle(self):
        self.fake.panels = {"outlinerPanel1": True}
        maya_hotkeys.run("editor.outliner")
        self.assertEqual(self.fake.evaluated, ["ToggleOutliner;"])

    def test_the_outliner_reports_which_way_it_went(self):
        self.fake.panels = {"outlinerPanel1": True}
        maya_hotkeys.run("editor.outliner")
        self.assertIn("hidden", self.fake.messages[-1])
        maya_hotkeys.run("editor.outliner")
        self.assertIn("shown", self.fake.messages[-1])

    def test_an_outliner_that_is_not_in_the_layout_is_said_so(self):
        self.fake.panels = {}
        maya_hotkeys.run("editor.outliner")
        self.assertIn("layout", self.fake.messages[-1])

    def test_both_rows_are_in_the_editors_category(self):
        for key in ("editor.graph", "editor.outliner"):
            self.assertEqual(maya_hotkeys.row(key)[1], "SkeldarAnim.Editors")


class TheVersionMarker(unittest.TestCase):
    """Every change to the key tables goes out through the version, which is
    what reaches a set the animator already has -- alt+g and alt+o arrived
    that way, and so did handing the number keys back. The table itself is
    pinned by TheStarterKeysAfterTheMove."""

    def setUp(self):
        self.fake = FakeCmds()
        use(self.fake)

    def test_the_version_went_up(self):
        self.assertGreaterEqual(maya_hotkeys.DEFAULT_KEYS_VERSION, 2)

    def test_an_old_marker_gets_the_new_keys(self):
        self.fake.sets.append("SkeldarAnim")
        self.fake.optionvars[maya_hotkeys.DEFAULT_KEYS_VAR] = 1
        maya_hotkeys.activate()
        self.assertEqual(
            self.fake.bindings[("g", True)],
            maya_hotkeys.name_command("editor.graph"))

    def test_a_current_marker_is_left_alone(self):
        self.fake.sets.append("SkeldarAnim")
        self.fake.optionvars[maya_hotkeys.DEFAULT_KEYS_VAR] = \
            maya_hotkeys.DEFAULT_KEYS_VERSION
        maya_hotkeys.activate()
        self.assertEqual(self.fake.bindings, {})


class TheStarterKeysAfterTheMove(unittest.TestCase):
    """The inbetweens moved off alt+4/alt+5 onto the plus and minus keys.

    Both spellings of each are bound to the same command: Maya keeps `+`
    and `=` as SEPARATE bindings (measured -- binding alt++ leaves alt+=
    untouched), and which one a physical alt+shift+= press fires cannot be
    measured over the command port. Binding both is what makes the key work
    whichever way the animator's hand reaches it.
    """

    def setUp(self):
        self.fake = FakeCmds()
        use(self.fake)

    def test_the_table(self):
        self.assertEqual([(key, row) for key, _mods, row
                          in maya_hotkeys.DEFAULT_KEYS],
                         [("a", "time.prev"), ("s", "time.next"),
                          ("+", "time.insert"), ("=", "time.insert"),
                          ("-", "time.remove"), ("_", "time.remove"),
                          ("g", "editor.graph"), ("o", "editor.outliner"),
                          ("c", "graph.overlay")])

    def test_the_version_went_up_again(self):
        self.assertGreaterEqual(maya_hotkeys.DEFAULT_KEYS_VERSION, 6)

    def test_both_spellings_reach_the_same_command(self):
        maya_hotkeys.bind_defaults()
        insert = maya_hotkeys.name_command("time.insert")
        self.assertEqual(self.fake.bindings[("+", True)], insert)
        self.assertEqual(self.fake.bindings[("=", True)], insert)
        remove = maya_hotkeys.name_command("time.remove")
        self.assertEqual(self.fake.bindings[("-", True)], remove)
        self.assertEqual(self.fake.bindings[("_", True)], remove)

    def test_the_number_keys_are_no_longer_bound(self):
        maya_hotkeys.bind_defaults()
        self.assertNotIn(("4", True), self.fake.bindings)
        self.assertNotIn(("5", True), self.fake.bindings)


class ReleasedKeys(unittest.TestCase):
    """A key we stop using is given back -- but only if it still holds the
    command we put there. One the animator has since re-assigned is theirs.
    """

    def setUp(self):
        self.fake = FakeCmds()
        use(self.fake)

    def test_the_table_names_the_old_inbetween_keys(self):
        self.assertEqual([(key, row) for key, _mods, row
                          in maya_hotkeys.RELEASED_KEYS],
                         [("4", "time.insert"), ("5", "time.remove")])

    def test_alt_c_is_ours_again(self):
        """Given back with the Curve Overlay on 2026-09-08, taken again for
        the Graph Overlay on 2026-09-30 - the same idea, the same key; a set
        still holding the Curve Overlay's toggle there is simply rebound."""
        self.fake.bindings[("c", True)] = \
            maya_hotkeys.name_command("window.curveview")
        self.assertNotIn("alt+c", maya_hotkeys.release_keys())
        maya_hotkeys.bind_defaults()
        self.assertEqual(self.fake.bindings[("c", True)],
                         maya_hotkeys.name_command("graph.overlay"))

    def test_no_released_key_is_still_in_use(self):
        """Or we would unbind a key we had just bound."""
        current = set((key, tuple(sorted(mods)))
                      for key, mods, _row in maya_hotkeys.DEFAULT_KEYS)
        for key, mods, _row in maya_hotkeys.RELEASED_KEYS:
            self.assertNotIn((key, tuple(sorted(mods))), current, key)

    def test_our_command_is_unbound(self):
        self.fake.bindings[("4", True)] = \
            maya_hotkeys.name_command("time.insert")
        freed = maya_hotkeys.release_keys()
        self.assertEqual(freed, ["alt+4"])
        self.assertEqual(self.fake.bindings[("4", True)], "")

    def test_somebody_elses_command_is_left_alone(self):
        self.fake.bindings[("4", True)] = "NameComToggle_ImagePlaneOption"
        self.assertEqual(maya_hotkeys.release_keys(), [])
        self.assertEqual(self.fake.bindings[("4", True)],
                         "NameComToggle_ImagePlaneOption")

    def test_an_unbound_key_is_left_alone(self):
        self.assertEqual(maya_hotkeys.release_keys(), [])
        self.assertEqual(self.fake.bindings, {})

    def test_activate_releases_before_binding(self):
        self.fake.sets.append("SkeldarAnim")
        self.fake.optionvars[maya_hotkeys.DEFAULT_KEYS_VAR] = 2
        self.fake.bindings[("4", True)] = \
            maya_hotkeys.name_command("time.insert")
        message = maya_hotkeys.activate()
        self.assertEqual(self.fake.bindings[("4", True)], "")
        self.assertEqual(self.fake.bindings[("+", True)],
                         maya_hotkeys.name_command("time.insert"))
        self.assertIn("alt+4", message)
