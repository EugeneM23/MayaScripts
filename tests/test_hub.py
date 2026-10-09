"""maya_hub: one dockable panel, every tool a collapsible section.

Spec: docs/superpowers/specs/2026-09-17-skeldar-hub-design.md
"""

import contextlib
import io
import os
import sys
import types
import unittest

import maya_hub as hub

from tests.uifakes import FakeUiCmds


def _add_builder(module, builder, fails=False):
    """Give a fake tool module a builder that records that it ran (or
    raises), where it ran (the last setParent), and marks one control. One
    module may carry several builders: Scene Setup's holds Characters and
    Weapons."""
    def build_panel():
        if fails:
            raise RuntimeError("boom in " + module.__name__ + "." + builder)
        module.built.append(builder)
        parents = [c[1][0] for c in hub.cmds.calls
                   if c[0] == "setParent" and c[1]]
        module.parents.append(parents[-1] if parents else None)
        hub.cmds.text(label=builder + " panel")
        hub.hubstyle.mark(module.__name__ + "." + builder, "primary")
    setattr(module, builder, build_panel)


class FakeToolsMixin(object):
    """Every section's module replaced by a recording fake for the test.
    `self.tools[key]` is (module, builder) for that section."""

    def install_fakes(self, failing=()):
        self.saved = {}
        self.tools = {}
        fakes = {}
        pkgs = {}
        for sec in hub.SECTIONS:
            fake = fakes.get(sec.module)
            if fake is None:
                self.saved[sec.module] = sys.modules.get(sec.module)
                fake = types.ModuleType(sec.module)
                fake.built = []
                fake.parents = []
                fakes[sec.module] = fake
                sys.modules[sec.module] = fake
                if "." in sec.module:
                    #  one fake package per parent: Scene Setup's window and
                    #  connections modules share `maya_scenesetup`
                    parent, leaf = sec.module.rsplit(".", 1)
                    pkg = pkgs.get(parent)
                    if pkg is None:
                        self.saved[parent] = sys.modules.get(parent)
                        pkg = types.ModuleType(parent)
                        pkgs[parent] = pkg
                        sys.modules[parent] = pkg
                    setattr(pkg, leaf, fake)
            _add_builder(fake, sec.builder, fails=sec.key in failing)
            self.tools[sec.key] = (fake, sec.builder)

    def built(self, key):
        module, builder = self.tools[key]
        return module.built.count(builder)

    def remove_fakes(self):
        for name, module in self.saved.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module


class TheTable(unittest.TestCase):

    def test_the_sections_in_the_hub_s_order(self):
        """2026-09-28, the skin: grouped; UE Bridge on top where it always
        was (the same evening), so Animation is the first group. Weapons
        still follows Characters (its refresh writes the Characters
        header). The Graph Overlay joined Animation on 2026-09-30, Shared joined Scene the
        same day, the Center of Mass Animation on 2026-10-01, Armor Scene the same day.
        And the same evening the UE Bridge became part of Characters, the
        first card - the Scene group above Animation («Characters самой
        первой, Scene выше») - and was named Animation Setup («Раздел
        Character Заменим на Animationsetup»), its key still "characters".
        The Pose Library joined Animation on 2026-10-02, after the Center of Mass."""
        self.assertEqual([s.label for s in hub.SECTIONS],
                         ["Animation Setup", "Inventory", "Connections", "Shared",
                          "Stash", "Retarget", "Graph Overlay",
                          "Center of Mass", "Pose Library",
                          "Studio", "Colour", "Hotkeys", "Update"])

    def test_the_pose_library_card(self):
        """2026-10-02: the window is too big for an accordion, so the card is one line and Open
        Pose Library; the hub's Tabler `books`."""
        sec = hub.section("poses")
        self.assertEqual((sec.label, sec.module, sec.builder, sec.frame, sec.group, sec.icon),
                         ("Pose Library", "maya_poselib.window", "build_panel",
                          "skeldarHubFramePoses", "animation", "books"))
        keys = [s.key for s in hub.SECTIONS]
        self.assertEqual(keys.index("poses"), keys.index("com") + 1)

    def test_the_ue_bridge_is_an_alias_of_characters(self):
        """2026-10-01: no section of its own; its key opens the card it
        lives in - the hotkey row, a flagged shelf button, an older verify."""
        self.assertNotIn("uebridge", [s.key for s in hub.SECTIONS])
        self.assertEqual(hub.ALIASES, {"uebridge": "characters", "armor": "weapons"})
        self.assertIs(hub.section("uebridge"), hub.section("characters"))

    def test_armor_is_part_of_the_inventory(self):
        """2026-10-01, the evening: «объеденим вкладки weapon и армор в одну
        inventory» - the Weapons card is Inventory (key "weapons", the
        backpack), Armor no card of its own and its key an alias."""
        self.assertNotIn("armor", [s.key for s in hub.SECTIONS])
        self.assertIs(hub.section("armor"), hub.section("weapons"))
        self.assertEqual((hub.section("weapons").label, hub.section("weapons").icon),
                         ("Inventory", "backpack"))

    def test_the_groups_and_their_icons(self):
        import maya_hubicons
        groups = [(s.key, s.group) for s in hub.SECTIONS]
        self.assertEqual(groups, [
            ("characters", "scene"), ("weapons", "scene"),
            ("connections", "scene"), ("shared", "scene"),
            ("stash", "scene"),
            ("retarget", "animation"),
            ("graphoverlay", "animation"), ("com", "animation"),
            ("poses", "animation"), ("studio", "look"),
            ("colour", "look"), ("hotkeys", "settings"),
            ("update", "settings")])
        for sec in hub.SECTIONS:
            self.assertIn(sec.icon, maya_hubicons.ICONS, sec.key)
            self.assertIsNotNone(hub.hubstyle.group(sec.group), sec.key)

    def test_a_group_is_contiguous(self):
        seen = []
        for sec in hub.SECTIONS:
            if not seen or seen[-1] != sec.group:
                self.assertNotIn(sec.group, seen, sec.key)
                seen.append(sec.group)

    def test_the_cards_are_every_section_but_the_header_s(self):
        """Hotkeys is the header's keyboard; Update is a card again
        (2026-09-28, «раздел с обновлением давай вернём»)."""
        self.assertEqual([s.key for s in hub.card_sections()],
                         ["characters", "weapons", "connections", "shared",
                          "stash", "retarget", "graphoverlay", "com", "poses",
                          "studio", "colour", "update"])

    def test_every_section_names_a_real_module_and_builder(self):
        wanted = {
            "characters": ("maya_scenesetup.window", "build_characters_panel"),
            "weapons": ("maya_scenesetup.window", "build_weapons_panel"),
            "connections": ("maya_scenesetup.connections", "build_panel"),
            "shared": ("maya_share", "build_panel"),
            "stash": ("maya_stash", "build_panel"),
            "retarget": ("maya_rig_retarget", "build_panel"),
            "graphoverlay": ("maya_graphoverlay.mode", "build_panel"),
            "com": ("maya_com.panel", "build_panel"),
            "poses": ("maya_poselib.window", "build_panel"),
            "hotkeys": ("maya_hotkeys", "build_panel"),
            "studio": ("maya_vpstudio", "build_panel"),
            "colour": ("maya_colour", "build_panel"),
            "update": ("maya_update", "build_panel"),
        }
        for sec in hub.SECTIONS:
            self.assertEqual((sec.module, sec.builder), wanted[sec.key])

    def test_keys_and_frames_are_unique(self):
        keys = [s.key for s in hub.SECTIONS]
        frames = [s.frame for s in hub.SECTIONS]
        self.assertEqual(len(set(keys)), len(keys))
        self.assertEqual(len(set(frames)), len(frames))

    def test_section_lookup(self):
        self.assertEqual(hub.section("colour").label, "Colour")
        self.assertIsNone(hub.section("nonsense"))


class TheInstallerKnowsTheControl(unittest.TestCase):
    """install.py names the hub's control itself (nothing of ours is importable at drop time) to
    rebuild an open hub after an install (2026-09-28); the two names must not drift apart."""

    def test_the_installer_s_name_is_the_hub_s(self):
        import install
        self.assertEqual(install.HUB_CONTROL, hub.CONTROL)


