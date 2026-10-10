"""The mode's refusals, its toggle and its hub section, on fakes."""

import unittest
from unittest import mock

from tests.uifakes import FakeUiCmds

import maya_hubstyle as hubstyle
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
                             "Graph Overlay: no viewport to open it over")
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

    def test_the_status_tells_the_hub(self):
        """2026-10-08: the first line goes to the hub's one message line; the
        writer shows it in the viewport itself (viewport=True)."""
        mode.build_panel()
        heard = []
        listener = lambda control, text, viewport: heard.append(
            (control, text, viewport))
        hubstyle.listen(listener)
        try:
            mode._show("Graph Overlay is on\nmore for the Script Editor")
        finally:
            hubstyle.unlisten(listener)
        self.assertEqual(heard, [(mode.STATUS, "Graph Overlay is on", True)])

    def _build(self, skin):
        mode.cmds = self.fake
        hubstyle.take_marks()
        hubstyle.set_skinning(skin)
        try:
            mode.build_panel()
        finally:
            hubstyle.set_skinning(False)
        return hubstyle.take_marks()

    def test_the_skin_is_tight(self):
        marks = self._build(True)
        self.assertEqual(self.fake.column["rowSpacing"], 3)
        button = [c[2] for c in self.fake.calls if c[0] == "button"][0]
        self.assertEqual(button["height"], 24)
        self.assertEqual([(m.role, m.icon) for m in marks
                          if m.role == "primary"], [("primary", "chart-line")])

    def test_the_classic_hub_keeps_its_numbers(self):
        self._build(False)
        self.assertEqual(self.fake.column["rowSpacing"], 6)
        button = [c[2] for c in self.fake.calls if c[0] == "button"][0]
        self.assertEqual(button["height"], 34)


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

    def test_the_standard_window_always_carries_its_chrome(self):
        """2026-10-02: the Graph Editor in a window of its own, its menus,
        toolbar and channel list as Maya draws them - there is no chrome
        switch any more, and the place is remembered in one option."""
        self.assertFalse(hasattr(mode, "CHROME"))
        self.assertEqual(mode.RECT_OPTION, "skeldarGraphOverlayRect")

    def test_maya_s_own_graph_editor_is_borrowed(self):
        """55 of Maya's runtime commands name graphEditor1GraphEd outright;
        in a panel of our own the Stacked View button switched the
        animator's Graph Editor (measured 2026-09-30)."""
        self.assertTrue(mode.BORROW)

    def test_the_chrome_waits_for_the_borrowed_panel_to_settle(self):
        """Maya rebuilds a re-parented panel just after; the first capture
        waits (the crash of 2026-09-30 came right after a switch-on)."""
        self.assertGreaterEqual(mode.CHROME_SETTLE_S, 0.3)
        self.assertTrue(hasattr(mode._STATE, "chrome_after"))
        self.assertTrue(hasattr(mode._STATE, "canvas_pointer"))


