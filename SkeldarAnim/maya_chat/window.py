"""The chat window (plan docs/superpowers/plans/2026-10-20-chat-window.md, spec
docs/superpowers/specs/2026-10-19-chat-messenger-design.md "The window").

A floating hub window in look B: drawn by our own widgets and QPainter from the session's
state, listening to it. The window never talks to the server but through the session
(and its `api` for the group presses). No modal dialog but the file pickers (a picture, a file
to send). A message may carry a file (2026-10-22, spec 2026-10-22-chat-files-design.md): its card
opens, imports, saves or stashes it, a paperclip sends a scene or a file, and files from Explorer,
Stash or Shared dropped on the window go into the open chat.
"""
import math
import sys
import os
import time
import traceback

import maya_hubmotion as hubmotion
import maya_hubqt as hubqt
import maya_hubstyle as hubstyle
import maya_hubwindow as hubwindow

from . import look
from . import records
from . import calls as _calls

POS_VAR = "skeldarChatWindowPos"
SIZE_VAR = "skeldarChatWindowSize"
ROOT_NAME = "skeldarChatWindow"
TICK_MS = 16
ENTER_MS = 260        # a new message comes up from below, a little overshoot
FOLD_MS = 200         # a deleted one folds
SENT_FLASH_MS = 120   # a message sent (its ack) flashes
POP_MS = 200          # a count pops when it changes
HOVER_MS = 110
TYPING_FRAME_S = 3.0
FILE_CARD = 46        # a file message's card (2026-10-22)
FILE_ROW = 24         # its buttons / its progress bar
FILE_WIDTH = 250      # the least a file bubble takes
FILE_ACTIONS = {"ready": (("open", "Open"), ("import", "Import"), ("more", u"\u22ef")),
                "upload": (("cancel", u"Отмена"),),
                "failed": (("cancel", u"Отмена"),),
                "download": (), "expired": (), "card": (),
                "image": (("view", u"Открыть"), ("save", u"Сохранить как…"))}
CARD_HINT = u"перетащите во вьюпорт или в библиотеку поз"
FILE_FILTER = "Maya scenes, FBX and pictures (*.ma *.mb *.fbx *.png *.jpg *.jpeg)"
PLAY_MS = 33          # an animation preview's frame while it plays under the mouse
BIG_EMOJI = 64        # an emoji sent alone (1-3 of them), logical px (2026-10-22)
PILL_EMOJI = 18       # a reaction's picture in its pill
PLAY_CAP_MS = 5000    # an emoji's play is dropped past this, painted or not (Noto's ~2.2 s)

_CLASSES = {}
_VARS = {}            # optionVars where there is no Maya (tests)


# ------------------------------------------------------------------ helpers

def _q():
    return hubqt.qt()


def _cmds():
    try:
        from maya import cmds
        cmds.optionVar(exists=POS_VAR)
        return cmds
    except Exception:                                        # noqa: BLE001
        return None


def get_var(name):
    cmds = _cmds()
    if cmds is not None:
        try:
            if cmds.optionVar(exists=name):
                return cmds.optionVar(query=name)
            return None
        except Exception:                                    # noqa: BLE001
            pass
    return _VARS.get(name)


def set_var(name, value):
    cmds = _cmds()
    if cmds is not None:
        try:
            cmds.optionVar(stringValue=(name, value))
            return
        except Exception:                                    # noqa: BLE001
            pass
    _VARS[name] = value


def _pair(text):
    try:
        a, b = [int(float(v)) for v in str(text).split(",")]
        return a, b
    except Exception:                                        # noqa: BLE001
        return None


def _scale():
    try:
        from maya import cmds
        return float(cmds.mayaDpiSetting(query=True, realScaleValue=True) or 1.0)
    except Exception:                                        # noqa: BLE001
        return 1.0


def _main_window():
    try:
        import maya_hubpop
        return maya_hubpop._main_window()
    except Exception:                                        # noqa: BLE001
        return None


def _now_ms():
    return int(time.time() * 1000)


def _colour(name_or_hex, alpha=1.0):
    q = _q()
    c = q.QtGui.QColor(hubstyle.TOKENS.get(name_or_hex, name_or_hex))
    c.setAlphaF(max(0.0, min(1.0, alpha)))
    return c


def _blend(a, b, k):
    q = _q()
    ca, cb = q.QtGui.QColor(hubstyle.TOKENS.get(a, a)), q.QtGui.QColor(hubstyle.TOKENS.get(b, b))
    k = max(0.0, min(1.0, k))
    return q.QtGui.QColor(int(ca.red() + (cb.red() - ca.red()) * k),
                          int(ca.green() + (cb.green() - ca.green()) * k),
                          int(ca.blue() + (cb.blue() - ca.blue()) * k))


def back_out(u):
    u = max(0.0, min(1.0, u))
    c = 1.70158
    return 1 + (c + 1) * (u - 1) ** 3 + c * (u - 1) ** 2


def pop_scale(age_ms):
    """A count's pop: 1 -> 1.25 -> 1 over POP_MS."""
    if age_ms < 0 or age_ms >= POP_MS:
        return 1.0
    import math
    return 1.0 + 0.25 * math.sin(math.pi * age_ms / float(POP_MS))


def _picture(user, rect):
    """A user's round picture for `rect`, or None (none set, not fetched yet, no cache)."""
    try:
        from . import avatars
        held = getattr(sys, avatars._ATTR, None)
        if held is None:
            return None
        return held.pixmap(user, int(round(rect.width() * 2)))
    except Exception:                                        # noqa: BLE001
        return None


def is_online(user, online):
    """Live from the session's presence, the user's own `online` the fallback."""
    user = user or {}
    seen = (online or {}).get(user.get("id"), {})
    return bool(seen.get("online", user.get("online")))


def paint_avatar(p, rect, user, scale, online=None, ring="panel"):
    """A user's circle: their picture, else their colour and initials. `online` True draws the
    green dot at the bottom-right (ringed in `ring`: what the circle stands on)."""
    q = _q()
    p.save()
    p.setRenderHint(q.QtGui.QPainter.Antialiasing)
    p.setRenderHint(q.QtGui.QPainter.SmoothPixmapTransform)
    p.setPen(q.QtCore.Qt.NoPen)
    picture = _picture(user, rect)
    if picture is not None:
        p.drawPixmap(rect, picture, q.QtCore.QRectF(picture.rect()))
    else:
        p.setBrush(q.QtGui.QColor(look.user_colour((user or {}).get("id"))))
        p.drawEllipse(rect)
        font = q.QtGui.QFont(p.font())
        font.setBold(True)
        font.setPixelSize(max(6, int(rect.height() * 0.38)))
        p.setFont(font)
        p.setPen(q.QtGui.QColor("#ffffff"))
        p.drawText(rect, q.QtCore.Qt.AlignCenter, look.initials(user))
    if online:
        d = max(5.0, rect.width() * 0.3)
        width = max(1.0, scale * 2.0)
        dot = q.QtCore.QRectF(rect.right() - d + width * 0.3, rect.bottom() - d + width * 0.3, d, d)
        p.setPen(q.QtCore.Qt.NoPen)
        p.setBrush(q.QtGui.QColor(hubstyle.TOKENS.get(ring, ring)))
        p.drawEllipse(dot)
        p.setBrush(q.QtGui.QColor(hubstyle.TOKENS["ok"]))
        p.drawEllipse(dot.adjusted(width, width, -width, -width))
    p.restore()


def avatar_widget_class():
    """AvatarDot(window, user, side): a painted avatar for a widget row (Members, New chat,
    the settings' preview, the chat header)."""
    if "avatar" not in _CLASSES:
        q = _q()
        QtCore, QtGui, QtWidgets = q.QtCore, q.QtGui, q.QtWidgets

        class AvatarDot(QtWidgets.QWidget):
            def __init__(self, win, user, side, dot=True, parent=None):
                super(AvatarDot, self).__init__(parent)
                self.win, self.user, self.dot = win, user, dot
                self.clickable = True       # a person's avatar opens their card (2026-10-22)
                self.setFixedSize(int(side), int(side))
                self.setCursor(QtCore.Qt.PointingHandCursor)

            def mousePressEvent(self, event):              # noqa: N802
                if self.clickable and event.button() == QtCore.Qt.LeftButton \
                        and self.win.show_profile(self.user):
                    return
                super(AvatarDot, self).mousePressEvent(event)

            def set_user(self, user, dot=True):
                self.user, self.dot = user, dot
                self.update()

            def paintEvent(self, event):                   # noqa: N802
                p = QtGui.QPainter(self)
                try:
                    online = self.dot and is_online(self.user, self.win.session.state.online)
                    paint_avatar(p, QtCore.QRectF(0.5, 0.5, self.width() - 1, self.height() - 1),
                                 self.user, self.win.scale, online)
                except Exception:                            # noqa: BLE001
                    traceback.print_exc()
                finally:
                    p.end()

        _CLASSES["avatar"] = AvatarDot
    return _CLASSES["avatar"]


def px_of(widget, n):
    return hubstyle.px(n, widget.win.scale)


