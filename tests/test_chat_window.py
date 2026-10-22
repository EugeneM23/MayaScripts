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


class Everybody(Base):
    """Everybody is in the list (2026-10-20): no friends, a click on a person opens the dm."""

    def setUp(self):
        Base.setUp(self)
        self.ses.read_people()
        self.win.refresh()

    def kinds(self):
        return [(r["kind"], r["title"]) for r in self.win.list.rows]

    def test_the_list_has_the_chats_then_everybody_without_a_dm(self):
        rows = self.kinds()
        self.assertEqual(rows[0][0], "chat")
        self.assertEqual(rows[-2][0], "head")
        self.assertIn("в сети", rows[-2][1])
        self.assertEqual(rows[-1], ("person", "Carl"))     # Bob has a dm already
        self.assertNotIn(("person", "Bob"), rows)

    def test_a_click_on_a_person_opens_the_dm(self):
        tops, _total = self.win.list.tops()
        y = tops[-1] + 5
        event = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonPress, QtCore.QPointF(20, y),
                                  QtCore.QPointF(20, y), QtCore.Qt.LeftButton,
                                  QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
        self.win.list.mousePressEvent(event)
        self.assertIn(("open_dm", "carl"), self.ses.calls)

    def test_the_search_reaches_people(self):
        self.win.search.setText("carl")
        self.assertEqual([k for k, _t in self.kinds()], ["head", "person"])

    def test_no_friends_pane_or_button(self):
        self.assertFalse(hasattr(self.win, "friends_button"))
        self.assertNotIn("friends", self.win.right_pages)
        self.assertNotIn("people", self.win.right_pages)

    def test_new_chat_and_members_offer_everybody(self):
        self.win.show_pane("new")
        boxes = [b.text() for b in self.win.new_body.findChildren(QtWidgets.QCheckBox)]
        self.assertEqual(len(boxes), 2)
        self.win.new_search.setText("carl")
        boxes = [b.text() for b in self.win.new_body.findChildren(QtWidgets.QCheckBox)]
        self.assertEqual(len(boxes), 1)

    def test_an_online_person_gets_the_dot(self):
        self.assertTrue(W.is_online({"id": "bob"}, self.ses.state.online)
                        or W.is_online(dict(BOB, online=True), {}))
        self.assertFalse(W.is_online({"id": "x", "online": False}, {}))
        self.assertTrue(W.is_online({"id": "x", "online": False}, {"x": {"online": True}}))


class Reactions(Base):
    def setUp(self):
        Base.setUp(self)
        self.reacted = []

        def react(chat, mid, e):
            self.reacted.append((chat, mid, e))
            for m in self.ses.state.messages[chat]:
                if m["id"] == mid:
                    m["reactions"] = {e: ["me", "bob"]}
            return True
        self.ses.react = react
        self.win.open_chat("dm")

    def test_a_reaction_shows_as_a_pill_and_a_click_toggles(self):
        self.win.react(self.ses.state.messages["dm"][0], "👍")
        self.assertEqual(self.reacted, [("dm", "m1", "👍")])
        box = next(b for b in self.win.feed.boxes if b.pills)
        rect, e, n, mine = box.pills[0]
        self.assertEqual((e, n, mine), ("👍", 2, True))
        found, where = self.win.feed.box_at(rect.center())
        self.assertEqual(where, "pill:👍")

    def test_the_menu_offers_a_reaction(self):
        item = next(b.item for b in self.win.feed.boxes if b.item.kind == "msg")
        self.assertIn("Реакция…", [label for label, _fn in self.win.menu_rows(item)])

    def test_the_picker_puts_an_emoji_in_the_composer(self):
        picker = self.win.pick_emoji()
        self.assertTrue(len(picker.items()) > 0)
        picker.pick("🔥")
        self.assertEqual(self.win.composer.toPlainText(), "🔥")

    def test_the_picker_reacts_from_a_message(self):
        picker = self.win.pick_emoji(self.ses.state.messages["dm"][0], at=(10, 10))
        picker.pick("😂")
        self.assertEqual(self.reacted[-1], ("dm", "m1", "😂"))


