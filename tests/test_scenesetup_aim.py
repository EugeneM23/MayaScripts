"""Tests for placing OverRig's aim on the weapon.

The build itself drives OverRig through a live scene and is proved by
docs/superpowers/plans/verify_weapon_aim.py. What is testable here is the
placement: where the two locators go, given the model's measured extents.

The numbers are the real LongSword_02, measured in the user's scene through the
command port -- 1382 mesh points, extents in the model's own local frame.
"""

import sys
import types
import unittest


def _install_fake_maya():
    """Let aim import without a Maya session.

    Real modules win when they are importable -- under mayapy they always are.
    The fakes below are only for an interpreter with no Maya at all.
    """
    try:
        import maya.api.OpenMaya  # noqa: F401
        import maya.cmds  # noqa: F401
        import maya.mel  # noqa: F401
        return
    except ImportError:
        pass

    maya = types.ModuleType("maya")
    api = types.ModuleType("maya.api")
    openmaya = types.ModuleType("maya.api.OpenMaya")
    cmds = types.ModuleType("maya.cmds")
    mel = types.ModuleType("maya.mel")
    maya.cmds = cmds
    maya.mel = mel
    maya.api = api
    api.OpenMaya = openmaya
    sys.modules.setdefault("maya", maya)
    sys.modules["maya.api"] = api
    sys.modules["maya.api.OpenMaya"] = openmaya
    sys.modules["maya.cmds"] = cmds
    sys.modules["maya.mel"] = mel


_install_fake_maya()

from maya_scenesetup import aim  # noqa: E402

# LongSword_02 as measured: the crossguard on X, the blade up Y with its tip at
# +115.925, the blade's thickness on Z.
SWORD_LO = (-15.576, -31.119, -1.570)
SWORD_HI = (15.576, 115.925, 1.570)


class Margin(unittest.TestCase):

    def test_fifteen_percent(self):
        self.assertEqual(aim.MARGIN, 0.15)


class Placement(unittest.TestCase):

    def test_top_goes_past_the_tip_along_the_blade(self):
        top, _side = aim.placement(SWORD_LO, SWORD_HI)
        self.assertAlmostEqual(top[1], 115.925 * 1.15, places=3)
        self.assertEqual(top[0], 0.0)
        self.assertEqual(top[2], 0.0)

    def test_top_clears_the_tip_rather_than_sitting_on_it(self):
        top, _side = aim.placement(SWORD_LO, SWORD_HI)
        self.assertGreater(top[1], 115.925)

    def test_side_goes_on_the_crossguard_axis(self):
        _top, side = aim.placement(SWORD_LO, SWORD_HI)
        self.assertEqual(side[1], 0.0)
        self.assertEqual(side[2], 0.0)
        self.assertNotEqual(side[0], 0.0)

    def test_side_sits_at_the_same_distance_as_top(self):
        """The user asked for the same distance, and a long lever makes the
        roll control precise."""
        top, side = aim.placement(SWORD_LO, SWORD_HI)
        self.assertAlmostEqual(abs(side[0]), abs(top[1]), places=6)

    def test_a_symmetric_axis_ties_positive(self):
        """A blade is symmetric across its width, so the tie IS the normal
        case and it must not depend on sort luck."""
        _top, side = aim.placement(SWORD_LO, SWORD_HI)
        self.assertGreater(side[0], 0.0)

    def test_a_model_authored_down_negative_y_points_the_other_way(self):
        """The signed further end is what makes this work with no special
        case."""
        top, _side = aim.placement((-15.0, -115.925, -1.0),
                                   (15.0, 31.119, 1.0))
        self.assertAlmostEqual(top[1], -115.925 * 1.15, places=3)

    def test_a_blade_along_x_is_found_too(self):
        top, side = aim.placement((-2.0, -3.0, -1.0), (90.0, 3.0, 1.0))
        self.assertAlmostEqual(top[0], 90.0 * 1.15, places=3)
        self.assertEqual(top[1], 0.0)
        self.assertNotEqual(side[1], 0.0)

    def test_the_two_locators_never_share_an_axis(self):
        top, side = aim.placement(SWORD_LO, SWORD_HI)
        moved = [axis for axis in range(3)
                 if top[axis] != 0.0 and side[axis] != 0.0]
        self.assertEqual(moved, [])

    def test_a_flat_model_has_no_placement(self):
        self.assertIsNone(aim.placement((0.0, 0.0, 0.0), (0.0, 0.0, 0.0)))

    def test_a_bigger_margin_pushes_top_further(self):
        near, _ = aim.placement(SWORD_LO, SWORD_HI, margin=0.0)
        far, _ = aim.placement(SWORD_LO, SWORD_HI, margin=1.0)
        self.assertAlmostEqual(near[1], 115.925, places=3)
        self.assertGreater(far[1], near[1])

    def test_ties_for_longest_break_by_axis_order(self):
        """A cube would otherwise depend on sort stability."""
        top, side = aim.placement((0.0, 0.0, 0.0), (10.0, 10.0, 10.0))
        self.assertEqual(top[0], 10.0 * 1.15)
        self.assertNotEqual(side[1], 0.0)


class Messages(unittest.TestCase):

    def test_the_added_message_names_the_locator_to_drag(self):
        message = aim.added_message("Long Sword 02",
                                    "|c|sword|LongSwordMesh_top")
        self.assertIn("Long Sword 02", message)
        self.assertIn("LongSwordMesh_top", message)
        self.assertNotIn("|", message)

    def test_the_added_message_warns_that_rotate_is_now_inert(self):
        """The constraint fixes the geometry's world orientation, so turning
        the carrier is compensated away. A dead field the animator has to
        discover on their own is worse than a noisy status line."""
        self.assertIn("Rotate", aim.added_message("X", "|x_top"))

    def test_the_already_message_names_the_cure(self):
        self.assertIn("Bake+Delete", aim.ALREADY_MESSAGE)

    def test_the_no_geometry_message_says_what_is_missing(self):
        self.assertIn("geometry", aim.NO_GEOMETRY_MESSAGE)


if __name__ == "__main__":
    unittest.main()
