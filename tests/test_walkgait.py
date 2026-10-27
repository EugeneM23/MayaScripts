"""maya_walk.gait - the parameters (2026-10-26): measured the same way on the clip and the result, mapped onto
the engine so a value asked reads back, stored as changes, linked to the physics, moved by macros - on the
synthetic walker of tests/test_walkmodel.py."""

import math
import unittest

import numpy as np

from tests import test_walkmodel as tw

wm = tw.wm
gait = tw.load("gait")


class MeasureTests(unittest.TestCase):

    def test_the_clip_reads_its_known_motion(self):
        w = tw.walk()
        m = gait.own(w)
        self.assertAlmostEqual(m["step"], 60.0, places=3)
        self.assertAlmostEqual(m["tempo"], 12.0, places=6)
        self.assertAlmostEqual(m["bounce"], 6.0, delta=0.05)       # 3 cos(2w + .3): 6 cm peak to peak
        self.assertAlmostEqual(m["sway"], 4.0, delta=0.05)         # 2 sin(w)
        self.assertAlmostEqual(m["surge"], 4.0, delta=0.05)        # 2 sin(2w)
        self.assertAlmostEqual(m["width"], 20.0, delta=0.5)        # the feet at +-10
        self.assertAlmostEqual(m["speed"], 1.5, places=6)

    def test_sided_keys_and_their_mean(self):
        m = gait.own(tw.walk())
        for name in ("arm_swing", "push", "knee_bend", "ground_time"):
            self.assertAlmostEqual(m[name], 0.5 * (m[name + "_l"] + m[name + "_r"]), places=9)

    def test_the_same_function_reads_a_result(self):
        w = tw.walk()
        r = w.evaluate(w.own_knobs())
        a, b = gait.own(w), gait.of_result(w, r)
        for name in ("step", "tempo", "bounce", "sway", "hips_twist", "arm_swing", "lean", "width", "ground_time",
                     "low_point", "arm_lag_l", "chest_twist"):
            self.assertAlmostEqual(a[name], b[name], delta=1e-3, msg=name)

    def test_a_low_point_is_read_from_the_nearest_strike(self):
        w = tw.walk()
        own = gait.own(w)
        self.assertLessEqual(abs(own["low_point"]), 50.0)


# (parameter, change asked): each inside what the synthetic walker reaches with no physics
READBACK = (("step", 6.0), ("tempo", 2.0), ("width", 4.0), ("bounce", -2.0), ("low_point", 10.0), ("lean", 8.0),
            ("arm_swing", 10.0), ("arm_lag", 2.0), ("sway", 2.0), ("surge", 1.5), ("hips_twist", 4.0),
            ("hip_drop", 2.0), ("chest_twist", 3.0), ("chest_sway", 2.0), ("chest_bounce", 2.0),
            ("head_motion", -4.0), ("elbow", 10.0), ("elbow_swing", 6.0), ("arm_out", 5.0), ("arms_forward", 8.0),
            ("toe_out", 8.0), ("ground_time", 4.0), ("push", 10.0), ("heel_strike", 8.0), ("foot_lift", 3.0),
            ("knee_bend", 8.0), ("height", -4.0), ("forward", 3.0), ("double_bounce", 2.0), ("elbow_lag", 2.0))


