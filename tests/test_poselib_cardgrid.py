"""The Pose Library's card grid on its own, offscreen (2026-10-02): the layout, the culled paint
(a paint of the top of a long library reads only the thumbnails it shows), the scaled-thumbnail
cache, the hit test, and the mouse - a click, a drag past the start distance, the middle-drag
blend, Esc - against a fake panel standing in for the window.

Spec: docs/superpowers/specs/2026-10-02-pose-library-design.md ("The window")
"""
import os
import shutil
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import maya_hubqt
    QT = maya_hubqt.qt()
except Exception:                                            # noqa: BLE001
    QT = None

from maya_poselib import cardgrid
from maya_poselib import look
from maya_poselib import store


class FakeScene(object):

    def __init__(self, log):
        self.log = log

    def snapshot_scene(self):
        self.log.append(("snapshot_scene",))
        return ["snap"]


class FakePanel(object):
    """What the canvas asks of the window, recorded."""

    def __init__(self):
        self.k = 1.0
        self.log = []
        self.scene = FakeScene(self.log)
        self.scroll = None
        self.blend = False
        self.aim_kind = "character"

    def thumb_side(self):
        return 220

    def pick(self, path):
        self.log.append(("pick", path))

    def apply_card(self, path):
        self.log.append(("apply_card", path))

    def context_actions(self, path):
        return []

    def aim(self, gx, gy, path, snap):
        self.log.append(("aim", path, snap))
        if self.aim_kind == "character":
            return {"kind": "character", "label": "Manny_Rig1", "root": "|Manny_Rig1:root"}
        return {"kind": "none", "text": "no floor under the cursor"}

    def drop_at(self, gx, gy, path, snap):
        self.log.append(("drop_at", path, snap))

    def say(self, text):
        self.log.append(("say", text))

    def blend_drag(self, path, dx):
        self.log.append(("blend_drag", path, dx))
        self.blend = True
        return 0.5

    def blend_release(self):
        self.log.append(("blend_release",))
        self.blend = False

    def blend_cancel(self):
        self.log.append(("blend_cancel",))
        self.blend = False

    def blending(self):
        return self.blend


def card(path, name, thumbnail="", kind="character", label="Manny [rig]"):
    return store.Card(path, "", name, "2026-10-02T18:00:00", "Eugene", label, kind, 1, [],
                      thumbnail)


