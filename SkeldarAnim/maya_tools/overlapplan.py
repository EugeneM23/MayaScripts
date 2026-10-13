"""The Tools card's Overlap, the pure half (2026-10-13): OverRig's overlapper, computed.

OverRig's `execute_overlap_command` builds a joint chain on the objects, hangs a locator ahead of
every joint along its X (softness x the distance to the next joint), bakes it riding the joint,
aims the joint at it and shifts the locator's keys later by the lag - top to bottom, so each
locator carries its joint's track after the joints above already trail. This module computes that
construction from the members' sampled world frames, with no rig at all. numpy only (a subprocess
test pins that no `maya` module is imported).

Maya's row vectors throughout: a point p goes to `p . M`; a frame is a 4x4 with its rotation in
rows 0-2 and its position in row 3; angles in degrees; rotate orders in Maya's enum (xyz yzx zxy xzy
yxz zyx). A member's frame is its world rotation at its world rotate pivot.

Spec: docs/superpowers/specs/2026-10-13-tools-aim-overlap-design.md
"""

import collections
import math

import numpy as np

from maya_tools import knotplan

Settings = collections.namedtuple("Settings",
                                  "softness lag easing hierarchy cycled total edges")
DEFAULTS = Settings(softness=2.0, lag=1.0, easing=0.0, hierarchy=True, cycled=False,
                    total=False, edges=False)
ORDERS = ("xyz", "yzx", "zxy", "xzy", "yxz", "zyx")
EDGE_SHARE = 0.2              # Keep edges: the overlap fades in and out over a fifth at each end
CHANGED = 1e-4                # a delta under this on every frame is no change (degrees, cm)
_AXES = {"x": 0, "y": 1, "z": 2}
_EVEN = ((0, 1, 2), (1, 2, 0), (2, 0, 1))


# -------------------------------------------------------------- rotations

def axis_matrix(axis, degrees):
    """The 3x3 turning row vectors about axis 0, 1 or 2 by `degrees`."""
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    if axis == 0:
        return np.array([[1.0, 0.0, 0.0], [0.0, c, s], [0.0, -s, c]])
    if axis == 1:
        return np.array([[c, 0.0, -s], [0.0, 1.0, 0.0], [s, 0.0, c]])
    return np.array([[c, s, 0.0], [-s, c, 0.0], [0.0, 0.0, 1.0]])


def _order_name(order):
    return ORDERS[int(order)] if not isinstance(order, str) else order


def matrix_from_euler(angles, order=0):
    """Maya's rotation for euler `angles` (rx, ry, rz) in rotate order `order` (its enum or its
    name): the order's first letter applies first."""
    out = np.eye(3)
    for letter in _order_name(order):
        index = _AXES[letter]
        out = out @ axis_matrix(index, angles[index])
    return out


def euler_from_matrix(matrix, order=0):
    """(rx, ry, rz) in degrees of the rotation `matrix`, in rotate order `order`."""
    i, j, k = (_AXES[letter] for letter in _order_name(order))
    sign = 1.0 if (i, j, k) in _EVEN else -1.0
    m = np.asarray(matrix, float).T               # the column form: m = R_k . R_j . R_i
    b = math.asin(max(-1.0, min(1.0, -sign * m[k][i])))
    if abs(math.cos(b)) > 1e-9:
        a = math.atan2(sign * m[k][j], m[k][k])
        c = math.atan2(sign * m[j][i], m[i][i])
    else:                                          # the gimbal: the outer two share one turn
        a = math.atan2(-sign * m[j][k], m[j][j])
        c = 0.0
    out = [0.0, 0.0, 0.0]
    out[i], out[j], out[k] = math.degrees(a), math.degrees(b), math.degrees(c)
    return tuple(out)


def nearest_rotation(matrix3):
    """The rotation nearest a 3x3 - scale and shear taken out, a mirror flipped back."""
    u, _s, vt = np.linalg.svd(np.asarray(matrix3, float))
    out = u @ vt
    if np.linalg.det(out) < 0.0:
        u[:, -1] *= -1.0
        out = u @ vt
    return out


def frame(world, pivot):
    """A member's frame: the rotation of its world matrix (4x4) at its world rotate `pivot`."""
    out = np.eye(4)
    out[:3, :3] = nearest_rotation(np.asarray(world, float)[:3, :3])
    out[3, :3] = pivot
    return out


def inverse_frames(frames):
    """The inverses of rigid frames (..., 4, 4)."""
    frames = np.asarray(frames, float)
    out = np.zeros_like(frames)
    turned = np.swapaxes(frames[..., :3, :3], -1, -2)
    out[..., :3, :3] = turned
    out[..., 3, :3] = -np.einsum("...i,...ij->...j", frames[..., 3, :3], turned)
    out[..., 3, 3] = 1.0
    return out


# ------------------------------------------------------- the rest geometry

