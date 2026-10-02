"""Tests for the character's outliner group and layer (2026-10-02).

The pure halves run here; the scene half -- every catalog row grouped, the layer hiding every shape,
the exports unchanged, Delete and Ctrl+Z -- is proved by
docs/superpowers/plans/verify_character_groups.py in mayapy standalone.
"""

import collections
import sys
import types
import unittest


def _install_fake_maya():
    try:
        import maya.cmds  # noqa: F401
        return
    except ImportError:
        pass
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

import maya_rigs  # noqa: E402
from maya_scenesetup import character  # noqa: E402
from maya_scenesetup import chargroup  # noqa: E402

Entry = collections.namedtuple("Entry", "key label file")


class Names(unittest.TestCase):

    def test_a_rig_is_named_for_its_namespace(self):
        self.assertEqual(chargroup.group_name("Manny_Rig1"), "Manny_Rig1_Character")
        self.assertEqual(chargroup.layer_name("Manny_Rig1"), "Manny_Rig1_Layer")

    def test_never_the_namespaces_own_name(self):
        # measured: Maya will not give a node a namespace's name, and a namespace cannot be made
        # over a node's -- the suffix is what keeps the two apart
        self.assertNotEqual(chargroup.group_name("Manny_Rig"), "Manny_Rig")
        self.assertNotEqual(chargroup.layer_name("Manny_Rig"), "Manny_Rig")

    def test_an_illegal_stem_is_made_legal(self):
        self.assertEqual(chargroup.legal("Manny UE5 [skeleton]"), "Manny_UE5__skeleton_")
        self.assertEqual(chargroup.legal("4arms"), "_4arms")
        self.assertEqual(chargroup.legal(""), "Character")

    def test_the_first_free_base(self):
        self.assertEqual(chargroup.free_base("Manny_Skeleton", set()), "Manny_Skeleton")
        taken = {"Manny_Skeleton_Character", "Manny_Skeleton_Layer"}
        self.assertEqual(chargroup.free_base("Manny_Skeleton", taken), "Manny_Skeleton1")
        taken |= {"Manny_Skeleton1_Character"}
        self.assertEqual(chargroup.free_base("Manny_Skeleton", taken), "Manny_Skeleton2")

    def test_a_taken_layer_alone_moves_the_base_too(self):
        self.assertEqual(chargroup.free_base("Creep_Skeleton", {"Creep_Skeleton_Layer"}),
                         "Creep_Skeleton1")


class ChildOnPath(unittest.TestCase):

    def test_the_top_under_the_group(self):
        self.assertEqual(chargroup.child_on_path("|G|Armature|root", "|G"), "|G|Armature")
        self.assertEqual(chargroup.child_on_path("|G|root", "|G"), "|G|root")

    def test_outside_the_group_is_none(self):
        self.assertIsNone(chargroup.child_on_path("|GX|root", "|G"))
        self.assertIsNone(chargroup.child_on_path("|root", "|G"))
        self.assertIsNone(chargroup.child_on_path("|G", "|G"))
        self.assertIsNone(chargroup.child_on_path("|G|root", None))


class Base(unittest.TestCase):

    def test_a_rigs_base_is_its_namespace(self):
        entry = Entry("Manny_Rig", "Manny [rig]", "Manny_Rig.ma")
        self.assertEqual(character.group_base(entry, "Manny_Rig1"), "Manny_Rig1")

    def test_a_skeletons_base_is_its_file_stem(self):
        self.assertEqual(character.group_base(
            Entry("Manny", "Manny UE5 [skeleton]", "Manny_Skeleton.ma"), ""), "Manny_Skeleton")
        self.assertEqual(character.group_base(
            Entry("UE4_Mannequin", "UE4 Mannequin [skeleton]", "UE4_Mannequin.fbx"), ""),
            "UE4_Mannequin")

    def test_every_catalog_row_gets_a_base(self):
        from maya_scenesetup import catalog
        for entry in catalog.CHARACTERS:
            ns = entry.key if catalog.is_rig(entry) else ""
            self.assertTrue(character.group_base(entry, ns), entry.label)


class WorldTops(unittest.TestCase):

    def test_only_world_level_paths_in_order(self):
        paths = ["|root", "|root|pelvis", "|Skin_3p", "|Skin_3p|Skin_3pShape", "|root", "|camera1"]
        self.assertEqual(character.world_tops(paths), ["|root", "|Skin_3p", "|camera1"])

    def test_nothing_is_nothing(self):
        self.assertEqual(character.world_tops(None), [])


class Markers(unittest.TestCase):

    def test_one_marker_for_every_module(self):
        self.assertEqual(chargroup.MARKER, maya_rigs.CHARACTER_MARKER)
        self.assertEqual(chargroup.ROOT_LINK, maya_rigs.CHARACTER_ROOT)

    def test_the_group_is_locked_where_it_moves(self):
        self.assertEqual(set(chargroup.LOCKED),
                         {a + x for a in "trs" for x in "xyz"})


class Wiring(unittest.TestCase):
    """The roads that park a part, read in their source: a refactor that drops one would leave
    the part loose at world level, which only a scene run would notice."""

    def _source(self, module, name):
        import inspect
        return inspect.getsource(getattr(module, name))

    def test_add_character_groups_the_character(self):
        self.assertIn("group_character(", self._source(character, "_after_import"))

    def test_the_camera_floor_weapon_and_lift_are_parked(self):
        from maya_scenesetup import camera, connections, floor
        self.assertIn("chargroup.park(", self._source(camera, "setup"))
        self.assertIn("chargroup.park(", self._source(floor, "drop"))
        self.assertIn("chargroup.park(", self._source(connections, "apply"))

    def test_the_export_lifts_the_character_out(self):
        from maya_uebridge import animexport
        self.assertIn("_out_of_group(", self._source(animexport, "export_hierarchy"))



class AllOrNothing(unittest.TestCase):
    """2026-10-02 (the review): a group half made -- some tops in it, no layer -- would be read
    as the whole character. `make` undoes itself on any failure and re-raises; the Add line says
    the character was not grouped. The scene half: verify_character_groups.py phase G."""

    def test_make_undoes_itself_and_reraises(self):
        import inspect
        source = inspect.getsource(chargroup.make)
        self.assertIn("_unmake(", source)
        self.assertIn("raise", source.split("_unmake(")[1])

    def test_unmake_never_deletes_a_top_with_the_group(self):
        import inspect
        source = inspect.getsource(chargroup._unmake)
        self.assertIn("world=True", source)
        self.assertIn("listRelatives(path, children=True)", source)

    def test_the_add_line_names_the_failure(self):
        note = character.group_failed_note(RuntimeError("parent: node is locked\nmore"))
        self.assertIn("no character group (parent: node is locked)", note)
        self.assertIn("world level", note)
        self.assertIn("group_failed_note(", inspect_source(character._after_import))


def inspect_source(func):
    import inspect
    return inspect.getsource(func)

if __name__ == "__main__":
    unittest.main()
