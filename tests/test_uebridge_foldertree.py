"""The folder tree of Animation Setup's list (2026-10-23): pure, no Maya."""

import json
import os
import subprocess
import sys
import unittest

import tests  # noqa: F401  (puts SkeldarAnim on sys.path)
from maya_uebridge import foldertree, records

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "SkeldarAnim")


def ue(package, frames=30):
    return records.AnimRecord(package.rsplit("/", 1)[-1], package, "", frames, 1.0, 30.0)


def onfile(path, source="folder", name=None):
    return records.AnimRecord(name or os.path.splitext(os.path.basename(path))[0], path,
                              "", 24, 1.0, 30.0, source, path, "", "fbx")


class FolderOf(unittest.TestCase):

    def test_an_unreal_record_lives_in_its_package_folder(self):
        self.assertEqual(foldertree.folder_of(ue("/Game/Characters/Anims/A_Jump")),
                         "Game/Characters/Anims")
        self.assertEqual(foldertree.folder_of(ue("/Game/A_Jump")), "Game")

    def test_a_file_lives_in_its_folder_under_the_root(self):
        rec = onfile("C:/clips/walks/fast/W.fbx")
        self.assertEqual(foldertree.folder_of(rec, "C:/clips"), "walks/fast")
        self.assertEqual(foldertree.folder_of(rec, "c:\\CLIPS\\"), "walks/fast")

    def test_a_file_in_the_root_itself_is_at_the_top(self):
        self.assertEqual(foldertree.folder_of(onfile("C:/clips/W.fbx"), "C:/clips"), "")

    def test_a_file_outside_its_root_keeps_its_whole_folder(self):
        self.assertEqual(foldertree.folder_of(onfile("D:\\x\\W.fbx"), "C:/clips"), "D:/x")

    def test_a_unity_clip_lives_in_its_model_s_folder(self):
        rec = onfile("C:/proj/Assets/Anim/Hero.fbx", source="unity", name="Run")
        self.assertEqual(foldertree.folder_of(rec, "C:/proj"), "Assets/Anim")


class Rows(unittest.TestCase):

    def setUp(self):
        self.tree = foldertree.build([
            ue("/Game/Chars/Manny/Walk"), ue("/Game/Chars/Manny/Run"),
            ue("/Game/Chars/Manny/sub/Idle"), ue("/Game/Chars/Quinn/Jump"),
            ue("/Game/Root_Anim")])

    def test_counts_take_the_subfolders_in(self):
        game = self.tree.folders["game"]
        self.assertEqual(game.count, 5)
        self.assertEqual(game.folders["chars"].folders["manny"].count, 3)

    def test_only_the_top_level_when_nothing_is_open(self):
        rows = foldertree.rows(self.tree, set())
        self.assertEqual([(r.kind, r.label, r.count, r.opened) for r in rows],
                         [("folder", "Game", 5, False)])

    def test_folders_come_first_then_animations_by_name(self):
        rows = foldertree.rows(self.tree, {"Game", "Game/Chars", "Game/Chars/Manny"})
        self.assertEqual([(r.kind, r.depth, r.label) for r in rows], [
            ("folder", 0, "Game"),
            ("folder", 1, "Chars"),
            ("folder", 2, "Manny"),
            ("folder", 3, "sub"),
            ("anim", 3, "Run"),
            ("anim", 3, "Walk"),
            ("folder", 2, "Quinn"),
            ("anim", 1, "Root_Anim")])
        self.assertIsNone(rows[0].record)
        self.assertEqual(rows[4].record.package, "/Game/Chars/Manny/Run")

    def test_a_chain_of_lone_folders_is_one_row_named_for_the_deepest(self):
        tree = foldertree.build([ue("/Game/A/B/C/Walk"), ue("/Game/A/B/C/Run")])
        rows = foldertree.rows(tree, set())
        self.assertEqual([(r.label, r.path) for r in rows], [("Game/A/B/C", "Game/A/B/C")])
        opened = foldertree.rows(tree, {"Game/A/B/C"})
        self.assertEqual([r.label for r in opened], ["Game/A/B/C", "Run", "Walk"])

    def test_none_opens_every_folder(self):
        rows = foldertree.rows(self.tree, None)
        self.assertEqual(sum(1 for r in rows if r.kind == "anim"), 5)
        self.assertTrue(all(r.opened for r in rows if r.kind == "folder"))

    def test_a_search_is_a_tree_of_the_matches_alone(self):
        shown = records.filter_records([ue("/Game/Chars/Manny/Walk"),
                                        ue("/Game/Chars/Quinn/Jump")], "walk")
        rows = foldertree.rows(foldertree.build(shown), None)
        self.assertEqual([r.label for r in rows], ["Game/Chars/Manny", "Walk"])


