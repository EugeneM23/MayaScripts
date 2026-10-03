"""The pose library's solvers: bone targets -> channel values, the pure halves.

`skelsolve.joint_channels` is the joint's own decomposition (`R = RA^-1 . rot(local) . JO^-1` in
the joint's rotate order, the euler nearest the channel's current value); `rigsolve`'s pure
helpers are the level order (the game skeleton's depth, never the DAG's: AdvancedSkeleton hangs
the finger and hip offsets under FKSystem, shallower than the wrist and the pelvis they follow),
the limbs a set of members touches (a hand alone moves the IK end and keeps the pole), the rotation
log / exp and the Newton step the neck's in-between is solved with, and the measure's arithmetic.
The scene halves are proved in mayapy standalone on the shipped rigs (the task's scratch proof,
then verify_poselib_solve.py).

For the animation cards (2026-10-03): a frame's eulers seeded with the previous frame's values
(`seed`, both solvers), a skeleton's own root written for the travel (`root=True`), and the rig's
`Solver` - the structure built once, `solve(rig, wanted, members)` its one-frame case, Main turned
and moved onto the game root's target before RootX_M when asked (`main=True`).

Spec: docs/superpowers/specs/2026-10-02-pose-library-design.md ("Onto a skeleton", "Onto a rig").
"""

import math
import unittest

import maya.api.OpenMaya as om

from maya_poselib import rigsolve, skelsolve


def euler(r, order=0):
    return om.MEulerRotation(*([math.radians(v) for v in r] + [order])).asMatrix()


def placed(turn, point):
    values = list(turn)
    values[12:15] = list(point)
    return om.MMatrix(values)


def angle(a, b):
    q = om.MTransformationMatrix(a).rotation(asQuaternion=True).inverse() * \
        om.MTransformationMatrix(b).rotation(asQuaternion=True)
    v = math.sqrt(q.x * q.x + q.y * q.y + q.z * q.z)
    return math.degrees(2 * math.atan2(v, abs(q.w)))


class JointChannels(unittest.TestCase):
    """A joint's local rotation is RA . R . JO (row vectors); the channels come back exactly."""

    JO = (10.0, 20.0, 30.0)
    RA = (5.0, 0.0, 0.0)
    ZYX = 5

    def local(self, channels, order=ZYX, jo=JO, ra=RA, translate=(3.0, -4.0, 12.0)):
        turn = euler(ra) * euler(channels, order) * euler(jo)
        return placed(turn, translate)

    def test_round_trip_with_orient_axis_and_order(self):
        channels = (12.0, -40.0, 70.0)
        got = skelsolve.joint_channels(self.local(channels), self.JO, self.RA, self.ZYX,
                                       (0.0, 0.0, 0.0))
        for g, w in zip(got, channels):
            self.assertAlmostEqual(g, w, places=9)

    def test_a_flat_matrix_is_taken_too(self):
        channels = (-75.0, 33.0, 160.0)
        got = skelsolve.joint_channels(list(self.local(channels)), self.JO, self.RA, self.ZYX,
                                       channels)
        for g, w in zip(got, channels):
            self.assertAlmostEqual(g, w, places=9)

    def test_the_euler_nearest_the_current_one(self):
        """A channel wound past 360 stays wound: the solution nearest what the channel shows."""
        channels = (12.0, -40.0, 70.0)
        current = (372.0, -40.0, 70.0)
        got = skelsolve.joint_channels(self.local(channels), self.JO, self.RA, self.ZYX, current)
        for g, w in zip(got, current):
            self.assertAlmostEqual(g, w, places=9)

    def test_the_alternate_triple_when_it_is_nearer(self):
        """The same rotation written the other way round (x+180, 180-y, z+180) when the current
        value sits there - the euler a key next to the old one should carry (trap 108)."""
        channels = (10.0, 20.0, 30.0)
        alternate = (190.0, 160.0, 210.0)
        self.assertLess(angle(euler(channels), euler(alternate)), 1e-9)
        local = self.local(channels, order=0, jo=(0, 0, 0), ra=(0, 0, 0))
        got = skelsolve.joint_channels(local, (0, 0, 0), (0, 0, 0), 0, (185.0, 158.0, 205.0))
        for g, w in zip(got, alternate):
            self.assertAlmostEqual(g, w, places=9)

    def test_scale_in_the_local_matrix_is_ignored(self):
        channels = (5.0, 15.0, -25.0)
        local = om.MMatrix([[2, 0, 0, 0], [0, 2, 0, 0], [0, 0, 2, 0], [0, 0, 0, 1]]) * \
            self.local(channels)
        got = skelsolve.joint_channels(local, self.JO, self.RA, self.ZYX, (0, 0, 0))
        for g, w in zip(got, channels):
            self.assertAlmostEqual(g, w, places=9)

    def test_every_rotate_order(self):
        channels = (33.0, -12.0, 57.0)
        for order in range(6):
            got = skelsolve.joint_channels(self.local(channels, order=order), self.JO, self.RA,
                                           order, channels)
            for g, w in zip(got, channels):
                self.assertAlmostEqual(g, w, places=9, msg="order %d" % order)


