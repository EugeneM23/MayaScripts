"""One arm out of Walk Builder's additive pose, playing the cycle (2026-11-02).

The spec: docs/superpowers/specs/2026-11-02-walk-one-arm-out-of-the-pose-design.md. The synthetic walker is
tests.test_walkmodel's; the card's chips run on tests.test_walk_panel's fake cmds.
"""

import math
import unittest

import numpy as np

from tests import test_walkmodel as T
from tests.test_walktarget import statics_of

wm = T.wm
wp = T.load("pose")
wt = T.load("target")


def prepared(frame=5):
    """A real prepared pose for the synthetic walker: the walker as it stands at `frame`."""
    clip = T.clip()
    walk = wm.analyse(clip)
    bones = statics_of(clip)
    for j, name in enumerate(clip.names):
        bones[name]["world"] = [float(v) for v in clip.worlds[j, frame].reshape(16)]
    return walk, wp.prepare(walk, statics_of(clip), bones, wm, wt)


def local_of(result, name, walk, f):
    j, p = walk.index[name], walk.parents[walk.index[name]]
    R = result.worlds[:, f, :3, :3]
    return wm.orthonormal(R[j]) @ wm.orthonormal(R[p]).T


def deg(r):
    return math.degrees(float(np.linalg.norm(wm.log_rot(wm.orthonormal(np.asarray(r, float))))))


class PartTests(unittest.TestCase):
    """The chips' own table: one part a side."""

    def test_the_parts_name_each_arm(self):
        names = [part for part, _ in wp.PARTS]
        self.assertIn("arm_l", names)
        self.assertIn("arm_r", names)
        self.assertNotIn("arms", names)

    def test_an_old_stored_list_means_both_arms(self):
        self.assertEqual(wp.parts_read(("torso", "arms")), ("torso", "arm_l", "arm_r"))

    def test_a_name_this_build_does_not_know_is_dropped_and_the_new_ones_kept(self):
        self.assertEqual(wp.parts_read(("arm_r", "wings")), ("arm_r",))
        self.assertEqual(wp.parts_read(wp.ALL_PARTS), tuple(wp.ALL_PARTS))

    def test_the_scene_s_list_of_every_part_has_both_arms(self):
        scene = T.load("scene")
        self.assertIn("arm_l", scene.ALL_PARTS)
        self.assertIn("arm_r", scene.ALL_PARTS)


class FilteredTests(unittest.TestCase):

    def setUp(self):
        self.walk, self.pose = prepared()
        self.left = set(j for j, side in self.pose["arm_side"].items() if side == "l")
        self.right = set(j for j, side in self.pose["arm_side"].items() if side == "r")

    def test_prepare_names_each_arm_joint_s_side(self):
        self.assertTrue(self.left and self.right)
        self.assertEqual(set(self.pose["arms"]), self.left | self.right)
        for j in self.left:
            self.assertTrue(self.walk.names[j].endswith("_l"), self.walk.names[j])

    def test_both_chips_on_keep_the_pose_whole(self):
        out = wp.filtered(self.pose, wp.ALL_PARTS)
        self.assertEqual(set(out["arms"]), set(self.pose["arms"]))
        self.assertEqual(bool(out["grip"]), bool(self.pose["grip"]))

    def test_one_chip_off_keeps_that_side_out_of_the_arms(self):
        out = wp.filtered(self.pose, [p for p in wp.ALL_PARTS if p != "arm_l"])
        self.assertEqual(set(out["arms"]), self.right)
        out = wp.filtered(self.pose, [p for p in wp.ALL_PARTS if p != "arm_r"])
        self.assertEqual(set(out["arms"]), self.left)

    def test_neither_chip_drops_the_arms_whole(self):
        out = wp.filtered(self.pose, [p for p in wp.ALL_PARTS if p not in ("arm_l", "arm_r")])
        for key in ("arms", "weapons", "grip"):
            self.assertNotIn(key, out)

    def test_an_old_stored_list_still_gives_both_arms(self):
        out = wp.filtered(self.pose, ("torso", "arms"))
        self.assertEqual(set(out["arms"]), set(self.pose["arms"]))

    def test_the_grip_needs_both_arms(self):
        pose = dict(self.pose)
        pose["grip"] = True
        self.assertTrue(wp.filtered(pose, wp.ALL_PARTS)["grip"])
        self.assertFalse(wp.filtered(pose, [p for p in wp.ALL_PARTS if p != "arm_l"])["grip"])

    def test_a_weapon_goes_with_the_hand_that_holds_it(self):
        pose = dict(self.pose)
        pose["weapons"] = {90: np.eye(4), 91: np.eye(4), 92: np.eye(4)}
        pose["weapon_side"] = {90: "l", 91: "r", 92: None}
        out = wp.filtered(pose, [p for p in wp.ALL_PARTS if p != "arm_l"])
        self.assertEqual(sorted(out["weapons"]), [91, 92], "the left hand's weapon goes, a sideless one stays")
        out = wp.filtered(pose, wp.ALL_PARTS)
        self.assertEqual(sorted(out["weapons"]), [90, 91, 92])


