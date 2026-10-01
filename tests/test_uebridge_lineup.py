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


class GridShape(unittest.TestCase):
    """2026-10-01, «всегда ... в квадратной формации»: as square as it gets."""

    def test_columns_then_rows(self):
        self.assertEqual([lineup.grid_shape(n) for n in range(1, 11)],
                         [(1, 1), (2, 1), (2, 2), (2, 2), (3, 2), (3, 2), (3, 3), (3, 3),
                          (3, 3), (4, 3)])
        self.assertEqual(lineup.grid_shape(0), (0, 0))


class Band(unittest.TestCase):

    def test_the_union_of_the_reaches(self):
        self.assertEqual(lineup.band([(-3.0, 1.0), (0.0, 9.0), (-1.0, 0.0)]), (-3.0, 9.0))
        self.assertEqual(lineup.band([]), (0.0, 0.0))


class Square(unittest.TestCase):

    def still(self, count):
        return [(0.0, 0.0)] * count

    def test_four_still_clips_stand_on_a_square_about_the_centre(self):
        got = lineup.square_offsets(self.still(4), self.still(4))
        self.assertEqual(got, [(-125.0, -125.0), (125.0, -125.0),
                               (-125.0, 125.0), (125.0, 125.0)])

    def test_row_zero_is_in_front_and_rows_go_left_to_right(self):
        slots = lineup.square_slots((0.0, 0.0, 0.0), self.still(3), self.still(3))
        self.assertEqual(slots, [(-125.0, 0.0, 125.0), (125.0, 0.0, 125.0),
                                 (-125.0, 0.0, -125.0)])

    def test_about_a_point(self):
        slots = lineup.square_slots((100.0, 2.0, -40.0), self.still(2), self.still(2))
        self.assertEqual(slots, [(-25.0, 2.0, -40.0), (225.0, 2.0, -40.0)])

    def test_one_clip_stands_on_the_centre(self):
        self.assertEqual(lineup.square_slots((7.0, 0.0, 8.0), [(-5.0, 9.0)], [(0.0, 3.0)]),
                         [(7.0, 0.0, 8.0)])

    def test_a_wanderer_widens_its_column_and_its_row(self):
        """Clip 1 (row 0, column 1) wanders 30 to the left along X and 200 back
        along the row axis: its column's band and its row's band grow, and
        every other clip moves with its band - the grid stays a grid."""
        x = [(0.0, 0.0), (-30.0, 0.0), (0.0, 0.0), (0.0, 0.0)]
        z = [(0.0, 0.0), (0.0, 200.0), (0.0, 0.0), (0.0, 0.0)]
        got = lineup.square_offsets(x, z)
        self.assertAlmostEqual(got[1][0] - got[0][0], 250.0 + 30.0)
        self.assertAlmostEqual(got[3][0] - got[2][0], 250.0 + 30.0)
        self.assertAlmostEqual(got[2][1] - got[0][1], 250.0 + 200.0)
        self.assertAlmostEqual(got[0][0], got[2][0])            # columns aligned
        self.assertAlmostEqual(got[0][1], got[1][1])            # rows aligned

    def test_no_two_paths_come_within_a_step(self):
        x = [(-5.0, 40.0), (-60.0, 10.0), (0.0, 0.0), (-3.0, 3.0), (0.0, 80.0)]
        z = [(0.0, 120.0), (-20.0, 0.0), (0.0, 249.0), (-7.0, 7.0), (0.0, 0.0)]
        offs = lineup.square_offsets(x, z, step=250.0)
        cols, _rows = lineup.grid_shape(5)
        for i in range(5):
            for j in range(i + 1, 5):
                if i % cols != j % cols:
                    a, b = (i, j) if offs[i][0] < offs[j][0] else (j, i)
                    gap = (offs[b][0] + x[b][0]) - (offs[a][0] + x[a][1])
                else:
                    a, b = (i, j) if offs[i][1] < offs[j][1] else (j, i)
                    gap = (offs[b][1] + z[b][0]) - (offs[a][1] + z[a][1])
                self.assertGreaterEqual(gap, 250.0 - 1e-9, (i, j))

    def test_the_row_axis_is_minus_z(self):
        self.assertEqual(lineup.ROWS, (0.0, 0.0, -1.0))
        self.assertEqual(lineup.COLUMNS, (1.0, 0.0, 0.0))

    def test_none(self):
        self.assertEqual(lineup.square_offsets([], []), [])


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
