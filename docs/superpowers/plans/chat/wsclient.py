"""A small stdlib WebSocket client for the chat verify (text frames, masked, no extensions)."""
import base64
import json
import os
import socket
import ssl
import struct
import time
import urllib.parse


class WS(object):
    def __init__(self, url, token, timeout=10):
        parts = urllib.parse.urlparse(url)
        host = parts.hostname
        port = parts.port or (443 if parts.scheme == "wss" else 80)
        raw = socket.create_connection((host, port), timeout=timeout)
        if parts.scheme == "wss":
            raw = ssl.create_default_context().wrap_socket(raw, server_hostname=host)
        self.sock = raw
        key = base64.b64encode(os.urandom(16)).decode()
        head = ("GET %s HTTP/1.1\r\nHost: %s\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n"
                "Authorization: Bearer %s\r\n\r\n" % (parts.path or "/", host, key, token))
        self.sock.sendall(head.encode())
        self.buf = b""
        while b"\r\n\r\n" not in self.buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise IOError("closed during the handshake")
            self.buf += chunk
        answer, self.buf = self.buf.split(b"\r\n\r\n", 1)
        self.status = int(answer.split(b" ")[1])
        if self.status != 101:
            raise IOError("handshake answered %d: %r" % (self.status, answer[:300]))

    def _frame(self, opcode, data):
        mask = os.urandom(4)
        n = len(data)
        if n < 126:
            head = struct.pack("!BB", 0x80 | opcode, 0x80 | n)
        elif n < 65536:
            head = struct.pack("!BBH", 0x80 | opcode, 0x80 | 126, n)
        else:
            head = struct.pack("!BBQ", 0x80 | opcode, 0x80 | 127, n)
        self.sock.sendall(head + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def send_text(self, text):
        self._frame(0x1, text.encode())

    def send(self, obj):
        self.send_text(json.dumps(obj))

    def _read(self, n):
        while len(self.buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise IOError("closed")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def recv_text(self, timeout=5):
        self.sock.settimeout(timeout)
        while True:
            b1, b2 = self._read(2)
            opcode, n = b1 & 0x0F, b2 & 0x7F
            if n == 126:
                n = struct.unpack("!H", self._read(2))[0]
            elif n == 127:
                n = struct.unpack("!Q", self._read(8))[0]
            mask = self._read(4) if b2 & 0x80 else None
            payload = self._read(n)
            if mask:
                payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
            if opcode == 0x8:
                raise IOError("closed by the server")
            if opcode == 0x9:
                self._frame(0xA, payload)
                continue
            if opcode in (0x0, 0x1):
                return payload.decode()

    def events(self, seconds):
        """Every JSON event that arrives within `seconds`."""
        out = []
        deadline = time.time() + seconds
        while time.time() < deadline:
            try:
                text = self.recv_text(max(0.05, deadline - time.time()))
            except (socket.timeout, ssl.SSLError):
                break
            if text != "pong":
                out.append(json.loads(text))
        return out

    def until(self, test, seconds=5):
        """The first event `test` accepts, and everything seen before it."""
        seen = []
        deadline = time.time() + seconds
        while time.time() < deadline:
            try:
                text = self.recv_text(max(0.05, deadline - time.time()))
            except (socket.timeout, ssl.SSLError):
                break
            if text == "pong":
                continue
            event = json.loads(text)
            if test(event):
                return event, seen
            seen.append(event)
        return None, seen

    def close(self):
        try:
            self._frame(0x8, struct.pack("!H", 1000))
        except Exception:
            pass
        self.sock.close()
