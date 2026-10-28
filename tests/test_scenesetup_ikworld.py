"""Connections: IK into a world control (2026-10-28).

The press's order of things on stubs (`switch_limb(world=True)`, the rows' W through
`toggle_world`), the W boxes in the limb rows, the controls' shapes, the messages, and the knot
keyed on frames only (`knots._key_samples`).

Spec: docs/superpowers/specs/2026-10-28-connections-ik-world-design.md
"""

import math
import unittest

import maya_rigs
from maya_scenesetup import connections as cx
from maya_scenesetup import ikworld
from maya_tools import knots

from tests.test_scenesetup_connections import FakeMenuCmds


class Messages(unittest.TestCase):

    def test_entered_names_the_control_and_its_keys(self):
        move = "|K|IKArm_R_worldMove_ctrl"
        self.assertEqual(ikworld.entered_message("|g|IKArm_R", move, [0, 12, 24]),
                         "IKArm_R in world on IKArm_R_worldMove_ctrl, 3 keys (0..24)")
        self.assertEqual(ikworld.entered_message("|g|IKArm_R", move, [12]),
                         "IKArm_R in world on IKArm_R_worldMove_ctrl, 1 key (12)")
        self.assertEqual(ikworld.entered_message("|g|IKArm_R", move, []),
                         "IKArm_R in world on IKArm_R_worldMove_ctrl, no keys - set at the "
                         "current frame")

    def test_left_says_where_the_control_is_and_how_well_the_limb_held(self):
        m = ikworld.fkik.Measure(0.00012, 12, 0.0004, 0.0003, 12)
        self.assertEqual(ikworld.left_message("Arm_R", "|g|IKArm_R", [0, 24], m),
                         "Arm_R back from world on 2 keys (0..24) - IKArm_R in Main's space "
                         "again, the arm kept to 0.0001 cm, 0.000 deg")
        moved = ikworld.fkik.Measure(1.5, 12, 3.0, 0.0, 12)
        self.assertIn("moved up to 1.50 cm (frame 12)",
                      ikworld.left_message("Leg_L", "|g|IKLeg_L", [12], moved, kind="Leg"))


class Shapes(unittest.TestCase):
    """The controls (2026-10-28, «вместо локатора мы будем создавать контроллер»)."""

    def test_the_move_is_a_cube_through_its_twelve_edges(self):
        points = ikworld.box(2.0)
        self.assertEqual(set(points), set((x, y, z) for x in (-2.0, 2.0) for y in (-2.0, 2.0)
                                          for z in (-2.0, 2.0)))
        edges = set()
        for a, b in zip(points, points[1:]):
            # every step runs along ONE axis: an edge, never a diagonal
            self.assertEqual(sum(1 for i in range(3) if a[i] != b[i]), 1)
            edges.add(frozenset((a, b)))
        self.assertEqual(len(edges), 12)

    def test_the_rotate_is_three_rings_in_one_line_with_no_chord(self):
        radius, sides = 3.0, 24
        points = ikworld.rings(radius, sides)
        step = 2.0 * radius * math.sin(math.pi / sides)
        for a, b in zip(points, points[1:]):
            self.assertLessEqual(math.dist(a, b), step + 1e-9)
        for p in points:
            self.assertAlmostEqual(math.sqrt(sum(c * c for c in p)), radius)
        for axis in range(3):
            # a ring in each plane: points with that axis at zero all round
            flat = [p for p in points if abs(p[axis]) < 1e-9]
            self.assertGreaterEqual(len(set(flat)), sides)

    def test_the_size_follows_the_ik_controls_drawing(self):
        self.assertEqual(ikworld.control_half(((-1.0, -4.0, -2.0), (1.0, 4.0, 2.0))), 4.0)
        self.assertEqual(ikworld.control_half(None), ikworld.LEAST)


