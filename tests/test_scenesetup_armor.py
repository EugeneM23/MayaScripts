"""The Armor card's scene rules (2026-10-01): which pieces an Equip takes off, what the
presses say, and the armor spaces kept apart from the weapons'. The scene half - a piece on its
bone where Unreal puts it, following a retarget, out of the export, gone after Unequip - is
docs/superpowers/plans/verify_armor.py's, in mayapy standalone.

Spec: docs/superpowers/specs/2026-10-01-armor-techlimb-design.md
"""

import os
import unittest

from maya_scenesetup import armor
from maya_scenesetup import catalog
from maya_scenesetup import weaponspace

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "SkeldarAnim")
TECH = catalog.ARMOR[0]


class SlotPlan(unittest.TestCase):

    def test_nothing_worn_takes_nothing_off(self):
        self.assertEqual(armor.slot_plan({}, TECH), [])

    def test_the_same_piece_again_is_replaced(self):
        self.assertEqual(armor.slot_plan({"Tech_Limb": "left_forearm"}, TECH),
                         ["Tech_Limb"])

    def test_another_piece_in_the_slot_comes_off(self):
        self.assertEqual(armor.slot_plan({"Other_Plate": "left_forearm"}, TECH),
                         ["Other_Plate"])

    def test_a_piece_in_another_slot_stays(self):
        self.assertEqual(armor.slot_plan({"Helmet": "head"}, TECH), [])

    def test_sorted_and_without_duplicates(self):
        worn = {"Z_Plate": "left_forearm", "Tech_Limb": "left_forearm", "Helmet": "head"}
        self.assertEqual(armor.slot_plan(worn, TECH), ["Tech_Limb", "Z_Plate"])


class Messages(unittest.TestCase):

    def test_equipped(self):
        self.assertEqual(
            armor.equipped_message("Tech Limb", "|Manny_Rig:root|x|Manny_Rig:lowerarm_l",
                                   "|Manny_Rig:root", [], "teal"),
            "Tech Limb on Manny_Rig's lowerarm_l, in teal")

    def test_equipped_over_what_the_slot_held(self):
        self.assertEqual(
            armor.equipped_message("Tech Limb", "|root|lowerarm_l", "|root",
                                   ["Tech Limb"], ""),
            "Tech Limb on root's lowerarm_l (replaced Tech Limb)")

    def test_unequipped(self):
        self.assertEqual(armor.unequipped_message("Tech Limb", "|Creep_Rig:Armature|Creep_Rig:root"),
                         "Tech Limb taken off Creep_Rig")

    def test_not_worn(self):
        self.assertEqual(armor.not_worn_message("Tech Limb", "|root"),
                         "root does not wear Tech Limb")

    def test_no_bone(self):
        self.assertEqual(armor.no_bone_message("Tech Limb", "lowerarm_l", "|root"),
                         "Tech Limb rides lowerarm_l - root has no such bone")

    def test_missing_file(self):
        self.assertEqual(armor.missing_message("Tech Limb", "C:/x/Tech_Limb.fbx"),
                         "Tech Limb: the model is missing - C:/x/Tech_Limb.fbx")

    def test_pick(self):
        self.assertEqual(armor.pick_message("Tech Limb", "lowerarm_l", True),
                         "Tech Limb (lowerarm_l) - worn: Equip puts it on again, Unequip takes it off")
        self.assertEqual(armor.pick_message("Tech Limb", "lowerarm_l", False),
                         "Tech Limb (lowerarm_l) - press Equip")


class Inside(unittest.TestCase):

    def test_a_bone_under_the_root(self):
        self.assertTrue(armor.inside("|ns:root|ns:pelvis|ns:lowerarm_l", "|ns:root"))

    def test_the_root_itself(self):
        self.assertTrue(armor.inside("|root", "|root"))

    def test_the_separator_matters(self):
        self.assertFalse(armor.inside("|root1|lowerarm_l", "|root"))

    def test_nothing(self):
        self.assertFalse(armor.inside(None, "|root"))
        self.assertFalse(armor.inside("|root|a", None))