class ReadbackTests(unittest.TestCase):

    def test_own_values_give_the_clip(self):
        w, c = tw.walk(), tw.clip()
        own = gait.own(w)
        r = w.evaluate(gait.engine_knobs(w, own, own, pins=set(), physics=False))
        self.assertLess(float(np.abs(r.worlds - c.worlds).max()), 1e-4)

    def test_every_parameter_reads_back(self):
        w = tw.walk()
        own = gait.own(w)
        bad = []
        for name, delta in READBACK:
            want = own[name] + delta
            asked = dict(own, **{name: want})
            if gait.P[name].sided:
                for side in "lr":
                    asked[name + "_" + side] = own[name + "_" + side] + delta
            k = gait.engine_knobs(w, own, asked, pins={name}, physics=False)
            got = gait.of_result(w, w.evaluate(k))[name]
            if abs(got - want) > max(0.1 * abs(delta), 0.3):
                bad.append("%s: asked %.2f got %.2f (own %.2f)" % (name, want, got, own[name]))
        self.assertEqual(bad, [])

    def test_a_sided_value_moves_its_side(self):
        w = tw.walk()
        own = gait.own(w)
        k = gait.engine_knobs(w, own, dict(own, arm_swing_l=own["arm_swing_l"] + 10.0), pins={"arm_swing_l"},
                              physics=False)
        got = gait.of_result(w, w.evaluate(k))
        self.assertAlmostEqual(got["arm_swing_l"], own["arm_swing_l"] + 10.0, delta=1.0)
        self.assertAlmostEqual(got["arm_swing_r"], own["arm_swing_r"], delta=0.05)

    def test_a_pinned_sway_turns_the_balance_off_on_its_axis(self):
        w = tw.walk()
        own = gait.own(w)
        k = gait.engine_knobs(w, own, dict(own, sway=6.0), pins={"sway"})
        self.assertEqual(k["balance_sway"], 0.0)
        self.assertNotIn("balance_surge", k)
        self.assertNotIn("balance_sway", gait.engine_knobs(w, own, own, pins=set()))

    def test_physics_on_turns_the_helpers_on(self):
        w = tw.walk()
        own = gait.own(w)
        k = gait.engine_knobs(w, own, own, pins=set())
        self.assertEqual((k["foot_placement"], k["balance"], k["root_sway"]), (1.0, 1.0, 0.0))
        self.assertGreater(k["knee_soft"], 0.0)
        off = gait.engine_knobs(w, own, dict(own, whip=0.0), pins=set())
        self.assertEqual((off["arm_drag"], off["torso_drag"], off["head_drag"]), (0.0, 0.0, 0.0))

    def test_the_engine_knobs_are_the_engine_s(self):
        w = tw.walk()
        own = gait.own(w)
        wm.knobs(**gait.engine_knobs(w, own, own, pins=set()))          # no unknown knob, every value in range


class StorageTests(unittest.TestCase):

    def test_a_ratio_applies_to_another_cycle(self):
        c = gait.stored_change(gait.P["step"], 60.0, 72.0)
        self.assertEqual(c, ("ratio", 1.2))
        self.assertAlmostEqual(gait.apply_change(gait.P["step"], 50.0, c), 60.0)

    def test_a_quiet_amplitude_is_an_offset(self):
        self.assertEqual(gait.stored_change(gait.P["bounce"], 0.2, 3.0)[0], "offset")
        self.assertAlmostEqual(gait.apply_change(gait.P["bounce"], 0.2, ("offset", 2.8)), 3.0)

    def test_a_posture_is_an_offset(self):
        self.assertEqual(gait.stored_change(gait.P["lean"], 2.0, 10.0), ("offset", 8.0))

    def test_values_apply_the_changes(self):
        own = gait.own(tw.walk())
        v = gait.values(own, {"step": ("ratio", 1.1), "lean": ("offset", 5.0)}, pins={"step", "lean"})
        self.assertAlmostEqual(v["step"], own["step"] * 1.1)
        self.assertAlmostEqual(v["lean"], own["lean"] + 5.0)
        self.assertAlmostEqual(v["bounce"], own["bounce"])

    def test_a_both_change_moves_both_sides_and_a_side_change_one(self):
        own = gait.own(tw.walk())
        v = gait.values(own, {"arm_swing": ("ratio", 1.2), "elbow_l": ("offset", 10.0)}, pins={"arm_swing"})
        self.assertAlmostEqual(v["arm_swing_l"], own["arm_swing_l"] * 1.2)
        self.assertAlmostEqual(v["arm_swing_r"], own["arm_swing_r"] * 1.2)
        self.assertAlmostEqual(v["elbow_l"], own["elbow_l"] + 10.0)
        self.assertAlmostEqual(v["elbow_r"], own["elbow_r"])


