"""The Time Bar's strip offscreen (2026-10-16): it paints, a press scrubs, a shift-drag
highlights, the band's handles move the playback range, the buttons step through the
keys - on a fake link, so no Maya scene is touched.

Spec: docs/superpowers/specs/2026-10-16-time-bar-design.md
"""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import maya_hubqt
    QT = maya_hubqt.qt()
except Exception:                                            # noqa: BLE001
    QT = None

import maya_hubstyle
from maya_timebar import bar, look


class FakeLink(object):

    def __init__(self):
        self.log = []
        self.s = {"now": 12.0, "a0": 0.0, "a1": 100.0, "p0": 10.0, "p1": 60.0,
                  "unit": "ntsc", "auto": True, "playing": False, "highlight": None}
        self.k = ([0.0, 6.0, 12.0, 30.0], [9.0])

    def light(self):
        return dict(self.s)

    def keys(self):
        self.log.append(("keys",))
        return self.k

    def now(self):
        return self.s["now"]

    def set_time(self, frame):
        self.log.append(("set_time", frame))
        self.s["now"] = float(frame)

    def set_ranges(self, a0, a1, p0, p1):
        self.log.append(("set_ranges", a0, a1, p0, p1))
        self.s.update(a0=a0, a1=a1, p0=p0, p1=p1)

    def set_highlight(self, sel):
        self.log.append(("set_highlight", sel))
        self.s["highlight"] = sel

    def step_key(self, forward, known):
        frame = look.neighbour_key(known, self.s["now"], forward)
        if frame is not None:
            self.set_time(frame)

    def toggle_play(self):
        self.log.append(("toggle_play",))
        self.s["playing"] = not self.s["playing"]

    def toggle_auto(self):
        self.s["auto"] = not self.s["auto"]

    def set_unit(self, unit):
        self.s["unit"] = unit

    def layers(self):
        return [("BaseAnimation", "BaseAnimation", False), ("Layer1", "Layer1", True)]

    def layer_label(self):
        return "Layer1"

    def pick_layer(self, name):
        self.log.append(("pick_layer", name))

    def back_to_maya(self):
        self.log.append(("back",))


