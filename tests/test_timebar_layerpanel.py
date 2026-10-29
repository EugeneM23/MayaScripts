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
        self.members = []               # the layers the selection belongs to
        self.member_calls = []
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

    def members_of(self, names):
        self.member_calls.append(list(names))
        return [n for n in names if n in self.members]

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

    def test_the_weight_key_cell_toggles_a_key(self):
        """2026-10-20: «нельзя проанимировать силу анимационного слоя»."""
        rect = L.row_parts(self.lay.row_at(0, 0), "anim", 1.0)["wkey"]
        self.click(self.col, *self.centre(rect))
        self.assertIn(("toggle_weight_key", "A2"), self.link.log)
        self.assertNotIn("begin_weight", [e[0] for e in self.link.log])

    def test_the_cell_follows_the_frame(self):
        self.link.anim[0]["weight_keys"] = (30.0,)
        self.panel.refresh(force=True)
        self.assertEqual(self.panel.weight_states()[0], "onkey")
        img = QT.QtGui.QImage(self.col.size(), QT.QtGui.QImage.Format_ARGB32)
        self.col.render(img)
        self.assertFalse(self.col._failed)
        painted = []
        self.col.repaint = lambda: painted.append(1)
        self.panel.on_time()
        self.assertFalse(painted, "the same frame: the cell stands")
        self.panel.strip.now = lambda: 12.0
        self.assertEqual(self.panel.weight_states()[0], "keyed")
        self.panel.on_time()
        self.assertTrue(painted, "off the key: the column drawn again")

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
                          "Remove selection", "Merge selected", "Merge down", "Delete"])
        merge = [r for r in rows if r and r[0] == "Merge selected"][0]
        self.assertIsNone(merge[1])          # one layer selected: nothing to merge


    def ctrl_click(self, i, mods):
        E, Qt = QT.QtCore.QEvent, QT.QtCore.Qt
        x, y = self.centre(L.row_parts(self.lay.row_at(i, 0), "anim", 1.0)["name"])
        for kind, held in ((E.MouseButtonPress, Qt.LeftButton), (E.MouseButtonRelease, Qt.NoButton)):
            p = QT.QtCore.QPointF(x, y)
            ev = QT.QtGui.QMouseEvent(kind, p, QT.QtCore.QPointF(self.col.mapToGlobal(p.toPoint())),
                                      Qt.LeftButton, held, mods)
            QT.QtWidgets.QApplication.sendEvent(self.col, ev)

    def test_ctrl_click_adds_a_layer_to_maya_s_selection(self):
        self.ctrl_click(2, QT.QtCore.Qt.ControlModifier)
        self.assertIn(("select_layers", ["A2", "Base"], "Base"), self.link.log)

    def test_shift_click_selects_the_range(self):
        self.ctrl_click(0, QT.QtCore.Qt.NoModifier)
        self.ctrl_click(2, QT.QtCore.Qt.ShiftModifier)
        self.assertIn(("select_layers", ["A2", "A1", "Base"], "Base"), self.link.log)

    def test_merge_with_two_selected_is_merge_selected(self):
        self.link.anim[1]["selected"] = True
        self.panel.refresh(force=True)
        self.lay = self.col.layout_()
        rect = dict(self.lay.foot)["merge"]
        self.click(self.col, *self.centre(rect))
        self.assertIn(("merge_selected", ["A2", "A1"]), self.link.log)
        rows = self.panel.row_menu(0)
        merge = [r for r in rows if r and r[0] == "Merge selected"][0]
        merge[1]()
        self.assertEqual(self.link.log[-1], ("merge_selected", ["A2", "A1"]))

    def test_every_selected_layer_wears_the_accent_frame(self):
        self.link.anim[1]["selected"] = True
        self.panel.refresh(force=True)
        img = QT.QtGui.QImage(self.col.size(), QT.QtGui.QImage.Format_ARGB32)
        img.fill(0)
        self.col.render(img)
        accent = QT.QtGui.QColor(maya_hubstyle.TOKENS["accent"])

        def framed(i):
            x, y, w, h = self.col.layout_().row_at(i, 0)
            c = img.pixelColor(int(x), int(y + h / 2))
            return abs(c.red() - accent.red()) < 40 and abs(c.green() - accent.green()) < 40
        self.assertTrue(framed(0) and framed(1))
        self.assertFalse(framed(2))

    def test_a_ctrl_pick_stays_framed_when_maya_folds_the_selection_to_one(self):
        self.ctrl_click(1, QT.QtCore.Qt.ControlModifier)      # the fake link leaves Maya's rows as they were
        self.assertEqual(self.panel.selected_names(), ["A2", "A1"])
        img = QT.QtGui.QImage(self.col.size(), QT.QtGui.QImage.Format_ARGB32)
        img.fill(0)
        self.col.render(img)
        accent = QT.QtGui.QColor(maya_hubstyle.TOKENS["accent"])
        x, y, w, h = self.col.layout_().row_at(1, 0)
        c = img.pixelColor(int(x), int(y + h / 2))
        self.assertTrue(abs(c.red() - accent.red()) < 40 and abs(c.green() - accent.green()) < 40)
        rect = dict(self.col.layout_().foot)["merge"]
        self.click(self.col, *self.centre(rect))
        self.assertIn(("merge_selected", ["A2", "A1"]), self.link.log)

    def test_a_plain_click_ends_the_ctrl_pick(self):
        self.ctrl_click(1, QT.QtCore.Qt.ControlModifier)
        self.ctrl_click(2, QT.QtCore.Qt.NoModifier)
        self.assertEqual(self.panel.selected_names(), ["Base"])

    def test_merge_with_one_selected_is_merge_down(self):
        rect = dict(self.lay.foot)["merge"]
        self.click(self.col, *self.centre(rect))
        self.assertIn(("merge_down", "A2"), self.link.log)


