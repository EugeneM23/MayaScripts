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

    def test_there_is_an_add_aim_callback(self):
        self.assertTrue(callable(window.add_aim))


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


class GripValues(unittest.TestCase):
    """Which grip the fields show, and in which SPACE (2026-08-21).

    The stored grip used to mean "channels under weapon_r"; the channels
    live under the hand now, so the same six numbers mean something else.
    New-era saves are raw; old-era saves compose with the drive bone's
    local matrix; and old-space numbers are never displayed as if they
    were new-space.
    """

    def _compose(self, calls):
        def compose(rotate, translate, bone_local):
            calls.append((rotate, translate, bone_local))
            return (7.0, 8.0, 9.0), (10.0, 11.0, 12.0)
        return compose

    def test_a_new_era_save_is_returned_raw(self):
        calls = []
        got = window.grip_values([1, 2, 3, 4, 5, 6], [9] * 6, "L",
                                 self._compose(calls))
        self.assertEqual(got, ((1.0, 2.0, 3.0), (4.0, 5.0, 6.0)))
        self.assertEqual(calls, [])

    def test_an_old_era_save_composes_with_the_bone(self):
        calls = []
        got = window.grip_values(None, [1, 2, 3, 4, 5, 6], "L",
                                 self._compose(calls))
        self.assertEqual(got, ((7.0, 8.0, 9.0), (10.0, 11.0, 12.0)))
        self.assertEqual(calls, [((1.0, 2.0, 3.0), (4.0, 5.0, 6.0), "L")])

    def test_no_save_defaults_to_the_bone_itself(self):
        """Zeros through the composition ARE the drive bone's pose - the
        sword lands exactly on weapon_r, which is the game's own grip."""
        calls = []
        window.grip_values(None, None, "L", self._compose(calls))
        self.assertEqual(calls, [((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), "L")])

    def test_without_a_bone_zeros_stand_in(self):
        """Old-space numbers must never be shown as if they were new-space;
        with no character there is nothing to compose against."""
        calls = []
        got = window.grip_values(None, [1, 2, 3, 4, 5, 6], None,
                                 self._compose(calls))
        self.assertEqual(got, ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0)))
        self.assertEqual(calls, [])

    def test_the_grip_optionvar_is_its_own_name(self):
        """A new space needs a new name, or an old-era triple would be read
        back as under-hand channels and put the sword at the hand origin."""
        self.assertNotEqual(window.grip_optionvar_name("LongSword_02"),
                            window.optionvar_name("LongSword_02"))
        self.assertIn("LongSword_02",
                      window.grip_optionvar_name("LongSword_02"))


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

    def test_no_character_points_at_both_ways_out(self):
        self.assertIn("picker", window.NO_CHARACTER)
        self.assertIn("select", window.NO_CHARACTER)

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
