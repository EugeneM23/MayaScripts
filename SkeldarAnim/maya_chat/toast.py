"""A message heard while the chat window is shut: a small card at the viewport's bottom-left,
just above the Time Bar (2026-10-20, «При свернутом окне чата сообщения давай показывать в
активном окне маи с левой части экрана над таймслайдером»).

Each card is a frameless Qt.Tool window owned by Maya's main window that never takes the focus.
It stands at its place at once, stays TOAST_STAY_MS (held while the mouse is over it) and goes at
once (2026-11-19: no flight, no fade, no flash). A click opens the chat on that conversation; the
cross dismisses. A newer card comes in at the bottom and the older ones step up; a second message
of the same chat replaces its card. Each card counts its own stay on a single-shot timer. State
on sys (trap 111): an install drops the old module's cards by their object name.
"""
import sys

from . import look
import maya_hubqt as hubqt

NAME = "skeldarChatToast"
_CLASSES = {}


def _q():
    return hubqt.qt()


def _state():
    st = getattr(sys, "_skeldar_chat_toasts", None)
    if st is None or st.get("module") is not sys.modules.get(__name__):
        if st is not None:
            timer = st.get("timer")                 # an older build's motion timer
            if timer is not None:
                try:
                    timer.stop()
                except Exception:                            # noqa: BLE001
                    pass
            for card in list(st.get("cards", [])):
                _kill(card)
        st = {"module": sys.modules.get(__name__), "cards": []}
        sys._skeldar_chat_toasts = st
    return st


def _kill(card):
    try:
        if hubqt._valid(card):
            card.hide()
            card.deleteLater()
    except Exception:                                        # noqa: BLE001
        pass


def _scale():
    from . import window
    return window._scale()


def area():
    """Where the cards stand: the viewport's area ending above the Time Bar's band, else Maya's
    window, else the screen (tests). Global physical px, plus the rects of ours on its left."""
    q = _q()
    obstacles = []
    rect = None
    try:
        import maya_hubedge
        rect = maya_hubedge._viewport_area("left")
        if rect is not None:
            rect = maya_hubedge._above_timebar(rect)
        hub = (getattr(sys, "_skeldar_hubedge", None) or {}).get("edge")
        if hub is not None and hub.alive():
            many = getattr(hub, "visible_rects", None)
            if many is not None:
                obstacles.extend(many())
    except Exception:                                        # noqa: BLE001
        rect = None
    if rect is None:
        from . import window
        main = window._main_window()
        if main is not None:
            p = main.mapToGlobal(main.rect().topLeft())
            rect = (p.x(), p.y(), main.width(), main.height())
        else:
            g = q.QtGui.QGuiApplication.primaryScreen().availableGeometry()
            rect = (g.x(), g.y(), g.width(), g.height())
    return tuple(int(v) for v in rect), obstacles


