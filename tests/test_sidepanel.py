"""The side panel (2026-10-17): Maya's Channel Box / Layer Editor and Attribute Editor
at the right edge of Maya's window. The rules as values, and the controller offscreen
on a fake window and cursor; the borrow of Maya's own forms on fake widgets.

Spec: docs/superpowers/specs/2026-10-17-side-panel-design.md
"""
import os
import subprocess
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import maya_hubqt
    QT = maya_hubqt.qt()
except Exception:                                            # noqa: BLE001
    QT = None

import maya_hubstyle
from maya_sidepanel import look

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SkeldarAnim")
WINDOW = [100, 50, 1600, 900]


class Look(unittest.TestCase):

    def test_it_imports_no_maya_and_no_qt(self):
        code = ("import sys; import maya_sidepanel.look; "
                "bad = [m for m in sys.modules if m.split('.')[0] in ('maya', 'PySide6', 'PySide2')]; "
                "assert not bad, bad")
        subprocess.check_call([sys.executable, "-c", code], cwd=PLUGIN)

    def test_the_area_is_the_viewport_above_the_time_bar(self):
        """2026-10-17: under the menus, status line and tabs (Maya's MainPane), above
        the Time Bar's band - read live: the window (0, 34, 2560, 1494), the pane
        (2, 176, 2556, 1350)."""
        window, pane = (0, 34, 2560, 1494), (2, 176, 2556, 1350)
        self.assertEqual(look.area(pane, window), pane)
        self.assertEqual(look.area(pane, window, 126), (2, 176, 2556, 1402 - 176))
        self.assertEqual(look.area(None, window), window)
        self.assertEqual(look.area(pane, window, 2), pane)        # a bar no taller than the gap under the pane
        self.assertIsNone(look.area(None, None))

    def test_the_band_stands_against_the_right_of_maya_s_window(self):
        self.assertEqual(look.side_band(WINDOW, 340, 1.0), (1360, 50, 340, 900))
        self.assertEqual(look.side_band(WINDOW, 340, 1.5), (1190, 50, 510, 900))
        self.assertEqual(look.side_band(WINDOW, 5000, 1.0)[2], look.MAX_WIDTH)
        self.assertEqual(look.side_band([0, 0, 200, 100], 340, 1.0), (0, 0, 200, 100))

    def test_the_sensor_and_the_zone_run_down_the_right_edge(self):
        self.assertEqual(look.sensor_band(WINDOW, 2), (1698, 50, 2, 900))
        self.assertEqual(look.zone_band(WINDOW, 1.0), (1652, 50, 48, 900))
        self.assertEqual(look.zone_band(WINDOW, 1.5), (1628, 50, 72, 900))

    def test_the_burst_rows_cover_the_panel_and_pop_nearest_first(self):
        rows = look.rows(900, 1.5)
        self.assertEqual(rows[0][0], 0)
        self.assertEqual(rows[-1][1], 900)
        self.assertEqual(rows[0][1] - rows[0][0], 66)
        self.assertLess(look.open_delay(0, 1.5), look.open_delay(300, 1.5))
        self.assertEqual(look.open_delay(-300, 1.5), look.open_delay(300, 1.5))
        #  going back, the farthest folds first and the nearest last
        self.assertEqual(look.fold_delay(800, 1.5, 800), 0.0)
        self.assertGreater(look.fold_delay(0, 1.5, 800), look.fold_delay(400, 1.5, 800))
        self.assertGreaterEqual(look.open_total(450, 900, 1.5), look.UNROLL_MS)
        self.assertLess(look.open_total(450, 900, 1.5), look.open_total(0, 900, 1.5))
        self.assertLess(look.open_total(0, 1500, 1.5), 700)
        self.assertGreater(look.close_folded(450, 900, 1.5), look.FOLD_MS)

    def test_the_grip_widens_to_the_left(self):
        self.assertEqual(look.dragged_width(340, -60, 1.0), 400)
        self.assertEqual(look.dragged_width(340, -60, 1.5), 380)
        self.assertEqual(look.dragged_width(340, 500, 1.0), look.MIN_WIDTH)

    def test_the_channels_tab_follows_maya_s_separate_preference(self):
        self.assertEqual(look.forms("channels", False),
                         (("Channel Box / Layer Editor", "MainChannelsLayersLayout"),))
        self.assertEqual([f for _c, f in look.forms("channels", True)],
                         ["MainChannelBoxLayout", "MainLayerEditorLayout"])
        self.assertEqual(look.forms("attributes", False),
                         (("Attribute Editor", "MainAttributeEditorLayout"),))
        self.assertEqual(look.tab_of_component("Layer Editor"), "channels")
        self.assertEqual(look.tab_of_component("Attribute Editor"), "attributes")

    def test_modes_and_tabs_fall_back(self):
        self.assertEqual(look.mode_from(None), "maya")
        self.assertEqual(look.mode_from("edge"), "edge")
        self.assertEqual(look.tab_from("bogus"), "channels")

    def test_the_unroll_opens_from_the_cursor_height(self):
        self.assertEqual(look.unroll(0, 300, 900, True), (300, 300))
        y0, y1 = look.unroll(1, 300, 900, True)
        self.assertEqual((round(y0), round(y1)), (0, 900))
        y0, y1 = look.unroll(1, 300, 900, False)
        self.assertEqual((round(y0), round(y1)), (300, 300))

    def test_the_mel_override_keeps_maya_s_answer_and_asks_us_first(self):
        for proc, tab in (("isAttributeEditorVisible", "attributes"),
                          ("isChannelBoxVisible", "channels")):
            self.assertIn("global proc int %s()" % proc, look.MEL_OVERRIDE)
            self.assertIn("holds('%s')" % tab, look.MEL_OVERRIDE)
        self.assertIn('isUIComponentVisible("Attribute Editor")', look.MEL_OVERRIDE)
        self.assertIn("channelsLayersSeparate", look.MEL_OVERRIDE)
        self.assertEqual(look.MEL_RESTORE, ('source "isAttributeEditorVisible.mel";',
                                            'source "isChannelBoxVisible.mel";'))

    def test_the_band_is_at_least_what_maya_s_forms_ask_for(self):
        """2026-10-17, live: the Attribute Editor asks 643 px at 150 % against the
        band's 510, the host grew past its mask and the panel showed half."""
        self.assertEqual(look.min_width_px([643, 400], 1.5), 651)
        self.assertEqual(look.side_band(WINDOW, 340, 1.5, least=651), (1049, 50, 651, 900))
        self.assertEqual(look.side_band(WINDOW, 340, 1.5, least=200)[2], 510)
        self.assertEqual(look.min_width_px([5000], 1.0), look.MAX_WIDTH)

    def test_the_ae_refresh_is_maya_s_update_without_the_raise_test(self):
        self.assertIn("global proc skeldarSidePanelRefreshAE()", look.MEL_REFRESH_AE)
        self.assertIn("updateAE($last)", look.MEL_REFRESH_AE)
        self.assertNotIn("-raise", look.MEL_REFRESH_AE)

    def test_blockers_in_order(self):
        self.assertEqual(look.blockers(), [])
        self.assertEqual(look.blockers(pinned=True, typing=True, dragging=True),
                         ["pinned", "typing", "dragging"])


