"""A straight stance leg at the passing phase (docs/superpowers/specs/2026-11-02-walk-straight-passing-leg-design.md):
the pure helpers, the lift, Leg stretch, and the parameters. numpy only, no Maya."""

import math
import unittest

import numpy as np

from tests import test_walkmodel as T
from tests.test_walktarget import statics_of, target_of

wt = __import__("maya_walk.target", fromlist=["target"])   # mayapy: target.py needs OpenMaya

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


def ask(k, deg, side=None):
    """The engine knobs `k` with Passing knee asked. Both sides by name: engine_knobs writes every sided knob's
    own `_l` and `_r`, and a side's own value wins over the plain one (trap 317)."""
    if side is not None:
        return dict(k, **{"passing_knee_" + side: deg})
    return dict(k, passing_knee_l=deg, passing_knee_r=deg)


def foot_track(w, res, side):
    n = res.frames
    return res.worlds[w.index["foot_" + side], :n, 3, :3].copy()


#  The fixture is a 24-frame walker whose hips bob 1.55 cm a frame, so the lift's rate (STRAIGHT_SHARE of
#  that) is what bounds it: it lands an ask up to 7 deg straighter than its own and reports the rest short.
#  A real cycle's hips move 1.7-7 cm a frame and land every ask the legs allow exactly (asd's 8 deg to 1e-14,
#  verify_walk_straight_leg.py) - a fixture more degenerate than the data (trap 321), so the ask here is 6.
ASK_DEG = 6.0


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
        off = self.w.evaluate(ask(self.k, 0.0))
        self.assertTrue(np.array_equal(off.worlds, self.plain.worlds))
        self.assertNotIn("passing", off.info)

    def test_an_ask_no_straighter_than_the_cycle_changes_nothing(self):
        same = self.w.evaluate(ask(self.k, self.own + 10.0))
        self.assertTrue(np.array_equal(same.worlds, self.plain.worlds))

    def test_the_passing_knee_reaches_the_ask(self):
        asked = self.own - ASK_DEG
        res = self.w.evaluate(ask(self.k, asked))
        self.assertAlmostEqual(at_passing(self.w, res), asked, delta=1.0)

    def test_it_straightens_the_middle_of_the_stance_and_not_its_ends(self):
        asked = self.own - ASK_DEG
        res = self.w.evaluate(ask(self.k, asked))
        for s in ("l", "r"):
            before, after = knees(self.w, self.plain.worlds, s), knees(self.w, res.worlds, s)
            for hs, to in self.w.contact[s]:
                f = int(round(hs)) % res.frames
                self.assertLess(abs(after[f] - before[f]), 2.5,
                                "%s strike at %d moved %.2f deg" % (s, f, after[f] - before[f]))

    def test_no_planted_foot_slides(self):
        res = self.w.evaluate(ask(self.k, self.own - ASK_DEG))
        planted = (res.info.get("placement") or {}).get("planted") or {}
        for s in ("l", "r"):
            now, before = foot_track(self.w, res, s), foot_track(self.w, self.plain, s)
            on = np.array(planted[s], bool) if planted else np.ones(len(now), bool)
            moved = np.abs(now[on] - before[on]).max()
            self.assertLess(float(moved), 1e-6, "%s foot moved %.6f cm while planted" % (s, moved))

    def test_the_hips_rise_at_the_passing_and_the_loop_closes(self):
        res = self.w.evaluate(ask(self.k, self.own - ASK_DEG))
        up = self.w.up
        pelvis = res.worlds[self.w.index["pelvis"], :, 3, :3] @ up
        was = self.plain.worlds[self.w.index["pelvis"], :, 3, :3] @ up
        pf = passings(self.w, res)
        for s in ("l", "r"):
            for f in pf[s]:
                self.assertGreater(pelvis[f] - was[f], 1.0, "frame %d rose %.2f cm" % (f, pelvis[f] - was[f]))
        self.assertAlmostEqual(pelvis[res.frames], pelvis[0], places=9)

    def test_the_lift_is_nothing_at_the_double_supports(self):
        res = self.w.evaluate(ask(self.k, self.own - ASK_DEG))
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
        asked = self.own - ASK_DEG
        res = self.w.evaluate(ask(self.k, asked))
        p = res.info["passing"]
        self.assertAlmostEqual(p["asked"]["l"], asked, places=6)
        self.assertAlmostEqual(p["got"]["l"], asked, delta=1.0)
        self.assertGreater(p["lift"], 1.0)
        self.assertLess(p["short"]["l"], 0.5)

    def test_the_model_s_own_line_says_it_too(self):
        """model.describe - what a caller that does not build the card's compact line reads."""
        asked = self.own - ASK_DEG
        text = wm.describe(self.w.evaluate(ask(self.k, asked)))
        self.assertIn("the passing knee", text)
        self.assertIn("asked %.0f" % asked, text)
        self.assertIn("higher there", text)
        far = wm.describe(self.w.evaluate(ask(self.k, 1.0)))
        self.assertIn("a shorter Step gives the rest", far)      # the legs ran out: the animator's own lever
        self.assertNotIn("a shorter Step", text)

    def test_one_side_alone(self):
        asked = self.own - ASK_DEG
        res = self.w.evaluate(ask(self.k, asked, 'l'))
        self.assertAlmostEqual(at_passing(self.w, res, "l"), asked, delta=1.5)
        self.assertGreater(at_passing(self.w, res, "r"), asked + 5.0)

    def test_an_ask_the_rate_cannot_serve_is_named_and_the_rate_is_why(self):
        """The fixture's hips barely bob, so an ask past ASK_DEG falls short of its own accord: it is reported,
        and lifting the rate lands it exactly - which is the control that pins the arithmetic under it."""
        asked = self.own - 15.0
        res = self.w.evaluate(ask(self.k, asked))
        p = res.info["passing"]
        self.assertGreater(p["short"]["l"], 1.0, "a bobless cycle landed a 15 deg ask: the rate does nothing")
        self.assertAlmostEqual(p["got"]["l"], at_passing(self.w, res), delta=0.5)   # it says what it did
        kept = wm.STRAIGHT_SHARE, wm.STRAIGHT_FLOOR
        try:
            wm.STRAIGHT_SHARE, wm.STRAIGHT_FLOOR = 100.0, 100.0
            free = self.w.evaluate(ask(self.k, asked))
        finally:
            wm.STRAIGHT_SHARE, wm.STRAIGHT_FLOOR = kept
        self.assertAlmostEqual(at_passing(self.w, free), asked, delta=0.1)
        self.assertLess(free.info["passing"]["short"]["l"], 0.1)
        self.assertGreater(free.info["passing"]["lift"], p["lift"])

    def test_an_ask_the_legs_cannot_reach_is_named(self):
        res = self.w.evaluate(ask(self.k, 1.0))
        p = res.info["passing"]
        self.assertGreater(p["short"]["l"], 0.5)       # the legs ran out of room
        self.assertLess(p["lift"], wm.STRAIGHT_LIFT_MAX + 1e-9)
        self.assertGreater(p["got"]["l"], 1.0)