class PendingStartup(FakeToolsMixin, unittest.TestCase):
    """Task 13b (2026-10-09): an install that had to MAKE the user's plug-ins
    folder leaves the startup plug-in unloaded (Maya's «Untrusted Plugin
    Loading» dialog otherwise - Maya trusts that folder from its next start)
    and marks it pending. The first time the hub is built or shown in a
    later session the registration is finished - deferred, silently - by the
    installer's `complete_startup`; the mark is asked here first, so a hub
    with nothing pending loads no installer at all."""

    def setUp(self):
        self.real = (hub.cmds, hub._installer)
        self.fake = FakeUiCmds()
        hub.cmds = self.fake
        self.completed = []
        self.note = ""

        def complete_startup():
            self.completed.append(True)
            return self.note
        self.installer = types.SimpleNamespace(complete_startup=complete_startup)
        hub._installer = lambda: self.installer
        hub._STARTUP_QUEUED = False
        self.install_fakes()

    def tearDown(self):
        hub.cmds, hub._installer = self.real
        hub._STARTUP_QUEUED = False
        self.remove_fakes()

    def pending(self):
        self.fake.optionvars[hub.STARTUP_PENDING_VAR] = 1

    def test_the_name_is_the_installer_s(self):
        import install
        self.assertEqual(hub.STARTUP_PENDING_VAR, install.STARTUP_PENDING)

    def test_nothing_pending_nothing_queued(self):
        hub.show()
        hub.build()
        self.assertEqual(self.fake.deferred, [])
        self.assertEqual(self.completed, [])

    def test_a_mark_of_zero_is_nothing_pending(self):
        self.fake.optionvars[hub.STARTUP_PENDING_VAR] = 0
        hub.show()
        self.assertEqual(self.fake.deferred, [])

    def test_show_finishes_it_deferred(self):
        self.pending()
        hub.show()
        self.assertEqual(self.completed, [])            # never inside show()
        self.fake.run_deferred()
        self.assertEqual(self.completed, [True])

    def test_build_finishes_it_too(self):
        """The uiScript: a docked hub Maya restored at the start."""
        self.pending()
        hub.build()
        self.assertEqual(self.completed, [])
        self.fake.run_deferred()
        self.assertEqual(self.completed, [True])

    def test_show_and_its_build_queue_it_once(self):
        """show() creating the control runs the uiScript's build() in the
        same turn: one completion queued, not two."""
        self.pending()
        hub.show()
        hub.build()
        self.fake.run_deferred()
        self.assertEqual(self.completed, [True])

    def test_a_failure_is_one_printed_line_and_tried_again_next_time(self):
        self.pending()
        self.note = "startup plug-in not registered: load refused"
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            hub.show()
            self.fake.run_deferred()
        lines = [line for line in out.getvalue().splitlines() if line]
        self.assertEqual(len(lines), 1)
        self.assertIn("load refused", lines[0])
        hub.show()                                      # the mark still 1
        self.fake.run_deferred()
        self.assertEqual(self.completed, [True, True])

    def test_success_prints_nothing(self):
        self.pending()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            hub.show()
            self.fake.run_deferred()
        self.assertEqual(out.getvalue(), "")

    def test_an_installer_that_raises_is_printed_never_raised(self):
        self.pending()

        def broken():
            raise ImportError("no install.py here")
        hub._installer = broken
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            hub.show()
            self.fake.run_deferred()
        self.assertIn("no install.py here", out.getvalue())
        self.assertEqual(len(out.getvalue().strip().splitlines()), 1)

    def test_the_installer_is_this_folder_s_install_py(self):
        """Loaded by path under a name of its own (the Update card's and the
        one-file installer's way): `import install` could find somebody
        else's install.py on sys.path, or a stale module."""
        before = set(sys.modules)
        module = self.real[1]()
        self.assertTrue(callable(module.complete_startup))
        self.assertEqual(
            os.path.normcase(os.path.abspath(module.__file__)),
            os.path.normcase(os.path.join(hub.plugin_root(), "install.py")))
        self.assertEqual(set(sys.modules) - before, set())


class TheUiScript(unittest.TestCase):
    """Maya replays it at startup, before any shelf button ran."""

    def test_it_bootstraps_imports_and_builds(self):
        script = hub.uiscript("C:/Users/Some Body/scripts/SkeldarAnim")
        self.assertIn('_p = "C:/Users/Some Body/scripts/SkeldarAnim"',
                      script)
        self.assertIn("sys.path.insert(0, _p)", script)
        self.assertIn("import maya_hub", script)
        self.assertIn("maya_hub.build()", script)

    def test_backslashes_never_reach_the_workspace_file(self):
        script = hub.uiscript("C:\\Users\\Some Body\\scripts\\SkeldarAnim\\")
        self.assertNotIn("\\", script)
        self.assertIn('"C:/Users/Some Body/scripts/SkeldarAnim"', script)


class ScrollOffset(unittest.TestCase):

    def test_the_first_section_is_at_the_top(self):
        self.assertEqual(hub.scroll_offset([300, 400, 80], 0, 4), 0)

    def test_the_sections_above_and_their_gaps(self):
        self.assertEqual(hub.scroll_offset([300, 400, 80], 2, 4),
                         300 + 400 + 2 * 4)

    def test_a_collapsed_section_counts_its_real_height(self):
        """Maya answers the header's height for a collapsed frame; the
        function sums what it is handed and assumes nothing."""
        self.assertEqual(hub.scroll_offset([24, 24, 600], 2, 0), 48)


class Build(FakeToolsMixin, unittest.TestCase):

    def setUp(self):
        self.real = hub.cmds
        self.fake = FakeUiCmds()
        hub.cmds = self.fake
        self.install_fakes()

    def tearDown(self):
        hub.cmds = self.real
        self.remove_fakes()

    def test_one_collapsable_frame_per_section_in_order(self):
        hub.build()
        frames = [c for c in self.fake.children if c in self.fake.frames]
        self.assertEqual(frames, [s.frame for s in hub.SECTIONS])
        for frame in frames:
            self.assertTrue(self.fake.frames[frame].get("collapsable"))

    def test_every_builder_runs_once(self):
        hub.build()
        for key in self.tools:
            self.assertEqual(self.built(key), 1, key)

    def test_sections_open_by_default(self):
        hub.build()
        for sec in hub.SECTIONS:
            self.assertFalse(self.fake.frames[sec.frame]["collapse"])

    def test_a_remembered_collapse_is_restored(self):
        self.fake.optionvars[hub.OPTIONVAR.format("characters")] = 1
        hub.build()
        self.assertTrue(self.fake.frames["skeldarHubFrameCharacters"]["collapse"])
        self.assertFalse(self.fake.frames["skeldarHubFrameColour"]["collapse"])

    def test_collapsing_and_expanding_write_the_memory(self):
        hub.build()
        frame = self.fake.frames["skeldarHubFrameStudio"]
        frame["collapseCommand"]()
        self.assertEqual(self.fake.optionvars[hub.OPTIONVAR.format("studio")],
                         1)
        frame["expandCommand"]()
        self.assertEqual(self.fake.optionvars[hub.OPTIONVAR.format("studio")],
                         0)

    def test_the_column_scrolls_and_stretches(self):
        hub.build()
        scroll = [c for c in self.fake.calls if c[0] == "scrollLayout"]
        self.assertTrue(scroll[0][2].get("childResizable"))
        self.assertTrue(self.fake.column.get("adjustableColumn"))

    def test_the_hub_never_opens_a_window_of_its_own(self):
        hub.build()
        self.assertEqual(self.fake.windows, {})


class BuildWithABrokenTool(FakeToolsMixin, unittest.TestCase):

    def setUp(self):
        self.real = hub.cmds
        self.fake = FakeUiCmds()
        hub.cmds = self.fake
        self.install_fakes(failing=("characters",))

    def tearDown(self):
        hub.cmds = self.real
        self.remove_fakes()

    def test_the_other_sections_are_still_built(self):
        """Weapons shares Characters' module and must still build."""
        hub.build()
        self.assertEqual(self.built("characters"), 0)
        for key in ("weapons", "connections", "retarget",
                    "hotkeys", "studio", "colour"):
            self.assertEqual(self.built(key), 1, key)

    def test_the_broken_section_says_so(self):
        hub.build()
        texts = [c[2].get("label", "") for c in self.fake.calls
                 if c[0] == "text"]
        self.assertTrue(any("Animation Setup could not be built" in t
                            and "boom" in t for t in texts))