@unittest.skipIf(QT is None, "no Qt")
class Strip(unittest.TestCase):

    def setUp(self):
        self.app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])
        self.link = FakeLink()
        self.strip = bar.make(self.link, 1.0, maya_hubstyle.TOKENS)
        self.strip.resize(1000, 44)
        self.strip.move(3000, 3000)
        self.strip.show()
        self.app.processEvents()
        self.addCleanup(self.strip.deleteLater)
        self.tl = self.strip.timeline

    def mouse(self, kind, x, button, buttons, mods=None):
        Qt = QT.QtCore.Qt
        local = QT.QtCore.QPointF(x, self.tl.height() / 2.0)
        event = QT.QtGui.QMouseEvent(kind, local, QT.QtCore.QPointF(self.tl.mapToGlobal(local.toPoint())),
                                     button, buttons, mods if mods is not None else Qt.NoModifier)
        QT.QtWidgets.QApplication.sendEvent(self.tl, event)

    def x(self, frame):
        return self.tl.track().x(frame)

    def test_it_shows_what_the_scene_holds(self):
        self.assertEqual(self.strip.field.text(), "12")
        self.assertEqual(self.strip.fps.text(), "30 fps")
        self.assertTrue(self.strip.auto.isChecked())
        self.assertIn("Layer1", self.strip.layer.text())
        self.assertEqual(self.strip.keys, [0.0, 6.0, 12.0, 30.0])
        self.assertEqual(self.strip.breakdowns, [9.0])

    def test_it_paints_the_band_keys_and_playhead(self):
        image = QT.QtGui.QImage(self.tl.size(), QT.QtGui.QImage.Format_ARGB32)
        image.fill(0)
        self.tl.render(image)
        row = self.tl.height() // 3
        accent = QT.QtGui.QColor(maya_hubstyle.TOKENS["accent"])

        def near(px, c):
            return abs(px.red() - c.red()) < 30 and abs(px.green() - c.green()) < 30 and abs(px.blue() - c.blue()) < 30
        self.assertTrue(near(image.pixelColor(int(self.x(30)), row), accent), "a key")
        self.assertTrue(near(image.pixelColor(int(self.x(12)), self.tl.height() - 6), accent), "the playhead")
        self.assertFalse(near(image.pixelColor(int(self.x(45)), row), accent))

    def test_a_press_scrubs_to_the_whole_frame(self):
        E, Qt = QT.QtCore.QEvent, QT.QtCore.Qt
        self.mouse(E.MouseButtonPress, self.x(40.3), Qt.LeftButton, Qt.LeftButton)
        self.mouse(E.MouseMove, self.x(44.6), Qt.NoButton, Qt.LeftButton)
        self.mouse(E.MouseButtonRelease, self.x(44.6), Qt.LeftButton, Qt.NoButton)
        self.assertEqual([e for e in self.link.log if e[0] == "set_time"], [("set_time", 40), ("set_time", 45)])
        self.assertEqual(self.strip.field.text(), "45")

    def test_a_shift_drag_highlights_and_a_click_clears_it(self):
        E, Qt = QT.QtCore.QEvent, QT.QtCore.Qt
        S = Qt.ShiftModifier
        self.mouse(E.MouseButtonPress, self.x(40), Qt.LeftButton, Qt.LeftButton, S)
        self.mouse(E.MouseMove, self.x(22), Qt.NoButton, Qt.LeftButton, S)
        self.mouse(E.MouseButtonRelease, self.x(22), Qt.LeftButton, Qt.NoButton, S)
        self.assertEqual(self.link.s["highlight"], (22, 40))
        self.assertNotIn("set_time", [e[0] for e in self.link.log])
        self.mouse(E.MouseButtonPress, self.x(50), Qt.LeftButton, Qt.LeftButton)
        self.mouse(E.MouseButtonRelease, self.x(50), Qt.LeftButton, Qt.NoButton)
        self.assertIsNone(self.link.s["highlight"])

    def test_dragging_a_handle_moves_the_playback_range(self):
        E, Qt = QT.QtCore.QEvent, QT.QtCore.Qt
        self.mouse(E.MouseButtonPress, self.x(60) - 1, Qt.LeftButton, Qt.LeftButton)
        self.mouse(E.MouseMove, self.x(72), Qt.NoButton, Qt.LeftButton)
        self.mouse(E.MouseButtonRelease, self.x(72), Qt.LeftButton, Qt.NoButton)
        self.assertEqual(self.link.s["p1"], 72)
        self.assertEqual(self.link.s["p0"], 10)
        self.assertNotIn("set_time", [e[0] for e in self.link.log])

    def test_the_grip_moves_the_animation_range_on_release(self):
        E, Qt = QT.QtCore.QEvent, QT.QtCore.Qt
        self.mouse(E.MouseButtonPress, 3, Qt.LeftButton, Qt.LeftButton)
        self.mouse(E.MouseMove, self.x(-15), Qt.NoButton, Qt.LeftButton)
        self.assertFalse([e for e in self.link.log if e[0] == "set_ranges"])
        self.mouse(E.MouseButtonRelease, self.x(-15), Qt.LeftButton, Qt.NoButton)
        self.assertEqual(self.link.s["a0"], -15)

    def test_the_key_buttons_step_through_keys_and_breakdowns(self):
        self.strip.next.click()
        self.assertEqual(self.link.s["now"], 30.0)
        self.strip.prev.click()
        self.strip.prev.click()
        self.assertEqual(self.link.s["now"], 9.0)

    def test_play_toggles_and_keys_are_not_read_while_playing(self):
        self.strip.play.click()
        self.assertTrue(self.link.s["playing"])
        self.link.log.clear()
        self.strip.refresh(keys=True)
        self.assertNotIn(("keys",), self.link.log)
        self.link.s["playing"] = False
        self.strip.refresh()
        self.assertIn(("keys",), self.link.log)

    def test_the_time_job_moves_only_the_playhead(self):
        self.link.s["now"] = 33.0
        self.link.log.clear()
        self.strip.on_time()
        self.assertEqual(self.strip.field.text(), "33")
        self.assertEqual(self.link.log, [])

    def test_a_typed_frame_goes_to_maya(self):
        self.strip.field.setText("27")
        self.strip.field.returnPressed.emit()
        self.assertIn(("set_time", 27.0), self.link.log)

    def test_a_link_that_raises_never_leaves_the_slot(self):
        def boom(*_a):
            raise RuntimeError("no")
        self.link.set_time = boom
        self.strip.field.setText("5")
        self.strip.field.returnPressed.emit()        # printed, not raised


if __name__ == "__main__":
    unittest.main()
