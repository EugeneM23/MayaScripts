"""maya_chat.window and maya_chat.notify offscreen, on a fake session."""
import os
import time
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tests  # noqa: F401  (puts SkeldarAnim/ on sys.path)

from PySide6 import QtCore, QtGui, QtWidgets

import maya_hubmotion as hubmotion
from maya_chat import look
from maya_chat import notify
from maya_chat import session as S
from maya_chat import window as W

ME = {"id": "me", "nick": "me", "name": "Me", "avatar_v": 0}
BOB = {"id": "bob", "nick": "bob", "name": "Bob", "avatar_v": 0}
ANN = {"id": "ann", "nick": "ann", "name": "Ann", "avatar_v": 0}
NOW = int(time.time() * 1000)


def _app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def msg(id, seq, frm="bob", chat="dm", text="hi", at=None, reply_to=None):
    return {"id": id, "chat": chat, "seq": seq, "from_id": frm, "cid": id, "text": text,
            "reply_to": reply_to, "at": at if at is not None else NOW - 1000 * (100 - seq),
            "edited_at": None, "deleted": False}


def dm_chat(cid="dm", other=BOB, last=None, unread=0):
    return {"id": cid, "kind": "dm", "name": "", "admin": None, "avatar_v": 0,
            "members": [ME, other], "last": last, "unread": unread, "read_upto": 0}


class FakeApi(object):
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def call(*args):
            self.calls.append((name,) + args)
            if name == "group":
                return {"id": "g1"}
            return {}
        return call


class FakeSession(object):
    """The parts of maya_chat.session.Session the window uses."""

    def __init__(self, signed=True):
        self.state = S.State()
        self.listeners = []
        self.calls = []
        self.api = FakeApi()
        if signed:
            self.state.me = dict(ME)
            self.state.status = "online"
            m1, m2 = msg("m1", 1, text="first"), msg("m2", 2, frm="me", text="mine")
            self.state.chats = {
                "dm": dm_chat(last=m2),
                "dm2": dict(dm_chat("dm2", ANN, last=msg("x", 1, frm="ann", chat="dm2",
                                                          at=NOW - 10 ** 7)), unread=3)}
            self.state.messages = {"dm": [m1, m2], "dm2": [msg("x", 1, frm="ann", chat="dm2")]}

    def read_people(self):
        self.calls.append(("read_people",))
        self.state.people = [dict(BOB, online=True, last_seen=0),
                             {"id": "carl", "nick": "carl", "name": "Carl", "avatar_v": 0,
                              "online": False, "last_seen": 0}]
        return self.state.people

    def listen(self, fn):
        self.listeners.append(fn)

    def unlisten(self, fn):
        if fn in self.listeners:
            self.listeners.remove(fn)

    def tell(self, kind, data=None):
        for fn in list(self.listeners):
            fn(kind, data)

    def send(self, chat, text, reply_to=None):
        self.calls.append(("send", chat, text, reply_to))
        cid = "c%d" % len(self.calls)
        self.state.pending.setdefault(chat, []).append(
            {"cid": cid, "chat": chat, "text": text, "reply_to": reply_to, "at": NOW,
             "from_id": "me", "state": "sending", "error": None})
        return cid

    def ack(self, chat, cid, mid, seq):
        self.state.pending[chat] = [p for p in self.state.pending.get(chat, []) if p["cid"] != cid]
        self.state.messages[chat].append(dict(msg(mid, seq, frm="me", chat=chat), cid=cid))
        self.tell("message", {"message": self.state.messages[chat][-1]})

    def edit(self, chat, mid, text):
        self.calls.append(("edit", chat, mid, text))
        return True

    def delete(self, chat, mid):
        self.calls.append(("delete", chat, mid))
        return True

    def read(self, chat):
        self.calls.append(("read", chat))
        self.state.chats[chat]["unread"] = 0
        return True

    def typing(self, chat):
        self.calls.append(("typing", chat))
        return True

    def retry(self, cid):
        self.calls.append(("retry", cid))
        return True

    def discard(self, cid):
        self.calls.append(("discard", cid))
        return True

    def load_history(self, chat):
        self.calls.append(("history", chat))
        return 0

    def open_dm(self, uid):
        self.calls.append(("open_dm", uid))
        return "dm"

    def sign_in(self, nick):
        self.calls.append(("sign_in", nick))
        self.state.me = {"id": "me", "nick": nick, "name": "", "avatar_v": 0}
        return self.state.me

    def sign_in_code(self, code):
        self.calls.append(("code", code))

    def code(self):
        return "secret-token"

    def sign_out(self):
        self.calls.append(("sign_out",))
        self.state = S.State()


