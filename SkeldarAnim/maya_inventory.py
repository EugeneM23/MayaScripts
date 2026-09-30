"""The weapon inventory: a window whose weapons go onto the character.

2026-09-29, the animator: «кнопка которая будет инвентарь похожий на
инвентарь как в игре diablo, чтобы я оружие переносил из этого инвентаря
прямо на персонажа и оно как вставлялось в руку или выпадало на пол». The
grid and the drag are the game's; the look is the hub's own since 2026-09-30
(«дизайн инвентаря все же не в стиле диабло а в стиле нашего интерфейса»):
the charcoal panel, rounded cards, the orange accent on the drop target.

A frameless tool window over Maya, opened by Weapons > Inventory or the
hotkey row `window.inventory`:

- the GRID is the catalog - every weapon always there, taken as often as
  wanted, by any character, each sized in cells by its model's length;
- two hand SLOTS show the current character's hands (the selection, else the
  only rig, else the only skeleton): a weapon in the hand, one on the floor
  following its bone (dimmed), a hand riding a weapon (its name);
- a DRAG - press on an item, move, release: the icon follows the cursor with
  a caption naming the target, Esc or the right button cancels. Released on a
  slot, the weapon goes into that hand; on the grid, a slot's weapon comes
  off; outside the window, onto the hand under the cursor in the viewport or,
  missing every character, onto the floor under it (`droptarget`).

The mouse is ours for the whole drag: a press captures it on Windows, so the
moves and the release keep coming here over the viewport, which never sees
them, and Maya's own drop handling never enters. Everything the window does
to the scene goes through `Scene`, which the tests replace; everything it
looks like is `maya_invlook`'s. Qt is imported lazily (`maya_hubqt.qt()`),
the classes are built on first use.

Spec: docs/superpowers/specs/2026-09-29-weapon-inventory-design.md
"""

import os
import traceback

import maya_invlook as look

OBJECT_NAME = "skeldarInventory"
GHOST_NAME = "skeldarInventoryGhost"
POSITION_OPTIONVAR = "skeldarInventoryGeometry"
LAYOUT_OPTIONVAR = "skeldarInventoryLayout"     # the grid as the animator left it
THROTTLE_MS = 33
HINT = "Drag a weapon onto a hand in the viewport, or onto the floor"
SLOT_LABEL = {"R": "Right hand", "L": "Left hand"}
WEAPONS_STATUS = "mayaSceneSetupStatus"      # the Weapons section's line
EVENTS = ("SelectionChanged", "Undo", "Redo", "SceneOpened", "NewSceneOpened")


def _last_line(error_text):
    lines = [line for line in (error_text or "").strip().splitlines() if line.strip()]
    return lines[-1] if lines else "failed"


# ------------------------------------------------------------------ scene

