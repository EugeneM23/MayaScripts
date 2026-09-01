"""Tests for manifest identity: whose rig is whose.

The decision this module makes goes wrong SILENTLY -- a second character
in the scene used to read as unrigged, so a build stacked FK over live IK
and a bake took the other character's limbs apart. So the pure half is
pinned hard here, and the scene half runs against a fake `cmds` where the
shape of the call is the thing under test.

The live proof is docs/superpowers/plans/verify_two_characters.py.
"""

import sys
import types
import unittest


def _install_fake_maya():
    """Let manifest import without a Maya session.

    Real modules win when they are importable -- under mayapy they always
    are -- and manifest reaches overrig, which needs maya.mel too.
    """
    try:
        import maya.cmds  # noqa: F401
        import maya.mel  # noqa: F401
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

from maya_overrig import manifest  # noqa: E402

R = manifest.Record

CHAR_A = "AAAAAAAA-0000-0000-0000-000000000001"
CHAR_B = "BBBBBBBB-0000-0000-0000-000000000002"


# ---------------------------------------------------------------------------
# pure
# ---------------------------------------------------------------------------

class SetNames(unittest.TestCase):

    def test_each_kind_has_its_own_prefix(self):
        self.assertEqual(manifest.set_name_for(manifest.KIND_IK, "arm_l"),
                         "RigPicker_build_arm_l")
        self.assertEqual(manifest.set_name_for(manifest.KIND_FK, "spine"),
                         "RigPicker_fk_spine")
        self.assertEqual(manifest.set_name_for(manifest.KIND_TWIST, "leg_r"),
                         "RigPicker_twist_leg_r")
        self.assertEqual(manifest.set_name_for(manifest.KIND_AIM, "Sword"),
                         "RigPicker_aim_Sword")

    def test_the_nameless_fk_manifest_is_the_legacy_flat_set(self):
        self.assertEqual(manifest.set_name_for(manifest.KIND_FK, ""),
                         "RigPicker_fk")

    def test_every_name_carries_the_shared_prefix(self):
        """builder.recorded_members() finds them all by RigPicker_, which
        is what shields every manifest from _reclaim."""
        for kind, name in ((manifest.KIND_IK, "arm_l"),
                           (manifest.KIND_FK, "spine"),
                           (manifest.KIND_FK, ""),
                           (manifest.KIND_TWIST, "leg_r"),
                           (manifest.KIND_AIM, "Sword")):
            self.assertTrue(
                manifest.set_name_for(kind, name).startswith(
                    manifest.PREFIX), (kind, name))

    def test_an_unknown_kind_raises_rather_than_inventing_a_name(self):
        with self.assertRaises(ValueError):
            manifest.set_name_for("spline", "spine")


class Classify(unittest.TestCase):
    """The legacy read: (kind, name) out of a set NAME."""

    def test_round_trips_every_kind(self):
        for kind, name in ((manifest.KIND_IK, "arm_l"),
                           (manifest.KIND_FK, "spine"),
                           (manifest.KIND_FK, ""),
                           (manifest.KIND_TWIST, "leg_r"),
                           (manifest.KIND_AIM, "LongSword_02")):
            self.assertEqual(
                manifest.classify(manifest.set_name_for(kind, name)),
                (kind, name), (kind, name))

    def test_the_flat_fk_set_is_not_read_as_a_chain(self):
        self.assertEqual(manifest.classify("RigPicker_fk"),
                         (manifest.KIND_FK, ""))

    def test_a_foreign_set_classifies_as_nothing(self):
        for name in ("OverRig_knots", "defaultLightSet", "", "RigPicker_",
                     "myRigPicker_fk_spine"):
            self.assertEqual(manifest.classify(name), ("", ""), name)

    def test_a_chain_name_holding_the_kind_word_survives(self):
        self.assertEqual(manifest.classify("RigPicker_fk_clavicle_l"),
                         (manifest.KIND_FK, "clavicle_l"))


