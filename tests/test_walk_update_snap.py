"""The rig pose's Update re-reads a snapped weapon (2026-11-11, the animator: «обновление позы в Walk builder не
обновляет оружие»).

Snap weapon reads the mean pose rig once, when its button is pressed; Update read only the rig's bones, so a weapon,
its Aim Mode target or its hand moved on the rig never reached the walker. The fake scene is tests.test_walk_meanrig's.
"""

import unittest

from tests import test_walkmodel as T
from tests.test_walk_meanrig import FakedTest, meanrig

sw = T.load("snapweapon")


def snap(target=(0.0, 5.0, 0.0)):
    """A stored snap: only `target` differs between two of them here."""
    return {"version": sw.VERSION, "side": "r", "anchor": "r", "label": "Sword",
            "offset": [1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0],
            "grip": [0.0, 0.0, 0.0], "aim": [0.0, 1.0, 0.0], "up_axis": [1.0, 0.0, 0.0],
            "target": list(target), "up": [0.0, 200.0, 0.0], "other": None}


class UpdateRereadsTheSnap(FakedTest):

    def setUp(self):
        FakedTest.setUp(self)
        self.root = self.walker(working=True)
        edits = self.scene.walker_edits(self.root, "asd")[0]
        edits["snap"] = snap()
        self.scene.set_edits(self.root, edits)
        meanrig.press(self.root)
        self.read = sw.read
        self.answer = snap()
        sw.read = lambda rig: self.answer

    def tearDown(self):
        sw.read = self.read
        FakedTest.tearDown(self)

    def test_a_target_moved_on_the_rig_reaches_the_walker(self):
        self.answer = snap(target=(0.0, 12.0, 3.0))
        self.scene.applied = []
        line = meanrig.update()
        self.assertEqual(self.scene.edits[self.root]["snap"]["target"], [0.0, 12.0, 3.0])
        self.assertTrue(self.scene.applied, "the walker was not keyed again")
        self.assertFalse(self.scene.applied[-1]["record"])
        self.assertIn("weapon", line)

    def test_an_unchanged_weapon_and_rig_still_say_nothing_moved(self):
        self.scene.edit_calls = []
        self.assertEqual(meanrig.update(), meanrig.NOTHING_MOVED)
        self.assertEqual(self.scene.edit_calls, [])

    def test_a_weapon_no_longer_in_aim_mode_keeps_the_snap_and_says_so(self):
        def refused(rig):
            raise sw.Refusal("no weapon in Aim Mode")
        sw.read = refused
        line = meanrig.update()
        self.assertEqual(self.scene.edits[self.root]["snap"]["target"], [0.0, 5.0, 0.0])
        self.assertIn("Aim Mode", line)

    def test_a_walker_without_a_snap_is_never_read_for_one(self):
        edits = self.scene.walker_edits(self.root, "asd")[0]
        edits["snap"] = None
        self.scene.set_edits(self.root, edits)
        sw.read = lambda rig: self.fail("read a weapon for a walker with no snap")
        meanrig.update()


if __name__ == "__main__":
    unittest.main()
