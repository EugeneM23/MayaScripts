"""The Animation Setup and Inventory cards' remaining paths (2026-10-27): which
character and weapon a press finds, what the Weapons line says for every
state of the hand, the Rig / Skeleton switch, the swap, Camera Setup, the
Inventory's tabs and the builders' failure rows - on a recording `cmds` and
on the card's helper modules rebound one attribute at a time, so no Maya
scene is touched.
"""

import contextlib
import io
import types
import unittest

import maya_hubstyle

from maya_scenesetup import armorpanel
from maya_scenesetup import catalog
from maya_scenesetup import window

SWORD = catalog.by_key("LongSword_02")
SPEAR = catalog.by_key("Spear_03")
ROOT = "|Manny_Rig:root"
HAND = ROOT + "|pelvis|hand_r"
BONE = HAND + "|weapon_r"


class Cmds(object):
    """A recording maya.cmds: optionVars, the lines written, a few nodes."""

    def __init__(self):
        self.vars = {}
        self.labels = []
        self.missing = set()
        self.nodes = {}
        self.keys = {}
        self.playback = (1.0, 24.0)
        self.layouts = set()
        self.managed = {}
        self.segments = set()
        self.selected = []
        self.menus = {}
        self.items = []
        self.buttons = {}
        self.parent = "card|column"
        self.parents = []
        self.texts = []
        self.controls = set()

    def optionVar(self, exists=None, query=None, stringValue=None, **_kw):
        if exists is not None:
            return exists in self.vars
        if query is not None:
            return self.vars.get(query)
        if stringValue is not None:
            self.vars[stringValue[0]] = stringValue[1]
        return None

    def text(self, control=None, edit=False, label=None, **kwargs):
        if edit:
            if control in self.missing:
                raise RuntimeError("Object '%s' not found." % control)
            self.labels.append((control, label))
            return control
        self.texts.append((label, kwargs))
        return control or "text%d" % len(self.texts)

    def objExists(self, node):
        return node in self.nodes

    def attributeQuery(self, attr, node=None, exists=False):
        return attr in self.nodes.get(node, {})

    def getAttr(self, plug):
        node, attr = plug.split(".", 1)
        return self.nodes[node][attr]

    def optionMenu(self, name, exists=False, query=False, value=None, edit=False, **kwargs):
        if exists:
            return name in self.menus
        if query:
            return self.menus[name]["value"]
        if edit:
            self.menus[name]["value"] = value
            return name
        self.menus[name] = dict(kwargs, value=None)
        return name

    def menuItem(self, label=None, **_kw):
        self.items.append(label)

    def button(self, name=None, exists=False, edit=False, label=None, **_kw):
        if exists:
            return name in self.buttons
        if edit:
            if self.buttons.get(name) == "broken":
                raise RuntimeError("button gone")
            self.buttons[name] = label
        return name

    def keyframe(self, node, query=False, timeChange=False):
        return self.keys.get(node)

    def playbackOptions(self, query=False, min=False, max=False):   # noqa: A002
        return self.playback[0] if min else self.playback[1]

    def columnLayout(self, name=None, exists=False, edit=False, manage=None, **_kw):
        if exists:
            return name in self.layouts
        if edit:
            self.managed[name] = manage
        return name

    def iconTextRadioButton(self, name, exists=False, edit=False, select=False, **_kw):
        if exists:
            return name in self.segments
        if edit and select:
            self.selected.append(name)
        return name

    def setParent(self, *args, **kwargs):
        if kwargs.get("query"):
            return self.parent
        self.parents.extend(args)
        return args[0] if args else None

    def control(self, name, exists=False):
        return name in self.controls

    def rowLayout(self, *args, **kwargs):
        return "row"

    def iconTextRadioCollection(self, *args, **kwargs):
        return "collection"


class Case(unittest.TestCase):
    """A Cmds in window.cmds, `swap` putting single attributes back."""

    def setUp(self):
        self.cmds = Cmds()
        self.swap(window, "cmds", self.cmds)
        self.lines = []
        self.addCleanup(maya_hubstyle.take_marks)       # the fallbacks mark their rows

    def swap(self, owner, name, value):
        old = getattr(owner, name)
        setattr(owner, name, value)
        self.addCleanup(setattr, owner, name, old)
        return old

    def capture_status(self):
        self.swap(window, "_status", lambda message, control=window._STATUS:
                  self.lines.append((message, control)))

    def quiet(self):
        """A traceback the code prints on purpose stays out of the run."""
        return contextlib.redirect_stderr(io.StringIO())


def ns(**kwargs):
    return types.SimpleNamespace(**kwargs)


# ----------------------------------------------------------------- messages

class Messages(unittest.TestCase):

    def test_a_weapon_out_in_world_names_the_bone_that_follows(self):
        self.assertEqual(window.in_world_message(SWORD, BONE),
                         "Long Sword 02 out in world - weapon_r follows it")

    def test_the_fallback_hand_segments(self):
        self.assertEqual(window.hand_segment("L"), "mayaSceneSetupHand_L")
        self.assertIn("left hand", window.hand_follows_message("L", "Long Sword 02"))

    def test_a_grip_of_a_weapon_on_the_floor(self):
        self.assertIn("lies on the floor", window.grip_note("Spear 03", "R", "floor"))
        self.assertIn("right hand", window.grip_note("Spear 03", "R", "floor"))

    def test_the_tab_and_kind_segments(self):
        self.assertEqual(window.tab_segment("armor"), "mayaSceneSetupInventoryTabs_armor")
        self.assertEqual(window.kind_segment("rig"), "mayaSceneSetupCharacterKind_rig")
        self.assertEqual(window.auto_label("rig"), "Auto [rig]")


