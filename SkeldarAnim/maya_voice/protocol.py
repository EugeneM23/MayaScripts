"""maya_voice.protocol - the wire format. Pure, stdlib.

Control messages are text frames carrying one JSON object with a field `t`.
Media messages are binary frames: a 7-byte header then the payload.

    header  !BHI   type ('A' audio, 'V' video), sender id, sequence
    audio   PCM s16le, 16 kHz, mono, 60 ms per packet (1920 bytes)
    video   one JPEG

The server rewrites the sender id from the socket's own id (bytes 1-2), so a
member cannot send as somebody else. Spec: docs/superpowers/specs/
2026-10-10-voice-screen-design.md.
"""

import json
import re
import struct

HEADER = struct.Struct("!BHI")
TYPE_AUDIO = ord("A")
TYPE_VIDEO = ord("V")

RATE = 16000
SAMPLE_BYTES = 2
PACKET_MS = 60
PACKET_SAMPLES = RATE * PACKET_MS // 1000          # 960
PACKET_BYTES = PACKET_SAMPLES * SAMPLE_BYTES        # 1920

MAX_MESSAGE = 2 * 1024 * 1024
MAX_MEMBERS = 30
NAME_MAX = 24
ROOM_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")


def pack_media(kind, sender, seq, payload):
    """One binary frame: the header, then the payload."""
    if kind not in (TYPE_AUDIO, TYPE_VIDEO):
        raise ValueError("unknown media type {0!r}".format(kind))
    return HEADER.pack(kind, sender & 0xFFFF, seq & 0xFFFFFFFF) + payload


def unpack_media(data):
    """(kind, sender, seq, payload) from one binary frame. Refuses the rest."""
    if len(data) < HEADER.size:
        raise ValueError("media frame too short: {0} bytes".format(len(data)))
    kind, sender, seq = HEADER.unpack_from(data)
    if kind not in (TYPE_AUDIO, TYPE_VIDEO):
        raise ValueError("unknown media type {0!r}".format(kind))
    return kind, sender, seq, bytes(data[HEADER.size:])


def control(kind, **fields):
    """A control message as text: {"t": kind, ...fields}."""
    body = dict(fields)
    body["t"] = kind
    return json.dumps(body, separators=(",", ":"), ensure_ascii=False)


def parse_control(text):
    """The dict of a control message. Raises ValueError for anything else."""
    msg = json.loads(text)
    if not isinstance(msg, dict) or not isinstance(msg.get("t"), str):
        raise ValueError("not a control message")
    return msg


def clean_name(text):
    """A display name: whitespace collapsed, at most NAME_MAX characters.

    An empty name becomes «Guest» so the roster never shows a blank line.
    """
    name = " ".join(str(text or "").split())
    if len(name) > NAME_MAX:
        name = name[:NAME_MAX].rstrip()
    return name or "Guest"


def clean_room(text):
    """The room name as the server accepts it, or None.

    Spaces become dashes and letters are lowercased, so «Layout Room» is
    «layout-room». Anything the server would refuse is refused here first.
    """
    name = "-".join(str(text or "").strip().lower().split())
    return name if ROOM_RE.match(name) else None
