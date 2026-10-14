"""maya_walk.clean - a raw clip made the walk cycle the model reads (2026-10-14).

The animator, with a walk they broke on purpose: «мы должны научить наш билдер исправлением такой анимации» -
not looped, floating 54 cm up, jittery, the left foot turned 72 deg out, both shoulders dropped, twist bones
keyed short, the spine still. Save walk keeps a clip as it stands; `clean()` makes the cycle when the walk is
read, by the knobs of the card's Clean tab (KNOBS):

1. the root carries the travel (a root standing still while the pelvis travels takes the pelvis's line);
2. the loop: a closed cycle as it is, one missing its closing frame given it, else the best loop cut out of
   the clip - the Kovar-Gleicher distance (the body's points in the root's ground frame, a few frames either
   side) over whole strides;
3. in place: a cycle whose root and pelvis stay while its planted feet slide back gets its travel back;
4. the seam: a cut cycle's (or a joint's own) seam closed by Holden's two-sided cubics - value and slope;
5. spikes: out-and-back runs of 1-3 frames replaced (Despike);
6. posture: a bone moved off its joint put back on its rest; a clavicle or a foot outside its limits against
   the reference takes its opposite's mirrored motion half a stride on, else the reference's mean with its
   own motion (Fix posture);
7. smooth (frames); 8. the floor (the planted feet on the reference's heights); 9. the derived bones - a
   helper or a twist bone that does not loop (and was not merely keyed short: those are refilled at the seam)
   put back on its bone / rebuilt by the UE twist rule.

Nothing found, nothing changed: a clean cycle comes back as it went in (the same worlds).
numpy only (a test pins it). Maya's row vectors: world = local . parent, a position its row 3.
The design: docs/superpowers/specs/2026-10-14-walk-clean-levers-overlap-design.md.
"""
import math
import re

import numpy as np

from . import model as wm

KNOBS = (
    ("despike", 1.0, 0.0, 3.0),
    ("smooth", 0.0, 0.0, 4.0),
    ("fix_posture", 1.0, 0.0, 1.0),
    ("floor", 1.0, 0.0, 1.0),
    ("floor_offset", 0.0, -30.0, 30.0),
    ("seam", 8.0, 0.0, 30.0),
)
DEFAULTS = dict((k[0], k[1]) for k in KNOBS)
RANGES = dict((k[0], (k[2], k[3])) for k in KNOBS)

CLOSED_TOL = (0.1, 0.002)  # cm, rotation elements: the last frame against the first moved by the root's travel
SEAM_TOL = (0.01, 0.05)    # cm, degrees: a joint's own seam this small is closed already
ROOT_STILL = 1.0           # cm a clip: a root that travels less stands still...
PELVIS_TRAVELS = 10.0      # ...while a pelvis travelling more carries the walk
MIN_CYCLE = 10             # frames: no shorter loop is cut
LOOP_WINDOW = 2            # frames either side of a candidate pair in the loop distance
LOOP_TIE = 1.2             # of the least distance: the longest loop within it is cut
LOW_TOL = 2.5              # cm: a foot point this near its own lowest is down
IN_PLACE_TRAVEL = 1.0      # cm a cycle: a root and a pelvis travelling less are in place...
IN_PLACE_SPEED = 0.2       # ...when the planted feet slide back faster than this (cm a frame)
SPIKE_MIN = 6.0            # deg or cm: no smaller jump is a spike
SPIKE_K = 6.0              # x the joint's median frame step: the jumps into and out of a spike
SPIKE_RETURN = 0.5         # the frames around a spike nearer each other than this x its smaller jump
SPIKE_RUN = 3              # frames: the longest spike
MOVING = 0.05              # cm: a local translation moving less is still (its series left alone)
OFFSET_TOL = (1.0, 0.1)    # cm, share of the bone: a bone this much longer or shorter than its opposite
CLAVICLE_RISE = (-22.0, 35.0)   # degrees against the reference: the clavicle's lateral end down / up
CLAVICLE_FORWARD = 30.0         # degrees either way
FOOT_PITCH = 35.0               # degrees: the toe down / up against the shin
FOOT_OUT = 35.0                 # degrees: the toe out / in
FLOOR_DEAD = 5.0           # cm: a walk this near the floor is left on it (asd 3.5, RunFast 4.5; six floating 17-20)
FOLLOW_TOL = 1e-3          # matrix elements: a helper holding its relation to its bone this well follows it
HELPER_BONES = (("ik_foot_root", "root"), ("ik_hand_root", "root"), ("interaction", "root"),
                ("center_of_mass", "root"), ("camera_root", "root"), ("camera_bone", "camera_root"),
                ("ik_foot_l", "foot_l"), ("ik_foot_r", "foot_r"), ("ik_hand_gun", "hand_r"),
                ("ik_hand_r", "hand_r"), ("ik_hand_l", "hand_l"), ("weapon_r", "hand_r"), ("weapon_l", "hand_l"))
TWIST = re.compile(r"^(upperarm|lowerarm|thigh|calf)_twist_\d+_(l|r)$")
TWIST_CHILD = {"upperarm": "lowerarm", "lowerarm": "hand", "thigh": "calf", "calf": "foot"}
COUNTER = ("upperarm", "thigh")      # the twist takes -(1 - t) of its bone's own roll; the others t of the far bone's
POSTURE = {"clavicle": ("upperarm", True), "foot": ("ball", False)}   # child, the child keeps its world turn


def knobs(given=None):
    """The clean knobs: the defaults with `given`'s clean ones on top (others ignored), each clamped."""
    out = dict(DEFAULTS)
    for name, value in (given or {}).items():
        if name in RANGES:
            low, high = RANGES[name]
            out[name] = min(max(float(value), low), high)
    return out


class Report(object):
    """What clean() found and did: lines of (step, text, tag) - the tag a few words for the status line."""

    def __init__(self):
        self.lines = []

    def add(self, step, text, tag):
        self.lines.append((step, text, tag))

    @property
    def changed(self):
        return bool(self.lines)

    def text(self):
        if not self.lines:
            return "clean: nothing to fix"
        return "\n".join("%s: %s" % (step, text) for step, text, _ in self.lines)

    def short(self):
        return "cleaned: " + ", ".join(tag for _, _, tag in self.lines) if self.lines else ""


