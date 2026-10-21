"""maya_camflight_rules - the camera flight's arithmetic, stdlib only (2026-10-21).

The animator: «переключение между камерами при использование нашего меню не мгновенное а с
анимацией ... скрипт создает подмену камеры и анимирует 0.3 сек полет от камеры персонажа в
перспективу». Asked: ortho views flatten smoothly, the flight orbits the subject.

A camera's VIEW is what the viewport shows through it, said about the point it looks at:
`pivot` (position + forward x centre of interest), `rot` (its world rotation, a quaternion),
`half` (the frame's half height at the pivot), `tan` (tan of the vertical half angle; an ortho
camera is the perspective one at `TAN_FLAT`), `ox` / `oy` (the frame's centre off the axis, in
half heights), the clip planes from the pivot, and `floor` (a perspective camera's own near
clip). The flight blends two views - pivot lerp, rotation slerp, frame size in log space, the
rest lerp - so what is looked at stays on the axis; `shot` turns a view into the substitute
camera's world matrix and clip planes, `lens` into its film back.

Row vectors (Maya's): a world matrix's rows 0-2 are the camera's right, up and back; it looks
down -Z.
"""

import collections
import math

FLIGHT_S = 0.3
TAN_FLAT = math.tan(math.radians(0.1))   # an ortho view as a perspective one: 0.1 deg half angle
MIN_COI = 1e-3
MIN_NEAR = 1e-3
MIN_FOCAL = 1.0                          # Maya's focalLength runs 0.5 .. 100000 mm
MAX_FOCAL = 100000.0
APERTURE = 1.0                           # the substitute's vertical film aperture, inches
MARKER = "skeldarCameraFlight"           # on the substitute camera's transform
SUB_NAME = ":skeldarCameraFlight"

View = collections.namedtuple("View", "pivot rot half tan ox oy near_rel far_rel floor")
Shot = collections.namedtuple("Shot", "matrix tan ox oy near far")


# ------------------------------------------------------------------ quaternions (w, x, y, z)

def _unit(v):
    n = math.sqrt(sum(c * c for c in v)) or 1.0
    return [c / n for c in v]


def quat_of(matrix):
    """The rotation of a 16-number world matrix (row vectors; scale dropped)."""
    rows = [_unit(matrix[0:3]), _unit(matrix[4:7]), _unit(matrix[8:11])]
    r = [[rows[j][i] for j in range(3)] for i in range(3)]      # the column-vector matrix
    trace = r[0][0] + r[1][1] + r[2][2]
    if trace > 0.0:
        s = math.sqrt(trace + 1.0) * 2.0
        q = (0.25 * s, (r[2][1] - r[1][2]) / s, (r[0][2] - r[2][0]) / s, (r[1][0] - r[0][1]) / s)
    elif r[0][0] > r[1][1] and r[0][0] > r[2][2]:
        s = math.sqrt(1.0 + r[0][0] - r[1][1] - r[2][2]) * 2.0
        q = ((r[2][1] - r[1][2]) / s, 0.25 * s, (r[0][1] + r[1][0]) / s, (r[0][2] + r[2][0]) / s)
    elif r[1][1] > r[2][2]:
        s = math.sqrt(1.0 + r[1][1] - r[0][0] - r[2][2]) * 2.0
        q = ((r[0][2] - r[2][0]) / s, (r[0][1] + r[1][0]) / s, 0.25 * s, (r[1][2] + r[2][1]) / s)
    else:
        s = math.sqrt(1.0 + r[2][2] - r[0][0] - r[1][1]) * 2.0
        q = ((r[1][0] - r[0][1]) / s, (r[0][2] + r[2][0]) / s, (r[1][2] + r[2][1]) / s, 0.25 * s)
    return tuple(_unit(q))


def rows_of(q):
    """The nine numbers of the rotation's rows (right, up, back), row vectors."""
    w, x, y, z = q
    r = ((1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)),
         (2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)),
         (2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)))
    return [r[j][i] for i in range(3) for j in range(3)]


