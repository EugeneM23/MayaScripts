"""maya_sidepanel.skin - Maya's editors in the side panel recoloured (2026-10-17): the
sheet (colours, borders and radii at the display's scale, never a size), the exact
Maya greys swapped for ours and back, the Channel Box's own colour flags."""
import re
import sys
import types
import unittest
from unittest import mock

try:
    from PySide6 import QtGui, QtWidgets
except ImportError:                                          # pragma: no cover
    QtGui = QtWidgets = None

from maya_sidepanel import skin


class Sheet(unittest.TestCase):

    def test_every_rule_is_scoped_to_the_page_stack(self):
        text = skin.sheet(1.0)
        rules = [r for r in re.split(r"}\s*", text) if r.strip()]
        for rule in rules:
            selectors = rule.split("{")[0]
            for selector in selectors.split(","):
                self.assertTrue(selector.strip().startswith("QWidget#" + skin.STACK), selector)

    def test_no_size_is_set(self):
        text = skin.sheet(1.5)
        for prop in ("width", "height", "min-width", "max-height", "font-size"):
            self.assertNotIn(prop + ":", text.replace("border-", "").replace("-radius", ""))

    def test_borders_and_radii_follow_the_scale(self):
        self.assertIn("1px solid", skin.sheet(1.0))
        self.assertIn("border-radius: 5px", skin.sheet(1.0))
        big = skin.sheet(2.0)
        self.assertIn("2px solid", big)
        self.assertIn("border-radius: 10px", big)

    def test_the_tokens_given_are_the_colours_used(self):
        tokens = dict(skin.T, panel="#010203")
        self.assertIn("#010203", skin.sheet(1.0, tokens))


@unittest.skipIf(QtWidgets is None, "no Qt")
class Recolor(unittest.TestCase):

    def setUp(self):
        self.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        self.root = QtWidgets.QWidget()
        self.child = QtWidgets.QWidget(self.root)
        self.other = QtWidgets.QWidget(self.root)
        pal = self.child.palette()
        pal.setColor(QtGui.QPalette.Window, QtGui.QColor("#444444"))
        pal.setColor(QtGui.QPalette.Base, QtGui.QColor("#2b2b2b"))
        self.child.setPalette(pal)
        pal = self.other.palette()
        pal.setColor(QtGui.QPalette.Window, QtGui.QColor("#123456"))
        self.other.setPalette(pal)
        self.addCleanup(self.root.deleteLater)

    def test_maya_s_exact_greys_are_swapped_and_others_left(self):
        swapped = skin.recolor(self.root, QtGui)
        self.assertGreaterEqual(swapped, 1)
        self.assertEqual(self.child.palette().color(QtGui.QPalette.Window).name(), skin.T["panel"])
        self.assertEqual(self.child.palette().color(QtGui.QPalette.Base).name(), skin.T["track"])
        self.assertEqual(self.other.palette().color(QtGui.QPalette.Window).name(), "#123456")

    def test_given_back_they_are_maya_s_again(self):
        skin.recolor(self.root, QtGui)
        skin.recolor(self.root, QtGui, back=True)
        self.assertEqual(self.child.palette().color(QtGui.QPalette.Window).name(), "#444444")
        self.assertEqual(self.child.palette().color(QtGui.QPalette.Base).name(), "#2b2b2b")

    def test_twice_swaps_nothing_more(self):
        skin.recolor(self.root, QtGui)
        before = self.child.palette().color(QtGui.QPalette.Window).name()
        skin.recolor(self.root, QtGui)
        self.assertEqual(self.child.palette().color(QtGui.QPalette.Window).name(), before)

    def test_the_maps_are_each_other_s_inverse(self):
        for maya, ours in skin.FILLS.items():
            self.assertEqual(skin.BACK[ours], maya)

    def test_apply_names_and_styles_the_stack(self):
        theme = types.ModuleType("maya_mayatheme")
        theme.palette = lambda QtGui: QtGui.QPalette()
        # one entry swapped and put back: patch.dict refills the whole of sys.modules,
        # and a module imported meanwhile would be imported twice afterwards
        saved = sys.modules.get("maya_mayatheme")
        sys.modules["maya_mayatheme"] = theme
        try:
            skin.apply(self.root, QtGui, 1.0)
        finally:
            if saved is None:
                sys.modules.pop("maya_mayatheme", None)
            else:
                sys.modules["maya_mayatheme"] = saved
        self.assertEqual(self.root.objectName(), skin.STACK)
        self.assertIn("QWidget#" + skin.STACK, self.root.styleSheet())
        self.assertTrue(self.root.autoFillBackground())


class ChannelBox(unittest.TestCase):

    class Cmds(object):
        def __init__(self, exists=True):
            self.exists = exists
            self.edits = []

        def channelBox(self, name, exists=False, edit=False, **kw):
            if exists:
                return self.exists
            self.edits.append(kw)

    def run_with(self, fake, on):
        cmds = types.ModuleType("maya.cmds")
        cmds.channelBox = fake.channelBox
        import maya
        saved = sys.modules.get("maya.cmds")
        sys.modules["maya.cmds"] = cmds
        try:
            with mock.patch.object(maya, "cmds", cmds, create=True):
                return skin.channel_box(on)
        finally:
            if saved is None:
                sys.modules.pop("maya.cmds", None)
            else:
                sys.modules["maya.cmds"] = saved

    def test_ours_then_maya_s_colours(self):
        fake = self.Cmds()
        self.assertTrue(self.run_with(fake, True))
        flags = dict((k, v) for e in fake.edits for k, v in e.items())
        self.assertEqual(flags["backgroundColor"], skin._rgb(skin.T["panel"]))
        fake.edits[:] = []
        self.assertTrue(self.run_with(fake, False))
        flags = dict((k, v) for e in fake.edits for k, v in e.items())
        self.assertEqual(flags["attrBgColor"], skin._rgb("#444444"))

    def test_no_channel_box_changes_nothing(self):
        fake = self.Cmds(exists=False)
        self.assertFalse(self.run_with(fake, True))
        self.assertEqual(fake.edits, [])

    def test_rgb(self):
        self.assertEqual(skin._rgb("#ff0080"), [1.0, 0.0, 128 / 255.0])


if __name__ == "__main__":
    unittest.main()
