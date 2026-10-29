"""`rigsolve`'s scene reads and its measure, the parts `test_poselib_solve` leaves out: a rig's game
bones and the node each follows, the bases built from them (`game_bones`, `_driver`, `bases`,
`root_leaf`), the drive chain as the rig shows it (`_blend`, `_shown`, `_drive`, `drive_matrices`),
the evaluation switch, the writable question a place asks, a Tools knot driving a control
(`knot_driver`), the spine's blend and the measure rows (`_rows`, `Solver.measure`, `measure`).

The scene is a dict behind a fake `cmds`; each seam is rebound for the test and restored by cleanup.
The solve itself (`_Job`) runs on a real rig and is proven by `verify_poselib_solve.py`, not here.
"""
import unittest

try:
    import maya.cmds  # noqa: F401  (the real package when mayapy has it - trap 60)
except ImportError:
    pass

import maya.api.OpenMaya as om
import maya_rigs
from maya_scenesetup import fkik

from maya_poselib import keys, posemath as pm, rigsolve
from tests.test_poselib_helpers import close, trs

RIG = maya_rigs.Rig("R", "R:ControlSet", "R:Main", "|chr|R:Group", "|chr|R:root", "|chr")


class Patched(unittest.TestCase):

    def patch(self, target, name, value):
        saved = getattr(target, name)
        setattr(target, name, value)
        self.addCleanup(setattr, target, name, saved)


class SceneCmds(object):
    """A dict scene: `names` {name: [long paths]} for `ls`, `children` {path: {type: [constraints]}},
    `targets` {constraint: [targets]}, `attrs` {(node, attr): value}, `exists`."""

    def __init__(self, names=None, children=None, targets=None, attrs=None, exists=(), joints=None,
                 mode=("off",)):
        self.names = names or {}
        self.children = children or {}
        self.targets = targets or {}
        self.attrs = attrs or {}
        self.exist = set(exists)
        self.joints = joints
        self.mode = mode

    def ls(self, name, long=False, **kwargs):
        return list(self.names.get(name, []))

    def objExists(self, node):
        return node in self.exist

    def listRelatives(self, path, children=False, allDescendents=False, type=None, fullPath=False):
        if allDescendents:
            return self.joints
        return self.children.get(path, {}).get(type)

    def orientConstraint(self, constraint, query=False, targetList=False):
        return self.targets.get(constraint)

    parentConstraint = orientConstraint

    def attributeQuery(self, attr, node=None, exists=False):
        return (node, attr) in self.attrs

    def getAttr(self, plug):
        node, attr = plug.rsplit(".", 1)
        value = self.attrs[(node, attr)]
        if isinstance(value, Exception):
            raise value
        return value

    def evaluationManager(self, query=False, mode=None):
        return self.mode


class Names(unittest.TestCase):

    def test_a_few_names_are_all_said(self):
        self.assertEqual(rigsolve._named(["a", "b"]), "a, b")
        self.assertEqual(rigsolve._named(iter(["a"])), "a")

    def test_many_names_are_cut_short(self):
        self.assertEqual(rigsolve._named(list("abcdef")), "a, b, c, d and 2 more")


class SceneReads(Patched):

    def use(self, **kwargs):
        fake = SceneCmds(**kwargs)
        self.patch(rigsolve, "cmds", fake)
        return fake

    def test_one_of_the_rig_s_nodes_is_its_long_path_when_it_is_the_only_one(self):
        self.use(names={"R:FKWrist_L": ["|chr|R:Group|R:FKWrist_L"], "R:FKX": ["|a", "|b"], "R:Gone": []})
        self.assertEqual(rigsolve._one(RIG, "FKWrist_L"), "|chr|R:Group|R:FKWrist_L")
        self.assertIsNone(rigsolve._one(RIG, "FKX"))
        self.assertIsNone(rigsolve._one(RIG, "Gone"))

    def test_the_game_bones_are_the_root_and_the_joints_under_it_by_leaf(self):
        self.use(exists=["|chr|R:root"], joints=["|chr|R:root|R:pelvis", "|chr|R:root|R:pelvis|R:hand_l",
                                                 "|other|R:hand_l"])
        self.assertEqual(rigsolve.game_bones(RIG), {
            "root": "|chr|R:root", "pelvis": "|chr|R:root|R:pelvis",
            "hand_l": "|chr|R:root|R:pelvis|R:hand_l"})

    def test_a_rig_with_no_game_skeleton_has_no_game_bones(self):
        self.use()
        self.assertEqual(rigsolve.game_bones(RIG), {})
        self.assertEqual(rigsolve.game_bones(RIG._replace(skeleton_root=None)), {})

    def test_a_rig_whose_root_has_no_joints_below_has_only_the_root(self):
        self.use(exists=["|chr|R:root"], joints=None)
        self.assertEqual(rigsolve.game_bones(RIG), {"root": "|chr|R:root"})

    def test_a_game_bone_follows_the_one_target_of_its_orient_constraint(self):
        self.use(children={"|g": {"orientConstraint": ["|g|oc"]}}, targets={"|g|oc": ["Wrist_L"]},
                 names={"Wrist_L": ["|chr|R:Wrist_L"]})
        self.assertEqual(rigsolve._driver("|g"), "|chr|R:Wrist_L")

    def test_else_the_one_target_of_its_parent_constraint(self):
        self.use(children={"|g": {"parentConstraint": ["|g|pc"]}}, targets={"|g|pc": ["Wrist_L"]},
                 names={"Wrist_L": ["|chr|R:Wrist_L"]})
        self.assertEqual(rigsolve._driver("|g"), "|chr|R:Wrist_L")

    def test_no_constraint_two_targets_or_an_ambiguous_target_follow_nothing(self):
        self.use(children={"|none": {}, "|two": {"orientConstraint": ["|two|oc"]},
                           "|amb": {"orientConstraint": ["|amb|oc"]}},
                 targets={"|two|oc": ["a", "b"], "|amb|oc": ["c"]}, names={"c": ["|x|c", "|y|c"]})
        self.assertIsNone(rigsolve._driver("|none"))
        self.assertIsNone(rigsolve._driver("|two"))
        self.assertIsNone(rigsolve._driver("|amb"))


