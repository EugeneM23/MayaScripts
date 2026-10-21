"""Maya's title and menu bar in the hub's colours (2026-10-21, maya_mainbar):
the sheet, the caption's colours, the menu bar skinned and given back on a
stand-in main window offscreen, the switch."""

import os
import sys
import types
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import maya_hubstyle as hubstyle
import maya_mainbar as mb


class Sheet(unittest.TestCase):
    def test_every_rule_is_under_the_menu_bars_mark(self):
        text = mb.sheet(1.5)
        selectors = [part.split("{")[0].strip() for part in text.split("}")
                     if "{" in part]
        self.assertTrue(selectors)
        for selector in selectors:
            for one in selector.split(","):
                self.assertTrue(one.strip().startswith('QMenuBar[skeldarMainBar="1"]'),
                                one)

    def test_its_pixels_follow_the_scale_and_its_colours_are_the_hubs(self):
        self.assertIn("border-radius: 6px", mb.sheet(1.0))
        self.assertIn("border-radius: 12px", mb.sheet(2.0))
        for token in ("panel", "hover", "muted", "text", "track"):
            self.assertIn(hubstyle.TOKENS[token], mb.sheet(1.0))

    def test_no_size_is_set(self):
        for word in ("width", "height", "font-size", "min-", "max-"):
            self.assertNotIn(word, mb.sheet(1.0))


class Caption(unittest.TestCase):
    def test_colorref_is_bgr(self):
        self.assertEqual(mb.colorref("#102030"), 0x302010)
        self.assertEqual(mb.colorref("ffffff"), 0xFFFFFF)

    def test_on_gives_the_hubs_colours_and_off_windows_own(self):
        on = mb.caption_values(True)
        self.assertEqual(on[mb.DWMWA_CAPTION_COLOR], mb.colorref(hubstyle.TOKENS["panel"]))
        self.assertEqual(on[mb.DWMWA_TEXT_COLOR], mb.colorref(mb.CAPTION_TEXT))
        off = mb.caption_values(False)
        self.assertEqual(set(off), set(on))
        self.assertTrue(all(v == mb.DWMWA_COLOR_DEFAULT for v in off.values()))


class FakeCmds(object):
    def __init__(self):
        self.vars = {}

    def optionVar(self, exists=None, query=None, intValue=None, **_):
        if exists is not None:
            return exists in self.vars
        if query is not None:
            return self.vars[query]
        if intValue is not None:
            self.vars[intValue[0]] = intValue[1]

    def about(self, batch=False, **_):
        return False

    def mayaDpiSetting(self, **_):
        return 1.5


class Skinned(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6 import QtWidgets
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        from PySide6 import QtWidgets
        self.window = QtWidgets.QMainWindow()
        self.window.menuBar().addMenu("File")
        self.window.menuBar().setStyleSheet("QMenuBar { color: red; }")
        self.cmds = FakeCmds()
        self.captions = []
        if hasattr(sys, mb.STATE):
            delattr(sys, mb.STATE)
        patches = [
            mock.patch.object(mb, "_cmds", lambda: self.cmds),
            mock.patch.object(mb, "main_window", lambda: self.window),
            mock.patch.object(mb, "paint_caption",
                              lambda hwnd, on: self.captions.append(on) or True),
            mock.patch.object(mb, "_hwnd", lambda window: 1234),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.addCleanup(mb.unwatch)

    def test_on_is_the_default_and_marks_and_sheets_the_menu_bar(self):
        self.assertTrue(mb.enabled())
        self.assertTrue(mb.ensure())
        bar = self.window.menuBar()
        self.assertEqual(bar.property(mb.MARK), "1")
        self.assertEqual(bar.styleSheet(), mb.sheet(1.5))
        self.assertEqual(self.captions, [True])
        self.assertIsNotNone(getattr(sys, mb.STATE)["timer"])

    def test_a_second_apply_paints_the_caption_once(self):
        mb.apply()
        mb.apply()
        self.assertEqual(self.captions, [True])

    def test_off_gives_maya_its_sheet_and_the_caption_back(self):
        mb.set_enabled(True)
        message = mb.set_enabled(False)
        bar = self.window.menuBar()
        self.assertIsNone(bar.property(mb.MARK))
        self.assertEqual(bar.styleSheet(), "QMenuBar { color: red; }")
        self.assertEqual(self.captions, [True, False])
        self.assertIn("Maya's", message)
        self.assertIsNone(getattr(sys, mb.STATE)["timer"])

    def test_a_sheet_maya_emptied_is_put_back_by_the_watch(self):
        mb.ensure()
        self.window.menuBar().setStyleSheet("")
        mb._tick()
        self.assertEqual(self.window.menuBar().styleSheet(), mb.sheet(1.5))


class Purity(unittest.TestCase):
    def test_it_imports_no_maya_or_qt_at_import(self):
        import subprocess
        here = os.path.dirname(os.path.abspath(mb.__file__))
        code = ("import sys; import maya_mainbar; "
                "bad = [m for m in sys.modules if m.startswith(('maya.', 'PySide'))]; "
                "print(bad); sys.exit(1 if bad else 0)")
        result = subprocess.run([sys.executable, "-c", code], cwd=here,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
