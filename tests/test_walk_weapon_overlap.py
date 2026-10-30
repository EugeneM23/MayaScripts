"""Walk Builder's Weapon overlap (2026-10-30): the weapon aimed at its own tip read a few frames earlier,
about its grip, with the hands that hold it carried - the animator's own recipe (the hands IK'd to the
weapon, Tools' Aim target on the tip, the tip's baked animation shifted)."""

import math
import unittest

import numpy as np

from tests.test_walkmodel import load, rot_y, walk, wm

gait = load("gait")
scene = load("scene")

#  a weapon in the right hand of the synthetic walker: its grip a little off the hand's origin, its tip a
#  long blade away (the Long Sword's own 116 cm)
GRIP = (2.0, -3.0, 1.0)
TIP = (2.0, -3.0, 101.0)
WEAPON = {"r": {"grip": GRIP, "tip": TIP}}


def points(local, mats):
    """A local point carried by a cycle of world matrices: (n+1, 3)."""
    local = np.asarray(local, float)
    return np.array([local @ m[:3, :3] + m[3, :3] for m in mats])


def cycle_points(n=8, travel=(0.0, 0.0, 80.0)):
    """A cycle of points (n+1, 3): a circle in place plus a travel, the last frame the first moved by it."""
    per = np.array(travel, float) / float(n)
    out = np.zeros((n + 1, 3))
    for f in range(n + 1):
        a = 360.0 * (f % n) / float(n)
        out[f] = np.array([10.0 * math.cos(math.radians(a)), 3.0 * math.sin(math.radians(a)), 0.0]) + per * f
    return out


class ShiftedPointsTests(unittest.TestCase):
    """The place half of shifted_cycle: the tip's own path read a lag earlier."""

    def test_no_lag_gives_the_input_back(self):
        pts = cycle_points()
        self.assertTrue(np.array_equal(wm.shifted_points(pts, 0.0), pts))

    def test_a_whole_lag_is_the_point_that_many_frames_earlier(self):
        pts, n = cycle_points(), 8
        per = (pts[n] - pts[0]) / float(n)
        got = wm.shifted_points(pts, 2.0)
        for f in range(n + 1):
            was = (f - 2) % n
            self.assertTrue(np.allclose(got[f] - per * f, pts[was] - per * was, atol=1e-9), f)

    def test_a_fractional_lag_falls_between_the_two_frames(self):
        pts = cycle_points()
        half = wm.shifted_points(pts, 2.5)
        early, late = wm.shifted_points(pts, 3.0), wm.shifted_points(pts, 2.0)
        self.assertTrue(np.allclose(half[4], 0.5 * (early[4] + late[4]), atol=1e-9))

    def test_the_result_is_a_cycle_again(self):
        pts, n = cycle_points(), 8
        travel = pts[n] - pts[0]
        for lag in (1.0, 2.5, -3.0):
            got = wm.shifted_points(pts, lag)
            self.assertTrue(np.allclose(got[n] - got[0], travel, atol=1e-9), lag)

    def test_it_agrees_with_shifted_cycle_s_own_places(self):
        """One rule for both: the matrices' places shifted are the points shifted."""
        mats = np.tile(np.eye(4), (9, 1, 1))
        pts = cycle_points()
        for f in range(9):
            mats[f, :3, :3] = rot_y(40.0 * f)
            mats[f, 3, :3] = pts[f]
        for lag in (1.0, 2.5, -3.0):
            self.assertTrue(np.allclose(wm.shifted_cycle(mats, lag)[:, 3, :3], wm.shifted_points(pts, lag),
                                        atol=1e-9), lag)