class ParamTests(unittest.TestCase):
    """The parameter the card shows: its own value, its range, and what it hands the engine."""

    def setUp(self):
        self.w = walk()
        self.own = gait.own(self.w)

    def test_the_measure_reads_the_knee_at_the_passing(self):
        for side in ("l", "r"):
            self.assertIn("passing_knee_" + side, self.own)
        res = self.w.evaluate(defaults(self.w))
        got = gait.of_result(self.w, res)
        measured = at_passing(self.w, res)
        self.assertAlmostEqual(0.5 * (got["passing_knee_l"] + got["passing_knee_r"]), measured, delta=2.0)

    def test_it_is_not_the_straightest_a_planted_knee_gets(self):
        # the crouched fixture is straightest near its contacts, most bent at its passing
        self.assertGreater(self.own["passing_knee_l"], self.own["knee_bend_l"] + 5.0)

    def test_the_range_runs_from_one_degree_to_the_cycles_own(self):
        p, _ = gait.param_of("passing_knee_l")
        lo, hi = gait.ranges(self.own, self.w.leg_length, self.w)["passing_knee_l"]
        self.assertAlmostEqual(lo, 1.0, places=6)
        self.assertAlmostEqual(hi, self.own["passing_knee_l"], places=6)

    def test_untouched_it_asks_the_engine_nothing(self):
        e = gait.engine_knobs(self.w, self.own, gait.values(self.own, {}))
        self.assertEqual(e["passing_knee_l"], 0.0)
        self.assertEqual(e["passing_knee_r"], 0.0)

    def test_dialled_down_it_passes_the_ask_through(self):
        p, _ = gait.param_of("passing_knee_l")
        want = self.own["passing_knee_l"] - 10.0
        changes = {"passing_knee_l": gait.stored_change(p, self.own["passing_knee_l"], want)}
        e = gait.engine_knobs(self.w, self.own, gait.values(self.own, changes))
        self.assertAlmostEqual(e["passing_knee_l"], want, places=6)
        self.assertEqual(e["passing_knee_r"], 0.0)

    def test_dialled_up_it_asks_nothing(self):
        p, _ = gait.param_of("passing_knee_l")
        more = self.own["passing_knee_l"] + 10.0
        changes = {"passing_knee_l": gait.stored_change(p, self.own["passing_knee_l"], more)}
        e = gait.engine_knobs(self.w, self.own, gait.values(self.own, changes))
        self.assertEqual(e["passing_knee_l"], 0.0)

    def test_a_change_means_the_same_on_another_cycle(self):
        p, _ = gait.param_of("passing_knee_l")
        change = gait.stored_change(p, 22.0, 8.0)
        self.assertAlmostEqual(gait.apply_change(p, 30.0, change), 16.0, places=6)   # an offset, not a ratio

    def test_the_diagnosis_names_a_bent_passing_knee(self):
        m = dict(self.own, passing_knee_l=24.0, passing_knee_r=23.0)
        found = dict((f.key, f) for f in gait.diagnose(m, self.own, {}, run=False, leg=self.w.leg_length))
        self.assertIn("bent_passing", found)
        self.assertAlmostEqual(found["bent_passing"].fix["passing_knee"], 8.0, places=6)

    def test_the_diagnosis_leaves_a_run_alone(self):
        m = dict(self.own, passing_knee_l=60.0, passing_knee_r=60.0)
        found = [f.key for f in gait.diagnose(m, self.own, {}, run=True, leg=self.w.leg_length)]
        self.assertNotIn("bent_passing", found)

    def test_the_diagnosis_is_silent_about_a_knee_the_animator_asked_for(self):
        m = dict(self.own, passing_knee_l=5.0, passing_knee_r=5.0, knee_bend_l=4.0, knee_bend_r=4.0)
        info = {"passing": {"asked": {"l": 5.0, "r": 5.0}}}
        found = [f.key for f in gait.diagnose(m, self.own, info, run=False, leg=self.w.leg_length)]
        self.assertNotIn("straight_knee", found)
        self.assertNotIn("bent_passing", found)

    def test_the_line_says_what_it_did(self):
        res = self.w.evaluate(ask(defaults(self.w), self.own["passing_knee_l"] - 8.0))
        text = wm.describe(res)
        self.assertIn("the passing knee", text)
        self.assertIn("the hips up to", text)


