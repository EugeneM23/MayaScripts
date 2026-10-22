"""A person's card (their avatar large, their files by kind) and the picture viewer (2026-10-22),
offscreen on the chat window's fake session."""
import os
import shutil
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtWidgets  # noqa: E402

from maya_chat import files  # noqa: E402
from maya_chat import look  # noqa: E402
from maya_chat import profile  # noqa: E402

from tests import test_chat_window as T  # noqa: E402

NOW = T.NOW


def entry(mid, name, kind, at, chat="dm", text="", **extra):
    f = {"id": mid * 8 if len(mid) == 2 else mid, "name": name, "kind": kind, "bytes": 1000,
         "zip": 500, "fps": None, "range": None, "expired": False, "thumb_v": 0, "sheet": None}
    f.update(extra)
    return {"msg": mid, "chat": chat, "seq": 1, "at": at, "text": text, "file": f,
            "chat_kind": "dm", "chat_name": ""}


FILES = [entry("m1", "Walk.anim", "anim", NOW - 5000), entry("m2", "Fist.pose", "pose", NOW - 4000),
         entry("m3", "Shot.ma", "scene", NOW - 3000, text="the shot"),
         entry("m4", "Run.fbx", "fbx", NOW - 2000), entry("m5", "ref.png", "image", NOW - 1000),
         entry("m6", "Idle.anim", "anim", NOW - 500, chat="g1")]


class Pure(unittest.TestCase):
    def test_counts_by_kind(self):
        c = look.profile_counts(FILES)
        self.assertEqual((c["all"], c["anim"], c["pose"], c["scene"], c["fbx"], c["image"]), (6, 2, 1, 1, 1, 1))

    def test_rows_by_kind_newest_first_and_searched(self):
        self.assertEqual([e["msg"] for e in look.profile_rows(FILES, "anim")], ["m6", "m1"])
        self.assertEqual([e["msg"] for e in look.profile_rows(FILES)][:2], ["m6", "m5"])
        self.assertEqual([e["msg"] for e in look.profile_rows(FILES, "all", "SHOT")], ["m3"])
        self.assertEqual(look.profile_rows(FILES, "pose", "walk"), [])

    def test_the_line(self):
        e = dict(FILES[0], chat_kind="group", chat_name="Fights")
        line = look.profile_line(e, now_ms=NOW)
        self.assertIn(u"анимация", line)
        self.assertIn(u"в «Fights»", line)
        self.assertIn(u"истёк", look.profile_line(entry("mx", "a.ma", "scene", NOW, expired=True), now_ms=NOW))

    def test_a_file_i_sent_says_so_on_another_s_card(self):
        e = dict(FILES[2], from_id="me")
        self.assertTrue(look.profile_line(e, now_ms=NOW, me="me", owner="bob").startswith(u"от вас"))
        self.assertNotIn(u"от вас", look.profile_line(e, now_ms=NOW, me="me", owner="me"))
        self.assertNotIn(u"от вас", look.profile_line(dict(e, from_id="bob"), now_ms=NOW, me="me", owner="bob"))


