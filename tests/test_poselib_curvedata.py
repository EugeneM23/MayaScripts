"""maya_poselib.curvedata - the pure rules of an animation card's ORIGINAL curves (spec
2026-10-28-pose-library-curves-and-layers-design.md): the layer records, the curves file's check,
the header's `curves` block, the layers a paste picks, which controls a card keeps, the pairing of
the card's nodes and layers on the target, Connect's one-layer rule. Stdlib data only."""

import unittest

from maya_poselib import curvedata as cd

BASE = cd.layer_record(cd.BASE, base=True)
ADD = cd.layer_record("tab1:AnimLayer1", weight=0.5)
OVER = cd.layer_record("Fix", override=True)
KEYED = {"keys": [[0.0, 1.0, "auto", "auto", 0.0, 1.0, 0.0, 1.0]], "weighted": False,
         "breakdown": []}


def nodes(*names):
    return [{"name": name, "attrs": {"rotateX": {cd.BASE: KEYED, "AnimLayer1": {"static": 2.0}}}}
            for name in names]


class LayerRecord(unittest.TestCase):

    def test_a_layer_keeps_its_leaf_name_and_settings(self):
        self.assertEqual(ADD, {"name": "AnimLayer1", "base": False, "override": False,
                               "weight": 0.5, "mute": False, "rotation": "component",
                               "scale": "multiply"})

    def test_the_base_is_always_named_base_animation(self):
        self.assertEqual(cd.layer_record("skeldarTabsLayerRoot", base=True)["name"], cd.BASE)
        self.assertTrue(BASE["base"])


class Check(unittest.TestCase):

    def test_a_whole_file_passes_and_comes_back(self):
        data = {"version": 1, "nodes": nodes("FKWrist_R")}
        self.assertIs(cd.check(data, [cd.BASE, "AnimLayer1"]), data)

    def test_a_layer_the_header_does_not_name_is_broken(self):
        with self.assertRaises(ValueError):
            cd.check({"version": 1, "nodes": nodes("a")}, [cd.BASE])

    def test_wrong_shapes_are_broken(self):
        nan = float("nan")
        for bad in (None, [], {"nodes": "x"}, {"nodes": [{"name": 1, "attrs": {}}]},
                    {"nodes": [{"name": "a", "attrs": {"rx": []}}]},
                    {"nodes": [{"name": "a", "attrs": {"rx": {}}}]},
                    {"nodes": [{"name": "a", "attrs": {"rx": {cd.BASE: {"keys": [[0.0, nan]]}}}}]},
                    {"nodes": [{"name": "a", "attrs": {"rx": {cd.BASE: {"static": "x"}}}}]},
                    {"nodes": [{"name": "a", "attrs": {"rx": {cd.BASE: {"static": True}}}}]}):
            with self.assertRaises(ValueError, msg=repr(bad)):
                cd.check(bad, [cd.BASE])


class Header(unittest.TestCase):

    def test_summary_and_reading_it_back(self):
        block = cd.summary([BASE, ADD], 3)
        self.assertEqual(block, {"layers": [BASE, ADD], "nodes": 3})
        header = {"curves": block}
        self.assertTrue(cd.has_curves(header))
        self.assertEqual(cd.layer_names(header), [cd.BASE, "AnimLayer1"])
        self.assertEqual(cd.records(header), [BASE, ADD])

    def test_no_block_or_a_broken_one_is_no_curves(self):
        for header in (None, {}, {"curves": None}, {"curves": {"layers": []}},
                       {"curves": {"layers": "x"}}, {"curves": {"layers": [{"name": 1}]}},
                       {"curves": {"layers": [ADD]}}):          # the first record is no base
            self.assertFalse(cd.has_curves(header), header)
            self.assertEqual(cd.layer_names(header), [])

    def test_has_keys_wants_one_keyed_curve(self):
        self.assertFalse(cd.has_keys([{cd.BASE: {"static": 1.0}}]))
        self.assertFalse(cd.has_keys([{cd.BASE: {"keys": []}}]))
        self.assertTrue(cd.has_keys([{cd.BASE: {"static": 1.0}}, {"AnimLayer1": KEYED}]))


