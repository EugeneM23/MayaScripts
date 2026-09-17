"""Connections: who drives whom - the two hands and the weapon (2026-09-18).

The pure model (scheme, plan, the three parent menus and their conflicts,
messages), the panel on a fake `cmds`, and the boundaries the design
promises: the hands are constrained and never re-parented, only the weapon
goes through OverRig, the retarget refuses a rig with following hands, no
shelf button.

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

    def test_every_case_the_animator_named_reads_back(self):
        self.assertEqual(cx.describe(scheme(F, H)),
                         "weapon in the right hand; left hand follows")
        self.assertEqual(cx.describe(scheme(F, F)),
                         "weapon in world; left hand, right hand follow")
        self.assertEqual(cx.describe(scheme(right=H)),
                         "weapon in the right hand; left hand free")
        self.assertEqual(cx.describe(scheme(left=H)),
                         "weapon in the left hand; right hand free")
        self.assertEqual(cx.describe(scheme(right=F)),
                         "weapon in world; right hand follows")
        self.assertEqual(cx.describe(scheme()), "weapon in world; hands free")


class Menus(unittest.TestCase):
    """Hand_R / Hand_L / Weapon, each with a parent."""

    def test_menus_from_scheme(self):
        self.assertEqual(cx.menus_from_scheme(scheme(right=H)),
                         {"R": "Free", "L": "Free", "W": "Hand_R"})
        self.assertEqual(cx.menus_from_scheme(scheme(F, F)),
                         {"R": "Weapon", "L": "Weapon", "W": "World"})
        self.assertEqual(cx.menus_from_scheme(scheme(F, H)),
                         {"R": "Free", "L": "Weapon", "W": "Hand_R"})

    def test_scheme_from_menus_round_trips(self):
        for s in (scheme(right=H), scheme(F, F), scheme(F, H), scheme(left=H),
                  scheme(), scheme(right=F)):
            self.assertEqual(cx.scheme_from_menus(cx.menus_from_scheme(s)), s)

    def test_the_weapon_menu_wins_a_conflict(self):
        """Weapon in Hand_R while Hand_R says Weapon: the hand holds."""
        self.assertEqual(cx.scheme_from_menus({"R": "Weapon", "L": "Free",
                                               "W": "Hand_R"}),
                         scheme(right=H))

    def test_picking_the_weapons_hand_frees_that_hand(self):
        fixed, note = cx.resolve_menus({"R": "Weapon", "L": "Weapon",
                                        "W": "Hand_R"}, changed="W")
        self.assertEqual(fixed, {"R": "Free", "L": "Weapon", "W": "Hand_R"})
        self.assertIn("Hand_R set to Free", note)

    def test_a_hand_following_the_weapon_it_holds_puts_it_in_world(self):
        fixed, note = cx.resolve_menus({"R": "Weapon", "L": "Free",
                                        "W": "Hand_R"}, changed="R")
        self.assertEqual(fixed, {"R": "Weapon", "L": "Free", "W": "World"})
        self.assertIn("Weapon set to World", note)

    def test_no_conflict_no_note(self):
        menus = {"R": "Free", "L": "Weapon", "W": "Hand_R"}
        self.assertEqual(cx.resolve_menus(menus, "L"), (menus, ""))


class WantedForRow(unittest.TestCase):
    """A row's Apply changes that link only."""

    def test_hand_row_to_weapon(self):
        self.assertEqual(cx.wanted_for_row(scheme(right=H), "L", "Weapon"),
                         scheme(F, H))

    def test_hand_row_to_free_releases_a_follower(self):
        self.assertEqual(cx.wanted_for_row(scheme(F, H), "L", "Free"),
                         scheme(None, H))

    def test_hand_row_to_free_on_the_holder_puts_the_weapon_in_world(self):
        self.assertEqual(cx.wanted_for_row(scheme(right=H), "R", "Free"),
                         scheme())

    def test_weapon_row_to_the_other_hand(self):
        self.assertEqual(cx.wanted_for_row(scheme(F, H), "W", "Hand_L"),
                         scheme(H, None))

    def test_weapon_row_to_world_keeps_followers(self):
        self.assertEqual(cx.wanted_for_row(scheme(F, H), "W", "World"),
                         scheme(F, None))

    def test_the_holder_asked_to_follow_becomes_a_follower(self):
        self.assertEqual(cx.wanted_for_row(scheme(right=H), "R", "Weapon"),
                         scheme(None, F))


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
        self.assertEqual([k for k, _ in steps],
                         ["release", "lift", "hang", "follow"])
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


