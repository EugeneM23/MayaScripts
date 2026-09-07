"""Tests for putting the working character into the scene.

The decisions are pure functions over data -- which file type, whether the
scene already holds a skeleton, which imported nodes are malware -- so they
run without Maya. The import itself is proved live by
docs/superpowers/plans/verify_add_character.py.

The ShippedAsset class pins a fact about a FILE, not about code: the copy in
assets/ is the user's character scene with the "vaccine" script-node malware
cut out. If the file is ever replaced with an unsanitized re-export, these
tests are what catches it before the button spreads the infection into every
new scene.
"""

import os
import sys
import types
import unittest


def _install_fake_maya():
    """Let character import without Maya. See CLAUDE.md on rebinding."""
    if "maya.cmds" in sys.modules:
        return
    maya = types.ModuleType("maya")
    cmds = types.ModuleType("maya.cmds")
    mel = types.ModuleType("maya.mel")
    maya.cmds = cmds
    maya.mel = mel
    sys.modules.setdefault("maya", maya)
    sys.modules["maya.cmds"] = cmds
    sys.modules["maya.mel"] = mel


_install_fake_maya()

from maya_scenesetup import catalog  # noqa: E402
from maya_scenesetup import character  # noqa: E402


class SceneType(unittest.TestCase):
    """The file type is decided explicitly, never sniffed by Maya."""

    def test_ma_is_ascii(self):
        self.assertEqual(character.scene_type("D:/rigs/Manny.ma"), "mayaAscii")

    def test_mb_is_binary(self):
        self.assertEqual(character.scene_type("D:/rigs/Manny.mb"),
                         "mayaBinary")

    def test_fbx_is_fbx(self):
        """The UE4 mannequin ships as FBX because that is what the editor
        exports; the type decides which import path runs, and the FBX one
        has to force the plugin's global mode (trap 33)."""
        self.assertEqual(character.scene_type("D:/a/UE4_Mannequin.fbx"),
                         "FBX")
        self.assertTrue(character.is_fbx("D:/a/UE4_Mannequin.FBX"))
        self.assertFalse(character.is_fbx("D:/rigs/Manny.ma"))

    def test_nothing_is_not_fbx(self):
        self.assertFalse(character.is_fbx(""))
        self.assertFalse(character.is_fbx(None))

    def test_extension_case_does_not_matter(self):
        self.assertEqual(character.scene_type("D:/rigs/MANNY.MB"),
                         "mayaBinary")


class NoRefusal(unittest.TestCase):
    """The blanket refusal is GONE (2026-09-01): a scene holds as many
    characters as the animator wants, because every rig operation is
    scoped to the one the picker is connected to. Pinned as a gone-test so
    it cannot come back by accident."""

    def test_the_refusal_is_gone(self):
        self.assertFalse(hasattr(character, "refusal"))
        self.assertFalse(hasattr(character, "ALREADY"))


class NewRoot(unittest.TestCase):
    """A path diff: the incoming TOP node is the one Maya renamed, so its
    name is not knowable in advance, and everything below it kept its
    plain name -- which is what a name diff would miss."""

    def test_finds_the_root_the_import_added(self):
        self.assertEqual(character.new_root(["|root"], ["|root", "|root1"]),
                         "|root1")

    def test_an_empty_scene_yields_the_only_root(self):
        self.assertEqual(character.new_root([], ["|root"]), "|root")

    def test_nothing_new_is_none(self):
        self.assertIsNone(character.new_root(["|root"], ["|root"]))
        self.assertIsNone(character.new_root([], []))
        self.assertIsNone(character.new_root(None, None))

    def test_the_shallowest_fresh_root_wins(self):
        """The import brings rig-helper joints too; the character root is
        always shallower than anything under it."""
        self.assertEqual(
            character.new_root([], ["|grp|root|extra_jnt", "|grp|root"]),
            "|grp|root")

    def test_ties_break_by_path_so_the_answer_never_moves(self):
        self.assertEqual(character.new_root([], ["|zeta", "|alpha"]),
                         character.new_root([], ["|alpha", "|zeta"]))