class TheWindow(unittest.TestCase):
    """The Graph Editor in a window of its own (2026-10-02): where it opens,
    and the glass following its frame."""

    def setUp(self):
        mode.reset_state()

    def tearDown(self):
        mode.reset_state()

    def test_it_opens_where_the_animator_left_it(self):
        with mock.patch.object(mode, "_remembered",
                               return_value=(100, 100, 600, 400)), \
                mock.patch.object(mode, "_screens",
                                  return_value=[(0, 0, 1920, 1080)]):
            self.assertEqual(mode._start_rect(viewport), (100, 100, 600, 400))

    def test_nothing_remembered_opens_in_the_viewport_corner(self):
        with mock.patch.object(mode, "_remembered", return_value=None), \
                mock.patch.object(mode, "_screens", return_value=[]), \
                mock.patch.object(viewport, "active_panel",
                                  return_value="modelPanel4"), \
                mock.patch.object(viewport, "gl_rect",
                                  return_value=(0, 0, 1000, 800)):
            self.assertEqual(mode._start_rect(viewport),
                             (388, 388, 600, 400))

    def test_a_remembered_place_off_every_screen_is_not_used(self):
        with mock.patch.object(mode, "_remembered",
                               return_value=(9000, 100, 600, 400)), \
                mock.patch.object(mode, "_screens",
                                  return_value=[(0, 0, 1920, 1080)]), \
                mock.patch.object(viewport, "active_panel",
                                  return_value=None), \
                mock.patch.object(viewport, "gl_rect", return_value=None):
            self.assertIsNone(mode._start_rect(viewport))

    def _on(self, showing, active=True, visible=False, rect=None):
        ghost, glass = mock.Mock(), mock.Mock()
        ghost.showing.return_value = showing
        ghost.frame_rect.return_value = rect
        glass.isVisible.return_value = visible
        mode._STATE.ghost, mode._STATE.glass = ghost, glass
        mode._STATE.active = active
        return ghost, glass

    def test_a_window_not_on_screen_hides_the_glass(self):
        _ghost, glass = self._on(showing=False, visible=True)
        mode._sync_glass()
        glass.hide.assert_called_once_with()
        glass.place.assert_not_called()

    def test_maya_behind_another_program_hides_the_glass(self):
        _ghost, glass = self._on(showing=True, active=False, visible=True,
                                 rect=(10, 20, 600, 400))
        mode._sync_glass()
        glass.hide.assert_called_once_with()

    def test_the_glass_takes_the_frame_and_the_place_is_remembered(self):
        _ghost, glass = self._on(showing=True, rect=(10, 20, 600, 400))
        with mock.patch.object(mode, "_remember") as remember, \
                mock.patch.object(mode, "_on_chrome_paint") as chrome:
            mode._sync_glass()
        glass.place.assert_called_once_with((10, 20, 600, 400))
        remember.assert_called_once_with((10, 20, 600, 400))
        chrome.assert_called_once_with()          # a new size: a new picture

    def test_a_move_alone_takes_no_new_chrome_picture(self):
        _ghost, glass = self._on(showing=True, visible=True,
                                 rect=(50, 60, 600, 400))
        mode._STATE.rect = (10, 20, 600, 400)
        with mock.patch.object(mode, "_remember"), \
                mock.patch.object(mode, "_on_chrome_paint") as chrome:
            mode._sync_glass()
        glass.place.assert_called_once_with((50, 60, 600, 400))
        chrome.assert_not_called()

    def test_nothing_moved_does_nothing(self):
        _ghost, glass = self._on(showing=True, visible=True,
                                 rect=(10, 20, 600, 400))
        mode._STATE.rect = (10, 20, 600, 400)
        mode._sync_glass()
        glass.place.assert_not_called()
        glass.hide.assert_not_called()


class NoGrabOfMayaWidgets(unittest.TestCase):
    """`QWidget.grab()` re-renders Maya's own widgets from Python; right
    after the panel was re-parented that crashed Maya (an access violation
    in SharedUI/ufe reached through shiboken, 2026-09-30). The chrome comes
    from DWM's copy of the window instead."""

    def test_no_grab_call_is_left_in_the_package(self):
        import ast
        import os
        import maya_graphoverlay
        folder = os.path.dirname(maya_graphoverlay.__file__)
        calls = []
        for name in os.listdir(folder):
            if not name.endswith(".py"):
                continue
            with open(os.path.join(folder, name), encoding="utf-8") as handle:
                tree = ast.parse(handle.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and \
                        isinstance(node.func, ast.Attribute) and \
                        node.func.attr == "grab":
                    calls.append((name, node.lineno))
        self.assertEqual(calls, [])

    def test_a_chrome_repaint_with_the_mode_off_does_nothing(self):
        mode._on_chrome_paint()
        self.assertFalse(mode._STATE.chrome_pending)
        self.assertEqual(mode._watch_chrome(), 0)

    def test_the_state_carries_the_chrome_fields(self):
        for name in ("watch", "watched", "grabbing", "chrome_pending",
                     "chrome_last", "chrome_grabs", "ticks"):
            self.assertTrue(hasattr(mode._STATE, name), name)


class TheHint(unittest.TestCase):

    def test_it_names_the_frame_keys_and_the_leave_key(self):
        """2026-10-10: no camera in the mode - the hint names only what the
        standard Graph Editor does with F / A and what alt+c does."""
        self.assertIn("alt+c", mode.HINT)
        self.assertIn("F / A", mode.HINT)
        self.assertNotIn("camera", mode.HINT)
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
