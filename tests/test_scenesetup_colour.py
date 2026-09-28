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


class Shader(unittest.TestCase):
    """One shader for every model and rig we put in the scene (2026-09-25, «на все наши
    модели и риги нужно настроить единый шейдер, такой чтобы он смотрелся хорошо в мае и в
    каскадере»): a phong carrying the values Cascadeur writes into its own FBX -- diffuse 1,
    specular 0.2, shininess 20, no reflection. The blinn before it (2026-09-03, still shiny,
    which is why it is not a lambert) exported DiffuseFactor 0.8 and ReflectionFactor 0.5."""

    def test_the_shader_is_a_phong(self):
        self.assertEqual(colour.SHADER, "phong")

    def test_the_look_is_cascadeurs_own(self):
        self.assertEqual(colour.LOOK, {"diffuse": 1.0, "specularColor": (0.2, 0.2, 0.2),
                                       "cosinePower": 20.0, "reflectivity": 0.0})

    def test_make_material_creates_that_type_wearing_the_look(self):
        real = colour.cmds
        fake = FakeCmds()
        colour.cmds = fake
        try:
            material, _ = colour.make_material((0.8, 0.25, 0.22), "Manny")
        finally:
            colour.cmds = real
        self.assertEqual(fake.kinds, [colour.SHADER])
        for attr, value in colour.LOOK.items():
            want = tuple(value) if isinstance(value, tuple) else (value,)
            self.assertEqual(fake.colours[material + "." + attr], want, attr)
        self.assertEqual(fake.colours[material + ".color"], (0.8, 0.25, 0.22))


class Unambiguous(unittest.TestCase):
    """`cmds.skinCluster(q=True, geometry=True)` answers with SHORT names --
    measured 2026-09-03: `['Hands_1PShape']`, not a path. Maya hands back
    the shortest UNIQUE name, so one path normally comes out; two Mannys in
    one scene share every leaf below the top node, and the next thing that
    happens to these shapes is a `forceElement`. A guess there repaints
    somebody else's character, so the ambiguous name is dropped."""

    class Resolver(object):
        def __init__(self, table):
            self.table = table

        def ls(self, name, **kwargs):
            return list(self.table.get(name, []))

    def setUp(self):
        self.real = colour.cmds

    def tearDown(self):
        colour.cmds = self.real

    def test_one_path_resolves(self):
        colour.cmds = self.Resolver({"bodyShape": ["|rig|body|bodyShape"]})
        self.assertEqual(colour.unambiguous("bodyShape"),
                         "|rig|body|bodyShape")

    def test_two_paths_are_dropped(self):
        colour.cmds = self.Resolver(
            {"Hands_1PShape": ["|a|Hands_1P|Hands_1PShape",
                               "|b|Hands_1P|Hands_1PShape"]})
        self.assertIsNone(colour.unambiguous("Hands_1PShape"))

    def test_nothing_resolves_to_nothing(self):
        colour.cmds = self.Resolver({})
        self.assertIsNone(colour.unambiguous("gone"))


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
        self.kinds = []
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
        self.kinds.append(kind)
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


class PaintingFresh(unittest.TestCase):
    """An Add paints a NEW material whatever the asset wears (2026-09-07):
    the shipped rig file carries the animator's own red blinn, and `paint`
    would have reused it and brought every rig in red, swatch ignored."""

    def setUp(self):
        self.real = colour.cmds

    def tearDown(self):
        colour.cmds = self.real

    def test_a_marked_material_is_not_reused(self):
        fake = FakeCmds(assigned={"|bodyShape": "skeldarColour_red"},
                        ours=["skeldarColour_red"])
        colour.cmds = fake
        material = colour.paint_fresh(["|bodyShape"], (0.25, 0.52, 0.85),
                                      "Manny_Rig")
        self.assertTrue(fake.created)
        self.assertNotEqual(material, "skeldarColour_red")
        self.assertNotIn("skeldarColour_red.color", fake.colours)
        self.assertTrue(fake.forced)

    def test_a_bare_mesh_is_painted_like_paint_does(self):
        fake = FakeCmds(assigned={"|bodyShape": "lambert1"})
        colour.cmds = fake
        colour.paint_fresh(["|bodyShape"], (0.8, 0.25, 0.22), "Manny_Rig")
        self.assertTrue(fake.created)
        self.assertTrue(fake.forced)

    def test_no_meshes_is_a_quiet_no_op(self):
        fake = FakeCmds()
        colour.cmds = fake
        self.assertIsNone(colour.paint_fresh([], (0.8, 0.25, 0.22), "x"))
        self.assertEqual(fake.created, [])

    def test_paint_nodes_goes_the_fresh_way(self):
        """Only Add Character calls it, and an import's nodes are fresh."""
        with open(colour.__file__.replace(".pyc", ".py"),
                  encoding="utf-8") as handle:
            body = handle.read().split("def paint_nodes")[1]
        self.assertIn("paint_fresh(", body)


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