class Members(Presses):
    """The layers the selection belongs to read green (2026-10-29: «Когда мы выделяем
    объект или группу объектов давай будем подсвечивать зелененьким имена анимационных
    слоев которым он пренадлежит»)."""

    def setUp(self):
        super(Members, self).setUp()
        del self.link.member_calls[:]

    def image(self):
        img = QT.QtGui.QImage(self.col.size(), QT.QtGui.QImage.Format_ARGB32)
        img.fill(0)
        self.col.render(img)
        return img

    def green_name(self, img, i):
        """Is row `i`'s name green ink? `ok` is (143, 209, 154); the card, the plain
        text, the accent and the strike-through all read green no higher than red."""
        x, y, w, h = L.row_parts(self.lay.row_at(i, 0), "anim", 1.0, base=self.lay.bases[i])["name"]
        for px in range(int(x), int(x + w)):
            for py in range(int(y), int(y + h)):
                c = img.pixelColor(px, py)
                if c.green() > c.red() + 10 and c.green() > c.blue() + 10:
                    return True
        return False

    def test_a_layer_the_selection_belongs_to_reads_green(self):
        self.link.members = ["A1"]              # muted: dimmed, and still green
        self.panel.refresh(keys=True)
        img = self.image()
        self.assertTrue(self.green_name(img, 1))
        self.assertFalse(self.green_name(img, 0))
        self.assertFalse(self.green_name(img, 2))

    def test_the_active_layer_reads_green_too_when_it_holds_the_selection(self):
        self.link.members = ["A2", "Base"]
        self.panel.refresh(keys=True)
        img = self.image()
        self.assertTrue(self.green_name(img, 0))        # A2 is the active row
        self.assertTrue(self.green_name(img, 2))
        self.assertFalse(self.green_name(img, 1))

    def test_nothing_selected_no_green_name(self):
        self.panel.refresh(keys=True)
        self.assertEqual(self.panel.members, frozenset())
        img = self.image()
        self.assertFalse(any(self.green_name(img, i) for i in range(3)))

    def test_they_are_read_with_the_keys_never_on_a_plain_tick(self):
        self.panel.refresh()
        self.assertEqual(self.link.member_calls, [])
        self.panel.refresh(keys=True)
        self.assertEqual(self.link.member_calls, [["A2", "A1", "Base"]])

    def test_new_rows_read_them(self):
        self.link.anim.insert(0, dict(self.link.anim[0], name="A3", label="A3"))
        self.panel.refresh()
        self.assertEqual(self.link.member_calls, [["A3", "A2", "A1", "Base"]])

    def test_the_display_tab_drops_them_and_the_animation_tab_reads_again(self):
        self.link.members = ["A1"]
        self.panel.refresh(keys=True)
        self.assertEqual(self.panel.members, frozenset(["A1"]))
        self.click(self.col, *self.centre(self.lay.segments["disp"]))
        self.assertEqual(self.panel.members, frozenset())
        self.panel.refresh(keys=True)
        self.assertEqual(self.panel.members, frozenset())
        self.click(self.col, *self.centre(self.lay.segments["anim"]))
        self.assertEqual(self.panel.members, frozenset(["A1"]))

    def test_an_open_panel_reads_them_at_once(self):
        self.panel.close()
        self.link.members = ["A1"]
        del self.link.member_calls[:]
        self.panel.open((1300, 815))
        self.assertEqual(self.panel.members, frozenset(["A1"]))

    def test_a_closed_panel_reads_nothing(self):
        self.panel.close()
        self.panel.refresh(keys=True)
        self.assertEqual(self.link.member_calls, [])


