"""maya_stashstore: the Stash folder's rules, as data - no Maya.

Spec: docs/superpowers/specs/2026-10-09-stash-design.md
"""

import os
import subprocess
import sys
import time
import unittest

import maya_stashstore as store

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.normpath(os.path.join(HERE, "..", "SkeldarAnim"))


class Kinds(unittest.TestCase):

    def test_scenes_and_fbx_are_items(self):
        for name in ("shot.ma", "shot.MB", "clip.fbx", "Rig draft.ma"):
            self.assertTrue(store.is_item(name), name)

    def test_anything_else_is_not(self):
        for name in ("notes.txt", "shot.ma.part", ".hidden.ma", "", "x.tga",
                     "folder"):
            self.assertFalse(store.is_item(name), name)

    def test_kind_of(self):
        self.assertEqual(store.kind_of("a.ma"), "scene")
        self.assertEqual(store.kind_of("a.mb"), "scene")
        self.assertEqual(store.kind_of("a.fbx"), "fbx")
        self.assertIsNone(store.kind_of("a.txt"))


class UniqueName(unittest.TestCase):

    def test_a_free_name_is_kept(self):
        self.assertEqual(store.unique_name("shot.ma", ["other.ma"]), "shot.ma")

    def test_a_taken_name_gets_two(self):
        self.assertEqual(store.unique_name("shot.ma", ["shot.ma"]),
                         "shot (2).ma")

    def test_the_next_free_number(self):
        taken = ["shot.ma", "shot (2).ma", "shot (3).ma"]
        self.assertEqual(store.unique_name("shot.ma", taken), "shot (4).ma")

    def test_case_does_not_count(self):
        self.assertEqual(store.unique_name("Shot.MA", ["shot.ma"]),
                         "Shot (2).MA")

    def test_the_extension_stays_last(self):
        self.assertEqual(store.unique_name("clip.fbx", ["clip.fbx"]),
                         "clip (2).fbx")


class DraftName(unittest.TestCase):

    def test_a_scene_takes_its_stem_and_the_time(self):
        now = 1786000000.0
        stamp = time.strftime("%H%M", time.localtime(now))
        self.assertEqual(store.draft_name("C:/x/shot.ma", now),
                         "shot_" + stamp + ".ma")

    def test_an_untitled_scene(self):
        now = 1786000000.0
        stamp = time.strftime("%H%M", time.localtime(now))
        self.assertEqual(store.draft_name("", now), "untitled_" + stamp + ".ma")

    def test_a_binary_scene_keeps_its_type(self):
        now = 1786000000.0
        stamp = time.strftime("%H%M", time.localtime(now))
        self.assertEqual(store.draft_name("C:/x/rig.mb", now),
                         "rig_" + stamp + ".mb")


class SelectionNames(unittest.TestCase):

    def test_a_namespace_and_the_path_go(self):
        self.assertEqual(store.short_name("|Manny_Rig:Main|hand_r"), "hand_r")
        self.assertEqual(store.short_name("Manny_Rig:Main"), "Main")

    def test_a_plain_name_stays(self):
        self.assertEqual(store.short_name("|cube1"), "cube1")

    def test_one_object_names_the_file_after_it(self):
        now = 1786000000.0
        stamp = time.strftime("%H%M", time.localtime(now))
        self.assertEqual(store.selection_name(["|Rig:Main"], now),
                         "Main_" + stamp + ".fbx")

    def test_several_objects_are_called_selection(self):
        now = 1786000000.0
        stamp = time.strftime("%H%M", time.localtime(now))
        self.assertEqual(store.selection_name(["|a", "|b"], now),
                         "selection_" + stamp + ".fbx")


class Listing(unittest.TestCase):

    def test_items_only_newest_first(self):
        listing = [("old.ma", 10, 100.0), ("notes.txt", 5, 999.0),
                   ("new.fbx", 20, 300.0), ("mid.mb", 30, 200.0)]
        names = [e["name"] for e in store.entries(listing)]
        self.assertEqual(names, ["new.fbx", "mid.mb", "old.ma"])

    def test_the_kind_and_size_are_carried(self):
        (entry,) = store.entries([("clip.fbx", 2048, 5.0)])
        self.assertEqual(entry, {"name": "clip.fbx", "kind": "fbx",
                                 "bytes": 2048, "mtime": 5.0})

    def test_equal_times_keep_name_order(self):
        listing = [("b.ma", 1, 7.0), ("a.ma", 1, 7.0)]
        names = [e["name"] for e in store.entries(listing)]
        self.assertEqual(names, ["a.ma", "b.ma"])

    def test_an_empty_listing(self):
        self.assertEqual(store.entries([]), [])


class Text(unittest.TestCase):

    def test_a_row_has_name_kind_size_and_time(self):
        now = 1786000000.0
        entry = {"name": "shot.ma", "kind": "scene", "bytes": 12 * 1048576,
                 "mtime": now}
        text = store.row_text(entry, now)
        self.assertTrue(text.startswith("shot.ma"))
        self.assertIn("scene", text)
        self.assertIn("12.0 MB", text)

    def test_a_long_name_is_cut_with_dots(self):
        entry = {"name": "x" * 80 + ".ma", "kind": "scene", "bytes": 1,
                 "mtime": 0.0}
        text = store.row_text(entry, 0.0)
        self.assertIn("..", text)
        self.assertLessEqual(len(text.split(" ")[0]), store.NAME_WIDTH)

    def test_the_subtitle_counts_and_says_nothing_leaves(self):
        self.assertEqual(store.subtitle(0),
                         "0 files on this machine - nothing is sent")
        self.assertEqual(store.subtitle(1),
                         "1 file on this machine - nothing is sent")
        self.assertEqual(store.subtitle(3),
                         "3 files on this machine - nothing is sent")

    def test_several_picked(self):
        self.assertIn("3 files picked", store.picked_text(3))

    def test_the_delete_question_names_them_and_says_gone(self):
        text = store.delete_question(["a.ma", "b.fbx"])
        self.assertIn("Delete 2 files", text)
        self.assertIn("  a.ma", text)
        self.assertIn("  b.fbx", text)
        self.assertIn("cannot be undone", text)

    def test_the_delete_question_counts_the_rest(self):
        names = ["f%d.ma" % i for i in range(8)]
        text = store.delete_question(names)
        self.assertIn("and 3 more", text)
        self.assertNotIn("f7.ma", text)

    def test_a_single_file_question(self):
        self.assertIn("Delete 1 file ", store.delete_question(["a.ma"]))

    def test_the_open_scene_refusal_names_it(self):
        text = store.open_refusal("shot.ma")
        self.assertIn("shot.ma", text)
        self.assertIn("nothing deleted", text)


class Purity(unittest.TestCase):

    def test_no_maya_is_imported(self):
        code = ("import sys; sys.path.insert(0, {0!r}); "
                "import maya_stashstore; "
                "print('maya' in sys.modules or 'maya.cmds' in sys.modules)"
                .format(PLUGIN))
        out = subprocess.check_output([sys.executable, "-c", code])
        self.assertEqual(out.decode().strip(), "False")


if __name__ == "__main__":
    unittest.main()