class SwitchWorld(unittest.TestCase):
    """`switch_limb(world=True)` and `toggle_world`, on stubs."""

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
                                ("knot_of", "limb_knot", "enter", "leave", "drop", "refusal",
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
        cx.fkik.whole_take = lambda arm: (0.0, 24.0)
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

    def test_plain_ik_switches_as_it_always_did(self):
        cx.switch_arm("R", "IK", highlight=False)
        self.assertEqual(self.kinds(), ["undo", "switch", "undo"])

    def test_world_switches_then_puts_the_ik_on_a_world_control_on_the_same_keys(self):
        text = cx.switch_arm("R", "IK", highlight=False, world=True)
        self.assertEqual(self.kinds(), ["undo", "switch", "enter", "undo"])
        self.assertEqual(self.done[2], ("enter", "R", [0.0, 12.0, 24.0],
                                        {12.0: ("step", "step")}, None))
        self.assertEqual(text, "Arm_R to IK; in world")

    def test_a_highlight_reaches_the_world_control_as_the_slider_answers_it(self):
        cx.switch_arm("L", "IK", highlight=(10.0, 16.0), world=True)
        self.assertEqual(self.done[1][3], (10, 15, True))
        self.assertEqual(self.done[2][4], (10.0, 16.0))

    def test_an_unkeyed_limb_takes_its_world_control_at_the_current_frame(self):
        cx.fkik.key_plan = lambda arm, span, extra=(): ([7.0], [], {})
        cx.switch_arm("R", "IK", highlight=False, world=True)
        self.assertEqual(self.done[2][2], [7.0])

    def test_world_on_an_ik_limb_makes_the_world_control_only(self):
        self.blend = [10.0]
        cx.switch_arm("R", "IK", highlight=False, world=True)
        self.assertEqual(self.kinds(), ["undo", "enter", "undo"])

    def test_world_on_an_ik_limb_in_world_is_refused(self):
        self.blend, self.top = [10.0], "|K|IKArm_R_worldMove_ctrl"
        text = cx.switch_arm("R", "IK", highlight=False, world=True)
        self.assertEqual(text, "Arm_R is already IK in world (IKArm_R_worldMove_ctrl)")
        self.assertEqual(self.done, [])

    def test_plain_ik_on_a_limb_in_world_names_the_w(self):
        self.blend, self.top = [10.0], "|K|IKArm_R_worldMove_ctrl"
        text = cx.switch_arm("R", "IK", highlight=False)
        self.assertEqual(text, "Arm_R is already IK, in world - W takes it back into Main's "
                               "space")
        self.assertEqual(self.done, [])

    def test_fk_on_a_limb_in_world_switches_on_its_keys_then_takes_the_control_off(self):
        self.blend, self.top = [10.0], "|K|IKArm_R_worldMove_ctrl"
        text = cx.switch_arm("R", "FK", highlight=False)
        self.assertEqual(self.kinds(), ["undo", "switch", "drop", "undo"])
        self.assertEqual(self.done[1][4], ("|K|IKArm_R_worldMove_ctrl",
                                           "|K|IKArm_R_worldMove_ctrl|inner"))
        self.assertEqual(text, "Arm_R to FK; dropped")

    def test_the_world_controls_keys_widen_the_whole_take(self):
        self.blend, self.top = [10.0], "|K|IKArm_R_worldMove_ctrl"
        cx.switch_arm("R", "FK", highlight=False)
        self.assertEqual(self.done[1][3], (0, 30, False))

    def test_fk_on_an_fk_limb_with_a_world_control_left_takes_it_off(self):
        self.blend, self.top = [0.0], "|K|IKArm_R_worldMove_ctrl"
        text = cx.switch_arm("R", "FK", highlight=False)
        self.assertEqual(self.kinds(), ["undo", "drop", "undo"])
        self.assertIn("Arm_R is already FK", text)

    def test_ik_on_a_limb_that_shows_fk_with_a_world_control_left_asks_for_fk(self):
        self.blend, self.top = [0.0], "|K|IKArm_R_worldMove_ctrl"
        text = cx.switch_arm("R", "IK", highlight=False, world=True)
        self.assertEqual(text, "Arm_R shows FK with a world control left on IKArm_R - "
                               "press FK to take it off first")
        self.assertEqual(self.done, [])

    def test_the_world_controls_refusal_moves_nothing(self):
        cx.ikworld.refusal = lambda limb: "IKArm_R.rotateX is locked"
        self.assertEqual(cx.switch_arm("R", "IK", highlight=False, world=True),
                         "IKArm_R.rotateX is locked")
        self.assertEqual(self.done, [])

    def test_the_switchs_refusal_comes_first(self):
        cx.fkik.refusal = lambda arm, mode, span, ignore=(): "Arm_R: layer locked"
        self.assertEqual(cx.switch_arm("R", "IK", highlight=False, world=True),
                         "Arm_R: layer locked")
        self.assertEqual(self.done, [])

    #  --- the rows' W ---

    def test_w_on_a_limb_not_in_world_puts_it_in_world(self):
        cx.toggle_world("R", highlight=False)
        self.assertEqual(self.kinds(), ["undo", "switch", "enter", "undo"])

    def test_w_on_a_leg_too(self):
        cx.toggle_world("L", highlight=False, kind=cx.fkik.LEG)
        self.assertEqual(self.kinds(), ["undo", "switch", "enter", "undo"])

    def test_w_on_a_limb_in_world_brings_it_back(self):
        self.blend, self.top = [10.0], "|K|IKArm_R_worldMove_ctrl"
        self.assertEqual(cx.toggle_world("R", highlight=False), "back")
        self.assertEqual(self.kinds(), ["undo", "leave", "undo"])

    def test_w_on_a_world_control_left_on_an_unseen_ik_takes_it_off(self):
        self.blend, self.top = [0.0], "|K|IKArm_R_worldMove_ctrl"
        self.assertEqual(cx.toggle_world("R", highlight=False), "dropped")
        self.assertEqual(self.kinds(), ["undo", "drop", "undo"])

    def test_w_is_refused_while_a_retarget_stands(self):
        self.cmds.existing.add("Manny_Rig:MoCapConstraints")
        self.assertEqual(cx.toggle_world("R", highlight=False), cx.RETARGETING)
        self.assertEqual(self.done, [])

    def test_a_hand_in_world_cannot_follow_a_weapon(self):
        self.top = "|K|IKArm_R_worldMove_ctrl"
        self.assertEqual(cx.world_refusal(self.rig, "R"),
                         "Arm_R is IK in world - press its W first")
        self.top = None
        self.assertEqual(cx.world_refusal(self.rig, "R"), "")


class PanelW(unittest.TestCase):
    """The W box beside each limb's IK."""

    def setUp(self):
        self.real = (cx.cmds, cx.refresh, cx.toggle_world)
        self.fake = FakeMenuCmds()
        cx.cmds = self.fake
        cx.refresh = lambda *a: ""
        self.asked = []
        cx.toggle_world = lambda side, rig=None, highlight=None, kind=cx.fkik.ARM: \
            self.asked.append((side, kind)) or "toggled"
        cx.hubstyle.take_marks()
        cx.build_panel()
        self.marks = dict((m.name, m) for m in cx.hubstyle.take_marks())

    def tearDown(self):
        cx.cmds, cx.refresh, cx.toggle_world = self.real

    def test_every_limb_has_a_w_segment_after_its_ik(self):
        names = [c[1][0] for c in self.fake.calls if c[0] == "iconTextCheckBox" and c[1]
                 and not (c[2].get("edit") or c[2].get("exists") or c[2].get("query"))]
        for kind in (cx.fkik.ARM, cx.fkik.LEG):
            for side in ("R", "L"):
                ik, w = cx.fkik_box(side, "IK", kind), cx.fkik_box(side, cx.W_MODE, kind)
                self.assertEqual(names.index(w), names.index(ik) + 1)
                self.assertEqual(self.fake.boxes[w]["label"], "W")
                self.assertEqual(self.marks[w].role, "segment")

    def test_either_press_of_w_toggles_that_limb(self):
        self.fake.press_box(cx.fkik_box("R", cx.W_MODE))
        self.fake.press_box(cx.fkik_box("R", cx.W_MODE))
        self.fake.press_box(cx.fkik_box("L", cx.W_MODE, cx.fkik.LEG))
        self.assertEqual(self.asked, [("R", cx.fkik.ARM), ("R", cx.fkik.ARM),
                                      ("L", cx.fkik.LEG)])

    def test_the_refresh_lights_w_for_a_limb_in_world_only(self):
        cx._set_fkik({"R": "IK", "L": "IK"}, worlds=["R"])
        value = lambda side, mode: self.fake.boxes[cx.fkik_box(side, mode)]["value"]
        self.assertEqual((value("R", "IK"), value("R", "W")), (True, True))
        self.assertEqual((value("L", "IK"), value("L", "W")), (True, False))
        self.assertEqual(self.asked, [])

    def test_no_world_chip_any_more(self):
        self.assertFalse([c for c in self.fake.calls if c[0] == "checkBox"
                          and c[1] and "FKIKWorld" in str(c[1][0])])


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