class AimSwingTests(unittest.TestCase):
    """The minimal swing (no twist) and the world turn about a point it is applied as."""

    def test_the_swing_takes_one_direction_onto_the_other(self):
        a, b = wm._unit(np.array([1.0, 0.2, -0.3])), wm._unit(np.array([0.1, 1.0, 0.4]))
        s = wm.aim_swing(a, b)
        self.assertTrue(np.allclose(a @ s, b, atol=1e-12))
        self.assertAlmostEqual(float(np.linalg.det(s)), 1.0, places=12)

    def test_the_same_direction_is_the_identity(self):
        a = wm._unit(np.array([0.0, 0.0, 1.0]))
        self.assertTrue(np.array_equal(wm.aim_swing(a, a), np.eye(3)))

    def test_it_adds_no_twist_about_the_blade(self):
        """A minimal swing: anything along the axis of the turn is left alone, and the turn is the angle
        between the two directions - never more."""
        a, b = wm._unit(np.array([1.0, 0.0, 0.0])), wm._unit(np.array([0.0, 1.0, 0.0]))
        s = wm.aim_swing(a, b)
        angle = float(np.linalg.norm(wm.log_rot(s)))
        self.assertAlmostEqual(math.degrees(angle), 90.0, places=9)
        self.assertTrue(np.allclose(np.array([0.0, 0.0, 1.0]) @ s, [0.0, 0.0, 1.0], atol=1e-12))

    def test_a_direction_turned_right_round_still_answers_a_rotation(self):
        a = wm._unit(np.array([0.0, 0.0, 1.0]))
        s = wm.aim_swing(a, -a)
        self.assertTrue(np.allclose(a @ s, -a, atol=1e-9))
        self.assertAlmostEqual(float(np.linalg.det(s)), 1.0, places=9)

    def test_too_short_a_vector_is_the_identity(self):
        a = np.array([0.0, 0.0, 1.0])
        self.assertTrue(np.array_equal(wm.aim_swing(a, np.zeros(3)), np.eye(3)))

    def test_swung_about_holds_its_own_point_and_turns_the_rest(self):
        o = np.array([3.0, -4.0, 5.0])
        s = wm.aim_swing(wm._unit(np.array([1.0, 0.0, 0.0])), wm._unit(np.array([0.0, 0.0, 1.0])))
        m = wm.swung_about(o, s)
        self.assertTrue(np.allclose(o @ m[:3, :3] + m[3, :3], o, atol=1e-12))
        p = o + np.array([10.0, 0.0, 0.0])
        self.assertTrue(np.allclose(p @ m[:3, :3] + m[3, :3], o + np.array([0.0, 0.0, 10.0]), atol=1e-12))


class KnobTests(unittest.TestCase):

    def test_the_engine_carries_a_sided_weapon_overlap_knob(self):
        self.assertEqual(wm.DEFAULTS["weapon_overlap"], 0.0)
        self.assertEqual(wm.RANGES["weapon_overlap"], (-120.0, 120.0))
        self.assertIn("weapon_overlap", wm.SIDED)
        self.assertEqual(wm.SIDE_KNOBS["weapon_overlap_l"], "weapon_overlap")
        self.assertIn("weapon_overlap", wm.ENGINE_ONLY)
        k = wm.knobs(weapon_overlap_l=3.0)
        self.assertEqual(wm.sided(k)["l"]["weapon_overlap"], 3.0)
        self.assertEqual(wm.sided(k)["r"]["weapon_overlap"], 0.0)

    def test_the_parameter_is_one_slider_of_its_own_tab(self):
        p = gait.P["weapon_overlap"]
        self.assertEqual((p.group, p.label, p.unit, p.kind, p.sided), (gait.WEAPON, "Weapon overlap", "ms",
                                                                       "added", True))
        self.assertEqual(p.default, 0.0)
        self.assertIn(gait.WEAPON, gait.GROUPS)
        self.assertEqual(gait.GROUP_LABELS[gait.WEAPON], "Weapon")
        self.assertEqual([q.name for q in gait.PARAMS if q.group == gait.WEAPON], ["weapon_overlap"])

    def test_milliseconds_become_frames_of_the_new_cycle(self):
        w = walk()
        own = gait.own(w)
        vals = dict((k, v) for k, v in own.items())
        vals["weapon_overlap"] = 150.0
        vals["weapon_overlap_l"] = vals["weapon_overlap_r"] = 150.0
        for fps, want in ((30.0, 4.5), (24.0, 3.6)):
            e = gait.engine_knobs(w, own, vals, fps_out=fps)
            self.assertAlmostEqual(e["weapon_overlap_r"], want, places=9, msg=fps)
            self.assertAlmostEqual(e["weapon_overlap_l"], want, places=9, msg=fps)

    def test_the_slider_reaches_half_the_cycle_either_way(self):
        w = walk()
        rng = gait.ranges(gait.own(w), 80.0, w)
        cap = gait.overlap_cap(w)
        for key in ("weapon_overlap", "weapon_overlap_l", "weapon_overlap_r"):
            self.assertEqual(rng[key], (-cap, cap), key)


