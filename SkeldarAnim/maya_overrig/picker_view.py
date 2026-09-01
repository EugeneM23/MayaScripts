"""Qt view for the OverRig picker.

Deliberately knows nothing about Maya: it draws the body map, handles input,
and reports button ids outward through signals. Everything that touches the
scene lives in picker_window.py.
"""

from PySide6 import QtCore, QtGui, QtWidgets

from maya_overrig import bodymap

STATE_NEUTRAL = "neutral"
STATE_SELECTED = "selected"

MODE_REPLACE = "replace"
MODE_ADD = "add"
MODE_TOGGLE = "toggle"

_CLICK_SLOP = 3.0  # a drag shorter than this is treated as a click


def mode_for(modifiers):
    """Map Qt keyboard modifiers to a selection mode."""
    if modifiers & QtCore.Qt.ControlModifier:
        return MODE_TOGGLE
    if modifiers & QtCore.Qt.ShiftModifier:
        return MODE_ADD
    return MODE_REPLACE


BACKGROUND = "#2b2b2b"

_CENTRE = "#8a8378"
_REGION_COLOURS = {
    "root": _CENTRE,
    "spine": _CENTRE,
    "head": _CENTRE,
    "arm_l": "#4a7ea8",
    "leg_l": "#4a7ea8",
    "hand_l": "#3f6885",
    "arm_r": "#a85a4a",
    "leg_r": "#a85a4a",
    "hand_r": "#8a4c40",
}

_DISABLED_FILL = "#3a3a3a"
_DISABLED_LINE = "#4a4a4a"
_HOVER_LINE = "#cfcfcf"
_SELECTED_LINE = "#ffb648"

_CORNER_RADIUS = 3.0


def region_colour(region):
    """Base fill colour for a body region."""
    return QtGui.QColor(_REGION_COLOURS[region])


class ButtonItem(QtWidgets.QGraphicsRectItem):
    """One body-map button. Paints itself from state, availability and hover.

    Takes either kind of bodymap button: FK buttons (with a `joint`) draw as
    rounded rects, IK buttons (with `limb` and `role`) as ellipses -- the
    `kind` hint decides. (Named `kind`, not `shape`: QGraphicsItem.shape() is
    a virtual method, and assigning a string over it breaks hit testing.)
    """

    def __init__(self, button, kind="rect"):
        super(ButtonItem, self).__init__(0.0, 0.0, float(button.w), float(button.h))
        self.button_id = button.id
        self.joint = getattr(button, "joint", None)
        self.region = button.region
        self.kind = kind
        self.state = STATE_NEUTRAL
        self.available = True
        self.view = None
        self._hovered = False

        self.setPos(float(button.x), float(button.y))
        self.setAcceptHoverEvents(True)
        if self.joint is not None:
            self.setToolTip(button.joint)
        else:
            self.setToolTip("{0} IK {1}".format(button.limb, button.role))

    def set_state(self, state):
        if state != self.state:
            self.state = state
            self.update()

    def set_available(self, flag):
        if flag != self.available:
            self.available = flag
            self.setAcceptHoverEvents(flag)
            if not flag:
                self._hovered = False
                self.state = STATE_NEUTRAL
            self.update()

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.update()
        if self.view is not None:
            self.view.hovered.emit(self.button_id)
        super(ButtonItem, self).hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.update()
        if self.view is not None:
            self.view.hovered.emit("")
        super(ButtonItem, self).hoverLeaveEvent(event)

    def _fill(self):
        if not self.available:
            return QtGui.QColor(_DISABLED_FILL)
        colour = region_colour(self.region)
        if self.state == STATE_SELECTED:
            return colour.lighter(118)
        return colour

    def _pen(self):
        if not self.available:
            return QtGui.QPen(QtGui.QColor(_DISABLED_LINE), 1.0)
        if self.state == STATE_SELECTED:
            return QtGui.QPen(QtGui.QColor(_SELECTED_LINE), 2.0)
        if self._hovered:
            return QtGui.QPen(QtGui.QColor(_HOVER_LINE), 1.0)
        return QtGui.QPen(QtGui.QColor(0, 0, 0, 160), 1.0)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)

        base = self._fill()
        gradient = QtGui.QLinearGradient(self.rect().topLeft(),
                                         self.rect().bottomLeft())
        gradient.setColorAt(0.0, base.lighter(108))
        gradient.setColorAt(1.0, base.darker(112))

        painter.setBrush(QtGui.QBrush(gradient))
        painter.setPen(self._pen())
        if self.kind == "ellipse":
            painter.drawEllipse(self.rect())
        else:
            painter.drawRoundedRect(self.rect(), _CORNER_RADIUS, _CORNER_RADIUS)


