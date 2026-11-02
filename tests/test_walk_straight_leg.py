"""A straight stance leg at the passing phase (docs/superpowers/specs/2026-11-02-walk-straight-passing-leg-design.md):
the pure helpers, the lift, Leg stretch, and the parameters. numpy only, no Maya."""

import math
import unittest

import numpy as np

from tests import test_walkmodel as T

wm, walk, clip, load, L1, L2 = T.wm, T.walk, T.clip, T.load, T.L1, T.L2

gait = load("gait")


class HelperTests(unittest.TestCase):
    """straight_ratio / knee_bend_at / passing_share / smooth_under / lift_to."""

    def test_a_bend_and_its_ratio_round_trip(self):
        for bend in (0.0, 2.5, 5.0, 12.0, 30.0, 90.0):
            r = wm.straight_ratio(bend, L1, L2)
            self.assertAlmostEqual(wm.knee_bend_at(r, L1, L2), bend, places=6)

    def test_a_straight_knee_is_the_whole_leg(self):
        self.assertAlmostEqual(wm.straight_ratio(0.0, L1, L2), 1.0, places=12)
        self.assertAlmostEqual(wm.knee_bend_at(1.0, L1, L2), 0.0, places=6)

    def test_a_straighter_knee_is_a_longer_leg(self):
        self.assertGreater(wm.straight_ratio(5.0, L1, L2), wm.straight_ratio(20.0, L1, L2))

    def test_five_degrees_is_a_centimetre_of_hip_on_an_eighty_six_cm_leg(self):
        # the lever the whole feature rests on (the spec's finding 2): near straight the knee is a square root
        # of its reach, so a centimetre of hip is fifteen degrees of knee
        l1 = l2 = 42.8
        d20 = wm.straight_ratio(20.0, l1, l2) * (l1 + l2)
        d5 = wm.straight_ratio(5.0, l1, l2) * (l1 + l2)
        self.assertAlmostEqual(d5 - d20, 1.24, places=1)

    def test_the_window_is_zero_at_the_strike_and_the_lift_off(self):
        self.assertEqual(wm.passing_share(0.0, 10.0), 0.0)
        self.assertEqual(wm.passing_share(10.0, 10.0), 0.0)
        self.assertEqual(wm.passing_share(-1.0, 10.0), 0.0)
        self.assertEqual(wm.passing_share(11.0, 10.0), 0.0)

    def test_the_window_is_whole_across_the_middle(self):
        self.assertAlmostEqual(wm.passing_share(5.0, 10.0), 1.0, places=12)
        self.assertAlmostEqual(wm.passing_share(4.0, 10.0), 1.0, places=12)
        self.assertAlmostEqual(wm.passing_share(6.0, 10.0), 1.0, places=12)

    def test_the_window_rises_and_falls_smoothly(self):
        xs = np.linspace(0.0, 10.0, 201)
        ys = np.array([wm.passing_share(x, 10.0) for x in xs])
        self.assertTrue(np.all(np.diff(ys[:60]) >= -1e-12))      # in
        self.assertTrue(np.all(np.diff(ys[-60:]) <= 1e-12))      # out
        self.assertLess(float(np.abs(np.diff(ys)).max()), 0.05)  # no step

    def test_the_window_of_a_contact_too_short_to_have_a_middle(self):
        self.assertEqual(wm.passing_share(0.0, 0.0), 0.0)
        self.assertGreaterEqual(wm.passing_share(0.5, 1.0), 0.0)

    def test_smooth_under_lies_under_its_room(self):
        rng = np.random.default_rng(5)
        for _ in range(20):
            room = np.abs(rng.normal(size=31)) * 3.0
            out = wm.smooth_under(room, room, 0.5)
            self.assertEqual(len(out), 31)
            self.assertTrue(np.all(out <= room + 1e-9))
            self.assertTrue(np.all(out >= -1e-12))

    def test_smooth_under_is_zero_where_the_room_is_zero(self):
        room = np.ones(30) * 4.0
        room[10] = 0.0
        out = wm.smooth_under(room, room, 1.0)
        self.assertEqual(out[10], 0.0)
        self.assertAlmostEqual(out[11], 1.0, places=9)    # its neighbours give way at the rate
        self.assertAlmostEqual(out[12], 2.0, places=9)
        self.assertEqual(out[20], 4.0)                    # far away it keeps the room whole

    def test_smooth_under_ramps_where_a_clamp_would_step(self):
        room = np.zeros(40) + 0.2
        room[12:28] = 5.0                      # a square room: a clamped curve steps 4.8 cm in one frame
        out = wm.smooth_under(room, room, 0.6)
        self.assertTrue(np.all(out <= room + 1e-9))
        self.assertAlmostEqual(out[20], 5.0, places=9)    # the middle of the room is used whole
        step = float(np.abs(np.diff(out, prepend=out[-1])).max())
        self.assertLessEqual(step, 0.6 + 1e-9)            # and it moves at the rate, never faster
        ramp = int(np.sum((out > 0.3) & (out < 4.9)))
        self.assertGreaterEqual(ramp, 12)                 # it ramps over several frames, on both sides

    def test_smooth_under_aims_at_its_need_not_its_room(self):
        room = np.zeros(30) + 9.0
        need = np.zeros(30)
        need[14:17] = 2.0
        out = wm.smooth_under(need, room, 1.0)
        self.assertTrue(np.all(out <= need + 1e-9))
        self.assertAlmostEqual(out[15], 2.0, places=9)
        self.assertEqual(out[0], 0.0)

    def test_smooth_under_is_periodic(self):
        room = np.zeros(24) + 1.0
        room[0] = 0.0
        out = wm.smooth_under(room, room, 0.4)
        self.assertAlmostEqual(out[23], 0.4, places=9)    # the frame before the gap gives way, the wrap counted
        self.assertAlmostEqual(out[1], 0.4, places=9)

    def test_smooth_under_of_nothing(self):
        self.assertEqual(len(wm.smooth_under(np.zeros(0), np.zeros(0), 0.5)), 0)
        self.assertTrue(np.all(wm.smooth_under(np.zeros(10), np.zeros(10), 0.5) == 0.0))

    def test_the_lift_that_reaches_a_target(self):
        up = np.array([0.0, 1.0, 0.0])
        q = np.array([0.0, -80.0, 0.0])        # the ankle 80 cm under the hip
        self.assertAlmostEqual(wm.lift_to(q, up, 85.0), 5.0, places=9)
        self.assertAlmostEqual(wm.lift_to(q, up, 80.0), 0.0, places=9)
        # a target shorter than the leg stands: the hip must come down (a negative lift)
        self.assertLess(wm.lift_to(q, up, 70.0), 0.0)

    def test_the_lift_with_the_ankle_aside(self):
        up = np.array([0.0, 1.0, 0.0])
        q = np.array([0.0, -60.0, 40.0])       # 72.111 cm away, 40 of it along the walk
        x = wm.lift_to(q, up, 80.0)
        self.assertAlmostEqual(float(np.linalg.norm(q - x * up)), 80.0, places=9)
        self.assertGreater(x, 0.0)

    def test_no_lift_reaches_a_target_shorter_than_the_ankle_is_aside(self):
        up = np.array([0.0, 1.0, 0.0])
        q = np.array([0.0, -10.0, 40.0])
        self.assertIsNone(wm.lift_to(q, up, 30.0))


