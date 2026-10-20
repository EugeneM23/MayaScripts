"""The Time Bar's timeline and the layer panel's lanes show one drag and one playhead
(2026-10-20, the animator: «НАш тайм слайдер основной должен в точности реагировать на
действия на выдвижной панели слоев. Каретка должна бегать одинаково и ключи должны
перемещаться при переносе и на таймслайдере и на выдвижной панели слоев не важно где я
их перемещаю»). The timeline shows the ACTIVE layer's keys, so a drag of that layer's
keys on either view is drawn on both."""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import maya_hubstyle
from tests.test_timebar_bar import QT, Strip, LiveLink


@unittest.skipIf(QT is None, "no Qt")
class Synced(Strip):

    def setUp(self):
        super(Synced, self).setUp()
        from maya_timebar import layerpanel
        from tests.test_timebar_layerpanel import FakeLink as LayerLink
        self.link = LiveLink()                          # the timeline's keys move live
        self.strip.link = self.link
        self.ll = LayerLink()                           # A2 is the active layer
        self.ll.opts[layerpanel.LANES_VAR] = 1
        self.reads = {"keys": 0}
        keys = self.ll.keys_by_layer

        def counted(names):
            self.reads["keys"] += 1
            return keys(names)
        self.ll.keys_by_layer = counted
        self.panel = layerpanel.Panel(self.strip, self.ll, 1.0, maya_hubstyle.TOKENS, False)
        self.addCleanup(self.panel.destroy)
        self.strip.layer_panel = self.panel
        self.panel.open((1300, 815))
        self.strip.refresh(keys=True)

    # -- a drag on the lanes, seen on the timeline ---------------------------------
    def test_a_lanes_drag_of_the_active_layer_moves_the_timeline_s_keys(self):
        self.panel.lane_sel = {"a": 10, "b": 20, "names": ["A2", "A1"]}
        self.panel.lane_drag = ("key", "hmove", 10, (10, 20), False)
        self.panel.lane_preview = (20, 30)
        moving = self.tl.moving()
        self.assertEqual(moving[:2], ((10, 20), (20, 30)))

    def test_a_lanes_drag_of_another_layer_leaves_the_timeline_alone(self):
        self.panel.lane_sel = {"a": 10, "b": 20, "names": ["A1"]}
        self.panel.lane_drag = ("key", "hmove", 10, (10, 20), False)
        self.panel.lane_preview = (20, 30)
        self.assertIsNone(self.tl.moving())

    def test_a_lanes_drag_step_repaints_the_timeline(self):
        painted = []
        self.tl.repaint = lambda *a: painted.append(1)
        self.panel.lane_sel = {"a": 10, "b": 20, "names": ["A2"]}
        self.panel.lane_drag = ("key", "hmove", 10, (10, 20), False)
        self.panel.lane_preview = (10, 20)
        t = self.panel._track()
        self.panel.lane_move(t.x(25) + 1, self.panel.column.layout_().row_at(0, 0)[1] + 10)
        self.assertTrue(painted)

    def accent_at(self, widget, x, y):
        img = QT.QtGui.QImage(widget.size(), QT.QtGui.QImage.Format_ARGB32)
        img.fill(0)
        widget.render(img)
        a = QT.QtGui.QColor(maya_hubstyle.TOKENS["accent"])
        px = img.pixelColor(int(x), int(y))
        return all(abs(u - v) < 30 for u, v in ((px.red(), a.red()), (px.green(), a.green()),
                                                 (px.blue(), a.blue())))

    def test_the_timeline_paints_the_lanes_drag(self):
        t, y = self.tl.track(), self.tl.height() / 2.0
        mid = lambda f: (t.x(f) + t.end(f)) / 2.0             # noqa: E731
        self.assertTrue(self.accent_at(self.tl, mid(12), y))
        self.assertFalse(self.accent_at(self.tl, mid(22), y))
        self.panel.lane_sel = {"a": 10, "b": 20, "names": ["A2"]}
        self.panel.lane_drag = ("key", "hmove", 10, (10, 20), False)
        self.panel.lane_preview = (20, 30)                     # the key at 12 dragged to 22
        self.assertFalse(self.accent_at(self.tl, mid(12), y))
        self.assertTrue(self.accent_at(self.tl, mid(22), y))
        self.assertFalse(getattr(self.tl, "_failed", False))

    # -- a drag on the timeline, seen on the lanes ---------------------------------
    def start_timeline_drag(self):
        self.strip.state["highlight"] = self.link.s["highlight"] = (22, 40)
        self.tl.drag = ("hmove", 22, self.tl.track(), (22, 40))
        self.tl.preview = (30, 48)

    def test_a_timeline_drag_moves_the_active_lane_s_keys(self):
        self.start_timeline_drag()
        view = self.panel.drag_view()
        self.assertEqual(view["names"], ["A2"])
        self.assertEqual((view["span"], view["target"]), ((22, 40), (30, 48)))

    def test_the_lanes_read_no_keys_while_the_timeline_drags_keys(self):
        self.start_timeline_drag()
        before = self.reads["keys"]
        self.panel.refresh(keys=True)
        self.assertEqual(self.reads["keys"], before)
        self.tl.drag = self.tl.preview = None
        self.panel.refresh(keys=True)
        self.assertEqual(self.reads["keys"], before + 1)

    def test_a_timeline_drag_step_repaints_the_lanes(self):
        E, Qt = QT.QtCore.QEvent, QT.QtCore.Qt
        painted = []
        self.panel.lanes.repaint = lambda *a: painted.append(1)
        self.mouse(self.tl, E.MouseButtonPress, self.x(30), Qt.LeftButton, Qt.LeftButton)
        self.mouse(self.tl, E.MouseMove, self.x(36), Qt.NoButton, Qt.LeftButton)
        self.assertTrue(painted)
        self.mouse(self.tl, E.MouseButtonRelease, self.x(36), Qt.LeftButton, Qt.NoButton)

    def test_the_lanes_paint_a_timeline_drag(self):
        lay = self.panel.column.layout_()
        t = self.panel._track()
        mid = lambda f: (t.x(f) + t.end(f)) / 2.0             # noqa: E731
        y_active = lay.row_at(0, 0)[1] + lay.row_at(0, 0)[3] / 2.0
        self.assertTrue(self.accent_at(self.panel.lanes, mid(10), y_active))
        self.tl.drag = ("hmove", 5, self.tl.track(), (5, 15))
        self.tl.preview = (25, 35)                             # every lane's key at 10 sits in it
        self.assertFalse(self.accent_at(self.panel.lanes, mid(10), y_active))
        self.assertTrue(self.accent_at(self.panel.lanes, mid(30), y_active), "the active lane follows")
        self.assertFalse(getattr(self.panel.lanes, "_failed", False))

    # -- one playhead --------------------------------------------------------------
    def test_a_lanes_scrub_moves_the_timeline_s_playhead_at_once(self):
        row = self.panel.column.layout_().row_at(0, 0)
        t = self.panel._track()
        self.panel.lane_press(t.x(25) + 1, row[1] + 10)
        self.assertEqual(self.strip.state["now"], 25)
        self.assertEqual(self.strip.field.text(), "25")
        self.panel.lane_move(t.x(33) + 1, row[1] + 10)
        self.assertEqual(self.strip.state["now"], 33)
        self.assertIn(("set_time", 33), self.link.log)
        self.panel.lane_release()

    def test_a_lanes_middle_scrub_moves_the_timeline_s_playhead(self):
        row = self.panel.column.layout_().row_at(0, 0)
        t = self.panel._track()
        self.panel.lane_press(t.x(25) + 1, row[1] + 10, middle=True)
        self.assertEqual(self.strip.state["now"], 25)
        self.assertIn(("scrub_only", 25), self.link.log)
        self.panel.lane_release()

    def test_a_timeline_scrub_repaints_the_lanes_playhead(self):
        E, Qt = QT.QtCore.QEvent, QT.QtCore.Qt
        painted = []
        self.panel.lanes.repaint = lambda *a: painted.append(1)
        self.mouse(self.tl, E.MouseButtonPress, self.x(50), Qt.LeftButton, Qt.LeftButton)
        self.assertTrue(painted)
        painted[:] = []
        self.mouse(self.tl, E.MouseMove, self.x(52), Qt.NoButton, Qt.LeftButton)
        self.assertTrue(painted)
        self.mouse(self.tl, E.MouseButtonRelease, self.x(52), Qt.LeftButton, Qt.NoButton)


if __name__ == "__main__":
    unittest.main()
