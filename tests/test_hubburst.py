"""maya_hubburst - a popup bursting out of a point (spec 2026-10-17-popup-burst-design.md)."""

import os
import subprocess
import sys
import unittest

import tests  # noqa: F401  (puts SkeldarAnim/ on sys.path)

import maya_hubburst as burst
from maya_timebar import look as tlook

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
        self.assertAlmostEqual(d[0], tlook.burst_delay(130, 2) / burst.OPEN_SPEED, delta=0.5)

    def test_distances_count_in_logical_pixels(self):
        big = burst.plan_open((30, 15), (450, 600), [(6, 540, 438, 36)], scale=1.5)
        small = burst.plan_open((20, 10), SIZE, [(4, 360, 292, 24)], scale=1.0)
        self.assertAlmostEqual(big.delays[0], small.delays[0])

    def test_a_row_overshoots_a_little_then_settles(self):
        d = self.plan.delays[0]
        scales = [burst.at(self.plan, d + ms).parts[0][1] for ms in range(0, 289, 4)]
        self.assertGreater(max(scales), 1.0)
        self.assertLess(max(scales), 1.1)
        self.assertAlmostEqual(scales[-1], 1.0)

    def test_the_total_covers_the_shape_the_light_and_the_last_row(self):
        self.assertGreaterEqual(self.plan.total, burst.SHAPE_MS)
        self.assertGreaterEqual(self.plan.total, burst.REVEAL_MS)
        self.assertGreaterEqual(self.plan.total, max(self.plan.delays) + burst.PART_MS)

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
        self.assertEqual(d[3], min(d))
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

    def test_a_tall_leaf_is_cut_into_bands(self):
        """2026-10-19: a list's viewport has no child widgets, and whole it was one
        420 px row: it waited its turn as an empty rectangle of the card's face
        («пустой прямоугольник во время анимации открытия»). Now bands no taller
        than row_max, together exactly the leaf, each popping by its own distance."""
        out = self.walk(((0, 10, 100, 300), []))
        self.assertEqual(len(out), 5)
        self.assertTrue(all(r[3] <= 64 for r in out))
        self.assertEqual(out[0][1], 10)
        self.assertEqual(sum(r[3] for r in out), 300)
        for a, b in zip(out, out[1:]):
            self.assertEqual(a[1] + a[3], b[1])
        self.assertTrue(all((r[0], r[2]) == (0, 100) for r in out))

    def test_a_leaf_at_the_depth_cap_is_cut_into_bands_too(self):
        deep = ((0, 0, 100, 300), [])
        for _ in range(12):
            deep = ((0, 0, 100, 300), [deep])
        self.assertEqual(len(self.walk(deep, depth=3)), 5)

    def test_rows_outside_the_clip_go_and_the_rest_are_cut(self):
        tree = ((0, 0, 100, 300), [((0, 0, 100, 30), []), ((0, 280, 100, 30), [])])
        self.assertEqual(self.walk(tree, clip=(0, 0, 100, 290)),
                         [(0, 0, 100, 30), (0, 280, 100, 10)])

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


