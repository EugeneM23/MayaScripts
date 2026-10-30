"""A test of the key flash on controls (variant B, drawn by Qt), 2026-10-19.

    exec(open(r".../keyflash_test.py").read()); install()

The controls that took a key are drawn again over the viewport - their own
curves, projected - as added accent light (a wide soft glow and a hot core)
that fades out. A frameless, click-through Qt window over each visible 3D view
does the drawing, so nothing depends on Show > Locators / NURBS Curves and
nothing is added to the scene.

install()  - listens for setKeyframe (the S key, the Channel Box's Key) and
             flashes every selected control that has curves.
flash(...) - flashes the given transforms (or the selection) by hand.
uninstall()- callbacks off, the overlays gone.
"""
import sys
import time

import maya.cmds as cmds
import maya.utils

DURATION = 0.62           # s, the whole flash
RISE = 0.06               # s, up to full
TICK_MS = 16
SAMPLES = 4               # points a span of a curve
GLOW_SCALE = 4            # the glow is drawn at a quarter of the size, then scaled up
MARGIN = 24.0             # px round the curves for the glow
GLOW_RADIUS = 2           # box radius in small pixels (x GLOW_SCALE on screen)
GLOW_PASSES = 2           # two box blurs read as a soft gaussian
GLOW_GAIN = 3.2           # the blurred mask brought back up
ACCENT = (224, 122, 54)
HOT = (255, 241, 226)
#  the hot core line: (width logical px, alpha)
CORE = (2.2, 1.0)


def _state():
    s = getattr(sys, "_skeldar_keyflash", None)
    if s is None:
        s = {}
        sys._skeldar_keyflash = s
    s.setdefault("flashes", {})
    s.setdefault("overlays", {})
    return s


def intensity(age):
    """0..1 of a flash `age` s old: a quick rise, then (1 - u)^1.6."""
    if age < 0 or age >= DURATION:
        return 0.0
    if age < RISE:
        return age / RISE
    u = (age - RISE) / (DURATION - RISE)
    return (1.0 - u) ** 1.6


# ---- the scene -----------------------------------------------------------

def _shown(node):
    """Not under a hidden or LOD-hidden parent (a hidden scene tab)."""
    path = node
    while path and path != "|":
        if not cmds.getAttr(path + ".visibility") or not cmds.getAttr(path + ".lodVisibility"):
            return False
        path = path.rsplit("|", 1)[0]
    return True


def _controls(nodes):
    out = []
    for node in nodes or []:
        if not cmds.objExists(node):
            continue
        if cmds.nodeType(node) == "nurbsCurve":
            node = cmds.listRelatives(node, parent=True, fullPath=True)[0]
        if not cmds.objectType(node, isAType="transform"):
            continue
        shapes = cmds.listRelatives(node, shapes=True, type="nurbsCurve",
                                    noIntermediate=True, fullPath=True) or []
        node = cmds.ls(node, long=True)[0]
        if shapes and _shown(node):
            out.append(node)
    return out


def _sampled(transform):
    """[(curve shape MDagPath, its sampled points in its OWN space as an Nx4
    numpy array, closed)] - read once per flash, moved by the shape's world
    matrix on every tick (a control may move while it flashes)."""
    import numpy as np
    import maya.api.OpenMaya as om
    sel = om.MSelectionList()
    try:
        sel.add(transform)
    except RuntimeError:
        return []
    path = sel.getDagPath(0)
    out = []
    for i in range(path.childCount()):
        child = path.child(i)
        if child.apiType() != om.MFn.kNurbsCurve:
            continue
        shape = om.MDagPath(path)
        shape.push(child)
        if om.MFnDagNode(shape).isIntermediateObject:
            continue
        fn = om.MFnNurbsCurve(shape)
        lo, hi = fn.knotDomain
        count = max(1, fn.numSpans) * SAMPLES + 1
        if fn.degree == 1:
            pts = [tuple(p) for p in fn.cvPositions(om.MSpace.kObject)]
        else:
            pts = [tuple(fn.getPointAtParam(lo + (hi - lo) * k / float(count - 1),
                                            om.MSpace.kObject))
                   for k in range(count)]
        local = np.array([(p[0], p[1], p[2], 1.0) for p in pts], dtype=np.float64)
        out.append((shape, local, fn.form != om.MFnNurbsCurve.kOpen))
    return out


