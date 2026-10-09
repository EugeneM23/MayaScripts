"""Pure rules of the Cascadeur bridge. Neither Cascadeur nor Maya present."""

import os
import subprocess
import sys
import unittest

from skeldar_cascadeur import rules


class SkeletonProblem(unittest.TestCase):

    def test_one_root_is_fine(self):
        self.assertEqual(rules.skeleton_problem(["root"]), "")

    def test_no_root_is_refused(self):
        self.assertEqual(rules.skeleton_problem([]), rules.NO_SKELETON)

    def test_several_roots_are_refused_and_named(self):
        text = rules.skeleton_problem(["root", "Hips"])
        self.assertIn("2 skeletons", text)
        self.assertIn("Hips", text)
        self.assertIn("root", text)


class ExportRefusal(unittest.TestCase):

    def test_no_package_asks_for_a_target(self):
        self.assertEqual(rules.export_refusal("", "", False), rules.NO_TARGET)

    def test_missing_uasset_is_named(self):
        text = rules.export_refusal("/Game/A/B", "C:/P/Content/A/B.uasset", False)
        self.assertIn("C:/P/Content/A/B.uasset", text)

    def test_existing_uasset_passes(self):
        self.assertEqual(rules.export_refusal("/Game/A/B", "x", True), "")


class FpsProblem(unittest.TestCase):

    def test_thirty_is_fine(self):
        self.assertEqual(rules.fps_problem(30.0), "")

    def test_unknown_is_not_claimed(self):
        self.assertEqual(rules.fps_problem(None), "")

    def test_other_rate_is_named(self):
        text = rules.fps_problem(24.0)
        self.assertIn("24 fps", text)
        self.assertIn("30", text)


class FrameRangeOutward(unittest.TestCase):

    def test_whole_range_unchanged(self):
        self.assertEqual(rules.frame_range_outward(0, 45), (0, 45))

    def test_fraction_rounds_outward(self):
        self.assertEqual(rules.frame_range_outward(0.4, 44.2), (0, 45))


class TabNameAndJoin(unittest.TestCase):

    def test_blank_name_gets_a_default(self):
        self.assertEqual(rules.clip_tab_name("  "), "clip")

    def test_name_is_kept(self):
        self.assertEqual(rules.clip_tab_name("A_Jump"), "A_Jump")

    def test_join_drops_empty_parts(self):
        self.assertEqual(rules.join_status(["a", "", "b"]), "a  |  b")


class Purity(unittest.TestCase):

    def test_rules_import_nothing_outside_the_stdlib(self):
        plugin = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "SkeldarAnim")
        code = ("import sys; sys.path.insert(0, %r); "
                "import skeldar_cascadeur.rules; "
                "print('maya.cmds' in sys.modules, 'csc' in sys.modules, "
                "'PySide6' in sys.modules)") % plugin
        out = subprocess.check_output([sys.executable, "-c", code],
                                      cwd=plugin).decode().strip()
        self.assertEqual(out, "False False False")


if __name__ == "__main__":
    unittest.main()
