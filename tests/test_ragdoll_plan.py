"""maya_ragdoll.plan - the ragdoll's pure half (2026-10-16)."""

import math
import subprocess
import sys
import unittest

import numpy as np

from maya_ragdoll import plan


def turn(axis, degrees):
    """A row-vector rotation of `degrees` about a world axis."""
    a = np.asarray(axis, dtype=float) / np.linalg.norm(axis)
    t = math.radians(degrees)
    c, s = math.cos(t), math.sin(t)
    x, y, z = a
    col = np.array([[c + x * x * (1 - c), x * y * (1 - c) - z * s, x * z * (1 - c) + y * s],
                    [y * x * (1 - c) + z * s, c + y * y * (1 - c), y * z * (1 - c) - x * s],
                    [z * x * (1 - c) - y * s, z * y * (1 - c) + x * s, c + z * z * (1 - c)]])
    return col.T


def at(rows, point):
    return plan.frame(rows, point)


class Bodies(unittest.TestCase):

    def test_sixteen_bodies_with_masses_that_sum_to_the_whole(self):
        keys = [r[0] for r in plan.BODIES]
        self.assertEqual(len(keys), 16)
        m = plan.masses(75.0, keys)
        self.assertAlmostEqual(sum(m.values()), 75.0, places=9)
        self.assertGreater(m["thigh_l"], m["calf_l"])
        self.assertAlmostEqual(m["thigh_l"], m["thigh_r"])

    def test_a_missing_first_bone_names_its_body_a_missing_finger_does_not(self):
        names = set(b for r in plan.BODIES for b in r[1]) | {"middle_01_l", "middle_01_r"}
        self.assertEqual(plan.missing_bodies(names), [])
        self.assertEqual(plan.missing_bodies(names - {"middle_01_l"}), [])
        self.assertEqual(plan.missing_bodies(names - {"calf_r"}), ["thigh_r", "calf_r"])

    def test_every_bone_under_a_body_rides_its_nearest_grouped_ancestor(self):
        parents = {"root": None, "pelvis": "root", "thigh_l": "pelvis", "calf_l": "thigh_l",
                   "calf_twist_01_l": "calf_l", "ik_foot_root": "root", "hand_r": "lowerarm_r",
                   "lowerarm_r": "upperarm_r", "upperarm_r": "clavicle_r",
                   "clavicle_r": "spine_05", "spine_05": "pelvis", "weapon_r": "hand_r"}
        r = plan.riders(parents)
        self.assertEqual(r["calf_twist_01_l"], "calf_l")
        self.assertEqual(r["weapon_r"], "hand_r")
        self.assertEqual(r["clavicle_r"], "spine_hi")
        self.assertNotIn("root", r)
        self.assertNotIn("ik_foot_root", r)

    def test_the_body_frame_runs_down_its_axis(self):
        worlds = {"thigh_l": at(np.identity(3), (10, 90, 0)),
                  "calf_l": at(np.identity(3), (10, 50, 0))}
        f = plan.body_frame("thigh_l", worlds)
        np.testing.assert_allclose(plan.rot(f)[0], [0, -1, 0], atol=1e-9)
        np.testing.assert_allclose(plan.pos(f), [10, 70, 0], atol=1e-9)

    def test_a_hand_without_a_middle_finger_carries_on_its_forearm(self):
        worlds = {"lowerarm_l": at(np.identity(3), (0, 0, 0)),
                  "hand_l": at(np.identity(3), (20, 0, 0))}
        a, b = plan.axis_points("hand_l", worlds)
        np.testing.assert_allclose(b, [20 + 20 * plan.HAND_FALLBACK, 0, 0])


class Shapes(unittest.TestCase):

    def test_capsule_length_runs_tip_to_tip_half_a_radius_past_each_end(self):
        self.assertEqual(plan.capsule_length(30.0, 6.0), 36.0)

    def test_radius_is_the_median_distance_of_the_skin_from_the_segment(self):
        a, b = np.zeros(3), np.array([0.0, 40.0, 0.0])
        pts = [(r, y, 0) for r in (4, 5, 6) for y in range(0, 41, 5)]
        self.assertAlmostEqual(plan.radius(pts, a, b, 40.0), 5.0)
        self.assertAlmostEqual(plan.radius(None, a, b, 40.0), 40.0 * plan.RADIUS_SHARE)

    def test_the_floor_is_the_lowest_sole_else_the_capsules(self):
        self.assertEqual(plan.floor_height([np.array([[0, 3, 0], [0, -1, 0]]), None], []), -1.0)
        caps = [(np.array([0, 10, 0]), np.array([0, 4, 0]), 3.0)]
        self.assertEqual(plan.floor_height([None, None], caps), 1.0)


