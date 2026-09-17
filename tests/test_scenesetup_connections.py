"""Connections: the hands on the weapon and off it (2026-09-18).

The pure halves, the panel on a fake `cmds`, and the boundaries the design
promises: the hands are constrained and never re-parented, only the weapon
goes through OverRig, and the retarget refuses a connected rig.

Spec: docs/superpowers/specs/2026-09-18-connections-design.md
"""

import ast
import os
import unittest

import maya_hub
import maya_rig_retarget
from maya_scenesetup import connections as cx

from tests.uifakes import FakeUiCmds

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "SkeldarAnim")


class Hands(unittest.TestCase):

    def test_both_by_default_in_rig_order(self):
        self.assertEqual(cx.hands_to_connect(True, True), ["R", "L"])

    def test_one_or_none(self):
        self.assertEqual(cx.hands_to_connect(False, True), ["L"])
        self.assertEqual(cx.hands_to_connect(True, False), ["R"])
        self.assertEqual(cx.hands_to_connect(False, False), [])


class BlendRefusal(unittest.TestCase):

    def test_an_unkeyed_blend_is_never_a_refusal(self):
        self.assertIsNone(cx.blend_refusal("R", 0.0, keyed=False))
        self.assertIsNone(cx.blend_refusal("R", 10.0, keyed=False))

    def test_a_blend_keyed_at_ik_passes(self):
        self.assertIsNone(cx.blend_refusal("L", 10.0, keyed=True))

    def test_a_blend_keyed_elsewhere_is_named(self):
        text = cx.blend_refusal("L", 3.0, keyed=True)
        self.assertIn("left hand", text)
        self.assertIn("FKIKArm_L.FKIKBlend", text)
        self.assertIn("3", text)


class UnionRange(unittest.TestCase):

    def test_the_playback_range_alone(self):
        self.assertEqual(cx.union_range((1.0, 24.0), []), (1.0, 24.0))

    def test_the_weapon_keys_widen_it(self):
        self.assertEqual(cx.union_range((10.0, 24.0), [-5.0, 30.0]),
                         (-5.0, 30.0))

    def test_fractions_snap_outward(self):
        """Trap 50's lesson from the export side: a fractional end frame
        must widen, never clip."""
        self.assertEqual(cx.union_range((0.4, 88.792), []), (0.0, 89.0))


class Messages(unittest.TestCase):

    def test_connected_names_the_hands_and_the_frame(self):
        text = cx.connected_message(["R", "L"], 12.0, lifted=True)
        self.assertIn("right hand, left hand", text)
        self.assertIn("frame 12", text)
        self.assertIn("weapon out to world", text)
        self.assertNotIn("weapon out", cx.connected_message(["R"], 0.0, False))

    def test_disconnected_names_the_span(self):
        text = cx.disconnected_message(["R"], (0.0, 48.0), returned=True)
        self.assertIn("right hand", text)
        self.assertIn("0..48", text)
        self.assertIn("back in the hand", text)

    def test_already_and_header(self):
        self.assertIn("Disconnect first", cx.already_message(["L"]))
        self.assertEqual(cx.header_text(None, None, []), "no rig in the scene")


class HeaderText(unittest.TestCase):

    def setUp(self):
        import maya_rigs
        self.rig = maya_rigs.Rig("Manny_Rig", "Manny_Rig:ControlSet",
                                 "|Manny_Rig:Group|Manny_Rig:Main",
                                 "|Manny_Rig:Group", "|Manny_Rig:root")

    def test_no_weapon(self):
        self.assertIn("no weapon", cx.header_text(self.rig, None, []))

    def test_weapon_in_hand_hands_free(self):
        text = cx.header_text(self.rig, "|a|b|LongSwordMesh", [])
        self.assertIn("LongSwordMesh", text)
        self.assertIn("hands free", text)

    def test_connected(self):
        text = cx.header_text(self.rig, "|LongSwordMesh", ["R", "L"])
        self.assertIn("right hand, left hand connected", text)