@unittest.skipIf(QT is None, "no Qt")
class CanvasCase(unittest.TestCase):

    def setUp(self):
        self.app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])
        self.tmp = tempfile.mkdtemp(prefix="skeldar_poselib_cardgrid_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.panel = FakePanel()
        self.canvas = cardgrid.make_canvas(self.panel)
        self.canvas.move(3000, 3000)
        self.addCleanup(self.canvas.deleteLater)

    def images(self, count):
        """`count` card folders, each with a thumbnail of its own colour."""
        cards = []
        for index in range(count):
            folder = os.path.join(self.tmp, "C%03d.pose" % index).replace("\\", "/")
            os.makedirs(folder)
            image = QT.QtGui.QImage(16, 16, QT.QtGui.QImage.Format_RGB32)
            image.fill(QT.QtGui.QColor(index % 256, 80, 200))
            path = folder + "/" + store.THUMB_FILE
            image.save(path, "JPG")
            cards.append(card(folder, "C%03d" % index, path))
        return cards

    def render(self, region=None):
        image = QT.QtGui.QImage(self.canvas.size(), QT.QtGui.QImage.Format_ARGB32)
        image.fill(0)
        if region is None:
            self.canvas.render(image)
        else:
            self.canvas.render(image, QT.QtCore.QPoint(), QT.QtGui.QRegion(*region))
        return image

    def mouse(self, kind, local, button, buttons=None):
        Qt = QT.QtCore.Qt
        types = {"press": QT.QtCore.QEvent.MouseButtonPress,
                 "move": QT.QtCore.QEvent.MouseMove,
                 "release": QT.QtCore.QEvent.MouseButtonRelease}
        buttons = button if buttons is None else buttons
        event = QT.QtGui.QMouseEvent(types[kind], QT.QtCore.QPointF(local),
                                     QT.QtCore.QPointF(self.canvas.mapToGlobal(local)),
                                     button, buttons, Qt.NoModifier)
        {"press": self.canvas.mousePressEvent, "move": self.canvas.mouseMoveEvent,
         "release": self.canvas.mouseReleaseEvent}[kind](event)

    def centre(self, index):
        x, y, w, h = self.canvas.rects()[index]
        return QT.QtCore.QPoint(x + w // 2, y + h // 2)


class Layout(CanvasCase):

    def test_the_canvas_is_laid_out_by_look(self):
        cards = self.images(7)
        self.canvas.set_cards(cards)
        self.canvas.fit(500, 300)
        _cols, rects, height = look.grid(500, 7, look.CELL_DEFAULT, 1.0)
        self.assertEqual(self.canvas.rects(), rects)
        self.assertEqual(self.canvas.height(), max(height, 300))
        self.assertEqual(self.canvas.width(), 500)

    def test_the_card_size_is_the_slider_s(self):
        self.canvas.set_cards(self.images(3))
        self.canvas.fit(800)
        self.canvas.set_cell(look.CELL_MAX)
        self.canvas.fit(800)
        self.assertEqual(self.canvas.rects()[0][2], look.CELL_MAX)

    def test_the_hit_test_names_the_card(self):
        cards = self.images(3)
        self.canvas.set_cards(cards)
        self.canvas.fit(500)
        point = self.centre(2)
        self.assertEqual(self.canvas.card_at(point.x(), point.y()).path, cards[2].path)
        self.assertIsNone(self.canvas.card_at(-5, -5))

    def test_only_the_cards_on_screen_are_read(self):
        cards = self.images(120)
        self.canvas.set_cards(cards)
        self.canvas.fit(500)
        self.assertGreater(self.canvas.height(), 2000)
        self.render(region=(0, 0, 500, 300))
        shown = look.visible(self.canvas.rects(), 0, 300, 1.0)
        self.assertTrue(0 < len(shown) < 20)
        self.assertEqual(len(self.canvas.pixmaps), len(shown))
        self.assertEqual(set(key[0] for key in self.canvas.pixmaps),
                         set(cards[index].thumbnail for index in shown))

    def test_an_empty_library_paints_its_line(self):
        self.canvas.set_cards([], "No poses yet")
        self.canvas.fit(400, 200)
        image = self.render()
        inked = sum(1 for x in range(0, image.width(), 2) for y in range(0, 60, 2)
                    if image.pixelColor(x, y).lightness() > 120)
        self.assertGreater(inked, 5)


class Cache(CanvasCase):

    def test_a_thumbnail_is_scaled_once_per_size(self):
        cards = self.images(1)
        first = self.canvas.thumb(cards[0].thumbnail, 64)
        self.assertIs(self.canvas.thumb(cards[0].thumbnail, 64), first)
        self.assertEqual((first.width(), first.height()), (64, 64))
        self.assertIsNot(self.canvas.thumb(cards[0].thumbnail, 32), first)

    def test_no_thumbnail_is_none(self):
        self.assertIsNone(self.canvas.thumb("", 64))
        self.assertIsNone(self.canvas.thumb(self.tmp + "/nothing.jpg", 64))

    def test_forget_drops_one_card_or_all(self):
        cards = self.images(2)
        for one in cards:
            self.canvas.thumb(one.thumbnail, 64)
        self.canvas.forget(cards[0].path)
        self.assertEqual([key[0] for key in self.canvas.pixmaps], [cards[1].thumbnail])
        self.canvas.forget()
        self.assertEqual(self.canvas.pixmaps, {})

    def test_a_layout_keeps_only_the_sizes_in_use(self):
        cards = self.images(2)
        self.canvas.set_cards(cards)
        self.canvas.thumb(cards[0].thumbnail, 77)
        self.canvas.thumb(cards[0].thumbnail, self.panel.thumb_side())
        self.canvas.fit(500)
        sides = set(key[1] for key in self.canvas.pixmaps)
        self.assertNotIn(77, sides)
        self.assertIn(self.panel.thumb_side(), sides)

    def test_scaled_crops_the_centre_square(self):
        wide = QT.QtGui.QPixmap(200, 100)
        wide.fill(QT.QtGui.QColor("#ff0000"))
        painter = QT.QtGui.QPainter(wide)
        painter.fillRect(100, 0, 100, 100, QT.QtGui.QColor("#0000ff"))
        painter.end()
        square = cardgrid.scaled(wide, 50).toImage()
        self.assertEqual((square.width(), square.height()), (50, 50))
        self.assertGreater(square.pixelColor(5, 25).red(), 200)      # the left half's red
        self.assertGreater(square.pixelColor(45, 25).blue(), 200)    # the right half's blue
        self.assertIsNone(cardgrid.scaled(QT.QtGui.QPixmap(), 50))


class Mouse(CanvasCase):

    def setUp(self):
        CanvasCase.setUp(self)
        self.cards = self.images(3)
        self.canvas.set_cards(self.cards)
        self.canvas.fit(500)

    def test_a_click_picks(self):
        point = self.centre(1)
        self.mouse("press", point, QT.QtCore.Qt.LeftButton)
        self.mouse("release", point, QT.QtCore.Qt.LeftButton)
        self.assertIn(("pick", self.cards[1].path), self.panel.log)
        self.assertIsNone(self.canvas._drag)

    def test_a_short_move_is_no_drag(self):
        point = self.centre(0)
        self.mouse("press", point, QT.QtCore.Qt.LeftButton)
        near = point + QT.QtCore.QPoint(2, 1)
        self.mouse("move", near, QT.QtCore.Qt.NoButton, QT.QtCore.Qt.LeftButton)
        self.assertIsNone(self.canvas._drag)

    def test_a_drag_carries_the_ghost_and_drops_with_its_snapshot(self):
        point = self.centre(0)
        self.mouse("press", point, QT.QtCore.Qt.LeftButton)
        far = point + QT.QtCore.QPoint(-3000, 0)
        self.mouse("move", far, QT.QtCore.Qt.NoButton, QT.QtCore.Qt.LeftButton)
        ghost = self.canvas._drag["ghost"]
        self.assertEqual(ghost.objectName(), "skeldarPoseGhost")
        self.assertEqual(ghost.text, "C000 · onto Manny_Rig1")
        self.mouse("release", far, QT.QtCore.Qt.LeftButton)
        self.assertIn(("drop_at", self.cards[0].path, ["snap"]), self.panel.log)
        self.assertEqual(self.panel.log.count(("snapshot_scene",)), 1)

    def test_an_objects_card_reads_no_scene(self):
        self.canvas.set_cards([card(self.cards[0].path, "Cubes", kind="objects",
                                    label="objects")])
        self.canvas.fit(500)
        point = self.centre(0)
        self.mouse("press", point, QT.QtCore.Qt.LeftButton)
        self.mouse("move", point + QT.QtCore.QPoint(-3000, 0), QT.QtCore.Qt.NoButton,
                   QT.QtCore.Qt.LeftButton)
        self.assertNotIn(("snapshot_scene",), self.panel.log)

    def test_a_bad_aim_reads_red(self):
        self.panel.aim_kind = "none"
        point = self.centre(0)
        self.mouse("press", point, QT.QtCore.Qt.LeftButton)
        self.mouse("move", point + QT.QtCore.QPoint(-3000, 0), QT.QtCore.Qt.NoButton,
                   QT.QtCore.Qt.LeftButton)
        self.assertFalse(self.canvas._drag["ghost"].good)
        self.assertEqual(self.canvas._drag["ghost"].text, "no floor under the cursor")

    def test_the_middle_drag_is_the_blend(self):
        point = self.centre(2)
        Qt = QT.QtCore.Qt
        self.mouse("press", point, Qt.MiddleButton)
        self.mouse("move", point + QT.QtCore.QPoint(40, 9), Qt.NoButton, Qt.MiddleButton)
        self.mouse("release", point, Qt.MiddleButton, Qt.NoButton)
        self.assertIn(("blend_drag", self.cards[2].path, 40), self.panel.log)
        self.assertIn(("blend_release",), self.panel.log)

    def test_escape_cancels_the_blend(self):
        point = self.centre(2)
        Qt = QT.QtCore.Qt
        self.mouse("press", point, Qt.MiddleButton)
        self.mouse("move", point + QT.QtCore.QPoint(40, 0), Qt.NoButton, Qt.MiddleButton)
        self.canvas.keyPressEvent(QT.QtGui.QKeyEvent(QT.QtCore.QEvent.KeyPress, Qt.Key_Escape,
                                                     Qt.NoModifier))
        self.assertIn(("blend_cancel",), self.panel.log)


if __name__ == "__main__":
    unittest.main()
