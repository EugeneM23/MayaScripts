"""maya_chat.look: the window's pure rules."""
import os
import subprocess
import sys
import time
import unittest

from maya_chat import look

ME = {"id": "me", "nick": "me", "name": "Me Myself"}
BOB = {"id": "bob", "nick": "bob", "name": ""}
ANN = {"id": "ann", "nick": "ann", "name": "Ann"}


def at(y, mo, d, h=12, mi=0):
    return int(time.mktime((y, mo, d, h, mi, 0, 0, 0, -1)) * 1000)


NOW = at(2026, 10, 20, 15, 0)


def m(id, seq, frm="bob", t=None, text="hi", deleted=False):
    return {"id": id, "chat": "dm", "seq": seq, "from_id": frm, "cid": id, "text": text,
            "reply_to": None, "at": t if t is not None else NOW, "edited_at": None,
            "deleted": deleted}


def dm(last=None, unread=0):
    return {"id": "dm", "kind": "dm", "name": "", "members": [ME, BOB], "last": last,
            "unread": unread}


def group(last=None):
    return {"id": "g", "kind": "group", "name": "Анимация", "members": [ME, BOB, ANN],
            "last": last, "unread": 0}


class Names(unittest.TestCase):

    def test_initials_from_the_name_else_the_nick(self):
        self.assertEqual(look.initials(ME), "MM")
        self.assertEqual(look.initials(ANN), "AN")
        self.assertEqual(look.initials(BOB), "BO")

    def test_a_user_keeps_their_colour(self):
        self.assertEqual(look.user_colour("bob"), look.user_colour("bob"))
        self.assertIn(look.user_colour("bob"), look.COLOURS)

    def test_a_display_name_falls_back_to_the_nick(self):
        self.assertEqual(look.display_name(BOB), "@bob")
        self.assertEqual(look.display_name(ANN), "Ann")

    def test_a_dm_is_titled_by_the_other_member_a_group_by_its_name(self):
        self.assertEqual(look.chat_title(dm(), "me"), "@bob")
        self.assertEqual(look.chat_title(group(), "me"), "Анимация")


class Times(unittest.TestCase):

    def test_clock(self):
        self.assertEqual(look.clock(at(2026, 10, 20, 9, 5), NOW), "09:05")
        self.assertEqual(look.clock(at(2026, 10, 19, 9, 5), NOW), "вчера")
        self.assertEqual(look.clock(at(2026, 3, 2), NOW), "02.03")
        self.assertEqual(look.clock(at(2025, 3, 2), NOW), "02.03.25")
        self.assertEqual(look.clock(0, NOW), "")

    def test_day_labels(self):
        self.assertEqual(look.day_label(at(2026, 10, 20), NOW), "Сегодня")
        self.assertEqual(look.day_label(at(2026, 10, 19), NOW), "Вчера")
        self.assertEqual(look.day_label(at(2026, 10, 12), NOW), "12 октября")
        self.assertEqual(look.day_label(at(2025, 1, 3), NOW), "3 января 2025")

    def test_last_seen(self):
        self.assertEqual(look.last_seen(at(2026, 10, 20, 14, 32), NOW), "был(а) в 14:32")
        self.assertEqual(look.last_seen(at(2026, 10, 19, 8, 0), NOW), "был(а) вчера в 08:00")


class Presence(unittest.TestCase):

    def test_a_dm_says_online_typing_or_last_seen(self):
        c = dm()
        self.assertEqual(look.presence(c, "me", {"bob": {"online": True}}, {}, 10.0, NOW), "в сети")
        self.assertEqual(look.presence(c, "me", {"bob": {"online": True}}, {"dm": {"bob": 9.0}},
                                       10.0, NOW), "печатает…")
        self.assertEqual(look.presence(c, "me", {"bob": {"online": True}}, {"dm": {"bob": 1.0}},
                                       10.0, NOW), "в сети")
        self.assertEqual(look.presence(c, "me", {"bob": {"online": False,
                                                         "last_seen": at(2026, 10, 20, 14, 32)}},
                                       {}, 10.0, NOW), "был(а) в 14:32")

    def test_a_group_counts_who_is_online_and_names_a_typer(self):
        c = group()
        self.assertEqual(look.presence(c, "me", {"bob": {"online": True}, "me": {"online": True}},
                                       {}, 10.0, NOW), "3 участников, 2 в сети")
        self.assertEqual(look.presence(c, "me", {}, {"g": {"ann": 9.5}}, 10.0, NOW),
                         "Ann печатает…")

    def test_the_title_status(self):
        self.assertEqual(look.status_title("online"), "в сети")
        self.assertIn("offline", look.status_title("offline"))


