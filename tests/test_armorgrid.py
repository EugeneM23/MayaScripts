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

    #  the drag (2026-10-01): a character under the cursor, or not
    aim = dict(kind="character", root="|Manny_Rig:root", label="Manny_Rig",
               text="onto Manny_Rig")
    hub = False

    def snapshot(self):
        return ["snap"]

    def target(self, gx, gy, snap):
        self.log.append(("target", snap))
        return self.aim

    def over_hub(self, gx, gy):
        return self.hub

    def equip_on(self, root, key):
        self.log.append(("equip_on", root, key))
        return "%s on %s" % (key, root)


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

    def test_the_name_lies_over_the_squares_bottom_on_a_shade(self):
        """2026-10-08: no strip under the tile - the name over the picture's
        bottom, on a shade that fades in from the picture."""
        import maya_hubstyle
        import maya_charlook as look
        self.grid.pixmaps = {}                 # no icon in the way of the pixels
        image = self.render()
        x, y, w, h = self.grid.rects()[0]
        nx, ny, nw, nh = look.name_rect((x, y, w, h), self.grid.k)
        self.assertEqual(ny + nh, y + h)

        def luma(px, py):
            c = image.pixelColor(int(px), int(py))
            return c.red() + c.green() + c.blue()
        self.assertEqual(image.pixelColor(x + 4, ny - 3).name(),
                         maya_hubstyle.TOKENS["field"])
        self.assertLess(luma(x + 4, y + h - 4), 0.7 * luma(x + 4, ny - 3))
        self.assertLess(luma(x + 4, y + h - 4), luma(x + 4, ny + 1))

    def test_the_worn_pill_sits_above_the_name(self):
        import maya_hubstyle
        import maya_charlook as look
        self.grid.pixmaps = {}
        self.scene.worn_keys = {"Tech_Limb"}
        self.grid.refresh()
        image = self.render()
        x, y, w, h = self.grid.rects()[0]
        nh = look.name_rect((x, y, w, h), self.grid.k)[3]
        pad = int(4 * self.grid.k)
        mid = y + h - nh - pad - int(8 * self.grid.k)
        self.assertEqual(image.pixelColor(x + pad + 2, mid).name(),
                         maya_hubstyle.TOKENS["ok_tint"])

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


@unittest.skipIf(QT is None, "no Qt")
class Drag(unittest.TestCase):
    """2026-10-01, «Броню тоже можно перетаскивать на персонажа - да, как
    оружие»: a press dragged past the start distance carries the icon; on a
    character in a viewport the piece goes on him, anywhere else nothing."""

    setUp = Grid.setUp
    centre = Grid.centre
    click = Grid.click

    def mouse(self, kind, point, button=None, buttons=None):
        Qt = QT.QtCore.Qt
        button = Qt.LeftButton if button is None else button
        buttons = button if buttons is None else buttons
        types = {"press": QT.QtCore.QEvent.MouseButtonPress,
                 "move": QT.QtCore.QEvent.MouseMove,
                 "release": QT.QtCore.QEvent.MouseButtonRelease}
        event = QT.QtGui.QMouseEvent(types[kind], QT.QtCore.QPointF(point),
                                     QT.QtCore.QPointF(self.grid.mapToGlobal(point)),
                                     button, buttons, Qt.NoModifier)
        {"press": self.grid.mousePressEvent, "move": self.grid.mouseMoveEvent,
         "release": self.grid.mouseReleaseEvent}[kind](event)

    def test_a_drop_on_a_character_equips_it_there(self):
        start = self.centre(0)
        self.mouse("press", start)
        self.assertIsNone(self.grid._drag)
        far = start + QT.QtCore.QPoint(-2000, 40)
        self.mouse("move", far, button=QT.QtCore.Qt.NoButton,
                   buttons=QT.QtCore.Qt.LeftButton)
        self.assertIsNotNone(self.grid._drag)
        self.assertEqual(self.grid._drag["ghost"].text, "Tech Limb · onto Manny_Rig")
        self.mouse("release", far)
        self.assertIsNone(self.grid._drag)
        self.assertIn(("equip_on", "|Manny_Rig:root", "Tech_Limb"), self.scene.log)

    def test_off_every_character_nothing_and_the_line_says_why(self):
        self.scene.aim = dict(kind="none", text="drop onto a character")
        self.grid.drop_at(-2000, 40, "Tech_Limb")
        self.assertFalse([e for e in self.scene.log if e[0] == "equip_on"])
        self.assertIn(("say", "drop onto a character"), self.scene.log)

    def test_back_on_the_hub_nothing(self):
        self.scene.hub = True
        self.grid.drop_at(-2000, 40, "Tech_Limb")
        self.assertFalse([e for e in self.scene.log if e[0] in ("equip_on", "target")])

    def test_a_click_is_no_drag(self):
        self.click(self.centre(0))
        self.assertIsNone(self.grid._drag)
        self.assertFalse([e for e in self.scene.log if e[0] == "equip_on"])

    def test_the_right_button_and_escape_cancel(self):
        start = self.centre(0)
        self.mouse("press", start)
        self.mouse("move", start + QT.QtCore.QPoint(60, 60),
                   button=QT.QtCore.Qt.NoButton, buttons=QT.QtCore.Qt.LeftButton)
        self.mouse("press", start, button=QT.QtCore.Qt.RightButton)
        self.assertIsNone(self.grid._drag)
        self.assertIn(("say", "cancelled"), self.scene.log)
        self.mouse("press", start)
        self.mouse("move", start + QT.QtCore.QPoint(60, 60),
                   button=QT.QtCore.Qt.NoButton, buttons=QT.QtCore.Qt.LeftButton)
        self.grid.keyPressEvent(QT.QtGui.QKeyEvent(QT.QtCore.QEvent.KeyPress,
                                                   QT.QtCore.Qt.Key_Escape,
                                                   QT.QtCore.Qt.NoModifier))
        self.assertIsNone(self.grid._drag)


if __name__ == "__main__":
    unittest.main()
