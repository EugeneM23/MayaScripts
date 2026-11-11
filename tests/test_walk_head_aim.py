"""Walk Builder's Head aim (2026-11-11): the head looks at a target placed on the rig pose, carried by the root,
as much as the parameter Head aim asks. The spec: docs/superpowers/specs/2026-11-11-walk-head-aim-design.md.

The synthetic walker is tests.test_walkmodel's; the rig pose's fake scene tests.test_walk_meanrig's.
"""

import math
import unittest

import numpy as np

from tests import test_walkmodel as T
from tests.test_walk_meanrig import FakedTest, meanrig

wm = T.wm
ha = T.load("headaim")
gait = T.load("gait")


def angle(a, b):
    a, b = ha._unit(a), ha._unit(b)
    return math.degrees(math.acos(min(max(float(np.dot(a, b)), -1.0), 1.0)))


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.walk = T.walk()
        knobs = {"arm_drag": 0.0, "torso_drag": 0.0, "head_drag": 0.0, "balance": 0.0}
        cls.worlds = np.asarray(cls.walk.evaluate(knobs, None).worlds, float)
        i = cls.walk.index
        f = 0
        head, root = cls.worlds[i["head"], f], cls.worlds[i["root"], f]
        cls.target = head[3, :3] + np.array([10.0, 20.0, 150.0])
        cls.aimed = ha.record(head, root, cls.target, "head")

    def look(self, worlds, f, aimed=None):
        aimed = aimed or self.aimed
        H = ha._rigid(worlds[self.walk.index["head"], f])
        return np.asarray(aimed["aim"]) @ H[:3, :3], H[3, :3]

    def target_at(self, worlds, f):
        return ha._point_of(self.aimed["target"], ha._rigid(worlds[self.walk.index["root"], f]))


class RecordTests(Base):
    def test_the_look_is_kept_in_the_head_s_own_axes_and_the_target_in_the_root_s(self):
        look, P = self.look(self.worlds, 0)
        self.assertLess(angle(look, self.target - P), 1e-9)
        self.assertLess(float(np.linalg.norm(self.target_at(self.worlds, 0) - self.target)), 1e-9)

    def test_a_kept_look_axis_stays_and_a_moved_target_turns_the_head(self):
        head, root = (self.worlds[self.walk.index[n], 0] for n in ("head", "root"))
        moved = ha.record(head, root, self.target + np.array([40.0, 0.0, 0.0]), "head", self.aimed["aim"])
        self.assertTrue(np.allclose(moved["aim"], self.aimed["aim"], atol=1e-12))
        out, info = ha.apply(self.walk, self.worlds, moved, 1.0)
        self.assertGreater(info["deg"], 10.0)

    def test_loads_round_trips_and_refuses_broken_data(self):
        self.assertEqual(ha.loads(self.aimed), self.aimed)
        self.assertIsNone(ha.loads(dict(self.aimed, version=99)))
        self.assertIsNone(ha.loads(dict(self.aimed, aim=[1.0])))
        self.assertIsNone(ha.loads(None))

    def test_a_target_on_the_head_is_refused(self):
        head = self.worlds[self.walk.index["head"], 0]
        with self.assertRaises(ha.Refusal):
            ha.record(head, self.worlds[self.walk.index["root"], 0], head[3, :3])


class SwingTests(unittest.TestCase):
    def test_the_swing_takes_a_onto_b_and_a_share_of_the_way(self):
        a, b = np.array([1.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0])
        self.assertTrue(np.allclose(a @ ha.swing(a, b), b))
        self.assertAlmostEqual(angle(a @ ha.swing(a, b, 0.5), a), 45.0, places=9)
        self.assertTrue(np.allclose(ha.swing(a, a), np.eye(3)))
        self.assertTrue(np.allclose(a @ ha.swing(a, -a), -a))


