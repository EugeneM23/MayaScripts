"""The Time Bar's layer panel, the parts its first tests do not reach (2026-10-27):
the burst and its driver, the Display tab, the right-button menus and renaming, the
wheel, the lanes' menu, cursors and edge cases, and every guarded failure. Offscreen
Qt, a fake link and strip, events sent to the panel's own widgets; the burst's clock
is the test's, ticked by hand.

Spec: docs/superpowers/specs/2026-10-18-time-bar-layer-panel-design.md
"""
import contextlib
import io
import os
import sys
import types
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import maya_hubqt
    QT = maya_hubqt.qt()
except Exception:                                            # noqa: BLE001
    QT = None
REAL_QMENU = QT.QtWidgets.QMenu if QT is not None else None     # auto_menu swaps the module's

import maya_hubstyle
from maya_timebar import layerlook as L, look

PANELS = "_skeldar_timebar_layer_panels"


def anim_row(name, **kw):
    row = {"name": name, "label": name, "mode": "add", "weight": 1.0, "weight_keyed": False,
           "mute": False, "solo": False, "lock": False, "active": False, "base": False}
    row.update(kw)
    return row


def disp_row(name, **kw):
    row = {"name": name, "label": name, "colour": "#7fa9e6", "visible": True, "playback": True, "type": 0}
    row.update(kw)
    return row


class FakeLink(object):
    """The panel's road into Maya: every write logged, the rows kept here."""

    def __init__(self):
        self.log = []
        self.opts = {}
        self.answers = {}
        self.anim = [anim_row("A2", weight=0.65, active=True),
                     anim_row("A1", mode="ovr", mute=True),
                     anim_row("Base", label="BaseAnimation", mode="base", base=True)]
        self.disp = [disp_row("lay1"), disp_row("lay2", visible=False, type=1)]
        self.keymap = {}
        self.members = []               # the layers the selection belongs to

    def _w(self, *entry):
        self.log.append(entry)
        return self.answers.get(entry[0], (True, ""))

    def anim_layers(self):
        return [dict(r) for r in self.anim]

    def display_layers(self):
        return [dict(r) for r in self.disp]

    def keys_by_layer(self, names):
        return dict((n, list(self.keymap.get(n, [0.0, 10.0]))) for n in names)

    def pick(self, name):
        for r in self.anim:
            r["active"] = r["name"] == name
        return self._w("pick", name)

    def set_flag(self, name, flag, on):
        next(r for r in self.anim if r["name"] == name)[flag] = on
        return self._w("set_flag", name, flag, on)

    def set_display(self, name, flag, value):
        for r in self.disp:
            if r["name"] == name and flag in r:
                r[flag] = value
        return self._w("set_display", name, flag, value)

    def set_weight(self, name, value):
        next(r for r in self.anim if r["name"] == name)["weight"] = value
        return self._w("set_weight", name, value)

    def delete_anim(self, name):
        self.anim = [r for r in self.anim if r["name"] != name]
        return self._w("delete_anim", name)

    def delete_display(self, name):
        self.disp = [r for r in self.disp if r["name"] != name]
        return self._w("delete_display", name)

    def rename(self, name, text):
        for r in self.anim + self.disp:
            if r["name"] == name:
                r["label"] = text
        return self._w("rename", name, text)

    def members_of(self, names):
        return [n for n in names if n in self.members]

    def display_members_of(self, names):
        return [n for n in names if n in self.members]

    def option(self, name, default):
        return self.opts.get(name, default)

    def set_option(self, name, value):
        self.opts[name] = value

    def __getattr__(self, name):                 # every other write
        if name.startswith("__"):
            raise AttributeError(name)
        return lambda *a: self._w(name, *a)


class Strip(object):
    """Where the panel stands: the strip, its timeline (10 px a frame on the lanes)."""

    def __init__(self):
        self.ui = 1.0
        self.frame = 30.0
        self.trk = look.Track(0, 99, 0, 1000, cells=True)

    def strip_rect(self):
        return (0, 800, 1500, 84)

    def timeline_rect(self):
        return (6, 840, 1120, 40)

    def top_room(self):
        return 760

    def track(self):
        return self.trk

    def now(self):
        return self.frame


def boom(*_a, **_k):
    raise RuntimeError("boom")


def find_action(menu, label):
    #  submenus by the menu's children: QAction.menu() hands back a wrapper that dies with
    #  the temporary it came through, the row found in it with it (PySide6 6.8)
    subs = dict((c.title(), c) for c in menu.children() if isinstance(c, REAL_QMENU))
    for a in menu.actions():
        if a.text() == label:
            return a
        if a.text() in subs:
            found = find_action(subs[a.text()], label)
            if found is not None:
                return found
    return None


@contextlib.contextmanager
def auto_menu(pick=None):
    """QMenu.exec answered at once: the row labelled `pick` (None: dismissed). The menus
    shown are yielded."""
    QtWidgets = QT.QtWidgets
    real = QtWidgets.QMenu
    shown = []

    class AutoMenu(real):
        def exec(self, *_args):
            shown.append([a.text() for a in self.actions()])
            return find_action(self, pick) if pick else None

    QtWidgets.QMenu = AutoMenu
    try:
        yield shown
    finally:
        QtWidgets.QMenu = real


