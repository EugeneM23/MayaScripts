"""Where the ghost goes, when it lets the mouse through, when a frame is due."""

import unittest

from maya_graphoverlay import geometry


class DefaultRect(unittest.TestCase):
    """The window's first place: the lower right of the viewport, a share of
    its size, never smaller than a usable graph (2026-10-02)."""

    def test_a_share_of_the_viewport_in_its_lower_right(self):
        self.assertEqual(geometry.default_rect((0, 0, 1000, 800)),
                         (1000 - 600 - 12, 800 - 400 - 12, 600, 400))

    def test_never_smaller_than_a_usable_graph(self):
        left, top, w, h = geometry.default_rect((100, 100, 400, 300))
        self.assertEqual((w, h), (400, 300))      # the viewport is the limit
        self.assertEqual((left, top), (100, 100))

    def test_a_small_viewport_keeps_the_window_on_it(self):
        left, top, w, h = geometry.default_rect((200, 50, 600, 260))
        self.assertGreaterEqual(left, 200)
        self.assertGreaterEqual(top, 50)
        self.assertLessEqual(left + w, 200 + 600)
        self.assertLessEqual(top + h, 50 + 260)


class OnSomeScreen(unittest.TestCase):
    """A remembered window on a monitor that is gone is put back on screen."""

    SCREENS = [(0, 0, 1920, 1080), (1920, 0, 1920, 1080)]

    def test_a_window_on_a_screen_is_kept(self):
        self.assertTrue(geometry.on_some_screen((100, 100, 500, 400),
                                                self.SCREENS))

    def test_a_window_on_the_second_screen_is_kept(self):
        self.assertTrue(geometry.on_some_screen((2000, 100, 500, 400),
                                                self.SCREENS))

    def test_a_window_on_no_screen_is_not(self):
        self.assertFalse(geometry.on_some_screen((5000, 100, 500, 400),
                                                 self.SCREENS))

    def test_a_sliver_at_the_edge_does_not_count(self):
        self.assertFalse(geometry.on_some_screen((1910, 100, 500, 400),
                                                 [(0, 0, 1920, 1080)]))

    def test_nothing_remembered_is_not_on_screen(self):
        self.assertFalse(geometry.on_some_screen(None, self.SCREENS))
        self.assertFalse(geometry.on_some_screen((0, 0, 0, 0), self.SCREENS))


class ChromeBands(unittest.TestCase):
    """The Graph Editor's own chrome - menus, toolbar, channel list - is
    everything of the host outside its curve area (2026-09-30, the
    animator: «я не могу выделить отдельно каналы... и нет остальных
    инструментов»)."""

    def test_the_four_bands_around_the_canvas(self):
        self.assertEqual(geometry.chrome_bands((1526, 1044),
                                               (320, 70, 1200, 970)),
                         [(0, 0, 1526, 70), (0, 1040, 1526, 4),
                          (0, 70, 320, 970), (1520, 70, 6, 970)])

    def test_empty_bands_are_left_out(self):
        self.assertEqual(geometry.chrome_bands((100, 50), (0, 20, 100, 30)),
                         [(0, 0, 100, 20)])

    def test_a_canvas_filling_the_host_leaves_no_chrome(self):
        self.assertEqual(geometry.chrome_bands((100, 50), (0, 0, 100, 50)), [])


class Usable(unittest.TestCase):

    def test_a_rectangle_with_area(self):
        self.assertTrue(geometry.usable((0, 0, 10, 10)))

    def test_nothing_or_a_flat_one(self):
        self.assertFalse(geometry.usable(None))
        self.assertFalse(geometry.usable((0, 0, 0, 10)))
        self.assertFalse(geometry.usable((0, 0, 10, 0)))


class DueIn(unittest.TestCase):

    def test_the_first_frame_is_due_now(self):
        self.assertEqual(geometry.due_in(10.0, None, 0.015), 0.0)

    def test_too_soon_waits_out_the_rest(self):
        self.assertAlmostEqual(geometry.due_in(10.005, 10.0, 0.015), 0.010)

    def test_late_is_now(self):
        self.assertEqual(geometry.due_in(11.0, 10.0, 0.015), 0.0)


if __name__ == "__main__":
    unittest.main()