def rest(frames):
    """Per member (d, distance, u) from its frames at the current frame: `d` the direction to the
    next member in the member's own axes (the last: from the one before, the line continued, as
    OverRig's end joint continues its parent), `distance` its length, `u` the member's own axis
    most across `d`, made perpendicular. ValueError(index) for a member standing on the next."""
    frames = np.asarray(frames, float)
    count = len(frames)
    out = []
    for index in range(count):
        if index < count - 1:
            vector = frames[index + 1, 3, :3] - frames[index, 3, :3]
            blame = index
        else:
            vector = frames[index, 3, :3] - frames[index - 1, 3, :3]
            blame = index - 1
        distance = float(np.linalg.norm(vector))
        if distance < 1e-6:
            raise ValueError(blame)
        d = vector @ frames[index, :3, :3].T
        d = d / np.linalg.norm(d)
        axis = np.eye(3)[int(np.argmin(np.abs(d)))]
        u = axis - float(axis @ d) * d
        out.append((d, distance, u / np.linalg.norm(u)))
    return out


# ------------------------------------------------------------------ reading

def lookup(track, at, cycled=False):
    """`track` (T, k) sampled on whole window indices, read at fractional indices `at` (N,):
    Catmull-Rom between samples; outside the window its end values - or, `cycled`, wrapped over
    its first T-1 samples (the last one is the first again)."""
    track = np.asarray(track, float)
    at = np.asarray(at, float)
    count = len(track)
    base = np.floor(at).astype(int)
    frac = (at - base)[:, None]
    if cycled:
        period = max(count - 1, 1)

        def pick(index):
            return track[np.mod(index, period)]
    else:
        def pick(index):
            return track[np.clip(index, 0, count - 1)]
    p0, p1, p2, p3 = pick(base - 1), pick(base), pick(base + 1), pick(base + 2)
    return 0.5 * (2.0 * p1 + (p2 - p0) * frac
                  + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * frac ** 2
                  + (3.0 * p1 - p0 - 3.0 * p2 + p3) * frac ** 3)


def smoothed(track, sigma, cycled=False):
    """`track` (T, k) through a Gaussian of `sigma` frames, its ends held (or wrapped)."""
    track = np.asarray(track, float)
    if sigma <= 1e-6:
        return track.copy()
    radius = int(math.ceil(3.0 * sigma))
    offsets = np.arange(-radius, radius + 1)
    weights = np.exp(-0.5 * (offsets / float(sigma)) ** 2)
    weights /= weights.sum()
    count = len(track)
    index = np.arange(count)[:, None] + offsets[None, :]
    if cycled:
        index = np.mod(index, max(count - 1, 1))
    else:
        index = np.clip(index, 0, count - 1)
    return np.einsum("w,twk->tk", weights, track[index])


# ------------------------------------------------------------------- the aim

def aimed(d, u, directions, ups):
    """Rotations (N, 3, 3) turning local `d` onto each world direction and leaning local `u`
    toward each world up - an aimConstraint's frame. Where an up runs along its direction the up
    of the frame before stands in (the first: any axis across)."""
    d = np.asarray(d, float)
    u = np.asarray(u, float)
    local = np.stack([d, u, np.cross(d, u)])
    heads = np.asarray(directions, float)
    heads = heads / np.maximum(np.linalg.norm(heads, axis=1), 1e-12)[:, None]
    ups = np.asarray(ups, float)
    across = ups - np.sum(ups * heads, axis=1)[:, None] * heads
    lengths = np.linalg.norm(across, axis=1)
    out = np.empty((len(heads), 3, 3))
    previous = None
    for t, head in enumerate(heads):
        if lengths[t] > 1e-9:
            lean = across[t] / lengths[t]
        else:
            seed = previous if previous is not None else np.eye(3)[int(np.argmin(np.abs(head)))]
            lean = seed - float(seed @ head) * head
            lean = lean / np.linalg.norm(lean)
        out[t] = local.T @ np.stack([head, lean, np.cross(head, lean)])
        previous = lean
    return out


def simulate(frames, rest_frames, lag, softness, easing=0.0, cycled=False):
    """Every member's new frames (n, T, 4, 4) over the window of `frames` (n, T, 4, 4).

    Top to bottom: the member's track before its own aim, `P = l . C_above` (l its place under the
    member above in the sampled frames; the root its own frames); its target, `softness x
    distance` along its `d` in P read `lag` frames earlier, and its up, `u` in P then; the root's
    target and up smoothed over `softness x easing` frames; the new frame at P's position, its `d`
    on the target and its `u` leaning to the up. Lag 0 gives the frames back."""
    frames = np.asarray(frames, float)
    count, length = frames.shape[:2]
    geometry = rest(rest_frames)
    at = np.arange(length) - float(lag)
    out = np.empty_like(frames)
    above = None
    for index in range(count):
        if index == 0:
            track = frames[0].copy()
        else:
            track = (frames[index] @ inverse_frames(frames[index - 1])) @ above
        d, distance, u = geometry[index]
        turns = track[:, :3, :3]
        targets = ((softness * distance) * d) @ turns + track[:, 3, :3]
        ups = u @ turns
        if index == 0 and easing > 0.0:
            targets = smoothed(targets, softness * easing, cycled)
            ups = smoothed(ups, softness * easing, cycled)
        targets = lookup(targets, at, cycled)
        ups = lookup(ups, at, cycled)
        new = track.copy()
        new[:, :3, :3] = aimed(d, u, targets - track[:, 3, :3], ups)
        out[index] = new
        above = new
    return out


