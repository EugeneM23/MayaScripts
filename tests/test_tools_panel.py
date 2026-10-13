"""maya_tools.panel: the hub's Tools card (2026-10-12) - its controls, the presses, the
remembered rotate order, the refresh; and its registration (hub row, icons, payload).

On the recording `cmds` (tests.uifakes) with a stub in place of `knots`: the scene half is
proven by docs/superpowers/plans/verify_knots.py in mayapy standalone.

Spec: docs/superpowers/specs/2026-10-12-tools-knots-design.md
"""

import unittest

import maya_hub
import maya_hubicons
import maya_hubstyle as hubstyle
from maya_tools import knotplan as plan
from maya_tools import overlapplan
from maya_tools import panel

from tests.uifakes import FakeUiCmds


class _Cmds(FakeUiCmds):
    """FakeUiCmds that remembers the labels of its texts and buttons."""

    def __init__(self):
        FakeUiCmds.__init__(self)
        self.labels = {}
        self.commands = {}
        self.radio = {}

    def _control(self, kind, args, kwargs):
        name = args[0] if args else None
        if kwargs.get("exists"):
            return name in self.labels
        if kwargs.get("query") or kwargs.get("q"):
            return self.labels.get(name)
        if kwargs.get("edit") or kwargs.get("e"):
            if "label" in kwargs:
                self.labels[name] = kwargs["label"]
            return name
        name = name or "%s%d" % (kind, len(self.children))
        self.calls.append((kind, (name,), kwargs))
        self.children.append(name)
        self.labels[name] = kwargs.get("label", "")
        if "command" in kwargs:
            self.commands[name] = kwargs["command"]
        return name

    def text(self, *args, **kwargs):
        return self._control("text", args, kwargs)

    def button(self, *args, **kwargs):
        return self._control("button", args, kwargs)

    def iconTextRadioButton(self, *args, **kwargs):
        name = args[0] if args else None
        if kwargs.get("exists") or kwargs.get("edit") or kwargs.get("query"):
            return FakeUiCmds.__getattr__(self, "iconTextRadioButton")(*args, **kwargs)
        self.radio[name] = kwargs
        return FakeUiCmds.__getattr__(self, "iconTextRadioButton")(*args, **kwargs)


class _Knots(object):
    """What the card asks of `knots`, recorded."""

    def __init__(self):
        self.calls = []
        self.waiting_now = False
        self.count = 2
        self.pivot_count = 0
        self.aim_count = 0
        self.fail = False

    def _say(self, *call):
        self.calls.append(call)
        if self.fail:
            raise RuntimeError("boom")
        return "did %s" % call[0]

    def create(self, kind, order=None):
        return self._say("create", kind, order)

    def begin_offset(self, order=None):
        return self._say("begin_offset", order)

    def finish_offset(self):
        return self._say("finish_offset")

    def bake(self):
        return self._say("bake")

    def remove(self):
        return self._say("remove")

    def waiting(self):
        return self.waiting_now

    def knots(self):
        return ["k"] * self.count

    def pivots(self):
        return ["p"] * self.pivot_count

    def aims_waiting(self):
        return ["a"] * self.aim_count

    def begin_aim(self, order=None):
        return self._say("begin_aim", order)

    def finish_aim(self):
        return self._say("finish_aim")

    def across(self, order=None):
        return self._say("across", order)

    def set_attach(self, value):
        return self._say("set_attach", value)

    def create_across(self, pairs, order=None, rotate=True, translate=True):
        return self._say("create_across", pairs, order, rotate, translate)

    selection = []

    def _selection(self, _selection):
        return list(self.selection)

    def _uuid(self, node):
        return "uuid:" + node


class _Reparent(object):

    def __init__(self, knots_stub):
        self.stub = knots_stub

    def inside(self):
        return self.stub._say("inside")

    def to_world(self):
        return self.stub._say("to_world")

    def swap(self):
        return self.stub._say("swap")


