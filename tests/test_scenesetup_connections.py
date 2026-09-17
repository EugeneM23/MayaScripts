"""Connections: who drives whom - the two hands and the weapon (2026-09-18).

The pure model (scheme, cycle, arrows, plan, messages), the panel on a fake
`cmds`, and the boundaries the design promises: the hands are constrained
and never re-parented, only the weapon goes through OverRig, the retarget
refuses a rig with following hands, no shelf button.

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

H, F = cx.HOLDS, cx.FOLLOWS


def scheme(left=None, right=None):
    return {"L": left, "R": right}


class TheModel(unittest.TestCase):

    def test_master_and_followers(self):
        self.assertEqual(cx.master(scheme(right=H)), "R")
        self.assertIsNone(cx.master(scheme(F, F)))
        self.assertEqual(cx.followers(scheme(F, H)), ["L"])
        self.assertEqual(cx.followers(scheme(F, F)), ["L", "R"])

    def test_every_case_the_animator_named_is_a_scheme(self):
        cases = {
            "both hands to the sword": scheme(F, F),
            "one hand to the sword": scheme(right=F),
            "sword in the right hand": scheme(right=H),
            "sword in the left hand": scheme(left=H),
            "sword in the right, left hand to the sword": scheme(F, H),
        }
        for name, s in cases.items():
            self.assertTrue(cx.describe(s), name)
        self.assertEqual(cx.describe(scheme(F, H)),
                         "weapon in the right hand; left hand follows")
        self.assertEqual(cx.describe(scheme(F, F)),
                         "weapon in world; left hand, right hand follow")
        self.assertEqual(cx.describe(scheme(right=H)),
                         "weapon in the right hand; left hand free")
        self.assertEqual(cx.describe(scheme()), "weapon in world; hands free")


class Cycle(unittest.TestCase):

    def test_none_follows_holds_none(self):
        s = scheme()
        s = cx.cycle(s, "L")
        self.assertEqual(s["L"], F)
        s = cx.cycle(s, "L")
        self.assertEqual(s["L"], H)
        s = cx.cycle(s, "L")
        self.assertIsNone(s["L"])

    def test_one_hand_holds_at_most(self):
        s = scheme(right=H)
        s = cx.cycle(cx.cycle(s, "L"), "L")          # L -> follows -> holds
        self.assertEqual(s, scheme(left=H, right=None))

    def test_the_other_link_is_otherwise_untouched(self):
        s = cx.cycle(scheme(right=F), "L")
        self.assertEqual(s, scheme(F, F))

    def test_cycle_does_not_mutate_its_input(self):
        s = scheme()
        cx.cycle(s, "R")
        self.assertEqual(s, scheme())


class Arrows(unittest.TestCase):
    """The button stands between the hand and the weapon; the arrow points
    from the driver to the driven."""

    def test_a_holding_hand_points_at_the_weapon(self):
        self.assertEqual(cx.arrow("L", H), "→")   # L -> W
        self.assertEqual(cx.arrow("R", H), "←")   # W <- R

    def test_a_following_hand_is_pointed_at_by_the_weapon(self):
        self.assertEqual(cx.arrow("L", F), "←")   # L <- W
        self.assertEqual(cx.arrow("R", F), "→")   # W -> R

    def test_no_link_is_a_dot(self):
        self.assertEqual(cx.arrow("L", None), cx.EMPTY)
        self.assertEqual(cx.arrow("R", None), cx.EMPTY)


class Plan(unittest.TestCase):

    def test_nothing_to_do(self):
        self.assertEqual(cx.plan(scheme(right=H), scheme(right=H)), [])

    def test_both_hands_to_the_weapon_from_the_right_hand(self):
        self.assertEqual(cx.plan(scheme(right=H), scheme(F, F)),
                         [("lift", "R"), ("follow", "L"), ("follow", "R")])

    def test_back_into_the_right_hand(self):
        self.assertEqual(cx.plan(scheme(F, F), scheme(right=H)),
                         [("release", "L"), ("release", "R"), ("hang", "R")])

    def test_weapon_from_right_hand_to_left_hand(self):
        self.assertEqual(cx.plan(scheme(right=H), scheme(left=H)),
                         [("lift", "R"), ("hang", "L")])

    def test_right_holds_left_follows_from_right_holds(self):
        self.assertEqual(cx.plan(scheme(right=H), scheme(F, H)),
                         [("follow", "L")])

    def test_releases_come_first_and_follows_last(self):
        steps = cx.plan(scheme(F, H), scheme(H, F))
        kinds = [k for k, _ in steps]
        self.assertEqual(kinds, ["release", "lift", "hang", "follow"])
        self.assertEqual(steps[0], ("release", "L"))
        self.assertEqual(steps[-1], ("follow", "R"))


class Messages(unittest.TestCase):

    def test_blend_refusal(self):
        self.assertIsNone(cx.blend_refusal("R", 0.0, keyed=False))
        self.assertIsNone(cx.blend_refusal("L", 10.0, keyed=True))
        text = cx.blend_refusal("L", 3.0, keyed=True)
        self.assertIn("left hand", text)
        self.assertIn("FKIKArm_L.FKIKBlend", text)

    def test_union_range_snaps_outward(self):
        self.assertEqual(cx.union_range((0.4, 88.792), []), (0.0, 89.0))
        self.assertEqual(cx.union_range((10.0, 24.0), [-5.0, 30.0]),
                         (-5.0, 30.0))

    def test_applied_names_each_step_and_the_result(self):
        text = cx.applied_message([("lift", "R"), ("follow", "L"),
                                   ("follow", "R")], 6.0, scheme(F, F))
        self.assertIn("weapon out of the right hand to world", text)
        self.assertIn("left hand follows (grip as at frame 6)", text)
        self.assertIn("-> weapon in world; left hand, right hand follow", text)

    def test_header(self):
        import maya_rigs
        rig = maya_rigs.Rig("Manny_Rig", "Manny_Rig:ControlSet",
                            "|Manny_Rig:Group|Manny_Rig:Main",
                            "|Manny_Rig:Group", "|Manny_Rig:root")
        self.assertEqual(cx.header_text(None, None, scheme()), "no rig in the scene")
        self.assertIn("Weapons > Add", cx.header_text(rig, None, scheme()))
        text = cx.header_text(rig, "|a|LongSwordMesh", scheme(F, H))
        self.assertIn("LongSwordMesh", text)
        self.assertIn("weapon in the right hand; left hand follows", text)


class Panel(unittest.TestCase):

    def setUp(self):
        self.real = (cx.cmds, cx.refresh)
        self.fake = FakeUiCmds()
        cx.cmds = self.fake
        cx.refresh = lambda *a: ""
        cx._PENDING.clear()
        cx.build_panel()

    def tearDown(self):
        cx.cmds, cx.refresh = self.real
        cx._PENDING.clear()

    def _buttons(self):
        return [c for c in self.fake.calls if c[0] == "button"
                and not c[2].get("edit")]

    def test_two_arrow_buttons_apply_a_header_and_a_status_no_window(self):
        self.assertIn(cx.LINK_BUTTON["L"], self.fake.children)
        self.assertIn(cx.LINK_BUTTON["R"], self.fake.children)
        self.assertIn(cx.HEADER, self.fake.children)
        self.assertIn(cx.STATUS, self.fake.children)
        self.assertEqual([c[2]["label"] for c in self._buttons()],
                         [cx.EMPTY, cx.EMPTY, "Apply"])
        self.assertEqual(self.fake.windows, {})
        self.assertTrue(cx.is_open())

    def test_the_row_reads_left_hand_weapon_right_hand(self):
        labels = [c[2].get("label") for c in self.fake.calls
                  if c[0] == "text" and not c[2].get("edit")]
        self.assertIn("Left hand", labels)
        self.assertIn("Weapon", labels)
        self.assertIn("Right hand", labels)
        self.assertLess(labels.index("Left hand"), labels.index("Weapon"))
        self.assertLess(labels.index("Weapon"), labels.index("Right hand"))

    def test_an_arrow_press_repaints_and_asks_for_apply_without_touching_the_scene(self):
        import maya_rigs
        rig = maya_rigs.Rig("Manny_Rig", "cs", "|G|Main", "|G", "|root")
        saved = (cx.maya_rigs.current_rig, cx.read_scheme)
        cx.maya_rigs.current_rig = lambda selection=None: (rig, "")
        cx.read_scheme = lambda rig, bones=None, weapon=None: scheme(right=H)
        try:
            self._buttons()[0][2]["command"]()            # the left arrow
        finally:
            cx.maya_rigs.current_rig, cx.read_scheme = saved
        edits = [c for c in self.fake.calls if c[0] == "button" and c[2].get("edit")]
        self.assertEqual(edits[0][1][0], cx.LINK_BUTTON["L"])
        self.assertEqual(edits[0][2]["label"], "←")     # left follows
        self.assertEqual(cx._PENDING["Manny_Rig"], scheme(F, H))
        status = [c for c in self.fake.calls
                  if c[0] == "text" and c[1] == (cx.STATUS,) and c[2].get("edit")]
        self.assertIn("press Apply for: weapon in the right hand; left hand follows",
                      status[-1][2]["label"])
        self.assertFalse([c for c in self.fake.calls
                          if c[0] in ("parentConstraint", "bakeResults")])

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
        """The rig hierarchy stays: no `cmds.parent(` anywhere, and the
        OverRig parent procs are reached only for the weapon."""
        tree = ast.parse(self._source())
        names = [node.func.attr for node in ast.walk(tree)
                 if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Attribute)]
        self.assertNotIn("parent", names)
        for wanted in ("parentConstraint", "parent_out", "parent_in",
                       "bakeResults", "unlink"):
            self.assertIn(wanted, names, wanted)

    def test_no_mel_eval_of_our_own(self):
        self.assertNotIn("mel.eval", self._source())

    def test_the_marker_is_an_attribute_not_a_name(self):
        self.assertEqual(cx.MARKER, "skeldarHandLink")
        self.assertIn("attributeQuery(MARKER", self._source())

    def test_the_drive_bone_takes_no_offset(self):
        """The export socket sits ON the weapon wherever the animator put
        it: the bone's constraint is made without maintainOffset."""
        self.assertIn("cmds.parentConstraint(weapon, bone, maintainOffset=False)",
                      self._source())

    def test_the_retarget_refuses_a_connected_rig(self):
        saved = (maya_rig_retarget.hands_connected, maya_rig_retarget.resolve)
        try:
            maya_rig_retarget.hands_connected = lambda rig: "connected!"
            maya_rig_retarget.resolve = lambda rig: (rig, object(), "")
            ok, text = maya_rig_retarget.run_retarget(rig=object())
            baked = maya_rig_retarget.bake(rig=object())
        finally:
            maya_rig_retarget.hands_connected, maya_rig_retarget.resolve = saved
        self.assertFalse(ok)
        self.assertEqual(text, "connected!")
        self.assertEqual(baked, "connected!")

    def test_no_shelf_button_for_connections(self):
        """The rule of 2026-09-17: a new tool is a section, nothing else."""
        import install
        labels = [row[0] for row in install._PYTHON_BUTTONS]
        self.assertNotIn("Connections", labels)


if __name__ == "__main__":
    unittest.main()