def paint_ticks(p, right, mid_y, tick, colour, scale):
    """A message's tick drawn ending at `right`, centred on `mid_y` (look A, 2026-10-22):
    ✓ sent, ✓✓ read, a clock while it goes, ! failed. Returns the width it took."""
    q = _q()
    QtCore, QtGui = q.QtCore, q.QtGui
    width = tick_width(tick, scale)
    if not width:
        return 0
    left = right - width
    p.save()
    p.setRenderHint(QtGui.QPainter.Antialiasing)
    pen = QtGui.QPen(QtGui.QColor(colour), max(1.1, 1.45 * scale))
    pen.setCapStyle(QtCore.Qt.RoundCap)
    pen.setJoinStyle(QtCore.Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(QtCore.Qt.NoBrush)
    path = QtGui.QPainterPath()
    if tick == "failed":
        f = QtGui.QFont(p.font())
        f.setBold(True)
        p.setFont(f)
        p.drawText(QtCore.QRectF(left, mid_y - width, width, 2 * width), QtCore.Qt.AlignCenter, "!")
        p.restore()
        return width
    if tick == "clock":
        k = width / 16.0
        p.drawEllipse(QtCore.QPointF(left + 8 * k, mid_y), 6.5 * k, 6.5 * k)
        path.moveTo(left + 8 * k, mid_y - 3.5 * k)
        path.lineTo(left + 8 * k, mid_y)
        path.lineTo(left + 10.5 * k, mid_y + 2 * k)
    elif tick == "sent":            # Tabler's check: M5 12 l5 5 L20 7
        k = width / 15.0
        path.moveTo(left, mid_y)
        path.lineTo(left + 5 * k, mid_y + 5 * k)
        path.lineTo(left + 15 * k, mid_y - 5 * k)
    else:                           # read: M7 12l5 5L22 7 M2 12l5 5 m5-5l5-5
        k = width / 20.0
        x = lambda u: left + (u - 2) * k                    # noqa: E731
        y = lambda v: mid_y + (v - 12) * k                  # noqa: E731
        path.moveTo(x(7), y(12))
        path.lineTo(x(12), y(17))
        path.lineTo(x(22), y(7))
        path.moveTo(x(2), y(12))
        path.lineTo(x(7), y(17))
        path.moveTo(x(12), y(12))
        path.lineTo(x(17), y(7))
    p.drawPath(path)
    p.restore()
    return width


def tick_width(tick, scale):
    return hubstyle.px({"sent": 11, "read": 15, "clock": 11, "failed": 6}.get(tick, 0), scale)


def _font(base, px_size, bold=False):
    q = _q()
    f = q.QtGui.QFont(base)
    f.setPixelSize(max(6, int(px_size)))
    f.setBold(bold)
    return f


def rich(text, px=None):
    """A message's text as HTML: escaped, links as anchors, emoji as pictures `px` square
    (the line's height when None), new lines kept."""
    from . import emojiart
    return emojiart.rich(text, px or 16)


# ------------------------------------------------------------------ the list

def list_class():
    """ChatList(window): the left column's rows, painted."""
    if "list" not in _CLASSES:
        q = _q()
        QtCore, QtGui, QtWidgets = q.QtCore, q.QtGui, q.QtWidgets

        class ChatList(QtWidgets.QWidget):

            def __init__(self, win, parent=None):
                super(ChatList, self).__init__(parent)
                self.win = win
                self.rows = []            # dicts: id, chat, title, preview, time, unread, user, typing
                self.selected = None
                self.hovered = None
                self.glow = {}            # id -> 0..1
                self.pops = {}            # id -> started (ms)
                self._unread = {}
                self.setMouseTracking(True)
                self.setObjectName("skeldarChatList")

            def row_h(self, row=None):
                if row is not None and row.get("kind") == "head":
                    return hubstyle.px(26, self.win.scale)
                return hubstyle.px(58, self.win.scale)

            def tops(self):
                out, y = [], 0
                for r in self.rows:
                    out.append(y)
                    y += self.row_h(r)
                return out, y

            def set_rows(self, rows):
                now = _now_ms()
                for r in rows:
                    before = self._unread.get(r["id"])
                    if before is not None and before != r.get("unread") and r.get("unread"):
                        self.pops[r["id"]] = now
                    self._unread[r["id"]] = r.get("unread")
                self.rows = rows
                self.setMinimumHeight(max(1, int(self.tops()[1])))
                if self.pops:
                    self.win.animate()
                self.update()

            def index_at(self, y):
                tops, _total = self.tops()
                for i, top in enumerate(tops):
                    if top <= y < top + self.row_h(self.rows[i]):
                        return -1 if self.rows[i].get("kind") == "head" else i
                return -1

            def avatar_rect(self, i):
                """Row `i`'s avatar (a click there opens the person's card)."""
                px = lambda n: hubstyle.px(n, self.win.scale)      # noqa: E731
                top = self.tops()[0][i]
                h = self.row_h(self.rows[i])
                return QtCore.QRectF(px(14), top + (h - px(42)) / 2.0, px(42), px(42))

            def mouseMoveEvent(self, event):              # noqa: N802
                i = self.index_at(event.position().y() if hasattr(event, "position")
                                  else event.pos().y())
                hovered = self.rows[i]["id"] if i >= 0 else None
                if hovered != self.hovered:
                    self.hovered = hovered
                    self.win.animate()

            def leaveEvent(self, event):                   # noqa: N802
                self.hovered = None
                self.win.animate()

            def mousePressEvent(self, event):              # noqa: N802
                pos = event.position() if hasattr(event, "position") else event.pos()
                i = self.index_at(pos.y())
                if i >= 0 and event.button() == QtCore.Qt.LeftButton:
                    row = self.rows[i]
                    person = row.get("kind") == "person" or (row.get("chat") or {}).get("kind") == "dm"
                    if person and self.avatar_rect(i).contains(pos) \
                            and self.win.show_profile(row.get("user")):
                        return
                    if row.get("kind") == "person":
                        self.win.write_to(row["user"]["id"])
                    else:
                        self.win.open_chat(row["id"])

            def tick(self, dt):
                busy = False
                for r in self.rows:
                    goal = 1.0 if r["id"] == self.hovered else 0.0
                    have = self.glow.get(r["id"], 0.0)
                    new = look_approach(have, goal, dt, HOVER_MS)
                    if new != have:
                        self.glow[r["id"]] = new
                        busy = True
                    if new != goal:
                        busy = True
                now = _now_ms()
                for key, start in list(self.pops.items()):
                    if now - start >= POP_MS:
                        del self.pops[key]
                    busy = True
                if busy:
                    self.update()
                return busy or bool(self.pops)

            def paintEvent(self, event):                   # noqa: N802
                p = QtGui.QPainter(self)
                try:
                    self._paint(p)
                except Exception:                            # noqa: BLE001
                    traceback.print_exc()
                finally:
                    p.end()

            def _paint(self, p):
                s = self.win.scale
                px = lambda n: hubstyle.px(n, s)              # noqa: E731
                p.setRenderHint(QtGui.QPainter.Antialiasing)
                w = self.width()
                now = _now_ms()
                tops, _total = self.tops()
                online = self.win.session.state.online
                from . import emojiart
                for i, r in enumerate(self.rows):
                    top = tops[i]
                    h = self.row_h(r)
                    if r.get("kind") == "head":
                        p.setFont(_font(self.font(), px(9), True))
                        p.setPen(_colour("muted"))
                        p.drawText(QtCore.QRectF(px(14), top + px(4), w - px(28), h - px(4)),
                                   QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, r["title"])
                        p.setPen(QtGui.QPen(_colour("track_edge"), 1))
                        p.drawLine(QtCore.QPointF(px(14), top + px(4)),
                                   QtCore.QPointF(w - px(14), top + px(4)))
                        continue
                    #  look A (2026-10-22): rows inset in the column, the open chat
                    #  `card_active` in a 1.5 px accent outline with an inner glow
                    rect = QtCore.QRectF(px(6), top + px(1), w - px(12), h - px(2))
                    glow = self.glow.get(r["id"], 0.0)
                    ring = "panel"
                    if r["id"] == self.selected:
                        ring = "card_active"
                        p.setPen(QtCore.Qt.NoPen)
                        p.setBrush(_colour("card_active"))
                        p.drawRoundedRect(rect, px(8), px(8))
                        p.setBrush(QtCore.Qt.NoBrush)
                        for k, alpha in ((3.0, 0.05), (2.0, 0.08), (1.0, 0.12)):
                            p.setPen(QtGui.QPen(_colour("accent", alpha), px(2)))
                            inset = (1.0 + k) * s
                            p.drawRoundedRect(rect.adjusted(inset, inset, -inset, -inset),
                                              px(8) - inset, px(8) - inset)
                        p.setPen(QtGui.QPen(_colour("accent"), max(1.0, 1.5 * s)))
                        p.drawRoundedRect(rect.adjusted(0.75 * s, 0.75 * s, -0.75 * s, -0.75 * s),
                                          px(8), px(8))
                    elif glow > 0.002:
                        ring = "card" if glow > 0.5 else "panel"
                        p.setPen(QtCore.Qt.NoPen)
                        p.setBrush(_colour("card", glow))
                        p.drawRoundedRect(rect, px(8), px(8))
                    av = QtCore.QRectF(px(14), top + (h - px(42)) / 2.0, px(42), px(42))
                    dot = r.get("kind") == "person" or (r.get("chat") or {}).get("kind") == "dm"
                    paint_avatar(p, av, r["user"], s, dot and is_online(r["user"], online),
                                 ring=ring)
                    x0 = av.right() + px(10)
                    right = w - px(16)
                    t_font = _font(self.font(), px(10))
                    tfm = QtGui.QFontMetrics(t_font)
                    tw = tfm.horizontalAdvance(r["time"]) if r["time"] else 0
                    tick = r.get("tick") or ""
                    kw = tick_width(tick, s)
                    if r["time"]:
                        p.setFont(t_font)
                        p.setPen(_colour("muted"))
                        p.drawText(QtCore.QPointF(right - tw, top + px(23)), r["time"])
                    if kw:
                        colour = hubstyle.TOKENS["muted" if tick == "clock" else
                                                 ("danger" if tick == "failed" else "accent_text")]
                        p.setFont(t_font)
                        paint_ticks(p, right - tw - px(4), top + px(19), tick, colour, s)
                    p.setFont(_font(self.font(), px(12), True))
                    p.setPen(_colour("text"))
                    fm = QtGui.QFontMetrics(p.font())
                    title = fm.elidedText(r["title"], QtCore.Qt.ElideRight,
                                          int(right - x0 - tw - kw - px(10)))
                    p.drawText(QtCore.QPointF(x0, top + px(24)), title)
                    body = _font(self.font(), px(11))
                    p.setFont(body)
                    pfm = QtGui.QFontMetrics(body)
                    badge_w = 0
                    line_y = top + px(42)
                    if r.get("unread"):
                        text = look.count_text(r["unread"])
                        bf = _font(self.font(), px(10), True)
                        bfm = QtGui.QFontMetrics(bf)
                        badge_w = max(px(20), bfm.horizontalAdvance(text) + px(12))
                        k = pop_scale(now - self.pops.get(r["id"], -10 ** 9))
                        badge = QtCore.QRectF(0, 0, badge_w * k, px(20) * k)
                        badge.moveCenter(QtCore.QPointF(right - badge_w / 2.0,
                                                        line_y - pfm.ascent() / 2.0 + px(1)))
                        p.setPen(QtCore.Qt.NoPen)
                        p.setBrush(_colour("accent"))
                        p.drawRoundedRect(badge, badge.height() / 2, badge.height() / 2)
                        p.setFont(bf)
                        p.setPen(QtGui.QColor(hubstyle.TOKENS.get("on_accent", "#1b1c1f")))
                        p.drawText(badge, QtCore.Qt.AlignCenter, text)
                        p.setFont(body)
                    width_left = right - x0 - badge_w - (px(8) if badge_w else 0)
                    x = x0
                    prefix = r.get("prefix") or ""
                    if prefix and not r.get("typing"):
                        lead = pfm.elidedText(prefix + ": ", QtCore.Qt.ElideRight,
                                              int(width_left))
                        p.setPen(_colour("#d2d3d7"))
                        p.drawText(QtCore.QPointF(x, line_y), lead)
                        used = pfm.horizontalAdvance(lead)
                        x += used
                        width_left -= used
                    if width_left > px(4):
                        ink = _colour("accent_text" if r.get("typing")
                                      else ("ok" if r.get("kind") == "person" and r.get("online")
                                            else "muted"))
                        text = r.get("text", r["preview"]) if prefix else r["preview"]
                        emojiart.draw_line(p, QtCore.QRectF(x, line_y - pfm.ascent(),
                                                            width_left, pfm.height()),
                                           text, body, ink)
                if not self.rows:
                    p.setPen(_colour("faint"))
                    p.setFont(_font(self.font(), px(10)))
                    p.drawText(QtCore.QRectF(0, px(10), w, px(40)), QtCore.Qt.AlignCenter,
                               self.win.empty_list_text())

        _CLASSES["list"] = ChatList
    return _CLASSES["list"]


TAB_VAR = "skeldarChatTab"


def tabs_class():
    """Tabs(window): «Все / Личные / Группы» over the list (look A, 2026-10-22), painted: the
    current one in `text` underlined in the accent with its glow, a grey count of the tab's
    chats with unread; a click shows that tab (`window.set_tab`)."""
    if "tabs" not in _CLASSES:
        q = _q()
        QtCore, QtGui, QtWidgets = q.QtCore, q.QtGui, q.QtWidgets

        class Tabs(QtWidgets.QWidget):

            def __init__(self, win, parent=None):
                super(Tabs, self).__init__(parent)
                self.win = win
                self.counts = {}
                self.hovered = None
                self.setObjectName("skeldarChatTabs")
                self.setMouseTracking(True)
                self.setFixedHeight(hubstyle.px(30, win.scale))
                self.setCursor(QtCore.Qt.PointingHandCursor)

            def set_counts(self, counts):
                if counts != self.counts:
                    self.counts = dict(counts)
                    self.update()

            def _font(self):
                return _font(self.font(), hubstyle.px(10.5, self.win.scale), True)

            def rects(self):
                """[(key, label, tab rect, count rect or None)] left to right."""
                px = lambda n: hubstyle.px(n, self.win.scale)      # noqa: E731
                fm = QtGui.QFontMetrics(self._font())
                cfm = QtGui.QFontMetrics(_font(self.font(), px(9), True))
                out, x = [], px(6)
                for key, label in look.TABS:
                    n = int(self.counts.get(key) or 0)
                    w = fm.horizontalAdvance(label) + px(18)
                    count = None
                    if n:
                        cw = max(px(16), cfm.horizontalAdvance(look.count_text(n)) + px(8))
                        count = QtCore.QRectF(x + w - px(4), (self.height() - px(16)) / 2.0,
                                              cw, px(16))
                        w += cw + px(1)
                    out.append((key, label, QtCore.QRectF(x, 0, w, self.height()), count))
                    x += w + px(2)
                return out

            def key_at(self, x):
                for key, _label, rect, _count in self.rects():
                    if rect.left() <= x < rect.right():
                        return key
                return None

            def mouseMoveEvent(self, event):               # noqa: N802
                pos = event.position() if hasattr(event, "position") else event.pos()
                key = self.key_at(pos.x())
                if key != self.hovered:
                    self.hovered = key
                    self.update()

            def leaveEvent(self, event):                   # noqa: N802
                self.hovered = None
                self.update()

            def mousePressEvent(self, event):              # noqa: N802
                if event.button() != QtCore.Qt.LeftButton:
                    return
                pos = event.position() if hasattr(event, "position") else event.pos()
                key = self.key_at(pos.x())
                if key:
                    self.win.set_tab(key)

            def paintEvent(self, event):                   # noqa: N802
                p = QtGui.QPainter(self)
                try:
                    self._paint(p)
                except Exception:                            # noqa: BLE001
                    traceback.print_exc()
                finally:
                    p.end()

            def _paint(self, p):
                s = self.win.scale
                px = lambda n: hubstyle.px(n, s)              # noqa: E731
                p.setRenderHint(QtGui.QPainter.Antialiasing)
                h = self.height()
                p.setPen(QtGui.QPen(_colour("track_edge"), 1))
                p.drawLine(QtCore.QPointF(0, h - 0.5), QtCore.QPointF(self.width(), h - 0.5))
                current = self.win.tab
                for key, label, rect, count in self.rects():
                    on = key == current
                    if key == self.hovered and not on:
                        p.setPen(QtCore.Qt.NoPen)
                        p.setBrush(_colour("track_edge"))
                        p.drawRoundedRect(rect.adjusted(0, px(3), 0, px(4)), px(5), px(5))
                    p.setFont(self._font())
                    p.setPen(_colour("text" if on or key == self.hovered else "muted"))
                    text_rect = QtCore.QRectF(rect.left() + px(9), 0, rect.width(), h)
                    p.drawText(text_rect, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, label)
                    if count is not None:
                        p.setPen(QtCore.Qt.NoPen)
                        p.setBrush(_colour("line"))
                        p.drawRoundedRect(count, count.height() / 2.0, count.height() / 2.0)
                        p.setFont(_font(self.font(), px(9), True))
                        p.setPen(_colour("text"))
                        p.drawText(count, QtCore.Qt.AlignCenter,
                                   look.count_text(self.counts.get(key)))
                    if on:
                        bar = QtCore.QRectF(rect.left() + px(6), h - px(2),
                                            rect.width() - px(12), px(2))
                        p.setPen(QtCore.Qt.NoPen)
                        for grow, alpha in ((px(4), 0.08), (px(2.5), 0.14), (px(1.2), 0.24)):
                            p.setBrush(_colour("accent", alpha))
                            p.drawRoundedRect(bar.adjusted(-grow, -grow, grow, 0), grow, grow)
                        p.setBrush(_colour("accent"))
                        p.drawRoundedRect(bar, px(1), px(1))

        _CLASSES["tabs"] = Tabs
    return _CLASSES["tabs"]


def look_approach(value, goal, dt_ms, ms):
    import math
    if ms <= 0 or not hubmotion.enabled():
        return goal
    k = 1.0 - math.exp(-3.0 * dt_ms / ms)
    out = value + (goal - value) * k
    return goal if abs(out - goal) < 0.005 else out


# ------------------------------------------------------------------ the feed

class Box(object):
    """A laid-out line of the feed."""
    __slots__ = ("item", "rect", "bubble", "doc", "doc_at", "name_at", "quote", "meta",
                 "meta_at", "failed_rect", "height", "pills", "card", "fbuttons", "fbar",
                 "thumb", "avatar", "bigs", "callpill", "bare", "tail", "meta_pill", "band")

    def __init__(self, item):
        self.item = item
        self.rect = None
        self.bubble = None
        self.doc = None
        self.doc_at = None
        self.name_at = None
        self.quote = None        # (rect, original id, name, text)
        self.meta = ""
        self.meta_at = None
        self.failed_rect = None
        self.height = 0.0
        self.pills = []          # [(rect, emoji, count, mine)] under the bubble
        self.card = None         # a file message's card (2026-10-22)
        self.fbuttons = []       # [(rect, action, label)] under the card
        self.fbar = None         # (rect, progress or None, text): an upload or download
        self.thumb = None        # the file's preview over its card
        self.avatar = None       # the sender's avatar beside a group's message
        self.bigs = []           # [(rect, glyph)]: a message of 1-3 emoji alone, as pictures
        self.callpill = None     # a call line's pill (2026-10-22)
        self.bare = False        # emoji alone: no bubble face (look A)
        self.tail = False        # the last of a run: Telegram's tail on the sender's side
        self.meta_pill = None    # emoji alone: the time in a dark pill under them
        self.band = None         # «Непрочитанные сообщения»


def feed_class():
    """Feed(window): the chat's bubbles, painted."""
    if "feed" not in _CLASSES:
        q = _q()
        QtCore, QtGui, QtWidgets = q.QtCore, q.QtGui, q.QtWidgets

        class Feed(QtWidgets.QWidget):

            def __init__(self, win, parent=None):
                super(Feed, self).__init__(parent)
                self.win = win
                self.items = []
                self.boxes = []
                self.ctx = {}
                self.docs = {}            # (key, text, width) -> QTextDocument
                self.entering = {}        # key -> started
                self.flashing = {}        # key -> started
                self.folding = []         # [(y, height, started)]
                self.pill_pops = {}       # (message id, emoji) -> started
                self._counts = {}         # (message id, emoji) -> count last seen
                self._known = None
                self._laid_w = -1
                self._press = None        # (point, item) on a file card, before a drag starts
                self._dragging = False
                self._hover_button = None
                self.playing = None       # (message key, started ms): an animation preview playing
                self.plays = {}           # (message key, glyph, "big"|"pill") -> started ms
                self.played = set()       # the same keys, played once since the window opened
                self.anim = None          # emojiart.Animated (the window sets it)
                self._emoji_hover = None  # (message key, glyph, kind) under the mouse
                self.hover_key = None     # the message whose row the mouse is on (look A)
                self.reply_level = 0.0    # its reply button fading in, 0..1
                self.reply_hot = False    # the mouse on that button
                self._tile = None         # the backdrop's dots
                self.setObjectName("skeldarChatFeed")
                self.setMouseTracking(True)

            # ---------------------------------------------------------- data
            def set_items(self, items, ctx, animate=True):
                keys = [i.key() for i in items if i.kind == "msg"]
                now = _now_ms()
                if self._known is not None and animate and hubmotion.enabled():
                    old = self._known
                    for i in items:
                        if i.kind != "msg":
                            continue
                        k = i.key()
                        if k not in old["keys"]:
                            # a pending one becoming its message keeps its place: it flashes
                            cid = i.message.get("cid")
                            if not i.pending and cid and cid in old["pending"]:
                                self.flashing[k] = now
                            elif not old.get("history"):
                                self.entering[k] = now
                    for box in self.boxes:
                        k = box.item.key() if box.item.kind == "msg" else None
                        if k and k not in keys and not box.item.pending \
                                and k in ctx.get("deleted", ()):
                            self.folding.append((box.rect.top(), box.height, now))
                counts = {}
                for i in items:
                    if i.kind == "msg" and not i.pending:
                        for e, ids in (i.message.get("reactions") or {}).items():
                            counts[(i.message.get("id"), e)] = len(ids)
                if self._known is not None and animate and hubmotion.enabled():
                    for k, n in counts.items():
                        if n > self._counts.get(k, 0):
                            self.pill_pops[k] = now
                self._counts = counts
                chat_id = (ctx.get("chat") or {}).get("id")
                if chat_id != getattr(self, "_chat_id", None):
                    self.plays.clear()            # another chat: nothing of the last one plays
                    self._emoji_hover = None
                self._chat_id = chat_id
                self._known = {"keys": set(keys),
                               "pending": set(i.key() for i in items if i.pending)}
                self.items = items
                self.ctx = ctx
                self.relayout()
                if self.entering or self.flashing or self.folding or self.pill_pops:
                    self.win.animate()

            def relayout(self):
                self.boxes = self._layout(max(1, self.width()))
                total = self.boxes[-1].rect.bottom() if self.boxes else 0
                self.setMinimumHeight(int(total + hubstyle.px(10, self.win.scale)))
                self._laid_w = self.width()
                self.update()

            def resizeEvent(self, event):                  # noqa: N802
                if self.width() != self._laid_w:
                    self.relayout()
                super(Feed, self).resizeEvent(event)

            def _big(self, item):
                """The glyphs of a message of 1-3 emoji alone, each with a picture; else []."""
                from . import emoji as _emoji
                from . import emojiart
                if not _emoji.only_emoji(item.text):
                    return []
                parts = [p for _k, p in _emoji.tokens("".join(item.text.split()))]
                return parts if all(emojiart._known(p) for p in parts) else []

            def _doc(self, item, width):
                key = (item.key(), item.text, int(width))
                doc = self.docs.get(key)
                if doc is None:
                    from . import emoji as _emoji
                    from . import emojiart
                    doc = QtGui.QTextDocument()
                    doc.setDocumentMargin(0)
                    big = _emoji.only_emoji(item.text)
                    font = _font(self.font(), hubstyle.px(30 if big else 11.5, self.win.scale))
                    font.setFamilies([font.family(), _emoji.FONT])
                    doc.setDefaultFont(font)
                    side = int(QtGui.QFontMetrics(font).height() * 1.2)
                    emojiart.register(doc, item.text, side)
                    doc.setDefaultStyleSheet("a {{ color: {0}; }}".format(
                        hubstyle.TOKENS["accent_text"]))
                    doc.setHtml('<span style="color:{0}">{1}</span>'.format(
                        hubstyle.TOKENS["text"], rich(item.text, side)))
                    doc.setTextWidth(width)
                    ideal = doc.idealWidth()
                    if ideal + 1 < width:
                        doc.setTextWidth(ideal + 1)
                    if len(self.docs) > 400:
                        self.docs.clear()
                    self.docs[key] = doc
                return doc

            def _layout(self, width):
                s = self.win.scale
                px = lambda n: hubstyle.px(n, s)              # noqa: E731
                group = (self.ctx.get("chat") or {}).get("kind") == "group"
                side = px(14)
                avatar = px(36) if group else 0
                max_w = min(0.72 * (width - 2 * side - avatar), px(520))
                pad_x, pad_y = px(10), px(6)
                sfm = QtGui.QFontMetrics(self._meta_font())
                nfm = QtGui.QFontMetrics(_font(self.font(), px(10.5), True))
                y = px(6)
                boxes = []
                for item in self.items:
                    box = Box(item)
                    if item.kind == "day":
                        h = px(32)
                        box.rect = QtCore.QRectF(0, y, width, h)
                        box.height = h
                        boxes.append(box)
                        y += h
                        continue
                    if item.kind == "call":
                        h = px(32)
                        box.rect = QtCore.QRectF(0, y, width, h)
                        box.height = h
                        w = self._call_width(item)
                        box.callpill = QtCore.QRectF((width - w) / 2.0, y + px(6), w, px(22))
                        boxes.append(box)
                        y += h
                        continue
                    if item.kind == "unread":
                        h = px(32)
                        box.rect = QtCore.QRectF(0, y, width, h)
                        box.band = QtCore.QRectF(0, y + px(6), width, px(22))
                        box.height = h
                        boxes.append(box)
                        y += h
                        continue
                    boxes.append(self._lay_message(box, y, width, max_w, side, avatar, group,
                                                   pad_x, pad_y, sfm, nfm))
                    y = box.rect.bottom()
                return boxes

            def _meta_width(self, box, sfm):
                tick = box.item.tick
                return sfm.horizontalAdvance(box.meta) + (
                    hubstyle.px(3, self.win.scale) + tick_width(tick, self.win.scale)
                    if tick else 0)

            def _last_line(self, doc):
                """(width, baseline y) of a document's last line."""
                block = doc.lastBlock()
                lay = block.layout()
                if lay is None or lay.lineCount() == 0:
                    return 0.0, doc.size().height()
                line = lay.lineAt(lay.lineCount() - 1)
                top = lay.position().y()
                return line.x() + line.naturalTextWidth(), top + line.y() + line.ascent()

            def _lay_message(self, box, y, width, max_w, side, avatar, group, pad_x, pad_y,
                             sfm, nfm):
                """One message (look A, 2026-10-22): a bubble with its time and ticks inside -
                on the text's last line when they fit, else under it or at the right of the
                last row of reactions - its reactions inside too; emoji alone bare, their time
                in a dark pill."""
                s = self.win.scale
                px = lambda n: hubstyle.px(n, s)              # noqa: E731
                item = box.item
                msg = item.message
                inner = max(px(40), max_w - 2 * pad_x)
                f = msg.get("file")
                bigs = [] if f else self._big(item)
                box.meta = ("изм. " if msg.get("edited_at") else "") + \
                    look.hm(msg.get("at") or _now_ms())
                meta_w = self._meta_width(box, sfm)
                meta_gap = px(8)
                rows = [] if item.pending else self._pill_rows(msg, inner)
                pills_w = max([w for w, _r in rows] or [0])
                ph, pgap = px(22), px(4)
                pills_h = (len(rows) * (ph + pgap) + px(2)) if rows else 0
                y += px(8) if item.first else px(2)
                box.tail = item.last and not bigs
                if bigs:
                    side_b, gap_b = px(BIG_EMOJI), px(4)
                    bw = len(bigs) * side_b + (len(bigs) - 1) * gap_b
                    x = width - side - bw if item.mine else side + avatar
                    box.bare = True
                    box.bubble = QtCore.QRectF(x, y, bw, side_b)
                    box.bigs = [(QtCore.QRectF(x + i * (side_b + gap_b), y, side_b, side_b), g)
                                for i, g in enumerate(bigs)]
                    mw = meta_w + px(14)
                    box.meta_pill = QtCore.QRectF(x + bw - mw, y + side_b + px(2), mw, px(18))
                    box.meta_at = QtCore.QPointF(
                        box.meta_pill.left() + px(7),
                        box.meta_pill.center().y() + (sfm.ascent() - sfm.descent()) / 2.0)
                    h = side_b + px(2) + px(18)
                    if rows:
                        self._place_pills(box, rows, x, y + h + px(2), bw, item.mine, ph, pgap)
                        h += px(2) + len(rows) * (ph + pgap)
                    if group and not item.mine and item.last:
                        box.avatar = QtCore.QRectF(side, y + side_b - px(30), px(30), px(30))
                    return self._close_box(box, y, h, width, sfm)
                if f and not item.text:
                    doc, doc_w, doc_h = None, 0, 0
                else:
                    doc = self._doc(item, inner)
                    doc_w, doc_h = doc.size().width(), doc.size().height()
                box.doc = doc
                ph_file = look.preview_height(f, self._pending_thumb(item)) if f else 0
                file_h = (px(FILE_CARD) + px(4) + px(FILE_ROW) + px(4)
                          + (px(ph_file) + px(4) if ph_file else 0)) if f else 0
                content_w = doc_w
                if f:
                    content_w = max(content_w, min(inner, px(FILE_WIDTH)))
                name_h = 0
                if group and not item.mine and item.first:
                    name = self.ctx.get("name_of", lambda uid: uid)(msg.get("from_id"))
                    name_h = nfm.height() + px(1)
                    content_w = max(content_w, nfm.horizontalAdvance(name))
                quote_h = 0
                reply = msg.get("reply_to")
                original = None
                if reply:
                    original = look.find(self.ctx.get("messages"), reply)
                    quote_h = px(38)
                    content_w = max(content_w, min(inner, px(160)))
                last_w, last_base = self._last_line(doc) if doc is not None else (0.0, 0.0)
                inline = doc is not None and not rows and look.meta_fits(
                    last_w, meta_w, inner, meta_gap)
                on_pills = False
                meta_h = 0
                if inline:
                    content_w = max(content_w, last_w + meta_gap + meta_w)
                elif rows and rows[-1][0] + meta_gap + meta_w <= inner:
                    on_pills = True
                    content_w = max(content_w, pills_w, rows[-1][0] + meta_gap + meta_w)
                else:
                    content_w = max(content_w, pills_w, meta_w)
                    meta_h = sfm.height() + px(1)
                content_w = min(max(content_w, px(24)), inner)
                bw = content_w + 2 * pad_x
                body = name_h + quote_h + file_h + doc_h
                bh = pad_y + body + pills_h + meta_h + pad_y
                if item.mine:
                    x = width - side - bw
                else:
                    x = side + avatar
                box.bubble = QtCore.QRectF(x, y, bw, bh)
                if group and not item.mine and item.last:
                    box.avatar = QtCore.QRectF(side, y + bh - px(30), px(30), px(30))
                cx = x + pad_x
                cy = y + pad_y
                if name_h:
                    box.name_at = QtCore.QPointF(cx, cy + nfm.ascent())
                    cy += name_h
                if quote_h:
                    qrect = QtCore.QRectF(cx, cy + px(1), bw - 2 * pad_x, quote_h - px(5))
                    if original is not None:
                        quid = original.get("from_id")
                        qname = self.ctx.get("name_of", lambda uid: uid)(quid)
                        qtext = "сообщение удалено" if original.get("deleted") \
                            else look.message_text(original)
                    else:
                        quid, qname, qtext = None, "", "сообщение"
                    box.quote = (qrect, reply, qname, qtext,
                                 look.user_colour(quid) if quid else hubstyle.TOKENS["accent"])
                    cy += quote_h
                if f:
                    self._lay_file(box, cx, cy, bw - 2 * pad_x)
                    cy += file_h
                box.doc_at = QtCore.QPointF(cx, cy)
                cy += doc_h
                right = x + bw - pad_x
                if inline:
                    box.meta_at = QtCore.QPointF(right - meta_w, box.doc_at.y() + last_base)
                if rows:
                    self._place_pills(box, rows, cx, cy + px(2), content_w, False, ph, pgap)
                    if on_pills:
                        r = box.pills[-1][0]
                        box.meta_at = QtCore.QPointF(
                            right - meta_w, r.center().y() + (sfm.ascent() - sfm.descent()) / 2.0)
                    cy += pills_h
                if meta_h:
                    box.meta_at = QtCore.QPointF(right - meta_w, cy + sfm.ascent())
                return self._close_box(box, y, bh, width, sfm)

            def _close_box(self, box, y, h, width, sfm):
                px = lambda n: hubstyle.px(n, self.win.scale)      # noqa: E731
                if box.item.tick == "failed":
                    b = box.bubble
                    box.failed_rect = QtCore.QRectF(b.left() - px(40), y + h + px(2),
                                                    b.width() + px(40), sfm.height() + px(2))
                    h += sfm.height() + px(4)
                box.rect = QtCore.QRectF(0, y, width, h)
                box.height = h
                return box

            def _lay_file(self, box, x, y, w):
                """A file message's card, and under it its buttons or its progress bar."""
                px = lambda n: hubstyle.px(n, self.win.scale)      # noqa: E731
                ph = look.preview_height(box.item.message.get("file"), self._pending_thumb(box.item))
                if ph:
                    box.thumb = QtCore.QRectF(x, y, w, px(ph))
                    y += px(ph) + px(4)
                box.card = QtCore.QRectF(x, y, w, px(FILE_CARD))
                row = QtCore.QRectF(x, y + px(FILE_CARD) + px(4), w, px(FILE_ROW))
                state = (self.ctx.get("file_state") or (lambda item: ("ready", None, "")))(box.item)
                mode, progress, text = state
                box.fbuttons = []
                actions = FILE_ACTIONS.get(mode, ())
                if mode in ("upload", "download", "expired", "failed", "card"):
                    tail = px(74) if actions else 0
                    box.fbar = (QtCore.QRectF(row.left(), row.top(), row.width() - tail, row.height()),
                                progress, text)
                    if actions:
                        action, label = actions[0]
                        box.fbuttons.append((QtCore.QRectF(row.right() - tail + px(4), row.top(),
                                                           tail - px(4), row.height()), action, label))
                    return
                box.fbar = None
                gap = px(4)
                more = px(32) if any(a[0] == "more" for a in actions) else -gap
                main = [a for a in actions if a[0] != "more"]
                each = (row.width() - more - gap * len(main)) / max(1, len(main))
                cx = row.left()
                for action, label in actions:
                    width = more if action == "more" else each
                    box.fbuttons.append((QtCore.QRectF(cx, row.top(), width, row.height()), action, label))
                    cx += width + gap

            def _pending_thumb(self, item):
                up = item.message.get("upload") if item.pending else None
                return bool(up and up.get("thumb"))

            def _preview_image(self, box):
                f = box.item.message.get("file") or {}
                up = box.item.message.get("upload") if box.item.pending else None
                try:
                    from . import thumbs
                    held = thumbs.cache(self.win.session)
                    return held.image(f, (up or {}).get("thumb")) if held is not None else None
                except Exception:                            # noqa: BLE001
                    return None

            def _paint_preview(self, p, box):
                s = self.win.scale
                px = lambda n: hubstyle.px(n, s)              # noqa: E731
                from . import thumbs
                f = box.item.message.get("file") or {}
                rect = box.thumb
                clip = QtGui.QPainterPath()
                clip.addRoundedRect(rect, px(6), px(6))
                p.setPen(QtCore.Qt.NoPen)
                p.setBrush(_colour("panel", 0.6))
                p.drawPath(clip)
                image = self._preview_image(box)
                if image is None:
                    p.setPen(_colour("muted"))
                    p.setFont(_font(self.font(), px(9)))
                    p.drawText(rect, QtCore.Qt.AlignCenter, u"превью…")
                    return
                sheet = thumbs.sheet_of(f)
                source = QtCore.QRectF(0, 0, image.width(), image.height())
                if sheet is None and f.get("kind") != "image":
                    # a still's own backdrop fills the frame round it (a viewport, a card's)
                    p.setBrush(image.pixelColor(1, 1))
                    p.drawPath(clip)
                if sheet is not None:
                    side = image.width() / float(sheet["columns"])
                    playing = self.playing if self.playing and self.playing[0] == box.item.key() \
                        else None
                    cell = thumbs.play_cell(_now_ms() - playing[1] if playing else None, sheet)
                    cx, cy, cw, ch = thumbs.cell_rect(cell, sheet["columns"], side)
                    source = QtCore.QRectF(cx, cy, cw, ch)
                fx, fy, fw, fh = look.fitted(source.width(), source.height(), rect.width(), rect.height())
                target = QtCore.QRectF(rect.left() + fx, rect.top() + fy, fw, fh)
                p.save()
                p.setClipPath(clip)
                p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
                p.drawImage(target, image, source)
                p.restore()
                if sheet is not None:
                    badge = u"\u25b6" if not (self.playing and self.playing[0] == box.item.key()) \
                        else u"\u25b6 %d" % (sheet["cells"])
                    p.setFont(_font(self.font(), px(9), True))
                    fm = QtGui.QFontMetrics(p.font())
                    bw = fm.horizontalAdvance(badge) + px(10)
                    br = QtCore.QRectF(rect.right() - bw - px(6), rect.bottom() - px(20), bw, px(16))
                    p.setPen(QtCore.Qt.NoPen)
                    p.setBrush(QtGui.QColor(0, 0, 0, 150))
                    p.drawRoundedRect(br, px(8), px(8))
                    p.setPen(_colour("text"))
                    p.drawText(br, QtCore.Qt.AlignCenter, badge)

            def _paint_file(self, p, box):
                s = self.win.scale
                px = lambda n: hubstyle.px(n, s)              # noqa: E731
                f = box.item.message.get("file") or {}
                if box.thumb is not None:
                    self._paint_preview(p, box)
                card = box.card
                mine = box.item.mine
                #  look A (2026-10-22): no plate, the tile ringed in the accent
                tile = QtCore.QRectF(card.left(), card.top() + px(2),
                                     card.height() - px(4), card.height() - px(4))
                p.setPen(QtGui.QPen(_colour("accent", 0.45), max(1.0, s)))
                p.setBrush(_colour("#2b1b10" if mine else "accent_tint"))
                p.drawRoundedRect(tile.adjusted(0.5, 0.5, -0.5, -0.5), px(8), px(8))
                p.setFont(_font(self.font(), px(9.5), True))
                p.setPen(_colour("accent_text"))
                p.drawText(tile, QtCore.Qt.AlignCenter, look.file_tag(f))
                left = tile.right() + px(8)
                width = card.right() - px(6) - left
                p.setFont(_font(self.font(), px(10.5), True))
                fm = QtGui.QFontMetrics(p.font())
                p.setPen(_colour("text"))
                p.drawText(QtCore.QPointF(left, card.top() + px(6) + fm.ascent()),
                           fm.elidedText(f.get("name") or "", QtCore.Qt.ElideMiddle, int(width)))
                p.setFont(_font(self.font(), px(9.5)))
                fm2 = QtGui.QFontMetrics(p.font())
                p.setPen(_colour(look.MINE_META if mine else "muted"))
                p.drawText(QtCore.QPointF(left, card.bottom() - px(6) - fm2.descent()),
                           fm2.elidedText(look.file_line(f), QtCore.Qt.ElideRight, int(width)))
                if box.fbar is not None:
                    rect, progress, text = box.fbar
                    p.setPen(QtCore.Qt.NoPen)
                    p.setBrush(QtGui.QColor(0, 0, 0, 77))
                    p.drawRoundedRect(rect, px(5), px(5))
                    if progress is not None:
                        done = QtCore.QRectF(rect)
                        done.setWidth(max(0.0, min(1.0, progress)) * rect.width())
                        p.setBrush(_colour("accent", 0.55))
                        p.drawRoundedRect(done, px(5), px(5))
                    p.setPen(_colour("text2"))
                    p.drawText(rect, QtCore.Qt.AlignCenter, text)
                for rect, action, label in box.fbuttons:
                    hover = self._hover_button == (id(box.item.message), action)
                    lead = action == "open"
                    edge = _colour("accent", 0.55) if lead or hover else (
                        QtGui.QColor(255, 255, 255, 46) if mine else _colour("line"))
                    p.setPen(QtGui.QPen(edge, max(1.0, s)))
                    p.setBrush(_colour("hover") if hover else QtGui.QColor(0, 0, 0, 36))
                    p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), px(5), px(5))
                    p.setPen(_colour("accent_text" if action == "open" else "text"))
                    p.drawText(rect, QtCore.Qt.AlignCenter, label)

            def _pill_font(self):
                return _font(self.font(), hubstyle.px(10.5, self.win.scale), True)

            def _meta_font(self):
                return _font(self.font(), hubstyle.px(9.5, self.win.scale))

            def _call_width(self, item):
                px = lambda n: hubstyle.px(n, self.win.scale)      # noqa: E731
                from . import emojiart
                text_w = emojiart.line_width(item.text, _font(self.font(), px(9.5), True))
                tfm = QtGui.QFontMetrics(_font(self.font(), px(9.5)))
                time_w = tfm.horizontalAdvance(look.hm(item.message.get("at") or _now_ms()))
                return px(12) + px(14) + px(6) + text_w + px(8) + time_w + px(12)

            def _pill_rows(self, message, width):
                """The reactions' pills wrapped into rows `width` wide: [(row width, [(w, e, n,
                me)])] (look A: they stand inside the bubble)."""
                from . import emoji as _emoji
                px = lambda n: hubstyle.px(n, self.win.scale)      # noqa: E731
                pills = _emoji.pills(message.get("reactions"), self.win.me_id())
                if not pills:
                    return []
                fm = QtGui.QFontMetrics(self._pill_font())
                gap = px(4)
                rows, row, used = [], [], 0
                for e, n, me in pills:
                    w = px(PILL_EMOJI) + px(4) + fm.horizontalAdvance(str(n)) + px(14)
                    if row and used + gap + w > width:
                        rows.append((used, row))
                        row, used = [], 0
                    row.append((w, e, n, me))
                    used += (gap if used else 0) + w
                rows.append((used, row))
                return rows

            def _place_pills(self, box, rows, x, top, width, right_aligned, ph, gap):
                y = top
                for total, row in rows:
                    cx = (x + width - total) if right_aligned else x
                    for w, e, n, me in row:
                        box.pills.append((QtCore.QRectF(cx, y, w, ph), e, n, me))
                        cx += w + gap
                    y += ph + gap

            # ---------------------------------------------------------- motion
            def tick(self, dt):
                now = _now_ms()
                for store, ms in ((self.entering, ENTER_MS), (self.flashing, SENT_FLASH_MS)):
                    for k, start in list(store.items()):
                        if now - start >= ms:
                            del store[k]
                self.folding = [f for f in self.folding if now - f[2] < FOLD_MS]
                for k, start in list(self.pill_pops.items()):
                    if now - start >= POP_MS:
                        del self.pill_pops[k]
                for k, start in list(self.plays.items()):
                    if now - start >= PLAY_CAP_MS:     # its box may never be painted again
                        del self.plays[k]
                goal = 1.0 if self.hover_key is not None else 0.0
                self.reply_level = look_approach(self.reply_level, goal, dt, HOVER_MS)
                busy = bool(self.entering or self.flashing or self.folding or self.pill_pops
                            or self.playing or self.plays or self.reply_level != goal)
                self.update()
                return busy

            def _start(self, key, glyph):
                """Play `glyph`'s animation now when it has one and its frames are ready."""
                from . import emojiart
                if self.anim is None or not hubmotion.enabled():
                    return False
                cp = emojiart.anim_of(glyph)
                if not cp:
                    return False
                side = int(hubstyle.px(BIG_EMOJI if key[2] == "big" else PILL_EMOJI,
                                       self.win.scale))
                if not self.anim.frames(cp, side):
                    return False
                self.plays[key] = _now_ms()
                self.played.add(key)
                self.win.animate()
                return True

            def _draw_emoji(self, p, rect, key, glyph, now):
                """Draw an emoji picture into `rect`; False when it has none."""
                pic = self._emoji_frame(key, glyph, rect.width(), now)
                if pic is None:
                    return False
                if isinstance(pic, QtGui.QPixmap):
                    p.drawPixmap(rect, pic, QtCore.QRectF(pic.rect()))
                else:
                    p.drawImage(rect, pic, QtCore.QRectF(pic.rect()))
                return True

            def _emoji_frame(self, key, glyph, side, now):
                """What to draw for an emoji picture at `side`: its animation's frame (a QImage)
                while it plays (starting it the first time it is painted), else its still
                picture (a QPixmap)."""
                from . import emojiart
                if key not in self.played:
                    self._start(key, glyph)
                start = self.plays.get(key)
                if start is not None and self.anim is not None:
                    frames = self.anim.frames(emojiart.anim_of(glyph), int(side))
                    img, done = emojiart.frame_at(frames, now - start)
                    if done:
                        self.plays.pop(key, None)
                    if img is not None:
                        return img
                return emojiart.pixmap(glyph, int(side))

            # ---------------------------------------------------------- paint
            def paintEvent(self, event):                   # noqa: N802
                p = QtGui.QPainter(self)
                try:
                    self._paint(p, event.rect())
                except Exception:                            # noqa: BLE001
                    traceback.print_exc()
                finally:
                    p.end()

            def _paint(self, p, clip):
                s = self.win.scale
                px = lambda n: hubstyle.px(n, s)              # noqa: E731
                p.setRenderHint(QtGui.QPainter.Antialiasing)
                p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
                now = _now_ms()
                small = self._meta_font()
                group = (self.ctx.get("chat") or {}).get("kind") == "group"
                self._paint_backdrop(p, clip)
                for top, height, start in self.folding:
                    k = 1.0 - (now - start) / float(FOLD_MS)
                    p.setPen(QtCore.Qt.NoPen)
                    p.setBrush(_colour("card_active", 0.6 * k))
                    r = QtCore.QRectF(self.width() * 0.25, top + height * (1 - k) / 2,
                                      self.width() * 0.5, height * k)
                    p.drawRoundedRect(r, px(8), px(8))
                from . import emojiart
                for box in self.boxes:
                    if box.rect.bottom() < clip.top() - px(40) or \
                            box.rect.top() > clip.bottom() + px(40):
                        continue
                    item = box.item
                    if item.kind == "day":
                        p.setFont(_font(self.font(), px(9.5), True))
                        fm = QtGui.QFontMetrics(p.font())
                        w = fm.horizontalAdvance(item.text) + px(20)
                        pill = QtCore.QRectF((self.width() - w) / 2.0,
                                             box.rect.top() + px(7), w, px(20))
                        self._dark_pill(p, pill)
                        p.setPen(_colour("#c9cacf"))
                        p.drawText(pill, QtCore.Qt.AlignCenter, item.text)
                        continue
                    if item.kind == "unread":
                        band = box.band
                        p.setPen(QtCore.Qt.NoPen)
                        p.setBrush(_colour("accent", 0.08))
                        p.drawRect(band)
                        p.setPen(QtGui.QPen(_colour("accent", 0.2), 1))
                        p.drawLine(band.topLeft(), band.topRight())
                        p.drawLine(band.bottomLeft(), band.bottomRight())
                        p.setFont(_font(self.font(), px(9.5), True))
                        p.setPen(_colour("accent_text"))
                        p.drawText(band, QtCore.Qt.AlignCenter, item.text)
                        continue
                    if item.kind == "call":
                        self._paint_call(p, box, item)
                        continue
                    p.save()
                    key = item.key()
                    if key in self.entering:
                        u = (now - self.entering[key]) / float(ENTER_MS)
                        p.translate(0, (1.0 - back_out(u)) * px(14))
                        p.setOpacity(max(0.0, min(1.0, u * 2.0)))
                    bubble = box.bubble
                    mine = item.mine
                    face = look.MINE if mine else look.THEIRS
                    if key in self.flashing:
                        k = 1.0 - (now - self.flashing[key]) / float(SENT_FLASH_MS)
                        colour = _blend(face, "accent", 0.45 * k)
                    else:
                        colour = _q().QtGui.QColor(face)
                    if item.pending and item.tick == "clock":
                        colour.setAlphaF(0.75)
                    if not box.bare:
                        p.setPen(QtCore.Qt.NoPen)
                        p.setBrush(colour)
                        p.drawPath(self._bubble_path(bubble, mine, box.tail))
                    if box.avatar is not None:
                        av = box.avatar
                        paint_avatar(p, av, self.ctx.get("user_of", lambda uid: {"id": uid})(
                            item.message.get("from_id")), s)
                    if box.name_at is not None:
                        uid = item.message.get("from_id")
                        p.setFont(_font(self.font(), px(10.5), True))
                        p.setPen(_q().QtGui.QColor(look.user_colour(uid)))
                        p.drawText(box.name_at, self.ctx.get("name_of", lambda u: u)(uid))
                    if box.quote is not None:
                        qrect, _rid, qname, qtext, qcolour = box.quote
                        clip_q = QtGui.QPainterPath()
                        clip_q.addRoundedRect(qrect, px(6), px(6))
                        p.save()
                        p.setClipPath(clip_q, QtCore.Qt.IntersectClip)
                        p.setPen(QtCore.Qt.NoPen)
                        p.setBrush(QtGui.QColor(0, 0, 0, 46) if mine
                                   else QtGui.QColor(255, 255, 255, 15))
                        p.drawRect(qrect)
                        p.setBrush(QtGui.QColor(qcolour))
                        p.drawRect(QtCore.QRectF(qrect.left(), qrect.top(), px(3), qrect.height()))
                        p.restore()
                        p.setFont(_font(self.font(), px(10), True))
                        p.setPen(QtGui.QColor(qcolour).lighter(135))
                        fm = QtGui.QFontMetrics(p.font())
                        p.drawText(QtCore.QPointF(qrect.left() + px(10), qrect.top() + fm.ascent()
                                                  + px(3)),
                                   fm.elidedText(qname, QtCore.Qt.ElideRight,
                                                 int(qrect.width() - px(14))))
                        p.setFont(_font(self.font(), px(10)))
                        p.setPen(_colour("#ead6c6" if mine else "#c9cacf"))
                        fm2 = QtGui.QFontMetrics(p.font())
                        emojiart.draw_line(p, QtCore.QRectF(qrect.left() + px(10),
                                                            qrect.bottom() - fm2.height() - px(3),
                                                            qrect.width() - px(14), fm2.height()),
                                           qtext, p.font(), p.pen().color())
                    if box.card is not None:
                        p.save()
                        self._paint_file(p, box)
                        p.restore()
                        p.setFont(small)
                    if box.doc is not None:
                        p.save()
                        p.translate(box.doc_at)
                        box.doc.drawContents(p)
                        p.restore()
                    for rect, glyph in box.bigs:
                        self._draw_emoji(p, rect, (key, glyph, "big"), glyph, now)
                    self._paint_meta(p, box, small)
                    if box.pills:
                        p.setFont(self._pill_font())
                        for rect, e, n, me in box.pills:
                            k = pop_scale(now - self.pill_pops.get(
                                (item.message.get("id"), e), -10 ** 9))
                            r = QtCore.QRectF(rect)
                            if k != 1.0:
                                c = r.center()
                                r.setSize(r.size() * k)
                                r.moveCenter(c)
                            if me:
                                p.setPen(QtGui.QPen(_colour("accent"), max(1.0, s)))
                                p.setBrush(_colour("accent", 0.3 if mine else 0.2))
                            else:
                                p.setPen(QtCore.Qt.NoPen)
                                p.setBrush(QtGui.QColor(0, 0, 0, 56) if mine and not box.bare
                                           else QtGui.QColor(255, 255, 255, 20))
                            p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
                            p.setPen(_colour("accent_text" if me else "text"))
                            side = px(PILL_EMOJI)
                            pic = QtCore.QRectF(r.left() + px(7), r.center().y() - side / 2.0,
                                                side, side)
                            if not self._draw_emoji(p, pic, (key, e, "pill"), e, now):
                                from . import emoji as _emoji
                                fallback = QtGui.QFont(p.font())
                                fallback.setFamilies([fallback.family(), _emoji.FONT])
                                p.save()
                                p.setFont(fallback)
                                p.drawText(pic, QtCore.Qt.AlignCenter, e)
                                p.restore()
                            p.drawText(QtCore.QRectF(pic.right() + px(4), r.top(),
                                                     r.right() - pic.right() - px(4), r.height()),
                                       QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, str(n))
                        p.setFont(small)
                    if box.failed_rect is not None:
                        p.setPen(_colour("danger"))
                        p.drawText(box.failed_rect,
                                   QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                                   if item.mine else QtCore.Qt.AlignLeft,
                                   "не отправлено — повторить")
                    if key == self.hover_key and self.reply_level > 0.01:
                        self._paint_reply_button(p, box)
                    p.restore()

            # ---------------------------------------------------------- look A's parts
            def _paint_backdrop(self, p, clip):
                """`look.FEED_BG` under a pattern of white and accent dots (2026-10-22)."""
                p.fillRect(clip, QtGui.QColor(look.FEED_BG))
                side = max(4, int(hubstyle.px(look.PATTERN, self.win.scale)))
                if self._tile is None or self._tile.width() != side:
                    tile = QtGui.QPixmap(side, side)
                    tile.fill(QtCore.Qt.transparent)
                    tp = QtGui.QPainter(tile)
                    try:
                        tp.setRenderHint(QtGui.QPainter.Antialiasing)
                        tp.setPen(QtCore.Qt.NoPen)
                        r = max(0.8, self.win.scale)
                        tp.setBrush(QtGui.QColor(255, 255, 255, 13))
                        tp.drawEllipse(QtCore.QPointF(r + 0.5, r + 0.5), r, r)
                        tp.setBrush(_colour("accent", 0.06))
                        tp.drawEllipse(QtCore.QPointF(side / 2.0 + r, side / 2.0 + r), r, r)
                    finally:
                        tp.end()
                    self._tile = tile
                p.fillRect(clip, QtGui.QBrush(self._tile))

            def _dark_pill(self, p, rect):
                p.setPen(QtGui.QPen(QtGui.QColor("#2c2e33"), 1))
                p.setBrush(QtGui.QColor(16, 17, 19, 204))
                p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5),
                                  rect.height() / 2.0, rect.height() / 2.0)

            def _paint_call(self, p, box, item):
                """A call's line: a dark pill, the phone drawn (green, missed red), its text and
                time."""
                px = lambda n: hubstyle.px(n, self.win.scale)      # noqa: E731
                from . import emojiart
                pill = box.callpill
                self._dark_pill(p, pill)
                ink = "danger" if item.missed else "ok"
                side = px(14)
                pic = hubqt.pixmap("phone", hubstyle.TOKENS[ink], side)
                x = pill.left() + px(12)
                p.drawPixmap(QtCore.QRectF(x, pill.center().y() - side / 2.0, side, side), pic,
                             QtCore.QRectF(pic.rect()))
                x += side + px(6)
                font = _font(self.font(), px(9.5), True)
                tw = emojiart.line_width(item.text, font)
                emojiart.draw_line(p, QtCore.QRectF(x, pill.top(), tw + 1, pill.height()),
                                   item.text, font, _colour("danger" if item.missed else "text"))
                p.setFont(_font(self.font(), px(9.5)))
                p.setPen(_colour("muted"))
                p.drawText(QtCore.QRectF(x + tw + px(8), pill.top(), pill.right() - x - tw,
                                         pill.height()),
                           QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
                           look.hm(item.message.get("at") or _now_ms()))

            def _bubble_path(self, bubble, mine, tail):
                """A bubble: radius 12; the last of a run square at the sender's bottom corner
                with Telegram's curl (the mockup's 9 x 14 tail, 2026-10-22)."""
                px = lambda n: hubstyle.px(n, self.win.scale)      # noqa: E731
                r = px(12)
                path = QtGui.QPainterPath()
                path.addRoundedRect(bubble, r, r)
                if not tail:
                    return path
                k = self.win.scale
                corner = QtGui.QPainterPath()
                corner.addRect(QtCore.QRectF(bubble.right() - r if mine else bubble.left(),
                                             bubble.bottom() - r, r, r))
                curl = QtGui.QPainterPath()
                bottom, top = bubble.bottom(), bubble.bottom() - 14 * k
                if mine:
                    x0 = bubble.right()
                    curl.moveTo(x0 - 0.4 * k, top + 0.5 * k)
                    curl.cubicTo(x0 + 0.4 * k - 0.4 * k, top + 7.5 * k,
                                 x0 + 4.0 * k, top + 12.0 * k, x0 + 8.6 * k, bottom)
                    curl.lineTo(x0 - 0.4 * k, bottom)
                else:
                    x0 = bubble.left()
                    curl.moveTo(x0 + 0.4 * k, top + 0.5 * k)
                    curl.cubicTo(x0, top + 7.5 * k, x0 - 4.0 * k, top + 12.0 * k,
                                 x0 - 8.6 * k, bottom)
                    curl.lineTo(x0 + 0.4 * k, bottom)
                curl.closeSubpath()
                return path.united(corner).united(curl)

            def _paint_meta(self, p, box, font):
                """The time and the drawn ticks: inside the bubble (mine in `MINE_META`, read
                in `accent_text`), or in a dark pill under emoji alone."""
                if box.meta_at is None:
                    return
                s = self.win.scale
                item = box.item
                fm = QtGui.QFontMetrics(font)
                if box.meta_pill is not None:
                    self._dark_pill(p, box.meta_pill)
                    ink = "#c9cacf"
                else:
                    ink = look.MINE_META if item.mine else hubstyle.TOKENS["muted"]
                p.setFont(font)
                p.setPen(QtGui.QColor(ink))
                p.drawText(box.meta_at, box.meta)
                tick = item.tick
                if tick:
                    colour = {"read": hubstyle.TOKENS["accent_text"],
                              "failed": hubstyle.TOKENS["danger"]}.get(tick, ink)
                    right = box.meta_at.x() + fm.horizontalAdvance(box.meta) + \
                        hubstyle.px(3, s) + tick_width(tick, s)
                    paint_ticks(p, right, box.meta_at.y() - fm.ascent() * 0.36, tick, colour, s)

            def _reply_rect(self, box):
                """The reply button beside a bubble (look A): a 26 px circle 8 px out."""
                px = lambda n: hubstyle.px(n, self.win.scale)      # noqa: E731
                b = box.bubble
                side = px(26)
                x = b.left() - px(8) - side if box.item.mine else b.right() + px(8)
                return QtCore.QRectF(x, b.center().y() - side / 2.0, side, side)

            def _paint_reply_button(self, p, box):
                s = self.win.scale
                rect = self._reply_rect(box)
                level = self.reply_level
                p.save()
                p.setOpacity(p.opacity() * level)
                hot = self.reply_hot
                if hot:
                    for grow, alpha in ((3.0, 0.08), (1.6, 0.16)):
                        p.setPen(QtCore.Qt.NoPen)
                        p.setBrush(_colour("accent", alpha))
                        g = grow * s
                        p.drawEllipse(rect.adjusted(-g, -g, g, g))
                p.setPen(QtGui.QPen(_colour("accent", 0.6) if hot else QtGui.QColor("#3a3c42"),
                                    max(1.0, s)))
                p.setBrush(_colour("card"))
                c = rect.center()
                lift = 1.1 if hot else 1.0
                r = QtCore.QRectF(0, 0, rect.width() * lift, rect.height() * lift)
                r.moveCenter(c)
                p.drawEllipse(r)
                side = hubstyle.px(15, s)
                pic = hubqt.pixmap("corner-up-left",
                                   hubstyle.TOKENS["text" if hot else "muted"], side)
                p.drawPixmap(QtCore.QRectF(c.x() - side / 2.0, c.y() - side / 2.0, side, side),
                             pic, QtCore.QRectF(pic.rect()))
                p.restore()

            # ---------------------------------------------------------- input
            def hover_box(self):
                if self.hover_key is None:
                    return None
                return next((b for b in self.boxes if b.item.kind == "msg"
                             and b.item.key() == self.hover_key), None)

            def box_at(self, point):
                hovered = self.hover_box()
                if hovered is not None and self.reply_level > 0.01 \
                        and self._reply_rect(hovered).contains(point):
                    return hovered, "reply"
                for box in self.boxes:
                    if box.callpill is not None:
                        if box.callpill.contains(point):
                            return box, "call"
                        continue
                    if box.avatar is not None and box.avatar.contains(point):
                        return box, "avatar"
                    for rect, action, _label in box.fbuttons:
                        if rect.contains(point):
                            return box, "file:" + action
                    if box.thumb is not None and box.thumb.contains(point):
                        return box, "thumb"
                    if box.card is not None and box.card.contains(point):
                        return box, "card"
                    for rect, e, _n, _me in box.pills:
                        if rect.contains(point):
                            return box, "pill:" + e
                    for rect, glyph in box.bigs:
                        if rect.contains(point):
                            return box, "big:" + glyph
                    if box.bubble is not None and box.bubble.contains(point):
                        return box, "bubble"
                    if box.failed_rect is not None and box.failed_rect.contains(point):
                        return box, "failed"
                return None, ""

            def mousePressEvent(self, event):              # noqa: N802
                pos = event.position() if hasattr(event, "position") else QtCore.QPointF(event.pos())
                gp = event.globalPosition().toPoint() if hasattr(event, "globalPosition") \
                    else event.globalPos()
                if self._dragging:
                    self._end_drag(gp, cancel=event.button() != QtCore.Qt.LeftButton)
                    return
                box, where = self.box_at(pos)
                if box is None:
                    return
                if where == "reply":
                    if event.button() == QtCore.Qt.LeftButton:
                        self.win.start_reply(box.item.message)
                    return
                if where == "call":
                    if event.button() == QtCore.Qt.LeftButton:
                        note = records.call_note(box.item.message.get("call")) or {}
                        self.win.start_call(note.get("kind") or "audio",
                                            box.item.message.get("chat"))
                    return
                if event.button() == QtCore.Qt.RightButton:
                    self.win.message_menu(box.item, gp)
                    return
                if event.button() != QtCore.Qt.LeftButton:
                    return
                if where == "avatar" or (box.name_at is not None and where == "bubble"
                                         and pos.y() < box.name_at.y() + px_of(self, 2)
                                         and pos.y() > box.name_at.y() - px_of(self, 14)):
                    uid = box.item.message.get("from_id")
                    if self.win.show_profile(self.ctx.get("user_of", lambda u: {"id": u})(uid)):
                        return
                if where.startswith("file:"):
                    self.win.file_action(box.item, where[5:], gp)
                    return
                if where in ("card", "thumb") and not box.item.pending:
                    from . import files as _files
                    f = box.item.message.get("file") or {}
                    if _files.is_image(f):
                        if where == "thumb":
                            self.win.file_action(box.item, "view", gp)
                        return
                    self._press = (QtCore.QPointF(pos), box.item)
                    return
                if where == "failed":
                    self.win.retry(box.item)
                    return
                if where.startswith("pill:"):
                    self.win.react(box.item.message, where[5:])
                    return
                if box.quote is not None and box.quote[0].contains(pos):
                    self.win.scroll_to_message(box.quote[1])
                    return
                if box.doc is not None:
                    local = pos - box.doc_at
                    href = box.doc.documentLayout().anchorAt(local)
                    if href:
                        QtGui.QDesktopServices.openUrl(QtCore.QUrl(href))

            def mouseMoveEvent(self, event):              # noqa: N802
                pos = event.position() if hasattr(event, "position") else QtCore.QPointF(event.pos())
                gp = event.globalPosition().toPoint() if hasattr(event, "globalPosition") \
                    else event.globalPos()
                if self._dragging:
                    self.win.drag_move(gp)
                    return
                if self._press is not None and event.buttons() & QtCore.Qt.LeftButton:
                    start, item = self._press
                    moved = (pos - start).manhattanLength()
                    if moved >= QtWidgets.QApplication.startDragDistance():
                        self._press = None
                        if self.win.start_drag(item, gp):
                            self._dragging = True
                            self.grabMouse()
                        return
                self._hover_row(pos)
                box, _where = self.box_at(pos)
                self._hover_emoji(box, _where)
                self._hover_preview(box if _where == "thumb" else None)
                if _where == "reply":
                    self.setCursor(QtCore.Qt.PointingHandCursor)
                    return
                hover = None
                if _where.startswith("file:"):
                    hover = (id(box.item.message), _where[5:])
                if hover != self._hover_button:
                    self._hover_button = hover
                    self.update()
                link = _where.startswith("pill:") or _where.startswith("file:")
                if box is not None and box.doc is not None and not link:
                    link = bool(box.doc.documentLayout().anchorAt(pos - box.doc_at))
                    link = link or (box.quote is not None and box.quote[0].contains(pos))
                self.setCursor(QtCore.Qt.PointingHandCursor if link else QtCore.Qt.ArrowCursor)

            def mouseReleaseEvent(self, event):            # noqa: N802
                gp = event.globalPosition().toPoint() if hasattr(event, "globalPosition") \
                    else event.globalPos()
                self._press = None
                if self._dragging:
                    self._end_drag(gp, cancel=event.button() != QtCore.Qt.LeftButton)

            def _end_drag(self, gp, cancel):
                self._dragging = False
                try:
                    self.releaseMouse()
                except Exception:                            # noqa: BLE001
                    pass
                self.win.drag_end(gp, cancel)

            def _hover_preview(self, box):
                """An animation's preview plays while the mouse is on it."""
                from . import thumbs
                key = None
                if box is not None and thumbs.sheet_of(box.item.message.get("file")) is not None:
                    key = box.item.key()
                if key == (self.playing[0] if self.playing else None):
                    return
                self.playing = (key, _now_ms()) if key else None
                if self.playing:
                    self.win.animate()
                self.update()

            def _hover_emoji(self, box, where):
                """The mouse entering an animated emoji (a big one, a pill) plays it again."""
                hit = None
                if box is not None and (where.startswith("big:") or where.startswith("pill:")):
                    kind, glyph = where.split(":", 1)
                    hit = (box.item.key(), glyph, kind)
                if hit != self._emoji_hover:
                    self._emoji_hover = hit
                    if hit is not None and hit not in self.plays:
                        self._start(hit, hit[1])

            def _hover_row(self, pos):
                """The message whose row the mouse is on shows its reply button (look A)."""
                key, hot = None, False
                for box in self.boxes:
                    if box.item.kind == "msg" and box.rect.top() <= pos.y() < box.rect.bottom():
                        if not box.item.pending:
                            key = box.item.key()
                            hot = self._reply_rect(box).contains(pos)
                        break
                if key != self.hover_key or hot != self.reply_hot:
                    self.hover_key, self.reply_hot = key, hot
                    self.win.animate()
                    self.update()

            def leaveEvent(self, event):                   # noqa: N802
                self._emoji_hover = None
                self._hover_preview(None)
                if self.hover_key is not None:
                    self.hover_key, self.reply_hot = None, False
                    self.win.animate()
                super(Feed, self).leaveEvent(event)

            def top_of(self, message_id):
                for box in self.boxes:
                    if box.item.kind == "msg" and box.item.message.get("id") == message_id:
                        return box.rect.top()
                return None

        _CLASSES["feed"] = Feed
    return _CLASSES["feed"]


