"""Connections: IK into a world control (2026-10-28).

The press's order of things on stubs (`switch_limb` with the World box), the card's World chip,
the messages, and the knot keyed on frames only (`knots._key_samples`).

Spec: docs/superpowers/specs/2026-10-28-connections-ik-world-design.md
"""

import unittest

import maya_rigs
from maya_scenesetup import connections as cx
from maya_scenesetup import ikworld
from maya_tools import knots

from tests.test_scenesetup_connections import FakeMenuCmds


class Messages(unittest.TestCase):

    def test_world_text_names_the_limbs(self):
        self.assertEqual(ikworld.world_text(["Arm_R", "Leg_L"]), "Arm_R, Leg_L IK in world")
        self.assertEqual(ikworld.world_text([]), "")

    def test_entered_names_the_control_and_its_keys(self):
        self.assertEqual(ikworld.entered_message("|g|IKArm_R", "|K|IKArm_R_dknotMove", [0, 12, 24]),
                         "IKArm_R in world on IKArm_R_dknotMove, 3 keys (0..24)")
        self.assertEqual(ikworld.entered_message("|g|IKArm_R", "|K|IKArm_R_dknotMove", [12]),
                         "IKArm_R in world on IKArm_R_dknotMove, 1 key (12)")
        self.assertEqual(ikworld.entered_message("|g|IKArm_R", "|K|IKArm_R_dknotMove", []),
                         "IKArm_R in world on IKArm_R_dknotMove, no keys - set at the "
                         "current frame")

    def test_left_says_where_the_control_is_and_how_well_the_limb_held(self):
        m = ikworld.fkik.Measure(0.00012, 12, 0.0004, 0.0003, 12)
        self.assertEqual(ikworld.left_message("Arm_R", "|g|IKArm_R", [0, 24], m),
                         "Arm_R back from world on 2 keys (0..24) - IKArm_R in Main's space "
                         "again, the arm kept to 0.0001 cm, 0.000 deg")
        moved = ikworld.fkik.Measure(1.5, 12, 3.0, 0.0, 12)
        self.assertIn("moved up to 1.50 cm (frame 12)",
                      ikworld.left_message("Leg_L", "|g|IKLeg_L", [12], moved, kind="Leg"))


