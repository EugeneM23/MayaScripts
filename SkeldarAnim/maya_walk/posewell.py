"""maya_walk.posewell - Walk Builder's pose well: Pose Library cards are dropped into it (2026-10-15).

The animator: «вместо строчки pose окошко для карточек которые будем перекидывать драгом прямо из библиотеки
поз», then the same day «массив в столбик так что бы я мог закинуть несколько карточек а работала та поза
которая активна тоесть выбрана». A column of cards, each its thumbnail in a square on the left and its name
beside it, the active one lit in the accent; under them a drop row («Drop another pose card here»; with no card
the whole well is the drop strip). The Pose Library's drag asks `well_at(gx, gy)` before it calls a release over
the hub nothing, and hands the card to the well (`take`: added to the column and made active; a card already in
it is made active). A click on a card makes it the active pose, a double click shows it in the library; the
right button offers Use this pose, Show in Pose Library, Remove from the well, Use no pose and Remove all.

Laid over the `cmds` placeholder the card makes (the portraits' `attach` + Keeper pattern), one per scope
(`maya_hubcopy`): the hub's card and every popup copy each have their own, and a release goes to the one under
it. The well keeps its placeholder as tall as its column. Qt is imported lazily (`maya_hubqt.qt()`); everything
the well does to the scene goes through `Scene`, which the tests replace.
Walk Builder has two wells since the same evening: the pose (kind "pose") and the walk cycle (kind "walk":
animation cards, `WalkScene`); one class, its texts by kind (`TEXTS`).
The design: docs/superpowers/specs/2026-10-15-walk-pose-card-well-design.md (its addendum: the column).
"""
import os
import traceback

import maya_hubcopy as hubcopy

OBJECT_NAME = "skeldarWalkPoseWell"
WALK_OBJECT_NAME = "skeldarWalkCycleWell"
HEIGHT = 64              # logical px: the empty well
ROW = 48                 # logical px: a card in the column
GAP = 4                  # logical px: under each card
DROP = 30                # logical px: the drop row under the cards
EMPTY = "Drop a pose card here"
EMPTY_HINT = "from the Pose Library - the walk takes its parts below"
MORE = "Drop another pose card here"
ACTIVE_LINE = "active - the walk takes this pose"
IDLE_LINE = "click to use this pose"
USE = "Use this pose"
SHOW = "Show in Pose Library"
REMOVE = "Remove from the well"
NONE = "Use no pose"
REMOVE_ALL = "Remove all"

#  What a well says, by its kind (2026-10-15: the walk cycles are animation cards in a well of their own)
TEXTS = {
    "pose": {"object": OBJECT_NAME, "empty": EMPTY, "hint": EMPTY_HINT, "more": MORE, "active": ACTIVE_LINE,
             "idle": IDLE_LINE, "use": USE, "none": NONE},
    "walk": {"object": WALK_OBJECT_NAME, "empty": "Drop a walk cycle card here",
             "hint": "an animation card from the Pose Library, or Save", "more": "Drop another walk cycle card here",
             "active": "active - the cycle Pick puts on a skeleton", "idle": "click to use this cycle",
             "use": "Use this cycle", "none": None},
}

#  The wells standing, by the placeholder they are laid over (in the scope that laid them).
_WELLS = {}


def scoped_name(name):
    scope = hubcopy.current()
    return name if scope is None else "{0}_{1}".format(name, scope.tag)


def _key(placeholder):
    return hubcopy.resolve(placeholder)


def _alive(widget):
    try:
        return _classes()["qt"].shiboken.isValid(widget)
    except Exception:                                        # noqa: BLE001
        return False


def _prune():
    for key, well in list(_WELLS.items()):
        if not _alive(well):
            _WELLS.pop(key, None)


def well_height(count):
    """The well's height in logical px for `count` cards (pure)."""
    return HEIGHT if count <= 0 else count * (ROW + GAP) + DROP