if __name__ == "__main__":
    unittest.main()


class TargetTests(unittest.TestCase):
    """The retarget's own reach cap takes the ask too, or it lowers the hips back onto the clip's own ratio and
    the knee bends again - 14 deg for an 8 deg ask, measured on asd over a Manny skeleton (2026-11-02)."""

    def rig(self, scale=1.0):
        c = T.clip()
        w = T.walk()
        return w, c, wt.Retarget(w, statics_of(c), target_of(c, scale=scale))

    def asked(self, w, deg):
        return w.evaluate(ask(defaults(w), deg))

    def straighter_than_the_clip(self, w, rt, by=5.0):
        """An ask `by` degrees straighter than the clip's own straightest - the only kind that raises the cap
        (its own straightest IS the cap). The fixture never comes within 45 deg of straight, so an ask read
        off its passing knee is still more bent than its cap and raises nothing."""
        l1, l2 = rt.lengths["l"]
        return max(0.0, wm.knee_bend_at(w.reach["l"], l1, l2) - by)

    def test_with_nothing_asked_the_cap_is_the_clip_s_own(self):
        w, _, rt = self.rig()
        rt.frames(w.evaluate(defaults(w)))
        self.assertEqual(rt.straight, {})
        for side in ("l", "r"):
            self.assertAlmostEqual(rt._reach_ratio(side), w.reach[side], places=12)

    def test_an_ask_raises_the_cap_to_what_that_knee_needs(self):
        w, _, rt = self.rig()
        deg = self.straighter_than_the_clip(w, rt)
        rt.frames(self.asked(w, deg))
        for side in ("l", "r"):
            l1, l2 = rt.lengths[side]
            want = wm.straight_ratio(deg, l1, l2)
            self.assertAlmostEqual(rt.straight[side], want, places=12)
            self.assertAlmostEqual(rt._reach_ratio(side), max(w.reach[side], want), places=12)
            self.assertGreater(rt._reach_ratio(side), w.reach[side])

    def test_an_ask_the_clip_is_already_straighter_than_raises_nothing(self):
        w, _, rt = self.rig()
        rt.frames(self.asked(w, at_passing(w, w.evaluate(defaults(w))) - ASK_DEG))
        for side in ("l", "r"):
            self.assertLess(rt.straight[side], w.reach[side])        # the clip's own cap is the straighter one
            self.assertAlmostEqual(rt._reach_ratio(side), w.reach[side], places=12)

    def test_the_cap_is_read_in_the_target_s_own_lengths(self):
        """The ask is a knee ANGLE: a smaller body wants the same bend at its own hip-to-ankle distance."""
        w, _, small = self.rig(scale=0.6)
        deg = self.straighter_than_the_clip(w, small)
        small.frames(self.asked(w, deg))
        for side in ("l", "r"):
            l1, l2 = small.lengths[side]
            self.assertAlmostEqual(small.straight[side], wm.straight_ratio(deg, l1, l2), places=12)
            self.assertGreater(sum(small.lengths[side]), 0.0)

    def test_the_target_keeps_the_straightened_hips_where_the_model_put_them(self):
        w, _, rt = self.rig()
        res = self.asked(w, self.straighter_than_the_clip(w, rt))
        frames, info = rt.frames(res)
        self.assertLess(max(info["drop"]), 0.05, "the target lowered the hips it was handed")
        got = min(min(knees(w, res.worlds, side)) for side in ("l", "r"))
        scene = min(min(_scene_bends(w, frames, side)) for side in ("l", "r"))
        self.assertLess(abs(scene - got), 0.5, "model %.2f, target %.2f" % (got, scene))

    #  The control - the cap left at the clip's own ratio, which pulls the hips back down and bends the knee
    #  again - lives in verify_walk_straight_leg.py's target phase: it needs a cycle whose rate lets the model
    #  reach the raised cap, and the fixture's hips bob too little (measured on asd over a Manny skeleton: the
    #  target's drop 0.455 cm and the knee 14 deg for an 8 deg ask, against 0.007 cm and 8.00 with the raise).


