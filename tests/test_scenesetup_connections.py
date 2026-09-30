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

    def test_a_keyed_blend_is_no_longer_a_refusal(self):
        """2026-09-30: a following arm is switched to IK keeping what it
        shows, so a keyed blend is made IK instead of refused."""
        self.assertFalse(hasattr(cx, "blend_refusal"))
        self.assertFalse(hasattr(cx, "IK_BLEND"))

    def test_arms_text_names_the_mixed_arms(self):
        self.assertEqual(cx.arms_text({"R": "FK", "L": "IK"}), "")
        self.assertEqual(cx.arms_text({"R": None, "L": "IK"}),
                         "Arm_R mixed FK/IK (keyed)")
        self.assertEqual(cx.arms_text({"R": None, "L": None}),
                         "Arm_R, Arm_L mixed FK/IK (keyed)")
        self.assertEqual(cx.arms_text({}), "")          # a rig with no arms

    def test_union_range_snaps_outward(self):
        self.assertEqual(cx.union_range((0.4, 88.792), []), (0.0, 89.0))
        self.assertEqual(cx.union_range((10.0, 24.0), [-5.0, 30.0]),
                         (-5.0, 30.0))

    def test_applied_names_each_step_and_the_result(self):
        text = cx.applied_message([("lift", "R"), ("follow", "L"),
                                   ("follow", "R")], scheme(F, F))
        self.assertIn("weapon out of the right hand to world", text)
        self.assertIn("left hand follows (its track kept on the proxy)", text)
        self.assertIn("-> weapon in world; left hand, right hand follow", text)

    def test_is_constant_collapses_a_still_channel_only(self):
        """A proxy channel that never moved loses its keys so the animator's
        own keys start from a plain value; a moving one keeps them."""
        self.assertTrue(cx.is_constant([]))
        self.assertTrue(cx.is_constant([1.0, 1.0, 1.0 + 1e-9]))
        self.assertFalse(cx.is_constant([1.0, 1.0, 1.5]))

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
        text = cx.header_text(rig, None, scheme(), arms="Arm_R mixed FK/IK (keyed)")
        self.assertTrue(text.endswith("; Arm_R mixed FK/IK (keyed)"))


class FakeMenuCmds(FakeUiCmds):
    """The UI fake plus the three rows' segments (2026-09-28): radio
    collections that remember which of their buttons is selected."""

    def __init__(self):
        FakeUiCmds.__init__(self)
        self.selected = {}          # collection -> selected button name
        self.segments = {}          # collection -> [(button, label)]
        self.owner = {}             # button -> collection
        self.on = {}                # button -> onCommand
        self.boxes = {}             # FK/IK check box -> value, commands
        self._current = None

    def iconTextRadioCollection(self, name=None, **kwargs):
        self.calls.append(("iconTextRadioCollection", (name,), kwargs))
        if kwargs.get("query") or kwargs.get("q"):
            return self.selected.get(name)
        self.selected[name] = None
        self.segments[name] = []
        self._current = name
        return name

    def iconTextRadioButton(self, name=None, **kwargs):
        self.calls.append(("iconTextRadioButton", (name,), kwargs))
        if kwargs.get("exists"):
            return name in self.owner
        if kwargs.get("edit") or kwargs.get("e"):
            if kwargs.get("select"):
                self.selected[self.owner[name]] = name
            return name
        self.owner[name] = self._current
        self.segments[self._current].append((name, kwargs.get("label")))
        self.on[name] = kwargs.get("onCommand")
        if kwargs.get("select"):
            self.selected[self._current] = name
        self.children.append(name)
        return name

    def iconTextCheckBox(self, name=None, **kwargs):
        """The FK / IK boxes (2026-09-30): a value, an on and an off command;
        an edit of the value runs neither (the real control's, too)."""
        self.calls.append(("iconTextCheckBox", (name,), kwargs))
        if kwargs.get("exists"):
            return name in self.boxes
        if kwargs.get("query") or kwargs.get("q"):
            return self.boxes[name]["value"]
        if kwargs.get("edit") or kwargs.get("e"):
            if "value" in kwargs:
                self.boxes[name]["value"] = kwargs["value"]
            return name
        self.boxes[name] = {"value": kwargs.get("value", False),
                            "on": kwargs.get("onCommand"),
                            "off": kwargs.get("offCommand"),
                            "label": kwargs.get("label")}
        self.children.append(name)
        return name

    def press_box(self, name):
        """The animator clicks a box: it toggles, then its command runs."""
        box = self.boxes[name]
        box["value"] = not box["value"]
        return (box["on"] if box["value"] else box["off"])()

    def pick(self, row, choice):
        """The animator presses a segment: selected, then its onCommand."""
        name = cx.segment_name(row, choice)
        self.selected[cx.MENU[row]] = name
        self.on[name]()

    def value(self, row):
        return cx.menus()[row]


