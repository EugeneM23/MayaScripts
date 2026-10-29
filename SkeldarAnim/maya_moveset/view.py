"""The combo trees drawn: a QGraphicsView of cards and wires, the page's look in
the hub's colours. The view talks to Maya through nothing: the card (`panel`)
hands it callbacks for what a press does.

Mouse: a click picks a card, a double click opens its montage (the 1P dot: 1P),
the right button is the status / assignee / open menu, the wheel zooms about the
cursor, a drag on empty space pans.
"""
from PySide6 import QtCore, QtGui, QtWidgets

import maya_hubstyle as hubstyle
from maya_moveset import model as m

T = hubstyle.TOKENS
NAME_H, THUMB_Y, THUMB_W, THUMB_H = 40, 44, 118, 70
DOT_W, DOT_H = 40, 31
TREE_GAP, TITLE_H = 56, 30
ZOOM_MIN, ZOOM_MAX = 0.2, 2.5
GLYPH = {"none": "·", "fwd": "↑", "fwd_right": "↗", "right": "→",
         "back_right": "↘", "back": "↓", "back_left": "↙", "left": "←",
         "fwd_left": "↖"}


def colour(hexed, alpha=255):
    c = QtGui.QColor(hexed)
    c.setAlpha(alpha)
    return c


class Card(QtWidgets.QGraphicsItem):
    """One attack in one tree."""

    def __init__(self, view, node, tree):
        super(Card, self).__init__()
        self.view, self.node, self.tree = view, node, tree
        self.setPos(node.x, node.y)
        self.setAcceptHoverEvents(True)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.hover = False
        self.setToolTip(self._tip())

    def _tip(self):
        node = self.node
        lines = [node.id]
        if node.link == "repeat":
            lines.append("↻ already in this tree above")
        elif node.link == "conv":
            lines.append("↪ opens a tree of its own")
        if node.via:
            dirs = " ".join(GLYPH.get(d, d) for d in node.dirs)
            lines.append("from the card before: {0} {1}".format(node.via, dirs).strip())
        lines.append("double click: open the 3P slot - on the 1P dot: the 1P slot")
        return "\n".join(lines)

    def boundingRect(self):
        return QtCore.QRectF(-6, -6, m.CARD_W + 12, m.CARD_H + 12)

    def dot_rect(self, view):
        x = 8 + THUMB_W + 6
        y = THUMB_Y + (0 if view == "3p" else DOT_H + 8)
        return QtCore.QRectF(x, y, DOT_W, DOT_H)

    def dot_at(self, pos):
        for v in m.VIEWS:
            if self.dot_rect(v).contains(pos):
                return v
        return None

    def paint(self, painter, option, widget=None):
        view, node = self.view, self.node
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        picked = view.picked == node.key
        body = QtCore.QRectF(0, 0, m.CARD_W, m.CARD_H)
        face = T["card_active"] if (self.hover or picked) else T["card"]
        painter.setPen(QtGui.QPen(colour(T["accent"] if picked else T["line"]), 2 if picked else 1))
        painter.setBrush(colour(face))
        painter.drawRoundedRect(body, 8, 8)
        bar = QtCore.QRectF(1, 1, m.CARD_W - 2, 4)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(colour(m.COLOURS.get(node.kind, T["faint"])))
        painter.drawRoundedRect(bar, 2, 2)

        name = view.label(node.id)
        if node.link == "repeat":
            name = "↻ " + name
        elif node.link == "conv":
            name = "↪ " + name
        font = QtGui.QFont(painter.font())
        font.setPixelSize(13)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(colour(T["text"] if not node.link else T["muted"]))
        painter.drawText(QtCore.QRectF(9, 8, m.CARD_W - 18, NAME_H - 6),
                         QtCore.Qt.TextWordWrap | QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop, name)

        thumb = QtCore.QRectF(8, THUMB_Y, THUMB_W, THUMB_H)
        pixmap = view.pixmap(node.id)
        path = QtGui.QPainterPath()
        path.addRoundedRect(thumb, 5, 5)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(colour(T["field"]))
        painter.drawPath(path)
        if pixmap is not None:
            painter.save()
            painter.setClipPath(path)
            scaled = pixmap.size().scaled(thumb.size().toSize(), QtCore.Qt.KeepAspectRatioByExpanding)
            target = QtCore.QRectF(0, 0, scaled.width(), scaled.height())
            target.moveCenter(thumb.center())
            painter.drawPixmap(target, pixmap, QtCore.QRectF(pixmap.rect()))
            painter.restore()
        else:
            painter.setPen(colour(T["faint"]))
            font.setBold(False)
            font.setPixelSize(10)
            painter.setFont(font)
            painter.drawText(thumb, QtCore.Qt.AlignCenter, "no preview")

        for v in m.VIEWS:
            self._paint_dot(painter, v)

        font.setBold(False)
        font.setPixelSize(10)
        painter.setFont(font)
        painter.setPen(colour(T["muted"]))
        foot = self._foot()
        painter.drawText(QtCore.QRectF(9, THUMB_Y + THUMB_H + 8, m.CARD_W - 18, 30),
                         QtCore.Qt.TextWordWrap | QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop, foot)

    def _foot(self):
        node = self.node
        if node.depth == 0:
            return " · ".join(self.tree.titles)
        dirs = " ".join(GLYPH.get(d, d) for d in node.dirs)
        return "{0} {1}".format(node.via, dirs).strip()

    def _paint_dot(self, painter, v):
        view, node = self.view, self.node
        key = m.skey(node.id, v)
        status = view.state["status"].get(key, "")
        tone = next((c for s, _l, c in m.STATUSES if s == status), None)
        rect = self.dot_rect(v)
        painter.setPen(QtGui.QPen(colour(tone or T["line"]), 1.5))
        painter.setBrush(colour(tone, 70) if tone else colour(T["field"]))
        painter.drawRoundedRect(rect, 6, 6)
        font = QtGui.QFont(painter.font())
        font.setPixelSize(11)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(colour(T["text"] if tone else T["muted"]))
        painter.drawText(rect.adjusted(0, 0, 0, -6 if view.state["assignee"].get(key) else 0),
                         QtCore.Qt.AlignCenter, v.upper())
        who = view.state["assignee"].get(key)
        if who:
            badge = view.state["icons"].get(who) or m.initials(who)
            font.setPixelSize(9)
            font.setBold(False)
            painter.setFont(font)
            painter.setPen(colour(T["text2"]))
            painter.drawText(QtCore.QRectF(rect.left(), rect.bottom() - 13, rect.width(), 12),
                             QtCore.Qt.AlignCenter, badge)

    # ---- mouse --------------------------------------------------------------
    def hoverEnterEvent(self, event):
        self.hover = True
        self.update()

    def hoverLeaveEvent(self, event):
        self.hover = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.view.pick(self.node)
            event.accept()
        elif event.button() == QtCore.Qt.RightButton:
            event.accept()
        else:
            event.ignore()

    def mouseDoubleClickEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.view.open(self.node.id, self.dot_at(event.pos()) or "3p")
            event.accept()

    def contextMenuEvent(self, event):
        self.view.pick(self.node)
        self.view.menu(self.node, self.dot_at(event.pos()), event.screenPos())
        event.accept()


