"""maya_chat.session on a fake api and a fake link."""
import json
import shutil
import sys
import tempfile
import unittest

from maya_chat import api as a
from maya_chat import session as s
from maya_chat import store as st

ME = {"id": "me", "nick": "me", "name": "Me", "avatar_v": 0}
BOB = {"id": "bob", "nick": "bob", "name": "Bob", "avatar_v": 0}


def msg(id, seq, frm="bob", chat="dm", cid=None, text="hi"):
    return {"id": id, "chat": chat, "seq": seq, "from_id": frm, "cid": cid or id, "text": text,
            "reply_to": None, "at": seq, "edited_at": None, "deleted": False}


def chat(id="dm", unread=0, last=None, members=(ME, BOB)):
    return {"id": id, "kind": "dm", "name": "", "admin": None, "avatar_v": 0,
            "members": [dict(u) for u in members], "last": last, "unread": unread, "read_upto": 0}


class FakeApi(object):
    instances = []
    nick = "me"

    def __init__(self, server, token=None):
        self.server, self.token = server, token
        self.chat_list = [chat()]
        self.histories = {"dm": [msg("m1", 1)]}
        self.seq = 20
        self.calls = []
        FakeApi.instances.append(self)

    def register(self, nick):
        if nick == "taken":
            raise a.ChatError("nick_taken", "@taken is taken", 409)
        FakeApi.nick = nick
        return {"token": "skc_new", "user": dict(ME, nick=nick)}

    def me(self):
        if self.token == "skc_bad":
            raise a.ChatError("bad_token", "no", 401)
        return dict(ME, nick=FakeApi.nick)

    def chats(self):
        self.calls.append("chats")
        return {"seq": self.seq, "chats": [dict(c) for c in self.chat_list]}

    def history(self, chat_id, before=None, limit=50):
        self.calls.append(("history", chat_id, before))
        rows = self.histories.get(chat_id, [])
        if before is not None:
            rows = [m for m in rows if m["seq"] < before]
        return [dict(m) for m in rows][-limit:]

    def friends(self):
        return {"friends": [dict(BOB, online=True, last_seen=0)], "incoming": [], "outgoing": []}

    def dm(self, user_id):
        return chat("dm_new", members=(ME, BOB))

    def people(self):
        return [dict(BOB, online=True, last_seen=0, relation="friend"),
                {"id": "carl", "nick": "carl", "name": "Carl", "avatar_v": 0, "online": False,
                 "last_seen": 5, "relation": None}]


class FakeLink(object):
    def __init__(self, server, token, protocol):
        self.protocol = protocol
        self.sent = []
        protocol.send = self.sent.append
        self.started = self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def frames(self):
        return [json.loads(t) for t in self.sent if t != "ping"]


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.store = st.Store(self.dir)
        FakeApi.instances = []
        FakeApi.nick = "me"

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def session(self, token="skc_1"):
        if token:
            self.store.set_token(token)
        ses = s.Session("https://x.dev", self.store, FakeApi, FakeLink)
        self.told = []
        ses.listen(lambda kind, data: self.told.append(kind))
        ses.start()
        return ses

    def frame(self, ses, doc):
        ses.protocol.received(json.dumps(doc))


