"""The Pose Library's Apply (2026-10-02): blend, the status line, which characters, objects,
the native rebuild - and the order of a press against a fake scene.

The animator: «Выделив наши объекты мы можем применить на них карточку ... достаточно выделить
любую часть скелета или рига нажать apply ... Поза должна накладываться на текущий активный
анимационный слой». The pure halves (`mix`, `summary`, `choose_targets`, `pair_objects`,
`unpaired`, `target_members`, `rebuild_joints`, `shown_notes`) run on plain data; the press's
frame (`apply`, `Blend`) runs on a fake `cmds` and fake `keys` / `_plan` rebound as module
attributes (CLAUDE.md's rule) and restored in `tearDown`. The scene half is
docs/superpowers/plans/verify_poselib_apply.py (mayapy standalone).
"""

import contextlib
import math
import unittest
from collections import OrderedDict

import maya.api.OpenMaya as om

from maya_poselib import apply as ap
from maya_poselib import keys as real_keys
from maya_poselib import rigsolve
from maya_poselib import scene


def quat(euler, order=0):
    return om.MEulerRotation(*([math.radians(v) for v in euler] + [order])).asQuaternion()


def qangle(a, b):
    """Degrees between two quaternions, the short way."""
    d = a.inverse() * b
    v = math.sqrt(d.x * d.x + d.y * d.y + d.z * d.z)
    return math.degrees(2.0 * math.atan2(v, abs(d.w)))


def rot(node, order=0):
    return {node: (node + ".rotateX", node + ".rotateY", node + ".rotateZ", order)}


def triple(values, node):
    return tuple(values[node + "." + a] for a in ("rotateX", "rotateY", "rotateZ"))


# ------------------------------------------------------------------ mix

class Mix(unittest.TestCase):

    def test_alpha_one_is_the_final_values_exactly(self):
        current = {"a.rotateX": 10.0, "a.rotateY": 20.0, "a.rotateZ": 30.0, "a.translateX": 1.0}
        final = {"a.rotateX": 11.123456789, "a.rotateY": -5.5, "a.rotateZ": 99.0,
                 "a.translateX": 7.25}
        self.assertEqual(ap.mix(current, final, 1.0, rot("a")), final)
        self.assertEqual(ap.mix(current, final, 1.7, rot("a")), final)

    def test_alpha_zero_is_the_current_values_exactly(self):
        current = {"a.rotateX": 10.0, "a.rotateY": 20.0, "a.rotateZ": 30.0, "a.translateX": 1.0}
        final = {"a.rotateX": 50.0, "a.rotateY": -5.5, "a.rotateZ": 99.0, "a.translateX": 7.25}
        self.assertEqual(ap.mix(current, final, 0.0, rot("a")), current)
        self.assertEqual(ap.mix(current, final, -0.3, rot("a")), current)

    def test_translations_and_scalars_are_lerped(self):
        got = ap.mix({"a.translateX": 2.0, "a.weight": 0.0}, {"a.translateX": 6.0,
                                                               "a.weight": 10.0}, 0.25, {})
        self.assertAlmostEqual(got["a.translateX"], 3.0, places=12)
        self.assertAlmostEqual(got["a.weight"], 2.5, places=12)

    def test_one_axis_turn_halfway(self):
        got = ap.mix({"a.rotateX": 0.0, "a.rotateY": 0.0, "a.rotateZ": 0.0},
                     {"a.rotateX": 90.0, "a.rotateY": 0.0, "a.rotateZ": 0.0}, 0.5, rot("a"))
        for value, want in zip(triple(got, "a"), (45.0, 0.0, 0.0)):
            self.assertAlmostEqual(value, want, places=9)

    def test_a_rotation_goes_the_quaternion_way_in_every_rotate_order(self):
        # the turn from current is `alpha` of the turn to final, and the rest of the way is
        # the rest of it: a geodesic, which per-channel lerp of two eulers is not
        for order in range(6):
            c, f = (12.0, -40.0, 70.0), (-35.0, 25.0, 140.0)
            current = dict(zip(("a.rotateX", "a.rotateY", "a.rotateZ"), c))
            final = dict(zip(("a.rotateX", "a.rotateY", "a.rotateZ"), f))
            for alpha in (0.2, 0.5, 0.9):
                got = triple(ap.mix(current, final, alpha, rot("a", order)), "a")
                q0, q1, q = quat(c, order), quat(f, order), quat(got, order)
                whole = qangle(q0, q1)
                self.assertAlmostEqual(qangle(q0, q), alpha * whole, places=7, msg=order)
                self.assertAlmostEqual(qangle(q, q1), (1 - alpha) * whole, places=7, msg=order)

    def test_the_short_way_and_the_euler_nearest_the_current_one(self):
        # 170 -> -170 is 20 degrees through 180, not 340 the other way; written nearest 170
        got = ap.mix({"a.rotateX": 170.0, "a.rotateY": 0.0, "a.rotateZ": 0.0},
                     {"a.rotateX": -170.0, "a.rotateY": 0.0, "a.rotateZ": 0.0}, 0.5, rot("a"))
        self.assertAlmostEqual(triple(got, "a")[0], 180.0, places=7)
        # a wound channel stays wound: 730 -> 740 halfway is 735, not 15
        got = ap.mix({"a.rotateX": 730.0, "a.rotateY": 0.0, "a.rotateZ": 0.0},
                     {"a.rotateX": 740.0, "a.rotateY": 0.0, "a.rotateZ": 0.0}, 0.5, rot("a"))
        self.assertAlmostEqual(triple(got, "a")[0], 735.0, places=7)

    def test_a_rotate_channel_without_its_two_brothers_is_lerped(self):
        got = ap.mix({"a.rotateX": 0.0}, {"a.rotateX": 90.0}, 0.5, rot("a"))
        self.assertAlmostEqual(got["a.rotateX"], 45.0, places=12)

    def test_a_plug_with_no_current_value_lands_on_its_final_one(self):
        got = ap.mix({}, {"a.translateX": 4.0}, 0.5, {})
        self.assertEqual(got, {"a.translateX": 4.0})

    def test_the_answer_holds_the_final_plugs_in_their_order(self):
        final = OrderedDict([("b.translateX", 1.0), ("a.rotateX", 1.0), ("a.rotateY", 1.0),
                             ("a.rotateZ", 1.0), ("c.v", 1.0)])
        current = dict((p, 0.0) for p in final)
        self.assertEqual(list(ap.mix(current, final, 0.5, rot("a"))), list(final))


