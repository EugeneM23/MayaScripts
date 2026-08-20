"""The pure half of maya_overshoot: shapes, and the key plan.

Everything here runs without a Maya session. The load-bearing claim of the
whole tool is in TestPoseNeverMoves: the animator's pose key keeps its value,
and everything written starts there and comes back to it.
"""

import math
import unittest

import maya_overshoot as mo


def numeric_slope(fn, u, h=1e-6):
    return (fn(u + h) - fn(u - h)) / (2.0 * h)


class TestSineShape(unittest.TestCase):

    def test_it_starts_at_the_pose(self):
        for swings, ratio in ((1, 0.3), (3, 0.3), (6, 0.6)):
            self.assertAlmostEqual(mo.sine_value(0.0, swings, ratio), 0.0,
                                   places=12, msg=(swings, ratio))

    def test_it_comes_back_to_the_pose(self):
        for swings, ratio in ((1, 0.3), (3, 0.3), (6, 0.6), (2, 0.15)):
            self.assertAlmostEqual(mo.sine_value(1.0, swings, ratio), 0.0,
                                   places=10, msg=(swings, ratio))

    def test_the_peak_is_exactly_one(self):
        for swings, ratio in ((1, 0.3), (3, 0.3), (6, 0.6), (2, 0.15)):
            u = mo.sine_first_extreme(swings, ratio)
            self.assertAlmostEqual(mo.sine_value(u, swings, ratio), 1.0,
                                   places=10, msg=(swings, ratio))

    def test_nothing_in_the_shape_goes_past_the_peak(self):
        for swings, ratio in ((1, 0.3), (3, 0.3), (6, 0.6)):
            worst = max(abs(mo.sine_value(i / 400.0, swings, ratio))
                        for i in range(401))
            self.assertLessEqual(worst, 1.0 + 1e-9, (swings, ratio))

    def test_with_no_decay_the_peak_is_the_quarter_period(self):
        self.assertAlmostEqual(mo.sine_first_extreme(3, 1.0), 1.0 / 6.0,
                               places=12)

    def test_the_first_extreme_is_where_the_derivative_vanishes(self):
        for swings, ratio in ((1, 0.3), (3, 0.3), (6, 0.6)):
            u = mo.sine_first_extreme(swings, ratio)
            slope = numeric_slope(lambda x: mo.sine_value(x, swings, ratio), u)
            self.assertAlmostEqual(slope, 0.0, places=4, msg=(swings, ratio))


class TestSineExtremes(unittest.TestCase):

    def test_one_crest_per_swing(self):
        for swings in (1, 2, 3, 6):
            self.assertEqual(len(mo.sine_extremes(swings, 0.3)), swings)

    def test_the_first_crest_is_the_peak(self):
        u, v = mo.sine_extremes(3, 0.3)[0]
        self.assertAlmostEqual(u, mo.sine_first_extreme(3, 0.3), places=12)
        self.assertEqual(v, 1.0)

    def test_the_crests_are_half_a_period_apart(self):
        us = [u for u, _ in mo.sine_extremes(4, 0.3)]
        for a, b in zip(us, us[1:]):
            self.assertAlmostEqual(b - a, 0.25, places=12)

    def test_the_swings_alternate_sides(self):
        vals = [v for _, v in mo.sine_extremes(5, 0.4)]
        for a, b in zip(vals, vals[1:]):
            self.assertLess(a * b, 0.0, vals)

    def test_each_swing_keeps_the_ratio_of_the_last(self):
        vals = [v for _, v in mo.sine_extremes(4, 0.3)]
        for a, b in zip(vals, vals[1:]):
            self.assertAlmostEqual(abs(b) / abs(a), 0.3, places=12)

    def test_the_table_agrees_with_the_closed_form(self):
        for swings, ratio in ((1, 0.3), (2, 0.15), (3, 0.3), (6, 0.6)):
            for u, v in mo.sine_extremes(swings, ratio):
                self.assertAlmostEqual(mo.sine_value(u, swings, ratio), v,
                                       places=9, msg=(swings, ratio, u))

    def test_every_crest_is_inside_the_window(self):
        for swings, ratio in ((1, 0.3), (3, 0.3), (6, 0.6), (10, 0.8)):
            for u, _ in mo.sine_extremes(swings, ratio):
                self.assertLess(u, 1.0, (swings, ratio))


