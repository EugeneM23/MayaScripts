"""The chat window (plan docs/superpowers/plans/2026-10-20-chat-window.md, spec
docs/superpowers/specs/2026-10-19-chat-messenger-design.md "The window").

A floating hub window in look B: drawn by our own widgets and QPainter from the session's
state, listening to it. The window never talks to the server but through the session
(and its `api` for the friends and group presses). No modal dialog anywhere.
"""
import html
import math
import sys
import time
import traceback

import maya_hubmotion as hubmotion
import maya_hubqt as hubqt
import maya_hubstyle as hubstyle
import maya_hubwindow as hubwindow

from . import look

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


def paint_avatar(p, rect, user, scale):
    """A user's circle: their colour and initials."""
    q = _q()
    p.save()
    p.setRenderHint(q.QtGui.QPainter.Antialiasing)
    p.setPen(q.QtCore.Qt.NoPen)
    p.setBrush(q.QtGui.QColor(look.user_colour((user or {}).get("id"))))
    p.drawEllipse(rect)
    font = q.QtGui.QFont(p.font())
    font.setBold(True)
    font.setPixelSize(max(6, int(rect.height() * 0.38)))
    p.setFont(font)
    p.setPen(q.QtGui.QColor("#ffffff"))
    p.drawText(rect, q.QtCore.Qt.AlignCenter, look.initials(user))
    p.restore()


def _font(base, px_size, bold=False):
    q = _q()
    f = q.QtGui.QFont(base)
    f.setPixelSize(max(6, int(px_size)))
    f.setBold(bold)
    return f