class Bases(Patched):

    GAME = {"pelvis": "|root|pelvis", "upperarm_l": "|root|pelvis|upperarm_l",
            "hand_l": "|root|pelvis|hand_l", "spine_01": "|root|pelvis|spine_01"}

    def setUp(self):
        self.driven = {}
        self.nodes = {}
        self.root = "pelvis"
        self.patch(rigsolve, "game_bones", lambda rig: self.GAME)
        self.patch(rigsolve, "_one", lambda rig, leaf: self.nodes.get(leaf))
        self.patch(rigsolve, "_driver", lambda path: self.driven.get(path))
        self.patch(rigsolve, "root_leaf", lambda rig, game: self.root)

    def test_a_game_bone_the_rig_drives_through_a_joint_base_is_a_base(self):
        self.nodes = {"FKShoulder_L": "|FKShoulder_L", "FKXShoulder_L": "|FKX", "IKXShoulder_L": "|IKX",
                      "Shoulder_L": "|Shoulder_L"}
        out = rigsolve.bases(RIG)
        self.assertEqual(out["upperarm_l"], rigsolve.Base(
            "upperarm_l", "Shoulder", "_L", "|FKShoulder_L", "|FKX", "|IKX", "|Shoulder_L", "arm"))

    def test_the_deformation_joint_is_the_target_the_orient_constraint_measured(self):
        self.nodes = {"FKShoulder_L": "|FK", "Shoulder_L": "|by_name"}
        self.driven["|root|pelvis|upperarm_l"] = "|measured"
        self.assertEqual(rigsolve.bases(RIG)["upperarm_l"].deform, "|measured")

    def test_a_bone_with_no_control_joint_or_deform_is_no_base(self):
        self.nodes = {}
        out = rigsolve.bases(RIG)
        self.assertNotIn("upperarm_l", out)
        self.assertNotIn("hand_l", out)
        self.assertNotIn("spine_01", out)

    def test_a_bone_the_skeleton_lacks_is_no_base(self):
        self.nodes = {"FKShoulder_R": "|FKShoulder_R"}
        self.assertNotIn("upperarm_r", rigsolve.bases(RIG))

    def test_the_root_bone_is_a_base_of_its_root_control_and_deform(self):
        self.nodes = {"RootX_M": "|RootX_M", "Root_M": "|Root_M"}
        self.assertEqual(rigsolve.bases(RIG)["pelvis"], rigsolve.Base(
            "pelvis", "Root", "_M", "|RootX_M", None, None, "|Root_M", None))

    def test_the_root_bone_prefers_the_measured_deform(self):
        self.nodes = {"RootX_M": "|RootX_M", "Root_M": "|Root_M"}
        self.driven[self.GAME["pelvis"]] = "|measured"
        self.assertEqual(rigsolve.bases(RIG)["pelvis"].deform, "|measured")

    def test_no_root_bone_is_no_root_base(self):
        self.root = None
        self.nodes = {"RootX_M": "|RootX_M"}
        self.assertNotIn("Root", [b.base for b in rigsolve.bases(RIG).values()])


class RootBone(Patched):

    def setUp(self):
        self.driven = {}
        self.attrs = {}
        self.patch(rigsolve, "_driver", lambda path: self.driven.get(path))

    def scene(self, attrs=None):
        self.patch(rigsolve, "cmds", SceneCmds(attrs=attrs))

    def test_the_pelvis_when_it_follows_something(self):
        self.driven["|pelvis"] = "|Root_M"
        self.scene()
        self.assertEqual(rigsolve.root_leaf(RIG, {"pelvis": "|pelvis"}), "pelvis")

    def test_a_part_rig_s_anchor_bone_when_the_pelvis_follows_nothing(self):
        self.driven["|spine_05"] = "|Spine5_M"
        self.scene({("|chr|R:Group", "skeldarPartAnchor"): "spine_05"})
        game = {"pelvis": "|pelvis", "spine_05": "|spine_05"}
        self.assertEqual(rigsolve.root_leaf(RIG, game), "spine_05")

    def test_an_anchor_that_follows_nothing_either_falls_back_to_the_pelvis(self):
        self.scene({("|chr|R:Group", "skeldarPartAnchor"): "spine_05"})
        game = {"pelvis": "|pelvis", "spine_05": "|spine_05"}
        self.assertEqual(rigsolve.root_leaf(RIG, game), "pelvis")

    def test_an_anchor_attribute_that_cannot_be_read_is_none(self):
        self.scene({("|chr|R:Group", "skeldarPartAnchor"): RuntimeError("bad attr")})
        self.assertEqual(rigsolve.root_leaf(RIG, {"pelvis": "|pelvis"}), "pelvis")

    def test_no_pelvis_and_no_anchor_is_no_root_bone(self):
        self.scene()
        self.assertIsNone(rigsolve.root_leaf(RIG, {"spine_01": "|s"}))

    def test_a_rig_with_no_group_has_no_anchor(self):
        self.scene()
        self.assertEqual(rigsolve.root_leaf(RIG._replace(group=None), {"pelvis": "|p"}), "pelvis")


