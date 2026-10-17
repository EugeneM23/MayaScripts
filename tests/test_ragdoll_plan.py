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
        self.assertAlmostEqual(lo[0], -40.0 - plan.HINGE_RANGE["knee"][1], places=6)
        self.assertAlmostEqual(hi[0], plan.HINGE_RANGE["knee"][0] - 40.0, places=6)
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


class Impulses(unittest.TestCase):

    def test_the_nearest_capsule_axis_names_the_body(self):
        axes = {"head": (np.array([0, 160, 0.0]), np.array([0, 175, 0.0])),
                "pelvis": (np.array([0, 90, 0.0]), np.array([0, 100, 0.0]))}
        self.assertEqual(plan.nearest_body((3, 170, 4), axes), "head")
        self.assertEqual(plan.nearest_body((10, 95, 0), axes), "pelvis")

    def test_an_arrow_rides_its_body(self):
        body0 = at(turn((0, 0, 1), 30.0), (0, 100, 0))
        arrow = at(turn((0, 1, 0), 90.0), (5, 110, 2))       # +Z turned onto +X
        tip, d = plan.in_body(arrow, body0)
        moved = at(turn((1, 0, 0), 50.0), (40, 20, 7))
        _j, point = plan.impulse(1.0, 1.0, tip, d, moved)
        expect = (np.append(plan.pos(arrow), 1) @ np.linalg.inv(body0) @ moved)[:3]
        np.testing.assert_allclose(point + plan.pos(moved), expect, atol=1e-9)

    def test_the_impulse_is_mass_times_speed_along_the_arrow_in_world(self):
        body = at(turn((0, 1, 0), 90.0), (10, 50, 0))
        j, point = plan.impulse(4.0, 3.0, (0, 0, 0), (1, 0, 0), body)
        np.testing.assert_allclose(j, np.array([1, 0, 0]) @ turn((0, 1, 0), 90.0) * 1200, atol=1e-9)
        np.testing.assert_allclose(point, [0, 0, 0], atol=1e-9)

    def test_a_hit_before_the_fall_lands_on_its_first_step_after_it_none(self):
        self.assertEqual(plan.hit_frame(2, 10, 40), 11)
        self.assertEqual(plan.hit_frame(10, 10, 40), 11)
        self.assertEqual(plan.hit_frame(25.4, 10, 40), 25)
        self.assertEqual(plan.hit_frame(40, 10, 40), 40)
        self.assertIsNone(plan.hit_frame(41, 10, 40))


LEFT, UP, FWD = np.array([1.0, 0, 0]), np.array([0, 1.0, 0]), np.array([0, 0, 1.0])
FACING = (LEFT, UP, FWD)


def body(direction, point=(0, 0, 0)):
    """A body frame running down `direction`."""
    x = plan._unit(direction)
    y = plan.perpendicular(x, FWD)
    return at(np.array([x, y, np.cross(x, y)]), point)


