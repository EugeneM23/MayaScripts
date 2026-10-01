"""The Armor card's tiles: pick a piece, press Equip.

2026-10-01, the animator: «в отличии от оружия не нужно делать сетчатый инвентарь а просто будем
выделять предмет нажимать кнопочку equip» -- and, asked how the items look, icon tiles like the
Characters portraits. One square icon per `catalog.ARMOR` row with its name under it:

- a CLICK picks the row (the card's line says what Equip will do; the pick is remembered);
- a row the current character wears carries an «equipped» pill;
- the RIGHT BUTTON offers Open scene: the row's model opened as the scene (`opener`), as the
  portraits and the weapons do;
- a DRAG (since the evening, the Inventory card: «Броню тоже можно перетаскивать на персонажа -
  да, как оружие») carries the icon; released on a character in a viewport the piece goes on him,
  in its one predetermined place (`armorpanel.equip_on`); anywhere else nothing.

The tiles live in a `cmds` card exactly as the portraits do: the builder makes an empty
columnLayout and `attach` lays the grid over it, the placeholder kept as tall as the grid needs
for its width (the portraits' Keeper) -- so the same tiles stand in the skinned hub and the
classic one. The layout is `maya_charlook`'s; everything the tiles do to the scene goes through
`Scene`, which the tests replace. Qt is imported lazily (`maya_hubqt.qt()`).

Spec: docs/superpowers/specs/2026-10-01-armor-techlimb-design.md
"""

import os
import traceback

import maya_charlook as look

OBJECT_NAME = "skeldarArmorGrid"
GHOST_NAME = "skeldarArmorGhost"
OFF_HUB = "release off the hub to equip"
WORN_TEXT = "equipped"
OPEN_SCENE = look.OPEN_SCENE

#  The grids standing, by the placeholder they are laid over.
_GRIDS = {}


def _last_line(error_text):
    lines = [line for line in (error_text or "").strip().splitlines() if line.strip()]
    return lines[-1] if lines else "failed"


# ------------------------------------------------------------------ scene

class Scene(object):
    """The real scene: what the tiles ask and what they do to it (the card's functions)."""

    def scale(self):
        import maya.cmds as cmds
        try:
            return float(cmds.mayaDpiSetting(query=True, realScaleValue=True) or 1.0)
        except Exception:                                    # noqa: BLE001
            return 1.0

    def select(self, key):
        from maya_scenesetup import armorpanel
        armorpanel.select_armor(key)

    def open_scene(self, key):
        from maya_scenesetup import armorpanel
        return armorpanel.open_armor_scene(key)

    def worn(self):
        from maya_scenesetup import armorpanel
        return armorpanel.worn_keys()

    def snapshot(self):
        """Every character's bones, read once for one drag."""
        from maya_scenesetup import droptarget
        return droptarget.snapshot()

    def target(self, gx, gy, snap):
        from maya_scenesetup import droptarget
        return droptarget.character_target(gx, gy, snap, self.scale())

    def over_hub(self, gx, gy):
        import maya_hubqt
        return maya_hubqt.on_hub(gx, gy)

    def equip_on(self, root, key):
        from maya_scenesetup import armorpanel
        return armorpanel.equip_on(root, key)

    def say(self, text):
        try:
            from maya_scenesetup import armorpanel
            armorpanel.say(text)
        except Exception:                                    # noqa: BLE001
            pass


# -------------------------------------------------------------------- Qt

_CLASSES = {}


