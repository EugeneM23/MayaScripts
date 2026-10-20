"""The live connection: a pure Protocol and a thin QtLink over QWebSocket.

Protocol (stdlib, testable without a socket):
    on open   - {"type": "hello", "since": N} first, then every queued send in order;
    a frame   - parsed by records.event; an ack drops its send from the outbox, an error naming a
                cid drops it too and is reported; a seq event and caught_up move `since`;
    close     - the next reconnect delay, 1, 2, 4, 8, 16, 30, 30 ... s (reset by an open);
    tick(now) - the text frame "ping" every PING_S while open (the server answers "pong" without
                waking); a socket that heard nothing for DEAD_S is "dead".

QtLink holds a QWebSocket to <server>/v1/ws with our User-Agent and the token, feeds the Protocol
and reconnects on a timer. Qt is imported only when a QtLink is made.
"""
import json
import time

from . import records

BACKOFF = (1, 2, 4, 8, 16, 30)
PING_S = 25
DEAD_S = 70
AGENT = "skeldar-chat/1"


def _ignore(*args):
    pass


class Protocol(object):
    def __init__(self, send=None, since=0, outbox=(), clock=time.monotonic):
        self.send = send
        self.since = int(since or 0)
        self.outbox = [dict(m) for m in outbox]
        self.clock = clock
        self.state = "closed"
        self.attempt = 0
        self.last_sent = 0.0
        self.last_heard = 0.0
        self.on_event = _ignore
        self.on_ack = _ignore
        self.on_error = _ignore
        self.on_resync = _ignore
        self.on_caught_up = _ignore
        self.on_state = _ignore

    def _set(self, state):
        if state != self.state:
            self.state = state
            self.on_state(state)

    def _out(self, msg):
        text = msg if isinstance(msg, str) else json.dumps(msg)
        self.send(text)
        self.last_sent = self.clock()

    # ---------------------------------------------------------------- the socket's life
    def connecting(self):
        self._set("connecting")

    def opened(self):
        self.attempt = 0
        self.last_heard = self.clock()
        self._set("open")
        self._out({"type": "hello", "since": self.since})
        for msg in list(self.outbox):
            self._out(msg)

    def closed(self):
        delay = BACKOFF[min(self.attempt, len(BACKOFF) - 1)]
        self.attempt += 1
        self._set("closed")
        return delay

    # ---------------------------------------------------------------- what goes out
    def queue(self, msg):
        """A send: kept until its ack, sent now when open."""
        if not any(m.get("cid") == msg.get("cid") for m in self.outbox):
            self.outbox.append(dict(msg))
        if self.state == "open":
            self._out(msg)

    def push(self, msg):
        """An edit, delete, read or typing: sent now when open, else False (never kept)."""
        if self.state != "open":
            return False
        self._out(msg)
        return True

    def tick(self, now=None):
        """"ping" when due, "dead" when the socket went quiet, else None."""
        if self.state != "open":
            return None
        now = self.clock() if now is None else now
        if now - self.last_heard >= DEAD_S:
            return "dead"
        if now - self.last_sent >= PING_S:
            self._out("ping")
            return "ping"
        return None

    # ---------------------------------------------------------------- what comes in
    def received(self, text):
        self.last_heard = self.clock()
        if text == "pong":
            return
        try:
            doc = json.loads(text)
        except ValueError:
            return
        e = records.event(doc)
        if e is None:
            return
        kind = e["kind"]
        if kind == "ack":
            self.outbox = [m for m in self.outbox if m.get("cid") != e["cid"]]
            self.on_ack(e)
        elif kind == "error":
            if e.get("cid"):
                self.outbox = [m for m in self.outbox if m.get("cid") != e["cid"]]
            self.on_error(e)
        elif kind == "resync":
            self.on_resync()
        elif kind == "caught_up":
            self.since = max(self.since, e["seq"])
            self.on_caught_up(e["seq"])
        else:
            if "seq" in e:
                self.since = max(self.since, e["seq"])
            self.on_event(e)


def ws_url(server):
    base = server.rstrip("/")
    if base.startswith("https://"):
        return "wss://" + base[len("https://"):] + "/v1/ws"
    if base.startswith("http://"):
        return "ws://" + base[len("http://"):] + "/v1/ws"
    return base + "/v1/ws"


class QtLink(object):
    """The Protocol on a QWebSocket, reconnecting by itself until stop()."""

    TICK_MS = 1000

    def __init__(self, server, token, protocol):
        from PySide6 import QtCore, QtNetwork, QtWebSockets
        self._core, self._net = QtCore, QtNetwork
        self.url = ws_url(server)
        self.token = token
        self.protocol = protocol
        protocol.send = self._send
        self.socket = QtWebSockets.QWebSocket()
        self.socket.connected.connect(self._connected)
        self.socket.disconnected.connect(self._disconnected)
        self.socket.textMessageReceived.connect(self._text)
        self.running = False
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.TICK_MS)
        self.timer.timeout.connect(self._tick)
        self.again = QtCore.QTimer()
        self.again.setSingleShot(True)
        self.again.timeout.connect(self._open)

    @property
    def connected(self):
        return self.protocol.state == "open"

    def start(self):
        if self.running:
            return
        self.running = True
        self.timer.start()
        self._open()

    def stop(self):
        self.running = False
        self.timer.stop()
        self.again.stop()
        try:
            self.socket.close()
        except RuntimeError:
            pass

    def _open(self):
        if not self.running:
            return
        req = self._net.QNetworkRequest(self._core.QUrl(self.url))
        req.setRawHeader(b"User-Agent", AGENT.encode())
        req.setRawHeader(b"Authorization", ("Bearer " + self.token).encode())
        self.protocol.connecting()
        self.socket.open(req)

    def _send(self, text):
        self.socket.sendTextMessage(text)

    def _connected(self):
        self.protocol.opened()

    def _disconnected(self):
        delay = self.protocol.closed()
        if self.running:
            self.again.start(int(delay * 1000))

    def _text(self, text):
        self.protocol.received(text)

    def _tick(self):
        if self.protocol.state == "connecting" and self.socket.state() == self._net.QAbstractSocket.UnconnectedState:
            self._disconnected()
            return
        if self.protocol.tick() == "dead":
            self.socket.abort()
