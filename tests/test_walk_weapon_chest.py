"""Walk Builder's weapon overlap from the CHEST (2026-11-03), and 2H.

The animator: «он должен быть в walk builder во вкладке Weapon и работать без рига». The weapon keeps its
own pose relative to the chest and the chest's own pose from `Chest lag` ms ago is put back, its turn and
its travel scaled by `Chest rotation` / `Chest position`; every hand holding it is moved with it, so the
grip holds and the arm's swing becomes a consequence. 2H binds a free hand to the holder's by the offset
it has at the cycle's first frame.

Spec: docs/superpowers/specs/2026-11-03-walk-weapon-chest-override-design.md
"""

import math
import unittest

import numpy as np

from tests.test_walkmodel import load, walk, wm
from tests.test_walk_weapon_overlap import GRIP, TIP, WEAPON, points

gait = load("gait")


class SteadyChest(unittest.TestCase):
    """`steady_chest`: the chest's own animation scaled, its travel kept."""

    def chest(self, n=8, travel=80.0):
        """A chest cycle that bobs, sways and turns while it travels."""
        out = np.zeros((n + 1, 4, 4))
        for f in range(n + 1):
            a = 2.0 * math.pi * (f % n) / float(n)
            out[f, :3, :3] = wm.exp_rot(np.array([0.04 * math.sin(a), 0.12 * math.cos(a), 0.0]))
            out[f, 3, :3] = np.array([3.0 * math.sin(a), 100.0 + 2.0 * math.cos(2.0 * a),
                                      travel * f / float(n)])
            out[f, 3, 3] = 1.0
        return out

    def test_full_strength_gives_the_cycle_back(self):
        w, mats = walk(), self.chest()
        self.assertTrue(np.allclose(w.steady_chest(mats, 1.0, 1.0), mats, atol=1e-12))

    def test_no_strength_leaves_one_heading_and_a_straight_line(self):
        w, mats = walk(), self.chest()
        got = w.steady_chest(mats, 0.0, 0.0)
        n = mats.shape[0] - 1
        for f in range(n + 1):
            self.assertTrue(np.allclose(got[f, :3, :3], got[0, :3, :3], atol=1e-12), f)
        per = (got[n, 3, :3] - got[0, 3, :3]) / float(n)
        for f in range(n + 1):
            self.assertTrue(np.allclose(got[f, 3, :3], got[0, 3, :3] + per * f, atol=1e-9), f)

    def test_the_travel_is_kept_at_any_strength(self):
        w, mats = walk(), self.chest()
        n = mats.shape[0] - 1
        was = mats[n, 3, :3] - mats[0, 3, :3]
        for rot, pos in ((0.0, 0.0), (0.5, 0.25), (1.0, 0.0)):
            got = w.steady_chest(mats, rot, pos)
            self.assertTrue(np.allclose(got[n, 3, :3] - got[0, 3, :3], was, atol=1e-9), (rot, pos))
            self.assertTrue(np.allclose(got[n, :3, :3], got[0, :3, :3], atol=1e-12), (rot, pos))

    def test_half_strength_is_half_the_deviation(self):
        w, mats = walk(), self.chest()
        flat, half = w.steady_chest(mats, 0.0, 0.0), w.steady_chest(mats, 0.5, 0.5)
        n = mats.shape[0] - 1
        for f in range(n + 1):
            want = flat[f, 3, :3] + 0.5 * (mats[f, 3, :3] - flat[f, 3, :3])
            self.assertTrue(np.allclose(half[f, 3, :3], want, atol=1e-9), f)


class EngineKnobs(unittest.TestCase):

    def test_the_four_knobs_exist_with_their_defaults(self):
        k = wm.knobs()
        self.assertEqual(k["weapon_hold"], 0.0)
        self.assertEqual(k["weapon_chest_rotation"], 1.0)
        self.assertEqual(k["weapon_chest_position"], 1.0)
        self.assertEqual(k["weapon_chest_lag"], 0.0)

    def test_they_are_sided(self):
        for name in ("weapon_hold", "weapon_chest_rotation", "weapon_chest_position", "weapon_chest_lag"):
            self.assertIn(name, wm.SIDED, name)
            self.assertEqual(wm.sided(wm.knobs(**{name + "_l": 0.5}))["l"][name], 0.5)
            self.assertEqual(wm.sided(wm.knobs(**{name + "_l": 0.5}))["r"][name],
                             wm.knobs()[name])


