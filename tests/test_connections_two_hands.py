"""2H Weapon (2026-11-02): one chip binds both hands to the weapon.

«намертво» means the hand FOLLOWS the weapon - the animator's own words in place of
the options offered - with today's proxy road kept («Прокси, одной кнопкой»). So the
chip is a shortcut for the two hand rows' picks and nothing else: no new state in the
scene, no new bake path, no new refusal.

Spec: docs/superpowers/specs/2026-11-02-connections-2h-and-override-design.md
"""
import unittest

from maya_scenesetup import connections as con
from maya_scenesetup import pending

from tests.test_scenesetup_connections import FakeMenuCmds


class TwoHandsState(unittest.TestCase):
    """The chip's LIT state is the scene's (the pick/press rule: a thumb is the state,
    a pick is an outline). A hand that HOLDS the weapon counts as bound: it travels
    with the weapon by construction."""

    def test_both_following_is_2h(self):
        self.assertTrue(con.two_hands_state({"R": con.FOLLOWS, "L": con.FOLLOWS}))

    def test_one_holding_and_one_following_is_2h(self):
        self.assertTrue(con.two_hands_state({"R": con.HOLDS, "L": con.FOLLOWS}))
        self.assertTrue(con.two_hands_state({"R": con.FOLLOWS, "L": con.HOLDS}))

    def test_a_free_hand_is_not(self):
        self.assertFalse(con.two_hands_state({"R": con.HOLDS, "L": None}))
        self.assertFalse(con.two_hands_state({"R": None, "L": con.FOLLOWS}))
        self.assertFalse(con.two_hands_state({"R": None, "L": None}))

    def test_an_empty_scheme_is_not(self):
        self.assertFalse(con.two_hands_state({}))


class TwoHandsPicks(unittest.TestCase):
    def test_in_world_both_hands_go_on_it(self):
        self.assertEqual(con.two_hands_picks({"R": None, "L": None}, True),
                         {"R": con.WEAPON, "L": con.WEAPON})

    def test_a_holding_hand_is_left_holding(self):
        #  it travels with the weapon already, and releasing it would move the weapon
        #  out of the hand - which the animator ruled out
        self.assertEqual(con.two_hands_picks({"R": con.HOLDS, "L": None}, True),
                         {"L": con.WEAPON})

    def test_the_other_hand_goes_on_it_beside_a_follower(self):
        self.assertEqual(con.two_hands_picks({"R": con.FOLLOWS, "L": None}, True),
                         {"L": con.WEAPON})

    def test_nothing_to_ask_when_both_are_bound(self):
        self.assertEqual(con.two_hands_picks({"R": con.HOLDS, "L": con.FOLLOWS}, True), {})
        self.assertEqual(con.two_hands_picks({"R": con.FOLLOWS, "L": con.FOLLOWS}, True), {})

    def test_unticking_frees_the_followers_only(self):
        self.assertEqual(con.two_hands_picks({"R": con.HOLDS, "L": con.FOLLOWS}, False),
                         {"L": con.FREE})

    def test_unticking_frees_both_followers(self):
        self.assertEqual(con.two_hands_picks({"R": con.FOLLOWS, "L": con.FOLLOWS}, False),
                         {"R": con.FREE, "L": con.FREE})

    def test_unticking_with_nothing_following_asks_nothing(self):
        self.assertEqual(con.two_hands_picks({"R": con.HOLDS, "L": None}, False), {})

    def test_the_weapon_row_is_never_touched(self):
        #  2H never moves the weapon: «оружие остаётся там, где стоит»
        for on in (True, False):
            for scheme in ({"R": con.HOLDS, "L": None}, {"R": None, "L": con.FOLLOWS},
                           {"R": None, "L": None},
                           {"R": con.FOLLOWS, "L": con.FOLLOWS}):
                self.assertNotIn("W", con.two_hands_picks(scheme, on))


class TwoHandsRoundTrip(unittest.TestCase):
    """What the chip asks for, applied, reads back as the chip being lit."""

    def test_ticking_leads_to_the_lit_state(self):
        for scheme in ({"R": None, "L": None}, {"R": con.HOLDS, "L": None},
                       {"R": None, "L": con.FOLLOWS}):
            after = dict(scheme)
            for side, choice in con.two_hands_picks(scheme, True).items():
                after = con.wanted_for_row(after, side, choice)
            self.assertTrue(con.two_hands_state(after), scheme)

    def test_unticking_leads_away_from_it(self):
        for scheme in ({"R": con.FOLLOWS, "L": con.FOLLOWS},
                       {"R": con.HOLDS, "L": con.FOLLOWS}):
            after = dict(scheme)
            for side, choice in con.two_hands_picks(scheme, False).items():
                after = con.wanted_for_row(after, side, choice)
            self.assertFalse(con.two_hands_state(after), scheme)
            #  and a holding hand still holds
            if con.master(scheme):
                self.assertEqual(con.master(after), con.master(scheme))


class Rig(object):
    namespace = "Manny_Rig"


