"""A character swapped for another keeps its animation layers (2026-10-29): the pure rules and
the reading / writing halves on a fake `cmds`.

The scene half is proved by docs/superpowers/plans/verify_swap_keep_layers.py in mayapy
standalone."""

import sys
import types
import unittest


def _install_fake_maya():
    try:
        import maya.cmds  # noqa: F401
        return
    except ImportError:
        pass
    maya = types.ModuleType("maya")
    cmds = types.ModuleType("maya.cmds")
    maya.cmds = cmds
    sys.modules.setdefault("maya", maya)
    sys.modules["maya.cmds"] = cmds


_install_fake_maya()

from maya_poselib import curvedata                            # noqa: E402
from maya_scenesetup import swaplayers                         # noqa: E402


def _record(name, **kwargs):
    return curvedata.layer_record(name, **kwargs)


class Buttons(unittest.TestCase):

    def test_each_button_answers_one_word(self):
        self.assertEqual(swaplayers.answer_of(swaplayers.KEEP), "keep")
        self.assertEqual(swaplayers.answer_of(swaplayers.BAKE), "bake")
        self.assertEqual(swaplayers.answer_of(swaplayers.CANCEL), "cancel")

    def test_a_dismissed_dialog_cancels(self):
        self.assertEqual(swaplayers.answer_of(None), "cancel")
        self.assertEqual(swaplayers.answer_of(""), "cancel")


class Keepable(unittest.TestCase):

    def test_an_additive_quaternion_layer_cannot_be_kept(self):
        record = _record("Spin", rotation="quaternion")
        self.assertTrue(swaplayers.quaternion_layer(record))
        self.assertEqual(swaplayers.keepable([record]), {"Spin": False})

    def test_an_override_quaternion_layer_is_kept(self):
        record = _record("Spin", rotation="quaternion", override=True)
        self.assertFalse(swaplayers.quaternion_layer(record))

    def test_a_plain_additive_layer_is_kept(self):
        self.assertEqual(swaplayers.keepable([_record("Fix")]), {"Fix": True})


class Cuts(unittest.TestCase):

    def test_one_cut_a_layer_the_base_first(self):
        plan = swaplayers.cut_plan(["A", "B"], {"A": True, "B": True})
        self.assertEqual(plan, [(None, []), (0, ["A"]), (1, ["A", "B"])])

    def test_a_layer_that_cannot_be_kept_folds_into_the_one_above(self):
        plan = swaplayers.cut_plan(["A", "B"], {"A": False, "B": True})
        self.assertEqual(plan, [(None, []), (1, ["A", "B"])])
        self.assertEqual(swaplayers.folds(["A", "B"], {"A": False, "B": True}), [("A", "B")])

    def test_the_top_cut_always_holds_every_layer(self):
        plan = swaplayers.cut_plan(["A", "B"], {"A": True, "B": False})
        self.assertEqual(plan, [(None, []), (0, ["A", "B"])])
        self.assertEqual(swaplayers.folds(["A", "B"], {"A": True, "B": False}), [("B", "A")])

    def test_no_layer_can_be_kept_means_no_cut(self):
        self.assertEqual(swaplayers.cut_plan(["A"], {"A": False}), [])
        self.assertEqual(swaplayers.folds(["A"], {"A": False}), [])


class Times(unittest.TestCase):

    def test_the_layers_own_times_inside_the_range(self):
        self.assertEqual(swaplayers.times_of([0.0, 12.0, 24.0, 99.0], 0.0, 30.0),
                         [0.0, 12.0, 24.0])

    def test_the_same_time_twice_is_one_key(self):
        self.assertEqual(swaplayers.times_of([5.0, 5.00001, 7.0], 0.0, 10.0), [5.0, 7.0])

    def test_a_layer_with_no_key_of_its_own_takes_the_ranges_start(self):
        self.assertEqual(swaplayers.times_of([], 3.0, 10.0), [3.0])


