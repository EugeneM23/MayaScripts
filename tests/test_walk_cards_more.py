"""Walk Builder's cards (maya_walk.cards), the corners the first tests left: the library's folder, paths and names,
a card that cannot be read or is not whole, the copy kept on a skeleton when a card is refused or gone, the old
poses and walks moved once even when one of them is broken, the time unit, the frames' order and Manny's bind
as a walk card's rest."""

import gzip
import json
import math
import os
import shutil
import sys
import tempfile
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.join(os.path.dirname(HERE), "SkeldarAnim")
if PLUGIN not in sys.path:
    sys.path.insert(0, PLUGIN)

from maya_walk import cards                    # noqa: E402
from maya_walk import files as wf              # noqa: E402
from maya_walk import model as wm              # noqa: E402
from maya_poselib import store                 # noqa: E402

EYE = [1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0]


def bones(x=0.0):
    moved = list(EYE)
    moved[12] = x
    return {"root": {"parent": None, "canonical": "root", "rest": EYE, "world": EYE},
            "pelvis": {"parent": "root", "canonical": "pelvis", "rest": EYE, "world": moved}}


def pose_card(library, folder, name, kind="character", data_bones=None):
    data = {"format": store.FORMAT, "kind": kind, "bones": bones() if data_bones is None else data_bones,
            "character": {"label": name}, "members": ["pelvis"], "objects": []}
    return store.write(library, folder, name, data)


def turn(degrees, x=0.0, y=0.0, z=0.0):
    """A row-vector world matrix: a turn about Y and a place."""
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return np.array([[c, 0, -s, 0], [0, 1, 0, 0], [s, 0, c, 0], [x, y, z, 1]], float)


def walk(names, parents, frames=3, start=0, positions=None):
    """A walk file's dict over `names` / `parents` (leaf: parent leaf), each bone turning a little a frame."""
    positions = positions or dict((leaf, (0.0, 10.0 * i, 0.0)) for i, leaf in enumerate(names))
    worlds = np.array([[turn(3.0 * f + i, *positions[leaf]) for f in range(frames)]
                       for i, leaf in enumerate(names)])
    statics = dict((leaf, {"parent": parents[leaf], "canonical": leaf,
                           "rest": [float(v) for v in worlds[i, 0].reshape(16)]}) for i, leaf in enumerate(names))
    index = dict((leaf, i) for i, leaf in enumerate(names))
    return {"names": list(names), "parents": [index[parents[leaf]] if parents[leaf] else -1 for leaf in names],
            "worlds": worlds, "fps": 30.0, "up": [0, 1, 0], "name": "stroll", "start": start, "statics": statics}


