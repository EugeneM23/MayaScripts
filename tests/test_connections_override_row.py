"""The Override row in the Weapon tab (2026-11-02): a chip, three numbers, a check.

A pick like every other (2026-10-29): the chip and the fields record, the section's
check or Apply all bakes. The numbers are part of the pick, so a knob turned while the
mode stands is a change to apply and one turned while it is off is not.

Spec: docs/superpowers/specs/2026-11-02-connections-2h-and-override-design.md
"""
import unittest

from maya_scenesetup import connections as con
from maya_scenesetup import pending
from maya_scenesetup import weaponoverride as wo

from tests.test_scenesetup_connections import FakeMenuCmds


import maya_rigs

#  a real Rig: `maya_rigs.node` reads anything else as a NAMESPACE STRING (trap 84),
#  and the Override press asks it for the rig's MoCapConstraints
RIG = maya_rigs.Rig("Manny_Rig", "Manny_Rig:ControlSet",
                    "|Manny_Rig:Group|Manny_Rig:Main", "|Manny_Rig:Group",
                    "|Manny_Rig:root")


class FakeOverrideCmds(FakeMenuCmds):
    """FakeMenuCmds plus float fields that remember their value: the shared fake
    answers a generic 1.0 for any `value` query, which cannot tell three knobs apart."""

    def __init__(self):
        FakeMenuCmds.__init__(self)
        self.fields = {}

    def floatField(self, name=None, **kwargs):
        self.calls.append(("floatField", (name,), kwargs))
        if kwargs.get("exists"):
            return name in self.fields
        if kwargs.get("query") or kwargs.get("q"):
            return self.fields[name]["value"]
        if kwargs.get("edit") or kwargs.get("e"):
            if "value" in kwargs:
                self.fields[name]["value"] = kwargs["value"]
            return name
        self.fields[name] = {"value": kwargs.get("value", 0.0),
                             "changeCommand": kwargs.get("changeCommand")}
        self.children.append(name)
        return name

    def type_number(self, name, value):
        """The animator types a number: the field takes it, then its changeCommand."""
        self.fields[name]["value"] = value
        command = self.fields[name]["changeCommand"]
        return command(value) if command else None


