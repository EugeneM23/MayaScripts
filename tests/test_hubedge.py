"""maya_hubedge: the edge panel's windows and controller, offscreen.

Every timer is driven by calling the controller's handlers directly; the
cursor, the mouse buttons, the work area and whether Maya is the active
application come through the constructor's seams. Since 2026-11-19 nothing
slides: the panel is out or off the edge at once.

Spec: docs/superpowers/specs/2026-10-08-hub-compact-and-edge-panel-design.md
"""

import os
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtWidgets

import maya_edgerules as rules
import maya_hubedge as hubedge
import maya_hubstyle as hubstyle
edgerules = rules


def _app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


class EdgeCase(unittest.TestCase):

    def setUp(self):
        self.app = _app()
        self.point = (500, 400)
        self.down = False
        self.active = True
        self.widths = []
        self.edge = hubedge.Edge(
            scale=1.0, width=360,
            on_width=self.widths.append,
            work_area=lambda: (0, 0, 1600, 900),
            cursor=lambda: self.point, buttons=lambda: self.down,
            app_active=lambda: self.active)

    def tearDown(self):
        self.edge.destroy()

    def test_built_hidden_the_sensor_up(self):
        self.assertFalse(self.edge.shown)
        self.assertFalse(self.edge.host.isVisible())
        self.assertTrue(self.edge.sensor.isVisible())
        self.assertEqual(self.edge.sensor.geometry().getRect(),
                         (0, 0, rules.SENSOR_PX, 900))

    def test_the_windows_are_named(self):
        self.assertEqual(self.edge.host.objectName(), hubedge.HOST)
        self.assertEqual(self.edge.sensor.objectName(), hubedge.SENSOR)
        self.assertEqual(self.edge.slot.objectName(), hubedge.SLOT)
        self.assertEqual(self.edge.slot.layout().objectName(),
                         hubedge.SLOT + "Layout")
        self.assertEqual(self.edge.grip.objectName(), hubedge.GRIP)
        self.assertTrue(self.edge.host.isWindow())
        self.assertTrue(self.edge.sensor.isWindow())

    def test_the_constructor_registers_nothing(self):
        self.assertIsNot(hubedge.state()["edge"], self.edge)

    def test_a_hidden_slot_waits_off_the_edge(self):
        self.assertEqual(self.edge.slot.x(), -self.edge.host.width())

    def test_dwell_on_the_edge_reveals(self):
        self.point = (0, 300)
        self.edge.sensor_entered()
        self.edge.dwell_done()
        self.assertTrue(self.edge.shown)
        self.assertEqual(self.edge.host.geometry().getRect(), (0, 0, 360, 900))
        self.assertEqual(self.edge.slot.x(), 0)
        self.assertFalse(self.edge.sensor.isVisible())
        self.assertTrue(self.edge.host.isVisible())
        self.assertFalse(self.edge.dwell.isActive())

    def test_a_dwell_cut_short_reveals_nothing(self):
        self.point = (0, 300)
        self.edge.sensor_entered()
        self.point = (40, 300)                  # moved off before the timer
        self.edge.dwell_done()
        self.assertFalse(self.edge.shown)

    def test_leaving_the_sensor_stops_the_dwell(self):
        self.edge.sensor_entered()
        self.assertTrue(self.edge.dwell.isActive())
        self.edge.sensor_left()
        self.assertFalse(self.edge.dwell.isActive())

    def test_no_reveal_with_a_button_held_or_maya_inactive(self):
        self.point = (0, 300)
        self.down = True
        self.edge.dwell_done()
        self.assertFalse(self.edge.shown)
        self.down, self.active = False, False
        self.edge.dwell_done()
        self.assertFalse(self.edge.shown)

    def _shown(self):
        self.point = (0, 300)
        self.edge.dwell_done()
        self.assertTrue(self.edge.shown)

    def test_leaving_hides(self):
        self._shown()
        self.point = (900, 300)
        self.edge.host_left()
        self.assertTrue(self.edge.hide.isActive())
        self.edge.hide_due()
        self.assertFalse(self.edge.shown)
        self.assertFalse(self.edge.host.isVisible())
        self.assertTrue(self.edge.sensor.isVisible())
        self.assertEqual(self.edge.slot.x(), -self.edge.host.width())

    def test_entering_again_cancels_the_hide(self):
        self._shown()
        self.edge.host_left()
        self.edge.host_entered()
        self.assertFalse(self.edge.hide.isActive())

    def test_the_cursor_back_inside_keeps_it(self):
        self._shown()
        self.point = (100, 300)
        self.edge.hide_due()
        self.assertTrue(self.edge.shown)
        self.assertEqual(self.edge.blockers(), ["inside"])
        self.assertTrue(self.edge.retry.isActive())

    def test_a_held_button_postpones(self):
        self._shown()
        self.point, self.down = (900, 300), True
        self.edge.hide_due()
        self.assertTrue(self.edge.shown)
        self.assertTrue(self.edge.retry.isActive())
        self.down = False
        self.edge.hide_due()
        self.assertFalse(self.edge.shown)

    def test_pinned_stays(self):
        self._shown()
        self.edge.set_pinned(True)
        self.point = (900, 300)
        self.edge.hide_due()
        self.assertTrue(self.edge.shown)
        #  the pin has its own way out (unpinning starts the hide): no
        #  retry ticking for as long as it stays pinned
        self.assertFalse(self.edge.retry.isActive())
        self.edge.set_pinned(False)
        self.assertTrue(self.edge.hide.isActive())
        self.edge.hide_due()
        self.assertFalse(self.edge.shown)

    def test_a_command_reveal_holds_until_visited(self):
        self.point = (900, 300)
        self.edge.reveal(hold=True)
        self.edge.hide_due()
        self.assertTrue(self.edge.shown)          # never entered
        self.point = (100, 300)
        self.edge.host_entered()
        self.point = (900, 300)
        self.edge.host_left()
        self.edge.hide_due()
        self.assertFalse(self.edge.shown)

    def test_a_command_reveal_under_the_cursor_counts_the_visit_begun(self):
        #  the cursor already over the panel sends no Enter: leaving it must
        #  still release the hold
        self.point = (100, 300)
        self.edge.reveal(hold=True)
        self.assertTrue(self.edge.hold.held)
        self.assertTrue(self.edge.hold.entered)
        self.point = (900, 300)
        self.edge.host_left()
        self.edge.hide_due()
        self.assertFalse(self.edge.shown)

    def test_a_press_outside_releases_the_hold(self):
        self.point = (900, 300)
        self.edge.reveal(hold=True)
        self.edge.press_at((900, 300))
        self.edge.hide_due()
        self.assertFalse(self.edge.shown)

    def test_a_press_inside_keeps_the_hold(self):
        self.point = (900, 300)
        self.edge.reveal(hold=True)
        self.edge.press_at((100, 300))
        self.assertTrue(self.edge.hold.held)
        self.edge.hide_due()
        self.assertTrue(self.edge.shown)

    def _typing(self, focus, active=True):
        """blockers() with `focus` as the application's focus widget and the
        host (in)active. Offscreen Qt gives no window the focus, so both are
        patched - what is tested is the rule, not the platform."""
        host_class = type(self.edge.host)
        with mock.patch.object(QtWidgets.QApplication, "focusWidget",
                               staticmethod(lambda: focus)), \
                mock.patch.object(host_class, "isActiveWindow",
                                  lambda widget: active):
            return self.edge.blockers()

    def test_a_focused_field_postpones(self):
        self._shown()
        self.point = (900, 300)
        for kind in (QtWidgets.QLineEdit, QtWidgets.QSpinBox,
                     QtWidgets.QTextEdit, QtWidgets.QPlainTextEdit):
            field = kind(self.edge.slot)
            self.assertEqual(self._typing(field), ["typing"], kind.__name__)
        field = QtWidgets.QLineEdit(self.edge.slot)
        host_class = type(self.edge.host)
        with mock.patch.object(QtWidgets.QApplication, "focusWidget",
                               staticmethod(lambda: field)), \
                mock.patch.object(host_class, "isActiveWindow",
                                  lambda widget: True):
            self.edge.hide_due()
            self.assertTrue(self.edge.shown)
            self.assertTrue(self.edge.retry.isActive())    # asks again

    def test_only_a_text_field_of_the_active_panel_counts(self):
        self._shown()
        self.point = (900, 300)
        button = QtWidgets.QPushButton(self.edge.slot)
        self.assertEqual(self._typing(button), [])         # not a text field
        outside = QtWidgets.QLineEdit()                    # not the panel's
        try:
            self.assertEqual(self._typing(outside), [])
        finally:
            outside.deleteLater()
        field = QtWidgets.QLineEdit(self.edge.slot)
        self.assertEqual(self._typing(field, active=False), [])  # Maya's
        self.assertEqual(self._typing(None), [])           # no focus at all

    def test_the_width_grip_clamps_and_reports(self):
        self.edge.set_width(1000)
        self.assertEqual(self.widths[-1], rules.MAX_WIDTH)
        self._shown()
        self.assertEqual(self.edge.host.width(), rules.MAX_WIDTH)

    def test_dragging_the_grip_widens_and_remembers_on_release(self):
        self._shown()
        grip = self.edge.grip
        grip.press(360)
        grip.drag(460)
        self.assertEqual(self.edge.host.width(), 460)
        self.assertEqual(self.widths, [])              # not while dragging
        grip.drag(300)
        self.assertEqual(self.edge.host.width(), 300)
        grip.release()
        self.assertEqual(self.widths, [300])
        self.assertEqual(self.edge.slot.x(), 0)
        #  the grip stays on the host's right edge at its width
        self.assertEqual(grip.geometry().getRect(),
                         (300 - rules.GRIP_PX, 0, rules.GRIP_PX, 900))

    def test_the_slot_leaves_the_host_s_right_line_uncovered(self):
        self._shown()
        self.assertEqual(self.edge.slot.width(), self.edge.host.width() - 1)
        self.assertEqual(self.edge.slot.height(), self.edge.host.height())

    def test_an_application_press_outside_releases_the_hold(self):
        pressed = []

        class Other(QtWidgets.QWidget):
            def mousePressEvent(self, event):              # noqa: N802
                pressed.append(event.globalPosition().toPoint().toTuple())

        other = Other()
        other.setGeometry(800, 200, 200, 200)
        other.show()
        try:
            self.point = (900, 300)
            self.edge.reveal(hold=True)
            QtWidgets.QApplication.sendEvent(other, _press((900, 300)))
            self.assertFalse(self.edge.hold.held)
            self.assertTrue(self.edge.hide.isActive())
            self.assertEqual(pressed, [(900, 300)])       # never swallowed
        finally:
            other.close()
            other.deleteLater()

    def test_the_press_watch_survives_the_host_s_deletion(self):
        pressed = []

        class Other(QtWidgets.QWidget):
            def mousePressEvent(self, event):              # noqa: N802
                pressed.append(1)

        other = Other()
        other.show()
        try:
            self.point = (900, 300)
            self.edge.reveal(hold=True)                   # the watch stands
            self.assertTrue(self.edge._watching)
            hubedge.destroy_all()                         # the host goes
            QtWidgets.QApplication.sendEvent(other, _press((900, 300)))
            self.edge.destroy()
            QtWidgets.QApplication.sendEvent(other, _press((900, 300)))
            self.assertEqual(pressed, [1, 1])
        finally:
            other.close()
            other.deleteLater()

    def test_the_press_watch_stands_only_while_a_hold_does(self):
        self.assertFalse(self.edge._watching)
        self._shown()
        self.assertFalse(self.edge._watching)            # a dwell: no hold
        self.edge.conceal()
        self.point = (900, 300)
        self.edge.reveal(hold=True)
        self.assertTrue(self.edge._watching)
        self.edge.press_at((900, 300))
        self.assertFalse(self.edge._watching)
        self.edge.reveal(hold=True)
        self.assertTrue(self.edge._watching)
        self.edge.conceal()
        self.assertFalse(self.edge._watching)

    def test_destroy_all_finds_them_by_name(self):
        other = hubedge.Edge(scale=1.0,
                             work_area=lambda: (0, 0, 800, 600),
                             cursor=lambda: (0, 0), buttons=lambda: False,
                             app_active=lambda: True)
        self.assertGreaterEqual(hubedge.destroy_all(), 2)
        self.assertFalse(other.alive())
        self.assertFalse(self.edge.alive())
        other.destroy()                                  # twice is harmless

    def test_destroy_clears_its_own_registration(self):
        hubedge.state()["edge"] = self.edge
        self.edge.destroy()
        self.assertIsNone(hubedge.state()["edge"])
        self.assertFalse(self.edge.alive())


