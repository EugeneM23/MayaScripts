"""Camera flight's pure half (2026-10-21): a camera's view, the flight between two views, the
substitute's lens."""

import math
import os
import subprocess
import sys
import unittest

import maya_camflight_rules as rules


def turned_y(deg):
    """A world matrix turned `deg` about Y (row vectors), at the origin."""
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return [c, 0, -s, 0, 0, 1, 0, 0, s, 0, c, 0, 0, 0, 0, 1]


def at(matrix, pos):
    return list(matrix[:12]) + [pos[0], pos[1], pos[2], 1]


TOP = [1, 0, 0, 0, 0, 0, -1, 0, 0, 1, 0, 0, 0, 1000.1, 0, 1]     # rotateX -90, y 1000.1


def persp(pos=(0, 100, 400), deg=0.0, coi=400.0, tan=0.32, near=0.1, far=10000.0, aspect=1.6):
    n = near
    frustum = (-tan * aspect * n, tan * aspect * n, -tan * n, tan * n)
    return rules.view_of(at(turned_y(deg), pos), frustum, near, far, coi, False)


def ortho(matrix=TOP, half=9.375, coi=1000.1, aspect=1.6):
    frustum = (-half * aspect, half * aspect, -half, half)
    return rules.view_of(matrix, frustum, 0.1, 10000.0, coi, True)


def close(test, a, b, places=7):
    for x, y in zip(a, b):
        test.assertAlmostEqual(x, y, places=places)


class Quaternions(unittest.TestCase):
    def test_rows_round_trip(self):
        for m in (turned_y(0), turned_y(37), turned_y(-170), TOP):
            close(self, rules.rows_of(rules.quat_of(m)), [m[i] for i in (0, 1, 2, 4, 5, 6, 8, 9, 10)])

    def test_slerp_ends_and_middle(self):
        a, b = rules.quat_of(turned_y(0)), rules.quat_of(turned_y(90))
        close(self, rules.slerp(a, b, 0.0), a)
        close(self, rules.slerp(a, b, 1.0), b)
        close(self, rules.rows_of(rules.slerp(a, b, 0.5)),
              [turned_y(45)[i] for i in (0, 1, 2, 4, 5, 6, 8, 9, 10)])

    def test_slerp_goes_the_short_way(self):
        a, b = rules.quat_of(turned_y(170)), rules.quat_of(turned_y(-170))
        mid = rules.rows_of(rules.slerp(a, b, 0.5))
        close(self, mid, [turned_y(180)[i] for i in (0, 1, 2, 4, 5, 6, 8, 9, 10)])

    def test_a_scaled_matrix_reads_its_rotation(self):
        m = turned_y(30)
        scaled = [v * 3 for v in m[:12]] + m[12:]
        close(self, rules.quat_of(scaled), rules.quat_of(m))


class Views(unittest.TestCase):
    def test_a_perspective_view(self):
        v = persp()
        close(self, v.pivot, (0, 100, 0))         # looks down -Z: 400 ahead
        self.assertAlmostEqual(v.tan, 0.32)
        self.assertAlmostEqual(v.half, 400 * 0.32)
        self.assertAlmostEqual(v.near_rel, 0.1 - 400)
        self.assertAlmostEqual(v.floor, 0.1)
        self.assertEqual((v.ox, v.oy), (0.0, 0.0))

    def test_an_ortho_view_is_flat_with_its_own_frame(self):
        v = ortho()
        close(self, v.pivot, (0, 0, 0))
        self.assertEqual(v.tan, rules.TAN_FLAT)
        self.assertAlmostEqual(v.half, 9.375)
        self.assertIsNone(v.floor)

    def test_a_film_offset_is_kept_in_half_heights(self):
        frustum = (-0.1381, 0.1717, -0.0968, 0.0968)
        v = rules.view_of(turned_y(0), frustum, 0.1, 1000.0, 5.0, False)
        self.assertAlmostEqual(v.ox, (0.1717 - 0.1381) / 0.1936, places=6)
        self.assertAlmostEqual(v.tan, 0.968, places=6)

    def test_a_tiny_centre_of_interest_is_held_off_zero(self):
        v = persp(coi=0.0)
        self.assertGreater(v.half, 0.0)


