"""A message heard while the chat window is shut: a small card at the viewport's bottom-left,
just above the Time Bar (2026-10-20, «При свернутом окне чата сообщения давай показывать в
активном окне маи с левой части экрана над таймслайдером»).

Each card is a frameless Qt.Tool window owned by Maya's main window that never takes the focus.
It unrolls out of its left edge with the accent ring flashing, stays TOAST_STAY_MS (held while the
mouse is over it), and fades to the left. A click opens the chat on that conversation; the cross
dismisses. A newer card comes in at the bottom and the older ones move up; a second message of
the same chat replaces its card. One 16 ms timer for every card, stopped at rest. With ⋮ ->
Interface animations off every card lands and leaves at once. State on sys (trap 111): an
install drops the old module's cards by their object name.
"""
import sys
import time

from . import look
import maya_hubqt as hubqt

NAME = "skeldarChatToast"
_CLASSES = {}


def _q():
    return hubqt.qt()


def _now():
    return time.monotonic() * 1000.0


def _animations():
    try:
        import maya_hubmotion
        return bool(maya_hubmotion.enabled())
    except Exception:                                        # noqa: BLE001
        return True


def _state():
    st = getattr(sys, "_skeldar_chat_toasts", None)
    if st is None or st.get("module") is not sys.modules.get(__name__):
        if st is not None:
            for card in list(st.get("cards", [])):
                _kill(card)
        st = {"module": sys.modules.get(__name__), "cards": [], "timer": None}
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
            self.born = _now()
            self.leaving = None
            self.hover = False
            self.cross_hover = False
            self.stay_left = float(look.TOAST_STAY_MS)
            self.last = self.born
            self.place_from = None
            self.place_at = None
            self.place_to = None
            self.set_text(user, head, text, fresh=False)
            self.resize(int(look.TOAST_W * self.scale), int(look.TOAST_H * self.scale))

        def px(self, n):
            return n * self.scale

        def set_text(self, user, head, text, fresh=True):
            self.user, self.head, self.text = user, head, look.toast_text(text)
            if fresh:
                self.born = _now() - look.TOAST_IN_MS     # no unroll again, only the flash
                self.flash_at = _now()
                self.stay_left = float(look.TOAST_STAY_MS)
            else:
                self.flash_at = self.born
            self.update()

        def cross_rect(self):
            s = self.px(14)
            return QtCore.QRectF(self.width() - self.px(8) - s, self.px(7), s, s)

        # ------------------------------------------------------------ time
        def tick(self, now):
            dt = now - self.last
            self.last = now
            if self.leaving is None and not self.hover:
                self.stay_left -= dt
                if self.stay_left <= 0:
                    self.leave()
            if self.place_to is not None:
                u = min(1.0, (now - self.place_at) / float(look.TOAST_MOVE_MS))
                k = look.ease_out(u, 3)
                (x0, y0), (x1, y1) = self.place_from, self.place_to
                self.move(int(x0 + (x1 - x0) * k), int(y0 + (y1 - y0) * k))
                if u >= 1.0:
                    self.place_to = None
            self.update()
            return self.moving(now)

        def moving(self, now):
            if self.leaving is not None or self.place_to is not None:
                return True
            if now - self.born < look.TOAST_IN_MS or now - self.flash_at < look.TOAST_FLASH_MS:
                return True
            return not self.hover            # the stay counts down

        def gone(self, now):
            return self.leaving is not None and now - self.leaving >= look.TOAST_OUT_MS

        def leave(self):
            if self.leaving is None:
                self.leaving = _now() if _animations() else _now() - look.TOAST_OUT_MS
                self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
                _wake()

        def go_to(self, x, y, animate=True):
            if not animate or not self.isVisible():
                self.place_to = None
                self.move(x, y)
                return
            if (x, y) == (self.x(), self.y()):
                return
            self.place_from = (self.x(), self.y())
            self.place_to = (x, y)
            self.place_at = _now()

        # ------------------------------------------------------------ mouse
        def enterEvent(self, event):                     # noqa: N802
            self.hover = True
            self.update()

        def leaveEvent(self, event):                     # noqa: N802
            self.hover = False
            self.cross_hover = False
            self.stay_left = max(self.stay_left, 1500.0)
            self.last = _now()
            _wake()

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
            now = _now()
            age = (now - self.born) if _animations() else 1e9
            leaving = None if self.leaving is None else now - self.leaving
            reveal, opacity, _flash, slide = look.toast_look(age, leaving)
            flash = 0.0
            if _animations():
                flash = max(0.0, 1.0 - (now - self.flash_at) / float(look.TOAST_FLASH_MS)) ** 1.5
            if opacity <= 0.0:
                return
            p = QtGui.QPainter(self)
            try:
                self._paint(p, reveal, opacity, flash, slide)
            finally:
                p.end()

        def _paint(self, p, reveal, opacity, flash, slide):
            from . import window as W
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            p.setOpacity(opacity)
            pad = self.px(3)
            full = QtCore.QRectF(pad - slide, pad, self.width() - 2 * pad, self.height() - 2 * pad)
            card = QtCore.QRectF(full.x(), full.y(), max(self.px(12), full.width() * reveal),
                                 full.height())
            radius = self.px(8)
            path = QtGui.QPainterPath()
            path.addRoundedRect(card, radius, radius)
            face = W._blend("panel", "card_active", 0.6 if self.hover else 0.0)
            p.fillPath(path, face)
            p.save()
            p.setClipPath(path)
            ink = max(0.0, min(1.0, (reveal - 0.35) / 0.65))
            p.setOpacity(opacity * ink)
            size = self.px(32)
            av = QtCore.QRectF(card.x() + self.px(10), card.center().y() - size / 2.0, size, size)
            held = getattr(sys, "_skeldar_chat", None)
            online = W.is_online(self.user, held.state.online if held is not None else {})
            W.paint_avatar(p, av, self.user, self.scale, online)
            tx = av.right() + self.px(10)
            right = full.right() - self.px(28)
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
            cross = self.cross_rect().translated(-slide, 0)
            p.setPen(QtGui.QPen(W._colour("text" if self.cross_hover else "faint"), self.px(1.4)))
            m = self.px(3.5)
            p.drawLine(QtCore.QPointF(cross.left() + m, cross.top() + m),
                       QtCore.QPointF(cross.right() - m, cross.bottom() - m))
            p.drawLine(QtCore.QPointF(cross.right() - m, cross.top() + m),
                       QtCore.QPointF(cross.left() + m, cross.bottom() - m))
            p.restore()
            p.setOpacity(opacity)
            p.setBrush(QtCore.Qt.NoBrush)
            p.setPen(QtGui.QPen(W._colour("line"), self.px(1)))
            p.drawPath(path)
            if flash > 0.0:
                p.setCompositionMode(QtGui.QPainter.CompositionMode_Plus)
                for i in range(4):
                    k = flash * (1.0 - i / 4.0)
                    pen = QtGui.QPen(W._colour("accent", 0.55 * k), self.px(1.0 + i * 1.2))
                    p.setPen(pen)
                    p.drawRoundedRect(card, radius, radius)

    _CLASSES["card"] = Toast
    return Toast


