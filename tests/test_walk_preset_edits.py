"""A Walk Builder preset keeps the working walker's own edits - the rig pose's layer, Fix posture, Snap weapon,
Head aim - and puts them back on the working walkers (2026-11-19)."""

import shutil
import tempfile
import unittest
from unittest import mock

from maya_walk import presets
from maya_walk import panel
from maya_walk import scene


EDITS = {"walk": "asd", "fix": {}, "keys": {"cycle": {"turns": {"upperarm_l": [0.1, 0.2, 0.3]}}},
         "posture": True, "snap": None, "head": None}


class Record(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def test_a_preset_keeps_the_edits_without_the_walk_s_name(self):
        presets.save(self.folder, "Hunch", {}, (), "", dict(EDITS))
        kept = presets.edits_of(presets.get(self.folder, "Hunch"))
        self.assertEqual(kept["walk"], "")
        self.assertTrue(kept["posture"])
        self.assertEqual(kept["keys"], EDITS["keys"])

    def test_a_preset_saved_before_keeps_none(self):
        presets.save(self.folder, "Old", {}, (), "")
        self.assertIsNone(presets.edits_of(presets.get(self.folder, "Old")))
        self.assertEqual(len(presets.fields(presets.get(self.folder, "Old"))), 3)


class JsonForm(unittest.TestCase):
    def test_parse_names_the_walk_given(self):
        dumped = scene.dump_edits(scene.empty_edits("asd"))
        out = scene.parse_edits(dumped, walk="dw")
        self.assertEqual(out["walk"], "dw")
        self.assertTrue(scene.edits_empty(out))

    def test_no_object_is_no_edits(self):
        self.assertIsNone(scene.parse_edits([1, 2]))

    def test_a_round_trip_keeps_posture(self):
        edits = scene.empty_edits("asd")
        edits["posture"] = True
        self.assertTrue(scene.parse_edits(scene.dump_edits(edits))["posture"])


class Panel(unittest.TestCase):
    def test_save_reads_the_first_working_walker(self):
        edits = scene.empty_edits("asd")
        edits["posture"] = True
        with mock.patch.object(scene, "working", return_value=["|A", "|B"]), \
                mock.patch.object(scene, "edits_of", side_effect=lambda r: edits if r == "|A" else None):
            dumped, root = panel._preset_edits()
        self.assertEqual(root, "|A")
        self.assertTrue(dumped["posture"])

    def test_no_working_walker_keeps_none(self):
        with mock.patch.object(scene, "working", return_value=[]):
            self.assertEqual(panel._preset_edits(), (None, None))

    def test_apply_puts_them_on_every_working_walker_under_its_own_walk(self):
        dumped = scene.dump_edits(dict(scene.empty_edits("asd"), posture=True))
        written = {}
        memos = {"|A": {"walk": "dw"}, "|B": {"walk": "own:1"}}
        with mock.patch.object(scene, "working", return_value=["|A", "|B"]), \
                mock.patch.object(scene, "memo_of", side_effect=lambda r: memos[r]), \
                mock.patch.object(scene, "set_edits", side_effect=lambda r, e: written.__setitem__(r, e)):
            note = panel._put_preset_edits(dumped)
        self.assertEqual(written["|A"]["walk"], "dw")
        self.assertEqual(written["|B"]["walk"], "own:1")
        self.assertTrue(all(e["posture"] for e in written.values()))
        self.assertIn("2 walkers", note)

    def test_an_old_preset_leaves_the_walkers_alone(self):
        with mock.patch.object(scene, "set_edits") as wrote:
            self.assertEqual(panel._put_preset_edits(None), "")
        wrote.assert_not_called()


if __name__ == "__main__":
    unittest.main()
