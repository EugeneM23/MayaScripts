"""maya_hubburst - a popup bursting out of a point (spec 2026-10-17-popup-burst-design.md)."""

import os
import subprocess
import sys
import unittest

import tests  # noqa: F401  (puts SkeldarAnim/ on sys.path)

import maya_hubburst as burst

SIZE = (300.0, 400.0)
PARTS = [(4.0, 2.0, 292.0, 24.0),      # the title
         (4.0, 30.0, 292.0, 24.0),
         (4.0, 60.0, 292.0, 24.0),
         (4.0, 360.0, 292.0, 24.0)]


def area(state):
    x0, y0, x1, y1 = state.shape
    return (x1 - x0) * (y1 - y0)


class Origin(unittest.TestCase):

    def test_a_point_inside_stays(self):
        self.assertEqual(burst.clamp_origin((50, 60), SIZE, 12), (50, 60))

    def test_a_point_outside_is_pulled_in(self):
        self.assertEqual(burst.clamp_origin((-200, 900), SIZE, 12), (12, 388))


class Open(unittest.TestCase):

    def setUp(self):
        self.plan = burst.plan_open((20, 10), SIZE, PARTS, scale=1.0)

    def test_it_starts_as_a_small_box_about_the_point_and_invisible(self):
        s = burst.at(self.plan, 0)
        x0, y0, x1, y1 = s.shape
        self.assertLessEqual(x1 - x0, 2 * burst.START_HALF[0] + 1e-9)
        self.assertLessEqual(y1 - y0, 2 * burst.START_HALF[1] + 1e-9)
        self.assertEqual(s.face, 0.0)
        self.assertTrue(all(op == 0.0 for op, _ in s.parts))

    def test_it_ends_as_the_whole_card_and_every_row_at_rest(self):
        s = burst.at(self.plan, self.plan.total)
        self.assertEqual(s.shape, (0.0, 0.0, 300.0, 400.0))
        self.assertEqual(s.radius, burst.CARD_RADIUS)
        self.assertEqual(s.face, 1.0)
        self.assertTrue(all(p == (1.0, 1.0) for p in s.parts))

    def test_the_shape_grows_without_shrinking(self):
        areas = [area(burst.at(self.plan, ms)) for ms in range(0, 320, 10)]
        self.assertEqual(areas, sorted(areas))

    def test_nearer_rows_start_first(self):
        d = self.plan.delays
        self.assertLess(d[0], d[2])
        self.assertLess(d[2], d[3])
        self.assertAlmostEqual(d[0], burst.DELAY0 + burst.DELAY_PER * (
            burst._dist((20, 12), (150, 14)) / burst.STEP))

    def test_distances_count_in_logical_pixels(self):
        big = burst.plan_open((30, 15), (450, 600), [(6, 540, 438, 36)], scale=1.5)
        small = burst.plan_open((20, 10), SIZE, [(4, 360, 292, 24)], scale=1.0)
        self.assertAlmostEqual(big.delays[0], small.delays[0])

    def test_a_row_overshoots_a_little_then_settles(self):
        d = self.plan.delays[0]
        scales = [burst.at(self.plan, d + ms).parts[0][1] for ms in range(0, 241, 4)]
        self.assertGreater(max(scales), 1.0)
        self.assertLess(max(scales), 1.05)
        self.assertAlmostEqual(scales[-1], 1.0)

    def test_the_total_covers_the_shape_and_the_last_row(self):
        self.assertGreaterEqual(self.plan.total, burst.SHAPE_MS)
        self.assertAlmostEqual(self.plan.total, max(self.plan.delays) + burst.PART_MS)

    def test_a_pivot_is_the_row_point_nearest_the_origin(self):
        self.assertEqual(self.plan.pivots[0], (16.0, 10.0))
        self.assertEqual(self.plan.pivots[3], (16.0, 0.0))


