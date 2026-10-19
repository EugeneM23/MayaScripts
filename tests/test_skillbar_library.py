"""The skill library drawer, offscreen (2026-10-19): chips, categories, search, a chip clicked into
the cell it was opened for, a chip dragged onto the bar, the fold."""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import maya_hubqt
    QT = maya_hubqt.qt()
except Exception:                                            # noqa: BLE001
    QT = None

import maya_hubstyle
from maya_skillbar import library, look, sources
from maya_timebar import bar

from tests.test_skillbar_grid import SkillLink

ENTRIES = [("Tools", {"kind": "cmd", "key": "tools.aim"}, "Aim"),
           ("Tools", {"kind": "cmd", "key": "tools.knot"}, "Knot"),
           ("Maya", {"kind": "maya", "command": "GraphEditor"}, "GraphEditor"),
           ("Scripts", {"kind": "script", "lang": "python", "code": "x=1", "label": "X"}, "X")]


def fake_entries(category, search=""):
    found = [e for e in ENTRIES if category == "All" or e[0] == category]
    return sources.filtered(found, search)


class Geometry(unittest.TestCase):

    def test_chip_rects_wrap_and_hit(self):
        rects = library.chip_rects(400, 10)
        self.assertEqual(len(rects), 10)
        self.assertGreater(rects[5][1], rects[0][1])          # wrapped
        x, y, w, h = rects[3]
        self.assertEqual(library.chip_at(x + 2, y + 2, rects), 3)
        self.assertIsNone(library.chip_at(1, 1, rects))
        self.assertGreater(library.content_height(400, 10), rects[-1][1])


@unittest.skipIf(QT is None, "no Qt")
class Drawer(unittest.TestCase):

    motion = False

    def setUp(self):
        self.app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])
        self.link = SkillLink(look.defaults())
        self.strip = bar.make(self.link, 1.0, maya_hubstyle.TOKENS, motion=self.motion)
        self.strip.resize(1100, 150)
        self.strip.move(200, 900)
        self.strip.show()
        self.strip.show_page(6)
        self.app.processEvents()
        self.addCleanup(self.strip.deleteLater)
        self.model = self.link.model

    def drawer(self, target=None):
        d = library.make(self.strip, target, (400, 900), entries=fake_entries, motion=self.motion)
        d.open()
        self.app.processEvents()
        self.addCleanup(lambda: library.close(instant=True))
        return d

    def mouse(self, widget, kind, x, y, button, buttons):
        local = QT.QtCore.QPointF(x, y)
        event = QT.QtGui.QMouseEvent(kind, local, QT.QtCore.QPointF(widget.mapToGlobal(local.toPoint())),
                                     button, buttons, QT.QtCore.Qt.NoModifier)
        QT.QtWidgets.QApplication.sendEvent(widget, event)

    def click(self, widget, x, y):
        E, Qt = QT.QtCore.QEvent, QT.QtCore.Qt
        self.mouse(widget, E.MouseButtonPress, x, y, Qt.LeftButton, Qt.LeftButton)
        self.mouse(widget, E.MouseButtonRelease, x, y, Qt.LeftButton, Qt.NoButton)

    def chip(self, d, i):
        x, y, w, h = d.rects()[i]
        return x + w / 2, y + h / 2

    def test_it_stands_over_the_bar_as_wide(self):
        d = self.drawer()
        self.assertEqual(d.width(), self.strip.width())
        self.assertLess(d.geometry().bottom(), self.strip.mapToGlobal(QT.QtCore.QPoint(0, 0)).y())
        self.assertEqual(len(d.found), 4)
        self.assertTrue(library.is_open())

    def test_categories_and_search(self):
        d = self.drawer()
        x, y, w, h = d.cat_rects()[list(sources.CATEGORIES).index("Tools")]
        self.click(d, x + w / 2, y + h / 2)
        self.assertEqual([e[2] for e in d.found], ["Aim", "Knot"])
        d.search.setText("kn")
        self.assertEqual([e[2] for e in d.found], ["Knot"])

    def test_a_chip_clicked_goes_to_its_cell_and_the_drawer_folds(self):
        d = self.drawer(("cell", 6, 0, 4))
        self.click(d, *self.chip(d, 2))
        self.assertEqual(look.item_at(self.model.data(), 6, 0, 4), {"kind": "maya", "command": "GraphEditor"})
        self.assertFalse(library.is_open())

    def test_with_no_cell_a_chip_goes_to_the_page_shown(self):
        d = self.drawer()
        self.click(d, *self.chip(d, 0))
        self.assertEqual(look.item_at(self.model.data(), 6, 0, 0), {"kind": "cmd", "key": "tools.aim"})
        self.assertTrue(library.is_open())            # it stays for more

    def test_a_chip_dragged_onto_a_cell(self):
        E, Qt = QT.QtCore.QEvent, QT.QtCore.Qt
        d = self.drawer()
        x, y = self.chip(d, 1)
        cell = self.strip.skill_grid.cell_rect(0, 2).center()
        g = self.strip.skill_grid.mapToGlobal(cell.toPoint())
        local = d.mapFromGlobal(g)
        self.mouse(d, E.MouseButtonPress, x, y, Qt.LeftButton, Qt.LeftButton)
        self.mouse(d, E.MouseMove, x + 30, y + 30, Qt.NoButton, Qt.LeftButton)
        self.assertIsNotNone(d.drag)
        self.mouse(d, E.MouseMove, local.x(), local.y(), Qt.NoButton, Qt.LeftButton)
        self.assertEqual(self.strip.lit_aim, ("cell", 6, 0, 2))
        self.mouse(d, E.MouseButtonRelease, local.x(), local.y(), Qt.LeftButton, Qt.NoButton)
        self.assertEqual(look.item_at(self.model.data(), 6, 0, 2), {"kind": "cmd", "key": "tools.knot"})
        self.assertIsNone(self.strip.lit_aim)

    def test_it_paints(self):
        d = self.drawer()
        image = QT.QtGui.QImage(d.size(), QT.QtGui.QImage.Format_ARGB32)
        image.fill(0)
        d.render(image)
        self.assertFalse(getattr(d, "_failed", False))


@unittest.skipIf(QT is None, "no Qt")
class DrawerMotion(Drawer):

    motion = True

    def test_chips_pop_in_from_the_point_and_fold(self):
        d = self.drawer()
        x, y = self.chip(d, 0)
        scale, _o = d._entrance(x, y)
        self.assertLess(scale, 1.0)
        d.t0 -= 5000
        self.assertEqual(d._entrance(x, y), (1.0, 1.0))
        d.fold()
        self.assertIsNotNone(d.folding)

    def test_a_chip_clicked_goes_to_its_cell_and_the_drawer_folds(self):
        d = self.drawer(("cell", 6, 0, 4))
        self.click(d, *self.chip(d, 2))
        self.assertEqual(look.item_at(self.model.data(), 6, 0, 4), {"kind": "maya", "command": "GraphEditor"})
        self.assertIsNotNone(d.folding)


if __name__ == "__main__":
    unittest.main()
