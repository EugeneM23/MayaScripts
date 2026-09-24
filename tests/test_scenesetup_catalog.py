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

    def test_holds_the_spear_too(self):
        """2026-09-08: the animator's Spear1, exported onto the sword's axes
        (shaft +Y with the head at +Y, blade width X, thickness Z)."""
        entry = catalog.by_key("Spear_01")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.label, "Spear 01")
        self.assertEqual(entry.bone, "weapon_r")
        self.assertEqual(entry.scale, 1.0)
        self.assertTrue(entry.path.endswith("assets/Spear_01.fbx"), entry.path)
        self.assertTrue(os.path.isfile(entry.path), entry.path)
        self.assertEqual(catalog.missing(entry), "")

    def test_the_spear_has_no_legacy_home(self):
        """No animator's folder to fall back to: with the shipped copy gone
        the table still names the shipped path, and `missing` says so."""
        original = catalog.os.path.isfile
        catalog.os.path.isfile = lambda _p: False
        try:
            path = catalog._asset_path("Spear_01.fbx")
        finally:
            catalog.os.path.isfile = original
        self.assertTrue(path.endswith("assets/Spear_01.fbx"), path)

    def test_the_dropdown_order_is_sword_then_spear(self):
        self.assertEqual(catalog.labels(),
                         ["Long Sword 02", "Spear 01", "Dagger 01", "Hunter Sword"])

    def test_the_hunter_sword_is_the_fourth_row(self):
        """2026-09-24: the Hunter's own sword out of its rig, on the catalog's
        axes -- blade +Y, guard X, thickness Z -- and on weapon_r like every
        weapon, at its natural size."""
        entry = catalog.by_key("Hunter_Sword")
        self.assertEqual((entry.label, entry.bone, entry.scale), ("Hunter Sword", "weapon_r", 1.0))
        self.assertTrue(entry.path.endswith("assets/Hunter_Sword.fbx"), entry.path)
        self.assertFalse(catalog.missing(entry))

    def test_the_dagger_is_the_third_row(self):
        """2026-09-17: the animator's Dagger.fbx, on the sword's axes."""
        entry = catalog.by_key("Dagger_01")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.label, "Dagger 01")
        self.assertEqual(entry.bone, "weapon_r")
        #  the model is 114 cm; the animator wants it 2.5 times smaller
        self.assertEqual(entry.scale, 0.4)
        self.assertTrue(entry.path.endswith("assets/Dagger_01.fbx"), entry.path)
        self.assertFalse(catalog.missing(entry))

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


