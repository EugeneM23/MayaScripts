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
        for name in ("connect_arms", "disconnect_arms", "add_aim"):
            self.assertFalse(hasattr(window, name), name)
        for name in ("add_character", "add_weapon", "remove_weapon",
                     "recolour_character", "recolour_weapon", "camera_setup"):
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

    def test_removed_names_the_weapon(self):
        self.assertIn(SWORD.label, window.removed_message(SWORD))

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
        self.assertEqual(window.bound_message("|root", rig=True),
                         "Character: root (rig)")
        self.assertEqual(window.bound_message("|clip:root", rig=False),
                         "Character: clip:root (skeleton)")
        self.assertEqual(window.bound_message("|SKM_Manny|root"),
                         "Character: root (skeleton)")

    def test_missing_bone_names_the_bone_and_the_character(self):
        message = window.missing_bone_message("|SKM_Manny|root", "weapon_r")
        self.assertIn("weapon_r", message)
        self.assertIn("root", message)
        self.assertNotIn("|", message)

    def test_missing_file_names_the_path(self):
        self.assertIn("C:/x/y.fbx", window.missing_file_message("C:/x/y.fbx"))

    def test_added_names_the_weapon_and_the_bone(self):
        message = window.added_message(SWORD, "|SKM_Manny|root|weapon_r")
        self.assertIn(SWORD.label, message)
        self.assertIn("weapon_r", message)
        self.assertNotIn("|", message)

    def test_a_coloured_weapon_names_its_colour(self):
        self.assertEqual(window.appearance(SWORD, (0.80, 0.25, 0.22), []),
                         "red")

    def test_a_textured_weapon_says_textured_not_a_colour(self):
        """2026-09-28, Spear 03: no swatch colour went on it."""
        spear = catalog.by_key("Spear_03")
        self.assertEqual(window.appearance(spear, (0.80, 0.25, 0.22), []),
                         "textured")

    def test_viewport_textures_turned_on_are_said(self):
        spear = catalog.by_key("Spear_03")
        text = window.appearance(spear, (0.80, 0.25, 0.22), ["modelPanel4"])
        self.assertIn("textured", text)
        self.assertIn("viewport textures on", text)

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


class ChosenEntry(unittest.TestCase):
    """The FBX field wins over the dropdown when it holds a path."""

    def test_an_empty_field_leaves_the_dropdown_alone(self):
        self.assertIs(window.chosen_entry("", SWORD), SWORD)

    def test_none_leaves_the_dropdown_alone(self):
        self.assertIs(window.chosen_entry(None, SWORD), SWORD)

    def test_whitespace_is_empty(self):
        """A stray space must not redirect Add at a file called " "."""
        self.assertIs(window.chosen_entry("   ", SWORD), SWORD)

    def test_a_path_wins_over_the_dropdown(self):
        got = window.chosen_entry("D:/props/Axe_01.fbx", SWORD)
        self.assertEqual(got.path, "D:/props/Axe_01.fbx")
        self.assertEqual(got.key, "Axe_01")

    def test_the_bone_comes_from_the_dropdown(self):
        got = window.chosen_entry("D:/props/Axe_01.fbx", SWORD)
        self.assertEqual(got.bone, SWORD.bone)

    def test_the_scale_is_never_the_dropdowns(self):
        got = window.chosen_entry("D:/props/Axe_01.fbx", SWORD)
        self.assertEqual(got.scale, 1.0)

    def test_the_path_is_stripped(self):
        got = window.chosen_entry("  D:/props/Axe_01.fbx  ", SWORD)
        self.assertEqual(got.path, "D:/props/Axe_01.fbx")

    def test_quotes_pasted_from_the_explorer_are_dropped(self):
        """Windows Explorer copies a path wrapped in double quotes."""
        got = window.chosen_entry('"D:/props/Axe_01.fbx"', SWORD)
        self.assertEqual(got.path, "D:/props/Axe_01.fbx")

    def test_the_key_is_legal_as_a_node_name(self):
        got = window.chosen_entry("D:/props/2 Handed Axe.fbx", SWORD)
        self.assertEqual(got.key, "_2_Handed_Axe")


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


