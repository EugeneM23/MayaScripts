"""maya_chat.window: the parts test_chat_window.py does not reach - hovers, drags, the picker's
mouse, the menus, the file verbs, the panes' buttons, the burst, the module's one window.
Offscreen on test_chat_window's fake session; nothing reaches a server."""
import os
import shutil
import sys
import tempfile
import time
import types
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tests  # noqa: F401  (puts SkeldarAnim/ on sys.path)

from PySide6 import QtCore, QtGui, QtWidgets  # noqa: E402

import maya_hubburst  # noqa: E402
import maya_hubmotion as hubmotion  # noqa: E402
import maya_hubqt  # noqa: E402
import maya_hubsound  # noqa: E402
from maya_chat import api as A  # noqa: E402
from maya_chat import files  # noqa: E402
from maya_chat import look  # noqa: E402
from maya_chat import notify  # noqa: E402
from maya_chat import window as W  # noqa: E402

from tests import test_chat_window as T  # noqa: E402

MISSING = object()
FILE = dict(T.FILE)
CARL = {"id": "carl", "nick": "carl", "name": "Carl", "avatar_v": 0}


def mouse(kind, pos, button=QtCore.Qt.LeftButton, buttons=None, glob=None):
    pos = QtCore.QPointF(pos)
    return QtGui.QMouseEvent(kind, pos, QtCore.QPointF(glob if glob is not None else pos),
                             button, button if buttons is None else buttons,
                             QtCore.Qt.NoModifier)


def wheel(pos, up=True):
    pos = QtCore.QPointF(pos)
    return QtGui.QWheelEvent(pos, pos, QtCore.QPoint(0, 0), QtCore.QPoint(0, 120 if up else -120),
                             QtCore.Qt.NoButton, QtCore.Qt.NoModifier, QtCore.Qt.NoScrollPhase,
                             False)


def render(widget):
    image = QtGui.QImage(max(1, widget.width()), max(1, widget.height()),
                         QtGui.QImage.Format_ARGB32)
    image.fill(0)
    widget.render(image)
    return image


class Swaps(object):
    """setattr with the old value put back on cleanup (module and object attributes)."""

    def swap(self, obj, name, value):
        old = getattr(obj, name, MISSING)
        setattr(obj, name, value)

        def back():
            if old is MISSING:
                try:
                    delattr(obj, name)
                except AttributeError:
                    pass
            else:
                setattr(obj, name, old)
        self.addCleanup(back)
        return old

    def swap_module(self, name, module):
        """One sys.modules entry swapped (never the whole dict), put back on cleanup."""
        old = sys.modules.get(name, MISSING)
        sys.modules[name] = module

        def back():
            if old is MISSING:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old
        self.addCleanup(back)


def group_chat(admin="me"):
    return {"id": "g1", "kind": "group", "name": "Team", "admin": admin, "avatar_v": 0,
            "members": [T.ME, T.BOB, T.ANN], "last": None, "unread": 0, "read_upto": 0}


class Base(Swaps, T.Base):
    def setUp(self):
        T.Base.setUp(self)
        self.swap(files, "DEFER", lambda fn: fn())
        self.swap(files, "SPAWN", lambda fn: fn())
        self.swap(maya_hubsound, "deleted", lambda: self.sounds.append("deleted"))
        self.sounds = []

    def msgs(self):
        return [b for b in self.win.feed.boxes if b.item.kind == "msg"]

    def box(self, mid):
        return next(b for b in self.win.feed.boxes if b.item.kind == "msg"
                    and (b.item.message.get("id") == mid or b.item.message.get("cid") == mid))

    def silent(self):
        """traceback.print_exc quiet for a path that prints on purpose."""
        patcher = mock.patch.object(W.traceback, "print_exc")
        patcher.start()
        self.addCleanup(patcher.stop)


# ---------------------------------------------------------------------------- the list, tabs

class ListHover(Base):
    def test_the_mouse_lights_a_row_and_leaving_puts_it_out(self):
        lst = self.win.list
        lst.resize(250, 300)
        y = lst.row_h() * 1.5
        with mock.patch.object(hubmotion, "enabled", return_value=False):
            lst.mouseMoveEvent(mouse(QtCore.QEvent.MouseMove, QtCore.QPointF(120, y),
                                     QtCore.Qt.NoButton))
            self.assertEqual(lst.hovered, "dm2")
            self.assertEqual(lst.glow.get("dm2"), 1.0)
            self.assertEqual(lst.glow.get("dm"), 0.0)
            lst.leaveEvent(QtCore.QEvent(QtCore.QEvent.Leave))
        self.assertIsNone(lst.hovered)

    def test_a_row_glows_in_over_its_hover_time_and_a_pop_ends(self):
        lst = self.win.list
        lst.hovered = "dm"
        lst.glow = {}
        busy = lst.tick(W.HOVER_MS / 2.0)
        self.assertTrue(busy)
        half = lst.glow["dm"]
        self.assertTrue(0.0 < half < 1.0)
        lst.tick(W.HOVER_MS * 4)
        self.assertEqual(lst.glow["dm"], 1.0)
        lst.pops["dm"] = W._now_ms() - W.POP_MS - 1
        lst.tick(1)
        self.assertNotIn("dm", lst.pops)
        self.assertFalse(lst.tick(1), "at rest: nothing moves")

    def test_an_unread_count_that_changes_pops(self):
        self.ses.state.chats["dm2"]["unread"] = 5
        self.win.refresh()
        self.assertIn("dm2", self.win.list.pops)

    def test_a_click_past_the_rows_does_nothing(self):
        lst = self.win.list
        lst.resize(250, 900)
        lst.mousePressEvent(mouse(QtCore.QEvent.MouseButtonPress, QtCore.QPointF(120, 880)))
        self.assertIsNone(self.win.chat)
        self.assertEqual(lst.index_at(-5), -1)


