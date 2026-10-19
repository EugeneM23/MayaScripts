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


class Frame(unittest.TestCase):
    """2026-10-09, the animator: «сперва появляется фоновая рамка и вот она
    появляется сильно резко я хочу что бы она выезжала анимацией плавно ...
    А потом выезжала основная панель»: the host shows only its `frame`, which
    slides out first; the hub follows; the frame leaves with the hub."""

    def _edge(self, motion=True):
        _app()
        return hubedge.Edge(scale=1.0, motion=lambda: motion,
                            work_area=lambda: (0, 0, 800, 600),
                            cursor=lambda: (0, 10), buttons=lambda: False,
                            app_active=lambda: True)

    def _run(self, edge, sample, until=None):
        seen = []
        loop_until = QtCore.QDeadlineTimer(3000)
        while edge.sliding() and not loop_until.hasExpired():
            QtWidgets.QApplication.processEvents()
            seen.append(sample())
            if until is not None and until():
                break
        return seen

    def test_the_frame_leads_and_the_hub_follows_close_behind(self):
        edge = self._edge()
        try:
            w = edge.host.width()
            edge.reveal()
            self.assertLess(edge.frame, w)                 # not whole at once
            seen = self._run(edge, lambda: (edge.frame, edge.slot.x()))
            frames = [f for f, _x in seen]
            self.assertEqual(frames, sorted(frames))
            #  the frame starts alone ...
            early = [x for f, x in seen if f < w // 2]
            self.assertTrue(early)
            self.assertTrue(all(x == -w for x in early))
            #  ... the hub comes out while the frame is still coming
            self.assertTrue([x for f, x in seen if f < w and x > -w])
            #  and never runs ahead of it
            for frame, x in seen:
                self.assertGreaterEqual(frame, w + x - 1)
            self.assertEqual((edge.frame, edge.slot.x()), (w, 0))
            self.assertTrue(edge.host.mask().isEmpty())   # at rest: all of it
        finally:
            edge.destroy()

    def test_the_window_shows_only_its_frame(self):
        edge = self._edge()
        try:
            w = edge.host.width()
            edge.reveal()
            self._run(edge, lambda: None,
                      until=lambda: 0 < edge.frame < w // 2)
            self.assertTrue(edge.sliding())
            shown = edge.host.mask().boundingRect()
            self.assertEqual((shown.x(), shown.width()), (0, edge.frame))
            self.assertEqual(shown.height(), edge.host.height())
        finally:
            edge.destroy()

    def test_the_frame_leaves_with_the_hub(self):
        edge = self._edge()
        try:
            w = edge.host.width()
            edge.reveal()
            self._run(edge, lambda: None)
            edge.conceal()
            seen = self._run(edge, lambda: (edge.frame, edge.slot.x()))
            self.assertTrue(seen)
            for frame, x in seen:
                self.assertLessEqual(abs(frame - (w + x)), 1)
            self.assertEqual(edge.frame, 0)
            self.assertFalse(edge.host.isVisible())
        finally:
            edge.destroy()

    def test_a_reveal_turned_back_in_its_frame_phase_takes_the_frame_back(self):
        edge = self._edge()
        try:
            w = edge.host.width()
            edge.reveal()
            self._run(edge, lambda: None, until=lambda: edge.frame > w // 3)
            self.assertEqual(edge.slot.x(), -w)            # still the frame phase
            stood = edge.frame
            edge.conceal()
            frames = [stood] + [f for f in self._run(edge, lambda: edge.frame)]
            self.assertEqual(frames, sorted(frames, reverse=True))
            self.assertEqual(edge.frame, 0)
            self.assertFalse(edge.host.isVisible())
            self.assertTrue(edge.sensor.isVisible())
        finally:
            edge.destroy()

    def test_without_motion_the_frame_is_whole_at_once(self):
        edge = self._edge(motion=False)
        try:
            edge.reveal()
            self.assertFalse(edge.sliding())
            self.assertEqual(edge.frame, edge.host.width())
            self.assertTrue(edge.host.mask().isEmpty())
            edge.conceal()
            self.assertEqual(edge.frame, 0)
            self.assertFalse(edge.host.isVisible())
        finally:
            edge.destroy()

    def test_a_width_change_out_keeps_the_frame_whole(self):
        edge = self._edge(motion=False)
        try:
            edge.reveal()
            edge.set_width(500, save=False)
            self.assertEqual(edge.frame, edge.host.width())
            self.assertTrue(edge.host.mask().isEmpty())
        finally:
            edge.destroy()


class RightSide(unittest.TestCase):
    """2026-10-09, the animator: «Можем добавить опцию выбора стороны
    монитора откуда выезжает наша полка?» - the right edge, mirrored. The
    offset and the frame still count from the screen edge inward."""

    AREA = (100, 20, 1600, 900)          # x 100..1700

    def _edge(self, motion=False, side="right"):
        _app()
        self.point = (1699, 300)
        self.widths = []
        return hubedge.Edge(scale=1.0, width=360, side=side,
                            motion=lambda: motion,
                            on_width=self.widths.append,
                            work_area=lambda: self.AREA,
                            cursor=lambda: self.point,
                            buttons=lambda: False,
                            app_active=lambda: True)

    def _run(self, edge, sample):
        seen = []
        loop_until = QtCore.QDeadlineTimer(3000)
        while edge.sliding() and not loop_until.hasExpired():
            QtWidgets.QApplication.processEvents()
            seen.append(sample())
        return seen

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

    def test_the_frame_grows_from_the_right_and_the_hub_comes_in_after(self):
        edge = self._edge(motion=True)
        try:
            w = edge.host.width()
            edge.reveal()
            seen = self._run(edge, lambda: (
                edge.frame, edge.offset, edge.slot.x(),
                edge.host.mask().boundingRect().getRect()))
            self.assertTrue(seen)
            for frame, offset, x, mask in seen:
                if frame < w:
                    #  only the frame's right part shows
                    self.assertEqual((mask[0], mask[2]),
                                     (w - max(1, frame), max(1, frame)))
                self.assertGreaterEqual(frame, w + offset - 1)
                self.assertEqual(x, 1 - offset)
            xs = [x for _f, _o, x, _m in seen]
            self.assertEqual(xs, sorted(xs, reverse=True))   # leftward
            self.assertTrue([x for f, _o, x, _m in seen if f < w
                             and x < w + 1])   # the hub in before the frame
            self.assertEqual((edge.frame, edge.offset), (w, 0))
            self.assertTrue(edge.host.mask().isEmpty())
        finally:
            edge.destroy()

    def test_it_goes_back_off_the_right_edge(self):
        edge = self._edge(motion=True)
        try:
            w = edge.host.width()
            edge.reveal()
            self._run(edge, lambda: None)
            edge.conceal()
            seen = self._run(edge, lambda: (edge.frame, edge.offset))
            self.assertTrue(seen)
            for frame, offset in seen:
                self.assertLessEqual(abs(frame - (w + offset)), 1)
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

    def test_set_side_stops_a_slide(self):
        edge = self._edge(motion=True, side="left")
        try:
            edge.reveal()
            self.assertTrue(edge.sliding())
            edge.set_side("right")
            self.assertFalse(edge.sliding())
            self.assertEqual((edge.offset, edge.frame), (-360, 0))
        finally:
            edge.destroy()


if __name__ == "__main__":
    unittest.main()


class RailDock(unittest.TestCase):
    """2026-10-17: «вешаем наш реил к боку экрана вьюпорта пусть он там висит
    постоянно, а при клике по иконкам рейла будут выезжать наши разделы» - the rail
    always shows on the viewport's side, the card comes out on a click only."""

    VIEWPORT = (100, 150, 1500, 700)

    def setUp(self):
        self.app = _app()
        self.point = (800, 400)
        self.edge = hubedge.Edge(
            scale=1.0, width=360, motion=lambda: False, rail=True,
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
            scale=1.0, width=360, motion=lambda: False, rail=True,
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


class RailBurst(unittest.TestCase):
    """2026-10-18 (floating windows, spec § 4): the rail card bursts out of the
    icon pressed and folds into the point the close came from; the mask shows
    the rail at once and the card only as far as the burst has grown it."""

    def setUp(self):
        self.app = _app()
        self.card = [(60, 10, 280, 200)]
        self.bursts = []
        self.done = None
        self.shapes = [(70, 20, 110, 50)]          # host-local x0, y0, x1, y1
        self.edges = []

    def tearDown(self):
        for edge in self.edges:
            edge.destroy()

    def burst(self, showing, origin, done, on_shape):
        self.bursts.append((showing, origin))
        for shape in self.shapes:
            on_shape(shape)
        self.done = done
        return True

    def build(self, burst=None, motion=True):
        edge = hubedge.Edge(
            scale=1.0, width=360, motion=lambda: motion, rail=True,
            rest=lambda: 40, shape=lambda: self.card,
            work_area=lambda: (100, 150, 1500, 700),
            cursor=lambda: (800, 400), buttons=lambda: False,
            app_active=lambda: True,
            burst=self.burst if burst is None else burst)
        self.edges.append(edge)
        return edge

    def test_reveal_bursts_from_the_origin_and_shows_the_frame_whole(self):
        edge = self.build()
        edge.reveal(origin=(140, 270))
        self.assertEqual(self.bursts, [(True, (140, 270))])
        self.assertTrue(edge.shown)
        self.assertEqual(edge.frame, edge.host.width())
        x0, y0, x1, y1 = self.shapes[-1]
        self.assertEqual(edge.burst_shape, (x0, y0, x1 - x0, y1 - y0))
        mask = edge.host.mask()
        self.assertTrue(mask.contains(QtCore.QPoint(20, 600)))      # the rail at once
        self.assertTrue(mask.contains(QtCore.QPoint(90, 30)))       # inside the shape
        self.assertFalse(mask.contains(QtCore.QPoint(200, 150)))    # card, not grown yet
        self.done()
        self.assertIsNone(edge.burst_shape)
        self.assertTrue(edge.shown)
        self.assertTrue(edge.host.mask().contains(QtCore.QPoint(200, 150)))

    def test_the_card_hides_under_the_start_box_until_the_first_tick(self):
        self.shapes = []
        edge = self.build()
        edge.reveal(origin=(140, 270))              # host-local (40, 120): the rail
        #  pulled ORIGIN_PAD inside the card (60, 10, 280, 200), as the plan pulls it
        #  and the box kept inside the card (maya_hubburst._box)
        hx, hy = hubedge.hubburst.START_HALF
        x = 60 + hubedge.hubburst.ORIGIN_PAD
        left = max(60, x - hx)
        self.assertEqual(edge.burst_shape, (left, 120 - hy, x + hx - left, 2 * hy))
        mask = edge.host.mask()
        self.assertTrue(mask.contains(QtCore.QPoint(x, 120)))       # the box shows
        self.assertFalse(mask.contains(QtCore.QPoint(200, 150)))

    def test_a_refused_burst_is_asked_before_the_frame_opens(self):
        frames = []

        def refuse(showing, origin, done, on_shape):
            frames.append(edge.frame)
            return False
        edge = self.build(burst=refuse, motion=True)
        rest = edge.frame
        edge.reveal(origin=(140, 270))
        self.assertEqual(frames, [rest])            # not the whole width first

    def test_an_older_burst_is_deaf_once_another_card_bursts(self):
        """Review 2026-10-18: ✕ on card A (its fold running), then B's icon - A's
        fold must not write its shape over B's or send the panel back."""
        calls = []

        def seam(showing, origin, done, on_shape):
            calls.append((showing, done, on_shape))
            return True
        edge = self.build(burst=seam)
        edge.reveal(origin=(140, 270))               # A out
        calls[-1][1]()
        edge.conceal(origin=(300, 180))              # A folding
        a_done, a_shape = calls[-1][1], calls[-1][2]
        edge.reveal(origin=(140, 400))               # B bursting
        b_done, b_shape = calls[-1][1], calls[-1][2]
        b_shape((70, 20, 110, 50))
        a_shape((0, 0, 5, 5))
        a_done()
        self.assertTrue(edge.shown)
        self.assertEqual(edge.frame, edge.host.width())
        self.assertEqual(edge.burst_shape, (70, 20, 40, 30))
        b_done()
        self.assertTrue(edge.shown)
        self.assertIsNone(edge.burst_shape)

    def test_the_visible_rects_follow_the_burst(self):
        edge = self.build()
        edge.reveal(origin=(140, 270))
        self.assertEqual(edge.visible_rects(),
                         [(100, 150, 40, 700), (170, 170, 40, 30)])

    def test_conceal_folds_into_its_point_then_rests_on_the_rail(self):
        edge = self.build()
        edge.reveal(origin=(140, 270))
        self.done()
        edge.conceal(origin=(300, 180))
        self.assertEqual(self.bursts[-1], (False, (300, 180)))
        self.assertEqual(edge.frame, edge.host.width())          # still folding
        self.done()
        self.assertEqual(edge.frame, min(edge.host.width(), edge.rest_px()))
        self.assertFalse(edge.shown)
        self.assertEqual(edge.host.mask().boundingRect().getRect(), (0, 0, 40, 700))
        self.assertTrue(edge.host.isVisible())

    def test_without_a_burst_the_old_slide_runs(self):
        edge = self.build(burst=lambda *a: False, motion=False)
        edge.reveal(origin=(140, 270))
        self.assertTrue(edge.shown)
        self.assertIsNone(edge.burst_shape)
        self.assertTrue(edge.host.mask().contains(QtCore.QPoint(200, 150)))  # the card

    def test_a_refused_or_raising_burst_slides(self):
        def boom(*_a):
            raise RuntimeError("no")
        for burst in (lambda *a: False, boom):
            edge = self.build(burst=burst)
            with mock.patch("traceback.print_exc"):
                edge.reveal(origin=(140, 270))
            self.assertTrue(edge.shown)
            self.assertIsNone(edge.burst_shape)

    def test_no_origin_or_no_motion_never_asks_the_burst(self):
        edge = self.build()
        edge.reveal()
        edge2 = self.build(motion=False)
        edge2.reveal(origin=(140, 270))
        self.assertEqual(self.bursts, [])
        self.assertTrue(edge.shown and edge2.shown)

    def test_a_reveal_during_a_fold_bursts_out_again(self):
        edge = self.build()
        edge.reveal(origin=(140, 270))
        self.done()
        edge.conceal(origin=(300, 180))
        edge.reveal(origin=(140, 300))
        self.assertEqual(self.bursts[-1], (True, (140, 300)))
        self.done()
        self.assertTrue(edge.shown)
        self.assertEqual(edge.frame, edge.host.width())


class RailBurstThroughTheHub(unittest.TestCase):
    """2026-10-18: the real road - maya_hub's focus / ✕ on a real windowed Skin
    in a real rail Edge, the Burster on the card's look-B frame telling the edge
    its shape in host coordinates."""

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
        self.motion = mock.patch("maya_hubmotion.enabled", lambda: True)
        self.motion.start()
        self.edge = hubedge.Edge(
            scale=1.0, width=360, motion=lambda: True, rail=True,
            rest=hub._rail_rest, shape=hub._rail_shape, burst=hub._rail_burst,
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
        self.motion.stop()
        for card in (self.card, self.beta):
            burster = getattr(card, "burster", None)
            if burster is not None:
                burster.stop(quiet=True)
        hub.cmds, hub._SKIN, hub._cursor, self.hubqt.find, self.hubqt.path_of, \
            listeners = self.saved
        self.style._LISTENERS[:] = listeners
        hubedge.state().clear()
        hubedge.state().update(self.state)
        self.skin.destroy()
        self.edge.destroy()

    def finish(self):
        """The burst to its end: the picture taken, the last tick."""
        burster = self.card.burster
        self.card.frame.grab()
        burster.effect.ms = burster.effect.plan.total
        burster.tick_now()

    def test_a_rail_click_bursts_the_card_out_of_its_icon(self):
        icon = self.skin.jumps["alpha"]
        centre = icon.mapToGlobal(QtCore.QPoint(icon.width() // 2, icon.height() // 2))
        self.edge._shown = False
        self.hub.focus("alpha")
        burster = self.card.burster
        self.assertTrue(burster.busy())
        self.assertEqual(burster._origin, (centre.x(), centre.y()))
        self.assertTrue(self.edge.shown)
        #  until the first tick the card shows as the start box: about the icon,
        #  pulled inside the card as the plan pulls it
        x, y, w, h = self.edge.burst_shape
        at = self.edge.host.mapFromGlobal(centre)
        card = self.card.frame.geometry()
        top = self.card.frame.mapTo(self.edge.host, QtCore.QPoint(0, 0))
        self.assertGreaterEqual(x, top.x())
        self.assertLessEqual(x + w, top.x() + card.width())
        self.assertTrue(y <= at.y() <= y + h or not (top.y() <= at.y() <= top.y() + card.height()))
        #  a tick: the shape in the host's coordinates
        self.card.frame.grab()
        burster.effect.ms = 60.0
        burster.tick_now()
        from maya_hubburst import at as state_at
        x0, y0, x1, y1 = state_at(burster.effect.plan, 60.0).shape
        off = self.card.frame.mapTo(self.edge.host, QtCore.QPoint(0, 0))
        self.assertEqual(self.edge.burst_shape,
                         (int(round(x0 + off.x())), int(round(y0 + off.y())),
                          int(round(x1 - x0)), int(round(y1 - y0))))
        self.finish()
        self.assertIsNone(self.edge.burst_shape)
        self.assertFalse(burster.busy())
        self.assertTrue(self.edge.shown)

    def test_the_close_folds_the_card_into_the_press_and_rests_on_the_rail(self):
        self.edge._shown = False
        self.hub.focus("alpha")
        self.finish()
        self.skin.cards["alpha"].close.click()
        burster = self.card.burster
        self.assertTrue(burster.busy())
        self.assertEqual(burster._origin, (600, 500))
        self.assertFalse(burster.effect.opening)
        self.finish()
        self.assertFalse(self.edge.shown)
        self.assertEqual(self.edge.frame, min(self.edge.host.width(), self.edge.rest_px()))
        self.assertIsNone(self.edge.burst_shape)

    def test_the_burst_runs_with_no_paint_at_all(self):
        """Review 2026-10-18: a frame masked to nothing may never be painted in
        Maya; the plan is made on the first tick, the shape grows, the burst
        ends at the plan's total, not at the driver's MAX_MS."""
        self.edge._shown = False
        self.hub.focus("alpha")
        burster = self.card.burster
        start = self.edge.burst_shape
        burster.effect.ms = 120.0
        burster.tick_now()                         # no grab: the plan from the tick
        plan = burster.effect.plan
        self.assertIsNotNone(plan)
        self.assertLess(plan.total, 1200)
        grown = self.edge.burst_shape
        self.assertGreater(grown[2] * grown[3], start[2] * start[3])
        burster.effect.ms = plan.total
        burster.tick_now()
        self.assertFalse(burster.busy())
        self.assertIsNone(self.edge.burst_shape)
        self.assertTrue(self.edge.shown)

    def test_a_fold_cut_short_by_another_card_never_hides_it(self):
        """Review 2026-10-18: ✕ on alpha (its fold running), then beta's icon -
        alpha's Burster stopped, its end never heard, beta out."""
        self.edge._shown = False
        self.hub.focus("alpha")
        self.finish()
        self.card.close.click()
        alpha = self.card.burster
        self.assertTrue(alpha.busy())
        self.hub.focus("beta")
        self.assertFalse(alpha.busy())
        beta = self.beta.burster
        self.assertTrue(beta.busy())
        self.assertTrue(self.edge.shown)
        alpha._finish()                            # a late end of the old fold
        self.assertTrue(self.edge.shown)
        beta.effect.ms = 2000.0
        beta.tick_now()
        self.assertTrue(self.edge.shown)
        self.assertEqual(self.edge.frame, self.edge.host.width())
