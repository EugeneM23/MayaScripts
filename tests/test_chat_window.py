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
        # on the row's text: its avatar (14..56) opens the person's card
        event = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonPress, QtCore.QPointF(120, y),
                                  QtCore.QPointF(120, y), QtCore.Qt.LeftButton,
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

    def test_a_card_is_dragged_not_pressed(self):
        self.ses.state.messages["dm"].append(dict(msg("mc", 4, text=""),
                                                  file=dict(FILE, id="c" * 16, name="Fist.pose", kind="pose")))
        self.win.refresh()
        box = self.card("mc")
        self.assertEqual(look.file_tag(box.item.message["file"]), "POSE")
        self.assertEqual(box.fbuttons, [])
        self.assertEqual(box.fbar[2], W.CARD_HINT)
        self.assertNotIn("Open", dict(self.win.menu_rows(box.item)))
        done = []
        self.win._later = lambda fn: fn()
        self.win.file_action = lambda item, action, at=None, target=None: done.append((action, target))
        with mock.patch.object(self.win, "card_aim", lambda gp, drag: {"kind": "library", "folder": "Fights",
                                                                      "text": "в библиотеку · Fights"}):
            self.win.start_drag(box.item, QtCore.QPoint(5, 5))
            self.assertEqual(self.win.drag_end(QtCore.QPoint(6, 6)), "library")
        with mock.patch.object(self.win, "card_aim", lambda gp, drag: {"kind": "apply", "root": "|root",
                                                                      "text": "на Manny"}):
            self.win.start_drag(box.item, QtCore.QPoint(5, 5))
            self.win.drag_end(QtCore.QPoint(6, 6))
        self.assertEqual(done[0], ("library", {"kind": "library", "folder": "Fights", "text": "в библиотеку · Fights"}))
        self.assertEqual(done[1][1]["kind"], "character")
        self.assertEqual(done[1][1]["root"], "|root")


class EmojiPictures(Base):
    @staticmethod
    def _paint(widget):
        """Run paintEvent even when the window is not exposed offscreen."""
        img = QtGui.QImage(max(1, widget.width()), max(1, widget.height()),
                           QtGui.QImage.Format_ARGB32)
        widget.render(img)

    def setUp(self):
        Base.setUp(self)
        self.win.open_chat("dm")

    def _send_in(self, text, mid="e1", seq=50):
        self.ses.state.messages["dm"].append(msg(mid, seq, text=text))
        self.win.refresh()
        return next(b for b in self.win.feed.boxes
                    if b.item.kind == "msg" and b.item.message.get("id") == mid)

    def test_text_with_emoji_has_its_picture_in_the_document(self):
        box = self._send_in("огонь 🔥")
        self.assertIsNotNone(box.doc)
        res = box.doc.resource(QtGui.QTextDocument.ImageResource, QtCore.QUrl("emoji:1f525"))
        self.assertIsNotNone(res)

    def test_emoji_alone_are_big_pictures(self):
        box = self._send_in("🔥😂")
        self.assertIsNone(box.doc)
        self.assertEqual([g for _r, g in box.bigs], ["🔥", "😂"])
        side = box.bigs[0][0].width()
        self.assertAlmostEqual(side, self.win.px(W.BIG_EMOJI), delta=1)
        found, where = self.win.feed.box_at(box.bigs[1][0].center())
        self.assertEqual(where, "big:😂")

    def test_an_animated_big_emoji_plays_once_then_on_hover(self):
        box = self._send_in("😂")
        feed = self.win.feed
        frames = [(QtGui.QImage(4, 4, QtGui.QImage.Format_ARGB32), 50)]

        class FakeAnim(object):
            def frames(self, cp, px):
                return frames

            def take_changed(self):
                return False
        feed.anim = FakeAnim()
        with mock.patch.object(hubmotion, "enabled", return_value=True):
            self._paint(feed)
            key = (box.item.key(), "😂", "big")
            self.assertIn(key, feed.plays)
            self.assertIn(key, feed.played)
            feed.plays.clear()
            self._paint(feed)
            self.assertNotIn(key, feed.plays)            # once only
            ev = QtGui.QMouseEvent(QtCore.QEvent.MouseMove, box.bigs[0][0].center(),
                                   box.bigs[0][0].center(), QtCore.Qt.NoButton,
                                   QtCore.Qt.NoButton, QtCore.Qt.NoModifier)
            feed.mouseMoveEvent(ev)
            self.assertIn(key, feed.plays)               # the mouse plays it again

    def test_no_animation_when_animations_are_off(self):
        box = self._send_in("😂")
        feed = self.win.feed

        class FakeAnim(object):
            def frames(self, cp, px):
                return [(QtGui.QImage(4, 4, QtGui.QImage.Format_ARGB32), 50)]

            def take_changed(self):
                return False
        feed.anim = FakeAnim()
        with mock.patch.object(hubmotion, "enabled", return_value=False):
            self._paint(feed)
        self.assertFalse(feed.plays)

    def test_a_play_never_painted_again_is_dropped_past_the_cap(self):
        feed = self.win.feed
        for store in (feed.entering, feed.flashing, feed.pill_pops):
            store.clear()
        feed.folding = []
        feed.playing = None
        key = (("gone", "x"), "😂", "big")                 # its box is never painted again
        feed.plays[key] = W._now_ms() - W.PLAY_CAP_MS - 1
        busy = feed.tick(16)
        self.assertNotIn(key, feed.plays)
        self.assertFalse(busy)

    def test_another_chat_drops_the_plays(self):
        feed = self.win.feed
        feed.plays[(("dm", "m1"), "😂", "big")] = W._now_ms()
        self.win.open_chat("dm2")
        self.assertFalse(feed.plays)

    def test_a_pill_is_a_picture_and_a_count(self):
        self.ses.state.messages["dm"][0]["reactions"] = {"🔥": ["bob"]}
        self.win.refresh()
        box = next(b for b in self.win.feed.boxes if b.pills)
        rect, e, n, mine = box.pills[0]
        self.assertEqual((e, n, mine), ("🔥", 1, False))
        self.assertLess(rect.width(), self.win.px(70))