def row_index(y, count):
    """The card under a logical height `y` from the well's top, else None - the gaps and the drop row are no
    card (pure)."""
    if y < 0:
        return None
    index = int(y // (ROW + GAP))
    if index >= count or y - index * (ROW + GAP) >= ROW:
        return None
    return index


class Scene(object):
    """What the well asks of Walk Builder and the Pose Library (the tests replace it)."""

    def scale(self):
        import maya.cmds as cmds
        try:
            return float(cmds.mayaDpiSetting(query=True, realScaleValue=True) or 1.0)
        except Exception:                                    # noqa: BLE001
            return 1.0

    def cards(self):
        """Every card in the well, top down: (absolute path, name, thumbnail or "", note or "", active)."""
        from . import panel
        return panel.well_rows()

    def take(self, path):
        from . import panel
        return panel.take_card(path)

    def pick(self, path):
        from . import panel
        return panel.pick_card(path)

    def remove(self, path):
        from . import panel
        return panel.remove_card(path)

    def remove_all(self):
        from . import panel
        return panel.remove_all_cards()

    def clear(self):
        from . import panel
        return panel.clear_card()

    def show(self, path):
        from . import panel
        return panel.show_card(path)


class WalkScene(Scene):
    """The walk well's: the walk cycles' cards (panel.walk_rows ...)."""

    def cards(self):
        from . import panel
        return panel.walk_rows()

    def take(self, path):
        from . import panel
        return panel.take_walk_card(path)

    def pick(self, path):
        from . import panel
        return panel.take_walk_card(path)

    def remove(self, path):
        from . import panel
        return panel.remove_walk_card(path)

    def remove_all(self):
        from . import panel
        return panel.remove_all_walk_cards()

    def clear(self):
        return None


_CLASSES = {}


def _classes():
    if _CLASSES:
        return _CLASSES
    import maya_hubqt
    import maya_hubstyle as hubstyle

    q = maya_hubqt.qt()
    QtCore, QtGui, QtWidgets = q.QtCore, q.QtGui, q.QtWidgets
    Qt = QtCore.Qt

    def colour(name):
        return QtGui.QColor(hubstyle.TOKENS[name])

    def font(px, bold=False):
        f = QtGui.QFont()
        f.setPixelSize(max(1, int(round(px))))
        f.setBold(bold)
        return f

    def local_of(event):
        return event.position().toPoint() if hasattr(event, "position") else event.pos()

    class PoseWell(QtWidgets.QWidget):
        """The column. `scene` is `Scene()` in Maya, a fake in the tests."""

        def __init__(self, scene, parent=None, kind="pose"):
            QtWidgets.QWidget.__init__(self, parent)
            self.kind = kind if kind in TEXTS else "pose"
            self.texts = TEXTS[self.kind]
            self.setObjectName(scoped_name(self.texts["object"]))
            self.scene = scene
            self.k = float(scene.scale() or 1.0)
            self.rows = []           # (path, name, pixmap or None, note, active)
            self.hot = False
            self._host = None
            self.setCursor(Qt.PointingHandCursor)
            self.refresh()

        # ------------------------------------------------------- what it holds

        def _active(self):
            for row in self.rows:
                if row[4]:
                    return row
            return None

        @property
        def path(self):
            """The active card's path, "" with none active."""
            row = self._active()
            return row[0] if row else ""

        @property
        def name(self):
            row = self._active()
            return row[1] if row else ""

        # ------------------------------------------------------ layout

        def height_for(self, width):
            return int(round(well_height(len(self.rows)) * self.k))

        def fit(self, host):
            self.setGeometry(host.rect())
            want = self.height_for(host.width())
            if host.height() != want:
                host.setFixedHeight(want)
                self.setGeometry(host.rect())

        def sizeHint(self):                                  # noqa: N802
            return QtCore.QSize(max(1, self.width()), self.height_for(self.width()))

        def row_rect(self, index):
            top = index * (ROW + GAP) * self.k
            return QtCore.QRectF(0.5, top + 0.5, self.width() - 1.0, ROW * self.k - 1.0)

        def drop_rect(self):
            if not self.rows:
                return QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
            top = len(self.rows) * (ROW + GAP) * self.k
            return QtCore.QRectF(0.5, top + 0.5, self.width() - 1.0, DROP * self.k - 1.0)

        def row_at(self, point):
            """The card row under a local point, else None."""
            return row_index(point.y() / self.k, len(self.rows))

        # ------------------------------------------------------- state

        def refresh(self):
            """What the well holds, read again; the placeholder made as tall as the column."""
            try:
                rows = self.scene.cards()
            except Exception:                                # noqa: BLE001
                traceback.print_exc()
                rows = []
            self.rows = []
            for path, name, thumbnail, note, active in rows:
                pixmap = QtGui.QPixmap(thumbnail) if thumbnail and os.path.isfile(thumbnail) else None
                self.rows.append((path or "", name or "", pixmap, note or "", bool(active)))
            if self._host is not None:
                try:
                    self.fit(self._host)
                except Exception:                            # noqa: BLE001
                    pass
            self.update()

        def set_hot(self, hot):
            """A card dragged over the well: lit."""
            hot = bool(hot)
            if hot != self.hot:
                self.hot = hot
                self.update()

        def take(self, path):
            """A card released over the well: Walk Builder takes it. Answers the line."""
            self.set_hot(False)
            return self._do(self.scene.take, path)

        def pick(self, index):
            """The card at `index` made the active pose; the active one clicked again does nothing."""
            if index is None or not 0 <= index < len(self.rows) or self.rows[index][4]:
                return None
            return self._do(self.scene.pick, self.rows[index][0])

        def context_actions(self, index=None):
            rows = []
            if index is not None and 0 <= index < len(self.rows):
                path, active = self.rows[index][0], self.rows[index][4]
                rows += [(self.texts["use"], None if active else (lambda: self.pick(index))),
                         (SHOW, lambda: self.scene.show(path)),
                         (REMOVE, lambda: self._do(self.scene.remove, path)), None]
            if self.rows:
                if self.texts["none"]:
                    rows.append((self.texts["none"], (lambda: self._do(self.scene.clear)) if self.path else None))
                rows.append((REMOVE_ALL, lambda: self._do(self.scene.remove_all)))
            return rows

        def _do(self, action, *args):
            try:
                text = action(*args)
            except Exception:                                # noqa: BLE001
                traceback.print_exc()
                text = traceback.format_exc().strip().splitlines()[-1]
            self.refresh()
            return text

        # ------------------------------------------------------- input

        def mousePressEvent(self, event):                    # noqa: N802
            point = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()
            index = self.row_at(local_of(event))
            if event.button() == Qt.RightButton:
                maya_hubqt.run_menu(self, point, self.context_actions(index))
            elif event.button() == Qt.LeftButton and index is not None:
                self.pick(index)

        def mouseDoubleClickEvent(self, event):              # noqa: N802
            index = self.row_at(local_of(event))
            if event.button() == Qt.LeftButton and index is not None:
                self.scene.show(self.rows[index][0])

        # ------------------------------------------------------- paint

        def _figure(self, p, square, side):
            """No thumbnail: a head and a body, muted."""
            p.setBrush(colour("line"))
            c = square.center()
            r = side * 0.13
            p.drawEllipse(QtCore.QPointF(c.x(), square.top() + side * 0.3), r, r)
            body = QtCore.QRectF(c.x() - side * 0.22, square.top() + side * 0.48, side * 0.44, side * 0.38)
            p.drawRoundedRect(body, side * 0.12, side * 0.12)

        def _square(self, p, box, pad, pixmap):
            k = self.k
            side = box.height() - 2 * pad
            square = QtCore.QRectF(box.left() + pad, box.top() + pad, side, side)
            p.setPen(Qt.NoPen)
            p.setBrush(colour("card"))
            p.drawRoundedRect(square, 4 * k, 4 * k)
            if pixmap is not None and not pixmap.isNull():
                clip = QtGui.QPainterPath()
                clip.addRoundedRect(square, 4 * k, 4 * k)
                p.save()
                p.setClipPath(clip)
                p.drawPixmap(square.toRect(), pixmap)
                p.restore()
            else:
                self._figure(p, square, side)
            left = square.right() + 8 * k
            return QtCore.QRectF(left, box.top() + pad, box.right() - pad - left, side), side

        def _two_lines(self, p, text, side, top, top_colour, top_px, bold, bottom, bottom_colour):
            k = self.k
            p.setPen(colour(top_colour))
            p.setFont(font(top_px * k, bold=bold))
            metrics = QtGui.QFontMetrics(p.font())
            p.drawText(text.adjusted(0, 0, 0, -side / 2), Qt.AlignLeft | Qt.AlignBottom,
                       metrics.elidedText(top, Qt.ElideRight, int(text.width())))
            p.setPen(colour(bottom_colour))
            p.setFont(font(11 * k))
            metrics = QtGui.QFontMetrics(p.font())
            p.drawText(text.adjusted(0, side / 2 + 2 * k, 0, 0), Qt.AlignLeft | Qt.AlignTop,
                       metrics.elidedText(bottom, Qt.ElideRight, int(text.width())))

        def _paint_row(self, p, box, row):
            k = self.k
            _path, name, pixmap, note, active = row
            p.setPen(QtGui.QPen(colour("accent" if active else "line"), (2 if active else 1) * k))
            p.setBrush(colour("card_active" if active else "field"))
            p.drawRoundedRect(box, 6 * k, 6 * k)
            text, side = self._square(p, box, 5 * k, pixmap)
            self._two_lines(p, text, side, name, "text" if active else "text2", 13, active,
                            note or (self.texts["active"] if active else self.texts["idle"]),
                            "danger" if note else ("accent_text" if active else "muted"))

        def paintEvent(self, _event):                        # noqa: N802
            k = self.k
            p = QtGui.QPainter(self)
            p.setRenderHint(QtGui.QPainter.Antialiasing, True)
            for index, row in enumerate(self.rows):
                self._paint_row(p, self.row_rect(index), row)
            box = self.drop_rect()
            pen = QtGui.QPen(colour("accent" if self.hot else "line"), (2 if self.hot else 1) * k)
            if self.rows and not self.hot:
                pen.setStyle(Qt.DashLine)
            p.setPen(pen)
            p.setBrush(colour("accent_tint" if self.hot else "field"))
            p.drawRoundedRect(box, 6 * k, 6 * k)
            if self.rows:                                    # the drop row: one line, centred
                p.setPen(colour("accent_text" if self.hot else "muted"))
                p.setFont(font(11 * k, bold=self.hot))
                p.drawText(box, Qt.AlignCenter, self.texts["more"])
            else:
                text, side = self._square(p, box, 6 * k, None)
                self._two_lines(p, text, side, self.texts["empty"], "accent_text" if self.hot else "text2", 12,
                                True, self.texts["hint"], "muted")
            p.end()

    import maya_chargrid
    _CLASSES.update(PoseWell=PoseWell, Keeper=maya_chargrid._classes()["Keeper"], qt=q)
    return _CLASSES


def make_well(scene, parent=None, kind="pose"):
    """A well over `scene` - the tests' seam."""
    return _classes()["PoseWell"](scene, parent, kind)


def attach(placeholder, scene=None, kind="pose"):
    """Lay the well over the `cmds` layout `placeholder`, or None where it cannot stand (no Qt, no such
    layout)."""
    import maya_hubqt
    if maya_hubqt.qt() is None:
        return None
    host = maya_hubqt.find(placeholder, layout=True)
    if host is None:
        return None
    _prune()
    classes = _classes()
    scene = hubcopy.bind(scene or (WalkScene() if kind == "walk" else Scene()))   # a release comes from the
    well = classes["PoseWell"](scene, host, kind)                                  # library, outside the scope
    well._host = host
    well._keeper = classes["Keeper"](well, well)
    host.installEventFilter(well._keeper)
    well.fit(host)
    well.show()
    _WELLS[_key(placeholder)] = well
    return well


def live(placeholder):
    """The well standing over `placeholder` in the scope that asks, or None."""
    well = _WELLS.get(_key(placeholder))
    if well is not None and _alive(well):
        return well
    _WELLS.pop(_key(placeholder), None)
    return None


def every():
    """Every well standing (the hub's and the popup copies')."""
    _prune()
    return list(_WELLS.values())


def well_at(gx, gy):
    """The standing, visible well whose rect holds the global point, or None (the Pose Library's drag asks)."""
    if not _WELLS:
        return None
    try:
        q = _classes()["qt"]
    except Exception:                                        # noqa: BLE001
        return None
    point = q.QtCore.QPoint(int(gx), int(gy))
    for well in every():
        try:
            if well.isVisible() and well.rect().contains(well.mapFromGlobal(point)):
                return well
        except Exception:                                    # noqa: BLE001
            continue
    return None


def light(well):
    """Only `well` lit (None: none) - the drag's hover."""
    for each in every():
        try:
            each.set_hot(each is well)
        except Exception:                                    # noqa: BLE001
            pass


def refresh_all():
    for each in every():
        try:
            each.refresh()
        except Exception:                                    # noqa: BLE001
            pass
