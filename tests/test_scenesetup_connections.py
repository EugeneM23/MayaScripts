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
import types
import unittest

import maya_hub
import maya_hubcopy as hubcopy
import maya_hubstyle as style
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
        self.checks = {}            # chip (cmds.checkBox) -> value, command
        self.commands = {}          # button name -> its command
        self.buttons = {}           # button name -> its kwargs, last edit last
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

    def checkBox(self, name=None, **kwargs):
        """A chip (2026-10-29, the limb rows' W): a value and a changeCommand."""
        self.calls.append(("checkBox", (name,) if name else (), kwargs))
        if kwargs.get("exists"):
            return name in self.checks
        if kwargs.get("query") or kwargs.get("q"):
            return self.checks[name]["value"]
        if kwargs.get("edit") or kwargs.get("e"):
            if "value" in kwargs:
                self.checks[name]["value"] = kwargs["value"]
            return name
        self.checks[name] = {"value": kwargs.get("value", False),
                             "changeCommand": kwargs.get("changeCommand"),
                             "label": kwargs.get("label")}
        self.children.append(name)
        return name

    def button(self, name=None, **kwargs):
        """A button: its command, and the label its press reads back."""
        self.calls.append(("button", (name,) if name else (), kwargs))
        if kwargs.get("exists"):
            return name in self.commands
        if kwargs.get("query") or kwargs.get("q"):
            return self.buttons.get(name, {}).get("label")
        if kwargs.get("edit") or kwargs.get("e"):
            self.buttons.setdefault(name, {}).update(
                (k, v) for k, v in kwargs.items() if k not in ("edit", "e"))
            return name
        label = name if name else "button%d" % len(self.children)
        self.commands[label] = kwargs.get("command")
        self.buttons[label] = dict(kwargs)
        self.children.append(label)
        return label

    def press_box(self, name):
        """The animator clicks a box: it toggles, then its command runs."""
        box = self.boxes[name]
        box["value"] = not box["value"]
        return (box["on"] if box["value"] else box["off"])()

    def press_check(self, name, value):
        """The animator clicks a chip: its value, then its changeCommand."""
        box = self.checks[name]
        box["value"] = value
        command = box["changeCommand"]
        return command(value) if command else None

    def press_button(self, name):
        """The animator presses a button by its control name."""
        command = self.commands.get(name)
        return command(False) if command else None

    def label_of(self, name):
        """A button's label as it stands - its last edit, else its creation."""
        return self.buttons.get(name, {}).get("label")

    def pick(self, row, choice):
        """The animator presses a segment: selected, then its onCommand."""
        name = cx.segment_name(row, choice)
        self.selected[cx.MENU[row]] = name
        self.on[name]()

    def pick_aim(self, choice):
        """The aim row's segment pressed (2026-10-29)."""
        name = cx.AIM_SEGMENT.format(choice)
        self.selected[cx.AIM_MENU] = name
        self.on[name]()

    def pick_camera(self, choice):
        """The camera tab's parent segment pressed."""
        name = cx.camera_segment(choice)
        self.selected[cx.CAMERA_MENU] = name
        self.on[name]()

    def pick_camera_aim(self, choice):
        name = cx.CAMERA_AIM_SEGMENT.format(choice)
        self.selected[cx.CAMERA_AIM_MENU] = name
        self.on[name]()

    def value(self, row):
        return cx.menus()[row]


class PanelRig(object):
    """The rig every press reads since 2026-10-29 (a pick belongs to one)."""
    namespace = "Manny_Rig"


