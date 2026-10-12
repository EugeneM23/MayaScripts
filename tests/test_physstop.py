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


def close(a, b, tol=1e-9):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


class PathTests(unittest.TestCase):

    def path(self, overshoot=4.5, swing=5.0, weight=1.0, t_a=0.0, t_m=5.0, t_b=9.0, s_m=0.5):
        return ps.Path(t_a, t_m, t_b, s_m, overshoot, swing, ps.damping(weight))

    def test_starts_at_rest_and_hits_the_breakdown_and_b_at_their_keys(self):
        path = self.path(s_m=0.6)
        self.assertEqual(path.at(0.0), (0.0, 0.0))
        self.assertAlmostEqual(path.at(5.0)[0], 0.6, places=12)
        self.assertAlmostEqual(path.at(9.0)[0], 1.0, places=12)

    def test_speed_is_continuous_at_the_breakdown_and_at_b(self):
        path = self.path(s_m=0.6)
        for t in (5.0, 9.0):
            before = path.at(t - 1e-7)[1]
            after = path.at(t + 1e-7)[1]
            self.assertAlmostEqual(before, after, places=5)
        self.assertGreater(path.at(9.0)[1], 0.0)

    def test_never_runs_backwards_even_for_an_uneven_breakdown(self):
        for t_m, s_m in ((5.0, 0.5), (2.0, 0.7), (8.0, 0.2), (3.0, 0.05), (7.0, 0.95)):
            path = self.path(t_m=t_m, s_m=s_m)
            values = [path.at(i / 200.0)[0] for i in range(0, 1801)]
            self.assertTrue(all(b >= a - 1e-12 for a, b in zip(values, values[1:])), (t_m, s_m))
            self.assertLessEqual(max(values), 1.0 + 1e-12)

    def test_first_overshoot_is_the_asked_one(self):
        path = self.path(overshoot=4.5)
        peak = max(path.at(9.0 + i / 100.0)[0] for i in range(1, 1000))
        self.assertAlmostEqual(peak - 1.0, 0.045, places=4)
        self.assertAlmostEqual(path.overshoot, 0.045, places=9)
        self.assertFalse(path.clamped)

    def test_swing_length_is_half_a_period(self):
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
        def ratio(weight):
            path = self.path(weight=weight)
            tau = math.atan2(path.w, path.sigma) / path.w
            return (path.at(9.0 + tau + 2 * math.pi / path.w)[0] - 1.0) / (path.at(9.0 + tau)[0] - 1.0)
        self.assertGreater(ratio(2.0), ratio(1.0))
        self.assertGreater(ratio(1.0), ratio(0.5))

    def test_a_slow_last_stretch_holds_the_overshoot(self):
        # A long last stretch asked to arrive fast would dip on the way: the arrival is held to
        # three times that stretch's average.
        path = self.path(overshoot=20.0, t_m=5.0, t_b=40.0, s_m=0.5)
        self.assertTrue(path.clamped)
        self.assertLess(path.overshoot, 0.2)

    def test_no_overshoot_stays_still_after_b(self):
        path = self.path(overshoot=0.0)
        self.assertEqual(path.at(15.0), (1.0, 0.0))