class TreeView(QtWidgets.QGraphicsView):
    """The trees. `actions` holds the card's callbacks:
    open(node_id, view), status(node_id, view, status), assign(node_id, view, person),
    picked(node_id)."""

    def __init__(self, parent=None, actions=None):
        super(TreeView, self).__init__(parent)
        self.setObjectName("skeldarMovesetView")
        self.actions = actions or {}
        self.setScene(QtWidgets.QGraphicsScene(self))
        self.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)
        self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
        self.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setBackgroundBrush(colour(T["field"]))
        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.setStyleSheet("QGraphicsView#skeldarMovesetView{border:1px solid %s;border-radius:6px;}"
                           % T["track_edge"])
        self.graph, self.folder = {"nodes": {}, "edges": [], "entries": []}, ""
        #  the weapon whose graph is shown (`model.Weapon`); None keeps the
        #  Longsword's rules, which is what a graph declaring nothing is
        self.weapon = None
        self.state = m.read_state("")
        self.mode, self.root, self.types, self.who = "combos", "", set(), None
        self.picked, self.picked_id = None, ""
        self._pixmaps = {}
        self.cards = []
        self.zoom = 0.62
        self.setTransform(QtGui.QTransform.fromScale(self.zoom, self.zoom))

    # ---- data ---------------------------------------------------------------
    def set_data(self, graph, state, folder, weapon=None):
        self.graph, self.state, self.folder, self.weapon = graph, state, folder, weapon
        self._pixmaps.clear()
        self.rebuild()

    # ---- the weapon's own rules ---------------------------------------------
    def label(self, node_id):
        """The card's name, the weapon's own prefix off it."""
        prefix = self.weapon.prefix if self.weapon else m.LONGSWORD_PREFIX
        return m.label(node_id, self.state["custom"], prefix)

    def thumb_path(self, node_id, view="3p"):
        """The preview in the weapon's own media subfolder, "" when there is none."""
        if not self.folder:
            return ""
        return m.thumbnail(self.folder, node_id, view, self.weapon.media if self.weapon else "")

    def set_state(self, state):
        self.state = state
        for card in self.cards:
            card.update()

    def set_filter(self, root=None, types=None, who="keep", mode=None):
        if root is not None:
            self.root = root
        if types is not None:
            self.types = set(types)
        if who != "keep":
            self.who = who
        if mode is not None:
            self.mode = mode
        self.rebuild()

    def pixmap(self, node_id):
        if node_id in self._pixmaps:
            return self._pixmaps[node_id]
        path = self.thumb_path(node_id)
        pix = QtGui.QPixmap(path) if path else QtGui.QPixmap()
        if not pix.isNull():
            pix = pix.scaledToWidth(THUMB_W * 2, QtCore.Qt.SmoothTransformation)
        self._pixmaps[node_id] = None if pix.isNull() else pix
        return self._pixmaps[node_id]

    def trees(self):
        trees = m.trees(self.graph, self.state, self.mode)
        for tree in trees:
            for node in tree.nodes:
                #  what the graph says the attack is, else its name (the sword's
                #  rule). Set here, so the cards, the wires and the type chips
                #  all read one answer.
                node.kind = m.node_type(self.graph, node.id)
        return trees

    def rebuild(self):
        scene = self.scene()
        scene.clear()
        self.cards = []
        top = 0.0
        width = 0.0
        shown = 0
        for tree in self.trees():
            if self.root and tree.root != self.root:
                continue
            keep = m.kept(tree, self.state, self.types, self.who)
            if keep is not None and not keep:
                continue
            shown += 1
            self._title(tree, top)
            body_top = top + TITLE_H
            for parent, child, lane, lanes in tree.wires:
                self._wire(parent, child, lane, lanes, body_top,
                           keep is None or (parent.key in keep and child.key in keep))
            for node in tree.nodes:
                card = Card(self, node, tree)
                card.moveBy(0, body_top)
                if keep is not None and node.key not in keep:
                    card.setOpacity(0.18)
                scene.addItem(card)
                self.cards.append(card)
                if node.id == self.picked_id and self.picked is None:
                    self.picked = node.key
            width = max(width, tree.width)
            top = body_top + tree.height + TREE_GAP
        if not shown:
            text = scene.addText("No tree matches the filter")
            text.setDefaultTextColor(colour(T["muted"]))
        scene.setSceneRect(QtCore.QRectF(-40, -20, max(width, 400) + 80, max(top, 200) + 40))
        return shown

    def _title(self, tree, top):
        text = self.scene().addSimpleText(self.label(tree.root))
        font = QtGui.QFont(text.font())
        font.setPixelSize(16)
        font.setBold(True)
        text.setFont(font)
        text.setBrush(colour(T["text"]))
        text.setPos(0, top)
        note = self.scene().addSimpleText("  ·  ".join(tree.titles))
        nfont = QtGui.QFont(font)
        nfont.setBold(False)
        nfont.setPixelSize(12)
        note.setFont(nfont)
        note.setBrush(colour(T["muted"]))
        note.setPos(text.boundingRect().width() + 14, top + 3)

    def _wire(self, parent, child, lane, lanes, top, lit):
        kind = child.kind or "chain"
        if kind not in m.COLOURS:
            kind = "chain"
        y_mid = THUMB_Y + THUMB_H / 2.0
        x1 = parent.x + m.CARD_W
        y1 = top + parent.y + y_mid + (lane - (lanes - 1) / 2.0) * 9
        x2 = child.x
        y2 = top + child.y + y_mid
        mid = x1 + 12 + lane * 7
        path = QtGui.QPainterPath(QtCore.QPointF(x1 + 3, y1))
        path.lineTo(mid, y1)
        path.lineTo(mid, y2)
        path.lineTo(x2 - 7, y2)
        pen = QtGui.QPen(colour(m.COLOURS[kind], 255 if lit else 50), 2.4)
        pen.setJoinStyle(QtCore.Qt.RoundJoin)
        self.scene().addPath(path, pen)
        head = QtGui.QPolygonF([QtCore.QPointF(x2 - 1, y2), QtCore.QPointF(x2 - 9, y2 - 5),
                                QtCore.QPointF(x2 - 9, y2 + 5)])
        self.scene().addPolygon(head, QtGui.QPen(QtCore.Qt.NoPen),
                                QtGui.QBrush(colour(m.COLOURS[kind], 255 if lit else 50)))

    # ---- presses ------------------------------------------------------------
    def pick(self, node):
        self.picked, self.picked_id = node.key, node.id
        for card in self.cards:
            card.update()
        fn = self.actions.get("picked")
        if fn:
            fn(node.id)

    def open(self, node_id, view):
        fn = self.actions.get("open")
        if fn:
            fn(node_id, view)

    def menu_rows(self, node, dot):
        """The right button's rows for a card: (label, callable) or None."""
        rows = []
        for v in m.VIEWS:
            slot = m.slot_of(self.graph, node.id, v)
            rows.append(("Open {0} montage ({1})".format(v.upper(), slot or "no slot"),
                         (lambda v=v: self.open(node.id, v)) if slot else None))
        views = [dot] if dot else list(m.VIEWS)
        for v in views:
            rows.append(None)
            now = self.state["status"].get(m.skey(node.id, v), "")
            for status, label, _c in (("", "Not planned", ""),) + m.STATUSES:
                mark = "✓ " if status == now else "    "
                rows.append(("{0}{1}: {2}".format(mark, v.upper(), label),
                             lambda v=v, s=status: self._act("status", node.id, v, s)))
        people = list(self.state["people"])
        if people:
            for v in views:
                rows.append(None)
                now = self.state["assignee"].get(m.skey(node.id, v), "")
                for person in [""] + people:
                    mark = "✓ " if person == now else "    "
                    name = person and "{0} {1}".format(self.state["icons"].get(person, ""), person).strip()
                    rows.append(("{0}{1} → {2}".format(mark, v.upper(), name or "nobody"),
                                 lambda v=v, p=person: self._act("assign", node.id, v, p)))
        return rows

    def _act(self, what, node_id, view, value):
        fn = self.actions.get(what)
        if fn:
            fn(node_id, view, value)

    def menu(self, node, dot, point):
        import maya_hubqt
        maya_hubqt.run_menu(self, point, self.menu_rows(node, dot))

    # ---- view ---------------------------------------------------------------
    def resizeEvent(self, event):
        super(TreeView, self).resizeEvent(event)
        if getattr(self, "_frame_pending", False):
            self.frame()

    def showEvent(self, event):
        super(TreeView, self).showEvent(event)
        if getattr(self, "_frame_pending", False):
            self.frame()

    def wheelEvent(self, event):
        step = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        zoom = max(ZOOM_MIN, min(ZOOM_MAX, self.zoom * step))
        factor = zoom / self.zoom
        self.zoom = zoom
        self.scale(factor, factor)
        event.accept()

    def frame(self):
        """Fit the drawn trees' width into the view."""
        rect = self.scene().itemsBoundingRect()
        if rect.width() <= 0:
            return
        if self.viewport().width() < 120 or not self.isVisible():
            self._frame_pending = True          # framed on the first real size
            return
        self._frame_pending = False
        zoom = max(ZOOM_MIN, min(1.0, (self.viewport().width() - 16) / rect.width()))
        self.setTransform(QtGui.QTransform.fromScale(zoom, zoom))
        self.zoom = zoom
        self.centerOn(rect.left() - 8 / zoom + self.viewport().width() / (2 * zoom),
                      rect.top() + self.viewport().height() / (2 * zoom))


class Keeper(QtCore.QObject):
    """Keeps the view over its placeholder: Maya's layouts place their own
    children, so the view is laid OVER the placeholder and follows its size."""

    def __init__(self, host, view):
        super(Keeper, self).__init__(view)
        self.host, self.view = host, view
        host.installEventFilter(self)
        view.setGeometry(host.rect())

    def eventFilter(self, obj, event):
        if event.type() in (QtCore.QEvent.Resize, QtCore.QEvent.Show):
            self.view.setGeometry(self.host.rect())
            self.view.raise_()
        return False