class Spaces(unittest.TestCase):
    """The armor space is the weapons' shape with markers of its own."""

    def test_its_own_markers(self):
        self.assertNotEqual(armor.SPACE_MARKER, weaponspace.SPACE_MARKER)
        self.assertNotEqual(armor.GROUP_MARKER, weaponspace.GROUP_MARKER)
        self.assertEqual((armor.SPACE_MARKER, armor.GROUP_MARKER, armor.GROUP_NAME),
                         ("mayaArmorSpace", "mayaArmorSpaces", "ArmorSpaces"))

    def test_the_name_follows_the_bone(self):
        self.assertEqual(weaponspace.space_name("|ns:root|ns:lowerarm_l", armor.SUFFIX),
                         "lowerarm_l_armorSpace")
        self.assertEqual(weaponspace.space_name("|root|hand_r"), "hand_r_weaponSpace")

    def test_the_module_goes_through_weaponspace(self):
        with open(os.path.join(PLUGIN, "maya_scenesetup", "armor.py"),
                  encoding="utf-8") as handle:
            source = handle.read()
        for name in ("ensure_marked_space", "marked_space_of", "prune_marked", "owner_for"):
            self.assertIn("weaponspace." + name, source)
        self.assertNotIn('ls("*.', source)          # trap 70


class SelectionNamesTheCharacter(unittest.TestCase):

    def test_current_root_resolves_an_armor_piece_to_its_bone(self):
        with open(os.path.join(PLUGIN, "maya_scenesetup", "skeleton.py"),
                  encoding="utf-8") as handle:
            source = handle.read()
        self.assertIn("armor.bone_for(path)", source)


if __name__ == "__main__":
    unittest.main()


class ArmorJointsAreNoCharacter(unittest.TestCase):
    """A skeletal piece's Root has no joint parent: the character-root query leaves every
    ArmorSpaces group out, by the same marker Scene Setup writes."""

    def test_the_marker_is_one(self):
        from maya_overrig import active
        self.assertEqual(active.ARMOR_GROUP_MARKER, armor.GROUP_MARKER)

    def test_the_query_excludes_the_groups(self):
        with open(os.path.join(PLUGIN, "maya_overrig", "active.py"), encoding="utf-8") as handle:
            self.assertIn("+ armor_groups()", handle.read())

    def test_a_skeletal_piece_records_its_namespace(self):
        self.assertEqual(armor.NAMESPACE, "mayaArmorNamespace")
        with open(os.path.join(PLUGIN, "maya_scenesetup", "armor.py"), encoding="utf-8") as handle:
            source = handle.read()
        self.assertIn("deleteNamespaceContent=True", source)


def _chain(lengths, scale=1.0):
    """A straight skeleton {leaf: (parent, (x, y, z))}: root, then a bone per length up Y."""
    bones = {"root": (None, (0.0, 0.0, 0.0))}
    parent, y = "root", 0.0
    for i, length in enumerate(lengths):
        y += length * scale
        name = "b%d" % i
        bones[name] = (parent, (0.0, y, 0.0))
        parent = name
    return bones


