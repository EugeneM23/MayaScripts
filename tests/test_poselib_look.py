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

# store.Card's fields (Task 1); look must not import store, so the test builds its own
Card = namedtuple("Card", "path folder name created author label kind count regions thumbnail")


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

    def test_the_row_is_spread_to_fill_the_width(self):
        _cols, rects, _height = look.grid(1000, 7, 112)
        self.assertEqual(rects[0][0], 0)
        self.assertEqual(rects[-1][0] + rects[-1][2], 1000)
        gaps = [b[0] - (a[0] + a[2]) for a, b in zip(rects, rects[1:])]
        self.assertEqual(len(set(gaps)), 1, gaps)
        self.assertGreater(gaps[0], look.GAP)

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
        for scale in (1.0, 1.5):
            gap = int(round(look.GAP * scale))
            for width in range(150, 1500, 37):
                _cols, rects, _height = look.grid(width, 12, 112, scale)
                for a, b in zip(rects, rects[1:]):
                    if b[1] == a[1]:
                        self.assertGreaterEqual(b[0] - (a[0] + a[2]), gap, (scale, width))


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
