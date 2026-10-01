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
                         ["Long Sword 02", "Spear 01", "Spear 03", "Dagger 01",
                          "Creep Sword"])

    def test_spear_03_ships_with_its_texture(self):
        """2026-09-28, «это должно выдаваться сразу с текстурой»: the first
        row that arrives in an image rather than a palette colour."""
        entry = catalog.by_key("Spear_03")
        self.assertEqual((entry.label, entry.bone, entry.scale, entry.frame),
                         ("Spear 03", "weapon_r", 1.0, (0.0, 0.0, 0.0)))
        self.assertTrue(entry.path.endswith("assets/Spear_03.fbx"), entry.path)
        self.assertTrue(entry.texture.endswith("assets/Spear_03.png"),
                        entry.texture)
        self.assertNotIn("\\", entry.texture)
        self.assertFalse(catalog.missing(entry))

    def test_only_spear_03_is_textured(self):
        for entry in catalog.WEAPONS:
            if entry.key != "Spear_03":
                self.assertEqual(entry.texture, "", entry.key)
        self.assertEqual(
            catalog.entry_for_path("C:/x/Axe.fbx", "weapon_r").texture, "")
        self.assertEqual(
            catalog.Weapon("X", "X", "C:/x.fbx", "weapon_r", 1.0).texture, "")

    def test_a_missing_texture_is_named_like_a_missing_model(self):
        entry = catalog.by_key("Spear_03")._replace(
            texture="C:/nowhere/Spear_03.png")
        self.assertEqual(catalog.missing(entry), "C:/nowhere/Spear_03.png")

    def test_the_creep_sword_is_the_fourth_row(self):
        """2026-09-24: the Creep's own sword out of its rig, on the catalog's
        axes -- blade +Y, guard X, thickness Z -- and on weapon_r like every
        weapon, at its natural size."""
        entry = catalog.by_key("Creep_Sword")
        self.assertEqual((entry.label, entry.bone, entry.scale), ("Creep Sword", "weapon_r", 1.0))
        self.assertTrue(entry.path.endswith("assets/Creep_Sword.fbx"), entry.path)
        self.assertFalse(catalog.missing(entry))

    def test_only_the_creep_sword_stands_in_a_frame_of_its_own(self):
        """2026-09-24, «чтобы оси соответствовали направлению геометрии, но при этом меч
        сохранил свою позу в руке»: the 45 the Creep holds it at is the row's FRAME, not
        its points; every other row -- and a file off the FBX field -- is on the bone's
        axes, and a row written without the column reads as the identity."""
        self.assertEqual(catalog.by_key("Creep_Sword").frame, (0.0, 45.0, 0.0))
        for entry in catalog.WEAPONS:
            if entry.key != "Creep_Sword":
                self.assertEqual(entry.frame, (0.0, 0.0, 0.0), entry.key)
        self.assertEqual(catalog.entry_for_path("C:/x/Axe.fbx", "weapon_r").frame, (0.0, 0.0, 0.0))
        self.assertEqual(catalog.Weapon("X", "X", "C:/x.fbx", "weapon_r", 1.0).frame, (0.0, 0.0, 0.0))

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
    """The sword resolves next to the container (repo or installed copy
    alike) and nowhere else: the animator's Animations/ fallback went on
    2026-09-28 («все нужные файлы ... в папку плагина»)."""

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

    def test_a_missing_shipped_copy_is_named_never_replaced(self):
        """No fallback outside the plugin: with the shipped copy gone the
        path is still the shipped one, and `missing` names it."""
        original = catalog.os.path.isfile
        catalog.os.path.isfile = lambda _p: False
        try:
            path = catalog._asset_path("LongSword_02.fbx")
        finally:
            catalog.os.path.isfile = original
        self.assertTrue(path.endswith("assets/LongSword_02.fbx"), path)
        self.assertNotIn("Animations", path)