class SwingTests(unittest.TestCase):
    """_weapon_swing itself, with no IK under it: the geometry of the aim, exact."""

    def setUp(self):
        self.w = walk()
        self.r = self.w.evaluate({"balance": 0.0, "arm_drag": 0.0})
        self.kin = np.array(self.r.worlds)
        self.n = self.r.frames
        self.chains = self.w._arm_chains()

    def swing(self, lag, weapons=WEAPON, grip=False, hands=None):
        hands = dict(hands or {})
        held = dict((s, weapons[s]) for s in weapons if s in self.chains)
        swings = dict((s, lag) for s in held)
        moved = self.w._weapon_swing(self.kin, self.n, self.chains, hands, swings, held, grip)
        return hands, moved

    def test_the_blade_aims_at_its_own_tip_that_many_frames_earlier_and_holds_its_grip(self):
        """The gate: the grip is held exactly, the blade keeps its length, and it points at where the tip
        was `lag` frames ago - the travel taken out, as the animator's shifted tip animation."""
        lag = 3.0
        hand_j = self.chains["r"][-1]
        before = np.array(self.kin[hand_j])
        hands, moved = self.swing(lag)
        o_before, t_before = points(GRIP, before), points(TIP, before)
        want = wm.shifted_points(t_before, lag)
        o_after, t_after = points(GRIP, hands["r"]), points(TIP, hands["r"])
        for f in range(self.n + 1):
            self.assertTrue(np.allclose(o_after[f], o_before[f], atol=1e-10), f)
            self.assertAlmostEqual(float(np.linalg.norm(t_after[f] - o_after[f])),
                                   float(np.linalg.norm(t_before[f] - o_before[f])), places=9, msg=f)
            d, aim = wm._unit(t_after[f] - o_after[f]), wm._unit(want[f] - o_before[f])
            self.assertLess(math.degrees(math.acos(min(1.0, abs(float(np.dot(d, aim)))))), 1e-4, f)
        self.assertGreater(moved, 1.0)
        self.assertAlmostEqual(moved, max(float(np.linalg.norm(t_after[f] - t_before[f]))
                                          for f in range(self.n + 1)), places=9)

    def test_a_lag_of_nothing_moves_nothing(self):
        hands, moved = self.swing(0.0)
        self.assertEqual(moved, 0.0)
        self.assertTrue(np.array_equal(hands["r"], self.kin[self.chains["r"][-1]]))

    def test_the_other_hand_is_left_alone_with_no_grip(self):
        hands, _ = self.swing(3.0)
        self.assertEqual(sorted(hands), ["r"])

    def test_a_two_handed_grip_carries_the_other_hand_and_keeps_its_hold(self):
        hand_r, hand_l = self.chains["r"][-1], self.chains["l"][-1]
        hands, _ = self.swing(3.0, grip=True)
        self.assertEqual(sorted(hands), ["l", "r"])
        weapon = lambda m: wm.matrix(m[:3, :3], GRIP @ m[:3, :3] + m[3, :3])
        moved = 0.0
        for f in range(self.n + 1):
            was = np.array(self.kin[hand_l, f]) @ np.linalg.inv(weapon(self.kin[hand_r, f]))
            now = hands["l"][f] @ np.linalg.inv(weapon(hands["r"][f]))
            self.assertTrue(np.allclose(now, was, atol=1e-9), f)
            moved = max(moved, float(np.linalg.norm(hands["l"][f, 3, :3] - self.kin[hand_l, f, 3, :3])))
        self.assertGreater(moved, 0.5)

    def test_a_weapon_in_each_hand_is_swung_about_its_own_grip(self):
        both = {"r": {"grip": GRIP, "tip": TIP}, "l": {"grip": GRIP, "tip": TIP}}
        hands, _ = self.swing(3.0, weapons=both)
        self.assertEqual(sorted(hands), ["l", "r"])
        for side in ("l", "r"):
            hand_j = self.chains[side][-1]
            self.assertTrue(np.allclose(points(GRIP, hands[side]), points(GRIP, np.array(self.kin[hand_j])),
                                        atol=1e-10), side)
            turned = max(float(np.linalg.norm(wm.log_rot(np.array(self.kin[hand_j, f, :3, :3]).T
                                                         @ hands[side][f][:3, :3]))) for f in range(self.n + 1))
            self.assertGreater(math.degrees(turned), 1.0, side)

    def test_it_swings_the_hands_the_other_knobs_already_moved(self):
        """The aim is read off the assembly as it stands, so a hand Arm overlap has moved is swung from
        there and its grip stays where that knob put it."""
        hand_j = self.chains["r"][-1]
        late = wm.shifted_cycle(self.kin[hand_j], 2.0)
        hands, _ = self.swing(3.0, hands={"r": np.array(late)})
        o_late, o_after = points(GRIP, late), points(GRIP, hands["r"])
        self.assertTrue(np.allclose(o_after, o_late, atol=1e-10))
        want = wm.shifted_points(points(TIP, late), 3.0)
        t_after = points(TIP, hands["r"])
        for f in range(self.n + 1):
            d, aim = wm._unit(t_after[f] - o_after[f]), wm._unit(want[f] - o_late[f])
            self.assertLess(math.degrees(math.acos(min(1.0, abs(float(np.dot(d, aim)))))), 1e-4, f)


