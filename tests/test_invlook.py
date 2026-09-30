"""The inventory's look as data (2026-09-29): cells, packing, the card
panel's layout (2026-09-30), the channel text, hits, and every catalog
weapon having its icon.

Spec: docs/superpowers/specs/2026-09-29-weapon-inventory-design.md
"""

import os
import subprocess
import sys
import unittest

import maya_invlook as look
from maya_scenesetup import catalog

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "SkeldarAnim")


class Cells(unittest.TestCase):

    def test_heights_follow_the_length(self):
        self.assertEqual(look.item_cells(45.7), (1, 2))      # Dagger 01
        self.assertEqual(look.item_cells(124.0), (1, 3))     # Creep Sword
        self.assertEqual(look.item_cells(147.0), (1, 4))     # Long Sword 02
        self.assertEqual(look.item_cells(199.6), (1, 5))     # Spear 03
        self.assertEqual(look.item_cells(266.2), (1, 5))     # Spear 01
        self.assertEqual(look.item_cells(5.0), (1, 2))


class Pack(unittest.TestCase):

    def test_column_by_column_first_fit(self):
        placed = look.pack([("a", (1, 4)), ("b", (1, 2)), ("c", (1, 2)),
                            ("d", (1, 5))], cols=3, rows=5)
        self.assertEqual(placed, {"a": (0, 0), "b": (1, 0), "c": (1, 2),
                                  "d": (2, 0)})

    def test_what_does_not_fit_is_left_out(self):
        self.assertEqual(look.pack([("a", (1, 6))], cols=2, rows=5), {})

    def test_the_catalog_fits_the_grid(self):
        cells = look.load_cells()
        items = [(e.key, cells.get(e.key, (1, 3))) for e in catalog.WEAPONS]
        self.assertEqual(set(look.pack(items)), set(e.key for e in catalog.WEAPONS))