class ModelTests(unittest.TestCase):
    """What the model does with one arm named and the other not: the named one stands in the pose, the other
    plays the cycle - its own mean, its own swing, its upper arm hanging in the world."""

    KNOBS = {"pose": 1.0, "balance": 0.0, "arm_drag": 0.0, "torso_drag": 0.0, "head_drag": 0.0,
             "arm_overlap": 0.0, "elbow_overlap": 0.0, "hand_overlap": 0.0}

    def setUp(self):
        self.walk, self.pose = prepared()
        self.pose = dict(self.pose, grip=True)          # the two-handed case: today it stills both arms
        self.both = self.walk.evaluate(self.KNOBS, wp.filtered(self.pose, wp.ALL_PARTS))
        self.none = self.walk.evaluate(self.KNOBS, wp.filtered(
            self.pose, [p for p in wp.ALL_PARTS if p not in ("arm_l", "arm_r")]))
        self.right_only = self.walk.evaluate(self.KNOBS, wp.filtered(
            self.pose, [p for p in wp.ALL_PARTS if p != "arm_l"]))

    BONES = ("upperarm", "lowerarm", "hand")
    FRAMES = (0, 6, 13, 19)

    def arm_frames(self, result, side):
        return [local_of(result, "%s_%s" % (bone, side), self.walk, f)
                for bone in self.BONES for f in self.FRAMES]

    def arm_worlds(self, result, side):
        """The arm's rotations in the WORLD: what the cycle gives it, free of where the posed chest stands."""
        out = []
        for bone in self.BONES + ("index_01",):
            name = "%s_%s" % (bone, side)
            if name not in self.walk.index:
                continue
            j = self.walk.index[name]
            out += [wm.orthonormal(result.worlds[j, f, :3, :3]) for f in self.FRAMES]
        return out

    def test_the_excluded_arm_plays_the_cycle(self):
        """In the WORLD, to the digit: its own mean and its own swing. Its local against its parent does differ -
        the clavicle over it stands where the pose puts the chest, and the arm hangs from that chest."""
        for mine, theirs in zip(self.arm_worlds(self.right_only, "l"), self.arm_worlds(self.none, "l")):
            self.assertLess(deg(mine @ theirs.T), 0.01)

    def test_and_it_is_not_what_the_pose_asked(self):
        apart = max(deg(a @ b.T) for a, b in zip(self.arm_worlds(self.right_only, "l"),
                                                 self.arm_worlds(self.both, "l")))
        self.assertGreater(apart, 1.0, "the pose does move the left arm, so the exclusion is visible")

    def test_the_arm_the_pose_keeps_is_untouched_by_the_mixing(self):
        """Its mean and its stilling: the hand that holds the thing goes on holding it. The two-handed CARRY is
        off, and that one does move the kept arm - 9.4 deg on the animator's own sword pose (the verify's gate
        5); these knobs have the springs and the carry off, so what is measured here is the mixing alone."""
        for mine, theirs in zip(self.arm_frames(self.right_only, "r"), self.arm_frames(self.both, "r")):
            self.assertLess(deg(mine @ theirs.T), 0.01)

    def test_the_two_handed_hold_itself_is_off(self):
        out = wp.filtered(self.pose, [p for p in wp.ALL_PARTS if p != "arm_l"])
        self.assertFalse(out["grip"], "one hand cannot hold a thing with two")
        self.assertEqual(out["grip_sides"], ("r",), "and the right arm is still held still by the pose")

    def test_a_pose_from_before_the_split_stills_both_arms(self):
        pose = dict(self.pose)
        pose.pop("grip_sides", None)
        r = self.walk.evaluate(self.KNOBS, pose)             # unfiltered, as the verify scripts hand it over
        for mine, theirs in zip(self.arm_frames(r, "l"), self.arm_frames(self.both, "l")):
            self.assertLess(deg(mine @ theirs.T), 0.01)

    def test_the_excluded_upper_arm_swings_as_the_cycle_does(self):
        """With no pose its upper arm hangs and swings in the WORLD; excluded, it does again."""
        j = self.walk.index["upperarm_l"]
        swing = lambda r: max(deg(wm.orthonormal(r.worlds[j, f, :3, :3])
                                  @ wm.orthonormal(r.worlds[j, 0, :3, :3]).T) for f in range(self.walk.P))
        self.assertAlmostEqual(swing(self.right_only), swing(self.none), delta=0.02)
        self.assertGreater(swing(self.none) - swing(self.both), 1.0, "the grip stills it in the pose")

    def test_the_excluded_side_s_fingers_play_the_cycle_too(self):
        name = "index_01_l"
        if name not in self.walk.index:
            self.skipTest("the fixture has no fingers")
        for f in (0, 6, 13):
            self.assertLess(deg(local_of(self.right_only, name, self.walk, f)
                                @ local_of(self.none, name, self.walk, f).T), 0.01)

    def test_the_excluded_arm_hangs_from_the_chest_the_pose_stands_in(self):
        """What its local difference IS: its parent's, to the digit - the body's doing, not the arm's."""
        for f in self.FRAMES:
            arm = deg(local_of(self.right_only, "upperarm_l", self.walk, f)
                      @ local_of(self.none, "upperarm_l", self.walk, f).T)
            j = self.walk.index["clavicle_l"]
            parent = deg(wm.orthonormal(self.right_only.worlds[j, f, :3, :3])
                         @ wm.orthonormal(self.none.worlds[j, f, :3, :3]).T)
            self.assertAlmostEqual(arm, parent, delta=0.01, msg=f)


class ChipTests(unittest.TestCase):
    """The card's two chips."""

    def test_the_card_has_a_chip_a_side(self):
        panel = T.load("panel")
        labels = dict(panel.PART_LABELS)
        self.assertEqual(labels.get("arm_l"), "Arm L")
        self.assertEqual(labels.get("arm_r"), "Arm R")
        self.assertNotIn("arms", labels)


if __name__ == "__main__":
    unittest.main()