def _press(point):
    """A left press at global `point`, as Qt delivers one."""
    gx, gy = point
    return QtGui.QMouseEvent(
        QtCore.QEvent.MouseButtonPress, QtCore.QPointF(5, 5),
        QtCore.QPointF(gx, gy), QtCore.Qt.LeftButton, QtCore.Qt.LeftButton,
        QtCore.Qt.NoModifier)


class Place(unittest.TestCase):

    def test_a_screen_on_the_left_and_a_display_scale(self):
        _app()
        edge = hubedge.Edge(scale=1.5, width=360,
                            work_area=lambda: (-1920, 40, 1920, 1000),
                            cursor=lambda: (0, 0), buttons=lambda: False,
                            app_active=lambda: True)
        try:
            self.assertEqual(edge.sensor.geometry().getRect(),
                             (-1920, 40, rules.SENSOR_PX, 1000))
            self.assertEqual(edge.host.geometry().getRect(),
                             (-1920, 40, 540, 1000))
            grip = 8                                # 5 logical px at 150 %
            self.assertEqual(edge.grip.geometry().getRect(),
                             (540 - grip, 0, grip, 1000))
        finally:
            edge.destroy()


class DefaultSeams(unittest.TestCase):
    """With no seams given, Qt answers (Maya's main window is absent here,
    so the primary screen stands in for its screen)."""

    def test_the_defaults_answer_plain_values(self):
        _app()
        x, y = hubedge._qt_cursor()
        self.assertIsInstance(x, int)
        self.assertIsInstance(y, int)
        self.assertIn(hubedge._qt_buttons(), (True, False))
        self.assertIn(hubedge._qt_app_active(), (True, False))
        area = hubedge._maya_work_area()
        self.assertEqual(len(area), 4)
        self.assertGreater(area[2], 0)
        self.assertIsNone(hubedge.main_window())

    def test_an_edge_with_no_seams_builds_and_goes(self):
        _app()
        edge = hubedge.Edge()
        try:
            self.assertEqual(edge.host.height(),
                             hubedge._maya_work_area()[3])
            self.assertEqual(edge.width, rules.WIDTH)
        finally:
            edge.destroy()
        self.assertFalse(edge.alive())