def card_class():
    if "card" in _CLASSES:
        return _CLASSES["card"]
    q = _q()
    QtCore, QtGui, QtWidgets = q.QtCore, q.QtGui, q.QtWidgets

    class Toast(QtWidgets.QWidget):
        def __init__(self, chat_id, user, head, text, parent=None):
            flags = (QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint
                     | QtCore.Qt.WindowDoesNotAcceptFocus | QtCore.Qt.NoDropShadowWindowHint)
            super(Toast, self).__init__(parent, flags)
            self.setObjectName(NAME)
            self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
            self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating, True)
            self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
            self.setMouseTracking(True)
            self.scale = _scale()
            self.chat_id = chat_id
            self.leaving = None                  # True once it went
            self.hover = False
            self.cross_hover = False
            self.stay_left = float(look.TOAST_STAY_MS)
            self.stay = QtCore.QTimer(self)
            self.stay.setSingleShot(True)
            self.stay.timeout.connect(self.leave)
            self.set_text(user, head, text, fresh=False)
            self.cw = int(look.TOAST_W * self.scale)
            self.resize(self.cw, int(look.TOAST_H * self.scale))

        def px(self, n):
            return n * self.scale

        def set_text(self, user, head, text, fresh=True):
            self.user, self.head, self.text = user, head, look.toast_text(text)
            if fresh:
                self.start_stay(look.TOAST_STAY_MS)
            self.update()

        def cross_rect(self):
            s = self.px(14)
            return QtCore.QRectF(self.cw - self.px(8) - s, self.px(7), s, s)

        # ------------------------------------------------------------ the stay
        def start_stay(self, ms=None):
            """The stay counts down from `ms` (what is left of it when None); never while
            the mouse is over the card."""
            if ms is not None:
                self.stay_left = float(ms)
            if self.hover or self.leaving is not None:
                return
            self.stay.start(int(max(0.0, self.stay_left)))

        def leave(self):
            """The card goes at once and the ones above it step down into its place."""
            if self.leaving is not None:
                return
            self.leaving = True
            self.stay.stop()
            st = _state()
            if self in st["cards"]:
                st["cards"].remove(self)
            _kill(self)
            _layout()

        def go_to(self, x, y):
            if (x, y) != (self.x(), self.y()):
                self.move(x, y)

        # ------------------------------------------------------------ mouse
        def enterEvent(self, event):                     # noqa: N802
            self.hover = True
            if self.stay.isActive():
                self.stay_left = float(self.stay.remainingTime())
                self.stay.stop()
            self.update()

        def leaveEvent(self, event):                     # noqa: N802
            self.hover = False
            self.cross_hover = False
            self.start_stay(max(self.stay_left, 1500.0))
            self.update()

        def mouseMoveEvent(self, event):                 # noqa: N802
            on = self.cross_rect().contains(event.position())
            if on != self.cross_hover:
                self.cross_hover = on
                self.update()

        def mousePressEvent(self, event):                # noqa: N802
            if event.button() == QtCore.Qt.RightButton or self.cross_rect().contains(
                    event.position()):
                self.leave()
                return
            if event.button() == QtCore.Qt.LeftButton:
                self.leave()
                open_chat(self.chat_id)

        # ------------------------------------------------------------ paint
        def paintEvent(self, event):                     # noqa: N802
            p = QtGui.QPainter(self)
            try:
                self._paint(p)
            finally:
                p.end()

        def _paint(self, p):
            from . import window as W
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            pad = self.px(3)
            card = QtCore.QRectF(pad, pad, self.cw - 2 * pad, self.height() - 2 * pad)
            radius = self.px(8)
            path = QtGui.QPainterPath()
            path.addRoundedRect(card, radius, radius)
            face = W._blend("panel", "card_active", 0.6 if self.hover else 0.0)
            p.fillPath(path, face)
            p.save()
            p.setClipPath(path)
            size = self.px(32)
            av = QtCore.QRectF(card.x() + self.px(10), card.center().y() - size / 2.0, size, size)
            held = getattr(sys, "_skeldar_chat", None)
            online = W.is_online(self.user, held.state.online if held is not None else {})
            W.paint_avatar(p, av, self.user, self.scale, online)
            tx = av.right() + self.px(10)
            right = card.right() - self.px(28)
            base = QtGui.QFont(self.font())
            p.setFont(W._font(base, self.px(12), bold=True))
            p.setPen(W._colour("text"))
            fm = QtGui.QFontMetrics(p.font())
            p.drawText(QtCore.QRectF(tx, card.y() + self.px(8), right - tx, self.px(16)),
                       QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
                       fm.elidedText(self.head, QtCore.Qt.ElideRight, int(right - tx)))
            p.setFont(W._font(base, self.px(11)))
            p.setPen(W._colour("muted"))
            from . import emojiart
            emojiart.draw_line(p, QtCore.QRectF(tx, card.y() + self.px(27), right - tx, self.px(16)),
                               self.text, p.font(), p.pen().color())
            cross = self.cross_rect()
            p.setPen(QtGui.QPen(W._colour("text" if self.cross_hover else "faint"), self.px(1.4)))
            m = self.px(3.5)
            p.drawLine(QtCore.QPointF(cross.left() + m, cross.top() + m),
                       QtCore.QPointF(cross.right() - m, cross.bottom() - m))
            p.drawLine(QtCore.QPointF(cross.right() - m, cross.top() + m),
                       QtCore.QPointF(cross.left() + m, cross.bottom() - m))
            p.restore()
            p.setBrush(QtCore.Qt.NoBrush)
            p.setPen(QtGui.QPen(W._colour("line"), self.px(1)))
            p.drawPath(path)

    _CLASSES["card"] = Toast
    return Toast