class ArcTests(unittest.TestCase):

    def test_passes_through_all_three(self):
        arc = ps.Arc((0.0, 0.0, 0.0), (3.0, 1.0, -10.0), (0.0, 0.0, -20.0))
        self.assertTrue(close(arc.at(0.0), (0.0, 0.0, 0.0), 1e-9))
        self.assertTrue(close(arc.at(arc.s_m), (3.0, 1.0, -10.0), 1e-9))
        self.assertTrue(close(arc.at(1.0), (0.0, 0.0, -20.0), 1e-9))

    def test_straight_when_the_breakdown_is_on_the_line(self):
        arc = ps.Arc((0.0, 0.0, 0.0), (0.0, 0.0, -7.0), (0.0, 0.0, -20.0))
        self.assertAlmostEqual(arc.length, 20.0, places=6)
        self.assertAlmostEqual(arc.s_m, 0.35, places=6)
        self.assertAlmostEqual(arc.bend(), 0.0, places=9)
        for i in range(11):
            x, y, _ = arc.at(i / 10.0)
            self.assertAlmostEqual(x, 0.0, places=9)
            self.assertAlmostEqual(y, 0.0, places=9)

    def test_bends_toward_the_breakdown(self):
        arc = ps.Arc((0.0, 0.0, 0.0), (4.0, 0.0, -10.0), (0.0, 0.0, -20.0))
        self.assertAlmostEqual(arc.bend(), 4.0, places=9)
        self.assertGreater(arc.length, 20.0)
        self.assertGreater(arc.at(0.25)[0], 0.0)

    def test_runs_on_past_b_along_its_tangent(self):
        arc = ps.Arc((0.0, 0.0, 0.0), (4.0, 0.0, -10.0), (0.0, 0.0, -20.0))
        tx, ty, tz = arc.tangent
        self.assertAlmostEqual(tx * tx + ty * ty + tz * tz, 1.0, places=9)
        self.assertLess(tx, 0.0)          # arriving from the +X side it leaves towards -X
        self.assertLess(tz, 0.0)
        past = arc.at(1.1)
        expected = tuple(b + 0.1 * arc.length * t for b, t in zip((0.0, 0.0, -20.0), arc.tangent))
        self.assertTrue(close(past, expected, 1e-9))

    def test_the_arc_fraction_grows_with_the_distance_along(self):
        arc = ps.Arc((0.0, 0.0, 0.0), (6.0, 0.0, -10.0), (0.0, 0.0, -20.0))
        points = [arc.at(i / 100.0) for i in range(101)]
        steps = [math.dist(a, b) for a, b in zip(points, points[1:])]
        self.assertLess(max(steps) / min(steps), 1.05)        # even steps: the arc is measured

    def test_the_same_three_points_make_no_arc(self):
        arc = ps.Arc((1.0, 2.0, 3.0), (1.0, 2.0, 3.0), (1.0, 2.0, 3.0))
        self.assertEqual(arc.length, 0.0)
        self.assertTrue(close(arc.at(0.7), (1.0, 2.0, 3.0), 1e-12))
        self.assertTrue(close(arc.at(1.2), (1.0, 2.0, 3.0), 1e-12))


class PinTests(unittest.TestCase):

    def test_zero_at_a_and_b_one_at_the_breakdown(self):
        self.assertEqual(ps.pin_weight(0.0, 0.0, 4.0, 10.0), 0.0)
        self.assertEqual(ps.pin_weight(4.0, 0.0, 4.0, 10.0), 1.0)
        self.assertEqual(ps.pin_weight(10.0, 0.0, 4.0, 10.0), 0.0)
        self.assertEqual(ps.pin_weight(15.0, 0.0, 4.0, 10.0), 0.0)
        self.assertEqual(ps.pin_weight(-1.0, 0.0, 4.0, 10.0), 0.0)

    def test_smooth_and_rising_then_falling(self):
        values = [ps.pin_weight(t / 10.0, 0.0, 4.0, 10.0) for t in range(0, 101)]
        self.assertTrue(all(b >= a for a, b in zip(values[:40], values[1:41])))
        self.assertTrue(all(b <= a for a, b in zip(values[40:100], values[41:101])))
        # flat at its ends and at the top (smoothstep): tiny steps there
        self.assertLess(values[1], 0.002)
        self.assertGreater(values[39], 0.998)


class ParamTests(unittest.TestCase):

    def test_defaults_and_clamping(self):
        p = ps.params()
        self.assertEqual(sorted(p), ["overshoot", "swing", "weight"])
        self.assertEqual(p, {"overshoot": 3.0, "swing": 5.0, "weight": 1.0})
        self.assertEqual(ps.params(sway=2.0, axis="+Z"), p)           # an older memo's extras are ignored
        self.assertEqual(ps.params(weight=99.0)["weight"], ps.RANGES["weight"][1])
        self.assertEqual(ps.params(swing=0.0)["swing"], ps.RANGES["swing"][0])

    def test_damping_follows_weight(self):
        self.assertAlmostEqual(ps.damping(1.0), ps.ZETA)
        self.assertAlmostEqual(ps.damping(2.0), ps.ZETA / 2.0)
        self.assertEqual(ps.damping(0.01), 0.9)