class Picker(Base):
    def setUp(self):
        Base.setUp(self)
        W._VARS.pop("skeldarChatEmojiTone", None)
        self.win.open_chat("dm")
        self.picker = self.win.pick_emoji()

    def tearDown(self):
        self.picker.close()
        Base.tearDown(self)

    def test_recent_then_the_eight_groups(self):
        keys = [k for k, _t, _items in self.picker.sections()]
        self.assertEqual(keys, ["recent", "smileys", "people", "animals", "food", "travel",
                                "activities", "objects", "symbols"])
        self.assertGreater(len(self.picker.items()), 1300)

    def test_search_in_russian(self):
        self.picker.search.setText("кот")
        self.assertEqual([k for k, _t, _i in self.picker.sections()], ["found"])
        self.assertIn("\U0001F431", self.picker.items())

    def test_nothing_found(self):
        self.picker.set_query("zzzzqq")
        self.assertEqual(self.picker.items(), [])

    def test_enter_picks_the_first_result(self):
        self.picker.set_query("огонь")
        first = self.picker.items()[0]
        enter = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, QtCore.Qt.Key_Return,
                                QtCore.Qt.NoModifier)
        self.picker.search.keyPressEvent(enter)
        self.assertEqual(self.win.composer.toPlainText(), first)

    def test_esc_clears_then_closes(self):
        self.picker.set_query("кот")
        esc = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, QtCore.Qt.Key_Escape, QtCore.Qt.NoModifier)
        self.picker.search.keyPressEvent(esc)
        self.assertEqual(self.picker.search.text(), "")
        self.assertTrue(self.picker.isVisible())
        self.picker.search.keyPressEvent(esc)
        self.assertFalse(self.picker.isVisible())

    def test_a_tone_is_applied_and_remembered(self):
        self.picker.set_tone(3)
        self.assertIn("\U0001F44D\U0001F3FD", self.picker.items())
        self.assertEqual(int(W.get_var("skeldarChatEmojiTone")), 3)
        again = self.win.pick_emoji()
        self.assertIn("\U0001F44D\U0001F3FD", again.items())
        again.close()

    def test_a_toned_pick_goes_into_the_composer_and_recent(self):
        self.picker.set_tone(5)
        self.picker.pick("\U0001F44D\U0001F3FF")
        self.assertEqual(self.win.composer.toPlainText(), "\U0001F44D\U0001F3FF")
        self.assertIn("\U0001F44D\U0001F3FF", W.get_var("skeldarChatEmojiRecent"))

    def test_a_tab_scrolls_to_its_group(self):
        self.picker.scroll_to("food")
        self.assertGreater(self.picker.scroll, 0)
        top = self.picker.section_top("food")
        self.assertAlmostEqual(self.picker.scroll, min(top, self.picker.max_scroll()), delta=1)

    # ---- fix round 1: the glow, the screen, the lit tab
    def _cell_in_widget(self, i=0):
        rect, g = self.picker.cells[i]
        return QtCore.QRectF(rect.x(), rect.y() + self.picker.top_grid - self.picker.scroll,
                             rect.width(), rect.height()), g

    def _render(self):
        img = QtGui.QImage(self.picker.size(), QtGui.QImage.Format_ARGB32)
        img.fill(QtGui.QColor(0, 0, 0))
        self.picker.render(img)
        return img

    @staticmethod
    def _mean(img, rect):
        r = g = b = n = 0
        for x in range(int(rect.left()) + 1, int(rect.right()) - 1):
            for y in range(int(rect.top()) + 1, int(rect.bottom()) - 1):
                c = img.pixelColor(x, y)
                r, g, b, n = r + c.red(), g + c.green(), b + c.blue(), n + 1
        return r / float(n), g / float(n), b / float(n)

    def _hover(self, rect):
        pos = QtCore.QPointF(rect.center())
        move = QtGui.QMouseEvent(QtCore.QEvent.MouseMove, pos, pos, QtCore.Qt.NoButton,
                                 QtCore.Qt.NoButton, QtCore.Qt.NoModifier)
        self.picker.mouseMoveEvent(move)

    def test_the_hovered_cell_glows(self):
        rect, g = self._cell_in_widget(0)
        cold = self._mean(self._render(), rect)
        with mock.patch.object(hubmotion, "enabled", return_value=False):
            self._hover(rect)
        self.assertEqual(self.picker.levels.get(("emoji", g)), 1.0)
        lit = self._mean(self._render(), rect)
        with mock.patch.object(self.picker, "_glow"):
            plain = self._mean(self._render(), rect)
        self.assertGreater(sum(lit), sum(cold) + 10)
        self.assertGreater(lit[0], plain[0] + 3)          # the accent's warm light
        self.assertGreater(lit[0] - lit[2], plain[0] - plain[2])

    def test_the_glow_stays_inside_its_cell(self):
        rect, g = self._cell_in_widget(0)
        right, _g = self._cell_in_widget(1)
        with mock.patch.object(hubmotion, "enabled", return_value=False):
            self._hover(rect)
        lit = self._mean(self._render(), right)
        with mock.patch.object(self.picker, "_glow"):
            plain = self._mean(self._render(), right)
        self.assertAlmostEqual(sum(lit), sum(plain), delta=0.5)

    def test_the_picker_stays_inside_a_small_screen(self):
        self.picker.close()
        area = (100, 100, 500, 420)
        with mock.patch.object(W, "_screen_area", return_value=area):
            for at in ((560, 480), (90, 90), (0, 5000)):
                p = self.win.pick_emoji(at=at)
                g = p.geometry()
                self.assertGreaterEqual(g.left(), 100)
                self.assertGreaterEqual(g.top(), 100)
                self.assertLessEqual(g.left() + g.width(), 600)
                self.assertLessEqual(g.top() + g.height(), 520)
                p.close()
            with mock.patch.object(W, "_cursor", return_value=(590, 510)):
                p = self.win.pick_emoji(message={"id": "m"})
                g = p.geometry()
                self.assertLessEqual(g.left() + g.width(), 600)
                self.assertLessEqual(g.top() + g.height(), 520)
                p.close()
        self.picker = self.win.pick_emoji()

    def test_below_the_button_when_there_is_no_room_above(self):
        self.picker.close()
        btn = self.win.emoji_button
        corner = btn.mapToGlobal(btn.rect().topLeft())
        area = (corner.x() - 500, corner.y() - 50, 3000, 3000)
        with mock.patch.object(W, "_screen_area", return_value=area):
            self.picker = self.win.pick_emoji()
        self.assertGreaterEqual(self.picker.y(), corner.y() + btn.height())

    def test_recent_is_lit_at_the_top_and_food_after_its_tab(self):
        self.assertEqual(self.picker._active_tab(), "recent")
        self.picker.scroll_to("food")
        self.assertEqual(self.picker._active_tab(), "food")

    def test_recent_is_lit_at_the_top_even_when_empty(self):
        self.picker.close()
        with mock.patch("maya_chat.emoji.recent", return_value=[]):
            self.picker = self.win.pick_emoji()
            self.assertEqual(self.picker._active_tab(), "recent")


