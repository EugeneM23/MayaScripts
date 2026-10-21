"""The AT bar (2026-10-21): animBot's tools as a bar of their own on top of the Time Bar.

Its glyphs, where it docks, the ⋮ -> Time bar ▸ AT bar switch, and the smoothing its SM slider uses.
"""

import os
import re
import sys
import types
import unittest
import xml.etree.ElementTree as ElementTree
from unittest import mock

import maya

import maya_atbar
from maya_atbar import core, glyphs

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SkeldarAnim")


class Glyphs(unittest.TestCase):
    def test_every_glyph_is_an_svg_drawn_in_the_colour_asked(self):
        for name in glyphs.GLYPHS:
            doc = glyphs.svg(name, "#123456")
            self.assertTrue(ElementTree.fromstring(doc).tag.endswith("svg"), name)
            self.assertNotIn("currentColor", doc, name)
            self.assertIn("#123456", doc, name)

    def test_every_button_names_a_glyph_and_all_26_are_used(self):
        with open(os.path.join(PLUGIN, "maya_atbar", "bar.py"), encoding="utf-8") as handle:
            source = handle.read()
        used = set(re.findall(r'(?:self\._button|\bb)\("(\w+)"', source))
        self.assertEqual(sorted(used - set(glyphs.GLYPHS)), [])
        self.assertEqual(sorted(set(glyphs.GLYPHS) - used), [])
        self.assertEqual(len(used), 26)


class Place(unittest.TestCase):
    """Docked as the Time Bar is, on top of it."""

    def test_on_top_of_the_time_bar_while_it_shows(self):
        self.assertEqual(maya_atbar.dock_target(lambda n: True, lambda n: n == "skeldarTimeBar"),
                         ("dockToControl", ("skeldarTimeBar", "top")))

    def test_on_top_of_maya_s_slider_while_only_it_shows(self):
        self.assertEqual(maya_atbar.dock_target(lambda n: True, lambda n: n == "TimeSlider"),
                         ("dockToControl", ("TimeSlider", "top")))

    def test_a_hidden_time_bar_still_comes_before_the_window(self):
        self.assertEqual(maya_atbar.dock_target(lambda n: n == "skeldarTimeBar", lambda n: False),
                         ("dockToControl", ("skeldarTimeBar", "top")))

    def test_the_bottom_of_maya_s_window_without_either(self):
        self.assertEqual(maya_atbar.dock_target(lambda n: False, lambda n: False),
                         ("dockToMainWindow", ("bottom", False)))

    def test_the_uiscript_builds_the_bar_from_the_plugin_folder(self):
        code = maya_atbar.uiscript("C:\\x\\SkeldarAnim\\")
        self.assertIn('_p = "C:/x/SkeldarAnim"', code)
        self.assertIn("maya_atbar.bar.build()", code)
        compile(code, "uiscript", "exec")


class _Cmds(object):
    def __init__(self):
        self.optionvars = {}

    def optionVar(self, q=None, exists=None, intValue=None):
        if exists is not None:
            return exists in self.optionvars
        if q is not None:
            return self.optionvars[q]
        if intValue is not None:
            self.optionvars[intValue[0]] = intValue[1]
        return None

    def about(self, batch=False):
        return False


class Switch(unittest.TestCase):
    """⋮ -> Time bar ▸ AT bar: off by default, remembered."""

    def setUp(self):
        self.cmds = _Cmds()
        for patch in (mock.patch.dict(sys.modules, {"maya.cmds": self.cmds}),
                      mock.patch.object(maya, "cmds", self.cmds, create=True)):
            patch.start()
            self.addCleanup(patch.stop)

    def test_off_until_the_animator_turns_it_on(self):
        self.assertFalse(maya_atbar.wanted())

    def test_on_is_remembered_and_shows_the_bar(self):
        with mock.patch.object(maya_atbar, "ensure") as ensure, mock.patch.object(maya_atbar, "hide") as hide:
            text = maya_atbar.set_on(True)
        self.assertEqual(self.cmds.optionvars[maya_atbar.OPTIONVAR], 1)
        ensure.assert_called_once_with()
        hide.assert_not_called()
        self.assertTrue(maya_atbar.wanted())
        self.assertEqual(text, maya_atbar.MESSAGES[True])

    def test_off_is_remembered_and_hides_the_bar(self):
        with mock.patch.object(maya_atbar, "ensure") as ensure, mock.patch.object(maya_atbar, "hide") as hide:
            text = maya_atbar.set_on(False)
        self.assertEqual(self.cmds.optionvars[maya_atbar.OPTIONVAR], 0)
        hide.assert_called_once_with()
        ensure.assert_not_called()
        self.assertEqual(text, maya_atbar.MESSAGES[False])

    def test_the_hub_brings_it_back_only_when_it_was_left_on(self):
        with mock.patch.object(maya_atbar, "ensure", return_value="skeldarATBar") as ensure:
            self.assertIsNone(maya_atbar.ensure_wanted())
            ensure.assert_not_called()
            self.cmds.optionvars[maya_atbar.OPTIONVAR] = 1
            self.assertEqual(maya_atbar.ensure_wanted(), "skeldarATBar")
            ensure.assert_called_once_with()


