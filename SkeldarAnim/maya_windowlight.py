"""The window under the mouse is lit, and only that one (2026-10-23).

The animator: «только то [окно] на котором указатель мыши ... Это касается всех
окон нашего плагина. Ченел бокс, тайм слайдер, библеотека поз, мессенджер ... я бы
подсвечивал и стандартные окна маи такие как аутлайнер или граф эдитор».

One watch for every window: a cursor poll finds the window under the mouse - the
window Windows itself finds there (`WindowFromPoint`, so another program in front
lights nothing), walked up to the nearest thing that is a WINDOW to the animator:

- a window of ours drawn by `maya_hubwindow.WindowFrame` (a section's floating
  window, the chat): its own light (`frame.level`; a section window's `set_light`);
- any other window of ours, or a workspaceControl of ours (the Pose Library, the
  docked Time Bar), the side panel's and the Time Bar's edge hosts: a ring drawn
  over it by an input-transparent overlay (`maya_hubqt.paint_light`, no face);
- with "Maya's windows" on: a Maya workspaceControl (Outliner, Graph Editor,
  Channel Box, Attribute Editor, docked or floating) or a floating Maya window.

Never lit: the viewport, Maya's own bars (shelf, status line, time slider, ...),
the hub (its cards light themselves), the edge rail, menus, toasts, ghosts and
overlays. The light fades in and out with the hub's card light rhythm
(`maya_hubmotion`), at once with Interface animations off.

`pick` (pure) is the rule; everything Qt or Maya lives below it. State on
`sys._skeldar_windowlight` (trap 111). ⋮ -> Window light / Light Maya's windows
(optionVars `skeldarWindowLight`, `skeldarWindowLightMaya`, both on)."""

import sys
import time
import traceback

OPTIONVAR = "skeldarWindowLight"
MAYA_OPTIONVAR = "skeldarWindowLightMaya"
DEFAULT = True
MAYA_DEFAULT = True
STATE = "_skeldar_windowlight"
POLL_MS = 50
TICK_MS = 16
CONTROLS_S = 5.0            # a workspaceControl name answer kept this long
MIN_PX = 40                 # a smaller window is a bar or a sensor, never lit
OURS = "skeldar"            # every window of ours is named so
OVERLAY = "skeldarWindowLight"
RADIUS_OURS = 8             # logical px: our hosts' corners
RADIUS_MAYA = 0

#  never lit, and nothing above them either (the walk stops)
STOP = (
    "MainPane",                                   # the viewport
    "TimeSlider", "RangeSlider", "Shelf", "StatusLine", "ToolBox",
    "CommandLine", "HelpLine", "ToolSettings",
    "skeldarAnimHub",                             # its cards light themselves
    "skeldarAnimHubEdge", "skeldarAnimHubEdgeSensor",
    "skeldarChatToast", "skeldarChatCallCard",
    "skeldarRadialMenu", "skeldarRadialFinish",
    "skeldarGraphOverlayHost", "skeldarGraphOverlayGlass",
    "skeldarSidePanelBurst", "skeldarSidePanelSensor",
    "skeldarTimeBarEdgeSensor",
    OVERLAY,
)


def stopped(name):
    """True for a widget the light never reaches past."""
    if not name:
        return False
    return name in STOP or name.startswith(OVERLAY) or "Ghost" in name


def pick(chain, maya_on=True):
    """The window to light from `chain` - dicts from the widget under the mouse up to
    its top-level window, each {"name", "top", "main", "framed", "control", "skip",
    "w", "h"} - as (index, kind), kind "frame" (it draws its own light) or "ring"; or
    None. `maya_on` lets Maya's own windows light too."""
    for i, node in enumerate(chain):
        name = node.get("name") or ""
        if node.get("skip") or stopped(name):
            return None
        ours = name.startswith(OURS)
        found = None
        if node.get("framed"):
            found = (i, "frame")
        elif node.get("control"):
            found = (i, "ring") if (ours or maya_on) else None
            if found is None:
                return None
        elif node.get("top"):
            if node.get("main"):
                return None
            found = (i, "ring") if (ours or maya_on) else None
            if found is None:
                return None
        if found is not None:
            if node.get("w", MIN_PX) < MIN_PX or node.get("h", MIN_PX) < MIN_PX:
                return None
            return found
    return None