def knees(w, worlds, side):
    """(n,) the knee's bend a frame, degrees (0 straight), read off the worlds."""
    n = worlds.shape[1] - 1
    h = worlds[w.index["thigh_" + side], :n, 3, :3]
    k = worlds[w.index["calf_" + side], :n, 3, :3]
    a = worlds[w.index["foot_" + side], :n, 3, :3]
    u = (k - h) / np.linalg.norm(k - h, axis=1)[:, None]
    v = (a - k) / np.linalg.norm(a - k, axis=1)[:, None]
    return np.degrees(np.arccos(np.clip(np.sum(u * v, axis=1), -1.0, 1.0)))


def passings(w, res):
    """{side: [frames]} - the frames a planted foot's own passing falls on (the other ankle crossing it along
    the travel), by the result's own planted mask."""
    n = res.frames
    planted = (res.info.get("placement") or {}).get("planted") or {}
    along = dict((s, res.worlds[w.index["foot_" + s], :n, 3, :3] @ w.basis[0]) for s in ("l", "r"))
    d = along["l"] - along["r"]
    out = {"l": [], "r": []}
    for f in range(n):
        g = (f + 1) % n
        if d[f] == 0.0 or (d[f] < 0.0) != (d[g] < 0.0):
            for s in ("l", "r"):
                if not planted or planted[s][f]:
                    out[s].append(f)
    return out


def at_passing(w, res, side=None):
    """The stance knee's bend at the passing frames (the mean over both sides unless one is named)."""
    pf = passings(w, res)
    out = []
    for s in (("l", "r") if side is None else (side,)):
        bend = knees(w, res.worlds, s)
        out.extend(float(bend[f]) for f in pf[s])
    return float(np.mean(out)) if out else 0.0


def defaults(w):
    own = gait.own(w)
    return gait.engine_knobs(w, own, gait.values(own, {}))


def foot_track(w, res, side):
    n = res.frames
    return res.worlds[w.index["foot_" + side], :n, 3, :3].copy()