class Instant(unittest.TestCase):
    """2026-11-19 (the animator: «удаляем все подсветки и анимации из плагина»):
    the panel is out or off the edge at once - the frame whole or gone, the slot
    on its place, nothing left running."""

    def _edge(self):
        _app()
        return hubedge.Edge(scale=1.0, work_area=lambda: (0, 0, 800, 600),
                            cursor=lambda: (0, 10), buttons=lambda: False,
                            app_active=lambda: True)

    def test_a_reveal_is_out_at_once(self):
        edge = self._edge()
        try:
            edge.reveal()
            self.assertEqual(edge.slot.x(), 0)
            self.assertEqual(edge.frame, edge.host.width())
            self.assertTrue(edge.host.mask().isEmpty())
            self.assertTrue(edge.host.isVisible())
            self.assertFalse(edge.sensor.isVisible())
        finally:
            edge.destroy()

    def test_a_conceal_is_off_the_edge_at_once(self):
        edge = self._edge()
        try:
            edge.reveal()
            edge.conceal()
            self.assertEqual(edge.slot.x(), -edge.host.width())
            self.assertEqual(edge.frame, 0)
            self.assertFalse(edge.host.isVisible())
            self.assertTrue(edge.sensor.isVisible())
        finally:
            edge.destroy()

    def test_a_width_change_out_keeps_the_frame_whole(self):
        edge = self._edge()
        try:
            edge.reveal()
            edge.set_width(500, save=False)
            self.assertEqual(edge.frame, edge.host.width())
            self.assertTrue(edge.host.mask().isEmpty())
        finally:
            edge.destroy()

    def test_no_slide_is_left(self):
        edge = self._edge()
        try:
            for name in ("sliding", "motion", "burst", "_anim", "_slide",
                         "_rail_slide", "_stop_anim"):
                self.assertFalse(hasattr(edge, name), name)
        finally:
            edge.destroy()


