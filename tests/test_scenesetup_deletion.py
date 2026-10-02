"""Characters > Delete (2026-10-01): the pure halves of `deletion`.

The scene half is proved by docs/superpowers/plans/verify_delete_character.py
in mayapy standalone; here: which DG garbage goes, which wrappers go, which
character a selected path names, and what the confirm and the line say.
"""

import sys
import types
import unittest


def _install_fake_maya():
    try:
        import maya.api.OpenMaya  # noqa: F401
        import maya.cmds  # noqa: F401
        import maya.mel  # noqa: F401
        return
    except ImportError:
        pass
    maya = types.ModuleType("maya")
    api = types.ModuleType("maya.api")
    openmaya = types.ModuleType("maya.api.OpenMaya")
    cmds = types.ModuleType("maya.cmds")
    mel = types.ModuleType("maya.mel")
    maya.cmds, maya.mel, maya.api = cmds, mel, api
    api.OpenMaya = openmaya
    sys.modules.setdefault("maya", maya)
    sys.modules["maya.api"] = api
    sys.modules["maya.api.OpenMaya"] = openmaya
    sys.modules["maya.cmds"] = cmds
    sys.modules["maya.mel"] = mel


_install_fake_maya()

from maya_scenesetup import deletion  # noqa: E402


def graph(edges):
    """{node: set(neighbours)} from undirected edges."""
    out = {}
    for a, b in edges:
        out.setdefault(a, set()).add(b)
        out.setdefault(b, set()).add(a)
    return out


class Garbage(unittest.TestCase):
    """The DG around the core: a component goes when it holds no DAG node and
    touches the core, or when every node in it was recorded by the Add."""

    def doomed(self, edges, core, dag=(), hubs=(), provenance=()):
        g = graph(edges)
        core = set(core)
        frontier = set()
        for node in core:
            frontier |= g.get(node, set())
        frontier -= core
        return deletion.doomed_components(
            core, frontier, set(provenance), lambda n: g.get(n, set()),
            lambda n: n in set(dag), lambda n: n in set(hubs))

    def test_a_material_worn_only_by_the_character_goes(self):
        edges = [("meshShape", "SG"), ("SG", "phong"), ("SG", "materialInfo"),
                 ("phong", "materialInfo"), ("phong", "file"), ("file", "place2d"),
                 ("SG", "lightLinker1"), ("lightLinker1", "otherSG"),
                 ("otherSG", "cubeShape")]
        out = self.doomed(edges, core={"meshShape"}, dag={"meshShape", "cubeShape"},
                          hubs={"lightLinker1"})
        self.assertEqual(out, {"SG", "phong", "materialInfo", "file", "place2d"})

    def test_without_the_hub_the_light_linker_joins_everything_and_nothing_goes(self):
        # Measured 2026-10-01: lightLinker1 is not a default node. Unknown hubs
        # only MERGE components - keeping, never deleting somebody else's node.
        edges = [("meshShape", "SG"), ("SG", "lightLinker1"),
                 ("lightLinker1", "otherSG"), ("otherSG", "cubeShape")]
        out = self.doomed(edges, core={"meshShape"}, dag={"meshShape", "cubeShape"})
        self.assertEqual(out, set())

    def test_a_material_shared_with_a_cube_stays(self):
        edges = [("meshShape", "SG"), ("SG", "phong"), ("SG", "cubeShape")]
        out = self.doomed(edges, core={"meshShape"}, dag={"meshShape", "cubeShape"})
        self.assertEqual(out, set())

    def test_curves_and_a_skin_go(self):
        edges = [("ctrl", "ctrl_rotateX"), ("joint", "skinCluster1"),
                 ("skinCluster1", "meshShape"), ("skinCluster1", "bindPose1"),
                 ("bindPose1", "joint")]
        out = self.doomed(edges, core={"ctrl", "joint", "meshShape"},
                          dag={"ctrl", "joint", "meshShape"})
        self.assertEqual(out, {"ctrl_rotateX", "skinCluster1", "bindPose1"})

    def test_a_layer_of_the_animators_holding_a_cube_too_stays(self):
        edges = [("joint", "myLayer"), ("myLayer", "cube"),
                 ("myLayer", "displayLayerManager")]
        out = self.doomed(edges, core={"joint"}, dag={"joint", "cube"},
                          hubs={"displayLayerManager"})
        self.assertEqual(out, set())

    def test_an_isolated_recorded_component_goes(self):
        # The dead AdvancedSkeleton half of Manny's skeleton asset: connected
        # to nothing of the character, recorded by the Add.
        edges = [("AllSet", "ChestFat"), ("ChestFat", "CupFat"),
                 ("BodyControls", "displayLayerManager")]
        out = self.doomed(edges, core={"root"}, dag={"root"},
                          hubs={"displayLayerManager"},
                          provenance={"AllSet", "ChestFat", "CupFat", "BodyControls"})
        self.assertEqual(out, {"AllSet", "ChestFat", "CupFat", "BodyControls"})

    def test_an_isolated_component_with_an_unrecorded_node_stays(self):
        edges = [("M_UE4Man_Body", "SK_MannequinSG"),
                 ("SK_MannequinSG", "myNetworkOfMine")]
        out = self.doomed(edges, core={"root"}, dag={"root"},
                          provenance={"M_UE4Man_Body", "SK_MannequinSG"})
        self.assertEqual(out, set())

    def test_a_recorded_node_reached_through_a_dag_node_stays(self):
        edges = [("M_UE4Man_Body", "SG"), ("SG", "myCubeShape")]
        out = self.doomed(edges, core={"root"}, dag={"root", "myCubeShape"},
                          provenance={"M_UE4Man_Body", "SG"})
        self.assertEqual(out, set())

    def test_hubs_are_never_doomed(self):
        edges = [("joint", "time1"), ("joint", "expression1"),
                 ("expression1", "time1")]
        out = self.doomed(edges, core={"joint"}, dag={"joint"}, hubs={"time1"},
                          provenance={"time1"})
        self.assertEqual(out, {"expression1"})


