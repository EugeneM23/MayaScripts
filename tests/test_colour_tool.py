"""The Colour shelf tool: target resolution, and the policy around it.

The tool is a panel over `maya_scenesetup.colour` and holds no colour
policy of its own -- a second copy of "which colour is free" would answer
differently from Scene Setup's swatch within a week. So what is tested
here is what this module actually decides: WHAT a press paints.
"""

import unittest

import maya_colour as mc
from maya_scenesetup import colour as colouring

from tests.uifakes import FakeUiCmds, inside, made


class TestLeaf(unittest.TestCase):

    def test_the_last_component(self):
        self.assertEqual(mc.leaf("|root|pelvis|spine_01"), "spine_01")

    def test_a_namespace_is_stripped(self):
        """A referenced or imported character wears one, and the leaf is
        the material's name -- `ns:root` is not a legal name component."""
        self.assertEqual(mc.leaf("|ns:root|ns:pelvis"), "pelvis")

    def test_a_bare_name_survives(self):
        self.assertEqual(mc.leaf("root"), "root")

    def test_nothing_is_empty(self):
        self.assertEqual(mc.leaf(None), "")


class TestChooseSource(unittest.TestCase):
    """The selection first, the connected character second, a refusal
    third -- the same order Import, Export and Camera Setup use."""

    def test_the_selection_wins(self):
        self.assertEqual(mc.choose_source(["|a"], "|connected"), ["|a"])

    def test_the_connect_is_the_fallback(self):
        self.assertEqual(mc.choose_source([], "|connected"), ["|connected"])

    def test_nothing_at_all_is_a_refusal_not_a_guess(self):
        self.assertEqual(mc.choose_source([], None), [])
        self.assertEqual(mc.choose_source(None, None), [])

    def test_an_empty_string_is_not_a_selection(self):
        self.assertEqual(mc.choose_source(["", None], "|c"), ["|c"])

    def test_several_selected_all_come_through(self):
        self.assertEqual(mc.choose_source(["|a", "|b"], "|c"),
                         ["|a", "|b"])


class TestMergeTargets(unittest.TestCase):

    def target(self, label, shapes):
        return mc.Target(label, list(shapes), label)

    def test_the_same_shapes_twice_is_one_target(self):
        """Three bones of one character resolve to that character three
        times over; painting it three times would work and report
        nonsense."""
        one = self.target("root", ["|a|aShape"])
        two = self.target("root", ["|a|aShape"])
        self.assertEqual(len(mc.merge_targets([one, two])), 1)

    def test_the_first_label_wins(self):
        merged = mc.merge_targets([self.target("first", ["|s"]),
                                   self.target("second", ["|s"])])
        self.assertEqual(merged[0].label, "first")

    def test_order_is_kept(self):
        merged = mc.merge_targets([self.target("a", ["|1"]),
                                   self.target("b", ["|2"])])
        self.assertEqual([t.label for t in merged], ["a", "b"])

    def test_different_shapes_stay_apart(self):
        self.assertEqual(len(mc.merge_targets([self.target("a", ["|1"]),
                                               self.target("b", ["|2"])])),
                         2)

    def test_the_same_shapes_in_a_different_order_is_still_one(self):
        self.assertEqual(len(mc.merge_targets([
            self.target("a", ["|1", "|2"]),
            self.target("b", ["|2", "|1"])])), 1)

    def test_a_target_with_no_shapes_is_dropped(self):
        """A character whose meshes are all gone paints nothing, and
        saying "painted" would be a lie."""
        self.assertEqual(mc.merge_targets([self.target("empty", [])]), [])

    def test_a_none_is_dropped(self):
        self.assertEqual(mc.merge_targets([None]), [])

    def test_nothing_in_nothing_out(self):
        self.assertEqual(mc.merge_targets([]), [])