class LinkTests(unittest.TestCase):

    def test_unpinned_arm_swing_follows_the_speed(self):
        own = {"arm_swing": 40.0, "speed": 1.4, "step": 70.0, "tempo": 15.0}
        v = gait.values(own, {"step": ("ratio", 1.3)}, pins=set(), macros={})
        self.assertGreater(v["arm_swing"], 40.0)
        held = gait.values(own, {"step": ("ratio", 1.3)}, pins={"arm_swing"}, macros={})
        self.assertAlmostEqual(held["arm_swing"], 40.0)

    def test_a_longer_step_pushes_off_and_strikes_further(self):
        own = {"push": 30.0, "heel_strike": 10.0, "step": 70.0, "tempo": 15.0}
        v = gait.values(own, {"step": ("ratio", 1.25)}, pins={"step"})
        self.assertAlmostEqual(v["push"], 30.0 + 0.25 * gait.PUSH_PER_STEP)
        self.assertAlmostEqual(v["heel_strike"], 10.0 + 0.25 * gait.HEEL_PER_STEP)


class MacroTests(unittest.TestCase):

    def test_weight_moves_its_parameters_and_back(self):
        own = gait.own(tw.walk())
        heavy = gait.values(own, {}, set(), {"weight": 1.0})
        self.assertAlmostEqual(heavy["bounce"], own["bounce"] * 1.6, places=6)
        self.assertAlmostEqual(heavy["low_point"], own["low_point"] + 8.0, places=6)
        self.assertEqual(gait.values(own, {}, set(), {"weight": 0.0}), gait.values(own, {}, set(), {}))

    def test_light_is_the_reverse_halved(self):
        own = gait.own(tw.walk())
        light = gait.values(own, {}, set(), {"weight": -1.0})
        self.assertAlmostEqual(light["bounce"], own["bounce"] * 1.6 ** -0.5, places=6)
        self.assertAlmostEqual(light["knee_bend"], own["knee_bend"] - 2.0, places=6)

    def test_a_hand_change_holds_under_a_macro(self):
        own = gait.own(tw.walk())
        v = gait.values(own, {"bounce": ("ratio", 0.5)}, {"bounce"}, {"weight": 1.0})
        self.assertAlmostEqual(v["bounce"], own["bounce"] * 0.5)

    def test_speed_keeps_the_walk_ratio(self):
        own = {"speed": 1.4, "step": 70.0, "tempo": 15.0}
        v = gait.values(own, {}, set(), {"speed": 2.0})
        self.assertAlmostEqual(v["step"] / own["step"], math.sqrt(2.0 / 1.4), places=6)
        self.assertAlmostEqual(v["tempo"] / own["tempo"], math.sqrt(1.4 / 2.0), places=6)

    def test_a_character_by_its_strength(self):
        own = gait.own(tw.walk())
        sad = gait.values(own, {}, set(), {}, "Sad", 1.0)
        half = gait.values(own, {}, set(), {}, "Sad", 0.5)
        self.assertAlmostEqual(sad["nod"], 15.0)
        self.assertAlmostEqual(half["nod"], 7.5)
        self.assertAlmostEqual(sad["tempo"], own["tempo"] * 1.12)
        self.assertEqual(gait.values(own, {}, set(), {}, "Natural", 1.0), gait.values(own, {}, set(), {}))

    def test_every_character_names_parameters(self):
        for name, effects in gait.CHARACTERS:
            for param, (kind, x) in effects.items():
                self.assertIn(param, gait.P, (name, param))
                self.assertIn(kind, ("ratio", "offset"))