class RowText(unittest.TestCase):

    def test_a_folder_row_says_its_state_and_its_count(self):
        closed = foldertree.Row("folder", 1, "Game/Chars", "Chars", None, 12, False)
        opened = closed._replace(opened=True)
        self.assertEqual(foldertree.row_text(closed), "  \u25b8 Chars  (12)")
        self.assertEqual(foldertree.row_text(opened), "  \u25be Chars  (12)")

    def test_an_animation_row_sits_under_its_folder_s_name(self):
        row = foldertree.Row("anim", 1, "", "Walk", ue("/Game/Chars/Walk", 61), 1, False)
        text = foldertree.row_text(row)
        self.assertTrue(text.startswith("    Walk"))
        self.assertTrue(text.endswith("61 fr"))

    def test_an_animation_with_no_length_has_no_length(self):
        rec = records.AnimRecord("Walk", "/Game/Walk", "", None, None, None)
        row = foldertree.Row("anim", 0, "", "Walk", rec, 1, False)
        self.assertEqual(foldertree.row_text(row), "  Walk")


class Memory(unittest.TestCase):

    def test_toggled_opens_and_closes(self):
        self.assertEqual(foldertree.toggled(set(), "A"), {"A"})
        self.assertEqual(foldertree.toggled({"A", "B"}, "A"), {"B"})

    def test_a_place_key_is_its_source_and_place_case_free(self):
        self.assertEqual(foldertree.place_key("folder", "C:\\Clips"), "folder:c:/clips")

    def test_the_memory_round_trips_per_place(self):
        text = foldertree.write_open("", "unreal:atone", {"Game", "Game/Chars"})
        text = foldertree.write_open(text, "folder:c:/x", {"walks"})
        self.assertEqual(foldertree.read_open(text, "unreal:atone"), {"Game", "Game/Chars"})
        self.assertEqual(foldertree.read_open(text, "folder:c:/x"), {"walks"})
        self.assertEqual(foldertree.read_open(text, "unity:none"), set())

    def test_the_memory_keeps_the_last_twenty_places(self):
        text = ""
        for i in range(25):
            text = foldertree.write_open(text, "p%d" % i, {"x"})
        self.assertEqual(len(json.loads(text)), foldertree.MAX_PLACES)
        self.assertEqual(foldertree.read_open(text, "p0"), set())
        self.assertEqual(foldertree.read_open(text, "p24"), {"x"})

    def test_a_broken_memory_reads_empty(self):
        for text in ("{", "42", '{"a": 1}', '[["k", 5]]', None):
            self.assertEqual(foldertree.read_open(text, "k"), set())


class Pure(unittest.TestCase):

    def test_it_imports_nothing_of_maya(self):
        code = ("import sys; sys.path.insert(0, %r); import maya_uebridge.foldertree; "
                "print([m for m in sys.modules if m.startswith('maya.') or m == 'maya'])"
                % PLUGIN)
        out = subprocess.check_output([sys.executable, "-c", code], cwd=PLUGIN)
        self.assertEqual(out.decode().strip(), "[]")


if __name__ == "__main__":
    unittest.main()