class Flight(unittest.TestCase):
    def test_both_ends_are_the_cameras_exactly(self):
        a, b = persp(), persp(pos=(300, 50, 0), deg=90, coi=250, tan=0.6, near=0.5, far=5000)
        for view, u in ((a, 0.0), (b, 1.0)):
            shot = rules.shot(rules.blend(a, b, u))
            src = rules.shot(view)
            close(self, shot.matrix, src.matrix, places=6)
            self.assertAlmostEqual(shot.tan, view.tan)
            self.assertAlmostEqual(shot.near, view.floor, places=6)

    def test_a_shot_of_a_perspective_view_is_its_camera(self):
        v = persp(pos=(10, 20, 30), deg=25)
        shot = rules.shot(v)
        close(self, shot.matrix[12:15], (10, 20, 30), places=6)
        self.assertAlmostEqual(shot.near, 0.1)
        self.assertAlmostEqual(shot.far, 10000.0, places=5)

    def test_the_pivot_stays_on_the_axis_mid_flight(self):
        a, b = persp(), persp(pos=(400, 100, 0), deg=90, coi=400)
        for u in (0.2, 0.5, 0.8):
            view = rules.blend(a, b, u)
            shot = rules.shot(view)
            fwd = [-shot.matrix[8], -shot.matrix[9], -shot.matrix[10]]
            d = view.half / view.tan
            close(self, [p + f * d for p, f in zip(shot.matrix[12:15], fwd)], view.pivot, places=5)

    def test_into_an_ortho_view_the_frame_at_the_pivot_is_its_frame(self):
        a, b = persp(), ortho()
        end = rules.blend(a, b, 1.0)
        shot = rules.shot(end)
        d = math.dist(shot.matrix[12:15], end.pivot)
        self.assertAlmostEqual(d * shot.tan, 9.375, places=5)
        # its depth range is the ortho camera's about the pivot
        self.assertAlmostEqual(shot.near - d, 0.1 - 1000.1, places=4)
        self.assertAlmostEqual(shot.far - d, 10000.0 - 1000.1, places=3)

    def test_the_flattening_is_even_in_tan(self):
        a, b = persp(tan=0.4), ortho()
        self.assertAlmostEqual(rules.blend(a, b, 0.5).tan, (0.4 + rules.TAN_FLAT) / 2)

    def test_the_frame_size_moves_in_log_space(self):
        a, b = persp(coi=10, tan=0.5), persp(coi=1000, tan=0.5)
        self.assertAlmostEqual(rules.blend(a, b, 0.5).half, math.sqrt(5 * 500), places=6)

    def test_the_near_clip_never_falls_under_the_perspective_end(self):
        a, b = persp(coi=5, near=0.5), ortho()
        for u in (0.0, 0.1, 0.3, 0.6, 0.9, 1.0):
            shot = rules.shot(rules.blend(a, b, u))
            self.assertGreaterEqual(shot.near, 0.5 - 1e-9)
            self.assertGreater(shot.far, shot.near)

    def test_two_ortho_ends_keep_a_positive_near(self):
        shot = rules.shot(rules.blend(ortho(), ortho(matrix=at(turned_y(0), (0, 0, 1000.1))), 0.5))
        self.assertGreater(shot.near, 0.0)


class Lens(unittest.TestCase):
    def test_the_lens_of_a_tan(self):
        lens = rules.lens(0.32, 0.1, -0.05, 1.6)
        self.assertAlmostEqual(lens["vertical"], 1.0)
        self.assertAlmostEqual(lens["horizontal"], 1.6)
        self.assertAlmostEqual(lens["focal"], 12.7 / 0.32)
        self.assertAlmostEqual(lens["hoffset"], 0.05)
        self.assertAlmostEqual(lens["voffset"], -0.025)

    def test_a_wide_angle_grows_the_aperture_not_under_the_least_focal(self):
        lens = rules.lens(40.0, 0.0, 0.0, 1.0)
        self.assertAlmostEqual(lens["focal"], rules.MIN_FOCAL)
        self.assertAlmostEqual(12.7 * lens["vertical"] / lens["focal"], 40.0)

    def test_a_flat_angle_stays_under_the_greatest_focal(self):
        lens = rules.lens(1e-6, 0.0, 0.0, 1.0)
        self.assertLessEqual(lens["focal"], rules.MAX_FOCAL)
        self.assertAlmostEqual(12.7 * lens["vertical"] / lens["focal"], 1e-6)


class Time(unittest.TestCase):
    def test_ease_in_out(self):
        self.assertEqual(rules.ease(0.0), 0.0)
        self.assertEqual(rules.ease(1.0), 1.0)
        self.assertAlmostEqual(rules.ease(0.5), 0.5)
        self.assertLess(rules.ease(0.1), 0.1)
        self.assertGreater(rules.ease(0.9), 0.9)
        self.assertEqual(rules.ease(-1.0), 0.0)
        self.assertEqual(rules.ease(3.0), 1.0)

    def test_progress(self):
        self.assertEqual(rules.progress(0.0, 0.3), 0.0)
        self.assertAlmostEqual(rules.progress(0.15, 0.3), 0.5)
        self.assertEqual(rules.progress(0.5, 0.3), 1.0)
        self.assertEqual(rules.progress(0.1, 0.0), 1.0)

    def test_the_flight_is_three_tenths(self):
        self.assertAlmostEqual(rules.FLIGHT_S, 0.3)


class Pure(unittest.TestCase):
    def test_stdlib_only(self):
        here = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "SkeldarAnim")
        code = ("import sys; import maya_camflight_rules; "
                "bad = [m for m in sys.modules if m.split('.')[0] in "
                "('maya', 'PySide6', 'shiboken6', 'numpy')]; print(bad)")
        out = subprocess.run([sys.executable, "-c", code], cwd=here, capture_output=True,
                             text=True, timeout=120)
        self.assertEqual(out.stdout.strip(), "[]", out.stderr)


if __name__ == "__main__":
    unittest.main()
