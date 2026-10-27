"""maya_chat.profile: a person's card - its file list under the mouse (a double click, a drag let
go, the lit rows, the previews), the backdrop, the tabs and the verbs, Написать - and the picture
viewer's mouse and keys. Offscreen on the chat window's fake session; nothing reaches a server."""
import os
import shutil
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tests  # noqa: F401  (puts SkeldarAnim/ on sys.path)

from PySide6 import QtCore, QtGui, QtWidgets  # noqa: E402

from maya_chat import files  # noqa: E402
from maya_chat import profile  # noqa: E402

from tests import test_chat_window as T  # noqa: E402
from tests.test_chat_profile import FILES, entry  # noqa: E402

MISSING = object()


def mouse(kind, pos, button=QtCore.Qt.LeftButton, buttons=None, glob=None):
    pos = QtCore.QPointF(pos)
    return QtGui.QMouseEvent(kind, pos, QtCore.QPointF(glob if glob is not None else pos),
                             button, button if buttons is None else buttons,
                             QtCore.Qt.NoModifier)


def render(widget):
    image = QtGui.QImage(max(1, widget.width()), max(1, widget.height()),
                         QtGui.QImage.Format_ARGB32)
    image.fill(0)
    widget.render(image)
    return image


class Swaps(object):
    def swap(self, obj, name, value):
        old = getattr(obj, name, MISSING)
        setattr(obj, name, value)

        def back():
            if old is MISSING:
                delattr(obj, name)
            else:
                setattr(obj, name, old)
        self.addCleanup(back)