def _classes():
    """The widget class, built on first use (Qt imported here)."""
    if _CLASSES:
        return _CLASSES
    import maya_chargrid
    import maya_hubqt
    from maya_scenesetup import catalog

    q = maya_hubqt.qt()
    QtCore, QtGui, QtWidgets = q.QtCore, q.QtGui, q.QtWidgets
    Qt = QtCore.Qt
    Ghost = maya_hubqt.ghost_class()     # the hub's own, the portraits' too

    def colour(name):
        return QtGui.QColor(look.PALETTE[name])

    def font(px, bold=False):
        f = QtGui.QFont()
        f.setPixelSize(max(1, int(round(px))))
        f.setBold(bold)
        return f

    class ArmorGrid(QtWidgets.QWidget):
        """The tiles. `scene` is `Scene()` in Maya, a fake in the tests."""

        def __init__(self, scene, parent=None, selected=None):
            QtWidgets.QWidget.__init__(self, parent)
            self.setObjectName(OBJECT_NAME)
            self.scene = scene
            self.k = float(scene.scale() or 1.0)
            self.rows = list(catalog.ARMOR)
            self.keys = [row.key for row in self.rows]
            self.selected = selected
            self.worn = set()
            self.status_text = ""
            self.pixmaps = {}
            for row in self.rows:
                path = catalog.armor_icon_path(row.key)
                if os.path.isfile(path):
                    self.pixmaps[row.key] = QtGui.QPixmap(path)
            self._hover = None
            self._press = None
            self._drag = None
            self._clock = QtCore.QElapsedTimer()
            self._clock.start()
            self.setMouseTracking(True)
            self.setCursor(Qt.PointingHandCursor)
            self.refresh()

        # ------------------------------------------------------ layout

        def height_for(self, width):
            return look.grid(width, len(self.rows), self.k)[3]

        def rects(self):
            return look.grid(self.width(), len(self.rows), self.k)[2]

        def fit(self, host):
            """Over the whole of `host`, and `host` as tall as the tiles."""
            self.setGeometry(host.rect())
            want = self.height_for(host.width())
            if host.height() != want:
                host.setFixedHeight(want)
                self.setGeometry(host.rect())

        def sizeHint(self):                                  # noqa: N802
            width = max(1, self.width())
            return QtCore.QSize(width, self.height_for(width))

        # ------------------------------------------------------- state

        def key_at(self, x, y):
            index = look.hit(self.rects(), x, y, self.k)
            return self.keys[index] if index is not None else None

        def set_selected(self, key):
            self.selected = key
            self.update()

        def select(self, key):
            """A tile picked: True when it could be."""
            if not key or key not in self.keys:
                return False
            self.selected = key
            self.update()
            self.scene.select(key)
            return True

        def refresh(self, worn=None):
            """The worn pills: `worn` when the caller has read it, else asked of the scene."""
            if worn is None:
                try:
                    worn = self.scene.worn()
                except Exception:                            # noqa: BLE001
                    traceback.print_exc()
                    worn = ()
            self.worn = set(worn or ())
            self.update()

        def _act(self, action):
            try:
                text = action()
            except Exception:                                # noqa: BLE001
                traceback.print_exc()
                text = _last_line(traceback.format_exc())
            self.status_text = text or ""
            self.scene.say(self.status_text)
            return self.status_text

        def context_actions(self, key):
            """What the right button offers over `key`: the row's model opened as the scene.
            [] off every tile."""
            if not key:
                return []
            return [(OPEN_SCENE, lambda: self._act(lambda: self.scene.open_scene(key)))]

        def _label(self, key):
            row = catalog.armor_by_key(key)
            return row.label if row else key

        def drop_at(self, gx, gy, key=None):
            """The release of a drag of `key` at the global point: on a
            character in a viewport, the piece on him; anywhere else nothing.
            Public, so a verify can drive it without a mouse."""
            key = key or (self._drag or {}).get("key")
            if not key:
                return self.status_text
            local = self.mapFromGlobal(QtCore.QPoint(int(gx), int(gy)))
            if self.rect().contains(local) or self.scene.over_hub(gx, gy):
                return self.status_text          # back on the hub: nothing
            snap = self._drag["snap"] if self._drag else self.scene.snapshot()
            aim = self.scene.target(gx, gy, snap)
            if aim.get("kind") == "character":
                root = aim["root"]
                return self._act(lambda: self.scene.equip_on(root, key))
            self.status_text = aim.get("text") or "no target"
            self.scene.say(self.status_text)
            return self.status_text

        # -------------------------------------------------------- drag

        def _start(self, key, point):
            size = int(look.GHOST * self.k)
            ghost = Ghost(self.pixmaps.get(key) or QtGui.QPixmap(), size, size, self.k,
                          anchor=(0.5, 0.5), name=GHOST_NAME, backdrop="field")
            try:
                snap = self.scene.snapshot()
            except Exception:                                # noqa: BLE001
                traceback.print_exc()
                snap = []
            self._drag = dict(key=key, ghost=ghost, snap=snap)
            self._press = None
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
            try:
                if (self.rect().contains(self.mapFromGlobal(point))
                        or self.scene.over_hub(gx, gy)):
                    drag["ghost"].set_caption(OFF_HUB, False)
                    return
                aim = self.scene.target(gx, gy, drag["snap"])
            except Exception:                                # noqa: BLE001
                aim = dict(kind="none", text=_last_line(traceback.format_exc()))
            if aim.get("kind") == "character":
                drag["ghost"].set_caption("%s %s %s" % (
                    self._label(drag["key"]), look.DOT, aim.get("text", "")), True)
            else:
                drag["ghost"].set_caption(aim.get("text", ""), False)

        # ------------------------------------------------------- mouse

        def _local(self, event):
            return event.position().toPoint() if hasattr(event, "position") else event.pos()

        def _global(self, event):
            return (event.globalPosition().toPoint() if hasattr(event, "globalPosition")
                    else event.globalPos())

        def mousePressEvent(self, event):                    # noqa: N802
            if self._drag:
                if event.button() == Qt.RightButton:
                    self._end()
                    self.scene.say("cancelled")
                return
            local = self._local(event)
            key = self.key_at(local.x(), local.y())
            if event.button() == Qt.RightButton:
                self._press = None
                maya_hubqt.run_menu(self, self._global(event), self.context_actions(key))
                return
            if event.button() == Qt.LeftButton and key and self.select(key):
                point = self._global(event)
                self._press = (key, (point.x(), point.y()))

        def mouseMoveEvent(self, event):                     # noqa: N802
            point = self._global(event)
            if self._drag:
                self._drag["ghost"].follow(point)
                self._caption(point)
                return
            if self._press and event.buttons() & Qt.LeftButton:
                key, start = self._press
                if look.dragged(start, (point.x(), point.y()),
                                QtWidgets.QApplication.startDragDistance()):
                    self._start(key, point)
                return
            local = self._local(event)
            hover = self.key_at(local.x(), local.y())
            if hover != self._hover:
                self._hover = hover
                self.update()

        def mouseReleaseEvent(self, event):                  # noqa: N802
            if self._drag and event.button() == Qt.LeftButton:
                point = self._global(event)
                key = self._drag["key"]
                try:
                    self.drop_at(point.x(), point.y(), key)
                finally:
                    self._end()
                return
            self._press = None

        def keyPressEvent(self, event):                      # noqa: N802
            if event.key() == Qt.Key_Escape and self._drag:
                self._end()
                self.scene.say("cancelled")
                return
            QtWidgets.QWidget.keyPressEvent(self, event)

        def leaveEvent(self, _event):                        # noqa: N802
            if self._hover is not None and not self._drag:
                self._hover = None
                self.update()

        # ------------------------------------------------------- paint

        def _stroke(self, p, box, radius, name, width):
            p.setPen(QtGui.QPen(colour(name), width))
            p.setBrush(Qt.NoBrush)
            half = width / 2.0
            p.drawRoundedRect(box.adjusted(half, half, -half, -half), radius, radius)

        def _missing(self, p, box):
            """No icon file: the hub's shield glyph, muted, centred."""
            side = int(box.width() * 0.45)
            try:
                icon = maya_hubqt.pixmap("shield", look.PALETTE["muted"], side)
            except Exception:                                # noqa: BLE001
                return
            p.drawPixmap(int(box.center().x() - side / 2.0),
                         int(box.center().y() - side / 2.0), icon)

        def paintEvent(self, _event):                        # noqa: N802
            k = self.k
            p = QtGui.QPainter(self)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
            radius = look.RADIUS * k
            for index, rect in enumerate(self.rects()):
                row = self.rows[index]
                chosen = row.key == self.selected
                lit = self._hover == row.key and not chosen
                box = QtCore.QRectF(*rect)
                shape = QtGui.QPainterPath()
                shape.addRoundedRect(box, radius, radius)
                p.fillPath(shape, colour("card_active" if chosen else
                                         ("hover" if lit else "field")))
                p.save()
                p.setClipPath(shape)
                pixmap = self.pixmaps.get(row.key)
                if pixmap is not None and not pixmap.isNull():
                    inset = int(6 * k)
                    p.drawPixmap(box.toRect().adjusted(inset, inset, -inset, -inset), pixmap)
                else:
                    self._missing(p, box)
                p.restore()
                if chosen:
                    self._stroke(p, box, radius, "accent", max(1.5, 2 * k))
                elif lit:
                    self._stroke(p, box, radius, "text2", max(1.0, k))
                else:
                    self._stroke(p, box, radius, "line", max(1.0, k))

                if row.key in self.worn:
                    pad = int(4 * k)
                    tag = QtCore.QRectF(box.left() + pad, box.bottom() - pad - int(16 * k),
                                        box.width() - 2 * pad, int(16 * k))
                    p.setPen(Qt.NoPen)
                    p.setBrush(colour("ok_tint"))
                    p.drawRoundedRect(tag, 4 * k, 4 * k)
                    p.setFont(font(10.5 * k, bold=True))
                    p.setPen(colour("ok"))
                    p.drawText(tag, Qt.AlignCenter, WORN_TEXT)

                nx, ny, nw, nh = look.name_rect(rect, k)
                name_font = font(11.5 * k, bold=chosen)
                p.setFont(name_font)
                p.setPen(colour("text" if chosen else "text2"))
                text = QtGui.QFontMetrics(name_font).elidedText(row.label, Qt.ElideRight, int(nw))
                p.drawText(QtCore.QRect(int(nx), int(ny), int(nw), int(nh)),
                           Qt.AlignHCenter | Qt.AlignVCenter, text)
            p.end()

    _CLASSES.update(ArmorGrid=ArmorGrid, Keeper=maya_chargrid._classes()["Keeper"], qt=q)
    return _CLASSES


