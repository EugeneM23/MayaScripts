"""Tools > Floor, the pure half: how far the body must move for the lower foot to stand on the floor on
every frame, which frames have nothing to stand on, and which of them are worth a key. No Maya, no
numpy - one value a frame.

docs/superpowers/specs/2026-11-02-tools-floor-design.md
"""

DOWN_TOL = 2.5        # cm: a foot within this of its own nearby low is DOWN - said on the line, and
                      # what Walk Builder calls a contact
FLOOR_DEAD = 0.2      # cm: nothing to do - the feet already stand on the floor
KEY_TOL = 0.02        # cm: a frame this near the line between the keys kept around it needs none of its own
DOWN_WINDOW = 8       # frames: "nearby" for a local low - a stance is some ten frames at 24-30 fps
AIR_TOL = 8.0         # cm: BOTH feet this far over their own nearby low is a flight, and nothing
                      # to stand the body on (a swing clears the floor by 10-20 cm at a walk, and a
                      # stance sunk less than this is still a stance)
AXIS_DEAD = 1e-4      # cm: a translate channel this still over every key is not keyed at all
SIDES = ("l", "r")


def down_frames(low, tol=DOWN_TOL, window=DOWN_WINDOW):
    """The frames this foot is down, from {frame: how far above the floor it is}: within `tol` of its
    own lowest NEARBY - the least it reaches inside `window` frames either side.

    Measured against the foot itself, never against the floor, because a take whose character floats
    15 cm up has no point near y = 0 and is the very take this tool is for. And measured LOCALLY, not
    over the whole span: one stance sunk 6 cm into the floor is the deepest the foot ever goes, and
    against that lowest every clean stance elsewhere reads as 6 cm of air and stops being a contact -
    the body would then be carried 6 cm down for the length of the take (measured, 2026-11-02). A
    window of some ten frames is a stance; much longer and a sunk stance poisons a clean one again,
    much shorter and the slow middle of a swing starts reading as a contact."""
    if not low:
        return []
    frames = sorted(low)
    out = []
    for i, f in enumerate(frames):
        near = frames[max(0, i - window):i + window + 1]
        if low[f] - min(low[g] for g in near) <= tol:
            out.append(f)
    return out


def airborne(low, tol=AIR_TOL, window=DOWN_WINDOW):
    """The frames with nothing to stand the body on: EVERY foot more than `tol` above its own nearby
    low (a flight, a jump). `low` is {side: {frame: its height}}.

    Why a frame is skipped only when both feet are that high, and not whenever a foot is off its own
    low: inside one stance the body may dip, and the foot goes down with it - so the clean half of
    that stance stands centimetres above the sunk half's low while being just as planted (measured
    2026-11-02: a 6 cm dip read the rest of its own stance as air, and the body was carried 6 cm down
    for the length of the take). A planted foot a few centimetres off its own low is still the thing
    the body stands on; only a foot a swing's height up is not."""
    frames = sorted(set(f for rows in low.values() for f in rows))
    out = []
    for f in frames:
        if all(_over(rows, f, window) > tol for rows in low.values() if f in rows):
            out.append(f)
    return out


def _over(rows, frame, window):
    """How far above its own nearby low this foot stands at `frame`."""
    frames = sorted(rows)
    i = frames.index(frame)
    near = frames[max(0, i - window):i + window + 1]
    return rows[frame] - min(rows[g] for g in near)


def wanted(low, skip=()):
    """{frame: the centimetres the body must move (+ up)}: minus the LOWEST foot's height, frame by
    frame, so nothing is left under the floor and the lowest point stands on it. `low` is
    {side: {frame: its height}}; a frame of `skip` (a flight: `airborne`) is left out and the curve
    runs between its neighbours.

    Where both feet are down and disagree (uneven ground), the lower one decides and the other is
    left above the floor: one vertical offset cannot put two feet at two heights, and a foot ABOVE
    the floor is the safe direction."""
    out = {}
    away = set(skip)
    for side, rows in low.items():
        for f, height in rows.items():
            if f in away:
                continue
            if f not in out or -height > out[f]:
                out[f] = -height
    return out


