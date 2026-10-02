"""Tests for the window's policy: optionVars, and what the status line says.

The widgets themselves are proved live -- a `cmds` window cannot be built
without Maya. What is testable is everything the callbacks decide before they
touch a widget.
"""

import sys
import types
import unittest


def _install_fake_maya():
    """Let window import without Maya. See CLAUDE.md on rebinding.

    Real modules win when they are importable -- under mayapy they always are,
    and window reaches camera and aim, which need maya.api.OpenMaya. Guarding on
    `"maya.cmds" in sys.modules` instead is not enough: run on its own, this
    module then installed a fake `maya` that is not a package and shadowed the
    real one, so the file only imported as part of the full discover run.
    """
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
    maya.cmds = cmds
    maya.mel = mel
    maya.api = api
    api.OpenMaya = openmaya
    sys.modules.setdefault("maya", maya)
    sys.modules["maya.api"] = api
    sys.modules["maya.api.OpenMaya"] = openmaya
    sys.modules["maya.cmds"] = cmds
    sys.modules["maya.mel"] = mel


_install_fake_maya()

from maya_scenesetup import catalog  # noqa: E402
from maya_scenesetup import window  # noqa: E402

SWORD = catalog.by_key("LongSword_02")


class AimRefusals(unittest.TestCase):
    """Add deletes the weapon whole, and the aim's locators drive the geometry
    inside it. Without this refusal the press leaves two locators pointing at a
    deleted node -- the same reasoning that already makes Add refuse while the
    hands are connected."""

    def test_add_has_a_refusal_naming_the_cure(self):
        self.assertIn("Bake+Delete", window.AIMED_NO_ADD)

    def test_the_two_add_refusals_are_different(self):
        self.assertNotEqual(window.AIMED_NO_ADD, window.LINKED_NO_ADD)

    def test_the_overrig_era_callbacks_are_gone(self):
        """Connect Arms, Disconnect Arms and Add Aim left the panel on
        2026-09-07. Gone, not disabled: a hotkey row pressing a callback that
        is not there fails at the worst moment, so the rows went the same
        day. Camera Setup came BACK on 2026-09-18 as the retarget's own
        camera step by hand, on camera_root."""
        for name in ("connect_arms", "disconnect_arms", "add_aim",
                     "recolour_character", "recolour_weapon"):
            self.assertFalse(hasattr(window, name), name)
        for name in ("add_character", "add_weapon", "remove_weapon",
                     "camera_setup", "place_character", "select_model",
                     "select_weapon", "select_hand", "set_hand_grip",
                     "hand_grips"):
            self.assertTrue(callable(getattr(window, name)), name)


class OptionVars(unittest.TestCase):

    def test_each_weapon_remembers_its_own_grip(self):
        self.assertNotEqual(window.optionvar_name("LongSword_02"),
                            window.optionvar_name("Shield_01"))

    def test_the_name_carries_the_key(self):
        self.assertIn("LongSword_02", window.optionvar_name("LongSword_02"))

    def test_packs_rotate_then_translate(self):
        self.assertEqual(
            window.pack_offsets((10.0, 20.0, 30.0), (1.0, 2.0, 3.0)),
            [10.0, 20.0, 30.0, 1.0, 2.0, 3.0])

    def test_unpacks_what_it_packed(self):
        packed = window.pack_offsets((10.0, 20.0, 30.0), (1.0, 2.0, 3.0))
        self.assertEqual(window.unpack_offsets(packed),
                         ((10.0, 20.0, 30.0), (1.0, 2.0, 3.0)))

    def test_an_unset_optionvar_reads_as_zeros(self):
        """Maya answers a missing optionVar with 0 or an empty list."""
        self.assertEqual(window.unpack_offsets(None),
                         ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0)))
        self.assertEqual(window.unpack_offsets([]),
                         ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0)))

    def test_a_short_optionvar_reads_as_zeros(self):
        """Rather than half a grip from an older version of this tool."""
        self.assertEqual(window.unpack_offsets([1.0, 2.0]),
                         ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0)))

    def test_reads_integers_maya_stored_as_ints(self):
        self.assertEqual(window.unpack_offsets([0, 90, 0, 0, 0, 0]),
                         ((0.0, 90.0, 0.0), (0.0, 0.0, 0.0)))


