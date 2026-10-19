import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from maya_skillbar import look, store


class Items(unittest.TestCase):

    def test_valid_items(self):
        self.assertTrue(look.valid_item({"kind": "section", "key": "tools"}))
        self.assertTrue(look.valid_item({"kind": "character", "model": "Manny", "char": "rig"}))
        self.assertTrue(look.valid_item({"kind": "script", "lang": "mel", "code": "print 1"}))
        self.assertFalse(look.valid_item({"kind": "script", "lang": "lua", "code": "x"}))
        self.assertFalse(look.valid_item({"kind": "character", "model": "Manny", "char": "x"}))
        self.assertFalse(look.valid_item({"kind": "cmd"}))
        self.assertFalse(look.valid_item({"kind": "nope", "key": "a"}))
        self.assertFalse(look.valid_item("section:tools"))

    def test_clean_item_keeps_only_its_fields(self):
        item = look.clean_item({"kind": "cmd", "key": "tools.aim", "junk": 3, "label": "Aim it"})
        self.assertEqual(item, {"kind": "cmd", "key": "tools.aim", "label": "Aim it"})

    def test_script_item(self):
        item = look.script_item("\n# mirror the pose\ncmds.select()\n", "python")
        self.assertEqual(item["label"], "mirror the pose")
        self.assertEqual(item["lang"], "python")
        self.assertIsNone(look.script_item("   \n"))
        self.assertEqual(look.script_item("x", "basic")["lang"], "python")

    def test_same_item_ignores_labels(self):
        a = {"kind": "cmd", "key": "tools.aim", "label": "A"}
        self.assertTrue(look.same_item(a, {"kind": "cmd", "key": "tools.aim"}))
        self.assertFalse(look.same_item(a, {"kind": "cmd", "key": "tools.knot"}))

    def test_initials(self):
        self.assertEqual(look.initials("Knot Offset"), "KO")
        self.assertEqual(look.initials("SetKey"), "Se")
        self.assertEqual(look.initials(""), "?")


class Model(unittest.TestCase):

    def test_defaults_are_valid_and_round_trip(self):
        data = look.defaults()
        self.assertEqual(data["rows"], 1)
        self.assertEqual(look.page_name(data, 2), "Animate")
        self.assertTrue(all(k.startswith("0.") for k in data["pages"]["2"]["cells"]))
        self.assertEqual(look.page_name(data, 1), "Time")
        self.assertEqual(look.filled(data, 2), look.SLOTS)
        self.assertEqual(look.decode(look.encode(data)), data)
        for n in range(2, 13):
            for item in data["pages"][str(n)]["cells"].values():
                self.assertTrue(look.valid_item(item))

    def test_normalised_drops_what_is_not_ours(self):
        data = look.normalised({"rows": 7, "pages": {
            "1": {"name": "x", "cells": {"0.0": {"kind": "cmd", "key": "a"}}},
            "3": {"name": "  Mine  ", "cells": {"0.1": {"kind": "cmd", "key": "a"},
                                                "9.9": {"kind": "cmd", "key": "b"},
                                                "x": {"kind": "cmd", "key": "c"},
                                                "1.0": {"kind": "bad"}}}}})
        self.assertEqual(data["rows"], 1)
        self.assertNotIn("1", data["pages"])
        self.assertEqual(data["pages"]["3"]["name"], "Mine")
        self.assertEqual(list(data["pages"]["3"]["cells"]), ["0.1"])

    def test_decode_refuses_text_that_is_not_ours(self):
        with self.assertRaises(ValueError):
            look.decode("[1, 2]")
        with self.assertRaises(ValueError):
            look.decode("not json")

    def test_put_take_swap(self):
        data = look.blank()
        a = {"kind": "cmd", "key": "tools.aim"}
        b = {"kind": "section", "key": "tools"}
        data = look.put(data, 4, 0, 2, a)
        self.assertEqual(look.item_at(data, 4, 0, 2), a)
        data = look.put(data, 4, 0, 7, b)
        data = look.swap(data, (4, 0, 2), (4, 0, 7))
        self.assertEqual(look.item_at(data, 4, 0, 2), b)
        self.assertEqual(look.item_at(data, 4, 0, 7), a)
        data = look.swap(data, (4, 0, 2), (5, 0, 0))
        self.assertIsNone(look.item_at(data, 4, 0, 2))
        self.assertEqual(look.item_at(data, 5, 0, 0), b)
        data = look.take(data, 5, 0, 0)
        self.assertEqual(look.filled(data, 5), 0)
        self.assertEqual(look.put(data, 1, 0, 0, a), look.normalised(data))  # F1 holds nothing

    def test_put_does_not_change_its_input(self):
        data = look.blank()
        look.put(data, 2, 0, 0, {"kind": "cmd", "key": "x"})
        self.assertEqual(look.filled(data, 2), 0)

    def test_first_free_and_put_on_page(self):
        data = look.blank()
        item = {"kind": "cmd", "key": "x"}
        data = look.put(data, 2, 0, 0, item)
        self.assertEqual(look.first_free(data, 2, cols=3), (0, 1))
        for c in range(3):
            data = look.put(data, 2, 0, c, item)
        self.assertIsNone(look.first_free(data, 2, cols=3))
        data, place = look.put_on_page(data, 2, item, cols=40)
        self.assertEqual(place, (0, 3))                          # never past SLOTS
        for c in range(look.SLOTS):
            data = look.put(data, 2, 0, c, item)
        self.assertIsNone(look.put_on_page(data, 2, item, cols=40)[1])

    def test_only_ten_cells_in_one_row(self):
        item = {"kind": "cmd", "key": "x"}
        data = look.put(look.blank(), 2, 1, 0, item)
        self.assertEqual(look.filled(data, 2), 0)                  # no second row
        data = look.put(data, 2, 0, look.SLOTS, item)
        self.assertEqual(look.filled(data, 2), 0)                  # no eleventh cell
        self.assertEqual(look.columns(5000, 30), look.SLOTS)

    def test_an_older_file_s_extra_cells_fold_into_the_ten(self):
        a, b, c = ({"kind": "cmd", "key": k} for k in ("a", "b", "c"))
        old = {"rows": 3, "pages": {"2": {"name": "", "cells": {
            "0.0": a, "1.0": b, "2.4": c,
            **dict(("0.%d" % i, {"kind": "cmd", "key": "k%d" % i}) for i in range(2, 30))}}}}
        data = look.normalised(old)
        cells = data["pages"]["2"]["cells"]
        self.assertEqual(len(cells), look.SLOTS)
        self.assertEqual(cells["0.0"], a)
        self.assertEqual(cells["0.1"], b)                          # the first free one
        self.assertEqual(data["rows"], 1)

    def test_rename_clear(self):
        data = look.defaults()
        data = look.rename_page(data, 5, "  Poses  ")
        self.assertEqual(look.tab_text(data, 5), ("F5", "Poses"))
        self.assertEqual(look.filled(look.clear_page(data, 2), 2), 0)