class TestEntrySlope(unittest.TestCase):

    def test_the_shape_leaves_the_pose_at_the_slope_it_advertises(self):
        for swings, ratio in ((1, 0.3), (3, 0.3), (6, 0.6)):
            want = mo.sine_entry_slope(swings, ratio)
            got = numeric_slope(lambda u: mo.sine_value(u, swings, ratio), 0.0)
            self.assertAlmostEqual(got / want, 1.0, places=8,
                                   msg=(swings, ratio, want, got))

    def test_a_bounce_leaves_the_pose_at_the_slope_it_advertises(self):
        want = mo.bounce_entry_slope(0.5)
        apex_u, apex_v, _ = mo.bounce_extremes(0.5)[0]
        # a parabola of height h over 2*apex_u has slope 4h/(2 apex_u) at zero
        self.assertAlmostEqual(want, 4.0 * apex_v / (2.0 * apex_u), places=12)

    def test_more_swings_leave_faster_for_the_same_peak(self):
        self.assertGreater(mo.sine_entry_slope(6, 0.6),
                           mo.sine_entry_slope(1, 0.3))


class TestBounceExtremes(unittest.TestCase):

    def test_it_starts_with_an_apex_and_ends_on_the_pose(self):
        ext = mo.bounce_extremes(0.5)
        self.assertEqual(ext[0][2], "apex")
        self.assertEqual(ext[-1], (1.0, 0.0, "contact"))

    def test_apexes_and_contacts_alternate(self):
        kinds = [k for _, _, k in mo.bounce_extremes(0.5)]
        for a, b in zip(kinds, kinds[1:]):
            self.assertNotEqual(a, b, kinds)

    def test_the_first_apex_is_the_peak(self):
        self.assertEqual(mo.bounce_extremes(0.5)[0][1], 1.0)

    def test_every_apex_keeps_the_square_of_the_restitution(self):
        apex = [v for _, v, k in mo.bounce_extremes(0.5) if k == "apex"]
        for a, b in zip(apex, apex[1:]):
            self.assertAlmostEqual(b / a, 0.25, places=12)

    def test_the_arcs_shrink_by_the_restitution(self):
        contacts = [u for u, _, k in mo.bounce_extremes(0.5) if k == "contact"]
        gaps = [b - a for a, b in zip([0.0] + contacts, contacts)]
        for a, b in zip(gaps, gaps[1:]):
            self.assertAlmostEqual(b / a, 0.5, places=10, msg=gaps)

    def test_it_never_crosses_the_pose(self):
        for e in (0.3, 0.5, 0.7):
            self.assertTrue(all(v >= 0.0 for _, v, _ in mo.bounce_extremes(e)))

    def test_the_span_is_normalised(self):
        for e in (0.3, 0.5, 0.7):
            self.assertAlmostEqual(mo.bounce_extremes(e)[-1][0], 1.0, places=12)


class TestPoseNeverMoves(unittest.TestCase):
    """The whole concept: the pose key keeps its value, whatever we write."""

    def plans(self):
        out = []
        for shape in mo.SHAPE_ORDER:
            for frames in (2, 5, 12, 30):
                for strength in (0.2, 1.0, 2.5):
                    keys, note = mo.plan_overshoot(
                        pose_time=20, pose_value=100.0, prev_time=10,
                        prev_value=0.0, strength=strength, frames=frames,
                        shape=shape)
                    out.append((shape, frames, strength, keys, note))
        return out

    def test_the_first_key_is_the_pose_itself_at_no_offset(self):
        for shape, frames, strength, keys, _ in self.plans():
            self.assertTrue(keys, (shape, frames, strength))
            self.assertEqual(keys[0].time, 20, (shape, frames))
            self.assertEqual(keys[0].value, 0.0, (shape, frames))

    def test_the_last_key_returns_to_the_pose(self):
        for shape, frames, _, keys, _ in self.plans():
            self.assertEqual(keys[-1].time, 20 + frames, (shape, frames))
            self.assertEqual(keys[-1].value, 0.0, (shape, frames))

    def test_nothing_is_written_before_the_pose(self):
        for shape, _, _, keys, _ in self.plans():
            self.assertTrue(all(k.time >= 20 for k in keys), shape)

    def test_the_times_are_distinct_and_in_order(self):
        for shape, frames, _, keys, _ in self.plans():
            times = [k.time for k in keys]
            self.assertEqual(times, sorted(times), (shape, frames, times))
            self.assertEqual(len(times), len(set(times)), (shape, frames, times))

    def test_the_plan_is_sparse(self):
        for shape, frames, _, keys, _ in self.plans():
            self.assertLessEqual(len(keys), 10, (shape, frames, keys))


