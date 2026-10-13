"""maya_tools.knotplan: the pure half of the Tools card's knots (2026-10-12).

Spans, the attach keys, which channels a knot takes, the round trips of what a knot remembers,
the bake order of a knot on a knot, which waiting pivot a Finish means, sizes, rotate orders and
the lines the card writes.

Spec: docs/superpowers/specs/2026-10-12-tools-knots-design.md
"""

import os
import subprocess
import sys
import unittest

from maya_tools import knotplan as plan


class Kinds(unittest.TestCase):

    def test_the_kinds_in_the_cards_order(self):
        """+ across (2026-10-12, the parent tab): a knot inside the parent; + aim (2026-10-13,
        the aim tab): the object's rotation aims at a target."""
        self.assertEqual([k.key for k in plan.KINDS],
                         ["knot", "offset", "orient", "double_local", "double_world", "across",
                          "aim"])
        self.assertEqual(plan.kind("across").constraint, "parent")
        self.assertEqual(plan.kind("across").suffix, "_across")
        self.assertEqual(plan.kind("aim").constraint, "aim")
        self.assertEqual((plan.kind("aim").suffix, plan.kind("aim").inner_suffix),
                         ("_aim", "_aimUp"))

    def test_the_double_knots_and_the_aim_have_an_inner_node_the_others_do_not(self):
        for kind in plan.KINDS:
            inner = kind.key.startswith("double") or kind.key == "aim"
            self.assertEqual(bool(kind.inner_suffix), inner, kind.key)
            self.assertEqual(kind.inner_colour is not None, inner)

    def test_only_knot_orient_follows_by_orientation(self):
        self.assertEqual([k.key for k in plan.KINDS if k.constraint == "orient"], ["orient"])
        self.assertTrue(all(k.constraint in ("parent", "orient", "aim") for k in plan.KINDS))

    def test_suffixes_are_distinct_and_name_safe(self):
        suffixes = [k.suffix for k in plan.KINDS] + [k.inner_suffix for k in plan.KINDS
                                                     if k.inner_suffix]
        suffixes += [plan.PIVOT_SUFFIX, plan.PIVOT_SPACE_SUFFIX, plan.AIM_TARGET_SUFFIX,
                     plan.AIM_SPACE_SUFFIX]
        self.assertEqual(len(suffixes), len(set(suffixes)))
        for suffix in suffixes:
            self.assertRegex(suffix, r"^_[A-Za-z]+$")

    def test_kind_lookup(self):
        self.assertEqual(plan.kind("orient").label, "Knot Orient")
        self.assertIsNone(plan.kind("nope"))

    def test_colours_are_rgb_in_range(self):
        for kind in plan.KINDS:
            for rgb in (kind.colour, kind.inner_colour or (0, 0, 0)):
                self.assertEqual(len(rgb), 3)
                self.assertTrue(all(0.0 <= c <= 1.0 for c in rgb))

    def test_markers_carry_our_prefix(self):
        """Delete character keeps a node carrying an attribute with our prefix as ours
        (deletion.OUR_ATTR_PREFIXES) - the knots group in a character group must read as ours."""
        for name in (plan.KIND_MARKER, plan.SOURCE_MARKER, plan.SPAN_MARKER, plan.KEYED_MARKER,
                     plan.OF_MARKER, plan.PENDING_MARKER, plan.PENDING_SPACE_MARKER,
                     plan.GROUP_MARKER, plan.ORDER_MARKER, plan.INNER_MARKER,
                     plan.REGISTRY_MARKER, plan.PENDING_KIND_MARKER):
            self.assertTrue(name.startswith("skeldar"), name)


class Leaf(unittest.TestCase):

    def test_the_short_name_without_namespace(self):
        self.assertEqual(plan.leaf("|Manny_Rig_Character|Manny_Rig:Group|Manny_Rig:FKShoulder_R"),
                         "FKShoulder_R")
        self.assertEqual(plan.leaf("|prop"), "prop")
        self.assertEqual(plan.leaf("a:b:c"), "c")


class RotateOrder(unittest.TestCase):

    def test_object_takes_the_objects_own(self):
        self.assertEqual(plan.rotate_order_index("object", 2), 2)

    def test_xyz_and_xzy(self):
        self.assertEqual(plan.rotate_order_index("xyz", 5), 0)
        self.assertEqual(plan.rotate_order_index("xzy", 5), 3)

    def test_an_unknown_choice_is_the_objects(self):
        self.assertEqual(plan.rotate_order_index("zyx?", 4), 4)

    def test_the_choices(self):
        self.assertEqual(plan.ORDERS, ("object", "xyz", "xzy"))
        self.assertEqual(plan.ORDER_DEFAULT, "object")