class DriveChain(Patched):
    """The drive chain S of a base as the rig shows it: the FKX joint, or the FKX and IKX joints
    blended by the limb's FK/IK weight."""

    FKX, IKX, DEFORM, GAME = "|FKX", "|IKX", "|DEF", "|GAME"

    def setUp(self):
        self.worlds = {self.FKX: trs((0, 0, 0), (0, 0, 0)), self.IKX: trs((10, 0, 0), (0, 0, 90)),
                       self.DEFORM: trs((0, 0, 0)), self.GAME: trs((0, 5, 0), (0, 0, 30))}
        self.patch(rigsolve, "_world", lambda node: self.worlds[node])

    def base(self, **kwargs):
        fields = dict(leaf="upperarm_l", base="Shoulder", side="_L", fk="|FK", fkx=self.FKX,
                      ikx=self.IKX, deform=self.DEFORM, limb="arm")
        fields.update(kwargs)
        return rigsolve.Base(**fields)

    def test_the_blend_is_the_switch_s_value_over_the_ik_value(self):
        self.patch(rigsolve, "_one", lambda rig, leaf: "|switch" if leaf == "FKIKArm_L" else None)
        self.patch(rigsolve, "cmds", SceneCmds(attrs={("|switch", "FKIKBlend"): 2.5}))
        self.assertEqual(rigsolve._blend(RIG, "arm", "_L"), 2.5 / fkik.BLEND[fkik.IK])

    def test_a_rig_without_the_switch_is_all_fk(self):
        self.patch(rigsolve, "_one", lambda rig, leaf: None)
        self.assertEqual(rigsolve._blend(RIG, "leg", "_R"), 0.0)

    def test_a_limb_joint_is_the_fkx_and_ikx_joints_blended_by_the_weight(self):
        self.patch(rigsolve, "_blend", lambda rig, kind, side: 1.0)
        close(self, rigsolve._shown(RIG, self.base()), pm.rigid(self.worlds[self.IKX]), 1e-9)
        self.patch(rigsolve, "_blend", lambda rig, kind, side: 0.0)
        close(self, rigsolve._shown(RIG, self.base()), pm.rigid(self.worlds[self.FKX]), 1e-9)

    def test_a_joint_that_is_no_limb_or_has_no_ikx_is_its_fkx_joint(self):
        self.patch(rigsolve, "_blend", lambda rig, kind, side: self.fail("no blend to ask"))
        for base in (self.base(limb=None), self.base(ikx=None)):
            close(self, rigsolve._shown(RIG, base), pm.rigid(self.worlds[self.FKX]), 1e-9)

    def test_the_drive_is_the_game_bone_turned_as_the_chain_holds_it_at_its_own_place(self):
        self.patch(rigsolve, "_blend", lambda rig, kind, side: 0.0)
        drive = rigsolve._drive(RIG, self.base(), self.GAME)
        expected = rigsolve.drive_of(self.worlds[self.GAME], self.worlds[self.DEFORM],
                                     pm.rigid(self.worlds[self.FKX]))
        close(self, drive, expected, 1e-9)
        self.assertEqual(pm.position(drive).y, 5.0)

    def test_only_the_unrolled_limb_bones_with_a_deform_and_an_fkx_are_drive_matrices(self):
        bases = {
            "upperarm_l": self.base(),
            "hand_l": self.base(leaf="hand_l", base="Wrist"),
            "thigh_l": self.base(leaf="thigh_l", base="Hip", deform=None),
            "calf_l": self.base(leaf="calf_l", base="Knee", fkx=None),
            "lowerarm_l": self.base(leaf="lowerarm_l", base="Elbow"),
        }
        self.patch(rigsolve, "game_bones", lambda rig: {"upperarm_l": "|g1", "hand_l": "|g2",
                                                        "thigh_l": "|g3", "calf_l": "|g4"})
        self.patch(rigsolve, "bases", lambda rig: bases)
        self.patch(rigsolve, "_drive", lambda rig, base, path: om.MMatrix(trs((1, 2, 3))))
        out = rigsolve.drive_matrices(RIG)
        self.assertEqual(list(out), ["upperarm_l"])
        self.assertEqual(out["upperarm_l"], pm.flat(trs((1, 2, 3))))


class Switch(Patched):

    def test_the_scene_is_switched_when_it_is_not_in_the_solve_s_mode(self):
        self.patch(rigsolve, "cmds", SceneCmds(mode=("parallel",)))
        self.assertTrue(rigsolve.switches())
        self.patch(rigsolve, "cmds", SceneCmds(mode=("off",)))
        self.assertFalse(rigsolve.switches())

    def test_a_scene_that_names_no_mode_is_switched(self):
        self.patch(rigsolve, "cmds", SceneCmds(mode=None))
        self.assertTrue(rigsolve.switches())

    def test_with_no_mode_to_switch_to_nothing_is_switched(self):
        self.patch(rigsolve, "cmds", SceneCmds(mode=("parallel",)))
        self.patch(rigsolve, "FRESH_MODE", None)
        self.assertFalse(rigsolve.switches())


class SessionPlaces(Patched):

    def setUp(self):
        self.asked = []
        self.locked = set()

        def writable(plug):
            self.asked.append(plug)
            return (False, "locked") if plug in self.locked else (True, "")

        self.patch(keys, "writable", writable)

    def test_plugs_all_writable_are_writable_and_asked_once_each(self):
        session = rigsolve._Session()
        self.assertTrue(session.writable(["a.tx", "a.ty"]))
        self.assertTrue(session.writable(["a.tx"]))
        self.assertEqual(self.asked, ["a.tx", "a.ty"])

    def test_a_refused_plug_is_not_writable_and_is_not_a_skipped_plug(self):
        self.locked.add("a.ty")
        session = rigsolve._Session()
        self.assertFalse(session.writable(["a.tx", "a.ty", "a.tz"]))
        self.assertEqual(session.skipped, {})
        self.assertEqual(self.asked, ["a.tx", "a.ty"])

    def test_allowed_records_the_refusal_where_writable_does_not(self):
        self.locked.add("a.ty")
        session = rigsolve._Session()
        self.assertFalse(session.allowed(["a.ty"]))
        self.assertEqual(session.skipped, {"a.ty": "locked"})
        self.assertFalse(session.writable(["a.ty"]))
        self.assertEqual(self.asked, ["a.ty"])


