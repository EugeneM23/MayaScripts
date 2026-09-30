"""Every rig's Main is Manny's circle -- mayapy STANDALONE (it adds rigs; never the animator's scene).

    $env:QT_QPA_PLATFORM = 'offscreen'
    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/verify_main_control_size.py <old Creep_Rig.ma> <scratch dir>

2026-09-30, the animator: «Давай сделаем размер главного контрола у всех ригов такой же как и у
menny».  `<old Creep_Rig.ma>` is a copy of the asset from before the change (git show HEAD~:...),
the positive control and the procedure step's input.  Writes `<scratch>/main_control_size.png`: the
three rigs added side by side, their meshes as dots, Main's circle as it is now and -- dashed -- as
it was.
"""
import math
import os
import sys

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

REPO = "C:/!!!Work/MayaScripts"
sys.path.insert(0, REPO + "/SkeldarAnim")
for p in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass
OLD = sys.argv[1].replace("\\", "/")
SCRATCH = sys.argv[2].replace("\\", "/")
MANNY_RADIUS = 40.523612701541616
ROWS = (("Manny_Rig", -130.0), ("Creep_Rig", 0.0), ("Orc_D_Rig", 130.0))
FAILS = []
TOTAL = 9


def gate(n, ok, msg):
    print("%s gate %02d: %s" % ("PASS" if ok else "FAIL", n, msg))
    sys.stdout.flush()
    if not ok:
        FAILS.append(n)


def main_shape(main):
    return cmds.listRelatives(main, shapes=True, type="nurbsCurve", fullPath=True)[0]


def world_ring(main):
    """(radius about Main in world XZ, worst |y - Main's y|, 64 points along the curve in world)."""
    shape = main_shape(main)
    sel = om.MSelectionList()
    sel.add(shape)
    fn = om.MFnNurbsCurve(sel.getDagPath(0))
    lo, hi = fn.knotDomain
    centre = cmds.xform(main, q=True, ws=True, t=True)
    points = [fn.getPointAtParam(lo + (hi - lo) * i / 64.0, om.MSpace.kWorld) for i in range(64)]
    cvs = fn.cvPositions(om.MSpace.kWorld)
    radius = max(math.hypot(p.x - centre[0], p.z - centre[2]) for p in cvs)
    height = max(abs(p.y - centre[1]) for p in cvs)
    return radius, height, [(p.x, p.y, p.z) for p in points]


cmds.file(new=True, force=True)
import maya_rigs  # noqa: E402
from maya_scenesetup import catalog, character  # noqa: E402

# 1-2: the procedure's step, on the old Creep (AdvancedSkeleton's default circle).
cmds.file(OLD, i=True, force=True, executeScriptNodes=False)
old_radius = world_ring("|Group|MotionSystem|MainSystem|Main")[0]
gate(1, abs(old_radius - 7.757359312880715) < 1e-9,
     "control: the old Creep's Main is AdvancedSkeleton's %.6f cm, not Manny's %.6f" % (old_radius, MANNY_RADIUS))
P = REPO + "/docs/superpowers/plans/as_creep_rig_procedure.py"
proc = {"__name__": "as_creep_rig_procedure", "__file__": P}
exec(compile(open(P, encoding="utf-8").read(), P, "exec"), proc)
factor = proc["main_size"]()
again = proc["main_size"]()
fixed = world_ring("|Group|MotionSystem|MainSystem|Main")[0]
gate(2, abs(fixed - MANNY_RADIUS) < 1e-9 and abs(factor - 5.223893) < 1e-5 and again == 1.0,
     "as_creep_rig_procedure.main_size: x%.6f to %.9f cm, a second run x%r" % (factor, fixed, again))

# 3-7: the shipped rigs, added as the card adds them, side by side.
cmds.file(new=True, force=True)
added = {}
for key, x in ROWS:
    entry = catalog.character_by_key(key)
    message = character.add_character(entry, at=(x, 0.0, 0.0))
    print("//", message)