class Span(unittest.TestCase):

    def test_the_whole_take_is_playback_and_the_objects_keys(self):
        self.assertEqual(plan.span_for((0.0, 100.0), [-5.0, 40.0, 120.0], None),
                         (-5.0, 120.0, False))

    def test_no_keys_is_the_playback_range(self):
        self.assertEqual(plan.span_for((10.0, 50.0), [], None), (10.0, 50.0, False))

    def test_a_fractional_range_widens_outward(self):
        self.assertEqual(plan.span_for((0.5, 49.2), [], None), (0.0, 50.0, False))

    def test_a_highlight_is_overrigs_minus_one_to_end(self):
        """timeControl -rangeArray answers [a, b) - OverRig bakes [a-1, b]."""
        self.assertEqual(plan.span_for((0.0, 100.0), [0.0, 100.0], (10.0, 30.0)),
                         (9.0, 30.0, True))

    def test_a_one_frame_highlight_is_no_range(self):
        self.assertEqual(plan.span_for((0.0, 100.0), [], (10.0, 11.0)), (0.0, 100.0, False))

    def test_round_trip(self):
        for span in ((9.0, 30.0, True), (-5.5, 120.0, False)):
            self.assertEqual(plan.decode_span(plan.encode_span(span)), span)

    def test_a_broken_record_decodes_to_none(self):
        self.assertIsNone(plan.decode_span(""))
        self.assertIsNone(plan.decode_span("garbage here"))

    def test_widen_by_the_knots_own_keys(self):
        self.assertEqual(plan.widen((9.0, 30.0, True), [5.0, 33.5]), (5.0, 34.0, True))
        self.assertEqual(plan.widen((0.0, 50.0, False), []), (0.0, 50.0, False))
        self.assertEqual(plan.widen((0.0, 50.0, False), [10.0, 20.0]), (0.0, 50.0, False))


class Attach(unittest.TestCase):

    def test_a_ranged_knot_blends_in_and_out_over_a_frame(self):
        self.assertEqual(plan.attach_keys((9.0, 30.0, True)),
                         [(9.0, 0.0), (10.0, 1.0), (29.0, 1.0), (30.0, 0.0)])

    def test_a_whole_take_knot_has_no_attach_keys(self):
        self.assertEqual(plan.attach_keys((0.0, 100.0, False)), [])

    def test_influence_is_where_attach_is_above_zero(self):
        samples = [(9, 0.0), (10, 1.0), (11, 0.5), (29, 1.0), (30, 0.0)]
        self.assertEqual(plan.influence(samples), (10.0, 29.0))

    def test_no_influence(self):
        self.assertIsNone(plan.influence([(0, 0.0), (1, 0.0)]))
        self.assertIsNone(plan.influence([]))


