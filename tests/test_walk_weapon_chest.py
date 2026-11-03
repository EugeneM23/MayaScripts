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
wp = load("pose")
sw = load("scene")


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

    def test_the_five_knobs_exist_with_their_defaults(self):
        k = wm.knobs()
        self.assertEqual(k["weapon_hold"], 0.0)
        self.assertEqual(k["weapon_chest"], 0.0)          # the mode is off until the chip is ticked
        self.assertEqual(k["weapon_chest_rotation"], 1.0)
        self.assertEqual(k["weapon_chest_position"], 1.0)
        self.assertEqual(k["weapon_chest_lag"], 0.0)

    def test_they_are_sided(self):
        for name in ("weapon_hold", "weapon_chest", "weapon_chest_rotation", "weapon_chest_position",
                     "weapon_chest_lag"):
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

    def on(self, **more):
        """The Chest chip on - the weapon parented to the chest, the sliders its strength."""
        return self.go(weapon_chest=1.0, **more)

    def over(self, result):
        return (result.info.get("arms") or {}).get("overlap") or {}

    #  off

    def test_the_defaults_are_the_walk_with_no_weapon_at_all(self):
        plain = self.go(weapons=None)
        self.assertTrue(np.array_equal(self.base.worlds, plain.worlds))
        self.assertEqual(self.over(self.base)["chest"], [])
        self.assertEqual(self.over(self.base)["chest_cm"], 0.0)

    def test_the_chip_off_the_three_sliders_do_nothing(self):
        """Neither end of the sliders is the cycle's own animation, so the mode is the chip's and the
        sliders cannot turn it on (2026-11-03)."""
        for more in ({"weapon_chest_rotation": 0.0}, {"weapon_chest_position": 0.0},
                     {"weapon_chest_lag": self.LAG},
                     {"weapon_chest_rotation": 0.0, "weapon_chest_position": 0.0,
                      "weapon_chest_lag": self.LAG}):
            got = self.go(**more)
            self.assertTrue(np.array_equal(got.worlds, self.base.worlds), more)
            self.assertEqual(self.over(got)["chest"], [], more)

    def test_the_chip_on_with_no_weapon_in_the_hands_changes_nothing(self):
        plain = self.go(weapons=None)
        got = self.go(weapons=None, weapon_chest=1.0, weapon_chest_lag=self.LAG)
        self.assertTrue(np.array_equal(got.worlds, plain.worlds))
        self.assertEqual(self.over(got)["chest"], [])

    def test_the_info_names_the_hand_the_scene_gives_a_weapon(self):
        self.assertEqual(self.over(self.base)["held"], ["r"])
        self.assertEqual(self.over(self.go(weapons=None))["held"], [])

    #  the promise: a parent constraint to the chest, the sliders its strength

    def want(self, rotation, position, lag=0.0):
        """What the chip promises the holding hand: its offset from the chest HELD at its mean, on the
        chest's own cycle scaled by the strengths and read `lag` frames back."""
        C = np.asarray(self.base.worlds[self.chest], float)
        H = np.asarray(self.base.worlds[self.hand_r], float)
        chest = wm.shifted_cycle(self.w.steady_chest(C, rotation, position), lag)
        arm = self.w.steady_chest(np.array([H[f] @ np.linalg.inv(C[f]) for f in range(self.n + 1)]),
                                  0.0, 0.0)
        return np.array([arm[f] @ chest[f] for f in range(self.n + 1)])

    def test_full_strength_rides_the_torso_rigidly(self):
        """The animator's own words (2026-11-03): «если 1 то двигаемся за туловищем, а не так как в
        изначальной анимации». At 1 / 1 / 0 the weapon's offset from the chest is constant - a parent
        constraint - and that is NOT what the cycle itself does."""
        got = self.on(weapon_chest_rotation=1.0, weapon_chest_position=1.0)
        C = np.asarray(got.worlds[self.chest], float)
        H = np.asarray(got.worlds[self.hand_r], float)
        rel = np.array([H[f] @ np.linalg.inv(C[f]) for f in range(self.n + 1)])
        rigid = max(float(np.abs(rel[f] - rel[0]).max()) for f in range(self.n + 1))
        moved = max(float(np.linalg.norm(got.worlds[self.hand_r, f, 3, :3]
                                         - self.base.worlds[self.hand_r, f, 3, :3]))
                    for f in range(self.n + 1))
        self.assertLess(rigid, 1e-6)
        self.assertGreater(moved, 0.5)       # the control: it is not the cycle's own animation

    def test_the_weapon_rides_the_chest_of_lag_frames_ago(self):
        got = self.on(weapon_chest_lag=self.LAG)
        want = self.want(1.0, 1.0, self.LAG)
        for f in range(self.n + 1):
            self.assertTrue(np.allclose(got.worlds[self.hand_r, f], want[f], atol=1e-6), f)

    def test_the_grip_really_moves(self):
        got = self.on(weapon_chest_lag=self.LAG)
        before = points(GRIP, np.asarray(self.base.worlds[self.hand_r], float))
        after = points(GRIP, np.asarray(got.worlds[self.hand_r], float))
        moved = max(float(np.linalg.norm(after[f] - before[f])) for f in range(self.n + 1))
        self.assertGreater(moved, 0.5)
        self.assertAlmostEqual(self.over(got)["chest_cm"], moved, delta=0.5 * moved + 1e-6)
        self.assertEqual(self.over(got)["chest"], ["r"])

    def test_no_strength_hangs_the_weapon_in_the_air(self):
        """«Если 0 то стоим на месте»: at 0 / 0 the weapon keeps nothing of the body but the walk's own
        locomotion - not the chest's bob, sway and turn, and not the arm's own swing."""
        got = self.on(weapon_chest_rotation=0.0, weapon_chest_position=0.0)
        after = points(GRIP, np.asarray(got.worlds[self.hand_r], float))
        before = points(GRIP, np.asarray(self.base.worlds[self.hand_r], float))
        per = (after[self.n] - after[0]) / float(self.n)
        was = (before[self.n] - before[0]) / float(self.n)
        wander = max(float(np.linalg.norm(after[f] - after[0] - per * f)) for f in range(self.n + 1))
        carried = max(float(np.linalg.norm(before[f] - before[0] - was * f)) for f in range(self.n + 1))
        self.assertLess(wander, 1e-4)
        self.assertGreater(carried, 0.5)     # the control: the body really does carry it about

    def test_the_arms_own_swing_is_off_the_weapon_at_every_strength(self):
        """The weapon hangs at its MEAN offset from the chest whatever the sliders say - it is a parent,
        not a mix with the cycle's own animation. The arm then follows the weapon."""
        C = np.asarray(self.base.worlds[self.chest], float)
        H = np.asarray(self.base.worlds[self.hand_r], float)
        own = np.array([H[f] @ np.linalg.inv(C[f]) for f in range(self.n + 1)])
        moved = max(float(np.linalg.norm(own[f, 3, :3] - own[0, 3, :3])) for f in range(self.n + 1))
        self.assertGreater(moved, 0.5)       # the control: the hand really does move in the chest's frame
        for rot, pos in ((0.0, 0.0), (0.5, 0.5), (1.0, 1.0), (0.09, 1.0)):
            got = self.on(weapon_chest_rotation=rot, weapon_chest_position=pos)
            want = self.want(rot, pos)
            for f in range(self.n + 1):
                self.assertTrue(np.allclose(got.worlds[self.hand_r, f], want[f], atol=1e-6), (rot, pos, f))

    def test_position_zero_takes_the_bob_and_sway_off_the_weapon(self):
        """With the turn at full strength the weapon inherits every heading the chest has and loses every
        deviation from the line it travels along."""
        got = self.on(weapon_chest_position=0.0)
        want = self.want(1.0, 0.0)
        for f in range(self.n + 1):
            self.assertTrue(np.allclose(got.worlds[self.hand_r, f], want[f], atol=1e-6), f)
        off = max(float(np.linalg.norm(want[f, 3, :3] - self.base.worlds[self.hand_r, f, 3, :3]))
                  for f in range(self.n + 1))
        self.assertGreater(off, 0.5)         # the control: it really does move the weapon

    def test_rotation_zero_leaves_the_weapon_on_one_heading(self):
        """With the place at full strength the weapon is carried where the chest carries it and stops
        turning."""
        got = self.on(weapon_chest_rotation=0.0)
        want = self.want(0.0, 1.0)
        for f in range(self.n + 1):
            self.assertTrue(np.allclose(got.worlds[self.hand_r, f], want[f], atol=1e-6), f)
        worst = max(math.degrees(float(np.linalg.norm(wm.log_rot(
            np.asarray(self.base.worlds[self.hand_r, 0, :3, :3], float).T
            @ self.base.worlds[self.hand_r, f, :3, :3])))) for f in range(self.n + 1))
        turn = max(math.degrees(float(np.linalg.norm(wm.log_rot(
            np.asarray(got.worlds[self.hand_r, 0, :3, :3], float).T
            @ got.worlds[self.hand_r, f, :3, :3])))) for f in range(self.n + 1))
        self.assertGreater(worst, 1.0)       # the control: the weapon really does turn without it
        self.assertLess(turn, 1e-3)

    #  what must not break

    def test_the_bones_keep_their_lengths(self):
        got = self.on(weapon_chest_lag=self.LAG)
        for side, chain in self.chains.items():
            for a, b in zip(chain, chain[1:]):
                for f in range(self.n + 1):
                    was = float(np.linalg.norm(self.base.worlds[b, f, 3, :3] - self.base.worlds[a, f, 3, :3]))
                    now = float(np.linalg.norm(got.worlds[b, f, 3, :3] - got.worlds[a, f, 3, :3]))
                    self.assertAlmostEqual(now, was, places=4, msg=(side, f))

    def test_the_loop_closes(self):
        got = self.on(weapon_chest_lag=self.LAG)
        travel = (self.base.worlds[self.hand_r, self.n, 3, :3] - self.base.worlds[self.hand_r, 0, 3, :3])
        self.assertTrue(np.allclose(got.worlds[self.hand_r, self.n, :3, :3],
                                    got.worlds[self.hand_r, 0, :3, :3], atol=1e-6))
        self.assertTrue(np.allclose(got.worlds[self.hand_r, self.n, 3, :3]
                                    - got.worlds[self.hand_r, 0, 3, :3], travel, atol=1e-6))

    def test_the_body_above_the_arms_is_untouched(self):
        got = self.on(weapon_chest_lag=self.LAG)
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


