"""The UE Bridge list's drag: an animation carried out of the list into a viewport.

2026-10-01, the animator: «я зажимаю клавишу мышки и ташу анимацию из списка
во вьюпорт и подобно с нашим оружием если я попадаю в какой-то риг то
анимация должна перекинутся на него какбуд-то мы нажали import с опцией rig
если мы не нашли ничего то тогда нам нужно сделать new rig».

- press a row and move past Qt's start distance: the hub's shared ghost rides
  the cursor with a caption naming the target - «A_Jump · retarget onto
  Manny_Rig1» over a rig (`droptarget.clip_target`: the rig whose game
  skeleton is under the cursor), «A_Jump · a new Creep [rig] · floor (120,
  -36)» over a viewport with no rig, muted text anywhere else;
- release over a rig: the clip goes onto THAT rig as Import with the Rig mode
  would; over a viewport with no rig: onto a new rig - the one active in the
  Characters card, Manny when that is no rig - standing on the floor point
  after every bake (both the animator's, the same day); elsewhere, or back
  on the hub: nothing. Esc or the right button cancels.

Maya's textScrollList IS a QListWidget: an event filter on it and its
viewport does the whole thing, so the window stays plain `cmds`. The press
passes through (Maya selects the row as it always did) and is remembered with
its record; every MOVE while that button is held is eaten - the list neither
drags its selection to another row nor autoscrolls - and once the drag starts
a synthetic release at the press point completes the click for the list, after
which every mouse event is ours until the release (Qt's implicit grab keeps
them coming over the viewport). Everything it does to the scene goes through
`Scene`, which the tests replace. Qt is imported lazily (`maya_hubqt.qt()`).

Spec: docs/superpowers/specs/2026-10-01-uebridge-drag-to-viewport-design.md
"""

import traceback

GHOST_NAME = "skeldarClipGhost"
GHOST = 48              # logical px: the icon riding the cursor
THROTTLE_MS = 33        # the caption is re-read at most this often
DOT = "·"
OFF_HUB = "release off the hub to import"
CANCELLED = "cancelled"

#  The drags standing, by the list they are attached to.
_DRAGS = {}


def _last_line(error_text):
    lines = [line for line in (error_text or "").strip().splitlines()
             if line.strip()]
    return lines[-1] if lines else "failed"


def caption(name, aim):
    """(text, good): what the ghost says over `aim`. Pure."""
    if (aim or {}).get("kind") in ("rig", "new_rig"):
        return "%s %s %s" % (name, DOT, aim.get("text", "")), True
    return (aim or {}).get("text") or "no target", False


def dragged(start, now, threshold):
    """Whether a held press has travelled far enough to be a drag (Qt's own
    measure: the manhattan length). Pure."""
    return abs(now[0] - start[0]) + abs(now[1] - start[1]) >= threshold


# ------------------------------------------------------------------ scene

class Scene(object):
    """The real scene: what the drag asks and what a drop does to it."""

    def scale(self):
        import maya.cmds as cmds
        try:
            return float(cmds.mayaDpiSetting(query=True, realScaleValue=True)
                         or 1.0)
        except Exception:                                    # noqa: BLE001
            return 1.0

    def snapshot(self):
        from maya_scenesetup import droptarget
        from maya_uebridge import rigimport
        self._new_label = rigimport.new_rig_entry().label
        return droptarget.rig_snapshot()

    def target(self, gx, gy, snap):
        from maya_scenesetup import droptarget
        label = getattr(self, "_new_label", None)
        if label is None:
            from maya_uebridge import rigimport
            label = self._new_label = rigimport.new_rig_entry().label
        return droptarget.clip_target(gx, gy, snap, self.scale(), label)

    def over_hub(self, gx, gy):
        import maya_hubqt
        return maya_hubqt.on_hub(gx, gy)

    def drop(self, record, aim):
        """The import, one idle later: the ghost is gone and the mouse free
        before the editor's round trip blocks Maya for seconds. A failure
        reaches the status line (`window._run`)."""
        import maya.utils
        from maya_uebridge import window

        def run():
            window._run(lambda: window.import_dropped(record, aim),
                        busy="exporting from the editor...")

        maya.utils.executeDeferred(run)
        return "%s %s %s..." % (record.name, DOT, aim.get("text", ""))

    def say(self, text):
        try:
            from maya_uebridge import window
            window._status(text)
        except Exception:                                    # noqa: BLE001
            pass


# -------------------------------------------------------------------- Qt

_CLASSES = {}


