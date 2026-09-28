"""maya_hubstyle: the skin's palette, groups, stylesheet and control marks.

Spec: docs/superpowers/specs/2026-09-28-hub-skin-design.md
"""

import os
import re
import subprocess
import sys
import unittest

import maya_hubstyle as style

_PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(
    __file__))), "SkeldarAnim")


class Tokens(unittest.TestCase):

    def test_every_token_is_a_hex_colour(self):
        for key, value in style.TOKENS.items():
            self.assertRegex(value, r"^#[0-9a-f]{6}$", key)

    def test_the_brand_accent_is_the_orange_the_animator_picked(self):
        self.assertEqual(style.TOKENS["accent"], "#e07a36")
        self.assertEqual(style.TOKENS["panel"], "#1f2023")
        self.assertEqual(style.TOKENS["card"], "#2a2c30")


class Groups(unittest.TestCase):

    def test_the_four_groups_in_order(self):
        self.assertEqual([g.key for g in style.GROUPS],
                         ["scene", "animation", "look", "settings"])
        self.assertEqual([g.label for g in style.GROUPS],
                         ["Scene", "Animation", "Look", "Settings"])

    def test_lookup(self):
        self.assertEqual(style.group("look").label, "Look")
        self.assertIsNone(style.group("nonsense"))

    def test_group_colours_are_hex(self):
        for g in style.GROUPS:
            self.assertRegex(g.colour, r"^#[0-9a-f]{6}$")
            self.assertRegex(g.chip, r"^#[0-9a-f]{6}$")


class HexAndPx(unittest.TestCase):

    def test_hex_of_an_rgb_triple(self):
        self.assertEqual(style.hex_of((1.0, 0.5, 0.0)), "#ff8000")
        self.assertEqual(style.hex_of([0, 0, 0]), "#000000")

    def test_hex_of_clamps(self):
        self.assertEqual(style.hex_of((1.4, -0.2, 0.5)), "#ff0080")

    def test_px_scales_and_rounds(self):
        self.assertEqual(style.px(6, 1.5), 9)
        self.assertEqual(style.px(6, 1.0), 6)
        self.assertEqual(style.px(3, 1.25), 4)

    def test_px_never_rounds_a_line_away(self):
        self.assertEqual(style.px(1, 0.4), 1)
        self.assertEqual(style.px(0, 1.5), 0)


class Marks(unittest.TestCase):

    def setUp(self):
        style.take_marks()

    def tearDown(self):
        style.take_marks()

    def test_mark_returns_the_name_so_a_creation_can_be_wrapped(self):
        self.assertEqual(style.mark("addButton", "primary", "plus"),
                         "addButton")

    def test_take_marks_hands_over_in_order_and_clears(self):
        style.mark("a", "primary", "plus")
        style.mark("row", "segments", layout=True)
        marks = style.take_marks()
        self.assertEqual([(m.name, m.role, m.icon, m.layout) for m in marks],
                         [("a", "primary", "plus", False),
                          ("row", "segments", None, True)])
        self.assertEqual(style.take_marks(), [])

    def test_an_unknown_role_is_an_error(self):
        with self.assertRaises(ValueError):
            style.mark("a", "sparkly")

    def test_a_swatch_carries_its_hex(self):
        self.assertEqual(style.swatch("dot1", (1.0, 0.5, 0.0)), "dot1")
        mark = style.take_marks()[0]
        self.assertEqual((mark.role, mark.colour), ("swatch", "#ff8000"))

    def test_every_role_is_known_to_the_stylesheet_or_the_qt_layer(self):
        sheet = style.stylesheet()
        styled = [r for r in style.ROLES if '[skRole="%s"]' % r in sheet]
        #  moved or recoloured by the Qt layer rather than styled
        handled = {"subtitle", "swatchonly", "swatch"}
        for role in style.ROLES:
            self.assertTrue(role in styled or role in handled, role)


class Stylesheet(unittest.TestCase):

    def test_the_root_is_the_scope(self):
        self.assertIn("#" + style.ROOT, style.stylesheet())

    def test_pixels_scale_with_the_display(self):
        one = style.stylesheet(1.0)
        big = style.stylesheet(1.5)
        radius = re.compile(r'\[skCard="true"\][^}]*border-radius: (\d+)px')
        self.assertEqual(int(radius.search(one).group(1)), 8)
        self.assertEqual(int(radius.search(big).group(1)), 12)

    def test_the_primary_button_is_the_accent(self):
        sheet = style.stylesheet()
        rule = re.search(r'QPushButton\[skRole="primary"\] \{([^}]*)\}',
                         sheet).group(1)
        self.assertIn(style.TOKENS["accent"], rule)
        self.assertIn(style.TOKENS["on_accent"], rule)

    def test_no_blanket_background_rule(self):
        """Measured 2026-09-28: `QFrame[skCard] QWidget {background:
        transparent}` outranked the primary button and emptied every field;
        a QLabel background hid the colour slider's swatch (a QLabel)."""
        sheet = style.stylesheet()
        self.assertNotRegex(sheet, r"QWidget\s*\{[^}]*background")
        self.assertNotRegex(sheet, r"(^|\}|,)\s*QLabel\s*\{[^}]*background")
        self.assertNotRegex(sheet, r"\] QWidget\s*\{")

    def test_the_chip_hides_its_indicator(self):
        sheet = style.stylesheet()
        self.assertRegex(
            sheet, r'QCheckBox\[skRole="chip"\]::indicator \{[^}]*width: 0')

    def test_it_uses_only_token_colours(self):
        sheet = style.stylesheet()
        colours = set(re.findall(r"#[0-9a-f]{6}", sheet))
        self.assertTrue(colours <= set(style.TOKENS.values()),
                        colours - set(style.TOKENS.values()))


class StdlibOnly(unittest.TestCase):

    def test_imports_nothing_of_maya_or_qt(self):
        code = ("import sys; import maya_hubstyle; "
                "bad = [m for m in sys.modules if m.split('.')[0] in "
                "('maya', 'PySide6', 'PySide2', 'shiboken6')]; "
                "print(','.join(bad))")
        out = subprocess.run([sys.executable, "-c", code], cwd=_PLUGIN,
                             capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