class RightSide(unittest.TestCase):
    """2026-10-09, the animator: «Можем добавить опцию выбора стороны
    монитора откуда выезжает наша полка?» - the right edge, mirrored. The
    offset and the frame still count from the screen edge inward."""

    AREA = (100, 20, 1600, 900)          # x 100..1700

    def _edge(self, side="right"):
        _app()
        self.point = (1699, 300)
        self.widths = []
        return hubedge.Edge(scale=1.0, width=360, side=side,
                            on_width=self.widths.append,
                            work_area=lambda: self.AREA,
                            cursor=lambda: self.point,
                            buttons=lambda: False,
                            app_active=lambda: True)

    def test_the_left_is_the_default(self):
        edge = self._edge(side=None)
        try:
            self.assertEqual(edge.side, "left")
            self.assertEqual(edge.host.x(), 100)
            self.assertEqual(edge.offset, edge.slot.x())
            edge.reveal()
            self.assertEqual((edge.offset, edge.slot.x()), (0, 0))
        finally:
            edge.destroy()

    def test_the_windows_stand_on_the_right_edge(self):
        edge = self._edge()
        try:
            self.assertEqual(edge.side, "right")
            self.assertEqual(edge.host.geometry().getRect(),
                             (1340, 20, 360, 900))
            self.assertEqual(edge.sensor.geometry().getRect(),
                             (1700 - rules.SENSOR_PX, 20, rules.SENSOR_PX,
                              900))
            #  hidden, the slot waits off the right edge
            self.assertEqual(edge.offset, -360)
            self.assertEqual(edge.slot.x(), 361)
        finally:
            edge.destroy()

    def test_a_dwell_on_the_right_edge_reveals(self):
        edge = self._edge()
        try:
            edge.sensor_entered()
            edge.dwell_done()
            self.assertTrue(edge.shown)
            self.assertEqual(edge.offset, 0)
            #  the slot stops short of the line on the panel's left
            self.assertEqual(edge.slot.geometry().getRect(),
                             (1, 0, 359, 900))
            self.assertEqual(edge.grip.geometry().getRect(),
                             (0, 0, rules.GRIP_PX, 900))
            self.assertTrue(edge.host.mask().isEmpty())
        finally:
            edge.destroy()

    def test_the_left_edge_does_not_reveal_it(self):
        edge = self._edge()
        try:
            self.point = (100, 300)
            edge.sensor_entered()
            edge.dwell_done()
            self.assertFalse(edge.shown)
        finally:
            edge.destroy()

    def test_dragging_the_grip_left_widens(self):
        edge = self._edge()
        try:
            edge.reveal()
            edge.grip.press(1340)
            edge.grip.drag(1240)
            self.assertEqual(edge.host.geometry().getRect(),
                             (1240, 20, 460, 900))
            edge.grip.drag(1400)                       # back right: narrower
            self.assertEqual(edge.host.geometry().getRect(),
                             (1400, 20, 300, 900))
            edge.grip.drag(1500)
            self.assertEqual(edge.host.width(), rules.MIN_WIDTH)
            edge.grip.release()
            self.assertEqual(self.widths, [rules.MIN_WIDTH])
            self.assertEqual(edge.host.geometry().right(), 1699)
            self.assertEqual(edge.grip.x(), 0)
            self.assertEqual(edge.offset, 0)
        finally:
            edge.destroy()

    def test_it_comes_out_from_the_right_at_once(self):
        edge = self._edge()
        try:
            w = edge.host.width()
            edge.reveal()
            self.assertEqual((edge.frame, edge.offset), (w, 0))
            self.assertEqual(edge.slot.x(), 1)
            self.assertTrue(edge.host.mask().isEmpty())
        finally:
            edge.destroy()

    def test_it_goes_back_off_the_right_edge(self):
        edge = self._edge()
        try:
            w = edge.host.width()
            edge.reveal()
            edge.conceal()
            self.assertEqual((edge.frame, edge.offset), (0, -w))
            self.assertFalse(edge.host.isVisible())
            self.assertTrue(edge.sensor.isVisible())
        finally:
            edge.destroy()

    def test_set_side_moves_a_standing_panel(self):
        edge = self._edge(side="left")
        try:
            edge.reveal(hold=True)
            self.assertTrue(edge.set_side("right"))
            self.assertEqual(edge.side, "right")
            self.assertFalse(edge.shown)
            self.assertFalse(edge.hold.held)
            self.assertFalse(edge.host.isVisible())
            self.assertTrue(edge.sensor.isVisible())
            self.assertEqual(edge.host.geometry().getRect(),
                             (1340, 20, 360, 900))
            self.assertEqual(edge.sensor.x(), 1700 - rules.SENSOR_PX)
            self.assertEqual((edge.offset, edge.frame), (-360, 0))
            edge.reveal()
            self.assertEqual(edge.slot.x(), 1)
            #  the same side again: nothing
            self.assertFalse(edge.set_side("right"))
            self.assertTrue(edge.shown)
        finally:
            edge.destroy()

    def test_set_side_takes_a_panel_out_off_the_new_edge(self):
        edge = self._edge(side="left")
        try:
            edge.reveal()
            edge.set_side("right")
            self.assertEqual((edge.offset, edge.frame), (-360, 0))
        finally:
            edge.destroy()