class CharacterShipsWithTheTool(unittest.TestCase):
    """The character scene resolves like the sword: the copy next to the
    container and nowhere else. The fallback it had to the animator's
    original -- typo, vaccine and all -- went on 2026-09-28."""

    def test_path_is_the_shipped_copy(self):
        path = catalog.character_path()
        self.assertTrue(path.endswith("assets/Manny_Skeleton.ma"), path)
        self.assertTrue(os.path.isfile(path), path)

    def test_shipped_path_uses_forward_slashes(self):
        self.assertNotIn("\\", catalog.character_path())

    def test_a_missing_shipped_copy_is_named_never_replaced(self):
        original = catalog.os.path.isfile
        catalog.os.path.isfile = lambda _p: False
        try:
            path = catalog.character_path()
        finally:
            catalog.os.path.isfile = original
        self.assertTrue(path.endswith("assets/Manny_Skeleton.ma"), path)
        self.assertNotIn("Sckeleton", path)


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
        #  its source, Manny_rig_02.ma, is in sources/manny/ (2026-09-28)
        self.assertFalse(hasattr(entry, "legacy"))
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

    def test_a_missing_copy_still_answers_a_path(self):
        """A missing shipped copy must not answer "" and make the refusal
        read as a bug."""
        entry = catalog.character_by_key("UE4_Mannequin")
        original = catalog.os.path.isfile
        catalog.os.path.isfile = lambda _p: False
        try:
            path = catalog.character_file(entry)
        finally:
            catalog.os.path.isfile = original
        self.assertTrue(path.endswith("UE4_Mannequin.fbx"), path)


class CreepRig(unittest.TestCase):
    """2026-09-24: the Creep's AdvancedSkeleton rig is the second rig row --
    «добавим хантера как риг в наш плагин». Manny stays the default."""

    def test_the_creep_rig_is_the_second_row_and_a_rig(self):
        entry = catalog.CHARACTERS[1]
        self.assertEqual((entry.key, entry.label, entry.file, entry.kind),
                         ("Creep_Rig", "Creep [rig]", "Creep_Rig.ma", "rig"))
        self.assertTrue(catalog.is_rig(entry))
        self.assertIs(catalog.default_rig(), catalog.character_by_key("Manny_Rig"))

    def test_the_shipped_creep_is_the_rig_and_nothing_else(self):
        """Built 2026-09-24 from the animator's scene in mayapy standalone
        (docs/superpowers/plans/make_creep_rig_asset.py): the rig marked for
        the rotation-only retarget, the meshes in the rig's Geometry group, and
        since 2026-09-28 the skeleton in the layout of the Creep's own FBX --
        `root` under a Null `Armature` («как в файле, единообразно», «и риг
        крипа тоже»; make_creep_armature_layout.py) -- and not the Manny
        reference mesh, the stray camera, the materialX stack or any script node."""
        path = catalog.character_file(catalog.character_by_key("Creep_Rig"))
        self.assertTrue(path.endswith("assets/Creep_Rig.ma"), path)
        wanted = {'createNode transform -n "Group";': False,
                  'createNode transform -n "Armature";': False,
                  'createNode joint -n "root" -p "Armature";': False,
                  'createNode objectSet -n "ControlSet";': False,
                  'createNode transform -n "Creep_Body" -p "Geometry";': False,
                  'createNode joint -n "weapon_r" -p "hand_r";': False,
                  'createNode joint -n "weapon_l" -p "hand_l";': False}
        mode = False
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                for banned in ("SKM_Manny_Simple", "camera1", "materialXStack", "Creep_Sword", "weapon_test",
                               "createNode script", "vaccine", "breed_gene", "Hunter", "Hanter"):
                    self.assertNotIn(banned, line)
                stripped = line.rstrip("\r\n")
                if stripped in wanted:
                    wanted[stripped] = True
                if '".skeldarRetarget"' in line and '"rotation"' in line:
                    mode = True
        self.assertEqual([k for k, v in wanted.items() if not v], [])
        self.assertTrue(mode, "the rig's retarget mark is not in the file")


