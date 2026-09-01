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
        repo_root = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "SkeldarAnim")
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


class TestBoneFallback(unittest.TestCase):
    """Buttons the caller allows may select the BONE when no control exists.

    Finger FK controllers stopped being built (2026-08-18) and the animator
    poses the bones, so the ten finger chains' buttons must stay live. The
    policy of WHICH buttons may fall back stays with the caller: this module
    falls back for whatever it is handed and knows nothing about fingers.
    """

    def test_a_button_with_no_controller_takes_the_bone(self):
        found = pickerstate.resolve({"index_01_l": None}, {},
                                    {"index_01_l": "|rig|index_01_l"})
        self.assertEqual(found["index_01_l"], "|rig|index_01_l")

    def test_a_button_absent_from_fk_nodes_takes_the_bone(self):
        """An unbuilt chain is not in fk_nodes at all, not merely None."""
        found = pickerstate.resolve({}, {},
                                    {"thumb_02_r": "|rig|thumb_02_r"})
        self.assertEqual(found["thumb_02_r"], "|rig|thumb_02_r")

    def test_the_controller_always_wins(self):
        """A scene rigged before the change still selects its controller."""
        found = pickerstate.resolve({"index_01_l": "|index_01_l_FK_ctrl"}, {},
                                    {"index_01_l": "|rig|index_01_l"})
        self.assertEqual(found["index_01_l"], "|index_01_l_FK_ctrl")

    def test_no_fallback_offered_leaves_the_button_out(self):
        self.assertNotIn("index_01_l", pickerstate.resolve(
            {"index_01_l": None}, {}))

    def test_a_fallback_for_an_unknown_joint_is_ignored(self):
        self.assertEqual(pickerstate.resolve({}, {}, {"martian": "|x"}), {})

    def test_other_buttons_are_untouched_by_the_fallback(self):
        found = pickerstate.resolve({"pelvis": None}, {},
                                    {"index_01_l": "|rig|index_01_l"})
        self.assertNotIn("pelvis", found)

    def test_a_bone_backed_button_lights_when_selected(self):
        resolution = pickerstate.resolve({}, {},
                                         {"index_01_l": "|rig|index_01_l"})
        self.assertEqual(
            pickerstate.selected_ids(resolution, {"|rig|index_01_l"}),
            ["index_01_l"])


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
