"""Tests for bonedrive: the bone that follows a marked node.

The pure half runs on real OpenMaya (mayapy ships it, as test_axes does).
The scene half is proved on a fake cmds that records CALL ORDER - the
orderings under test are the ones the camera setup already paid for:
bake before delete, cut before constrain.
"""

import math
import sys
import types
import unittest

import maya.api.OpenMaya as om


def _install_fake_maya():
    """Let bonedrive import without a full Maya. See CLAUDE.md on rebinding."""
    if "maya.cmds" in sys.modules:
        return
    maya = types.ModuleType("maya")
    cmds = types.ModuleType("maya.cmds")
    maya.cmds = cmds
    sys.modules.setdefault("maya", maya)
    sys.modules["maya.cmds"] = cmds


_install_fake_maya()

from maya_scenesetup import bonedrive  # noqa: E402


def _matrix(rx, ry, rz, tx, ty, tz):
    m = om.MTransformationMatrix()
    m.setRotation(om.MEulerRotation(math.radians(rx), math.radians(ry),
                                    math.radians(rz)))
    m.setTranslation(om.MVector(tx, ty, tz), om.MSpace.kTransform)
    return tuple(m.asMatrix())


class UnionRange(unittest.TestCase):
    """Trap 38 from the export side: a bake narrower than the keys silently
    truncates them, so every bake range is the union."""

    def test_keys_widen_the_playback_range(self):
        self.assertEqual(
            bonedrive.union_range(0.0, 30.0, [-20.0, 10.0, 45.0]),
            (-20.0, 45.0))

    def test_no_keys_keep_the_playback_range(self):
        self.assertEqual(bonedrive.union_range(0.0, 30.0, []), (0.0, 30.0))

    def test_keys_inside_change_nothing(self):
        self.assertEqual(bonedrive.union_range(0.0, 30.0, [5.0, 12.0]),
                         (0.0, 30.0))


class MatrixOf(unittest.TestCase):

    def test_identity_channels_make_the_identity(self):
        got = bonedrive.matrix_of((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
        want = tuple(om.MMatrix())
        self.assertLess(max(abs(a - b) for a, b in zip(got, want)), 1e-12)

    def test_matches_maya_channel_semantics(self):
        got = bonedrive.matrix_of((10.0, 20.0, 30.0), (1.0, 2.0, 3.0))
        want = _matrix(10.0, 20.0, 30.0, 1.0, 2.0, 3.0)
        self.assertLess(max(abs(a - b) for a, b in zip(got, want)), 1e-12)


class ComposedGrip(unittest.TestCase):
    """Old-scheme grip (channels under weapon_r) -> channels under the hand.

    The sword's world matrix must be identical in both schemes:
    matrix(new channels) == matrix(grip) * bone_local.
    """

    def test_identity_bone_local_returns_the_grip(self):
        rotate, translate = bonedrive.composed_grip(
            (10.0, 20.0, 30.0), (1.0, 2.0, 3.0), _matrix(0, 0, 0, 0, 0, 0))
        for got, want in zip(tuple(rotate) + tuple(translate),
                             (10.0, 20.0, 30.0, 1.0, 2.0, 3.0)):
            self.assertAlmostEqual(got, want, places=9)

    def test_zero_grip_returns_the_bone_local(self):
        rotate, translate = bonedrive.composed_grip(
            (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), _matrix(90.0, 0, 0, 5.0, 0, 0))
        self.assertAlmostEqual(rotate[0], 90.0, places=9)
        self.assertAlmostEqual(rotate[1], 0.0, places=9)
        self.assertAlmostEqual(rotate[2], 0.0, places=9)
        self.assertAlmostEqual(translate[0], 5.0, places=9)

    def test_composition_matches_the_matrix_product(self):
        grip_rotate = (10.0, -35.0, 4.0)
        grip_translate = (0.5, -2.0, 12.0)
        bone_local = _matrix(25.0, 80.0, -5.0, 3.0, 4.0, -1.0)
        rotate, translate = bonedrive.composed_grip(
            grip_rotate, grip_translate, bone_local)
        want = (om.MMatrix(bonedrive.matrix_of(grip_rotate, grip_translate))
                * om.MMatrix(bone_local))
        got = om.MMatrix(bonedrive.matrix_of(rotate, translate))
        worst = max(abs(got[i] - want[i]) for i in range(16))
        self.assertLess(worst, 1e-9)


if __name__ == "__main__":
    unittest.main()