class TestMessages(unittest.TestCase):

    def target(self, label):
        return mc.Target(label, ["|s" + label], label)

    def test_one_target_is_named(self):
        message = mc.painted_message([self.target("root")], (0.8, 0.25, 0.22))
        self.assertIn("root", message)
        self.assertIn("red", message)

    def test_several_are_counted(self):
        message = mc.painted_message(
            [self.target("a"), self.target("b")], (0.8, 0.25, 0.22))
        self.assertIn("2", message)
        self.assertIn("red", message)

    def test_none_says_what_to_do_about_it(self):
        message = mc.painted_message([], (0.8, 0.25, 0.22))
        self.assertEqual(message, mc.NOTHING_TO_PAINT)
        self.assertIn("select", message)

    def test_an_off_palette_colour_is_named_custom(self):
        """`colour_name` is the one authority on that, and it lives in
        the module that owns the palette."""
        self.assertIn(colouring.CUSTOM,
                      mc.painted_message([self.target("root")],
                                         (0.11, 0.22, 0.33)))

    def test_the_taken_line_lists_the_names(self):
        line = mc.taken_message([("red", (0.8, 0.25, 0.22)),
                                 ("teal", (0.2, 0.7, 0.68))])
        self.assertIn("red", line)
        self.assertIn("teal", line)

    def test_the_taken_line_says_so_when_nothing_is_painted(self):
        self.assertIn("nothing", mc.taken_message([]))

    def test_a_colour_worn_twice_is_listed_once(self):
        line = mc.taken_message([("red", (0.8, 0.25, 0.22)),
                                 ("red", (0.8, 0.25, 0.22))])
        self.assertEqual(line.count("red"), 1)


def _source():
    """The tool's own text, for the "no second copy" checks."""
    with open(mc.__file__, encoding="utf-8") as handle:
        return handle.read()


class TestNoPolicyOfItsOwn(unittest.TestCase):
    """The palette, the free colour and the painting all belong to
    `maya_scenesetup.colour`. A copy here would drift."""

    def test_the_palette_is_not_redefined(self):
        source = _source()
        for hue in ("0.80, 0.25, 0.22", "0.25, 0.52, 0.85"):
            self.assertNotIn(hue, source,
                             "the palette lives in maya_scenesetup.colour")

    def test_it_reads_the_shared_palette(self):
        self.assertIs(mc.colouring, colouring)
        self.assertEqual(len(colouring.PALETTE), 8)

    def test_the_grid_covers_every_palette_entry(self):
        """Four across; a row of eight would not fit and a missing entry
        would be a colour with no button."""
        self.assertEqual(mc.COLUMNS, 4)
        self.assertEqual(len(colouring.PALETTE) % mc.COLUMNS, 0)

    def test_no_free_colour_logic_of_its_own(self):
        source = _source()
        self.assertIn("colouring.free_colour()", source)
        self.assertNotIn("def free_colour", source)

    def test_no_painting_of_its_own(self):
        source = _source()
        self.assertIn("colouring.paint(", source)
        self.assertNotIn("shadingNode", source)
        self.assertNotIn("forceElement", source)


class FakeCmds(object):
    """Enough of `maya.cmds` for the target resolution."""

    def __init__(self, types=None, parents=None, meshes=None, markers=()):
        self.types = dict(types or {})
        self.parents = dict(parents or {})
        self.meshes = dict(meshes or {})
        self.markers = set(markers)
        self.chunks = []
        self.messages = []

    def attributeQuery(self, attr, **kwargs):
        node = kwargs.get("node")
        return attr == "mayaWeapon" and node in self.markers

    def objExists(self, name):
        return name in self.types

    def nodeType(self, name):
        return self.types.get(name, "transform")

    def ls(self, *args, **kwargs):
        if kwargs.get("selection"):
            return list(self.selection)
        return [args[0]] if args else []

    def listRelatives(self, name, **_kwargs):
        parent = self.parents.get(name)
        return [parent] if parent else []

    def undoInfo(self, **kwargs):
        self.chunks.append(kwargs)

    def headsUpMessage(self, text, **_kwargs):
        self.messages.append(text)

    def control(self, *_a, **_kw):
        return False

    def text(self, *_a, **_kw):
        return ""


