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

    def test_the_note_names_the_plain_root_it_collided_with_not_a_rigs_joint(self):
        """2026-09-24: a second Creep skeleton beside a Creep rig read
        "(Creep_Rig:FKXAnkle_L already in the scene)" -- an AdvancedSkeleton
        rig has many top joints, and the first of them is not what collided."""
        note = character.rename_note(
            "|Creep_Skeleton_root",
            ["|Creep_Rig:FKXAnkle_L", "|Creep_Rig:root", "|root", "|Creep_Skeleton_root"])
        self.assertEqual(note, "imported as Creep_Skeleton_root (root already in the scene)")

    def test_beside_rigs_alone_nothing_collided(self):
        """2026-09-30, the portrait grid's live run: a Creep skeleton added
        beside rigs only kept its plain `root`, and the note still said
        "imported as root (Manny_Rig:FKXAnkle_L already in the scene)". A
        rig's joints are namespaced; with no plain top joint nothing collides."""
        self.assertEqual(character.rename_note(
            "|Armature|root", ["|Manny_Rig:FKXAnkle_L", "|Manny_Rig:root",
                               "|Armature|root"]), "")

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


class ManyRigs(unittest.TestCase):
    """Since 2026-09-08 a rig arrives in its own namespace and the one-rig
    refusal of 2026-09-07 is gone («я должен иметь возможность добавить в
    сцену много ригов»). Bare skeletons keep their plain names."""

    def test_the_refusal_is_gone(self):
        self.assertFalse(hasattr(character, "RIG_PRESENT"))

    def test_the_namespace_is_the_rig_key_uniquified(self):
        self.assertEqual(character.free_namespace("Manny_Rig", []), "Manny_Rig")
        self.assertEqual(character.free_namespace("Manny_Rig", ["Manny_Rig"]),
                         "Manny_Rig1")
        self.assertEqual(character.free_namespace(
            "Manny_Rig", ["Manny_Rig", "Manny_Rig1", "UI", "shared"]),
            "Manny_Rig2")

    def test_each_rig_lands_in_a_namespace_named_for_its_own_key(self):
        """2026-09-24, the Creep: a second rig row must not arrive as
        `Manny_Rig1`."""
        from maya_scenesetup import catalog
        self.assertEqual(character.rig_namespace(catalog.character_by_key("Creep_Rig")), "Creep_Rig")
        self.assertEqual(character.rig_namespace(catalog.character_by_key("Manny_Rig")), "Manny_Rig")

    def test_the_namespace_is_maya_legal(self):
        self.assertEqual(character.free_namespace("Manny Rig.02", []),
                         "Manny_Rig_02")
        self.assertEqual(character.free_namespace("2rig", []), "_2rig")
        self.assertEqual(character.free_namespace("", []), "rig")

    def test_the_message_names_the_namespace(self):
        text = character.added_message(93, 6, [], label="Manny [rig]",
                                       namespace="Manny_Rig1", selected=True)
        self.assertTrue(text.startswith("Manny [rig] added as Manny_Rig1 - 93 joints"))
        self.assertTrue(text.endswith(" - selected"))

    def test_a_skeleton_message_says_nothing_about_a_namespace(self):
        text = character.added_message(93, 6, [], label="Manny UE5 [skeleton]")
        self.assertEqual(text, "Manny UE5 [skeleton] added - 93 joints, 6 meshes")

    def test_a_missing_rig_file_is_still_the_refusal(self):
        saved = catalog.character_file
        catalog.character_file = lambda entry: "D:/nowhere/" + entry.file
        try:
            text = character.add_character(catalog.default_rig())
        finally:
            catalog.character_file = saved
        self.assertEqual(text, character.NO_FILE.format(
            "D:/nowhere/Manny_Rig.ma"))


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


class TagsItsRoot(unittest.TestCase):
    """2026-09-25: Add Character wrote the catalog key on the skeleton root for the morning's
    export wrapper named for the character; since the evening the wrapper is `Armature` for
    every character and nothing reads the tag, so nothing writes it. (A root tagged that one
    day is still held out of every export by maya_uebridge.fbxlayout.tag_held.)"""

    def test_add_character_no_longer_tags_the_root(self):
        import inspect
        self.assertNotIn("tag_root(", inspect.getsource(character.add_character))
        self.assertFalse(hasattr(character, "tag_root"))
        self.assertFalse(hasattr(character, "CHARACTER_TAG"))