# ------------------------------------------------------------------ the emoji picker

PICK_COLS = 9
PICK_ROWS = 8
PICK_CELL = 32
PICK_HEAD = 18        # a section's title row
PICK_LIFT = 1.10      # a cell under the mouse grows 10 % (the Time Bar's hover)
PICK_GLOW = 0.35      # the accent glow's alpha at a lit cell's centre
PICK_TONES = ("#ffc93a", "#f7d7c4", "#e0b291", "#bf8f68", "#9b643d", "#594539")


def picker_class():
    """EmojiPicker(window, picked): a search field over tone swatches, group tabs and a
    scrolling painted grid; a click (or Enter on the search) calls picked(emoji) and closes it."""
    if "picker" not in _CLASSES:
        q = _q()
        QtCore, QtGui, QtWidgets = q.QtCore, q.QtGui, q.QtWidgets
        from . import emoji as _emoji
        from . import emojiart

        class Search(QtWidgets.QLineEdit):
            def __init__(self, picker):
                super(Search, self).__init__(picker)
                self.picker = picker

            def keyPressEvent(self, event):                # noqa: N802
                if event.key() == QtCore.Qt.Key_Escape:
                    if self.text():
                        self.clear()
                    else:
                        self.picker.close()
                    return
                if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
                    items = self.picker.items()
                    if items:
                        self.picker.pick(items[0])
                    return
                super(Search, self).keyPressEvent(event)

        class EmojiPicker(QtWidgets.QWidget):

            def __init__(self, win, picked, parent=None):
                super(EmojiPicker, self).__init__(parent or win.root,
                                                  QtCore.Qt.Popup | QtCore.Qt.FramelessWindowHint)
                self.win, self.picked = win, picked
                self.setObjectName("skeldarChatEmojiPicker")
                self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
                self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
                self.setMouseTracking(True)
                px = win.px
                self.pad = px(8)
                self.cell = px(PICK_CELL)
                self.head = px(PICK_HEAD)
                self.idx = _emoji.index()
                try:
                    self.tone = int(get_var(_emoji.TONE_VAR) or 0)
                except (TypeError, ValueError):
                    self.tone = 0
                self.query = ""
                self.scroll = 0.0
                self.hover = None
                self.levels = {}          # hovered cell -> its lift, 0..1
                self._last = time.monotonic()
                self.timer = QtCore.QTimer(self)
                self.timer.setInterval(TICK_MS)
                self.timer.timeout.connect(self._tick)
                width = 2 * self.pad + PICK_COLS * self.cell
                self.search = Search(self)
                self.search.setObjectName("skeldarChatEmojiSearch")
                self.search.setPlaceholderText(u"Поиск: кот, огонь, fire…")
                self.search.setGeometry(self.pad, self.pad, width - 2 * self.pad, px(26))
                self.search.textChanged.connect(self.set_query)
                self.top_tones = self.pad + px(26) + px(6)
                self.top_tabs = self.top_tones + px(20)
                self.top_grid = self.top_tabs + self.cell + px(4)
                self.setFixedSize(width, self.top_grid + PICK_ROWS * self.cell + self.pad)
                self.font_ = QtGui.QFont(self.font())
                self.font_.setFamilies([self.font_.family(), _emoji.FONT])
                self.font_.setPixelSize(px(19))
                self._layout()
                self.search.setFocus()

            # ------------------------------------------------------ what is listed
            def _glyph(self, rec):
                return _emoji.toned(rec, self.tone)[0]

            def sections(self):
                """[(key, title, [glyph])] as last laid out."""
                return self._sections

            def _fresh_sections(self):
                """The results of a search, else Recent and the groups."""
                if self.query.strip():
                    return [("found", u"Найдено",
                             [self._glyph(r) for r in _emoji.search(self.query, idx=self.idx)])]
                out = [("recent", u"Недавние", _emoji.recent(get_var(_emoji.RECENT_VAR)))]
                for key, _tab, title in self.idx.groups:
                    out.append((key, title, [self._glyph(r) for r in self.idx.of_group(key)]))
                return out

            def items(self):
                return [g for _k, _t, glyphs in self.sections() for g in glyphs]

            def _layout(self):
                """Each section's top and each cell's rect, in grid coordinates (scroll 0)."""
                self._sections = self._fresh_sections()
                self.tops, self.cells, y = {}, [], 0
                for key, title, glyphs in self._sections:
                    self.tops[key] = y
                    y += self.head
                    for i, g in enumerate(glyphs):
                        self.cells.append((QtCore.QRectF(self.pad + (i % PICK_COLS) * self.cell,
                                                         y + (i // PICK_COLS) * self.cell,
                                                         self.cell, self.cell), g))
                    y += ((len(glyphs) + PICK_COLS - 1) // PICK_COLS) * self.cell
                self.height_ = y
                self.scroll = max(0.0, min(self.scroll, self.max_scroll()))
                self.update()

            def max_scroll(self):
                return max(0.0, self.height_ - PICK_ROWS * self.cell)

            def section_top(self, key):
                return self.tops.get(key, 0)

            def scroll_to(self, key):
                self.scroll = max(0.0, min(float(self.section_top(key)), self.max_scroll()))
                self.update()

            def set_query(self, text):
                self.query = text or ""
                if self.search.text() != self.query:
                    self.search.setText(self.query)
                self.scroll = 0.0
                self._layout()

            def set_tone(self, tone):
                self.tone = max(0, min(5, int(tone)))
                set_var(_emoji.TONE_VAR, str(self.tone))
                self._layout()

            # ------------------------------------------------------ hits
            def _tabs(self):
                keys = ["recent"] + [g[0] for g in self.idx.groups]
                glyphs = [u"\U0001F558"] + [g[1] for g in self.idx.groups]
                return [(QtCore.QRectF(self.pad + i * self.cell, self.top_tabs, self.cell,
                                       self.cell), k, g)
                        for i, (k, g) in enumerate(zip(keys, glyphs))]

            def _tone_rects(self):
                s = self.win.px(14)
                return [(QtCore.QRectF(self.pad + i * (s + self.win.px(6)),
                                       self.top_tones + self.win.px(3), s, s), i)
                        for i in range(6)]

            def hit(self, pos):
                for rect, t in self._tone_rects():
                    if rect.contains(pos):
                        return ("tone", t)
                for rect, key, _g in self._tabs():
                    if rect.contains(pos):
                        return ("tab", key)
                if pos.y() < self.top_grid or pos.y() > self.top_grid + PICK_ROWS * self.cell:
                    return None
                gp = QtCore.QPointF(pos.x(), pos.y() - self.top_grid + self.scroll)
                for rect, g in self.cells:
                    if rect.contains(gp):
                        return ("emoji", g)
                return None

            # ------------------------------------------------------ input
            def wheelEvent(self, event):                   # noqa: N802
                dy = event.angleDelta().y()
                self.scroll = max(0.0, min(self.scroll - dy / 120.0 * self.cell * 1.5,
                                           self.max_scroll()))
                where = (event.position() if hasattr(event, "position")
                         else QtCore.QPointF(event.pos()))
                self._rehover(where)
                self.update()

            def _rehover(self, pos):
                h = self.hit(pos)
                if h != self.hover:
                    self.hover = h
                    if h is not None and h[0] == "emoji" and not hubmotion.enabled():
                        self.levels = {h: 1.0}
                    self._wake()

            def mouseMoveEvent(self, event):              # noqa: N802
                pos = event.position() if hasattr(event, "position") else QtCore.QPointF(event.pos())
                self._rehover(pos)
                self.update()

            def leaveEvent(self, event):                   # noqa: N802
                self.hover = None
                self._wake()

            def hideEvent(self, event):                    # noqa: N802
                emojiart.release()
                super(EmojiPicker, self).hideEvent(event)

            def mousePressEvent(self, event):              # noqa: N802
                pos = event.position() if hasattr(event, "position") else QtCore.QPointF(event.pos())
                if not self.rect().contains(pos.toPoint()):
                    self.close()
                    return
                h = self.hit(pos)
                if h is None:
                    return
                if h[0] == "tone":
                    self.set_tone(h[1])
                elif h[0] == "tab":
                    if self.query:
                        self.set_query("")
                    self.scroll_to(h[1])
                else:
                    self.pick(h[1])

            def pick(self, e):
                self.close()
                try:
                    self.picked(e)
                except Exception:                            # noqa: BLE001
                    traceback.print_exc()

            # ------------------------------------------------------ motion
            def _wake(self):
                if hubmotion.enabled() and not self.timer.isActive():
                    self._last = time.monotonic()
                    self.timer.start()
                elif not hubmotion.enabled():
                    self.levels = {self.hover: 1.0} if self.hover else {}
                    self.update()

            def _tick(self):
                now = time.monotonic()
                dt = (now - self._last) * 1000.0
                self._last = now
                keys = set(self.levels) | ({self.hover} if self.hover else set())
                busy = False
                for k in keys:
                    goal = 1.0 if k == self.hover else 0.0
                    v = look_approach(self.levels.get(k, 0.0), goal, dt, HOVER_MS)
                    if v <= 0.0:
                        self.levels.pop(k, None)
                    else:
                        self.levels[k] = v
                    busy = busy or v != goal
                self.update()
                if not busy:
                    self.timer.stop()

            # ------------------------------------------------------ paint
            def paintEvent(self, event):                   # noqa: N802
                p = QtGui.QPainter(self)
                try:
                    self._paint(p)
                except Exception:                            # noqa: BLE001
                    traceback.print_exc()
                finally:
                    p.end()

            def _glow(self, p, rect, lift):
                """The Time Bar's hover glow: added accent light, brightest at the cell's
                centre, never past the cell."""
                p.save()
                try:
                    p.setClipRect(rect, QtCore.Qt.IntersectClip)
                    grad = QtGui.QRadialGradient(rect.center(), rect.width() / 2.0)
                    grad.setColorAt(0.0, _colour("accent", PICK_GLOW * lift))
                    grad.setColorAt(1.0, _colour("accent", 0.0))
                    p.setCompositionMode(QtGui.QPainter.CompositionMode_Plus)
                    p.setPen(QtCore.Qt.NoPen)
                    p.setBrush(QtGui.QBrush(grad))
                    p.drawRect(rect)
                finally:
                    p.restore()

            def _active_tab(self):
                if self.query:
                    return None
                active = "recent"
                for key, top in sorted(self.tops.items(), key=lambda kv: kv[1]):
                    if top <= self.scroll + 1:
                        active = key
                return active

            def _paint(self, p):
                px = self.win.px
                p.setRenderHint(QtGui.QPainter.Antialiasing)
                p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
                p.setPen(QtGui.QPen(_colour("line"), 1))
                p.setBrush(_colour("panel"))
                p.drawRoundedRect(QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5),
                                  px(8), px(8))
                for rect, t in self._tone_rects():
                    p.setPen(QtGui.QPen(_colour("accent") if t == self.tone else _colour("line"),
                                        px(1.5) if t == self.tone else 1))
                    p.setBrush(QtGui.QColor(PICK_TONES[t]))
                    p.drawEllipse(rect)
                active = self._active_tab()
                for rect, key, glyph in self._tabs():
                    if key == active:
                        p.setPen(QtCore.Qt.NoPen)
                        p.setBrush(_colour("card_active"))
                        p.drawRoundedRect(rect.adjusted(1, 1, -1, -1), px(6), px(6))
                        p.setPen(QtGui.QPen(_colour("accent"), 1.5))
                        p.drawLine(QtCore.QPointF(rect.left() + px(6), rect.bottom() - 1),
                                   QtCore.QPointF(rect.right() - px(6), rect.bottom() - 1))
                    elif self.hover == ("tab", key):
                        p.setPen(QtCore.Qt.NoPen)
                        p.setBrush(_colour("hover"))
                        p.drawRoundedRect(rect.adjusted(1, 1, -1, -1), px(6), px(6))
                    pm = emojiart.pixmap(glyph, px(20))
                    if pm is not None:
                        p.drawPixmap(rect.center() - QtCore.QPointF(px(10), px(10)), pm)
                    else:
                        p.setFont(self.font_)
                        p.setPen(_colour("text"))
                        p.drawText(rect, QtCore.Qt.AlignCenter, glyph)
                grid = QtCore.QRectF(0, self.top_grid, self.width(), PICK_ROWS * self.cell)
                p.save()
                p.setClipRect(grid)
                p.translate(0, self.top_grid - self.scroll)
                title_font = _font(self.font(), px(9), True)
                for key, title, glyphs in self.sections():
                    top = self.tops[key]
                    p.setFont(title_font)
                    p.setPen(_colour("muted"))
                    p.drawText(QtCore.QRectF(self.pad, top, self.width() - 2 * self.pad, self.head),
                               QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, title.upper())
                    if not glyphs and key == "found":
                        p.drawText(QtCore.QRectF(self.pad, top + self.head,
                                                 self.width() - 2 * self.pad, self.cell),
                                   QtCore.Qt.AlignCenter, u"Ничего не нашлось")
                lo, hi = self.scroll - self.cell, self.scroll + grid.height() + self.cell
                side = px(24)
                for rect, g in self.cells:
                    if rect.bottom() < lo or rect.top() > hi:
                        continue
                    lift = self.levels.get(("emoji", g), 0.0)
                    if lift > 0.0:
                        p.setPen(QtCore.Qt.NoPen)
                        p.setBrush(_colour("hover", lift))
                        p.drawRoundedRect(rect.adjusted(1, 1, -1, -1), px(6), px(6))
                        self._glow(p, rect, lift)
                    k = 1.0 + (PICK_LIFT - 1.0) * lift
                    s = side * k
                    target = QtCore.QRectF(rect.center().x() - s / 2.0, rect.center().y() - s / 2.0, s, s)
                    pm = emojiart.pixmap(g, int(round(side * PICK_LIFT)))
                    if pm is not None:
                        p.drawPixmap(target, pm, QtCore.QRectF(pm.rect()))
                    else:
                        p.setFont(self.font_)
                        p.setPen(_colour("text"))
                        p.drawText(rect, QtCore.Qt.AlignCenter, g)
                p.restore()

        _CLASSES["picker"] = EmojiPicker
    return _CLASSES["picker"]


# ------------------------------------------------------------------ the composer

def composer_class():
    if "composer" not in _CLASSES:
        q = _q()
        QtCore, QtWidgets = q.QtCore, q.QtWidgets

        class Composer(QtWidgets.QPlainTextEdit):

            def __init__(self, win, parent=None):
                super(Composer, self).__init__(parent)
                self.win = win
                self.setObjectName("skeldarChatComposer")
                self.setPlaceholderText("Сообщение")
                self.setFont(_font(self.font(), hubstyle.px(11.5, win.scale)))
                self.setTabChangesFocus(True)
                self.document().contentsChanged.connect(self._grow)
                self._grow()

            def _grow(self):
                # Every line plus what stands around them: the document's own
                # margin (top and bottom) and the frame, border and padding the
                # stylesheet gives (contentsMargins). Leaving the document margin
                # out clipped the one line by 8 px at the bottom.
                lines = max(1, min(look.MAX_LINES, int(self.document().size().height())))
                #  a scroll bar only once the text is past what the field grows to (look A:
                #  its handle stood in the round field on one line)
                self.setVerticalScrollBarPolicy(
                    QtCore.Qt.ScrollBarAsNeeded
                    if self.document().size().height() > look.MAX_LINES
                    else QtCore.Qt.ScrollBarAlwaysOff)
                fm = self.fontMetrics()
                m = self.contentsMargins()
                v = self.viewportMargins()
                doc = 2 * self.document().documentMargin()
                frame = m.top() + m.bottom() + v.top() + v.bottom()
                self.setFixedHeight(int(math.ceil(lines * fm.lineSpacing() + doc + frame)))

            def changeEvent(self, event):                  # noqa: N802
                super(Composer, self).changeEvent(event)
                if event.type() in (QtCore.QEvent.StyleChange, QtCore.QEvent.FontChange):
                    self._grow()

            def showEvent(self, event):                    # noqa: N802
                super(Composer, self).showEvent(event)
                self._grow()

            def focusInEvent(self, event):                 # noqa: N802
                super(Composer, self).focusInEvent(event)
                self.win._field_lit(True)

            def focusOutEvent(self, event):                # noqa: N802
                super(Composer, self).focusOutEvent(event)
                self.win._field_lit(False)

            def keyPressEvent(self, event):                # noqa: N802
                key = event.key()
                mods = event.modifiers()
                if key in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter) \
                        and not mods & QtCore.Qt.ShiftModifier:
                    self.win.send_now()
                    return
                if key == QtCore.Qt.Key_Up and not self.toPlainText():
                    if self.win.edit_last():
                        return
                if key == QtCore.Qt.Key_Escape:
                    if self.win.cancel_bar():
                        return
                super(Composer, self).keyPressEvent(event)

            def canInsertFromMimeData(self, source):       # noqa: N802
                if source is not None and (source.hasImage() or self.win.sendable(source)):
                    return True
                return super(Composer, self).canInsertFromMimeData(source)

            def insertFromMimeData(self, source):          # noqa: N802
                """Ctrl+V (or a drop) of a picture or of files: they go into the chat; text is
                text (2026-10-22: «кидать в чат картинки просто через ctrl + v»)."""
                paths = self.win.sendable(source)
                if paths:
                    self.win.dropped(paths)
                    return
                if source is not None and source.hasImage():
                    self.win.send_image(source.imageData())
                    return
                super(Composer, self).insertFromMimeData(source)

        _CLASSES["composer"] = Composer
    return _CLASSES["composer"]