class OwnerMatches(unittest.TestCase):

    def test_a_tagged_manifest_belongs_to_the_character_it_names(self):
        self.assertTrue(manifest.owner_matches(CHAR_A, CHAR_A, sole=False))
        self.assertFalse(manifest.owner_matches(CHAR_A, CHAR_B, sole=False))

    def test_a_tagged_manifest_is_not_up_for_grabs_even_alone(self):
        """Sole-character is the LEGACY rule. A tagged manifest names its
        owner, and a second character must never inherit it."""
        self.assertFalse(manifest.owner_matches(CHAR_A, CHAR_B, sole=True))

    def test_an_untagged_manifest_answers_for_the_sole_character(self):
        self.assertTrue(manifest.owner_matches("", CHAR_A, sole=True))

    def test_an_untagged_manifest_answers_for_nobody_in_a_crowd(self):
        self.assertFalse(manifest.owner_matches("", CHAR_A, sole=False))

    def test_no_active_character_owns_nothing(self):
        self.assertFalse(manifest.owner_matches(CHAR_A, None, sole=False))
        self.assertFalse(manifest.owner_matches(CHAR_A, "", sole=True))


class Pick(unittest.TestCase):

    def test_finds_this_characters_manifest_among_two(self):
        table = [R("RigPicker_build_arm_l", CHAR_A, "ik", "arm_l"),
                 R("RigPicker_build_arm_l1", CHAR_B, "ik", "arm_l")]
        self.assertEqual(
            manifest.pick(table, "ik", "arm_l", CHAR_B, sole=False),
            "RigPicker_build_arm_l1")

    def test_mayas_uniquifying_digit_is_never_parsed(self):
        """The whole point: `RigPicker_build_arm_l1` is arm_l, and only
        the tag says so."""
        table = [R("RigPicker_build_arm_l1", CHAR_B, "ik", "arm_l")]
        self.assertEqual(
            manifest.pick(table, "ik", "arm_l", CHAR_B, sole=False),
            "RigPicker_build_arm_l1")

    def test_a_character_with_nothing_built_gets_none(self):
        table = [R("RigPicker_build_arm_l", CHAR_A, "ik", "arm_l")]
        self.assertIsNone(
            manifest.pick(table, "ik", "arm_l", CHAR_B, sole=False))

    def test_kind_and_name_both_have_to_match(self):
        table = [R("RigPicker_build_arm_l", CHAR_A, "ik", "arm_l")]
        self.assertIsNone(manifest.pick(table, "fk", "arm_l", CHAR_A, False))
        self.assertIsNone(manifest.pick(table, "ik", "arm_r", CHAR_A, False))

    def test_tagged_beats_untagged_mid_migration(self):
        table = [R("RigPicker_fk_spine", "", "fk", "spine"),
                 R("RigPicker_fk_spine1", CHAR_A, "fk", "spine")]
        self.assertEqual(
            manifest.pick(table, "fk", "spine", CHAR_A, sole=True),
            "RigPicker_fk_spine1")

    def test_an_untagged_legacy_manifest_answers_when_alone(self):
        table = [R("RigPicker_fk_spine", "", "fk", "spine")]
        self.assertEqual(
            manifest.pick(table, "fk", "spine", CHAR_A, sole=True),
            "RigPicker_fk_spine")

    def test_an_untagged_manifest_stays_out_of_a_crowded_scene(self):
        table = [R("RigPicker_fk_spine", "", "fk", "spine")]
        self.assertIsNone(
            manifest.pick(table, "fk", "spine", CHAR_B, sole=False))

    def test_an_empty_scene_answers_none(self):
        self.assertIsNone(manifest.pick([], "ik", "arm_l", CHAR_A, True))


class Untagged(unittest.TestCase):

    def test_lists_only_the_manifests_carrying_no_tag(self):
        table = [R("a", "", "fk", "spine"),
                 R("b", CHAR_A, "fk", "neck"),
                 R("c", "", "ik", "arm_l")]
        self.assertEqual(manifest.untagged_names(table), ["a", "c"])

    def test_filters_by_kind(self):
        table = [R("a", "", "fk", "spine"), R("c", "", "ik", "arm_l")]
        self.assertEqual(manifest.untagged_names(table, "ik"), ["c"])


class Inside(unittest.TestCase):

    def test_the_separator_matters(self):
        """`|root_extra` is a different node, not a child of `|root`."""
        self.assertTrue(manifest.inside("|root|pelvis", "|root"))
        self.assertFalse(manifest.inside("|root_extra", "|root"))

    def test_a_node_is_inside_itself(self):
        self.assertTrue(manifest.inside("|root", "|root"))

    def test_nothing_is_inside_nothing(self):
        self.assertFalse(manifest.inside("", "|root"))
        self.assertFalse(manifest.inside("|root", ""))

    def test_members_inside_finds_one_hit(self):
        members = ["|other|thing", "|root|pelvis|pelvis_parentConstraint1"]
        self.assertTrue(manifest.members_inside(members, "|root"))

    def test_members_inside_is_false_for_another_character(self):
        members = ["|root1|pelvis|pelvis_parentConstraint1"]
        self.assertFalse(manifest.members_inside(members, "|root"))

    def test_no_members_is_no_hit(self):
        self.assertFalse(manifest.members_inside([], "|root"))
        self.assertFalse(manifest.members_inside(None, "|root"))