CALL_NAME = "skeldarChatCallCard"
CALL_H = look.TOAST_H + 34          # logical px: the card plus a row of buttons
BUTTONS = (("voice", "Голос"), ("video", "Видео"), ("decline", "Отклонить"))


def call_card_class():
    if "call" in _CLASSES:
        return _CLASSES["call"]
    q = _q()
    QtCore, QtGui = q.QtCore, q.QtGui
    Toast = card_class()

    class CallCard(Toast):
        """An incoming call: who, what kind, and Голос / Видео / Отклонить. It stays until the
        call is answered, declined or gone (dismiss_call), never on its own timer."""

        def __init__(self, call_view, user, head, parent=None):
            super(CallCard, self).__init__(call_view.get("chat"), user, head, "", parent)
            self.call_id = call_view["id"]
            self.kind = call_view.get("kind")
            self.over = None
            self.setObjectName(CALL_NAME)
            self.cw = int(look.TOAST_W * self.scale)
            self.resize(self.cw, int(CALL_H * self.scale))

        def set_call(self, call_view, user, head):
            self.kind = call_view.get("kind")
            self.user, self.head = user, head
            self.update()

        def start_stay(self, ms=None):
            """The card never leaves on its own."""
            return None

        def button_rects(self):
            gap, pad = self.px(6), self.px(13)
            top = self.height() - self.px(3) - self.px(34) + self.px(2)
            h = self.px(26)
            width = (self.cw - 2 * pad - 2 * gap) / 3.0
            return {name: QtCore.QRectF(pad + i * (width + gap), top, width, h)
                    for i, (name, _t) in enumerate(BUTTONS)}

        def press(self, name):
            self.leave()
            try:
                from . import notify
                notify._gone(self.call_id)         # the ring stops now, not on the server's word
            except Exception:                                # noqa: BLE001
                pass
            if name == "decline":
                decline_call(self.call_id)
            else:
                answer_call(self.call_id, "video" if name == "video" else "audio")

        def _button_at(self, pos):
            for name, rect in self.button_rects().items():
                if rect.contains(pos):
                    return name
            return None

        def mouseMoveEvent(self, event):                 # noqa: N802
            name = self._button_at(event.position())
            if name != self.over:
                self.over = name
                self.update()

        def leaveEvent(self, event):                     # noqa: N802
            self.over = None
            super(CallCard, self).leaveEvent(event)

        def mousePressEvent(self, event):                # noqa: N802
            if event.button() == QtCore.Qt.LeftButton:
                name = self._button_at(event.position())
                if name is not None:
                    self.press(name)

        def _paint(self, p):
            from . import window as W
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            pad = self.px(3)
            card = QtCore.QRectF(pad, pad, self.cw - 2 * pad, self.height() - 2 * pad)
            radius = self.px(8)
            path = QtGui.QPainterPath()
            path.addRoundedRect(card, radius, radius)
            p.fillPath(path, W._blend("panel", "card_active", 0.6 if self.hover else 0.0))
            p.save()
            p.setClipPath(path)
            size = self.px(32)
            top = card.y() + self.px(8)
            av = QtCore.QRectF(card.x() + self.px(10), top + self.px(3), size, size)
            held = getattr(sys, "_skeldar_chat", None)
            online = W.is_online(self.user, held.state.online if held is not None else {})
            W.paint_avatar(p, av, self.user, self.scale, online)
            tx = av.right() + self.px(10)
            right = card.right() - self.px(10)
            base = QtGui.QFont(self.font())
            p.setFont(W._font(base, self.px(12), bold=True))
            p.setPen(W._colour("text"))
            fm = QtGui.QFontMetrics(p.font())
            p.drawText(QtCore.QRectF(tx, top, right - tx, self.px(16)),
                       QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
                       fm.elidedText("Входящий звонок · " + str(self.head), QtCore.Qt.ElideRight,
                                     int(right - tx)))
            p.setFont(W._font(base, self.px(11)))
            p.setPen(W._colour("muted"))
            p.drawText(QtCore.QRectF(tx, top + self.px(19), right - tx, self.px(16)),
                       QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
                       "Видеозвонок" if self.kind == "video" else "Звонок")
            p.setFont(W._font(base, self.px(11), bold=True))
            for name, text in BUTTONS:
                rect = self.button_rects()[name]
                k = 1.0 if self.over == name else 0.0       # the button under the mouse, flat
                accent, danger = W._colour("accent"), W._colour("danger")
                if name == "video":
                    fill = W._blend("accent", "accent_text", 0.25 * k)
                    ink_c, edge = W._colour("panel"), fill
                elif name == "voice":
                    fill = W._blend("card", "accent", 0.18 + 0.2 * k)
                    ink_c, edge = W._colour("text"), accent
                else:
                    fill = W._blend("card", "danger", 0.18 + 0.2 * k)
                    ink_c, edge = W._colour("text"), danger
                p.setBrush(fill)
                p.setPen(QtGui.QPen(edge, self.px(1)))
                p.drawRoundedRect(rect, self.px(6), self.px(6))
                p.setPen(ink_c)
                p.drawText(rect, QtCore.Qt.AlignCenter, text)
            p.restore()
            p.setBrush(QtCore.Qt.NoBrush)
            p.setPen(QtGui.QPen(W._colour("accent", 0.7), self.px(1)))
            p.drawPath(path)

    _CLASSES["call"] = CallCard
    return CallCard


