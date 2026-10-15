"""maya_walk.posewell - Walk Builder's pose well: a Pose Library card is dropped into it (2026-10-15).

The animator: «вместо строчки pose окошко для карточек которые будем перекидывать драгом прямо из библиотеки
поз». A strip in the card: the card's thumbnail in a square on the left, its name and what it does beside it;
empty, «Drop a pose card here». The Pose Library's drag asks `well_at(gx, gy)` before it calls a release over
the hub nothing, and hands the card to the well (`take`). A click shows the card in the library; the right
button offers Show in Pose Library and Clear.

Laid over the `cmds` placeholder the card makes (the portraits' `attach` + Keeper pattern), one per scope
(`maya_hubcopy`): the hub's card and every popup copy each have their own, and a release goes to the one under
it. Qt is imported lazily (`maya_hubqt.qt()`); everything the well does to the scene goes through `Scene`, which
the tests replace.
The design: docs/superpowers/specs/2026-10-15-walk-pose-card-well-design.md.
"""
import os
import traceback

import maya_hubcopy as hubcopy

OBJECT_NAME = "skeldarWalkPoseWell"
HEIGHT = 64              # logical px: the strip
EMPTY = "Drop a pose card here"
EMPTY_HINT = "from the Pose Library - the walk takes its parts below"
SHOW = "Show in Pose Library"
CLEAR = "Clear"

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