# ------------------------------------------------------------------ the status line

def result(**kw):
    base = dict(name="Fist", target="Manny_Rig1", count=23, noun="controls", layer="AnimLayer1",
                frame=12.0, worst=(0.003, 0.0), notes=[], alpha=1.0, mirror=False)
    base.update(kw)
    return ap.Result(**base)


class Summary(unittest.TestCase):

    def test_the_spec_line(self):
        self.assertEqual(
            ap.summary([result(notes=["the FK forearm twist is lost on arm_r (31 deg)"])]),
            "Fist onto Manny_Rig1: 23 controls keyed on AnimLayer1 at frame 12 - worst 0.003 "
            "deg | the FK forearm twist is lost on arm_r (31 deg)")

    def test_no_layers_at_all_says_no_layer(self):
        self.assertEqual(ap.summary([result(layer=None)]),
                         "Fist onto Manny_Rig1: 23 controls keyed at frame 12 - worst 0.003 deg")

    def test_several_targets_are_joined(self):
        text = ap.summary([result(), result(target="Creep_Rig", count=1, worst=None,
                                            notes=["no hand_l on Creep_Rig"])])
        self.assertEqual(text, "Fist onto Manny_Rig1: 23 controls keyed on AnimLayer1 at frame "
                               "12 - worst 0.003 deg | Fist onto Creep_Rig: 1 control keyed on "
                               "AnimLayer1 at frame 12 | no hand_l on Creep_Rig")

    def test_a_place_is_said_when_it_is_off(self):
        self.assertIn("worst 0.012 deg / 0.03 cm", ap.summary([result(worst=(0.012, 0.03))]))
        self.assertNotIn("cm", ap.summary([result(worst=(0.012, 0.0001))]))

    def test_mirrored_and_blended(self):
        text = ap.summary([result(mirror=True, alpha=0.5, worst=None, noun="joints",
                                  frame=3.5)])
        self.assertEqual(text, "Fist mirrored at 50 % onto Manny_Rig1: 23 joints keyed on "
                               "AnimLayer1 at frame 3.5")

    def test_nothing_keyed(self):
        self.assertEqual(ap.summary([result(count=0, notes=["2 not keyed (locked): a, b"])]),
                         "Fist onto Manny_Rig1: nothing keyed | 2 not keyed (locked): a, b")

    def test_the_rigs_own_twist_bones_are_not_news(self):
        driven = "16 member(s) are driven on a rig (twist and helper bones): a, b and 14 more"
        kept = ["the FK forearm twist is lost on arm_r (an IK elbow is a hinge): 31 deg"]
        self.assertEqual(ap.shown_notes([driven] + kept), kept)
        self.assertEqual(ap.shown_notes(["no hand_l on Creep_Rig"]), ["no hand_l on Creep_Rig"])

    def test_the_driven_note_is_matched_on_rigsolves_own_phrase(self):
        # the phrase is rigsolve's constant, not a slice of its format string: the note rigsolve
        # makes is the one dropped, however its format changes around the phrase
        self.assertIn(rigsolve.DRIVEN_PHRASE, rigsolve.DRIVEN)
        self.assertEqual(ap.shown_notes([rigsolve.DRIVEN % (3, "a, b, c")]), [])
        self.assertEqual(ap._QUIET, rigsolve.DRIVEN_PHRASE)

    def test_the_worst_angle_has_four_decimals(self):
        # «worst 0 deg» on most lines with 3 decimals said nothing (task 7's concern 7)
        self.assertIn("- worst 0.0007 deg", ap.summary([result(worst=(0.00068, 0.0))]))
        self.assertIn("- worst 0.0123 deg / 0.03 cm",
                      ap.summary([result(worst=(0.012345, 0.03))]))

    def test_a_worst_angle_below_half_a_thousandth_is_not_said(self):
        self.assertEqual(ap.summary([result(worst=(0.0004, 0.0))]),
                         "Fist onto Manny_Rig1: 23 controls keyed on AnimLayer1 at frame 12")
        # ... while a place worth a word still is
        self.assertIn("at frame 12 - worst 0.03 cm", ap.summary([result(worst=(0.0004, 0.03))]))


# ------------------------------------------------------------------ which characters

def ref(name, kind="rig", label=None):
    root = "|%s_Character|%s:root" % (name, name) if kind == "rig" else "|%s|root" % name
    return scene.CharacterRef(kind, root, None, label or ("Manny [rig]" if kind == "rig" else
                                                          "Manny UE5 [skeleton]"),
                              None, None, name if kind == "rig" else "")


class ChooseTargets(unittest.TestCase):

    def test_the_selection_names_its_characters(self):
        a, b = ref("Manny_Rig"), ref("Creep_Rig")
        self.assertEqual(ap.choose_targets([a, b], True, [a, b, ref("Orc_D_Rig")]), ([a, b], ""))

    def test_nothing_selected_the_only_character(self):
        a = ref("Manny_Rig")
        self.assertEqual(ap.choose_targets([], False, [a]), ([a], ""))

    def test_nothing_selected_and_no_character(self):
        self.assertEqual(ap.choose_targets([], False, []), ([], ap.NO_CHARACTER))

    def test_nothing_selected_and_several_characters_names_them(self):
        refs, refusal = ap.choose_targets([], False, [ref("Manny_Rig"), ref("Manny_Rig1"),
                                                      ref("Manny", "skeleton")])
        self.assertEqual(refs, [])
        self.assertEqual(refusal, "3 characters in the scene (Manny_Rig, Manny_Rig1, Manny UE5 "
                                  "[skeleton] (root)) - select any part of the one you mean")

    def test_a_selection_of_no_character_is_refused_not_redirected(self):
        self.assertEqual(ap.choose_targets([], True, [ref("Manny_Rig")]),
                         ([], ap.NOT_A_CHARACTER))

    def test_a_rig_is_named_by_its_namespace(self):
        self.assertEqual(ap.target_label(ref("Manny_Rig1")), "Manny_Rig1")
        self.assertEqual(ap.target_label(ref("Manny", "skeleton")), "Manny UE5 [skeleton] (root)")


# ------------------------------------------------------------------ pairing members

