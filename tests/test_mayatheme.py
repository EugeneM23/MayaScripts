"""maya_mayatheme: Maya in the hub's colours (2026-10-17, variant B) - the
palette, the sheet, the display colours saved once and given back, the Qt part
offscreen.

Spec: docs/superpowers/specs/2026-10-17-maya-theme-design.md
"""

import json
import os
import re
import subprocess
import sys
import unittest

import maya_hubstyle as hubstyle
import maya_mayatheme as theme

_PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(
    __file__))), "SkeldarAnim")


class FakeCmds(object):
    """optionVar, displayRGBColor and displayPref as Maya answers them."""

    def __init__(self):
        self.optionvars = {}
        self.colours = dict((name, [0.5, 0.5, 0.5, 1.0])
                            for name in theme.RGB)
        self.colours["graphEditorOutlinerSelected"] = [0.32, 0.52, 0.65, 0.8]
        self.gradient = False
        self.writes = 0

    def optionVar(self, exists=None, query=None, intValue=None,  # noqa: N802
                  stringValue=None, remove=None):
        if exists is not None:
            return exists in self.optionvars
        if query is not None:
            return self.optionvars[query]
        if remove is not None:
            self.optionvars.pop(remove, None)
            return None
        name, value = intValue if intValue is not None else stringValue
        self.optionvars[name] = value
        return None

    def displayRGBColor(self, name, *values, **flags):  # noqa: N802
        if flags.get("query") or flags.get("q"):
            return list(self.colours[name])
        if name not in self.colours:
            raise RuntimeError("no colour " + name)
        self.colours[name] = list(values)
        self.writes += 1
        return None

    def displayPref(self, **flags):  # noqa: N802
        if flags.get("query"):
            return self.gradient
        self.gradient = bool(flags["displayGradient"])
        return None


class Pure(unittest.TestCase):

    def test_the_module_imports_no_maya_and_no_qt(self):
        code = ("import sys; sys.path.insert(0, %r); import maya_mayatheme; "
                "bad = [m for m in sys.modules if m.split('.')[0] in "
                "('maya', 'PySide6', 'PySide2')]; print(bad)") % _PLUGIN
        out = subprocess.check_output([sys.executable, "-c", code],
                                      cwd=_PLUGIN).decode().strip()
        self.assertEqual(out, "[]")

    def test_the_sheet_sets_no_size(self):
        sheet = theme.sheet(1.5)
        for prop in ("width", "height", "padding", "margin", "spacing",
                     "font-size", "font:"):
            for line in sheet.splitlines():
                body = line.split("{", 1)[-1]
                self.assertNotRegex(
                    body, r"(^|[;{\s])(min-|max-)?" + re.escape(prop),
                    "%s in %r" % (prop, line))

    def test_the_sheet_has_no_blanket_widget_rule(self):
        for line in theme.sheet(1.0).splitlines():
            self.assertFalse(re.match(r"\s*QWidget\b", line), line)

    def test_the_sheet_takes_its_colours_from_the_hub(self):
        sheet = theme.sheet(1.0)
        for key in ("panel", "field", "line", "accent", "text"):
            self.assertIn(hubstyle.TOKENS[key], sheet)

    def test_the_palette_is_the_hub_s(self):
        self.assertEqual(theme.PALETTE["Window"], hubstyle.TOKENS["panel"])
        self.assertEqual(theme.PALETTE["Text"], hubstyle.TOKENS["text"])
        for value in list(theme.PALETTE.values()) + list(
                theme.DISABLED.values()):
            self.assertRegex(value, r"^#[0-9a-f]{6}$")

    def test_keys_and_curves_keep_maya_s_colours(self):
        for name in theme.RGB:
            self.assertNotRegex(name, r"Key|Curve|Tangent|Rotate|Translate"
                                      r"|Scale|manip|lead|hilite")

    def test_the_rgb_values_are_floats_in_range(self):
        for name, rgb in theme.RGB.items():
            self.assertEqual(len(rgb), 3, name)
            for c in rgb:
                self.assertTrue(0.0 <= c <= 1.0, name)

    def test_with_ours_and_without_are_inverse(self):
        original = "QMenu { color: red; }\n/* keep me */"
        ours = theme.with_ours(original, "QToolTip { color: blue; }")
        self.assertIn(theme.START, ours)
        self.assertEqual(theme.without_ours(ours), original)
        #  applied twice: one copy of ours, the original kept
        twice = theme.with_ours(ours, "QToolTip { color: blue; }")
        self.assertEqual(twice.count(theme.START), 1)
        self.assertEqual(theme.without_ours(twice), original)

    def test_without_ours_on_a_sheet_that_never_had_it(self):
        self.assertEqual(theme.without_ours("QMenu {}"), "QMenu {}")
        self.assertEqual(theme.without_ours(""), "")


