"""The Graph Editor's picture with its flat background taken out. numpy only.

The curve area of Maya 2027's Graph Editor is a QOpenGLWindow that clears
OPAQUE whatever alpha its background colour carries (measured 2026-09-30:
alpha 255 on every pixel at a background alpha of 0). So the transparency
is made here, from the picture: a pixel's alpha is how far it stands from
the background colour, and its colour stays exactly as Maya drew it.

Straight alpha: `alpha = table[max over channels |P - K|]`, the table rising
from 0 to 255 over `SOFT` levels. The background is 0; a curve, a key, a
number, the time marker are opaque; the grid (23 levels off the default
background) about 82 %. An anti-aliased curve pixel keeps the K it was
blended with - which is how the curve looks in the Graph Editor itself.

The background is TWO tones (measured on the animator's Graph Editor,
2026-09-30): 64 inside the playback range, 55 outside it, each near half the
frame. Keyed against 64 alone the 55 stood 32 % opaque - grey panels over a
light viewport - so every colour covering `BACKGROUND_SHARE` of the frame is
a key, and a pixel's alpha is its distance from the NEAREST one.

Speed, measured in Maya's numpy at 1850x1067: lookup tables on every
channel 44.5 ms, this uint8 version 19.7 ms on one thread and 5.7 ms on
four - numpy lets the GIL go, so the bands really run side by side.
"""

from concurrent.futures import ThreadPoolExecutor

import numpy as np

SOFT = 28          # levels off the background at which a pixel is opaque
BANDS = 4          # horizontal bands keyed side by side
SAMPLE_STEP = 7    # every 7th pixel both ways finds the background
BACKGROUND_SHARE = 0.05   # a colour covering this much of a frame is one
MOST_KEYS = 2             # background tones found in one frame


def alpha_table(soft=SOFT):
    """Channel distance 0..255 -> alpha 0..255, as uint8."""
    levels = np.arange(256, dtype=np.int32)
    return np.minimum(levels * 255 // max(1, int(soft)), 255).astype(np.uint8)


def make_pool(workers=BANDS):
    """The keying threads. Made once a session by the mode."""
    return ThreadPoolExecutor(max_workers=workers,
                              thread_name_prefix="skeldarGraphKey")


def backgrounds(bgra, step=SAMPLE_STEP, share=BACKGROUND_SHARE,
                most=MOST_KEYS):
    """The background tones as [(r, g, b), ...], commonest first: every
    colour covering `share` of a sparse sample, at most `most`, and always
    at least the commonest.

    Read off the picture rather than a preference, so the classic Graph
    Editor and a colour the animator changed are both right, and nothing
    of theirs is written.
    """
    sample = np.ascontiguousarray(bgra[::step, ::step, :3])
    sample = sample.reshape(-1, 3).astype(np.uint32)
    packed = (sample[:, 2] << 16) | (sample[:, 1] << 8) | sample[:, 0]
    values, counts = np.unique(packed, return_counts=True)
    order = np.argsort(-counts, kind="stable")
    found = []
    for index in order[:max(1, most)]:
        if found and counts[index] < share * packed.size:
            break
        value = int(values[index])
        found.append(((value >> 16) & 255, (value >> 8) & 255, value & 255))
    return found


def background(bgra, step=SAMPLE_STEP):
    """The commonest background tone as (r, g, b)."""
    return backgrounds(bgra, step)[0]


def _as_keys(keys):
    """One (r, g, b) or a list of them -> a list of B G R uint8 triples."""
    if len(keys) == 3 and all(isinstance(v, (int, np.integer)) for v in keys):
        keys = [keys]
    return [(np.uint8(k[2]), np.uint8(k[1]), np.uint8(k[0])) for k in keys]


def _band(src, out, keys_bgr, table, y0, y1):
    part = src[y0:y1]
    nearest = None
    for key_bgr in keys_bgr:
        dist = None
        for channel, k in enumerate(key_bgr):
            plane = part[..., channel]
            d = np.maximum(plane, k) - np.minimum(plane, k)
            dist = d if dist is None else np.maximum(dist, d)
        nearest = dist if nearest is None else np.minimum(nearest, dist)
    out[y0:y1, :, :3] = part[..., :3]
    out[y0:y1, :, 3] = table[nearest]


def key_out(bgra, keys, table, pool=None, bands=BANDS):
    """A copy of `bgra` - (h, w, 4) uint8, the bytes B G R A as QImage's
    ARGB32 lays them out - whose alpha says how far each pixel stands from
    the nearest of `keys` (one (r, g, b) or a list). The input is not
    written.
    """
    height = bgra.shape[0]
    out = np.empty(bgra.shape, np.uint8)
    keys_bgr = _as_keys(keys)
    if pool is None or bands <= 1 or height < bands:
        _band(bgra, out, keys_bgr, table, 0, height)
        return out
    step = -(-height // bands)
    jobs = [pool.submit(_band, bgra, out, keys_bgr, table, y,
                        min(height, y + step))
            for y in range(0, height, step)]
    for job in jobs:
        job.result()
    return out