class Anatomy(unittest.TestCase):

    def test_a_positive_turn_about_z_flexes_and_about_y_moves_toward_the_left(self):
        rows = plan.anatomical_frame("hip", "thigh_l", FACING, -UP)
        np.testing.assert_allclose(rows[0], -UP, atol=1e-9)
        down = -UP
        self.assertGreater((down @ turn(rows[2], 30.0))[2], 0.4)    # flexion: the knee forward
        self.assertGreater((down @ turn(rows[1], 30.0))[0], 0.4)    # Y: toward +X, the left
        np.testing.assert_allclose(np.cross(rows[0], rows[1]), rows[2], atol=1e-9)

    def test_the_foot_s_neutral_is_forward_and_plantarflexion_is_positive(self):
        rows = plan.anatomical_frame("ankle", "foot_l", FACING, -UP)
        np.testing.assert_allclose(rows[0], FWD, atol=1e-9)
        self.assertLess((FWD @ turn(rows[2], 30.0))[1], -0.4)       # toes down

    def test_euler_reads_one_axis_as_its_angle(self):
        for axis, index in ((LEFT, 0), (UP, 1), (FWD, 2)):
            col = turn(axis, 25.0).T
            angles = plan.euler_xyz(col)
            self.assertAlmostEqual(angles[index], 25.0, places=6)
            self.assertAlmostEqual(float(np.abs(np.delete(angles, index)).max()), 0.0, places=6)

    def test_turn_between_takes_one_direction_onto_another(self):
        a, b = np.array([0, -1.0, 0]), plan._unit(np.array([1.0, -1.0, 0.3]))
        np.testing.assert_allclose(a @ plan.turn_between(a, b), b, atol=1e-9)
        np.testing.assert_allclose(a @ plan.turn_between(a, -a), -a, atol=1e-9)

    def _arm(self, key, out, now=None):
        """A shoulder joint: the chest upright, the arm resting `out` (an A pose) and now `now`."""
        chest = body(UP)
        rest = (chest, body(out), UP, out)
        arm_now = body(now if now is not None else out)
        return plan.anatomical_joint("shoulder", key, np.zeros(3), rest, (chest, arm_now),
                                     FACING)

    def assertInsideCone(self, kind, key, offset, lo, hi, twist_too=True):
        """Every corner and every end of Bullet's box keeps inside the joint's cone (the twist read
        only where the swing stays moderate: past ~120 degrees of swing a twist means little)."""
        for x in (lo[0], 0.0, hi[0]):
            for y in (lo[1], 0.0, hi[1]):
                for z in (lo[2], 0.0, hi[2]):
                    turn = offset @ plan.axis_turn(2, z) @ plan.axis_turn(1, y) @                         plan.axis_turn(0, x)
                    swing, twist = plan.cone_excess(kind, key, turn, offset)
                    self.assertLessEqual(swing, plan.CONE_SLACK + 1e-6, (x, y, z))
                    if twist_too:
                        self.assertLessEqual(twist, 25.0, (x, y, z))   # see _inside_cone

    def test_a_limb_hanging_at_neutral_reads_no_offset(self):
        frame, lo, hi, off = self._arm("upperarm_l", -UP)
        np.testing.assert_allclose(off, 0.0, atol=1e-9)
        self.assertEqual((lo[0], hi[0]), (-80.0, 80.0))               # the twist whole
        self.assertGreater(hi[2], 90.0)                                 # the arm swings far up
        self.assertInsideCone("shoulder", "upperarm_l", np.identity(3), lo, hi, twist_too=False)
        np.testing.assert_allclose(plan.rot(frame)[0], -UP, atol=1e-9)  # X down the arm

    def test_an_a_pose_arm_reads_its_abduction_mirrored_by_side(self):
        out_l = plan._unit(-UP + LEFT)
        out_r = plan._unit(-UP - LEFT)
        _f, lo_l, hi_l, off_l = self._arm("upperarm_l", out_l)
        _f, lo_r, hi_r, off_r = self._arm("upperarm_r", out_r)
        self.assertAlmostEqual(off_l[1], 45.0, places=4)            # toward +X: the left one's out
        self.assertAlmostEqual(off_r[1], -45.0, places=4)
        for axis in (0, 1):                                           # twist and side mirror,
            self.assertAlmostEqual(lo_l[axis], -hi_r[axis], delta=1.0)  # flexion does not
            self.assertAlmostEqual(hi_l[axis], -lo_r[axis], delta=1.0)
        self.assertAlmostEqual(lo_l[2], lo_r[2], delta=1.0)
        self.assertAlmostEqual(hi_l[2], hi_r[2], delta=1.0)

    def test_a_flexed_hip_has_less_flexion_left_and_more_extension(self):
        thigh_rest = (body(UP), body(-UP), UP, -UP)
        bent = plan._unit(-UP + FWD)                                 # 45 forward
        _f, lo, hi, off = plan.anatomical_joint("hip", "thigh_l", np.zeros(3), thigh_rest,
                                                (body(UP), body(bent)), FACING)
        self.assertAlmostEqual(off[2], 45.0, places=4)
        self.assertLessEqual(hi[2], 120.0 - 45.0)                     # flexion left: 75 at most
        self.assertGreater(hi[2], 30.0)
        self.assertLess(lo[2], -60.0)                                  # 30 of extension past neutral

    def test_a_pose_past_its_range_is_never_snapped_back(self):
        off = plan.axis_turn(2, 140.0)
        lo, hi = plan.anatomical_limits("hip", "thigh_l", off)
        self.assertEqual(hi[2], plan.LIMIT_GRACE)
        self.assertLess(lo[2], -100.0)

    def test_maya_s_bullet_composes_z_y_x(self):
        m = plan.axis_turn(2, 10.0) @ plan.axis_turn(1, 20.0) @ plan.axis_turn(0, 30.0)
        np.testing.assert_allclose(plan.euler_xyz(m), (30.0, 20.0, 10.0), atol=1e-9)

    def test_a_twist_of_bullet_s_is_a_twist_of_the_limb(self):
        off = plan.axis_turn(2, 30.0) @ plan.axis_turn(1, 15.0)       # a bent wrist
        sy, sz, tw = plan.swing_twist(off)
        sy2, sz2, tw2 = plan.swing_twist(off @ plan.axis_turn(0, 50.0))
        self.assertAlmostEqual(sy, sy2, places=6)
        self.assertAlmostEqual(sz, sz2, places=6)
        self.assertAlmostEqual(tw2 - tw, 50.0, places=6)

    def test_limits_keep_a_bent_twisted_joint_inside_its_cone(self):
        off = plan.axis_turn(2, 30.0) @ plan.axis_turn(0, 40.0)       # flexed and twisted
        lo, hi = plan.anatomical_limits("hip", "thigh_l", off)
        self.assertInsideCone("hip", "thigh_l", off, lo, hi)
        lo, hi = plan.anatomical_limits("wrist", "hand_r", off)
        self.assertInsideCone("wrist", "hand_r", off, lo, hi)

    def test_swing_twist_reads_a_pure_flexion(self):
        sy, sz, tw = plan.swing_twist(plan.axis_turn(2, 70.0))
        self.assertAlmostEqual(sz, 70.0, places=6)
        self.assertAlmostEqual(sy, 0.0, places=6)
        self.assertAlmostEqual(tw, 0.0, places=6)
        self.assertEqual(plan.cone_excess("hip", "thigh_l", plan.axis_turn(2, 70.0)), (0.0, 0.0))
        self.assertAlmostEqual(plan.cone_excess("hip", "thigh_l", plan.axis_turn(2, 130.0))[0],
                               10.0, places=6)

    def test_hinges_take_their_own_range(self):
        down = np.array([0.0, -1.0, 0.0])
        _f, lo, hi = plan.joint_frame("knee", np.zeros(3), down, down, FWD, FWD)
        self.assertAlmostEqual(hi[0], plan.HINGE_RANGE["knee"][0], places=6)
        _f, lo, hi = plan.joint_frame("elbow", np.zeros(3), down, down, FWD, FWD)
        self.assertAlmostEqual(lo[0], -plan.HINGE_RANGE["elbow"][1], places=6)