class Tangents(unittest.TestCase):

    def test_a_step_in_tangent_is_left_to_maya(self):
        self.assertEqual(swaplayers.tangent_flags("step", "step"),
                         {"outTangentType": "step"})

    def test_both_types_travel_when_maya_takes_them(self):
        self.assertEqual(swaplayers.tangent_flags("auto", "linear"),
                         {"inTangentType": "auto", "outTangentType": "linear"})

    def test_no_type_is_no_flag(self):
        self.assertEqual(swaplayers.tangent_flags(None, None), {})

    def test_a_stored_key_carries_its_time_value_and_types(self):
        stored = swaplayers.stored_keys({0.0: 1.0, 12.0: 2.0}, [0.0, 12.0, 24.0],
                                        {0.0: ("step", "step")})
        self.assertEqual(stored, [[0.0, 1.0, "step", "step"], [12.0, 2.0, "auto", "auto"]])


class Readings(unittest.TestCase):
    """The rules the first live run taught (2026-10-29): a cut keys only what moves, so one cut
    can key `rotateZ` where another keys `rotateX`, and each retarget lands on its own turn."""

    def _reading(self, index, values, times):
        return swaplayers.Reading(index, values, times, {})

    def test_a_transform_channel_brings_its_whole_family(self):
        self.assertEqual(swaplayers.triples(["|c.rotateZ"]),
                         ["|c.rotateX", "|c.rotateY", "|c.rotateZ"])
        self.assertEqual(swaplayers.triples(["|c.translateY", "|c.visibility"]),
                         ["|c.translateX", "|c.translateY", "|c.translateZ", "|c.visibility"])

    def test_a_family_is_listed_once_however_often_it_is_asked(self):
        self.assertEqual(swaplayers.triples(["|c.rotateX", "|c.rotateZ"]),
                         ["|c.rotateX", "|c.rotateY", "|c.rotateZ"])

    def test_a_plug_missing_from_a_cut_takes_the_first_readings_value(self):
        readings = swaplayers.fill_gaps([
            self._reading(None, {"a": {0.0: 1.0}}, [0.0]),
            self._reading(0, {"a": {0.0: 2.0}, "b": {0.0: 5.0}}, [0.0])])
        self.assertEqual(readings[0].values["b"], {0.0: 5.0})

    def test_filling_covers_every_time_of_the_reading(self):
        readings = swaplayers.fill_gaps([
            self._reading(None, {"a": {0.0: 1.0, 9.0: 1.0}}, [0.0, 9.0]),
            self._reading(0, {"a": {0.0: 2.0}, "b": {0.0: 5.0}}, [0.0])])
        self.assertEqual(readings[0].values["b"], {0.0: 5.0, 9.0: 5.0})

    def test_a_later_cuts_rotation_is_snapped_onto_the_first_cuts_turn(self):
        readings = swaplayers.align_turns([
            self._reading(None, {"|c.rotateX": {0.0: 1.4, 9.0: 2.0}}, [0.0, 9.0]),
            self._reading(0, {"|c.rotateX": {0.0: 721.4, 9.0: 722.0}}, [0.0, 9.0])])
        snapped = readings[1].values["|c.rotateX"]
        self.assertAlmostEqual(snapped[0.0], 1.4, places=9)
        self.assertAlmostEqual(snapped[9.0], 2.0, places=9)

    def test_only_rotations_are_snapped(self):
        readings = swaplayers.align_turns([
            self._reading(None, {"|c.translateX": {0.0: 1.0}}, [0.0]),
            self._reading(0, {"|c.translateX": {0.0: 361.0}}, [0.0])])
        self.assertEqual(readings[1].values["|c.translateX"], {0.0: 361.0})

    def test_a_layer_keeps_only_the_channels_it_changes(self):
        readings = swaplayers.trim_layers([
            self._reading(None, {"a": {0.0: 1.0}, "b": {0.0: 1.0}}, [0.0]),
            self._reading(0, {"a": {0.0: 9.0}, "b": {0.0: 1.0}}, [0.0])])
        self.assertEqual(sorted(readings[1].values), ["a"])

    def test_the_retargets_own_noise_is_no_offset(self):
        readings = swaplayers.trim_layers([
            self._reading(None, {"a": {0.0: 1.0}}, [0.0]),
            self._reading(0, {"a": {0.0: 1.0 + 1e-5}}, [0.0])])
        self.assertEqual(sorted(readings[1].values), [])

    def test_the_base_is_never_trimmed(self):
        readings = swaplayers.trim_layers([self._reading(None, {"a": {0.0: 1.0}}, [0.0])])
        self.assertEqual(sorted(readings[0].values), ["a"])

    def test_a_stack_nothing_can_be_kept_from_says_why(self):
        notes = swaplayers.nothing_kept([_record("Spin", rotation="quaternion")])
        self.assertEqual(len(notes), 1)
        self.assertIn("Spin", notes[0])
        self.assertIn("quaternions", notes[0])

    def test_a_stack_with_a_keepable_layer_says_nothing(self):
        self.assertEqual(swaplayers.nothing_kept([_record("Fix"),
                                                  _record("Spin", rotation="quaternion")]), [])
        self.assertEqual(swaplayers.nothing_kept([]), [])

    def test_the_1p_road_names_a_layer_of_the_animators_own(self):
        records = [_record("_3P_Lower_Body"), _record("_3P_Upper_Body"), _record("Fix")]
        self.assertEqual(swaplayers.extra_1p(records), ["Fix"])