class _Overlapper(object):

    def __init__(self, knots_stub):
        self.stub = knots_stub

    def run(self, settings=None):
        return self.stub._say("overlap", settings)


class _LayerBake(object):

    def __init__(self, knots_stub):
        self.stub = knots_stub

    def bake(self):
        return self.stub._say("bake_layer")


class _Base(unittest.TestCase):

    def setUp(self):
        self.fake = _Cmds()
        self.stub = _Knots()
        self.saved = (panel.cmds, panel.knots, panel.reparent, panel.overlapper,
                      panel.layerbake)
        panel.cmds = self.fake
        panel.knots = self.stub
        panel.reparent = _Reparent(self.stub)
        panel.overlapper = _Overlapper(self.stub)
        panel.layerbake = _LayerBake(self.stub)
        panel.JOB.clear()
        import sys
        self.lists = getattr(sys, "_skeldar_tools_lists", None)
        sys._skeldar_tools_lists = {"objects": [], "targets": []}
        self.fake.ls = lambda *a, **k: ([a[0][len("uuid:"):]] if a and isinstance(a[0], str)
                                        and a[0].startswith("uuid:") else [])
        hubstyle.take_marks()

    def tearDown(self):
        (panel.cmds, panel.knots, panel.reparent, panel.overlapper,
         panel.layerbake) = self.saved
        panel.JOB.clear()
        import sys
        if self.lists is None:
            del sys._skeldar_tools_lists
        else:
            sys._skeldar_tools_lists = self.lists
        hubstyle.take_marks()