class RenameNote(unittest.TestCase):
    """Said out loud because the animator sees `root1` in the outliner and
    wonders what went wrong. Nothing did -- only the top node collides."""

    def test_names_the_new_root_and_the_one_already_there(self):
        note = character.rename_note("|root1", ["|root", "|root1"])
        self.assertIn("root1", note)
        self.assertIn("root", note)

    def test_the_first_character_gets_no_note(self):
        self.assertEqual(character.rename_note("|root", ["|root"]), "")

    def test_nothing_imported_gets_no_note(self):
        self.assertEqual(character.rename_note(None, ["|root"]), "")
        self.assertEqual(character.rename_note("|root", []), "")

    def test_no_note_when_the_name_did_not_actually_collide(self):
        """A character imported into a scene whose skeleton is called
        something else keeps its own name."""
        self.assertEqual(
            character.rename_note("|root", ["|pelvis_only", "|root"]),
            "imported as root (pelvis_only already in the scene)")


class MalwareNodes(unittest.TestCase):
    """Only nodes THIS import created are candidates; the sweep never
    reaches into what was already in the scene."""

    def test_finds_the_two_gene_nodes(self):
        names = ["bindPose2", "vaccine_gene", "breed_gene", "camera1"]
        self.assertEqual(character.malware_nodes(names),
                         ["vaccine_gene", "breed_gene"])

    def test_a_clean_import_finds_nothing(self):
        self.assertEqual(character.malware_nodes(["root", "SKM_Manny"]), [])

    def test_a_maya_renamed_copy_still_matches(self):
        """A clash on import gets a numeric suffix."""
        self.assertEqual(character.malware_nodes(["vaccine_gene1"]),
                         ["vaccine_gene1"])

    def test_case_does_not_matter(self):
        self.assertEqual(character.malware_nodes(["Vaccine_Gene"]),
                         ["Vaccine_Gene"])

    def test_none_is_an_empty_answer(self):
        self.assertEqual(character.malware_nodes(None), [])


class AddedMessage(unittest.TestCase):

    def test_names_the_character_and_the_counts(self):
        self.assertEqual(character.added_message(93, 6, []),
                         "Manny added - 93 joints, 6 meshes")

    def test_a_sweep_is_reported_by_node_name(self):
        message = character.added_message(93, 6, ["vaccine_gene"])
        self.assertIn("Manny added", message)
        self.assertIn("vaccine_gene", message)
        self.assertIn("malware", message)

    def test_the_rename_note_rides_along(self):
        message = character.added_message(
            93, 6, [], note="imported as root1 (root already in the scene)")
        self.assertIn("root1", message)

    def test_the_connect_is_reported(self):
        """"add it" and "work on it" are one press, so the press has to say
        which one it happened to."""
        self.assertIn("connected",
                      character.added_message(93, 6, [], connected=True))
        self.assertNotIn("connected",
                         character.added_message(93, 6, []))

    def test_the_label_names_WHICH_skeleton_arrived(self):
        """With a dropdown offering more than one, "Manny added" over a UE4
        mannequin would be a lie the animator has no other way to catch."""
        message = character.added_message(68, 2, [], label="UE4 Mannequin")
        self.assertIn("UE4 Mannequin added", message)
        self.assertNotIn("Manny added", message)

    def test_no_label_keeps_the_original_wording(self):
        self.assertIn("Manny added", character.added_message(93, 6, []))

    def test_the_colour_is_named(self):
        """Every press brings a different one, so the colour is how the
        animator tells the presses apart afterwards."""
        message = character.added_message(93, 6, [], colour_name="red")
        self.assertIn("red", message)

    def test_no_colour_says_nothing_about_colour(self):
        """A press that painted nothing must not claim a colour."""
        self.assertEqual(character.added_message(93, 6, [], colour_name=""),
                         character.added_message(93, 6, []))

    def test_the_colour_does_not_displace_the_rename_note(self):
        message = character.added_message(
            93, 6, [], note="imported as root1 (root already in the scene)",
            colour_name="blue", connected=True)
        for fragment in ("93 joints", "blue", "root1", "connected"):
            self.assertIn(fragment, message)