class Chosen(unittest.TestCase):

    def test_none_is_every_layer_in_the_cards_order(self):
        self.assertEqual(cd.chosen([cd.BASE, "A", "B"], None), [cd.BASE, "A", "B"])

    def test_a_pick_keeps_the_cards_order_and_drops_unknown_names(self):
        self.assertEqual(cd.chosen([cd.BASE, "A", "B"], ["B", "Z", cd.BASE]), [cd.BASE, "B"])

    def test_connect_needs_exactly_one_layer(self):
        self.assertTrue(cd.connect_ok(["A"]))
        self.assertFalse(cd.connect_ok([cd.BASE, "A"]))
        self.assertFalse(cd.connect_ok([]))


class KeepsControl(unittest.TestCase):

    def test_a_control_whose_bones_meet_the_members(self):
        self.assertTrue(cd.keeps_control(["hand_l"], ["hand_l", "lowerarm_l"], False))
        self.assertFalse(cd.keeps_control(["hand_r"], ["hand_l"], False))
        self.assertFalse(cd.keeps_control([], ["hand_l"], True))

    def test_main_only_with_a_whole_body_card(self):
        self.assertTrue(cd.keeps_control(cd.WHOLE, ["pelvis"], True))
        self.assertFalse(cd.keeps_control(cd.WHOLE, ["hand_l"], False))


class PairNodes(unittest.TestCase):

    def test_by_leaf_namespace_and_path_ignored(self):
        def leaf(path):
            return path.split("|")[-1].split(":")[-1]
        paired, missing = cd.pair_nodes(
            ["FKWrist_R", "Main", "FKGone_L"],
            ["|Manny_Rig1:grp|Manny_Rig1:FKWrist_R", "|Manny_Rig1:Main"], leaf)
        self.assertEqual(paired, {"FKWrist_R": "|Manny_Rig1:grp|Manny_Rig1:FKWrist_R",
                                  "Main": "|Manny_Rig1:Main"})
        self.assertEqual(missing, ["FKGone_L"])


class LayerTarget(unittest.TestCase):

    EXISTING = [
        {"name": "tab1:AnimLayer1", "override": False, "rotation": "component", "locked": False},
        {"name": "Fix", "override": False, "rotation": "component", "locked": False},
        {"name": "Held", "override": False, "rotation": "component", "locked": True}]

    def test_the_base_goes_to_the_base(self):
        self.assertEqual(cd.layer_target(BASE, self.EXISTING), ("base", None))

    def test_a_namesake_of_the_same_mode_takes_it(self):
        self.assertEqual(cd.layer_target(ADD, self.EXISTING), ("layer", "tab1:AnimLayer1"))

    def test_a_namesake_of_another_mode_makes_a_new_one(self):
        self.assertEqual(cd.layer_target(OVER, self.EXISTING), ("make", None))

    def test_another_rotation_accumulation_makes_a_new_one(self):
        record = cd.layer_record("Fix", rotation="quaternion")
        self.assertEqual(cd.layer_target(record, self.EXISTING), ("make", None))

    def test_a_locked_namesake_is_refused(self):
        self.assertEqual(cd.layer_target(cd.layer_record("Held"), self.EXISTING),
                         ("refused", "Held"))

    def test_no_namesake_makes_one(self):
        self.assertEqual(cd.layer_target(cd.layer_record("New"), self.EXISTING), ("make", None))


class PerLayer(unittest.TestCase):

    def test_a_plain_objects_curve_is_the_bases(self):
        self.assertEqual(cd.per_layer(KEYED), {cd.BASE: KEYED})

    def test_a_layered_one_answers_its_layers(self):
        curve = dict(KEYED, layers={cd.BASE: KEYED, "A": {"static": 1.0}})
        self.assertEqual(cd.per_layer(curve), {cd.BASE: KEYED, "A": {"static": 1.0}})


class ConnectOffset(unittest.TestCase):

    def test_the_difference_over_the_weight(self):
        self.assertAlmostEqual(cd.connect_offset(10.0, 4.0, 0.5), 12.0)
        self.assertAlmostEqual(cd.connect_offset(10.0, 4.0, 1.0), 6.0)

    def test_weight_zero_moves_nothing(self):
        self.assertIsNone(cd.connect_offset(10.0, 4.0, 0.0))