class GripSpace(unittest.TestCase):
    """The offsets are BONE-relative (2026-08-25, the user's ruling: «наше
    оружие подставляется в позицию вепон боны с указанными офсетами»).

    Zeros mean exactly on weapon_r. That is the pre-2026-08-21 meaning, so
    the pre-redesign optionVars read back verbatim and the four days of
    under-hand policy - grip_values, the composition, the separate
    grip-optionVar name - are gone rather than disabled. The under-hand
    numbers saved into `mayaSceneSetup_grip_*` during those days mean
    nothing in the bone space and are deliberately never read.
    """

    def test_the_under_hand_policy_is_gone(self):
        self.assertFalse(hasattr(window, "grip_values"))
        self.assertFalse(hasattr(window, "grip_optionvar_name"))

    def test_the_save_name_is_the_bone_relative_one(self):
        self.assertEqual(window.optionvar_name("LongSword_02"),
                         "mayaSceneSetup_offset_LongSword_02")


class RemoveWeapon(unittest.TestCase):
    """The button the inverted drive forces: deleting the sword by hand
    would lose the bone's animation and orphan the constraint (trap 4)."""

    def test_there_is_a_remove_callback(self):
        self.assertTrue(callable(window.remove_weapon))

    def test_remove_is_refused_while_linked(self):
        self.assertIn("disconnect", window.LINKED_NO_REMOVE.lower())

    def test_a_parentless_bone_is_named(self):
        message = window.missing_parent_message("weapon_r")
        self.assertIn("weapon_r", message)
        self.assertIn("parent", message.lower())


class Messages(unittest.TestCase):

    def test_no_character_names_the_new_rule_and_not_the_picker(self):
        """Since 2026-09-07 the character comes from the selection (a rig
        control or a joint), then the rig; the picker is off the shelf."""
        self.assertIn("select", window.NO_CHARACTER)
        self.assertIn("control", window.NO_CHARACTER)
        self.assertNotIn("picker", window.NO_CHARACTER.lower())

    def test_bound_says_rig_or_skeleton(self):
        """No "Character:" prefix since 2026-09-28: in the skin the line is
        the subtitle of the card called Characters."""
        self.assertEqual(window.bound_message("|root", rig=True),
                         "root (rig)")
        self.assertEqual(window.bound_message("|clip:root", rig=False),
                         "clip:root (skeleton)")
        self.assertEqual(window.bound_message("|SKM_Manny|root"),
                         "root (skeleton)")

    def test_missing_bone_names_the_bone_and_the_character(self):
        message = window.missing_bone_message("|SKM_Manny|root", "weapon_r")
        self.assertIn("weapon_r", message)
        self.assertIn("root", message)
        self.assertNotIn("|", message)

    def test_missing_file_names_the_path(self):
        self.assertIn("C:/x/y.fbx", window.missing_file_message("C:/x/y.fbx"))

    def test_bound_names_the_character(self):
        self.assertIn("root", window.bound_message("|SKM_Manny|root"))

    def test_bound_says_so_when_nothing_is_bound(self):
        self.assertIn("no", window.bound_message(None).lower())


class LinkedMessages(unittest.TestCase):
    """What the window says once the hands ride the weapon."""

    def test_add_is_refused_with_a_reason(self):
        """Replacing would delete the weapon, and the IK controls are its
        children -- the press would take both arm rigs down unbaked."""
        self.assertIn("disconnect", window.LINKED_NO_ADD.lower())

    def test_offsets_say_the_weapon_is_animated(self):
        self.assertIn("animated", window.LINKED_NO_OFFSETS.lower())

    def test_disconnect_says_when_there_is_no_link(self):
        self.assertIn("not connected", window.NOT_CONNECTED.lower())

    def test_connect_needs_a_weapon_first(self):
        self.assertIn("add", window.NO_WEAPON.lower())

    def test_linked_status_names_the_weapon(self):
        message = window.linked_message(SWORD)
        self.assertIn(SWORD.label, message)
        self.assertIn("arms", message.lower())


