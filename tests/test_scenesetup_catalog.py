"""Tests for the weapon table.

It is pure data with lookups over it, so it needs neither Maya nor Qt -- and
the first test here is what keeps it that way.
"""

import os
import subprocess
import sys
import unittest

from maya_scenesetup import catalog


class MayaFreeBoundary(unittest.TestCase):
    """catalog must stay importable with no Maya and no Qt loaded.

    Checked in a fresh interpreter: by the time the rest of the suite has run,
    maya.cmds is already in this process's sys.modules.
    """

    def test_importing_catalog_pulls_in_neither_maya_nor_qt(self):
        script = (
            "import sys\n"
            "from maya_scenesetup import catalog\n"
            "leaked = [m for m in sys.modules\n"
            "          if m.startswith('maya.') or m.startswith('PySide6')]\n"
            "print(';'.join(sorted(leaked)))\n"
        )
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=repo_root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "",
                         "importing catalog leaked: " + result.stdout.strip())


class Table(unittest.TestCase):

    def test_holds_the_long_sword(self):
        entry = catalog.by_key("LongSword_02")
        self.assertIsNotNone(entry)
        self.assertTrue(entry.path.endswith("LongSword_02.fbx"))

    def test_the_sword_goes_to_the_right_hand(self):
        self.assertEqual(catalog.by_key("LongSword_02").bone, "weapon_r")

    def test_paths_use_forward_slashes(self):
        """A backslash starts an escape in the MEL the FBX plugin sees."""
        for entry in catalog.WEAPONS:
            self.assertNotIn("\\", entry.path, entry.key)

    def test_keys_are_unique(self):
        keys = [entry.key for entry in catalog.WEAPONS]
        self.assertEqual(len(keys), len(set(keys)))

    def test_labels_are_unique(self):
        """The dropdown resolves a pick by its label, so duplicates would hide
        an entry the animator can see."""
        found = catalog.labels()
        self.assertEqual(len(found), len(set(found)))

    def test_labels_are_in_table_order(self):
        self.assertEqual(catalog.labels(),
                         [entry.label for entry in catalog.WEAPONS])


class Lookups(unittest.TestCase):

    def test_by_label_finds_the_entry(self):
        entry = catalog.WEAPONS[0]
        self.assertIs(catalog.by_label(entry.label), entry)

    def test_by_label_is_none_for_a_stranger(self):
        self.assertIsNone(catalog.by_label("Halberd"))

    def test_by_key_is_none_for_a_stranger(self):
        self.assertIsNone(catalog.by_key("Halberd"))


class OnDisk(unittest.TestCase):

    def test_missing_names_the_path_that_is_not_there(self):
        entry = catalog.Weapon("X", "X", "C:/nowhere/X.fbx", "weapon_r", 1.0)
        self.assertEqual(catalog.missing(entry), "C:/nowhere/X.fbx")

    def test_missing_is_empty_for_a_file_that_exists(self):
        here = os.path.abspath(__file__).replace("\\", "/")
        entry = catalog.Weapon("X", "X", here, "weapon_r", 1.0)
        self.assertEqual(catalog.missing(entry), "")