class Panel(unittest.TestCase):

    def setUp(self):
        self.real = (cx.cmds, cx.refresh, cx.maya_rigs.current_rig,
                     cx.read_scheme)
        self.fake = FakeMenuCmds()
        cx.cmds = self.fake
        cx.refresh = lambda *a: ""
        cx.hubstyle.take_marks()
        cx.build_panel()
        self.marks = dict((m.name, m) for m in cx.hubstyle.take_marks())

    def tearDown(self):
        (cx.cmds, cx.refresh, cx.maya_rigs.current_rig,
         cx.read_scheme) = self.real

    def _buttons(self):
        return [c for c in self.fake.calls if c[0] == "button"
                and not c[2].get("edit")]

    def test_three_rows_each_with_segments_and_apply_then_apply_all(self):
        labels_of = lambda row: [label for _n, label in
                                 self.fake.segments[cx.MENU[row]]]
        self.assertEqual(labels_of("R"), ["Free", "Weapon"])
        self.assertEqual(labels_of("L"), ["Free", "Weapon"])
        self.assertEqual(labels_of("W"), ["World", "Hand R", "Hand L"])
        self.assertEqual([c[2]["label"] for c in self._buttons()],
                         ["Apply", "Apply", "Apply", "Apply all",
                          "BakeAcross", "Release"])
        labels = [c[2].get("label") for c in self.fake.calls
                  if c[0] == "text" and not c[2].get("edit")]
        for wanted in ("Hand_R", "Hand_L", "Weapon"):
            self.assertIn(wanted, labels)
        #  no description paragraph (the animator: «весь текст описания
        #  убираем») - the header, the two FK/IK rows (2026-09-30), the
        #  chooser's label (2026-09-29), the three row labels and the status
        self.assertIn("Acts on", labels)
        self.assertEqual(labels[1:3], ["Arm_R", "Arm_L"])
        self.assertEqual(len(labels), 8)

    def test_every_row_starts_on_its_first_choice(self):
        self.assertEqual(cx.menus(), {"R": "Free", "L": "Free", "W": "World"})

    def test_the_segments_are_marked_for_the_skin(self):
        for row, choices in cx._ROWS:
            for choice in choices:
                self.assertEqual(self.marks[cx.segment_name(row, choice)].role,
                                 "segment")
        segment_rows = [m for m in self.marks.values()
                        if m.role == "segments"]
        self.assertEqual(len(segment_rows), 6)      # the chooser's, FK/IK's too
        for side in ("R", "L"):
            for mode in ("FK", "IK"):
                self.assertEqual(self.marks[cx.fkik_box(side, mode)].role, "segment")
        self.assertTrue(all(m.layout for m in segment_rows))
        self.assertEqual(self.marks[cx.HEADER].role, "context")
        self.assertEqual(self.marks[cx.STATUS].role, "status")
        roles = [(m.role, m.icon) for m in self.marks.values()
                 if m.role in ("primary", "tool", "secondary")]
        self.assertEqual(roles.count(("tool", "check")), 3)
        self.assertIn(("primary", "check"), roles)
        self.assertIn(("secondary", "link"), roles)
        self.assertIn(("secondary", "unlink"), roles)

    def test_set_menus_selects_the_segment(self):
        cx._set_menus({"R": "Weapon", "W": "Hand_L"})
        self.assertEqual(cx.menus(), {"R": "Weapon", "L": "Free",
                                      "W": "Hand_L"})

    def test_bake_across_and_release_press_the_module(self):
        asked = []
        saved = (cx.bake_across, cx.release_across)
        cx.bake_across = lambda selection=None: asked.append("bake") or "done"
        cx.release_across = lambda selection=None: asked.append("release") or "done"
        try:
            self._buttons()[4][2]["command"]()
            self._buttons()[5][2]["command"]()
        finally:
            cx.bake_across, cx.release_across = saved
        self.assertEqual(asked, ["bake", "release"])
        self.assertIn(cx.HEADER, self.fake.children)
        self.assertIn(cx.STATUS, self.fake.children)
        self.assertEqual(self.fake.windows, {})
        self.assertTrue(cx.is_open())

    def test_a_pick_that_makes_a_cycle_fixes_the_other_row_and_asks_for_apply(self):
        cx._set_menus({"R": "Weapon"})
        self.fake.pick("W", "Hand_R")                   # the Weapon row picked
        self.assertEqual(self.fake.value("R"), "Free")
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
            cx._set_menus({"L": "Weapon"})
            self._buttons()[1][2]["command"]()          # Hand_L's Apply
        finally:
            cx.apply = saved_apply
        self.assertEqual(asked, [scheme(F, H)])

    def test_apply_all_takes_all_three_rows(self):
        asked = []
        saved_apply = cx.apply
        cx.apply = lambda wanted, rig=None: asked.append(wanted) or "done"
        try:
            cx._set_menus({"R": "Weapon", "L": "Weapon", "W": "World"})
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

    def _stub_switch(self):
        asked = []
        saved = cx.switch_arm
        cx.switch_arm = lambda side, mode, rig=None, highlight=None: \
            asked.append((side, mode)) or "switched"
        self.addCleanup(setattr, cx, "switch_arm", saved)
        return asked

    def test_fkik_rows_have_two_boxes_each(self):
        for side in ("R", "L"):
            self.assertEqual([self.fake.boxes[cx.fkik_box(side, m)]["label"]
                              for m in ("FK", "IK")], ["FK", "IK"])

    def test_either_press_of_a_box_switches_that_arm(self):
        """Lighting a box or un-lighting the lit one: both switch - a range
        inside a take already in that mode must still be pressable."""
        asked = self._stub_switch()
        self.fake.press_box(cx.fkik_box("R", "IK"))        # off -> on
        self.fake.press_box(cx.fkik_box("R", "IK"))        # on -> off
        self.fake.press_box(cx.fkik_box("L", "FK"))
        self.assertEqual(asked, [("R", "IK"), ("R", "IK"), ("L", "FK")])

    def test_the_refresh_lights_the_mode_and_presses_nothing(self):
        """Even if Maya ran a box's command on an edit (trap 116)."""
        asked = self._stub_switch()
        plain = self.fake.iconTextCheckBox

        def edit_fires(name=None, **kwargs):
            out = plain(name, **kwargs)
            if kwargs.get("edit"):
                box = self.fake.boxes[name]
                (box["on"] if box["value"] else box["off"])()
            return out
        self.fake.iconTextCheckBox = edit_fires
        cx._set_fkik({"R": "IK", "L": None})
        value = lambda side, mode: self.fake.boxes[cx.fkik_box(side, mode)]["value"]
        self.assertEqual((value("R", "FK"), value("R", "IK")), (False, True))
        self.assertEqual((value("L", "FK"), value("L", "IK")), (False, False))
        self.assertEqual(asked, [])


