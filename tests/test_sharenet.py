"""maya_sharenet against a local server that plays litterbox and ntfy.sh.

Nothing here reaches the internet: every call is pointed at 127.0.0.1.

Spec: docs/superpowers/specs/2026-09-30-shared-files-design.md
"""

import http.server
import json
import os
import re
import shutil
import tempfile
import threading
import time
import unittest
import urllib.parse

import maya_sharenet as net

LITTER = "https://litter.catbox.moe/abc123.zip"
TEMPSH = "https://temp.sh/AbCdE/share.zip"


class _Server(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self):
        http.server.ThreadingHTTPServer.__init__(self, ("127.0.0.1", 0),
                                                 _Handler)
        self.fields = {}
        self.upload = None
        self.filename = None
        self.reply = LITTER
        self.status = 200
        self.messages = []
        self.queries = []
        self.files = {}
        self.cond = threading.Condition()
        self.closing = False
        self.close_after = None
        self.tempsh_reply = TEMPSH
        self.tempsh_status = 200
        self.downloads = []

    @property
    def base(self):
        return "http://127.0.0.1:{0}".format(self.server_address[1])

    def post_message(self, topic, body):
        with self.cond:
            mid = "m{0}".format(len(self.messages) + 1)
            self.messages.append({"id": mid, "event": "message",
                                  "topic": topic, "message": body})
            self.cond.notify_all()
            return mid

    def stop(self):
        with self.cond:
            self.closing = True
            self.cond.notify_all()
        self.shutdown()
        self.server_close()


class _Handler(http.server.BaseHTTPRequestHandler):

    def log_message(self, *args):
        pass

    def _answer(self, code, data):
        try:
            self.send_response(code)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except OSError:
            pass                    # the client hung up (a cancelled upload)

    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        path = urllib.parse.urlsplit(self.path).path
        if path == "/api.php":
            self._multipart(body)
            self._answer(self.server.status, self.server.reply.encode())
            return
        if path == "/upload":
            self._multipart(body)
            self._answer(self.server.tempsh_status,
                         self.server.tempsh_reply.encode())
            return
        if path.startswith("/file/"):
            self._serve(path, "POST")
            return
        mid = self.server.post_message(path.strip("/"), body.decode("utf-8"))
        self._answer(200, json.dumps({"id": mid, "event": "message"}).encode())

    def _multipart(self, body):
        boundary = self.headers["Content-Type"].split("boundary=")[1].encode()
        for part in body.split(b"--" + boundary):
            if b"\r\n\r\n" not in part:
                continue
            head, content = part.split(b"\r\n\r\n", 1)
            if content.endswith(b"\r\n"):
                content = content[:-2]
            name = re.search(rb'name="([^"]+)"', head).group(1).decode()
            found = re.search(rb'filename="([^"]+)"', head)
            if found:
                self.server.upload = content
                self.server.filename = found.group(1).decode()
            else:
                self.server.fields[name] = content.decode()

    def _serve(self, path, method):
        self.server.downloads.append(method)
        data = self.server.files.get(path[len("/file/"):])
        if data is None:
            self._answer(404, b"not found")
        else:
            self._answer(200, data)

    def _line(self, event):
        self.wfile.write((json.dumps(event) + "\n").encode())
        self.wfile.flush()

    def do_GET(self):
        split = urllib.parse.urlsplit(self.path)
        if split.path.startswith("/file/"):
            self._serve(split.path, "GET")
            return
        if not split.path.endswith("/json"):
            self._answer(404, b"")
            return
        since = urllib.parse.parse_qs(split.query).get("since", [""])[0]
        self.server.queries.append(since)
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson")
        self.end_headers()
        try:
            self._line({"event": "open"})
            ids = [m["id"] for m in self.server.messages]
            index = ids.index(since) + 1 if since in ids else 0
            sent = 0
            with self.server.cond:
                while not self.server.closing:
                    while index < len(self.server.messages):
                        self._line(self.server.messages[index])
                        index += 1
                        sent += 1
                        if (self.server.close_after
                                and sent >= self.server.close_after):
                            return
                    self.server.cond.wait(0.1)
        except OSError:
            return


def _wait(predicate, timeout=5.0):
    end = time.time() + timeout
    while time.time() < end:
        if predicate():
            return True
        time.sleep(0.02)
    return predicate()


class _WithServer(unittest.TestCase):

    def setUp(self):
        self.server = _Server()
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       daemon=True)
        self.thread.start()
        self.dir = tempfile.mkdtemp(prefix="sharenet_")

    def tearDown(self):
        self.server.stop()
        shutil.rmtree(self.dir, ignore_errors=True)

    def _file(self, size=600 * 1024, name="a.zip"):
        path = os.path.join(self.dir, name)
        with open(path, "wb") as out:
            out.write(os.urandom(size))
        return path