class OutOfPose(unittest.TestCase):
    """An arm the pose's own chip leaves out is left alone by the Weapon tab too (2026-11-03, the animator:
    «фильтр который исключает влияние позы ... на руку должен исключать и обработку руки вкладкой weapon»)."""

    BENT = 70.0

    def setUp(self):
        from tests.test_walk_one_arm import prepared
        self.w, self.whole = prepared()
        self.whole = dict(self.whole, grip=True)
        self.chains = self.w._arm_chains()
        self.hand_r, self.hand_l = self.chains["r"][-1], self.chains["l"][-1]

    def pose(self, *parts):
        return wp.filtered(self.whole, parts or wp.ALL_PARTS)

    def go(self, pose, weapons=WEAPON, **over):
        ks = dict({"balance": 0.0, "arm_drag": 0.0, "elbow_add": self.BENT, "pose": 1.0}, **over)
        for name, value in list(over.items()):
            if name in wm.SIDED:
                ks[name + "_l"] = ks[name + "_r"] = value
        return self.w.evaluate(ks, pose, weapons=weapons)

    def over(self, result):
        return (result.info.get("arms") or {}).get("overlap") or {}

    def test_filtered_records_which_arms_are_in(self):
        self.assertEqual(wp.filtered(self.whole, wp.ALL_PARTS)["arm_sides"], ("l", "r"))
        self.assertEqual(self.pose("torso", "arm_r")["arm_sides"], ("r",))
        self.assertEqual(self.pose("torso")["arm_sides"], ())

    def test_a_pose_that_was_never_filtered_leaves_every_arm_in(self):
        self.assertNotIn("arm_sides", self.whole)
        got = self.go(self.whole, weapon_chest=1.0, weapon_chest_lag=3.0)
        self.assertEqual(self.over(got)["chest"], ["r"])
        self.assertEqual(self.over(got)["out_of_pose"], [])

    def test_the_weapons_own_arm_out_of_the_pose_is_not_processed(self):
        left = {"l": {"grip": GRIP, "tip": TIP}}
        kept = self.go(self.pose(*[p for p in wp.ALL_PARTS if p != "arm_l"]), weapons=left,
                       weapon_chest_lag=3.0, weapon_chest_rotation=0.0, weapon_chest_position=0.0)
        plain = self.go(self.pose(*[p for p in wp.ALL_PARTS if p != "arm_l"]), weapons=left)
        self.assertTrue(np.array_equal(kept.worlds, plain.worlds))
        self.assertEqual(self.over(kept)["chest"], [])
        self.assertEqual(self.over(kept)["out_of_pose"], ["l"])

    def test_the_other_arm_out_of_the_pose_is_not_carried(self):
        out = self.pose(*[p for p in wp.ALL_PARTS if p != "arm_l"])
        got = self.go(out, weapon_chest=1.0, weapon_chest_lag=3.0)
        base = self.go(out)
        n = got.frames
        moved = max(float(np.linalg.norm(got.worlds[self.hand_l, f, 3, :3]
                                         - base.worlds[self.hand_l, f, 3, :3])) for f in range(n + 1))
        self.assertLess(moved, 1e-9)
        carried = self.go(self.pose(), weapon_chest=1.0, weapon_chest_lag=3.0)
        with_both = self.go(self.pose())
        moved_both = max(float(np.linalg.norm(carried.worlds[self.hand_l, f, 3, :3]
                                              - with_both.worlds[self.hand_l, f, 3, :3]))
                         for f in range(n + 1))
        self.assertGreater(moved_both, 0.5)      # the control: with both arms in it IS carried

    def test_2h_cannot_bind_an_arm_out_of_the_pose(self):
        out = self.pose(*[p for p in wp.ALL_PARTS if p != "arm_l"])
        got = self.go(out, weapon_hold=1.0, weapon_chest_lag=3.0)
        self.assertEqual(self.over(got)["hold"], [])
        both = self.go(self.pose(), weapon_hold=1.0, weapon_chest_lag=3.0)
        self.assertEqual(self.over(both)["hold"], ["l"])


