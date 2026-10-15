"""Walk Builder's pose from a Pose Library card (maya_walk.cards) and the well (maya_walk.posewell): reading a card,
the copy kept on a walked skeleton, the old .wpose poses moved into the library once."""

import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.join(os.path.dirname(HERE), "SkeldarAnim")
if PLUGIN not in sys.path:
    sys.path.insert(0, PLUGIN)

from maya_walk import cards                    # noqa: E402
from maya_walk import files as wf              # noqa: E402
from maya_poselib import store                 # noqa: E402

EYE = [1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0]


def bones(x=0.0, drive=False):
    moved = list(EYE)
    moved[12] = x
    out = {"root": {"parent": None, "canonical": "root", "rest": EYE, "world": EYE},
           "pelvis": {"parent": "root", "canonical": "pelvis", "rest": EYE, "world": moved}}
    if drive:
        out["pelvis"]["drive"] = EYE
    return out


def write_card(library, folder, name, kind="character", anim=False, data_bones=None):
    data = {"format": store.ANIM_FORMAT if anim else store.FORMAT, "kind": kind,
            "bones": bones() if data_bones is None else data_bones, "character": {"label": name},
            "members": ["pelvis"], "objects": []}
    return store.write(library, folder, name, data)


class Base(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.mkdtemp()
        self.library = os.path.join(self.temp, "library").replace("\\", "/")
        self.walks = os.path.join(self.temp, "walks")
        os.makedirs(self.library)
        os.makedirs(self.walks)

    def tearDown(self):
        shutil.rmtree(self.temp, ignore_errors=True)


class ReadCard(Base):

    def test_a_pose_card_reads_with_its_drive(self):
        path = write_card(self.library, "Swords", "sword", data_bones=bones(3.0, drive=True))
        name, read = cards.read_card(path)
        self.assertEqual(name, "sword")
        self.assertEqual(read["pelvis"]["world"][12], 3.0)
        self.assertEqual(read["pelvis"]["drive"], EYE)          # posemath.Transfer reads it

    def test_an_animation_an_objects_or_a_broken_card_is_refused(self):
        anim = write_card(self.library, "", "Run", anim=True)
        with self.assertRaises(cards.Refusal) as raised:
            cards.read_card(anim)
        self.assertIn("animation card", str(raised.exception))
        objects = write_card(self.library, "", "Cam", kind="objects")
        with self.assertRaises(cards.Refusal):
            cards.read_card(objects)
        empty = write_card(self.library, "", "Empty", data_bones={})
        with self.assertRaises(cards.Refusal):
            cards.read_card(empty)

    def test_paths_relative_to_the_library(self):
        path = write_card(self.library, "A/B", "pose")
        rel = cards.relative(path, self.library)
        self.assertEqual(rel, "A/B/pose.pose")
        self.assertEqual(cards.absolute(rel, self.library), path.replace("\\", "/"))
        self.assertEqual(cards.card_name(rel), "pose")
        outside = os.path.join(self.temp, "elsewhere.pose")
        self.assertTrue(os.path.isabs(cards.relative(outside, self.library)))


class Copy(Base):

    def test_pack_round_trip(self):
        self.assertEqual(cards.unpack(cards.pack(bones(2.5, drive=True))), bones(2.5, drive=True))
        self.assertIsNone(cards.unpack(""))
        self.assertIsNone(cards.unpack("not base64 of gzip"))

    def test_the_card_first_then_the_copy_when_it_is_gone(self):
        path = write_card(self.library, "Swords", "sword", data_bones=bones(1.0))
        rel = cards.relative(path, self.library)
        copy = cards.pack(bones(9.0))
        name, read, note = cards.resolve(rel, copy, None, self.library, self.walks)
        self.assertEqual((name, read["pelvis"]["world"][12], note), ("sword", 1.0, ""))   # the card, edited
        shutil.rmtree(path)
        name, read, note = cards.resolve(rel, copy, None, self.library, self.walks)
        self.assertEqual((name, read["pelvis"]["world"][12]), ("sword", 9.0))
        self.assertEqual(note, "pose card sword is gone - using the copy on the skeleton")
        self.assertEqual(cards.resolve(rel, "", None, self.library, self.walks)[:2], (None, None))

    def test_an_old_pose_name_its_migrated_card_then_its_file(self):
        wf.save_pose(wf.pose_path_for(self.walks, "goblin"), "goblin", bones(4.0))
        name, read, note = cards.resolve(None, "", "goblin", self.library, self.walks)
        self.assertEqual((name, read["pelvis"]["world"][12], note), ("goblin", 4.0, ""))
        write_card(self.library, cards.MIGRATED_FOLDER, "goblin", data_bones=bones(5.0))
        self.assertEqual(cards.resolve(None, "", "goblin", self.library, self.walks)[1]["pelvis"]["world"][12],
                         5.0)
        self.assertEqual(cards.resolve(None, None, None, self.library, self.walks), (None, None, ""))


class Migrate(Base):

    def test_old_poses_become_cards_once(self):
        for name, x in (("goblin", 1.0), ("two_handed_sword", 2.0)):
            wf.save_pose(wf.pose_path_for(self.walks, name), name, bones(x))
        made = cards.migrate(self.walks, self.library)
        self.assertEqual(made, ["goblin", "two_handed_sword"])
        sword = os.path.join(self.library, cards.MIGRATED_FOLDER, "two_handed_sword.pose")
        self.assertEqual(cards.read_card(sword)[1]["pelvis"]["world"][12], 2.0)
        self.assertEqual(cards.migrate(self.walks, self.library), [])
        shutil.rmtree(sword)                                     # deleted by the animator: not made again
        self.assertEqual(cards.migrate(self.walks, self.library), [])
        self.assertFalse(os.path.isdir(sword))
        self.assertTrue(os.path.exists(wf.pose_path_for(self.walks, "goblin")))   # the .wpose stays

    def test_a_name_taken_in_the_library_is_left(self):
        write_card(self.library, cards.MIGRATED_FOLDER, "goblin", data_bones=bones(7.0))
        wf.save_pose(wf.pose_path_for(self.walks, "goblin"), "goblin", bones(1.0))
        self.assertEqual(cards.migrate(self.walks, self.library), [])
        card = os.path.join(self.library, cards.MIGRATED_FOLDER, "goblin.pose")
        self.assertEqual(cards.read_card(card)[1]["pelvis"]["world"][12], 7.0)

    def test_a_migrated_card_is_listed_by_the_library(self):
        wf.save_pose(wf.pose_path_for(self.walks, "goblin"), "goblin", bones())
        cards.migrate(self.walks, self.library)
        found, broken = store.cards(self.library)
        self.assertEqual([(c.folder, c.name, c.kind) for c in found], [(cards.MIGRATED_FOLDER, "goblin", "character")])
        self.assertEqual(broken, [])


class Well(Base):
    """The Qt well, offscreen, over a fake Scene."""

    def setUp(self):
        Base.setUp(self)
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        import maya_hubqt
        if maya_hubqt.qt() is None:
            self.skipTest("no Qt")
        self.QtWidgets = maya_hubqt.qt().QtWidgets
        self.app = self.QtWidgets.QApplication.instance() or self.QtWidgets.QApplication([])
        from maya_walk import posewell
        self.posewell = posewell
        test = self

        class FakeScene(object):
            path = ""

            def scale(self):
                return 1.0

            def card(self):
                return (self.path, "sword" if self.path else "", "", "")

            def take(self, path):
                self.path = path
                test.taken.append(path)
                return "pose card sword"

            def clear(self):
                self.path = ""

            def show(self, path):
                test.shown.append(path)
        self.taken, self.shown = [], []
        self.scene = FakeScene()
        self.well = posewell.make_well(self.scene)
        self.well.resize(300, 64)

    def tearDown(self):
        self.well.deleteLater()
        Base.tearDown(self)

    def test_a_card_taken_shows_and_clears(self):
        self.assertEqual(self.well.path, "")
        self.assertEqual(self.well.context_actions(), [])
        self.assertEqual(self.well.take("C:/lib/sword.pose"), "pose card sword")
        self.assertEqual((self.well.path, self.well.name), ("C:/lib/sword.pose", "sword"))
        labels = [row[0] for row in self.well.context_actions() if row]
        self.assertEqual(labels, [self.posewell.SHOW, self.posewell.CLEAR])
        dict(row for row in self.well.context_actions() if row)[self.posewell.CLEAR]()
        self.assertEqual(self.well.path, "")

    def test_it_paints_empty_lit_and_filled(self):
        image = self.well.grab().toImage()                       # empty
        self.assertFalse(image.isNull())
        self.well.set_hot(True)
        self.assertTrue(self.well.hot)
        self.well.take("C:/lib/sword.pose")
        self.assertFalse(self.well.hot)                           # a release unlights it
        self.assertFalse(self.well.grab().toImage().isNull())
