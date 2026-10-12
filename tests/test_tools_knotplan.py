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

    def test_the_five_kinds_in_the_cards_order(self):
        self.assertEqual([k.key for k in plan.KINDS],
                         ["knot", "offset", "orient", "double_local", "double_world"])

    def test_the_double_knots_have_an_inner_node_the_others_do_not(self):
        for kind in plan.KINDS:
            self.assertEqual(bool(kind.inner_suffix), kind.key.startswith("double"), kind.key)
            self.assertEqual(kind.inner_colour is not None, kind.key.startswith("double"))

    def test_only_knot_orient_follows_by_orientation(self):
        self.assertEqual([k.key for k in plan.KINDS if k.constraint == "orient"], ["orient"])
        self.assertTrue(all(k.constraint in ("parent", "orient") for k in plan.KINDS))

    def test_suffixes_are_distinct_and_name_safe(self):
        suffixes = [k.suffix for k in plan.KINDS] + [k.inner_suffix for k in plan.KINDS
                                                     if k.inner_suffix]
        suffixes += [plan.PIVOT_SUFFIX, plan.PIVOT_SPACE_SUFFIX]
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
                     plan.GROUP_MARKER, plan.ORDER_MARKER):
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
        self.assertIn("press Knot Offset first", refusal)

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
        self.assertEqual(plan.offset_label(False), "Knot Offset")
        self.assertEqual(plan.offset_label(True), "Finish offset")

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
        self.assertIn("Finish offset", plan.begin_message("sword"))
        self.assertIn("sword", plan.finish_message("sword", "sword_knotOffset",
                                                   (0.0, 10.0, False)))


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