class RailDock(unittest.TestCase):
    """2026-10-17: «вешаем наш реил к боку экрана вьюпорта пусть он там висит
    постоянно, а при клике по иконкам рейла будут выезжать наши разделы» - the rail
    always shows on the viewport's side, the card comes out on a click only."""

    VIEWPORT = (100, 150, 1500, 700)

    def setUp(self):
        self.app = _app()
        self.point = (800, 400)
        self.edge = hubedge.Edge(
            scale=1.0, width=360, rail=True,
            rest=lambda: 40, work_area=lambda: self.VIEWPORT,
            cursor=lambda: self.point, buttons=lambda: False,
            app_active=lambda: True)

    def tearDown(self):
        self.edge.destroy()

    def frame_rect(self):
        return self.edge.host.mask().boundingRect().getRect()

    def test_the_rail_stands_on_the_viewport_side_at_rest(self):
        self.assertTrue(self.edge.host.isVisible())
        self.assertFalse(self.edge.sensor.isVisible())
        self.assertFalse(self.edge.shown)
        self.assertEqual(self.edge.host.geometry().getRect(), (100, 150, 360, 700))
        self.assertEqual(self.frame_rect(), (0, 0, 40, 700))
        self.assertEqual(self.edge.visible_rect(), (100, 150, 40, 700))
        self.assertFalse(self.edge.grip.isVisible())

    def test_a_reveal_opens_the_card_and_a_conceal_leaves_the_rail(self):
        self.edge.reveal()
        self.assertTrue(self.edge.shown)
        self.assertTrue(self.edge.host.mask().isEmpty())          # all of it
        self.assertTrue(self.edge.grip.isVisible())
        self.edge.conceal()
        self.assertFalse(self.edge.shown)
        self.assertTrue(self.edge.host.isVisible())
        self.assertEqual(self.frame_rect(), (0, 0, 40, 700))

    def test_the_hover_rules_do_nothing(self):
        self.edge.reveal()
        self.point = (1500, 400)
        self.edge.host_left()
        self.edge.hide_due()
        self.edge.press_at((1500, 400))
        self.assertTrue(self.edge.shown)
        self.assertFalse(self.edge.hide.isActive())
        self.edge.conceal()
        self.point = (100, 400)
        self.edge.dwell_done()
        self.assertFalse(self.edge.shown)

    def test_toggle(self):
        self.assertTrue(self.edge.toggle())
        self.assertFalse(self.edge.toggle())

    def test_the_right_side(self):
        self.edge.set_side("right")
        self.assertTrue(self.edge.host.isVisible())
        self.assertEqual(self.edge.host.geometry().getRect(), (1240, 150, 360, 700))
        self.assertEqual(self.frame_rect(), (320, 0, 40, 700))

    def test_it_follows_the_viewport(self):
        self.VIEWPORT = (0, 100, 1200, 600)
        self.edge._follow()
        self.assertEqual(self.edge.host.geometry().getRect(), (0, 100, 360, 600))


