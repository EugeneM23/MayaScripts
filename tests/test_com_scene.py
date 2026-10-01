"""The scene modules' pure halves: the network's, the tool's, the panel's."""

import unittest

import numpy as np

from maya_com import drag, massmodel, network, panel


class Network(unittest.TestCase):

    def test_first_person_meshes_are_left_out(self):
        for name in ("Hands_1P", "|Manny_Rig:SKM|Manny_Rig:Hands_1PShape",
                     "Orc_D_1P", "Orc_D_1PShape"):
            self.assertTrue(network.is_first_person(name), name)
        for name in ("Skin_3p", "Creep_Body", "Orc_D_3PShape", "Creep_Arm_L"):
            self.assertFalse(network.is_first_person(name), name)

    def test_weight_rows_are_mass_shares_times_the_centre(self):
        model = massmodel.Model({"a": 3.0, "b": 1.0},
                                {"a": np.array([1.0, 2.0, 3.0]),
                                 "b": np.array([4.0, 0.0, -4.0])}, 4.0)
        rows = network.weight_rows(model)
        self.assertEqual([r[0] for r in rows], ["a", "b"])
        np.testing.assert_allclose(rows[0][1:], (0.75, 1.5, 2.25, 0.75))
        np.testing.assert_allclose(rows[1][1:], (1.0, 0.0, -1.0, 0.25))
        self.assertAlmostEqual(sum(r[4] for r in rows), 1.0)

    def test_the_sum_of_rows_is_the_formula(self):
        """row0(Wx) + row1(Wy) + row2(Wz) + row3(Wt) = Σ m̂ (c · M)."""
        rng = np.random.default_rng(3)
        model = massmodel.Model({"a": 2.0, "b": 5.0},
                                {"a": rng.normal(size=3), "b": rng.normal(size=3)},
                                7.0)
        world = {}
        for k in ("a", "b"):
            m = np.identity(4)
            m[:3, :3] = rng.normal(size=(3, 3))
            m[3, :3] = rng.normal(size=3)
            world[k] = m
        rows = network.weight_rows(model)
        wx = sum(r[1] * world[r[0]] for r in rows)
        wy = sum(r[2] * world[r[0]] for r in rows)
        wz = sum(r[3] * world[r[0]] for r in rows)
        wt = sum(r[4] * world[r[0]] for r in rows)
        got = wx[0, :3] + wy[1, :3] + wz[2, :3] + wt[3, :3]
        np.testing.assert_allclose(got, massmodel.com(model, world), atol=1e-12)

    def test_names_take_the_namespace(self):
        self.assertEqual(network.name_in("Manny_Rig", "COM_handle"),
                         "Manny_Rig:COM_handle")
        self.assertEqual(network.name_in("", "COM_handle"), "COM_handle")


class Tool(unittest.TestCase):

    def test_handles_only(self):
        groups = {"h1": "g1", "h2": "g1", "h3": "g2"}
        look = groups.get
        self.assertEqual(drag.handles_only(["h1", "h2"], look), ["g1"])
        self.assertEqual(drag.handles_only(["h1", "h3"], look), ["g1", "g2"])
        self.assertEqual(drag.handles_only(["h1", "pelvis"], look), [])
        self.assertEqual(drag.handles_only([], look), [])

    def test_wer_with_a_handle_comes_back(self):
        self.assertTrue(drag.should_bounce("moveSuperContext", ["g"]))
        self.assertFalse(drag.should_bounce("selectSuperContext", ["g"]))
        self.assertFalse(drag.should_bounce("moveSuperContext", []))


class Panel(unittest.TestCase):

    def test_the_character_line(self):
        self.assertEqual(panel.line_for("Manny_Rig", None),
                         "Manny_Rig - no CoM yet")
        self.assertEqual(panel.line_for("Manny_Rig", {"volume": 83.3, "joints": 74}),
                         "Manny_Rig - 83 L over 74 bones")


if __name__ == "__main__":
    unittest.main()