class Question(unittest.TestCase):

    def test_it_names_the_layers_and_both_buttons(self):
        text = swaplayers.question("Manny_Rig", "Creep [rig]", [_record("Fix")], False,
                                   [(None, []), (0, ["Fix"])], [])
        self.assertIn("Manny_Rig", text)
        self.assertIn("Creep [rig]", text)
        self.assertIn("Fix", text)
        self.assertIn("runs 2 times", text)
        self.assertIn(swaplayers.KEEP, text)
        self.assertIn(swaplayers.BAKE, text)

    def test_a_rig_in_1p_says_1p_setup_runs_again(self):
        text = swaplayers.question("Manny_Rig", "Creep [rig]",
                                   [_record("_3P_Lower_Body"), _record("_3P_Upper_Body")],
                                   True, [], [])
        self.assertIn("1P Setup is run again", text)
        self.assertIn("no 1P setup", text)
        self.assertNotIn("runs", text.split("1P Setup is run again")[0])

    def test_a_folded_layer_is_named(self):
        text = swaplayers.question("A", "B", [_record("Spin", rotation="quaternion")], False,
                                   [], [("Spin", "Fix")])
        self.assertIn("Spin cannot be kept on its own", text)
        self.assertIn("Fix", text)


class Plans(unittest.TestCase):

    def test_a_rig_in_1p_onto_a_rig_is_the_1p_plan(self):
        plan = swaplayers.plan_of([_record("_3P_Lower_Body")], True, True)
        self.assertTrue(plan.first_person)
        self.assertEqual(plan.cuts, [])

    def test_a_rig_in_1p_onto_a_skeleton_is_cut_layer_by_layer(self):
        plan = swaplayers.plan_of([_record("_3P_Lower_Body")], True, False)
        self.assertFalse(plan.first_person)
        self.assertEqual(plan.cuts, [(None, []), (0, ["_3P_Lower_Body"])])

    def test_no_layer_at_all_is_no_plan(self):
        plan = swaplayers.plan_of([], False, True)
        self.assertFalse(plan.cuts)
        self.assertFalse(plan.first_person)

    def test_the_line_names_the_layers_it_made(self):
        self.assertIn("A, B", swaplayers.line_of(["A", "B"], []))
        self.assertIn("note", swaplayers.line_of(["A"], ["note"]))
        self.assertEqual(swaplayers.line_of([], []), "")