# ---------------------------------------------------------------------------
# scene, against a fake cmds
# ---------------------------------------------------------------------------

class FakeCmds(object):
    """Just enough Maya to exercise the manifest reads and writes."""

    def __init__(self, sets=None):
        # {set name: {attr: value}}
        self.sets_data = dict(sets or {})
        self.created = []

    def ls(self, *args, **kwargs):
        if kwargs.get("type") == "objectSet" and not args:
            return sorted(self.sets_data)
        return []

    def attributeQuery(self, attr, node=None, exists=False):
        return attr in self.sets_data.get(node, {})

    def getAttr(self, plug):
        node, _dot, attr = plug.partition(".")
        return self.sets_data.get(node, {}).get(attr, "")

    def addAttr(self, node, longName=None, dataType=None):
        self.sets_data.setdefault(node, {})[longName] = ""

    def setAttr(self, plug, value, type=None):
        node, _dot, attr = plug.partition(".")
        self.sets_data.setdefault(node, {})[attr] = value

    def sets(self, *args, **kwargs):
        name = kwargs.get("name")
        # Maya uniquifies; so does this.
        while name in self.sets_data:
            name += "1"
        self.sets_data[name] = {}
        self.created.append(name)
        return name


class FakeOverRig(object):
    def __init__(self, members=None):
        self.members = dict(members or {})

    def set_members(self, name):
        return self.members.get(name, [])


class FakeActive(object):
    def __init__(self, uuid=None, root=None, sole=True):
        self._uuid = uuid
        self._root = root
        self._sole = sole
        self.adopted = []

    def root_uuid(self):
        return self._uuid

    def root(self):
        return self._root

    def sole_character(self):
        return self._sole

    def adopt(self, scene_map):
        self.adopted.append(scene_map)
        return self._uuid


