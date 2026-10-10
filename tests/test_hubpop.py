"""maya_hubpop - the popup window, its drag, its follow and its memory.

Offscreen Qt, and the Maya seams replaced: `cmds` by a fake that keeps the
optionVars, the viewport (`active_panel`, `_rect_of`) and the hub (`_hub`) by
plain stand-ins. The Maya-side proof is live (the spec's section); these tests
pin the logic a press depends on. Spec:
docs/superpowers/specs/2026-10-09-hub-section-popups-design.md.
"""

import collections
import os
import time
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tests  # noqa: F401  (puts SkeldarAnim/ on sys.path)

from PySide6 import QtCore, QtGui, QtWidgets

import maya_hubcopy as hubcopy
import maya_hubpop as hubpop
import maya_hubpop_rules as rules
import maya_hubqt as hubqt
import maya_hubstyle as hubstyle
from tests.test_hubcopy import FakeCmds

Section = collections.namedtuple("Section",
                                 "key label module builder frame group icon")

VIEW = (100, 50, 1000, 700)     # the viewport's rectangle, physical px


def _app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


class FakeMaya(FakeCmds):
    """FakeCmds with the option variables a popup stores and the deferred
    calls it queues (run by the test, as Maya's idle would)."""

    def __init__(self):
        super(FakeMaya, self).__init__()
        self.vars = {}
        self.deferred_calls = []

    def optionVar(self, *args, **kwargs):                # noqa: N802
        if kwargs.get("exists") is not None:
            return kwargs["exists"] in self.vars
        if "query" in kwargs:
            return self.vars.get(kwargs["query"])
        for flag in ("stringValue", "intValue"):
            if flag in kwargs:
                name, value = kwargs[flag]
                self.vars[name] = value
        return None

    def evalDeferred(self, fn, **kwargs):                # noqa: N802
        self.deferred_calls.append(fn)

    def mayaDpiSetting(self, **_kwargs):                 # noqa: N802
        return 1.0


class FakeHub(object):
    """The hub's face the popup asks: the sections, their builders, the
    line and the card button."""

    HEADER_ONLY = ("hotkeys",)

    def __init__(self, builders):
        self.sections = [
            Section("alpha", "Alpha", "fake_alpha", "build", "f", "scene",
                    "user"),
            Section("beta", "Beta", "fake_beta", "build", "f", "animation",
                    "bulb"),
            Section("hotkeys", "Hotkeys", "fake_alpha", "build", "f", "settings",
                    "keyboard"),
        ]
        self.builders = builders
        self.painted = []
        self.said = []

    def section(self, key):
        for sec in self.sections:
            if sec.key == key:
                return sec
        return None

    def card_sections(self):
        return [s for s in self.sections if s.key not in self.HEADER_ONLY]

    def _import(self, dotted):
        return self

    def build(self):
        return self.builders["build"]()

    def paint_popped(self, key, on):
        self.painted.append((key, on))

    def say(self, message, state=None):
        self.said.append(message)


class Seams(unittest.TestCase):
    """A fake cmds, a fake viewport and a fake hub for every test."""

    def setUp(self):
        self.app = _app()
        self.cmds = FakeMaya()
        self.builds = []

        def build_alpha():
            self.builds.append(hubcopy.current())
            self.cmds.text("mayaSceneSetupStatus", label="ready")
            self.cmds.button("press", command=lambda *_a: self.presses.append(
                hubcopy.current()))

        self.presses = []
        self.hub = FakeHub({"build": build_alpha})
        self.patches = [
            mock.patch.object(hubpop, "cmds", self.cmds),
            mock.patch.object(hubpop, "_hub", lambda: self.hub),
            mock.patch.object(hubpop, "_scale", lambda: 1.0),
            mock.patch.object(hubpop, "_main_window", lambda: None),
            mock.patch.object(hubpop, "model_panels",
                              lambda: ["modelPanel1"]),
            mock.patch.object(hubpop, "active_panel",
                              lambda: "modelPanel1"),
            mock.patch.object(hubpop, "_gl_rect", lambda panel: VIEW),
            mock.patch.object(hubqt, "path_of",
                              lambda obj: "path|" + obj.objectName()),
        ]
        for patch in self.patches:
            patch.start()
        #  the fake's commands wrapped as the real ones are, so the copy's
        #  names are prefixed the way they are in Maya
        hubcopy.install(self.cmds)
        self.hub.paint_calls = []
        hubpop._state()["popups"].clear()
        hubpop._state()["queued"] = False        # a restore queued by another test
        hubpop._stop_timer()
        self.addCleanup(self._tear_down)

    def _tear_down(self):
        for patch in self.patches:
            patch.stop()
        hubpop.destroy_all(forget=False)
        for scope in hubcopy.live():
            hubcopy.close(scope, None)

    def run_deferred(self):
        calls, self.cmds.deferred_calls = self.cmds.deferred_calls, []
        for fn in calls:
            fn()