@contextlib.contextmanager
def printed():
    """stdout caught (the panel prints a guarded failure's traceback there)."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        yield out


@contextlib.contextmanager
def swapped(obj, name, value):
    own = getattr(obj, "__dict__", {})
    had = name in own
    old = own[name] if had else None              # the raw entry (a class's staticmethod too)
    setattr(obj, name, value)
    try:
        yield
    finally:
        if had:
            setattr(obj, name, old)
        else:
            delattr(obj, name)


@unittest.skipIf(QT is None, "no Qt")
class Base(unittest.TestCase):

    motion = False
    ui = 1.0

    def setUp(self):
        from maya_timebar import layerpanel
        self.mod = layerpanel
        self.app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])
        had = hasattr(sys, PANELS)
        before = list(getattr(sys, PANELS, []))

        def restore():
            if had:
                getattr(sys, PANELS)[:] = before
            elif hasattr(sys, PANELS):
                delattr(sys, PANELS)
        self.addCleanup(restore)
        #  after destroy: the lanes' app-wide key filter goes with the widgets, so a drag a
        #  test left held cannot take a later test's S
        self.addCleanup(QT.QtCore.QCoreApplication.sendPostedEvents, None, QT.QtCore.QEvent.DeferredDelete)
        self.link = FakeLink()
        self.strip = self.make_strip()
        self.panel = layerpanel.Panel(self.strip, self.link, self.ui, maya_hubstyle.TOKENS, self.motion)
        self.addCleanup(self.panel.destroy)

    def make_strip(self):
        return Strip()

    # -- events --------------------------------------------------------------
    def send(self, widget, kind, x, y, button=None, held=None, mods=None):
        E, Qt = QT.QtCore.QEvent, QT.QtCore.Qt
        button = Qt.LeftButton if button is None else button
        if held is None:
            held = Qt.NoButton if kind == "MouseButtonRelease" else button
        p = QT.QtCore.QPointF(x, y)
        ev = QT.QtGui.QMouseEvent(getattr(E, kind), p, QT.QtCore.QPointF(widget.mapToGlobal(p.toPoint())),
                                  button, held, mods if mods is not None else Qt.NoModifier)
        QT.QtWidgets.QApplication.sendEvent(widget, ev)

    def click(self, widget, x, y, button=None, mods=None):
        self.send(widget, "MouseButtonPress", x, y, button, mods=mods)
        self.send(widget, "MouseButtonRelease", x, y, button, mods=mods)

    def plain(self, widget, kind):
        QT.QtWidgets.QApplication.sendEvent(widget, QT.QtCore.QEvent(getattr(QT.QtCore.QEvent, kind)))

    def key(self, widget, key, text=""):
        E, Qt = QT.QtCore.QEvent, QT.QtCore.Qt
        ev = QT.QtGui.QKeyEvent(E.KeyPress, key, Qt.NoModifier, text)
        QT.QtWidgets.QApplication.sendEvent(widget, ev)
        return ev

    def render(self, widget):
        img = QT.QtGui.QImage(widget.size(), QT.QtGui.QImage.Format_ARGB32)
        img.fill(0)
        widget.render(img)
        return img

    @staticmethod
    def centre(rect):
        return rect[0] + rect[2] / 2.0, rect[1] + rect[3] / 2.0

    def part(self, i, name, tab="anim"):
        lay = self.panel.column.layout_()
        return L.row_parts(lay.row_at(i, self.panel.scroll), tab, self.ui, base=lay.bases[i])[name]


class LinkFailures(Base):
    """A link or strip that fails: the default, the traceback, never an exception
    out of a Qt slot."""

    def test_a_failing_option_reads_the_defaults(self):
        self.link.option = boom
        self.panel.open((1300, 815))
        self.assertEqual((self.panel.tab, self.panel.height, self.panel.lanes_on), ("anim", L.DEFAULT_H, False))

    def test_a_height_that_is_no_number_is_the_default(self):
        self.link.opts[self.mod.HEIGHT_VAR] = "tall"
        self.panel.open((1300, 815))
        self.assertEqual(self.panel.height, L.DEFAULT_H)
        self.assertEqual(self.panel.column.height(), L.DEFAULT_H)

    def test_a_failing_set_option_still_switches_the_tab(self):
        self.panel.open((1300, 815))
        self.link.set_option = boom
        with printed() as out:
            self.click(self.panel.column, *self.centre(self.panel.column.layout_().segments["disp"]))
        self.assertEqual(self.panel.tab, "disp")
        self.assertIn("boom", out.getvalue())

    def test_a_failing_read_leaves_no_rows_and_prints(self):
        self.link.anim_layers = boom
        with printed() as out:
            self.panel.open((1300, 815))
        self.assertEqual(self.panel.rows["anim"], [])
        self.assertIn("boom", out.getvalue())
        self.assertIsNone(self.panel.active_name())

    def test_a_write_s_message_goes_on_the_line_and_the_timer_clears_it(self):
        self.panel.open((1300, 815))
        self.link.answers["pick"] = (True, "A1 is the active layer now")
        self.click(self.panel.column, *self.centre(self.part(1, "name")))
        self.assertEqual(self.panel.status, "A1 is the active layer now")
        self.assertTrue(self.panel.status_timer.isActive())
        self.render(self.panel.column)
        self.assertFalse(self.panel.column._failed)
        self.panel.status_timer.timeout.emit()              # the 4 s run out
        self.assertEqual(self.panel.status, "")

    def test_a_strip_holding_the_panel_reads_it_once_for_a_write(self):
        calls = []
        self.strip.refresh = lambda keys=False, force=False: calls.append((keys, force))
        self.strip.layer_panel = self.panel
        self.panel.open((1300, 815))
        reads = []
        real = self.link.anim_layers
        self.link.anim_layers = lambda: reads.append(1) or real()
        self.click(self.panel.column, *self.centre(self.part(1, "name")))
        self.assertEqual(calls, [(True, True)])
        self.assertEqual(reads, [], "the strip's refresh reads the panel, not the write")

    def test_a_failing_strip_refresh_falls_back_to_the_panel_s_own_read(self):
        self.strip.refresh = boom
        self.strip.layer_panel = self.panel
        self.panel.open((1300, 815))
        reads = []
        real = self.link.anim_layers
        self.link.anim_layers = lambda: reads.append(1) or real()
        with printed() as out:
            self.click(self.panel.column, *self.centre(self.part(1, "name")))
        self.assertEqual(len(reads), 1)
        self.assertEqual(out.getvalue().count("RuntimeError: boom"), 2)
        self.assertEqual(self.panel.active_name(), "A1")

    def test_a_failing_strip_stops_the_placer(self):
        self.panel.open((1300, 815))
        self.assertTrue(self.panel.placer.isActive())
        self.strip.strip_rect = boom
        with printed():
            self.panel.placer.timeout.emit()
        self.assertFalse(self.panel.placer.isActive())

    def test_close_with_no_origin_folds_toward_the_column_s_bottom(self):
        self.panel.open((1300, 815))
        self.panel._origin = None
        self.panel.close()
        self.assertFalse(self.panel.is_open() or self.panel.column.isVisible())

    def test_a_failing_paint_prints_once_and_stops(self):
        self.panel.open((1300, 815))
        self.panel.live_units = boom
        with printed() as out:
            self.render(self.panel.column)
            self.render(self.panel.column)
        self.assertTrue(self.panel.column._failed)
        self.assertEqual(out.getvalue().count("RuntimeError: boom"), 1)


class Destroying(Base):

    def test_destroy_all_prints_a_panel_that_fails_and_goes_on(self):
        class Bad(object):
            def destroy(self):
                raise RuntimeError("boom")
        self.mod.live_panels().append(Bad())
        from maya_timebar import layerscene
        with swapped(layerscene, "end_weight", boom), printed() as out:
            self.mod.destroy_all()
        self.assertIn("boom", out.getvalue())
        self.assertEqual(self.mod.live_panels(), [])
        self.assertEqual(self.panel.phase, "closed")

    def test_destroy_all_with_no_qt_stops_after_the_panels(self):
        with swapped(self.mod, "maya_hubqt", types.SimpleNamespace(qt=lambda: None)):
            self.mod.destroy_all()
        self.assertEqual(self.mod.live_panels(), [])

    def test_destroy_twice_after_qt_deleted_its_widgets(self):
        self.panel.open((1300, 815))
        self.panel.destroy()
        QT.QtCore.QCoreApplication.sendPostedEvents(None, QT.QtCore.QEvent.DeferredDelete)
        self.panel.destroy()                       # dead wrappers: RuntimeError swallowed
        self.assertEqual(self.panel.phase, "closed")
        self.assertNotIn(self.panel, self.mod.live_panels())

    def test_a_release_that_fails_in_destroy_is_printed(self):
        self.panel.open((1300, 815))
        rect = self.part(0, "weight")
        self.send(self.panel.column, "MouseButtonPress", rect[0] + rect[2] / 2.0, rect[1] + 4)
        with swapped(self.panel, "release", boom), printed() as out:
            self.panel.destroy()
        self.assertIn("boom", out.getvalue())


class Display(Base):
    """The Display tab: rows, toggles, the foot, the lanes button dimmed."""

    def setUp(self):
        super(Display, self).setUp()
        self.panel.open((1300, 815))
        self.col = self.panel.column
        self.click(self.col, *self.centre(self.col.layout_().segments["disp"]))
        self.assertEqual(self.panel.tab, "disp")

    def test_a_row_click_picks_the_display_layer(self):
        self.click(self.col, *self.centre(self.part(1, "name", "disp")))
        self.assertEqual(self.panel.picked_disp, "lay2")
        self.click(self.col, *self.centre(self.part(0, "swatch", "disp")))
        self.assertEqual(self.panel.picked_disp, "lay1")

    def test_the_toggles_write_visible_playback_and_the_next_type(self):
        for name in ("visible", "playback", "type"):
            self.click(self.col, *self.centre(self.part(1, name, "disp")))
        self.assertIn(("set_display", "lay2", "visible", True), self.link.log)
        self.assertIn(("set_display", "lay2", "playback", False), self.link.log)
        self.assertIn(("set_display", "lay2", "type", 2), self.link.log)

    def test_it_paints_the_rows_and_a_hidden_layer_dimmed(self):
        img = self.render(self.col)
        self.assertFalse(self.col._failed)
        x, y, w, h = self.part(0, "swatch", "disp")
        c = img.pixelColor(int(x + w / 2), int(y + h / 2))
        self.assertEqual(c.name(), "#7fa9e6")
        x, y, w, h = self.part(1, "swatch", "disp")         # lay2: hidden, so dimmed
        self.assertNotEqual(img.pixelColor(int(x + w / 2), int(y + h / 2)).name(), "#7fa9e6")

    def test_the_lanes_button_does_nothing_here(self):
        self.click(self.col, *self.centre(self.col.layout_().lanes))
        self.assertFalse(self.panel.lanes_on)
        self.assertNotIn(self.mod.LANES_VAR, self.link.opts)
        self.render(self.col)
        self.assertFalse(self.col._failed)

    def test_the_foot_adds_and_asks_for_a_pick(self):
        foot = dict(self.col.layout_().foot)
        self.click(self.col, *self.centre(foot["add"]))
        self.assertIn(("create_display",), self.link.log)
        self.click(self.col, *self.centre(foot["select"]))
        self.assertEqual(self.panel.status, "pick a layer first")
        self.click(self.col, *self.centre(self.part(0, "name", "disp")))
        for name, call in (("addsel", "display_add"), ("remsel", "display_remove"), ("select", "display_select")):
            self.click(self.col, *self.centre(foot[name]))
            self.assertIn((call, "lay1"), self.link.log)

    def test_the_foot_delete_takes_the_picked_layer(self):
        import maya_hubsound
        played = []
        with swapped(maya_hubsound, "deleted", lambda: played.append(1)):
            self.click(self.col, *self.centre(self.part(0, "name", "disp")))
            self.click(self.col, *self.centre(dict(self.col.layout_().foot)["delete"]))
        self.assertIn(("delete_display", "lay1"), self.link.log)
        self.assertEqual(played, [1])
        self.assertIsNone(self.panel.picked_disp)
        self.assertEqual(self.panel.ghosts, [], "no motion, no ghost")

    def test_the_right_button_rows(self):
        rows = self.panel.row_menu(0)
        self.assertEqual([r[0] for r in rows if r], ["Rename", "Colour", "Select objects", "Add selection",
                                                     "Remove selection", "Delete"])
        menu = dict((r[0], r[1]) for r in rows if r)
        self.assertEqual(len(menu["Colour"]), 31)
        dict(menu["Colour"])["Colour 3"]()
        self.assertEqual(self.link.log[-1], ("set_display", "lay1", "colour", 3))
        for label, call in (("Select objects", "display_select"), ("Add selection", "display_add"),
                            ("Remove selection", "display_remove")):
            menu[label]()
            self.assertEqual(self.link.log[-1], (call, "lay1"))
        import maya_hubsound
        with swapped(maya_hubsound, "deleted", lambda: None):
            menu["Delete"]()
        self.assertIn(("delete_display", "lay1"), self.link.log)

    def test_back_to_animation_brings_the_lanes_back(self):
        self.panel.lanes_on = True
        self.click(self.col, *self.centre(self.col.layout_().segments["anim"]))
        self.assertTrue(self.panel.lanes.isVisible())
        self.click(self.col, *self.centre(self.col.layout_().segments["anim"]))     # the same tab: nothing
        self.assertEqual(self.panel.tab, "anim")


class Column(Base):
    """The column's own hand: the foot, the menus, renaming, the wheel, the hover."""

    def setUp(self):
        super(Column, self).setUp()
        self.panel.open((1300, 815))
        self.col = self.panel.column

    def foot(self, name):
        return self.centre(dict(self.col.layout_().foot)[name])

    def test_the_anim_foot_acts_on_the_active_layer(self):
        for name, call in (("addsel", "add_selection"), ("remsel", "remove_selection")):
            self.click(self.col, *self.foot(name))
            self.assertIn((call, "A2"), self.link.log)

    def test_the_anim_foot_asks_for_a_pick_with_no_active_layer(self):
        for r in self.link.anim:
            r["active"] = False
        self.panel.refresh(force=True)
        self.click(self.col, *self.foot("addsel"))
        self.assertEqual(self.panel.status, "pick a layer first")
        self.assertNotIn("add_selection", [e[0] for e in self.link.log])

    def test_the_foot_delete_takes_the_active_layer_and_plays_the_sound(self):
        import maya_hubsound
        played = []
        with swapped(maya_hubsound, "deleted", lambda: played.append(1)):
            self.click(self.col, *self.foot("delete"))
        self.assertIn(("delete_anim", "A2"), self.link.log)
        self.assertEqual(played, [1])
        self.assertEqual([r["name"] for r in self.panel.rows["anim"]], ["A1", "Base"])

    def test_a_delete_the_scene_refused_plays_nothing(self):
        import maya_hubsound
        played = []
        self.link.delete_anim = lambda name: self.link._w("delete_anim", name)      # nothing deleted
        with swapped(maya_hubsound, "deleted", lambda: played.append(1)):
            self.click(self.col, *self.foot("delete"))
        self.assertEqual(played, [])

    def test_a_press_on_nothing_does_nothing(self):
        self.click(self.col, 1, self.col.height() / 2.0)
        self.assertEqual(self.link.log, [])

    def test_a_press_past_the_rows_is_ignored(self):
        self.panel._row_press(10, "name", self.col.layout_(), None)
        self.assertEqual(self.link.log, [])
        self.panel.drag_to(10, 10)                          # no drag held: nothing
        self.assertIsNone(self.panel.drag)

    def test_the_lanes_button_turns_them_off_again(self):
        lanes = self.col.layout_().lanes
        self.click(self.col, *self.centre(lanes))
        self.assertTrue(self.panel.lanes.isVisible())
        self.click(self.col, *self.centre(lanes))
        self.assertFalse(self.panel.lanes.isVisible())
        self.assertEqual(self.link.opts[self.mod.LANES_VAR], 0)

    def test_a_grip_drag_moves_the_lanes_too(self):
        self.click(self.col, *self.centre(self.col.layout_().lanes))
        invalid = []
        real = self.panel.lanes.invalidate
        self.panel.lanes.invalidate = lambda: invalid.append(1) or real()
        g0 = self.col.geometry()
        E, Qt = QT.QtCore.QEvent, QT.QtCore.Qt
        for kind, dy, held in ((E.MouseButtonPress, 0, Qt.LeftButton), (E.MouseMove, -40, Qt.LeftButton)):
            p = QT.QtCore.QPointF(20, 3 + dy)
            gp = QT.QtCore.QPointF(g0.x() + 20, g0.y() + 3 + dy)
            QT.QtWidgets.QApplication.sendEvent(self.col, QT.QtGui.QMouseEvent(kind, p, gp, Qt.LeftButton, held,
                                                                               Qt.NoModifier))
        self.assertTrue(invalid)
        self.assertEqual(self.panel.lanes.geometry().height(), self.col.geometry().height())
        self.assertIn(("grip",), self.panel.live_units(self.col.layout_()))
        self.render(self.col)                               # the held grip drawn lit over the picture
        self.assertFalse(self.col._failed)
        self.send(self.col, "MouseButtonRelease", 20, -37)
        self.assertEqual(self.link.opts[self.mod.HEIGHT_VAR], L.DEFAULT_H + 40)

    def test_the_grip_s_cursor_and_its_glow(self):
        self.send(self.col, "MouseMove", 20, 3, QT.QtCore.Qt.NoButton)
        self.assertEqual(self.col.cursor().shape(), QT.QtCore.Qt.SizeVerCursor)
        img = self.render(self.col)
        self.assertFalse(self.col._failed)
        c = img.pixelColor(int(self.col.width() / 2), 4)
        accent = QT.QtGui.QColor(maya_hubstyle.TOKENS["accent"])
        self.assertLess(abs(c.red() - accent.red()) + abs(c.green() - accent.green()), 60)

    def test_hovering_a_foot_button_shows_its_tip_and_delete_goes_red(self):
        self.send(self.col, "MouseMove", *self.foot("delete"), button=QT.QtCore.Qt.NoButton)
        self.assertEqual(self.col.toolTip(), L.FOOT_TIPS["delete"])
        self.assertEqual(self.col.cursor().shape(), QT.QtCore.Qt.PointingHandCursor)
        self.render(self.col)
        self.assertFalse(self.col._failed)
        self.send(self.col, "MouseMove", *self.centre(self.part(0, "name")), button=QT.QtCore.Qt.NoButton)
        self.assertEqual(self.col.toolTip(), "")

    def test_hovering_the_lanes_button_lifts_it(self):
        self.send(self.col, "MouseMove", *self.centre(self.col.layout_().lanes), button=QT.QtCore.Qt.NoButton)
        self.assertEqual(self.panel.hover.get(("lanes",)), 1.0)
        self.assertEqual(self.col.cursor().shape(), QT.QtCore.Qt.PointingHandCursor)
        self.render(self.col)
        self.assertFalse(self.col._failed)

    def test_hovering_the_other_tab_lifts_it(self):
        self.send(self.col, "MouseMove", *self.centre(self.col.layout_().segments["disp"]),
                  button=QT.QtCore.Qt.NoButton)
        self.assertEqual(self.panel.hover.get(("seg", "disp")), 1.0)
        self.render(self.col)
        self.assertFalse(self.col._failed)

    def test_leaving_the_column_drops_the_hover(self):
        self.send(self.col, "MouseMove", *self.centre(self.part(0, "mute")), button=QT.QtCore.Qt.NoButton)
        self.assertEqual(self.panel.goal.get(("ctl", 0, "mute")), 1.0)
        self.plain(self.col, "Leave")
        self.assertEqual(self.panel.goal.get(("ctl", 0, "mute")), 0.0)

    def test_a_hovered_row_that_went_away_is_not_drawn(self):
        self.send(self.col, "MouseMove", *self.centre(self.part(2, "name")), button=QT.QtCore.Qt.NoButton)
        self.link.anim = self.link.anim[:1]
        self.panel.refresh()
        self.assertIn(("row", 2), self.panel.live_units(self.col.layout_()))
        self.render(self.col)
        self.assertFalse(self.col._failed)

    def test_a_keyed_weight_s_cell_is_outlined(self):
        self.link.anim[0]["weight_keys"] = (5.0,)
        self.panel.refresh(force=True)
        self.assertEqual(self.panel.weight_states()[0], "keyed")
        img = self.render(self.col)
        cx, cy, cw, ch = L.wkey_cell(self.part(0, "wkey"), self.ui)
        edge = img.pixelColor(int(cx + 1), int(cy + ch / 2))
        middle = img.pixelColor(int(cx + cw / 2), int(cy + ch / 2))
        accent = QT.QtGui.QColor(maya_hubstyle.TOKENS["accent"])
        self.assertLess(abs(edge.red() - accent.red()), 60)
        self.assertGreater(abs(middle.red() - accent.red()), 60, "outlined, not filled")

    def test_the_wheel_scrolls_a_long_list_and_draws_its_bar(self):
        self.link.anim = [anim_row("L%d" % i, active=(i == 0)) for i in range(14)]
        self.click(self.col, *self.centre(self.col.layout_().lanes))         # the lanes follow the scroll
        self.panel.refresh(force=True)
        lay = self.col.layout_()
        self.assertGreater(lay.max_scroll, 0)
        E, Qt = QT.QtCore.QEvent, QT.QtCore.Qt

        def wheel(dy):
            p = QT.QtCore.QPointF(100, 100)
            ev = QT.QtGui.QWheelEvent(p, QT.QtCore.QPointF(self.col.mapToGlobal(p.toPoint())), QT.QtCore.QPoint(0, 0),
                                      QT.QtCore.QPoint(0, dy), Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False)
            QT.QtWidgets.QApplication.sendEvent(self.col, ev)
        wheel(-120)
        self.assertAlmostEqual(self.panel.scroll, L.ROW_H + L.ROW_GAP)
        for _ in range(20):
            wheel(-120)
        self.assertAlmostEqual(self.panel.scroll, lay.max_scroll)
        img = self.render(self.col)
        self.assertFalse(self.col._failed)
        wx, wy, ww, wh = lay.well
        line = QT.QtGui.QColor(maya_hubstyle.TOKENS["line"])
        bar_px = img.pixelColor(int(wx + ww - 3.5), int(wy + wh - 8))
        self.assertEqual(bar_px.name(), line.name(), "the scrollbar at the bottom of the well")
        wheel(120)
        self.assertLess(self.panel.scroll, lay.max_scroll)

    def test_the_anim_row_menu_writes(self):
        menu = dict((r[0], r[1]) for r in self.panel.row_menu(0) if r)
        for label, entry in (("Additive", ("set_mode", "A2", "add")), ("Override", ("set_mode", "A2", "ovr")),
                             ("Select objects", ("select_objects", "A2")),
                             ("Add selection", ("add_selection", "A2")),
                             ("Remove selection", ("remove_selection", "A2")),
                             ("Merge down", ("merge_down", "A2"))):
            menu[label]()
            self.assertEqual(self.link.log[-1], entry)
        import maya_hubsound
        with swapped(maya_hubsound, "deleted", lambda: None):
            menu["Delete"]()
        self.assertIn(("delete_anim", "A2"), self.link.log)
        self.assertEqual(self.panel.row_menu(9), [])

    def test_the_base_layer_s_menu_is_all_greyed_but_merge(self):
        rows = [r for r in self.panel.row_menu(2) if r]
        self.assertTrue(all(r[1] is None for r in rows))
        self.assertEqual(len(rows), 9)

    def test_the_right_button_on_a_row_opens_its_menu_and_runs_the_pick(self):
        x, y = self.centre(self.part(0, "name"))
        with auto_menu("Override") as shown:
            self.send(self.col, "MouseButtonPress", x, y, QT.QtCore.Qt.RightButton)
        self.assertEqual(shown[0][0], "Additive")
        self.assertIn(("set_mode", "A2", "ovr"), self.link.log)
        with auto_menu(None):
            self.send(self.col, "MouseButtonPress", x, y, QT.QtCore.Qt.RightButton)
        self.assertEqual(len([e for e in self.link.log if e[0] == "set_mode"]), 1)
        with auto_menu("Override") as shown:                # off the rows: no menu
            self.send(self.col, "MouseButtonPress", 1, self.col.height() / 2.0, QT.QtCore.Qt.RightButton)
        self.assertEqual(shown, [])

    def test_a_menu_from_the_strip_s_own_builder(self):
        built = []

        def builder(rows, menu):
            built.append(len(rows))
            return self.mod._menu_rows(QT.QtWidgets, rows, menu)
        self.strip.menu_rows = builder
        with auto_menu("Merge down"):
            self.panel.menu_at(1, QT.QtCore.QPoint(10, 10))
        self.assertEqual(built, [11])
        self.assertIn(("merge_down", "A1"), self.link.log)

    def test_a_row_runs_when_its_wrapper_died_before_exec_answered(self):
        from tests import menurows
        with menurows.dead_rows(QT.QtWidgets, "Merge down"):
            self.panel.menu_at(1, QT.QtCore.QPoint(10, 10))
        self.assertIn(("merge_down", "A1"), self.link.log)

    def test_a_menu_whose_builder_or_row_fails_is_printed(self):
        self.strip.menu_rows = boom
        with printed() as out:
            self.panel.menu_at(0, QT.QtCore.QPoint(10, 10))
        self.assertIn("boom", out.getvalue())
        del self.strip.menu_rows
        self.link.set_mode = boom
        self.panel._write = lambda *a: boom()
        with auto_menu("Additive"), printed() as out:
            self.panel.menu_at(0, QT.QtCore.QPoint(10, 10))
        self.assertIn("boom", out.getvalue())
        self.panel.menu_at(9, QT.QtCore.QPoint(10, 10))     # no row: no menu

    def test_menu_rows_builds_separators_checks_greyed_rows_and_submenus(self):
        menu = QT.QtWidgets.QMenu()
        self.addCleanup(menu.deleteLater)
        go = lambda: None                                    # noqa: E731
        rows = [("Plain", go), None, ("Checked", go, True), ("Grey", None), ("Sub", [("Inner", go)])]
        _menu, picked = self.mod._menu_rows(QT.QtWidgets, rows, menu)
        actions = menu.actions()
        self.assertTrue(actions[1].isSeparator())
        self.assertTrue(actions[2].isCheckable() and actions[2].isChecked())
        self.assertFalse(actions[3].isEnabled())
        self.assertEqual(sorted(a.text() for a in picked), ["Checked", "Inner", "Plain"])

    def test_rename_through_the_menu_writes_the_typed_name(self):
        menu = dict((r[0], r[1]) for r in self.panel.row_menu(1) if r)
        menu["Rename"]()
        editor = self.panel._editor
        self.assertIsNotNone(editor)
        self.assertEqual(editor.text(), "A1")
        self.assertEqual(editor.objectName(), "skeldarTimeBarLayerName")
        editor.setText("  Walk  ")
        self.key(editor, QT.QtCore.Qt.Key_Return, "\r")
        self.assertIn(("rename", "A1", "Walk"), self.link.log)
        self.assertIsNone(self.panel._editor)

    def test_escape_and_leaving_the_field_rename_nothing(self):
        self.panel.start_rename(0)
        editor = self.panel._editor
        self.key(editor, QT.QtCore.Qt.Key_A, "a")           # an ordinary key types
        self.assertIn("a", editor.text())
        self.key(editor, QT.QtCore.Qt.Key_Escape)
        self.assertIsNone(self.panel._editor)
        self.panel.start_rename(0)
        editor = self.panel._editor
        QT.QtWidgets.QApplication.sendEvent(editor, QT.QtGui.QFocusEvent(QT.QtCore.QEvent.FocusOut,
                                                                         QT.QtCore.Qt.OtherFocusReason))
        self.assertIsNone(self.panel._editor)
        self.assertNotIn("rename", [e[0] for e in self.link.log])

    def test_an_empty_name_renames_nothing_and_a_second_rename_replaces_the_first(self):
        self.panel.start_rename(0)
        first = self.panel._editor
        self.panel.start_rename(1)
        self.assertIsNot(self.panel._editor, first)
        self.assertFalse(first.isVisible())
        self.panel.finish_rename("A1", "   ")
        self.assertNotIn("rename", [e[0] for e in self.link.log])
        self.panel.start_rename(9)                           # no such row
        self.assertIsNone(self.panel._editor)

    def test_failures_in_the_column_s_events_are_printed(self):
        x, y = self.centre(self.part(0, "name"))
        with printed() as out:
            with swapped(self.panel, "press", boom):
                self.click(self.col, x, y)
            with swapped(self.panel, "hover_at", boom):
                self.send(self.col, "MouseMove", x, y, QT.QtCore.Qt.NoButton)
            with swapped(self.panel, "release", boom):
                self.send(self.col, "MouseButtonRelease", x, y)
            with swapped(self.panel, "_end_drag", boom):
                self.plain(self.col, "UngrabMouse")
        self.assertEqual(out.getvalue().count("RuntimeError: boom"), 4)


