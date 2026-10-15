"""The radial menu's Maya half without Maya (2026-10-15): the slots in their optionVar, the catalog a
slot chooses from, what a chosen item does, the Finish popup's trigger."""

import unittest

try:
    import maya.cmds  # noqa: F401
    HAVE_MAYA = True
except ImportError:
    HAVE_MAYA = False

if HAVE_MAYA:
    import maya_radial
    import maya_radial_rules as rules


class FakeCmds(object):
    def __init__(self):
        self.vars = {}
        self.messages = []

    def optionVar(self, exists=None, query=None, stringValue=None, **_kw):
        if exists is not None:
            return exists in self.vars
        if query is not None:
            return self.vars.get(query, 0)
        if stringValue is not None:
            self.vars[stringValue[0]] = stringValue[1]

    def inViewMessage(self, assistMessage=None, **_kw):
        self.messages.append(assistMessage)

    def button(self, *_a, **_kw):
        return False

    def text(self, *_a, **_kw):
        return False


@unittest.skipUnless(HAVE_MAYA, "needs maya.cmds importable")
class RadialTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeCmds()
        self.saved = maya_radial.cmds
        maya_radial.cmds = self.fake
        self.calls = []

    def tearDown(self):
        maya_radial.cmds = self.saved

    def test_no_var_is_the_defaults(self):
        self.assertEqual(maya_radial.slots(), rules.DEFAULTS)

    def test_set_slot_keeps_the_others(self):
        maya_radial.set_slot(2, "section:studio")
        items = maya_radial.slots()
        self.assertEqual(items[2], "section:studio")
        self.assertEqual(items[0], rules.DEFAULTS[0])
        maya_radial.set_slot(2, "")
        self.assertEqual(maya_radial.slots()[2], "")

    def test_functions_leave_openers_and_the_menu_out(self):
        keys = [key for _cat, rows in maya_radial.functions() for key, _l in rows]
        self.assertIn("tools.aim", keys)
        self.assertFalse([k for k in keys if k.startswith(("window.", "radial."))])
        categories = [cat for cat, _rows in maya_radial.functions()]
        self.assertIn("Tools", categories)
        self.assertEqual(len(categories), len(set(categories)))

    def test_sections_leave_the_menu_card_out(self):
        keys = [key for key, _l, _i in maya_radial.sections()]
        self.assertIn("tools", keys)
        self.assertNotIn("radial", keys)

    def test_labels(self):
        self.assertEqual(maya_radial.item_label("section:tools"), "Tools")
        self.assertEqual(maya_radial.item_label("cmd:tools.aim"), "Aim")
        self.assertEqual(maya_radial.item_label(""), "")
        self.assertEqual(maya_radial.item_icon("section:tools"), "tool")
        self.assertEqual(maya_radial.item_icon("cmd:tools.aim"), "tool")
        self.assertIsNone(maya_radial.item_icon(""))

    def _patch(self, name, value):
        old = getattr(maya_radial, name)
        setattr(maya_radial, name, value)
        self.addCleanup(setattr, maya_radial, name, old)

    def test_a_section_opens_its_popup_at_the_point(self):
        import maya_hubpop
        old = maya_hubpop.open_at
        maya_hubpop.open_at = lambda key, point: self.calls.append((key, point)) or object()
        self.addCleanup(setattr, maya_hubpop, "open_at", old)
        maya_radial.run_item("section:tools", (300, 200))
        self.assertEqual(self.calls, [("tools", (300, 200))])

    def test_a_function_runs_its_row(self):
        import maya_hotkeys
        old = maya_hotkeys.run
        maya_hotkeys.run = lambda key: self.calls.append(key) or "done"
        self.addCleanup(setattr, maya_hotkeys, "run", old)
        self._patch("waiting", lambda key: False)
        self._patch("show_finish", lambda *a: self.calls.append(("finish",) + a))
        self.assertEqual(maya_radial.run_item("cmd:tools.knot", (0, 0)), "done")
        self.assertEqual(self.calls, ["tools.knot"])

    def test_a_two_step_left_waiting_gets_the_finish_popup(self):
        import maya_hotkeys
        old = maya_hotkeys.run
        maya_hotkeys.run = lambda key: "Aim: place the target"
        self.addCleanup(setattr, maya_hotkeys, "run", old)
        self._patch("waiting", lambda key: True)
        self._patch("show_finish", lambda *a: self.calls.append(a))
        maya_radial.run_item("cmd:tools.aim", (10, 20))
        self.assertEqual(self.calls, [("tools.aim", (10, 20), "Aim: place the target")])

    def test_a_two_step_that_finished_gets_none(self):
        import maya_hotkeys
        old = maya_hotkeys.run
        maya_hotkeys.run = lambda key: "aimed"
        self.addCleanup(setattr, maya_hotkeys, "run", old)
        self._patch("waiting", lambda key: False)
        self._patch("show_finish", lambda *a: self.calls.append(a))
        maya_radial.run_item("cmd:tools.aim", (10, 20))
        self.assertEqual(self.calls, [])

    def test_slot_text_reads_finish_while_waiting(self):
        self._patch("waiting", lambda key: key == "tools.aim")
        self.assertEqual(maya_radial.slot_text("cmd:tools.aim"), "Finish Aim")
        self.assertEqual(maya_radial.slot_text("cmd:tools.knot"), "Knot")

    def test_an_unknown_function_is_said(self):
        self.assertIn("set this slot again", maya_radial.run_item("cmd:nope.nope", (0, 0)))

    def test_two_step_rows_exist(self):
        import maya_hotkeys
        import importlib
        for key, (module, func, _label) in rules.TWO_STEP.items():
            self.assertIsNotNone(maya_hotkeys.row(key), key)
            self.assertTrue(hasattr(importlib.import_module(module), func), key)

    def test_hub_has_the_card(self):
        import maya_hub
        sec = maya_hub.section("radial")
        self.assertEqual(sec.module, "maya_radial")
        self.assertEqual(sec.group, "settings")


if __name__ == "__main__":
    unittest.main()