class SwitchArm(unittest.TestCase):
    """`switch_arm`'s order of things, on stubs: refusals before anything
    moves, a following hand released before FK, IK refused on it."""

    def setUp(self):
        import maya_rigs
        self.rig = maya_rigs.Rig("Manny_Rig", "cs", "|G|Main", "|G", "|root")
        self.done = []
        self.saved = dict((name, getattr(cx, name)) for name in
                          ("cmds", "_rig", "following", "_release", "_span",
                           "sweep_orphans", "_control", "weapon_label"))
        self.saved_fkik = dict((name, getattr(cx.fkik, name)) for name in
                               ("limb", "whole_take", "refusal", "switch",
                                "blend_values"))

        class Cmds(object):
            existing = set()

            def objExists(self, name):
                return name in self.existing

            def undoInfo(inner, **kwargs):
                self.done.append(("undo", "open" if kwargs.get("openChunk") else "close"))

        self.cmds = Cmds()
        cx.cmds = self.cmds
        cx._rig = lambda rig: (self.rig, "")
        cx.following = lambda rig, side: None
        cx._release = lambda rig, side, span: self.done.append(("release", side))
        cx._span = lambda weapon, controls: (0.0, 24.0)
        cx.sweep_orphans = lambda: 0
        cx._control = lambda rig, side: "|IKArm_" + side
        cx.weapon_label = lambda weapon: "Long Sword 02"
        cx.fkik.limb = lambda rig, side: ("arm_" + side, "")
        cx.fkik.whole_take = lambda arm: (0.0, 24.0)
        cx.fkik.refusal = lambda arm, mode, span, ignore=(): ""
        cx.fkik.switch = lambda arm, mode, span: self.done.append(
            ("switch", arm, mode, span)) or "Arm_R to %s" % mode
        cx.fkik.blend_values = lambda arm: [10.0]

    def tearDown(self):
        for name, value in self.saved.items():
            setattr(cx, name, value)
        for name, value in self.saved_fkik.items():
            setattr(cx.fkik, name, value)

    def test_a_free_arm_is_switched_over_the_whole_take(self):
        text = cx.switch_arm("R", "FK", highlight=False)
        self.assertEqual(self.done, [("undo", "open"),
                                     ("switch", "arm_R", "FK", (0, 24, False)),
                                     ("undo", "close")])
        self.assertEqual(text, "Arm_R to FK")

    def test_a_highlight_is_the_span(self):
        cx.switch_arm("L", "IK", highlight=(10.0, 16.0))
        self.assertIn(("switch", "arm_L", "IK", (10, 15, True)), self.done)

    def test_fk_on_a_following_hand_releases_it_first(self):
        cx.following = lambda rig, side: "|sword"
        text = cx.switch_arm("R", "FK", highlight=False)
        self.assertEqual([d[0] for d in self.done],
                         ["undo", "release", "switch", "undo"])
        self.assertIn("Hand_R released from Long Sword 02", text)

    def test_ik_on_a_following_hand_is_already_ik(self):
        cx.following = lambda rig, side: "|sword"
        text = cx.switch_arm("R", "IK", highlight=False)
        self.assertIn("already IK (it follows Long Sword 02)", text)
        self.assertEqual(self.done, [])

    def test_ik_on_a_following_hand_in_a_mixed_take_asks_for_free(self):
        cx.following = lambda rig, side: "|sword"
        cx.fkik.blend_values = lambda arm: [10.0, 0.0]
        text = cx.switch_arm("R", "IK", highlight=False)
        self.assertEqual(text, "Hand_R follows Long Sword 02 - set it Free first")
        self.assertEqual(self.done, [])

    def test_a_refusal_moves_nothing(self):
        cx.fkik.refusal = lambda arm, mode, span, ignore=(): "Arm_R is already FK"
        self.assertEqual(cx.switch_arm("R", "FK", highlight=False), "Arm_R is already FK")
        self.assertEqual(self.done, [])

    def test_a_standing_retarget_is_refused(self):
        self.cmds.existing.add("Manny_Rig:MoCapConstraints")
        self.assertEqual(cx.switch_arm("R", "FK", highlight=False), cx.RETARGETING)
        self.assertEqual(self.done, [])


