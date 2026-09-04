"""The Curve Overlay's arithmetic, proved with no Maya in the room.

Every bug this kind of tool has -- the key grabbed off to one side, the
marquee catching a neighbour, the drag drifting a frame over 800 events --
lives in `mapping.py`, which is why it is pure and why this file is long.
"""

import os
import subprocess
import sys
import unittest

from maya_curveview import mapping


class TestPurity(unittest.TestCase):
    """mapping.py must stay importable with neither Maya nor Qt loaded.

    Checked in a fresh interpreter: by the time the rest of the suite has
    run, maya.cmds and Qt are already in this process's sys.modules.
    """

    def test_mapping_pulls_in_neither_maya_nor_qt(self):
        script = (
            "import sys\n"
            "from maya_curveview import mapping\n"
            # 'maya.' with the dot: our own package is called
            # maya_curveview and is not what this is looking for.
            "leaked = [m for m in sys.modules\n"
            "          if m.startswith('maya.') or m.startswith('PySide6')\n"
            "          or m.startswith('shiboken6')]\n"
            "print(';'.join(sorted(leaked)))\n")
        plugin = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "SkeldarAnim")
        result = subprocess.run([sys.executable, "-c", script],
                                cwd=plugin, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "",
                         "importing mapping leaked: " + result.stdout.strip())


class TestFrame(unittest.TestCase):

    def test_value_span_over_several_curves(self):
        span = mapping.value_span([[(0, 1.0), (5, 3.0)], [(0, -2.0)]])
        self.assertEqual(span, (-2.0, 3.0))

    def test_value_span_of_nothing_is_none(self):
        self.assertIsNone(mapping.value_span([]))
        self.assertIsNone(mapping.value_span([[]]))

    def test_autoframe_x_is_the_time_range_exactly(self):
        frame = mapping.autoframe((0.0, 100.0), (0.0, 10.0))
        self.assertEqual((frame.t0, frame.t1), (0.0, 100.0))

    def test_autoframe_pads_the_value_range(self):
        frame = mapping.autoframe((0.0, 10.0), (0.0, 10.0), margin=0.1)
        self.assertAlmostEqual(frame.v0, -1.0)
        self.assertAlmostEqual(frame.v1, 11.0)

    def test_a_flat_curve_still_gets_a_window(self):
        frame = mapping.autoframe((0.0, 10.0), (5.0, 5.0), floor=2.0)
        self.assertLess(frame.v0, 5.0)
        self.assertGreater(frame.v1, 5.0)

    def test_no_span_still_gives_a_usable_frame(self):
        frame = mapping.autoframe((0.0, 10.0), None)
        self.assertLess(frame.v0, frame.v1)

    def test_a_zero_length_time_range_still_gives_a_usable_frame(self):
        frame = mapping.autoframe((7.0, 7.0), (0.0, 1.0))
        self.assertLess(frame.t0, frame.t1)