class SkeletonHelpers(unittest.TestCase):

    def test_the_pelvis_by_canonical_name_then_by_leaf(self):
        self.assertEqual(skelsolve.pelvis_of({"Hips": {"canonical": "pelvis"},
                                              "pelvis": {"canonical": None}}), "Hips")
        self.assertEqual(skelsolve.pelvis_of({"pelvis": {}}), "pelvis")
        self.assertIsNone(skelsolve.pelvis_of({"root": {"canonical": "root"}}))

    def test_the_root_by_the_reference_then_the_shallowest(self):
        from collections import namedtuple
        Ref = namedtuple("Ref", "root")
        bones = {"root": {"parent": None, "path": "|g|root"},
                 "pelvis": {"parent": "root", "path": "|g|root|pelvis"},
                 "loose": {"parent": None, "path": "|loose"}}
        self.assertEqual(skelsolve.root_leaf(Ref("|g|root"), bones), "root")
        self.assertEqual(skelsolve.root_leaf(Ref(None), {"root": {"parent": None},
                                                          "pelvis": {"parent": "root"}}), "root")

    def test_parents_first(self):
        bones = {"root": {"parent": None}, "pelvis": {"parent": "root"},
                 "spine_01": {"parent": "pelvis"}, "thigh_l": {"parent": "pelvis"}}
        self.assertEqual(skelsolve.parents_first(bones, ["spine_01", "thigh_l", "pelvis", "x"]),
                         ["pelvis", "spine_01", "thigh_l", "x"])

    def test_a_local_against_its_parent_target(self):
        parent = placed(euler((0, 0, 30)), (10, 0, 0))
        local = placed(euler((15, 0, 0)), (5, 2, 0))
        got = skelsolve.local_of(local * parent, parent)
        self.assertLess(angle(got, local), 1e-9)
        for i in (12, 13, 14):
            self.assertAlmostEqual(got[i], local[i], places=9)


class LevelOrder(unittest.TestCase):

    def test_by_depth_then_by_name(self):
        depths = {"hand_l": 6, "index_metacarpal_l": 7, "clavicle_l": 4, "upperarm_l": 5,
                  "clavicle_r": 4, "thumb_01_l": 7}
        self.assertEqual(rigsolve.level_order(depths),
                         [["clavicle_l", "clavicle_r"], ["upperarm_l"], ["hand_l"],
                          ["index_metacarpal_l", "thumb_01_l"]])

    def test_nothing_is_no_level(self):
        self.assertEqual(rigsolve.level_order({}), [])

    def test_game_depth_from_a_path(self):
        self.assertEqual(rigsolve.depth_of("|Manny_Rig_Character|Manny_Rig:root|Manny_Rig:pelvis"), 3)
        self.assertEqual(rigsolve.depth_of("|root"), 1)


class LimbMembers(unittest.TestCase):
    """Which limbs a pose moves, and how: any chain bone poses the IK end; the pole (and the
    arm's swivel) only when the upper or the middle bone is a member - a hand alone keeps the
    arm's plane, the pole and the swivel standing."""

    def test_a_hand_alone_poses_the_end_and_keeps_the_pole(self):
        got = rigsolve.limb_members(["hand_l", "index_01_l", "middle_01_l"])
        self.assertEqual(got, {("arm", "L"): {"end": True, "pole": False}})

    def test_a_whole_arm_poses_the_pole(self):
        got = rigsolve.limb_members(["upperarm_r", "lowerarm_r", "hand_r"])
        self.assertEqual(got, {("arm", "R"): {"end": True, "pole": True}})

    def test_a_ball_belongs_to_the_leg(self):
        got = rigsolve.limb_members(["ball_l"])
        self.assertEqual(got, {("leg", "L"): {"end": True, "pole": False}})

    def test_the_clavicle_and_the_spine_touch_no_limb(self):
        self.assertEqual(rigsolve.limb_members(["clavicle_l", "spine_03", "head", "pelvis"]), {})

    def test_a_calf_poses_the_leg_pole(self):
        got = rigsolve.limb_members(["calf_l", "thigh_r"])
        self.assertEqual(got, {("leg", "L"): {"end": True, "pole": True},
                               ("leg", "R"): {"end": True, "pole": True}})


class Held(unittest.TestCase):
    """A bone no member of the pose but moved, non-rigidly, by a member's solve: the child of a
    member whose FKX joint is NOT below its control - AdvancedSkeleton's neck in-between, where
    solving FKNeck_M turns FKOffsetNeckPart1_M by the control's whole turn and neck_01 by half.
    Measured (task 7's verify, a Mixamo card - one neck - onto Manny_Rig): neck_02, not paired,
    stood 28.9 deg off the transfer's rigid follow and neck_01 pointed 14.3 deg off its source's
    neck. Such a child is held on its target (its rigid follow)."""

    CHILDREN = {"spine_05": ["neck_01", "clavicle_l"], "neck_01": ["neck_02"],
                "neck_02": ["head"], "pelvis": ["spine_01", "thigh_l"],
                "lowerarm_l": ["lowerarm_twist_01_l", "hand_l"]}

    def held(self, members, numeric=("neck_01",)):
        controlled = {"neck_01", "neck_02", "head", "spine_05", "clavicle_l", "spine_01",
                      "thigh_l", "hand_l", "lowerarm_l", "lowerarm_twist_01_l"}
        return rigsolve.held_bones(members, self.CHILDREN, set(numeric), controlled)

    def test_the_child_of_a_member_through_the_in_between_is_held(self):
        self.assertEqual(self.held(["spine_05", "neck_01", "head"]), ["neck_02"])
        self.assertEqual(self.held(["neck_01"]), ["neck_02"])

    def test_a_member_child_is_no_held_one(self):
        self.assertEqual(self.held(["neck_01", "neck_02", "head"]), [])

    def test_a_rigid_parent_holds_nothing(self):
        # the pelvis (RootX_M, no FKX joint) and every FK control above its FKX joint
        self.assertEqual(self.held(["pelvis", "lowerarm_l", "spine_05"], numeric=()), [])

    def test_a_held_bone_through_the_in_between_holds_its_own_child(self):
        self.assertEqual(self.held(["neck_01"], numeric=("neck_01", "neck_02")),
                         ["neck_02", "head"])

    def test_twist_and_helper_bones_and_bones_with_no_control_are_never_held(self):
        got = rigsolve.held_bones(["lowerarm_l"], {"lowerarm_l": ["lowerarm_twist_01_l",
                                                                  "ik_hand_l", "hand_l"]},
                                  {"lowerarm_l"}, {"lowerarm_twist_01_l", "ik_hand_l"})
        self.assertEqual(got, [])


