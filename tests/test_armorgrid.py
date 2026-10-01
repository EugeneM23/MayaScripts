"""The Armor card's tiles, offscreen (2026-10-01): they paint, a click picks a row and tells the
scene, a worn row carries its pill, the right button offers Open scene - on a fake scene, so no
Maya scene is touched. The scene half is verify_armor.py's.

Spec: docs/superpowers/specs/2026-10-01-armor-techlimb-design.md
"""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import maya_hubqt
    QT = maya_hubqt.qt()
except Exception:                                            # noqa: BLE001
    QT = None

import maya_armorgrid as ag
from maya_scenesetup import catalog


class FakeScene(object):

    def __init__(self, worn=()):
        self.log = []
        self.worn_keys = set(worn)

    def scale(self):
        return 1.0

    def select(self, key):
        self.log.append(("select", key))

    def open_scene(self, key):
        self.log.append(("open_scene", key))
        return "opened " + key

    def worn(self):
        return set(self.worn_keys)

    def say(self, text):
        self.log.append(("say", text))


class Pure(unittest.TestCase):

    def test_the_pill_text(self):
        self.assertEqual(ag.WORN_TEXT, "equipped")

    def test_the_menu_label_is_the_portraits(self):
        self.assertEqual(ag.OPEN_SCENE, "Open scene")


@unittest.skipIf(QT is None, "no Qt")
class Grid(unittest.TestCase):

    def setUp(self):
        self.app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])
        self.scene = FakeScene()
        self.grid = ag.make_grid(self.scene, selected=None)
        self.grid.resize(330, self.grid.height_for(330))
        self.grid.move(3000, 3000)
        self.addCleanup(self.grid.deleteLater)

    def centre(self, index):
        x, y, w, h = self.grid.rects()[index]
        return QT.QtCore.QPoint(x + w // 2, y + h // 2)

    def render(self):
        image = QT.QtGui.QImage(self.grid.size(), QT.QtGui.QImage.Format_ARGB32)
        image.fill(0)
        self.grid.render(image)
        return image

    def click(self, point, button=None):
        button = button or QT.QtCore.Qt.LeftButton
        for kind in (QT.QtCore.QEvent.MouseButtonPress, QT.QtCore.QEvent.MouseButtonRelease):
            event = QT.QtGui.QMouseEvent(kind, QT.QtCore.QPointF(point),
                                         QT.QtCore.QPointF(self.grid.mapToGlobal(point)),
                                         button, button, QT.QtCore.Qt.NoModifier)
            QT.QtWidgets.QApplication.sendEvent(self.grid, event)

    def test_one_tile_per_row(self):
        self.assertEqual(len(self.grid.rects()), len(catalog.ARMOR))
        self.assertEqual(self.grid.keys, [row.key for row in catalog.ARMOR])

    def test_it_paints_ink(self):
        image = self.render()
        inked = sum(1 for x in range(0, image.width(), 4)
                    for y in range(0, image.height(), 4)
                    if image.pixelColor(x, y).alpha() > 0)
        self.assertGreater(inked, 200)

    def test_every_row_has_its_icon_loaded(self):
        for row in catalog.ARMOR:
            self.assertIn(row.key, self.grid.pixmaps)

    def test_a_click_picks_and_tells_the_scene(self):
        self.click(self.centre(0))
        self.assertEqual(self.grid.selected, "Tech_Limb")
        self.assertIn(("select", "Tech_Limb"), self.scene.log)

    def test_a_click_off_every_tile_picks_nothing(self):
        far = QT.QtCore.QPoint(self.grid.width() - 2, self.grid.height() - 2)
        self.assertIsNone(self.grid.key_at(far.x(), far.y()))
        self.click(far)
        self.assertEqual(self.scene.log, [])

    def test_a_worn_row_draws_its_pill(self):
        plain = self.render()
        self.scene.worn_keys = {"Tech_Limb"}
        self.grid.refresh()
        self.assertEqual(self.grid.worn, {"Tech_Limb"})
        pilled = self.render()
        differ = sum(1 for x in range(0, plain.width(), 2)
                     for y in range(0, plain.height(), 2)
                     if plain.pixel(x, y) != pilled.pixel(x, y))
        self.assertGreater(differ, 20)

    def test_the_selected_tile_is_lit(self):
        plain = self.render()
        self.grid.set_selected("Tech_Limb")
        lit = self.render()
        self.assertNotEqual(plain, lit)

    def test_the_right_button_offers_open_scene(self):
        actions = self.grid.context_actions("Tech_Limb")
        self.assertEqual([label for label, _fn in actions], ["Open scene"])
        actions[0][1]()
        self.assertIn(("open_scene", "Tech_Limb"), self.scene.log)
        self.assertIn(("say", "opened Tech_Limb"), self.scene.log)

    def test_nothing_off_every_tile(self):
        self.assertEqual(self.grid.context_actions(None), [])

    def test_the_height_follows_the_width(self):
        self.assertEqual(self.grid.height_for(330), self.grid.sizeHint().height())
        self.assertGreater(self.grid.height_for(330), 0)


if __name__ == "__main__":
    unittest.main()