# ------------------------------------------------------------------ channels

def carried(parent, before, after):
    """A parent's world matrices (T, 4, 4) once the member it rides moves from its frames `before`
    to `after`: the parent keeps its place under it."""
    return np.asarray(parent, float) @ inverse_frames(before) @ np.asarray(after, float)


def rotate_values(world_rotation, parent_matrix, rotate_axis, joint_orient=None):
    """The rotate matrix that stands a node turned `world_rotation` under `parent_matrix` (4x4,
    its rotation taken): `RA^-1 . local . JO^-1` - a transform has no JO."""
    local = (np.asarray(world_rotation, float)
             @ nearest_rotation(np.asarray(parent_matrix, float)[:3, :3]).T)
    out = np.asarray(rotate_axis, float).T @ local
    if joint_orient is not None:
        out = out @ np.asarray(joint_orient, float).T
    return out


def eulers(rotations, order, base):
    """Euler rows for `rotations` (N, 3, 3) in rotate order `order`, each the equivalent nearest
    the base row it adds to - so the delta a layer holds stays small (trap 108)."""
    return [knotplan.closest_euler(tuple(float(v) for v in row),
                                   euler_from_matrix(rotation, order), int(order))
            for rotation, row in zip(rotations, base)]


def translate_delta(pivot, parent, new_pivot, new_parent):
    """How far a node's translate moves (in its parent's space) to put its pivot at `new_pivot`
    under `new_parent`, from `pivot` under `parent`: (T, 3) points, (T, 4, 4) parents."""
    def local(points, matrices):
        points = np.asarray(points, float)
        homogeneous = np.concatenate([points, np.ones((len(points), 1))], axis=1)
        return np.einsum("ti,tij->tj", homogeneous, np.linalg.inv(matrices))[:, :3]
    return local(new_pivot, new_parent) - local(pivot, parent)


def edge_weights(count, share=EDGE_SHARE):
    """Keep edges: 0 at the range's two ends, 1 from `share` of it in (a smoothstep)."""
    if count < 3:
        return np.ones(count)
    x = np.arange(count) / float(count - 1)
    reach = np.clip(np.minimum(x, 1.0 - x) / share, 0.0, 1.0)
    return reach * reach * (3.0 - 2.0 * reach)


def link_lag(settings, members):
    """The frames each link trails: Total lag shares the lag over the chain (OverRig's abs)."""
    return settings.lag / float(members) if settings.total else float(settings.lag)


def pad(lag, members):
    """Frames sampled past each end of the range, so every look back (or ahead) lands on the
    chain's real motion: the whole chain's lag and two more."""
    return int(math.ceil(abs(lag) * (members + 1))) + 2


# --------------------------------------------------------------------- lines

NOTHING = "select a chain to overlap - its root (Hierarchy on) or its members top to bottom"


def alone_refusal(name, hierarchy):
    if hierarchy:
        return ("%s has nothing of its kind below it - select a chain's root, or turn Hierarchy "
                "off and select the members top to bottom" % name)
    return ("%s alone is no chain - select the members top to bottom, or turn Hierarchy on and "
            "select the root" % name)


def settings_refusal(settings):
    if settings.softness <= 0.01:
        return "set a Softness above 0 - it is how far ahead each link looks"
    if abs(settings.lag) < 1e-6:
        return "set a Lag - at 0 the chain does not trail"
    if settings.easing < 0.0:
        return "Easing cannot be negative"
    return ""


def overlap_message(chains, settings, lag, first, last, ranged, layer, replaced, notes):
    """The line after an Overlap press."""
    links = sum(len(chain) for chain in chains)
    if len(chains) == 1:
        who = "%s > %s (%d links)" % (knotplan.leaf(chains[0][0]), knotplan.leaf(chains[0][-1]),
                                      links)
    else:
        who = "%d chains (%d links)" % (len(chains), links)
    parts = ["Overlap on %s: softness %g, lag %g fr a link, over %d-%d%s" % (
        who, settings.softness, lag, first, last, " (the highlight)" if ranged else "")]
    flags = [word for on, word in ((settings.cycled, "cycled"), (settings.edges, "edges kept"),
                                   (settings.easing > 0.0, "eased")) if on]
    if flags:
        parts.append(", ".join(flags))
    parts.append("layer %s%s" % (layer, " (the previous overlap replaced)" if replaced else ""))
    return " - ".join(parts) + "".join(" | " + note for note in notes)