class Upload(_WithServer):

    def test_sends_the_fields_and_the_file(self):
        path = self._file()
        calls = []
        url = net.upload(path, progress=lambda d, t: calls.append((d, t)),
                         url=self.server.base + "/api.php")
        self.assertEqual(url, LITTER)
        self.assertEqual(self.server.fields,
                         {"reqtype": "fileupload", "time": "72h"})
        with open(path, "rb") as handle:
            self.assertEqual(self.server.upload, handle.read())
        self.assertEqual(self.server.filename, "share.zip")
        self.assertGreaterEqual(len(calls), 2)
        self.assertEqual(calls[-1][0], calls[-1][1])

    def test_progress_false_cancels(self):
        with self.assertRaises(net.Cancelled):
            net.upload(self._file(), progress=lambda d, t: False,
                       url=self.server.base + "/api.php")

    def test_a_reply_that_is_no_address(self):
        self.server.reply = "File too big"
        with self.assertRaises(net.ShareError) as caught:
            net.upload(self._file(1000), url=self.server.base + "/api.php")
        self.assertIn("litterbox", str(caught.exception))

    def test_an_http_error(self):
        self.server.status = 500
        with self.assertRaises(net.ShareError):
            net.upload(self._file(1000), url=self.server.base + "/api.php")

    def test_an_unreachable_host(self):
        with self.assertRaises(net.ShareError) as caught:
            net.upload(self._file(1000), url="http://127.0.0.1:1/api.php")
        self.assertIn("could not reach", str(caught.exception))

    def test_the_upload_writes_in_big_pieces(self):
        """http.client given the body itself reads it 8 KB at a time, and
        that ran at 0.20 MB/s against 1.56 in 1 MB pieces (2026-09-30)."""
        seen = []
        saved = net._open

        def spy(request, timeout=net.TIMEOUT):
            seen.append(request.data)
            return saved(request, timeout)

        net._open = spy
        try:
            net.upload(self._file(3 * 1024 * 1024 + 5),
                       url=self.server.base + "/api.php")
        finally:
            net._open = saved
        self.assertFalse(hasattr(seen[0], "read"))
        body = net.MultipartBody(self._file(3 * 1024 * 1024 + 5), [], "f",
                                 "share.zip")
        sizes = [len(piece) for piece in body.chunks()]
        body.close()
        self.assertEqual(sizes[0], net.SEND_BLOCK)
        self.assertEqual(sum(sizes), body.length)

    def test_the_body_length_is_exact(self):
        path = self._file(12345)
        body = net.MultipartBody(path, [("a", "1")], "f", "share.zip")
        data = b""
        while True:
            chunk = body.read(1000)
            if not chunk:
                break
            data += chunk
        body.close()
        self.assertEqual(len(data), body.length)
        self.assertIn("boundary=", body.content_type)


class TempSh(_WithServer):

    def test_sends_the_file_field(self):
        path = self._file()
        url = net.upload_tempsh(path, url=self.server.base + "/upload")
        self.assertEqual(url, TEMPSH)
        self.assertEqual(self.server.fields, {})
        with open(path, "rb") as handle:
            self.assertEqual(self.server.upload, handle.read())

    def test_a_reply_that_is_no_address(self):
        self.server.tempsh_reply = "<html>busy</html>"
        with self.assertRaises(net.ShareError) as caught:
            net.upload_tempsh(self._file(1000),
                              url=self.server.base + "/upload")
        self.assertIn("temp.sh", str(caught.exception))


class UploadAny(_WithServer):

    def setUp(self):
        _WithServer.setUp(self)
        self.saved = (net.TEMPSH_URL, net.UPLOAD_URL)

    def tearDown(self):
        net.TEMPSH_URL, net.UPLOAD_URL = self.saved
        _WithServer.tearDown(self)

    def test_temp_sh_first(self):
        net.TEMPSH_URL = self.server.base + "/upload"
        net.UPLOAD_URL = "http://127.0.0.1:1/api.php"
        self.assertEqual(net.upload_any(self._file(1000)), TEMPSH)

    def test_litterbox_when_temp_sh_fails(self):
        net.TEMPSH_URL = "http://127.0.0.1:1/upload"
        net.UPLOAD_URL = self.server.base + "/api.php"
        self.assertEqual(net.upload_any(self._file(1000)), LITTER)

    def test_both_failing_names_both(self):
        net.TEMPSH_URL = "http://127.0.0.1:1/upload"
        net.UPLOAD_URL = "http://127.0.0.1:1/api.php"
        with self.assertRaises(net.ShareError) as caught:
            net.upload_any(self._file(1000))
        self.assertIn("temp.sh", str(caught.exception))
        self.assertIn("litterbox", str(caught.exception))

    def test_a_cancel_does_not_fall_back(self):
        net.TEMPSH_URL = self.server.base + "/upload"
        net.UPLOAD_URL = self.server.base + "/api.php"
        with self.assertRaises(net.Cancelled):
            net.upload_any(self._file(), progress=lambda d, t: False)
        self.assertIsNone(self.server.fields.get("reqtype"))


