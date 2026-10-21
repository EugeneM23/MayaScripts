"""The AT bar (2026-10-21): animBot's tools as a bar of their own on top of the Time Bar.

Its glyphs, where it docks, the ⋮ -> Time bar ▸ AT bar switch, and the smoothing its SM slider uses.
"""

import os
import re
import sys
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
