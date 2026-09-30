"""Where the ghost goes, when it lets the mouse through, when a frame is due."""

import unittest

from maya_graphoverlay import geometry


class HostRect(unittest.TestCase):

    def test_the_measured_case_lands_the_canvas_on_the_viewport(self):
        """2026-09-30: host (300, 250, 900, 560), canvas (305, 253, 892,
        554), viewport (462, 374, 861, 500) - and the canvas came out on the
        viewport pixel for pixel."""
        self.assertEqual(geometry.host_rect((462, 374, 861, 500),
                                            (300, 250, 900, 560),
                                            (305, 253, 892, 554)),
                         (457, 371, 869, 506))

    def test_already_aligned_is_a_fixed_point(self):
        host, canvas = (457, 371, 869, 506), (462, 374, 861, 500)
        self.assertEqual(geometry.host_rect(canvas, host, canvas), host)


class Usable(unittest.TestCase):

    def test_a_rectangle_with_area(self):
        self.assertTrue(geometry.usable((0, 0, 10, 10)))

    def test_nothing_or_a_flat_one(self):
        self.assertFalse(geometry.usable(None))
        self.assertFalse(geometry.usable((0, 0, 0, 10)))
        self.assertFalse(geometry.usable((0, 0, 10, 0)))


class LetThrough(unittest.TestCase):

    def test_alt_is_the_camera(self):
        self.assertTrue(geometry.let_through(True, True, True))

    def test_without_alt_the_graph_takes_the_click(self):
        self.assertFalse(geometry.let_through(False, True, True))

    def test_maya_behind_or_no_viewport(self):
        self.assertTrue(geometry.let_through(False, False, True))
        self.assertTrue(geometry.let_through(False, True, False))


class DueIn(unittest.TestCase):

    def test_the_first_frame_is_due_now(self):
        self.assertEqual(geometry.due_in(10.0, None, 0.015), 0.0)

    def test_too_soon_waits_out_the_rest(self):
        self.assertAlmostEqual(geometry.due_in(10.005, 10.0, 0.015), 0.010)

    def test_late_is_now(self):
        self.assertEqual(geometry.due_in(11.0, 10.0, 0.015), 0.0)


if __name__ == "__main__":
    unittest.main()
