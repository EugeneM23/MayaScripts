"""Connections: pick, then press (2026-10-29).

The animator: «нужно сделать консистентно что бы перепекание происходило по
нажатию кнопки а не по разному в каждом разделе». A press of a segment, a chip
or a parent menu records a pick and bakes NOTHING; the row's check, or the
tab's Apply all, is what bakes.

Spec: docs/superpowers/specs/2026-10-29-connections-pick-then-apply-design.md
"""

import unittest

from maya_scenesetup import connections as cx
from maya_scenesetup import pending

from tests.test_scenesetup_connections import FakeMenuCmds


class Rig(object):
    namespace = "Manny_Rig"


class LimbPicks(unittest.TestCase):
    """The Body tab: a press records, the row's check bakes."""

    def setUp(self):
        pending.clear()
        self.addCleanup(pending.clear)
        self.baked = []
        self.real = (cx.cmds, cx.refresh, cx.maya_rigs.current_rig,
                     cx.read_scheme, cx.switch_limb, cx.toggle_world,
                     cx._limb_modes)
        self.fake = FakeMenuCmds()
        cx.cmds = self.fake
        cx.refresh = lambda *a: ""
        cx.maya_rigs.current_rig = lambda: (Rig(), "")
        cx.read_scheme = lambda *a, **k: {"L": None, "R": None}
        #  the scene a press CHANGES: both arms and legs IK, none in world.
        #  A press that is refused leaves it as it was, so the settle rule (a
        #  pick that came true drops, a refused one stays) is testable.
        self.modes = {cx.fkik.ARM: {"R": "IK", "L": "IK"},
                      cx.fkik.LEG: {"R": "IK", "L": "IK"}}
        self.worlds = {cx.fkik.ARM: [], cx.fkik.LEG: []}
        self.refuse = set()

        def limb_modes(rig, kind, worlds=None):
            if worlds is not None:
                worlds.extend(self.worlds[kind])
            return dict(self.modes[kind])

        def switch(side, mode, rig=None, highlight=None, kind=cx.fkik.ARM,
                   world=False):
            self.baked.append(("switch", kind, side, mode, world))
            if (kind, side) in self.refuse:
                return "%s is retargeting" % cx.fkik.LABEL[kind].format(side)
            self.modes[kind][side] = mode
            if world and side not in self.worlds[kind]:
                self.worlds[kind].append(side)
            return "baked"

        def world_toggle(side, rig=None, highlight=None, kind=cx.fkik.ARM):
            self.baked.append(("world", kind, side))
            if side in self.worlds[kind]:
                self.worlds[kind].remove(side)
            else:
                self.worlds[kind].append(side)
                self.modes[kind][side] = cx.fkik.IK
            return "baked"

        cx._limb_modes = limb_modes
        cx.switch_limb = switch
        cx.toggle_world = world_toggle
        cx.hubstyle.take_marks()
        cx.build_panel()
        self.marks = dict((m.name, m) for m in cx.hubstyle.take_marks())

    def tearDown(self):
        (cx.cmds, cx.refresh, cx.maya_rigs.current_rig, cx.read_scheme,
         cx.switch_limb, cx.toggle_world, cx._limb_modes) = self.real

    def test_a_press_of_fk_bakes_nothing_and_records_the_pick(self):
        self.fake.press_box(cx.fkik_box("R", "FK"))
        self.assertEqual(self.baked, [])
        self.assertEqual(cx.picks(Rig()),
                         {pending.limb_key(cx.fkik.ARM, "R"): "FK"})

    def test_a_press_of_the_mode_it_already_is_records_nothing(self):
        self.fake.press_box(cx.fkik_box("R", "IK"))
        self.assertEqual(self.baked, [])
        self.assertEqual(cx.picks(Rig()), {})

    def test_the_row_s_check_bakes_that_limb_only(self):
        self.fake.press_box(cx.fkik_box("R", "FK"))
        self.fake.press_button(cx.LIMB_APPLY.format(cx.fkik.ARM, "R"))
        self.assertEqual(self.baked, [("switch", cx.fkik.ARM, "R", "FK", False)])
        self.assertEqual(cx.picks(Rig()), {})

    def test_the_w_chip_records_and_asks_for_ik(self):
        self.fake.press_check(cx.W_BOX.format(cx.fkik.ARM, "L"), True)
        self.assertEqual(self.baked, [])
        #  the arm IS IK, so only the world pick is a change
        self.assertEqual(cx.picks(Rig()),
                         {pending.world_key(cx.fkik.ARM, "L"): True})

    def test_the_check_of_a_limb_asked_into_world_toggles_it(self):
        self.fake.press_check(cx.W_BOX.format(cx.fkik.ARM, "L"), True)
        self.fake.press_button(cx.LIMB_APPLY.format(cx.fkik.ARM, "L"))
        self.assertEqual(self.baked, [("world", cx.fkik.ARM, "L")])
        self.assertEqual(cx.picks(Rig()), {})

    def test_a_limb_asked_to_ik_and_into_world_is_one_switch(self):
        self.modes[cx.fkik.ARM]["R"] = "FK"
        self.fake.press_check(cx.W_BOX.format(cx.fkik.ARM, "R"), True)
        self.assertEqual(cx.picks(Rig()),
                         {pending.world_key(cx.fkik.ARM, "R"): True,
                          pending.limb_key(cx.fkik.ARM, "R"): "IK"})
        self.fake.press_button(cx.LIMB_APPLY.format(cx.fkik.ARM, "R"))
        self.assertEqual(self.baked, [("switch", cx.fkik.ARM, "R", "IK", True)])
        self.assertEqual(cx.picks(Rig()), {})

    def test_picking_fk_drops_a_pending_w(self):
        self.fake.press_check(cx.W_BOX.format(cx.fkik.ARM, "R"), True)
        self.fake.press_box(cx.fkik_box("R", "FK"))
        self.assertEqual(cx.picks(Rig()),
                         {pending.limb_key(cx.fkik.ARM, "R"): "FK"})

    def test_the_legs_have_their_own_rows(self):
        self.fake.press_box(cx.fkik_box("L", "FK", cx.fkik.LEG))
        self.assertEqual(cx.picks(Rig()),
                         {pending.limb_key(cx.fkik.LEG, "L"): "FK"})
        self.fake.press_button(cx.LIMB_APPLY.format(cx.fkik.LEG, "L"))
        self.assertEqual(self.baked, [("switch", cx.fkik.LEG, "L", "FK", False)])

    def test_the_rows_are_one_limb_each_with_a_chip_and_a_check(self):
        self.assertEqual(self.marks[cx.W_BOX.format(cx.fkik.ARM, "R")].role,
                         "chip")
        self.assertEqual(self.marks[cx.LIMB_APPLY.format(cx.fkik.ARM, "R")].role,
                         "tool")
        boxes = [c[1][0] for c in self.fake.calls
                 if c[0] == "iconTextCheckBox" and not c[2].get("edit")]
        self.assertEqual(boxes[:4],
                         [cx.fkik_box("R", "FK"), cx.fkik_box("R", "IK"),
                          cx.fkik_box("L", "FK"), cx.fkik_box("L", "IK")])

    def test_no_w_among_the_segments(self):
        self.assertNotIn(cx.fkik_box("R", "W"), self.fake.boxes)

    def test_another_rig_s_picks_are_dropped(self):
        self.fake.press_box(cx.fkik_box("R", "FK"))
        other = Rig()
        other.namespace = "Creep_Rig"
        cx.maya_rigs.current_rig = lambda: (other, "")
        self.assertEqual(cx.picks(other), {})
        self.assertEqual(pending.for_rig("Manny_Rig"), {})

    def test_a_refused_press_keeps_its_pick(self):
        self.refuse.add((cx.fkik.ARM, "R"))
        self.fake.press_box(cx.fkik_box("R", "FK"))
        self.fake.press_button(cx.LIMB_APPLY.format(cx.fkik.ARM, "R"))
        self.assertEqual(self.baked, [("switch", cx.fkik.ARM, "R", "FK", False)])
        self.assertEqual(cx.picks(Rig()),
                         {pending.limb_key(cx.fkik.ARM, "R"): "FK"})

    def test_a_check_with_nothing_picked_bakes_nothing(self):
        self.fake.press_button(cx.LIMB_APPLY.format(cx.fkik.ARM, "R"))
        self.assertEqual(self.baked, [])