class Channels(unittest.TestCase):

    def _all(self, value):
        return dict((ch, value) for ch in plan.CHANNELS)

    def test_free_and_keyed_channels_are_taken(self):
        drivers = self._all(None)
        drivers["tx"] = ""                       # a time curve: keyed
        free, skipped, refusal = plan.channel_plan("obj", self._all(False), drivers)
        self.assertEqual((free, skipped, refusal), (list(plan.CHANNELS), [], ""))

    def test_locked_channels_are_skipped(self):
        locked = self._all(False)
        locked["rz"] = locked["ty"] = True
        free, skipped, refusal = plan.channel_plan("obj", locked, self._all(None))
        self.assertEqual(skipped, ["ty", "rz"])
        self.assertEqual(free, ["tx", "tz", "rx", "ry"])
        self.assertEqual(refusal, "")

    def test_a_driven_channel_refuses_by_name(self):
        drivers = self._all(None)
        drivers["ry"] = "an expression"
        free, skipped, refusal = plan.channel_plan("FKHead_M", self._all(False), drivers)
        self.assertEqual((free, skipped), ([], []))
        self.assertIn("FKHead_M.rotateY", refusal)
        self.assertIn("an expression", refusal)

    def test_a_locked_driven_channel_is_only_skipped(self):
        locked, drivers = self._all(False), self._all(None)
        locked["ry"], drivers["ry"] = True, "a constraint"
        free, skipped, refusal = plan.channel_plan("obj", locked, drivers)
        self.assertEqual(refusal, "")
        self.assertEqual(skipped, ["ry"])

    def test_everything_locked_refuses(self):
        free, skipped, refusal = plan.channel_plan("obj", self._all(True), self._all(None))
        self.assertIn("no free translate or rotate channel", refusal)

    def test_knot_orient_asks_for_rotates_only(self):
        locked = dict((ch, True) for ch in plan.ROTATE)
        free, skipped, refusal = plan.channel_plan("obj", locked, {}, plan.ROTATE)
        self.assertIn("no free rotate channel", refusal)
        free, skipped, refusal = plan.channel_plan("obj", {}, {}, plan.ROTATE)
        self.assertEqual(free, list(plan.ROTATE))

    def test_driver_words(self):
        self.assertEqual(plan.driver_word("animCurveTL", False), "")
        self.assertEqual(plan.driver_word("animCurveTA", False), "")
        self.assertEqual(plan.driver_word("animCurveUA", False), "a driven key")
        self.assertEqual(plan.driver_word("animBlendNodeAdditiveDL", False),
                         "an animation layer")
        self.assertEqual(plan.driver_word("parentConstraint", True), "a constraint")
        self.assertEqual(plan.driver_word("pairBlend", False), "a constraint")
        self.assertEqual(plan.driver_word("expression", False), "an expression")
        self.assertEqual(plan.driver_word("character", False), "a character")

    def test_keyed_round_trip(self):
        keyed = {"tz": 3.0, "rx": -12.25}
        self.assertEqual(plan.decode_keyed(plan.encode_keyed(keyed)), keyed)
        self.assertEqual(plan.decode_keyed(""), {})
        self.assertEqual(plan.decode_keyed(None), {})

    def test_static(self):
        self.assertTrue(plan.is_constant([1.0, 1.0, 1.0000001]))
        self.assertFalse(plan.is_constant([1.0, 1.1]))
        self.assertTrue(plan.still_static([3.0], 3.0))
        self.assertFalse(plan.still_static([3.0, 4.0], 3.0))
        self.assertFalse(plan.still_static([], 3.0))


class Eulers(unittest.TestCase):

    def test_whole_turns_come_off(self):
        self.assertEqual(plan.closest_euler((10.0, 20.0, 30.0), (370.0, -340.0, 30.0), 0),
                         (10.0, 20.0, 30.0))

    def test_the_other_solution_is_taken_when_nearer(self):
        """(a+180, 180-b, c+180) is the same rotation in xyz (middle y)."""
        self.assertEqual(plan.closest_euler((10.0, 20.0, 30.0), (190.0, 160.0, 210.0), 0),
                         (10.0, 20.0, 30.0))

    def test_the_middle_axis_follows_the_rotate_order(self):
        """zxy (2): the middle axis is x."""
        self.assertEqual(plan.closest_euler((10.0, 20.0, 30.0), (170.0, 200.0, 210.0), 2),
                         (10.0, 20.0, 30.0))

    def test_a_spin_stays_a_spin(self):
        rows = [(0.0, 170.0, 0.0), (0.0, -170.0, 0.0), (0.0, -150.0, 0.0)]
        self.assertEqual(plan.continuous_eulers((0.0, 160.0, 0.0), rows, 0),
                         [(0.0, 170.0, 0.0), (0.0, 190.0, 0.0), (0.0, 210.0, 0.0)])

    def test_no_anchor_keeps_the_first_row(self):
        rows = [(0.0, 300.0, 0.0), (0.0, -50.0, 0.0)]
        self.assertEqual(plan.continuous_eulers(None, rows, 0),
                         [(0.0, 300.0, 0.0), (0.0, 310.0, 0.0)])

    def test_one_channel_by_whole_turns(self):
        self.assertEqual(plan.continuous_channel(350.0, [-5.0, 10.0, 375.0]),
                         [355.0, 370.0, 375.0])
        self.assertEqual(plan.continuous_channel(None, [10.0, 380.0]), [10.0, 20.0])


