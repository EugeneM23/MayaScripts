"""The Armor card's tiles: pick a piece, press Equip.

2026-10-01, the animator: «в отличии от оружия не нужно делать сетчатый инвентарь а просто будем
выделять предмет нажимать кнопочку equip» -- and, asked how the items look, icon tiles like the
Characters portraits. One square icon per `catalog.ARMOR` row with its name under it:

- a CLICK picks the row (the card's line says what Equip will do; the pick is remembered);
- a row the current character wears carries an «equipped» pill;
- the RIGHT BUTTON offers Open scene: the row's model opened as the scene (`opener`), as the
  portraits and the weapons do;
- no drag: Equip puts a piece in its one predetermined place.

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

        def refresh(self):
            """The worn pills re-read from the scene."""
            try:
                self.worn = set(self.scene.worn() or ())
            except Exception:                                # noqa: BLE001
                traceback.print_exc()
                self.worn = set()
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

        # ------------------------------------------------------- mouse

        def _local(self, event):
            return event.position().toPoint() if hasattr(event, "position") else event.pos()

        def _global(self, event):
            return (event.globalPosition().toPoint() if hasattr(event, "globalPosition")
                    else event.globalPos())

        def mousePressEvent(self, event):                    # noqa: N802
            local = self._local(event)
            key = self.key_at(local.x(), local.y())
            if event.button() == Qt.RightButton:
                maya_hubqt.run_menu(self, self._global(event), self.context_actions(key))
                return
            if event.button() == Qt.LeftButton and key:
                self.select(key)

        def mouseMoveEvent(self, event):                     # noqa: N802
            local = self._local(event)
            hover = self.key_at(local.x(), local.y())
            if hover != self._hover:
                self._hover = hover
                self.update()

        def leaveEvent(self, _event):                        # noqa: N802
            if self._hover is not None:
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