class Rows(unittest.TestCase):

    def test_preview(self):
        self.assertEqual(look.preview(dm(m("a", 1, text="hey\nthere")), "me", {}, 0), "hey there")
        self.assertEqual(look.preview(dm(m("a", 1, frm="me")), "me", {}, 0), "Вы: hi")
        self.assertEqual(look.preview(dm(m("a", 1, deleted=True)), "me", {}, 0),
                         "сообщение удалено")
        self.assertEqual(look.preview(group(m("a", 1, frm="ann")), "me", {}, 0), "Ann: hi")
        self.assertEqual(look.preview(dm(), "me", {}, 0), "нет сообщений")
        self.assertEqual(look.preview(dm(m("a", 1)), "me", {"dm": {"bob": 4.0}}, 5.0), "печатает…")

    def test_ordered_newest_first(self):
        old, new, none = dict(dm(m("a", 1, t=5)), id="x"), dict(dm(m("b", 2, t=9)), id="y"), \
            dict(dm(), id="z")
        self.assertEqual([c["id"] for c in look.ordered([old, none, new])], ["y", "x", "z"])

    def test_search_over_titles_nicks_and_names(self):
        self.assertTrue(look.matches(dm(), "BO", "me"))
        self.assertTrue(look.matches(dm(), "@bob", "me"))
        self.assertTrue(look.matches(group(), "ann", "me"))
        self.assertTrue(look.matches(group(), "аним", "me"))
        self.assertFalse(look.matches(dm(), "me myself", "me"))
        self.assertTrue(look.matches(dm(), "", "me"))

    def test_counts_and_nicks_and_columns(self):
        self.assertEqual(look.count_text(7), "7")
        self.assertEqual(look.count_text(140), "99+")
        self.assertIsNone(look.nick_problem("good_nick"))
        self.assertIsNotNone(look.nick_problem("x"))
        self.assertTrue(look.one_column(599))
        self.assertFalse(look.one_column(600))
        self.assertTrue(look.one_column(800, scale=1.5))
        self.assertEqual(look.total_unread([dm(unread=2), group()]), 2)


class Feed(unittest.TestCase):

    def test_days_runs_and_deleted(self):
        msgs = [m("a", 1, t=at(2026, 10, 19, 10)), m("b", 2, t=at(2026, 10, 20, 9, 0)),
                m("c", 3, t=at(2026, 10, 20, 9, 3)), m("d", 4, frm="me", t=at(2026, 10, 20, 9, 4)),
                m("e", 5, t=at(2026, 10, 20, 9, 40)), m("f", 6, deleted=True)]
        items = look.feed(msgs, [], "me", dm(), {}, NOW)
        self.assertEqual([i.kind for i in items], ["day", "msg", "day", "msg", "msg", "msg", "msg"])
        self.assertEqual(items[0].text, "Вчера")
        self.assertEqual(items[2].text, "Сегодня")
        b, c, d, e = items[3:]
        self.assertTrue(b.first and not b.last)
        self.assertTrue(not c.first and c.last)
        self.assertTrue(d.mine and d.first and d.last)
        self.assertTrue(e.first, "40 minutes later is a new run")

    def test_ticks_sent_read_clock_and_failed(self):
        mine = [m("a", 1, frm="me"), m("b", 2, frm="me")]
        pending = [{"cid": "p", "chat": "dm", "text": "x", "at": NOW, "from_id": "me",
                    "state": "sending"},
                   {"cid": "q", "chat": "dm", "text": "y", "at": NOW, "from_id": "me",
                    "state": "failed"},
                   {"cid": "r", "chat": "dm", "text": "z", "at": NOW - look.UNSENT_MS - 1,
                    "from_id": "me", "state": "sending"}]
        items = [i for i in look.feed(mine, pending, "me", dm(), {"dm": {"bob": 1}}, NOW)
                 if i.kind == "msg"]
        self.assertEqual([i.tick for i in items], ["read", "sent", "clock", "failed", "failed"])
        self.assertTrue(items[2].pending)
        self.assertEqual(items[2].key(), "p")

    def test_others_have_no_tick(self):
        items = look.feed([m("a", 1)], [], "me", dm(), {}, NOW)
        self.assertEqual(items[-1].tick, "")
        self.assertFalse(items[-1].mine)

    def test_last_mine_and_find(self):
        msgs = [m("a", 1, frm="me"), m("b", 2), m("c", 3, frm="me", deleted=True)]
        self.assertEqual(look.last_mine(msgs, "me")["id"], "a")
        self.assertEqual(look.find(msgs, "b")["seq"], 2)
        self.assertIsNone(look.last_mine([], "me"))


