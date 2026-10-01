"""Several animations in a line (2026-10-01): where each clip's rig stands.

Pure arithmetic: a clip's sideways reach, the gaps, the slots. The scene half
is lineimport's and verify_uebridge_many.py's.

Spec: docs/superpowers/specs/2026-10-01-uebridge-many-animations-design.md
"""
import os
import subprocess
import sys
import unittest

from maya_uebridge import lineup

X = (1.0, 0.0, 0.0)


class SideExtent(unittest.TestCase):

    def test_a_still_clip_reaches_nowhere(self):
        self.assertEqual(lineup.side_extent([(5.0, 0.0, 7.0)] * 4, X), (0.0, 0.0))

    def test_relative_to_its_first_frame(self):
        track = [(100.0, 0.0, 0.0), (110.0, 0.0, 0.0), (130.0, 0.0, 9.0)]
        self.assertEqual(lineup.side_extent(track, X), (0.0, 30.0))

    def test_left_and_right(self):
        track = [(0.0, 0.0, 0.0), (-20.0, 5.0, 0.0), (12.0, 0.0, 0.0)]
        self.assertEqual(lineup.side_extent(track, X), (-20.0, 12.0))

    def test_along_any_axis(self):
        track = [(0.0, 0.0, 0.0), (0.0, 0.0, 50.0)]
        self.assertEqual(lineup.side_extent(track, (0.0, 0.0, -1.0)), (-50.0, 0.0))

    def test_no_track(self):
        self.assertEqual(lineup.side_extent([], X), (0.0, 0.0))


class Offsets(unittest.TestCase):

    def test_three_still_clips_stand_a_step_apart_about_the_centre(self):
        self.assertEqual(lineup.offsets([(0, 0)] * 3), [-250.0, 0.0, 250.0])

    def test_two_are_symmetric(self):
        self.assertEqual(lineup.offsets([(0, 0)] * 2, step=100.0), [-50.0, 50.0])

    def test_a_wanderer_widens_both_its_gaps(self):
        """The gap grows by how far each of the two neighbours wanders toward
        the other: their root paths stay a whole step apart."""
        out = lineup.offsets([(0.0, 0.0), (-20.0, 30.0), (0.0, 0.0)])
        self.assertAlmostEqual(out[1] - out[0], 250.0 + 20.0)
        self.assertAlmostEqual(out[2] - out[1], 250.0 + 30.0)
        self.assertAlmostEqual(out[0] + out[2], 0.0)

    def test_the_paths_keep_a_step_between_them(self):
        extents = [(-5.0, 40.0), (-60.0, 10.0), (0.0, 0.0), (-3.0, 3.0)]
        out = lineup.offsets(extents, step=250.0)
        for i in range(len(out) - 1):
            right_edge = out[i] + extents[i][1]
            left_edge = out[i + 1] + extents[i + 1][0]
            self.assertAlmostEqual(left_edge - right_edge, 250.0)

    def test_one_and_none(self):
        self.assertEqual(lineup.offsets([(-4.0, 9.0)]), [0.0])
        self.assertEqual(lineup.offsets([]), [])


class FloorAxis(unittest.TestCase):

    def test_the_vertical_part_goes(self):
        self.assertEqual(lineup.floor_axis((0.0, 5.0, 2.0)), (0.0, 0.0, 1.0))

    def test_normalised(self):
        axis = lineup.floor_axis((3.0, 0.0, 4.0))
        self.assertAlmostEqual(axis[0], 0.6)
        self.assertAlmostEqual(axis[2], 0.8)
        self.assertEqual(axis[1], 0.0)

    def test_straight_up_falls_back_to_world_x(self):
        self.assertEqual(lineup.floor_axis((0.0, 1.0, 0.0)), (1.0, 0.0, 0.0))
        self.assertEqual(lineup.floor_axis(None), (1.0, 0.0, 0.0))


class Slots(unittest.TestCase):

    def test_along_the_axis_about_the_centre(self):
        got = lineup.slots((100.0, 3.0, -50.0), (0.0, 0.0, 1.0), [-250.0, 0.0, 250.0])
        self.assertEqual(got, [(100.0, 3.0, -300.0), (100.0, 3.0, -50.0), (100.0, 3.0, 200.0)])


class Widened(unittest.TestCase):

    def test_only_the_ones_that_wander(self):
        names = ["A_Idle", "A_Strafe", "A_Sway"]
        extents = [(0.0, 0.0), (-2.0, 40.0), (-0.5, 0.9)]
        self.assertEqual(lineup.widened(names, extents), ["A_Strafe"])


class SampleFrames(unittest.TestCase):

    def test_every_frame_of_a_short_clip(self):
        self.assertEqual(lineup.sample_frames(0, 10), [float(f) for f in range(11)])

    def test_a_long_clip_evenly(self):
        frames = lineup.sample_frames(0, 1000, 240)
        self.assertEqual(len(frames), 240)
        self.assertEqual((frames[0], frames[-1]), (0.0, 1000.0))

    def test_no_range(self):
        self.assertEqual(lineup.sample_frames(5, None), [5.0])
        self.assertEqual(lineup.sample_frames(5, 5), [5.0])


class Boundary(unittest.TestCase):

    def test_stdlib_only(self):
        plugin = os.path.dirname(os.path.dirname(os.path.abspath(lineup.__file__)))
        code = ("import sys; import maya_uebridge.lineup; "
                "bad = [m for m in sys.modules if m.split('.')[0] in "
                "('maya', 'PySide6', 'shiboken6')]; print(bad)")
        out = subprocess.run([sys.executable, "-c", code], cwd=plugin,
                             capture_output=True, text=True)
        self.assertEqual(out.stdout.strip(), "[]", out.stderr)


if __name__ == "__main__":
    unittest.main()
