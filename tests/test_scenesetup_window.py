"""Tests for the window's policy: optionVars, and what the status line says.

The widgets themselves are proved live -- a `cmds` window cannot be built
without Maya. What is testable is everything the callbacks decide before they
touch a widget.
"""

import sys
import types
import unittest


def _install_fake_maya():
    """Let window import without Maya. See CLAUDE.md on rebinding."""
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

from maya_scenesetup import catalog  # noqa: E402
from maya_scenesetup import window  # noqa: E402

SWORD = catalog.by_key("LongSword_02")


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
        """Replacing would delete the carrier, and the IK controls are its
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