class SceneSide(unittest.TestCase):

    def setUp(self):
        self.real = (manifest.cmds, manifest.overrig, manifest.active)

    def tearDown(self):
        manifest.cmds, manifest.overrig, manifest.active = self.real

    def _use(self, cmds_fake, overrig_fake=None, active_fake=None):
        manifest.cmds = cmds_fake
        manifest.overrig = overrig_fake or FakeOverRig()
        manifest.active = active_fake or FakeActive(CHAR_A)

    def test_records_reads_the_tag_when_there_is_one(self):
        self._use(FakeCmds({"RigPicker_build_arm_l1": {
            manifest.ROOT_ATTR: CHAR_B,
            manifest.KIND_ATTR: "ik",
            manifest.NAME_ATTR: "arm_l"}}))
        self.assertEqual(manifest.records(),
                         [R("RigPicker_build_arm_l1", CHAR_B, "ik", "arm_l")])

    def test_records_falls_back_to_the_name_when_there_is_none(self):
        self._use(FakeCmds({"RigPicker_fk_spine": {}}))
        self.assertEqual(manifest.records(),
                         [R("RigPicker_fk_spine", "", "fk", "spine")])

    def test_records_ignores_sets_that_are_not_ours(self):
        self._use(FakeCmds({"OverRig_knots": {}, "RigPicker_fk_neck": {}}))
        self.assertEqual([r.set_name for r in manifest.records()],
                         ["RigPicker_fk_neck"])

    def test_find_scopes_to_the_active_character(self):
        self._use(FakeCmds({
            "RigPicker_build_arm_l": {manifest.ROOT_ATTR: CHAR_A,
                                      manifest.KIND_ATTR: "ik",
                                      manifest.NAME_ATTR: "arm_l"},
            "RigPicker_build_arm_l1": {manifest.ROOT_ATTR: CHAR_B,
                                       manifest.KIND_ATTR: "ik",
                                       manifest.NAME_ATTR: "arm_l"}}),
            active_fake=FakeActive(CHAR_B))
        self.assertEqual(manifest.find("ik", "arm_l"),
                         "RigPicker_build_arm_l1")

    def test_tag_writes_all_three_attributes(self):
        fake = FakeCmds({"RigPicker_fk_spine": {}})
        self._use(fake)
        manifest.tag("RigPicker_fk_spine", "fk", "spine", CHAR_A)
        self.assertEqual(fake.sets_data["RigPicker_fk_spine"],
                         {manifest.ROOT_ATTR: CHAR_A,
                          manifest.KIND_ATTR: "fk",
                          manifest.NAME_ATTR: "spine"})

    def test_ensure_creates_and_tags_when_there_is_nothing(self):
        fake = FakeCmds()
        self._use(fake)
        name = manifest.ensure("ik", "arm_l")
        self.assertEqual(name, "RigPicker_build_arm_l")
        self.assertEqual(fake.sets_data[name][manifest.ROOT_ATTR], CHAR_A)

    def test_ensure_returns_the_existing_one_instead_of_a_second(self):
        fake = FakeCmds({"RigPicker_build_arm_l": {
            manifest.ROOT_ATTR: CHAR_A,
            manifest.KIND_ATTR: "ik",
            manifest.NAME_ATTR: "arm_l"}})
        self._use(fake)
        self.assertEqual(manifest.ensure("ik", "arm_l"),
                         "RigPicker_build_arm_l")
        self.assertEqual(fake.created, [])

    def test_ensure_takes_the_uniquified_name_for_a_second_character(self):
        fake = FakeCmds({"RigPicker_build_arm_l": {
            manifest.ROOT_ATTR: CHAR_A,
            manifest.KIND_ATTR: "ik",
            manifest.NAME_ATTR: "arm_l"}})
        self._use(fake, active_fake=FakeActive(CHAR_B))
        name = manifest.ensure("ik", "arm_l")
        self.assertEqual(name, "RigPicker_build_arm_l1")
        self.assertEqual(fake.sets_data[name][manifest.ROOT_ATTR], CHAR_B)
        # ...and character A's is untouched.
        self.assertEqual(
            fake.sets_data["RigPicker_build_arm_l"][manifest.ROOT_ATTR],
            CHAR_A)

    def test_claim_tags_the_legacy_manifests_of_a_lone_character(self):
        fake = FakeCmds({"RigPicker_fk_spine": {},
                         "RigPicker_build_arm_l": {}})
        self._use(fake, active_fake=FakeActive(CHAR_A, "|root", sole=True))
        self.assertEqual(sorted(manifest.claim_untagged()),
                         ["RigPicker_build_arm_l", "RigPicker_fk_spine"])
        for name in fake.sets_data:
            self.assertEqual(fake.sets_data[name][manifest.ROOT_ATTR], CHAR_A)

    def test_claim_leaves_aims_alone(self):
        """An aim belongs to a weapon and already carries its own identity
        attributes; tagging it as a character's would be a lie."""
        fake = FakeCmds({"RigPicker_aim_LongSword_02": {}})
        self._use(fake, active_fake=FakeActive(CHAR_A, "|root", sole=True))
        self.assertEqual(manifest.claim_untagged(), [])

    def test_in_a_crowd_a_claim_needs_a_member_inside_the_character(self):
        fake = FakeCmds({"RigPicker_fk_spine": {},
                         "RigPicker_fk_neck": {}})
        overrig_fake = FakeOverRig({
            "RigPicker_fk_spine": ["|root|pelvis|spine_pc1"],
            "RigPicker_fk_neck": ["|root1|neck_01|neck_pc1"]})
        self._use(fake, overrig_fake,
                  FakeActive(CHAR_A, "|root", sole=False))
        self.assertEqual(manifest.claim_untagged(), ["RigPicker_fk_spine"])
        self.assertEqual(fake.sets_data["RigPicker_fk_neck"], {})

    def test_claim_does_nothing_without_an_active_character(self):
        fake = FakeCmds({"RigPicker_fk_spine": {}})
        self._use(fake, active_fake=FakeActive(None))
        self.assertEqual(manifest.claim_untagged(), [])

    def test_members_reads_through_the_resolved_set(self):
        fake = FakeCmds({"RigPicker_fk_spine1": {
            manifest.ROOT_ATTR: CHAR_A,
            manifest.KIND_ATTR: "fk",
            manifest.NAME_ATTR: "spine"}})
        self._use(fake, FakeOverRig({"RigPicker_fk_spine1": ["|a", "|b"]}))
        self.assertEqual(manifest.members("fk", "spine"), ["|a", "|b"])

    def test_members_of_a_character_with_nothing_built_is_empty(self):
        self._use(FakeCmds(), active_fake=FakeActive(CHAR_B))
        self.assertEqual(manifest.members("fk", "spine"), [])


if __name__ == "__main__":
    unittest.main()