class CreepSkeleton(unittest.TestCase):
    """2026-09-24: «добавим возможность загрузить не только риг хантера, а и
    чистый скелет» -- the Creep's second row, like the Manny's."""

    def test_the_creep_skeleton_is_a_skeleton_row_after_the_manny_one(self):
        entry = catalog.character_by_key("Creep")
        self.assertEqual((entry.label, entry.file, entry.kind),
                         ("Creep [skeleton]", "Creep_Skeleton.ma", "skeleton"))
        self.assertFalse(catalog.is_rig(entry))
        keys = [e.key for e in catalog.CHARACTERS]
        self.assertEqual(keys.index("Creep"), keys.index("Manny") + 1)
        self.assertEqual(catalog.default_character().key, "Manny")

    def test_the_shipped_skeleton_carries_nothing_of_the_rig(self):
        """Built from Creep_Rig.ma by make_creep_skeleton_asset.py, and since
        2026-09-28 in the layout of the Creep's own FBX (make_creep_armature_layout.py):
        `root` under a Null `Armature`, the five meshes at the top of the scene
        beside it -- and no rig group, no control set, no fit skeleton, no
        retarget mark, no script node."""
        path = catalog.character_file(catalog.character_by_key("Creep"))
        self.assertTrue(path.endswith("assets/Creep_Skeleton.ma"), path)
        wanted = {'createNode transform -n "Armature";': False,
                  'createNode joint -n "root" -p "Armature";': False,
                  'createNode transform -n "Creep_Body";': False,
                  'createNode joint -n "weapon_r" -p "hand_r";': False,
                  'createNode joint -n "weapon_l" -p "hand_l";': False}
        skins = 0
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                for banned in ('createNode transform -n "Group"', 'createNode transform -n "Creep";',
                               "ControlSet", "FitSkeleton",
                               "MoCapConstraints", "skeldarRetarget", "SKM_Manny_Simple", "Creep_Sword", "weapon_test",
                               "createNode script", "vaccine", "breed_gene", "Hunter", "Hanter"):
                    self.assertNotIn(banned, line)
                stripped = line.rstrip("\r\n")
                if stripped in wanted:
                    wanted[stripped] = True
                if line.startswith("createNode skinCluster "):
                    skins += 1
        self.assertEqual([k for k, v in wanted.items() if not v], [])
        self.assertEqual(skins, 5)


ORC_SOURCE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "sources", "orc", "Orc_Rig.ma")


class OrcRig(unittest.TestCase):
    """2026-09-25: «В открытом проекте в Unreal есть персонаж SK_Orc_Marauder_F ... добавим к нам в
    проект еще один риг "ORC"» -- the third rig row until 2026-09-28, when it left the plugin
    («орка без текстур уберем из плагина он больше не нужен»). Its file stays in sources/orc/ as
    what the textured Orc D is built from, and these tests pin that file."""

    def test_the_untextured_orc_left_the_plugin(self):
        self.assertIsNone(catalog.character_by_key("Orc_Rig"))
        self.assertNotIn("Orc [rig]", catalog.character_labels())
        self.assertFalse(os.path.exists(os.path.join(os.path.dirname(catalog.character_file(
            catalog.default_rig())), "Orc_Rig.ma")))
        self.assertTrue(os.path.isfile(ORC_SOURCE), ORC_SOURCE)
        self.assertIs(catalog.default_rig(), catalog.character_by_key("Manny_Rig"))

    def test_the_orc_source_is_the_rig_with_manny_s_helper_bones(self):
        """Built in mayapy standalone from the animator's own FBX export of the
        Unreal asset (make_orc_source.py -> rebuild_orc_rig.py -> make_orc_rig_asset.py):
        the rig marked for the rotation-only retarget, one mesh in the rig's
        Geometry group with its skin and blendShape, the four helper bones Manny
        has (the animator: «все четыре») and the shoulder pads -- and none of the
        LODs, the dead-path texture or any script node."""
        path = ORC_SOURCE
        wanted = {'createNode transform -n "Group";': False,
                  'createNode joint -n "root";': False,
                  'createNode objectSet -n "ControlSet";': False,
                  'createNode transform -n "Orc_Body" -p "Geometry";': False,
                  'createNode joint -n "camera_root" -p "root";': False,
                  'createNode joint -n "camera_bone" -p "camera_root";': False,
                  'createNode joint -n "weapon_r" -p "hand_r";': False,
                  'createNode joint -n "weapon_l" -p "hand_l";': False,
                  'createNode joint -n "AB_Armor_Shoulder_L" -p "clavicle_l";': False,
                  'createNode joint -n "AB_Armor_Shoulder_R" -p "clavicle_r";': False}
        mode, skins, blends = False, 0, 0
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                for banned in ("createNode script", "vaccine", "breed_gene", "SK_Orc_Marauder_F_LOD1",
                               "LodGroup", "D:/Characters", "camera1", "arp_rig_name", "flip_fluid", "ori_name"):
                    self.assertNotIn(banned, line)
                stripped = line.rstrip("\r\n")
                if stripped in wanted:
                    wanted[stripped] = True
                if '".skeldarRetarget"' in line and '"rotation"' in line:
                    mode = True
                skins += line.startswith("createNode skinCluster ")
                blends += line.startswith("createNode blendShape ")
        self.assertEqual([k for k, v in wanted.items() if not v], [])
        self.assertTrue(mode, "the rig's retarget mark is not in the file")
        self.assertEqual((skins, blends), (1, 1))