class TestWeaponFilter(unittest.TestCase):
    """A character's meshes are found partly by a DAG walk, on purpose --
    and a sword in the hand is caught by exactly that walk. A weapon has
    its own colour by design, and `colour.paint` reuses whatever material
    of ours is already on the shapes, so leaving the sword in the
    character's list makes the two share one material: painting the SWORD
    then repaints the character. Measured live 2026-09-03."""

    def setUp(self):
        self.real = mc.cmds
        self.fake = FakeCmds(
            types={"|root": "joint", "|root|hand": "joint",
                   "|root|hand|Sword": "transform",
                   "|root|hand|Sword|SwordShape": "mesh",
                   "|root|hand|Pack": "transform",
                   "|root|hand|Pack|PackShape": "mesh",
                   "|Body|BodyShape": "mesh", "|Body": "transform"},
            parents={"|root|hand": "|root",
                     "|root|hand|Sword": "|root|hand",
                     "|root|hand|Sword|SwordShape": "|root|hand|Sword",
                     "|root|hand|Pack": "|root|hand",
                     "|root|hand|Pack|PackShape": "|root|hand|Pack",
                     "|Body|BodyShape": "|Body"},
            markers={"|root|hand|Sword"})
        mc.cmds = self.fake

    def tearDown(self):
        mc.cmds = self.real

    def test_the_marker_comes_from_the_module_that_owns_it(self):
        from maya_scenesetup import bonedrive
        self.assertEqual(mc.weapon_marker(), bonedrive.MARKER)
        self.assertEqual(bonedrive.MARKER, "mayaWeapon")

    def test_a_marked_node_is_a_weapon(self):
        self.assertTrue(mc.is_weapon("|root|hand|Sword"))

    def test_so_is_anything_under_it(self):
        """The marker sits on the weapon's transform; its shape carries
        nothing."""
        self.assertTrue(mc.is_weapon("|root|hand|Sword|SwordShape"))

    def test_the_hand_holding_it_is_not(self):
        self.assertFalse(mc.is_weapon("|root|hand"))

    def test_an_unmarked_prop_is_not(self):
        self.assertFalse(mc.is_weapon("|root|hand|Pack"))

    def test_the_weapon_s_shape_is_dropped(self):
        kept = mc.without_weapons(["|Body|BodyShape",
                                   "|root|hand|Sword|SwordShape"])
        self.assertEqual(kept, ["|Body|BodyShape"])

    def test_an_unmarked_prop_travels_with_the_figure(self):
        kept = mc.without_weapons(["|Body|BodyShape",
                                   "|root|hand|Pack|PackShape"])
        self.assertEqual(kept, ["|Body|BodyShape",
                                "|root|hand|Pack|PackShape"])

    def test_nothing_in_nothing_out(self):
        self.assertEqual(mc.without_weapons([]), [])
        self.assertEqual(mc.without_weapons(None), [])

    def test_a_character_of_only_weapons_paints_nothing(self):
        """And `merge_targets` then drops it, rather than reporting a
        paint that touched no shape."""
        self.assertEqual(
            mc.without_weapons(["|root|hand|Sword|SwordShape"]), [])


