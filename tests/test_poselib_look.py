"""The Pose Library window's look as data (2026-10-02): how many columns of cards a width
holds and where each card is, what a point is, what the drag's caption says, what the details
panel and the status line say. Stdlib only, like maya_charlook and maya_invlook, so every
decision is tested without Qt or Maya.

Spec: docs/superpowers/specs/2026-10-02-pose-library-design.md
"""
import os
import re
import subprocess
import sys
import unittest
from collections import namedtuple

from maya_poselib import look

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "SkeldarAnim")

# store.Card's fields (Task 1); look must not import store, so the test builds its own - with
# the animation card's six fields and their defaults (2026-10-03), as store.Card has them
Card = namedtuple("Card", "path folder name created author label kind count regions thumbnail "
                          "type frames preview fps start end",
                  defaults=("pose", 0, "", "", 0.0, 0.0))

# a card of the listing, every field given: the animation tests build theirs from it
BASE = dict(path="p/Walk.anim", folder="", name="Walk", created="2026-10-03T12:00:00",
            author="E", label="Manny [rig]", kind="character", count=2, regions=["Spine"],
            thumbnail="")


def _tile(rect, scale=1.0):
    """A card's square and its name strip as (x, y, w, h)."""
    x, y, w, h = rect
    return (x, y, w, h + int(round(look.NAME_H * scale)))


