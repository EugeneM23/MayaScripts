"""Tests for bonedrive: the bone that follows a marked node.

The pure half runs on real OpenMaya (mayapy ships it, as test_axes does).
The scene half is proved on a fake cmds that records CALL ORDER - the
orderings under test are the ones the camera setup already paid for:
bake before delete, cut before constrain.
"""

import math
import sys
import types
import unittest

import maya.api.OpenMaya as om


def _install_fake_maya():
    """Let bonedrive import without a full Maya. See CLAUDE.md on rebinding."""
    if "maya.cmds" in sys.modules:
        return
    maya = types.ModuleType("maya")
    cmds = types.ModuleType("maya.cmds")
    maya.cmds = cmds
    sys.modules.setdefault("maya", maya)
    sys.modules["maya.cmds"] = cmds


_install_fake_maya()

from maya_scenesetup import bonedrive  # noqa: E402


def _matrix(rx, ry, rz, tx, ty, tz):
    m = om.MTransformationMatrix()
    m.setRotation(om.MEulerRotation(math.radians(rx), math.radians(ry),
                                    math.radians(rz)))
    m.setTranslation(om.MVector(tx, ty, tz), om.MSpace.kTransform)
    return tuple(m.asMatrix())


class UnionRange(unittest.TestCase):
    """Trap 38 from the export side: a bake narrower than the keys silently
    truncates them, so every bake range is the union."""

    def test_keys_widen_the_playback_range(self):
        self.assertEqual(
            bonedrive.union_range(0.0, 30.0, [-20.0, 10.0, 45.0]),
            (-20.0, 45.0))

    def test_no_keys_keep_the_playback_range(self):
        self.assertEqual(bonedrive.union_range(0.0, 30.0, []), (0.0, 30.0))

    def test_keys_inside_change_nothing(self):
        self.assertEqual(bonedrive.union_range(0.0, 30.0, [5.0, 12.0]),
                         (0.0, 30.0))


