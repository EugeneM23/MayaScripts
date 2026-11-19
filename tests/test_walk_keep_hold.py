"""The rig pose's layer keeps a two-handed hold (2026-11-19: «левая рука соскочила и не следует за оружием»)."""

import unittest

import numpy as np

from maya_walk import keyposes as kp


def rigid(deg, t):
    a = np.radians(deg)
    m = np.eye(4)
    m[:3, :3] = [[np.cos(a), np.sin(a), 0], [-np.sin(a), np.cos(a), 0], [0, 0, 1]]
    m[3, :3] = t
    return m


class FakeWalk(object):
    """Two hands and nothing else: _arm_to_hand puts the hand where asked."""
    index = {"hand_l": 0, "hand_r": 1}

    def _arm_chains(self):
        return {"l": [0], "r": [1]}

    def _arm_to_hand(self, kin, n, chains, hands):
        return {chains[s][-1]: h for s, h in hands.items()}

    def _reattach(self, worlds, kin, new):
        for j, m in new.items():
            worlds[j] = m


def frames(rels, rights):
    w = np.zeros((2, len(rights), 4, 4))
    for f, (rel, right) in enumerate(zip(rels, rights)):
        w[1, f] = right
        w[0, f] = rel @ right
    return w


class KeepHold(unittest.TestCase):
    def setUp(self):
        self.rights = [rigid(10.0 * f, (f, 2.0 * f, 0.0)) for f in range(6)]
        self.hold = rigid(30.0, (4.0, -13.0, -15.0))

    def test_a_held_pair_comes_back_held(self):
        before = frames([self.hold] * 6, self.rights)
        wander = [rigid(30.0 + 3.0 * np.sin(f), (4.0 + np.cos(f), -13.0, -15.0)) for f in range(6)]
        after = frames(wander, self.rights)
        out, carrier = kp.keep_hold(FakeWalk(), before, after, {"r": {}})
        self.assertEqual(carrier, "r")
        rel = kp._relation(out, 0, 1)
        self.assertLess(np.max(np.abs(rel - rel[0])), 1e-9)
        np.testing.assert_allclose(out[1], after[1])

    def test_hands_that_did_not_hold_are_left_alone(self):
        before = frames([rigid(30.0, (4.0 + f, -13.0, -15.0)) for f in range(6)], self.rights)
        after = frames([rigid(40.0, (5.0, -13.0, -15.0))] * 6, self.rights)
        out, carrier = kp.keep_hold(FakeWalk(), before, after)
        self.assertIsNone(carrier)
        self.assertIs(out, after)

    def test_the_mean_of_rigid_matrices_is_rigid(self):
        m = kp._mean_rigid(np.array([rigid(10.0, (1, 0, 0)), rigid(20.0, (3, 0, 0))]))
        np.testing.assert_allclose(m[:3, :3] @ m[:3, :3].T, np.eye(3), atol=1e-12)
        np.testing.assert_allclose(m[3, :3], (2, 0, 0))


if __name__ == "__main__":
    unittest.main()
