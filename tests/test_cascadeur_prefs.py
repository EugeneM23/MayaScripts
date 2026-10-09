"""Prefs of the Cascadeur bridge: a JSON file it owns. Stdlib only."""

import os
import shutil
import tempfile
import unittest

from skeldar_cascadeur import prefs


class Prefs(unittest.TestCase):

    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="prefs_")
        self.path = os.path.join(self.folder, "SkeldarAnim", "cascadeur.json")

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def test_missing_file_reads_empty(self):
        self.assertEqual(prefs.load(self.path), {})
        self.assertEqual(prefs.get(self.path, "author", "fallback"), "fallback")

    def test_put_then_get_round_trips(self):
        prefs.put(self.path, "author", "Yevhen")
        self.assertEqual(prefs.get(self.path, "author"), "Yevhen")

    def test_put_keeps_other_keys(self):
        prefs.put(self.path, "author", "A")
        prefs.put(self.path, "target", "/Game/A/B")
        self.assertEqual(prefs.get(self.path, "author"), "A")
        self.assertEqual(prefs.get(self.path, "target"), "/Game/A/B")

    def test_a_broken_file_reads_empty_and_is_not_overwritten_by_get(self):
        os.makedirs(os.path.dirname(self.path))
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write("{not json")
        self.assertEqual(prefs.load(self.path), {})
        self.assertEqual(prefs.get(self.path, "author", "d"), "d")
        with open(self.path, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "{not json")

    def test_a_non_object_file_reads_empty(self):
        os.makedirs(os.path.dirname(self.path))
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write("[1, 2]")
        self.assertEqual(prefs.load(self.path), {})

    def test_a_value_of_another_type_falls_back_to_the_default(self):
        prefs.put(self.path, "author", 42)
        self.assertEqual(prefs.get(self.path, "author", "dflt"), "dflt")

    def test_default_path_is_under_appdata(self):
        self.assertEqual(prefs.default_path(r"C:\Users\x\AppData\Roaming"),
                         os.path.join(r"C:\Users\x\AppData\Roaming",
                                      "SkeldarAnim", "cascadeur.json"))


if __name__ == "__main__":
    unittest.main()