class TheRow(unittest.TestCase):
    def setUp(self):
        pending.clear()
        self.addCleanup(pending.clear)
        self.done = []
        self.real = (con.cmds, con.refresh, con.maya_rigs.current_rig,
                     con.read_scheme, con.apply, con.aim_mode, con._limb_modes,
                     con.weapon_of, con.weaponaim.is_aimed,
                     wo.state, wo.enter, wo.leave, wo.chest_of, wo.refusal)
        self.fake = FakeOverrideCmds()
        con.cmds = self.fake
        con.refresh = lambda *a: ""
        con.maya_rigs.current_rig = lambda selection=None: (RIG, "")
        con._limb_modes = lambda rig, kind, worlds=None: {}
        self.scheme = {"L": None, "R": con.HOLDS}
        con.read_scheme = lambda *a, **k: dict(self.scheme)
        con.weapon_of = lambda *a, **k: "LongSwordMesh"
        con.weaponaim.is_aimed = lambda weapon: False
        con.apply = lambda wanted, rig=None, weapon=None: "applied"
        con.aim_mode = lambda rig=None, weapon=None, on=True: "aimed"
        #  the mode's own state, and the two presses
        self.standing = None
        wo.state = lambda weapon: self.standing
        wo.chest_of = lambda rig: "|Manny_Rig:root|Manny_Rig:spine_03"
        wo.refusal = lambda weapon, chest: ""

        def enter(weapon, chest, settings):
            self.done.append(("enter", tuple(settings)))
            self.standing = settings
            return "entered"

        def leave(weapon):
            self.done.append(("leave",))
            self.standing = None
            return "left"

        wo.enter, wo.leave = enter, leave
        con.hubstyle.take_marks()
        con.build_panel()
        self.marks = dict((m.name, m) for m in con.hubstyle.take_marks())

    def tearDown(self):
        (con.cmds, con.refresh, con.maya_rigs.current_rig, con.read_scheme,
         con.apply, con.aim_mode, con._limb_modes, con.weapon_of,
         con.weaponaim.is_aimed, wo.state, wo.enter, wo.leave, wo.chest_of,
         wo.refusal) = self.real

    #  --- where it stands, and what it is

    def test_the_section_is_after_the_aim(self):
        order = self.fake.children
        self.assertLess(order.index(con.AIM_APPLY), order.index(con.OVERRIDE_CHIP))

    def test_the_names_stand_over_the_fields(self):
        order = self.fake.children
        self.assertLess(order.index(con.OVERRIDE_NAMES),
                        order.index(con.OVERRIDE_FIELD["rotation"]))

    def test_the_three_numbers_are_there_in_order(self):
        order = self.fake.children
        self.assertLess(order.index(con.OVERRIDE_FIELD["rotation"]),
                        order.index(con.OVERRIDE_FIELD["position"]))
        self.assertLess(order.index(con.OVERRIDE_FIELD["position"]),
                        order.index(con.OVERRIDE_FIELD["lag"]))

    def test_the_chip_is_a_chip_and_the_check_a_tool(self):
        self.assertEqual(self.marks[con.OVERRIDE_CHIP].role, "chip")
        self.assertEqual(self.marks[con.OVERRIDE_APPLY].role, "tool")

    def test_the_tab_s_one_orange_is_still_apply_all(self):
        oranges = [name for name, mark in self.marks.items() if mark.role == "primary"]
        self.assertIn(con.APPLY_ALL["weapon"], oranges)
        self.assertNotIn(con.OVERRIDE_CHIP, oranges)
        self.assertNotIn(con.OVERRIDE_APPLY, oranges)

    def test_the_fields_open_on_the_defaults(self):
        self.assertEqual(con.card_settings(), wo.DEFAULTS)

    #  --- the pick

    def test_ticking_the_chip_records_the_cards_numbers_and_bakes_nothing(self):
        self.fake.press_check(con.OVERRIDE_CHIP, True)
        self.assertEqual(self.done, [])
        self.assertEqual(con.picks(RIG),
                         {pending.OVERRIDE: (True,) + tuple(wo.DEFAULTS)})

    def test_a_number_typed_with_the_mode_off_is_no_pick(self):
        self.fake.type_number(con.OVERRIDE_FIELD["lag"], 160.0)
        self.assertEqual(con.picks(RIG), {})

    def test_a_number_typed_with_the_mode_on_is_a_pick(self):
        self.standing = wo.Settings(1.0, 1.0, 80.0)
        self.fake.type_number(con.OVERRIDE_FIELD["lag"], 160.0)
        self.assertEqual(con.picks(RIG), {pending.OVERRIDE: (True, 1.0, 1.0, 160.0)})

    def test_unticking_a_standing_mode_is_a_pick(self):
        self.standing = wo.Settings(1.0, 1.0, 80.0)
        self.fake.press_check(con.OVERRIDE_CHIP, False)
        picked = con.picks(RIG)[pending.OVERRIDE]
        self.assertFalse(picked[0])

    def test_ticking_what_already_stands_records_nothing(self):
        self.standing = wo.Settings(*wo.DEFAULTS)
        self.fake.press_check(con.OVERRIDE_CHIP, True)
        self.assertEqual(con.picks(RIG), {})

    #  --- the press

    def test_the_sections_check_enters_with_the_picked_numbers(self):
        self.fake.type_number(con.OVERRIDE_FIELD["lag"], 120.0)
        self.fake.press_check(con.OVERRIDE_CHIP, True)
        self.fake.press_button(con.OVERRIDE_APPLY)
        self.assertEqual(self.done, [("enter", (1.0, 1.0, 120.0))])
        self.assertEqual(con.picks(RIG), {})

    def test_the_sections_check_leaves_when_that_is_the_pick(self):
        self.standing = wo.Settings(1.0, 1.0, 80.0)
        self.fake.press_check(con.OVERRIDE_CHIP, False)
        self.fake.press_button(con.OVERRIDE_APPLY)
        self.assertEqual(self.done, [("leave",)])
        self.assertEqual(con.picks(RIG), {})

    def test_the_check_with_nothing_picked_says_so(self):
        self.assertEqual(self.fake.press_button(con.OVERRIDE_APPLY), con.NOTHING_PICKED)
        self.assertEqual(self.done, [])

    def test_apply_all_takes_the_override_after_the_parents_and_the_aim(self):
        self.fake.pick("L", con.WEAPON)
        self.fake.pick_aim(con.AIM_ON)
        self.fake.press_check(con.OVERRIDE_CHIP, True)
        self.fake.press_button(con.APPLY_ALL["weapon"])
        self.assertEqual([step[0] for step in self.done], ["enter"])

    def test_apply_all_counts_the_override_as_one_change(self):
        self.fake.press_check(con.OVERRIDE_CHIP, True)
        self.assertEqual(pending.count(pending.of_tab(con.picks(RIG), "weapon")), 1)

    #  --- the painting

    def test_the_chip_is_lit_by_the_scene(self):
        self.standing = wo.Settings(0.5, 1.0, 40.0)
        con._set_override(self.standing, {})
        self.assertTrue(self.fake.checks[con.OVERRIDE_CHIP]["value"])
        con._set_override(None, {})
        self.assertFalse(self.fake.checks[con.OVERRIDE_CHIP]["value"])

    def test_the_fields_show_the_standing_numbers(self):
        con._set_override(wo.Settings(0.25, 0.5, 200.0), {})
        self.assertEqual(con.card_settings(), wo.Settings(0.25, 0.5, 200.0))

    def test_the_fields_are_left_alone_with_the_mode_off(self):
        self.fake.type_number(con.OVERRIDE_FIELD["lag"], 33.0)
        con._set_override(None, {})
        self.assertEqual(con.card_settings().lag, 33.0)