class Status(Case):

    def test_say_weapon_writes_the_weapons_line_and_tells_the_hub(self):
        told = []
        listener = lambda control, text, viewport: told.append((control, text))   # noqa: E731
        maya_hubstyle.listen(listener)
        self.addCleanup(maya_hubstyle.unlisten, listener)
        window.say_weapon("hello")
        self.assertEqual(self.cmds.labels, [(window._STATUS, "hello")])
        self.assertIn((window._STATUS, "hello"), told)

    def test_is_open_asks_for_the_weapons_line(self):
        self.assertFalse(window.is_open())
        self.cmds.controls.add(window._STATUS)
        self.assertTrue(window.is_open())


# ------------------------------------------------------- which weapon in hand

class HeldEntry(Case):

    def test_the_marker_names_the_row_of_the_weapon_in_the_hand(self):
        self.cmds.nodes["|w|SpearMesh"] = {window.attach.MARKER: "Spear_03"}
        self.assertIs(window._held_entry("|w|SpearMesh", SWORD), SPEAR)

    def test_no_weapon_no_node_no_marker_or_a_stale_key_is_the_picked_row(self):
        self.cmds.nodes["|plain"] = {}
        self.cmds.nodes["|stale"] = {window.attach.MARKER: "Excalibur"}
        self.cmds.nodes["|empty"] = {window.attach.MARKER: None}
        for weapon in (None, "", "|gone", "|plain", "|stale", "|empty"):
            self.assertIs(window._held_entry(weapon, SWORD), SWORD, weapon)


# ------------------------------------------------------------ the character

class FakeSkeleton(object):
    def __init__(self, root=ROOT, rig=ROOT, bones=None):
        self.root, self.rig = root, rig
        self.bones = {"weapon_r": BONE, "weapon_l": ROOT + "|hand_l|weapon_l",
                      "camera_root": ROOT + "|camera_root"} if bones is None else bones

    def current_root(self):
        return self.root

    def rig_root(self):
        return self.rig

    def resolve_bone(self, root, name):
        return self.bones.get(name)


class BoundRoot(Case):

    def setUp(self):
        Case.setUp(self)
        self.skeleton = FakeSkeleton()
        self.swap(window, "skeleton", self.skeleton)

    def test_both_subtitles_name_the_rig(self):
        self.assertEqual(window._bound_root(), ROOT)
        self.assertEqual(self.cmds.labels, [(window._BOUND, "Manny_Rig:root (rig)"),
                                            (window._WEAPONS_BOUND, "Manny_Rig:root (rig)")])
        self.assertEqual(window.current_character(), ROOT)

    def test_a_bare_skeleton_is_named_a_skeleton(self):
        self.skeleton.rig = "|other:root"
        window._bound_root()
        self.assertEqual(self.cmds.labels[-1], (window._WEAPONS_BOUND, "Manny_Rig:root (skeleton)"))

    def test_no_character(self):
        self.skeleton.root = None
        self.assertIsNone(window._bound_root())
        self.assertEqual(self.cmds.labels[-1], (window._WEAPONS_BOUND, "no character"))

    def test_a_card_not_built_has_no_subtitle_to_write(self):
        self.cmds.missing = {window._BOUND, window._WEAPONS_BOUND}
        self.assertEqual(window._bound_root(), ROOT)            # nothing raised
        self.assertEqual(self.cmds.labels, [])