class PolePoint(unittest.TestCase):
    """The pole for a drive chain: in the chain's own bend plane when it is bent (an IK elbow
    then lands exactly), fkik's nudge in the elbow's frame only when it is straight."""

    S, W = om.MVector(0, 0, 0), om.MVector(50, 0, 0)

    def normal(self, e):
        return ((e - self.S) ^ (self.W - self.S)).normal()

    def test_a_bent_chain_keeps_its_plane_whatever_the_side(self):
        e = om.MVector(25, 6, 2)
        sideways = om.MVector(0, 0, 1)            # a side out of the plane, as a rolled elbow
        point = rigsolve.pole_point(self.S, e, self.W, om.MMatrix(), sideways)
        self.assertAlmostEqual((point - self.S) * self.normal(e), 0.0, places=9)
        # on the elbow's side of the shoulder-wrist line, a limb out
        self.assertGreater(point.y, e.y)

    def test_fkik_bends_the_plane_with_the_same_side(self):
        """The control: fkik's own pole leaves the plane for that side - what this replaces."""
        from maya_scenesetup import fkik
        e = om.MVector(25, 6, 2)
        point = fkik.pole_point(self.S, e, self.W, om.MMatrix(), om.MVector(0, 0, 1))
        self.assertGreater(abs((point - self.S) * self.normal(e)), 1e-3)

    def test_a_straight_chain_takes_the_side(self):
        e = om.MVector(25, 0, 0)
        point = rigsolve.pole_point(self.S, e, self.W, om.MMatrix(), om.MVector(0, 0, 1))
        from maya_scenesetup import fkik
        expected = fkik.pole_point(self.S, e, self.W, om.MMatrix(), om.MVector(0, 0, 1))
        self.assertLess((point - expected).length(), 1e-9)
        self.assertGreater(point.z, 0.0)          # nudged away from the side, aimed back past it


class RotationVectors(unittest.TestCase):

    def test_log_and_exp_round_trip(self):
        for r in ((0, 0, 0), (30, 0, 0), (10, -50, 120), (0, 179, 0)):
            m = euler(r)
            back = rigsolve.turn(rigsolve.rotation_vector(m))
            self.assertLess(angle(m, back), 1e-9, msg=str(r))

    def test_the_length_is_the_angle(self):
        v = rigsolve.rotation_vector(euler((0, 0, 40)))
        self.assertAlmostEqual(math.degrees(math.sqrt(sum(x * x for x in v))), 40.0, places=9)
        self.assertAlmostEqual(v[2], math.radians(40.0), places=9)

    def test_the_short_way(self):
        """A quaternion with w < 0 is the same rotation: its vector is the short one."""
        v = rigsolve.rotation_vector(euler((0, 0, 350)))
        self.assertAlmostEqual(v[2], math.radians(-10.0), places=9)

    def test_identity_is_zero(self):
        self.assertEqual(rigsolve.rotation_vector(om.MMatrix()), (0.0, 0.0, 0.0))


class SolveStep(unittest.TestCase):
    """The numeric solve's step: damped least squares, `-(J'J + lambda I)^-1 J' e` - Newton when
    `J` has full rank (the neck's in-between, the IK toes), the reachable part only when it does
    not, so a joint with less freedom than its control is approached, never flown past."""

    def residual(self, columns, e0, d):
        return [e0[k] + sum(columns[i][k] * d[i] for i in range(3)) for k in range(3)]

    def test_a_linear_response_is_solved_in_one_step(self):
        """error(d) = e0 + J.d; the step lands it on zero."""
        columns = ((2.0, 0.5, 0.0), (0.0, 1.0, -0.3), (0.1, 0.0, 0.5))
        e0 = (0.3, -0.2, 0.7)
        d = rigsolve.solve_step(columns, e0)
        for r in self.residual(columns, e0, d):
            self.assertAlmostEqual(r, 0.0, places=7)

    def test_a_half_gain_doubles_the_step(self):
        """The neck's in-between at bias 0 turns the joint by half of the control's turn."""
        columns = ((0.5, 0, 0), (0, 0.5, 0), (0, 0, 0.5))
        for got, want in zip(rigsolve.solve_step(columns, (0.1, -0.2, 0.05)), (-0.2, 0.4, -0.1)):
            self.assertAlmostEqual(got, want, places=7)

    def test_an_axis_with_no_response_takes_no_step(self):
        """Rank 2: the reachable part is solved, the unreachable axis stays where it is."""
        columns = ((0, 0, 0), (0, 1, 0), (0, 0, 1))
        d = rigsolve.solve_step(columns, (1.0, 0.2, -0.3))
        self.assertAlmostEqual(d[0], 0.0, places=9)
        self.assertAlmostEqual(d[1], -0.2, places=7)
        self.assertAlmostEqual(d[2], 0.3, places=7)

    def test_two_controls_on_one_axis_share_it(self):
        """A rank-1 response along x from two parameters: the least step solves it."""
        columns = ((1, 0, 0), (1, 0, 0), (0, 0, 0))
        d = rigsolve.solve_step(columns, (0.4, 0.0, 0.0))
        self.assertAlmostEqual(d[0], -0.2, places=7)
        self.assertAlmostEqual(d[1], -0.2, places=7)
        self.assertAlmostEqual(d[2], 0.0, places=9)

    def test_no_response_is_no_step(self):
        self.assertIsNone(rigsolve.solve_step(((0, 0, 0), (0, 0, 0), (0, 0, 0)), (1, 0, 0)))


