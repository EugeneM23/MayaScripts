"""The mode's refusals, its toggle and its hub section, on fakes."""

import unittest
from unittest import mock

from tests.uifakes import FakeUiCmds

from maya_graphoverlay import mode, viewport, winstyle


class Refusals(unittest.TestCase):

    def setUp(self):
        mode.reset_state()

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
        mode.reset_state()
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
            mode.reset_state()

    def test_the_section_key(self):
        self.assertEqual(mode.HUB_SECTION, "graphoverlay")


class LearnTones(unittest.TestCase):

    def setUp(self):
        mode.reset_state()

    def tearDown(self):
        mode.reset_state()

    def test_tones_grow_and_never_shrink(self):
        self.assertEqual(mode.learn_tones([(64, 64, 64)]), [(64, 64, 64)])
        self.assertEqual(mode.learn_tones([(55, 55, 55), (64, 64, 64)]),
                         [(64, 64, 64), (55, 55, 55)])
        self.assertEqual(mode.learn_tones([(64, 64, 64)]),
                         [(64, 64, 64), (55, 55, 55)])

    def test_at_most_three(self):
        for tone in ((1, 1, 1), (2, 2, 2), (3, 3, 3), (4, 4, 4)):
            mode.learn_tones([tone])
        self.assertEqual(len(mode._STATE.keys), mode.MOST_TONES)

    def test_a_tone_far_from_the_background_is_never_learnt(self):
        """Measured live 2026-09-30: (0, 0, 0) was learnt as a third tone
        (a frame drawn half black while the host grew) and would have keyed
        out the black range flags. The Graph Editor's tones stand within a
        few levels of each other (64 and 55)."""
        mode.learn_tones([(64, 64, 64), (55, 55, 55)])
        self.assertEqual(mode.learn_tones([(0, 0, 0)]),
                         [(64, 64, 64), (55, 55, 55)])


class TheChrome(unittest.TestCase):
    """The whole Graph Editor, its curve area alone see-through
    (2026-09-30: «я не могу выделить отдельно каналы ... и нет остальных
    инструментов»)."""

    def setUp(self):
        mode.reset_state()

    def test_the_menus_toolbar_and_channel_list_are_on_by_default(self):
        self.assertTrue(mode.CHROME)

    def test_maya_s_own_graph_editor_is_borrowed(self):
        """55 of Maya's runtime commands name graphEditor1GraphEd outright;
        in a panel of our own the Stacked View button switched the
        animator's Graph Editor (measured 2026-09-30)."""
        self.assertTrue(mode.BORROW)

    def test_two_wrappers_of_nothing_are_not_the_same_object(self):
        self.assertFalse(mode._same_object(None, None))
        self.assertFalse(mode._same_object(object(), None))

    def test_a_chrome_repaint_with_the_mode_off_does_nothing(self):
        mode._on_chrome_paint()
        self.assertFalse(mode._STATE.chrome_pending)
        self.assertEqual(mode._watch_chrome(), 0)

    def test_the_state_carries_the_chrome_fields(self):
        for name in ("watch", "watched", "grabbing", "chrome_pending",
                     "chrome_last", "chrome_grabs", "ticks"):
            self.assertTrue(hasattr(mode._STATE, name), name)


class TheHint(unittest.TestCase):

    def test_it_names_the_camera_and_the_key(self):
        self.assertIn("alt+mouse: camera", mode.HINT)
        self.assertIn("alt+c", mode.HINT)


class OneStatePerSession(unittest.TestCase):
    """Measured live 2026-09-30: an install purges our modules, the hub's
    button stays bound to the copy that built it, and four copies of this
    module each kept their own state - the live overlay ran in a copy
    nobody could reach, and the one `import` handed out said it was off.
    Every copy shares the one state now."""

    def test_a_second_copy_of_the_module_sees_the_same_state(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("mode_second_copy",
                                                      mode.__file__)
        copy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(copy)
        self.assertIs(copy._STATE, mode._STATE)
        mode.reset_state()
        mode._STATE.ghost = object()
        try:
            self.assertTrue(copy.is_on())
        finally:
            mode.reset_state()

    def test_a_reset_clears_the_fields_an_older_class_never_knew(self):
        """Measured live 2026-09-30: the session's state was made by the
        first build, whose `reset()` knew no chrome fields - after an off
        the dead event filter stayed, and the next on died on it."""
        class Older(object):
            def reset(self):
                self.ghost = None

        older = Older()
        older.watch = "a dead filter"
        older.watched = {1, 2}
        mode.reset_state(older)
        self.assertIsNone(older.watch)
        self.assertEqual(older.watched, set())
        self.assertIsNone(older.ghost)

    def test_a_state_from_an_older_copy_gains_the_new_fields(self):
        import sys
        state = getattr(sys, mode.SESSION_STATE)
        del state.cost
        try:
            mode._shared_state()
            self.assertEqual(state.cost, 0.0)
        finally:
            mode.reset_state()


class ThePackage(unittest.TestCase):

    def test_the_package_names_resolve_lazily_to_the_mode(self):
        import maya_graphoverlay
        self.assertIs(maya_graphoverlay.toggle, mode.toggle)
        with self.assertRaises(AttributeError):
            maya_graphoverlay.nonsense


if __name__ == "__main__":
    unittest.main()
