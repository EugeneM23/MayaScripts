"""The pose library on disk, the corners `test_poselib_store` leaves out: a drive letter's own slash,
an animation's frames or curves file of the wrong shape or read twice, a write that fails half way
(no `.part` left, the card as it was), a rename to a name the walk would skip, a folder renamed
that is not there or only in case.
"""
import gzip
import json
import os
import shutil
import tempfile
import unittest

from maya_poselib import store


def pose(name="Fist"):
    return {"format": store.FORMAT, "version": store.VERSION, "kind": "character", "name": name,
            "created": "2026-10-02T10:00:00", "author": "A", "character": {"label": "Manny [rig]"},
            "members": ["hand_l"], "regions": ["Hand L"], "bones": {}}


class Patched(unittest.TestCase):

    def patch(self, target, name, value):
        saved = getattr(target, name)
        setattr(target, name, value)
        self.addCleanup(setattr, target, name, saved)


class Slashes(unittest.TestCase):

    def test_back_slashes_become_forward_and_a_trailing_one_goes(self):
        self.assertEqual(store._fwd("C:\\poses\\hands\\"), "C:/poses/hands")
        self.assertEqual(store._fwd("a/b//"), "a/b")

    def test_a_drive_or_filesystem_root_keeps_its_own_slash(self):
        self.assertEqual(store._fwd("C:/"), "C:/")
        self.assertEqual(store._fwd("C:\\"), "C:/")
        self.assertEqual(store._fwd("/"), "/")

    def test_nothing_is_an_empty_path(self):
        self.assertEqual(store._fwd(""), "")
        self.assertEqual(store._fwd(None), "")


class CardFolder(Patched):

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.path = store.write(self.root, "", "Fist", pose())


class FramesAndCurves(CardFolder):

    def gz(self, name, data):
        with gzip.open(self.path + "/" + name, "wt", encoding="utf-8") as handle:
            json.dump(data, handle)

    def test_frames_of_the_wrong_shape_are_refused(self):
        for data in ({"bones": [], "world": "x"}, {"bones": {}, "world": []},
                     {"bones": [], "world": [], "drive": []}, [], {"world": []}):
            self.gz(store.FRAMES_FILE, data)
            with self.assertRaises(ValueError) as caught:
                store.read_frames(self.path)
            self.assertIn("not an animation's frames", str(caught.exception))

    def test_frames_without_a_drive_answer_an_empty_one(self):
        self.gz(store.FRAMES_FILE, {"bones": ["a"], "world": [[[0] * 7]]})
        self.assertEqual(store.read_frames(self.path)["drive"], {})

    def test_frames_read_twice_are_the_one_object(self):
        self.gz(store.FRAMES_FILE, {"bones": ["a"], "world": [[[0] * 7]]})
        self.assertIs(store.read_frames(self.path), store.read_frames(self.path))

    def test_frames_that_are_not_gzip_are_refused(self):
        with open(self.path + "/" + store.FRAMES_FILE, "w") as handle:
            handle.write("plain text")
        with self.assertRaises(ValueError):
            store.read_frames(self.path)

    def test_frames_that_are_missing_are_refused_by_path(self):
        with self.assertRaises(ValueError) as caught:
            store.read_frames(self.path)
        self.assertIn(store.FRAMES_FILE, str(caught.exception))

    def test_curves_read_twice_are_the_one_object(self):
        self.gz(store.CURVES_FILE, {"version": 1, "nodes": []})
        self.assertIs(store.read_curves(self.path), store.read_curves(self.path))

    def test_curves_written_again_are_read_again(self):
        self.gz(store.CURVES_FILE, {"version": 1, "nodes": []})
        first = store.read_curves(self.path)
        self.gz(store.CURVES_FILE, {"version": 1, "nodes": [{"node": "a"}]})
        second = store.read_curves(self.path)
        self.assertIsNot(first, second)
        self.assertEqual(second["nodes"], [{"node": "a"}])

    def test_curves_without_a_nodes_list_are_refused(self):
        self.gz(store.CURVES_FILE, {"version": 1, "nodes": "no"})
        with self.assertRaises(ValueError):
            store.read_curves(self.path)

    def test_curves_that_are_missing_are_refused(self):
        with self.assertRaises(ValueError):
            store.read_curves(self.path)


