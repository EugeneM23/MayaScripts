"""The Pose Library's objects beside a character (2026-10-15): `objects.pair_card`, pure."""

import unittest

try:
    import maya.cmds  # noqa: F401  (the real package when mayapy has it - trap 60)
except ImportError:
    pass

from maya_poselib import apply as ap
from maya_poselib import objects


def cards():
    return [{"name": "camera1", "path": "|camera1", "attrs": {"translateX": 1.0}},
            {"name": "SceneSetup_camera", "path": "|Manny_Rig_Character|Manny_Rig:SceneSetup_camera",
             "attrs": {}, "own": True},
            {"name": "prop", "path": "|prop", "attrs": {}}]


class PairCard(unittest.TestCase):

    def test_the_selection_finds_a_camera_in_another_namespace(self):
        stored = cards()
        matched, how, unfound = objects.pair_card(stored, ["|shot:camera1"], {}, ap.pair_objects)
        self.assertEqual([(r["name"], p) for r, p in matched], [("camera1", "|shot:camera1")])
        self.assertEqual(how, "name")
        self.assertEqual([r["name"] for r in unfound], ["SceneSetup_camera", "prop"])

    def test_the_rest_is_found_and_never_by_name(self):
        stored = cards()
        found = {1: ["|Manny_Rig1_Character|Manny_Rig1:SceneSetup_camera"], 2: ["|prop"]}
        matched, how, unfound = objects.pair_card(stored, [], found, ap.pair_objects)
        self.assertEqual([p for _r, p in matched],
                         ["|Manny_Rig1_Character|Manny_Rig1:SceneSetup_camera", "|prop"])
        self.assertEqual(how, "found")
        self.assertEqual([r["name"] for r in unfound], ["camera1"])

    def test_selected_first_then_found_never_twice(self):
        stored = cards()
        found = {0: ["|camera1"], 2: ["|prop"]}
        matched, how, unfound = objects.pair_card(stored, ["|shot:camera1"], found,
                                                  ap.pair_objects)
        self.assertEqual([(r["name"], p) for r, p in matched],
                         [("camera1", "|shot:camera1"), ("prop", "|prop")])
        self.assertEqual(how, "name+found")
        self.assertEqual([r["name"] for r in unfound], ["SceneSetup_camera"])

    def test_an_own_object_found_in_two_targets_is_keyed_on_both(self):
        stored = cards()
        found = {1: ["|A|a:SceneSetup_camera", "|B|b:SceneSetup_camera"]}
        matched, _how, _unfound = objects.pair_card(stored, [], found, ap.pair_objects)
        self.assertEqual([p for _r, p in matched],
                         ["|A|a:SceneSetup_camera", "|B|b:SceneSetup_camera"])

    def test_a_found_path_the_selection_took_is_not_taken_again(self):
        stored = cards()
        matched, _how, unfound = objects.pair_card(stored, ["|prop"], {0: ["|prop"]},
                                                   ap.pair_objects)
        self.assertEqual([(r["name"], p) for r, p in matched], [("prop", "|prop")])
        self.assertEqual([r["name"] for r in unfound], ["camera1", "SceneSetup_camera"])


if __name__ == "__main__":
    unittest.main()