class TimeBarNumbers(unittest.TestCase):
    """2026-10-18: the burst is the Time Bar's (spec 2026-10-18-floating-windows-design.md)."""

    SIZE = (300.0, 400.0)
    PARTS = [(10, 10, 280, 30), (10, 300, 280, 30)]


    def test_the_fold_delay_is_the_time_bars_own(self):
        for scale in (1.0, 1.5):
            plan = burst.plan_close((20, 20), self.SIZE, self.PARTS, scale=scale)
            for part, delay in zip(plan.parts, plan.delays):
                x, y, w, h = part
                dx, dy = x + w / 2.0 - plan.origin[0], y + h / 2.0 - plan.origin[1]
                self.assertAlmostEqual(
                    delay, tlook.fold_delay(abs(dx) + 1.5 * abs(dy), scale) / burst.CLOSE_SPEED)
    def test_the_shape_grows_over_the_time_bars_unroll(self):
        plan = burst.plan_open((20, 20), self.SIZE, self.PARTS)
        self.assertEqual(burst.at(plan, burst.SHAPE_MS).shape, (0.0, 0.0, 300.0, 400.0))
        mid = burst.at(plan, burst.SHAPE_MS / 2.0).shape
        self.assertLess(mid[2], 300.0)

    def test_a_part_pops_from_the_time_bars_start_scale(self):
        plan = burst.plan_open((20, 20), self.SIZE, self.PARTS)
        d = plan.delays[0]
        op, sc = burst.at(plan, d + 0.5).parts[0]
        self.assertAlmostEqual(sc, tlook.START_SCALE, delta=0.02)
        self.assertEqual(burst.at(plan, d + burst.PART_MS).parts[0], (1.0, 1.0))

    def test_the_nearest_part_starts_by_the_time_bars_delay(self):
        plan = burst.plan_open((20, 20), self.SIZE, self.PARTS)
        self.assertLess(plan.delays[0], plan.delays[1])
        self.assertAlmostEqual(plan.delays[0], tlook.burst_delay(130, 5) / burst.OPEN_SPEED, delta=0.5)

    def test_the_close_starts_its_shape_after_the_last_fold(self):
        plan = burst.plan_close((20, 20), self.SIZE, self.PARTS)
        last = max(plan.delays) + tlook.FOLD_MS / 2.0
        self.assertAlmostEqual(plan.m0, last + tlook.CLOSE_AFTER_MS / 2.0, delta=0.5)
        self.assertAlmostEqual(plan.total, plan.m0 + tlook.CLOSE_MS / 2.0, delta=0.5)

    def test_a_close_runs_twice_the_time_bars_speed(self):
        plan = burst.plan_close((20, 20), self.SIZE, self.PARTS)
        far = max(range(len(self.PARTS)), key=lambda i: plan.delays[i])
        cx, cy = burst._centre(self.PARTS[far])
        o = plan.origin
        slow = tlook.fold_delay(abs(cx - o[0]) + 1.5 * abs(cy - o[1]), 1.0)
        self.assertAlmostEqual(plan.delays[far], slow / 2.0, delta=0.01)
        slow_total = slow + tlook.FOLD_MS + tlook.CLOSE_AFTER_MS + tlook.CLOSE_MS
        self.assertAlmostEqual(plan.total, slow_total / 2.0, delta=0.5)

    def test_a_folded_part_ends_at_the_start_scale_and_gone(self):
        plan = burst.plan_close((20, 20), self.SIZE, self.PARTS)
        d = plan.delays[0]
        self.assertEqual(burst.at(plan, d + tlook.FOLD_MS / 2.0).parts[0], (0.0, tlook.START_SCALE))


class Light(unittest.TestCase):

    SIZE = (300.0, 400.0)
    PARTS = [(10, 10, 280, 30)]

    def test_the_edges_inside_the_card_carry_light_while_it_grows(self):
        plan = burst.plan_open((150, 200), self.SIZE, self.PARTS)
        light = burst.light(plan, 40.0)
        axes = sorted(e[0] for e in light.edges)
        self.assertEqual(axes, ["x", "x", "y", "y"])
        self.assertTrue(all(0.0 < e[2] <= 1.0 for e in light.edges))

    def test_the_edge_light_fades_as_the_edges_slow(self):
        plan = burst.plan_open((150, 200), self.SIZE, self.PARTS)
        early = max(e[2] for e in burst.light(plan, 20.0).edges)
        later = max(e[2] for e in burst.light(plan, 100.0).edges)
        self.assertGreater(early, later)

    def test_an_edge_on_the_card_border_carries_none(self):
        plan = burst.plan_open((150, 200), self.SIZE, self.PARTS)
        self.assertEqual(burst.light(plan, burst.SHAPE_MS).edges, [])

    def test_the_top_lights_once_the_shape_reaches_it_and_fades(self):
        plan = burst.plan_open((150, 390), self.SIZE, self.PARTS)
        self.assertEqual(burst.light(plan, 1.0).top, 0.0)
        reached = burst.light(plan, burst.SHAPE_MS).top
        self.assertGreater(reached, 0.0)
        self.assertEqual(burst.light(plan, burst.REVEAL_MS).top, 0.0)

    def test_a_close_carries_no_light(self):
        plan = burst.plan_close((150, 200), self.SIZE, self.PARTS)
        light = burst.light(plan, 50.0)
        self.assertEqual((light.edges, light.top), ([], 0.0))

    def test_the_light_lengths_are_the_time_bars(self):
        self.assertEqual((burst.EDGE_GLOW, burst.EDGE_CORE, burst.TOP_GLOW),
                         (tlook.EDGE_GLOW, tlook.EDGE_CORE, tlook.TOP_GLOW))


