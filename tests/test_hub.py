"""maya_hub: one dockable panel, every tool a collapsible section.

Spec: docs/superpowers/specs/2026-09-17-skeldar-hub-design.md
"""

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
        """2026-09-28, the skin: grouped Scene / Animation / Look, then the
        header's two. Weapons still follows Characters (its refresh writes
        the Characters header)."""
        self.assertEqual([s.label for s in hub.SECTIONS],
                         ["Characters", "Weapons", "Connections", "UE Bridge",
                          "Retarget", "Studio", "Colour", "Hotkeys",
                          "Update"])

    def test_the_groups_and_their_icons(self):
        import maya_hubicons
        groups = [(s.key, s.group) for s in hub.SECTIONS]
        self.assertEqual(groups, [
            ("characters", "scene"), ("weapons", "scene"),
            ("connections", "scene"), ("uebridge", "animation"),
            ("retarget", "animation"), ("studio", "look"),
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
        self.assertEqual([s.key for s in hub.card_sections()],
                         ["characters", "weapons", "connections", "uebridge",
                          "retarget", "studio", "colour"])

    def test_every_section_names_a_real_module_and_builder(self):
        wanted = {
            "uebridge": ("maya_uebridge.window", "build_panel"),
            "characters": ("maya_scenesetup.window", "build_characters_panel"),
            "weapons": ("maya_scenesetup.window", "build_weapons_panel"),
            "connections": ("maya_scenesetup.connections", "build_panel"),
            "retarget": ("maya_rig_retarget", "build_panel"),
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
        self.fake.optionvars[hub.OPTIONVAR.format("uebridge")] = 1
        hub.build()
        self.assertTrue(self.fake.frames["skeldarHubFrameUebridge"]["collapse"])
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
        for key in ("uebridge", "weapons", "connections", "retarget",
                    "hotkeys", "studio", "colour"):
            self.assertEqual(self.built(key), 1, key)

    def test_the_broken_section_says_so(self):
        hub.build()
        texts = [c[2].get("label", "") for c in self.fake.calls
                 if c[0] == "text"]
        self.assertTrue(any("Characters could not be built" in t
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
        expected = hub.scroll_offset([self.fake.control_height] * 8, index,
                                     hub.ROW_SPACING)
        self.assertEqual(scrolls[0][0], "up")
        self.assertEqual(scrolls[1], ("down", expected))

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

    def body_path(self):
        return "body|" + self.key

    def set_collapsed(self, value):
        self._collapsed = value

    def collapsed(self):
        return self._collapsed


class FakeSkin(object):

    fail_finish = False

    def __init__(self, layout, scale=1.0, callbacks=None):
        self.layout = layout
        self.scale = scale
        self.callbacks = callbacks
        self.cards = {}
        self.jumps = []
        self.order = []
        self.said = []
        self.painted = []
        self.sheet = None
        self._alive = True

    def add_jump(self, key, label, icon, colour):
        self.jumps.append(key)

    def add_group(self, key, label):
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

    def set_version(self, text, tooltip, state=None):
        pass

    def scroll_to(self, key):
        return 42 if key in self.cards else None

    def alive(self):
        return self._alive

    def destroy(self):
        self._alive = False


def _fake_qt(available=True):
    module = types.ModuleType("maya_hubqt_fake")
    module.available = lambda: available
    module.host_widget = lambda control: "widget of " + control
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

    def test_cards_under_group_labels_and_no_frames(self):
        hub.build()
        self.assertEqual(hub._SKIN.order, [
            ("group", "scene"), ("card", "characters"), ("card", "weapons"),
            ("card", "connections"), ("group", "animation"),
            ("card", "uebridge"), ("card", "retarget"), ("group", "look"),
            ("card", "studio"), ("card", "colour")])
        self.assertEqual(self.fake.frames, {})
        self.assertEqual(hub._SKIN.jumps, [s.key for s in hub.card_sections()])

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

    def test_the_header_sections_are_not_cards(self):
        hub.build()
        self.assertEqual(self.built("hotkeys"), 0)
        self.assertEqual(self.built("update"), 0)
        self.assertNotIn("hotkeys", hub._SKIN.cards)

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

    def test_expanding_a_header_section_is_quiet(self):
        """maya_hotkeys.show_window / maya_update.show_window still ask for
        their keys; in the skin those are the header."""
        hub.build()
        self.assertIsNone(hub.expand("hotkeys"))
        self.assertIsNone(hub.expand("update"))

    def test_say_and_paint_reach_the_skin(self):
        hub.build()
        hub.say("Up to date: 601eaae", state="ok")
        hub.paint_hotkeys(True)
        self.assertEqual(hub._SKIN.said, [("Up to date: 601eaae", "ok")])
        self.assertEqual(hub._SKIN.painted, [True])

    def test_say_and_paint_are_quiet_without_a_skin(self):
        self.assertEqual(hub.say("hello"), "hello")
        self.assertFalse(hub.paint_hotkeys(False))

    def test_rebuild_destroys_the_skin_first(self):
        hub.build()
        first = hub._SKIN
        hub.rebuild()
        self.assertFalse(first.alive())
        self.assertTrue(hub._SKIN.alive())
        self.assertIsNot(hub._SKIN, first)


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
