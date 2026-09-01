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