class Card(_Base):

    def test_the_controls_top_down(self):
        panel.build_panel()
        names = [n for n in self.fake.children if n.startswith("skeldarTools")]
        self.assertEqual(names, [
            panel.SUBTITLE, panel.KNOTS_HEADING, panel.KNOT_BTN, panel.OFFSET_BTN,
            panel.ORIENT_BTN, panel.DOUBLE_HEADING, panel.LOCAL_BTN, panel.WORLD_BTN,
            panel.PARENT_HEADING, panel.INSIDE_BTN, panel.TOWORLD_BTN, panel.SWAP_BTN,
            panel.ACROSS_BTN, panel.MULTI_HEADING, panel.OBJECTS_BTN, panel.TARGETS_BTN,
            panel.LISTSWAP_BTN, panel.ROTATE_CHIP, panel.TRANSLATE_CHIP, panel.MULTI_BTN,
            panel.AIM_HEADING, panel.AIM_BTN, panel.OVERLAP_HEADING, panel.SOFT_LABEL,
            panel.SOFT_FIELD, panel.LAG_LABEL, panel.LAG_FIELD, panel.EASE_LABEL,
            panel.EASE_FIELD, panel.HIER_CHIP, panel.CYCLE_CHIP, panel.TOTAL_CHIP,
            panel.EDGES_CHIP, panel.OVERLAP_BTN,
            panel.GAP, panel.ORDER_LABEL, panel.ORDER_SEG["object"], panel.ORDER_SEG["xyz"],
            panel.ORDER_SEG["xzy"], panel.ATTACH_LABEL, panel.ATTACH0_BTN, panel.ATTACH1_BTN,
            panel.BAKE_BTN, panel.LAYER_BTN, panel.REMOVE_BTN, panel.STATUS])

    def test_two_subsections_their_buttons_stretched(self):
        """2026-10-12, «два под раздела Knots и Double knots ... кнопочки ... растягивать
        вместе с интерфейсом»: two headings, and every row of buttons marked `fill` - the skin
        spreads its buttons over the card's width and they stretch with it."""
        panel.build_panel()
        marks = hubstyle.take_marks()
        roles = dict((m.name, m.role) for m in marks)
        for name in (panel.KNOTS_HEADING, panel.DOUBLE_HEADING, panel.PARENT_HEADING,
                     panel.MULTI_HEADING, panel.AIM_HEADING, panel.OVERLAP_HEADING):
            self.assertEqual(roles[name], "heading")
        self.assertEqual(self.fake.labels[panel.AIM_HEADING], "Aim")
        self.assertEqual(self.fake.labels[panel.OVERLAP_HEADING], "Overlap")
        self.assertEqual(self.fake.labels[panel.KNOTS_HEADING], "Knots")
        self.assertEqual(self.fake.labels[panel.DOUBLE_HEADING], "Double knot")
        self.assertEqual(self.fake.labels[panel.PARENT_HEADING], "Parent")
        self.assertEqual(self.fake.labels[panel.MULTI_HEADING], "Multiple across")
        fills = [m for m in marks if m.role == "fill"]
        self.assertEqual(len(fills), 11)
        self.assertTrue(all(m.layout for m in fills))
        made = [n for n in self.fake.children]
        rows = [made.index(m.name) for m in fills]
        buttons = [[made.index(b) for b in group] for group in (
            (panel.KNOT_BTN, panel.OFFSET_BTN, panel.ORIENT_BTN),
            (panel.LOCAL_BTN, panel.WORLD_BTN),
            (panel.INSIDE_BTN, panel.TOWORLD_BTN, panel.SWAP_BTN, panel.ACROSS_BTN),
            (panel.OBJECTS_BTN, panel.TARGETS_BTN, panel.LISTSWAP_BTN),
            (panel.ROTATE_CHIP, panel.TRANSLATE_CHIP, panel.MULTI_BTN),
            (panel.AIM_BTN,), (panel.HIER_CHIP, panel.CYCLE_CHIP),
            (panel.TOTAL_CHIP, panel.EDGES_CHIP), (panel.OVERLAP_BTN,),
            (panel.ATTACH0_BTN, panel.ATTACH1_BTN),
            (panel.BAKE_BTN, panel.LAYER_BTN, panel.REMOVE_BTN))]
        ends = rows[1:] + [len(made)]
        for row, end, group in zip(rows, ends, buttons):
            self.assertTrue(all(row < b < end for b in group), "the buttons are in their row")

    def test_the_rotate_order_label_is_shown(self):
        """The skin hides a `note` (it becomes the card header's tooltip) - the compact card's
        row names never showed. The rotate order's label carries no role: it stays visible."""
        panel.build_panel()
        roles = dict((m.name, m.role) for m in hubstyle.take_marks())
        self.assertNotIn(panel.ORDER_LABEL, roles)
        self.assertNotIn("note", roles.values())
        self.assertEqual(self.fake.labels[panel.ORDER_LABEL], "Rotate order")

    def test_the_short_words(self):
        panel.build_panel()
        self.assertEqual([self.fake.labels[n] for n in (
            panel.KNOT_BTN, panel.OFFSET_BTN, panel.ORIENT_BTN, panel.LOCAL_BTN,
            panel.WORLD_BTN, panel.BAKE_BTN, panel.LAYER_BTN, panel.REMOVE_BTN)],
            ["Knot", "Offset", "Orient", "Local", "World", "Bake", "Layer", "Remove"])
        self.assertEqual([self.fake.radio[panel.ORDER_SEG[c]]["label"] for c in plan.ORDERS],
                         ["Object", "XYZ", "XZY"])

    def test_the_roles(self):
        """«все кнопочки одинаково важные ... сделаем выделение для всех одинаковое»: every
        button orange, Remove too (it destroys nothing - it gives the animation back)."""
        panel.build_panel()
        roles = dict((m.name, m.role) for m in hubstyle.take_marks())
        buttons = (panel.KNOT_BTN, panel.OFFSET_BTN, panel.ORIENT_BTN, panel.LOCAL_BTN,
                   panel.WORLD_BTN, panel.INSIDE_BTN, panel.TOWORLD_BTN, panel.SWAP_BTN,
                   panel.ACROSS_BTN, panel.OBJECTS_BTN, panel.TARGETS_BTN, panel.LISTSWAP_BTN,
                   panel.MULTI_BTN, panel.ATTACH0_BTN, panel.ATTACH1_BTN, panel.BAKE_BTN,
                   panel.REMOVE_BTN, panel.AIM_BTN, panel.OVERLAP_BTN, panel.LAYER_BTN)
        self.assertEqual(sorted(n for n, r in roles.items() if r == "primary"), sorted(buttons))
        self.assertEqual(sorted(n for n, r in roles.items() if r == "chip"),
                         sorted((panel.ROTATE_CHIP, panel.TRANSLATE_CHIP, panel.HIER_CHIP,
                                 panel.CYCLE_CHIP, panel.TOTAL_CHIP, panel.EDGES_CHIP)))
        self.assertNotIn("danger", roles.values())
        self.assertEqual(roles[panel.STATUS], "status")
        self.assertEqual(roles[panel.SUBTITLE], "subtitle")
        self.assertEqual(sorted(n for n, r in roles.items() if r == "segment"),
                         sorted(panel.ORDER_SEG.values()))

    def test_every_icon_exists(self):
        panel.build_panel()
        for mark in hubstyle.take_marks():
            if mark.icon:
                self.assertIn(mark.icon, maya_hubicons.ICONS, mark.icon)

    def test_the_refresh_after_the_build(self):
        panel.build_panel()
        self.assertEqual(self.fake.labels[panel.SUBTITLE], "2 knots in the scene")
        self.assertEqual(self.fake.labels[panel.OFFSET_BTN], "Offset")

    def test_the_remembered_order_is_lit(self):
        self.fake.optionvars[panel.ORDER_VAR] = "xzy"
        panel.build_panel()
        self.assertTrue(self.fake.radio[panel.ORDER_SEG["xzy"]]["select"])
        self.assertFalse(self.fake.radio[panel.ORDER_SEG["object"]]["select"])

    def test_a_segment_remembers_its_order(self):
        panel.build_panel()
        self.fake.radio[panel.ORDER_SEG["xyz"]]["onCommand"]()
        self.assertEqual(self.fake.optionvars[panel.ORDER_VAR], "xyz")

    def test_the_buttons_press(self):
        panel.build_panel()
        self.fake.commands[panel.WORLD_BTN]()
        self.assertEqual(self.stub.calls[-1], ("create", "double_world", "object"))
        self.assertEqual(self.fake.labels[panel.STATUS], "did create")

    def test_a_refresh_job_per_card(self):
        panel.build_panel()
        jobs = [c for c in self.fake.calls if c[0] == "scriptJob" and c[2].get("event")]
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0][2]["parent"], panel.STATUS)