def _classes():
    """The filter class, built on first use (Qt imported here)."""
    if _CLASSES:
        return _CLASSES
    import maya_hubqt

    q = maya_hubqt.qt()
    QtCore, QtGui, QtWidgets = q.QtCore, q.QtGui, q.QtWidgets
    Qt = QtCore.Qt
    E = QtCore.QEvent
    Ghost = maya_hubqt.ghost_class()

    def same(a, b):
        try:
            return (q.shiboken.getCppPointer(a)[0]
                    == q.shiboken.getCppPointer(b)[0])
        except Exception:                                    # noqa: BLE001
            return False

    def local_of(event):
        return (event.position().toPoint() if hasattr(event, "position")
                else event.pos())

    def global_of(event):
        return (event.globalPosition().toPoint()
                if hasattr(event, "globalPosition") else event.globalPos())

    class Drag(QtCore.QObject):
        """The event filter on one list. `scene` is `Scene()` in Maya."""

        def __init__(self, widget, records_of, scene):
            QtCore.QObject.__init__(self, widget)
            self.setObjectName("skeldarClipDrag")
            self.list = widget                  # held: trap 96's dead wrapper
            self.port = widget.viewport()
            self.records_of = records_of
            self.scene = scene
            self.k = float(scene.scale() or 1.0)
            self.status_text = ""
            self._press = None
            self._drag = None
            self._synthetic = False
            self._clock = QtCore.QElapsedTimer()
            self._clock.start()

        # ---------------------------------------------------------- state

        def dragging(self):
            """The record being carried, or None."""
            return self._drag["record"] if self._drag else None

        def ghost(self):
            return self._drag["ghost"] if self._drag else None

        def detach(self):
            for target in (self.port, self.list):
                try:
                    target.removeEventFilter(self)
                except Exception:                            # noqa: BLE001
                    pass

        def _say(self, text):
            self.status_text = text or ""
            if self.status_text:
                self.scene.say(self.status_text)
            return self.status_text

        def _act(self, action):
            try:
                text = action()
            except Exception:                                # noqa: BLE001
                traceback.print_exc()
                text = _last_line(traceback.format_exc())
            return self._say(text)

        def _record_at(self, local):
            index = self.list.indexAt(local)
            if not index.isValid():
                return None
            try:
                records = list(self.records_of() or [])
            except Exception:                                # noqa: BLE001
                return None
            row = index.row()
            return records[row] if 0 <= row < len(records) else None

        def _on_list(self, gx, gy):
            local = self.list.mapFromGlobal(QtCore.QPoint(int(gx), int(gy)))
            return self.list.rect().contains(local)

        # ----------------------------------------------------------- drop

        def drop_at(self, gx, gy, record=None):
            """The release of a drag of `record` at the global point. Public,
            so a verify can drive it without a mouse."""
            record = record or self.dragging()
            if record is None:
                return self.status_text
            if self._on_list(gx, gy) or self.scene.over_hub(gx, gy):
                return self.status_text          # back on the hub: nothing
            snap = (self._drag["snap"] if self._drag
                    else self._snapshot())
            try:
                aim = self.scene.target(gx, gy, snap)
            except Exception:                                # noqa: BLE001
                traceback.print_exc()
                return self._say(_last_line(traceback.format_exc()))
            if aim.get("kind") in ("rig", "new_rig"):
                return self._act(lambda: self.scene.drop(record, aim))
            return self._say(aim.get("text") or "no target")

        def _snapshot(self):
            try:
                return self.scene.snapshot()
            except Exception:                                # noqa: BLE001
                traceback.print_exc()
                return []

        # ----------------------------------------------------------- drag

        def _start(self, record, point):
            press = self._press
            # The click ends for the list where it began: its selection stays
            # on the pressed row and its state returns to none. Sent past
            # this filter, never through Qt's window, so the implicit grab
            # stays and the moves keep coming here.
            self._synthetic = True
            try:
                release = QtGui.QMouseEvent(
                    E.MouseButtonRelease, QtCore.QPointF(press["local"]),
                    QtCore.QPointF(press["global"]), Qt.LeftButton,
                    Qt.NoButton, Qt.NoModifier)
                QtWidgets.QApplication.sendEvent(self.port, release)
            finally:
                self._synthetic = False
            import maya_hubqt
            size = int(GHOST * self.k)
            try:
                pixmap = maya_hubqt.pixmap(
                    "run", maya_hubqt.hubstyle.TOKENS["accent"], size)
            except Exception:                                # noqa: BLE001
                pixmap = QtGui.QPixmap()
            ghost = Ghost(pixmap, size, size, self.k, anchor=(0.5, 0.5),
                          name=GHOST_NAME, backdrop="field")
            self._drag = dict(record=record, ghost=ghost,
                              snap=self._snapshot())
            ghost.follow(point)
            ghost.show()
            try:
                self.list.grabKeyboard()
            except Exception:                                # noqa: BLE001
                pass
            self.caption_at(point, force=True)

        def _end(self):
            if self._drag:
                ghost = self._drag["ghost"]
                ghost.hide()
                ghost.deleteLater()
            self._drag = None
            self._press = None
            try:
                self.list.releaseKeyboard()
            except Exception:                                # noqa: BLE001
                pass

        def caption_at(self, point, force=False):
            """The ghost's caption for the global `point` (throttled)."""
            drag = self._drag
            if not drag:
                return
            if not force and self._clock.elapsed() < THROTTLE_MS:
                return
            self._clock.restart()
            gx, gy = point.x(), point.y()
            try:
                if self._on_list(gx, gy) or self.scene.over_hub(gx, gy):
                    drag["ghost"].set_caption(OFF_HUB, False)
                    return
                aim = self.scene.target(gx, gy, drag["snap"])
            except Exception:                                # noqa: BLE001
                aim = dict(kind="none",
                           text=_last_line(traceback.format_exc()))
            text, good = caption(drag["record"].name, aim)
            drag["ghost"].set_caption(text, good)

        def _cancel(self):
            self._end()
            self._say(CANCELLED)

        # ---------------------------------------------------------- events

        def eventFilter(self, obj, event):                   # noqa: N802
            kind = event.type()
            if kind == E.KeyPress:
                if not self._drag:
                    return False
                if event.key() == Qt.Key_Escape:
                    self._cancel()
                return True
            if kind not in (E.MouseButtonPress, E.MouseMove,
                            E.MouseButtonRelease, E.MouseButtonDblClick):
                return False
            if self._synthetic or not same(obj, self.port):
                return False
            try:
                return self._mouse(kind, event)
            except Exception:                                # noqa: BLE001
                traceback.print_exc()
                self._end()
                return False

        def _mouse(self, kind, event):
            if kind == E.MouseButtonPress:
                if self._drag:
                    if event.button() == Qt.RightButton:
                        self._cancel()
                    return True
                self._press = None
                if event.button() == Qt.LeftButton:
                    local = local_of(event)
                    record = self._record_at(local)
                    if record is not None:
                        point = global_of(event)
                        self._press = {"record": record, "local": local,
                                       "global": point,
                                       "start": (point.x(), point.y())}
                return False
            if kind == E.MouseMove:
                point = global_of(event)
                if self._drag:
                    self._drag["ghost"].follow(point)
                    self.caption_at(point)
                    return True
                if self._press and event.buttons() & Qt.LeftButton:
                    if dragged(self._press["start"], (point.x(), point.y()),
                               QtWidgets.QApplication.startDragDistance()):
                        self._start(self._press["record"], point)
                    return True
                return False
            if kind == E.MouseButtonRelease:
                if self._drag:
                    if event.button() == Qt.LeftButton:
                        point = global_of(event)
                        record = self._drag["record"]
                        try:
                            self.drop_at(point.x(), point.y(), record)
                        finally:
                            self._end()
                    return True
                self._press = None
                return False
            #  a double click: the list's own (Import), unless a drag stands
            return bool(self._drag)

    _CLASSES.update(Drag=Drag, Ghost=Ghost, qt=q)
    return _CLASSES