class Members(unittest.TestCase):

    def test_the_target_members_in_skeleton_order(self):
        bones = OrderedDict((k, {}) for k in ("root", "pelvis", "spine_01", "hand_l", "finger"))
        pairs = {"root": "Root", "pelvis": "Hips", "hand_l": "LeftHand", "finger": "LeftFinger"}
        self.assertEqual(ap.target_members(bones, pairs, ["LeftFinger", "Hips", "LeftHand"]),
                         ["pelvis", "hand_l", "finger"])

    def test_unpaired_members_are_named_twist_bones_aside(self):
        pairs = {"hand_l": "hand_l"}
        self.assertEqual(ap.unpaired(["hand_l", "index_01_l", "lowerarm_twist_02_l"], pairs),
                         ["index_01_l"])

    def test_a_bone_with_no_name_of_its_own_is_not_news(self):
        # Mixamo's finger end joints and HeadTop_End: recognize names none of them, nothing can
        # pair them - «no LeftHandIndex4 ... and 7 more» said nothing on every Mixamo card
        source = {"Hips": {"canonical": "pelvis"}, "LeftHand": {"canonical": "hand_l"},
                  "LeftHandIndex4": {"canonical": None}, "HeadTop_End": {"canonical": None},
                  "LeftHandIndex1": {"canonical": "index_01_l"}}
        pairs = {"pelvis": "Hips", "hand_l": "LeftHand"}
        self.assertEqual(ap.unpaired(list(source), pairs, source), ["LeftHandIndex1"])
        # a UE-named card: every leaf is its own name
        ue = {"root": {}, "pelvis": {}, "spine_01": {}, "thigh_l": {}, "thigh_r": {},
              "calf_l": {}, "calf_r": {}, "foot_l": {}, "foot_r": {}, "clavicle_l": {},
              "clavicle_r": {}, "upperarm_l": {}, "upperarm_r": {}, "lowerarm_l": {},
              "lowerarm_r": {}, "hand_l": {}, "hand_r": {}, "neck_02": {}}
        for bone in ue.values():
            bone["canonical"] = None
        self.assertEqual(ap.unpaired(["neck_02", "hand_l"], {"hand_l": "hand_l"}, ue),
                         ["neck_02"])

    def test_the_unpaired_note(self):
        self.assertEqual(ap.unpaired_note(["hand_l"], "Creep_Rig"), "no hand_l on Creep_Rig")
        self.assertEqual(ap.unpaired_note(list("abcdef"), "X"), "no a, b, c, d and 2 more on X")
        self.assertEqual(ap.unpaired_note([], "X"), "")


# ------------------------------------------------------------------ objects

def obj(name, path=None, **attrs):
    return {"name": name, "path": path or "|" + name, "attrs": attrs}


class PairObjects(unittest.TestCase):

    def test_by_name_namespace_blind(self):
        objects = [obj("pCube1", translateX=1.0), obj("pCube2", translateX=2.0)]
        got, how = ap.pair_objects(objects, ["|copy:pCube2", "|grp|copy:pCube1"], {0: "|pCube1"})
        self.assertEqual(how, "name")
        self.assertEqual([(o["name"], p) for o, p in got],
                         [("pCube1", "|grp|copy:pCube1"), ("pCube2", "|copy:pCube2")])

    def test_else_the_stored_ones_found_in_the_scene(self):
        objects = [obj("pCube1"), obj("pCube2")]
        got, how = ap.pair_objects(objects, [], {0: "|pCube1", 1: None})
        self.assertEqual((how, [(o["name"], p) for o, p in got]), ("stored",
                                                                   [("pCube1", "|pCube1")]))

    def test_else_by_selection_order_when_the_counts_match(self):
        objects = [obj("pCube1"), obj("pCube2")]
        got, how = ap.pair_objects(objects, ["|a", "|b"], {})
        self.assertEqual((how, [(o["name"], p) for o, p in got]),
                         ("order", [("pCube1", "|a"), ("pCube2", "|b")]))
        self.assertEqual(ap.pair_objects(objects, ["|a"], {}), ([], ""))

    def test_nothing_found(self):
        self.assertEqual(ap.pair_objects([obj("x")], [], {}), ([], ""))

    def test_the_selection_decides_over_the_stored_originals(self):
        # the originals are in the scene, two differently named boxes selected: the pose goes onto
        # the boxes, by order - never onto the unselected originals
        objects = [obj("pCube1"), obj("pCube2")]
        got, how = ap.pair_objects(objects, ["|boxOne", "|boxTwo"],
                                   {0: "|pCube1", 1: "|pCube2"})
        self.assertEqual((how, [(o["name"], p) for o, p in got]),
                         ("order", [("pCube1", "|boxOne"), ("pCube2", "|boxTwo")]))

    def test_by_name_then_the_rest_by_order(self):
        objects = [obj("pCube1"), obj("pCube2"), obj("pCube3")]
        got, how = ap.pair_objects(objects, ["|boxA", "|copy:pCube2", "|boxB"], {})
        self.assertEqual(how, "name+order")
        self.assertEqual([(o["name"], p) for o, p in got],
                         [("pCube2", "|copy:pCube2"), ("pCube1", "|boxA"), ("pCube3", "|boxB")])

    def test_the_rest_not_as_many_takes_nothing_by_order(self):
        objects = [obj("pCube1"), obj("pCube2")]
        got, how = ap.pair_objects(objects, ["|copy:pCube1", "|boxA", "|boxB"], {1: "|pCube2"})
        self.assertEqual((how, [(o["name"], p) for o, p in got]),
                         ("name", [("pCube1", "|copy:pCube1")]))

    def test_a_selection_that_matches_nothing_is_nothing_never_the_originals(self):
        objects = [obj("pCube1"), obj("pCube2")]
        self.assertEqual(ap.pair_objects(objects, ["|boxA"], {0: "|pCube1", 1: "|pCube2"}),
                         ([], ""))

    def test_two_selected_copies_of_one_object_both_take_it(self):
        objects = [obj("pCube1"), obj("pCube2")]
        got, how = ap.pair_objects(objects, ["|a:pCube1", "|b:pCube1"], {})
        self.assertEqual((how, [(o["name"], p) for o, p in got]),
                         ("name", [("pCube1", "|a:pCube1"), ("pCube1", "|b:pCube1")]))

    def test_a_selected_object_takes_one_stored_object_of_its_name(self):
        # two stored objects share a leaf (|a|pCube1, |b|pCube1) and neither is selected: the
        # selected copy takes the first not taken - the first
        objects = [obj("pCube1", "|a|pCube1"), obj("pCube1", "|b|pCube1")]
        got, how = ap.pair_objects(objects, ["|copy:pCube1"], {})
        self.assertEqual((how, [(o["path"], p) for o, p in got]),
                         ("name", [("|a|pCube1", "|copy:pCube1")]))

    # two referenced copies of one prop share a leaf: the most common Studio-Library case. The
    # first rewrite gave every selected path the FIRST stored object of its leaf - propB took
    # propA's values, selected with it or alone (fix round 1)

    def props(self):
        return [obj("ctrl", "|propA:ctrl", translateX=1.0),
                obj("ctrl", "|propB:ctrl", translateX=2.0)]

    def test_two_same_named_originals_selected_each_take_their_own(self):
        got, how = ap.pair_objects(self.props(), ["|propA:ctrl", "|propB:ctrl"], {})
        self.assertEqual((how, [(o["path"], o["attrs"]["translateX"], p) for o, p in got]),
                         ("name", [("|propA:ctrl", 1.0, "|propA:ctrl"),
                                   ("|propB:ctrl", 2.0, "|propB:ctrl")]))
        got, how = ap.pair_objects(self.props(), ["|propB:ctrl", "|propA:ctrl"], {})
        self.assertEqual([(o["path"], p) for o, p in got],
                         [("|propA:ctrl", "|propA:ctrl"), ("|propB:ctrl", "|propB:ctrl")])

    def test_the_second_same_named_original_alone_takes_its_own(self):
        got, how = ap.pair_objects(self.props(), ["|propB:ctrl"], {})
        self.assertEqual((how, [(o["path"], o["attrs"]["translateX"], p) for o, p in got]),
                         ("name", [("|propB:ctrl", 2.0, "|propB:ctrl")]))

    def test_same_named_copies_take_the_stored_ones_in_order_then_the_first(self):
        # three copies, none an original: the next not taken in the stored order, and the third,
        # with both taken, the first of the name
        got, how = ap.pair_objects(self.props(), ["|c1:ctrl", "|c2:ctrl", "|c3:ctrl"], {})
        self.assertEqual((how, [(o["path"], p) for o, p in got]),
                         ("name", [("|propA:ctrl", "|c1:ctrl"), ("|propA:ctrl", "|c3:ctrl"),
                                   ("|propB:ctrl", "|c2:ctrl")]))

    def test_an_original_keeps_its_own_and_a_copy_takes_the_other(self):
        # propB's own path wins even selected after the copy, which then takes propA
        got, how = ap.pair_objects(self.props(), ["|copy:ctrl", "|propB:ctrl"], {})
        self.assertEqual((how, [(o["path"], p) for o, p in got]),
                         ("name", [("|propA:ctrl", "|copy:ctrl"), ("|propB:ctrl", "|propB:ctrl")]))