class Spring(unittest.TestCase):
    """The spring (2026-10-22, spec 2026-10-22-window-look-b-spring-design.md)."""

    def test_it_is_the_motion_in_use(self):
        self.assertEqual(burst.MOTION, "spring")
        plan = burst.plan(True, (20, 10), SIZE, lambda: self.fail("rows walked"))
        self.assertEqual(plan.kind, "spring")

    def test_the_burst_still_walks_its_rows(self):
        walked = []
        plan = burst.plan(True, (20, 10), SIZE, lambda: walked.append(1) or PARTS,
                          motion="burst")
        self.assertEqual(plan.kind, "burst")
        self.assertEqual(walked, [1])

    def test_the_spring_overshoots_once_a_little_and_settles(self):
        values = [burst.spring(ms) for ms in range(0, 1000, 2)]
        self.assertEqual(values[0], 0.0)
        peak = max(values)
        self.assertGreater(peak, 1.0)
        self.assertLess(peak, 1.05)          # 3.8 % of the way: the scale 1.2 % over
        self.assertLess(abs(burst.spring(burst.SPRING_MS) - 1.0), 0.004)

    def test_opening_grows_from_spring_from_about_the_point_and_fades_in(self):
        plan = burst.plan_spring(True, (20, 10), SIZE)
        o = burst.clamp_origin((20, 10), SIZE, burst.ORIGIN_PAD)
        start = burst.at(plan, 0.0)
        self.assertAlmostEqual(burst.scale_of(plan, start), burst.SPRING_FROM)
        self.assertEqual(start.face, 0.0)
        # the point stays where it is
        x0, y0, x1, y1 = start.shape
        self.assertAlmostEqual(o[0] - x0, (o[0]) * burst.SPRING_FROM)
        self.assertAlmostEqual(y1 - o[1], (SIZE[1] - o[1]) * burst.SPRING_FROM)
        mid = burst.at(plan, burst.SPRING_FADE_MS)
        self.assertEqual(mid.face, 1.0)
        end = burst.at(plan, plan.total)
        self.assertEqual(end.shape, (0.0, 0.0, SIZE[0], SIZE[1]))
        self.assertEqual(plan.total, burst.SPRING_MS)
        self.assertEqual(end.parts, [])

    def test_closing_shrinks_toward_the_point_and_fades_out(self):
        plan = burst.plan_spring(False, (280, 12), SIZE)
        self.assertEqual(burst.at(plan, 0.0).face, 1.0)
        self.assertAlmostEqual(burst.scale_of(plan, burst.at(plan, 0.0)), 1.0)
        end = burst.at(plan, plan.total)
        self.assertEqual(end.face, 0.0)
        self.assertAlmostEqual(burst.scale_of(plan, end), burst.SHUT_TO)
        self.assertEqual(plan.total, burst.SHUT_MS)
        scales = [burst.scale_of(plan, burst.at(plan, ms)) for ms in range(0, 141, 10)]
        self.assertEqual(scales, sorted(scales, reverse=True))

    def test_a_spring_carries_no_light(self):
        plan = burst.plan_spring(True, (150, 200), SIZE)
        self.assertEqual(burst.light(plan, 20.0), burst.Light([], 0.0))


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
