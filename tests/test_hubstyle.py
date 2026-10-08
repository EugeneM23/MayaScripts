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
        handled = {"subtitle", "swatchonly", "swatch", "flow"}
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

    def test_a_heading_is_a_bold_title_over_a_line(self):
        """2026-10-01: a section's title inside a card («UE Connect»,
        «Weapon», «Armor») - bold, the primary text, a hairline under it."""
        self.assertIn("heading", style.ROLES)
        rule = re.search(r'QLabel\[skRole="heading"\] \{([^}]*)\}',
                         style.stylesheet()).group(1)
        self.assertIn("font-weight: bold", rule)
        self.assertIn(style.TOKENS["text"], rule)
        self.assertIn("border-bottom", rule)

    def test_the_chip_hides_its_indicator(self):
        sheet = style.stylesheet()
        self.assertRegex(
            sheet, r'QCheckBox\[skRole="chip"\]::indicator \{[^}]*width: 0')

    def test_it_uses_only_token_colours(self):
        sheet = style.stylesheet()
        colours = set(re.findall(r"#[0-9a-f]{6}", sheet))
        self.assertTrue(colours <= set(style.TOKENS.values()),
                        colours - set(style.TOKENS.values()))


class Skinning(unittest.TestCase):

    def tearDown(self):
        style.set_skinning(False)

    def test_classic_by_default(self):
        self.assertFalse(style.skinning())
        self.assertEqual(style.pick("skin", "classic"), "classic")
        self.assertEqual(style.tool_label("Recolour"), "Recolour")
        self.assertEqual(style.tool_width(90), 90)

    def test_the_skin_s_tool_button_is_an_icon(self):
        style.set_skinning(True)
        self.assertTrue(style.skinning())
        self.assertEqual(style.pick("skin", "classic"), "skin")
        self.assertEqual(style.tool_label("Recolour"), "")
        self.assertEqual(style.tool_width(90), 30)


class Arrow(unittest.TestCase):

    def test_no_arrow_rule_without_a_file(self):
        self.assertNotIn("down-arrow", style.stylesheet(1.5))

    def test_the_arrow_file_is_the_dropdown_arrow(self):
        sheet = style.stylesheet(1.5, arrow="C:\\tmp\\chevron.svg")
        self.assertIn("QComboBox::down-arrow { image: url(C:/tmp/chevron.svg)",
                      sheet)


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


class Glow(unittest.TestCase):
    """2026-10-01: the lit card's inner glow, as data."""

    def test_dark_is_nothing(self):
        self.assertTrue(all(a == 0.0 for _i, _w, a in style.glow_rings(0, 0)))

    def test_strongest_at_the_edge_fading_inward(self):
        rings = style.glow_rings(1.0, 0.0)
        self.assertEqual(len(rings), int(style.GLOW["width"]))
        alphas = [a for _i, _w, a in rings]
        self.assertEqual(alphas, sorted(alphas, reverse=True))
        self.assertAlmostEqual(alphas[0], style.GLOW["alpha"])
        insets = [i for i, _w, _a in rings]
        self.assertEqual(insets, sorted(insets))
        self.assertEqual(insets[0], 0.0)

    def test_a_flash_brightens_and_widens(self):
        lit = style.glow_rings(1.0, 0.0)
        flash = style.glow_rings(1.0, 1.0)
        self.assertGreater(flash[0][2], lit[0][2])
        self.assertGreater(flash[-1][0] + flash[-1][1],
                           lit[-1][0] + lit[-1][1])
        self.assertTrue(all(a <= 1.0 for _i, _w, a in flash))

    def test_half_lit_is_half_the_light(self):
        full = style.glow_rings(1.0, 0.0)
        half = style.glow_rings(0.5, 0.0)
        self.assertAlmostEqual(half[0][2], full[0][2] / 2)

    def test_mix(self):
        self.assertEqual(style.mix("#000000", "#ffffff", 0.0), "#000000")
        self.assertEqual(style.mix("#000000", "#ffffff", 1.0), "#ffffff")
        self.assertEqual(style.mix("#000000", "#ffffff", 0.5), "#808080")
        self.assertEqual(style.mix("#e07a36", "#f0a26b", -1), "#e07a36")

    def test_the_sheet_no_longer_switches_the_light(self):
        """The card paints it, fading; a stylesheet switch was instant."""
        sheet = style.stylesheet()
        self.assertNotIn('[skActive="true"]', sheet)
        self.assertIn('QFrame[skCard="true"]', sheet)