class RailShape(unittest.TestCase):
    """2026-10-17: «не нужно им рисовать фон под ними» - out, only the rail and the
    card show."""

    def setUp(self):
        self.app = _app()
        self.card = [(60, 10, 280, 200)]
        self.edge = hubedge.Edge(
            scale=1.0, width=360, rail=True,
            rest=lambda: 40, shape=lambda: self.card,
            work_area=lambda: (100, 150, 1500, 700),
            cursor=lambda: (800, 400), buttons=lambda: False,
            app_active=lambda: True)

    def tearDown(self):
        self.edge.destroy()

    def test_out_only_the_rail_and_the_card_show(self):
        self.edge.reveal()
        mask = self.edge.host.mask()
        self.assertTrue(mask.contains(QtCore.QPoint(20, 600)))      # the rail
        self.assertTrue(mask.contains(QtCore.QPoint(100, 100)))     # the card
        self.assertFalse(mask.contains(QtCore.QPoint(100, 400)))    # under the card
        self.assertFalse(mask.contains(QtCore.QPoint(350, 100)))    # past it

    def test_a_card_that_grows_is_followed(self):
        self.edge.reveal()
        self.card = [(60, 10, 280, 500)]
        self.edge._follow()
        self.assertTrue(self.edge.host.mask().contains(QtCore.QPoint(100, 400)))

    def test_at_rest_only_the_rail(self):
        mask = self.edge.host.mask()
        self.assertTrue(mask.contains(QtCore.QPoint(20, 100)))
        self.assertFalse(mask.contains(QtCore.QPoint(100, 100)))

    def test_the_visible_rects_are_the_rail_and_the_card(self):
        self.assertEqual(self.edge.visible_rects(), [(100, 150, 40, 700)])
        self.edge.reveal()
        self.assertEqual(self.edge.visible_rects(),
                         [(100, 150, 40, 700), (160, 160, 280, 200)])


