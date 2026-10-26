"""Walk Builder's walk cycle is a Pose Library animation card (2026-10-15): a card read as a walk and a walk
written as a card (maya_walk.cards), the old walk files moved into the library once, the walk file a card is read
into (maya_walk.scene.walk_path), and the card's walk well (maya_walk.panel)."""

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
from maya_walk import scene                    # noqa: E402
from maya_poselib import store                 # noqa: E402


def turn(degrees, x=0.0, y=0.0, z=0.0):
    """A row-vector world matrix: a turn about Y and a place."""
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return np.array([[c, 0, -s, 0], [0, 1, 0, 0], [s, 0, c, 0], [x, y, z, 1]], float)


def walk(frames=5, start=3):
    """A small walk file's dict: root > pelvis > thigh_l, moving and turning frame by frame."""
    names = ["root", "pelvis", "thigh_l"]
    worlds = np.array([[turn(0, 0, 0, 10.0 * f) for f in range(frames)],
                       [turn(5.0 * f, 0, 95, 10.0 * f) for f in range(frames)],
                       [turn(-7.0 * f, 10, 90, 10.0 * f + 1) for f in range(frames)]])
    rest = dict((leaf, [float(v) for v in worlds[i, 0].reshape(16)]) for i, leaf in enumerate(names))
    statics = {"root": {"parent": None, "canonical": "root", "rest": rest["root"]},
               "pelvis": {"parent": "root", "canonical": "pelvis", "rest": rest["pelvis"]},
               "thigh_l": {"parent": "pelvis", "canonical": "thigh_l", "rest": rest["thigh_l"]}}
    return {"names": names, "parents": [-1, 0, 1], "worlds": worlds, "fps": 30.0, "up": [0, 1, 0],
            "name": "stroll", "start": start, "statics": statics}