class FirstPerson(unittest.TestCase):
    """2026-10-29: a card saved off a rig in 1P pasted its raw curves onto a 3P rig 180 deg off."""

    def test_the_block_says_it(self):
        header = {"curves": cd.summary([BASE], 3, first_person=True)}
        self.assertTrue(cd.saved_in_first_person(header))
        self.assertNotIn("first_person", cd.summary([BASE], 3))

    def test_a_card_saved_before_is_known_by_its_layers(self):
        layers = [BASE, cd.layer_record("_3P_Lower_Body1"), cd.layer_record("Fix")]
        self.assertTrue(cd.saved_in_first_person({"curves": cd.summary(layers, 1)}))
        self.assertFalse(cd.saved_in_first_person({"curves": cd.summary([BASE, ADD], 1)}))
        self.assertFalse(cd.saved_in_first_person({}))


class Identity(unittest.TestCase):

    def test_scale_by_multiply_is_one_everything_else_zero(self):
        self.assertEqual(cd.identity("scaleY"), 1.0)
        self.assertEqual(cd.identity("scaleY", "additive"), 0.0)
        self.assertEqual(cd.identity("rotateX"), 0.0)
        self.assertEqual(cd.identity("translateZ", "additive"), 0.0)


class Pinned(unittest.TestCase):
    """The range's ends held, so a target key outside them bends nothing inside."""

    KEYS = [[5.0, 1.0, "auto", "auto"], [8.0, 3.0, "spline", "linear"]]

    def test_a_curve_inside_the_range_is_held_at_both_ends(self):
        out = cd.pinned(self.KEYS, 0.0, 10.0)
        self.assertEqual(out[0], [0.0, 1.0, "flat", "step"])
        self.assertEqual(out[2], [8.0, 3.0, "spline", "step"])
        self.assertEqual(out[3], [10.0, 3.0, "flat", "flat"])
        self.assertEqual(self.KEYS[1][3], "linear")

    def test_nothing_outside_to_hold_against_adds_nothing(self):
        self.assertEqual(cd.pinned(self.KEYS, 0.0, 10.0, before=False, after=False), self.KEYS)

    def test_a_curve_reaching_the_ends_is_kept(self):
        keys = [[0.0, 1.0], [10.0, 2.0]]
        self.assertEqual(cd.pinned(keys, 0.0, 10.0), keys)

    def test_a_short_key_gets_its_types_filled(self):
        self.assertEqual(cd.pinned([[0.0, 4.0]], 0.0, 6.0),
                         [[0.0, 4.0, None, "step"], [6.0, 4.0, "flat", "flat"]])

    def test_no_keys_none(self):
        self.assertEqual(cd.pinned([], 0.0, 6.0), [])

    def test_an_end_key_beside_a_target_key_keeps_the_angles_it_showed(self):
        keys = [[0.0, 1.0, "auto", "auto", 10.0, 1.0, 10.0, 1.0],
                [5.0, 2.0, "spline", "linear", 4.0, 1.0, 4.0, 1.0],
                [10.0, 3.0, "clamped", "plateau", -3.0, 1.0, -3.0, 1.0]]
        out = cd.pinned(keys, 0.0, 10.0)
        self.assertEqual([k[2:4] for k in out], [["fixed", "fixed"], ["spline", "linear"],
                                                 ["fixed", "fixed"]])
        self.assertEqual(out[0][4:], [10.0, 1.0, 10.0, 1.0])
        out = cd.pinned(keys, 0.0, 10.0, before=False, after=False)
        self.assertEqual(out, keys)

    def test_a_stable_type_is_kept(self):
        keys = [[0.0, 1.0, "linear", "flat", 0.0, 1.0, 0.0, 1.0]]
        self.assertEqual(cd.pinned(keys, 0.0, 0.0), keys)


class Bounded(unittest.TestCase):
    """A layer curve the paste makes adds nothing outside the range the target animates."""

    def test_identity_a_frame_either_side_stepped_in(self):
        out = cd.bounded([[5.0, 2.0], [8.0, 4.0]], 0.0, 10.0, 0.0)
        self.assertEqual(out, [[-1.0, 0.0, "flat", "step"], [0.0, 2.0, "flat", "step"],
                               [5.0, 2.0], [8.0, 4.0, None, "step"], [10.0, 4.0, "flat", "step"],
                               [11.0, 0.0, "flat", "flat"]])

    def test_only_the_sides_the_target_animates(self):
        out = cd.bounded([[0.0, 2.0], [10.0, 4.0]], 0.0, 10.0, 1.0, before=False)
        self.assertEqual(out, [[0.0, 2.0], [10.0, 4.0, None, "step"], [11.0, 1.0, "flat", "flat"]])
        self.assertEqual(cd.bounded([], 0.0, 10.0, 0.0), [])


if __name__ == "__main__":
    unittest.main()