class Worst(unittest.TestCase):

    def test_full_rotation_position_and_the_worst_bone(self):
        a = placed(euler((0, 0, 0)), (0, 0, 0))
        rows = [("hand_l", a, placed(euler((0, 3, 0)), (0, 0, 0)), None),
                ("pelvis", a, placed(euler((0, 0, 1)), (0, 0.5, 0)), None)]
        deg, cm, leaf = rigsolve.worst(rows)
        self.assertAlmostEqual(deg, 3.0, places=9)
        self.assertAlmostEqual(cm, 0.5, places=9)
        self.assertEqual(leaf, "hand_l")

    def test_a_direction_ignores_the_roll_about_the_bone(self):
        """An unrolled limb bone is judged by where it points: a roll about its own axis (the
        twist AdvancedSkeleton moves into the twist joints, or the hinge an IK elbow is) is not
        a miss."""
        a = om.MMatrix()
        rolled = euler((25, 0, 0))
        deg, cm, leaf = rigsolve.worst([("lowerarm_l", a, rolled, (10.0, 0.0, 0.0))])
        self.assertAlmostEqual(deg, 0.0, places=9)
        bent = euler((0, 0, 7))
        deg, cm, leaf = rigsolve.worst([("lowerarm_l", a, bent, (10.0, 0.0, 0.0))])
        self.assertAlmostEqual(deg, 7.0, places=9)
        self.assertEqual(leaf, "lowerarm_l")

    def test_nothing_measured(self):
        self.assertEqual(rigsolve.worst([]), (0.0, 0.0, None))

    def test_a_row_not_placed_is_judged_by_its_turn_alone(self):
        """Only the pelvis is placed by a solve (RootX_M); every other bone stands where the
        rig's own lengths put it - Manny_Rig's point-constrained game bones wander 0.06 cm from
        pose to pose - so its position is no miss."""
        a = placed(euler((0, 0, 0)), (0, 0, 0))
        rows = [("calf_l", a, placed(euler((0, 0, 0)), (0, 0.06, 0)), None, False),
                ("pelvis", a, placed(euler((0, 0, 0)), (0, 0.004, 0)), None, True)]
        deg, cm, leaf = rigsolve.worst(rows)
        self.assertAlmostEqual(cm, 0.004, places=9)
        self.assertEqual(leaf, "pelvis")


class Unrolled(unittest.TestCase):
    """The unrolled bones are the four of a limb whose AdvancedSkeleton deformation joint never
    rolls (its roll lives in the twist joints, trap 126): only they are given in DRIVE form. The
    neck's in-between takes a share of the head's twist into neck_02 (measured: FKHead_M rx 30
    turned NeckPart1_M 15.0000, FKXNeckPart1_M 0.0000, Neck_M 0.0000), but its controls can hold
    any turn of their bones, so the neck lands its BONES - a skeleton's card held in drive form
    put Manny_Rig's neck_02 12.7 deg off."""

    def test_the_four_limb_bones(self):
        self.assertEqual(rigsolve.UNROLLED, ("Shoulder", "Elbow", "Hip", "Knee"))
        self.assertEqual(rigsolve.DIRECTION_BASES, ("Shoulder", "Elbow", "Hip", "Knee"))

    def test_the_share_of_the_head(self):
        self.assertEqual(rigsolve.SHARE_FROM, {"NeckPart1": "Head"})


class DriveOf(unittest.TestCase):
    """A drive is the drive chain's TURN at the game bone's PLACE: the chain stands on the
    deformation joint, and Manny_Rig's game calf, point-constrained with an offset, stands
    0.064 cm off `Knee_L` - a drive read whole put the calf there, off the bone every card and
    every target is read from."""

    def test_the_turn_of_the_chain_at_the_place_of_the_bone(self):
        g = placed(euler((10, 20, 30)), (4.0, 95.0, -2.0))
        d = placed(euler((12, 18, 33)), (4.0, 95.0, -2.0))
        s = placed(euler((40, -5, 60)), (4.0, 95.5, -2.0))
        got = rigsolve.drive_of(g, d, s)
        self.assertLess(angle(got, g * d.inverse() * s), 1e-9)
        self.assertLess((om.MVector(got[12], got[13], got[14]) -
                         om.MVector(4.0, 95.0, -2.0)).length(), 1e-12)

    def test_with_the_chain_on_the_joint_it_is_the_bone(self):
        g = placed(euler((10, 20, 30)), (4.0, 95.0, -2.0))
        d = placed(euler((12, 18, 33)), (4.0, 95.0, -2.0))
        got = rigsolve.drive_of(g, d, d)
        self.assertLess(angle(got, g), 1e-9)


class RecordingCmds(object):
    """The few `cmds` calls `_Job.run`'s frame makes, recorded in order: the undo chunk, the
    evaluation manager (already in `FRESH_MODE`, so `_fresh` switches nothing), any time change
    (there must be none) and the session's autoKey toggles."""

    def __init__(self):
        self.log = []

    def undoInfo(self, openChunk=False, closeChunk=False, chunkName=None, **kwargs):
        if openChunk:
            self.log.append(("open", chunkName))
        if closeChunk:
            self.log.append(("close",))

    def evaluationManager(self, query=False, mode=None):
        if query:
            return [rigsolve.FRESH_MODE]
        self.log.append(("em", mode))

    def currentTime(self, value=None, query=False, update=None):
        if query:
            return 7.0
        self.log.append(("time", value))

    def autoKeyframe(self, query=False, state=None):
        if query:
            return True
        self.log.append(("autoKey", state))


