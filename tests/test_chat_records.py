"""maya_chat.records: what the server sends, parsed strictly."""
import subprocess
import sys
import unittest

from maya_chat import records as r

USER = {"id": "a1", "nick": "anna", "name": "Anna", "avatar_v": 0}
MSG = {"id": "m1", "chat": "c1", "seq": 1, "from_id": "a1", "cid": "x", "text": "hi",
       "reply_to": None, "at": 10, "edited_at": None, "deleted": False}
CHAT = {"id": "c1", "kind": "dm", "name": "", "admin": None, "avatar_v": 0,
        "members": [dict(USER, online=True, last_seen=0, joined=5)], "last": MSG, "unread": 1,
        "read_upto": 0}


class Nick(unittest.TestCase):
    def test_folds_and_refuses(self):
        self.assertEqual(r.nick(" @Anna_1 "), "anna_1")
        for bad in ("ab", "a" * 25, "anna smith", "аня", "", None):
            self.assertIsNone(r.nick(bad), bad)


class Shapes(unittest.TestCase):
    def test_user_message_chat(self):
        self.assertEqual(r.user(USER)["nick"], "anna")
        self.assertEqual(r.message(MSG)["text"], "hi")
        c = r.chat(CHAT)
        self.assertEqual(c["members"][0]["online"], True)
        self.assertEqual(c["last"]["id"], "m1")
        self.assertEqual(c["unread"], 1)

    def test_wrong_types_are_refused(self):
        with self.assertRaises(r.Bad):
            r.message(dict(MSG, seq="1"))
        with self.assertRaises(r.Bad):
            r.user(dict(USER, id=""))
        with self.assertRaises(r.Bad):
            r.chat(dict(CHAT, kind="channel"))
        with self.assertRaises(r.Bad):
            r.message(dict(MSG, seq=True))


class Events(unittest.TestCase):
    def test_a_message_event(self):
        e = r.event({"seq": 7, "kind": "message", "message": MSG})
        self.assertEqual((e["seq"], e["message"]["id"]), (7, "m1"))

    def test_malformed_and_unknown_are_none(self):
        self.assertIsNone(r.event({"kind": "message", "seq": 1}))
        self.assertIsNone(r.event({"kind": "message", "message": MSG}))  # no seq
        self.assertIsNone(r.event({"kind": "launch", "seq": 1}))
        self.assertIsNone(r.event("pong"))
        self.assertIsNone(r.event({"kind": "ack", "cid": "x"}))

    def test_live_kinds_need_no_seq(self):
        self.assertEqual(r.event({"kind": "typing", "chat_id": "c", "user_id": "u"})["kind"], "typing")
        p = r.event({"kind": "presence", "user_id": "u", "online": False, "last_seen": 9})
        self.assertEqual((p["online"], p["last_seen"]), (False, 9))
        self.assertEqual(r.event({"kind": "caught_up", "seq": 4})["seq"], 4)
        self.assertEqual(r.event({"kind": "resync"}), {"kind": "resync"})
        err = r.event({"kind": "error", "cid": None, "code": "too_long", "text": "t"})
        self.assertEqual(err["code"], "too_long")

    def test_each_seq_kind(self):
        rows = [
            {"kind": "edited", "chat_id": "c", "id": "m", "text": "t", "edited_at": 3},
            {"kind": "deleted", "chat_id": "c", "id": "m"},
            {"kind": "read", "chat_id": "c", "user_id": "u", "upto": 2},
            {"kind": "chat", "chat": dict(CHAT)},
            {"kind": "member_added", "chat_id": "c", "user": USER},
            {"kind": "member_removed", "chat_id": "c", "user_id": "u", "admin": None},
            {"kind": "friend_request", "user": USER},
            {"kind": "request_sent", "user": USER},
            {"kind": "friend_added", "user": USER},
            {"kind": "friend_removed", "user_id": "u"},
            {"kind": "request_cancelled", "from_id": "a", "to_id": "b"},
            {"kind": "user", "user": USER},
        ]
        for row in rows:
            self.assertIsNotNone(r.event(dict(row, seq=1)), row["kind"])


class Merge(unittest.TestCase):
    def test_order_and_replace(self):
        a = r.message(dict(MSG, id="a", seq=2))
        b = r.message(dict(MSG, id="b", seq=1))
        edited = dict(a, text="changed")
        out = r.merge([a, b], [edited])
        self.assertEqual([m["id"] for m in out], ["b", "a"])
        self.assertEqual(out[1]["text"], "changed")

    def test_unread_skips_mine_and_deleted(self):
        msgs = [r.message(dict(MSG, id="1", seq=1, from_id="me")),
                r.message(dict(MSG, id="2", seq=2, from_id="b")),
                r.message(dict(MSG, id="3", seq=3, from_id="b", deleted=True)),
                r.message(dict(MSG, id="4", seq=4, from_id="b"))]
        self.assertEqual(r.unread({"read_upto": 2}, msgs, "me"), 1)
        self.assertEqual(r.unread({"read_upto": 0}, msgs, "me"), 2)


class Runs(unittest.TestCase):
    def test_links(self):
        self.assertEqual(r.runs("see https://a.b/c, ok"),
                         [("text", "see "), ("link", "https://a.b/c"), ("text", ", ok")])
        self.assertEqual(r.runs("(http://x.y)"), [("text", "("), ("link", "http://x.y"), ("text", ")")])
        self.assertEqual(r.runs("plain"), [("text", "plain")])
        self.assertEqual(r.runs(""), [])


class Pure(unittest.TestCase):
    def test_imports_nothing_of_maya_or_qt(self):
        code = ("import sys; sys.path.insert(0, 'SkeldarAnim'); "
                "import maya_chat.records, maya_chat.api, maya_chat.store; "
                "print(any(m.split('.')[0] in ('maya', 'PySide6', 'shiboken6') for m in sys.modules))")
        out = subprocess.check_output([sys.executable, "-c", code]).decode().strip()
        self.assertEqual(out, "False")


if __name__ == "__main__":
    unittest.main()