class Parameters(unittest.TestCase):

    def test_the_weapon_tab_holds_the_five_beside_the_overlap(self):
        names = [p.name for p in gait.PARAMS if p.group == gait.WEAPON]
        self.assertEqual(names, ["weapon_overlap", "weapon_hold", "weapon_chest",
                                 "weapon_chest_rotation", "weapon_chest_position", "weapon_chest_lag"])

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


class ChipMigration(unittest.TestCase):
    """A card or a walker from before the chip (2026-11-03): the three sliders WERE the mode, so any of
    them set means the animator wanted it on. `normal_params` turns it on once, and the next press writes
    the chip back."""

    def params(self, changes, pins=()):
        return sw.normal_params({"changes": changes, "pins": list(pins)})["changes"]

    def test_a_stored_slider_turns_the_chip_on(self):
        for name in ("weapon_chest_rotation", "weapon_chest_position", "weapon_chest_lag"):
            for key in (name, name + "_l", name + "_r"):
                got = self.params({key: ("offset", -0.5)})
                self.assertEqual(got.get("weapon_chest"), ("offset", 1.0), key)

    def test_the_chips_own_key_is_not_a_slider(self):
        """"weapon_chest_lag" starts with the chip's own sided key "weapon_chest_l" - the migration must
        name the keys, never match a prefix."""
        for key in ("weapon_chest", "weapon_chest_l", "weapon_chest_r"):
            got = self.params({key: ("offset", 0.0)})
            self.assertEqual(got.get("weapon_chest"), ("offset", 0.0) if key == "weapon_chest" else None,
                             key)

    def test_a_chip_the_animator_set_is_left_alone(self):
        got = self.params({"weapon_chest_lag": ("offset", 100.0), "weapon_chest_r": ("offset", 1.0)})
        self.assertNotIn("weapon_chest", got)
        self.assertEqual(got["weapon_chest_r"], ("offset", 1.0))

    def test_nothing_stored_turns_nothing_on(self):
        self.assertEqual(self.params({}), {})
        self.assertNotIn("weapon_chest", self.params({"step": ("ratio", 1.2)}))

    def test_a_chip_the_animator_unticked_stays_off(self):
        """The card drops a change that is its parameter's default but pins the key either way, so an
        unticked chip is in `pins` with nothing in `changes` - and must not be migrated back on."""
        got = self.params({"weapon_chest_rotation": ("offset", -0.5)}, pins=["weapon_chest"])
        self.assertNotIn("weapon_chest", got)
        for key in ("weapon_chest_l", "weapon_chest_r"):
            self.assertNotIn("weapon_chest", self.params({"weapon_chest_lag": ("offset", 100.0)},
                                                         pins=[key]))


class Balance(unittest.TestCase):

    def test_the_carry_sees_the_pass(self):
        w = walk()
        base = w.evaluate({"elbow_add": 70.0, "arm_drag": 0.0}, weapons=WEAPON)
        got = w.evaluate({"elbow_add": 70.0, "arm_drag": 0.0, "weapon_chest": 1.0,
                          "weapon_chest_lag": 6.0}, weapons=WEAPON)
        a = np.asarray(base.worlds[w.index["pelvis"]], float)[:, 3, :3]
        b = np.asarray(got.worlds[w.index["pelvis"]], float)[:, 3, :3]
        self.assertGreater(float(np.abs(a - b).max()), 1e-9)


if __name__ == "__main__":
    unittest.main()
