"""The AT bar's strip (`maya_atbar.bar`) offscreen: its painted buttons and their motion, the blend tracks,
the select sets' cells, the Blend pop-up of the compact bar, the flow layout, every button wired to its
tool, and where the strip stands (its own control, the Time Bar's top row, the F row).

`bar.cmds` is a fake and every tool of `core` a MagicMock for the length of a test.
"""

import os
import sys
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import maya
from PySide6 import QtCore, QtGui, QtWidgets
from shiboken6 import getCppPointer

from maya_atbar import CONTROL, TIMEBAR, bar, core

Qt = QtCore.Qt

#  the tools the strip calls; `sets_grid` and `_state` stay real
TOOLS = ("nudge", "inbetween", "save_recovery", "install_recovery_check", "selection_sets", "set_colour",
         "set_size", "delete_selection_set", "has_set", "deselect_set", "select_set", "create_selection_set",
         "update_selection_set", "rename_selection_set", "paint_set", "temp_controls_active", "temp_pivot_active",
         "motion_trails_exist", "copy_animation", "paste_animation", "copy_pose", "paste_pose", "mirror_pose",
         "align_objects", "euler_filter", "snapshot_default_pose", "toggle_temp_controls", "toggle_temp_pivot",
         "motion_trail_click", "add_motion_trail", "clear_motion_trail", "clear_all_motion_trails",
         "set_viewport_suspended", "message", "open_recovery_folder", "select_opposite", "copy_relationship",
         "paste_relationship", "paste_world_space", "copy_world_space", "enum_attrs", "selection", "space_switch",
         "add_bookmark", "go_to_bookmark", "delete_bookmark_here", "clear_bookmarks", "bookmarks",
         "select_rig_controls", "select_animated", "key_selection", "delete_static_channels", "bake_selection",
         "reset_to_default_pose", "clear_default_pose")


class BarCmds(object):
    def __init__(self, dpi=1.0):
        self.dpi = dpi
        self.optionvars = {}
        self.warnings = []
        self.workspace = []
        self.times = []

    def mayaDpiSetting(self, **kw):
        if isinstance(self.dpi, Exception):
            raise self.dpi
        return self.dpi

    def optionVar(self, q=None, exists=None, iv=None, intValue=None):
        if exists is not None:
            return exists in self.optionvars
        if q is not None:
            return self.optionvars[q]
        pair = iv or intValue
        self.optionvars[pair[0]] = pair[1]

    def warning(self, text):
        self.warnings.append(text)

    def workspaceControl(self, name, **kw):
        self.workspace.append((name, kw))

    def currentTime(self, t, **kw):
        self.times.append(t)


def mouse(kind, x, y=5.0, button=Qt.LeftButton, buttons=None):
    if buttons is None:
        buttons = Qt.NoButton if kind == QtCore.QEvent.MouseButtonRelease else button
    point = QtCore.QPointF(x, y)
    return QtGui.QMouseEvent(kind, point, point, button, buttons, Qt.NoModifier)


def press(x, y=5.0, button=Qt.LeftButton):
    return mouse(QtCore.QEvent.MouseButtonPress, x, y, button)


def move(x, y=5.0, held=True):
    return mouse(QtCore.QEvent.MouseMove, x, y, Qt.NoButton, Qt.LeftButton if held else Qt.NoButton)


def release(x, y=5.0, button=Qt.LeftButton):
    return mouse(QtCore.QEvent.MouseButtonRelease, x, y, button)


def enter():
    return QtGui.QEnterEvent(QtCore.QPointF(1, 1), QtCore.QPointF(1, 1), QtCore.QPointF(1, 1))


def pixel(widget, x, y):
    return widget.grab().toImage().pixelColor(x, y).name()


class Menus(object):
    """QMenu.exec stood in for: each menu shown read as [(label, submenu or None)] with where it was asked
    to show, and the rows in `picks` chosen while it shows (a submenu dies with the call that built it)."""

    def __init__(self):
        self.shown = []
        self.picks = []

    def __call__(self, menu, where=None, *rest):
        self.shown.append((self.tree(menu), where))
        picks, self.picks = self.picks, []
        for path in picks:
            self.action(menu, *path).trigger()

    #  submenus by their parent's children: QAction.menu() hands back wrappers that go dead in PySide6 6.8
    @staticmethod
    def submenus(menu):
        return {c.title(): c for c in menu.children() if isinstance(c, QtWidgets.QMenu)}

    @classmethod
    def tree(cls, menu):
        subs = cls.submenus(menu)
        return [(a.text(), cls.tree(subs[a.text()]) if a.text() in subs else None) for a in menu.actions()]

    @staticmethod
    def labels(tree):
        return [label for label, _sub in tree]

    @classmethod
    def action(cls, menu, *path):
        for label in path[:-1]:
            menu = cls.submenus(menu)[label]
        return [a for a in menu.actions() if a.text() == path[-1]][0]


class BarTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.cmds = BarCmds()
        self.tools = {name: mock.MagicMock(name=name) for name in TOOLS}
        for name in ("temp_controls_active", "temp_pivot_active", "motion_trails_exist", "has_set"):
            self.tools[name].return_value = False
        self.tools["selection_sets"].return_value = []
        self.tools["set_colour"].return_value = None
        self.tools["set_size"].return_value = 0
        self.tools["bookmarks"].return_value = []
        self.tools["enum_attrs"].return_value = {}
        self.tools["save_recovery"].return_value = "C:/r/shot_1.mb"
        self.menus = Menus()
        #  every QTimer.singleShot recorded, never left to fire into a later test after its widget is gone
        self.deferred = []
        for patch in (mock.patch.object(QtCore.QTimer, "singleShot",
                                        side_effect=lambda ms, fn: self.deferred.append(fn)),
                      mock.patch.object(bar, "cmds", self.cmds), mock.patch.multiple(core, **self.tools),
                      mock.patch.dict(core._state), mock.patch.object(bar.traceback, "print_exc"),
                      mock.patch.object(QtWidgets.QMenu, "exec", lambda menu, *a: self.menus(menu, *a)),
                      mock.patch.object(QtWidgets.QMenu, "exec_", lambda menu, *a: self.menus(menu, *a),
                                        create=True)):
            patch.start()
            self.addCleanup(patch.stop)
        self.widgets = []
        self.addCleanup(self._drop_widgets)

    def keep(self, widget):
        self.widgets.append(widget)
        return widget

    def _drop_widgets(self):
        for w in self.widgets:
            try:
                w.hide()
                w.setParent(None)
                w.deleteLater()
            except RuntimeError:
                pass
        QtWidgets.QApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)

    def later(self):
        """What QTimer.singleShot was asked to run next turn (recorded, not waited for)."""
        return self.deferred

    def at_once(self):
        patch = mock.patch.object(QtCore.QTimer, "singleShot", side_effect=lambda ms, fn: fn())
        patch.start()
        self.addCleanup(patch.stop)

    def modifiers(self, mods):
        patch = mock.patch.object(QtWidgets.QApplication, "keyboardModifiers", return_value=mods)
        patch.start()
        self.addCleanup(patch.stop)


# ---------------------------------------------------------------- helpers

