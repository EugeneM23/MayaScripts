import os
import subprocess
import sys
import unittest

from maya_overrig import bodymap, pickerstate


class TestMayaFreeBoundary(unittest.TestCase):
    """pickerstate must stay importable with no Maya and no Qt loaded."""

    def test_importing_pickerstate_pulls_in_neither_maya_nor_qt(self):
        script = (
            "import sys\n"
            "from maya_overrig import pickerstate\n"
            "leaked = [m for m in sys.modules\n"
            "          if m.startswith('maya.') or m.startswith('PySide6')]\n"
            "print(';'.join(sorted(leaked)))\n"
        )
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=repo_root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "",
                         "importing pickerstate leaked: "
                         + result.stdout.strip())


class TestResolve(unittest.TestCase):

    def test_fk_button_maps_to_its_controller(self):
        found = pickerstate.resolve({"pelvis": "|pelvis_FK_ctrl"}, {})
        self.assertEqual(found["pelvis"], "|pelvis_FK_ctrl")

    def test_missing_controller_leaves_the_button_out(self):
        found = pickerstate.resolve({"pelvis": None}, {})
        self.assertNotIn("pelvis", found)

    def test_ik_button_maps_through_limb_and_role(self):
        found = pickerstate.resolve({}, {("leg_l", "end"): "|foot_l_IK_feet"})
        self.assertEqual(found["leg_l_ik_end"], "|foot_l_IK_feet")

    def test_missing_ik_control_leaves_the_button_out(self):
        found = pickerstate.resolve({}, {("leg_l", "end"): None})
        self.assertNotIn("leg_l_ik_end", found)

    def test_unknown_joints_are_ignored(self):
        self.assertEqual(pickerstate.resolve({"martian": "|x"}, {}), {})

    def test_empty_scene_resolves_nothing(self):
        self.assertEqual(pickerstate.resolve({}, {}), {})


class TestSelectedIds(unittest.TestCase):

    def test_matches_on_full_paths(self):
        resolution = {"pelvis": "|a|pelvis_FK_ctrl", "head": "|a|head_FK_ctrl"}
        self.assertEqual(
            pickerstate.selected_ids(resolution, {"|a|pelvis_FK_ctrl"}),
            ["pelvis"])

    def test_bare_names_do_not_match(self):
        """Another character's same-named controller must not light us up."""
        resolution = {"pelvis": "|a|pelvis_FK_ctrl"}
        self.assertEqual(
            pickerstate.selected_ids(resolution, {"pelvis_FK_ctrl"}), [])

    def test_ik_and_fk_ids_come_back_in_map_order(self):
        resolution = {"leg_l_ik_end": "|foot_l_IK_feet",
                      "pelvis": "|pelvis_FK_ctrl",
                      "head": "|head_FK_ctrl"}
        found = pickerstate.selected_ids(
            resolution, {"|foot_l_IK_feet", "|pelvis_FK_ctrl"})
        self.assertEqual(found, ["pelvis", "leg_l_ik_end"])

    def test_empty_selection_gives_nothing(self):
        self.assertEqual(pickerstate.selected_ids({"pelvis": "|p"}, set()), [])


if __name__ == "__main__":
    unittest.main()
