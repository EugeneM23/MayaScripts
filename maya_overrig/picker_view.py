"""Qt view for the OverRig picker.

Deliberately knows nothing about Maya: it draws the body map, handles input,
and reports button ids outward through signals. Everything that touches the
scene lives in picker_window.py.
"""

from PySide6 import QtCore, QtGui, QtWidgets

from maya_overrig import bodymap

STATE_NEUTRAL = "neutral"
STATE_SELECTED = "selected"

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
    """One body-map button. Paints itself from state, availability and hover."""

    def __init__(self, button):
        super(ButtonItem, self).__init__(0.0, 0.0, float(button.w), float(button.h))
        self.button_id = button.id
        self.joint = button.joint
        self.region = button.region
        self.state = STATE_NEUTRAL
        self.available = True
        self.view = None
        self._hovered = False

        self.setPos(float(button.x), float(button.y))
        self.setAcceptHoverEvents(True)
        self.setToolTip(button.joint)

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
        painter.drawRoundedRect(self.rect(), _CORNER_RADIUS, _CORNER_RADIUS)


class PickerView(QtWidgets.QGraphicsView):
    """Renders the body map. Emits button ids; never touches Maya."""

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
