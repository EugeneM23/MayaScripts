"""Tests for the attach mechanics.

The import itself needs a live Maya and a real FBX, so it is proved by
docs/superpowers/plans/verify_weapons.py. What is testable here is everything
around it: which imported transforms are the roots, how the attached weapon is
recognised, and that writing offsets cannot leave autoKey on.
"""

import sys
import types
import unittest


def _install_fake_maya():
    """Let attach import without Maya. See CLAUDE.md on rebinding."""
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

from maya_weapons import attach  # noqa: E402

BONE = "|SKM_Manny|root|hand_r|weapon_r"


class FakeCmds(object):
    """Enough of maya.cmds for the child walk and the attribute writes."""

    def __init__(self, children=(), marked=()):
        self._children = list(children)
        self._marked = set(marked)
        self.attrs = {}
        self.deleted = []
        self.autokey = True
        self.autokey_during_write = []

    def listRelatives(self, node, children=False, type=None, fullPath=False,
                      **kwargs):
        if not children:
            return None
        found = [c for c in self._children if c.rsplit("|", 1)[0] == node]
        return found or None

    def attributeQuery(self, name, node=None, exists=False, **kwargs):
        return node in self._marked and name == attach.MARKER

    def delete(self, node):
        self.deleted.append(node)

    def setAttr(self, plug, *values, **kwargs):
        self.attrs[plug] = values[0] if len(values) == 1 else values
        self.autokey_during_write.append(self.autokey)

    def getAttr(self, plug):
        return self.attrs.get(plug, 0.0)

    def autoKeyframe(self, query=False, state=None):
        if query:
            return self.autokey
        self.autokey = state


class Outermost(unittest.TestCase):
    """Which of the imported transforms go into the carrier."""

    def test_keeps_a_lone_transform(self):
        self.assertEqual(attach.outermost(["|sword"]), ["|sword"])

    def test_drops_the_children(self):
        self.assertEqual(
            attach.outermost(["|sword", "|sword|blade", "|sword|grip"]),
            ["|sword"])

    def test_keeps_two_unrelated_roots(self):
        self.assertEqual(attach.outermost(["|sword", "|scabbard"]),
                         ["|sword", "|scabbard"])

    def test_a_shared_prefix_is_not_containment(self):
        """'|swordExtra' is not a child of '|sword'. The separator is the test."""
        self.assertEqual(attach.outermost(["|sword", "|swordExtra"]),
                         ["|sword", "|swordExtra"])

    def test_empty_stays_empty(self):
        self.assertEqual(attach.outermost([]), [])


class CarrierName(unittest.TestCase):

    def test_names_the_carrier_after_the_weapon(self):
        self.assertEqual(attach.carrier_name("LongSword_02"),
                         "LongSword_02_weapon")


class FindAttached(unittest.TestCase):

    def test_finds_the_marked_child(self):
        fake = FakeCmds(children=[BONE + "|prop", BONE + "|LongSword_02_weapon"],
                        marked=[BONE + "|LongSword_02_weapon"])
        attach.cmds = fake
        self.assertEqual(attach.find_attached(BONE),
                         BONE + "|LongSword_02_weapon")

    def test_ignores_children_the_animator_parented_by_hand(self):
        """Only what this module attached is ours to delete."""
        fake = FakeCmds(children=[BONE + "|LongSword_02_weapon"], marked=[])
        attach.cmds = fake
        self.assertIsNone(attach.find_attached(BONE))

    def test_is_none_when_the_bone_is_bare(self):
        attach.cmds = FakeCmds()
        self.assertIsNone(attach.find_attached(BONE))

    def test_remove_deletes_only_the_marked_child(self):
        fake = FakeCmds(children=[BONE + "|prop", BONE + "|LongSword_02_weapon"],
                        marked=[BONE + "|LongSword_02_weapon"])
        attach.cmds = fake
        attach.remove_attached(BONE)
        self.assertEqual(fake.deleted, [BONE + "|LongSword_02_weapon"])

    def test_remove_on_a_bare_bone_deletes_nothing(self):
        fake = FakeCmds()
        attach.cmds = fake
        self.assertIsNone(attach.remove_attached(BONE))
        self.assertEqual(fake.deleted, [])


class Offsets(unittest.TestCase):

    def setUp(self):
        self.fake = FakeCmds()
        attach.cmds = self.fake

    def test_writes_all_six_channels(self):
        attach.write_offsets("|c", (10.0, 20.0, 30.0), (1.0, 2.0, 3.0))
        self.assertEqual(self.fake.attrs["|c.rotateY"], 20.0)
        self.assertEqual(self.fake.attrs["|c.translateZ"], 3.0)

    def test_autokey_is_off_for_every_write(self):
        """The user works with autoKey ON; a scripted poke must not key."""
        attach.write_offsets("|c", (10.0, 0.0, 0.0), (0.0, 0.0, 0.0))
        self.assertEqual(set(self.fake.autokey_during_write), {False})

    def test_autokey_is_put_back(self):
        attach.write_offsets("|c", (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
        self.assertTrue(self.fake.autokey)

    def test_autokey_is_put_back_even_when_a_write_blows_up(self):
        def boom(plug, *values, **kwargs):
            raise RuntimeError("locked channel")
        self.fake.setAttr = boom
        with self.assertRaises(RuntimeError):
            attach.write_offsets("|c", (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
        self.assertTrue(self.fake.autokey)

    def test_reads_what_it_wrote(self):
        attach.write_offsets("|c", (10.0, 20.0, 30.0), (1.0, 2.0, 3.0))
        rotate, translate = attach.read_offsets("|c")
        self.assertEqual(rotate, (10.0, 20.0, 30.0))
        self.assertEqual(translate, (1.0, 2.0, 3.0))