class Start(Base):
    def test_no_token_is_signed_out(self):
        ses = self.session(token=None)
        self.assertEqual(ses.state.status, "signed_out")
        self.assertIsNone(ses.link)

    def test_start_reads_everything(self):
        ses = self.session()
        self.assertEqual(ses.state.me["id"], "me")
        self.assertEqual(list(ses.state.chats), ["dm"])
        self.assertEqual([m["id"] for m in ses.state.messages["dm"]], ["m1"])
        self.assertEqual([u["id"] for u in ses.state.people], ["bob", "carl"])
        self.assertEqual(ses.state.online["bob"]["online"], True)
        self.assertEqual(ses.protocol.since, 20)
        self.assertEqual(self.store.since(), 20)
        self.assertTrue(ses.link.started)

    def test_a_bad_token_signs_out(self):
        ses = self.session(token="skc_bad")
        self.assertEqual(ses.state.status, "signed_out")
        self.assertIsNone(self.store.token())

    def test_sign_in_and_out(self):
        ses = self.session(token=None)
        me = ses.sign_in(" @Anna ")
        self.assertEqual(me["nick"], "anna")
        self.assertEqual(self.store.token(), "skc_new")
        with self.assertRaises(a.ChatError):
            ses.sign_in("x")
        with self.assertRaises(a.ChatError):
            ses.sign_in("taken")
        link = ses.link
        ses.sign_out()
        self.assertTrue(link.stopped)
        self.assertIsNone(self.store.token())
        self.assertEqual(ses.state.status, "signed_out")

    def test_status_follows_the_link(self):
        ses = self.session()
        ses.protocol.opened()
        self.assertEqual(ses.state.status, "online")
        ses.protocol.closed()
        self.assertEqual(ses.state.status, "offline")


class Sending(Base):
    def test_a_send_waits_then_becomes_the_message(self):
        ses = self.session()
        cid = ses.send("dm", "  hello ")
        pend = ses.state.pending["dm"][0]
        self.assertEqual((pend["text"], pend["state"]), ("hello", "sending"))
        self.assertEqual(self.store.outbox()[0]["cid"], cid)
        ses.protocol.opened()
        frames = ses.link.frames()
        self.assertEqual(frames[0]["type"], "hello")
        self.assertEqual((frames[1]["type"], frames[1]["cid"]), ("send", cid))
        self.frame(ses, {"seq": 21, "kind": "message", "message": msg("m2", 2, "me", cid=cid)})
        self.frame(ses, {"kind": "ack", "cid": cid, "id": "m2", "seq": 2})
        self.assertNotIn("dm", ses.state.pending)
        self.assertEqual(self.store.outbox(), [])
        self.assertEqual([m["id"] for m in ses.state.messages["dm"]], ["m1", "m2"])
        self.assertEqual(ses.state.chats["dm"]["unread"], 0)
        self.assertEqual(ses.state.chats["dm"]["read_upto"], 2)
        self.assertEqual(self.store.since(), 21)

    def test_the_outbox_survives_a_restart(self):
        ses = self.session()
        cid = ses.send("dm", "later")
        ses.stop()
        again = s.Session("https://x.dev", self.store, FakeApi, FakeLink)
        again.start()
        self.assertEqual(again.state.pending["dm"][0]["cid"], cid)
        again.protocol.opened()
        self.assertEqual(again.link.frames()[1]["cid"], cid)

    def test_a_refused_send_is_failed_and_can_go_again(self):
        ses = self.session()
        ses.protocol.opened()
        cid = ses.send("dm", "x")
        self.frame(ses, {"kind": "error", "cid": cid, "code": "too_many", "text": "Too fast"})
        pend = ses.state.pending["dm"][0]
        self.assertEqual((pend["state"], pend["error"]), ("failed", "Too fast"))
        self.assertIn("failed", self.told)
        self.assertTrue(ses.retry(cid))
        self.assertEqual(ses.link.frames()[-1]["cid"], cid)
        self.assertTrue(ses.discard(cid))
        self.assertNotIn("dm", ses.state.pending)

    def test_empty_and_offline_pushes(self):
        ses = self.session()
        self.assertIsNone(ses.send("dm", "   "))
        self.assertFalse(ses.edit("dm", "m1", "t"))
        ses.protocol.opened()
        self.assertTrue(ses.edit("dm", "m1", "t"))
        self.assertTrue(ses.typing("dm"))
        self.assertFalse(ses.typing("dm"))