class ExportName(unittest.TestCase):
    """2026-09-25: the wrapper over `root` in an exported FBX was named for the character
    in the morning («по персонажу») and is `Armature` since the evening
    (maya_uebridge.fbxlayout.WRAPPER_NAME) -- the catalog no longer names it."""

    def test_the_catalog_names_no_wrapper(self):
        self.assertFalse(hasattr(catalog, "export_name"))

    def test_every_character_key_is_listed(self):
        self.assertEqual(catalog.character_keys(), [c.key for c in catalog.CHARACTERS])


class OrcD(unittest.TestCase):
    """2026-09-28: «Давай добавим еще один вариант орка но на этот раз SK_Orc_Marauder_D ... и для
    этой версии сделаем материал с текстурами» -- the fourth rig row, the first CHARACTER that
    arrives in its textures. Its skeleton is the F orc's to 0.0, so the asset is Orc_Rig.ma with
    D's mesh re-skinned onto the same game joints (make_orc_d_rig_asset.py). The third row since the
    untextured «Orc [rig]» left the plugin the same day."""

    MAPS = ("Orc_D_Body_Color.jpg", "Orc_D_Body_Normal.jpg", "Orc_D_Cloth_Color.jpg",
            "Orc_D_Cloth_Normal.jpg", "Orc_D_Cloth_Mask.png", "Orc_D_Eye_Color.jpg")

    def test_the_third_row_is_the_textured_orc_d_rig(self):
        entry = catalog.CHARACTERS[2]
        self.assertEqual((entry.key, entry.label, entry.file, entry.kind),
                         ("Orc_D_Rig", "Orc D [rig]", "Orc_D_Rig.ma", "rig"))
        self.assertTrue(entry.textured)
        self.assertTrue(catalog.is_rig(entry))

    def test_every_row_but_the_ue4_mannequin_is_textured(self):
        """The Orc D since 2026-09-28, both Manny rows and both Creep rows since 2026-09-30."""
        self.assertEqual([c.key for c in catalog.CHARACTERS if not c.textured], ["UE4_Mannequin"])

    def test_textured_defaults_to_false(self):
        self.assertFalse(catalog.Character("X", "X", "X.ma", "rig").textured)

    def test_an_asset_path_is_under_assets_with_forward_slashes(self):
        path = catalog.asset_path("Orc_D/Orc_D_Body_Color.jpg")
        self.assertTrue(path.endswith("/assets/Orc_D/Orc_D_Body_Color.jpg"), path)
        self.assertNotIn("\\", path)

    def test_the_maps_ship_in_assets(self):
        for name in self.MAPS:
            self.assertTrue(os.path.isfile(catalog.asset_path("Orc_D/" + name)), name)

    def test_the_shipped_orc_d_names_its_images_relatively(self):
        """Every file node carries `skeldarAssetImage` (the path under assets/) and Add Character
        points it at the installed copy: no path of the machine that built the asset is in it."""
        path = catalog.character_file(catalog.character_by_key("Orc_D_Rig"))
        self.assertTrue(path.endswith("assets/Orc_D_Rig.ma"), path)
        images, files, mode, skins, blends, body, view = [], 0, False, 0, 0, 0, False
        banned = ("createNode script", "vaccine", "breed_gene", "C:/", "c:/", "Unreal Projects",
                  "scratchpad", "Skirt_Proxy", "srcD:", "D:/Characters", "arp_rig_name",
                  "flip_fluid", "ori_name")
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                for word in banned:
                    self.assertNotIn(word, line)
                files += line.startswith("createNode file ")
                if '".skeldarAssetImage"' in line:
                    images.append(line.split('"')[-2])
                if '".skeldarRetarget"' in line and '"rotation"' in line:
                    mode = True
                skins += line.startswith("createNode skinCluster ")
                blends += line.startswith("createNode blendShape ")
                body += line.startswith('createNode transform -n "Orc_D_3P" -p "Geometry";')
                body += line.startswith('createNode transform -n "Orc_D_1P" -p "Geometry";')
                view = view or ('-ln "view"' in line and '-en "3P:1P"' in line)
        self.assertTrue(mode, "the rig's retarget mark is not in the file")
        # the 3P and, since 2026-09-28, the animator's 1P (the 3P without its head), Main's switch
        self.assertEqual(body, 2, "Orc_D_3P and Orc_D_1P are not both in the rig's Geometry group")
        self.assertTrue(view, "Main has no view (3P:1P) switch")
        self.assertEqual((skins, blends), (2, 1))
        self.assertEqual(sorted(set(images)), sorted("Orc_D/" + m for m in self.MAPS))
        self.assertEqual(files, len(images))


