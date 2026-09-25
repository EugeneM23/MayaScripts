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
    """Let attach import without Maya. See CLAUDE.md on rebinding.

    Real modules win when they are importable -- under mayapy they always
    are, and attach reaches bonedrive, which needs maya.api.OpenMaya as
    well. Guarding on `"maya.cmds" in sys.modules` instead is not enough:
    run on its own, this module then installed a fake `maya` that is not a
    package and shadowed the real one.
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
    maya.api = api
    maya.cmds = cmds
    maya.mel = mel
    api.OpenMaya = openmaya
    sys.modules.setdefault("maya", maya)
    sys.modules["maya.api"] = api
    sys.modules["maya.api.OpenMaya"] = openmaya
    sys.modules["maya.cmds"] = cmds
    sys.modules["maya.mel"] = mel


_install_fake_maya()

from maya_scenesetup import attach  # noqa: E402
from maya_scenesetup import bonedrive  # noqa: E402

BONE = "|SKM_Manny|root|hand_r|weapon_r"
SPACE = "|WeaponSpaces|hand_r_weaponSpace"


class FakeWeaponSpace(object):
    """weaponspace as attach sees it (2026-09-24): one space per hand, made
    on demand, OUTSIDE the skeleton, pruned when it empties."""

    def __init__(self, space=None, log=None):
        self.space = space
        self.log = log if log is not None else []

    def space_of(self, hand):
        return self.space

    def ensure_space(self, hand):
        self.log.append(("space", hand))
        self.space = self.space or SPACE
        return self.space

    def prune(self, space):
        self.log.append(("prune", space))
        return True


class SpaceSwap(object):
    """Every test here runs against a FakeWeaponSpace unless it wires its own."""

    def setUp(self):
        self.real_weaponspace = attach.weaponspace
        attach.weaponspace = FakeWeaponSpace()
        self.addCleanup(self._restore_space)

    def _restore_space(self):
        attach.weaponspace = self.real_weaponspace


class FakeCmds(object):
    """Enough of maya.cmds for the child walk and the attribute writes."""

    def __init__(self, children=(), marked=(), parents=None):
        self._children = list(children)
        self._marked = set(marked)
        self._parents = dict(parents or {})
        self.attrs = {}
        self.deleted = []
        self.autokey = True
        self.autokey_during_write = []

    def listRelatives(self, node, children=False, parent=False, type=None,
                      fullPath=False, **kwargs):
        if parent:
            found = self._parents.get(node)
            return [found] if found else None
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


class FindAttached(SpaceSwap, unittest.TestCase):

    def test_finds_the_marked_child_in_the_hands_space(self):
        """Since 2026-09-24 the weapon lives in the space that follows the
        hand, outside the skeleton."""
        attach.cmds = FakeCmds(children=[SPACE + "|sword"], marked=[SPACE + "|sword"])
        attach.weaponspace = FakeWeaponSpace(space=SPACE)
        self.assertEqual(attach.find_attached(HAND), SPACE + "|sword")

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

    def test_remove_attached_is_gone(self):
        """It deleted without giving the bone its animation back; `detach`
        is the removal now."""
        self.assertFalse(hasattr(attach, "remove_attached"))


HAND = "|SKM_Manny|root|hand_r"


class FakeBonedrive(object):
    """Records unlink calls in a log shared with FakeCmds.deleted-style
    assertions: the ORDER of unlink against delete is the design."""

    MARKER = bonedrive.MARKER

    def __init__(self, log):
        self.log = log

    def unlink(self, bone):
        self.log.append(("unlink", bone))
        return None

    def snap(self, node, target):
        self.log.append(("snap", node, target))

    def store_frame(self, weapon, rotate):
        self.log.append(("frame", weapon, tuple(rotate)))

    def place_at_grip(self, weapon, bone, rotate, translate):
        self.log.append(("place", weapon, bone, rotate, translate))

    def apply_grip(self, weapon, bone, rotate, translate):
        self.log.append(("grip", weapon, bone, rotate, translate))

    def link(self, weapon, bone):
        self.log.append(("link", weapon, bone))
        return 0


class Marker(unittest.TestCase):

    def test_the_marker_is_bonedrives(self):
        """One string, defined in the leaf module, re-exported here so
        every existing attach.MARKER reader keeps working."""
        self.assertEqual(attach.MARKER, bonedrive.MARKER)
        self.assertEqual(attach.MARKER, "mayaWeapon")


class ParentBone(unittest.TestCase):

    def test_answers_the_dag_parent(self):
        attach.cmds = FakeCmds(parents={BONE: HAND})
        self.assertEqual(attach.parent_bone(BONE), HAND)

    def test_none_for_a_parentless_bone(self):
        attach.cmds = FakeCmds()
        self.assertIsNone(attach.parent_bone(BONE))


class Detach(SpaceSwap, unittest.TestCase):

    def test_a_weapon_in_the_space_comes_off_and_the_empty_space_goes(self):
        fake = FakeCmds(children=[SPACE + "|sword"], marked=[SPACE + "|sword"])
        log = self._wire(fake)
        attach.weaponspace = FakeWeaponSpace(space=SPACE, log=log)
        removed = attach.detach(HAND, BONE)
        self.assertEqual(removed, SPACE + "|sword")
        self.assertEqual(log, [("unlink", BONE), ("delete", SPACE + "|sword"), ("prune", SPACE)])

    def _wire(self, fake):
        attach.cmds = fake
        log = []
        fake_drive = FakeBonedrive(log)
        real_delete = fake.delete

        def logged_delete(node):
            log.append(("delete", node))
            real_delete(node)
        fake.delete = logged_delete
        self.real_bonedrive = attach.bonedrive
        attach.bonedrive = fake_drive
        self.addCleanup(self._unwire)
        return log

    def _unwire(self):
        attach.bonedrive = self.real_bonedrive

    def test_unlinks_before_deleting(self):
        """The bone's animation lives on the weapon while the link stands;
        deleting first would take it away (the camera's paid-for order)."""
        fake = FakeCmds(children=[HAND + "|sword"], marked=[HAND + "|sword"])
        log = self._wire(fake)
        removed = attach.detach(HAND, BONE)
        self.assertEqual(removed, HAND + "|sword")
        self.assertEqual(log, [("unlink", BONE),
                               ("delete", HAND + "|sword")])

    def test_looks_under_the_hand_first_and_the_bone_second(self):
        """A file attached by the old version keeps its sword under
        weapon_r; it is still found and still comes off."""
        fake = FakeCmds(children=[BONE + "|oldSword"],
                        marked=[BONE + "|oldSword"])
        log = self._wire(fake)
        removed = attach.detach(HAND, BONE)
        self.assertEqual(removed, BONE + "|oldSword")
        self.assertEqual(log[0], ("unlink", BONE))

    def test_nothing_attached_means_nothing_touched(self):
        fake = FakeCmds()
        log = self._wire(fake)
        self.assertIsNone(attach.detach(HAND, BONE))
        self.assertEqual(log, [])


class FakeColouring(object):
    """The colour module as attach sees it: a free colour and a painter.

    Stubbed rather than exercised -- what this class of test is about is the
    ORDER of attach's steps. The colour's own decisions are pinned in
    test_scenesetup_colour.py and proved live in verify_scenesetup_colour.py.
    """

    FREE = (0.80, 0.25, 0.22)

    def __init__(self, log):
        self.log = log

    def free_colour(self):
        class _Entry(object):
            name = "red"
            rgb = FakeColouring.FREE
        return _Entry()

    def paint_nodes(self, nodes, rgb, key):
        self.log.append(("paint", list(nodes), tuple(rgb), key))
        return "skeldarColour_red"


class AttachFlow(SpaceSwap, unittest.TestCase):
    """attach() ordering, with the import and the scene both faked.

    What is under test is the design's order: parent, mark, seat, snap onto
    the drive bone, link, and the grip only when nothing was transferred.
    The real import needs a live Maya and stays in verify_weapons.py.
    """

    class Entry(object):
        path = "C:/x/sword.fbx"
        key = "sword"
        scale = 1.0

    class FlowCmds(FakeCmds):

        def __init__(self):
            FakeCmds.__init__(self)
            self.log = []
            self.existing = {"|sword"}

        def undoInfo(self, **kwargs):
            pass

        def parent(self, node, target):
            new = "{0}|{1}".format(target, str(node).rsplit("|", 1)[-1])
            self.existing.discard(node)
            self.existing.add(new)
            self.log.append(("parent", node, target))
            return [new]

        def ls(self, nodes=None, **kwargs):
            listed = nodes if isinstance(nodes, (list, tuple)) else [nodes]
            return [n for n in listed if n]

        def objExists(self, node):
            return node in self.existing

        def addAttr(self, node, **kwargs):
            self.log.append(("mark", node))

        def setAttr(self, plug, *values, **kwargs):
            self.log.append(("set", plug))
            FakeCmds.setAttr(self, plug, *values, **kwargs)

        def delete(self, node):
            self.log.append(("deleted", node))

    def _wire(self, frames):
        fake = self.FlowCmds()
        attach.cmds = fake
        self.real_bonedrive = attach.bonedrive
        self.real_import = attach.import_model
        self.real_meshes = attach.mesh_transforms
        self.real_colouring = attach.colouring
        drive = FakeBonedrive(fake.log)
        drive.link = lambda weapon, bone: (
            fake.log.append(("link", weapon, bone)) or frames)
        attach.bonedrive = drive
        attach.import_model = lambda path: ["|sword"]
        attach.mesh_transforms = lambda roots: ["|sword"]
        attach.colouring = FakeColouring(fake.log)
        attach.weaponspace = FakeWeaponSpace(log=fake.log)
        self.addCleanup(self._unwire)
        return fake

    def _unwire(self):
        attach.bonedrive = self.real_bonedrive
        attach.import_model = self.real_import
        attach.mesh_transforms = self.real_meshes
        attach.colouring = self.real_colouring

    def _kinds(self, fake):
        return [entry[0] for entry in fake.log]

    def test_parent_mark_frame_grip_then_link(self):
        """The grip lands BEFORE the link (2026-08-25): the transfer keeps
        the sword's offset from the bone (mo=True), so a dialled grip rides
        the clip. The placement is bonedrive.apply_grip - BONE-relative
        (the same day's space ruling: zeros mean exactly on weapon_r),
        never raw channels under the hand - and the model's own frame is
        on the node before it (2026-09-24), since the placement stands the
        node in it."""
        fake = self._wire(frames=0)
        weapon, note = attach.attach(self.Entry(), HAND, BONE,
                                     rotate=(1.0, 2.0, 3.0),
                                     translate=(4.0, 5.0, 6.0))
        self.assertEqual(weapon, SPACE + "|sword")
        kinds = self._kinds(fake)
        self.assertLess(kinds.index("parent"), kinds.index("mark"))
        self.assertLess(kinds.index("mark"), kinds.index("frame"))
        self.assertLess(kinds.index("frame"), kinds.index("grip"))
        self.assertLess(kinds.index("grip"), kinds.index("link"))
        self.assertEqual(fake.log[kinds.index("grip")],
                         ("grip", SPACE + "|sword", BONE,
                          (1.0, 2.0, 3.0), (4.0, 5.0, 6.0)))
        self.assertNotIn("snap", kinds)
        self.assertEqual(note, "")

    def test_the_entrys_frame_goes_on_the_node(self):
        """The catalog's frame (the Creep Sword's 45) is written on the
        marked node; an entry written without the column is the identity."""
        fake = self._wire(frames=0)
        attach.attach(self.Entry(), HAND, BONE)
        self.assertIn(("frame", SPACE + "|sword", (0.0, 0.0, 0.0)), fake.log)

    def test_a_framed_entry_writes_its_frame(self):
        class Framed(self.Entry):
            frame = (0.0, 45.0, 0.0)
        fake = self._wire(frames=0)
        attach.attach(Framed(), HAND, BONE)
        self.assertIn(("frame", SPACE + "|sword", (0.0, 45.0, 0.0)), fake.log)

    def test_the_weapon_is_never_parented_into_the_skeleton(self):
        """2026-09-24, «не нарушали иерархию нашего скелета»: the mesh goes into
        the hand's space, made before the parent; nothing is parented under
        the hand or any bone."""
        fake = self._wire(frames=0)
        attach.attach(self.Entry(), HAND, BONE)
        kinds = self._kinds(fake)
        self.assertEqual(fake.log[kinds.index("space")], ("space", HAND))
        self.assertLess(kinds.index("space"), kinds.index("parent"))
        targets = [entry[2] for entry in fake.log if entry[0] == "parent"]
        self.assertEqual(targets, [SPACE])

    def test_no_grip_given_means_stay_on_the_bone(self):
        """None is not zeros: zeros are a real grip (the sword exactly on
        the bone). With no grip the sword is placed at zero grip - on the
        bone in its own frame - and nothing is stored (apply_grip is never
        called)."""
        fake = self._wire(frames=0)
        attach.attach(self.Entry(), HAND, BONE)
        kinds = self._kinds(fake)
        self.assertNotIn("grip", kinds)
        self.assertEqual(fake.log[kinds.index("place")],
                         ("place", SPACE + "|sword", BONE,
                          (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)))
        self.assertLess(kinds.index("place"), kinds.index("link"))

    def test_the_grip_rides_a_transferred_bone(self):
        """The user's 2026-08-25 report: adding into an animated scene
        dropped the dialled grip entirely. The grip is placed before the
        link, and the transfer (mo=True) keeps it - so the saved offsets
        shape the sword whether or not the bone brought animation."""
        fake = self._wire(frames=31)
        _weapon, note = attach.attach(self.Entry(), HAND, BONE,
                                      rotate=(1.0, 2.0, 3.0),
                                      translate=(4.0, 5.0, 6.0))
        kinds = self._kinds(fake)
        self.assertIn("grip", kinds)
        self.assertLess(kinds.index("grip"), kinds.index("link"))
        self.assertIn("31", note)

    def test_the_weapon_is_painted_after_it_is_marked(self):
        """The colour lands on the weapon inside the chunk attach already
        opens, and after the mark: a half-undone Add must not leave geometry
        with a shader and no marker."""
        fake = self._wire(frames=0)
        attach.attach(self.Entry(), HAND, BONE)
        kinds = self._kinds(fake)
        self.assertIn("paint", kinds)
        self.assertLess(kinds.index("mark"), kinds.index("paint"))
        painted = fake.log[kinds.index("paint")]
        self.assertEqual(painted[1], [SPACE + "|sword"])
        self.assertEqual(painted[2], FakeColouring.FREE)
        self.assertEqual(painted[3], "sword")

    def test_a_given_colour_beats_the_palette(self):
        """None means the next free colour, which is what the button passes.
        An explicit one is honoured - that is the seam the verify script
        drives, and it must not be quietly overridden by a scan."""
        fake = self._wire(frames=0)
        attach.attach(self.Entry(), HAND, BONE, rgb=(0.1, 0.2, 0.3))
        painted = fake.log[self._kinds(fake).index("paint")]
        self.assertEqual(painted[2], (0.1, 0.2, 0.3))


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

    The guard itself moved to `fbximport` on 2026-09-01 (Add Character needs
    the identical thing for UE4_Mannequin.fbx) and is tested there. What is
    still attach's own is that it reports the OUTERMOST transforms.
    """

    def setUp(self):
        from maya_scenesetup import fbximport
        self.fbximport = fbximport
        self.real = (fbximport.cmds, fbximport.mel, attach.cmds)
        self.mel = FakeMel("exmerge")
        self.cmds = FakeImportCmds(self.mel)
        fbximport.mel = self.mel
        fbximport.cmds = self.cmds
        attach.cmds = self.cmds

    def tearDown(self):
        self.fbximport.cmds, self.fbximport.mel, attach.cmds = self.real

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
        self.fbximport.cmds = self.cmds
        attach.cmds = self.cmds
        with self.assertRaises(RuntimeError):
            attach.import_model("C:/x/sword.fbx")
        self.assertEqual(self.mel.mode, "exmerge")

    def test_returns_what_arrived(self):
        self.assertEqual(attach.import_model("C:/x/sword.fbx"),
                         ["|LongSwordMesh"])

    def test_only_the_outermost_transforms_are_reported(self):
        """attach's own half: a file arriving as a null holding the mesh
        must answer the null, not both."""
        self.cmds = FakeImportCmds(
            self.mel, nodes=("|grp", "|grp|LongSwordMesh"))
        self.fbximport.cmds = self.cmds
        attach.cmds = self.cmds
        self.assertEqual(attach.import_model("C:/x/sword.fbx"), ["|grp"])


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

    def test_the_raw_channel_utilities_are_gone(self):
        """write_offsets and read_offsets wrote and read plain channels
        under whatever the parent was. The grip is BONE-relative now and
        goes through bonedrive.apply_grip / measured_grip; keeping a raw
        write around is how the next reader applies a grip in the wrong
        space again."""
        self.assertFalse(hasattr(attach, "write_offsets"))
        self.assertFalse(hasattr(attach, "read_offsets"))