class KnotDrivers(Patched):

    CONTROL, CON, KNOT = "|g|FKSpine3_M", "|g|FKSpine3_M|FKSpine3_M_pc", "|k|Chest_1P_ctrl"

    def scene(self, **overrides):
        base = dict(
            children={self.CONTROL: {"parentConstraint": [self.CON, "|g|FKSpine3_M|other_pc"]}},
            attrs={(self.CON, rigsolve.KNOT_OF): "U1", (self.KNOT, rigsolve.KNOT_KIND): "knot"},
            names={"U1": [self.KNOT], self.KNOT: [self.KNOT], "T1": [self.KNOT]},
            targets={self.CON: ["T1"]}, exists=[self.CONTROL])
        base.update(overrides)
        self.patch(rigsolve, "cmds", SceneCmds(**base))

    def test_the_knot_driving_a_control_through_our_one_constraint_is_found(self):
        self.scene()
        self.assertEqual(rigsolve.knot_driver(self.CONTROL), self.KNOT)

    def test_no_control_or_one_that_is_gone_has_no_knot(self):
        self.scene()
        self.assertIsNone(rigsolve.knot_driver(None))
        self.assertIsNone(rigsolve.knot_driver("|gone"))

    def test_a_control_with_no_constraint_of_ours_or_two_has_no_knot(self):
        self.scene(children={self.CONTROL: {"parentConstraint": ["|g|x_pc"]}})
        self.assertIsNone(rigsolve.knot_driver(self.CONTROL))
        self.scene(children={self.CONTROL: {"parentConstraint": [self.CON, "|g|b"]}},
                   attrs={(self.CON, rigsolve.KNOT_OF): "U1", ("|g|b", rigsolve.KNOT_OF): "U1",
                          (self.KNOT, rigsolve.KNOT_KIND): "knot"})
        self.assertIsNone(rigsolve.knot_driver(self.CONTROL))

    def test_a_constraint_naming_no_node_or_two_has_no_knot(self):
        self.scene(names={"U1": []})
        self.assertIsNone(rigsolve.knot_driver(self.CONTROL))
        self.scene(names={"U1": [self.KNOT, "|other"]})
        self.assertIsNone(rigsolve.knot_driver(self.CONTROL))

    def test_a_node_that_is_not_a_plain_knot_drives_nothing(self):
        self.scene(attrs={(self.CON, rigsolve.KNOT_OF): "U1", (self.KNOT, rigsolve.KNOT_KIND): "snapshot"})
        self.assertIsNone(rigsolve.knot_driver(self.CONTROL))
        self.scene(attrs={(self.CON, rigsolve.KNOT_OF): "U1"})
        self.assertIsNone(rigsolve.knot_driver(self.CONTROL))

    def test_a_constraint_that_follows_something_else_than_the_knot_has_no_knot(self):
        self.scene(targets={self.CON: ["T2"]}, names={"U1": [self.KNOT], "T2": ["|elsewhere"]})
        self.assertIsNone(rigsolve.knot_driver(self.CONTROL))

    def test_a_scene_that_cannot_be_asked_has_no_knot(self):
        class Broken(object):
            def objExists(self, node):
                raise RuntimeError("no scene")

        self.patch(rigsolve, "cmds", Broken())
        self.assertIsNone(rigsolve.knot_driver(self.CONTROL))


class SpineBlend(Patched):

    def test_the_weight_is_the_switch_s_value_over_the_ik_value(self):
        self.patch(rigsolve, "_one", lambda rig, leaf: "|switch" if leaf == rigsolve.SPINE_SWITCH else None)
        self.patch(rigsolve, "cmds", SceneCmds(attrs={("|switch", "FKIKBlend"): 10.0}))
        self.assertEqual(rigsolve._spine_weight(RIG), 1.0)

    def test_a_rig_without_the_spine_switch_is_all_fk(self):
        self.patch(rigsolve, "_one", lambda rig, leaf: None)
        self.assertEqual(rigsolve._spine_weight(RIG), 0.0)


class MeasureRows(Patched):

    def bases(self):
        return {
            "upperarm_l": rigsolve.Base("upperarm_l", "Shoulder", "_L", "|FK1", "|FKX1", "|IKX1",
                                        "|D1", "arm"),
            "lowerarm_l": rigsolve.Base("lowerarm_l", "Elbow", "_L", "|FK2", "|FKX2", "|IKX2",
                                        "|D2", "arm"),
            "hand_l": rigsolve.Base("hand_l", "Wrist", "_L", "|FK3", "|FKX3", None, "|D3", "arm"),
            "pelvis": rigsolve.Base("pelvis", "Root", "_M", "|RootX", None, None, "|D0", None),
        }

    GAME = {"upperarm_l": "|g1", "lowerarm_l": "|g2", "hand_l": "|g3", "pelvis": "|g0"}

    def setUp(self):
        self.patch(rigsolve, "_drive",
                   lambda rig, base, path: om.MMatrix(trs((0, 0, {"|g1": 0, "|g2": 10}[path]))))
        self.patch(rigsolve, "_world", lambda node: trs((1, 2, 3)))

    def rows(self, wanted, members, placed=()):
        return rigsolve._rows(RIG, self.bases(), self.GAME, wanted, members, placed)

    def test_an_unrolled_bone_is_read_in_drive_form_with_the_direction_to_its_child(self):
        rows = self.rows({"upperarm_l": trs()}, ["upperarm_l"])
        leaf, actual, _wanted, direction, placed = rows[0]
        self.assertEqual(leaf, "upperarm_l")
        self.assertEqual(pm.position(actual).z, 0.0)
        self.assertEqual(tuple(round(v, 9) for v in direction), (0.0, 0.0, 10.0))
        self.assertFalse(placed)

    def test_any_other_bone_is_its_game_bone_s_whole_turn_with_no_direction(self):
        rows = self.rows({"hand_l": trs()}, ["hand_l"])
        _leaf, actual, _wanted, direction, _placed = rows[0]
        self.assertIsNone(direction)
        self.assertEqual((pm.position(actual).x, pm.position(actual).y), (1.0, 2.0))

    def test_the_root_and_the_placed_members_are_measured_by_their_place_too(self):
        rows = self.rows({"pelvis": trs(), "hand_l": trs()}, ["pelvis", "hand_l"], placed=["hand_l"])
        self.assertEqual([row[4] for row in rows], [True, True])

    def test_a_member_with_no_target_no_game_bone_or_no_base_is_not_measured(self):
        rows = self.rows({"hand_l": trs(), "ghost": trs()}, ["upperarm_l", "hand_l", "ghost"])
        self.assertEqual([row[0] for row in rows], ["hand_l"])

    def test_the_solver_measures_its_leaves_against_the_targets_with_namespaces_dropped(self):
        seen = []
        self.patch(rigsolve, "_rows", lambda rig, bases, game, wanted, leaves, placed: seen.append(
            (rig, bases, game, wanted, leaves, placed)) or [("hand_l", trs(), trs(), None, True)])
        solver = rigsolve.Solver.__new__(rigsolve.Solver)
        solver.rig, solver.bases, solver.game = "the rig", "bases", "game"
        solver.leaves, solver.placed = ["hand_l"], {"hand_l"}
        self.assertEqual(solver.measure({"R:hand_l": trs((0, 0, 7))}), (0.0, 0.0, "hand_l"))
        self.assertEqual(list(seen[0][3]), ["hand_l"])
        close(self, seen[0][3]["hand_l"], pm.rigid(trs((0, 0, 7))), 1e-9)

    def test_a_solver_with_nothing_wanted_measures_nothing(self):
        self.patch(rigsolve, "_rows", lambda *args: [])
        solver = rigsolve.Solver.__new__(rigsolve.Solver)
        solver.rig, solver.bases, solver.game, solver.leaves, solver.placed = None, {}, {}, [], set()
        self.assertEqual(solver.measure(None), (0.0, 0.0, None))

    def test_the_measure_is_the_solver_s_for_the_members_and_places_given(self):
        made = []

        class FakeSolver(object):
            def __init__(self, rig, members, placed=()):
                made.append((rig, members, placed))

            def measure(self, wanted):
                return ("measured", wanted)

        self.patch(rigsolve, "Solver", FakeSolver)
        self.assertEqual(rigsolve.measure("rig", {"a": 1}, ["hand_l"], ("pelvis",)),
                         ("measured", {"a": 1}))
        self.assertEqual(made, [("rig", ["hand_l"], ("pelvis",))])


