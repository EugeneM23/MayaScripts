"""maya_panezoom - the Space tap's single / four views switch, flown in and out (2026-10-22).

See `maya_panezoom_rules` for the motion. How:

- the main pane's picture is taken BEFORE the switch: DWM's copy of Maya's main window
  (`PrintWindow`, PW_RENDERFULLCONTENT - our own top-level windows are not in it) cropped to the
  pane, each visible viewport put over it from its own colour buffer (`M3dView.readColorBuffer`)
  where DWM's copy of it is one flat colour;
- an overlay (a frameless mouse-deaf opaque Qt.Tool owned by Maya's window) is shown with that
  picture over the single view's own 3D drawing area only - the panels' menu and icon bars stay
  live around it - so the switch underneath is never seen;
- Maya's own switch runs (`doSwitchPanes`, as Maya's hotbox), the pane is drawn and its picture
  taken again;
- the overlay flies the view from where it stood to where it stands now, turning from the old
  picture into the new one, then fades (its window opacity) onto the live view and goes.
  Nothing is recorded; the data (the layout) is switched at once.

Every picture is a pixmap made once, the moving one halved down in mips (a smooth scale never
shrinks a big picture much in a frame), drawn on a precise 16 ms timer.

Instant (Maya's switch alone) with ⋮ -> Interface animations off, without Qt, or when anything
of the above fails. State on `sys._skeldar_panezoom` (trap 111).
"""

import sys
import time
import traceback

import maya_panezoom_rules as rules

OVERLAY = "skeldarPaneZoom"
TICK_MS = 16
MEL_SWITCH = ('global string $gMainPane;'
              'if (`paneLayout -q -configuration $gMainPane` == "single")'
              ' doSwitchPanes(1, { "@goBack", "" });'
              ' else doSwitchPanes(1, { "single", "%s" });'
              ' updateToolbox();')


def _state():
    st = getattr(sys, "_skeldar_panezoom", None)
    if st is None:
        st = {"zoom": None}
        sys._skeldar_panezoom = st
    return st


def switch_plain(panel):
    import maya.mel as mel
    mel.eval(MEL_SWITCH % panel)


def _animations():
    try:
        import maya_hubmotion
        return maya_hubmotion.enabled()
    except Exception:                                        # noqa: BLE001
        return True


def tap(panel):
    """Single / four views, flown. Falls back to the plain switch on anything wrong."""
    finish()
    if not _animations():
        switch_plain(panel)
        return "instant"
    _state()["switched"] = False
    try:
        zoom = Zoom.start(panel)
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
        zoom = None
    if not isinstance(zoom, Zoom):
        finish()
        if not _state()["switched"]:        # never switch twice
            switch_plain(panel)
        return "instant"
    return zoom.kind


def finish():
    """End a standing flight at once (a second tap, a rebuild)."""
    zoom = _state().get("zoom")
    _state()["zoom"] = None
    if zoom is not None:
        zoom.stop()
    _destroy_strays()


def _destroy_strays():
    try:
        from PySide6 import QtWidgets
    except ImportError:
        return
    app = QtWidgets.QApplication.instance()
    if app is None:
        return
    for w in app.topLevelWidgets():
        try:
            if w.objectName() == OVERLAY:
                w.hide()
                w.deleteLater()
        except RuntimeError:
            pass


# --------------------------------------------------------------------------- Maya's side

def _wrap(ptr, cls):
    import shiboken6
    return shiboken6.wrapInstance(int(ptr), cls)


def _pane_widget():
    import maya.mel as mel
    from maya import OpenMayaUI as omui
    from PySide6 import QtWidgets
    name = mel.eval("global string $gMainPane; $tmp = $gMainPane;")
    ptr = omui.MQtUtil.findControl(name) or omui.MQtUtil.findLayout(name)
    return _wrap(ptr, QtWidgets.QWidget) if ptr else None


def _config():
    import maya.mel as mel
    return mel.eval("global string $gMainPane; paneLayout -q -configuration $gMainPane;")