class Publish(_WithServer):

    def test_the_body_arrives_and_the_id_comes_back(self):
        mid = net.publish('{"a": "б"}', topic="t1", base=self.server.base)
        self.assertEqual(mid, "m1")
        self.assertEqual(self.server.messages[0]["message"], '{"a": "б"}')
        self.assertEqual(self.server.messages[0]["topic"], "t1")

    def test_an_unreachable_channel(self):
        with self.assertRaises(net.ShareError):
            net.publish("x", topic="t", base="http://127.0.0.1:1")


class Download(_WithServer):

    def test_bytes_and_progress(self):
        data = os.urandom(700 * 1024)
        self.server.files["x.zip"] = data
        path = os.path.join(self.dir, "got.zip")
        calls = []
        size = net.download(self.server.base + "/file/x.zip", path,
                            progress=lambda d, t: calls.append((d, t)))
        self.assertEqual(size, len(data))
        with open(path, "rb") as handle:
            self.assertEqual(handle.read(), data)
        self.assertFalse(os.path.exists(path + ".part"))
        self.assertEqual(calls[-1], (len(data), len(data)))

    def test_temp_sh_is_fetched_with_a_post(self):
        self.server.files["x.zip"] = b"payload"
        saved = net.TEMPSH_HOST
        net.TEMPSH_HOST = "127.0.0.1"
        try:
            path = os.path.join(self.dir, "got.zip")
            net.download(self.server.base + "/file/x.zip", path)
        finally:
            net.TEMPSH_HOST = saved
        self.assertEqual(self.server.downloads, ["POST"])
        with open(path, "rb") as handle:
            self.assertEqual(handle.read(), b"payload")

    def test_404_is_expired_and_leaves_nothing(self):
        path = os.path.join(self.dir, "got.zip")
        with self.assertRaises(net.Expired):
            net.download(self.server.base + "/file/gone.zip", path)
        self.assertFalse(os.path.exists(path))
        self.assertFalse(os.path.exists(path + ".part"))


class Subscriber(_WithServer):

    def test_messages_before_and_after_arrive_in_order(self):
        self.server.post_message("t", "one")
        self.server.post_message("t", "two")
        events, states = [], []
        sub = net.Subscriber(events.append, since="all", topic="t",
                             base=self.server.base, on_state=states.append,
                             timeout=5)
        sub.start()
        self.assertTrue(_wait(lambda: len([e for e in events
                                           if e.get("event") == "message"])
                              == 2))
        self.server.post_message("t", "three")
        self.assertTrue(_wait(lambda: sub.since == "m3"))
        bodies = [e["message"] for e in events if e.get("event") == "message"]
        self.assertEqual(bodies, ["one", "two", "three"])
        self.assertIn("online", states)
        self.assertEqual(self.server.queries[0], "all")
        started = time.time()
        sub.stop()
        sub.join(3)
        self.assertFalse(sub.is_alive())
        self.assertLess(time.time() - started, 3)

    def test_a_dropped_stream_reconnects_from_the_last_id(self):
        self.server.close_after = 1
        self.server.post_message("t", "one")
        self.server.post_message("t", "two")
        events, states = [], []
        sub = net.Subscriber(events.append, since="all", topic="t",
                             base=self.server.base, on_state=states.append,
                             delays=(0.05,), timeout=5)
        sub.start()
        try:
            self.assertTrue(_wait(lambda: sub.since == "m2"))
            self.assertEqual(self.server.queries[:2], ["all", "m1"])
            self.assertTrue(any(s.startswith("offline - ") for s in states))
        finally:
            sub.stop()
            sub.join(3)

    def test_a_callback_that_raises_does_not_stop_it(self):
        self.server.post_message("t", "one")
        self.server.post_message("t", "two")
        seen = []

        def angry(event):
            seen.append(event)
            raise RuntimeError("boom")

        sub = net.Subscriber(angry, since="all", topic="t",
                             base=self.server.base, timeout=5)
        sub.start()
        try:
            self.assertTrue(_wait(lambda: sub.since == "m2"))
        finally:
            sub.stop()
            sub.join(3)

    def test_the_url_resolves_the_topic_at_call_time(self):
        saved = net.TOPIC
        try:
            net.TOPIC = "later-topic"
            sub = net.Subscriber(lambda e: None, since="12h")
            self.assertIn("/later-topic/json?since=12h", sub.url())
        finally:
            net.TOPIC = saved


if __name__ == "__main__":
    unittest.main()