class Card(unittest.TestCase):
    def setUp(self):
        T._app()
        files.DEFER = lambda fn: fn()
        files.SPAWN = lambda fn: fn()
        T.W._VARS.clear()
        self.ses = T.FakeSession()
        self.ses.api.person_files = lambda uid: {"user": dict(T.BOB, online=False, last_seen=NOW - 60000),
                                                 "files": list(FILES), "more": False}
        self.win = T.W.ChatWindow(self.ses, scale=1.0)
        self.win.root.resize(760, 560)
        self.win.root.show()
        self.win.open_chat("dm")
        self.win.refresh()

    def tearDown(self):
        files.DEFER = files.SPAWN = None
        self.win.destroy()
        QtWidgets.QApplication.processEvents()

    def test_a_person_s_card_with_their_files(self):
        self.assertTrue(self.win.show_profile({"id": "bob"}))
        card = self.win.profile
        self.assertTrue(card.is_open())
        self.assertEqual(card.name.text(), "Bob")
        self.assertEqual(card.nick.text(), "@bob")
        self.assertEqual(card.tabs["anim"][0].text(), u"Анимации 2")
        self.assertEqual(card.tabs["all"][0].text(), u"Все 6")
        self.assertEqual(len(card.list.rows), 6)
        card.show_kind("pose")
        self.assertEqual([e["msg"] for e in card.list.rows], ["m2"])
        self.assertTrue(card.tabs["pose"][0].isChecked())
        self.assertFalse(card.tabs["all"][0].isChecked())
        card.show_kind("all")
        card.search.setText("ref")
        self.assertEqual([e["msg"] for e in card.list.rows], ["m5"])
        self.assertEqual(int(card.avatar.width()), int(self.win.px(profile.AVATAR)))

    def test_a_group_s_picture_is_no_person(self):
        self.assertFalse(self.win.show_profile({"id": "dm2", "name": "a chat"}))
        self.assertFalse(self.win.show_profile({}))
        self.assertIsNone(self.win.profile)

    def test_the_header_avatar_opens_the_partner(self):
        av = self.win.chat_avatar
        event = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonPress, QtCore.QPointF(3, 3), QtCore.QPointF(3, 3),
                                  QtCore.Qt.LeftButton, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
        av.mousePressEvent(event)
        self.assertIsNotNone(self.win.profile)
        self.assertEqual(self.win.profile.user["id"], "bob")

    def test_a_list_avatar_opens_the_card_and_the_rest_of_the_row_the_chat(self):
        lst = self.win.list
        lst.resize(260, 400)
        i = next(n for n, r in enumerate(lst.rows) if r["id"] == "dm2")
        c = lst.avatar_rect(i).center()
        event = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonPress, c, c, QtCore.Qt.LeftButton,
                                  QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
        lst.mousePressEvent(event)
        self.assertEqual(self.win.profile.user["id"], "ann")
        self.assertEqual(self.win.chat, "dm")

    def test_escape_and_the_cross_close_it(self):
        self.win.show_profile({"id": "bob"})
        card = self.win.profile
        card.cover.keyPressEvent(QtGui.QKeyEvent(QtCore.QEvent.KeyPress, QtCore.Qt.Key_Escape,
                                                 QtCore.Qt.NoModifier))
        self.assertFalse(card.is_open())
        self.assertIsNone(self.win.profile)

    def test_a_double_click_goes_to_the_message(self):
        self.ses.state.messages["dm"].append(dict(T.msg("m3", 3, text="the shot"), file=FILES[2]["file"]))
        self.win.show_profile({"id": "bob"})
        card = self.win.profile
        with mock.patch.object(self.win, "scroll_to_message", lambda mid: setattr(self, "went", mid)):
            card.open_entry(FILES[2])
        self.assertEqual(self.went, "m3")
        self.assertEqual(self.win.chat, "dm")
        self.assertFalse(card.is_open())

    def test_its_verbs_follow_the_kind(self):
        self.win.show_profile({"id": "bob"})
        card = self.win.profile
        labels = lambda e: [label for label, _f in card.verbs(e)]  # noqa: E731
        self.assertIn("Import", labels(FILES[2]))
        self.assertIn(u"В библиотеку поз", labels(FILES[0]))
        self.assertIn(u"Открыть", labels(FILES[4]))
        got = []
        self.win.file_action = lambda item, action, at=None, target=None: got.append(
            (item.message["id"], item.message["chat"], action))
        dict(card.verbs(FILES[2]))["Import"]()
        self.assertEqual(got, [("m3", "dm", "import")])

    def test_a_row_is_dragged_out_as_the_feed_drags_a_card(self):
        self.win.show_profile({"id": "bob"})
        card = self.win.profile
        started = []
        self.win.start_drag = lambda item, gp: started.append(item.message["file"]["name"]) or False
        lst = card.list
        lst.resize(400, 400)
        y = self.win.px(profile.ROW_H) * 0.5
        press = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonPress, QtCore.QPointF(100, y), QtCore.QPointF(100, y),
                                  QtCore.Qt.LeftButton, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
        lst.mousePressEvent(press)
        move = QtGui.QMouseEvent(QtCore.QEvent.MouseMove, QtCore.QPointF(140, y), QtCore.QPointF(140, y),
                                 QtCore.Qt.NoButton, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
        lst.mouseMoveEvent(move)
        self.assertEqual(started, [card.list.rows[0]["file"]["name"]])

    def test_the_list_paints(self):
        self.win.show_profile({"id": "bob"})
        lst = self.win.profile.list
        lst.resize(400, lst.minimumHeight())
        image = QtGui.QImage(lst.size(), QtGui.QImage.Format_ARGB32)
        image.fill(0)
        lst.render(image)
        inked = sum(1 for x in range(0, image.width(), 4) for y in range(0, image.height(), 4)
                    if image.pixelColor(x, y).alpha())
        self.assertGreater(inked, 100)

    def test_a_failed_read_says_so(self):
        from maya_chat import api as a

        def refuse(uid):
            raise a.ChatError("offline", "The chat server did not answer")
        self.ses.api.person_files = refuse
        self.win.show_profile({"id": "bob"})
        self.assertIn("did not answer", self.win.profile.line.text())


class Viewer(unittest.TestCase):
    def setUp(self):
        T._app()
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "ref.png")
        image = QtGui.QImage(2000, 1000, QtGui.QImage.Format_RGB32)
        image.fill(QtGui.QColor("#2c8ae0"))
        image.save(self.path)
        self.v = profile.viewer_class()(self.path, 1.0)
        self.v.resize(800, 600)
        self.v.show()

    def tearDown(self):
        self.v.close()
        QtWidgets.QApplication.processEvents()
        shutil.rmtree(self.dir, ignore_errors=True)

    def wheel(self, at, up=True):
        e = QtGui.QWheelEvent(QtCore.QPointF(*at), QtCore.QPointF(*at), QtCore.QPoint(0, 0),
                              QtCore.QPoint(0, 120 if up else -120), QtCore.Qt.NoButton,
                              QtCore.Qt.NoModifier, QtCore.Qt.NoScrollPhase, False)
        self.v.wheelEvent(e)

    def test_it_fits_then_zooms_about_the_mouse_and_fits_again(self):
        fit = self.v.k()
        self.assertLess(fit, 1.0)
        r = self.v.placed()
        self.assertLessEqual(r.width(), 800)
        at = (r.left() + r.width() * 0.25, r.top() + r.height() * 0.5)
        self.wheel(at)
        self.assertAlmostEqual(self.v.k(), fit * 1.2)
        r2 = self.v.placed()
        self.assertAlmostEqual(r2.left() + r2.width() * 0.25, at[0], places=4)
        self.v.mouseDoubleClickEvent(QtGui.QMouseEvent(QtCore.QEvent.MouseButtonDblClick, QtCore.QPointF(5, 100),
                                                       QtCore.QPointF(5, 100), QtCore.Qt.LeftButton,
                                                       QtCore.Qt.LeftButton, QtCore.Qt.NoModifier))
        self.assertAlmostEqual(self.v.k(), fit)

    def test_the_chat_opens_pictures_in_it(self):
        seen = []
        with mock.patch.object(profile, "view_picture", lambda path, scale=1.0: seen.append(path)):
            files.show_picture(self.path)
        self.assertEqual(seen, [self.path])

    def test_it_paints_the_picture(self):
        image = QtGui.QImage(self.v.size(), QtGui.QImage.Format_ARGB32)
        self.v.render(image)
        c = image.pixelColor(400, 330)
        self.assertEqual(c.name(), "#2c8ae0")


if __name__ == "__main__":
    unittest.main()