class TestMapping(unittest.TestCase):

    def setUp(self):
        self.frame = mapping.Frame(0.0, 100.0, 0.0, 10.0)
        self.rect = mapping.Rect(1000, 500)

    def test_time_maps_left_to_right(self):
        x, _ = mapping.to_pixels(self.frame, self.rect, 50.0, 0.0)
        self.assertAlmostEqual(x, 500.0)

    def test_value_maps_bottom_up_in_qt_coordinates(self):
        _, y_low = mapping.to_pixels(self.frame, self.rect, 0.0, 0.0)
        _, y_high = mapping.to_pixels(self.frame, self.rect, 0.0, 10.0)
        self.assertAlmostEqual(y_low, 500.0)
        self.assertAlmostEqual(y_high, 0.0)

    def test_round_trip(self):
        t, v = mapping.to_curve(self.frame, self.rect,
                                *mapping.to_pixels(self.frame, self.rect,
                                                   33.0, 7.5))
        self.assertAlmostEqual(t, 33.0)
        self.assertAlmostEqual(v, 7.5)

    def test_flip_y_is_measured_from_the_bottom(self):
        self.assertAlmostEqual(mapping.flip_y(self.rect, 0.0), 500.0)
        self.assertAlmostEqual(mapping.flip_y(self.rect, 500.0), 0.0)

    def test_flip_y_is_its_own_inverse(self):
        self.assertAlmostEqual(
            mapping.flip_y(self.rect, mapping.flip_y(self.rect, 137.0)),
            137.0)

    def test_a_degenerate_rect_does_not_divide_by_zero(self):
        rect = mapping.Rect(0, 0)
        x, y = mapping.to_pixels(self.frame, rect, 50.0, 5.0)
        self.assertEqual((x, y), (0.0, 0.0))
        self.assertEqual(mapping.to_curve(self.frame, rect, 10.0, 10.0),
                         (self.frame.t0, self.frame.v0))

    def test_snap_goes_to_whole_frames(self):
        self.assertEqual(mapping.snap(3.4), 3.0)
        self.assertEqual(mapping.snap(3.6), 4.0)
        self.assertEqual(mapping.snap(-3.6), -4.0)
        self.assertEqual(mapping.snap(-3.4), -3.0)

    def test_snap_rounds_a_half_away_from_zero(self):
        self.assertEqual(mapping.snap(2.5), 3.0)
        self.assertEqual(mapping.snap(-2.5), -3.0)


class TestPicking(unittest.TestCase):

    def setUp(self):
        self.frame = mapping.Frame(0.0, 100.0, 0.0, 10.0)
        self.rect = mapping.Rect(1000, 500)
        self.keys = [(0.0, 0.0), (50.0, 5.0), (100.0, 10.0)]

    def test_picks_the_key_under_the_point(self):
        x, y = mapping.to_pixels(self.frame, self.rect, 50.0, 5.0)
        self.assertEqual(mapping.pick_key(self.frame, self.rect, self.keys,
                                          x + 2, y - 2), 1)

    def test_nothing_outside_the_radius(self):
        x, y = mapping.to_pixels(self.frame, self.rect, 50.0, 5.0)
        self.assertIsNone(mapping.pick_key(self.frame, self.rect, self.keys,
                                           x + 40, y, radius=8.0))

    def test_the_nearest_wins(self):
        keys = [(50.0, 5.0), (51.0, 5.0)]
        x, y = mapping.to_pixels(self.frame, self.rect, 51.0, 5.0)
        self.assertEqual(mapping.pick_key(self.frame, self.rect, keys, x, y,
                                          radius=40.0), 1)

    def test_no_keys_picks_nothing(self):
        self.assertIsNone(mapping.pick_key(self.frame, self.rect, [], 5, 5))

    def test_box_catches_what_is_inside_it(self):
        x0, y0 = mapping.to_pixels(self.frame, self.rect, 40.0, 4.0)
        x1, y1 = mapping.to_pixels(self.frame, self.rect, 60.0, 6.0)
        self.assertEqual(mapping.keys_in_box(self.frame, self.rect, self.keys,
                                             x0, y0, x1, y1), [1])

    def test_box_normalises_its_corners(self):
        x0, y0 = mapping.to_pixels(self.frame, self.rect, 60.0, 6.0)
        x1, y1 = mapping.to_pixels(self.frame, self.rect, 40.0, 4.0)
        self.assertEqual(mapping.keys_in_box(self.frame, self.rect, self.keys,
                                             x0, y0, x1, y1), [1])

    def test_box_over_everything_takes_everything(self):
        self.assertEqual(
            mapping.keys_in_box(self.frame, self.rect, self.keys,
                                -10, -10, 1010, 510), [0, 1, 2])

    def test_a_click_is_not_a_marquee(self):
        self.assertFalse(mapping.is_marquee(10.0, 10.0, 11.0, 12.0))
        self.assertTrue(mapping.is_marquee(10.0, 10.0, 60.0, 12.0))

    def test_a_marquee_counts_in_either_direction(self):
        self.assertTrue(mapping.is_marquee(60.0, 60.0, 10.0, 10.0))