class TheChip(unittest.TestCase):
    """The chip in the card: it records the hand rows' picks and bakes nothing. The
    fixture is the pick/press suite's own (`FakeMenuCmds`)."""

    def setUp(self):
        pending.clear()
        self.addCleanup(pending.clear)
        self.done = []
        self.real = (con.cmds, con.refresh, con.maya_rigs.current_rig,
                     con.read_scheme, con.apply, con.aim_mode, con._limb_modes,
                     con.weapon_of, con.weaponaim.is_aimed)
        self.fake = FakeMenuCmds()
        con.cmds = self.fake
        con.refresh = lambda *a: ""
        con.maya_rigs.current_rig = lambda selection=None: (Rig(), "")
        con._limb_modes = lambda rig, kind, worlds=None: {}
        #  the scene: the weapon in the right hand, the left hand free
        self.scheme = {"L": None, "R": con.HOLDS}
        con.read_scheme = lambda *a, **k: dict(self.scheme)
        con.weapon_of = lambda *a, **k: "LongSwordMesh"
        con.weaponaim.is_aimed = lambda weapon: False

        def apply_scheme(wanted, rig=None, weapon=None):
            self.done.append(("apply", wanted))
            self.scheme = dict(wanted)
            return "applied"

        con.apply = apply_scheme
        con.aim_mode = lambda rig=None, weapon=None, on=True: "aimed"
        con.hubstyle.take_marks()
        con.build_panel()
        self.marks = dict((m.name, m) for m in con.hubstyle.take_marks())

    def tearDown(self):
        (con.cmds, con.refresh, con.maya_rigs.current_rig, con.read_scheme,
         con.apply, con.aim_mode, con._limb_modes, con.weapon_of,
         con.weaponaim.is_aimed) = self.real

    def test_it_is_a_chip(self):
        self.assertEqual(self.marks[con.TWO_HANDS_CHIP].role, "chip")

    def test_it_stands_under_the_three_rows_and_over_apply_all(self):
        order = self.fake.children
        self.assertLess(order.index(con.ROW_APPLY.format("W")),
                        order.index(con.TWO_HANDS_CHIP))
        self.assertLess(order.index(con.TWO_HANDS_CHIP),
                        order.index(con.APPLY_ALL["weapon"]))

    def test_the_tab_s_one_orange_is_still_apply_all(self):
        oranges = [name for name, mark in self.marks.items() if mark.role == "primary"]
        self.assertIn(con.APPLY_ALL["weapon"], oranges)
        self.assertNotIn(con.TWO_HANDS_CHIP, oranges)

    def test_ticking_it_records_the_free_hand_only_and_bakes_nothing(self):
        self.fake.press_check(con.TWO_HANDS_CHIP, True)
        self.assertEqual(self.done, [])
        self.assertEqual(con.picks(Rig()), {pending.parent_key("L"): con.WEAPON})

    def test_the_rows_show_the_pick_while_the_scene_keeps_its_own(self):
        self.fake.press_check(con.TWO_HANDS_CHIP, True)
        self.assertEqual(con.menus()["L"], con.FREE)
        self.assertEqual(con.wanted_menus(Rig())["L"], con.WEAPON)

    def test_unticking_drops_the_pick_it_made(self):
        self.fake.press_check(con.TWO_HANDS_CHIP, True)
        self.fake.press_check(con.TWO_HANDS_CHIP, False)
        self.assertEqual(con.picks(Rig()), {})
        self.assertEqual(self.done, [])

    def test_ticking_a_scene_that_is_already_2h_records_nothing(self):
        self.scheme = {"L": con.FOLLOWS, "R": con.HOLDS}
        con.refresh = self.real[1]
        self.fake.press_check(con.TWO_HANDS_CHIP, True)
        self.assertEqual(con.picks(Rig()), {})

    def test_unticking_a_2h_scene_frees_the_follower_and_not_the_holder(self):
        self.scheme = {"L": con.FOLLOWS, "R": con.HOLDS}
        self.fake.press_check(con.TWO_HANDS_CHIP, False)
        self.assertEqual(con.picks(Rig()), {pending.parent_key("L"): con.FREE})

    def test_apply_all_bakes_what_the_chip_picked(self):
        self.fake.press_check(con.TWO_HANDS_CHIP, True)
        self.fake.press_button(con.APPLY_ALL["weapon"])
        self.assertEqual(self.done, [("apply", {"L": con.FOLLOWS, "R": con.HOLDS})])
        self.assertEqual(con.picks(Rig()), {})

    def test_it_is_lit_by_the_scene_and_wants_by_the_pick(self):
        #  the scene is not 2H, so the chip is off and nothing wants
        con.refresh = self.real[1]
        con._set_menus(con.menus_from_scheme(self.scheme), {})
        self.assertFalse(self.fake.checks[con.TWO_HANDS_CHIP]["value"])
        #  with the pick on top it shows ticked
        con._set_menus(con.menus_from_scheme(self.scheme),
                       {pending.parent_key("L"): con.WEAPON})
        self.assertTrue(self.fake.checks[con.TWO_HANDS_CHIP]["value"])

    def test_a_2h_scene_lights_it_with_no_pick(self):
        con._set_menus(con.menus_from_scheme({"L": con.FOLLOWS, "R": con.HOLDS}), {})
        self.assertTrue(self.fake.checks[con.TWO_HANDS_CHIP]["value"])
