"""maya_voice.session - one connection to one room. Stdlib, no Qt, no cmds.

Two threads do the socket work: a reader turns what the server sends into
events, a writer sends what the main thread queued. The main thread never
waits on the network: it calls `drain()` on its timer and gets the events
that arrived since the last call.

Events (tuples):
    ('control', msg)                  a control message, parsed
    ('media', kind, sender, seq, data)
    ('closed', reason)                the connection is gone
    ('rooms', list)                   the lobby answer (see fetch_rooms_async)
    ('rooms_error', text)

The outbox is bounded. A full outbox drops its oldest media frame, so a slow
link costs audio quality, never a frozen Maya. Control messages are never
dropped.
"""

import json
import queue
import threading
import urllib.request

from maya_voice import protocol
from maya_voice import ws

OUTBOX = 64
PING_EVERY = 20.0
CONTROL_WAIT = 2.0


def room_url(server, room):
    """The WebSocket address of a room on the server the animator typed."""
    base = _base(server)
    scheme = "wss" if base.startswith("https://") else "ws"
    host = base.split("://", 1)[1]
    return "{0}://{1}/room/{2}".format(scheme, host, room)


def rooms_url(server):
    return _base(server) + "/rooms"


def _base(server):
    base = str(server or "").strip().rstrip("/")
    if not base.startswith(("https://", "http://", "wss://", "ws://")):
        base = "https://" + base
    base = base.replace("wss://", "https://").replace("ws://", "http://")
    return base


def fetch_rooms(server, timeout=4.0):
    """The lobby list: [{room, members:[names]}]. Raises on failure."""
    with urllib.request.urlopen(rooms_url(server), timeout=timeout) as reply:
        data = json.loads(reply.read().decode("utf-8"))
    rooms = data.get("rooms") if isinstance(data, dict) else None
    if not isinstance(rooms, list):
        raise ValueError("the lobby answered without a room list")
    return rooms


def fetch_rooms_async(server, inbox):
    """Fetch the lobby on a thread; the answer goes to `inbox` as an event."""
    def run():
        try:
            inbox.put(("rooms", fetch_rooms(server)))
        except Exception as exc:                         # noqa: BLE001
            inbox.put(("rooms_error", str(exc)))
    thread = threading.Thread(target=run, name="skeldar-voice-lobby")
    thread.daemon = True
    thread.start()
    return thread


class Session(object):
    """A connection to one room. `connector` makes the socket (tests inject)."""

    def __init__(self, connector=None):
        self.connector = connector or ws.connect
        self.conn = None
        self.inbox = queue.Queue()
        self.outbox = queue.Queue(maxsize=OUTBOX)
        self.alive = False
        self.threads = []

    # --------------------------------------------------------------- life

    def open(self, url, name):
        """Connect and say who we are. Raises what the connector raises."""
        conn = self.connector(url)
        self.conn = conn
        self.alive = True
        reader = threading.Thread(target=self._read, args=(conn,),
                                  name="skeldar-voice-read")
        writer = threading.Thread(target=self._write, args=(conn,),
                                  name="skeldar-voice-write")
        reader.daemon = True
        writer.daemon = True
        self.threads = [reader, writer]
        reader.start()
        writer.start()
        self.send_control("join", name=protocol.clean_name(name))

    def close(self):
        """Leave the room. Safe to call twice; the events stop."""
        if not self.alive and self.conn is None:
            return
        self.alive = False
        try:
            self.outbox.put_nowait(None)
        except queue.Full:
            pass
        if self.conn is not None:
            self.conn.close()
        self.conn = None

    # ------------------------------------------------------------ sending

    def send_control(self, kind, **fields):
        self._put_control(("text", protocol.control(kind, **fields)))

    def send_state(self, muted, deafened, sharing):
        self.send_control("state", muted=bool(muted),
                          deafened=bool(deafened), sharing=bool(sharing))

    def send_audio(self, seq, payload):
        self._put_media(("bin", protocol.pack_media(
            protocol.TYPE_AUDIO, 0, seq, payload)))

    def send_video(self, seq, payload):
        self._put_media(("bin", protocol.pack_media(
            protocol.TYPE_VIDEO, 0, seq, payload)))

    def _put_control(self, item):
        try:
            self.outbox.put(item, timeout=CONTROL_WAIT)
        except queue.Full:
            self.inbox.put(("closed", "the link is too slow"))

    def _put_media(self, item):
        try:
            self.outbox.put_nowait(item)
        except queue.Full:
            try:
                self.outbox.get_nowait()          # the oldest media goes
            except queue.Empty:
                pass
            try:
                self.outbox.put_nowait(item)
            except queue.Full:
                pass

    # ------------------------------------------------------------ threads

    def _read(self, conn):
        try:
            while self.alive:
                opcode, payload = conn.recv_message()
                if opcode == ws.OP_CLOSE:
                    reason = payload[2:].decode("utf-8", "replace") \
                        if len(payload) > 2 else "closed by the server"
                    self.inbox.put(("closed", reason or "closed"))
                    break
                if opcode == ws.OP_TEXT:
                    try:
                        msg = protocol.parse_control(payload.decode("utf-8"))
                    except ValueError:
                        continue
                    self.inbox.put(("control", msg))
                elif opcode == ws.OP_BIN:
                    try:
                        kind, sender, seq, data = protocol.unpack_media(payload)
                    except ValueError:
                        continue
                    self.inbox.put(("media", kind, sender, seq, data))
        except Exception as exc:                          # noqa: BLE001
            if self.alive:
                self.inbox.put(("closed", str(exc) or exc.__class__.__name__))
        finally:
            self.alive = False

    def _write(self, conn):
        try:
            while True:
                try:
                    item = self.outbox.get(timeout=PING_EVERY)
                except queue.Empty:
                    conn.send_ping()
                    continue
                if item is None:
                    break
                kind, data = item
                if kind == "text":
                    conn.send_text(data)
                else:
                    conn.send_binary(data)
        except Exception as exc:                          # noqa: BLE001
            if self.alive:
                self.inbox.put(("closed", str(exc) or exc.__class__.__name__))
        finally:
            self.alive = False

    # ------------------------------------------------------------ draining

    def drain(self):
        """Every event that arrived since the last call, oldest first."""
        events = []
        while True:
            try:
                events.append(self.inbox.get_nowait())
            except queue.Empty:
                return events