class SolveTests(unittest.TestCase):

    def solve(self, t_m=5.0, s_m=0.5, **given):
        return ps.solve(0.0, t_m, 9.0, s_m, 32.36 / 11.645, given)

    def test_rows_cover_a_to_the_end_frame_by_frame(self):
        tr = self.solve()
        times = [r.t for r in tr.rows]
        self.assertEqual(times, [float(i) for i in range(len(times))])
        self.assertEqual(times[-1], tr.end)
        self.assertGreater(tr.end, 9.0)

    def test_a_fractional_breakdown_has_its_own_row(self):
        tr = self.solve(t_m=4.5)
        self.assertIn(4.5, [r.t for r in tr.rows])
        self.assertAlmostEqual(tr.row_at(4.5).p, 0.5, places=12)

    def test_ends_exactly_on_b_and_starts_on_a(self):
        tr = self.solve()
        first, last = tr.rows[0], tr.rows[-1]
        self.assertEqual((first.p, first.tilt), (0.0, 0.0))
        self.assertEqual((last.p, last.tilt), (1.0, 0.0))

    def test_the_lag_shape_is_one_at_the_breakdown(self):
        tr = self.solve()
        self.assertTrue(tr.readable)
        self.assertAlmostEqual(tr.lag_share(tr.row_at(5.0).tilt), 1.0, places=12)
        after = [tr.lag_share(r.tilt) for r in tr.rows if r.t > 10]
        self.assertLess(min(after), 0.0)                       # the top swings past after the stop

    def test_a_breakdown_where_the_spring_barely_bends_is_read_at_the_peak(self):
        tr = self.solve(t_m=0.3, s_m=0.001)
        self.assertFalse(tr.readable)
        self.assertAlmostEqual(max(abs(tr.lag_share(r.tilt)) for r in tr.rows), 1.0, places=9)

    def test_nothing_but_the_tilt_rides_on_the_path(self):
        # the breakdown sets how the object comes in: no spring of the model moves the bottom off the arc
        self.assertEqual(ps.Row.__slots__, ("t", "p", "tilt"))
        for name in ("K_SINK", "K_SWAY", "K_YAW", "SWAY_RATE", "SINK_LIMIT", "SWAY_LIMIT"):
            self.assertFalse(hasattr(ps, name), name)

    def test_heavier_settles_later(self):
        self.assertGreater(self.solve(weight=2.0).end, self.solve(weight=1.0).end)
        self.assertGreater(self.solve(weight=1.0).end, self.solve(weight=0.5).end)

    def test_no_travel_no_tilt(self):
        tr = ps.solve(0.0, 5.0, 9.0, 0.5, 0.0, None)
        self.assertEqual(tr.peak_tilt, 0.0)
        self.assertFalse(tr.readable)


try:
    import maya.api.OpenMaya as om
except ImportError:   # pragma: no cover
    om = None


