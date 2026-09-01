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
        repo_root = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "SkeldarAnim")
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


class NodeKey(unittest.TestCase):
    """The key is not only a marker value: it names the aim manifest, which
    reaches cmds.sets, and an optionVar."""

    def test_a_plain_name_is_untouched(self):
        self.assertEqual(catalog.node_key("LongSword_02"), "LongSword_02")

    def test_spaces_and_dots_become_underscores(self):
        self.assertEqual(catalog.node_key("My Sword v1.2"), "My_Sword_v1_2")

    def test_a_leading_digit_gets_a_prefix(self):
        self.assertEqual(catalog.node_key("2handed"), "_2handed")

    def test_non_ascii_is_replaced(self):
        self.assertEqual(catalog.node_key("mech"), "mech")
        self.assertEqual(len(catalog.node_key("\u043c\u0435\u0447")), 3)
        self.assertNotIn("\u043c", catalog.node_key("\u043c\u0435\u0447"))

    def test_empty_becomes_a_usable_name(self):
        self.assertEqual(catalog.node_key(""), "weapon")

    def test_a_dash_is_not_legal_in_a_maya_name(self):
        self.assertEqual(catalog.node_key("two-handed"), "two_handed")


class EntryForPath(unittest.TestCase):

    def test_key_and_label_come_from_the_file_stem(self):
        entry = catalog.entry_for_path("D:/props/Axe_01.FBX", "weapon_r")
        self.assertEqual(entry.key, "Axe_01")
        self.assertEqual(entry.label, "Axe_01")

    def test_the_path_is_kept_verbatim(self):
        entry = catalog.entry_for_path("D:/props/Axe_01.FBX", "weapon_r")
        self.assertEqual(entry.path, "D:/props/Axe_01.FBX")

    def test_the_bone_is_the_callers(self):
        self.assertEqual(
            catalog.entry_for_path("D:/a.fbx", "weapon_l").bone, "weapon_l")

    def test_scale_is_one_never_the_catalogs(self):
        """A scale correction is a fact about one known model; applying the
        sword's to somebody else's file is a surprise nobody asked for."""
        self.assertEqual(catalog.entry_for_path("D:/a.fbx", "weapon_r").scale,
                         1.0)

    def test_a_windows_path_works_too(self):
        entry = catalog.entry_for_path(r"D:\props\Big Axe.fbx", "weapon_r")
        self.assertEqual(entry.key, "Big_Axe")

    def test_missing_answers_for_a_custom_entry_too(self):
        entry = catalog.entry_for_path("C:/nowhere/Axe.fbx", "weapon_r")
        self.assertEqual(catalog.missing(entry), "C:/nowhere/Axe.fbx")


class SwordShipsWithTheTool(unittest.TestCase):
    """The sword resolves next to the container first (repo or installed
    copy alike), the user's legacy absolute path only as fallback."""

    def test_table_path_is_the_shipped_copy(self):
        path = catalog.WEAPONS[0].path
        self.assertTrue(path.endswith("assets/LongSword_02.fbx"), path)
        self.assertTrue(os.path.isfile(path), path)

    def test_shipped_path_uses_forward_slashes(self):
        """The path reaches the FBX plugin through MEL, where a backslash
        starts an escape (module docstring rule)."""
        self.assertNotIn("\\", catalog.WEAPONS[0].path)

    def test_missing_is_empty_for_the_shipped_sword(self):
        self.assertEqual(catalog.missing(catalog.WEAPONS[0]), "")

    def test_falls_back_to_the_legacy_path(self):
        """With no shipped copy on disk the old absolute path returns --
        a machine that predates assets/ keeps working."""
        original = catalog.os.path.isfile
        catalog.os.path.isfile = lambda _p: False
        try:
            path = catalog._sword_path()
        finally:
            catalog.os.path.isfile = original
        self.assertEqual(
            path, "C:/!!!Work/Animations/Sources/LongSword_02.fbx")


class CharacterShipsWithTheTool(unittest.TestCase):
    """The character scene resolves like the sword: the copy next to the
    container first, the user's original file as fallback. The fallback
    keeps the filename's real spelling, typo and all -- it has to match
    the file that is actually on that disk."""

    def test_path_is_the_shipped_copy(self):
        path = catalog.character_path()
        self.assertTrue(path.endswith("assets/Manny_Skeleton.ma"), path)
        self.assertTrue(os.path.isfile(path), path)

    def test_shipped_path_uses_forward_slashes(self):
        self.assertNotIn("\\", catalog.character_path())

    def test_falls_back_to_the_legacy_path(self):
        original = catalog.os.path.isfile
        catalog.os.path.isfile = lambda _p: False
        try:
            path = catalog.character_path()
        finally:
            catalog.os.path.isfile = original
        self.assertEqual(
            path,
            "C:/!!!Work/Animations/Rigs/Characters/Manny_Sckeleton.ma")