class ChestJoint(unittest.TestCase):

    def test_it_is_the_top_spine_joint_the_chest_knobs_use(self):
        w = walk()
        j = w._chest_joint()
        self.assertIsNotNone(j)
        self.assertIn(j, w.chest_share)
        top = max((int(w.names[x].split("_")[-1]), x) for x in w.chest_share)[1]
        self.assertEqual(j, top)

    def test_with_no_spine_of_its_own_it_is_what_the_arms_hang_from(self):
        w = walk()
        w.chest_share = {}
        self.assertEqual(w._chest_joint(), w.parents[w._arm_chains()["l"][0]])


class Pass(unittest.TestCase):
    """The pass through evaluate. The elbows are bent and the springs off for the same reason the Weapon
    overlap tests bend them: the walker's arm hangs 99 % extended, and an arm at full stretch cannot follow
    a hand the pass moves - two_bone clamps it on its line and the promise gives by millimetres."""

    BENT = 70.0
    LAG = 3.0

    def setUp(self):
        self.w = walk()
        self.base = self.go()
        self.n = self.base.frames
        self.chains = self.w._arm_chains()
        self.hand_r, self.hand_l = self.chains["r"][-1], self.chains["l"][-1]
        self.chest = self.w._chest_joint()

    def go(self, weapons=WEAPON, **more):
        knobs = dict({"balance": 0.0, "arm_drag": 0.0, "elbow_add": self.BENT}, **more)
        return self.w.evaluate(knobs, weapons=weapons)

    def over(self, result):
        return (result.info.get("arms") or {}).get("overlap") or {}

    #  the identity

    def test_the_defaults_are_the_walk_with_no_weapon_at_all(self):
        plain = self.go(weapons=None)
        self.assertTrue(np.array_equal(self.base.worlds, plain.worlds))
        self.assertEqual(self.over(self.base)["chest"], [])
        self.assertEqual(self.over(self.base)["chest_cm"], 0.0)

    def test_full_strength_with_no_lag_is_the_identity_matrix_for_matrix(self):
        got = self.go(weapon_chest_rotation=1.0, weapon_chest_position=1.0, weapon_chest_lag=0.0)
        self.assertTrue(np.array_equal(got.worlds, self.base.worlds))

    def test_a_lag_with_no_weapon_in_the_hands_changes_nothing(self):
        plain = self.go(weapons=None)
        got = self.go(weapons=None, weapon_chest_lag=self.LAG)
        self.assertTrue(np.array_equal(got.worlds, plain.worlds))
        self.assertEqual(self.over(got)["chest"], [])

    #  the promise

    def test_the_weapon_sits_on_the_chest_of_lag_frames_ago(self):
        got = self.go(weapon_chest_lag=self.LAG)
        C = np.asarray(self.base.worlds[self.chest], float)
        late = wm.shifted_cycle(C, self.LAG)
        for f in range(self.n + 1):
            was = np.asarray(self.base.worlds[self.hand_r, f], float) @ np.linalg.inv(C[f])
            now = np.asarray(got.worlds[self.hand_r, f], float) @ np.linalg.inv(late[f])
            self.assertTrue(np.allclose(now, was, atol=1e-6), f)

    def test_the_grip_really_moves(self):
        got = self.go(weapon_chest_lag=self.LAG)
        before = points(GRIP, np.asarray(self.base.worlds[self.hand_r], float))
        after = points(GRIP, np.asarray(got.worlds[self.hand_r], float))
        moved = max(float(np.linalg.norm(after[f] - before[f])) for f in range(self.n + 1))
        self.assertGreater(moved, 0.5)
        self.assertAlmostEqual(self.over(got)["chest_cm"], moved, delta=0.5 * moved + 1e-6)
        self.assertEqual(self.over(got)["chest"], ["r"])

    def test_the_strengths_work_with_no_lag_at_all(self):
        """The animator's own report (2026-11-03): at 0 / 0 the weapon must stop inheriting the body,
        lag or no lag. The first build scaled only the lag's own motion, so this moved nothing."""
        got = self.go(weapon_chest_rotation=0.0, weapon_chest_position=0.0)
        moved = max(float(np.linalg.norm(got.worlds[self.hand_r, f, 3, :3]
                                         - self.base.worlds[self.hand_r, f, 3, :3]))
                    for f in range(self.n + 1))
        self.assertGreater(moved, 0.5)

    def test_position_zero_takes_the_chests_bob_and_sway_off_the_weapon(self):
        """With the turn at full strength the pass is a pure translation: minus the chest's own deviation
        from the straight line it travels along."""
        got = self.go(weapon_chest_position=0.0)
        C = np.asarray(self.base.worlds[self.chest], float)
        steady = self.w.steady_chest(C, 1.0, 0.0)
        for f in range(self.n + 1):
            want = (self.base.worlds[self.hand_r, f, 3, :3] + steady[f, 3, :3] - C[f, 3, :3])
            self.assertTrue(np.allclose(got.worlds[self.hand_r, f, 3, :3], want, atol=1e-6), f)
            self.assertTrue(np.allclose(got.worlds[self.hand_r, f, :3, :3],
                                        self.base.worlds[self.hand_r, f, :3, :3], atol=1e-9), f)
        off = max(float(np.linalg.norm(steady[f, 3, :3] - C[f, 3, :3])) for f in range(self.n + 1))
        self.assertGreater(off, 0.5)         # the control: the chest really does bob and sway

    def test_rotation_zero_leaves_the_weapon_on_the_cycles_mean_heading(self):
        """With the place at full strength the pass turns the weapon by the chest's own turn, undone."""
        got = self.go(weapon_chest_rotation=0.0)
        C = np.asarray(self.base.worlds[self.chest], float)
        steady = self.w.steady_chest(C, 0.0, 1.0)
        worst = 0.0
        for f in range(self.n + 1):
            want = (np.asarray(self.base.worlds[self.hand_r, f, :3, :3], float)
                    @ C[f, :3, :3].T @ steady[f, :3, :3])
            self.assertTrue(np.allclose(got.worlds[self.hand_r, f, :3, :3], want, atol=1e-6), f)
            worst = max(worst, math.degrees(float(np.linalg.norm(
                wm.log_rot(C[0, :3, :3].T @ C[f, :3, :3])))))
        self.assertGreater(worst, 1.0)       # the control: the chest really does turn over the cycle

    #  what must not break

    def test_the_bones_keep_their_lengths(self):
        got = self.go(weapon_chest_lag=self.LAG)
        for side, chain in self.chains.items():
            for a, b in zip(chain, chain[1:]):
                for f in range(self.n + 1):
                    was = float(np.linalg.norm(self.base.worlds[b, f, 3, :3] - self.base.worlds[a, f, 3, :3]))
                    now = float(np.linalg.norm(got.worlds[b, f, 3, :3] - got.worlds[a, f, 3, :3]))
                    self.assertAlmostEqual(now, was, places=4, msg=(side, f))

    def test_the_loop_closes(self):
        got = self.go(weapon_chest_lag=self.LAG)
        travel = (self.base.worlds[self.hand_r, self.n, 3, :3] - self.base.worlds[self.hand_r, 0, 3, :3])
        self.assertTrue(np.allclose(got.worlds[self.hand_r, self.n, :3, :3],
                                    got.worlds[self.hand_r, 0, :3, :3], atol=1e-6))
        self.assertTrue(np.allclose(got.worlds[self.hand_r, self.n, 3, :3]
                                    - got.worlds[self.hand_r, 0, 3, :3], travel, atol=1e-6))

    def test_the_body_above_the_arms_is_untouched(self):
        got = self.go(weapon_chest_lag=self.LAG)
        for j in (self.chest, self.w.index["pelvis"], self.w.index["head"]):
            self.assertTrue(np.allclose(got.worlds[j], self.base.worlds[j], atol=1e-9), j)