def job(**fields):
    """A `_Job` built without a solver: only the fields a test sets."""
    made = rigsolve._Job.__new__(rigsolve._Job)
    made.session = rigsolve._Session()
    made.notes = rigsolve.OrderedDict()
    for name, value in fields.items():
        setattr(made, name, value)
    return made


class JobTargets(Patched):
    """Where a base's drive chain should stand, and which half of a limb takes a pose."""

    def test_a_wanted_bone_s_chain_stands_where_its_offset_undone_puts_it(self):
        offset = trs((0, 5, 0), (0, 0, 30))
        wanted = trs((1, 2, 3), (0, 40, 0))
        made = job(wanted={"hand_l": wanted}, offset={"hand_l": offset}, shown={})
        close(self, made.target("hand_l"), offset.inverse() * wanted, 1e-9)

    def test_a_bone_with_no_target_or_no_offset_stands_as_it_is_shown(self):
        shown = trs((7, 7, 7))
        made = job(wanted={"hand_l": trs()}, offset={}, shown={"hand_l": shown, "head": shown})
        self.assertIs(made.target("hand_l"), shown)
        self.assertIs(made.target("head"), shown)
        self.assertIsNone(made.target("nothing"))

    def test_a_limb_is_half_blended_with_only_part_of_its_chain_posed(self):
        made = job(limbs={("arm", "L"): {}}, blends={("arm", "L"): 0.5}, member_set={"hand_l"})
        self.assertTrue(made.half_blended(("arm", "L")))

    def test_a_limb_whose_whole_chain_is_posed_is_not_half_blended(self):
        chain = {"upperarm_l", "lowerarm_l", "hand_l"}
        made = job(limbs={("arm", "L"): {}}, blends={("arm", "L"): 0.5}, member_set=chain)
        self.assertFalse(made.half_blended(("arm", "L")))

    def test_a_limb_shown_all_fk_or_all_ik_or_not_posed_is_not_half_blended(self):
        for weight in (0.0, 1.0):
            made = job(limbs={("arm", "L"): {}}, blends={("arm", "L"): weight},
                       member_set={"hand_l"})
            self.assertFalse(made.half_blended(("arm", "L")), weight)
        made = job(limbs={}, blends={("arm", "L"): 0.5}, member_set={"hand_l"})
        self.assertFalse(made.half_blended(("arm", "L")))
        made = job(limbs={("arm", "L"): {}}, blends={}, member_set={"hand_l"})
        self.assertFalse(made.half_blended(("arm", "L")))

    def test_a_centre_bone_or_a_limb_not_half_blended_keeps_the_plain_target(self):
        aim = trs((1, 2, 3))
        made = job(wanted={}, offset={}, shown={"head": aim, "hand_l": aim}, limbs={}, blends={},
                   member_set=set(), bases={})
        self.assertIs(made.target_fk("head"), aim)
        self.assertIs(made.target_fk("hand_l"), aim)
        self.assertIsNone(made.target_fk("nothing"))

    def test_on_a_half_blended_limb_a_bone_takes_the_pose_relative_to_its_fkx_parent(self):
        upper_target, hand_target = trs((0, 0, 0), (0, 0, 30)), trs((10, 0, 0), (0, 0, 70))
        fkx_parent = trs((0, 0, 0), (0, 0, 10))
        self.patch(rigsolve, "_world", lambda node: fkx_parent)
        base = rigsolve.Base("lowerarm_l", "Elbow", "_L", "|FK", "|FKX", None, "|D", "arm")
        made = job(wanted={}, offset={}, shown={"hand_l": hand_target, "lowerarm_l": upper_target},
                   limbs={("arm", "L"): {}}, blends={("arm", "L"): 0.5}, member_set={"hand_l"},
                   bases={"lowerarm_l": base})
        close(self, made.target_fk("hand_l"),
              hand_target * upper_target.inverse() * pm.rigid(fkx_parent), 1e-9)

    def test_a_half_blended_limb_whose_parent_has_no_fkx_keeps_the_plain_target(self):
        hand_target = trs((10, 0, 0))
        made = job(wanted={}, offset={}, shown={"hand_l": hand_target, "lowerarm_l": trs()},
                   limbs={("arm", "L"): {}}, blends={("arm", "L"): 0.5}, member_set={"hand_l"},
                   bases={})
        self.assertIs(made.target_fk("hand_l"), hand_target)


