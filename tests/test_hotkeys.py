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
    """23 of ours: four openers plus the map's own toggle, six picker,
    seven scene, five overshoot."""

    def _keys(self, prefix):
        return [row[0] for row in maya_hotkeys.COMMANDS
                if row[0].startswith(prefix)]

    def test_the_four_openers_and_the_toggle(self):
        self.assertEqual(sorted(self._keys("window.")),
                         ["window.hotkeys", "window.overshoot",
                          "window.picker", "window.scenesetup",
                          "window.uebridge"])

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