class Base(unittest.TestCase):

    def setUp(self):
        _app()
        W._VARS.clear()
        notify._VARS.clear()
        self.ses = FakeSession()
        self.win = W.ChatWindow(self.ses, scale=1.0)
        self.win.root.resize(760, 520)
        self.win.root.show()
        self.win.refresh()

    def tearDown(self):
        self.win.destroy()
        QtWidgets.QApplication.processEvents()

    def key(self, key, mods=QtCore.Qt.NoModifier, text=""):
        event = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, key, mods, text)
        self.win.composer.keyPressEvent(event)


class SignIn(unittest.TestCase):

    def setUp(self):
        _app()
        self.ses = FakeSession(signed=False)
        self.win = W.ChatWindow(self.ses, scale=1.0)

    def tearDown(self):
        self.win.destroy()

    def test_signed_out_shows_the_nick_page_and_checks_the_format(self):
        self.assertEqual(self.win.pages.currentWidget().objectName(), "skeldarChatSignIn")
        self.win.nick_field.setText("x")
        self.assertFalse(self.win.signin_go.isEnabled())
        self.assertIn("3", self.win.signin_line.text())
        self.win.nick_field.setText("good_nick")
        self.assertTrue(self.win.signin_go.isEnabled())
        self.assertTrue(self.win.sign_in())
        self.assertEqual(self.ses.calls, [("sign_in", "good_nick")])
        self.assertEqual(self.win.pages.currentWidget().objectName(), "skeldarChatMain")

    def test_a_refusal_is_a_line_not_a_dialog(self):
        from maya_chat import api

        def taken(nick):
            raise api.ChatError("nick_taken", "@taken is taken")
        self.ses.sign_in = taken
        self.win.nick_field.setText("taken")
        self.assertFalse(self.win.sign_in())
        self.assertEqual(self.win.signin_line.text(), "@taken is taken")