by_group = dict((r.group, r) for r in maya_rigs.rigs())
for rig in maya_rigs.rigs():
    for key, x in ROWS:
        if rig.namespace.startswith(key):
            added[key] = (rig, x)
gate(3, sorted(added) == sorted(k for k, _x in ROWS),
     "three rigs added: %s" % sorted((k, r.namespace) for k, (r, _x) in added.items()))
rings = {}
for key, (rig, x) in sorted(added.items()):
    rings[key] = world_ring(rig.main)
worst = max(abs(r[0] - MANNY_RADIUS) for r in rings.values())
gate(4, worst < 1e-9, "every rig's Main in world: %s cm (Manny's %.6f), worst %.2e"
     % (dict((k, round(v[0], 6)) for k, v in rings.items()), MANNY_RADIUS, worst))
flat = max(r[1] for r in rings.values())
gate(5, flat < 1e-9, "every circle flat on Main's plane: %.2e" % flat)
at = dict((k, cmds.xform(r.main, q=True, ws=True, t=True)) for k, (r, _x) in added.items())
gate(6, all(abs(at[k][0] - x) < 1e-6 and abs(at[k][1]) < 1e-9 and abs(at[k][2]) < 1e-6 for k, (_r, x) in added.items()),
     "Main where the drop put it, on the floor: %s" % dict((k, [round(v, 4) for v in p]) for k, p in at.items()))
wiring = []
for key, (rig, _x) in added.items():
    shape = main_shape(rig.main)
    ins = cmds.listConnections(shape, source=True, destination=False, plugs=True, connections=True) or []
    wiring.append((key, [ins[i] for i in range(0, len(ins), 2)], cmds.getAttr(rig.main + ".scale")[0],
                   cmds.getAttr(shape + ".intermediateObject")))
gate(7, all(w[1] and all(p.endswith(".visibility") for p in w[1]) and w[2] == (1.0, 1.0, 1.0) and not w[3]
            for w in wiring),
     "only the drawing changed: the shape's one input its visibility, Main's scale 1, not intermediate: %s" % wiring)

# 8: Main still carries the rig (a control, not a picture): +25 in X moves the root 25.
rig, x = added["Creep_Rig"]
before = cmds.xform(rig.skeleton_root, q=True, ws=True, t=True)
cmds.setAttr(rig.main + ".translateX", x + 25.0)
cmds.currentTime(1)
cmds.currentTime(0)
after = cmds.xform(rig.skeleton_root, q=True, ws=True, t=True)
cmds.setAttr(rig.main + ".translateX", x)
gate(8, abs(after[0] - before[0] - 25.0) < 1e-6, "the Creep's Main moves its root: %.6f for 25" % (after[0] - before[0]))

# 9: the other two rigs untouched by that move.
others = [k for k in added if k != "Creep_Rig"]
drift = max(abs(a - b) for k in others for a, b in zip(at[k], cmds.xform(added[k][0].main, q=True, ws=True, t=True)))
gate(9, drift < 1e-12, "the other rigs' Main unmoved: %.2e" % drift)

