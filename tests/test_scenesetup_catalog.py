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

    def test_only_the_orc_d_is_textured(self):
        self.assertEqual([c.key for c in catalog.CHARACTERS if c.textured], ["Orc_D_Rig"])

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