class Appearance(unittest.TestCase):
    """What an Add says a character arrived wearing (2026-09-28, the Orc D): its colour's name,
    or «textured» -- with the viewport's Textures named when this press turned them on, and any
    image the installed copy is missing named too (the character still arrives)."""

    def test_a_coloured_character_says_its_colour(self):
        from maya_scenesetup import colour
        rgb = colour.PALETTE[1].rgb
        self.assertEqual(character.appearance(False, rgb, [], []), colour.colour_name(rgb))

    def test_a_textured_character_says_textured(self):
        self.assertEqual(character.appearance(True, None, [], []), "textured")

    def test_turning_the_textures_on_is_said(self):
        self.assertEqual(character.appearance(True, None, ["modelPanel4"], []),
                         "textured (viewport textures on)")

    def test_a_missing_image_is_named_by_its_file(self):
        text = character.appearance(True, None, [], ["C:/x/assets/Orc_D/Orc_D_Eye_Color.jpg"])
        self.assertEqual(text, "textured - missing image(s): Orc_D_Eye_Color.jpg")


class TexturedAdd(unittest.TestCase):
    """A textured row keeps the asset's own materials: no palette colour is painted, the images
    are pointed at the installed copy, the viewport's Textures come on."""

    class Cmds(object):
        def undoInfo(self, **kwargs):
            pass

        def ls(self, *args, **kwargs):
            return []

        def objExists(self, name):
            return False

        def delete(self, *args):
            pass

    def setUp(self):
        import tempfile
        from maya_overrig import builder
        from maya_scenesetup import colour
        handle, self.file = tempfile.mkstemp(suffix=".ma")
        os.close(handle)
        self.calls = []
        self.saved = [(character, "cmds", character.cmds),
                      (character, "import_asset", character.import_asset),
                      (character, "connect", character.connect),
                      (character, "select_rig", character.select_rig),
                      (character, "existing_namespaces", character.existing_namespaces),
                      (catalog, "character_file", catalog.character_file),
                      (builder, "character_roots", builder.character_roots)]
        for name in ("paint_nodes", "relink_images", "show_textures"):
            self.saved.append((colour, name, getattr(colour, name)))
        character.cmds = self.Cmds()
        character.import_asset = lambda path, namespace=None: ["|Orc_D_Rig:root"]
        character.connect = lambda root: False
        character.select_rig = lambda namespace: True
        character.existing_namespaces = lambda: []
        catalog.character_file = lambda entry: self.file
        builder.character_roots = lambda: []
        colour.paint_nodes = lambda *a: self.calls.append(("paint",)) or "phong1"
        colour.relink_images = lambda nodes, resolve: (
            self.calls.append(("relink", resolve("Orc_D/a.jpg"))) or (6, []))
        colour.show_textures = lambda: self.calls.append(("show",)) or ["modelPanel4"]

    def tearDown(self):
        for owner, name, value in self.saved:
            setattr(owner, name, value)
        os.remove(self.file)

    def test_the_orc_d_is_not_painted_and_its_images_are_relinked(self):
        text = character.add_character(catalog.character_by_key("Orc_D_Rig"), (0.8, 0.25, 0.22))
        self.assertNotIn(("paint",), self.calls)
        self.assertEqual(self.calls[0], ("relink", catalog.asset_path("Orc_D/a.jpg")))
        self.assertIn(("show",), self.calls)
        self.assertIn("Orc D [rig] added as Orc_D_Rig", text)
        self.assertIn(" - textured (viewport textures on)", text)
        self.assertNotIn(" - red", text)

    def test_the_mannys_and_the_creeps_are_not_painted_and_their_images_are_relinked(self):
        """Textured since 2026-09-30, the rigs and the skeletons alike."""
        for key in ("Manny_Rig", "Manny", "Creep_Rig", "Creep"):
            del self.calls[:]
            text = character.add_character(catalog.character_by_key(key), (0.8, 0.25, 0.22))
            self.assertNotIn(("paint",), self.calls, key)
            self.assertIn(("show",), self.calls, key)
            self.assertIn(" - textured (viewport textures on)", text, key)
            self.assertNotIn(" - red", text, key)

    def test_an_untextured_row_is_still_painted_and_nothing_relinked(self):
        """The UE4 Mannequin, the one row left untextured (a Manny, then a Creep, until 2026-09-30)."""
        text = character.add_character(catalog.character_by_key("UE4_Mannequin"), (0.8, 0.25, 0.22))
        self.assertEqual(self.calls, [("paint",)])
        self.assertIn(" - red", text)