def _outs_goals(rt, res):
    """The retarget's own per-frame target worlds and foot goals, as frames() builds them."""
    outs, goals = [], []
    first = rt._bones(res.worlds[:, 0])
    for f in range(res.frames):
        src = rt._bones(res.worlds[:, f])
        root_world = rt.transfer.travel(src, first) * rt.place
        outs.append(rt.transfer.frame(source=src, target=rt.target, root_world=root_world))
        source_root = rt.transfer._source_root_pose(src)
        goals.append(dict((s, rt._mapped(res.worlds[rt.walk.index["foot_" + s], f, 3, :3], source_root,
                                         root_world)) for s in ("l", "r")))
    return outs, goals


def _scene_bends(w, frames, side):
    """The target's own knee bend a frame, degrees, off the frames the retarget wrote."""
    out = []
    for f in frames[:-1]:
        p = [np.array(list(f[b + "_" + side])).reshape(4, 4)[3, :3] for b in ("thigh", "calf", "foot")]
        u, v = p[1] - p[0], p[2] - p[1]
        u, v = u / np.linalg.norm(u), v / np.linalg.norm(v)
        out.append(math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(u, v)))))))
    return out


#  The fixture at rest passes on a 45 deg knee - far from the lock, where a centimetre of hip is a degree of
#  knee and nothing can go wrong. Its hips raised PACE_HEIGHT cm, its planted legs stand near their reach, and
#  an ask at the lock is where the knee's own degrees and the hip's centimetres part company (the animator's
#  own walk: its left knee turned 14 deg a frame where its own cycle turns 9; 2026-11-02)
PACE_HEIGHT = 8.0