class OneUndoStep(unittest.TestCase):
    """A solve is ONE closed undo chunk around everything it writes and puts back - the autoKey
    toggles, the settle, every temporary setAttr and every restore - so a Ctrl+Z after it is one
    net-nothing step. Measured before the fix (mayapy, Manny_Rig, autoKey on, a solve outside any
    chunk): the scene came back exact, then the first Ctrl+Z turned the animator's autoKey OFF and
    the second put the solve's temporary 30 deg on an unkeyed FKElbow_L.rotateX (trap 186). The
    scene half is proved by the task's scratch check (undo6.py); this pins the frame's order."""

    def setUp(self):
        self.fake = RecordingCmds()
        self.saved = rigsolve.cmds
        rigsolve.cmds = self.fake

    def tearDown(self):
        rigsolve.cmds = self.saved

    def job(self, run_pass=None):
        from collections import OrderedDict
        job = object.__new__(rigsolve._Job)
        job.rig, job.members, job.notes = None, [], OrderedDict()
        job.session = rigsolve._Session()
        log = self.fake.log
        job.sample = lambda: log.append(("sample",))
        job.plan_levels = lambda: log.append(("levels",))
        job.run_pass = run_pass or (lambda: log.append(("pass",)))
        job.rows = lambda: []
        return job

    def test_the_chunk_holds_everything_the_solve_does_and_no_time_change(self):
        # no time change: the first build's same-frame `currentTime` "settle" threw away every
        # unkeyed tweak on a keyed channel in the whole scene (the final review)
        solution = self.job().run()
        self.assertEqual(self.fake.log, [
            ("open", rigsolve.UNDO_CHUNK),
            ("autoKey", False),
            ("sample",), ("levels",), ("pass",),
            ("autoKey", True),
            ("close",),
        ])
        self.assertEqual(rigsolve.UNDO_CHUNK, "skeldarPoseSolve")
        self.assertEqual(dict(solution.values), {})

    def test_a_solve_that_raises_still_closes_its_chunk(self):
        log = self.fake.log

        def broken():
            log.append(("pass",))
            raise RuntimeError("half way")

        with self.assertRaises(RuntimeError):
            self.job(broken).run()
        self.assertEqual(log[0], ("open", rigsolve.UNDO_CHUNK))
        self.assertEqual(log[-2:], [("autoKey", True), ("close",)])
        self.assertEqual(sum(1 for entry in log if entry[0] == "close"), 1)


class ParallelCmds(RecordingCmds):
    """RecordingCmds in a GUI Maya: the evaluation manager answers "parallel" until switched."""

    def __init__(self):
        RecordingCmds.__init__(self)
        self.mode = "parallel"

    def evaluationManager(self, query=False, mode=None):
        if query:
            return [self.mode]
        self.log.append(("em", mode))
        self.mode = mode


class FreshMode(unittest.TestCase):
    """The solve reads under DG. Measured 2026-10-03 in a disposable GUI Maya (verify_poselib_gui
    `fresh` / `stale`): under the parallel evaluation manager `FKHead_M.parentMatrix[0]` read
    after the neck's numeric probes set `FKNeckPart1_M` on a KEYED rig came back stale, and the
    head landed 8 to 24 deg off its pose in every trial; DG landed it to 0.0002 deg. Leaving the
    manager be (`FRESH_MODE = None`) is the measured-wrong choice, whatever the switch costs
    (Cached Playback flushed)."""

    job = OneUndoStep.job

    def setUp(self):
        self.fake = ParallelCmds()
        self.saved = rigsolve.cmds, rigsolve.keys
        rigsolve.cmds = self.fake
        log = self.fake.log

        class Tweaks(object):
            def __init__(self):
                log.append(("tweaks",))

            def restore(self, skip=()):
                log.append(("restore", list(skip)))
                return []

        class Keys(object):
            pass
        fake_keys = Keys()
        fake_keys.Tweaks = Tweaks
        fake_keys.writable = rigsolve.keys.writable
        rigsolve.keys = fake_keys

    def tearDown(self):
        rigsolve.cmds, rigsolve.keys = self.saved

    def test_the_solve_reads_under_dg(self):
        self.assertEqual(rigsolve.FRESH_MODE, "off")

    def test_a_parallel_scene_is_switched_inside_the_chunk_and_put_back(self):
        self.job().run()
        log = self.fake.log
        self.assertEqual(log[0], ("open", rigsolve.UNDO_CHUNK))
        self.assertEqual(log[-2:], [("restore", []), ("close",)])
        self.assertLess(log.index(("em", "off")), log.index(("sample",)))
        self.assertLess(log.index(("em", "parallel")), log.index(("close",)))
        self.assertEqual(self.fake.mode, "parallel")

    def test_the_switch_puts_the_scene_s_tweaks_back_both_ways(self):
        """The final review: switching the evaluation manager re-evaluates every time curve in
        the scene, and an unkeyed tweak on a keyed channel snaps back to its curve. The tweaks
        are read BEFORE the switch, and set back right after it - before the solve reads the rig,
        and again after the switch back."""
        self.job().run()
        log = self.fake.log
        self.assertEqual(log[1:4], [("tweaks",), ("em", "off"), ("restore", [])])
        self.assertLess(log.index(("restore", [])), log.index(("sample",)))
        back = len(log) - 1 - log[::-1].index(("em", "parallel"))
        self.assertEqual(log[back + 1], ("restore", []))


