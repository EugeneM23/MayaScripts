"""The Characters card's portrait grid: pick a character, or drag it in.

2026-09-30, the animator: «переделаем наше меню на сетку с портретами (как
меню выбора героев в Mortal Kombat или Dota 2). Выделив какой-то портрет ...
нажав кнопочку Add Character ... добавляем риг или скелет в сцену. ... зажать
на портрете и перетащить его в сцену Maya, и персонаж создастся в том месте,
куда я его перетащил, подобно тому функционалу, что мы сделали с оружием и
инвентарем».

One square head-and-shoulders portrait per model (catalog.MODELS), the kind
- rig or skeleton - chosen by the card's [Rig | Skeleton] switch; a model
without that kind is dimmed and cannot be picked or dragged.

- a CLICK selects a portrait (the line says what Add will import);
- a DRAG - press, move past Qt's start distance, release - carries the
  portrait on the cursor (maya_hubqt's ghost, the inventory's) with a caption
  naming the floor point; released over a viewport, the character is added
  standing where the camera ray meets the floor. Esc or the right button
  cancels; a release back on the hub does nothing;
- the RIGHT BUTTON on a portrait offers Open scene (2026-09-30, «при нажатии
  правой клавишей по иконке рига ... Open scene»): the model's file in the
  kind the switch shows, opened as the scene (`maya_scenesetup.opener`).

The mouse is ours for the whole drag: the press grabs it, so the moves and
the release keep coming here over the viewport, which never sees them.

The portrait under the cursor takes the hover face and ring, flat: the fire
it burned with from 2026-10-02 is gone (2026-11-19, «удаляем все подсветки и
анимации из плагина ... интерфейс должен быть максимально легким»).

The grid lives in a `cmds` card: the builder makes an empty columnLayout and
`attach` lays the grid over it, the placeholder's height kept at what the
grid needs for its width - so the same grid stands in the skinned hub and the
classic one. Everything it does to the scene goes through `Scene`, which the
tests replace; everything it looks like is `maya_charlook`'s. Qt is imported
lazily (`maya_hubqt.qt()`), the classes are built on first use.

Spec: docs/superpowers/specs/2026-09-30-character-portrait-grid-design.md
"""

import os
import traceback

import maya_charlook as look
import maya_hubcopy as hubcopy

OBJECT_NAME = "skeldarCharacterGrid"
GHOST_NAME = "skeldarCharacterGhost"
HUB_CONTROL = "skeldarAnimHub"          # maya_hub.CONTROL, the workspaceControl

#  The grids standing, by the placeholder they are laid over - by the name the
#  placeholder answers to in the scope that asks (`_key`), 2026-10-09.
_GRIDS = {}


def _named(base, scope):
    """`base` outside a section popup; inside one, `base` tagged with the copy's
    scope (2026-10-09, H2): the hub's grid and a popup's grid, and their ghost,
    never share a Qt object name."""
    return base if scope is None else "{0}_{1}".format(base, scope.tag)


def scoped_name(name):
    """`name` for a Qt object of ours, tagged with the copy it is made in
    (2026-10-09, H2): two copies never share an object name. The hub's is
    `name` itself."""
    scope = hubcopy.current()
    return name if scope is None else "{0}_{1}".format(name, scope.tag)

def _key(placeholder):
    """The registry key of `placeholder` (2026-10-09, H1): the name a copy's own
    control answers to inside the copy, so a popup's grid never takes the hub's
    entry. Outside a copy the name itself."""
    return hubcopy.resolve(placeholder)


def run_in(scope, fn, *args, **kwargs):
    """`fn` run inside `scope` (2026-10-09, H3): a Qt event calls the grid, and a
    callback of a Qt object is not a cmds command, so the names it writes must be
    the copy's own. A closed copy runs nothing - its names are gone, and a call
    would reach the hub's controls. No scope: `fn` as it is."""
    if scope is None:
        return fn(*args, **kwargs)
    if not scope.alive:
        return None
    with hubcopy.entered(scope):
        return fn(*args, **kwargs)