class Presses(_Base):

    def test_each_press_and_its_kind(self):
        panel.knot()
        panel.knot_orient()
        panel.double_local()
        panel.double_world()
        panel.bake()
        panel.remove()
        self.assertEqual(self.stub.calls, [
            ("create", "knot", "object"), ("create", "orient", "object"),
            ("create", "double_local", "object"), ("create", "double_world", "object"),
            ("bake",), ("remove",)])

    def test_the_offset_press_begins_or_finishes(self):
        panel.knot_offset()
        self.stub.waiting_now = True
        panel.knot_offset()
        self.assertEqual(self.stub.calls, [("begin_offset", "object"), ("finish_offset",)])

    def test_the_order_reaches_the_press(self):
        panel.set_order("xzy")
        panel.knot()
        self.assertEqual(self.stub.calls[-1], ("create", "knot", "xzy"))

    def test_a_bad_remembered_order_is_the_default(self):
        self.fake.optionvars[panel.ORDER_VAR] = "zyx"
        self.assertEqual(panel.order(), plan.ORDER_DEFAULT)
        self.assertEqual(panel.set_order("nope"), plan.ORDER_DEFAULT)

    def test_with_the_card_closed_a_press_answers_its_line(self):
        self.assertEqual(panel.knot(), "did create")
        self.assertNotIn(panel.STATUS, self.fake.labels)

    def test_a_failure_reaches_the_line(self):
        panel.build_panel()
        self.stub.fail = True
        line = panel.bake()
        self.assertEqual(line, "Tools failed: boom")
        self.assertEqual(self.fake.labels[panel.STATUS], line)

    def test_the_offset_button_reads_finish_while_a_pivot_waits(self):
        panel.build_panel()
        self.stub.pivot_count = 1
        self.stub.count = 0
        panel.refresh()
        self.assertEqual(self.fake.labels[panel.OFFSET_BTN], "Finish")
        self.assertEqual(self.fake.labels[panel.SUBTITLE], "1 pivot waiting")


