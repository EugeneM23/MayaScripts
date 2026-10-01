"""Which frames of a trail to compute, and in what order. Pure.

The engine (engine.py) owns the scene; this owns the arithmetic it decides
with, so the decisions are testable without a Maya.
"""

import math

#  frames walked in one slice at most, whatever the measured cost says
MAX_BATCH = 24


def trail_range(mode, playback, current, around, animation):
    """(start, end) whole frames of a trail.

    "playback": the playback range; "around": `current` ± `around`, inside
    the animation range. A fractional range snaps outward (trap 50's lesson:
    the time slider stops on fractions)."""
    if mode == "around":
        lo = max(math.floor(animation[0]), math.floor(current - around))
        hi = min(math.ceil(animation[1]), math.ceil(current + around))
        return int(lo), int(max(hi, lo))
    lo, hi = math.floor(playback[0]), math.ceil(playback[1])
    return int(lo), int(max(hi, lo))


def frames_of(span):
    return list(range(span[0], span[1] + 1))


def changed_frames(before, after, tol=1e-9):
    """Frames whose value differs between two {frame: value} samples."""
    out = set()
    for frame in set(before) | set(after):
        a, b = before.get(frame), after.get(frame)
        if a is None or b is None or abs(a - b) > tol:
            out.add(frame)
    return out


def nearest_first(dirty, current):
    """Dirty frames by distance from the current one, the earlier on a tie."""
    return sorted(dirty, key=lambda f: (abs(f - current), f))


def budget(per_frame_ms, slice_ms, return_ms):
    """How many frames fit a slice that also pays the walk back."""
    if per_frame_ms <= 0:
        return MAX_BATCH
    n = int((slice_ms - return_ms) // per_frame_ms)
    return max(1, min(MAX_BATCH, n))


def rerange(points, span):
    """(points kept inside `span`, frames of `span` with no point)."""
    kept = {f: p for f, p in points.items() if span[0] <= f <= span[1]}
    return kept, set(frames_of(span)) - set(kept)


def ordered_points(points, span):
    """The trail's points frame by frame; a frame not yet computed takes the
    nearest known one (the earlier on a tie), so the line never jumps."""
    known = sorted(points)
    out = []
    for frame in frames_of(span):
        if frame in points:
            out.append(points[frame])
        elif known:
            near = min(known, key=lambda f: (abs(f - frame), f))
            out.append(points[near])
        else:
            out.append((0.0, 0.0, 0.0))
    return out
