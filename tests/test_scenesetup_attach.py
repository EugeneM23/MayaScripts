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

from maya_scenesetup import attach  # noqa: E402

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


class GroupName(unittest.TestCase):
    """The fallback group, for a file that holds no single mesh."""

    def test_names_the_group_after_the_weapon(self):
        self.assertEqual(attach.group_name("LongSword_02"),
                         "LongSword_02_weapon")

    def test_the_old_name_is_gone(self):
        self.assertFalse(hasattr(attach, "carrier_name"))


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


class FakeMel(object):
    """The FBX plugin's option state, as maya.mel answers for it."""

    def __init__(self, mode="exmerge"):
        self.mode = mode
        self.commands = []

    def eval(self, command):
        self.commands.append(command)
        if command.strip() == "FBXImportMode -q":
            return self.mode
        if command.startswith("FBXImportMode -v"):
            self.mode = command.rsplit(None, 1)[-1]
        return None


class FakeImportCmds(object):
    """Enough of maya.cmds to watch what state the import runs in."""

    def __init__(self, mel, nodes=("|LongSwordMesh",), boom=False):
        self._mel = mel
        self._nodes = list(nodes)
        self._boom = boom
        self.mode_during_import = None

    def pluginInfo(self, name, query=False, loaded=False, **kwargs):
        return True

    def loadPlugin(self, name, quiet=False, **kwargs):
        return [name]

    def file(self, path, **kwargs):
        self.mode_during_import = self._mel.mode
        if self._boom:
            raise RuntimeError("import failed")
        return list(self._nodes)

    def ls(self, nodes, long=False, type=None, **kwargs):
        return list(nodes)


class ImportMode(unittest.TestCase):
    """The FBX import mode is global and outlives whoever set it.

    Measured 2026-08-17 in the user's session: maya_uebridge leaves the plugin
    on `exmerge`, where the importer matches names against the scene and
    creates NOTHING. cmds.file then returns an empty list and Add reports
    "nothing came out of ...". The mode must be set for every import, never
    inherited.
    """

    def setUp(self):
        self.mel = FakeMel("exmerge")
        self.cmds = FakeImportCmds(self.mel)
        attach.mel = self.mel
        attach.cmds = self.cmds

    def test_the_import_runs_in_add_mode(self):
        attach.import_model("C:/x/sword.fbx")
        self.assertEqual(self.cmds.mode_during_import, "add")

    def test_the_previous_mode_is_put_back(self):
        """The bridge sets its own mode on every import, but leaving another
        tool's session state rearranged is not ours to do."""
        attach.import_model("C:/x/sword.fbx")
        self.assertEqual(self.mel.mode, "exmerge")

    def test_the_mode_is_put_back_when_the_import_blows_up(self):
        self.cmds = FakeImportCmds(self.mel, boom=True)
        attach.cmds = self.cmds
        with self.assertRaises(RuntimeError):
            attach.import_model("C:/x/sword.fbx")
        self.assertEqual(self.mel.mode, "exmerge")

    def test_returns_what_arrived(self):
        self.assertEqual(attach.import_model("C:/x/sword.fbx"),
                         ["|LongSwordMesh"])


class FakeModel(object):
    """A node holding an imported model and, later, hung controls.

    `with_mesh` answers "has a mesh somewhere below", `direct_mesh` answers
    "holds a mesh shape itself" -- the two questions model_root asks, in that
    order, and the distinction is the whole point since the marked node is
    now the geometry.
    """

    def __init__(self, children, with_mesh, direct_mesh=()):
        self._children = dict(children)
        self._with_mesh = set(with_mesh)
        self._direct_mesh = set(direct_mesh)

    def listRelatives(self, node, children=False, allDescendents=False,
                      type=None, fullPath=False, **kwargs):
        if allDescendents and type == "mesh":
            return ["shape"] if node in self._with_mesh else None
        if allDescendents and type == "transform":
            return self._descendants(node) or None
        if children and type == "mesh":
            return ["shape"] if node in self._direct_mesh else None
        if children:
            return list(self._children.get(node, [])) or None
        return None

    def _descendants(self, node):
        found = []
        frontier = list(self._children.get(node, []))
        while frontier:
            child = frontier.pop(0)
            found.append(child)
            frontier.extend(self._children.get(child, []))
        return found