class Panel(unittest.TestCase):

    def setUp(self):
        self.real = (cx.cmds, cx.refresh, cx.maya_rigs.current_rig,
                     cx.read_scheme, cx._limb_modes, cx._spine_state)
        self.fake = FakeMenuCmds()
        cx.cmds = self.fake
        cx.refresh = lambda *a: ""
        #  the presses and the painters read the rig and what it shows
        #  (2026-10-29): without Maya those readers are stubs here
        cx.maya_rigs.current_rig = lambda selection=None: (PanelRig(), "")
        cx._limb_modes = lambda rig, kind, worlds=None: {"R": "IK", "L": "IK"}
        cx._spine_state = lambda rig: ("FK", False)
        cx.read_scheme = lambda *a, **k: {"L": None, "R": None}
        cx.pending.clear()
        self.addCleanup(cx.pending.clear)
        cx.hubstyle.take_marks()
        cx.build_panel()
        self.marks = dict((m.name, m) for m in cx.hubstyle.take_marks())

    def tearDown(self):
        (cx.cmds, cx.refresh, cx.maya_rigs.current_rig,
         cx.read_scheme, cx._limb_modes, cx._spine_state) = self.real

    def _buttons(self):
        return [c for c in self.fake.calls if c[0] == "button"
                and not c[2].get("edit")]

    def test_three_rows_each_with_segments_and_apply_then_apply_all(self):
        labels_of = lambda row: [label for _n, label in
                                 self.fake.segments[cx.MENU[row]]]
        self.assertEqual(labels_of("R"), ["Free", "Weapon"])
        self.assertEqual(labels_of("L"), ["Free", "Weapon"])
        self.assertEqual(labels_of("W"), ["World", "Hand R", "Hand L"])
        #  2026-10-21: [Body | Weapon] - the body tab first, then the weapon
        #  tab's rows, Apply all and Aim Mode / Default.
        #  2026-10-29: a check a limb row ahead of BakeAcross / Release
        self.assertEqual([c[2]["label"] for c in self._buttons()],
                         ["Apply", "Apply", "Apply", "Apply", "Apply",
                          "Apply all",
                          "Apply", "Apply", "Apply", "Apply all", "Apply",
                          "Apply", "Apply", "Apply all",
                          "BakeAcross", "Release"])
        labels = [c[2].get("label") for c in self.fake.calls
                  if c[0] == "text" and not c[2].get("edit")]
        for wanted in ("Hand R", "Hand L", "Weapon"):
            self.assertIn(wanted, labels)
        #  no description paragraph (the animator: Â«Ð²ÐµÑÑŒ Ñ‚ÐµÐºÑÑ‚ Ð¾Ð¿Ð¸ÑÐ°Ð½Ð¸Ñ
        #  ÑƒÐ±Ð¸Ñ€Ð°ÐµÐ¼Â») - the header, the two FK/IK rows (2026-09-30), the
        #  chooser's label (2026-09-29), the three row labels and the status
        self.assertIn("Acts on", labels)
        #  (2026-10-08: both arms on one row, written "Arm R" / "Arm L")
        #  (2026-10-16: under the caption «FK / IK»)
        self.assertEqual(labels[1:4], ["FK / IK", "Arm R", "Arm L"])
        #  + the legs' two labels and the spine (2026-10-10), the three
        #  captions (2026-10-16)
        self.assertEqual(len(labels), 19)          # + the camera tab's two captions (2026-10-28); + the caption «Aim» (2026-10-21); + the two aim rows' labels (2026-10-29)

    def test_every_row_starts_on_its_first_choice(self):
        self.assertEqual(cx.menus(), {"R": "Free", "L": "Free", "W": "World"})

    def test_the_segments_are_marked_for_the_skin(self):
        for row, choices in cx._ROWS:
            for choice in choices:
                self.assertEqual(self.marks[cx.segment_name(row, choice)].role,
                                 "segment")
        segment_rows = [m for m in self.marks.values()
                        if m.role == "segments"]
        #  the chooser, the three parents, the tabs, the camera, four limbs,
        #  the spine and the weapon aim (2026-10-29)
        self.assertEqual(len(segment_rows), 13)
        for side in ("R", "L"):
            for mode in ("FK", "IK"):
                self.assertEqual(self.marks[cx.fkik_box(side, mode)].role, "segment")
        self.assertTrue(all(m.layout for m in segment_rows))
        #  the scene's state line is the card's subtitle (2026-10-08)
        self.assertEqual(self.marks[cx.HEADER].role, "subtitle")
        self.assertEqual(self.marks[cx.STATUS].role, "status")
        roles = [(m.role, m.icon) for m in self.marks.values()
                 if m.role in ("primary", "tool", "secondary")]
        #  the three parent rows + the camera tab's Apply (2026-10-28)
        #  + a check a limb row, the spine's and the two aims' (2026-10-29)
        self.assertEqual(roles.count(("tool", "check")), 11)
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
        by_label = dict((c[2]["label"], c[2]) for c in self._buttons())
        try:
            by_label["BakeAcross"]["command"]()
            by_label["Release"]["command"]()
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
        status = [c for c in self.fake.calls
                  if c[0] == "text" and c[1] == (cx.STATUS,) and c[2].get("edit")]
        self.assertIn("Hand_R set to Free", status[-1][2]["label"])
        #  2026-10-29: the pick waits for a button, and the status names it
        self.assertIn("the weapon to Hand R", status[-1][2]["label"])
        self.assertIn("Press the row's check, or Apply all",
                      status[-1][2]["label"])
        #  the fix is a pick of its own, and the collections keep the scene
        self.assertEqual(cx.picks(PanelRig()),
                         {cx.pending.parent_key("W"): "Hand_R"})
        self.assertEqual(self.fake.value("R"), "Free")
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
            self.fake.press_button(cx.ROW_APPLY.format("L"))
        finally:
            cx.apply = saved_apply
        self.assertEqual(asked, [scheme(F, H)])

    def test_apply_all_takes_all_three_rows(self):
        asked = []
        saved_apply = cx.apply
        cx.apply = lambda wanted, rig=None: asked.append(wanted) or "done"
        try:
            #  2026-10-29: the rows are PICKED, then the tab's one button bakes
            self.fake.pick("R", cx.WEAPON)
            self.fake.pick("L", cx.WEAPON)
            self.fake.press_button(cx.APPLY_ALL["weapon"])
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
        """What the row's check reaches (2026-10-29: `switch_limb`, with the
        limb's W; `switch_arm` is its arm-only wrapper)."""
        asked = []
        saved = cx.switch_limb
        cx.switch_limb = lambda side, mode, rig=None, highlight=None, \
            kind=cx.fkik.ARM, world=False: \
            asked.append((side, mode, world)) or "switched"
        self.addCleanup(setattr, cx, "switch_limb", saved)
        return asked

    def test_fkik_rows_have_two_boxes_each(self):
        for side in ("R", "L"):
            self.assertEqual([self.fake.boxes[cx.fkik_box(side, m)]["label"]
                              for m in ("FK", "IK")], ["FK", "IK"])

    def test_a_box_records_and_the_row_s_check_switches(self):
        """2026-10-29: a press of a box is a PICK - the row's check bakes it.
        Either press of a box records, lighting it or un-lighting the lit one:
        a range inside a take already in that mode must still be pickable."""
        asked = self._stub_switch()
        self.fake.press_box(cx.fkik_box("L", "FK"))
        self.assertEqual(asked, [])
        self.fake.press_button(cx.LIMB_APPLY.format(cx.fkik.ARM, "L"))
        self.assertEqual(asked, [("L", "FK", False)])

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
        cx._set_fkik({"R": "IK", "L": None}, chosen={})
        value = lambda side, mode: self.fake.boxes[cx.fkik_box(side, mode)]["value"]
        self.assertEqual((value("R", "FK"), value("R", "IK")), (False, True))
        self.assertEqual((value("L", "FK"), value("L", "IK")), (False, False))
        self.assertEqual(asked, [])

    #  --- the compact arrangement (2026-10-08, variant B) ---

    def _made(self, kind, **match):
        """The creation calls (no edit/query/exists) of `kind` whose kwargs
        hold `match`, with their position in the fake's call list."""
        return [(i, c) for i, c in enumerate(self.fake.calls)
                if c[0] == kind and not (c[2].get("edit") or c[2].get("e")
                                         or c[2].get("query") or c[2].get("q")
                                         or c[2].get("exists"))
                and all(c[2].get(k) == v for k, v in match.items())]

    def _inside(self, start):
        """The calls between the layout created at `start` and the setParent
        that closes it (nested layouts included)."""
        depth, out = 1, []
        for call in self.fake.calls[start + 1:]:
            if call[0] == "rowLayout" and not (
                    call[2].get("edit") or call[2].get("exists")):
                depth += 1
            elif call[0] == "setParent" and call[1] == ("..",):
                depth -= 1
                if not depth:
                    return out
            out.append(call)
        return out

    def test_each_limb_has_a_row_of_its_own(self):
        """2026-10-29 («более удобного разсположения»): one limb a row - label,
        [FK | IK], the W chip, the row's check - so the segments are the width
        of the card and not the ~28 px two limbs in one row left them."""
        #  the tabs' row has four columns too since 2026-10-29: the limb rows
        #  are the ones that size them
        rows = [(i, c) for i, c in self._made("rowLayout", numberOfColumns=4)
                if "columnWidth4" in c[2]]
        #  two arms, two legs, then the spine's row of the same shape
        self.assertEqual(len(rows), 5)
        wanted = [("Arm R", cx.fkik.ARM, "R"), ("Arm L", cx.fkik.ARM, "L"),
                  ("Leg R", cx.fkik.LEG, "R"), ("Leg L", cx.fkik.LEG, "L")]
        for (index, call), (label, kind, side) in zip(rows, wanted):
            self.assertEqual(call[2]["adjustableColumn"], 2)
            inside = self._inside(index)
            self.assertEqual([c[2]["label"] for c in inside
                              if c[0] == "text"], [label])
            self.assertEqual([c[1][0] for c in inside
                              if c[0] == "iconTextCheckBox"],
                             [cx.fkik_box(side, mode, kind)
                              for mode in ("FK", "IK")])
            self.assertEqual([c[1][0] for c in inside if c[0] == "checkBox"],
                             [cx.W_BOX.format(kind, side)])
            self.assertEqual([c[1][0] for c in inside if c[0] == "button"],
                             [cx.LIMB_APPLY.format(kind, side)])

    def test_w_is_a_chip_and_no_longer_a_segment(self):
        for kind in (cx.fkik.ARM, cx.fkik.LEG):
            for side in ("R", "L"):
                self.assertIn(cx.W_BOX.format(kind, side), self.fake.checks)
                self.assertNotIn(cx.fkik_box(side, cx.W_MODE, kind),
                                 self.fake.boxes)

    def test_the_chooser_row_is_named_and_starts_hidden(self):
        rows = self._made("rowLayout", numberOfColumns=2, adjustableColumn=2)
        chooser = [(i, c) for i, c in rows if c[1] == (cx.CHOOSER_ROW,)]
        self.assertEqual(len(chooser), 1)
        index, call = chooser[0]
        self.assertIs(call[2]["manage"], False)
        self.assertEqual(call[2]["columnWidth2"], (64, 110))
        self.assertEqual([c[2]["label"] for c in self._inside(index)
                          if c[0] == "text"], ["Acts on"])

    def test_the_chooser_row_shows_only_for_two_weapons(self):
        fake = FakeUiCmds()
        saved = cx.cmds
        cx.cmds = fake
        try:
            cx._set_chooser(["|a"], "|a")
            cx._set_chooser(["|a", "|b"], "|a")
        finally:
            cx.cmds = saved
        manages = [c[2]["manage"] for c in fake.calls
                   if c[0] == "rowLayout" and c[1] and c[1][0] == cx.CHOOSER_ROW
                   and "manage" in c[2]]
        self.assertEqual(manages, [False, True])

    def test_no_weapon_hides_the_chooser_row_too(self):
        fake = FakeUiCmds()
        saved = cx.cmds
        cx.cmds = fake
        try:
            cx._set_chooser([], None)
        finally:
            cx.cmds = saved
        manages = [c[2]["manage"] for c in fake.calls
                   if c[0] == "rowLayout" and "manage" in c[2]]
        self.assertEqual(manages, [False])

    def test_apply_all_alone_bake_and_release_under_their_caption(self):
        """2026-10-16, the card rules: Apply all is the weapon section's
        orange, alone; BakeAcross and Release (any object) share a row under
        the caption «Any object»."""
        rows = self._made("rowLayout", numberOfColumns=2, adjustableColumn=1)
        inside = [[b[2]["label"] for b in self._inside(index)
                   if b[0] == "button"] for index, _call in rows]
        self.assertIn(["BakeAcross", "Release"], inside)
        self.assertFalse([labels for labels in inside if "Apply all" in labels])
        names = [c[1][0] for c in self.fake.calls if c[0] == "text" and c[1]]
        for key in ("limbs", "weapon", "any"):
            self.assertIn(cx.CAPTION[key], names)
            self.assertEqual(self.marks[cx.CAPTION[key]].role, "heading")
        order = [c[1][0] if c[1] else c[2].get("label")
                 for c in self.fake.calls if c[0] in ("text", "button")
                 and not c[2].get("edit")]
        self.assertLess(order.index(cx.CAPTION["any"]), order.index("BakeAcross"))
        #  and their marks stay what they were: a primary a tab (the body's
        #  Apply all since 2026-10-29), the aims, then the two secondaries
        roles = [(m.role, m.icon) for m in self.marks.values()
                 if m.role in ("primary", "secondary")]
        #  2026-10-29: both aims are rows, so their Aim Mode / Default buttons
        #  are gone - one primary a tab (its Apply all) and the two secondaries
        self.assertEqual(sorted(roles), [("primary", "check"), ("primary", "check"),
                                         ("primary", "check"),
                                         ("secondary", "link"),
                                         ("secondary", "unlink")])

    def test_the_status_tells_the_hub(self):
        heard = []
        listener = lambda control, text, viewport: heard.append((control, text))
        style.listen(listener)
        try:
            cx._status("linked")
        finally:
            style.unlisten(listener)
        self.assertIn((cx.STATUS, "linked"), heard)

    def test_the_status_of_a_card_that_is_not_open_tells_nothing(self):
        heard = []
        listener = lambda control, text, viewport: heard.append((control, text))
        saved = cx.cmds
        cx.cmds = FakeUiCmds()          # no control answers `exists`
        style.listen(listener)
        try:
            self.assertEqual(cx._status("linked"), "linked")
        finally:
            style.unlisten(listener)
            cx.cmds = saved
        self.assertEqual(heard, [])


