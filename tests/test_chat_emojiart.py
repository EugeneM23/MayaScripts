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


import shutil
import tempfile


class NoAnimation(unittest.TestCase):
    """2026-11-19: every emoji is its still picture - nothing is fetched, decoded or played."""

    def test_the_animation_machinery_is_gone(self):
        for gone in ("Animated", "animated", "anim_of", "frame_at", "decode", "NOTO",
                     "FRAME_MS", "_fetch", "_spawn", "_ANIM_ATTR"):
            self.assertFalse(hasattr(A, gone), gone)

    def test_nothing_reaches_the_network(self):
        import inspect
        source = inspect.getsource(A)
        for word in ("urllib", "urlopen", "threading", "QImageReader"):
            self.assertNotIn(word, source, word)


class NoSheetHeld(unittest.TestCase):
    def setUp(self):
        _app()

    def test_release_drops_every_sheet_and_the_cells_keep_their_ink(self):
        import time
        A.release()
        A._OK.clear()
        glyphs = [r["g"] for r in emoji.index().records if r["sheet"] == emoji.index().records[0]["sheet"]][:50]
        t = time.time()
        cells = [A.image(g) for g in glyphs]
        self.assertLess(time.time() - t, 2.0)
        self.assertLessEqual(len(A._SHEETS), A.SHEETS_KEPT)
        A.release()
        self.assertEqual(len(A._SHEETS), 0)
        self.assertGreater(sum(1 for c in cells if _ink(c) > 30), len(cells) // 2)

    def test_at_most_two_sheets_are_held(self):
        A.release()
        for sheet in {r["sheet"] for r in emoji.index().records}:
            A._sheet(sheet)
        self.assertLessEqual(len(A._SHEETS), 2)
        A.release()


class BrokenSheet(unittest.TestCase):
    """emoji.json is fine but one sheet is corrupt (or gone): its emoji stay text."""

    def setUp(self):
        _app()
        self.dir = tempfile.mkdtemp()
        real = A.folder()
        self.fire = "\U0001F525"
        self.sheet = emoji.index().cell(self.fire)[0]
        for name in os.listdir(real):
            shutil.copy(os.path.join(real, name), self.dir)
        self.old_folder = A.folder
        A.folder = lambda: self.dir
        self._clear()

    def tearDown(self):
        A.folder = self.old_folder
        self._clear()
        shutil.rmtree(self.dir, ignore_errors=True)

    def _clear(self):
        A.release()
        A._OK.clear()
        A._BAD.clear()
        A._PIX.clear()

    def _break(self, remove):
        path = os.path.join(self.dir, self.sheet)
        if remove:
            os.remove(path)
        else:
            with open(path, "wb") as f:
                f.write(b"not a webp")
        self._clear()

    def _check(self):
        self.assertIsNone(A.image(self.fire))
        self.assertFalse(A._known(self.fire))
        out = A.rich("a " + self.fire, 20)
        self.assertNotIn("<img", out)
        self.assertIn(self.fire, out)
        font = QtGui.QFont()
        font.setPixelSize(14)
        # offscreen Qt has no font to draw text with: the line is judged by its parts
        parts, _fm, _side = A._parts(self.fire, font)
        self.assertEqual([k for k, _p, _w in parts], ["text"])
        img = QtGui.QImage(120, 24, QtGui.QImage.Format_ARGB32)
        img.fill(QtCore.Qt.transparent)
        p = QtGui.QPainter(img)
        used = A.draw_line(p, QtCore.QRectF(0, 0, 120, 24), self.fire, font,
                           QtGui.QColor("white"))
        p.end()
        self.assertGreater(used, 0)

    def test_a_corrupt_sheet_falls_back_to_text(self):
        self._break(remove=False)
        self._check()

    def test_a_missing_sheet_falls_back_to_text(self):
        self._break(remove=True)
        self._check()
        self.assertIn(self.sheet, A._BAD)

    def test_a_good_sheet_still_makes_pictures(self):
        self.assertTrue(A._known(self.fire))
        self.assertIn("<img", A.rich(self.fire, 20))