class ColourSwatches(unittest.TestCase):
    """What the two swatches mean. The widgets themselves need a live Maya;
    what is testable is the policy in front of them."""

    def test_the_refusal_is_its_own_message(self):
        """A swatch moved with nothing connected is not "nothing attached" --
        it is previewing the next Add, and saying so is the difference
        between a dead control and one that is waiting."""
        self.assertNotEqual(window.NO_COLOUR_TARGET, window.NOT_ATTACHED)
        self.assertIn("next Add", window.NO_COLOUR_TARGET)

    def test_recoloured_names_the_colour_and_the_leaf(self):
        from maya_scenesetup import colour
        message = window.recoloured_message("|group|root",
                                            colour.PALETTE[0].rgb)
        self.assertIn("root", message)
        self.assertNotIn("|", message)
        self.assertIn("red", message)

    def test_a_hand_dialled_colour_is_still_reported(self):
        message = window.recoloured_message("root", (0.11, 0.93, 0.44))
        self.assertIn("custom", message)

    def test_both_recolour_buttons_exist(self):
        self.assertTrue(callable(window.recolour_character))
        self.assertTrue(callable(window.recolour_weapon))

    def test_the_changeCommand_callbacks_are_gone(self):
        """The swatch used to repaint on change; the animator reversed it
        («цвет будем задавать перед созданием персонажа или оружия в
        сцене») and a Recolour button took over. Leaving the old names
        around is how a caller keeps reaching the retired behaviour."""
        self.assertFalse(hasattr(window, "character_colour_changed"))
        self.assertFalse(hasattr(window, "weapon_colour_changed"))

    def test_the_two_swatches_are_different_controls(self):
        """One layout, two rows: sharing a name would make the weapon's
        swatch edit the character's."""
        self.assertNotEqual(window._CHARACTER_COLOUR, window._WEAPON_COLOUR)


class NextAddColour(unittest.TestCase):
    """The swatch means ONE thing: the colour the next Add will bring.

    It is filled on open and advanced after every press, and `refresh`
    never touches it -- a refresh fires on every dropdown change and at the
    front of every press, so writing to it there would throw away the
    colour the animator had just picked.
    """

    class FakeColouring(object):
        def __init__(self, free=(0.1, 0.2, 0.3)):
            self._free = free
            self.painted = []

        def free_colour(self):
            class _Entry(object):
                pass
            entry = _Entry()
            entry.rgb = self._free
            return entry

    def setUp(self):
        self.real_colouring = window.colouring
        self.real_set = window._set_swatch
        self.written = []
        window._set_swatch = lambda control, rgb: self.written.append(
            (control, tuple(rgb)))

    def tearDown(self):
        window.colouring = self.real_colouring
        window._set_swatch = self.real_set

    def test_advancing_writes_the_next_free_colour(self):
        window.colouring = self.FakeColouring(free=(0.9, 0.5, 0.18))
        window._advance_swatch(window._CHARACTER_COLOUR)
        self.assertEqual(self.written,
                         [(window._CHARACTER_COLOUR, (0.9, 0.5, 0.18))])

    def test_refresh_is_not_what_fills_it(self):
        """The guard against the one bug this design can have: a `refresh`
        overwriting a colour the animator chose a second earlier.

        Comments are stripped before the check -- `refresh` says out loud
        that it leaves the swatches alone, and naming the functions it does
        not call must not be what fails this.
        """
        import inspect
        code = [line.split("#")[0]
                for line in inspect.getsource(window.refresh).splitlines()]
        body = chr(10).join(code)
        self.assertNotIn("_set_swatch(", body)
        self.assertNotIn("_advance_swatch(", body)


class TexturedAddKeepsTheSwatch(unittest.TestCase):
    """A textured character used no colour (2026-09-28, the Orc D), so the swatch is not moved on:
    the colour the animator picked is still the next coloured Add's -- Weapons > Add's rule for
    Spear 03."""

    def setUp(self):
        self.saved = [(window, n, getattr(window, n)) for n in
                      ("chosen_character", "_swatch", "refresh", "_advance_swatch", "_status")]
        self.saved.append((window.character, "add_character", window.character.add_character))
        self.advanced = []
        window._swatch = lambda control: (0.1, 0.2, 0.3)
        window.refresh = lambda: None
        window._advance_swatch = lambda control: self.advanced.append(control)
        window._status = lambda message, control=None: None
        window.character.add_character = lambda entry, rgb: "added"

    def tearDown(self):
        for owner, name, value in self.saved:
            setattr(owner, name, value)

    def test_the_textured_orc_leaves_the_swatch(self):
        window.chosen_character = lambda: catalog.character_by_key("Orc_D_Rig")
        window.add_character()
        self.assertEqual(self.advanced, [])

    def test_a_coloured_character_still_advances_it(self):
        window.chosen_character = lambda: catalog.character_by_key("Manny_Rig")
        window.add_character()
        self.assertEqual(self.advanced, [window._CHARACTER_COLOUR])