class Scene(object):
    """The real scene: what the window asks and what it does to it."""

    def scale(self):
        import maya.cmds as cmds
        try:
            return float(cmds.mayaDpiSetting(query=True, realScaleValue=True)
                         or 1.0)
        except Exception:                                    # noqa: BLE001
            return 1.0

    def current(self):
        from maya_scenesetup import skeleton
        return skeleton.current_root()

    def label(self, root):
        from maya_scenesetup import equip
        return equip.character_name(root)

    def holdings(self, root):
        from maya_scenesetup import equip
        return equip.holdings(root)

    def snapshot(self):
        from maya_scenesetup import droptarget
        return droptarget.snapshot()

    def target(self, gx, gy, snap, freed=None):
        from maya_scenesetup import droptarget
        return droptarget.target(gx, gy, snap, self.scale(), freed)

    def to_hand(self, root, side, entry):
        from maya_scenesetup import equip
        return equip.to_hand(root, side, entry)

    def to_floor(self, root, entry, point, heading, side=None):
        from maya_scenesetup import equip
        return equip.to_floor(root, entry, point, heading, side)

    def take_off(self, root, side):
        from maya_scenesetup import equip
        return equip.take_off(root, side)

    def move(self, root, side, target):
        from maya_scenesetup import equip
        return equip.move(root, side, target)

    def watch(self, callback):
        """A scriptJob per event, calling `callback` - the doll follows the
        selection, undo and a new scene."""
        import maya.cmds as cmds
        return [cmds.scriptJob(event=[event, callback]) for event in EVENTS]

    def unwatch(self, jobs):
        import maya.cmds as cmds
        for job in jobs or []:
            try:
                if cmds.scriptJob(exists=job):
                    cmds.scriptJob(kill=job, force=True)
            except Exception:                                # noqa: BLE001
                pass

    def echo(self, text):
        """The Weapons section's status line says it too, when it is built."""
        import maya.cmds as cmds
        try:
            if cmds.control(WEAPONS_STATUS, exists=True):
                cmds.text(WEAPONS_STATUS, edit=True, label=text)
        except Exception:                                    # noqa: BLE001
            pass

    def remembered_position(self):
        import maya.cmds as cmds
        if not cmds.optionVar(exists=POSITION_OPTIONVAR):
            return None
        try:
            x, y = [int(v) for v in cmds.optionVar(query=POSITION_OPTIONVAR).split()]
            return x, y
        except Exception:                                    # noqa: BLE001
            return None

    def remember_position(self, x, y):
        import maya.cmds as cmds
        cmds.optionVar(stringValue=(POSITION_OPTIONVAR, "%d %d" % (x, y)))

    def remembered_layout(self):
        """The grid as it was left ({key: [col, row]}), {} when never moved."""
        import maya.cmds as cmds
        if not cmds.optionVar(exists=LAYOUT_OPTIONVAR):
            return {}
        return look.read_record(cmds.optionVar(query=LAYOUT_OPTIONVAR))

    def remember_layout(self, placements):
        import maya.cmds as cmds
        cmds.optionVar(stringValue=(LAYOUT_OPTIONVAR, look.layout_record(placements)))


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

    def colour(name, alpha=255):
        c = QtGui.QColor(look.PALETTE[name])
        c.setAlpha(alpha)
        return c

    def font(px, bold=False):
        """The UI font, as the hub's stylesheet leaves it."""
        f = QtGui.QFont()
        f.setPixelSize(max(1, int(round(px))))
        f.setBold(bold)
        return f

    def rounded(p, box, radius, fill=None, edge=None, width=1.0):
        """A rounded rect in the hub's corners: `fill` and `edge` are token
        names (None for none), the pen drawn inside the box."""
        half = width / 2.0
        shape = QtCore.QRectF(box).adjusted(half, half, -half, -half)
        p.setPen(QtGui.QPen(colour(edge), width) if edge else Qt.NoPen)
        p.setBrush(colour(fill) if fill else Qt.NoBrush)
        p.drawRoundedRect(shape, radius, radius)

    def rect_of(r):
        return QtCore.QRect(int(r[0]), int(r[1]), int(r[2]), int(r[3]))

    def fitted(pixmap, box, margin):
        """`pixmap`'s rect fitted inside `box` (a QRect), aspect kept."""
        inner = box.adjusted(margin, margin, -margin, -margin)
        if pixmap.isNull() or inner.width() <= 0 or inner.height() <= 0:
            return inner
        size = pixmap.size().scaled(inner.size(), Qt.KeepAspectRatio)
        return QtCore.QRect(inner.x() + (inner.width() - size.width()) // 2,
                            inner.y() + (inner.height() - size.height()) // 2,
                            size.width(), size.height())

    #  The drag ghost is the hub's own since 2026-09-30, shared with the
    #  Characters portrait grid (maya_hubqt.ghost_class).
    Ghost = maya_hubqt.ghost_class()

    class InventoryWindow(QtWidgets.QWidget):
        """The inventory. `scene` is `Scene()` in Maya, a fake in the tests."""

        def __init__(self, scene, parent=None, remember=True):
            QtWidgets.QWidget.__init__(self, parent,
                                       Qt.Tool | Qt.FramelessWindowHint)
            self.setObjectName(OBJECT_NAME)
            self.setWindowTitle("Inventory")
            # the panel's rounded corners: nothing painted outside them
            self.setAttribute(Qt.WA_TranslucentBackground)
            self.scene = scene
            self.k = float(scene.scale() or 1.0)
            self.cell = look.CELL * self.k
            self.rects = look.scaled(look.layout(), self.k)
            _x, _y, width, height = self.rects["window"]
            self.setFixedSize(width, height)
            stored = look.load_cells()
            self.cells = dict((e.key, stored.get(e.key, (1, 3)))
                              for e in catalog.WEAPONS)
            # the grid as the animator left it (2026-09-29), new rows in the
            # free cells, a broken record never losing an item
            try:
                record = scene.remembered_layout()
            except Exception:                                # noqa: BLE001
                record = {}
            self.placements = look.arrange(self._items(), record)
            self.preview = None
            self.pixmaps = {}
            for entry in catalog.WEAPONS:
                path = look.icon_path(entry.key)
                if os.path.isfile(path):
                    self.pixmaps[entry.key] = QtGui.QPixmap(path)
            self.status_text = HINT
            self.root, self.name, self.holding = None, "", {}
            self._drag = None
            self._moving = None
            self._hover = None
            self._clock = QtCore.QElapsedTimer()
            self._clock.start()
            self._remember = remember
            self.setMouseTracking(True)
            self.setFocusPolicy(Qt.StrongFocus)
            self._jobs = scene.watch(self._queue_refresh)
            jobs, watcher = self._jobs, scene
            self.destroyed.connect(lambda *_a: watcher.unwatch(jobs))
            if remember:
                spot = scene.remembered_position()
                if spot and QtGui.QGuiApplication.screenAt(QtCore.QPoint(*spot)):
                    self.move(*spot)
            self.refresh()

        # ---------------------------------------------------------- state

        def refresh(self):
            try:
                self.root = self.scene.current()
                self.holding = self.scene.holdings(self.root) if self.root else {}
                self.name = (self.scene.label(self.root) if self.root else
                             "no character - select one (or keep one rig)")
            except Exception:                                # noqa: BLE001
                self.holding = {}
                self.status_text = _last_line(traceback.format_exc())
            self.update()

        def _queue_refresh(self, *_args):
            try:
                QtCore.QTimer.singleShot(0, self.refresh)
            except Exception:                                # noqa: BLE001
                pass

        def _say(self, text):
            self.status_text = text or ""
            self.scene.echo(self.status_text)
            self.update()
            return self.status_text

        def _act(self, action):
            try:
                text = action()
            except Exception:                                # noqa: BLE001
                traceback.print_exc()
                text = _last_line(traceback.format_exc())
            self._say(text)
            self.refresh()
            return text

        def _entry(self, key):
            return catalog.by_key(key)

        def _items(self):
            return [(e.key, self.cells[e.key]) for e in catalog.WEAPONS]

        def _label(self, key):
            entry = catalog.by_key(key)
            return entry.label if entry else key

        # ------------------------------------------------ the grid by hand

        def grid_plan(self, x, y, key, grab):
            """(kind, placements, other, spot) for `key` released at local
            (x, y), pressed `grab` cells into itself - the grab point stays
            under the cursor (`look.plan_move`: move, swap, same or None)."""
            gx, gy = self.rects["grid"][:2]
            spot = (int((x - gx) // self.cell) - grab[0],
                    int((y - gy) // self.cell) - grab[1])
            size = self.cells.get(key, (1, 3))
            spot = look.clamp(spot, size)
            kind, placed, other = look.plan_move(self.placements, self.cells,
                                                 key, spot)
            return kind, placed, other, spot

        def _rearrange(self, key, x, y, grab):
            kind, placed, other, _spot = self.grid_plan(x, y, key, grab)
            if kind == "same":
                return self.status_text
            if kind is None:
                return self._say("no room there for the %s" % self._label(key))
            self.placements = placed
            self.scene.remember_layout(placed)
            if kind == "swap":
                return self._say("%s and %s swapped" % (self._label(key),
                                                        self._label(other)))
            return self._say("%s moved" % self._label(key))

        def sort(self):
            """The catalog packed again in its order, and remembered."""
            self.placements = look.pack(self._items())
            self.scene.remember_layout(self.placements)
            return self._say("inventory sorted")

        def _grid_menu(self, point):
            menu = QtWidgets.QMenu(self)
            action = menu.addAction("Sort the inventory")
            if menu.exec(point) is action:
                self.sort()

        def source_at(self, x, y):
            """What a press at local (x, y) would drag, or None."""
            what = look.hit(self.rects, self.placements, self.cells, x, y,
                            self.cell)
            if what and what[0] == "item":
                return ("grid", what[1])
            if what and what[0] == "slot":
                held = self.holding.get(what[1])
                if held and held.where in ("hand", "floor") and held.weapon:
                    return ("slot", what[1])
            return None

        def _key_of(self, source):
            if source[0] == "grid":
                return source[1]
            held = self.holding.get(source[1])
            return held.key if held else ""

        # ----------------------------------------------------------- drop

        def drop_at(self, gx, gy, source, grab=None):
            """The release of a drag from `source` at the global point: the
            spec's table. Public, so a verify can drive it without a mouse.
            `grab` is where a grid item was pressed, in its own cells (the
            drag's when a drag is on)."""
            kind, arg = source
            if grab is None:
                grab = (self._drag or {}).get("grab") or (0, 0)
            key = self._key_of(source)
            entry = self._entry(key) if kind == "grid" else None
            local = self.mapFromGlobal(QtCore.QPoint(int(gx), int(gy)))
            if self.rect().contains(local):
                what = look.hit(self.rects, self.placements, self.cells,
                                local.x(), local.y(), self.cell)
                if what and what[0] == "slot":
                    side = what[1]
                    if kind == "grid":
                        return self._act(lambda: self.scene.to_hand(self.root, side, entry))
                    if side != arg:
                        return self._act(lambda: self.scene.move(
                            self.root, arg, ("hand", self.root, side)))
                    return self.status_text
                if what and what[0] in ("grid", "item") and kind == "slot":
                    return self._act(lambda: self.scene.take_off(self.root, arg))
                if what and what[0] in ("grid", "item") and kind == "grid":
                    return self._rearrange(arg, local.x(), local.y(), grab)
                return self.status_text
            snap = self._drag["snap"] if self._drag else self.scene.snapshot()
            freed = (self.root, arg) if kind == "slot" else None
            aim = self.scene.target(gx, gy, snap, freed)
            if aim.get("kind") == "hand":
                if kind == "grid":
                    return self._act(lambda: self.scene.to_hand(
                        aim["root"], aim["side"], entry))
                if aim["root"] == self.root and aim["side"] == arg:
                    return self._say("already in the %s" % SLOT_LABEL[arg].lower())
                return self._act(lambda: self.scene.move(
                    self.root, arg, ("hand", aim["root"], aim["side"])))
            if aim.get("kind") == "floor":
                if kind == "grid":
                    return self._act(lambda: self.scene.to_floor(
                        aim["root"], entry, aim["point"], aim["heading"],
                        aim.get("side")))
                return self._act(lambda: self.scene.move(
                    self.root, arg, ("floor", aim["root"], aim["point"],
                                     aim["heading"])))
            return self._say(aim.get("text") or "no target")

        # ---------------------------------------------------------- drag

        def _start(self, source, point, grab=(0, 0)):
            key = self._key_of(source)
            pixmap = self.pixmaps.get(key) or QtGui.QPixmap()
            cells = self.cells.get(key, (1, 3))
            ghost = Ghost(pixmap, int(cells[0] * look.CELL * self.k),
                          int(cells[1] * look.CELL * self.k), self.k,
                          anchor=(0.5, 0.25), name=GHOST_NAME)
            try:
                snap = self.scene.snapshot()
            except Exception:                                # noqa: BLE001
                snap = []
                self._say(_last_line(traceback.format_exc()))
            self._drag = dict(source=source, ghost=ghost, snap=snap, grab=grab)
            ghost.follow(point)
            ghost.show()
            self.grabKeyboard()
            self._caption(point, force=True)

        def _end(self):
            if self._drag:
                ghost = self._drag["ghost"]
                ghost.hide()
                ghost.deleteLater()
            self._drag = None
            self.preview = None
            try:
                self.releaseKeyboard()
            except Exception:                                # noqa: BLE001
                pass
            self.update()

        def _caption(self, point, force=False):
            drag = self._drag
            if not drag:
                return
            source = drag["source"]
            local = self.mapFromGlobal(point)
            if self.rect().contains(local):
                what = look.hit(self.rects, self.placements, self.cells,
                                local.x(), local.y(), self.cell)
                self.preview = None
                if what and what[0] == "slot":
                    same = source == ("slot", what[1])
                    drag["ghost"].set_caption(SLOT_LABEL[what[1]], not same)
                elif what and what[0] in ("grid", "item") and source[0] == "slot":
                    drag["ghost"].set_caption("back to the inventory", True)
                elif what and what[0] in ("grid", "item") and source[0] == "grid":
                    kind, _placed, other, spot = self.grid_plan(
                        local.x(), local.y(), source[1], drag["grab"])
                    size = self.cells.get(source[1], (1, 3))
                    fits = kind in ("move", "swap")
                    if kind != "same":
                        self.preview = (look.footprint(spot, size), fits)
                    caption = {"move": "move here", "same": "",
                               "swap": "swap with %s" % self._label(other)}
                    drag["ghost"].set_caption(caption.get(kind, "no room"), fits
                                              or kind == "same")
                else:
                    drag["ghost"].set_caption("", True)
                self.update()
                return
            if self.preview is not None:
                self.preview = None
                self.update()
            if not force and self._clock.elapsed() < THROTTLE_MS:
                return
            self._clock.restart()
            freed = (self.root, source[1]) if source[0] == "slot" else None
            try:
                aim = self.scene.target(point.x(), point.y(), drag["snap"], freed)
            except Exception:                                # noqa: BLE001
                aim = dict(kind="none", text=_last_line(traceback.format_exc()))
            drag["ghost"].set_caption(aim.get("text", ""),
                                      aim.get("kind") in ("hand", "floor"))

        # --------------------------------------------------------- mouse

        def _local(self, event):
            point = event.position().toPoint() if hasattr(event, "position") \
                else event.pos()
            return point

        def _global(self, event):
            return (event.globalPosition().toPoint()
                    if hasattr(event, "globalPosition") else event.globalPos())

        def mousePressEvent(self, event):
            if self._drag:
                if event.button() == Qt.RightButton:
                    self._end()
                    self._say("cancelled")
                return
            local = self._local(event)
            what = look.hit(self.rects, self.placements, self.cells,
                            local.x(), local.y(), self.cell)
            if event.button() == Qt.RightButton and what and what[0] in ("grid", "item"):
                self._grid_menu(self._global(event))
                return
            if event.button() != Qt.LeftButton:
                return
            if what == ("close",):
                self.close()
                return
            source = self.source_at(local.x(), local.y())
            if source:
                grab = (0, 0)
                if source[0] == "grid":
                    ix, iy = look.item_rect(self.rects, self.placements[source[1]],
                                            self.cells[source[1]], self.cell)[:2]
                    grab = (int((local.x() - ix) // self.cell),
                            int((local.y() - iy) // self.cell))
                self._start(source, self._global(event), grab)
                return
            if what in (("title",), None):
                self._moving = self._global(event) - self.frameGeometry().topLeft()

        def mouseMoveEvent(self, event):
            point = self._global(event)
            if self._moving is not None:
                self.move(point - self._moving)
                return
            if self._drag:
                self._drag["ghost"].follow(point)
                self._caption(point)
                return
            local = self._local(event)
            what = look.hit(self.rects, self.placements, self.cells,
                            local.x(), local.y(), self.cell)
            hover = what if what and what[0] in ("item", "slot", "close") else None
            if hover != self._hover:
                self._hover = hover
                self.update()

        def mouseReleaseEvent(self, event):
            if self._moving is not None:
                self._moving = None
                if self._remember:
                    self.scene.remember_position(self.x(), self.y())
                return
            if self._drag and event.button() == Qt.LeftButton:
                point = self._global(event)
                source = self._drag["source"]
                try:
                    self.drop_at(point.x(), point.y(), source)
                finally:
                    self._end()

        def leaveEvent(self, _event):
            if self._hover is not None:
                self._hover = None
                self.update()

        def keyPressEvent(self, event):
            if event.key() == Qt.Key_Escape:
                if self._drag:
                    self._end()
                    self._say("cancelled")
                else:
                    self.close()
                return
            QtWidgets.QWidget.keyPressEvent(self, event)

        def closeEvent(self, event):
            self._end()
            self.scene.unwatch(self._jobs)
            self._jobs = []
            QtWidgets.QWidget.closeEvent(self, event)

        # --------------------------------------------------------- paint

        def _card(self, p, r, lit=None):
            """A hub card: `card`, rounded; lit "target" is the hub's active
            card (`card_active`, a 2 px accent outline), "refused" a danger
            outline."""
            box = rect_of(r)
            fill = "card_active" if lit == "target" else "card"
            edge = {"target": "accent", "refused": "danger"}.get(lit)
            rounded(p, box, look.RADIUS["card"] * self.k, fill, edge,
                    max(1.0, 2 * self.k) if edge else 1.0)
            return box

        def _well(self, p, box):
            """A field-coloured well inside a card, rounded."""
            rounded(p, box, look.RADIUS["well"] * self.k, "field")
            return box

        def _icon(self, size):
            """The hub's backpack icon in `muted`, cached per size."""
            cached = getattr(self, "_icon_cache", None)
            if cached is None or cached.width() != size:
                try:
                    import maya_hubqt
                    cached = maya_hubqt.pixmap("backpack", look.PALETTE["muted"], size)
                except Exception:                            # noqa: BLE001
                    cached = QtGui.QPixmap(size, size)
                    cached.fill(Qt.transparent)
                self._icon_cache = cached
            return cached

        def paintEvent(self, _event):
            k = self.k
            p = QtGui.QPainter(self)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
            whole = self.rect()
            rounded(p, whole, look.RADIUS["card"] * k, "panel", "line", max(1.0, k))

            # the title: the hub's icon and bold text, left, like a card title
            title = rect_of(self.rects["title"])
            icon = int(18 * k)
            p.drawPixmap(title.left(), title.center().y() - icon // 2, self._icon(icon))
            p.setFont(font(15 * k, bold=True))
            p.setPen(colour("text"))
            p.drawText(title.adjusted(icon + int(8 * k), 0, 0, 0),
                       Qt.AlignLeft | Qt.AlignVCenter, "Inventory")

            close = rect_of(self.rects["close"])
            lit_close = self._hover == ("close",)
            if lit_close:
                rounded(p, close, look.RADIUS["item"] * k, "hover")
            p.setPen(QtGui.QPen(colour("text" if lit_close else "muted"), max(1.2, 1.6 * k)))
            d = int(8 * k)
            p.drawLine(close.left() + d, close.top() + d, close.right() - d, close.bottom() - d)
            p.drawLine(close.right() - d, close.top() + d, close.left() + d, close.bottom() - d)

            p.setFont(font(11.5 * k))
            p.setPen(colour("muted"))
            p.drawText(rect_of(self.rects["name"]), Qt.AlignLeft | Qt.AlignVCenter, self.name)

            dragging = self._drag["source"] if self._drag else None
            label_h = int(20 * k)
            pad = int(6 * k)
            for side in ("R", "L"):
                lit = None
                if dragging:
                    lit = "refused" if dragging == ("slot", side) else "target"
                elif self._hover == ("slot", side):
                    lit = "target"
                box = self._card(p, self.rects["slot_" + side], lit)
                p.setFont(font(11 * k))
                p.setPen(colour("muted"))
                p.drawText(QtCore.QRect(box.left() + pad, box.top(), box.width() - 2 * pad,
                                        label_h), Qt.AlignLeft | Qt.AlignVCenter,
                           SLOT_LABEL[side])
                inner = self._well(p, box.adjusted(pad, label_h, -pad, -pad))
                held = self.holding.get(side)
                if held and held.where in ("hand", "floor") and held.key in self.pixmaps \
                        and dragging != ("slot", side):
                    pix = self.pixmaps[held.key]
                    p.setOpacity(1.0 if held.where == "hand" else 0.45)
                    p.drawPixmap(fitted(pix, inner, int(4 * k)), pix)
                    p.setOpacity(1.0)
                    if held.where == "floor":
                        tag = QtCore.QRect(inner.left() + int(4 * k), inner.top() + int(4 * k),
                                           inner.width() - int(8 * k), int(18 * k))
                        rounded(p, tag, look.RADIUS["item"] * k, "status")
                        p.setFont(font(10.5 * k))
                        p.setPen(colour("status_text"))
                        p.drawText(tag, Qt.AlignCenter, "on the floor")
                elif held and held.weapon and dragging != ("slot", side):
                    p.setFont(font(11 * k))
                    p.setPen(colour("muted"))
                    text = ("follows\n" if held.where == "follows" else "") + held.label
                    p.drawText(inner, Qt.AlignCenter | Qt.TextWordWrap, text)

            grid_rect = rect_of(self.rects["grid"])
            self._card(p, (grid_rect.x() - pad, grid_rect.y() - pad,
                           grid_rect.width() + 2 * pad, grid_rect.height() + 2 * pad),
                       "target" if dragging and dragging[0] == "slot" else None)
            grid = self._well(p, grid_rect)
            p.setPen(QtGui.QPen(colour("line", 90), 1))
            for col in range(1, look.COLS):
                x = grid.left() + int(col * self.cell)
                p.drawLine(x, grid.top() + 2, x, grid.bottom() - 2)
            for row in range(1, look.ROWS):
                y = grid.top() + int(row * self.cell)
                p.drawLine(grid.left() + 2, y, grid.right() - 2, y)
            if self.preview:
                # where the dragged item would land: the hub's ok it fits (or
                # swaps), danger no room (2026-09-29)
                cells, fits = self.preview
                for col, row in cells:
                    if 0 <= col < look.COLS and 0 <= row < look.ROWS:
                        cell = QtCore.QRect(grid.left() + int(col * self.cell) + 1,
                                            grid.top() + int(row * self.cell) + 1,
                                            int(self.cell) - 2, int(self.cell) - 2)
                        rounded(p, cell, look.RADIUS["item"] * k,
                                "ok_tint" if fits else "danger_tint",
                                "ok" if fits else "danger")
            for key, spot in self.placements.items():
                item = rect_of(look.item_rect(self.rects, spot, self.cells[key], self.cell))
                if self._hover == ("item", key) or dragging == ("grid", key):
                    rounded(p, item.adjusted(1, 1, -1, -1), look.RADIUS["item"] * k, "hover")
                pix = self.pixmaps.get(key)
                if pix is not None:
                    p.setOpacity(0.4 if dragging == ("grid", key) else 1.0)
                    p.drawPixmap(fitted(pix, item, int(2 * k)), pix)
                    p.setOpacity(1.0)
                else:
                    p.setFont(font(10 * k))
                    p.setPen(colour("muted"))
                    p.drawText(item, Qt.AlignCenter | Qt.TextWordWrap, key)

            # the status: the hub's message line
            status = rect_of(self.rects["status"])
            rounded(p, status, look.RADIUS["well"] * k, "status")
            p.setFont(font(11.5 * k))
            p.setPen(colour("status_text"))
            p.drawText(status.adjusted(int(10 * k), 0, -int(10 * k), 0),
                       Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap, self.status_text)
            p.end()

    _CLASSES.update(Ghost=Ghost, InventoryWindow=InventoryWindow, qt=q)
    return _CLASSES


# ----------------------------------------------------------------- open

def make_window(scene, parent=None, remember=False):
    """The window over `scene` - the tests' seam."""
    return _classes()["InventoryWindow"](scene, parent, remember)


def _maya_window():
    try:
        import maya.OpenMayaUI as omui
        q = _classes()["qt"]
        pointer = omui.MQtUtil.mainWindow()
        return q.shiboken.wrapInstance(int(pointer), q.QtWidgets.QWidget) \
            if pointer else None
    except Exception:                                        # noqa: BLE001
        return None


def _ours():
    """Every inventory window and ghost alive - an older build's too, found
    by name (a module purged by an update keeps its widgets; trap 102)."""
    q = _classes()["qt"]
    app = q.QtWidgets.QApplication.instance()
    return [w for w in (app.topLevelWidgets() if app else [])
            if w.objectName() in (OBJECT_NAME, GHOST_NAME)]


def live():
    """The open inventory of THIS module, or None."""
    cls = _classes()["InventoryWindow"]
    for widget in _ours():
        if isinstance(widget, cls) and widget.isVisible():
            return widget
    return None


def close_all():
    for widget in _ours():
        try:
            widget.close()
            widget.deleteLater()
        except Exception:                                    # noqa: BLE001
            pass


def show():
    """Open the inventory (or bring the open one up), over Maya."""
    window = live()
    if window is None:
        close_all()
        window = make_window(Scene(), parent=_maya_window(), remember=True)
    window.show()
    window.raise_()
    window.activateWindow()
    window.refresh()
    return window