class RailThroughTheHub(unittest.TestCase):
    """The real road - maya_hub's focus / ✕ on a real windowed Skin in a real rail
    Edge. Since 2026-11-19 the card comes out and goes back at once."""

    def setUp(self):
        import maya_hub as hub
        import maya_hubqt as hubqt
        import maya_hubstyle as style
        from tests.uifakes import FakeUiCmds
        self.app = _app()
        self.hub, self.hubqt = hub, hubqt
        self.saved = (hub.cmds, hub._SKIN, hub._cursor, hubqt.find, hubqt.path_of,
                      list(style._LISTENERS))
        self.style = style
        hub.cmds = FakeUiCmds()
        hub._cursor = lambda: (600, 500)
        hubqt.find = lambda name, layout=False: None
        hubqt.path_of = lambda obj: "path|" + obj.objectName()
        self.edge = hubedge.Edge(
            scale=1.0, width=360, rail=True,
            rest=hub._rail_rest, shape=hub._rail_shape,
            work_area=lambda: (100, 150, 800, 600), cursor=lambda: (600, 500),
            buttons=lambda: False, app_active=lambda: True)
        self.state = dict(hubedge.state())
        hubedge.state()["edge"] = self.edge
        skin = hubqt.Skin(self.edge.slot, scale=1.0, layout="rail", windowed=True,
                          callbacks={"close": hub._press_rail_close})
        skin.add_jump("alpha", "Alpha", "user", "#7fa9e6", group="scene")
        self.card = skin.add_card("alpha", "Alpha", "user", "#7fa9e6", "#23324a",
                                  collapsible=False)
        for i in range(3):
            label = QtWidgets.QLabel("row {0}".format(i))
            label.setFixedHeight(30)
            self.card.body_layout.addWidget(label)
        skin.add_jump("beta", "Beta", "user", "#7fa9e6", group="scene")
        self.beta = skin.add_card("beta", "Beta", "user", "#7fa9e6", "#23324a",
                                  collapsible=False)
        skin.show_card("alpha")
        hub._SKIN = self.skin = skin
        self.edge.place()
        self.app.processEvents()

    def tearDown(self):
        hub = self.hub
        hub.cmds, hub._SKIN, hub._cursor, self.hubqt.find, self.hubqt.path_of, \
            listeners = self.saved
        self.style._LISTENERS[:] = listeners
        hubedge.state().clear()
        hubedge.state().update(self.state)
        self.skin.destroy()
        self.edge.destroy()

    def test_a_rail_click_brings_the_card_out_at_once(self):
        self.hub.focus("alpha")
        self.assertTrue(self.edge.shown)
        self.assertEqual(self.edge.frame, self.edge.host.width())
        self.assertIsNone(self.card.frame.graphicsEffect())
        top = self.card.frame.mapTo(self.edge.host, QtCore.QPoint(10, 10))
        self.assertTrue(self.edge.host.mask().contains(top))

    def test_the_close_sends_the_card_back_to_the_rail_at_once(self):
        self.hub.focus("alpha")
        self.skin.cards["alpha"].close.click()
        self.assertFalse(self.edge.shown)
        self.assertEqual(self.edge.frame,
                         min(self.edge.host.width(), self.edge.rest_px()))
        self.assertTrue(self.edge.host.isVisible())

    def test_another_icon_shows_its_card_and_the_panel_stays_out(self):
        self.hub.focus("alpha")
        self.hub.focus("beta")
        self.assertTrue(self.edge.shown)
        self.assertEqual(self.skin.shown, "beta")
        self.assertTrue(self.beta.frame.isVisible())
        self.assertFalse(self.card.frame.isVisible())