class Parent(unittest.TestCase):

    IDENTITY = [1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0, 0, 5.0, 6.0, 7.0, 1.0]

    def test_an_even_parent_is_fine(self):
        self.assertEqual(plan.uneven_parent("a", self.IDENTITY), "")
        even = [2.0, 0, 0, 0, 0, 2.0, 0, 0, 0, 0, 2.0, 0, 0, 0, 0, 1.0]
        self.assertEqual(plan.uneven_parent("a", even), "")

    def test_uneven_sheared_or_mirrored_refuses(self):
        uneven = [1.0, 0, 0, 0, 0, 2.5, 0, 0, 0, 0, 0.7, 0, 0, 0, 0, 1.0]
        sheared = [1.0, 0, 0, 0, 0.5, 1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0]
        mirrored = [-1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0]
        for matrix in (uneven, sheared, mirrored):
            self.assertIn("parent is scaled unevenly", plan.uneven_parent("cube", matrix))

    def test_a_zero_scale_refuses(self):
        zero = [0.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0]
        self.assertIn("scaled to zero", plan.uneven_parent("cube", zero))


class TakeRange(unittest.TestCase):

    def test_playback_and_animation_together(self):
        self.assertEqual(plan.take_range((10.0, 20.0), (0.0, 40.0)), (0.0, 40.0))
        self.assertEqual(plan.take_range((-5.0, 50.0), (0.0, 40.0)), (-5.0, 50.0))


class Size(unittest.TestCase):

    def test_a_third_of_the_diagonal(self):
        self.assertAlmostEqual(plan.knot_size(30.0), 10.0)

    def test_never_below_three_cm(self):
        self.assertAlmostEqual(plan.knot_size(1.0), plan.MIN_SIZE)

    def test_a_joint_without_a_shape_from_its_radius(self):
        self.assertAlmostEqual(plan.knot_size(0.0, 4.0), 8.0)
        self.assertAlmostEqual(plan.knot_size(0.0, 0.5), plan.MIN_SIZE)

    def test_nothing_known_is_the_default(self):
        self.assertAlmostEqual(plan.knot_size(0.0, None), plan.DEFAULT_SIZE)

    def test_the_outer_node_is_bigger(self):
        self.assertGreater(plan.OUTER_SCALE, 1.0)


class BakeOrder(unittest.TestCase):

    def test_a_knot_on_a_knot_bakes_first(self):
        """B carries A's motion (B's source is A): B's edits go into A first, then A into the
        object."""
        self.assertEqual(plan.bake_order([("A", "obj"), ("B", "A")]), ["B", "A"])

    def test_a_chain_of_three(self):
        self.assertEqual(plan.bake_order([("A", "obj"), ("C", "B"), ("B", "A")]),
                         ["C", "B", "A"])

    def test_independent_knots_keep_their_order(self):
        self.assertEqual(plan.bake_order([("A", "o1"), ("B", "o2")]), ["A", "B"])


class Pivot(unittest.TestCase):

    def test_the_selected_pivot(self):
        self.assertEqual(plan.choose_pivot(["p1"], ["p1", "p2"]), ("p1", ""))

    def test_the_only_waiting_pivot(self):
        self.assertEqual(plan.choose_pivot([], ["p1"]), ("p1", ""))

    def test_none_waiting(self):
        pivot, refusal = plan.choose_pivot([], [])
        self.assertIsNone(pivot)
        self.assertIn("press Offset first", refusal)

    def test_several_waiting_and_none_selected_refuses_naming_them(self):
        pivot, refusal = plan.choose_pivot([], ["|g|a_pivotSpace|a_pivot", "|g|b_pivotSpace|b_pivot"])
        self.assertIsNone(pivot)
        self.assertIn("a_pivot", refusal)
        self.assertIn("b_pivot", refusal)

    def test_several_selected_refuses(self):
        pivot, refusal = plan.choose_pivot(["a", "b"], ["a", "b"])
        self.assertIsNone(pivot)
        self.assertIn("select the one to finish", refusal)