class TestTargetResolution(unittest.TestCase):
    """`target_for` is the whole decision: a bone means the character, a
    mesh means the mesh. The order of those two questions is what keeps
    them disjoint."""

    def setUp(self):
        self.real_cmds = mc.cmds
        self.real_colour = mc.colouring
        #  |root is a joint, |root|hand_r is a joint, and the sword mesh
        #  hangs under the hand -- the real shape of this rig.
        self.fake = FakeCmds(
            types={"|root": "joint", "|root|hand_r": "joint",
                   "|root|hand_r|Sword": "transform",
                   "|Ctrl": "transform", "|Skin": "transform"},
            parents={"|root|hand_r": "|root",
                     "|root|hand_r|Sword": "|root|hand_r"})
        mc.cmds = self.fake

        painted = {}

        class FakeColour(object):
            CUSTOM = colouring.CUSTOM
            PALETTE = colouring.PALETTE

            @staticmethod
            def mesh_shapes(nodes):
                found = {"|root|hand_r|Sword": ["|SwordShape"],
                         "|Skin": ["|SkinShape"]}
                out = []
                for node in nodes:
                    out += found.get(node, [])
                return out

            @staticmethod
            def character_meshes(root):
                return ["|BodyShape", "|HandsShape"] if root else []

            @staticmethod
            def colour_name(rgb):
                return colouring.colour_name(rgb)

            @staticmethod
            def paint(shapes, rgb, key):
                painted[key] = (tuple(shapes), tuple(rgb))
                return "mat_" + key

        self.painted = painted
        mc.colouring = FakeColour

    def tearDown(self):
        mc.cmds = self.real_cmds
        mc.colouring = self.real_colour

    def test_a_bone_means_the_whole_character(self):
        target = mc.target_for("|root|hand_r")
        self.assertEqual(target.label, "root")
        self.assertEqual(target.shapes, ["|BodyShape", "|HandsShape"])

    def test_it_climbs_to_the_TOPMOST_joint(self):
        """The nearest joint above a hand is the hand; a character is
        painted whole."""
        self.assertEqual(mc.skeleton_root("|root|hand_r|Sword"), "|root")

    def test_the_root_joint_itself_resolves_to_itself(self):
        self.assertEqual(mc.skeleton_root("|root"), "|root")

    def test_a_node_with_no_joint_above_it_has_no_skeleton(self):
        self.assertIsNone(mc.skeleton_root("|Ctrl"))

    def test_a_mesh_means_that_mesh(self):
        """The sword IS the geometry, which is how the weapon tool
        works -- an animator clicking a sword wants the sword."""
        target = mc.target_for("|root|hand_r|Sword")
        self.assertEqual(target.label, "Sword")
        self.assertEqual(target.shapes, ["|SwordShape"])

    def test_the_joint_question_comes_first(self):
        """`hand_r` has the sword parented under it, so a mesh-first rule
        would resolve a hand-bone click to the sword."""
        self.assertEqual(mc.target_for("|root|hand_r").shapes,
                         ["|BodyShape", "|HandsShape"])

    def test_a_control_names_nothing(self):
        self.assertIsNone(mc.target_for("|Ctrl"))

    def test_a_node_that_is_gone_names_nothing(self):
        self.assertIsNone(mc.target_for("|deleted"))
        self.assertIsNone(mc.target_for(None))

    def test_the_key_is_a_legal_name_component(self):
        """It reaches `cmds.shadingNode(name=...)` through
        `make_material`, so a path separator there is a traceback."""
        for node in ("|root|hand_r", "|root|hand_r|Sword"):
            self.assertNotIn("|", mc.target_for(node).key)

    def test_a_selection_of_two_bones_is_one_character(self):
        found = mc.targets(["|root|hand_r", "|root"], connected=None)
        self.assertEqual(len(found), 1)

    def test_a_bone_and_a_sword_are_two_targets(self):
        found = mc.targets(["|root", "|root|hand_r|Sword"], connected=None)
        self.assertEqual(sorted(t.label for t in found), ["Sword", "root"])

    def test_a_selection_of_only_controls_falls_back_to_the_connect(self):
        found = mc.targets(["|Ctrl"], connected="|root")
        self.assertEqual([t.label for t in found], ["root"])

    def test_an_empty_selection_falls_back_to_the_connect(self):
        found = mc.targets([], connected="|root")
        self.assertEqual([t.label for t in found], ["root"])

    def test_no_selection_and_no_connect_paints_nothing(self):
        self.assertEqual(mc.targets([], connected=None), [])

    def test_the_press_paints_every_target(self):
        message = mc.paint((0.25, 0.52, 0.85),
                           selection=["|root", "|root|hand_r|Sword"],
                           undoable=False)
        self.assertEqual(sorted(self.painted), ["Sword", "root"])
        self.assertIn("blue", message)

    def test_the_press_refuses_rather_than_painting_a_guess(self):
        message = mc.paint((0.25, 0.52, 0.85), selection=[],
                           connected=None, undoable=False)
        self.assertEqual(message, mc.NOTHING_TO_PAINT)
        self.assertEqual(self.painted, {})

    def test_a_refusal_opens_no_undo_chunk(self):
        """Nothing happened, so there is nothing for a Ctrl+Z to undo --
        and an empty chunk eats the animator's previous undo step."""
        mc.paint((0.25, 0.52, 0.85), selection=[], connected=None)
        self.assertEqual(self.fake.chunks, [])

    def test_a_real_press_is_one_undo_step(self):
        mc.paint((0.25, 0.52, 0.85), selection=["|root"])
        self.assertEqual(len(self.fake.chunks), 2)
        self.assertTrue(self.fake.chunks[0].get("openChunk"))
        self.assertTrue(self.fake.chunks[-1].get("closeChunk"))

    def test_the_colour_reaches_the_shapes_unchanged(self):
        mc.paint((0.11, 0.22, 0.33), selection=["|root"], undoable=False)
        self.assertEqual(self.painted["root"][1], (0.11, 0.22, 0.33))


