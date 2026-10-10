"""maya_voice.ws - the WebSocket client, against a loopback server written here.

The server side is the smallest RFC 6455 peer that exercises the client:
the handshake, unmasked server frames (text, binary, fragments, ping, close),
and the masked frames a client must send.
"""

import socket
import struct
import threading
import unittest

from maya_voice import ws


def server_frame(opcode, payload=b"", fin=True):
    head = bytearray([(0x80 if fin else 0) | opcode])
    n = len(payload)
    if n < 126:
        head.append(n)
    elif n < 65536:
        head.append(126)
        head.extend(struct.pack("!H", n))
    else:
        head.append(127)
        head.extend(struct.pack("!Q", n))
    return bytes(head) + payload


def read_client_frame(sock):
    """(opcode, payload) of one masked frame sent by the client."""
    def take(n):
        out = b""
        while len(out) < n:
            chunk = sock.recv(n - len(out))
            if not chunk:
                raise IOError("client went away")
            out += chunk
        return out
    b0, b1 = take(2)
    opcode = b0 & 0x0F
    assert b1 & 0x80, "a client frame must be masked"
    length = b1 & 0x7F
    if length == 126:
        (length,) = struct.unpack("!H", take(2))
    elif length == 127:
        (length,) = struct.unpack("!Q", take(8))
    key = take(4)
    payload = take(length)
    return opcode, ws.mask(payload, key)


class LoopbackServer(object):
    """One connection, scripted: `script(sock)` runs after the handshake."""

    def __init__(self, script):
        self.script = script
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(1)
        self.port = self.listener.getsockname()[1]
        self.error = None
        self.request = b""
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def url(self, path="/room/test"):
        return "ws://127.0.0.1:{0}{1}".format(self.port, path)

    def _run(self):
        try:
            sock, _ = self.listener.accept()
            sock.settimeout(5)
            data = b""
            while b"\r\n\r\n" not in data:
                data += sock.recv(1024)
            self.request = data
            head, rest = data.split(b"\r\n\r\n", 1)
            key = None
            for line in head.decode("latin-1").split("\r\n"):
                if line.lower().startswith("sec-websocket-key:"):
                    key = line.split(":", 1)[1].strip()
            accept = ws.accept_key(key)
            sock.sendall((
                "HTTP/1.1 101 Switching Protocols\r\n"
                "Upgrade: websocket\r\nConnection: Upgrade\r\n"
                "Sec-WebSocket-Accept: {0}\r\n\r\n".format(accept)
            ).encode("ascii") + rest)
            self.script(sock)
            sock.close()
        except Exception as exc:                        # noqa: BLE001
            self.error = exc
        finally:
            self.listener.close()


class MaskingAndAccept(unittest.TestCase):

    def test_accept_key_is_the_rfc_example(self):
        self.assertEqual(ws.accept_key("dGhlIHNhbXBsZSBub25jZQ=="),
                         "s3pPLMBiTxaQ9kYGzzhZRbK+xOo=")

    def test_mask_is_its_own_inverse_and_handles_lengths(self):
        key = b"\x01\x02\x03\x04"
        for n in (0, 1, 3, 4, 5, 127, 1000):
            data = bytes(range(256)) * 4
            data = data[:n]
            self.assertEqual(ws.mask(ws.mask(data, key), key), data)


