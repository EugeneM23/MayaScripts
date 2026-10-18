"""The Time Bar's layer panel offscreen (2026-10-18), on a fake link.
Spec: docs/superpowers/specs/2026-10-18-time-bar-layer-panel-design.md"""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import maya_hubqt
    QT = maya_hubqt.qt()
except Exception:                                            # noqa: BLE001
    QT = None

import maya_hubstyle
from maya_timebar import layerlook as L


class FakeLink(object):

    def __init__(self):
        self.log = []
        self.opts = {}
        self.anim = [
            {"name": "A2", "label": "A2", "mode": "add", "weight": 0.65, "weight_keyed": False, "mute": False,
             "solo": False, "lock": False, "active": True, "base": False},
            {"name": "A1", "label": "A1", "mode": "ovr", "weight": 1.0, "weight_keyed": False, "mute": True,
             "solo": False, "lock": False, "active": False, "base": False},
            {"name": "Base", "label": "BaseAnimation", "mode": "base", "weight": 1.0, "weight_keyed": False,
             "mute": False, "solo": False, "lock": False, "active": False, "base": True}]
        self.disp = [{"name": "lay1", "label": "lay1", "colour": "#7fa9e6", "visible": True, "playback": True, "type": 0}]

    def _w(self, *entry):
        self.log.append(entry)
        return True, ""

    def anim_layers(self):
        return [dict(r) for r in self.anim]

    def display_layers(self):
        return [dict(r) for r in self.disp]

    def keys_by_layer(self, names):
        return {n: [0.0, 10.0] for n in names}

    def pick(self, name):
        for r in self.anim:
            r["active"] = r["name"] == name
        return self._w("pick", name)

    def set_flag(self, name, flag, on):
        next(r for r in self.anim if r["name"] == name)[flag] = on
        return self._w("set_flag", name, flag, on)

    def begin_weight(self):
        self._w("begin_weight")

    def set_weight(self, name, value):
        next(r for r in self.anim if r["name"] == name)["weight"] = value
        return self._w("set_weight", name, value)

    def end_weight(self):
        self._w("end_weight")

    def set_display(self, name, flag, value):
        return self._w("set_display", name, flag, value)

    def create_anim(self):
        return self._w("create_anim")

    def option(self, name, default):
        return self.opts.get(name, default)

    def set_option(self, name, value):
        self.opts[name] = value

    def __getattr__(self, name):            # every other write
        return lambda *a: self._w(name, *a)


class FakeStrip(object):
    """What the panel asks of the strip: where it stands, where its timeline is."""

    def __init__(self):
        self.ui = 1.0

    def strip_rect(self):
        return (0, 800, 1500, 84)

    def timeline_rect(self):
        return (6, 840, 1120, 40)

    def top_room(self):
        return 760

    def track(self):
        from maya_timebar import look
        return look.Track(16, 1116, 0, 95, cells=True)

    def now(self):
        return 30.0


@unittest.skipIf(QT is None, "no Qt")
class Panel(unittest.TestCase):

    motion = False

    def setUp(self):
        from maya_timebar import layerpanel
        self.app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])
        self.link = FakeLink()
        self.panel = layerpanel.Panel(FakeStrip(), self.link, 1.0, maya_hubstyle.TOKENS, self.motion)
        self.addCleanup(self.panel.destroy)

    def click(self, widget, x, y, button=None):
        E, Qt = QT.QtCore.QEvent, QT.QtCore.Qt
        button = button or Qt.LeftButton
        for kind, held in ((E.MouseButtonPress, button), (E.MouseButtonRelease, Qt.NoButton)):
            p = QT.QtCore.QPointF(x, y)
            ev = QT.QtGui.QMouseEvent(kind, p, QT.QtCore.QPointF(widget.mapToGlobal(p.toPoint())), button, held, Qt.NoModifier)
            QT.QtWidgets.QApplication.sendEvent(widget, ev)

    def centre(self, rect):
        return rect[0] + rect[2] / 2.0, rect[1] + rect[3] / 2.0


class Opens(Panel):

    def test_toggle_opens_and_closes_at_once_without_motion(self):
        self.panel.toggle((1300, 815))
        self.assertTrue(self.panel.is_open() and self.panel.column.isVisible())
        g = self.panel.column.geometry()
        self.assertEqual((g.x(), g.y() + g.height()), (1126 + L.SIDE, 800 - L.ABOVE))
        self.assertEqual(g.height(), L.DEFAULT_H)
        self.panel.toggle((1300, 815))
        self.assertFalse(self.panel.is_open() or self.panel.column.isVisible())

    def test_remembered_height_and_tab(self):
        self.link.opts = {"skeldarTimeBarLayersHeight": 400, "skeldarTimeBarLayersTab": "disp"}
        self.panel.open((1300, 815))
        self.assertEqual(self.panel.column.height(), 400)
        self.assertEqual(self.panel.tab, "disp")


