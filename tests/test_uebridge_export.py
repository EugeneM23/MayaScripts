"""Tests for the export-back direction: the pure range/wording logic and the
window-free parts of the checkouts machinery."""

import sys
import types
import unittest


def _install_fake_maya():
    if "maya.cmds" in sys.modules:
        return
    maya = types.ModuleType("maya")
    cmds = types.ModuleType("maya.cmds")
    mel = types.ModuleType("maya.mel")
    maya.cmds = cmds
    maya.mel = mel
    sys.modules.setdefault("maya", maya)
    sys.modules["maya.cmds"] = cmds
    sys.modules["maya.mel"] = mel


_install_fake_maya()

from maya_uebridge import animexport  # noqa: E402


class UnionRange(unittest.TestCase):

    def test_equal_ranges_stay_put(self):
        self.assertEqual(animexport.union_range((0, 60), (0, 60)), (0, 60))

    def test_a_zoomed_in_timeline_does_not_trim_the_clip(self):
        """Trap 38: the visible slider narrowed inside the animation range
        must not narrow the export."""
        self.assertEqual(animexport.union_range((0, 120), (30, 50)), (0, 120))

    def test_a_widened_slider_widens_the_export(self):
        self.assertEqual(animexport.union_range((0, 60), (-10, 80)), (-10, 80))


class OutsideKeysWarning(unittest.TestCase):

    def test_keys_inside_say_nothing(self):
        self.assertEqual(
            animexport.outside_keys_warning([0, 30, 60], 0, 60), "")

    def test_no_keys_say_nothing(self):
        self.assertEqual(animexport.outside_keys_warning([], 0, 60), "")

    def test_keys_outside_are_counted_and_placed(self):
        text = animexport.outside_keys_warning([-5, 0, 60, 70, 80], 0, 60)
        self.assertIn("3", text)
        self.assertIn("-5", text)


class ExportCommand(unittest.TestCase):

    def test_backslashes_become_forward_slashes(self):
        self.assertEqual(animexport.export_command("C:\\a\\b.fbx"),
                         'FBXExport -f "C:/a/b.fbx" -s;')


class ExportLine(unittest.TestCase):

    def info(self, **over):
        info = {"root": "root", "joints": 93, "start": 0.0, "end": 62.0,
                "warning": ""}
        info.update(over)
        return info

    def test_names_the_clip_the_bones_and_the_range(self):
        line = animexport.export_line("AS_Walk", self.info())
        self.assertIn("AS_Walk", line)
        self.assertIn("93", line)
        self.assertIn("0-62", line)

    def test_a_warning_rides_along(self):
        line = animexport.export_line("A",
                                      self.info(warning="2 key(s) outside"))
        self.assertIn("outside", line)


if __name__ == "__main__":
    unittest.main()