class CallsInWindow(Base):

    def setUp(self):
        super(CallsInWindow, self).setUp()
        self.win.open_chat("dm")

    def button(self, name):
        return self.win.root.findChild(QtWidgets.QAbstractButton, name)

    def test_header_buttons_start_calls(self):
        got = []
        with mock.patch("maya_chat.callview.start", side_effect=lambda s, c, k: got.append((c, k))):
            self.button("skeldarChatCallVoice").click()
            self.button("skeldarChatCallVideo").click()
        self.assertEqual(got, [("dm", "audio"), ("dm", "video")])

    def test_a_running_call_turns_them_into_join(self):
        now = int(time.time() * 1000)
        view = {"id": "c1", "chat": "dm", "by": "bob", "kind": "video", "cid": "x",
                "state": "live", "members": ["bob", "carl"], "declined": [],
                "started_at": now, "answered_at": now, "ended_at": None}
        self.ses.state.calls = {"c1": view}
        self.ses.tell("call", {"kind": "call", "call": view})
        join = self.button("skeldarChatCallJoin")
        self.assertTrue(join.isVisibleTo(self.win.root))
        self.assertFalse(self.button("skeldarChatCallVoice").isVisibleTo(self.win.root))
        got = []
        with mock.patch("maya_chat.callview.answer", side_effect=lambda s, c, k: got.append((c, k))):
            join.click()
        self.assertEqual(got, [("c1", "video")])

    def test_the_call_line_paints_and_a_click_calls_back(self):
        note = {"id": "c", "kind": "video", "answered": False, "seconds": 0}
        call = dict(msg("m9", 9, text="", at=NOW - 500), call=note)
        self.ses.state.messages["dm"].append(call)
        self.win.refresh()
        QtWidgets.QApplication.processEvents()
        boxes = [b for b in self.win.feed.boxes if b.item.kind == "call"]
        self.assertEqual(len(boxes), 1)
        self.assertTrue(boxes[0].item.missed)
        self.assertGreater(self.win.feed.grab().toImage().width(), 0)
        got = []
        centre = boxes[0].callpill.center()
        box, where = self.win.feed.box_at(centre)
        self.assertEqual(where, "call")
        with mock.patch("maya_chat.callview.start", side_effect=lambda s, c, k: got.append((c, k))):
            event = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonPress, centre,
                                      self.win.feed.mapToGlobal(centre), QtCore.Qt.LeftButton,
                                      QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
            self.win.feed.mousePressEvent(event)
        self.assertEqual(got, [("dm", "video")])