class LaneStrip(FakeStrip):

    quiets = 0

    def quiet_keys(self):
        self.quiets += 1

    def track(self):
        from maya_timebar import look
        return look.Track(0, 99, 0, 1000, cells=True)        # 10 px a frame


@unittest.skipIf(QT is None, "no Qt")
class Lanes(unittest.TestCase):
    """The lanes as a dope sheet of the layers (2026-10-19)."""

    def setUp(self):
        from maya_timebar import layerpanel
        self.app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])
        self.link = FakeLink()
        self.link.opts = {"skeldarTimeBarLayerLanes": 1}
        self.panel = layerpanel.Panel(LaneStrip(), self.link, 1.0, maya_hubstyle.TOKENS, False)
        self.addCleanup(self.panel.destroy)
        self.panel.open((1300, 815))
        self.lay = self.panel.column.layout_()
        self.y = [self.lay.row_at(i, 0)[1] + 10 for i in range(3)]

    def send(self, kind, x, y, button, held, mods=None):
        E, Qt = QT.QtCore.QEvent, QT.QtCore.Qt
        w = self.panel.lanes
        p = QT.QtCore.QPointF(x, y)
        ev = QT.QtGui.QMouseEvent(getattr(E, kind), p, QT.QtCore.QPointF(w.mapToGlobal(p.toPoint())),
                                  button, held, mods if mods is not None else Qt.NoModifier)
        QT.QtWidgets.QApplication.sendEvent(w, ev)

    def drag(self, x0, y0, x1, y1, mods=None, button=None):
        Qt = QT.QtCore.Qt
        button = button or Qt.LeftButton
        self.send("MouseButtonPress", x0, y0, button, button, mods)
        self.send("MouseMove", x1, y1, Qt.NoButton, button, mods)
        QT.QtWidgets.QApplication.processEvents()      # a real drag's turn: the scene's step
        self.send("MouseButtonRelease", x1, y1, button, Qt.NoButton, mods)

    def test_moves_with_no_turn_between_make_one_step_to_the_newest(self):
        # 2026-10-20: the lanes drawn at once, the scene following once, to the newest target
        Qt = QT.QtCore.Qt
        self.panel.lane_sel = {"a": 10, "b": 20, "names": ["A2"]}
        self.send("MouseButtonPress", 155, self.y[0], Qt.LeftButton, Qt.LeftButton)
        for x in (185, 215, 255):
            self.send("MouseMove", x, self.y[0], Qt.NoButton, Qt.LeftButton)
        self.assertNotIn("lane_live_to", [e[0] for e in self.link.log])
        self.assertEqual(self.panel.lane_preview, (20, 30))
        QT.QtWidgets.QApplication.processEvents()
        self.assertEqual([e for e in self.link.log if e[0] == "lane_live_to"], [("lane_live_to", (20, 30))])
        self.send("MouseButtonRelease", 255, self.y[0], Qt.LeftButton, Qt.NoButton)
        self.assertIn(("lane_live_end", (20, 30)), self.link.log)

    def test_a_lane_highlight_shows_its_first_and_last_frame(self):
        """2026-10-20: the frame numbers at the block's edges, on its top lane (not
        over the ruler, where the playhead's flag is)."""
        from maya_timebar import bar
        blue = QT.QtGui.QColor(bar.HIGHLIGHT)

        def pills(sel):
            self.panel.lane_sel = sel
            img = QT.QtGui.QImage(self.panel.lanes.size(), QT.QtGui.QImage.Format_ARGB32)
            img.fill(0)
            self.panel.lanes.render(img)
            y = int(self.lay.row_at(0, 0)[1] + 8)
            return [x for x in range(img.width())
                    if all(abs(a - b) < 12 for a, b in ((img.pixelColor(x, y).red(), blue.red()),
                                                         (img.pixelColor(x, y).green(), blue.green()),
                                                         (img.pixelColor(x, y).blue(), blue.blue())))]
        self.assertFalse(pills(None))
        t = LaneStrip().track()
        xs = pills({"a": 10, "b": 40, "names": ["A2"]})
        self.assertTrue([x for x in xs if t.x(10) <= x < t.x(10) + 30], "the start label")
        self.assertTrue([x for x in xs if t.end(40) - 30 < x <= t.end(40)], "the end label")
        head = int(self.lay.head[1] + 6)
        img = QT.QtGui.QImage(self.panel.lanes.size(), QT.QtGui.QImage.Format_ARGB32)
        img.fill(0)
        self.panel.lanes.render(img)
        self.assertFalse([x for x in range(img.width())
                          if abs(img.pixelColor(x, head).blue() - blue.blue()) < 12
                          and abs(img.pixelColor(x, head).red() - blue.red()) < 12], "nothing over the ruler")

    def test_a_layer_s_weight_keys_are_marked_l_on_its_lane(self):
        """2026-10-20: «ключик в котором проанимирован слой будем отмечать буквой L»."""
        from maya_hubstyle import TOKENS
        mark = QT.QtGui.QColor(TOKENS["accent_text"])

        def marked(x0, x1, y):
            img = QT.QtGui.QImage(self.panel.lanes.size(), QT.QtGui.QImage.Format_ARGB32)
            img.fill(0)
            self.panel.lanes.render(img)
            return [x for x in range(x0, x1)
                    if all(abs(a - b) < 12 for a, b in ((img.pixelColor(x, y).red(), mark.red()),
                                                         (img.pixelColor(x, y).green(), mark.green()),
                                                         (img.pixelColor(x, y).blue(), mark.blue())))]
        y = int(self.y[0] + 2)
        self.assertFalse(marked(495, 515, y))
        self.link.anim[0]["weight_keys"] = (50.0,)
        self.panel.refresh(force=True)
        self.assertTrue(marked(495, 515, y))
        self.assertFalse(self.panel.lanes._failed)

    def test_the_lanes_are_shown(self):
        self.assertTrue(self.panel.lanes.isVisible())

    def test_a_press_scrubs_and_picks_the_lane_s_layer(self):
        self.drag(205, self.y[1], 305, self.y[1])
        names = [e[0] for e in self.link.log]
        self.assertIn(("pick", "A1"), self.link.log)
        self.assertIn(("set_time", 20), self.link.log)
        self.assertIn(("set_time", 30), self.link.log)
        self.assertEqual(names[-1], "end_scrub")
        self.assertIn("begin_scrub", names)

    def test_a_middle_drag_scrubs_without_update(self):
        Qt = QT.QtCore.Qt
        self.drag(205, self.y[0], 305, self.y[0], button=Qt.MiddleButton)
        self.assertIn(("scrub_only", 30), self.link.log)
        self.assertNotIn("set_time", [e[0] for e in self.link.log])

    def test_shift_drag_highlights_across_lanes(self):
        Qt = QT.QtCore.Qt
        self.drag(105, self.y[0], 405, self.y[2], mods=Qt.ShiftModifier)
        self.assertEqual(self.panel.lane_sel, {"a": 10, "b": 40, "names": ["A2", "A1", "Base"]})

    def test_the_highlight_body_moves_those_layers_keys(self):
        self.panel.lane_sel = {"a": 10, "b": 20, "names": ["A2", "A1"]}
        self.drag(155, self.y[0], 255, self.y[0])
        self.assertEqual(self.link.log[:3], [("lane_live_begin", ["A2", "A1"], (10, 20)),
                                             ("lane_live_to", (20, 30)), ("lane_live_end", (20, 30))])
        self.assertEqual(self.panel.lane_sel, {"a": 20, "b": 30, "names": ["A2", "A1"]})

    def test_an_edge_scales(self):
        self.panel.lane_sel = {"a": 10, "b": 20, "names": ["A2"]}
        self.drag(210, self.y[0], 310, self.y[0])               # the right edge: frame 20's cell ends at x 210
        self.assertIn(("lane_live_to", (10, 30)), self.link.log)
        self.assertIn(("lane_live_end", (10, 30)), self.link.log)

    def test_a_press_off_the_highlight_clears_it(self):
        self.panel.lane_sel = {"a": 10, "b": 20, "names": ["A2"]}
        self.drag(605, self.y[0], 605, self.y[0])
        self.assertIsNone(self.panel.lane_sel)

    def test_a_double_click_highlights_every_key_of_the_lane(self):
        Qt = QT.QtCore.Qt
        self.send("MouseButtonDblClick", 505, self.y[1], Qt.LeftButton, Qt.LeftButton)
        self.assertEqual(self.panel.lane_sel, {"a": 0, "b": 10, "names": ["A1"]})

    def test_the_key_menu_acts_on_the_highlighted_lanes(self):
        self.panel.lane_sel = {"a": 10, "b": 20, "names": ["A2", "A1"]}
        rows = dict((r[0], r[1]) for r in self.panel.lane_menu(self.y[0]) if r)
        for label in ("Breakdown", "Cut", "Copy", "Paste", "Delete", "Tangents", "Snap",
                      "Highlight all keys", "Clear highlight", "Set key on A2"):
            self.assertIn(label, rows)
        rows["Delete"]()
        self.assertEqual(self.link.log[-1], ("lane_keys", "delete", ["A2", "A1"], (10, 20), 30.0, None))
        dict((r[0], r[1]) for r in rows["Tangents"])["Linear"]()
        self.assertEqual(self.link.log[-1][:2], ("lane_keys", "tangents"))
        self.assertEqual(self.link.log[-1][-1], "linear")
        rows["Set key on A2"]()
        self.assertEqual(self.link.log[-1], ("lane_set_key", "A2"))

    def test_without_a_highlight_the_menu_acts_on_the_lane_at_the_frame(self):
        rows = dict((r[0], r[1]) for r in self.panel.lane_menu(self.y[2]) if r)
        self.assertNotIn("Clear highlight", rows)
        rows["Cut"]()
        self.assertEqual(self.link.log[-1], ("lane_keys", "cut", ["Base"], None, 30.0, None))

    def test_a_key_dragged_alone_moves_without_a_highlight(self):
        #  keys of every lane at 0 and 10 (the fake link); the key at 10 on lane A1
        self.drag(105, self.y[1], 205, self.y[1])
        self.assertEqual(self.link.log[:3], [("lane_live_begin", ["A1"], (10, 10)),
                                             ("lane_live_to", (20, 20)), ("lane_live_end", (20, 20))])
        self.assertIsNone(self.panel.lane_sel)

    def test_a_key_clicked_not_dragged_sends_the_time(self):
        Qt = QT.QtCore.Qt
        self.send("MouseButtonPress", 105, self.y[1], Qt.LeftButton, Qt.LeftButton)
        self.send("MouseButtonRelease", 105, self.y[1], Qt.LeftButton, Qt.NoButton)
        self.assertIn(("set_time", 10), self.link.log)

    def test_s_during_a_key_drag_puts_a_copy_down(self):
        Qt, E = QT.QtCore.Qt, QT.QtCore.QEvent
        self.panel.lane_sel = {"a": 10, "b": 20, "names": ["A2"]}
        self.send("MouseButtonPress", 155, self.y[0], Qt.LeftButton, Qt.LeftButton)
        self.send("MouseMove", 255, self.y[0], Qt.NoButton, Qt.LeftButton)
        ev = QT.QtGui.QKeyEvent(E.KeyPress, Qt.Key_S, Qt.NoModifier, "s")
        QT.QtWidgets.QApplication.sendEvent(self.panel.lanes, ev)
        self.assertIn(("lane_live_stamp",), self.link.log)
        self.send("MouseButtonRelease", 255, self.y[0], Qt.LeftButton, Qt.NoButton)

    def test_the_copy_s_puts_down_is_drawn_before_the_release(self):
        # 2026-10-19: «проставленный ключик не будет отрисовываться пока не отпустить клавишу мышки»
        Qt, E = QT.QtCore.Qt, QT.QtCore.QEvent
        self.link.lane_live_stamp = lambda: {"c": {"keys": [(10.0, {})], "stamped": {20.0}}}
        self.drag_held = None
        self.send("MouseButtonPress", 105, self.y[1], Qt.LeftButton, Qt.LeftButton)   # the key at 10 on A1
        self.send("MouseMove", 205, self.y[1], Qt.NoButton, Qt.LeftButton)
        ev = QT.QtGui.QKeyEvent(E.KeyPress, Qt.Key_S, Qt.NoModifier, "s")
        QT.QtWidgets.QApplication.sendEvent(self.panel.lanes, ev)
        self.assertIn(20.0, self.panel.keys["A1"], "the copy is on the lane while the button is held")
        self.assertNotIn(20.0, self.panel.keys["A2"], "only on the lane the key came from")
        img = QT.QtGui.QImage(self.panel.lanes.size(), QT.QtGui.QImage.Format_ARGB32)
        img.fill(0)
        self.panel.lanes.render(img)
        t = LaneStrip().track()
        x0, x1 = t.cell(20)
        row = self.panel.column.layout_().row_at(1, 0)
        ink = [img.pixelColor(int(x), int(row[1] + row[3] / 2)) for x in range(int(x0), int(x1))]
        self.assertTrue(any(c.red() > 0x40 for c in ink), "a key drawn in frame 20's cell")
        self.send("MouseButtonRelease", 205, self.y[1], Qt.LeftButton, Qt.NoButton)

    def test_s_during_a_scrub_keys_the_active_layer(self):
        Qt, E = QT.QtCore.Qt, QT.QtCore.QEvent
        self.send("MouseButtonPress", 305, self.y[0], Qt.LeftButton, Qt.LeftButton)
        ev = QT.QtGui.QKeyEvent(E.KeyPress, Qt.Key_S, Qt.NoModifier, "s")
        QT.QtWidgets.QApplication.sendEvent(self.panel.lanes, ev)
        self.send("MouseButtonRelease", 305, self.y[0], Qt.LeftButton, Qt.NoButton)
        self.assertIn(("lane_set_key", "A2"), self.link.log)

    def test_s_over_a_lane_block_keys_every_frame_of_it(self):
        # 2026-10-19: «При выделении массива не работает проставление ключей как на таймлайне»
        Qt, E = QT.QtCore.Qt, QT.QtCore.QEvent
        self.panel.lane_sel = {"a": 10, "b": 20, "names": ["A2", "A1"]}
        ev = QT.QtGui.QKeyEvent(E.KeyPress, Qt.Key_S, Qt.NoModifier, "s")
        QT.QtWidgets.QApplication.sendEvent(self.panel.lanes, ev)
        self.assertIn(("lane_key_range", ["A2", "A1"], 10, 20), self.link.log)

    def test_s_over_a_one_frame_block_on_several_lanes_keys_each_lane(self):
        # 2026-10-20: «при груповом выделении сразу на нескольких таймлайнах сейчас не
        # работает проставление ключей через хоткей s»
        Qt, E = QT.QtCore.Qt, QT.QtCore.QEvent
        self.panel.lane_sel = {"a": 12, "b": 12, "names": ["A2", "A1"]}
        override = QT.QtGui.QKeyEvent(E.ShortcutOverride, Qt.Key_S, Qt.NoModifier, "s")
        override.ignore()
        QT.QtWidgets.QApplication.sendEvent(self.panel.lanes, override)
        self.assertTrue(override.isAccepted(), "Maya's S must not fire")
        ev = QT.QtGui.QKeyEvent(E.KeyPress, Qt.Key_S, Qt.NoModifier, "s")
        QT.QtWidgets.QApplication.sendEvent(self.panel.lanes, ev)
        self.assertIn(("lane_key_range", ["A2", "A1"], 12, 12), self.link.log)

    def test_s_over_a_one_frame_lane_block_is_maya_s(self):
        Qt, E = QT.QtCore.Qt, QT.QtCore.QEvent
        self.panel.lane_sel = {"a": 10, "b": 10, "names": ["A2"]}
        ev = QT.QtGui.QKeyEvent(E.KeyPress, Qt.Key_S, Qt.NoModifier, "s")
        QT.QtWidgets.QApplication.sendEvent(self.panel.lanes, ev)
        self.assertNotIn("lane_key_range", [e[0] for e in self.link.log])

    def test_s_with_no_drag_is_maya_s(self):
        Qt, E = QT.QtCore.Qt, QT.QtCore.QEvent
        ev = QT.QtGui.QKeyEvent(E.KeyPress, Qt.Key_S, Qt.NoModifier, "s")
        QT.QtWidgets.QApplication.sendEvent(self.panel.lanes, ev)
        self.assertNotIn("lane_live_stamp", [e[0] for e in self.link.log])

    def test_the_key_under_the_mouse_lifts(self):
        Qt = QT.QtCore.Qt
        self.send("MouseMove", 104, self.y[1], Qt.NoButton, Qt.NoButton)
        self.assertEqual(self.panel.lane_aimed, ("A1", 10.0))
        self.assertEqual(self.panel.lanes.cursor().shape(), Qt.OpenHandCursor)
        self.panel.lanes.repaint()
        self.assertFalse(self.panel.lanes._failed)
        self.send("MouseMove", 555, self.y[1], Qt.NoButton, Qt.NoButton)
        self.assertIsNone(self.panel.lane_aimed)

    def test_a_key_move_on_the_lanes_quiets_the_strip_s_effects(self):
        # 2026-10-19: «при переносе ключей по слоям ... эффекты разрушения ключа и вспышек не
        # должны отыгрываться»
        self.drag(105, self.y[1], 205, self.y[1])                 # a key dragged alone
        self.assertEqual(self.panel.strip.quiets, 1)
        self.panel.lane_sel = {"a": 10, "b": 20, "names": ["A2"]}
        self.drag(155, self.y[0], 255, self.y[0])                 # the highlight's body
        self.assertEqual(self.panel.strip.quiets, 2)

    def test_the_lanes_read_no_keys_while_they_drag_keys(self):
        # 2026-10-19: «Ключи мигают при переносе по выдвижной панели» - a read mid-drag took
        # the keys already moved in the scene and the preview moved them again
        reads = []
        keys_by_layer = self.link.keys_by_layer
        self.link.keys_by_layer = lambda names: reads.append(names) or keys_by_layer(names)
        Qt = QT.QtCore.Qt
        self.panel.lane_sel = {"a": 10, "b": 20, "names": ["A2"]}
        self.send("MouseButtonPress", 155, self.y[0], Qt.LeftButton, Qt.LeftButton)
        self.send("MouseMove", 255, self.y[0], Qt.NoButton, Qt.LeftButton)
        self.panel.keys_dirty()                       # Maya's key-edit callback mid-drag
        self.panel.refresh(keys=True)
        self.assertEqual(reads, [], "drawn from the keys read before the drag")
        self.send("MouseButtonRelease", 255, self.y[0], Qt.LeftButton, Qt.NoButton)
        self.assertTrue(reads, "read again on the release")

    def test_a_key_pressed_but_not_yet_dragged_reads_no_keys_either(self):
        reads = []
        self.link.keys_by_layer = lambda names: reads.append(names) or {}
        Qt = QT.QtCore.Qt
        self.send("MouseButtonPress", 105, self.y[1], Qt.LeftButton, Qt.LeftButton)
        self.panel.refresh(keys=True)
        self.assertEqual(reads, [])
        self.send("MouseButtonRelease", 105, self.y[1], Qt.LeftButton, Qt.NoButton)

    def test_a_scrub_on_the_lanes_does_not_quiet_them(self):
        self.drag(305, self.y[0], 405, self.y[0])
        self.assertEqual(self.panel.strip.quiets, 0)

    def ink_at(self, frame, row=1):
        """Whether frame `frame`'s cell on lane `row` holds a key's ink now."""
        img = QT.QtGui.QImage(self.panel.lanes.size(), QT.QtGui.QImage.Format_ARGB32)
        img.fill(0)
        self.panel.lanes.render(img)
        x0, x1 = LaneStrip().track().cell(frame)
        r = self.panel.column.layout_().row_at(row, 0)
        return any(img.pixelColor(x, int(r[1] + r[3] / 2)).red() > 0x40 for x in range(int(x0) + 2, int(x1) - 1))

    def test_a_drag_step_does_not_draw_the_still_picture_again(self):
        # 2026-10-19: «очень сильно проседает быстродействие когда мы перетаскиваем ключи» -
        # every mouse move drew every lane's every key again (93 ms a step on 12 x 200 keys)
        Qt = QT.QtCore.Qt
        self.panel.lane_sel = {"a": 10, "b": 20, "names": ["A2"]}
        self.send("MouseButtonPress", 155, self.y[0], Qt.LeftButton, Qt.LeftButton)
        self.send("MouseMove", 175, self.y[0], Qt.NoButton, Qt.LeftButton)
        self.panel.lanes.repaint()
        first = self.panel.lanes.rebuilds
        for x in range(185, 405, 10):
            self.send("MouseMove", x, self.y[0], Qt.NoButton, Qt.LeftButton)
            self.panel.lanes.repaint()
        self.assertEqual(self.panel.lanes.rebuilds, first, "the dragged keys are drawn over the still picture")
        self.send("MouseButtonRelease", 395, self.y[0], Qt.LeftButton, Qt.NoButton)

    def test_the_dragged_key_is_drawn_where_the_drag_has_it_not_where_it_was(self):
        Qt = QT.QtCore.Qt
        self.send("MouseButtonPress", 105, self.y[1], Qt.LeftButton, Qt.LeftButton)   # the key at 10 on A1
        self.send("MouseMove", 305, self.y[1], Qt.NoButton, Qt.LeftButton)
        self.assertTrue(self.ink_at(30))
        self.assertFalse(self.ink_at(10))
        self.send("MouseButtonRelease", 305, self.y[1], Qt.LeftButton, Qt.NoButton)

    def test_on_the_release_the_key_never_shows_at_its_old_place(self):
        # 2026-10-19: «после перетягивания когда отпускаем ключик то сперва мигает изображение
        # там где он был потом он ставится где должен»: the preview was cleared before the keys
        # were read again, and Maya's time callback repaints the lanes at once in between
        Qt = QT.QtCore.Qt
        seen = []
        link = self.link

        def live_end(target=None):
            seen.append(self.ink_at(10))                 # a paint inside the release, before the read
            link.keys_by_layer = lambda names: dict((n, [0.0, 30.0] if n == "A1" else [0.0, 10.0]) for n in names)
            return True, ""
        link.lane_live_end = live_end
        self.send("MouseButtonPress", 105, self.y[1], Qt.LeftButton, Qt.LeftButton)
        self.send("MouseMove", 305, self.y[1], Qt.NoButton, Qt.LeftButton)
        QT.QtWidgets.QApplication.processEvents()      # the scene's step
        self.send("MouseButtonRelease", 305, self.y[1], Qt.LeftButton, Qt.NoButton)
        self.assertEqual(seen, [False], "no key at its old place while the release sets it down")
        self.assertFalse(self.ink_at(10))
        self.assertTrue(self.ink_at(30))

    def test_after_the_release_the_key_aimed_at_the_press_is_not_lit_there(self):
        # 2026-10-20: «в момент отпускания мышки в том месте где мы его взяли на пару кадров
        # появится изображение ключа»: the key under the mouse when the drag began stayed
        # aimed, and its lifted picture came back at the old frame once the drag ended -
        # until the next mouse move aimed again
        Qt = QT.QtCore.Qt
        link = self.link

        def live_end(target=None):
            link.keys_by_layer = lambda names: dict((n, [0.0, 30.0] if n == "A1" else [0.0, 10.0]) for n in names)
            return True, ""
        link.lane_live_end = live_end
        self.send("MouseMove", 105, self.y[1], Qt.NoButton, Qt.NoButton)        # hover: aims the key at 10
        self.assertIsNotNone(self.panel.lane_aimed)
        self.send("MouseButtonPress", 105, self.y[1], Qt.LeftButton, Qt.LeftButton)
        self.send("MouseMove", 305, self.y[1], Qt.NoButton, Qt.LeftButton)
        QT.QtWidgets.QApplication.processEvents()
        self.send("MouseButtonRelease", 305, self.y[1], Qt.LeftButton, Qt.NoButton)
        self.assertFalse(self.ink_at(10), "no key lit at the frame it was taken from")
        self.assertTrue(self.ink_at(30))

    def test_it_paints_the_highlight_and_a_preview(self):
        self.panel.lane_sel = {"a": 10, "b": 20, "names": ["A2"]}
        self.panel.lane_preview = (30, 40)
        self.panel.lanes.repaint()
        self.assertFalse(self.panel.lanes._failed)


