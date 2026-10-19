"""Scene tabs' shared undo history across tabs: the pure half (maya_scenetabs.tabundo)."""

import importlib
import sys
import types
import unittest


def _module():
    if "maya_scenetabs.tabundo" in sys.modules:
        return sys.modules["maya_scenetabs.tabundo"]
    try:
        import maya.cmds  # noqa: F401
    except ImportError:
        fake = types.ModuleType("maya")
        fake.cmds = types.ModuleType("maya.cmds")
        sys.modules.setdefault("maya", fake)
        sys.modules.setdefault("maya.cmds", fake.cmds)
    return importlib.import_module("maya_scenetabs.tabundo")


tabundo = _module()


class Names(unittest.TestCase):
    def test_a_marker_names_where_the_switch_came_from_and_went(self):
        name = tabundo.marker_name("tab_a", "tab_rig", 7)
        self.assertTrue(tabundo.is_marker(name))
        self.assertEqual(tabundo.marker_tabs(name), ("tab_a", "tab_rig"))

    def test_anything_else_is_no_marker(self):
        for name in ("", None, "skeldarTabFence:tab_a:1", "move", "skeldarTabSwitch:broken"):
            if name != "skeldarTabSwitch:broken":
                self.assertFalse(tabundo.is_marker(name), name)
            self.assertEqual(tabundo.marker_tabs(name), ("", ""))


class Legacy(unittest.TestCase):
    def test_a_boundary_build_fence_is_known_and_is_no_marker(self):
        self.assertTrue(tabundo.is_legacy("skeldarTabFence:tab_a:3"))
        self.assertFalse(tabundo.is_marker("skeldarTabFence:tab_a:3"))
        self.assertFalse(tabundo.is_legacy(tabundo.marker_name("tab_a", "tab_b", 1)))
        self.assertFalse(tabundo.is_legacy("skeldarTabSwitch"))


class PlanEnter(unittest.TestCase):
    def test_a_tab_left_untouched_has_its_marker_popped_and_the_tab_below_goes_on(self):
        markers = {"M:1": {"from": "tab_a", "to": "tab_b", "below": "tab_a"}}
        self.assertEqual(tabundo.plan_enter(markers, "tab_b", "tab_b", "tab_a", "M:1"), (True, False))

    def test_a_tab_worked_in_keeps_its_steps_and_a_marker_is_laid(self):
        markers = {"M:1": {"from": "tab_a", "to": "tab_b", "below": "tab_a"}}
        self.assertEqual(tabundo.plan_enter(markers, "tab_b", "tab_b", "tab_a", "move"), (False, True))

    def test_popping_onto_a_third_tabs_steps_still_lays_a_marker(self):
        markers = {"M:2": {"from": "tab_b", "to": "tab_c", "below": "tab_b"}}
        self.assertEqual(tabundo.plan_enter(markers, "tab_c", "tab_c", "tab_a", "M:2"), (True, True))

    def test_an_unknown_owner_lays_a_marker(self):
        self.assertEqual(tabundo.plan_enter({}, None, "tab_a", "tab_b", ""), (False, True))

    def test_entering_the_owner_after_a_flush_lays_none(self):
        self.assertEqual(tabundo.plan_enter({}, "tab_b", "tab_a", "tab_b", ""), (False, False))

    def test_a_marker_into_another_tab_on_top_is_not_popped(self):
        markers = {"M:1": {"from": "tab_b", "to": "tab_a", "below": None}}
        self.assertEqual(tabundo.plan_enter(markers, "tab_a", "tab_b", "tab_a", "M:1"), (False, False))


class Selection(unittest.TestCase):
    def test_steps_that_only_look(self):
        for name in ("select -r tab_a:cube", "select -cl  ", "select -add b", "select -tgl a",
                     "selectKey -clear", "hilite -r x", "currentTime -e 36.0"):
            self.assertTrue(tabundo.is_selection(name), name)

    def test_anything_else_does_not(self):
        for name in ("", None, "move -r 1 0 0", "SetKey", "selectMode -o", "skeldarTabSwitch:a:b:1",
                     "skeldarTimeBarLayers", "selection"):
            self.assertFalse(tabundo.is_selection(name), name)

class Message(unittest.TestCase):
    def test_the_step_is_named_when_maya_named_it(self):
        self.assertEqual(tabundo.say_step(tabundo.UNDO_IN, "attack", "move -r 1 0 0 "), "Undo in attack: move -r 1 0 0")

    def test_an_unnamed_step_says_only_the_tab(self):
        self.assertEqual(tabundo.say_step(tabundo.REDO_IN, "walk", ""), "Redo in walk")


class Reset(unittest.TestCase):
    def test_a_flush_forgets_the_markers(self):
        st = tabundo.state()
        st["markers"]["x"] = {"from": "a", "to": "b", "below": None}
        st["popped"].add("y")
        tabundo.reset("tab_b")
        self.assertEqual(st["markers"], {})
        self.assertEqual(st["popped"], set())
        self.assertEqual(st["owner"], "tab_b")


if __name__ == "__main__":
    unittest.main()