# ------------------------------------------------------------------ the native rebuild

def placed(euler, point, order=0):
    tm = om.MTransformationMatrix(om.MEulerRotation(
        *([math.radians(v) for v in euler] + [order])).asMatrix())
    tm.setTranslation(om.MVector(*point), om.MSpace.kTransform)
    return [float(v) for v in tm.asMatrix()]


class RebuildJoints(unittest.TestCase):

    def bones(self):
        return OrderedDict([
            ("hand", {"parent": "arm", "rest": placed((5, 60, -10), (40, 140, 3)),
                      "rotateOrder": 4}),
            ("Hips", {"parent": None, "rest": placed((0, 0, 0), (0, 100, 0)), "rotateOrder": 0}),
            ("arm", {"parent": "Hips", "rest": placed((0, 0, 80), (20, 140, 0)),
                     "rotateOrder": 5}),
        ])

    def test_parents_first_and_the_rests_rebuilt_exactly(self):
        bones = self.bones()
        joints = ap.rebuild_joints(bones)
        self.assertEqual([j["name"] for j in joints], ["Hips", "arm", "hand"])
        self.assertEqual([j["parent"] for j in joints], [None, 0, 1])
        self.assertEqual([j["order"] for j in joints], ["xyz", "zyx", "yxz"])
        worlds = []
        for joint in joints:
            tm = om.MTransformationMatrix(om.MQuaternion(*joint["q"]).asMatrix())
            tm.setTranslation(om.MVector(*joint["t"]), om.MSpace.kTransform)
            local = tm.asMatrix()
            world = local if joint["parent"] is None else local * worlds[joint["parent"]]
            worlds.append(world)
            want = om.MMatrix(bones[joint["name"]]["rest"])
            self.assertTrue(world.isEquivalent(want, 1e-9), joint["name"])

    def test_the_rebuilt_root_stands_on_the_point_whatever_its_rest(self):
        # a Mixamo card rebuilt from a rest at x=40, z=-25, dropped at (-100, 0, 50): the root's
        # first position is the point (the first build put it at rest + point: (-60, 25))
        self.assertEqual(ap.floor_move((40.0, 95.0, -25.0), (-100.0, 0.0, 50.0)),
                         (-140.0, 0.0, 75.0))
        self.assertEqual(ap.floor_move((0.0, 95.0, 0.0), (150.0, 7.0, -60.0)), (150.0, 0.0, -60.0))

    def test_the_line_names_the_floor_point_as_the_ghost_did(self):
        # the live run (2026-10-03): the ghost said «floor (0, 141)» for z 140.699 and the line
        # after the drop «at floor (0, 140)» - "%d" truncated where the caption rounds
        from maya_poselib import look
        for point in ((0.0, 0.0, 140.699), (-36.7, 0.0, 12.5), (120.49, 0.0, -0.5)):
            caption = look.drop_caption("Fist", {"kind": "floor", "label": "Manny [rig]",
                                                  "point": point})[0]
            floor = caption.split("floor ")[-1]
            self.assertEqual(ap.ADDED % (("Manny [rig]", "Manny_Rig2") + ap.floor_xz(point)),
                             "a new Manny [rig] Manny_Rig2 at floor " + floor)
            self.assertEqual(ap.REBUILT % (("pose_Fist",) + ap.floor_xz(point)),
                             "pose_Fist rebuilt (bones only) at floor " + floor)

    def test_a_joint_name_maya_cannot_take_is_made_legal(self):
        joints = ap.rebuild_joints({"DEF-spine.003": {"parent": None,
                                                      "rest": placed((0, 0, 0), (0, 0, 0))}})
        self.assertEqual(joints[0]["name"], "DEF_spine_003")


# ------------------------------------------------------------------ the press, against a fake scene

