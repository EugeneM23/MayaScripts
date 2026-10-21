"""Render the Armor card's tile icons from the models themselves (2026-10-01).

    $env:QT_QPA_PLATFORM = 'offscreen'
    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/make_armor_icons.py

mayapy standalone, a fresh scene per catalog.ARMOR row: its FBX imported (add mode - trap 33),
its triangles projected along the model's THINNEST bounding-box axis from the side its bulk stands
on (the outside of the piece -- an armor model's points are in its bone's axes, the bone at the
origin), the longer of the other two axes upright, flat shaded steel by the weapon icons' light
from the upper left, painted back to front over a dark rim. Written to
SkeldarAnim/assets/armor_icons/<key>.png, 256 px square with alpha (catalog.armor_icon_path).

A textured row (2026-10-21, the Playerchar's clothing) is painted in its own colours: each triangle
the texel at its uvs' centre (map1), lit the same way, so the icon reads as the piece it is.
"""
import os
import sys

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

PLUGIN = "C:/!!!Work/MayaScripts/SkeldarAnim"
sys.path.insert(0, PLUGIN)
cmds.loadPlugin("fbxmaya", quiet=True)

from PySide6.QtCore import QPointF, Qt  # noqa: E402
from PySide6.QtGui import QBrush, QColor, QGuiApplication, QImage, QPainter, QPen, QPolygonF  # noqa: E402

from maya_scenesetup import catalog  # noqa: E402

APP = QGuiApplication.instance() or QGuiApplication([sys.argv[0]])
SIZE = 256
PAD = 0.08
LIGHT = om.MVector(-0.55, 0.45, 0.70).normal()
HALF = (LIGHT + om.MVector(0, 0, 1)).normal()
STEEL = (0.58, 0.62, 0.68)
RIM = QColor("#050302")


def triangles(entry):
    """Every triangle of the row's meshes as they stand (a skeletal piece deformed in its pose),
    in the file's (= its bone's) space."""
    cmds.file(new=True, force=True)
    if entry.path.lower().endswith(".fbx"):
        mel.eval("FBXResetImport; FBXImportMode -v add;")
        cmds.file(entry.path, i=True, type="FBX", ignoreVersion=True)
    else:
        cmds.file(entry.path, i=True, type="mayaAscii", ignoreVersion=True)
    out = []
    for mesh in cmds.ls(type="mesh", noIntermediate=True, long=True) or []:
        fn = om.MFnMesh(om.MSelectionList().add(mesh).getDagPath(0))
        points = fn.getPoints(om.MSpace.kWorld)
        uvs = bool(fn.numUVs())
        for poly in range(fn.numPolygons):
            verts = list(fn.getPolygonVertices(poly))
            for i in range(1, len(verts) - 1):
                corners = (0, i, i + 1)
                tri = [om.MVector(points[verts[c]]) for c in corners]
                uv = None
                if uvs:
                    try:
                        got = [fn.getPolygonUV(poly, c) for c in corners]
                        uv = (sum(u for u, _v in got) / 3.0, sum(v for _u, v in got) / 3.0)
                    except RuntimeError:
                        uv = None
                out.append((tri, uv))
    return out


def texel(image, uv):
    """The texture's colour (0..1 floats) at `uv`, rows from the top (v 0 is the bottom)."""
    if image is None or uv is None:
        return STEEL
    x = min(image.width() - 1, max(0, int((uv[0] % 1.0) * image.width())))
    y = min(image.height() - 1, max(0, int((1.0 - (uv[1] % 1.0)) * image.height())))
    c = image.pixelColor(x, y)
    return (c.redF(), c.greenF(), c.blueF())


def view_axes(tris, clothing=False):
    """(right, up, toward the viewer) in model space: the viewer on the bulk's side of the
    thinnest axis, the longer remaining axis upright. Clothing (a skinned row, standing where the
    character wears it, facing +Z) is seen as the character is: up Y, from the front - or from
    behind when its bulk is behind (a shield on the back)."""
    pts = [p for t, _uv in tris for p in t]
    lo = [min(p[i] for p in pts) for i in range(3)]
    hi = [max(p[i] for p in pts) for i in range(3)]
    span = [hi[i] - lo[i] for i in range(3)]
    thin = span.index(min(span))
    if clothing:
        thin = 2
    rest = [i for i in range(3) if i != thin]
    up_i = 1 if clothing else max(rest, key=lambda i: span[i])
    right_i = [i for i in rest if i != up_i][0]
    toward = om.MVector(0, 0, 0)
    toward[thin] = 1.0 if sum(p[thin] for p in pts) / len(pts) > 0 else -1.0
    up = om.MVector(0, 0, 0)
    up[up_i] = 1.0
    right = up ^ toward          # right-handed: right x up = toward
    return right.normal(), up, toward


def render(entry):
    tris = triangles(entry)
    image = QImage(entry.texture) if getattr(entry, "texture", "") else None
    if image is not None and image.isNull():
        raise RuntimeError("%s: cannot read %s" % (entry.key, entry.texture))
    right, up, toward = view_axes(tris, getattr(entry, "kind", "") == catalog.SKINNED)
    flat = [([om.MVector(p * right, p * up, p * toward) for p in t], texel(image, uv)) for t, uv in tris]
    xs = [p.x for t, _c in flat for p in t]
    ys = [p.y for t, _c in flat for p in t]
    cx, cy = (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0
    k = SIZE * (1 - 2 * PAD) / max(max(xs) - min(xs), max(ys) - min(ys), 1e-6)

    def to_px(p):
        return QPointF(SIZE / 2.0 + (p.x - cx) * k, SIZE / 2.0 - (p.y - cy) * k)

    image = QImage(SIZE, SIZE, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    order = sorted(flat, key=lambda tc: tc[0][0].z + tc[0][1].z + tc[0][2].z)
    polys = [QPolygonF([to_px(p) for p in t]) for t, _c in order]
    painter.setPen(QPen(RIM, 3.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    painter.setBrush(QBrush(RIM))
    for poly in polys:
        painter.drawPolygon(poly)
    for ((a, b, c), base), poly in zip(order, polys):
        n = (b - a) ^ (c - a)
        if n.length() < 1e-12:
            continue
        n = n.normal()
        if n.z < 0:
            n = -n
        shade = 0.22 + 0.85 * max(0.0, n * LIGHT)
        spec = (0.5 if image is None else 0.18) * max(0.0, n * HALF) ** 16
        colour = QColor.fromRgbF(*[min(1.0, base[i] * shade + spec) for i in range(3)])
        painter.setPen(QPen(colour, 0.8))
        painter.setBrush(QBrush(colour))
        painter.drawPolygon(poly)
    painter.end()
    return image, len(tris)


def main():
    for entry in catalog.ARMOR:
        path = catalog.armor_icon_path(entry.key)
        if not os.path.isdir(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        image, count = render(entry)
        image.save(path)
        print("icon %-12s %d triangles -> %s" % (entry.key, count, path))
    print("DONE %d icons" % len(catalog.ARMOR))


main()