class Show(FakeToolsMixin, unittest.TestCase):

    def setUp(self):
        self.real = hub.cmds
        self.fake = FakeUiCmds()
        hub.cmds = self.fake
        self.install_fakes()

    def tearDown(self):
        hub.cmds = self.real
        self.remove_fakes()

    def test_a_missing_control_is_created_with_the_uiscript(self):
        hub.show()
        created = self.fake.workspace[hub.CONTROL]
        self.assertEqual(created["label"], "SkeldarAnim")
        self.assertIn("maya_hub.build()", created["uiScript"])
        self.assertIn(hub.plugin_root().replace("\\", "/"),
                      created["uiScript"])
        self.assertFalse(created["retain"])

    def test_an_existing_control_is_restored_not_rebuilt(self):
        self.fake.workspace[hub.CONTROL] = {"label": "SkeldarAnim"}
        hub.build()                                   # this module object built what stands
        del self.fake.deleted[:]
        hub.show()
        edits = self.fake.workspace[hub.CONTROL]["edits"]
        self.assertTrue(any(e.get("restore") for e in edits))
        self.assertNotIn("uiScript", self.fake.workspace[hub.CONTROL])
        self.assertNotIn(hub.SCROLL, self.fake.deleted)
        self.assertEqual(self.built("characters"), 1)

    def test_a_control_an_older_copy_built_is_rebuilt_in_place(self):
        """2026-09-24: an update purges the plugin's modules while the hub
        stays open, and a restore alone kept showing the OLD build -- the
        character dropdown without the Creep row the update had added
        («НЕ вижу хантера в списке персонажей»). A module object that did not
        build the standing accordion rebuilds it inside the same control, so
        where it is docked survives."""
        self.fake.workspace[hub.CONTROL] = {"label": "SkeldarAnim"}
        self.fake.existing.add(hub.SCROLL)
        hub._BUILT_HERE = False
        hub.show()
        self.assertIn(hub.SCROLL, self.fake.deleted)
        self.assertEqual(self.built("characters"), 1)
        self.assertNotIn("uiScript", self.fake.workspace[hub.CONTROL])
        self.assertTrue(any(e.get("restore") for e in self.fake.workspace[hub.CONTROL]["edits"]))
        hub.show()                                    # built here now: no second rebuild
        self.assertEqual(self.built("characters"), 1)

    def test_legacy_standalone_windows_are_closed(self):
        self.fake.windows["skeldarColourWin"] = {}
        self.fake.windows["mayaSceneSetupWindow"] = {}
        hub.show()
        self.assertIn("skeldarColourWin", self.fake.deleted)
        self.assertIn("mayaSceneSetupWindow", self.fake.deleted)

    def test_show_with_a_key_expands_that_section_only(self):
        self.fake.optionvars[hub.OPTIONVAR.format("colour")] = 1
        self.fake.optionvars[hub.OPTIONVAR.format("studio")] = 1
        hub.build()
        hub.show("colour")
        self.assertFalse(self.fake.frames["skeldarHubFrameColour"]["collapse"])
        self.assertTrue(self.fake.frames["skeldarHubFrameStudio"]["collapse"])
        self.assertEqual(self.fake.optionvars[hub.OPTIONVAR.format("colour")],
                         0)

    def test_expanding_scrolls_the_section_into_view_deferred(self):
        hub.build()
        hub.show("studio")
        self.assertEqual(len(self.fake.deferred), 1)
        self.fake.run_deferred()
        scrolls = [c[2]["scrollByPixel"] for c in self.fake.calls
                   if c[0] == "scrollLayout" and "scrollByPixel" in c[2]]
        index = [s.key for s in hub.SECTIONS].index("studio")
        expected = hub.scroll_offset([self.fake.control_height] * len(hub.SECTIONS), index,
                                     hub.ROW_SPACING)
        self.assertEqual(scrolls[0][0], "up")
        self.assertEqual(scrolls[1], ("down", expected))

    def test_the_ue_bridge_key_opens_the_characters_card(self):
        self.fake.optionvars[hub.OPTIONVAR.format("characters")] = 1
        hub.build()
        hub.show("uebridge")
        self.assertFalse(self.fake.frames["skeldarHubFrameCharacters"]["collapse"])
        self.assertEqual(self.fake.optionvars[hub.OPTIONVAR.format("characters")], 0)
        self.assertNotIn(hub.OPTIONVAR.format("uebridge"), self.fake.optionvars)

    def test_an_unknown_key_is_an_error(self):
        with self.assertRaises(KeyError):
            hub.expand("nonsense")

    def test_scroll_to_without_the_layout_is_quiet(self):
        self.assertIsNone(hub.scroll_to("colour"))


# ------------------------------------------------------------------ the skin

class FakeCard(object):

    def __init__(self, key, collapsed):
        self.key = key
        self._collapsed = collapsed
        self.animated = []                  # what set_collapsed was asked

    def body_path(self):
        return "body|" + self.key

    def set_collapsed(self, value, animate=False):
        self.animated.append((value, animate))
        self._collapsed = value

    def collapsed(self):
        return self._collapsed


class FakeSkin(object):

    fail_finish = False

    def __init__(self, layout, scale=1.0, callbacks=None):
        self.layout = layout
        self.host = layout                  # maya_hubqt.Skin keeps its host
        self.scale = scale
        self.callbacks = callbacks
        self.edge_mode = None               # set_edge_mode (the edge panel)
        self.edge_painted = []              # paint_edge, as asked
        self.pins = []                      # paint_pin, as asked
        self.cards = {}
        self.jumps = []
        self.groups = []
        self.order = []
        self.said = []
        self.painted = []
        self.sounds = None
        self.animations = None
        self.scrolled = []
        self.sheet = None
        self._alive = True

    def add_jump(self, key, label, icon, colour):
        self.jumps.append(key)

    def add_group(self, key, label):
        self.groups.append(key)
        self.order.append(("group", key))

    def add_card(self, key, label, icon, colour, chip, collapsed=False):
        card = FakeCard(key, collapsed)
        self.cards[key] = card
        self.order.append(("card", key))
        return card

    def finish(self, sheet):
        if FakeSkin.fail_finish:
            raise RuntimeError("the skin broke")
        self.sheet = sheet

    def say(self, text, state=None):
        self.said.append((text, state))

    def paint_hotkeys(self, active):
        self.painted.append(active)

    def paint_sounds(self, on):
        self.sounds = on

    def paint_animations(self, on):
        self.animations = on

    def set_version(self, text, tooltip, state=None):
        pass

    def set_state(self, state):
        self.state = state

    def scroll_to(self, key, animate=False):
        self.scrolled.append((key, animate))
        return 42 if key in self.cards else None

    def set_active(self, key):
        self.active = key

    def set_edge_mode(self, on, side="left"):
        self.edge_mode = bool(on)
        self.edge_side = side
        self.edge_painted.append((bool(on), side))

    def paint_edge(self, on, side="left"):
        self.edge_painted.append((bool(on), side))

    def paint_pin(self, on):
        self.pins.append(bool(on))

    def alive(self):
        return self._alive

    def destroy(self):
        self._alive = False


def _fake_qt(available=True):
    module = types.ModuleType("maya_hubqt_fake")
    module.available = lambda: available
    module.host_widget = lambda control: "widget of " + control
    module.destroyed = []
    module.destroy_roots = lambda control: module.destroyed.append(control)
    #  the roots in a given host (the edge panel's slot)
    module.destroyed_in = []
    module.destroy_roots_in = lambda host: module.destroyed_in.append(host)
    module.Skin = FakeSkin
    module.applied = []
    module.apply_marks = lambda marks, card, scale: module.applied.append(
        (card.key, [m.name for m in marks]))
    return module