class ListAndChat(Base):

    def test_the_list_is_newest_first_with_its_unread(self):
        rows = self.win.list.rows
        self.assertEqual([r["id"] for r in rows], ["dm", "dm2"])
        self.assertEqual(rows[0]["preview"], "Вы: mine")
        self.assertEqual(rows[1]["unread"], 3)
        self.assertEqual(self.win.state_label.text(), "в сети")

    def test_search_narrows_the_list(self):
        self.win.search.setText("ann")
        self.assertEqual([r["id"] for r in self.win.list.rows], ["dm2"])

    def test_a_click_opens_the_chat_and_reads_it(self):
        self.win.list.resize(250, 200)
        y = self.win.list.row_h() * 1.5
        event = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonPress, QtCore.QPointF(50, y),
                                  QtCore.QPointF(50, y), QtCore.Qt.LeftButton,
                                  QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
        self.win.list.mousePressEvent(event)
        self.assertEqual(self.win.chat, "dm2")
        self.assertIn(("read", "dm2"), self.ses.calls)
        self.assertEqual(self.win.chat_title.text(), "Ann")

    def test_enter_sends_and_the_bubble_goes_clock_sent_read(self):
        self.win.open_chat("dm")
        self.win.composer.setPlainText("hello")
        self.key(QtCore.Qt.Key_Return)
        self.assertEqual(self.ses.calls[-1], ("send", "dm", "hello", None))
        self.assertEqual(self.win.composer.toPlainText(), "")
        last = [b for b in self.win.feed.boxes if b.item.kind == "msg"][-1]
        self.assertEqual((last.item.tick, last.item.text), ("clock", "hello"))
        cid = self.ses.calls[-1] and self.ses.state.pending["dm"][0]["cid"]
        self.ses.ack("dm", cid, "m3", 3)
        QtWidgets.QApplication.processEvents()
        self.win.refresh()
        last = [b for b in self.win.feed.boxes if b.item.kind == "msg"][-1]
        self.assertEqual(last.item.tick, "sent")
        self.assertIn("m3", self.win.feed.flashing, "the sent one flashes")
        self.ses.state.reads["dm"] = {"bob": 3}
        self.win.refresh()
        last = [b for b in self.win.feed.boxes if b.item.kind == "msg"][-1]
        self.assertEqual(last.item.tick, "read")

    def test_shift_enter_is_a_new_line(self):
        self.win.open_chat("dm")
        self.win.composer.setPlainText("a")
        self.win.composer.moveCursor(QtGui.QTextCursor.End)
        self.key(QtCore.Qt.Key_Return, QtCore.Qt.ShiftModifier, "\r")
        self.assertNotIn("send", [c[0] for c in self.ses.calls])

    def test_up_edits_my_last_and_esc_cancels(self):
        self.win.open_chat("dm")
        self.key(QtCore.Qt.Key_Up)
        self.assertEqual(self.win.editing, "m2")
        self.assertEqual(self.win.composer.toPlainText(), "mine")
        self.assertFalse(self.win.bar.isHidden())
        self.win.composer.setPlainText("mine, edited")
        self.key(QtCore.Qt.Key_Return)
        self.assertEqual(self.ses.calls[-1], ("edit", "dm", "m2", "mine, edited"))
        self.key(QtCore.Qt.Key_Up)
        self.key(QtCore.Qt.Key_Escape)
        self.assertIsNone(self.win.editing)
        self.assertEqual(self.win.composer.toPlainText(), "")

    def test_reply_carries_the_original(self):
        self.win.open_chat("dm")
        first = [b for b in self.win.feed.boxes if b.item.kind == "msg"][0].item
        rows = dict(self.win.menu_rows(first))
        self.assertNotIn("Изменить", rows, "not mine")
        rows["Ответить"]()
        self.assertIn("Ответ Bob", self.win.bar_text.text())
        self.win.composer.setPlainText("yes")
        self.win.send_now()
        self.assertEqual(self.ses.calls[-1], ("send", "dm", "yes", "m1"))

    def test_delete_is_the_session_s(self):
        self.win.open_chat("dm")
        mine = [b for b in self.win.feed.boxes if b.item.kind == "msg" and b.item.mine][0].item
        dict(self.win.menu_rows(mine))["Удалить"]()
        self.assertEqual(self.ses.calls[-1], ("delete", "dm", "m2"))

    def test_a_failed_one_offers_retry(self):
        self.win.open_chat("dm")
        self.ses.state.pending["dm"] = [{"cid": "f", "chat": "dm", "text": "lost", "at": NOW,
                                          "from_id": "me", "state": "failed", "error": None}]
        self.win.refresh()
        box = [b for b in self.win.feed.boxes if b.item.kind == "msg"][-1]
        self.assertEqual(box.item.tick, "failed")
        self.assertIsNotNone(box.failed_rect)
        dict(self.win.menu_rows(box.item))["Повторить"]()
        self.assertIn(("retry", "f"), self.ses.calls)

    def test_a_new_message_comes_in_from_below(self):
        self.win.open_chat("dm")
        new = msg("m9", 9, text="news")
        self.ses.state.messages["dm"].append(new)
        self.ses.tell("message", {"message": new})
        self.win.refresh()
        self.assertIn("m9", self.win.feed.entering)
        with mock.patch.object(hubmotion, "enabled", return_value=False):
            self.win.animate()
        self.assertEqual(self.win.feed.entering, {})

    def test_typing_goes_to_the_session(self):
        self.win.open_chat("dm")
        self.win.composer.setPlainText("h")
        self.assertIn(("typing", "dm"), self.ses.calls)

    def test_the_feed_paints(self):
        self.win.open_chat("dm")
        image = QtGui.QImage(self.win.feed.size(), QtGui.QImage.Format_ARGB32)
        image.fill(0)
        self.win.feed.render(image)
        painted = sum(1 for x in range(0, image.width(), 7) for y in range(0, image.height(), 7)
                      if image.pixelColor(x, y).alpha())
        self.assertGreater(painted, 10)


