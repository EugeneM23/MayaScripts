"""maya_voice.jitter - what the playback side holds. Pure, stdlib.

- `JitterBuffer`: one per sender. Packets are kept by sequence number and
  handed out in order, once `depth` of them are waiting (the start). A gap
  inside the window is played as silence; a packet that arrives after its
  slot has been played is dropped; a jump of more than RESET packets starts
  the buffer over (the sender restarted).
- `LatestFrame`: the newest video frame of one sender.
- `mix`: the PCM of several senders summed and clipped to s16.
"""

from array import array

from maya_voice import protocol

RESET = 500
DEPTH = 2
S16_MIN = -32768
S16_MAX = 32767


def signed_gap(seq, base):
    """How far `seq` is after `base` on the 32-bit counter, negative if before."""
    gap = (seq - base) & 0xFFFFFFFF
    return gap - 0x100000000 if gap >= 0x80000000 else gap


class JitterBuffer(object):

    def __init__(self, depth=DEPTH, packet_bytes=protocol.PACKET_BYTES):
        self.depth = depth
        self.packet_bytes = packet_bytes
        self.silence = bytes(packet_bytes)
        self.expected = None
        self.items = {}
        self.started = False

    def push(self, seq, data):
        """Keep one packet. False when it is too late to play."""
        if self.expected is None:
            self.expected = seq
        gap = signed_gap(seq, self.expected)
        if gap < -RESET or gap > RESET:
            #  far behind or far ahead: the sender started again
            self.reset(seq)
            gap = 0
        elif not self.items and gap > self.depth:
            #  the sender was silent and talks again: play from here, do not
            #  wait for the packets of the silence
            self.reset(seq)
            gap = 0
        if gap < 0:
            return False                       # its slot was already played
        self.items[seq] = data
        return True

    def reset(self, seq=None):
        self.items.clear()
        self.expected = seq
        self.started = False

    def pop(self):
        """The next packet for playback, the silence for a gap, or None.

        None means nothing is due: the buffer is still filling, or it has run
        dry and the caller should play nothing for this sender.
        """
        if self.expected is None:
            return None
        if not self.started:
            if len(self.items) < self.depth:
                return None
            self.started = True
        if self.expected in self.items:
            data = self.items.pop(self.expected)
            self.expected = (self.expected + 1) & 0xFFFFFFFF
            return data
        if len(self.items) >= self.depth:
            #  the packet is missing and later ones are waiting: a gap
            self.expected = (self.expected + 1) & 0xFFFFFFFF
            return self.silence
        return None

    def waiting(self):
        return len(self.items)


class LatestFrame(object):
    """The newest video frame of one sender; an older one never replaces it."""

    def __init__(self):
        self.seq = None
        self.data = None

    def put(self, seq, data):
        if self.seq is None or signed_gap(seq, self.seq) > 0:
            self.seq = seq
            self.data = data
            return True
        return False

    def take(self):
        return self.data


def mix(chunks, size):
    """Sum the PCM chunks sample by sample, clipped. `size` bytes out.

    Chunks shorter or longer than `size` are cut or padded with silence, so
    one odd packet never breaks the playback clock.
    """
    total = [0] * (size // 2)
    count = 0
    for chunk in chunks:
        if not chunk:
            continue
        usable = min(len(chunk), size)
        usable -= usable % 2                    # whole samples only
        samples = array("h")
        samples.frombytes(bytes(chunk[:usable]))
        for i, value in enumerate(samples):
            if i < len(total):
                total[i] += value
        count += 1
    if not count:
        return bytes(size)
    out = array("h", [max(S16_MIN, min(S16_MAX, v)) for v in total])
    raw = out.tobytes()
    return raw + bytes(size - len(raw))
