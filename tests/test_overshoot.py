"""The pure half of maya_overshoot: shapes, and the key plan.

Everything here runs without a Maya session. The shape tests check the key
table against the closed form it is derived from, which is the whole argument
for keying four frames instead of baking sixty.
"""

import math
import unittest

import maya_overshoot as mo


def numeric_slope(fn, u, h=1e-6):
    return (fn(u + h) - fn(u - h)) / (2.0 * h)


class TestSpringExtremes(unittest.TestCase):

    def test_one_turning_point_per_swing_plus_the_landing(self):
        for swings in (1, 2, 3, 6):
            ext = mo.spring_extremes(swings, 0.3)
            self.assertEqual(len(ext), swings + 1, swings)

    def test_it_starts_at_the_extreme(self):
        u, v = mo.spring_extremes(3, 0.3)[0]
        self.assertEqual(u, 0.0)
        self.assertEqual(v, 1.0)

    def test_the_turning_points_are_evenly_spaced(self):
        us = [u for u, _ in mo.spring_extremes(4, 0.3)]
        self.assertEqual(us, [0.0, 0.25, 0.5, 0.75, 1.0])

    def test_the_swings_alternate_sides(self):
        vals = [v for _, v in mo.spring_extremes(5, 0.4)]
        for a, b in zip(vals, vals[1:]):
            self.assertLess(a * b, 0.0, vals)

    def test_each_swing_keeps_the_ratio_of_the_last(self):
        vals = [v for _, v in mo.spring_extremes(4, 0.3)]
        for a, b in zip(vals, vals[1:]):
            self.assertAlmostEqual(abs(b) / abs(a), 0.3, places=12)

    def test_ratio_one_never_decays(self):
        vals = [abs(v) for _, v in mo.spring_extremes(3, 1.0)]
        self.assertEqual(vals, [1.0, 1.0, 1.0, 1.0])


class TestSpringClosedForm(unittest.TestCase):
    """f(u) = e^-ku (cos(pi c u) + k/(pi c) sin(pi c u)), k = -c ln r."""

    def test_it_starts_at_one(self):
        self.assertAlmostEqual(mo.spring_value(0.0, 3, 0.3), 1.0, places=12)

    def test_it_leaves_the_extreme_with_no_velocity(self):
        for swings, ratio in ((1, 0.3), (3, 0.3), (6, 0.6)):
            slope = numeric_slope(lambda u: mo.spring_value(u, swings, ratio), 0.0)
            self.assertAlmostEqual(slope, 0.0, places=5, msg=(swings, ratio))

    def test_the_key_table_lands_on_the_closed_form(self):
        for swings, ratio in ((1, 0.3), (2, 0.15), (3, 0.3), (6, 0.6)):
            for u, v in mo.spring_extremes(swings, ratio):
                self.assertAlmostEqual(mo.spring_value(u, swings, ratio), v,
                                       places=10, msg=(swings, ratio, u))

    def test_the_closed_form_turns_only_at_those_points(self):
        swings, ratio = 3, 0.3
        turns = []
        prev = numeric_slope(lambda u: mo.spring_value(u, swings, ratio), 0.005)
        u = 0.005
        while u < 0.995:
            u += 0.005
            cur = numeric_slope(lambda x: mo.spring_value(x, swings, ratio), u)
            if cur == 0.0 or (cur < 0) != (prev < 0):
                turns.append(u)
            prev = cur
        self.assertEqual(len(turns), 2, turns)       # 1/3 and 2/3
        self.assertAlmostEqual(turns[0], 1.0 / 3.0, places=2)
        self.assertAlmostEqual(turns[1], 2.0 / 3.0, places=2)

    def test_it_is_monotone_between_turning_points(self):
        swings, ratio = 3, 0.3
        for i in range(swings):
            a, b = i / 3.0, (i + 1) / 3.0
            samples = [mo.spring_value(a + (b - a) * j / 40.0, swings, ratio)
                       for j in range(41)]
            deltas = [y - x for x, y in zip(samples, samples[1:])]
            self.assertTrue(all(d > 0 for d in deltas) or
                            all(d < 0 for d in deltas), (i, deltas[:5]))


