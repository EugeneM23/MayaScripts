"""Curve controls the plugin draws on a rig (2026-10-21): 1P Setup's chest, the Root control and
the camera's control.

The animator: «нужно изменить создание узла на создание нормального контроллера (квадратной
формы красного цвета)». A control is a transform with ONE degree-1 nurbsCurve shape, coloured
through the shape's RGB override (the knots' way), drawn 2 px wide. Shapes are point lists in the
control's own space (`points`, pure); `make` builds a control, `reshape` gives an existing
transform (a knot's locator) a curve in place of its shapes.
"""

import maya.cmds as cmds

RED = (0.95, 0.12, 0.10)
YELLOW = (1.0, 0.78, 0.10)
CYAN = (0.25, 0.75, 1.0)

AXES = {"x": 0, "y": 1, "z": 2}


# -------------------------------------------------------------------- pure

def _on(axes, u, v, w=0.0):
    """A point with `u` on axes[0], `v` on axes[1] and `w` on the third axis."""
    p = [0.0, 0.0, 0.0]
    a, b = AXES[axes[0]], AXES[axes[1]]
    c = 3 - a - b
    p[a], p[b], p[c] = u, v, w
    return tuple(p)


def square(half, axes=("x", "z"), centre=(0.0, 0.0, 0.0)):
    """A closed square of half side `half` in the plane of `axes`, about `centre`."""
    corners = [(-1, -1), (1, -1), (1, 1), (-1, 1), (-1, -1)]
    return [tuple(c + o for c, o in zip(centre, _on(axes, u * half, v * half)))
            for u, v in corners]


def root_arrow(half):
    """The Root control: a square on the floor (XZ) with an arrow out of its front (+Z)."""
    h = half
    return [(-h, 0, -h), (h, 0, -h), (h, 0, h), (0.35 * h, 0, h), (0.35 * h, 0, 1.35 * h),
            (0.7 * h, 0, 1.35 * h), (0, 0, 2.0 * h), (-0.7 * h, 0, 1.35 * h),
            (-0.35 * h, 0, 1.35 * h), (-0.35 * h, 0, h), (-h, 0, h), (-h, 0, -h)]


def camera_body(size):
    """A camera in CAMERA space (Maya's: looking down -Z, up +Y): a box and its lens frustum, one
    degree-1 line through every edge."""
    w, h, d = 0.6 * size, 0.45 * size, 0.5 * size
    box = [(-w, -h, -d), (w, -h, -d), (w, h, -d), (-w, h, -d), (-w, -h, -d),
           (-w, -h, d), (w, -h, d), (w, h, d), (-w, h, d), (-w, -h, d),
           (-w, h, d), (-w, h, -d), (w, h, -d), (w, h, d), (w, -h, d), (w, -h, -d)]
    lens = 0.9 * size
    lw, lh = 0.55 * size, 0.42 * size
    frustum = [(-0.3 * w, -0.3 * h, -d), (-lw, -lh, -d - lens), (lw, -lh, -d - lens),
               (0.3 * w, -0.3 * h, -d), (lw, -lh, -d - lens), (lw, lh, -d - lens),
               (0.3 * w, 0.3 * h, -d), (lw, lh, -d - lens), (-lw, lh, -d - lens),
               (-0.3 * w, 0.3 * h, -d), (-lw, lh, -d - lens), (-lw, -lh, -d - lens)]
    top = [(-0.2 * w, h, d), (-0.2 * w, 1.7 * h, d), (0.2 * w, 1.7 * h, d), (0.2 * w, h, d)]
    return box + [(w, -h, -d)] + frustum + [(-0.3 * w, -0.3 * h, -d)] + top


def transformed(points, matrix):
    """`points` through a row-vector 4x4 `matrix` (16 floats): p · M."""
    m = matrix
    out = []
    for x, y, z in points:
        out.append((x * m[0] + y * m[4] + z * m[8] + m[12],
                    x * m[1] + y * m[5] + z * m[9] + m[13],
                    x * m[2] + y * m[6] + z * m[10] + m[14]))
    return out


def plane_of(extents):
    """The two axes a box of `extents` (x, y, z) is widest along, widest first."""
    order = sorted(range(3), key=lambda i: -extents[i])
    names = "xyz"
    return names[order[0]], names[order[1]]


# ------------------------------------------------------------------- scene

def _dress(shape, colour, width=2.0):
    cmds.setAttr(shape + ".overrideEnabled", 1)
    cmds.setAttr(shape + ".overrideRGBColors", 1)
    cmds.setAttr(shape + ".overrideColorRGB", *colour)
    try:
        cmds.setAttr(shape + ".lineWidth", width)
    except Exception:                                            # noqa: BLE001
        pass


def reshape(node, points, colour):
    """`node`'s shapes replaced by one curve through `points`. The shape's path."""
    for shape in cmds.listRelatives(node, shapes=True, fullPath=True) or []:
        cmds.delete(shape)
    temp = cmds.curve(degree=1, point=list(points))
    shape = cmds.listRelatives(temp, shapes=True, fullPath=True)[0]
    leaf = node.split("|")[-1]
    cmds.parent(shape, node, shape=True, relative=True)
    cmds.delete(temp)
    shape = cmds.listRelatives(node, shapes=True, fullPath=True)[0]
    shape = cmds.rename(shape, leaf.split(":")[-1] + "Shape")
    shape = (cmds.listRelatives(node, shapes=True, fullPath=True) or [shape])[0]
    _dress(shape, colour)
    return shape


def make(name, parent, points, colour):
    """A new control `name` under `parent` (None: world level) at identity, its curve
    `points`. Its long path."""
    node = cmds.createNode("transform", name=name, skipSelect=True)
    uuid = cmds.ls(node, uuid=True)[0]
    if parent:
        cmds.parent(node, parent, relative=True)
    node = cmds.ls(uuid, long=True)[0]
    reshape(node, points, colour)
    return cmds.ls(uuid, long=True)[0]


def local_box(node):
    """(minimum, maximum) of `node`'s curve CVs in its own space, or None."""
    lo, hi = [1e30] * 3, [-1e30] * 3
    found = False
    for shape in cmds.listRelatives(node, shapes=True, fullPath=True, type="nurbsCurve") or []:
        points = cmds.xform(shape + ".cv[*]", query=True, translation=True, objectSpace=True)
        for i in range(0, len(points or []), 3):
            found = True
            for a in range(3):
                lo[a] = min(lo[a], points[i + a])
                hi[a] = max(hi[a], points[i + a])
    return (tuple(lo), tuple(hi)) if found else None