class TestSpeedAndAmplitude(unittest.TestCase):

    def plan(self, **kw):
        base = dict(pose_time=20, pose_value=100.0, prev_time=10,
                    prev_value=0.0, strength=1.0, frames=12)
        base.update(kw)
        return mo.plan_overshoot(**base)

    def test_it_leaves_the_pose_at_the_speed_of_the_move(self):
        # 100 units over 10 frames is 10 a frame, and strength 1 means exactly
        # that -- the overshoot continues the move instead of restarting it
        keys, _ = self.plan()
        self.assertAlmostEqual(keys[0].slope, 10.0, places=9)

    def test_strength_scales_the_speed_it_leaves_at(self):
        self.assertAlmostEqual(self.plan(strength=0.5)[0][0].slope, 5.0,
                               places=9)
        self.assertAlmostEqual(self.plan(strength=2.0)[0][0].slope, 20.0,
                               places=9)

    def test_a_slower_move_gets_a_smaller_overshoot(self):
        fast = mo.peak_of(self.plan(prev_time=10)[0])[1]
        slow = mo.peak_of(self.plan(prev_time=0)[0])[1]
        self.assertAlmostEqual(fast / slow, 2.0, places=9)

    def test_the_peak_is_the_speed_times_the_window(self):
        keys, _ = self.plan()
        entry = mo.sine_entry_slope(3, 0.3)
        self.assertAlmostEqual(mo.peak_of(keys)[1], 10.0 * 12 / entry,
                               places=9)

    def test_amplitude_is_linear_in_strength(self):
        a = mo.peak_of(self.plan(strength=0.5)[0])[1]
        b = mo.peak_of(self.plan(strength=1.5)[0])[1]
        self.assertAlmostEqual(b / a, 3.0, places=9)

    def test_a_move_in_the_other_direction_overshoots_the_other_way(self):
        keys, _ = self.plan(pose_value=-100.0)
        self.assertLess(mo.peak_of(keys)[1], 0.0)
        self.assertAlmostEqual(keys[0].slope, -10.0, places=9)

    def test_rotation_is_no_different_from_translation(self):
        degrees, _ = self.plan(pose_value=60.0)
        self.assertAlmostEqual(degrees[0].slope, 6.0, places=9)

    def test_an_absurd_excursion_is_clamped_and_said_so(self):
        keys, note = self.plan(prev_time=19, frames=48)
        self.assertAlmostEqual(abs(mo.peak_of(keys)[1]), 200.0, places=6)
        self.assertIn("clamped", note)


