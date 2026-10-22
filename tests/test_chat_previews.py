"""The chat's previews and pictures (2026-10-22): maya_chat.thumbs, the uploads carrying a preview,
pictures sent and pasted, and the window drawing and playing them - offscreen."""
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtWidgets  # noqa: E402

from maya_chat import api as a  # noqa: E402
from maya_chat import files  # noqa: E402
from maya_chat import look  # noqa: E402
from maya_chat import records as r  # noqa: E402
from maya_chat import thumbs  # noqa: E402

from tests.test_chat_files import FILE, FileApi, Inline  # noqa: E402


def _app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def picture(path, w=800, h=500, colour="#3a7bd5"):
    image = QtGui.QImage(w, h, QtGui.QImage.Format_RGB32)
    image.fill(QtGui.QColor(colour))
    image.save(path)
    return path


def anim_card(folder, cells=12, columns=4, size=40):
    card = os.path.join(folder, "Walk.anim")
    os.makedirs(card)
    rows = -(-cells // columns)
    sheet = QtGui.QImage(columns * size, rows * size, QtGui.QImage.Format_RGB32)
    sheet.fill(QtGui.QColor("#000000"))
    p = QtGui.QPainter(sheet)
    for i in range(cells):
        row, col = divmod(i, columns)
        p.fillRect(col * size, row * size, size, size, QtGui.QColor(20 * i, 100, 200))
    p.end()
    sheet.save(os.path.join(card, "preview.jpg"))
    picture(os.path.join(card, "thumbnail.jpg"), 64, 64)
    with open(os.path.join(card, "anim.json"), "w") as out:
        json.dump({"format": "skeldar.anim", "fps": 30, "preview": {
            "frames": cells, "columns": columns, "size": size, "step": 2}}, out)
    return card


class Pure(unittest.TestCase):
    def test_a_preview_is_wanted_only_with_a_version(self):
        self.assertIsNone(thumbs.wanted({"id": "a"}))
        self.assertEqual(thumbs.wanted({"id": "a", "thumb_v": 2}), ("a", 2))

    def test_the_sheet_grid_is_read_strictly(self):
        self.assertIsNone(thumbs.sheet_of({}))
        self.assertIsNone(thumbs.sheet_of({"sheet": {"cells": 1, "columns": 1}}))
        self.assertIsNone(thumbs.sheet_of({"sheet": {"cells": "x", "columns": 2}}))
        self.assertEqual(thumbs.sheet_of({"sheet": {"cells": 6, "columns": 3}}),
                         {"cells": 6, "columns": 3, "step": 1, "fps": 0.0})

    def test_cells_play_at_the_clip_s_rate_and_rest_on_the_middle(self):
        sheet = {"cells": 10, "columns": 4, "step": 2, "fps": 30.0}
        self.assertEqual(thumbs.play_cell(None, sheet), 5)
        self.assertEqual(thumbs.play_cell(0, sheet), 0)
        self.assertEqual(thumbs.play_cell(1000, sheet), 5)        # 30 frames, 2 a cell
        self.assertEqual(thumbs.play_cell(4000, sheet), 0)        # loops
        self.assertEqual(thumbs.cell_rect(5, 4, 32), (32, 32, 32, 32))

    def test_the_file_record_carries_the_preview(self):
        f = r.file(dict(FILE, thumb_v=3, sheet={"cells": 8, "columns": 3, "step": 1, "fps": 24}))
        self.assertEqual(f["thumb_v"], 3)
        self.assertEqual(f["sheet"]["cells"], 8)
        f = r.file(dict(FILE, thumb_v="x", sheet={"cells": 1}))
        self.assertEqual((f["thumb_v"], f["sheet"]), (0, None))
        self.assertEqual(r.file(dict(FILE, kind="image", name="a.png"))["kind"], "image")

    def test_how_tall_a_preview_stands(self):
        self.assertEqual(look.preview_height({"kind": "scene"}), 0)
        self.assertEqual(look.preview_height({"kind": "scene"}, True), look.PREVIEW_H)
        self.assertEqual(look.preview_height({"kind": "image", "thumb_v": 1}), look.PICTURE_H)
        self.assertEqual(look.fitted(200, 100, 100, 100), (0.0, 25.0, 100.0, 50.0))
        self.assertEqual(look.file_tag({"name": "shot.jpeg"}), "JPG")

    def test_the_api_puts_and_gets_a_preview(self):
        calls = []

        class Answer(object):
            def __init__(self, data):
                self.data = data

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self):
                return self.data

        def opener(req, timeout=None):
            calls.append((req.get_method(), req.full_url, req.data))
            return Answer(b'{"id": "abc", "thumb_v": 1}' if req.get_method() == "PUT" else b"JPEG")

        api = a.Api("https://x.dev", "tok", opener)
        self.assertEqual(api.file_thumb_put("abc", b"\xff\xd8\xff", {"cells": 6, "columns": 3,
                                                                    "step": 2, "fps": 24})["thumb_v"], 1)
        method, url, data = calls[0]
        self.assertEqual(method, "PUT")
        self.assertTrue(url.startswith("https://x.dev/v1/files/abc/thumb?"))
        self.assertIn("cells=6", url)
        self.assertIn("columns=3", url)
        self.assertEqual(api.file_thumb("abc"), b"JPEG")