class JobSmallReads(Patched):

    def test_a_limb_follows_its_fk_half_only_while_it_shows_fk(self):
        base = rigsolve.Base("hand_l", "Wrist", "_L", "|FK", "|FKX", "|IKX", "|D", "arm")
        made = job(rig=RIG, bases={"hand_l": base})
        for weight, shows in ((0.0, True), (0.5, False), (1.0, False)):
            self.patch(rigsolve, "_blend", lambda rig, kind, side, weight=weight: weight)
            self.assertIs(made._shows_fk("hand_l"), shows, weight)

    def test_the_spine_follows_its_fk_half_only_while_it_shows_fk(self):
        base = rigsolve.Base("spine_02", "Spine2", "_M", "|FK", "|FKX", None, "|D", None)
        made = job(rig=RIG, bases={"spine_02": base})
        self.patch(rigsolve, "_spine_weight", lambda rig: 0.0)
        self.assertTrue(made._shows_fk("spine_02"))
        self.patch(rigsolve, "_spine_weight", lambda rig: 1.0)
        self.assertFalse(made._shows_fk("spine_02"))

    def test_any_other_bone_follows_its_fk_control(self):
        base = rigsolve.Base("head", "Head", "_M", "|FK", "|FKX", None, "|D", None)
        self.assertTrue(job(rig=RIG, bases={"head": base})._shows_fk("head"))

    def test_the_levels_are_the_members_but_the_pelvis_and_the_ends_of_the_limbs_they_touch(self):
        game = {"pelvis": "|r|pelvis", "spine_01": "|r|pelvis|spine_01",
                "thigh_l": "|r|pelvis|thigh_l", "foot_l": "|r|pelvis|thigh_l|calf_l|foot_l"}
        made = job(ik={("leg", "l"): {"game": ("thigh_l", "calf_l", "foot_l")}, ("arm", "l"): None},
                   game=game, members=["pelvis", "spine_01", "thigh_l"], pelvis="pelvis")
        made.plan_levels()
        self.assertEqual(made.ends, {"foot_l": [("leg", "l")]})
        self.assertEqual(made.levels, [["spine_01", "thigh_l"], ["foot_l"]])

    def test_an_end_the_skeleton_lacks_is_not_a_level(self):
        made = job(ik={("leg", "l"): {"game": ("thigh_l", "calf_l", "foot_l")}},
                   game={"thigh_l": "|r|thigh_l"}, members=["thigh_l"], pelvis="pelvis")
        made.plan_levels()
        self.assertEqual(made.levels, [["thigh_l"]])

    def test_the_rows_are_the_measure_rows_of_the_job_s_members(self):
        seen = []
        self.patch(rigsolve, "_rows", lambda *args: seen.append(args) or "rows")
        made = job(rig="rig", bases="bases", game="game", wanted="wanted", members=["m"],
                   placed={"m"})
        self.assertEqual(made.rows(), "rows")
        self.assertEqual(seen, [("rig", "bases", "game", "wanted", ["m"], {"m"})])


class HoldCmds(object):
    """A node's attributes with defaults, and the plug values a session reads and sets."""

    def __init__(self, defaults, values=None):
        self.defaults = defaults
        self.values = dict(values or {})
        self.sets = []

    def attributeQuery(self, name, node=None, exists=False, listDefault=False):
        if exists:
            return name in self.defaults
        return self.defaults[name]

    def getAttr(self, plug):
        return self.values.get(plug, 0.0)

    def setAttr(self, plug, value):
        self.sets.append((plug, value))
        self.values[plug] = value


class JobWrites(Patched):
    """What a frame's solve writes through its session: the attributes held at their defaults,
    an FK control turned (and placed), the toes and the spine's twist."""

    def setUp(self):
        self.locked = set()
        self.patch(keys, "writable", lambda plug: (False, "locked") if plug in self.locked else (True, ""))

    def test_the_named_attributes_are_set_to_their_defaults(self):
        fake = HoldCmds({"roll": [0.0], "rock": [2.5]}, {"|IKLeg_L.roll": 30.0, "|IKLeg_L.rock": -4.0})
        self.patch(rigsolve, "cmds", fake)
        made = job()
        made._hold_default("|IKLeg_L", ("roll", "rock", "missing"))
        self.assertEqual(fake.sets, [("|IKLeg_L.roll", 0.0), ("|IKLeg_L.rock", 2.5)])
        self.assertEqual(dict(made.session.last), {"|IKLeg_L.roll": 0.0, "|IKLeg_L.rock": 2.5})
        self.assertEqual(dict(made.session.original), {"|IKLeg_L.roll": 30.0, "|IKLeg_L.rock": -4.0})

    def test_a_locked_attribute_or_no_node_is_left_alone(self):
        fake = HoldCmds({"roll": [0.0]})
        self.patch(rigsolve, "cmds", fake)
        self.locked.add("|IKLeg_L.roll")
        made = job()
        made._hold_default("|IKLeg_L", ("roll",))
        made._hold_default(None, ("roll",))
        self.assertEqual(fake.sets, [])

    def test_an_attribute_with_no_listed_default_is_held_at_zero(self):
        fake = HoldCmds({"roll": []}, {"|IKLeg_L.roll": 9.0})
        self.patch(rigsolve, "cmds", fake)
        job()._hold_default("|IKLeg_L", ("roll",))
        self.assertEqual(fake.sets, [("|IKLeg_L.roll", 0.0)])

    def test_the_spine_s_twist_is_the_worst_turn_of_the_members_the_spline_carries(self):
        wanted = {"spine_01": trs(), "spine_02": trs(), "spine_03": trs(), "pelvis": trs((0, 0, 0), (0, 0, 80))}
        game = dict((leaf, "|" + leaf) for leaf in ("spine_01", "spine_02", "spine_03", "pelvis"))
        turns = {"|spine_01": 10, "|spine_02": 35, "|spine_03": 20, "|pelvis": 80}
        self.patch(rigsolve, "_world", lambda node: trs((0, 0, 0), (0, 0, turns[node])))
        made = job(member_set={"spine_01", "spine_02", "spine_03", "pelvis"}, wanted=wanted, game=game)
        deg, leaf = made._spine_twist()
        self.assertAlmostEqual(deg, 35.0, 6)
        self.assertEqual(leaf, "spine_02")

    def test_a_spine_bone_that_is_no_member_or_has_no_target_or_game_bone_is_not_measured(self):
        self.patch(rigsolve, "_world", lambda node: trs((0, 0, 0), (0, 0, 50)))
        made = job(member_set={"spine_01", "spine_02"}, wanted={"spine_01": trs()},
                   game={"spine_01": "|spine_01", "spine_02": "|spine_02"})
        self.assertEqual(made._spine_twist()[1], "spine_01")
        made = job(member_set={"spine_01"}, wanted={"spine_01": trs()}, game={})
        self.assertEqual(made._spine_twist(), (0.0, None))


