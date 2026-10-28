"""The aim engine shared by the weapon's and the camera's Aim Mode (2026-10-28): the weapon module
re-exports the pure halves from it, so one fix serves both."""

import unittest

from maya_scenesetup import aimcore
from maya_scenesetup import weaponaim as wa


class Shared(unittest.TestCase):

    def test_the_weapon_s_pure_halves_are_the_core_s(self):
        for name in ("diamond", "point_of", "up_axis", "turn_between", "frames_off", "broken"):
            self.assertIs(getattr(wa, name), getattr(aimcore, name), name)

    def test_the_weapon_kind_keeps_its_scene_names(self):
        kind = wa.KIND
        self.assertEqual((kind.marker, kind.ctrl_marker, kind.con_marker, kind.vectors_attr),
                         ("skeldarWeaponAim", "skeldarWeaponAimCtrl", "skeldarWeaponAimOf",
                          "skeldarWeaponAimVectors"))
        self.assertEqual(kind.group_name.format("Sword"), "Sword_aim")
        self.assertEqual(kind.enter_chunk, "Connections: Aim Mode")
        self.assertEqual(kind.leave_chunk, "Connections: Default")

    def test_the_world_level_is_one_word_for_both(self):
        self.assertEqual(wa.WORLD, aimcore.WORLD)


if __name__ == "__main__":
    unittest.main()