class Switch(unittest.TestCase):

    def setUp(self):
        self.cmds = FakeCmds()
        self.saved = (theme._cmds, theme.apply_qt, theme.remove_qt)
        self.qt_calls = []
        theme._cmds = lambda: self.cmds
        theme.apply_qt = lambda: self.qt_calls.append("on") or True
        theme.remove_qt = lambda: self.qt_calls.append("off") or True

    def tearDown(self):
        theme._cmds, theme.apply_qt, theme.remove_qt = self.saved

    def test_off_by_default(self):
        self.assertFalse(theme.enabled())

    def test_on_writes_the_colours_and_keeps_theirs(self):
        before = json.loads(json.dumps(self.cmds.colours))
        message = theme.set_enabled(True)
        self.assertTrue(theme.enabled())
        self.assertIn("on", message.lower())
        self.assertTrue(self.cmds.gradient)
        self.assertEqual(self.qt_calls, ["on"])
        for name, rgb in theme.RGB.items():
            self.assertEqual(self.cmds.colours[name][:3], list(rgb))
            #  the alpha stays the animator's
            self.assertEqual(self.cmds.colours[name][3], before[name][3])
        kept = json.loads(self.cmds.optionvars[theme.SAVED_VAR])
        self.assertEqual(kept["rgb"], before)
        self.assertFalse(kept["gradient"])

    def test_a_second_on_does_not_save_the_theme_as_theirs(self):
        before = json.loads(json.dumps(self.cmds.colours))
        theme.set_enabled(True)
        theme.set_enabled(True)
        kept = json.loads(self.cmds.optionvars[theme.SAVED_VAR])
        self.assertEqual(kept["rgb"], before)

    def test_off_gives_everything_back(self):
        before = json.loads(json.dumps(self.cmds.colours))
        self.cmds.gradient = False
        theme.set_enabled(True)
        message = theme.set_enabled(False)
        self.assertFalse(theme.enabled())
        self.assertIn("off", message.lower())
        self.assertEqual(self.cmds.colours, before)
        self.assertFalse(self.cmds.gradient)
        self.assertNotIn(theme.SAVED_VAR, self.cmds.optionvars)
        self.assertEqual(self.qt_calls, ["on", "off"])

    def test_off_without_a_memory_changes_no_colour(self):
        theme.set_enabled(False)
        self.assertEqual(self.cmds.writes, 0)
        self.assertEqual(self.qt_calls, ["off"])

    def test_a_colour_maya_lacks_is_skipped_and_said(self):
        del self.cmds.colours["hyperBackgroundColor"]
        message = theme.set_enabled(True)
        self.assertIn("1 colour", message)
        theme.set_enabled(False)

    def test_ensure_applies_only_the_qt_part_when_on(self):
        theme.ensure()
        self.assertEqual(self.qt_calls, [])
        theme.set_enabled(True)
        writes = self.cmds.writes
        theme.ensure()
        self.assertEqual(self.qt_calls, ["on", "on"])
        self.assertEqual(self.cmds.writes, writes)


def _qt():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PySide6 import QtWidgets
    except ImportError:
        return None
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@unittest.skipIf(_qt() is None, "no Qt")
class QtPart(unittest.TestCase):

    def setUp(self):
        self.app = _qt()
        self.app.setStyleSheet("QLabel { color: #123456; }")
        self.palette = self.app.palette()
        if hasattr(sys, theme.STATE):
            delattr(sys, theme.STATE)

    def tearDown(self):
        theme.remove_qt()
        self.app.setStyleSheet("")
        self.app.setPalette(self.palette)
        if hasattr(sys, theme.STATE):
            delattr(sys, theme.STATE)

    def test_on_and_off(self):
        from PySide6 import QtGui
        self.assertTrue(theme.apply_qt())
        sheet = self.app.styleSheet()
        self.assertTrue(sheet.startswith("QLabel { color: #123456; }"))
        self.assertIn(theme.START, sheet)
        window = self.app.palette().color(QtGui.QPalette.Window).name()
        self.assertEqual(window, hubstyle.TOKENS["panel"])
        #  applied again (Maya's start, a hub rebuild): one copy
        theme.apply_qt()
        self.assertEqual(self.app.styleSheet().count(theme.START), 1)
        self.assertTrue(theme.remove_qt())
        self.assertEqual(self.app.styleSheet(), "QLabel { color: #123456; }")
        self.assertEqual(self.app.palette().color(QtGui.QPalette.Window),
                         self.palette.color(QtGui.QPalette.Window))

    def test_off_with_the_state_lost_still_cuts_ours_out(self):
        from PySide6 import QtGui
        theme.apply_qt()
        delattr(sys, theme.STATE)
        theme.remove_qt()
        self.assertEqual(self.app.styleSheet(), "QLabel { color: #123456; }")
        #  the palette goes back to the style's own
        self.assertNotEqual(
            self.app.palette().color(QtGui.QPalette.Window).name(),
            hubstyle.TOKENS["panel"])


if __name__ == "__main__":
    unittest.main()