def _panels():
    import maya.cmds as cmds
    shown = cmds.getPanel(visiblePanels=True) or []
    models = set(cmds.getPanel(type="modelPanel") or [])
    return [p for p in shown if p in models]


def _panel_widget(panel):
    from maya import OpenMayaUI as omui
    from PySide6 import QtWidgets
    ptr = omui.MQtUtil.findControl(panel) or omui.MQtUtil.findLayout(panel)
    return _wrap(ptr, QtWidgets.QWidget) if ptr else None


def _rect_in(widget, pane):
    from PySide6 import QtCore
    if widget is None or not widget.isVisible():
        return None
    top = widget.mapTo(pane, QtCore.QPoint(0, 0)) if pane.isAncestorOf(widget) else \
        pane.mapFromGlobal(widget.mapToGlobal(QtCore.QPoint(0, 0)))
    return (float(top.x()), float(top.y()), float(widget.width()), float(widget.height()))


def _window_rect(hwnd):
    import ctypes
    from ctypes import wintypes as wt
    user32 = ctypes.WinDLL("user32")
    user32.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
    rect = wt.RECT()
    if not user32.GetWindowRect(wt.HWND(int(hwnd)), ctypes.byref(rect)):
        return None
    return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top


def _flat(image, rect, dpr):
    """True when the picture's `rect` (logical) is one colour - DWM gave no viewport there."""
    x, y, w, h = [int(round(v * dpr)) for v in rect]
    seen = set()
    for i in range(1, 6):
        for j in range(1, 6):
            px = x + w * i // 6
            py = y + h * j // 6
            if 0 <= px < image.width() and 0 <= py < image.height():
                seen.add(image.pixel(px, py) & 0xF0F0F0)
    return len(seen) <= 1


def _view_image(panel):
    """A viewport's own colour buffer as a QImage and its widget, or (None, None)."""
    import ctypes
    import maya.api.OpenMaya as om
    import maya.api.OpenMayaUI as omui
    from PySide6 import QtGui, QtWidgets
    view = omui.M3dView.getM3dViewFromModelPanel(panel)
    img = om.MImage()
    view.readColorBuffer(img, True)
    w, h = img.getSize()                          # a list (trap 87)
    if w < 2 or h < 2:
        return None, None
    data = ctypes.string_at(img.pixels(), w * h * 4)   # pixels() is an address (trap 87)
    q = QtGui.QImage(data, w, h, w * 4, QtGui.QImage.Format_RGBA8888).copy()
    widget = _wrap(view.widget(), QtWidgets.QWidget)
    return q.mirrored(False, True), widget       # MImage starts at the lower left


def _view_widget(panel):
    import maya.api.OpenMayaUI as omui
    from PySide6 import QtWidgets
    view = omui.M3dView.getM3dViewFromModelPanel(panel)
    return _wrap(view.widget(), QtWidgets.QWidget)


def capture(pane):
    """(the pane's picture at physical size with its devicePixelRatio, {"views", "panels"}) or None.

    "views" - each visible model panel's 3D drawing area, "panels" - the whole panel (with its
    menu and icon bars), both {panel: rect} in the pane's logical px."""
    from PySide6 import QtCore, QtGui
    from maya_graphoverlay import winstyle
    main = pane.window()
    dpr = float(main.devicePixelRatioF() or 1.0)
    hwnd = int(main.effectiveWinId())
    wr = _window_rect(hwnd)
    if wr is None:
        return None
    raw = winstyle.capture(hwnd, wr[2], wr[3])
    if raw is None:
        return None
    whole = QtGui.QImage(raw, wr[2], wr[3], wr[2] * 4, QtGui.QImage.Format_RGB32).copy()
    frame_top = main.frameGeometry().topLeft()
    at = pane.mapToGlobal(QtCore.QPoint(0, 0)) - frame_top
    phys = QtCore.QRect(int(round(at.x() * dpr)), int(round(at.y() * dpr)),
                        int(round(pane.width() * dpr)), int(round(pane.height() * dpr)))
    image = whole.copy(phys)
    views, panels = {}, {}
    painter = QtGui.QPainter(image)
    try:
        for panel in _panels():
            prect = _rect_in(_panel_widget(panel), pane)
            try:
                vrect = _rect_in(_view_widget(panel), pane)
            except Exception:                                # noqa: BLE001
                vrect = None
            if not rules.usable(vrect):
                continue
            views[panel] = vrect
            if rules.usable(prect):
                panels[panel] = prect
            if not _flat(image, vrect, dpr):
                continue
            try:
                view, _widget = _view_image(panel)
            except Exception:                                # noqa: BLE001
                view = None
            if view is not None:
                painter.drawImage(QtCore.QRectF(*[v * dpr for v in vrect]), view)
    finally:
        painter.end()
    image.setDevicePixelRatio(dpr)
    return image, {"views": views, "panels": panels}