class LaneStrip(Strip):

    def __init__(self):
        super(LaneStrip, self).__init__()
        self.quiets = 0
        self.marks = []

    def quiet_keys(self):
        self.quiets += 1


class Lanes(Base):
    """The lanes: their menu, cursors, a drag's edges, the guarded failures."""

    def make_strip(self):
        return LaneStrip()

    def setUp(self):
        super(Lanes, self).setUp()
        self.link.opts[self.mod.LANES_VAR] = 1
        self.panel.open((1300, 815))
        self.w = self.panel.lanes
        lay = self.panel.column.layout_()
        self.y = [lay.row_at(i, 0)[1] + 10 for i in range(3)]
        self.ruler = lay.head[1] + 4
        self.assertTrue(self.w.isVisible())

    def lane(self, kind, x, row, **kw):
        self.send(self.w, kind, x, self.y[row] if isinstance(row, int) else row, **kw)

    def test_the_right_button_waits_then_opens_the_key_menu(self):
        self.lane("MouseButtonPress", 105, 1, button=QT.QtCore.Qt.RightButton)
        self.assertTrue(self.w.menu_wait.isActive())
        self.assertLessEqual(self.w.menu_wait.interval(), look.RIGHT_DOUBLE_MS)
        with auto_menu("Cut") as shown:
            self.w.menu_wait.timeout.emit()               # no second press came
        self.assertEqual(shown[0][0], "Set key on A1")
        self.assertEqual(self.link.log[-1], ("lane_keys", "cut", ["A1"], None, 30.0, None))
        self.assertIsNone(self.w._menu_at)

    def test_a_second_right_press_highlights_the_lane_instead(self):
        self.lane("MouseButtonPress", 105, 1, button=QT.QtCore.Qt.RightButton)
        self.lane("MouseButtonDblClick", 105, 1, button=QT.QtCore.Qt.RightButton)
        self.assertFalse(self.w.menu_wait.isActive())
        self.assertEqual(self.panel.lane_sel, {"a": 0, "b": 10, "names": ["A1"]})
        with auto_menu("Cut") as shown:
            self.w._open_menu()                           # nothing pending: no menu
        self.assertEqual(shown, [])

    def test_the_key_menu_s_clear_row_and_a_tangent_submenu(self):
        self.panel.lane_sel = {"a": 10, "b": 20, "names": ["A2"]}
        with auto_menu("Clear highlight"):
            self.panel.lane_menu_at(self.y[0], QT.QtCore.QPoint(5, 5))
        self.assertIsNone(self.panel.lane_sel)
        with auto_menu("Stepped"):
            self.panel.lane_menu_at(self.y[0], QT.QtCore.QPoint(5, 5))
        self.assertEqual(self.link.log[-1][:2], ("lane_keys", "tangents"))
        self.assertEqual(self.link.log[-1][-1], "step")

    def test_the_key_menu_through_the_strip_s_builder_and_its_failures(self):
        built = []
        self.strip.menu_rows = lambda rows, menu: built.append(1) or self.mod._menu_rows(QT.QtWidgets, rows, menu)
        with auto_menu("Snap"):
            self.panel.lane_menu_at(self.y[2], QT.QtCore.QPoint(5, 5))
        self.assertEqual(built, [1])
        self.assertEqual(self.link.log[-1], ("lane_keys", "snap", ["Base"], None, 30.0, None))
        self.strip.menu_rows = boom
        with printed() as out:
            self.panel.lane_menu_at(self.y[2], QT.QtCore.QPoint(5, 5))
        self.assertIn("boom", out.getvalue())
        del self.strip.menu_rows
        self.panel._write = lambda *a: boom()
        with auto_menu("Snap"), printed() as out:
            self.panel.lane_menu_at(self.y[2], QT.QtCore.QPoint(5, 5))
        self.assertIn("boom", out.getvalue())

    def test_over_the_ruler_with_no_highlight_there_is_no_menu(self):
        self.assertEqual(self.panel.lane_menu(self.ruler), [])
        with auto_menu("Cut") as shown:
            self.panel.lane_menu_at(self.ruler, QT.QtCore.QPoint(5, 5))
        self.assertEqual(shown, [])

    def test_a_highlight_s_menu_names_a_layer_gone_from_the_rows_as_it_is(self):
        self.panel.lane_sel = {"a": 10, "b": 20, "names": ["Gone"]}
        rows = dict((r[0], r[1]) for r in self.panel.lane_menu(self.ruler) if r)
        self.assertIn("Set key on Gone", rows)

    def test_a_failing_clock_puts_the_menu_at_frame_0(self):
        self.strip.now = boom
        rows = dict((r[0], r[1]) for r in self.panel.lane_menu(self.y[0]) if r)
        rows["Delete"]()
        self.assertEqual(self.link.log[-1], ("lane_keys", "delete", ["A2"], None, 0.0, None))

    def test_a_lifted_key_whose_layer_went_away_is_not_drawn(self):
        self.lane("MouseMove", 104, 2, button=QT.QtCore.Qt.NoButton)
        self.assertEqual(self.panel.lane_aimed, ("Base", 10.0))
        self.link.anim = self.link.anim[:2]
        self.panel.refresh()
        self.render(self.w)
        self.assertFalse(self.w._failed)

    def test_the_double_click_window_falls_back_to_the_right_double(self):
        with swapped(QT.QtWidgets.QApplication, "doubleClickInterval", staticmethod(boom)):
            self.assertEqual(self.w.double_window(), look.RIGHT_DOUBLE_MS)

    def test_leaving_the_lanes_drops_the_lifted_key(self):
        self.lane("MouseMove", 104, 1, button=QT.QtCore.Qt.NoButton)
        self.assertEqual(self.panel.lane_aimed, ("A1", 10.0))
        self.plain(self.w, "Leave")
        self.assertIsNone(self.panel.lane_aimed)
        self.plain(self.w, "Leave")                        # nothing aimed: nothing to do

    def test_the_lifted_key_is_drawn_lit(self):
        self.lane("MouseMove", 104, 1, button=QT.QtCore.Qt.NoButton)
        img = self.render(self.w)
        self.assertFalse(self.w._failed)
        lit = QT.QtGui.QColor(maya_hubstyle.TOKENS["accent_text"])
        c = img.pixelColor(105, int(self.y[1]))
        self.assertLess(abs(c.red() - lit.red()) + abs(c.green() - lit.green()) + abs(c.blue() - lit.blue()), 40)

    def test_the_edge_cursor_over_a_highlight_s_end(self):
        self.panel.lane_sel = {"a": 10, "b": 20, "names": ["A2"]}
        self.lane("MouseMove", 100, 0, button=QT.QtCore.Qt.NoButton)
        self.assertEqual(self.w.cursor().shape(), QT.QtCore.Qt.SizeHorCursor)
        self.assertEqual(self.panel.lane_aim(100, self.y[0]), "edge")
        self.assertEqual(self.panel.lane_aim(155, self.y[0]), "grab")
        self.assertEqual(self.panel.lane_aim(605, self.y[0]), "time")

    def test_a_press_on_the_ruler_scrubs_and_picks_nothing(self):
        self.lane("MouseButtonPress", 405, self.ruler)
        self.lane("MouseButtonRelease", 405, self.ruler)
        self.assertNotIn("pick", [e[0] for e in self.link.log])
        self.assertIn(("set_time", 40), self.link.log)
        self.assertEqual(self.link.log[-1], ("end_scrub",))

    def test_a_double_click_on_the_ruler_highlights_nothing(self):
        self.lane("MouseButtonDblClick", 405, self.ruler)
        self.assertIsNone(self.panel.lane_sel)

    def test_a_double_click_ends_a_drag_still_held(self):
        self.lane("MouseButtonPress", 305, 0)
        self.assertEqual(self.panel.lane_drag[0], "scrub")
        self.lane("MouseButtonDblClick", 305, 0)
        self.assertIsNone(self.panel.lane_drag)
        self.assertIn(("end_scrub",), self.link.log)

    def test_a_release_with_nothing_pressed_does_nothing(self):
        self.lane("MouseButtonRelease", 305, 0)
        self.assertEqual(self.link.log, [])

    def test_a_key_pressed_and_barely_moved_stays_a_click(self):
        self.lane("MouseButtonPress", 105, 1)
        self.lane("MouseMove", 106, 1, held=QT.QtCore.Qt.LeftButton, button=QT.QtCore.Qt.NoButton)
        self.assertEqual(self.panel.lane_drag[0], "kpend")
        self.lane("MouseButtonRelease", 106, 1)
        self.assertIn(("set_time", 10), self.link.log)

    def test_a_key_dragged_out_and_back_moves_nothing_and_drops_its_highlight(self):
        Qt = QT.QtCore.Qt
        self.lane("MouseButtonPress", 105, 1)
        self.lane("MouseMove", 135, 1, held=Qt.LeftButton, button=Qt.NoButton)
        self.assertEqual(self.panel.lane_drag[0], "key")
        self.lane("MouseMove", 105, 1, held=Qt.LeftButton, button=Qt.NoButton)
        self.lane("MouseButtonRelease", 105, 1)
        self.assertIsNone(self.panel.lane_sel)
        self.assertNotIn("lane_move", [e[0] for e in self.link.log])
        self.assertNotIn("lane_live_begin", [e[0] for e in self.link.log])

    def test_the_start_distance_falls_back_to_4px(self):
        Qt = QT.QtCore.Qt
        self.lane("MouseButtonPress", 105, 1)
        with swapped(self.panel, "q", types.SimpleNamespace(QtWidgets=None)):
            self.lane("MouseMove", 108, 1, held=Qt.LeftButton, button=Qt.NoButton)
            self.assertEqual(self.panel.lane_drag[0], "kpend")
            self.lane("MouseMove", 110, 1, held=Qt.LeftButton, button=Qt.NoButton)
            self.assertEqual(self.panel.lane_drag[0], "key")
        self.lane("MouseButtonRelease", 110, 1)

    def test_a_shift_drag_off_the_lanes_keeps_its_first_lane(self):
        Qt = QT.QtCore.Qt
        self.lane("MouseButtonPress", 105, 1, mods=Qt.ShiftModifier)
        self.lane("MouseMove", 305, self.ruler, held=Qt.LeftButton, button=Qt.NoButton, mods=Qt.ShiftModifier)
        self.assertEqual(self.panel.lane_sel, {"a": 10, "b": 30, "names": ["A1"]})
        self.key(self.w, Qt.Key_S, "s")                    # S during a highlight drag is Maya's
        self.assertNotIn("lane_live_stamp", [e[0] for e in self.link.log])
        self.assertNotIn("lane_set_key", [e[0] for e in self.link.log])
        self.lane("MouseButtonRelease", 305, self.ruler)
        self.assertEqual(self.panel.lane_sel["names"], ["A1"])

    def test_the_scene_step_waits_for_a_key_drag(self):
        self.lane("MouseButtonPress", 305, 0)
        self.panel.lane_timer.timeout.emit()               # a step with no key drag: nothing
        self.assertNotIn("lane_live_to", [e[0] for e in self.link.log])
        self.lane("MouseButtonRelease", 305, 0)

    def test_ctrl_s_during_a_drag_is_maya_s(self):
        E, Qt = QT.QtCore.QEvent, QT.QtCore.Qt
        self.panel.lane_sel = {"a": 10, "b": 20, "names": ["A2"]}
        self.lane("MouseButtonPress", 155, 0)
        ev = QT.QtGui.QKeyEvent(E.KeyPress, Qt.Key_S, Qt.ControlModifier, "s")
        QT.QtWidgets.QApplication.sendEvent(self.w, ev)
        self.assertNotIn("lane_live_stamp", [e[0] for e in self.link.log])
        self.lane("MouseButtonRelease", 155, 0)

    def test_s_on_a_held_block_not_moved_yet_starts_the_live_drag_and_copies(self):
        Qt = QT.QtCore.Qt
        self.panel.lane_sel = {"a": 10, "b": 20, "names": ["A2"]}
        self.lane("MouseButtonPress", 155, 0)
        self.key(self.w, Qt.Key_S, "s")
        names = [e[0] for e in self.link.log]
        self.assertLess(names.index("lane_live_begin"), names.index("lane_live_stamp"))
        self.lane("MouseButtonRelease", 155, 0)
        self.assertIn(("lane_live_end", (10, 20)), self.link.log)

    def test_a_copy_whose_key_did_not_land_on_the_drag_is_not_drawn(self):
        self.panel.lane_sel = {"a": 10, "b": 10, "names": ["A1"]}
        self.panel.keys = {"A1": [10.0]}
        self.panel._add_drawn_copies({"c": {"keys": [(10.0, {})], "stamped": {40.0}}}, (10, 10), (20, 20))
        self.assertEqual(self.panel.keys["A1"], [10.0])

    def test_s_over_a_block_holding_the_active_layer_marks_the_strip(self):
        self.strip.mark_set = lambda a, b: self.strip.marks.append((a, b))
        self.panel.lane_sel = {"a": 10, "b": 20, "names": ["A2", "A1"]}
        self.assertTrue(self.panel.lane_key_range())
        self.assertEqual(self.strip.marks, [(10, 20)])
        self.panel.lane_sel = None
        self.assertFalse(self.panel.lane_key_range())
        self.assertFalse(self.panel.lane_stamp(), "no drag: S is not the lanes'")

    def test_a_lost_live_drag_is_set_down_by_the_next_press(self):
        Qt = QT.QtCore.Qt
        self.panel.lane_sel = {"a": 10, "b": 20, "names": ["A2"]}
        self.lane("MouseButtonPress", 155, 0)
        self.lane("MouseMove", 255, 0, held=Qt.LeftButton, button=Qt.NoButton)
        self.panel.flush_lane_live()                       # the scene's step made
        self.assertTrue(self.panel.lane_live)
        quiets = self.strip.quiets
        self.lane("MouseButtonPress", 605, 1)              # the release never came
        self.assertIn(("lane_live_end", (20, 30)), self.link.log)
        self.assertEqual(self.strip.quiets, quiets + 1)
        self.assertIsNone(self.panel.lane_live)

    def test_a_lost_drag_leaves_no_phantom_drag_behind(self):
        """Fixed 2026-10-27, the bug as it was - layerpanel.py:660-666 `_lane_end_live`: a press after a lost release sets
        the keys down but keeps `lane_preview` (and `lane_stamped`), which only
        `lane_release` clears. A Shift-press that starts a new highlight then reads as a
        key drag: `drag_view()` / `active_lane_drag()` answer the old target, so the
        lanes draw the new block at the old drag's frames and the timeline shows a
        phantom drag of the active layer."""
        Qt = QT.QtCore.Qt
        self.panel.lane_sel = {"a": 10, "b": 20, "names": ["A2"]}
        self.lane("MouseButtonPress", 155, 0)
        self.lane("MouseMove", 255, 0, held=Qt.LeftButton, button=Qt.NoButton)
        self.panel.flush_lane_live()
        self.lane("MouseButtonPress", 505, 0, mods=Qt.ShiftModifier)     # the release was lost
        self.assertEqual(self.panel.lane_sel, {"a": 50, "b": 50, "names": ["A2"]})
        self.assertIsNone(self.panel.active_lane_drag(), "no key drag stands")
        self.assertIsNone(self.panel.drag_view())

    def test_a_failing_strip_track_stops_the_lanes_quietly(self):
        self.strip.track = boom
        self.lane("MouseButtonPress", 305, 0)
        self.lane("MouseMove", 405, 0, held=QT.QtCore.Qt.LeftButton, button=QT.QtCore.Qt.NoButton)
        self.assertIsNone(self.panel.lane_drag)
        self.assertEqual(self.link.log, [])
        self.render(self.w)                                # the face alone
        self.assertFalse(self.w._failed)
        self.assertIsNone(self.panel.lane_key_under(105, 1))
        self.assertIsNone(self.panel.lane_part(105, 1))

    def test_a_failing_clock_makes_every_key_a_drag_and_hides_the_playhead(self):
        self.strip.now = boom
        self.lane("MouseButtonPress", 305, 1)
        self.assertEqual(self.panel.lane_drag[0], "scrub")
        self.lane("MouseButtonRelease", 305, 1)
        self.lane("MouseButtonPress", 105, 1)              # on the key at 10: a key press
        self.assertEqual(self.panel.lane_drag[0], "kpend")
        self.lane("MouseButtonRelease", 105, 1)
        self.assertIsNone(self.panel.now())
        self.render(self.w)
        self.assertFalse(self.w._failed)

    def test_a_failing_scrub_to_falls_back_to_maya(self):
        self.strip.scrub_to = boom
        with printed() as out:
            self.lane("MouseButtonPress", 305, 0)
            self.lane("MouseButtonRelease", 305, 0)
        self.assertIn(("set_time", 30), self.link.log)
        self.assertIn("boom", out.getvalue())

    def test_a_failing_quiet_is_printed_and_the_drag_set_down(self):
        Qt = QT.QtCore.Qt
        self.strip.quiet_keys = boom
        with printed() as out:
            self.lane("MouseButtonPress", 105, 1)
            self.lane("MouseMove", 205, 1, held=Qt.LeftButton, button=Qt.NoButton)
            self.lane("MouseButtonRelease", 205, 1)
        self.assertIn("boom", out.getvalue())
        self.assertIn(("lane_move", ["A1"], (10, 10), (20, 20)), self.link.log)

    def test_a_timeline_that_fails_is_printed_not_followed(self):
        Qt = QT.QtCore.Qt
        self.strip.timeline = types.SimpleNamespace(own_moving=boom, live=None, repaint=boom)
        with printed() as out:
            self.assertIsNone(self.panel.drag_view())
            self.panel.lane_sel = {"a": 10, "b": 20, "names": ["A2"]}       # the active layer's lane
            self.lane("MouseButtonPress", 155, 0)
            self.lane("MouseMove", 255, 0, held=Qt.LeftButton, button=Qt.NoButton)
            self.lane("MouseButtonRelease", 255, 0)
        self.assertGreaterEqual(out.getvalue().count("RuntimeError: boom"), 2)
        self.assertIn(("lane_move", ["A2"], (10, 20), (20, 30)), self.link.log)

    def test_the_timeline_s_drag_is_drawn_on_the_active_lane(self):
        self.strip.timeline = types.SimpleNamespace(own_moving=lambda: ((10, 10), (40, 40), None), live=None)
        view = self.panel.drag_view()
        self.assertEqual(view["names"], ["A2"])
        self.panel.refresh(keys=True)
        self.assertTrue(self.panel._keys_stale, "no read under a timeline drag")
        img = self.render(self.w)
        self.assertFalse(self.w._failed)
        x = int(LaneStrip().track().x(40) + 5)
        self.assertGreater(img.pixelColor(x, int(self.y[0])).red(), 0x40, "the key drawn at 40")

    def test_failures_in_the_lanes_events_are_printed(self):
        Qt = QT.QtCore.Qt
        with printed() as out:
            with swapped(self.panel, "lane_press", boom):
                self.lane("MouseButtonPress", 305, 0)
            with swapped(self.panel, "lane_all", boom):
                self.lane("MouseButtonDblClick", 305, 0)
            with swapped(self.panel, "lane_aim", boom):
                self.lane("MouseMove", 305, 0, button=Qt.NoButton)
            self.panel.lane_aimed = ("A1", 10.0)
            with swapped(self.w, "update", boom):
                self.plain(self.w, "Leave")
            with swapped(self.panel, "lane_release", boom):
                self.lane("MouseButtonRelease", 305, 0)
                self.panel.lane_drag = ("scrub", 30)
                self.plain(self.w, "UngrabMouse")
        self.assertEqual(out.getvalue().count("RuntimeError: boom"), 6)
        self.panel.lane_drag = None

    def test_ungrab_ends_a_lanes_drag(self):
        self.lane("MouseButtonPress", 305, 0)
        self.plain(self.w, "UngrabMouse")
        self.assertIsNone(self.panel.lane_drag)
        self.assertIn(("end_scrub",), self.link.log)

    def test_s_typed_into_a_text_field_is_the_field_s(self):
        Qt = QT.QtCore.Qt
        self.panel.lane_sel = {"a": 10, "b": 20, "names": ["A2"]}
        field = QT.QtWidgets.QLineEdit()
        self.addCleanup(field.deleteLater)
        with swapped(QT.QtWidgets.QApplication, "focusWidget", staticmethod(lambda: field)):
            self.key(field, Qt.Key_S, "s")
        self.assertNotIn("lane_key_range", [e[0] for e in self.link.log])
        self.assertEqual(field.text(), "s")

    def test_a_failing_key_filter_lets_the_key_through(self):
        with swapped(self.panel, "keys_block", boom), printed() as out:
            self.key(self.w, QT.QtCore.Qt.Key_S, "s")
        self.assertIn("boom", out.getvalue())
        self.assertNotIn("lane_key_range", [e[0] for e in self.link.log])

    def test_on_time_with_a_broken_weight_key_is_printed(self):
        self.link.anim[0]["weight_keys"] = ("x",)
        self.panel.refresh(force=True)
        with printed() as out:
            self.panel.on_time()
        self.assertIn("ValueError", out.getvalue())