class Raising(unittest.TestCase):
    """A plain transform whose every child goes goes too."""

    def tree(self, paths):
        kids = {}
        for path in paths:
            parent = path.rsplit("|", 1)[0]
            if parent:
                kids.setdefault(parent, []).append(path)
        return kids

    def raised(self, tops, paths, plain=None):
        kids = self.tree(paths)
        plain = plain or (lambda p: True)
        return deletion.raised(tops, lambda p: p.rsplit("|", 1)[0] or None,
                               lambda p: kids.get(p, []), plain)

    def test_the_creep_layout_null_goes_with_its_root(self):
        paths = ["|Armature", "|Armature|root"]
        self.assertEqual(self.raised(["|Armature|root"], paths), ["|Armature"])

    def test_a_group_of_meshes_goes_when_every_mesh_goes(self):
        paths = ["|SKM", "|SKM|Hands_1P", "|SKM|Skin_3p"]
        self.assertEqual(self.raised(["|SKM|Hands_1P", "|SKM|Skin_3p"], paths),
                         ["|SKM"])

    def test_a_group_holding_something_else_stays(self):
        paths = ["|grp", "|grp|root", "|grp|cube"]
        self.assertEqual(self.raised(["|grp|root"], paths), ["|grp|root"])

    def test_not_into_a_parent_that_is_not_plain(self):
        paths = ["|hand", "|hand|space"]
        out = self.raised(["|hand|space"], paths, plain=lambda p: p != "|hand")
        self.assertEqual(out, ["|hand|space"])

    def test_it_climbs_more_than_one_level(self):
        paths = ["|a", "|a|b", "|a|b|root"]
        self.assertEqual(self.raised(["|a|b|root"], paths), ["|a"])

    def test_outermost_drops_what_lies_inside_another(self):
        self.assertEqual(deletion.outermost(["|a|b", "|a", "|ab", "|c|d"]),
                         ["|a", "|ab", "|c|d"])


def char(label, namespace="", parts=()):
    return deletion.Character("rig" if namespace else "skeleton", label,
                              namespace, parts[0] if parts else "", None,
                              list(parts))