class CardGrips(unittest.TestCase):
    """2026-10-22: «окна который открываются на рейле можно было изменять размер
    перетаскивая за противоположный край и за низ» - the rail card's width grip
    down its inner side, its height grip along its bottom."""

    VIEWPORT = (100, 150, 1500, 700)

    def setUp(self):
        self.app = _app()
        self.card = [60, 10, 280, 200]
        self.heights = []
        self.edge = hubedge.Edge(
            scale=1.0, width=360, rail=True,
            rest=lambda: 40, work_area=lambda: self.VIEWPORT,
            cursor=lambda: (800, 400), buttons=lambda: False,
            app_active=lambda: True, card=lambda: tuple(self.card),
            on_height=self.set_height)

    def set_height(self, logical, save):
        self.heights.append((logical, save))
        if logical is not None:
            self.card[3] = logical

    def tearDown(self):
        self.edge.destroy()

    def test_hidden_at_rest(self):
        self.assertFalse(self.edge.grip.isVisible())
        self.assertFalse(self.edge.hgrip.isVisible())

    def test_out_they_stand_on_the_card(self):
        self.edge.reveal()
        self.edge._place_grips()
        g = hubstyle.px(edgerules.GRIP_PX, 1.0)
        self.assertTrue(self.edge.grip.isVisible())
        self.assertTrue(self.edge.hgrip.isVisible())
        self.assertEqual(self.edge.grip.geometry().getRect(), (340 - g, 10, g, 200 - g))
        self.assertEqual(self.edge.hgrip.geometry().getRect(), (60, 210 - g, 280, g))

    def test_dragging_the_bottom_sets_the_height_and_the_release_keeps_it(self):
        self.edge.reveal()
        self.edge._place_grips()
        hgrip = self.edge.hgrip
        hgrip.press(500)
        hgrip.drag(560)
        self.assertEqual(self.heights[-1], (260, False))
        hgrip.drag(100)
        self.assertEqual(self.heights[-1], (edgerules.MIN_HEIGHT, False))
        hgrip.drag(540)
        hgrip.release()
        self.assertEqual(self.heights[-1], (240, True))
        g = hubstyle.px(edgerules.GRIP_PX, 1.0)
        self.assertEqual(hgrip.geometry().getRect(), (60, 250 - g, 280, g))

    def test_a_double_click_gives_the_content_s_height_back(self):
        self.edge.reveal()
        self.edge.hgrip.mouseDoubleClickEvent(None)
        self.assertEqual(self.heights[-1], (None, True))

    def test_the_width_grip_still_widens(self):
        self.edge.reveal()
        grip = self.edge.grip
        grip.press(400)
        grip.drag(440)
        grip.release()
        self.assertEqual(self.edge.width, 400)

    def test_on_the_right_side_the_width_grip_is_the_card_s_left(self):
        self.edge.set_side("right")
        self.edge.reveal()
        self.edge._place_grips()
        self.assertEqual(self.edge.grip.geometry().x(), 60)

    def test_the_follow_leaves_still_grips_alone(self):
        """2026-10-27: placed again every 150 ms with nothing changed, a raise_ each
        time repainted the card under the grips six times a second."""
        self.edge.reveal()
        self.edge._place_grips()
        touched = []
        for widget in (self.edge.grip, self.edge.hgrip):
            for name in ("setGeometry", "raise_", "show", "hide"):
                real = getattr(widget, name)
                setattr(widget, name, lambda *a, _n=name, _r=real: (touched.append(_n), _r(*a)))
        for _ in range(5):
            self.edge._place_grips()
        self.assertEqual(touched, [])
        self.card[3] = 260                                   # the card grew: the grips move
        self.edge._place_grips()
        self.assertIn("setGeometry", touched)
        g = hubstyle.px(edgerules.GRIP_PX, 1.0)
        self.assertEqual(self.edge.hgrip.geometry().getRect(), (60, 270 - g, 280, g))


class CardGripRules(unittest.TestCase):

    def test_card_grips(self):
        side, bottom = edgerules.card_grips((60, 10, 280, 200), 5, "left")
        self.assertEqual(side, (335, 10, 5, 195))
        self.assertEqual(bottom, (60, 205, 280, 5))
        side, _ = edgerules.card_grips((60, 10, 280, 200), 5, "right")
        self.assertEqual(side[0], 60)

    def test_dragged_height(self):
        self.assertEqual(edgerules.dragged_height(200, 30, 1.5), 220)
        self.assertEqual(edgerules.dragged_height(200, -500, 1.0), edgerules.MIN_HEIGHT)


class RailWidthFloor(unittest.TestCase):
    """2026-10-22, «баг с обрезанием окна»: a card needing more than the grip's width
    was cut at its inner side; the panel stands at least as wide as `least()` asks,
    and the rail's window is see-through round the card's rounded corners."""

    VIEWPORT = (100, 150, 1500, 700)

    def setUp(self):
        self.app = _app()
        self.need = 0
        self.edge = hubedge.Edge(
            scale=1.5, width=280, rail=True,
            rest=lambda: 40, work_area=lambda: self.VIEWPORT,
            cursor=lambda: (800, 400), buttons=lambda: False,
            app_active=lambda: True, least=lambda: self.need)

    def tearDown(self):
        self.edge.destroy()

    def test_the_grip_s_width_with_no_card_asking_more(self):
        self.edge.place()
        self.assertEqual(self.edge.host.width(), int(round(280 * 1.5)))

    def test_a_wider_card_widens_the_panel_without_saving_it(self):
        self.need = 390
        self.edge._follow()
        self.assertEqual(self.edge.host.width(), int(round(390 * 1.5)))
        self.assertEqual(self.edge.width, 280)
        self.need = 0
        self.edge._follow()
        self.assertEqual(self.edge.host.width(), int(round(280 * 1.5)))

    def test_the_grip_cannot_go_under_what_the_card_needs(self):
        self.need = 390
        self.edge.set_width(300, save=False)
        self.assertEqual(self.edge.width, 390)

    def test_the_rail_window_is_see_through(self):
        self.assertTrue(self.edge.host.testAttribute(QtCore.Qt.WA_TranslucentBackground))