class ModelRoot(unittest.TestCase):
    """What rides the weapon must ride the GEOMETRY, not the offset group.

    Measured 2026-08-17: with the IK hand controls hung on the carrier they
    were siblings of the mesh, so dragging the sword in the viewport moved it
    32.840 and the hands 0.000 -- the sword came out of the hands.
    """

    def test_finds_the_imported_model(self):
        attach.cmds = FakeModel(
            {"|weapon": ["|weapon|LongSwordMesh", "|weapon|hand_l_IK_feet"]},
            with_mesh=["|weapon|LongSwordMesh"])
        self.assertEqual(attach.model_root("|weapon"),
                         "|weapon|LongSwordMesh")

    def test_ignores_the_controls_already_hung_on_it(self):
        """A locator has a shape too; only a mesh below counts as the model."""
        attach.cmds = FakeModel(
            {"|weapon": ["|weapon|hand_l_IK_feet", "|weapon|LongSwordMesh"]},
            with_mesh=["|weapon|LongSwordMesh"])
        self.assertEqual(attach.model_root("|weapon"),
                         "|weapon|LongSwordMesh")

    def test_falls_back_to_the_carrier_when_nothing_holds_a_mesh(self):
        attach.cmds = FakeModel({"|weapon": ["|weapon|locator1"]},
                                with_mesh=[])
        self.assertEqual(attach.model_root("|weapon"), "|weapon")

    def test_falls_back_on_an_empty_carrier(self):
        attach.cmds = FakeModel({}, with_mesh=[])
        self.assertEqual(attach.model_root("|weapon"), "|weapon")

    def test_takes_the_first_of_several_model_parts(self):
        attach.cmds = FakeModel(
            {"|weapon": ["|weapon|blade", "|weapon|scabbard"]},
            with_mesh=["|weapon|blade", "|weapon|scabbard"])
        self.assertEqual(attach.model_root("|weapon"), "|weapon|blade")

    def test_a_marked_mesh_transform_answers_itself(self):
        """With no group the marked node IS the geometry, and a mesh the
        animator parented under it must not outrank the weapon itself."""
        attach.cmds = FakeModel(
            {"|Sword": ["|Sword|somebodyElse"]},
            with_mesh=["|Sword", "|Sword|somebodyElse"],
            direct_mesh=["|Sword"])
        self.assertEqual(attach.model_root("|Sword"), "|Sword")


class MeshTransforms(unittest.TestCase):
    """Which of the imported transforms hold geometry -- the decision that
    says whether Add needs a group at all."""

    def test_finds_the_one_transform_holding_a_mesh(self):
        attach.cmds = FakeModel({}, with_mesh=[], direct_mesh=["|Sword"])
        self.assertEqual(attach.mesh_transforms(["|Sword", "|null1"]),
                         ["|Sword"])

    def test_looks_below_a_wrapper_null(self):
        """An exporter that wraps the mesh in a null IS the group the animator
        is trying to be rid of, so the mesh under it still counts."""
        attach.cmds = FakeModel({"|null1": ["|null1|Sword"]}, with_mesh=[],
                                direct_mesh=["|null1|Sword"])
        self.assertEqual(attach.mesh_transforms(["|null1"]), ["|null1|Sword"])

    def test_two_meshes_are_both_reported(self):
        attach.cmds = FakeModel({}, with_mesh=[],
                                direct_mesh=["|blade", "|guard"])
        self.assertEqual(attach.mesh_transforms(["|blade", "|guard"]),
                         ["|blade", "|guard"])

    def test_nothing_when_no_mesh_arrived(self):
        attach.cmds = FakeModel({}, with_mesh=[], direct_mesh=[])
        self.assertEqual(attach.mesh_transforms(["|locator1"]), [])

    def test_a_mesh_is_never_reported_twice(self):
        """The roots can overlap after an import; the answer may not."""
        attach.cmds = FakeModel({"|null1": ["|null1|Sword"]}, with_mesh=[],
                                direct_mesh=["|null1|Sword"])
        self.assertEqual(attach.mesh_transforms(["|null1", "|null1|Sword"]),
                         ["|null1|Sword"])


class FakeCurves(object):
    """maya.cmds enough to answer what carries an animation curve."""

    def __init__(self, curves):
        self._curves = dict(curves)

    def listConnections(self, plug, source=False, destination=False,
                        type=None, **kwargs):
        return list(self._curves.get(plug, [])) or None


class IsAnimated(unittest.TestCase):
    """Once the weapon has been out in the world its channels carry curves.

    setAttr on a connected channel raises, so the window has to ask before it
    writes -- a traceback on the status line reads like a broken tool.
    """

    def test_true_when_a_channel_carries_a_curve(self):
        attach.cmds = FakeCurves({"|c.rotateY": ["curve1"]})
        self.assertTrue(attach.is_animated("|c"))

    def test_true_for_a_translate_channel_too(self):
        attach.cmds = FakeCurves({"|c.translateX": ["curve2"]})
        self.assertTrue(attach.is_animated("|c"))

    def test_false_on_a_clean_node(self):
        attach.cmds = FakeCurves({})
        self.assertFalse(attach.is_animated("|c"))

    def test_false_for_nothing(self):
        attach.cmds = FakeCurves({})
        self.assertFalse(attach.is_animated(None))


class Seat(unittest.TestCase):
    """Zeroing translate and rotate does NOT put a node on its parent.

    Measured 2026-08-17 in the Manny scene: `cmds.group` puts the group's
    pivot at the bounding-box centre of what it holds (42.4 up the sword), and
    `cmds.parent` compensates for that pivot in `rotatePivotTranslate`. The
    carrier then reads translate 0, rotate 0 -- and hangs 28.5 cm off the
    bone. Every channel that can hold an offset has to go.
    """

    def setUp(self):
        self.fake = FakeCmds()
        attach.cmds = self.fake

    def test_zeroes_every_channel_that_can_hold_an_offset(self):
        attach.seat("|c", 1.0)
        for channel in ("translate", "rotate", "shear", "rotatePivot",
                        "rotatePivotTranslate", "scalePivot",
                        "scalePivotTranslate", "rotateAxis"):
            self.assertEqual(self.fake.attrs["|c." + channel],
                             (0.0, 0.0, 0.0), channel)

    def test_applies_the_entry_scale(self):
        attach.seat("|c", 0.5)
        self.assertEqual(self.fake.attrs["|c.scale"], (0.5, 0.5, 0.5))


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
