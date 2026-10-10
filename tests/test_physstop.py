"""The physical stop: the model, the geometry and the cube it was fitted to."""

import importlib.util
import json
import math
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.join(os.path.dirname(HERE), "docs", "superpowers", "plans", "physstop")
SCRIPT = os.path.join(FOLDER, "skeldar_physstop.py")


def load():
    spec = importlib.util.spec_from_file_location("skeldar_physstop_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ps = load()


class PathTests(unittest.TestCase):

    def path(self, amplitude=4.5, swing=4.75, weight=1.0, t_a=0.0, t_b=9.0):
        return ps.Path(t_a, t_b, amplitude, swing, ps.damping(weight))

    def test_starts_at_rest_and_passes_b_at_its_key(self):
        path = self.path()
        self.assertEqual(path.at(0.0), (0.0, 0.0))
        p, _ = path.at(9.0)
        self.assertAlmostEqual(p, 1.0, places=12)

    def test_velocity_is_continuous_at_b(self):
        path = self.path()
        _, before = path.at(9.0 - 1e-7)
        _, after = path.at(9.0 + 1e-7)
        self.assertAlmostEqual(before, after, places=5)
        self.assertGreater(before, 0.0)

    def test_first_overshoot_is_the_amplitude(self):
        path = self.path(amplitude=4.5)
        peak = max(path.at(9.0 + i / 100.0)[0] for i in range(1, 1000))
        self.assertAlmostEqual(peak - 1.0, 0.045, places=4)
        self.assertAlmostEqual(path.overshoot, 0.045, places=9)
        self.assertFalse(path.clamped)

    def test_swing_time_is_half_a_period(self):
        path = self.path(swing=5.0)
        crests = []
        prev = path.at(9.0)[1]
        for i in range(1, 4000):
            t = 9.0 + i / 100.0
            v = path.at(t)[1]
            if prev > 0 >= v or prev < 0 <= v:
                crests.append(t)
            prev = v
        self.assertAlmostEqual(crests[1] - crests[0], 5.0, places=1)
        self.assertAlmostEqual(crests[2] - crests[1], 5.0, places=1)

    def test_heavier_rings_longer(self):
        def swings(weight):
            path = self.path(weight=weight)
            first = path.at(9.0 + math.atan2(path.w, path.sigma) / path.w)[0] - 1.0
            later = path.at(9.0 + math.atan2(path.w, path.sigma) / path.w + 2 * math.pi / path.w)[0] - 1.0
            return later / first
        self.assertGreater(swings(2.0), swings(1.0))
        self.assertGreater(swings(1.0), swings(0.5))

    def test_never_overshoots_on_the_way(self):
        # A long move asked to arrive fast enough for a big overshoot would have to dip on the way:
        # its arrival slope is held to three times the average.
        path = self.path(amplitude=20.0, t_b=30.0)
        self.assertTrue(path.clamped)
        self.assertLess(path.overshoot, 0.2)
        values = [path.at(i / 100.0)[0] for i in range(0, 3001)]
        self.assertTrue(all(b >= a - 1e-12 for a, b in zip(values, values[1:])))
        self.assertLessEqual(max(values), 1.0 + 1e-12)

    def test_no_amplitude_no_overshoot(self):
        path = self.path(amplitude=0.0)
        self.assertEqual(path.at(15.0), (1.0, 0.0))


class ParamTests(unittest.TestCase):

    def test_defaults_and_clamping(self):
        p = ps.params()
        self.assertEqual(sorted(p), ["amplitude", "overlap", "sway", "swing", "weight"])
        self.assertEqual(ps.params(weight=99.0)["weight"], ps.RANGES["weight"][1])
        self.assertEqual(ps.params(swing=0.0)["swing"], ps.RANGES["swing"][0])

    def test_damping_follows_weight(self):
        self.assertAlmostEqual(ps.damping(1.0), ps.ZETA)
        self.assertAlmostEqual(ps.damping(2.0), ps.ZETA / 2.0)
        self.assertEqual(ps.damping(0.01), 0.9)


class SolveTests(unittest.TestCase):

    def solve(self, **given):
        return ps.solve(0.0, 9.0, 32.36 / 11.645, 32.36 / 11.645, 11.645, given)

    def test_rows_cover_a_to_the_end_frame_by_frame(self):
        tr = self.solve()
        times = [r.t for r in tr.rows]
        self.assertEqual(times[0], 0.0)
        self.assertEqual(times, [float(i) for i in range(len(times))])
        self.assertEqual(times[-1], tr.end)
        self.assertGreater(tr.end, 9.0)

    def test_ends_exactly_on_b(self):
        last = self.solve().rows[-1]
        self.assertEqual((last.p, last.tilt, last.sink, last.sway, last.yaw), (1.0, 0.0, 0.0, 0.0, 0.0))

    def test_starts_exactly_on_a(self):
        first = self.solve().rows[0]
        self.assertEqual((first.p, first.tilt, first.sink, first.sway, first.yaw), (0.0, 0.0, 0.0, 0.0, 0.0))

    def test_signs_the_top_lags_it_sinks_down_and_sways_left(self):
        tr = self.solve()
        mid = [r for r in tr.rows if r.t == 5.0][0]
        self.assertGreater(mid.tilt, 0.0)
        self.assertGreater(mid.sink, 0.0)
        self.assertGreater(mid.sway, 0.0)
        self.assertGreater(mid.yaw, 0.0)
        left = self.solve(sway=-1.0)
        self.assertLess([r for r in left.rows if r.t == 5.0][0].sway, 0.0)

    def test_controls_scale_what_they_name(self):
        base = self.solve()
        self.assertGreater(self.solve(overlap=2.0).peak_tilt, 1.5 * base.peak_tilt)
        self.assertGreater(self.solve(weight=2.0).peak_sink, 1.5 * base.peak_sink)
        self.assertEqual(self.solve(overlap=0.0).peak_tilt, 0.0)
        self.assertEqual(self.solve(sway=0.0).peak_sway, 0.0)

    def test_heavier_settles_later(self):
        self.assertGreater(self.solve(weight=2.0).end, self.solve(weight=1.0).end)
        self.assertGreater(self.solve(weight=1.0).end, self.solve(weight=0.5).end)

    def test_no_travel_no_springs(self):
        tr = ps.solve(0.0, 9.0, 0.0, 0.0, 10.0, None)
        self.assertEqual(tr.peak_tilt + tr.peak_sink + tr.peak_sway, 0.0)

    def test_fractional_keys(self):
        tr = ps.solve(0.5, 9.25, 2.0, 2.0, 10.0, None)
        self.assertEqual(tr.rows[0].t, 0.5)
        self.assertEqual(tr.rows[1].t, 1.0)
        self.assertEqual(tr.rows[-1].t, tr.end)
        self.assertEqual(tr.end, int(tr.end))


try:
    import maya.api.OpenMaya as om
except ImportError:   # pragma: no cover
    om = None


def close(a, b, tol=1e-9):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


class AxisTests(unittest.TestCase):

    def test_auto_picks_the_axis_nearest_world_up_with_its_sign(self):
        rows = ((1, 0, 0), (0, 0, -1), (0, 1, 0))          # local Z points up
        self.assertEqual(ps.up_axis(rows), (2, 1.0))
        rows = ((1, 0, 0), (0, -1, 0), (0, 0, 1))          # local Y points down
        self.assertEqual(ps.up_axis(rows), (1, -1.0))

    def test_override(self):
        self.assertEqual(ps.up_axis(((1, 0, 0), (0, 1, 0), (0, 0, 1)), "-X"), (0, -1.0))

    def test_bottom_is_the_low_end_and_height_is_world(self):
        rows = ((4.0, 0, 0), (0, 11.0, 0), (0, 0, 3.0))
        bottom, height = ps.bottom_and_height((-0.5, -0.5, -0.5), (0.5, 0.5, 0.5), 1, 1.0, rows)
        self.assertEqual(bottom, (0.0, -0.5, 0.0))
        self.assertAlmostEqual(height, 11.0)
        bottom, _ = ps.bottom_and_height((-0.5, -0.5, -0.5), (0.5, 0.5, 0.5), 1, -1.0, rows)
        self.assertEqual(bottom, (0.0, 0.5, 0.0))


@unittest.skipIf(om is None, "needs maya.api.OpenMaya")
class TransformTests(unittest.TestCase):

    FIXED = {
        "scale": (4.1, 11.6, 3.9), "shear": (0.1, 0.0, 0.05), "scalePivot": (-0.2, 0.3, 0.1),
        "scalePivotTranslate": (0.05, 0.1, 0.0), "rotatePivot": (0.1, -0.5, 0.2),
        "rotatePivotTranslate": (0.3, 0.0, -0.1), "rotateAxis": (5.0, -7.0, 12.0)}

    def test_round_trip_in_every_rotate_order(self):
        for order in range(6):
            m = ps.local_matrix((1.0, 2.0, -3.0), (10.0, -20.0, 30.0), order, self.FIXED)
            t, r = ps.channels_from_local(m, order, self.FIXED, (10.0, -20.0, 30.0))
            self.assertTrue(close(t, (1.0, 2.0, -3.0), 1e-9), (order, t))
            self.assertTrue(close(r, (10.0, -20.0, 30.0), 1e-9), (order, r))

    def test_euler_stays_near_its_neighbour(self):
        m = ps.local_matrix((0, 0, 0), (0.0, 370.0, 0.0), 0, ps.IDENTITY_FIXED)
        _, r = ps.channels_from_local(m, 0, ps.IDENTITY_FIXED, (0.0, 369.0, 0.0))
        self.assertTrue(close(r, (0.0, 370.0, 0.0), 1e-9), r)

    def test_tilt_moves_the_top_back_against_the_motion(self):
        heading = om.MVector(0, 0, -1)
        g = ps.secondary(om.MPoint(0, 0, 0), heading, 30.0, 0.0, 0.0, 0.0)
        top = om.MPoint(0, 10, 0) * g
        self.assertAlmostEqual(top.z, 10 * math.sin(math.radians(30)))
        self.assertAlmostEqual((om.MPoint(0, 0, 0) * g).z, 0.0)   # the bottom stays

    def test_sink_is_down_and_sway_is_left(self):
        heading = om.MVector(0, 0, -1)                  # facing -Z with Y up, left is -X
        g = ps.secondary(om.MPoint(0, 0, 0), heading, 0.0, 0.0, 2.0, 1.5)
        p = om.MPoint(0, 0, 0) * g
        self.assertTrue(close((p.x, p.y, p.z), (-1.5, -2.0, 0.0), 1e-12))

    def test_yaw_is_about_world_up_through_the_bottom(self):
        g = ps.secondary(om.MPoint(5, 0, 0), om.MVector(0, 0, -1), 0.0, 90.0, 0.0, 0.0)
        p = om.MPoint(6, 0, 0) * g
        self.assertTrue(close((p.x, p.y, p.z), (5.0, 0.0, -1.0), 1e-12))

    def test_no_heading_no_tilt_but_still_a_sink(self):
        g = ps.secondary(om.MPoint(0, 0, 0), None, 30.0, 20.0, 1.0, 1.0)
        p = om.MPoint(0, 10, 0) * g
        self.assertTrue(close((p.x, p.y, p.z), (0.0, 9.0, 0.0), 1e-12))

    def test_channel_frames_start_on_a_and_end_on_b(self):
        tr = ps.solve(0.0, 9.0, 2.0, 2.0, 10.0, None)
        pose_a = ((0.0, 5.0, 0.0), (0.0, 0.0, 0.0))
        pose_b = ((0.0, 5.0, -20.0), (3.0, 0.0, 0.0))
        parent = om.MMatrix()
        frames = ps.channel_frames(tr, pose_a, pose_b, 0, ps.IDENTITY_FIXED, lambda t: parent,
                                   (0.0, -0.5, 0.0), om.MVector(0, 0, -1))
        self.assertTrue(close(frames[0][1] + frames[0][2], pose_a[0] + pose_a[1], 1e-9))
        self.assertTrue(close(frames[-1][1] + frames[-1][2], pose_b[0] + pose_b[1], 1e-9))
        self.assertEqual([f[0] for f in frames], [r.t for r in tr.rows])


if __name__ == "__main__":
    unittest.main()