class _ScopedCmds(object):
    """The fake with every command put through maya_hubcopy's wrapper, as
    `maya_hubcopy.install` does to maya.cmds (the fake's own `install` would
    miss the commands its __getattr__ answers)."""

    def __init__(self, fake):
        self._fake = fake

    def __getattr__(self, name):
        real = getattr(self._fake, name)
        if not callable(real):
            return real
        return hubcopy._command_wrapper(name, real)


class PopupCopy(unittest.TestCase):
    """The card's popup copy (2026-10-09) builds under prefixed names. 2026-10-13
    (the animator: «в режиме виджета не работает переключение рук на оружие и
    обратно ... статусы не обновляются при выделении персонажа»): a copy's rows
    read their first choice whatever was picked, and no card followed the
    selection."""

    def setUp(self):
        self.real = (cx.cmds, cx.refresh, dict(cx.JOB),
                     cx.maya_rigs.current_rig, cx.read_scheme,
                     cx._limb_modes, cx._spine_state)
        self.fake = FakeMenuCmds()
        cx.cmds = _ScopedCmds(self.fake)
        self.refreshed = []
        cx.refresh = lambda *a: self.refreshed.append(hubcopy.current()) or ""
        #  a pick reads the rig and what it shows (2026-10-29)
        cx.maya_rigs.current_rig = lambda selection=None: (PanelRig(), "")
        cx.read_scheme = lambda *a, **k: {"L": None, "R": None}
        cx._limb_modes = lambda rig, kind, worlds=None: {"R": "IK", "L": "IK"}
        cx._spine_state = lambda rig: ("FK", False)
        cx.pending.clear()
        self.addCleanup(cx.pending.clear)
        cx.JOB.clear()
        cx.build_panel()                                    # the hub's card
        self.scope = hubcopy.new_scope(section=cx.HUB_SECTION)
        with hubcopy.entered(self.scope):
            cx.build_panel()                                # the copy
        self.refreshed[:] = []

    def tearDown(self):
        hubcopy.close(self.scope, cmds=self.fake)
        cx.cmds, cx.refresh = self.real[0], self.real[1]
        cx.JOB.clear()
        cx.JOB.update(self.real[2])
        (cx.maya_rigs.current_rig, cx.read_scheme, cx._limb_modes,
         cx._spine_state) = self.real[3:]

    def _pick(self, row, choice, scope=None):
        """The animator presses a segment of the card `scope` (None: the hub's)."""
        name = cx.segment_name(row, choice)
        collection = cx.MENU[row]
        if scope is not None:
            name, collection = scope.resolve(name), scope.resolve(collection)
        self.fake.selected[collection] = name
        self.fake.on[name]()

    def _menus(self, scope=None):
        with hubcopy.entered(scope):
            return cx.menus()

    def test_the_copy_makes_its_own_segments(self):
        made = self.scope.resolve(cx.segment_name("R", "Weapon"))
        self.assertNotEqual(made, cx.segment_name("R", "Weapon"))
        self.assertIn(made, self.fake.owner)

    def test_a_copys_picks_are_read_back_in_it(self):
        """2026-10-29: a pick lives in `pending`, one set per RIG, and the
        collections keep showing the scene - so a pick made in the copy is read
        back by `wanted_menus` there AND in the hub's card (the two must not
        disagree about one rig), while the lit segments stay the scene's."""
        self._pick("R", "Weapon", self.scope)
        self._pick("W", "Hand_L", self.scope)
        rig = PanelRig()
        with hubcopy.entered(self.scope):
            self.assertEqual(cx.wanted_menus(rig),
                             {"R": "Weapon", "L": "Free", "W": "Hand_L"})
        self.assertEqual(cx.wanted_menus(rig),
                         {"R": "Weapon", "L": "Free", "W": "Hand_L"})
        self.assertEqual(self._menus(self.scope),
                         {"R": "Free", "L": "Free", "W": "World"})

    def test_a_copys_row_apply_asks_for_the_picked_parent(self):
        import maya_rigs
        rig = maya_rigs.Rig("Manny_Rig", "cs", "|G|Main", "|G", "|root")
        asked = []
        saved = (cx.maya_rigs.current_rig, cx.read_scheme, cx.apply)
        cx.maya_rigs.current_rig = lambda selection=None: (rig, "")
        cx.read_scheme = lambda rig, bones=None, weapon=None: scheme(right=H)
        cx.apply = lambda wanted, rig=None: asked.append(wanted) or "done"
        try:
            self._pick("L", "Weapon", self.scope)
            with hubcopy.entered(self.scope):
                cx._press_row("L")()
        finally:
            cx.maya_rigs.current_rig, cx.read_scheme, cx.apply = saved
        self.assertEqual(asked, [scheme(F, H)])

    def test_a_pick_in_the_copy_is_kept_and_said(self):
        self._pick("R", "Weapon", self.scope)
        self.assertEqual(cx.picks(PanelRig()),
                         {cx.pending.parent_key("R"): "Weapon"})
        status = [c for c in self.fake.calls if c[0] == "text"
                  and c[1] == (self.scope.resolve(cx.STATUS),) and c[2].get("edit")]
        self.assertIn("the right hand to Weapon", status[-1][2]["label"])

    def test_each_card_follows_the_selection(self):
        jobs = [c for c in self.fake.calls if c[0] == "scriptJob"
                and "SelectionChanged" in (c[2].get("event") or ())]
        self.assertEqual([c[2]["parent"] for c in jobs],
                         [cx.STATUS, self.scope.resolve(cx.STATUS)])
        for job, scope in zip(jobs, (None, self.scope)):
            self.refreshed[:] = []
            job[2]["event"][1]()
            self.assertEqual(self.refreshed, [scope])

    def test_a_press_in_the_copy_refreshes_the_hubs_card_too(self):
        saved = cx.apply
        cx.apply = lambda wanted, rig=None: "done"
        try:
            with hubcopy.entered(self.scope):
                cx._press_apply_all()
        finally:
            cx.apply = saved
        self.assertEqual(sorted(self.refreshed, key=lambda s: s is not None),
                         [None, self.scope])

    def test_a_refresh_selecting_a_segment_presses_nothing(self):
        """Even if Maya ran a segment's onCommand on an edit (trap 116): a refresh on
        every selection change must not write «press Apply for» over the status."""
        plain = FakeMenuCmds.iconTextRadioButton

        def edit_fires(fake, name=None, **kwargs):
            out = plain(fake, name, **kwargs)
            if kwargs.get("edit") and kwargs.get("select"):
                fake.on[name]()
            return out
        self.fake.iconTextRadioButton = lambda name=None, **kw: edit_fires(
            self.fake, name, **kw)
        before = len([c for c in self.fake.calls if c[0] == "text"
                      and c[1] == (cx.STATUS,) and c[2].get("edit")])
        cx._set_menus({"R": "Weapon", "W": "Hand_L"})
        after = len([c for c in self.fake.calls if c[0] == "text"
                     and c[1] == (cx.STATUS,) and c[2].get("edit")])
        self.assertEqual(after, before)
        self.assertEqual(self._menus(), {"R": "Weapon", "L": "Free", "W": "Hand_L"})