class Window(Seams):

    def test_the_popup_is_a_card_with_a_title_and_a_scroll_area(self):
        popup = hubpop.open_popup("alpha")
        self.assertIsNotNone(popup)
        self.assertTrue(popup.root.objectName().startswith(
            hubstyle.POPUP_ROOT))
        self.assertIsNotNone(popup.title)
        self.assertIsNotNone(popup.scroll)
        self.assertIs(popup.scroll.widget(), popup.content)
        self.assertTrue(popup.root.windowFlags() & QtCore.Qt.Tool)

    def test_the_section_builds_inside_its_own_scope(self):
        popup = hubpop.open_popup("alpha")
        self.assertEqual(self.builds, [popup.scope])
        self.assertEqual(sorted(popup.scope.names),
                         ["mayaSceneSetupStatus", "press"])

    def test_a_press_in_the_copy_runs_in_the_copy_scope(self):
        popup = hubpop.open_popup("alpha")
        button = [c for c in self.cmds.calls if c[0] == "button"][-1]
        button[2]["command"]()
        self.assertEqual(self.presses, [popup.scope])

    def test_the_title_row_carries_the_section_name_and_a_close_button(self):
        popup = hubpop.open_popup("alpha")
        titles = [w.text() for w in popup.root.findChildren(QtWidgets.QLabel)]
        self.assertIn("Alpha", titles)
        closes = popup.root.findChildren(QtWidgets.QToolButton)
        self.assertTrue(any(b.objectName().startswith(
            "skeldarAnimPopupClose_") for b in closes))

    def test_the_card_button_is_lit_while_the_popup_stands(self):
        hubpop.open_popup("alpha")
        self.assertIn(("alpha", True), self.hub.painted)
        hubpop.close_popup("alpha")
        self.assertIn(("alpha", False), self.hub.painted)

    def test_a_second_open_of_the_same_section_is_the_same_popup(self):
        first = hubpop.open_popup("alpha")
        self.assertIs(hubpop.open_popup("alpha"), first)
        self.assertEqual(len(self.builds), 1)

    def test_a_header_only_section_has_no_popup(self):
        with self.assertRaises(KeyError):
            hubpop.open_popup("hotkeys")

    def test_no_viewport_says_so_and_opens_nothing(self):
        with mock.patch.object(hubpop, "active_panel", lambda: None):
            self.assertIsNone(hubpop.open_popup("alpha"))
        self.assertTrue(any("no 3D view" in m for m in self.hub.said))
        self.assertFalse(hubpop.is_open("alpha"))


