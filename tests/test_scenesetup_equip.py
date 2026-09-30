"""The inventory's scene actions (2026-09-29): which bone a floor drop takes,
and what each action says. The actions themselves are the Weapons section's
machinery and are proved in docs/superpowers/plans/verify_inventory.py.

Spec: docs/superpowers/specs/2026-09-29-weapon-inventory-design.md
"""

import os
import unittest

from maya_scenesetup import equip

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "SkeldarAnim")


class FloorSide(unittest.TestCase):

    def test_the_free_right_first(self):
        self.assertEqual(equip.floor_side({"R": False, "L": False}), "R")

    def test_the_free_left_when_the_right_is_taken(self):
        self.assertEqual(equip.floor_side({"R": True, "L": False}), "L")

    def test_both_taken_replaces_the_right(self):
        self.assertEqual(equip.floor_side({"R": True, "L": True}), "R")


class Messages(unittest.TestCase):

    def test_into_a_hand(self):
        self.assertEqual(
            equip.into_message("Long Sword 02", "|Manny_Rig:root", "L"),
            "Long Sword 02 into Manny_Rig's left hand")

    def test_onto_the_floor(self):
        self.assertEqual(
            equip.floor_message("Spear 01", "|Manny_Rig:root", "L"),
            "Spear 01 onto the floor - Manny_Rig's weapon_l follows it")

    def test_off(self):
        self.assertEqual(
            equip.off_message("Dagger 01", "|root", "R"),
            "Dagger 01 off root's right hand - the bone has its animation back")

    def test_a_character_is_named_by_its_rig_namespace_or_its_root(self):
        self.assertEqual(equip.character_name(
            "|Creep_Rig:Armature|Creep_Rig:root"), "Creep_Rig")
        self.assertEqual(equip.character_name("|root"), "root")
        self.assertEqual(equip.character_name(None), "")


class Boundaries(unittest.TestCase):
    """The inventory uses the Weapons section's own machinery - it can never
    disagree with the panel about what a weapon in a hand is."""

    def _source(self):
        with open(os.path.join(PLUGIN, "maya_scenesetup", "equip.py"),
                  encoding="utf-8") as handle:
            return handle.read()

    def test_a_hand_goes_through_attach_with_the_hands_grip(self):
        source = self._source()
        self.assertIn("grips.for_hand(entry, side, root)", source)
        self.assertIn("attach.attach(entry, hand, bone, rotate, translate)",
                      source)

    def test_the_inventory_remembers_no_grip(self):
        """2026-09-30: the inventory dials nothing, so it stores nothing - a
        stored copy of the left hand's mirror froze it (the next rig got
        Manny's numbers, not its own sockets'); the fields remember."""
        self.assertNotIn("grips.remember(", self._source())

    def test_the_floor_goes_through_floor_drop(self):
        self.assertIn("floor.drop(entry, bone, point, heading)", self._source())

    def test_taking_off_is_detach(self):
        self.assertIn("attach.detach(hand, bone)", self._source())

    def test_every_action_is_one_undo_chunk(self):
        source = self._source()
        self.assertEqual(source.count("undoInfo(openChunk=True"),
                         source.count("undoInfo(closeChunk=True)"))
        self.assertGreaterEqual(source.count("undoInfo(openChunk=True"), 4)