# ------------------------------------------------------------------ the window

def _button(text, role=None, icon_name=None, name=None, scale=1.0, tip=None):
    q = _q()
    b = q.QtWidgets.QPushButton(text)
    if name:
        b.setObjectName(name)
    if role:
        b.setProperty("skRole", role)
    if icon_name:
        colour = hubstyle.TOKENS["on_accent"] if role == "primary" else hubstyle.TOKENS["text2"]
        b.setIcon(hubqt.icon(icon_name, colour, hubstyle.px(14, scale)))
    if tip:
        b.setToolTip(tip)
    b.setCursor(q.QtCore.Qt.PointingHandCursor)
    b.setMinimumHeight(hubstyle.px(24, scale))
    return b


MENU_ICONS = {u"Ответить": "corner-up-left", u"Скопировать": "copy", u"Изменить": "pencil",
              u"Удалить": "trash", u"Реакция…": "mood-smile", u"Повторить": "refresh",
              "Open": "folder", "Import": "download", u"Открыть": "folder",
              u"Сохранить как…": "device-floppy", u"В Stash": "archive",
              u"Отправить сцену": "upload", u"Отправить выделенное (FBX)": "focus-2",
              u"Отправить файл…": "paperclip"}


def _menu_icon(action, label, scale):
    """A menu row's Tabler icon (look A, 2026-10-22); Удалить's in `danger`."""
    name = MENU_ICONS.get(label)
    if name:
        colour = hubstyle.TOKENS["danger" if label == u"Удалить" else "text2"]
        action.setIcon(hubqt.icon(name, colour, hubstyle.px(14, scale)))