class Placement(Seams):

    def test_the_default_place_is_inside_the_viewport_top_right(self):
        popup = hubpop.open_popup("alpha")
        x, y = popup.root.x(), popup.root.y()
        self.assertGreaterEqual(x, VIEW[0])
        self.assertLessEqual(x + popup.root.width(), VIEW[0] + VIEW[2])
        self.assertGreaterEqual(y, VIEW[1])

    def test_a_second_popup_cascades_from_the_first(self):
        first = hubpop.open_popup("alpha")
        second = hubpop.open_popup("beta")
        self.assertNotEqual((first.root.x(), first.root.y()),
                            (second.root.x(), second.root.y()))

    def test_the_popup_follows_its_viewport(self):
        popup = hubpop.open_popup("alpha")
        before = (popup.root.x() - VIEW[0], popup.root.y() - VIEW[1])
        moved = (VIEW[0] + 200, VIEW[1] + 90, VIEW[2], VIEW[3])
        with mock.patch.object(hubpop, "_gl_rect", lambda panel: moved):
            popup.follow()
        self.assertEqual((popup.root.x() - moved[0],
                          popup.root.y() - moved[1]), before)

    def test_it_hides_while_its_panel_is_not_visible_and_shows_again(self):
        popup = hubpop.open_popup("alpha")
        with mock.patch.object(hubpop, "model_panels", lambda: []):
            popup.follow()
        self.assertTrue(popup.hidden)
        popup.follow()                  # the panel is visible again (setUp)
        self.assertFalse(popup.hidden)

    def test_a_drag_is_clamped_to_the_viewport_and_remembered(self):
        popup = hubpop.open_popup("alpha")
        popup._grab((popup.root.x() + 10, popup.root.y() + 5))
        popup._drag((-5000, 9000))
        self.assertEqual(popup.root.x(), VIEW[0])
        self.assertEqual(popup.root.y() + popup.root.height(),
                         VIEW[1] + VIEW[3])
        popup._drop()
        self.assertEqual(self.cmds.vars.get("skeldarHubPopupPos_alpha"),
                         rules.encode_offset(popup.offset))

    def test_a_drag_inside_the_viewport_lands_under_the_pointer(self):
        popup = hubpop.open_popup("alpha")
        popup._grab((popup.root.x() + 10, popup.root.y() + 5))
        popup._drag((VIEW[0] + 300 + 10, VIEW[1] + 200 + 5))
        self.assertEqual((popup.root.x(), popup.root.y()),
                         (VIEW[0] + 300, VIEW[1] + 200))

    def test_a_drop_without_a_drag_saves_nothing(self):
        popup = hubpop.open_popup("alpha")
        popup._drop()
        self.assertNotIn("skeldarHubPopupPos_alpha", self.cmds.vars)


class TitleMouse(Seams):
    """The title row's real mouse events, sent to the widget."""

    def mouse(self, widget, kind, local, global_pt, buttons):
        event = QtGui.QMouseEvent(
            kind, QtCore.QPointF(*local), QtCore.QPointF(*global_pt),
            QtCore.Qt.LeftButton, buttons, QtCore.Qt.NoModifier)
        QtWidgets.QApplication.sendEvent(widget, event)

    def test_press_move_release_drags_the_popup_through_its_title(self):
        popup = hubpop.open_popup("alpha")
        title = popup.title
        start = (popup.root.x() + 40, popup.root.y() + 8)
        self.mouse(title, QtCore.QEvent.MouseButtonPress, (40, 8), start,
                   QtCore.Qt.LeftButton)
        target = (VIEW[0] + 250 + 40, VIEW[1] + 120 + 8)
        self.mouse(title, QtCore.QEvent.MouseMove, (40, 8), target,
                   QtCore.Qt.LeftButton)
        self.assertEqual((popup.root.x(), popup.root.y()),
                         (VIEW[0] + 250, VIEW[1] + 120))
        self.mouse(title, QtCore.QEvent.MouseButtonRelease, (40, 8), target,
                   QtCore.Qt.NoButton)
        self.assertIsNone(popup.grab)
        self.assertIn("skeldarHubPopupPos_alpha", self.cmds.vars)

    def test_a_move_without_the_button_does_nothing(self):
        popup = hubpop.open_popup("alpha")
        before = (popup.root.x(), popup.root.y())
        self.mouse(popup.title, QtCore.QEvent.MouseMove, (5, 5), (9999, 9999),
                   QtCore.Qt.NoButton)
        self.assertEqual((popup.root.x(), popup.root.y()), before)