def keys_for(want, tol=KEY_TOL):
    """The frames of `want` worth a key: its ends, the ends of every run of frames, and inside a run
    the frames the curve needs to stay within `tol` of what every frame asks - so a still contact
    costs two keys and a sinking one follows the foot. The bound HOLDS: each kept stretch is split at
    its own worst frame until none is further than `tol` from the line between its ends (a greedy
    walk only compares with the key behind it, and lets the error past the tolerance)."""
    frames = sorted(want)
    if len(frames) <= 2:
        return frames
    runs, run = [], [frames[0]]
    for f in frames[1:]:
        if f == run[-1] + 1:
            run.append(f)
        else:
            runs.append(run)
            run = [f]
    runs.append(run)
    out = []
    for run in runs:
        out.extend(_thinned(want, run, tol))
    return out


def _thinned(want, run, tol):
    """`run`'s ends plus the fewest frames inside it that keep every frame within `tol` of the line
    between the keys around it (Douglas-Peucker, iterative)."""
    if len(run) <= 2:
        return list(run)
    kept = [0, len(run) - 1]
    todo = [(0, len(run) - 1)]
    while todo:
        a, b = todo.pop()
        if b - a < 2:
            continue
        ya, yb = want[run[a]], want[run[b]]
        span = float(run[b] - run[a])
        worst, at = 0.0, None
        for i in range(a + 1, b):
            line = ya + (yb - ya) * (run[i] - run[a]) / span if span else ya
            off = abs(want[run[i]] - line)
            if off > worst:
                worst, at = off, i
        if at is not None and worst > tol:
            kept.append(at)
            todo.extend(((a, at), (at, b)))
    return [run[i] for i in sorted(kept)]


def refusal(want, start, end, dead=FLOOR_DEAD):
    """Why the press changes nothing, or None."""
    if not want:
        return ("both feet are in the air over every frame of %d..%d - there is nothing to stand the body "
                "on" % (start, end))
    if max(abs(v) for v in want.values()) <= dead:
        return ("the feet are already on the floor (within %.1f cm) - nothing changed" % dead)
    return None


def line(label, carrier, want, keys, contacts):
    """What the press says: which way the body went, on what, and how many contacts carried it."""
    up = max([v for v in want.values() if v > 0.0] or [0.0])
    down = max([-v for v in want.values() if v < 0.0] or [0.0])
    moved = []
    if up > 0.005:
        moved.append("raised %.1f cm" % up)
    if down > 0.005:
        moved.append("lowered %.1f cm" % down)
    feet = ", ".join("%s %d fr" % (side.upper(), len(contacts.get(side) or ()))
                     for side in SIDES if contacts.get(side))
    return "%s on the floor: the body %s on %s, %d keys%s" % (
        label, " and ".join(moved) or "left where it was", carrier, len(keys),
        " | feet down: %s" % feet if feet else "")


def tracks_for(want, keys, axes, dead=AXIS_DEAD):
    """{channel: (times, values)} for `layerbake.write_deltas`: the LOCAL displacement each key
    frame wants, from `axes` {frame: (x, y, z)} - what one centimetre of world rise costs in the
    carrier's own translate channels on that frame (its parent may be turned: the Creep's root
    hangs under a -90 X wrapper, where world up is the root's own Z). A channel that never moves
    further than `dead` is left out, so a rig's Main takes one curve and not three."""
    out = {}
    for ch, axis in (("tx", 0), ("ty", 1), ("tz", 2)):
        values = [want[f] * (axes.get(f) or (0.0, 0.0, 0.0))[axis] for f in keys]
        if values and max(abs(v) for v in values) > dead:
            out[ch] = (list(keys), values)
    return out
