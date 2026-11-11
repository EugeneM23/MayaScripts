"""Walk Builder's Snap weapon: the weapon lies on the shoulder through the whole walk (2026-11-11).

The spec: docs/superpowers/specs/2026-11-11-walk-snap-weapon-design.md. The synthetic walker of
tests.test_walkmodel stands in for the rig pose too: its frame 0 is "the rig", a blade put in its right hand
aiming at a point above its right clavicle, an up point beside it. Its chest turns and bobs and its clavicles
shrug, so the hand moves against the body and every gate below can fail.
"""

import unittest

import numpy as np

from tests import test_walkmodel as T

wm = T.wm
sw = T.load("snapweapon")

GRIP = np.array([0.0, -2.0, 3.0])        # the weapon's grip in the right hand's frame
AIM_V, UP_V = (0.0, 1.0, 0.0), (1.0, 0.0, 0.0)


def pt(local, m):
    return np.asarray(local, float) @ m[:3, :3] + m[3, :3]


def rig_of(worlds, walk, f=0, two_hands=False):
    """(mats, weapon world, target, up): the walker's own frame `f` read as the rig pose."""
    mats = dict((name, np.asarray(worlds[walk.index[name], f], float))
                for name in ("hand_l", "hand_r", "clavicle_l", "clavicle_r", "root"))
    hand = sw._rigid(mats["hand_r"])
    grip = pt(GRIP, hand)
    target = mats["clavicle_r"][3, :3] + np.array([0.0, 8.0, 0.0])
    up = grip + np.array([40.0, 30.0, 0.0])
    B = sw.basis(target - grip, up - grip)            # rows aim, up, side -> the weapon's y, x, -z
    W = np.eye(4)
    W[0, :3], W[1, :3], W[2, :3] = B[1], B[0], -B[2]
    W[3, :3] = grip
    if two_hands:                                     # the left hand on the blade, a little past the grip
        left = np.array(mats["hand_l"])
        left[3, :3] = grip + sw._unit(target - grip) * 10.0
        mats["hand_l"] = left
    return mats, W, target, up


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.walk = T.walk()
        knobs = {"arm_drag": 0.0, "torso_drag": 0.0, "head_drag": 0.0, "balance": 0.0}
        cls.worlds = np.asarray(cls.walk.evaluate(knobs, None).worlds, float)

    def snap(self, **kw):
        mats, W, target, up = rig_of(self.worlds, self.walk, **kw)
        return sw.record(mats, "r", W, AIM_V, UP_V, target, up, "Sword")

    def mats(self, worlds, name):
        return np.asarray(worlds[self.walk.index[name]], float)


class RecordTests(Base):
    def test_the_target_is_kept_in_the_clavicle_nearest_it(self):
        snap = self.snap()
        self.assertEqual(snap["side"], "r")
        self.assertEqual(snap["anchor"], "r")
        C = sw._rigid(self.mats(self.worlds, "clavicle_r")[0])
        want = C[3, :3] + np.array([0.0, 8.0, 0.0])
        self.assertLess(np.linalg.norm(pt(snap["target"], C) - want), 1e-9)

    def test_a_free_other_hand_is_not_recorded_one_on_the_blade_is(self):
        self.assertIsNone(self.snap()["other"])
        self.assertIsNotNone(self.snap(two_hands=True)["other"])

    def test_loads_round_trips_and_refuses_broken_data(self):
        snap = self.snap()
        self.assertEqual(sw.loads(snap), snap)
        self.assertIsNone(sw.loads(dict(snap, version=99)))
        self.assertIsNone(sw.loads(dict(snap, grip=[1.0])))
        self.assertIsNone(sw.loads(None))
        self.assertIsNone(sw.loads({"version": 1}))