class Events(Base):
    def test_a_message_from_bob_counts_once(self):
        ses = self.session()
        e = {"seq": 21, "kind": "message", "message": msg("m2", 2)}
        self.frame(ses, e)
        self.frame(ses, dict(e, seq=22))
        self.assertEqual(ses.state.chats["dm"]["unread"], 1)
        self.assertEqual(ses.state.chats["dm"]["last"]["id"], "m2")
        self.assertEqual(len(self.store.messages("dm")), 2)
        self.assertIn("message", self.told)

    def test_read_marks_it_read(self):
        ses = self.session()
        self.frame(ses, {"seq": 21, "kind": "message", "message": msg("m2", 2)})
        ses.protocol.opened()
        self.assertTrue(ses.read("dm"))
        self.assertEqual(ses.link.frames()[-1], {"type": "read", "chat": "dm", "upto": 2})
        self.assertEqual(ses.state.chats["dm"]["unread"], 0)
        self.assertFalse(ses.read("dm"))
        self.frame(ses, {"seq": 22, "kind": "read", "chat_id": "dm", "user_id": "bob", "upto": 2})
        self.assertEqual(ses.state.reads["dm"]["bob"], 2)

    def test_edit_delete(self):
        ses = self.session()
        self.frame(ses, {"seq": 21, "kind": "edited", "chat_id": "dm", "id": "m1", "text": "new",
                         "edited_at": 5})
        self.assertEqual(ses.state.messages["dm"][0]["text"], "new")
        self.frame(ses, {"seq": 22, "kind": "deleted", "chat_id": "dm", "id": "m1"})
        self.assertTrue(ses.state.messages["dm"][0]["deleted"])
        self.assertEqual(self.store.messages("dm")[0]["text"], "")

    def test_a_message_in_an_unknown_chat_reads_the_chats(self):
        ses = self.session()
        api = ses.api
        api.chat_list.append(chat("g1", members=(ME,)))
        api.histories["g1"] = [msg("g1m", 1, chat="g1")]
        self.frame(ses, {"seq": 21, "kind": "message", "message": msg("g1m", 1, chat="g1")})
        self.assertIn("g1", ses.state.chats)
        self.assertEqual(ses.state.messages["g1"][0]["id"], "g1m")

    def test_removed_from_a_chat(self):
        ses = self.session()
        self.frame(ses, {"seq": 21, "kind": "member_removed", "chat_id": "dm", "user_id": "me",
                         "admin": None})
        self.assertNotIn("dm", ses.state.chats)
        self.assertEqual(self.store.chats(), [])

    def test_people_are_read_and_follow_presence_and_names(self):
        ses = self.session()
        people = ses.read_people()
        self.assertEqual([u["id"] for u in people], ["bob", "carl"])
        self.assertIn("people", self.told)
        self.assertEqual(ses.state.online["carl"], {"online": False, "last_seen": 5})
        self.frame(ses, {"kind": "presence", "user_id": "carl", "online": True, "last_seen": 5})
        self.assertTrue(ses.state.people[1]["online"])
        self.frame(ses, {"seq": 30, "kind": "user", "user": {"id": "carl", "nick": "carl",
                                                             "name": "Karl", "avatar_v": 0}})
        self.assertEqual(ses.state.people[1]["name"], "Karl")

    def test_everybody_follows_presence_names_and_newcomers(self):
        ses = self.session()
        self.frame(ses, {"kind": "presence", "user_id": "bob", "online": False, "last_seen": 9})
        self.assertEqual(ses.state.online["bob"], {"online": False, "last_seen": 9})
        self.assertFalse(ses.state.people[0]["online"])
        self.frame(ses, {"seq": 24, "kind": "user", "user": dict(BOB, name="Robert")})
        self.assertEqual(ses.state.chats["dm"]["members"][1]["name"], "Robert")
        self.assertEqual(ses.state.people[0]["name"], "Robert")
        dan = {"id": "dan", "nick": "dan", "name": "Dan", "avatar_v": 0, "online": False,
               "last_seen": 0}
        self.frame(ses, {"seq": 25, "kind": "user", "user": dan})
        self.assertEqual([u["id"] for u in ses.state.people], ["bob", "carl", "dan"])
        self.frame(ses, {"seq": 26, "kind": "user", "user": dict(ME, name="Me again")})
        self.assertNotIn("me", [u["id"] for u in ses.state.people])

    def test_a_reaction_is_toggled_locally_and_by_the_server(self):
        ses = self.session()
        ses.protocol.opened()
        self.assertTrue(ses.react("dm", "m1", "👍"))
        self.assertEqual(ses.state.messages["dm"][0]["reactions"], {"👍": ["me"]})
        sent = [f for f in ses.link.frames() if f.get("type") == "react"]
        self.assertEqual(sent[-1], {"type": "react", "chat": "dm", "id": "m1", "emoji": "👍",
                                    "on": True})
        self.frame(ses, {"seq": 27, "kind": "reaction", "chat_id": "dm", "id": "m1",
                         "user_id": "me", "emoji": "👍", "on": True})
        self.frame(ses, {"seq": 28, "kind": "reaction", "chat_id": "dm", "id": "m1",
                         "user_id": "bob", "emoji": "👍", "on": True})
        self.assertEqual(ses.state.messages["dm"][0]["reactions"], {"👍": ["me", "bob"]})
        self.assertFalse(ses.react("dm", "m1", "👍"))
        self.assertEqual(ses.state.messages["dm"][0]["reactions"], {"👍": ["bob"]})
        self.frame(ses, {"seq": 29, "kind": "reaction", "chat_id": "dm", "id": "m1",
                         "user_id": "bob", "emoji": "👍", "on": False})
        self.assertEqual(ses.state.messages["dm"][0]["reactions"], {})
        self.assertIsNone(ses.react("dm", "nope", "👍"))

    def test_an_avatar_is_uploaded_and_bumps_me(self):
        ses = self.session()
        ses.api.put_avatar = lambda data, kind: dict(ME, avatar_v=3)
        me = ses.set_avatar(bytes([0xff, 0xd8, 0xff]))
        self.assertEqual(me["avatar_v"], 3)
        self.assertEqual(ses.state.me["avatar_v"], 3)
        self.assertEqual(ses.state.chats["dm"]["members"][0]["avatar_v"], 3)

    def test_resync_reads_again(self):
        ses = self.session()
        ses.api.seq = 99
        ses.api.histories["dm"].append(msg("m5", 5))
        self.frame(ses, {"kind": "resync"})
        self.assertEqual(ses.protocol.since, 99)
        self.assertEqual(ses.state.messages["dm"][-1]["id"], "m5")
        self.assertIn("resync", self.told)

    def test_history_goes_back(self):
        ses = self.session()
        ses.api.histories["dm"] = [msg("m%d" % i, i) for i in range(1, 8)]
        ses.state.messages["dm"] = [msg("m6", 6), msg("m7", 7)]
        self.assertEqual(ses.load_history("dm"), 5)
        self.assertEqual([m["seq"] for m in ses.state.messages["dm"]], [1, 2, 3, 4, 5, 6, 7])
        self.assertEqual(ses.api.calls[-1], ("history", "dm", 6))

    def test_open_dm(self):
        ses = self.session()
        self.assertEqual(ses.open_dm("bob"), "dm_new")
        self.assertIn("dm_new", ses.state.chats)

    def test_a_listener_failing_does_not_stop_it(self):
        ses = self.session()
        ses.listen(lambda kind, data: 1 / 0)
        old = sys.stderr
        try:
            sys.stderr = open(self.dir + "/err.txt", "w")
            self.frame(ses, {"seq": 21, "kind": "message", "message": msg("m2", 2)})
        finally:
            sys.stderr.close()
            sys.stderr = old
        self.assertIn("message", self.told)


class OnePerMaya(unittest.TestCase):
    def test_get_is_kept_on_sys(self):
        made = []

        class Quiet(s.Session):
            def start(self):
                made.append(self)

        old_cls = s.Session
        s.Session = Quiet
        try:
            s.close()
            first = s.get()
            self.assertIs(s.get(), first)
            self.assertEqual(len(made), 1)
            s.close()
            self.assertFalse(hasattr(sys, "_skeldar_chat"))
        finally:
            s.Session = old_cls
            s.close()


if __name__ == "__main__":
    unittest.main()