class DiagnosisTests(unittest.TestCase):

    def test_arms_in_step(self):
        found = gait.diagnose({"arm_lag_l": 0.2, "arm_lag_r": -0.1, "ground_time": 60.0, "bounce": 4.0,
                               "push_l": 30.0, "push_r": 30.0, "chest_timing": 150.0})
        self.assertIn("arms_in_step", [f.key for f in found])
        fix = next(f for f in found if f.key == "arms_in_step").fix
        self.assertEqual(fix, {"arm_lag": 3.0})

    def test_a_flat_walk(self):
        found = gait.diagnose({"bounce": 1.0, "arm_lag_l": 3.0, "arm_lag_r": 3.0, "ground_time": 60.0,
                               "push_l": 30.0, "push_r": 30.0, "chest_timing": 150.0})
        self.assertIn("flat", [f.key for f in found])
        self.assertNotIn("arms_in_step", [f.key for f in found])

    def test_a_run_is_judged_as_one(self):
        found = gait.diagnose({"bounce": 1.0, "arm_lag_l": 0.0, "arm_lag_r": 0.0, "ground_time": 35.0,
                               "push_l": 30.0, "push_r": 30.0, "chest_timing": 150.0})
        self.assertNotIn("flat", [f.key for f in found])
        self.assertNotIn("arms_in_step", [f.key for f in found])

    def test_physics_giving_way_is_said(self):
        found = gait.diagnose({"ground_time": 60.0, "push_l": 30.0, "push_r": 30.0, "bounce": 4.0,
                               "arm_lag_l": 3.0, "arm_lag_r": 3.0, "chest_timing": 150.0}, info={"lowered": 4.0})
        self.assertIn("physics", [f.key for f in found])

    def test_no_tempo_is_told_for_a_body_standing_still(self):
        """2026-10-27, seen on 7002: an In place result measured 7.5e-18 m/s and the Froude tempo read 110 million
        frames a step («The tempo is not the body's: 15.5 fr a step, 35864562.6 for its size»)."""
        self.assertEqual(gait.froude_tempo(85.0, 30.0, 7.5e-18), 0.0)
        self.assertEqual(gait.froude_tempo(85.0, 30.0, 0.01), 0.0)
        self.assertGreater(gait.froude_tempo(85.0, 30.0, 1.7), 5.0)
        found = gait.diagnose({"arm_lag_l": 3.0, "arm_lag_r": 3.0, "bounce": 4.0, "push_l": 30.0, "push_r": 30.0,
                               "chest_timing": 150.0, "ground_time": 60.0, "tempo": 15.5, "speed": 7.5e-18},
                              leg=85.0, fps=30.0)
        self.assertNotIn("tempo_size", [f.key for f in found])

    def test_an_in_place_result_reads_the_walk_s_speed_and_step(self):
        """In place takes the travel off the keys; the walk still walks at its speed and its step."""
        w = tw.walk()
        walking, standing = gait.of_result(w, w.evaluate({})), gait.of_result(w, w.evaluate({"in_place": 1.0}))
        self.assertGreater(walking["speed"], 1.0)
        self.assertAlmostEqual(standing["speed"], walking["speed"], places=6)
        self.assertAlmostEqual(standing["step"], walking["step"], places=6)

    def test_every_fix_names_parameters(self):
        found = gait.diagnose({"arm_lag_l": 0.0, "arm_lag_r": 0.0, "bounce": 1.0, "head_motion": 9.0,
                               "chest_timing": 30.0, "push_l": 2.0, "push_r": 2.0, "arm_swing_l": 40.0,
                               "arm_swing_r": 40.0, "hips_twist": -4.0, "knee_bend_l": 2.0, "knee_bend_r": 8.0,
                               "ground_time": 60.0, "tempo": 40.0, "speed": 1.4}, info={"lowered": 3.0},
                              leg=90.0, fps=30.0)
        self.assertGreaterEqual(len(found), 7)
        for f in found:
            for key in f.fix:
                gait.param_of(key)


