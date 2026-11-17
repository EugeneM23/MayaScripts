"""maya_tools.relink: the pure half of pointing dead UUID markers again (2026-11-17).

An import gives every node a new UUID, so a tab's knot and Aim Mode markers named nodes that were
gone; `heal` reads them back from the scene graph (verified in mayapy:
docs/verify/verify_relink_import.py)."""

import unittest

from maya_tools import relink


class IsUuid(unittest.TestCase):

    def test_maya_s_uuid_shape(self):
        self.assertTrue(relink.is_uuid("5F89577E-4A51-24F1-6985-B3A448907929"))
        self.assertTrue(relink.is_uuid("5f89577e-4a51-24f1-6985-b3a448907929"))

    def test_anything_else_is_not_one(self):
        for text in ("", None, "DaggerMesh", "0 1 0 0.75", "5F89577E-4A51-24F1-6985"):
            self.assertFalse(relink.is_uuid(text), text)


class One(unittest.TestCase):

    def test_one_node_named_twice_is_that_node(self):
        self.assertEqual(relink.one(["|a", "|a"]), "|a")

    def test_two_nodes_or_none_answer_nothing(self):
        self.assertIsNone(relink.one(["|a", "|b"]))
        self.assertIsNone(relink.one([]))
        self.assertIsNone(relink.one([None, ""]))


class AimBase(unittest.TestCase):

    def test_the_group_s_node_keeps_its_namespace(self):
        self.assertEqual(relink.aim_base("tab_1:DaggerMesh_aim1"), "tab_1:DaggerMesh")
        self.assertEqual(relink.aim_base("Camera_ctrl_aim"), "Camera_ctrl")

    def test_a_name_without_the_suffix_names_nothing(self):
        self.assertIsNone(relink.aim_base("DaggerMesh_knotOffset"))
        self.assertIsNone(relink.aim_base("_aim"))

    def test_only_the_last_aim_suffix_goes(self):
        self.assertEqual(relink.aim_base("Sword_aim_aim2"), "Sword_aim")


class Markers(unittest.TestCase):

    def test_the_names_are_the_ones_the_tools_write(self):
        from maya_tools import firstperson, knotplan
        from maya_scenesetup import cameraaim, weaponaim
        self.assertEqual(relink.KNOT_OF, knotplan.OF_MARKER)
        self.assertEqual(relink.KNOT_SOURCE, knotplan.SOURCE_MARKER)
        self.assertEqual(relink.KNOT_INNER, knotplan.INNER_MARKER)
        self.assertEqual(relink.ARM_1P, firstperson.ARM_MARKER)
        self.assertEqual(relink.AIM_MARKERS,
                         ((weaponaim.KIND.marker, weaponaim.KIND.con_marker),
                          (cameraaim.KIND.marker, cameraaim.KIND.con_marker)))


if __name__ == "__main__":
    unittest.main()