class Messages(unittest.TestCase):

    def test_one_object(self):
        line = plan.created_message("Knot", [("FKShoulder_R", "FKShoulder_R_knot")],
                                    (0.0, 120.0, False))
        self.assertEqual(line, "Knot: FKShoulder_R rides FKShoulder_R_knot over 0-120")

    def test_several_objects_and_a_range(self):
        line = plan.created_message("Knot Orient", [("a", "a_k"), ("b", "b_k")],
                                    (9.0, 30.0, True))
        self.assertIn("2 objects ride knots", line)
        self.assertIn("10-29", line)
        self.assertIn("attach", line)

    def test_the_offset_button_label(self):
        self.assertEqual(plan.offset_label(False), "Offset")
        self.assertEqual(plan.offset_label(True), "Finish")

    def test_subtitle(self):
        self.assertEqual(plan.subtitle(0, 0), "no knots in the scene")
        self.assertEqual(plan.subtitle(1, 0), "1 knot in the scene")
        self.assertEqual(plan.subtitle(3, 1), "3 knots in the scene, 1 pivot waiting")
        self.assertEqual(plan.subtitle(0, 2), "2 pivots waiting")

    def test_bake_and_remove_lines(self):
        self.assertIn("Baked 2 knots", plan.baked_message(["a", "b"]))
        self.assertIn("a, b", plan.baked_message(["a", "b"]))
        line = plan.removed_message(["a"], 1)
        self.assertIn("Removed 1 knot", line)
        self.assertIn("1 pivot", line)
        self.assertIn("own animation", line)

    def test_riding_refusal_names_the_way_out(self):
        line = plan.riding_refusal("sword")
        self.assertIn("sword", line)
        self.assertIn("Bake", line)

    def test_begin_and_finish(self):
        self.assertIn("press Finish", plan.begin_message("sword"))
        self.assertIn("sword", plan.finish_message("sword", "sword_knotOffset",
                                                   (0.0, 10.0, False)))


class ParentTab(unittest.TestCase):
    """The parent tab (2026-10-12): Inside, World, Swap, Across, Multiple across, Attach 0 / 1."""

    PARENTS = {"|P|X": "|P", "|P|X|Y": "|P|X", "|B": None, "|P": None, "|W": None}

    def test_inside_refusals(self):
        self.assertEqual(plan.inside_refusal(["|W"], "|B", self.PARENTS.get), "")
        self.assertIn("already inside", plan.inside_refusal(["|P|X"], "|P", self.PARENTS.get))
        self.assertIn("lies inside", plan.inside_refusal(["|P|X"], "|P|X|Y", self.PARENTS.get))
        self.assertIn("is the parent", plan.inside_refusal(["|B"], "|B", self.PARENTS.get))

    def test_world_refusal(self):
        self.assertEqual(plan.world_refusal(["|P|X"], self.PARENTS.get), "")
        self.assertIn("already at world level", plan.world_refusal(["|W"], self.PARENTS.get))

    def test_swap_plan_parent_then_child(self):
        """P > X > Y, X then Y selected: Y goes under P, X under Y."""
        moves, refusal = plan.swap_plan(["|P|X", "|P|X|Y"], self.PARENTS.get)
        self.assertEqual(refusal, "")
        self.assertEqual(moves, [("|P|X", "|P|X|Y"), ("|P|X|Y", "|P")])

    def test_swap_plan_at_world(self):
        moves, refusal = plan.swap_plan(["|W", "|B"], self.PARENTS.get)
        self.assertEqual(moves, [("|W", "|B"), ("|B", None)])

    def test_swap_refusals(self):
        self.assertIn("two", plan.swap_plan(["|W"], self.PARENTS.get)[1])
        moves, refusal = plan.swap_plan(["|P|X|Y", "|P|X"], self.PARENTS.get)
        self.assertIsNone(moves)
        self.assertIn("select the parent first", refusal)

    def test_attach_times(self):
        self.assertEqual(plan.attach_times((10.0, 30.0), [], 5.0), (10.0, 29.0))
        self.assertEqual(plan.attach_times(None, [3.0, 8.0, 5.0], 5.0), (3.0, 8.0))
        self.assertEqual(plan.attach_times(None, [], 12.0), (12.0,))
        self.assertEqual(plan.attach_times((10.0, 11.0), [4.0], 12.0), (4.0,))

    def test_list_labels(self):
        self.assertEqual(plan.list_label("Objects", 3), "Objects 3")
        self.assertEqual(plan.list_label("Targets", 0), "Targets")

    def test_multiple_refusals(self):
        self.assertIn("remember", plan.multiple_refusal(0, 2, True, True))
        self.assertIn("must match", plan.multiple_refusal(2, 3, True, True))
        self.assertIn("Rotate or Translate", plan.multiple_refusal(2, 2, False, False))
        self.assertEqual(plan.multiple_refusal(2, 2, True, False), "")

    def test_lines_name_the_way_out(self):
        self.assertIn("Across", plan.rig_part_line("FKShoulder_R", "a control of Manny_Rig"))
        self.assertIn("locked", plan.locked_line("prop"))
        self.assertIn("scale", plan.scale_line("prop"))
        self.assertIn("carrier", plan.uneven_target("prop", "carrier",
                                                    [1.0, 0, 0, 0, 0, 3.0, 0, 0, 0, 0, 1.0, 0,
                                                     0, 0, 0, 1.0]))
        self.assertEqual(plan.uneven_target("prop", "carrier", Parent.IDENTITY), "")
        line = plan.reparent_message("Inside", ["prop", "cup"], "carrier", (0.0, 40.0, False))
        self.assertIn("2 objects", line)
        self.assertIn("carrier", line)
        self.assertIn("0-40", line)
        self.assertIn("world level", plan.reparent_message("World", ["prop"], None,
                                                           (0.0, 40.0, False)))
        self.assertIn("attach 0", plan.attach_message(0.0, 2, (12.0,)))
        self.assertIn("10-29", plan.attach_message(1.0, 1, (10.0, 29.0)))