class Choosing(unittest.TestCase):

    def tearDown(self):
        swaplayers.set_asker(None)

    def test_the_asker_is_what_the_press_asks(self):
        asked = []

        def answer(text):
            asked.append(text)
            return swaplayers.KEEP

        swaplayers.set_asker(answer)
        plan = swaplayers.plan_of([_record("Fix")], False, True)
        self.assertEqual(swaplayers.choose(plan, "A", "B"), "keep")
        self.assertEqual(len(asked), 1)

    def test_bake_is_the_answer_with_nobody_to_ask(self):
        swaplayers.set_asker(None)
        plan = swaplayers.plan_of([_record("Fix")], False, True)
        saved = swaplayers.can_ask
        swaplayers.can_ask = lambda: False
        try:
            self.assertEqual(swaplayers.choose(plan, "A", "B"), "bake")
        finally:
            swaplayers.can_ask = saved

    def test_cancel_raises(self):
        swaplayers.set_asker(lambda text: swaplayers.CANCEL)
        plan = swaplayers.plan_of([_record("Fix")], False, True)
        self.assertRaises(swaplayers.Cancelled, swaplayers.choose, plan, "A", "B")

    def test_a_character_with_no_layer_is_never_asked(self):
        swaplayers.set_asker(lambda text: self.fail("asked with no layer"))
        self.assertEqual(swaplayers.choose(swaplayers.plan_of([], False, True), "A", "B"),
                         "bake")

    def test_a_stack_with_no_road_to_keep_it_is_never_asked(self):
        swaplayers.set_asker(lambda text: self.fail("asked with nothing keepable"))
        plan = swaplayers.plan_of([_record("Spin", rotation="quaternion")], False, True)
        self.assertEqual(swaplayers.choose(plan, "A", "B"), "bake")


class FakeScene(object):
    """The `cmds` calls the scene half makes, answered from a tiny model."""

    def __init__(self, stack=(), plugs=None, keyed=None, muted=None):
        self.stack = list(stack)
        self.plugs = dict(plugs or {})
        self.keyed = dict(keyed or {})       # {plug or curve: [(time, in, out)]}
        self.muted = dict(muted or {})
        self.mutes_set = []
        self.tangents = []

    def animLayer(self, *args, **kwargs):
        if kwargs.get("query"):
            if kwargs.get("root"):
                return self.stack[0] if self.stack else None
            name = args[0]
            if kwargs.get("children"):
                return list(self.stack[1:]) if self.stack and name == self.stack[0] else []
            if kwargs.get("attribute"):
                return list(self.plugs.get(name, ()))
            if kwargs.get("mute"):
                return bool(self.muted.get(name))
            if kwargs.get("override") or kwargs.get("weight"):
                return False
            return None
        if kwargs.get("edit") and "mute" in kwargs:
            self.mutes_set.append((args[0], bool(kwargs["mute"])))
            self.muted[args[0]] = bool(kwargs["mute"])
            return args[0]
        return args[0] if args else None

    def ls(self, *args, **kwargs):
        if not args:
            return []
        name = args[0]
        return [name if name.startswith("|") else "|" + name]

    def attributeQuery(self, attr, **kwargs):
        return attr

    def listAnimatable(self, node):
        return [plug for plug in sorted(self.keyed) if plug.startswith(node + ".")]

    def keyframe(self, *args, **kwargs):
        rows = self.keyed.get(args[0], [])
        if kwargs.get("keyframeCount"):
            return len(rows)
        if kwargs.get("timeChange"):
            return [t for t, _i, _o in rows]
        return []

    def keyTangent(self, *args, **kwargs):
        if kwargs.get("inTangentType") is True:
            return [i for _t, i, _o in self.keyed.get(args[0], [])]
        if kwargs.get("outTangentType") is True:
            return [o for _t, _i, o in self.keyed.get(args[0], [])]
        self.tangents.append((list(args[0]), kwargs.get("inTangentType"),
                              kwargs.get("outTangentType")))
        return None

    def getAttr(self, plug, **kwargs):
        return 7.0


class FakeKeys(object):
    """`maya_poselib.keys` as the writing half uses it."""

    def __init__(self):
        from maya_poselib import keys
        self.Layer = keys.Layer
        self._written = keys.Written
        self.written = []
        self.raw = []
        self.made = []

    def write(self, values, frame, layer):
        name = None if layer is None else layer.name
        self.written.append((dict(values), frame, name))
        return self._written(len(values), [], sorted(values))

    def write_raw(self, plug, layer, stored, weighted=False, pre=None, post=None):
        self.raw.append((plug, layer, [list(key) for key in stored]))
        return self._written(len(stored), [], [plug])

    def make_layer(self, record):
        self.made.append(dict(record))
        return record["name"]

    @staticmethod
    def curve_for(plug, layer):
        return plug + "@" + str(layer)

    @staticmethod
    def layer_stack():
        return []

    @staticmethod
    def layer_plugs(name):
        return set()


