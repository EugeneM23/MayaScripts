"""maya_voice.session - the room connection, the lobby fetch, the panel's pure parts."""

import json
import queue
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from maya_voice import protocol, session as sessionmod, ws


class FakeConn(object):
    """A socket stand-in: `incoming` is what the server sends, `sent` what we send."""

    def __init__(self):
        self.incoming = queue.Queue()
        self.sent = []
        self.closed = False

    def recv_message(self):
        item = self.incoming.get()
        if item is None:
            raise ws.WebSocketError("connection closed")
        return item

    def send_text(self, text):
        self.sent.append((ws.OP_TEXT, text))

    def send_binary(self, data):
        self.sent.append((ws.OP_BIN, bytes(data)))

    def send_ping(self):
        self.sent.append((ws.OP_PING, b""))

    def close(self, code=1000):
        self.closed = True
        self.incoming.put(None)


def wait_for(predicate, timeout=3.0):
    import time
    end = time.time() + timeout
    while time.time() < end:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


def collect(sess, count, timeout=3.0):
    """Drain the session until `count` events came, or the time is up."""
    import time
    events = []
    end = time.time() + timeout
    while len(events) < count and time.time() < end:
        events.extend(sess.drain())
        time.sleep(0.01)
    return events


class RoomAddresses(unittest.TestCase):

    def test_https_becomes_wss_and_keeps_the_host(self):
        self.assertEqual(sessionmod.room_url("https://v.example.dev/", "lay"),
                         "wss://v.example.dev/room/lay")

    def test_bare_host_gets_https(self):
        self.assertEqual(sessionmod.room_url("v.example.dev", "lay"),
                         "wss://v.example.dev/room/lay")

    def test_lobby_address(self):
        self.assertEqual(sessionmod.rooms_url("v.example.dev/"),
                         "https://v.example.dev/rooms")


class SessionLifecycle(unittest.TestCase):

    def test_open_says_join_and_the_welcome_comes_back_as_an_event(self):
        conn = FakeConn()
        sess = sessionmod.Session(connector=lambda url: conn)
        sess.open("wss://x/room/lay", "Eugene")
        self.assertTrue(wait_for(lambda: any(
            op == ws.OP_TEXT and '"join"' in data for op, data in conn.sent)))
        join = [d for op, d in conn.sent if op == ws.OP_TEXT][0]
        self.assertEqual(protocol.parse_control(join),
                         {"t": "join", "name": "Eugene"})
        sess.close()

    def test_media_and_control_from_the_server_are_decoded(self):
        conn = FakeConn()
        sess = sessionmod.Session(connector=lambda url: conn)
        sess.open("wss://x/room/lay", "Eugene")
        conn.incoming.put((ws.OP_BIN, protocol.pack_media(
            protocol.TYPE_AUDIO, 2, 9, b"pcm")))
        conn.incoming.put((ws.OP_TEXT, b'{"t":"roster","members":[]}'))
        events = collect(sess, 2)
        kinds = [e[0] for e in events]
        self.assertIn("media", kinds)
        self.assertIn("control", kinds)
        media = [e for e in events if e[0] == "media"][0]
        self.assertEqual(media[1:], (protocol.TYPE_AUDIO, 2, 9, b"pcm"))
        sess.close()

    def test_server_close_is_reported_once_with_the_reason(self):
        conn = FakeConn()
        sess = sessionmod.Session(connector=lambda url: conn)
        sess.open("wss://x/room/lay", "Eugene")
        conn.incoming.put(None)                     # the socket dies
        events = collect(sess, 1)
        closed = [e for e in events if e[0] == "closed"]
        self.assertEqual(len(closed), 1)
        sess.close()

    def test_audio_sent_is_a_binary_frame_of_type_a(self):
        conn = FakeConn()
        sess = sessionmod.Session(connector=lambda url: conn)
        sess.open("wss://x/room/lay", "Eugene")
        sess.send_audio(5, b"\x01\x02")
        self.assertTrue(wait_for(lambda: any(
            op == ws.OP_BIN for op, _ in conn.sent)))
        frame = [d for op, d in conn.sent if op == ws.OP_BIN][0]
        kind, sender, seq, payload = protocol.unpack_media(frame)
        self.assertEqual((kind, seq, payload), (protocol.TYPE_AUDIO, 5,
                                                b"\x01\x02"))
        sess.close()

    def test_full_outbox_drops_the_oldest_media_and_never_blocks(self):
        sess = sessionmod.Session(connector=lambda url: FakeConn())
        sess.outbox = queue.Queue(maxsize=2)
        for seq in range(5):
            sess.send_audio(seq, b"x")
        items = []
        while True:
            try:
                items.append(sess.outbox.get_nowait())
            except queue.Empty:
                break
        self.assertEqual(len(items), 2)

    def test_connector_failure_propagates_to_the_caller(self):
        def refuse(url):
            raise OSError("no route")
        sess = sessionmod.Session(connector=refuse)
        with self.assertRaises(OSError):
            sess.open("wss://x/room/lay", "Eugene")


class LobbyFetch(unittest.TestCase):

    def test_fetch_rooms_reads_the_lobby_json(self):
        body = json.dumps({"rooms": [{"room": "lay", "members": ["Eugene"]}]})

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body.encode())

            def log_message(self, *args):
                pass
        server = HTTPServer(("127.0.0.1", 0), Handler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.handle_request, daemon=True)
        thread.start()
        rooms = sessionmod.fetch_rooms("http://127.0.0.1:{0}".format(port))
        server.server_close()
        self.assertEqual(rooms, [{"room": "lay", "members": ["Eugene"]}])

    def test_async_fetch_returns_an_error_event_when_nothing_answers(self):
        inbox = queue.Queue()
        sessionmod.fetch_rooms_async("http://127.0.0.1:1", inbox).join(5)
        self.assertEqual(inbox.get(timeout=1)[0], "rooms_error")


if __name__ == "__main__":
    unittest.main()