class PassTests(unittest.TestCase):
    """The whole pass through evaluate: the walker's arms rebuilt to the swung weapon.

    Every run bends the elbows (`elbow_add`, the cascade tests' own reason): the walker's arm hangs
    98.8 .. 100.0 % extended, and an arm at full stretch cannot follow a weapon whose grip stands off the
    hand - two_bone clamps the hand on its line and the grip gives by a couple of millimetres. Bent, the
    arm reaches what the swing asks and the aim is exact."""

    BENT = 70.0       # deg: the elbows bent, so the arm is 72 .. 81 % extended and can follow its hand

    def setUp(self):
        self.w = walk()
        self.base = self.run_knob(0.0)
        self.n = self.base.frames
        self.chains = self.w._arm_chains()
        self.hand_r = self.chains["r"][-1]
        self.hand_l = self.chains["l"][-1]

    def run_knob(self, lag, pose=None, weapons=WEAPON, share=None, **more):
        #  the springs off: with Whip on, the arms' inertia moves the hands too and the geometry of the
        #  swing alone cannot be read (the drags default to 1.5)
        knobs = dict({"balance": 0.0, "arm_drag": 0.0, "elbow_add": self.BENT}, weapon_overlap=lag, **more)
        if share is not None:
            knobs["pose"] = share
        return self.w.evaluate(knobs, pose=pose, weapons=weapons)


    def test_a_lag_of_nothing_is_the_walk_with_no_weapon_at_all(self):
        plain = self.run_knob(0.0, weapons=None)
        self.assertTrue(np.array_equal(self.run_knob(0.0).worlds, plain.worlds))
        self.assertEqual(self.base.info["arms"]["overlap"]["weapon"], 0.0)
        self.assertEqual(self.base.info["arms"]["overlap"]["weapon_sides"], [])

    def test_a_lag_with_no_weapon_in_the_hands_changes_nothing(self):
        plain = self.run_knob(0.0, weapons=None)
        got = self.run_knob(3.0, weapons=None)
        self.assertTrue(np.array_equal(got.worlds, plain.worlds))
        self.assertEqual(got.info["arms"]["overlap"]["weapon"], 0.0)
        self.assertEqual(got.info["arms"]["overlap"]["weapon_sides"], [])

    def aims_at(self, lag):
        """The run at `lag`: the grip held, the blade's length kept and the blade aimed at the tip's own path
        that many frames away. Returns the most the tip moved."""
        got = self.run_knob(lag)
        before, after = np.array(self.base.worlds[self.hand_r]), np.array(got.worlds[self.hand_r])
        o_before, t_before = points(GRIP, before), points(TIP, before)
        want = wm.shifted_points(t_before, lag)
        o_after, t_after = points(GRIP, after), points(TIP, after)
        moved = 0.0
        for f in range(self.n + 1):
            self.assertTrue(np.allclose(o_after[f], o_before[f], atol=1e-6), (lag, f))   # the grip is held
            self.assertAlmostEqual(float(np.linalg.norm(t_after[f] - o_after[f])),
                                   float(np.linalg.norm(t_before[f] - o_before[f])), places=6, msg=(lag, f))
            d, aim = wm._unit(t_after[f] - o_after[f]), wm._unit(want[f] - o_before[f])
            self.assertLess(math.degrees(math.acos(min(1.0, abs(float(np.dot(d, aim)))))), 1e-3, (lag, f))
            moved = max(moved, float(np.linalg.norm(t_after[f] - t_before[f])))
        return moved

    def test_the_blade_points_at_its_own_tip_that_many_frames_earlier(self):
        """End to end: the arm rebuilt to the swung hand still holds the grip and aims the blade where the
        tip was `lag` frames ago."""
        self.assertGreater(self.aims_at(3.0), 1.0)          # it really swung the blade

    def test_a_lead_aims_at_the_tip_the_other_way_round(self):
        """A negative lag is a lead: the blade points at where the tip WILL be, as far the other way. (Not
        measured against the tip's own velocity: the tip runs a loop, so three frames along a reversal is
        not three frames along the way it is going at that instant.)"""
        self.assertGreater(self.aims_at(-3.0), 1.0)
        late = points(TIP, np.array(self.run_knob(3.0).worlds[self.hand_r]))
        early = points(TIP, np.array(self.run_knob(-3.0).worlds[self.hand_r]))
        self.assertGreater(float(np.abs(late - early).max()), 1.0)

    def test_the_shoulder_does_not_move_and_the_bones_keep_their_lengths(self):
        got = self.run_knob(4.0)
        up, low, hand = self.chains["r"]
        for f in range(self.n + 1):
            self.assertTrue(np.allclose(got.worlds[up, f, 3, :3], self.base.worlds[up, f, 3, :3], atol=1e-9), f)
            for a, b in ((up, low), (low, hand)):
                was = float(np.linalg.norm(self.base.worlds[b, f, 3, :3] - self.base.worlds[a, f, 3, :3]))
                now = float(np.linalg.norm(got.worlds[b, f, 3, :3] - got.worlds[a, f, 3, :3]))
                self.assertAlmostEqual(now, was, places=6, msg=(f, a, b))

    def test_the_other_arm_is_left_alone_with_no_grip(self):
        got = self.run_knob(4.0)
        for j in self.chains["l"]:
            self.assertTrue(np.allclose(got.worlds[j], self.base.worlds[j], atol=1e-9), j)

    def test_the_cycle_is_still_a_loop(self):
        got = self.run_knob(3.5)
        travel = self.base.worlds[self.hand_r, self.n, 3, :3] - self.base.worlds[self.hand_r, 0, 3, :3]
        self.assertTrue(np.allclose(got.worlds[self.hand_r, self.n, :3, :3],
                                    got.worlds[self.hand_r, 0, :3, :3], atol=1e-9))
        self.assertTrue(np.allclose(got.worlds[self.hand_r, self.n, 3, :3] - got.worlds[self.hand_r, 0, 3, :3],
                                    travel, atol=1e-9))

    def test_a_two_handed_grip_carries_the_other_hand_and_keeps_its_hold(self):
        pose = {"grip": True, "weapons": {}}
        base = self.run_knob(0.0, pose=pose, share=1.0)
        got = self.run_knob(3.0, pose=pose, share=1.0)
        weapon = lambda r, f: wm.matrix(*(lambda m: (m[:3, :3], GRIP @ m[:3, :3] + m[3, :3]))(
            np.array(r.worlds[self.hand_r, f])))
        moved = 0.0
        for f in range(self.n + 1):
            was = np.array(base.worlds[self.hand_l, f]) @ np.linalg.inv(weapon(base, f))
            now = np.array(got.worlds[self.hand_l, f]) @ np.linalg.inv(weapon(got, f))
            self.assertTrue(np.allclose(now, was, atol=1e-5), f)
            moved = max(moved, float(np.linalg.norm(got.worlds[self.hand_l, f, 3, :3]
                                                    - base.worlds[self.hand_l, f, 3, :3])))
        self.assertGreater(moved, 0.5)          # the other hand really went with the weapon

    def test_it_rides_on_top_of_the_arms_own_lag(self):
        """Arm overlap moves the hand, then the weapon's aim swings the assembly from there: the grip stays
        where Arm overlap put it."""
        lag, w = 2.0, 3.0
        arm = self.run_knob(0.0, arm_overlap=lag)
        both = self.run_knob(w, arm_overlap=lag)
        o_arm = points(GRIP, np.array(arm.worlds[self.hand_r]))
        o_both = points(GRIP, np.array(both.worlds[self.hand_r]))
        self.assertTrue(np.allclose(o_both, o_arm, atol=1e-6))
        want = wm.shifted_points(points(TIP, np.array(arm.worlds[self.hand_r])), w)
        t_both = points(TIP, np.array(both.worlds[self.hand_r]))
        for f in range(self.n + 1):
            d, aim = wm._unit(t_both[f] - o_both[f]), wm._unit(want[f] - o_arm[f])
            self.assertLess(math.degrees(math.acos(min(1.0, abs(float(np.dot(d, aim)))))), 1e-3, f)

    def test_whip_takes_the_swung_arm_as_its_target(self):
        quiet = self.run_knob(0.0, arm_drag=2.0)
        swung = self.run_knob(4.0, arm_drag=2.0)
        moved = max(float(np.linalg.norm(swung.worlds[self.hand_r, f, 3, :3] - quiet.worlds[self.hand_r, f, 3, :3]))
                    for f in range(self.n + 1))
        self.assertGreater(moved, 0.1)

    def test_balance_counts_it(self):
        """The carry balances the swung arms: with no knob of the arms' own set, the weapon's lag alone is
        what makes the balance swing them (moved_arms)."""
        quiet = self.w.evaluate({"arm_drag": 0.0, "weapon_overlap": 0.0}, weapons=WEAPON)
        swung = self.w.evaluate({"arm_drag": 0.0, "weapon_overlap": 5.0}, weapons=WEAPON)
        self.assertNotEqual(float(swung.info["balance"]["carry"]), float(quiet.info["balance"]["carry"]))

    def test_the_info_and_the_line_say_what_it_did(self):
        got = self.run_knob(3.0)
        out = got.info["arms"]["overlap"]
        self.assertAlmostEqual(out["weapon"], 3.0, places=9)
        self.assertEqual(out["weapon_sides"], ["r"])
        self.assertGreater(out["weapon_cm"], 1.0)
        line = wm.describe(got)
        self.assertIn("the weapon trails 3.0 fr", line)
        self.assertIn("cm behind", line)


