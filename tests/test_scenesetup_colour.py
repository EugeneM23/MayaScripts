"""Tests for the colour a character or weapon arrives wearing.

The decisions worth pinning are pure: which palette entry is still free,
whether two colours read as the same one through Maya's floats, what the
material is called, and how the meshes of a character are gathered from two
sources. The assignment itself is proved live by
docs/superpowers/plans/verify_scenesetup_colour.py -- in this project a
green unit run has repeatedly sat beside a wrong scene.
"""

import sys
import types
import unittest


def _install_fake_maya():
    """Let colour import without Maya. See CLAUDE.md on rebinding."""
    try:
        import maya.cmds  # noqa: F401
        return
    except ImportError:
        pass
    maya = types.ModuleType("maya")
    cmds = types.ModuleType("maya.cmds")
    mel = types.ModuleType("maya.mel")
    maya.cmds = cmds
    maya.mel = mel
    sys.modules.setdefault("maya", maya)
    sys.modules["maya.cmds"] = cmds
    sys.modules["maya.mel"] = mel


_install_fake_maya()

from maya_scenesetup import colour  # noqa: E402


class Palette(unittest.TestCase):
    """The table itself carries requirements, not just values."""

    def test_eight_named_colours(self):
        self.assertEqual(len(colour.PALETTE), 8)
        names = [entry.name for entry in colour.PALETTE]
        self.assertEqual(len(set(names)), 8)

    def test_no_entry_is_near_black(self):
        """`character.needs_grey` reads a near-black untextured material as
        an import that lost its textures and greys it out. A palette entry
        down there would be overwritten from under us on the FBX path."""
        for entry in colour.PALETTE:
            self.assertGreater(max(entry.rgb), 0.2, entry.name)

    def test_no_entry_is_maya_default_grey(self):
        """A coloured character must never read as an uncoloured one."""
        for entry in colour.PALETTE:
            self.assertFalse(colour.same_colour(entry.rgb, (0.5, 0.5, 0.5)),
                             entry.name)

    def test_entries_are_distinguishable_from_each_other(self):
        """The whole feature is telling two figures apart at a glance."""
        for i, first in enumerate(colour.PALETTE):
            for second in colour.PALETTE[i + 1:]:
                self.assertFalse(colour.same_colour(first.rgb, second.rgb),
                                 "{0} vs {1}".format(first.name, second.name))

    def test_channels_are_in_range(self):
        for entry in colour.PALETTE:
            for channel in entry.rgb:
                self.assertGreaterEqual(channel, 0.0)
                self.assertLessEqual(channel, 1.0)


class SameColour(unittest.TestCase):
    """A colour written as a float and read back through Maya is not
    bit-identical. An exact compare reports every colour as still free."""

    def test_identical_is_same(self):
        self.assertTrue(colour.same_colour((0.8, 0.25, 0.22),
                                           (0.8, 0.25, 0.22)))

    def test_float_noise_is_same(self):
        self.assertTrue(colour.same_colour((0.8, 0.25, 0.22),
                                           (0.80000001, 0.2499999, 0.22)))

    def test_a_different_colour_is_not(self):
        self.assertFalse(colour.same_colour((0.8, 0.25, 0.22),
                                            (0.25, 0.52, 0.85)))

    def test_none_is_never_the_same(self):
        self.assertFalse(colour.same_colour(None, (0.5, 0.5, 0.5)))
        self.assertFalse(colour.same_colour((0.5, 0.5, 0.5), None))

    def test_a_short_triple_is_not_the_same(self):
        """getAttr on a colour plug can only give three, but a caller that
        hands over two must not silently match."""
        self.assertFalse(colour.same_colour((0.5, 0.5), (0.5, 0.5, 0.5)))


