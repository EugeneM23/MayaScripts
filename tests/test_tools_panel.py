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
        self.layouts = {}

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

    def columnLayout(self, *args, **kwargs):
        """Named columns (the subsections' bodies, the footer) are remembered with their
        `manage`; the card's own column stays FakeUiCmds'."""
        name = args[0] if args else None
        if name is None or (name not in self.layouts and not kwargs.get("exists")
                            and (kwargs.get("query") or kwargs.get("edit"))):
            return FakeUiCmds.columnLayout(self, *args, **kwargs)
        if kwargs.get("exists"):
            return name in self.layouts
        if kwargs.get("query"):
            return self.layouts[name].get("manage", True)
        if kwargs.get("edit"):
            self.layouts[name].update((k, v) for k, v in kwargs.items() if k != "edit")
            return name
        self.calls.append(("columnLayout", args, kwargs))
        self.children.append(name)
        self.layouts[name] = dict(kwargs)
        return name


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
        self.saved_light = panel._light
        self.lit = []
        panel._light = lambda name, state: self.lit.append((name, state))
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
        panel._light = self.saved_light
        panel.JOB.clear()
        import sys
        if self.lists is None:
            del sys._skeldar_tools_lists
        else:
            sys._skeldar_tools_lists = self.lists
        hubstyle.take_marks()