def rich(text):
    """A message's text as HTML: escaped, links as anchors, new lines kept."""
    from . import records
    out = []
    for kind, piece in records.runs(text or ""):
        if kind == "link":
            out.append('<a href="{0}">{1}</a>'.format(html.escape(piece, quote=True),
                                                      html.escape(piece)))
        else:
            out.append(html.escape(piece))
    return "".join(out).replace("\n", "<br>")


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

            def row_h(self):
                return hubstyle.px(54, self.win.scale)

            def set_rows(self, rows):
                now = _now_ms()
                for r in rows:
                    before = self._unread.get(r["id"])
                    if before is not None and before != r["unread"] and r["unread"]:
                        self.pops[r["id"]] = now
                    self._unread[r["id"]] = r["unread"]
                self.rows = rows
                self.setMinimumHeight(max(1, len(rows) * self.row_h()))
                if self.pops:
                    self.win.animate()
                self.update()

            def index_at(self, y):
                i = int(y // self.row_h())
                return i if 0 <= i < len(self.rows) else -1

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
                    self.win.open_chat(self.rows[i]["id"])

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
                h = self.row_h()
                w = self.width()
                now = _now_ms()
                for i, r in enumerate(self.rows):
                    top = i * h
                    rect = QtCore.QRectF(px(4), top + px(2), w - px(8), h - px(4))
                    glow = self.glow.get(r["id"], 0.0)
                    if r["id"] == self.selected:
                        p.setPen(QtCore.Qt.NoPen)
                        p.setBrush(_colour("card_active"))
                        p.drawRoundedRect(rect, px(6), px(6))
                        p.setPen(QtGui.QPen(_colour("accent", 0.9), max(1.0, s)))
                        p.setBrush(QtCore.Qt.NoBrush)
                        p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), px(6), px(6))
                    elif glow > 0.002:
                        p.setPen(QtCore.Qt.NoPen)
                        p.setBrush(_colour("hover", glow))
                        p.drawRoundedRect(rect.translated(0, -glow * s), px(6), px(6))
                    lift = -glow * s
                    av = QtCore.QRectF(px(10), top + (h - px(38)) / 2.0 + lift, px(38), px(38))
                    paint_avatar(p, av, r["user"], s)
                    x0 = av.right() + px(10)
                    right = w - px(12)
                    p.setFont(_font(self.font(), px(11.5), True))
                    p.setPen(_colour("text"))
                    fm = QtGui.QFontMetrics(p.font())
                    t_font = _font(self.font(), px(9.5))
                    tfm = QtGui.QFontMetrics(t_font)
                    tw = tfm.horizontalAdvance(r["time"]) if r["time"] else 0
                    title = fm.elidedText(r["title"], QtCore.Qt.ElideRight,
                                          int(right - x0 - tw - px(6)))
                    p.drawText(QtCore.QPointF(x0, top + px(22) + lift), title)
                    if r["time"]:
                        p.setFont(t_font)
                        p.setPen(_colour("faint"))
                        p.drawText(QtCore.QPointF(right - tw, top + px(21) + lift), r["time"])
                    p.setFont(_font(self.font(), px(10)))
                    pfm = QtGui.QFontMetrics(p.font())
                    badge_w = 0
                    if r["unread"]:
                        text = look.count_text(r["unread"])
                        bf = _font(self.font(), px(9), True)
                        bfm = QtGui.QFontMetrics(bf)
                        badge_w = max(px(18), bfm.horizontalAdvance(text) + px(10))
                        k = pop_scale(now - self.pops.get(r["id"], -10 ** 9))
                        badge = QtCore.QRectF(0, 0, badge_w * k, px(18) * k)
                        badge.moveCenter(QtCore.QPointF(right - badge_w / 2.0,
                                                        top + px(37) + lift))
                        p.setPen(QtCore.Qt.NoPen)
                        p.setBrush(_colour("accent"))
                        p.drawRoundedRect(badge, badge.height() / 2, badge.height() / 2)
                        p.setFont(bf)
                        p.setPen(QtGui.QColor(hubstyle.TOKENS.get("on_accent", "#1b1c1f")))
                        p.drawText(badge, QtCore.Qt.AlignCenter, text)
                        p.setFont(_font(self.font(), px(10)))
                    p.setPen(_colour("accent_text" if r["typing"] else "muted"))
                    sub = pfm.elidedText(r["preview"], QtCore.Qt.ElideRight,
                                         int(right - x0 - badge_w - px(6)))
                    p.drawText(QtCore.QPointF(x0, top + px(41) + lift), sub)
                if not self.rows:
                    p.setPen(_colour("faint"))
                    p.setFont(_font(self.font(), px(10)))
                    p.drawText(QtCore.QRectF(0, px(10), w, px(40)), QtCore.Qt.AlignCenter,
                               self.win.empty_list_text())

        _CLASSES["list"] = ChatList
    return _CLASSES["list"]


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
                 "meta_at", "failed_rect", "height")

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
                self._known = None
                self._laid_w = -1
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
                self._known = {"keys": set(keys),
                               "pending": set(i.key() for i in items if i.pending)}
                self.items = items
                self.ctx = ctx
                self.relayout()
                if self.entering or self.flashing or self.folding:
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

            def _doc(self, item, width):
                key = (item.key(), item.text, int(width))
                doc = self.docs.get(key)
                if doc is None:
                    doc = QtGui.QTextDocument()
                    doc.setDocumentMargin(0)
                    doc.setDefaultFont(_font(self.font(), hubstyle.px(11, self.win.scale)))
                    doc.setDefaultStyleSheet("a {{ color: {0}; }}".format(
                        hubstyle.TOKENS["accent_text"]))
                    doc.setHtml('<span style="color:{0}">{1}</span>'.format(
                        hubstyle.TOKENS["text"], rich(item.text)))
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
                side = px(12)
                avatar = px(28) if group else 0
                max_w = min(0.74 * (width - 2 * side - avatar), px(520))
                pad_x, pad_y = px(10), px(6)
                small = _font(self.font(), px(9))
                sfm = QtGui.QFontMetrics(small)
                name_font = _font(self.font(), px(10), True)
                nfm = QtGui.QFontMetrics(name_font)
                y = px(8)
                boxes = []
                for item in self.items:
                    box = Box(item)
                    if item.kind == "day":
                        h = px(28)
                        box.rect = QtCore.QRectF(0, y, width, h)
                        box.height = h
                        boxes.append(box)
                        y += h
                        continue
                    msg = item.message
                    inner = max(px(40), max_w - 2 * pad_x)
                    doc = self._doc(item, inner)
                    box.doc = doc
                    doc_w, doc_h = doc.size().width(), doc.size().height()
                    meta = []
                    if msg.get("edited_at"):
                        meta.append("изм.")
                    meta.append(look.hm(msg.get("at") or _now_ms()))
                    tick = {"clock": "◷", "sent": "✓", "read": "✓✓", "failed": "!"}.get(item.tick, "")
                    if tick:
                        meta.append(tick)
                    box.meta = " ".join(meta)
                    meta_w = sfm.horizontalAdvance(box.meta)
                    content_w = max(doc_w, meta_w)
                    name_h = 0
                    if group and not item.mine and item.first:
                        name = self.ctx.get("name_of", lambda uid: uid)(msg.get("from_id"))
                        name_h = nfm.height() + px(2)
                        content_w = max(content_w, nfm.horizontalAdvance(name))
                    quote_h = 0
                    reply = msg.get("reply_to")
                    original = None
                    if reply:
                        original = look.find(self.ctx.get("messages"), reply)
                        quote_h = px(34)
                        content_w = max(content_w, min(inner, px(160)))
                    bw = content_w + 2 * pad_x
                    bh = pad_y + name_h + quote_h + doc_h + px(2) + sfm.height() + pad_y
                    gap = px(8) if item.first else px(2)
                    y += gap
                    if item.mine:
                        x = width - side - bw
                    else:
                        x = side + avatar
                    box.bubble = QtCore.QRectF(x, y, bw, bh)
                    cx = x + pad_x
                    cy = y + pad_y
                    if name_h:
                        box.name_at = QtCore.QPointF(cx, cy + nfm.ascent())
                        cy += name_h
                    if quote_h:
                        qrect = QtCore.QRectF(cx, cy, bw - 2 * pad_x, quote_h - px(4))
                        if original is not None:
                            qname = self.ctx.get("name_of", lambda uid: uid)(
                                original.get("from_id"))
                            qtext = "сообщение удалено" if original.get("deleted") \
                                else " ".join(str(original.get("text") or "").split())
                        else:
                            qname, qtext = "", "сообщение"
                        box.quote = (qrect, reply, qname, qtext)
                        cy += quote_h
                    box.doc_at = QtCore.QPointF(cx, cy)
                    cy += doc_h + px(2)
                    box.meta_at = QtCore.QPointF(x + bw - pad_x - meta_w, cy + sfm.ascent())
                    h = bh
                    if item.tick == "failed":
                        box.failed_rect = QtCore.QRectF(x, y + bh + px(2), bw, sfm.height() + px(2))
                        h += sfm.height() + px(4)
                    box.rect = QtCore.QRectF(0, y, width, h)
                    box.height = h
                    boxes.append(box)
                    y += h
                return boxes

            # ---------------------------------------------------------- motion
            def tick(self, dt):
                now = _now_ms()
                for store, ms in ((self.entering, ENTER_MS), (self.flashing, SENT_FLASH_MS)):
                    for k, start in list(store.items()):
                        if now - start >= ms:
                            del store[k]
                self.folding = [f for f in self.folding if now - f[2] < FOLD_MS]
                busy = bool(self.entering or self.flashing or self.folding)
                self.update()
                return busy

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
                now = _now_ms()
                small = _font(self.font(), px(9))
                group = (self.ctx.get("chat") or {}).get("kind") == "group"
                for top, height, start in self.folding:
                    k = 1.0 - (now - start) / float(FOLD_MS)
                    p.setPen(QtCore.Qt.NoPen)
                    p.setBrush(_colour("card_active", 0.6 * k))
                    r = QtCore.QRectF(self.width() * 0.25, top + height * (1 - k) / 2,
                                      self.width() * 0.5, height * k)
                    p.drawRoundedRect(r, px(8), px(8))
                for box in self.boxes:
                    if box.rect.bottom() < clip.top() - px(40) or \
                            box.rect.top() > clip.bottom() + px(40):
                        continue
                    item = box.item
                    if item.kind == "day":
                        p.setFont(_font(self.font(), px(9.5), True))
                        fm = QtGui.QFontMetrics(p.font())
                        w = fm.horizontalAdvance(item.text) + px(16)
                        pill = QtCore.QRectF((self.width() - w) / 2.0,
                                             box.rect.top() + px(5), w, px(18))
                        p.setPen(QtCore.Qt.NoPen)
                        p.setBrush(_colour("field"))
                        p.drawRoundedRect(pill, px(9), px(9))
                        p.setPen(_colour("muted"))
                        p.drawText(pill, QtCore.Qt.AlignCenter, item.text)
                        continue
                    p.save()
                    key = item.key()
                    if key in self.entering:
                        u = (now - self.entering[key]) / float(ENTER_MS)
                        p.translate(0, (1.0 - back_out(u)) * px(14))
                        p.setOpacity(max(0.0, min(1.0, u * 2.0)))
                    bubble = box.bubble
                    face = look.MINE if item.mine else hubstyle.TOKENS["card_active"]
                    if key in self.flashing:
                        k = 1.0 - (now - self.flashing[key]) / float(SENT_FLASH_MS)
                        colour = _blend(face, "accent", 0.45 * k)
                    else:
                        colour = _q().QtGui.QColor(face)
                    if item.pending and item.tick == "clock":
                        colour.setAlphaF(0.75)
                    p.setPen(QtCore.Qt.NoPen)
                    p.setBrush(colour)
                    p.drawRoundedRect(bubble, px(10), px(10))
                    if item.last:          # the tail corner, square on the sender's side
                        corner = QtCore.QRectF(bubble.right() - px(10) if item.mine
                                               else bubble.left(), bubble.bottom() - px(10),
                                               px(10), px(10))
                        p.drawRect(corner)
                    if group and not item.mine and item.last:
                        av = QtCore.QRectF(px(12), bubble.bottom() - px(24), px(24), px(24))
                        paint_avatar(p, av, self.ctx.get("user_of", lambda uid: {"id": uid})(
                            item.message.get("from_id")), s)
                    if box.name_at is not None:
                        uid = item.message.get("from_id")
                        p.setFont(_font(self.font(), px(10), True))
                        p.setPen(_q().QtGui.QColor(look.user_colour(uid)))
                        p.drawText(box.name_at, self.ctx.get("name_of", lambda u: u)(uid))
                    if box.quote is not None:
                        qrect, _rid, qname, qtext = box.quote
                        p.setPen(QtCore.Qt.NoPen)
                        p.setBrush(_colour("panel", 0.35))
                        p.drawRoundedRect(qrect, px(4), px(4))
                        p.setBrush(_colour("accent"))
                        p.drawRect(QtCore.QRectF(qrect.left(), qrect.top(), px(2), qrect.height()))
                        p.setFont(_font(self.font(), px(9.5), True))
                        p.setPen(_colour("accent_text"))
                        fm = QtGui.QFontMetrics(p.font())
                        p.drawText(QtCore.QPointF(qrect.left() + px(7), qrect.top() + fm.ascent()
                                                  + px(2)),
                                   fm.elidedText(qname, QtCore.Qt.ElideRight,
                                                 int(qrect.width() - px(10))))
                        p.setFont(_font(self.font(), px(9.5)))
                        p.setPen(_colour("text2"))
                        fm2 = QtGui.QFontMetrics(p.font())
                        p.drawText(QtCore.QPointF(qrect.left() + px(7),
                                                  qrect.bottom() - fm2.descent() - px(2)),
                                   fm2.elidedText(qtext, QtCore.Qt.ElideRight,
                                                  int(qrect.width() - px(10))))
                    p.save()
                    p.translate(box.doc_at)
                    box.doc.drawContents(p)
                    p.restore()
                    p.setFont(small)
                    if item.tick == "read":
                        p.setPen(_colour("accent_text"))
                    elif item.tick == "failed":
                        p.setPen(_colour("danger"))
                    else:
                        p.setPen(_colour("muted"))
                    p.drawText(box.meta_at, box.meta)
                    if box.failed_rect is not None:
                        p.setPen(_colour("danger"))
                        p.drawText(box.failed_rect,
                                   QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                                   if item.mine else QtCore.Qt.AlignLeft,
                                   "не отправлено — повторить")
                    p.restore()

            # ---------------------------------------------------------- input
            def box_at(self, point):
                for box in self.boxes:
                    if box.bubble is not None and box.bubble.contains(point):
                        return box, "bubble"
                    if box.failed_rect is not None and box.failed_rect.contains(point):
                        return box, "failed"
                return None, ""

            def mousePressEvent(self, event):              # noqa: N802
                pos = event.position() if hasattr(event, "position") else QtCore.QPointF(event.pos())
                box, where = self.box_at(pos)
                if box is None:
                    return
                if event.button() == QtCore.Qt.RightButton:
                    gp = event.globalPosition().toPoint() if hasattr(event, "globalPosition") \
                        else event.globalPos()
                    self.win.message_menu(box.item, gp)
                    return
                if event.button() != QtCore.Qt.LeftButton:
                    return
                if where == "failed":
                    self.win.retry(box.item)
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
                box, _where = self.box_at(pos)
                link = False
                if box is not None and box.doc is not None:
                    link = bool(box.doc.documentLayout().anchorAt(pos - box.doc_at))
                    link = link or (box.quote is not None and box.quote[0].contains(pos))
                self.setCursor(QtCore.Qt.PointingHandCursor if link else QtCore.Qt.ArrowCursor)

            def top_of(self, message_id):
                for box in self.boxes:
                    if box.item.kind == "msg" and box.item.message.get("id") == message_id:
                        return box.rect.top()
                return None

        _CLASSES["feed"] = Feed
    return _CLASSES["feed"]


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
                self.setPlaceholderText("Сообщение…")
                self.setTabChangesFocus(True)
                self.document().contentsChanged.connect(self._grow)
                self._grow()

            def _grow(self):
                # Every line plus what stands around them: the document's own
                # margin (top and bottom) and the frame, border and padding the
                # stylesheet gives (contentsMargins). Leaving the document margin
                # out clipped the one line by 8 px at the bottom.
                lines = max(1, min(look.MAX_LINES, int(self.document().size().height())))
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
        self.pane = "chat"           # chat | friends | new | settings | members
        self.single = "list"         # in one column: list | right
        self.reply_to = None         # a message id
        self.editing = None          # a message id
        self.query = ""
        self.history_done = set()
        self.unseen = 0              # messages that came while scrolled up
        self._dirty = False
        self._last_tick = None
        self.root = None
        self.burster = None
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
        column.addWidget(card, 1)
        self.card = card
        body = w.QVBoxLayout(card)
        body.setContentsMargins(px(6), px(6), px(6), px(6))
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

        sheet = hubstyle.stylesheet(s)
        root.setStyleSheet(
            sheet + "\n#skeldarChatFrame {{ border: none; background: transparent; }}"
            "\nQScrollArea {{ background: transparent; border: none; }}"
            "\n#skeldarChatList, #skeldarChatFeed, #skeldarChatFriendsBody, #skeldarChatNewBody,"
            " #skeldarChatMembersBody, #skeldarChatViewport {{ background: transparent; }}"
            "\nQPlainTextEdit#skeldarChatComposer {{ background: {0}; color: {1};"
            " border: 1px solid {2}; border-radius: {3}px; padding: {4}px; }}"
            "\n#skeldarChatLeft {{ background: transparent; }}"
            "\n#skeldarChatSplit {{ background: {2}; }}".format(
                hubstyle.TOKENS["field"], hubstyle.TOKENS["text"],
                hubstyle.TOKENS["track_edge"], px(6), px(4)))
        hubwindow.dress(frame, s)
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

        left = w.QWidget()
        left.setObjectName("skeldarChatLeft")
        left.setFixedWidth(px(look.LIST_W))
        lv = w.QVBoxLayout(left)
        lv.setContentsMargins(0, 0, px(4), 0)
        lv.setSpacing(px(4))
        top = w.QHBoxLayout()
        self.search = w.QLineEdit()
        self.search.setObjectName("skeldarChatSearch")
        self.search.setPlaceholderText("Поиск")
        self.search.textChanged.connect(self._searched)
        top.addWidget(self.search, 1)
        new = _button("", "tool", "pencil", "skeldarChatNew", self.scale, "Новый чат или группа")
        new.clicked.connect(lambda *_a: self.show_pane("new"))
        top.addWidget(new)
        lv.addLayout(top)
        self.list = list_class()(self)
        self.list_area = self._scroll(self.list, "skeldarChatListArea")
        lv.addWidget(self.list_area, 1)
        foot = w.QHBoxLayout()
        self.me_label = _label("", "label", "skeldarChatMe")
        foot.addWidget(self.me_label, 1)
        self.friends_button = _button("", "tool", "users", "skeldarChatFriendsButton", self.scale,
                                      "Друзья")
        self.friends_button.clicked.connect(lambda *_a: self.show_pane("friends"))
        foot.addWidget(self.friends_button)
        people = _button("", "tool", "world", "skeldarChatPeopleButton", self.scale,
                         "Все пользователи")
        people.clicked.connect(lambda *_a: self.show_pane("people"))
        foot.addWidget(people)
        settings = _button("", "tool", "settings", "skeldarChatSettingsButton", self.scale,
                           "Настройки")
        settings.clicked.connect(lambda *_a: self.show_pane("settings"))
        foot.addWidget(settings)
        lv.addLayout(foot)
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
                             ("friends", self._build_friends), ("people", self._build_people),
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
        lay.setContentsMargins(px(6), 0, 0, 0)
        lay.setSpacing(px(4))
        head = w.QHBoxLayout()
        self.chat_back = _button("", "tool", "arrow-left", "skeldarChatBack", self.scale, "К списку")
        self.chat_back.clicked.connect(lambda *_a: self.back())
        head.addWidget(self.chat_back)
        texts = w.QVBoxLayout()
        texts.setSpacing(0)
        self.chat_title = _label("", None, "skeldarChatTitleText")
        self.chat_title.setStyleSheet("font-weight: bold; color: {0};".format(
            hubstyle.TOKENS["text"]))
        self.chat_sub = _label("", "subtitle", "skeldarChatSub")
        texts.addWidget(self.chat_title)
        texts.addWidget(self.chat_sub)
        head.addLayout(texts, 1)
        self.members_button = _button("", "tool", "users", "skeldarChatMembers", self.scale,
                                      "Участники")
        self.members_button.clicked.connect(lambda *_a: self.show_pane("members"))
        head.addWidget(self.members_button)
        lay.addLayout(head)

        self.feed = feed_class()(self)
        self.feed_area = self._scroll(self.feed, "skeldarChatFeedArea")
        self.feed_area.verticalScrollBar().valueChanged.connect(self._scrolled)
        self.feed_area.verticalScrollBar().rangeChanged.connect(self._range_changed)
        lay.addWidget(self.feed_area, 1)
        self.down = _button("", "primary", "arrow-down", "skeldarChatDown", self.scale,
                            "К новым сообщениям")
        self.down.setParent(self.feed_area)
        self.down.clicked.connect(lambda *_a: self.to_bottom())
        self.down.hide()

        self.bar = w.QWidget()
        self.bar.setObjectName("skeldarChatBar")
        bar = w.QHBoxLayout(self.bar)
        bar.setContentsMargins(px(6), 0, 0, 0)
        self.bar_text = _label("", "note", "skeldarChatBarText")
        bar.addWidget(self.bar_text, 1)
        cancel = _button("", "tool", "x", "skeldarChatBarCancel", self.scale, "Отменить (Esc)")
        cancel.clicked.connect(lambda *_a: self.cancel_bar())
        bar.addWidget(cancel)
        self.bar.hide()
        lay.addWidget(self.bar)

        row = w.QHBoxLayout()
        self.composer = composer_class()(self)
        self.composer.textChanged.connect(self._typed)
        row.addWidget(self.composer, 1)
        self.send_button = _button("", "primary", "send", "skeldarChatSend", self.scale,
                                   "Отправить (Enter)")
        self.send_button.clicked.connect(lambda *_a: self.send_now())
        row.addWidget(self.send_button, 0, Qt.AlignBottom)
        lay.addLayout(row)
        self.line = _label("", "status", "skeldarChatLine", wrap=True)
        self.line.hide()
        lay.addWidget(self.line)
        return page

    def _build_friends(self):
        q = _q()
        w = q.QtWidgets
        page, lay = self._pane_box("Друзья", "skeldarChatFriends")
        add = w.QHBoxLayout()
        self.friend_field = w.QLineEdit()
        self.friend_field.setObjectName("skeldarChatFriendNick")
        self.friend_field.setPlaceholderText("@ник друга")
        self.friend_field.returnPressed.connect(self.request_friend)
        add.addWidget(self.friend_field, 1)
        go = _button("Добавить", "primary", "plus", "skeldarChatFriendAdd", self.scale)
        go.clicked.connect(lambda *_a: self.request_friend())
        add.addWidget(go)
        lay.addLayout(add)
        self.friends_line = _label("", "status", "skeldarChatFriendsLine", wrap=True)
        lay.addWidget(self.friends_line)
        self.friends_body = w.QWidget()
        self.friends_body.setObjectName("skeldarChatFriendsBody")
        self.friends_rows = w.QVBoxLayout(self.friends_body)
        self.friends_rows.setContentsMargins(0, 0, 0, 0)
        self.friends_rows.setSpacing(self.px(3))
        lay.addWidget(self._scroll(self.friends_body, "skeldarChatFriendsArea"), 1)
        return page

    def _build_people(self):
        q = _q()
        w = q.QtWidgets
        page, lay = self._pane_box("Все пользователи", "skeldarChatPeople")
        self.people_field = w.QLineEdit()
        self.people_field.setObjectName("skeldarChatPeopleSearch")
        self.people_field.setPlaceholderText("Имя или @ник")
        self.people_field.textChanged.connect(lambda *_a: self._fill_people())
        lay.addWidget(self.people_field)
        self.people_count = _label("", "label", "skeldarChatPeopleCount")
        lay.addWidget(self.people_count)
        self.people_line = _label("", "status", "skeldarChatPeopleLine", wrap=True)
        lay.addWidget(self.people_line)
        self.people_body = w.QWidget()
        self.people_body.setObjectName("skeldarChatPeopleBody")
        self.people_rows = w.QVBoxLayout(self.people_body)
        self.people_rows.setContentsMargins(0, 0, 0, 0)
        self.people_rows.setSpacing(self.px(3))
        lay.addWidget(self._scroll(self.people_body, "skeldarChatPeopleArea"), 1)
        return page

    def _build_new(self):
        q = _q()
        w = q.QtWidgets
        page, lay = self._pane_box("Новый чат", "skeldarChatNewPane")
        lay.addWidget(_label("Личный чат: нажмите на друга. Группа: отметьте друзей и назовите её.",
                             "note", wrap=True))
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
        self.sound_box = w.QCheckBox("Звук")
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
    def _heard(self, kind, data):
        if self.root is None or not hubqt._valid(self.root):
            return
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
        self.me_label.setText(look.display_name(me))
        incoming = len(st.friends.get("incoming", []))
        self.friends_button.setText(look.count_text(incoming) if incoming else "")
        now = time.monotonic()
        rows = []
        for c in look.ordered(self.chats()):
            if not look.matches(c, self.query, me["id"]):
                continue
            last = c.get("last") or {}
            rows.append({"id": c["id"], "chat": c, "title": look.chat_title(c, me["id"]),
                         "preview": look.preview(c, me["id"], st.typing, now),
                         "time": look.clock(last.get("at"), _now_ms()) if last else "",
                         "unread": int(c.get("unread") or 0),
                         "user": look.other(c, me["id"]) or {"id": c["id"], "name": c.get("name")},
                         "typing": bool(look.typers(st.typing, c["id"], me["id"], now))})
        self.list.selected = self.chat
        self.list.set_rows(rows)
        if self.chat is not None and self.chat not in st.chats:
            self.chat = None
        self._layout_columns()
        self._refresh_chat()
        if self.pane == "friends":
            self._fill_friends()
        elif self.pane == "people":
            self._fill_people()
        elif self.pane == "new":
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
        else:
            self.left.setVisible(True)
            self.right.setVisible(True)
            self.split.setVisible(True)
        self.chat_back.setVisible(narrow)

    def _refresh_chat(self):
        st = self.session.state
        c = st.chats.get(self.chat) if self.chat else None
        if c is None:
            return
        me_id = self.me_id()
        self.chat_title.setText(look.chat_title(c, me_id))
        self.chat_sub.setText(look.presence(c, me_id, st.online, st.typing, time.monotonic(),
                                            _now_ms()))
        self.members_button.setVisible(c.get("kind") == "group")
        messages = st.messages.get(self.chat, [])
        users = dict((m["id"], m) for m in c.get("members", []))

        def user_of(uid):
            return users.get(uid, {"id": uid, "nick": uid})

        items = look.feed(messages, st.pending.get(self.chat, []), me_id, c, st.reads, _now_ms())
        ctx = {"chat": c, "messages": messages, "user_of": user_of,
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
        if pane == "people":
            self.read_people()
        self.refresh()

    def read_people(self):
        """Asks the server for everybody again (the pane is opened, a friend press answered)."""
        fn = getattr(self.session, "read_people", None)
        if fn is not None:
            self._call(fn, self.people_line)

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
        if self.editing:
            self.bar_text.setText("Изменение сообщения")
        elif self.reply_to:
            m = look.find(self.session.state.messages.get(self.chat, []), self.reply_to) or {}
            c = self.session.state.chats.get(self.chat) or {}
            who = next((u for u in c.get("members", []) if u.get("id") == m.get("from_id")),
                       {"nick": "?"})
            self.bar_text.setText("Ответ " + look.display_name(who) + ": "
                                  + " ".join(str(m.get("text") or "").split())[:60])
        self.bar.setVisible(bool(self.editing or self.reply_to))

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
        for label, fn in rows:
            act = menu.addAction(label)
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
        rows.append(("Ответить", lambda: self.start_reply(m)))
        rows.append(("Скопировать", lambda: self.copy_text(m.get("text") or "")))
        if item.mine:
            rows.append(("Изменить", lambda: self.start_edit(m)))
            rows.append(("Удалить", lambda: self.delete_message(m)))
        return rows

    def copy_text(self, text):
        q = _q()
        q.QtWidgets.QApplication.clipboard().setText(text)

    def delete_message(self, message):
        try:
            self.session.delete(self.chat, message["id"])
        except Exception as exc:                             # noqa: BLE001
            self.say(getattr(exc, "text", str(exc)))

    def _typed(self):
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
        return "Пока нет чатов. Добавьте друга 👤"

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

    # ---------------------------------------------------------- friends, groups, settings
    def _call(self, fn, line):
        try:
            result = fn()
        except Exception as exc:                             # noqa: BLE001
            self.say(getattr(exc, "text", str(exc)), line)
            return None
        self.say("", line)
        return result

    def _after_people(self):
        for name in ("_read_friends", "_refresh_chats") + (("read_people",)
                                                            if self.pane == "people" else ()):
            fn = getattr(self.session, name, None)
            if fn is not None:
                try:
                    fn()
                except Exception:                            # noqa: BLE001
                    pass
        self.refresh()

    def request_friend(self, nick=None, line=None):
        typed = nick is None
        nick = (self.friend_field.text() if typed else nick).strip().lstrip("@").lower()
        line = line or self.friends_line
        if not nick:
            return
        if self._call(lambda: self.session.api.request(nick), line) is not None:
            if typed:
                self.friend_field.clear()
            self.say("Запрос отправлен @" + nick, line)
            self._after_people()

    def _pane_line(self):
        return self.people_line if self.pane == "people" else self.friends_line

    def answer(self, verb, user_id):
        if self._call(lambda: self.session.api.answer(verb, user_id), self._pane_line()) is not None:
            self._after_people()

    def unfriend(self, user_id):
        if self._call(lambda: self.session.api.unfriend(user_id), self.friends_line) is not None:
            self._after_people()

    def write_to(self, user_id):
        chat_id = self._call(lambda: self.session.open_dm(user_id), self._pane_line())
        if chat_id:
            self.open_chat(chat_id)

    def make_group(self):
        name = self.group_name.text().strip()
        if not name:
            self.say("Назовите группу", self.new_line)
            return
        if not self.picked:
            self.say("Отметьте хотя бы одного друга", self.new_line)
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
        online = self.session.state.online.get(user.get("id"), {}).get("online", user.get("online"))
        dot = "● " if online else "○ "
        name = _label(dot + look.display_name(user) + "  @" + str(user.get("nick") or ""), None)
        name.setStyleSheet("color: {0};".format(hubstyle.TOKENS["text" if online else "text2"]))
        lay.addWidget(name, 1)
        for text, role, fn in buttons:
            b = _button(text, role, None, None, self.scale)
            b.clicked.connect(lambda *_a, f=fn: f())
            lay.addWidget(b)
        return row

    def _fill_friends(self):
        self._clear(self.friends_rows)
        fr = self.session.state.friends
        for title, users, buttons in (
                ("Входящие запросы", fr.get("incoming", []),
                 lambda u: [("Принять", "primary", lambda: self.answer("accept", u["id"])),
                            ("Отклонить", None, lambda: self.answer("decline", u["id"]))]),
                ("Отправленные", fr.get("outgoing", []),
                 lambda u: [("Отменить", None, lambda: self.answer("cancel", u["id"]))]),
                ("Друзья", fr.get("friends", []),
                 lambda u: [("Написать", "primary", lambda: self.write_to(u["id"])),
                            ("Удалить", "danger", lambda: self.unfriend(u["id"]))])):
            if not users:
                continue
            self.friends_rows.addWidget(_label(title, "heading"))
            for u in users:
                self.friends_rows.addWidget(self._person_row(u, buttons(u)))
        if not any(fr.get(k) for k in ("incoming", "outgoing", "friends")):
            self.friends_rows.addWidget(_label("Пока никого. Добавьте друга по его нику.", "note"))
        self.friends_rows.addStretch(1)

    def _people_buttons(self, u):
        line = self.people_line
        rel = u.get("relation")
        if rel == "friend":
            return [("Написать", "primary", lambda: self.write_to(u["id"]))]
        if rel == "incoming":
            return [("Принять", "primary", lambda: self.answer("accept", u["id"]))]
        if rel == "outgoing":
            return [("Отменить запрос", None, lambda: self.answer("cancel", u["id"]))]
        return [("В друзья", None, lambda: self.request_friend(u.get("nick"), line))]

    def _fill_people(self):
        st = self.session.state
        self._clear(self.people_rows)
        rows = look.people_rows(getattr(st, "people", []), st.friends, st.online,
                                self.people_field.text())
        self.people_count.setText(look.people_count(rows) if rows else "")
        for u in rows:
            row = self._person_row(u, self._people_buttons(u))
            if not u["online"]:
                row.setToolTip(look.last_seen(u.get("last_seen"), _now_ms()))
            self.people_rows.addWidget(row)
        if not rows:
            text = ("Никого не нашли" if self.people_field.text().strip()
                    else "Пока здесь никого, кроме вас")
            self.people_rows.addWidget(_label(text, "note"))
        self.people_rows.addStretch(1)

    def _fill_new(self):
        q = _q()
        self._clear(self.new_rows)
        friends = self.session.state.friends.get("friends", [])
        if not friends:
            self.new_rows.addWidget(_label("Сначала добавьте друзей 👤", "note"))
        for u in friends:
            row = q.QtWidgets.QWidget()
            lay = q.QtWidgets.QHBoxLayout(row)
            lay.setContentsMargins(0, 0, 0, 0)
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
            more = [u for u in self.session.state.friends.get("friends", []) if u["id"] not in ids]
            if more:
                self.members_rows.addWidget(_label("Добавить друга", "heading"))
            for u in more:
                self.members_rows.addWidget(self._person_row(
                    u, [("Добавить", "primary", lambda uid=u["id"]: self.add_member(uid))]))
        self.members_rows.addStretch(1)

    def _fill_settings(self):
        me = self.session.state.me or {}
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


def _screens():
    try:
        import maya_hubpop
        return maya_hubpop.screens()
    except Exception:                                        # noqa: BLE001
        return [(0, 0, 1920, 1080)]


def _on(screen, point):
    return screen[0] <= point[0] < screen[0] + screen[2] and \
        screen[1] <= point[1] < screen[1] + screen[3]


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