def step(level, goal, dt_ms, on_ms, off_ms):
    """`level` moved toward `goal` over `dt_ms` (the whole way in on_ms / off_ms)."""
    if level == goal:
        return level
    span = on_ms if goal > level else off_ms
    move = dt_ms / float(max(1.0, span))
    if goal > level:
        return min(goal, level + move)
    return max(goal, level - move)


# ------------------------------------------------------------------ settings

def _cmds():
    import maya.cmds as cmds
    return cmds


def _option(name, default):
    try:
        cmds = _cmds()
        if not cmds.optionVar(exists=name):
            return default
        return bool(cmds.optionVar(query=name))
    except Exception:                                        # noqa: BLE001
        return default


def enabled():
    return _option(OPTIONVAR, DEFAULT)


def maya_enabled():
    return _option(MAYA_OPTIONVAR, MAYA_DEFAULT)


def set_enabled(on):
    _cmds().optionVar(intValue=(OPTIONVAR, int(bool(on))))
    if on:
        ensure()
        return "Window light: the window under the mouse is lit"
    stop()
    return "Window light off"


def set_maya_enabled(on):
    _cmds().optionVar(intValue=(MAYA_OPTIONVAR, int(bool(on))))
    st = _state()
    if st.get("light") is not None:
        st["light"].maya_on = bool(on)
        st["light"].poll(force=True)
    return ("Maya's windows light under the mouse too" if on
            else "Only our windows light under the mouse")


def _state():
    st = getattr(sys, STATE, None)
    if st is None:
        st = {"light": None}
        setattr(sys, STATE, st)
    return st


def ensure():
    """Start the watch when it is on and Maya has a UI (the hub's build calls this)."""
    if not enabled():
        return None
    st = _state()
    light = st.get("light")
    if light is not None and light.alive() and type(light) is Light:
        return light
    if light is not None:
        light.stop()
    import maya_hubqt as hubqt
    if not hubqt.available():
        return None
    light = Light()
    light.start()
    st["light"] = light
    return light


def stop():
    st = _state()
    light = st.get("light")
    st["light"] = None
    if light is not None:
        light.stop()


def reload_live():
    """An install purged our modules: the old watch goes, a new one starts."""
    stop()
    return ensure()


# ------------------------------------------------------------------ Qt part

_CLASSES = {}


def _overlay_class():
    if "overlay" not in _CLASSES:
        import maya_hubqt as hubqt
        q = hubqt.qt()
        QtCore, QtWidgets = q.QtCore, q.QtWidgets

        class Overlay(QtWidgets.QWidget):
            """An input-transparent window over a target, painting the card light's
            ring and glow at `level`."""

            def __init__(self, scale, radius, parent=None):
                flags = (QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint
                         | QtCore.Qt.WindowTransparentForInput
                         | QtCore.Qt.NoDropShadowWindowHint)
                super(Overlay, self).__init__(parent, flags)
                self.setObjectName(OVERLAY)
                self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
                self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
                self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating, True)
                self.setFocusPolicy(QtCore.Qt.NoFocus)
                self.scale = scale
                self.radius = radius
                self.level = 0.0
                self.goal = 0.0
                self.broken = False

            def paintEvent(self, event):                   # noqa: N802
                if self.broken or self.level <= 0.002:
                    return
                try:
                    hubqt.paint_light(self, self.level, 0.0, self.scale,
                                      radius=self.radius, face=False)
                except Exception:                            # noqa: BLE001
                    self.broken = True
                    traceback.print_exc()

        _CLASSES["overlay"] = Overlay
    return _CLASSES["overlay"]


def _follower_class():
    """An event filter that keeps a ring on its window AS it moves: a dragged Maya
    window sends Move on every step, the 50 ms poll trailed behind it (2026-10-23,
    «рамка отстает и доганяет окно»)."""
    if "follower" not in _CLASSES:
        import maya_hubqt as hubqt
        q = hubqt.qt()
        QtCore = q.QtCore
        kinds = (QtCore.QEvent.Move, QtCore.QEvent.Resize, QtCore.QEvent.Show,
                 QtCore.QEvent.Hide)

        class Follower(QtCore.QObject):

            def __init__(self, light):
                super(Follower, self).__init__()
                self.light = light

            def eventFilter(self, obj, event):             # noqa: N802
                try:
                    if event.type() in kinds:
                        self.light._follow()
                except Exception:                            # noqa: BLE001
                    traceback.print_exc()
                return False

        _CLASSES["follower"] = Follower
    return _CLASSES["follower"]