class TestBounceExtremes(unittest.TestCase):

    def test_it_starts_at_the_apex_and_ends_on_the_pose(self):
        ext = mo.bounce_extremes(0.5)
        self.assertEqual(ext[0], (0.0, 1.0, "apex"))
        self.assertEqual(ext[-1][0], 1.0)
        self.assertEqual(ext[-1][1], 0.0)
        self.assertEqual(ext[-1][2], "contact")

    def test_apexes_and_contacts_alternate(self):
        kinds = [k for _, _, k in mo.bounce_extremes(0.5)]
        self.assertEqual(kinds[0], "apex")
        for a, b in zip(kinds, kinds[1:]):
            self.assertNotEqual(a, b, kinds)

    def test_every_apex_keeps_the_square_of_the_restitution(self):
        apex = [v for _, v, k in mo.bounce_extremes(0.5) if k == "apex"]
        for a, b in zip(apex, apex[1:]):
            self.assertAlmostEqual(b / a, 0.25, places=12)

    def test_the_contact_intervals_shrink_by_the_restitution(self):
        contacts = [u for u, _, k in mo.bounce_extremes(0.5) if k == "contact"]
        gaps = [b - a for a, b in zip(contacts, contacts[1:])]
        for a, b in zip(gaps, gaps[1:]):
            self.assertAlmostEqual(b / a, 0.5, places=10, msg=gaps)

    def test_it_never_crosses_the_pose(self):
        for e in (0.3, 0.5, 0.7):
            self.assertTrue(all(v >= 0.0 for _, v, _ in mo.bounce_extremes(e)))

    def test_a_livelier_ball_bounces_more_times(self):
        few = len(mo.bounce_extremes(0.3))
        many = len(mo.bounce_extremes(0.8))
        self.assertLess(few, many)

    def test_the_span_is_normalised(self):
        for e in (0.3, 0.5, 0.7):
            self.assertAlmostEqual(mo.bounce_extremes(e)[-1][0], 1.0, places=12)


class TestPlanRefusals(unittest.TestCase):

    def test_the_first_key_of_a_channel_has_nothing_to_overshoot(self):
        keys, note = mo.plan_overshoot(pose_time=10, pose_value=5.0,
                                       prev_time=None, prev_value=None)
        self.assertEqual(keys, [])
        self.assertIn("no previous key", note)

    def test_a_channel_that_did_not_move_is_skipped(self):
        keys, note = mo.plan_overshoot(pose_time=10, pose_value=5.0,
                                       prev_time=0, prev_value=5.0)
        self.assertEqual(keys, [])
        self.assertIn("no move", note)

    def test_a_pass_through_key_is_refused(self):
        keys, note = mo.plan_overshoot(pose_time=10, pose_value=100.0,
                                       prev_time=0, prev_value=0.0,
                                       next_time=20, next_value=200.0)
        self.assertEqual(keys, [])
        self.assertIn("not a stop", note)

    def test_a_reversal_is_a_stop(self):
        keys, _ = mo.plan_overshoot(pose_time=10, pose_value=100.0,
                                    prev_time=0, prev_value=0.0,
                                    next_time=30, next_value=20.0)
        self.assertTrue(keys)

    def test_a_hold_is_a_stop(self):
        keys, _ = mo.plan_overshoot(pose_time=10, pose_value=100.0,
                                    prev_time=0, prev_value=0.0,
                                    next_time=40, next_value=100.0)
        self.assertTrue(keys)

    def test_the_last_key_of_a_channel_is_a_stop(self):
        keys, _ = mo.plan_overshoot(pose_time=10, pose_value=100.0,
                                    prev_time=0, prev_value=0.0)
        self.assertTrue(keys)

    def test_no_room_before_the_next_key_is_refused(self):
        keys, note = mo.plan_overshoot(pose_time=10, pose_value=100.0,
                                       prev_time=0, prev_value=0.0,
                                       next_time=11, next_value=100.0)
        self.assertEqual(keys, [])
        self.assertIn("no room", note)