class Holds(unittest.TestCase):

    def test_holds_answers_from_the_state_on_sys(self):
        import maya_sidepanel
        saved = getattr(sys, "_skeldar_sidepanel", None)
        try:
            sys._skeldar_sidepanel = {"edge": None, "held": {"attributes": [{"form": "x"}]}}
            self.assertEqual(maya_sidepanel.holds("attributes"), 1)
            self.assertEqual(maya_sidepanel.holds("channels"), 0)
        finally:
            if saved is None:
                del sys._skeldar_sidepanel
            else:
                sys._skeldar_sidepanel = saved


@unittest.skipIf(QT is None, "no Qt")
class Edge(unittest.TestCase):

    def setUp(self):
        from maya_sidepanel import edge, panel
        self.app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])
        self.window = list(WINDOW)
        self.cursor = [900, 500]
        self.down = [False]
        self.over = [True]
        self.tabs = []
        self.widths = []
        self.ticks = []
        self.picture = None

        def make(parent, on_tab, on_pin, on_width):
            return panel.make(parent, 1.0, maya_hubstyle.TOKENS, motion=False,
                              on_tab=on_tab, on_pin=on_pin, on_width=on_width)
        self.edge = edge.SideEdge(make, width=340, scale=1.0,
                                  window_rect=lambda: tuple(self.window),
                                  cursor=lambda: tuple(self.cursor),
                                  buttons=lambda: self.down[0], app_active=lambda: True,
                                  over_maya=lambda: self.over[0], motion=False,
                                  on_tab=self.tabs.append, on_width=self.widths.append,
                                  tick=self.ticks.append, capture=lambda host: self.picture)
        self.addCleanup(self.edge.destroy)

    def geometry(self, widget):
        g = widget.geometry()
        return g.x(), g.y(), g.width(), g.height()

    def test_it_starts_hidden_with_the_sensor_on_the_right(self):
        self.assertFalse(self.edge.shown)
        self.assertFalse(self.edge.host.isVisible())
        self.assertTrue(self.edge.sensor.isVisible())
        self.assertEqual(self.geometry(self.edge.sensor), (1698, 50, 2, 900))
        self.assertEqual(self.geometry(self.edge.host), (1360, 50, 340, 900))

    def test_resting_on_the_sensor_brings_it_out(self):
        self.cursor[:] = [1699, 400]
        self.edge.dwell_done()
        self.assertTrue(self.edge.shown)
        self.assertTrue(self.edge.host.isVisible())
        self.assertFalse(self.edge.sensor.isVisible())

    def test_not_from_elsewhere_nor_with_a_button_held(self):
        self.edge.dwell_done()
        self.assertFalse(self.edge.shown)
        self.cursor[:] = [1699, 400]
        self.down[0] = True
        self.edge.dwell_done()
        self.assertFalse(self.edge.shown)

    def test_resting_in_the_zone_brings_it_out_after_the_dwell(self):
        self.cursor[:] = [1690, 400]
        ticks = int(look.ZONE_DWELL_MS // look.ZONE_POLL_MS)
        for _ in range(ticks - 1):
            self.edge.zone_tick()
        self.assertFalse(self.edge.shown)
        self.edge.zone_tick()
        self.assertTrue(self.edge.shown)

    def test_the_zone_ignores_a_window_over_it_and_a_held_button(self):
        self.cursor[:] = [1690, 400]
        self.over[0] = False
        for _ in range(20):
            self.edge.zone_tick()
        self.assertFalse(self.edge.shown)
        self.over[0] = True
        self.down[0] = True
        for _ in range(20):
            self.edge.zone_tick()
        self.assertFalse(self.edge.shown)

    def test_it_goes_back_after_the_cursor_left_and_stays_while_pinned(self):
        self.edge.reveal()
        self.cursor[:] = [300, 300]
        self.edge.watch_tick()
        self.assertTrue(self.edge.hide_timer.isActive())
        self.edge.set_pinned(True)
        self.assertTrue(self.edge.panel.pin.isChecked())
        self.edge.hide_due()
        self.assertTrue(self.edge.shown)
        self.edge.set_pinned(False)
        self.edge.hide_due()
        self.assertFalse(self.edge.shown)
        self.assertFalse(self.edge.host.isVisible())
        self.assertTrue(self.edge.sensor.isVisible())

    def test_the_pin_button_pins(self):
        self.edge.panel.pin.click()
        self.assertTrue(self.edge.pinned)

    def test_the_cursor_over_it_keeps_it(self):
        self.edge.reveal()
        self.cursor[:] = [1500, 400]
        self.edge.watch_tick()
        self.assertFalse(self.edge.hide_timer.isActive())
        self.assertIn("inside", self.edge.blockers())

    def test_a_held_reveal_waits_for_a_visit(self):
        self.edge.reveal(held=True, tab="attributes")
        self.assertEqual(self.edge.panel.tab, "attributes")
        self.cursor[:] = [300, 300]
        self.edge.watch_tick()
        self.assertIn("held", self.edge.blockers())
        self.cursor[:] = [1500, 400]
        self.edge.watch_tick()                      # visited
        self.cursor[:] = [300, 300]
        self.edge.watch_tick()                      # and left
        self.assertNotIn("held", self.edge.blockers())
        self.edge.hide_due()
        self.assertFalse(self.edge.shown)

    def test_a_press_outside_releases_a_hold(self):
        self.edge.reveal(held=True)
        self.cursor[:] = [300, 300]
        self.down[0] = True
        self.edge.watch_tick()
        self.down[0] = False
        self.assertNotIn("held", self.edge.blockers())

    def test_typing_in_a_field_of_the_panel_keeps_it(self):
        self.edge.reveal()
        field = QT.QtWidgets.QLineEdit(self.edge.panel.pages["attributes"].parentWidget())
        self.edge.panel.pages["attributes"].addWidget(field)
        self.edge.panel.set_tab("attributes")
        self.edge.host.activateWindow()
        field.setFocus()
        self.app.processEvents()
        if self.app.focusWidget() is field:          # offscreen may give no focus at all
            self.assertIn("typing", self.edge.blockers())

    def test_the_tabs_switch_pages_and_report(self):
        self.edge.panel.tabs["attributes"].click()
        self.assertEqual(self.tabs, ["attributes"])
        self.assertEqual(self.edge.panel.stack.currentIndex(), 1)
        self.assertTrue(self.edge.panel.tabs["attributes"].isChecked())
        self.assertFalse(self.edge.panel.tabs["channels"].isChecked())

    def test_the_grip_widens_it_keeping_its_right_edge(self):
        self.edge._grip(-60, False)
        self.assertEqual(self.geometry(self.edge.host), (1300, 50, 400, 900))
        self.assertEqual(self.widths, [])
        self.assertIn("dragging", self.edge.blockers())
        self.edge._grip(-80, True)
        self.assertEqual(self.widths, [420])
        self.assertEqual(self.geometry(self.edge.host), (1280, 50, 420, 900))

    def test_it_follows_maya_s_window_and_calls_the_tick(self):
        self.window[:] = [0, 0, 1200, 700]
        self.edge.place_tick()
        self.assertEqual(self.geometry(self.edge.host), (860, 0, 340, 700))
        self.assertEqual(len(self.ticks), 1)
        self.assertIs(self.ticks[0], self.edge)

    def test_the_host_is_not_grown_by_a_wide_child_and_keeps_its_least(self):
        wide = QT.QtWidgets.QWidget()
        wide.setMinimumWidth(700)
        self.edge.panel.pages["attributes"].addWidget(wide)
        self.edge.reveal()
        self.app.processEvents()
        self.assertEqual(self.edge.host.width(), 340)
        self.edge.least = 650
        self.edge.place()
        self.assertEqual(self.geometry(self.edge.host), (1050, 50, 650, 900))
        self.assertEqual(self.edge.host.mask().boundingRect().width(), 650)

    def test_a_reveal_on_a_tab_while_out_still_refreshes(self):
        calls = []
        self.edge._on_reveal = lambda: calls.append(1)
        self.edge.reveal()
        self.edge.reveal(tab="attributes")
        self.assertEqual(calls, [1, 1])

    def burst_picture(self):
        pixmap = QT.QtGui.QPixmap(340, 900)
        pixmap.fill(QT.QtGui.QColor("#ff0000"))
        return pixmap

    def draw_overlay(self):
        image = QT.QtGui.QImage(340, 900, QT.QtGui.QImage.Format_ARGB32)
        image.fill(0)
        painter = QT.QtGui.QPainter(image)
        self.edge.paint_burst(painter)
        painter.end()
        return image

    def test_a_reveal_bursts_the_panel_s_picture_from_the_cursor(self):
        """2026-10-17, «как у таймслайдера»: the picture moves, Maya's editors wait."""
        self.picture = self.burst_picture()
        self.edge.motion = True
        self.cursor[:] = [1690, 500]
        self.edge.reveal()
        self.assertTrue(self.edge.overlay.isVisible())
        self.assertEqual(self.edge.host.windowOpacity(), 1.0)
        b = self.edge._slide
        self.assertEqual(b["cy"], 450.0)
        b["t0"] -= look.open_delay(0, 1.0) + look.POP_MS * 0.3      # the middle rows popping
        image = self.draw_overlay()
        face = QT.QtGui.QColor(maya_hubstyle.TOKENS["panel"])
        self.assertGreater(image.pixelColor(170, 450).red(), face.red() + 60)  # near: coming in
        self.assertEqual(image.pixelColor(170, 10).name(), face.name())         # far: not yet
        b["t0"] -= look.open_total(450, 900, 1.0)
        self.edge.slide_tick()
        self.assertIsNone(self.edge._slide)
        self.assertFalse(self.edge.overlay.isVisible())
        self.assertEqual(self.edge.host.mask().boundingRect().height(), 900)

    def test_going_back_folds_the_picture_then_closes_onto_the_cursor(self):
        self.edge.reveal()
        self.picture = self.burst_picture()
        self.edge.motion = True
        self.cursor[:] = [300, 500]
        self.edge.conceal()
        b = self.edge._slide
        self.assertTrue(self.edge.overlay.isVisible())
        self.edge.slide_tick()
        self.assertEqual(self.edge.host.mask().boundingRect().height(), 900)   # folding first
        b["t0"] -= b["folded"] + look.CLOSE_MS + 1
        self.edge.slide_tick()
        self.assertIsNone(self.edge._slide)
        self.assertFalse(self.edge.host.isVisible())
        self.assertTrue(self.edge.sensor.isVisible())

    def test_no_picture_falls_back_to_the_plain_unroll(self):
        self.edge.motion = True
        self.edge.reveal()
        self.assertFalse(self.edge.overlay.isVisible())
        self.assertIsNotNone(self.edge._slide)

    def test_the_end_of_the_unroll_asks_every_widget_to_paint(self):
        """2026-10-17, live: Maya's editors showed their values only where the mouse
        passed after the panel unrolled."""
        asked = []
        real = self.edge.repaint_all
        self.edge.repaint_all = lambda: asked.append(real())
        QT.QtWidgets.QTableView(self.edge.panel)       # its update() wants an index
        self.edge.motion = True
        self.edge.reveal()
        self.edge._slide["t0"] -= look.UNROLL_MS + 1
        self.edge.slide_tick()
        self.assertEqual(len(asked), 1)
        self.assertGreater(asked[0], 10)

    def test_the_unroll_masks_from_the_cursor_and_ends_whole(self):
        self.edge.motion = True
        self.cursor[:] = [1699, 300]
        self.edge.reveal()
        self.assertIsNotNone(self.edge._slide)
        self.assertEqual(self.edge._slide["cy"], 250.0)
        self.assertLess(self.edge.host.mask().boundingRect().height(), 10)
        self.edge._slide["t0"] -= look.UNROLL_MS + 1
        self.edge.slide_tick()
        self.assertIsNone(self.edge._slide)
        self.assertEqual(self.edge.host.mask().boundingRect().height(), 900)


@unittest.skipIf(QT is None, "no Qt")
class Borrow(unittest.TestCase):
    """take / give on plain Qt widgets standing in for Maya's: the form leaves its
    parent's layout for our page and comes back at its own index."""

    def setUp(self):
        from maya_sidepanel import holder
        self.app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])
        self.holder = holder
        self.ws = QT.QtWidgets.QWidget()
        self.ws.setObjectName("AttributeEditor")
        inner = QT.QtWidgets.QWidget(self.ws)
        inner.setObjectName("AEInner")
        QT.QtWidgets.QVBoxLayout(self.ws).addWidget(inner)
        box = QT.QtWidgets.QVBoxLayout(inner)
        self.before = QT.QtWidgets.QLabel("before", inner)
        self.form = QT.QtWidgets.QWidget(inner)
        self.form.setObjectName("MainAttributeEditorLayout")
        box.addWidget(self.before)
        box.addWidget(self.form)
        self.inner = inner
        self.page = QT.QtWidgets.QWidget()
        self.page_layout = QT.QtWidgets.QVBoxLayout(self.page)
        widgets = {"MainAttributeEditorLayout": self.form, "AttributeEditor": self.ws}
        self.ws_state = {"AttributeEditor": True}
        self.saved = (holder.widget, holder.dock_control, holder.ws_visible, holder._set_ws)
        holder.widget = lambda name: widgets.get(name)
        holder.dock_control = lambda component: "AttributeEditor"
        holder.ws_visible = lambda name: self.ws_state.get(name, False)
        holder._set_ws = lambda name, visible: self.ws_state.__setitem__(name, bool(visible))

    def tearDown(self):
        (self.holder.widget, self.holder.dock_control, self.holder.ws_visible,
         self.holder._set_ws) = self.saved

    def test_take_moves_the_form_and_hides_maya_s_control(self):
        record = self.holder.take("Attribute Editor", "MainAttributeEditorLayout",
                                  self.page_layout)
        self.assertIs(self.form.parentWidget(), self.page)
        self.assertFalse(self.ws_state["AttributeEditor"])
        self.assertEqual(record, {"component": "Attribute Editor",
                                  "form": "MainAttributeEditorLayout", "ws": "AttributeEditor",
                                  "shown": True, "parent": "AEInner", "index": 1})

    def test_give_puts_it_back_at_its_index_and_shows_the_control(self):
        record = self.holder.take("Attribute Editor", "MainAttributeEditorLayout",
                                  self.page_layout)
        self.assertTrue(self.holder.give(record))
        self.assertIs(self.form.parentWidget(), self.inner)
        self.assertEqual(self.inner.layout().indexOf(self.form), 1)
        self.assertTrue(self.ws_state["AttributeEditor"])

    def test_a_control_that_was_hidden_stays_hidden(self):
        self.ws_state["AttributeEditor"] = False
        record = self.holder.take("Attribute Editor", "MainAttributeEditorLayout",
                                  self.page_layout)
        self.holder.give(record)
        self.assertFalse(self.ws_state["AttributeEditor"])

    def test_a_form_that_does_not_exist_is_no_record(self):
        self.assertIsNone(self.holder.take("Attribute Editor", "Nope", self.page_layout))


if __name__ == "__main__":
    unittest.main()