class CharacterTable(unittest.TestCase):
    """A table since 2026-09-01, so a third skeleton is a row rather than a
    branch. The animator's packs (Longsword/SwordAnimsetPro, ~1200 clips)
    all run on UE4_Mannequin, which is what the second row is for."""

    def test_the_rig_is_first_and_marked_as_a_rig(self):
        """2026-09-07: Add Character adds the AdvancedSkeleton rig; the
        dropdown opens on it."""
        entry = catalog.CHARACTERS[0]
        self.assertEqual(entry.key, "Manny_Rig")
        self.assertEqual(entry.kind, "rig")
        self.assertIn("[rig]", entry.label)
        self.assertEqual(entry.file, "Manny_Rig.ma")
        self.assertTrue(entry.legacy.endswith("Manny_rig_02.ma"))
        self.assertIs(catalog.default_rig(), entry)
        self.assertTrue(catalog.is_rig(entry))

    def test_the_skeletons_are_marked_as_skeletons(self):
        for key in ("Manny", "UE4_Mannequin"):
            entry = catalog.character_by_key(key)
            self.assertEqual(entry.kind, "skeleton", key)
            self.assertIn("[skeleton]", entry.label)
            self.assertFalse(catalog.is_rig(entry))

    def test_the_default_character_is_still_the_skeleton(self):
        """`character_path()` with no argument has always meant the Manny
        SKELETON, whatever row the dropdown opens on."""
        self.assertEqual(catalog.default_character().key, "Manny")
        self.assertIsNot(catalog.default_character(), catalog.CHARACTERS[0])

    def test_the_ue4_mannequin_is_there(self):
        entry = catalog.character_by_key("UE4_Mannequin")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.file, "UE4_Mannequin.fbx")

    def test_labels_are_unique_and_in_table_order(self):
        labels = catalog.character_labels()
        self.assertEqual(len(labels), len(set(labels)))
        self.assertEqual(labels,
                         [entry.label for entry in catalog.CHARACTERS])

    def test_keys_are_unique(self):
        keys = [entry.key for entry in catalog.CHARACTERS]
        self.assertEqual(len(keys), len(set(keys)))

    def test_lookup_by_label_and_by_key_agree(self):
        for entry in catalog.CHARACTERS:
            self.assertIs(catalog.character_by_label(entry.label), entry)
            self.assertIs(catalog.character_by_key(entry.key), entry)

    def test_an_unknown_name_is_none_rather_than_a_guess(self):
        self.assertIsNone(catalog.character_by_label("Sevarog"))
        self.assertIsNone(catalog.character_by_key("Sevarog"))
        self.assertIsNone(catalog.character_by_label(""))

    def test_every_entry_ships_in_assets(self):
        for entry in catalog.CHARACTERS:
            path = catalog.character_file(entry)
            self.assertTrue(os.path.isfile(path), path)
            self.assertNotIn("\\", path)

    def test_character_path_with_no_argument_still_means_manny(self):
        """maya_skelfit, verify_add_character and three test modules ask
        this question and none of them is about the dropdown."""
        self.assertEqual(catalog.character_path(),
                         catalog.character_file(
                             catalog.character_by_key("Manny")))
        self.assertTrue(catalog.character_path().endswith("Manny_Skeleton.ma"))

    def test_the_shipped_rig_is_the_animators_file_minus_camera1(self):
        """A textual cut, diff-verified when it was made (2026-09-07): the
        rig file minus the leftover `camera1` transform and shape, nothing
        else. The file is 53 MB, so only the two facts that matter are
        pinned: the camera is gone and the rig's own nodes are there."""
        path = catalog.character_file(catalog.default_rig())
        self.assertTrue(path.endswith("assets/Manny_Rig.ma"), path)
        wanted = {'createNode transform -n "Group";': False,
                  'createNode joint -n "root";': False,
                  'createNode objectSet -n "ControlSet";': False,
                  'createNode joint -n "camera_bone" -p "camera_root";': False,
                  'createNode joint -n "weapon_r" -p "hand_r";': False}
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                self.assertNotIn("camera1", line)
                stripped = line.rstrip("\r\n")
                if stripped in wanted:
                    wanted[stripped] = True
        self.assertTrue(all(wanted.values()), wanted)

    def test_character_path_takes_an_entry(self):
        entry = catalog.character_by_key("UE4_Mannequin")
        self.assertTrue(
            catalog.character_path(entry).endswith("UE4_Mannequin.fbx"))

    def test_an_entry_with_no_legacy_still_answers_a_path(self):
        """Only Manny has a legacy file. A missing shipped copy for the
        others must not answer "" and make the refusal read as a bug."""
        entry = catalog.character_by_key("UE4_Mannequin")
        original = catalog.os.path.isfile
        catalog.os.path.isfile = lambda _p: False
        try:
            path = catalog.character_file(entry)
        finally:
            catalog.os.path.isfile = original
        self.assertTrue(path.endswith("UE4_Mannequin.fbx"), path)