def _apart(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay


class Constants(unittest.TestCase):

    def test_the_numbers_the_window_is_built_on(self):
        self.assertEqual((look.CELL_MIN, look.CELL_MAX, look.CELL_DEFAULT),
                         (72, 200, 112))
        self.assertEqual((look.GAP, look.NAME_H, look.GHOST, look.THROTTLE_MS),
                         (8, 34, 96, 33))
        self.assertEqual(look.DOT, "\u00b7")


class Grid(unittest.TestCase):

    def test_a_wide_pane_holds_every_card_in_one_row(self):
        # 1000 // (112 + 8) = 8 columns fit, but there are only 7 cards
        cols, rects, height = look.grid(1000, 7, 112)
        self.assertEqual(cols, 7)
        self.assertEqual(len(rects), 7)
        self.assertEqual(len(set(r[1] for r in rects)), 1)
        self.assertEqual(height, 112 + look.NAME_H)

    def test_the_card_size_is_the_card_size(self):
        """The slider says 112, the card is 112 wide and square - the extra width goes into the
        gaps between the columns, never into the cards."""
        _cols, rects, _height = look.grid(1000, 7, 112)
        self.assertEqual(set((r[2], r[3]) for r in rects), {(112, 112)})

    def test_a_full_row_is_spread_to_fill_the_width(self):
        # 1022 px holds 8 columns of 112 with a step of exactly 130: equal gaps of 18
        cols, rects, _height = look.grid(1022, 8, 112)
        self.assertEqual(cols, 8)
        self.assertEqual(rects[0][0], 0)
        self.assertEqual(rects[-1][0] + rects[-1][2], 1022)
        gaps = [b[0] - (a[0] + a[2]) for a, b in zip(rects, rects[1:])]
        self.assertEqual(gaps, [18] * 7)

    def test_a_full_row_ends_on_the_edge_at_every_width(self):
        """Whatever the width, the last column of a row that fills the columns that fit touches
        the right edge, and the gaps differ by at most one px (rounding)."""
        for scale in (1.0, 1.25, 1.5):
            for width in range(150, 1500):
                fit = look.grid(width, 100, 112, scale)[0]
                if fit < 2:
                    continue
                _cols, rects, _height = look.grid(width, fit, 112, scale)
                self.assertEqual(rects[0][0], 0, (scale, width))
                self.assertEqual(rects[-1][0] + rects[-1][2], width, (scale, width))
                gaps = [b[0] - (a[0] + a[2]) for a, b in zip(rects, rects[1:])]
                self.assertLessEqual(max(gaps) - min(gaps), 1, (scale, width, gaps))

    def test_a_short_row_stands_where_a_full_row_would_put_it(self):
        """The spread is over the columns that FIT, not over the cards there are: the reviewer's
        case, 500 px holds 4 columns of 112 and the cards sit at the same x whether the library
        holds one, two, three or four of them."""
        for count in (1, 2, 3, 4):
            _cols, rects, _height = look.grid(500, count, 112)
            self.assertEqual([r[0] for r in rects], [0, 129, 259, 388][:count], count)
        # 1000 px holds 8: three cards are not pushed to 0 / 444 / 888
        self.assertEqual([r[0] for r in look.grid(1000, 3, 112)[1]], [0, 127, 254])

    def test_a_card_does_not_move_when_another_is_added(self):
        """Every Save adds a card; the ones already there must stay where they are, at every
        width, card size and scale - and so must a card in a second row."""
        for scale in (1.0, 1.5):
            for cell in (72, 112, 200):
                for width in (0, 90, 231, 240, 300, 500, 777, 1000, 1400):
                    fit = look.grid(width, 1000, cell, scale)[0]
                    big = look.grid(width, 3 * fit + 1, cell, scale)[1]
                    for count in range(1, 3 * fit + 2):
                        rects = look.grid(width, count, cell, scale)[1]
                        label = (scale, cell, width, count)
                        self.assertEqual([r[0] for r in rects], [r[0] for r in big[:count]],
                                         label)
                        self.assertEqual(rects, big[:count], label)

    def test_one_card_in_a_wide_pane_stands_at_the_left_like_the_first_of_a_longer_row(self):
        self.assertEqual(look.grid(1000, 1, 112)[1][0][0], 0)
        self.assertEqual(look.grid(1000, 1, 112)[1][0], look.grid(1000, 30, 112)[1][0])

    def test_a_narrow_pane_wraps(self):
        # 300 // (112 + 8) = 2 columns, 7 cards -> 4 rows, the last one holding a single card
        cols, rects, height = look.grid(300, 7, 112)
        self.assertEqual(cols, 2)
        self.assertEqual(len(set(r[1] for r in rects)), 4)
        self.assertEqual(height, 4 * (112 + look.NAME_H) + 3 * look.GAP)

    def test_rows_stand_one_card_and_one_gap_apart(self):
        _cols, rects, _height = look.grid(300, 7, 112)
        self.assertEqual(rects[0][1], 0)
        self.assertEqual(rects[2][1], 112 + look.NAME_H + look.GAP)
        self.assertEqual(rects[4][1], 2 * (112 + look.NAME_H + look.GAP))

    def test_a_short_last_row_keeps_the_columns(self):
        _cols, rects, _height = look.grid(300, 7, 112)
        self.assertEqual(rects[6][0], rects[0][0])
        self.assertEqual(rects[5][0], rects[1][0])
        self.assertEqual(rects[1][0] + rects[1][2], 300)

    def test_exactly_enough_width_fits_the_column(self):
        # n cards need n * cell + (n - 1) * gap
        self.assertEqual(look.grid(2 * 112 + look.GAP, 5, 112)[0], 2)
        self.assertEqual(look.grid(2 * 112 + look.GAP - 1, 5, 112)[0], 1)

    def test_one_column_is_centred(self):
        cols, rects, _height = look.grid(200, 3, 112)
        self.assertEqual(cols, 1)
        self.assertEqual([r[0] for r in rects], [44, 44, 44])

    def test_a_pane_narrower_than_a_card_shrinks_the_card_not_the_row(self):
        cols, rects, _height = look.grid(90, 3, 112)
        self.assertEqual(cols, 1)
        self.assertEqual({(r[0], r[2], r[3]) for r in rects}, {(0, 90, 90)})

    def test_no_width_yet_is_one_column(self):
        for width in (0, -5, None):
            cols, rects, height = look.grid(width, 3, 112)
            self.assertEqual(cols, 1, width)
            self.assertEqual([r[0] for r in rects], [0, 0, 0], width)
            self.assertEqual(height, 3 * (112 + look.NAME_H) + 2 * look.GAP, width)

    def test_the_card_size_is_clamped(self):
        self.assertEqual(look.grid(1000, 3, 10)[1][0][2], look.CELL_MIN)
        self.assertEqual(look.grid(1000, 3, 999)[1][0][2], look.CELL_MAX)
        self.assertEqual(look.grid(1000, 3, 200)[1][0][2], 200)

    def test_nothing_to_lay_out(self):
        cols, rects, height = look.grid(500, 0, 112)
        self.assertEqual((rects, height), ([], 0))
        self.assertGreaterEqual(cols, 1)

    def test_the_scale_multiplies_every_size(self):
        # 450 px at 150 %: 168 px cards, 12 px gaps, 51 px name strips; (450 + 12) // 180 = 2
        cols, rects, height = look.grid(450, 7, 112, scale=1.5)
        self.assertEqual(cols, 2)
        self.assertEqual(rects[0][2], 168)
        self.assertEqual(rects[2][1], 168 + 51 + 12)
        self.assertEqual(height, 4 * (168 + 51) + 3 * 12)

    def test_the_scale_changes_how_many_fit(self):
        self.assertEqual(look.grid(1000, 20, 112, scale=1.0)[0], 8)
        self.assertEqual(look.grid(1000, 20, 112, scale=1.5)[0], 5)

    def test_cards_never_overlap_and_stay_inside_the_pane(self):
        """Every width, count, card size and scale the window can meet."""
        for scale in (1.0, 1.25, 1.5, 2.0):
            for cell in (72, 112, 150, 200):
                for width in (0, 60, 150, 231, 232, 300, 480, 777, 1000, 1400):
                    for count in (1, 2, 7, 30):
                        cols, rects, height = look.grid(width, count, cell, scale)
                        label = (scale, cell, width, count)
                        self.assertEqual(len(rects), count, label)
                        self.assertGreaterEqual(cols, 1, label)
                        tiles = [_tile(r, scale) for r in rects]
                        for i, a in enumerate(tiles):
                            for b in tiles[i + 1:]:
                                self.assertTrue(_apart(a, b), (label, a, b))
                            self.assertGreaterEqual(a[0], 0, label)
                            self.assertGreaterEqual(a[1], 0, label)
                            self.assertLessEqual(a[1] + a[3], height, label)
                            if width > 0:
                                self.assertLessEqual(a[0] + a[2], width, label)

    def test_the_gap_between_columns_is_never_below_the_gap(self):
        """Every pixel width (the rounding of the spread must never eat into the gap), full
        rows and short ones, at three card sizes and scales."""
        for scale in (1.0, 1.5):
            gap = int(round(look.GAP * scale))
            for cell in (72, 112, 200):
                for width in range(150, 1500):
                    for count in (2, 3, 5, 12):
                        _cols, rects, _height = look.grid(width, count, cell, scale)
                        for a, b in zip(rects, rects[1:]):
                            if b[1] == a[1]:
                                self.assertGreaterEqual(b[0] - (a[0] + a[2]), gap,
                                                        (scale, cell, width, count))


class Strips(unittest.TestCase):
    """The painter draws the name where the hit test and the culling think it is: one rounding."""

    def test_the_name_strip_sits_under_the_square(self):
        rect = look.grid(300, 7, 112)[1][3]
        x, y, w, h = rect
        self.assertEqual(look.name_rect(rect), (x, y + h, w, look.NAME_H))

    def test_the_tile_is_the_square_and_its_strip(self):
        rect = look.grid(300, 7, 112)[1][3]
        x, y, w, h = rect
        self.assertEqual(look.tile_rect(rect), (x, y, w, h + look.NAME_H))

    def test_both_follow_the_scale(self):
        rect = look.grid(450, 7, 112, scale=1.5)[1][0]
        self.assertEqual(look.name_rect(rect, 1.5)[3], 51)
        self.assertEqual(look.tile_rect(rect, 1.5)[3], 168 + 51)


class Visible(unittest.TestCase):

    def setUp(self):
        # 2 columns, 4 rows; a row is 112 + 34 = 146 px tall and 154 px apart
        self.rects = look.grid(300, 7, 112)[1]

    def test_the_top_of_the_list(self):
        self.assertEqual(look.visible(self.rects, 0, 100), [0, 1])

    def test_a_middle_slice_culls_the_rest(self):
        self.assertEqual(look.visible(self.rects, 160, 300), [2, 3])

    def test_a_card_cut_by_the_edge_is_visible(self):
        # row 0 ends at 146 (its name strip included), row 1 starts at 154
        self.assertEqual(look.visible(self.rects, 140, 160), [0, 1, 2, 3])

    def test_the_name_strip_counts(self):
        # 112 is the end of the square, 146 the end of the strip
        self.assertEqual(look.visible(self.rects, 120, 130), [0, 1])

    def test_the_gap_alone_shows_nothing(self):
        self.assertEqual(look.visible(self.rects, 146, 154), [])

    def test_everything_and_nothing(self):
        self.assertEqual(look.visible(self.rects, -10, 10 ** 6), list(range(7)))
        self.assertEqual(look.visible(self.rects, 10 ** 6, 10 ** 6 + 100), [])
        self.assertEqual(look.visible([], 0, 100), [])

    def test_the_scale_widens_the_name_strip(self):
        rects = look.grid(450, 7, 112, scale=1.5)[1]
        # row 0 ends at 168 + 51 = 219 at 150 %, but at 168 + 34 = 202 with a 100 % strip
        self.assertEqual(look.visible(rects, 205, 215, scale=1.5), [0, 1])
        self.assertEqual(look.visible(rects, 205, 215, scale=1.0), [])


class Hit(unittest.TestCase):

    def setUp(self):
        self.rects = look.grid(300, 7, 112)[1]

    def test_inside_the_square(self):
        x, y, w, h = self.rects[3]
        self.assertEqual(look.hit(self.rects, x + 3, y + 3), 3)
        self.assertEqual(look.hit(self.rects, x + w - 1, y + h - 1), 3)

    def test_inside_the_name_strip(self):
        x, y, w, h = self.rects[3]
        self.assertEqual(look.hit(self.rects, x + 3, y + h + 5), 3)
        self.assertEqual(look.hit(self.rects, x + 3, y + h + look.NAME_H - 1), 3)

    def test_the_edges_are_exclusive(self):
        x, y, w, h = self.rects[0]
        self.assertIsNone(look.hit(self.rects, x + w, y + 3))
        self.assertIsNone(look.hit(self.rects, x + 3, y + h + look.NAME_H))
        self.assertIsNone(look.hit(self.rects, x - 1, y + 3))

    def test_the_gaps_are_nothing(self):
        x, y, w, h = self.rects[0]
        # between the two columns
        self.assertIsNone(look.hit(self.rects, x + w + 4, y + 3))
        # between the rows
        self.assertIsNone(look.hit(self.rects, x + 3, y + h + look.NAME_H + 4))

    def test_outside_and_empty(self):
        self.assertIsNone(look.hit(self.rects, -5, -5))
        self.assertIsNone(look.hit(self.rects, 10 ** 5, 10 ** 5))
        self.assertIsNone(look.hit([], 5, 5))

    def test_the_scale_widens_the_name_strip(self):
        rects = look.grid(450, 7, 112, scale=1.5)[1]
        x, y, w, h = rects[0]
        self.assertEqual(look.hit(rects, x + 3, y + h + 40, scale=1.5), 0)
        self.assertIsNone(look.hit(rects, x + 3, y + h + 40, scale=1.0))

    def test_every_card_finds_itself(self):
        rects = look.grid(777, 25, 100)[1]
        for index, (x, y, w, h) in enumerate(rects):
            self.assertEqual(look.hit(rects, x + w // 2, y + h // 2), index)


class DropCaption(unittest.TestCase):

    def test_over_a_character(self):
        aim = {"kind": "character", "label": "Manny_Rig1"}
        self.assertEqual(look.drop_caption("Fist", aim), ("Fist \u00b7 onto Manny_Rig1", True))

    def test_over_the_floor_names_the_character_it_would_bring(self):
        aim = {"kind": "floor", "label": "Manny [rig]", "point": (120.4, 0.0, -35.6)}
        self.assertEqual(look.drop_caption("Fist", aim),
                         ("Fist \u00b7 a new Manny [rig] \u00b7 floor (120, -36)", True))

    def test_the_floor_point_is_x_and_z(self):
        aim = {"kind": "floor", "label": "Creep [rig]", "point": (-7.0, 55.0, 9.4)}
        self.assertEqual(look.drop_caption("Pose", aim)[0],
                         "Pose \u00b7 a new Creep [rig] \u00b7 floor (-7, 9)")

    def test_a_floor_without_a_point_or_a_label(self):
        self.assertEqual(look.drop_caption("Fist", {"kind": "floor", "label": "Manny [rig]"}),
                         ("Fist \u00b7 a new Manny [rig]", True))
        self.assertEqual(look.drop_caption("Fist", {"kind": "floor"}),
                         ("Fist \u00b7 a new character", True))

    def test_over_a_folder(self):
        self.assertEqual(look.drop_caption("Fist", {"kind": "folder", "folder": "Hands"}),
                         ("Fist \u00b7 move to Hands", True))
        self.assertEqual(look.drop_caption("Fist", {"kind": "folder", "folder": "Hands/Left"})[0],
                         "Fist \u00b7 move to Hands/Left")

    def test_over_the_library_root(self):
        self.assertEqual(look.drop_caption("Fist", {"kind": "folder", "folder": ""})[0],
                         "Fist \u00b7 move to Library")

    def test_no_target_says_why(self):
        self.assertEqual(look.drop_caption("Fist", {"kind": "none", "text": "no character here"}),
                         ("no character here", False))
        self.assertEqual(look.drop_caption("Fist", {"kind": "none"}), ("no target", False))

    def test_over_the_window_itself(self):
        self.assertEqual(look.drop_caption("Fist", {"kind": "window"}),
                         ("release off the window to apply", False))
        self.assertEqual(look.OFF_WINDOW, "release off the window to apply")

    def test_nothing_and_the_unknown(self):
        self.assertEqual(look.drop_caption("Fist", None), ("no target", False))
        self.assertEqual(look.drop_caption("Fist", {}), ("no target", False))
        self.assertEqual(look.drop_caption("Fist", {"kind": "moon"}), ("no target", False))

    def test_an_empty_name_still_reads(self):
        self.assertEqual(look.drop_caption("", {"kind": "character", "label": "Rig"})[0],
                         "Pose \u00b7 onto Rig")


class Details(unittest.TestCase):

    CHARACTER = {
        "kind": "character", "name": "Fist", "author": "Eugene",
        "created": "2026-10-02T18:00:00", "scene": "shot_010.ma", "frame": 12.0,
        "character": {"label": "Manny [rig]", "key": "Manny_Rig"},
        "members": ["hand_l", "index_01_l", "middle_01_l"], "regions": ["Hand L", "Arm L"],
    }

    OBJECTS = {
        "kind": "objects", "name": "Cubes", "author": "Eugene",
        "created": "2026-10-02T09:05:59", "scene": "rig_test.ma", "frame": 5,
        "objects": [{"name": "pCube1", "path": "|pCube1", "attrs": {"translateX": 1.0}},
                    {"name": "pCube2", "path": "|pCube2", "attrs": {}}],
    }

    def card(self, **fields):
        base = dict(path="p/Fist.pose", folder="", name="Fist", created="2026-10-02T18:00:00",
                    author="Eugene", label="Manny [rig]", kind="character", count=3,
                    regions=["Hand L", "Arm L"], thumbnail="")
        base.update(fields)
        return Card(**base)

    def test_a_character_card(self):
        self.assertEqual(look.details(self.card(), self.CHARACTER), [
            "Manny [rig]",
            "3 bones \u00b7 Hand L, Arm L",
            "Eugene \u00b7 2026-10-02 18:00",
            "frame 12 \u00b7 shot_010.ma",
        ])

    def test_an_objects_card(self):
        card = self.card(label="objects", kind="objects", count=2, regions=[])
        self.assertEqual(look.details(card, self.OBJECTS), [
            "Objects",
            "2 objects",
            "Eugene \u00b7 2026-10-02 09:05",
            "frame 5 \u00b7 rig_test.ma",
        ])

    def test_singular_counts(self):
        data = dict(self.CHARACTER, members=["hand_l"], regions=[])
        self.assertEqual(look.details(self.card(), data)[1], "1 bone")
        objects = dict(self.OBJECTS, objects=[{"name": "a", "path": "|a", "attrs": {}}])
        self.assertEqual(look.details(self.card(kind="objects"), objects)[1], "1 object")

    def test_no_regions_is_just_the_count(self):
        data = dict(self.CHARACTER, regions=[])
        self.assertEqual(look.details(self.card(), data)[1], "3 bones")

    def test_a_fractional_frame(self):
        data = dict(self.CHARACTER, frame=12.5)
        self.assertEqual(look.details(self.card(), data)[3], "frame 12.5 \u00b7 shot_010.ma")

    def test_what_is_missing_is_left_out(self):
        data = dict(self.CHARACTER, author="", scene="")
        lines = look.details(self.card(author=""), data)
        self.assertEqual(lines[2], "2026-10-02 18:00")
        self.assertEqual(lines[3], "frame 12")
        data = dict(self.CHARACTER, frame=None)
        self.assertEqual(look.details(self.card(), data)[3], "shot_010.ma")
        data = dict(self.CHARACTER, frame=None, scene="")
        self.assertEqual(len(look.details(self.card(), data)), 3)

    def test_a_scene_path_shows_its_file_name(self):
        data = dict(self.CHARACTER, scene="C:/work/shots/shot_010.ma")
        self.assertEqual(look.details(self.card(), data)[3], "frame 12 \u00b7 shot_010.ma")
        data = dict(self.CHARACTER, scene="C:\\work\\shots\\shot_010.ma")
        self.assertEqual(look.details(self.card(), data)[3], "frame 12 \u00b7 shot_010.ma")

    def test_the_card_stands_in_when_the_file_is_not_read_yet(self):
        lines = look.details(self.card(), None)
        self.assertEqual(lines, ["Manny [rig]", "3 bones \u00b7 Hand L, Arm L",
                                 "Eugene \u00b7 2026-10-02 18:00"])

    def test_the_file_wins_over_the_card(self):
        data = dict(self.CHARACTER, author="Oleg", character={"label": "Creep [rig]"})
        lines = look.details(self.card(), data)
        self.assertEqual(lines[0], "Creep [rig]")
        self.assertTrue(lines[2].startswith("Oleg"))

    def test_a_strange_created_is_shown_as_it_is(self):
        data = dict(self.CHARACTER, created="last Tuesday")
        self.assertEqual(look.details(self.card(created="last Tuesday"), data)[2],
                         "Eugene \u00b7 last Tuesday")

    def test_nothing_at_all_is_an_empty_list(self):
        self.assertEqual(look.details(None, None), [])
        self.assertEqual(look.details(None, {}), [])


class StatusLine(unittest.TestCase):

    FULL = {"name": "Fist", "target": "Manny_Rig1", "count": 23, "noun": "controls",
            "layer": "AnimLayer1", "frame": 12.0, "worst": 0.003, "worst_unit": "deg",
            "notes": ["the FK forearm twist is lost on arm_r (31 deg)"]}

    def test_the_whole_summary(self):
        self.assertEqual(
            look.status_line(self.FULL),
            "Fist onto Manny_Rig1: 23 controls keyed on AnimLayer1 at frame 12 - worst 0.003 deg"
            " | the FK forearm twist is lost on arm_r (31 deg)")

    def test_several_notes(self):
        applied = dict(self.FULL, notes=["no hand_l on Creep_Rig", "weapon_r is driven"])
        self.assertTrue(look.status_line(applied).endswith(
            " | no hand_l on Creep_Rig | weapon_r is driven"))

    def test_a_skeleton(self):
        applied = {"name": "Fist", "target": "root", "count": 11, "noun": "bones",
                   "frame": 3, "worst": 0.0, "worst_unit": "deg"}
        self.assertEqual(look.status_line(applied),
                         "Fist onto root: 11 bones keyed at frame 3 - worst 0 deg")

    def test_the_least_that_reads(self):
        self.assertEqual(look.status_line({"name": "Fist", "target": "Rig", "count": 4}),
                         "Fist onto Rig: 4 channels keyed")

    def test_one_of_a_kind(self):
        applied = {"name": "Fist", "target": "Rig", "count": 1, "noun": "controls"}
        self.assertEqual(look.status_line(applied), "Fist onto Rig: 1 control keyed")

    def test_a_worst_too_small_to_print(self):
        applied = dict(self.FULL, worst=0.0004, notes=[])
        self.assertIn("worst <0.001 deg", look.status_line(applied))
        applied = dict(self.FULL, worst=12.3456, notes=[])
        self.assertIn("worst 12.346 deg", look.status_line(applied))

    def test_a_worst_in_centimetres(self):
        applied = dict(self.FULL, worst=0.02, worst_unit="cm", notes=[])
        self.assertTrue(look.status_line(applied).endswith("worst 0.02 cm"))

    def test_several_targets(self):
        second = dict(self.FULL, target="Manny_Rig2", notes=[])
        text = look.status_line([dict(self.FULL, notes=[]), second])
        self.assertEqual(text.count(" | "), 1)
        self.assertIn("Fist onto Manny_Rig1:", text)
        self.assertTrue(text.split(" | ")[1].startswith("Fist onto Manny_Rig2:"))

    def test_nothing_applied(self):
        self.assertEqual(look.status_line(None), "")
        self.assertEqual(look.status_line({}), "")
        self.assertEqual(look.status_line([]), "")


class ZoomRect(unittest.TestCase):
    """The card under the mouse shown twice as large over its neighbours (2026-10-03): its tile
    grown about its own centre, moved inside the viewport rather than cut."""

    VIEW = (0, 0, 1000, 800)

    def grown(self, rect, view=VIEW, scale=1.0, **kw):
        return look.zoom_rect(rect, view, scale, **kw)

    def test_the_numbers(self):
        self.assertEqual(look.ZOOM, 2.0)
        self.assertEqual(look.ZOOM_MARGIN, 6)
        self.assertEqual((look.ZOOM_IN_MS, look.ZOOM_OUT_MS), (140, 180))

    def test_twice_the_tile_about_its_centre(self):
        rect = (400, 300, 112, 112)
        (x, y, w, h), z = self.grown(rect)
        self.assertEqual(z, 2.0)
        tile = _tile(rect)
        self.assertEqual((w, h), (tile[2] * 2.0, tile[3] * 2.0))
        self.assertAlmostEqual(x + w / 2.0, tile[0] + tile[2] / 2.0)
        self.assertAlmostEqual(y + h / 2.0, tile[1] + tile[3] / 2.0)

    def test_moved_inside_the_top_left(self):
        (x, y, w, h), z = self.grown((20, 20, 112, 112))
        self.assertEqual(z, 2.0)
        self.assertEqual((x, y), (look.ZOOM_MARGIN, look.ZOOM_MARGIN))

    def test_moved_inside_the_bottom_right(self):
        rect = (1000 - 112 - 20, 800 - 112 - look.NAME_H - 20, 112, 112)
        (x, y, w, h), _z = self.grown(rect)
        self.assertAlmostEqual(x + w, 1000 - look.ZOOM_MARGIN)
        self.assertAlmostEqual(y + h, 800 - look.ZOOM_MARGIN)

    def test_a_card_on_the_edge_grows_flush_with_it(self):
        # the first column touches the pane's left edge: the margin would put the grown card
        # beside the mouse instead of under it
        (x, y, _w, _h), _z = self.grown((0, 0, 112, 112))
        self.assertEqual((x, y), (0, 0))
        rect = (1000 - 112, 800 - 112 - look.NAME_H, 112, 112)
        (x, y, w, h), _z = self.grown(rect)
        self.assertEqual((x + w, y + h), (1000, 800))

    def test_the_view_is_where_the_scroll_stands(self):
        # the viewport shows canvas rows 2000..2400: a card near its top edge grows downwards
        rect = (300, 2010, 112, 112)
        (_x, y, _w, _h), _z = self.grown(rect, view=(0, 2000, 1000, 400))
        self.assertEqual(y, 2000 + look.ZOOM_MARGIN)

    def test_a_card_cut_by_the_edge_grows_inside_the_view(self):
        (_x, y, _w, _h), _z = self.grown((300, 1950, 112, 112), view=(0, 2000, 1000, 400))
        self.assertEqual(y, 2000 + look.ZOOM_MARGIN)

    def test_a_short_view_shrinks_the_factor_to_fit(self):
        rect = (100, 100, 112, 112)
        tile_h = 112 + look.NAME_H
        (_x, y, _w, h), z = self.grown(rect, view=(0, 0, 1000, 250))
        self.assertAlmostEqual(z, (250 - 2 * look.ZOOM_MARGIN) / float(tile_h))
        self.assertAlmostEqual(h, 250 - 2 * look.ZOOM_MARGIN)
        self.assertTrue(0 <= y and y + h <= 250)

    def test_never_smaller_than_the_card(self):
        (_x, _y, w, _h), z = self.grown((0, 0, 112, 112), view=(0, 0, 90, 90))
        self.assertEqual(z, 1.0)
        self.assertEqual(w, 112)

    def test_the_scale_multiplies_the_margin(self):
        (x, y, _w, _h), _z = self.grown((30, 30, 168, 168), view=(0, 0, 1500, 1200), scale=1.5)
        self.assertEqual((x, y), (look.ZOOM_MARGIN * 1.5, look.ZOOM_MARGIN * 1.5))

    def test_the_name_strip_grows_with_it(self):
        (_x, _y, w, h), z = self.grown((400, 300, 168, 168), view=(0, 0, 1500, 1200),
                                       scale=1.5)
        self.assertAlmostEqual(h - w, round(look.NAME_H * 1.5) * z)

    def test_no_view_is_centred(self):
        (x, y, w, h), z = self.grown((400, 300, 112, 112), view=None)
        self.assertEqual(z, 2.0)
        self.assertEqual((x, y), (400 - 56, 300 - (112 + look.NAME_H) / 2.0))

    def test_the_grown_card_holds_the_card_s_own_tile(self):
        # so the mouse, on the card's own tile when it starts to grow, is on the grown card
        _cols, rects, _h = look.grid(700, 30, look.CELL_DEFAULT)
        for view in ((0, 0, 700, 500), (0, 300, 700, 400), (0, 610, 700, 310)):
            for rect in rects:
                x, y, w, h = _tile(rect)
                if not (view[1] <= y and y + h <= view[1] + view[3]):
                    continue                    # a card cut by the edge is not hovered whole
                (gx, gy, gw, gh), z = self.grown(rect, view=view)
                self.assertEqual(z, 2.0)
                self.assertTrue(gx <= x and x + w <= gx + gw, (rect, view))
                self.assertTrue(gy <= y and y + h <= gy + gh, (rect, view))
                self.assertTrue(view[0] <= gx and gx + gw <= view[0] + view[2], (rect, view))
                self.assertTrue(view[1] <= gy and gy + gh <= view[1] + view[3], (rect, view))


class ZoomAt(unittest.TestCase):

    def test_the_ends_and_the_middle(self):
        rect = (400, 300, 112, 112)
        target = look.zoom_rect(rect, (0, 0, 1000, 800))
        self.assertEqual(look.zoom_at(rect, target, 0.0), (_tile(rect), 1.0))
        self.assertEqual(look.zoom_at(rect, target, 1.0), target)
        (x, y, w, h), z = look.zoom_at(rect, target, 0.5)
        self.assertEqual(z, 1.5)
        self.assertEqual(w, 112 * 1.5)
        tile = _tile(rect)
        self.assertAlmostEqual(x, (tile[0] + target[0][0]) / 2.0)


class Zoom(unittest.TestCase):
    """One card's zoom level over time: 0 at rest, 1 grown."""

    def test_at_rest(self):
        zoom = look.Zoom()
        self.assertEqual(zoom.level(0), 0.0)
        self.assertFalse(zoom.moving(0))
        self.assertFalse(zoom.lifted(0))

    def test_growing_takes_zoom_in_ms_eased_out(self):
        zoom = look.Zoom()
        zoom.to(1.0, 1000)
        self.assertTrue(zoom.moving(1000))
        self.assertTrue(zoom.lifted(1001))
        self.assertGreater(zoom.level(1000 + look.ZOOM_IN_MS // 2), 0.6)   # fast start
        self.assertLess(zoom.level(1000 + look.ZOOM_IN_MS - 1), 1.0)
        self.assertEqual(zoom.level(1000 + look.ZOOM_IN_MS), 1.0)
        self.assertFalse(zoom.moving(1000 + look.ZOOM_IN_MS))

    def test_shrinking_takes_zoom_out_ms(self):
        zoom = look.Zoom()
        zoom.to(1.0, 0, animate=False)
        zoom.to(0.0, 500)
        self.assertGreater(zoom.level(500 + look.ZOOM_OUT_MS - 1), 0.0)
        self.assertEqual(zoom.level(500 + look.ZOOM_OUT_MS), 0.0)
        self.assertFalse(zoom.lifted(500 + look.ZOOM_OUT_MS))

    def test_turned_back_mid_way_starts_where_it_stands(self):
        zoom = look.Zoom()
        zoom.to(1.0, 0)
        mid = zoom.level(40)
        zoom.to(0.0, 40)
        self.assertEqual(zoom.level(40), mid)
        self.assertEqual(zoom.ms, max(look.ZOOM_MIN_MS, int(round(look.ZOOM_OUT_MS * mid))))

    def test_without_animation_at_once(self):
        zoom = look.Zoom()
        zoom.to(1.0, 0, animate=False)
        self.assertEqual(zoom.level(0), 1.0)
        self.assertFalse(zoom.moving(0))
        zoom.to(0.0, 5, animate=False)
        self.assertEqual(zoom.level(5), 0.0)

    def test_the_same_target_again_changes_nothing(self):
        zoom = look.Zoom()
        zoom.to(1.0, 0)
        zoom.to(1.0, 50)
        self.assertEqual(zoom.t0, 0)


class Animation(unittest.TestCase):
    """The animation cards (2026-10-03): the clip's rate, the preview sheet and which of its
    cells plays, the badge, the details and the status line of a paste."""

    def test_fps_of_the_units(self):
        self.assertEqual(look.fps_of("ntsc"), 30.0)
        self.assertEqual(look.fps_of("film"), 24.0)
        self.assertAlmostEqual(look.fps_of("23.976fps"), 23.976)
        self.assertEqual(look.fps_of("bogus"), 30.0)

    def test_every_named_unit(self):
        self.assertEqual(look.FPS, {"game": 15.0, "film": 24.0, "pal": 25.0, "ntsc": 30.0,
                                    "show": 48.0, "palf": 50.0, "ntscf": 60.0})
        for unit, fps in look.FPS.items():
            self.assertEqual(look.fps_of(unit), fps, unit)
        self.assertEqual(look.fps_of("120fps"), 120.0)
        for nothing in ("", None, "0fps", "fps", "-5fps"):
            self.assertEqual(look.fps_of(nothing), 30.0, nothing)

    def test_preview_frames_and_step(self):
        self.assertEqual(look.preview_frames(0, 47), (list(range(48)), 1))
        frames, step = look.preview_frames(0, 199)
        self.assertEqual(step, 4)
        self.assertEqual(frames[:3], [0, 4, 8])
        self.assertLessEqual(len(frames), 60)
        self.assertEqual(look.preview_frames(5, 5), ([5], 1))

    def test_preview_frames_stay_inside_the_range(self):
        self.assertEqual((look.PREVIEW_MAX, look.PREVIEW_SIZE), (60, 320))
        for start, end in ((0, 59), (0, 60), (10, 250), (-20, 17), (3, 1000)):
            frames, step = look.preview_frames(start, end)
            self.assertEqual(frames[0], start)
            self.assertLessEqual(frames[-1], end)
            self.assertLessEqual(len(frames), look.PREVIEW_MAX, (start, end))
            self.assertEqual(frames, list(range(start, end + 1, step)))
        self.assertEqual(look.preview_frames(0, 9, most=4), ([0, 3, 6, 9], 3))

    def test_sheet_geometry(self):
        self.assertEqual(look.sheet_columns(48), 7)
        self.assertEqual(look.sheet_columns(1), 1)
        self.assertEqual(look.sheet_columns(0), 1)
        self.assertEqual(look.sheet_columns(49), 7)
        self.assertEqual(look.sheet_columns(50), 8)
        self.assertEqual(look.sheet_cell(8, 7, 320), (320, 320, 320, 320))
        self.assertEqual(look.sheet_cell(0, 7, 320), (0, 0, 320, 320))
        self.assertEqual(look.sheet_cell(6, 7, 320), (1920, 0, 320, 320))

    def test_play_cell_runs_at_the_clips_rate(self):
        self.assertEqual(look.play_cell(0, 48, 1, 30.0), 0)
        self.assertEqual(look.play_cell(1000, 48, 1, 30.0), 30)
        self.assertEqual(look.play_cell(1000, 48, 4, 30.0), 7)
        self.assertEqual(look.play_cell(1700, 48, 1, 30.0), 3)      # 51 % 48
        self.assertEqual(look.play_cell(999, 1, 1, 30.0), 0)
        self.assertEqual(look.PLAY_MS, 33)

    def test_badge(self):
        self.assertEqual(look.badge_text(48), "\u25b6 48")
        self.assertEqual(look.badge_text(2), "\u25b6 2")
        self.assertEqual(look.badge_text(1), "")
        self.assertEqual(look.badge_text(0), "")

    def test_details_of_an_animation(self):
        card = Card(**dict(BASE, type="anim", frames=48, fps="ntsc", start=0.0, end=47.0))
        data = {"kind": "character", "character": {"label": "Manny [rig]"}, "members": ["a", "b"],
                "regions": ["Spine"], "frames": 48, "start": 0.0, "end": 47.0, "fps": "ntsc",
                "key_times": [0, 12, 47], "author": "E", "created": "2026-10-03T12:00:00",
                "scene": "C:/x/shot.ma"}
        lines = look.details(card, data)
        self.assertEqual(lines[0], "Manny [rig]")
        self.assertEqual(lines[1], "48 frames (0-47) \u00b7 30 fps \u00b7 3 keys")
        self.assertEqual(lines[2], "2 bones \u00b7 Spine")
        self.assertIn("shot.ma", lines[-1])
        self.assertNotIn("frame ", lines[-1])
        self.assertEqual(lines, ["Manny [rig]", "48 frames (0-47) \u00b7 30 fps \u00b7 3 keys",
                                 "2 bones \u00b7 Spine", "E \u00b7 2026-10-03 12:00", "shot.ma"])

    def test_an_animation_without_key_times_says_no_keys(self):
        card = Card(**dict(BASE, type="anim", frames=48, fps="film", start=0.0, end=47.0))
        data = {"kind": "character", "members": ["a"], "frames": 48, "start": 0.0, "end": 47.0,
                "fps": "film", "key_times": [], "scene": "shot.ma"}
        self.assertEqual(look.details(card, data)[1], "48 frames (0-47) \u00b7 24 fps")

    def test_the_listing_stands_in_for_an_animation_not_read_yet(self):
        card = Card(**dict(BASE, type="anim", frames=48, fps="ntsc", start=12.0, end=59.0))
        self.assertEqual(look.details(card, None),
                         ["Manny [rig]", "48 frames (12-59) \u00b7 30 fps", "2 bones \u00b7 Spine",
                          "E \u00b7 2026-10-03 12:00"])

    def test_an_objects_animation(self):
        card = Card(**dict(BASE, kind="objects", label="objects", count=1, regions=[],
                           type="anim", frames=10, fps="ntsc", start=1.0, end=10.0))
        data = {"kind": "objects", "frames": 10, "start": 1.0, "end": 10.0, "fps": "ntsc",
                "objects": [{"name": "pCube1", "path": "|pCube1", "attrs": {}}],
                "scene": "cubes.ma", "frame": 4}
        self.assertEqual(look.details(card, data),
                         ["Objects", "10 frames (1-10) \u00b7 30 fps", "1 object",
                          "E \u00b7 2026-10-03 12:00", "cubes.ma"])

    def test_one_frame_and_one_key(self):
        card = Card(**dict(BASE, type="anim", frames=1, fps="ntsc", start=5.0, end=5.0))
        data = {"kind": "character", "members": ["a"], "frames": 1, "start": 5.0, "end": 5.0,
                "fps": "ntsc", "key_times": [5.0]}
        self.assertEqual(look.details(card, data)[1], "1 frame (5) \u00b7 30 fps \u00b7 1 key")

    def test_a_pose_card_reads_as_it_did(self):
        card = Card(**dict(BASE, path="p/Fist.pose"))
        data = {"kind": "character", "members": ["a", "b"], "regions": ["Spine"], "frame": 12.0,
                "scene": "shot.ma", "author": "E", "created": "2026-10-03T12:00:00"}
        self.assertEqual(look.details(card, data),
                         ["Manny [rig]", "2 bones \u00b7 Spine", "E \u00b7 2026-10-03 12:00",
                          "frame 12 \u00b7 shot.ma"])

    FULL = {"name": "Walk", "target": "Manny_Rig1", "count": 73, "noun": "controls",
            "layer": "AnimLayer1", "a": 12, "b": 59, "frames": 48, "mode": "replace",
            "worst": (0.003, 0.0), "worst_frame": 31, "notes": ["n1"], "alpha": 1.0,
            "mirror": False}

    def test_anim_status(self):
        text = look.anim_status({"name": "Walk", "target": "Manny_Rig1", "count": 73,
                                 "noun": "controls", "layer": "AnimLayer1", "a": 12, "b": 59,
                                 "frames": 48, "mode": "replace", "worst": (0.003, 0.0),
                                 "worst_frame": 31, "notes": ["n1"], "alpha": 1.0, "mirror": False})
        self.assertEqual(text, "Walk onto Manny_Rig1: 73 controls keyed over frames 12-59 "
                               "(48 frames, replace) on AnimLayer1 - worst 0.003 deg at frame 31 | n1")

    def test_anim_status_mirrored_blended_in_degrees_and_centimetres(self):
        status = dict(self.FULL, mirror=True, alpha=0.5, worst=(0.00071, 0.02), notes=[],
                      layer="", mode="insert")
        self.assertEqual(look.anim_status(status),
                         "Walk mirrored at 50 % onto Manny_Rig1: 73 controls keyed over frames "
                         "12-59 (48 frames, insert) - worst 0.0007 deg / 0.02 cm at frame 31")

    def test_a_worst_too_small_to_say_is_left_out(self):
        status = dict(self.FULL, worst=(0.0004, 0.0001), notes=[])
        self.assertTrue(look.anim_status(status).endswith("(48 frames, replace) on AnimLayer1"))
        status = dict(self.FULL, worst=None, notes=[])
        self.assertTrue(look.anim_status(status).endswith("on AnimLayer1"))
        status = dict(self.FULL, worst_frame=None, notes=[])
        self.assertTrue(look.anim_status(status).endswith("- worst 0.003 deg"))

    def test_nothing_keyed(self):
        status = dict(self.FULL, count=0)
        self.assertEqual(look.anim_status(status), "Walk onto Manny_Rig1: nothing keyed | n1")

    def test_the_paste_modes_read_as_words(self):
        status = dict(self.FULL, mode="replace_all", notes=[], worst=None, layer="")
        self.assertTrue(look.anim_status(status).endswith("(48 frames, replace all)"))

    def test_one_control_on_one_frame(self):
        status = dict(self.FULL, count=1, a=12, b=12, frames=1, notes=[], worst=None, layer="")
        self.assertEqual(look.anim_status(status),
                         "Walk onto Manny_Rig1: 1 control keyed at frame 12 (1 frame, replace)")

    def test_several_targets_and_a_result_tuple(self):
        Result = namedtuple("Result", sorted(self.FULL))
        second = Result(**dict(self.FULL, target="Manny_Rig2", notes=[]))
        text = look.anim_status([dict(self.FULL, notes=[]), second])
        self.assertEqual(text.count(" | "), 1)
        self.assertTrue(text.split(" | ")[1].startswith("Walk onto Manny_Rig2: 73 controls"))
        self.assertEqual(look.anim_status(None), "")
        self.assertEqual(look.anim_status([]), "")


class Boundary(unittest.TestCase):
    """look is stdlib only: the window imports Qt, the geometry must not."""

    def test_importing_it_pulls_in_neither_maya_nor_qt(self):
        script = (
            "import sys\n"
            "from maya_poselib import look\n"
            "leaked = [m for m in sys.modules\n"
            "          if m.startswith('maya.') or m.startswith('PySide')]\n"
            "print(';'.join(sorted(leaked)))\n"
        )
        result = subprocess.run([sys.executable, "-c", script], cwd=PLUGIN,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "",
                         "importing look leaked: " + result.stdout.strip())

    def test_no_maya_qt_or_sibling_import_in_the_source(self):
        with open(os.path.join(PLUGIN, "maya_poselib", "look.py"), encoding="utf-8") as handle:
            source = handle.read()
        self.assertEqual(re.findall(
            r"^\s*(?:import|from)\s+(?:maya|PySide|shiboken)", source, re.MULTILINE), [])
        # it knows no other module of the library either: the window feeds it plain data
        self.assertEqual(re.findall(
            r"^\s*(?:import|from)\s+(?:maya_poselib|\.)", source, re.MULTILINE), [])


if __name__ == "__main__":
    unittest.main()