def _world(entries):
    """All of a control's curves in world space: [(Nx4 array, closed)]."""
    import numpy as np
    out = []
    for shape, local, closed in entries:
        if not shape.isValid():
            continue
        m = np.array(list(shape.inclusiveMatrix()), dtype=np.float64).reshape(4, 4)
        out.append((local @ m, closed))
    return out


# ---- the overlays --------------------------------------------------------

def _views():
    """(view index, M3dView, its widget) for every visible 3D view."""
    import maya.api.OpenMayaUI as omui
    from shiboken6 import wrapInstance
    from PySide6 import QtWidgets
    out = []
    for i in range(omui.M3dView.numberOf3dViews()):
        view = omui.M3dView.get3dView(i)
        ptr = view.widget()
        if not ptr:
            continue
        widget = wrapInstance(int(ptr), QtWidgets.QWidget)
        if widget.isVisible() and widget.width() > 8 and widget.height() > 8:
            out.append((i, view, widget))
    return out


def _overlay_class():
    s = _state()
    if "Overlay" in s:
        return s["Overlay"]
    from PySide6 import QtCore, QtGui, QtWidgets

    class Overlay(QtWidgets.QWidget):
        """A window only as big as the flash: a translucent window costs its
        whole area on every update, so it never spans the viewport."""

        def __init__(self, index):
            parent = None
            try:
                import maya.OpenMayaUI as omui1
                from shiboken6 import wrapInstance
                parent = wrapInstance(int(omui1.MQtUtil.mainWindow()), QtWidgets.QWidget)
            except Exception:                                # noqa: BLE001
                pass
            super().__init__(parent)
            self.index = index
            self.setObjectName("skeldarKeyFlashOverlay%d" % index)
            self.setWindowFlags(QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint
                                | QtCore.Qt.WindowTransparentForInput
                                | QtCore.Qt.WindowDoesNotAcceptFocus
                                | QtCore.Qt.NoDropShadowWindowHint)
            self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
            self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating)
            self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
            self.groups = []      # [(QPainterPath in this window's pixels, level)]
            self.glow = None      # the glow at 1 / GLOW_SCALE, drawn scaled up

        def bake_glow(self):
            """The glow: the curves drawn thin into a small mask, blurred with
            numpy and tinted. Wide antialiased pens cost Qt a vector outline of
            every segment (60 ms for 160 controls); a blur costs its pixels."""
            import numpy as np
            if not self.groups:
                self.glow = None
                return
            k = 1.0 / GLOW_SCALE
            w = max(1, int(self.width() * k) + 2)
            h = max(1, int(self.height() * k) + 2)
            #  ARGB, not Grayscale8: Qt's painter drew nothing into a gray image
            mask = QtGui.QImage(w, h, QtGui.QImage.Format_ARGB32_Premultiplied)
            mask.fill(0)
            p = QtGui.QPainter(mask)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            p.scale(k, k)
            top = max(level for _, level in self.groups)
            for path, level in self.groups:
                pen = QtGui.QPen(QtGui.QColor(255, 255, 255))
                pen.setCosmetic(True)
                pen.setWidthF(1.6)
                p.setOpacity(level / top if top else 0.0)
                p.drawPath(path)
            p.end()
            a = np.frombuffer(mask.constBits(), np.uint8).reshape(h, mask.bytesPerLine() // 4, 4)
            a = a[:, :w, 3].astype(np.float32) / 255.0
            for _ in range(GLOW_PASSES):
                a = _box(_box(a, GLOW_RADIUS, 0), GLOW_RADIUS, 1)
            a = np.clip(a * (GLOW_GAIN * top), 0.0, 1.0)
            buf = np.empty((h, w, 4), np.uint8)
            buf[..., 0] = (a * ACCENT[2]).astype(np.uint8)       # B G R A, premultiplied
            buf[..., 1] = (a * ACCENT[1]).astype(np.uint8)
            buf[..., 2] = (a * ACCENT[0]).astype(np.uint8)
            buf[..., 3] = (a * 255).astype(np.uint8)
            self._glow_buf = buf
            self.glow = QtGui.QImage(buf.data, w, h, w * 4,
                                     QtGui.QImage.Format_ARGB32_Premultiplied)

        def paintEvent(self, event):
            if not self.groups:
                return
            p = QtGui.QPainter(self)
            p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
            if self.glow is not None:
                p.drawImage(QtCore.QRectF(0, 0, self.glow.width() * GLOW_SCALE,
                                          self.glow.height() * GLOW_SCALE), self.glow)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            p.setCompositionMode(QtGui.QPainter.CompositionMode_Plus)
            for path, level in self.groups:
                grow = 1.0 + 0.6 * level
                pen = QtGui.QPen(QtGui.QColor(HOT[0], HOT[1], HOT[2], int(255 * CORE[1] * level)))
                pen.setWidthF(CORE[0] * grow)
                pen.setCosmetic(True)
                pen.setCapStyle(QtCore.Qt.RoundCap)
                pen.setJoinStyle(QtCore.Qt.RoundJoin)
                p.strokePath(path, pen)
            p.end()

    s["Overlay"] = Overlay
    return Overlay


def _box(a, r, axis):
    """A box blur of radius r along an axis (running sums, edges padded 0)."""
    import numpy as np
    pad = [(0, 0), (0, 0)]
    pad[axis] = (r + 1, r)
    c = np.cumsum(np.pad(a, pad), axis=axis, dtype=np.float32)
    n = a.shape[axis]
    hi = np.take(c, np.arange(2 * r + 1, 2 * r + 1 + n), axis=axis)
    lo = np.take(c, np.arange(0, n), axis=axis)
    return (hi - lo) / float(2 * r + 1)


def _view_matrix(view, widget):
    """World -> this widget's pixels as one 4x4 (row vectors) and the size;
    the camera's modelView . projection, then NDC to pixels."""
    import numpy as np
    mv = np.array(list(view.modelViewMatrix()), dtype=np.float64).reshape(4, 4)
    pr = np.array(list(view.projectionMatrix()), dtype=np.float64).reshape(4, 4)
    return mv @ pr, float(widget.width()), float(widget.height())


def _to_pixels(clip, w, h):
    """Clip-space rows -> (x, y) pixels from the top left; None when a point
    is behind the camera (the curve is skipped rather than drawn wrapped)."""
    import numpy as np
    wc = clip[:, 3]
    if np.any(wc <= 1e-6):
        return None
    x = (clip[:, 0] / wc * 0.5 + 0.5) * w
    y = (1.0 - (clip[:, 1] / wc * 0.5 + 0.5)) * h
    return np.stack((x, y), axis=1)


def _paint_all():
    """Every flash onto every visible view; overlays without one are hidden."""
    import numpy as np
    from PySide6 import QtCore, QtGui
    s = _state()
    cache = s.setdefault("cache", {})
    now = time.time()
    lit = {}
    for name, start in list(s["flashes"].items()):
        level = intensity(now - start)
        if now - start >= DURATION:
            s["flashes"].pop(name, None)
            cache.pop(name, None)
            continue
        if level > 0.0:
            if name not in cache:
                cache[name] = _sampled(name)
            lit.setdefault(round(level, 3), []).extend(_world(cache[name]))
    seen = set()
    for index, view, widget in _views():
        seen.add(index)
        overlay = s["overlays"].get(index)
        if overlay is None:
            overlay = _overlay_class()(index)
            s["overlays"][index] = overlay
        vp, w, h = _view_matrix(view, widget)
        projected = []          # (level, [(Nx2, closed)])
        lo = np.array([1e18, 1e18])
        hi = -lo
        for level, curves in lit.items():
            out = []
            for world, closed in curves:
                px = _to_pixels(world @ vp, w, h)
                if px is None or len(px) < 2:
                    continue
                lo = np.minimum(lo, px.min(axis=0))
                hi = np.maximum(hi, px.max(axis=0))
                out.append((px, closed))
            if out:
                projected.append((level, out))
        if not projected:
            overlay.groups = []
            if overlay.isVisible():
                overlay.hide()
            continue
        margin = MARGIN
        lo = np.maximum(lo - margin, 0.0)
        hi = np.minimum(hi + margin, (w, h))
        if hi[0] - lo[0] < 2 or hi[1] - lo[1] < 2:
            overlay.groups = []
            overlay.hide()
            continue
        groups = []
        for level, out in projected:
            path = QtGui.QPainterPath()
            for px, closed in out:
                local = px - lo
                poly = QtGui.QPolygonF([QtCore.QPointF(x, y) for x, y in local.tolist()])
                path.addPolygon(poly)
                if closed:
                    path.closeSubpath()
            groups.append((path, level))
        origin = widget.mapToGlobal(QtCore.QPoint(int(lo[0]), int(lo[1])))
        rect = QtCore.QRect(origin, QtCore.QSize(int(hi[0] - lo[0]) + 1, int(hi[1] - lo[1]) + 1))
        if overlay.geometry() != rect:
            overlay.setGeometry(rect)
        overlay.groups = groups
        overlay.bake_glow()
        if not overlay.isVisible():
            overlay.show()
        overlay.repaint()
    for index, overlay in list(s["overlays"].items()):
        if index not in seen and overlay.isVisible():
            overlay.hide()
    return bool(lit)


def _tick():
    s = _state()
    try:
        alive = _paint_all()
    except Exception as exc:                                 # noqa: BLE001
        s["error"] = repr(exc)
        alive = False
    if not alive and not s["flashes"]:
        s["timer"].stop()
        for overlay in s["overlays"].values():
            overlay.strokes = []
            overlay.hide()


def _timer():
    from PySide6 import QtCore
    s = _state()
    t = s.get("timer")
    if t is None:
        t = QtCore.QTimer()
        t.setInterval(TICK_MS)
        t.timeout.connect(_tick)
        s["timer"] = t
    return t


def flash(nodes=None):
    """Flash these transforms (or the selection's) now."""
    if nodes is None:
        nodes = cmds.ls(sl=True, long=True)
    controls = _controls(nodes)
    if not controls:
        return []
    now = time.time()
    for c in controls:
        _state()["flashes"][c] = now
    _timer().start()
    _tick()
    return controls


# ---- a one-button window -------------------------------------------------

WINDOW = "skeldarKeyFlashWindow"


def _press(*_):
    """Flash the selected controls; nothing selected: every shown control."""
    nodes = cmds.ls(sl=True, long=True)
    if not nodes:
        nodes = [cmds.listRelatives(c, parent=True, fullPath=True)[0]
                 for c in cmds.ls(type="nurbsCurve", long=True, noIntermediate=True) or []]
    done = flash(nodes)
    cmds.text(WINDOW + "Line", e=True,
              label="%d control(s) flashed" % len(done) if done else "no control to flash")


def show_window():
    if cmds.window(WINDOW, exists=True):
        cmds.deleteUI(WINDOW)
    cmds.window(WINDOW, title="Key flash", sizeable=False)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=6, columnAttach=("both", 8))
    cmds.separator(style="none", height=4)
    cmds.button(label="Flash", height=40, backgroundColor=(0.88, 0.48, 0.21),
                command=_press,
                annotation="Flash the selected controls (nothing selected: every shown control)")
    cmds.text(WINDOW + "Line", label="Select controls, or none for all", align="center")
    cmds.separator(style="none", height=4)
    cmds.showWindow(WINDOW)
    cmds.window(WINDOW, e=True, widthHeight=(220, 90))


# ---- the trigger ---------------------------------------------------------

def _command(command, *args):
    word = command.strip().split(" ", 1)[0] if command else ""
    if word == "setKeyframe":
        maya.utils.executeDeferred(flash)


def install():
    import maya.api.OpenMaya as om
    uninstall_callbacks()
    _state()["callbacks"] = [om.MCommandMessage.addCommandCallback(_command)]
    print("key flash on - press S on a control")


def uninstall_callbacks():
    import maya.api.OpenMaya as om
    for cb in _state().pop("callbacks", []):
        try:
            om.MMessage.removeCallback(cb)
        except Exception:                                    # noqa: BLE001
            pass


def uninstall():
    uninstall_callbacks()
    s = _state()
    t = s.get("timer")
    if t is not None:
        t.stop()
    s["flashes"].clear()
    s.pop("cache", None)
    for overlay in s["overlays"].values():
        try:
            overlay.hide()
            overlay.deleteLater()
        except Exception:                                    # noqa: BLE001
            pass
    s["overlays"].clear()
    s.pop("Overlay", None)        # a reloaded script makes its class afresh
    print("key flash off")