def answer_call(call_id, kind):
    from . import callview, session as _session
    callview.answer(_session.get(), call_id, kind)


def decline_call(call_id):
    from . import session as _session
    try:
        _session.get().decline_call(call_id)
    except Exception:                                        # noqa: BLE001
        pass


# ------------------------------------------------------------------ the stack
def _alive(st):
    st["cards"] = [c for c in st["cards"] if hubqt._valid(c)]
    return st["cards"]


def _layout():
    """Every standing card at its place at once: the newest at the bottom, the call cards
    nearest the Time Bar, the message cards above them."""
    st = _state()
    cards = [c for c in _alive(st) if c.leaving is None]
    if not cards:
        return
    cards = [c for c in cards if not hasattr(c, "call_id")] + \
            [c for c in cards if hasattr(c, "call_id")]
    rect, obstacles = area()
    scale = cards[0].scale
    margin = look.TOAST_MARGIN * scale
    left = look.toast_left(rect, obstacles, margin)
    x, y, w, h = rect
    bottom = y + h - margin
    for card in reversed(cards):                             # the newest at the bottom
        bottom -= card.height()
        card.go_to(int(left), int(bottom))
        bottom -= look.TOAST_GAP * scale


def show(chat_id, user, head, text):
    """A card for a message; the card of the same chat is replaced. Returns the card."""
    st = _state()
    for card in _alive(st):
        if card.chat_id == chat_id and card.leaving is None and not hasattr(card, "call_id"):
            card.set_text(user, head, text)
            st["cards"].remove(card)
            st["cards"].append(card)
            _layout()
            return card
    from . import window
    card = card_class()(chat_id, user, head, text, window._main_window())
    st["cards"].append(card)
    live = [c for c in st["cards"] if c.leaving is None and not hasattr(c, "call_id")]
    for old in live[:-look.TOAST_MAX]:
        old.leave()
    _layout()
    card.show()
    card.raise_()
    card.start_stay()
    return card


def cards():
    return [c for c in _alive(_state()) if c.leaving is None]


def call_cards():
    return [c for c in cards() if hasattr(c, "call_id")]


def show_call(call_view, user, head):
    """A card for an incoming call; a second show of the same call updates it."""
    st = _state()
    for card in call_cards():
        if card.call_id == call_view["id"]:
            card.set_call(call_view, user, head)
            return card
    from . import window
    card = call_card_class()(call_view, user, head, window._main_window())
    st["cards"].append(card)
    _layout()
    card.show()
    card.raise_()
    return card


def dismiss_call(call_id):
    for card in call_cards():
        if card.call_id == call_id:
            card.leave()


def dismiss_chat(chat_id):
    """The chat was opened: its message card goes (a call card stays until answered)."""
    for card in cards():
        if card.chat_id == chat_id and not hasattr(card, "call_id"):
            card.leave()


def clear():
    for card in list(_alive(_state())):
        _kill(card)
    _state()["cards"] = []


def open_chat(chat_id):
    try:
        from . import window
        win = window.show()
        if win is not None and chat_id:
            win.open_chat(chat_id)
    except Exception:                                        # noqa: BLE001
        import traceback
        traceback.print_exc()