class Skinned(FakeToolsMixin, unittest.TestCase):

    def setUp(self):
        self.real = (hub.cmds, hub._hubqt, hub._dress_header)
        self.fake = FakeUiCmds(dpi=1.5)
        hub.cmds = self.fake
        self.qt = _fake_qt()
        hub._hubqt = lambda: self.qt
        hub._dress_header = lambda skin: None
        FakeSkin.fail_finish = False
        self.install_fakes()

    def tearDown(self):
        hub.cmds, hub._hubqt, hub._dress_header = self.real
        FakeSkin.fail_finish = False
        hub._SKIN = None
        self.remove_fakes()

    def test_skinned_when_qt_is_there(self):
        self.assertTrue(hub.skinned())
        hub.build()
        self.assertTrue(hub.is_skinned())
        self.assertEqual(hub._SKIN.layout, "widget of " + hub.CONTROL)
        self.assertEqual(hub._SKIN.scale, 1.5)

    def test_an_older_skin_in_the_control_goes_first(self):
        """After an install the fresh module does not know the old skin:
        the roots are found in the control by name and deleted."""
        hub.build()
        self.assertEqual(self.qt.destroyed, [hub.CONTROL])

    def test_cards_in_group_order_and_no_frames(self):
        """2026-10-08 (the compact hub): the cards stand in their groups'
        order with no label between them - a card's group is its stripe."""
        hub.build()
        self.assertEqual(hub._SKIN.order, [
            ("card", "characters"), ("card", "weapons"),
            ("card", "connections"), ("card", "shared"), ("card", "stash"),
            ("card", "retarget"), ("card", "graphoverlay"), ("card", "com"),
            ("card", "poses"), ("card", "studio"), ("card", "colour"),
            ("card", "update")])
        self.assertEqual(self.fake.frames, {})
        self.assertEqual(hub._SKIN.jumps, [s.key for s in hub.card_sections()])

    def test_the_skin_has_no_group_labels(self):
        """The compact skin shows a card's group as a coloured stripe, so
        `_build_skin` never asks for a group label (Skin.add_group stays an
        API)."""
        hub.build()
        self.assertFalse([entry for entry in hub._SKIN.order
                          if entry[0] == "group"])
        self.assertEqual(hub._SKIN.groups, [])

    def test_every_card_builder_runs_once_into_its_body(self):
        hub.build()
        for sec in hub.card_sections():
            self.assertEqual(self.built(sec.key), 1, sec.key)
            module, builder = self.tools[sec.key]
            index = module.built.index(builder)
            self.assertEqual(module.parents[index], "body|" + sec.key)

    def test_the_builders_know_they_build_the_skin(self):
        seen = []
        module, builder = self.tools["colour"]
        real = getattr(module, builder)

        def build_panel():
            seen.append(hub.hubstyle.skinning())
            real()
        setattr(module, builder, build_panel)
        hub.build()
        self.assertEqual(seen, [True])
        self.assertFalse(hub.hubstyle.skinning())            # and after

    def test_the_hotkeys_are_the_header_s_and_update_a_card(self):
        hub.build()
        self.assertEqual(self.built("hotkeys"), 0)
        self.assertNotIn("hotkeys", hub._SKIN.cards)
        self.assertEqual(self.built("update"), 1)
        self.assertIn("update", hub._SKIN.cards)

    def test_each_card_gets_its_own_marks(self):
        hub.build()
        applied = dict(self.qt.applied)
        self.assertEqual(applied["characters"],
                         ["maya_scenesetup.window.build_characters_panel"])
        self.assertEqual(applied["colour"], ["maya_colour.build_panel"])

    def test_the_stylesheet_is_set_at_the_display_scale(self):
        hub.build()
        self.assertEqual(hub._SKIN.sheet, hub.hubstyle.stylesheet(1.5))

    def test_remembered_collapse_reaches_the_card(self):
        self.fake.optionvars[hub.OPTIONVAR.format("studio")] = 1
        hub.build()
        self.assertTrue(hub._SKIN.cards["studio"].collapsed())
        self.assertFalse(hub._SKIN.cards["colour"].collapsed())

    def test_the_callbacks_remember_and_jump(self):
        hub.build()
        callbacks = hub._SKIN.callbacks
        callbacks["toggled"]("colour", True)
        self.assertEqual(self.fake.optionvars[hub.OPTIONVAR.format("colour")],
                         1)
        hub._SKIN.cards["colour"].set_collapsed(True)
        callbacks["jump"]("colour")
        self.assertFalse(hub._SKIN.cards["colour"].collapsed())

    def _fake_sound(self):
        """maya_hubsound on the fake cmds, its player recording the file."""
        import maya_hubsound as hubsound
        saved = (hubsound._cmds, hubsound.make_player)
        played = []

        class Player(object):
            def __init__(self, path):
                self.path = path

            def play(self):
                played.append(self.path)

        hubsound._cmds = lambda: self.fake
        hubsound.make_player = Player
        hubsound.reset()

        def restore():
            hubsound._cmds, hubsound.make_player = saved
            hubsound.reset()
        self.addCleanup(restore)
        return hubsound, played

    def test_the_callbacks_play_and_switch_the_sounds(self):
        """2026-10-01: «приятный и простой звук наводки на кнопочку», and
        the menu's Interface sounds."""
        hubsound, played = self._fake_sound()
        self.fake.optionvars[hubsound.OPTIONVAR] = 1         # switched on
        hub.build()
        callbacks = hub._SKIN.callbacks
        self.assertTrue(callbacks["hover"]())
        self.assertEqual(played, [hubsound.sound_path("hover")])
        self.assertFalse(callbacks["sounds"](False))
        self.assertEqual(self.fake.optionvars[hubsound.OPTIONVAR], 0)
        self.assertIs(hub._SKIN.sounds, False)
        self.assertFalse(callbacks["hover"]())
        self.assertEqual(len(played), 1)

    def test_the_skin_shows_the_switch_and_loads_the_sound(self):
        """Off by default (2026-10-01: «Отключи воспроизведение звуков по
        умолчанию»): the row unchecked and no audio opened; switched on, the
        row checked and the sound loaded before the first hover."""
        hubsound, played = self._fake_sound()
        skin = FakeSkin(None)
        hub._dress_sounds(skin)
        self.assertIs(skin.sounds, False)
        self.assertNotIn("hover", hubsound._state()["players"])
        self.fake.optionvars[hubsound.OPTIONVAR] = 1
        hubsound.reset()
        hub._dress_sounds(skin)
        self.assertIs(skin.sounds, True)
        self.assertIn("hover", hubsound._state()["players"])   # preloaded
        self.assertEqual(played, [])

    def test_a_jump_opens_that_card_only(self):
        """2026-09-28: «при нажатии на верхнюю панель с разделами все другие
        панели должны закрыться и открыться только нужная»."""
        hub.build()
        hub._SKIN.callbacks["jump"]("studio")
        for key, card in hub._SKIN.cards.items():
            self.assertEqual(card.collapsed(), key != "studio", key)
            self.assertEqual(
                self.fake.optionvars[hub.OPTIONVAR.format(key)],
                int(key != "studio"), key)
        self.assertEqual(hub._SKIN.active, "studio")
        self.fake.run_deferred()                            # and scrolled

    def test_a_jump_slides_the_cards_and_glides(self):
        """2026-10-01: «открывать закрывать с какими-то анимациями» - every
        card a jump changes is asked to slide, the scroll to glide."""
        hub.build()
        hub._SKIN.callbacks["jump"]("studio")
        for key, card in hub._SKIN.cards.items():
            if card.animated:
                self.assertEqual(card.animated[-1],
                                 (key != "studio", True), key)
        self.assertEqual(hub._SKIN.cards["studio"].animated[-1],
                         (False, True))
        self.fake.run_deferred()
        self.assertEqual(hub._SKIN.scrolled, [("studio", True)])

    def test_a_scroll_by_code_does_not_glide(self):
        hub.build()
        hub.scroll_to("studio")
        self.assertEqual(hub._SKIN.scrolled, [("studio", False)])

    def test_the_menu_row_switches_the_animations(self):
        import maya_hubmotion
        saved = maya_hubmotion._cmds
        maya_hubmotion._cmds = lambda: self.fake
        self.addCleanup(setattr, maya_hubmotion, "_cmds", saved)
        hub.build()
        self.assertFalse(hub._SKIN.callbacks["animations"](False))
        self.assertEqual(self.fake.optionvars[maya_hubmotion.OPTIONVAR], 0)
        self.assertIs(hub._SKIN.animations, False)
        skin = FakeSkin(None)
        hub._dress_animations(skin)                    # read back at a build
        self.assertIs(skin.animations, False)
        self.assertTrue(hub.set_animations(True))
        self.assertIs(hub._SKIN.animations, True)

    def test_a_header_click_still_opens_one_card_alone(self):
        """Only a header jump closes the others; a card's own header toggles
        that card."""
        hub.build()
        hub._SKIN.callbacks["toggled"]("colour", True)
        self.assertFalse(hub._SKIN.cards["studio"].collapsed())

    def test_the_menu_check_update_opens_the_update_card_then_checks(self):
        """2026-10-08: the version chip is gone (the update jump just
        focuses its card); the menu's Check update is what opens the card
        and runs the check."""
        pressed = []
        #  maya_update is the recording fake here (install_fakes)
        self.tools["update"][0]._press = lambda *a: pressed.append(True)
        hub.build()
        hub._SKIN.cards["update"].set_collapsed(True)
        hub._SKIN.callbacks["check_update"]()
        self.assertFalse(hub._SKIN.cards["update"].collapsed())
        self.assertEqual(pressed, [True])

    def test_the_skin_has_no_version_chip_callback(self):
        """The compact header has no chip to press (Task 2 removed it)."""
        hub.build()
        self.assertNotIn("version", hub._SKIN.callbacks)

    def test_told_is_a_quiet_callback(self):
        """A card's status reached the message line: with no edge panel
        standing the hub has nothing to add (never an error)."""
        hub.build()
        callbacks = hub._SKIN.callbacks
        self.assertIn("told", callbacks)
        self.assertIsNone(callbacks["told"]("characters", "Added", True))
        self.assertIsNone(callbacks["told"]("characters", "", False))

    def test_chip_state_colours_the_chip(self):
        hub.build()
        hub.chip_state("ok")
        self.assertEqual(hub._SKIN.state, "ok")

    def test_a_broken_skin_falls_back_to_the_classic_hub(self):
        FakeSkin.fail_finish = True
        hub.build()
        self.assertFalse(hub.is_skinned())
        self.assertEqual([c for c in self.fake.children
                          if c in self.fake.frames],
                         [s.frame for s in hub.SECTIONS])
        self.assertEqual(self.built("characters"), 2)       # skin, then classic
        self.assertEqual(self.built("hotkeys"), 1)

    def test_classic_when_asked(self):
        self.fake.optionvars[hub.CLASSIC_VAR] = 1
        self.assertFalse(hub.skinned())
        hub.build()
        self.assertFalse(hub.is_skinned())
        self.assertIn("skeldarHubFrameCharacters", self.fake.frames)

    def test_the_classic_hub_offers_the_way_back(self):
        self.fake.optionvars[hub.CLASSIC_VAR] = 1
        hub.build()
        buttons = [c for c in self.fake.calls if c[0] == "button"
                   and c[1] == (hub.NEW_LOOK_BUTTON,)]
        self.assertEqual(len(buttons), 1)
        buttons[0][2]["command"]()
        self.assertEqual(self.fake.optionvars[hub.CLASSIC_VAR], 0)
        self.assertEqual(len(self.fake.deferred), 1)

    def test_set_classic_defers_the_rebuild(self):
        hub.build()
        hub.set_classic(True)
        self.assertEqual(self.fake.optionvars[hub.CLASSIC_VAR], 1)
        skin = hub._SKIN
        self.assertTrue(skin.alive())                     # not yet
        self.fake.run_deferred()
        self.assertFalse(skin.alive())
        self.assertFalse(hub.is_skinned())
        self.assertIn("skeldarHubFrameColour", self.fake.frames)

    def test_expand_opens_the_card_and_scrolls_deferred(self):
        self.fake.optionvars[hub.OPTIONVAR.format("studio")] = 1
        hub.build()
        hub.show("studio")
        self.assertFalse(hub._SKIN.cards["studio"].collapsed())
        self.assertEqual(self.fake.optionvars[hub.OPTIONVAR.format("studio")],
                         0)
        self.assertEqual(len(self.fake.deferred), 1)
        self.fake.run_deferred()
        self.assertEqual(hub.scroll_to("studio"), 42)
        self.assertEqual(hub._SKIN.active, "studio")       # and lit

    def test_the_ue_bridge_key_opens_and_lights_the_characters_card(self):
        self.fake.optionvars[hub.OPTIONVAR.format("characters")] = 1
        hub.build()
        hub.show("uebridge")
        self.assertFalse(hub._SKIN.cards["characters"].collapsed())
        self.assertEqual(hub._SKIN.active, "characters")
        hub.focus("uebridge")
        self.assertEqual(hub._SKIN.active, "characters")
        self.assertTrue(hub._SKIN.cards["studio"].collapsed())

    def test_expanding_a_header_section_is_quiet(self):
        """maya_hotkeys.show_window still asks for its key; in the skin the
        hotkeys are the header."""
        hub.build()
        self.assertIsNone(hub.expand("hotkeys"))
        self.assertIsNotNone(hub.expand("update"))

    def test_say_and_paint_reach_the_skin(self):
        hub.build()
        hub.say("Up to date: 601eaae", state="ok")
        hub.paint_hotkeys(True)
        self.assertEqual(hub._SKIN.said, [("Up to date: 601eaae", "ok")])
        self.assertEqual(hub._SKIN.painted, [True])

    def test_say_and_paint_are_quiet_without_a_skin(self):
        self.assertEqual(hub.say("hello"), "hello")
        self.assertFalse(hub.paint_hotkeys(False))

    def test_leaving_the_classic_hub_keeps_the_collapse_memory(self):
        """Deleting classic frames runs their collapseCommand (measured):
        the memory from before the delete is what the skin opens with."""
        self.fake.optionvars[hub.CLASSIC_VAR] = 1
        hub.build()
        self.fake.optionvars[hub.OPTIONVAR.format("colour")] = 0
        self.fake.existing.add(hub.SCROLL)
        real_delete = self.fake.deleteUI

        def delete(name, **kwargs):
            for sec in hub.SECTIONS:                   # what Maya does
                self.fake.frames[sec.frame]["collapseCommand"]()
            return real_delete(name, **kwargs)
        self.fake.deleteUI = delete
        self.fake.optionvars[hub.CLASSIC_VAR] = 0
        hub.rebuild()
        self.assertTrue(hub.is_skinned())
        self.assertFalse(hub._SKIN.cards["colour"].collapsed())
        self.assertEqual(self.fake.optionvars[hub.OPTIONVAR.format("colour")],
                         0)

    def test_rebuild_destroys_the_skin_first(self):
        hub.build()
        first = hub._SKIN
        hub.rebuild()
        self.assertFalse(first.alive())
        self.assertTrue(hub._SKIN.alive())
        self.assertIsNot(hub._SKIN, first)