def look_a_sheet(scale):
    """The window's own rules over the hub's stylesheet (look A, 2026-10-22, spec
    2026-10-22-chat-look-telegram-design.md): the two columns on `panel`, a round search
    field, the header and the composer on `panel` with a hairline, a round field holding the
    text, a round send button that turns orange with text. Lengths are physical (trap 98)."""
    t = hubstyle.TOKENS
    px = lambda n: hubstyle.px(n, scale)                    # noqa: E731
    lit = "rgba(224,122,54,180)"
    return "\n".join([
        "#skeldarChatFrame { border: none; background: transparent; }",
        "QScrollArea { background: transparent; border: none; }",
        "#skeldarChatList, #skeldarChatFeed, #skeldarChatNewBody, #skeldarChatMembersBody,"
        " #skeldarChatViewport { background: transparent; }",
        "#skeldarChatLeft, #skeldarChatRight { background: %s; }" % t["panel"],
        "#skeldarChatSplit { background: %s; }" % hubwindow.EDGE,
        "QLineEdit#skeldarChatSearch { background: %s; color: %s; border: 1px solid %s;"
        " border-radius: %dpx; padding: 0 %dpx 0 %dpx; min-height: %dpx; }"
        % (t["field"], t["text"], t["track_edge"], px(15), px(10), px(2), px(28)),
        "QLineEdit#skeldarChatSearch:focus { border: 1px solid %s; }" % lit,
        "#skeldarChatHead { background: %s; border: none; border-bottom: 1px solid %s; }"
        % (t["panel"], t["track_edge"]),
        "#skeldarChatCompose { background: %s; border: none; border-top: 1px solid %s; }"
        % (t["panel"], t["track_edge"]),
        "#skeldarChatField { background: %s; border: 1px solid %s; border-radius: %dpx; }"
        % (t["field"], t["track_edge"], px(17)),
        "#skeldarChatField[skFocus=\"true\"] { border: 1px solid %s; }" % lit,
        "QPlainTextEdit#skeldarChatComposer { background: transparent; color: %s;"
        " border: none; padding: %dpx 0 %dpx 0; }" % (t["text"], px(3), px(3)),
        "QPushButton#skeldarChatEmoji { background: transparent; border: none;"
        " border-radius: %dpx; min-width: %dpx; max-width: %dpx; min-height: %dpx;"
        " max-height: %dpx; padding: 0; }" % (px(14), px(28), px(28), px(28), px(28)),
        "QPushButton#skeldarChatEmoji:hover { background: %s; }" % t["hover"],
        "QPushButton#skeldarChatSend { background: #2c2e33; border: none; border-radius: %dpx;"
        " min-width: %dpx; max-width: %dpx; min-height: %dpx; max-height: %dpx; padding: 0; }"
        % (px(17), px(34), px(34), px(34), px(34)),
        "QPushButton#skeldarChatSend[skState=\"ready\"] { background: %s; }" % t["accent"],
        "QPushButton#skeldarChatSend[skState=\"ready\"]:hover { background: %s;"
        " border: 1px solid %s; }" % (t["accent_hover"], hubstyle.TOKENS.get("rim", "#fff1e2")),
        "QPushButton#skeldarChatDown { background: %s; color: %s; border: 1px solid %s;"
        " border-radius: %dpx; min-width: %dpx; min-height: %dpx; max-height: %dpx;"
        " padding: 0 %dpx; font-weight: bold; }"
        % (t["card"], t["text"], t["line"], px(18), px(36), px(36), px(36), px(8)),
        "QPushButton#skeldarChatDown:hover { border: 1px solid %s; }" % t["accent"],
        "#skeldarChatBar { background: transparent; }",
        "#skeldarChatBarQuote { background: rgba(255,255,255,13); border-radius: %dpx; }"
        % px(6),
        "#skeldarChatBarText { color: #c9cacf; }",
    ])


def _label(text="", role=None, name=None, wrap=False):
    q = _q()
    lab = q.QtWidgets.QLabel(text)
    if name:
        lab.setObjectName(name)
    if role:
        lab.setProperty("skRole", role)
    lab.setWordWrap(wrap)
    return lab