class LanePaint(Base):
    """What the lanes draw: steel ingots, keys between frames, marks off the track,
    the lanes beyond the rows."""

    def make_strip(self):
        return LaneStrip()

    def setUp(self):
        super(LanePaint, self).setUp()
        self.link.opts[self.mod.LANES_VAR] = 1

    def open(self):
        self.panel.open((1300, 815))
        lay = self.panel.column.layout_()
        self.y = [lay.row_at(i, 0)[1] + 10 for i in range(3)]

    def test_steel_keys_are_ingots_on_the_active_lane(self):
        self.strip.steel = True
        self.strip.key_hex = lambda: "#8a929c"
        self.open()
        img = self.render(self.panel.lanes)
        self.assertFalse(self.panel.lanes._failed)
        c = img.pixelColor(105, int(self.y[0] + 4))
        self.assertGreater(c.red(), 0x40)
        self.assertLess(abs(c.red() - c.blue()), 40, "steel grey, not the accent")

    def test_a_key_between_frames_and_marks_off_the_track(self):
        self.strip.trk = look.Track(0, 99, 0, 3000, cells=True)         # wider than the lanes
        self.link.keymap = {"A1": [10.5]}
        self.link.anim[0]["weight_keys"] = (500.0,)                       # off the track
        self.open()
        img = self.render(self.panel.lanes)
        self.assertFalse(self.panel.lanes._failed)
        x = int(self.strip.trk.x(10.5))
        self.assertGreater(img.pixelColor(x, int(self.y[1])).red(), 0x40, "a thin mark at 10.5")

    def test_lanes_drawn_with_more_rows_than_layers_skip_the_extra(self):
        self.open()
        self.panel.tab = "disp"
        self.link.disp = [disp_row("d%d" % i) for i in range(6)]
        self.panel.refresh(force=True)
        self.render(self.panel.lanes)
        self.assertFalse(self.panel.lanes._failed)