class TwoHands(unittest.TestCase):

    BENT = 70.0

    def setUp(self):
        self.w = walk()
        self.base = self.go()
        self.n = self.base.frames
        self.chains = self.w._arm_chains()
        self.hand_r, self.hand_l = self.chains["r"][-1], self.chains["l"][-1]

    def go(self, weapons=WEAPON, **more):
        knobs = dict({"balance": 0.0, "arm_drag": 0.0, "elbow_add": self.BENT}, **more)
        return self.w.evaluate(knobs, weapons=weapons)

    def offsets(self, result):
        """The free hand's offset from the holder's, frame by frame."""
        return [np.asarray(result.worlds[self.hand_l, f], float)
                @ np.linalg.inv(np.asarray(result.worlds[self.hand_r, f], float))
                for f in range(self.n + 1)]

    def test_off_it_changes_nothing(self):
        self.assertTrue(np.array_equal(self.go(weapon_hold_l=0.0).worlds, self.base.worlds))

    def test_the_free_hand_keeps_the_frame_zero_offset_on_every_frame(self):
        got = self.go(weapon_hold_l=1.0, weapon_chest_lag=3.0)
        offs = self.offsets(got)
        for f in range(self.n + 1):
            self.assertTrue(np.allclose(offs[f], offs[0], atol=1e-5), f)
        self.assertEqual(((got.info.get("arms") or {}).get("overlap") or {})["hold"], ["l"])

    def test_without_it_the_free_hand_swings_on_its_own(self):
        offs = self.offsets(self.base)
        moved = max(float(np.linalg.norm(offs[f][3, :3] - offs[0][3, :3])) for f in range(self.n + 1))
        self.assertGreater(moved, 1.0)

    def test_a_hand_holding_its_own_weapon_is_not_bound(self):
        both = {"r": {"grip": GRIP, "tip": TIP}, "l": {"grip": GRIP, "tip": TIP}}
        got = self.go(weapons=both, weapon_hold_l=1.0)
        self.assertEqual(((got.info.get("arms") or {}).get("overlap") or {})["hold"], [])