# ---------------------------------------------------------------------------
#  The panel: a section of the SkeldarAnim hub (2026-09-17), no window
# ---------------------------------------------------------------------------

class TestPanelBuildsIntoTheHub(unittest.TestCase):
    """The window of its own is gone (it had clipped Next free colour and
    the status on a 150 % display that same morning): `build_panel` puts
    the controls into whatever layout is current, `show_window` opens the
    hub on the Colour section."""

    def setUp(self):
        self.real = (mc.cmds, mc.scene_colours)
        self.fake = FakeUiCmds(control_height=30, dpi=1.5)
        mc.cmds = self.fake
        #  The taken line is filled on build; the scene read is the
        #  colour module's and not under test here.
        mc.scene_colours = lambda: [("red", (0.8, 0.2, 0.2))]
        self.column = mc.build_panel()

    def tearDown(self):
        mc.cmds, mc.scene_colours = self.real

    def test_no_window_is_created(self):
        self.assertEqual(self.fake.windows, {})
        self.assertFalse([c for c in self.fake.calls
                          if c[0] in ("showWindow", "windowPref")])

    def test_the_controls_land_in_one_stretching_column(self):
        self.assertTrue(self.fake.column.get("adjustableColumn"))
        self.assertGreater(len(self.fake.children), 8)

    def test_the_status_and_taken_lines_exist(self):
        self.assertIn(mc.STATUS, self.fake.children)
        self.assertIn(mc.TAKEN, self.fake.children)
        self.fake.existing.add(mc.STATUS)
        self.assertTrue(mc.is_open())

    def test_the_skin_s_marks(self):
        """2026-09-28: rounded swatches, "taken" the card's subtitle."""
        import maya_hubstyle
        maya_hubstyle.take_marks()
        mc.build_panel()
        marks = maya_hubstyle.take_marks()
        swatches = [m.colour for m in marks if m.role == "swatch"]
        self.assertEqual(swatches, [maya_hubstyle.hex_of(e.rgb)
                                    for e in colouring.PALETTE])
        by_name = dict((m.name, m.role) for m in marks)
        self.assertEqual(by_name[mc.TAKEN], "subtitle")
        self.assertEqual(by_name[mc.STATUS], "status")
        self.assertEqual(by_name[mc.CUSTOM], "swatchonly")

    def test_every_palette_colour_has_a_button(self):
        labels = [c[2].get("label") for c in self.fake.calls
                  if c[0] == "button"]
        for entry in colouring.PALETTE:
            self.assertIn(entry.name, labels)