class Attached(Case):
    """Where the hand's weapon is: under the hand, under the drive bone (the
    legacy home), riding the OverRig link, or out in world driving the bone."""

    def setUp(self):
        Case.setUp(self)
        self.skeleton = FakeSkeleton()
        self.swap(window, "skeleton", self.skeleton)
        self.found = {}
        self.parent = {BONE: HAND}
        self.swap(window, "attach", ns(
            MARKER=window.attach.MARKER,
            parent_bone=lambda bone: self.parent.get(bone),
            find_attached=lambda node: self.found.get(node),
            model_root=lambda weapon: weapon + "|geo",
            is_animated=lambda weapon: False))
        self.legacy = None
        self.swap(window, "linking", ns(linked_weapon=lambda: self.legacy))
        self.world = {}
        self.swap(window, "bonedrive", ns(driving_weapon=lambda bone: self.world.get(bone)))
        self.followers = {}
        self.swap(window, "connections", ns(
            followers_of=lambda weapon: self.followers.get(weapon, [])))

    def test_no_character(self):
        self.skeleton.root = None
        self.assertEqual(window._attached(SWORD), (None, None, None, None, False))

    def test_a_character_without_the_bone(self):
        self.skeleton.bones = {}
        self.assertEqual(window._attached(SWORD), (ROOT, None, None, None, False))

    def test_a_weapon_in_the_hand(self):
        self.found[HAND] = "|sword"
        self.assertEqual(window._attached(SWORD, "R"), (ROOT, HAND, BONE, "|sword", False))

    def test_a_weapon_under_the_drive_bone_from_an_older_build(self):
        self.found[BONE] = "|old_sword"
        self.assertEqual(window._attached(SWORD, "R"), (ROOT, HAND, BONE, "|old_sword", False))

    def test_a_bone_with_no_parent_still_finds_the_legacy_weapon(self):
        self.parent = {}
        self.found[BONE] = "|old_sword"
        self.assertEqual(window._attached(SWORD, "R"), (ROOT, None, BONE, "|old_sword", False))

    def test_the_overrig_link_is_linked(self):
        self.legacy = "|LongSwordMesh"
        self.assertEqual(window._attached(SWORD, "R"),
                         (ROOT, HAND, BONE, "|LongSwordMesh", True))

    def test_a_weapon_out_in_world_is_linked_only_while_a_hand_rides_it(self):
        self.world[BONE] = "|floor_sword"
        self.assertEqual(window._attached(SWORD, "R")[3:], ("|floor_sword", False))
        self.followers["|floor_sword"] = ["IKArm_L"]
        self.assertEqual(window._attached(SWORD, "R")[3:], ("|floor_sword", True))

    def test_a_bare_bone(self):
        self.assertEqual(window._attached(SWORD, "R"), (ROOT, HAND, BONE, None, False))

    def test_the_picked_hand_by_default(self):
        self.cmds.vars[window._HAND_OPTIONVAR] = "L"
        left = ROOT + "|hand_l|weapon_l"
        self.parent[left] = ROOT + "|hand_l"
        self.assertEqual(window._attached(SWORD)[2], left)


class Locate(Case):

    def setUp(self):
        Case.setUp(self)
        self.capture_status()
        self.answer = (ROOT, HAND, BONE, None, False)
        self.swap(window, "_attached", lambda entry, key=None: self.answer)

    def test_no_character(self):
        self.answer = (None, None, None, None, False)
        self.assertIsNone(window._locate(SWORD, "R"))
        self.assertEqual(self.lines, [(window.NO_CHARACTER, window._STATUS)])

    def test_no_bone(self):
        self.answer = (ROOT, None, None, None, False)
        self.assertIsNone(window._locate(SWORD, "L"))
        self.assertEqual(self.lines[-1][0], "Manny_Rig:root has no bone 'weapon_l'")

    def test_no_parent(self):
        self.answer = (ROOT, None, BONE, None, False)
        self.assertIsNone(window._locate(SWORD, "R"))
        self.assertIn("'weapon_r' has no parent bone", self.lines[-1][0])

    def test_found(self):
        self.assertEqual(window._locate(SWORD, "R"), self.answer)
        self.assertEqual(self.lines, [])


class Follows(Case):

    def test_the_weapon_a_hand_rides(self):
        rig = object()
        asked = []
        self.swap(window, "maya_rigs", ns(rigs=lambda: ["rigs"],
                                          rig_of=lambda root, rigs: rig if root == ROOT else None))
        self.swap(window, "connections", ns(
            following=lambda r, key: asked.append((r, key)) or "|sword"))
        self.assertEqual(window._follows(ROOT, "L"), "|sword")
        self.assertEqual(asked, [(rig, "L")])
        self.assertIsNone(window._follows("|bare:root", "L"))
        self.assertIsNone(window._follows(None, "L"))


# -------------------------------------------------------------------- grips

class HandGrip(Case):

    def setUp(self):
        Case.setUp(self)
        self.capture_status()
        self.held = {}
        self.swap(window, "equip", ns(
            bones=lambda root, key: (HAND, BONE),
            occupant=lambda root, key: self.held.get(key, (None, None))))
        self.asked = []
        self.swap(window, "grips", ns(
            for_hand=lambda entry, key, root: self.asked.append((entry.key, key, root))
            or ((1.0, 1.0, 1.0), (2.0, 2.0, 2.0)),
            remember=lambda *a: self.asked.append(("remember",) + a)))
        self.is_held = True
        self.animated = False
        self.swap(window, "bonedrive", ns(is_held=lambda w: self.is_held,
                                          frame_of=lambda w: (0, 0, 0)))
        self.swap(window, "attach", ns(MARKER="mayaWeapon",
                                       is_animated=lambda w: self.animated))
        self.swap(window, "_held_entry", lambda weapon, entry: SPEAR)
        self.swap(window, "skeleton", FakeSkeleton())

    def test_an_animated_weapon_shows_its_remembered_grip_editable(self):
        self.held["R"] = ("|spear", "hand")
        self.animated = True
        self.assertEqual(window._hand_grip(ROOT, "R", SWORD),
                         ((1.0, 1.0, 1.0), (2.0, 2.0, 2.0), True))
        self.assertEqual(self.asked, [("Spear_03", "R", ROOT)])

    def test_a_weapon_out_in_world_shows_its_remembered_grip(self):
        self.held["R"] = ("|spear", "hand")
        self.is_held = False
        self.assertTrue(window._hand_grip(ROOT, "R", SWORD)[2])
        self.assertEqual(self.asked, [("Spear_03", "R", ROOT)])

    def test_an_edit_while_the_weapon_is_out_in_world_waits_for_the_hand(self):
        self.held["R"] = ("|spear", "hand")
        self.is_held = False
        text = window.set_hand_grip("R", (0, 0, 0), (0, 0, 0))
        self.assertEqual(text, "Spear 03 out in world - weapon_r follows it"
                               " - the grip applies in the hand")
        self.assertEqual(self.lines[-1][0], text)
        self.assertIn(("remember", "Spear_03", "R", (0, 0, 0), (0, 0, 0)), self.asked)