class AimAndOverrideExcludeEachOther(unittest.TestCase):
    """Both write the weapon's rotation, so each refuses while the other stands."""

    def setUp(self):
        self.real = (con.cmds, con.maya_rigs.current_rig, con.weapon_of,
                     con.weaponaim.is_aimed, con.weaponaim.enter, wo.is_overridden,
                     con.bones_of)
        self.fake = FakeOverrideCmds()
        con.cmds = self.fake
        con.maya_rigs.current_rig = lambda selection=None: (RIG, "")
        #  `aim_mode` reads the weapon bones before it looks at the weapon it was
        #  given; `skeleton`/`naming` hold their own `cmds`, not this fake
        con.bones_of = lambda rig, bones=None: {"R": ("|hand_r", "|weapon_r"),
                                                "L": ("|hand_l", "|weapon_l")}
        con.weapon_of = lambda *a, **k: "|LongSwordMesh"
        con.weaponaim.is_aimed = lambda weapon: False
        con.weaponaim.enter = lambda weapon: "aimed"
        wo.is_overridden = lambda weapon: True

    def tearDown(self):
        (con.cmds, con.maya_rigs.current_rig, con.weapon_of,
         con.weaponaim.is_aimed, con.weaponaim.enter, wo.is_overridden,
         con.bones_of) = self.real

    def test_aim_mode_refuses_while_override_stands(self):
        text = con.aim_mode(rig=RIG, weapon="|LongSwordMesh", on=True)
        self.assertIn("Override", text)

    def test_default_is_still_allowed(self):
        #  leaving the aim writes the rotation back - that is how a scene with both
        #  (an older build, or a hand edit) is untangled
        con.weaponaim.leave = lambda weapon: "left"
        self.addCleanup(lambda: setattr(con.weaponaim, "leave", self.real[4]))
        self.assertNotIn("Override", con.aim_mode(rig=RIG, weapon="|LongSwordMesh",
                                                  on=False))