# ----------------------------------------------------------------- attach

def attach_widget(widget, records_of, scene=None, key=None):
    """The drag on a QListWidget `widget`: `records_of()` answers the record
    of every row, in row order. Replaces a drag attached under the same `key`
    (the list's name; the widget's address when none)."""
    classes = _classes()
    q = classes["qt"]
    key = key or q.shiboken.getCppPointer(widget)[0]
    old = _DRAGS.pop(key, None)
    if old is not None:
        try:
            if q.shiboken.isValid(old):
                old.detach()
        except Exception:                                    # noqa: BLE001
            pass
    drag = classes["Drag"](widget, records_of, scene or Scene())
    widget.viewport().installEventFilter(drag)
    widget.installEventFilter(drag)
    _DRAGS[key] = drag
    return drag


def attach(list_name, records_of, scene=None):
    """The drag on the `cmds` textScrollList `list_name`, or None where it
    cannot stand (no Qt, no such control, not a list underneath)."""
    import maya_hubqt
    q = maya_hubqt.qt()
    if q is None:
        return None
    import maya.OpenMayaUI as omui
    ptr = omui.MQtUtil.findControl(list_name)
    if not ptr:
        return None
    widget = q.shiboken.wrapInstance(int(ptr), q.QtWidgets.QListWidget)
    if not hasattr(widget, "indexAt"):
        #  a QWidget wrapper cached at this address (trap 96): wrap afresh
        q.shiboken.invalidate(widget)
        widget = q.shiboken.wrapInstance(int(ptr), q.QtWidgets.QListWidget)
    if not (q.shiboken.isValid(widget)
            and widget.inherits("QAbstractItemView")):
        return None
    return attach_widget(widget, records_of, scene, key=list_name)