class ApplyTests(Base):
    @classmethod
    def setUpClass(cls):
        Base.setUpClass()
        cls.out, cls.info = ha.apply(cls.walk, cls.worlds, cls.aimed, 1.0)

    def test_the_input_is_not_changed(self):
        again = np.asarray(self.walk.evaluate({"arm_drag": 0.0, "torso_drag": 0.0, "head_drag": 0.0,
                                               "balance": 0.0}, None).worlds, float)
        self.assertTrue(np.allclose(again, self.worlds))

    def test_the_head_looks_at_the_target_on_every_frame(self):
        worst = max(angle(*((lambda l, P: (l, self.target_at(self.out, f) - P))(*self.look(self.out, f))))
                    for f in range(self.out.shape[1]))
        self.assertLess(worst, 1e-4)
        walked = max(angle(*((lambda l, P: (l, self.target_at(self.worlds, f) - P))(*self.look(self.worlds, f))))
                     for f in range(self.worlds.shape[1]))
        self.assertGreater(walked, 0.5)      # the walk's own head wanders off it: the gate can fail
        self.assertGreater(self.info["deg"], 0.5)

    def test_the_head_keeps_its_place_and_the_body_is_untouched(self):
        i = self.walk.index
        self.assertTrue(np.allclose(self.out[i["head"], :, 3, :3], self.worlds[i["head"], :, 3, :3], atol=1e-9))
        others = [j for n, j in i.items() if n != "head"]
        self.assertTrue(np.allclose(self.out[others], self.worlds[others], atol=1e-12))

    def test_the_roll_about_the_look_stays_the_walk_s(self):
        """A least swing: the head's axis square to the look turns no more than the look itself does."""
        i = self.walk.index["head"]
        for f in range(self.out.shape[1]):
            before, after = ha._rigid(self.worlds[i, f]), ha._rigid(self.out[i, f])
            look0, _ = self.look(self.worlds, f)
            look1, _ = self.look(self.out, f)
            turn = angle(look0, look1)
            for row in range(3):
                self.assertLessEqual(angle(before[row, :3], after[row, :3]), turn + 1e-6)

    def test_share_zero_is_the_walk_and_a_half_turns_half_way(self):
        out, info = ha.apply(self.walk, self.worlds, self.aimed, 0.0)
        self.assertTrue(np.array_equal(out, self.worlds))
        half, _ = ha.apply(self.walk, self.worlds, self.aimed, 0.5)
        for f in (0, 5, 11):
            whole = angle(self.look(self.worlds, f)[0], self.look(self.out, f)[0])
            self.assertAlmostEqual(angle(self.look(self.worlds, f)[0], self.look(half, f)[0]), 0.5 * whole,
                                   places=6)

    def test_a_walker_without_a_head_is_left_alone_and_says_so(self):
        class NoHead(object):
            index = {"root": 0}
            parents = [-1]
        out, info = ha.apply(NoHead(), self.worlds[:1], self.aimed, 1.0)
        self.assertIn("head", info["note"])
        self.assertIn("not aimed", ha.line(self.aimed, 1.0, info))


class ParameterTests(unittest.TestCase):
    def test_head_aim_is_a_head_parameter_that_starts_at_one(self):
        param = [p for p in gait.PARAMS if p.name == "head_aim"][0]
        self.assertEqual(param.group, gait.HEAD)
        self.assertEqual(param.default, 1.0)
        self.assertIn("head_aim", wm.DEFAULTS)
        self.assertEqual(wm.DEFAULTS["head_aim"], 1.0)


class UpdateRereadsTheHead(FakedTest):
    def setUp(self):
        FakedTest.setUp(self)
        self.root = self.walker(working=True)
        self.first = {"version": ha.VERSION, "label": "head", "aim": [0.0, 0.0, 1.0], "target": [0.0, 160.0, 150.0]}
        edits = self.scene.walker_edits(self.root, "asd")[0]
        edits["head"] = dict(self.first)
        self.scene.set_edits(self.root, edits)
        meanrig.press(self.root)
        self.read = ha.read
        self.answer = dict(self.first)
        ha.read = lambda rig, aim=None: self.answer

    def tearDown(self):
        ha.read = self.read
        FakedTest.tearDown(self)

    def test_a_target_moved_on_the_rig_reaches_the_walker(self):
        self.answer = dict(self.first, target=[0.0, 140.0, 150.0])
        self.scene.applied = []
        line = meanrig.update()
        self.assertEqual(self.scene.edits[self.root]["head"]["target"], [0.0, 140.0, 150.0])
        self.assertTrue(self.scene.applied)
        self.assertIn("head target", line)

    def test_an_unmoved_target_says_nothing_moved(self):
        self.assertEqual(meanrig.update(), meanrig.NOTHING_MOVED)

    def test_a_target_gone_keeps_the_aim_and_says_so(self):
        def gone(rig, aim=None):
            raise ha.Refusal(ha.NO_TARGET)
        ha.read = gone
        line = meanrig.update()
        self.assertEqual(self.scene.edits[self.root]["head"]["target"], self.first["target"])
        self.assertIn("head aim kept", line)


if __name__ == "__main__":
    unittest.main()