class Memory(Seams):

    def test_the_open_sections_are_remembered_in_order(self):
        hubpop.open_popup("beta")
        hubpop.open_popup("alpha")
        self.assertEqual(self.cmds.vars["skeldarHubPopups"], "beta,alpha")

    def test_closing_forgets_and_destroying_keeps_the_memory(self):
        hubpop.open_popup("alpha")
        hubpop.destroy_all(forget=False)
        self.assertEqual(self.cmds.vars["skeldarHubPopups"], "alpha")
        self.assertFalse(hubpop.is_open("alpha"))
        hubpop.open_popup("alpha")
        hubpop.close_popup("alpha")
        self.assertEqual(self.cmds.vars["skeldarHubPopups"], "")

    def test_a_restore_reopens_what_was_remembered_at_its_place(self):
        popup = hubpop.open_popup("alpha")
        popup._grab((popup.root.x() + 1, popup.root.y() + 1))
        popup._drag((VIEW[0] + 333, VIEW[1] + 111))
        popup._drop()
        remembered = popup.offset
        hubpop.destroy_all(forget=False)
        hubpop.restore_later()
        self.run_deferred()
        again = hubpop._state()["popups"].get("alpha")
        self.assertIsNotNone(again)
        self.assertEqual(rules.decode_offset(
            self.cmds.vars["skeldarHubPopupPos_alpha"]), remembered)
        self.assertEqual(again.offset, remembered)
        self.assertEqual((again.root.x(), again.root.y()),
                         rules.origin_of(remembered, VIEW, again.root.width(),
                                         again.root.height(), 1.0))

    def test_a_restore_skips_a_section_the_hub_no_longer_has(self):
        self.cmds.vars["skeldarHubPopups"] = "gone,alpha"
        hubpop.restore_later()
        self.run_deferred()
        self.assertEqual(hubpop.open_keys(), ["alpha"])

    def test_a_popup_opened_again_comes_back_at_its_remembered_place(self):
        popup = hubpop.open_popup("alpha")
        popup._grab((popup.root.x() + 1, popup.root.y() + 1))
        popup._drag((VIEW[0] + 400, VIEW[1] + 150))
        popup._drop()
        remembered = popup.offset
        hubpop.close_popup("alpha")
        again = hubpop.open_popup("alpha")
        self.assertEqual(again.offset, remembered)


    def test_adopt_destroys_the_old_popups_and_queues_the_restore(self):
        hubpop.open_popup("alpha")
        hubpop.adopt()
        self.assertFalse(hubpop.is_open("alpha"))
        self.assertEqual(len(self.cmds.deferred_calls), 1)
        self.run_deferred()
        self.assertTrue(hubpop.is_open("alpha"))


class Toggle(Seams):

    def test_toggle_opens_then_closes(self):
        self.assertTrue(hubpop.toggle("alpha"))
        self.assertFalse(hubpop.toggle("alpha"))
        self.assertFalse(hubpop.is_open("alpha"))