class FakeUiCmds(object):
    """Enough of maya.cmds to answer for one optionMenu and one optionVar."""

    def __init__(self, menu_value=None, stored=None, menu_exists=True):
        self.menu_value = menu_value
        self.stored = dict(stored or {})
        self.menu_exists = menu_exists
        self.status = []

    def optionMenu(self, name, exists=False, query=False, value=None,
                   edit=False, **kwargs):
        if exists:
            return self.menu_exists
        if edit and value is not None:
            self.menu_value = value
            return name
        return self.menu_value

    def optionVar(self, exists=None, query=None, stringValue=None, **kwargs):
        if exists is not None:
            return exists in self.stored
        if query is not None:
            return self.stored.get(query)
        if stringValue is not None:
            self.stored[stringValue[0]] = stringValue[1]
        return None

    def text(self, *args, **kwargs):
        if kwargs.get("label") is not None:
            self.status.append(kwargs["label"])
        return args[0] if args else ""


class CharacterDropdown(unittest.TestCase):
    """Which skeleton Add Character imports (2026-09-01).

    The default matters most: anyone who never opens the list must get
    exactly the behaviour they had before the dropdown existed.
    """

    def setUp(self):
        self.real = window.cmds
        self.fake = FakeUiCmds()
        window.cmds = self.fake

    def tearDown(self):
        window.cmds = self.real

    def _labels(self):
        return window.catalog.character_labels()

    def test_the_dropdown_names_the_catalog_in_table_order(self):
        """The rig is row 0 since 2026-09-07 -- the row the menu opens on
        and the fallback for a label the table no longer carries. The
        SKELETON stays `default_character()`, which is a different
        question (`character_path()` with no argument)."""
        self.assertEqual(self._labels()[0],
                         window.catalog.default_rig().label)
        self.assertEqual(self._labels(),
                         window.catalog.character_labels())

    def test_a_chosen_label_resolves_to_its_entry(self):
        wanted = window.catalog.character_by_key("UE4_Mannequin")
        self.fake.menu_value = wanted.label
        self.assertIs(window.chosen_character(), wanted)

    def test_no_menu_yet_falls_back_to_the_default(self):
        """The window builds its controls in order; nothing may raise
        because it asked before the menu existed."""
        self.fake.menu_exists = False
        self.assertIs(window.chosen_character(),
                      window.catalog.default_rig())

    def test_an_unknown_label_falls_back_rather_than_raising(self):
        """A scene file outlives a rename of a table row."""
        self.fake.menu_value = "Sevarog"
        self.assertIs(window.chosen_character(),
                      window.catalog.default_rig())

    def test_an_empty_menu_value_falls_back(self):
        self.fake.menu_value = ""
        self.assertIs(window.chosen_character(),
                      window.catalog.default_rig())

    def test_changing_the_choice_remembers_it(self):
        wanted = window.catalog.character_by_key("UE4_Mannequin")
        self.fake.menu_value = wanted.label
        window.character_changed()
        self.assertEqual(self.fake.stored.get(window._CHARACTER_OPTIONVAR),
                         wanted.label)

    def test_changing_the_choice_says_what_will_be_imported(self):
        wanted = window.catalog.character_by_key("UE4_Mannequin")
        self.fake.menu_value = wanted.label
        window.character_changed()
        self.assertTrue(any(wanted.label in line
                            for line in self.fake.status), self.fake.status)

    def test_nothing_remembered_reads_as_empty(self):
        self.assertEqual(window.remembered_character(), "")

    def test_a_remembered_label_reads_back(self):
        self.fake.stored[window._CHARACTER_OPTIONVAR] = "UE4 Mannequin"
        self.assertEqual(window.remembered_character(), "UE4 Mannequin")