class FakeCmds(object):
    """The `cmds` calls a press makes, recorded in order."""

    def __init__(self, log, frame=12.0):
        self.log = log
        self.frame = frame
        self.auto = True
        self.recording = True

    def undoInfo(self, query=False, state=None, openChunk=False, closeChunk=False,
                 chunkName=None, stateWithoutFlush=None, **kwargs):
        if query:
            return self.recording
        if stateWithoutFlush is not None:
            self.recording = bool(stateWithoutFlush)
            self.log.append(("record", self.recording))
        if openChunk:
            self.log.append(("open", chunkName))
        if closeChunk:
            self.log.append(("close",))

    def autoKeyframe(self, query=False, state=None):
        if query:
            return self.auto
        self.auto = state
        self.log.append(("autoKey", state))

    def currentTime(self, value=None, query=False, update=None):
        if query:
            return self.frame
        self.log.append(("time", value, update, self.recording))

    def ls(self, *args, **kwargs):
        return []

    def refresh(self, **kwargs):
        self.log.append(("refresh",))

    def dgdirty(self, nodes):
        self.log.append(("dirty", list(nodes), self.recording))

    def getAttr(self, plug):
        return 0

    def attributeQuery(self, attr, node=None, exists=False):
        return True


class FakeKeys(object):
    """`keys` as a press sees it: the layer (and its refusal), the quaternion note, the reads and
    writes logged. `write` keys every plug but those in `refused`; `inputs` says what feeds a
    plug (`input_of`, `feed_of` - its node `feed:<plug>`), "free" when unnamed."""

    Written = real_keys.Written

    def __init__(self, log, layer=None, refusal="", quaternion="", refused=(), inputs=None):
        self.log = log
        self.layer = layer
        self.refusal = refusal
        self.quaternion = quaternion
        self.refused = set(refused)
        self.inputs = dict(inputs or {})

    def active_layer(self):
        self.log.append(("layer",))
        return self.layer, self.refusal

    def quaternion_note(self, layer):
        self.log.append(("quaternion",))
        return self.quaternion

    def layer_note(self, layer):
        return real_keys.layer_note(layer)

    def current(self, plugs):
        return dict((p, 0.0) for p in plugs)

    def write(self, values, frame, layer):
        self.log.append(("write", dict(values), frame))
        keyed = [p for p in values if p not in self.refused]
        notes = ["%d not keyed (layer L took no key): %s" % (
            len(self.refused & set(values)), ", ".join(sorted(self.refused & set(values))))] \
            if self.refused & set(values) else []
        return real_keys.Written(len(keyed), notes, keyed)

    def preview(self, values):
        self.log.append(("preview", dict(values)))

    def input_of(self, plug):
        return self.inputs.get(plug, "free")

    def feed_of(self, plug):
        kind = self.input_of(plug)
        return kind, (None if kind in ("free", "missing") else "feed:" + plug)

    @property
    def Tweaks(self):                                        # noqa: N802 - keys.Tweaks
        log = self.log

        class Tweaks(object):
            """The scene's tweaks: read (logged), and set back (logged with what is skipped)."""

            def __init__(self):
                log.append(("tweaks",))

            def restore(self, skip=()):
                log.append(("restore", sorted(skip)))
                return []
        return Tweaks