class TestTangents(unittest.TestCase):

    def setUp(self):
        self.frame = mapping.Frame(0.0, 100.0, 0.0, 10.0)
        self.rect = mapping.Rect(1000, 500)

    def test_a_flat_out_tangent_points_right(self):
        _, out = mapping.tangent_points(self.frame, self.rect, (50.0, 5.0),
                                        0.0, 0.0, length=40.0)
        x, y = mapping.to_pixels(self.frame, self.rect, 50.0, 5.0)
        self.assertAlmostEqual(out[0], x + 40.0)
        self.assertAlmostEqual(out[1], y)

    def test_a_flat_in_tangent_points_left(self):
        into, _ = mapping.tangent_points(self.frame, self.rect, (50.0, 5.0),
                                         0.0, 0.0, length=40.0)
        x, y = mapping.to_pixels(self.frame, self.rect, 50.0, 5.0)
        self.assertAlmostEqual(into[0], x - 40.0)
        self.assertAlmostEqual(into[1], y)

    def test_a_rising_tangent_goes_up_in_pixels(self):
        _, out = mapping.tangent_points(self.frame, self.rect, (50.0, 5.0),
                                        0.0, 45.0, length=40.0)
        _, y = mapping.to_pixels(self.frame, self.rect, 50.0, 5.0)
        self.assertLess(out[1], y)

    def test_the_handle_length_is_constant_in_pixels(self):
        for frame in (mapping.Frame(0.0, 100.0, 0.0, 10.0),
                      mapping.Frame(0.0, 4.0, -900.0, 900.0)):
            _, out = mapping.tangent_points(frame, self.rect, (2.0, 0.0),
                                            0.0, 30.0, length=40.0)
            x, y = mapping.to_pixels(frame, self.rect, 2.0, 0.0)
            reach = ((out[0] - x) ** 2 + (out[1] - y) ** 2) ** 0.5
            self.assertAlmostEqual(reach, 40.0, places=6)

    def test_pick_tangent_finds_a_handle_of_a_selected_key(self):
        keys = [(50.0, 5.0)]
        angles = {0: (0.0, 0.0)}
        _, out = mapping.tangent_points(self.frame, self.rect, keys[0],
                                        0.0, 0.0, length=48.0)
        found = mapping.pick_tangent(self.frame, self.rect, keys, angles, {0},
                                     out[0] + 2, out[1])
        self.assertEqual(found, (0, "out"))

    def test_pick_tangent_ignores_an_unselected_key(self):
        keys = [(50.0, 5.0)]
        angles = {0: (0.0, 0.0)}
        _, out = mapping.tangent_points(self.frame, self.rect, keys[0],
                                        0.0, 0.0, length=48.0)
        self.assertIsNone(
            mapping.pick_tangent(self.frame, self.rect, keys, angles, set(),
                                 out[0], out[1]))

    def test_angle_from_a_pixel_offset_is_the_inverse_of_the_drawing(self):
        key = (50.0, 5.0)
        _, out = mapping.tangent_points(self.frame, self.rect, key,
                                        0.0, 30.0, length=48.0)
        angle = mapping.tangent_angle(self.frame, self.rect, key,
                                      out[0], out[1], "out")
        self.assertAlmostEqual(angle, 30.0, places=6)