class Geometry(unittest.TestCase):

    def test_cell_size_and_height(self):
        side = look.cell_size(80, 2)
        self.assertAlmostEqual(side, (80 - 12 - 4) / 2.0)
        self.assertEqual(look.cell_size(20, 4), look.CELL_MIN)
        self.assertEqual(look.cell_size(400, 2), look.CELL_MAX)
        self.assertAlmostEqual(look.grid_height(2, side=32), 12 + 64 + 4)

    def test_columns_fit_the_width(self):
        self.assertEqual(look.columns(12 + 10 * 34 + 9 * 4, 34), 10)
        self.assertEqual(look.columns(12 + 10 * 34 + 9 * 4 - 1, 34), 9)
        self.assertEqual(look.columns(5, 34), 1)

    def test_a_row_stands_in_the_middle(self):
        x0 = look.row_left(1000, 10, 50)
        first = look.cell_rect(0, 0, 50, x0=x0)
        last = look.cell_rect(0, 9, 50, x0=x0)
        self.assertAlmostEqual(first[0], 1000 - (last[0] + last[2]))
        self.assertEqual(look.cell_at(first[0] + 25, first[1] + 25, 1, 10, 50, x0=x0), (0, 0))
        self.assertIsNone(look.cell_at(first[0] - 5, first[1] + 25, 1, 10, 50, x0=x0))

    def test_cell_rect_and_cell_at_agree(self):
        for r in range(3):
            for c in range(5):
                x, y, w, h = look.cell_rect(r, c, 30, ui=1.5)
                self.assertEqual(look.cell_at(x + w / 2, y + h / 2, 3, 5, 30, ui=1.5), (r, c))
        x, y, w, h = look.cell_rect(0, 0, 30)
        self.assertIsNone(look.cell_at(x + w + 1, y + 5, 3, 5, 30))      # the gap
        self.assertIsNone(look.cell_at(1, 1, 3, 5, 30))                  # the margin
        self.assertIsNone(look.cell_at(*look.cell_rect(0, 5, 30)[:2], rows=3, cols=5, side=30))

    def test_tabs(self):
        rects = look.tab_rects([("F1", "Time"), ("F2", ""), ("F3", "Rigs")], lambda s: 6 * len(s))
        self.assertEqual(len(rects), 3)
        self.assertEqual(look.tab_at(rects[1][0] + 1, rects), 2)
        self.assertIsNone(look.tab_at(rects[2][0] + rects[2][1] + 50, rects))
        self.assertLess(rects[1][1], rects[0][1])        # no name: narrower

    def test_captions(self):
        self.assertEqual(look.drop_caption("Aim", ("cell", 3, 0, 3)), "Aim · skill F3 · cell 4")
        self.assertEqual(look.drop_caption("Aim", ("tab", 5)), "Aim · onto F5")
        self.assertEqual(look.drop_caption("Aim", None), "Aim")


class Store(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = store.path_in(self.dir)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_first_read_is_the_defaults(self):
        data, note = store.read(self.path)
        self.assertEqual(data, look.defaults())
        self.assertEqual(note, "")

    def test_write_then_read(self):
        data = look.rename_page(look.defaults(), 7, "Mine")
        store.write(self.path, data)
        self.assertTrue(self.path.endswith("SkeldarSkills/skills.json"))
        self.assertEqual(store.read(self.path)[0], data)
        self.assertFalse(os.path.exists(self.path + ".tmp"))

    def test_a_broken_file_is_kept_aside(self):
        os.makedirs(os.path.dirname(self.path))
        with open(self.path, "w") as handle:
            handle.write("{broken")
        data, note = store.read(self.path)
        self.assertEqual(data, look.defaults())
        self.assertIn("kept as", note)
        self.assertFalse(os.path.exists(self.path))
        self.assertEqual(len([n for n in os.listdir(os.path.dirname(self.path)) if "broken" in n]), 1)


class Purity(unittest.TestCase):

    def test_look_and_store_import_with_the_stdlib_alone(self):
        plugin = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "SkeldarAnim")
        code = ("import sys; import maya_skillbar, maya_skillbar.look, maya_skillbar.store; "
                "bad = [m for m in sys.modules if m.split('.')[0] in "
                "('maya', 'PySide6', 'PySide2', 'shiboken6', 'maya_hub', 'maya_hubqt')]; "
                "print(bad); sys.exit(1 if bad else 0)")
        done = subprocess.run([sys.executable, "-c", code], cwd=plugin,
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


if __name__ == "__main__":
    unittest.main()