class AddCharacterPress(unittest.TestCase):
    """2026-09-30: the colour left the Characters card - Add passes none (the
    next free colour), and a model without the chosen kind is refused by name."""

    def setUp(self):
        self.saved = [(window, n, getattr(window, n)) for n in
                      ("chosen_character", "remembered_choice", "refresh", "_status",
                       "_dropdown_value")]
        self.saved.append((window.character, "add_character", window.character.add_character))
        self.lines, self.added = [], []
        window._dropdown_value = lambda: None
        window.remembered_choice = lambda: ("Manny", "rig")
        window.refresh = lambda: None
        window._status = lambda message, control=None: self.lines.append(message)
        window.character.add_character = lambda entry, rgb=None, at=None: (
            self.added.append((entry.key, rgb, at)) or "added")

    def tearDown(self):
        for owner, name, value in self.saved:
            setattr(owner, name, value)

    def test_add_passes_no_colour(self):
        window.chosen_character = lambda: catalog.character_by_key("Creep_Rig")
        window.add_character()
        self.assertEqual(self.added, [("Creep_Rig", None, None)])
        self.assertEqual(self.lines[-1], "added")

    def test_an_absent_pair_is_refused(self):
        window.chosen_character = lambda: None
        window.remembered_choice = lambda: ("Orc_D", "skeleton")
        window.add_character()
        self.assertEqual(self.added, [])
        self.assertIn("Orc D has no skeleton", self.lines[-1])

    def test_a_drop_places_at_the_point(self):
        text = window.place_character("Manny", "rig", (1.0, 0.0, 2.0))
        self.assertEqual(self.added, [("Manny_Rig", None, (1.0, 0.0, 2.0))])
        self.assertEqual(text, "added")

    def test_a_drop_of_an_absent_pair_places_nothing(self):
        text = window.place_character("UE4_Mannequin", "rig", (1.0, 0.0, 2.0))
        self.assertEqual(self.added, [])
        self.assertIn("UE4 Mannequin has no rig", text)

    def test_the_auto_card_adds_nothing(self):
        """2026-10-02: Auto has no character of its own - an import finds one."""
        window.chosen_character = lambda: None
        window.remembered_choice = lambda: ("Auto", "rig")
        window.add_character()
        self.assertEqual(self.added, [])
        self.assertEqual(self.lines[-1], window.charlook.AUTO_ADD)

    def test_the_auto_card_is_never_placed(self):
        text = window.place_character("Auto", "skeleton", (1.0, 0.0, 2.0))
        self.assertEqual(self.added, [])
        self.assertEqual(text, window.charlook.AUTO_ADD)

    def test_the_auto_card_opens_no_scene(self):
        self.assertEqual(window.open_character_scene("Auto", "rig"),
                         window.charlook.AUTO_ADD)


class DeletePress(unittest.TestCase):
    """2026-10-01: Characters > Delete writes what `deletion` answers on the
    card's line, after the refresh, and hands the confirm through."""

    def setUp(self):
        from maya_scenesetup import deletion
        self.deletion = deletion
        self.saved = [(window, n, getattr(window, n)) for n in ("refresh", "_status")]
        self.saved.append((deletion, "delete_selected", deletion.delete_selected))
        self.lines, self.calls = [], []
        window.refresh = lambda: self.calls.append("refresh")
        window._status = lambda message, control=None: self.lines.append((message, control))
        deletion.delete_selected = lambda selection=None, confirm=None: (
            self.calls.append(("delete", confirm)) or "Deleted it")

    def tearDown(self):
        for owner, name, value in self.saved:
            setattr(owner, name, value)

    def test_the_line_is_the_deletions_and_comes_last(self):
        answer = lambda text: True                               # noqa: E731
        self.assertEqual(window.delete_characters(confirm=answer), "Deleted it")
        self.assertEqual(self.calls, [("delete", answer), "refresh"])
        self.assertEqual(self.lines[-1], ("Deleted it", window._CHARACTER_STATUS))


