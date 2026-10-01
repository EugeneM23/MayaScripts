"""The trail engine's frame maths, pure."""

import unittest

from maya_com import frames


class Range(unittest.TestCase):

    def test_playback_is_the_playback_range(self):
        self.assertEqual(frames.trail_range("playback", (0, 100), 40, 20,
                                            (-10, 120)), (0, 100))

    def test_around_is_the_current_frame_both_ways(self):
        self.assertEqual(frames.trail_range("around", (0, 100), 40, 20,
                                            (-10, 120)), (20, 60))

    def test_around_is_clipped_to_the_animation_range(self):
        self.assertEqual(frames.trail_range("around", (0, 100), 5, 20,
                                            (0, 120)), (0, 25))

    def test_fractional_ranges_snap_outward(self):
        self.assertEqual(frames.trail_range("playback", (0.4, 88.7), 0, 0,
                                            (0, 100)), (0, 89))

    def test_frames_of_a_range(self):
        self.assertEqual(frames.frames_of((3, 6)), [3, 4, 5, 6])


class Changed(unittest.TestCase):

    def test_only_the_frames_whose_value_moved(self):
        before = {0: 1.0, 1: 2.0, 2: 3.0, 3: 4.0}
        after = {0: 1.0, 1: 2.5, 2: 3.0, 3: 4.0 + 1e-12}
        self.assertEqual(frames.changed_frames(before, after), {1})

    def test_a_frame_new_on_one_side_is_changed(self):
        self.assertEqual(frames.changed_frames({0: 1.0}, {0: 1.0, 1: 2.0}), {1})


class Order(unittest.TestCase):

    def test_nearest_first_earlier_wins_a_tie(self):
        self.assertEqual(frames.nearest_first({0, 4, 5, 6, 10}, 5),
                         [5, 4, 6, 0, 10])

    def test_budget(self):
        self.assertEqual(frames.budget(5.0, 25.0, 5.0), 4)
        self.assertEqual(frames.budget(40.0, 25.0, 5.0), 1)
        #  a cheap frame: two at least, or the walk back eats half the slice
        self.assertEqual(frames.budget(15.0, 40.0, 15.0), 2)
        self.assertEqual(frames.budget(0.0, 25.0, 5.0), frames.MAX_BATCH)


class Rerange(unittest.TestCase):

    def test_new_frames_are_dirty_and_known_points_stay(self):
        points = {0: (0, 0, 0), 1: (1, 0, 0), 2: (2, 0, 0)}
        kept, dirty = frames.rerange(points, (1, 4))
        self.assertEqual(sorted(kept), [1, 2])
        self.assertEqual(dirty, {3, 4})

    def test_the_trail_points_in_frame_order(self):
        points = {2: (2, 0, 0), 0: (0, 0, 0), 1: (1, 0, 0)}
        self.assertEqual(frames.ordered_points(points, (0, 2)),
                         [(0, 0, 0), (1, 0, 0), (2, 0, 0)])

    def test_a_hole_takes_the_nearest_known_point(self):
        """A frame not yet computed is drawn where its neighbour is, so the
        line never jumps to the origin while the engine catches up."""
        points = {0: (0, 0, 0), 3: (3, 0, 0)}
        self.assertEqual(frames.ordered_points(points, (0, 3)),
                         [(0, 0, 0), (0, 0, 0), (3, 0, 0), (3, 0, 0)])


if __name__ == "__main__":
    unittest.main()