class Roll(TitleMouse):
    """Rolling up to the title row and back (2026-10-09): the roll button, a
    click on the name, a drag that is not a click, the memory, the size."""

    def test_rolled_up_the_popup_is_its_title_row(self):
        popup = hubpop.open_popup("alpha")
        expanded = popup.root.height()
        popup.toggle_roll()
        self.assertTrue(popup.collapsed)
        self.assertTrue(popup.scroll.isHidden())
        self.assertEqual(popup.root.height(), popup._chrome())
        self.assertLess(popup.root.height(), expanded)
        popup.toggle_roll()
        self.assertFalse(popup.collapsed)
        self.assertEqual(popup.root.height(), expanded)

    def test_the_roll_button_toggles(self):
        popup = hubpop.open_popup("alpha")
        popup.roll.click()
        self.assertTrue(popup.collapsed)
        popup.roll.click()
        self.assertFalse(popup.collapsed)

    def test_a_click_on_the_name_toggles_and_a_drag_does_not(self):
        popup = hubpop.open_popup("alpha")
        title = popup.title
        start = (popup.root.x() + 40, popup.root.y() + 8)
        self.mouse(title, QtCore.QEvent.MouseButtonPress, (40, 8), start,
                   QtCore.Qt.LeftButton)
        self.mouse(title, QtCore.QEvent.MouseButtonRelease, (40, 8), start,
                   QtCore.Qt.NoButton)
        self.assertTrue(popup.collapsed)
        moved = (start[0] + 120, start[1] + 60)
        self.mouse(title, QtCore.QEvent.MouseButtonPress, (40, 8), start,
                   QtCore.Qt.LeftButton)
        self.mouse(title, QtCore.QEvent.MouseMove, (160, 68), moved,
                   QtCore.Qt.LeftButton)
        self.mouse(title, QtCore.QEvent.MouseButtonRelease, (160, 68), moved,
                   QtCore.Qt.NoButton)
        self.assertTrue(popup.collapsed)           # still rolled up: no click

    def test_the_roll_is_remembered_and_restored(self):
        popup = hubpop.open_popup("alpha")
        popup.toggle_roll()
        self.assertEqual(self.cmds.vars["skeldarHubPopupCollapsed_alpha"],
                         "1")
        hubpop.destroy_all(forget=False)
        again = hubpop.open_popup("alpha")
        self.assertTrue(again.collapsed)
        self.assertTrue(again.scroll.isHidden())
        again.toggle_roll()
        self.assertEqual(self.cmds.vars["skeldarHubPopupCollapsed_alpha"],
                         "0")

    def test_the_outline_paints_without_error(self):
        popup = hubpop.open_popup("alpha")
        image = popup.root.grab().toImage()
        self.assertFalse(image.isNull())
        popup.toggle_roll()
        self.assertFalse(popup.root.grab().toImage().isNull())


def settle(test, done, timeout_ms=3000):
    """Run the Qt loop until `done()` (an animation's ticks, its finish)."""
    deadline = time.time() + timeout_ms / 1000.0
    while not done() and time.time() < deadline:
        QtWidgets.QApplication.processEvents()
        time.sleep(0.005)
    test.assertTrue(done(), "the animation did not finish in time")