class OpenScene(unittest.TestCase):
    """2026-09-30: Open scene on a portrait or a weapon - the catalog's file
    handed to the opener, its answer on the card's line."""

    def setUp(self):
        from maya_scenesetup import opener
        self.opener = opener
        self.saved = [(window, n, getattr(window, n)) for n in ("refresh", "_status")]
        self.saved.append((opener, "open_asset", opener.open_asset))
        self.lines, self.opened = [], []
        window.refresh = lambda: None
        window._status = lambda message, control=None: self.lines.append(
            (message, control))
        opener.open_asset = lambda path, label: (
            self.opened.append((path, label)) or "opened " + label)

    def tearDown(self):
        for owner, name, value in self.saved:
            setattr(owner, name, value)

    def test_a_portrait_opens_the_file_of_the_shown_kind(self):
        text = window.open_character_scene("Creep", "skeleton")
        entry = catalog.character_for("Creep", "skeleton")
        self.assertEqual(self.opened, [(catalog.character_file(entry), "Creep [skeleton]")])
        self.assertEqual(text, "opened Creep [skeleton]")
        self.assertEqual(self.lines[-1], (text, window._CHARACTER_STATUS))

    def test_an_absent_pair_opens_nothing(self):
        text = window.open_character_scene("Orc_D", "skeleton")
        self.assertEqual(self.opened, [])
        self.assertIn("Orc D has no skeleton", text)

    def test_a_weapon_opens_its_catalog_file(self):
        text = window.open_weapon_scene("Spear_03")
        self.assertEqual(self.opened, [(catalog.by_key("Spear_03").path, "Spear 03")])
        self.assertEqual(self.lines[-1][0], text)

    def test_an_unknown_weapon_opens_nothing(self):
        self.assertEqual(window.open_weapon_scene("Nope"), "")
        self.assertEqual(self.opened, [])


class Choice(unittest.TestCase):
    """What the card opens on: the two optionVars, else the old dropdown's
    label, else the default rig."""

    def test_the_two_optionvars_win(self):
        self.assertEqual(window.choice_from("Creep", "skeleton", "Manny [rig]"),
                         ("Creep", "skeleton"))

    def test_the_old_label_is_the_fallback(self):
        self.assertEqual(window.choice_from("", "", "UE4 Mannequin [skeleton]"),
                         ("UE4_Mannequin", "skeleton"))

    def test_nothing_is_the_default_rig(self):
        self.assertEqual(window.choice_from(None, None, ""), ("Manny", "rig"))

    def test_a_stale_model_falls_back(self):
        self.assertEqual(window.choice_from("Sevarog", "rig", ""), ("Manny", "rig"))

    def test_chosen_character_reads_the_choice_without_the_dropdown(self):
        fake = FakeUiCmds(menu_exists=False, stored={
            window._MODEL_OPTIONVAR: "Orc_D", window._KIND_OPTIONVAR: "skeleton"})
        real, window.cmds = window.cmds, fake
        try:
            self.assertIsNone(window.chosen_character())
            fake.stored[window._KIND_OPTIONVAR] = "rig"
            self.assertEqual(window.chosen_character().key, "Orc_D_Rig")
        finally:
            window.cmds = real

    def test_the_auto_card_is_a_kept_choice_with_no_row(self):
        """2026-10-02: «Auto» is a model of its own, pickable in both kinds."""
        self.assertEqual(window.choice_from("Auto", "skeleton", ""), ("Auto", "skeleton"))
        fake = FakeUiCmds(menu_exists=False, stored={
            window._MODEL_OPTIONVAR: "Auto", window._KIND_OPTIONVAR: "skeleton"})
        real, window.cmds = window.cmds, fake
        try:
            self.assertIsNone(window.chosen_character())
            self.assertEqual(window.current_choice(), ("Auto", "skeleton"))
            self.assertEqual(window.auto_kind(), "skeleton")
            fake.stored[window._MODEL_OPTIONVAR] = "Manny"
            self.assertIsNone(window.auto_kind())
        finally:
            window.cmds = real

    def test_the_dropdown_carries_the_auto_card_too(self):
        """Without Qt the card is a dropdown: «Auto [rig]» / «Auto [skeleton]» after the rows."""
        fake = FakeUiCmds(menu_value="Auto [rig]")
        real, window.cmds = window.cmds, fake
        try:
            self.assertIsNone(window.chosen_character())
            self.assertEqual(window.current_choice(), ("Auto", "rig"))
            self.assertEqual(window.auto_kind(), "rig")
            fake.menu_value = "Creep [skeleton]"
            self.assertEqual(window.current_choice(), ("Creep", "skeleton"))
            self.assertIsNone(window.auto_kind())
            self.assertEqual(window.chosen_character().key, "Creep")
        finally:
            window.cmds = real

    def test_picking_the_auto_card_says_what_an_import_does(self):
        fake = FakeUiCmds(menu_exists=False, stored={window._KIND_OPTIONVAR: "rig"})
        real, window.cmds = window.cmds, fake
        try:
            window.select_model("Auto")
            self.assertEqual(fake.stored[window._MODEL_OPTIONVAR], "Auto")
            self.assertEqual(fake.status[-1], window.charlook.auto_text("rig"))
        finally:
            window.cmds = real

    def test_selecting_a_model_remembers_it_and_says_what_add_brings(self):
        fake = FakeUiCmds(menu_exists=False)
        real, window.cmds = window.cmds, fake
        try:
            window.select_model("Creep")
            self.assertEqual(fake.stored[window._MODEL_OPTIONVAR], "Creep")
            self.assertIn("Creep [rig]", fake.status[-1])
        finally:
            window.cmds = real