class Panel(unittest.TestCase):

    def setUp(self):
        self.real = (cx.cmds, cx.refresh)
        self.fake = FakeUiCmds()
        cx.cmds = self.fake
        cx.refresh = lambda *a: ""
        cx.build_panel()

    def tearDown(self):
        cx.cmds, cx.refresh = self.real

    def test_two_checkboxes_two_buttons_a_header_and_a_status(self):
        self.assertIn(cx._RIGHT, self.fake.children)
        self.assertIn(cx._LEFT, self.fake.children)
        self.assertIn(cx.HEADER, self.fake.children)
        self.assertIn(cx.STATUS, self.fake.children)
        labels = [c[2].get("label") for c in self.fake.calls if c[0] == "button"]
        self.assertEqual(labels, ["Connect", "Disconnect"])
        self.assertEqual(self.fake.windows, {})
        self.assertTrue(cx.is_open())

    def test_both_hands_checked_by_default(self):
        boxes = [c for c in self.fake.calls if c[0] == "checkBox"
                 and not c[2].get("query")]
        self.assertEqual([c[2]["value"] for c in boxes], [True, True])

    def test_a_remembered_choice_comes_back(self):
        self.fake.optionvars[cx._OPTIONVAR.format("left")] = 0
        self.fake.children = []
        self.fake.calls = []
        cx.build_panel()
        boxes = [c for c in self.fake.calls if c[0] == "checkBox"
                 and not c[2].get("query")]
        self.assertEqual([c[2]["value"] for c in boxes], [True, False])

    def test_ticking_a_box_is_remembered(self):
        boxes = [c for c in self.fake.calls if c[0] == "checkBox"
                 and not c[2].get("query")]
        boxes[1][2]["changeCommand"](False)
        self.assertEqual(self.fake.optionvars[cx._OPTIONVAR.format("left")], 0)

    def test_show_window_opens_the_hub_on_connections(self):
        asked = []
        saved = maya_hub.show
        maya_hub.show = lambda key=None: asked.append(key) or "hub"
        try:
            cx.show_window()
        finally:
            maya_hub.show = saved
        self.assertEqual(asked, ["connections"])
        sec = maya_hub.section("connections")
        self.assertEqual((sec.module, sec.builder),
                         ("maya_scenesetup.connections", "build_panel"))

    def test_the_section_follows_weapons(self):
        keys = [s.key for s in maya_hub.SECTIONS]
        self.assertEqual(keys.index("connections"), keys.index("weapons") + 1)


class Boundaries(unittest.TestCase):
    """What the module may and may not do, read off its source."""

    def _source(self):
        path = os.path.join(PLUGIN, "maya_scenesetup", "connections.py")
        with open(path, encoding="utf-8") as handle:
            return handle.read()

    def test_the_hands_are_never_reparented(self):
        """The rig hierarchy stays: no `cmds.parent(` on a control, and the
        OverRig parent procs are reached only for the weapon."""
        tree = ast.parse(self._source())
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
        names = []
        for call in calls:
            func = call.func
            if isinstance(func, ast.Attribute):
                names.append(func.attr)
        self.assertNotIn("parent", names)
        self.assertIn("parentConstraint", names)
        self.assertIn("parent_out", names)
        self.assertIn("parent_in", names)
        self.assertIn("bakeResults", names)

    def test_no_mel_eval_of_our_own(self):
        self.assertNotIn("mel.eval", self._source())

    def test_the_marker_is_an_attribute_not_a_name(self):
        self.assertEqual(cx.MARKER, "skeldarHandLink")
        self.assertIn("attributeQuery(MARKER", self._source())

    def test_the_retarget_refuses_a_connected_rig(self):
        saved = (maya_rig_retarget.hands_connected, maya_rig_retarget.resolve)
        try:
            maya_rig_retarget.hands_connected = lambda rig: "connected!"
            maya_rig_retarget.resolve = lambda rig: (rig, object(), "")
            ok, text = maya_rig_retarget.run_retarget(rig=object())
            baked = maya_rig_retarget.bake(rig=object())
        finally:
            maya_rig_retarget.hands_connected, maya_rig_retarget.resolve = saved
        self.assertEqual(baked, "connected!")
        self.assertFalse(ok)
        self.assertEqual(text, "connected!")

    def test_no_shelf_button_for_connections(self):
        """The rule of 2026-09-17: a new tool is a section, nothing else."""
        import install
        labels = [row[0] for row in install._PYTHON_BUTTONS]
        self.assertNotIn("Connections", labels)


if __name__ == "__main__":
    unittest.main()