class ScopedScene(object):
    """A grid's scene (`Scene()` in Maya, a fake in the tests) with every call of
    it run in the scope the grid was made in (2026-10-09, H3): the grid's mouse
    and drag code calls the scene from Qt, outside any command. Attributes read
    through as they are (a test may replace one after the grid is made)."""

    def __init__(self, scene, scope):
        self._scene = scene
        self._scope = scope

    def __getattr__(self, name):
        attr = getattr(self._scene, name)
        if not callable(attr):
            return attr

        def call(*args, **kwargs):
            return run_in(self._scope, attr, *args, **kwargs)
        return call


def _prune():
    """Drop the grids whose windows are gone (2026-10-09, H1: a closed copy's
    grid is never read again, so it leaves the registry when the next grid is
    laid). Needs Qt, which `attach` has already."""
    q = _classes()["qt"]
    for key, grid in list(_GRIDS.items()):
        try:
            alive = q.shiboken.isValid(grid)
        except Exception:                                    # noqa: BLE001
            alive = False
        if not alive:
            _GRIDS.pop(key, None)


def _last_line(error_text):
    lines = [line for line in (error_text or "").strip().splitlines()
             if line.strip()]
    return lines[-1] if lines else "failed"


# ------------------------------------------------------------------ the skill bar

def _skillbar():
    """maya_skillbar, or None (2026-10-19: a portrait dropped on the Time Bar's skill page is a
    character skill)."""
    try:
        import maya_skillbar
        return maya_skillbar
    except Exception:                                        # noqa: BLE001
        return None


def skill_aim(gx, gy):
    bar = _skillbar()
    if bar is None:
        return None
    try:
        return bar.aim(gx, gy)
    except Exception:                                        # noqa: BLE001
        return None


def skill_light(target):
    bar = _skillbar()
    if bar is not None:
        try:
            bar.light(target)
        except Exception:                                    # noqa: BLE001
            pass


# ------------------------------------------------------------------ scene

class Scene(object):
    """The real scene: what the grid asks and what it does to it."""

    def scale(self):
        import maya.cmds as cmds
        try:
            return float(cmds.mayaDpiSetting(query=True, realScaleValue=True)
                         or 1.0)
        except Exception:                                    # noqa: BLE001
            return 1.0

    def __init__(self):
        self._snap = None
        self._label = ""

    def begin(self, label=""):
        """A drag starts: every character read once (2026-10-17, a portrait dropped on one
        swaps it). `label` is the dragged row's, for the caption."""
        from maya_scenesetup import droptarget
        try:
            self._snap = droptarget.snapshot()
        except Exception:                                    # noqa: BLE001
            self._snap = []
        self._label = label

    def end(self):
        self._snap = None

    def target(self, gx, gy):
        """kind "swap" (root, label, text) over a character, else the floor (`floor_at`)."""
        from maya_scenesetup import catalog, droptarget, swap
        snap = self._snap
        if snap is None:
            try:
                snap = droptarget.snapshot()
            except Exception:                                # noqa: BLE001
                snap = []
        if snap:
            aim = droptarget.character_target(gx, gy, snap, self.scale())
            if aim.get("kind") == "character":
                entry = catalog.character_by_label(self._label) if self._label else None
                return dict(kind="swap", root=aim["root"], label=aim["label"],
                            text=swap.swap_caption(aim["label"], self._label or "it",
                                                   getattr(entry, "part", "")))
        return droptarget.floor_at(gx, gy)

    def over_hub(self, gx, gy):
        """Whether the global point lies on the hub (maya_hubqt.on_hub)."""
        import maya_hubqt
        return maya_hubqt.on_hub(gx, gy, HUB_CONTROL)

    def select(self, model):
        from maya_scenesetup import window
        window.select_model(model)

    def place(self, model, kind, point):
        from maya_scenesetup import window
        return window.place_character(model, kind, point)

    def swap(self, model, kind, root):
        from maya_scenesetup import window
        return window.swap_character(model, kind, root)

    def open_scene(self, model, kind):
        from maya_scenesetup import window
        return window.open_character_scene(model, kind)

    def say(self, text):
        try:
            from maya_scenesetup import window
            window.say_character(text)
        except Exception:                                    # noqa: BLE001
            pass


# -------------------------------------------------------------------- Qt

_CLASSES = {}