class Gone(unittest.TestCase):
    """2026-09-30: the Weapons card IS the inventory. The colour went to the
    Colour section, the custom FBX «пока уберем совсем», the dropdown and
    the Hand row to the grid and the hand cards, the grip rows to the
    Channel Box columns, the Inventory button with the floating window."""

    def test_the_retired_names_are_gone(self):
        for name in ("chosen_entry", "custom_changed", "browse_fbx",
                     "_remembered_path", "_CUSTOM", "_CUSTOM_OPTIONVAR",
                     "_BROWSE", "_MENU", "_ROTATE", "_TRANSLATE", "_fields",
                     "_set_fields", "offsets_changed", "_WEAPON_COLOUR",
                     "_WEAPON_DOT", "recolour_weapon", "_colour_row",
                     "pick_dot", "_swatch", "_set_swatch", "_advance_swatch",
                     "NO_COLOUR_TARGET", "recoloured_message", "appearance",
                     "open_inventory", "_hand_row", "_entry",
                     "added_message", "removed_message", "_rides",
                     "character_colour_changed", "weapon_colour_changed",
                     "_CHARACTER_COLOUR", "_CHARACTER_DOT"):
            self.assertFalse(hasattr(window, name), name)


class Picked(unittest.TestCase):
    """Which weapon and which hand the card has picked: two optionVars."""

    def setUp(self):
        self.fake = FakeUiCmds(menu_exists=False)
        self.real, window.cmds = window.cmds, self.fake
        self.saved = [(window.skeleton, "current_root",
                       window.skeleton.current_root)]
        window.skeleton.current_root = lambda: None

    def tearDown(self):
        window.cmds = self.real
        for owner, name, value in self.saved:
            setattr(owner, name, value)

    def test_nothing_picked_is_the_first_row_and_the_right_hand(self):
        self.assertIs(window.chosen_weapon(), catalog.WEAPONS[0])
        self.assertEqual(window.side(), "R")
        self.assertEqual(window.picked(), (catalog.WEAPONS[0].key, "R"))

    def test_a_stale_key_falls_back(self):
        self.fake.stored[window._WEAPON_OPTIONVAR] = "Excalibur"
        self.fake.stored[window._HAND_OPTIONVAR] = "X"
        self.assertIs(window.chosen_weapon(), catalog.WEAPONS[0])
        self.assertEqual(window.side(), "R")

    def test_picking_a_weapon_remembers_it_and_says_what_add_does(self):
        text = window.select_weapon("Spear_03")
        self.assertEqual(self.fake.stored[window._WEAPON_OPTIONVAR], "Spear_03")
        self.assertIs(window.chosen_weapon(), catalog.by_key("Spear_03"))
        self.assertIn("Spear 03", text)
        self.assertIn("right hand", text)
        self.assertEqual(self.fake.status[-1], text)

    def test_an_unknown_weapon_changes_nothing(self):
        self.assertEqual(window.select_weapon("Excalibur"), "")
        self.assertNotIn(window._WEAPON_OPTIONVAR, self.fake.stored)

    def test_picking_a_hand_remembers_it(self):
        text = window.select_hand("L")
        self.assertEqual(window.side(), "L")
        self.assertIn("left hand", text)
        self.assertIn("free", text)
        self.assertEqual(window.select_hand("Q"), "")
        self.assertEqual(window.side(), "L")

    def test_the_hand_line_names_what_it_holds(self):
        text = window.hand_pick_text("R", "Dagger 01", "Long Sword 02")
        self.assertIn("Long Sword 02", text)
        self.assertIn("Dagger 01", text)
        self.assertIn("Unequip", text)