# ------------------------------------------------------------ the inventory

class Inventory(Case):

    def test_no_inventory_module_is_none(self):
        import maya_inventory

        def boom(name):
            raise RuntimeError("no Qt")
        self.swap(maya_inventory, "live", boom)
        self.assertIsNone(window._inventory())
        window._refresh_inventory()                          # nothing to refresh

    def test_the_live_panel_is_the_cards(self):
        import maya_inventory
        panel = object()
        self.swap(maya_inventory, "live", lambda name: panel if name == window._INVENTORY else None)
        self.assertIs(window._inventory(), panel)


class Refresh(Case):
    """The Weapons line says the picked hand's state - only on the Weapon tab."""

    def setUp(self):
        Case.setUp(self)
        self.capture_status()
        self.cmds.vars[window._WEAPON_OPTIONVAR] = "LongSword_02"
        self.answer = (ROOT, HAND, BONE, None, False)
        self.swap(window, "_attached", lambda entry, key=None: self.answer)
        self.refreshed = []
        self.swap(window, "_inventory", lambda: ns(refresh=lambda: self.refreshed.append(1)))
        self.swap(window, "_held_entry", lambda weapon, entry: SPEAR)
        self.held = True
        self.swap(window, "bonedrive", ns(is_held=lambda w: self.held))

    def said(self):
        window.refresh()
        return self.lines[-1][0] if self.lines else None

    def test_the_inventory_is_refreshed_and_the_armor_tab_keeps_its_line(self):
        self.cmds.vars[window._TAB_OPTIONVAR] = "armor"
        self.assertIsNone(self.said())
        self.assertEqual(self.refreshed, [1])

    def test_a_weapon_the_hands_ride(self):
        self.answer = (ROOT, HAND, BONE, "|spear", True)
        self.assertEqual(self.said(), "Spear 03 drives the arms")

    def test_a_held_weapon(self):
        self.answer = (ROOT, HAND, BONE, "|spear", False)
        self.assertEqual(self.said(), "Spear 03 on hand_r")

    def test_a_held_weapon_with_no_hand_names_the_bone(self):
        self.answer = (ROOT, None, BONE, "|spear", False)
        self.assertEqual(self.said(), "Spear 03 on weapon_r")

    def test_a_weapon_out_in_world(self):
        self.answer = (ROOT, HAND, BONE, "|spear", False)
        self.held = False
        self.assertEqual(self.said(), "Spear 03 out in world - weapon_r follows it")

    def test_no_character_no_bone_no_hand(self):
        self.answer = (None, None, None, None, False)
        self.assertEqual(self.said(), window.NO_CHARACTER)
        self.answer = (ROOT, None, None, None, False)
        self.assertEqual(self.said(), "Manny_Rig:root has no bone 'weapon_r'")
        self.answer = (ROOT, None, BONE, None, False)
        self.assertIn("has no parent bone", self.said())

    def test_a_free_hand_says_what_equip_will_do(self):
        self.assertEqual(self.said(), window.pick_text("Long Sword 02", "R"))

    def test_with_no_inventory_the_line_still_follows(self):
        window._inventory = lambda: None
        self.assertEqual(self.said(), window.pick_text("Long Sword 02", "R"))


# --------------------------------------------------------- the character card

class Choice(Case):

    def test_the_auto_card_has_its_own_absent_text(self):
        self.swap(window, "current_choice", lambda: ("Auto", "rig"))
        self.assertEqual(window._absent_choice(), window.charlook.AUTO_ADD)
        window.current_choice = lambda: ("Orc_D", "skeleton")
        self.assertIn("Orc D has no skeleton", window._absent_choice())

    def test_the_add_button_follows_the_choice(self):
        self.cmds.buttons[window._ADD] = "old"
        self.swap(window, "current_choice", lambda: ("Creep", "skeleton"))
        from maya_uebridge import window as bridge
        painted = []
        self.swap(bridge, "paint_import", lambda: painted.append(1))
        window._paint_labels()
        self.assertEqual(self.cmds.buttons[window._ADD], window.add_label())
        self.assertIn("Creep", self.cmds.buttons[window._ADD])
        self.assertEqual(painted, [1])

    def test_a_button_or_a_bridge_that_raises_is_left(self):
        self.cmds.buttons[window._ADD] = "broken"
        from maya_uebridge import window as bridge

        def boom():
            raise RuntimeError("no bridge")
        self.swap(bridge, "paint_import", boom)
        window._paint_labels()                               # nothing raised

    def test_no_add_button_yet_is_left(self):
        from maya_uebridge import window as bridge
        self.swap(bridge, "paint_import", lambda: None)
        window._paint_labels()
        self.assertEqual(self.cmds.buttons, {})