class MatrixOf(unittest.TestCase):

    def test_identity_channels_make_the_identity(self):
        got = bonedrive.matrix_of((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
        want = tuple(om.MMatrix())
        self.assertLess(max(abs(a - b) for a, b in zip(got, want)), 1e-12)

    def test_matches_maya_channel_semantics(self):
        got = bonedrive.matrix_of((10.0, 20.0, 30.0), (1.0, 2.0, 3.0))
        want = _matrix(10.0, 20.0, 30.0, 1.0, 2.0, 3.0)
        self.assertLess(max(abs(a - b) for a, b in zip(got, want)), 1e-12)


class ComposedGrip(unittest.TestCase):
    """Old-scheme grip (channels under weapon_r) -> channels under the hand.

    The sword's world matrix must be identical in both schemes:
    matrix(new channels) == matrix(grip) * bone_local.
    """

    def test_grip_between_inverts_composed_grip(self):
        """The read-back: the grip measured between the composed frame and
        the bone frame is the grip that was composed in."""
        rotate, translate = (10.0, -20.0, 35.0), (1.0, 2.0, -3.0)
        bone = bonedrive.matrix_of((30.0, 40.0, -25.0), (5.0, -1.0, 2.0))
        placed = bonedrive.composed_grip(rotate, translate, bone)
        back_r, back_t = bonedrive.grip_between(
            bonedrive.matrix_of(placed[0], placed[1]), bone)
        self.assertLess(max(abs(a - b) for a, b in zip(back_r, rotate)), 1e-6)
        self.assertLess(max(abs(a - b) for a, b in zip(back_t, translate)),
                        1e-6)

    def test_grip_between_identity_frames_is_zero(self):
        identity = bonedrive.matrix_of((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
        rotate, translate = bonedrive.grip_between(identity, identity)
        self.assertLess(max(abs(v) for v in rotate + translate), 1e-9)

    def test_identity_bone_local_returns_the_grip(self):
        rotate, translate = bonedrive.composed_grip(
            (10.0, 20.0, 30.0), (1.0, 2.0, 3.0), _matrix(0, 0, 0, 0, 0, 0))
        for got, want in zip(tuple(rotate) + tuple(translate),
                             (10.0, 20.0, 30.0, 1.0, 2.0, 3.0)):
            self.assertAlmostEqual(got, want, places=9)

    def test_zero_grip_returns_the_bone_local(self):
        rotate, translate = bonedrive.composed_grip(
            (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), _matrix(90.0, 0, 0, 5.0, 0, 0))
        self.assertAlmostEqual(rotate[0], 90.0, places=9)
        self.assertAlmostEqual(rotate[1], 0.0, places=9)
        self.assertAlmostEqual(rotate[2], 0.0, places=9)
        self.assertAlmostEqual(translate[0], 5.0, places=9)

    def test_framed_is_the_frame_times_the_bone(self):
        bone = bonedrive.matrix_of((30.0, 40.0, -25.0), (5.0, -1.0, 2.0))
        got = om.MMatrix(bonedrive.framed((0.0, 45.0, 0.0), bone))
        want = (om.MMatrix(bonedrive.matrix_of((0.0, 45.0, 0.0), (0.0, 0.0, 0.0)))
                * om.MMatrix(bone))
        self.assertLess(max(abs(got[i] - want[i]) for i in range(16)), 1e-12)
        same = bonedrive.framed((0.0, 0.0, 0.0), bone)
        self.assertLess(max(abs(a - b) for a, b in zip(same, bone)), 1e-12)

    def test_unframing_undoes_the_frame_in_every_rotate_order(self):
        """The target offset that puts a bone on the socket of a framed
        weapon: O = frame^-1, as an euler in the BONE's rotate order (a
        constraint reads its offset in the constrained node's order)."""
        frame = (12.0, 45.0, -30.0)
        want = om.MMatrix(bonedrive.matrix_of(frame, (0.0, 0.0, 0.0))).inverse()
        for order in range(6):
            euler = om.MEulerRotation(
                *[math.radians(v) for v in bonedrive.unframing(frame, order)],
                order=order)
            got = euler.asMatrix()
            self.assertLess(max(abs(got[i] - want[i]) for i in range(16)), 1e-9, order)
        self.assertLess(max(abs(v) for v in bonedrive.unframing((0.0, 0.0, 0.0))), 1e-12)

    def test_composition_matches_the_matrix_product(self):
        grip_rotate = (10.0, -35.0, 4.0)
        grip_translate = (0.5, -2.0, 12.0)
        bone_local = _matrix(25.0, 80.0, -5.0, 3.0, 4.0, -1.0)
        rotate, translate = bonedrive.composed_grip(
            grip_rotate, grip_translate, bone_local)
        want = (om.MMatrix(bonedrive.matrix_of(grip_rotate, grip_translate))
                * om.MMatrix(bone_local))
        got = om.MMatrix(bonedrive.matrix_of(rotate, translate))
        worst = max(abs(got[i] - want[i]) for i in range(16))
        self.assertLess(worst, 1e-9)


class FakeCmds(object):
    """Records the calls whose ORDER is the design.

    One weapon, one bone. `bone_keys` are the bone's key values (empty =
    no animation, constant = curves that never move); `bone_curves` says
    whether the transform channels carry animCurve connections at all.
    """

    def __init__(self, bone_keys=(), bone_curves=False,
                 weapon="|hand|sword", constrained=False,
                 marked=("|hand|sword",), grip=None):
        self.log = []
        self.autokey = True
        self.autokey_during = []
        self._bone_keys = list(bone_keys)
        self._bone_curves = bone_curves
        self._weapon = weapon
        self._marked = set(marked)
        self._constraints = {}
        self.attrs = {}
        # Deliberately fractional: the offset capture must not trust it.
        self.now = 7.3
        self.times = []
        self.reads = []
        self.matrices = {}
        if grip:
            self.attrs[weapon + "." + bonedrive.GRIP_ROTATE] = tuple(grip[0])
            self.attrs[weapon + "." + bonedrive.GRIP_TRANSLATE] = tuple(grip[1])
        if constrained:
            self._constraints["|skel|weapon_r"] = "|skel|weapon_r|drive1"

    def _note(self, entry):
        self.log.append(entry)
        self.autokey_during.append(self.autokey)

    def playbackOptions(self, query=False, minTime=False, maxTime=False):
        return 0.0 if minTime else 30.0

    def keyframe(self, node, query=False, timeChange=False,
                 valueChange=False, **kwargs):
        if valueChange:
            return list(self._bone_keys)
        return [0.0, 30.0] if self._bone_keys else []

    def listRelatives(self, node, children=False, type=None, fullPath=False,
                      **kwargs):
        if type == "parentConstraint":
            found = self._constraints.get(node)
            return [found] if found else None
        if kwargs.get("parent"):
            #  the sword hangs under the hand joint (a hold - `is_held`,
            #  2026-09-29: a weapon out in world is relinked where it lies)
            parent = node.rsplit("|", 1)[0]
            return [parent] if parent else None
        return None

    def objectType(self, node, **kwargs):
        return "joint"

    def parentConstraint(self, *nodes, **kwargs):
        if kwargs.get("query"):
            return [self._weapon]
        self._note(("constrain", nodes, kwargs.get("maintainOffset", True)))
        name = nodes[-1] + "|constraint{0}".format(len(self.log))
        self._constraints[nodes[-1]] = name
        return [name]

    def ls(self, *args, **kwargs):
        if args and args[0]:
            listed = args[0] if isinstance(args[0], (list, tuple)) else [args[0]]
            return list(listed)
        return []

    def attributeQuery(self, name, node=None, exists=False, **kwargs):
        if name == bonedrive.MARKER:
            return node in self._marked
        return "{0}.{1}".format(node, name) in self.attrs

    def addAttr(self, node, longName=None, **kwargs):
        self._note(("addattr", node, longName))
        self.attrs.setdefault("{0}.{1}".format(node, longName), None)

    def setAttr(self, plug, *values, **kwargs):
        self._note(("set", plug))
        self.attrs[plug] = tuple(values)

    def getAttr(self, plug, **kwargs):
        if "time" in kwargs:
            # A keyed channel read off its curve at `time`: a value that
            # depends on the time asked for, so a test can tell a frame-0
            # read from a stale one.
            self.reads.append((plug, kwargs["time"]))
            return 100.0 + kwargs["time"]
        stored = self.attrs.get(plug)
        return [tuple(stored)] if stored else [(0.0, 0.0, 0.0)]

    def listConnections(self, plug, **kwargs):
        return ["someCurve"] if self._bone_curves else None

    def bakeResults(self, node, **kwargs):
        self._note(("bake", node, kwargs.get("time")))

    def cutKey(self, node, **kwargs):
        self._note(("cut", node, kwargs.get("attribute")))

    def delete(self, node):
        self._note(("delete", node))
        doomed = node if isinstance(node, (list, tuple)) else [node]
        for bone, constraint in list(self._constraints.items()):
            if constraint in doomed:
                del self._constraints[bone]

    def xform(self, node, **kwargs):
        if kwargs.get("query"):
            if kwargs.get("matrix"):
                return list(self.matrices.get(node, (
                    1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0,
                    0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0)))
            return (0.0, 0.0, 0.0)
        self._note(("xform", node, kwargs))

    def autoKeyframe(self, query=False, state=None):
        if query:
            return self.autokey
        self.autokey = state

    def currentTime(self, value=None, query=False):
        if query:
            return self.now
        self.times.append(value)
        self.now = value

    def objExists(self, node):
        return True


BONE = "|skel|weapon_r"
SWORD = "|hand|sword"


class WithFake(unittest.TestCase):

    def use(self, fake):
        self.fake = fake
        bonedrive.cmds = fake
        self.addCleanup(self._restore)
        return fake

    def _restore(self):
        bonedrive.cmds = sys.modules["maya.cmds"]

    def kinds(self):
        return [entry[0] for entry in self.fake.log]

    def phases(self):
        """Call kinds with consecutive repeats collapsed: `_cut` logs one
        entry per connected channel, and the ORDER is what is under test."""
        collapsed = []
        for kind in self.kinds():
            if not collapsed or collapsed[-1] != kind:
                collapsed.append(kind)
        return collapsed


class Link(WithFake):

    def test_moving_bone_transfers_then_inverts(self):
        """Temp constraint bone->weapon (mo=TRUE - the transfer keeps
        whatever offset the caller placed, which is the dialled grip;
        identity when the weapon stands on the bone), bake the WEAPON,
        delete the temp, cut the bone, constrain weapon->bone (mo=TRUE -
        the bone keeps playing ITS OWN track at the grip's inverse; the
        user's 2026-08-25 ruling: the grip is not the export's to carry) -
        in that order. The camera paid for cut-after-constrain (a
        pairBlend); the first grip fix paid for mo=False here shifting the
        bone by the grip."""
        fake = self.use(FakeCmds(bone_keys=[0.0, 25.0], bone_curves=True))
        frames = bonedrive.link(SWORD, BONE)
        self.assertEqual(self.phases(),
                         ["constrain", "bake", "delete", "cut", "set",
                          "constrain"])
        first = fake.log[0]
        self.assertEqual(first[1], (BONE, SWORD))
        self.assertIs(first[2], True)
        self.assertEqual(fake.log[1][1], SWORD)
        last = fake.log[-1]
        self.assertEqual(last[1], (SWORD, BONE))
        self.assertIs(last[2], True)
        self.assertEqual(frames, 31)

    def test_the_final_offset_is_captured_on_a_sampled_frame(self):
        """After the transfer the sword is a SAMPLED curve: capturing the
        offset at a fractional currentTime compares an interpolated sword
        against the bone's exact cut value, and the error rides every
        frame for ever. The capture jumps to the range start (always a
        sample) and puts the time back."""
        fake = self.use(FakeCmds(bone_keys=[0.0, 25.0], bone_curves=True))
        bonedrive.link(SWORD, BONE)
        self.assertEqual(fake.times, [0.0, 7.3])

    def test_the_bone_is_settled_on_the_capture_frame_before_the_capture(self):
        """`cutKey` leaves a channel at whatever the DG last EVALUATED, and a
        session with no viewport pulling the joint evaluates nothing on a
        bare currentTime -- measured in mayapy 2026-09-07: the bone kept
        its frame-24 values through a cut "at frame 0" and rode the sword
        0.319 cm off for the whole take. So the frame-start values are read
        off the curves before the cut and written back after it, before the
        constraint captures its offset."""
        fake = self.use(FakeCmds(bone_keys=[0.0, 25.0], bone_curves=True))
        bonedrive.link(SWORD, BONE)
        # Read at the range START, one per transform channel.
        self.assertEqual(fake.reads,
                         [("{0}.{1}".format(BONE, ch), 0.0)
                          for ch in bonedrive.CHANNELS])
        kinds = self.kinds()
        cut, constrain = kinds.index("cut"), len(kinds) - 1
        sets = [i for i, k in enumerate(kinds) if k == "set"]
        self.assertEqual(len(sets), 6)
        self.assertTrue(all(cut < i < constrain for i in sets))
        # ... and what is written back is the frame-0 value, not `now`.
        self.assertEqual(fake.attrs[BONE + ".translateX"], (100.0,))

    def test_no_transfer_means_no_time_jump(self):
        """A static sword evaluates exactly at any time - the animator's
        cursor is not touched without a reason."""
        fake = self.use(FakeCmds(bone_keys=[], bone_curves=False))
        bonedrive.link(SWORD, BONE)
        self.assertEqual(fake.times, [])

    def test_still_bone_gets_no_transfer_and_reports_zero(self):
        """Constant curves are not animation (trap 30) - transferring them
        would key the weapon's channels and mute the grip fields."""
        fake = self.use(FakeCmds(bone_keys=[5.0, 5.0], bone_curves=True))
        frames = bonedrive.link(SWORD, BONE)
        self.assertEqual(frames, 0)
        self.assertNotIn("bake", self.kinds())
        self.assertEqual(self.kinds().count("constrain"), 1)
        self.assertIn("cut", self.kinds())

    def test_clean_bone_is_not_cut(self):
        fake = self.use(FakeCmds(bone_keys=[], bone_curves=False))
        bonedrive.link(SWORD, BONE)
        self.assertEqual(self.kinds(), ["constrain"])

    def test_autokey_is_off_for_every_write_and_restored(self):
        fake = self.use(FakeCmds(bone_keys=[0.0, 25.0], bone_curves=True))
        bonedrive.link(SWORD, BONE)
        self.assertTrue(all(state is False for state in fake.autokey_during))
        self.assertTrue(fake.autokey)

    def test_bake_range_is_the_union_of_playback_and_keys(self):
        """The clip runs -20..45 while playback shows 0..30: baking the
        playback range would truncate the transfer (trap 38)."""
        fake = self.use(FakeCmds(bone_keys=[0.0, 25.0], bone_curves=True))
        fake.keyframe = lambda node, **kw: ([0.0, 25.0] if kw.get("valueChange")
                                            else [-20.0, 45.0])
        bonedrive.link(SWORD, BONE)
        self.assertEqual(fake.log[1][2], (-20.0, 45.0))


class Unlink(WithFake):

    def test_bakes_the_bone_before_deleting_the_constraint(self):
        """The animation lives on the weapon while the link stands; the
        other order is the camera's paid-for bug."""
        fake = self.use(FakeCmds(constrained=True))
        weapon = bonedrive.unlink(BONE)
        self.assertEqual(weapon, SWORD)
        self.assertEqual(self.kinds(), ["bake", "delete"])
        self.assertEqual(fake.log[0][1], BONE)

    def test_nothing_of_ours_means_no_touch(self):
        fake = self.use(FakeCmds(constrained=False))
        self.assertIsNone(bonedrive.unlink(BONE))
        self.assertEqual(fake.log, [])

    def test_a_foreign_constraint_is_not_ours(self):
        """A constraint whose driver carries no marker is somebody else's
        rig - never bake over it, never delete it."""
        fake = self.use(FakeCmds(constrained=True, marked=()))
        self.assertIsNone(bonedrive.unlink(BONE))
        self.assertEqual(fake.log, [])


class Relink(WithFake):

    def test_cuts_the_weapon_snaps_then_links(self):
        """The weapon's curves are stale by definition after a merge - the
        merge's contract is 'the scene plays this clip'. Cuts (one per
        connected channel) target the WEAPON and come before the snap,
        which comes before any constraint."""
        fake = self.use(FakeCmds(bone_keys=[0.0, 25.0], bone_curves=True))
        frames = bonedrive.relink(SWORD, BONE)
        kinds = self.kinds()
        first_xform = kinds.index("xform")
        self.assertGreater(first_xform, 0)
        for entry in fake.log[:first_xform]:
            self.assertEqual(entry[0], "cut")
            self.assertEqual(entry[1], SWORD)
        self.assertEqual(kinds[first_xform:first_xform + 2],
                         ["xform", "xform"])
        self.assertLess(first_xform, kinds.index("constrain"))
        self.assertEqual(frames, 31)

    def test_a_clip_without_weapon_keys_still_relinks(self):
        """The bone was cleared and got nothing: the weapon snaps onto its
        cleared pose and the constraint is rebuilt with no transfer."""
        fake = self.use(FakeCmds(bone_keys=[], bone_curves=True))
        frames = bonedrive.relink(SWORD, BONE)
        self.assertEqual(frames, 0)
        self.assertNotIn("bake", self.kinds())
        self.assertEqual(self.kinds().count("constrain"), 1)

    def _placed(self):
        """The last placement's world (translation, rotation)."""
        writes = [entry[2] for entry in self.fake.log if entry[0] == "xform"]
        translation = [w["translation"] for w in writes if "translation" in w][-1]
        rotation = [w["rotation"] for w in writes if "rotation" in w][-1]
        return tuple(translation), tuple(rotation)

    def test_a_stored_grip_is_reapplied_before_the_link(self):
        """A merge's contract is 'the scene plays this clip', but the GRIP
        is not the clip's to flatten: the sword goes back to its dialled
        pose relative to the bone, and the transfer keeps that offset. One
        placement (two writes), before any constraint."""
        fake = self.use(FakeCmds(bone_keys=[0.0, 25.0], bone_curves=True,
                                 grip=((10.0, 0.0, 0.0), (0.0, 5.0, 0.0))))
        bonedrive.relink(SWORD, BONE)
        kinds = self.kinds()
        placements = [i for i, kind in enumerate(kinds) if kind == "xform"]
        self.assertEqual(len(placements), 2)
        self.assertLess(placements[-1], kinds.index("constrain"))
        translation, rotation = self._placed()
        self.assertAlmostEqual(translation[1], 5.0, places=9)
        self.assertAlmostEqual(rotation[0], 10.0, places=9)

    def test_no_stored_grip_means_onto_the_bone(self):
        """A legacy sword (attached before the grip lived on the node)
        relinks exactly as before: onto the bone, nothing more."""
        fake = self.use(FakeCmds(bone_keys=[0.0, 25.0], bone_curves=True))
        fake.matrices[BONE] = bonedrive.matrix_of((0.0, 0.0, 30.0), (1.0, 2.0, 3.0))
        bonedrive.relink(SWORD, BONE)
        self.assertEqual(self.kinds().count("xform"), 2)
        translation, rotation = self._placed()
        self.assertLess(max(abs(a - b) for a, b in zip(translation, (1.0, 2.0, 3.0))), 1e-9)
        self.assertLess(max(abs(a - b) for a, b in zip(rotation, (0.0, 0.0, 30.0))), 1e-9)

    def test_a_framed_weapon_with_no_grip_relinks_into_its_frame(self):
        """The Creep Sword's 45 is its FRAME: zero grip stands it turned on
        the bone, so a relink with nothing stored lands it there too."""
        fake = self.use(FakeCmds(bone_keys=[0.0, 25.0], bone_curves=True))
        fake.attrs[SWORD + "." + bonedrive.FRAME_ROTATE] = (0.0, 45.0, 0.0)
        bonedrive.relink(SWORD, BONE)
        _translation, rotation = self._placed()
        self.assertLess(max(abs(a - b) for a, b in zip(rotation, (0.0, 45.0, 0.0))), 1e-9)


class Frame(WithFake):
    """The weapon's own frame on its bone (2026-09-24): stored on the node,
    composed under every grip, removed from every read-back."""

    def test_the_identity_writes_nothing_on_a_node_that_has_none(self):
        self.use(FakeCmds())
        bonedrive.store_frame(SWORD, (0.0, 0.0, 0.0))
        self.assertEqual(self.kinds(), [])
        self.assertEqual(bonedrive.frame_of(SWORD), (0.0, 0.0, 0.0))

    def test_round_trips(self):
        self.use(FakeCmds())
        bonedrive.store_frame(SWORD, (0.0, 45.0, 0.0))
        self.assertEqual(bonedrive.frame_of(SWORD), (0.0, 45.0, 0.0))
        bonedrive.store_frame(SWORD, (0.0, 0.0, 0.0))
        self.assertEqual(bonedrive.frame_of(SWORD), (0.0, 0.0, 0.0))
        self.assertEqual(self.kinds().count("addattr"), 1)

    def test_zero_grip_stands_the_weapon_in_its_frame_on_the_bone(self):
        fake = self.use(FakeCmds())
        bone = bonedrive.matrix_of((10.0, 20.0, 30.0), (1.0, 2.0, 3.0))
        fake.matrices[BONE] = bone
        fake.attrs[SWORD + "." + bonedrive.FRAME_ROTATE] = (0.0, 45.0, 0.0)
        bonedrive.place_at_grip(SWORD, BONE, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
        writes = [entry[2] for entry in fake.log if entry[0] == "xform"]
        placed = bonedrive.matrix_of(writes[1]["rotation"], writes[0]["translation"])
        want = bonedrive.framed((0.0, 45.0, 0.0), bone)
        self.assertLess(max(abs(a - b) for a, b in zip(placed, want)), 1e-9)

    def test_the_read_back_takes_the_frame_away(self):
        """A framed sword standing where zero grip puts it reads 0 0 0 --
        the fields show the grip, never the model's own turn."""
        fake = self.use(FakeCmds())
        bone = bonedrive.matrix_of((10.0, 20.0, 30.0), (1.0, 2.0, 3.0))
        fake.matrices[BONE] = bone
        grip = om.MMatrix(bonedrive.matrix_of((5.0, 0.0, 0.0), (0.0, 7.0, 0.0)))
        fake.matrices[SWORD] = tuple(
            grip * om.MMatrix(bonedrive.framed((0.0, 45.0, 0.0), bone)))
        fake.attrs[SWORD + "." + bonedrive.FRAME_ROTATE] = (0.0, 45.0, 0.0)
        rotate, translate = bonedrive.measured_grip(SWORD, BONE)
        self.assertLess(max(abs(a - b) for a, b in zip(rotate, (5.0, 0.0, 0.0))), 1e-9)
        self.assertLess(max(abs(a - b) for a, b in zip(translate, (0.0, 7.0, 0.0))), 1e-9)


class Regrip(WithFake):
    """A new grip moves the SWORD only, placed relative to the BONE (the
    user's 2026-08-25 space ruling: zeros mean exactly on weapon_r). The
    bone plays its own animation through the constraint's captured offset,
    so placing the sword under a live constraint would drag the bone along
    by the OLD offset - the constraint is dropped (the bone freezes where
    it stands), the sword placed, and the constraint remade capturing the
    new offset. The bone never moves."""

    def test_drops_places_and_remakes_around_our_constraint(self):
        fake = self.use(FakeCmds(constrained=True))
        bonedrive.regrip(SWORD, BONE, (1.0, 2.0, 3.0), (4.0, 5.0, 6.0))
        kinds = self.kinds()
        self.assertEqual(kinds.count("delete"), 1)
        self.assertEqual(kinds.count("constrain"), 1)
        placements = [i for i, kind in enumerate(kinds) if kind == "xform"]
        self.assertEqual(len(placements), 2)
        self.assertLess(kinds.index("delete"), placements[0])
        self.assertLess(placements[-1], kinds.index("constrain"))
        last = fake.log[-1]
        self.assertEqual(last[1], (SWORD, BONE))
        self.assertIs(last[2], True)

    def test_an_unconstrained_bone_gets_a_plain_placement(self):
        """A legacy sword (old file, no inverted drive) still takes its
        offsets; there is nothing to rehook."""
        fake = self.use(FakeCmds(constrained=False))
        bonedrive.regrip(SWORD, BONE, (1.0, 0.0, 0.0), (0.0, 0.0, 0.0))
        self.assertNotIn("delete", self.kinds())
        self.assertNotIn("constrain", self.kinds())
        self.assertEqual(self.kinds().count("xform"), 2)

    def test_a_foreign_constraint_is_left_standing(self):
        """A constraint whose driver carries no marker is somebody else's
        rig - place the sword, touch nothing on the bone."""
        fake = self.use(FakeCmds(constrained=True, marked=()))
        bonedrive.regrip(SWORD, BONE, (1.0, 0.0, 0.0), (0.0, 0.0, 0.0))
        self.assertNotIn("delete", self.kinds())
        self.assertNotIn("constrain", self.kinds())

    def test_stores_the_grip_on_a_marked_weapon(self):
        fake = self.use(FakeCmds(constrained=True))
        bonedrive.regrip(SWORD, BONE, (1.0, 2.0, 3.0), (4.0, 5.0, 6.0))
        self.assertEqual(bonedrive.stored_grip(SWORD),
                         ((1.0, 2.0, 3.0), (4.0, 5.0, 6.0)))

    def test_an_unmarked_node_stores_no_grip(self):
        fake = self.use(FakeCmds(constrained=True, marked=()))
        bonedrive.regrip(SWORD, BONE, (1.0, 2.0, 3.0), (4.0, 5.0, 6.0))
        self.assertIsNone(bonedrive.stored_grip(SWORD))

    def test_autokey_is_off_for_every_write_and_restored(self):
        fake = self.use(FakeCmds(constrained=True))
        bonedrive.regrip(SWORD, BONE, (1.0, 0.0, 0.0), (0.0, 0.0, 0.0))
        self.assertTrue(all(state is False
                            for state in fake.autokey_during))
        self.assertTrue(fake.autokey)


class StoredGrip(WithFake):
    """The grip lives on the marked node itself: the optionVar is window
    policy, and the bridge's relink must not reach into it."""

    def test_round_trips(self):
        self.use(FakeCmds())
        bonedrive.store_grip(SWORD, (1.0, 2.0, 3.0), (4.0, 5.0, 6.0))
        self.assertEqual(bonedrive.stored_grip(SWORD),
                         ((1.0, 2.0, 3.0), (4.0, 5.0, 6.0)))

    def test_absent_reads_as_none(self):
        """None, not zeros: zeros are a real grip (the bone itself), and a
        legacy sword with no stored grip must keep today's snap-only path."""
        self.use(FakeCmds())
        self.assertIsNone(bonedrive.stored_grip(SWORD))

    def test_storing_twice_updates_without_adding_twice(self):
        self.use(FakeCmds())
        bonedrive.store_grip(SWORD, (1.0, 2.0, 3.0), (4.0, 5.0, 6.0))
        bonedrive.store_grip(SWORD, (7.0, 8.0, 9.0), (1.0, 1.0, 1.0))
        self.assertEqual(self.kinds().count("addattr"), 2)
        self.assertEqual(bonedrive.stored_grip(SWORD),
                         ((7.0, 8.0, 9.0), (1.0, 1.0, 1.0)))


class FindLinks(WithFake):

    def test_pairs_only_marked_drivers(self):
        fake = self.use(FakeCmds(constrained=True))
        self.assertEqual(bonedrive.find_links([BONE, "|skel|hand_r"]),
                         [(BONE, SWORD)])

    def test_unmarked_drivers_stay_out(self):
        fake = self.use(FakeCmds(constrained=True, marked=()))
        self.assertEqual(bonedrive.find_links([BONE]), [])

    def test_reads_only(self):
        fake = self.use(FakeCmds(constrained=True))
        bonedrive.find_links([BONE])
        self.assertEqual(fake.log, [])


if __name__ == "__main__":
    unittest.main()
