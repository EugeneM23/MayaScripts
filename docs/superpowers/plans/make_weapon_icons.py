"""Render the weapon inventory's icons from the models themselves (2026-09-29).

    $env:QT_QPA_PLATFORM = 'offscreen'
    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/make_weapon_icons.py

mayapy standalone, a fresh scene per catalog weapon: its FBX imported (the
plugin's add mode - trap 33), the mesh's own triangles projected along its
thickness axis (every catalog weapon: blade +Y, guard X, thickness Z), flat
shaded by a light from the upper left with a steel highlight, painted back to
front over a dark rim so the icon reads on the inventory's near-black cells.
No model says which part is blade and which is grip (one plain material
each), so the colour is a rule of the shape: steel above the grip, bronze
where the guard widens and on a wide pommel, leather on the grip below it,
wood along a polearm's shaft; a textured row (Spear 03) is sampled from its
own image. Written to SkeldarAnim/assets/weapon_icons/<key>.png at
maya_invlook.ICON_PX per cell, with weapon_icons.json = {key: {"cells": [w,
h], "length": cm}}.
"""
import json
import math
import os
import sys

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

PLUGIN = "C:/!!!Work/MayaScripts/SkeldarAnim"
sys.path.insert(0, PLUGIN)
cmds.loadPlugin("fbxmaya", quiet=True)

from PySide6.QtCore import QPointF, Qt  # noqa: E402
from PySide6.QtGui import (QBrush, QColor, QGuiApplication, QImage,  # noqa: E402
                           QPainter, QPen, QPolygonF)

import maya_invlook as look  # noqa: E402
from maya_scenesetup import catalog  # noqa: E402

APP = QGuiApplication.instance() or QGuiApplication([sys.argv[0]])
OUT = look.icons_dir()
LIGHT = om.MVector(-0.55, 0.45, 0.70).normal()
HALF = (LIGHT + om.MVector(0, 0, 1)).normal()
STEEL = (0.64, 0.67, 0.72)
BRONZE = (0.72, 0.55, 0.26)
LEATHER = (0.40, 0.25, 0.14)
WOOD = (0.50, 0.33, 0.18)
RIM = QColor("#050302")
PAD = 0.07


def triangles(entry):
    """[(a, b, c, uv)] world points (scaled by the row) and the mean UV."""
    cmds.file(new=True, force=True)
    mel.eval("FBXResetImport; FBXImportMode -v add;")
    cmds.file(entry.path, i=True, type="FBX", ignoreVersion=True)
    out = []
    s = float(entry.scale)
    for mesh in cmds.ls(type="mesh", noIntermediate=True, long=True) or []:
        fn = om.MFnMesh(om.MSelectionList().add(mesh).getDagPath(0))
        points = fn.getPoints(om.MSpace.kWorld)
        uv_counts, uv_ids = fn.getAssignedUVs()
        us, vs = fn.getUVs()
        start = 0
        for poly in range(fn.numPolygons):
            verts = list(fn.getPolygonVertices(poly))
            ids = list(uv_ids[start:start + uv_counts[poly]]) if uv_counts[poly] else []
            start += uv_counts[poly]
            for i in range(1, len(verts) - 1):
                tri = (verts[0], verts[i], verts[i + 1])
                pts = [om.MPoint(points[v].x * s, points[v].y * s, points[v].z * s) for v in tri]
                uv = None
                if ids:
                    corners = (ids[0], ids[i], ids[i + 1])
                    uv = (sum(us[c] for c in corners) / 3.0, sum(vs[c] for c in corners) / 3.0)
                out.append((pts[0], pts[1], pts[2], uv))
    return out


def colour_of(centre, box, polearm):
    xmin, ymin, xmax, ymax = box
    length = ymax - ymin
    wide = max(abs(xmin), abs(xmax)) or 1.0
    if polearm:
        return STEEL if centre.y > ymax - 0.22 * length else WOOD
    if abs(centre.y) < 0.06 * length and abs(centre.x) > 0.45 * wide:
        return BRONZE
    if centre.y < 0:
        return BRONZE if abs(centre.x) > 0.30 * wide else LEATHER
    return STEEL


def render(entry):
    tris = triangles(entry)
    xs = [p.x for t in tris for p in t[:3]]
    ys = [p.y for t in tris for p in t[:3]]
    box = (min(xs), min(ys), max(xs), max(ys))
    length, width = box[3] - box[1], box[2] - box[0]
    cells = look.item_cells(length)
    w_px, h_px = cells[0] * look.ICON_PX, cells[1] * look.ICON_PX
    k = min(w_px * (1 - 2 * PAD) / max(width, 1e-6), h_px * (1 - 2 * PAD) / max(length, 1e-6))
    cx, cy = (box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0
    polearm = length / max(width, 1e-6) > 10.0
    texture = QImage(entry.texture) if getattr(entry, "texture", "") else None

    def to_px(p):
        return QPointF(w_px / 2.0 + (p.x - cx) * k, h_px / 2.0 - (p.y - cy) * k)

    image = QImage(w_px, h_px, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    order = sorted(tris, key=lambda t: (t[0].z + t[1].z + t[2].z))
    polys = [QPolygonF([to_px(p) for p in t[:3]]) for t in order]
    painter.setPen(QPen(RIM, 3.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    painter.setBrush(QBrush(RIM))
    for poly in polys:
        painter.drawPolygon(poly)
    for tri, poly in zip(order, polys):
        a, b, c, uv = tri
        n = ((b - a) ^ (c - a))
        if n.length() < 1e-12:
            continue
        n = n.normal()
        if n.z < 0:
            n = -n
        diffuse = max(0.0, n * LIGHT)
        centre = om.MVector((a.x + b.x + c.x) / 3.0, (a.y + b.y + c.y) / 3.0, 0.0)
        if texture is not None and uv is not None:
            px = texture.pixelColor(int((uv[0] % 1.0) * (texture.width() - 1)),
                                    int((1.0 - uv[1] % 1.0) * (texture.height() - 1)))
            base = (px.redF(), px.greenF(), px.blueF())
            gloss = 0.25
        else:
            base = colour_of(centre, box, polearm)
            gloss = 0.55 if base == STEEL else 0.2
        shade = 0.22 + 0.85 * diffuse
        if base == STEEL:
            # the blade darkens toward the guard, as Diablo's icons do
            along = (centre.y - box[1]) / max(length, 1e-6)
            shade *= 0.80 + 0.32 * along
        spec = gloss * max(0.0, n * HALF) ** 16
        rgb = [min(1.0, base[i] * shade + spec) for i in range(3)]
        colour = QColor.fromRgbF(*rgb)
        painter.setPen(QPen(colour, 0.8))
        painter.setBrush(QBrush(colour))
        painter.drawPolygon(poly)
    painter.end()
    return image, cells, length


def main():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    table = {}
    for entry in catalog.WEAPONS:
        image, cells, length = render(entry)
        path = look.icon_path(entry.key)
        image.save(path)
        table[entry.key] = {"cells": list(cells), "length": round(length, 1)}
        print("icon %-14s %s cells, %.1f cm -> %s" % (entry.key, cells, length, path))
    with open(os.path.join(OUT, "weapon_icons.json"), "w") as handle:
        json.dump(table, handle, indent=1, sort_keys=True)
    print("DONE %d icons" % len(table))


main()