class TabsHover(Base):
    def test_the_mouse_over_a_tab_and_off_it(self):
        tabs = self.win.tabs
        tabs.resize(260, tabs.height())
        rect = [r for key, _l, r, _c in tabs.rects() if key == "dm"][0]
        tabs.mouseMoveEvent(mouse(QtCore.QEvent.MouseMove, rect.center(), QtCore.Qt.NoButton))
        self.assertEqual(tabs.hovered, "dm")
        drawn = render(tabs)
        self.assertGreater(sum(1 for x in range(0, tabs.width(), 3)
                               if drawn.pixelColor(x, tabs.height() // 2).alpha()), 0)
        tabs.leaveEvent(QtCore.QEvent(QtCore.QEvent.Leave))
        self.assertIsNone(tabs.hovered)
        self.assertIsNone(tabs.key_at(-50))

    def test_a_right_click_on_a_tab_does_nothing(self):
        tabs = self.win.tabs
        tabs.resize(260, tabs.height())
        rect = [r for key, _l, r, _c in tabs.rects() if key == "groups"][0]
        tabs.mousePressEvent(mouse(QtCore.QEvent.MouseButtonPress, rect.center(),
                                   QtCore.Qt.RightButton))
        self.assertEqual(self.win.tab, "all")

    def test_an_unknown_tab_is_ignored(self):
        self.win.set_tab("nope")
        self.assertEqual(self.win.tab, "all")
        self.win.set_tab("groups")
        self.assertEqual(self.win.empty_list_text(), u"Групп пока нет - ✎ создаст")
        self.win.search.setText("zzz")
        self.assertEqual(self.win.empty_list_text(), u"Ничего не найдено")
        self.win.search.setText("")
        self.win.set_tab("all")
        self.assertEqual(self.win.empty_list_text(), u"Пока здесь никого, кроме вас")


# ---------------------------------------------------------------------------- the feed's mouse

class FeedMouse(Base):
    def setUp(self):
        Base.setUp(self)
        self.ses.state.messages["dm"].append(dict(T.msg("mf", 3, text=""), file=dict(FILE)))
        self.win.open_chat("dm")
        self.win.refresh()

    def test_the_reply_button_is_drawn_lit_under_the_mouse(self):
        feed = self.win.feed
        box = self.msgs()[0]
        feed._hover_row(box.bubble.center())
        rect = feed._reply_rect(box)
        feed._hover_row(rect.center())
        self.assertTrue(feed.reply_hot)
        feed.reply_level = 1.0
        lit = render(feed)
        feed.hover_key, feed.reply_hot, feed.reply_level = None, False, 0.0
        plain = render(feed)
        r = rect.toRect()
        differ = sum(1 for x in range(r.left(), r.right()) for y in range(r.top(), r.bottom())
                     if lit.pixelColor(x, y) != plain.pixelColor(x, y))
        self.assertGreater(differ, 20)

    def test_a_card_pressed_and_dragged_starts_the_drag_and_the_release_ends_it(self):
        feed = self.win.feed
        got = []
        self.win.start_drag = lambda item, gp: got.append(("start", item.message["id"])) or True
        self.win.drag_move = lambda gp: got.append(("move",))
        self.win.drag_end = lambda gp, cancel=False: got.append(("end", cancel))
        card = self.box("mf").card
        feed.mousePressEvent(mouse(QtCore.QEvent.MouseButtonPress, card.center()))
        self.assertIsNotNone(feed._press)
        far = card.center() + QtCore.QPointF(40, 0)
        feed.mouseMoveEvent(mouse(QtCore.QEvent.MouseMove, far, QtCore.Qt.NoButton,
                                  QtCore.Qt.LeftButton))
        self.assertTrue(feed._dragging)
        feed.mouseMoveEvent(mouse(QtCore.QEvent.MouseMove, far + QtCore.QPointF(5, 0),
                                  QtCore.Qt.NoButton, QtCore.Qt.LeftButton))
        feed.mouseReleaseEvent(mouse(QtCore.QEvent.MouseButtonRelease, far))
        self.assertFalse(feed._dragging)
        self.assertIsNone(feed._press)
        self.assertEqual(got, [("start", "mf"), ("move",), ("end", False)])

    def test_a_right_release_cancels_the_drag_and_a_press_ends_one_too(self):
        feed = self.win.feed
        ends = []
        self.win.drag_end = lambda gp, cancel=False: ends.append(cancel)
        feed._dragging = True
        feed.mouseReleaseEvent(mouse(QtCore.QEvent.MouseButtonRelease, QtCore.QPointF(5, 5),
                                     QtCore.Qt.RightButton))
        feed._dragging = True
        feed.mousePressEvent(mouse(QtCore.QEvent.MouseButtonPress, QtCore.QPointF(5, 5)))
        self.assertEqual(ends, [True, False])
        feed.mouseReleaseEvent(mouse(QtCore.QEvent.MouseButtonRelease, QtCore.QPointF(5, 5)))
        self.assertEqual(ends, [True, False], "no drag: a release ends nothing")

    def test_a_press_that_does_not_move_far_starts_no_drag(self):
        feed = self.win.feed
        self.win.start_drag = lambda item, gp: self.fail("no drag")
        card = self.box("mf").card
        feed.mousePressEvent(mouse(QtCore.QEvent.MouseButtonPress, card.center()))
        feed.mouseMoveEvent(mouse(QtCore.QEvent.MouseMove, card.center() + QtCore.QPointF(1, 0),
                                  QtCore.Qt.NoButton, QtCore.Qt.LeftButton))
        self.assertFalse(feed._dragging)

    def test_the_mouse_over_a_file_button_lights_it_and_off_the_feed_drops_the_hover(self):
        feed = self.win.feed
        rect = [r for r, a, _l in self.box("mf").fbuttons if a == "open"][0]
        feed.mouseMoveEvent(mouse(QtCore.QEvent.MouseMove, rect.center(), QtCore.Qt.NoButton))
        self.assertEqual(feed._hover_button[1], "open")
        self.assertEqual(feed.cursor().shape(), QtCore.Qt.PointingHandCursor)
        feed._hover_row(self.msgs()[0].bubble.center())
        self.assertIsNotNone(feed.hover_key)
        feed.leaveEvent(QtCore.QEvent(QtCore.QEvent.Leave))
        self.assertIsNone(feed.hover_key)
        self.assertFalse(feed.reply_hot)
        self.assertIsNone(feed._emoji_hover)

    def test_top_of_finds_a_message_s_row(self):
        box = self.box("m2")
        self.assertEqual(self.win.feed.top_of("m2"), box.rect.top())
        self.assertIsNone(self.win.feed.top_of("nope"))

    def test_a_click_on_a_quote_scrolls_to_the_original(self):
        self.ses.state.messages["dm"].append(T.msg("mr", 4, text="re", reply_to="m1"))
        self.win.refresh()
        box = self.box("mr")
        self.assertIsNotNone(box.quote)
        qrect = box.quote[0]
        self.win.feed.mousePressEvent(mouse(QtCore.QEvent.MouseButtonPress, qrect.center()))
        self.assertIn(self.box("m1").item.key(), self.win.feed.flashing)

    def test_a_middle_press_on_a_bubble_does_nothing(self):
        before = list(self.ses.calls)
        self.win.feed.mousePressEvent(mouse(QtCore.QEvent.MouseButtonPress,
                                            self.box("m1").bubble.center(),
                                            QtCore.Qt.MiddleButton))
        self.assertEqual(self.ses.calls, before)

    def test_a_right_press_opens_the_message_menu(self):
        shown = []
        self.win.message_menu = lambda item, gp: shown.append(item.message["id"])
        self.win.feed.mousePressEvent(mouse(QtCore.QEvent.MouseButtonPress,
                                            self.box("m1").bubble.center(),
                                            QtCore.Qt.RightButton))
        self.assertEqual(shown, ["m1"])

    def test_the_read_ticks_are_drawn(self):
        self.ses.state.reads["dm"] = {"bob": 9}
        self.win.refresh()
        mine = [b for b in self.msgs() if b.item.mine][0]
        self.assertEqual(mine.item.tick, "read")
        image = QtGui.QImage(40, 20, QtGui.QImage.Format_ARGB32)
        image.fill(0)
        p = QtGui.QPainter(image)
        try:
            width = W.paint_ticks(p, 30, 10, "read", "#ffffff", 1.0)
            failed = W.paint_ticks(p, 10, 10, "failed", "#ffffff", 1.0)
            nothing = W.paint_ticks(p, 10, 10, "", "#ffffff", 1.0)
        finally:
            p.end()
        self.assertEqual((width, failed, nothing), (W.tick_width("read", 1.0),
                                                    W.tick_width("failed", 1.0), 0))
        self.assertGreater(sum(1 for x in range(40) for y in range(20)
                               if image.pixelColor(x, y).alpha()), 5)
        drawn = render(self.win.feed)
        self.assertGreater(sum(1 for x in range(0, drawn.width(), 3)
                               for y in range(0, drawn.height(), 3)
                               if drawn.pixelColor(x, y).alpha()), 10)


class FeedPaint(Base):
    """What the feed draws for each state, and the presses on its parts."""

    def setUp(self):
        Base.setUp(self)
        self.reacted = []
        self.ses.react = lambda chat, mid, e: self.reacted.append((chat, mid, e)) or True
        dm = self.ses.state.messages["dm"]
        dm[0]["reactions"] = {"👍": ["me", "bob"], "🔥": ["bob"]}
        dm.append(T.msg("mr", 3, text="answer", reply_to="m1"))
        dm.append(T.msg("mx", 4, text="quoting a gone one", reply_to="gone"))
        dm.append(T.msg("ml", 5, text="see https://example.com/x now"))
        self.ses.state.chats["dm"]["unread"] = 3
        self.ses.state.pending["dm"] = [
            {"cid": "pc", "chat": "dm", "text": "going", "at": T.NOW, "from_id": "me",
             "state": "sending", "error": None},
            {"cid": "pf", "chat": "dm", "text": "lost", "at": T.NOW, "from_id": "me",
             "state": "failed", "error": None}]
        self.win.open_chat("dm")
        self.win.refresh()

    def inked(self, image, rect):
        r = rect.toRect()
        return sum(1 for x in range(max(0, r.left()), min(image.width(), r.right()), 2)
                   for y in range(max(0, r.top()), min(image.height(), r.bottom()), 2)
                   if image.pixelColor(x, y).alpha())

    def test_quotes_pills_the_unread_band_and_a_fold_are_drawn(self):
        feed = self.win.feed
        kinds = [b.item.kind for b in feed.boxes]
        self.assertIn("unread", kinds)
        quoted = self.box("mx")
        self.assertEqual(quoted.quote[2:4], ("", u"сообщение"))
        feed.folding = [(5.0, 40.0, W._now_ms())]
        feed.pill_pops[("m1", "🔥")] = W._now_ms() - W.POP_MS / 2.0
        image = render(feed)
        self.assertGreater(self.inked(image, self.box("mr").quote[0]), 10)
        for rect, _e, _n, _me in self.box("m1").pills:
            self.assertGreater(self.inked(image, rect), 5)
        band = next(b for b in feed.boxes if b.item.kind == "unread").band
        self.assertGreater(self.inked(image, band), 10)
        self.assertGreater(self.inked(image, self.box("pf").failed_rect), 0)

    def test_a_press_on_failed_retries_and_on_a_pill_reacts(self):
        box = self.box("pf")
        self.win.feed.mousePressEvent(mouse(QtCore.QEvent.MouseButtonPress,
                                            box.failed_rect.center()))
        self.assertIn(("retry", "pf"), self.ses.calls)
        rect = self.box("m1").pills[1][0]
        self.win.feed.mousePressEvent(mouse(QtCore.QEvent.MouseButtonPress, rect.center()))
        self.assertEqual(self.reacted, [("dm", "m1", self.box("m1").pills[1][1])])

    def test_a_link_in_a_message_opens_and_a_plain_word_does_not(self):
        box = self.box("ml")
        layout = box.doc.documentLayout()
        size = box.doc.size()
        at = next(QtCore.QPointF(x, y) for y in range(2, int(size.height()), 2)
                  for x in range(2, int(size.width()), 2)
                  if layout.anchorAt(QtCore.QPointF(x, y)))
        opened = []
        with mock.patch.object(QtGui.QDesktopServices, "openUrl",
                               side_effect=lambda url: opened.append(url.toString())):
            self.win.feed.mousePressEvent(mouse(QtCore.QEvent.MouseButtonPress,
                                                box.doc_at + at))
            self.win.feed.mouseMoveEvent(mouse(QtCore.QEvent.MouseMove, box.doc_at + at,
                                               QtCore.Qt.NoButton))
            self.assertEqual(self.win.feed.cursor().shape(), QtCore.Qt.PointingHandCursor)
            self.win.feed.mousePressEvent(mouse(QtCore.QEvent.MouseButtonPress,
                                                box.doc_at + QtCore.QPointF(2, 2)))
        self.assertEqual(opened, ["https://example.com/x"])

    def test_a_reaction_refused_or_offline_is_said(self):
        def refuse(chat, mid, e):
            raise A.ChatError("too_many", "too many reactions")
        self.ses.react = refuse
        self.assertIsNone(self.win.react({"id": "m1"}, "👍"))
        self.assertEqual(self.win.line.text(), "too many reactions")
        self.ses.react = lambda chat, mid, e: None
        self.assertIsNone(self.win.react({"id": "m1"}, "👍"))
        self.assertIn(u"Нет связи", self.win.line.text())
        W._VARS.pop("skeldarChatEmojiRecent", None)
        self.ses.react = lambda chat, mid, e: False
        self.assertFalse(self.win.react({"id": "m1"}, "👍"))
        self.assertIsNone(W.get_var("skeldarChatEmojiRecent"), "taken off: not recent")
        self.assertIsNone(self.win.react(None, "👍"))

    def test_a_send_refused_keeps_the_text(self):
        def refuse(chat, text, reply_to=None):
            raise A.ChatError("too_long", "message too long")
        self.ses.send = refuse
        self.win.composer.setPlainText("keep me")
        self.assertIsNone(self.win.send_now())
        self.assertEqual(self.win.line.text(), "message too long")
        self.assertEqual(self.win.composer.toPlainText(), "keep me")
        self.win.composer.setPlainText("   ")
        self.assertIsNone(self.win.send_now())
        self.win.chat = None
        self.assertIsNone(self.win.send_now())
        self.assertIsNone(self.win.start_call("audio"))

    def test_a_file_dragged_onto_stash_or_shared_asks_the_file_drag_rules(self):
        import maya_filedrag
        seen = []
        self.swap(maya_filedrag, "_names_at", lambda x, y: ["names"])
        self.swap(maya_filedrag, "section_under", lambda names: None)
        self.swap(maya_filedrag, "_viewport_at", lambda x, y: 1 / 0)
        self.swap(maya_filedrag, "aim_for", lambda who, under, viewport: seen.append(
            (who, under, viewport)) or {"kind": "none", "text": "x"})
        item = look.Item("msg", "", {"id": "m", "file": dict(FILE)})
        self.win._card_drag = {"item": item}
        self.win.drag_aim(QtCore.QPoint(3, 4))
        self.assertEqual(seen, [("chat", None, False)])
        self.win._card_drag = None

    def test_the_list_draws_its_people_head_a_lit_row_and_the_open_chat(self):
        self.ses.read_people()
        self.win.refresh()
        lst = self.win.list
        lst.resize(260, int(lst.tops()[1]))
        lst.glow["dm2"] = 0.7
        image = render(lst)
        tops, _total = lst.tops()
        head = next(i for i, r in enumerate(lst.rows) if r["kind"] == "head")
        rect = QtCore.QRectF(0, tops[head], lst.width(), lst.row_h(lst.rows[head]))
        self.assertGreater(self.inked(image, rect), 5)
        sel = next(i for i, r in enumerate(lst.rows) if r["id"] == "dm")
        self.assertGreater(self.inked(image, QtCore.QRectF(0, tops[sel], lst.width(),
                                                           lst.row_h())), 100)


class GroupFeed(Base):
    def setUp(self):
        Base.setUp(self)
        self.ses.state.chats["g1"] = group_chat()
        self.ses.state.messages["g1"] = [T.msg("g-1", 1, frm="bob", chat="g1", text="from bob"),
                                         T.msg("g-2", 2, frm="ann", chat="g1", text="from ann")]
        self.win.open_chat("g1")
        self.win.refresh()

    def test_a_press_on_a_sender_s_name_opens_their_card(self):
        opened = []
        self.win.show_profile = lambda user: opened.append(user["id"]) or True
        box = self.box("g-1")
        self.assertIsNotNone(box.name_at)
        at = QtCore.QPointF(box.name_at.x() + 2, box.name_at.y() - W.px_of(self.win.feed, 4))
        self.win.feed.mousePressEvent(mouse(QtCore.QEvent.MouseButtonPress, at))
        self.assertEqual(opened, ["bob"])

    def test_the_group_feed_paints_names_and_avatars(self):
        box = self.box("g-2")
        self.assertIsNotNone(box.avatar)
        image = render(self.win.feed)
        r = box.avatar.toRect()
        self.assertGreater(sum(1 for x in range(r.left(), r.right())
                               for y in range(r.top(), r.bottom())
                               if image.pixelColor(x, y).alpha()), 20)

    def test_the_members_button_shows_for_a_group(self):
        self.assertTrue(self.win.members_button.isVisibleTo(self.win.root))
        self.win.members_button.click()
        self.assertEqual(self.win.pane, "members")


# ---------------------------------------------------------------------------- the picker's mouse

class PickerMouse(Base):
    def setUp(self):
        Base.setUp(self)
        W._VARS.pop("skeldarChatEmojiTone", None)
        self.win.open_chat("dm")
        self.picker = self.win.pick_emoji()

    def tearDown(self):
        try:
            self.picker.close()
        except RuntimeError:
            pass
        Base.tearDown(self)

    def in_widget(self, rect):
        return QtCore.QPointF(rect.center().x(), rect.center().y() + self.picker.top_grid
                              - self.picker.scroll)

    def test_the_wheel_scrolls_within_the_grid(self):
        p = self.picker
        at = QtCore.QPointF(p.width() / 2.0, p.top_grid + 10)
        p.wheelEvent(wheel(at, up=False))
        self.assertGreater(p.scroll, 0)
        for _i in range(5):
            p.wheelEvent(wheel(at, up=True))
        self.assertEqual(p.scroll, 0.0)
        for _i in range(2000):
            p.wheelEvent(wheel(at, up=False))
            if p.scroll >= p.max_scroll():
                break
        self.assertEqual(p.scroll, p.max_scroll())

    def test_a_press_on_a_tone_picks_it(self):
        p = self.picker
        rect, tone = p._tone_rects()[2]
        p.mousePressEvent(mouse(QtCore.QEvent.MouseButtonPress, rect.center()))
        self.assertEqual(p.tone, 2)
        self.assertEqual(int(W.get_var("skeldarChatEmojiTone")), 2)

    def test_a_press_on_a_tab_scrolls_and_clears_a_search(self):
        p = self.picker
        p.set_query("кот")
        rect = [r for r, key, _g in p._tabs() if key == "food"][0]
        p.mousePressEvent(mouse(QtCore.QEvent.MouseButtonPress, rect.center()))
        self.assertEqual(p.query, "")
        self.assertEqual(p._active_tab(), "food")

    def test_a_press_on_a_cell_picks_its_emoji(self):
        p = self.picker
        rect, g = p.cells[0]
        p.mousePressEvent(mouse(QtCore.QEvent.MouseButtonPress, self.in_widget(rect)))
        self.assertEqual(self.win.composer.toPlainText(), g)

    def test_a_press_on_nothing_and_one_outside(self):
        p = self.picker
        between = QtCore.QPointF(p.width() - 2, p.top_tones - 1)
        self.assertIsNone(p.hit(between))
        p.mousePressEvent(mouse(QtCore.QEvent.MouseButtonPress, between))
        self.assertTrue(p.isVisible())
        p.mousePressEvent(mouse(QtCore.QEvent.MouseButtonPress, QtCore.QPointF(-30, -30)))
        self.assertFalse(p.isVisible())

    def test_the_lift_rises_and_falls_on_its_timer(self):
        p = self.picker
        rect, g = p.cells[3]
        with mock.patch.object(hubmotion, "enabled", return_value=True):
            p.mouseMoveEvent(mouse(QtCore.QEvent.MouseMove, self.in_widget(rect),
                                   QtCore.Qt.NoButton))
            self.assertEqual(p.hover, ("emoji", g))
            self.assertTrue(p.timer.isActive())
            p._last = time.monotonic() - W.HOVER_MS / 2000.0
            p._tick()
            self.assertTrue(0.0 < p.levels[("emoji", g)] < 1.0)
            p._last = time.monotonic() - 1.0
            p._tick()
            self.assertEqual(p.levels[("emoji", g)], 1.0)
            self.assertFalse(p.timer.isActive(), "at rest the timer stops")
            p.leaveEvent(QtCore.QEvent(QtCore.QEvent.Leave))
            self.assertIsNone(p.hover)
            p._last = time.monotonic() - 1.0
            p._tick()
            self.assertEqual(p.levels, {})

    def test_with_animations_off_the_lift_is_at_once(self):
        p = self.picker
        rect, g = p.cells[1]
        with mock.patch.object(hubmotion, "enabled", return_value=False):
            p.mouseMoveEvent(mouse(QtCore.QEvent.MouseMove, self.in_widget(rect),
                                   QtCore.Qt.NoButton))
            self.assertEqual(p.levels, {("emoji", g): 1.0})
            p.leaveEvent(QtCore.QEvent(QtCore.QEvent.Leave))
            self.assertEqual(p.levels, {})

    def test_a_picker_whose_handler_raises_still_closes(self):
        self.silent()
        p = self.picker
        p.picked = lambda e: 1 / 0
        p.pick("🔥")
        self.assertFalse(p.isVisible())

    def test_a_reaction_picked_from_the_cursor(self):
        self.picker.close()
        got = []
        self.ses.react = lambda chat, mid, e: got.append((chat, mid, e)) or True
        with mock.patch.object(W, "_cursor", return_value=None):
            self.picker = self.win.pick_emoji(message=self.ses.state.messages["dm"][0])
        self.picker.pick("😂")
        self.assertEqual(got, [("dm", "m1", "😂")])
        self.assertIn("😂", W.get_var("skeldarChatEmojiRecent"))


# ---------------------------------------------------------------------------- menus

class Menus(Base):
    def setUp(self):
        Base.setUp(self)
        self.reacted = []
        self.ses.react = lambda chat, mid, e: self.reacted.append((chat, mid, e)) or True
        self.ses.state.messages["dm"].append(dict(T.msg("mf", 3, text=""), file=dict(FILE)))
        self.ses.state.messages["dm"].append(dict(
            T.msg("mi", 4, text=""), file=dict(FILE, id="i" * 16, name="ref.png", kind="image")))
        self.win.open_chat("dm")
        self.win.refresh()

    def tearDown(self):
        menu = getattr(self.win, "_menu", None)
        if menu is not None:
            try:
                menu.close()
            except RuntimeError:
                pass
        Base.tearDown(self)

    def test_the_message_menu_opens_with_quick_reactions_and_icons(self):
        item = self.box("m1").item
        self.win.message_menu(item, QtCore.QPoint(10, 10))
        menu = self.win._menu
        acts = menu.actions()
        self.assertIsInstance(acts[0], QtWidgets.QWidgetAction)
        self.assertTrue(acts[1].isSeparator())
        rows = dict((a.text(), a) for a in acts[2:])
        self.assertIn(u"Ответить", rows)
        self.assertFalse(rows[u"Ответить"].icon().isNull())
        self.assertTrue(rows[u"Реакция…"].icon().isNull() is False)
        rows[u"Ответить"].trigger()
        self.assertEqual(self.win.reply_to, "m1")

    def test_a_quick_reaction_reacts_and_closes_the_menu(self):
        item = self.box("m1").item
        self.ses.state.messages["dm"][0]["reactions"] = {"👍": ["me"]}
        self.win.message_menu(item, QtCore.QPoint(10, 10))
        holder = self.win._menu.findChild(QtWidgets.QWidget, "skeldarChatQuickReactions")
        buttons = holder.findChildren(QtWidgets.QToolButton)
        self.assertEqual(len(buttons), 6)
        lit = [b for b in buttons if b.styleSheet()]
        self.assertEqual(len(lit), 1, "mine is lit")
        buttons[1].click()
        self.assertEqual(self.reacted[-1][:2], ("dm", "m1"))

    def test_a_pending_message_s_menu_has_no_reactions_and_its_delete_discards(self):
        self.ses.state.pending["dm"] = [{"cid": "p1", "chat": "dm", "text": "wait", "at": T.NOW,
                                          "from_id": "me", "state": "failed", "error": None}]
        self.win.refresh()
        item = self.box("p1").item
        self.win.message_menu(item, QtCore.QPoint(10, 10))
        acts = self.win._menu.actions()
        self.assertNotIsInstance(acts[0], QtWidgets.QWidgetAction)
        self.assertEqual([a.text() for a in acts], [u"Повторить", u"Удалить"])
        acts[1].trigger()
        self.assertIn(("discard", "p1"), self.ses.calls)

    def test_a_retry_of_a_pending_send_marks_it_failed_first(self):
        pending = {"cid": "p2", "chat": "dm", "text": "wait", "at": T.NOW, "from_id": "me",
                   "state": "sending", "error": None}
        self.ses.state.pending["dm"] = [pending]
        self.ses._find_pending = lambda cid: pending if cid == "p2" else None
        self.win.refresh()
        self.win.retry(self.box("p2").item)
        self.assertEqual(pending["state"], "failed")
        self.assertIn(("retry", "p2"), self.ses.calls)
        before = list(self.ses.calls)
        self.win.retry(self.box("m1").item)                     # not pending: nothing
        self.assertEqual(self.ses.calls, before)

    def test_copy_puts_the_text_on_the_clipboard(self):
        rows = dict(self.win.menu_rows(self.box("m1").item))
        rows[u"Скопировать"]()
        self.assertEqual(QtWidgets.QApplication.clipboard().text(), "first")

    def test_edit_and_delete_rows_of_mine(self):
        rows = dict(self.win.menu_rows(self.box("m2").item))
        rows[u"Изменить"]()
        self.assertEqual(self.win.editing, "m2")
        self.win.cancel_bar()
        rows[u"Удалить"]()
        self.assertEqual(self.ses.calls[-1], ("delete", "dm", "m2"))
        self.assertEqual(self.sounds, ["deleted"])

    def test_a_refused_delete_says_why_and_plays_nothing(self):
        def refuse(chat, mid):
            raise A.ChatError("gone", "already gone")
        self.ses.delete = refuse
        self.win.delete_message({"id": "m2"})
        self.assertEqual(self.win.line.text(), "already gone")
        self.assertEqual(self.sounds, [])

    def test_the_reaction_row_opens_the_picker_for_the_message(self):
        rows = dict(self.win.menu_rows(self.box("m1").item))
        rows[u"Реакция…"]()
        picker = self.win._picker
        picker.pick("🔥")
        self.assertEqual(self.reacted[-1], ("dm", "m1", "🔥"))

    def test_a_file_s_rows_and_a_picture_s_rows_go_to_file_action(self):
        done = []
        self.win.file_action = lambda item, action, at=None, target=None: done.append(
            (item.message["id"], action))
        for label in ("Open", "Import", u"Сохранить как…", u"В Stash"):
            dict(self.win.menu_rows(self.box("mf").item))[label]()
        for label in (u"Открыть", u"Сохранить как…"):
            dict(self.win.menu_rows(self.box("mi").item))[label]()
        self.assertEqual(done, [("mf", "open"), ("mf", "import"), ("mf", "save"),
                                ("mf", "stash"), ("mi", "view"), ("mi", "save")])

    def test_a_call_line_s_menu_offers_no_copy_or_edit(self):
        note = {"id": "c", "kind": "audio", "answered": True, "seconds": 7}
        self.ses.state.messages["dm"].append(dict(T.msg("mc", 9, frm="me", text="📞 7 s"),
                                                  call=note))
        self.win.refresh()
        item = next(b.item for b in self.win.feed.boxes if b.item.kind == "call")
        labels = [label for label, _f in self.win.menu_rows(item)]
        self.assertNotIn(u"Скопировать", labels)
        self.assertNotIn(u"Изменить", labels)

    def test_the_paperclip_menu_runs_its_rows(self):
        got = []
        self.swap(files, "send_scene", lambda ses, chat, caption="": got.append(
            ("scene", chat, caption)) or "cid")
        self.win.composer.setPlainText("the shot")
        self.win.clip_button.click()
        menu = self.win._menu
        acts = dict((a.text(), a) for a in menu.actions())
        self.assertEqual(sorted(acts), sorted(label for label, _f in self.win.clip_rows()))
        self.assertFalse(acts[u"Отправить сцену"].icon().isNull())
        acts[u"Отправить сцену"].trigger()
        self.assertEqual(got, [("scene", "dm", "the shot")])

    def test_a_menu_with_no_rows_is_not_shown(self):
        self.win._menu = None
        with mock.patch.object(self.win, "menu_rows", return_value=[]):
            self.win.message_menu(self.box("m1").item, QtCore.QPoint(1, 1))
        self.assertIsNone(self.win._menu)


# ---------------------------------------------------------------------------- sending files

class Sending(Base):
    def setUp(self):
        Base.setUp(self)
        self.win.open_chat("dm")
        self.got = []
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)

    def sender(self, kind):
        def send(ses, chat, *args):
            self.got.append((kind, chat) + args)
            return "cid-" + kind
        return send

    def test_scene_selection_card_and_path_go_with_the_caption(self):
        for name in ("send_scene", "send_selection", "send_card", "send_path"):
            self.swap(files, name, self.sender(name))
        self.win.composer.setPlainText("one")
        self.assertEqual(self.win.send_scene(), "cid-send_scene")
        self.win.composer.setPlainText("two")
        self.assertEqual(self.win.send_selection(), "cid-send_selection")
        self.win.composer.setPlainText("three")
        self.assertEqual(self.win.send_card("C:/lib/Fist.pose"), "cid-send_card")
        self.assertEqual(self.win.send_path("C:/x/Run.ma"), "cid-send_path")
        self.assertEqual(self.got, [("send_scene", "dm", "one"), ("send_selection", "dm", "two"),
                                    ("send_card", "dm", "C:/lib/Fist.pose", "three"),
                                    ("send_path", "dm", "C:/x/Run.ma", "")])
        self.assertEqual(self.win.composer.toPlainText(), "")
        self.assertFalse(self.win.line.isVisibleTo(self.win.root))

    def test_a_refusal_is_said_and_the_editing_text_is_no_caption(self):
        def refuse(ses, chat, caption=""):
            raise A.ChatError("nothing_selected", u"Сначала выделите объекты")
        self.swap(files, "send_selection", refuse)
        self.assertIsNone(self.win.send_selection())
        self.assertEqual(self.win.line.text(), u"Сначала выделите объекты")
        self.win.start_edit(self.ses.state.messages["dm"][1])
        self.assertEqual(self.win._caption(), "")
        self.assertEqual(self.win.composer.toPlainText(), "mine", "the edit keeps its text")

    def test_an_unexpected_error_is_said_too(self):
        self.silent()
        self.swap(files, "send_scene", lambda ses, chat, caption="": 1 / 0)
        self.assertIsNone(self.win.send_scene())
        self.assertIn("division", self.win.line.text())

    def test_a_picture_from_a_path_is_made_an_image(self):
        path = os.path.join(self.dir, "p.png")
        image = QtGui.QImage(8, 8, QtGui.QImage.Format_RGB32)
        image.fill(QtGui.QColor("#00ff00"))
        image.save(path)
        seen = []
        self.swap(files, "send_image", lambda ses, chat, img, caption="": seen.append(
            (chat, img.width(), img.pixelColor(1, 1).name())) or "c")
        self.assertEqual(self.win.send_image(path), "c")
        self.assertEqual(seen, [("dm", 8, "#00ff00")])

    def test_the_file_dialog_sends_what_was_picked(self):
        self.swap(files, "send_path", self.sender("send_path"))
        with mock.patch.object(QtWidgets.QFileDialog, "getOpenFileName",
                               return_value=("C:/x/Run.fbx", "")):
            self.assertEqual(self.win.send_file_dialog(), "cid-send_path")
        with mock.patch.object(QtWidgets.QFileDialog, "getOpenFileName", return_value=("", "")):
            self.assertIsNone(self.win.send_file_dialog())
        self.assertEqual(self.got, [("send_path", "dm", "C:/x/Run.fbx", "")])

    def test_dropped_files_only_good_ones(self):
        self.swap(files, "send_path", self.sender("send_path"))
        self.assertEqual(self.win.dropped(["C:/x/a.txt"]), 0)
        self.assertIn(".ma", self.win.line.text())

    def test_the_drop_filter_takes_files_and_sends_them(self):
        sent = []
        self.win.dropped = lambda paths: sent.append(paths) or len(paths)
        mime = QtCore.QMimeData()
        mime.setUrls([QtCore.QUrl.fromLocalFile("C:/x/Run.ma")])
        flt = self.win._drops
        for kind in (QtCore.QEvent.DragEnter, QtCore.QEvent.DragMove):
            ev = QtGui.QDragMoveEvent(QtCore.QPoint(5, 5), QtCore.Qt.CopyAction, mime,
                                      QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, kind)
            self.assertTrue(flt.eventFilter(self.win.root, ev))
        drop = QtGui.QDropEvent(QtCore.QPointF(5, 5), QtCore.Qt.CopyAction, mime,
                                QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
        self.assertTrue(flt.eventFilter(self.win.root, drop))
        self.assertEqual(sent, [["C:/x/Run.ma"]])
        empty = QtCore.QMimeData()
        self.assertFalse(flt.eventFilter(self.win.root, QtGui.QDropEvent(
            QtCore.QPointF(5, 5), QtCore.Qt.CopyAction, empty, QtCore.Qt.LeftButton,
            QtCore.Qt.NoModifier)))
        self.assertEqual(W._local_paths(None), [])


# ---------------------------------------------------------------------------- a file's verbs

class FileVerbs(Base):
    def setUp(self):
        Base.setUp(self)
        self.ses.state.messages["dm"].append(dict(T.msg("mf", 3, text=""), file=dict(FILE)))
        self.win.open_chat("dm")
        self.win.refresh()
        self.item = self.box("mf").item
        self.calls = []
        self.swap(files, "fetch", lambda ses, f, then: (then("C:/dl/" + f["name"]), True)[1])

    def verb(self, name):
        def fn(*args):
            self.calls.append((name,) + args)
            return name + " done"
        self.swap(files, name, fn)

    def test_every_verb_runs_on_the_downloaded_file(self):
        for name in ("open_file", "import_file", "save_to", "to_stash", "to_share",
                     "show_picture", "to_library", "apply_card"):
            self.verb(name)
        f = self.item.message["file"]
        for action, name in (("open", "open_file"), ("import", "import_file"),
                             ("save", "save_to"), ("stash", "to_stash"), ("share", "to_share"),
                             ("view", "show_picture")):
            self.assertTrue(self.win.file_action(self.item, action))
            self.assertEqual(self.win.line.text(), name + " done")
        self.win.file_action(self.item, "library", target={"folder": "Fights"})
        self.win.file_action(self.item, "apply", target={"kind": "character", "root": "|r"})
        path = "C:/dl/Run_Cycle.ma"
        self.assertEqual(self.calls, [
            ("open_file", path, f, "Bob"), ("import_file", path, f, "Bob"),
            ("save_to", path, f), ("to_stash", path, f), ("to_share", path, f),
            ("show_picture", path, f, 1.0), ("to_library", path, "Fights"),
            ("apply_card", path, {"kind": "character", "root": "|r"})])

    def test_my_own_file_is_from_you(self):
        self.verb("open_file")
        mine = dict(self.item.message, from_id="me")
        self.win.file_action(look.Item("msg", "", mine, mine=True), "open")
        self.assertEqual(self.calls[-1][-1], u"вас")
        stranger = dict(self.item.message, from_id="zed")
        self.win.file_action(look.Item("msg", "", stranger), "open")
        self.assertEqual(self.calls[-1][-1], "@?")

    def test_a_verb_that_raises_is_said(self):
        self.silent()
        self.swap(files, "open_file", lambda path, f, sender: 1 / 0)
        self.win.file_action(self.item, "open")
        self.assertIn(u"Не вышло", self.win.line.text())

    def test_a_refused_fetch_is_said_and_an_unknown_verb_is_nothing(self):
        def expired(ses, f, then):
            raise A.ChatError("expired", "This file has expired")
        self.swap(files, "fetch", expired)
        self.assertIsNone(self.win.file_action(self.item, "open"))
        self.assertEqual(self.win.line.text(), "This file has expired")
        self.assertIsNone(self.win.file_action(self.item, "nope"))

    def test_more_opens_a_menu_of_save_and_stash(self):
        self.verb("to_stash")
        self.assertIsNone(self.win.file_action(self.item, "more", QtCore.QPoint(3, 3)))
        menu = self.win._menu
        acts = dict((a.text(), a) for a in menu.actions())
        self.assertEqual(sorted(acts), sorted([u"Сохранить как…", u"В Stash"]))
        acts[u"В Stash"].trigger()
        self.assertEqual(self.calls[-1][0], "to_stash")
        menu.close()

    def test_a_card_hint_and_a_picture_state(self):
        card = look.Item("msg", "", {"file": dict(FILE, kind="pose", name="F.pose")})
        self.assertEqual(self.win.file_state(card), ("card", None, W.CARD_HINT))
        pic = look.Item("msg", "", {"file": dict(FILE, kind="image", name="a.png")})
        self.assertEqual(self.win.file_state(pic), ("image", None, ""))
        self.ses.state.downloads[FILE["id"]] = {"state": "loading", "progress": None, "then": []}
        self.assertEqual(self.win.file_state(self.item)[2], u"скачиваю…")
        up = look.Item("msg", "", {"file": dict(FILE), "upload": {"phase": "zip"}},
                       pending=True)
        self.assertEqual(self.win.file_state(up), ("upload", None, u"сжимаю…"))
        failed = look.Item("msg", "", {"file": dict(FILE), "state": "failed",
                                       "upload": {"phase": "upload"}}, pending=True)
        self.assertEqual(self.win.file_state(failed)[0], "failed")

    def test_a_picture_or_a_file_without_an_id_is_not_dragged(self):
        pic = look.Item("msg", "", {"file": dict(FILE, kind="image", name="a.png")})
        self.assertFalse(self.win.start_drag(pic, QtCore.QPoint(1, 1)))
        noid = look.Item("msg", "", {"file": dict(FILE, id=None)})
        self.assertFalse(self.win.start_drag(noid, QtCore.QPoint(1, 1)))

    def test_with_no_drag_standing_drag_end_and_drag_move_do_nothing(self):
        """Fixed 2026-10-27 (the card drag is `self._card_drag` now), the bug as it was: ChatWindow
        kept its card drag in `self._drag`, which is also
        the name of its title-drag METHOD (window.py:4185). Before any card drag,
        getattr(self, "_drag", None) is that bound method, so the "no drag" guards of drag_end
        and drag_move never fire: drag_end raises TypeError ('method' object is not
        subscriptable) and drag_move AttributeError, where both should return None."""
        self.assertIsNone(self.win.drag_end(QtCore.QPoint(1, 1)))
        self.assertIsNone(self.win.drag_move(QtCore.QPoint(1, 1)))
        self.assertTrue(callable(self.win._drag))          # the title still drags the window

    def test_a_cancelled_drag_does_nothing(self):
        self.win._later = lambda fn: self.fail("nothing runs")
        with mock.patch.object(self.win, "drag_aim", lambda gp: {"kind": "import", "text": "x"}):
            self.assertTrue(self.win.start_drag(self.item, QtCore.QPoint(5, 5)))
            self.assertIsNone(self.win.drag_end(QtCore.QPoint(6, 6), cancel=True))
        self.win.drag_move(QtCore.QPoint(1, 1))          # the drag ended: nothing

    def test_a_drag_onto_the_floor_applies_onto_a_new_character(self):
        done = []
        self.win._later = lambda fn: fn()
        self.win.file_action = lambda item, action, at=None, target=None: done.append(
            (action, target))
        aim = {"kind": "apply", "point": (1, 0, 2), "floor": True, "text": u"на полу"}
        with mock.patch.object(self.win, "drag_aim", lambda gp: dict(aim)):
            self.win.start_drag(self.item, QtCore.QPoint(5, 5))
            self.assertIn(u"на полу", self.win._card_drag["ghost"].caption_text())
            self.assertEqual(self.win.drag_end(QtCore.QPoint(6, 6)), "apply")
        self.assertEqual(done[0][1]["kind"], "floor")


# ---------------------------------------------------------------------------- card_aim

class FakeLive(object):
    def __init__(self, folder):
        self.folder = folder

    def folder_at(self, x, y):
        return self.folder


class CardAim(Base):
    def setUp(self):
        Base.setUp(self)
        from maya_poselib import window as libwindow
        from maya_scenesetup import droptarget
        self.lib, self.drop = libwindow, droptarget
        self.snaps = []
        self.swap(libwindow, "live", lambda: None)
        self.swap(maya_hubqt, "on_hub", lambda x, y, control=None: False)
        self.swap(droptarget, "snapshot", lambda: self.snaps.append(1) or "SNAP")
        self.swap(droptarget, "character_target",
                  lambda x, y, snap, scale=1.0: {"kind": "none", "text": "nowhere"})
        self.swap(droptarget, "floor_at", lambda x, y: {"kind": "none"})

    def aim(self, drag=None):
        return self.win.card_aim(QtCore.QPoint(10, 20), {} if drag is None else drag)

    def test_a_folder_of_the_library_s_tree(self):
        self.swap(self.lib, "live", lambda: FakeLive("Fights"))
        self.assertEqual(self.aim(), {"kind": "library", "folder": "Fights",
                                      "text": u"в библиотеку · Fights"})
        self.swap(self.lib, "live", lambda: FakeLive(""))
        self.assertEqual(self.aim()["text"], u"в библиотеку · Library")

    def test_the_library_window_itself_is_from_chat(self):
        self.swap(maya_hubqt, "on_hub", lambda x, y, control=None: control == self.lib.CONTROL)
        self.assertEqual(self.aim(), {"kind": "library", "folder": None,
                                      "text": u"в библиотеку · From Chat"})

    def test_a_character_under_the_cursor(self):
        self.swap(self.drop, "character_target", lambda x, y, snap, scale=1.0: {
            "kind": "character", "root": "|root", "label": "Manny"})
        drag = {}
        self.assertEqual(self.aim(drag), {"kind": "apply", "root": "|root", "text": u"на Manny"})
        self.aim(drag)
        self.assertEqual(self.snaps, [1], "the scene is read once a drag")
        self.assertEqual(drag["snap"], "SNAP")

    def test_the_floor_then_nowhere(self):
        self.swap(self.drop, "floor_at", lambda x, y: {"kind": "floor", "point": (1, 0, 2)})
        self.assertEqual(self.aim(), {"kind": "apply", "point": (1, 0, 2), "floor": True,
                                      "text": u"новый персонаж на полу"})
        self.swap(self.drop, "character_target", lambda x, y, snap, scale=1.0: {
            "kind": "none", "text": self.drop.NO_VIEWPORT})
        self.assertEqual(self.aim()["kind"], "none")

    def test_a_library_that_raises_still_aims_at_the_scene(self):
        self.silent()

        def broken():
            raise RuntimeError("no library")
        self.swap(self.lib, "live", broken)

        def scene_broken(x, y, snap, scale=1.0):
            raise RuntimeError("no scene")
        self.swap(self.drop, "character_target", scene_broken)
        self.assertEqual(self.aim(), {"kind": "none", "text": u"во вьюпорт или в библиотеку поз"})

    def test_drag_aim_of_a_card_asks_card_aim(self):
        item = look.Item("msg", "", {"id": "m", "file": dict(FILE, kind="pose", name="F.pose")})
        self.win._card_drag = {"item": item}
        self.swap(self.lib, "live", lambda: FakeLive("Fights"))
        self.assertEqual(self.win.drag_aim(QtCore.QPoint(1, 1))["kind"], "library")
        self.win._card_drag = None


class Later(Base):
    def test_one_idle_later_through_maya_and_at_once_without_it(self):
        import maya.utils
        queued = []
        self.swap(maya.utils, "executeDeferred", queued.append)
        ran = []
        self.win._later(lambda: ran.append(1))
        self.assertEqual((len(queued), ran), (1, []))
        queued[0]()
        self.assertEqual(ran, [1])
        self.swap_module("maya.utils", None)            # `import maya.utils` raises ImportError
        self.win._later(lambda: ran.append(2))
        self.assertEqual(ran, [1, 2])


# ---------------------------------------------------------------------------- the panes' buttons

class Buttons(Base):
    def button(self, name):
        return self.win.root.findChild(QtWidgets.QAbstractButton, name)

    def test_new_back_and_the_list_back(self):
        self.button("skeldarChatNew").click()
        self.assertEqual(self.win.pane, "new")
        self.assertIn(("read_people",), self.ses.calls)
        self.button("skeldarChatNewPaneBack").click()
        self.assertEqual(self.win.pane, "chat")
        self.win.open_chat("dm")
        self.win.chat_back.click()
        self.assertEqual(self.win.single, "list")

    def test_the_menu_button_opens_my_menu_and_its_rows_run(self):
        self.ses.api.person_files = lambda uid: {"user": dict(T.ME), "files": [], "more": False}
        self.win.menu_button.click()
        menu = self.win._menu
        rows = dict((a.text(), a) for a in menu.actions() if a.text())
        rows[u"Новый чат или группа"].trigger()
        self.assertEqual(self.win.pane, "new")
        rows[u"Мой профиль"].trigger()
        self.assertIsNotNone(self.win.profile)
        self.assertEqual(self.win.profile.user["id"], "me")
        self.assertFalse(self.win.profile.write.isVisibleTo(self.win.root), "no Написать to me")
        menu.close()
        self.win.profile.close()

    def test_the_composer_s_buttons(self):
        self.win.open_chat("dm")
        self.win.composer.setPlainText("by button")
        self.win.send_button.click()
        self.assertEqual(self.ses.calls[-1], ("send", "dm", "by button", None))
        self.win.emoji_button.click()
        self.assertTrue(self.win._picker.isVisible())
        self.win._picker.close()
        self.win.start_reply(self.ses.state.messages["dm"][0])
        self.button("skeldarChatBarCancel").click()
        self.assertIsNone(self.win.reply_to)
        self.win.unseen = 4
        self.win.down.click()
        self.assertEqual(self.win.unseen, 0)

    def test_the_settings_buttons(self):
        self.win.show_pane("settings")
        self.ses.api.rename = lambda name: dict(T.ME, name=name)
        self.win.name_field.setText("New Me")
        self.button("skeldarChatNameSave").click()
        self.assertEqual(self.win.settings_line.text(), u"Сохранено")
        self.assertEqual(self.ses.state.me["name"], "New Me")
        self.win.code_show.click()
        self.assertEqual(self.win.code_text.text(), "secret-token")
        self.win.code_show.click()
        self.assertEqual(self.win.code_text.text(), u"••••••••")
        self.button("skeldarChatCodeCopy").click()
        self.assertEqual(QtWidgets.QApplication.clipboard().text(), "secret-token")
        self.assertEqual(self.win.settings_line.text(), u"Код скопирован")
        self.win.notify_box.setChecked(not notify.option("viewport"))
        self.assertEqual(notify.option("viewport"), self.win.notify_box.isChecked())
        self.win.sound_box.setChecked(not notify.option("sound"))
        self.assertEqual(notify.option("sound"), self.win.sound_box.isChecked())

    def test_a_refused_rename_is_said(self):
        self.win.show_pane("settings")

        def refuse(name):
            raise A.ChatError("bad_name", "too long")
        self.ses.api.rename = refuse
        self.win.rename_me()
        self.assertEqual(self.win.settings_line.text(), "too long")

    def test_a_notify_option_that_fails_does_not_break(self):
        self.silent()
        self.swap(notify, "set_option", lambda what, on: 1 / 0)
        self.win._set_notify("viewport", True)          # said in the Script Editor only

    def test_choose_avatar_asks_for_a_picture(self):
        picked = []
        self.win.set_avatar_from = picked.append
        with mock.patch.object(QtWidgets.QFileDialog, "getOpenFileName",
                               return_value=("C:/x/me.png", "")):
            self.button("skeldarChatAvatarChoose").click()
        with mock.patch.object(QtWidgets.QFileDialog, "getOpenFileName", return_value=("", "")):
            self.win.choose_avatar()
        self.assertEqual(picked, ["C:/x/me.png"])

    def test_a_picture_that_cannot_be_uploaded_says_why(self):
        def refuse(data):
            raise A.ChatError("too_big", "too big")
        self.ses.set_avatar = refuse
        dir_ = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, dir_, True)
        path = os.path.join(dir_, "a.png")
        QtGui.QImage(10, 10, QtGui.QImage.Format_RGB32).save(path)
        self.assertIsNone(self.win.set_avatar_from(path))
        self.assertEqual(self.win.settings_line.text(), "too big")

    def test_sign_out_by_its_button(self):
        self.win.show_pane("settings")
        self.button("skeldarChatSignOut").click()
        self.assertEqual(self.win.pages.currentWidget().objectName(), "skeldarChatSignIn")


class SignInButtons(Swaps, unittest.TestCase):
    def setUp(self):
        T._app()
        W._VARS.clear()
        self.ses = T.FakeSession(signed=False)
        self.win = W.ChatWindow(self.ses, scale=1.0)
        self.win.root.resize(760, 520)
        self.win.root.show()

    def tearDown(self):
        self.win.destroy()
        QtWidgets.QApplication.processEvents()

    def test_the_go_button_and_the_code_road(self):
        self.win.nick_field.setText("anna")
        self.win.signin_go.click()
        self.assertEqual(self.ses.calls, [("sign_in", "anna")])

    def test_the_code_field_toggles_and_its_enter_signs_in(self):
        self.assertFalse(self.win.code_field.isVisible())
        self.win.code_toggle.click()
        self.assertTrue(self.win.code_field.isVisible())
        self.win.code_field.setText("skc_code")
        self.win.code_field.returnPressed.emit()
        self.assertEqual(self.ses.calls, [("code", "skc_code")])
        self.assertEqual(self.win.code_field.text(), "")
        self.win.code_toggle.click()
        self.assertFalse(self.win.code_field.isVisible())

    def test_a_bad_code_is_said(self):
        def refuse(code):
            raise A.ChatError("bad_code", "no such code")
        self.ses.sign_in_code = refuse
        self.win.code_field.setText("x")
        self.assertFalse(self.win.sign_in_code())
        self.assertEqual(self.win.signin_line.text(), "no such code")

    def test_a_nick_with_a_bad_format_is_said_on_the_press(self):
        self.win.nick_field.setText("x")
        self.assertFalse(self.win.sign_in())
        self.assertTrue(self.win.signin_line.text())
        self.assertEqual(self.ses.calls, [])


class Members(Base):
    def setUp(self):
        Base.setUp(self)
        self.ses.read_people()
        self.ses.state.chats["g1"] = group_chat()
        self.ses.state.messages["g1"] = []
        self.win.open_chat("g1")
        self.win.show_pane("members")

    def rows(self):
        out = []
        for i in range(self.win.members_rows.count()):
            w = self.win.members_rows.itemAt(i).widget()
            if w is None:
                continue
            labels = [label.text() for label in w.findChildren(QtWidgets.QLabel)]
            buttons = dict((b.text(), b) for b in w.findChildren(QtWidgets.QPushButton))
            out.append((" ".join(labels) or (w.text() if hasattr(w, "text") else ""), buttons))
        return out

    def test_the_admin_removes_others_leaves_himself_and_adds_people(self):
        rows = self.rows()
        names = [text for text, _b in rows]
        self.assertTrue(any("Bob" in n for n in names))
        self.assertIn(u"Добавить", names, "the heading over those not in the group")
        bob = next(b for text, b in rows if "@bob" in text)
        me = next(b for text, b in rows if "@me" in text)
        carl = next(b for text, b in rows if "@carl" in text)
        self.assertIn(u"Удалить", bob)
        self.assertIn(u"Выйти", me)
        bob[u"Удалить"].click()
        carl[u"Добавить"].click()
        me[u"Выйти"].click()
        api = [c for c in self.ses.api.calls if c[0] in ("remove_member", "add_member")]
        self.assertEqual(api, [("remove_member", "g1", "bob"), ("add_member", "g1", "carl"),
                               ("remove_member", "g1", "me")])
        self.assertTrue(self.win.chat_rename.isEnabled())

    def test_the_rename_button(self):
        self.win.chat_name_field.setText("Fights")
        self.win.chat_rename.click()
        self.assertIn(("rename_chat", "g1", "Fights"), self.ses.api.calls)

    def test_a_refused_member_change_is_said(self):
        def refuse(*a):
            raise A.ChatError("not_admin", "only the admin")
        self.ses.api.add_member = refuse
        self.win.add_member("carl")
        self.assertEqual(self.win.members_line.text(), "only the admin")

    def test_not_the_admin_can_only_leave(self):
        self.ses.state.chats["g1"]["admin"] = "bob"
        self.win.refresh()
        rows = self.rows()
        self.assertFalse(self.win.chat_rename.isEnabled())
        bob = next(b for text, b in rows if "@bob" in text)
        self.assertEqual(bob, {})
        self.assertNotIn(u"Добавить", [text for text, _b in rows])

    def test_an_offline_member_s_tooltip_says_when(self):
        self.ses.state.people[1]["last_seen"] = T.NOW - 3600 * 1000
        row = self.win._person_row(dict(CARL, online=False, last_seen=T.NOW - 3600 * 1000), [])
        label = row.findChildren(QtWidgets.QLabel)[0]
        self.assertTrue(label.toolTip())


class NewPane(Base):
    def setUp(self):
        Base.setUp(self)
        self.win.show_pane("new")

    def test_a_tick_picks_and_write_opens_the_dm(self):
        boxes = self.win.new_body.findChildren(QtWidgets.QCheckBox)
        box = next(b for b in boxes if "@carl" in b.text())
        box.setChecked(True)
        self.assertEqual(self.win.picked, {"carl"})
        box.setChecked(False)
        self.assertEqual(self.win.picked, set())
        row = box.parentWidget()
        write = next(b for b in row.findChildren(QtWidgets.QPushButton) if b.text() == u"Написать")
        write.click()
        self.assertIn(("open_dm", "carl"), self.ses.calls)
        self.assertEqual(self.win.chat, "dm")

    def test_nobody_found_says_so(self):
        self.win.new_search.setText("zzzz")
        labels = [w.text() for w in self.win.new_body.findChildren(QtWidgets.QLabel)]
        self.assertIn(u"Никого не нашли", labels)

    def test_the_make_button_makes_a_group_and_opens_it(self):
        self.ses.state.chats["g1"] = group_chat()
        self.ses.state.messages["g1"] = []
        self.win.group_name.setText("Team")
        self.win.picked = {"carl"}
        self.win.root.findChild(QtWidgets.QAbstractButton, "skeldarChatGroupMake").click()
        self.assertIn(("group", "Team", ["carl"]), self.ses.api.calls)
        self.assertEqual(self.win.chat, "g1")
        self.assertEqual(self.win.group_name.text(), "")

    def test_a_refused_dm_is_said_on_the_new_pane(self):
        def refuse(uid):
            raise A.ChatError("blocked", "cannot write")
        self.ses.open_dm = refuse
        self.win.write_to("carl")
        self.assertEqual(self.win.new_line.text(), "cannot write")


# ---------------------------------------------------------------------------- scroll and history

class Scroll(Base):
    def setUp(self):
        Base.setUp(self)
        self.ses.state.messages["dm"] = [T.msg("h%02d" % i, i, frm="bob" if i % 2 else "me",
                                               text="line %d " % i * 6) for i in range(1, 60)]
        self.win.root.resize(760, 420)
        self.win.open_chat("dm")
        QtWidgets.QApplication.processEvents()
        self.bar = self.win.feed_area.verticalScrollBar()

    def test_the_distance_from_the_bottom_is_kept(self):
        self.assertGreater(self.bar.maximum(), 0)
        self.bar.setValue(self.bar.maximum() - 40)
        self.assertEqual(self.win._distance_from_bottom(), 40)
        self.win._keep_distance(40)
        self.assertEqual(self.bar.maximum() - self.bar.value(), 40)
        self.assertEqual(self.win._pending_scroll, ("keep", 40))
        self.win._range_changed(0, self.bar.maximum())
        self.assertEqual(self.bar.maximum() - self.bar.value(), 40)

    def test_history_at_the_top_and_its_end(self):
        came = [5]
        self.ses.load_history = lambda chat: (self.ses.calls.append(("history", chat)),
                                              came.pop() if came else 0)[1]
        self.assertEqual(self.win.load_history(), 5)
        self.assertNotIn("dm", self.win.history_done)
        self.bar.setValue(0)
        self.assertIn("dm", self.win.history_done, "a top with nothing more marks it done")
        calls = len([c for c in self.ses.calls if c[0] == "history"])
        self.win._scrolled(0)
        self.assertEqual(len([c for c in self.ses.calls if c[0] == "history"]), calls)

    def test_a_failed_history_read_is_said(self):
        def refuse(chat):
            raise A.ChatError("offline", "no answer")
        self.ses.load_history = refuse
        self.assertEqual(self.win.load_history(), 0)
        self.assertEqual(self.win.line.text(), "no answer")

    def test_scroll_to_a_message_and_one_older_than_the_history(self):
        self.assertFalse(self.win.scroll_to_message("nope"))
        self.assertIn(u"старше", self.win.line.text())
        self.assertTrue(self.win.scroll_to_message("h05"))
        self.assertIn(self.box("h05").item.key(), self.win.feed.flashing)
        self.assertLess(self.bar.value(), self.bar.maximum())

    def test_scrolled_up_shows_the_down_button_with_the_count(self):
        self.bar.setValue(0)
        self.win.unseen = 3
        self.win._paint_down()
        self.assertTrue(self.win.down.isVisibleTo(self.win.root))
        self.assertEqual(self.win.down.text(), look.count_text(3))
        new = T.msg("h99", 99, text="new")
        self.ses.state.messages["dm"].append(new)
        self.win._heard("message", {"message": new})
        self.assertEqual(self.win.unseen, 4)

    def test_the_resize_filter_lays_out_and_reads(self):
        flt = self.win._watch
        calls = []
        self.win.resized = lambda: calls.append("resized")
        self.win._read_if_seen = lambda: calls.append("read")
        self.assertFalse(flt.eventFilter(self.win.root, QtGui.QResizeEvent(
            QtCore.QSize(10, 10), QtCore.QSize(5, 5))))
        self.assertFalse(flt.eventFilter(self.win.root, QtCore.QEvent(QtCore.QEvent.Show)))
        self.assertEqual(calls, ["resized", "read"])


# ---------------------------------------------------------------------------- each second

class FakeCache(object):
    def __init__(self, changed=True):
        self.changed = changed

    def take_changed(self):
        changed, self.changed = self.changed, False
        return changed


class EachSecond(Base):
    def test_typing_and_pending_refresh_and_fresh_pictures_repaint(self):
        refreshed = []
        real = self.win.refresh
        self.win.refresh = lambda: (refreshed.append(1), real())
        self.ses.state.typing = {"dm": {"bob": time.monotonic()}}
        self.win.avatars = FakeCache()
        self.win.feed.anim = FakeCache()
        self.win._each_second()
        self.assertEqual(refreshed, [1])
        self.assertFalse(self.win.avatars.changed)
        self.assertFalse(self.win.feed.anim.changed)
        self.ses.state.typing = {"dm": {"bob": time.monotonic() - 3600}}
        self.win._each_second()
        self.assertEqual(refreshed, [1], "an old typing mark refreshes nothing")
        self.ses.state.pending["dm"] = [{"cid": "x"}]
        self.win._each_second()
        self.assertEqual(refreshed, [1, 1])

    def test_a_hidden_window_does_nothing(self):
        self.win.root.hide()
        self.win.refresh = lambda: self.fail("hidden: no refresh")
        self.ses.state.pending["dm"] = [{"cid": "x"}]
        self.win._each_second()


# ---------------------------------------------------------------------------- place, burst

class PlaceAndBurst(Base):
    def test_the_title_drags_the_window_and_the_drop_remembers_it(self):
        self.win.root.move(100, 100)
        self.win._grab((110, 105))
        self.win._drag((310, 205))
        self.assertEqual((self.win.root.x(), self.win.root.y()), (300, 200))
        self.win._drop()
        self.assertEqual(W.get_var(W.POS_VAR), "300,200")

    def test_show_and_close_without_a_point_are_at_once(self):
        done = []
        self.assertFalse(self.win.show_at(None))
        self.assertTrue(self.win.root.isVisible())
        self.assertFalse(self.win.close_into(None, lambda: done.append(1)))
        self.assertFalse(self.win.root.isVisible())
        self.assertEqual(done, [1])

    def drive(self):
        burster = self.win.burster
        self.assertIsNotNone(burster.anim)
        burster._tick(10 ** 6)
        self.assertIsNone(burster.anim, "the burst ended")

    def test_a_burst_out_of_a_point_and_a_fold_into_one(self):
        self.swap(maya_hubburst, "MOTION", "burst")
        self.win.root.hide()
        with mock.patch.object(hubmotion, "enabled", return_value=True):
            self.assertTrue(self.win.show_at((400, 300)))
            self.assertTrue(self.win.root.testAttribute(QtCore.Qt.WA_TransparentForMouseEvents))
            self.drive()
            self.assertFalse(self.win.root.testAttribute(QtCore.Qt.WA_TransparentForMouseEvents))
            done = []
            self.assertTrue(self.win.close_into((400, 300), lambda: done.append(1)))
            self.drive()
        self.assertEqual(done, [1])
        self.assertFalse(self.win.root.isVisible())
        self.assertEqual(self.win._burst_face(), W.hubstyle.TOKENS["card"])
        self.assertTrue(self.win._burst_parts())

    def test_a_burst_that_cannot_start_shows_at_once(self):
        self.silent()

        def broken(*a, **k):
            raise RuntimeError("no effect")
        self.win.burster.run = broken
        with mock.patch.object(hubmotion, "enabled", return_value=True):
            self.assertFalse(self.win.show_at((400, 300)))
        self.assertFalse(self.win.root.testAttribute(QtCore.Qt.WA_TransparentForMouseEvents))

    def test_destroy_closes_a_standing_profile(self):
        closed = []

        class Card(object):
            def close(self):
                closed.append(1)
        self.win.profile = Card()
        self.win.destroy()
        self.assertEqual(closed, [1])
        self.win.refresh()                               # gone: nothing


# ---------------------------------------------------------------------------- one window a Maya

class FakeHeldSession(T.FakeSession):
    pass


class OneWindow(Swaps, unittest.TestCase):
    def setUp(self):
        T._app()
        W._VARS.clear()
        notify._VARS.clear()
        self.ses = FakeHeldSession()
        self.swap(sys, "_skeldar_chat_window", {"win": None})
        self.swap(sys, "_skeldar_chat", self.ses)
        import maya_hub
        self.rail = []
        self.swap(maya_hub, "paint_floating", lambda key, on: self.rail.append((key, on)))

    def tearDown(self):
        W.destroy()
        QtWidgets.QApplication.processEvents()

    def test_show_makes_it_once_and_a_second_show_flashes_it(self):
        self.assertIsNone(W.window())
        self.assertFalse(W.is_open())
        win = W.show(session=self.ses)
        self.assertIs(W.window(), win)
        self.assertTrue(W.is_open())
        self.assertEqual(self.rail, [("chat", True)])
        again = W.show()
        self.assertIs(again, win)
        self.assertEqual(win.frame.flash, 1.0)

    def test_show_without_a_session_takes_this_maya_s(self):
        win = W.show()
        self.assertIs(win.session, self.ses)

    def test_toggle_closes_then_opens(self):
        W.show(session=self.ses)
        self.assertTrue(W.toggle())
        self.assertFalse(W.is_open())
        self.assertEqual(self.rail[-1], ("chat", False))
        self.assertFalse(W.close_window(), "shut already")
        self.assertTrue(W.toggle(session=self.ses))
        self.assertTrue(W.is_open())

    def test_a_card_or_a_file_needs_an_open_chat(self):
        self.assertIn(u"Откройте чат", W.send_card("C:/lib/Fist.pose"))
        self.assertIn(u"Откройте чат", W.send_path("C:/x/Run.ma"))
        win = W.show(session=self.ses)
        win.open_chat("dm")
        self.swap(files, "send_card", lambda ses, chat, card, caption="": "cid")
        self.swap(files, "send_path", lambda ses, chat, path, caption="": "cid")
        self.assertEqual(W.send_card("C:/lib/Fist.pose/"), u"Fist.pose - в чат")
        self.assertEqual(W.send_path("C:/x/Run.ma"), u"Run.ma - в чат")

        def refuse(ses, chat, path, caption=""):
            raise A.ChatError("bad_file", "not a scene")
        self.swap(files, "send_path", refuse)
        self.assertEqual(W.send_path("C:/x/Run.ma"), "not a scene")

    def test_destroy_takes_every_window_of_ours(self):
        win = W.show(session=self.ses)
        W.destroy()
        self.assertIsNone(W.window())
        self.assertIsNone(win.root)

    def test_a_dead_root_is_no_window(self):
        win = W.show(session=self.ses)
        win.root = None
        self.assertIsNone(W.window())

    def test_the_rail_is_told_quietly_when_the_hub_raises(self):
        import maya_hub
        self.swap(maya_hub, "paint_floating", lambda key, on: 1 / 0)
        W._paint_rail(True)                              # nothing raises


class Helpers(unittest.TestCase):
    def test_clamp_into_and_on(self):
        self.assertEqual(W.clamp_into(5, 5, 10, 10, None), (5, 5))
        self.assertEqual(W.clamp_into(95, -5, 10, 10, (0, 0, 100, 100)), (90, 0))
        self.assertTrue(W._on((0, 0, 10, 10), (5, 5)))
        self.assertFalse(W._on((0, 0, 10, 10), (10, 5)))

    def test_pair_and_back_out(self):
        self.assertEqual(W._pair("3,4"), (3, 4))
        self.assertIsNone(W._pair("x"))
        self.assertEqual(W.back_out(1.0), 1.0)
        self.assertAlmostEqual(W.back_out(-1), 0.0)

    def test_a_menu_icon_only_for_known_rows(self):
        T._app()
        menu = QtWidgets.QMenu()
        known = menu.addAction(u"Удалить")
        unknown = menu.addAction("Whatever")
        W._menu_icon(known, u"Удалить", 1.0)
        W._menu_icon(unknown, "Whatever", 1.0)
        self.assertFalse(known.icon().isNull())
        self.assertTrue(unknown.icon().isNull())
        menu.deleteLater()


if __name__ == "__main__":
    unittest.main()
