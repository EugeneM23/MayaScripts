"""The shipped emoji sheets and index (built by docs/superpowers/plans/make_emoji_sheets.py)."""
import json
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tests  # noqa: F401  (puts SkeldarAnim/ on sys.path)

FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "SkeldarAnim", "assets", "emoji")
GROUPS = ["smileys", "people", "animals", "food", "travel", "activities", "objects", "symbols"]
CELL, COLS = 96, 64


def _index():
    with open(os.path.join(FOLDER, "emoji.json"), encoding="utf-8") as f:
        return json.load(f)


class Shipped(unittest.TestCase):
    def test_the_groups_in_order_and_no_flags(self):
        data = _index()
        self.assertEqual([g[0] for g in data["groups"]], GROUPS)
        self.assertNotIn("\U0001F1F7\U0001F1FA", [r["g"] for r in data["emoji"]])

    def test_the_whole_set_is_there(self):
        data = _index()
        self.assertGreater(len(data["emoji"]), 1300)
        glyphs = set(r["g"] for r in data["emoji"])
        for g in ("\U0001F600", "\U0001F44D", "\U0001F525", "❤️", "\U0001F431"):
            self.assertIn(g, glyphs)
        self.assertGreater(sum(len(r.get("tones") or {}) for r in data["emoji"]), 500)

    def test_russian_names_and_keywords(self):
        cat = next(r for r in _index()["emoji"] if r["g"] == "\U0001F431")
        self.assertIn("кот", (cat["ru"] + " " + " ".join(cat["kw"])).lower())
        self.assertIn("cat", (cat["en"] + " " + " ".join(cat["kw"])).lower())

    def test_every_cell_fits_its_sheet(self):
        from PySide6 import QtGui
        sizes = {}
        for g in GROUPS:
            img = QtGui.QImage(os.path.join(FOLDER, "sheet_%s.webp" % g))
            self.assertFalse(img.isNull(), g)
            self.assertEqual(img.width(), CELL * COLS)
            sizes["sheet_%s.webp" % g] = img.height()
        for r in _index()["emoji"]:
            cells = [(r["sheet"], r["cell"])] + [(t[0], t[1]) for t in (r.get("tones") or {}).values()]
            for sheet, cell in cells:
                self.assertLess((cell // COLS + 1) * CELL, sizes[sheet] + 1, r["g"])

    def test_animations_are_named_where_noto_has_them(self):
        anim = {r["g"]: r["anim"] for r in _index()["emoji"]}
        self.assertEqual(anim["\U0001F602"], "1f602")
        self.assertGreater(sum(1 for v in anim.values() if v), 500)

    def test_the_licence_credits_all_three(self):
        with open(os.path.join(FOLDER, "LICENSE.txt"), encoding="utf-8") as f:
            text = f.read()
        for name in ("Fluent Emoji", "emojibase", "Noto", "CC BY 4.0", "MIT"):
            self.assertIn(name, text)