class CallsInWindowRound1(Base):

    def setUp(self):
        super(CallsInWindowRound1, self).setUp()
        self.win.open_chat("dm")

    def vis(self, name):
        return self.win.root.findChild(QtWidgets.QAbstractButton, name).isVisibleTo(self.win.root)

    def run_call(self, members, state="live"):
        now = int(time.time() * 1000)
        view = {"id": "c1", "chat": "dm", "by": "bob", "kind": "audio", "cid": "x",
                "state": state, "members": members, "declined": [], "started_at": now,
                "answered_at": now, "ended_at": None}
        self.ses.state.calls = {"c1": view}
        self.ses.tell("call", {"kind": "call", "call": view})
        return view

    def test_in_the_call_shows_neither(self):
        self.run_call(["bob", "me"])
        self.assertFalse(self.vis("skeldarChatCallJoin"))
        self.assertFalse(self.vis("skeldarChatCallVoice"))
        self.assertFalse(self.vis("skeldarChatCallVideo"))

    def test_a_full_call_shows_neither_and_a_press_starts_nothing(self):
        self.run_call(["bob", "a", "b", "c"])
        self.assertFalse(self.vis("skeldarChatCallJoin"))
        self.assertFalse(self.vis("skeldarChatCallVoice"))
        with mock.patch("maya_chat.callview.start") as start, \
                mock.patch("maya_chat.callview.answer") as answer:
            self.win.start_call("audio")
        start.assert_not_called()
        answer.assert_not_called()

    def test_an_old_call_line_joins_a_joinable_call_else_nothing(self):
        self.run_call(["bob"])
        with mock.patch("maya_chat.callview.start") as start, \
                mock.patch("maya_chat.callview.answer") as answer:
            self.win.start_call("video", "dm")
        start.assert_not_called()
        answer.assert_called_once()

    def test_refresh_on_a_chat_switch_repaints_and_an_end_brings_voice_back(self):
        self.run_call(["bob"])
        self.win.open_chat("dm2")
        self.assertTrue(self.vis("skeldarChatCallVoice"))
        self.win.open_chat("dm")
        self.assertTrue(self.vis("skeldarChatCallJoin"))
        self.assertFalse(self.vis("skeldarChatCallVoice"))
        view = dict(self.ses.state.calls["c1"], state="ended")
        self.ses.state.calls = {"c1": view}
        self.ses.tell("call", {"kind": "call", "call": view})
        self.assertTrue(self.vis("skeldarChatCallVoice"))
        self.assertFalse(self.vis("skeldarChatCallJoin"))