class Joints(unittest.TestCase):

    def test_a_bent_knee_flexes_about_the_plane_s_normal(self):
        down = np.array([0.0, -1.0, 0.0])
        back = np.array([0.0, -1.0, -1.0]) / math.sqrt(2)
        axis, bend = plan.hinge_axis("knee", down, back, np.array([0, 0, 1.0]))
        self.assertAlmostEqual(bend, 45.0, places=6)
        # a positive turn about the axis takes the thigh's direction toward the shin's
        moved = down @ turn(axis, 45.0)
        np.testing.assert_allclose(moved, back, atol=1e-9)

    def test_a_straight_knee_flexes_the_shin_backward_a_straight_elbow_forward(self):
        down = np.array([0.0, -1.0, 0.0])
        fwd = np.array([0.0, 0.0, 1.0])
        knee, _ = plan.hinge_axis("knee", down, down, fwd)
        elbow, _ = plan.hinge_axis("elbow", down, down, fwd)
        self.assertLess((down @ turn(knee, 30.0))[2], 0)          # the shin goes back
        self.assertGreater((down @ turn(elbow, 30.0))[2], 0)      # the forearm goes forward

    def test_hinge_limits_run_from_straight_to_the_whole_flexion(self):
        down = np.array([0.0, -1.0, 0.0])
        bent = down @ turn((1, 0, 0), -40.0)
        frame, lo, hi = plan.joint_frame("knee", np.zeros(3), down, bent, np.array([0, 0, 1.0]),
                                         np.array([0, 0, 1.0]))
        self.assertAlmostEqual(lo[0], -40.0 - plan.HINGE_SLACK, places=6)
        self.assertAlmostEqual(hi[0], plan.HINGE_FLEX - 40.0, places=6)
        self.assertEqual((lo[1], hi[1]), (-plan.HINGE_SIDE, plan.HINGE_SIDE))

    def test_a_ball_twists_about_the_child_and_swings_both_ways(self):
        frame, lo, hi = plan.joint_frame("hip", np.zeros(3), np.array([0, 1.0, 0]),
                                         np.array([0, -1.0, 0]), np.array([0, 0, 1.0]),
                                         np.array([1.0, 0, 0]))
        np.testing.assert_allclose(plan.rot(frame)[0], [0, -1, 0], atol=1e-9)
        self.assertEqual(hi, (30.0, 70.0, 70.0))
        self.assertEqual(lo, (-30.0, -70.0, -70.0))

    def test_muscles_hold_then_let_go(self):
        self.assertEqual(plan.fade_keys(10, 8, 5.0), [(10, 5.0), (18, 0.0)])
        self.assertEqual(plan.fade_keys(10, 0, 5.0), [(10, 0.0)])
        self.assertAlmostEqual(plan.stiffness(1.0, 5.0, 25.0), plan.MUSCLE_GAIN * 5 * plan.G * 25)


class Start(unittest.TestCase):

    def test_velocities_are_cm_and_degrees_a_second_in_world_axes(self):
        before = at(np.identity(3), (0, 0, 0))
        now = at(turn((0, 1, 0), 3.0), (2, 0, 0))
        v, w = plan.velocities(before, now, 30.0)
        np.testing.assert_allclose(v, [60, 0, 0], atol=1e-9)
        np.testing.assert_allclose(w, [0, 90, 0], atol=1e-6)

    def test_the_spin_is_about_the_world_axis_whatever_the_body_s_own_turn(self):
        start = turn((1, 0, 0), 70.0)
        before = at(start, (0, 0, 0))
        now = at(start @ turn((0, 0, 1), 6.0), (0, 0, 0))
        _v, w = plan.velocities(before, now, 24.0)
        np.testing.assert_allclose(w, [0, 0, 144], atol=1e-6)


class Bake(unittest.TestCase):

    def test_a_riding_bone_keeps_its_place_in_its_body(self):
        body0 = at(turn((0, 0, 1), 20.0), (5, 80, 0))
        hand = at(turn((1, 0, 0), 10.0), (30, 70, 4))
        local = plan.offsets({"hand_r": hand}, {"hand_r": body0}, {"hand_r": "hand_r"})
        moved = at(turn((0, 1, 0), 90.0), (0, 10, 50))
        out = plan.bone_worlds(local, {"hand_r": moved}, {"root": np.identity(4)})
        np.testing.assert_allclose(out["hand_r"], hand @ np.linalg.inv(body0) @ moved, atol=1e-9)
        np.testing.assert_allclose(out["root"], np.identity(4))

    def test_the_span_is_the_highlight_else_the_current_frame_for_its_length(self):
        self.assertEqual(plan.span((10.0, 31.0), 0, 60), (10, 30))
        self.assertEqual(plan.span(None, 12.0, 60), (12, 72))


class Pure(unittest.TestCase):

    def test_plan_imports_nothing_of_maya(self):
        code = ("import sys; sys.path.insert(0, 'SkeldarAnim'); import maya_ragdoll.plan; "
                "print(any(m == 'maya' or m.startswith('maya.') for m in sys.modules))")
        out = subprocess.check_output([sys.executable, "-c", code]).decode().strip()
        self.assertEqual(out, "False")


if __name__ == "__main__":
    unittest.main()
