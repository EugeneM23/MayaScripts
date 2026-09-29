"""The weapon inventory: a Diablo window whose weapons go onto the character.

2026-09-29, the animator: «кнопка которая будет инвентарь похожий на
инвентарь как в игре diablo, чтобы я оружие переносил из этого инвентаря
прямо на персонажа и оно как вставлялось в руку или выпадало на пол».

A frameless tool window over Maya (look A: bronze, parchment, a gold serif
title), opened by Weapons > Inventory or the hotkey row `window.inventory`:

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

    def font(px, title=False, bold=False):
        f = QtGui.QFont()
        if title:
            f.setFamilies(list(look.TITLE_FONTS))
            f.setCapitalization(QtGui.QFont.SmallCaps)
        f.setPixelSize(max(1, int(round(px))))
        f.setBold(bold)
        return f

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

    class Ghost(QtWidgets.QWidget):
        """The weapon riding the cursor, and the caption naming its target."""

        def __init__(self, pixmap, cells, k):
            QtWidgets.QWidget.__init__(
                self, None, Qt.ToolTip | Qt.FramelessWindowHint
                | Qt.WindowStaysOnTopHint)
            self.setObjectName(GHOST_NAME)
            self.setAttribute(Qt.WA_TranslucentBackground)
            self.setAttribute(Qt.WA_TransparentForMouseEvents)
            self.setAttribute(Qt.WA_ShowWithoutActivating)
            self.pixmap, self.k = pixmap, k
            self.icon_w = int(cells[0] * look.CELL * k)
            self.icon_h = int(cells[1] * look.CELL * k)
            self.text, self.good = "", True
            self._resize()

        def _caption_width(self):
            metrics = QtGui.QFontMetrics(font(12 * self.k))
            return metrics.horizontalAdvance(self.text) + int(16 * self.k) \
                if self.text else 0

        def _resize(self):
            width = max(self.icon_w, self._caption_width())
            self.resize(width, self.icon_h + int(26 * self.k))

        def set_caption(self, text, good):
            if (text, good) != (self.text, self.good):
                self.text, self.good = text, good
                self._resize()
                self.update()

        def follow(self, point):
            """The icon's middle on the cursor's x, the cursor a quarter down
            its height - the grip end under the hand that holds it."""
            self.move(point.x() - self.width() // 2,
                      point.y() - self.icon_h // 4)

        def paintEvent(self, _event):
            p = QtGui.QPainter(self)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
            box = QtCore.QRect((self.width() - self.icon_w) // 2, 0,
                               self.icon_w, self.icon_h)
            p.setOpacity(0.85)
            p.drawPixmap(fitted(self.pixmap, box, int(2 * self.k)), self.pixmap)
            p.setOpacity(1.0)
            if self.text:
                cw = self._caption_width()
                cap = QtCore.QRect((self.width() - cw) // 2,
                                   self.icon_h + int(3 * self.k), cw,
                                   int(21 * self.k))
                p.setPen(QtGui.QPen(colour("frame_hi" if self.good else "invalid"),
                                    max(1.0, self.k)))
                p.setBrush(colour("ground", 235))
                p.drawRoundedRect(cap, 3 * self.k, 3 * self.k)
                p.setFont(font(12 * self.k))
                p.setPen(colour("ghost_text" if self.good else "parchment"))
                p.drawText(cap, Qt.AlignCenter, self.text)
            p.end()

    class InventoryWindow(QtWidgets.QWidget):
        """The inventory. `scene` is `Scene()` in Maya, a fake in the tests."""

        def __init__(self, scene, parent=None, remember=True):
            QtWidgets.QWidget.__init__(self, parent,
                                       Qt.Tool | Qt.FramelessWindowHint)
            self.setObjectName(OBJECT_NAME)
            self.setWindowTitle("Inventory")
            self.scene = scene
            self.k = float(scene.scale() or 1.0)
            self.cell = look.CELL * self.k
            self.rects = look.scaled(look.layout(), self.k)
            _x, _y, width, height = self.rects["window"]
            self.setFixedSize(width, height)
            stored = look.load_cells()
            self.cells = dict((e.key, stored.get(e.key, (1, 3)))
                              for e in catalog.WEAPONS)
            self.placements = look.pack([(e.key, self.cells[e.key])
                                         for e in catalog.WEAPONS])
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

        def drop_at(self, gx, gy, source):
            """The release of a drag from `source` at the global point: the
            spec's table. Public, so a verify can drive it without a mouse."""
            kind, arg = source
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

        def _start(self, source, point):
            key = self._key_of(source)
            pixmap = self.pixmaps.get(key) or QtGui.QPixmap()
            ghost = Ghost(pixmap, self.cells.get(key, (1, 3)), self.k)
            try:
                snap = self.scene.snapshot()
            except Exception:                                # noqa: BLE001
                snap = []
                self._say(_last_line(traceback.format_exc()))
            self._drag = dict(source=source, ghost=ghost, snap=snap)
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
                if what and what[0] == "slot":
                    same = source == ("slot", what[1])
                    drag["ghost"].set_caption(SLOT_LABEL[what[1]], not same)
                elif what and what[0] in ("grid", "item") and source[0] == "slot":
                    drag["ghost"].set_caption("back to the inventory", True)
                else:
                    drag["ghost"].set_caption("", True)
                self.update()
                return
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
            if event.button() != Qt.LeftButton:
                return
            local = self._local(event)
            what = look.hit(self.rects, self.placements, self.cells,
                            local.x(), local.y(), self.cell)
            if what == ("close",):
                self.close()
                return
            source = self.source_at(local.x(), local.y())
            if source:
                self._start(source, self._global(event))
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
            hover = what if what and what[0] in ("item", "slot") else None
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

        def _bevel(self, p, rect, width):
            """Diablo's frame: a dark outer line, bronze, a light inner line."""
            k = self.k
            for name, inset, pen in (("frame_lo", 0, 3), ("frame", 2, 2),
                                     ("frame_hi", 4, 1)):
                p.setPen(QtGui.QPen(colour(name), max(1.0, pen * k * width)))
                p.setBrush(Qt.NoBrush)
                d = int(inset * k)
                p.drawRect(rect.adjusted(d, d, -d - 1, -d - 1))

        def _box(self, p, r, lit=None):
            """A cell-floored box with a bronze border (valid / invalid lit)."""
            box = rect_of(r)
            p.fillRect(box, colour("cell"))
            edge = {"valid": "valid", "invalid": "invalid"}.get(lit, "frame")
            p.setPen(QtGui.QPen(colour(edge), max(1.0, (2 if lit else 1) * self.k)))
            p.setBrush(Qt.NoBrush)
            p.drawRect(box.adjusted(0, 0, -1, -1))
            return box

        def _diamond(self, p, x, y, size):
            path = QtGui.QPainterPath()
            path.moveTo(x, y - size)
            path.lineTo(x + size, y)
            path.lineTo(x, y + size)
            path.lineTo(x - size, y)
            path.closeSubpath()
            p.fillPath(path, colour("frame_hi"))

        def paintEvent(self, _event):
            k = self.k
            p = QtGui.QPainter(self)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
            whole = self.rect()
            p.fillRect(whole, colour("ground"))
            self._bevel(p, whole, 1.0)
            for x, y in ((whole.left(), whole.top()), (whole.right(), whole.top()),
                         (whole.left(), whole.bottom()), (whole.right(), whole.bottom())):
                self._diamond(p, x + (6 if x == whole.left() else -6) * k,
                              y + (6 if y == whole.top() else -6) * k, 4 * k)

            title = rect_of(self.rects["title"])
            p.setFont(font(22 * k, title=True))
            p.setPen(colour("gold"))
            p.drawText(title, Qt.AlignCenter, "Inventory")
            line_y = title.bottom() - int(3 * k)
            p.setPen(QtGui.QPen(colour("frame"), max(1.0, k)))
            p.drawLine(title.left() + int(40 * k), line_y, title.right() - int(40 * k), line_y)

            close = rect_of(self.rects["close"])
            p.setPen(QtGui.QPen(colour("frame_hi"), max(1.5, 2 * k)))
            d = int(7 * k)
            p.drawLine(close.left() + d, close.top() + d, close.right() - d, close.bottom() - d)
            p.drawLine(close.right() - d, close.top() + d, close.left() + d, close.bottom() - d)

            p.setFont(font(13 * k))
            p.setPen(colour("parchment"))
            p.drawText(rect_of(self.rects["name"]), Qt.AlignCenter, self.name)

            dragging = self._drag["source"] if self._drag else None
            for side in ("R", "L"):
                lit = None
                if dragging:
                    lit = "invalid" if dragging == ("slot", side) else "valid"
                elif self._hover == ("slot", side):
                    lit = "valid"
                box = self._box(p, self.rects["slot_" + side], lit)
                label_h = int(18 * k)
                held = self.holding.get(side)
                inner = box.adjusted(0, 0, 0, -label_h)
                if held and held.where in ("hand", "floor") and held.key in self.pixmaps \
                        and dragging != ("slot", side):
                    pix = self.pixmaps[held.key]
                    p.setOpacity(1.0 if held.where == "hand" else 0.45)
                    p.drawPixmap(fitted(pix, inner, int(4 * k)), pix)
                    p.setOpacity(1.0)
                    if held.where == "floor":
                        tag = QtCore.QRect(inner.left() + int(4 * k), inner.top() + int(4 * k),
                                           inner.width() - int(8 * k), int(16 * k))
                        p.fillRect(tag, colour("ground", 220))
                        p.setFont(font(11 * k))
                        p.setPen(colour("parchment"))
                        p.drawText(tag, Qt.AlignCenter, "on the floor")
                elif held and held.weapon and dragging != ("slot", side):
                    p.setFont(font(11 * k))
                    p.setPen(colour("parchment"))
                    text = ("follows\n" if held.where == "follows" else "") + held.label
                    p.drawText(inner, Qt.AlignCenter | Qt.TextWordWrap, text)
                p.setFont(font(11 * k))
                p.setPen(colour("dim"))
                p.drawText(QtCore.QRect(box.left(), box.bottom() - label_h, box.width(), label_h),
                           Qt.AlignCenter, SLOT_LABEL[side])

            grid = self._box(p, self.rects["grid"],
                             "valid" if dragging and dragging[0] == "slot" else None)
            p.setPen(QtGui.QPen(colour("cell_line"), 1))
            for col in range(1, look.COLS):
                x = grid.left() + int(col * self.cell)
                p.drawLine(x, grid.top() + 1, x, grid.bottom() - 1)
            for row in range(1, look.ROWS):
                y = grid.top() + int(row * self.cell)
                p.drawLine(grid.left() + 1, y, grid.right() - 1, y)
            for key, spot in self.placements.items():
                item = rect_of(look.item_rect(self.rects, spot, self.cells[key], self.cell))
                if self._hover == ("item", key) or dragging == ("grid", key):
                    p.fillRect(item.adjusted(1, 1, -1, -1), colour("hover"))
                pix = self.pixmaps.get(key)
                if pix is not None:
                    p.setOpacity(0.5 if dragging == ("grid", key) else 1.0)
                    p.drawPixmap(fitted(pix, item, int(2 * k)), pix)
                    p.setOpacity(1.0)
                else:
                    p.setFont(font(10 * k))
                    p.setPen(colour("parchment"))
                    p.drawText(item, Qt.AlignCenter | Qt.TextWordWrap, key)

            p.setFont(font(12 * k))
            p.setPen(colour("parchment"))
            p.drawText(rect_of(self.rects["status"]),
                       Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap,
                       self.status_text)
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