class Writable(object):
    """A stand-in for `keys`: `writable` answers "locked" for the plugs in `locked` (held, not
    copied - a test may lock a plug after the fake is installed)."""

    def __init__(self, locked=()):
        self.locked = locked

    def writable(self, plug):
        return (False, "locked") if plug in self.locked else (True, "")


class SkeletonCmds(object):
    """The `cmds` reads `skelsolve.solve` makes: a joint's parentMatrix / worldMatrix (identity
    unless given) and a channel's current value (0 unless given)."""

    def __init__(self, parents=None, values=None):
        self.parents = parents or {}
        self.values = values or {}
        self.read = []

    def getAttr(self, plug, **kwargs):
        self.read.append(plug)
        node, attr = plug.rsplit(".", 1)
        if attr == "parentMatrix[0]":
            return list(self.parents.get(node, om.MMatrix()))
        if attr == "worldMatrix[0]":
            return list(om.MMatrix())
        return self.values.get(plug, 0.0)


class SkeletonFake(unittest.TestCase):
    """`skelsolve` with its `cmds` and `keys` rebound (`skelsolve.cmds = fake`)."""

    def setUp(self):
        self.saved = skelsolve.cmds, skelsolve.keys

    def tearDown(self):
        skelsolve.cmds, skelsolve.keys = self.saved

    def use(self, cmds, locked=()):
        skelsolve.cmds = cmds
        skelsolve.keys = Writable(locked)


class Seed(SkeletonFake):
    """A frame series seeds each frame's eulers with the PREVIOUS frame's solved values (trap
    108): the seed replaces what the channel shows now as the nearest-euler reference - a
    channel the walk has not keyed yet reads 0 while the previous frame stood at 360."""

    BONES = {"hips": {"path": "|hips", "parent": None, "canonical": None,
                      "world": list(om.MMatrix()), "rotateOrder": 0,
                      "jointOrient": (0.0, 0.0, 0.0), "rotateAxis": (0.0, 0.0, 0.0)}}

    def solve(self, seed=None):
        self.use(SkeletonCmds())
        wanted = {"hips": euler((10.0, 0.0, 0.0))}
        ref = type("Ref", (), {"root": None})()
        return skelsolve.solve(ref, self.BONES, wanted, ["hips"], seed=seed)

    def test_without_a_seed_the_nearest_to_what_the_channel_shows(self):
        self.assertAlmostEqual(self.solve().values["|hips.rotateX"], 10.0, places=6)

    def test_the_seed_is_the_reference(self):
        seed = {"|hips.rotateX": 360.0, "|hips.rotateY": 0.0, "|hips.rotateZ": 0.0}
        values = self.solve(seed).values
        self.assertAlmostEqual(values["|hips.rotateX"], 370.0, places=6)
        self.assertAlmostEqual(values["|hips.rotateY"], 0.0, places=6)

    def test_a_seed_that_names_other_plugs_changes_nothing(self):
        values = self.solve({"|other.rotateX": 360.0}).values
        self.assertAlmostEqual(values["|hips.rotateX"], 10.0, places=6)


class RootWritten(SkeletonFake):
    """An animation's travel: with `root=True` a skeleton's own root joint is written to its
    target - rotate and translate, against its DAG parent (`local = wanted[root] .
    parentMatrix^-1`); without it the root is never written (the pose rule)."""

    ROOT, PELVIS = "|grp|root", "|grp|root|pelvis"
    GROUP = placed(om.MMatrix(), (0.0, 0.0, 2.0))   # the root's DAG parent, 2 cm along Z

    def bones(self):
        bone = {"world": list(om.MMatrix()), "rotateOrder": 0,
                "jointOrient": (0.0, 0.0, 0.0), "rotateAxis": (0.0, 0.0, 0.0)}
        return {"root": dict(bone, path=self.ROOT, parent=None, canonical="root"),
                "pelvis": dict(bone, path=self.PELVIS, parent="root", canonical="pelvis")}

    def solve(self, root, locked=()):
        self.use(SkeletonCmds(parents={self.ROOT: self.GROUP}), locked)
        root_at = placed(euler((0.0, 30.0, 0.0)), (5.0, 0.0, 7.0))
        wanted = {"root": root_at, "pelvis": placed(euler((0, 0, 15)), (0, 96, 0)) * root_at}
        ref = type("Ref", (), {"root": self.ROOT})()
        return skelsolve.solve(ref, self.bones(), wanted, ["pelvis"], root=root)

    def test_without_root_the_root_is_never_written(self):
        solution = self.solve(root=False)
        self.assertFalse([p for p in solution.values if p.startswith(self.ROOT + ".")])
        self.assertAlmostEqual(solution.values[self.PELVIS + ".rotateZ"], 15.0, places=6)

    def test_with_root_its_rotate_and_translate_reach_the_target(self):
        values = self.solve(root=True).values
        self.assertAlmostEqual(values[self.ROOT + ".rotateY"], 30.0, places=6)
        self.assertAlmostEqual(values[self.ROOT + ".rotateX"], 0.0, places=6)
        got = [values[self.ROOT + "." + ch] for ch in skelsolve.TRANSLATE]
        for g, w in zip(got, (5.0, 0.0, 5.0)):        # 7 along Z less the group's 2
            self.assertAlmostEqual(g, w, places=6)
        # the pelvis as before, against the root's target
        self.assertAlmostEqual(values[self.PELVIS + ".rotateZ"], 15.0, places=6)

    def test_a_root_not_in_wanted_is_not_written(self):
        self.use(SkeletonCmds())
        ref = type("Ref", (), {"root": self.ROOT})()
        solution = skelsolve.solve(ref, self.bones(), {"pelvis": om.MMatrix()}, ["pelvis"],
                                   root=True)
        self.assertFalse([p for p in solution.values if p.startswith(self.ROOT + ".")])

    def test_a_locked_root_translate_is_skipped(self):
        solution = self.solve(root=True, locked=[self.ROOT + ".translateX"])
        self.assertIn("root", solution.skipped)
        self.assertIn("translateX locked", solution.skipped["root"])
        self.assertFalse([p for p in solution.values if p.startswith(self.ROOT + ".translate")])