class Owners(unittest.TestCase):
    def setUp(self):
        self.rig = char("Manny_Rig1", "Manny_Rig1",
                        ["|Manny_Rig1:Group", "|Manny_Rig1:root"])
        self.creep = char("Creep [skeleton] (root)", "",
                          ["|Armature", "|Creep_Body", "|WeaponSpaces|hand_r_weaponSpace"])
        self.chars = [self.rig, self.creep]

    def test_a_node_in_a_rigs_namespace_is_the_rigs(self):
        self.assertEqual(deletion.owners("|Manny_Rig1:SKM_Manny_Simple", self.chars),
                         [self.rig])

    def test_not_a_namespace_that_merely_starts_alike(self):
        self.assertEqual(deletion.owners("|Manny_Rig12:Group", self.chars), [])

    def test_a_nested_namespace_counts(self):
        self.assertEqual(deletion.owners("|Manny_Rig1:clip:root", self.chars), [self.rig])

    def test_under_a_part(self):
        self.assertEqual(deletion.owners("|Armature|root|pelvis", self.chars), [self.creep])
        self.assertEqual(
            deletion.owners("|WeaponSpaces|hand_r_weaponSpace|CreepSwordMesh", self.chars),
            [self.creep])

    def test_a_shared_group_above_the_parts_is_nobodys(self):
        self.assertEqual(deletion.owners("|WeaponSpaces", self.chars), [])

    def test_the_layout_null_is_a_part_of_its_own(self):
        self.assertEqual(deletion.owners("|Armature", self.chars), [self.creep])

    def test_choose_collapses_repeats_and_keeps_order(self):
        picked, unowned = deletion.choose(
            ["|Armature|root|pelvis", "|Manny_Rig1:Group|Manny_Rig1:Main",
             "|Creep_Body", "|pCube1"], self.chars)
        self.assertEqual(picked, [self.creep, self.rig])
        self.assertEqual(unowned, ["|pCube1"])


class Strangers(unittest.TestCase):
    """2026-10-02 (the character groups' review): the character group is a folder the animator
    can drop their own things into, and Delete takes everything under its parts -- a prop parked
    in `Manny_Rig1_Character` went with the rig unnamed. A child of the group that is none of
    the character's is a STRANGER: kept, moved out to world level, named in the confirm."""

    GROUP = "|Manny_Skeleton_Character"

    def strangers(self, children, parts=(), namespace="", recorded=(), attrs=None):
        attrs = attrs or {}
        return deletion.strangers(children, list(parts), namespace, set(recorded),
                                  lambda p: "uuid:" + p, lambda p: attrs.get(p, []))

    def test_a_prop_of_the_animators_is_a_stranger(self):
        g = self.GROUP
        self.assertEqual(self.strangers([g + "|root", g + "|prop_cube"], parts=[g + "|root"]),
                         [g + "|prop_cube"])

    def test_a_part_and_whatever_holds_one_are_the_characters(self):
        g = "|Creep_Skeleton_Character"
        self.assertEqual(self.strangers([g + "|Armature", g + "|Creep_Body"],
                                        parts=[g + "|Armature|root", g + "|Creep_Body"]), [])

    def test_the_rigs_namespace_is_the_rigs(self):
        g = "|Manny_Rig1_Character"
        self.assertEqual(self.strangers([g + "|Manny_Rig1:Group", g + "|Manny_Rig1:SKM"],
                                        namespace="Manny_Rig1"), [])

    def test_what_the_add_recorded_is_the_characters(self):
        g = self.GROUP
        self.assertEqual(self.strangers([g + "|camera1"], recorded=["uuid:" + g + "|camera1"]),
                         [])

    def test_our_markers_make_it_ours(self):
        g = self.GROUP
        children = [g + "|SceneSetup_camera", g + "|WeaponSpaces", g + "|CenterOfMass",
                    g + "|SpearMesh", g + "|animLabel", g + "|locator1"]
        attrs = {children[0]: ["mayaSceneSetupCamera"], children[1]: ["mayaWeaponSpaces"],
                 children[2]: ["skeldarCom"], children[3]: ["mayaWeapon", "mayaWeaponSource"],
                 children[4]: ["skeldarAnimLabel"], children[5]: ["myOwnAttr"]}
        self.assertEqual(self.strangers(children, attrs=attrs), [g + "|locator1"])

    def test_a_stranger_names_no_character_when_selected(self):
        g = self.GROUP
        c = deletion.Character("skeleton", "Manny UE5 [skeleton] (root)", "", g + "|root", None,
                               [g], [g + "|prop_cube"])
        self.assertEqual(deletion.owners(g + "|prop_cube|prop_cubeShape", [c]), [])
        self.assertEqual(deletion.owners(g + "|root|pelvis", [c]), [c])
        self.assertEqual(deletion.owners(g, [c]), [c])

    def test_the_confirm_names_what_is_kept(self):
        text = deletion.confirm_text([("Manny_Rig1 (rig)", [])], kept=["prop_cube"])
        self.assertIn("prop_cube", text)
        self.assertIn("kept", text)

    def test_the_line_names_what_was_kept(self):
        self.assertIn("prop_cube", deletion.kept_note(["|prop_cube"]))
        self.assertEqual(deletion.kept_note([]), "")