def _classes():
    """The widget classes, built on first use (Qt imported here)."""
    if _CLASSES:
        return _CLASSES
    import maya_hubqt
    from maya_scenesetup import catalog

    q = maya_hubqt.qt()
    QtCore, QtGui, QtWidgets = q.QtCore, q.QtGui, q.QtWidgets
    Qt = QtCore.Qt
    Ghost = maya_hubqt.ghost_class()

    def colour(name):
        return QtGui.QColor(look.PALETTE[name])

    def font(px, bold=False):
        f = QtGui.QFont()
        f.setPixelSize(max(1, int(round(px))))
        f.setBold(bold)
        return f

    class Keeper(QtCore.QObject):
        """Keeps the grid over its placeholder, the placeholder as tall as
        the grid needs for its width (the width is Maya's layout's to give)."""

        def __init__(self, grid, parent=None):
            QtCore.QObject.__init__(self, parent)
            self._grid = grid

        def eventFilter(self, obj, event):                   # noqa: N802
            if event.type() == QtCore.QEvent.Resize:
                try:
                    self._grid.fit(obj)
                except Exception:                            # noqa: BLE001
                    pass
            return False

    class PortraitGrid(QtWidgets.QWidget):
        """The grid. `scene` is `Scene()` in Maya, a fake in the tests."""

        def __init__(self, scene, parent=None, kind="rig", selected=None):
            QtWidgets.QWidget.__init__(self, parent)
            self.setObjectName(scoped_name(OBJECT_NAME))
            self.scene = scene
            self.k = float(scene.scale() or 1.0)
            self.models = list(catalog.MODELS)
            self.kind = kind if kind in catalog.KINDS else catalog.KINDS[0]
            self.selected = selected
            self.status_text = ""
            self.pixmaps = {}
            for model in self.models:
                path = catalog.portrait_path(model.key)
                if os.path.isfile(path):
                    self.pixmaps[model.key] = QtGui.QPixmap(path)
            self._hover = None
            self._press = None
            self._drag = None
            self._clock = QtCore.QElapsedTimer()
            self._clock.start()
            self.setMouseTracking(True)
            self.setFocusPolicy(Qt.ClickFocus)
            self.setCursor(Qt.PointingHandCursor)

        # ------------------------------------------------------ layout

        def height_for(self, width):
            return look.grid(width, len(self.models), self.k)[3]

        def rects(self):
            return look.grid(self.width(), len(self.models), self.k)[2]

        def fit(self, host):
            """Over the whole of `host`, and `host` as tall as the grid."""
            self.setGeometry(host.rect())
            want = self.height_for(host.width())
            if host.height() != want:
                host.setFixedHeight(want)
                self.setGeometry(host.rect())

        def sizeHint(self):                                  # noqa: N802
            width = max(1, self.width())
            return QtCore.QSize(width, self.height_for(width))

        # ------------------------------------------------------- state

        def available(self, model):
            return self.kind in catalog.kinds_of(model)

        def model_at(self, x, y):
            index = look.hit(self.rects(), x, y, self.k)
            return self.models[index].key if index is not None else None

        def set_kind(self, kind):
            if kind in catalog.KINDS:
                self.kind = kind
                self.update()

        def set_selected(self, model):
            self.selected = model
            self.update()

        def select(self, model):
            """A portrait picked: True when it could be."""
            if not model or not self.available(model):
                return False
            self.selected = model
            self.update()
            self.scene.select(model)
            return True

        def _row(self, model):
            entry = catalog.character_for(model, self.kind)
            return entry.label if entry else model

        def _say(self, text):
            self.status_text = text or ""
            self.scene.say(self.status_text)
            return self.status_text

        def _act(self, action):
            try:
                text = action()
            except Exception:                                # noqa: BLE001
                traceback.print_exc()
                text = _last_line(traceback.format_exc())
            return self._say(text)

        # ------------------------------------------------------- menu

        def context_actions(self, model):
            """What the right button offers over `model` (2026-09-30, «при
            нажатии правой клавишей по иконке рига ... Open scene»): the file
            of the kind the switch shows, opened as the scene; a dimmed
            portrait's row is shown disabled. [] off every portrait, and on the Auto card, which
            has no file of its own (2026-10-02)."""
            if not model or catalog.is_auto(model):
                return []
            if not self.available(model):
                return [(look.open_absent_text(self.kind), None)]
            kind = self.kind
            return [(look.OPEN_SCENE, lambda: self._act(
                lambda: self.scene.open_scene(model, kind)))]

        # -------------------------------------------------------- drop

        def drop_at(self, gx, gy, model=None):
            """The release of a drag of `model` at the global point. Public,
            so a verify can drive it without a mouse."""
            model = model or (self._drag or {}).get("model")
            if not model:
                return self.status_text
            if catalog.is_auto(model):
                return self._say(look.AUTO_ADD)
            if not self.available(model):
                name = catalog.model_by_key(model)
                return self._say(look.absent_text(name.label if name else model,
                                                  self.kind))
            local = self.mapFromGlobal(QtCore.QPoint(int(gx), int(gy)))
            if self.rect().contains(local) or self.scene.over_hub(gx, gy):
                return self.status_text          # back on the hub: nothing
            skill = skill_aim(gx, gy)
            if skill:
                skill_light(None)
                return self._say(_skillbar().drop(gx, gy, {"kind": "character", "model": model,
                                                          "char": self.kind}))
            aim = self.scene.target(gx, gy)
            if aim.get("kind") == "floor":
                point, kind = aim["point"], self.kind
                return self._act(lambda: self.scene.place(model, kind, point))
            if aim.get("kind") == "swap":
                root, kind = aim["root"], self.kind
                return self._act(lambda: self.scene.swap(model, kind, root))
            return self._say(aim.get("text") or "no target")

        # -------------------------------------------------------- drag

        def _start(self, model, point):
            size = int(look.GHOST * self.k)
            ghost = Ghost(self.pixmaps.get(model) or QtGui.QPixmap(), size,
                          size, self.k, anchor=(0.5, 0.5), name=GHOST_NAME,
                          backdrop="field")
            self._drag = dict(model=model, ghost=ghost)
            begin = getattr(self.scene, "begin", None)
            if begin is not None:
                begin(self._row(model))
            ghost.follow(point)
            ghost.show()
            try:
                self.grabKeyboard()
            except Exception:                                # noqa: BLE001
                pass
            self._caption(point, force=True)
            self.update()

        def _end(self):
            if self._drag:
                ghost = self._drag["ghost"]
                ghost.hide()
                ghost.deleteLater()
            self._drag = None
            self._press = None
            skill_light(None)
            end = getattr(self.scene, "end", None)
            if end is not None:
                end()
            try:
                self.releaseKeyboard()
            except Exception:                                # noqa: BLE001
                pass
            self.update()

        def _caption(self, point, force=False):
            drag = self._drag
            if not drag:
                return
            if not force and self._clock.elapsed() < look.THROTTLE_MS:
                return
            self._clock.restart()
            gx, gy = point.x(), point.y()
            local = self.mapFromGlobal(point)
            try:
                if self.rect().contains(local) or self.scene.over_hub(gx, gy):
                    drag["ghost"].set_caption("release off the hub to place",
                                              False)
                    return
                skill = skill_aim(gx, gy)
                skill_light(skill)
                if skill:
                    drag["ghost"].set_caption(_skillbar().caption(self._row(drag["model"]), skill), True)
                    return
                aim = self.scene.target(gx, gy)
            except Exception:                                # noqa: BLE001
                aim = dict(kind="none",
                           text=_last_line(traceback.format_exc()))
            if aim.get("kind") == "floor":
                drag["ghost"].set_caption(
                    look.place_caption(self._row(drag["model"]), aim["point"]),
                    True)
            elif aim.get("kind") == "swap":
                drag["ghost"].set_caption(aim.get("text", ""), True)
            else:
                drag["ghost"].set_caption(aim.get("text", ""), False)

        # ------------------------------------------------------- mouse

        def _local(self, event):
            return (event.position().toPoint() if hasattr(event, "position")
                    else event.pos())

        def _global(self, event):
            return (event.globalPosition().toPoint()
                    if hasattr(event, "globalPosition") else event.globalPos())

        def mousePressEvent(self, event):                    # noqa: N802
            if self._drag:
                if event.button() == Qt.RightButton:
                    self._end()
                    self._say("cancelled")
                return
            local = self._local(event)
            if event.button() == Qt.RightButton:
                self._press = None
                actions = self.context_actions(
                    self.model_at(local.x(), local.y()))
                maya_hubqt.run_menu(self, self._global(event), actions)
                return
            if event.button() != Qt.LeftButton:
                return
            model = self.model_at(local.x(), local.y())
            if model and self.select(model):
                point = self._global(event)
                # the Auto card is picked, never dragged in: it has no character of its own
                if not catalog.is_auto(model):
                    self._press = (model, (point.x(), point.y()))

        def mouseMoveEvent(self, event):                     # noqa: N802
            point = self._global(event)
            if self._drag:
                self._drag["ghost"].follow(point)
                self._caption(point)
                return
            if self._press and event.buttons() & Qt.LeftButton:
                model, start = self._press
                if look.dragged(start, (point.x(), point.y()),
                                QtWidgets.QApplication.startDragDistance()):
                    self._start(model, point)
                return
            local = self._local(event)
            self._set_hover(self.model_at(local.x(), local.y()))

        def mouseReleaseEvent(self, event):                  # noqa: N802
            if self._drag and event.button() == Qt.LeftButton:
                point = self._global(event)
                model = self._drag["model"]
                try:
                    self.drop_at(point.x(), point.y(), model)
                finally:
                    self._end()
                return
            self._press = None

        def leaveEvent(self, _event):                        # noqa: N802
            if not self._drag:
                self._set_hover(None)

        def keyPressEvent(self, event):                      # noqa: N802
            if event.key() == Qt.Key_Escape and self._drag:
                self._end()
                self._say("cancelled")
                return
            QtWidgets.QWidget.keyPressEvent(self, event)

        # ------------------------------------------------------- hover
        def _set_hover(self, model):
            """The portrait under the mouse takes the hover face and ring."""
            if model != self._hover:
                self._hover = model
                self.update()

        # ------------------------------------------------------- paint

        def _stroke(self, p, box, radius, name, width, dashed=False):
            pen = QtGui.QPen(colour(name), width)
            if dashed:
                pen.setStyle(Qt.DashLine)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            half = width / 2.0
            p.drawRoundedRect(box.adjusted(half, half, -half, -half), radius,
                              radius)

        def _missing(self, p, box):
            """No portrait file: the hub's user icon, muted, centred."""
            side = int(box.width() * 0.45)
            try:
                import maya_hubqt as hubqt
                icon = hubqt.pixmap("user", look.PALETTE["muted"], side)
            except Exception:                                # noqa: BLE001
                return
            p.drawPixmap(int(box.center().x() - side / 2.0),
                         int(box.center().y() - side / 2.0), icon)

        def _paint_cold(self, p, index, rect, dragging):
            """A portrait at rest: the face, the picture, the ring, the
            name."""
            k = self.k
            radius = look.RADIUS * k
            model = self.models[index]
            state = look.state(model.key, self.kind, self.selected,
                               catalog.kinds_of(model.key))
            absent = state in ("absent", "selected_absent")
            lit = (self._hover == model.key and state == "available"
                   and not dragging)
            box = QtCore.QRectF(*rect)
            shape = QtGui.QPainterPath()
            shape.addRoundedRect(box, radius, radius)
            if state == "selected":
                p.fillPath(shape, colour("card_active"))
            elif lit:
                p.fillPath(shape, colour("hover"))
            else:
                p.fillPath(shape, colour("field"))
            p.save()
            p.setClipPath(shape)
            p.setOpacity(0.28 if absent else
                         (0.45 if dragging == model.key else 1.0))
            pixmap = self.pixmaps.get(model.key)
            if pixmap is not None and not pixmap.isNull():
                p.drawPixmap(box.toRect(), pixmap)
            else:
                self._missing(p, box)
            p.restore()

            # the name over the picture's bottom - before the ring, so the
            # shade never dims the outline
            self._paint_name(p, rect, model.label, state, absent)

            if state == "selected":
                self._stroke(p, box, radius, "accent", max(1.5, 2 * k))
            elif state == "selected_absent":
                self._stroke(p, box, radius, "accent", max(1.0, 1.5 * k),
                             dashed=True)
            elif lit:
                self._stroke(p, box, radius, "text2", max(1.0, k))
            else:
                self._stroke(p, box, radius, "line", max(1.0, k))

            if absent:
                # above the name's strip (2026-10-08: the name lies over the
                # square's bottom now)
                pad = int(4 * k)
                nh = look.name_rect(rect, k)[3]
                tag = QtCore.QRectF(box.left() + pad,
                                    box.bottom() - nh - pad - int(16 * k),
                                    box.width() - 2 * pad, int(16 * k))
                p.setPen(Qt.NoPen)
                p.setBrush(colour("status"))
                p.drawRoundedRect(tag, 4 * k, 4 * k)
                tag_font = font(9.5 * k)
                p.setFont(tag_font)
                p.setPen(colour("faint"))
                p.drawText(tag, Qt.AlignCenter,
                           QtGui.QFontMetrics(tag_font).elidedText(
                               look.tag_text(self.kind), Qt.ElideRight,
                               int(tag.width())))

        def _paint_name(self, p, rect, label, state, absent):
            """The name over the picture's bottom, on a shade fading in from
            the picture (2026-10-08, the compact hub: five tiles a row, no
            strip under the square). The shade is cut to the tile's rounded
            shape; whoever calls draws the ring after it."""
            k = self.k
            nx, ny, nw, nh = look.name_rect(rect, k)
            radius = look.RADIUS * k
            shape = QtGui.QPainterPath()
            shape.addRoundedRect(QtCore.QRectF(*rect), radius, radius)
            shade = QtGui.QLinearGradient(nx, ny, nx, ny + nh)
            shade.setColorAt(0.0, QtGui.QColor(0, 0, 0, 0))
            shade.setColorAt(1.0, QtGui.QColor(0, 0, 0, 190))
            p.save()
            p.setClipPath(shape, Qt.IntersectClip)
            p.setPen(Qt.NoPen)
            p.setBrush(shade)
            p.drawRect(QtCore.QRectF(nx, ny, nw, nh))
            p.restore()
            name_font = font(10 * k, bold=state == "selected")
            p.setFont(name_font)
            if state == "selected":
                pen = colour("text")
            elif absent:
                pen = colour("faint")
            else:
                pen = colour("text2")
            p.setPen(pen)
            text = QtGui.QFontMetrics(name_font).elidedText(
                label, Qt.ElideRight, int(nw - 6 * k))      # clear of the ring
            p.drawText(QtCore.QRect(int(nx), int(ny), int(nw), int(nh)),
                       Qt.AlignHCenter | Qt.AlignVCenter, text)

        def paintEvent(self, _event):                        # noqa: N802
            p = QtGui.QPainter(self)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
            dragging = self._drag["model"] if self._drag else None
            for index, rect in enumerate(self.rects()):
                self._paint_cold(p, index, rect, dragging)
            p.end()

    _CLASSES.update(Keeper=Keeper, PortraitGrid=PortraitGrid, Ghost=Ghost,
                    qt=q)
    return _CLASSES