class NextColour(unittest.TestCase):
    """Which colour the next Add brings. Read from the scene, so an empty
    scene, a half-used one and a full one are all normal."""

    def test_empty_scene_takes_the_first(self):
        self.assertEqual(colour.next_colour([]), colour.PALETTE[0])
        self.assertEqual(colour.next_colour(None), colour.PALETTE[0])

    def test_the_first_free_one_wins(self):
        used = [colour.PALETTE[0].rgb, colour.PALETTE[1].rgb]
        self.assertEqual(colour.next_colour(used), colour.PALETTE[2])

    def test_a_gap_is_filled_before_moving_on(self):
        """A deleted character frees its colour, and the next Add should
        take it rather than walking off the end of the palette."""
        used = [colour.PALETTE[0].rgb, colour.PALETTE[2].rgb]
        self.assertEqual(colour.next_colour(used), colour.PALETTE[1])

    def test_noisy_values_still_count_as_used(self):
        used = [tuple(c + 1e-6 for c in colour.PALETTE[0].rgb)]
        self.assertEqual(colour.next_colour(used), colour.PALETTE[1])

    def test_a_colour_outside_the_palette_blocks_nothing(self):
        self.assertEqual(colour.next_colour([(0.1, 0.9, 0.1)]),
                         colour.PALETTE[0])

    def test_a_full_palette_wraps_deterministically(self):
        used = [entry.rgb for entry in colour.PALETTE]
        self.assertEqual(colour.next_colour(used), colour.PALETTE[0])
        self.assertEqual(colour.next_colour(used + [(0.1, 0.1, 0.9)]),
                         colour.PALETTE[1])

    def test_it_is_pure(self):
        used = [colour.PALETTE[0].rgb]
        colour.next_colour(used)
        self.assertEqual(used, [colour.PALETTE[0].rgb])


class Naming(unittest.TestCase):
    """The name is for the Hypershade and the status line. Nothing is ever
    FOUND by it -- Maya uniquifies, and every tool in this repo that
    identified a node by name has paid for it."""

    def test_a_palette_colour_is_named(self):
        self.assertEqual(colour.colour_name(colour.PALETTE[0].rgb), "red")

    def test_noise_still_names_the_palette_entry(self):
        noisy = tuple(c + 1e-7 for c in colour.PALETTE[3].rgb)
        self.assertEqual(colour.colour_name(noisy), colour.PALETTE[3].name)

    def test_a_hand_dialled_colour_is_custom(self):
        self.assertEqual(colour.colour_name((0.11, 0.93, 0.44)), "custom")

    def test_no_colour_at_all_is_named(self):
        self.assertEqual(colour.colour_name(None), "custom")

    def test_the_material_name_is_a_legal_maya_name(self):
        for entry in colour.PALETTE:
            name = colour.material_name(entry.rgb)
            self.assertTrue(name.replace("_", "").isalnum(), name)
            self.assertFalse(name[0].isdigit(), name)

    def test_the_material_name_carries_the_colour(self):
        self.assertIn("red", colour.material_name(colour.PALETTE[0].rgb))


class MeshSet(unittest.TestCase):
    """Manny's six meshes sit at WORLD level, not under the skeleton, so the
    skinCluster route is the one that finds them and the DAG walk finds
    nothing. Both are kept: the second covers unskinned geometry parented
    into the character by hand."""

    def test_the_union_keeps_order_and_deduplicates(self):
        self.assertEqual(
            colour.mesh_set(["|bodyShape", "|headShape"],
                            ["|headShape", "|propShape"]),
            ["|bodyShape", "|headShape", "|propShape"])

    def test_skinned_alone_is_enough(self):
        self.assertEqual(colour.mesh_set(["|bodyShape"], []), ["|bodyShape"])

    def test_descendants_alone_are_enough(self):
        self.assertEqual(colour.mesh_set([], ["|propShape"]), ["|propShape"])

    def test_nothing_is_an_empty_list(self):
        self.assertEqual(colour.mesh_set(None, None), [])


class Marker(unittest.TestCase):
    """Identity by attribute, the same schema as `mayaWeapon` on the weapon
    geometry and `rigPickerRoot` on the rig manifests."""

    def test_the_marker_is_a_legal_attribute_name(self):
        self.assertTrue(colour.MARKER.isalnum())
        self.assertFalse(colour.MARKER[0].isdigit())

    def test_the_marker_is_not_the_weapon_marker(self):
        from maya_scenesetup import bonedrive
        self.assertNotEqual(colour.MARKER, bonedrive.MARKER)