class AxisTests(unittest.TestCase):

    def test_auto_picks_the_axis_nearest_world_up_with_its_sign(self):
        rows = ((1, 0, 0), (0, 0, -1), (0, 1, 0))          # local Z points up
        self.assertEqual(ps.up_axis(rows), (2, 1.0))
        rows = ((1, 0, 0), (0, -1, 0), (0, 0, 1))          # local Y points down
        self.assertEqual(ps.up_axis(rows), (1, -1.0))

    def test_always_auto(self):
        self.assertFalse(hasattr(ps, "AXES"))
        with self.assertRaises(TypeError):
            ps.up_axis(((1, 0, 0), (0, 1, 0), (0, 0, 1)), "-X")

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

    def test_the_lag_turns_the_top_about_the_bottom(self):
        lag = om.MQuaternion(math.radians(30), om.MVector(1, 0, 0))
        g = ps.secondary(om.MPoint(0, 2, 0), lag)
        top = om.MPoint(0, 12, 0) * g
        self.assertAlmostEqual(top.z, 10 * math.sin(math.radians(30)))
        bottom = om.MPoint(0, 2, 0) * g
        self.assertTrue(close((bottom.x, bottom.y, bottom.z), (0.0, 2.0, 0.0), 1e-12))   # the bottom stays

    def compose(self, pose_m, t_m=5.0, given=None):
        pose_a = ((0.0, 5.0, 0.0), (0.0, 0.0, 0.0))
        pose_b = ((0.0, 5.0, -20.0), (0.0, 0.0, 0.0))
        bottom = (0.0, -0.5, 0.0)
        parent = om.MMatrix()
        bases = [om.MPoint(bottom) * ps.local_matrix(p[0], p[1], 0, ps.IDENTITY_FIXED) for p in
                 (pose_a, pose_m, pose_b)]
        arc = ps.Arc(*[(b.x, b.y, b.z) for b in bases])
        tr = ps.solve(0.0, t_m, 9.0, arc.s_m, arc.length / 1.0, given)
        setup = ps.Setup((pose_a, pose_m, pose_b), (0.0, t_m, 9.0), 0, ps.IDENTITY_FIXED,
                         lambda t: parent, bottom, arc, om.MVector(0, 0, -1))
        frames, info = ps.compose(tr, setup)
        return frames, info, (pose_a, pose_m, pose_b)

    def bottoms(self, frames):
        """{t: the bottom's world point} for every frame written."""
        out = {}
        for t, tr, ro in frames:
            p = om.MPoint(0.0, -0.5, 0.0) * ps.local_matrix(tr, ro, 0, ps.IDENTITY_FIXED)
            out[t] = (p.x, p.y, p.z)
        return out

    def test_a_m_and_b_are_hit_exactly(self):
        frames, _, (pose_a, pose_m, pose_b) = self.compose(((1.0, 4.8, -10.0), (15.0, 3.0, -2.0)))
        by_time = {f[0]: f for f in frames}
        self.assertTrue(close(frames[0][1] + frames[0][2], pose_a[0] + pose_a[1], 1e-9))
        self.assertTrue(close(by_time[5.0][1] + by_time[5.0][2], pose_m[0] + pose_m[1], 1e-6))
        self.assertTrue(close(frames[-1][1] + frames[-1][2], pose_b[0] + pose_b[1], 1e-9))

    def test_a_breakdown_tilted_back_reads_back(self):
        # moving towards -Z, the top behind the motion is +Z: a +rotateX tilts it back
        # (no sway: its yaw at M is taken out of the lag, and on this 1 cm object it saturates)
        _, info, _ = self.compose(((0.0, 5.0, -10.0), (20.0, 0.0, 0.0)))
        self.assertAlmostEqual(info["lag_deg"], 20.0, delta=1e-6)
        self.assertEqual(info["lag_dir"], "back")

    def test_a_breakdown_tilted_aside_reads_aside(self):
        # rotateZ +20 swings the top towards -X: the left of a motion towards -Z
        _, info, _ = self.compose(((0.0, 5.0, -10.0), (0.0, 0.0, 20.0)))
        self.assertEqual(info["lag_dir"], "left")

    def test_an_untilted_even_breakdown_gives_no_lag_and_a_straight_path(self):
        frames, info, _ = self.compose(((0.0, 5.0, -10.0), (0.0, 0.0, 0.0)), given={"weight": 0.2})
        self.assertLess(info["lag_deg"], 1e-6)
        self.assertLess(info["bend"], 1e-9)
        self.assertEqual(info["entry"], "straight in")
        for t, b in self.bottoms(frames).items():
            self.assertTrue(close((b[0], b[1]), (0.0, 4.5), 1e-9), (t, b))       # on the line A-B, at its height
        self.assertTrue(all(abs(f[2][0]) < 1e-6 for f in frames))

    def test_a_raised_breakdown_comes_in_from_above(self):
        # the animator's report: a breakdown raised still came into B from below (a sink spring under the arc)
        frames, info, _ = self.compose(((0.0, 8.0, -10.0), (0.0, 0.0, 0.0)))
        self.assertEqual(info["entry"], "arc bends 3.0 cm up")
        b = self.bottoms(frames)
        approach = [b[t][1] for t in sorted(b) if 0.0 < t < 9.0]
        self.assertTrue(all(y > 4.5 for y in approach), approach)                # above B's height all the way
        self.assertAlmostEqual(b[9.0][1], 4.5, places=9)                          # on B at B's frame
        after = [b[t][1] for t in sorted(b) if 9.0 < t <= 13.0]
        self.assertLess(min(after), 4.5)                                          # then on, down past it
        self.assertLess(after[0], 4.5)

    def test_a_lowered_breakdown_comes_in_from_below(self):
        frames, info, _ = self.compose(((0.0, 2.0, -10.0), (0.0, 0.0, 0.0)))
        self.assertEqual(info["entry"], "arc bends 3.0 cm down")
        b = self.bottoms(frames)
        approach = [b[t][1] for t in sorted(b) if 0.0 < t < 9.0]
        self.assertTrue(all(y < 4.5 for y in approach), approach)
        self.assertAlmostEqual(b[9.0][1], 4.5, places=9)
        self.assertGreater(b[10.0][1], 4.5)                                       # on up past it

    def test_a_breakdown_aside_comes_in_from_that_side(self):
        frames, info, _ = self.compose(((-3.0, 5.0, -10.0), (0.0, 0.0, 0.0)))
        self.assertEqual(info["entry"], "arc bends 3.0 cm left")                  # -X is left of -Z
        b = self.bottoms(frames)
        self.assertTrue(all(b[t][0] < 0.0 for t in sorted(b) if 0.0 < t < 9.0))
        self.assertTrue(all(abs(b[t][1] - 4.5) < 1e-9 for t in b))                # and no sink at all