class Texts(unittest.TestCase):
    def test_the_confirm_names_everything(self):
        text = deletion.confirm_text(
            [("Manny_Rig1 (rig)", ["1 weapon", "camera"]),
             ("Creep [skeleton] (root)", [])],
            disconnects=["Manny_Rig"], foreign=["pCube1"])
        self.assertIn("Delete 2 characters", text)
        self.assertIn("Manny_Rig1 (rig) - 1 weapon, camera", text)
        self.assertIn("Creep [skeleton] (root)", text)
        self.assertIn("Manny_Rig is retargeted from them", text)
        self.assertIn("pCube1", text)
        self.assertIn("Ctrl+Z", text)

    def test_one_character_reads_in_the_singular(self):
        text = deletion.confirm_text([("root (skeleton)", [])])
        self.assertIn("Delete 1 character and everything", text)
        self.assertNotIn("retargeted", text)
        self.assertNotIn("constrained", text)

    def test_the_line_names_them_and_the_undo(self):
        line = deletion.deleted_message(["Manny_Rig1 (rig)", "root (skeleton)"], 3412)
        self.assertEqual(line, "Deleted Manny_Rig1 (rig), root (skeleton) - 3412 nodes. "
                               "Ctrl+Z brings them back.")

    def test_extras_follow(self):
        line = deletion.deleted_message(["root (skeleton)"], 90, unowned=2,
                                        notes=["Manny_Rig disconnected"])
        self.assertIn("Manny_Rig disconnected", line)
        self.assertIn("2 selected nodes belong to no character and stay.", line)
        one = deletion.deleted_message(["root (skeleton)"], 90, unowned=1)
        self.assertIn("1 selected node belongs to no character and stays.", one)

    def test_counted_names(self):
        self.assertEqual(deletion.counted(1, "weapon"), "1 weapon")
        self.assertEqual(deletion.counted(2, "armor piece"), "2 armor pieces")


class SpelledHere(unittest.TestCase):
    """The markers `deletion` spells rather than imports (maya_com.network drags numpy in,
    connections maya.mel): pinned equal to their owners'."""

    def test_the_hand_link_is_connections(self):
        from maya_scenesetup import connections
        self.assertEqual(deletion.HAND_LINK, connections.MARKER)

    def test_the_com_markers_are_networks(self):
        try:
            from maya_com import network
        except ImportError as exc:                                # pragma: no cover
            self.skipTest(str(exc))
        self.assertEqual(deletion.COM_MARKER, network.MARKER)
        self.assertEqual(deletion.COM_ROOT_LINK, network.ROOT_LINK)

    def test_the_holder_and_its_sources_are_the_retargets(self):
        import maya_asretarget
        import maya_pmretarget
        self.assertEqual(deletion.HOLDER, maya_asretarget.HOLDER)
        self.assertEqual(deletion.HOLDER, maya_pmretarget.HOLDER)
        self.assertEqual(set(deletion.HOLDER_SOURCES),
                         {maya_asretarget.SOURCE_ATTR, maya_pmretarget.SOURCE_ATTR})

    def test_the_singletons_are_hubs(self):
        for kind in deletion.SINGLETONS:
            self.assertIn(kind, deletion.HUB_TYPES)


class Recording(unittest.TestCase):
    """The Add records what it brought; the weapon import too."""

    def test_add_character_records_a_skeleton_import(self):
        import inspect
        from maya_scenesetup import character
        source = inspect.getsource(character._after_import)
        self.assertIn("deletion.record_import(root, new, entry.label)", source)
        self.assertIn("if root and not namespace:", source)

    def test_the_weapon_import_records_on_the_weapon(self):
        import inspect
        from maya_scenesetup import attach
        self.assertIn("deletion.record_on(weapon, brought)", inspect.getsource(attach.import_weapon))
        self.assertIn("_LAST_IMPORT[:] = cmds.ls(new", inspect.getsource(attach.import_model))


if __name__ == "__main__":
    unittest.main()