class TestShapeCharacter(unittest.TestCase):

    def plan(self, **kw):
        base = dict(pose_time=20, pose_value=100.0, prev_time=10,
                    prev_value=0.0, strength=1.0, frames=12)
        base.update(kw)
        return mo.plan_overshoot(**base)[0]

    def test_snap_never_undershoots(self):
        self.assertTrue(all(k.value >= 0.0 for k in self.plan(shape="Snap")))

    def test_spring_undershoots_and_comes_back(self):
        vals = [k.value for k in self.plan(shape="Spring")]
        self.assertGreater(max(vals), 0.0)
        self.assertLess(min(vals), 0.0)

    def test_recoil_undershoots_once(self):
        self.assertEqual(len([k for k in self.plan(shape="Recoil")
                              if k.value < 0.0]), 1)

    def test_elastic_swings_more_than_spring(self):
        self.assertGreater(len(self.plan(shape="Elastic")),
                           len(self.plan(shape="Spring")))

    def test_bounce_stays_on_the_overshoot_side(self):
        self.assertTrue(all(k.value >= 0.0 for k in self.plan(shape="Bounce")))

    def test_bounce_gives_its_contacts_a_corner(self):
        keys = self.plan(shape="Bounce")
        contacts = [k for k in keys[1:-1] if k.value == 0.0]
        self.assertTrue(contacts)
        self.assertTrue(all(k.tangent == mo.TAN_LINEAR for k in contacts))

    def test_the_crests_are_flat_because_they_are_turning_points(self):
        for k in self.plan(shape="Spring")[1:]:
            self.assertEqual(k.tangent, mo.TAN_FLAT, k)

    def test_the_pose_key_carries_the_slope(self):
        first = self.plan(shape="Spring")[0]
        self.assertEqual(first.tangent, mo.TAN_SLOPE)
        self.assertIsNotNone(first.slope)

    def test_the_swings_can_be_overridden(self):
        self.assertEqual(len(self.plan(shape="Spring", swings=5, ratio=0.5)), 7)


class TestRefusals(unittest.TestCase):

    def test_the_first_key_of_a_channel_has_no_move_behind_it(self):
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
        self.assertTrue(mo.plan_overshoot(pose_time=10, pose_value=100.0,
                                          prev_time=0, prev_value=0.0,
                                          next_time=30, next_value=20.0)[0])

    def test_a_hold_is_a_stop(self):
        self.assertTrue(mo.plan_overshoot(pose_time=10, pose_value=100.0,
                                          prev_time=0, prev_value=0.0,
                                          next_time=40, next_value=100.0)[0])

    def test_the_last_key_of_a_channel_is_a_stop(self):
        self.assertTrue(mo.plan_overshoot(pose_time=10, pose_value=100.0,
                                          prev_time=0, prev_value=0.0)[0])

    def test_no_room_before_the_next_key_is_refused(self):
        for next_time in (11, 12):
            keys, note = mo.plan_overshoot(pose_time=10, pose_value=100.0,
                                           prev_time=0, prev_value=0.0,
                                           next_time=next_time,
                                           next_value=100.0)
            self.assertEqual(keys, [], next_time)
            self.assertIn("no room", note)


class TestRoom(unittest.TestCase):

    def test_the_settle_stops_a_frame_before_the_next_key(self):
        keys, note = mo.plan_overshoot(pose_time=20, pose_value=100.0,
                                        prev_time=10, prev_value=0.0,
                                        next_time=26, next_value=100.0,
                                        frames=12)
        self.assertEqual(keys[-1].time, 25)
        self.assertIn("shortened", note)

    def test_a_short_window_drops_swings_rather_than_keys_on_one_frame(self):
        keys, note = mo.plan_overshoot(pose_time=20, pose_value=100.0,
                                        prev_time=10, prev_value=0.0,
                                        next_time=24, next_value=100.0,
                                        frames=12, shape="Elastic")
        times = [k.time for k in keys]
        self.assertEqual(len(times), len(set(times)), times)
        self.assertIn("swings", note)

    def test_planning_twice_gives_the_same_plan(self):
        args = dict(pose_time=20, pose_value=100.0, prev_time=10,
                    prev_value=0.0, frames=12)
        self.assertEqual(mo.plan_overshoot(**args), mo.plan_overshoot(**args))

    def test_the_window_is_the_pose_and_the_settle_end(self):
        keys, _ = mo.plan_overshoot(pose_time=20, pose_value=100.0,
                                     prev_time=10, prev_value=0.0, frames=12)
        self.assertEqual(mo.plan_window(keys), (20, 32))

    def test_an_empty_plan_has_no_window(self):
        self.assertIsNone(mo.plan_window([]))
        self.assertIsNone(mo.peak_of([]))