# ----------------------------------------------------------- the edge panel

class FakeEdge(object):
    """maya_hubedge.Edge as maya_hub drives it: what was asked of it."""

    def __init__(self, scale=1.0, parent=None, width=360, motion=None,
                 on_width=None, side="left", **_seams):
        self.scale, self.width, self.on_width = scale, width, on_width
        self.side = side
        self.sides = []                     # set_side(side) as asked
        self.slot = object()                # the skin's host, one per edge
        self.shown = False
        self.pinned = False
        self.reveals = []                   # reveal(hold) as asked
        self.concealed = 0
        self.destroyed = False

    @property
    def revealed_with_hold(self):
        return True in self.reveals

    def reveal(self, hold=False):
        self.reveals.append(bool(hold))
        self.shown = True

    def conceal(self):
        self.concealed += 1
        self.shown = False

    def set_pinned(self, on):
        self.pinned = bool(on)

    def set_side(self, side):
        self.sides.append(side)
        if side == self.side:
            return False
        self.side = side
        self.shown = False
        return True

    def alive(self):
        return not self.destroyed

    def destroy(self):
        self.destroyed = True
        self.shown = False


def _fake_hubedge(edges):
    """A maya_hubedge whose Edge records every panel made into `edges`; its
    state() is the module's own dict (the real one lives on `sys`)."""
    module = types.ModuleType("maya_hubedge_fake")
    st = {"edge": None}
    module.state = lambda: st

    def make(*args, **kwargs):
        edge = FakeEdge(*args, **kwargs)
        edges.append(edge)
        return edge
    module.Edge = make

    def destroy_all():
        """Every host found by name and deleted, an older module's too."""
        count = 0
        for edge in edges:
            if not edge.destroyed:
                edge.destroyed = True
                count += 1
        if st["edge"] is not None and not st["edge"].alive():
            st["edge"] = None
        return count
    module.destroy_all = destroy_all
    return module