class Press(unittest.TestCase):
    """The frame of a press: refusals before anything, ONE undo chunk around the solve and the
    keys (a Ctrl+Z after Apply is the whole press), autoKey off inside it and back; a Blend that
    solves and previews UNRECORDED and keys in one chunk on finish, so a cancel leaves no undo
    step at all and nothing stays open while the animator drags."""

    def setUp(self):
        self.log = []
        self.saved = dict((name, getattr(ap, name)) for name in
                          ("cmds", "keys", "_plan", "_targets", "_measure", "rotations_of",
                           "_add", "_rebuild", "_reselect", "apply_onto", "_selected",
                           "_find_object", "_objects_entry", "_switches", "_evaluated",
                           "_not_characters"))
        ap.cmds = FakeCmds(self.log)
        ap.keys = FakeKeys(self.log)
        self.parts = {}                      # path -> the character it is part of
        ap._not_characters = self.not_characters
        self.switch = False                  # the scene under DG: the measure switches nothing
        ap._switches = lambda: self.switch
        log = self.log

        @contextlib.contextmanager
        def evaluated(tweaks, skip):
            log.append(("evaluate", tweaks is not None, sorted(skip)))
            yield
            log.append(("evaluated",))
        ap._evaluated = evaluated
        self.target = ref("Manny_Rig1")
        ap._targets = lambda selection: ([self.target], "")
        ap._measure = lambda plan, extra: (0.001, 0.0, "hand_l")
        ap.rotations_of = lambda values: {}

        def plan(data, target, mirror=False):
            self.log.append(("plan", self.log_recording()))
            return (ap.Plan(target, OrderedDict([("Manny_Rig1:FKWrist_L.rotateX", 30.0)]),
                            {"Manny_Rig1:FKWrist_L.rotateX": 10.0}, [], {}), None)
        ap._plan = plan
        self.card = {"kind": "character", "name": "Fist", "bones": {"root": {}},
                     "members": ["hand_l"]}

    def log_recording(self):
        return ap.cmds.recording

    def not_characters(self, paths):
        """`_not_characters` on `self.parts`, its notes spelled as the real one spells them."""
        loose = [p for p in paths if p not in self.parts]
        named = [p.split("|")[-1].split(":")[-1] for p in paths if p in self.parts]
        whose = ", ".join(sorted(set(self.parts[p] for p in paths if p in self.parts)))
        if not named:
            return loose, ""
        if len(named) == 1:
            return loose, ap.CHARACTER_PART % (named[0], whose)
        return loose, ap.CHARACTER_PARTS % (len(named), whose)

    def tearDown(self):
        for name, value in self.saved.items():
            setattr(ap, name, value)

    def test_apply_is_one_chunk_around_the_solve_and_the_keys(self):
        ok, text = ap.apply(self.card)
        self.assertTrue(ok, text)
        names = [entry[0] for entry in self.log]
        self.assertEqual(names[:3], ["layer", "quaternion", "open"])
        self.assertEqual(self.log[2], ("open", "skeldarPoseApply"))
        self.assertLess(names.index("open"), names.index("plan"))
        self.assertLess(names.index("plan"), names.index("write"))
        self.assertLess(names.index("write"), names.index("close"))
        self.assertEqual(names.count("open"), 1)
        self.assertEqual(self.log[names.index("open") + 1], ("autoKey", False))
        self.assertEqual(self.log[names.index("close") - 1], ("autoKey", True))
        self.assertEqual(text, "Fist onto Manny_Rig1: 1 control keyed at frame 12 - worst "
                               "0.001 deg")

    def test_a_press_changes_no_time_and_measures_under_the_solve_s_evaluation(self):
        """The final review: a same-frame `currentTime` after the keys threw away every unkeyed
        tweak on a keyed channel in the scene. The measure reads under `rigsolve._fresh`, the
        plugs just keyed handed to it as those NOT to set back."""
        ok, text = ap.apply(self.card)
        self.assertTrue(ok, text)
        names = [entry[0] for entry in self.log]
        self.assertNotIn("time", names)
        self.assertNotIn("tweaks", names)            # under DG nothing re-evaluates: none read
        self.assertEqual(self.log[names.index("evaluate")],
                         ("evaluate", False, ["Manny_Rig1:FKWrist_L.rotateX"]))
        self.assertLess(names.index("write"), names.index("evaluate"))
        self.assertLess(names.index("evaluated"), names.index("close"))

    def test_in_a_parallel_scene_the_tweaks_are_read_before_the_keys(self):
        self.switch = True
        ok, text = ap.apply(self.card)
        self.assertTrue(ok, text)
        names = [entry[0] for entry in self.log]
        self.assertLess(names.index("tweaks"), names.index("write"))
        self.assertEqual(self.log[names.index("evaluate")],
                         ("evaluate", True, ["Manny_Rig1:FKWrist_L.rotateX"]))

    def test_a_muted_layer_takes_the_keys_and_the_line_says_why_nothing_shows(self):
        muted = real_keys.Layer("PoseM", False, True, False, False, True, 1.0)
        ap.keys = FakeKeys(self.log, layer=muted)
        ok, text = ap.apply(self.card)
        self.assertTrue(ok, text)
        self.assertIn("write", [entry[0] for entry in self.log])
        self.assertIn("1 control keyed on PoseM", text)
        self.assertIn(real_keys.MUTED % "PoseM", text)

    def test_a_layer_at_weight_zero_is_said_too(self):
        ap.keys = FakeKeys(self.log, layer=real_keys.Layer("PoseW", False, True, False, False,
                                                           False, 0.0))
        ok, text = ap.apply(self.card)
        self.assertIn(real_keys.NO_WEIGHT % "PoseW", text)

    def test_a_refused_layer_changes_nothing(self):
        ap.keys = FakeKeys(self.log, refusal="the animation layer L is locked")
        ok, text = ap.apply(self.card)
        self.assertEqual((ok, text), (False, "the animation layer L is locked"))
        self.assertEqual(self.log, [("layer",)])

    def test_apply_at_half_keys_the_mix(self):
        ok, _text = ap.apply(self.card, alpha=0.5)
        written = [entry for entry in self.log if entry[0] == "write"][0]
        self.assertAlmostEqual(written[1]["Manny_Rig1:FKWrist_L.rotateX"], 20.0, places=12)

    def test_a_blend_previews_unrecorded_and_a_cancel_leaves_no_step(self):
        blend = ap.Blend()
        self.assertEqual(blend.start(self.card), "")
        blend.set(0.5)
        blend.cancel()
        self.assertNotIn("open", [entry[0] for entry in self.log])
        plans = [entry for entry in self.log if entry[0] == "plan"]
        self.assertEqual(plans, [("plan", False)])           # solved with recording off
        previews = [entry[1] for entry in self.log if entry[0] == "preview"]
        self.assertEqual(previews, [{"Manny_Rig1:FKWrist_L.rotateX": 20.0},
                                    {"Manny_Rig1:FKWrist_L.rotateX": 10.0}])
        self.assertTrue(ap.cmds.recording)
        self.assertTrue(ap.cmds.auto)
        self.assertFalse(blend.active())

    def test_a_blend_finish_keys_its_last_alpha_in_one_chunk(self):
        blend = ap.Blend()
        blend.start(self.card)
        blend.set(0.25)
        text = blend.finish()
        names = [entry[0] for entry in self.log]
        self.assertEqual(names.count("open"), 1)
        opened = names.index("open")
        # every value back, unrecorded, before the chunk: a Ctrl+Z then finds the static
        # channels as they were before the session, not at the preview's value
        last = max(i for i, entry in enumerate(self.log[:opened]) if entry[0] == "preview")
        self.assertEqual(self.log[last][1], {"Manny_Rig1:FKWrist_L.rotateX": 10.0})
        self.assertIn(("record", True), self.log[last:opened])
        self.assertTrue(all(entry != ("record", False) for entry in self.log[opened:]))
        written = [entry for entry in self.log if entry[0] == "write"]
        self.assertEqual(len(written), 1)
        self.assertAlmostEqual(written[0][1]["Manny_Rig1:FKWrist_L.rotateX"], 15.0, places=12)
        self.assertLess(opened, names.index("write"))
        self.assertLess(names.index("write"), names.index("close"))
        self.assertIn("at 25 %", text)
        self.assertFalse(blend.active())

    def test_a_blend_at_zero_keys_nothing(self):
        blend = ap.Blend()
        blend.start(self.card)
        text = blend.finish()
        self.assertNotIn("write", [entry[0] for entry in self.log])
        self.assertIn("nothing keyed", text)

    def test_a_blend_refused_starts_nothing(self):
        ap.keys = FakeKeys(self.log, refusal="the animation layer L is locked")
        blend = ap.Blend()
        self.assertEqual(blend.start(self.card), "the animation layer L is locked")
        self.assertFalse(blend.active())
        self.assertNotIn("plan", [entry[0] for entry in self.log])

    # ---- the refusals: before anything changes

    QUATERNION = real_keys.QUATERNION % "PoseQ"
    LAYER_Q = real_keys.Layer("PoseQ", False, True, False, True)

    def test_a_quaternion_layer_refuses_a_character_pose_before_anything(self):
        ap.keys = FakeKeys(self.log, layer=self.LAYER_Q, quaternion=self.QUATERNION)
        ok, text = ap.apply(self.card)
        self.assertEqual((ok, text), (False, self.QUATERNION))
        self.assertEqual(self.log, [("layer",), ("quaternion",)])     # only the layer read

    def objects_entry(self, attrs):
        values = OrderedDict(("|boxA." + attr, value) for attr, value in attrs.items())
        plan = ap.Plan(None, values, dict((plug, 0.0) for plug in values), [], {})
        return (plan, ap.Extra(None, None, None, "1 object")), ""

    def test_a_quaternion_layer_refuses_an_objects_pose_that_turns(self):
        ap.keys = FakeKeys(self.log, layer=self.LAYER_Q, quaternion=self.QUATERNION)
        ap._objects_entry = lambda data, selection: self.objects_entry(
            {"rotateY": 33.0, "translateX": 1.0})
        ok, text = ap.apply({"kind": "objects", "name": "Cubes", "objects": [obj("boxA")]})
        self.assertEqual((ok, text), (False, self.QUATERNION))
        names = [entry[0] for entry in self.log]
        self.assertEqual(names, ["layer", "quaternion"])

    def test_a_quaternion_layer_keys_an_objects_pose_that_only_moves(self):
        ap.keys = FakeKeys(self.log, layer=self.LAYER_Q, quaternion=self.QUATERNION)
        ap._objects_entry = lambda data, selection: self.objects_entry({"translateX": 1.0})
        ok, text = ap.apply({"kind": "objects", "name": "Cubes", "objects": [obj("boxA")]})
        self.assertTrue(ok, text)
        self.assertIn("write", [entry[0] for entry in self.log])

    def floor_patched(self):
        added = []
        ap._add = lambda entry, point: added.append(entry.key) or ("|root", "added")
        ap._rebuild = lambda data, point: added.append("rebuild") or ("|root", "rebuilt")
        ap._reselect = lambda selection: None
        ap.apply_onto = lambda data, root, mirror=False: (True, "posed")
        return added

    def test_drop_floor_refuses_a_bad_layer_before_it_adds_a_character(self):
        added = self.floor_patched()
        catalogued = dict(self.card, character={"key": "Manny_Rig"})
        native = dict(self.card, character={"key": None})
        for keys_ in (FakeKeys(self.log, refusal=real_keys.LOCKED % "PoseO"),
                      FakeKeys(self.log, layer=self.LAYER_Q, quaternion=self.QUATERNION)):
            ap.keys = keys_
            for card in (catalogued, native):
                ok, text = ap.drop_floor(card, (10.0, 0.0, 20.0))
                self.assertFalse(ok)
                self.assertIn(text, (real_keys.LOCKED % "PoseO", self.QUATERNION))
        self.assertEqual(added, [])
        self.assertNotIn("open", [entry[0] for entry in self.log])

    def test_drop_floor_adds_the_character_when_the_layer_is_fine(self):
        # the positive control of the refusal above: the same cards, a layer that takes keys
        added = self.floor_patched()
        ok, text = ap.drop_floor(dict(self.card, character={"key": "Manny_Rig"}), (1.0, 0, 2.0))
        self.assertEqual((ok, text), (True, "added | posed"))
        ok, text = ap.drop_floor(dict(self.card, character={"key": None}), (1.0, 0, 2.0))
        self.assertEqual((ok, text), (True, "rebuilt | posed"))
        self.assertEqual(added, ["Manny_Rig", "rebuild"])

    # ---- what the line counts

    def test_the_line_counts_the_nodes_that_took_a_key(self):
        wrist, elbow_x, elbow_y = ("Manny_Rig1:FKWrist_L.rotateX", "Manny_Rig1:FKElbow_L.rotateX",
                                   "Manny_Rig1:FKElbow_L.rotateY")

        def plan(data, target, mirror=False):
            values = OrderedDict([(wrist, 30.0), (elbow_x, 5.0), (elbow_y, 6.0)])
            return ap.Plan(target, values, dict((p, 0.0) for p in values), [], {}), None
        ap._plan = plan
        ap.keys = FakeKeys(self.log, refused=(elbow_x, elbow_y))
        ok, text = ap.apply(self.card)
        self.assertTrue(ok, text)
        self.assertTrue(text.startswith("Fist onto Manny_Rig1: 1 control keyed at frame 12"),
                        text)
        self.assertIn("2 not keyed", text)

    def test_nothing_keyed_counts_nothing(self):
        ap.keys = FakeKeys(self.log, refused=("Manny_Rig1:FKWrist_L.rotateX",))
        ok, text = ap.apply(self.card)
        self.assertFalse(ok)
        self.assertTrue(text.startswith("Fist onto Manny_Rig1: nothing keyed | 1 not keyed"),
                        text)

    # ---- plan_for

    def test_plan_for_solves_unrecorded_and_opens_no_chunk(self):
        plan = ap.plan_for(self.card, self.target)
        self.assertEqual(dict(plan.values), {"Manny_Rig1:FKWrist_L.rotateX": 30.0})
        self.assertEqual([entry for entry in self.log if entry[0] == "plan"], [("plan", False)])
        self.assertNotIn("open", [entry[0] for entry in self.log])
        self.assertEqual([entry for entry in self.log if entry[0] == "record"],
                         [("record", False), ("record", True)])
        self.assertTrue(ap.cmds.recording)

    # ---- a blend ended after the time moved

    FREE, KEYED = "Manny_Rig1:FKWrist_L.rotateX", "Manny_Rig1:FKWrist_L.rotateY"
    LAYERED, DRIVEN = "Manny_Rig1:FKWrist_L.rotateZ", "Manny_Rig1:FKElbow_L.rotateX"

    def moved_blend(self, inputs=None):
        def plan(data, target, mirror=False):
            values = OrderedDict([(self.FREE, 30.0), (self.KEYED, 50.0), (self.LAYERED, 70.0),
                                  (self.DRIVEN, 90.0)])
            current = {self.FREE: 10.0, self.KEYED: 20.0, self.LAYERED: 40.0, self.DRIVEN: 60.0}
            return ap.Plan(target, values, current, [], {}), None
        ap._plan = plan
        ap.keys = FakeKeys(self.log, inputs=inputs if inputs is not None else {
            self.KEYED: "curve", self.LAYERED: "layer", self.DRIVEN: "driven"})
        blend = ap.Blend()
        self.assertEqual(blend.start(self.card), "")
        blend.set(0.5)
        ap.cmds.frame = 13.0                         # the animator moved the time
        blend.set(0.7)                               # ... and the preview went on at the new frame
        del self.log[:]
        return blend

    def assert_settled(self):
        # the free channel set back to its start value, the keyed and the layered one never
        # written (their start values are the OLD frame's): their feeding nodes dirtied - a
        # static channel in a layer is not time-dependent, a same-time currentTime alone left it
        # on the preview's value (fix round 1) - then the time evaluated once at the frame now
        # shown; the driven one neither; all of it unrecorded
        previews = [entry[1] for entry in self.log if entry[0] == "preview"]
        self.assertEqual(previews, [{self.FREE: 10.0}])
        dirty = [entry for entry in self.log if entry[0] == "dirty"]
        self.assertEqual(dirty, [("dirty", ["feed:" + self.KEYED, "feed:" + self.LAYERED],
                                  False)])
        times = [entry for entry in self.log if entry[0] == "time"]
        self.assertEqual(times, [("time", 13.0, True, False)])
        names = [entry[0] for entry in self.log]
        self.assertLess(names.index("preview"), names.index("dirty"))
        self.assertLess(names.index("dirty"), names.index("time"))
        # the scene's OTHER tweaks read before that time evaluation and set back after it, the
        # session's own channels aside (the final review)
        self.assertLess(names.index("tweaks"), names.index("time"))
        self.assertEqual(self.log[names.index("time") + 1],
                         ("restore", sorted([self.FREE, self.KEYED, self.LAYERED, self.DRIVEN])))
        self.assertNotIn("open", names)
        self.assertNotIn("write", names)
        self.assertTrue(ap.cmds.recording)
        self.assertTrue(ap.cmds.auto)

    def test_a_blend_over_free_channels_only_dirties_nothing(self):
        blend = self.moved_blend(inputs={})
        blend.cancel()
        names = [entry[0] for entry in self.log]
        self.assertNotIn("dirty", names)
        self.assertEqual([entry for entry in self.log if entry[0] == "time"],
                         [("time", 13.0, True, False)])
        self.assertEqual([entry[1] for entry in self.log if entry[0] == "preview"],
                         [{self.FREE: 10.0, self.KEYED: 20.0, self.LAYERED: 40.0,
                           self.DRIVEN: 60.0}])

    def test_a_blend_cancelled_after_the_time_moved_sets_back_only_the_free_channels(self):
        blend = self.moved_blend()
        blend.cancel()
        self.assert_settled()
        self.assertFalse(blend.active())

    def test_a_blend_finished_after_the_time_moved_keys_nothing_and_settles(self):
        blend = self.moved_blend()
        self.assertEqual(blend.finish(), ap.TIME_MOVED)
        self.assert_settled()
        self.assertFalse(blend.active())

    # ---- objects: the selection decides

    CUBES = {"kind": "objects", "name": "Cubes",
             "objects": [obj("pCube1", translateX=1.0), obj("pCube2", translateX=2.0)]}

    def test_with_objects_selected_the_originals_are_never_looked_for(self):
        ap._selected = lambda selection: list(selection or [])

        def find(record):
            raise AssertionError("looked for %s" % record["name"])
        ap._find_object = find
        entry, refusal = ap._objects_entry(self.CUBES, ["|copy:pCube1", "|boxA", "|boxB"])
        self.assertEqual(refusal, "")
        self.assertEqual(dict(entry[0].values), {"|copy:pCube1.translateX": 1.0})
        self.assertIn("2 selected matched nothing of the pose: boxA, boxB", entry[0].notes)

    def test_a_selection_that_matches_nothing_is_refused_in_its_own_words(self):
        ap._selected = lambda selection: list(selection or [])
        ap._find_object = lambda record: "|" + record["name"]       # the originals are there
        entry, refusal = ap._objects_entry(self.CUBES, ["|boxA"])
        self.assertIsNone(entry)
        self.assertEqual(refusal, ap.SELECTION_UNMATCHED % (2, "s", 2))

    def test_by_order_onto_the_selection_says_so(self):
        ap._selected = lambda selection: list(selection or [])
        ap._find_object = lambda record: "|" + record["name"]
        entry, _refusal = ap._objects_entry(self.CUBES, ["|boxA", "|boxB"])
        self.assertEqual(dict(entry[0].values), {"|boxA.translateX": 1.0,
                                                 "|boxB.translateX": 2.0})
        self.assertIn(ap.BY_ORDER, entry[0].notes)

    def test_nothing_selected_the_stored_ones_found_in_the_scene(self):
        ap._selected = lambda selection: list(selection or [])
        ap._find_object = lambda record: "|grp|" + record["name"] \
            if record["name"] == "pCube1" else None
        entry, refusal = ap._objects_entry(self.CUBES, [])
        self.assertEqual(refusal, "")
        self.assertEqual(dict(entry[0].values), {"|grp|pCube1.translateX": 1.0})
        self.assertEqual(entry[0].notes, [])
        ap._find_object = lambda record: None
        self.assertEqual(ap._objects_entry(self.CUBES, []),
                         (None, ap.OBJECTS_MISSING % (2, "s")))

    # the final review (2026-10-03): a one-object card applied right after Add Character (which
    # selects the new rig's Main) keyed Main by selection order - an objects pose is for
    # anything that is NOT a character, and a character's parts are left out of it

    MAIN = "|Manny_Rig_Character|Manny_Rig:Group|Manny_Rig:Main"

    def test_a_character_part_alone_is_refused_and_named(self):
        ap._selected = lambda selection: list(selection or [])
        self.parts = {self.MAIN: "Manny_Rig"}
        entry, refusal = ap._objects_entry({"kind": "objects", "name": "Box",
                                            "objects": [obj("Box", translateX=120.0)]},
                                           [self.MAIN])
        self.assertIsNone(entry)
        self.assertEqual(refusal, ap.CHARACTER_PART % ("Main", "Manny_Rig") + ap.ONTO_OBJECTS)

    def test_a_character_part_beside_objects_is_left_out_and_said(self):
        ap._selected = lambda selection: list(selection or [])
        self.parts = {self.MAIN: "Manny_Rig"}
        entry, refusal = ap._objects_entry(self.CUBES, [self.MAIN, "|boxA", "|boxB"])
        self.assertEqual(refusal, "")
        self.assertEqual(dict(entry[0].values), {"|boxA.translateX": 1.0,
                                                 "|boxB.translateX": 2.0})
        self.assertIn(ap.CHARACTER_PART % ("Main", "Manny_Rig") + ap.LEFT_OUT, entry[0].notes)

    def test_nothing_selected_a_stored_name_found_on_a_character_is_none_of_its(self):
        ap._selected = lambda selection: list(selection or [])
        ap._find_object = lambda record: "|Manny_Rig:" + record["name"]
        self.parts = {"|Manny_Rig:pCube1": "Manny_Rig", "|Manny_Rig:pCube2": "Manny_Rig"}
        self.assertEqual(ap._objects_entry(self.CUBES, []),
                         (None, ap.OBJECTS_MISSING % (2, "s")))


if __name__ == "__main__":
    unittest.main()