class LookA(Base):
    """Telegram's layout in our colours (2026-10-22, spec 2026-10-22-chat-look-telegram-design.md)."""

    def msgs(self):
        return [b for b in self.win.feed.boxes if b.item.kind == "msg"]

    def test_the_tabs_filter_the_list_and_are_remembered(self):
        self.assertEqual(self.win.tab, "all")
        self.assertEqual(self.win.tabs.counts, {"all": 1, "dm": 1, "groups": 0})
        self.win.set_tab("groups")
        self.assertEqual(self.win.list.rows, [])
        self.assertIn("Групп", self.win.empty_list_text())
        self.assertEqual(W.get_var(W.TAB_VAR), "groups")
        self.win.set_tab("dm")
        self.assertEqual([r["id"] for r in self.win.list.rows], ["dm", "dm2"])
        other = W.ChatWindow(self.ses, scale=1.0)
        try:
            self.assertEqual(other.tab, "dm")
        finally:
            other.destroy()

    def test_a_click_on_a_tab_shows_it(self):
        tabs = self.win.tabs
        tabs.resize(260, tabs.height())
        rect = [r for key, _l, r, _c in tabs.rects() if key == "groups"][0]
        event = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonPress, rect.center(), rect.center(),
                                  QtCore.Qt.LeftButton, QtCore.Qt.LeftButton,
                                  QtCore.Qt.NoModifier)
        tabs.mousePressEvent(event)
        self.assertEqual(self.win.tab, "groups")

    def test_the_rows_carry_the_sender_apart_and_my_tick(self):
        row = self.win.list.rows[0]
        self.assertEqual((row["prefix"], row["text"], row["tick"]), ("Вы", "mine", "sent"))
        self.ses.state.reads["dm"] = {"bob": 2}
        self.win.refresh()
        self.assertEqual(self.win.list.rows[0]["tick"], "read")

    def test_my_menu_holds_my_card_new_chat_and_settings(self):
        self.assertEqual([label for label, _i, _f in self.win.me_rows()],
                         ["Мой профиль", "Новый чат или группа", "Настройки"])
        menu = self.win.me_menu()
        self.assertEqual(len(menu.actions()), 5)          # me, a line, three rows
        dict((label, fn) for label, _i, fn in self.win.me_rows())["Настройки"]()
        self.assertEqual(self.win.pane, "settings")
        menu.close()

    def test_the_unread_band_stands_before_what_was_unread(self):
        self.ses.state.messages["dm2"] = [msg("a1", 1, frm="ann", chat="dm2"),
                                          msg("a2", 2, frm="me", chat="dm2"),
                                          msg("a3", 3, frm="ann", chat="dm2"),
                                          msg("a4", 4, frm="ann", chat="dm2")]
        self.ses.state.chats["dm2"]["unread"] = 2
        self.win.open_chat("dm2")
        kinds = [(b.item.kind, b.item.message.get("id") if b.item.message else None)
                 for b in self.win.feed.boxes]
        i = kinds.index(("unread", None))
        self.assertEqual(kinds[i + 1], ("msg", "a3"))
        self.assertIsNotNone(self.win.feed.boxes[i].band)
        self.win.refresh()
        self.assertIn("unread", [b.item.kind for b in self.win.feed.boxes], "it stays")
        self.win.open_chat("dm")
        self.win.open_chat("dm2")
        self.assertNotIn("unread", [b.item.kind for b in self.win.feed.boxes],
                         "read since: gone when the chat opens again")

    def test_a_short_message_s_time_stands_on_its_line(self):
        self.win.open_chat("dm")
        short = self.msgs()[0]
        self.assertTrue(short.tail, "alone in its run: the tail")
        self.assertLessEqual(short.bubble.height(),
                             short.doc.size().height() + 2 * hubstyle_px(6) + 0.5,
                             "one line: the time inside it, no line of its own")
        self.assertGreater(short.meta_at.x(), short.doc_at.x())
        self.assertTrue(short.bubble.contains(short.meta_at))

    def test_a_long_message_s_time_takes_a_line_when_the_last_is_full(self):
        self.ses.state.messages["dm"].append(msg("m5", 5, text="word " * 60))
        self.win.open_chat("dm")
        box = self.msgs()[-1]
        last_w, _base = self.win.feed._last_line(box.doc)
        inner = box.bubble.width() - 2 * hubstyle_px(10)
        fits = look.meta_fits(last_w, self.win.feed._meta_width(
            box, QtGui.QFontMetrics(self.win.feed._meta_font())), inner, hubstyle_px(8))
        under = box.meta_at.y() > box.doc_at.y() + box.doc.size().height()
        self.assertEqual(under, not fits)
        self.assertTrue(box.bubble.contains(box.meta_at))

    def test_reactions_stand_inside_the_bubble(self):
        self.ses.state.messages["dm"][0]["reactions"] = {"👍": ["me", "bob"]}
        self.win.open_chat("dm")
        box = self.msgs()[0]
        rect = box.pills[0][0]
        self.assertTrue(box.bubble.contains(rect))
        self.assertTrue(box.bubble.contains(box.meta_at))

    def test_the_reply_button_shows_on_hover_and_replies(self):
        self.win.open_chat("dm")
        box = self.msgs()[0]
        self.win.feed._hover_row(box.bubble.center())
        self.assertEqual(self.win.feed.hover_key, box.item.key())
        with mock.patch.object(hubmotion, "enabled", return_value=False):
            self.win.feed.tick(16)
        rect = self.win.feed._reply_rect(box)
        self.assertGreater(rect.left(), box.bubble.right(), "theirs: on the right")
        found, where = self.win.feed.box_at(rect.center())
        self.assertEqual(where, "reply")
        event = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonPress, rect.center(),
                                  self.win.feed.mapToGlobal(rect.center()), QtCore.Qt.LeftButton,
                                  QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
        self.win.feed.mousePressEvent(event)
        self.assertEqual(self.win.reply_to, "m1")
        self.assertIn("Ответ Bob", self.win.bar_text.text())
        self.assertEqual(self.win.bar_sub.text(), "first")

    def test_emoji_alone_have_no_bubble_and_a_time_pill(self):
        self.ses.state.messages["dm"].append(msg("m6", 6, text="🔥"))
        self.win.open_chat("dm")
        box = self.msgs()[-1]
        if box.bigs:            # the Fluent picture is shipped: emoji alone are bare
            self.assertTrue(box.bare)
            self.assertIsNotNone(box.meta_pill)
            self.assertFalse(box.tail)

    def test_the_send_button_turns_orange_with_text(self):
        self.win.open_chat("dm")
        self.assertEqual(self.win.send_button.property("skState"), "")
        self.win.composer.setPlainText("hey")
        self.assertEqual(self.win.send_button.property("skState"), "ready")
        self.win.composer.clear()
        self.assertEqual(self.win.send_button.property("skState"), "")

    def test_the_window_paints_its_own_faces(self):
        self.assertEqual(self.win.frame.content_face, "none")
        self.win.open_chat("dm")
        image = QtGui.QImage(self.win.feed.size(), QtGui.QImage.Format_ARGB32)
        image.fill(0)
        self.win.feed.render(image)
        corner = image.pixelColor(6, 6)        # between the pattern's dots
        self.assertEqual((corner.red(), corner.green(), corner.blue()), (0x18, 0x19, 0x1b),
                         "the feed's backdrop")


def hubstyle_px(n):
    import maya_hubstyle
    return maya_hubstyle.px(n, 1.0)