class Reads(Panel):
    """What the panel reads when (2026-10-18 final review): rows on every refresh,
    the lanes' keys only when they can have changed."""

    def setUp(self):
        from maya_timebar import layerpanel
        super(Reads, self).setUp()
        self.link.opts[layerpanel.LANES_VAR] = 1
        self.keys = []
        real = self.link.keys_by_layer
        self.link.keys_by_layer = lambda names: self.keys.append(names) or real(names)
        self.panel.open((1300, 815))
        self.assertTrue(self.panel.lanes.isVisible())
        del self.keys[:]

    def test_a_plain_refresh_reads_no_keys(self):
        self.panel.refresh()
        self.assertEqual(self.keys, [])

    def test_a_keys_refresh_reads_them(self):
        self.panel.refresh(keys=True)
        self.assertEqual(len(self.keys), 1)

    def test_new_rows_read_the_keys(self):
        self.link.anim.insert(0, dict(self.link.anim[0], name="A3", label="A3"))
        self.panel.refresh()
        self.assertEqual(len(self.keys), 1)

    def test_keys_dirty_waits_for_the_next_refresh(self):
        self.panel.keys_dirty()
        self.panel.keys_dirty()
        self.assertEqual(self.keys, [])
        self.panel.refresh()
        self.assertEqual(len(self.keys), 1)
        self.panel.refresh()
        self.assertEqual(len(self.keys), 1)