def is_helper(name):
    return name.startswith(wm.HELPER_PREFIXES)


def is_twist(name):
    return bool(TWIST.match(name))


def opposite(name):
    if name.endswith("_l"):
        return name[:-2] + "_r"
    if name.endswith("_r"):
        return name[:-2] + "_l"
    return name


def _flat(v, up):
    v = np.asarray(v, float)
    return v - np.dot(v, up)[..., None] * up if v.ndim > 1 else v - float(np.dot(v, up)) * up


def _order(parents):
    kids = dict((j, []) for j in range(len(parents)))
    for j, p in enumerate(parents):
        if p >= 0:
            kids[p].append(j)
    out, queue = [], [j for j, p in enumerate(parents) if p < 0]
    while queue:
        j = queue.pop(0)
        out.append(j)
        queue.extend(kids[j])
    return out


def _quat_twist(rot, axis):
    """The twist (radians) of row-vector rotations `rot` (..., 3, 3) about the unit `axis` (swing-twist)."""
    w = wm.log_rot(rot)
    angle = np.linalg.norm(w, axis=-1)
    unit = w / np.where(angle > 1e-12, angle, 1.0)[..., None]
    qv = np.sin(angle / 2.0)[..., None] * unit
    return 2.0 * np.arctan2(qv @ axis, np.cos(angle / 2.0))


class Rig(object):
    """The clip as locals: `rot` (J, F, 3, 3) and `trans` (J, F, 3) - each joint's against its parent, a joint
    with no parent its world's. `worlds()` composes them back (rigid: scale stripped)."""

    def __init__(self, names, parents, worlds):
        self.names, self.parents = list(names), [int(p) for p in parents]
        self.index = dict((n, i) for i, n in enumerate(self.names))
        self.order = _order(self.parents)
        worlds = np.asarray(worlds, float)
        rot = wm._batch_rot(worlds)
        pos = worlds[..., 3, :3]
        self.rot, self.trans = np.empty_like(rot), np.empty_like(pos)
        for j, p in enumerate(self.parents):
            if p < 0:
                self.rot[j], self.trans[j] = rot[j], pos[j]
            else:
                back = np.swapaxes(rot[p], -1, -2)
                self.rot[j] = rot[j] @ back
                self.trans[j] = np.einsum("fi,fij->fj", pos[j] - pos[p], back)

    @property
    def frames(self):
        return self.rot.shape[1]

    def worlds(self):
        count, frames = self.rot.shape[:2]
        rot, pos = np.empty((count, frames, 3, 3)), np.empty((count, frames, 3))
        for j in self.order:
            p = self.parents[j]
            if p < 0:
                rot[j], pos[j] = self.rot[j], self.trans[j]
            else:
                rot[j] = self.rot[j] @ rot[p]
                pos[j] = np.einsum("fi,fij->fj", self.trans[j], rot[p]) + pos[p]
        out = np.tile(np.eye(4), (count, frames, 1, 1))
        out[..., :3, :3], out[..., 3, :3] = rot, pos
        return out


def _rest(statics, name):
    """A bone's rest world (4x4) from `statics`, else None."""
    if not statics or name not in statics or "rest" not in statics[name]:
        return None
    return np.asarray(statics[name]["rest"], float).reshape(4, 4)


class _Clip(object):
    """What the steps share: names, parents, the up, the frames a second, the root's index."""

    def __init__(self, clip):
        self.names, self.parents = list(clip.names), [int(p) for p in clip.parents]
        self.index = dict((n, i) for i, n in enumerate(self.names))
        self.up = wm._unit(clip.up)
        self.fps = float(clip.fps)
        roots = [j for j, p in enumerate(self.parents) if p < 0]
        self.root = self.index.get("root", roots[0] if roots else 0)
        self.body = [j for j, n in enumerate(self.names) if not is_helper(n) and not is_twist(n)]

    def has(self, *names):
        return all(n in self.index for n in names)


# ---- 1. the root ----

def carry_root(worlds, c, report):
    """A root standing still (under ROOT_STILL a clip) while the pelvis travels (over PELVIS_TRAVELS) takes the
    pelvis's ground line, start to end; every other joint keeps its world."""
    if not c.has("pelvis"):
        return worlds
    pos = worlds[..., 3, :3]
    r, p = c.root, c.index["pelvis"]
    root_travel = _flat(pos[r, -1] - pos[r, 0], c.up)
    pelvis_travel = _flat(pos[p, -1] - pos[p, 0], c.up)
    if np.linalg.norm(root_travel) >= ROOT_STILL or np.linalg.norm(pelvis_travel) <= PELVIS_TRAVELS:
        return worlds
    out = worlds.copy()
    steps = np.arange(worlds.shape[1]) / float(worlds.shape[1] - 1)
    out[r, :, 3, :3] += np.outer(steps, pelvis_travel)
    report.add("root", "the root stood still while the pelvis travelled %.0f cm: the root carries the travel"
               % np.linalg.norm(pelvis_travel), "root carries the travel")
    return out


# ---- 2. the loop ----

def _travel(worlds, c):
    pos = worlds[..., 3, :3]
    return pos[c.root, -1] - pos[c.root, 0]


def is_closed(worlds, c):
    """Whether the body's last frame stands on its first moved by the root's travel (helpers and twist bones
    left out: they are rebuilt from the body)."""
    pos = worlds[c.body][:, :, 3, :3]
    moved = float(np.abs(pos[:, -1] - pos[:, 0] - _travel(worlds, c)).max())
    rot = wm._batch_rot(worlds[c.body][:, [0, -1]])
    turned = float(np.abs(rot[:, 1] - rot[:, 0]).max())
    return moved <= CLOSED_TOL[0] and turned <= CLOSED_TOL[1]


def _ground_points(worlds, c):
    """The body's points in the root's ground frame: (F, B * 3) - each frame's positions less the root's place
    on the floor."""
    pos = worlds[c.body][:, :, 3, :3]
    ground = _flat(worlds[c.root, :, 3, :3], c.up)
    return np.swapaxes(pos - ground[None], 0, 1).reshape(worlds.shape[1], -1)


def _down(worlds, c, side):
    """(F,) whether the foot is down: its ankle or its ball within LOW_TOL of its own lowest over the clip."""
    out = np.zeros(worlds.shape[1], bool)
    for name in ("foot_" + side, "ball_" + side):
        if name in c.index:
            h = worlds[c.index[name], :, 3, :3] @ c.up
            out |= h <= h.min() + LOW_TOL
    return out


