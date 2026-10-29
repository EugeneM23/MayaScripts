"""The composer's pure helpers: the channel set and euler continuity."""

import unittest

from maya_uebridge import montage


class Continuous(unittest.TestCase):
    def test_a_wrap_between_two_frames_is_unwrapped(self):
        """A 359 -> 1 step is a wrap, not 358 degrees in one frame."""
        self.assertEqual(montage.continuous([359.0, 1.0]), [359.0, 361.0])

    def test_a_wrap_the_other_way(self):
        self.assertEqual(montage.continuous([1.0, 359.0]), [1.0, -1.0])

    def test_a_genuine_step_under_180_is_left_alone(self):
        self.assertEqual(montage.continuous([0.0, 170.0, -170.0]),
                         [0.0, 170.0, 190.0])

    def test_a_still_series_is_left_alone(self):
        self.assertEqual(montage.continuous([12.5, 12.5, 12.5]),
                         [12.5, 12.5, 12.5])

    def test_the_first_value_never_moves(self):
        """The take must start where the montage starts."""
        self.assertEqual(montage.continuous([200.0, -170.0])[0], 200.0)

    def test_an_empty_series(self):
        self.assertEqual(montage.continuous([]), [])

    def test_several_wraps_in_a_row_keep_turning(self):
        out = montage.continuous([0.0, 179.0, -2.0, 177.0])
        self.assertEqual(out, [0.0, 179.0, 358.0, 537.0])


class ChannelPlan(unittest.TestCase):
    def test_the_union_of_what_the_clips_animate(self):
        animated = {"/Game/A": {"root": ["translateX", "rotateY"]},
                    "/Game/B": {"root": ["rotateY"], "pelvis": ["rotateX"]}}
        self.assertEqual(montage.channel_plan(animated),
                         [("pelvis", "rotateX"), ("root", "rotateY"),
                          ("root", "translateX")])

    def test_a_channel_only_the_second_clip_animates_is_in_the_plan(self):
        animated = {"/Game/A": {"root": ["rotateY"]},
                    "/Game/B": {"root": ["Pose_3"]}}
        self.assertIn(("root", "Pose_3"), montage.channel_plan(animated))

    def test_visibility_is_never_composed(self):
        animated = {"/Game/A": {"root": ["visibility", "rotateY"]}}
        self.assertEqual(montage.channel_plan(animated), [("root", "rotateY")])

    def test_nothing_animated_is_an_empty_plan(self):
        self.assertEqual(montage.channel_plan({}), [])

    def test_the_order_is_stable(self):
        animated = {"/Game/A": {"b": ["rotateZ", "rotateX"], "a": ["translateY"]}}
        self.assertEqual(montage.channel_plan(animated),
                         [("a", "translateY"), ("b", "rotateX"),
                          ("b", "rotateZ")])


class PlanFile(unittest.TestCase):
    def test_a_plan_round_trips_through_its_payload(self):
        payload = {"montages": {"/Game/AM_X": {"name": "AM_X", "slots": [
            {"slot": "1P", "segments": [
                {"clip": "/Game/C", "start_pos": 0.0, "anim_start_time": 0.0,
                 "anim_end_time": 0.5, "anim_play_rate": 1.25,
                 "looping_count": 1, "additive": ""}]}]}}}
        plan = montage.plan_for(payload, "/Game/AM_X", "1P")
        written = montage.plan_payload(plan, {"/Game/C": "C:/t/C.fbx"}, 30.0)
        back = montage.plan_of_payload(written)
        self.assertEqual(back.montage, "AM_X")
        self.assertEqual(back.slot, "1P")
        self.assertEqual(back.clips, ["/Game/C"])
        self.assertAlmostEqual(back.end, plan.end, places=9)
        self.assertAlmostEqual(back.spans[0].rate, 1.25, places=9)
        self.assertEqual(written["clips"], {"/Game/C": "C:/t/C.fbx"})
        self.assertEqual(written["name"], "AM_X_1P")

    def test_the_line_names_the_frames_and_the_cuts(self):
        payload = {"montages": {"/Game/AM_X": {"name": "AM_X", "slots": [
            {"slot": "1P", "segments": [
                {"clip": "/Game/C", "start_pos": 0.0, "anim_start_time": 0.0,
                 "anim_end_time": 0.5, "anim_play_rate": 1.0,
                 "looping_count": 1},
                {"clip": "/Game/D", "start_pos": 0.5, "anim_start_time": 0.0,
                 "anim_end_time": 0.5, "anim_play_rate": 1.0,
                 "looping_count": 1}]}]}}}
        plan = montage.plan_for(payload, "/Game/AM_X", "1P")
        line = montage.plan_line(plan, 30.0)
        self.assertIn("AM_X · 1P", line)
        self.assertIn("31 frames", line)
        self.assertIn("cuts at 15", line)
        self.assertIn("2 clips", line)


if __name__ == "__main__":
    unittest.main()