class HunterRig(unittest.TestCase):
    """2026-09-24: the Hunter's AdvancedSkeleton rig is the second rig row --
    «добавим хантера как риг в наш плагин». Manny stays the default."""

    def test_the_hunter_rig_is_the_second_row_and_a_rig(self):
        entry = catalog.CHARACTERS[1]
        self.assertEqual((entry.key, entry.label, entry.file, entry.kind),
                         ("Hunter_Rig", "Hunter [rig]", "Hunter_Rig.ma", "rig"))
        self.assertTrue(catalog.is_rig(entry))
        self.assertIs(catalog.default_rig(), catalog.character_by_key("Manny_Rig"))

    def test_the_shipped_hunter_is_the_rig_and_nothing_else(self):
        """Built 2026-09-24 from the animator's scene in mayapy standalone
        (docs/superpowers/plans/make_hunter_rig_asset.py): the rig marked for
        the rotation-only retarget, the skeleton at world level, the meshes in
        the rig's Geometry group -- and not the Manny reference mesh, the
        stray camera, the materialX stack or any script node."""
        path = catalog.character_file(catalog.character_by_key("Hunter_Rig"))
        self.assertTrue(path.endswith("assets/Hunter_Rig.ma"), path)
        wanted = {'createNode transform -n "Group";': False,
                  'createNode joint -n "root";': False,
                  'createNode objectSet -n "ControlSet";': False,
                  'createNode transform -n "Hunter_Body" -p "Geometry";': False,
                  'createNode joint -n "weapon_r" -p "hand_r";': False,
                  'createNode joint -n "weapon_l" -p "hand_l";': False}
        mode = False
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                for banned in ("SKM_Manny_Simple", "camera1", "materialXStack", "Hunter_Sword", "weapon_test",
                               "createNode script", "vaccine", "breed_gene"):
                    self.assertNotIn(banned, line)
                stripped = line.rstrip("\r\n")
                if stripped in wanted:
                    wanted[stripped] = True
                if '".skeldarRetarget"' in line and '"rotation"' in line:
                    mode = True
        self.assertEqual([k for k, v in wanted.items() if not v], [])
        self.assertTrue(mode, "the rig's retarget mark is not in the file")


class HunterSkeleton(unittest.TestCase):
    """2026-09-24: «добавим возможность загрузить не только риг хантера, а и
    чистый скелет» -- the Hunter's second row, like the Manny's."""

    def test_the_hunter_skeleton_is_a_skeleton_row_after_the_manny_one(self):
        entry = catalog.character_by_key("Hunter")
        self.assertEqual((entry.label, entry.file, entry.kind),
                         ("Hunter [skeleton]", "Hunter_Skeleton.ma", "skeleton"))
        self.assertFalse(catalog.is_rig(entry))
        keys = [e.key for e in catalog.CHARACTERS]
        self.assertEqual(keys.index("Hunter"), keys.index("Manny") + 1)
        self.assertEqual(catalog.default_character().key, "Manny")

    def test_the_shipped_skeleton_carries_nothing_of_the_rig(self):
        """Built from Hunter_Rig.ma by make_hunter_skeleton_asset.py: the
        skeleton at world level, the meshes in `|Hunter` -- and no rig group,
        no control set, no fit skeleton, no retarget mark, no script node."""
        path = catalog.character_file(catalog.character_by_key("Hunter"))
        self.assertTrue(path.endswith("assets/Hunter_Skeleton.ma"), path)
        wanted = {'createNode joint -n "root";': False,
                  'createNode transform -n "Hunter";': False,
                  'createNode transform -n "Hunter_Body" -p "Hunter";': False,
                  'createNode joint -n "weapon_r" -p "hand_r";': False,
                  'createNode joint -n "weapon_l" -p "hand_l";': False}
        skins = 0
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                for banned in ('createNode transform -n "Group"', "ControlSet", "FitSkeleton",
                               "MoCapConstraints", "skeldarRetarget", "SKM_Manny_Simple", "Hunter_Sword", "weapon_test",
                               "createNode script", "vaccine", "breed_gene"):
                    self.assertNotIn(banned, line)
                stripped = line.rstrip("\r\n")
                if stripped in wanted:
                    wanted[stripped] = True
                if line.startswith("createNode skinCluster "):
                    skins += 1
        self.assertEqual([k for k, v in wanted.items() if not v], [])
        self.assertEqual(skins, 5)
