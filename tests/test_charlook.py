"""The Characters card's portrait grid as data (2026-09-30): how many columns a
width holds, where each tile is, what a point is, what the lines say. Stdlib.

Spec: docs/superpowers/specs/2026-09-30-character-portrait-grid-design.md
"""
import os
import re
import unittest

import maya_charlook as look

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "SkeldarAnim")


class Grid(unittest.TestCase):

    def test_the_animators_dock_holds_one_row_of_four(self):
        cols, cell, rects, height = look.grid(330, 4)
        self.assertEqual(cols, 4)
        self.assertTrue(look.CELL_MIN <= cell <= look.CELL_MAX, cell)
        self.assertEqual(len(rects), 4)
        self.assertEqual(height, cell)          # the name is over the square: no strip
        self.assertEqual(len(set(r[1] for r in rects)), 1)

    def test_a_narrow_dock_wraps(self):
        width = 2 * look.CELL_MIN + look.GAP + 10        # room for two columns, not three
        cols, cell, rects, height = look.grid(width, 4)
        self.assertEqual(cols, 2)
        self.assertEqual(height, 2 * cell + look.GAP)
        self.assertEqual(rects[2][1], cell + look.GAP)   # the next row: a square and a gap down
        self.assertGreater(rects[2][1], rects[0][1])

    def test_a_wide_dock_caps_the_portrait(self):
        cols, cell, _rects, _height = look.grid(900, 4)
        self.assertEqual((cols, cell), (4, look.CELL_MAX))

    def test_no_width_yet_is_one_row_at_the_minimum(self):
        cols, cell, _rects, height = look.grid(0, 4)
        self.assertEqual((cols, cell), (4, look.CELL_MIN))
        self.assertEqual(height, look.CELL_MIN)

    def test_the_scale_multiplies(self):
        one = look.grid(330, 4)
        big = look.grid(495, 4, scale=1.5)
        self.assertEqual(big[0], one[0])
        self.assertEqual(big[1], int(round(one[1] * 1.5)))

    def test_tiles_do_not_overlap_and_fit_the_width(self):
        _cols, _cell, rects, _h = look.grid(330, 4)
        for a, b in zip(rects, rects[1:]):
            self.assertLessEqual(a[0] + a[2], b[0])
        self.assertLessEqual(rects[-1][0] + rects[-1][2], 330)

    def test_nothing_to_draw(self):
        self.assertEqual(look.grid(330, 0), (0, 0, [], 0))