def _onsets(worlds, c):
    """{side: (F,) True where the foot comes down} - None without both feet."""
    if not c.has("foot_l", "foot_r"):
        return None
    out = {}
    for side in ("l", "r"):
        down = _down(worlds, c, side)
        out[side] = down & ~np.concatenate([[True], down[:-1]])
    return out


def _missing_close(worlds, c):
    """Whether the clip is a cycle written without its closing frame: its first frame stands where its last
    would go next (as far from it as one frame's motion, the motion carrying on smoothly)."""
    q = _ground_points(worlds, c)
    frames = q.shape[0]
    if frames < MIN_CYCLE:
        return False
    steps = np.linalg.norm(np.diff(q, axis=0), axis=1)
    accel = np.linalg.norm(q[2:] - 2.0 * q[1:-1] + q[:-2], axis=1)
    seam = float(np.linalg.norm(q[0] - q[-1]))
    turn = float(np.linalg.norm(q[0] - 2.0 * q[-1] + q[-2]))
    step, acc = float(np.median(steps)), float(np.median(accel))
    return 0.0 < seam <= 1.5 * max(step, 1e-9) and turn <= 3.0 * max(acc, 1e-9) + 1e-9


def loop_window(worlds, c):
    """(i, j, rms cm): the best loop in the clip - the least Kovar-Gleicher distance (the body's ground-frame
    points over LOOP_WINDOW frames either side, RMS a point) among pairs holding whole strides (each foot coming
    down as often between them), the longest within LOOP_TIE of it."""
    q = _ground_points(worlds, c)
    frames, width = q.shape[0], q.shape[1] // 3
    sq = np.sum(q * q, axis=1)
    d0 = np.maximum(sq[:, None] + sq[None, :] - 2.0 * (q @ q.T), 0.0)
    total, count = np.zeros((frames, frames)), np.zeros((frames, frames))
    for k in range(-LOOP_WINDOW, LOOP_WINDOW + 1):
        lo, hi = max(0, -k), frames - max(0, k)
        idx = np.arange(lo, hi)
        total[np.ix_(idx, idx)] += d0[np.ix_(idx + k, idx + k)]
        count[np.ix_(idx, idx)] += 1.0
    cost = np.sqrt(total / np.maximum(count, 1.0) / width)
    onsets = _onsets(worlds, c)
    if onsets is not None:
        left, right = np.concatenate([[0], np.cumsum(onsets["l"])]), np.concatenate([[0], np.cumsum(onsets["r"])])
    pairs = []
    for i in range(frames):
        for j in range(i + MIN_CYCLE, frames):
            whole = True
            if onsets is not None:
                nl, nr = left[j] - left[i], right[j] - right[i]
                whole = nl == nr and nl >= 1
            pairs.append((whole, float(cost[i, j]), i, j))
    if not pairs:
        return None
    usable = [p for p in pairs if p[0]] or pairs
    least = min(p[1] for p in usable)
    near = [p for p in usable if p[1] <= least * LOOP_TIE + 1e-6]
    best = max(near, key=lambda p: (p[3] - p[2], -p[1]))
    return best[2], best[3], best[1]


