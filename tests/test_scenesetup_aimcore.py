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


class KeysIn(unittest.TestCase):
    """The controllers' key times kept for a re-entry after a parent move: inside the span, once."""

    def test_the_union_in_order_each_once(self):
        self.assertEqual(aimcore.keys_in([20, 0, 10, 10.0, 0.00001, 10], (0, 20, False)),
                         [0.0, 10.0, 20.0])

    def test_keys_outside_the_span_are_left_out(self):
        self.assertEqual(aimcore.keys_in([-5, 0, 12.5, 20, 21], (0, 20, False)), [0.0, 12.5, 20.0])

    def test_the_span_s_ends_take_a_key_within_the_tolerance(self):
        self.assertEqual(aimcore.keys_in([-0.00005, 20.00005], (0, 20, False)), [-0.00005, 20.00005])

    def test_no_keys_none(self):
        self.assertEqual(aimcore.keys_in([], (0, 20, False)), [])


class FillPasses(unittest.TestCase):
    """Default's fill loop, shared with the camera's re-entry after a parent move."""

    def test_keys_what_is_off_then_checks_the_rest_again(self):
        off = {1: True, 2: False, 3: True}
        keyed, asked = [], []

        def missed(todo):
            asked.append(list(todo))
            if keyed:                       # a key re-shaped a neighbour: 2 turns off once
                off[2] = 2 not in keyed
            return [f for f in todo if off[f]]

        def key(f):
            keyed.append(f)
            off[f] = False

        self.assertEqual(aimcore.fill_passes([3, 1, 2], missed, key), 3)
        self.assertEqual(sorted(keyed), [1, 2, 3])
        self.assertEqual(asked[0], [1, 2, 3])
        self.assertEqual(asked[1], [2])

    def test_stops_after_fill_passes(self):
        calls = []
        added = aimcore.fill_passes(range(100), lambda todo: (calls.append(1), [todo[0]])[1],
                                    lambda f: None)
        self.assertEqual((added, len(calls)), (aimcore.FILL_PASSES, aimcore.FILL_PASSES))

    def test_nothing_off_nothing_keyed(self):
        self.assertEqual(aimcore.fill_passes([1, 2], lambda todo: [], lambda f: 1 / 0), 0)


class TrackOff(unittest.TestCase):

    @staticmethod
    def matrix(ry=0.0, tx=0.0):
        import math
        import maya.api.OpenMaya as om
        m = om.MTransformationMatrix(om.MEulerRotation(0, math.radians(ry), 0).asMatrix())
        m.setTranslation(om.MVector(tx, 0, 0), om.MSpace.kTransform)
        return m.asMatrix()

    def test_turn_beyond_the_tolerance_or_a_move_beyond_the_cm(self):
        wanted = dict((f, self.matrix()) for f in range(4))
        now = {0: self.matrix(), 1: self.matrix(ry=0.09), 2: self.matrix(ry=0.11),
               3: self.matrix(tx=aimcore.FILL_CM * 2)}
        self.assertEqual(aimcore.track_off(wanted, now), [2, 3])

    def test_frames_without_a_wanted_matrix_are_skipped(self):
        self.assertEqual(aimcore.track_off({}, {5: self.matrix(ry=40)}), [])


if __name__ == "__main__":
    unittest.main()