class Motion(Base):
    """The burst, the tab's wave, pops, flashes, hover and ghosts on the test's clock."""

    motion = True

    def setUp(self):
        super(Motion, self).setUp()
        self.t = [1000.0]
        self.panel.clock = lambda: self.t[0]

    def run_until(self, cond, step=16.0, limit=500):
        for _ in range(limit):
            if cond():
                return True
            self.t[0] += step
            self.panel._animate()
        return cond()

    def settle(self):
        self.assertTrue(self.run_until(lambda: not self.panel.driver.isActive()))

    def test_the_column_and_lanes_unroll_rest_and_the_driver_stops(self):
        self.link.opts[self.mod.LANES_VAR] = 1
        self.panel.open((1300, 815))
        self.assertEqual(self.panel.phase, "opening")
        self.assertIsNotNone(self.panel.lanes_burst)
        self.assertEqual(set(self.panel.lanes_burst["delays"]), {0, 1, 2})
        self.t[0] += 60
        img = self.render(self.panel.column)
        self.assertEqual(img.pixelColor(4, 12).alpha(), 0)
        lanes = self.render(self.panel.lanes)
        self.assertEqual(lanes.pixelColor(5, int(lanes.height() / 2)).alpha(), 0, "unrolling from the right")
        self.assertEqual(self.panel.lane_of(0)[0] < 1.0 or self.panel.lane_of(0)[1] < 1.0, True)
        self.settle()
        self.assertEqual(self.panel.phase, "open")
        self.assertIsNone(self.panel.burst)
        self.assertIsNone(self.panel.lanes_burst)
        self.assertEqual(self.panel.lane_of(0), (1.0, 1.0))
        self.assertGreater(self.render(self.panel.column).pixelColor(4, 12).alpha(), 0)

    def test_closing_folds_then_hides_both(self):
        self.link.opts[self.mod.LANES_VAR] = 1
        self.panel.open((1300, 815))
        self.settle()
        self.panel.close((1300, 815))
        self.assertEqual(self.panel.phase, "closing")
        self.assertFalse(self.panel.lanes_burst["open"])
        self.panel.age_override = self.panel.burst["ends"] - 15
        img = self.render(self.panel.column)
        self.assertEqual(img.pixelColor(4, 12).alpha(), 0, "the shape closing onto the pill")
        self.render(self.panel.lanes)
        self.panel.age_override = None
        self.assertTrue(self.run_until(lambda: self.panel.phase == "closed"))
        self.assertFalse(self.panel.column.isVisible() or self.panel.lanes.isVisible())
        self.settle()

    def test_close_with_no_origin_folds_toward_the_column_s_bottom(self):
        self.panel.open((1300, 815))
        self.settle()
        self.panel._origin = None
        self.panel.close()
        w, h = self.panel.column.width(), self.panel.column.height()
        self.assertEqual(self.panel.burst["origin"], (w / 2.0, float(h)))

    def test_turning_the_lanes_off_folds_them(self):
        self.link.opts[self.mod.LANES_VAR] = 1
        self.panel.open((1300, 815))
        self.settle()
        self.click(self.panel.column, *self.centre(self.panel.column.layout_().lanes))
        self.assertFalse(self.panel.lanes_burst["open"])
        self.assertTrue(self.panel.lanes.isVisible())
        self.assertGreater(self.panel.flash_of(("lanes",)), 0.0)
        self.render(self.panel.column)
        self.assertFalse(self.panel.column._failed)
        self.settle()
        self.assertFalse(self.panel.lanes.isVisible())

    def test_a_tab_switch_pops_its_rows_in_a_wave(self):
        self.panel.open((1300, 815))
        self.settle()
        col = self.panel.column
        self.click(col, *self.centre(col.layout_().segments["disp"]))
        self.assertEqual(set(self.panel.wave["delays"]), {0, 1})
        lay = col.layout_()
        self.assertEqual(self.panel.excluded(lay), frozenset([("row", 0), ("row", 1)]))
        self.assertIn(("row", 1), self.panel.live_units(lay))
        scale, _op = self.panel.burst_of(("row", 1))
        self.assertLess(scale, 1.0)
        self.render(col)
        self.assertFalse(col._failed)
        self.assertTrue(self.run_until(lambda: self.panel.wave is None))
        self.assertEqual(self.panel.burst_of(("row", 1)), (1.0, 1.0))
        self.settle()

    def test_lanes_folding_after_a_switch_to_display_fold_every_lane(self):
        """Fixed 2026-10-27, the bug as it was - layerpanel.py:960-961 with 348-351: `_switch_tab` sets the new tab before
        `_hide_lanes(burst=True)`, so the folding lanes' parts are read from the Display
        tab's layout - one lane per display layer, not per animation layer. With three
        animation layers and two display layers only two lanes fold; the third vanishes
        at once (and `Lanes._paint` draws the folding lanes at the Display rows)."""
        self.link.opts[self.mod.LANES_VAR] = 1
        self.panel.open((1300, 815))
        self.settle()
        col = self.panel.column
        self.click(col, *self.centre(col.layout_().segments["disp"]))
        self.assertEqual(set(self.panel.lanes_burst["delays"]), {0, 1, 2})

    def test_pops_and_flashes_fade_and_the_driver_stops(self):
        self.panel.open((1300, 815))
        self.settle()
        col = self.panel.column
        rect = L.row_parts(col.layout_().row_at(0, 0), "anim", 1.0)["mute"]
        self.click(col, *self.centre(rect))
        self.t[0] += 40
        self.assertLess(self.panel.pop_of(("ctl", 0, "mute")), 1.0)
        for name in ("add", "merge"):
            self.click(col, *self.centre(dict(col.layout_().foot)[name]))
        self.click(col, *self.centre(col.layout_().segments["anim"]))
        self.assertGreater(self.panel.flash_of(("foot", "merge")), 0.5)
        self.render(col)
        self.assertFalse(col._failed)
        self.settle()
        self.assertEqual((self.panel.pops, self.panel.flashes), ({}, {}))
        self.assertEqual(self.panel.flash_of(("foot", "merge")), 0.0)

    def test_the_hover_eases_in_and_out(self):
        self.panel.open((1300, 815))
        self.settle()
        self.panel.hover_at(("row", 0, "mute"))
        self.assertEqual(self.panel.hover.get(("ctl", 0, "mute"), 0.0), 0.0)
        self.assertTrue(self.run_until(lambda: self.panel.hover.get(("ctl", 0, "mute"), 0) > 0.99))
        self.render(self.panel.column)
        self.panel.hover_at(None)
        self.settle()
        self.assertEqual((self.panel.goal, self.panel.hover), ({}, {}))

    def test_a_deleted_row_folds_where_it_stood(self):
        import maya_hubsound
        self.panel.open((1300, 815))
        self.settle()
        col = self.panel.column
        with swapped(maya_hubsound, "deleted", lambda: None):
            self.click(col, *self.centre(dict(col.layout_().foot)["delete"]))
        self.assertEqual([g["row"]["name"] for g in self.panel.ghosts], ["A2"])
        self.t[0] += 30
        self.render(col)
        self.assertFalse(col._failed)
        self.click(col, *self.centre(col.layout_().segments["disp"]))
        self.render(col)                                   # the ghost belongs to the other tab
        self.assertFalse(col._failed)
        self.settle()
        self.assertEqual(self.panel.ghosts, [])

    def test_the_driver_stops_when_a_step_fails(self):
        self.panel.open((1300, 815))
        self.panel._busy = boom
        with printed() as out:
            self.panel._animate()
        self.assertFalse(self.panel.driver.isActive())
        self.assertIn("boom", out.getvalue())


if __name__ == "__main__":
    unittest.main()