class FakeMenuCmds(FakeUiCmds):
    """The UI fake plus optionMenus that hold a value."""

    def __init__(self):
        FakeUiCmds.__init__(self)
        self.menu_values = {}
        self.menu_items = {}
        self._current_menu = None

    def optionMenu(self, name=None, **kwargs):
        self.calls.append(("optionMenu", (name,), kwargs))
        if kwargs.get("exists"):
            return name in self.menu_values
        if kwargs.get("query") or kwargs.get("q"):
            return self.menu_values.get(name)
        if kwargs.get("edit") or kwargs.get("e"):
            if "value" in kwargs:
                self.menu_values[name] = kwargs["value"]
            return name
        self.menu_values[name] = None
        self.menu_items[name] = []
        self._current_menu = name
        self.children.append(name)
        return name

    def menuItem(self, **kwargs):
        self.menu_items[self._current_menu].append(kwargs.get("label"))
        if self.menu_values[self._current_menu] is None:
            self.menu_values[self._current_menu] = kwargs.get("label")
        return kwargs.get("label")


class Panel(unittest.TestCase):

    def setUp(self):
        self.real = (cx.cmds, cx.refresh, cx.maya_rigs.current_rig,
                     cx.read_scheme)
        self.fake = FakeMenuCmds()
        cx.cmds = self.fake
        cx.refresh = lambda *a: ""
        cx.build_panel()

    def tearDown(self):
        (cx.cmds, cx.refresh, cx.maya_rigs.current_rig,
         cx.read_scheme) = self.real

    def _buttons(self):
        return [c for c in self.fake.calls if c[0] == "button"
                and not c[2].get("edit")]

    def test_three_rows_each_with_a_parent_menu_and_apply_then_apply_all(self):
        for row in ("R", "L", "W"):
            self.assertIn(cx.MENU[row], self.fake.children)
        self.assertEqual(self.fake.menu_items[cx.MENU["R"]], ["Free", "Weapon"])
        self.assertEqual(self.fake.menu_items[cx.MENU["L"]], ["Free", "Weapon"])
        self.assertEqual(self.fake.menu_items[cx.MENU["W"]],
                         ["World", "Hand_R", "Hand_L"])
        self.assertEqual([c[2]["label"] for c in self._buttons()],
                         ["Apply", "Apply", "Apply", "Apply all"])
        labels = [c[2].get("label") for c in self.fake.calls
                  if c[0] == "text" and not c[2].get("edit")]
        for wanted in ("Hand_R", "Hand_L", "Weapon"):
            self.assertIn(wanted, labels)
        self.assertIn(cx.HEADER, self.fake.children)
        self.assertIn(cx.STATUS, self.fake.children)
        self.assertEqual(self.fake.windows, {})
        self.assertTrue(cx.is_open())

    def test_a_pick_that_makes_a_cycle_fixes_the_other_menu_and_asks_for_apply(self):
        self.fake.menu_values[cx.MENU["R"]] = "Weapon"
        self.fake.menu_values[cx.MENU["W"]] = "Hand_R"
        menus = [c for c in self.fake.calls if c[0] == "optionMenu"
                 and not c[2].get("edit") and not c[2].get("query")]
        menus[2][2]["changeCommand"]()                  # the Weapon row picked
        self.assertEqual(self.fake.menu_values[cx.MENU["R"]], "Free")
        status = [c for c in self.fake.calls
                  if c[0] == "text" and c[1] == (cx.STATUS,) and c[2].get("edit")]
        self.assertIn("Hand_R set to Free", status[-1][2]["label"])
        self.assertIn("press Apply for: weapon in the right hand; left hand free",
                      status[-1][2]["label"])
        self.assertFalse([c for c in self.fake.calls
                          if c[0] in ("parentConstraint", "bakeResults")])

    def test_a_rows_apply_changes_that_link_only(self):
        import maya_rigs
        rig = maya_rigs.Rig("Manny_Rig", "cs", "|G|Main", "|G", "|root")
        asked = []
        cx.maya_rigs.current_rig = lambda selection=None: (rig, "")
        cx.read_scheme = lambda rig, bones=None, weapon=None: scheme(right=H)
        saved_apply = cx.apply
        cx.apply = lambda wanted, rig=None: asked.append(wanted) or "done"
        try:
            self.fake.menu_values[cx.MENU["L"]] = "Weapon"
            self._buttons()[1][2]["command"]()          # Hand_L's Apply
        finally:
            cx.apply = saved_apply
        self.assertEqual(asked, [scheme(F, H)])

    def test_apply_all_takes_all_three_menus(self):
        asked = []
        saved_apply = cx.apply
        cx.apply = lambda wanted, rig=None: asked.append(wanted) or "done"
        try:
            self.fake.menu_values[cx.MENU["R"]] = "Weapon"
            self.fake.menu_values[cx.MENU["L"]] = "Weapon"
            self.fake.menu_values[cx.MENU["W"]] = "World"
            self._buttons()[3][2]["command"]()          # Apply all
        finally:
            cx.apply = saved_apply
        self.assertEqual(asked, [scheme(F, F)])

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
        import install
        labels = [row[0] for row in install._PYTHON_BUTTONS]
        self.assertNotIn("Connections", labels)


if __name__ == "__main__":
    unittest.main()