class ShippedAsset(unittest.TestCase):
    """The sanitize is a fact about the file; pin it or lose it silently."""

    def _shipped(self):
        path = catalog.character_path()
        if not path.endswith("assets/Manny_Skeleton.ma"):
            self.fail("character_path does not resolve to the shipped copy: "
                      + path)
        return path

    def test_the_shipped_scene_is_on_disk(self):
        self.assertTrue(os.path.isfile(self._shipped()))

    def test_the_shipped_scene_carries_no_vaccine(self):
        """Binary scan: the malware block held non-ascii text, so a text
        read would hinge on encoding; bytes cannot lie."""
        with open(self._shipped(), "rb") as handle:
            content = handle.read()
        self.assertNotIn(b"vaccine", content)
        self.assertNotIn(b"breed_gene", content)

    def test_the_shipped_scene_still_holds_the_skeleton(self):
        """The cut must take the malware and nothing else."""
        with open(self._shipped(), "rb") as handle:
            content = handle.read()
        self.assertIn(b'createNode joint -n "root"', content)
        self.assertIn(b"bindPose", content)


class WrapperNodes(unittest.TestCase):
    """Which imported node is the FBX importer's axis-conversion wrapper.

    Pure: the scene arrives as three lookups. The wrapper is one transform
    at WORLD level holding no shape of its own and not a joint -- and
    flattening it is correctness, not tidiness: a UE clip carries the same
    -90 on root's jointOrient, so a merge onto a wrapped skeleton rotates
    twice and the character lies down (measured, head Y=2.96 against
    Y=147.84).
    """

    def _find(self, nodes, joints=(), shaped=()):
        return character.wrapper_nodes(
            nodes,
            is_joint=lambda n: n in joints,
            has_shape=lambda n: n in shaped,
            depth=lambda n: n.count("|"))

    def test_finds_the_shapeless_world_level_transform(self):
        self.assertEqual(
            self._find(["|SK_Mannequin", "|SK_Mannequin|root"],
                       joints=("|SK_Mannequin|root",)),
            ["|SK_Mannequin"])

    def test_a_joint_is_never_a_wrapper(self):
        """Manny's root arrives at world level and must stay exactly
        where it is."""
        self.assertEqual(self._find(["|root"], joints=("|root",)), [])

    def test_a_transform_holding_a_shape_is_not_a_wrapper(self):
        """The mesh transform is content, not scaffolding."""
        self.assertEqual(
            self._find(["|SKM_Manny_Simple"], shaped=("|SKM_Manny_Simple",)),
            [])

    def test_nested_transforms_are_left_alone(self):
        """Only the TOP wrapper: a group inside the file is the author's."""
        self.assertEqual(
            self._find(["|SK_Mannequin|inner", "|SK_Mannequin|inner|more"]),
            [])

    def test_several_wrappers_all_come_back(self):
        self.assertEqual(self._find(["|a", "|b"]), ["|a", "|b"])

    def test_duplicates_collapse(self):
        self.assertEqual(self._find(["|a", "|a"]), ["|a"])

    def test_nothing_in_nothing_out(self):
        self.assertEqual(self._find([]), [])
        self.assertEqual(self._find(None), [])


class TransformPlugs(unittest.TestCase):
    """The FBX importer LOCKS a skinned mesh's transform -- all nine of
    t/r/s, measured -- and a locked plug makes `cmds.xform` a SILENT no-op.
    That is how the first flatten left the skeleton standing and the
    geometry on its side: the joints took their world matrix back and the
    mesh could not."""

    def test_twelve_plugs_in_a_fixed_order(self):
        plugs = character.transform_plugs("|mesh")
        self.assertEqual(len(plugs), 12)
        self.assertEqual(plugs[0], "|mesh.translateX")
        self.assertEqual(plugs[-1], "|mesh.shearZ")

    def test_it_covers_what_the_importer_locks(self):
        plugs = set(character.transform_plugs("m"))
        for channel in ("translate", "rotate", "scale"):
            for axis in "XYZ":
                self.assertIn("m.{0}{1}".format(channel, axis), plugs)

    def test_the_order_is_stable_across_calls(self):
        self.assertEqual(character.transform_plugs("a"),
                         character.transform_plugs("a"))