class Reading(unittest.TestCase):

    def setUp(self):
        from maya_poselib import keys
        self.keys_module = keys
        self.saved = swaplayers.cmds
        self.saved_keys = keys.cmds

    def tearDown(self):
        swaplayers.cmds = self.saved
        self.keys_module.cmds = self.saved_keys

    def _scene(self, fake):
        """A fake `cmds` for the module AND for `maya_poselib.keys`, which reads the stack."""
        swaplayers.cmds = fake
        self.keys_module.cmds = fake
        return fake

    def test_only_the_layers_holding_the_characters_channels(self):
        self._scene(FakeScene(
            stack=["BaseAnimation", "Fix", "Other"],
            plugs={"Fix": ["|rig:ctrl.rotateX"], "Other": ["|prop.translateX"]}))
        self.assertEqual(swaplayers.layers_of(["|rig:ctrl"]), ["Fix"])

    def test_the_base_is_mayas_root(self):
        self._scene(FakeScene(stack=["BaseAnimation", "Fix"]))
        layer = swaplayers.base_layer()
        self.assertEqual(layer.name, "BaseAnimation")
        self.assertTrue(layer.base)
        self.assertEqual(swaplayers.base_name(), "BaseAnimation")

    def test_no_layers_means_no_base_layer(self):
        self._scene(FakeScene())
        self.assertIsNone(swaplayers.base_layer())
        self.assertIsNone(swaplayers.base_name())

    def test_a_cut_mutes_every_layer_it_leaves_out_and_restores(self):
        fake = FakeScene(stack=["BaseAnimation", "A", "B"], muted={"A": False, "B": True})
        self._scene(fake)
        saved = swaplayers.mutes_of(["A", "B"])
        self.assertEqual(saved, {"A": False, "B": True})
        swaplayers.set_mutes(["A", "B"], ["A"])
        self.assertEqual(fake.muted, {"A": False, "B": True})
        swaplayers.set_mutes(["A", "B"], [])
        self.assertTrue(fake.muted["A"])
        swaplayers.restore_mutes(saved)
        self.assertEqual(fake.muted, {"A": False, "B": True})

    def test_the_times_and_tangents_of_a_layers_own_curves(self):
        self._scene(FakeScene(
            keyed={"c1": [(0.0, "step", "step"), (12.0, "step", "step")]}))
        times, tangents = swaplayers.times_and_tangents(["c1"], 0.0, 24.0)
        self.assertEqual(times, [0.0, 12.0])
        self.assertEqual(tangents[12.0], ("step", "step"))

    def test_only_the_channels_that_carry_keys_are_captured(self):
        self._scene(FakeScene(keyed={"|c.rotateX": [(0.0, "auto", "auto")]}))
        plugs = swaplayers.animated_plugs(["|c"])
        self.assertEqual(plugs, ["|c.rotateX"])
        self.assertEqual(swaplayers.capture(plugs, [0.0]), {"|c.rotateX": {0.0: 7.0}})