class TestPlanAmplitude(unittest.TestCase):

    def plan(self, **kw):
        base = dict(pose_time=20, pose_value=100.0, prev_time=10,
                    prev_value=0.0, amount=0.15, frames=12)
        base.update(kw)
        return mo.plan_overshoot(**base)

    def test_the_extreme_lands_on_the_selected_key(self):
        keys, _ = self.plan()
        peak = max(keys, key=lambda k: abs(k.value))
        self.assertEqual(peak.time, 20)

    def test_the_extreme_is_the_requested_share_of_the_move(self):
        keys, _ = self.plan()
        peak = max(keys, key=lambda k: abs(k.value))
        self.assertAlmostEqual(peak.value, 15.0, places=12)

    def test_amplitude_is_linear_in_the_amount(self):
        a = max(k.value for k in self.plan(amount=0.10)[0])
        b = max(k.value for k in self.plan(amount=0.30)[0])
        self.assertAlmostEqual(b / a, 3.0, places=12)

    def test_a_move_in_the_other_direction_overshoots_the_other_way(self):
        keys, _ = self.plan(pose_value=-100.0, prev_value=0.0)
        peak = min(keys, key=lambda k: k.value)
        self.assertAlmostEqual(peak.value, -15.0, places=12)
        self.assertEqual(peak.time, 20)

    def test_the_arrival_starts_from_nothing_at_the_previous_key(self):
        keys, _ = self.plan()
        self.assertEqual(keys[0].time, 10)
        self.assertEqual(keys[0].value, 0.0)

    def test_the_settle_lands_exactly_on_the_pose(self):
        keys, _ = self.plan()
        self.assertEqual(keys[-1].value, 0.0)
        self.assertEqual(keys[-1].time, 32)

    def test_peak_delay_moves_the_extreme_and_the_settle_with_it(self):
        keys, _ = self.plan(peak_delay=3)
        peak = max(keys, key=lambda k: abs(k.value))
        self.assertEqual(peak.time, 23)
        self.assertEqual(keys[-1].time, 35)


class TestPlanShape(unittest.TestCase):

    def plan(self, **kw):
        base = dict(pose_time=20, pose_value=100.0, prev_time=10,
                    prev_value=0.0, amount=0.20, frames=12)
        base.update(kw)
        return mo.plan_overshoot(**base)

    def test_spring_writes_the_turning_points_and_nothing_else(self):
        keys, _ = self.plan(shape="Spring")
        self.assertEqual([k.time for k in keys], [10, 20, 24, 28, 32])

    def test_spring_values_follow_the_geometric_ratio(self):
        keys, _ = self.plan(shape="Spring")
        vals = [k.value for k in keys[1:-1]]
        self.assertAlmostEqual(vals[0], 20.0, places=12)
        self.assertAlmostEqual(vals[1], -6.0, places=12)
        self.assertAlmostEqual(vals[2], 1.8, places=12)

    def test_snap_never_undershoots(self):
        keys, _ = self.plan(shape="Snap")
        self.assertEqual([k.time for k in keys], [10, 20, 32])
        self.assertTrue(all(k.value >= 0.0 for k in keys), keys)

    def test_recoil_undershoots_once(self):
        keys, _ = self.plan(shape="Recoil")
        negative = [k for k in keys if k.value < 0.0]
        self.assertEqual(len(negative), 1)

    def test_elastic_swings_more_than_spring(self):
        self.assertGreater(len(self.plan(shape="Elastic")[0]),
                           len(self.plan(shape="Spring")[0]))

    def test_bounce_stays_on_the_overshoot_side(self):
        keys, _ = self.plan(shape="Bounce")
        self.assertTrue(all(k.value >= 0.0 for k in keys), keys)

    def test_bounce_gives_its_contacts_a_corner(self):
        keys, _ = self.plan(shape="Bounce")
        contacts = [k for k in keys[1:] if k.value == 0.0]
        self.assertTrue(contacts)
        self.assertTrue(all(k.tangent == mo.TAN_LINEAR for k in contacts[:-1]),
                        contacts)

    def test_the_extremes_are_flat_because_they_are_extremes(self):
        keys, _ = self.plan(shape="Spring")
        for k in keys[1:]:
            self.assertEqual(k.tangent, mo.TAN_FLAT, k)

    def test_the_arrival_key_copies_the_animators_own_tangents(self):
        keys, _ = self.plan()
        self.assertEqual(keys[0].tangent, mo.TAN_COPY)

    def test_the_swings_of_a_shape_can_be_overridden(self):
        keys, _ = self.plan(shape="Spring", swings=5, ratio=0.5)
        self.assertEqual(len(keys), 7)
        self.assertAlmostEqual(keys[2].value, -10.0, places=12)


