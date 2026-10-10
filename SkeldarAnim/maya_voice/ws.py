"""maya_voice.ws - a WebSocket client on the standard library (RFC 6455).

Maya's Python has no WebSocket package, and a dependency would ship in the
payload for one client. So this is the part of the protocol a client needs:

- the handshake (`connect`), with the accept key checked;
- every frame a client sends is masked, as the RFC requires;
- incoming fragments are joined, pings answered, a close answered and
  reported (`recv_message` returns the close frame to the caller);
- a message over MAX_MESSAGE is refused rather than read into memory.

Text in and out is UTF-8. Binary is bytes. Nothing is retried here: the
session decides when to reconnect.
"""

import base64
import hashlib
import os
import socket
import ssl
import struct
from urllib.parse import urlsplit

GUID = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
OP_CONT = 0x0
OP_TEXT = 0x1
OP_BIN = 0x2
OP_CLOSE = 0x8
OP_PING = 0x9
OP_PONG = 0xA
MAX_MESSAGE = 4 * 1024 * 1024
MAX_HANDSHAKE = 16 * 1024


class WebSocketError(Exception):
    """The connection failed, closed, or spoke something we refuse."""


def accept_key(key):
    """The Sec-WebSocket-Accept value the server must answer with."""
    digest = hashlib.sha1(key.encode("ascii") + GUID).digest()
    return base64.b64encode(digest).decode("ascii")


def mask(data, key):
    """XOR `data` with the 4-byte `key`, in one big-integer operation."""
    n = len(data)
    if n == 0:
        return b""
    pattern = (key * (n // 4 + 1))[:n]
    value = int.from_bytes(data, "big") ^ int.from_bytes(pattern, "big")
    return value.to_bytes(n, "big")


class Connection(object):
    """One open WebSocket. Created by `connect`; not for direct construction."""

    def __init__(self, sock, pending=b""):
        self.sock = sock
        self.buffer = bytearray(pending)
        self.closed = False

    # ------------------------------------------------------------ reading

    def _take(self, n):
        while len(self.buffer) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise WebSocketError("connection closed")
            self.buffer.extend(chunk)
        out = bytes(self.buffer[:n])
        del self.buffer[:n]
        return out

    def _frame(self):
        b0, b1 = self._take(2)
        fin = bool(b0 & 0x80)
        opcode = b0 & 0x0F
        masked = bool(b1 & 0x80)
        length = b1 & 0x7F
        if length == 126:
            (length,) = struct.unpack("!H", self._take(2))
        elif length == 127:
            (length,) = struct.unpack("!Q", self._take(8))
        if length > MAX_MESSAGE:
            raise WebSocketError("frame of {0} bytes refused".format(length))
        key = self._take(4) if masked else None
        payload = self._take(length) if length else b""
        if key is not None:
            payload = mask(payload, key)
        return fin, opcode, payload

    def recv_message(self):
        """(opcode, payload) of the next data or close message.

        Pings are answered here and never returned. A close frame is
        answered, marks the connection closed, and comes back as
        (OP_CLOSE, payload) so the caller can see why.
        """
        parts = []
        message_op = None
        total = 0
        while True:
            fin, opcode, payload = self._frame()
            if opcode == OP_PING:
                self._send(OP_PONG, payload)
                continue
            if opcode == OP_PONG:
                continue
            if opcode == OP_CLOSE:
                self.closed = True
                try:
                    self._send(OP_CLOSE, payload[:2])
                except (OSError, WebSocketError):
                    pass
                return OP_CLOSE, payload
            if opcode in (OP_TEXT, OP_BIN):
                if message_op is not None:
                    raise WebSocketError("new message inside a fragment")
                message_op = opcode
            elif opcode == OP_CONT:
                if message_op is None:
                    raise WebSocketError("continuation without a message")
            else:
                raise WebSocketError("unknown opcode {0}".format(opcode))
            total += len(payload)
            if total > MAX_MESSAGE:
                raise WebSocketError("message over {0} bytes".format(
                    MAX_MESSAGE))
            parts.append(payload)
            if fin:
                return message_op, b"".join(parts)

    # ------------------------------------------------------------ writing

    def _send(self, opcode, payload=b""):
        n = len(payload)
        head = bytearray([0x80 | opcode])
        if n < 126:
            head.append(0x80 | n)
        elif n < 65536:
            head.append(0x80 | 126)
            head.extend(struct.pack("!H", n))
        else:
            head.append(0x80 | 127)
            head.extend(struct.pack("!Q", n))
        key = os.urandom(4)
        head.extend(key)
        self.sock.sendall(bytes(head) + mask(payload, key))

    def send_text(self, text):
        self._send(OP_TEXT, text.encode("utf-8"))

    def send_binary(self, data):
        self._send(OP_BIN, bytes(data))

    def send_ping(self):
        self._send(OP_PING, b"")

    def close(self, code=1000):
        """Say goodbye if we can, then drop the socket. Never raises."""
        if not self.closed:
            self.closed = True
            try:
                self._send(OP_CLOSE, struct.pack("!H", code))
            except (OSError, WebSocketError):
                pass
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass


def _split_url(url):
    parts = urlsplit(url)
    secure = parts.scheme in ("wss", "https")
    if parts.scheme not in ("ws", "wss", "http", "https"):
        raise WebSocketError("not a WebSocket address: {0}".format(url))
    host = parts.hostname
    if not host:
        raise WebSocketError("no host in {0}".format(url))
    port = parts.port or (443 if secure else 80)
    path = parts.path or "/"
    if parts.query:
        path += "?" + parts.query
    hostport = host if parts.port is None else "{0}:{1}".format(host, port)
    return secure, host, port, path, hostport


def connect(url, timeout=10.0):
    """Open a WebSocket to `url`. Raises WebSocketError or OSError."""
    secure, host, port, path, hostport = _split_url(url)
    raw = socket.create_connection((host, port), timeout=timeout)
    try:
        if secure:
            context = ssl.create_default_context()
            raw = context.wrap_socket(raw, server_hostname=host)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        raw.sendall((
            "GET {0} HTTP/1.1\r\n"
            "Host: {1}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Key: {2}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "User-Agent: skeldar-voice\r\n\r\n"
        ).format(path, hostport, key).encode("ascii"))
        head = bytearray()
        while b"\r\n\r\n" not in head:
            chunk = raw.recv(4096)
            if not chunk:
                raise WebSocketError("closed during the handshake")
            head.extend(chunk)
            if len(head) > MAX_HANDSHAKE:
                raise WebSocketError("handshake too long")
        text, rest = bytes(head).split(b"\r\n\r\n", 1)
        lines = text.decode("latin-1").split("\r\n")
        status = lines[0].split(" ", 2)
        if len(status) < 2 or status[1] != "101":
            raise WebSocketError("handshake refused: {0}".format(lines[0]))
        headers = {}
        for line in lines[1:]:
            if ":" in line:
                name, value = line.split(":", 1)
                headers[name.strip().lower()] = value.strip()
        if headers.get("sec-websocket-accept") != accept_key(key):
            raise WebSocketError("bad Sec-WebSocket-Accept")
        raw.settimeout(None)
        try:
            raw.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        except OSError:
            pass
        return Connection(raw, pending=rest)
    except Exception:
        try:
            raw.close()
        except OSError:
            pass
        raise
