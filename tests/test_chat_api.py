"""maya_chat.api on a fake opener: what goes out, what an answer raises."""
import io
import json
import unittest
import urllib.error

from maya_chat import api as a


class Answer(object):
    def __init__(self, doc, status=200):
        self.raw = json.dumps(doc).encode("utf-8")
        self.status = status

    def read(self):
        return self.raw

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class Opener(object):
    def __init__(self, answer=None, raise_=None):
        self.answer = answer if answer is not None else Answer({})
        self.raise_ = raise_
        self.seen = []

    def __call__(self, req, timeout=None):
        self.seen.append(req)
        if self.raise_ is not None:
            raise self.raise_
        return self.answer


def headers(req):
    return {k.lower(): v for k, v in req.header_items()}


class Calls(unittest.TestCase):
    def test_register_sends_the_body_and_our_agent(self):
        op = Opener(Answer({"token": "t", "user": {}}))
        out = a.Api("https://x.dev/", opener=op).register("anna")
        req = op.seen[0]
        self.assertEqual((req.full_url, req.get_method()), ("https://x.dev/v1/register", "POST"))
        self.assertEqual(json.loads(req.data.decode()), {"nick": "anna"})
        h = headers(req)
        self.assertEqual(h["user-agent"], a.AGENT)
        self.assertNotIn("authorization", h)
        self.assertEqual(out["token"], "t")

    def test_the_token_goes_as_bearer(self):
        op = Opener(Answer({"users": [1]}))
        out = a.Api("https://x.dev", "skc_1", opener=op).users("an na")
        req = op.seen[0]
        self.assertEqual(req.full_url, "https://x.dev/v1/users?q=an%20na")
        self.assertEqual(headers(req)["authorization"], "Bearer skc_1")
        self.assertEqual(out, [1])

    def test_routes(self):
        op = Opener(Answer({"messages": []}))
        api = a.Api("https://x.dev", "t", opener=op)
        api.answer("accept", "u1")
        api.unfriend("u1")
        api.dm("u1")
        api.group("G", ["u1", "u2"])
        api.remove_member("g_1", "u2")
        api.history("g_1", before=9, limit=20)
        got = [(r.get_method(), r.full_url.replace("https://x.dev", "")) for r in op.seen]
        self.assertEqual(got, [("POST", "/v1/friends/accept"), ("DELETE", "/v1/friends/u1"),
                               ("POST", "/v1/chats"), ("POST", "/v1/chats"),
                               ("DELETE", "/v1/chats/g_1/members/u2"),
                               ("GET", "/v1/chats/g_1/messages?limit=20&before=9")])
        self.assertEqual(json.loads(op.seen[2].data.decode()), {"kind": "dm", "with": "u1"})
        with self.assertRaises(ValueError):
            api.answer("launch", "u1")


class Failures(unittest.TestCase):
    def test_a_refusal_carries_the_server_code(self):
        err = urllib.error.HTTPError("u", 409, "x", {},
                                     io.BytesIO(json.dumps({"error": "nick_taken", "text": "@a is taken"}).encode()))
        with self.assertRaises(a.ChatError) as caught:
            a.Api("https://x.dev", opener=Opener(raise_=err)).register("a")
        self.assertEqual((caught.exception.code, caught.exception.text, caught.exception.status),
                         ("nick_taken", "@a is taken", 409))

    def test_offline(self):
        op = Opener(raise_=urllib.error.URLError("no route"))
        with self.assertRaises(a.ChatError) as caught:
            a.Api("https://x.dev", "t", opener=op).me()
        self.assertEqual(caught.exception.code, "offline")

    def test_unreadable(self):
        class Raw(Answer):
            def read(self):
                return b"<html>"
        with self.assertRaises(a.ChatError) as caught:
            a.Api("https://x.dev", opener=Opener(Raw({}))).me()
        self.assertEqual(caught.exception.code, "server")


if __name__ == "__main__":
    unittest.main()


class ServerClock(unittest.TestCase):
    """The server's Date header gives this machine's clock skew (a call rings by the server's time)."""

    def test_the_skew_is_read_off_the_date_header(self):
        import time
        from email.utils import formatdate
        ans = Answer({})
        ans.headers = {"Date": formatdate(time.time() - 120, usegmt=True)}   # the server 2 min behind
        api = a.Api("https://x.dev", opener=Opener(ans))
        self.assertEqual(api.skew_ms, 0)
        api.me()
        self.assertAlmostEqual(api.skew_ms, 120000, delta=2000)

    def test_no_date_keeps_the_skew(self):
        api = a.Api("https://x.dev", opener=Opener(Answer({})))
        api.me()
        self.assertEqual(api.skew_ms, 0)
