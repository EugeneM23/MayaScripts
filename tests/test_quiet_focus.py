"""No field of ours holds the keyboard until it is clicked (2026-11-19).

The animator: «в некоторых участках интерфейса активна опция печатания по
умолчанию и когда я хочу использовать горячую клавишу опция перехватывает
управление. Пока я не кликнул в поле опция не должна быть активна» - the AT
bar's frames field held the caret by default and took Maya's hotkeys.
"""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6 import QtCore, QtWidgets
except ImportError:                                          # pragma: no cover
    QtWidgets = None

import maya_hubqt


@unittest.skipIf(QtWidgets is None, "no Qt")
class QuietFocus(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def make(self):
        root = QtWidgets.QWidget()
        self.addCleanup(root.deleteLater)
        lay = QtWidgets.QVBoxLayout(root)
        widgets = dict(spin=QtWidgets.QSpinBox(), line=QtWidgets.QLineEdit(),
                       button=QtWidgets.QPushButton("go"),
                       tool=QtWidgets.QToolButton(),
                       combo=QtWidgets.QComboBox(),
                       box=QtWidgets.QCheckBox("x"),
                       listing=QtWidgets.QListWidget())
        for widget in widgets.values():
            lay.addWidget(widget)
        return root, widgets

    def test_nothing_takes_tab_focus_after_it(self):
        root, w = self.make()
        maya_hubqt.quiet_focus(root)
        Qt = QtCore.Qt
        for name in ("spin", "line", "listing"):
            self.assertEqual(w[name].focusPolicy(), Qt.ClickFocus, name)
        for name in ("button", "tool", "combo", "box"):
            self.assertEqual(w[name].focusPolicy(), Qt.NoFocus, name)

    def test_a_shown_window_gives_its_keyboard_to_nobody(self):
        # the AT bar's own road: the window becomes active and Qt hands its
        # keyboard to the first widget that takes Tab focus
        root, w = self.make()
        before = root.focusNextPrevChild(True)
        self.assertTrue(before)                      # without it: the spin box takes it
        w["spin"].clearFocus()
        maya_hubqt.quiet_focus(root)
        root.focusNextPrevChild(True)
        self.assertFalse(any(x.hasFocus() for x in w.values()))

    def test_enter_lets_the_keyboard_go(self):
        root, w = self.make()
        maya_hubqt.quiet_focus(root)
        root.show()
        self.addCleanup(root.hide)
        w["spin"].setFocus()
        self.app.processEvents()
        if not w["spin"].hasFocus():
            self.skipTest("the offscreen platform gives no focus")
        event = QtWidgets.QApplication.sendEvent
        from PySide6 import QtGui
        event(w["spin"], QtGui.QKeyEvent(QtCore.QEvent.KeyPress, QtCore.Qt.Key_Return,
                                         QtCore.Qt.NoModifier))
        self.app.processEvents()
        self.assertFalse(w["spin"].hasFocus())

    def test_twice_is_once(self):
        root, w = self.make()
        self.assertGreater(maya_hubqt.quiet_focus(root), 0)
        self.assertEqual(maya_hubqt.quiet_focus(root), 0)


if __name__ == "__main__":
    unittest.main()