class LegacyTests(unittest.TestCase):

    def test_a_version_2_memo(self):
        w = tw.walk()
        changes, pins, macros = gait.from_legacy(w, {"stride": 1.2, "bob": 1.5, "weight": 0.5, "overlap": 2})
        self.assertEqual(changes["step"], ("ratio", 1.2))
        self.assertEqual(changes["bounce"], ("ratio", 1.5))
        self.assertEqual(macros, {"weight": 0.5})
        self.assertEqual(changes["arm_lag"][0], "offset")
        self.assertAlmostEqual(changes["arm_lag"][1], 1.6)
        self.assertTrue({"step", "bounce", "arm_lag"} <= pins)

    def test_the_walk_s_own_knobs_translate_to_nothing(self):
        w = tw.walk()
        legacy = dict((k, wm.DEFAULTS[k]) for k in ("arm_drag", "torso_drag", "head_drag", "arm_bounce"))
        changes, pins, macros = gait.from_legacy(w, dict(w.own_knobs(), foot_placement=1.0, balance=1.0,
                                                         root_sway=0.0, **legacy))
        self.assertEqual(macros, {})
        self.assertEqual(changes, {})

    def test_legacy_twists_keep_their_degrees(self):
        w = tw.walk()
        own = gait.own(w)
        changes, _, _ = gait.from_legacy(w, {"pelvis_twist": 5.0, "stride": 1.0})
        self.assertAlmostEqual(own["hips_twist"] + changes["hips_twist"][1], w.twist_gain * 5.0, places=6)


class ReachTests(unittest.TestCase):
    """What a walk's own body reaches (2026-10-26, the read-back on real walks): an arm swings, an elbow
    straightens and a foot lowers only so far; a side's range comes from its own value."""

    def setUp(self):
        self.w = tw.walk()
        self.own = gait.own(self.w)

    def test_each_side_s_range_comes_from_its_own_value(self):
        rng = gait.ranges(self.own, self.w.leg_length, self.w)
        for s in gait.SIDES:
            lo, hi = rng["arm_lag_" + s]
            self.assertAlmostEqual(0.5 * (lo + hi), self.own["arm_lag_" + s], places=9)

    def test_an_arm_asked_past_its_widest_swing_stops_there(self):
        lo, hi = gait.reach(self.w, "arm_swing_l")
        self.assertIsNone(lo)
        self.assertGreater(hi, self.own["arm_swing_l"])
        g = gait._solved_gain(self.w, "arm", "l", hi + 50.0, 1.0, 3.0)
        self.assertAlmostEqual(gait._swing_of(self.w, "arm", "l", g, 1.0), hi, places=6)
        self.assertLessEqual(g, wm.RANGES["g_arm"][1])            # never past what the engine lets through

    def test_an_elbow_straightens_only_as_far_as_its_hinge_brings_it(self):
        lo, hi = gait.reach(self.w, "elbow_l")
        self.assertLess(lo, self.own["elbow_l"])
        x = gait._solved_elbow(self.w, "l", lo - 20.0, -40.0)
        self.assertAlmostEqual(gait._elbow_of(self.w, "l", x), lo, places=6)
        x = gait._solved_elbow(self.w, "l", self.own["elbow_l"] + 10.0, 10.0)
        self.assertAlmostEqual(gait._elbow_of(self.w, "l", x), self.own["elbow_l"] + 10.0, places=4)

    def test_a_foot_lowers_no_further_than_its_swing_takes(self):
        floor = gait.lift_floor(self.w, "l")
        self.assertGreaterEqual(floor, 0.0)
        self.assertLess(floor, self.own["foot_lift_l"])
        self.assertEqual(gait.reach(self.w, "foot_lift_l"), (floor, None))

    def test_the_hip_drop_s_take_through_the_twisted_pelvis(self):
        self.assertTrue(0.3 <= gait._list_take(self.w) <= 1.5)


if __name__ == "__main__":
    unittest.main()
