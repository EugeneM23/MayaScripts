"""maya_hubedge: the edge panel's windows and controller, offscreen.

Every timer is driven by calling the controller's handlers directly; the
cursor, the mouse buttons, the work area and whether Maya is the active
application come through the constructor's seams. Animations are off unless
the test is about the slide.

Spec: docs/superpowers/specs/2026-10-08-hub-compact-and-edge-panel-design.md
"""

import os
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtWidgets

import maya_edgerules as rules
import maya_hubedge as hubedge


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
            scale=1.0, width=360, motion=lambda: False,
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
        other = hubedge.Edge(scale=1.0, motion=lambda: False,
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
        edge = hubedge.Edge(scale=1.5, width=360, motion=lambda: False,
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
        edge = hubedge.Edge(motion=lambda: False)
        try:
            self.assertEqual(edge.host.height(),
                             hubedge._maya_work_area()[3])
            self.assertEqual(edge.width, rules.WIDTH)
        finally:
            edge.destroy()
        self.assertFalse(edge.alive())


class Slide(unittest.TestCase):

    def test_a_slide_moves_the_slot_in_from_off_the_edge(self):
        _app()
        edge = hubedge.Edge(scale=1.0, motion=lambda: True,
                            work_area=lambda: (0, 0, 800, 600),
                            cursor=lambda: (0, 10), buttons=lambda: False,
                            app_active=lambda: True)
        try:
            edge.reveal()
            self.assertTrue(edge.sliding())
            xs = []
            loop_until = QtCore.QDeadlineTimer(1500)
            while edge.sliding() and not loop_until.hasExpired():
                QtWidgets.QApplication.processEvents()
                xs.append(edge.slot.x())
            self.assertEqual(edge.slot.x(), 0)
            self.assertEqual(xs, sorted(xs))
            self.assertLess(xs[0], 0)
        finally:
            edge.destroy()

    def test_a_slide_out_hides_the_host_at_its_end(self):
        _app()
        edge = hubedge.Edge(scale=1.0, motion=lambda: True,
                            work_area=lambda: (0, 0, 800, 600),
                            cursor=lambda: (0, 10), buttons=lambda: False,
                            app_active=lambda: True)
        try:
            edge.reveal()
            loop_until = QtCore.QDeadlineTimer(1500)
            while edge.sliding() and not loop_until.hasExpired():
                QtWidgets.QApplication.processEvents()
            edge.conceal()
            self.assertTrue(edge.sliding())
            self.assertTrue(edge.host.isVisible())     # until the slide ends
            xs = []
            loop_until = QtCore.QDeadlineTimer(1500)
            while edge.sliding() and not loop_until.hasExpired():
                QtWidgets.QApplication.processEvents()
                xs.append(edge.slot.x())
            self.assertEqual(xs, sorted(xs, reverse=True))
            self.assertEqual(edge.slot.x(), -edge.host.width())
            self.assertFalse(edge.host.isVisible())
            self.assertTrue(edge.sensor.isVisible())
        finally:
            edge.destroy()

    def test_a_reveal_mid_slide_out_turns_back_from_where_it_stands(self):
        _app()
        edge = hubedge.Edge(scale=1.0, motion=lambda: True,
                            work_area=lambda: (0, 0, 800, 600),
                            cursor=lambda: (0, 10), buttons=lambda: False,
                            app_active=lambda: True)
        try:
            edge.reveal()
            loop_until = QtCore.QDeadlineTimer(1500)
            while edge.sliding() and not loop_until.hasExpired():
                QtWidgets.QApplication.processEvents()
            edge.conceal()
            loop_until = QtCore.QDeadlineTimer(1500)
            while (edge.slot.x() > -100 and edge.sliding()
                   and not loop_until.hasExpired()):
                QtWidgets.QApplication.processEvents()
            stood = edge.slot.x()
            self.assertTrue(edge.sliding())               # caught mid-way
            self.assertGreater(stood, -edge.host.width())
            edge.reveal()
            xs = [edge.slot.x()]
            loop_until = QtCore.QDeadlineTimer(1500)
            while edge.sliding() and not loop_until.hasExpired():
                QtWidgets.QApplication.processEvents()
                xs.append(edge.slot.x())
            self.assertGreaterEqual(xs[0], stood - 1)    # no jump back out
            self.assertEqual(xs, sorted(xs))
            self.assertEqual(edge.slot.x(), 0)
            self.assertTrue(edge.host.isVisible())
        finally:
            edge.destroy()


if __name__ == "__main__":
    unittest.main()