class Scene(object):
    """What the well asks of Walk Builder and the Pose Library (the tests replace it)."""

    def scale(self):
        import maya.cmds as cmds
        try:
            return float(cmds.mayaDpiSetting(query=True, realScaleValue=True) or 1.0)
        except Exception:                                    # noqa: BLE001
            return 1.0

    def card(self):
        """(the card's absolute path or "", its name or "", its thumbnail or "", a note or "")."""
        from . import panel
        return panel.well_state()

    def take(self, path):
        from . import panel
        return panel.take_card(path)

    def clear(self):
        from . import panel
        return panel.clear_card()

    def show(self, path):
        from . import panel
        return panel.show_card(path)


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

    class PoseWell(QtWidgets.QWidget):
        """The strip. `scene` is `Scene()` in Maya, a fake in the tests."""

        def __init__(self, scene, parent=None):
            QtWidgets.QWidget.__init__(self, parent)
            self.setObjectName(scoped_name(OBJECT_NAME))
            self.scene = scene
            self.k = float(scene.scale() or 1.0)
            self.path, self.name, self.note = "", "", ""
            self.pixmap = None
            self.hot = False
            self.setCursor(Qt.PointingHandCursor)
            self.refresh()

        # ------------------------------------------------------ layout

        def height_for(self, width):
            return int(round(HEIGHT * self.k))

        def fit(self, host):
            self.setGeometry(host.rect())
            want = self.height_for(host.width())
            if host.height() != want:
                host.setFixedHeight(want)
                self.setGeometry(host.rect())

        def sizeHint(self):                                  # noqa: N802
            return QtCore.QSize(max(1, self.width()), self.height_for(self.width()))

        # ------------------------------------------------------- state

        def refresh(self):
            """What the card holds, read again."""
            try:
                path, name, thumbnail, note = self.scene.card()
            except Exception:                                # noqa: BLE001
                traceback.print_exc()
                path, name, thumbnail, note = "", "", "", ""
            self.path, self.name, self.note = path or "", name or "", note or ""
            self.pixmap = QtGui.QPixmap(thumbnail) if thumbnail and os.path.isfile(thumbnail) else None
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
            try:
                text = self.scene.take(path)
            except Exception:                                # noqa: BLE001
                traceback.print_exc()
                text = traceback.format_exc().strip().splitlines()[-1]
            self.refresh()
            return text

        def context_actions(self):
            if not self.path:
                return []
            return [(SHOW, lambda: self.scene.show(self.path)), None, (CLEAR, self._clear)]

        def _clear(self):
            self.scene.clear()
            self.refresh()

        # ------------------------------------------------------- input

        def mousePressEvent(self, event):                    # noqa: N802
            point = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()
            if event.button() == Qt.RightButton:
                maya_hubqt.run_menu(self, point, self.context_actions())
            elif event.button() == Qt.LeftButton and self.path:
                self.scene.show(self.path)

        # ------------------------------------------------------- paint

        def paintEvent(self, _event):                        # noqa: N802
            k = self.k
            p = QtGui.QPainter(self)
            p.setRenderHint(QtGui.QPainter.Antialiasing, True)
            box = QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
            p.setPen(QtGui.QPen(colour("accent" if self.hot else "line"), (2 if self.hot else 1) * k))
            p.setBrush(colour("accent_tint" if self.hot else "field"))
            p.drawRoundedRect(box, 6 * k, 6 * k)
            pad = 6 * k
            side = box.height() - 2 * pad
            square = QtCore.QRectF(box.left() + pad, box.top() + pad, side, side)
            p.setPen(Qt.NoPen)
            p.setBrush(colour("card"))
            p.drawRoundedRect(square, 4 * k, 4 * k)
            if self.pixmap is not None and not self.pixmap.isNull():
                path = QtGui.QPainterPath()
                path.addRoundedRect(square, 4 * k, 4 * k)
                p.save()
                p.setClipPath(path)
                p.drawPixmap(square.toRect(), self.pixmap)
                p.restore()
            else:                                            # a figure: a head and a body, muted
                p.setBrush(colour("line"))
                c = square.center()
                r = side * 0.13
                p.drawEllipse(QtCore.QPointF(c.x(), square.top() + side * 0.3), r, r)
                body = QtCore.QRectF(c.x() - side * 0.22, square.top() + side * 0.48, side * 0.44, side * 0.38)
                p.drawRoundedRect(body, side * 0.12, side * 0.12)
            left = square.right() + 8 * k
            text = QtCore.QRectF(left, box.top() + pad, box.right() - pad - left, side)
            if self.path:
                p.setPen(colour("text"))
                p.setFont(font(13 * k, bold=True))
                metrics = QtGui.QFontMetrics(p.font())
                name = metrics.elidedText(self.name, Qt.ElideRight, int(text.width()))
                p.drawText(text.adjusted(0, 0, 0, -side / 2), Qt.AlignLeft | Qt.AlignBottom, name)
                p.setPen(colour("danger" if self.note else "muted"))
                p.setFont(font(11 * k))
                metrics = QtGui.QFontMetrics(p.font())
                line = metrics.elidedText(self.note or "Pose card - drop another to replace it", Qt.ElideRight,
                                          int(text.width()))
                p.drawText(text.adjusted(0, side / 2 + 2 * k, 0, 0), Qt.AlignLeft | Qt.AlignTop, line)
            else:
                p.setPen(colour("accent_text" if self.hot else "text2"))
                p.setFont(font(12 * k, bold=True))
                p.drawText(text.adjusted(0, 0, 0, -side / 2), Qt.AlignLeft | Qt.AlignBottom, EMPTY)
                p.setPen(colour("muted"))
                p.setFont(font(11 * k))
                metrics = QtGui.QFontMetrics(p.font())
                p.drawText(text.adjusted(0, side / 2 + 2 * k, 0, 0), Qt.AlignLeft | Qt.AlignTop,
                           metrics.elidedText(EMPTY_HINT, Qt.ElideRight, int(text.width())))
            p.end()

    import maya_chargrid
    _CLASSES.update(PoseWell=PoseWell, Keeper=maya_chargrid._classes()["Keeper"], qt=q)
    return _CLASSES


def make_well(scene, parent=None):
    """A well over `scene` - the tests' seam."""
    return _classes()["PoseWell"](scene, parent)


def attach(placeholder, scene=None):
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
    scene = hubcopy.bind(scene or Scene())   # a release comes from the library, outside the copy's scope
    well = classes["PoseWell"](scene, host)
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
