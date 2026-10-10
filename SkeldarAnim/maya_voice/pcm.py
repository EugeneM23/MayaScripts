"""maya_voice.pcm - turning a device's PCM into ours and back. Pure, stdlib.

Ours is 16 kHz mono s16. A device that will not open at that format gives its
own preferred one. On this studio's machines that is 48 kHz, two channels,
Float32 (measured 2026-10-10 in mayapy), so both sample kinds are converted:
'h' (Int16) and 'f' (Float32, full scale 1.0). The device's rate must be an
integer multiple of 16 kHz for the conversion to stay exact; anything else is
refused by `ratio_for` and the panel says so.
"""

from array import array

from maya_voice import protocol

#  bytes per sample -> the array type that reads it
KINDS = {2: "h", 4: "f"}


def kind_for(sample_bytes):
    """The array type for a device's sample size, or None when unsupported."""
    return KINDS.get(sample_bytes)


def ratio_for(device_rate, device_channels, sample_bytes):
    """The integer rate ratio, or None when the format cannot be converted.

    Only Int16 and Float32 devices with one or two channels are converted; the
    ratio is device_rate / 16000 and must be a whole number.
    """
    if sample_bytes not in KINDS:
        return None
    if device_channels not in (1, 2):
        return None
    if not device_rate or device_rate % protocol.RATE:
        return None
    return device_rate // protocol.RATE


def _to_s16(value):
    return max(-32768, min(32767, int(round(value * 32767.0))))


def to_ours(data, channels, ratio, kind="h"):
    """Mono s16 at 16 kHz from interleaved samples at `ratio` times that rate.

    `kind` is the device's array type ('h' or 'f'). Stereo is averaged to
    mono; the mono samples are averaged in groups of `ratio` (a plain low-pass
    before the decimation).
    """
    width = array(kind).itemsize
    usable = len(data) - (len(data) % (width * channels))
    samples = array(kind)
    samples.frombytes(bytes(data[:usable]))
    if kind == "f":
        samples = array("h", [_to_s16(v) for v in samples])
    if channels == 2:
        mono = array("h", [
            (samples[i] + samples[i + 1]) // 2
            for i in range(0, len(samples) - 1, 2)])
    else:
        mono = samples
    out = array("h")
    for start in range(0, len(mono) - ratio + 1, ratio):
        group = mono[start:start + ratio]
        out.append(sum(group) // ratio)
    return out.tobytes()


def from_ours(data, channels, ratio, kind="h"):
    """Interleaved samples at `ratio` times 16 kHz from mono s16 at 16 kHz.

    Each sample is repeated `ratio` times and copied to every channel, in the
    device's own sample type ('h' or 'f').
    """
    samples = array("h")
    samples.frombytes(bytes(data[:len(data) - (len(data) % 2)]))
    if kind == "f":
        out = array("f")
        for value in samples:
            for _ in range(ratio):
                for _ in range(channels):
                    out.append(value / 32767.0)
        return out.tobytes()
    out = array("h")
    for value in samples:
        for _ in range(ratio):
            for _ in range(channels):
                out.append(value)
    return out.tobytes()
