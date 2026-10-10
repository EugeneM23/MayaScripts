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

Several rows the same day («выделить массив анимаций ... перетягивание в
сцену рукой»): a press on a picked row carries every picked row
(`carried_rows`), and the list keeps them picked; onto a rig the first goes,
onto the floor every one gets a new rig, in a square on the world's axes
about the point (`window.import_dropped` -> `lineimport`). The ghost says
which. With Skeleton picked in Characters (read when the drag starts; the
UE Bridge's Skeleton mode before the two cards merged, 2026-10-01) a release
on a skeleton puts the clip on it, keeping its place, and anywhere else over
a viewport places skeletons on the floor point, rigs ignored
(`droptarget.skeleton_target`).

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

import maya_hubcopy as hubcopy

GHOST_NAME = "skeldarClipGhost"
GHOST = 48              # logical px: the icon riding the cursor
THROTTLE_MS = 33        # the caption is re-read at most this often
DOT = "·"
OFF_HUB = "release off the hub to import"
CANCELLED = "cancelled"
DROPS = ("rig", "new_rig", "skeleton", "onto_skeleton")   # the aims a release acts on

#  The drags standing, by the list they are attached to.
_DRAGS = {}


def _last_line(error_text):
    lines = [line for line in (error_text or "").strip().splitlines()
             if line.strip()]
    return lines[-1] if lines else "failed"


def caption(names, aim):
    """(text, good): what the ghost says over `aim` for the clip(s) `names`
    (one name or a list). Several onto a rig: the first goes, and says so;
    several onto the floor: a square of new rigs. A skeleton under the cursor
    (kind "onto_skeleton", Skeleton picked in Characters) reads as a rig
    does. Pure."""
    names = [names] if isinstance(names, str) else list(names or [])
    aim = aim or {}
    kind = aim.get("kind")
    first = names[0] if names else ""
    if aim.get("auto") and kind in ("new_rig", "skeleton"):
        # the Auto card over the floor (2026-10-02): what lands is decided per clip
        point = aim.get("point")
        floor = ("" if point is None else " %s floor (%d, %d)" % (
            DOT, int(round(point[0])), int(round(point[2]))))
        if len(names) > 1:
            return "%d animations %s %s %s in a square%s" % (
                len(names), DOT, auto_what(aim.get("auto_kind"), True), DOT, floor), True
        return "%s %s %s%s" % (first, DOT, auto_what(aim.get("auto_kind")), floor), True
    if kind in ("rig", "onto_skeleton"):
        text = "%s %s %s" % (first, DOT, aim.get("text", ""))
        if len(names) > 1:
            text += " %s first of %d" % (DOT, len(names))
        return text, True
    if kind == "new_rig":
        if len(names) > 1:
            text = "%d animations %s %d new %s in a square" % (
                len(names), DOT, len(names), aim.get("label") or "rig")
            point = aim.get("point")
            if point is not None:
                text += " %s floor (%d, %d)" % (DOT, int(round(point[0])),
                                                int(round(point[2])))
            return text, True
        return "%s %s %s" % (first, DOT, aim.get("text", "")), True
    if kind == "skeleton":
        if len(names) > 1:
            text = "%d animations %s %d new %s in a square" % (
                len(names), DOT, len(names), aim.get("label") or "skeleton")
            point = aim.get("point")
            if point is not None:
                text += " %s floor (%d, %d)" % (DOT, int(round(point[0])),
                                                int(round(point[2])))
            return text, True
        return "%s %s %s" % (first, DOT, aim.get("text", "")), True
    return aim.get("text") or "no target", False


def auto_what(kind, several=False):
    """What an Auto drop over the floor brings: «our rig if it matches, else its own» (2026-10-02).
    Pure."""
    kind = kind or "rig"
    if several:
        return "each onto our %s if it matches, else its own" % kind
    return "our %s if it matches, else its own" % kind


def carried_rows(pressed, before, after, plain):
    """The rows a drag started on row `pressed` carries, in list order. Pure.

    A plain press (no Ctrl/Shift) on a row that was picked before it carries
    every row picked before it - Explorer's rule; Qt's ExtendedSelection
    would collapse the selection to the pressed row on the click's release.
    Otherwise what the press left picked, when it holds the pressed row;
    otherwise the pressed row alone."""
    if plain and pressed in (before or []):
        return sorted(set(before))
    if pressed in (after or []):
        return sorted(set(after))
    return [pressed]


def _as_list(records):
    if records is None:
        return []
    if hasattr(records, "name"):
        return [records]
    return [r for r in records if r is not None]


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

    def _read_kind(self):
        """The Characters card's [Rig | Skeleton]: what a drop makes (since
        the merge, 2026-10-01; the Skeleton mode before it)."""
        try:
            from maya_uebridge import window
            return window.import_kind()
        except Exception:                                    # noqa: BLE001
            return "rig"

    def _read_auto(self):
        """The Auto card's kind when it is picked, else None (2026-10-02): a floor drop then
        matches each clip, read once at the drag's start like the kind."""
        try:
            from maya_uebridge import window
            return window.auto_kind()
        except Exception:                                    # noqa: BLE001
            return None

    def snapshot(self):
        """What a drag needs, read once when it starts: the kind (Skeleton
        puts the clip on skeletons, 2026-10-01), the character a floor drop
        adds, and the bones of every rig - or, for Skeleton, of every bare
        skeleton."""
        from maya_scenesetup import droptarget
        from maya_uebridge import rigimport, skeletonimport
        self._kind = self._read_kind()
        self._auto = self._read_auto()
        self._new_label = rigimport.new_rig_entry().label
        self._skeleton_label = skeletonimport.skeleton_entry().label
        if self._kind == "skeleton":
            return droptarget.skeleton_snapshot()
        return droptarget.rig_snapshot()

    def target(self, gx, gy, snap):
        from maya_scenesetup import droptarget
        kind = getattr(self, "_kind", None) or self._read_kind()
        if kind == "skeleton":
            label = getattr(self, "_skeleton_label", None)
            if label is None:
                from maya_uebridge import skeletonimport
                label = self._skeleton_label = skeletonimport.skeleton_entry().label
            return self._marked(droptarget.skeleton_target(gx, gy, label, snap, self.scale()))
        label = getattr(self, "_new_label", None)
        if label is None:
            from maya_uebridge import rigimport
            label = self._new_label = rigimport.new_rig_entry().label
        return self._marked(droptarget.clip_target(gx, gy, snap, self.scale(), label))

    def _marked(self, aim):
        """An aim over the floor marked as the Auto card's when it is picked: the drop matches
        each clip (`window.import_dropped`), the caption says so. A character under the cursor
        stays what it is - the explicit target wins."""
        auto = getattr(self, "_auto", None)
        if auto and aim.get("kind") in ("new_rig", "skeleton"):
            aim = dict(aim, auto=True, auto_kind=auto)
        return aim

    def over_hub(self, gx, gy):
        import maya_hubqt
        return maya_hubqt.on_hub(gx, gy)

    def drop(self, records, aim):
        """The import of `records` (every carried clip), one idle later: the
        ghost is gone and the mouse free before the editor's round trip
        blocks Maya for seconds. A failure reaches the status line
        (`window._run`)."""
        import maya.utils
        from maya_uebridge import window
        records = list(records)

        def run():
            window._run(lambda: window.import_dropped(records, aim),
                        busy="exporting from the editor...")

        maya.utils.executeDeferred(run)
        return caption([r.name for r in records], aim)[0] + "..."

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
            """The (first) record being carried, or None."""
            return self._drag["records"][0] if self._drag else None

        def carried(self):
            """Every record being carried, in list order ([] with no drag)."""
            return list(self._drag["records"]) if self._drag else []

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

        def _records(self):
            try:
                return list(self.records_of() or [])
            except Exception:                                # noqa: BLE001
                return []

        def _row_at(self, local):
            """(row, record) under the list-local point, or (None, None)."""
            index = self.list.indexAt(local)
            if not index.isValid():
                return None, None
            records = self._records()
            row = index.row()
            if 0 <= row < len(records):
                return row, records[row]
            return None, None

        def _picked_rows(self):
            try:
                return sorted(set(index.row() for index in
                                  self.list.selectionModel().selectedIndexes()))
            except Exception:                                # noqa: BLE001
                return []

        def _pick_rows(self, rows):
            """The list's selection set to exactly `rows`."""
            model = self.list.model()
            selection = QtCore.QItemSelection()
            for row in rows:
                index = model.index(row, 0)
                selection.select(index, index)
            self.list.selectionModel().select(
                selection, QtCore.QItemSelectionModel.ClearAndSelect)

        def _on_list(self, gx, gy):
            local = self.list.mapFromGlobal(QtCore.QPoint(int(gx), int(gy)))
            return self.list.rect().contains(local)

        # ----------------------------------------------------------- drop

        def drop_at(self, gx, gy, records=None):
            """The release of a drag of `records` (one record or a list; the
            carried ones when None) at the global point. Public, so a verify
            can drive it without a mouse."""
            records = _as_list(records) or self.carried()
            if not records:
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
            if aim.get("kind") in DROPS:
                return self._act(lambda: self.scene.drop(records, aim))
            return self._say(aim.get("text") or "no target")

        def _snapshot(self):
            try:
                return self.scene.snapshot()
            except Exception:                                # noqa: BLE001
                traceback.print_exc()
                return []

        # ----------------------------------------------------------- drag

        def _start(self, point):
            press = self._press
            # What travels: the pressed row with the rows picked before the
            # press, else what the press left picked (`carried_rows`), read
            # before the release below - which, on a picked row, collapses
            # Qt's ExtendedSelection to that row.
            rows = carried_rows(press["row"], press["before"],
                                self._picked_rows(), press["plain"])
            records = self._records()
            carried = [records[r] for r in rows if 0 <= r < len(records)]
            if press["record"] not in carried:
                rows, carried = [press["row"]], [press["record"]]
            # The click ends for the list where it began: its state returns
            # to none. Sent past this filter, never through Qt's window, so
            # the implicit grab stays and the moves keep coming here.
            self._synthetic = True
            try:
                release = QtGui.QMouseEvent(
                    E.MouseButtonRelease, QtCore.QPointF(press["local"]),
                    QtCore.QPointF(press["global"]), Qt.LeftButton,
                    Qt.NoButton, press["modifiers"])
                QtWidgets.QApplication.sendEvent(self.port, release)
            finally:
                self._synthetic = False
            # ...and the list keeps every row it carries picked.
            if self._picked_rows() != sorted(rows):
                try:
                    self._pick_rows(rows)
                except Exception:                            # noqa: BLE001
                    traceback.print_exc()
            import maya_hubqt
            size = int(GHOST * self.k)
            try:
                pixmap = maya_hubqt.pixmap(
                    "run", maya_hubqt.hubstyle.TOKENS["accent"], size)
            except Exception:                                # noqa: BLE001
                pixmap = QtGui.QPixmap()
            ghost = Ghost(pixmap, size, size, self.k, anchor=(0.5, 0.5),
                          name=GHOST_NAME, backdrop="field")
            self._drag = dict(records=carried, ghost=ghost,
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
            text, good = caption([r.name for r in drag["records"]], aim)
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
                    row, record = self._row_at(local)
                    if record is not None:
                        point = global_of(event)
                        modifiers = event.modifiers()
                        plain = not (modifiers & (Qt.ControlModifier
                                                  | Qt.ShiftModifier))
                        # the rows picked BEFORE Qt handles this press
                        self._press = {"record": record, "row": row,
                                       "before": self._picked_rows(),
                                       "plain": plain, "modifiers": modifiers,
                                       "local": local, "global": point,
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
                        self._start(point)
                    return True
                return False
            if kind == E.MouseButtonRelease:
                if self._drag:
                    if event.button() == Qt.LeftButton:
                        point = global_of(event)
                        records = self.carried()
                        try:
                            self.drop_at(point.x(), point.y(), records)
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
    #  the list's name as the scope that asks knows it (2026-10-09, H1): a popup's
    #  drag on the same list never detaches the hub's
    if isinstance(key, str):
        key = hubcopy.resolve(key)
    key = key or q.shiboken.getCppPointer(widget)[0]
    old = _DRAGS.pop(key, None)
    if old is not None:
        try:
            if q.shiboken.isValid(old):
                old.detach()
        except Exception:                                    # noqa: BLE001
            pass
    #  the scene is called from Qt events (a drag): its calls run in the scope
    #  the drag was attached in (H3)
    drag = classes["Drag"](widget, records_of, hubcopy.bind(scene or Scene()))
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
    ptr = omui.MQtUtil.findControl(hubcopy.resolve(list_name))
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