class TestPlanRoom(unittest.TestCase):

    def test_the_settle_stops_a_frame_before_the_next_key(self):
        keys, note = mo.plan_overshoot(pose_time=20, pose_value=100.0,
                                        prev_time=10, prev_value=0.0,
                                        next_time=26, next_value=100.0,
                                        amount=0.2, frames=12)
        self.assertEqual(keys[-1].time, 25)
        self.assertIn("shortened", note)

    def test_a_short_window_drops_swings_rather_than_keys_on_one_frame(self):
        keys, note = mo.plan_overshoot(pose_time=20, pose_value=100.0,
                                        prev_time=10, prev_value=0.0,
                                        next_time=23, next_value=100.0,
                                        amount=0.2, frames=12, shape="Elastic")
        times = [k.time for k in keys]
        self.assertEqual(len(times), len(set(times)), times)
        self.assertIn("swings", note)

    def test_times_never_collide_however_tight_the_window(self):
        for frames in range(1, 14):
            for shape in ("Snap", "Spring", "Elastic", "Recoil", "Bounce"):
                keys, _ = mo.plan_overshoot(pose_time=20, pose_value=100.0,
                                             prev_time=10, prev_value=0.0,
                                             amount=0.2, frames=frames,
                                             shape=shape)
                times = [k.time for k in keys]
                self.assertEqual(len(times), len(set(times)),
                                 (shape, frames, times))
                self.assertEqual(times, sorted(times), (shape, frames, times))

    def test_the_pose_is_always_the_last_word(self):
        for frames in range(1, 14):
            for shape in ("Snap", "Spring", "Elastic", "Recoil", "Bounce"):
                keys, _ = mo.plan_overshoot(pose_time=20, pose_value=100.0,
                                             prev_time=10, prev_value=0.0,
                                             amount=0.2, frames=frames,
                                             shape=shape)
                self.assertEqual(keys[-1].value, 0.0, (shape, frames))

    def test_the_plan_is_sparse(self):
        for shape in ("Snap", "Spring", "Elastic", "Recoil", "Bounce"):
            keys, _ = mo.plan_overshoot(pose_time=20, pose_value=100.0,
                                         prev_time=10, prev_value=0.0,
                                         amount=0.2, frames=20, shape=shape)
            self.assertLessEqual(len(keys), 10, (shape, keys))

    def test_planning_twice_gives_the_same_plan(self):
        args = dict(pose_time=20, pose_value=100.0, prev_time=10,
                    prev_value=0.0, amount=0.2, frames=12)
        self.assertEqual(mo.plan_overshoot(**args), mo.plan_overshoot(**args))


class TestWindowAndAbsolute(unittest.TestCase):

    def test_the_window_is_the_first_and_last_key_of_the_plan(self):
        keys, _ = mo.plan_overshoot(pose_time=20, pose_value=100.0,
                                     prev_time=10, prev_value=0.0,
                                     amount=0.2, frames=12)
        self.assertEqual(mo.plan_window(keys), (10, 32))

    def test_an_empty_plan_has_no_window(self):
        self.assertIsNone(mo.plan_window([]))

    def test_absolute_values_are_the_pose_plus_the_offset(self):
        keys, _ = mo.plan_overshoot(pose_time=20, pose_value=100.0,
                                     prev_time=10, prev_value=0.0,
                                     amount=0.2, frames=12)
        absolute = mo.as_absolute(keys, 100.0, 0.0)
        self.assertEqual(absolute[0].value, 0.0)        # the previous key itself
        self.assertAlmostEqual(absolute[1].value, 120.0, places=12)
        self.assertAlmostEqual(absolute[-1].value, 100.0, places=12)

    def test_absolute_keeps_the_times_and_tangents(self):
        keys, _ = mo.plan_overshoot(pose_time=20, pose_value=100.0,
                                     prev_time=10, prev_value=0.0,
                                     amount=0.2, frames=12)
        absolute = mo.as_absolute(keys, 100.0, 0.0)
        self.assertEqual([k.time for k in keys], [k.time for k in absolute])
        self.assertEqual([k.tangent for k in keys],
                         [k.tangent for k in absolute])


