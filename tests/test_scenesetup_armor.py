"""The Armor card's scene rules (2026-10-01): which pieces an Equip takes off, what the
presses say, and the armor spaces kept apart from the weapons'. The scene half - a piece on its
bone where Unreal puts it, following a retarget, out of the export, gone after Unequip - is
docs/superpowers/plans/verify_armor.py's, in mayapy standalone.

Spec: docs/superpowers/specs/2026-10-01-armor-techlimb-design.md
"""

import os
import unittest

from maya_scenesetup import armor
from maya_scenesetup import catalog
from maya_scenesetup import weaponspace

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "SkeldarAnim")
TECH = catalog.ARMOR[0]


class SlotPlan(unittest.TestCase):

    def test_nothing_worn_takes_nothing_off(self):
        self.assertEqual(armor.slot_plan({}, TECH), [])

    def test_the_same_piece_again_is_replaced(self):
        self.assertEqual(armor.slot_plan({"Tech_Limb": "left_forearm"}, TECH),
                         ["Tech_Limb"])

    def test_another_piece_in_the_slot_comes_off(self):
        self.assertEqual(armor.slot_plan({"Other_Plate": "left_forearm"}, TECH),
                         ["Other_Plate"])

    def test_a_piece_in_another_slot_stays(self):
        self.assertEqual(armor.slot_plan({"Helmet": "head"}, TECH), [])

    def test_sorted_and_without_duplicates(self):
        worn = {"Z_Plate": "left_forearm", "Tech_Limb": "left_forearm", "Helmet": "head"}
        self.assertEqual(armor.slot_plan(worn, TECH), ["Tech_Limb", "Z_Plate"])


class Messages(unittest.TestCase):

    def test_equipped(self):
        self.assertEqual(
            armor.equipped_message("Tech Limb", "|Manny_Rig:root|x|Manny_Rig:lowerarm_l",
                                   "|Manny_Rig:root", [], "teal"),
            "Tech Limb on Manny_Rig's lowerarm_l, in teal")

    def test_equipped_over_what_the_slot_held(self):
        self.assertEqual(
            armor.equipped_message("Tech Limb", "|root|lowerarm_l", "|root",
                                   ["Tech Limb"], ""),
            "Tech Limb on root's lowerarm_l (replaced Tech Limb)")

    def test_unequipped(self):
        self.assertEqual(armor.unequipped_message("Tech Limb", "|Creep_Rig:Armature|Creep_Rig:root"),
                         "Tech Limb taken off Creep_Rig")

    def test_not_worn(self):
        self.assertEqual(armor.not_worn_message("Tech Limb", "|root"),
                         "root does not wear Tech Limb")

    def test_no_bone(self):
        self.assertEqual(armor.no_bone_message("Tech Limb", "lowerarm_l", "|root"),
                         "Tech Limb rides lowerarm_l - root has no such bone")

    def test_missing_file(self):
        self.assertEqual(armor.missing_message("Tech Limb", "C:/x/Tech_Limb.fbx"),
                         "Tech Limb: the model is missing - C:/x/Tech_Limb.fbx")

    def test_pick(self):
        self.assertEqual(armor.pick_message("Tech Limb", "lowerarm_l", True),
                         "Tech Limb (lowerarm_l) - worn: Equip puts it on again, Unequip takes it off")
        self.assertEqual(armor.pick_message("Tech Limb", "lowerarm_l", False),
                         "Tech Limb (lowerarm_l) - press Equip")


class Inside(unittest.TestCase):

    def test_a_bone_under_the_root(self):
        self.assertTrue(armor.inside("|ns:root|ns:pelvis|ns:lowerarm_l", "|ns:root"))

    def test_the_root_itself(self):
        self.assertTrue(armor.inside("|root", "|root"))

    def test_the_separator_matters(self):
        self.assertFalse(armor.inside("|root1|lowerarm_l", "|root"))

    def test_nothing(self):
        self.assertFalse(armor.inside(None, "|root"))
        self.assertFalse(armor.inside("|root|a", None))


class Spaces(unittest.TestCase):
    """The armor space is the weapons' shape with markers of its own."""

    def test_its_own_markers(self):
        self.assertNotEqual(armor.SPACE_MARKER, weaponspace.SPACE_MARKER)
        self.assertNotEqual(armor.GROUP_MARKER, weaponspace.GROUP_MARKER)
        self.assertEqual((armor.SPACE_MARKER, armor.GROUP_MARKER, armor.GROUP_NAME),
                         ("mayaArmorSpace", "mayaArmorSpaces", "ArmorSpaces"))

    def test_the_name_follows_the_bone(self):
        self.assertEqual(weaponspace.space_name("|ns:root|ns:lowerarm_l", armor.SUFFIX),
                         "lowerarm_l_armorSpace")
        self.assertEqual(weaponspace.space_name("|root|hand_r"), "hand_r_weaponSpace")

    def test_the_module_goes_through_weaponspace(self):
        with open(os.path.join(PLUGIN, "maya_scenesetup", "armor.py"),
                  encoding="utf-8") as handle:
            source = handle.read()
        for name in ("ensure_marked_space", "marked_space_of", "prune_marked", "owner_for"):
            self.assertIn("weaponspace." + name, source)
        self.assertNotIn('ls("*.', source)          # trap 70


class SelectionNamesTheCharacter(unittest.TestCase):

    def test_current_root_resolves_an_armor_piece_to_its_bone(self):
        with open(os.path.join(PLUGIN, "maya_scenesetup", "skeleton.py"),
                  encoding="utf-8") as handle:
            source = handle.read()
        self.assertIn("armor.bone_for(path)", source)


if __name__ == "__main__":
    unittest.main()