class Writing(unittest.TestCase):

    def setUp(self):
        self.saved = swaplayers.cmds
        self.fake = FakeScene(stack=["BaseAnimation"])
        swaplayers.cmds = self.fake
        self.keys = FakeKeys()

    def tearDown(self):
        swaplayers.cmds = self.saved

    def _readings(self, *rows):
        return [swaplayers.Reading(index, values, times, tangents)
                for index, values, times, tangents in rows]

    def test_the_base_is_written_as_raw_curves_one_call_a_channel(self):
        readings = self._readings((None, {"p": {0.0: 1.0, 12.0: 2.0}}, [0.0, 12.0],
                                   {0.0: ("step", "step")}))
        made, _notes = swaplayers.write_stack(readings, [], keys_module=self.keys)
        self.assertEqual(made, [])
        self.assertEqual(len(self.keys.raw), 1)
        plug, layer, stored = self.keys.raw[0]
        self.assertEqual((plug, layer), ("p", "BaseAnimation"))
        self.assertEqual(stored, [[0.0, 1.0, "step", "step"], [12.0, 2.0, "auto", "auto"]])

    def test_each_layer_is_made_and_keyed_bottom_to_top_after_the_base(self):
        records = [_record("A"), _record("B")]
        readings = self._readings(
            (None, {"p": {0.0: 1.0}}, [0.0], {}),
            (0, {"p": {0.0: 2.0}}, [0.0], {}),
            (1, {"p": {0.0: 3.0}}, [0.0], {}))
        made, _notes = swaplayers.write_stack(readings, records, keys_module=self.keys)
        self.assertEqual(made, ["A", "B"])
        self.assertEqual([name for _v, _f, name in self.keys.written], ["A", "B"])
        self.assertEqual([values["p"] for values, _f, _n in self.keys.written], [2.0, 3.0])

    def test_a_layer_is_made_unmuted_and_muted_after_its_keys(self):
        records = [_record("A", mute=True)]
        readings = self._readings((0, {"p": {0.0: 2.0}}, [0.0], {}))
        swaplayers.write_stack(readings, records, keys_module=self.keys)
        self.assertFalse(self.keys.made[0]["mute"])
        self.assertIn(("A", True), self.fake.mutes_set)

    def test_the_source_tangent_types_are_set_on_a_layers_keys(self):
        records = [_record("A")]
        readings = self._readings((0, {"p": {0.0: 2.0}}, [0.0], {0.0: ("flat", "flat")}))
        swaplayers.write_stack(readings, records, keys_module=self.keys)
        self.assertIn((["p@A"], "flat", "flat"), self.fake.tangents)

    def test_a_layer_at_weight_zero_is_made_and_left_empty(self):
        records = [_record("A", weight=0.0)]
        readings = self._readings((0, {"p": {0.0: 2.0}}, [0.0], {}))
        made, notes = swaplayers.write_stack(readings, records, keys_module=self.keys)
        self.assertEqual(made, ["A"])
        self.assertEqual(self.keys.written, [])
        self.assertTrue(any("weight 0" in note for note in notes))

    def test_a_record_with_no_reading_makes_no_layer(self):
        records = [_record("A"), _record("B")]
        readings = self._readings((1, {"p": {0.0: 3.0}}, [0.0], {}))
        made, _notes = swaplayers.write_stack(readings, records, keys_module=self.keys)
        self.assertEqual(made, ["B"])


class FirstPerson(unittest.TestCase):

    class Rig(object):
        namespace = "Manny_Rig"
        main = "|Manny_Rig:Main"

    def test_a_rig_with_a_chest_knot_of_its_own_is_in_1p(self):
        class Found(object):
            @staticmethod
            def chest_of(rig):
                return "|Manny_Rig:Chest_1P_ctrl"

        class Missing(object):
            @staticmethod
            def chest_of(rig):
                return None

        self.assertTrue(swaplayers.in_1p(self.Rig(), module=Found))
        self.assertFalse(swaplayers.in_1p(self.Rig(), module=Missing))

    def test_none_is_never_in_1p(self):
        self.assertFalse(swaplayers.in_1p(None))

    def test_a_raising_module_is_no_1p(self):
        class Raises(object):
            @staticmethod
            def chest_of(rig):
                raise RuntimeError("no scene")

        self.assertFalse(swaplayers.in_1p(self.Rig(), module=Raises))

    def test_the_split_names_the_rig_it_ran_on(self):
        class Ok(object):
            @staticmethod
            def setup(selection=None):
                return "1P: Manny_Rig split over 2 layers"

        line, failure = swaplayers.split_again(self.Rig(), module=Ok)
        self.assertEqual(line, swaplayers.SPLIT_AGAIN % "Manny_Rig")
        self.assertEqual(failure, "")

    def test_a_refused_split_is_the_failure(self):
        class Refused(object):
            @staticmethod
            def setup(selection=None):
                return "1P Setup: no rig in the selection"

        line, failure = swaplayers.split_again(self.Rig(), module=Refused)
        self.assertEqual(line, "")
        self.assertIn("no rig", failure)

    def test_a_raising_split_is_the_failure(self):
        class Raises(object):
            @staticmethod
            def setup(selection=None):
                raise RuntimeError("the chest control is gone")

        line, failure = swaplayers.split_again(self.Rig(), module=Raises)
        self.assertEqual(line, "")
        self.assertIn("chest control", failure)


if __name__ == "__main__":
    unittest.main()
