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
class FlatTests(unittest.TestCase):
    """The menu offscreen (2026-11-19): up at once, the pointed pill flat-lit, gone at once."""

    def setUp(self):
        import os
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6 import QtWidgets
        self.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        import maya_hubqt
        self.q = maya_hubqt.qt()
        self.fake = FakeCmds()
        self.ran = []
        for name, value in (("cmds", self.fake), ("waiting", lambda key: False),
                            ("_run_later", lambda q, item, point: self.ran.append(item))):
            old = getattr(maya_radial, name)
            setattr(maya_radial, name, value)
            self.addCleanup(setattr, maya_radial, name, old)
        state = maya_radial._state()
        saved = dict(state)
        self.addCleanup(lambda: (state.clear(), state.update(saved)))
        state["menu"] = None

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

    def test_the_motion_is_gone(self):
        for name in ("animated", "_now_ms", "drop_leaving", "_mix"):
            self.assertFalse(hasattr(maya_radial, name), name)
        menu = self._menu()
        for name in ("progress", "ring", "moving", "step_lift", "leave", "lift", "phase",
                     "fired", "animate"):
            self.assertFalse(hasattr(menu, name), name)
        self.assertNotIn("leaving", maya_radial._state())

    def test_every_pill_stands_in_its_place_at_once(self):
        menu = self._menu()
        self.assertGreater(self._ink(menu), 0)

    def test_the_pointed_pill_is_lit_flat(self):
        from PySide6 import QtGui
        menu = self._menu()
        plain = self._image(menu)
        menu.hover = 2
        lit = self._image(menu)
        self.assertNotEqual(plain, lit)
        dx, dy = rules.slot_position(2, menu.px(rules.ring_radius(menu.count)), menu.count)
        x, y = int(300 + dx), int(300 + dy)        # slot 2 is east: its pill grows rightwards
        face = lit.pixelColor(x + int(menu.px(4)), y)
        self.assertEqual(face.name(), QtGui.QColor(maya_radial.hubstyle.TOKENS["card_active"])
                         .name())
        menu.hover = None
        self.assertEqual(plain, self._image(menu))  # no glow left behind, nothing to settle

    def test_chosen_closes_at_once_and_runs(self):
        menu = self._menu()
        menu.choose(1)
        self.assertEqual(self.ran, [rules.DEFAULTS[1]])
        self.assertIsNone(menu.window)
        self.assertFalse(maya_radial.is_up())

    def test_closing_is_at_once(self):
        menu = self._menu()
        maya_radial.close_menu()
        self.assertIsNone(menu.window)
        self.assertIsNone(maya_radial._state()["menu"])


if __name__ == "__main__":
    unittest.main()


class HeldKeys(unittest.TestCase):
    """2026-10-22: Windows reported a stuck "A" and Play/Pause as held, and the camera menu,
    listening to every key held at the press, never saw Space go up."""

    def held(self, kind, down):
        import maya_radial
        old = (maya_radial.key_down, maya_radial.keys_down)
        maya_radial.key_down = lambda vk: vk in down
        maya_radial.keys_down = lambda: sorted(down)
        try:
            return maya_radial.held_keys(kind)
        finally:
            maya_radial.key_down, maya_radial.keys_down = old

    def test_the_camera_menu_listens_to_space_alone(self):
        self.assertEqual(self.held("cameras", {0x20, 0x41, 0xB3}), [0x20])

    def test_a_quick_tap_already_up_is_still_space(self):
        self.assertEqual(self.held("cameras", {0x41}), [0x20])

    def test_the_slots_menu_listens_to_its_q(self):
        self.assertEqual(self.held("slots", {0x51, 0x41, 0xB3}), [0x51])

    def test_another_key_without_the_media_keys(self):
        self.assertEqual(self.held("slots", {0x46, 0xB3}), [0x46])