class Close(unittest.TestCase):

    def setUp(self):
        self.plan = burst.plan_close((280, 12), SIZE, PARTS, scale=1.0)

    def test_it_starts_whole(self):
        s = burst.at(self.plan, 0)
        self.assertEqual(s.shape, (0.0, 0.0, 300.0, 400.0))
        self.assertEqual(s.face, 1.0)
        self.assertTrue(all(p == (1.0, 1.0) for p in s.parts))

    def test_the_farthest_row_folds_first(self):
        d = self.plan.delays
        self.assertEqual(d[3], 0.0)
        self.assertGreater(d[0], d[3])

    def test_it_ends_small_about_the_point_and_gone(self):
        s = burst.at(self.plan, self.plan.total)
        x0, y0, x1, y1 = s.shape
        self.assertLessEqual(x1 - x0, 2 * burst.CLOSE_HALF[0] + 1e-9)
        self.assertEqual(s.face, 0.0)
        self.assertTrue(all(op == 0.0 for op, _ in s.parts))

    def test_the_shape_shrinks_without_growing(self):
        areas = [area(burst.at(self.plan, ms)) for ms in range(0, int(self.plan.total) + 10, 10)]
        self.assertEqual(areas, sorted(areas, reverse=True))


class Rows(unittest.TestCase):
    """A tree of (rect, children) split into rows no taller than row_max."""

    @staticmethod
    def walk(tree, row_max=64, clip=None, depth=8):
        return burst.rows(tree, lambda n: n[1], lambda n: n[0], row_max, clip, depth)

    def test_a_short_widget_is_one_row(self):
        self.assertEqual(self.walk(((0, 0, 100, 40), [((0, 0, 10, 10), [])])),
                         [(0, 0, 100, 40)])

    def test_a_tall_column_is_split_into_its_children(self):
        tree = ((0, 0, 100, 300), [((0, 0, 100, 30), []), ((0, 30, 100, 30), [])])
        self.assertEqual(self.walk(tree), [(0, 0, 100, 30), (0, 30, 100, 30)])

    def test_a_tall_leaf_stays_whole(self):
        self.assertEqual(self.walk(((0, 0, 100, 300), [])), [(0, 0, 100, 300)])

    def test_rows_outside_the_clip_go_and_the_rest_are_cut(self):
        tree = ((0, 0, 100, 300), [((0, 0, 100, 30), []), ((0, 280, 100, 30), [])])
        self.assertEqual(self.walk(tree, clip=(0, 0, 100, 290)),
                         [(0, 0, 100, 30), (0, 280, 100, 10)])

    def test_the_depth_is_capped(self):
        deep = ((0, 0, 100, 300), [])
        for _ in range(12):
            deep = ((0, 0, 100, 300), [deep])
        self.assertEqual(len(self.walk(deep, depth=3)), 1)

    def test_too_many_rows_merge_into_bands(self):
        rects = [(0, i * 10, 100, 10) for i in range(10)]
        out = burst.bands(rects, 4)
        self.assertLessEqual(len(out), 4)
        self.assertEqual(out[0], (0, 0, 100, 30))
        self.assertEqual(burst.bands(rects, 20), rects)


class Blend(unittest.TestCase):

    def test_ends_and_middle(self):
        self.assertEqual(burst.blend("#000000", "#ffffff", 0.0), (0, 0, 0))
        self.assertEqual(burst.blend("#000000", "#ffffff", 1.0), (255, 255, 255))
        self.assertEqual(burst.blend("#000000", "#ffffff", 0.5), (128, 128, 128))


class Pure(unittest.TestCase):

    def test_it_imports_no_maya_and_no_qt(self):
        plugin = os.path.dirname(burst.__file__)
        code = ("import sys; import maya_hubburst; "
                "bad=[m for m in sys.modules if m.startswith(('maya.', 'PySide'))]; "
                "print(bad)")
        out = subprocess.run([sys.executable, "-c", code], cwd=plugin,
                             capture_output=True, text=True, timeout=120)
        self.assertEqual(out.stdout.strip(), "[]", out.stderr)


if __name__ == "__main__":
    unittest.main()
