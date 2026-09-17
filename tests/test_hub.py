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
    raises). One module may carry several builders: Scene Setup's holds
    Characters and Weapons."""
    def build_panel():
        if fails:
            raise RuntimeError("boom in " + module.__name__ + "." + builder)
        module.built.append(builder)
        hub.cmds.text(label=builder + " panel")
    setattr(module, builder, build_panel)


class FakeToolsMixin(object):
    """Every section's module replaced by a recording fake for the test.
    `self.tools[key]` is (module, builder) for that section."""

    def install_fakes(self, failing=()):
        self.saved = {}
        self.tools = {}
        fakes = {}
        for sec in hub.SECTIONS:
            fake = fakes.get(sec.module)
            if fake is None:
                self.saved[sec.module] = sys.modules.get(sec.module)
                fake = types.ModuleType(sec.module)
                fake.built = []
                fakes[sec.module] = fake
                sys.modules[sec.module] = fake
                if "." in sec.module:
                    parent, leaf = sec.module.rsplit(".", 1)
                    self.saved[parent] = sys.modules.get(parent)
                    pkg = types.ModuleType(parent)
                    setattr(pkg, leaf, fake)
                    sys.modules[parent] = pkg
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

    def test_seven_sections_in_shelf_order(self):
        """Scene Setup is Characters + Weapons since the evening of
        2026-09-17; Weapons follows Characters (its refresh writes the
        Characters header)."""
        self.assertEqual([s.label for s in hub.SECTIONS],
                         ["UE Bridge", "Characters", "Weapons", "Retarget",
                          "Hotkeys", "Studio", "Colour"])

    def test_every_section_names_a_real_module_and_builder(self):
        wanted = {
            "uebridge": ("maya_uebridge.window", "build_panel"),
            "characters": ("maya_scenesetup.window", "build_characters_panel"),
            "weapons": ("maya_scenesetup.window", "build_weapons_panel"),
            "retarget": ("maya_rig_retarget", "build_panel"),
            "hotkeys": ("maya_hotkeys", "build_panel"),
            "studio": ("maya_vpstudio", "build_panel"),
            "colour": ("maya_colour", "build_panel"),
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
        for key in ("uebridge", "weapons", "retarget", "hotkeys", "studio",
                    "colour"):
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
        hub.show()
        edits = self.fake.workspace[hub.CONTROL]["edits"]
        self.assertTrue(any(e.get("restore") for e in edits))
        self.assertNotIn("uiScript", self.fake.workspace[hub.CONTROL])

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
        expected = hub.scroll_offset([self.fake.control_height] * 7, index,
                                     hub.ROW_SPACING)
        self.assertEqual(scrolls[0][0], "up")
        self.assertEqual(scrolls[1], ("down", expected))

    def test_an_unknown_key_is_an_error(self):
        with self.assertRaises(KeyError):
            hub.expand("nonsense")

    def test_scroll_to_without_the_layout_is_quiet(self):
        self.assertIsNone(hub.scroll_to("colour"))


if __name__ == "__main__":
    unittest.main()
