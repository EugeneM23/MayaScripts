"""The CoM tool's maths, pure: where the mouse puts the CoM, and what every
driver of the body does about it.

Every part of the body moves by the same world vector d («должны двигаться
все части в зависимости от карты весов», 2026-10-01): among all moves that
put the CoM at the target, that is the one with the least mass-weighted
displacement (min Σ m_p |d_p|² subject to Σ m_p d_p = M·Δ gives d_p = Δ).
A driver's local translate then takes start + d·A, where A (3x3, a row per
world axis) is measured once a press (drag.plan) because the poles follow
blends of other drivers.
"""

#  The world-space drivers of an AdvancedSkeleton rig (measured 2026-10-01 on
#  Manny, the Creep and the Orc D: everything else rides these through
#  constraints). RootX_M first - the others' follow blends read it. Main is
#  root motion and never moves.
RIG_DRIVERS = ("RootX_M", "IKLeg_L", "IKLeg_R", "IKArm_L", "IKArm_R",
               "PoleLeg_L", "PoleLeg_R", "PoleArm_L", "PoleArm_R",
               "IKSpine1_M", "IKSpine2_M", "IKSpine3_M")

#  A bare skeleton: the body, and the two IK helper roots that ride beside it.
SKELETON_DRIVERS = ("pelvis", "ik_foot_root", "ik_hand_root")

#  A ray this close to parallel with a plane misses it.
PARALLEL = 1e-6


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _add(a, b, k=1.0):
    return tuple(x + k * y for x, y in zip(a, b))


def ray_plane(origin, direction, point, normal):
    """Where a ray meets a plane, or None."""
    den = _dot(direction, normal)
    if abs(den) < PARALLEL:
        return None
    t = _dot(_add(point, origin, -1.0), normal) / den
    return _add(origin, direction, t)


def ray_line_closest(origin, direction, point, axis):
    """The point of the line (point, axis) closest to the ray."""
    w0 = _add(origin, point, -1.0)
    a, b, c = _dot(direction, direction), _dot(direction, axis), _dot(axis, axis)
    d, e = _dot(direction, w0), _dot(axis, w0)
    den = a * c - b * b
    if abs(den) < PARALLEL:
        return tuple(point)
    s = (a * e - b * d) / den
    return _add(point, axis, s)


def mode_for(modifier):
    """The draggerContext's modifier string -> the drag's mode."""
    mod = (modifier or "").lower()
    if "ctrl" in mod:
        return "vertical"
    if "shift" in mod:
        return "floor"
    return "view"


def drag_point(mode, ray, com, view_dir):
    """The CoM's new place for the mouse ray (origin, direction)."""
    origin, direction = ray
    if mode == "vertical":
        return ray_line_closest(origin, direction, com, (0.0, 1.0, 0.0))
    if mode == "floor":
        hit = ray_plane(origin, direction, com, (0.0, 1.0, 0.0))
        if hit is not None:
            return hit
    hit = ray_plane(origin, direction, com, view_dir)
    return hit if hit is not None else tuple(com)


def _inverse3(m):
    (a, b, c), (d, e, f), (g, h, i) = m
    det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    if abs(det) < 1e-12:
        raise ValueError("a parent with no inverse (scaled to zero)")
    return ((( e * i - f * h) / det, (c * h - b * i) / det, (b * f - c * e) / det),
            (( f * g - d * i) / det, (a * i - c * g) / det, (c * d - a * f) / det),
            (( d * h - e * g) / det, (b * g - a * h) / det, (a * e - b * d) / det))


def _vec_mat(v, m):
    return tuple(sum(v[r] * m[r][c] for r in range(3)) for c in range(3))


def solve_local(target, measured, parent3):
    """The local translate change that moves a node by (target - measured)
    in world, its parent's world 3x3 being `parent3` (row-vector)."""
    shortfall = _add(target, measured, -1.0)
    return _vec_mat(shortfall, _inverse3(parent3))


def apply(plan, start, d):
    """{driver: start + d·A} for a plan {driver: A}."""
    out = {}
    for driver, a in plan.items():
        out[driver] = _add(start[driver], _vec_mat(d, a))
    return out


def autokey_channels(moved, has_curve, autokey_on):
    """The (driver, attr) to key on release: Maya's own autoKey rule - a
    changed channel that already has a curve, and only with autoKey on."""
    if not autokey_on:
        return []
    return [ch for ch in moved if ch in has_curve]