class FakeEquip(object):
    """Records what Add and Remove ask of `equip`; occupant/bones on demand."""

    def __init__(self):
        self.calls = []
        self.held = {}
        self.bone_of = {"R": ("|root|hand_r", "|root|hand_r|weapon_r"),
                        "L": ("|root|hand_l", "|root|hand_l|weapon_l")}

    def to_hand(self, root, key, entry):
        self.calls.append(("to_hand", root, key, entry.key))
        return "into"

    def take_off(self, root, key):
        self.calls.append(("take_off", root, key))
        return "off"

    def bones(self, root, key):
        return self.bone_of[key]

    def occupant(self, root, key):
        return self.held.get(key, (None, None))


class AddRemovePress(unittest.TestCase):
    """Add and Remove go through `equip` - the inventory's own path - with the
    picked weapon and hand, after the refusals only the card knows."""

    def setUp(self):
        self.fake = FakeUiCmds(menu_exists=False, stored={
            window._WEAPON_OPTIONVAR: "Dagger_01", window._HAND_OPTIONVAR: "L"})
        self.equip = FakeEquip()
        self.saved = [(window, n, getattr(window, n)) for n in
                      ("cmds", "equip", "_locate", "_status")]
        self.saved.append((window.linking, "linked_weapon",
                           window.linking.linked_weapon))
        self.lines = []
        window.cmds = self.fake
        window.equip = self.equip
        window._status = lambda message, control=None: self.lines.append(message)
        window.linking.linked_weapon = lambda: None
        self.located = ("|root", "|root|hand_l", "|root|hand_l|weapon_l", None,
                        False)
        window._locate = lambda entry, key=None: self.located

    def tearDown(self):
        for owner, name, value in self.saved:
            setattr(owner, name, value)

    def test_add_puts_the_picked_weapon_into_the_picked_hand(self):
        window.add_weapon()
        self.assertEqual(self.equip.calls, [("to_hand", "|root", "L", "Dagger_01")])
        self.assertEqual(self.lines[-1], "into")

    def test_add_and_remove_refresh_the_inventory_after(self):
        """Measured live: a refresh the import's selection change queued ran
        midway and left the column showing a half-attached grip."""
        refreshed = []

        class Panel(object):
            def refresh(self):
                refreshed.append(list(self_equip.calls))
        self_equip = self.equip
        saved = window._inventory
        window._inventory = lambda: Panel()
        try:
            window.add_weapon()
            window.remove_weapon()
        finally:
            window._inventory = saved
        self.assertEqual([len(calls) for calls in refreshed], [1, 2])

    def test_remove_takes_the_picked_hand_off(self):
        window.remove_weapon()
        self.assertEqual(self.equip.calls, [("take_off", "|root", "L")])
        self.assertEqual(self.lines[-1], "off")

    def test_a_refusal_calls_nothing(self):
        window._locate = lambda entry, key=None: None
        window.add_weapon()
        window.remove_weapon()
        self.assertEqual(self.equip.calls, [])

    def test_the_legacy_link_is_refused_by_name(self):
        window.linking.linked_weapon = lambda: "|LongSwordMesh"
        window.add_weapon()
        window.remove_weapon()
        self.assertEqual(self.equip.calls, [])
        self.assertEqual(self.lines, [window.LINKED_NO_ADD,
                                      window.LINKED_NO_REMOVE])


