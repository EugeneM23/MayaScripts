"""maya_hubwindow - the floating window's and the rail card's look B and burst. Offscreen Qt.
Spec: docs/superpowers/specs/2026-10-18-floating-windows-design.md."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tests  # noqa: F401

from PySide6 import QtCore, QtGui, QtWidgets

import maya_hubburst as hubburst
import maya_hubmotion as hubmotion
import maya_hubstyle as hubstyle
import maya_hubwindow as hubwindow
from unittest import mock


def _app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _rgb(image, x, y):
    c = image.pixelColor(x, y)
    return (c.red(), c.green(), c.blue())


def _hex(name):
    v = hubstyle.TOKENS[name]
    return (int(v[1:3], 16), int(v[3:5], 16), int(v[5:7], 16))


class Frame(unittest.TestCase):

    def setUp(self):
        self.app = _app()
        self.frame = hubwindow.frame_class()(1.0)
        self.frame.resize(240, 160)
        layout = QtWidgets.QVBoxLayout(self.frame)
        layout.setContentsMargins(5, 34, 5, 5)
        self.frame.content = QtWidgets.QFrame()
        self.frame.content.setObjectName("testContent")
        layout.addWidget(self.frame.content)
        hubwindow.dress(self.frame, 1.0)
        self.frame.show()
        self.app.processEvents()

    def render(self):
        image = QtGui.QImage(240, 160, QtGui.QImage.Format_ARGB32)
        image.fill(0)
        self.frame.render(image)
        return image

    def test_the_frame_face_is_the_panel_and_the_content_the_card(self):
        image = self.render()
        self.assertEqual(_rgb(image, 120, 20), _hex("panel"))
        self.assertEqual(_rgb(image, 120, 100), _hex("card"))

    def test_no_stripe_and_no_accent_along_the_edges(self):
        image = self.render()
        accent = _hex("accent")
        for x, y in ((2, 80), (120, 1), (4, 40)):
            self.assertNotEqual(_rgb(image, x, y), accent)

    def test_a_lit_frame_paints_the_accent_ring(self):
        self.frame.level = 1.0
        image = self.render()
        r, g, b = _rgb(image, 120, 1)
        self.assertGreater(r, 180)


class Pill(unittest.TestCase):

    def setUp(self):
        self.app = _app()
        self.pill = hubwindow.pill_class()("x", 1.0)
        self.pill.show()

    def test_a_pill_is_its_24_by_22_face_and_4_px_round_it(self):
        self.assertEqual((self.pill.width(), self.pill.height()), (32, 30))

    def test_a_hovered_pill_glows_outside_its_face(self):
        with mock.patch.object(hubmotion, "enabled", lambda: False):
            self.pill.hover(True)
        image = QtGui.QImage(32, 30, QtGui.QImage.Format_ARGB32)
        image.fill(0)
        self.pill.render(image)
        face = QtCore.QRect(4, 4, 24, 22)
        glow = 0
        for y in range(30):
            for x in range(32):
                c = image.pixelColor(x, y)
                if face.contains(x, y) or c.alpha() == 0:
                    continue
                if c.red() > c.blue() + 20:
                    glow += 1
        self.assertGreater(glow, 20)

    def test_hover_lifts_it_and_rest_stops_its_timer(self):
        self.pill.hover(True)
        self.pill.advance(200.0)
        self.assertAlmostEqual(self.pill.level, 1.0, places=2)
        self.pill.hover(False)
        self.pill.advance(400.0)
        self.assertEqual(self.pill.level, 0.0)
        self.assertFalse(self.pill.timer.isActive())

    def test_a_press_flashes_for_120_ms(self):
        self.pill.press()
        self.assertGreater(self.pill.flash_at(0.0), 0.9)
        self.assertEqual(self.pill.flash_at(121.0), 0.0)

    def test_animations_off_lands_at_once(self):
        with mock.patch.object(hubmotion, "enabled", lambda: False):
            self.pill.hover(True)
            self.assertEqual(self.pill.level, 1.0)


class Burst(unittest.TestCase):

    def setUp(self):
        self.app = _app()
        self.frame = hubwindow.frame_class()(1.0)
        self.frame.resize(240, 160)
        self.frame.show()
        self.app.processEvents()
        self.ended = []
        self.burster = hubwindow.Burster(
            self.frame, lambda: [(5, 5, 230, 24), (5, 120, 230, 30)],
            lambda: (42, 44, 48), 1.0)

    def test_a_burst_runs_and_ends_plain(self):
        origin = self.frame.mapToGlobal(QtCore.QPoint(10, 10))
        self.assertTrue(self.burster.run(True, (origin.x(), origin.y()),
                                         lambda: self.ended.append(1)))
        self.assertTrue(self.burster.busy())
        self.frame.grab()
        self.burster.effect.ms = self.burster.effect.plan.total
        self.burster.tick_now()
        self.assertEqual(self.ended, [1])
        self.assertFalse(self.burster.busy())
        self.assertFalse(self.burster.effect.isEnabled())

    def test_the_shape_is_reported_each_tick(self):
        shapes = []
        origin = self.frame.mapToGlobal(QtCore.QPoint(10, 10))
        self.burster.run(True, (origin.x(), origin.y()), lambda: None, on_tick=shapes.append)
        self.frame.grab()
        self.burster.effect.ms = 40.0
        self.burster.tick_now()
        self.assertTrue(shapes)
        x0, y0, x1, y1 = shapes[-1]
        self.assertLess(x1 - x0, 240)

    def test_a_burst_ticks_without_any_paint(self):
        """Review 2026-10-18: the plan is made on the first tick when no paint
        made it; it ends at the plan's total."""
        shapes, ended = [], []
        origin = self.frame.mapToGlobal(QtCore.QPoint(10, 10))
        self.burster.run(True, (origin.x(), origin.y()), lambda: ended.append(1),
                         on_tick=shapes.append)
        self.burster.effect.ms = 40.0
        self.burster.tick_now()
        self.assertIsNotNone(self.burster.effect.plan)
        self.assertEqual(len(shapes), 1)
        self.burster.effect.ms = self.burster.effect.plan.total
        self.burster.tick_now()
        self.assertEqual(ended, [1])

    def test_the_light_is_added_inside_the_shape(self):
        origin = self.frame.mapToGlobal(QtCore.QPoint(120, 80))
        self.burster.run(True, (origin.x(), origin.y()), lambda: None)
        self.frame.grab()
        self.burster.effect.ms = 30.0
        image = self.frame.grab().toImage()
        plan = self.burster.effect.plan
        edge = [e for e in hubburst.light(plan, 30.0).edges if e[0] == "x"][0]
        lit = image.pixelColor(int(edge[1]), 80)
        self.assertGreater(lit.red(), 120)

    def test_the_light_stays_inside_the_rounded_corners(self):
        origin = self.frame.mapToGlobal(QtCore.QPoint(120, 80))
        self.burster.run(True, (origin.x(), origin.y()), lambda: None)
        self.frame.grab()
        effect = self.burster.effect
        effect.ms = 30.0
        image = self.frame.grab().toImage()
        state = hubburst.at(effect.plan, 30.0)
        x0, y0, x1, y1 = state.shape
        self.assertGreater(state.radius, 3.0)
        lit = hubburst.light(effect.plan, 30.0)
        self.assertTrue(lit.edges)
        # the bounding rect's own corner lies outside the rounded shape: no light there
        c = image.pixelColor(int(x0), int(y0))
        self.assertLess(c.red(), 60)

    def test_with_animations_off_nothing_runs(self):
        with mock.patch.object(hubmotion, "enabled", lambda: False):
            self.assertFalse(self.burster.run(True, (0, 0), lambda: None))
        self.assertFalse(self.burster.busy())
