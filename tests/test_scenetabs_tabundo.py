"""Scene tabs' per-tab undo fences: the pure half (maya_scenetabs.tabundo)."""

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
    def test_a_fence_names_its_tab(self):
        name = tabundo.fence_name("tab_rig", 7)
        self.assertTrue(tabundo.is_fence(name))
        self.assertEqual(tabundo.fence_tab(name), "tab_rig")

    def test_anything_else_is_no_fence(self):
        for name in ("", None, "skeldarTabSwitch", "move"):
            self.assertFalse(tabundo.is_fence(name))
            self.assertEqual(tabundo.fence_tab(name), "")


class PlanEnter(unittest.TestCase):
    def test_a_tab_left_untouched_has_its_fence_popped_and_the_one_below_goes_on(self):
        fences = {"F:b:1": {"ns": "tab_b", "below": "tab_a"}}
        self.assertEqual(tabundo.plan_enter(fences, "tab_b", "tab_b", "tab_a", "F:b:1"), (True, False))

    def test_a_tab_worked_in_keeps_its_steps_and_the_new_tab_gets_a_fence(self):
        fences = {"F:b:1": {"ns": "tab_b", "below": "tab_a"}}
        self.assertEqual(tabundo.plan_enter(fences, "tab_b", "tab_b", "tab_a", ""), (False, True))

    def test_popping_onto_another_tabs_work_still_lays_a_fence(self):
        fences = {"F:c:2": {"ns": "tab_c", "below": "tab_b"}}
        self.assertEqual(tabundo.plan_enter(fences, "tab_c", "tab_c", "tab_a", "F:c:2"), (True, True))

    def test_an_unknown_owner_lays_a_fence(self):
        self.assertEqual(tabundo.plan_enter({}, None, "tab_a", "tab_b", ""), (False, True))

    def test_entering_the_owner_after_a_flush_lays_none(self):
        self.assertEqual(tabundo.plan_enter({}, "tab_b", "tab_a", "tab_b", ""), (False, False))

    def test_another_tabs_fence_on_top_is_not_popped(self):
        fences = {"F:a:1": {"ns": "tab_a", "below": None}}
        self.assertEqual(tabundo.plan_enter(fences, "tab_a", "tab_b", "tab_a", "F:a:1"), (False, False))


class Selection(unittest.TestCase):
    def test_mel_selection_steps_are_selection(self):
        for name in ("select -r tab_a:cube", "select -cl  ", "select -add b", "select -tgl a",
                     "selectKey -clear", "hilite -r x"):
            self.assertTrue(tabundo.is_selection(name), name)

    def test_anything_else_is_not(self):
        for name in ("", None, "move -r 1 0 0", "SetKey", "selectMode -o", "skeldarTabFence:tab_a:1",
                     "skeldarTimeBarLayers", "selection"):
            self.assertFalse(tabundo.is_selection(name), name)

    def test_the_latest_fence_of_a_tab(self):
        fences = {tabundo.fence_name("tab_a", 1): {"ns": "tab_a"}, tabundo.fence_name("tab_b", 2): {"ns": "tab_b"},
                  tabundo.fence_name("tab_a", 10): {"ns": "tab_a"}}
        self.assertEqual(tabundo.latest_fence(fences, "tab_a"), tabundo.fence_name("tab_a", 10))
        self.assertEqual(tabundo.latest_fence(fences, "tab_c"), "")


class Message(unittest.TestCase):
    def test_a_first_fence_is_the_start(self):
        fences = {tabundo.fence_name("tab_a", 1): {"ns": "tab_a", "below": None, "earlier": False}}
        self.assertEqual(tabundo.blocked_message(fences, tabundo.fence_name("tab_a", 1)), tabundo.START)

    def test_a_fence_over_the_tabs_own_earlier_work_says_it_is_under_another_tab(self):
        fences = {tabundo.fence_name("tab_a", 3): {"ns": "tab_a", "below": "tab_b", "earlier": True}}
        self.assertEqual(tabundo.blocked_message(fences, tabundo.fence_name("tab_a", 3)), tabundo.UNDER)

    def test_the_message_names_both_tabs_when_it_can(self):
        fences = {"F": {"ns": "tab_a", "below": "tab_b", "earlier": True}}
        text = tabundo.blocked_message(fences, "F", lambda ns: ns.upper())
        self.assertIn("TAB_A", text)
        self.assertIn("under the work done in TAB_B", text)

    def test_entering_says_whose_work_buried_the_history(self):
        record = {"ns": "tab_a", "below": "tab_b", "earlier": True}
        text = tabundo.entered_message(record, lambda ns: ns[4:])
        self.assertTrue(text.startswith("a: earlier undo steps are under the work done in b"), text)

    def test_entering_a_tab_for_the_first_time_says_nothing(self):
        self.assertEqual(tabundo.entered_message({"ns": "tab_a", "below": "tab_b", "earlier": False}, str), "")
        self.assertEqual(tabundo.entered_message(None, str), "")

    def test_an_unknown_fence_is_the_start(self):
        self.assertEqual(tabundo.blocked_message({}, tabundo.fence_name("tab_a", 9)), tabundo.START)


class Reset(unittest.TestCase):
    def test_a_flush_forgets_the_fences(self):
        st = tabundo.state()
        st["fences"]["x"] = {"ns": "a", "below": None}
        tabundo.reset("tab_b")
        self.assertEqual(st["fences"], {})
        self.assertEqual(st["owner"], "tab_b")


if __name__ == "__main__":
    unittest.main()