def _cycle_travel(path, up, harmonics=6):
    """The travel of a cycle written without its closing frame: its root's ground path (P, 3) fitted as a line
    plus a periodic wobble of a few harmonics of the P frames (least squares), the line's slope x P. The ends
    alone read the root's wobble as travel (a centimetre on the synthetic walker)."""
    P = path.shape[0]
    f = np.arange(P, dtype=float)
    top = max(0, min(harmonics, (P - 3) // 2))
    columns = [f, np.ones(P)]
    for k in range(1, top + 1):
        columns += [np.cos(2.0 * math.pi * k * f / P), np.sin(2.0 * math.pi * k * f / P)]
    coeffs = np.linalg.lstsq(np.stack(columns, axis=1), _flat(path, up), rcond=None)[0]
    return coeffs[0] * P


def loop(worlds, c, report):
    """(worlds, cut): the clip as a cycle (its last frame its first's place in the next cycle) and whether its seam
    still needs closing (a loop cut out of a longer clip)."""
    if is_closed(worlds, c):
        return worlds, False
    frames = worlds.shape[1]
    if _missing_close(worlds, c):
        travel = _cycle_travel(worlds[c.root, :, 3, :3], c.up)
        last = worlds[:, :1].copy()
        last[:, 0, 3, :3] += travel
        report.add("loop", "a cycle of %d frames written without its closing frame: the closing frame added"
                   % frames, "loop closed")
        return np.concatenate([worlds, last], axis=1), False
    found = loop_window(worlds, c)
    if found is None:
        return worlds, False
    i, j, rms = found
    report.add("loop", "the loop cut out of frames %d-%d: %d-%d (%d frames), the seam %.2f cm off before closing"
               % (0, frames - 1, i, j, j - i, rms), "loop %d-%d" % (i, j))
    return worlds[:, i:j + 1].copy(), True


# ---- 3. in place ----

def restore_travel(worlds, c, report):
    """A cycle whose root and pelvis travel under IN_PLACE_TRAVEL while its planted feet slide back: every joint
    carried forward by the feet's median slide (both feet's frames down on their heel and toe)."""
    if not c.has("pelvis", "foot_l", "foot_r"):
        return worlds
    pos = worlds[..., 3, :3]
    frames = worlds.shape[1]
    P = frames - 1
    for j in (c.root, c.index["pelvis"]):
        if np.linalg.norm(_flat(pos[j, P] - pos[j, 0], c.up)) >= IN_PLACE_TRAVEL:
            return worlds
    slides = []
    for side in ("l", "r"):
        flat_down = np.ones(frames, bool)
        for name in ("foot_" + side, "ball_" + side):
            if name in c.index:
                h = pos[c.index[name]] @ c.up
                flat_down &= h <= h.min() + LOW_TOL
        ankle = pos[c.index["foot_" + side], :P]
        for f in range(P):
            if flat_down[f]:
                slides.append(_flat((ankle[(f + 1) % P] - ankle[(f - 1) % P]) / 2.0, c.up))
    if len(slides) < 2:
        return worlds
    slide = np.median(np.array(slides), axis=0)
    if np.linalg.norm(slide) < IN_PLACE_SPEED:
        return worlds
    out = worlds.copy()
    out[:, :, 3, :3] -= np.arange(frames)[None, :, None] * slide[None, None, :]
    report.add("in place", "an in-place cycle: its travel restored from the planted feet, %.2f m/s"
               % (np.linalg.norm(slide) * c.fps / 100.0), "travel restored")
    return out


# ---- the series a rig's joints move by ----

def _rot_series(rig, j):
    """(x (F, 3) radians - the joint's turn about its mean, the mean)."""
    mean = wm.mean_rot(rig.rot[j, :-1])
    return wm.log_rot(rig.rot[j] @ mean.T), mean


def _root_line(rig, r):
    frames = rig.frames
    travel = rig.trans[r, -1] - rig.trans[r, 0]
    return rig.trans[r, 0] + np.outer(np.arange(frames) / float(frames - 1), travel)


def _trans_series(rig, j, r):
    """(x (F, 3) cm, back(x) -> trans) for a joint's place: the root's off its travel line, another's local
    translation (None when it stays put)."""
    if j == r:
        line = _root_line(rig, r)
        return rig.trans[r] - line, lambda x: x + line
    t = rig.trans[j]
    if float(np.abs(t - t.mean(axis=0)).max()) < MOVING:
        return None, None
    return t.copy(), lambda x: x


def _close_frames(rig, r):
    """The closing frame made the first's: every local, the root's turn; the root's place its first's moved by
    the travel."""
    travel = rig.trans[r, -1] - rig.trans[r, 0]
    rig.rot[:, -1] = rig.rot[:, 0]
    keep = rig.trans[r, 0] + travel
    rig.trans[:, -1] = rig.trans[:, 0]
    rig.trans[r, -1] = keep


# ---- 4. the seam ----

def _holden(frames, width, d, dv):
    """Two-sided cubic offsets (F, d) taking a seam's value step `d` (= x[P] - x[0]) and its slope step `dv`
    (per frame) off: +d/2 at the start, -d/2 at the end, each easing to zero value and zero slope over
    `width` frames (Holden: offset(t) = a t^3 + b t^2 + c t + x, b = -3x - 2c, a = 2x + c)."""
    P = frames - 1
    out = np.zeros((frames,) + np.shape(d))
    if width <= 0:
        return out
    c = -0.5 * np.asarray(dv, float) * width
    for x, ends in ((0.5 * np.asarray(d, float), range(0, width + 1)),
                    (-0.5 * np.asarray(d, float), range(P - width, P + 1))):
        a, b = 2.0 * x + c, -3.0 * x - 2.0 * c
        for f in ends:
            t = (f / float(width)) if ends.start == 0 else ((P - f) / float(width))
            out[f] += ((a * t + b) * t + c) * t + x
    return out


def _seam_steps(x):
    """(d, dv): a periodic series' (F frames, the last the first's next) step in value and in slope at its seam
    - the slope's beyond what the curve's own bend there asks for."""
    d = x[-1] - x[0]
    if x.shape[0] < 5:
        return d, np.zeros_like(d)
    bend = 0.5 * ((x[2] - 2.0 * x[1] + x[0]) + (x[-1] - 2.0 * x[-2] + x[-3]))
    dv = (x[1] - x[0]) - (x[-1] - x[-2]) - bend
    return d, dv


def _held_from(x):
    """The frame a series' keys stopped at: its last frames all equal (a curve keyed short holds its last key to
    the end of the clip) - the first of them - or None (fewer than two held)."""
    last = x.shape[0] - 1
    f = last
    while f > 0 and float(np.abs(x[f] - x[f - 1]).max()) < 1e-6:
        f -= 1
    return f if last - f >= 2 else None


def _refill(x, held):
    """The held frames after `held` on the cubic Hermite from it to the cycle's first frame again (the closing
    frame), slopes from the frames beside each end: (F, d) new."""
    out = np.array(x, float)
    last = out.shape[0] - 1
    span = float(last - held)
    p1, p2 = out[held], out[0]
    m1 = (out[held] - out[held - 1]) * span if held > 0 else 0.0 * p1
    m2 = (out[1] - out[0]) * span
    for f in range(held + 1, last + 1):
        u = (f - held) / span
        h00, h10, h01, h11 = 2 * u ** 3 - 3 * u ** 2 + 1, u ** 3 - 2 * u ** 2 + u, -2 * u ** 3 + 3 * u ** 2, u ** 3 - u ** 2
        out[f] = h00 * p1 + h10 * m1 + h01 * p2 + h11 * m2
    return out


def _can_rebuild(rig, statics, name):
    """Whether `derived` can rebuild the joint: a helper with its bone (HELPER_BONES), a twist bone under its
    bone with the bone's far child - every one of them with a rest."""
    if is_helper(name):
        bone = dict(HELPER_BONES).get(name)
        names = [name, bone] if bone in rig.index else None
    elif is_twist(name):
        m = TWIST.match(name)
        bone, far = "%s_%s" % (m.group(1), m.group(2)), "%s_%s" % (TWIST_CHILD[m.group(1)], m.group(2))
        if bone not in rig.index or far not in rig.index or rig.parents[rig.index[name]] != rig.index[bone]:
            return False
        grand = rig.parents[rig.index[bone]]
        names = [name, bone, far] + ([rig.names[grand]] if grand >= 0 else [None])
    else:
        return False
    return names is not None and all(n is not None and _rest(statics, n) is not None for n in names)


def close_seam(rig, r, width, cut, statics, report):
    """Each joint's seam closed. After a cut every series - value and slope (Holden). Else only a joint whose own
    series does not close: a helper or a twist bone is left to `derived` (returned: their indices); a body joint
    keyed short (its last frames held) has the held frames refilled back to its first; any other is closed by
    Holden's offsets. The closing frame then made the first's."""
    frames = rig.frames
    width = int(min(width, (frames - 1) // 4))
    refilled, blended, rebuild = [], [], set()

    def fix(j, x, d, dv, kind):
        """the new series for one of joint j's series that does not close"""
        name = rig.names[j]
        if cut:
            return x + _holden(frames, width, d, dv)
        # a helper or a twist bone that does not loop is rebuilt from the body (the animator's broken walk: its
        # helpers and twists keyed short over motion of no use - ik_hand_gun turning 180 deg against its hand,
        # where the walk it came from holds them still)
        if _can_rebuild(rig, statics, name):
            rebuild.add(j)
            return x
        held = _held_from(x[:-1])
        if held is not None:
            refilled.append("%s (from frame %d)" % (name, held))
            return _refill(x, held)
        blended.append(name)
        return x + _holden(frames, width, d, dv * 0.0)

    for j in range(len(rig.names)):
        x, mean = _rot_series(rig, j)
        d, dv = _seam_steps(x)
        if cut or float(np.degrees(np.linalg.norm(d))) > SEAM_TOL[1]:
            rig.rot[j] = wm.exp_rot(fix(j, x, d, dv, "rot")) @ mean
        tx, back = _trans_series(rig, j, r)
        if tx is None:
            continue
        d, dv = _seam_steps(tx)
        if j == r:
            d = d * 0.0
        if cut or float(np.linalg.norm(d)) > SEAM_TOL[0]:
            rig.trans[j] = back(fix(j, tx, d, dv, "trans"))
    _close_frames(rig, r)
    if cut:
        report.add("seam", "closed over %d frames each side (value and slope)" % width, "seam closed")
    if refilled:
        unique = list(dict.fromkeys(refilled))
        report.add("seam", "keys that stopped early, refilled back to the first frame: " + _names(unique),
                   "%d short-keyed joints refilled" % len(unique))
    if blended:
        unique = list(dict.fromkeys(blended))
        report.add("seam", "joints that did not loop closed over %d frames: %s" % (width, _names(unique)),
                   "%d joints looped" % len(unique))
    return rebuild


def _names(names, most=6):
    names = list(names)
    return ", ".join(names[:most]) + (" and %d more" % (len(names) - most) if len(names) > most else "")


# ---- 5. spikes ----

def spike_runs(x, scale=1.0):
    """[[frame, ...], ...]: the out-and-back runs of a periodic series `x` (P, d) - 1..SPIKE_RUN frames whose
    jump in and jump out are both over max(SPIKE_MIN, SPIKE_K x the median frame step) / scale (a single frame's
    two jumps opposite), the frames around nearer each other than SPIKE_RETURN x the smaller jump. Longest
    first; the series is not changed."""
    x = np.asarray(x, float)
    P = x.shape[0]
    if scale <= 0.0 or P < 2 * SPIKE_RUN + 3:
        return []
    steps = np.linalg.norm(x - np.roll(x, 1, axis=0), axis=1)
    threshold = max(SPIKE_MIN, SPIKE_K * float(np.median(steps))) / scale
    taken, runs = set(), []
    for length in range(SPIKE_RUN, 0, -1):
        for f in range(P):
            run = [(f + i) % P for i in range(length)]
            if taken.intersection(run):
                continue
            a, b = (f - 1) % P, (f + length) % P
            j_in, j_out = x[run[0]] - x[a], x[b] - x[run[-1]]
            n_in, n_out = float(np.linalg.norm(j_in)), float(np.linalg.norm(j_out))
            if n_in < threshold or n_out < threshold:
                continue
            # one frame out must come straight back; a longer run's frames may scatter (lowerarm_r 17-19 of the
            # animator's broken walk: three frames of garbage, each 70 deg from the next)
            if length == 1 and float(np.dot(j_in, j_out)) >= 0.0:
                continue
            if float(np.linalg.norm(x[b] - x[a])) > SPIKE_RETURN * min(n_in, n_out):
                continue
            runs.append(run)
            taken.update(run)
    return runs


def _bridge(x, run):
    """A run's frames on the cubic Hermite from the frame before it to the frame after it (their slopes from
    their own outer neighbours), in place on the periodic series x (P, d)."""
    P = x.shape[0]
    a, b = (run[0] - 1) % P, (run[-1] + 1) % P
    span = len(run) + 1
    p1, p2 = x[a], x[b]
    m1 = (x[a] - x[(a - 1) % P]) * span
    m2 = (x[(b + 1) % P] - x[b]) * span
    for i, f in enumerate(run):
        u = (i + 1) / float(span)
        h00, h10, h01, h11 = 2 * u ** 3 - 3 * u ** 2 + 1, u ** 3 - 2 * u ** 2 + u, -2 * u ** 3 + 3 * u ** 2, u ** 3 - u ** 2
        x[f] = h00 * p1 + h10 * m1 + h01 * p2 + h11 * m2


def despike(rig, r, scale, report):
    """Each joint's out-and-back runs (its turn, and its place where it moves) bridged; toes and helpers left
    alone (a toe's flick at the push-off is out-and-back)."""
    if scale <= 0.0:
        return
    found = []
    P = rig.frames - 1
    for j, name in enumerate(rig.names):
        if is_helper(name) or name.startswith("ball_"):
            continue
        x, mean = _rot_series(rig, j)
        deg = np.degrees(x[:P])
        runs = spike_runs(deg, scale)
        if runs:
            before = deg.copy()
            for run in runs:
                _bridge(deg, run)
            worst = max(float(np.linalg.norm(before[f] - deg[f])) for run in runs for f in run)
            rig.rot[j, :P] = wm.exp_rot(np.radians(deg)) @ mean
            found.append((name, runs, worst, "deg"))
        tx, back = _trans_series(rig, j, r)
        if tx is None:
            continue
        cycle = tx[:P].copy()
        runs = spike_runs(cycle, scale)
        if runs:
            before = cycle.copy()
            for run in runs:
                _bridge(cycle, run)
            worst = max(float(np.linalg.norm(before[f] - cycle[f])) for run in runs for f in run)
            tx[:P] = cycle
            rig.trans[j] = back(tx)
            found.append((name, runs, worst, "cm"))
    _close_frames(rig, r)
    if found:
        parts = []
        for name, runs, worst, unit in found:
            frames = ", ".join("%d" % run[0] if len(run) == 1 else "%d-%d" % (run[0], run[-1]) for run in runs)
            parts.append("%s %s (%.0f %s)" % (name, frames, worst, unit))
        report.add("spikes", "out-and-back spikes bridged: " + "; ".join(parts),
                   "%d spike%s" % (len(found), "" if len(found) == 1 else "s"))


# ---- 6. posture ----

def _body_axes(points, up, c):
    """(fwd, side, up): side the reference's left (upper arms, else thighs, right to left), fwd where its toes
    point."""
    side = None
    for name in ("upperarm", "thigh"):
        if name + "_l" in points and name + "_r" in points:
            side = _flat(points[name + "_l"][3, :3] - points[name + "_r"][3, :3], up)
            if np.linalg.norm(side) > 1e-6:
                break
    if side is None or np.linalg.norm(side) < 1e-6:
        return None
    side = wm._unit(side)
    fwd = np.cross(side, up)
    if "foot_l" in points and "ball_l" in points:
        toe = _flat(points["ball_l"][3, :3] - points["foot_l"][3, :3], up)
        if float(np.dot(toe, fwd)) < 0.0:
            fwd = -fwd
    return fwd, side, up


def _child_dir(world_rot, world_pos, j, child, parent):
    """(F, 3) unit: the direction from joint j to its child in the parent's frame."""
    d = world_pos[child] - world_pos[j]
    local = np.einsum("fi,fij->fj", d, np.swapaxes(world_rot[parent], -1, -2))
    return local / np.linalg.norm(local, axis=1, keepdims=True)


def _angles(kind, a, sign, axes):
    """A joint's measured angles (degrees) from a body-axes direction `a` of its child."""
    fwd, side, up = axes
    if kind == "clavicle":
        return (math.degrees(math.asin(min(max(float(a @ up), -1.0), 1.0))),
                math.degrees(math.atan2(float(a @ fwd), sign * float(a @ side))))
    return (math.degrees(math.asin(min(max(-float(a @ up), -1.0), 1.0))),
            math.degrees(math.atan2(sign * float(a @ side), float(a @ fwd))))


def _out_of_limits(kind, delta):
    if kind == "clavicle":
        rise, forward = delta
        return rise < CLAVICLE_RISE[0] or rise > CLAVICLE_RISE[1] or abs(forward) > CLAVICLE_FORWARD
    pitch, out = delta
    return abs(pitch) > FOOT_PITCH or abs(out) > FOOT_OUT


def _say(kind, delta):
    if kind == "clavicle":
        return "%.0f deg %s, %.0f deg %s" % (abs(delta[0]), "down" if delta[0] < 0 else "up",
                                              abs(delta[1]), "forward" if delta[1] >= 0 else "back")
    return "%.0f deg toe %s, %.0f deg %s" % (abs(delta[0]), "down" if delta[0] >= 0 else "up",
                                             abs(delta[1]), "out" if delta[1] >= 0 else "in")


def _strides(worlds, c):
    onsets = _onsets(worlds, c)
    if onsets is None:
        return 1
    return max(1, int(min(onsets["l"][:-1].sum(), onsets["r"][:-1].sum())))


def _shifted(rots, shift):
    """A periodic rotation series (P, 3, 3) read `shift` frames later (slerped between whole frames)."""
    P = rots.shape[0]
    out = np.empty_like(rots)
    for f in range(P):
        t = f + shift
        i = int(math.floor(t))
        u = t - i
        a, b = rots[i % P], rots[(i + 1) % P]
        out[f] = a if u < 1e-12 else wm.exp_rot(u * wm.log_rot(b @ a.T)) @ a
    return out


def _mirrored_locals(world_rot, x, parent, root, rest_rot, flip):
    """(P, 3, 3): joint x's local turn as its opposite's mirror (posemath's rule: each joint's turn from its rest
    in the root's frame, reflected) - its parent mirrored the same way."""
    root_rot = world_rot[root]

    def mirrored(name_index, opp_index):
        q = world_rot[opp_index] @ np.swapaxes(root_rot, -1, -2)
        rest_q_opp = rest_rot[opp_index] @ rest_rot[root].T
        rest_q = rest_rot[name_index] @ rest_rot[root].T
        delta = rest_q_opp.T[None] @ q
        return rest_q[None] @ flip[None] @ delta @ flip[None]
    q_x = mirrored(x[0], x[1])
    q_p = mirrored(parent[0], parent[1])
    return q_x @ np.swapaxes(q_p, -1, -2)


def posture(rig, worlds, c, statics, reference, strength, report):
    """Bones moved off their joints put back; clavicles and feet outside their limits against the reference
    fixed (the module's docstring). Returns whether anything changed."""
    if strength <= 0.0:
        return False
    P = rig.frames - 1
    rest = dict((n, _rest(statics, n)) for n in c.names)
    changed = False
    # bones moved off their joints: a pair's lengths apart past OFFSET_TOL, the side farther from its rest put back
    if all(v is not None for v in rest.values()):
        moved = []
        for j, name in enumerate(c.names):
            other = opposite(name)
            p = c.parents[j]
            if other == name or other not in c.index or p < 0 or is_helper(name) or is_twist(name) \
                    or name in ("root", "pelvis") or name > other:
                continue
            o = c.index[other]
            rest_len = dict((k, float(np.linalg.norm(rest[c.names[k]][3, :3] - rest[c.names[c.parents[k]]][3, :3])))
                            for k in (j, o))
            mean_len = dict((k, float(np.linalg.norm(rig.trans[k, :P].mean(axis=0)))) for k in (j, o))
            if abs(mean_len[j] - mean_len[o]) <= max(OFFSET_TOL[0], OFFSET_TOL[1] * max(rest_len.values())):
                continue
            k = max((j, o), key=lambda k: abs(mean_len[k] - rest_len[k]))
            pk = c.parents[k]
            back = rest[c.names[pk]][:3, :3]
            back = wm.orthonormal(back).T
            local = (rest[c.names[k]][3, :3] - rest[c.names[pk]][3, :3]) @ back
            rig.trans[k] = (1.0 - strength) * rig.trans[k] + strength * local[None]
            moved.append("%s %.1f cm (its rest %.1f)" % (c.names[k], mean_len[k], rest_len[k]))
        if moved:
            report.add("posture", "bones moved off their joints put back: " + "; ".join(moved),
                       "%d bone%s back" % (len(moved), "" if len(moved) == 1 else "s"))
            changed = True
            worlds = rig.worlds()
    ref = reference if reference else (dict((n, m) for n, m in rest.items() if m is not None) if statics else None)
    if not ref:
        return changed
    axes = _body_axes(ref, c.up, c)
    if axes is None:
        return changed
    world_rot = wm._batch_rot(worlds)
    world_pos = worlds[..., 3, :3]
    ref_rot = dict((n, wm.orthonormal(m)) for n, m in ref.items())
    flags = {}
    for kind, (child_stem, _) in POSTURE.items():
        for side, sign in (("l", 1.0), ("r", -1.0)):
            name, child = "%s_%s" % (kind, side), "%s_%s" % (child_stem, side)
            if not c.has(name, child) or name not in ref or child not in ref:
                continue
            j, ch = c.index[name], c.index[child]
            p = c.parents[j]
            pname = c.names[p]
            if pname not in ref:
                continue
            u = _child_dir(world_rot, world_pos, j, ch, p)[:P].mean(axis=0)
            u_ref = (ref[child][3, :3] - ref[name][3, :3]) @ ref_rot[pname].T
            a, a_ref = wm._unit(u @ ref_rot[pname]), wm._unit(u_ref @ ref_rot[pname])
            got, want = _angles(kind, a, sign, axes), _angles(kind, a_ref, sign, axes)
            delta = (got[0] - want[0], (got[1] - want[1] + 180.0) % 360.0 - 180.0)
            flags[name] = (kind, delta, _out_of_limits(kind, delta))
    broken = [n for n, (_, _, out) in flags.items() if out]
    if not broken:
        return changed
    strides = _strides(worlds, c)
    have_rest = all(rest.get(n) is not None for n in c.names)
    flip = None
    if have_rest:
        rest_rot = np.array([wm.orthonormal(rest[n]) for n in c.names])
        rest_axes = _body_axes(rest, c.up, c)
        root_rest = rest_rot[c.root]
        across = rest_axes[1] @ root_rest.T if rest_axes is not None else np.array([1.0, 0.0, 0.0])
        across = wm._unit(across)
        flip = np.eye(3) - 2.0 * np.outer(across, across)
    said = []
    for name in sorted(broken):
        kind, delta, _ = flags[name]
        j = c.index[name]
        p = c.parents[j]
        other = opposite(name)
        own = rig.rot[j, :P].copy()
        healthy = other in flags and not flags[other][2]
        if healthy and flip is not None:
            o, pp = c.index[other], c.parents[c.index[other]]
            mirrored = _mirrored_locals(world_rot[:, :P], (j, o), (p, pp), c.root, rest_rot, flip)
            new = _shifted(mirrored, P / (2.0 * strides))
            how = "its opposite's motion mirrored onto it"
        else:
            mean = wm.mean_rot(own)
            ref_local = ref_rot[name] @ ref_rot[c.names[p]].T
            new = wm.exp_rot(wm.log_rot(own @ mean.T)) @ ref_local
            how = "set on the reference, its own motion kept"
        final = wm.exp_rot(strength * wm.log_rot(new @ np.swapaxes(own, -1, -2))) @ own
        keeps_world = POSTURE[kind][1]
        if keeps_world:
            kids = [k for k, q in enumerate(c.parents) if q == j]
            parent_rot = world_rot[p, :P]
            for k in kids:
                old_world = rig.rot[k, :P] @ own @ parent_rot
                rig.rot[k, :P] = old_world @ np.swapaxes(final @ parent_rot, -1, -2)
        rig.rot[j, :P] = final
        said.append("%s %s: %s" % (name, _say(kind, delta), how))
    _close_frames(rig, c.root)
    report.add("posture", "against the reference: " + "; ".join(said),
               "%d joint%s set right" % (len(said), "" if len(said) == 1 else "s"))
    return True


# ---- 7. smooth ----

def smooth(rig, r, sigma, report):
    """Every joint's turn and moving place (the root's off its travel line) through a periodic Gaussian of
    `sigma` frames."""
    if sigma <= 0.0:
        return
    P = rig.frames - 1
    k = np.fft.rfftfreq(P)
    gain = np.exp(-0.5 * (2.0 * math.pi * k * sigma) ** 2)

    def low(x):
        return np.fft.irfft(np.fft.rfft(x, axis=0) * gain[:, None], n=P, axis=0)
    for j, name in enumerate(rig.names):
        if is_helper(name):
            continue
        x, mean = _rot_series(rig, j)
        rig.rot[j, :P] = wm.exp_rot(low(x[:P])) @ mean
        tx, back = _trans_series(rig, j, r)
        if tx is not None:
            tx[:P] = low(tx[:P])
            rig.trans[j] = back(tx)
    _close_frames(rig, r)
    report.add("smooth", "every joint through a Gaussian of %.1f frames" % sigma, "smoothed %.1f fr" % sigma)


# ---- 8. the floor ----

def _subtree(parents, top):
    out, todo = {top}, [top]
    while todo:
        j = todo.pop()
        for k, p in enumerate(parents):
            if p == j and k not in out:
                out.add(k)
                todo.append(k)
    return out


def _helper_bones(c):
    return [(c.index[h], c.index[b]) for h, b in HELPER_BONES if c.has(h, b)]


def floor(worlds, c, statics, reference, share, offset, report):
    """The body (the pelvis and below it, and the helpers on it) moved so the planted feet stand on the
    reference's heights (else the rest's) over the root: the median at mid-stance of the lower of the ankle's
    and the ball's difference; left alone within FLOOR_DEAD; `offset` cm on top."""
    if not c.has("pelvis", "foot_l", "foot_r"):
        return worlds
    standing = reference
    if not standing and statics:
        standing = dict((n, _rest(statics, n)) for n in c.names if _rest(statics, n) is not None)
    shift = 0.0
    measured = None
    if standing and share > 0.0 and "root" in standing:
        pos = worlds[..., 3, :3]
        base = standing["root"][3, :3] @ c.up
        diffs = []
        for side in ("l", "r"):
            names = [n for n in ("foot_" + side, "ball_" + side) if n in c.index and n in standing]
            if not names:
                continue
            down = np.ones(worlds.shape[1] - 1, bool)
            for n in names:
                h = pos[c.index[n], :-1] @ c.up
                down &= h <= h.min() + LOW_TOL
            if not down.any():
                continue
            for f in np.nonzero(down)[0]:
                above = pos[c.root, f] @ c.up
                diffs.append(min((pos[c.index[n], f] @ c.up - above) - (standing[n][3, :3] @ c.up - base)
                                 for n in names))
        if diffs:
            measured = float(np.median(diffs))
            if abs(measured) > FLOOR_DEAD:
                shift = -share * measured
    shift += offset
    if abs(shift) < 1e-9:
        return worlds
    moved = _subtree(c.parents, c.index["pelvis"])
    relations = [(h, b, worlds[h] @ np.linalg.inv(worlds[b])) for h, b in _helper_bones(c)
                 if b in moved and h not in moved]
    out = worlds.copy()
    out[sorted(moved), :, 3, :3] += shift * c.up
    for h, b, rel in relations:
        out[h] = rel @ out[b]
    text = "the body %s %.1f cm" % ("lowered" if shift < 0 else "raised", abs(shift))
    if measured is not None and abs(measured) > FLOOR_DEAD:
        text += " - its planted feet stood %.1f cm %s the floor" % (abs(measured), "over" if measured > 0 else "under")
    report.add("floor", text, "floor %+.1f cm" % shift)
    return out


# ---- 9. the derived bones ----

def derived(worlds, c, statics, rebuild, report):
    """The helpers and twist bones in `rebuild` (they did not loop and were not keyed short - close_seam): a
    helper put back on its bone at their rest relation (the helpers riding it with it), a twist bone rebuilt
    by the UE twist rule."""
    if not rebuild:
        return worlds
    out = worlds.copy()
    seated, bones = [], dict(_helper_bones(c))
    redo = set(j for j in rebuild if j in bones)
    for j in _order(c.parents):                 # a helper riding one put back is put back with it
        if j in bones and c.parents[j] in redo:
            redo.add(j)
    for h in [j for j in _order(c.parents) if j in redo]:
        b = bones[h]
        rest_h, rest_b = _rest(statics, c.names[h]), _rest(statics, c.names[b])
        if rest_h is None or rest_b is None:
            continue
        fixed = rest_h @ np.linalg.inv(rest_b)
        fixed[:3, :3] = wm.orthonormal(fixed[:3, :3])
        out[h] = fixed[None] @ out[b]
        seated.append(c.names[h])
    rebuilt = []
    twists = [j for j in rebuild if is_twist(c.names[j])]
    if twists:
        rig = Rig(c.names, c.parents, out)
        for j in twists:
            rule = _twist_rule(rig, c, statics, c.names[j])
            if rule is not None:
                rig.rot[j] = rule
                rebuilt.append(c.names[j])
        if rebuilt:
            out = rig.worlds()
    if seated:
        report.add("helpers", "put back on their bones: " + _names(seated), "%d helpers re-seated" % len(seated))
    if rebuilt:
        report.add("twists", "rebuilt by the UE twist rule: " + _names(rebuilt), "%d twists rebuilt" % len(rebuilt))
    return out


def _twist_rule(rig, c, statics, name):
    """A twist bone's local turns (F, 3, 3) by the UE rule, or None: its rest relation rolled about its bone's
    axis by -(1 - t) of the bone's own roll against its parent (upper arm, thigh) or t of the far bone's roll
    (forearm, calf); t its place along the bone."""
    m = TWIST.match(name)
    if not m:
        return None
    segment, side = m.group(1), m.group(2)
    bone, far = "%s_%s" % (segment, side), "%s_%s" % (TWIST_CHILD[segment], side)
    if not c.has(bone, far) or c.parents[c.index[name]] != c.index[bone]:
        return None
    s, f, t_index = c.index[bone], c.index[far], c.index[name]
    grand = c.parents[s]
    names = [name, bone, far] + ([c.names[grand]] if grand >= 0 else [])
    rests = dict((n, _rest(statics, n)) for n in names)
    if any(v is None for v in rests.values()) or grand < 0:
        return None
    rot = dict((n, wm.orthonormal(m_)) for n, m_ in rests.items())
    pos = dict((n, m_[3, :3]) for n, m_ in rests.items())
    far_offset = (pos[far] - pos[bone]) @ rot[bone].T            # the bone's axis in its own frame
    length = float(np.linalg.norm(far_offset))
    if length < 1e-6:
        return None
    axis = far_offset / length
    t = min(max(float(np.linalg.norm((pos[name] - pos[bone]) @ rot[bone].T)) / length, 0.0), 1.0)
    rest_twist = rot[name] @ rot[bone].T
    if segment in COUNTER:
        rest_local = rot[bone] @ rot[c.names[grand]].T
        delta = np.swapaxes(rest_local, -1, -2)[None] @ rig.rot[s]    # local = rest . delta: in the parent's frame
        roll = _quat_twist(delta, axis @ rest_local)
        angle = -(1.0 - t) * roll
    else:
        rest_local = rot[far] @ rot[bone].T
        delta = np.swapaxes(rest_local, -1, -2)[None] @ rig.rot[f]
        roll = _quat_twist(delta, axis)
        angle = t * roll
    return rest_twist[None] @ wm.exp_rot(angle[:, None] * axis[None])


# ---- the whole ----

def clean(clip, statics=None, reference=None, given=None):
    """(the clean cycle as a model.Clip, Report). `statics` {name: {"rest": 16 floats, ...}} (the saved walk's),
    `reference` {name: 4x4 world} on the walk's skeleton (pose.carried) or None, `given` the knobs (clean's
    picked out). A clip in which nothing is found comes back as it went in."""
    k = knobs(given)
    c = _Clip(clip)
    report = Report()
    worlds = np.asarray(clip.worlds, float)
    if worlds.shape[1] < 3:
        return clip, report
    worlds = carry_root(worlds, c, report)
    worlds, cut = loop(worlds, c, report)
    worlds = restore_travel(worlds, c, report)
    rig = Rig(c.names, c.parents, worlds)
    lines = len(report.lines)
    rebuild = close_seam(rig, c.root, k["seam"], cut, statics, report)
    despike(rig, c.root, k["despike"], report)
    touched = posture(rig, rig.worlds(), c, statics, reference, k["fix_posture"], report)
    smooth(rig, c.root, k["smooth"], report)
    if len(report.lines) > lines or touched:
        worlds = rig.worlds()
    worlds = floor(worlds, c, statics, reference, k["floor"], k["floor_offset"], report)
    worlds = derived(worlds, c, statics, rebuild, report)
    if not report.changed:
        return clip, report
    return wm.Clip(c.names, c.parents, worlds, clip.fps, clip.up, clip.name), report