class Boundaries(unittest.TestCase):
    """What the module may and may not do, read off its source."""

    def _source(self):
        path = os.path.join(PLUGIN, "maya_scenesetup", "connections.py")
        with open(path, encoding="utf-8") as handle:
            return handle.read()

    def test_the_hands_are_never_reparented(self):
        """`cmds.parent(` appears in ONE function, `_make_proxy`, and what
        it parents is our own locator; no control is ever re-parented."""
        tree = ast.parse(self._source())
        parents_in = []
        for func in ast.walk(tree):
            if not isinstance(func, ast.FunctionDef):
                continue
            for node in ast.walk(func):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                        and node.func.attr == "parent":
                    parents_in.append(func.name)
        self.assertEqual(parents_in, ["_make_proxy"])
        names = [node.func.attr for node in ast.walk(tree)
                 if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Attribute)]
        for wanted in ("parentConstraint", "parent_out", "parent_in",
                       "bakeResults", "unlink", "spaceLocator"):
            self.assertIn(wanted, names, wanted)

    def test_the_proxy_carries_the_hands_track_and_is_marked(self):
        """The follow goes through a proxy: baked from the control, the
        still channels collapsed, the control constrained to it with no
        offset, both marked by attribute."""
        source = self._source()
        self.assertEqual(cx.PROXY_MARKER, "skeldarHandProxy")
        self.assertIn("_bake_onto(obj, proxy, span)", source)
        self.assertIn("cmds.parentConstraint(proxy, obj, maintainOffset=False)",
                      source)
        self.assertIn("is_constant(values)", source)
        self.assertIn("def proxy_of(rig, side)", source)
        #  the proxies are found by ATTRIBUTE, never by a name pattern: a
        #  `*.attr` pattern does not cross a namespace colon, which is how
        #  proxies once survived a bake in the animator's scene
        self.assertNotIn('cmds.ls("*.', source)

    def test_the_rider_is_hidden_and_shown_again(self):
        source = self._source()
        self.assertIn("_set_visible(obj, False)", source)
        self.assertIn("_set_visible(obj, visible)", source)
        self.assertEqual(cx.HIDDEN_VIS, "skeldarHiddenVis")

    def test_the_proxy_is_forty_percent_bigger(self):
        self.assertAlmostEqual(cx.PROXY_SCALE, 6.0 * 1.4)


    def test_no_mel_eval_of_our_own(self):
        self.assertNotIn("mel.eval", self._source())

    def test_the_marker_is_an_attribute_not_a_name(self):
        self.assertEqual(cx.MARKER, "skeldarHandLink")
        self.assertIn("attributeQuery(MARKER", self._source())

    def test_the_weapon_hangs_in_the_hands_space_never_in_the_skeleton(self):
        """2026-09-24, «не нарушали иерархию нашего скелета»: a hold is the
        weapon in the space that follows the hand (weaponspace), re-baked by
        OverRig's parent_in into THAT -- never parent_in onto the hand bone --
        and which hand holds is read through the space."""
        source = self._source()
        self.assertIn("overrig.parent_in(weapon, weaponspace.ensure_space(hand))", source)
        self.assertNotIn("overrig.parent_in(weapon, hand)", source)
        self.assertIn("weaponspace.holding_hand(weapon)", source)
        self.assertIn("weaponspace.prune(", source)

    def _bonedrive_source(self):
        path = os.path.join(PLUGIN, "maya_scenesetup", "bonedrive.py")
        with open(path, encoding="utf-8") as handle:
            return handle.read()

    def test_the_drive_bone_takes_no_offset(self):
        """`bonedrive.drive_socket` since 2026-09-29 (the floor drives its
        bone the same way); Connections' hang goes through it."""
        self.assertIn("return bonedrive.drive_socket(weapon, bone)",
                      self._source())
        self.assertIn("cmds.parentConstraint(weapon, bone, maintainOffset=False)",
                      self._bonedrive_source())

    def test_a_framed_weapons_frame_is_undone_on_the_new_bone(self):
        """2026-09-24: the Creep Sword stands turned 45 on its bone at zero
        grip (its FRAME), so a bone that takes it over sits on its socket,
        not on the turned node: the target offset holds the frame undone,
        in the bone's own rotate order."""
        source = self._bonedrive_source()
        socket = source[source.index("def drive_socket("):]
        self.assertIn("frame_of(weapon)", socket)
        self.assertIn('.target[0].targetOffsetRotate', socket)
        self.assertIn('unframing(frame, cmds.getAttr(bone + ".rotateOrder"))', socket)

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


