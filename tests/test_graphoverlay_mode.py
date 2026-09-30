"""The mode's refusals, its toggle and its hub section, on fakes."""

import unittest
from unittest import mock

from tests.uifakes import FakeUiCmds

from maya_graphoverlay import mode, viewport, winstyle


class Refusals(unittest.TestCase):

    def setUp(self):
        mode._STATE.reset()

    def test_off_when_already_off(self):
        self.assertEqual(mode.disable(), "Graph Overlay is already off")

    def test_no_windows_no_overlay(self):
        with mock.patch.object(winstyle, "available", return_value=False):
            self.assertEqual(mode.enable(), "Graph Overlay needs Windows")
        self.assertFalse(mode.is_on())

    def test_no_viewport_no_overlay(self):
        with mock.patch.object(winstyle, "available", return_value=True), \
                mock.patch.object(viewport, "active_panel",
                                  return_value=None), \
                mock.patch.object(viewport, "gl_rect", return_value=None):
            self.assertEqual(mode.enable(),
                             "Graph Overlay: no viewport to lie on")
        self.assertFalse(mode.is_on())


class HubSection(unittest.TestCase):

    def setUp(self):
        mode._STATE.reset()
        self.fake = FakeUiCmds()
        self.real = mode.cmds
        mode.cmds = self.fake

    def tearDown(self):
        mode.cmds = self.real

    def test_it_builds_a_hint_the_button_and_the_status(self):
        mode.build_panel()
        made = [(name, args) for name, args, _kw in self.fake.calls]
        self.assertIn(("button", (mode.BUTTON,)), made)
        self.assertIn(("text", (mode.STATUS,)), made)

    def test_the_button_says_the_state(self):
        self.assertEqual(mode.button_label(), "Graph Overlay: OFF")
        mode._STATE.ghost = object()
        try:
            self.assertEqual(mode.button_label(), "Graph Overlay: ON")
        finally:
            mode._STATE.reset()

    def test_the_section_key(self):
        self.assertEqual(mode.HUB_SECTION, "graphoverlay")


class TheHint(unittest.TestCase):

    def test_it_names_the_camera_and_the_key(self):
        self.assertIn("alt+mouse: camera", mode.HINT)
        self.assertIn("alt+c", mode.HINT)


class ThePackage(unittest.TestCase):

    def test_the_package_names_resolve_lazily_to_the_mode(self):
        import maya_graphoverlay
        self.assertIs(maya_graphoverlay.toggle, mode.toggle)
        with self.assertRaises(AttributeError):
            maya_graphoverlay.nonsense


if __name__ == "__main__":
    unittest.main()