class Placed(unittest.TestCase):
    """2026-09-30: a portrait dropped on the floor - the rig's Main, or the
    skeleton's root, moved by (x, 0, z) in world space; one undo chunk."""

    class Cmds(object):
        def __init__(self):
            self.log = []

        def undoInfo(self, **kwargs):
            if kwargs.get("query"):
                return True
            self.log.append(("undo", kwargs.get("stateWithoutFlush")))

        def ls(self, *args, **kwargs):
            if args and args[0] == "Manny_Rig:Main":
                return ["|Manny_Rig:Group|Manny_Rig:Main"]
            return []

        def objExists(self, name):
            return False

        def delete(self, *args):
            pass

        def move(self, *args, **kwargs):
            self.log.append(("move", args, kwargs))

    def setUp(self):
        import tempfile
        from maya_overrig import builder
        from maya_scenesetup import colour
        handle, self.file = tempfile.mkstemp(suffix=".ma")
        os.close(handle)
        self.cmds = self.Cmds()
        self.roots = [[], ["|Armature|root"]]
        self.saved = [(character, "cmds", character.cmds),
                      (character, "import_asset", character.import_asset),
                      (character, "connect", character.connect),
                      (character, "select_rig", character.select_rig),
                      (character, "existing_namespaces", character.existing_namespaces),
                      (catalog, "character_file", catalog.character_file),
                      (builder, "character_roots", builder.character_roots),
                      (colour, "paint_nodes", colour.paint_nodes),
                      (colour, "relink_images", colour.relink_images),
                      (colour, "show_textures", colour.show_textures)]
        character.cmds = self.cmds
        character.import_asset = lambda path, namespace=None: []
        character.connect = lambda root: False
        character.select_rig = lambda namespace: True
        character.existing_namespaces = lambda: []
        catalog.character_file = lambda entry: self.file
        builder.character_roots = lambda: self.roots.pop(0)
        colour.paint_nodes = lambda *a: "phong1"
        # the Manny rig is a textured row since 2026-09-30: its dressing is TexturedAdd's business
        colour.relink_images = lambda nodes, resolve: (0, [])
        colour.show_textures = lambda: []

    def tearDown(self):
        for owner, name, value in self.saved:
            setattr(owner, name, value)
        os.remove(self.file)

    def moves(self):
        return [e for e in self.cmds.log if e[0] == "move"]

    def test_the_placement_keeps_the_files_height(self):
        self.assertEqual(character.placement((120.0, 3.0, -35.0)), (120.0, 0.0, -35.0))

    def test_a_rig_moves_its_main(self):
        text = character.add_character(catalog.character_by_key("Manny_Rig"),
                                       (0.8, 0.25, 0.22), at=(120.0, 0.0, -35.0))
        self.assertEqual(self.moves(), [("move", (120.0, 0.0, -35.0,
                                                  "|Manny_Rig:Group|Manny_Rig:Main"),
                                         {"relative": True, "worldSpace": True})])
        self.assertIn(" - at (120, -35)", text)

    def test_a_skeleton_moves_its_root_never_the_armature(self):
        character.add_character(catalog.character_by_key("Creep"), (0.8, 0.25, 0.22),
                                at=(10.0, 0.0, 20.0))
        self.assertEqual(self.moves()[0][1][3], "|Armature|root")

    def test_no_point_moves_nothing(self):
        text = character.add_character(catalog.character_by_key("Manny_Rig"), (0.8, 0.25, 0.22))
        self.assertEqual(self.moves(), [])
        self.assertNotIn(" - at (", text)

    def test_nothing_after_the_import_is_recorded_for_undo(self):
        """Measured live 2026-09-30: `file -import` flushes Maya's undo queue,
        so a character can never be undone - Maya's own File > Import cannot
        be either. What follows it (the colour, the move, the selection) is
        therefore not recorded: a Ctrl+Z must not leave the character
        unpainted at the origin."""
        character.add_character(catalog.character_by_key("Manny_Rig"), (0.8, 0.25, 0.22),
                                at=(1.0, 0.0, 2.0))
        undo = [e for e in self.cmds.log if e[0] == "undo"]
        self.assertEqual(undo, [("undo", False), ("undo", True)])
        first_move = self.cmds.log.index([e for e in self.cmds.log if e[0] == "move"][0])
        self.assertLess(self.cmds.log.index(("undo", False)), first_move)
        self.assertEqual(self.cmds.log[-1], ("undo", True))
