"""The pose library on disk (2026-10-02): a card is a folder <Name>.pose holding pose.json and a
thumbnail, a catalog is a plain folder; written atomically, deleted to a trash folder. Stdlib only.

Spec: docs/superpowers/specs/2026-10-02-pose-library-design.md
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from maya_poselib import store

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(store.__file__)))


def pose(name="Fist", label="Manny [rig]", members=("hand_l",), created="2026-10-02T10:00:00"):
    return {"format": store.FORMAT, "version": store.VERSION, "kind": "character", "name": name,
            "created": created, "author": "A", "character": {"label": label},
            "members": list(members), "regions": ["Hand L"], "bones": {}}


class Root(unittest.TestCase):

    def test_default_is_the_plugins_poses_folder(self):
        self.assertEqual(store.default_root("C:/p/SkeldarAnim"), "C:/p/SkeldarAnim/poses")

    def test_the_option_wins_only_when_it_is_a_folder(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        self.assertEqual(store.library_root(tmp, "C:/p"), tmp.replace("\\", "/"))
        self.assertEqual(store.library_root(os.path.join(tmp, "nope"), "C:/p"), "C:/p/poses")
        self.assertEqual(store.library_root("", "C:/p"), "C:/p/poses")


class Names(unittest.TestCase):

    def test_safe_name(self):
        self.assertEqual(store.safe_name('a:b*c?'), "a_b_c_")
        self.assertEqual(store.safe_name("  Fist  pose. "), "Fist pose")
        self.assertEqual(store.safe_name("CON"), "_CON")
        self.assertEqual(store.safe_name(""), "Pose")
        self.assertEqual(len(store.safe_name("x" * 200)), 80)


class Cards(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)

    def test_write_read_list(self):
        path = store.write(self.root, "Hands", "Fist", pose())
        self.assertTrue(path.endswith("Hands/Fist.pose"))
        self.assertEqual(store.read(path)["name"], "Fist")
        found, broken = store.cards(self.root)
        self.assertEqual([c.name for c in found], ["Fist"])
        self.assertEqual(found[0].folder, "Hands")
        self.assertEqual(found[0].label, "Manny [rig]")
        self.assertEqual(found[0].count, 1)
        self.assertEqual(broken, [])
        self.assertEqual(store.folders(self.root), ["Hands"])

    def test_no_part_file_is_left(self):
        path = store.write(self.root, "", "Fist", pose())
        self.assertEqual(sorted(os.listdir(path)), [store.POSE_FILE])

    def test_refuses_to_overwrite_unless_asked(self):
        store.write(self.root, "", "Fist", pose())
        with self.assertRaises(ValueError):
            store.write(self.root, "", "Fist", pose())
        store.write(self.root, "", "Fist", pose(members=("a", "b")), replace=True)
        self.assertEqual(store.cards(self.root)[0][0].count, 2)

    def test_unique_name(self):
        store.write(self.root, "", "Fist", pose())
        self.assertEqual(store.unique_name(self.root, "", "Fist"), "Fist 2")

    def test_a_broken_card_is_reported_not_raised(self):
        bad = os.path.join(self.root, "Bad.pose")
        os.makedirs(bad)
        with open(os.path.join(bad, store.POSE_FILE), "w") as handle:
            handle.write("{nope")
        found, broken = store.cards(self.root)
        self.assertEqual(found, [])
        self.assertEqual(len(broken), 1)

    def test_thumbnail_rename_move_remove(self):
        image = os.path.join(self.root, "x.jpg")
        with open(image, "wb") as handle:
            handle.write(b"\xff\xd8jpg")
        path = store.write(self.root, "", "Fist", pose(), thumbnail=image)
        self.assertTrue(store.cards(self.root)[0][0].thumbnail.endswith(store.THUMB_FILE))
        path = store.rename(path, "Grip")
        self.assertEqual(store.read(path)["name"], "Grip")
        store.make_folder(self.root, "", "Hands")
        path = store.move(path, self.root, "Hands")
        self.assertEqual(store.cards(self.root)[0][0].folder, "Hands")
        trash = os.path.join(self.root, "_trash_test")
        gone = store.remove(path, trash)
        self.assertTrue(os.path.isdir(gone))
        self.assertEqual(store.cards(self.root)[0], [])

    def test_folders_skip_cards_and_hidden(self):
        store.write(self.root, "A/B", "P", pose())
        os.makedirs(os.path.join(self.root, ".git"))
        self.assertEqual(store.folders(self.root), ["A", "A/B"])

    def test_rename_folder(self):
        store.write(self.root, "A", "P", pose())
        self.assertEqual(store.rename_folder(self.root, "A", "Hands"), "Hands")
        self.assertEqual(store.cards(self.root)[0][0].folder, "Hands")


class SearchSort(unittest.TestCase):

    def card(self, name, folder="", label="Manny [rig]", created="2026-10-01T00:00:00"):
        return store.Card("p/" + name, folder, name, created, "A", label, "character", 1, [], "")

    def test_every_term_narrows(self):
        cards = [self.card("Fist", "Hands"), self.card("Run", "Body"), self.card("Fist", "Body",
                                                                                  "Creep [rig]")]
        self.assertEqual(len(store.filter_cards(cards, "fist")), 2)
        self.assertEqual(len(store.filter_cards(cards, "fist creep")), 1)
        self.assertEqual(len(store.filter_cards(cards, "")), 3)

    def test_sorts(self):
        a = self.card("b", created="2026-10-01T00:00:00")
        b = self.card("A", created="2026-10-03T00:00:00", label="Creep [rig]")
        self.assertEqual([c.name for c in store.sort_cards([a, b], "name")], ["A", "b"])
        self.assertEqual([c.name for c in store.sort_cards([a, b], "newest")], ["A", "b"])
        self.assertEqual([c.name for c in store.sort_cards([a, b], "character")], ["A", "b"])


class Invariants(unittest.TestCase):
    """What the store keeps beyond the happy path: it never lists what it cannot find again, never
    loses a card to a collision, and a failed write leaves nothing behind."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)
        self.trash = tempfile.mkdtemp()     # outside the library, as the real one is
        self.addCleanup(shutil.rmtree, self.trash)

    def test_safe_name_edges(self):
        self.assertEqual(store.safe_name("a\x01b"), "a_b")
        self.assertEqual(store.safe_name("nul.txt"), "_nul.txt")
        self.assertEqual(store.safe_name("...", fallback="Folder"), "Folder")
        self.assertEqual(store.safe_name("Rock'n'Roll"), "Rock'n'Roll")
        self.assertLessEqual(len(store.safe_name("CON." + "y" * 200)), 80)

    def test_unique_name_counts_on(self):
        for name in ("Fist", "Fist 2"):
            store.write(self.root, "", name, pose())
        self.assertEqual(store.unique_name(self.root, "", "Fist"), "Fist 3")
        self.assertEqual(store.unique_name(self.root, "", "Open"), "Open")

    def test_write_leaves_the_callers_dict_alone(self):
        data = pose(name="typed")
        store.write(self.root, "", "Fist", data)
        self.assertEqual(data["name"], "typed")

    def test_write_stamps_a_missing_format(self):
        path = store.write(self.root, "", "Bare", {"kind": "character", "members": []})
        self.assertEqual(store.read(path)["format"], store.FORMAT)
        self.assertEqual(len(store.cards(self.root)[0]), 1)

    def test_a_failed_write_leaves_no_card(self):
        with self.assertRaises(OSError):
            store.write(self.root, "A", "Fist", pose(),
                        thumbnail=os.path.join(self.root, "missing.jpg"))
        self.assertEqual(os.listdir(os.path.join(self.root, "A")), [])
        self.assertEqual(store.cards(self.root), ([], []))

    def test_a_failed_replace_keeps_the_old_card(self):
        path = store.write(self.root, "", "Fist", pose(members=("a", "b")))
        with self.assertRaises(OSError):
            store.write(self.root, "", "Fist", pose(), replace=True,
                        thumbnail=os.path.join(self.root, "missing.jpg"))
        self.assertEqual(len(store.read(path)["members"]), 2)

    def test_replace_keeps_the_thumbnail_unless_a_new_one_comes(self):
        image = os.path.join(self.root, "x.jpg")
        with open(image, "wb") as handle:
            handle.write(b"\xff\xd8one")
        path = store.write(self.root, "", "Fist", pose(), thumbnail=image)
        store.write(self.root, "", "Fist", pose(), replace=True)
        self.assertTrue(store.cards(self.root)[0][0].thumbnail)
        with open(image, "wb") as handle:
            handle.write(b"\xff\xd8two")
        store.set_thumbnail(path, image)
        with open(path + "/" + store.THUMB_FILE, "rb") as handle:
            self.assertEqual(handle.read(), b"\xff\xd8two")
        self.assertEqual(sorted(os.listdir(path)), [store.POSE_FILE, store.THUMB_FILE])

    def test_names_the_walk_would_hide_are_refused(self):
        with self.assertRaises(ValueError):
            store.write(self.root, "", "_trash me", pose())
        with self.assertRaises(ValueError):
            store.write(self.root, "_trash", "Fist", pose())
        with self.assertRaises(ValueError):
            store.make_folder(self.root, "", "_Trash")
        with self.assertRaises(ValueError):
            store.make_folder(self.root, "", "Hands.pose")
        store.make_folder(self.root, "", "Hands")
        with self.assertRaises(ValueError):
            store.rename_folder(self.root, "Hands", "_trash2")

    def test_a_folder_cannot_leave_the_library(self):
        for bad in ("..", "A/../..", "C:/x", ".git"):
            with self.assertRaises(ValueError):
                store.write(self.root, bad, "Fist", pose())
        with self.assertRaises(ValueError):
            store.cards(self.root, "..")

    def test_make_and_rename_folder_refuse_a_taken_name(self):
        self.assertEqual(store.make_folder(self.root, "", "Hands"), "Hands")
        self.assertEqual(store.make_folder(self.root, "Hands", "Left"), "Hands/Left")
        with self.assertRaises(ValueError):
            store.make_folder(self.root, "", "Hands")
        with self.assertRaises(ValueError):
            store.make_folder(self.root, "Nope", "Left")
        store.make_folder(self.root, "", "Body")
        with self.assertRaises(ValueError):
            store.rename_folder(self.root, "Body", "Hands")
        with self.assertRaises(ValueError):
            store.rename_folder(self.root, "", "Anything")
        self.assertEqual(store.rename_folder(self.root, "Hands/Left", "L"), "Hands/L")

    def test_rename_a_card_refuses_a_taken_name_and_keeps_the_old_one(self):
        first = store.write(self.root, "", "Fist", pose())
        store.write(self.root, "", "Open", pose(name="Open"))
        with self.assertRaises(ValueError):
            store.rename(first, "Open")
        self.assertEqual(store.read(first)["name"], "Fist")
        self.assertEqual(store.rename(first, "Fist"), first)

    def test_rename_an_unreadable_card_moves_nothing(self):
        bad = os.path.join(self.root, "Bad.pose")
        os.makedirs(bad)
        with self.assertRaises(ValueError):
            store.rename(bad, "Good")
        self.assertTrue(os.path.isdir(bad))

    def test_move_refuses_a_collision_and_a_missing_folder(self):
        first = store.write(self.root, "A", "Fist", pose())
        store.write(self.root, "B", "Fist", pose())
        with self.assertRaises(ValueError):
            store.move(first, self.root, "B")
        with self.assertRaises(ValueError):
            store.move(first, self.root, "Nowhere")
        self.assertEqual(store.move(first, self.root, "A"), first)
        self.assertTrue(os.path.isdir(first))
        top = store.move(first, self.root, "")
        self.assertEqual(top, self.root.replace("\\", "/") + "/Fist.pose")

    def test_remove_keeps_two_of_one_name(self):
        trash = store.trash_dir(self.trash)
        self.assertTrue(trash.endswith("/SkeldarPoses_trash"))
        gone = []
        for _ in range(2):
            path = store.write(self.root, "", "Fist", pose())
            gone.append(store.remove(path, trash))
        self.assertEqual(len(set(gone)), 2)
        self.assertTrue(all(os.path.isdir(path) and path.endswith(".pose") for path in gone))
        self.assertFalse(os.path.exists(self.root + "/Fist.pose"))

    def test_remove_takes_a_catalog_with_its_cards(self):
        store.write(self.root, "A", "Fist", pose())
        gone = store.remove(self.root + "/A", store.trash_dir(self.trash))
        self.assertTrue(os.path.isdir(gone + "/Fist.pose"))
        self.assertEqual(store.folders(self.root), [])

    def test_wrong_files_are_broken_and_read_raises(self):
        wrong = os.path.join(self.root, "Wrong.pose")
        os.makedirs(wrong)
        with open(os.path.join(wrong, store.POSE_FILE), "w") as handle:
            json.dump({"format": "something.else", "name": "Wrong"}, handle)
        empty = os.path.join(self.root, "Empty.pose")
        os.makedirs(empty)
        found, broken = store.cards(self.root)
        self.assertEqual(found, [])
        self.assertEqual(len(broken), 2)
        for path in (wrong, empty):
            with self.assertRaises(ValueError):
                store.read(path)

    def test_a_card_is_found_by_its_folder_name_and_non_ascii_survives(self):
        path = store.write(self.root, "", "Кулак", pose(name="Кулак"))
        os.rename(path, self.root + "/Fist.pose")
        card = store.cards(self.root)[0][0]
        self.assertEqual(card.name, "Fist")
        self.assertEqual(store.read(card.path)["name"], "Кулак")

    def test_cards_can_stay_in_one_folder(self):
        store.write(self.root, "", "Top", pose())
        store.write(self.root, "A", "Fist", pose())
        store.write(self.root, "A/B", "Deep", pose())
        names = lambda found: [c.name for c in found[0]]
        self.assertEqual(names(store.cards(self.root)), ["Top", "Fist", "Deep"])
        self.assertEqual(names(store.cards(self.root, "A")), ["Fist", "Deep"])
        self.assertEqual(names(store.cards(self.root, "A", recursive=False)), ["Fist"])
        self.assertEqual(store.cards(self.root, "Nowhere"), ([], []))
        self.assertEqual(store.cards(self.root + "/nowhere"), ([], []))

    def test_the_card_reads_its_kind(self):
        objects = {"format": store.FORMAT, "version": 1, "kind": "objects", "created": "2026-10-02",
                   "author": "B", "objects": [{"name": "a"}, {"name": "b"}, {"name": "c"}]}
        store.write(self.root, "", "Cubes", objects)
        card = store.cards(self.root)[0][0]
        self.assertEqual((card.kind, card.label, card.count, card.author, card.created),
                         ("objects", "objects", 3, "B", "2026-10-02"))
        self.assertEqual(card.regions, [])
        self.assertEqual(card.thumbnail, "")

    def test_folders_keep_a_catalog_with_its_children(self):
        for folder in ("A", "a b", "A/x", "B"):
            os.makedirs(os.path.join(self.root, folder))
        self.assertEqual(store.folders(self.root), ["A", "A/x", "a b", "B"])
        self.assertEqual(store.folders(self.root + "/nowhere"), [])


def card_named(name):
    return store.Card("p/" + name, "", name, "2026-10-01T00:00:00", "A", "Manny [rig]",
                      "character", 1, [], "")


class SortErrors(unittest.TestCase):

    def test_an_unknown_sort_is_refused_and_newest_ties_fall_to_the_name(self):
        a, b = card_named("b"), card_named("A")
        self.assertEqual([c.name for c in store.sort_cards([a, b], "newest")], ["A", "b"])
        with self.assertRaises(ValueError):
            store.sort_cards([a], "size")

    def test_the_input_is_not_reordered(self):
        cards = [card_named("b"), card_named("A")]
        store.sort_cards(cards, "name")
        self.assertEqual([c.name for c in cards], ["b", "A"])
        self.assertIsNot(store.filter_cards(cards, ""), cards)


class Purity(unittest.TestCase):

    def test_stdlib_only(self):
        code = ("import sys; sys.path.insert(0, %r); import maya_poselib.store; "
                "bad = [m for m in sys.modules if m.startswith(('maya.', 'PySide'))]; "
                "print(bad); sys.exit(1 if bad else 0)") % PLUGIN
        result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