# ----------------------------------------------------------------- open

def make_grid(scene, parent=None, selected=None):
    """Tiles over `scene` - the tests' seam."""
    return _classes()["ArmorGrid"](scene, parent, selected)


def attach(placeholder, scene=None, selected=None):
    """Lay the tiles over the `cmds` layout `placeholder`, or None where they cannot stand (no
    Qt, no such layout) -- the portraits' pattern (`maya_chargrid.attach`)."""
    import maya_hubqt
    if maya_hubqt.qt() is None:
        return None
    host = maya_hubqt.find(placeholder, layout=True)
    if host is None:
        return None
    classes = _classes()
    grid = classes["ArmorGrid"](scene or Scene(), host, selected)
    grid._host = host                    # the wrapper lives as long as the grid
    grid._keeper = classes["Keeper"](grid, grid)
    host.installEventFilter(grid._keeper)
    grid.fit(host)
    grid.show()
    _GRIDS[placeholder] = grid
    return grid


def live(placeholder):
    """The tiles standing over `placeholder`, or None."""
    grid = _GRIDS.get(placeholder)
    if grid is None:
        return None
    try:
        if _classes()["qt"].shiboken.isValid(grid):
            return grid
    except Exception:                                        # noqa: BLE001
        pass
    _GRIDS.pop(placeholder, None)
    return None
