"""The skill bar in the Time Bar's strip, offscreen (2026-10-19): the page row, a page of cells in
place of the time rows, running, the menus, a cell dragged, text dropped, the burst.

Spec: docs/superpowers/specs/2026-10-19-skill-bar-design.md
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
from maya_skillbar import look, skills
from maya_timebar import bar

from tests.test_timebar_bar import FakeLink


class SkillLink(FakeLink):
    """The fake link with a skill model in memory."""

    def __init__(self, data=None):
        FakeLink.__init__(self)
        self.model = skills.MemorySkills(data)
        self.heights = []

    def skills(self):
        return self.model

    def page_height(self, strip):
        self.heights.append(strip.skills.page())


@unittest.skipIf(QT is None, "no Qt")
class Base(unittest.TestCase):

    motion = False
    rows = 2

    def setUp(self):
        self.app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])
        self.link = SkillLink(look.defaults())
        self.strip = bar.make(self.link, 1.0, maya_hubstyle.TOKENS, motion=self.motion)
        self.strip.resize(1200, 160)
        self.strip.move(3000, 3000)
        self.strip.show()
        self.app.processEvents()
        self.addCleanup(self.strip.deleteLater)
        self.model = self.link.model

    def mouse(self, widget, kind, x, y, button, buttons):
        local = QT.QtCore.QPointF(x, y)
        event = QT.QtGui.QMouseEvent(kind, local, QT.QtCore.QPointF(widget.mapToGlobal(local.toPoint())),
                                     button, buttons, QT.QtCore.Qt.NoModifier)
        QT.QtWidgets.QApplication.sendEvent(widget, event)

    def click(self, widget, x, y, button=None):
        E, Qt = QT.QtCore.QEvent, QT.QtCore.Qt
        button = button or Qt.LeftButton
        self.mouse(widget, E.MouseButtonPress, x, y, button, button)
        self.mouse(widget, E.MouseButtonRelease, x, y, button, Qt.NoButton)

    def centre(self, r, c):
        rect = self.strip.skill_grid.cell_rect(r, c).center()
        return rect.x(), rect.y()

    def show(self, n):
        self.strip.show_page(n)
        self.app.processEvents()

    def image(self, widget):
        image = QT.QtGui.QImage(widget.size(), QT.QtGui.QImage.Format_ARGB32)
        image.fill(0)
        widget.render(image)
        return image


class Pages(Base):

    rows = 1

    def test_f1_shows_the_time_rows_and_the_page_row(self):
        st = self.strip
        self.assertTrue(st.tabs.isVisible())
        self.assertTrue(st.time_box.isVisible())
        self.assertFalse(st.skill_grid.isVisible())
        self.assertEqual(st.page(), 1)

    def test_a_skill_page_takes_the_time_rows_place(self):
        st = self.strip
        self.show(3)
        self.assertFalse(st.time_box.isVisible())
        self.assertTrue(st.skill_grid.isVisible())
        self.assertEqual(self.link.heights[-1], 3)
        self.show(1)
        self.assertTrue(st.time_box.isVisible())

    def test_ten_cells_in_one_row_as_tall_as_the_time_rows(self):
        st = self.strip
        time_h = st.time_height()
        self.show(2)
        grid = st.skill_grid
        self.assertLessEqual(abs(grid.height() - time_h), 2)
        self.assertEqual(grid.cols(), look.SLOTS)
        first, last = grid.cell_rect(0, 0), grid.cell_rect(0, look.SLOTS - 1)
        self.assertAlmostEqual(first.left(), grid.width() - last.right(), delta=1)   # centred
        self.assertGreater(first.height(), time_h * 0.7)
        self.assertEqual(grid.cell_at(*self.centre(0, 3)), (0, 3))

    def test_a_tab_click_shows_its_page(self):
        st = self.strip
        x, w = st.tabs.rects()[4]
        self.click(st.tabs, x + w / 2, st.tabs.height() / 2)
        self.assertEqual(st.page(), 5)

    def test_the_tabs_fit_and_hit(self):
        rects = self.strip.tabs.rects()
        self.assertEqual(len(rects), 12)
        self.assertLessEqual(rects[-1][0] + rects[-1][1], self.strip.tabs.width())
        self.assertEqual(self.strip.tabs.page_at(rects[2][0] + 2), 3)

    def test_pages_paint(self):
        for n in (1, 2, 3, 7):
            self.show(n)
            self.image(self.strip)            # no exception
        self.assertFalse(getattr(self.strip.skill_grid, "_failed", False))
        self.assertFalse(getattr(self.strip.tabs, "_failed", False))


class Cells(Base):

    def test_a_click_runs_its_skill(self):
        self.show(2)
        item = look.item_at(self.model.data(), 2, 0, 0)
        self.click(self.strip.skill_grid, *self.centre(0, 0))
        runs = [e for e in self.model.log if e[0] == "run"]
        self.assertEqual(runs[-1][1], item)
        self.assertIn(("say", "ran %s" % self.model.label(item)), self.model.log)

    def test_an_empty_cell_opens_the_library(self):
        self.show(9)
        self.click(self.strip.skill_grid, *self.centre(0, 2))
        self.assertIn(("library", ("cell", 9, 0, 2)), [e[:2] for e in self.model.log])

    def test_the_menus(self):
        st = self.strip
        rows = st.cell_rows(2, 0, 0)
        labels = [r[0] for r in rows if r]
        self.assertTrue(labels[1].startswith("Run"))
        self.assertIn("Clear", labels)
        self.assertNotIn("Rows", labels)
        dict((r[0], r[1]) for r in rows if r)["Clear"]()
        self.assertIsNone(look.item_at(self.model.data(), 2, 0, 0))
        empty = [r[0] for r in st.cell_rows(9, 0, 0) if r]
        self.assertIn("Script from the Script Editor", empty)
        page = [r[0] for r in st.page_rows(4) if r]
        self.assertIn("Rename page...", page)
        self.assertEqual([r[0] for r in st.page_rows(1) if r][0], "Show F1")

    def test_place_onto_a_cell_and_a_tab(self):
        st = self.strip
        item = {"kind": "maya", "command": "GraphEditor"}
        st.place_skill(("cell", 6, 0, 3), item)
        self.assertEqual(look.item_at(self.model.data(), 6, 0, 3), item)
        st.place_skill(("tab", 6), item)
        self.assertEqual(look.item_at(self.model.data(), 6, 0, 0), item)

    def test_move_swaps_and_sends_to_a_page(self):
        st = self.strip
        data = self.model.data()
        a, b = look.item_at(data, 2, 0, 0), look.item_at(data, 2, 0, 1)
        st.move_skill((2, 0, 0), ("cell", 2, 0, 1))
        self.assertEqual(look.item_at(self.model.data(), 2, 0, 1), a)
        self.assertEqual(look.item_at(self.model.data(), 2, 0, 0), b)
        st.move_skill((2, 0, 0), ("tab", 11))
        self.assertIsNone(look.item_at(self.model.data(), 2, 0, 0))
        self.assertEqual(look.item_at(self.model.data(), 11, 0, 0), b)

    def test_a_drag_of_a_cell_onto_another(self):
        E, Qt = QT.QtCore.QEvent, QT.QtCore.Qt
        st, grid = self.strip, self.strip.skill_grid
        self.show(2)
        a = look.item_at(self.model.data(), 2, 0, 0)
        x0, y0 = self.centre(0, 0)
        x1, y1 = self.centre(0, 3)
        self.mouse(grid, E.MouseButtonPress, x0, y0, Qt.LeftButton, Qt.LeftButton)
        self.mouse(grid, E.MouseMove, x0 + 20, y0, Qt.NoButton, Qt.LeftButton)
        self.assertIsNotNone(grid.drag)
        self.mouse(grid, E.MouseMove, x1, y1, Qt.NoButton, Qt.LeftButton)
        self.assertEqual(st.lit_aim, ("cell", 2, 0, 3))
        self.mouse(grid, E.MouseButtonRelease, x1, y1, Qt.LeftButton, Qt.NoButton)
        self.assertIsNone(grid.drag)
        self.assertEqual(look.item_at(self.model.data(), 2, 0, 3), a)
        self.assertEqual([e for e in self.model.log if e[0] == "run"], [])

    def test_aim_over_the_bar(self):
        st = self.strip
        self.show(4)
        g = st.skill_grid.mapToGlobal(QT.QtCore.QPoint(*map(int, self.centre(0, 1))))
        self.assertEqual(st.skill_aim(g.x(), g.y()), ("cell", 4, 0, 1))
        x, w = st.tabs.rects()[6]
        t = st.tabs.mapToGlobal(QT.QtCore.QPoint(int(x + w / 2), 5))
        self.assertEqual(st.skill_aim(t.x(), t.y()), ("tab", 7))
        f1 = st.tabs.mapToGlobal(QT.QtCore.QPoint(int(st.tabs.rects()[0][0] + 3), 5))
        self.assertIsNone(st.skill_aim(f1.x(), f1.y()))

    def test_text_dropped_is_a_script(self):
        st, grid = self.strip, self.strip.skill_grid
        self.show(8)
        data = QT.QtCore.QMimeData()
        data.setText("# hello\nprint(1)")
        x, y = self.centre(0, 2)
        event = QT.QtGui.QDropEvent(QT.QtCore.QPointF(x, y), QT.QtCore.Qt.CopyAction, data,
                                    QT.QtCore.Qt.LeftButton, QT.QtCore.Qt.NoModifier)
        grid.dropEvent(event)
        item = look.item_at(self.model.data(), 8, 0, 2)
        self.assertEqual(item["kind"], "script")
        self.assertEqual(item["label"], "hello")

    def test_a_waiting_skill_is_lit(self):
        self.show(2)
        item = look.item_at(self.model.data(), 2, 0, 1)
        before = self.image(self.strip.skill_grid)
        self.model.waiting_items = [item]
        after = self.image(self.strip.skill_grid)
        x, y = self.centre(0, 1)
        accent = QT.QtGui.QColor(maya_hubstyle.TOKENS["accent"])
        px = after.pixelColor(int(x) - 8, int(y) + 8)
        self.assertLess(abs(px.red() - accent.red()) + abs(px.green() - accent.green()), 40)
        self.assertNotEqual(before.pixelColor(int(x) - 8, int(y) + 8), px)


class OffTheBar(Base):

    def drag_off(self, r, c, x, y):
        E, Qt = QT.QtCore.QEvent, QT.QtCore.Qt
        grid = self.strip.skill_grid
        x0, y0 = self.centre(r, c)
        self.mouse(grid, E.MouseButtonPress, x0, y0, Qt.LeftButton, Qt.LeftButton)
        self.mouse(grid, E.MouseMove, x0 + 20, y0, Qt.NoButton, Qt.LeftButton)
        self.mouse(grid, E.MouseMove, x, y, Qt.NoButton, Qt.LeftButton)
        self.mouse(grid, E.MouseButtonRelease, x, y, Qt.LeftButton, Qt.NoButton)

    def test_a_character_dragged_off_the_bar_goes_into_the_scene(self):
        self.show(3)
        item = look.item_at(self.model.data(), 3, 0, 0)
        self.drag_off(0, 0, 300, -400)
        drops = [e for e in self.model.log if e[0] == "scene_drop"]
        self.assertEqual(drops[-1][1], item)
        self.assertIn(("say", "dropped"), self.model.log)
        self.assertIn(("scene_end",), self.model.log)
        self.assertEqual(look.item_at(self.model.data(), 3, 0, 0), item)     # the cell keeps it

    def test_a_tool_dragged_off_goes_into_the_scene_too(self):
        self.show(2)
        item = look.item_at(self.model.data(), 2, 0, 0)
        self.drag_off(0, 0, 300, -400)
        drops = [e for e in self.model.log if e[0] == "scene_drop"]
        self.assertEqual(drops[-1][1], item)
        self.assertIn(("say", "dropped"), self.model.log)


class Module(Base):
    """maya_skillbar's roads for the hotkeys and other panels' drags, on the live strip."""

    def setUp(self):
        Base.setUp(self)
        import sys
        import maya_skillbar
        import maya_timebar
        self.bar = maya_skillbar
        state = maya_timebar._state()
        self._saved = dict(state)
        state["bar"] = self.strip
        state.pop("edge", None)
        self.addCleanup(lambda: (state.clear(), state.update(self._saved)))
        self._wanted = maya_timebar.wanted
        maya_timebar.wanted = lambda: True
        self.addCleanup(lambda: setattr(maya_timebar, "wanted", self._wanted))
        self.sys = sys

    def test_page_shows_it(self):
        self.assertEqual(self.bar.page(4), "")
        self.assertEqual(self.strip.page(), 4)
        self.assertEqual(self.bar.page(1), "")
        self.assertTrue(self.strip.time_box.isVisible())
        self.assertEqual(self.bar.page(13), "")
        self.assertEqual(self.strip.page(), 1)

    def test_maya_s_own_slider_says_where_the_bar_is(self):
        import maya_timebar
        maya_timebar.wanted = lambda: False
        self.assertIn("Time Bar", self.bar.page(3))

    def test_aim_light_and_drop(self):
        self.show(5)
        g = self.strip.skill_grid.mapToGlobal(QT.QtCore.QPoint(*map(int, self.centre(0, 3))))
        self.assertEqual(self.bar.aim(g.x(), g.y()), ("cell", 5, 0, 3))
        self.bar.light(("cell", 5, 0, 3))
        self.assertEqual(self.strip.lit_aim, ("cell", 5, 0, 3))
        line = self.bar.drop(g.x(), g.y(), {"kind": "section", "key": "tools"})
        self.assertIn("F5", line)
        self.assertIsNone(self.strip.lit_aim)
        self.assertEqual(look.item_at(self.model.data(), 5, 0, 3), {"kind": "section", "key": "tools"})
        self.assertEqual(self.bar.drop(-5000, -5000, {"kind": "section", "key": "tools"}), "")
        self.assertIsNone(self.bar.aim(-5000, -5000))

    def test_a_number_pressed_twice_runs_the_first_row(self):
        self.show(2)
        item = look.item_at(self.model.data(), 2, 0, 2)
        self.bar._state()["armed"] = None
        self.assertEqual(self.bar.run_number(2), "")
        self.assertEqual([e for e in self.model.log if e[0] == "run"], [])   # once: armed, lit
        self.assertEqual(self.strip.skill_grid.armed["cell"], (0, 2))
        self.assertEqual(self.bar.run_number(2), "")
        self.assertEqual([e for e in self.model.log if e[0] == "run"][-1][1], item)
        self.assertIn((0, 2), self.strip.skill_grid.run_at)
        self.assertIsNone(self.strip.skill_grid.armed)

    def test_another_number_between_arms_itself(self):
        self.show(2)
        self.bar._state()["armed"] = None
        self.bar.run_number(2)
        self.bar.run_number(3)
        self.assertEqual([e for e in self.model.log if e[0] == "run"], [])
        self.assertEqual(self.strip.skill_grid.armed["cell"], (0, 3))

    def test_second_tap_window(self):
        self.bar._state()["armed"] = None
        self.assertFalse(self.bar.second_tap(4, now=1000, window=400))
        self.assertTrue(self.bar.second_tap(4, now=1300, window=400))
        self.assertFalse(self.bar.second_tap(4, now=1400, window=400))     # disarmed: a first again
        self.assertFalse(self.bar.second_tap(4, now=2000, window=400))     # too late
        self.assertFalse(self.bar.second_tap(5, now=2100, window=400))     # another key
        self.assertTrue(self.bar.second_tap(5, now=2200, window=400))

    def test_a_first_press_off_screen_says_to_press_again(self):
        self.strip.hide()
        self.bar._state()["armed"] = None
        self.bar.set_current_page(2)
        line = self.bar.run_number(1)
        self.assertIn("press 2 again", line)

    def test_the_number_keys_type_into_a_focused_field(self):
        field = QT.QtWidgets.QLineEdit()
        field.show()
        field.setFocus()
        self.app.processEvents()
        self.addCleanup(field.deleteLater)
        if QT.QtWidgets.QApplication.focusWidget() is not field:
            self.skipTest("no focus offscreen")
        self.show(2)
        self.assertEqual(self.bar.run_number(3), "")
        self.assertEqual(self.bar.run_number(3), "")
        self.assertEqual(field.text(), "44")
        self.assertEqual([e for e in self.model.log if e[0] == "run"], [])

    def test_the_number_page_is_the_last_skill_page_while_f1_shows(self):
        self.bar.set_current_page(5)
        self.bar.set_current_page(1)
        self.assertEqual(self.bar.number_page(), 5)

    def test_a_portrait_drag_lands_on_a_cell(self):
        import maya_chargrid
        self.show(3)
        g = self.strip.skill_grid.mapToGlobal(QT.QtCore.QPoint(*map(int, self.centre(0, 5))))
        self.assertEqual(maya_chargrid.skill_aim(g.x(), g.y()), ("cell", 3, 0, 5))


class Motion(Base):

    motion = True

    def test_a_page_pops_in_from_its_tab(self):
        st = self.strip
        st.show_page(3)
        grid = st.skill_grid
        self.assertIsNotNone(grid.pop)
        scale, opacity = grid.entrance(0, 0)
        self.assertLess(scale, 1.0)
        grid.pop["t0"] -= 5000
        self.assertEqual(grid.entrance(0, 0), (1.0, 1.0))
        self.assertFalse(grid.busy(st.clock()) and grid.pop is not None)

    def test_the_burst_reaches_the_cells(self):
        st = self.strip
        st.show_page(2)
        st.skill_grid.pop = None
        g = st.skill_grid.mapToGlobal(QT.QtCore.QPoint(0, 0))
        st.burst_at(g.x(), g.y(), True)
        near = st.skill_grid.entrance(0, 0)
        far = st.skill_grid.entrance(1, st.skill_grid.cols() - 1)
        self.assertLessEqual(near[0], 1.0)
        self.assertLessEqual(far[1], near[1])

    def test_a_run_glows(self):
        st = self.strip
        st.show_page(2)
        st.skill_grid.run_cell((0, 0))
        self.assertIn((0, 0), st.skill_grid.run_at)
        self.assertTrue(st.skill_grid.busy(st.clock()))


class CharacterFire(Base):
    """A character cell burns under the mouse as Animation Setup's portrait does (2026-10-22)."""

    motion = True

    def cell_of(self, kind):
        page = look.page_of(self.model.data(), 3)
        for key, item in page["cells"].items():
            if item.get("kind") == kind:
                return tuple(look.parse_key(key))
        self.fail("no %s cell on F3" % kind)

    def hover(self, cell):
        grid = self.strip.skill_grid
        x, y = self.centre(*cell)
        E, Qt = QT.QtCore.QEvent, QT.QtCore.Qt
        self.mouse(grid, E.MouseMove, x, y, Qt.NoButton, Qt.NoButton)

    def run_for(self, seconds):
        grid = self.strip.skill_grid
        for _ in range(int(seconds / 0.016)):
            grid.step(16.0)

    def test_a_character_cell_catches_fire_and_burns_out(self):
        from maya_skillbar import run as skillrun
        self.model.picture = skillrun.picture            # the real portraits
        self.show(3)
        grid = self.strip.skill_grid
        grid.pop, self.strip.entrance = None, None       # the page popped in: cells whole
        cell = self.cell_of("character")
        self.hover(cell)
        self.assertIn(cell, grid.fire)
        self.run_for(0.6)
        self.assertGreater(grid.fire[cell][1].power, 0.5)
        self.assertTrue(grid.busy(self.strip.clock()))
        hot = self.image(grid)
        fire, grid.fire = grid.fire, {}
        cold = self.image(grid)                          # the same hover, no fire
        grid.fire = fire
        rect = grid.cell_rect(*cell).toRect()
        changed = sum(1 for x in range(rect.left(), rect.right(), 2)
                      for y in range(rect.top(), rect.bottom(), 2)
                      if hot.pixel(x, y) != cold.pixel(x, y))
        self.assertGreater(changed, 20)
        grid.leaveEvent(QT.QtCore.QEvent(QT.QtCore.QEvent.Leave))
        self.run_for(4.0)
        self.assertEqual(grid.fire, {})

    def test_a_tool_cell_does_not_burn(self):
        self.show(3)
        grid = self.strip.skill_grid
        page = look.page_of(self.model.data(), 3)
        for key, item in page["cells"].items():
            if item.get("kind") != "character":
                r, c = look.parse_key(key)
                self.assertIsNone(grid.burning_model((r, c)))
                return

    def test_no_fire_without_motion(self):
        self.show(3)
        grid = self.strip.skill_grid
        self.strip.motion = False
        self.hover(self.cell_of("character"))
        self.assertEqual(grid.fire, {})


if __name__ == "__main__":
    unittest.main()