class TextureCmds(object):
    """A scene with nodes, attributes and connections: enough to build a
    textured material and find it again."""

    def __init__(self, panels=None):
        self.kinds = {}                        # node -> type
        self.attrs = {}                        # "node.attr" -> value
        self.links = []                        # (source plug, target plug)
        self.forced = []
        self.panels = dict(panels or {})       # panel -> textures on?
        self.edited = []

    def shadingNode(self, kind, **kwargs):
        name = kwargs.get("name", kind)
        while name in self.kinds:
            name += "1"
        self.kinds[name] = kind
        return name

    def sets(self, *args, **kwargs):
        if kwargs.get("empty"):
            name = kwargs.get("name", "SG")
            self.kinds[name] = "shadingEngine"
            return name
        self.forced.append((list(args[0]), kwargs.get("forceElement")))
        return kwargs.get("forceElement")

    def connectAttr(self, source, target, **kwargs):
        self.links.append((source, target))

    def setAttr(self, plug, *values, **kwargs):
        self.attrs[plug] = values[0] if len(values) == 1 else tuple(values)

    def getAttr(self, plug, **kwargs):
        return self.attrs[plug]

    def addAttr(self, node, **kwargs):
        self.attrs[node + "." + kwargs["longName"]] = ""

    def attributeQuery(self, name, **kwargs):
        return kwargs.get("node", "") + "." + name in self.attrs

    def ls(self, *args, **kwargs):
        if kwargs.get("materials"):
            return [n for n, k in self.kinds.items() if k in ("phong", "lambert")]
        return list(args[0]) if args else []

    def listConnections(self, plug, **kwargs):
        found = []
        for source, target in self.links:
            if target == plug:
                found.append(source.split(".")[0])
            elif source == plug:
                found.append(target.split(".")[0])
        kind = kwargs.get("type")
        return [n for n in found if not kind or self.kinds.get(n) == kind]

    def getPanel(self, **kwargs):
        if kwargs.get("type") == "modelPanel":
            return list(self.panels)
        if kwargs.get("visiblePanels"):
            #  what a Maya whose window was never exposed answers
            return None
        return "modelPanel" if kwargs["typeOf"] in self.panels else "outlinerPanel"

    def modelEditor(self, panel, **kwargs):
        if kwargs.get("query"):
            return self.panels[panel]
        self.edited.append(panel)
        self.panels[panel] = kwargs["displayTextures"]


class Textured(unittest.TestCase):
    """A weapon that arrives in its own texture (2026-09-28, Spear 03):
    the one shader wearing LOOK, a file node on its colour, and a marker
    that is NOT the palette's - so no colour scan reads it and Recolour
    builds a colour material over it."""

    IMAGE = "C:/prefs/SkeldarAnim/assets/Spear_03.png"

    def setUp(self):
        self.real = colour.cmds
        self.fake = TextureCmds()
        colour.cmds = self.fake

    def tearDown(self):
        colour.cmds = self.real

    def test_the_one_shader_with_the_image_on_its_colour(self):
        material = colour.paint_texture(["|spearShape"], self.IMAGE, "Spear_03")
        self.assertEqual(self.fake.kinds[material], colour.SHADER)
        for attr, value in colour.LOOK.items():
            self.assertEqual(self.fake.attrs[material + "." + attr], value, attr)
        files = [n for n, k in self.fake.kinds.items() if k == "file"]
        self.assertEqual(len(files), 1)
        self.assertEqual(self.fake.attrs[files[0] + ".fileTextureName"],
                         self.IMAGE)
        self.assertIn((files[0] + ".outColor", material + ".color"),
                      self.fake.links)

    def test_the_file_reads_its_uvs_from_a_place2d(self):
        colour.paint_texture(["|spearShape"], self.IMAGE, "Spear_03")
        place = [n for n, k in self.fake.kinds.items()
                 if k == "place2dTexture"][0]
        targets = [t for s, t in self.fake.links if s.startswith(place + ".")]
        self.assertTrue(any(t.endswith(".uvCoord") for t in targets))
        self.assertTrue(any(t.endswith(".uvFilterSize") for t in targets))

    def test_the_shapes_wear_it(self):
        material = colour.paint_texture(["|spearShape"], self.IMAGE, "Spear_03")
        engine = colour.engine_of(material)
        self.assertEqual(self.fake.forced, [(["|spearShape"], engine)])

    def test_marked_as_textured_never_as_a_palette_colour(self):
        material = colour.paint_texture(["|spearShape"], self.IMAGE, "Spear_03")
        self.assertEqual(self.fake.attrs[material + "." + colour.TEXTURE_MARKER],
                         self.IMAGE)
        self.assertFalse(colour.is_ours(material))
        self.assertNotIn(material, colour.our_materials())

    def test_a_second_add_reuses_the_material(self):
        first = colour.paint_texture(["|a"], self.IMAGE, "Spear_03")
        second = colour.paint_texture(["|b"], self.IMAGE, "Spear_03")
        self.assertEqual(first, second)
        self.assertEqual(
            len([n for n, k in self.fake.kinds.items() if k == "file"]), 1)

    def test_another_image_is_another_material(self):
        first = colour.paint_texture(["|a"], self.IMAGE, "Spear_03")
        second = colour.paint_texture(["|b"], "C:/x/Axe.png", "Axe")
        self.assertNotEqual(first, second)

    def test_no_meshes_is_a_quiet_no_op(self):
        self.assertIsNone(colour.paint_texture([], self.IMAGE, "Spear_03"))
        self.assertEqual(self.fake.kinds, {})


class ShowTextures(unittest.TestCase):
    """A textured material reads flat grey in a viewport with Textures off,
    so a textured Add turns them on where they are off - and only there."""

    def setUp(self):
        self.real = colour.cmds

    def tearDown(self):
        colour.cmds = self.real

    def test_only_the_model_panels_that_had_them_off(self):
        fake = TextureCmds(panels={"modelPanel4": False, "modelPanel1": True})
        colour.cmds = fake
        self.assertEqual(colour.show_textures(), ["modelPanel4"])
        self.assertEqual(fake.edited, ["modelPanel4"])
        self.assertTrue(fake.panels["modelPanel4"])

    def test_nothing_to_do_is_nothing_done(self):
        fake = TextureCmds(panels={"modelPanel4": True})
        colour.cmds = fake
        self.assertEqual(colour.show_textures(), [])
        self.assertEqual(fake.edited, [])


if __name__ == "__main__":
    unittest.main()