class ClientAgainstLoopback(unittest.TestCase):

    def test_handshake_then_text_binary_fragments_and_close(self):
        def script(sock):
            sock.sendall(server_frame(ws.OP_TEXT, b'{"t":"welcome"}'))
            sock.sendall(server_frame(ws.OP_BIN, b"abc", fin=False))
            sock.sendall(server_frame(0x0, b"def", fin=True))
            sock.sendall(server_frame(ws.OP_CLOSE, struct.pack("!H", 1000)))
            #  the client answers the close; read it so the test is honest
            opcode, _ = read_client_frame(sock)
            self.assertEqual(opcode, ws.OP_CLOSE)

        server = LoopbackServer(script)
        conn = ws.connect(server.url())
        self.assertEqual(conn.recv_message(), (ws.OP_TEXT,
                                               b'{"t":"welcome"}'))
        self.assertEqual(conn.recv_message(), (ws.OP_BIN, b"abcdef"))
        opcode, payload = conn.recv_message()
        self.assertEqual(opcode, ws.OP_CLOSE)
        self.assertEqual(payload, struct.pack("!H", 1000))
        self.assertTrue(conn.closed)
        server.thread.join(5)
        self.assertIsNone(server.error)
        self.assertIn(b"GET /room/test HTTP/1.1", server.request)

    def test_client_frames_are_masked_and_carry_the_text(self):
        def script(sock):
            opcode, payload = read_client_frame(sock)
            self.assertEqual(opcode, ws.OP_TEXT)
            self.assertEqual(payload, '{"t":"join","name":"Ё"}'.encode())
            opcode, payload = read_client_frame(sock)
            self.assertEqual(opcode, ws.OP_BIN)
            self.assertEqual(payload, bytes(range(200)))

        server = LoopbackServer(script)
        conn = ws.connect(server.url())
        conn.send_text('{"t":"join","name":"Ё"}')
        conn.send_binary(bytes(range(200)))
        conn.close()
        server.thread.join(5)
        self.assertIsNone(server.error)

    def test_ping_is_answered_with_a_pong_and_not_returned(self):
        def script(sock):
            sock.sendall(server_frame(ws.OP_PING, b"hi"))
            opcode, payload = read_client_frame(sock)
            self.assertEqual(opcode, ws.OP_PONG)
            self.assertEqual(payload, b"hi")
            sock.sendall(server_frame(ws.OP_TEXT, b"after"))
            read_client_frame(sock)                    # the client's close

        server = LoopbackServer(script)
        conn = ws.connect(server.url())
        self.assertEqual(conn.recv_message(), (ws.OP_TEXT, b"after"))
        conn.close()
        server.thread.join(5)
        self.assertIsNone(server.error)

    def test_a_refused_handshake_raises(self):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]

        def answer():
            sock, _ = listener.accept()
            sock.recv(4096)
            sock.sendall(b"HTTP/1.1 404 Not Found\r\n\r\n")
            sock.close()
        threading.Thread(target=answer, daemon=True).start()
        with self.assertRaises(ws.WebSocketError):
            ws.connect("ws://127.0.0.1:{0}/room/x".format(port))
        listener.close()

    def test_a_bad_accept_key_raises(self):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]

        def answer():
            sock, _ = listener.accept()
            sock.recv(4096)
            sock.sendall(b"HTTP/1.1 101 Switching Protocols\r\n"
                         b"Sec-WebSocket-Accept: nope\r\n\r\n")
            sock.close()
        threading.Thread(target=answer, daemon=True).start()
        with self.assertRaises(ws.WebSocketError):
            ws.connect("ws://127.0.0.1:{0}/room/x".format(port))
        listener.close()

    def test_oversized_frame_is_refused(self):
        def script(sock):
            sock.sendall(bytes([0x82, 127]) + struct.pack(
                "!Q", ws.MAX_MESSAGE + 1))

        server = LoopbackServer(script)
        conn = ws.connect(server.url())
        with self.assertRaises(ws.WebSocketError):
            conn.recv_message()
        conn.close()

    def test_address_rules(self):
        self.assertEqual(ws._split_url("wss://a.example/room/x")[1:],
                         ("a.example", 443, "/room/x", "a.example"))
        self.assertEqual(ws._split_url("ws://h:8080/p?q=1")[2:],
                         (8080, "/p?q=1", "h:8080"))
        with self.assertRaises(ws.WebSocketError):
            ws._split_url("ftp://x/y")


if __name__ == "__main__":
    unittest.main()