class Parameters(unittest.TestCase):

    def test_the_weapon_tab_holds_the_four_beside_the_overlap(self):
        names = [p.name for p in gait.PARAMS if p.group == gait.WEAPON]
        self.assertEqual(names, ["weapon_overlap", "weapon_hold", "weapon_chest_rotation",
                                 "weapon_chest_position", "weapon_chest_lag"])

    def test_every_one_of_them_is_sided(self):
        for p in gait.PARAMS:
            if p.group == gait.WEAPON:
                self.assertTrue(p.sided, p.name)

    def test_the_defaults_are_the_identity(self):
        by = dict((p.name, p) for p in gait.PARAMS)
        self.assertEqual(by["weapon_hold"].default, 0.0)
        self.assertEqual(by["weapon_chest_rotation"].default, 1.0)
        self.assertEqual(by["weapon_chest_position"].default, 1.0)
        self.assertEqual(by["weapon_chest_lag"].default, 0.0)

    def test_the_lag_is_ms_turned_into_frames_at_the_output_rate(self):
        w = walk()
        e = gait.engine_knobs(w, gait.own(w), {"weapon_chest_lag": 150.0}, fps_out=30.0)
        self.assertAlmostEqual(e["weapon_chest_lag_r"], 4.5, places=6)
        self.assertAlmostEqual(e["weapon_chest_lag_l"], 4.5, places=6)
        e24 = gait.engine_knobs(w, gait.own(w), {"weapon_chest_lag": 150.0}, fps_out=24.0)
        self.assertAlmostEqual(e24["weapon_chest_lag_r"], 3.6, places=6)

    def test_the_strengths_and_the_hold_pass_through(self):
        w = walk()
        e = gait.engine_knobs(w, gait.own(w),
                              {"weapon_chest_rotation": 0.6, "weapon_hold": 1.0}, fps_out=30.0)
        self.assertAlmostEqual(e["weapon_chest_rotation_r"], 0.6, places=6)
        self.assertEqual(e["weapon_hold_r"], 1.0)

    def test_the_defaults_give_the_identity_knobs(self):
        w = walk()
        e = gait.engine_knobs(w, gait.own(w), {}, fps_out=30.0)
        for side in ("_l", "_r"):
            self.assertEqual(e["weapon_chest_lag" + side], 0.0)
            self.assertEqual(e["weapon_chest_rotation" + side], 1.0)
            self.assertEqual(e["weapon_chest_position" + side], 1.0)
            self.assertEqual(e["weapon_hold" + side], 0.0)

    def test_the_lag_reaches_half_the_cycle_either_way(self):
        w = walk()
        lo, hi = gait.ranges(gait.own(w), w.leg_length, w)["weapon_chest_lag"]
        cap = gait.overlap_cap(w)
        self.assertAlmostEqual(lo, -cap, places=6)
        self.assertAlmostEqual(hi, cap, places=6)

    def test_the_cycles_own_values_are_the_defaults(self):
        """They are not measured off a cycle, so a cycle's own value IS the default - which is what makes
        `own_knobs()` give the clip back and the sliders open on the identity."""
        own = gait.own(walk())
        for name, want in (("weapon_chest_rotation", 1.0), ("weapon_chest_position", 1.0),
                           ("weapon_chest_lag", 0.0), ("weapon_hold", 0.0)):
            self.assertNotIn(name, own, name)
            self.assertEqual(gait.own_value(own, name), want, name)


class Balance(unittest.TestCase):

    def test_the_carry_sees_the_pass(self):
        w = walk()
        base = w.evaluate({"elbow_add": 70.0, "arm_drag": 0.0}, weapons=WEAPON)
        got = w.evaluate({"elbow_add": 70.0, "arm_drag": 0.0, "weapon_chest_lag": 6.0}, weapons=WEAPON)
        a = np.asarray(base.worlds[w.index["pelvis"]], float)[:, 3, :3]
        b = np.asarray(got.worlds[w.index["pelvis"]], float)[:, 3, :3]
        self.assertGreater(float(np.abs(a - b).max()), 1e-9)


if __name__ == "__main__":
    unittest.main()