class Grid(Case):

    def test_the_live_grid_or_none(self):
        import maya_chargrid
        grid = object()
        self.swap(maya_chargrid, "live", lambda name: grid if name == window._PORTRAITS else None)
        self.assertIs(window._grid(), grid)

        def boom(name):
            raise RuntimeError("no Qt")
        maya_chargrid.live = boom
        self.assertIsNone(window._grid())

    def test_attach_grid_says_whether_the_grid_stands(self):
        import maya_chargrid
        asked = []
        self.swap(maya_chargrid, "attach", lambda name, kind=None, selected=None: (
            asked.append((name, kind, selected)) or object()))
        self.assertTrue(window._attach_grid("Creep", "skeleton"))
        self.assertEqual(asked, [(window._PORTRAITS, "skeleton", "Creep")])
        maya_chargrid.attach = lambda name, kind=None, selected=None: None
        self.assertFalse(window._attach_grid("Creep", "skeleton"))

        def boom(*a, **k):
            raise RuntimeError("no Qt")
        maya_chargrid.attach = boom
        with self.quiet():
            self.assertFalse(window._attach_grid("Creep", "skeleton"))


class KindChanged(Case):

    def setUp(self):
        Case.setUp(self)
        self.said = []
        self.swap(window, "_say_choice", lambda: self.said.append(1))

    def test_a_segment_remembers_the_kind_and_dims_the_grid(self):
        kinds = []
        self.swap(window, "_grid", lambda: ns(set_kind=kinds.append))
        window.kind_changed("skeleton")()
        self.assertEqual(self.cmds.vars[window._KIND_OPTIONVAR], "skeleton")
        self.assertEqual(kinds, ["skeleton"])
        self.assertEqual(self.said, [1])

    def test_without_a_grid_it_still_remembers(self):
        self.swap(window, "_grid", lambda: None)
        window.kind_changed("rig")("ignored", "args")
        self.assertEqual(self.cmds.vars[window._KIND_OPTIONVAR], "rig")


class CharacterChanged(Case):

    def test_the_auto_row_says_what_an_import_does(self):
        self.cmds.menus[window._CHARACTER] = {"value": "Auto [skeleton]"}
        self.swap(window, "_paint_labels", lambda: None)
        window.character_changed()
        self.assertEqual(self.cmds.vars[window._CHARACTER_OPTIONVAR], "Auto [skeleton]")
        self.assertEqual(self.cmds.labels[-1],
                         (window._CHARACTER_STATUS, window.charlook.auto_text("skeleton")))


class Presses(Case):
    """Delete, a drop, a swap, an Open scene: the press's own line comes last,
    even when the refresh after it raises."""

    def setUp(self):
        Case.setUp(self)
        self.capture_status()

        def boom():
            raise RuntimeError("refresh broke")
        self.swap(window, "refresh", boom)

    def last(self):
        return self.lines[-1]

    def test_delete_says_its_line_and_plays_only_for_a_deletion(self):
        from maya_scenesetup import deletion
        import maya_hubsound
        played = []
        self.swap(maya_hubsound, "deleted", lambda: played.append(1))
        self.swap(deletion, "delete_selected", lambda confirm=None: "Nothing selected")
        with self.quiet():
            self.assertEqual(window.delete_characters(), "Nothing selected")
        self.assertEqual(played, [])
        self.assertEqual(self.last(), ("Nothing selected", window._CHARACTER_STATUS))
        deletion.delete_selected = lambda confirm=None: "Deleted Manny_Rig"
        with self.quiet():
            window.delete_characters()
        self.assertEqual(played, [1])

    def test_a_drop_says_its_line(self):
        self.swap(window.character, "add_character", lambda entry, at=None: "added")
        with self.quiet():
            self.assertEqual(window.place_character("Manny", "rig", (0, 0, 0)), "added")
        self.assertEqual(self.last(), ("added", window._CHARACTER_STATUS))

    def test_open_scene_says_its_line(self):
        from maya_scenesetup import opener
        self.swap(opener, "open_asset", lambda path, label: "opened " + label)
        with self.quiet():
            self.assertEqual(window.open_character_scene("Creep", "rig"), "opened Creep [rig]")
            self.assertEqual(window.open_weapon_scene("Spear_03"), "opened Spear 03")
        self.assertEqual(self.last(), ("opened Spear 03", window._STATUS))

    def test_an_unknown_model_is_named_as_it_was_given(self):
        self.assertIn("Sevarog", window.open_character_scene("Sevarog", "rig"))
        self.assertIn("Sevarog", window.place_character("Sevarog", "rig", (0, 0, 0)))