class Avatar(Base):
    def test_a_picture_is_cut_square_and_uploaded(self):
        import tempfile
        from maya_chat import avatars
        path = os.path.join(tempfile.mkdtemp(), "p.png")
        image = QtGui.QImage(400, 200, QtGui.QImage.Format_RGB32)
        image.fill(QtGui.QColor("#ff0000"))
        image.save(path)
        sent = []

        def set_avatar(data):
            sent.append(data)
            return dict(ME, avatar_v=1)
        self.ses.set_avatar = set_avatar
        self.win.avatars = avatars.Cache(tempfile.mkdtemp(), lambda: None)
        self.win.set_avatar_from(path)
        self.assertEqual(sent[0][:3], bytes([0xff, 0xd8, 0xff]))
        back = QtGui.QImage.fromData(sent[0])
        self.assertEqual((back.width(), back.height()), (256, 256))
        self.assertIn("обновлена", self.win.settings_line.text())


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

    def test_the_composer_shows_its_whole_line(self):
        self.win.open_chat("dm")
        QtWidgets.QApplication.processEvents()
        c = self.win.composer
        line = c.fontMetrics().lineSpacing()
        inner = c.viewport().height() - 2 * c.document().documentMargin()
        self.assertGreaterEqual(inner, line)
        c.setPlainText("a\nb\nc")
        QtWidgets.QApplication.processEvents()
        inner = c.viewport().height() - 2 * c.document().documentMargin()
        self.assertGreaterEqual(inner, 3 * line)

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
        self.ses.read_people()
        self.win.show_pane("new")
        self.win.group_name.setText("Аним")
        self.win.make_group()
        self.assertIn("человека", self.win.new_line.text())
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
        notify.set_option("sound", False)
        with mock.patch.object(notify, "say", return_value=True), \
                mock.patch.object(notify, "paint", return_value=0):
            self.assertEqual(notify.heard(self.ses, "message",
                                          {"message": msg("a", 1, frm="me")}), [("badge", 0)])
            notify.set_option("viewport", False)
            self.assertEqual(notify.heard(self.ses, "message", {"message": msg("b", 2)}),
                             [("badge", 0)])

    def test_the_sound_is_on_by_default_and_rings_the_chime(self):
        self.assertTrue(notify.option("sound"))
        with mock.patch.object(notify, "say", return_value=True), \
                mock.patch.object(notify, "paint", return_value=0), \
                mock.patch.object(notify, "ring", return_value=True) as ring:
            done = notify.heard(self.ses, "message", {"message": msg("c", 3)})
        self.assertIn(("sound",), done)
        self.assertTrue(ring.called)
        self.assertTrue(notify.option("viewport"))

    def test_the_unread_total(self):
        self.assertEqual(notify.unread(self.ses), 3)


if __name__ == "__main__":
    unittest.main()


FILE = {"id": "f" * 16, "name": "Run_Cycle.ma", "kind": "scene", "bytes": 12900000, "zip": 4000000,
        "fps": 30.0, "range": [0.0, 48.0], "expired": False}


