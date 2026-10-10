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

The cursor on a portrait sets it alight (2026-10-02, «на заднем фоне в
карточке загорался огонь летели искры и она немного увеличивалась в размере
... у каждого персонажа свой цвет огня»): flames behind the character in its
own fire's colours, sparks, the character lit by it, the card grown 7 % on a
spring with a glow. `maya_charfire` is the simulation and the colours; the
painting is here. The burning cards are drawn by a mouse-transparent overlay
in the hub's scrolled content (`FireOverlay`), because the grid is clipped to
its placeholder and a grown card, its glow and its sparks would be cut at
every edge; while the grid is not whole inside its ancestors (a card sliding
shut) it draws them itself. A 16 ms timer runs only while something burns.
No fire with the menu's Interface animations off, on a dimmed portrait, on a
model with no fire (`maya_charfire.FIRES`), or during a drag; the «?» card
burns as Manny's does.

Spec (the fire): docs/superpowers/specs/2026-10-02-character-card-fire-design.md

The grid lives in a `cmds` card: the builder makes an empty columnLayout and
`attach` lays the grid over it, the placeholder's height kept at what the
grid needs for its width - so the same grid stands in the skinned hub and the
classic one. Everything it does to the scene goes through `Scene`, which the
tests replace; everything it looks like is `maya_charlook`'s. Qt is imported
lazily (`maya_hubqt.qt()`), the classes are built on first use.

