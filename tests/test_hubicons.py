"""maya_hubicons: the Tabler outline icons the hub skin draws.

Spec: docs/superpowers/specs/2026-09-28-hub-skin-design.md
"""

import os
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET

import maya_hubicons as icons

_PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(
    __file__))), "SkeldarAnim")

_WANTED = ("user", "sword", "hand-grab", "transfer-in", "arrows-exchange",
           "bulb", "palette", "keyboard", "dots-vertical", "chevron-down",
           "chevron-right", "plus", "camera", "trash", "folder", "brush",
           "download", "upload", "refresh", "check", "x", "link", "unlink",
           "arrow-back-up", "shield", "books")


class TheSet(unittest.TestCase):

    def test_every_icon_the_skin_uses_is_there(self):
        for name in _WANTED:
            self.assertIn(name, icons.ICONS, name)
        self.assertEqual(sorted(icons.NAMES), sorted(icons.ICONS))

    def test_every_path_is_a_nonempty_path(self):
        for name, paths in icons.ICONS.items():
            self.assertTrue(paths, name)
            for d in paths:
                self.assertRegex(d, r"^[Mm]", name)

    def test_the_pose_library_s_books(self):
        """2026-10-02: Tabler's `books`, two spines, a leaning third book, and their bands."""
        paths = icons.ICONS["books"]
        self.assertEqual(len(paths), 7)
        self.assertEqual(paths[2:4], ("M5 8h4", "M9 16h4"))
        self.assertTrue(paths[4].startswith("M13.803 4.56l2.184 -.53"))
        self.assertTrue(paths[4].endswith("-1.219l.133 -.041z"))

    def test_the_licence_notice_rides_along(self):
        self.assertIn("MIT", icons.__doc__)
        self.assertIn("Tabler", icons.__doc__)


class Svg(unittest.TestCase):

    def test_it_parses_as_an_svg_of_the_tabler_grid(self):
        root = ET.fromstring(icons.svg("sword", "#f0a26b"))
        self.assertTrue(root.tag.endswith("svg"))
        self.assertEqual(root.get("viewBox"), "0 0 24 24")
        self.assertEqual(root.get("stroke"), "#f0a26b")
        self.assertEqual(root.get("fill"), "none")
        paths = [e for e in root if e.tag.endswith("path")]
        self.assertEqual(len(paths), len(icons.ICONS["sword"]))

    def test_no_current_color_survives(self):
        """Qt's renderer has no CSS colour to resolve it against."""
        for name in icons.ICONS:
            self.assertNotIn("currentColor", icons.svg(name, "#ffffff"))

    def test_the_stroke_width_is_a_parameter(self):
        root = ET.fromstring(icons.svg("plus", "#000000", stroke=1.5))
        self.assertEqual(root.get("stroke-width"), "1.5")

    def test_an_unknown_icon_is_a_key_error(self):
        with self.assertRaises(KeyError):
            icons.svg("sparkles", "#ffffff")


class StdlibOnly(unittest.TestCase):

    def test_imports_nothing_of_maya_or_qt(self):
        code = ("import sys; import maya_hubicons; "
                "bad = [m for m in sys.modules if m.split('.')[0] in "
                "('maya', 'PySide6', 'PySide2', 'shiboken6')]; "
                "print(','.join(bad))")
        out = subprocess.run([sys.executable, "-c", code], cwd=_PLUGIN,
                             capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