# The picture: an axonometric view (yaw 35, pitch 28), mesh vertices as dots, Main's circle orange,
# the old circle dashed.
try:
    from PySide6 import QtCore, QtGui
    app = QtGui.QGuiApplication.instance() or QtGui.QGuiApplication([])
    yaw, pitch = math.radians(35.0), math.radians(28.0)

    def project(p):
        x, y, z = p
        x1 = x * math.cos(yaw) + z * math.sin(yaw)
        z1 = -x * math.sin(yaw) + z * math.cos(yaw)
        y1 = y * math.cos(pitch) + z1 * math.sin(pitch)
        return x1, y1

    meshes = {}
    for key, (rig, _x) in added.items():
        pts = []
        for shape in cmds.ls(rig.namespace + ":*", type="mesh", long=True) or []:
            if cmds.getAttr(shape + ".intermediateObject") or not cmds.getAttr(shape + ".visibility"):
                continue
            tr = cmds.listRelatives(shape, parent=True, fullPath=True)[0]
            if not cmds.getAttr(tr + ".visibility"):
                continue
            sel = om.MSelectionList()
            sel.add(shape)
            pts.extend((p.x, p.y, p.z) for p in om.MFnMesh(sel.getDagPath(0)).getPoints(om.MSpace.kWorld)[::5])
        meshes[key] = pts
    every = [project(p) for pts in meshes.values() for p in pts] + \
            [project(p) for r in rings.values() for p in r[2]]
    xs, ys = [p[0] for p in every], [p[1] for p in every]
    W, H, pad = 1500, 760, 60
    scale = min((W - 2 * pad) / (max(xs) - min(xs)), (H - 2 * pad - 40) / (max(ys) - min(ys)))

    def to_px(p):
        x1, y1 = project(p)
        return QtCore.QPointF(pad + (x1 - min(xs)) * scale, H - pad - (y1 - min(ys)) * scale)

    image = QtGui.QImage(W, H, QtGui.QImage.Format_ARGB32)
    image.fill(QtGui.QColor("#26272b"))
    paint = QtGui.QPainter(image)
    paint.setRenderHint(QtGui.QPainter.Antialiasing)
    paint.setPen(QtCore.Qt.NoPen)
    paint.setBrush(QtGui.QColor(200, 202, 208, 55))
    for pts in meshes.values():
        for p in pts:
            paint.drawEllipse(to_px(p), 0.9, 0.9)
    for key, (rig, _x) in added.items():
        ring = rings[key][2]
        if key != "Manny_Rig":
            centre = cmds.xform(rig.main, q=True, ws=True, t=True)
            k = 7.757359312880715 / MANNY_RADIUS
            old = [(centre[0] + (p[0] - centre[0]) * k, p[1], centre[2] + (p[2] - centre[2]) * k) for p in ring]
            pen = QtGui.QPen(QtGui.QColor(150, 152, 160), 2.0, QtCore.Qt.DashLine)
            paint.setPen(pen)
            paint.setBrush(QtCore.Qt.NoBrush)
            paint.drawPolygon(QtGui.QPolygonF([to_px(p) for p in old]))
        paint.setPen(QtGui.QPen(QtGui.QColor("#e8913a"), 3.0))
        paint.setBrush(QtCore.Qt.NoBrush)
        paint.drawPolygon(QtGui.QPolygonF([to_px(p) for p in ring]))
        label = catalog.character_by_key(key).label
        base = to_px((cmds.xform(rig.main, q=True, ws=True, t=True)[0], 0.0, MANNY_RADIUS + 12))
        font = QtGui.QFont()
        font.setPixelSize(22)
        paint.setFont(font)
        paint.setPen(QtGui.QColor("#e9e9ec"))
        paint.drawText(QtCore.QRectF(base.x() - 150, base.y() + 8, 300, 30), QtCore.Qt.AlignCenter, label)
    font = QtGui.QFont()
    font.setPixelSize(20)
    paint.setFont(font)
    paint.setPen(QtGui.QColor("#e8913a"))
    paint.drawText(24, 34, "Main now: %.2f cm radius on every rig" % MANNY_RADIUS)
    paint.setPen(QtGui.QColor(170, 172, 180))
    paint.drawText(24, 62, "- - - before: %.2f cm (AdvancedSkeleton's default)" % 7.757359312880715)
    paint.end()
    out = SCRATCH + "/main_control_size.png"
    image.save(out)
    print("// picture:", out)
except Exception as exc:  # the picture is a courtesy; the gates are the proof
    print("// no picture: %s" % exc)

print("%d of %d gates failed %s" % (len(FAILS), TOTAL, FAILS))