class PanelCompact(unittest.TestCase):
    """The same panel built for the skin and for the classic hub
    (2026-10-08): the skin's heights and gaps, the classic numbers kept."""

    def _build(self, skin):
        fake = FakeMenuCmds()
        real = (cx.cmds, cx.refresh)
        cx.cmds, cx.refresh = fake, (lambda *a: "")
        style.take_marks()
        style.set_skinning(skin)
        try:
            cx.build_panel()
        finally:
            style.set_skinning(False)
            cx.cmds, cx.refresh = real
        return fake, style.take_marks()

    @staticmethod
    def _by_label(fake, kind="button"):
        return dict((c[2]["label"], c[2]) for c in fake.calls
                    if c[0] == kind and "label" in c[2]
                    and not (c[2].get("edit") or c[2].get("e")))

    def test_the_skin_is_tight(self):
        fake, _marks = self._build(True)
        self.assertEqual(fake.column["rowSpacing"], 3)
        header = [c[2] for c in fake.calls
                  if c[0] == "text" and c[1] == (cx.HEADER,)][0]
        self.assertEqual((header["height"], header["wordWrap"]), (18, False))
        for kind in ("iconTextRadioButton", "iconTextCheckBox"):
            heights = [c[2]["height"] for c in fake.calls
                       if c[0] == kind and "height" in c[2]]
            self.assertTrue(heights)
            self.assertEqual(set(heights), {22}, kind)
        made = [c for c in fake.calls if c[0] == "button"
                and not (c[2].get("edit") or c[2].get("e"))]
        by_name = dict((c[1][0], c[2]) for c in made if c[1])
        by_label = dict((c[2]["label"], c[2]) for c in made if not c[1])
        bake, release = by_label["BakeAcross"], by_label["Release"]
        apply_all = by_name[cx.APPLY_ALL["weapon"]]
        apply_rows = [by_name[cx.ROW_APPLY.format(row)] for row, _ in cx._ROWS]
        apply_rows += [by_name[cx.LIMB_APPLY.format(kind, side)]
                       for kind in (cx.fkik.ARM, cx.fkik.LEG)
                       for side in ("R", "L")]
        for button in apply_rows:                  # icon only, small
            self.assertEqual((button["label"], button["width"],
                              button["height"]), ("", 30, 22))
        self.assertEqual(apply_all["height"], 24)
        self.assertEqual((bake["height"], release["height"]), (24, 24))
        self.assertEqual(release["width"], 78)

    def test_the_skin_narrows_the_label_column(self):
        fake, _marks = self._build(True)
        widths = [c[2]["columnWidth3"] for c in fake.calls
                  if c[0] == "rowLayout" and "columnWidth3" in c[2]]
        #  the three parent rows, the weapon aim and the camera aim (2026-10-29)
        self.assertEqual(widths, [(48, 110, 30)] * 5)
        chooser = [c[2] for c in fake.calls if c[0] == "rowLayout"
                   and c[1] == (cx.CHOOSER_ROW,)][0]
        self.assertEqual(chooser["columnWidth2"], (48, 110))

    def test_a_limb_s_row_gives_its_segments_the_card(self):
        """2026-10-08's shared row read 86 and 128 px for the two tracks (Maya's
        rowLayout has one adjustable column), and with W among the segments each
        was ~28 px. One limb a row since 2026-10-29: the label, the segments
        (adjustable), the W chip and the check, the segments taking the rest."""
        for skin, label, chip in ((True, 48, 28), (False, 64, 34)):
            fake, _marks = self._build(skin)
            rows = [c[2] for c in fake.calls if c[0] == "rowLayout"
                    and c[2].get("numberOfColumns") == 4
                    and "columnWidth4" in c[2]]
            #  four limbs and the spine, all of one shape
            self.assertEqual(len(rows), 5, skin)
            for row in rows:
                self.assertEqual(row["adjustableColumn"], 2, skin)
                self.assertEqual(row["columnWidth4"],
                                 (label, 110, chip, 30 if skin else 66), skin)

    def test_the_classic_hub_keeps_its_numbers(self):
        fake, _marks = self._build(False)
        self.assertEqual(fake.column["rowSpacing"], 6)
        header = [c[2] for c in fake.calls
                  if c[0] == "text" and c[1] == (cx.HEADER,)][0]
        self.assertEqual((header["height"], header["wordWrap"]), (36, True))
        by = self._by_label(fake)
        self.assertEqual(by["Apply"]["height"], 24)
        self.assertEqual(by["Apply"]["width"], 66)
        self.assertEqual(by["Apply all"]["height"], 32)
        self.assertEqual(by["BakeAcross"]["height"], 28)
        self.assertEqual(by["Release"]["width"], 90)
        widths = [c[2]["columnWidth3"] for c in fake.calls
                  if c[0] == "rowLayout" and "columnWidth3" in c[2]]
        self.assertEqual(widths, [(64, 110, 66)] * 5)

    def test_both_builds_keep_every_control_and_the_roles(self):
        for skin in (True, False):
            fake, marks = self._build(skin)
            by_name = dict((m.name, m) for m in marks)
            #  a layout is named, not marked
            self.assertTrue([c for c in fake.calls if c[0] == "rowLayout"
                             and c[1] == (cx.CHOOSER_ROW,)], skin)
            for name in (cx.HEADER, cx.STATUS, cx.chooser_segment(0),
                         cx.chooser_segment(1), cx.fkik_box("R", "FK"),
                         cx.fkik_box("L", "IK")):
                self.assertIn(name, fake.children, (skin, name))
            self.assertEqual(by_name[cx.HEADER].role, "subtitle", skin)
            self.assertEqual(by_name[cx.STATUS].role, "status", skin)