# a Manny_Rig's structure as data: the game root and pelvis, a left hand
STRUCTURE_RIG = rigsolve.maya_rigs.Rig("Manny_Rig", "Manny_Rig:ControlSet", "Manny_Rig:Main",
                                       "|chr|Manny_Rig:Group", "|chr|Manny_Rig:root", "|chr")
MAIN_PATH = "|chr|Manny_Rig:Group|Manny_Rig:Main"
ROOTX_PATH = "|chr|Manny_Rig:Group|Manny_Rig:RootX_M"
STRUCTURE_GAME = {"root": "|chr|Manny_Rig:root", "pelvis": "|chr|Manny_Rig:root|Manny_Rig:pelvis",
                  "hand_l": "|chr|Manny_Rig:root|Manny_Rig:pelvis|Manny_Rig:hand_l"}
STRUCTURE_BASES = {
    "pelvis": rigsolve.Base("pelvis", "Root", "_M", ROOTX_PATH, None, None, "|Root_M", None),
    "hand_l": rigsolve.Base("hand_l", "Wrist", "_L", "|FKWrist_L", "|FKWrist_L|FKXWrist_L",
                            "|IKXWrist_L", "|Wrist_L", "arm"),
}


class StructureCmds(RecordingCmds):
    """RecordingCmds that also resolves a rig node to its long path (`Main` under the group)."""

    def ls(self, name, long=False, **kwargs):
        return [MAIN_PATH] if name == STRUCTURE_RIG.main else []


class StructureFake(unittest.TestCase):
    """`rigsolve` with the rig's structure as data: `bases` / `game_bones` stubbed (and counted),
    the job's scene steps - the samples, the levels, the measure, every control turned or moved -
    logged instead of run; the passes themselves run."""

    def setUp(self):
        from unittest import mock
        self.fake = StructureCmds()
        self.log = self.fake.log
        self.counts = {"bases": 0, "game_bones": 0}
        log, counts = self.log, self.counts

        def bases(rig):
            counts["bases"] += 1
            return dict(STRUCTURE_BASES)

        def game_bones(rig):
            counts["game_bones"] += 1
            return dict(STRUCTURE_GAME)

        def sample(job):
            log.append(("sample", tuple(job.members), tuple(sorted(job.wanted))))
            job.root_offset = om.MMatrix()
            job.main_offset = self.offset

        def plan_levels(job):
            log.append(("levels",))
            job.levels, job.ends = [], {}

        def turn(job, node, world):
            log.append(("turn", node, tuple(om.MMatrix(world))))
            return True

        def move(job, node, point):
            log.append(("move", node, (point.x, point.y, point.z)))
            return True

        self.offset = om.MMatrix()
        self.locked = set()
        patches = [mock.patch.object(rigsolve, "cmds", self.fake),
                   mock.patch.object(rigsolve, "keys", Writable(self.locked)),
                   mock.patch.object(rigsolve, "bases", bases),
                   mock.patch.object(rigsolve, "game_bones", game_bones),
                   mock.patch.object(rigsolve._Job, "sample", sample),
                   mock.patch.object(rigsolve._Job, "plan_levels", plan_levels),
                   mock.patch.object(rigsolve._Job, "rows", lambda job: []),
                   mock.patch.object(rigsolve._Job, "_turn", turn),
                   mock.patch.object(rigsolve._Job, "_move", move)]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)


class SolverIsSolve(StructureFake):
    """`solve(rig, wanted, members)` is `Solver(rig, members).solve(wanted)`: the structure - the
    game bones, the bases, the member filter, the limbs, the held bones - built ONCE per Solver,
    each `.solve` one frame's samples, targets and writes."""

    WANTED = {"pelvis": om.MMatrix(), "hand_l": om.MMatrix()}

    def test_the_same_calls_either_way(self):
        rigsolve.solve(STRUCTURE_RIG, self.WANTED, ["hand_l", "pelvis"])
        once = list(self.log)
        del self.log[:]
        rigsolve.Solver(STRUCTURE_RIG, ["hand_l", "pelvis"]).solve(self.WANTED)
        self.assertEqual(self.log, once)
        self.assertIn(("sample", ("hand_l", "pelvis"), ("hand_l", "pelvis")), once)
        self.assertIn(ROOTX_PATH, [entry[1] for entry in once if entry[0] == "turn"])

    def test_the_structure_is_built_once(self):
        solver = rigsolve.Solver(STRUCTURE_RIG, ["hand_l", "pelvis"])
        solver.solve(self.WANTED)
        solver.solve(self.WANTED)
        self.assertEqual(self.counts, {"bases": 1, "game_bones": 1})
        self.assertEqual(sum(1 for entry in self.log if entry[0] == "sample"), 2)
        self.assertEqual(sum(1 for entry in self.log if entry == ("open", rigsolve.UNDO_CHUNK)),
                         2)

    def test_controls_for_is_the_solver_s(self):
        self.assertEqual(rigsolve.controls_for(STRUCTURE_RIG, ["pelvis"]), [ROOTX_PATH])
        self.assertEqual(rigsolve.Solver(STRUCTURE_RIG, ["pelvis"]).controls(), [ROOTX_PATH])

    def test_controls_with_main_put_main_first(self):
        self.assertEqual(rigsolve.controls_for(STRUCTURE_RIG, ["pelvis"], main=True),
                         [MAIN_PATH, ROOTX_PATH])