CALL_NAME = "skeldarChatCallCard"
CALL_H = look.TOAST_H + 34          # logical px: the card plus a row of buttons
HOVER_MS = 110.0
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
            self.level = {name: 0.0 for name, _t in BUTTONS}
            self.over = None
            self.setObjectName(CALL_NAME)
            self.resize(int(look.TOAST_W * self.scale), int(CALL_H * self.scale))

        def set_call(self, call_view, user, head):
            self.kind = call_view.get("kind")
            self.user, self.head = user, head
            self.update()

        # the card never leaves on its own
        def tick(self, now):
            self.stay_left = 1e12
            for name, _t in BUTTONS:
                goal = 1.0 if self.over == name else 0.0
                if not _animations():
                    self.level[name] = goal
                else:
                    step = (now - self.last) / HOVER_MS
                    cur = self.level[name]
                    self.level[name] = min(goal, cur + step) if goal > cur else max(goal, cur - step)
            return super(CallCard, self).tick(now)

        def moving(self, now):
            if self.leaving is not None or self.place_to is not None:
                return True
            if now - self.born < look.TOAST_IN_MS or now - self.flash_at < look.TOAST_FLASH_MS:
                return True
            return any(0.0 < v < 1.0 or (v == 0.0 and n == self.over)
                       for n, v in self.level.items())

        def button_rects(self):
            gap, pad = self.px(6), self.px(13)
            top = self.height() - self.px(3) - self.px(34) + self.px(2)
            h = self.px(26)
            width = (self.width() - 2 * pad - 2 * gap) / 3.0
            return {name: QtCore.QRectF(pad + i * (width + gap), top, width, h)
                    for i, (name, _t) in enumerate(BUTTONS)}

        def press(self, name):
            self.leave()
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
                if not _animations():
                    self.tick(_now())
                _wake()
                self.update()

        def leaveEvent(self, event):                     # noqa: N802
            self.over = None
            super(CallCard, self).leaveEvent(event)

        def mousePressEvent(self, event):                # noqa: N802
            if event.button() == QtCore.Qt.LeftButton:
                name = self._button_at(event.position())
                if name is not None:
                    self.press(name)

        def _paint(self, p, reveal, opacity, flash, slide):
            from . import window as W
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            p.setOpacity(opacity)
            pad = self.px(3)
            full = QtCore.QRectF(pad - slide, pad, self.width() - 2 * pad, self.height() - 2 * pad)
            card = QtCore.QRectF(full.x(), full.y(), max(self.px(12), full.width() * reveal),
                                 full.height())
            radius = self.px(8)
            path = QtGui.QPainterPath()
            path.addRoundedRect(card, radius, radius)
            p.fillPath(path, W._blend("panel", "card_active", 0.6 if self.hover else 0.0))
            p.save()
            p.setClipPath(path)
            ink = max(0.0, min(1.0, (reveal - 0.35) / 0.65))
            p.setOpacity(opacity * ink)
            size = self.px(32)
            top = card.y() + self.px(8)
            av = QtCore.QRectF(card.x() + self.px(10), top + self.px(3), size, size)
            held = getattr(sys, "_skeldar_chat", None)
            online = W.is_online(self.user, held.state.online if held is not None else {})
            W.paint_avatar(p, av, self.user, self.scale, online)
            tx = av.right() + self.px(10)
            right = full.right() - self.px(10)
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
                k = self.level[name]
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
            p.setOpacity(opacity)
            p.setBrush(QtCore.Qt.NoBrush)
            p.setPen(QtGui.QPen(W._colour("accent", 0.7), self.px(1)))
            p.drawPath(path)
            if flash > 0.0:
                p.setCompositionMode(QtGui.QPainter.CompositionMode_Plus)
                for i in range(4):
                    k = flash * (1.0 - i / 4.0)
                    p.setPen(QtGui.QPen(W._colour("accent", 0.55 * k), self.px(1.0 + i * 1.2)))
                    p.drawRoundedRect(card, radius, radius)

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