class Swap(Case):
    """2026-10-17: a portrait dropped on a character swaps it."""

    def setUp(self):
        Case.setUp(self)
        self.capture_status()
        from maya_scenesetup import swap
        self.swapped = []
        self.swap(swap, "swap", lambda entry, root: self.swapped.append((entry.key, root))
                  or "swapped")
        self.refreshed = []
        self.swap(window, "refresh", lambda: self.refreshed.append(1))

    def test_the_portraits_character_takes_the_ones_place(self):
        self.assertEqual(window.swap_character("Creep", "rig", ROOT), "swapped")
        self.assertEqual(self.swapped, [("Creep_Rig", ROOT)])
        self.assertEqual(self.refreshed, [1])
        self.assertEqual(self.lines[-1], ("swapped", window._CHARACTER_STATUS))

    def test_the_auto_card_swaps_nothing(self):
        self.assertEqual(window.swap_character("Auto", "rig", ROOT), window.charlook.AUTO_ADD)
        self.assertEqual(self.swapped, [])

    def test_an_absent_pair_swaps_nothing(self):
        text = window.swap_character("Orc_D", "skeleton", ROOT)
        self.assertIn("Orc D has no skeleton", text)
        self.assertIn("Sevarog", window.swap_character("Sevarog", "rig", ROOT))
        self.assertEqual(self.swapped, [])
        self.assertEqual(self.refreshed, [])

    def test_a_refresh_that_raises_still_says_the_swap(self):
        def boom():
            raise RuntimeError("refresh broke")
        window.refresh = boom
        with self.quiet():
            self.assertEqual(window.swap_character("Manny", "rig", ROOT), "swapped")
        self.assertEqual(self.lines[-1], ("swapped", window._CHARACTER_STATUS))


class Camera(Case):

    def setUp(self):
        Case.setUp(self)
        self.capture_status()
        self.skeleton = FakeSkeleton()
        self.swap(window, "skeleton", self.skeleton)
        self.swap(window, "_bound_root", lambda: self.skeleton.root)
        self.standing = None
        self.calls = []
        self.swap(window, "camera", ns(
            BONE="camera_root",
            camera_for=lambda bone: self.standing,
            teardown=lambda bone, start, end: self.calls.append(("teardown", bone, start, end)),
            setup=lambda bone, start, end: self.calls.append(("setup", bone, start, end))
            or "camera set up",
            leaf=window.camera.leaf))

    def test_the_span_covers_the_playback_and_the_bones_keys(self):
        self.cmds.keys["b"] = [-3.0, 10.0, 40.0]
        self.assertEqual(window.camera_span("b"), (-3.0, 40.0))
        self.assertEqual(window.camera_span("unkeyed"), (1.0, 24.0))

    def test_a_first_press_sets_the_camera_up(self):
        window.camera_setup()
        self.assertEqual(self.calls, [("setup", ROOT + "|camera_root", 1.0, 24.0)])
        self.assertEqual(self.lines[-1], ("camera set up", window._CHARACTER_STATUS))

    def test_a_second_press_bakes_the_bone_back(self):
        self.standing = "|SceneSetup_camera"
        window.camera_setup()
        self.assertEqual(self.calls, [("teardown", ROOT + "|camera_root", 1.0, 24.0)])
        self.assertEqual(self.lines[-1][0], "camera removed - camera_root baked back and free")

    def test_no_character_or_no_camera_bone(self):
        self.skeleton.root = None
        window.camera_setup()
        self.assertEqual(self.lines[-1], (window.NO_CHARACTER, window._CHARACTER_STATUS))
        self.skeleton.root = ROOT
        self.skeleton.bones = {}
        window.camera_setup()
        self.assertEqual(self.lines[-1][0], "Manny_Rig:root has no bone 'camera_root'")
        self.assertEqual(self.calls, [])


class AimRefusal(Case):

    def test_a_weapon_with_an_aim_is_neither_replaced_nor_removed(self):
        self.capture_status()
        self.swap(window, "_locate", lambda entry, key=None: (ROOT, HAND, BONE, "|sword", False))
        self.swap(window, "linking", ns(linked_weapon=lambda: None))
        self.swap(window, "attach", ns(model_root=lambda weapon: weapon + "|geo"))
        aimed = []
        self.swap(window, "aimrig", ns(aim_for=lambda node: aimed.append(node) or "aim1"))
        calls = []
        self.swap(window, "equip", ns(to_hand=lambda *a: calls.append(a),
                                      take_off=lambda *a: calls.append(a)))
        window.add_weapon()
        window.remove_weapon()
        self.assertEqual(calls, [])
        self.assertEqual(aimed, ["|sword|geo", "|sword|geo"])
        self.assertEqual([line for line, _c in self.lines],
                         [window.AIMED_NO_ADD, window.AIMED_NO_ADD])


# -------------------------------------------------------------------- tabs