class ParentTab(_Base):
    """The parent tab (2026-10-12): Inside, World, Swap, Across, Multiple across, Attach."""

    def test_the_parent_presses(self):
        panel.inside()
        panel.to_world()
        panel.swap()
        panel.across()
        panel.attach_0()
        panel.attach_1()
        self.assertEqual(self.stub.calls, [("inside",), ("to_world",), ("swap",),
                                           ("across", "object"), ("set_attach", 0.0),
                                           ("set_attach", 1.0)])

    def test_the_lists_remember_the_selection_and_swap(self):
        panel.build_panel()
        self.stub.selection = ["|a", "|b"]
        panel.remember_objects()
        self.assertEqual(self.fake.labels[panel.OBJECTS_BTN], "Objects 2")
        self.stub.selection = ["|t"]
        panel.remember_targets()
        self.assertEqual(self.fake.labels[panel.TARGETS_BTN], "Targets 1")
        panel.swap_lists()
        self.assertEqual(self.fake.labels[panel.OBJECTS_BTN], "Objects 1")
        self.assertEqual(self.fake.labels[panel.TARGETS_BTN], "Targets 2")

    def test_multiple_refuses_lists_of_different_lengths(self):
        panel.build_panel()
        self.stub.selection = ["|a", "|b"]
        panel.remember_objects()
        self.stub.selection = ["|t"]
        panel.remember_targets()
        line = panel.multiple_across()
        self.assertIn("must match", line)
        self.assertNotIn("create_across", [c[0] for c in self.stub.calls])

    def test_multiple_pairs_the_lists_with_the_chips(self):
        panel.build_panel()
        self.stub.selection = ["|a", "|b"]
        panel.remember_objects()
        self.stub.selection = ["|t1", "|t2"]
        panel.remember_targets()
        self.fake.optionvars[panel.ROTATE_VAR] = 0
        panel.multiple_across()
        self.assertEqual(self.stub.calls[-1],
                         ("create_across", [("|a", "|t1"), ("|b", "|t2")], "object", False, True))

    def test_the_chips_remember(self):
        panel.build_panel()
        command = [c for c in self.fake.calls if c[0] == "checkBox"
                   and c[1] and c[1][0] == panel.TRANSLATE_CHIP][0][2]["changeCommand"]
        command(False)
        self.assertEqual(self.fake.optionvars[panel.TRANSLATE_VAR], 0)