class TestAbsoluteAndMerge(unittest.TestCase):

    def plan(self, pose_time=20, pose_value=100.0, prev_time=10,
             prev_value=0.0, **kw):
        return mo.plan_overshoot(pose_time=pose_time, pose_value=pose_value,
                                 prev_time=prev_time, prev_value=prev_value,
                                 **kw)[0]

    def test_absolute_values_are_the_pose_plus_the_offset(self):
        keys = self.plan(frames=12)
        absolute = mo.as_absolute(keys, 100.0)
        self.assertEqual(absolute[0].value, 100.0)
        self.assertEqual(absolute[-1].value, 100.0)
        self.assertAlmostEqual(absolute[1].value - 100.0, keys[1].value,
                               places=12)

    def test_absolute_keeps_times_tangents_and_slope(self):
        keys = self.plan(frames=12)
        absolute = mo.as_absolute(keys, 100.0)
        self.assertEqual([k.time for k in keys], [k.time for k in absolute])
        self.assertEqual([k.tangent for k in keys],
                         [k.tangent for k in absolute])
        self.assertEqual(keys[0].slope, absolute[0].slope)

    def test_two_poses_on_one_channel_keep_both_pose_keys_at_zero(self):
        first = self.plan(pose_time=20, pose_value=100.0, prev_time=10,
                          prev_value=0.0, next_time=40, next_value=0.0,
                          frames=12)
        second = self.plan(pose_time=40, pose_value=0.0, prev_time=20,
                           prev_value=100.0, frames=12)
        keys = mo.merge_plans([(first, 100.0), (second, 0.0)])
        by_time = {k.time: k.value for k in keys}
        self.assertEqual(by_time[20], 0.0)
        self.assertEqual(by_time[40], 0.0)

    def test_merging_keeps_every_key_of_both_plans(self):
        first = self.plan(pose_time=20, next_time=40, next_value=0.0, frames=12)
        second = self.plan(pose_time=40, pose_value=0.0, prev_time=20,
                           prev_value=100.0, frames=12)
        keys = mo.merge_plans([(first, 100.0), (second, 0.0)])
        self.assertEqual(set(k.time for k in keys),
                         set(k.time for k in first + second))

    def test_absolute_merge_anchors_each_key_on_its_own_pose(self):
        first = self.plan(pose_time=20, next_time=40, next_value=0.0, frames=12)
        second = self.plan(pose_time=40, pose_value=0.0, prev_time=20,
                           prev_value=100.0, frames=12)
        keys = mo.merge_plans([(first, 100.0), (second, 0.0)], use_layer=False)
        by_time = {k.time: k.value for k in keys}
        self.assertEqual(by_time[20], 100.0)
        self.assertEqual(by_time[40], 0.0)

    def test_one_plan_merges_to_itself(self):
        keys = self.plan(frames=12)
        self.assertEqual(mo.merge_plans([(keys, 100.0)]), keys)

    def test_no_plans_write_nothing(self):
        self.assertEqual(mo.merge_plans([]), [])


class TestPresets(unittest.TestCase):

    def test_every_button_has_a_preset(self):
        for name in ("Snap", "Spring", "Elastic", "Recoil", "Bounce"):
            self.assertIn(name, mo.SHAPES)

    def test_the_preset_order_is_the_button_order(self):
        self.assertEqual(list(mo.SHAPES), mo.SHAPE_ORDER)

    def test_bounce_is_the_only_one_that_is_not_a_sine(self):
        families = {n: s["family"] for n, s in mo.SHAPES.items()}
        self.assertEqual(families["Bounce"], "bounce")
        for name in ("Snap", "Spring", "Elastic", "Recoil"):
            self.assertEqual(families[name], "sine")

    def test_the_channel_groups_are_translate_and_rotate(self):
        self.assertEqual(mo.GROUPS["pos"],
                         ("translateX", "translateY", "translateZ"))
        self.assertEqual(mo.GROUPS["rot"],
                         ("rotateX", "rotateY", "rotateZ"))


if __name__ == "__main__":
    unittest.main()
