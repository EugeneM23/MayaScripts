"""The pose library's solvers: bone targets -> channel values, the pure halves.

`skelsolve.joint_channels` is the joint's own decomposition (`R = RA^-1 . rot(local) . JO^-1` in
the joint's rotate order, the euler nearest the channel's current value); `rigsolve`'s pure
helpers are the level order (the game skeleton's depth, never the DAG's: AdvancedSkeleton hangs
the finger and hip offsets under FKSystem, shallower than the wrist and the pelvis they follow),
the limbs a set of members touches (a hand alone moves the IK end and keeps the pole), the rotation
log / exp and the Newton step the neck's in-between is solved with, and the measure's arithmetic.
The scene halves are proved in mayapy standalone on the shipped rigs (the task's scratch proof,
then verify_poselib_solve.py).

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
    evaluation manager (already in `FRESH_MODE`, so `_fresh` switches nothing), the settle's
    time change and the session's autoKey toggles."""

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

    def test_the_chunk_holds_everything_the_solve_does(self):
        solution = self.job().run()
        self.assertEqual(self.fake.log, [
            ("open", rigsolve.UNDO_CHUNK),
            ("autoKey", False),
            ("time", 7.0),
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
            self.job(broken).run(settle=False)
        self.assertEqual(log[0], ("open", rigsolve.UNDO_CHUNK))
        self.assertEqual(log[-2:], [("autoKey", True), ("close",)])
        self.assertEqual(sum(1 for entry in log if entry[0] == "close"), 1)


class Shared(unittest.TestCase):

    def test_one_solution_shape_for_both(self):
        self.assertIs(rigsolve.Solution, skelsolve.Solution)
        self.assertEqual(skelsolve.Solution._fields, ("values", "notes", "skipped"))
        self.assertEqual(rigsolve.Base._fields,
                         ("leaf", "base", "side", "fk", "fkx", "ikx", "deform", "limb"))


if __name__ == "__main__":
    unittest.main()