class SelfCollision(unittest.TestCase):

    def _standing(self):
        """Axes and radii of a man standing at attention, arms out a little."""
        P = lambda *v: np.array(v, dtype=float)                          # noqa: E731
        axes = {
            "pelvis": (P(10, 95, 0), P(-10, 95, 0)), "spine_lo": (P(0, 100, 0), P(0, 120, 0)),
            "spine_hi": (P(0, 120, 0), P(0, 150, 0)), "head": (P(0, 150, 0), P(0, 175, 0))}
        for s, x in (("l", 1), ("r", -1)):
            axes.update({
                "upperarm_" + s: (P(18 * x, 145, 0), P(30 * x, 118, 0)),
                "lowerarm_" + s: (P(30 * x, 118, 0), P(38 * x, 92, 0)),
                "hand_" + s: (P(38 * x, 92, 0), P(40 * x, 75, 0)),
                "thigh_" + s: (P(10 * x, 92, 0), P(11 * x, 50, 0)),
                "calf_" + s: (P(11 * x, 50, 0), P(11 * x, 9, 0)),
                "foot_" + s: (P(11 * x, 9, 0), P(11 * x, 3, 15))})
        radii = dict((k, 6.0) for k in axes)
        radii.update({"spine_lo": 13.0, "spine_hi": 15.0, "pelvis": 12.0, "head": 9.0})
        return axes, radii

    def test_every_group_bit_fits_maya_s_sixteen_bits(self):
        self.assertLess(plan.WEAPON_BIT, 1 << 15)
        self.assertLess(plan.world_mask(), 1 << 15)

    def test_a_limb_collides_with_the_body_but_not_with_its_jointed_neighbours(self):
        axes, radii = self._standing()
        filters, apart = plan.collision_filters(axes, radii)
        g_hand, m_hand = filters["hand_l"]
        g_chest, m_chest = filters["spine_hi"]
        self.assertTrue(m_hand & g_chest and m_chest & g_hand)        # a hand meets the chest
        g_leg = filters["calf_r"][0]
        self.assertTrue(filters["calf_l"][1] & g_leg)                  # the legs meet each other
        self.assertFalse(filters["upperarm_l"][1] & g_chest)           # jointed: never
        self.assertFalse(filters["lowerarm_l"][1] & filters["upperarm_l"][0])
        self.assertEqual(filters["hand_l"][0], filters["lowerarm_l"][0])  # one group, the forearm
        self.assertFalse(filters["hand_l"][1] & filters["hand_l"][0])
        self.assertTrue(all(m & plan.WORLD_BIT for _g, m in filters.values()))
        self.assertIn((("pelvis", "thigh_l"), "jointed"), apart)

    def test_bodies_already_deep_in_each_other_are_left_apart(self):
        axes, radii = self._standing()
        axes["hand_l"] = (np.array([10.0, 100.0, 0]), np.array([5.0, 105.0, 0]))   # on the belly
        filters, apart = plan.collision_filters(axes, radii)
        self.assertFalse(filters["hand_l"][1] & filters["spine_lo"][0])
        self.assertTrue(any(pair == ("forearm_l", "spine_lo") and why.startswith("overlap")
                            for pair, why in apart))

    def test_bodies_the_take_brings_together_are_left_apart(self):
        axes, radii = self._standing()
        later = dict(axes)
        later["hand_l"] = (np.array([10.0, 100.0, 0]), np.array([5.0, 105.0, 0]))
        filters, _apart = plan.collision_filters(axes, radii, poses=[later])
        self.assertFalse(filters["hand_l"][1] & filters["spine_lo"][0])
        alone, _apart = plan.collision_filters(axes, radii)
        self.assertTrue(alone["hand_l"][1] & alone["spine_lo"][0])

    def test_segment_distance(self):
        d = plan.segment_distance((0, 0, 0), (10, 0, 0), (5, 3, 0), (5, 8, 0))
        self.assertAlmostEqual(d, 3.0, places=9)
        d = plan.segment_distance((0, 0, 0), (10, 0, 0), (12, 0, 4), (20, 0, 4))
        self.assertAlmostEqual(d, math.hypot(2, 4), places=9)


