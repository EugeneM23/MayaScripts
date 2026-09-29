"""The inventory's look as data (2026-09-29): cells, packing, layout, hits,
and every catalog weapon having its icon.

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


class Layout(unittest.TestCase):

    def setUp(self):
        self.rects = look.layout()

    def test_everything_inside_the_window(self):
        wx, wy, ww, wh = self.rects["window"]
        for name, (x, y, w, h) in self.rects.items():
            self.assertTrue(x >= wx and y >= wy and x + w <= wx + ww
                            and y + h <= wy + wh, name)

    def test_nothing_overlaps(self):
        names = ("title", "name", "slot_R", "slot_L", "grid", "status")
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                ax, ay, aw, ah = self.rects[a]
                bx, by, bw, bh = self.rects[b]
                apart = (ax + aw <= bx or bx + bw <= ax
                         or ay + ah <= by or by + bh <= ay)
                self.assertTrue(apart, (a, b))

    def test_the_grid_is_ten_by_five_cells(self):
        _x, _y, w, h = self.rects["grid"]
        self.assertEqual((w, h), (look.COLS * look.CELL, look.ROWS * look.CELL))

    def test_the_slots_are_two_by_four_cells(self):
        for side in ("R", "L"):
            self.assertEqual(self.rects["slot_" + side][2:],
                             (2 * look.CELL, 4 * look.CELL))

    def test_the_right_hand_slot_is_on_the_viewers_left(self):
        self.assertLess(self.rects["slot_R"][0], self.rects["slot_L"][0])

    def test_it_fits_a_small_screen_at_150_percent(self):
        _x, _y, w, h = look.scaled(self.rects, 1.5)["window"]
        self.assertLess(w, 1000)
        self.assertLess(h, 1100)


class Hits(unittest.TestCase):

    def setUp(self):
        self.rects = look.layout()
        self.placements = {"LongSword_02": (0, 0), "Dagger_01": (1, 0)}
        self.cells = {"LongSword_02": (1, 4), "Dagger_01": (1, 2)}

    def at(self, name, dx=3, dy=3):
        x, y = self.rects[name][:2]
        return look.hit(self.rects, self.placements, self.cells, x + dx, y + dy)

    def test_an_item_its_cells_and_the_grid_between(self):
        self.assertEqual(self.at("grid"), ("item", "LongSword_02"))
        self.assertEqual(self.at("grid", 3, 3 * look.CELL + 5),
                         ("item", "LongSword_02"))
        self.assertEqual(self.at("grid", look.CELL + 3, 3), ("item", "Dagger_01"))
        self.assertEqual(self.at("grid", look.CELL + 3, 2 * look.CELL + 3),
                         ("grid",))

    def test_slots_close_title_nothing(self):
        self.assertEqual(self.at("slot_L"), ("slot", "L"))
        self.assertEqual(self.at("slot_R"), ("slot", "R"))
        self.assertEqual(self.at("close"), ("close",))
        self.assertEqual(self.at("title"), ("title",))
        self.assertIsNone(look.hit(self.rects, self.placements, self.cells, -5, -5))


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
