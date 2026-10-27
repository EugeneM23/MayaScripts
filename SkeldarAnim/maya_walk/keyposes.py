"""maya_walk.keyposes - a cycle's four key poses, and the edits an animator makes to them (2026-10-26).

The animator: «Мы находим в нашем цикле 4 ключевые позы через которые строится походка или бег, выносим эти позы
каждую на свой риг и изменяя риги контролируем весь наш цикл а умные обработчики нам помогают». The rigs are
maya_walk.keyrig; this module is what they read and write, numpy only (no Maya):

- `find(walk)`: every step of the cycle (a foot's heel strike to the other foot's) and its four key poses -
  CONTACT (the heel strike), DOWN (the pelvis lowest before the passing), PASSING (the swinging foot passes the
  standing one), UP (the pelvis highest before the next contact). A run reads the same: its Up is the flight;
- `measure(worlds, walk)`: what is read off a pose of the walk's skeleton - the upper body's local turns, the
  pelvis's place over the root, each knee (for its turn about the leg) and each foot (its place and turn);
- `combine(keys, key, base, now, walk, frame)`: the key's edit moved by what changed between two readings;
- `correct(clip, keys, steps, walk)`: the cycle's frames with the edits in them, before the analysis. A key's
  edit is exact at its key and fades to nothing at the keys on either side (smoothstep, turns in log space).
  The rigs show the first step of the LEFT foot; a step of the right foot takes the same edit mirrored across
  the walk's middle (the right arm's turn at the left contact is the left arm's at the right contact). The
  upper body's turns are in the parent's frame (the motion about them kept), the pelvis is moved over the root,
  and each leg is solved again from its hip onto its foot - a foot flat on the ground stays where the cycle
  plants it, a foot on its heel or its ball takes the edit's turn about that point, a foot in the air takes
  the move and the turn. The smart helpers (Foot placement, Balance, the knees' soft limit) do the rest when
  the walk is put on a skeleton.

The edits live beside the walk's file as <walk>.walkkeys.json (`load`, `save`). The design:
docs/superpowers/specs/2026-10-26-walk-key-poses-design.md.
"""
import json
import math
import os

import numpy as np

from . import meanpose as mp
from . import model as wm

FORMAT = "skeldar.walkkeys"
VERSION = 1
SUFFIX = ".walkkeys.json"
SIDES = ("l", "r")
KEYS = ("contact", "down", "passing", "up")
LABELS = {"contact": "Contact", "down": "Down", "passing": "Passing", "up": "Up"}
REF_SIDE = "l"                      # the rigs show the first step of this foot; the other foot's are mirrored
MIN_STEP = 4                        # frames: a step shorter than this has no room for four key poses
FLAT_CM = 0.2                       # cm: a pelvis moving less than this over a span has no Down or Up there
SHARES = (0.25, 0.5, 0.75)          # Down, Passing, Up: their share of the step (the guide's layout)
GROUND_CM = wm.GROUND_TOL           # a foot point this near its own lowest is on the ground
MIN_TURN = mp.MIN_TURN
MIN_CM = mp.MIN_CM
KNEE_MIN = math.radians(1.5)        # a knee turned less than this on a rig is its IK solver following the hips
KNEE_BENT = mp.KNEE_BENT           # a knee's turn about its leg is read only while the leg is bent this much...
KNEE_FLIP = mp.KNEE_FLIP           # ...and under this: past it the IK solver flipped the knee (2026-10-27)
COMMON_SHARE = 0.6                  # a pelvis move alike on all four keys: each at least this share of the largest
OTHER = {"l": "r", "r": "l"}


class Refusal(Exception):
    """What the key poses do not do, and why."""


def empty():
    return {}


def empty_print():
    return dict((s, {"t": np.zeros(3), "yaw": 0.0}) for s in SIDES)


def empty_key():
    """A key's edit: "rot" {bone: 3x3 in its parent's frame} (the toes, ball_l / ball_r, among them), "pelvis" (a move
    in travel coordinates), "knee" {side: radians about the leg}, "foot" {side: a move and turn in the air}, "print"
    {side: {"t": where the foot stands for its whole stance, travel coordinates, "yaw": its turn about up}}."""
    return {"rot": {}, "pelvis": np.zeros(3), "knee": {"l": 0.0, "r": 0.0},
            "foot": dict((s, {"t": np.zeros(3), "r": np.eye(3)}) for s in SIDES), "print": empty_print()}


def _print_empty(entry):
    prints = entry.get("print") or {}
    return all(float(np.abs(prints[s]["t"]).max()) < 1e-9 and abs(prints[s]["yaw"]) < 1e-12
               for s in SIDES if s in prints)


def key_empty(entry):
    return (not entry.get("rot") and float(np.abs(entry["pelvis"]).max()) < 1e-9
            and all(abs(entry["knee"][s]) < 1e-12 for s in SIDES)
            and all(float(np.abs(entry["foot"][s]["t"]).max()) < 1e-9
                    and float(np.abs(entry["foot"][s]["r"] - np.eye(3)).max()) < 1e-12 for s in SIDES)
            and _print_empty(entry))


def is_empty(keys):
    return not keys or all(key_empty(entry) for entry in keys.values())


# ---- the file ----