class Files(Base):
    """A file message's card, the paperclip, drops and the card dragged out (2026-10-22)."""

    def setUp(self):
        Base.setUp(self)
        self.ses.state.messages["dm"].append(dict(msg("mf", 3, text=""), file=dict(FILE)))
        self.win.open_chat("dm")
        self.win.refresh()

    def card(self, mid="mf"):
        return [b for b in self.win.feed.boxes if b.item.kind == "msg"
                and (b.item.message.get("id") == mid or b.item.message.get("cid") == mid)][-1]

    def press(self, rect, button=QtCore.Qt.LeftButton):
        local = rect.center()
        gp = self.win.feed.mapToGlobal(local.toPoint())
        event = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonPress, local, QtCore.QPointF(gp),
                                  button, button, QtCore.Qt.NoModifier)
        self.win.feed.mousePressEvent(event)

    def test_a_file_message_is_a_card_with_its_buttons(self):
        box = self.card()
        self.assertIsNotNone(box.card)
        self.assertIsNone(box.doc)               # no caption: no text line
        self.assertEqual([a for _r, a, _l in box.fbuttons], ["open", "import", "more"])
        self.assertIn("12.3 MB", look.file_line(FILE))
        self.assertEqual(look.file_tag(FILE), "MA")
        plain = [b for b in self.win.feed.boxes if b.item.kind == "msg"][0]
        self.assertIsNone(plain.card)

    def test_open_downloads_then_opens_it(self):
        from maya_chat import files
        got = []
        with mock.patch.object(files, "fetch", lambda ses, f, then: (got.append(f["id"]), then("C:/x/Run_Cycle.ma"), True)[2]), \
                mock.patch.object(files, "open_file", lambda path, f, sender: "Opened %s from %s" % (f["name"], sender)):
            rect = [r for r, a, _l in self.card().fbuttons if a == "open"][0]
            self.press(rect)
        self.assertEqual(got, ["f" * 16])
        self.assertEqual(self.win.line.text(), "Opened Run_Cycle.ma from Bob")

    def test_a_download_in_flight_is_a_bar_and_said(self):
        from maya_chat import files
        with mock.patch.object(files, "fetch", lambda ses, f, then: False):
            self.win.file_action(self.card().item, "import")
        self.assertIn("Скачиваю Run_Cycle.ma", self.win.line.text())
        self.ses.state.downloads["f" * 16] = {"state": "loading", "progress": 0.4, "then": []}
        self.win.refresh()
        box = self.card()
        self.assertEqual(box.fbuttons, [])
        self.assertEqual(box.fbar[2], "скачиваю 40%")

    def test_an_upload_shows_its_progress_and_cancels(self):
        self.ses.state.pending["dm"] = [{
            "cid": "up", "chat": "dm", "text": "", "at": NOW, "from_id": "me", "state": "sending",
            "error": None, "file": dict(FILE, id=None),
            "upload": {"phase": "upload", "progress": 0.5, "local": "x", "id": "a"}}]
        self.win.refresh()
        box = self.card("up")
        self.assertEqual(box.fbar[2], "отправляю 50%")
        rect = [r for r, a, _l in box.fbuttons if a == "cancel"][0]
        self.press(rect)
        self.assertIn(("discard", "up"), self.ses.calls)

    def test_an_expired_file_has_no_buttons(self):
        self.ses.state.messages["dm"][-1]["file"]["expired"] = True
        self.win.refresh()
        box = self.card()
        self.assertEqual(box.fbuttons, [])
        self.assertEqual(box.fbar[2], "файл истёк")
        self.assertNotIn("Open", dict(self.win.menu_rows(box.item)))

    def test_the_menu_offers_the_file_and_no_copy_of_an_empty_text(self):
        rows = dict(self.win.menu_rows(self.card().item))
        for label in ("Open", "Import", "Сохранить как…", "В Stash"):
            self.assertIn(label, rows)
        self.assertNotIn("Скопировать", rows)

    def test_the_card_paints(self):
        image = QtGui.QImage(self.win.feed.size(), QtGui.QImage.Format_ARGB32)
        image.fill(0)
        self.win.feed.render(image)
        rect = self.card().card.toRect()
        inked = sum(1 for x in range(rect.left(), rect.right(), 3)
                    for y in range(rect.top(), rect.bottom(), 3) if image.pixelColor(x, y).alpha())
        self.assertGreater(inked, 50)

    def test_the_paperclip_sends_a_scene_or_a_file(self):
        self.assertEqual([label for label, _f in self.win.clip_rows()],
                         ["Отправить сцену", "Отправить выделенное (FBX)", "Отправить файл…"])

    def test_a_dropped_scene_goes_with_the_composer_s_text(self):
        from maya_chat import files
        sent = []
        self.win.composer.setPlainText("the run")
        with mock.patch.object(files, "send_path", lambda ses, chat, path, caption="": (sent.append((chat, path, caption)), "cid")[1]):
            self.assertEqual(self.win.dropped(["C:/x/Run.ma", "C:/x/notes.txt"]), 1)
        self.assertEqual(sent, [("dm", "C:/x/Run.ma", "the run")])
        self.assertEqual(self.win.composer.toPlainText(), "")
        self.assertIn("notes.txt", self.win.line.text())
        self.assertEqual(self.win.dropped(["C:/x/notes.txt"]), 0)

    def test_the_window_takes_file_drops(self):
        mime = QtCore.QMimeData()
        mime.setUrls([QtCore.QUrl.fromLocalFile("C:/x/Run.ma")])
        self.assertEqual(W._local_paths(mime), ["C:/x/Run.ma"])
        self.assertTrue(self.win.root.acceptDrops())

    def test_a_card_dragged_onto_a_viewport_imports_it(self):
        done = []
        self.win._later = lambda fn: fn()
        self.win.file_action = lambda item, action, at=None: done.append(action)
        with mock.patch.object(self.win, "drag_aim", lambda gp: {"kind": "import", "text": "import into the scene"}):
            self.assertTrue(self.win.start_drag(self.card().item, QtCore.QPoint(5, 5)))
            self.assertIn("import into the scene", self.win._drag["ghost"].caption_text())
            self.assertEqual(self.win.drag_end(QtCore.QPoint(6, 6)), "import")
        self.assertEqual(done, ["import"])

    def test_a_drag_let_go_nowhere_does_nothing(self):
        self.win._later = lambda fn: fn()
        with mock.patch.object(self.win, "drag_aim", lambda gp: {"kind": "none", "text": "nowhere"}):
            self.win.start_drag(self.card().item, QtCore.QPoint(5, 5))
            self.assertIsNone(self.win.drag_end(QtCore.QPoint(6, 6)))

    def test_with_no_chat_open_a_file_is_refused(self):
        self.win.chat = None
        self.assertIsNone(self.win.send_path("C:/x/Run.ma"))
        self.assertIn("Откройте чат", self.win.line.text())