class ApplyTests(Base):
    @classmethod
    def setUpClass(cls):
        super(ApplyTests, cls).setUpClass()
        mats, W, target, up = rig_of(cls.worlds, cls.walk)
        cls.snapped = sw.record(mats, "r", W, AIM_V, UP_V, target, up, "Sword")
        cls.out, cls.info = sw.apply(cls.walk, cls.worlds, cls.snapped)

    def test_the_input_is_not_changed(self):
        again = np.asarray(self.walk.evaluate({"arm_drag": 0.0, "torso_drag": 0.0, "head_drag": 0.0,
                                               "balance": 0.0}, None).worlds, float)
        self.assertLess(float(np.max(np.abs(again - self.worlds))), 1e-12)

    def test_the_grip_rides_the_clavicle_on_every_frame(self):
        off = sw._m(self.snapped["offset"])
        C, H = self.mats(self.out, "clavicle_r"), self.mats(self.out, "hand_r")
        worst = max(np.linalg.norm(pt(GRIP, sw._rigid(H[f])) - pt(GRIP, off @ sw._rigid(C[f])))
                    for f in range(len(H)))
        self.assertLess(worst, 1e-6)
        # ... while in the walk itself the hand swings against the clavicle (so the gate can fail)
        C0, H0 = self.mats(self.worlds, "clavicle_r"), self.mats(self.worlds, "hand_r")
        free = max(np.linalg.norm(pt(GRIP, sw._rigid(H0[f])) - pt(GRIP, off @ sw._rigid(C0[f])))
                   for f in range(len(H0)))
        self.assertGreater(free, 1.0)

    def test_the_blade_passes_through_the_shoulder_point_and_rolls_toward_the_up(self):
        H, C, R = (self.mats(self.out, n) for n in ("hand_r", "clavicle_r", "root"))
        aim, upax = np.asarray(self.snapped["aim"]), np.asarray(self.snapped["up_axis"])
        for f in range(len(H)):
            h = sw._rigid(H[f])
            G = pt(GRIP, h)
            T_ = pt(self.snapped["target"], sw._rigid(C[f]))
            U = pt(self.snapped["up"], sw._rigid(R[f]))
            a = sw._unit(aim @ h[:3, :3])
            to = T_ - G
            self.assertLess(np.linalg.norm(np.cross(a, to)), 1e-6)
            self.assertGreater(float(np.dot(a, to)), 0.0)
            u = upax @ h[:3, :3]
            side = np.cross(a, U - G)
            self.assertLess(abs(float(np.dot(u, sw._unit(side)))), 1e-6)       # in the aim / up plane
            self.assertGreater(float(np.dot(u, U - G)), 0.0)                  # leaning toward the up

    def test_the_arm_keeps_its_bones_and_reaches(self):
        idx = self.walk.index
        for a, b in (("upperarm_r", "lowerarm_r"), ("lowerarm_r", "hand_r")):
            d0 = np.linalg.norm(self.worlds[idx[b], :, 3, :3] - self.worlds[idx[a], :, 3, :3], axis=1)
            d1 = np.linalg.norm(self.out[idx[b], :, 3, :3] - self.out[idx[a], :, 3, :3], axis=1)
            self.assertLess(float(np.max(np.abs(d1 - d0.mean()))), 1e-3)
        self.assertLess(self.info["off"], 1e-6)
        self.assertEqual(self.info["note"], "")

    def test_the_finger_rides_the_hand(self):
        idx = self.walk.index
        for f in range(self.out.shape[1]):       # the finger's own animation in the hand, kept frame for frame
            rel0 = self.worlds[idx["index_01_r"], f] @ np.linalg.inv(self.worlds[idx["hand_r"], f])
            rel = self.out[idx["index_01_r"], f] @ np.linalg.inv(self.out[idx["hand_r"], f])
            self.assertLess(float(np.max(np.abs(rel - rel0))), 1e-6)

    def test_the_body_and_the_other_arm_are_untouched(self):
        idx = self.walk.index
        for name in ("pelvis", "spine_02", "head", "clavicle_r", "hand_l", "foot_l"):
            self.assertLess(float(np.max(np.abs(self.out[idx[name]] - self.worlds[idx[name]]))), 1e-12, name)

    def test_the_line_says_it(self):
        self.assertIn("Sword on the right shoulder, right hand", sw.line(self.snapped, self.info))


class TwoHandsTests(Base):
    def test_the_other_hand_holds_its_offset_from_the_holding_hand(self):
        snap = self.snap(two_hands=True)
        out, info = sw.apply(self.walk, self.worlds, snap)
        O = sw._m(snap["other"])
        H, L = self.mats(out, "hand_r"), self.mats(out, "hand_l")
        worst = max(np.linalg.norm(L[f, 3, :3] - (O @ sw._rigid(H[f]))[3, :3]) for f in range(len(H)))
        self.assertLess(worst, max(info["off"], 1e-6) + 1e-6)


class MissingTests(Base):
    def test_a_walker_without_the_bones_is_left_alone_and_says_so(self):
        snap = dict(self.snap(), side="l", anchor="l")
        walk = self.walk
        saved = dict(walk.index)
        try:
            del walk.index["clavicle_l"]
            out, info = sw.apply(walk, self.worlds, snap)
        finally:
            walk.index.clear()
            walk.index.update(saved)
        self.assertIs(out, self.worlds)
        self.assertIn("clavicle_l", info["note"])


if __name__ == "__main__":
    unittest.main()