class MainFirst(StructureFake):
    """The travel on a rig: Main turned and moved onto `O^-1 . wanted[root]` (O the game root in
    Main, sampled each frame) BEFORE RootX_M, which then solves against the moved Main - and only
    when the Solver was asked (`main=True`) and the frame's wanted holds the root."""

    ROOT_AT = placed(euler((0.0, 40.0, 0.0)), (120.0, 0.0, -30.0))

    @property
    def writes(self):
        return [entry for entry in self.log if entry[0] in ("turn", "move")]

    def solve(self, main, wanted=None):
        wanted = dict({"root": self.ROOT_AT, "pelvis": om.MMatrix()}, **(wanted or {}))
        return rigsolve.Solver(STRUCTURE_RIG, ["pelvis"], main=main).solve(wanted)

    def test_main_before_rootx(self):
        self.offset = placed(om.MMatrix(), (0.0, 0.0, 3.0))       # the game root 3 cm off Main
        self.solve(main=True)
        self.assertEqual([(w[0], w[1]) for w in self.writes],
                         [("turn", MAIN_PATH), ("move", MAIN_PATH),
                          ("turn", ROOTX_PATH), ("move", ROOTX_PATH)])
        aim = self.offset.inverse() * self.ROOT_AT
        self.assertLess(angle(om.MMatrix(self.writes[0][2]), aim), 1e-9)
        self.assertLess((om.MVector(*self.writes[1][2]) -
                         om.MVector(aim[12], aim[13], aim[14])).length(), 1e-9)

    def test_without_main_no_main_write(self):
        self.solve(main=False)
        self.assertEqual([w[1] for w in self.writes], [ROOTX_PATH, ROOTX_PATH])

    def test_without_the_root_in_wanted_no_main_write(self):
        rigsolve.Solver(STRUCTURE_RIG, ["pelvis"], main=True).solve({"pelvis": om.MMatrix()})
        self.assertNotIn(MAIN_PATH, [w[1] for w in self.writes])

    def test_a_main_that_is_not_writable_is_kept_and_named(self):
        self.locked.add(MAIN_PATH + ".translateY")
        solution = self.solve(main=True)
        self.assertNotIn(MAIN_PATH, [w[1] for w in self.writes])
        self.assertIn(rigsolve.MAIN_KEPT % "translateY locked", solution.notes)
        self.assertEqual(rigsolve.MAIN_KEPT,
                         "Main kept where it stands (%s) - the travel is not carried")


class RigSeedCmds(object):
    """The reads `_Job._remember` makes on one control, counting the rotate reads."""

    def __init__(self):
        self.rotate_reads = 0

    def getAttr(self, plug, **kwargs):
        if plug.endswith(".rotateOrder"):
            return 2
        if plug.endswith(".rotateAxis"):
            return [(0.0, 0.0, 0.0)]
        if plug.endswith(".rotate"):
            self.rotate_reads += 1
            return [(0.0, 0.0, 0.0)]
        raise AssertionError(plug)

    def ls(self, path, **kwargs):
        return [path.split("|")[-1]]


class RigSeed(unittest.TestCase):
    """A rig's control takes its nearest-euler reference from the seed (the previous frame's
    Solution.values, spelled by the control's short name) when the seed names all three rotate
    channels; else from what the control shows."""

    def setUp(self):
        self.fake = RigSeedCmds()
        self.saved = rigsolve.cmds
        rigsolve.cmds = self.fake

    def tearDown(self):
        rigsolve.cmds = self.saved

    def job(self, seed):
        job = object.__new__(rigsolve._Job)
        job.order, job.axis, job.rest_rotate = {}, {}, {}
        job.seed = seed
        job.spelled = {}
        return job

    def test_the_seed_names_the_control(self):
        job = self.job({"FKWrist_L.rotateX": 360.0, "FKWrist_L.rotateY": 10.0,
                        "FKWrist_L.rotateZ": -720.0})
        job._remember("|g|FKWrist_L")
        self.assertEqual(job.rest_rotate["|g|FKWrist_L"], (360.0, 10.0, -720.0))
        self.assertEqual(job.order["|g|FKWrist_L"], 2)
        self.assertEqual(self.fake.rotate_reads, 0)

    def test_a_partial_seed_reads_the_control(self):
        job = self.job({"FKWrist_L.rotateX": 360.0})
        job._remember("|g|FKWrist_L")
        self.assertEqual(job.rest_rotate["|g|FKWrist_L"], (0.0, 0.0, 0.0))
        self.assertEqual(self.fake.rotate_reads, 1)


class Shared(unittest.TestCase):

    def test_one_solution_shape_for_both(self):
        self.assertIs(rigsolve.Solution, skelsolve.Solution)
        self.assertEqual(skelsolve.Solution._fields, ("values", "notes", "skipped"))
        self.assertEqual(rigsolve.Base._fields,
                         ("leaf", "base", "side", "fk", "fkx", "ikx", "deform", "limb"))


if __name__ == "__main__":
    unittest.main()