class PeoplePane(Base):
    def buttons(self):
        return [b.text() for b in self.win.people_body.findChildren(QtWidgets.QPushButton)]

    def test_opening_it_reads_everybody(self):
        self.ses.state.friends = {"friends": [BOB], "incoming": [], "outgoing": []}
        self.win.show_pane("people")
        self.assertIn(("read_people",), self.ses.calls)
        self.assertEqual(self.win.people_count.text(), "1 в сети из 2")
        self.assertEqual(self.buttons(), ["Написать", "В друзья"])

    def test_a_stranger_is_asked_to_be_a_friend(self):
        self.win.show_pane("people")
        add = [b for b in self.win.people_body.findChildren(QtWidgets.QPushButton)
               if b.text() == "В друзья"]
        add[-1].click()
        self.assertIn(("request", "carl"), self.ses.api.calls)
        self.assertIn("@carl", self.win.people_line.text())

    def test_the_search_filters(self):
        self.win.show_pane("people")
        self.win.people_field.setText("carl")
        self.assertEqual(self.buttons(), ["В друзья"])


class Toasts(unittest.TestCase):
    def setUp(self):
        _app()
        from maya_chat import toast
        self.toast = toast
        toast.clear()

    def tearDown(self):
        self.toast.clear()
        QtWidgets.QApplication.processEvents()

    def test_a_message_shows_one_card_and_the_same_chat_replaces_it(self):
        a = self.toast.show("dm", BOB, "Bob", "hi")
        b = self.toast.show("dm", BOB, "Bob", "again")
        self.assertIs(a, b)
        self.assertEqual(a.text, "again")
        self.assertEqual(len(self.toast.cards()), 1)

    def test_the_newest_stands_at_the_bottom_and_a_fourth_drops_the_oldest(self):
        cards = [self.toast.show("c%d" % i, BOB, "Bob", "m") for i in range(4)]
        live = self.toast.cards()
        self.assertEqual(live, cards[1:])
        self.toast._layout(animate=False)
        self.assertLess(cards[2].y(), cards[3].y())
        self.assertEqual(cards[2].x(), cards[3].x())

    def test_it_stands_at_the_bottom_left_of_its_area(self):
        card = self.toast.show("dm", BOB, "Bob", "hi")
        self.toast._layout(animate=False)
        (x, y, w, h), _o = self.toast.area()
        margin = look.TOAST_MARGIN * card.scale
        self.assertAlmostEqual(card.x(), x + margin, delta=1)
        self.assertAlmostEqual(card.y() + card.height(), y + h - margin, delta=1)

    def test_a_click_opens_the_chat_and_the_card_leaves(self):
        card = self.toast.show("dm", BOB, "Bob", "hi")
        with mock.patch.object(self.toast, "open_chat") as opened:
            event = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonPress, QtCore.QPointF(40, 20),
                                      QtCore.QPointF(40, 20), QtCore.Qt.LeftButton,
                                      QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
            card.mousePressEvent(event)
        opened.assert_called_once_with("dm")
        self.assertEqual(self.toast.cards(), [])

    def test_it_goes_by_itself_after_its_stay(self):
        card = self.toast.show("dm", BOB, "Bob", "hi")
        card.stay_left = 0
        card.last -= 20
        self.toast._tick()
        self.assertIsNotNone(card.leaving)
        card.leaving -= look.TOAST_OUT_MS + 1
        self.toast._tick()
        self.assertEqual(self.toast._state()["cards"], [])

    def test_the_card_paints_ink(self):
        card = self.toast.show("dm", BOB, "Bob", "hi there")
        card.born -= 10000
        card.flash_at -= 10000
        image = QtGui.QImage(card.size(), QtGui.QImage.Format_ARGB32)
        image.fill(0)
        card.render(image)
        inked = sum(1 for x in range(0, image.width(), 3) for y in range(0, image.height(), 3)
                    if image.pixelColor(x, y).alpha() > 0)
        self.assertGreater(inked, 100)

    def test_opening_its_chat_takes_its_card_away(self):
        self.toast.show("dm", BOB, "Bob", "hi")
        self.toast.dismiss_chat("dm")
        self.assertEqual(self.toast.cards(), [])