def truncated_gzip(path, payload):
    """A gzip file cut in half: the header reads, the stream ends early."""
    raw = gzip.compress(json.dumps(payload).encode("utf-8"))
    with open(path, "wb") as handle:
        handle.write(raw[:len(raw) // 2])


class Base(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.mkdtemp()
        self.library = os.path.join(self.temp, "library").replace("\\", "/")
        self.walks = os.path.join(self.temp, "walks")
        os.makedirs(self.library)
        os.makedirs(self.walks)

    def tearDown(self):
        shutil.rmtree(self.temp, ignore_errors=True)

    def anim_card(self, data, name="stroll", folder=cards.WALK_FOLDER):
        header, frames = cards.card_of_walk(data)
        return store.write(self.library, folder, name, header, frames=frames)


class FakeVars(object):
    """A cmds with only optionVar (the library's folder remembered)."""

    def __init__(self, value=None, broken=False):
        self.value, self.broken = value, broken

    def optionVar(self, exists=None, query=None):
        if self.broken:
            raise RuntimeError("no optionVar here")
        if exists is not None:
            return self.value is not None
        return self.value


class LibraryAndPaths(Base):

    def test_the_plugin_folder_holds_maya_walk_and_maya_poselib(self):
        here = cards.plugin_dir()
        self.assertNotIn("\\", here)
        self.assertEqual(os.path.normcase(here), os.path.normcase(os.path.abspath(PLUGIN).replace("\\", "/")))
        self.assertTrue(os.path.isdir(os.path.join(here, "maya_walk")))
        self.assertTrue(os.path.isdir(os.path.join(here, "maya_poselib")))

    def test_the_library_is_the_remembered_folder_when_it_names_one_else_the_plugin_s(self):
        default = store.default_root(cards.plugin_dir())
        self.assertEqual(cards.library_root(), default)                        # no cmds: the plugin's
        self.assertEqual(cards.library_root(FakeVars(self.library)), self.library)
        self.assertEqual(cards.library_root(FakeVars(None)), default)          # nothing remembered
        self.assertEqual(cards.library_root(FakeVars(os.path.join(self.temp, "nowhere"))), default)
        self.assertEqual(cards.library_root(FakeVars(broken=True)), default)  # a cmds that cannot say
        self.assertEqual(cards.library_root(object()), default)                # a fake with no optionVar

    def test_absolute_of_nothing_an_absolute_path_and_a_relative_one(self):
        self.assertEqual(cards.absolute("", self.library), "")
        self.assertEqual(cards.absolute(None, self.library), "")
        outside = os.path.join(self.temp, "Elsewhere", "goblin.pose")
        self.assertEqual(cards.absolute(outside, self.library), outside.replace("\\", "/"))
        self.assertEqual(cards.absolute("A/b.pose", self.library + "\\"), self.library + "/A/b.pose")

    def test_a_path_inside_the_library_is_relative_whatever_its_letter_case(self):
        rel = cards.relative(self.library.upper() + "/Swords/sword.pose", self.library.lower())
        self.assertEqual(rel.lower(), "swords/sword.pose")
        self.assertEqual(cards.relative(self.library + "/x.pose/", self.library), "x.pose")
        sibling = self.library + "_other/x.pose"                   # a folder starting with the same letters
        self.assertTrue(os.path.isabs(cards.relative(sibling, self.library)))

    def test_a_card_s_name_without_its_suffix_and_a_folder_s_as_it_is(self):
        self.assertEqual(cards.card_name("Walk poses/goblin.pose"), "goblin")
        self.assertEqual(cards.card_name("Walk cycles\\run.anim\\"), "run")
        self.assertEqual(cards.card_name("Folder/plain"), "plain")
        self.assertEqual(cards.legacy_card("two handed/sword"), cards.MIGRATED_FOLDER + "/" +
                         store.safe_name("two handed/sword") + store.CARD_SUFFIX)


class ReadAndStamp(Base):

    def test_a_card_whose_file_is_broken_cannot_be_read(self):
        path = pose_card(self.library, "", "broken")
        with open(os.path.join(path, store.POSE_FILE), "w") as handle:
            handle.write("{ not json")
        with self.assertRaises(cards.Refusal) as raised:
            cards.read_card(path)
        self.assertIn("broken cannot be read", str(raised.exception))

    def test_a_bone_short_of_a_whole_matrix_is_refused_by_name(self):
        half = bones()
        half["pelvis"]["world"] = EYE[:15]
        path = pose_card(self.library, "", "half", data_bones=half)
        with self.assertRaises(cards.Refusal) as raised:
            cards.read_card(path)
        self.assertEqual(str(raised.exception), "half: the bone pelvis is not whole")
        restless = bones()
        del restless["root"]["rest"]
        path = pose_card(self.library, "", "restless", data_bones=restless)
        with self.assertRaises(cards.Refusal):
            cards.read_card(path)

    def test_the_stamp_is_the_card_s_file_time_and_none_when_it_is_gone(self):
        path = pose_card(self.library, "", "goblin")
        self.assertEqual(cards.stamp(path), os.path.getmtime(os.path.join(path, store.POSE_FILE)))
        shutil.rmtree(path)
        self.assertIsNone(cards.stamp(path))

    def test_unpack_refuses_what_is_not_bones(self):
        import base64
        self.assertIsNone(cards.unpack(None))
        not_a_dict = base64.b64encode(gzip.compress(b"[1, 2]")).decode("ascii")
        self.assertIsNone(cards.unpack(not_a_dict))
        empty = base64.b64encode(gzip.compress(b"{}")).decode("ascii")
        self.assertIsNone(cards.unpack(empty))


class Resolve(Base):

    def test_a_card_refused_walks_on_the_copy_and_says_why(self):
        path = pose_card(self.library, "Cams", "dolly", kind="objects")
        rel = cards.relative(path, self.library)
        name, read, note = cards.resolve(rel, cards.pack(bones(6.0)), None, self.library, self.walks)
        self.assertEqual((name, read["pelvis"]["world"][12]), ("dolly", 6.0))
        self.assertIn("card of objects", note)
        self.assertTrue(note.endswith(" - using the copy on the skeleton"))

    def test_a_card_refused_with_no_copy_is_no_pose_and_says_why(self):
        path = pose_card(self.library, "", "dolly", kind="objects")
        rel = cards.relative(path, self.library)
        name, read, note = cards.resolve(rel, "", None, self.library, self.walks)
        self.assertEqual((name, read), (None, None))
        self.assertIn("card of objects", note)
        self.assertNotIn("using the copy", note)
        name, read, note = cards.resolve("gone/away.pose", None, None, self.library, self.walks)
        self.assertEqual((name, read, note), (None, None, "pose card away is gone"))

    def test_an_old_pose_name_with_neither_its_card_nor_its_file_walks_on_the_copy(self):
        name, read, note = cards.resolve(None, cards.pack(bones(2.0)), "goblin", self.library, self.walks)
        self.assertEqual((name, read["pelvis"]["world"][12], note), ("goblin", 2.0, cards.GONE % "goblin"))
        self.assertEqual(cards.resolve(None, "", "goblin", self.library, self.walks), (None, None, ""))


class MigratePoses(Base):

    def test_a_broken_pose_file_is_listed_and_left_and_the_good_ones_move(self):
        wf.save_pose(wf.pose_path_for(self.walks, "goblin"), "goblin", bones(1.0))
        with open(wf.pose_path_for(self.walks, "broken"), "wb") as handle:
            handle.write(b"not a gzip at all")
        self.assertEqual(cards.migrate(self.walks, self.library, author="me"), ["goblin"])
        with open(os.path.join(self.walks, cards.MIGRATED_LIST)) as handle:
            self.assertEqual(json.load(handle), ["broken", "goblin"])
        card = store.read(os.path.join(self.library, cards.MIGRATED_FOLDER, "goblin.pose"))
        self.assertEqual((card["author"], card["members"]), ("me", ["pelvis", "root"]))
        self.assertEqual(cards.migrate(self.walks, self.library), [])          # never tried again

    def test_a_list_not_a_list_counts_as_nothing_moved(self):
        wf.save_pose(wf.pose_path_for(self.walks, "goblin"), "goblin", bones())
        with open(os.path.join(self.walks, cards.MIGRATED_LIST), "w") as handle:
            json.dump({"goblin": True}, handle)
        self.assertEqual(cards.migrate(self.walks, self.library), ["goblin"])

    def test_a_list_that_cannot_be_written_still_moves_the_poses(self):
        wf.save_pose(wf.pose_path_for(self.walks, "goblin"), "goblin", bones())
        os.makedirs(os.path.join(self.walks, cards.MIGRATED_LIST))             # a folder where the list goes
        self.assertEqual(cards.migrate(self.walks, self.library), ["goblin"])
        self.assertTrue(os.path.isdir(os.path.join(self.library, cards.MIGRATED_FOLDER, "goblin.pose")))

    def test_no_walks_folder_moves_nothing(self):
        self.assertEqual(cards.migrate(os.path.join(self.temp, "none"), self.library), [])

    def test_a_truncated_pose_file_is_listed_and_left_like_any_broken_one(self):
        """Fixed 2026-10-27, the bug as it was (maya_walk/files.py:158, load_pose): a .wpose.gz cut short raises EOFError, which is neither the
        OSError nor the ValueError it catches - so cards.migrate (cards.py:182) stops at that pose instead of
        listing it as broken: the poses after it are never moved and the list is never written, so every
        session's first Walk Builder card prints the same traceback."""
        truncated_gzip(wf.pose_path_for(self.walks, "a_cut"), {"format": wf.POSE_FORMAT, "bones": bones()})
        wf.save_pose(wf.pose_path_for(self.walks, "goblin"), "goblin", bones())
        self.assertEqual(cards.migrate(self.walks, self.library), ["goblin"])


class TimeUnits(unittest.TestCase):

    def test_a_card_s_time_unit_both_ways(self):
        self.assertEqual(cards.unit_of(60), "ntscf")
        self.assertEqual(cards.unit_of(29.97), "29.97fps")
        self.assertEqual(cards.fps_of("29.97fps"), 29.97)
        self.assertEqual(cards.fps_of("48fps"), 48.0)
        self.assertEqual(cards.fps_of("fastfps"), 30.0)          # "<n>fps" with no number: the default
        self.assertEqual(cards.fps_of(None), 30.0)
        self.assertEqual(cards.fps_of(""), 30.0)


class WalkCards(Base):

    def test_the_stamp_is_both_files_times_and_none_without_them(self):
        path = self.anim_card(walk(["root", "pelvis"], {"root": None, "pelvis": "root"}))
        self.assertEqual(cards.walk_stamp(path), [os.path.getmtime(os.path.join(path, store.ANIM_FILE)),
                                                  os.path.getmtime(os.path.join(path, store.FRAMES_FILE))])
        os.remove(os.path.join(path, store.FRAMES_FILE))
        self.assertIsNone(cards.walk_stamp(path))
        self.assertIsNone(cards.walk_stamp(pose_card(self.library, "", "pose")))

    def test_a_cycle_of_parents_has_a_finite_depth(self):
        self.assertEqual(cards._depth("a", {"a": "b", "b": "a"}), 2)
        self.assertEqual(cards._depth("c", {"c": "b", "b": "a", "a": None}), 2)
        self.assertEqual(cards._depth("lone", {}), 0)

    def test_children_saved_before_their_parents_are_read_parents_first(self):
        names = ["thigh_l", "pelvis", "root"]
        parents = {"thigh_l": "pelvis", "pelvis": "root", "root": None}
        data = walk(names, parents, frames=4)
        back = cards.walk_data(self.anim_card(data))
        self.assertEqual(back["names"], ["root", "pelvis", "thigh_l"])
        self.assertEqual(back["parents"], [-1, 0, 1])
        for i, leaf in enumerate(back["names"]):
            self.assertLess(float(np.abs(back["worlds"][i] - data["worlds"][names.index(leaf)]).max()), 1e-6, leaf)
        self.assertEqual(back["statics"]["thigh_l"]["parent"], "pelvis")

    def test_a_bone_with_no_frames_is_left_out_and_its_parent_read_as_none(self):
        data = walk(["root", "pelvis", "thigh_l"], {"root": None, "pelvis": "root", "thigh_l": "pelvis"})
        header, frames = cards.card_of_walk(data)
        frames["bones"] = ["pelvis", "thigh_l"]                     # the root's frames gone
        frames["world"] = [row[7:] for row in frames["world"]]
        path = store.write(self.library, cards.WALK_FOLDER, "rootless", header, frames=frames)
        back = cards.walk_data(path)
        self.assertEqual(back["names"], ["pelvis", "thigh_l"])
        self.assertEqual(back["parents"], [-1, 0])
        self.assertIsNone(back["statics"]["pelvis"]["parent"])

    def test_a_card_whose_header_is_broken_cannot_be_read(self):
        path = self.anim_card(walk(["root", "pelvis"], {"root": None, "pelvis": "root"}))
        with open(os.path.join(path, store.ANIM_FILE), "w") as handle:
            handle.write("garbage")
        with self.assertRaises(cards.Refusal) as raised:
            cards.walk_data(path)
        self.assertIn("stroll cannot be read", str(raised.exception))

    def test_a_card_with_no_bones_is_no_walk(self):
        data = walk(["root", "pelvis"], {"root": None, "pelvis": "root"})
        header, frames = cards.card_of_walk(data)
        frames["bones"] = ["somebody_else"]
        path = store.write(self.library, cards.WALK_FOLDER, "strangers", header, frames=frames)
        with self.assertRaises(cards.Refusal) as raised:
            cards.walk_data(path)
        self.assertIn("holds no bones", str(raised.exception))

    def test_a_skeleton_of_manny_s_bones_takes_manny_s_bind_as_its_rest(self):
        """files.template_rests: a walk whose bone lengths are Manny's takes his bind (here a template turned
        a quarter about Y at the same places) - the walk tool's own rest rule."""
        tree = (("root", None, (0, 0, 0)), ("pelvis", "root", (0, 100, 0)), ("spine_01", "pelvis", (0, 110, 0)),
                ("spine_02", "spine_01", (0, 120, 0)), ("spine_03", "spine_02", (0, 130, 0)),
                ("neck_01", "spine_03", (0, 145, 0)), ("head", "neck_01", (0, 155, 0)),
                ("thigh_l", "pelvis", (10, 95, 0)), ("calf_l", "thigh_l", (10, 50, 0)),
                ("foot_l", "calf_l", (10, 8, 0)), ("thigh_r", "pelvis", (-10, 95, 0)),
                ("calf_r", "thigh_r", (-10, 50, 0)), ("foot_r", "calf_r", (-10, 8, 0)))
        names = [leaf for leaf, _, _ in tree]
        parents = dict((leaf, parent) for leaf, parent, _ in tree)
        places = dict((leaf, tuple(float(v) for v in at)) for leaf, _, at in tree)
        data = walk(names, parents, frames=2, positions=places)
        template = dict((leaf, {"parent": parent, "world_matrix": [float(v) for v in turn(90.0, *at).reshape(16)]})
                        for leaf, parent, at in tree)
        path = self.anim_card(data, name="manny_walk")
        plain = cards.walk_data(path)
        manny = cards.walk_data(path, template)
        for leaf in names:
            self.assertEqual(manny["statics"][leaf]["rest"], template[leaf]["world_matrix"], leaf)
            self.assertNotEqual(plain["statics"][leaf]["rest"], template[leaf]["world_matrix"], leaf)
        self.assertLess(float(np.abs(manny["worlds"] - plain["worlds"]).max()), 1e-12)   # the frames as they are
        stranger = dict(template)
        stranger["calf_l"] = dict(template["calf_l"], world_matrix=[float(v) for v in turn(90.0, 10, 80, 0).reshape(16)])
        stranger["calf_r"] = dict(template["calf_r"], world_matrix=[float(v) for v in turn(90.0, -10, 80, 0).reshape(16)])
        stranger["head"] = dict(template["head"], world_matrix=[float(v) for v in turn(90.0, 0, 175, 0).reshape(16)])
        stranger["spine_02"] = dict(template["spine_02"],
                                    world_matrix=[float(v) for v in turn(90.0, 0, 125, 0).reshape(16)])
        not_manny = cards.walk_data(path, stranger)                  # other lengths: the card's own rest
        self.assertEqual(not_manny["statics"]["pelvis"]["rest"], plain["statics"]["pelvis"]["rest"])


class MigrateWalks(Base):

    def save_walk(self, name):
        data = walk(["root", "pelvis"], {"root": None, "pelvis": "root"})
        wf.save(wf.path_for(self.walks, name), wf.clip_of(data, wm), data["statics"], data["start"])

    def test_a_broken_walk_file_is_listed_and_left_and_a_taken_name_too(self):
        self.save_walk("asd")
        self.save_walk("dw")
        with open(wf.path_for(self.walks, "broken"), "wb") as handle:
            handle.write(b"garbage")
        self.anim_card(walk(["root", "pelvis"], {"root": None, "pelvis": "root"}), name="dw")   # the animator's
        before = os.path.getmtime(os.path.join(self.library, cards.WALK_FOLDER, "dw.anim", store.ANIM_FILE))
        self.assertEqual(cards.migrate_walks(self.walks, self.library, author="me"), ["asd"])
        with open(os.path.join(self.walks, cards.WALKS_LIST)) as handle:
            self.assertEqual(json.load(handle), ["asd", "broken", "dw"])
        self.assertEqual(os.path.getmtime(os.path.join(self.library, cards.WALK_FOLDER, "dw.anim", store.ANIM_FILE)),
                         before)                                     # the animator's card stands
        self.assertEqual(store.read(os.path.join(self.library, cards.WALK_FOLDER, "asd.anim"))["author"], "me")
        self.assertEqual(cards.migrate_walks(self.walks, self.library), [])

    def test_a_list_that_is_no_list_counts_as_nothing_moved(self):
        self.save_walk("asd")
        with open(os.path.join(self.walks, cards.WALKS_LIST), "w") as handle:
            handle.write("5")
        self.assertEqual(cards.migrate_walks(self.walks, self.library), ["asd"])

    def test_a_list_that_cannot_be_written_still_moves_the_walks(self):
        self.save_walk("asd")
        os.makedirs(os.path.join(self.walks, cards.WALKS_LIST))
        self.assertEqual(cards.migrate_walks(self.walks, self.library), ["asd"])

    def test_the_card_of_a_walk_reads_back_its_start_and_its_time_unit(self):
        data = walk(["root", "pelvis"], {"root": None, "pelvis": "root"}, frames=3, start=12)
        data["fps"] = 24
        header, frames = cards.card_of_walk(data, author="me")
        self.assertEqual((header["fps"], header["start"], header["end"], header["frames"]), ("film", 12.0, 14.0, 3))
        self.assertEqual(header["key_times"], [12.0, 13.0, 14.0])
        self.assertEqual((header["author"], header["scene"]), ("me", "stroll" + wf.SUFFIX))
        back = cards.walk_data(store.write(self.library, "", "film", header, frames=frames))
        self.assertEqual((back["fps"], back["start"]), (24.0, 12))

    def test_a_truncated_walk_file_is_listed_and_left_like_any_broken_one(self):
        """Fixed 2026-10-27, the bug as it was (maya_walk/files.py:69, load): a .walk.gz cut short raises EOFError, outside the (OSError,
        ValueError) it turns into a Refusal - so cards.migrate_walks (cards.py:357) stops there: the walks after it
        are never moved and the list is never written (every session tries again and fails the same way)."""
        truncated_gzip(wf.path_for(self.walks, "a_cut"), {"format": wf.FORMAT, "names": ["root"] * 50})
        self.save_walk("dw")
        self.assertEqual(cards.migrate_walks(self.walks, self.library), ["dw"])


if __name__ == "__main__":
    unittest.main()
