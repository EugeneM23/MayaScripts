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


def edge_module():
    from maya_timebar import edge
    return edge


@unittest.skipIf(QT is None, "no Qt")
class Edge(unittest.TestCase):

    motion = False

    def setUp(self):
        from maya_timebar import edge
        self.app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])
        self.window = list(WINDOW)
        self.cursor = [900, 500]
        self.down = [False]
        self.over = [True]
        self.play = [False]
        self.suspend = [False]
        self.link = FakeLink()
        self.edge = edge.BottomEdge(
            lambda parent: bar.make(self.link, 1.0, maya_hubstyle.TOKENS, parent=parent, motion=self.motion),
            window_rect=lambda: tuple(self.window), cursor=lambda: tuple(self.cursor),
            buttons=lambda: self.down[0], app_active=lambda: True, motion=self.motion,
            over_maya=lambda: self.over[0], playing=lambda: self.play[0],
            suspended=lambda: self.suspend[0])
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

    def test_it_stays_out_while_maya_plays(self):
        self.at_edge()
        self.edge.dwell_done()
        self.cursor[:] = [900, 300]
        self.play[0] = True
        self.edge.hide_due()
        self.assertTrue(self.edge.shown)
        self.assertTrue(self.edge.hide_timer.isActive())          # asked again
        self.play[0] = False
        self.edge.hide_due()
        self.assertFalse(self.edge.shown)

    def test_a_bake_brings_it_out_and_keeps_it(self):
        self.cursor[:] = [900, 300]
        for _ in range(edge_module().BAKE_RUN - 1):
            self.edge.on_time()
        self.assertFalse(self.edge.shown)                          # a step or two: no
        self.edge.on_time()
        self.assertTrue(self.edge.shown)
        self.assertTrue(self.edge.baking)
        self.edge.hide_due()
        self.assertTrue(self.edge.shown)                           # not while it bakes
        self.edge._idle()                                          # the bake is done
        self.edge.hide_due()
        self.assertFalse(self.edge.shown)

    def test_steps_with_the_event_loop_between_are_no_bake(self):
        for _ in range(10):
            self.edge.on_time()
            self.edge._idle()
        self.assertFalse(self.edge.shown)

    def test_our_own_walks_with_the_viewport_suspended_are_no_bake(self):
        self.suspend[0] = True
        for _ in range(10):
            self.edge.on_time()
        self.assertFalse(self.edge.shown)

    def test_play_brings_it_out(self):
        self.cursor[:] = [900, 300]
        self.edge.on_time()
        self.assertFalse(self.edge.shown)                          # a time change alone: no
        self.play[0] = True
        self.edge.on_time()
        self.assertTrue(self.edge.shown)
        self.assertTrue(self.edge.host.isVisible())
        if not self.motion:
            self.assertIsNone(self.edge._slide)
            self.assertEqual(self.edge.host.mask().boundingRect().width(), self.edge.host.width())

    def in_band(self):
        x, y, w, h = look.bottom_band(self.window, self.edge.height())
        self.cursor[:] = [x + w // 3, y + h // 2]

    def rest(self, ms):
        for _ in range(int(ms // look.ZONE_POLL_MS)):
            self.edge.zone_tick()

    def test_resting_where_maya_s_slider_stood_brings_it_out(self):
        self.in_band()
        self.rest(look.ZONE_DWELL_MS - look.ZONE_POLL_MS)
        self.assertFalse(self.edge.shown)
        self.rest(look.ZONE_POLL_MS)
        self.assertTrue(self.edge.shown)

    def test_passing_through_the_band_does_not(self):
        self.in_band()
        self.rest(look.ZONE_DWELL_MS - look.ZONE_POLL_MS)
        self.cursor[:] = [900, 300]
        self.edge.zone_tick()
        self.in_band()
        self.rest(look.ZONE_DWELL_MS - look.ZONE_POLL_MS)
        self.assertFalse(self.edge.shown)

    def test_not_with_a_button_held_nor_under_another_window(self):
        self.in_band()
        self.down[0] = True
        self.rest(500)
        self.assertFalse(self.edge.shown)
        self.down[0] = False
        self.over[0] = False
        self.rest(500)
        self.assertFalse(self.edge.shown)

    def test_above_the_band_never(self):
        x, y, w, h = look.bottom_band(self.window, self.edge.height())
        self.cursor[:] = [x + 50, y - 5]
        self.rest(500)
        self.assertFalse(self.edge.shown)

    def test_it_follows_maya_s_window(self):
        self.window[:] = [0, 0, 1200, 700]
        self.edge.place()
        g = self.edge.host.geometry()
        self.assertEqual((g.x(), g.width(), g.y() + g.height()), (0, 1200, 700))


class EdgeMotion(Edge):
    """The burst from the cursor (mockup A, 1.5x slower)."""

    motion = True

    def later(self, ms):
        """Every clock of the burst moved `ms` into the past."""
        b, e = self.edge._slide, self.edge.strip.entrance
        if b is not None:
            b["t0"] -= ms
        if e is not None:
            e["t0"] -= ms

    def mask_width(self):
        return self.edge.host.mask().boundingRect().width()

    def test_play_bursts_it_out_frame_by_frame(self):
        self.cursor[:] = [900, 300]                                # up in the viewport
        self.play[0] = True
        self.edge.on_time()
        self.assertIsNotNone(self.edge._slide)
        self.assertIsNotNone(self.edge.strip.entrance)
        w = self.edge.host.width()
        g = self.edge.host.geometry()
        self.assertAlmostEqual(self.edge._slide["cx"], 900 - g.x())   # from the cursor's x
        self.assertLess(self.mask_width(), 5)
        self.later(look.UNROLL_MS / 3.0)
        self.edge.on_time()                                        # the next frame of playback
        self.assertTrue(5 < self.mask_width() < w)
        self.later(10000)
        self.edge.on_time()
        self.edge.on_time()
        self.assertIsNone(self.edge._slide)
        self.assertIsNone(self.edge.strip.entrance)
        self.assertEqual(self.mask_width(), w)

    def test_resting_on_the_edge_brings_it_out(self):
        self.at_edge()
        self.edge.dwell_done()
        self.assertTrue(self.edge.shown)
        w = self.edge.host.width()
        self.assertLess(self.mask_width(), 5)                       # from a point under the cursor
        self.later(look.UNROLL_MS / 3.0)
        self.edge.slide_tick()
        self.assertTrue(5 < self.mask_width() < w)
        self.later(look.UNROLL_MS)
        self.edge.slide_tick()
        self.assertEqual(self.mask_width(), w)
        self.assertIsNone(self.edge._slide)

    def test_the_nearest_control_pops_first(self):
        self.at_edge()
        self.edge.dwell_done()
        strip = self.edge.strip
        delays = strip.entrance["delays"]
        x = self.cursor[0]
        near = min(strip.moving, key=lambda w: abs(w.mapToGlobal(w.rect().center()).x() - x))
        far = max(strip.moving, key=lambda w: abs(w.mapToGlobal(w.rect().center()).x() - x))
        self.assertLess(delays[near.index], delays[far.index])
        self.later(delays[near.index] + look.POP_OPEN_MS / 2.0)
        self.assertGreater(strip.opening_of(near.index)[0], look.START_SCALE)
        self.assertEqual(strip.opening_of(far.index), (look.START_SCALE, 0.0))

    def test_the_keys_pop_with_them(self):
        self.at_edge()
        self.edge.dwell_done()
        strip = self.edge.strip
        self.assertEqual(strip.entrance_of(self.cursor[0] + 300, self.cursor[1]), (look.START_SCALE, 0.0))
        self.later(strip.entrance["ends"])
        self.assertEqual(strip.entrance_of(self.cursor[0] + 300, self.cursor[1]), (1.0, 1.0))

    def test_leaving_it_sends_it_back(self):
        self.at_edge()
        self.edge.dwell_done()
        self.later(10000)
        self.edge.slide_tick()
        self.cursor[:] = [900, 300]
        self.edge.hide_due()
        self.assertFalse(self.edge.shown)
        b = self.edge._slide
        self.assertFalse(b["showing"])
        self.edge.slide_tick()
        self.assertEqual(self.mask_width(), self.edge.host.width())    # the controls fold first
        self.later(b["after"] + look.CLOSE_MS / 2.0)
        self.edge.slide_tick()
        self.assertLess(self.mask_width(), self.edge.host.width())
        self.later(look.CLOSE_MS)
        self.edge.slide_tick()
        self.assertFalse(self.edge.host.isVisible())
        self.assertTrue(self.edge.sensor.isVisible())

    test_the_pin_keeps_it_out = None
    test_a_drag_in_the_strip_keeps_it_out = None
    test_coming_back_onto_it_stops_the_hide = None


if __name__ == "__main__":
    unittest.main()
