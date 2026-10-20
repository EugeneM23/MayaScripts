"""maya_chat.link.Protocol without a socket."""
import json
import unittest

from maya_chat import link as l

MSG = {"id": "m1", "chat": "c1", "seq": 1, "from_id": "a1", "cid": "x", "text": "hi",
       "reply_to": None, "at": 10, "edited_at": None, "deleted": False}


class Clock(object):
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


def made(since=0, outbox=()):
    sent, clock = [], Clock()
    p = l.Protocol(sent.append, since, outbox, clock=clock)
    seen = []
    for name in ("event", "ack", "error", "caught_up", "state"):
        setattr(p, "on_" + name, lambda *a, n=name: seen.append((n,) + a))
    p.on_resync = lambda: seen.append(("resync",))
    return p, sent, clock, seen


class Open(unittest.TestCase):
    def test_hello_then_the_outbox_in_order(self):
        p, sent, _, seen = made(7, [{"type": "send", "cid": "1"}, {"type": "send", "cid": "2"}])
        p.opened()
        self.assertEqual([json.loads(t) for t in sent],
                         [{"type": "hello", "since": 7}, {"type": "send", "cid": "1"},
                          {"type": "send", "cid": "2"}])
        self.assertIn(("state", "open"), seen)

    def test_queue_while_closed_waits_and_is_not_doubled(self):
        p, sent, _, _ = made()
        p.queue({"type": "send", "cid": "1"})
        p.queue({"type": "send", "cid": "1"})
        self.assertEqual(sent, [])
        p.opened()
        self.assertEqual(len(sent), 2)

    def test_push_is_never_kept(self):
        p, sent, _, _ = made()
        self.assertFalse(p.push({"type": "read"}))
        p.opened()
        self.assertTrue(p.push({"type": "read"}))
        self.assertEqual(len(sent), 2)
        p.opened()
        self.assertEqual(len(sent), 3)  # hello only: the read is gone


class Frames(unittest.TestCase):
    def test_an_ack_drops_its_send(self):
        p, _, _, seen = made(outbox=[{"type": "send", "cid": "1"}, {"type": "send", "cid": "2"}])
        p.received(json.dumps({"kind": "ack", "cid": "1", "id": "m", "seq": 3}))
        self.assertEqual([m["cid"] for m in p.outbox], ["2"])
        self.assertEqual(seen[-1][0], "ack")

    def test_an_error_naming_a_cid_drops_it(self):
        p, _, _, seen = made(outbox=[{"type": "send", "cid": "1"}])
        p.received(json.dumps({"kind": "error", "cid": "1", "code": "too_long", "text": "t"}))
        self.assertEqual(p.outbox, [])
        self.assertEqual(seen[-1][1]["code"], "too_long")

    def test_seq_moves_since(self):
        p, _, _, seen = made(5)
        p.received(json.dumps({"seq": 9, "kind": "message", "message": MSG}))
        self.assertEqual(p.since, 9)
        p.received(json.dumps({"kind": "caught_up", "seq": 12}))
        self.assertEqual(p.since, 12)
        p.received(json.dumps({"kind": "caught_up", "seq": 4}))
        self.assertEqual(p.since, 12)
        self.assertEqual([s[0] for s in seen], ["event", "caught_up", "caught_up"])

    def test_resync_pong_and_junk(self):
        p, _, _, seen = made()
        p.received(json.dumps({"kind": "resync"}))
        p.received("pong")
        p.received("{broken")
        p.received(json.dumps({"kind": "launch", "seq": 1}))
        self.assertEqual(seen, [("resync",)])


class Timing(unittest.TestCase):
    def test_backoff(self):
        p, _, _, _ = made()
        self.assertEqual([p.closed() for _ in range(8)], [1, 2, 4, 8, 16, 30, 30, 30])
        p.opened()
        self.assertEqual(p.closed(), 1)

    def test_ping_while_open_only(self):
        p, sent, clock, _ = made()
        self.assertIsNone(p.tick(clock.now + 100))
        p.opened()
        clock.now += 10
        self.assertIsNone(p.tick())
        clock.now += 20
        self.assertEqual(p.tick(), "ping")
        self.assertEqual(sent[-1], "ping")
        p.received("pong")
        clock.now += 10
        self.assertIsNone(p.tick())

    def test_a_quiet_socket_is_dead(self):
        p, _, clock, _ = made()
        p.opened()
        clock.now += l.DEAD_S
        self.assertEqual(p.tick(), "dead")


class Address(unittest.TestCase):
    def test_ws_url(self):
        self.assertEqual(l.ws_url("https://a.dev/"), "wss://a.dev/v1/ws")
        self.assertEqual(l.ws_url("http://127.0.0.1:8787"), "ws://127.0.0.1:8787/v1/ws")


if __name__ == "__main__":
    unittest.main()
