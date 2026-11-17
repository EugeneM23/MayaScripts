"""maya_startstop.weapon: Walk Builder's Weapon tab on a start or a stop - Hold, Inherit, Overlap, Aim target,
Shoulder with no cycle: the slow part stands for the mean, the root's motion for the travel, a lag held at the
clip's ends. Runs under mayapy (numpy + the model's OpenMaya-free helpers)."""
import unittest

import numpy as np

from maya_startstop import model as pc
from maya_startstop import weapon as w
from tests.test_startstop_model import synthetic_stop


def rel(a, b):
    return np.einsum("fij,fjk->fik", a, np.linalg.inv(b))


class Pieces(unittest.TestCase):
    def setUp(self):
        self.clip = synthetic_stop()
        self.mats = self.clip.worlds[self.clip.index["hand_l"]]

    def test_late_is_the_input_at_zero_and_holds_the_first_frame(self):
        np.testing.assert_allclose(w.late(self.mats, 0.0), self.mats)
        out = w.late(self.mats, 3.0)                # (the template's rotations orthonormal to 4e-7)
        np.testing.assert_allclose(out[10], self.mats[7], atol=1e-6)
        np.testing.assert_allclose(out[1], self.mats[0], atol=1e-6)
        lead = w.late(self.mats, -3.0)
        np.testing.assert_allclose(lead[-1], self.mats[-1], atol=1e-6)

    def test_a_fractional_lag_falls_between_two_frames(self):
        out = w.late(self.mats, 0.5)
        np.testing.assert_allclose(out[10, 3, :3], 0.5 * (self.mats[9, 3, :3] + self.mats[10, 3, :3]), atol=1e-9)

    def test_keeping_one_is_the_input_and_zero_the_slow_part(self):
        np.testing.assert_allclose(w.keeping(self.mats, 1.0), self.mats)
        np.testing.assert_allclose(w.keeping(self.mats, 0.0), w.slow_mats(self.mats), atol=1e-9)
        half = w.keeping(self.mats, 0.5)
        slow = w.slow_mats(self.mats)
        np.testing.assert_allclose(half[:, 3, :3], 0.5 * (slow[:, 3, :3] + self.mats[:, 3, :3]), atol=1e-9)

    def test_the_slow_part_of_a_still_series_is_itself(self):
        still = np.tile(self.mats[0], (30, 1, 1))
        np.testing.assert_allclose(w.slow_mats(still), still, atol=1e-6)

    def test_aim_swing_is_the_least_turn(self):
        r = w.aim_swing([1.0, 0, 0], [0, 1.0, 0])
        np.testing.assert_allclose(np.array([1.0, 0, 0]) @ r, [0, 1.0, 0], atol=1e-12)
        np.testing.assert_allclose(np.array([0, 0, 1.0]) @ r, [0, 0, 1.0], atol=1e-12)