def _mul(p, m):
    return tuple(sum(p[k] * m[k][j] for k in range(4)) for j in range(4))


def cube_components(data):
    """The cube decomposed as the model describes it: the bottom's progress along its path, the long
    axis's tilt back (minus pose B's own 2.9 deg lean, carried by the path), the bottom's sink and sway
    (+ = left = -X), the yaw of its local X about world up."""
    mats = [[m[i * 4:(i + 1) * 4] for i in range(4)] for m in data["wm"]]
    bottom = [_mul((0, -0.5, 0, 1), m) for m in mats]
    top = [_mul((0, 0.5, 0, 1), m) for m in mats]
    height = math.dist(bottom[0][:3], top[0][:3])
    start, finish = bottom[0][2], bottom[-1][2]
    travel = [(b[2] - start) / (finish - start) for b in bottom]
    lean = math.degrees(math.atan2(top[-1][2] - bottom[-1][2], top[-1][1] - bottom[-1][1]))
    tilt = [math.degrees(math.atan2(t[2] - b[2], t[1] - b[1])) - lean * max(0.0, p)
            for b, t, p in zip(bottom, top, travel)]
    sink = [bottom[0][1] - b[1] for b in bottom]
    sway = [-b[0] for b in bottom]
    yaw = []
    for m in mats:
        x = m[0][:3]
        yaw.append(math.degrees(math.atan2(-x[2], x[0])))
    t_b = next(i + (1 - travel[i]) / (travel[i + 1] - travel[i]) for i in range(30)
               if travel[i] < 1 <= travel[i + 1])
    return {"travel": travel, "tilt": tilt, "sink": sink, "sway": sway, "yaw": yaw, "t_b": t_b,
            "reach": abs(finish - start) / height, "height": height, "bottom": [b[:3] for b in bottom]}


def rms(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)) / len(a))


CUBE_BREAKDOWN = 5


