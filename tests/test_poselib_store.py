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

    def test_the_install_s_manifest_is_no_card_and_no_folder(self):
        """`poses/.shipped.json` (the install's record of the shipped cards, 2026-10-03) lives in
        the library folder and is never listed - as a file, or should a folder carry its name."""
        store.write(self.root, "", "Fist", pose())
        with open(os.path.join(self.root, ".shipped.json"), "w") as handle:
            handle.write("{}")
        self.assertEqual([c.name for c in store.cards(self.root)[0]], ["Fist"])
        self.assertEqual(store.folders(self.root), [])
        os.remove(os.path.join(self.root, ".shipped.json"))
        os.makedirs(os.path.join(self.root, ".shipped.json"))
        self.assertEqual(store.folders(self.root), [])
        self.assertEqual(store.cards(self.root)[1], [])

    def test_rename_folder(self):
        store.write(self.root, "A", "P", pose())
        self.assertEqual(store.rename_folder(self.root, "A", "Hands"), "Hands")
        self.assertEqual(store.cards(self.root)[0][0].folder, "Hands")


class SearchSort(unittest.TestCase):
    """The fixtures are built so that every rule has a card only it can decide: a search term that
    only the folder (or only the label, or only the name) holds, and sorts whose three orders
    all differ - so a key that is ignored, or compared case-sensitively, changes an answer."""

    def card(self, name, folder="", label="Manny [rig]", created="2026-10-01T00:00:00",
             kind="character"):
        return store.Card("p/" + name, folder, name, created, "A", label, kind, 1, [], "")

    def names(self, found):
        return [c.name for c in found]

    def test_every_term_narrows(self):
        cards = [self.card("Fist", "Hands"), self.card("Run", "Body"), self.card("Fist", "Body",
                                                                                  "Creep [rig]")]
        self.assertEqual(len(store.filter_cards(cards, "fist")), 2)
        self.assertEqual(len(store.filter_cards(cards, "fist creep")), 1)
        self.assertEqual(len(store.filter_cards(cards, "")), 3)

    def test_a_term_is_found_in_the_name_the_folder_or_the_label(self):
        fist = self.card("Fist", "Hands", "Manny [rig]")
        run = self.card("Run", "Body/Arms", "Creep [rig]")
        cards = [fist, run]
        # each term below is held by ONE field of ONE card and by no other field of either card
        self.assertEqual(store.filter_cards(cards, "run"), [run])        # the name
        self.assertEqual(store.filter_cards(cards, "hands"), [fist])     # the folder
        self.assertEqual(store.filter_cards(cards, "body"), [run])       # the folder (a nested one)
        self.assertEqual(store.filter_cards(cards, "arms"), [run])       # ... at any depth
        self.assertEqual(store.filter_cards(cards, "creep"), [run])      # the label
        self.assertEqual(store.filter_cards(cards, "manny"), [fist])     # the label
        # terms from different fields of one card all have to hold
        self.assertEqual(store.filter_cards(cards, "run body creep"), [run])
        self.assertEqual(store.filter_cards(cards, "run hands"), [])
        # no field holds it ("pose" is a pose card's type word since 2026-10-03, so not that)
        self.assertEqual(store.filter_cards(cards, "walk"), [])

    def test_search_ignores_case_and_extra_whitespace(self):
        cards = [self.card("Fist", "Hands"), self.card("Run", "Body")]
        self.assertEqual(self.names(store.filter_cards(cards, "  BODY  ")), ["Run"])
        self.assertEqual(self.names(store.filter_cards(cards, "FIST\thands")), ["Fist"])
        self.assertEqual(self.names(store.filter_cards(cards, "   ")), ["Fist", "Run"])

    def test_a_term_does_not_span_two_fields(self):
        # "Fist" + "Hands" must not read as the one word "fisthands": the fields are separate
        cards = [self.card("Fist", "Hands")]
        self.assertEqual(store.filter_cards(cards, "sthan"), [])
        self.assertEqual(store.filter_cards(cards, "fist hands"), cards)

    def test_the_three_sorts_give_three_different_orders(self):
        a = self.card("a", label="Orc D [rig]", created="2026-10-02T09:00:00")
        big_b = self.card("B", label="Creep [rig]", created="2026-10-03T09:00:00")
        c = self.card("c", label="objects", created="2026-10-02T12:00:00", kind="objects")
        big_d = self.card("D", label="Manny [rig]", created="2026-10-01T09:00:00")
        cards = [a, big_b, c, big_d]
        # name: by the lower-cased name, so "a" < "B" < "c" < "D" (a case-sensitive sort would
        # put B and D first)
        self.assertEqual(self.names(store.sort_cards(cards, "name")), ["a", "B", "c", "D"])
        # newest: the latest `created` first - no relation to the names' order
        self.assertEqual(self.names(store.sort_cards(cards, "newest")), ["B", "c", "a", "D"])
        # character: by the label, lower-cased ("creep" < "manny" < "objects" < "orc d"; a
        # case-sensitive sort would put "objects" last) - neither the name order nor the newest
        self.assertEqual(self.names(store.sort_cards(cards, "character")), ["B", "D", "c", "a"])
        # whatever order the cards come in, the answer is the same
        for key in store.SORTS:
            expected = self.names(store.sort_cards(cards, key))
            self.assertEqual(self.names(store.sort_cards(list(reversed(cards)), key)), expected)

    def test_cards_of_one_character_are_ordered_by_name(self):
        # two Manny cards, handed over in the order the name must undo; "B" < "a" only if the
        # name is compared case-sensitively
        big_b = self.card("B", label="Manny [rig]")
        a = self.card("a", label="Manny [rig]")
        creep = self.card("z", label="Creep [rig]")
        self.assertEqual(self.names(store.sort_cards([big_b, a, creep], "character")),
                         ["z", "a", "B"])

    def test_newest_cards_of_one_moment_are_ordered_by_name(self):
        big_b, a = self.card("B"), self.card("a")           # one `created`
        self.assertEqual(self.names(store.sort_cards([big_b, a], "newest")), ["a", "B"])
        later = self.card("z", created="2026-10-02T00:00:00")
        self.assertEqual(self.names(store.sort_cards([big_b, a, later], "newest")),
                         ["z", "a", "B"])


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


