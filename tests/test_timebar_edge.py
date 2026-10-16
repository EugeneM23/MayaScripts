"""The Time Bar at the bottom edge of Maya's window (2026-10-16), offscreen: hidden
with its sensor up, out when the cursor rests on the edge, back when it leaves,
kept out by the pin, a drag, a menu - on a fake window and cursor.

Spec: docs/superpowers/specs/2026-10-16-time-bar-design.md
"""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import maya_hubqt
    QT = maya_hubqt.qt()
except Exception:                                            # noqa: BLE001
    QT = None

import maya_hubstyle
from maya_timebar import bar, look

from tests.test_timebar_bar import FakeLink

WINDOW = [100, 50, 1600, 900]


@unittest.skipIf(QT is None, "no Qt")
class Edge(unittest.TestCase):

    motion = False

    def setUp(self):
        from maya_timebar import edge
        self.app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])
        self.window = list(WINDOW)
        self.cursor = [900, 500]
        self.down = [False]
        self.link = FakeLink()
        self.edge = edge.BottomEdge(
            lambda parent: bar.make(self.link, 1.0, maya_hubstyle.TOKENS, parent=parent, motion=self.motion),
            window_rect=lambda: tuple(self.window), cursor=lambda: tuple(self.cursor),
            buttons=lambda: self.down[0], app_active=lambda: True, motion=self.motion)
        self.addCleanup(self.edge.destroy)

    def at_edge(self):
        x, y, w, h = look.sensor_band(self.window, 2)
        self.cursor[:] = [x + w // 2, y + 1]

    def test_it_starts_hidden_with_the_sensor_along_the_bottom(self):
        self.assertFalse(self.edge.shown)
        self.assertFalse(self.edge.host.isVisible())
        self.assertTrue(self.edge.sensor.isVisible())
        g = self.edge.sensor.geometry()
        self.assertEqual((g.x(), g.y(), g.width(), g.height()), look.sensor_band(self.window, 2))
        self.assertTrue(self.edge.strip.pin.isVisibleTo(self.edge.strip))

    def test_the_host_is_the_bottom_band(self):
        g = self.edge.host.geometry()
        self.assertEqual((g.x(), g.width()), (100, 1600))
        self.assertEqual(g.y() + g.height(), 950)

    def test_resting_on_the_edge_brings_it_out(self):
        self.at_edge()
        self.edge.dwell_done()
        self.assertTrue(self.edge.shown)
        self.assertTrue(self.edge.host.isVisible())
        self.assertFalse(self.edge.sensor.isVisible())
        self.assertEqual(self.edge.offset, 0)

    def test_not_from_elsewhere_nor_with_a_button_held(self):
        self.edge.dwell_done()
        self.assertFalse(self.edge.shown)
        self.at_edge()
        self.down[0] = True
        self.edge.dwell_done()
        self.assertFalse(self.edge.shown)

    def test_leaving_it_sends_it_back(self):
        self.at_edge()
        self.edge.dwell_done()
        self.cursor[:] = [900, 300]
        self.edge.watch_tick()
        self.assertTrue(self.edge.hide_timer.isActive())
        self.edge.hide_due()
        self.assertFalse(self.edge.shown)
        self.assertFalse(self.edge.host.isVisible())
        self.assertTrue(self.edge.sensor.isVisible())

    def test_coming_back_onto_it_stops_the_hide(self):
        self.at_edge()
        self.edge.dwell_done()
        self.cursor[:] = [900, 300]
        self.edge.watch_tick()
        g = self.edge.host.geometry()
        self.cursor[:] = [g.x() + 20, g.y() + 20]
        self.edge.watch_tick()
        self.assertFalse(self.edge.hide_timer.isActive())

    def test_the_pin_keeps_it_out(self):
        self.at_edge()
        self.edge.dwell_done()
        self.edge.strip.pin.click()
        self.assertTrue(self.edge.pinned)
        self.cursor[:] = [900, 300]
        self.edge.hide_due()
        self.assertTrue(self.edge.shown)
        self.edge.strip.pin.click()
        self.assertFalse(self.edge.pinned)
        self.edge.hide_due()
        self.assertFalse(self.edge.shown)

    def test_a_drag_in_the_strip_keeps_it_out(self):
        self.at_edge()
        self.edge.dwell_done()
        self.cursor[:] = [900, 300]
        self.edge.strip.timeline.drag = ("now", None, self.edge.strip.timeline.track())
        self.edge.hide_due()
        self.assertTrue(self.edge.shown)
        self.edge.strip.timeline.drag = None
        self.edge.hide_due()
        self.assertFalse(self.edge.shown)

    def test_it_follows_maya_s_window(self):
        self.window[:] = [0, 0, 1200, 700]
        self.edge.place()
        g = self.edge.host.geometry()
        self.assertEqual((g.x(), g.width(), g.y() + g.height()), (0, 1200, 700))


class EdgeMotion(Edge):

    motion = True

    def test_resting_on_the_edge_brings_it_out(self):
        self.at_edge()
        self.edge.dwell_done()
        self.assertTrue(self.edge.shown)
        h = self.edge.host.height()
        started, showing, start = self.edge._slide
        self.edge._slide = (self.edge.strip.clock() - look.SLIDE_MS / 3.0, True, start)
        self.edge.slide_tick()
        self.assertTrue(0 < self.edge.offset < h)
        self.edge._slide = (self.edge.strip.clock() - look.SLIDE_MS - 1, True, start)
        self.edge.slide_tick()
        self.assertEqual(self.edge.offset, 0)

    def test_leaving_it_sends_it_back(self):
        self.at_edge()
        self.edge.dwell_done()
        self.edge._slide = (self.edge.strip.clock() - look.SLIDE_MS - 1, True, self.edge.host.height())
        self.edge.slide_tick()
        self.cursor[:] = [900, 300]
        self.edge.hide_due()
        self.assertFalse(self.edge.shown)
        self.edge._slide = (self.edge.strip.clock() - look.SLIDE_BACK_MS - 1, False, 0)
        self.edge.slide_tick()
        self.assertEqual(self.edge.offset, self.edge.host.height())
        self.assertFalse(self.edge.host.isVisible())

    test_the_pin_keeps_it_out = None
    test_a_drag_in_the_strip_keeps_it_out = None
    test_coming_back_onto_it_stops_the_hide = None


if __name__ == "__main__":
    unittest.main()