def cube_model(cube, given=None, t_m=CUBE_BREAKDOWN):
    """The model between the cube's frame 0, its frame t_m and the frame it passes B (its rest place): its
    components on frames 0..30 - the bottom on the arc through the three, the tilt shape scaled to the
    cube's lag at t_m (as the breakdown sets it)."""
    bottom = cube["bottom"]
    arc = ps.Arc(bottom[0], bottom[t_m], bottom[-1])
    tr = ps.solve(0.0, float(t_m), cube["t_b"], arc.s_m, arc.length / cube["height"], given)
    rows = {r.t: r for r in tr.rows}
    last = tr.rows[-1]
    scale = cube["tilt"][t_m] / tr.row_at(float(t_m)).tilt
    start, finish = bottom[0], bottom[-1]
    out = {k: [] for k in ("travel", "tilt", "sink", "sway")}
    for f in range(31):
        r = rows.get(float(f), last)
        x, y, z = arc.at(r.p)
        out["travel"].append((z - start[2]) / (finish[2] - start[2]))
        out["tilt"].append(r.tilt * scale)
        out["sink"].append(start[1] - y)
        out["sway"].append(-x)
    return out, tr


class CubeTests(unittest.TestCase):
    """The defaults ARE the cube: the model run between the cube's own frames 0 and 5 and the frame it
    passes B."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(FOLDER, "cube_reference.json")) as f:
            cls.cube = cube_components(json.load(f))
        cls.model, tr = cube_model(cls.cube)
        cls.end = tr.end

    def test_the_cube_passes_b_at_frame_nine(self):
        self.assertAlmostEqual(self.cube["t_b"], 9.1, places=1)

    def test_travel(self):
        self.assertLess(rms(self.model["travel"], self.cube["travel"]) * 32.36, 0.5)

    def test_tilt(self):
        self.assertLess(rms(self.model["tilt"], self.cube["tilt"]), 2.5)

    def test_height_and_side_from_the_arc(self):
        # nothing is fitted here: the arc through the cube's own frames 0, 5 and rest. The cube still came
        # into its place 2 cm low as it passed it; the model is on B's height at B's frame.
        self.assertLess(rms(self.model["sink"], self.cube["sink"]), 0.8)
        self.assertLess(rms(self.model["sway"], self.cube["sway"]), 0.45)
        self.assertAlmostEqual(self.model["sink"][CUBE_BREAKDOWN], self.cube["sink"][CUBE_BREAKDOWN], places=9)
        self.assertGreater(min(self.model["sink"][1:9]), 0.0)       # it comes in from below, as the cube did

    def test_settles_where_the_cube_does(self):
        self.assertTrue(24 <= self.end <= 36, self.end)


class FakeCmds(object):
    """Just enough of maya.cmds for the window: records controls, answers queries."""

    def __init__(self):
        self.values = {}
        self.vars = {}
        self.created = []
        self.selection = []

    def window(self, name, exists=False, **kw):
        if exists:
            return False
        self.created.append(("window", name))
        return name

    def windowPref(self, name, exists=False, remove=False):
        return False

    def deleteUI(self, name):
        pass

    def columnLayout(self, *a, **kw):
        return "col"

    def rowLayout(self, *a, **kw):
        return "row"

    def setParent(self, *a):
        pass

    def showWindow(self, name):
        self.created.append(("show", name))

    def text(self, name=None, edit=False, label=None, **kw):
        if edit:
            self.values[name] = label
        elif name is None and kw.get("font") == "boldLabelFont":
            self.created.append(("heading", label))
        return name

    def button(self, *a, **kw):
        self.created.append(("button", kw.get("label")))

    def floatSliderGrp(self, name, query=False, value=None, edit=False, **kw):
        if query:
            return self.values[name]
        self.values[name] = value
        if not edit:
            self.created.append(("slider", name, kw.get("label")))
        return name

    def optionMenu(self, name, query=False, value=None, edit=False, **kw):
        if query:
            return self.values.get(name, "Auto")
        if value is not None:
            self.values[name] = value
        if not edit:
            self.created.append(("menu", name, kw.get("label")))
        return name

    def menuItem(self, **kw):
        pass

    def optionVar(self, exists=None, q=None, floatValue=None, stringValue=None):
        if exists is not None:
            return exists in self.vars
        if q is not None:
            return self.vars[q]
        name, value = floatValue or stringValue
        self.vars[name] = value


class WindowTests(unittest.TestCase):

    def setUp(self):
        self.fake = FakeCmds()
        self.saved = (ps._cmds, ps.apply, ps.selected, ps.remembered, ps.restore)
        self.calls = []
        ps._cmds = lambda: self.fake
        ps.apply = lambda nodes, given=None: self.calls.append((nodes, given)) or ["done"]
        ps.restore = lambda nodes: self.calls.append(("restore", nodes)) or ["restored"]
        ps.selected = lambda: list(self.fake.selection)
        ps.remembered = lambda node: {"tE": 1} if node.endswith("applied") else None

    def tearDown(self):
        ps._cmds, ps.apply, ps.selected, ps.remembered, ps.restore = self.saved

    def test_three_sliders_and_nothing_else(self):
        ps.show()
        made = [c for c in self.fake.created if c[0] in ("heading", "slider", "menu")]
        self.assertEqual([c[0] for c in made], ["slider", "slider", "slider"])
        self.assertEqual([c[2] for c in made], ["Overshoot, %", "Swing length, fr", "Weight"])
        for name, default in ps.DEFAULTS:
            self.assertEqual(self.fake.values[ps._control(name)], default)
        self.assertEqual([c[1] for c in self.fake.created if c[0] == "button"], ["Apply", "Restore keys", "Reset"])

    def test_no_overlap_sway_or_axis(self):
        ps.show()
        for name in ("overlap", "sway"):
            self.assertNotIn(ps._control(name), self.fake.values)
            self.assertNotIn(name, ps.params())
        self.assertFalse(hasattr(ps, "AXIS_MENU"))
        self.assertIn("above, below or the side", ps.INTRO)

    def test_remembered_values_come_back(self):
        self.fake.vars[ps.OPTION + "weight"] = 2.5
        self.fake.vars[ps.OPTION + "axis"] = "+Z"           # left by an older version: ignored
        ps.show()
        self.assertEqual(self.fake.values[ps._control("weight")], 2.5)

    def test_apply_reads_the_sliders_and_remembers_them(self):
        ps.show()
        self.fake.values[ps._control("overshoot")] = 7.0
        self.fake.selection = ["|cube"]
        ps.press_apply()
        nodes, given = self.calls[-1]
        self.assertEqual(nodes, ["|cube"])
        self.assertEqual(given, {"overshoot": 7.0, "swing": 5.0, "weight": 1.0})
        self.assertEqual(self.fake.vars[ps.OPTION + "overshoot"], 7.0)
        self.assertNotIn(ps.OPTION + "axis", self.fake.vars)
        self.assertEqual(self.fake.values[ps.STATUS], "done")

    def test_a_slider_re_applies_only_what_already_carries_a_transition(self):
        ps.show()
        self.fake.selection = ["|cube"]
        ps.slider_changed()
        self.assertEqual(self.calls, [])
        self.assertIn("Apply", self.fake.values[ps.STATUS])
        self.fake.selection = ["|cube_applied"]
        ps.slider_changed()
        self.assertEqual(self.calls[-1][0], ["|cube_applied"])

    def test_nothing_selected_says_so(self):
        ps.show()
        ps.press_apply()
        self.assertEqual(self.calls, [])
        self.assertIn("three keys", self.fake.values[ps.STATUS])

    def test_restore_goes_to_restore(self):
        ps.show()
        self.fake.selection = ["|cube_applied"]
        ps.press_restore()
        self.assertEqual(self.calls[-1], ("restore", ["|cube_applied"]))

    def test_reset_puts_the_defaults_back(self):
        ps.show()
        self.fake.values[ps._control("swing")] = 9.0
        ps.press_reset()
        self.assertEqual(self.fake.values[ps._control("swing")], dict(ps.DEFAULTS)["swing"])

    def test_the_drop_handler_exists(self):
        self.assertTrue(callable(ps.onMayaDroppedPythonFile))


if __name__ == "__main__":
    unittest.main()