class SwitchWorld(unittest.TestCase):
    """`switch_limb`'s order with the World box, on stubs."""

    def setUp(self):
        self.rig = maya_rigs.Rig("Manny_Rig", "cs", "|G|Main", "|G", "|root")
        self.done = []
        self.saved = dict((name, getattr(cx, name)) for name in
                          ("cmds", "_rig", "following", "_release", "_span",
                           "sweep_orphans", "_control", "weapon_label",
                           "release_refusal"))
        self.saved_fkik = dict((name, getattr(cx.fkik, name)) for name in
                               ("limb", "whole_take", "refusal", "switch",
                                "blend_values", "key_plan"))
        self.saved_world = dict((name, getattr(cx.ikworld, name)) for name in
                                ("is_on", "knot_of", "limb_knot", "enter", "leave", "drop", "refusal",
                                 "nodes_of", "key_times"))
        done = self.done

        class Cmds(object):
            existing = set()

            def objExists(self, name):
                return name in self.existing

            def undoInfo(inner, **kwargs):
                done.append(("undo", "open" if kwargs.get("openChunk") else "close"))

            def currentTime(inner, **kwargs):
                return 7.0

        self.cmds = Cmds()
        cx.cmds = self.cmds
        cx._rig = lambda rig: (self.rig, "")
        cx.following = lambda rig, side: None
        cx._release = lambda rig, side, span: done.append(("release", side))
        cx._span = lambda weapon, controls: (0.0, 24.0)
        cx.sweep_orphans = lambda: 0
        cx._control = lambda rig, side: "|IKArm_" + side

        class Arm(object):
            def __init__(self, side):
                self.side, self.ik, self.kind = side, "|G|IKArm_" + side, "Arm"

        self.arms = {"R": Arm("R"), "L": Arm("L")}
        cx.fkik.limb = lambda rig, side, kind="Arm": (self.arms[side], "")
        cx.fkik.whole_take = lambda arm, extra=(): (0.0, 24.0)
        cx.fkik.refusal = lambda arm, mode, span, ignore=(): ""
        cx.fkik.key_plan = lambda arm, span, extra=(): (
            [0.0, 12.0, 24.0], [0.0, 12.0, 24.0], {12.0: ("step", "step")})

        def switch(arm, mode, span, every_frame=False, extra=()):
            done.append(("switch", arm.side, mode, span, tuple(extra)))
            return "%s to %s" % ("Arm_" + arm.side, mode)
        cx.fkik.switch = switch
        self.blend = [0.0]
        cx.fkik.blend_values = lambda arm: list(self.blend)
        self.top = None
        self.on = False
        cx.ikworld.is_on = lambda: self.on
        cx.ikworld.knot_of = lambda control: self.top
        cx.ikworld.limb_knot = lambda limb: self.top
        cx.ikworld.nodes_of = lambda top: [top, top + "|inner"]
        cx.ikworld.key_times = lambda top: [3.0, 30.0]
        cx.ikworld.refusal = lambda limb: ""
        cx.ikworld.enter = lambda limb, frames, tangents, highlight: done.append(
            ("enter", limb.side, list(frames), dict(tangents), highlight)) or "in world"
        cx.ikworld.leave = lambda limb, top: done.append(("leave", limb.side, top)) or "back"
        cx.ikworld.drop = lambda top: done.append(("drop", top)) or "dropped"

    def tearDown(self):
        for name, value in self.saved.items():
            setattr(cx, name, value)
        for name, value in self.saved_fkik.items():
            setattr(cx.fkik, name, value)
        for name, value in self.saved_world.items():
            setattr(cx.ikworld, name, value)

    def kinds(self):
        return [d[0] for d in self.done]

    def test_world_off_switches_as_it_always_did(self):
        cx.switch_arm("R", "IK", highlight=False)
        self.assertEqual(self.kinds(), ["undo", "switch", "undo"])

    def test_world_on_switches_then_puts_the_ik_on_a_world_control_on_the_same_keys(self):
        self.on = True
        text = cx.switch_arm("R", "IK", highlight=False)
        self.assertEqual(self.kinds(), ["undo", "switch", "enter", "undo"])
        self.assertEqual(self.done[2], ("enter", "R", [0.0, 12.0, 24.0],
                                        {12.0: ("step", "step")}, None))
        self.assertEqual(text, "Arm_R to IK; in world")

    def test_the_box_is_read_only_when_the_press_says_nothing(self):
        cx.switch_limb("R", "IK", highlight=False, world=True)
        self.assertIn("enter", self.kinds())

    def test_a_highlight_reaches_the_world_control_as_the_slider_answers_it(self):
        self.on = True
        cx.switch_arm("L", "IK", highlight=(10.0, 16.0))
        self.assertEqual(self.done[1][3], (10, 15, True))
        self.assertEqual(self.done[2][4], (10.0, 16.0))

    def test_an_unkeyed_limb_takes_its_world_control_at_the_current_frame(self):
        self.on = True
        cx.fkik.key_plan = lambda arm, span, extra=(): ([7.0], [], {})
        cx.switch_arm("R", "IK", highlight=False)
        self.assertEqual(self.done[2][2], [7.0])

    def test_world_on_an_ik_limb_makes_the_world_control_only(self):
        self.on, self.blend = True, [10.0]
        cx.switch_arm("R", "IK", highlight=False)
        self.assertEqual(self.kinds(), ["undo", "enter", "undo"])

    def test_world_on_an_ik_limb_in_world_is_refused(self):
        self.on, self.blend, self.top = True, [10.0], "|K|IKArm_R_dknotMove"
        text = cx.switch_arm("R", "IK", highlight=False)
        self.assertEqual(text, "Arm_R is already IK in world (IKArm_R_dknotMove)")
        self.assertEqual(self.done, [])

    def test_ik_without_world_on_a_limb_in_world_brings_it_back(self):
        self.blend, self.top = [10.0], "|K|IKArm_R_dknotMove"
        text = cx.switch_arm("R", "IK", highlight=False)
        self.assertEqual(self.kinds(), ["undo", "leave", "undo"])
        self.assertEqual(text, "back")

    def test_fk_on_a_limb_in_world_switches_on_its_keys_then_takes_the_control_off(self):
        self.blend, self.top = [10.0], "|K|IKArm_R_dknotMove"
        text = cx.switch_arm("R", "FK", highlight=False)
        self.assertEqual(self.kinds(), ["undo", "switch", "drop", "undo"])
        self.assertEqual(self.done[1][4], ("|K|IKArm_R_dknotMove", "|K|IKArm_R_dknotMove|inner"))
        self.assertEqual(text, "Arm_R to FK; dropped")

    def test_the_world_controls_keys_widen_the_whole_take(self):
        self.blend, self.top = [10.0], "|K|IKArm_R_dknotMove"
        cx.switch_arm("R", "FK", highlight=False)
        self.assertEqual(self.done[1][3], (0, 30, False))

    def test_fk_on_an_fk_limb_with_a_world_control_left_takes_it_off(self):
        self.blend, self.top = [0.0], "|K|IKArm_R_dknotMove"
        text = cx.switch_arm("R", "FK", highlight=False)
        self.assertEqual(self.kinds(), ["undo", "drop", "undo"])
        self.assertIn("Arm_R is already FK", text)

    def test_ik_on_a_limb_that_shows_fk_with_a_world_control_left_asks_for_fk(self):
        self.blend, self.top = [0.0], "|K|IKArm_R_dknotMove"
        text = cx.switch_arm("R", "IK", highlight=False)
        self.assertEqual(text, "Arm_R shows FK with a world control left on IKArm_R - "
                               "press FK to take it off first")
        self.assertEqual(self.done, [])

    def test_the_world_controls_refusal_moves_nothing(self):
        self.on = True
        cx.ikworld.refusal = lambda limb: "IKArm_R.rotateX is locked"
        self.assertEqual(cx.switch_arm("R", "IK", highlight=False), "IKArm_R.rotateX is locked")
        self.assertEqual(self.done, [])

    def test_the_switchs_refusal_comes_first(self):
        self.on = True
        cx.fkik.refusal = lambda arm, mode, span, ignore=(): "Arm_R: layer locked"
        self.assertEqual(cx.switch_arm("R", "IK", highlight=False), "Arm_R: layer locked")
        self.assertEqual(self.done, [])

    def test_a_leg_takes_the_world_control_too(self):
        self.on = True
        cx.switch_limb("L", "IK", highlight=False, kind=cx.fkik.LEG)
        self.assertEqual(self.kinds(), ["undo", "switch", "enter", "undo"])

    def test_a_hand_in_world_cannot_follow_a_weapon(self):
        self.top = "|K|IKArm_R_dknotMove"
        self.assertEqual(cx.world_refusal(self.rig, "R"),
                         "Arm_R is IK in world - press IK without World first")
        self.top = None
        self.assertEqual(cx.world_refusal(self.rig, "R"), "")