class Motion(Seams):
    """The popup's look and motion (2026-10-09, the animator's review): a
    see-through window, a shorter roll, a capped height, the open and close
    fade, the roll's slide, the card light under the mouse."""

    def test_the_window_is_see_through_so_the_corners_show_the_viewport(self):
        popup = hubpop.open_popup("alpha")
        self.assertTrue(popup.root.testAttribute(
            QtCore.Qt.WA_TranslucentBackground))
        image = popup.root.grab().toImage()
        self.assertFalse(image.isNull())
        #  the outermost pixel is outside the card's rounded corner
        self.assertEqual(image.pixelColor(0, 0).alpha(), 0)

    def test_the_scroll_area_and_its_viewport_paint_nothing_of_their_own(self):
        popup = hubpop.open_popup("alpha")
        self.assertFalse(popup.scroll.viewport().autoFillBackground())
        self.assertEqual(popup.scroll.objectName(),
                         "skeldarAnimPopupScroll_" + popup.scope.tag)

    def test_an_expanded_popup_is_never_taller_than_the_cap(self):
        popup = hubpop.open_popup("alpha")
        tall = QtWidgets.QWidget()
        tall.setFixedHeight(900)
        popup.body.addWidget(tall)
        popup._fit()
        self.assertLessEqual(popup.root.height(), rules.MAX_HEIGHT)
        self.assertGreater(popup.root.height(), popup._chrome())

    def test_the_open_fades_in_and_settles_at_full_opacity(self):
        popup = hubpop.open_popup("alpha", animate=True)
        self.assertLess(popup.root.windowOpacity(), 1.0)
        settle(self, lambda: popup._open_anim is None)
        self.assertAlmostEqual(popup.root.windowOpacity(), 1.0)
        self.assertEqual(popup.slide, 0.0)

    def test_the_close_fades_out_and_leaves_the_list_at_once(self):
        popup = hubpop.open_popup("alpha")
        self.assertTrue(hubpop.close_popup("alpha", animate=True))
        self.assertFalse(hubpop.is_open("alpha"))
        self.assertIn(popup, hubpop._state()["closing"])
        self.assertTrue(popup.alive())              # still on screen, fading
        self.assertTrue(popup.root.testAttribute(
            QtCore.Qt.WA_TransparentForMouseEvents))
        settle(self, lambda: popup not in hubpop._state()["closing"])
        self.assertFalse(popup.alive())
        self.assertEqual(hubpop._state()["closing"], [])

    def test_a_close_during_a_roll_or_an_open_leaves_no_animation(self):
        popup = hubpop.open_popup("alpha", animate=True)
        popup.set_collapsed(True, animate=True)
        hubpop.close_popup("alpha", animate=True)
        settle(self, lambda: popup not in hubpop._state()["closing"])
        self.assertIsNone(popup._roll_anim)
        self.assertIsNone(popup._open_anim)
        self.assertIsNone(popup._fade)

    def test_the_roll_slides_down_to_the_name_and_back_to_full(self):
        popup = hubpop.open_popup("alpha")
        expanded = popup.root.height()
        popup.set_collapsed(True, animate=True)
        self.assertTrue(popup.collapsed)
        self.assertIsNotNone(popup._roll_anim)
        settle(self, lambda: popup._roll_anim is None)
        self.assertEqual(popup.root.height(), popup._chrome())
        self.assertTrue(popup.scroll.isHidden())
        popup.set_collapsed(False, animate=True)
        self.assertFalse(popup.scroll.isHidden())   # shown while it opens
        settle(self, lambda: popup._roll_anim is None)
        self.assertEqual(popup.root.height(), expanded)

    def test_a_drag_during_an_open_takes_the_window_at_once(self):
        popup = hubpop.open_popup("alpha", animate=True)
        popup._grab((popup.root.x() + 1, popup.root.y() + 1))
        self.assertIsNone(popup._open_anim)
        self.assertEqual(popup.root.windowOpacity(), 1.0)
        self.assertEqual(popup.slide, 0.0)

    def test_the_card_light_comes_up_under_the_mouse_and_goes_down(self):
        popup = hubpop.open_popup("alpha")
        QtWidgets.QApplication.sendEvent(
            popup.root, QtCore.QEvent(QtCore.QEvent.Enter))
        settle(self, lambda: popup.frame.level >= 1.0)
        self.assertEqual(popup.frame.level, 1.0)
        QtWidgets.QApplication.sendEvent(
            popup.root, QtCore.QEvent(QtCore.QEvent.Leave))
        settle(self, lambda: popup.frame.level <= 0.0)
        self.assertEqual(popup.frame.level, 0.0)

    def test_a_lit_popup_paints_its_ring_and_a_plain_one_its_outline(self):
        popup = hubpop.open_popup("alpha")
        popup.set_light(True)
        self.assertFalse(popup.root.grab().toImage().isNull())
        popup.set_light(False)
        self.assertFalse(popup.root.grab().toImage().isNull())

    def test_destroying_with_animations_running_is_quiet(self):
        popup = hubpop.open_popup("alpha", animate=True)
        popup.set_collapsed(True, animate=True)
        popup.set_light(True, animate=True)
        hubpop.destroy_all(forget=False)
        self.assertFalse(popup.alive())
        self.assertIsNone(popup._open_anim)
        self.assertIsNone(popup._roll_anim)
        self.assertIsNone(popup._light_anim)