def _raise_ours(overlay):
    """Our other top-level windows (the rail, the Time Bar, the side panel) stay above it."""
    from PySide6 import QtWidgets
    for w in QtWidgets.QApplication.instance().topLevelWidgets():
        try:
            if w is not overlay and w.isVisible() and w.objectName().startswith("skeldar"):
                w.raise_()
        except RuntimeError:
            pass


# --------------------------------------------------------------------------- the flight

def overlay_class():
    from PySide6 import QtCore, QtGui, QtWidgets

    class Overlay(QtWidgets.QWidget):
        """Opaque (a layered per-pixel window costs a whole-window upload a frame): the fade is
        the window's own opacity."""

        def __init__(self, parent=None):
            super().__init__(parent, QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint
                             | QtCore.Qt.WindowDoesNotAcceptFocus
                             | QtCore.Qt.WindowTransparentForInput)
            self.setObjectName(OVERLAY)
            self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
            self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating)
            self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent)
            self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
            self.setWindowOpacity(0.999)        # layered from the start: no flash at the fade
            self.zoom = None

        def paintEvent(self, event):                         # noqa: N802
            if self.zoom is not None:
                p = QtGui.QPainter(self)
                try:
                    self.zoom.paint(p)
                finally:
                    p.end()

    return Overlay


def _pixmap(image):
    from PySide6 import QtGui
    pm = QtGui.QPixmap.fromImage(image)
    pm.setDevicePixelRatio(float(image.devicePixelRatio() or 1.0))
    return pm