class Card(_Base):

    def test_the_controls_top_down(self):
        """2026-10-13, mockup C: the subtitle; Knots, Parent and Overlap, each a head over its
        body; «Selected knots»; the line."""
        panel.build_panel()
        names = [n for n in self.fake.children if n.startswith("skeldarTools")]
        self.assertEqual(names, [
            panel.SUBTITLE,
            panel.HEAD["knots"], panel.BODY["knots"], panel.KNOT_BTN, panel.OFFSET_BTN,
            panel.ORIENT_BTN, panel.LOCAL_BTN, panel.WORLD_BTN, panel.AIM_BTN,
            panel.ORDER_LABEL, panel.ORDER_SEG["object"], panel.ORDER_SEG["xyz"],
            panel.ORDER_SEG["xzy"],
            panel.HEAD["parent"], panel.BODY["parent"], panel.INSIDE_BTN, panel.TOWORLD_BTN,
            panel.SWAP_BTN, panel.ACROSS_BTN, panel.PAIRS_CAPTION, panel.OBJECTS_BTN,
            panel.TARGETS_BTN, panel.LISTSWAP_BTN, panel.ROTATE_CHIP, panel.TRANSLATE_CHIP,
            panel.MULTI_BTN,
            panel.HEAD["overlap"], panel.BODY["overlap"], panel.OVERLAP_NAMES, panel.SOFT_LABEL,
            panel.LAG_LABEL, panel.EASE_LABEL, panel.OVERLAP_FIELDS, panel.SOFT_FIELD,
            panel.LAG_FIELD, panel.EASE_FIELD, panel.HIER_CHIP, panel.CYCLE_CHIP,
            panel.TOTAL_CHIP, panel.EDGES_CHIP, panel.OVERLAP_BTN,
            panel.FOOTER, panel.FOOTER_CAPTION, panel.ATTACH0_BTN, panel.ATTACH1_BTN,
            panel.BAKE_BTN, panel.LAYER_BTN, panel.REMOVE_BTN, panel.STATUS])

    def test_every_tool_is_a_row_with_its_explanation(self):
        panel.build_panel()
        marks = dict((m.name, m) for m in hubstyle.take_marks())
        rows = (panel.KNOT_BTN, panel.OFFSET_BTN, panel.ORIENT_BTN, panel.LOCAL_BTN,
                panel.WORLD_BTN, panel.AIM_BTN, panel.INSIDE_BTN, panel.TOWORLD_BTN,
                panel.SWAP_BTN, panel.ACROSS_BTN, panel.OVERLAP_BTN)
        self.assertEqual(sorted(n for n, m in marks.items() if m.role == "toolrow"),
                         sorted(rows))
        for name in rows:
            self.assertTrue(marks[name].hint, name)
            self.assertEqual(marks[name].hint, panel.HINTS[name])
            self.assertLessEqual(len(marks[name].hint), 28, name)    # ~290 px of card

    def test_nothing_is_orange_but_a_waiting_row(self):
        """«Все кнопки не должны быть такими оранжевыми»: no primary control at all - only a row
        that reads Finish is lit (the skin's `wait`); the footer outlined, Remove the danger red."""
        panel.build_panel()
        roles = dict((m.name, m.role) for m in hubstyle.take_marks())
        self.assertNotIn("primary", roles.values())
        self.assertEqual(sorted(n for n, r in roles.items() if r == "secondary"),
                         sorted((panel.OBJECTS_BTN, panel.TARGETS_BTN, panel.LISTSWAP_BTN,
                                 panel.MULTI_BTN, panel.ATTACH0_BTN, panel.ATTACH1_BTN,
                                 panel.BAKE_BTN, panel.LAYER_BTN)))
        self.assertEqual(roles[panel.REMOVE_BTN], "danger")
        self.assertEqual(roles[panel.FOOTER], "inset")
        self.assertEqual(sorted(n for n, r in roles.items() if r == "chip"),
                         sorted((panel.ROTATE_CHIP, panel.TRANSLATE_CHIP, panel.HIER_CHIP,
                                 panel.CYCLE_CHIP, panel.TOTAL_CHIP, panel.EDGES_CHIP)))
        self.assertEqual(roles[panel.STATUS], "status")
        self.assertEqual(roles[panel.SUBTITLE], "subtitle")
        self.assertEqual(sorted(n for n, r in roles.items() if r == "segment"),
                         sorted(panel.ORDER_SEG.values()))
        self.assertEqual(sorted(n for n, r in roles.items() if r == "caption"),
                         sorted((panel.PAIRS_CAPTION, panel.FOOTER_CAPTION, panel.SOFT_LABEL,
                                 panel.LAG_LABEL, panel.EASE_LABEL)))
        self.assertEqual(sorted(n for n, r in roles.items() if r == "columns"),
                         sorted((panel.OVERLAP_NAMES, panel.OVERLAP_FIELDS)))
        self.assertNotIn("note", roles.values())        # the skin hides a note (trap 226)
        self.assertNotIn("heading", roles.values())

    def test_the_heads(self):
        panel.build_panel()
        marks = dict((m.name, m) for m in hubstyle.take_marks())
        for key, label, hint in panel.SECTIONS:
            self.assertEqual(marks[panel.HEAD[key]].role, "subhead")
            self.assertEqual(marks[panel.HEAD[key]].hint, hint)
            self.assertEqual(self.fake.labels[panel.HEAD[key]], label)
        self.assertEqual([k for k, _, _ in panel.SECTIONS], ["knots", "parent", "overlap"])

    def test_the_rotate_order_label_is_shown(self):
        """The skin hides a `note` (it becomes the card header's tooltip) - the compact card's
        row names never showed. The rotate order's label carries no role: it stays visible."""
        panel.build_panel()
        roles = dict((m.name, m.role) for m in hubstyle.take_marks())
        self.assertNotIn(panel.ORDER_LABEL, roles)
        self.assertEqual(self.fake.labels[panel.ORDER_LABEL], "Rotate order")

    def test_the_short_words(self):
        panel.build_panel()
        self.assertEqual([self.fake.labels[n] for n in (
            panel.KNOT_BTN, panel.OFFSET_BTN, panel.ORIENT_BTN, panel.LOCAL_BTN,
            panel.WORLD_BTN, panel.AIM_BTN, panel.INSIDE_BTN, panel.TOWORLD_BTN,
            panel.SWAP_BTN, panel.ACROSS_BTN, panel.MULTI_BTN, panel.ATTACH0_BTN,
            panel.ATTACH1_BTN, panel.BAKE_BTN, panel.LAYER_BTN)],
            ["Knot", "Offset", "Orient", "Local ×2", "World ×2", "Aim", "Inside",
             "To world", "Swap", "Across", "Pairs", "0", "1", "Bake", "Layer"])
        self.assertEqual(self.fake.labels[panel.FOOTER_CAPTION], "Selected knots")
        self.assertEqual(self.fake.labels[panel.PAIRS_CAPTION], "Across, pair by pair")
        self.assertEqual([self.fake.radio[panel.ORDER_SEG[c]]["label"] for c in plan.ORDERS],
                         ["Object", "XYZ", "XZY"])

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