class MannyTextured(unittest.TestCase):
    """2026-09-30: «Давай для нашего мени рига и скелета найдем текстуры и добавим их в проект точно
    так же как и для орка». Unreal's UE5 mannequin textures (the Orc Marauder pack's demo copy --
    our meshes' UVs exactly), the base colour as M_Mannequin computes it (the D map itself, the chest
    logo baked into the torso), the bevel normal, at 2048 JPG; both shipped .ma dressed in place by
    make_manny_textured_assets.py, two materials by Unreal's two slots."""

    MAPS = ("Manny_HeadLegs_Color.jpg", "Manny_HeadLegs_Normal.jpg",
            "Manny_Torso_Color.jpg", "Manny_Torso_Normal.jpg")

    def test_both_manny_rows_are_textured(self):
        for key in ("Manny_Rig", "Manny"):
            self.assertTrue(catalog.character_by_key(key).textured, key)

    def test_the_maps_ship_in_assets(self):
        for name in self.MAPS:
            self.assertTrue(os.path.isfile(catalog.asset_path("Manny/" + name)), name)

    def test_the_shipped_mannys_name_their_images_relatively(self):
        """Each asset's four file nodes carry `skeldarAssetImage` and store that same relative
        path; nothing of the dead MI_Manny networks (D:/dev/..., /Users/Shared/...) is left."""
        banned = ("createNode script", "vaccine", "breed_gene", "C:/", "c:/", "D:/", "d:/",
                  "/Users/Shared", "Unreal Projects", "scratchpad", "ueManny:", "MI_Manny",
                  "T_Manny_0", "skeldarColour", "EnvSamplerTex")
        for key in ("Manny_Rig", "Manny"):
            path = catalog.character_file(catalog.character_by_key(key))
            images, stored, files, materials = [], [], 0, []
            with open(path, encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    for word in banned:
                        self.assertNotIn(word, line, key)
                    files += line.startswith("createNode file ")
                    if line.startswith("createNode phong "):
                        materials.append(line.split('"')[1])
                    if '".skeldarAssetImage"' in line:
                        images.append(line.split('"')[-2])
                    if line.startswith('\tsetAttr ".ftn" -type "string"'):
                        stored.append(line.split('"')[-2])
            want = sorted("Manny/" + m for m in self.MAPS)
            self.assertEqual(sorted(images), want, key)
            self.assertEqual(sorted(stored), want, key)
            self.assertEqual(files, 4, key)
            self.assertEqual(sorted(materials), ["skeldarTexture_Manny_HeadLegs",
                                                 "skeldarTexture_Manny_Torso"], key)



class CreepTextured(unittest.TestCase):
    """2026-09-30: «Вот текстуры для крипа давай сделаем тоже самое что и для мени» -- and the whole
    Creep («Весь Крип»): the animator's body colour + normal and head colour, the head's normal and the
    back/arms set out of the Creep's own Cascadeur FBX, whose UVs our meshes carry index for index; three
    sets at 2048 JPG, one material per mesh (make_creep_textured_assets.py dressed both .ma in place)."""

    MAPS = tuple("Creep_%s_%s.jpg" % (k, kind) for k in ("Body", "Face", "Limbs") for kind in ("Color", "Normal"))

    def test_both_creep_rows_are_textured(self):
        for key in ("Creep_Rig", "Creep"):
            self.assertTrue(catalog.character_by_key(key).textured, key)

    def test_the_maps_ship_in_assets(self):
        for name in self.MAPS:
            self.assertTrue(os.path.isfile(catalog.asset_path("Creep/" + name)), name)

    def test_the_shipped_creeps_name_their_images_relatively(self):
        """Six file nodes, each storing the relative path it is marked with; three materials; nothing
        of Cascadeur's paths or the palette materials the assets wore, nor the animator's own path the
        scene they were cut out of left in `fileInfo "exportedFrom"`."""
        banned = ("createNode script", "vaccine", "C:/", "c:/", "D:/", "E:/", "FBXASC", "creep_T-pose",
                  "skeldarColour", "exportedFrom", "scratchpad")
        for key in ("Creep_Rig", "Creep"):
            path = catalog.character_file(catalog.character_by_key(key))
            images, stored, files, materials = [], [], 0, []
            with open(path, encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    for word in banned:
                        self.assertNotIn(word, line, key)
                    files += line.startswith("createNode file ")
                    if line.startswith("createNode phong "):
                        materials.append(line.split('"')[1])
                    if '".skeldarAssetImage"' in line:
                        images.append(line.split('"')[-2])
                    if line.startswith('	setAttr ".ftn" -type "string"'):
                        stored.append(line.split('"')[-2])
            want = sorted("Creep/" + m for m in self.MAPS)
            self.assertEqual(sorted(images), want, key)
            self.assertEqual(sorted(stored), want, key)
            self.assertEqual(files, 6, key)
            self.assertEqual(sorted(materials), ["skeldarTexture_Creep_Body", "skeldarTexture_Creep_Face",
                                                 "skeldarTexture_Creep_Limbs"], key)

class Models(unittest.TestCase):
    """2026-09-30, the portrait grid: one portrait per MODEL, the kind a switch.
    A catalog row is (model, kind)."""

    def test_the_models_in_grid_order(self):
        self.assertEqual([m.key for m in catalog.MODELS],
                         ["Manny", "Creep", "Orc_D", "UE4_Mannequin"])
        self.assertEqual(catalog.model_by_key("Orc_D").label, "Orc D")
        self.assertIsNone(catalog.model_by_key("Sevarog"))

    def test_every_row_names_a_model_and_every_model_has_a_row(self):
        keys = set(m.key for m in catalog.MODELS)
        for entry in catalog.CHARACTERS:
            self.assertIn(entry.model, keys, entry.key)
        for model in catalog.MODELS:
            self.assertTrue(catalog.kinds_of(model.key), model.key)

    def test_a_model_and_a_kind_name_at_most_one_row(self):
        pairs = [(e.model, e.kind) for e in catalog.CHARACTERS]
        self.assertEqual(len(pairs), len(set(pairs)))

    def test_the_pairs(self):
        want = {("Manny", "rig"): "Manny_Rig", ("Manny", "skeleton"): "Manny",
                ("Creep", "rig"): "Creep_Rig", ("Creep", "skeleton"): "Creep",
                ("Orc_D", "rig"): "Orc_D_Rig",
                ("UE4_Mannequin", "skeleton"): "UE4_Mannequin"}
        for (model, kind), key in want.items():
            self.assertEqual(catalog.character_for(model, kind).key, key)
        self.assertIsNone(catalog.character_for("Orc_D", "skeleton"))
        self.assertIsNone(catalog.character_for("UE4_Mannequin", "rig"))
        self.assertEqual(catalog.kinds_of("Orc_D"), ("rig",))
        self.assertEqual(catalog.kinds_of("UE4_Mannequin"), ("skeleton",))
        self.assertEqual(catalog.kinds_of("Manny"), ("rig", "skeleton"))

    def test_the_default_is_the_default_rigs_model(self):
        self.assertEqual(catalog.default_model(), "Manny")
        self.assertIs(catalog.model_of(catalog.default_rig()),
                      catalog.model_by_key("Manny"))

    def test_the_portrait_path(self):
        self.assertTrue(catalog.portrait_path("Creep").endswith(
            "assets/character_portraits/Creep.png"))
        self.assertNotIn("\\", catalog.portrait_path("Creep"))


class Portraits(unittest.TestCase):
    """Every model ships its portrait: a 256 px square PNG with alpha
    (docs/superpowers/plans/make_character_portraits.py renders them)."""

    def test_every_model_has_its_portrait(self):
        for model in catalog.MODELS:
            path = catalog.portrait_path(model.key)
            self.assertTrue(os.path.isfile(path), path)
            with open(path, "rb") as handle:
                head = handle.read(32)
            self.assertEqual(head[:8], b"\x89PNG\r\n\x1a\n", path)
            width = int.from_bytes(head[16:20], "big")
            height = int.from_bytes(head[20:24], "big")
            self.assertEqual((width, height), (256, 256), path)
            self.assertEqual(head[25], 6, "RGBA expected: " + path)


def _main_curve(path):
    """MainShape's `.cc` in a rig's .ma, read as text: (degree, spans, form, cvs).

    Stops at the block, so the 50 MB Manny is read only as far as its Main."""
    tokens = None
    with open(path, encoding="utf-8", errors="replace") as handle:
        inside = False
        for line in handle:
            if not inside:
                inside = line.startswith('createNode nurbsCurve -n "MainShape" -p "Main";')
                continue
            if tokens is None:
                if line.startswith("createNode"):
                    break
                if line.strip().startswith('setAttr ".cc" -type "nurbsCurve"'):
                    tokens = []
                continue
            tokens.extend(line.replace(";", " ; ").split())
            if ";" in tokens:
                break
    if not tokens:
        return None
    values = tokens[:tokens.index(";")]
    degree, spans, form, _rational, dim = int(values[0]), int(values[1]), int(values[2]), values[3], int(values[4])
    knots = int(values[5])
    count = int(values[6 + knots])
    flat = [float(v) for v in values[7 + knots:]]
    cvs = [tuple(flat[i * dim:i * dim + 3]) for i in range(count)]
    return degree, spans, form, cvs


class MainControlSize(unittest.TestCase):
    """Every rig's Main is Manny's circle (2026-09-30, the animator: «Давай сделаем
    размер главного контрола у всех ригов такой же как и у menny»). The Creep's and
    the Orc's were AdvancedSkeleton's default, 7.76 cm -- 5.22x smaller, lost inside
    the feet (make_main_control_size.py, the procedure's `main_size`)."""

    def test_manny_s_main_is_the_reference_circle(self):
        degree, spans, form, cvs = _main_curve(catalog.character_file(catalog.default_rig()))
        self.assertEqual((degree, spans, form, len(cvs)), (3, 8, 2, 11))
        radius = max((x * x + z * z) ** 0.5 for x, _y, z in cvs)
        self.assertAlmostEqual(radius, 40.523612701541616, places=9)
        self.assertLess(max(abs(y) for _x, y, _z in cvs), 1e-9)

    def test_every_rig_s_main_is_manny_s(self):
        reference = _main_curve(catalog.character_file(catalog.default_rig()))
        files = [catalog.character_file(e) for e in catalog.CHARACTERS if catalog.is_rig(e)]
        files.append(ORC_SOURCE)          # what the Orc D is built from
        self.assertGreaterEqual(len(files), 4)
        for path in files:
            curve = _main_curve(path)
            self.assertIsNotNone(curve, path)
            self.assertEqual(curve[:3], reference[:3], path)
            self.assertEqual(len(curve[3]), len(reference[3]), path)
            worst = max(abs(a - b) for cv, ref in zip(curve[3], reference[3]) for a, b in zip(cv, ref))
            self.assertLess(worst, 1e-9, "%s: Main %.4f cm off Manny's" % (path, worst))


def _curve_cvs(path, shape, parent):
    """The CVs of `shape`'s `.cc` in a .ma, read as text (one CV a line, as Maya writes them)."""
    start = 'createNode nurbsCurve -n "%s" -p "%s";' % (shape, parent)
    tokens, inside = None, False
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not inside:
                inside = line.startswith(start)
                continue
            if tokens is None:
                if line.startswith("createNode"):
                    break
                if line.strip().startswith('setAttr ".cc" -type "nurbsCurve"'):
                    tokens = []
                continue
            tokens.extend(line.replace(";", " ; ").split())
            if ";" in tokens:
                break
    if not tokens:
        return None
    values = tokens[:tokens.index(";")]
    dim, knots = int(values[4]), int(values[5])
    count = int(values[6 + knots])
    # the CVs, and only them: since Maya 2022 the data can end in component tags ("gtag" ...)
    flat = [float(v) for v in values[7 + knots:7 + knots + count * dim]]
    return [tuple(flat[i * dim:i * dim + 3]) for i in range(count)]


class ClavicleShoulderSize(unittest.TestCase):
    """The Creep's and the Orc's clavicle and shoulder controls grown to be seen on their bodies
    (2026-09-30, «контролы ключиц плечей не видны они внутри шеометрии тела»; asked, «Увеличить под
    тело»). Each drawing is the AdvancedSkeleton one scaled about its origin, L and R alike, to be seen
    at least as well as Manny's (measure_control_sizes.py, make_control_sizes.py)."""

    RADII = {"Creep": {"FKScapula": 16.183303, "FKShoulder": 20.707995},
             "Orc": {"FKScapula": 16.183303, "FKShoulder": 22.590540}}

    def files(self):
        return [(catalog.character_file(catalog.character_by_key("Creep_Rig")), "Creep"),
                (catalog.character_file(catalog.character_by_key("Orc_D_Rig")), "Orc"),
                (ORC_SOURCE, "Orc")]

    def test_the_four_controls_are_at_their_radii(self):
        for path, who in self.files():
            for name, wanted in self.RADII[who].items():
                for side in ("L", "R"):
                    cvs = _curve_cvs(path, "%s_%sShape" % (name, side), "%s_%s" % (name, side))
                    self.assertIsNotNone(cvs, (path, name, side))
                    radius = max((x * x + y * y + z * z) ** 0.5 for x, y, z in cvs)
                    self.assertAlmostEqual(radius, wanted, places=5, msg=(path, name, side))

    def test_left_and_right_are_the_same_size(self):
        for path, _who in self.files():
            for name in ("FKScapula", "FKShoulder"):
                r = [max(sum(v * v for v in cv) ** 0.5 for cv in _curve_cvs(path, "%s_%sShape" % (name, s),
                                                                              "%s_%s" % (name, s)))
                     for s in ("L", "R")]
                self.assertAlmostEqual(r[0], r[1], places=6, msg=(path, name))


class ArmorTable(unittest.TestCase):
    """The ARMOR table (2026-10-01, the Armor card): rigid pieces riding a bone,
    the first Atone's Tech Limb plate on `lowerarm_l` -- DA_Techlimb's own equip
    socket."""

    def test_the_tech_limb_is_the_first_row(self):
        row = catalog.ARMOR[0]
        self.assertEqual((row.key, row.label, row.bone, row.slot),
                         ("Tech_Limb", "Tech Limb", "lowerarm_l", "left_forearm"))

    def test_every_row_ships_its_model(self):
        for row in catalog.ARMOR:
            self.assertTrue(os.path.isfile(row.path), row.path)
            self.assertEqual(catalog.missing(row), "", row.key)
            self.assertTrue(row.path.endswith(".fbx"), row.path)

    def test_the_model_lives_in_the_plugin(self):
        assets = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(catalog.__file__))), "assets").replace("\\", "/")
        for row in catalog.ARMOR:
            self.assertTrue(row.path.startswith(assets + "/"), row.path)

    def test_keys_are_legal_node_names_and_unique(self):
        keys = [row.key for row in catalog.ARMOR]
        self.assertEqual(len(keys), len(set(keys)))
        for key in keys:
            self.assertEqual(catalog.node_key(key), key)

    def test_every_row_has_a_bone_and_a_slot(self):
        for row in catalog.ARMOR:
            self.assertTrue(row.bone, row.key)
            self.assertTrue(row.slot, row.key)

    def test_untextured_by_default(self):
        self.assertEqual(catalog.ARMOR[0].texture, "")

    def test_lookups(self):
        self.assertIs(catalog.armor_by_key("Tech_Limb"), catalog.ARMOR[0])
        self.assertIs(catalog.armor_by_label("Tech Limb"), catalog.ARMOR[0])
        self.assertIsNone(catalog.armor_by_key("nope"))
        self.assertIsNone(catalog.armor_by_label("nope"))
        self.assertEqual(catalog.armor_labels(), [r.label for r in catalog.ARMOR])

    def test_an_armor_row_is_not_a_weapon(self):
        keys = set(w.key for w in catalog.WEAPONS)
        for row in catalog.ARMOR:
            self.assertNotIn(row.key, keys)
            self.assertIsNone(catalog.by_key(row.key))

    def test_the_icon_path(self):
        self.assertTrue(catalog.armor_icon_path("Tech_Limb").endswith(
            "/assets/armor_icons/Tech_Limb.png"))