class Card(Swaps, unittest.TestCase):
    def setUp(self):
        T._app()
        T.W._VARS.clear()
        self.swap(files, "DEFER", lambda fn: fn())
        self.swap(files, "SPAWN", lambda fn: fn())
        self.ses = T.FakeSession()
        self.ses.api.person_files = lambda uid: {"user": dict(T.BOB, online=True),
                                                 "files": list(FILES), "more": False}
        self.win = T.W.ChatWindow(self.ses, scale=1.0)
        self.win.root.resize(760, 560)
        self.win.root.show()
        self.win.open_chat("dm")
        self.assertTrue(self.win.show_profile({"id": "bob"}))
        self.card = self.win.profile
        self.lst = self.card.list
        self.lst.resize(420, self.lst.minimumHeight())

    def tearDown(self):
        if self.win.profile is not None:
            self.win.profile.close()
        self.win.destroy()
        QtWidgets.QApplication.processEvents()

    def row_y(self, i):
        return self.win.px(profile.ROW_H) * (i + 0.5)

    # ---------------------------------------------------------------- the list
    def test_a_double_click_on_a_row_goes_to_its_message(self):
        went = []
        self.card.open_entry = went.append
        self.lst.mouseDoubleClickEvent(mouse(QtCore.QEvent.MouseButtonDblClick,
                                             QtCore.QPointF(100, self.row_y(1))))
        self.assertEqual(went, [self.lst.rows[1]])
        self.lst.mouseDoubleClickEvent(mouse(QtCore.QEvent.MouseButtonDblClick,
                                             QtCore.QPointF(100, self.lst.height() + 400)))
        self.assertEqual(len(went), 1, "below the rows: nothing")

    def test_a_row_dragged_out_and_let_go_ends_the_drag(self):
        got = []
        self.win.start_drag = lambda item, gp: got.append(("start", item.message["id"])) or True
        self.win.drag_move = lambda gp: got.append(("move",))
        self.win.drag_end = lambda gp, cancel=False: got.append(("end", cancel))
        y = self.row_y(0)
        self.lst.mousePressEvent(mouse(QtCore.QEvent.MouseButtonPress, QtCore.QPointF(100, y)))
        self.lst.mouseMoveEvent(mouse(QtCore.QEvent.MouseMove, QtCore.QPointF(160, y),
                                      QtCore.Qt.NoButton, QtCore.Qt.LeftButton))
        self.assertTrue(self.lst._dragging)
        self.lst.mouseMoveEvent(mouse(QtCore.QEvent.MouseMove, QtCore.QPointF(170, y),
                                      QtCore.Qt.NoButton, QtCore.Qt.LeftButton))
        self.lst.mouseReleaseEvent(mouse(QtCore.QEvent.MouseButtonRelease,
                                         QtCore.QPointF(170, y)))
        self.assertFalse(self.lst._dragging)
        self.assertEqual(got, [("start", self.lst.rows[0]["msg"]), ("move",), ("end", False)])

    def test_the_right_button_or_a_press_cancels_a_standing_drag(self):
        ends = []
        self.win.drag_end = lambda gp, cancel=False: ends.append(cancel)
        self.lst._dragging = True
        self.lst.mouseReleaseEvent(mouse(QtCore.QEvent.MouseButtonRelease, QtCore.QPointF(5, 5),
                                         QtCore.Qt.RightButton))
        self.lst._dragging = True
        self.lst.mousePressEvent(mouse(QtCore.QEvent.MouseButtonPress, QtCore.QPointF(5, 5)))
        self.assertEqual(ends, [True, False])
        self.lst.mouseReleaseEvent(mouse(QtCore.QEvent.MouseButtonRelease, QtCore.QPointF(5, 5)))
        self.assertEqual(ends, [True, False], "no drag: the release ends nothing")

    def test_a_refused_drag_starts_nothing(self):
        self.win.start_drag = lambda item, gp: False
        y = self.row_y(0)
        self.lst.mousePressEvent(mouse(QtCore.QEvent.MouseButtonPress, QtCore.QPointF(100, y)))
        self.lst.mouseMoveEvent(mouse(QtCore.QEvent.MouseMove, QtCore.QPointF(200, y),
                                      QtCore.Qt.NoButton, QtCore.Qt.LeftButton))
        self.assertFalse(self.lst._dragging)

    def test_the_row_under_the_mouse_lights_and_leaving_puts_it_out(self):
        self.lst.mouseMoveEvent(mouse(QtCore.QEvent.MouseMove, QtCore.QPointF(100, self.row_y(2)),
                                      QtCore.Qt.NoButton))
        self.assertEqual(self.lst.hovered, self.lst.rows[2]["msg"])
        lit = render(self.lst)
        self.lst.leaveEvent(QtCore.QEvent(QtCore.QEvent.Leave))
        self.assertIsNone(self.lst.hovered)
        plain = render(self.lst)
        x, y = 5, int(self.row_y(2))
        self.assertNotEqual(lit.pixelColor(x, y), plain.pixelColor(x, y))

    def test_a_right_press_picks_the_row_and_opens_its_menu(self):
        shown = []
        self.card.menu = lambda e, gp: shown.append(e["msg"])
        self.lst.mousePressEvent(mouse(QtCore.QEvent.MouseButtonPress,
                                       QtCore.QPointF(100, self.row_y(3)),
                                       QtCore.Qt.RightButton))
        self.assertEqual(shown, [self.lst.rows[3]["msg"]])
        self.assertEqual(self.lst.selected, self.lst.rows[3]["msg"])
        self.assertGreater(render(self.lst).width(), 0)

    def test_previews_are_drawn_cropped_and_an_animation_shows_its_middle_cell(self):
        red = QtGui.QImage(64, 32, QtGui.QImage.Format_RGB32)
        red.fill(QtGui.QColor("#ff0000"))
        sheet = QtGui.QImage(80, 80, QtGui.QImage.Format_RGB32)
        sheet.fill(QtGui.QColor("#0000ff"))
        painter = QtGui.QPainter(sheet)
        painter.fillRect(QtCore.QRect(40, 20, 20, 20), QtGui.QColor("#00ff00"))   # cell 6 of 4 x 4
        painter.end()

        class Thumbs(object):
            def image(self, f):
                if f.get("kind") == "anim":
                    return sheet
                return red if f.get("kind") == "image" else None
        self.card.thumbs = lambda: Thumbs()
        rows = [entry("a1", "Walk.anim", "anim", T.NOW, sheet={"cells": 12, "columns": 4,
                                                                "step": 1, "fps": 30}),
                entry("p1", "ref.png", "image", T.NOW - 10)]
        self.lst.set_rows(rows)
        self.lst.resize(420, self.lst.minimumHeight())
        image = render(self.lst)
        px = self.win.px
        tile = lambda i: QtCore.QPointF(px(2) + px(6) + px(profile.THUMB) / 2.0,    # noqa: E731
                                        self.row_y(i))
        self.assertEqual(image.pixelColor(tile(0).toPoint()).name(), "#00ff00")
        self.assertEqual(image.pixelColor(tile(1).toPoint()).name(), "#ff0000")

    # ---------------------------------------------------------------- the card
    def test_the_backdrop_dims_and_a_click_on_it_closes_but_not_on_the_card(self):
        cover = self.card.cover
        image = render(cover)
        self.assertGreater(image.pixelColor(2, 2).alpha(), 100)
        inside = self.card.box.geometry().center()
        cover.mousePressEvent(mouse(QtCore.QEvent.MouseButtonPress, QtCore.QPointF(inside)))
        self.assertTrue(self.card.is_open())
        cover.keyPressEvent(QtGui.QKeyEvent(QtCore.QEvent.KeyPress, QtCore.Qt.Key_A,
                                            QtCore.Qt.NoModifier, "a"))
        self.assertTrue(self.card.is_open())
        cover.mousePressEvent(mouse(QtCore.QEvent.MouseButtonPress, QtCore.QPointF(2, 2)))
        self.assertFalse(self.card.is_open())
        self.assertIsNone(self.win.profile)

    def test_a_tab_button_shows_its_kind(self):
        b, _label = self.card.tabs["scene"]
        b.click()
        self.assertEqual(self.card.kind, "scene")
        self.assertEqual([e["msg"] for e in self.lst.rows], ["m3"])
        self.assertEqual(b.property("skRole"), "primary")

    def test_the_verbs_of_each_kind_run_through_the_window(self):
        done = []
        self.win.file_action = lambda item, action, at=None, target=None: (
            done.append((item.message["id"], action, target)), self.win.say("did " + action))
        went = []
        self.card.open_entry = went.append
        by = dict((e["msg"], e) for e in FILES)
        for mid in ("m1", "m3", "m5"):
            for label, fn in self.card.verbs(by[mid]):
                fn()
        self.assertEqual(went, [by["m1"], by["m3"], by["m5"]])
        self.assertEqual(done, [
            ("m1", "library", {"kind": "library", "folder": None}),
            ("m3", "open", None), ("m3", "import", None), ("m3", "save", None),
            ("m3", "stash", None), ("m5", "view", None), ("m5", "save", None)])
        self.assertEqual(self.card.line.text(), "did save")

    def test_an_expired_file_can_only_be_shown(self):
        gone = entry("mz", "Old.ma", "scene", T.NOW, expired=True)
        self.assertEqual([label for label, _f in self.card.verbs(gone)], [u"Показать в чате"])

    def test_the_menu_holds_the_verbs(self):
        done = []
        self.win.file_action = lambda item, action, at=None, target=None: done.append(action)
        self.card.menu(FILES[2], QtCore.QPoint(10, 10))
        menu = self.card._menu
        acts = dict((a.text(), a) for a in menu.actions())
        self.assertEqual(sorted(acts), sorted(label for label, _f in self.card.verbs(FILES[2])))
        acts["Import"].trigger()
        self.assertEqual(done, ["import"])
        menu.close()

    def test_write_closes_the_card_and_opens_the_dm(self):
        self.card.write.click()
        self.assertFalse(self.card.is_open())
        self.assertIn(("open_dm", "bob"), self.ses.calls)

    def test_the_message_is_looked_for_in_older_history(self):
        pages = [[T.msg("m3", 3, text="the shot")], []]

        def load_history(chat):
            got = pages.pop(0) if pages else []
            self.ses.state.messages[chat] = got + self.ses.state.messages[chat]
            return len(got)
        self.ses.load_history = load_history
        went = []
        self.win.scroll_to_message = went.append
        self.card.open_entry(FILES[2])
        self.assertEqual(went, ["m3"])
        self.assertEqual(len(pages), 1, "stopped once it was there")

    def test_a_history_that_fails_or_ends_stops_looking(self):
        def broken(chat):
            raise RuntimeError("offline")
        self.ses.load_history = broken
        went = []
        self.win.scroll_to_message = went.append
        self.card.open_entry(FILES[3])
        self.assertEqual(went, ["m4"])
        self.ses.load_history = lambda chat: 0
        self.win.show_profile({"id": "bob"})
        self.win.profile.open_entry(FILES[3])
        self.assertEqual(went, ["m4", "m4"])

    def test_my_own_card_with_nothing_sent_and_a_search_that_finds_nothing(self):
        self.card.close()
        self.ses.api.person_files = lambda uid: {"user": dict(T.ME), "files": []}
        self.win.show_profile({"id": "me", "nick": "me"})
        mine = self.win.profile
        self.assertIn(u"ничего не отправляли", mine.line.text())
        mine.close()
        self.ses.api.person_files = lambda uid: {"files": list(FILES)}
        self.win.show_profile({"id": "bob"})
        other = self.win.profile
        other.search.setText("zzz-nothing")
        self.assertEqual(other.line.text(), u"Ничего не нашли")
        other.close()
        self.ses.api.person_files = lambda uid: {"files": []}
        self.win.show_profile({"id": "bob"})
        self.assertIn(u"не обменивались", self.win.profile.line.text())

    def test_an_answer_after_the_card_closed_is_dropped(self):
        later = []
        self.swap(files, "SPAWN", later.append)
        self.card.close()
        self.win.show_profile({"id": "bob"})
        card = self.win.profile
        self.assertEqual(card.line.text(), u"Загружаю файлы…")
        card.close()
        later[-1]()                                     # the read comes back: nothing to fill
        self.assertFalse(card.is_open())

    def test_a_card_over_a_gone_window_is_not_placed(self):
        root, self.card.win.root = self.card.win.root, None
        try:
            self.card.place()
        finally:
            self.card.win.root = root


