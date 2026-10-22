"""maya_chat.emojiart offscreen."""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tests  # noqa: F401  (puts SkeldarAnim/ on sys.path)

from PySide6 import QtCore, QtGui, QtWidgets

from maya_chat import emoji
from maya_chat import emojiart as A


def _app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _ink(img):
    img = img.convertToFormat(QtGui.QImage.Format_ARGB32)
    return sum(1 for y in range(0, img.height(), 3) for x in range(0, img.width(), 3)
               if img.pixelColor(x, y).alpha() > 40)


class Pictures(unittest.TestCase):
    def setUp(self):
        _app()

    def test_every_record_has_ink(self):
        for rec in emoji.index().records[::25]:
            img = A.image(rec["g"])
            self.assertIsNotNone(img, rec["g"])
            self.assertGreater(_ink(img), 30, rec["g"])

    def test_a_tone_is_another_picture(self):
        base, toned = A.image("\U0001F44D"), A.image("\U0001F44D\U0001F3FF")
        self.assertNotEqual(base.constBits().tobytes(), toned.constBits().tobytes())

    def test_unknown_is_none(self):
        self.assertIsNone(A.image("x"))
        self.assertIsNone(A.pixmap("x", 20))

    def test_pixmap_size_and_cache(self):
        pm = A.pixmap("\U0001F525", 24)
        self.assertEqual((pm.width(), pm.height()), (24, 24))
        self.assertIs(A.pixmap("\U0001F525", 24), pm)


class Rich(unittest.TestCase):
    def setUp(self):
        _app()

    def test_images_links_and_escapes(self):
        out = A.rich("a<b> \U0001F525 https://x.io/y\nz", 20)
        self.assertIn("a&lt;b&gt; ", out)
        self.assertIn('<img src="emoji:1f525" width="20" height="20"', out)
        self.assertIn('<a href="https://x.io/y">', out)
        self.assertIn("<br>z", out)

    def test_a_document_draws_the_picture(self):
        doc = QtGui.QTextDocument()
        A.register(doc, "\U0001F525", 32)
        doc.setHtml(A.rich("\U0001F525", 32))
        res = doc.resource(QtGui.QTextDocument.ImageResource, QtCore.QUrl("emoji:1f525"))
        self.assertIsNotNone(res)
        img = QtGui.QImage(64, 64, QtGui.QImage.Format_ARGB32)
        img.fill(QtCore.Qt.transparent)
        p = QtGui.QPainter(img)
        doc.drawContents(p)
        p.end()
        self.assertGreater(_ink(img), 20)


class Line(unittest.TestCase):
    def setUp(self):
        _app()
        self.font = QtGui.QFont()
        self.font.setPixelSize(14)

    def _draw(self, text, width):
        img = QtGui.QImage(width, 24, QtGui.QImage.Format_ARGB32)
        img.fill(QtCore.Qt.transparent)
        p = QtGui.QPainter(img)
        used = A.draw_line(p, QtCore.QRectF(0, 0, width, 24), text, self.font, QtGui.QColor("white"))
        p.end()
        return used, img

    def test_fits_and_draws(self):
        used, img = self._draw("ok \U0001F525", 200)
        self.assertAlmostEqual(used, A.line_width("ok \U0001F525", self.font), delta=1)
        self.assertGreater(_ink(img), 5)

    def test_elides_to_the_rect(self):
        used, _img = self._draw("long " * 40 + "\U0001F525", 80)
        self.assertLessEqual(used, 80)