class AnimCards(unittest.TestCase):
    """2026-10-03, animation cards: a folder <Name>.anim holding anim.json (the header, read by
    every listing), frames.json.gz (the per-frame data, read by Apply only), the still and the
    preview sheet - in the same library, under the same rules as a pose card."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)
        self.trash = tempfile.mkdtemp()     # outside the library, as the real one is
        self.addCleanup(shutil.rmtree, self.trash)
        self.images = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.images)

    def image(self, data=b"\xff\xd8jpg"):
        """A small image file outside the library; its path."""
        path = os.path.join(self.images, "%d.jpg" % len(os.listdir(self.images)))
        with open(path, "wb") as handle:
            handle.write(data)
        return path

    def header(self, **extra):
        data = {"format": store.ANIM_FORMAT, "version": 1, "kind": "character", "name": "Walk",
                "created": "2026-10-03T12:00:00", "author": "E", "fps": "ntsc",
                "start": 0.0, "end": 47.0, "frames": 48, "character": {"label": "Manny [rig]"},
                "members": ["pelvis", "hand_l"], "regions": ["Pelvis"], "bones": {},
                "preview": {"frames": 48, "columns": 7, "size": 320, "step": 1}}
        data.update(extra)
        return data

    def frames(self, count=48):
        return {"bones": ["root"], "world": [[0, 0, 0, 1, 0, 0, 0]] * count, "drive": {}}

    def test_an_animation_is_a_dot_anim_card_with_its_files(self):
        path = store.write(self.root, "", "Walk", self.header(), frames=self.frames(),
                           thumbnail=self.image(), preview=self.image())
        self.assertTrue(path.endswith("/Walk.anim"))
        self.assertEqual(sorted(os.listdir(path)), sorted(
            [store.ANIM_FILE, store.FRAMES_FILE, store.THUMB_FILE, store.PREVIEW_FILE]))
        card = store.cards(self.root)[0][0]
        self.assertEqual((card.type, card.frames, card.fps, card.start, card.end),
                         ("anim", 48, "ntsc", 0.0, 47.0))
        self.assertTrue(card.preview.endswith("/Walk.anim/preview.jpg"))
        self.assertTrue(card.thumbnail.endswith("/Walk.anim/thumbnail.jpg"))
        self.assertEqual(card.label, "Manny [rig]")
        self.assertEqual(card.count, 2)
        self.assertEqual(card.name, "Walk")

    def test_the_suffix_answers_the_type(self):
        self.assertEqual(store.CARD_SUFFIXES, (".pose", ".anim"))
        self.assertEqual(store.card_suffix("C:/lib/Walk.anim"), ".anim")
        self.assertEqual(store.card_suffix("C:/lib/Walk.ANIM/"), ".anim")
        self.assertEqual(store.card_suffix("C:\\lib\\Fist.pose"), ".pose")
        self.assertTrue(store.is_anim("C:/lib/Walk.anim"))
        self.assertFalse(store.is_anim("C:/lib/Fist.pose"))

    def test_read_answers_the_header_and_read_frames_the_data(self):
        path = store.write(self.root, "", "Walk", self.header(), frames=self.frames())
        self.assertEqual(store.read(path)["frames"], 48)
        self.assertEqual(store.read(path)["format"], store.ANIM_FORMAT)
        self.assertNotIn("world", store.read(path))
        data = store.read_frames(path)
        self.assertEqual(len(data["world"]), 48)
        self.assertEqual(data["bones"], ["root"])
        self.assertEqual(data["drive"], {})

    def test_the_frames_file_is_compact_gzip_json(self):
        import gzip
        path = store.write(self.root, "", "Walk", self.header(), frames=self.frames(2))
        with gzip.open(path + "/" + store.FRAMES_FILE, "rt", encoding="utf-8") as handle:
            text = handle.read()
        self.assertEqual(json.loads(text), self.frames(2))
        self.assertNotIn(", ", text)
        self.assertNotIn(": ", text)

    def test_read_frames_is_cached_until_the_file_changes(self):
        path = store.write(self.root, "", "Walk", self.header(), frames=self.frames())
        first = store.read_frames(path)
        self.assertIs(store.read_frames(path), first)
        store.write(self.root, "", "Walk", self.header(frames=10), frames=self.frames(10),
                    replace=True)
        self.assertEqual(len(store.read_frames(path)["world"]), 10)

    def test_frames_without_a_drive_answer_an_empty_one(self):
        """A skeleton's clip carries no drive; the answer holds `bones`, `world` and `drive`
        whatever the file wrote, so a reader never asks whether the key is there."""
        path = store.write(self.root, "", "Walk", self.header(),
                           frames={"bones": ["root"], "world": [[0, 0, 0, 1, 0, 0, 0]]})
        data = store.read_frames(path)
        self.assertEqual(data["drive"], {})
        self.assertIs(store.read_frames(path), data)          # cached as it was answered

    def test_read_frames_refuses_a_missing_or_broken_file(self):
        path = store.write(self.root, "", "Door", self.header(kind="objects", objects=[]))
        with self.assertRaises(ValueError):
            store.read_frames(path)
        with open(path + "/" + store.FRAMES_FILE, "wb") as handle:
            handle.write(b"not gzip")
        with self.assertRaises(ValueError):
            store.read_frames(path)

    def test_a_pose_card_reads_as_a_pose(self):
        store.write(self.root, "", "Fist", pose())
        card = store.cards(self.root)[0][0]
        self.assertEqual((card.type, card.frames, card.preview, card.fps, card.start, card.end),
                         ("pose", 0, "", "", 0.0, 0.0))

    def test_a_pose_card_takes_no_frames_and_no_preview(self):
        with self.assertRaises(ValueError):
            store.write(self.root, "", "Fist", pose(), frames=self.frames())
        with self.assertRaises(ValueError):
            store.write(self.root, "", "Fist", pose(), preview=self.image())
        self.assertEqual(os.listdir(self.root), [])
        path = store.write(self.root, "", "Fist", pose())
        with self.assertRaises(ValueError):
            store.set_preview(path, self.image())
        self.assertEqual(os.listdir(path), [store.POSE_FILE])

    def test_set_preview_replaces_the_sheet(self):
        path = store.write(self.root, "", "Walk", self.header(), frames=self.frames(),
                           preview=self.image(b"\xff\xd8one"))
        store.set_preview(path, self.image(b"\xff\xd8two"))
        with open(path + "/" + store.PREVIEW_FILE, "rb") as handle:
            self.assertEqual(handle.read(), b"\xff\xd8two")

    def test_a_name_is_free_only_when_neither_type_holds_it(self):
        store.write(self.root, "", "Walk", self.header(), frames=self.frames())
        self.assertEqual(store.unique_name(self.root, "", "Walk"), "Walk 2")
        with self.assertRaises(ValueError):
            store.write(self.root, "", "Walk", pose())
        with self.assertRaises(ValueError):
            store.write(self.root, "", "Walk", pose(), replace=True)
        store.write(self.root, "", "Fist", pose())
        self.assertEqual(store.unique_name(self.root, "", "Fist"), "Fist 2")
        with self.assertRaises(ValueError):
            store.write(self.root, "", "Fist", self.header(), frames=self.frames())
        self.assertEqual(sorted(os.listdir(self.root)), ["Fist.pose", "Walk.anim"])

    def test_a_card_beside_the_other_type_of_its_name_is_still_replaced(self):
        """The install keeps local cards card by card, so a local Walk.pose can stand beside a
        shipped Walk.anim (keep_local puts it back there, not `write`) - and Update from
        selection REPLACES it. The other suffix is asked only for a card that does not exist
        yet: a replace of one that does is no new name."""
        store.write(self.root, "", "Walk", self.header(), frames=self.frames())
        os.makedirs(self.root + "/Walk.pose")
        with open(self.root + "/Walk.pose/" + store.POSE_FILE, "w") as handle:
            json.dump(pose(name="Walk"), handle)
        path = store.write(self.root, "", "Walk", pose(members=("a", "b")), replace=True)
        self.assertTrue(path.endswith("/Walk.pose"))
        self.assertEqual(store.read(path)["members"], ["a", "b"])
        anim = store.write(self.root, "", "Walk", self.header(frames=10), frames=self.frames(10),
                           replace=True)
        self.assertEqual(store.read(anim)["frames"], 10)
        self.assertEqual(sorted(os.listdir(self.root)), ["Walk.anim", "Walk.pose"])
        # without replace both are still refused: each name is taken by its own card
        for data, extra in ((pose(), {}), (self.header(), {"frames": self.frames()})):
            with self.assertRaises(ValueError):
                store.write(self.root, "", "Walk", data, **extra)

    def test_a_rename_or_a_move_onto_the_other_type_s_name_is_refused(self):
        walk = store.write(self.root, "", "Walk", self.header(), frames=self.frames())
        fist = store.write(self.root, "", "Fist", pose())
        with self.assertRaises(ValueError):
            store.rename(walk, "Fist")
        self.assertEqual(store.read(walk)["name"], "Walk")
        store.write(self.root, "Loco", "Walk", pose(name="Walk"))
        with self.assertRaises(ValueError):
            store.move(walk, self.root, "Loco")
        self.assertTrue(os.path.isdir(walk) and os.path.isdir(fist))

    def test_an_objects_animation_counts_its_objects(self):
        store.write(self.root, "", "Door", self.header(kind="objects", objects=[
            {"name": "door", "path": "|door", "attrs": {}}], members=[]))
        card = store.cards(self.root)[0][0]
        self.assertEqual((card.type, card.kind, card.label, card.count),
                         ("anim", "objects", "objects", 1))
        self.assertEqual(card.preview, "")

    def test_rename_move_remove_keep_the_suffix(self):
        path = store.write(self.root, "", "Walk", self.header(), frames=self.frames())
        path = store.rename(path, "Run")
        self.assertTrue(path.endswith("/Run.anim"))
        self.assertEqual(store.read(path)["name"], "Run")
        self.assertEqual(len(store.read_frames(path)["world"]), 48)
        store.make_folder(self.root, "", "Loco")
        path = store.move(path, self.root, "Loco")
        self.assertTrue(path.endswith("/Loco/Run.anim"))
        self.assertEqual(store.cards(self.root)[0][0].folder, "Loco")
        gone = store.remove(path, self.trash)
        self.assertTrue(gone.endswith("_Run.anim"))
        self.assertTrue(os.path.isfile(gone + "/" + store.ANIM_FILE))

    def test_remove_keeps_two_of_one_animation_and_its_suffix(self):
        trash = store.trash_dir(self.trash)
        gone = []
        for _ in range(2):
            path = store.write(self.root, "", "Walk", self.header(), frames=self.frames())
            gone.append(store.remove(path, trash))
        self.assertEqual(len(set(gone)), 2)
        self.assertTrue(all(os.path.isdir(path) and path.endswith(".anim") for path in gone))

    def test_a_replace_keeps_the_files_it_is_not_given(self):
        path = store.write(self.root, "", "Walk", self.header(), frames=self.frames(),
                           thumbnail=self.image(), preview=self.image())
        store.write(self.root, "", "Walk", self.header(frames=10), frames=self.frames(),
                    replace=True)
        self.assertTrue(os.path.isfile(path + "/" + store.PREVIEW_FILE))
        self.assertTrue(os.path.isfile(path + "/" + store.THUMB_FILE))
        self.assertEqual(store.read(path)["frames"], 10)

    def test_a_failed_animation_write_leaves_no_card(self):
        with self.assertRaises(OSError):
            store.write(self.root, "", "Walk", self.header(), frames=self.frames(),
                        preview=os.path.join(self.images, "missing.jpg"))
        self.assertEqual(os.listdir(self.root), [])

    def test_a_failed_animation_replace_keeps_the_old_card_whole(self):
        """The frames are staged with the rest: a replace that dies on the preview must not leave
        the new frames under the old header."""
        path = store.write(self.root, "", "Walk", self.header(), frames=self.frames())
        with self.assertRaises(OSError):
            store.write(self.root, "", "Walk", self.header(frames=10), frames=self.frames(10),
                        replace=True, preview=os.path.join(self.images, "missing.jpg"))
        self.assertEqual(store.read(path)["frames"], 48)
        self.assertEqual(len(store.read_frames(path)["world"]), 48)
        self.assertEqual(sorted(os.listdir(path)), [store.ANIM_FILE, store.FRAMES_FILE])

    def test_a_folder_named_like_a_card_is_refused(self):
        with self.assertRaises(ValueError):
            store.make_folder(self.root, "", "Loco.anim")
        store.make_folder(self.root, "", "Loco")
        with self.assertRaises(ValueError):
            store.rename_folder(self.root, "Loco", "Loco.anim")
        with self.assertRaises(ValueError):
            store.write(self.root, "Loco.anim", "Walk", pose())

    def test_a_broken_animation_header_is_reported(self):
        os.makedirs(self.root + "/Bad.anim")
        with open(self.root + "/Bad.anim/anim.json", "w") as f:
            f.write("{")
        os.makedirs(self.root + "/Empty.anim")
        os.makedirs(self.root + "/Posey.anim")
        with open(self.root + "/Posey.anim/anim.json", "w") as f:
            json.dump(pose(), f)                         # a pose's format in an animation card
        found, broken = store.cards(self.root)
        self.assertEqual(found, [])
        self.assertEqual(len(broken), 3)

    def test_a_header_number_that_is_no_number_is_a_broken_card(self):
        """Python's json reads Infinity and NaN, and an integer of any length: `int(inf)` is an
        OverflowError, `int(nan)` a ValueError, `float(10 ** 400)` an OverflowError - each a
        card reported broken, never an exception out of `cards()` blanking the library."""
        for name, field in (("Inf", '"frames": Infinity'), ("NaN", '"frames": NaN'),
                            ("Huge", '"start": 1' + "0" * 400)):
            os.makedirs(self.root + "/%s.anim" % name)
            with open(self.root + "/%s.anim/anim.json" % name, "w") as handle:
                handle.write('{"format": "%s", "version": 1, "kind": "character", %s}'
                             % (store.ANIM_FORMAT, field))
        store.write(self.root, "", "Walk", self.header(), frames=self.frames())
        found, broken = store.cards(self.root)
        self.assertEqual([card.name for card in found], ["Walk"])
        self.assertEqual(sorted(os.path.basename(path) for path in broken),
                         ["Huge.anim", "Inf.anim", "NaN.anim"])

    def test_the_type_word_is_searched_and_the_type_filters(self):
        store.write(self.root, "", "Walk", self.header(), frames=self.frames())
        store.write(self.root, "", "Fist", pose())
        cards = store.cards(self.root)[0]
        self.assertEqual([c.name for c in store.filter_cards(cards, "animation")], ["Walk"])
        self.assertEqual([c.name for c in store.filter_cards(cards, "pose")], ["Fist"])
        self.assertEqual([c.name for c in store.of_type(cards, "pose")], ["Fist"])
        self.assertEqual([c.name for c in store.of_type(cards, "anim")], ["Walk"])
        self.assertEqual(len(store.of_type(cards, "all")), 2)
        self.assertEqual(store.TYPES, ("all", "pose", "anim"))
        with self.assertRaises(ValueError):
            store.of_type(cards, "clips")

    def test_a_part_of_the_type_word_matches_no_card_by_its_type(self):
        """The final review (S14): «po» or «anim» typed on the way to a name matched EVERY card
        of that type through its type word. The type word is a whole term now - pose / poses,
        anim / animation / animations - and the name, the folder and the label still match by
        any part."""
        store.write(self.root, "", "Walk", self.header(), frames=self.frames())
        store.write(self.root, "", "Fist", pose())
        store.write(self.root, "", "Point", pose(name="Point"))
        store.write(self.root, "", "Animal", pose(name="Animal"))
        cards = store.cards(self.root)[0]

        def names(query):
            return sorted(c.name for c in store.filter_cards(cards, query))

        self.assertEqual(names("po"), ["Point"])                 # the name, not «pose»
        self.assertEqual(names("ani"), ["Animal"])               # the name, not «animation»
        self.assertEqual(names("anima"), ["Animal"])
        for word in ("pose", "poses", "POSES"):
            self.assertEqual(names(word), ["Animal", "Fist", "Point"], word)
        for word in ("animation", "Animations"):
            self.assertEqual(names(word), ["Walk"], word)
        self.assertEqual(names("anim"), ["Animal", "Walk"])     # the type word, and a name
        self.assertEqual(names("walk anim"), ["Walk"])
        self.assertEqual(names("fist animation"), [])

    def test_a_header_range_that_is_no_number_or_key_times_that_are_no_list_is_broken(self):
        """The final review (S12): `"start": NaN` and `"end": Infinity` passed `float()` and the
        pick raised half way; a `key_times` that is no list (or holds what is no number) raised in
        the paste plan. Each is a card reported broken; absent `key_times` is fine."""
        bad = {"NaNStart": '"start": NaN, "end": 5.0, "frames": 6',
               "InfEnd": '"start": 0.0, "end": Infinity, "frames": 6',
               "MinusInf": '"start": -Infinity, "end": 5.0, "frames": 6',
               "Times": '"start": 0.0, "end": 5.0, "frames": 6, "key_times": "0 5"',
               "TimesNum": '"start": 0.0, "end": 5.0, "frames": 6, "key_times": 5',
               "TimesNaN": '"start": 0.0, "end": 5.0, "frames": 6, "key_times": [0, NaN]',
               "TimesWord": '"start": 0.0, "end": 5.0, "frames": 6, "key_times": [0, "x"]'}
        good = {"NoTimes": '"start": 0.0, "end": 5.0, "frames": 6',
                "Times": '"start": 0.0, "end": 5.0, "frames": 6, "key_times": [0, 2.5, 5]',
                "NullTimes": '"start": 0.0, "end": 5.0, "frames": 6, "key_times": null'}
        for group, fields in (("Bad", bad), ("Good", good)):
            for name, field in fields.items():
                folder = self.root + "/%s%s.anim" % (group, name)
                os.makedirs(folder)
                with open(folder + "/anim.json", "w") as handle:
                    handle.write('{"format": "%s", "version": 1, "kind": "character", %s}'
                                 % (store.ANIM_FORMAT, field))
        found, broken = store.cards(self.root)
        self.assertEqual(sorted(card.name for card in found),
                         sorted("Good" + name for name in good))
        self.assertEqual(sorted(os.path.basename(path) for path in broken),
                         sorted("Bad%s.anim" % name for name in bad))

    def test_replace_writes_into_the_card_at_its_path(self):
        """The final review (S13): Update and Replace thumbnail wrote back BY NAME, so a card
        renamed in Explorer to a name `safe_name` changes («Walk.» -> «Walk») came back as a
        stray new card. `store.replace` writes into the card folder at `path`, the staging rules
        of `write`: every file given swapped in (the main file last), every file not given
        kept, the `name` inside the folder's own."""
        path = store.write(self.root, "", "Walk", self.header(), frames=self.frames(),
                           thumbnail=self.image(b"old still"), preview=self.image(b"old sheet"))
        odd = self.root + "/Walk. .anim"                     # an Explorer rename: «Walk. »
        os.rename(path, odd)
        store.replace(odd, self.header(frames=10, name="whatever"), frames=self.frames(10))
        self.assertEqual(sorted(os.listdir(self.root)), ["Walk. .anim"])      # no stray card
        self.assertEqual(store.read(odd)["frames"], 10)
        self.assertEqual(store.read(odd)["name"], "Walk. ")
        self.assertEqual(len(store.read_frames(odd)["world"]), 10)
        with open(odd + "/" + store.THUMB_FILE, "rb") as handle:
            self.assertEqual(handle.read(), b"old still")    # not given: kept
        store.replace(odd, self.header(), thumbnail=self.image(b"new still"),
                      preview=self.image(b"new sheet"))
        for name, data in ((store.THUMB_FILE, b"new still"), (store.PREVIEW_FILE, b"new sheet")):
            with open(odd + "/" + name, "rb") as handle:
                self.assertEqual(handle.read(), data)
        self.assertEqual(len(store.read_frames(odd)["world"]), 10)   # the frames kept
        self.assertEqual([n for n in os.listdir(odd) if n.endswith(".part")], [])
        # a pose card too, the pose's own file
        fist = store.write(self.root, "", "Fist", pose())
        store.replace(fist, pose(members=("a", "b")))
        self.assertEqual(store.read(fist)["members"], ["a", "b"])
        # refused: no card there; the other type's data; a pose given frames
        with self.assertRaises(ValueError):
            store.replace(self.root + "/Gone.anim", self.header())
        with self.assertRaises(ValueError):
            store.replace(fist, self.header())
        with self.assertRaises(ValueError):
            store.replace(odd, pose())
        with self.assertRaises(ValueError):
            store.replace(fist, pose(), frames=self.frames())
        self.assertEqual(store.read(fist)["members"], ["a", "b"])

    def test_a_failed_replace_at_a_path_keeps_the_card_whole(self):
        path = store.write(self.root, "", "Walk", self.header(), frames=self.frames())
        with self.assertRaises(OSError):
            store.replace(path, self.header(frames=10), frames=self.frames(10),
                          preview=os.path.join(self.images, "missing.jpg"))
        self.assertEqual(store.read(path)["frames"], 48)
        self.assertEqual(sorted(os.listdir(path)), [store.ANIM_FILE, store.FRAMES_FILE])


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
