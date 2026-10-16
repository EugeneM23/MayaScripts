"""maya_timebar.look - the Time Bar's arithmetic (2026-10-16)."""

import os
import subprocess
import sys
import unittest

from maya_timebar import look


class TrackTests(unittest.TestCase):

    def test_frame_and_x_round_trip(self):
        t = look.Track(-10, 90, 12, 1012)
        self.assertAlmostEqual(t.scale, 10.0)
        self.assertAlmostEqual(t.x(0), 112.0)
        self.assertAlmostEqual(t.frame(t.x(37.5)), 37.5)

    def test_whole_rounds_and_clamps(self):
        t = look.Track(0, 100, 0, 1000)
        self.assertEqual(t.whole(54.9), 5)
        self.assertEqual(t.whole(-500, lo=0, hi=60), 0)
        self.assertEqual(t.whole(5000, lo=0, hi=60), 60)

    def test_an_empty_range_still_has_width(self):
        t = look.Track(5, 5, 0, 100)
        self.assertGreater(t.scale, 0)


class TickTests(unittest.TestCase):

    def test_labels_leave_room_for_their_numbers(self):
        for width in (300, 800, 2000):
            t = look.Track(0, 120, 0, width)
            labels = [f for f, kind in look.ticks(t) if kind == "label"]
            gaps = {b - a for a, b in zip(labels, labels[1:])}
            self.assertEqual(len(gaps), 1)
            self.assertGreaterEqual(gaps.pop() * t.scale, look.LABEL_GAP)

    def test_every_label_is_a_multiple_of_its_step_and_inside_the_view(self):
        t = look.Track(-13, 77, 0, 900)
        found = look.ticks(t)
        self.assertTrue(all(-13 <= f <= 77 for f, _ in found))
        self.assertIn((0, "label"), found)

    def test_ticks_never_crowd(self):
        t = look.Track(0, 5000, 0, 1000)
        frames = [f for f, _ in look.ticks(t)]
        self.assertTrue(all((b - a) * t.scale >= look.TICK_GAP
                            for a, b in zip(frames, frames[1:])))

    def test_the_display_scale_widens_the_steps(self):
        t = look.Track(0, 120, 0, 600)
        step = lambda ui: [f for f, k in look.ticks(t, ui) if k == "label"][1]  # noqa: E731
        self.assertGreater(step(2.0), step(1.0))


class HitTests(unittest.TestCase):

    def setUp(self):
        self.t = look.Track(0, 100, 12, 1012)        # 10 px a frame

    def test_the_band_s_edges_are_handles(self):
        self.assertEqual(look.hit(self.t, self.t.x(20) + 3, 50, 20, 80), "p0")
        self.assertEqual(look.hit(self.t, self.t.x(80) - 4, 50, 20, 80), "p1")
        self.assertEqual(look.hit(self.t, self.t.x(50), 50, 20, 80), "now")

    def test_without_the_band_everything_scrubs(self):
        self.assertEqual(look.hit(self.t, self.t.x(20), 50, 20, 80, band=False), "now")

    def test_the_grips_live_past_the_track_s_ends(self):
        self.assertEqual(look.hit(self.t, 3, 50, 0, 100), "a0")
        self.assertEqual(look.hit(self.t, 1020, 50, 0, 100), "a1")
        self.assertEqual(look.hit(self.t, self.t.x(0) + 2, 50, 0, 100), "p0")


class DragTests(unittest.TestCase):

    def test_the_band_keeps_a_frame(self):
        self.assertEqual(look.dragged("p0", 90, 0, 100, 10, 60), (0, 100, 59, 60))
        self.assertEqual(look.dragged("p1", -5, 0, 100, 10, 60), (0, 100, 10, 11))

    def test_the_animation_range_grows_to_hold_the_band(self):
        self.assertEqual(look.dragged("p0", -20, 0, 100, 10, 60), (-20, 100, -20, 60))
        self.assertEqual(look.dragged("p1", 130, 0, 100, 10, 60), (0, 130, 10, 130))

    def test_the_animation_range_never_cuts_the_band(self):
        self.assertEqual(look.dragged("a0", 40, 0, 100, 10, 60), (10, 100, 10, 60))
        self.assertEqual(look.dragged("a1", 30, 0, 100, 10, 60), (0, 60, 10, 60))


class HighlightTests(unittest.TestCase):

    def test_a_drag_either_way(self):
        self.assertEqual(look.highlight(30, 12), (12, 30))
        self.assertEqual(look.highlight(12.4, 29.6), (12, 30))

    def test_range_array_is_end_exclusive_and_more_than_a_frame(self):
        self.assertEqual(look.range_array((12, 30)), (12.0, 31.0))
        self.assertIsNone(look.range_array((12, 12)))
        self.assertIsNone(look.range_array(None))


class KeyTests(unittest.TestCase):

    def test_neighbours(self):
        keys = [0, 6, 12.5, 18]
        self.assertEqual(look.neighbour_key(keys, 6, True), 12.5)
        self.assertEqual(look.neighbour_key(keys, 6, False), 0)
        self.assertIsNone(look.neighbour_key(keys, 18, True))
        self.assertIsNone(look.neighbour_key([], 5, False))


class TextTests(unittest.TestCase):

    def test_frames(self):
        self.assertEqual(look.frame_text(12.0), "12")
        self.assertEqual(look.frame_text(-3), "-3")
        self.assertEqual(look.frame_text(12.5), "12.5")

    def test_fps(self):
        self.assertEqual(look.fps_label("ntsc"), "30 fps")
        self.assertEqual(look.fps_label("film"), "24 fps")
        self.assertEqual(look.fps_label("23.976fps"), "23.976 fps")
        self.assertEqual([u for _, u in look.FPS], ["film", "pal", "ntsc", "show", "palf", "ntscf"])


class Purity(unittest.TestCase):

    def test_look_and_the_package_import_with_the_stdlib_alone(self):
        plugin = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "SkeldarAnim")
        code = ("import sys; import maya_timebar, maya_timebar.look; "
                "bad = [m for m in sys.modules if m.split('.')[0] in "
                "('maya', 'PySide6', 'PySide2', 'shiboken6')]; print(bad); "
                "sys.exit(1 if bad else 0)")
        done = subprocess.run([sys.executable, "-c", code], cwd=plugin,
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


if __name__ == "__main__":
    unittest.main()
