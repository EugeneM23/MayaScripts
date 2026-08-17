"""Tests for connecting the arms to the weapon.

The two orchestrators drive OverRig through a live scene and are proved by
docs/superpowers/plans/verify_connect_arms.py. What is testable here is the
policy: which arms need converting, and how a link is recognised.
"""

import sys
import types
import unittest


def _install_fake_maya():
    """Let connect import without a Maya session.

    Real modules win when they are importable -- under mayapy they always are,
    and connect reaches maya_overrig.fkcontrols, which needs maya.api.OpenMaya
    as well. The fakes below are only for an interpreter with no Maya at all.
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

from maya_weapons import connect  # noqa: E402


class Arms(unittest.TestCase):

    def test_both_arms_and_nothing_else(self):
        self.assertEqual(connect.ARMS, ("arm_l", "arm_r"))


class LimbsToSwitch(unittest.TestCase):
    """Bringing a limb TO IK is not the same as switching it.

    switch_limbs converts to the opposite type, so calling it on an arm that
    is already IK hands back an FK arm -- the exact opposite of what the
    button promises.
    """

    def test_nothing_to_do_when_both_arms_are_ik(self):
        self.assertEqual(
            connect.limbs_to_switch({"arm_l": True, "arm_r": True}), [])

    def test_both_when_neither_is(self):
        self.assertEqual(
            connect.limbs_to_switch({"arm_l": False, "arm_r": False}),
            ["arm_l", "arm_r"])

    def test_only_the_fk_arm_in_a_mixed_rig(self):
        self.assertEqual(
            connect.limbs_to_switch({"arm_l": True, "arm_r": False}),
            ["arm_r"])

    def test_answers_in_arms_order(self):
        """So the status line reads the same way twice running."""
        self.assertEqual(
            connect.limbs_to_switch({"arm_r": False, "arm_l": False}),
            ["arm_l", "arm_r"])


class MarkedAncestor(unittest.TestCase):

    def test_finds_the_carrier_above_the_control(self):
        marked = {"|LongSword_02_weapon"}
        self.assertEqual(
            connect.marked_ancestor(
                "|LongSword_02_weapon|arm_r_IK_feet|ctrl",
                marked.__contains__),
            "|LongSword_02_weapon")

    def test_is_none_when_nothing_above_is_marked(self):
        self.assertIsNone(
            connect.marked_ancestor("|root_FK_ctrl|arm_r_IK_feet",
                                    set().__contains__))

    def test_takes_the_nearest_one(self):
        marked = {"|a", "|a|b"}
        self.assertEqual(
            connect.marked_ancestor("|a|b|c", marked.__contains__), "|a|b")

    def test_a_shared_prefix_is_not_an_ancestor(self):
        """'|swordExtra' is not inside '|sword'. Trap 7, once more."""
        self.assertIsNone(
            connect.marked_ancestor("|swordExtra|ctrl",
                                    {"|sword"}.__contains__))

    def test_the_node_itself_does_not_count(self):
        """A marked control would otherwise be read as its own carrier."""
        self.assertIsNone(
            connect.marked_ancestor("|sword", {"|sword"}.__contains__))

    def test_an_empty_path_answers_nothing(self):
        self.assertIsNone(connect.marked_ancestor("", set().__contains__))


class Messages(unittest.TestCase):

    def test_connect_names_what_it_did(self):
        message = connect.connected_message(["arm_r"], ["arm_l", "arm_r"])
        self.assertIn("arm_r", message)
        self.assertIn("2", message)

    def test_connect_says_when_the_arms_were_already_ik(self):
        message = connect.connected_message([], ["arm_l", "arm_r"])
        self.assertNotIn("switched", message.lower())

    def test_connect_reports_hanging_nothing(self):
        """Two arms in IK and neither hung means the link did not happen."""
        self.assertIn("0", connect.connected_message([], []))

    def test_disconnect_counts_the_hands(self):
        self.assertIn("2", connect.disconnected_message(["arm_l", "arm_r"]))

    def test_disconnect_promises_no_destination(self):
        """The hands go back under the root controller only if there is one.
        A rig built by Switch after a full bake has none and stands in world;
        measured in the user's scene, where the claim would have been false.
        """
        self.assertNotIn("root", connect.disconnected_message([]).lower())