class PanelWorld(unittest.TestCase):

    def setUp(self):
        self.real = (cx.cmds, cx.refresh, cx.ikworld.cmds)
        self.fake = FakeMenuCmds()
        cx.cmds = self.fake
        cx.ikworld.cmds = self.fake
        cx.refresh = lambda *a: ""
        cx.hubstyle.take_marks()

    def tearDown(self):
        cx.cmds, cx.refresh, cx.ikworld.cmds = self.real

    def build(self):
        cx.build_panel()
        return dict((m.name, m) for m in cx.hubstyle.take_marks())

    def box(self):
        return [c for c in self.fake.calls if c[0] == "checkBox" and c[1]
                and c[1][0] == cx.WORLD_BOX and not c[2].get("edit")
                and not c[2].get("query")][0]

    def test_a_world_chip_stands_under_the_fkik_rows(self):
        marks = self.build()
        self.assertEqual(marks[cx.WORLD_BOX].role, "chip")
        call = self.box()
        self.assertEqual(call[2]["label"], "World")
        self.assertFalse(call[2]["value"])
        names = [c[1][0] for c in self.fake.calls if c[1] and c[0] in ("checkBox",
                                                                          "iconTextCheckBox")]
        self.assertGreater(names.index(cx.WORLD_BOX),
                           names.index(cx.fkik_box("L", "IK", cx.fkik.LEG)))

    def test_the_chip_shows_what_was_remembered_and_remembers_a_change(self):
        self.fake.optionvars[ikworld.OPTIONVAR] = 1
        self.build()
        call = self.box()
        self.assertTrue(call[2]["value"])
        self.fake.optionvars.clear()
        original = self.fake.checkBox
        self.fake.checkBox = lambda *a, **k: True if k.get("query") else original(*a, **k)
        call[2]["changeCommand"](True)
        self.assertEqual(self.fake.optionvars[ikworld.OPTIONVAR], 1)
        self.assertTrue(ikworld.is_on())


class KeyedOnFrames(unittest.TestCase):
    """`knots._key_samples`: a knot keyed on the switch's frames, not baked."""

    def setUp(self):
        self.real = knots.cmds
        self.calls = []
        calls = self.calls

        class Cmds(object):
            def setKeyframe(self, node, **kwargs):
                calls.append(("key", node, kwargs["attribute"], kwargs["time"], kwargs["value"],
                              kwargs.get("inTangentType"), kwargs.get("outTangentType")))

            def setAttr(self, plug, value):
                calls.append(("set", plug, value))

            def listConnections(self, *a, **k):
                return []

            def filterCurve(self, *a, **k):
                calls.append(("filter",))

        knots.cmds = Cmds()

    def tearDown(self):
        knots.cmds = self.real

    def test_each_channel_is_keyed_on_the_frames_with_the_switchs_tangents(self):
        samples = {("|k", "translateX"): [1.0, 2.0, 3.0]}
        knots._key_samples(samples, [0.0, 12.0, 24.0], (0.0, 24.0, False),
                           {12.0: ("linear", "step")})
        self.assertEqual(self.calls, [("key", "|k", "translateX", 0.0, 1.0, None, None),
                                      ("key", "|k", "translateX", 12.0, 2.0, "linear", "step"),
                                      ("key", "|k", "translateX", 24.0, 3.0, None, None)])

    def test_a_still_channel_over_the_whole_take_is_a_plain_value(self):
        knots._key_samples({("|k", "translateY"): [4.0, 4.0]}, [0.0, 24.0],
                           (0.0, 24.0, False), {})
        self.assertEqual(self.calls, [("set", "|k.translateY", 4.0)])

    def test_a_ranged_still_channel_keeps_its_keys(self):
        knots._key_samples({("|k", "translateY"): [4.0, 4.0]}, [10.0, 15.0],
                           (9.0, 16.0, True), {})
        self.assertEqual([c[0] for c in self.calls], ["key", "key"])


if __name__ == "__main__":
    unittest.main()
