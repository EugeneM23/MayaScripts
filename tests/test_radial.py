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

    def optionVar(self, exists=None, query=None, stringValue=None, intValue=None, **_kw):
        if exists is not None:
            return exists in self.vars
        if query is not None:
            return self.vars.get(query, 0)
        if stringValue is not None:
            self.vars[stringValue[0]] = stringValue[1]
        if intValue is not None:
            self.vars[intValue[0]] = intValue[1]

    def inViewMessage(self, assistMessage=None, **_kw):
        self.messages.append(assistMessage)

    def button(self, *_a, **_kw):
        return False

    def optionMenu(self, *_a, **_kw):
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
        self.assertEqual(maya_radial.slots()[:rules.SLOTS], rules.DEFAULTS)
        self.assertEqual(maya_radial.count(), 8)

    def test_count_remembered_and_clamped(self):
        self.assertEqual(maya_radial.set_count(5), 5)
        self.assertEqual(maya_radial.count(), 5)
        maya_radial.set_count(99)
        self.assertEqual(maya_radial.count(), rules.MAX_SLOTS)

    def test_reset_brings_eight_back(self):
        maya_radial.set_count(4)
        maya_radial.set_slot(9, "section:studio")
        maya_radial.reset_defaults()
        self.assertEqual(maya_radial.count(), 8)
        self.assertEqual(maya_radial.slots()[:8], rules.DEFAULTS)

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


@unittest.skipUnless(HAVE_MAYA, "needs maya.cmds importable")
class MotionTests(unittest.TestCase):
    """The menu's motion offscreen (2026-10-16): out of the centre, lit, flashed, back in."""

    def setUp(self):
        import os
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6 import QtWidgets
        self.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        import maya_hubqt
        self.q = maya_hubqt.qt()
        self.fake = FakeCmds()
        self.clock = [1000.0]
        self.ran = []
        for name, value in (("cmds", self.fake), ("waiting", lambda key: False),
                            ("animated", lambda: True), ("_now_ms", lambda: self.clock[0]),
                            ("_run_later", lambda q, item, point: self.ran.append(item))):
            old = getattr(maya_radial, name)
            setattr(maya_radial, name, value)
            self.addCleanup(setattr, maya_radial, name, old)
        state = maya_radial._state()
        saved = dict(state)
        self.addCleanup(lambda: (state.clear(), state.update(saved)))
        state["menu"] = state["leaving"] = None

    def _menu(self):
        menu = maya_radial.Menu(self.q)
        menu.centre = (300, 300)
        menu.origin = (0, 0)
        menu.cursor = lambda: (300, 300)
        menu.window = maya_radial._overlay_class(self.q)(menu)
        menu.window.resize(600, 600)
        self.addCleanup(menu.window.deleteLater)
        maya_radial._state()["menu"] = menu
        return menu

    def _image(self, menu):
        from PySide6 import QtGui
        image = QtGui.QImage(600, 600, QtGui.QImage.Format_ARGB32)
        image.fill(0)
        menu.paint(menu.window, device=image)       # what the overlay itself paints
        return image

    def _ink(self, menu):
        image = self._image(menu)
        return sum(1 for y in range(0, 600, 3) for x in range(0, 600, 3)
                   if image.pixelColor(x, y).alpha() > 60)

    def test_pills_fly_out_of_the_centre(self):
        menu = self._menu()
        self.assertEqual(menu.progress(0), 0.0)
        self.assertEqual(self._ink(menu), 0)
        self.clock[0] += rules.OPEN_STEP_MS * 3
        self.assertGreater(menu.progress(0), menu.progress(2))
        half = self._ink(menu)
        self.assertGreater(half, 0)
        self.clock[0] += rules.open_total(menu.count)
        for i in range(menu.count):
            self.assertAlmostEqual(menu.progress(i), 1.0)
        self.assertGreater(self._ink(menu), half)
        self.assertFalse(menu.moving())

    def test_the_pointed_pill_lifts_and_falls(self):
        menu = self._menu()
        self.clock[0] += rules.open_total(menu.count)
        menu.hover = 2
        menu.step_lift(rules.HOVER_MS / 2.0)
        self.assertAlmostEqual(menu.lift[2], 0.5)
        self.assertTrue(menu.moving())
        menu.step_lift(rules.HOVER_MS)
        self.assertEqual(menu.lift[2], 1.0)
        lit = self._ink(menu)
        menu.hover = None
        menu.step_lift(rules.HOVER_MS)
        self.assertEqual(menu.lift[2], 0.0)
        self.assertGreater(lit, self._ink(menu))      # the glow and the larger pill

    def test_chosen_runs_at_once_then_flashes_and_goes_back_in(self):
        menu = self._menu()
        self.clock[0] += rules.open_total(menu.count)
        menu.choose(1)
        self.assertEqual(menu.phase, "fired")
        # the item is asked for at the press, not after the flash (2026-10-19)
        self.assertEqual(self.ran, [rules.DEFAULTS[1]])
        self.assertTrue(maya_radial.is_up())
        self.clock[0] += rules.FLASH_MS
        menu.tick()
        self.assertEqual(self.ran, [rules.DEFAULTS[1]])
        self.assertEqual(menu.phase, "leaving")
        self.assertFalse(maya_radial.is_up())
        self.assertIs(maya_radial._state()["leaving"], menu)
        self.clock[0] += rules.CLOSE_STEP_MS + 1
        self.assertLess(menu.progress(menu.count - 1), menu.progress(0))
        menu.clicked(True)                            # takes no clicks while it goes
        self.assertEqual(self.ran, [rules.DEFAULTS[1]])
        self.clock[0] += rules.close_total(menu.count)
        menu.tick()
        self.assertIsNone(menu.window)
        self.assertIsNone(maya_radial._state()["leaving"])

    def test_closing_paints_no_veil(self):
        menu = self._menu()
        self.clock[0] += rules.open_total(menu.count)
        maya_radial.close_menu()
        self.assertEqual(menu.phase, "leaving")
        image = self._image(menu)
        self.assertEqual(image.pixelColor(5, 5).alpha(), 0)

    def test_a_new_press_drops_a_closing_menu(self):
        menu = self._menu()
        maya_radial.close_menu()
        self.assertIs(maya_radial._state()["leaving"], menu)
        maya_radial.drop_leaving()
        self.assertIsNone(menu.window)

    def test_animations_off_is_at_once(self):
        maya_radial.animated = lambda: False
        menu = self._menu()
        self.assertEqual(menu.progress(3), 1.0)
        self.assertFalse(menu.moving())
        menu.choose(4)
        self.assertEqual(self.ran, [rules.DEFAULTS[4]])
        self.assertIsNone(menu.window)
        self.assertIsNone(maya_radial._state()["leaving"])


if __name__ == "__main__":
    unittest.main()
