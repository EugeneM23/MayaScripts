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
        self.assertTrue(72 <= cell <= 120, cell)
        self.assertEqual(len(rects), 4)
        self.assertEqual(height, cell + look.NAME_H)
        self.assertEqual(len(set(r[1] for r in rects)), 1)

    def test_a_narrow_dock_wraps(self):
        cols, cell, rects, height = look.grid(200, 4)
        self.assertEqual(cols, 2)
        self.assertEqual(height, 2 * (cell + look.NAME_H) + look.GAP)
        self.assertGreater(rects[2][1], rects[0][1])

    def test_a_wide_dock_caps_the_portrait(self):
        cols, cell, _rects, _height = look.grid(900, 4)
        self.assertEqual((cols, cell), (4, look.CELL_MAX))

    def test_no_width_yet_is_one_row_at_the_minimum(self):
        cols, cell, _rects, height = look.grid(0, 4)
        self.assertEqual((cols, cell), (4, look.CELL_MIN))
        self.assertEqual(height, look.CELL_MIN + look.NAME_H)

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
        _c, cell, rects, _h = look.grid(330, 4)
        x, y = rects[2][:2]
        self.assertEqual(look.hit(rects, x + 3, y + 3), 2)
        self.assertEqual(look.hit(rects, x + 3, y + cell + 5), 2)

    def test_the_gap_is_nothing(self):
        _c, _cell, rects, _h = look.grid(330, 4)
        self.assertIsNone(look.hit(rects, rects[0][0] + rects[0][2] + 2, 5))


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


class Drag(unittest.TestCase):

    def test_a_drag_starts_past_the_distance(self):
        self.assertFalse(look.dragged((10, 10), (12, 11), 4))
        self.assertTrue(look.dragged((10, 10), (13, 11), 4))

    def test_over_the_hub(self):
        self.assertTrue(look.over_hub(["", "skeldarAnimHubRoot", "MayaWindow"]))
        self.assertTrue(look.over_hub(["skeldarAnimHub"]))
        self.assertFalse(look.over_hub(["modelPanel4", "MayaWindow"]))


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
