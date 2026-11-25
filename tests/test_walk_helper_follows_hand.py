"""A helper bone rigid to its own parent follows that parent, even when the parent rides a shallower bone rigidly.

2026-11-25: under the Weapon tab's Hold the right hand rides the chest rigidly, so weapon_r was rigid to hand_r AND
to the spine; `meanpose._follows` took the shallowest (the spine), and the rig pose's layer, which turns the arm,
left weapon_r - and the dagger on it - 20 cm off the hand.
"""
import unittest

import numpy as np

from maya_walk import meanpose as mp


def _m(t, rz=0.0):
    c, s = np.cos(rz), np.sin(rz)
    out = np.eye(4)
    out[:2, :2] = [[c, s], [-s, c]]
    out[3, :3] = t
    return out


class NearestAncestorFirst(unittest.TestCase):
    def setUp(self):
        # root -> spine_03 -> hand_r -> weapon_r ; the hand fixed on the spine, weapon_r fixed on the hand
        self.names = ["root", "spine_03", "hand_r", "weapon_r"]
        self.parents = [-1, 0, 1, 2]
        frames = 5
        W = np.zeros((4, frames, 4, 4))
        for f in range(frames):
            W[0, f] = _m([f * 10.0, 0, 0], rz=0.1 * f)        # the root moves and turns
            W[1, f] = _m([0, 100, 0], rz=0.05 * f) @ W[0, f]   # the spine turns on it
            W[2, f] = _m([30, 0, 0]) @ W[1, f]                 # the hand rigid on the spine (held)
            W[3, f] = _m([-7, -2, 3]) @ W[2, f]                # the weapon bone rigid on the hand
        self.W = W

    def test_a_helper_rigid_to_its_parent_follows_its_parent(self):
        helper = mp._helpers(self.names, self.parents)
        self.assertIn(3, helper)
        follows = mp._follows(self.W, helper, self.names, self.parents)
        self.assertEqual(follows[3][0], 2)       # hand_r, not spine_03
        np.testing.assert_allclose(follows[3][1][3, :3], [-7, -2, 3], atol=1e-9)

    def test_without_its_parent_rigid_the_shallowest_is_taken(self):
        W = self.W.copy()
        for f in range(W.shape[1]):                          # the hand now moves on the spine
            W[2, f] = _m([30, f * 2.0, 0]) @ W[1, f]
            W[3, f] = _m([-7, -2, 3]) @ W[1, f]              # the weapon bone rigid on the spine instead
        helper = mp._helpers(self.names, self.parents)
        follows = mp._follows(W, helper, self.names, self.parents)
        self.assertEqual(follows[3][0], 1)


if __name__ == "__main__":
    unittest.main()
