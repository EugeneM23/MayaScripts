"""The weapon inventory: the Weapons card, whose weapons go onto the character.

2026-09-29, the animator: «кнопка которая будет инвентарь похожий на
инвентарь как в игре diablo, чтобы я оружие переносил из этого инвентаря
прямо на персонажа и оно как вставлялось в руку или выпадало на пол». The
grid and the drag are the game's; the look is the hub's own since 2026-09-30
(«дизайн инвентаря все же не в стиле диабло а в стиле нашего интерфейса»).

And since the same evening it is no window: it IS the Weapons card («когда я
открываю вкладку weapon то у меня вместо того что сейчас открывается наш
сетчатый инвентарь с оружием, но не в отдельном окне а как часть нашего
меню»). A Qt panel laid over the card's `cmds` placeholder (the Characters
grid's `attach` + `Keeper`), so the same panel stands in the skinned hub and
the classic one:

- two HAND cards side by side (the right hand on the viewer's left), each a
  WELL showing what the hand holds - held, on the floor (dimmed), or a hand
  riding another weapon - and, left of it, the hand's GRIP as a column laid
  out like Maya's Channel Box («слева от окошка столбик с параметрами так
  как в стандартном интерфейсе маи в channel box»): Translate X/Y/Z, Rotate
  X/Y/Z, a value typed and Enter applies that hand's six (Esc puts back);
- the TILES - the catalog, every weapon always there, one square each
  (the portraits' and the armor's geometry, `maya_charlook`), the icon laid
  across it, the name under it, an «equipped» pill on what the character
  holds (2026-10-01, the evening: «уберем функционал сетчатого инвентаря ...
  перемещать по сетке не нужно. Пусть все будет конссистентно» - the cell
  grid, its rearranging, Sort and the remembered layout are gone);
- the RIGHT BUTTON on a weapon - a tile or a hand card - offers Open scene:
  its catalog file opened as the scene (2026-09-30, `opener`);
- a CLICK picks a weapon, or a hand (the card's Equip / Unequip act on
  them); a DRAG - press, move past Qt's start distance, release - carries
  the icon with a caption naming the target: onto a hand card, back to the
  tiles (a hand's weapon taken off), onto the hand under the cursor in a
  viewport, or the floor under it.

The mouse is ours for the whole drag: a press captures it, so the moves and
the release keep coming here over the viewport, which never sees them.
Everything the panel does to the scene goes through `Scene`, which the tests
replace; everything it looks like is `maya_invlook`'s. Qt is imported lazily
(`maya_hubqt.qt()`), the classes are built on first use.

Specs: docs/superpowers/specs/2026-09-29-weapon-inventory-design.md,
docs/superpowers/specs/2026-09-30-weapons-card-inventory-design.md,
docs/superpowers/specs/2026-10-01-inventory-card-design.md
"""

import os
import traceback

import maya_charlook as charlook
import maya_invlook as look

PLACEHOLDER = "mayaSceneSetupInventory"         # window._INVENTORY
OBJECT_NAME = "skeldarInventoryPanel"
FIELD_NAME = "skeldarChannel"
GHOST_NAME = "skeldarInventoryGhost"
WINDOW_NAME = "skeldarInventory"                # the floating window, before
THROTTLE_MS = 33
SLOT_LABEL = {"R": "Right hand", "L": "Left hand"}
EVENTS = ("SelectionChanged", "Undo", "Redo", "SceneOpened", "NewSceneOpened")
CHANNEL_PX = 9.5           # the channel names' and values' font, logical px
VALUE_SAMPLE = "-179.51"   # the value a field must have room for

#  The panels standing, by the placeholder they are laid over.
_PANELS = {}


def _last_line(error_text):
    lines = [line for line in (error_text or "").strip().splitlines() if line.strip()]
    return lines[-1] if lines else "failed"