Spec: docs/superpowers/specs/2026-09-30-character-portrait-grid-design.md
"""

import math
import os
import time
import traceback

import maya_charlook as look
import maya_hubcopy as hubcopy

OBJECT_NAME = "skeldarCharacterGrid"
GHOST_NAME = "skeldarCharacterGhost"
FIRE_NAME = "skeldarCharacterFire"      # the overlay drawing the burning cards
FIRE_MS = 16                            # the fire's frame while it burns
HUB_CONTROL = "skeldarAnimHub"          # maya_hub.CONTROL, the workspaceControl

#  The grids standing, by the placeholder they are laid over - by the name the
#  placeholder answers to in the scope that asks (`_key`), 2026-10-09.
_GRIDS = {}


def _named(base, scope):
    """`base` outside a section popup; inside one, `base` tagged with the copy's
    scope (2026-10-09, H2): the hub's grid and a popup's grid, their overlay and
    their ghost, never share a Qt object name."""
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


def _animations():
    """The menu's Interface animations (maya_hubmotion): the fire only with
    them on. A seam the tests replace."""
    try:
        import maya_hubmotion
        return maya_hubmotion.enabled()
    except Exception:                                        # noqa: BLE001
        return True


def _last_line(error_text):
    lines = [line for line in (error_text or "").strip().splitlines()
             if line.strip()]
    return lines[-1] if lines else "failed"


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

    def target(self, gx, gy):
        from maya_scenesetup import droptarget
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

    import maya_charfire as charfire

    q = maya_hubqt.qt()
    QtCore, QtGui, QtWidgets = q.QtCore, q.QtGui, q.QtWidgets
    Qt = QtCore.Qt
    Ghost = maya_hubqt.ghost_class()
    Plus = QtGui.QPainter.CompositionMode_Plus
    Over = QtGui.QPainter.CompositionMode_SourceOver
    Premultiplied = QtGui.QImage.Format_ARGB32_Premultiplied

    def colour(name):
        return QtGui.QColor(look.PALETTE[name])

    def font(px, bold=False):
        f = QtGui.QFont()
        f.setPixelSize(max(1, int(round(px))))
        f.setBold(bold)
        return f

    # ------------------------------------------------------------ fire
    def mix(a, b, u):
        u = min(1.0, max(0.0, u))
        return QtGui.QColor(
            int(a.red() + (b.red() - a.red()) * u),
            int(a.green() + (b.green() - a.green()) * u),
            int(a.blue() + (b.blue() - a.blue()) * u),
            int(a.alpha() + (b.alpha() - a.alpha()) * u))

    def fire_colour(name, heat, alpha=1.0):
        r, g, b, a = charfire.palette_rgba(name, heat)
        return QtGui.QColor(int(r), int(g), int(b),
                            int(255 * min(1.0, a * alpha)))

    def sprite(name, heat):
        """A spark's glow: a white-hot core, a halo of the fire's colour."""
        side = 64
        image = QtGui.QImage(side, side, Premultiplied)
        image.fill(0)
        g = QtGui.QRadialGradient(side / 2.0, side / 2.0, side / 2.0)
        g.setColorAt(0.0, fire_colour(name, min(1.0, heat + 0.2)))
        g.setColorAt(0.16, fire_colour(name, heat))
        g.setColorAt(0.42, fire_colour(name, heat - 0.2, 0.32))
        g.setColorAt(1.0, QtGui.QColor(0, 0, 0, 0))
        p = QtGui.QPainter(image)
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawEllipse(0, 0, side, side)
        p.end()
        return image

    class FireLook(object):
        """What one fire draws with, made once."""

        def __init__(self, name):
            self.name = name
            self.lut = charfire.palette_lut(name)
            self.sprites = [sprite(name, t) for t in (0.62, 0.78, 0.95)]
            self.rim = fire_colour(name, 0.84)
            self.light = fire_colour(name, 0.50)
            self.ring = fire_colour(name, 0.78)
            self.glow = fire_colour(name, 0.50)
            self.base = fire_colour(name, 0.34)
            r, g, b, _a = charfire.palette_rgba(name, 0.20)
            self.bg_hot = QtGui.QColor(int(r * 0.30 + 16), int(g * 0.30 + 14),
                                       int(b * 0.30 + 15))

    LOOKS = {}

    def fire_look(name):
        if name not in LOOKS:
            LOOKS[name] = FireLook(name)
        return LOOKS[name]

    def mask_image(mask, colour):
        """A float mask 0..1 as a premultiplied image of `colour`."""
        import numpy as np
        side_y, side_x = mask.shape
        m = np.clip(mask, 0.0, 1.0)
        data = np.zeros((side_y, side_x, 4), np.uint8)
        data[:, :, 0] = (colour.blue() * m).astype(np.uint8)
        data[:, :, 1] = (colour.green() * m).astype(np.uint8)
        data[:, :, 2] = (colour.red() * m).astype(np.uint8)
        data[:, :, 3] = (255 * m).astype(np.uint8)
        return QtGui.QImage(data.data, side_x, side_y, side_x * 4,
                            Premultiplied).copy()

    def portrait_alpha(pixmap, side):
        """A portrait's alpha drawn `side` px square, a float array 0..1."""
        import numpy as np
        image = pixmap.toImage().scaled(
            side, side, Qt.IgnoreAspectRatio, Qt.SmoothTransformation
        ).convertToFormat(QtGui.QImage.Format_ARGB32)
        bits = np.frombuffer(image.constBits(), np.uint8).reshape(
            side, image.bytesPerLine())
        return bits[:, :side * 4].reshape(side, side, 4)[:, :, 3].astype(
            np.float32) / 255.0

    def lit_images(pixmap, side, flame):
        """(shade, rim, firelight) images of a portrait drawn `side` px."""
        shade, rim, light = charfire.lit_masks(portrait_alpha(pixmap, side))
        return (mask_image(shade, QtGui.QColor(0, 0, 0)),
                mask_image(rim, flame.rim), mask_image(light, flame.light))

    def same(a, b):
        if a is b:
            return True
        try:
            return (q.shiboken.getCppPointer(a)[0]
                    == q.shiboken.getCppPointer(b)[0])
        except Exception:                                    # noqa: BLE001
            return False

    def scrolled_content(widget):
        """The hub's scrolled content holding `widget` - the first ancestor
        whose parent is a scroll area's viewport (the skin's
        skeldarHubContent, the classic hub's scrollLayout) - or None."""
        w = widget
        while w is not None:
            parent = w.parentWidget()
            if parent is None:
                return None
            area = parent.parentWidget()
            if (isinstance(area, QtWidgets.QAbstractScrollArea)
                    and same(area.viewport(), parent)):
                return w
            w = parent
        return None

    class FireOverlay(QtWidgets.QWidget):
        """The burning cards, drawn over the grid and past its edges. The
        mouse goes straight through it to the grid (in-window, so Qt's flag
        does it). `origin` is where the grid's (0, 0) stands in it."""

        def __init__(self, content, grid, name=FIRE_NAME):
            QtWidgets.QWidget.__init__(self, content)
            self.setObjectName(name)              # per copy (2026-10-09, H2)
            self.setAttribute(Qt.WA_TransparentForMouseEvents)
            self.setAttribute(Qt.WA_NoSystemBackground)
            self.setFocusPolicy(Qt.NoFocus)
            self._grid = grid
            self.origin = QtCore.QPoint(0, 0)
            self.paint_ms = 0.0

        def paintEvent(self, _event):                        # noqa: N802
            grid = self._grid
            try:
                if not q.shiboken.isValid(grid):
                    return
            except Exception:                                # noqa: BLE001
                return
            started = time.perf_counter()
            p = QtGui.QPainter(self)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
            p.translate(self.origin)
            try:
                grid._paint_burning(p, grid.overlaid)
            finally:
                p.end()
            self.paint_ms = (time.perf_counter() - started) * 1000.0

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
            #  the fire overlay's name, read here: its own event calls it from Qt,
            #  outside the copy's scope (2026-10-09, H2)
            self._fire_name = scoped_name(FIRE_NAME)
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
            self.fx = {}                     # model -> maya_charfire.CardFx
            self.overlay = None              # FireOverlay, made when needed
            self.overlaid = set()            # the models the overlay draws
            self.paint_ms = 0.0
            self._lit = {}
            self.fire_timer = QtCore.QTimer(self)
            self.fire_timer.setInterval(FIRE_MS)
            self.fire_timer.timeout.connect(self._tick)
            self._fire_clock = QtCore.QElapsedTimer()
            self._fire_clock.start()
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
            self._burst(model)
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
            aim = self.scene.target(gx, gy)
            if aim.get("kind") == "floor":
                point, kind = aim["point"], self.kind
                return self._act(lambda: self.scene.place(model, kind, point))
            return self._say(aim.get("text") or "no target")

        # -------------------------------------------------------- drag

        def _start(self, model, point):
            size = int(look.GHOST * self.k)
            ghost = Ghost(self.pixmaps.get(model) or QtGui.QPixmap(), size,
                          size, self.k, anchor=(0.5, 0.5), name=GHOST_NAME,
                          backdrop="field")
            self._drag = dict(model=model, ghost=ghost)
            self._put_out()
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
                aim = self.scene.target(gx, gy)
            except Exception:                                # noqa: BLE001
                aim = dict(kind="none",
                           text=_last_line(traceback.format_exc()))
            if aim.get("kind") == "floor":
                drag["ghost"].set_caption(
                    look.place_caption(self._row(drag["model"]), aim["point"]),
                    True)
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

        # -------------------------------------------------------- fire
        def _index(self, model):
            for index, entry in enumerate(self.models):
                if entry.key == model:
                    return index
            return None

        def _burns(self, model):
            """Whether `model`'s portrait may burn right now."""
            return bool(model and charfire.fire_of(model)
                        and self.available(model) and not self._drag
                        and _animations())

        def _fx(self, model):
            fx = self.fx.get(model)
            if fx is None:
                fx = charfire.CardFx(7 + 31 * (self._index(model) or 0))
                self.fx[model] = fx
            return fx

        def _set_hover(self, model):
            """The portrait under the mouse: the old hover face, and the
            fire lit on it (and put out on the one left)."""
            if model != self._hover:
                self._hover = model
                self.update()
            lit = model if self._burns(model) else None
            for key, fx in self.fx.items():
                fx.set_hover(key == lit)
            if lit and not self.fx.get(lit):
                self._fx(lit).set_hover(True)
            if self.fx:
                self._wake()

        def hover_model(self, model):
            """`_set_hover` for a verify: the fire on `model` (None: off)."""
            self._set_hover(model)

        def _put_out(self):
            for fx in self.fx.values():
                fx.set_hover(False)

        def _burst(self, model):
            if self._burns(model):
                self._fx(model).burst()
                self._wake()

        def _wake(self):
            self._sync_overlay()
            if not self.fire_timer.isActive():
                self._fire_clock.restart()
                self.fire_timer.start()

        def _tick(self):
            dt = min(0.05, self._fire_clock.restart() / 1000.0)
            self.advance(dt)

        def advance(self, dt):
            """Every burning card `dt` seconds on; the burnt-out dropped.
            True while something still burns (the timer stops when not)."""
            if not _animations():
                self.fx.clear()
            for key in list(self.fx):
                fx = self.fx[key]
                if fx.active():
                    fx.step(dt)
                if not fx.active():
                    del self.fx[key]
            self._sync_overlay()
            self.update()
            overlay = self._live_overlay()
            if overlay is not None:
                overlay.update()
            if not self.fx:
                self.fire_timer.stop()
            return bool(self.fx)

        # ----------------------------------------------------- overlay
        def _live_overlay(self):
            overlay = self.overlay
            try:
                if overlay is not None and q.shiboken.isValid(overlay):
                    return overlay
            except Exception:                                # noqa: BLE001
                pass
            self.overlay = None
            return None

        def _whole_in(self, content):
            """The grid stands whole inside every ancestor up to `content`
            (a card sliding shut caps its body and cuts the grid)."""
            w = self
            while not same(w, content):
                parent = w.parentWidget()
                if parent is None:
                    return False
                inside = QtCore.QRect(self.mapTo(parent, QtCore.QPoint(0, 0)),
                                      self.size())
                if not parent.rect().contains(inside):
                    return False
                w = parent
            return True

        def _sync_overlay(self):
            """The overlay over the grid, widened, in the hub's content - or
            the grid draws its burning cards itself."""
            overlay = self._live_overlay()
            content = scrolled_content(self) if self.fx else None
            if (content is None or not self.isVisible()
                    or not self._whole_in(content)):
                self.overlaid = set()
                if overlay is not None:
                    overlay.hide()
                return
            if overlay is None or not same(overlay.parentWidget(), content):
                if overlay is not None:
                    overlay.deleteLater()
                overlay = FireOverlay(content, self, name=self._fire_name)
                self.destroyed.connect(overlay.deleteLater)
                self.overlay = overlay
            rects = self.rects()
            cell = rects[0][2] if rects else 0
            side, top = int(cell * 0.2), int(cell * 0.6)
            corner = self.mapTo(content, QtCore.QPoint(0, 0))
            area = QtCore.QRect(corner.x() - side, corner.y() - top,
                                self.width() + 2 * side,
                                self.height() + top + side)
            area = area.intersected(content.rect())
            if overlay.geometry() != area:
                overlay.setGeometry(area)
            overlay.origin = corner - area.topLeft()
            overlay.raise_()
            overlay.show()
            self.overlaid = set(self.fx)

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

        def _paint_name(self, p, rect, label, state, absent, hot=0.0,
                        flame=None):
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
            name_font = font(10 * k, bold=state == "selected" or hot > 0.5)
            p.setFont(name_font)
            if state == "selected":
                pen = colour("text")
            elif absent:
                pen = colour("faint")
            else:
                pen = colour("text2")
            if flame is not None and hot > 0:
                pen = mix(pen, flame.ring, hot * 0.85)
            p.setPen(pen)
            text = QtGui.QFontMetrics(name_font).elidedText(
                label, Qt.ElideRight, int(nw - 6 * k))      # clear of the ring
            p.drawText(QtCore.QRect(int(nx), int(ny), int(nw), int(nh)),
                       Qt.AlignHCenter | Qt.AlignVCenter, text)

        def _lit_for(self, key, side, flame):
            cache = (key, side, flame.name)
            if cache not in self._lit:
                pixmap = self.pixmaps.get(key)
                if pixmap is None or pixmap.isNull():
                    return None
                self._lit[cache] = lit_images(pixmap, side, flame)
            return self._lit[cache]

        def _body_for(self, key, side, face):
            """The portrait's silhouette, opaque, in the card's own face
            colour: laid under the portrait it hides the fire behind the
            body, so a faint silhouette (the «?» card's) looks as it does on
            a cold card and the fire burns behind it, as on the others."""
            cache = ("body", key, side, face.rgba())
            if cache not in self._lit:
                pixmap = self.pixmaps.get(key)
                if pixmap is None or pixmap.isNull():
                    return None
                self._lit[cache] = mask_image(
                    charfire.body_mask(portrait_alpha(pixmap, side)), face)
            return self._lit[cache]

        def _paint_sparks(self, p, box, fx, flame, front):
            sparks = fx.sparks
            if not len(sparks.age):
                return
            side = box.width()
            p.setCompositionMode(Plus)
            for i in range(len(sparks.age)):
                if bool(sparks.front[i]) != front:
                    continue
                left = 1.0 - float(sparks.age[i] / sparks.life[i])
                twinkle = 0.72 + 0.28 * math.sin(sparks.t * 26.0
                                                 + float(sparks.phase[i]))
                alpha = min(1.0, left * 2.6) * twinkle
                x = box.left() + float(sparks.pos[i, 0]) * side
                y = box.top() + float(sparks.pos[i, 1]) * side
                d = side * float(sparks.size[i]) * (0.55 + 0.45 * left)
                if front:
                    d *= 0.8
                head = QtCore.QPointF(x, y)
                tail = QtCore.QPointF(x - float(sparks.vel[i, 0]) * side * 0.05,
                                      y - float(sparks.vel[i, 1]) * side * 0.05)
                grad = QtGui.QLinearGradient(head, tail)
                grad.setColorAt(0.0, fire_colour(flame.name, 0.5 + 0.4 * left,
                                                 0.65 * alpha))
                grad.setColorAt(1.0, QtGui.QColor(0, 0, 0, 0))
                pen = QtGui.QPen(QtGui.QBrush(grad), max(1.0, d * 0.28))
                pen.setCapStyle(Qt.RoundCap)
                p.setPen(pen)
                p.drawLine(head, tail)
                image = flame.sprites[2 if left > 0.66 else
                                      (1 if left > 0.33 else 0)]
                p.setOpacity(alpha)
                p.drawImage(QtCore.QRectF(x - d, y - d, 2 * d, 2 * d), image)
                p.setOpacity(1.0)
            p.setCompositionMode(Over)

        def _paint_hot(self, p, index, rect, fx):
            """A burning portrait, in the coordinates of whoever paints it:
            grown on its spring, its glow, its fire behind the character,
            the character lit by it, sparks in front and past its edges."""
            k = self.k
            radius = look.RADIUS * k
            model = self.models[index]
            key = model.key
            flame = fire_look(charfire.fire_of(key) or "ember")
            state = look.state(key, self.kind, self.selected,
                               catalog.kinds_of(key))
            selected = state == "selected"
            dragging = self._drag["model"] if self._drag else None
            hot, heat = fx.power, fx.warm
            grow = 1.0 + charfire.GROW * fx.shown_grow()
            box = QtCore.QRectF(*rect)
            centre = box.center()
            p.save()
            p.translate(centre)
            p.scale(grow, grow)
            p.translate(-centre)
            shape = QtGui.QPainterPath()
            shape.addRoundedRect(box, radius, radius)

            # the glow, behind the card
            glow = 0.55 * hot + 0.35 * heat + 0.3 * fx.flash
            if glow > 0.01:
                rings, step = 9, 1.6 * k
                p.setBrush(Qt.NoBrush)
                for i in range(rings, 0, -1):
                    c = QtGui.QColor(flame.glow)
                    c.setAlphaF(min(1.0, glow * 0.22
                                    * (1.0 - (i - 1) / float(rings)) ** 1.6))
                    p.setPen(QtGui.QPen(c, step * 1.4))
                    p.drawRoundedRect(box.adjusted(-i * step, -i * step,
                                                   i * step, i * step),
                                      radius + i * step, radius + i * step)

            # the face, warming with the fire
            if selected:
                face = colour("card_active")
            elif self._hover == key and not dragging:
                face = colour("hover")
            else:
                face = colour("field")
            p.fillPath(shape, mix(face, flame.bg_hot,
                                  min(1.0, 0.35 * hot + 0.75 * heat)))

            pixmap = self.pixmaps.get(key)
            side = int(round(box.width()))
            p.save()
            p.setClipPath(shape)
            if hot > 0.002 or heat > 0.002:
                dark = QtGui.QLinearGradient(box.topLeft(), box.bottomLeft())
                dark.setColorAt(0.0, QtGui.QColor(0, 0, 0, int(150 * hot)))
                dark.setColorAt(0.6, QtGui.QColor(0, 0, 0, 0))
                p.fillRect(box, QtGui.QBrush(dark))
                embers = QtGui.QRadialGradient(
                    QtCore.QPointF(centre.x(),
                                   box.bottom() + box.height() * 0.15),
                    box.width() * 0.95)
                c = QtGui.QColor(flame.base)
                c.setAlphaF(min(1.0, 0.30 * heat + 0.20 * fx.flash))
                embers.setColorAt(0.0, c)
                embers.setColorAt(1.0, QtGui.QColor(0, 0, 0, 0))
                p.setCompositionMode(Plus)
                p.fillRect(box, QtGui.QBrush(embers))
                target = box.adjusted(-box.width() * 0.03, 0,
                                      box.width() * 0.03, box.height() * 0.02)
                data = fx.fire.field(flame.lut, target.width(),
                                     target.height())
                height, width = data.shape[0], data.shape[1]
                image = QtGui.QImage(data.data, width, height, width * 4,
                                     Premultiplied)
                p.drawImage(target, image)
                del image, data
                p.setCompositionMode(Over)
                self._paint_sparks(p, box, fx, flame, front=False)
            body = self._body_for(key, side, face)
            if body is not None:                 # the fire behind the body
                p.drawImage(box, body)
            p.setOpacity(0.45 if dragging == key else 1.0)
            if pixmap is not None and not pixmap.isNull():
                p.drawPixmap(box, pixmap, QtCore.QRectF(pixmap.rect()))
            else:
                self._missing(p, box)
            p.setOpacity(1.0)
            if hot > 0.002 or heat > 0.002:
                lit = self._lit_for(key, side, flame)
                if lit:
                    shade, rim, light = lit
                    flicker = (0.82 + 0.18 * math.sin(fx.fire.t * 17.0)
                               * math.sin(fx.fire.t * 5.3))
                    p.setOpacity(0.30 * hot)                 # backlit
                    p.drawImage(box, shade)
                    p.setCompositionMode(Plus)
                    p.setOpacity(min(1.0, (0.20 + 0.60 * heat) * hot
                                     * flicker))
                    p.drawImage(box, rim)
                    p.setOpacity(min(1.0, 0.26 * heat * flicker
                                     + 0.18 * fx.flash))
                    p.drawImage(box, light)
                    p.setOpacity(1.0)
                    p.setCompositionMode(Over)
                self._paint_sparks(p, box, fx, flame, front=True)
            p.restore()

            # the name over the bottom, under the ring (2026-10-08: it lies
            # inside the square, so it is part of the grown card)
            self._paint_name(p, rect, model.label, state, False, hot, flame)

            # the ring, hot
            if selected:
                ring, width = colour("accent"), max(1.5, 2 * k)
            elif self._hover == key and not dragging:
                ring, width = colour("text2"), max(1.0, k)
            else:
                ring, width = colour("line"), max(1.0, k)
            if hot > 0.01:
                ring = mix(ring, flame.ring, min(1.0, hot * 0.6 + heat * 0.5))
                width = max(width, (1.0 + 1.2 * hot) * k)
            p.setPen(QtGui.QPen(ring, width))
            p.setBrush(Qt.NoBrush)
            half = width / 2.0
            p.drawRoundedRect(box.adjusted(half, half, -half, -half),
                              radius, radius)

            # the sparks that left the card fly on
            if fx.sparks.alive():
                outside = QtGui.QPainterPath()
                outside.addRect(box.adjusted(-box.width() * 4,
                                             -box.height() * 4,
                                             box.width() * 4,
                                             box.height() * 4))
                p.setClipPath(outside.subtracted(shape))
                self._paint_sparks(p, box, fx, flame, front=False)
                self._paint_sparks(p, box, fx, flame, front=True)
            p.restore()

        def _paint_burning(self, p, models):
            """The burning cards among `models`, the most grown last (over
            its neighbours), in the grid's coordinates."""
            rects = self.rects()
            order = sorted((key for key in models if key in self.fx),
                           key=lambda key: self.fx[key].shown_grow())
            for key in order:
                index = self._index(key)
                if index is not None and index < len(rects):
                    self._paint_hot(p, index, rects[index], self.fx[key])

        def paintEvent(self, _event):                        # noqa: N802
            started = time.perf_counter()
            p = QtGui.QPainter(self)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
            dragging = self._drag["model"] if self._drag else None
            for index, rect in enumerate(self.rects()):
                if self.models[index].key in self.fx:
                    continue                     # burning: drawn hot
                self._paint_cold(p, index, rect, dragging)
            self._paint_burning(p, [key for key in self.fx
                                    if key not in self.overlaid])
            p.end()
            self.paint_ms = (time.perf_counter() - started) * 1000.0

    _CLASSES.update(Keeper=Keeper, PortraitGrid=PortraitGrid, Ghost=Ghost,
                    FireOverlay=FireOverlay, scrolled_content=scrolled_content,
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