class ReadingTests(unittest.TestCase):
    """What the scene hands the model (the reading itself runs in a real Maya: verify_walk_weapon_overlap.py)."""

    def test_the_cache_key_names_every_weapon_and_is_stable(self):
        a = {"r": {"grip": (1.0, 2.0, 3.0), "tip": (1.0, 102.0, 3.0)}}
        b = {"r": {"grip": np.array([1.0, 2.0, 3.0]), "tip": np.array([1.0, 102.0, 3.0])}}
        self.assertEqual(scene.weapons_key(a), scene.weapons_key(b))      # a list or an array, one key
        self.assertEqual(scene.weapons_key(None), scene.weapons_key({}))
        self.assertNotEqual(scene.weapons_key(a), scene.weapons_key({}))
        both = dict(a, l={"grip": (0.0, 0.0, 0.0), "tip": (0.0, 50.0, 0.0)})
        self.assertNotEqual(scene.weapons_key(both), scene.weapons_key(a))
        self.assertEqual(scene.weapons_key(both), scene.weapons_key(dict(reversed(list(both.items())))))

    def test_a_hair_of_a_difference_in_a_reading_costs_no_evaluation(self):
        a = {"r": {"grip": (1.0, 2.0, 3.0), "tip": (1.0, 102.0, 3.0)}}
        b = {"r": {"grip": (1.0 + 1e-9, 2.0, 3.0), "tip": (1.0, 102.0 - 1e-9, 3.0)}}
        self.assertEqual(scene.weapons_key(a), scene.weapons_key(b))

    def test_the_tip_rule_is_tools_aim_s_own(self):
        """The aim's target is the tip past the blade; Weapon overlap aims at the tip itself - one rule."""
        aim = load_aim()
        lo, hi = (-15.6, -31.1, -1.6), (15.6, 115.9, 1.6)
        self.assertEqual(aim.tip_offset(lo, hi), (0.0, 115.9, 0.0))
        top, _ = aim.placement(lo, hi)
        self.assertAlmostEqual(top[1], 115.9 * (1.0 + aim.MARGIN), places=9)
        self.assertEqual(aim.tip_offset((0.0, 0.0, 0.0), (0.0, 0.0, 0.0)), None)

    def test_the_tip_is_the_further_end_of_the_longest_axis(self):
        aim = load_aim()
        self.assertEqual(aim.tip_offset((-1.0, -84.2, -8.0), (1.0, 30.0, 8.0)), (0.0, -84.2, 0.0))


def load_aim():
    import os
    import sys
    plugin = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SkeldarAnim")
    if plugin not in sys.path:
        sys.path.insert(0, plugin)
    from maya_scenesetup import aim
    return aim


class CardTests(unittest.TestCase):

    def test_the_card_grows_a_weapon_tab_with_the_one_slider(self):
        panel = load("panel")
        self.assertIn(("weapon", "Weapon", ("weapon_overlap",)), panel.GROUPS)
        self.assertIn("weapon", [key for row in panel.GROUP_ROWS for key in row])