class TestPanelCompact(unittest.TestCase):
    """The same panel for the skin and for the classic hub (2026-10-08, the
    compact hub): the eight swatches in ONE row in the skin, four a row in
    the classic hub; the status tells the hub."""

    def setUp(self):
        self.real = (mc.cmds, mc.scene_colours)
        mc.scene_colours = lambda: []

    def tearDown(self):
        mc.cmds, mc.scene_colours = self.real

    def _build(self, skin):
        import maya_hubstyle
        fake = FakeUiCmds(control_height=30)
        mc.cmds = fake
        maya_hubstyle.take_marks()
        maya_hubstyle.set_skinning(skin)
        try:
            mc.build_panel()
        finally:
            maya_hubstyle.set_skinning(False)
        return fake, maya_hubstyle.take_marks()

    def test_the_skin_has_one_row_of_eight_swatches(self):
        import maya_hubstyle
        fake, marks = self._build(True)
        rows = made(fake, "rowLayout", numberOfColumns=8)
        self.assertEqual(len(rows), 1)
        index, call = rows[0]
        cell = (mc.WIDTH - 16) // 8
        self.assertEqual(call[2]["columnWidth"],
                         [(i + 1, cell) for i in range(8)])
        buttons = [c[2] for c in inside(fake, index) if c[0] == "button"]
        self.assertEqual(len(buttons), 8)
        for button, entry in zip(buttons, colouring.PALETTE):
            self.assertEqual((button["label"], button["width"],
                              button["height"]), ("", cell - 4, 22))
            self.assertEqual(button["backgroundColor"], entry.rgb)
            self.assertIn(entry.name, button["annotation"])
        self.assertEqual([m.colour for m in marks if m.role == "swatch"],
                         [maya_hubstyle.hex_of(e.rgb)
                          for e in colouring.PALETTE])
        self.assertEqual(made(fake, "rowLayout", numberOfColumns=4), [])

    def test_the_classic_hub_keeps_four_a_row_and_the_names(self):
        fake, _marks = self._build(False)
        rows = made(fake, "rowLayout", numberOfColumns=mc.COLUMNS)
        self.assertEqual(len(rows), 2)
        cell = (mc.WIDTH - 16) // mc.COLUMNS
        names = []
        for index, call in rows:
            self.assertEqual(call[2]["columnWidth"],
                             [(i + 1, cell) for i in range(mc.COLUMNS)])
            for button in [c[2] for c in inside(fake, index)
                           if c[0] == "button"]:
                names.append(button["label"])
                self.assertEqual((button["width"], button["height"]),
                                 (cell - 4, 28))
        self.assertEqual(names, [e.name for e in colouring.PALETTE])

    def test_paint_and_next_free_are_tight_in_the_skin(self):
        fake, _marks = self._build(True)
        by = dict((c[2]["label"], c[2]) for c in fake.calls
                  if c[0] == "button" and c[2].get("label"))
        self.assertEqual((by["Paint"]["height"],
                          by["Next free"]["height"],
                          by["Next free"]["width"]), (24, 24, 84))
        self.assertNotIn("Next free colour", by)
        self.assertEqual(fake.column["rowSpacing"], 3)
        classic, _marks = self._build(False)
        by = dict((c[2]["label"], c[2]) for c in classic.calls
                  if c[0] == "button" and c[2].get("label"))
        self.assertEqual((by["Paint"]["height"],
                          by["Next free colour"]["height"],
                          by["Next free colour"]["width"]), (26, 26, 130))
        self.assertEqual(classic.column["rowSpacing"], 6)

    def test_taken_stays_a_subtitle_and_the_status_a_status(self):
        for skin in (True, False):
            _fake, marks = self._build(skin)
            by_name = dict((m.name, m.role) for m in marks)
            self.assertEqual(by_name[mc.TAKEN], "subtitle", skin)
            self.assertEqual(by_name[mc.STATUS], "status", skin)
            self.assertEqual(by_name[mc.CUSTOM], "swatchonly", skin)

    def test_the_status_tells_the_hub_and_shows_itself_in_the_viewport(self):
        import maya_hubstyle
        fake, _marks = self._build(True)
        heard = []
        listener = lambda control, text, viewport: heard.append(
            (control, text, viewport))
        maya_hubstyle.listen(listener)
        try:
            self.assertEqual(mc._status("painted Manny red"),
                             "painted Manny red")
        finally:
            maya_hubstyle.unlisten(listener)
        self.assertEqual(heard, [(mc.STATUS, "painted Manny red", True)])
        self.assertTrue([c for c in fake.calls if c[0] == "headsUpMessage"])

    def test_a_panel_that_is_not_built_tells_nothing(self):
        import maya_hubstyle
        mc.cmds = FakeUiCmds()
        heard = []
        listener = lambda control, text, viewport: heard.append(text)
        maya_hubstyle.listen(listener)
        try:
            mc._status("nobody listens")
        finally:
            maya_hubstyle.unlisten(listener)
        self.assertEqual(heard, [])


class TestShowWindowOpensTheHub(unittest.TestCase):

    def test_it_asks_the_hub_for_the_colour_section(self):
        import maya_hub
        asked = []
        saved = maya_hub.show
        maya_hub.show = lambda key=None: asked.append(key) or "hub"
        try:
            self.assertEqual(mc.show_window(), "hub")
        finally:
            maya_hub.show = saved
        self.assertEqual(asked, ["colour"])
        self.assertEqual(maya_hub.section("colour").module, "maya_colour")


if __name__ == "__main__":
    unittest.main()