class Presses(Panel):

    def setUp(self):
        super(Presses, self).setUp()
        self.panel.open((1300, 815))
        self.col = self.panel.column
        self.lay = self.col.layout_()

    def test_a_row_click_picks_the_layer(self):
        rect = self.lay.row_at(1, 0)
        self.click(self.col, *self.centre(L.row_parts(rect, "anim", 1.0)["name"]))
        self.assertIn(("pick", "A1"), self.link.log)

    def test_mute_solo_lock(self):
        rect = self.lay.row_at(0, 0)
        self.click(self.col, *self.centre(L.row_parts(rect, "anim", 1.0)["mute"]))
        self.assertIn(("set_flag", "A2", "mute", True), self.link.log)

    def test_a_weight_drag_is_one_chunk(self):
        rect = L.row_parts(self.lay.row_at(0, 0), "anim", 1.0)["weight"]
        self.click(self.col, rect[0] + rect[2] * 0.25, rect[1] + 4)
        names = [e[0] for e in self.link.log]
        self.assertEqual(names[0], "begin_weight")
        self.assertEqual(names[-1], "end_weight")
        self.assertIn("set_weight", names)

    def test_the_tab_switches_and_is_remembered(self):
        self.click(self.col, *self.centre(self.lay.segments["disp"]))
        self.assertEqual(self.panel.tab, "disp")
        self.assertEqual(self.link.opts["skeldarTimeBarLayersTab"], "disp")

    def test_the_grip_resizes_and_is_remembered(self):
        E, Qt = QT.QtCore.QEvent, QT.QtCore.Qt
        y0 = 3
        g0 = self.col.geometry()
        for kind, dy, held in ((E.MouseButtonPress, 0, Qt.LeftButton), (E.MouseMove, -60, Qt.LeftButton),
                               (E.MouseButtonRelease, -60, Qt.NoButton)):
            p = QT.QtCore.QPointF(20, y0 + dy)
            gp = QT.QtCore.QPointF(g0.x() + 20, g0.y() + y0 + dy)
            ev = QT.QtGui.QMouseEvent(kind, p, gp, Qt.LeftButton, held, Qt.NoModifier)
            QT.QtWidgets.QApplication.sendEvent(self.col, ev)
        self.assertEqual(self.col.height(), g0.height() + 60)
        self.assertEqual(self.link.opts["skeldarTimeBarLayersHeight"], g0.height() + 60)
        self.assertEqual(self.col.geometry().bottom(), g0.bottom())

    def test_the_lanes_follow_the_column(self):
        self.click(self.col, *self.centre(self.lay.lanes))
        self.assertTrue(self.panel.lanes.isVisible())
        lg, cg = self.panel.lanes.geometry(), self.col.geometry()
        self.assertEqual((lg.x(), lg.right() + 1, lg.y(), lg.height()), (6, cg.x(), cg.y(), cg.height()))
        self.assertEqual(self.link.opts["skeldarTimeBarLayerLanes"], 1)

    def test_the_foot_presses(self):
        name, rect = self.lay.foot[0]
        self.click(self.col, *self.centre(rect))
        self.assertIn(("create_anim",), self.link.log)

    def test_a_weight_drag_ended_by_close_closes_the_chunk_once(self):
        rect = L.row_parts(self.lay.row_at(0, 0), "anim", 1.0)["weight"]
        E, Qt = QT.QtCore.QEvent, QT.QtCore.Qt
        p = QT.QtCore.QPointF(rect[0] + rect[2] * 0.5, rect[1] + 4)
        ev = QT.QtGui.QMouseEvent(E.MouseButtonPress, p, QT.QtCore.QPointF(self.col.mapToGlobal(p.toPoint())),
                                  Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
        QT.QtWidgets.QApplication.sendEvent(self.col, ev)
        self.panel.close()
        self.panel.destroy()
        names = [e[0] for e in self.link.log]
        self.assertEqual(names.count("begin_weight"), 1)
        self.assertEqual(names.count("end_weight"), 1)
        self.assertEqual(names[-1], "end_weight")

    def test_a_weight_drag_reads_the_scene_once(self):
        rect = L.row_parts(self.lay.row_at(0, 0), "anim", 1.0)["weight"]
        reads = []
        real = self.link.anim_layers
        self.link.anim_layers = lambda: reads.append(1) or real()
        E, Qt = QT.QtCore.QEvent, QT.QtCore.Qt
        for kind, u, held in ((E.MouseButtonPress, 0.2, Qt.LeftButton), (E.MouseMove, 0.4, Qt.LeftButton),
                              (E.MouseMove, 0.6, Qt.LeftButton), (E.MouseButtonRelease, 0.6, Qt.NoButton)):
            p = QT.QtCore.QPointF(rect[0] + rect[2] * u, rect[1] + 4)
            ev = QT.QtGui.QMouseEvent(kind, p, QT.QtCore.QPointF(self.col.mapToGlobal(p.toPoint())),
                                      Qt.LeftButton, held, Qt.NoModifier)
            QT.QtWidgets.QApplication.sendEvent(self.col, ev)
        self.assertEqual(len(reads), 1)
        self.assertAlmostEqual(self.link.anim[0]["weight"], 0.6, places=2)

    def test_a_hover_sweep_draws_the_still_picture_once(self):
        E, Qt = QT.QtCore.QEvent, QT.QtCore.Qt

        def paint():
            img = QT.QtGui.QImage(self.col.size(), QT.QtGui.QImage.Format_ARGB32)
            img.fill(0)
            self.col.render(img)
        paint()
        first = self.col.rebuilds
        for i in range(len(self.lay.rows)):
            for part in ("name", "mute", "solo", "lock"):
                parts = L.row_parts(self.lay.row_at(i, 0), "anim", 1.0, base=self.lay.bases[i])
                if part not in parts:
                    continue
                p = QT.QtCore.QPointF(*self.centre(parts[part]))
                ev = QT.QtGui.QMouseEvent(E.MouseMove, p, QT.QtCore.QPointF(self.col.mapToGlobal(p.toPoint())),
                                          Qt.NoButton, Qt.NoButton, Qt.NoModifier)
                QT.QtWidgets.QApplication.sendEvent(self.col, ev)
                paint()
        self.panel.hover_at(None)
        paint()
        self.assertEqual(self.col.rebuilds, first)

    def test_the_right_button_rows(self):
        rows = self.panel.row_menu(0)
        self.assertEqual([r[0] for r in rows if r],
                         ["Additive", "Override", "Rename", "Select objects", "Add selection",
                          "Remove selection", "Merge down", "Delete"])


class Scaled(Panel):
    """At 150 % the height is logical px x ui, the remembered height logical."""

    def setUp(self):
        from maya_timebar import layerpanel
        self.app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])
        self.link = FakeLink()
        self.panel = layerpanel.Panel(FakeStrip(), self.link, 1.5, maya_hubstyle.TOKENS, False)
        self.addCleanup(self.panel.destroy)

    def test_the_default_height_is_logical(self):
        self.panel.open((1300, 815))
        g = self.panel.column.geometry()
        self.assertEqual(g.height(), int(round(L.DEFAULT_H * 1.5)))
        self.assertEqual(g.y() + g.height(), int(round(800 - L.ABOVE * 1.5)))
        lay = self.panel.column.layout_()
        self.assertEqual(len(self.panel._visible_rows(lay)), 3)
        lg = self.panel.lanes.geometry()
        self.assertEqual((lg.y(), lg.height()), (g.y(), g.height()))      # the lanes level with the rows

    def test_a_grip_drag_stores_logical_px(self):
        self.panel.open((1300, 815))
        col = self.panel.column
        E, Qt = QT.QtCore.QEvent, QT.QtCore.Qt
        g0 = col.geometry()
        for kind, dy, held in ((E.MouseButtonPress, 0, Qt.LeftButton), (E.MouseMove, -60, Qt.LeftButton),
                               (E.MouseButtonRelease, -60, Qt.NoButton)):
            p = QT.QtCore.QPointF(20, 3 + dy)
            gp = QT.QtCore.QPointF(g0.x() + 20, g0.y() + 3 + dy)
            QT.QtWidgets.QApplication.sendEvent(col, QT.QtGui.QMouseEvent(kind, p, gp, Qt.LeftButton, held,
                                                                          Qt.NoModifier))
        self.assertEqual(self.link.opts["skeldarTimeBarLayersHeight"], L.DEFAULT_H + 40)
        self.assertEqual(col.height(), int(round((L.DEFAULT_H + 40) * 1.5)))
        self.assertEqual(col.geometry().bottom(), g0.bottom())


class Motion(Panel):

    motion = True

    def test_mid_open_the_shape_is_small_and_far_pixels_empty(self):
        self.panel.open((1300, 815))
        col = self.panel.column
        self.panel.age_override = 60.0               # ms into the burst
        img = QT.QtGui.QImage(col.size(), QT.QtGui.QImage.Format_ARGB32)
        img.fill(0)
        col.render(img)
        self.assertEqual(img.pixelColor(4, 12).alpha(), 0)      # the far top-left corner: not yet
        self.panel.age_override = None


if __name__ == "__main__":
    unittest.main()
