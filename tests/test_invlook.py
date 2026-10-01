"""The inventory's look as data: the card panel's layout (2026-09-30), the
channel text, hits, every catalog weapon having its icon - and, since
2026-10-01, the tiles in place of the cell grid («уберем функционал
сетчатого инвентаря ... перемещать по сетке не нужно»).

Specs: docs/superpowers/specs/2026-09-29-weapon-inventory-design.md,
docs/superpowers/specs/2026-10-01-inventory-card-design.md
"""

import os
import subprocess
import sys
import unittest
from collections import namedtuple

import maya_charlook
import maya_invlook as look
from maya_scenesetup import catalog

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "SkeldarAnim")
COUNT = len(catalog.WEAPONS)


def _apart(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay


def _inside(inner, outer):
    ix, iy, iw, ih = inner
    ox, oy, ow, oh = outer
    return ix >= ox and iy >= oy and ix + iw <= ox + ow and iy + ih <= oy + oh


class Panel(unittest.TestCase):
    """2026-09-30: two hands, each a Channel Box column left of its well
    («слева от окошка столбик с параметрами так как в стандартном интерфейсе
    маи в channel box»); 2026-10-01: the tiles under them."""

    WIDTHS = (250, 320, 360, 500)

    def test_the_hands_stand_side_by_side_the_right_one_on_the_left(self):
        for width in self.WIDTHS:
            r = look.panel(width, COUNT)
            self.assertLess(r["hand_R"][0], r["hand_L"][0], width)
            self.assertEqual(r["hand_R"][1:], r["hand_L"][1:], width)
            self.assertTrue(_apart(r["hand_R"], r["hand_L"]), width)

    def test_each_column_stands_left_of_its_well_inside_its_card(self):
        for width in self.WIDTHS:
            r = look.panel(width, COUNT)
            for side in ("R", "L"):
                col, well = r["column_" + side], r["well_" + side]
                self.assertLess(col[0] + col[2], well[0], (width, side))
                for name in ("name_", "column_", "well_"):
                    self.assertTrue(_inside(r[name + side], r["hand_" + side]),
                                    (width, name + side))
                self.assertGreaterEqual(well[2], 32)

    def test_six_rows_in_channel_box_order_top_to_bottom(self):
        self.assertEqual(look.CHANNELS, ("tx", "ty", "tz", "rx", "ry", "rz"))
        r = look.panel(320, COUNT)
        for side in ("R", "L"):
            tops = [r["row_%s_%s" % (side, ch)][1] for ch in look.CHANNELS]
            self.assertEqual(tops, sorted(tops))
            for ch in look.CHANNELS:
                self.assertTrue(_inside(r["row_%s_%s" % (side, ch)],
                                        r["column_" + side]), ch)
            self.assertEqual(r["row_%s_rz" % side][1] + r["row_%s_rz" % side][3],
                             r["column_" + side][1] + r["column_" + side][3])

    def test_the_tiles_are_the_portraits_geometry_under_both_hands(self):
        """The armor's and the portraits' own squares (`maya_charlook.grid`),
        one per catalog weapon, below the hands, ending the panel."""
        for width in self.WIDTHS:
            r = look.panel(width, COUNT)
            _cols, _cell, squares, height = maya_charlook.grid(width, COUNT, 1.0)
            self.assertEqual(len(r["tiles"]), COUNT, width)
            top = r["tilesarea"][1]
            self.assertEqual(r["tiles"], [(x, top + y, w, h) for x, y, w, h in squares])
            for side in ("R", "L"):
                self.assertGreaterEqual(top, r["hand_" + side][1] + r["hand_" + side][3])
            for tile in r["tiles"]:
                self.assertEqual(tile[2], tile[3])                  # square
                self.assertTrue(_inside(tile, r["tilesarea"]), width)
            self.assertEqual(r["tilesarea"][3], height)
            self.assertEqual(r["panel"], (0, 0, width, top + height))

    def test_scaled_scales_the_tiles_too(self):
        r = look.scaled(look.panel(320, COUNT), 1.5)
        logical = look.panel(320, COUNT)
        self.assertEqual(len(r["tiles"]), COUNT)
        self.assertEqual(r["tiles"][1], tuple(int(round(v * 1.5)) for v in logical["tiles"][1]))
        self.assertEqual(r["panel"][3], int(round(logical["panel"][3] * 1.5)))

    def test_the_window_layout_is_gone(self):
        for name in ("layout", "SLOT", "TITLE_H", "STATUS_H", "MARGIN"):
            self.assertFalse(hasattr(look, name), name)

    def test_the_grid_is_gone(self):
        """2026-10-01: «перемещать по сетке не нужно» - no cells, no
        rearranging, no Sort, no remembered layout."""
        for name in ("CELL", "MIN_CELL", "COLS", "ROWS", "SORT", "pack", "item_cells",
                     "load_cells", "footprint", "clamp", "plan_move", "arrange",
                     "layout_record", "read_record", "item_rect"):
            self.assertFalse(hasattr(look, name), name)


class Channels(unittest.TestCase):

    def test_the_channel_box_text(self):
        for value, text in ((0, "0"), (-0.0, "0"), (90, "90"), (1.38, "1.38"),
                            (-179.5134, "-179.513"), (1e-7, "0"),
                            (-1e-7, "0"), (12.5, "12.5")):
            self.assertEqual(look.channel_text(value), text, value)

    def test_parse(self):
        self.assertEqual(look.parse_channel("1,5"), 1.5)
        self.assertEqual(look.parse_channel(" -2 "), -2.0)
        self.assertIsNone(look.parse_channel("x"))
        self.assertIsNone(look.parse_channel(""))
        self.assertIsNone(look.parse_channel(None))

    def test_the_names_nice_and_short(self):
        self.assertEqual(look.channel_names(False)["tx"], "Translate X")
        self.assertEqual(look.channel_names(False)["rz"], "Rotate Z")
        self.assertEqual(look.channel_names(True),
                         dict((c, c) for c in look.CHANNELS))

    def test_a_row_takes_the_nice_names_where_they_fit(self):
        self.assertEqual(look.split_row(100, 55, 14, 40), (False, 55, 42))
        self.assertEqual(look.split_row(80, 55, 14, 40), (True, 14, 63))
        self.assertEqual(look.split_row(10, 55, 14, 40), (True, 14, 0))


class Hits(unittest.TestCase):

    KEYS = [e.key for e in catalog.WEAPONS]

    def setUp(self):
        self.rects = look.panel(320, COUNT)

    def at(self, rect, dx=3, dy=3, scale=1.0):
        x, y = rect[:2]
        return look.hit(self.rects, self.KEYS, x + dx, y + dy, scale)

    def test_a_tile_and_its_name_are_its_weapon(self):
        for index, key in enumerate(self.KEYS):
            tile = self.rects["tiles"][index]
            self.assertEqual(self.at(tile), ("tile", key))
            self.assertEqual(self.at(tile, 3, tile[3] + 5), ("tile", key))   # the name

    def test_a_hand_card_is_its_slot_all_over(self):
        for side in ("R", "L"):
            for part in ("hand_", "column_", "well_", "name_"):
                self.assertEqual(self.at(self.rects[part + side]), ("slot", side), part)

    def test_between_the_tiles_is_the_tiles(self):
        first, second = self.rects["tiles"][0], self.rects["tiles"][1]
        gap_x = first[0] + first[2] + (second[0] - first[0] - first[2]) // 2
        self.assertEqual(look.hit(self.rects, self.KEYS, gap_x, first[1] + 5), ("tiles",))

    def test_the_gaps_are_nothing(self):
        hx, _hy, hw, hh = self.rects["hand_R"]
        self.assertIsNone(look.hit(self.rects, self.KEYS, hx + hw + 1, 5))
        self.assertIsNone(look.hit(self.rects, self.KEYS, -5, -5))


class Worn(unittest.TestCase):
    """The «equipped» pills: what the character holds, in a hand or on the floor."""

    Holding = namedtuple("Holding", "where key")

    def test_a_hand_and_the_floor_count_a_follower_does_not(self):
        holding = {"R": self.Holding("hand", "LongSword_02"),
                   "L": self.Holding("floor", "Dagger_01")}
        self.assertEqual(look.worn(holding), {"LongSword_02", "Dagger_01"})
        holding["L"] = self.Holding("follows", "Spear_01")
        self.assertEqual(look.worn(holding), {"LongSword_02"})
        self.assertEqual(look.worn({"R": None, "L": self.Holding("", "")}), set())
        self.assertEqual(look.worn(None), set())


class Look(unittest.TestCase):
    """2026-09-30, «в стиле нашего интерфейса»: the hub's own tokens, so the
    inventory can never drift from the hub's colours."""

    def test_the_palette_is_the_hubs(self):
        import maya_hubstyle
        self.assertIs(look.PALETTE, maya_hubstyle.TOKENS)

    def test_no_serif_title(self):
        self.assertFalse(hasattr(look, "TITLE_FONTS"))

    def test_the_radii(self):
        self.assertEqual(look.RADIUS, {"card": 8, "well": 6, "item": 4})

    def test_the_tiles_speak_as_armor_s(self):
        self.assertEqual(look.WORN_TEXT, "equipped")
        self.assertEqual(look.GHOST, maya_charlook.GHOST)
        self.assertEqual(look.TURN, 45)


class Icons(unittest.TestCase):

    def test_every_catalog_row_has_an_icon(self):
        for entry in catalog.WEAPONS:
            self.assertTrue(os.path.isfile(look.icon_path(entry.key)), entry.key)

    def test_the_icons_are_assets_so_they_ship(self):
        self.assertTrue(look.icons_dir().startswith(os.path.join(PLUGIN, "assets")))

    def test_stdlib_only(self):
        code = ("import sys; sys.path.insert(0, %r); import maya_invlook; "
                "bad = [m for m in sys.modules if m.split('.')[0] in "
                "('maya', 'PySide6', 'PySide2', 'shiboken6')]; "
                "print(','.join(bad))" % PLUGIN)
        out = subprocess.check_output([sys.executable, "-c", code],
                                      cwd=PLUGIN).decode().strip()
        self.assertEqual(out, "")


if __name__ == "__main__":
    unittest.main()