class Helpers(BarTest):

    def test_the_ui_scale_is_maya_s_else_one(self):
        self.cmds.dpi = 1.5
        self.assertEqual(bar._ui(), 1.5)
        self.cmds.dpi = None
        self.assertEqual(bar._ui(), 1.0)
        self.cmds.dpi = RuntimeError("no ui")
        self.assertEqual(bar._ui(), 1.0)

    def test_the_clock_is_in_milliseconds(self):
        a = bar._now()
        b = bar._now()
        self.assertGreaterEqual(b, a)
        self.assertGreater(a, 0)

    def test_colours_mix_and_take_an_alpha_clamped(self):
        self.assertEqual(bar._mix("#000000", "#ffffff", 0.5).name(), "#808080")
        self.assertEqual(bar._mix("#102030", "#ffffff", -1).name(), "#102030")
        self.assertEqual(bar._mix("#102030", "#ffffff", 2).name(), "#ffffff")
        self.assertAlmostEqual(bar._alpha("#e07a36", 0.25).alphaF(), 0.25, places=2)
        self.assertEqual(bar._alpha("#e07a36", 3).alphaF(), 1.0)

    def test_the_pop_overshoots_and_lands(self):
        self.assertAlmostEqual(bar._back_out(0.0), 0.0)
        self.assertAlmostEqual(bar._back_out(1.0), 1.0)
        self.assertGreater(max(bar._back_out(u / 20.0) for u in range(21)), 1.0)

    def test_a_glyph_is_drawn_in_its_colour_once_per_size(self):
        bar._PIXMAPS.clear()
        pm = bar._glyph("mirror", "#ff0000", 16, 1.0)
        self.assertIs(bar._glyph("mirror", "#ff0000", 16, 1.0), pm)
        self.assertIsNot(bar._glyph("mirror", "#00ff00", 16, 1.0), pm)
        self.assertEqual((pm.width(), pm.height()), (16, 16))
        self.assertEqual(bar._glyph("mirror", "#ff0000", 16, 2.0).width(), 32)
        image = pm.toImage()
        inked = [image.pixelColor(x, y) for x in range(16) for y in range(16) if image.pixelColor(x, y).alpha() > 200]
        self.assertTrue(inked)
        self.assertTrue(all(c.red() > 200 and c.green() < 60 for c in inked))

    def test_the_chip_font_scales_with_the_ui(self):
        self.assertEqual(bar._chip_font(1.0).pixelSize(), 10)
        self.assertEqual(bar._chip_font(1.5).pixelSize(), 15)
        self.assertTrue(bar._chip_font(1.0).bold())

    def test_a_failing_tool_is_said_not_raised(self):
        def copy_animation():
            raise RuntimeError("boom")
        ran = []
        bar._safe(lambda *a, **k: ran.append((a, k)), 1, key=2)("clicked")
        self.assertEqual(ran, [((1,), {"key": 2})])
        bar._safe(copy_animation)()
        self.assertEqual(self.cmds.warnings, ["AT: copy_animation failed (see script editor)"])
        bar.traceback.print_exc.assert_called_once_with()

    def test_shift_and_an_event_s_position(self):
        self.modifiers(Qt.ShiftModifier | Qt.ControlModifier)
        self.assertTrue(bar._shift())
        self.assertEqual(bar._pos(press(12.5)), 12.5)
        self.assertEqual(bar._pos(mock.Mock(spec=["x"], x=lambda: 7)), 7)


class Driving(BarTest):

    def test_the_driver_ticks_what_moves_and_stops_at_rest(self):
        class Part(object):
            def __init__(self, busy):
                self.busy, self.updates = list(busy), 0

            def step(self, now):
                return self.busy.pop(0)

            def update(self):
                self.updates += 1

        class Gone(object):
            def step(self, now):
                raise RuntimeError("deleted")

        driver = bar.Driver()
        a, b = Part([True, False]), Part([False])
        for part in (a, b, Gone()):
            driver.kick(part)
        self.assertTrue(driver._timer.isActive())
        driver._tick()
        self.assertEqual(driver._busy, {a})
        self.assertTrue(driver._timer.isActive())
        driver._tick()
        self.assertEqual(driver._busy, set())
        self.assertFalse(driver._timer.isActive())
        self.assertEqual((a.updates, b.updates), (2, 1))


# ---------------------------------------------------------------- buttons

class Button(BarTest):

    def button(self, **kw):
        kw.setdefault("click", mock.MagicMock())
        return self.keep(bar.ATButton("mirror", bar.SPACE, "Mirror Pose: flip L/R\nRight click: more", **kw))

    def test_a_click_runs_its_tool_and_the_tip_names_it(self):
        tool = mock.MagicMock()
        btn = self.button(click=tool)
        btn.click()
        tool.assert_called_once_with()
        self.assertEqual(btn.accessibleName(), "Mirror Pose")
        self.assertEqual((btn.width(), btn.height()), (bar.FACE + 2 * bar.MARGIN,) * 2)

    def test_a_chip_is_as_wide_as_its_text(self):
        btn = self.button(text="BLEND", face=bar.COMPACT_FACE, pad=bar.COMPACT_PAD)
        advance = QtGui.QFontMetrics(bar._chip_font(1.0)).horizontalAdvance("BLEND")
        self.assertEqual(btn.width(), int(round(advance + 14 + 2 * bar.COMPACT_PAD)))
        self.assertEqual(btn.height(), bar.COMPACT_FACE + 2 * bar.COMPACT_PAD)
        self.assertFalse(btn.grab().isNull())

    def test_hover_lifts_it_and_settles(self):
        btn = self.button()
        with mock.patch.object(btn, "update") as update:
            btn.enterEvent(enter())
        update.assert_called()
        self.assertEqual(btn._goal, 1.0)
        self.assertTrue(btn.step(0.0))
        self.assertEqual(btn._hover, 0.0)
        self.assertTrue(btn.step(55.0))
        self.assertAlmostEqual(btn._hover, 1.0 - 2.718281828 ** -1.5, places=3)
        self.assertFalse(btn.step(5000.0))
        self.assertEqual(btn._hover, 1.0)
        btn.leaveEvent(QtCore.QEvent(QtCore.QEvent.Leave))
        self.assertEqual(btn._goal, 0.0)

    def test_hover_and_presses_go_through_the_bar_s_driver(self):
        driver = mock.MagicMock()
        btn = self.button(driver=driver, checkable=True)
        btn.enterEvent(enter())
        btn.mousePressEvent(press(5))
        btn.setChecked(True)
        self.assertEqual(driver.kick.call_count, 3)

    def test_a_press_flashes_and_a_toggle_pops_for_their_time(self):
        btn = self.button(checkable=True)
        with mock.patch.object(bar, "_now", return_value=1000.0):
            btn.mousePressEvent(press(5))
            btn.mousePressEvent(press(5, button=Qt.RightButton))
            btn.setChecked(True)
        self.assertEqual((btn._flash_t, btn._pop_t), (1000.0, 1000.0))
        self.assertTrue(btn.step(1000.0 + bar.FLASH_MS - 1))
        self.assertTrue(btn.step(1000.0 + bar.POP_MS - 1))
        self.assertFalse(btn.step(1000.0 + bar.POP_MS + 1))

    def test_a_checked_button_wears_the_accent_tint_and_a_press_flashes_the_accent(self):
        btn = self.button(checkable=True)
        plain = pixel(btn, 5, 15)
        btn.setChecked(True)
        btn._pop_t = None
        self.assertEqual(pixel(btn, 5, 15), bar.ACCENT_TINT)
        self.assertNotEqual(plain, bar.ACCENT_TINT)
        btn.setChecked(False)
        btn._pop_t = None
        with mock.patch.object(bar, "_now", return_value=5000.0):
            btn._flash_t = 5000.0
            self.assertEqual(pixel(btn, 5, 15), bar.ACCENT)
        btn._flash_t = None
        btn._hover = 1.0
        self.assertFalse(btn.grab().isNull())

    def test_its_menu_shows_rows_separators_and_submenus(self):
        first, second = mock.MagicMock(), mock.MagicMock()
        entries = lambda: [("First", first), None, ("More", [("Second", second)])]        # noqa: E731
        btn = self.button(click="menu", menu=entries)
        self.menus.picks = [("First",), ("More", "Second")]
        btn.click()
        tree, where = self.menus.shown[-1]
        self.assertEqual(tree, [("First", None), ("", None), ("More", [("Second", None)])])
        self.assertEqual(where, btn.mapToGlobal(QtCore.QPoint(0, btn.height())))
        first.assert_called_once_with()
        second.assert_called_once_with()
        btn.customContextMenuRequested.emit(QtCore.QPoint(3, 4))
        self.assertEqual(self.menus.shown[-1][1], btn.mapToGlobal(QtCore.QPoint(3, 4)))
        self.assertEqual(btn.contextMenuPolicy(), Qt.CustomContextMenu)


