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


def _webp_bytes():
    """A one-frame WebP standing in for Noto's file."""
    img = QtGui.QImage(8, 8, QtGui.QImage.Format_ARGB32)
    img.fill(QtGui.QColor("red"))
    buf = QtCore.QBuffer()
    buf.open(QtCore.QIODevice.WriteOnly)
    img.save(buf, "WEBP", 90)
    return bytes(buf.data())


class Animation(unittest.TestCase):
    def setUp(self):
        _app()
        self.dir = tempfile.mkdtemp()
        self.fetched = []

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def _anim(self, fail=False):
        def fetch(u):
            self.fetched.append(u)
            if fail:
                raise IOError("no")
            return _webp_bytes()
        return A.Animated(self.dir, fetch=fetch, spawn=lambda fn: fn())

    def test_downloads_once_then_has_frames(self):
        a = self._anim()
        frames = a.frames("1f525", 32)
        if frames is None:                      # spawn ran inline: the second ask has them
            frames = a.frames("1f525", 32)
        self.assertTrue(frames)
        self.assertEqual(self.fetched, [A.NOTO.format("1f525")])
        self.assertTrue(os.path.isfile(os.path.join(self.dir, "1f525.webp")))
        self.assertTrue(a.take_changed())
        self.assertFalse(a.take_changed())
        a.frames("1f525", 32)
        self.assertEqual(len(self.fetched), 1)

    def test_a_failure_is_not_asked_again(self):
        a = self._anim(fail=True)
        self.assertIsNone(a.frames("1f602", 32))
        self.assertIsNone(a.frames("1f602", 32))
        self.assertEqual(len(self.fetched), 1)
        self.assertIn("1f602", a.failed)

    def test_keeps_the_last_ones_only(self):
        a = self._anim()
        a.keep = 2
        for cp in ("a1", "a2", "a3"):
            a.frames(cp, 16)
        self.assertEqual(len(a._frames), 2)

    def test_frame_at_plays_once_and_rests_on_the_first(self):
        f0, f1 = QtGui.QImage(1, 1, QtGui.QImage.Format_ARGB32), QtGui.QImage(2, 2, QtGui.QImage.Format_ARGB32)
        frames = [(f0, 40), (f1, 80)]
        self.assertEqual(A.frame_at(frames, 10), (f0, False))
        self.assertEqual(A.frame_at(frames, 50), (f1, False))
        self.assertEqual(A.frame_at(frames, 80), (f0, True))
        self.assertEqual(A.frame_at([], 0), (None, True))

    def test_anim_of(self):
        self.assertEqual(A.anim_of("\U0001F602"), "1f602")
        self.assertEqual(A.anim_of("x"), "")


class BadFiles(Animation):
    def test_a_corrupt_cached_file_is_fetched_again(self):
        bad = os.path.join(self.dir, "1f525.webp")
        with open(bad, "wb") as f:
            f.write(b"<html>not a picture</html>")
        a = self._anim()
        frames = a.frames("1f525", 32)
        self.assertTrue(frames)
        self.assertEqual(self.fetched, [A.NOTO.format("1f525")])
        self.assertNotIn("1f525", a.failed)
        with open(bad, "rb") as f:
            self.assertEqual(f.read(), _webp_bytes())

    def test_garbage_from_the_fetch_fails_and_leaves_no_file(self):
        a = A.Animated(self.dir, fetch=lambda u: self.fetched.append(u) or b"garbage",
                       spawn=lambda fn: fn())
        self.assertIsNone(a.frames("1f602", 32))
        self.assertIn("1f602", a.failed)
        self.assertEqual(len(self.fetched), 1)
        self.assertFalse(os.path.exists(os.path.join(self.dir, "1f602.webp")))


class NoSheetHeld(unittest.TestCase):
    def setUp(self):
        _app()

    def test_cutting_cells_keeps_no_whole_sheet(self):
        A._OK.clear()
        for g in ("\U0001F525", "\U0001F602", "\U0001F44D"):
            self.assertGreater(_ink(A.image(g)), 30)
        self.assertFalse(hasattr(A, "_SHEETS") and A._SHEETS)


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


class DecodeRaises(unittest.TestCase):
    def test_a_decode_that_raises_removes_the_cached_file(self):
        d = tempfile.mkdtemp()
        try:
            a = A.Animated(d, fetch=lambda u: _webp_bytes(), spawn=lambda fn: fn())
            real = A.decode

            def boom(path, px):
                raise RuntimeError("bad")
            A.decode = boom
            try:
                self.assertIsNone(a.frames("1f525", 32))
            finally:
                A.decode = real
            self.assertIn("1f525", a.failed)
            self.assertFalse(os.path.exists(os.path.join(d, "1f525.webp")))
        finally:
            shutil.rmtree(d, ignore_errors=True)