def slerp(a, b, u):
    """From `a` to `b` the shorter way round."""
    dot = sum(p * q for p, q in zip(a, b))
    if dot < 0.0:
        b, dot = tuple(-c for c in b), -dot
    if dot > 0.9995:
        return tuple(_unit([p + (q - p) * u for p, q in zip(a, b)]))
    theta = math.acos(min(1.0, dot))
    sa, sb = math.sin((1.0 - u) * theta), math.sin(u * theta)
    s = math.sin(theta)
    return tuple(_unit([(p * sa + q * sb) / s for p, q in zip(a, b)]))


# ----------------------------------------------------------------------------- views

def view_of(matrix, frustum, near, far, coi, ortho):
    """A camera's view: its world matrix, its viewing frustum for the panel's aspect (left,
    right, bottom, top - at the near plane for a perspective camera, in world units for an ortho
    one), its clip planes, its centre of interest."""
    pos = matrix[12:15]
    rot = quat_of(matrix)
    back = _unit(matrix[8:11])
    dist = max(float(coi), MIN_COI)
    pivot = tuple(p - b * dist for p, b in zip(pos, back))
    left, right, bottom, top = frustum
    height = max(top - bottom, 1e-12)
    ox, oy = (left + right) / height, (bottom + top) / height
    if ortho:
        half, tan, floor = height / 2.0, TAN_FLAT, None
    else:
        tan = height / (2.0 * max(near, 1e-12))
        half, floor = dist * tan, float(near)
    return View(pivot, rot, half, tan, ox, oy, near - dist, far - dist, floor)


def _lerp(a, b, u):
    return a + (b - a) * u


def blend(a, b, u):
    """The view `u` of the way from `a` to `b` (`u` already eased)."""
    if u <= 0.0:
        return a
    if u >= 1.0:
        return b
    if a.floor is not None and b.floor is not None:
        floor = _lerp(a.floor, b.floor, u)
    else:
        floor = a.floor if a.floor is not None else b.floor
    return View(tuple(_lerp(p, q, u) for p, q in zip(a.pivot, b.pivot)),
                slerp(a.rot, b.rot, u),
                math.exp(_lerp(math.log(a.half), math.log(b.half), u)),
                _lerp(a.tan, b.tan, u), _lerp(a.ox, b.ox, u), _lerp(a.oy, b.oy, u),
                _lerp(a.near_rel, b.near_rel, u), _lerp(a.far_rel, b.far_rel, u), floor)


def shot(view):
    """The substitute camera standing as `view`: its world matrix and clip planes."""
    rows = rows_of(view.rot)
    back = rows[6:9]
    d = view.half / view.tan
    pos = [p + b * d for p, b in zip(view.pivot, back)]
    floor = view.floor if view.floor is not None else MIN_NEAR
    near = max(floor, d + view.near_rel)
    far = max(near * 2.0, d + view.far_rel)
    matrix = rows[0:3] + [0.0] + rows[3:6] + [0.0] + rows[6:9] + [0.0] + pos + [1.0]
    return Shot(matrix, view.tan, view.ox, view.oy, near, far)


def lens(tan, ox, oy, aspect):
    """The substitute's film back for a vertical half-angle tangent `tan` in a viewport of
    `aspect`: film fit Vertical, the aperture with the viewport's aspect (the focal length kept
    inside Maya's range by growing or shrinking the aperture)."""
    vertical = APERTURE
    focal = 12.7 * vertical / tan
    if focal < MIN_FOCAL:
        vertical, focal = MIN_FOCAL * tan / 12.7, MIN_FOCAL
    elif focal > MAX_FOCAL:
        vertical, focal = MAX_FOCAL * tan / 12.7, MAX_FOCAL
    return {"vertical": vertical, "horizontal": vertical * aspect, "focal": focal,
            "hoffset": ox * vertical / 2.0, "voffset": oy * vertical / 2.0}


# ------------------------------------------------------------------------------ time

def ease(u):
    """Cubic ease in and out."""
    u = min(1.0, max(0.0, u))
    if u < 0.5:
        return 4.0 * u * u * u
    return 1.0 - (-2.0 * u + 2.0) ** 3 / 2.0


def progress(elapsed, duration):
    if duration <= 0.0:
        return 1.0
    return min(1.0, max(0.0, elapsed / duration))