# ---------------------------------------------------------------- blend tracks

class Session(object):
    made = []

    def __init__(self, mode):
        self.mode, self.applied, self.finished = mode, [], False
        Session.made.append(self)

    def apply(self, value):
        self.applied.append(value)

    def finish(self):
        self.finished = True


class Slider(BarTest):

    def setUp(self):
        super(Slider, self).setUp()
        Session.made = []
        patch = mock.patch.object(core, "SliderSession", Session)
        patch.start()
        self.addCleanup(patch.stop)
        self.s = self.keep(bar.BlendSlider("TW", "TW", bar.BLEND, "Tweener"))

    def test_its_marks_run_from_minus_to_plus_150_around_the_centre(self):
        pts = self.s._points()
        self.assertEqual(len(pts), 2 * len(bar.SLIDER_PRESETS) + 1)
        self.assertEqual(pts[len(pts) // 2], (self.s.width() / 2.0, 0.0))
        self.assertEqual([v for _x, v in pts], sorted(v for _x, v in pts))
        self.assertEqual((pts[0][1], pts[-1][1]), (-150.0, 150.0))
        self.assertEqual(self.s.size(), QtCore.QSize(214, bar.FACE + 2 * bar.MARGIN))

    def test_a_value_and_its_place_round_trip(self):
        for v in (-150, -100, -12.5, 0, 7, 50, 120, 150):
            self.assertAlmostEqual(self.s._value_at(self.s._x_of(v)), v, places=6)
        pts = self.s._points()
        self.assertEqual(self.s._x_of(999), pts[-1][0])
        self.assertEqual(self.s._x_of(-999), pts[0][0])
        self.assertEqual(self.s._value_at(-50), -150.0)
        self.assertEqual(self.s._value_at(10000), 150.0)

    def test_a_mark_is_found_near_the_cursor_but_never_the_centre(self):
        self.assertEqual(self.s._dot_at(self.s._x_of(50) + 3), 50.0)
        self.assertIsNone(self.s._dot_at(self.s.width() / 2.0))
        self.assertIsNone(self.s._dot_at(self.s._points()[-1][0] + 10))

    def test_a_drag_scrubs_one_session_and_finishes_it_on_release(self):
        cx = self.s.width() / 2.0
        self.s.mousePressEvent(press(cx))
        self.s.mouseMoveEvent(move(cx + 2))
        self.assertEqual(Session.made, [])
        self.s.mouseMoveEvent(move(self.s._x_of(100)))
        self.s.mouseMoveEvent(move(self.s._x_of(-40)))
        session = Session.made[0]
        self.assertEqual(len(Session.made), 1)
        self.assertEqual(session.mode, "TW")
        self.assertAlmostEqual(session.applied[0], 100.0, places=6)
        self.assertAlmostEqual(session.applied[1], -40.0, places=6)
        self.assertAlmostEqual(self.s._value, -40.0, places=6)
        self.s.mouseReleaseEvent(release(self.s._x_of(-40)))
        self.assertTrue(session.finished)
        self.assertEqual((self.s._session, self.s._value, self.s._press_x), (None, None, None))

    def test_a_click_on_a_mark_applies_its_preset(self):
        x = self.s._x_of(-15)
        self.s.mousePressEvent(press(x))
        self.s.mouseReleaseEvent(release(x))
        self.assertEqual(Session.made[0].applied, [-15.0])
        self.assertTrue(Session.made[0].finished)

    def test_a_click_off_the_marks_or_a_release_without_press_does_nothing(self):
        self.s.mouseReleaseEvent(release(10))
        cx = self.s.width() / 2.0
        self.s.mousePressEvent(press(cx, button=Qt.RightButton))
        self.s.mouseReleaseEvent(release(cx))
        self.s.mousePressEvent(press(cx))
        self.s.mouseReleaseEvent(release(cx))
        self.assertEqual(Session.made, [])

    def test_the_mark_under_the_cursor_lights_and_goes_out_on_leave(self):
        self.s.mouseMoveEvent(move(self.s._x_of(5), held=False))
        self.assertEqual(self.s._hover, 5.0)
        self.s.leaveEvent(QtCore.QEvent(QtCore.QEvent.Leave))
        self.assertIsNone(self.s._hover)

    def test_a_session_that_cannot_start_does_not_break_the_drag(self):
        with mock.patch.object(core, "SliderSession", side_effect=RuntimeError("no keys")):
            self.s.mousePressEvent(press(10))
            self.s.mouseMoveEvent(move(60))
            self.s.mouseReleaseEvent(release(60))
        self.assertIsNone(self.s._session)
        bar.traceback.print_exc.assert_called()

    def test_while_dragging_the_chip_turns_accent_and_shows_the_value(self):
        idle = pixel(self.s, 93, 15)
        self.s._value = 100.0
        self.s._hover = 50.0
        self.assertEqual(pixel(self.s, 93, 15), bar.ACCENT_TINT)
        self.assertEqual(idle, bar.CARD)


# ---------------------------------------------------------------- select sets

class Sets(BarTest):

    def setUp(self):
        super(Sets, self).setUp()
        core.selection_sets.return_value = [("a", "a"), ("b", "b")]
        core.set_colour.side_effect = {"b": "#123456"}.get
        core.set_size.side_effect = {"a": 3, "b": 5}.get
        self.anchor = self.keep(QtWidgets.QWidget())
        self.anchor.resize(40, 30)
        geo = QtWidgets.QApplication.primaryScreen().availableGeometry()
        self.anchor.move(geo.left() + 50, geo.bottom() - 60)
        self.anchor.show()
        self.popup = self.keep(bar.SetsPopup(self.anchor, 1.0))

    def place(self, cell):
        return self.popup.grid.getItemPosition(self.popup.grid.indexOf(cell))[:2]

    def test_a_cell_per_set_and_one_that_makes_a_set(self):
        cells = self.popup.cells
        self.assertEqual([c.label for c in cells], ["a", "b", "New from selection"])
        self.assertEqual([c.colour for c in cells], [bar.POSE, "#123456", bar.MUTED])
        self.assertEqual([c.count for c in cells], [3, 5, None])
        self.assertEqual([c.new for c in cells], [False, False, True])
        self.assertEqual([self.place(c) for c in cells], [(0, 0), (0, 1), (0, 2)])
        self.assertTrue(cells[0].toolTip().startswith("a: 3 objects"))
        self.assertTrue(cells[2].toolTip().startswith("Make a select set"))

    def test_it_opens_above_the_button_with_the_nearest_cell_popping_first(self):
        self.popup.open_at()
        corner = self.anchor.mapToGlobal(QtCore.QPoint(0, 0))
        self.assertTrue(self.popup.isVisible())
        self.assertTrue(self.popup._above)
        self.assertEqual(self.popup.y(), corner.y() - self.popup.height() - 4)
        delays = [c._delay for c in self.popup.cells]
        self.assertGreaterEqual(min(delays), 48.0)
        self.assertEqual(delays, sorted(delays))
        self.assertTrue(all(c._born is not None for c in self.popup.cells))

    def test_with_no_room_above_it_opens_below(self):
        self.anchor.move(self.anchor.x(), 0)
        popup = self.keep(bar.open_sets(self.anchor, 1.0))
        self.assertTrue(popup.isVisible())
        self.assertFalse(popup._above)
        self.assertEqual(popup.y(), self.anchor.mapToGlobal(QtCore.QPoint(0, 0)).y() + self.anchor.height() + 4)

    def test_a_set_deleted_from_its_cross_closes_the_gap(self):
        first = self.popup.cells[0]
        self.popup.remove(first)
        core.delete_selection_set.assert_called_once_with("a")
        self.assertEqual([c.label for c in self.popup.cells], ["b", "New from selection"])
        self.assertEqual([self.place(c) for c in self.popup.cells], [(0, 0), (0, 1)])
        self.assertIsNone(first.parentWidget())

    def test_a_panel_one_row_shorter_keeps_its_edge_on_the_button(self):
        core.selection_sets.return_value = [(n, n) for n in "abcd"]
        popup = self.keep(bar.SetsPopup(self.anchor, 1.0)).open_at()
        last = popup.cells[-1]
        self.assertEqual(popup.grid.getItemPosition(popup.grid.indexOf(last))[:2], (1, 0))
        height, bottom = popup.height(), popup.geometry().bottom()
        popup.remove(popup.cells[0])
        self.assertLess(popup.height(), height)
        self.assertEqual(popup.geometry().bottom(), bottom)

    def test_a_set_that_would_not_go_keeps_its_cell(self):
        core.has_set.return_value = True
        self.popup.remove(self.popup.cells[0])
        self.assertEqual(len(self.popup.cells), 3)

    def test_a_click_selects_shift_adds_ctrl_removes(self):
        cell = self.popup.cells[0]
        self.modifiers(Qt.NoModifier)
        self.popup.picked(cell)
        core.select_set.assert_called_with("a", add=False)
        with mock.patch.object(QtWidgets.QApplication, "keyboardModifiers", return_value=Qt.ShiftModifier):
            self.popup.picked(cell)
        core.select_set.assert_called_with("a", add=True)
        with mock.patch.object(QtWidgets.QApplication, "keyboardModifiers", return_value=Qt.ControlModifier):
            self.popup.picked(cell)
        core.deselect_set.assert_called_once_with("a")

    def test_the_new_cell_closes_makes_the_set_and_opens_again(self):
        self.at_once()
        self.popup.open_at()
        with mock.patch.object(bar, "open_sets") as reopen:
            self.popup.picked(self.popup.cells[-1])
        core.create_selection_set.assert_called_once_with()
        reopen.assert_called_once_with(self.anchor, 1.0)
        self.assertFalse(self.popup.isVisible())

    def test_nothing_opens_again_when_the_button_is_gone_or_hidden(self):
        self.at_once()
        with mock.patch.object(bar, "open_sets") as reopen:
            self.anchor.hide()
            self.popup._after(core.update_selection_set)
            self.popup.anchor = mock.Mock(isVisible=mock.Mock(side_effect=RuntimeError("deleted")))
            self.popup._after(core.update_selection_set)
        reopen.assert_not_called()
        self.assertEqual(core.update_selection_set.call_count, 2)

    def test_the_right_click_menu_acts_on_its_set(self):
        self.at_once()
        cell = self.popup.cells[0]
        with mock.patch.object(bar, "open_sets"):
            self.menus.picks = [("Add to selection",), ("Colour", "Cyan"), ("Rename...",),
                                ("Update from selection",), ("Delete",)]
            cell.customContextMenuRequested.emit(QtCore.QPoint(2, 2))
            tree = self.menus.shown[-1][0]
            self.assertEqual(self.menus.labels(tree), ["Select", "Add to selection", "Remove from selection", "",
                                                       "Update from selection", "Rename...", "Colour", "", "Delete"])
            self.assertEqual(self.menus.labels(dict(tree)["Colour"]), [name for name, _c in bar.SET_COLOURS])
        core.select_set.assert_called_with("a", add=True)
        core.paint_set.assert_called_once_with("a", bar.BLEND)
        core.rename_selection_set.assert_called_once_with("a")
        core.update_selection_set.assert_called_once_with("a")
        core.delete_selection_set.assert_called_once_with("a")

    def test_the_cross_deletes_and_the_rest_of_the_cell_selects(self):
        self.popup.open_at()
        cell = self.popup.cells[0]
        x = cell.x_rect().translated(cell.width() / 2.0, cell.height() / 2.0).center()
        with mock.patch.object(self.popup, "remove") as remove, mock.patch.object(self.popup, "picked") as picked:
            cell.mouseMoveEvent(move(x.x(), x.y(), held=False))
            self.assertTrue(cell._on_x)
            cell.mousePressEvent(press(x.x(), x.y()))
            self.assertTrue(cell._x_down)
            cell.mouseReleaseEvent(release(x.x(), x.y()))
            remove.assert_called_once_with(cell)
            picked.assert_not_called()
            cell.mouseMoveEvent(move(20, 17, held=False))
            self.assertFalse(cell._on_x)
            cell.mousePressEvent(press(x.x(), x.y()))
            cell.mouseReleaseEvent(release(20, 17))
            remove.assert_called_once()
            cell.mousePressEvent(press(20, 17))
            cell.mouseReleaseEvent(release(20, 17))
        picked.assert_called_once_with(cell)
        self.assertFalse(self.popup.cells[-1]._over_x(press(*[x.x(), x.y()])))

    def test_a_cell_pops_in_lifts_and_settles(self):
        cell = self.popup.cells[0]
        cell.pop_in(1000.0, 50.0)
        self.assertTrue(cell.step(1000.0))
        self.assertFalse(cell.step(1000.0 + 50.0 + bar.POP_OPEN_MS + 1))
        with mock.patch.object(self.popup.driver, "kick") as kick:
            cell.enterEvent(enter())
            cell.leaveEvent(QtCore.QEvent(QtCore.QEvent.Leave))
            cell.mousePressEvent(press(20, 17))
        self.assertEqual(kick.call_count, 3)
        self.assertTrue(cell.step(cell._flash_t))

    def test_a_cell_is_drawn_on_the_field_and_lit_under_the_cursor(self):
        cell = self.popup.cells[0]
        middle = cell.width() // 2
        self.assertEqual(pixel(cell, middle, 6), bar.FIELD)
        cell._hover = 1.0
        self.assertEqual(pixel(cell, middle, 6), bar.HOVER)
        cell._on_x = True
        self.assertFalse(cell.grab().isNull())
        with mock.patch.object(bar, "_now", return_value=100.0):
            cell.pop_in(100.0, 50.0)
            unborn = cell.grab().toImage()
            self.assertEqual(unborn.pixelColor(middle, 6), unborn.pixelColor(0, 0))
            self.assertNotEqual(unborn.pixelColor(middle, 6).name(), bar.FIELD)
            cell._flash_t = 100.0
            self.popup.cells[-1]._flash_t = 100.0
            self.assertFalse(self.popup.cells[-1].grab().isNull())

    def test_escape_closes_it(self):
        self.popup.open_at()
        self.popup.keyPressEvent(QtGui.QKeyEvent(QtCore.QEvent.KeyPress, Qt.Key_A, Qt.NoModifier))
        self.assertTrue(self.popup.isVisible())
        self.popup.keyPressEvent(QtGui.QKeyEvent(QtCore.QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier))
        self.assertFalse(self.popup.isVisible())
        self.assertFalse(self.popup.grab().isNull())


# ---------------------------------------------------------------- the compact bar's Blend pop-up

class Blend(BarTest):

    def setUp(self):
        super(Blend, self).setUp()
        self.anchor = self.keep(QtWidgets.QWidget())
        self.anchor.resize(60, 22)
        geo = QtWidgets.QApplication.primaryScreen().availableGeometry()
        self.anchor.move(geo.left() + 100, geo.bottom() - 60)
        self.anchor.show()
        self.tracks = [bar.BlendSlider(code, code, bar.BLEND, code) for code in ("SM", "TW")]

    def test_the_tracks_rise_into_place_above_the_chip(self):
        popup = self.keep(bar.BlendPopup(self.anchor, 1.0, self.tracks))
        caption = [w.text() for w in popup.findChildren(QtWidgets.QLabel)]
        self.assertEqual(caption, ["BLEND"])
        self.assertEqual(len(popup.findChildren(bar.BlendSlider)), 2)
        popup.open_at()
        corner = self.anchor.mapToGlobal(QtCore.QPoint(0, 0))
        final = corner.y() - popup.height() - 4
        self.assertTrue(popup.isVisible())
        self.assertEqual(popup.y(), final + 4)
        popup._fade.setCurrentTime(int(bar.POP_MS))
        self.assertEqual((popup.x(), popup.y()), (corner.x(), final))
        self.assertFalse(popup.grab().isNull())

    def test_with_no_room_above_it_opens_below_and_escape_closes_it(self):
        self.anchor.move(self.anchor.x(), 0)
        popup = self.keep(bar.BlendPopup(self.anchor, 1.0, self.tracks))
        popup.open_at()
        popup._fade.setCurrentTime(int(bar.POP_MS))
        self.assertEqual(popup.y(), self.anchor.mapToGlobal(QtCore.QPoint(0, 0)).y() + self.anchor.height() + 4)
        popup.keyPressEvent(QtGui.QKeyEvent(QtCore.QEvent.KeyPress, Qt.Key_B, Qt.NoModifier))
        popup.keyPressEvent(QtGui.QKeyEvent(QtCore.QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier))
        self.assertFalse(popup.isVisible())


# ---------------------------------------------------------------- layout pieces

class Layout(BarTest):

    def flow(self, count=5):
        host = self.keep(QtWidgets.QWidget())
        lay = bar.FlowLayout(host, spacing=6, margins=(4, 3, 4, 3))
        for _ in range(count):
            w = QtWidgets.QWidget()
            w.setFixedSize(50, 20)
            lay.addWidget(w)
        return host, lay

    def test_the_flow_wraps_rows_to_the_width(self):
        host, lay = self.flow()
        self.assertEqual(lay.count(), 5)
        self.assertIsNotNone(lay.itemAt(4))
        self.assertIsNone(lay.itemAt(5))
        self.assertIsNone(lay.takeAt(9))
        self.assertTrue(lay.hasHeightForWidth())
        self.assertEqual(lay.heightForWidth(1000), 3 + 20 + 3)
        self.assertEqual(lay.heightForWidth(120), 3 + 3 * 20 + 2 * 6 + 3)
        lay.setGeometry(QtCore.QRect(0, 0, 120, 78))
        self.assertEqual([lay.itemAt(i).geometry().topLeft().toTuple() for i in range(5)],
                         [(4, 3), (60, 3), (4, 29), (60, 29), (4, 55)])
        self.assertEqual(lay.minimumSize(), QtCore.QSize(58, 26))
        self.assertEqual(lay.sizeHint(), lay.minimumSize())
        self.assertEqual(getattr(lay.expandingDirections(), "value", lay.expandingDirections()), 0)
        taken = lay.takeAt(0)
        self.assertIsNotNone(taken)
        self.assertEqual(lay.count(), 4)

    def test_a_group_has_its_caption_in_its_colour_unless_compact(self):
        widgets = [QtWidgets.QWidget(), QtWidgets.QWidget()]
        group = self.keep(bar._group("KEYS", bar.KEYS, widgets, 1.5, spacing=4))
        caption = group.findChildren(QtWidgets.QLabel)
        self.assertEqual([c.text() for c in caption], ["KEYS"])
        self.assertIn(bar.KEYS, caption[0].styleSheet())
        self.assertEqual(caption[0].maximumHeight(), int(round(bar.CAPTION_H * 1.5)))
        bare = self.keep(bar._group("KEYS", bar.KEYS, [QtWidgets.QWidget()], 1.0, spacing=4, caption=False))
        self.assertEqual(bare.findChildren(QtWidgets.QLabel), [])
        self.assertEqual(bare.layout().spacing(), 4)

    def test_the_style_scales_and_follows_where_the_bar_stands(self):
        sheet = bar._style(1.5)
        self.assertIn("QWidget#%s { background: %s;" % (bar.BAR_NAME, bar.PANEL), sheet)
        self.assertIn("border-bottom: 1px solid %s;" % bar.TRACK, sheet)
        self.assertIn("font-size: 18px", sheet)
        self.assertNotIn("border-bottom", bar._style(1.0, embedded=True))
        self.assertIn("QWidget#%s { background: transparent;" % bar.COMPACT_NAME,
                      bar._style(1.0, root=bar.COMPACT_NAME))


# ---------------------------------------------------------------- the strip

class Strip(BarTest):

    def strip(self, **kw):
        return self.keep(bar.ATBar(**kw))

    def buttons(self, strip):
        return strip.findChildren(bar.ATButton)

    def by_tip(self, strip, start):
        found = [b for b in self.buttons(strip) if b.toolTip().startswith(start)]
        self.assertEqual(len(found), 1, start)
        return found[0]

    def test_the_full_strip_carries_every_group_with_its_caption(self):
        strip = self.strip()
        self.assertEqual(strip.objectName(), bar.BAR_NAME)
        captions = [w.text() for w in strip.findChildren(QtWidgets.QLabel)]
        for title in ("AT", "KEYS", "BLEND", "POSE", "SPACE", "TIME", "TOOLS"):
            self.assertIn(title, captions)
        self.assertEqual(len(self.buttons(strip)), 26)
        self.assertEqual(len(strip.findChildren(bar.BlendSlider)), 4)
        self.assertIsInstance(strip.layout(), bar.FlowLayout)
        core.install_recovery_check.assert_called_once_with()
        self.assertEqual(pixel(strip, 1, 1), bar.PANEL)

    def test_the_compact_strip_puts_blend_first_behind_a_chip_and_drops_the_captions(self):
        strip = self.strip(compact=True)
        self.assertEqual(strip.objectName(), bar.COMPACT_NAME)
        captions = [w.text() for w in strip.findChildren(QtWidgets.QLabel)]
        self.assertEqual(captions, [])
        self.assertEqual(strip.findChildren(bar.BlendSlider), [])
        self.assertEqual(strip.blend_btn.text, "BLEND")
        self.assertEqual(strip.blend_btn.height(), bar.COMPACT_FACE + 2 * bar.COMPACT_PAD)
        self.assertTrue(strip.layout().itemAt(0).widget().isAncestorOf(strip.blend_btn))
        self.assertEqual(len(self.buttons(strip)), 27)
        self.assertEqual(strip.nudge_spin.width(), 28)
        self.assertFalse(strip.grab().isNull())

    def test_the_blend_chip_opens_the_four_tracks(self):
        strip = self.strip(compact=True)
        strip.show()
        strip.blend_btn.click()
        popups = [w for w in QtWidgets.QApplication.topLevelWidgets() if isinstance(w, bar.BlendPopup)
                  and w.isVisible()]
        self.assertEqual(len(popups), 1)
        self.keep(popups[0])
        self.assertEqual([s.code for s in popups[0].findChildren(bar.BlendSlider)], ["SM", "TW", "BD", "BN"])

    def test_the_frames_field_is_remembered_and_drives_the_key_tools(self):
        self.cmds.optionvars[bar.NUDGE_OPT] = 5
        strip = self.strip()
        self.assertEqual(strip.nudge_spin.value(), 5)
        strip.nudge_spin.setValue(7)
        self.assertEqual(self.cmds.optionvars[bar.NUDGE_OPT], 7)
        self.by_tip(strip, "Nudge Left").click()
        self.by_tip(strip, "Nudge Right").click()
        for what in ("Insert", "Remove"):
            for where in ("selected", "whole"):
                self.by_tip(strip, "%s Inbetween: the field's frames after the current time (%s" % (what, where)).click()
        self.assertEqual(core.nudge.call_args_list, [mock.call(-7), mock.call(7)])
        self.assertEqual(core.inbetween.call_args_list, [mock.call(7), mock.call(7, scene=True), mock.call(-7),
                                                         mock.call(-7, scene=True)])

    def test_without_a_remembered_value_the_field_reads_two(self):
        self.assertEqual(self.strip().nudge_spin.value(), 2)

    def test_every_tool_button_calls_its_tool(self):
        strip = self.strip()
        for tip, tool in (("Copy Animation", "copy_animation"), ("Paste Animation", "paste_animation"),
                          ("Copy Pose", "copy_pose"), ("Paste Pose", "paste_pose"), ("Mirror Pose", "mirror_pose"),
                          ("Align Objects", "align_objects"), ("Euler Filter", "euler_filter"),
                          ("Snapshot Default Pose", "snapshot_default_pose"), ("Time Bookmark:", "add_bookmark")):
            self.by_tip(strip, tip).click()
            getattr(core, tool).assert_called_once_with()

    def test_a_tool_that_fails_is_said_in_maya(self):
        core.copy_pose.side_effect = RuntimeError("boom")
        self.by_tip(self.strip(), "Copy Pose").click()
        self.assertEqual(len(self.cmds.warnings), 1)
        self.assertTrue(self.cmds.warnings[0].startswith("AT: "))

    def test_a_toggle_shows_the_scene_s_state_not_the_click_s(self):
        strip = self.strip()
        strip.temp_ctrl_btn.click()
        core.toggle_temp_controls.assert_called_once_with()
        self.assertFalse(strip.temp_ctrl_btn.isChecked())
        core.temp_pivot_active.return_value = True
        strip.temp_pivot_btn.click()
        core.toggle_temp_pivot.assert_called_once_with()
        self.assertTrue(strip.temp_pivot_btn.isChecked())
        core.motion_trails_exist.return_value = True
        strip.trail_btn.click()
        core.motion_trail_click.assert_called_once_with()
        self.assertTrue(strip.trail_btn.isChecked())

    def test_the_toggles_follow_the_scene_and_a_failing_question_changes_nothing(self):
        strip = self.strip()
        core.temp_controls_active.return_value = True
        core.temp_pivot_active.side_effect = RuntimeError("no scene")
        strip.temp_pivot_btn.setChecked(True)
        strip._sync_toggles()
        self.assertTrue(strip.temp_ctrl_btn.isChecked())
        self.assertTrue(strip.temp_pivot_btn.isChecked())
        self.assertTrue(strip._sync_timer.isActive())

    def test_anim_recovery_is_on_unless_turned_off_and_its_interval_remembered(self):
        strip = self.strip()
        self.assertTrue(strip.recovery_btn.isChecked())
        self.assertTrue(strip._recovery_timer.isActive())
        self.assertEqual(strip._recovery_timer.interval(), 60 * 1000)
        self.assertEqual(self.cmds.optionvars[bar.RECOVERY_ON_OPT], 1)
        core.message.assert_not_called()
        strip.recovery_btn.click()
        self.assertFalse(strip._recovery_timer.isActive())
        self.assertEqual(self.cmds.optionvars[bar.RECOVERY_ON_OPT], 0)
        core.message.assert_called_with("anim recovery off")
        self.cmds.optionvars[bar.RECOVERY_OPT] = 5
        strip.recovery_btn.click()
        self.assertEqual(strip._recovery_timer.interval(), 5 * 60 * 1000)
        core.message.assert_called_with("anim recovery on: every 5 min")

    def test_anim_recovery_left_off_stays_off(self):
        self.cmds.optionvars[bar.RECOVERY_ON_OPT] = 0
        strip = self.strip()
        self.assertFalse(strip.recovery_btn.isChecked())
        self.assertFalse(strip._recovery_timer.isActive())

    def test_the_recovery_menu_saves_now_opens_the_folder_and_sets_the_interval(self):
        strip = self.strip()
        entries = strip._recovery_menu()
        self.assertEqual([e[0] for e in entries], ["Save backup now", "Open backups folder", "Interval"])
        entries[0][1]()
        core.save_recovery.assert_called_once_with(force=True)
        core.message.assert_called_with("saved C:/r/shot_1.mb")
        self.assertIs(entries[1][1], core.open_recovery_folder)
        interval = dict(entries[2][1])
        self.assertEqual(sorted(interval), ["1 min", "10 min", "2 min", "5 min"])
        interval["10 min"]()
        self.assertEqual(self.cmds.optionvars[bar.RECOVERY_OPT], 10)
        self.assertEqual(strip._recovery_timer.interval(), 10 * 60 * 1000)
        strip.recovery_btn.setChecked(False)
        strip._recovery_timer.stop()
        interval["2 min"]()
        self.assertFalse(strip._recovery_timer.isActive())

    def test_the_trail_menu_adds_clears_and_follows_the_scene(self):
        strip = self.strip()
        entries = [e for e in strip._trail_menu() if e]
        self.assertEqual([e[0] for e in entries], ["Add trail to the selection", "Clear the selection's trails",
                                                   "Clear all trails"])
        core.motion_trails_exist.return_value = True
        entries[0][1]()
        core.add_motion_trail.assert_called_once_with()
        self.assertTrue(strip.trail_btn.isChecked())
        entries[1][1]()
        entries[2][1]()
        core.clear_motion_trail.assert_called_once_with()
        core.clear_all_motion_trails.assert_called_once_with()

    def test_the_sets_menu_lists_the_sets_and_shift_adds(self):
        strip = self.strip()
        entries = strip._sets_menu()
        self.assertEqual(entries[0], None)
        self.assertNotIn("Delete set", [e[0] for e in entries if e])
        core.selection_sets.return_value = [("hands", "hands"), ("feet", "feet")]
        entries = strip._sets_menu()
        self.assertEqual([e[0] if e else None for e in entries],
                         ["hands", "feet", None, "Create set from selection...", "Delete set"])
        self.modifiers(Qt.ShiftModifier)
        entries[0][1]()
        core.select_set.assert_called_once_with("hands", add=True)
        dict(entries[4][1])["feet"]()
        core.delete_selection_set.assert_called_once_with("feet")

    def test_the_sets_button_opens_the_cells_out_of_itself(self):
        strip = self.strip()
        with mock.patch.object(bar, "open_sets") as opened:
            strip.sets_btn.click()
        opened.assert_called_once_with(strip.sets_btn, strip.ui)

    def test_paste_animation_mirror_world_and_snapshot_menus(self):
        strip = self.strip()
        paste = strip._paste_anim_menu()
        paste[1][1]()
        paste[2][1]()
        self.assertEqual(core.paste_animation.call_args_list, [mock.call("insert"), mock.call("original")])
        mirror = strip._mirror_menu()
        mirror[-1][1]()
        core.select_opposite.assert_called_once_with(add=True)
        world = strip._world_menu()
        world[2][1]()
        core.paste_world_space.assert_called_once_with(all_keys=True)
        self.assertEqual([e[1] for e in strip._snapshot_menu()],
                         [core.snapshot_default_pose, core.reset_to_default_pose, core.clear_default_pose])

    def test_the_relationship_button_copies_and_shift_pastes_by_channels(self):
        strip = self.strip()
        for mods, want in ((Qt.NoModifier, ("copy", None)), (Qt.ShiftModifier, ("paste", {})),
                           (Qt.ShiftModifier | Qt.ControlModifier, ("paste", {"channels": "t"})),
                           (Qt.ShiftModifier | Qt.AltModifier, ("paste", {"channels": "r"}))):
            core.copy_relationship.reset_mock()
            core.paste_relationship.reset_mock()
            with mock.patch.object(QtWidgets.QApplication, "keyboardModifiers", return_value=mods):
                strip._relationship_click()
            if want[0] == "copy":
                core.copy_relationship.assert_called_once_with()
                core.paste_relationship.assert_not_called()
            else:
                core.paste_relationship.assert_called_once_with(**want[1])

    def test_the_relationship_menu_pastes_each_channel_set_now_or_on_the_highlight(self):
        entries = [e for e in self.strip()._relationship_menu() if e]
        self.assertEqual(len(entries), 7)
        dict(entries)["Paste Translate only"]()
        dict(entries)["Paste Rotate only on the highlighted keys"]()
        self.assertEqual(core.paste_relationship.call_args_list,
                         [mock.call(channels="t"), mock.call(in_range=True, channels="r")])

    def test_the_world_button_copies_and_shift_pastes(self):
        strip = self.strip()
        strip._world_click()
        core.copy_world_space.assert_called_once_with()
        self.modifiers(Qt.ShiftModifier)
        strip._world_click()
        core.paste_world_space.assert_called_once_with()

    def test_the_space_switcher_lists_the_selection_s_enums(self):
        strip = self.strip()
        entries = strip._space_entries(False)
        self.assertEqual([e[0] for e in entries], ["(no enum attributes on the selection)"])
        self.assertIsNone(entries[0][1]())
        core.enum_attrs.return_value = {"space": ["World", "Hand"], "follow": ["Off", "On"]}
        entries = strip._space_entries(True)
        self.assertEqual([e[0] for e in entries], ["follow", "space"])
        dict(entries[1][1])["Hand"]()
        core.space_switch.assert_called_once_with("space", 1, all_keys=True)
        self.by_tip(strip, "Space Switcher:").click()
        self.assertEqual(self.menus.labels(self.menus.shown[-1][0]), ["follow", "space"])
        self.by_tip(strip, "Space Switcher (all keys)").click()
        tree = self.menus.shown[-1][0]
        self.assertEqual(tree, [("follow", [("Off", None), ("On", None)]), ("space", [("World", None), ("Hand", None)])])

    def test_the_bookmark_menus(self):
        strip = self.strip()
        marks = strip._bookmark_menu()
        marks[1][1]()
        marks[2][1]()
        self.assertEqual(core.go_to_bookmark.call_args_list, [mock.call(1), mock.call(-1)])
        empty = strip._bookmarks_panel()
        self.assertEqual(empty[0][0], "(no bookmarks)")
        self.assertIsNone(empty[0][1]())
        self.assertIs(empty[2][1], core.add_bookmark)
        core.bookmarks.return_value = [("intro", 10, 20)]
        panel = strip._bookmarks_panel()
        self.assertEqual(panel[0][0], "intro   10-20")
        panel[0][1]()
        self.assertEqual(self.cmds.times, [10])

    def test_the_extra_menu_offers_suspend_or_resume(self):
        strip = self.strip()
        self.assertEqual(strip._extra_menu()[-1][0], "Suspend viewport")
        strip._toggle_suspend()
        core.set_viewport_suspended.assert_called_once_with(True)
        core._state["suspended"] = True
        self.assertEqual(strip._extra_menu()[-1][0], "Resume viewport")

    def test_a_narrow_strip_wraps_into_more_rows(self):
        strip = self.strip()
        self.assertGreater(strip.needed_height(400), strip.needed_height(4000))
        strip.resize(150, 10)                                # not laid out yet: a row as wide as Maya's window
        self.assertEqual(strip.needed_height(), strip.needed_height(1920))
        self.assertEqual(strip.logical_height(), strip.needed_height())
        host = self.keep(QtWidgets.QWidget())
        host.resize(450, 10)
        strip.setParent(host)
        strip.resize(150, 10)
        self.assertEqual(strip.needed_height(), strip.needed_height(450))

    def test_inside_the_time_bar_it_is_exactly_as_tall_as_its_rows(self):
        strip = self.strip(embedded=True)
        self.assertNotIn("border-bottom", strip.styleSheet())
        with mock.patch.object(bar, "_fit_timebar") as fit:
            strip.fit_dock()
        want = strip.needed_height()
        self.assertEqual((strip.minimumHeight(), strip.maximumHeight()), (want, want))
        fit.assert_called_once_with()

    def test_a_compact_strip_never_fits_a_dock(self):
        strip = self.strip(compact=True)
        strip.fit_dock()
        self.assertEqual(strip.minimumHeight(), 0)
        self.assertEqual(self.cmds.workspace, [])

    def test_its_own_control_grows_when_too_short(self):
        self.later()
        host = self.keep(QtWidgets.QWidget())
        QtWidgets.QVBoxLayout(host).setContentsMargins(0, 0, 0, 0)
        strip = bar.ATBar(host)
        host.layout().addWidget(strip)
        host.resize(600, 10)
        strip.resize(600, 10)
        strip.fit_dock()
        want = strip.needed_height()
        self.assertEqual(strip.minimumHeight(), want)
        self.assertEqual(self.cmds.workspace, [(CONTROL, {"edit": True, "resizeHeight": want})])
        self.cmds.workspace = []
        host.setFixedHeight(want + 50)
        strip.fit_dock()
        self.assertEqual(self.cmds.workspace, [])

    def test_a_docked_control_takes_its_room_from_the_tallest_neighbour(self):
        self.later()
        splitter = self.keep(QtWidgets.QSplitter(Qt.Vertical))
        view, host = QtWidgets.QWidget(), QtWidgets.QWidget()
        QtWidgets.QVBoxLayout(host).setContentsMargins(0, 0, 0, 0)
        strip = bar.ATBar(host)
        host.layout().addWidget(strip)
        splitter.addWidget(view)
        splitter.addWidget(host)
        splitter.resize(500, 800)
        splitter.show()
        self.app.processEvents()
        splitter.setSizes([780, 20])
        before = splitter.sizes()
        strip.fit_dock()
        want = strip.needed_height()
        delta = want - before[1]
        self.assertGreater(delta, 0)
        self.assertEqual(splitter.sizes(), [before[0] - delta, before[1] + delta])

    def test_a_neighbour_too_small_to_give_keeps_its_room(self):
        self.later()
        splitter = self.keep(QtWidgets.QSplitter(Qt.Vertical))
        view, host = QtWidgets.QWidget(), QtWidgets.QWidget()
        QtWidgets.QVBoxLayout(host).setContentsMargins(0, 0, 0, 0)
        strip = bar.ATBar(host)
        host.layout().addWidget(strip)
        splitter.addWidget(view)
        splitter.addWidget(host)
        splitter.resize(500, 160)
        splitter.show()
        self.app.processEvents()
        splitter.setSizes([140, 20])
        before = splitter.sizes()
        strip.fit_dock()
        self.assertEqual(splitter.sizes(), before)


class FRow(QtWidgets.QWidget):
    """The Time Bar's F row as the compact bar sees it: its status tools and the room it leaves."""

    def __init__(self):
        super(FRow, self).__init__()
        self.resize(900, 22)
        self.extra_room = 0
        self.tools = QtWidgets.QWidget(self)
        self.tools.setGeometry(100, 0, 200, 22)
        self.tools.place = mock.MagicMock()


class Compact(BarTest):

    def test_it_stands_after_the_status_tools_and_takes_its_room_from_the_tabs(self):
        row = self.keep(FRow())
        strip = bar.ATBar(row, compact=True)
        strip.place_in_row()
        size = strip.sizeHint()
        self.assertEqual(row.extra_room, size.width() + bar.COMPACT_GAP)
        row.tools.place.assert_called_once_with()
        self.assertEqual(strip.geometry(), QtCore.QRect(300 + bar.COMPACT_GAP, (22 - size.height()) // 2,
                                                        size.width(), size.height()))
        strip.place_in_row()
        row.tools.place.assert_called_once_with()

    def test_without_status_tools_it_stays_put(self):
        row = self.keep(QtWidgets.QWidget())
        strip = bar.ATBar(row, compact=True)
        before = strip.geometry()
        strip.place_in_row()
        self.assertEqual(strip.geometry(), before)

    def test_a_resize_or_a_move_places_it_again_on_the_next_turn(self):
        calls = self.later()
        row = self.keep(FRow())
        strip = bar.ATBar(row, compact=True)
        del calls[:]
        self.assertFalse(strip.eventFilter(row, QtGui.QResizeEvent(QtCore.QSize(9, 9), QtCore.QSize(8, 8))))
        self.assertFalse(strip.eventFilter(row.tools, QtGui.QMoveEvent(QtCore.QPoint(1, 1), QtCore.QPoint(0, 0))))
        self.assertEqual(calls, [strip.place_in_row, strip.place_in_row])
        strip.resizeEvent(QtGui.QResizeEvent(QtCore.QSize(9, 9), QtCore.QSize(8, 8)))
        self.assertEqual(len(calls), 2)

    def test_the_time_bar_resized_fits_an_embedded_strip_again(self):
        calls = self.later()
        host = self.keep(QtWidgets.QWidget())
        strip = bar.ATBar(host, embedded=True)
        del calls[:]
        strip.eventFilter(host, QtGui.QResizeEvent(QtCore.QSize(9, 9), QtCore.QSize(8, 8)))
        strip.eventFilter(strip, QtGui.QResizeEvent(QtCore.QSize(9, 9), QtCore.QSize(8, 8)))
        strip.eventFilter(host, QtGui.QMoveEvent(QtCore.QPoint(1, 1), QtCore.QPoint(0, 0)))
        self.assertEqual(calls, [strip.fit_dock])
        strip.resizeEvent(QtGui.QResizeEvent(QtCore.QSize(9, 9), QtCore.QSize(8, 8)))
        self.assertEqual(calls, [strip.fit_dock, strip.fit_dock])


# ---------------------------------------------------------------- where it stands

class Standing(BarTest):

    def named(self, name, parent=None):
        w = QtWidgets.QWidget(parent)
        w.setObjectName(name)
        return w

    def test_a_control_s_widget_is_found_through_maya(self):
        host = self.keep(QtWidgets.QWidget())
        omui = mock.MagicMock()
        omui.MQtUtil.findControl.side_effect = lambda name: getCppPointer(host)[0] if name == CONTROL else None
        with mock.patch.dict(sys.modules, {"maya.OpenMayaUI": omui}), \
                mock.patch.object(maya, "OpenMayaUI", omui, create=True):
            self.assertIs(bar._control_widget(), host)
            self.assertIsNone(bar._control_widget(TIMEBAR))

    def test_the_live_strip_in_our_control_else_in_the_time_bar(self):
        ours, timebar = self.keep(QtWidgets.QWidget()), self.keep(QtWidgets.QWidget())
        hosts = {CONTROL: ours, TIMEBAR: timebar}
        with mock.patch.object(bar, "_control_widget", side_effect=lambda control=CONTROL: hosts.get(control)):
            self.assertIsNone(bar.current())
            row = self.named(bar.BAR_NAME, timebar)
            self.assertIs(bar.embedded(), row)
            self.assertIs(bar.current(), row)
            mine = self.named(bar.BAR_NAME, ours)
            self.assertIs(bar.current(), mine)
        self.assertIsNone(bar._strip_in(None))

    def test_the_time_bar_is_fitted_to_its_page_and_our_row(self):
        from maya_timebar import bar as timebar, scene
        strip = object()
        with mock.patch.object(timebar, "current", return_value=strip), \
                mock.patch.object(scene, "page_height") as page:
            bar._fit_timebar()
        page.assert_called_once_with(strip)
        with mock.patch.object(timebar, "current", return_value=None), \
                mock.patch.object(scene, "page_height") as page:
            bar._fit_timebar()
        page.assert_not_called()
        with mock.patch.object(timebar, "current", side_effect=RuntimeError("no bar")):
            bar._fit_timebar()
        bar.traceback.print_exc.assert_called_once_with()

    def test_attached_it_is_the_time_bar_s_top_row_once(self):
        calls = self.later()
        host = self.keep(QtWidgets.QWidget())
        QtWidgets.QVBoxLayout(host).addWidget(QtWidgets.QLabel("page"))
        host.layout().setSpacing(6)
        strip = bar.attach(host)
        self.assertIs(host.layout().itemAt(0).widget(), strip)
        self.assertTrue(strip.embedded)
        self.assertEqual(host.layout().spacing(), 0)
        self.assertIn(strip.fit_dock, calls)
        self.assertIs(bar.attach(host), strip)
        self.assertEqual(host.layout().count(), 2)
        del calls[:]
        QtWidgets.QApplication.sendEvent(host, QtGui.QResizeEvent(QtCore.QSize(9, 9), QtCore.QSize(8, 8)))
        self.assertIn(strip.fit_dock, calls)

    def test_detached_the_time_bar_shrinks_back(self):
        host = self.keep(QtWidgets.QWidget())
        strip = self.named(bar.BAR_NAME, host)
        with mock.patch.object(bar, "embedded", return_value=strip), \
                mock.patch.object(bar, "_fit_timebar") as fit:
            self.assertTrue(bar.detach())
        self.assertIsNone(strip.parentWidget())
        fit.assert_called_once_with()
        with mock.patch.object(bar, "embedded", return_value=None):
            self.assertFalse(bar.detach())

    def test_the_f_row_is_the_time_bar_s_tabs(self):
        from maya_timebar import bar as timebar
        with mock.patch.object(timebar, "current", return_value=None):
            self.assertIsNone(bar.compact_host())
        with mock.patch.object(timebar, "current", return_value=mock.Mock(tabs="tabs")):
            self.assertEqual(bar.compact_host(), "tabs")
        with mock.patch.object(timebar, "current", side_effect=RuntimeError("no bar")):
            self.assertIsNone(bar.compact_host())

    def test_the_compact_bar_goes_into_one_f_row_at_a_time(self):
        calls = self.later()
        first, second = self.keep(FRow()), self.keep(FRow())
        strip = bar.attach_compact(first)
        self.keep(strip)
        self.assertIs(strip.parentWidget(), first)
        self.assertIs(bar.compact(), strip)
        self.assertIn(strip.place_in_row, calls)
        self.assertIs(bar.attach_compact(first), strip)
        del calls[:]
        QtWidgets.QApplication.sendEvent(first.tools, QtGui.QMoveEvent(QtCore.QPoint(1, 1), QtCore.QPoint(0, 0)))
        self.assertIn(strip.place_in_row, calls)
        moved = self.keep(bar.attach_compact(second))
        self.assertIsNot(moved, strip)
        self.assertIsNone(strip.parentWidget())
        self.assertEqual(first.extra_room, 0)
        self.assertIs(moved.parentWidget(), second)

    def test_detaching_the_compact_bar_gives_the_tabs_their_room(self):
        self.later()
        row = self.keep(FRow())
        strip = self.keep(bar.attach_compact(row))
        row.tools.place.reset_mock()
        self.assertTrue(bar.detach_compact())
        self.assertEqual(row.extra_room, 0)
        row.tools.place.assert_called_once_with()
        QtWidgets.QApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
        self.assertIsNone(bar.compact())
        self.assertFalse(bar.detach_compact())

    def test_the_ui_script_builds_a_fresh_strip_in_our_control(self):
        calls = self.later()
        with mock.patch.object(bar, "_control_widget", return_value=None):
            self.assertIsNone(bar.build())
        host = self.keep(QtWidgets.QWidget())
        old = self.named(bar.BAR_NAME, host)
        with mock.patch.object(bar, "_control_widget", return_value=host):
            strip = bar.build()
        self.assertIsNone(old.parentWidget())
        self.assertIs(host.layout().itemAt(0).widget(), strip)
        self.assertEqual(host.layout().contentsMargins().top(), 0)
        self.assertIn(strip.fit_dock, calls)
        self.assertFalse(strip.embedded)


if __name__ == "__main__":
    unittest.main()