def path_for(walk_path):
    """The key poses' file beside a walk's file (<walk>.walk.gz -> <walk>.walkkeys.json)."""
    from . import files
    base = walk_path[:-len(files.SUFFIX)] if walk_path.endswith(files.SUFFIX) else walk_path
    return base + SUFFIX


def _m3(values):
    return np.array(values, float).reshape(3, 3)


def loads(data, what="the key poses"):
    """{key: entry} from the plain data `dumps` gives (a file's, a walker's attribute)."""
    if not data:
        return empty()
    if data.get("format") != FORMAT or int(data.get("version", 0)) > VERSION:
        raise Refusal("%s are not key pose edits this tool reads" % what)
    out = {}
    for key, raw in (data.get("keys") or {}).items():
        if key not in KEYS:
            continue
        entry = empty_key()
        entry["rot"] = dict((name, _m3(m)) for name, m in (raw.get("rot") or {}).items())
        entry["pelvis"] = np.array(raw.get("pelvis", [0.0, 0.0, 0.0]), float)
        entry["knee"] = dict((s, float((raw.get("knee") or {}).get(s, 0.0))) for s in SIDES)
        for s in SIDES:
            foot = (raw.get("foot") or {}).get(s) or {}
            entry["foot"][s] = {"t": np.array(foot.get("t", [0.0, 0.0, 0.0]), float),
                                "r": _m3(foot["r"]) if "r" in foot else np.eye(3)}
            stance = (raw.get("print") or {}).get(s) or {}
            entry["print"][s] = {"t": np.array(stance.get("t", [0.0, 0.0, 0.0]), float),
                                 "yaw": float(stance.get("yaw", 0.0))}
        out[key] = entry
    return out


def dumps(keys):
    """The plain data (JSON) of `keys`; {} for no edit at all."""
    if is_empty(keys):
        return {}
    flat = lambda m: [round(float(v), 12) for v in np.asarray(m, float).reshape(-1)]
    data = {"format": FORMAT, "version": VERSION, "keys": {}}
    for key, entry in keys.items():
        if key_empty(entry):
            continue
        prints = entry.get("print") or empty_print()
        data["keys"][key] = {"rot": dict((n, flat(m)) for n, m in entry["rot"].items()),
                             "pelvis": flat(entry["pelvis"]),
                             "knee": dict((s, float(entry["knee"][s])) for s in SIDES),
                             "foot": dict((s, {"t": flat(entry["foot"][s]["t"]), "r": flat(entry["foot"][s]["r"])})
                                          for s in SIDES),
                             "print": dict((s, {"t": flat(prints[s]["t"]), "yaw": float(prints[s]["yaw"])})
                                           for s in SIDES)}
    return data


def load(path):
    """The key poses' edits in `path` ({key: entry}), or none when there is no file."""
    if not os.path.exists(path):
        return empty()
    try:
        with open(path) as handle:
            data = json.load(handle)
    except (OSError, ValueError) as error:
        raise Refusal("%s is not a key poses file (%s)" % (os.path.basename(path), error))
    return loads(data, os.path.basename(path))