class TestMergePlans(unittest.TestCase):
    """Two poses on one channel share a frame; the arrival must give way."""

    def two_poses(self):
        first, _ = mo.plan_overshoot(pose_time=20, pose_value=100.0,
                                      prev_time=10, prev_value=0.0,
                                      next_time=40, next_value=0.0,
                                      amount=0.2, frames=12)
        second, _ = mo.plan_overshoot(pose_time=40, pose_value=0.0,
                                       prev_time=20, prev_value=100.0,
                                       amount=0.2, frames=12)
        return [(first, 100.0, 0.0), (second, 0.0, 100.0)]

    def test_the_later_arrival_does_not_flatten_the_earlier_extreme(self):
        keys = mo.merge_plans(self.two_poses())
        at20 = [k for k in keys if k.time == 20]
        self.assertEqual(len(at20), 1)
        self.assertAlmostEqual(at20[0].value, 20.0, places=12)

    def test_every_other_key_of_both_plans_survives(self):
        plans = self.two_poses()
        keys = mo.merge_plans(plans)
        expected = set(k.time for kk, _, _ in plans for k in kk)
        self.assertEqual(set(k.time for k in keys), expected)

    def test_the_keys_come_out_in_time_order(self):
        times = [k.time for k in mo.merge_plans(self.two_poses())]
        self.assertEqual(times, sorted(times))

    def test_absolute_mode_anchors_each_key_on_its_own_pose(self):
        keys = mo.merge_plans(self.two_poses(), use_layer=False)
        by_time = {k.time: k.value for k in keys}
        self.assertAlmostEqual(by_time[10], 0.0, places=12)     # prev of pose 1
        self.assertAlmostEqual(by_time[20], 120.0, places=12)   # pose 1 + 20%
        self.assertAlmostEqual(by_time[40], -20.0, places=12)   # pose 2 - 20%

    def test_a_bigger_excursion_wins_a_shared_frame(self):
        a = [mo.Key(0, 0.0, mo.TAN_COPY), mo.Key(10, 5.0, mo.TAN_FLAT),
             mo.Key(20, 0.0, mo.TAN_FLAT)]
        b = [mo.Key(5, 0.0, mo.TAN_COPY), mo.Key(10, -9.0, mo.TAN_FLAT),
             mo.Key(20, 0.0, mo.TAN_FLAT)]
        keys = mo.merge_plans([(a, 0.0, 0.0), (b, 0.0, 0.0)])
        self.assertAlmostEqual([k for k in keys if k.time == 10][0].value, -9.0)

    def test_one_plan_merges_to_itself(self):
        keys, _ = mo.plan_overshoot(pose_time=20, pose_value=100.0,
                                     prev_time=10, prev_value=0.0,
                                     amount=0.2, frames=12)
        self.assertEqual(mo.merge_plans([(keys, 100.0, 0.0)]), keys)

    def test_no_plans_write_nothing(self):
        self.assertEqual(mo.merge_plans([]), [])


class TestPresets(unittest.TestCase):

    def test_every_button_has_a_preset(self):
        for name in ("Snap", "Spring", "Elastic", "Recoil", "Bounce"):
            self.assertIn(name, mo.SHAPES)

    def test_the_preset_order_is_the_button_order(self):
        self.assertEqual(list(mo.SHAPES), mo.SHAPE_ORDER)

    def test_bounce_is_the_only_one_that_is_not_a_spring(self):
        families = {n: s["family"] for n, s in mo.SHAPES.items()}
        self.assertEqual(families["Bounce"], "bounce")
        for name in ("Snap", "Spring", "Elastic", "Recoil"):
            self.assertEqual(families[name], "spring")

    def test_the_channel_groups_are_translate_and_rotate(self):
        self.assertEqual(mo.GROUPS["pos"],
                         ("translateX", "translateY", "translateZ"))
        self.assertEqual(mo.GROUPS["rot"],
                         ("rotateX", "rotateY", "rotateZ"))


if __name__ == "__main__":
    unittest.main()