def _layout(animate=True):
    st = _state()
    cards = [c for c in _alive(st) if c.leaving is None]
    if not cards:
        return
    #  the call cards stand nearest the Time Bar, the message cards above them
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
        card.go_to(int(left), int(bottom), animate and _animations())
        bottom -= look.TOAST_GAP * scale


def _wake():
    st = _state()
    q = _q()
    timer = st.get("timer")
    if timer is None or not hubqt._valid(timer):
        timer = q.QtCore.QTimer()
        timer.setInterval(16)
        timer.timeout.connect(_tick)
        st["timer"] = timer
    if not timer.isActive():
        timer.start()


def _tick():
    st = _state()
    now = _now()
    busy = False
    for card in list(_alive(st)):
        if card.gone(now):
            st["cards"].remove(card)
            _kill(card)
            continue
        busy = card.tick(now) or busy
    if not busy and st.get("timer") is not None:
        st["timer"].stop()


def show(chat_id, user, head, text):
    """A card for a message; the card of the same chat is replaced. Returns the card."""
    st = _state()
    for card in _alive(st):
        if card.chat_id == chat_id and card.leaving is None and not hasattr(card, "call_id"):
            card.set_text(user, head, text)
            st["cards"].remove(card)
            st["cards"].append(card)
            _layout()
            _wake()
            return card
    from . import window
    card = card_class()(chat_id, user, head, text, window._main_window())
    st["cards"].append(card)
    live = [c for c in st["cards"] if c.leaving is None and not hasattr(c, "call_id")]
    for old in live[:-look.TOAST_MAX]:
        old.leave()
    _layout()
    if not _animations():
        card.born = _now() - 1e9
        card.flash_at = card.born
    card.show()
    card.raise_()
    _layout(animate=False)
    _wake()
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
    if not _animations():
        card.born = _now() - 1e9
        card.flash_at = card.born
    card.show()
    card.raise_()
    _layout(animate=False)
    _wake()
    return card


def dismiss_call(call_id):
    for card in call_cards():
        if card.call_id == call_id:
            card.leave()
            if not _animations():
                _tick()


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
