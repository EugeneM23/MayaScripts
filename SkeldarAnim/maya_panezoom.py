"""maya_panezoom - the Space tap's single / four views switch, flown in and out (2026-10-22).

See `maya_panezoom_rules` for the motion. How:

- the main pane's picture is taken BEFORE the switch: DWM's copy of Maya's main window
  (`PrintWindow`, PW_RENDERFULLCONTENT - our own top-level windows are not in it) cropped to the
  pane, each visible viewport put over it from its own colour buffer (`M3dView.readColorBuffer`)
  where DWM's copy of it is one flat colour;
- an overlay (a frameless mouse-deaf Qt.Tool owned by Maya's window, over the pane) is shown with
  that picture, so the switch underneath is never seen;
- Maya's own switch runs (`doSwitchPanes`, as Maya's hotbox), the pane is drawn and its picture
  taken again;
- the overlay flies the panel from where it stood to where it stands now, then fades onto the
  live view and goes. Nothing is recorded; the data (the layout) is switched at once.

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


def capture(pane):
    """(the pane's picture at physical size with its devicePixelRatio, {panel: rect}) or None."""
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
    rects = {}
    painter = QtGui.QPainter(image)
    try:
        for panel in _panels():
            rect = _rect_in(_panel_widget(panel), pane)
            if not rules.usable(rect):
                continue
            rects[panel] = rect
            try:
                view, widget = _view_image(panel)
            except Exception:                                # noqa: BLE001
                view, widget = None, None
            if view is None or widget is None:
                continue
            vrect = _rect_in(widget, pane)
            if not rules.usable(vrect) or not _flat(image, vrect, dpr):
                continue
            target = QtCore.QRectF(*[v * dpr for v in vrect])
            painter.drawImage(target, view)
    finally:
        painter.end()
    image.setDevicePixelRatio(dpr)
    return image, rects


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
        def __init__(self, parent=None):
            super().__init__(parent, QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint
                             | QtCore.Qt.WindowDoesNotAcceptFocus
                             | QtCore.Qt.WindowTransparentForInput)
            self.setObjectName(OVERLAY)
            self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
            self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating)
            self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
            self.zoom = None

        def paintEvent(self, event):                         # noqa: N802
            if self.zoom is not None:
                p = QtGui.QPainter(self)
                try:
                    self.zoom.paint(p)
                finally:
                    p.end()

    return Overlay


class Zoom:
    """One flight. `paint` draws it at the age the clock says; `tick` moves it on."""

    def __init__(self, kind, before, after, src, dst, panel, piece=None, clock=time.time):
        self.kind = kind
        self.before = before            # QImage, what was on screen
        self.after = after              # QImage, what is under the overlay now
        self.src, self.dst = src, dst   # the moving panel's rects, pane logical px
        self.panel = panel
        self.piece = piece              # the moving picture (a crop of `before`)
        self.clock = clock
        self.started = None
        self.overlay = None
        self.timer = None
        self.ui = 1.0

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
        before, before_rects = got
        src = before_rects.get(panel)
        if kind == rules.IN and not rules.usable(src):
            return None
        overlay = overlay_class()(pane.window())
        top = pane.mapToGlobal(QtCore.QPoint(0, 0))
        overlay.setGeometry(top.x(), top.y(), pane.width(), pane.height())
        zoom = cls(kind, before, before, src, src, panel)
        zoom.hold = True
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
        after, after_rects = got
        dst = after_rects.get(panel)
        if kind == rules.IN:
            zoom.setup(after, src, dst or (0.0, 0.0, float(pane.width()), float(pane.height())))
        else:
            full = (0.0, 0.0, float(pane.width()), float(pane.height()))
            zoom.setup(after, before_rects.get(panel) or full, dst)
        zoom.ui = float(overlay.devicePixelRatioF() or 1.0)
        zoom.run()
        return zoom

    def setup(self, after, src, dst):
        self.after = after
        self.src = src
        self.dst = dst if rules.usable(dst) else None
        self.piece = self._crop(self.before, src)
        self.hold = False

    def _crop(self, image, rect):
        from PySide6 import QtCore
        if image is None or not rules.usable(rect):
            return None
        dpr = float(image.devicePixelRatio() or 1.0)
        return image.copy(QtCore.QRect(*[int(round(v * dpr)) for v in rect]))

    def run(self):
        from PySide6 import QtCore
        self.started = self.clock()
        self.timer = QtCore.QTimer(self.overlay)
        self.timer.setInterval(TICK_MS)
        self.timer.timeout.connect(self.tick)
        self.timer.start()
        self.overlay.update()

    def age_ms(self):
        return 0.0 if self.started is None else (self.clock() - self.started) * 1000.0

    def tick(self):
        if self.overlay is None:
            return
        if self.state()["done"]:
            if _state().get("zoom") is self:
                _state()["zoom"] = None
            self.stop()
            return
        try:
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
        if self.dst is None or self.piece is None:     # nowhere to fly: the old picture fades
            age, whole = self.age_ms(), rules.total_ms(self.kind)
            return {"rect": None, "dim": 0.0, "ring": 0.0,
                    "alpha": 1.0 - min(1.0, age / whole), "done": age >= whole}
        return rules.frame(self.kind, self.age_ms(), self.src, self.dst)

    def paint(self, p, size=None):
        from PySide6 import QtCore, QtGui
        st = self.state()
        if st["alpha"] <= 0.0:
            return
        p.setOpacity(st["alpha"])
        p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        if size is None:
            size = QtCore.QRectF(0, 0, self.overlay.width(), self.overlay.height())
        if st["rect"] is None:
            p.drawImage(size, self.before)
            return
        back = self.before if self.kind == rules.IN else self.after
        p.drawImage(size, back)
        if st["dim"] > 0.0:
            p.fillRect(size, QtGui.QColor(10, 11, 13, int(255 * st["dim"])))
        rect = QtCore.QRectF(*st["rect"])
        if self.piece is not None:
            p.drawImage(rect, self.piece)
        if st["ring"] > 0.01:
            self._ring(p, rect, st["ring"])

    def _ring(self, p, rect, strength):
        from PySide6 import QtGui
        import maya_hubstyle
        accent = QtGui.QColor(maya_hubstyle.TOKENS["accent"])
        p.save()
        p.setCompositionMode(QtGui.QPainter.CompositionMode_Plus)
        p.setBrush(QtGui.QBrush())
        steps = 5
        for i in range(steps):
            reach = rules.GLOW * (i + 1) / steps
            c = QtGui.QColor(accent)
            c.setAlphaF(max(0.0, min(1.0, strength * 0.22 * (steps - i) / steps)))
            pen = QtGui.QPen(c, 1.6)
            p.setPen(pen)
            p.drawRoundedRect(rect.adjusted(-reach, -reach, reach, reach), 6 + reach, 6 + reach)
        c = QtGui.QColor(accent)
        c.setAlphaF(min(1.0, strength))
        p.setPen(QtGui.QPen(c, rules.RING))
        p.drawRoundedRect(rect, 4, 4)
        p.restore()