class Viewer(Swaps, unittest.TestCase):
    def setUp(self):
        T._app()
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.path = os.path.join(self.dir, "ref.png")
        image = QtGui.QImage(400, 200, QtGui.QImage.Format_RGB32)
        image.fill(QtGui.QColor("#2c8ae0"))
        image.save(self.path)
        self.v = profile.viewer_class()(self.path, 1.0)
        self.v.resize(800, 600)
        self.v.move(100, 100)
        self.v.show()

    def tearDown(self):
        try:
            self.v.close()
        except RuntimeError:
            pass
        QtWidgets.QApplication.processEvents()

    def test_the_cross_closes_it(self):
        self.v.mousePressEvent(mouse(QtCore.QEvent.MouseButtonPress, self.v.close_rect().center()))
        self.assertFalse(self.v.isVisible())

    def test_the_title_moves_the_window(self):
        start = QtCore.QPointF(50, 10)
        self.v.mousePressEvent(mouse(QtCore.QEvent.MouseButtonPress, start,
                                     glob=QtCore.QPointF(150, 110)))
        self.assertIsNotNone(self.v._move)
        self.v.mouseMoveEvent(mouse(QtCore.QEvent.MouseMove, start, QtCore.Qt.NoButton,
                                    QtCore.Qt.LeftButton, glob=QtCore.QPointF(250, 160)))
        self.assertEqual((self.v.x(), self.v.y()), (200, 150))
        self.v.mouseReleaseEvent(mouse(QtCore.QEvent.MouseButtonRelease, start))
        self.assertIsNone(self.v._move)

    def test_a_drag_on_the_picture_pans_it(self):
        start = QtCore.QPointF(400, 300)
        self.v.mousePressEvent(mouse(QtCore.QEvent.MouseButtonPress, start))
        self.v.mouseMoveEvent(mouse(QtCore.QEvent.MouseMove, start + QtCore.QPointF(30, -20),
                                    QtCore.Qt.NoButton, QtCore.Qt.LeftButton))
        self.assertEqual(self.v.offset, QtCore.QPointF(30, -20))
        self.v.mouseReleaseEvent(mouse(QtCore.QEvent.MouseButtonRelease, start))
        self.assertIsNone(self.v._drag)
        self.v.mouseMoveEvent(mouse(QtCore.QEvent.MouseMove, QtCore.QPointF(0, 0),
                                    QtCore.Qt.NoButton))
        self.assertEqual(self.v.offset, QtCore.QPointF(30, -20), "no button: no pan")

    def test_the_right_button_does_nothing_and_keys_other_than_esc_pass(self):
        self.v.mousePressEvent(mouse(QtCore.QEvent.MouseButtonPress, QtCore.QPointF(400, 300),
                                     QtCore.Qt.RightButton))
        self.assertIsNone(self.v._drag)
        self.v.keyPressEvent(QtGui.QKeyEvent(QtCore.QEvent.KeyPress, QtCore.Qt.Key_A,
                                             QtCore.Qt.NoModifier, "a"))
        self.assertTrue(self.v.isVisible())
        self.v.keyPressEvent(QtGui.QKeyEvent(QtCore.QEvent.KeyPress, QtCore.Qt.Key_Escape,
                                             QtCore.Qt.NoModifier))
        self.assertFalse(self.v.isVisible())

    def test_a_picture_that_cannot_be_read_says_so(self):
        broken = os.path.join(self.dir, "broken.png")
        with open(broken, "wb") as out:
            out.write(b"not a png")
        v = profile.viewer_class()(broken, 1.0)
        v.resize(500, 400)
        self.assertEqual(v.fit_k(), 1.0)
        image = render(v)
        self.assertGreater(sum(1 for x in range(0, 500, 4) if
                               image.pixelColor(x, 200).name() != image.pixelColor(2, 200).name()),
                           3, "the line is drawn in the middle")
        v.deleteLater()

    def test_view_picture_opens_one_beside_maya_and_keeps_it(self):
        self.swap(T.W, "_main_window", lambda: None)
        v = profile.view_picture(self.path, 1.0)
        self.addCleanup(v.close)
        self.assertTrue(v.isVisible())
        self.assertIn(v, profile._OPEN)
        self.assertEqual(v.windowTitle(), "ref.png")

    def test_view_picture_without_a_window_module_still_opens(self):
        def broken():
            raise RuntimeError("no Maya")
        self.swap(T.W, "_main_window", broken)
        v = profile.view_picture(self.path)
        self.addCleanup(v.close)
        self.assertTrue(v.isVisible())


if __name__ == "__main__":
    unittest.main()
