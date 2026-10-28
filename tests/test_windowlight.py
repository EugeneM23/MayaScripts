"""maya_windowlight - only the window under the mouse is lit (2026-10-23): the rule
(`pick`), the fade (`step`) and the watch over offscreen widgets, the mouse's window
handed in."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tests  # noqa: F401

from PySide6 import QtCore, QtWidgets

import maya_hubwindow as hubwindow
import maya_windowlight as wl


def _app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def node(name="", top=False, main=False, framed=False, control=False, skip=False,
         w=300, h=300):
    return {"name": name, "top": top, "main": main, "framed": framed,
            "control": control, "skip": skip, "w": w, "h": h}


class Pick(unittest.TestCase):

    def test_a_maya_workspace_control_is_lit(self):
        chain = [node("treeView"), node("Outliner", control=True),
                 node("MayaWindow", top=True, main=True)]
        self.assertEqual(wl.pick(chain), (1, "ring"))

    def test_maya_s_windows_off_lights_only_ours(self):
        chain = [node("x"), node("Outliner", control=True), node("M", top=True, main=True)]
        self.assertIsNone(wl.pick(chain, maya_on=False))
        ours = [node("x"), node("skeldarPoseLibrary", control=True),
                node("M", top=True, main=True)]
        self.assertEqual(wl.pick(ours, maya_on=False), (1, "ring"))

    def test_the_viewport_and_maya_s_bars_are_never_lit(self):
        for name in ("MainPane", "Shelf", "TimeSlider", "StatusLine"):
            chain = [node("panel"), node(name, control=True), node("M", top=True, main=True)]
            self.assertIsNone(wl.pick(chain), name)

    def test_the_hub_lights_its_own_cards(self):
        chain = [node("card"), node("skeldarAnimHub", control=True),
                 node("M", top=True, main=True)]
        self.assertIsNone(wl.pick(chain))

    def test_a_window_of_ours_with_a_frame_lights_itself(self):
        chain = [node("btn"), node("skeldarChatFrame"),
                 node("skeldarChatWindow", top=True, framed=True)]
        self.assertEqual(wl.pick(chain), (2, "frame"))

    def test_a_floating_window_is_lit_whole_and_the_main_window_never(self):
        self.assertEqual(wl.pick([node("b"), node("hotkeyEditor", top=True)]), (1, "ring"))
        self.assertIsNone(wl.pick([node("b"), node("MayaWindow", top=True, main=True)]))

    def test_menus_ghosts_and_bars_too_small_are_not_lit(self):
        self.assertIsNone(wl.pick([node("menu", top=True, skip=True)]))
        self.assertIsNone(wl.pick([node("skeldarPoseGhost", top=True)]))
        self.assertIsNone(wl.pick([node("skeldarSceneTabs", control=True, h=20),
                                   node("M", top=True, main=True)]))


class Step(unittest.TestCase):

    def test_it_comes_up_and_goes_down_at_its_own_pace(self):
        self.assertAlmostEqual(wl.step(0.0, 1.0, 70, 140, 260), 0.5)
        self.assertAlmostEqual(wl.step(1.0, 0.0, 130, 140, 260), 0.5)
        self.assertEqual(wl.step(0.9, 1.0, 500, 140, 260), 1.0)
        self.assertEqual(wl.step(0.1, 0.0, 500, 140, 260), 0.0)


class Watch(unittest.TestCase):

    def setUp(self):
        self.app = _app()
        self.saved = (wl.widget_at, wl.Light._is_control)
        self.under = None
        wl.widget_at = lambda q, pos: self.under
        wl.Light._is_control = lambda self_, name: name in ("Outliner", "Graph")
        self.light = wl.Light()
        self.light.start()
        self.light.tick_timer.stop()
        self.made = []

    def tearDown(self):
        self.light.stop()
        for widget in self.made:
            widget.deleteLater()
        wl.widget_at, wl.Light._is_control = self.saved
        self.app.processEvents()

    def window(self, control):
        top = QtWidgets.QWidget()
        top.setObjectName("FakeMain" + control)
        inner = QtWidgets.QWidget(top)
        inner.setObjectName(control)
        inner.setGeometry(0, 0, 200, 200)
        leaf = QtWidgets.QWidget(inner)
        leaf.setGeometry(10, 10, 50, 50)
        top.resize(220, 220)
        top.show()
        self.made.append(top)
        return inner, leaf

    def settle(self):
        for _ in range(200):
            self.light.tick_at = (self.light.tick_at or 0) - 0.05
            self.light.tick()
            if not self.light.tick_timer.isActive():
                break

    def test_a_widget_hiding_parentwidget_under_its_own_attribute_is_walked_past(self):
        """2026-10-28: animBot's widgets carry an attribute named parentWidget
        (`'SliderWidget' object is not callable`, 20 times a second in the
        Script Editor) - the walk asks Qt's own QWidget.parentWidget."""
        outliner, leaf = self.window("Outliner")
        leaf.parentWidget = QtWidgets.QWidget()           # what animBot's classes do
        self.made.append(leaf.parentWidget)
        self.under = leaf
        nodes, _widgets = self.light.chain(leaf)
        self.assertEqual([n["name"] for n in nodes][:2], ["", "Outliner"])
        self.light.poll(force=True)
        self.settle()
        self.assertEqual(self.light.overlays[wl._ptr(self.light.q, outliner)].level, 1.0)

    def test_the_window_under_the_mouse_is_lit_and_the_other_goes_out(self):
        outliner, leaf_a = self.window("Outliner")
        graph, leaf_b = self.window("Graph")
        self.under = leaf_a
        self.light.poll(force=True)
        self.settle()
        key_a = wl._ptr(self.light.q, outliner)
        self.assertEqual(self.light.overlays[key_a].level, 1.0)
        self.under = leaf_b
        self.light.poll(force=True)
        self.settle()
        key_b = wl._ptr(self.light.q, graph)
        self.assertNotIn(key_a, self.light.overlays)        # faded out and gone
        self.assertEqual(self.light.overlays[key_b].level, 1.0)
        self.under = None
        self.light.poll(force=True)
        self.settle()
        self.assertEqual(self.light.overlays, {})

    def test_the_ring_stands_on_its_window(self):
        outliner, leaf = self.window("Outliner")
        self.under = leaf
        self.light.poll(force=True)
        overlay = self.light.overlays[wl._ptr(self.light.q, outliner)]
        rect = QtCore.QRect(outliner.mapToGlobal(QtCore.QPoint(0, 0)), outliner.size())
        self.assertEqual(overlay.geometry(), rect)
        self.assertEqual(overlay.objectName(), wl.OVERLAY)

    def test_the_ring_follows_a_dragged_window_with_no_poll(self):
        outliner, leaf = self.window("Outliner")
        self.under = leaf
        self.light.poll(force=True)
        overlay = self.light.overlays[wl._ptr(self.light.q, outliner)]
        top = outliner.window()
        for step in range(1, 4):
            top.move(top.x() + 37, top.y() + 11)
            self.app.processEvents()
            rect = QtCore.QRect(outliner.mapToGlobal(QtCore.QPoint(0, 0)),
                                outliner.size())
            self.assertEqual(overlay.geometry(), rect, step)
        outliner.resize(150, 120)
        self.app.processEvents()
        self.assertEqual(overlay.size(), QtCore.QSize(150, 120))

    def test_the_old_window_is_no_longer_followed(self):
        outliner, leaf_a = self.window("Outliner")
        graph, leaf_b = self.window("Graph")
        self.under = leaf_a
        self.light.poll(force=True)
        self.under = leaf_b
        self.light.poll(force=True)
        self.assertNotIn(outliner, self.light.watched)
        self.assertIn(graph, self.light.watched)
        self.light.stop()
        self.assertEqual(self.light.watched, [])

    def test_a_framed_window_of_ours_lights_its_own_frame(self):
        root = QtWidgets.QWidget(None, QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint)
        root.setObjectName("skeldarChatWindow")
        layout = QtWidgets.QVBoxLayout(root)
        frame = hubwindow.frame_class()(1.0)
        layout.addWidget(frame)
        leaf = QtWidgets.QWidget(frame)
        root.resize(300, 300)
        root.show()
        self.made.append(root)
        self.under = leaf
        self.light.poll(force=True)
        self.settle()
        self.assertEqual(frame.level, 1.0)
        self.assertEqual(self.light.overlays, {})
        self.under = None
        self.light.poll(force=True)
        self.settle()
        self.assertEqual(frame.level, 0.0)


if __name__ == "__main__":
    unittest.main()