class JobFk(Patched):
    """An FK control onto its target: analytic when its FKX joint stands below it, else numeric on
    the deformation joint."""

    def setUp(self):
        self.calls = []

    def made(self, base, aim, **fields):
        made = job(bases={base.leaf: base}, member_set={base.leaf}, in_control={}, **fields)
        made.target_fk = lambda leaf: aim
        made._turn = lambda node, turn: self.calls.append(("turn", node, turn))
        made._numeric = lambda node, joint, turn, after=(): self.calls.append(
            ("numeric", node, joint, list(after)))
        made._place = lambda leaf, after=(): self.calls.append(("place", leaf, list(after)))
        made._knot_place = lambda leaf: self.calls.append(("knot", leaf))
        return made

    def test_a_bone_with_no_target_or_no_control_is_left(self):
        base = rigsolve.Base("hand_l", "Wrist", "_L", "|FK", "|FKX", None, "|D", "arm")
        self.made(base, None)._fk("hand_l")
        self.made(base._replace(fk=None), trs())._fk("hand_l")
        self.assertEqual(self.calls, [])

    def test_a_control_with_its_fkx_joint_below_it_is_turned_by_the_relation_undone_then_placed(self):
        base = rigsolve.Base("hand_l", "Wrist", "_L", "|FK", "|FKX", None, "|D", "arm")
        relation, aim = trs((0, 0, 0), (0, 0, 20)), trs((0, 0, 0), (0, 0, 50))
        made = self.made(base, aim)
        made.in_control = {"hand_l": relation}
        made._fk("hand_l")
        self.assertEqual([call[:2] for call in self.calls],
                         [("turn", "|FK"), ("place", "hand_l"), ("knot", "hand_l")])
        close(self, self.calls[0][2], relation.inverse() * aim, 1e-9)

    def test_any_other_control_is_solved_numerically_on_the_deformation_joint(self):
        base = rigsolve.Base("head", "Head", "_M", "|FK", "|FKX", None, "|D", None)
        self.made(base, trs())._fk("head")
        self.assertEqual(self.calls, [("numeric", "|FK", "|D", []), ("place", "head", [])])

    def test_a_base_with_no_deformation_joint_uses_its_fkx_joint_and_with_neither_nothing(self):
        base = rigsolve.Base("head", "Head", "_M", "|FK", "|FKX", None, None, None)
        self.made(base, trs())._fk("head")
        self.assertEqual(self.calls[0], ("numeric", "|FK", "|FKX", []))
        self.calls[:] = []
        self.made(base._replace(fkx=None), trs())._fk("head")
        self.assertEqual(self.calls, [])

    def test_the_neck_that_shares_the_head_s_twist_re_solves_the_head_inside_its_probes(self):
        neck = rigsolve.Base("neck_02", "NeckPart1", "_M", "|FKN", "|FKXN", None, "|DN", None)
        head = rigsolve.Base("head", "Head", "_M", "|FKH", "|FKXH", None, "|DH", None)
        made = self.made(neck, trs())
        made.bases["head"] = head
        made.member_set.add("head")
        made.in_control = {"neck_02": trs(), "head": trs()}
        made._fk("neck_02")
        self.assertEqual(self.calls, [("numeric", "|FKN", "|DN", ["head"]), ("place", "neck_02", ["head"])])