class Aim(unittest.TestCase):
    """The aim tab (2026-10-13): where the locators start, the vectors from the placement, which
    waiting aims a Finish means, the button and the lines."""

    def test_the_reach(self):
        self.assertEqual(plan.aim_reach(5.0), 20.0)

    def test_the_vectors_from_the_placement(self):
        aim, up, refusal = plan.aim_vectors("prop", (20.0, 0.0, 0.0), (3.0, 20.0, 0.0))
        self.assertEqual(refusal, "")
        self.assertEqual(aim, (1.0, 0.0, 0.0))
        self.assertAlmostEqual(up[1], 1.0)
        self.assertAlmostEqual(up[0], 0.0)              # made perpendicular to the aim

    def test_a_target_on_the_object_is_refused(self):
        aim, _up, refusal = plan.aim_vectors("prop", (0.0, 0.0, 0.0), (0.0, 20.0, 0.0))
        self.assertIsNone(aim)
        self.assertIn("prop", refusal)
        self.assertIn("target", refusal)

    def test_an_up_on_the_line_to_the_target_is_refused(self):
        _aim, up, refusal = plan.aim_vectors("prop", (20.0, 0.0, 0.0), (40.0, 0.5, 0.0))
        self.assertIsNone(up)
        self.assertIn("up", refusal)
        self.assertEqual(plan.aim_vectors("prop", (20.0, 0.0, 0.0), (0.0, 0.0, 0.0))[2] != "",
                         True)

    def test_axes_take_the_scale_out(self):
        m = [2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 3.0, 0.0, 0.0, -4.0, 0.0, 0.0, 5.0, 6.0, 7.0, 1.0]
        rows = plan.axes_of(m)
        self.assertEqual([tuple(round(c, 9) for c in row) for row in rows],
                         [(1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0)])

    def test_which_aims_finish(self):
        self.assertEqual(plan.choose_aims(["|a"], ["|a", "|b"]), (["|a"], ""))
        self.assertEqual(plan.choose_aims([], ["|a", "|b"]), (["|a", "|b"], ""))
        found, refusal = plan.choose_aims([], [])
        self.assertIsNone(found)
        self.assertIn("press Aim first", refusal)

    def test_the_button_and_the_lines(self):
        self.assertEqual(plan.aim_label(False), "Aim")
        self.assertEqual(plan.aim_label(True), "Finish")
        self.assertIn("Finish", plan.aim_begin_message(["prop"]))
        self.assertIn("2 objects", plan.aim_begin_message(["a", "b"]))
        line = plan.aim_finish_message([("prop", "prop_aimTarget")], (0.0, 40.0, False))
        self.assertIn("prop aims at prop_aimTarget", line)
        self.assertIn("2 objects aim", plan.aim_finish_message([("a", "x"), ("b", "y")],
                                                               (9.0, 21.0, True)))

    def test_the_subtitle_counts_waiting_aims(self):
        self.assertEqual(plan.subtitle(2, 0, 1), "2 knots in the scene, 1 aim waiting")
        self.assertEqual(plan.subtitle(0, 1, 2), "1 pivot waiting, 2 aims waiting")
        self.assertEqual(plan.subtitle(0, 0), "no knots in the scene")