def save(path, keys):
    """`keys` to `path`; no edit at all removes the file."""
    if is_empty(keys):
        if os.path.exists(path):
            os.remove(path)
        return
    data = dumps(keys)
    folder = os.path.dirname(path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    temporary = path + ".part"
    with open(temporary, "w") as handle:
        json.dump(data, handle, indent=1)
    if os.path.exists(path):
        os.remove(path)
    os.rename(temporary, path)


# ---- the key poses of a cycle ----

def _at(walk, j, f):
    """Joint j's place at an unwrapped frame f (the travel added for each cycle past the first)."""
    P = walk.P
    return walk.pos[j][f % P] + (f // P) * walk.travel


def find(walk):
    """[{"side": the foot that strikes, "contact", "down", "passing", "up": unwrapped frames, "next": the next
    contact}] for every step of the cycle, in the order they come. Refused, by name: a walk whose steps the model
    could not read, feet that do not take turns, a step too short for four key poses."""
    if getattr(walk, "placement_note", ""):
        raise Refusal("the key poses need the steps: %s" % walk.placement_note)
    P = walk.P
    strikes = sorted((int(round(hs)) % P, s) for s in SIDES for hs, _ in walk.contact.get(s, []))
    n = len(strikes)
    if n < 2 or any(strikes[i][1] == strikes[(i + 1) % n][1] for i in range(n)):
        raise Refusal("the feet do not take turns in this cycle (%s): no steps to find key poses in"
                      % " ".join(s for _, s in strikes))
    idx = walk.index
    pelvis = idx["pelvis"]
    height = lambda f: float(np.dot(_at(walk, pelvis, f), walk.up))
    steps = []
    for i, (c, side) in enumerate(strikes):
        nxt = strikes[(i + 1) % n][0] + (P if i + 1 == n else 0)
        if nxt <= c:
            nxt += P
        if nxt - c < MIN_STEP:
            raise Refusal("a step of %d frames (the %s foot's at frame %d): too short for four key poses"
                          % (nxt - c, wm.SIDE_WORD.get(side, side), c))
        stand, swing = idx["foot_" + side], idx["foot_" + OTHER[side]]
        ahead = lambda f: float(np.dot(_at(walk, swing, f) - _at(walk, stand, f), walk.fwd))
        span = nxt - c
        down_band, pass_band, up_band = (_band(c, span, share) for share in SHARES)
        crossing = [f for f in range(c + 1, nxt) if ahead(f - 1) < 0.0 <= ahead(f)]
        middle = c + 0.5 * span
        inside = [f for f in crossing if f in pass_band]
        if inside:
            passing = min(inside, key=lambda f: abs(f - middle))
        elif crossing:                      # the feet pass outside the band (a sprint's: right after the strike)
            passing = min(pass_band, key=lambda f: abs(ahead(f)))
        else:                               # a strafe: the feet never pass - where they come nearest
            passing = max(pass_band, key=ahead)
        down = _extreme(down_band, height, min, down_band[0], down_band[-1])
        frames = up_band
        other = OTHER[side]
        flight = [f for f in frames if not _is_down(walk, side, f) and not _is_down(walk, other, f)]
        up = _extreme(flight or frames, height, max, frames[0], frames[-1])
        down, passing, up = _ordered(c, down, passing, up, nxt)
        steps.append({"side": side, "contact": c, "down": down, "passing": passing, "up": up, "next": nxt})
    return steps


def _is_down(walk, side, f):
    return max(ground(walk, side, f)) >= 0.5


def _band(c, span, share):
    """The frames a key pose may take: within a sixteenth of the step of its own share of it (the guide's layout
    - Down near a quarter, Passing the middle, Up three quarters), inside the step. Each key looks for its event
    (the pelvis lowest, the feet passing, the pelvis highest) only there, so the four are poses of their own: a
    sprint's raw events fell on three frames in a row (2026-10-27)."""
    target = c + share * span
    half = span / 16.0
    lo = max(c + 1, int(math.ceil(target - half)))
    hi = min(c + span - 1, int(math.floor(target + half)))
    if lo > hi:
        lo = hi = min(max(int(round(target)), c + 1), c + span - 1)
    return list(range(lo, hi + 1))


def _ordered(c, down, passing, up, nxt):
    """Down, Passing and Up kept apart and in order between the contact and the next one (a frame at least
    between any two), nearest to where they were found."""
    keys = [down, passing, up]
    for i in range(3):
        keys[i] = min(max(keys[i], c + 1 + i), nxt - 3 + i)
    for i in (1, 2):
        keys[i] = max(keys[i], keys[i - 1] + 1)
    for i in (1, 0):
        keys[i] = min(keys[i], keys[i + 1] - 1)
    return keys


def _extreme(frames, value, pick, lo, hi):
    """The frame in `frames` where `value` is lowest (pick=min) or highest (max) - the middle of lo..hi when the
    pelvis barely moves there (under FLAT_CM: no extreme to find)."""
    frames = list(frames)
    if not frames:
        return (lo + hi) // 2
    values = [value(f) for f in frames]
    if max(values) - min(values) < FLAT_CM:
        return min(max((lo + hi) // 2, frames[0]), frames[-1])
    return pick(frames, key=value)


def reference(steps):
    """The step the rigs show: the first of REF_SIDE's foot (its frames mod P are the rigs' frames)."""
    for step in steps:
        if step["side"] == REF_SIDE:
            return step
    return steps[0]


def frames_of(steps, P):
    """{key: frame} - the rigs' frames (the reference step's, within the cycle)."""
    ref = reference(steps)
    return dict((key, ref[key] % P) for key in KEYS)


# ---- reading a pose ----

def measure(worlds, walk):
    """{"local": {bone: 3x3}, "pelvis": the pelvis over the root (travel coordinates), "knee": {side: (hip, knee -
    hip, ankle)}, "foot": {side: (its place over the root in travel coordinates, its world 3x3)}} of a pose
    ({name: 4x4 world}) of the walk's skeleton."""
    W = lambda n: np.asarray(worlds[n], float)
    rot = lambda n: wm.orthonormal(W(n)[:3, :3])
    out = {"local": {}, "knee": {}, "foot": {}}
    for name in mp.upper_bones(walk):
        parent = walk.names[walk.parents[walk.index[name]]]
        if name in worlds and parent in worlds:
            out["local"][name] = rot(name) @ rot(parent).T
    root = W("root")[3, :3] if "root" in worlds else np.zeros(3)
    out["pelvis"] = (W("pelvis")[3, :3] - root) @ walk.basis.T
    for side in SIDES:
        hip, knee, ankle = (W("%s_%s" % (b, side))[3, :3] for b in mp.LEGS)
        out["knee"][side] = (hip, knee - hip, ankle)
        out["foot"][side] = ((ankle - root) @ walk.basis.T, rot("foot_" + side))
        ball = "ball_" + side
        if ball in worlds and ball in walk.index:            # the toes: a turn in the foot's frame
            out["local"][ball] = rot(ball) @ rot("foot_" + side).T
    return out


bend = mp.leg_bend            # a leg's knee bend from measure's (hip, knee - hip, ankle)


def yaw_of(r, up):
    """The turn about `up` (radians) in a world 3x3 `r` (its twist about up)."""
    q = wm.log_rot(wm.orthonormal(r))
    angle = float(np.linalg.norm(q))
    if angle < 1e-12:
        return 0.0
    axis = q / angle
    # swing-twist: the twist about up of the rotation (half angle formulation)
    w = math.cos(angle / 2.0)
    v = math.sin(angle / 2.0) * float(np.dot(axis, up))
    return 2.0 * math.atan2(v, w)


def ground(walk, side, f):
    """(the heel's, the ball's share on the ground, 0..1) of a foot at frame f of the walk - each point within
    GROUND_CM of its own lowest in the cycle is down."""
    out = []
    for part in ("foot", "ball"):
        j = walk.index["%s_%s" % (part, side)]
        h = walk.pos[j] @ walk.up
        out.append(min(max(1.0 - (float(h[f % walk.P]) - float(h.min())) / GROUND_CM, 0.0), 1.0))
    return tuple(out)


def increment(key, base, now, walk, frame, knees=None):
    """(the edit that turns the reading `base` into `now`, [(what moved, how much, unit)], [what was not taken]):
    read on the rig standing in the key `key` at the walk's frame `frame` (2026-10-27, «нужно убедиться что наша
    анимация реагирует на изменения всех контроллеров»):
    - a bone's local turned to now = base . Y gives Y (in its parent's frame) - every bone above the legs, the
      toes;
    - the pelvis's move;
    - a foot in the air: its move and its turn;
    - a foot on the ground (its heel or its ball, `ground`): its move along the ground is its PRINT - where it
      stands for its whole stance -; its turn about the point it stands on; flat on the ground, only the turn
      about up (its toe out) as the print's; a lift of a planted foot, and a tilt of a flat one, not taken (said);
    - a knee: its turn about the leg's line, only while the leg is bent KNEE_BENT in both readings and the turn
      is under KNEE_FLIP - else the IK solver straightened or flipped it (said) - and only on the sides `knees`
      gives (keyrig.knees_taken: an IK leg whose pole stayed turns by itself); None every side."""
    entry = empty_key()
    moved, ignored = [], []
    label = LABELS.get(key, key)
    # a leg the pelvis pulled straight (moved past the IK leg's reach): its foot and toes follow the hip - the
    # solver's, not the animator's (a rig's pelvis +5 cm read 1.4 cm lifts, 0.8 cm prints, 7 deg toes, 2026-10-27)
    d = np.asarray(now["pelvis"], float) - np.asarray(base["pelvis"], float)
    pulled = set()
    for side in SIDES:
        b_now, b_base = bend(now["knee"][side]), bend(base["knee"][side])
        if float(np.linalg.norm(d)) >= MIN_CM and b_now < KNEE_BENT and b_now < b_base - math.radians(0.5):
            pulled.add(side)
            ignored.append("leg_%s at %s is pulled straight by the pelvis: its foot and toes not taken"
                           % (side, label))
    for name, rot_now in now["local"].items():
        if name not in base["local"]:
            continue
        if name.startswith("ball_") and name[-1] in pulled:
            continue
        turn = base["local"][name].T @ rot_now
        deg = float(np.linalg.norm(wm.log_rot(turn)))
        if deg < MIN_TURN:
            continue
        entry["rot"][name] = wm.orthonormal(turn)
        moved.append((name, math.degrees(deg), "deg"))
    if float(np.linalg.norm(d)) >= MIN_CM:
        entry["pelvis"] = d
        moved.append(("pelvis", _signed(d), "cm"))
    up = np.asarray(walk.up, float)
    for side in SIDES:
        if side in pulled:
            continue
        name = "foot_" + side
        t = np.asarray(now["foot"][side][0], float) - np.asarray(base["foot"][side][0], float)
        r = wm.orthonormal(base["foot"][side][1].T @ now["foot"][side][1])
        angle = float(np.linalg.norm(wm.log_rot(r)))
        shifted, turned = float(np.linalg.norm(t)) >= MIN_CM, angle >= MIN_TURN
        heel, ball = ground(walk, side, frame)
        planted = max(heel, ball) > 0.5
        if planted and shifted:
            along = np.array([t[0], t[1], 0.0])
            if float(np.linalg.norm(along)) >= MIN_CM:
                entry["print"][side]["t"] = along
                moved.append((name + " print", float(np.linalg.norm(along)), "cm"))
            if abs(float(t[2])) >= MIN_CM:
                ignored.append("%s stands on the ground at %s: lifted %.1f cm, not taken (a planted foot stays "
                               "on the ground)" % (name, label, float(t[2])))
        elif shifted:
            entry["foot"][side]["t"] = t
            moved.append((name, _signed(t), "cm"))
        if turned and heel > 0.5 and ball > 0.5:          # flat: only its toe out, for the whole stance
            yaw = yaw_of(r, up)
            if abs(yaw) >= MIN_TURN:
                entry["print"][side]["yaw"] = yaw
                moved.append((name + " toe out", math.degrees(yaw), "deg"))
            if angle - abs(yaw) >= MIN_TURN:
                ignored.append("%s stands flat at %s: tilted %.1f deg, not taken (only its turn about up)"
                               % (name, label, math.degrees(angle - abs(yaw))))
        elif turned:
            entry["foot"][side]["r"] = r
            moved.append((name, math.degrees(angle), "deg"))
        if knees is not None and not knees.get(side, True):
            continue
        turn = mp.knee_turn(base["knee"][side], now["knee"][side])
        if abs(turn) >= KNEE_MIN:
            if min(bend(base["knee"][side]), bend(now["knee"][side])) < KNEE_BENT:
                ignored.append("knee_%s is nearly straight at %s: its turn (%.0f deg) not taken - the IK leg "
                               "flips there" % (side, label, math.degrees(turn)))
            elif abs(turn) > KNEE_FLIP:
                ignored.append("knee_%s flipped at %s (%.0f deg): not taken" % (side, label, math.degrees(turn)))
            else:
                entry["knee"][side] = turn
                moved.append(("knee_" + side, math.degrees(turn), "deg"))
    return entry, moved, ignored


def add(keys, key, inc):
    """`keys` with the edit `inc` added to the key `key`'s: turns composed, moves added."""
    out = dict((k, _copy(v)) for k, v in keys.items())
    entry = out.get(key) or empty_key()
    for name, turn in inc["rot"].items():
        entry["rot"][name] = wm.orthonormal(entry["rot"].get(name, np.eye(3)) @ turn)
    entry["pelvis"] = entry["pelvis"] + inc["pelvis"]
    for side in SIDES:
        entry["knee"][side] = entry["knee"][side] + inc["knee"][side]
        entry["foot"][side]["t"] = entry["foot"][side]["t"] + inc["foot"][side]["t"]
        entry["foot"][side]["r"] = wm.orthonormal(entry["foot"][side]["r"] @ inc["foot"][side]["r"])
        entry["print"][side]["t"] = entry["print"][side]["t"] + inc["print"][side]["t"]
        entry["print"][side]["yaw"] = entry["print"][side]["yaw"] + inc["print"][side]["yaw"]
    for name in [n for n, m in entry["rot"].items() if float(np.linalg.norm(wm.log_rot(m))) < 1e-9]:
        del entry["rot"][name]
    out[key] = entry
    return out


def combine(keys, key, base, now, walk, frame):
    """(the new edits, [(what moved, how much, unit)], [what was not taken]): `keys` with the key `key`'s edit
    moved by what changed from the reading `base` to `now` (increment), read on the rig at the walk's frame
    `frame`."""
    inc, moved, ignored = increment(key, base, now, walk, frame)
    return add(keys, key, inc), moved, ignored


def one_print(incs):
    """The four keys' increments with each foot's print kept on one key only - the largest: the rigs of one stance
    show the same print, and a foot moved alike on two rigs is one move, not two."""
    out = dict((k, _copy(v)) for k, v in incs.items())
    for side in SIDES:
        best = max(out, key=lambda k: float(np.linalg.norm(out[k]["print"][side]["t"])), default=None)
        turn = max(out, key=lambda k: abs(out[k]["print"][side]["yaw"]), default=None)
        for k in out:
            if k != best:
                out[k]["print"][side]["t"] = np.zeros(3)
            if k != turn:
                out[k]["print"][side]["yaw"] = 0.0
    return out


def split_common(incs):
    """({"forward": cm, "height": cm}, the increments less it): what the pelvis did alike on all four keys is a
    setting of the whole walk (2026-10-27, «цикл должен измениться по умному»: Forward and Height, the guide's
    knobs, and the walk's physics does the rest); alike = the same sign on all four, each at least COMMON_SHARE of
    the largest, the largest at least MIN_CM; the common part is the smallest. What is left is each key's."""
    common = {"forward": 0.0, "height": 0.0}
    if any(k not in incs for k in KEYS):
        return common, incs
    out = dict((k, _copy(v)) for k, v in incs.items())
    for axis, what in ((0, "forward"), (2, "height")):
        v = np.array([float(out[k]["pelvis"][axis]) for k in KEYS])
        big = float(np.abs(v).max())
        if big < MIN_CM or not (np.all(v > 0.0) or np.all(v < 0.0)) or float(np.abs(v).min()) < COMMON_SHARE * big:
            continue
        c = math.copysign(float(np.abs(v).min()), float(v[0]))
        common[what] = c
        for k in KEYS:
            out[k]["pelvis"][axis] = out[k]["pelvis"][axis] - c
    return common, out


def _signed(d):
    """A move's length for a line: signed by its up when up is most of it (the pelvis lowered reads -4.0 cm)."""
    d = np.asarray(d, float)
    n = float(np.linalg.norm(d))
    return math.copysign(n, d[2]) if abs(d[2]) >= 0.5 * n else n


def _copy(entry):
    prints = entry.get("print") or empty_print()
    return {"rot": dict((n, np.array(m, float)) for n, m in entry["rot"].items()),
            "pelvis": np.array(entry["pelvis"], float), "knee": dict(entry["knee"]),
            "foot": dict((s, {"t": np.array(entry["foot"][s]["t"], float), "r": np.array(entry["foot"][s]["r"], float)})
                         for s in SIDES),
            "print": dict((s, {"t": np.array(prints[s]["t"], float), "yaw": float(prints[s]["yaw"])}) for s in SIDES)}


def describe(moved, limit=4):
    return mp.describe(moved, limit)


def summary(keys):
    """«Contact, Down edited» - which keys hold an edit."""
    edited = [LABELS[k] for k in KEYS if k in keys and not key_empty(keys[k])]
    return ("%s edited" % ", ".join(edited)) if edited else "no key pose edited"


# ---- into the cycle ----

def mirror_name(name):
    """The bone on the other side (upperarm_l <-> upperarm_r); a bone of the middle is its own."""
    for a, b in (("_l", "_r"), ("_r", "_l")):
        if name.endswith(a):
            return name[:-len(a)] + b
    return name


def reflection(walk):
    """The mirror across the walk's middle (its side axis flipped), 3x3."""
    n = np.asarray(walk.side, float)
    return np.eye(3) - 2.0 * np.outer(n, n)


def knots(keys, steps, walk):
    """[(unwrapped frame, values)] - every step's four keys in order, each with what the edits ask there: the
    reference foot's steps as edited, the other foot's mirrored. `values`: {"rot": {bone: log vector, in the
    bone's parent frame at that frame}, "pelvis": travel coordinates, "knee": {side: radians}, "foot": {side:
    (move in travel coordinates, turn as a log vector in world axes)}}."""
    P = walk.P
    M = reflection(walk)
    ref = frames_of(steps, P)
    R = walk.clip.worlds[:, :, :3, :3]
    parent_rot = lambda name, f: wm.orthonormal(R[walk.parents[walk.index[name]], f % P])
    flip = np.array([1.0, -1.0, 1.0])
    out = []
    for step in steps:
        mirrored = step["side"] != REF_SIDE
        for key in KEYS:
            entry = keys.get(key)
            f = step[key]
            values = {"rot": {}, "pelvis": np.zeros(3), "knee": {"l": 0.0, "r": 0.0},
                      "foot": dict((s, (np.zeros(3), np.zeros(3))) for s in SIDES)}
            if entry is not None and not key_empty(entry):
                for source, Y in entry["rot"].items():
                    if source not in walk.index:
                        continue
                    if not mirrored:
                        values["rot"][source] = wm.log_rot(Y)
                        continue
                    target = mirror_name(source)
                    if target not in walk.index or walk.parents[walk.index[target]] < 0:
                        continue
                    Wp = parent_rot(source, ref[key])
                    D = Wp.T @ Y @ Wp                              # the edit as a turn in world axes
                    Dm = M @ D @ M
                    Wq = parent_rot(target, f)
                    values["rot"][target] = wm.log_rot(wm.orthonormal(Wq @ Dm @ Wq.T))
                values["pelvis"] = entry["pelvis"] * (flip if mirrored else 1.0)
                for side in SIDES:
                    to = OTHER[side] if mirrored else side
                    values["knee"][to] = -entry["knee"][side] if mirrored else entry["knee"][side]
                    t, r = entry["foot"][side]["t"], entry["foot"][side]["r"]
                    if mirrored:
                        t, r = t * flip, M @ r @ M
                    values["foot"][to] = (np.asarray(t, float), wm.log_rot(wm.orthonormal(r)))
            out.append((f, values))
    return out


def _smooth(u):
    return u * u * (3.0 - 2.0 * u)


def blended(points, f, P):
    """(the knot before, the knot after, their weights) for frame f of the cycle (0..P): each key's edit exact at
    its frame and fading to the next key's by a smoothstep - turns in log space, nothing overshooting."""
    times = [t for t, _ in points]
    n = len(points)
    first = times[0]
    x = first + ((f - first) % P)
    for i in range(n):
        a = times[i]
        b = times[i + 1] if i + 1 < n else times[0] + P
        if a <= x <= b:
            u = 0.0 if b <= a else (x - a) / float(b - a)
            return points[i][1], points[(i + 1) % n][1], 1.0 - _smooth(u), _smooth(u)
    return points[0][1], points[0][1], 1.0, 0.0


def _mix(a, b, wa, wb, names):
    """The edits between two knots, weighted (log vectors and moves alike)."""
    out = {"rot": {}, "knee": {}, "foot": {}}
    for name in names:
        va, vb = a["rot"].get(name), b["rot"].get(name)
        if va is None and vb is None:
            continue
        va = np.zeros(3) if va is None else va
        vb = np.zeros(3) if vb is None else vb
        out["rot"][name] = wa * va + wb * vb
    out["pelvis"] = wa * a["pelvis"] + wb * b["pelvis"]
    for side in SIDES:
        out["knee"][side] = wa * a["knee"][side] + wb * b["knee"][side]
        out["foot"][side] = (wa * a["foot"][side][0] + wb * b["foot"][side][0],
                             wa * a["foot"][side][1] + wb * b["foot"][side][1])
    return out


def correct(clip, keys, steps, walk):
    """A new model.Clip: `clip` (the walk's own analysed clip, walk.clip) with the key poses' edits in every
    frame (the module docstring). No edit gives the clip back as it is."""
    if is_empty(keys) or not steps:
        return clip
    names, parents = clip.names, clip.parents
    index = dict((n, j) for j, n in enumerate(names))
    W = np.asarray(clip.worlds, float)
    J, F = W.shape[:2]
    P = walk.P
    R, Pos = W[..., :3, :3], W[..., 3, :3]
    kids = mp._children(parents)
    lr, lt = np.zeros((J, F, 3, 3)), np.zeros((J, F, 3))
    for j, p in enumerate(parents):
        if p >= 0:
            back = np.swapaxes(R[p], -1, -2)
            lr[j] = R[j] @ back
            lt[j] = np.einsum("fi,fij->fj", Pos[j] - Pos[p], back)
    points = knots(keys, steps, walk)
    upper = [n for n in mp.upper_bones(walk) if n in index]
    toes = ["ball_" + s for s in SIDES if "ball_" + s in index]
    pelvis, root = index["pelvis"], index["root"]
    frames = []
    for f in range(F):
        a, b, wa, wb = blended(points, f, P)
        frames.append(_mix(a, b, wa, wb, upper + toes))
    prints = stance_prints(keys)
    for name in upper:                                   # the upper body's turns, in the parent's frame
        j = index[name]
        for f in range(F):
            v = frames[f]["rot"].get(name)
            if v is not None and float(np.linalg.norm(v)) > 1e-12:
                lr[j, f] = lr[j, f] @ wm.exp_rot(v)
    for f in range(F):                                   # the pelvis moved over the root
        move = frames[f]["pelvis"] @ walk.basis
        lt[pelvis, f] = lt[pelvis, f] + move @ R[root, f].T
    legs = dict((s, index["thigh_" + s]) for s in SIDES if all("%s_%s" % (b, s) in index for b in mp.LEGS))
    solved, feet = set(), {}
    for side, th in legs.items():
        solved.update(mp._below(th, kids))
        feet[side] = set(mp._below(index["foot_" + side], kids))
    helper = mp._helpers(names, parents)
    follows = mp._follows(W, helper, names, parents)
    newR, newP = R.copy(), Pos.copy()
    order = mp._order(parents)
    shares = dict((s, [ground(walk, s, f) for f in range(F)]) for s in legs)
    for j in order:
        p = parents[j]
        if p < 0 or j in solved:
            continue
        newR[j] = lr[j] @ newR[p]
        newP[j] = np.einsum("fi,fij->fj", lt[j], newR[p]) + newP[p]
        for s, th in legs.items():
            if parents[th] == j:
                _solve_leg(s, th, index, lr, lt, R, Pos, newR, newP, kids, feet[s], frames, shares[s], walk,
                           prints[s], stance_weights(walk, s, F))
    out = np.array(W, copy=True)
    out[..., :3, :3], out[..., 3, :3] = newR, newP
    for j in order:                         # a helper that followed a bone rigidly follows it again
        if j not in helper:
            continue
        if j in follows:
            bone, rel = follows[j]
            out[j] = rel[None] @ out[bone]
        elif parents[j] >= 0:
            p = parents[j]
            local = W[j] @ np.linalg.inv(W[p])
            out[j] = local @ out[p]
    return wm.Clip(names, parents, out, clip.fps, clip.up, clip.name)


def stance_prints(keys):
    """{side: {"t", "yaw"}} - where each foot stands for its stances: its own prints (any key's) and the other foot's
    mirrored (the side axis flipped, the turn reversed) - the edits always mirror (the module docstring)."""
    total = empty_print()
    for entry in (keys or {}).values():
        for side in SIDES:
            stance = (entry.get("print") or {}).get(side)
            if stance:
                total[side]["t"] = total[side]["t"] + np.asarray(stance["t"], float)
                total[side]["yaw"] += float(stance["yaw"])
    flip = np.array([1.0, -1.0, 1.0])
    return dict((s, {"t": total[s]["t"] + total[OTHER[s]]["t"] * flip,
                     "yaw": total[s]["yaw"] - total[OTHER[s]]["yaw"]}) for s in SIDES)


def stance_weights(walk, side, F):
    """(F,) 0..1: 1 while the foot `side` stands (walk.contact, its strike to its lift-off), fading to 0 over half
    of the swing on either side (smoothstep) - a print holds the planted foot still and moves the swing toward it."""
    P = walk.P
    stances = sorted((float(a), float(b)) for a, b in walk.contact.get(side, []))
    out = np.zeros(F)
    if not stances:
        return out
    n = len(stances)
    for i, (a, b) in enumerate(stances):
        span = b - a
        before = (a - stances[i - 1][1]) % P if n > 1 else P - span
        after = (stances[(i + 1) % n][0] - b) % P if n > 1 else P - span
        for f in range(F):
            x = float(f)
            if (x - a) % P <= span:
                w = 1.0
            else:
                past = (x - b) % P
                ahead = (a - x) % P
                w = 0.0
                if after > 1e-9 and past <= 0.5 * after:
                    w = max(w, 1.0 - _smooth(past / (0.5 * after)))
                if before > 1e-9 and ahead <= 0.5 * before:
                    w = max(w, 1.0 - _smooth(ahead / (0.5 * before)))
            out[f] = max(out[f], w)
    return out


def result_walk(walk, worlds, name="result"):
    """The walk `walk`'s evaluated frames (J, N+1, 4, 4) read as a walk of their own (model.analyse): its steps and
    feet are what the walker does."""
    clip = wm.Clip(walk.clip.names, walk.clip.parents, np.asarray(worlds, float), walk.clip.fps, walk.clip.up, name)
    return wm.analyse(clip)


def on_result(walk, worlds, keys):
    """(the frames with the key poses' edits in them, the result read as a walk, its steps, a note): the edits put
    on the walker's evaluated animation (`worlds`, before In place) - after the parameters, the pose and the
    physics, so the walker shows at each key exactly what its rig shows (2026-10-27). Its key poses are found on
    the result itself. A result that cannot be read gets no edit, said."""
    try:
        rw = result_walk(walk, worlds)
        steps = find(rw)
    except (wm.Refusal, Refusal) as error:
        return np.asarray(worlds, float), None, None, "the key poses: %s" % error
    if is_empty(keys):
        return np.asarray(worlds, float), rw, steps, ""
    out = correct(rw.clip, keys, steps, rw)
    return np.asarray(out.worlds, float), rw, steps, ""


def in_place(worlds, walk, amount):
    """The model's In place on `worlds` (J, n+1, 4, 4): every joint moved back by the root's progress along the walk
    and by the line's climb, x `amount` (model.Walk._in_place, for frames edited after the evaluation)."""
    if amount <= 0.0:
        return worlds
    out = np.array(worlds, float, copy=True)
    root = walk.index["root"]
    n = out.shape[1] - 1
    along = (out[root, :, 3, :3] - out[root, 0, 3, :3]) @ np.asarray(walk.fwd, float)
    climb = float(np.dot(out[root, n, 3, :3] - out[root, 0, 3, :3], walk.up)) * np.arange(n + 1) / float(max(n, 1))
    shift = np.outer(along, walk.fwd) + np.outer(climb, walk.up)
    out[:, :, 3, :3] -= amount * shift[None]
    return out


def _solve_leg(side, th, index, lr, lt, R, Pos, newR, newP, kids, foot_tree, frames, shares, walk, stance=None,
               weights=None):
    """A leg on every frame: its foot (and what is under it) given the frame's edit - turned about its heel or its
    ball where that point is down, moved and turned where it is in the air, untouched where it stands flat - then
    the leg solved from its new hip onto the foot (its lengths, its plane turned the least, the knee turned about
    the leg's line by the edit's knee turn); out of reach the leg stands straight at the ankle, its shin
    stretched (the target's reach takes the pelvis down there)."""
    ca, fo = index["calf_" + side], index["foot_" + side]
    ball = index.get("ball_" + side)
    F = R.shape[1]
    parent = [k for k, v in kids.items() if th in v][0]
    hip = np.einsum("fi,fij->fj", lt[th], newR[parent]) + newP[parent]
    for f in range(F):
        h0, k0, a0 = Pos[th, f], Pos[ca, f], Pos[fo, f]
        move, turn = frames[f]["foot"][side]
        heel_down, ball_down = shares[f]
        free = 1.0 - heel_down * ball_down                  # flat on the ground: the foot stays as planted
        air = 1.0 - max(heel_down, ball_down)
        D = wm.exp_rot(free * np.asarray(turn, float)) if free > 0.0 and np.linalg.norm(turn) > 1e-12 else np.eye(3)
        T = air * (np.asarray(move, float) @ walk.basis)
        on_ball = ball_down * (1.0 - heel_down)
        pivot = a0 if ball is None else (1.0 - on_ball) * a0 + on_ball * Pos[ball, f]
        for j in foot_tree:
            newR[j, f] = R[j, f] @ D
            newP[j, f] = pivot + (Pos[j, f] - pivot) @ D + T
        w = float(weights[f]) if weights is not None else 0.0
        if stance is not None and w > 0.0:               # the print: where the foot stands for its whole stance
            centre = newP[fo, f] if ball is None else 0.5 * (newP[fo, f] + newP[ball, f])
            Dy = wm.exp_rot(w * float(stance["yaw"]) * np.asarray(walk.up, float))
            shift = w * (np.asarray(stance["t"], float) @ walk.basis)
            for j in foot_tree:
                newR[j, f] = newR[j, f] @ Dy
                newP[j, f] = centre + (newP[j, f] - centre) @ Dy + shift
        if ball is not None:                              # the toes turned in the foot's frame
            v = frames[f]["rot"].get("ball_" + side)
            if v is not None and float(np.linalg.norm(v)) > 1e-12:
                local = R[ball, f] @ R[fo, f].T
                newR[ball, f] = local @ wm.exp_rot(v) @ newR[fo, f]
                for j in mp._below(ball, kids):
                    if j == ball:
                        continue
                    q = [k for k, c in kids.items() if j in c][0]
                    newR[j, f] = (R[j, f] @ R[q, f].T) @ newR[q, f]
                    newP[j, f] = ((Pos[j, f] - Pos[q, f]) @ R[q, f].T) @ newR[q, f] + newP[q, f]
        a1 = newP[fo, f]
        l1, l2 = float(np.linalg.norm(k0 - h0)), float(np.linalg.norm(a0 - k0))
        e = mp._unit(a1 - hip[f])
        bend = k0 - h0
        knee_turn = frames[f]["knee"][side]
        if abs(knee_turn) > 1e-12:
            bend = wm.turned_about(bend, -e, knee_turn)
        knee, _, _ = wm.two_bone(hip[f], a1, l1, l2, bend, 1.0)
        rt, rc = mp._leg_turns(h0, k0, a0, hip[f], knee, a1)
        newR[th, f], newP[th, f] = R[th, f] @ rt, hip[f]
        newR[ca, f], newP[ca, f] = R[ca, f] @ rc, knee
    for j in mp._below(th, kids):
        if j in (th, ca) or j in foot_tree:
            continue
        q = [k for k, v in kids.items() if j in v][0]
        newR[j] = lr[j] @ newR[q]
        newP[j] = np.einsum("fi,fij->fj", lt[j], newR[q]) + newP[q]