class AimOverlap(_Base):
    """The aim tab (2026-10-13): Aim (two presses) and Overlap (its remembered settings)."""

    def test_the_aim_press_begins_or_finishes(self):
        panel.aim()
        self.stub.aim_count = 1
        panel.aim()
        self.assertEqual(self.stub.calls, [("begin_aim", "object"), ("finish_aim",)])

    def test_the_aim_button_reads_finish_while_an_aim_waits(self):
        panel.build_panel()
        self.assertEqual(self.fake.labels[panel.AIM_BTN], "Aim")
        self.stub.aim_count = 1
        panel.refresh()
        self.assertEqual(self.fake.labels[panel.AIM_BTN], "Finish")
        self.assertEqual(self.fake.labels[panel.SUBTITLE], "2 knots in the scene, 1 aim waiting")
        self.assertEqual(self.fake.labels[panel.OFFSET_BTN], "Offset")

    def test_the_overlap_defaults(self):
        panel.overlap()
        self.assertEqual(self.stub.calls, [("overlap", overlapplan.DEFAULTS)])

    def test_the_overlap_reads_the_remembered_settings(self):
        self.fake.optionvars.update({panel.SOFT_VAR: 3.0, panel.LAG_VAR: 2.5,
                                     panel.EASE_VAR: 1.0, panel.HIER_VAR: 0,
                                     panel.CYCLE_VAR: 1, panel.TOTAL_VAR: 1,
                                     panel.EDGES_VAR: 1})
        panel.overlap()
        self.assertEqual(self.stub.calls[-1], ("overlap", overlapplan.Settings(
            softness=3.0, lag=2.5, easing=1.0, hierarchy=False, cycled=True, total=True,
            edges=True)))

    def test_the_fields_and_chips_remember(self):
        panel.build_panel()
        field = [c for c in self.fake.calls if c[0] == "floatField"
                 and c[1] and c[1][0] == panel.LAG_FIELD][0][2]
        self.assertEqual(field["value"], 1.0)
        field["changeCommand"](4.0)
        self.assertEqual(self.fake.optionvars[panel.LAG_VAR], 4.0)
        chips = dict((c[1][0], c[2]) for c in self.fake.calls if c[0] == "checkBox" and c[1])
        self.assertTrue(chips[panel.HIER_CHIP]["value"])
        self.assertFalse(chips[panel.CYCLE_CHIP]["value"])
        chips[panel.EDGES_CHIP]["changeCommand"](True)
        self.assertEqual(self.fake.optionvars[panel.EDGES_VAR], 1)

    def test_the_short_words(self):
        panel.build_panel()
        self.assertEqual([self.fake.labels[n] for n in (
            panel.SOFT_LABEL, panel.LAG_LABEL, panel.EASE_LABEL, panel.OVERLAP_BTN)],
            ["Softness", "Lag, fr", "Easing", "Overlap"])


class Layer(_Base):
    """Bake to a layer (2026-10-13): the third button of the bottom row."""

    def test_the_button_presses_layerbake(self):
        panel.build_panel()
        self.fake.commands[panel.LAYER_BTN]()
        self.assertEqual(self.stub.calls[-1], ("bake_layer",))
        self.assertEqual(self.fake.labels[panel.STATUS], "did bake_layer")

    def test_with_the_card_closed_it_answers_its_line(self):
        self.assertEqual(panel.bake_layer(), "did bake_layer")


class Registration(unittest.TestCase):

    def test_the_hub_row(self):
        sec = maya_hub.section("tools")
        self.assertEqual((sec.label, sec.module, sec.builder, sec.frame, sec.group, sec.icon),
                         ("Tools", "maya_tools.panel", "build_panel", "skeldarHubFrameTools",
                          "animation", "tool"))
        keys = [s.key for s in maya_hub.SECTIONS]
        self.assertEqual(keys.index("tools"), keys.index("poses") + 1)
        self.assertEqual(panel.HUB_SECTION, "tools")

    def test_the_new_icons(self):
        for name in ("tool", "rotate", "focus-2", "stack-2"):
            self.assertIn(name, maya_hubicons.ICONS)
            self.assertIn("<path", maya_hubicons.svg(name))

    def test_reparent_knows_our_prefixes(self):
        """reparent refuses the plugin's own nodes by deletion's prefixes - one list."""
        from maya_scenesetup import deletion
        from maya_tools import reparent
        self.assertEqual(reparent.OUR_PREFIXES, deletion.OUR_ATTR_PREFIXES)

    def test_the_package_ships(self):
        import install
        self.assertIn("maya_tools", install.payload())


if __name__ == "__main__":
    unittest.main()