class Resize(TitleMouse):
    """The edges of a popup (2026-10-09): a rolled-up popup as wide as its name,
    the edges dragged to resize, a double click giving a side back, the sizes
    remembered, the far edges kept inside the viewport."""

    def drag_grip(self, grip, dx, dy):
        centre = QtCore.QPoint(grip.width() // 2, grip.height() // 2)
        start = grip.mapToGlobal(centre)
        end = QtCore.QPoint(start.x() + dx, start.y() + dy)
        local = (centre.x() + dx, centre.y() + dy)
        self.mouse(grip, QtCore.QEvent.MouseButtonPress, (centre.x(), centre.y()),
                   (start.x(), start.y()), QtCore.Qt.LeftButton)
        self.mouse(grip, QtCore.QEvent.MouseMove, local, (end.x(), end.y()),
                   QtCore.Qt.LeftButton)
        self.mouse(grip, QtCore.QEvent.MouseButtonRelease, local,
                   (end.x(), end.y()), QtCore.Qt.NoButton)

    def move_to(self, popup, x, y):
        popup._grab((popup.root.x() + 1, popup.root.y() + 1))
        popup._drag((x, y))
        popup._drop()

    def test_a_popup_has_three_edge_strips(self):
        popup = hubpop.open_popup("alpha")
        self.assertEqual(len(popup.grips), 3)

    def test_rolled_up_the_popup_is_as_wide_as_its_name(self):
        popup = hubpop.open_popup("alpha")
        popup.toggle_roll()
        self.assertEqual(popup.root.width(), popup._title_width())
        self.assertEqual(popup.root.height(), popup._chrome())
        self.assertLess(popup.root.width(), rules.WIDTH)

    def test_a_roll_up_slides_the_width_down_to_the_name(self):
        popup = hubpop.open_popup("alpha")
        popup.set_collapsed(True, animate=True)
        settle(self, lambda: popup._roll_anim is None)
        self.assertEqual(popup.root.width(), popup._title_width())

    def test_the_right_edge_drag_widens_the_popup_and_is_remembered(self):
        popup = hubpop.open_popup("alpha")
        self.move_to(popup, VIEW[0] + 100, VIEW[1] + 100)
        before = popup.root.width()
        self.drag_grip(popup.grips[0], 60, 0)
        self.assertEqual(popup.root.width(), before + 60)
        self.assertEqual(popup.user_w, before + 60)
        self.assertIsNone(popup.user_h)
        self.assertEqual(rules.decode_pair(
            self.cmds.vars["skeldarHubPopupSize_alpha"]), (before + 60, None))

    def test_the_bottom_edge_drag_sets_the_height(self):
        popup = hubpop.open_popup("alpha")
        self.move_to(popup, VIEW[0] + 100, VIEW[1] + 100)
        before = popup.root.height()
        self.drag_grip(popup.grips[1], 0, 80)
        self.assertEqual(popup.root.height(), before + 80)
        self.assertEqual(popup.user_h, before + 80)
        self.assertEqual(rules.decode_pair(
            self.cmds.vars["skeldarHubPopupSize_alpha"])[1], before + 80)

    def test_the_corner_drag_sets_both_sides(self):
        popup = hubpop.open_popup("alpha")
        self.move_to(popup, VIEW[0] + 100, VIEW[1] + 100)
        width, height = popup.root.width(), popup.root.height()
        self.drag_grip(popup.grips[2], 40, 30)
        self.assertEqual((popup.root.width(), popup.root.height()),
                         (width + 40, height + 30))

    def test_the_popup_stays_inside_the_viewport_while_it_is_widened(self):
        popup = hubpop.open_popup("alpha")
        self.move_to(popup, VIEW[0] + 100, VIEW[1] + 100)
        self.drag_grip(popup.grips[0], 5000, 0)
        self.assertLessEqual(popup.root.x() + popup.root.width(),
                             VIEW[0] + VIEW[2] - rules.MARGIN)

    def test_the_popup_cannot_be_dragged_narrower_than_its_minimum(self):
        popup = hubpop.open_popup("alpha")
        self.move_to(popup, VIEW[0] + 100, VIEW[1] + 100)
        self.drag_grip(popup.grips[0], -2000, 0)
        self.assertGreaterEqual(popup.root.width(), rules.MIN_RESIZE_W)

    def test_a_rolled_up_popup_widens_only_its_bar(self):
        popup = hubpop.open_popup("alpha")
        self.move_to(popup, VIEW[0] + 100, VIEW[1] + 100)
        popup.toggle_roll()
        width, height = popup.root.width(), popup.root.height()
        self.drag_grip(popup.grips[0], 80, 0)
        self.assertEqual(popup.root.width(), width + 80)
        self.assertEqual(popup.root.height(), height)
        self.assertIsNone(popup.user_w)
        self.assertEqual(popup.bar_w, width + 80)
        self.assertEqual(rules.decode_single(
            self.cmds.vars["skeldarHubPopupBar_alpha"]), width + 80)

    def test_a_double_click_gives_the_side_back_to_automatic(self):
        popup = hubpop.open_popup("alpha")
        self.move_to(popup, VIEW[0] + 100, VIEW[1] + 100)
        automatic = popup.root.width()
        self.drag_grip(popup.grips[0], 60, 0)
        self.assertIsNotNone(popup.user_w)
        grip = popup.grips[0]
        centre = QtCore.QPoint(grip.width() // 2, grip.height() // 2)
        at = grip.mapToGlobal(centre)
        self.mouse(grip, QtCore.QEvent.MouseButtonDblClick,
                   (centre.x(), centre.y()), (at.x(), at.y()),
                   QtCore.Qt.LeftButton)
        self.assertIsNone(popup.user_w)
        self.assertEqual(popup.root.width(), automatic)

    def test_the_sizes_are_remembered_across_a_restart(self):
        popup = hubpop.open_popup("alpha")
        self.move_to(popup, VIEW[0] + 100, VIEW[1] + 100)
        self.drag_grip(popup.grips[0], 60, 0)
        self.drag_grip(popup.grips[1], 0, 50)
        width, height = popup.root.width(), popup.root.height()
        hubpop.destroy_all(forget=False)
        again = hubpop.open_popup("alpha")
        self.assertEqual((again.root.width(), again.root.height()),
                         (width, height))
        self.assertEqual(again.user_w, width)
        self.assertEqual(again.user_h, height)


class Card(unittest.TestCase):
    """The popout button on a hub card's header (maya_hubqt.Card)."""

    def setUp(self):
        self.app = _app()

    def test_the_card_has_a_popout_button_before_its_chevron(self):
        clicks = []
        card = hubqt.Card("alpha", "Alpha", "user", "#f0a26b", "#4a3322",
                          1.0, on_popout=clicks.append)
        self.assertEqual(card.popout.objectName(),
                         "skeldarHubCardPopout_alpha")
        row = card.header.layout()
        index = {row.itemAt(i).widget(): i for i in range(row.count())
                 if row.itemAt(i).widget() is not None}
        self.assertLess(index[card.popout], index[card.chevron])

    def test_a_click_on_the_button_reports_the_section(self):
        clicks = []
        card = hubqt.Card("alpha", "Alpha", "user", "#f0a26b", "#4a3322",
                          1.0, on_popout=clicks.append)
        card.popout.click()
        self.assertEqual(clicks, ["alpha"])

    def test_the_button_lights_while_its_popup_stands(self):
        card = hubqt.Card("alpha", "Alpha", "user", "#f0a26b", "#4a3322",
                          1.0, on_popout=lambda k: None)
        self.assertFalse(bool(card.popout.property("skPopped")))
        card.set_popped(True)
        self.assertTrue(bool(card.popout.property("skPopped")))
        card.set_popped(False)
        self.assertFalse(bool(card.popout.property("skPopped")))

    def test_a_card_without_a_callback_has_the_button_still(self):
        card = hubqt.Card("alpha", "Alpha", "user", "#f0a26b", "#4a3322",
                          1.0)
        card.popout.click()
        self.assertEqual(card.popout.objectName(),
                         "skeldarHubCardPopout_alpha")


class RootOverlap(unittest.TestCase):
    """A drop released over a popup is a drop on the hub (over_hub)."""

    def test_a_popup_root_counts_as_the_hub(self):
        self.assertTrue(hubstyle.over_hub(
            [hubstyle.POPUP_ROOT + "_hubcopy3", "skeldarHubCard_colour"]))

    def test_a_plain_viewport_widget_does_not(self):
        self.assertFalse(hubstyle.over_hub(["modelPanel4Window", "x"]))


if __name__ == "__main__":
    unittest.main()