def _apart(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay


def _inside(inner, outer):
    ix, iy, iw, ih = inner
    ox, oy, ow, oh = outer
    return ix >= ox and iy >= oy and ix + iw <= ox + ow and iy + ih <= oy + oh


class Panel(unittest.TestCase):
    """2026-09-30: the inventory is the Weapons card - two hands, each a
    Channel Box column left of its well, the grid under them, all from the
    card's width («слева от окошка столбик с параметрами так как в
    стандартном интерфейсе маи в channel box»)."""

    WIDTHS = (250, 320, 360, 500)

    def test_the_hands_stand_side_by_side_the_right_one_on_the_left(self):
        for width in self.WIDTHS:
            r = look.panel(width)
            self.assertLess(r["hand_R"][0], r["hand_L"][0], width)
            self.assertEqual(r["hand_R"][1:], r["hand_L"][1:], width)
            self.assertTrue(_apart(r["hand_R"], r["hand_L"]), width)

    def test_each_column_stands_left_of_its_well_inside_its_card(self):
        for width in self.WIDTHS:
            r = look.panel(width)
            for side in ("R", "L"):
                col, well = r["column_" + side], r["well_" + side]
                self.assertLess(col[0] + col[2], well[0], (width, side))
                for name in ("name_", "column_", "well_"):
                    self.assertTrue(_inside(r[name + side], r["hand_" + side]),
                                    (width, name + side))
                self.assertGreaterEqual(well[2], 36)

    def test_six_rows_in_channel_box_order_top_to_bottom(self):
        self.assertEqual(look.CHANNELS, ("tx", "ty", "tz", "rx", "ry", "rz"))
        r = look.panel(320)
        for side in ("R", "L"):
            tops = [r["row_%s_%s" % (side, ch)][1] for ch in look.CHANNELS]
            self.assertEqual(tops, sorted(tops))
            for ch in look.CHANNELS:
                self.assertTrue(_inside(r["row_%s_%s" % (side, ch)],
                                        r["column_" + side]), ch)
            self.assertEqual(r["row_%s_rz" % side][1] + r["row_%s_rz" % side][3],
                             r["column_" + side][1] + r["column_" + side][3])

    def test_the_grid_is_ten_cells_of_the_width_clamped(self):
        for width in self.WIDTHS:
            r = look.panel(width)
            cell = r["cell"]
            self.assertTrue(look.MIN_CELL <= cell <= look.CELL, width)
            self.assertEqual(r["grid"][2:], (look.COLS * cell, look.ROWS * cell))
            self.assertTrue(_inside(r["grid"], r["gridcard"]), width)
            self.assertLessEqual(r["gridcard"][0] + r["gridcard"][2], max(
                width, r["gridcard"][2]), width)
        self.assertEqual(look.panel(500)["cell"], look.CELL)
        self.assertLess(look.panel(320)["cell"], look.CELL)

    def test_a_wide_card_centres_the_grid(self):
        r = look.panel(500)
        left = r["grid"][0]
        right = 500 - (r["grid"][0] + r["grid"][2])
        self.assertLessEqual(abs(left - right), 1)

    def test_the_grid_is_under_both_hands_and_ends_the_panel(self):
        for width in self.WIDTHS:
            r = look.panel(width)
            for side in ("R", "L"):
                self.assertGreaterEqual(r["gridcard"][1],
                                        r["hand_" + side][1] + r["hand_" + side][3])
            self.assertEqual(r["panel"][3], r["gridcard"][1] + r["gridcard"][3])
            self.assertEqual(r["panel"][2], width)

    def test_scaled_keeps_the_cell_an_int(self):
        r = look.scaled(look.panel(320), 1.5)
        self.assertIsInstance(r["cell"], int)
        self.assertEqual(r["cell"], int(round(look.panel(320)["cell"] * 1.5)))
        self.assertEqual(len(r["grid"]), 4)

    def test_the_window_layout_is_gone(self):
        for name in ("layout", "SLOT", "TITLE_H", "STATUS_H", "MARGIN"):
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
        self.assertEqual(look.split_row(100, 55, 14, 40), (False, 55, 41))
        self.assertEqual(look.split_row(80, 55, 14, 40), (True, 14, 62))
        self.assertEqual(look.split_row(10, 55, 14, 40), (True, 14, 0))


class Hits(unittest.TestCase):

    def setUp(self):
        self.rects = look.panel(320)
        self.cell = self.rects["cell"]
        self.placements = {"LongSword_02": (0, 0), "Dagger_01": (1, 0)}
        self.cells = {"LongSword_02": (1, 4), "Dagger_01": (1, 2)}

    def at(self, name, dx=3, dy=3):
        x, y = self.rects[name][:2]
        return look.hit(self.rects, self.placements, self.cells, x + dx,
                        y + dy, self.cell)

    def test_an_item_its_cells_and_the_grid_between(self):
        c = self.cell
        self.assertEqual(self.at("grid"), ("item", "LongSword_02"))
        self.assertEqual(self.at("grid", 3, 3 * c + 5), ("item", "LongSword_02"))
        self.assertEqual(self.at("grid", c + 3, 3), ("item", "Dagger_01"))
        self.assertEqual(self.at("grid", c + 3, 2 * c + 3), ("grid",))

    def test_a_hand_card_is_its_slot_all_over(self):
        for side in ("R", "L"):
            for part in ("hand_", "column_", "well_", "name_"):
                self.assertEqual(self.at(part + side), ("slot", side), part)

    def test_the_gaps_are_nothing(self):
        hx, _hy, hw, hh = self.rects["hand_R"]
        self.assertIsNone(look.hit(self.rects, self.placements, self.cells,
                                   hx + hw + 1, 5, self.cell))
        self.assertIsNone(look.hit(self.rects, self.placements, self.cells,
                                   -5, -5, self.cell))


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


class Icons(unittest.TestCase):

    def test_every_catalog_row_has_an_icon_and_cells(self):
        cells = look.load_cells()
        for entry in catalog.WEAPONS:
            self.assertTrue(os.path.isfile(look.icon_path(entry.key)), entry.key)
            self.assertIn(entry.key, cells, entry.key)

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


# ------------------------------------------- the grid rearranged (2026-09-29)

DEFAULT = {"LongSword_02": (0, 0), "Spear_01": (1, 0), "Spear_03": (2, 0),
           "Dagger_01": (3, 0), "Creep_Sword": (3, 2)}
SIZES = {"LongSword_02": (1, 4), "Spear_01": (1, 5), "Spear_03": (1, 5),
         "Dagger_01": (1, 2), "Creep_Sword": (1, 3)}


class PlanMove(unittest.TestCase):
    """«можно было перетаскивать по инвентарю»: move into free cells, swap
    with the one item it lands on when that one fits back, else nothing."""

    def test_into_free_cells_it_moves(self):
        kind, placed, other = look.plan_move(DEFAULT, SIZES, "Dagger_01", (6, 1))
        self.assertEqual((kind, placed["Dagger_01"], other), ("move", (6, 1), None))
        self.assertEqual(DEFAULT["Dagger_01"], (3, 0))       # the input untouched

    def test_over_its_own_old_cells_it_moves(self):
        kind, _placed, _other = look.plan_move(DEFAULT, SIZES, "Creep_Sword", (3, 1))
        self.assertIsNone(kind)                  # (3, 1) is the dagger's, and it won't fit back
        _kind, placed, _other = look.plan_move(DEFAULT, SIZES, "Dagger_01", (4, 0))
        kind, placed, _other = look.plan_move(placed, SIZES, "Dagger_01", (4, 1))
        self.assertEqual((kind, placed["Dagger_01"]), ("move", (4, 1)))

    def test_the_same_spot_is_nothing(self):
        self.assertEqual(look.plan_move(DEFAULT, SIZES, "Dagger_01", (3, 0))[0], "same")

    def test_onto_one_item_that_fits_back_they_swap(self):
        kind, placed, other = look.plan_move(DEFAULT, SIZES, "LongSword_02", (1, 0))
        self.assertEqual((kind, other), ("swap", "Spear_01"))
        self.assertEqual((placed["LongSword_02"], placed["Spear_01"]), ((1, 0), (0, 0)))

    def test_onto_one_item_that_does_not_fit_back_nothing(self):
        kind, placed, other = look.plan_move(DEFAULT, SIZES, "Dagger_01", (0, 0))
        self.assertEqual((kind, other), (None, "LongSword_02"))
        self.assertEqual(placed, DEFAULT)

    def test_onto_two_items_nothing(self):
        spots = dict(DEFAULT, Dagger_01=(5, 0), Creep_Sword=(5, 2))
        kind, placed, _other = look.plan_move(spots, SIZES, "LongSword_02", (5, 0))
        self.assertIsNone(kind)
        self.assertEqual(placed, spots)

    def test_the_spot_is_clamped_into_the_grid(self):
        kind, placed, _other = look.plan_move(DEFAULT, SIZES, "Spear_01", (9, 3))
        self.assertEqual((kind, placed["Spear_01"]), ("move", (9, 0)))
        self.assertEqual(look.clamp((-3, 7), (1, 4)), (0, 1))

    def test_a_footprint_is_its_cells(self):
        self.assertEqual(look.footprint((2, 1), (1, 3)), {(2, 1), (2, 2), (2, 3)})


class Arrange(unittest.TestCase):
    """The remembered layout read back: kept where valid, never an item lost."""

    ITEMS = [(k, SIZES[k]) for k in ("LongSword_02", "Spear_01", "Spear_03",
                                      "Dagger_01", "Creep_Sword")]

    def test_nothing_stored_is_the_pack(self):
        self.assertEqual(look.arrange(self.ITEMS, {}), look.pack(self.ITEMS))
        self.assertEqual(look.arrange(self.ITEMS, {}), DEFAULT)

    def test_stored_spots_are_kept(self):
        placed = look.arrange(self.ITEMS, {"Dagger_01": [9, 3], "LongSword_02": [8, 0]})
        self.assertEqual((placed["Dagger_01"], placed["LongSword_02"]), ((9, 3), (8, 0)))
        self.assertEqual(set(placed), set(k for k, _ in self.ITEMS))

    def test_an_overlap_or_a_spot_outside_is_repacked_not_lost(self):
        placed = look.arrange(self.ITEMS, {"LongSword_02": [0, 0], "Spear_01": [0, 0],
                                           "Dagger_01": [9, 4], "Creep_Sword": "x",
                                           "Gone_Row": [5, 0]})
        self.assertEqual(placed["LongSword_02"], (0, 0))
        self.assertEqual(set(placed), set(k for k, _ in self.ITEMS))
        cells = [c for k, s in placed.items() for c in look.footprint(s, SIZES[k])]
        self.assertEqual(len(cells), len(set(cells)))

    def test_the_record_round_trips_and_a_bad_one_reads_empty(self):
        self.assertEqual(look.read_record(look.layout_record(DEFAULT)),
                         dict((k, list(v)) for k, v in DEFAULT.items()))
        self.assertEqual(look.read_record("{not json"), {})
        self.assertEqual(look.read_record(None), {})
        self.assertEqual(look.read_record("[1, 2]"), {})