class DestroyAll(Panel):
    """A rebuild mid-drag (2026-10-18 final review): destroy_all ends the weight drag."""

    def test_destroy_all_ends_a_weight_drag(self):
        from unittest import mock
        from maya_timebar import layerpanel, layerscene
        self.panel.open((1300, 815))
        lay = self.panel.column.layout_()
        rect = L.row_parts(lay.row_at(0, 0), "anim", 1.0)["weight"]
        E, Qt = QT.QtCore.QEvent, QT.QtCore.Qt
        p = QT.QtCore.QPointF(rect[0] + rect[2] * 0.5, rect[1] + 4)
        ev = QT.QtGui.QMouseEvent(E.MouseButtonPress, p, QT.QtCore.QPointF(self.panel.column.mapToGlobal(p.toPoint())),
                                  Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
        QT.QtWidgets.QApplication.sendEvent(self.panel.column, ev)
        self.assertTrue(self.panel.drag)
        with mock.patch.object(layerscene, "end_weight") as ended:
            layerpanel.destroy_all()
        names = [e[0] for e in self.link.log]
        self.assertEqual(names.count("end_weight"), 1)
        self.assertIsNone(self.panel.drag)
        self.assertTrue(ended.called)
        self.assertNotIn(self.panel, layerpanel.live_panels())

    def test_destroy_all_with_no_panel_still_ends_the_chunk(self):
        from unittest import mock
        from maya_timebar import layerpanel, layerscene
        self.panel.destroy()
        with mock.patch.object(layerscene, "end_weight") as ended:
            layerpanel.destroy_all()
        self.assertTrue(ended.called)


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