class GlowPixels(unittest.TestCase):

    def test_one_physical_pixel_a_ring(self):
        """Wider rings showed as bands (photographed live at 150 %)."""
        rings = style.glow_rings(1.0, 0.0, 1.5)
        self.assertEqual(len(rings), 15)
        self.assertTrue(all(abs(w * 1.5 - 1.0) < 1e-9 for _i, w, _a in rings))
        insets = [i * 1.5 for i, _w, _a in rings]
        self.assertEqual([round(x, 6) for x in insets], list(range(15)))


class Compact(unittest.TestCase):
    """2026-10-08, variant B: the builders' heights, the relay, the lists."""

    def tearDown(self):
        style.set_skinning(False)
        style.take_marks()
        for fn in list(style._LISTENERS):
            style.unlisten(fn)

    def test_heights_are_the_compact_ones_in_the_skin_only(self):
        self.assertEqual(style.height("button", 32), 32)
        style.set_skinning(True)
        self.assertEqual(style.height("button", 32), 24)
        self.assertEqual(style.height("small", 28), 22)
        self.assertEqual(style.height("segment", 22), 22)
        self.assertEqual(style.height("field", 24), 20)

    def test_row_spacing(self):
        self.assertEqual(style.row_spacing(), 6)
        self.assertEqual(style.row_spacing(4), 4)
        style.set_skinning(True)
        self.assertEqual(style.row_spacing(4), 3)

    def test_a_grip_mark_names_its_list(self):
        self.assertEqual(style.grip("aGrip", "aList"), "aGrip")
        mark = style.take_marks()[0]
        self.assertEqual((mark.name, mark.role, mark.target),
                         ("aGrip", "grip", "aList"))

    def test_an_ordinary_mark_has_no_target(self):
        style.mark("b", "primary", "plus")
        self.assertIsNone(style.take_marks()[0].target)

    def test_new_roles(self):
        self.assertIn("grip", style.ROLES)
        self.assertIn("dot", style.ROLES)
        self.assertIn("flow", style.ROLES)        # live, 2026-10-08

    def test_tell_reaches_every_listener_and_answers_the_text(self):
        heard = []
        style.listen(lambda c, t, v: heard.append((c, t, v)))
        self.assertEqual(style.tell("status1", "done", viewport=True), "done")
        self.assertEqual(heard, [("status1", "done", True)])

    def test_tell_without_a_listener_is_quiet(self):
        self.assertEqual(style.tell("status1", "done"), "done")

    def test_a_listener_that_raises_costs_only_itself(self):
        heard = []

        def bad(*_a):
            raise RuntimeError("no")
        style.listen(bad)
        style.listen(lambda c, t, v: heard.append(t))
        style.tell("s", "x")
        self.assertEqual(heard, ["x"])

    def test_unlisten(self):
        heard = []
        fn = style.listen(lambda c, t, v: heard.append(t))
        style.unlisten(fn)
        style.unlisten(fn)                       # twice is harmless
        style.tell("s", "x")
        self.assertEqual(heard, [])

    def test_rows_clamp(self):
        self.assertEqual(style.clamp_rows(2), 5)
        self.assertEqual(style.clamp_rows(10.4), 10)
        self.assertEqual(style.clamp_rows(99), 40)

    def test_rows_after_a_drag_move_by_whole_rows(self):
        self.assertEqual(style.rows_after_drag(10, 0, 16), 10)
        self.assertEqual(style.rows_after_drag(10, 7, 16), 10)   # under half
        self.assertEqual(style.rows_after_drag(10, 9, 16), 11)
        self.assertEqual(style.rows_after_drag(10, -48, 16), 7)
        self.assertEqual(style.rows_after_drag(10, -999, 16), 5)
        self.assertEqual(style.rows_after_drag(10, 50, 0), 10)   # no row size

    def test_list_height(self):
        self.assertEqual(style.list_height(10, 16, 6), 166)

    def test_the_sheet_has_the_dot_and_grip_rules(self):
        sheet = style.stylesheet(1.0)
        self.assertIn('QLabel[skRole="dot"]', sheet)
        self.assertIn('QWidget[skRole="grip"]', sheet)