class Layout(Base):

    def test_narrow_is_one_column(self):
        self.win.root.resize(540, 400)
        self.win.resized()
        self.assertTrue(self.win.left.isVisible())
        self.assertFalse(self.win.right.isVisible())
        self.win.open_chat("dm")
        self.assertFalse(self.win.left.isVisible())
        self.assertTrue(self.win.right.isVisible())
        self.assertTrue(self.win.chat_back.isVisible())
        self.win.back()
        self.assertTrue(self.win.left.isVisible())

    def test_wide_is_two_columns(self):
        self.win.root.resize(800, 500)
        self.win.resized()
        self.assertTrue(self.win.left.isVisible() and self.win.right.isVisible())

    def test_place_and_size_are_remembered(self):
        self.win.root.move(120, 90)
        self.win.root.resize(700, 480)
        self.win.remember()
        self.assertEqual(W.get_var(W.POS_VAR), "120,90")
        self.assertEqual(W.get_var(W.SIZE_VAR), "700,480")
        with mock.patch.object(W, "_screens", return_value=[(0, 0, 1920, 1040)]):
            self.win.place()
        self.assertEqual((self.win.root.x(), self.win.root.y()), (120, 90))
        self.assertEqual(self.win.root.width(), 700)

    def test_a_place_off_every_screen_is_dropped(self):
        W.set_var(W.POS_VAR, "9000,9000")
        with mock.patch.object(W, "_screens", return_value=[(0, 0, 1920, 1040)]):
            self.win.place(origin=(500, 500))
        self.assertLess(self.win.root.x(), 1920)

    def test_the_panes(self):
        self.ses.state.friends = {"friends": [BOB], "incoming": [ANN], "outgoing": []}
        self.win.refresh()
        self.assertEqual(self.win.friends_button.text(), "1")
        self.win.show_pane("friends")
        texts = [w.text() for w in self.win.friends_body.findChildren(QtWidgets.QPushButton)]
        self.assertIn("Принять", texts)
        self.assertIn("Написать", texts)
        self.win.friend_field.setText("@Carl")
        self.win.request_friend()
        self.assertIn(("request", "carl"), self.ses.api.calls)
        self.win.show_pane("new")
        self.win.group_name.setText("Аним")
        self.win.make_group()
        self.assertIn("друга", self.win.new_line.text())
        self.win.picked = {"bob"}
        self.win.make_group()
        self.assertIn(("group", "Аним", ["bob"]), self.ses.api.calls)
        self.win.show_pane("settings")
        self.win.toggle_code()
        self.assertEqual(self.win.code_text.text(), "secret-token")
        self.win.sign_out()
        self.assertEqual(self.win.pages.currentWidget().objectName(), "skeldarChatSignIn")


class Notify(unittest.TestCase):

    def setUp(self):
        notify._VARS.clear()
        self.ses = FakeSession()

    def test_a_message_from_another_is_a_viewport_message_and_the_badge(self):
        m = msg("m5", 5, text="hey " * 40)
        with mock.patch.object(notify, "say", return_value=True) as said, \
                mock.patch.object(notify, "paint", return_value=3) as badge:
            done = notify.heard(self.ses, "message", {"message": m})
        self.assertEqual(done[0], ("badge", 3))
        self.assertEqual(done[1][0], "viewport")
        head, text = said.call_args[0][:2]
        self.assertEqual(said.call_args[0][3]["id"], "bob")
        self.assertEqual(head, "Bob")
        self.assertLessEqual(len(text), notify.PREVIEW)
        self.assertTrue(badge.called)

    def test_mine_and_switched_off_say_nothing(self):
        with mock.patch.object(notify, "say", return_value=True), \
                mock.patch.object(notify, "paint", return_value=0):
            self.assertEqual(notify.heard(self.ses, "message",
                                          {"message": msg("a", 1, frm="me")}), [("badge", 0)])
            notify.set_option("viewport", False)
            self.assertEqual(notify.heard(self.ses, "message", {"message": msg("b", 2)}),
                             [("badge", 0)])

    def test_the_sound_is_off_by_default(self):
        self.assertFalse(notify.option("sound"))
        self.assertTrue(notify.option("viewport"))

    def test_the_unread_total(self):
        self.assertEqual(notify.unread(self.ses), 3)


if __name__ == "__main__":
    unittest.main()