class LiftTests(unittest.TestCase):
    """Passing knee: the hips lifted at the stance's middle, under a cap that gives way there only."""

    def setUp(self):
        self.w = walk()
        self.k = defaults(self.w)
        self.plain = self.w.evaluate(self.k)
        self.own = at_passing(self.w, self.plain)

    def test_the_synthetic_walker_passes_on_a_bent_knee(self):
        self.assertGreater(self.own, 60.0)          # the fixture is a crouched walker: ~72 deg

    def test_nothing_asked_changes_nothing(self):
        off = self.w.evaluate(dict(self.k, passing_knee=0.0))
        self.assertTrue(np.array_equal(off.worlds, self.plain.worlds))
        self.assertNotIn("passing", off.info)

    def test_an_ask_no_straighter_than_the_cycle_changes_nothing(self):
        same = self.w.evaluate(dict(self.k, passing_knee=self.own + 10.0))
        self.assertTrue(np.array_equal(same.worlds, self.plain.worlds))

    def test_the_passing_knee_reaches_the_ask(self):
        asked = self.own - 8.0
        res = self.w.evaluate(dict(self.k, passing_knee=asked))
        self.assertAlmostEqual(at_passing(self.w, res), asked, delta=1.0)

    def test_it_straightens_the_middle_of_the_stance_and_not_its_ends(self):
        asked = self.own - 8.0
        res = self.w.evaluate(dict(self.k, passing_knee=asked))
        for s in ("l", "r"):
            before, after = knees(self.w, self.plain.worlds, s), knees(self.w, res.worlds, s)
            for hs, to in self.w.contact[s]:
                f = int(round(hs)) % res.frames
                self.assertLess(abs(after[f] - before[f]), 2.5,
                                "%s strike at %d moved %.2f deg" % (s, f, after[f] - before[f]))

    def test_no_planted_foot_slides(self):
        res = self.w.evaluate(dict(self.k, passing_knee=self.own - 8.0))
        planted = (res.info.get("placement") or {}).get("planted") or {}
        for s in ("l", "r"):
            now, before = foot_track(self.w, res, s), foot_track(self.w, self.plain, s)
            on = np.array(planted[s], bool) if planted else np.ones(len(now), bool)
            moved = np.abs(now[on] - before[on]).max()
            self.assertLess(float(moved), 1e-6, "%s foot moved %.6f cm while planted" % (s, moved))

    def test_the_hips_rise_at_the_passing_and_the_loop_closes(self):
        res = self.w.evaluate(dict(self.k, passing_knee=self.own - 8.0))
        up = self.w.up
        pelvis = res.worlds[self.w.index["pelvis"], :, 3, :3] @ up
        was = self.plain.worlds[self.w.index["pelvis"], :, 3, :3] @ up
        pf = passings(self.w, res)
        for s in ("l", "r"):
            for f in pf[s]:
                self.assertGreater(pelvis[f] - was[f], 1.0, "frame %d rose %.2f cm" % (f, pelvis[f] - was[f]))
        self.assertAlmostEqual(pelvis[res.frames], pelvis[0], places=9)

    def test_the_lift_is_nothing_at_the_double_supports(self):
        res = self.w.evaluate(dict(self.k, passing_knee=self.own - 8.0))
        drop = np.array(res.info["drop"][:res.frames])
        base = np.array(self.plain.info["drop"][:res.frames])
        lift = base - drop
        planted = (res.info.get("placement") or {}).get("planted") or {}
        if planted:
            both = [f for f in range(res.frames) if planted["l"][f] and planted["r"][f]]
            self.assertTrue(both)
            # the lift lives at the passing: at a double support the other leg stands at its own limit and
            # leaves almost nothing (what little it leaves is the room's, and the slide test holds it there)
            self.assertLess(float(np.abs(lift[both]).max()), 0.25 * float(lift.max()))

    def test_it_says_what_it_did(self):
        asked = self.own - 8.0
        res = self.w.evaluate(dict(self.k, passing_knee=asked))
        p = res.info["passing"]
        self.assertAlmostEqual(p["asked"]["l"], asked, places=6)
        self.assertAlmostEqual(p["got"]["l"], asked, delta=1.0)
        self.assertGreater(p["lift"], 1.0)
        self.assertLess(p["short"]["l"], 0.5)

    def test_one_side_alone(self):
        asked = self.own - 8.0
        res = self.w.evaluate(dict(self.k, passing_knee_l=asked))
        self.assertAlmostEqual(at_passing(self.w, res, "l"), asked, delta=1.5)
        self.assertGreater(at_passing(self.w, res, "r"), asked + 5.0)

    def test_an_ask_the_legs_cannot_reach_is_named(self):
        res = self.w.evaluate(dict(self.k, passing_knee=1.0))
        p = res.info["passing"]
        self.assertGreater(p["short"]["l"], 0.5)       # the legs ran out of room
        self.assertLess(p["lift"], wm.STRAIGHT_LIFT_MAX + 1e-9)
        self.assertGreater(p["got"]["l"], 1.0)


if __name__ == "__main__":
    unittest.main()