class InsideTheTimeBar(unittest.TestCase):
    """2026-10-21, «прибери ще сірі роздєлітєльні лінії»: a control of its own stood behind Maya's splitter
    line, so on a docked Time Bar the strip is its top row - and the Time Bar's height counts it."""

    def test_no_row_no_height_and_nothing_imported_for_it(self):
        with mock.patch.dict(sys.modules):
            sys.modules.pop("maya_atbar.bar", None)
            self.assertEqual(maya_atbar.docked_height(), 0)
            self.assertNotIn("maya_atbar.bar", sys.modules)

    def test_the_time_bar_asks_the_at_bar(self):
        import maya_timebar
        with mock.patch.object(maya_atbar, "docked_height", return_value=57):
            self.assertEqual(maya_timebar.extra_height(), 57)
        with mock.patch.object(maya_atbar, "docked_height", side_effect=RuntimeError("no Qt")):
            self.assertEqual(maya_timebar.extra_height(), 0)

    def test_a_page_shown_sizes_the_control_for_the_page_and_the_row(self):
        import maya_timebar
        from maya_timebar import scene

        class Cmds(object):
            def __init__(self):
                self.edits = []

            def workspaceControl(self, name, exists=False, edit=False, **kwargs):
                if exists:
                    return True
                self.edits.append((name, kwargs))

        class Strip(object):
            ui = 1.0

            def sizeHint(self):
                return types.SimpleNamespace(height=lambda: 130)

        fake = Cmds()
        state = {"bar": None, "jobs": [], "callbacks": [], "host": "docked"}
        with mock.patch.object(scene, "cmds", fake), mock.patch.object(sys, "_skeldar_timebar", state, create=True), \
                mock.patch.object(maya_timebar, "extra_height", return_value=57):
            scene.page_height(Strip())
        self.assertEqual(fake.edits, [(maya_timebar.CONTROL, {"resizeHeight": 130 + 57})])


class SelectSets(unittest.TestCase):
    """2026-10-21: a set made in a scene tab went into the tab's namespace, and the menu, listing
    `AT_sel_*` at the root, showed none - «не зберігається нічого»."""

    TAB = "tab_AS_Dagger_Attack_Cbm_L_R_1p_Full_with3p_1"

    def test_a_set_in_the_tab_s_namespace_is_listed_by_its_own_name(self):
        nodes = [self.TAB + ":AT_sel_L_fingers", self.TAB + ":defaultObjectSet", "AT_sel_root_only",
                 "tab_other:AT_sel_elsewhere", self.TAB + ":Manny_Rig1:AT_sel_inside_the_rig"]
        self.assertEqual(core.sets_in(nodes, self.TAB), [("L_fingers", self.TAB + ":AT_sel_L_fingers")])

    def test_the_root_namespace_lists_the_root_s_sets(self):
        nodes = ["AT_sel_hands", self.TAB + ":AT_sel_L_fingers", "AT_sel_feet", "lightLinker1"]
        self.assertEqual(core.sets_in(nodes, ":"), [("feet", "AT_sel_feet"), ("hands", "AT_sel_hands")])
        self.assertEqual(core.sets_in(nodes, ""), core.sets_in(nodes, ":"))

    def test_a_label_is_the_name_without_namespace_and_prefix(self):
        self.assertEqual(core.set_label(self.TAB + ":AT_sel_L_fingers1"), "L_fingers1")

    def test_the_cells_fill_four_columns_then_wrap(self):
        """2026-10-21, «окремі ячейки щоб вони спливали»: the pop-up's grid."""
        self.assertEqual(core.sets_grid(1), [(0, 0)])
        self.assertEqual(core.sets_grid(3), [(0, 0), (0, 1), (0, 2)])
        self.assertEqual(core.sets_grid(6), [(0, 0), (0, 1), (0, 2), (0, 3), (1, 0), (1, 1)])
        self.assertEqual(core.sets_grid(0), [])


class Smoothing(unittest.TestCase):
    """The SM slider (2026-10-21): left smooths - gradually, pass by pass - right roughens."""

    def test_jitter_is_removed_not_flipped(self):
        noise = [10.0, -10.0] * 6
        out = core.smoothed(noise, 3)
        self.assertLess(max(abs(v) for v in out[2:-2]), 1.0)

    def test_zero_changes_nothing_and_each_step_left_smooths_more(self):
        values = [0.0, 10.0, -10.0, 10.0, -10.0, 50.0, 10.0, -10.0, 0.0]
        levels = core.smoothing_levels(values)
        spike = [level[5] for level in levels]
        self.assertEqual(core.smooth_at(spike, -0.0), 50.0)
        shown = [core.smooth_at(spike, p) for p in (-0.05, -0.25, -0.5, -1.0, -1.5)]
        self.assertEqual(shown, sorted(shown, reverse=True))
        self.assertAlmostEqual(core.smooth_at(spike, -0.125), (spike[0] + spike[1]) / 2.0)
        self.assertAlmostEqual(core.smooth_at(spike, -1.0), spike[core.SM_PASSES_AT_100])
        self.assertAlmostEqual(core.smooth_at(spike, -9.0), spike[-1])


if __name__ == "__main__":
    unittest.main()