class Layer(unittest.TestCase):
    """Bake to an additive layer (2026-10-13): what each constraint is, and the differences."""

    def test_what_a_constraint_is(self):
        self.assertEqual(plan.driver_kind(True, False, False, False), "knot")
        self.assertEqual(plan.driver_kind(False, True, True, True), "retarget")
        self.assertEqual(plan.driver_kind(False, False, True, True), "ours")
        self.assertEqual(plan.driver_kind(False, False, False, True), "rig")
        self.assertEqual(plan.driver_kind(False, False, False, False), "foreign")

    def test_the_refusals_name_the_object_and_the_constraint(self):
        self.assertEqual(plan.driver_refusal("knot", "prop", "c"), "")
        self.assertEqual(plan.driver_refusal("foreign", "prop", "c"), "")
        for kind, word in (("retarget", "Retarget"), ("ours", "its own card"),
                           ("rig", "break the rig")):
            line = plan.driver_refusal(kind, "FKWrist_R", "FKWrist_R_parentConstraint1")
            self.assertIn("FKWrist_R", line)
            self.assertIn("FKWrist_R_parentConstraint1", line)
            self.assertIn(word, line)

    def test_a_still_object(self):
        self.assertIn("nothing animates prop", plan.undriven_refusal("prop", []))
        line = plan.undriven_refusal("prop", ["an expression", "a driven key", "an expression"])
        self.assertIn("an expression and a driven key", line)
        self.assertIn("on layers already", plan.undriven_refusal("prop", [], layered=True))

    def test_the_layer_name(self):
        self.assertEqual(plan.layer_name(["prop"]), "Baked_prop")
        self.assertEqual(plan.layer_name(["Manny_Rig:FKWrist_R", "b"]), "Baked_FKWrist_R")

    def test_translate_differences(self):
        own = [(0.0, 0.0, 0.0, 0.0, 0.0, 0.0), (1.0, 0.0, 0.0, 0.0, 0.0, 0.0)]
        shown = [(0.0, 2.0, 0.0, 0.0, 0.0, 0.0), (1.5, 2.0, 0.0, 0.0, 0.0, 0.0)]
        out = plan.layer_deltas(shown, own, 0, plan.CHANNELS)
        self.assertEqual(sorted(out), ["tx", "ty"])
        self.assertEqual(out["tx"], [0.0, 0.5])
        self.assertEqual(out["ty"], [2.0, 2.0])

    def test_a_difference_under_the_minimum_is_left_out(self):
        own = [(0.0,) * 6] * 3
        shown = [(0.00005, 0.0, 0.0, 0.0, 0.0, 0.00009)] * 3
        self.assertEqual(plan.layer_deltas(shown, own, 0, plan.CHANNELS), {})

    def test_only_free_channels(self):
        own = [(0.0,) * 6]
        shown = [(1.0, 1.0, 1.0, 0.0, 0.0, 0.0)]
        self.assertEqual(sorted(plan.layer_deltas(shown, own, 0, ("tx", "tz"))), ["tx", "tz"])

    def test_a_turn_through_180_stays_continuous(self):
        """The shown euler follows the frame before it, never the own one alone: a constraint
        spinning the object 0 -> 360 about Y reads as one turn on the layer, not a jump at 180."""
        own = [(0.0,) * 6] * 5
        shown = [(0.0, 0.0, 0.0, 0.0, y, 0.0) for y in (0.0, 90.0, 179.0, -91.0, -1.0)]
        out = plan.layer_deltas(shown, own, 0, plan.CHANNELS)
        self.assertEqual(sorted(out), ["ry"])
        self.assertEqual([round(v, 6) for v in out["ry"]], [0.0, 90.0, 179.0, 269.0, 359.0])

    def test_the_layer_lands_the_shown_rotation(self):
        """own + difference = the shown rotation, whichever euler the walk read it as."""
        own = [(0.0, 0.0, 0.0, 10.0, 20.0, 30.0)]
        shown = [(0.0, 0.0, 0.0, 10.0 + 180.0, 180.0 - 25.0, 30.0 + 180.0)]
        out = plan.layer_deltas(shown, own, 0, plan.CHANNELS)
        self.assertEqual(round(out["ry"][0], 6), 5.0)
        self.assertNotIn("rx", out)
        self.assertNotIn("rz", out)

    def test_with_a_locked_rotate_whole_turns_only(self):
        own = [(0.0,) * 6] * 2
        shown = [(0.0, 0.0, 0.0, 0.0, 350.0, 0.0), (0.0, 0.0, 0.0, 0.0, -5.0, 0.0)]
        out = plan.layer_deltas(shown, own, 0, ("ry", "rz"))
        self.assertEqual([round(v, 6) for v in out["ry"]], [-10.0, -5.0])

    def test_the_line(self):
        line = plan.layer_message(["prop"], 1, 1, 1, 0.0, 48.0, False, "Baked_prop",
                                  pose_frame=0.0)
        self.assertIn("prop baked onto Baked_prop over 0-48", line)
        self.assertIn("its keys, 1 knot and 1 constraint moved onto it", line)
        self.assertIn("the base holds the pose of frame 0", line)
        line = plan.layer_message(["prop"], 1, 0, 0, 0.0, 48.0, False, "Baked_prop")
        self.assertIn("its keys moved onto it", line)
        self.assertIn("each base holds the pose of its first frame", line)
        line = plan.layer_message(["a", "b"], 2, 0, 2, 10.0, 20.0, True, "Baked_a", ["note"])
        self.assertIn("2 objects", line)
        self.assertIn("their keys and 2 constraints", line)
        self.assertIn("outside the highlight", line)
        self.assertTrue(line.endswith("note"))
        line = plan.layer_message(["prop"], 0, 1, 0, 0.0, 48.0, False, "")
        self.assertIn("1 knot taken off; nothing changed", line)
        self.assertIn("no layer", line)

    def test_every_difference_on_request(self):
        own = [(0.0,) * 6] * 2
        shown = [(0.00005, 0.0, 0.0, 0.0, 0.0, 0.0)] * 2
        out = plan.layer_deltas(shown, own, 0, plan.CHANNELS, minimum=-1.0)
        self.assertEqual(sorted(out), sorted(plan.CHANNELS))

    def test_anchored_at_the_first_frame(self):
        """The whole take: the base takes the first frame's difference, so the layer starts at 0
        and a channel left with nothing is dropped."""
        kept, shifts = plan.anchored({"tx": [2.0, 3.0, 5.0], "ry": [10.0, 10.0, 10.0],
                                      "tz": [0.0, 0.0, 0.0]})
        self.assertEqual(kept, {"tx": [0.0, 1.0, 3.0]})
        self.assertEqual(shifts, {"tx": 2.0, "ry": 10.0, "tz": 0.0})

    def test_how_a_curve_bridges_exactly(self):
        self.assertEqual(plan.bridge_kind(["fixed", "spline", "auto"], False), "smooth")
        self.assertEqual(plan.bridge_kind(["step", "step"], False), "stepped")
        self.assertIsNone(plan.bridge_kind(["step", "spline"], False))
        self.assertIsNone(plan.bridge_kind(["spline", "stepnext"], False))
        self.assertIsNone(plan.bridge_kind(["spline"], True))

    def test_the_bridge_keys_are_differences(self):
        keys = [(9.0, 1.0, 0.5, 0.5), (12.0, 4.0, 1.0, -2.0), (21.0, 3.0, 0.2, 0.2)]
        bridge = [(1.0, 0.5, 0.5), (2.5, 0.25, 0.25), (3.0, 0.2, 0.2)]
        self.assertEqual(plan.bridge_keys(keys, bridge),
                         [(9.0, 0.0, 0.0, 0.0), (12.0, 1.5, 0.75, -2.25), (21.0, 0.0, 0.0, 0.0)])

    def test_the_bridge(self):
        """A highlight 10-20: the base's keys strictly between 9 and 21 go."""
        self.assertEqual(plan.bridged([0.0, 9.0, 10.0, 15.5, 20.0, 21.0, 30.0], 10.0, 20.0),
                         [10.0, 15.5, 20.0])
        self.assertEqual(plan.bridged([0.0, 40.0], 10.0, 20.0), [])


class Purity(unittest.TestCase):

    def test_stdlib_only(self):
        """The plan answers with no Maya at all (a subprocess with a clean interpreter)."""
        plugin = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "SkeldarAnim")
        code = ("import sys; sys.path.insert(0, %r); import maya_tools.knotplan; "
                "print(sorted(m for m in sys.modules if m.startswith('maya')))" % plugin)
        out = subprocess.check_output([sys.executable, "-c", code], cwd=plugin)
        self.assertEqual(out.decode().strip(), "['maya_tools', 'maya_tools.knotplan']")


if __name__ == "__main__":
    unittest.main()