class FakeCmds(object):
    """Just enough scene to exercise the reuse-or-create decision."""

    def __init__(self, assigned=None, ours=()):
        self.assigned = dict(assigned or {})   # shape -> material
        self.ours = set(ours)
        self.engines = {}                      # material -> shading engine
        self.colours = {}                      # material -> rgb
        self.created = []
        self.forced = []

    # -- reads
    def ls(self, *args, **kwargs):
        if kwargs.get("materials"):
            return sorted(set(self.assigned.values()) | self.ours)
        items = args[0] if args else []
        if isinstance(items, str):
            items = [items]
        return list(items or [])

    def attributeQuery(self, name, **kwargs):
        return kwargs.get("node") in self.ours and name == colour.MARKER

    def listSets(self, **kwargs):
        shape = kwargs.get("object")
        material = self.assigned.get(shape)
        return ["SG_" + material] if material else []

    def listConnections(self, plug, **kwargs):
        node = plug.split(".")[0]
        if kwargs.get("type") == "shadingEngine":
            return [self.engines.get(node, "SG_" + node)]
        if plug.endswith(".surfaceShader"):
            for material, engine in self.engines.items():
                if engine == node:
                    return [material]
            return [node[3:]] if node.startswith("SG_") else []
        return []

    def getAttr(self, plug, **kwargs):
        return [self.colours.get(plug, (0.0, 0.0, 0.0))]

    def objExists(self, name):
        return True

    # -- writes
    def setAttr(self, plug, *values, **kwargs):
        self.colours[plug] = tuple(values)

    def shadingNode(self, kind, **kwargs):
        name = kwargs.get("name", kind)
        self.created.append(name)
        self.ours.add(name)
        return name

    def sets(self, *args, **kwargs):
        if kwargs.get("empty"):
            name = kwargs.get("name", "SG")
            return name
        self.forced.append((list(args[0]), kwargs.get("forceElement")))
        return kwargs.get("forceElement")

    def addAttr(self, node, **kwargs):
        self.ours.add(node)

    def connectAttr(self, source, target, **kwargs):
        self.engines[source.split(".")[0]] = target.split(".")[0]

    def undoInfo(self, **kwargs):
        pass


class Painting(unittest.TestCase):
    """Reuse ours, create otherwise. A live recolour must be one setAttr --
    re-creating the material on every swatch drag would leave the scene
    full of orphans."""

    def setUp(self):
        self.real = colour.cmds

    def tearDown(self):
        colour.cmds = self.real

    def test_a_bare_mesh_gets_a_new_material(self):
        fake = FakeCmds(assigned={"|bodyShape": "lambert1"})
        colour.cmds = fake
        colour.paint(["|bodyShape"], (0.8, 0.25, 0.22), "Manny")
        self.assertTrue(fake.created)
        self.assertTrue(fake.forced)

    def test_our_material_is_recoloured_in_place(self):
        fake = FakeCmds(assigned={"|bodyShape": "skeldarColour_red"},
                        ours=["skeldarColour_red"])
        colour.cmds = fake
        colour.paint(["|bodyShape"], (0.25, 0.52, 0.85), "Manny")
        self.assertEqual(fake.created, [])
        self.assertEqual(fake.colours["skeldarColour_red.color"],
                         (0.25, 0.52, 0.85))

    def test_somebody_elses_material_is_never_recoloured(self):
        """Manny's own materials are left alone; ours is added over the
        assignment instead. Recolouring theirs would change every other
        mesh using it, anywhere in the scene."""
        fake = FakeCmds(assigned={"|bodyShape": "M_Manny_Body"})
        colour.cmds = fake
        colour.paint(["|bodyShape"], (0.8, 0.25, 0.22), "Manny")
        self.assertNotIn("M_Manny_Body.color", fake.colours)
        self.assertTrue(fake.created)

    def test_no_meshes_is_a_quiet_no_op(self):
        fake = FakeCmds()
        colour.cmds = fake
        self.assertIsNone(colour.paint([], (0.8, 0.25, 0.22), "Manny"))
        self.assertEqual(fake.created, [])


class ColourOf(unittest.TestCase):
    """What the swatch shows: our colour, or None when there is none. The
    window's standing rule is that the numbers on screen are never a lie
    about the scene."""

    def setUp(self):
        self.real = colour.cmds

    def tearDown(self):
        colour.cmds = self.real

    def test_ours_reads_back(self):
        fake = FakeCmds(assigned={"|bodyShape": "skeldarColour_red"},
                        ours=["skeldarColour_red"])
        fake.colours["skeldarColour_red.color"] = (0.8, 0.25, 0.22)
        colour.cmds = fake
        self.assertTrue(colour.same_colour(colour.colour_of(["|bodyShape"]),
                                           (0.8, 0.25, 0.22)))

    def test_a_foreign_material_reads_as_nothing(self):
        fake = FakeCmds(assigned={"|bodyShape": "M_Manny_Body"})
        colour.cmds = fake
        self.assertIsNone(colour.colour_of(["|bodyShape"]))

    def test_no_meshes_reads_as_nothing(self):
        colour.cmds = FakeCmds()
        self.assertIsNone(colour.colour_of([]))


if __name__ == "__main__":
    unittest.main()