class NeedsGrey(unittest.TestCase):
    """The UE4 mannequin's FBX brings its two materials at color (0,0,0):
    UE does not put the textures in the file, so the character arrives pure
    black. A reference figure has to read as a figure."""

    def test_a_flat_black_material_is_the_case_this_exists_for(self):
        self.assertTrue(character.needs_grey((0.0, 0.0, 0.0), False))

    def test_a_TEXTURED_colour_is_never_overridden(self):
        """The texture decides the look and the plug's value means nothing
        then -- black or not."""
        self.assertFalse(character.needs_grey((0.0, 0.0, 0.0), True))
        self.assertFalse(character.needs_grey((0.8, 0.8, 0.8), True))

    def test_a_material_that_is_merely_dark_is_left_alone(self):
        self.assertFalse(character.needs_grey((0.2, 0.2, 0.2), False))

    def test_a_coloured_material_is_left_alone(self):
        self.assertFalse(character.needs_grey((0.0, 0.0, 0.6), False))

    def test_rounding_noise_still_counts_as_black(self):
        self.assertTrue(character.needs_grey((0.0, 1e-8, 0.0), False))

    def test_no_colour_at_all_is_not_a_decision(self):
        self.assertFalse(character.needs_grey(None, False))

    def test_the_grey_is_maya_s_own_default(self):
        self.assertEqual(character.GREY, (0.5, 0.5, 0.5))


class OneRigPerScene(unittest.TestCase):
    """The AdvancedSkeleton rig is added once (2026-09-07): both retarget
    modules address it by name, and Maya uniquifies every one of those names
    on a second import. Bare skeletons stay unlimited -- the 2026-09-01
    freedom is untouched for them."""

    def setUp(self):
        self.real_cmds = character.cmds
        self.real_present = character.rig_present

    def tearDown(self):
        character.cmds = self.real_cmds
        character.rig_present = self.real_present

    def _cmds(self, existing):
        return types.SimpleNamespace(objExists=lambda name: name in existing)

    def test_rig_present_needs_both_of_the_rigs_nodes(self):
        character.cmds = self._cmds({"ControlSet"})
        self.assertFalse(character.rig_present())
        character.cmds = self._cmds({"Main"})
        self.assertFalse(character.rig_present())
        character.cmds = self._cmds({"ControlSet", "Main"})
        self.assertTrue(character.rig_present())

    def test_a_second_rig_is_refused_by_name_before_anything_is_touched(self):
        character.rig_present = lambda: True
        self.assertEqual(character.add_character(catalog.default_rig()),
                         character.RIG_PRESENT)
        self.assertIn("one AdvancedSkeleton rig per scene",
                      character.RIG_PRESENT)

    def test_a_skeleton_is_never_refused_for_a_standing_rig(self):
        """Only the rig row asks; the skeleton rows go straight to the
        file check, which is the next line and fails on a fake path."""
        character.rig_present = lambda: True
        saved = catalog.character_file
        catalog.character_file = lambda entry: "D:/nowhere/" + entry.file
        try:
            text = character.add_character(catalog.default_character())
        finally:
            catalog.character_file = saved
        self.assertEqual(text, character.NO_FILE.format(
            "D:/nowhere/Manny_Skeleton.ma"))


class ConnectFollowsThePickerFlag(unittest.TestCase):
    """With the picker off the shelf (skeldar_features.PICKER False), a new
    character is never handed to it -- opening a panel that is not on the
    shelf from a Scene Setup press would surprise."""

    def test_connect_is_off_while_the_picker_is_off(self):
        import skeldar_features
        saved = skeldar_features.PICKER
        skeldar_features.PICKER = False
        try:
            self.assertFalse(character.connect("|root"))
        finally:
            skeldar_features.PICKER = saved

    def test_no_root_is_no_connect_whatever_the_flag(self):
        self.assertFalse(character.connect(None))
        self.assertFalse(character.connect(""))