class PickerView(QtWidgets.QGraphicsView):
    """Renders the body map. Emits button ids; never touches Maya."""

    selection_requested = QtCore.Signal(list, str)
    hovered = QtCore.Signal(str)

    def __init__(self, parent=None):
        super(PickerView, self).__init__(parent)

        scene = QtWidgets.QGraphicsScene(self)
        scene.setSceneRect(0.0, 0.0,
                           float(bodymap.CANVAS_W), float(bodymap.CANVAS_H))
        self.setScene(scene)

        self.setRenderHint(QtGui.QPainter.Antialiasing, True)
        self.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(BACKGROUND)))
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)

        self.items_by_id = {}
        for button in bodymap.BUTTONS:
            item = ButtonItem(button)
            item.view = self
            scene.addItem(item)
            self.items_by_id[button.id] = item
        for button in bodymap.IK_BUTTONS:
            item = ButtonItem(button, kind="ellipse")
            item.view = self
            scene.addItem(item)
            self.items_by_id[button.id] = item

        self.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)
        self.setMouseTracking(True)
        self._press_pos = None

    def ids_in_rect(self, rect):
        """Ids of available buttons intersecting a rect in scene coordinates."""
        found = []
        for item in self.scene().items(rect):
            if isinstance(item, ButtonItem) and item.available:
                found.append(item.button_id)
        return found

    def emit_click(self, button_id, mode):
        """Emit a single-button selection request. Separated out for testing."""
        self.selection_requested.emit([button_id], mode)

    def emit_marquee(self, rect, mode):
        """Emit a rect selection request, unless it covers nothing."""
        ids = self.ids_in_rect(rect)
        if ids:
            self.selection_requested.emit(ids, mode)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MiddleButton:
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
        elif event.button() == QtCore.Qt.LeftButton:
            self._press_pos = event.position().toPoint()
        super(PickerView, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.MiddleButton:
            super(PickerView, self).mouseReleaseEvent(event)
            self.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)
            return

        if event.button() != QtCore.Qt.LeftButton or self._press_pos is None:
            super(PickerView, self).mouseReleaseEvent(event)
            return

        release = event.position().toPoint()
        travelled = release - self._press_pos
        is_click = (abs(travelled.x()) < _CLICK_SLOP
                    and abs(travelled.y()) < _CLICK_SLOP)
        mode = mode_for(event.modifiers())

        if is_click:
            item = self.itemAt(release)
            if isinstance(item, ButtonItem) and item.available:
                self.emit_click(item.button_id, mode)
        else:
            rect = QtCore.QRectF(self.mapToScene(self._press_pos),
                                 self.mapToScene(release)).normalized()
            self.emit_marquee(rect, mode)

        self._press_pos = None
        super(PickerView, self).mouseReleaseEvent(event)

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1.0 / 1.15
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.scale(factor, factor)

    def set_selected(self, ids):
        """Mark exactly these button ids selected; everything else neutral."""
        wanted = set(ids)
        for bid, item in self.items_by_id.items():
            if not item.available:
                continue
            item.set_state(STATE_SELECTED if bid in wanted else STATE_NEUTRAL)

    def set_available(self, ids):
        """Mark these ids interactive; dim every other button."""
        wanted = set(ids)
        for bid, item in self.items_by_id.items():
            item.set_available(bid in wanted)

    def resizeEvent(self, event):
        super(PickerView, self).resizeEvent(event)
        self.fitInView(self.scene().sceneRect(), QtCore.Qt.KeepAspectRatio)
