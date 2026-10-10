"""maya_voice.gate - the voice activity gate. Pure, stdlib.

A packet is sent when its level is above THRESHOLD, and for HANG packets
after the last such packet, so the tail of a word is not cut. Level is the
RMS of the samples on the int16 scale (0..32767).
"""

from array import array
import math

THRESHOLD = 250.0
HANG = 3


def rms(pcm):
    """The RMS level of a PCM s16 chunk. 0.0 for an empty one."""
    samples = array("h")
    usable = len(pcm) - (len(pcm) % 2)
    samples.frombytes(bytes(pcm[:usable]))
    if not samples:
        return 0.0
    total = 0
    for value in samples:
        total += value * value
    return math.sqrt(total / float(len(samples)))


class Gate(object):

    def __init__(self, threshold=THRESHOLD, hang=HANG):
        self.threshold = threshold
        self.hang = hang
        self.left = 0

    def feed(self, pcm):
        """True when this packet should be sent."""
        if rms(pcm) >= self.threshold:
            self.left = self.hang
            return True
        if self.left > 0:
            self.left -= 1
            return True
        return False

    def speaking(self, pcm):
        """True when this packet alone is loud enough (no hangover)."""
        return rms(pcm) >= self.threshold