class Clothing(unittest.TestCase):
    """2026-10-21, the Playerchar's clothes: a skinned piece fits the skeleton it was skinned on
    (the animator's pick, «same skeleton only») and is rewired onto the wearer's bones by name."""

    LENGTHS = [10.0, 12.0, 8.0, 30.0, 25.0]

    def test_the_lengths(self):
        self.assertEqual(armor.bone_lengths(_chain([3.0, 4.0])), {"b0": 3.0, "b1": 4.0})

    def test_a_twin_fits(self):
        bones = _chain(self.LENGTHS)
        self.assertEqual(armor.fit_refusal("Pants", "Manny", ["b0", "b1"], bones, bones), "")

    def test_the_same_skeleton_standing_elsewhere_fits(self):
        moved = dict((k, (p, (x + 100.0, y, z - 40.0)))
                     for k, (p, (x, y, z)) in _chain(self.LENGTHS).items())
        self.assertEqual(armor.fit_refusal("Pants", "Manny", ["b0"], _chain(self.LENGTHS), moved), "")

    def test_within_one_percent_fits(self):
        self.assertEqual(armor.fit_refusal("Pants", "Manny", ["b0"], _chain(self.LENGTHS),
                                           _chain(self.LENGTHS, 1.009)), "")

    def test_another_body_is_refused_with_its_difference(self):
        self.assertEqual(
            armor.fit_refusal("Pants", "Creep_Rig", ["b0"], _chain(self.LENGTHS),
                              _chain(self.LENGTHS, 1.24)),
            "Pants is made for another body - Creep_Rig's bones differ from its skeleton by 19 % "
            "(median)")

    def test_a_missing_bone_is_named(self):
        wearer = _chain(self.LENGTHS)
        del wearer["b4"]
        self.assertEqual(armor.fit_refusal("Helmet", "UE4_Mannequin", ["b1", "b4"], _chain(self.LENGTHS),
                                           wearer),
                         "Helmet needs b4 - UE4_Mannequin has no such bone")

    def test_many_missing_bones_are_cut_short(self):
        self.assertEqual(armor.fit_refusal("Helmet", "X", ["a", "b", "c", "d", "e"], {}, {}),
                         "Helmet needs a, b, c, d ... - X has no such bone")

    def test_short_bones_do_not_vote(self):
        piece = _chain([0.5, 20.0])
        wearer = _chain([0.9, 20.0])
        self.assertEqual(armor.fit_refusal("Pants", "Manny", [], piece, wearer), "")

    def test_no_shared_bone(self):
        self.assertEqual(armor.fit_refusal("Pants", "X", [], _chain([5.0]),
                                           {"other": (None, (0, 0, 0))}),
                         "Pants: X shares no bone with it")

    def test_the_rewire_plan(self):
        plan, missing = armor.rewire_plan([(0, "root"), (3, "pelvis"), (7, "tail")],
                                          {"root": "|w:root", "pelvis": "|w:root|w:pelvis"})
        self.assertEqual(plan, [(0, "|w:root"), (3, "|w:root|w:pelvis")])
        self.assertEqual(missing, ["tail"])


class ClothingRows(unittest.TestCase):

    def test_four_clothing_rows_after_the_tech_limb(self):
        self.assertEqual([r.key for r in catalog.ARMOR],
                         ["Tech_Limb", "Playerchar_Helmet", "Playerchar_Armor",
                          "Playerchar_Shield", "Playerchar_Pants"])

    def test_the_tech_limb_is_rigid_and_the_clothes_skinned(self):
        self.assertEqual(TECH.kind, catalog.RIGID)
        for row in catalog.ARMOR[1:]:
            self.assertEqual(row.kind, catalog.SKINNED, row.key)

    def test_each_piece_its_own_slot(self):
        slots = [r.slot for r in catalog.ARMOR]
        self.assertEqual(len(slots), len(set(slots)))
        self.assertEqual([r.slot for r in catalog.ARMOR[1:]], ["head", "torso", "back", "legs"])

    def test_the_clothes_wear_the_character_s_atlas(self):
        atlas = catalog.asset_path("Playerchar/Playerchar_Color.jpg")
        self.assertTrue(os.path.isfile(atlas), atlas)
        for row in catalog.ARMOR[1:]:
            self.assertEqual(row.texture, atlas, row.key)
            self.assertEqual(catalog.missing(row), "", row.key)

    def test_a_clothing_file_is_a_group_and_a_skeleton(self):
        for row in catalog.ARMOR[1:]:
            with open(row.path, encoding="utf-8", errors="replace") as handle:
                text = handle.read()
            self.assertIn('createNode transform -n "%s";' % row.key, text)
            self.assertIn('createNode joint -n "root";', text)
            self.assertEqual(text.count('createNode joint -n "'), 93, row.key)
            self.assertIn("createNode skinCluster", text)
            self.assertIn('setAttr ".it" no;', text)       # the meshes do not inherit
            for word in ("createNode script", "C:/", "Downloads", "vaccine"):
                self.assertNotIn(word, text, row.key)

    def test_a_skinned_row_goes_its_own_way(self):
        import inspect
        source = inspect.getsource(armor.equip)
        self.assertIn("_equip_clothing", source)
        self.assertIn("catalog.SKINNED", source)
