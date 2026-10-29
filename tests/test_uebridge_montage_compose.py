"""The composer: the channel set, euler continuity and the euler choice."""

import math
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


class TurnNear(unittest.TestCase):
    def test_a_value_is_shifted_by_whole_turns_toward_the_previous(self):
        turn = 2.0 * math.pi
        self.assertAlmostEqual(montage._turn_near(0.1, 0.1 + turn), 0.1, 9)
        self.assertAlmostEqual(montage._turn_near(0.1, 0.1 - turn), 0.1, 9)

    def test_a_value_already_near_is_left_alone(self):
        self.assertAlmostEqual(montage._turn_near(1.0, 1.5), 1.5, 9)

    def test_half_a_turn_is_the_boundary(self):
        self.assertAlmostEqual(montage._turn_near(0.0, math.pi - 0.01),
                               math.pi - 0.01, 9)
        self.assertAlmostEqual(montage._turn_near(0.0, math.pi + 0.01),
                               math.pi + 0.01 - 2.0 * math.pi, 9)


try:
    from maya.api import OpenMaya as _om
    HAVE_API = True
except ImportError:                                          # pragma: no cover
    HAVE_API = False


@unittest.skipUnless(HAVE_API, "needs maya.api")
class ClosestEuler(unittest.TestCase):
    """A quaternion names one rotation and two eulers: the series is chosen
    against what came before, or channels flip frame to frame."""

    def euler(self, x, y, z):
        return _om.MEulerRotation(math.radians(x), math.radians(y),
                                  math.radians(z))

    def test_the_first_sample_takes_the_rotation_as_it_is(self):
        values = montage._closest_euler(None, self.euler(10.0, 20.0, 30.0))
        self.assertAlmostEqual(math.degrees(values[0]), 10.0, 6)
        self.assertAlmostEqual(math.degrees(values[1]), 20.0, 6)
        self.assertAlmostEqual(math.degrees(values[2]), 30.0, 6)

    def test_a_whole_turn_is_taken_off_to_stay_near(self):
        previous = [math.radians(v) for v in (10.0, 20.0, 30.0)]
        values = montage._closest_euler(previous,
                                        self.euler(370.0, 20.0, 30.0))
        self.assertAlmostEqual(math.degrees(values[0]), 10.0, 6)

    def test_the_alternate_solution_wins_when_it_is_nearer(self):
        """The alternate names the same rotation; near it, it must be taken."""
        rotation = self.euler(170.0, 150.0, -160.0)
        alternate = rotation.alternateSolution()
        previous = [alternate.x, alternate.y, alternate.z]
        values = montage._closest_euler(previous, rotation)
        for got, want in zip(values, previous):
            self.assertAlmostEqual(got, want, 6)

    def test_the_answer_is_always_the_same_rotation(self):
        rotation = self.euler(40.0, -70.0, 120.0)
        previous = [math.radians(v) for v in (0.0, 0.0, 0.0)]
        values = montage._closest_euler(previous, rotation)
        again = _om.MEulerRotation(values[0], values[1], values[2])
        quat, back = rotation.asQuaternion(), again.asQuaternion()
        dot = (quat.x * back.x + quat.y * back.y + quat.z * back.z
               + quat.w * back.w)
        self.assertAlmostEqual(abs(dot), 1.0, 9)


class Note(unittest.TestCase):
    """What a press's status adds about a composite - the head of every line
    already says the clip's name and its frames."""

    def test_an_ordinary_clip_adds_nothing(self):
        self.assertEqual(montage.note_of({"start": 0, "end": 45}), "")
        self.assertEqual(montage.note_of({}), "")
        self.assertEqual(montage.note_of(None), "")

    def test_the_cuts_and_the_clips_are_named(self):
        note = montage.note_of({"montage": {
            "name": "AM_X", "slot": "1P", "frames": 59,
            "cuts": [19.0, 38.0], "clips": ["a", "b", "c"], "held": []}})
        self.assertIn("cuts at 19, 38", note)
        self.assertIn("3 clips", note)

    def test_one_clip_and_one_span_say_nothing_of_either(self):
        note = montage.note_of({"montage": {
            "name": "AM_X", "slot": "1P", "frames": 20, "cuts": [],
            "clips": ["a"], "held": []}})
        self.assertEqual(note, "")

    def test_a_held_channel_is_named(self):
        note = montage.note_of({"montage": {
            "name": "AM_X", "slot": "1P", "cuts": [], "clips": ["a"],
            "held": ["root.Pose_7"]}})
        self.assertIn("root.Pose_7", note)


class ResultLines(unittest.TestCase):
    """Both roads' status lines carry the note (the rig's and the
    skeleton's), so the animator sees where the montage's edits fall."""

    def test_the_rig_road_names_the_cuts(self):
        import sys
        import types
        if "maya.cmds" not in sys.modules:
            try:
                import maya.cmds  # noqa: F401
            except ImportError:
                maya = types.ModuleType("maya")
                maya.cmds = types.ModuleType("maya.cmds")
                maya.mel = types.ModuleType("maya.mel")
                sys.modules.setdefault("maya", maya)
                sys.modules["maya.cmds"] = maya.cmds
                sys.modules["maya.mel"] = maya.mel
        from maya_uebridge import rigimport
        line = rigimport.result_line(
            "AM_X_1P", {"start": 0, "end": 58,
                        "montage": {"name": "AM_X", "slot": "1P",
                                    "cuts": [19.0, 38.0],
                                    "clips": ["a", "b", "c"], "held": []}},
            "connected", "baked", "AM_X_1P", "Manny_Rig")
        self.assertIn("frames 0-58", line)
        self.assertIn("cuts at 19, 38", line)

    def test_the_skeleton_road_names_the_cuts(self):
        from maya_uebridge import skeletonimport
        line = skeletonimport.result_line(
            "AM_X_1P", "Manny UE5 [skeleton]", "root",
            {"moved": 91, "twin": True, "mode": "stretch"},
            {"start": 0, "end": 58,
             "montage": {"name": "AM_X", "slot": "1P", "cuts": [19.0],
                         "clips": ["a", "b"], "held": []}})
        self.assertIn("cuts at 19", line)
        self.assertIn("2 clips", line)


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