class Tabs(Case):

    def setUp(self):
        Case.setUp(self)
        self.refreshed = []
        self.swap(window, "refresh", lambda: self.refreshed.append(1))
        self.armor = []
        self.swap(armorpanel, "show", lambda: self.armor.append(1))
        self.fitted = []
        self.panel = ns(_host="host", fit=self.fitted.append)
        self.swap(window, "_inventory", lambda: self.panel)

    def test_an_unknown_tab_does_nothing(self):
        window.show_tab("colour")
        self.assertNotIn(window._TAB_OPTIONVAR, self.cmds.vars)

    def test_before_the_card_is_built_it_only_remembers(self):
        window.show_tab("armor")
        self.assertEqual(self.cmds.vars[window._TAB_OPTIONVAR], "armor")
        self.assertEqual((self.cmds.managed, self.armor, self.refreshed), ({}, [], []))

    def test_the_weapon_tab_shows_its_column_lights_its_segment_and_fits_the_panel(self):
        self.cmds.layouts.update(window._TAB_COLUMN.values())
        self.cmds.segments.add(window.tab_segment("weapon"))
        window.show_tab("weapon")
        self.assertEqual(self.cmds.managed, {window._TAB_COLUMN["weapon"]: True,
                                             window._TAB_COLUMN["armor"]: False})
        self.assertEqual(self.cmds.selected, [window.tab_segment("weapon")])
        self.assertEqual(self.fitted, ["host"])
        self.assertEqual(self.refreshed, [1])

    def test_a_panel_with_no_host_or_no_panel_is_not_fitted(self):
        self.cmds.layouts.update(window._TAB_COLUMN.values())
        self.panel = ns(fit=self.fitted.append)
        window.show_tab("weapon")
        window._inventory = lambda: None
        window.show_tab("weapon")
        self.assertEqual(self.fitted, [])
        self.assertEqual(self.refreshed, [1, 1])
        self.assertEqual(self.cmds.selected, [])        # no segment built

    def test_the_armor_tab_is_the_armor_panels(self):
        self.cmds.layouts.update(window._TAB_COLUMN.values())
        window.show_tab("armor")
        self.assertEqual(self.cmds.managed[window._TAB_COLUMN["armor"]], True)
        self.assertEqual(self.armor, [1])
        self.assertEqual(self.refreshed, [])

    def test_a_tab_shown_while_another_is_being_shown_is_ignored(self):
        self.cmds.layouts.update(window._TAB_COLUMN.values())
        inner = []

        def refresh():
            window.show_tab("armor")                     # a segment's onCommand mid-show
            inner.append(self.cmds.vars[window._TAB_OPTIONVAR])
        window.refresh = refresh
        window.show_tab("weapon")
        self.assertEqual(inner, ["weapon"])
        self.assertEqual(self.armor, [])

    def test_a_failing_show_leaves_the_tabs_free(self):
        self.cmds.layouts.update(window._TAB_COLUMN.values())

        def boom():
            raise RuntimeError("refresh broke")
        window.refresh = boom
        with self.assertRaises(RuntimeError):
            window.show_tab("weapon")
        self.assertEqual(window._TAB_BUSY, [False])
        window.show_tab("armor")
        self.assertEqual(self.armor, [1])

    def test_a_segment_shows_its_tab(self):
        window.tab_changed("armor")()
        self.assertEqual(self.cmds.vars[window._TAB_OPTIONVAR], "armor")


# ----------------------------------------------------------- the builders

class Fallbacks(Case):
    """Without Qt the cards show dropdowns; a section that fails to build is
    a line of text and the rest of the card still builds."""

    def test_the_character_dropdown_opens_on_the_remembered_row(self):
        label = catalog.character_by_key("Creep").label
        self.cmds.vars[window._CHARACTER_OPTIONVAR] = label
        window._character_dropdown()
        self.assertEqual(self.cmds.menus[window._CHARACTER]["value"], label)
        self.assertEqual(self.cmds.items[-2:], ["Auto [rig]", "Auto [skeleton]"])
        changed = []
        self.swap(window, "character_changed", lambda: changed.append(1))
        self.cmds.menus[window._CHARACTER]["changeCommand"]("whatever")
        self.assertEqual(changed, [1])

    def test_a_label_the_table_no_longer_carries_is_not_selected(self):
        self.cmds.vars[window._CHARACTER_OPTIONVAR] = "Sevarog [rig]"
        window._character_dropdown()
        self.assertIsNone(self.cmds.menus[window._CHARACTER]["value"])

    def test_the_weapon_dropdown_picks_the_weapon_it_names(self):
        picked = []
        self.swap(window, "select_weapon", picked.append)
        window._weapon_fallback()
        menu = self.cmds.menus[window._WEAPON_MENU]
        self.assertEqual(menu["value"], catalog.WEAPONS[0].label)
        menu["value"] = SPEAR.label
        menu["changeCommand"]()
        self.assertEqual(picked, ["Spear_03"])
        menu["value"] = "Excalibur"
        window.weapon_menu_changed()
        self.assertEqual(picked, ["Spear_03"])

    def test_the_bridge_rows_failing_leave_a_line(self):
        from maya_uebridge import window as bridge

        def boom():
            raise RuntimeError("no editor")
        self.swap(bridge, "build_rows", boom)
        with self.quiet():
            window._bridge_rows()
        self.assertEqual(self.cmds.parents, ["card|column"])
        self.assertEqual(self.cmds.texts[-1][0], "UE Bridge failed: RuntimeError: no editor")
        self.cmds.parent = None
        with self.quiet():
            window._bridge_rows()
        self.assertEqual(self.cmds.parents, ["card|column"])

    def test_the_armor_rows_failing_leave_a_line(self):
        def boom():
            raise ValueError("no tiles")
        self.swap(armorpanel, "build_rows", boom)
        with self.quiet():
            window._armor_rows()
        self.assertEqual(self.cmds.parents, ["card|column"])
        self.assertEqual(self.cmds.texts[-1][0], "Armor failed: ValueError: no tiles")
        self.cmds.parent = None
        with self.quiet():
            window._armor_rows()
        self.assertEqual(self.cmds.parents, ["card|column"])

    def test_the_armor_watch_failing_is_left(self):
        def boom():
            raise RuntimeError("no line")
        self.swap(armorpanel, "watch", boom)
        with self.quiet():
            window._watch_armor()                            # nothing raised

    def test_attach_inventory_says_whether_it_stands(self):
        import maya_inventory
        self.swap(maya_inventory, "attach", lambda name: object())
        self.assertTrue(window._attach_inventory())
        maya_inventory.attach = lambda name: None
        self.assertFalse(window._attach_inventory())

        def boom(name):
            raise RuntimeError("no Qt")
        maya_inventory.attach = boom
        with self.quiet():
            self.assertFalse(window._attach_inventory())