class Sections(_Base):
    """2026-10-13: each subsection's head opens and closes its body, remembered - Knots open,
    Parent and Overlap closed at first - and a row that reads Finish is lit."""

    def test_the_defaults(self):
        panel.build_panel()
        self.assertTrue(self.fake.layouts[panel.BODY["knots"]]["manage"])
        self.assertFalse(self.fake.layouts[panel.BODY["parent"]]["manage"])
        self.assertFalse(self.fake.layouts[panel.BODY["overlap"]]["manage"])
        self.assertIn((panel.HEAD["knots"], "open"), self.lit)
        self.assertIn((panel.HEAD["parent"], "closed"), self.lit)

    def test_a_head_s_press_flips_its_body_and_remembers(self):
        panel.build_panel()
        self.fake.commands[panel.HEAD["parent"]]()
        self.assertTrue(self.fake.layouts[panel.BODY["parent"]]["manage"])
        self.assertEqual(self.fake.optionvars[panel.OPEN_VAR % "parent"], 1)
        self.assertEqual(self.lit[-1], (panel.HEAD["parent"], "open"))
        self.fake.commands[panel.HEAD["parent"]]()
        self.assertFalse(self.fake.layouts[panel.BODY["parent"]]["manage"])
        self.assertEqual(self.fake.optionvars[panel.OPEN_VAR % "parent"], 0)
        self.assertEqual(self.lit[-1], (panel.HEAD["parent"], "closed"))

    def test_the_memory_builds_the_card(self):
        self.fake.optionvars[panel.OPEN_VAR % "knots"] = 0
        self.fake.optionvars[panel.OPEN_VAR % "overlap"] = 1
        panel.build_panel()
        self.assertFalse(self.fake.layouts[panel.BODY["knots"]]["manage"])
        self.assertTrue(self.fake.layouts[panel.BODY["overlap"]]["manage"])
        self.assertTrue(panel.is_section_open("overlap"))

    def test_a_toggle_asks_its_own_body(self):
        """The hub's card and a popup copy share the memory, not their state: a press flips what
        THIS card shows, whatever the memory says."""
        panel.build_panel()
        self.fake.optionvars[panel.OPEN_VAR % "parent"] = 1   # another card opened it
        self.assertTrue(panel.toggle_section("parent"))       # this one was closed: opens
        self.assertTrue(self.fake.layouts[panel.BODY["parent"]]["manage"])

    def test_with_the_card_closed_a_toggle_is_the_memory(self):
        self.assertTrue(panel.toggle_section("overlap"))
        self.assertEqual(self.fake.optionvars[panel.OPEN_VAR % "overlap"], 1)

    def test_a_waiting_row_is_lit_and_put_out(self):
        panel.build_panel()
        self.assertIn((panel.OFFSET_BTN, ""), self.lit)
        self.assertIn((panel.AIM_BTN, ""), self.lit)
        self.stub.pivot_count = 1
        panel.refresh()
        self.assertIn((panel.OFFSET_BTN, "wait"), self.lit)
        self.assertEqual(self.fake.labels[panel.OFFSET_BTN], "Finish")
        self.stub.pivot_count = 0
        self.stub.aim_count = 1
        del self.lit[:]
        panel.refresh()
        self.assertEqual(sorted(self.lit), sorted([(panel.OFFSET_BTN, ""),
                                                   (panel.AIM_BTN, "wait")]))

    def test_the_seam_is_quiet_without_maya_s_ui(self):
        """`_light` reaches Qt only where the skin can stand; here (no Maya UI) it does nothing
        and raises nothing."""
        self.saved_light(panel.OFFSET_BTN, "wait")


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