class FailedWrites(CardFolder):

    def test_a_json_that_cannot_be_written_leaves_the_card_as_it_was_and_no_part_file(self):
        before = store.read(self.path)

        def dump(part, data):
            with open(part, "w") as handle:
                handle.write("{half")
            raise OSError("disk full")

        self.patch(store, "_dump_json", dump)
        with self.assertRaises(OSError):
            store._write_json(self.path, pose("Other"))
        self.assertEqual(sorted(os.listdir(self.path)), [store.POSE_FILE])
        self.assertEqual(store.read(self.path), before)

    def test_an_interrupt_in_the_middle_of_a_write_is_cleaned_up_and_passed_on(self):
        def dump(part, data):
            with open(part, "w") as handle:
                handle.write("{half")
            raise KeyboardInterrupt()

        self.patch(store, "_dump_json", dump)
        with self.assertRaises(KeyboardInterrupt):
            store._write_json(self.path, pose("Other"))
        self.assertEqual(sorted(os.listdir(self.path)), [store.POSE_FILE])

    def test_a_copy_that_fails_leaves_the_target_as_it_was_and_no_part_file(self):
        source = os.path.join(self.root, "new.jpg")
        target = self.path + "/" + store.THUMB_FILE
        with open(source, "wb") as handle:
            handle.write(b"new")
        with open(target, "wb") as handle:
            handle.write(b"old")

        def copy(src, dst):
            with open(dst, "wb") as handle:
                handle.write(b"ne")
            raise OSError("disk full")

        self.patch(shutil, "copy2", copy)
        with self.assertRaises(OSError):
            store.set_thumbnail(self.path, source)
        with open(target, "rb") as handle:
            self.assertEqual(handle.read(), b"old")
        self.assertEqual(sorted(os.listdir(self.path)), [store.POSE_FILE, store.THUMB_FILE])

    def test_a_write_that_fails_before_any_part_file_exists_still_passes_the_error_on(self):
        def dump(part, data):
            raise OSError("no room for even a part file")

        self.patch(store, "_dump_json", dump)
        with self.assertRaises(OSError) as caught:
            store._write_json(self.path, pose("Other"))
        self.assertIn("no room", str(caught.exception))
        self.assertEqual(sorted(os.listdir(self.path)), [store.POSE_FILE])

    def test_a_copy_that_fails_before_any_part_file_exists_still_passes_the_error_on(self):
        with self.assertRaises(OSError):
            store._copy_atomic(os.path.join(self.root, "missing.jpg"),
                               self.path + "/" + store.THUMB_FILE)
        self.assertEqual(sorted(os.listdir(self.path)), [store.POSE_FILE])

    def test_a_copy_that_works_replaces_the_target_whole(self):
        source = os.path.join(self.root, "new.jpg")
        with open(source, "wb") as handle:
            handle.write(b"new")
        store.set_thumbnail(self.path, source)
        with open(self.path + "/" + store.THUMB_FILE, "rb") as handle:
            self.assertEqual(handle.read(), b"new")
        self.assertNotIn(store.THUMB_FILE + ".part", os.listdir(self.path))


class Renames(CardFolder):

    def test_a_card_cannot_be_named_so_the_walk_would_skip_it(self):
        for name in ("_trash", "_Trash old"):
            with self.assertRaises(ValueError) as caught:
                store.rename(self.path, name)
            self.assertIn("a name cannot start with _trash", str(caught.exception))
        self.assertEqual(store.read(self.path)["name"], "Fist")

    def test_a_leading_dot_is_dropped_from_the_new_name_not_refused(self):
        path = store.rename(self.path, ".hidden")
        self.assertTrue(path.endswith("/hidden.pose"))
        self.assertEqual(store.read(path)["name"], "hidden")

    def test_a_folder_that_is_not_there_cannot_be_renamed(self):
        with self.assertRaises(ValueError) as caught:
            store.rename_folder(self.root, "Nope", "Hands")
        self.assertIn("no folder 'Nope'", str(caught.exception))

    def test_the_library_folder_itself_cannot_be_renamed(self):
        for rel in ("", "/", None):
            with self.assertRaises(ValueError):
                store.rename_folder(self.root, rel, "Hands")

    def test_a_nested_folder_stays_under_its_parent(self):
        store.make_folder(self.root, "", "Body")
        store.make_folder(self.root, "Body", "Arms")
        self.assertEqual(store.rename_folder(self.root, "Body/Arms", "Hands"), "Body/Hands")
        self.assertEqual(store.folders(self.root), ["Body", "Body/Hands"])

    def test_a_folder_renamed_onto_another_is_refused(self):
        store.make_folder(self.root, "", "A")
        store.make_folder(self.root, "", "B")
        with self.assertRaises(ValueError) as caught:
            store.rename_folder(self.root, "A", "B")
        self.assertIn("B already exists", str(caught.exception))
        self.assertEqual(store.folders(self.root), ["A", "B"])

    def test_a_folder_renamed_to_its_own_name_is_left_alone(self):
        store.make_folder(self.root, "", "Hands")
        self.assertEqual(store.rename_folder(self.root, "Hands", "Hands"), "Hands")
        self.assertEqual(store.folders(self.root), ["Hands"])

    def test_a_change_of_case_alone_renames_the_folder(self):
        store.make_folder(self.root, "", "Hands")
        self.assertEqual(store.rename_folder(self.root, "Hands", "HANDS"), "HANDS")
        self.assertEqual(store.folders(self.root), ["HANDS"])
        self.assertIn("HANDS", os.listdir(self.root))


if __name__ == "__main__":
    unittest.main()