class SwitchArm(unittest.TestCase):
    """`switch_arm`'s order of things, on stubs: refusals before anything
    moves, a following hand released before FK, IK refused on it."""

    def setUp(self):
        import maya_rigs
        self.rig = maya_rigs.Rig("Manny_Rig", "cs", "|G|Main", "|G", "|root")
        self.done = []
        self.saved = dict((name, getattr(cx, name)) for name in
                          ("cmds", "_rig", "following", "_release", "_span",
                           "sweep_orphans", "_control", "weapon_label",
                           "release_refusal"))
        self.saved_fkik = dict((name, getattr(cx.fkik, name)) for name in
                               ("limb", "whole_take", "refusal", "switch",
                                "blend_values"))
        #  no world control on the limb (2026-10-28): the switch as it always was
        self.saved_world = cx.ikworld.limb_knot
        cx.ikworld.limb_knot = lambda arm: None

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
        cx.release_refusal = lambda obj: ""
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
        cx.ikworld.limb_knot = self.saved_world

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

    def test_fk_on_a_hand_its_layer_cannot_take_moves_nothing(self):
        """2026-10-21: the release keys the active layer; a layer that cannot
        take the keys refuses the press before the release or the switch."""
        cx.following = lambda rig, side: "|sword"
        cx.release_refusal = lambda obj: "the animation layer L is locked"
        text = cx.switch_arm("R", "FK", highlight=False)
        self.assertEqual(text, "the animation layer L is locked")
        self.assertEqual(self.done, [])

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

    def test_no_module_function_is_defined_twice(self):
        """A second `def` of a name silently replaces the first. On
        2026-10-13 the card's selection handler was named `_follow`, the
        name of the step that puts a hand on its proxy, and every Apply of
        a following hand ran a refresh instead - 'Applied: right hand
        follows' over a hand that followed nothing."""
        tree = ast.parse(self._source())
        names = [node.name for node in tree.body
                 if isinstance(node, (ast.FunctionDef, ast.ClassDef))]
        twice = sorted(set(n for n in names if names.count(n) > 1))
        self.assertEqual(twice, [])

    def test_the_follow_step_puts_the_hand_on_a_proxy(self):
        """`apply`'s follow step reaches `attach_to_proxy`."""
        calls = []
        saved = (cx.attach_to_proxy, cx._not_ik, cx._control, cx.maya_rigs.node)
        cx.attach_to_proxy = lambda *a: calls.append(a) or ("p", "c")
        cx._not_ik = lambda rig, side: None
        cx._control = lambda rig, side: "IKArm_" + side
        cx.maya_rigs.node = lambda rig, leaf: leaf
        try:
            rig = types.SimpleNamespace(namespace="ns")
            cx._follow(rig, "R", "|Sword", (0, 10))
        finally:
            (cx.attach_to_proxy, cx._not_ik, cx._control, cx.maya_rigs.node) = saved
        self.assertEqual([c[0] for c in calls], ["IKArm_R"])

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
        #  a bake goes through maya_timewarp.call(cmds.bakeResults, ...) (2026-10-20)
        names += [node.attr for node in ast.walk(tree)
                  if isinstance(node, ast.Attribute) and node.attr == "bakeResults"]
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
        """2026-09-24, Â«Ð½Ðµ Ð½Ð°Ñ€ÑƒÑˆÐ°Ð»Ð¸ Ð¸ÐµÑ€Ð°Ñ€Ñ…Ð¸ÑŽ Ð½Ð°ÑˆÐµÐ³Ð¾ ÑÐºÐµÐ»ÐµÑ‚Ð°Â»: a hold is the
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


class LayeredRelease(unittest.TestCase):
    """2026-10-21: a hand on an animation layer released from the dagger came
    off 33 cm away - `bakeResults` lands in the layers' blend node. A layered
    rider is read on every frame while it still rides, freed, and keyed onto
    the active layer as final values; a plain one is baked as before."""

    def setUp(self):
        self.done = []
        self.saved = (cx.cmds, cx.layered, cx.maya_timewarp, cx.our_constraints,
                      cx.proxy_for, cx._set_visible)
        test = self

        class Cmds(object):
            def objExists(self, name):
                return True

            def delete(self, name):
                test.done.append(("delete", name))

            def attributeQuery(self, *args, **kwargs):
                return False

            def bakeResults(self, *args, **kwargs):
                test.done.append(("bakeResults",))

        self.stacked = True
        self.layer = ("Upper", "")
        cx.cmds = Cmds()
        cx.maya_timewarp = types.SimpleNamespace(
            call=lambda fn, *a, **k: fn(*a, **k))
        cx.layered = types.SimpleNamespace(
            is_layered=lambda obj, *a: self.stacked,
            target=lambda: self.layer,
            check_target=lambda layer, channels: "",
            read=lambda objs, channels, frames: self.done.append(
                ("read", tuple(channels), list(frames))) or {objs[0]: {"shown": True}},
            key_shown=lambda obj, channels, first, last, shown, layer: self.done.append(
                ("key", obj, first, last, shown, layer)))
        cx.our_constraints = lambda obj: ["|IKArm_R|link"]
        cx.proxy_for = lambda con: "|sword|handProxy_R"
        cx._set_visible = lambda node, visible: self.done.append(("visible", visible))

    def tearDown(self):
        (cx.cmds, cx.layered, cx.maya_timewarp, cx.our_constraints,
         cx.proxy_for, cx._set_visible) = self.saved

    def test_a_layered_rider_is_read_freed_then_keyed_on_the_active_layer(self):
        removed = cx.detach_from_proxy("|IKArm_R", (0.0, 61.0))
        self.assertEqual(removed, 1)
        self.assertEqual([d[0] for d in self.done],
                         ["read", "delete", "delete", "key", "visible"])
        self.assertEqual(self.done[0][2], list(range(0, 62)))
        self.assertEqual(self.done[3], ("key", "|IKArm_R", 0, 61, {"shown": True}, "Upper"))
        self.assertNotIn(("bakeResults",), self.done)

    def test_a_plain_rider_is_baked_as_before(self):
        self.stacked = False
        cx.detach_from_proxy("|IKArm_R", (0.0, 61.0))
        self.assertEqual([d[0] for d in self.done],
                         ["bakeResults", "delete", "delete", "visible"])

    def test_a_hand_that_rides_nothing_is_left_alone(self):
        cx.our_constraints = lambda obj: []
        self.assertEqual(cx.detach_from_proxy("|IKArm_R", (0.0, 61.0)), 0)
        self.assertEqual(cx.release_refusal("|IKArm_R"), "")
        self.assertEqual(self.done, [])

    def test_the_release_refusal_is_the_active_layers(self):
        self.assertEqual(cx.release_refusal("|IKArm_R"), "")
        self.layer = (None, "the animation layer Upper is locked")
        self.assertEqual(cx.release_refusal("|IKArm_R"), "the animation layer Upper is locked")
        self.layer = ("Upper", "")
        cx.layered.check_target = lambda layer, channels: "adds rotation as quaternions"
        self.assertEqual(cx.release_refusal("|IKArm_R"), "adds rotation as quaternions")
        self.stacked = False
        self.assertEqual(cx.release_refusal("|IKArm_R"), "")