class Blend(unittest.TestCase):

    def test_every_body_has_a_zone_and_every_zone_a_body(self):
        keys = [row[0] for row in plan.BODIES]
        self.assertEqual(sorted(set(plan.zone_of(k) for k in keys)), sorted(plan.ZONES))
        self.assertEqual(plan.zone_of("hand_l"), "arm_l")
        self.assertEqual(plan.zone_of("foot_r"), "leg_r")
        self.assertEqual(plan.zone_of("spine_hi"), "torso")

    def test_zones_take_what_is_given_and_keep_the_rest(self):
        z = plan.zones({"head": ["free", 0.2], "arm_l": ["bogus", 1.0], "leg_r": "x", "tail": 1})
        self.assertEqual(z["head"], ["free", 0.2])
        self.assertEqual(z["arm_l"], list(plan.PRESETS[plan.DEFAULT_PRESET][1]["arm_l"]))
        self.assertEqual(list(z), list(plan.ZONES))

    def test_presets_cover_every_zone(self):
        for name in plan.PRESETS:
            self.assertEqual(list(plan.preset(name)), list(plan.ZONES))
        self.assertEqual(plan.preset("hit")["leg_l"][0], "anim")

    def test_strength_eases_from_the_take_to_the_zone_and_back(self):
        a, b = 10, 50
        self.assertAlmostEqual(plan.blend_strength(a, a, b, 6, 10, 0.2), 1.0)
        self.assertAlmostEqual(plan.blend_strength(a + 6, a, b, 6, 10, 0.2), 0.2)
        self.assertAlmostEqual(plan.blend_strength(30, a, b, 6, 10, 0.2), 0.2)
        self.assertAlmostEqual(plan.blend_strength(b, a, b, 6, 10, 0.2), 1.0)
        mid = plan.blend_strength(a + 3, a, b, 6, 10, 0.2)
        self.assertTrue(0.2 < mid < 1.0)
        self.assertAlmostEqual(plan.blend_strength(a, a, b, 0, 0, 0.0), 0.0)

    def test_the_layer_is_the_take_outside_and_eases_out_at_the_end(self):
        keys = dict(plan.layer_weight_keys(10, 40, 10))
        self.assertEqual(keys[9], 0.0)
        self.assertEqual(keys[10], 1.0)
        self.assertEqual(keys[30], 1.0)
        self.assertEqual(keys[40], 0.0)
        self.assertTrue(0.0 < keys[35] < 1.0)
        none = dict(plan.layer_weight_keys(10, 40, 0))
        self.assertEqual((none[40], none[41]), (1.0, 0.0))

    def test_the_servo_takes_its_share_of_the_way(self):
        before = at(np.identity(3), (0, 100, 0))
        now = at(np.identity(3), (2, 100, 0))           # moving 2 cm a frame along X
        target = at(turn((0, 1, 0), 30), (10, 100, 0))
        inertia = plan.capsule_inertia(5.0, 30.0, 5.0)
        j, torque = plan.servo(before, now, target, 30.0, 1.0, 5.0, inertia, gravity=0.0)
        self.assertTrue(np.allclose(j, [5.0 * (8 - 2) * 30.0, 0, 0]))
        spin = math.radians(30.0) * 30.0
        self.assertTrue(np.allclose(np.abs(torque), [0, inertia[2] * spin, 0]))
        half, _ = plan.servo(before, now, target, 30.0, 0.5, 5.0, inertia, gravity=0.0)
        self.assertTrue(np.allclose(half, j * 0.5))
        none = plan.servo(before, now, target, 30.0, 0.0, 5.0, inertia)
        self.assertFalse(np.any(none[0]) or np.any(none[1]))

    def test_the_servo_pays_for_gravity_over_the_frame(self):
        still = at(np.identity(3), (0, 100, 0))
        j, _t = plan.servo(still, still, still, 30.0, 1.0, 2.0, (1, 1, 1))
        self.assertAlmostEqual(j[1], 2.0 * plan.G / 30.0)

    def test_bullet_s_capsule_inertia_is_a_box_s(self):
        along, across, _ = plan.capsule_inertia(5.0, 30.0, 5.0)
        self.assertAlmostEqual(across, 416.6666, places=3)
        self.assertAlmostEqual(along, 5.0 / 12.0 * 200.0)

    def test_a_hit_off_centre_turns(self):
        self.assertTrue(np.allclose(plan.hit_torque((0, 10, 0), (100, 0, 0)), [0, 0, -1000]))

    def test_the_soles_follow_their_foot(self):
        foot = at(np.identity(3), (0, 10, 0))
        pts = np.array([[0, 2, 5], [0, 4, -5]])
        lifted = at(np.identity(3), (0, 30, 0))
        self.assertEqual(plan.sole_heights(pts, foot, [foot, lifted]), [2.0, 22.0])
        self.assertEqual(plan.sole_heights(None, foot, [foot]), [])

    def test_a_bone_is_carried_by_its_body_s_change(self):
        bone = at(turn((0, 1, 0), 30), (1, 2, 3))
        body = at(turn((1, 0, 0), 10), (0, 1, 0))
        self.assertTrue(np.allclose(plan.carried_by(bone, body, body), bone))
        moved = at(turn((0, 0, 1), 20), (5, 1, 0))
        out = plan.carried_by(bone, body, moved)
        self.assertTrue(np.allclose(out @ np.linalg.inv(moved), bone @ np.linalg.inv(body)))

    def test_zone_strengths_stop_at_one(self):
        self.assertEqual(plan.zones({"head": ["follow", 1.7]})["head"], ["follow", 1.0])

    def test_planted_legs_hold_the_pelvis(self):
        keys = [row[0] for row in plan.BODIES]
        state, strength = plan.body_states(dict(plan.preset("hit")), keys)
        self.assertEqual((state["pelvis"], strength["pelvis"]), ("anim", 1.0))
        self.assertEqual(state["spine_lo"], "follow")
        state, _s = plan.body_states(dict(plan.preset("follow")), keys)
        self.assertEqual(state["pelvis"], "follow")

    def test_a_limb_rolls_with_its_bend_plane_and_keeps_it_when_straight(self):
        bent = {"thigh_l": at(turn((0, 1, 0), 80), (10, 90, 0)),     # the bone's own roll: any
                "calf_l": at(np.identity(3), (10, 50, 8)),
                "foot_l": at(np.identity(3), (10, 10, 0))}
        straight = {"thigh_l": at(turn((0, 1, 0), -40), (10, 90, 0)),
                    "calf_l": at(np.identity(3), (10, 50, 0)),
                    "foot_l": at(np.identity(3), (10, 10, 0))}
        keys = ["thigh_l", "calf_l"]
        first, second = plan.blend_bodies([bent, straight], keys)
        normal = np.cross(np.array([0, -40.0, 8]), np.array([0, -40.0, -8]))
        normal /= np.linalg.norm(normal)
        for key in keys:
            self.assertAlmostEqual(abs(float(np.dot(plan.rot(first[key])[1], normal))), 1.0)
        np.testing.assert_allclose(plan.rot(first["thigh_l"])[1], plan.rot(first["calf_l"])[1],
                                   atol=1e-9)
        # straight: no plane, so the roll carries on from the frame before
        self.assertGreater(float(np.dot(plan.rot(second["thigh_l"])[1],
                                        plan.rot(first["thigh_l"])[1])), 0.99)

    def test_a_rigid_joint_gets_the_margin_a_shrug_its_reach(self):
        joint = at(np.identity(3), (0, 100, 0))
        parent = [at(np.identity(3), (0, 90, 0))] * 3
        child = [at(np.identity(3), (0, 110, 0))] * 3
        lo, hi = plan.joint_travel(joint, (0, 100, 0), parent, child, margin=0.5)
        self.assertEqual((lo, hi), ((-0.5,) * 3, (0.5,) * 3))
        child = [at(np.identity(3), (0, 110 + dy, 0)) for dy in (0, 4, -2)]
        lo, hi = plan.joint_travel(joint, (0, 100, 0), parent, child, margin=0.5)
        self.assertAlmostEqual(hi[1], 4.5)
        self.assertAlmostEqual(lo[1], -2.5)

    def test_joint_angles_read_the_take_and_widen_the_limits(self):
        joint = at(np.identity(3), (0, 0, 0))
        parents = [at(np.identity(3), (0, 0, 0))] * 2
        children = [at(np.identity(3), (0, 0, 0)), at(turn((0, 0, 1), 30), (0, 0, 0))]
        angles = plan.joint_angles(joint, parents, children)
        np.testing.assert_allclose(angles[0], [0, 0, 0], atol=1e-9)
        np.testing.assert_allclose(angles[1], [0, 0, 30], atol=1e-6)
        lo, hi = plan.widened((-10, -10, -10), (10, 10, 10), angles, margin=2.0)
        self.assertEqual(lo, (-10.0, -10.0, -10.0))
        self.assertAlmostEqual(hi[2], 32.0)
        lo, hi = plan.widened((0, 0, 0), (0, 0, 0), [(0, 120, 0)], margin=0.0)
        self.assertEqual(hi[1], plan.MIDDLE_MAX)

    def test_a_drift_is_leaned_against(self):
        w = turn((1, 1, 0), 24)
        np.testing.assert_allclose(plan.turn_power(w, 1.0), w, atol=1e-9)
        half = plan.turn_power(w, 0.5)
        np.testing.assert_allclose(half @ half, w, atol=1e-9)
        np.testing.assert_allclose(plan.turn_power(w, -1.0) @ w, np.identity(3), atol=1e-9)
        a, b = at(turn((0, 0, 1), 10), (1, 2, 3)), at(turn((0, 1, 0), 50), (0, 0, 0))
        np.testing.assert_allclose(plan.rot(a) @ plan.world_turn(a, b), plan.rot(b), atol=1e-9)
        target = at(turn((0, 0, 1), 10), (5, 0, 0))
        np.testing.assert_allclose(plan.aimed(target, w, 0.0), target, atol=1e-9)
        np.testing.assert_allclose(plan.rot(plan.aimed(target, w, 1.0)) @ w, plan.rot(target),
                                   atol=1e-9)


class Pure(unittest.TestCase):

    def test_plan_imports_nothing_of_maya(self):
        code = ("import sys; sys.path.insert(0, 'SkeldarAnim'); import maya_ragdoll.plan; "
                "print(any(m == 'maya' or m.startswith('maya.') for m in sys.modules))")
        out = subprocess.check_output([sys.executable, "-c", code]).decode().strip()
        self.assertEqual(out, "False")


if __name__ == "__main__":
    unittest.main()