class HandGrip(unittest.TestCase):
    """What a hand's column shows and what an edit of it does."""

    class FakeGrips(object):
        def __init__(self):
            self.remembered = []

        def for_hand(self, entry, key, root):
            return ((1.0, 2.0, 3.0), (4.0, 5.0, 6.0)) if key == "R" else \
                ((7.0, 8.0, 9.0), (0.5, 0.5, 0.5))

        def remember(self, weapon_key, key, rotate, translate):
            self.remembered.append((weapon_key, key, tuple(rotate),
                                    tuple(translate)))

        def standard(self, rotate, translate, frame, entry):
            return rotate, translate

        def on_node(self, rotate, translate, frame, entry):
            return rotate, translate

    class FakeDrive(object):
        def __init__(self):
            self.regrips = []
            self.held = True

        def is_held(self, weapon):
            return self.held

        def measured_grip(self, weapon, bone):
            return (0.0, 90.0, 0.0), (1.0, 0.0, 0.0)

        def frame_of(self, weapon):
            return (0.0, 0.0, 0.0)

        def regrip(self, weapon, bone, rotate, translate):
            self.regrips.append((weapon, bone, rotate, translate))

    def setUp(self):
        self.fake = FakeUiCmds(menu_exists=False, stored={
            window._WEAPON_OPTIONVAR: "Spear_03"})
        self.equip = FakeEquip()
        self.grips = self.FakeGrips()
        self.drive = self.FakeDrive()
        self.saved = [(window, n, getattr(window, n)) for n in
                      ("cmds", "equip", "grips", "bonedrive", "_status",
                       "_held_entry", "_follows")]
        self.saved += [(window.skeleton, "current_root",
                        window.skeleton.current_root),
                       (window.attach, "is_animated", window.attach.is_animated)]
        self.lines = []
        window.cmds = self.fake
        window.equip = self.equip
        window.grips = self.grips
        window.bonedrive = self.drive
        window._status = lambda message, control=None: self.lines.append(message)
        window._held_entry = lambda weapon, entry: catalog.by_key("LongSword_02")
        window._follows = lambda root, key: None
        window.skeleton.current_root = lambda: "|root"
        self.animated = False
        window.attach.is_animated = lambda weapon: self.animated

    def tearDown(self):
        for owner, name, value in self.saved:
            setattr(owner, name, value)

    def test_empty_hands_show_the_picked_weapons_grips_editable(self):
        grips = window.hand_grips("|root")
        self.assertEqual(grips["R"], ((1.0, 2.0, 3.0), (4.0, 5.0, 6.0), True))
        self.assertEqual(grips["L"], ((7.0, 8.0, 9.0), (0.5, 0.5, 0.5), True))

    def test_a_held_clean_weapon_shows_its_measured_grip(self):
        self.equip.held["R"] = ("|sword", "hand")
        self.assertEqual(window.hand_grips("|root")["R"],
                         ((0.0, 90.0, 0.0), (1.0, 0.0, 0.0), True))

    def test_a_following_hand_or_no_character_is_read_only(self):
        window._follows = lambda root, key: "|sword" if key == "L" else None
        self.assertFalse(window.hand_grips("|root")["L"][2])
        self.assertTrue(window.hand_grips("|root")["R"][2])
        self.assertFalse(window.hand_grips(None)["R"][2])

    def test_an_edit_of_a_held_weapon_regrips_it_and_remembers_its_grip(self):
        self.equip.held["R"] = ("|sword", "hand")
        window.set_hand_grip("R", (0.0, 45.0, 0.0), (1.0, 2.0, 3.0))
        self.assertEqual(self.grips.remembered,
                         [("LongSword_02", "R", (0.0, 45.0, 0.0), (1.0, 2.0, 3.0))])
        self.assertEqual(self.drive.regrips,
                         [("|sword", "|root|hand_r|weapon_r", (0.0, 45.0, 0.0),
                           (1.0, 2.0, 3.0))])
        self.assertIn("Long Sword 02", self.lines[-1])

    def test_an_edit_of_an_empty_hand_remembers_the_picked_weapons(self):
        text = window.set_hand_grip("L", (1.0, 1.0, 1.0), (0.0, 0.0, 0.0))
        self.assertEqual(self.grips.remembered,
                         [("Spear_03", "L", (1.0, 1.0, 1.0), (0.0, 0.0, 0.0))])
        self.assertEqual(self.drive.regrips, [])
        self.assertIn("next Equip", text)

    def test_an_animated_or_floor_weapon_is_remembered_not_moved(self):
        self.equip.held["R"] = ("|sword", "hand")
        self.animated = True
        self.assertEqual(window.set_hand_grip("R", (0, 0, 0), (0, 0, 0)),
                         window.LINKED_NO_OFFSETS)
        self.equip.held["R"] = ("|sword", "floor")
        self.assertIn("floor", window.set_hand_grip("R", (0, 0, 0), (0, 0, 0)))
        self.assertEqual(self.drive.regrips, [])
        self.assertEqual(len(self.grips.remembered), 2)