def _parent_of(q, widget):
    """`widget`'s parent widget by Qt's own method: animBot's widgets carry an
    attribute named `parentWidget`, and `widget.parentWidget()` raised «object
    is not callable» on every poll over them (2026-10-28)."""
    return q.QtWidgets.QWidget.parentWidget(widget)


def _ptr(q, widget):
    try:
        return int(q.shiboken.getCppPointer(widget)[0])
    except Exception:                                        # noqa: BLE001
        return 0


def _main_window(q):
    try:
        import maya.OpenMayaUI as omui
        ptr = omui.MQtUtil.mainWindow()
        return int(ptr) if ptr is not None else 0
    except Exception:                                        # noqa: BLE001
        return 0


def _hwnd_at():
    """(hwnd, our process) of the window Windows finds under the cursor; None off
    Windows."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        import os
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        point = wintypes.POINT()
        if not user32.GetCursorPos(ctypes.byref(point)):
            return None
        user32.WindowFromPoint.argtypes = [wintypes.POINT]
        user32.WindowFromPoint.restype = wintypes.HWND
        hwnd = user32.WindowFromPoint(point)
        if not hwnd:
            return (0, False)
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return (int(hwnd), pid.value == os.getpid())
    except Exception:                                        # noqa: BLE001
        return None


def _parent_hwnd(hwnd):
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        user32.GetParent.argtypes = [wintypes.HWND]
        user32.GetParent.restype = wintypes.HWND
        return int(user32.GetParent(hwnd) or 0)
    except Exception:                                        # noqa: BLE001
        return 0


def widget_at(q, pos):
    """The deepest QWidget under the global `pos`, or None (another program in
    front, nothing of Maya's there)."""
    w = q.QtWidgets
    found = _hwnd_at()
    if found is None:
        return w.QApplication.widgetAt(pos)
    hwnd, ours = found
    if not hwnd or not ours:
        return None
    widget = None
    while hwnd and widget is None:
        try:
            widget = w.QWidget.find(hwnd)
        except Exception:                                    # noqa: BLE001
            widget = None
        if widget is None:
            hwnd = _parent_hwnd(hwnd)
    if widget is None:
        return None
    try:
        deeper = widget.childAt(widget.mapFromGlobal(pos))
    except Exception:                                        # noqa: BLE001
        deeper = None
    return deeper or widget


class Light(object):
    """The watch: a cursor poll choosing the window to light, one fade timer."""

    def __init__(self):
        import maya_hubqt as hubqt
        import maya_hubmotion as hubmotion
        self.hubqt = hubqt
        self.hubmotion = hubmotion
        self.q = hubqt.qt()
        self.maya_on = maya_enabled()
        self.main = _main_window(self.q)
        self.controls = {}          # name -> (is a workspaceControl, read at)
        self.target = None          # (key, kind, widget)
        self.overlays = {}          # key -> Overlay
        self.frames = {}            # key -> [frame, goal]   (frames we fade)
        self.last_pos = None
        self.last_full = 0.0
        self.tick_at = None
        self.poll_timer = None
        self.tick_timer = None
        self.follower = None
        self.watched = []           # widgets the follower listens to
        try:
            import maya_hub
            self.scale = maya_hub._scale()
        except Exception:                                    # noqa: BLE001
            self.scale = 1.0

    # -- life

    def start(self):
        QtCore = self.q.QtCore
        self.poll_timer = QtCore.QTimer()
        self.poll_timer.setInterval(POLL_MS)
        self.poll_timer.timeout.connect(self._poll_slot)
        self.poll_timer.start()
        self.tick_timer = QtCore.QTimer()
        self.tick_timer.setInterval(TICK_MS)
        self.tick_timer.timeout.connect(self._tick_slot)

    def alive(self):
        return self.poll_timer is not None and self.hubqt._valid(self.poll_timer)

    def stop(self):
        for timer in (self.poll_timer, self.tick_timer):
            try:
                if timer is not None:
                    timer.stop()
                    timer.deleteLater()
            except RuntimeError:
                pass
        self.poll_timer = self.tick_timer = None
        self._set_target(None, animate=False)
        self._unwatch()
        for overlay in list(self.overlays.values()):
            self._drop(overlay)
        self.overlays = {}
        for frame, _goal in list(self.frames.values()):
            if self.hubqt._valid(frame):
                frame.level = 0.0
                frame.update()
        self.frames = {}

    def _poll_slot(self):
        try:
            self.poll()
        except Exception:                                    # noqa: BLE001
            traceback.print_exc()

    def _tick_slot(self):
        try:
            self.tick()
        except Exception:                                    # noqa: BLE001
            traceback.print_exc()

    # -- the choice

    def _is_control(self, name):
        now = time.time()
        known = self.controls.get(name)
        if known is not None and now - known[1] < CONTROLS_S:
            return known[0]
        try:
            answer = bool(_cmds().workspaceControl(name, exists=True))
        except Exception:                                    # noqa: BLE001
            answer = False
        self.controls[name] = (answer, now)
        return answer

    def _framed(self, widget):
        frame_class = sys.modules.get("maya_hubwindow")
        if frame_class is None:
            return None
        try:
            cls = frame_class.frame_class()
        except Exception:                                    # noqa: BLE001
            return None
        if isinstance(widget, cls):
            return widget
        try:
            for child in widget.children():
                if isinstance(child, cls):
                    return child
        except RuntimeError:
            return None
        return None

    def chain(self, widget):
        """The walk from `widget` up to its window, for `pick`, and the widgets."""
        Qt = self.q.QtCore.Qt
        nodes, widgets = [], []
        while widget is not None:
            try:
                name = widget.objectName() or ""
                top = widget.isWindow()
                kind = widget.windowType() if top else None
                skip = top and kind in (Qt.Popup, Qt.ToolTip, Qt.SplashScreen)
                framed = None
                if top and name.startswith(OURS) and not stopped(name):
                    framed = self._framed(widget)
                rect = self.rect_of(widget)
                nodes.append({
                    "name": name, "top": top,
                    "main": top and _ptr(self.q, widget) == self.main,
                    "framed": framed is not None,
                    "control": bool(name) and not top and self._is_control(name),
                    "skip": skip,
                    "w": rect.width() / self.scale if rect is not None else 0,
                    "h": rect.height() / self.scale if rect is not None else 0})
                widgets.append((widget, framed))
                if top:
                    break
                widget = _parent_of(self.q, widget)
            except (RuntimeError, TypeError, AttributeError):
                break
        return nodes, widgets

    def rect_of(self, widget):
        """The global rect of what shows of `widget` (a masked host: its mask)."""
        QtCore = self.q.QtCore
        try:
            mask = widget.mask()
            local = mask.boundingRect() if not mask.isEmpty() else widget.rect()
            if local.isEmpty():
                return None
            return QtCore.QRect(widget.mapToGlobal(local.topLeft()), local.size())
        except RuntimeError:
            return None

    def poll(self, force=False):
        q = self.q
        pos = q.QtGui.QCursor.pos()
        now = time.time()
        moved = self.last_pos is None or pos != self.last_pos
        if not (moved or force or now - self.last_full > 0.5):
            return
        self.last_pos = pos
        self.last_full = now
        if q.QtWidgets.QApplication.mouseButtons() != q.QtCore.Qt.NoButton \
                and self.target is not None:
            self._follow()          # a drag keeps its window lit
            return
        widget = widget_at(q, pos)
        chosen = None
        if widget is not None:
            nodes, widgets = self.chain(widget)
            found = pick(nodes, self.maya_on)
            if found is not None:
                index, kind = found
                target, frame = widgets[index]
                if kind == "frame":
                    chosen = (_ptr(q, frame), "frame", frame)
                else:
                    chosen = (_ptr(q, target), "ring", target)
        self._set_target(chosen, animate=self.hubmotion.enabled())
        self._follow()

    # -- the light

    def _set_target(self, chosen, animate):
        old = self.target
        if old is not None and chosen is not None and old[0] == chosen[0]:
            return
        if old is not None:
            self._light(old, False, animate)
        self.target = chosen
        self._unwatch()
        if chosen is not None:
            self._light(chosen, True, animate)
            if chosen[1] == "ring":
                self._watch(chosen[2])

    def _watch(self, widget):
        """Listen to the ringed widget and every widget above it to its window, so
        a move or a resize re-places the ring at once."""
        if self.follower is None:
            self.follower = _follower_class()(self)
        watched = []
        try:
            while widget is not None:
                widget.installEventFilter(self.follower)
                watched.append(widget)
                if widget.isWindow():
                    break
                widget = _parent_of(self.q, widget)
        except (RuntimeError, TypeError, AttributeError):
            pass
        self.watched = watched

    def _unwatch(self):
        for widget in self.watched:
            try:
                if self.hubqt._valid(widget):
                    widget.removeEventFilter(self.follower)
            except RuntimeError:
                pass
        self.watched = []

    def _popup_of(self, frame):
        hubpop = sys.modules.get("maya_hubpop")
        if hubpop is None:
            return None
        try:
            for popup in hubpop._state()["popups"].values():
                if popup.frame is not None and _ptr(self.q, popup.frame) == \
                        _ptr(self.q, frame):
                    return popup
        except Exception:                                    # noqa: BLE001
            return None
        return None

    def _light(self, target, on, animate):
        key, kind, widget = target
        if kind == "frame":
            popup = self._popup_of(widget)
            if popup is not None:
                if popup.alive() and not popup.bursting():
                    popup.set_light(on, animate=animate)
                return
            if not self.hubqt._valid(widget):
                self.frames.pop(key, None)
                return
            self.frames[key] = [widget, 1.0 if on else 0.0]
            if not animate:
                widget.level = 1.0 if on else 0.0
                widget.update()
        else:
            overlay = self.overlays.get(key)
            if overlay is None and on:
                overlay = _overlay_class()(self.scale, self._radius(widget))
                self.overlays[key] = overlay
            if overlay is None:
                return
            overlay.goal = 1.0 if on else 0.0
            if not animate:
                overlay.level = overlay.goal
            if on:
                self._place(overlay, widget)
                overlay.show()
                overlay.raise_()
            overlay.update()
        self._run_tick()

    def _radius(self, widget):
        try:
            name = widget.objectName() or ""
        except RuntimeError:
            name = ""
        return RADIUS_OURS if name.startswith(OURS) else RADIUS_MAYA

    def _place(self, overlay, widget):
        rect = self.rect_of(widget) if self.hubqt._valid(widget) else None
        if rect is None or rect.width() < MIN_PX or rect.height() < MIN_PX:
            overlay.goal = 0.0
            return
        if overlay.geometry() != rect:
            overlay.setGeometry(rect)

    def _follow(self):
        """The lit ring kept on its window (it moves, resizes, is hidden)."""
        target = self.target
        if target is None or target[1] != "ring":
            return
        overlay = self.overlays.get(target[0])
        widget = target[2]
        if overlay is None:
            return
        try:
            visible = self.hubqt._valid(widget) and widget.isVisible()
        except RuntimeError:
            visible = False
        if not visible:
            self._set_target(None, animate=self.hubmotion.enabled())
            return
        self._place(overlay, widget)

    def _run_tick(self):
        if self.tick_timer is not None and not self.tick_timer.isActive():
            self.tick_at = time.time()
            self.tick_timer.start()

    def tick(self):
        now = time.time()
        dt = (now - (self.tick_at or now)) * 1000.0
        self.tick_at = now
        on_ms = self.hubmotion.LIGHT_IN_MS
        off_ms = self.hubmotion.LIGHT_OUT_MS
        moving = False
        for key, overlay in list(self.overlays.items()):
            if not self.hubqt._valid(overlay):
                self.overlays.pop(key, None)
                continue
            level = step(overlay.level, overlay.goal, dt, on_ms, off_ms)
            if level != overlay.level:
                overlay.level = level
                overlay.update()
            if overlay.level != overlay.goal:
                moving = True
            elif overlay.goal == 0.0:
                self.overlays.pop(key, None)
                self._drop(overlay)
        for key, (frame, goal) in list(self.frames.items()):
            if not self.hubqt._valid(frame):
                self.frames.pop(key, None)
                continue
            level = step(frame.level, goal, dt, on_ms, off_ms)
            if level != frame.level:
                frame.level = level
                frame.update()
            if frame.level != goal:
                moving = True
            elif goal == 0.0:
                self.frames.pop(key, None)
        if not moving and self.tick_timer is not None:
            self.tick_timer.stop()

    def _drop(self, overlay):
        try:
            overlay.hide()
            overlay.deleteLater()
        except RuntimeError:
            pass