def hand_values(grip):
    """A hand's (rotate, translate) as {channel: value} in CHANNELS order."""
    rotate, translate = grip[0], grip[1]
    values = list(translate) + list(rotate)
    return dict(zip(look.CHANNELS, [float(v) for v in values]))


def grip_of(values):
    """{channel: value} back to (rotate, translate)."""
    return (tuple(values[c] for c in ("rx", "ry", "rz")),
            tuple(values[c] for c in ("tx", "ty", "tz")))


# ------------------------------------------------------------------ scene

class Scene(object):
    """The real scene: what the panel asks and what it does to it."""

    def __init__(self, placeholder=PLACEHOLDER):
        self.placeholder = placeholder

    def scale(self):
        import maya.cmds as cmds
        try:
            return float(cmds.mayaDpiSetting(query=True, realScaleValue=True)
                         or 1.0)
        except Exception:                                    # noqa: BLE001
            return 1.0

    def current(self):
        from maya_scenesetup import window
        return window.current_character()

    def holdings(self, root):
        from maya_scenesetup import equip
        return equip.holdings(root)

    def grips(self, root):
        from maya_scenesetup import window
        return window.hand_grips(root)

    def picked(self):
        from maya_scenesetup import window
        return window.picked()

    def select_weapon(self, key):
        from maya_scenesetup import window
        return window.select_weapon(key)

    def select_hand(self, side):
        from maya_scenesetup import window
        return window.select_hand(side)

    def set_grip(self, side, rotate, translate):
        from maya_scenesetup import window
        return window.set_hand_grip(side, rotate, translate)

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

    def open_scene(self, key):
        from maya_scenesetup import window
        return window.open_weapon_scene(key)

    def watch(self, callback):
        """A scriptJob per event, calling `callback` - the hands follow the
        selection, undo and a new scene. Parented to the placeholder, so Maya
        kills them with the card."""
        import maya.cmds as cmds
        jobs = []
        for event in EVENTS:
            try:
                jobs.append(cmds.scriptJob(event=[event, callback],
                                           parent=self.placeholder))
            except Exception:                                # noqa: BLE001
                jobs.append(cmds.scriptJob(event=[event, callback]))
        return jobs

    def unwatch(self, jobs):
        import maya.cmds as cmds
        for job in jobs or []:
            try:
                if cmds.scriptJob(exists=job):
                    cmds.scriptJob(kill=job, force=True)
            except Exception:                                # noqa: BLE001
                pass

    def say(self, text):
        """The Weapons card's line."""
        try:
            from maya_scenesetup import window
            window.say_weapon(text)
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

    #  The drag ghost is the hub's own, shared with the Characters grid.
    Ghost = maya_hubqt.ghost_class()

    def field_sheet(k):
        """The channel fields as the Channel Box draws its values: a dark
        box, the text right-aligned, the accent outline while typed in; an
        ID selector, so it outranks the hub's own QLineEdit rule."""
        t = look.PALETTE
        r, b = max(1, int(3 * k)), max(1, int(k))
        pad = max(1, int(3 * k))
        return (
            "QLineEdit#{n} {{ background: {field}; border: {b}px solid {field};"
            " border-radius: {r}px; padding: 0px {pad}px; color: {text};"
            " selection-background-color: {sel}; }}\n"
            "QLineEdit#{n}:focus {{ border: {b}px solid {accent}; }}\n"
            "QLineEdit#{n}[readOnly=\"true\"] {{ background: transparent;"
            " border: {b}px solid transparent; color: {faint}; }}\n").format(
                n=FIELD_NAME, field=t["field"], text=t["text"],
                sel=t["accent_tint"], accent=t["accent"], faint=t["faint"],
                r=r, b=b, pad=pad)

    class Keeper(QtCore.QObject):
        """Keeps the panel over its placeholder, the placeholder as tall as
        the panel needs for its width (the width is Maya's layout's)."""

        def __init__(self, panel, parent=None):
            QtCore.QObject.__init__(self, parent)
            self._panel = panel

        def eventFilter(self, obj, event):                   # noqa: N802
            if event.type() == QtCore.QEvent.Resize:
                try:
                    self._panel.fit(obj)
                except Exception:                            # noqa: BLE001
                    pass
            return False

    class ChannelField(QtWidgets.QLineEdit):
        """One value of a hand's grip. Enter or leaving the field applies the
        hand's six; Esc puts back what was shown."""

        def __init__(self, panel, side, channel):
            QtWidgets.QLineEdit.__init__(self, panel)
            self.setObjectName(FIELD_NAME)
            self.setProperty("skChannel", "%s_%s" % (side, channel))
            self.side, self.channel = side, channel
            self.shown = "0"
            self.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.setText(self.shown)
            self.editingFinished.connect(lambda: panel._commit(side))

        def show_value(self, value, editable=True):
            self.shown = look.channel_text(value)
            self.setText(self.shown)
            self.setReadOnly(not editable)
            self.setToolTip(self.shown)
            maya_hubqt.repolish(self)

        def keyPressEvent(self, event):                      # noqa: N802
            if event.key() == Qt.Key_Escape:
                self.setText(self.shown)
                self.clearFocus()
                return
            QtWidgets.QLineEdit.keyPressEvent(self, event)

    class InventoryPanel(QtWidgets.QWidget):
        """The card's inventory. `scene` is `Scene()` in Maya, a fake in the
        tests."""

        def __init__(self, scene, parent=None):
            QtWidgets.QWidget.__init__(self, parent)
            self.setObjectName(OBJECT_NAME)
            self.scene = scene
            self.k = float(scene.scale() or 1.0)
            self.keys = [e.key for e in catalog.WEAPONS]
            self.pixmaps, self.turned = {}, {}
            for entry in catalog.WEAPONS:
                path = look.icon_path(entry.key)
                if os.path.isfile(path):
                    pixmap = QtGui.QPixmap(path)
                    self.pixmaps[entry.key] = pixmap
                    # laid across its square tile: an upright 1 x 4 sword
                    # would be a quarter of the tile wide
                    self.turned[entry.key] = pixmap.transformed(
                        QtGui.QTransform().rotate(look.TURN),
                        Qt.SmoothTransformation)
            self.status_text = ""
            self.root, self.holding, self.grips = None, {}, {}
            self.picked_key, self.picked_side = None, "R"
            self.short = {"R": False, "L": False}
            self.field_font = font(CHANNEL_PX * self.k)
            self.setStyleSheet(field_sheet(self.k))
            self.fields = {}
            for side in ("R", "L"):
                for channel in look.CHANNELS:
                    field = ChannelField(self, side, channel)
                    field.setFont(self.field_font)
                    self.fields[(side, channel)] = field
            self._drag = None
            self._press = None
            self._hover = None
            self._clock = QtCore.QElapsedTimer()
            self._clock.start()
            self.setMouseTracking(True)
            self.setFocusPolicy(Qt.ClickFocus)
            self.label_w = {"R": 0, "L": 0}
            self._jobs = scene.watch(self._queue_refresh)
            jobs, watcher = self._jobs, scene
            self.destroyed.connect(lambda *_a: watcher.unwatch(jobs))
            self._place_fields()
            self.refresh()

        # ------------------------------------------------------- layout

        def rects(self, width=None):
            width = self.width() if width is None else width
            return look.scaled(look.panel(width / self.k, len(self.keys)), self.k)

        def height_for(self, width):
            return self.rects(width)["panel"][3]

        def fit(self, host):
            """Over the whole of `host`, and `host` as tall as the panel."""
            self.setGeometry(host.rect())
            want = self.height_for(host.width())
            if host.height() != want:
                host.setFixedHeight(want)
                self.setGeometry(host.rect())
            self._place_fields()          # a hidden widget gets no resize event

        def sizeHint(self):                                  # noqa: N802
            width = max(1, self.width())
            return QtCore.QSize(width, self.height_for(width))

        def resizeEvent(self, event):                        # noqa: N802
            self._place_fields()
            QtWidgets.QWidget.resizeEvent(self, event)

        def _split(self, column_w):
            metrics = QtGui.QFontMetrics(self.field_font)
            nice = max(metrics.horizontalAdvance(look.NICE[c])
                       for c in look.CHANNELS)
            short = max(metrics.horizontalAdvance(c) for c in look.CHANNELS)
            value_min = metrics.horizontalAdvance(VALUE_SAMPLE) + int(6 * self.k)
            return look.split_row(column_w, nice, short, value_min,
                                  int(round(look.ROW_GAP * self.k)))

        def _place_fields(self):
            rects = self.rects()
            gap = int(round(look.ROW_GAP * self.k))
            inset = max(1, int(round(self.k)))
            self.label_w = {}
            for side in ("R", "L"):
                short, label_w, value_w = self._split(rects["column_" + side][2])
                self.short[side], self.label_w[side] = short, label_w
                for channel in look.CHANNELS:
                    x, y, _w, h = rects["row_%s_%s" % (side, channel)]
                    self.fields[(side, channel)].setGeometry(
                        x + label_w + gap, y + inset, max(0, value_w),
                        max(0, h - 2 * inset))

        def field(self, side, channel):
            return self.fields[(side, channel)]

        # -------------------------------------------------------- state

        def refresh(self, force=None):
            """Re-read the scene; a field being typed in keeps its text
            (unless `force` names its hand - just applied)."""
            try:
                self.root = self.scene.current()
                self.holding = self.scene.holdings(self.root) if self.root else {}
                self.grips = self.scene.grips(self.root)
                self.picked_key, self.picked_side = self.scene.picked()
            except Exception:                                # noqa: BLE001
                self.holding = {}
                self._say(_last_line(traceback.format_exc()))
            for side in ("R", "L"):
                grip = self.grips.get(side)
                if not grip:
                    continue
                values = hand_values(grip)
                editable = bool(grip[2]) if len(grip) > 2 else True
                for channel in look.CHANNELS:
                    field = self.fields[(side, channel)]
                    if field.hasFocus() and side != force:
                        continue
                    field.show_value(values[channel], editable)
            self.update()

        def _queue_refresh(self, *_args):
            try:
                if q.shiboken.isValid(self):
                    QtCore.QTimer.singleShot(0, self.refresh)
            except Exception:                                # noqa: BLE001
                pass

        def _say(self, text):
            self.status_text = text or ""
            self.scene.say(self.status_text)
            self.update()
            return self.status_text

        def _act(self, action, force=None):
            try:
                text = action()
            except Exception:                                # noqa: BLE001
                traceback.print_exc()
                text = _last_line(traceback.format_exc())
            self._say(text)
            self.refresh(force)
            return text

        def _label(self, key):
            entry = catalog.by_key(key)
            return entry.label if entry else key

        # ----------------------------------------------------- picking

        def pick_item(self, key):
            """A weapon's tile clicked: the card's picked weapon."""
            if key not in self.keys:
                return self.status_text
            self.picked_key = key
            text = self._act(lambda: self.scene.select_weapon(key))
            return text

        def pick_hand(self, side):
            """A hand card clicked: the card's picked hand."""
            if side not in ("R", "L"):
                return self.status_text
            self.picked_side = side
            return self._act(lambda: self.scene.select_hand(side))

        # ------------------------------------------------------ channels

        def _commit(self, side):
            """A hand's field left or Entered: its six values applied when
            they are numbers and differ from what was shown."""
            typed, shown = {}, {}
            for channel in look.CHANNELS:
                field = self.fields[(side, channel)]
                typed[channel] = look.parse_channel(field.text())
                shown[channel] = look.parse_channel(field.shown)
            if any(v is None for v in typed.values()):
                for channel in look.CHANNELS:
                    field = self.fields[(side, channel)]
                    field.setText(field.shown)
                return self.status_text
            if all(abs(typed[c] - (shown[c] or 0.0)) < 1e-9
                   for c in look.CHANNELS):
                return self.status_text
            rotate, translate = grip_of(typed)
            return self._act(lambda: self.scene.set_grip(side, rotate, translate),
                             force=side)

        def context_actions(self, what):
            """What the right button offers over `what` (a `_hit` answer):
            over a weapon - a tile, or held / on the floor in a hand card -
            Open scene, its catalog file opened as the scene (2026-09-30,
            «по иконке ... оружия ... Open scene»). [] elsewhere."""
            key = None
            if what and what[0] == "tile":
                key = what[1]
            elif what and what[0] == "slot":
                held = self.holding.get(what[1])
                if held and held.key and catalog.by_key(held.key):
                    key = held.key
            actions = []
            if key:
                actions.append((look.OPEN_SCENE, lambda: self._act(
                    lambda: self.scene.open_scene(key))))
            return actions

        def _hit(self, x, y):
            return look.hit(self.rects(), self.keys, x, y, self.k)

        def tile_of(self, key):
            """The physical rect of `key`'s square, or None."""
            if key not in self.keys:
                return None
            return self.rects()["tiles"][self.keys.index(key)]

        def source_at(self, x, y):
            """What a press at local (x, y) would drag, or None."""
            what = self._hit(x, y)
            if what and what[0] == "tile":
                return ("tile", what[1])
            if what and what[0] == "slot":
                held = self.holding.get(what[1])
                if held and held.where in ("hand", "floor") and held.weapon:
                    return ("slot", what[1])
            return None

        def _key_of(self, source):
            if source[0] == "tile":
                return source[1]
            held = self.holding.get(source[1])
            return held.key if held else ""

        # ----------------------------------------------------------- drop

        def drop_at(self, gx, gy, source):
            """The release of a drag from `source` (("tile", key) or ("slot",
            side)) at the global point: the spec's table. Public, so a verify
            can drive it without a mouse."""
            kind, arg = source
            key = self._key_of(source)
            entry = catalog.by_key(key) if kind == "tile" else None
            local = self.mapFromGlobal(QtCore.QPoint(int(gx), int(gy)))
            if self.rect().contains(local):
                what = self._hit(local.x(), local.y())
                if what and what[0] == "slot":
                    side = what[1]
                    if kind == "tile":
                        return self._act(lambda: self.scene.to_hand(self.root, side, entry))
                    if side != arg:
                        return self._act(lambda: self.scene.move(
                            self.root, arg, ("hand", self.root, side)))
                    return self.status_text
                if what and what[0] in ("tiles", "tile") and kind == "slot":
                    return self._act(lambda: self.scene.take_off(self.root, arg))
                return self.status_text        # a tile among the tiles: nothing
            snap = self._drag["snap"] if self._drag else self.scene.snapshot()
            freed = (self.root, arg) if kind == "slot" else None
            aim = self.scene.target(gx, gy, snap, freed)
            if aim.get("kind") == "hand":
                if kind == "tile":
                    return self._act(lambda: self.scene.to_hand(
                        aim["root"], aim["side"], entry))
                if aim["root"] == self.root and aim["side"] == arg:
                    return self._say("already in the %s" % SLOT_LABEL[arg].lower())
                return self._act(lambda: self.scene.move(
                    self.root, arg, ("hand", aim["root"], aim["side"])))
            if aim.get("kind") == "floor":
                if kind == "tile":
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
            pixmap = self.turned.get(key) or QtGui.QPixmap()
            size = int(look.GHOST * self.k)
            ghost = Ghost(pixmap, size, size, self.k, anchor=(0.5, 0.5),
                          name=GHOST_NAME, backdrop="field")
            try:
                snap = self.scene.snapshot()
            except Exception:                                # noqa: BLE001
                snap = []
                self._say(_last_line(traceback.format_exc()))
            self._drag = dict(source=source, ghost=ghost, snap=snap)
            self._press = None
            ghost.follow(point)
            ghost.show()
            try:
                self.grabKeyboard()
            except Exception:                                # noqa: BLE001
                pass
            self._caption(point, force=True)

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
            source = drag["source"]
            local = self.mapFromGlobal(point)
            if self.rect().contains(local):
                what = self._hit(local.x(), local.y())
                if what and what[0] == "slot":
                    same = source == ("slot", what[1])
                    drag["ghost"].set_caption(SLOT_LABEL[what[1]], not same)
                elif what and what[0] in ("tiles", "tile") and source[0] == "slot":
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
            what = self._hit(local.x(), local.y())
            if event.button() == Qt.RightButton:
                self._press = None
                maya_hubqt.run_menu(self, self._global(event),
                                    self.context_actions(what))
                return
            if event.button() != Qt.LeftButton or not what:
                return
            self.setFocus()                  # a field being typed in commits
            point = self._global(event)
            if what[0] == "tile":
                self.pick_item(what[1])
                self._press = (("tile", what[1]), (point.x(), point.y()))
            elif what[0] == "slot":
                self.pick_hand(what[1])
                source = self.source_at(local.x(), local.y())
                if source:
                    self._press = (source, (point.x(), point.y()))

        def mouseMoveEvent(self, event):                     # noqa: N802
            point = self._global(event)
            if self._drag:
                self._drag["ghost"].follow(point)
                self._caption(point)
                return
            if self._press and event.buttons() & Qt.LeftButton:
                source, start = self._press
                moved = abs(point.x() - start[0]) + abs(point.y() - start[1])
                if moved >= QtWidgets.QApplication.startDragDistance():
                    self._start(source, point)
                return
            local = self._local(event)
            what = self._hit(local.x(), local.y())
            hover = what if what and what[0] in ("tile", "slot") else None
            if hover != self._hover:
                self._hover = hover
                self.update()

        def mouseReleaseEvent(self, event):                  # noqa: N802
            if self._drag and event.button() == Qt.LeftButton:
                point = self._global(event)
                source = self._drag["source"]
                try:
                    self.drop_at(point.x(), point.y(), source)
                finally:
                    self._end()
                return
            self._press = None

        def leaveEvent(self, _event):                        # noqa: N802
            if self._hover is not None and not self._drag:
                self._hover = None
                self.update()

        def keyPressEvent(self, event):                      # noqa: N802
            if event.key() == Qt.Key_Escape and self._drag:
                self._end()
                self._say("cancelled")
                return
            QtWidgets.QWidget.keyPressEvent(self, event)

        # --------------------------------------------------------- paint

        def _card(self, p, box, lit=None):
            """A hub card: `card`, rounded; lit "target" / "picked" is the
            hub's active card (`card_active`, a 2 px accent outline), "hover"
            the active fill alone, "refused" a danger outline."""
            fill = "card_active" if lit in ("target", "picked", "hover") else "card"
            edge = {"target": "accent", "picked": "accent",
                    "refused": "danger"}.get(lit)
            rounded(p, box, look.RADIUS["card"] * self.k, fill, edge,
                    max(1.0, 2 * self.k) if edge else 1.0)
            return box

        def _hand_lit(self, side, dragging):
            if dragging:
                return "refused" if dragging == ("slot", side) else "target"
            if side == self.picked_side:
                return "picked"
            if self._hover == ("slot", side):
                return "hover"
            return None

        def _paint_hand(self, p, rects, side, dragging):
            k = self.k
            self._card(p, rect_of(rects["hand_" + side]),
                       self._hand_lit(side, dragging))
            p.setFont(font(11 * k, bold=side == self.picked_side))
            p.setPen(colour("text" if side == self.picked_side else "muted"))
            p.drawText(rect_of(rects["name_" + side]), Qt.AlignLeft | Qt.AlignVCenter,
                       SLOT_LABEL[side])

            grip = self.grips.get(side)
            editable = bool(grip[2]) if grip and len(grip) > 2 else True
            names = look.channel_names(self.short.get(side, False))
            label_w = self.label_w.get(side, 0)
            p.setFont(self.field_font)
            p.setPen(colour("muted" if editable else "faint"))
            for channel in look.CHANNELS:
                x, y, _w, h = rects["row_%s_%s" % (side, channel)]
                p.drawText(QtCore.QRect(x, y, label_w, h),
                           Qt.AlignRight | Qt.AlignVCenter, names[channel])

            well = rect_of(rects["well_" + side])
            rounded(p, well, look.RADIUS["well"] * k, "field")
            held = self.holding.get(side)
            if held and held.where in ("hand", "floor") and held.key in self.pixmaps \
                    and dragging != ("slot", side):
                pix = self.pixmaps[held.key]
                p.setOpacity(1.0 if held.where == "hand" else 0.45)
                p.drawPixmap(fitted(pix, well, int(4 * k)), pix)
                p.setOpacity(1.0)
                if held.where == "floor":
                    tag = QtCore.QRect(well.left() + int(2 * k), well.top() + int(4 * k),
                                       well.width() - int(4 * k), int(18 * k))
                    rounded(p, tag, look.RADIUS["item"] * k, "status")
                    p.setFont(font(9.5 * k))
                    p.setPen(colour("status_text"))
                    p.drawText(tag, Qt.AlignCenter, "floor")
            elif held and held.weapon and dragging != ("slot", side):
                p.setFont(font(10 * k))
                p.setPen(colour("muted"))
                text = ("follows\n" if held.where == "follows" else "") + held.label
                p.drawText(well.adjusted(int(2 * k), 0, -int(2 * k), 0),
                           Qt.AlignCenter | Qt.TextWordWrap, text)

        def _paint_tile(self, p, key, rect, dragging, worn, radius):
            """A weapon's tile as Armor's and the portraits': the square, the
            icon laid across it, the pick lit, an «equipped» pill, the name."""
            k = self.k
            chosen = key == self.picked_key and dragging != ("tile", key)
            lit = (self._hover == ("tile", key) or dragging == ("tile", key)) \
                and not chosen
            box = QtCore.QRectF(*rect)
            shape = QtGui.QPainterPath()
            shape.addRoundedRect(box, radius, radius)
            p.fillPath(shape, colour("card_active" if chosen else
                                     ("hover" if lit else "field")))
            pixmap = self.turned.get(key)
            if pixmap is not None and not pixmap.isNull():
                p.setOpacity(0.4 if dragging == ("tile", key) else 1.0)
                p.drawPixmap(fitted(pixmap, box.toRect(), int(4 * k)), pixmap)
                p.setOpacity(1.0)
            else:
                p.setFont(font(10 * k))
                p.setPen(colour("muted"))
                p.drawText(box, Qt.AlignCenter | Qt.TextWordWrap, key)
            width = max(1.5, 2 * k) if chosen else max(1.0, k)
            edge = "accent" if chosen else ("text2" if lit else "line")
            p.setPen(QtGui.QPen(colour(edge), width))
            p.setBrush(Qt.NoBrush)
            half = width / 2.0
            p.drawRoundedRect(box.adjusted(half, half, -half, -half), radius, radius)
            if worn:
                pad = int(4 * k)
                tag = QtCore.QRectF(box.left() + pad, box.bottom() - pad - int(16 * k),
                                    box.width() - 2 * pad, int(16 * k))
                p.setPen(Qt.NoPen)
                p.setBrush(colour("ok_tint"))
                p.drawRoundedRect(tag, 4 * k, 4 * k)
                p.setFont(font(10.5 * k, bold=True))
                p.setPen(colour("ok"))
                p.drawText(tag, Qt.AlignCenter, look.WORN_TEXT)
            nx, ny, nw, nh = charlook.name_rect(rect, k)
            name_font = font(11.5 * k, bold=chosen)
            p.setFont(name_font)
            p.setPen(colour("text" if chosen else "text2"))
            text = QtGui.QFontMetrics(name_font).elidedText(
                self._label(key), Qt.ElideRight, int(nw))
            p.drawText(QtCore.QRect(int(nx), int(ny), int(nw), int(nh)),
                       Qt.AlignHCenter | Qt.AlignVCenter, text)

        def paintEvent(self, _event):                        # noqa: N802
            k = self.k
            p = QtGui.QPainter(self)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
            rects = self.rects()
            dragging = self._drag["source"] if self._drag else None
            for side in ("R", "L"):
                self._paint_hand(p, rects, side, dragging)

            if dragging and dragging[0] == "slot":
                # a hand's weapon over the tiles goes back to the inventory
                self._card(p, rect_of(rects["tilesarea"]).adjusted(
                    -int(2 * k), -int(2 * k), int(2 * k), int(2 * k)), "target")
            worn = look.worn(self.holding)
            radius = look.RADIUS["well"] * k
            for key, rect in zip(self.keys, rects["tiles"]):
                self._paint_tile(p, key, rect, dragging, key in worn, radius)
            p.end()

    _CLASSES.update(Ghost=Ghost, Keeper=Keeper, ChannelField=ChannelField,
                    InventoryPanel=InventoryPanel, qt=q)
    return _CLASSES