class JobToes(Patched):

    INFO = {"toes": "|IKToes", "toes_rel": trs(), "toes_joint": "|IKXToes",
            "game": ("thigh_l", "calf_l", "foot_l", "ball_l")}

    def made(self, targets, turned=True, blend=1.0, joint_turn=0.0):
        self.numeric = []
        made = job(blends={("leg", "l"): blend})
        made.target = lambda leaf: targets.get(leaf)
        made._turn = lambda node, turn: turned
        made._numeric = lambda node, joint, turn: self.numeric.append((node, joint))
        self.patch(rigsolve, "_world", lambda node: trs((0, 0, 0), (0, 0, joint_turn)))
        return made

    def test_the_toes_land_the_ball_s_target_and_the_numeric_solve_finishes_it(self):
        made = self.made({"ball_l": trs()})
        made._toes(("leg", "l"), self.INFO)
        self.assertEqual(self.numeric, [("|IKToes", "|IKXToes")])
        self.assertEqual(made.notes, rigsolve.OrderedDict())

    def test_a_turn_out_of_reach_with_the_leg_shown_in_ik_is_said(self):
        made = self.made({"ball_l": trs()}, joint_turn=40.0)
        made._toes(("leg", "l"), self.INFO)
        self.assertEqual(made.notes["toes leg l"],
                         "the IK toes do not reach the ball's turn on leg_l: 40 deg")

    def test_a_turn_out_of_reach_with_the_leg_shown_in_fk_is_not_said(self):
        made = self.made({"ball_l": trs()}, blend=0.0, joint_turn=40.0)
        made._toes(("leg", "l"), self.INFO)
        self.assertNotIn("toes leg l", made.notes)

    def test_an_old_note_is_cleared_first(self):
        made = self.made({"ball_l": trs()})
        made.notes["toes leg l"] = "an old note"
        made._toes(("leg", "l"), self.INFO)
        self.assertNotIn("toes leg l", made.notes)

    def test_no_ball_target_or_toes_that_cannot_be_turned_solves_nothing(self):
        self.made({})._toes(("leg", "l"), self.INFO)
        self.assertEqual(self.numeric, [])
        self.made({"ball_l": trs()}, turned=False)._toes(("leg", "l"), self.INFO)
        self.assertEqual(self.numeric, [])

    def test_a_foot_given_puts_the_ball_in_its_relation_to_that_foot(self):
        ball, shown_foot, foot = trs((0, 0, 5)), trs((0, 0, 0), (0, 0, 10)), trs((0, 0, 0), (0, 0, 30))
        seen = []
        made = self.made({"ball_l": ball, "foot_l": shown_foot})
        made._turn = lambda node, turn: seen.append(turn) or True
        made._toes(("leg", "l"), self.INFO, foot)
        close(self, seen[0], ball * shown_foot.inverse() * foot, 1e-9)


class GuardCmds(object):
    """The IK solve attributes of a few nodes: {node: {attr: (value, default)}}."""

    def __init__(self, nodes):
        self.nodes = nodes

    def listAttr(self, node, userDefined=False):
        return list(self.nodes[node])

    def attributeQuery(self, name, node=None, exists=False, listDefault=False):
        if exists:
            return name in self.nodes[node]
        return [self.nodes[node][name][1]]

    def getAttr(self, plug):
        node, name = plug.rsplit(".", 1)
        return self.nodes[node][name][0]


class IkGuard(Patched):

    def test_an_ik_end_whose_anti_pop_is_off_its_default_is_named(self):
        self.patch(rigsolve, "cmds", GuardCmds({"|IKArm_L": {"antiPop": (0.0, 1.0)}}))
        self.assertEqual(rigsolve._Job._guard("|IKArm_L", None), ["IKArm_L.antiPop"])

    def test_attributes_at_their_defaults_are_no_guard(self):
        self.patch(rigsolve, "cmds", GuardCmds({
            "|IKArm_L": {"antiPop": (1.0, 1.0)},
            "|PoleArm_L": {"follow": (0.0, 0.0), "lock": (0.0, 0.0)}}))
        self.assertEqual(rigsolve._Job._guard("|IKArm_L", "|PoleArm_L"), [])

    def test_a_pole_s_follow_and_lock_attributes_are_guarded_by_prefix(self):
        self.patch(rigsolve, "cmds", GuardCmds({"|IKArm_L": {}, "|PoleArm_L": {
            "follow": (1.0, 0.0), "lock": (0.0, 0.0), "other": (5.0, 0.0)}}))
        self.assertEqual(rigsolve._Job._guard("|IKArm_L", "|PoleArm_L"), ["PoleArm_L.follow"])

    def test_a_limb_with_no_ik_end_or_pole_has_no_guard(self):
        self.patch(rigsolve, "cmds", GuardCmds({}))
        self.assertEqual(rigsolve._Job._guard(None, None), [])


class Hinge(Patched):

    BASE = rigsolve.Base("upperarm_l", "Shoulder", "_L", "|FK", "|FKX", "|IKX", "|D", "arm")

    def made(self, blend, pole=True, key=("arm", "l")):
        return job(blends={key: blend}, limbs={key: {"pole": pole}},
                   notes=rigsolve.OrderedDict([("hinge %s %s" % key, "an old note")]))

    def chain(self, ikx=True):
        base = self.BASE if ikx else self.BASE._replace(ikx=None)
        return {"chain": [base, base, base]}

    def test_an_ik_limb_whose_chain_turned_past_the_tolerance_says_the_twist_is_lost(self):
        self.patch(rigsolve, "_world", lambda node: trs((0, 0, 0), (0, 0, 30)))
        made = self.made(1.0)
        made._hinge(("arm", "l"), self.chain(), [trs(), trs(), trs()])
        self.assertEqual(made.notes["hinge arm l"],
                         "the FK forearm twist is lost on arm_l (an IK elbow is a hinge): 30 deg")

    def test_a_leg_names_the_calf_and_the_knee(self):
        self.patch(rigsolve, "_world", lambda node: trs((0, 0, 0), (0, 0, 20)))
        made = self.made(1.0, key=("leg", "r"))
        made._hinge(("leg", "r"), self.chain(), [trs(), trs(), trs()])
        self.assertEqual(made.notes["hinge leg r"],
                         "the FK calf twist is lost on leg_r (an IK knee is a hinge): 20 deg")

    def test_a_chain_within_the_tolerance_says_nothing_and_clears_the_old_note(self):
        self.patch(rigsolve, "_world", lambda node: trs())
        made = self.made(1.0)
        made._hinge(("arm", "l"), self.chain(), [trs(), trs(), trs()])
        self.assertNotIn("hinge arm l", made.notes)

    def test_a_limb_shown_in_fk_or_with_no_pole_posed_or_no_ikx_says_nothing(self):
        self.patch(rigsolve, "_world", lambda node: trs((0, 0, 0), (0, 0, 30)))
        for made, chain in ((self.made(0.0), self.chain()), (self.made(1.0, pole=False), self.chain()),
                            (self.made(1.0), self.chain(ikx=False))):
            made._hinge(("arm", "l"), chain, [trs(), trs(), trs()])
            self.assertNotIn("hinge arm l", made.notes)


if __name__ == "__main__":
    unittest.main()