class TestNormalise(unittest.TestCase):

    def test_each_curve_gets_its_own_window(self):
        frames = mapping.normalise((0.0, 100.0),
                                   [[(0, 0.0), (10, 100.0)],
                                    [(0, -1.0), (10, 1.0)]])
        self.assertEqual(len(frames), 2)
        self.assertNotAlmostEqual(frames[0].v1, frames[1].v1)

    def test_both_curves_then_fill_the_same_band(self):
        rect = mapping.Rect(100, 200)
        series = [[(0, 0.0), (10, 100.0)], [(0, -1.0), (10, 1.0)]]
        frames = mapping.normalise((0.0, 10.0), series)
        tops = [mapping.to_pixels(frame, rect, 10.0, points[-1][1])[1]
                for frame, points in zip(frames, series)]
        self.assertAlmostEqual(tops[0], tops[1], places=6)

    def test_a_flat_curve_normalises_to_the_middle(self):
        rect = mapping.Rect(100, 200)
        frames = mapping.normalise((0.0, 10.0), [[(0, 5.0), (10, 5.0)]])
        _, y = mapping.to_pixels(frames[0], rect, 5.0, 5.0)
        self.assertAlmostEqual(y, 100.0, places=6)


class TestPolicy(unittest.TestCase):

    def test_modifier_maps_onto_maya_selection_behaviour(self):
        self.assertEqual(mapping.adjustment("none"), "replace")
        self.assertEqual(mapping.adjustment("shift"), "toggle")
        self.assertEqual(mapping.adjustment("ctrl"), "remove")
        self.assertEqual(mapping.adjustment("ctrlShift"), "add")

    def test_unknown_modifier_replaces(self):
        self.assertEqual(mapping.adjustment("hyper"), "replace")
        self.assertEqual(mapping.adjustment(None), "replace")

    def test_axis_colours(self):
        self.assertEqual(mapping.axis_colour("translateX"),
                         mapping.AXIS_COLOURS["x"])
        self.assertEqual(mapping.axis_colour("rotateY"),
                         mapping.AXIS_COLOURS["y"])
        self.assertEqual(mapping.axis_colour("node.scaleZ"),
                         mapping.AXIS_COLOURS["z"])

    def test_a_channel_that_is_not_an_axis_is_neutral(self):
        self.assertEqual(mapping.axis_colour("visibility"),
                         mapping.AXIS_COLOURS["other"])
        self.assertEqual(mapping.axis_colour("autoTwist"),
                         mapping.AXIS_COLOURS["other"])

    def test_the_axis_is_read_from_the_family_not_the_last_letter(self):
        # `blendParent1` ends in no axis letter and `myCustomZ` is not a
        # transform channel: neither may borrow an axis colour.
        self.assertEqual(mapping.axis_colour("blendParent1"),
                         mapping.AXIS_COLOURS["other"])
        self.assertEqual(mapping.axis_colour("myCustomZ"),
                         mapping.AXIS_COLOURS["other"])

    def test_throttle_lets_the_first_through(self):
        self.assertTrue(mapping.should_evaluate(0.0, None, 0.05))

    def test_throttle_holds_inside_the_interval(self):
        self.assertFalse(mapping.should_evaluate(1.01, 1.0, 0.05))
        self.assertTrue(mapping.should_evaluate(1.06, 1.0, 0.05))

    def test_grid_step_is_a_friendly_number(self):
        self.assertEqual(mapping.grid_step(24, target=12), 2.0)
        self.assertEqual(mapping.grid_step(100, target=12), 10.0)
        self.assertEqual(mapping.grid_step(1000, target=12), 100.0)

    def test_grid_step_never_goes_below_a_frame(self):
        self.assertEqual(mapping.grid_step(6, target=12), 1.0)
        self.assertEqual(mapping.grid_step(0), 1.0)

    def test_grid_step_gives_roughly_the_asked_for_count(self):
        for span in (7, 13, 48, 101, 250, 3000):
            step = mapping.grid_step(span, target=12)
            self.assertLessEqual(span / step, 13.0, span)

    def test_sample_count_never_exceeds_the_pixels(self):
        self.assertEqual(mapping.sample_count(mapping.Rect(300, 100), step=3),
                         100)
        self.assertGreaterEqual(mapping.sample_count(mapping.Rect(2, 2)), 2)


if __name__ == "__main__":
    unittest.main()