def planted_steps(w, res, side):
    """[|d bend| a frame] over the frames this foot is planted at both ends of the step, degrees."""
    n = res.frames
    bend = knees(w, res.worlds, side)
    pl = (res.info.get("placement") or {}).get("planted") or {}
    on = np.array(pl[side], bool) if pl else np.ones(n, bool)
    return [abs(float(bend[(f + 1) % n] - bend[f])) for f in range(n)
            if on[f] and on[(f + 1) % n]]


class PaceTests(unittest.TestCase):
    """The lift is paced in the KNEE's own degrees, not the hip's centimetres (trap 266)."""

    def setUp(self):
        self.w = walk()
        self.k = dict(defaults(self.w), pelvis_height=PACE_HEIGHT)
        self.plain = self.w.evaluate(self.k)
        self.own = max(max(planted_steps(self.w, self.plain, s)) for s in ("l", "r"))

    def test_the_fixture_s_own_planted_knee_turns_evenly(self):
        self.assertLess(self.own, 6.0)                       # ~4.2 deg a frame: the cycle's own pace

    def test_an_ask_at_the_lock_turns_the_knee_no_faster_than_the_cycle_does(self):
        res = self.w.evaluate(ask(self.k, 1.0))
        for side in ("l", "r"):
            worst = max(planted_steps(self.w, res, side))
            self.assertLess(worst, 1.4 * self.own,
                            "%s: %.2f deg a frame against the cycle's own %.2f" % (side, worst, self.own))

    def test_an_ask_at_the_lock_still_straightens_the_knee(self):
        res = self.w.evaluate(ask(self.k, 1.0))
        self.assertLess(at_passing(self.w, res), at_passing(self.w, self.plain) - 2.0)

    def test_the_pace_is_what_held_it_and_the_line_says_so(self):
        """Two shortfalls with two cures, and the line says which: the legs' reach (shorten the Step) and the
        knee's own pace. The fixture's hips are raised so its legs stand near their reach - a modest ask then
        lands, and only the pace keeps it from landing whole."""
        k = dict(defaults(self.w), pelvis_height=24.0)
        own = at_passing(self.w, self.w.evaluate(k))
        res = self.w.evaluate(ask(k, own - 6.0))
        p = res.info["passing"]
        self.assertGreater(max(p["paced"].values()), 1.0)
        self.assertAlmostEqual(max(p["paced"].values()), max(p["short"].values()), delta=0.5)
        self.assertIn("the pace held it", wm.describe(res))
        kept = wm.STRAIGHT_DEG_SHARE
        try:
            wm.STRAIGHT_DEG_SHARE = 100.0          # the pace out of the way: the ask lands
            free = self.w.evaluate(ask(k, own - 6.0))
        finally:
            wm.STRAIGHT_DEG_SHARE = kept
        self.assertLess(at_passing(self.w, free), at_passing(self.w, res))
        self.assertNotIn("the pace held it", wm.describe(free))

    def test_it_still_lands_an_ask_the_legs_allow(self):
        own = at_passing(self.w, self.plain)
        res = self.w.evaluate(ask(self.k, own - 3.0))
        self.assertAlmostEqual(at_passing(self.w, res), own - 3.0, delta=1.0)