class BakeAcross(unittest.TestCase):
    """Every selected object rides the LAST selected through a proxy."""

    def test_the_last_selected_is_the_parent(self):
        parent, children = cx.across_plan(["|a", "|b", "|c"])
        self.assertEqual((parent, children), ("|c", ["|a", "|b"]))

    def test_fewer_than_two_is_a_refusal(self):
        parent, text = cx.across_plan(["|a"])
        self.assertIsNone(parent)
        self.assertIn("LAST", text)

    def test_a_cycle_is_refused_by_name(self):
        parent, text = cx.across_plan(["|a", "|a|b"])       # parent inside child
        self.assertIsNone(parent)
        self.assertIn("cycle", text)
        parent, text = cx.across_plan(["|c|d", "|c"])       # child inside parent
        self.assertIsNone(parent)
        self.assertIn("already inside", text)

    def test_messages(self):
        self.assertIn("2 object(s) ride proxies inside sword",
                      cx.across_message(["|a", "|b"], "|x|sword"))
        self.assertIn("2 proxy(ies) removed", cx.release_message(2, 2))


if __name__ == "__main__":
    unittest.main()


class TwoWeapons(unittest.TestCase):
    """2026-09-29: a sword in one hand, a dagger in the other. The section
    acts on one of them; a hand holds XOR follows, across both."""

    A = "|g|WeaponSpaces|hand_r_weaponSpace|LongSwordMesh"
    B = "|g|WeaponSpaces|hand_l_weaponSpace|DaggerMesh"

    def test_the_selection_names_the_weapon(self):
        self.assertEqual(cx.choose_weapon([self.A, self.B],
                                          [self.B + "|handProxy_R"], None),
                         self.B)
        self.assertEqual(cx.choose_weapon([self.A, self.B], [self.A], self.B),
                         self.A)

    def test_else_the_picked_one(self):
        self.assertEqual(cx.choose_weapon([self.A, self.B], [], self.B), self.B)

    def test_a_pick_beats_the_selection_it_was_made_under(self):
        """Measured live 2026-09-29: an Apply leaves the sword selected, and a
        pick of the dagger in the chooser snapped straight back to the
        sword. The pick is the newer word until the selection changes."""
        self.assertEqual(cx.choose_weapon([self.A, self.B], [self.A], self.B,
                                          [self.A]), self.B)
        self.assertEqual(cx.choose_weapon([self.A, self.B], [self.A], self.B,
                                          []), self.A)

    def test_a_picked_weapon_that_went_is_forgotten(self):
        self.assertEqual(cx.choose_weapon([self.A], [], self.B), self.A)

    def test_else_the_first(self):
        self.assertEqual(cx.choose_weapon([self.A, self.B], ["|elsewhere"],
                                          None), self.A)
        self.assertIsNone(cx.choose_weapon([], [], None))

    def test_a_prefix_is_not_containment(self):
        self.assertEqual(cx.choose_weapon([self.A, self.B], [self.B + "X"],
                                          None), self.A)

    def test_labels_of_one_key_carry_their_hand(self):
        self.assertEqual(cx.labels_for([("Long Sword 02", "R"),
                                        ("Long Sword 02", "L")]),
                         ["Long Sword 02 (R)", "Long Sword 02 (L)"])
        self.assertEqual(cx.labels_for([("Long Sword 02", "R"),
                                        ("Dagger 01", "L")]),
                         ["Long Sword 02", "Dagger 01"])

    def test_a_hand_the_other_weapon_hangs_in_takes_nothing(self):
        self.assertEqual(
            cx.blocked(scheme(right=H), scheme(left=H), scheme(left=H),
                       "Dagger 01"),
            "Hand_L holds the Dagger 01 - move it first")
        self.assertEqual(
            cx.blocked(scheme(right=H), scheme(left=F, right=H),
                       scheme(left=H), "Dagger 01"),
            "Hand_L holds the Dagger 01 - move it first")

    def test_a_hand_riding_the_other_weapon_takes_nothing(self):
        self.assertEqual(
            cx.blocked(scheme(right=H), scheme(left=F, right=H),
                       scheme(left=F), "Dagger 01"),
            "Hand_L follows the Dagger 01 - release it first")

    def test_a_bone_the_other_weapon_drives_from_world(self):
        self.assertEqual(
            cx.blocked(scheme(right=H), scheme(left=H), scheme(),
                       "Dagger 01", bone_taken="L"),
            "weapon_l is driven by the Dagger 01 (in world) - remove it or "
            "put it in a hand first")

    def test_what_already_stands_is_never_blocked(self):
        self.assertEqual(cx.blocked(scheme(right=H), scheme(right=H),
                                    scheme(left=H), "Dagger 01"), "")

    def test_the_free_hand_is_free(self):
        self.assertEqual(cx.blocked(scheme(right=H), scheme(right=F),
                                    scheme(left=H), "Dagger 01"), "")

    def test_the_chooser_row_has_two_segments(self):
        fake = FakeMenuCmds()
        real = (cx.cmds, cx.refresh)
        cx.cmds, cx.refresh = fake, (lambda *a: "")
        try:
            cx.hubstyle.take_marks()
            cx.build_panel()
            cx.hubstyle.take_marks()
        finally:
            cx.cmds, cx.refresh = real
        names = [n for n, _l in fake.segments[cx.CHOOSER]]
        self.assertEqual(names, [cx.chooser_segment(0), cx.chooser_segment(1)])

    def test_the_header_names_the_other_weapon(self):
        import maya_rigs
        rig = maya_rigs.Rig("Manny_Rig", "cs", "|G|Main", "|G", "|root")
        text = cx.header_text(rig, "|a|LongSwordMesh", scheme(right=H),
                              "Dagger 01 in the left hand")
        self.assertIn("also Dagger 01 in the left hand", text)