class Base(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.mkdtemp()
        self.library = os.path.join(self.temp, "library").replace("\\", "/")
        self.walks = os.path.join(self.temp, "walks")
        os.makedirs(self.library)
        os.makedirs(self.walks)

    def tearDown(self):
        shutil.rmtree(self.temp, ignore_errors=True)

    def card(self, data=None, name="stroll"):
        header, frames = cards.card_of_walk(data or walk())
        return store.write(self.library, cards.WALK_FOLDER, name, header, frames=frames)


class RoundTrip(Base):

    def test_a_walk_written_as_a_card_reads_back_as_the_same_walk(self):
        data = walk()
        back = cards.walk_data(self.card(data))
        self.assertEqual(back["names"], data["names"])
        self.assertEqual(back["parents"], data["parents"])
        self.assertEqual((back["fps"], back["start"], back["name"]), (30.0, 3, "stroll"))
        self.assertLess(float(np.abs(back["worlds"] - data["worlds"]).max()), 1e-6)
        self.assertEqual(back["statics"]["thigh_l"]["parent"], "pelvis")
        self.assertEqual(back["statics"]["pelvis"]["rest"], data["statics"]["pelvis"]["rest"])
        clip = wf.clip_of(back, wm)
        self.assertEqual(clip.worlds.shape, (3, 5, 4, 4))

    def test_the_card_is_one_the_library_lists_as_an_animation(self):
        self.card()
        found, broken = store.cards(self.library)
        self.assertEqual([(c.folder, c.name, c.type, c.frames) for c in found],
                         [(cards.WALK_FOLDER, "stroll", "anim", 5)])
        self.assertEqual(broken, [])

    def test_a_pose_card_an_objects_card_or_one_frame_is_refused(self):
        pose = store.write(self.library, "", "Fist", {"format": store.FORMAT, "kind": "character",
                                                       "bones": {}, "members": [], "objects": []})
        with self.assertRaises(cards.Refusal) as raised:
            cards.walk_data(pose)
        self.assertIn("pose card", str(raised.exception))
        header, frames = cards.card_of_walk(walk())
        header["kind"] = "objects"
        objects = store.write(self.library, "", "Cubes", header, frames=frames)
        with self.assertRaises(cards.Refusal):
            cards.walk_data(objects)
        short = walk(frames=1)
        with self.assertRaises(cards.Refusal) as raised:
            cards.walk_data(self.card(short, name="still"))
        self.assertIn("one frame", str(raised.exception))

    def test_the_time_unit_both_ways(self):
        self.assertEqual(cards.unit_of(24), "film")
        self.assertEqual(cards.fps_of("film"), 24.0)
        self.assertEqual(cards.fps_of(cards.unit_of(29.97)), 29.97)
        self.assertEqual(cards.fps_of("nonsense"), 30.0)


class Migrate(Base):

    def test_old_walks_become_cards_once(self):
        data = walk()
        clip = wf.clip_of(data, wm)
        wf.save(wf.path_for(self.walks, "asd"), clip, data["statics"], data["start"])
        self.assertEqual(cards.migrate_walks(self.walks, self.library), ["asd"])
        card = os.path.join(self.library, cards.WALK_FOLDER, "asd.anim")
        self.assertLess(float(np.abs(cards.walk_data(card)["worlds"] - data["worlds"]).max()), 1e-6)
        self.assertEqual(cards.walk_card("asd"), cards.WALK_FOLDER + "/asd.anim")
        self.assertEqual(cards.migrate_walks(self.walks, self.library), [])
        shutil.rmtree(card)                                      # deleted by the animator: not made again
        self.assertEqual(cards.migrate_walks(self.walks, self.library), [])
        self.assertTrue(os.path.exists(wf.path_for(self.walks, "asd")))     # the file stays


class CardCache(Base):
    """scene.walk_path: a card read into a walk file of its own, read again when the card changes."""

    def setUp(self):
        Base.setUp(self)
        self.saved = (scene.folder, scene.wcards.library_root, scene._cmds, scene._state)
        state = {"loaded": {}}
        scene.folder = lambda: self.walks
        scene.wcards.library_root = lambda cmds=None: self.library
        scene._cmds = lambda: None
        scene._state = lambda: state

    def tearDown(self):
        scene.folder, scene.wcards.library_root, scene._cmds, scene._state = self.saved
        Base.tearDown(self)

    def test_the_card_is_read_once_and_again_when_it_changes(self):
        path = self.card()
        name = scene.card_walk(cards.relative(path, self.library))
        self.assertEqual(scene.walk_label(name), "stroll")
        cache = scene.walk_path(name)
        self.assertTrue(cache.startswith(os.path.join(self.walks, scene.CARD_CACHE)))
        first = os.path.getmtime(cache)
        self.assertEqual(scene.walk_path(name), cache)
        self.assertEqual(os.path.getmtime(cache), first)            # not written again
        changed = walk()
        changed["worlds"][1, :, 3, 1] += 2.0                          # the pelvis 2 cm higher
        header, frames = cards.card_of_walk(changed)
        store.replace(path, header, frames=frames)
        os.utime(os.path.join(path, store.FRAMES_FILE), (first + 5, first + 5))
        back = wf.load(scene.walk_path(name))
        self.assertAlmostEqual(float(back["worlds"][1, 0, 3, 1]), 97.0, places=5)
        self.assertTrue(scene.walk_exists(name))

    def test_a_migrated_walk_keeps_its_mean_pose_correction(self):
        from maya_walk import meanpose as mp
        data = walk()
        wf.save(wf.path_for(self.walks, "dw"), wf.clip_of(data, wm), data["statics"], data["start"])
        with open(mp.path_for(wf.path_for(self.walks, "dw")), "w") as handle:
            handle.write('{"height": -5.0}')
        cards.migrate_walks(self.walks, self.library)
        cache = scene.walk_path(scene.card_walk(cards.walk_card("dw")))
        with open(mp.path_for(cache)) as handle:
            self.assertEqual(handle.read(), '{"height": -5.0}')

    def test_a_card_gone_keeps_the_walk_it_gave_and_none_is_refused(self):
        path = self.card()
        name = scene.card_walk(cards.relative(path, self.library))
        cache = scene.walk_path(name)
        shutil.rmtree(path)
        self.assertEqual(scene.walk_path(name), cache)
        never = scene.card_walk(cards.WALK_FOLDER + "/never.anim")
        self.assertFalse(scene.walk_exists(never))
        with self.assertRaises(scene.Refusal):
            scene.walk_path(never)
        self.assertEqual(scene.walk_label("asd"), "asd")


class Panel(unittest.TestCase):
    """The walk well's presses on the card's fake cmds (test_walk_panel's)."""

    def setUp(self):
        from tests import test_walk_panel as tp
        self.tp = tp
        self.case = tp.CardTests("test_the_card")
        self.case.setUp()
        self.panel = tp.panel
        self.fake = self.case.fake
        self.library = self.case.library

    def tearDown(self):
        self.case.tearDown()

    def write(self, name):
        header, frames = cards.card_of_walk(walk())
        return store.write(self.library, cards.WALK_FOLDER, name, header, frames=frames)

    def test_cards_stack_and_the_active_one_is_what_pick_puts_on(self):
        panel = self.panel
        panel.build_panel()
        stroll, run = self.write("stroll"), self.write("run")
        panel.take_walk_card(stroll)
        line = panel.take_walk_card(run)
        self.assertIn("walk run", line)
        self.assertEqual(panel.walk_list(), [cards.WALK_FOLDER + "/stroll.anim", cards.WALK_FOLDER + "/run.anim"])
        self.assertEqual(panel.chosen_walk(), scene.card_walk(cards.WALK_FOLDER + "/run.anim"))
        self.assertEqual([r[4] for r in panel.walk_rows()], [False, True])
        self.fake.selection = ["|root"]
        panel.press_apply()
        self.assertEqual(self.case.applied[-1][1], scene.card_walk(cards.WALK_FOLDER + "/run.anim"))
        panel.take_walk_card(stroll)                              # a click on it: the walker keyed with it at once
        self.assertEqual(self.case.applied[-1][1], scene.card_walk(cards.WALK_FOLDER + "/stroll.anim"))
        self.assertNotIn("tempo", self.case.applied[-1][5]["changes"])     # at the card's own tempo
        panel.press_apply()                                       # and Pick keeps putting the chosen card on
        self.assertEqual(self.case.applied[-1][1], scene.card_walk(cards.WALK_FOLDER + "/stroll.anim"))
        self.assertEqual(len(panel.walk_list()), 2)

    def test_taking_a_card_out_puts_its_walkers_back_on_their_own_animation(self):
        panel = self.panel
        panel.build_panel()
        stroll, run = self.write("stroll"), self.write("run")
        panel.take_walk_card(stroll)
        self.case.keyed = {"|a"}                                  # a carries its own clip; b nothing
        self.fake.selection = ["|a", "|b"]
        panel.press_apply()
        card = scene.card_walk(cards.WALK_FOLDER + "/stroll.anim")
        self.assertEqual([a[1] for a in self.case.applied[-2:]], [card, card])
        self.fake.selection = []
        line = panel.remove_walk_card(stroll)
        self.assertEqual(self.case.applied[-1][:2], ("|a", scene.OWN + "a"))   # back on its own clip
        self.assertEqual(self.case.memos["|b"]["walk"], card)                 # nothing to go back to
        self.assertIn("back on their own animation: a", line)
        self.assertIn("no animation of their own to go back to (keep the card's keys): b", line)

    def test_a_tempo_set_on_one_cycle_is_the_same_ratio_on_another(self):
        panel = self.panel
        panel.build_panel()
        own = self.case.own
        self.case.release("tempo", 0.8 * own["tempo"])            # set while asd is the active cycle
        self.fake.vars[panel.OPTION + "walk"] = "dw"              # the active cycle changed some other way
        self.fake.selection = ["|root"]
        panel.press_apply()
        self.assertEqual(self.case.applied[-1][1], "dw")
        kind, x = self.case.applied[-1][5]["changes"]["tempo"]
        self.assertEqual(kind, "ratio")
        self.assertAlmostEqual(x, 0.8, places=9)                   # dw from its own tempo, never another's frames

    def test_a_pose_card_is_refused_by_the_walk_well(self):
        pose = self.tp.write_card(self.library, "", "goblin")
        self.assertIn("pose card", self.panel.take_walk_card(pose))
        self.assertEqual(self.panel.walk_list(), [])

    def test_removing_the_active_card_moves_on_to_the_next(self):
        panel = self.panel
        stroll, run = self.write("stroll"), self.write("run")
        panel.take_walk_card(stroll)
        panel.take_walk_card(run)
        self.assertIn("taken out of the walk well", panel.remove_walk_card(run))
        self.assertEqual(panel.chosen_walk(), scene.card_walk(cards.WALK_FOLDER + "/stroll.anim"))
        panel.remove_all_walk_cards()
        self.assertEqual(panel.walk_list(), [])
        with self.assertRaises(scene.Refusal):                   # an empty well is no walk (never a saved file)
            panel.chosen_walk()

    def test_a_walk_remembered_by_name_means_its_migrated_card(self):
        self.write("dw")
        self.fake.vars[self.panel.OPTION + "walk"] = "dw"
        self.assertEqual(self.panel.chosen_walk(), scene.card_walk(cards.WALK_FOLDER + "/dw.anim"))


if __name__ == "__main__":
    unittest.main()