class Tab(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clip = synthetic_stop()
        cls.a = pc.Analysis(cls.clip)
        cls.F = cls.clip.F
        ix = cls.clip.index
        cls.hand, cls.chest, cls.root = ix["hand_l"], w._chest(cls.clip), cls.a.root
        cls.up, cls.low = ix["upperarm_l"], ix["lowerarm_l"]

    def knobs(self, **given):
        return pc.knobs(**given)

    def test_nothing_held_nothing_moved(self):
        out, info, held = w.apply(self.a, self.clip.worlds, self.knobs(), alpha=np.zeros(self.F))
        np.testing.assert_array_equal(out, self.clip.worlds)
        self.assertEqual(held, set())

    def test_hold_puts_the_hand_on_the_chest_at_its_slow_offset(self):
        out, info, held = w.apply(self.a, self.clip.worlds, self.knobs(), alpha=np.ones(self.F))
        self.assertEqual(held, {"l", "r"})
        H, C = self.clip.worlds[self.hand], self.clip.worlds[self.chest]
        want = w.slow_mats(rel(H, C))
        np.testing.assert_allclose(rel(out[self.hand], out[self.chest]), want, atol=1e-6)
        # the arm swung before; it rides the chest now
        swing = np.linalg.norm(np.diff(rel(H, C)[:, 3, :3], axis=0), axis=1).max()
        held_swing = np.linalg.norm(np.diff(rel(out[self.hand], out[self.chest])[:, 3, :3], axis=0), axis=1).max()
        self.assertLess(held_swing, 0.5 * swing)
        for a_, b_ in ((self.up, self.low), (self.low, self.hand)):
            np.testing.assert_allclose(np.linalg.norm(out[a_, :, 3, :3] - out[b_, :, 3, :3], axis=1),
                                       np.linalg.norm(self.clip.worlds[a_, :, 3, :3] - self.clip.worlds[b_, :, 3, :3],
                                                      axis=1), atol=1e-6)

    def test_hold_blends_in_by_how_much_a_pose_holds_the_arm(self):
        alpha = np.zeros(self.F)
        alpha[30:] = 1.0                      # only where the body stands
        out, _info, _held = w.apply(self.a, self.clip.worlds, self.knobs(), alpha=alpha)
        np.testing.assert_allclose(out[self.hand, :30], self.clip.worlds[self.hand, :30], atol=1e-6)
        self.assertGreater(float(np.abs(out[self.hand, 30:] - self.clip.worlds[self.hand, 30:]).max()), 1e-6)

    def test_where_the_body_stands_hold_keeps_the_hand_where_it_is(self):
        # 2026-11-17: the slow part reaching into the run put a start's hands 12-20 cm off its pose
        still = np.zeros(self.F)
        still[:10] = 1.0
        out, _info, _held = w.apply(self.a, self.clip.worlds, self.knobs(), alpha=np.ones(self.F), still=still)
        H, C = self.clip.worlds[self.hand], self.clip.worlds[self.chest]
        np.testing.assert_allclose(rel(out[self.hand], out[self.chest])[:10], rel(H, C)[:10], atol=1e-6)
        np.testing.assert_allclose(rel(out[self.hand], out[self.chest])[10:], w.slow_mats(rel(H, C))[10:], atol=1e-6)

    def test_a_hand_with_a_weapon_is_held_with_no_pose(self):
        weapons = {"r": {"grip": (0.0, 0.0, 0.0), "tip": (0.0, 0.0, 80.0)}}
        out, info, held = w.apply(self.a, self.clip.worlds, self.knobs(), alpha=np.zeros(self.F), weapons=weapons)
        self.assertEqual(held, {"r"})
        np.testing.assert_allclose(out[self.hand], self.clip.worlds[self.hand], atol=1e-9)    # the empty hand swings

    def test_inherit_zero_rides_only_the_chests_slow_motion_in_the_roots_frame(self):
        out, _i, _h = w.apply(self.a, self.clip.worlds, self.knobs(weapon_inherit=0.0), alpha=np.ones(self.F))
        H, C, R = (self.clip.worlds[j] for j in (self.hand, self.chest, self.root))
        want = np.einsum("fij,fjk->fik", w.slow_mats(rel(H, C)), w.slow_mats(rel(C, R)))
        np.testing.assert_allclose(rel(out[self.hand], out[self.root]), want, atol=1e-6)

    def test_overlap_rides_the_chest_of_that_many_frames_ago(self):
        k = self.knobs(weapon_overlap=100.0)                 # 100 ms at 30 fps: 3 frames
        out, info, _h = w.apply(self.a, self.clip.worlds, k, alpha=np.ones(self.F))
        self.assertAlmostEqual(info["lag"], 3.0)
        H, C, R = (self.clip.worlds[j] for j in (self.hand, self.chest, self.root))
        want = np.einsum("fij,fjk->fik", w.slow_mats(rel(H, C)), w.late(rel(C, R), 3.0))
        np.testing.assert_allclose(rel(out[self.hand], out[self.root]), want, atol=1e-6)

    def test_aim_target_zero_points_the_blade_at_the_slow_target_from_the_grip(self):
        weapons = {"l": {"grip": (2.0, 0.0, 0.0), "tip": (2.0, 0.0, 60.0)}}
        k = self.knobs(weapon_aim=0.0, weapon_hold=0.0)
        out, info, _h = w.apply(self.a, self.clip.worlds, k, alpha=np.zeros(self.F), weapons=weapons)
        grip, tip = np.array([2.0, 0, 0]), np.array([2.0, 0, 60.0 * w.AIM_REACH])
        H0, H1, R = self.clip.worlds[self.hand], out[self.hand], self.clip.worlds[self.root]
        G0 = np.array([grip @ H0[f, :3, :3] + H0[f, 3, :3] for f in range(self.F)])
        G1 = np.array([grip @ H1[f, :3, :3] + H1[f, 3, :3] for f in range(self.F)])
        T0 = np.array([tip @ H0[f, :3, :3] + H0[f, 3, :3] for f in range(self.F)])
        T1 = np.array([tip @ H1[f, :3, :3] + H1[f, 3, :3] for f in range(self.F)])
        rr = np.array([pc.orthonormal(r) for r in R])
        Tr = np.einsum("fi,fij->fj", T0 - R[:, 3, :3], np.swapaxes(rr, -1, -2))
        target = np.einsum("fi,fij->fj", w.keeping_points(Tr, 0.0), rr) + R[:, 3, :3]
        np.testing.assert_allclose(G1, G0, atol=1e-4)                     # the grip stays (within the arm's reach)
        for f in range(self.F):                                           # the blade's line through the target
            d = pc._unit(T1[f] - G1[f])
            off = (target[f] - G1[f]) - np.dot(target[f] - G1[f], d) * d
            self.assertLess(float(np.linalg.norm(off)), 1e-3, f)
        self.assertEqual(info["aim"]["lever"], {"l": "weapon"})

    def test_aim_target_with_no_weapon_and_no_bone_says_so(self):
        _o, info, _h = w.apply(self.a, self.clip.worlds, self.knobs(weapon_aim_l=0.0, weapon_hold=0.0),
                               alpha=np.zeros(self.F))
        self.assertEqual(info["aim"]["asked"], ["l"])
        self.assertIn("Aim target does nothing", w.line(info))

    def test_shoulder_one_leaves_the_arm_its_slow_reach(self):
        k = self.knobs(weapon_shoulder_l=1.0, weapon_hold=0.0)
        out, info, _h = w.apply(self.a, self.clip.worlds, k, alpha=np.zeros(self.F))
        H = self.clip.worlds[self.hand, :, 3, :3]
        before = np.linalg.norm(H - self.clip.worlds[self.up, :, 3, :3], axis=1)
        after = np.linalg.norm(out[self.hand, :, 3, :3] - out[self.up, :, 3, :3], axis=1)
        self.assertLess(float(np.ptp(after)), 0.5 * float(np.ptp(before)))
        np.testing.assert_allclose(out[self.hand, :, 3, :3], H, atol=1e-4)       # the hand where it was

    def test_two_hands_holding_one_thing_keep_their_hold(self):
        # the hands each arm is rebuilt to keep their relation (the arms' reach is the fixture's: its hands hang
        # 40 cm apart, so the IK itself is not what is asked here)
        wanted = {}
        real = w.arm_to_hand

        def record(clip, kin, chain, want):
            wanted[chain[3]] = np.array(want)
            return real(clip, kin, chain, want)
        w.arm_to_hand = record
        try:
            w.apply(self.a, self.clip.worlds, self.knobs(weapon_overlap=100.0), alpha=np.ones(self.F), grip=True)
        finally:
            w.arm_to_hand = real
        ix = self.clip.index
        before = rel(self.clip.worlds[ix["hand_l"]], self.clip.worlds[ix["hand_r"]])
        np.testing.assert_allclose(rel(wanted[ix["hand_l"]], wanted[ix["hand_r"]]), before, atol=1e-6)

    def test_the_status_line(self):
        _o, info, _h = w.apply(self.a, self.clip.worlds, self.knobs(weapon_overlap=100.0, weapon_inherit=0.5),
                               alpha=np.ones(self.F))
        text = w.line(info)
        self.assertIn("both hands ride the chest at 50 % of its motion", text)
        self.assertIn("3.0 fr late", text)


class Evaluate(unittest.TestCase):
    def test_a_held_hand_takes_no_arm_spring_and_evaluate_reports_the_tab(self):
        from tests.test_startstop_model import statics_of, pose_from
        clip = synthetic_stop()
        a = pc.Analysis(clip)
        pose = pc.prepare(a, statics_of(clip), pose_from(synthetic_stop(lean_end=0.3), clip.F - 1))
        result = pc.evaluate(a, pose, k=pc.knobs(arm_drag=2.0))
        self.assertEqual(result.info["weapon"]["hold"], ["l", "r"])
        off = pc.evaluate(a, pose, k=pc.knobs(arm_drag=2.0, weapon_hold=0.0))
        self.assertEqual(off.info["weapon"]["hold"], [])
        self.assertGreater(off.info["overlap"]["arms"], 0.0)

    def test_the_first_version_holds_nothing(self):
        self.assertEqual(pc.knobs_from()["weapon_hold"], 0.0)


if __name__ == "__main__":
    unittest.main()