class Making(unittest.TestCase):
    def setUp(self):
        _app()
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_a_picture_shrinks_to_a_jpeg_under_the_limit(self):
        data, sheet = thumbs.from_picture(picture(os.path.join(self.dir, "a.png"), 3000, 2000), 360)
        self.assertIsNone(sheet)
        self.assertTrue(data.startswith(b"\xff\xd8\xff"))
        self.assertLessEqual(len(data), thumbs.MOST)
        image = QtGui.QImage.fromData(data)
        self.assertEqual((image.width(), image.height()), (360, 240))

    def test_not_a_picture_makes_no_preview(self):
        junk = os.path.join(self.dir, "a.png")
        with open(junk, "wb") as out:
            out.write(b"nope")
        self.assertIsNone(thumbs.from_picture(junk))

    def test_an_animation_card_s_preview_is_its_sheet_again_with_its_grid(self):
        data, sheet = thumbs.from_card(anim_card(self.dir, cells=12, columns=4, size=40))
        self.assertEqual(sheet, {"cells": 12, "columns": 4, "step": 2, "fps": 30.0})
        image = QtGui.QImage.fromData(data)
        self.assertEqual((image.width(), image.height()), (4 * thumbs.CELL, 3 * thumbs.CELL))
        # cell 5 (row 1, col 1) is cell 5's colour
        c = image.pixelColor(thumbs.CELL + thumbs.CELL // 2, thumbs.CELL + thumbs.CELL // 2)
        self.assertLess(abs(c.red() - 100), 12)

    def test_a_pose_card_s_preview_is_its_still(self):
        card = os.path.join(self.dir, "Fist.pose")
        os.makedirs(card)
        with open(os.path.join(card, "pose.json"), "w") as out:
            out.write("{}")
        picture(os.path.join(card, "thumbnail.jpg"), 640, 640)
        data, sheet = thumbs.from_card(card)
        self.assertIsNone(sheet)
        self.assertEqual(QtGui.QImage.fromData(data).width(), thumbs.STILL)

    def test_the_cache_fetches_once_and_keeps_it(self):
        got = []

        class Api(object):
            def file_thumb(self, fid):
                got.append(fid)
                return thumbs.from_picture(picture(os.path.join(self.dir, "p.png")))[0]

        Api.dir = self.dir
        cache = thumbs.Cache(os.path.join(self.dir, "thumbs"), lambda: Api(), start=lambda fn: fn())
        f = {"id": "a" * 16, "thumb_v": 1}
        self.assertIsNone(cache.file(f))                     # fetched now, here next time
        self.assertTrue(cache.take_changed())
        self.assertIsNotNone(cache.image(f))
        self.assertIsNotNone(cache.image(f))
        self.assertEqual(got, ["a" * 16])


class Uploads(Inline):
    """A preview goes up with its file; a picture goes as a file of kind image."""

    def setUp(self):
        Inline.setUp(self)
        _app()

    def ready(self, fake=None):
        fake = fake or PreviewApi()
        return Inline.ready(self, fake)

    def test_a_card_goes_with_its_sheet_and_the_sender_keeps_it(self):
        ses = self.ready()
        card = anim_card(self.src)
        cid = files.send_card(ses, "dm", card)
        fid = "%016x" % 1
        self.assertEqual(ses.api.thumbs[fid][1]["cells"], 12)
        frame = [f for f in ses.link.frames() if f.get("type") == "send"][-1]
        self.assertEqual(frame["file_meta"]["thumb_v"], 1)
        self.assertEqual(frame["file_meta"]["sheet"]["columns"], 4)
        held = thumbs.cache(ses)
        self.assertTrue(os.path.isfile(thumbs.path_for(held.folder, fid, 1)))   # no fetch for mine
        self.assertIsNone(ses._find_pending(cid)["upload"])

    def test_a_preview_the_server_refuses_leaves_the_file_going(self):
        fake = PreviewApi(refuse=True)
        ses = self.ready(fake)
        cid = files.send_card(ses, "dm", anim_card(self.src))
        frame = [f for f in ses.link.frames() if f.get("type") == "send"][-1]
        self.assertEqual((frame["file_meta"]["thumb_v"], frame["file_meta"]["sheet"]), (0, None))
        self.assertEqual(frame["cid"], cid)

    def test_a_picture_from_disk_and_from_the_clipboard(self):
        ses = self.ready()
        files.send_path(ses, "dm", picture(os.path.join(self.src, "ref.png")))
        self.assertEqual(ses.api.started[0][1:3], ("ref.png", "image"))
        self.assertIn("%016x" % 1, ses.api.thumbs)
        image = QtGui.QImage(300, 200, QtGui.QImage.Format_RGB32)
        image.fill(QtGui.QColor("#ff8800"))
        files.send_image(ses, "dm", image, "look")
        name = ses.api.started[1][1]
        self.assertTrue(name.startswith("picture_") and name.endswith((".png", ".jpg")), name)
        self.assertEqual(ses.api.started[1][2], "image")
        with self.assertRaises(a.ChatError):
            files.send_image(ses, "dm", QtGui.QImage())


class PreviewApi(FileApi):
    def __init__(self, refuse=False, **kw):
        FileApi.__init__(self, **kw)
        self.thumbs = {}
        self.refuse = refuse

    def file_thumb_put(self, fid, data, sheet=None):
        if self.refuse:
            raise a.ChatError("too_big", "A picture is at most 256 KB", 413)
        self.thumbs[fid] = (bytes(data), sheet)
        return {"id": fid, "thumb_v": 1}


class Window(unittest.TestCase):
    """The preview over a file's card, played on hover; pictures; Ctrl+V."""

    def setUp(self):
        _app()
        from tests import test_chat_window as T
        from maya_chat import window as W
        self.T, self.W = T, W
        W._VARS.clear()
        self.dir = tempfile.mkdtemp()
        self.ses = T.FakeSession()
        from maya_chat import store as ST
        self.ses.store = ST.Store(self.dir)
        self.cache = thumbs.Cache(os.path.join(self.dir, "thumbs"), lambda: None)
        patcher = mock.patch.object(thumbs, "cache", lambda session=None: self.cache)
        patcher.start()
        self.addCleanup(patcher.stop)
        sheet_data, sheet = thumbs.from_card(anim_card(self.dir))
        self.cache.put("a" * 16, 1, sheet_data)
        self.cache.put("p" * 16, 1, thumbs.from_picture(picture(os.path.join(self.dir, "r.png")))[0])
        self.ses.state.messages["dm"] += [
            dict(T.msg("ma", 3, text=""), file=dict(FILE, id="a" * 16, name="Walk.anim", kind="anim",
                                                    thumb_v=1, sheet=sheet)),
            dict(T.msg("mp", 4, text=""), file=dict(FILE, id="p" * 16, name="ref.png", kind="image",
                                                    thumb_v=1))]
        self.win = W.ChatWindow(self.ses, scale=1.0)
        self.win.root.resize(760, 640)
        self.win.root.show()
        self.win.open_chat("dm")
        self.win.refresh()

    def tearDown(self):
        self.win.destroy()
        QtWidgets.QApplication.processEvents()
        shutil.rmtree(self.dir, ignore_errors=True)

    def box(self, mid):
        return [b for b in self.win.feed.boxes if b.item.kind == "msg"
                and b.item.message.get("id") == mid][-1]

    def render(self):
        image = QtGui.QImage(self.win.feed.size(), QtGui.QImage.Format_ARGB32)
        image.fill(0)
        self.win.feed.render(image)
        return image

    def test_a_preview_stands_over_the_card(self):
        anim, pic = self.box("ma"), self.box("mp")
        self.assertIsNotNone(anim.thumb)
        self.assertLess(anim.thumb.bottom(), anim.card.top())
        self.assertEqual(int(anim.thumb.height()), look.PREVIEW_H)
        self.assertEqual(int(pic.thumb.height()), look.PICTURE_H)
        plain = [b for b in self.win.feed.boxes if b.item.kind == "msg"][0]
        self.assertIsNone(plain.thumb)

    def test_a_picture_is_drawn(self):
        image = self.render()
        rect = self.box("mp").thumb.toRect()
        c = image.pixelColor(rect.center())
        self.assertEqual((c.red() // 8, c.green() // 8, c.blue() // 8), (0x3a // 8, 0x7b // 8, 0xd5 // 8))

    def test_an_animation_plays_under_the_mouse_and_rests_off_it(self):
        feed = self.win.feed
        box = self.box("ma")
        rest = self.render().pixelColor(box.thumb.center().toPoint())
        feed._hover_preview(box)
        self.assertEqual(feed.playing[0], box.item.key())
        feed.playing = (box.item.key(), feed.playing[1] - 0)      # cell 0 now
        playing = self.render().pixelColor(box.thumb.center().toPoint())
        self.assertNotEqual(rest.red() // 10, playing.red() // 10)
        self.assertTrue(feed.tick(16))                              # the timer keeps running
        feed._hover_preview(None)
        self.assertIsNone(feed.playing)

    def test_a_picture_opens_and_is_not_dragged(self):
        got = []
        self.win.file_action = lambda item, action, at=None, target=None: got.append(action)
        box = self.box("mp")
        local = box.thumb.center()
        gp = self.win.feed.mapToGlobal(local.toPoint())
        event = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonPress, local, QtCore.QPointF(gp),
                                  QtCore.Qt.LeftButton, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
        self.win.feed.mousePressEvent(event)
        self.assertEqual(got, ["view"])
        self.assertFalse(self.win.start_drag(box.item, QtCore.QPoint(1, 1)))
        self.assertEqual([a for _r, a, _l in box.fbuttons], ["view", "save"])
        self.assertIn(u"Открыть", dict(self.win.menu_rows(box.item)))

    def test_ctrl_v_sends_a_picture_and_files_and_pastes_text(self):
        sent = []
        self.win.send_image = lambda image: sent.append(("image", image.width()))
        self.win.dropped = lambda paths: sent.append(("files", paths)) or len(paths)
        mime = QtCore.QMimeData()
        image = QtGui.QImage(30, 20, QtGui.QImage.Format_RGB32)
        mime.setImageData(image)
        self.assertTrue(self.win.composer.canInsertFromMimeData(mime))
        self.win.composer.insertFromMimeData(mime)
        mime = QtCore.QMimeData()
        mime.setUrls([QtCore.QUrl.fromLocalFile("C:/x/Run.ma"), QtCore.QUrl.fromLocalFile("C:/x/a.txt")])
        self.win.composer.insertFromMimeData(mime)
        mime = QtCore.QMimeData()
        mime.setText("hello")
        self.win.composer.insertFromMimeData(mime)
        self.assertEqual(sent, [("image", 30), ("files", ["C:/x/Run.ma"])])
        self.assertEqual(self.win.composer.toPlainText(), "hello")


if __name__ == "__main__":
    unittest.main()