class Hit(unittest.TestCase):

    def test_the_tile_and_its_name_are_the_tile(self):
        """The name lies over the square's bottom (2026-10-08): pressing on it
        is pressing on the tile, and under the square there is nothing."""
        _c, cell, rects, _h = look.grid(330, 4)
        x, y = rects[2][:2]
        self.assertEqual(look.hit(rects, x + 3, y + 3), 2)
        nx, ny, _nw, nh = look.name_rect(rects[2])
        self.assertEqual(look.hit(rects, nx + 3, ny + nh // 2), 2)
        self.assertIsNone(look.hit(rects, x + 3, y + cell + 1))

    def test_the_gap_is_nothing(self):
        _c, _cell, rects, _h = look.grid(330, 4)
        self.assertIsNone(look.hit(rects, rects[0][0] + rects[0][2] + 1, 5))


class OverlayNames(unittest.TestCase):
    """2026-10-08, variant B: five a row in the card, the name over the
    picture's bottom (no strip under it)."""

    def test_five_portraits_a_row_in_a_338_px_card(self):
        cols, cell, rects, height = look.grid(338, 5)
        self.assertEqual(cols, 5)
        self.assertGreaterEqual(cell, look.CELL_MIN)
        self.assertEqual(height, cell)                  # one row, no strip

    def test_the_name_lies_inside_the_square(self):
        rect = (10, 20, 64, 64)
        nx, ny, nw, nh = look.name_rect(rect)
        self.assertEqual((nx, nw, nh), (10, 64, look.NAME_H))
        self.assertEqual(ny + nh, 20 + 64)

    def test_the_name_strip_scales(self):
        rect = (10, 20, 96, 96)
        nx, ny, nw, nh = look.name_rect(rect, 1.5)
        self.assertEqual((nx, nw, nh), (10, 96, int(round(look.NAME_H * 1.5))))
        self.assertEqual(ny + nh, 20 + 96)

    def test_a_tile_is_its_square(self):
        self.assertEqual(look.tile_rect((1, 2, 30, 30)), (1, 2, 30, 30))
        self.assertEqual(look.tile_rect((1, 2, 30, 30), 1.5), (1, 2, 30, 30))

    def test_two_rows_height(self):
        cols, cell, rects, height = look.grid(338, 7)
        self.assertEqual(height, 2 * cell + look.GAP)

    def test_the_compact_constants(self):
        self.assertEqual((look.CELL_MIN, look.GAP, look.NAME_H), (58, 3, 16))


class State(unittest.TestCase):

    def test_the_four_states(self):
        both, rig = ("rig", "skeleton"), ("rig",)
        self.assertEqual(look.state("Manny", "rig", "Manny", both), "selected")
        self.assertEqual(look.state("Orc_D", "skeleton", "Orc_D", rig), "selected_absent")
        self.assertEqual(look.state("Orc_D", "skeleton", "Manny", rig), "absent")
        self.assertEqual(look.state("Creep", "rig", "Manny", both), "available")


class Lines(unittest.TestCase):

    def test_the_place_caption_names_the_row_and_the_floor_point(self):
        self.assertEqual(look.place_caption("Manny [rig]", (120.4, 0.0, -35.6)),
                         "Manny [rig] · floor (120, -36)")

    def test_an_absent_pair_is_refused_by_name(self):
        text = look.absent_text("Orc D", "skeleton")
        self.assertIn("Orc D has no skeleton", text)
        self.assertIn("Rig", text)
        self.assertIn("rig", look.absent_text("UE4 Mannequin", "rig"))

    def test_the_import_line(self):
        self.assertIn("Manny [rig]", look.import_text("Manny [rig]"))
        self.assertIn("drag", look.import_text("Manny [rig]"))

    def test_the_tag(self):
        self.assertEqual(look.tag_text("skeleton"), "no skeleton")

    def test_the_auto_lines(self):
        """2026-10-02: the «?» card says what an import with it does, and what + Import cannot."""
        self.assertTrue(look.auto_text("rig").startswith("Auto [rig] - Import Animation"))
        self.assertIn("its own skeleton", look.auto_text("skeleton"))
        self.assertIn("our skeleton", look.auto_text("skeleton"))
        self.assertIn("no character of its own", look.AUTO_ADD)


class Drag(unittest.TestCase):

    def test_a_drag_starts_past_the_distance(self):
        self.assertFalse(look.dragged((10, 10), (12, 11), 4))
        self.assertTrue(look.dragged((10, 10), (13, 11), 4))

    def test_over_the_hub(self):
        """maya_hubstyle's since 2026-10-01 (the UE Bridge list drags too)."""
        import maya_hubstyle
        self.assertTrue(maya_hubstyle.over_hub(["", "skeldarAnimHubRoot", "MayaWindow"]))
        self.assertTrue(maya_hubstyle.over_hub(["skeldarAnimHub"]))
        self.assertFalse(maya_hubstyle.over_hub(["modelPanel4", "MayaWindow"]))


class Boundary(unittest.TestCase):

    def test_no_maya_and_no_qt(self):
        with open(os.path.join(PLUGIN, "maya_charlook.py"), encoding="utf-8") as handle:
            source = handle.read()
        self.assertEqual(re.findall(r"^\s*(?:import|from)\s+(?:maya(?:\.|\s|$)|PySide)",
                                    source, re.MULTILINE), [])

    def test_the_payload_ships_it(self):
        import install
        for name in ("maya_charlook.py", "maya_chargrid.py"):
            self.assertIn(name, install.payload())


if __name__ == "__main__":
    unittest.main()