class EdgeMode(FakeToolsMixin, unittest.TestCase):
    """2026-10-08 (the animator: «когда я подношу мышку к левому краю экрана
    то появляется наша полка когда убираю то полка скрывается»): ⋮ -> Edge
    panel puts the skinned hub into maya_hubedge's panel instead of the
    dock; `show(key)` reveals it and holds it; a status while it is hidden
    is Maya's viewport message too."""

    def setUp(self):
        self.real = (hub.cmds, hub._hubqt, hub._dress_header, hub._hubedge)
        self.fake = FakeUiCmds(dpi=1.5)
        hub.cmds = self.fake
        self.qt = _fake_qt()
        hub._hubqt = lambda: self.qt
        hub._dress_header = lambda skin: None
        self.edges = []
        self.he = _fake_hubedge(self.edges)
        hub._hubedge = lambda: self.he
        FakeSkin.fail_finish = False
        hub._SKIN = None
        hub._EDGE_FAILED = False
        hub._EDGE_FAILURE = ""
        self.install_fakes()

    def tearDown(self):
        hub.cmds, hub._hubqt, hub._dress_header, hub._hubedge = self.real
        FakeSkin.fail_finish = False
        hub._SKIN = None
        hub._EDGE_FAILED = False
        hub._EDGE_FAILURE = ""
        self.remove_fakes()

    def viewport_messages(self):
        return [c for c in self.fake.calls if c[0] == "inViewMessage"]

    # --------------------------------------------------- the switch

    def test_edge_mode_is_off_by_default(self):
        self.assertFalse(hub.edge_on())

    def test_the_variable_is_the_rules(self):
        import maya_edgerules
        self.assertEqual(hub.EDGE_VAR, maya_edgerules.EDGE_VAR)
        self.assertEqual(hub.EDGE_VAR, "skeldarAnimHub_edge")

    def test_set_edge_on_drops_the_dock_and_builds_the_edge(self):
        self.fake.workspace[hub.CONTROL] = {}
        hub.set_edge(True)
        self.assertEqual(self.fake.optionvars[hub.EDGE_VAR], 1)
        self.fake.run_deferred()
        self.assertIn(hub.CONTROL, self.fake.deleted)
        self.assertTrue(self.edges[-1].revealed_with_hold)

    def test_set_edge_is_deferred(self):
        """The press comes from the menu, inside the hub it deletes (⋮)."""
        self.fake.workspace[hub.CONTROL] = {}
        hub.set_edge(True)
        self.assertEqual(self.edges, [])
        self.assertNotIn(hub.CONTROL, self.fake.deleted)

    def test_set_edge_off_destroys_the_edge_and_opens_the_dock(self):
        self.fake.optionvars[hub.EDGE_VAR] = 1
        hub.start()
        hub.set_edge(False)
        self.fake.run_deferred()
        self.assertTrue(self.edges[-1].destroyed)
        self.assertIn(hub.CONTROL, self.fake.workspace)

    def test_the_last_press_wins(self):
        """On, then off before the first switch ran: the dock, no edge."""
        hub.set_edge(True)
        hub.set_edge(False)
        self.fake.run_deferred()
        self.assertEqual(self.edges, [])
        self.assertIn(hub.CONTROL, self.fake.workspace)

    def test_edge_mode_needs_the_skin(self):
        self.fake.optionvars[hub.CLASSIC_VAR] = 1
        self.assertFalse(hub.set_edge(True))
        self.assertNotEqual(self.fake.optionvars.get(hub.EDGE_VAR), 1)

    def test_and_qt(self):
        self.qt.available = lambda: False
        self.fake.optionvars[hub.EDGE_VAR] = 1
        self.assertFalse(hub.edge_on())
        self.assertFalse(hub.set_edge(True))

    def test_the_menu_row_shows_the_mode(self):
        skin = FakeSkin(None)
        hub._dress_edge(skin)
        self.fake.optionvars[hub.EDGE_VAR] = 1
        hub._dress_edge(skin)
        self.assertEqual(skin.edge_painted, [(False, "left"), (True, "left")])

    def test_the_pin_and_the_switch_are_the_header_s(self):
        self.fake.optionvars[hub.EDGE_VAR] = 1
        hub.start()
        callbacks = hub._SKIN.callbacks
        callbacks["pin"](True)
        self.assertTrue(self.edges[-1].pinned)
        callbacks["pin"](False)
        self.assertFalse(self.edges[-1].pinned)
        self.assertIs(callbacks["edge"], hub.set_edge)
        self.assertIs(callbacks["edge_side"], hub.set_edge_side)

    # --------------------------------------------------- the side

    def test_the_side_is_left_by_default_and_remembered(self):
        """2026-10-09: «Можем добавить опцию выбора стороны монитора
        откуда выезжает наша полка?» - ⋮ -> Edge panel ▸ Left / Right."""
        self.assertEqual(hub.SIDE_VAR, "skeldarAnimHub_edgeSide")
        self.assertEqual(hub.edge_side(), "left")
        self.fake.optionvars[hub.SIDE_VAR] = "right"
        self.assertEqual(hub.edge_side(), "right")
        self.fake.optionvars[hub.SIDE_VAR] = "top"
        self.assertEqual(hub.edge_side(), "left")

    def test_the_panel_is_built_on_the_remembered_side(self):
        self.fake.optionvars[hub.EDGE_VAR] = 1
        self.fake.optionvars[hub.SIDE_VAR] = "right"
        edge = hub.start()
        self.assertEqual(edge.side, "right")
        self.assertTrue(hub._SKIN.edge_mode)
        self.assertEqual(hub._SKIN.edge_side, "right")

    def test_a_side_picked_while_off_turns_the_mode_on_there(self):
        self.fake.workspace[hub.CONTROL] = {}
        self.assertTrue(hub.set_edge_side("right"))
        self.assertEqual(self.fake.optionvars[hub.SIDE_VAR], "right")
        self.assertEqual(self.fake.optionvars[hub.EDGE_VAR], 1)
        self.assertEqual(self.edges, [])                 # deferred
        self.fake.run_deferred()
        self.assertIn(hub.CONTROL, self.fake.deleted)
        self.assertEqual(self.edges[-1].side, "right")
        self.assertTrue(self.edges[-1].revealed_with_hold)

    def test_the_other_side_moves_the_standing_panel(self):
        self.fake.optionvars[hub.EDGE_VAR] = 1
        edge = hub.start()
        self.assertTrue(hub.set_edge_side("right"))
        self.assertEqual(edge.sides, [])                 # deferred
        self.fake.run_deferred()
        self.assertEqual(edge.sides, ["right"])
        self.assertEqual(edge.side, "right")
        self.assertTrue(edge.revealed_with_hold)
        self.assertEqual(len(self.edges), 1)             # the same panel
        self.assertIs(hub._SKIN.host, edge.slot)
        self.assertEqual(hub._SKIN.edge_painted[-1], (True, "right"))

    def test_the_same_side_again_changes_nothing(self):
        self.fake.optionvars[hub.EDGE_VAR] = 1
        edge = hub.start()
        hub.set_edge_side("left")
        self.fake.run_deferred()
        self.assertEqual(edge.sides, ["left"])           # asked, refused
        self.assertEqual(edge.reveals, [])

    def test_the_last_side_picked_wins(self):
        self.fake.optionvars[hub.EDGE_VAR] = 1
        edge = hub.start()
        hub.set_edge_side("right")
        hub.set_edge_side("left")
        self.fake.run_deferred()
        self.assertEqual(edge.side, "left")
        self.assertEqual(edge.reveals, [])

    def test_off_is_set_edge_false(self):
        self.fake.optionvars[hub.EDGE_VAR] = 1
        hub.start()
        self.assertFalse(hub.set_edge_side("off"))
        self.assertEqual(self.fake.optionvars[hub.EDGE_VAR], 0)
        self.fake.run_deferred()
        self.assertTrue(self.edges[-1].destroyed)
        self.assertIn(hub.CONTROL, self.fake.workspace)

    def test_a_side_needs_the_skin(self):
        self.fake.optionvars[hub.CLASSIC_VAR] = 1
        self.assertFalse(hub.set_edge_side("right"))
        self.assertNotIn(hub.SIDE_VAR, self.fake.optionvars)
        self.assertNotEqual(self.fake.optionvars.get(hub.EDGE_VAR), 1)

    def test_a_side_with_no_panel_standing_builds_it_there(self):
        """The mode on but no panel (it failed earlier, or was never
        built this session): the panel is built on the side and shown."""
        self.fake.optionvars[hub.EDGE_VAR] = 1
        hub.set_edge_side("right")
        self.fake.run_deferred()
        self.assertEqual(self.edges[-1].side, "right")
        self.assertTrue(self.edges[-1].revealed_with_hold)

    def test_the_menu_shows_the_side(self):
        skin = FakeSkin(None)
        self.fake.optionvars[hub.EDGE_VAR] = 1
        self.fake.optionvars[hub.SIDE_VAR] = "right"
        hub._dress_edge(skin)
        self.assertEqual(skin.edge_painted, [(True, "right")])

    # --------------------------------------------------- the build

    def test_start_does_nothing_in_dock_mode(self):
        hub.start()
        self.assertEqual(self.edges, [])

    def test_start_builds_the_skin_into_the_edge_hidden(self):
        """The startup plug-in's call: the panel waits at the edge."""
        self.fake.optionvars[hub.EDGE_VAR] = 1
        edge = hub.start()
        self.assertIs(edge, self.edges[-1])
        self.assertIs(self.he.state()["edge"], edge)
        self.assertEqual(edge.reveals, [])               # hidden
        self.assertTrue(hub.is_skinned())
        self.assertIs(hub._SKIN.layout, edge.slot)
        self.assertTrue(hub._SKIN.edge_mode)
        self.assertEqual(hub._SKIN.scale, 1.5)
        self.assertEqual(self.qt.destroyed, [])          # not the control's
        self.assertEqual(self.qt.destroyed_in, [edge.slot])
        for sec in hub.card_sections():
            self.assertEqual(self.built(sec.key), 1, sec.key)
        self.assertNotIn(hub.CONTROL, self.fake.workspace)

    def test_start_twice_is_one_edge(self):
        self.fake.optionvars[hub.EDGE_VAR] = 1
        first = hub.start()
        self.assertIs(hub.start(), first)
        self.assertEqual(len(self.edges), 1)
        self.assertEqual(self.built("characters"), 1)

    def test_start_leaves_a_panel_an_older_module_built(self):
        """The startup plug-in (2026-10-08): an install reloads it after its
        purge, and the deferred start() of the FRESH module meets the panel
        the purged one built - out, if the install came from its Update card.
        Left as it is: the install's own rebuild_open_hub rebuilds it and
        keeps it out (`_rebuild_edge`); a start() rebuilding it first would
        have put it away hidden under the animator."""
        self.fake.optionvars[hub.EDGE_VAR] = 1
        older = FakeEdge()
        older.reveal(hold=True)
        self.edges.append(older)
        self.he.state()["edge"] = older
        self.assertIs(hub.start(), older)
        self.assertFalse(older.destroyed)
        self.assertEqual(len(self.edges), 1)
        self.assertEqual(self.built("characters"), 0)
        hub.rebuild()                                    # the install's
        self.assertTrue(older.destroyed)
        self.assertTrue(self.edges[-1].shown)

    def test_a_pending_registration_s_start_keeps_the_panel_show_built(self):
        """Task 13b (2026-10-09): the first show() of a later session opens
        the edge panel AND finishes the pending registration, whose load runs
        the plug-in's initializePlugin - its deferred maya_hub.start() meets
        the panel show() built: one edge, still out, one skin."""
        self.fake.optionvars[hub.EDGE_VAR] = 1
        self.fake.optionvars[hub.STARTUP_PENDING_VAR] = 1
        starts = []

        def complete_startup():
            #  loadPlugin -> initializePlugin -> executeDeferred(_start)
            self.fake.deferred.append(lambda: starts.append(hub.start()))
            return ""
        saved = hub._installer
        hub._installer = lambda: types.SimpleNamespace(
            complete_startup=complete_startup)
        hub._STARTUP_QUEUED = False
        try:
            hub.show("colour")
            shown, skin = self.edges[-1], hub._SKIN
            self.assertLessEqual(self._drain(), 3)
        finally:
            hub._installer = saved
            hub._STARTUP_QUEUED = False
        self.assertEqual(starts, [shown])                 # the plug-in's start ran
        self.assertEqual(len(self.edges), 1)
        self.assertIs(hub.edge(), shown)
        self.assertFalse(shown.destroyed)
        self.assertTrue(shown.shown)
        self.assertEqual(shown.concealed, 0)
        self.assertIs(hub._SKIN, skin)
        self.assertEqual(self.built("characters"), 1)

    def test_the_width_is_remembered_and_reused(self):
        import maya_edgerules
        self.fake.optionvars[hub.EDGE_VAR] = 1
        edge = hub.start()
        self.assertEqual(edge.width, maya_edgerules.WIDTH)
        edge.on_width(512)                              # the grip released
        self.assertEqual(self.fake.optionvars[maya_edgerules.WIDTH_VAR], 512)
        hub.rebuild()
        self.assertEqual(self.edges[-1].width, 512)

    def test_is_open_while_the_edge_stands(self):
        self.fake.optionvars[hub.EDGE_VAR] = 1
        self.assertFalse(hub.is_open())
        hub.start()
        self.assertTrue(hub.is_open())
        hub.stop()
        self.assertFalse(hub.is_open())
        self.assertIsNone(hub.edge())

    def test_stop_destroys_the_skin_then_the_edge(self):
        """The skin's root first: the edge's destroy deletes its slot and
        whatever still stands in it."""
        self.fake.optionvars[hub.EDGE_VAR] = 1
        hub.start()
        log = []
        skin, edge = hub._SKIN, self.edges[-1]
        skin_destroy, edge_destroy = skin.destroy, edge.destroy
        skin.destroy = lambda: (log.append("skin"), skin_destroy())
        edge.destroy = lambda: (log.append("edge"), edge_destroy())
        hub.stop()
        self.assertEqual(log, ["skin", "edge"])
        self.assertIsNone(hub._SKIN)
        self.assertIsNone(self.he.state()["edge"])

    def test_the_uiscript_in_edge_mode_builds_nothing_in_the_dock(self):
        self.fake.optionvars[hub.EDGE_VAR] = 1
        self.fake.workspace[hub.CONTROL] = {}
        hub.build()
        self.assertEqual(self.built("characters"), 0)    # not in the dock
        self.fake.run_deferred()
        self.assertIn(hub.CONTROL, self.fake.deleted)
        self.assertEqual(self.built("characters"), 1)    # in the edge
        self.assertIs(hub._SKIN.layout, self.edges[-1].slot)

    def test_the_uiscript_builds_the_dock_once_the_mode_is_off(self):
        """Edge mode turned off before the deferred half ran: the control
        Maya restored is kept and gets the hub build() left out of it."""
        self.fake.optionvars[hub.EDGE_VAR] = 1
        self.fake.workspace[hub.CONTROL] = {}
        hub.build()
        self.fake.optionvars[hub.EDGE_VAR] = 0
        self.fake.run_deferred()
        self.assertEqual(self.edges, [])
        self.assertNotIn(hub.CONTROL, self.fake.deleted)
        self.assertEqual(self.built("characters"), 1)
        self.assertEqual(hub._SKIN.layout, "widget of " + hub.CONTROL)

    def test_a_skin_failing_at_the_edge_leaves_the_hub_to_the_dock(self):
        """The dock's fallback for a broken skin is the classic hub; at the
        edge it is the dock, for the rest of this module object's session -
        or the uiScript, start() and show() would hand the hub to each
        other."""
        self.fake.optionvars[hub.EDGE_VAR] = 1
        FakeSkin.fail_finish = True
        self.assertIsNone(hub.start())
        self.assertTrue(self.edges[-1].destroyed)
        self.assertIsNone(hub.edge())
        self.assertFalse(hub.edge_on())
        hub.show()
        self.assertIn(hub.CONTROL, self.fake.workspace)
        self.assertEqual(len(self.edges), 1)             # not tried again

    def _maya_like(self):
        """The fake as Maya behaves where it matters here: deleteUI removes
        the control, and creating one runs its uiScript (build())."""
        fake = self.fake

        def delete_ui(name, **kwargs):
            fake.workspace.pop(name, None)
            fake.deleted.append(name)

        plain = fake.workspaceControl

        def workspace_control(name, **kwargs):
            created = not any(kwargs.get(k) for k in (
                "exists", "query", "q", "edit", "e"))
            result = plain(name, **kwargs)
            if created and "uiScript" in kwargs:
                hub.build()
            return result
        fake.deleteUI = delete_ui
        fake.workspaceControl = workspace_control

    def _drain(self, rounds=10):
        """Run the deferred queue until it is empty; how many rounds it took
        (`rounds` + 1: it never emptied)."""
        for done in range(rounds):
            if not self.fake.deferred:
                return done
            self.fake.run_deferred()
        return rounds + 1 if self.fake.deferred else rounds

    def test_an_edge_that_cannot_be_built_leaves_the_hub_docked(self):
        """Review, fix round 1: an Edge raising before the skin (a half
        installed maya_hubedge, a constructor's first live run) was outside
        the try that records a failure - nothing printed, edge_on() still
        True, and the dock and the edge handed the hub to each other on
        every idle (the control deleted and created again for ever)."""
        self._maya_like()
        self.fake.optionvars[hub.EDGE_VAR] = 1

        def broken(*args, **kwargs):
            raise RuntimeError("no edge here")
        self.he.Edge = broken
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertIsNone(hub.start())
            hub.show()
            rounds = self._drain()
        self.assertLessEqual(rounds, 2)                      # it drained
        self.assertEqual(self.fake.deferred, [])
        self.assertIn(hub.CONTROL, self.fake.workspace)      # docked
        self.assertNotIn(hub.CONTROL, self.fake.deleted)
        self.assertFalse(hub.edge_on())                      # this session
        self.assertTrue(hub.is_skinned())
        self.assertEqual(hub._SKIN.layout, "widget of " + hub.CONTROL)
        printed = out.getvalue()
        self.assertIn("edge panel", printed)
        self.assertIn("no edge here", printed)              # the traceback
        #  and the animator is told why the dock came back, once
        said = [text for text, _state in hub._SKIN.said]
        self.assertEqual(len([t for t in said if "no edge here" in t]), 1)
        hub.show()
        said = [text for text, _state in hub._SKIN.said]
        self.assertEqual(len([t for t in said if "no edge here" in t]), 1)

    def test_a_missing_maya_hubedge_leaves_the_hub_docked(self):
        """The import itself inside the same try."""
        self._maya_like()
        self.fake.optionvars[hub.EDGE_VAR] = 1

        def missing():
            raise ImportError("No module named 'maya_hubedge'")
        hub._hubedge = missing
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            hub.set_edge(True)
            self.assertLessEqual(self._drain(), 2)
        self.assertIn(hub.CONTROL, self.fake.workspace)
        self.assertFalse(hub.edge_on())
        self.assertIn("maya_hubedge", out.getvalue())

    def test_a_restored_dock_keeps_the_hub_when_the_edge_cannot_be_built(self):
        """Maya restored a docked control while edge mode is on, and the
        edge fails: the hub is built in that control, once."""
        self._maya_like()
        self.fake.optionvars[hub.EDGE_VAR] = 1
        self.fake.workspace[hub.CONTROL] = {}

        def broken(*args, **kwargs):
            raise RuntimeError("no edge here")
        self.he.Edge = broken
        with contextlib.redirect_stdout(io.StringIO()):
            hub.build()                                     # the uiScript
            self.assertLessEqual(self._drain(), 2)
        self.assertIn(hub.CONTROL, self.fake.workspace)
        self.assertEqual(self.built("characters"), 1)
        self.assertEqual(hub._SKIN.layout, "widget of " + hub.CONTROL)
        self.assertTrue([text for text, _state in hub._SKIN.said
                         if "no edge here" in text])

    def test_the_failure_line_names_the_error_on_one_line(self):
        text = hub.edge_failure_text(RuntimeError("no edge here\nmore"))
        self.assertIn("RuntimeError: no edge here", text)
        self.assertNotIn("\n", text)
        self.assertIn("docked", text)
        self.assertIn("(ImportError)", hub.edge_failure_text(ImportError()))
        text.encode("ascii")                         # printable anywhere

    def test_turning_it_on_again_tries_again(self):
        self.fake.optionvars[hub.EDGE_VAR] = 1
        FakeSkin.fail_finish = True
        hub.start()
        FakeSkin.fail_finish = False
        hub.set_edge(True)
        self.fake.run_deferred()
        self.assertEqual(len(self.edges), 2)
        self.assertTrue(self.edges[-1].alive())
        self.assertTrue(self.edges[-1].revealed_with_hold)

    # --------------------------------------------------- show

    def test_show_in_edge_mode_reveals_and_holds(self):
        self.fake.optionvars[hub.EDGE_VAR] = 1
        hub.start()
        hub.show("retarget")
        self.assertTrue(self.edges[-1].revealed_with_hold)
        self.assertNotIn(hub.CONTROL, self.fake.workspace)

    def test_show_builds_the_edge_when_none_stands_and_opens_the_card(self):
        self.fake.optionvars[hub.EDGE_VAR] = 1
        self.fake.optionvars[hub.OPTIONVAR.format("studio")] = 1
        hub.show("studio")
        self.assertEqual(len(self.edges), 1)
        self.assertEqual(self.edges[-1].reveals, [True])
        self.assertFalse(hub._SKIN.cards["studio"].collapsed())
        self.assertEqual(hub._SKIN.active, "studio")
        self.assertNotIn(hub.CONTROL, self.fake.workspace)

    def test_an_edge_an_older_module_built_is_rebuilt_deferred(self):
        """An install purges our modules and leaves the panel standing; a
        show() from inside that panel must not delete it under itself."""
        self.fake.optionvars[hub.EDGE_VAR] = 1
        older = FakeEdge()
        self.edges.append(older)
        self.he.state()["edge"] = older
        hub.show("retarget")
        self.assertFalse(older.destroyed)                # not under the call
        self.assertEqual(len(self.edges), 1)
        self.fake.run_deferred()
        self.assertTrue(older.destroyed)
        self.assertTrue(self.edges[-1].revealed_with_hold)
        self.assertIs(hub._SKIN.layout, self.edges[-1].slot)

    def test_show_in_dock_mode_with_an_edge_still_standing_leaves_it_first(self):
        """A switch off on its way (or Classic look): the edge panel goes
        before the dock opens - deferred, the call may come from inside it -
        or two skins would answer to the controls' names (⋮ -> Classic
        look pressed at the edge is the other way here)."""
        self.fake.optionvars[hub.EDGE_VAR] = 1
        hub.start()
        edge = self.edges[-1]
        self.fake.optionvars[hub.EDGE_VAR] = 0
        hub.show("colour")
        self.assertFalse(edge.destroyed)
        self.assertNotIn(hub.CONTROL, self.fake.workspace)
        self.fake.run_deferred()
        self.assertTrue(edge.destroyed)
        self.assertIn(hub.CONTROL, self.fake.workspace)

    # --------------------------------------------------- rebuild

    def test_rebuild_recreates_the_edge_keeping_it_out_and_pinned(self):
        """After an install the panel is rebuilt from the fresh modules (a new
        Edge, a new skin): the animator who was working in it keeps it out,
        and the pin is per session, not per build."""
        self.fake.optionvars[hub.EDGE_VAR] = 1
        first = hub.start()
        old_skin = hub._SKIN
        first.reveal()
        hub._press_pin(True)
        hub.rebuild()
        self.assertTrue(first.destroyed)
        self.assertFalse(old_skin.alive())
        new = self.edges[-1]
        self.assertIsNot(new, first)
        self.assertTrue(new.shown)
        self.assertTrue(new.pinned)
        self.assertEqual(hub._SKIN.pins, [True])
        self.assertIs(hub._SKIN.layout, new.slot)

    def test_rebuild_of_a_hidden_edge_stays_hidden(self):
        self.fake.optionvars[hub.EDGE_VAR] = 1
        hub.start()
        hub.rebuild()
        self.assertEqual(len(self.edges), 2)
        self.assertEqual(self.edges[-1].reveals, [])
        self.assertFalse(self.edges[-1].pinned)

    def test_classic_at_the_edge_moves_the_hub_to_the_dock(self):
        """The classic hub does not live at the edge (the spec's "not
        built"): ⋮ -> Classic look takes the hub to the dock."""
        self.fake.optionvars[hub.EDGE_VAR] = 1
        hub.start()
        hub.set_classic(True)
        self.fake.run_deferred()
        self.assertTrue(self.edges[-1].destroyed)
        self.assertIsNone(self.he.state()["edge"])
        self.assertIn(hub.CONTROL, self.fake.workspace)

    def test_the_new_look_from_the_classic_dock_goes_back_to_the_edge(self):
        self.fake.optionvars[hub.EDGE_VAR] = 1
        self.fake.optionvars[hub.CLASSIC_VAR] = 1
        self.fake.workspace[hub.CONTROL] = {}
        hub.build()                                     # the classic dock
        self.assertIn("skeldarHubFrameCharacters", self.fake.frames)
        hub.set_classic(False)
        self.fake.run_deferred()
        self.assertIn(hub.SCROLL, self.fake.deleted)
        self.assertIn(hub.CONTROL, self.fake.deleted)
        self.assertEqual(len(self.edges), 1)
        self.assertTrue(self.edges[-1].revealed_with_hold)
        self.assertTrue(hub.is_skinned())

    # --------------------------------------------------- the viewport message

    def test_a_status_while_hidden_goes_to_the_viewport(self):
        self.fake.optionvars[hub.EDGE_VAR] = 1
        hub.start()
        self.edges[-1].shown = False
        hub._told("characters", "Imported A_Jump", False)
        msgs = self.viewport_messages()
        self.assertTrue(msgs)

    def test_the_viewport_message_is_the_first_line(self):
        self.fake.optionvars[hub.EDGE_VAR] = 1
        hub.start()
        hub._told("characters", "Imported A_Jump\nonto Manny_Rig", False)
        kwargs = self.viewport_messages()[0][2]
        self.assertEqual(kwargs["assistMessage"], "Imported A_Jump")
        self.assertTrue(kwargs["fade"])

    def test_not_when_shown_or_when_the_writer_showed_it(self):
        self.fake.optionvars[hub.EDGE_VAR] = 1
        hub.start()
        self.edges[-1].shown = True
        hub._told("characters", "x", False)
        self.edges[-1].shown = False
        hub._told("retarget", "y", True)
        self.assertFalse([c for c in self.fake.calls
                          if c[0] == "inViewMessage"])

    def test_not_in_the_dock_nor_for_an_empty_line(self):
        hub._told("characters", "x", False)              # no edge
        self.fake.optionvars[hub.EDGE_VAR] = 1
        hub.start()
        hub._told("characters", "", False)
        self.assertEqual(self.viewport_messages(), [])


class ClassicWithoutQt(FakeToolsMixin, unittest.TestCase):

    def setUp(self):
        self.real = (hub.cmds, hub._hubqt)
        self.fake = FakeUiCmds()
        hub.cmds = self.fake
        hub._hubqt = lambda: _fake_qt(available=False)
        self.install_fakes()

    def tearDown(self):
        hub.cmds, hub._hubqt = self.real
        self.remove_fakes()

    def test_no_way_to_a_skin_that_cannot_be_built(self):
        hub.build()
        self.assertFalse(hub.is_skinned())
        self.assertNotIn(hub.NEW_LOOK_BUTTON,
                         [c[1][0] for c in self.fake.calls
                          if c[0] == "button" and c[1]])

    def test_the_marks_are_dropped(self):
        hub.build()
        self.assertEqual(hub.hubstyle.take_marks(), [])


if __name__ == "__main__":
    unittest.main()