class Run(Case):
    """Every callback goes through `_run`: a failure lands on its line."""

    def test_a_failure_is_written_on_the_line_and_raised(self):
        self.capture_status()

        def boom():
            raise ValueError("bad press")
        with self.assertRaises(ValueError):
            window._run(boom, window._CHARACTER_STATUS)
        self.assertEqual(self.lines, [("ValueError: bad press", window._CHARACTER_STATUS)])

    def test_the_tab_rows_equip_and_unequip_act_on_the_tab_shown(self):
        calls = []
        self.swap(window, "add_weapon", lambda: calls.append("add_weapon"))
        self.swap(window, "remove_weapon", lambda: calls.append("remove_weapon"))
        self.swap(armorpanel, "equip_armor", lambda: calls.append("equip_armor"))
        self.swap(armorpanel, "unequip_armor", lambda: calls.append("unequip_armor"))
        window.equip_current()
        window.unequip_current()
        self.cmds.vars[window._TAB_OPTIONVAR] = "armor"
        window.equip_current()
        window.unequip_current()
        self.assertEqual(calls, ["add_weapon", "remove_weapon", "equip_armor",
                                 "unequip_armor"])

    def test_a_hand_segment_picks_its_hand(self):
        picked = []
        self.swap(window, "select_hand", picked.append)
        window.hand_changed("L")("args")
        self.assertEqual(picked, ["L"])

    def test_the_cards_open_the_hub_on_their_sections(self):
        import maya_hub
        asked = []
        self.swap(maya_hub, "show", lambda key=None: asked.append(key) or "hub")
        tabs = []
        self.swap(window, "show_tab", tabs.append)
        self.assertEqual(window.show_window(), "hub")
        self.assertEqual(window.show_weapons(), "hub")
        self.assertEqual(asked, [window.HUB_SECTION, window.HUB_WEAPONS])
        self.assertEqual(tabs, ["weapon"])


class Builders(unittest.TestCase):
    """The two cards built on the recording `cmds` of the hub's tests: their
    buttons press what they say, and a card remembered on Armor opens there."""

    def setUp(self):
        from tests.uifakes import FakeUiCmds
        self.fake = FakeUiCmds()
        self.calls = []
        names = {"cmds": self.fake,
                 "_attach_grid": lambda model, kind: True,
                 "_attach_inventory": lambda: True,
                 "_bridge_rows": lambda: None,
                 "_armor_rows": lambda: None,
                 "_watch_armor": lambda: None,
                 "_bound_root": lambda: None,
                 "_say_choice": lambda: None,
                 "refresh": lambda: None,
                 "show_tab": lambda tab: self.calls.append(("show_tab", tab)),
                 "add_character": lambda: self.calls.append("add"),
                 "camera_setup": lambda: self.calls.append("camera"),
                 "delete_characters": lambda: self.calls.append("delete"),
                 "equip_current": lambda: self.calls.append("equip"),
                 "unequip_current": lambda: self.calls.append("unequip")}
        for name, value in names.items():
            self.addCleanup(setattr, window, name, getattr(window, name))
            setattr(window, name, value)
        maya_hubstyle.take_marks()
        self.addCleanup(maya_hubstyle.take_marks)

    def buttons(self):
        return dict((c[2].get("label"), c[2].get("command")) for c in self.fake.calls
                    if c[0] == "button" and c[2].get("command"))

    def test_the_character_cards_buttons_press_their_callbacks(self):
        window.build_characters_panel()
        found = self.buttons()
        found[window.add_label()]()
        found["Camera"]()
        found["Delete"]()
        self.assertEqual(self.calls, ["add", "camera", "delete"])

    def test_the_inventory_cards_buttons_and_its_remembered_armor_tab(self):
        self.fake.optionvars[window._TAB_OPTIONVAR] = "armor"
        window.build_weapons_panel()
        self.assertEqual(self.calls, [("show_tab", "armor")])
        for command in self.buttons().values():
            command()
        self.assertEqual(sorted(self.calls[1:]), ["equip", "unequip"])

    def test_on_the_weapon_tab_it_opens_on_it_without_a_show(self):
        window.build_weapons_panel()
        self.assertEqual(self.calls, [])

    def test_without_qt_the_cards_build_their_dropdowns(self):
        made = []
        self.addCleanup(setattr, window, "_character_dropdown", window._character_dropdown)
        self.addCleanup(setattr, window, "_weapon_fallback", window._weapon_fallback)
        window._character_dropdown = lambda: made.append("characters")
        window._weapon_fallback = lambda: made.append("weapons")
        window._attach_grid = lambda model, kind: False
        window._attach_inventory = lambda: False
        window.build_characters_panel()
        window.build_weapons_panel()
        self.assertEqual(made, ["characters", "weapons"])


if __name__ == "__main__":
    unittest.main()