class Pure(unittest.TestCase):

    def test_it_imports_no_maya_and_no_qt(self):
        here = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "SkeldarAnim")
        code = ("import sys; import maya_chat.look; "
                "bad = [n for n in sys.modules if n.split('.')[0] in ('maya', 'PySide6')]; "
                "print(bad); sys.exit(1 if bad else 0)")
        done = subprocess.run([sys.executable, "-c", code], cwd=here, capture_output=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


class People(unittest.TestCase):
    PEOPLE = [{"id": "z", "nick": "zed", "name": "Zed", "online": False, "last_seen": 1},
              {"id": "b", "nick": "bob", "name": "Bob", "online": False, "last_seen": 0},
              {"id": "a", "nick": "ann", "name": "Ann", "online": True, "last_seen": 0}]
    FRIENDS = {"friends": [{"id": "b"}], "incoming": [{"id": "z"}], "outgoing": []}

    def test_online_first_then_by_name(self):
        rows = look.people_rows(self.PEOPLE, self.FRIENDS, {})
        self.assertEqual([r["id"] for r in rows], ["a", "b", "z"])

    def test_live_presence_wins_over_the_list(self):
        rows = look.people_rows(self.PEOPLE, self.FRIENDS, {"z": {"online": True, "last_seen": 9}})
        self.assertEqual([r["id"] for r in rows], ["a", "z", "b"])
        self.assertEqual(look.people_count(rows), "2 в сети из 3")

    def test_relation_comes_from_the_friend_lists(self):
        rows = {r["id"]: r["relation"] for r in look.people_rows(self.PEOPLE, self.FRIENDS, {})}
        self.assertEqual(rows, {"a": None, "b": "friend", "z": "incoming"})

    def test_filter_by_name_or_nick(self):
        self.assertEqual([r["id"] for r in look.people_rows(self.PEOPLE, {}, {}, "@ze")], ["z"])
        self.assertEqual([r["id"] for r in look.people_rows(self.PEOPLE, {}, {}, "an")], ["a"])


class Toast(unittest.TestCase):
    def test_left_edge_passes_the_rail(self):
        area = (0, 100, 1000, 600)
        self.assertEqual(look.toast_left(area, [], 10), 10)
        self.assertEqual(look.toast_left(area, [(0, 100, 48, 600)], 10), 58)
        #  a rail card out on the right of the screen, or above the bottom half, is not in the way
        self.assertEqual(look.toast_left(area, [(900, 100, 48, 600)], 10), 10)
        self.assertEqual(look.toast_left(area, [(0, 100, 300, 200)], 10), 10)

    def test_cards_stack_up_from_the_bottom(self):
        area = (0, 100, 1000, 600)
        r0 = look.toast_rect(area, 10, (300, 56), 0, 10, 6)
        r1 = look.toast_rect(area, 10, (300, 56), 1, 10, 6)
        self.assertEqual(r0, (10, 634, 300, 56))
        self.assertEqual(r1[1], 634 - 62)

    def test_the_look_over_time(self):
        reveal, opacity, flash, slide = look.toast_look(0)
        self.assertEqual((reveal, opacity, slide), (0.0, 0.0, 0.0))
        self.assertEqual(flash, 1.0)
        reveal, opacity, flash, slide = look.toast_look(10000)
        self.assertEqual((reveal, opacity, flash), (1.0, 1.0, 0.0))
        _r, opacity, _f, slide = look.toast_look(10000, look.TOAST_OUT_MS)
        self.assertEqual(opacity, 0.0)
        self.assertGreater(slide, 0)

    def test_long_text_is_cut(self):
        self.assertTrue(look.toast_text("a " * 200).endswith("…"))
        self.assertEqual(look.toast_text("a\n b"), "a b")


if __name__ == "__main__":
    unittest.main()


class CallLine(unittest.TestCase):

    def msg(self, seq, call, frm="bob"):
        d = m("m%d" % seq, seq, frm=frm, t=NOW + seq, text="")
        d["call"] = call
        return d

    def test_a_call_note_is_its_own_item(self):
        items = look.feed([self.msg(1, {"id": "c", "kind": "audio", "answered": True, "seconds": 300})],
                          [], "me", dm(), {}, NOW)
        calls = [i for i in items if i.kind == "call"]
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].text, "Звонок · 5 мин")
        self.assertFalse(calls[0].missed)

    def test_a_missed_call(self):
        items = look.feed([self.msg(1, {"id": "c", "kind": "video", "answered": False, "seconds": 0})],
                          [], "me", dm(), {}, NOW)
        call = [i for i in items if i.kind == "call"][0]
        self.assertEqual(call.text, "Пропущенный звонок")
        self.assertTrue(call.missed)

    def test_a_call_breaks_a_run_of_one_sender(self):
        items = look.feed([m("a", 1, t=NOW), self.msg(2, {"id": "c", "kind": "audio",
                                                          "answered": False, "seconds": 0}),
                           m("b", 3, t=NOW + 2)], [], "me", dm(), {}, NOW)
        kinds = [i.kind for i in items]
        self.assertEqual(kinds, ["day", "msg", "call", "msg"])
        self.assertTrue(items[1].last and items[3].first)

    def test_the_preview_reads_the_call(self):
        self.assertEqual(look.message_text(self.msg(1, {"id": "c", "kind": "audio",
                                                        "answered": False, "seconds": 0})),
                         u"\U0001F4DE Пропущенный звонок")