# ----------------------------------------------------------------- open

def make_grid(scene, parent=None, kind="rig", selected=None):
    """A grid over `scene` - the tests' seam."""
    return _classes()["PortraitGrid"](scene, parent, kind, selected)


def attach(placeholder, scene=None, kind="rig", selected=None):
    """Lay a grid over the `cmds` layout `placeholder`, or None where it
    cannot stand (no Qt, no such layout). Maya's layouts place their own
    children, so the grid is laid OVER the placeholder (the hub's `_spread`
    pattern) and the placeholder is given the grid's height for its width
    on every resize."""
    import maya_hubqt
    if maya_hubqt.qt() is None:
        return None
    host = maya_hubqt.find(placeholder, layout=True)
    if host is None:
        return None
    _prune()
    classes = _classes()
    #  the scene is called from Qt events (a click, a drag): its calls run in
    #  the scope the grid was laid in (H3, 2026-10-09)
    scene = hubcopy.bind(scene or Scene())
    grid = classes["PortraitGrid"](scene, host, kind, selected)
    grid._host = host                    # the wrapper lives as long as the grid
    grid._keeper = classes["Keeper"](grid, grid)
    host.installEventFilter(grid._keeper)
    grid.fit(host)
    grid.show()
    _GRIDS[_key(placeholder)] = grid
    return grid


def live(placeholder):
    """The grid standing over `placeholder` in the scope that asks, or None."""
    key = _key(placeholder)
    grid = _GRIDS.get(key)
    if grid is None:
        return None
    try:
        q = _classes()["qt"]
        if q.shiboken.isValid(grid):
            return grid
    except Exception:                                        # noqa: BLE001
        pass
    _GRIDS.pop(key, None)
    return None
