"""maya_chat.calls and the call records."""
import subprocess
import sys
import unittest

import tests  # noqa: F401

from maya_chat import calls, look, records

NOW = 1_800_000_000_000


def view(id="c1", chat="dm", by="a", state="ringing", members=("a",), declined=(), kind="video",
         started=NOW - 5000, answered=None, ended=None, cid="x1"):
    return {"id": id, "chat": chat, "by": by, "kind": kind, "cid": cid, "state": state,
            "members": list(members), "declined": list(declined), "started_at": started,
            "answered_at": answered, "ended_at": ended}


class Records(unittest.TestCase):
    def test_a_call_view(self):
        self.assertEqual(records.call(view()), view())

    def test_a_bad_call_is_bad(self):
        for bad in (dict(view(), state="paused"), dict(view(), kind="fax"), dict(view(), members="a"),
                    {k: v for k, v in view().items() if k != "chat"}):
            with self.assertRaises(records.Bad):
                records.call(bad)

    def test_the_events(self):
        e = records.event({"kind": "call", "seq": 7, "call": view()})
        self.assertEqual((e["kind"], e["seq"], e["call"]["id"]), ("call", 7, "c1"))
        s = records.event({"kind": "call_signal", "call": "c1", "from": "b", "data": {"sdp": "x"}})
        self.assertEqual((s["call"], s["from"], s["data"]), ("c1", "b", {"sdp": "x"}))
        self.assertIsNone(records.event({"kind": "call_signal", "call": "c1", "from": "b", "data": "x"}))
        self.assertIsNone(records.event({"kind": "call", "call": view()}))

    def test_a_message_keeps_its_call_note(self):
        m = records.message({"id": "m", "chat": "dm", "seq": 3, "from_id": "a", "cid": "call:c1", "text": "",
                             "reply_to": None, "at": NOW, "edited_at": None, "deleted": False,
                             "call": {"id": "c1", "kind": "audio", "answered": True, "seconds": 75}})
        self.assertEqual(m["call"], {"id": "c1", "kind": "audio", "answered": True, "seconds": 75})
        self.assertIsNone(records.call_note({"id": "c1"}))
        self.assertIsNone(records.call_note(None))


class Rules(unittest.TestCase):
    def test_merge_and_of_chat(self):
        by_id = calls.merge({}, view())
        self.assertEqual(calls.of_chat(by_id, "dm")["id"], "c1")
        by_id = calls.merge(by_id, view(state="ended", ended=NOW))
        self.assertIsNone(calls.of_chat(by_id, "dm"))

    def test_mine(self):
        by_id = calls.merge({}, view(state="live", members=("a", "b")))
        self.assertEqual(calls.mine(by_id, "b")["id"], "c1")
        self.assertIsNone(calls.mine(by_id, "z"))

    def test_ringing_for_me(self):
        by_id = calls.merge({}, view())
        self.assertEqual([c["id"] for c in calls.ringing_for(by_id, "b", NOW)], ["c1"])
        self.assertEqual(calls.ringing_for(by_id, "a", NOW), [])
        self.assertEqual(calls.ringing_for(calls.merge({}, view(declined=("b",))), "b", NOW), [])
        self.assertEqual(calls.ringing_for(calls.merge({}, view(started=NOW - 46000)), "b", NOW), [])
        self.assertEqual(calls.ringing_for(calls.merge({}, view(state="live", members=("a", "c"))), "b", NOW), [])

    def test_can_join(self):
        self.assertTrue(calls.can_join(view(state="live", members=("a", "c")), "b"))
        self.assertFalse(calls.can_join(view(state="live", members=("a", "c", "d", "e")), "b"))
        self.assertFalse(calls.can_join(view(state="ended"), "b"))
        self.assertFalse(calls.can_join(view(members=("a", "b")), "b"))

    def test_the_joiner_offers_to_everyone_already_in(self):
        args = calls.start_args(view(state="live", members=("a", "c", "b")), "b", {"a": "Ann"},
                                [{"urls": ["stun:x"]}], True, mic="m1")
        self.assertEqual(args["me"], "b")
        self.assertEqual(sorted(args["peers"]), ["a", "c"])
        self.assertEqual(sorted(args["offer_to"]), ["a", "c"])
        self.assertEqual((args["video"], args["mic"], args["cam"]), (True, "m1", ""))
        self.assertEqual(calls.start_args(view(), "a", {}, [], False)["peers"], [])

    def test_peer_commands(self):
        cmds = calls.peer_commands(["a", "b"], ["a", "b", "c"], "a")
        self.assertEqual(cmds, [("add_peer", {"uid": "c", "offer": False})])
        cmds = calls.peer_commands(["a", "b", "c"], ["a", "c"], "a")
        self.assertEqual(cmds, [("remove_peer", {"uid": "b"})])
        self.assertEqual(calls.peer_commands(["a"], ["a"], "a"), [])

    def test_texts(self):
        self.assertEqual(calls.duration_text(42), u"42 с")
        self.assertEqual(calls.duration_text(61), u"1 мин")
        self.assertEqual(calls.duration_text(3600 + 120), u"62 мин")
        self.assertEqual(calls.note_text({"id": "c", "kind": "audio", "answered": True, "seconds": 300}),
                         u"Звонок · 5 мин")
        self.assertEqual(calls.note_text({"id": "c", "kind": "video", "answered": False, "seconds": 0}),
                         u"Пропущенный звонок")
        self.assertEqual(calls.note_text(None), "")

    def test_the_preview_of_a_call_line(self):
        m = {"id": "m", "text": "", "call": {"id": "c", "kind": "audio", "answered": False, "seconds": 0}}
        self.assertEqual(look.message_text(m),
                         u"\U0001F4DE Пропущенный звонок")

    def test_stdlib_only(self):
        code = ("import sys; sys.path.insert(0, 'SkeldarAnim'); "
                "import maya_chat.calls, maya_chat.records; "
                "print(any(m.split('.')[0] in ('maya', 'PySide6', 'shiboken6') for m in sys.modules))")
        out = subprocess.check_output([sys.executable, "-c", code]).decode().strip()
        self.assertEqual(out, "False")


if __name__ == "__main__":
    unittest.main()