def _mips(image):
    """The picture at its own size and halved down to ~160 px wide, as pixmaps, largest first:
    a smooth scale is then never asked to shrink a big picture much in one frame."""
    from PySide6 import QtCore, QtGui
    if image is None:
        return []
    out = []
    img = image
    while True:
        pm = QtGui.QPixmap.fromImage(img)
        pm.setDevicePixelRatio(1.0)
        out.append(pm)
        if img.width() <= 320 or img.height() <= 180:
            break
        img = img.scaled(max(1, img.width() // 2), max(1, img.height() // 2),
                         QtCore.Qt.IgnoreAspectRatio, QtCore.Qt.SmoothTransformation)
    return out


class Zoom:
    """One flight. `paint` draws it at the age the clock says; `tick` moves it on.

    Everything is drawn inside `area` (the single view's 3D drawing area, pane logical px): the
    overlay stands exactly there, so the panels' menu and icon bars around it stay live."""

    def __init__(self, kind, before, after, src, dst, panel, piece=None, clock=time.perf_counter,
                 area=None):
        self.kind = kind
        self.before = before            # QImage, what was on screen (the whole pane)
        self.after = after              # QImage, what is under the overlay now
        self.src, self.dst = src, dst   # the moving view's rects, pane logical px
        self.panel = panel
        self.clock = clock
        self.started = None
        self.overlay = None
        self.timer = None
        self.area = area
        self.window_fade = False        # the real overlay fades by its window opacity
        self._back = None
        self._old = None
        self._from = []                 # the old view (mips)
        self._to = []                   # the new view (mips)

    # the Maya side -------------------------------------------------------
    @classmethod
    def start(cls, panel):
        from PySide6 import QtCore, QtWidgets
        if not panel:
            return None
        pane = _pane_widget()
        if pane is None or not pane.isVisible():
            return None
        kind = rules.kind_of(_config())
        got = capture(pane)
        if got is None:
            return None
        before, seen = got
        src = seen["views"].get(panel)
        if not rules.usable(src):
            return None
        full = (0.0, 0.0, float(pane.width()), float(pane.height()))
        if kind == rules.IN:          # where the single view will draw: the pane less its bars
            outer = seen["panels"].get(panel)
            area = rules.inset(full, rules.margins(outer, src)) if outer else src
        else:
            area = src
        if not rules.usable(area):
            return None
        overlay = overlay_class()(pane.window())
        zoom = cls(kind, before, before, src, src, panel, area=area)
        zoom.window_fade = True
        zoom.hold = True
        zoom._old = zoom._back = _pixmap(before)
        zoom._place(overlay, pane)
        overlay.zoom = zoom
        zoom.overlay = overlay
        overlay.show()
        _raise_ours(overlay)
        overlay.repaint()
        QtWidgets.QApplication.processEvents()
        _state()["zoom"] = zoom
        _state()["switched"] = True
        switch_plain(panel)
        try:
            import maya.cmds as cmds
            cmds.refresh(force=True)
        except Exception:                                    # noqa: BLE001
            pass
        QtWidgets.QApplication.processEvents()
        got = capture(pane)
        if got is None:
            return None
        after, now = got
        dst = now["views"].get(panel)
        if kind == rules.IN and rules.usable(dst):
            zoom.area = dst                 # where it really draws, not where it was guessed
            zoom._place(overlay, pane)
        zoom.setup(after, src, dst)
        zoom.run()
        return zoom

    def _place(self, overlay, pane):
        from PySide6 import QtCore
        x, y, w, h = self.area
        top = pane.mapToGlobal(QtCore.QPoint(int(round(x)), int(round(y))))
        overlay.setGeometry(top.x(), top.y(), int(round(w)), int(round(h)))

    def setup(self, after, src, dst):
        self.after = after
        self.src = src
        self.dst = dst if rules.usable(dst) else None
        if self.area is None:
            image = self.before
            dpr = float(image.devicePixelRatio() or 1.0)
            self.area = (0.0, 0.0, image.width() / dpr, image.height() / dpr)
        self._old = _pixmap(self.before) if self.before is not None else None
        back = self.before if self.kind == rules.IN else after
        self._back = _pixmap(back) if back is not None else None
        self._from = _mips(self._crop(self.before, src))
        self._to = _mips(self._crop(after, self.dst)) if self.dst else []
        self.hold = False

    def _crop(self, image, rect):
        from PySide6 import QtCore
        if image is None or not rules.usable(rect):
            return None
        dpr = float(image.devicePixelRatio() or 1.0)
        return image.copy(QtCore.QRect(*[int(round(v * dpr)) for v in rect]))

    def run(self):
        from PySide6 import QtCore
        self.timer = QtCore.QTimer(self.overlay)
        self.timer.setTimerType(QtCore.Qt.PreciseTimer)
        self.timer.setInterval(TICK_MS)
        self.timer.timeout.connect(self.tick)
        self.started = self.clock()
        self.timer.start()
        self.overlay.repaint()

    def age_ms(self):
        return 0.0 if self.started is None else (self.clock() - self.started) * 1000.0

    def tick(self):
        if self.overlay is None:
            return
        st = self.state()
        if st["done"]:
            if _state().get("zoom") is self:
                _state()["zoom"] = None
            self.stop()
            return
        try:
            if self.window_fade and st["alpha"] < 1.0:
                self.overlay.setWindowOpacity(max(0.0, st["alpha"]))
            if st["rect"] is not None or not self.window_fade:
                self.overlay.repaint()
        except RuntimeError:
            self.stop()

    def stop(self):
        timer, overlay = self.timer, self.overlay
        self.timer = self.overlay = None
        try:
            if timer is not None:
                timer.stop()
            if overlay is not None:
                overlay.hide()
                overlay.deleteLater()
        except RuntimeError:
            pass

    # the picture ---------------------------------------------------------
    hold = False      # True while the switch runs under the overlay: the old picture, still

    def state(self):
        if self.hold:
            return {"rect": None, "dim": 0.0, "ring": 0.0, "alpha": 1.0, "done": False}
        if self.dst is None or not self._from:     # nowhere to fly: the old picture fades
            age, whole = self.age_ms(), rules.total_ms(self.kind)
            return {"rect": None, "dim": 0.0, "ring": 0.0,
                    "alpha": 1.0 - min(1.0, age / whole), "done": age >= whole}
        return rules.frame(self.kind, self.age_ms(), self.src, self.dst)

    def paint(self, p, size=None):
        from PySide6 import QtCore, QtGui
        st = self.state()
        if st["alpha"] <= 0.0:
            return
        if size is None:
            size = QtCore.QRectF(0, 0, self.overlay.width(), self.overlay.height())
        ax, ay, aw, ah = self.area
        area = QtCore.QRectF(ax, ay, aw, ah)
        p.save()
        p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        if not self.window_fade:
            p.setOpacity(st["alpha"])
        p.translate(size.x(), size.y())
        p.scale(size.width() / aw, size.height() / ah)
        p.translate(-ax, -ay)
        p.setClipRect(area)
        hold = st["rect"] is None          # held, or nowhere to fly: the old picture
        back = self._back
        if hold:
            back = self._old or back
        if back is not None:
            dpr = back.devicePixelRatio()
            p.drawPixmap(area, back, QtCore.QRectF(ax * dpr, ay * dpr, aw * dpr, ah * dpr))
        if hold:
            p.restore()
            return
        if st["dim"] > 0.0:
            p.fillRect(area, QtGui.QColor(10, 11, 13, int(255 * st["dim"])))
        rect = QtCore.QRectF(*st["rect"])
        device = p.transform().m11() * float(p.device().devicePixelRatioF() or 1.0)
        want = rect.width() * device
        turn = rules.mix(self.age_ms(), self.kind) if self._to else 0.0
        for mips, opacity in ((self._from, 1.0), (self._to, turn)):
            if not mips or opacity <= 0.0:
                continue
            pm = mips[rules.mip_for([m.width() for m in mips], want)]
            p.setOpacity((1.0 if self.window_fade else st["alpha"]) * opacity)
            p.drawPixmap(rect, pm, QtCore.QRectF(pm.rect()))
        p.setOpacity(1.0 if self.window_fade else st["alpha"])
        if st["ring"] > 0.01:
            self._ring(p, rect, st["ring"])
        p.restore()

    def _ring(self, p, rect, strength):
        from PySide6 import QtGui
        import maya_hubstyle
        accent = QtGui.QColor(maya_hubstyle.TOKENS["accent"])
        p.save()
        p.setCompositionMode(QtGui.QPainter.CompositionMode_Plus)
        p.setBrush(QtGui.QBrush())
        steps = 4
        for i in range(steps):
            reach = rules.GLOW * (i + 1) / steps
            c = QtGui.QColor(accent)
            c.setAlphaF(max(0.0, min(1.0, strength * 0.22 * (steps - i) / steps)))
            p.setPen(QtGui.QPen(c, 2.0))
            p.drawRoundedRect(rect.adjusted(-reach, -reach, reach, reach), 6 + reach, 6 + reach)
        c = QtGui.QColor(accent)
        c.setAlphaF(min(1.0, strength))
        p.setPen(QtGui.QPen(c, rules.RING))
        p.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 4, 4)
        p.restore()