class ChatWindow(object):
    """The messenger's window over one session."""

    def __init__(self, session, scale=None):
        self.session = session
        self.scale = float(scale or _scale())
        self.chat = None             # the open chat's id
        self.pane = "chat"           # chat | new | settings | members
        self.single = "list"         # in one column: list | right
        self.reply_to = None         # a message id
        self.editing = None          # a message id
        self.query = ""
        self.history_done = set()
        self.unseen = 0              # messages that came while scrolled up
        self.unread_from = None      # (chat, message id): where the unread band stands
        self._dirty = False
        self._last_tick = None
        self.root = None
        self.burster = None
        self.avatars = None
        self.profile = None          # a person's card standing over the window
        try:
            from . import avatars
            self.avatars = avatars.cache(session)
        except Exception:                                    # noqa: BLE001
            traceback.print_exc()
        self._build()
        self.session.listen(self._heard)
        self.refresh()

    def px(self, n):
        return hubstyle.px(n, self.scale)

    # ---------------------------------------------------------- build
    def _build(self):
        q = _q()
        w, Qt = q.QtWidgets, q.QtCore.Qt
        s = self.scale
        px = self.px
        root = w.QWidget(_main_window(), Qt.Tool | Qt.FramelessWindowHint)
        root.setObjectName(ROOT_NAME)
        root.setAttribute(Qt.WA_TranslucentBackground, True)
        root.setMinimumSize(px(look.LEAST_SIZE[0]), px(look.LEAST_SIZE[1]))
        outer = w.QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        frame = hubqt._named(hubwindow.frame_class()(s), "skeldarChatFrame")
        outer.addWidget(frame)
        self.frame = frame
        column = w.QVBoxLayout(frame)
        column.setContentsMargins(px(5), 0, px(5), px(5))
        column.setSpacing(0)

        import maya_hubpop
        title = maya_hubpop._title_class()(self._grab, self._drag, self._drop, lambda: None, frame)
        title.setObjectName("skeldarChatTitle")
        title.setFixedHeight(px(hubwindow.TITLE_H))
        row = w.QHBoxLayout(title)
        row.setContentsMargins(px(5), 0, 0, 0)
        row.setSpacing(px(6))
        colour = hubstyle.group("scene").colour
        row.addWidget(hubwindow.title_icon("message-circle", colour, s, "skeldarChatIcon"))
        row.addWidget(hubwindow.title_label("Chat", s, "skeldarChatName"))
        self.state_label = _label("", "subtitle", "skeldarChatState")
        row.addWidget(self.state_label, 1)
        close = hubqt._named(hubwindow.pill_class()("x", s), "skeldarChatClose")
        close.setToolTip("Закрыть окно - чат остаётся на связи")
        close.clicked.connect(lambda *_a: close_window(_cursor()))
        row.addWidget(close)
        column.addWidget(title)
        self.title = title

        card = w.QFrame()
        card.setObjectName("skeldarChatCard")
        frame.content = card
        #  look A (2026-10-22): the columns paint their own faces, no card behind them
        frame.content_face = "none"
        column.addWidget(card, 1)
        self.card = card
        body = w.QVBoxLayout(card)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        self.pages = w.QStackedWidget()
        self.pages.setObjectName("skeldarChatPages")
        body.addWidget(self.pages)
        self.pages.addWidget(self._build_signin())
        self.pages.addWidget(self._build_main())
        grip = w.QSizeGrip(card)
        grip.setObjectName("skeldarChatGrip")
        grip.setFixedSize(px(14), px(14))
        self.grip = grip

        root.setStyleSheet(hubstyle.stylesheet(s) + "\n" + look_a_sheet(s))
        hubwindow.dress(frame, s)
        card.setStyleSheet("#skeldarChatCard {{ background: transparent;"
                           " border-top: 1px solid {0}; }}".format(hubstyle.TOKENS["track_edge"]))
        self.root = root
        self.burster = hubwindow.Burster(frame, self._burst_parts, self._burst_face, s)
        self.timer = q.QtCore.QTimer(root)
        self.timer.setInterval(TICK_MS)
        self.timer.timeout.connect(self._tick)
        self.slow = q.QtCore.QTimer(root)
        self.slow.setInterval(1000)
        self.slow.timeout.connect(self._each_second)
        self.slow.start()
        self.later = q.QtCore.QTimer(root)
        self.later.setSingleShot(True)
        self.later.setInterval(0)
        self.later.timeout.connect(self.refresh)
        root.installEventFilter(_resize_filter(self))
        self._drops = _drop_filter(self)
        root.setAcceptDrops(True)
        root.installEventFilter(self._drops)
        self.composer.viewport().installEventFilter(self._drops)
        self.root.destroyed.connect(lambda *_a: self._gone())

    def _build_signin(self):
        q = _q()
        w = q.QtWidgets
        px = self.px
        page = w.QWidget()
        page.setObjectName("skeldarChatSignIn")
        lay = w.QVBoxLayout(page)
        lay.addStretch(1)
        box = w.QWidget()
        box.setObjectName("skeldarChatSignInBox")
        box.setMaximumWidth(px(320))
        inner = w.QVBoxLayout(box)
        inner.setSpacing(px(6))
        inner.addWidget(_label("Ваш ник", "heading"))
        nick_row = w.QHBoxLayout()
        nick_row.addWidget(_label("@", "label"))
        self.nick_field = w.QLineEdit()
        self.nick_field.setObjectName("skeldarChatNick")
        self.nick_field.setPlaceholderText("nick")
        self.nick_field.textChanged.connect(self._nick_typed)
        self.nick_field.returnPressed.connect(self.sign_in)
        nick_row.addWidget(self.nick_field, 1)
        inner.addLayout(nick_row)
        self.signin_go = _button("Войти", "primary", None, "skeldarChatSignInGo", self.scale)
        self.signin_go.clicked.connect(lambda *_a: self.sign_in())
        inner.addWidget(self.signin_go)
        self.code_toggle = _button("Войти по коду", "secondary", None, "skeldarChatCodeToggle",
                                   self.scale)
        self.code_toggle.clicked.connect(lambda *_a: self._show_code_field())
        inner.addWidget(self.code_toggle)
        self.code_field = w.QLineEdit()
        self.code_field.setObjectName("skeldarChatCode")
        self.code_field.setPlaceholderText("код входа с другой машины")
        self.code_field.setEchoMode(w.QLineEdit.Password)
        self.code_field.returnPressed.connect(self.sign_in_code)
        self.code_field.hide()
        inner.addWidget(self.code_field)
        self.signin_line = _label("", "note", "skeldarChatSignInLine", wrap=True)
        inner.addWidget(self.signin_line)
        h = w.QHBoxLayout()
        h.addStretch(1)
        h.addWidget(box)
        h.addStretch(1)
        lay.addLayout(h)
        lay.addStretch(2)
        return page

    def _scroll(self, widget, name):
        q = _q()
        w = q.QtWidgets
        area = w.QScrollArea()
        area.setObjectName(name)
        area.setWidgetResizable(True)
        area.setFrameShape(w.QFrame.NoFrame)
        area.setHorizontalScrollBarPolicy(q.QtCore.Qt.ScrollBarAlwaysOff)
        area.viewport().setAutoFillBackground(False)
        area.viewport().setObjectName("skeldarChatViewport")
        area.setWidget(widget)
        widget.setAutoFillBackground(False)
        return area

    def _build_main(self):
        q = _q()
        w = q.QtWidgets
        px = self.px
        page = w.QWidget()
        page.setObjectName("skeldarChatMain")
        lay = w.QHBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        #  look A (2026-10-22): ≡ (my card, New chat, Settings), the round search, ✎; the
        #  tabs; the rows. My name and Settings moved from a foot into ≡, as in Telegram.
        left = w.QWidget()
        left.setObjectName("skeldarChatLeft")
        left.setAttribute(q.QtCore.Qt.WA_StyledBackground, True)
        left.setFixedWidth(px(look.LIST_W))
        lv = w.QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(0)
        head = w.QWidget()
        head.setObjectName("skeldarChatListTop")
        head.setFixedHeight(px(44))
        top = w.QHBoxLayout(head)
        top.setContentsMargins(px(6), 0, px(6), 0)
        top.setSpacing(px(4))
        self.menu_button = _button("", "tool", "menu-2", "skeldarChatMenuButton", self.scale,
                                   "Мой профиль, новый чат, настройки")
        self.menu_button.clicked.connect(lambda *_a: self.me_menu())
        top.addWidget(self.menu_button)
        self.search = w.QLineEdit()
        self.search.setObjectName("skeldarChatSearch")
        self.search.setPlaceholderText("Поиск")
        self.search.setFont(_font(self.search.font(), px(11)))
        self.search.addAction(hubqt.icon("search", hubstyle.TOKENS["muted"], px(14)),
                              w.QLineEdit.LeadingPosition)
        self.search.textChanged.connect(self._searched)
        top.addWidget(self.search, 1)
        new = _button("", "tool", "pencil", "skeldarChatNew", self.scale, "Новый чат или группа")
        new.clicked.connect(lambda *_a: self.show_pane("new"))
        top.addWidget(new)
        lv.addWidget(head)
        self.tab = get_var(TAB_VAR) or "all"
        if self.tab not in dict(look.TABS):
            self.tab = "all"
        self.tabs = tabs_class()(self)
        lv.addWidget(self.tabs)
        self.list = list_class()(self)
        self.list_area = self._scroll(self.list, "skeldarChatListArea")
        lv.addWidget(self.list_area, 1)
        lay.addWidget(left)
        self.left = left

        split = w.QFrame()
        split.setObjectName("skeldarChatSplit")
        split.setFixedWidth(1)
        lay.addWidget(split)
        self.split = split

        self.right = w.QStackedWidget()
        self.right.setObjectName("skeldarChatRight")
        self.right_pages = {}
        for key, builder in (("empty", self._build_empty), ("chat", self._build_chat),
                             ("new", self._build_new),
                             ("settings", self._build_settings),
                             ("members", self._build_members)):
            widget = builder()
            self.right_pages[key] = widget
            self.right.addWidget(widget)
        lay.addWidget(self.right, 1)
        return page

    def _pane_box(self, title, name):
        """A right pane's column with a back button and its title."""
        q = _q()
        w = q.QtWidgets
        page = w.QWidget()
        page.setObjectName(name)
        lay = w.QVBoxLayout(page)
        lay.setContentsMargins(self.px(8), self.px(4), self.px(4), self.px(4))
        lay.setSpacing(self.px(6))
        head = w.QHBoxLayout()
        back = _button("", "tool", "arrow-left", name + "Back", self.scale, "Назад")
        back.clicked.connect(lambda *_a: self.back())
        head.addWidget(back)
        head.addWidget(_label(title, "heading"), 1)
        lay.addLayout(head)
        return page, lay

    def _build_empty(self):
        q = _q()
        page = q.QtWidgets.QWidget()
        lay = q.QtWidgets.QVBoxLayout(page)
        self.empty_label = _label("Выберите чат слева или начните новый ✎", "note",
                                  "skeldarChatEmpty")
        self.empty_label.setAlignment(q.QtCore.Qt.AlignCenter)
        lay.addWidget(self.empty_label)
        return page

    def _build_chat(self):
        q = _q()
        w, Qt = q.QtWidgets, q.QtCore.Qt
        px = self.px
        page = w.QWidget()
        page.setObjectName("skeldarChatPage")
        lay = w.QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        #  look A (2026-10-22): the header on `panel` with a hairline under it
        head_w = w.QFrame()
        head_w.setObjectName("skeldarChatHead")
        head_w.setFixedHeight(px(50))
        head = w.QHBoxLayout(head_w)
        head.setContentsMargins(px(10), 0, px(8), 0)
        head.setSpacing(px(8))
        self.chat_back = _button("", "tool", "arrow-left", "skeldarChatBack", self.scale, "К списку")
        self.chat_back.clicked.connect(lambda *_a: self.back())
        head.addWidget(self.chat_back)
        self.chat_avatar = avatar_widget_class()(self, {}, px(34))
        self.chat_avatar.setObjectName("skeldarChatHeadAvatar")
        head.addWidget(self.chat_avatar)
        texts = w.QVBoxLayout()
        texts.setSpacing(px(1))
        texts.setContentsMargins(px(2), 0, 0, 0)
        self.chat_title = _label("", None, "skeldarChatTitleText")
        self.chat_title.setFont(_font(self.chat_title.font(), px(12.5), True))
        self.chat_title.setStyleSheet("color: {0};".format(hubstyle.TOKENS["text"]))
        self.chat_sub = _label("", None, "skeldarChatSub")
        self.chat_sub.setFont(_font(self.chat_sub.font(), px(10.5)))
        texts.addWidget(self.chat_title)
        texts.addWidget(self.chat_sub)
        head.addLayout(texts, 1)
        self.members_button = _button("", "tool", "users", "skeldarChatMembers", self.scale,
                                      "Участники")
        self.members_button.clicked.connect(lambda *_a: self.show_pane("members"))
        head.addWidget(self.members_button)
        self.call_voice = _button("", "tool", "phone", "skeldarChatCallVoice", self.scale,
                                  "Голосовой звонок")
        self.call_voice.clicked.connect(lambda *_a: self.start_call("audio"))
        self.call_video = _button("", "tool", "video", "skeldarChatCallVideo", self.scale,
                                  "Видеозвонок")
        self.call_video.clicked.connect(lambda *_a: self.start_call("video"))
        self.call_join = _button("Присоединиться", "primary", None, "skeldarChatCallJoin",
                                 self.scale)
        self.call_join.clicked.connect(lambda *_a: self.join_call())
        self.call_join.hide()
        self._joinable = None
        head.addWidget(self.call_voice)
        head.addWidget(self.call_video)
        head.addWidget(self.call_join)
        lay.addWidget(head_w)

        self.feed = feed_class()(self)
        from . import emojiart
        try:
            self.feed.anim = emojiart.animated(self.session)
        except Exception:                                    # noqa: BLE001
            self.feed.anim = None
        self.feed_area = self._scroll(self.feed, "skeldarChatFeedArea")
        self.feed_area.verticalScrollBar().valueChanged.connect(self._scrolled)
        self.feed_area.verticalScrollBar().rangeChanged.connect(self._range_changed)
        lay.addWidget(self.feed_area, 1)
        self.down = _button("", None, None, "skeldarChatDown", self.scale, "К новым сообщениям")
        self.down.setIcon(hubqt.icon("arrow-down", hubstyle.TOKENS["text2"], px(16)))
        self.down.setParent(self.feed_area)
        self.down.clicked.connect(lambda *_a: self.to_bottom())
        self.down.hide()

        #  the composer (look A): on `panel` with a hairline over it; the reply / edit bar
        #  is an icon, a quote in the sender's colour and ✕
        compose = w.QFrame()
        compose.setObjectName("skeldarChatCompose")
        cv = w.QVBoxLayout(compose)
        cv.setContentsMargins(px(8), px(6), px(8), px(8))
        cv.setSpacing(px(6))
        self.bar = w.QWidget()
        self.bar.setObjectName("skeldarChatBar")
        bar = w.QHBoxLayout(self.bar)
        bar.setContentsMargins(px(4), 0, 0, 0)
        bar.setSpacing(px(8))
        self.bar_icon = w.QLabel()
        self.bar_icon.setObjectName("skeldarChatBarIcon")
        bar.addWidget(self.bar_icon)
        self.bar_quote = w.QFrame()
        self.bar_quote.setObjectName("skeldarChatBarQuote")
        qv = w.QVBoxLayout(self.bar_quote)
        qv.setContentsMargins(px(10), px(2), px(8), px(2))
        qv.setSpacing(0)
        self.bar_text = _label("", None, "skeldarChatBarTitle")
        self.bar_text.setFont(_font(self.bar_text.font(), px(10), True))
        qv.addWidget(self.bar_text)
        self.bar_sub = _label("", None, "skeldarChatBarText")
        self.bar_sub.setFont(_font(self.bar_sub.font(), px(10.5)))
        qv.addWidget(self.bar_sub)
        bar.addWidget(self.bar_quote, 1)
        cancel = _button("", "tool", "x", "skeldarChatBarCancel", self.scale, "Отменить (Esc)")
        cancel.clicked.connect(lambda *_a: self.cancel_bar())
        bar.addWidget(cancel)
        self.bar.hide()
        cv.addWidget(self.bar)

        row = w.QHBoxLayout()
        row.setSpacing(px(6))
        self.clip_button = _button("", "tool", "paperclip", "skeldarChatClip", self.scale,
                                   "Отправить сцену, выделенное или файл (.ma .mb .fbx) - "
                                   "или перетащите файл в окно")
        self.clip_button.clicked.connect(lambda *_a: self.clip_menu())
        row.addWidget(self.clip_button, 0, Qt.AlignBottom)
        self.field = w.QFrame()
        self.field.setObjectName("skeldarChatField")
        fl = w.QHBoxLayout(self.field)
        fl.setContentsMargins(px(14), px(2), px(3), px(2))
        fl.setSpacing(px(2))
        self.composer = composer_class()(self)
        self.composer.textChanged.connect(self._typed)
        fl.addWidget(self.composer, 1)
        self.emoji_button = _button("", None, None, "skeldarChatEmoji", self.scale, "Эмоджи")
        self.emoji_button.setIcon(hubqt.icon("mood-smile", hubstyle.TOKENS["muted"], px(18)))
        self.emoji_button.setIconSize(q.QtCore.QSize(px(18), px(18)))
        self.emoji_button.clicked.connect(lambda *_a: self.pick_emoji())
        fl.addWidget(self.emoji_button, 0, Qt.AlignBottom)
        row.addWidget(self.field, 1)
        self.send_button = _button("", None, None, "skeldarChatSend", self.scale,
                                   "Отправить (Enter)")
        self.send_button.setIconSize(q.QtCore.QSize(px(17), px(17)))
        self.send_button.clicked.connect(lambda *_a: self.send_now())
        row.addWidget(self.send_button, 0, Qt.AlignBottom)
        cv.addLayout(row)
        self.line = _label("", "status", "skeldarChatLine", wrap=True)
        self.line.hide()
        cv.addWidget(self.line)
        lay.addWidget(compose)
        self._paint_send()
        return page

    def _paint_send(self):
        """The round send button (look A): grey while there is nothing to send, the accent
        with the arrow in `on_accent` once there is."""
        ready = bool(self.composer.toPlainText().strip())
        button = self.send_button
        if button.property("skState") == ("ready" if ready else "") and button.icon().cacheKey():
            return
        button.setProperty("skState", "ready" if ready else "")
        colour = hubstyle.TOKENS["on_accent"] if ready else hubstyle.TOKENS["faint"]
        button.setIcon(hubqt.icon("send", colour, self.px(17)))
        style = button.style()
        style.unpolish(button)
        style.polish(button)
        button.update()

    def _field_lit(self, on):
        """The composer's round field lights while the text has the focus."""
        self.field.setProperty("skFocus", "true" if on else "")
        style = self.field.style()
        style.unpolish(self.field)
        style.polish(self.field)
        self.field.update()

    def _build_new(self):
        q = _q()
        w = q.QtWidgets
        page, lay = self._pane_box("Новый чат", "skeldarChatNewPane")
        lay.addWidget(_label("Личный чат: «Написать». Группа: отметьте людей и назовите её.",
                             "note", wrap=True))
        self.new_search = w.QLineEdit()
        self.new_search.setObjectName("skeldarChatNewSearch")
        self.new_search.setPlaceholderText("Имя или @ник")
        self.new_search.textChanged.connect(lambda *_a: self._fill_new())
        lay.addWidget(self.new_search)
        name = w.QHBoxLayout()
        self.group_name = w.QLineEdit()
        self.group_name.setObjectName("skeldarChatGroupName")
        self.group_name.setPlaceholderText("Название группы")
        name.addWidget(self.group_name, 1)
        make = _button("Создать группу", "primary", "users", "skeldarChatGroupMake", self.scale)
        make.clicked.connect(lambda *_a: self.make_group())
        name.addWidget(make)
        lay.addLayout(name)
        self.new_line = _label("", "status", "skeldarChatNewLine", wrap=True)
        lay.addWidget(self.new_line)
        self.new_body = w.QWidget()
        self.new_body.setObjectName("skeldarChatNewBody")
        self.new_rows = w.QVBoxLayout(self.new_body)
        self.new_rows.setContentsMargins(0, 0, 0, 0)
        self.new_rows.setSpacing(self.px(3))
        lay.addWidget(self._scroll(self.new_body, "skeldarChatNewArea"), 1)
        self.picked = set()
        return page

    def _build_settings(self):
        q = _q()
        w = q.QtWidgets
        page, lay = self._pane_box("Настройки", "skeldarChatSettings")
        pic = w.QHBoxLayout()
        self.settings_avatar = avatar_widget_class()(self, {}, self.px(56), False)
        self.settings_avatar.clickable = False
        self.settings_avatar.setObjectName("skeldarChatSettingsAvatar")
        pic.addWidget(self.settings_avatar)
        choose = _button("Выбрать картинку…", None, "photo", "skeldarChatAvatarChoose", self.scale,
                         "PNG или JPG: обрежется в квадрат по центру")
        choose.clicked.connect(lambda *_a: self.choose_avatar())
        pic.addWidget(choose)
        pic.addStretch(1)
        lay.addLayout(pic)
        lay.addWidget(_label("Имя", "label"))
        row = w.QHBoxLayout()
        self.name_field = w.QLineEdit()
        self.name_field.setObjectName("skeldarChatName")
        row.addWidget(self.name_field, 1)
        save = _button("Сохранить", None, "check", "skeldarChatNameSave", self.scale)
        save.clicked.connect(lambda *_a: self.rename_me())
        row.addWidget(save)
        lay.addLayout(row)
        lay.addWidget(_label("Код входа - для другой машины, никому не показывайте", "label",
                             wrap=True))
        code = w.QHBoxLayout()
        self.code_text = _label("••••••••", None, "skeldarChatCodeText")
        self.code_text.setTextInteractionFlags(q.QtCore.Qt.TextSelectableByMouse)
        code.addWidget(self.code_text, 1)
        self.code_show = _button("Показать", None, None, "skeldarChatCodeShow", self.scale)
        self.code_show.clicked.connect(lambda *_a: self.toggle_code())
        code.addWidget(self.code_show)
        copy = _button("Скопировать", None, None, "skeldarChatCodeCopy", self.scale)
        copy.clicked.connect(lambda *_a: self.copy_code())
        code.addWidget(copy)
        lay.addLayout(code)
        lay.addWidget(_label("Уведомления", "label"))
        self.notify_box = w.QCheckBox("Сообщение во вьюпорте")
        self.notify_box.setObjectName("skeldarChatNotifyBox")
        self.notify_box.toggled.connect(lambda on: self._set_notify("viewport", on))
        lay.addWidget(self.notify_box)
        self.sound_box = w.QCheckBox("Звук нового сообщения")
        self.sound_box.setObjectName("skeldarChatSoundBox")
        self.sound_box.toggled.connect(lambda on: self._set_notify("sound", on))
        lay.addWidget(self.sound_box)
        self.settings_line = _label("", "status", "skeldarChatSettingsLine", wrap=True)
        lay.addWidget(self.settings_line)
        lay.addStretch(1)
        out = _button("Выйти на этой машине", "danger", None, "skeldarChatSignOut", self.scale)
        out.clicked.connect(lambda *_a: self.sign_out())
        lay.addWidget(out)
        return page

    def _build_members(self):
        q = _q()
        w = q.QtWidgets
        page, lay = self._pane_box("Участники", "skeldarChatMembersPane")
        row = w.QHBoxLayout()
        self.chat_name_field = w.QLineEdit()
        self.chat_name_field.setObjectName("skeldarChatRenameField")
        row.addWidget(self.chat_name_field, 1)
        self.chat_rename = _button("Переименовать", None, "pencil", "skeldarChatRename",
                                   self.scale)
        self.chat_rename.clicked.connect(lambda *_a: self.rename_chat())
        row.addWidget(self.chat_rename)
        lay.addLayout(row)
        self.members_line = _label("", "status", "skeldarChatMembersLine", wrap=True)
        lay.addWidget(self.members_line)
        self.members_body = w.QWidget()
        self.members_body.setObjectName("skeldarChatMembersBody")
        self.members_rows = w.QVBoxLayout(self.members_body)
        self.members_rows.setContentsMargins(0, 0, 0, 0)
        self.members_rows.setSpacing(self.px(3))
        lay.addWidget(self._scroll(self.members_body, "skeldarChatMembersArea"), 1)
        return page

    # ---------------------------------------------------------- session -> picture
    def _paint_call_buttons(self):
        """Voice and video, or «Присоединиться» while the chat has a call I may come into."""
        chat = self.chat
        me = self.me_id()
        running = _calls.of_chat(getattr(self.session.state, "calls", {}), chat) if chat else None
        joinable = running if running and _calls.can_join(running, me) else None
        self.call_join.setVisible(bool(joinable))
        free = chat is not None and running is None
        self.call_voice.setVisible(free)
        self.call_video.setVisible(free)
        self._joinable = joinable

    def start_call(self, kind, chat=None):
        chat = chat or self.chat
        if chat is None:
            return None
        running = _calls.of_chat(getattr(self.session.state, "calls", {}), chat)
        if running is not None:
            return self.join_call() if self._joinable and self._joinable["chat"] == chat else None
        from . import callview
        return callview.start(self.session, chat, kind)

    def join_call(self):
        view = self._joinable
        if not view:
            return None
        from . import callview
        return callview.answer(self.session, view["id"], view["kind"])

    def _heard(self, kind, data):
        if self.root is None or not hubqt._valid(self.root):
            return
        if kind == "call":
            try:
                self._paint_call_buttons()
            except Exception:                                # noqa: BLE001
                traceback.print_exc()
        if kind == "message" and data and self.chat == data["message"]["chat"] \
                and not self.at_bottom() and data["message"]["from_id"] != self.me_id():
            self.unseen += 1
        if not self.later.isActive():
            self.later.start()

    def me_id(self):
        return (self.session.state.me or {}).get("id")

    def chats(self):
        return list(self.session.state.chats.values())

    def refresh(self):
        if self.root is None or not hubqt._valid(self.root):
            return
        try:
            self._refresh()
        except Exception:                                    # noqa: BLE001
            traceback.print_exc()

    def _refresh(self):
        st = self.session.state
        signed = st.me is not None
        self.state_label.setText(look.status_title(st.status) if signed else "")
        self.pages.setCurrentIndex(1 if signed else 0)
        if not signed:
            return
        me = st.me
        now = time.monotonic()
        rows = []
        chats, persons = look.directory(self.chats(), getattr(st, "people", []), me["id"],
                                        st.online, self.query, _now_ms())
        for c in chats:
            if not look.in_tab("group" if c.get("kind") == "group" else "dm", self.tab):
                continue
            last = c.get("last") or {}
            prefix, text = look.preview_parts(c, me["id"], st.typing, now)
            tick = ""
            if last and last.get("from_id") == me["id"] and not last.get("deleted"):
                upto = look.read_by_others(c, st.reads, me["id"])
                tick = "read" if (last.get("seq") or 0) <= upto else "sent"
            rows.append({"id": c["id"], "kind": "chat", "chat": c,
                         "title": look.chat_title(c, me["id"]),
                         "preview": look.preview(c, me["id"], st.typing, now),
                         "prefix": prefix, "text": text, "tick": tick,
                         "time": look.clock(last.get("at"), _now_ms()) if last else "",
                         "unread": int(c.get("unread") or 0),
                         "user": look.other(c, me["id"]) or {"id": c["id"], "name": c.get("name")},
                         "typing": bool(look.typers(st.typing, c["id"], me["id"], now))})
        if not look.in_tab("person", self.tab):
            persons = []
        if persons:
            rows.append({"id": "head:people", "kind": "head",
                         "title": "ВСЕ ПОЛЬЗОВАТЕЛИ · " + look.people_count(persons)})
        for u in persons:
            rows.append({"id": "person:" + u["id"], "kind": "person", "user": u,
                         "title": look.display_name(u), "preview": u["line"], "time": "",
                         "unread": 0, "typing": False, "online": u["online"]})
        self.tabs.set_counts(dict((key, look.tab_count(self.chats(), key))
                                  for key, _label in look.TABS))
        self.list.selected = self.chat
        self.list.set_rows(rows)
        if self.chat is not None and self.chat not in st.chats:
            self.chat = None
        self._layout_columns()
        self._refresh_chat()
        if self.pane == "new":
            self._fill_new()
        elif self.pane == "members":
            self._fill_members()
        elif self.pane == "settings":
            self._fill_settings()
        self._read_if_seen()

    def _layout_columns(self):
        narrow = look.one_column(self.root.width() / self.scale)
        page = self.pane if self.pane != "chat" else ("chat" if self.chat else "empty")
        self.right.setCurrentWidget(self.right_pages[page])
        if narrow:
            show_right = self.single == "right"
            self.left.setVisible(not show_right)
            self.right.setVisible(show_right)
            self.split.setVisible(False)
            #  one column: the list takes the window's width (it stood at its fixed width
            #  with a gap beside it)
            self.left.setMinimumWidth(0)
            self.left.setMaximumWidth(16777215)
        else:
            self.left.setVisible(True)
            self.right.setVisible(True)
            self.split.setVisible(True)
            self.left.setFixedWidth(self.px(look.LIST_W))
        self.chat_back.setVisible(narrow)

    def _refresh_chat(self):
        st = self.session.state
        c = st.chats.get(self.chat) if self.chat else None
        if c is None:
            return
        me_id = self.me_id()
        self.chat_title.setText(look.chat_title(c, me_id))
        partner = look.other(c, me_id)
        self.chat_avatar.set_user(partner or {"id": c["id"], "name": c.get("name")},
                                  dot=partner is not None)
        self.chat_sub.setText(look.presence(c, me_id, st.online, st.typing, time.monotonic(),
                                            _now_ms()))
        typing = bool(look.typers(st.typing, c["id"], me_id, time.monotonic()))
        self.chat_sub.setStyleSheet("color: {0};".format(
            hubstyle.TOKENS["accent_text" if typing else "muted"]))
        self.members_button.setVisible(c.get("kind") == "group")
        self._paint_call_buttons()
        messages = st.messages.get(self.chat, [])
        users = dict((m["id"], m) for m in c.get("members", []))

        def user_of(uid):
            return users.get(uid, {"id": uid, "nick": uid})

        items = look.feed(messages, st.pending.get(self.chat, []), me_id, c, st.reads, _now_ms())
        mark = self.unread_from
        if mark and mark[0] == self.chat and mark[1]:
            items = look.mark_unread(items, mark[1])
        ctx = {"chat": c, "messages": messages, "user_of": user_of,
               "file_state": self.file_state,
               "name_of": lambda uid: look.display_name(user_of(uid)),
               "deleted": set(m["id"] for m in messages if m.get("deleted"))}
        was_bottom = self.at_bottom()
        history = getattr(self, "_history_came", False)
        self._history_came = False
        if history:
            ctx_bottom = self._distance_from_bottom()
        if (self.feed.ctx.get("chat") or {}).get("id") != self.chat:
            self.feed._known = None
        if self.feed._known is not None:
            self.feed._known["history"] = history
        self.feed.set_items(items, ctx)
        if history:
            self._keep_distance(ctx_bottom)
        elif was_bottom:
            self.to_bottom()
        self._paint_down()
        self._paint_bar()

    # ---------------------------------------------------------- the feed's scroll
    def at_bottom(self):
        bar = self.feed_area.verticalScrollBar()
        return bar.value() >= bar.maximum() - self.px(6)

    def _distance_from_bottom(self):
        bar = self.feed_area.verticalScrollBar()
        return bar.maximum() - bar.value()

    def _keep_distance(self, distance):
        self.feed.adjustSize()
        bar = self.feed_area.verticalScrollBar()
        self._pending_scroll = ("keep", distance)
        bar.setValue(bar.maximum() - distance)

    def to_bottom(self):
        self._pending_scroll = ("bottom", 0)
        bar = self.feed_area.verticalScrollBar()
        bar.setValue(bar.maximum())
        self.unseen = 0
        self._paint_down()

    def _range_changed(self, _lo, hi):
        pending = getattr(self, "_pending_scroll", None)
        if pending is None:
            return
        bar = self.feed_area.verticalScrollBar()
        if pending[0] == "bottom":
            bar.setValue(hi)
        else:
            bar.setValue(hi - pending[1])

    def _scrolled(self, value):
        bar = self.feed_area.verticalScrollBar()
        if value < bar.maximum() - self.px(6):
            self._pending_scroll = None
        else:
            self.unseen = 0
            self._read_if_seen()
        self._paint_down()
        if value <= 0 and bar.maximum() > 0 and self.chat and self.chat not in self.history_done:
            self.load_history()

    def _paint_down(self):
        show = self.chat is not None and not self.at_bottom()
        self.down.setVisible(show)
        if show:
            self.down.setText(look.count_text(self.unseen) if self.unseen else "")
            self.down.adjustSize()
            area = self.feed_area
            self.down.move(area.width() - self.down.width() - self.px(10),
                           area.height() - self.down.height() - self.px(10))
            self.down.raise_()

    def load_history(self):
        try:
            came = self.session.load_history(self.chat)
        except Exception as exc:                             # noqa: BLE001
            self.say(getattr(exc, "text", str(exc)))
            return 0
        if not came:
            self.history_done.add(self.chat)
        self._history_came = True
        self.refresh()
        return came

    def scroll_to_message(self, message_id):
        y = self.feed.top_of(message_id)
        if y is None:
            self.say("Это сообщение старше загруженной истории")
            return False
        self._pending_scroll = None
        self.feed_area.verticalScrollBar().setValue(int(max(0, y - self.px(20))))
        self.feed.flashing[next(b.item.key() for b in self.feed.boxes
                                if b.item.kind == "msg"
                                and b.item.message.get("id") == message_id)] = _now_ms()
        self.animate()
        return True

    def _read_if_seen(self):
        if self.chat is None or not self.root.isVisible() or not self.at_bottom():
            return
        c = self.session.state.chats.get(self.chat)
        if c is None or not c.get("unread"):
            return
        try:
            self.session.read(self.chat)
        except Exception:                                    # noqa: BLE001
            pass

    # ---------------------------------------------------------- presses
    def open_chat(self, chat_id):
        if chat_id != self.chat:
            self.reply_to = self.editing = None
            self.composer.clear()
            self.unseen = 0
            #  «Непрочитанные сообщения» stands before what was unread as the chat opened,
            #  until another chat is opened (look A, 2026-10-22)
            c = self.session.state.chats.get(chat_id) or {}
            self.unread_from = (chat_id, look.first_unread(
                self.session.state.messages.get(chat_id, []), int(c.get("unread") or 0),
                self.me_id()))
        self.chat = chat_id
        self.pane = "chat"
        self.single = "right"
        try:
            from . import toast
            toast.dismiss_chat(chat_id)
        except Exception:                                    # noqa: BLE001
            pass
        self.feed._known = None
        self._pending_scroll = ("bottom", 0)
        self.refresh()
        self.to_bottom()
        self._read_if_seen()
        self.composer.setFocus()

    def back(self):
        if self.pane != "chat":
            self.pane = "chat"
            if self.chat is None:
                self.single = "list"
        else:
            self.single = "list"
        self.refresh()

    def show_pane(self, pane):
        self.pane = pane
        self.single = "right"
        if pane in ("new", "members"):
            self.read_people()
        self.refresh()

    def read_people(self):
        """Asks the server for everybody again (New chat, Members opened)."""
        fn = getattr(self.session, "read_people", None)
        if fn is not None:
            try:
                fn()
            except Exception:                                # noqa: BLE001
                pass

    def say(self, text, where=None):
        label = where or self.line
        label.setText(text or "")
        label.setVisible(bool(text))

    def send_now(self):
        if self.chat is None:
            return None
        text = self.composer.toPlainText().strip()
        if not text:
            return None
        try:
            if self.editing:
                self.session.edit(self.chat, self.editing, text)
                result = self.editing
            else:
                result = self.session.send(self.chat, text, reply_to=self.reply_to)
        except Exception as exc:                             # noqa: BLE001
            self.say(getattr(exc, "text", str(exc)))
            return None
        self.composer.clear()
        self.reply_to = self.editing = None
        self.say("")
        self._pending_scroll = ("bottom", 0)
        self.refresh()
        self.to_bottom()
        return result

    def edit_last(self):
        m = look.last_mine(self.session.state.messages.get(self.chat, []), self.me_id())
        if m is None:
            return False
        self.start_edit(m)
        return True

    def start_edit(self, message):
        self.editing = message["id"]
        self.reply_to = None
        self.composer.setPlainText(message.get("text") or "")
        self.composer.moveCursor(_q().QtGui.QTextCursor.End)
        self._paint_bar()
        self.composer.setFocus()

    def start_reply(self, message):
        self.reply_to = message["id"]
        self.editing = None
        self._paint_bar()
        self.composer.setFocus()

    def cancel_bar(self):
        if not (self.reply_to or self.editing):
            return False
        if self.editing:
            self.composer.clear()
        self.reply_to = self.editing = None
        self._paint_bar()
        return True

    def _paint_bar(self):
        """The reply / edit bar (look A): its icon, a quote whose bar and title take the
        replied sender's colour, the text under."""
        messages = self.session.state.messages.get(self.chat, [])
        colour = hubstyle.TOKENS["accent_text"]
        if self.editing:
            m = look.find(messages, self.editing) or {}
            icon_name, title = "pencil", "Изменение сообщения"
            text = " ".join(str(m.get("text") or "").split())
        elif self.reply_to:
            m = look.find(messages, self.reply_to) or {}
            c = self.session.state.chats.get(self.chat) or {}
            who = next((u for u in c.get("members", []) if u.get("id") == m.get("from_id")),
                       {"nick": "?"})
            icon_name, title = "corner-up-left", "Ответ " + look.display_name(who)
            text = look.message_text(m) if (m.get("call") or m.get("file")) else \
                " ".join(str(m.get("text") or "").split())
            if m.get("from_id"):
                colour = _q().QtGui.QColor(look.user_colour(m.get("from_id"))).lighter(135).name()
        else:
            self.bar.setVisible(False)
            return
        self.bar_icon.setPixmap(hubqt.pixmap(icon_name, hubstyle.TOKENS["accent_text"],
                                             self.px(17)))
        self.bar_text.setText(title)
        self.bar_text.setStyleSheet("color: {0};".format(colour))
        fm = self.bar_sub.fontMetrics()
        self.bar_sub.setText(fm.elidedText(text, _q().QtCore.Qt.ElideRight,
                                           max(self.px(60), self.bar_quote.width() - self.px(24))))
        self.bar_quote.setStyleSheet(
            "#skeldarChatBarQuote {{ background: rgba(255,255,255,13); border-radius: {0}px;"
            " border-left: {1}px solid {2}; }}".format(self.px(6), self.px(3), colour))
        self.bar.setVisible(True)

    def retry(self, item):
        if item.pending:
            cid = item.message.get("cid")
            p = self.session._find_pending(cid) if hasattr(self.session, "_find_pending") else None
            if p is not None and p.get("state") != "failed":
                p["state"] = "failed"
            self.session.retry(cid)
            self.refresh()

    def message_menu(self, item, global_point):
        """The right button on a message: Reply, Copy, Edit and Delete for one's own."""
        rows = self.menu_rows(item)
        if not rows:
            return
        q = _q()
        menu = q.QtWidgets.QMenu(self.root)
        menu.setObjectName("skeldarChatMenu")
        if not item.pending:
            menu.addAction(self._quick_reactions(menu, item.message))
            menu.addSeparator()
        for label, fn in rows:
            act = menu.addAction(label)
            _menu_icon(act, label, self.scale)
            act.triggered.connect(lambda *_a, f=fn: f())
        menu.popup(global_point)
        self._menu = menu

    def menu_rows(self, item):
        m = item.message
        rows = []
        if item.pending:
            rows.append(("Повторить", lambda: self.retry(item)))
            rows.append(("Удалить", lambda: (self.session.discard(m.get("cid")), self.refresh())))
            return rows
        from . import files as _files
        if m.get("file") and not m["file"].get("expired") and _files.is_image(m["file"]):
            for action, label in FILE_ACTIONS["image"]:
                rows.append((label, lambda a=action: self.file_action(item, a)))
        elif m.get("file") and not m["file"].get("expired") and not _files.is_card(m["file"]):
            for action, label in FILE_MENU:
                rows.append((label, lambda a=action: self.file_action(item, a)))
        rows.append(("Реакция…", lambda: self.pick_emoji(m)))
        rows.append(("Ответить", lambda: self.start_reply(m)))
        call = bool(m.get("call"))      # a call's line: its text is for older clients only
        if m.get("text") and not call:
            rows.append(("Скопировать", lambda: self.copy_text(m.get("text") or "")))
        if item.mine and not call:
            rows.append(("Изменить", lambda: self.start_edit(m)))
            rows.append(("Удалить", lambda: self.delete_message(m)))
        return rows

    # ---------------------------------------------------------- files (2026-10-22)
    def clip_menu(self):
        q = _q()
        menu = q.QtWidgets.QMenu(self.root)
        menu.setObjectName("skeldarChatClipMenu")
        for label, fn in self.clip_rows():
            act = menu.addAction(label)
            _menu_icon(act, label, self.scale)
            act.triggered.connect(lambda *_a, f=fn: f())
        menu.popup(self.clip_button.mapToGlobal(q.QtCore.QPoint(0, 0)))
        self._menu = menu

    def clip_rows(self):
        return [(u"Отправить сцену", self.send_scene),
                (u"Отправить выделенное (FBX)", self.send_selection),
                (u"Отправить файл…", self.send_file_dialog)]

    def _caption(self):
        """The composer's text goes with a file as its caption."""
        if self.editing:
            return ""
        text = self.composer.toPlainText().strip()
        self.composer.clear()
        return text

    def _sent_file(self, fn, what):
        if self.chat is None:
            self.say(u"Откройте чат, чтобы отправить в него файл.")
            return None
        try:
            cid = fn()
        except Exception as exc:                             # noqa: BLE001
            if not getattr(exc, "text", None):
                traceback.print_exc()
            self.say(getattr(exc, "text", None) or str(exc))
            return None
        self.say("")
        self.refresh()
        self.to_bottom()
        return cid

    def send_scene(self):
        from . import files
        return self._sent_file(lambda: files.send_scene(self.session, self.chat, self._caption()),
                               "scene")

    def send_selection(self):
        from . import files
        return self._sent_file(lambda: files.send_selection(self.session, self.chat,
                                                            self._caption()), "selection")

    def send_card(self, card):
        """A Pose Library card dropped on the window (2026-10-22)."""
        from . import files
        return self._sent_file(lambda: files.send_card(self.session, self.chat, card,
                                                       self._caption()), "card")

    def show_profile(self, user):
        """A person's card over the window (their avatar large, their files); False when `user`
        is no person (a group's picture)."""
        user = user or {}
        uid = user.get("id")
        if not uid or uid in self.session.state.chats:
            return False
        known = dict(user)
        for chat in self.session.state.chats.values():
            for u in chat.get("members") or ():
                if u.get("id") == uid:
                    known.update(u)
        for u in getattr(self.session.state, "people", None) or ():
            if u.get("id") == uid:
                known.update(u)
        if uid == self.me_id():
            known.update(self.session.state.me or {})
        if not known.get("nick"):
            return False
        old = getattr(self, "profile", None)
        if old is not None and old.is_open():
            old.close()
        from . import profile
        self.profile = profile.Profile(self, known)
        return True

    def send_image(self, image):
        """A picture (the clipboard's QImage) into the open chat."""
        from . import files
        q = _q()
        if image is not None and not isinstance(image, q.QtGui.QImage):
            image = q.QtGui.QImage(image)
        return self._sent_file(lambda: files.send_image(self.session, self.chat, image,
                                                        self._caption()), "image")

    def sendable(self, mime):
        """The local files of `mime` the chat can send (scenes, FBX, pictures)."""
        from . import files
        return [path for path in _local_paths(mime) if files.kind_of(path)]

    def send_file_dialog(self):
        q = _q()
        path, _filter = q.QtWidgets.QFileDialog.getOpenFileName(
            self.root, u"Отправить файл в чат", "", FILE_FILTER)
        return self.send_path(path) if path else None

    def send_path(self, path):
        from . import files
        return self._sent_file(lambda: files.send_path(self.session, self.chat, path,
                                                       self._caption()), "file")

    def file_state(self, item):
        """(mode, progress, text) of a file message: ready, upload, failed, download, expired."""
        m = item.message
        f = m.get("file") or {}
        up = m.get("upload") if item.pending else None
        if up:
            if m.get("state") == "failed":
                return "failed", None, u"не отправлено"
            if up.get("phase") == "zip":
                return "upload", None, u"сжимаю…"
            return "upload", up.get("progress") or 0.0, u"отправляю %d%%" % int(
                100 * (up.get("progress") or 0.0))
        if f.get("expired"):
            return "expired", None, u"файл истёк"
        d = self.session.state.downloads.get(f.get("id")) if f.get("id") else None
        if d and d.get("state") == "loading":
            progress = d.get("progress")
            return "download", progress, (u"скачиваю %d%%" % int(100 * progress)
                                          if progress is not None else u"скачиваю…")
        from . import files
        if files.is_card(f):
            return "card", None, CARD_HINT
        if files.is_image(f):
            return "image", None, ""
        return "ready", None, ""

    def _sender(self, m):
        if m.get("from_id") == self.me_id():
            return u"вас"
        c = self.session.state.chats.get(self.chat) or {}
        who = next((u for u in c.get("members", []) if u.get("id") == m.get("from_id")),
                   {"id": m.get("from_id"), "nick": "?"})
        return look.display_name(who)

    def file_action(self, item, action, at=None, target=None):
        """A file card's button, its menu row, or where it was dropped (`target`: a Pose Library
        card's folder, or the character / floor it goes onto)."""
        from . import files
        m = item.message
        if action == "cancel":
            self.session.discard(m.get("cid"))
            self.refresh()
            return None
        if action == "more":
            q = _q()
            menu = q.QtWidgets.QMenu(self.root)
            menu.setObjectName("skeldarChatFileMenu")
            for a, label in FILE_MORE:
                act = menu.addAction(label)
                act.triggered.connect(lambda *_a, a=a: self.file_action(item, a))
            menu.popup(at or q.QtGui.QCursor.pos())
            self._menu = menu
            return None
        f = m.get("file") or {}
        sender = self._sender(m)
        verb = {"open": lambda path: files.open_file(path, f, sender),
                "import": lambda path: files.import_file(path, f, sender),
                "save": lambda path: files.save_to(path, f),
                "stash": lambda path: files.to_stash(path, f),
                "share": lambda path: files.to_share(path, f),
                "view": lambda path: files.show_picture(path, f, self.scale),
                "library": lambda path: files.to_library(path, (target or {}).get("folder")),
                "apply": lambda path: files.apply_card(path, target or {})}.get(action)
        if verb is None:
            return None

        def then(path):
            try:
                self.say(verb(path) or "")
            except Exception as exc:                         # noqa: BLE001
                traceback.print_exc()
                self.say(u"Не вышло: %s" % exc)

        try:
            there = files.fetch(self.session, f, then)
        except Exception as exc:                             # noqa: BLE001
            self.say(getattr(exc, "text", None) or str(exc))
            return None
        if not there:
            self.say(u"Скачиваю %s…" % (f.get("name") or u"файл"))
            self.refresh()
        return there

    # ---------------------------------------------------------- a card dragged out
    def start_drag(self, item, gp):
        import maya_hubqt
        from . import files as _files
        f = item.message.get("file") or {}
        if not f.get("id") or f.get("expired") or _files.is_image(f):
            return False
        q = _q()
        size = int(self.px(40))
        try:
            pixmap = maya_hubqt.pixmap("message-circle", hubstyle.TOKENS["accent"], size)
        except Exception:                                    # noqa: BLE001
            pixmap = q.QtGui.QPixmap()
        ghost = maya_hubqt.ghost_class()(pixmap, size, size, self.scale, anchor=(0.5, 0.5),
                                         name="skeldarChatGhost", backdrop="field")
        self._card_drag = {"item": item, "ghost": ghost, "aim": None}
        ghost.follow(gp)
        ghost.show()
        self.drag_move(gp)
        return True

    def drag_aim(self, gp):
        drag = getattr(self, "_card_drag", None) or {}
        from . import files
        if files.is_card((drag.get("item") and drag["item"].message.get("file")) or {}):
            return self.card_aim(gp, drag)
        import maya_filedrag
        under = maya_filedrag.section_under(maya_filedrag._names_at(gp.x(), gp.y()))
        viewport = False
        if under is None:
            try:
                viewport = maya_filedrag._viewport_at(gp.x(), gp.y())
            except Exception:                                # noqa: BLE001
                viewport = False
        return maya_filedrag.aim_for("chat", under, viewport)

    def card_aim(self, gp, drag):
        """A pose / animation card from the chat: into the Pose Library (a folder of its tree,
        else «From Chat»), onto a character in a viewport, onto the floor - else nothing."""
        x, y = gp.x(), gp.y()
        try:
            from maya_poselib import window as libwindow
            import maya_hubqt
            live = libwindow.live()
            folder = live.folder_at(x, y) if live is not None else None
            if folder is not None:
                return {"kind": "library", "folder": folder,
                        "text": u"в библиотеку · %s" % (folder or "Library")}
            if maya_hubqt.on_hub(x, y, control=libwindow.CONTROL):
                return {"kind": "library", "folder": None, "text": u"в библиотеку · From Chat"}
        except Exception:                                    # noqa: BLE001
            traceback.print_exc()
        try:
            from maya_scenesetup import droptarget
            if "snap" not in drag:
                drag["snap"] = droptarget.snapshot()
            aim = droptarget.character_target(x, y, drag["snap"], self.scale)
            if aim.get("kind") == "character":
                return {"kind": "apply", "root": aim.get("root"),
                        "text": u"на %s" % (aim.get("label") or u"персонажа")}
            if aim.get("text") != droptarget.NO_VIEWPORT:
                floor = droptarget.floor_at(x, y)
                if floor.get("kind") == "floor":
                    return {"kind": "apply", "point": floor.get("point"), "floor": True,
                            "text": u"новый персонаж на полу"}
        except Exception:                                    # noqa: BLE001
            traceback.print_exc()
        return {"kind": "none", "text": u"во вьюпорт или в библиотеку поз"}

    def drag_move(self, gp):
        drag = getattr(self, "_card_drag", None)
        if not drag:
            return
        aim = self.drag_aim(gp)
        drag["aim"] = aim
        drag["ghost"].follow(gp)
        f = drag["item"].message.get("file") or {}
        if aim["kind"] in DRAG_VERBS or aim["kind"] in ("library", "apply"):
            drag["ghost"].set_caption(u"%s · %s" % (f.get("name") or "", aim["text"]), True)
        else:
            drag["ghost"].set_caption(aim["text"], False)

    def drag_end(self, gp, cancel=False):
        drag, self._card_drag = getattr(self, "_card_drag", None), None
        if not drag:
            return None
        drag["ghost"].hide()
        drag["ghost"].deleteLater()
        if cancel:
            return None
        self._card_drag = drag
        aim = self.drag_aim(gp)
        self._card_drag = None
        item = drag["item"]
        if aim["kind"] in ("library", "apply"):
            target = dict(aim)
            if target.get("floor"):
                target["kind"] = "floor"
            elif aim["kind"] == "apply":
                target["kind"] = "character"
            self._later(lambda: self.file_action(item, aim["kind"], target=target))
            return aim["kind"]
        action = DRAG_VERBS.get(aim["kind"])
        if action is None:
            return None
        self._later(lambda: self.file_action(item, action))
        return action

    def _later(self, fn):
        """One idle later (the ghost gone first, a Maya import outside the mouse grab)."""
        try:
            import maya.utils
            maya.utils.executeDeferred(fn)
        except ImportError:
            fn()

    def dropped(self, paths):
        """Files from Explorer let go on the window: each sent into the open chat."""
        from . import files
        good = [path for path in paths if files.kind_of(path)]
        bad = [path for path in paths if not files.kind_of(path)]
        if not good:
            self.say(u"В чат можно отправить только .ma, .mb, .fbx и картинки (.png, .jpg).")
            return 0
        sent = 0
        for path in good:
            if self.send_path(path):
                sent += 1
        if bad and sent:
            self.say(u"Не отправлено (не сцена, не fbx и не картинка): %s" % ", ".join(
                os.path.basename(b) for b in bad[:3]))
        return sent

    def _quick_reactions(self, menu, message):
        """The menu's first row: the six quick reactions, mine lit."""
        q = _q()
        from . import emoji as _emoji
        holder = q.QtWidgets.QWidget(menu)
        holder.setObjectName("skeldarChatQuickReactions")
        lay = q.QtWidgets.QHBoxLayout(holder)
        lay.setContentsMargins(self.px(6), self.px(2), self.px(6), self.px(2))
        lay.setSpacing(self.px(2))
        mine = message.get("reactions") or {}
        font = q.QtGui.QFont(holder.font())
        font.setFamilies([font.family(), _emoji.FONT])
        font.setPixelSize(self.px(17))
        for e in _emoji.QUICK:
            b = q.QtWidgets.QToolButton(holder)
            from . import emojiart
            pm = emojiart.pixmap(e, self.px(22))
            if pm is not None:
                b.setIcon(q.QtGui.QIcon(pm))
                b.setIconSize(q.QtCore.QSize(self.px(22), self.px(22)))
            else:
                b.setText(e)
                b.setFont(font)
            b.setToolTip(e)
            b.setAutoRaise(True)
            b.setCursor(q.QtCore.Qt.PointingHandCursor)
            b.setFixedSize(self.px(30), self.px(30))
            if self.me_id() in mine.get(e, []):
                b.setStyleSheet("QToolButton {{ background: {0}; border-radius: {1}px; }}".format(
                    hubstyle.TOKENS["accent_tint"], self.px(6)))

            def go(*_a, e=e):
                menu.close()
                self.react(message, e)
            b.clicked.connect(go)
            lay.addWidget(b)
        action = q.QtWidgets.QWidgetAction(menu)
        action.setDefaultWidget(holder)
        return action

    def react(self, message, emoji_text):
        """Mine toggled on a message; the emoji becomes recently used."""
        if self.chat is None or not message:
            return None
        from . import emoji as _emoji
        try:
            on = self.session.react(self.chat, message["id"], emoji_text)
        except Exception as exc:                             # noqa: BLE001
            self.say(getattr(exc, "text", str(exc)))
            return None
        if on is None:
            self.say("Нет связи - реакция не отправлена")
            return None
        if on:
            set_var(_emoji.RECENT_VAR, _emoji.used(get_var(_emoji.RECENT_VAR), emoji_text))
        self.refresh()
        return on

    def pick_emoji(self, message=None, at=None):
        """The picker: into the composer, or a reaction on `message`."""
        from . import emoji as _emoji

        def picked(e):
            if message is not None:
                self.react(message, e)
                return
            set_var(_emoji.RECENT_VAR, _emoji.used(get_var(_emoji.RECENT_VAR), e))
            self.composer.insertPlainText(e)
            self.composer.setFocus()

        picker = picker_class()(self, picked)
        picker.search.setStyleSheet(
            "QLineEdit {{ background: {0}; border: 1px solid {1}; border-radius: {2}px;"
            " color: {3}; padding: 0 {4}px; }}".format(
                hubstyle.TOKENS["track"], hubstyle.TOKENS["track_edge"], self.px(5),
                hubstyle.TOKENS["text"], self.px(6)))
        w, h = picker.width(), picker.height()
        if at is None:
            if message is None:
                corner = self.emoji_button.mapToGlobal(self.emoji_button.rect().topLeft())
                area = _screen_area((corner.x(), corner.y()))
                at = (corner.x(), corner.y() - h - self.px(4))
                if area is not None and at[1] < area[1]:
                    # no room above the button: below it
                    at = (corner.x(), corner.y() + self.emoji_button.height() + self.px(4))
            else:
                at = _cursor() or (0, 0)
        area = _screen_area((int(at[0]), int(at[1])))
        at = clamp_into(int(at[0]), int(at[1]), w, h, area)
        picker.move(int(at[0]), int(at[1]))
        picker.search.setFocus()
        picker.show()
        self._picker = picker
        return picker

    def choose_avatar(self):
        q = _q()
        path, _filter = q.QtWidgets.QFileDialog.getOpenFileName(
            self.root, "Аватарка", "", "Картинки (*.png *.jpg *.jpeg *.bmp *.webp)")
        if path:
            self.set_avatar_from(path)

    def set_avatar_from(self, path):
        """The picture at `path` made square, uploaded, and shown at once."""
        from . import avatars
        try:
            data = avatars.prepare(path)
            me = self.session.set_avatar(data)
        except Exception as exc:                             # noqa: BLE001
            self.say(getattr(exc, "text", str(exc)), self.settings_line)
            return None
        if self.avatars is not None:
            try:
                self.avatars.put(me["id"], me["avatar_v"], data)
            except Exception:                                # noqa: BLE001
                pass
        self.say("Аватарка обновлена", self.settings_line)
        self.refresh()
        for widget in self.root.findChildren(avatar_widget_class()):
            widget.update()
        return me

    def copy_text(self, text):
        q = _q()
        q.QtWidgets.QApplication.clipboard().setText(text)

    def delete_message(self, message):
        try:
            self.session.delete(self.chat, message["id"])
        except Exception as exc:                             # noqa: BLE001
            self.say(getattr(exc, "text", str(exc)))
            return
        import maya_hubsound
        maya_hubsound.deleted()                 # the fireball (2026-10-22)

    def _typed(self):
        self._paint_send()
        if self.chat is None or not self.composer.toPlainText() or self.editing:
            return
        try:
            self.session.typing(self.chat)
        except Exception:                                    # noqa: BLE001
            pass

    def _searched(self, text):
        self.query = text
        self.refresh()

    def empty_list_text(self):
        if self.query:
            return "Ничего не найдено"
        if self.tab == "groups":
            return "Групп пока нет - ✎ создаст"
        return "Пока здесь никого, кроме вас"

    def set_tab(self, key):
        """A tab over the list: «Все», «Личные» (dm chats and everybody), «Группы»."""
        if key not in dict(look.TABS):
            return
        self.tab = key
        set_var(TAB_VAR, key)
        self.list_area.verticalScrollBar().setValue(0)
        self.refresh()

    def me_rows(self):
        """≡'s rows (look A, 2026-10-22): what the list's foot held."""
        return [(u"Мой профиль", "user", lambda: self.show_profile(self.session.state.me)),
                (u"Новый чат или группа", "pencil", lambda: self.show_pane("new")),
                (u"Настройки", "settings", lambda: self.show_pane("settings"))]

    def me_menu(self):
        """≡: my avatar, name and @nick over my card, New chat and Settings."""
        q = _q()
        w = q.QtWidgets
        menu = w.QMenu(self.root)
        menu.setObjectName("skeldarChatMeMenu")
        me = self.session.state.me or {}
        holder = w.QWidget(menu)
        holder.setObjectName("skeldarChatMeHead")
        row = w.QHBoxLayout(holder)
        row.setContentsMargins(self.px(10), self.px(8), self.px(16), self.px(8))
        row.setSpacing(self.px(10))
        face = avatar_widget_class()(self, me, self.px(36), False)
        face.clickable = False
        row.addWidget(face)
        texts = w.QVBoxLayout()
        texts.setSpacing(0)
        name = _label(look.display_name(me), None, "skeldarChatMeName")
        name.setFont(_font(name.font(), self.px(12), True))
        texts.addWidget(name)
        texts.addWidget(_label("@" + (me.get("nick") or "?"), "subtitle", "skeldarChatMeNick"))
        row.addLayout(texts, 1)
        head = w.QWidgetAction(menu)
        head.setDefaultWidget(holder)
        menu.addAction(head)
        menu.addSeparator()
        for label, icon_name, fn in self.me_rows():
            act = menu.addAction(hubqt.icon(icon_name, hubstyle.TOKENS["text2"], self.px(14)),
                                 label)
            act.triggered.connect(lambda *_a, f=fn: f())
        menu.popup(self.menu_button.mapToGlobal(
            q.QtCore.QPoint(0, self.menu_button.height())))
        self._menu = menu
        return menu

    # ---------------------------------------------------------- sign-in
    def _nick_typed(self, text):
        problem = look.nick_problem(text.strip().lower()) if text.strip() else None
        self.signin_line.setText(problem or "")
        self.signin_go.setEnabled(bool(text.strip()) and problem is None)

    def _show_code_field(self):
        self.code_field.setVisible(not self.code_field.isVisible())
        if self.code_field.isVisible():
            self.code_field.setFocus()

    def sign_in(self):
        nick = self.nick_field.text().strip().lower()
        if look.nick_problem(nick):
            self.signin_line.setText(look.nick_problem(nick))
            return False
        try:
            self.session.sign_in(nick)
        except Exception as exc:                             # noqa: BLE001
            self.signin_line.setText(getattr(exc, "text", str(exc)))
            return False
        self.signin_line.setText("")
        self.refresh()
        return True

    def sign_in_code(self):
        try:
            self.session.sign_in_code(self.code_field.text())
        except Exception as exc:                             # noqa: BLE001
            self.signin_line.setText(getattr(exc, "text", str(exc)))
            return False
        self.code_field.clear()
        self.refresh()
        return True

    def sign_out(self):
        self.session.sign_out()
        self.chat = None
        self.pane = "chat"
        self.single = "list"
        self.refresh()

    # ---------------------------------------------------------- groups, settings
    def _call(self, fn, line):
        try:
            result = fn()
        except Exception as exc:                             # noqa: BLE001
            self.say(getattr(exc, "text", str(exc)), line)
            return None
        self.say("", line)
        return result

    def _after_people(self):
        for name in ("_refresh_chats", "read_people"):
            fn = getattr(self.session, name, None)
            if fn is not None:
                try:
                    fn()
                except Exception:                            # noqa: BLE001
                    pass
        self.refresh()

    def write_to(self, user_id):
        line = self.new_line if self.pane == "new" else self.line
        chat_id = self._call(lambda: self.session.open_dm(user_id), line)
        if chat_id:
            self.open_chat(chat_id)

    def make_group(self):
        name = self.group_name.text().strip()
        if not name:
            self.say("Назовите группу", self.new_line)
            return
        if not self.picked:
            self.say("Отметьте хотя бы одного человека", self.new_line)
            return
        made = self._call(lambda: self.session.api.group(name, sorted(self.picked)), self.new_line)
        if made:
            self.group_name.clear()
            self.picked = set()
            self._after_people()
            chat_id = made.get("id") if isinstance(made, dict) else None
            if chat_id and chat_id in self.session.state.chats:
                self.open_chat(chat_id)

    def rename_me(self):
        name = self.name_field.text().strip()
        me = self._call(lambda: self.session.api.rename(name), self.settings_line)
        if me is not None:
            try:
                from . import records
                self.session.state.me = records.user(me)
                self.session.store.set_me(self.session.state.me)
            except Exception:                                # noqa: BLE001
                pass
            self.say("Сохранено", self.settings_line)
            self.refresh()

    def toggle_code(self):
        shown = self.code_show.text() == "Скрыть"
        self.code_text.setText("••••••••" if shown else (self.session.code() or ""))
        self.code_show.setText("Показать" if shown else "Скрыть")

    def copy_code(self):
        self.copy_text(self.session.code() or "")
        self.say("Код скопирован", self.settings_line)

    def _set_notify(self, what, on):
        try:
            from . import notify
            notify.set_option(what, on)
        except Exception:                                    # noqa: BLE001
            traceback.print_exc()

    def rename_chat(self):
        name = self.chat_name_field.text().strip()
        if self._call(lambda: self.session.api.rename_chat(self.chat, name),
                      self.members_line) is not None:
            self._after_people()

    def add_member(self, user_id):
        if self._call(lambda: self.session.api.add_member(self.chat, user_id),
                      self.members_line) is not None:
            self._after_people()

    def remove_member(self, user_id):
        if self._call(lambda: self.session.api.remove_member(self.chat, user_id),
                      self.members_line) is not None:
            self._after_people()

    def _clear(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _person_row(self, user, buttons):
        q = _q()
        w = q.QtWidgets
        row = w.QWidget()
        lay = w.QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        online = is_online(user, self.session.state.online)
        lay.addWidget(avatar_widget_class()(self, user, self.px(26)))
        name = _label(look.display_name(user) + "  @" + str(user.get("nick") or ""), None)
        name.setStyleSheet("color: {0};".format(hubstyle.TOKENS["text" if online else "text2"]))
        if not online:
            name.setToolTip(look.last_seen(user.get("last_seen"), _now_ms()))
        lay.addWidget(name, 1)
        for text, role, fn in buttons:
            b = _button(text, role, None, None, self.scale)
            b.clicked.connect(lambda *_a, f=fn: f())
            lay.addWidget(b)
        return row

    def _fill_new(self):
        q = _q()
        self._clear(self.new_rows)
        people = look.everybody(getattr(self.session.state, "people", []), self.me_id(),
                                self.new_search.text())
        if not people:
            self.new_rows.addWidget(_label("Никого не нашли" if self.new_search.text().strip()
                                           else "Пока здесь никого, кроме вас", "note"))
        for u in people:
            row = q.QtWidgets.QWidget()
            lay = q.QtWidgets.QHBoxLayout(row)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.addWidget(avatar_widget_class()(self, u, self.px(26)))
            box = q.QtWidgets.QCheckBox(look.display_name(u) + "  @" + u.get("nick", ""))
            box.setChecked(u["id"] in self.picked)
            box.toggled.connect(lambda on, uid=u["id"]: (self.picked.add(uid) if on
                                                         else self.picked.discard(uid)))
            lay.addWidget(box, 1)
            write = _button("Написать", "primary", None, None, self.scale)
            write.clicked.connect(lambda *_a, uid=u["id"]: self.write_to(uid))
            lay.addWidget(write)
            self.new_rows.addWidget(row)
        self.new_rows.addStretch(1)

    def _fill_members(self):
        self._clear(self.members_rows)
        c = self.session.state.chats.get(self.chat) or {}
        admin = c.get("admin") == self.me_id()
        if not self.chat_name_field.hasFocus():
            self.chat_name_field.setText(c.get("name") or "")
        self.chat_name_field.setEnabled(admin)
        self.chat_rename.setEnabled(admin)
        ids = set(m.get("id") for m in c.get("members", []))
        for u in c.get("members", []):
            buttons = []
            if admin and u.get("id") != self.me_id():
                buttons.append(("Удалить", "danger", lambda uid=u["id"]: self.remove_member(uid)))
            elif u.get("id") == self.me_id():
                buttons.append(("Выйти", "danger", lambda uid=u["id"]: self.remove_member(uid)))
            self.members_rows.addWidget(self._person_row(u, buttons))
        if admin:
            more = [u for u in look.everybody(getattr(self.session.state, "people", []),
                                              self.me_id()) if u["id"] not in ids]
            if more:
                self.members_rows.addWidget(_label("Добавить", "heading"))
            for u in more:
                self.members_rows.addWidget(self._person_row(
                    u, [("Добавить", "primary", lambda uid=u["id"]: self.add_member(uid))]))
        self.members_rows.addStretch(1)

    def _fill_settings(self):
        me = self.session.state.me or {}
        self.settings_avatar.set_user(me, dot=False)
        if not self.name_field.hasFocus():
            self.name_field.setText(me.get("name") or "")
        try:
            from . import notify
            for box, what in ((self.notify_box, "viewport"), (self.sound_box, "sound")):
                box.blockSignals(True)
                box.setChecked(notify.option(what))
                box.blockSignals(False)
        except Exception:                                    # noqa: BLE001
            pass

    # ---------------------------------------------------------- motion
    def animate(self):
        if not hubmotion.enabled():
            self.feed.entering.clear()
            self.feed.flashing.clear()
            self.feed.folding = []
            self.list.pops.clear()
            self.list.glow = dict((r["id"], 1.0 if r["id"] == self.list.hovered else 0.0)
                                  for r in self.list.rows)
            self.list.update()
            self.feed.update()
            return
        if not self.timer.isActive():
            self._last_tick = time.monotonic()
            self.timer.start()

    def _tick(self):
        now = time.monotonic()
        dt = (now - (self._last_tick or now)) * 1000.0
        self._last_tick = now
        busy = False
        try:
            busy = self.list.tick(dt) or busy
            busy = self.feed.tick(dt) or busy
        except RuntimeError:
            busy = False
        if not busy:
            self.timer.stop()

    def _each_second(self):
        st = self.session.state
        if self.root is None or not self.root.isVisible():
            return
        now = time.monotonic()
        if any(now - t < look.TYPING_S + 1.5 for marks in st.typing.values()
               for t in marks.values()) or any(st.pending.values()):
            self.refresh()
        cache = self.avatars
        if cache is not None and cache.take_changed():
            for widget in self.root.findChildren(avatar_widget_class()):
                widget.update()
            self.list.update()
            self.feed.update()
        anim = self.feed.anim
        if anim is not None and anim.take_changed():
            self.feed.update()
        try:
            from . import thumbs
            held = thumbs.cache(self.session)
            if held is not None and held.take_changed():
                self.feed.update()
        except Exception:                                    # noqa: BLE001
            pass

    # ---------------------------------------------------------- place, size, show
    def _grab(self, point):
        pos = self.root.pos()
        self._grab_at = (point[0] - pos.x(), point[1] - pos.y())

    def _drag(self, point):
        grab = getattr(self, "_grab_at", (0, 0))
        self.root.move(point[0] - grab[0], point[1] - grab[1])

    def _drop(self):
        self.remember()

    def remember(self):
        set_var(POS_VAR, "%d,%d" % (self.root.x(), self.root.y()))
        set_var(SIZE_VAR, "%d,%d" % (self.root.width(), self.root.height()))

    def resized(self):
        self._layout_columns()
        self._paint_down()
        g = self.grip
        g.move(self.card.width() - g.width(), self.card.height() - g.height())
        g.raise_()

    def place(self, origin=None):
        size = _pair(get_var(SIZE_VAR)) or (self.px(look.DEFAULT_SIZE[0]),
                                            self.px(look.DEFAULT_SIZE[1]))
        size = (max(size[0], self.px(look.LEAST_SIZE[0])), max(size[1], self.px(look.LEAST_SIZE[1])))
        self.root.resize(size[0], size[1])
        pos = _pair(get_var(POS_VAR))
        screens = _screens()
        if pos is None or not any(_on(sc, (pos[0] + size[0] // 2, pos[1] + self.px(10)))
                                  for sc in screens):
            point = origin or _cursor() or (screens[0][0] + screens[0][2] // 2,
                                            screens[0][1] + screens[0][3] // 2)
            sc = next((s_ for s_ in screens if _on(s_, point)), screens[0])
            pos = (sc[0] + (sc[2] - size[0]) // 2, sc[1] + (sc[3] - size[1]) // 2)
        self.root.move(pos[0], pos[1])

    def show_at(self, origin=None):
        self.place(origin)
        self.root.show()
        self.root.raise_()
        self.refresh()
        self.resized()
        if origin is not None and self._burst(True, origin, self._opened):
            return True
        self._opened()
        return False

    def close_into(self, origin, done):
        self.remember()
        if origin is not None and self._burst(False, origin, lambda: self._folded(done)):
            return True
        self._folded(done)
        return False

    def _burst(self, opening, origin, done):
        q = _q()
        self.root.setAttribute(q.QtCore.Qt.WA_TransparentForMouseEvents, True)
        try:
            started = self.burster.run(opening, origin, done)
        except Exception:                                    # noqa: BLE001
            traceback.print_exc()
            started = False
        if not started:
            self._end_burst()
        return started

    def _end_burst(self):
        q = _q()
        try:
            self.burster.stop()
        except Exception:                                    # noqa: BLE001
            pass
        try:
            self.root.setAttribute(q.QtCore.Qt.WA_TransparentForMouseEvents, False)
            self.frame.update()
        except RuntimeError:
            pass

    def _opened(self):
        self._end_burst()
        self._read_if_seen()

    def _folded(self, done):
        self._end_burst()
        try:
            self.root.hide()
        except RuntimeError:
            pass
        if done is not None:
            done()

    def _burst_parts(self):
        return hubqt.burst_parts(self.frame, self.title, self.pages, None, self.scale)

    def _burst_face(self):
        return hubstyle.TOKENS["card"]

    def _gone(self):
        try:
            self.session.unlisten(self._heard)
        except Exception:                                    # noqa: BLE001
            pass
        self.root = None

    def destroy(self):
        self.session.unlisten(self._heard)
        if getattr(self, "profile", None) is not None:
            try:
                self.profile.close()
            except Exception:                                # noqa: BLE001
                pass
        root, self.root = self.root, None
        if root is not None and hubqt._valid(root):
            root.hide()
            root.deleteLater()


def _resize_filter(win):
    q = _q()
    if "resize" not in _CLASSES:

        class ResizeWatch(q.QtCore.QObject):

            def __init__(self, win, parent=None):
                super(ResizeWatch, self).__init__(parent)
                self.win = win

            def eventFilter(self, obj, event):               # noqa: N802
                if event.type() == q.QtCore.QEvent.Resize:
                    try:
                        self.win.resized()
                    except Exception:                        # noqa: BLE001
                        traceback.print_exc()
                elif event.type() in (q.QtCore.QEvent.Show, q.QtCore.QEvent.WindowActivate):
                    try:
                        self.win._read_if_seen()
                    except Exception:                        # noqa: BLE001
                        pass
                return False

        _CLASSES["resize"] = ResizeWatch
    watch = _CLASSES["resize"](win, win.root if win.root is not None else None)
    win._watch = watch                                      # held
    return watch


FILE_MENU = (("open", "Open"), ("import", "Import"), ("save", u"Сохранить как…"),
             ("stash", u"В Stash"))
FILE_MORE = (("save", u"Сохранить как…"), ("stash", u"В Stash"))
DRAG_VERBS = {"import": "import", "stash": "stash", "send": "share"}


def _drop_filter(win):
    """Files from Explorer dropped anywhere on the window, the composer included."""
    if "drop_filter" not in _CLASSES:
        q = _q()
        QtCore = q.QtCore

        class DropFilter(QtCore.QObject):
            def __init__(self, win, parent=None):
                super(DropFilter, self).__init__(parent)
                self.win = win

            def eventFilter(self, obj, event):               # noqa: N802
                kind = event.type()
                if kind in (QtCore.QEvent.DragEnter, QtCore.QEvent.DragMove):
                    if _local_paths(event.mimeData()):
                        event.acceptProposedAction()
                        return True
                elif kind == QtCore.QEvent.Drop:
                    paths = _local_paths(event.mimeData())
                    if paths:
                        event.acceptProposedAction()
                        self.win.dropped(paths)
                        return True
                return False

        _CLASSES["drop_filter"] = DropFilter
    return _CLASSES["drop_filter"](win, win.root)


def _local_paths(mime):
    if mime is None or not mime.hasUrls():
        return []
    return [u.toLocalFile() for u in mime.urls() if u.isLocalFile() and u.toLocalFile()]


def send_card(card):
    """A Pose Library card sent into the chat that is open in the window (its drag, 2026-10-22)."""
    win = window()
    if win is None or win.chat is None:
        return u"Откройте чат, чтобы отправить в него карточку."
    cid = win.send_card(card)
    return (u"%s - в чат" % os.path.basename(card.rstrip("/\\"))) if cid else (win.line.text() or "")


def send_path(path):
    """A file sent into the chat that is open in the window (a Stash / Shared drop)."""
    win = window()
    if win is None or win.chat is None:
        return u"Откройте чат, чтобы отправить в него файл."
    cid = win.send_path(path)
    return (u"%s - в чат" % os.path.basename(path)) if cid else (win.line.text() or "")


def _screens():
    try:
        import maya_hubpop
        return maya_hubpop.screens()
    except Exception:                                        # noqa: BLE001
        return [(0, 0, 1920, 1080)]


def _on(screen, point):
    return screen[0] <= point[0] < screen[0] + screen[2] and \
        screen[1] <= point[1] < screen[1] + screen[3]


def clamp_into(x, y, w, h, area):
    """(x, y) moved so a w x h box lies inside area (x, y, w, h); a box larger than the
    area keeps its top-left on the area's. None: unchanged."""
    if area is None:
        return (x, y)
    ax, ay, aw, ah = area
    x = max(ax, min(x, ax + aw - w))
    y = max(ay, min(y, ay + ah - h))
    return (x, y)


def _screen_area(point):
    """(x, y, w, h) of the available geometry of the screen holding `point`, else the
    primary screen's; None without a screen."""
    try:
        q = _q()
        app = q.QtGui.QGuiApplication
        screen = app.screenAt(q.QtCore.QPoint(int(point[0]), int(point[1]))) \
            or app.primaryScreen()
        if screen is None:
            return None
        g = screen.availableGeometry()
        return (g.x(), g.y(), g.width(), g.height())
    except Exception:                                        # noqa: BLE001
        return None


def _cursor():
    try:
        q = _q()
        pos = q.QtGui.QCursor.pos()
        return (pos.x(), pos.y())
    except Exception:                                        # noqa: BLE001
        return None


# ------------------------------------------------------------------ one window a Maya

def _held():
    held = getattr(sys, "_skeldar_chat_window", None)
    if held is None:
        held = {"win": None}
        sys._skeldar_chat_window = held
    return held


def window():
    """The standing window, or None."""
    win = _held()["win"]
    if win is None or win.root is None or not hubqt._valid(win.root):
        _held()["win"] = None
        return None
    return win


def is_open():
    win = window()
    return bool(win is not None and win.root.isVisible())


def show(origin=None, session=None):
    """The window up (made on first use), out of `origin`."""
    win = window()
    if win is None:
        if session is None:
            import maya_chat
            session = maya_chat.current()
        win = ChatWindow(session)
        _held()["win"] = win
    if win.root.isVisible():
        win.root.raise_()
        win.root.activateWindow()
        win.frame.flash = 1.0
        win.frame.update()
        return win
    win.show_at(origin)
    _paint_rail(True)
    return win


def close_window(origin=None):
    win = window()
    if win is None or not win.root.isVisible():
        return False
    win.close_into(origin, lambda: _paint_rail(False))
    return True


def toggle(origin=None, session=None):
    if is_open():
        return close_window(origin)
    show(origin, session)
    return True


def destroy():
    """The window gone now (a plugin update rebuilds it by name)."""
    win = _held()["win"]
    _held()["win"] = None
    if win is not None:
        win.destroy()
    q = _q()
    if q is not None:
        for w in q.QtWidgets.QApplication.topLevelWidgets():
            if w.objectName() == ROOT_NAME:
                w.hide()
                w.deleteLater()


def _paint_rail(on):
    try:
        import maya_hub
        maya_hub.paint_floating("chat", on)
    except Exception:                                        # noqa: BLE001
        pass
