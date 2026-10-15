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


class WellLayout(unittest.TestCase):

    def test_the_height_follows_the_column(self):
        from maya_walk import posewell as pw
        self.assertEqual(pw.well_height(0), pw.HEIGHT)
        self.assertEqual(pw.well_height(3), 3 * (pw.ROW + pw.GAP) + pw.DROP)

    def test_a_point_names_the_card_under_it_not_the_gaps_or_the_drop_row(self):
        from maya_walk import posewell as pw
        self.assertEqual(pw.row_index(1, 2), 0)
        self.assertIsNone(pw.row_index(pw.ROW + 1, 2))                  # the gap
        self.assertEqual(pw.row_index(pw.ROW + pw.GAP + 1, 2), 1)
        self.assertIsNone(pw.row_index(2 * (pw.ROW + pw.GAP) + 2, 2))   # the drop row
        self.assertIsNone(pw.row_index(-1, 2))


class Well(Base):
    """The Qt well, offscreen, over a fake Scene holding a column of cards."""

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
            def __init__(self):
                self.paths, self.active = [], ""

            def scale(self):
                return 1.0

            def cards(self):
                return [(p, p.rsplit("/", 1)[-1][:-5], "", "", p == self.active) for p in self.paths]

            def take(self, path):
                if path not in self.paths:
                    self.paths.append(path)
                self.active = path
                test.taken.append(path)
                return "pose card " + path

            pick = take

            def remove(self, path):
                self.paths.remove(path)
                if self.active == path:
                    self.active = ""

            def remove_all(self):
                self.paths, self.active = [], ""

            def clear(self):
                self.active = ""

            def show(self, path):
                test.shown.append(path)
        self.taken, self.shown = [], []
        self.scene = FakeScene()
        self.well = posewell.make_well(self.scene)
        self.well.resize(300, 64)

    def tearDown(self):
        self.well.deleteLater()
        Base.tearDown(self)

    def labels(self, index=None):
        return [row[0] for row in self.well.context_actions(index) if row]

    def act(self, label, index=None):
        dict(row for row in self.well.context_actions(index) if row)[label]()

    def test_cards_stack_in_a_column_and_the_last_dropped_is_active(self):
        pw = self.posewell
        self.assertEqual((self.well.path, self.well.context_actions()), ("", []))
        self.well.take("C:/lib/sword.pose")
        self.well.take("C:/lib/goblin.pose")
        self.assertEqual([r[0] for r in self.well.rows], ["C:/lib/sword.pose", "C:/lib/goblin.pose"])
        self.assertEqual((self.well.path, self.well.name), ("C:/lib/goblin.pose", "goblin"))
        self.assertEqual(self.well.height_for(300), pw.well_height(2))
        self.well.take("C:/lib/sword.pose")                       # already in it: made active, not doubled
        self.assertEqual(len(self.well.rows), 2)
        self.assertEqual(self.well.path, "C:/lib/sword.pose")

    def test_a_click_picks_the_card_and_the_active_one_again_does_nothing(self):
        self.well.take("C:/lib/sword.pose")
        self.well.take("C:/lib/goblin.pose")
        self.assertEqual(self.well.pick(0), "pose card C:/lib/sword.pose")
        self.assertEqual(self.well.path, "C:/lib/sword.pose")
        self.assertIsNone(self.well.pick(0))
        self.assertIsNone(self.well.pick(5))

    def test_the_menu_uses_shows_removes_and_empties(self):
        pw = self.posewell
        self.well.take("C:/lib/sword.pose")
        self.well.take("C:/lib/goblin.pose")
        self.assertEqual(self.labels(0), [pw.USE, pw.SHOW, pw.REMOVE, pw.NONE, pw.REMOVE_ALL])
        self.assertEqual(self.labels(), [pw.NONE, pw.REMOVE_ALL])
        menu = dict(row for row in self.well.context_actions(1) if row)
        self.assertIsNone(menu[pw.USE])                           # the active card
        self.act(pw.SHOW, 0)
        self.assertEqual(self.shown, ["C:/lib/sword.pose"])
        self.act(pw.REMOVE, 1)                                    # the active one: none active
        self.assertEqual(([r[0] for r in self.well.rows], self.well.path), (["C:/lib/sword.pose"], ""))
        self.act(pw.USE, 0)
        self.act(pw.NONE)
        self.assertEqual((len(self.well.rows), self.well.path), (1, ""))
        self.act(pw.REMOVE_ALL)
        self.assertEqual(self.well.rows, [])

    def test_it_paints_empty_lit_and_filled(self):
        self.assertFalse(self.well.grab().toImage().isNull())    # empty
        self.well.set_hot(True)
        self.assertTrue(self.well.hot)
        self.well.take("C:/lib/sword.pose")
        self.well.take("C:/lib/goblin.pose")
        self.assertFalse(self.well.hot)                           # a release unlights it
        self.well.resize(300, self.well.height_for(300))
        self.assertFalse(self.well.grab().toImage().isNull())