# ----------------------------------------------------------------- open

def make_panel(scene, parent=None):
    """A panel over `scene` - the tests' seam."""
    return _classes()["InventoryPanel"](scene, parent)


def _windows():
    """An older build's floating inventory windows and ghosts, found by name
    (a module purged by an update keeps its widgets; trap 102)."""
    import maya_hubqt
    q = maya_hubqt.qt()
    if q is None:
        return []
    app = q.QtWidgets.QApplication.instance()
    return [w for w in (app.topLevelWidgets() if app else [])
            if w.objectName() in (WINDOW_NAME, GHOST_NAME)]


def close_windows():
    """Close the floating inventory an older build left open - it is the
    Weapons card now."""
    for widget in _windows():
        try:
            widget.close()
            widget.deleteLater()
        except Exception:                                    # noqa: BLE001
            pass


def attach(placeholder=PLACEHOLDER, scene=None):
    """Lay a panel over the `cmds` layout `placeholder`, or None where it
    cannot stand (no Qt, no such layout). Maya's layouts place their own
    children, so the panel is laid OVER the placeholder (the hub's `_spread`
    pattern) and the placeholder is given the panel's height for its width
    on every resize."""
    import maya_hubqt
    if maya_hubqt.qt() is None:
        return None
    host = maya_hubqt.find(placeholder, layout=True)
    if host is None:
        return None
    close_windows()
    classes = _classes()
    panel = classes["InventoryPanel"](scene or Scene(placeholder), host)
    panel._host = host                   # the wrapper lives as long as the panel
    panel._keeper = classes["Keeper"](panel, panel)
    host.installEventFilter(panel._keeper)
    panel.fit(host)
    panel.show()
    _PANELS[placeholder] = panel
    return panel


def live(placeholder=PLACEHOLDER):
    """The panel standing over `placeholder`, or None."""
    panel = _PANELS.get(placeholder)
    if panel is None:
        return None
    try:
        q = _classes()["qt"]
        if q.shiboken.isValid(panel):
            return panel
    except Exception:                                        # noqa: BLE001
        pass
    _PANELS.pop(placeholder, None)
    return None


def show():
    """Open the hub on the Weapons card - the inventory lives there."""
    close_windows()
    import maya_hub
    return maya_hub.show("weapons")
