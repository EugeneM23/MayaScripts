"""A person's card over the chat window, and our picture viewer (2026-10-22).

The animator: «давай добавим возможность нажать на аватар пользователя и у нас откроется окошко с
увеличенной аватаркой и списком всех файлов. Мы должны иметь возможность сортировать по типам
файлов, позы анимации сцены». And for pictures: «У меня картинки по умолчанию открываются в пейнте.
А можно что бы в каком-то просмотрщике?» - so a picture opens in a viewer of ours.

- `Profile` covers the chat window (a dimmed backdrop, a card in the middle): the avatar large, the
  name, @nick, presence, Написать; kind tabs with counts (`look.PROFILE_KINDS`), a search, and the
  person's files (`GET /v1/users/<id>/files`, read on a thread): a row its preview, name and line.
  A click picks, a double click goes to its message, the right button its verbs, a drag takes it
  out (the feed's own drag: a card onto a character / the library, a file into Stash / Shared / a
  viewport). Esc, ✕ or a click on the backdrop closes it.
- `Viewer` is a frameless window of ours: the picture fitted, the wheel zooms about the mouse, a
  drag pans, a double click fits again, Esc closes.

Spec: docs/superpowers/specs/2026-10-22-chat-profile-design.md
"""
import os
import traceback

from . import look

_CLASSES = {}
ROW_H = 58            # logical px, a file row
THUMB = 46            # its preview
CARD_W = 560          # the card's width at most
AVATAR = 92


def _w():
    from . import window
    return window


def _q():
    return _w()._q()


# ---------------------------------------------------------------------- the files list

def list_class():
    if "list" not in _CLASSES:
        q = _q()
        QtCore, QtGui, QtWidgets = q.QtCore, q.QtGui, q.QtWidgets
        W = _w()

        class FileList(QtWidgets.QWidget):

            def __init__(self, card, parent=None):
                super(FileList, self).__init__(parent)
                self.card = card
                self.rows = []
                self.selected = None
                self.hovered = None
                self._press = None
                self._dragging = False
                self.setMouseTracking(True)
                self.setObjectName("skeldarChatProfileFiles")

            def px(self, n):
                return W.hubstyle.px(n, self.card.win.scale)

            def set_rows(self, rows):
                self.rows = list(rows)
                self.setMinimumHeight(max(1, self.px(ROW_H) * len(self.rows)))
                self.update()

            def index_at(self, y):
                i = int(y // max(1, self.px(ROW_H)))
                return i if 0 <= i < len(self.rows) else -1

            def entry_at(self, pos):
                i = self.index_at(pos.y())
                return self.rows[i] if i >= 0 else None

            # ---------------------------------------------------------- input
            def mousePressEvent(self, event):              # noqa: N802
                pos = event.position() if hasattr(event, "position") else QtCore.QPointF(event.pos())
                gp = event.globalPosition().toPoint() if hasattr(event, "globalPosition") \
                    else event.globalPos()
                if self._dragging:
                    self._end(gp, cancel=event.button() != QtCore.Qt.LeftButton)
                    return
                e = self.entry_at(pos)
                if e is None:
                    return
                self.selected = e.get("msg")
                self.update()
                if event.button() == QtCore.Qt.RightButton:
                    self.card.menu(e, gp)
                    return
                if event.button() == QtCore.Qt.LeftButton:
                    self._press = (QtCore.QPointF(pos), e)

            def mouseDoubleClickEvent(self, event):        # noqa: N802
                pos = event.position() if hasattr(event, "position") else QtCore.QPointF(event.pos())
                e = self.entry_at(pos)
                if e is not None and event.button() == QtCore.Qt.LeftButton:
                    self._press = None
                    self.card.open_entry(e)

            def mouseMoveEvent(self, event):               # noqa: N802
                pos = event.position() if hasattr(event, "position") else QtCore.QPointF(event.pos())
                gp = event.globalPosition().toPoint() if hasattr(event, "globalPosition") \
                    else event.globalPos()
                if self._dragging:
                    self.card.win.drag_move(gp)
                    return
                if self._press is not None and event.buttons() & QtCore.Qt.LeftButton:
                    start, e = self._press
                    if (pos - start).manhattanLength() >= QtWidgets.QApplication.startDragDistance():
                        self._press = None
                        if self.card.win.start_drag(self.card.item_of(e), gp):
                            self._dragging = True
                            self.grabMouse()
                        return
                e = self.entry_at(pos)
                hovered = e.get("msg") if e else None
                if hovered != self.hovered:
                    self.hovered = hovered
                    self.update()

            def mouseReleaseEvent(self, event):            # noqa: N802
                gp = event.globalPosition().toPoint() if hasattr(event, "globalPosition") \
                    else event.globalPos()
                self._press = None
                if self._dragging:
                    self._end(gp, cancel=event.button() != QtCore.Qt.LeftButton)

            def _end(self, gp, cancel):
                self._dragging = False
                try:
                    self.releaseMouse()
                except Exception:                            # noqa: BLE001
                    pass
                self.card.win.drag_end(gp, cancel)

            def leaveEvent(self, event):                   # noqa: N802
                self.hovered = None
                self.update()
                super(FileList, self).leaveEvent(event)

            # ---------------------------------------------------------- paint
            def paintEvent(self, event):                   # noqa: N802
                p = QtGui.QPainter(self)
                try:
                    self._paint(p)
                except Exception:                            # noqa: BLE001
                    traceback.print_exc()
                finally:
                    p.end()

            def _paint(self, p):
                px = self.px
                p.setRenderHint(QtGui.QPainter.Antialiasing)
                p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
                w = self.width()
                now = W._now_ms()
                cache = self.card.thumbs()
                for i, e in enumerate(self.rows):
                    top = i * px(ROW_H)
                    f = e.get("file") or {}
                    rect = QtCore.QRectF(px(2), top + px(2), w - px(4), px(ROW_H) - px(4))
                    if e.get("msg") == self.selected:
                        p.setPen(QtGui.QPen(W._colour("accent", 0.9), max(1.0, self.card.win.scale)))
                        p.setBrush(W._colour("card_active"))
                        p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), px(6), px(6))
                    elif e.get("msg") == self.hovered:
                        p.setPen(QtCore.Qt.NoPen)
                        p.setBrush(W._colour("hover"))
                        p.drawRoundedRect(rect, px(6), px(6))
                    tile = QtCore.QRectF(rect.left() + px(6), rect.top() + (rect.height() - px(THUMB)) / 2.0,
                                         px(THUMB), px(THUMB))
                    clip = QtGui.QPainterPath()
                    clip.addRoundedRect(tile, px(5), px(5))
                    image = cache.image(f) if cache is not None else None
                    if image is not None:
                        from . import thumbs
                        source = QtCore.QRectF(0, 0, image.width(), image.height())
                        sheet = thumbs.sheet_of(f)
                        if sheet is not None:
                            side = image.width() / float(sheet["columns"])
                            cx, cy, cw, ch = thumbs.cell_rect(sheet["cells"] // 2, sheet["columns"], side)
                            source = QtCore.QRectF(cx, cy, cw, ch)
                        # cropped square by its centre
                        k = min(source.width(), source.height())
                        source = QtCore.QRectF(source.center().x() - k / 2.0, source.center().y() - k / 2.0,
                                               k, k)
                        p.save()
                        p.setClipPath(clip)
                        p.drawImage(tile, image, source)
                        p.restore()
                    else:
                        p.setPen(QtCore.Qt.NoPen)
                        p.setBrush(W._colour("accent_tint"))
                        p.drawPath(clip)
                        p.setFont(W._font(self.font(), px(9), True))
                        p.setPen(W._colour("accent_text"))
                        p.drawText(tile, QtCore.Qt.AlignCenter, look.file_tag(f))
                    left = tile.right() + px(10)
                    width = rect.right() - px(8) - left
                    p.setFont(W._font(self.font(), px(11), True))
                    fm = QtGui.QFontMetrics(p.font())
                    p.setPen(W._colour("faint" if f.get("expired") else "text"))
                    p.drawText(QtCore.QPointF(left, rect.top() + px(8) + fm.ascent()),
                               fm.elidedText(f.get("name") or "", QtCore.Qt.ElideMiddle, int(width)))
                    p.setFont(W._font(self.font(), px(9.5)))
                    fm2 = QtGui.QFontMetrics(p.font())
                    p.setPen(W._colour("muted"))
                    p.drawText(QtCore.QPointF(left, rect.bottom() - px(8) - fm2.descent()),
                               fm2.elidedText(look.profile_line(e, now_ms=now), QtCore.Qt.ElideRight,
                                              int(width)))

        _CLASSES["list"] = FileList
    return _CLASSES["list"]


# ---------------------------------------------------------------------- the card

class Profile(object):
    """A person's card over `win.root`."""

    def __init__(self, win, user):
        self.win = win
        self.user = dict(user or {})
        self.entries = []
        self.kind = "all"
        self.state = "loading"         # loading / ready / failed
        self.error = ""
        self._build()
        self.load()

    # ------------------------------------------------------------------ build
    def px(self, n):
        return self.win.px(n)

    def thumbs(self):
        try:
            from . import thumbs
            return thumbs.cache(self.win.session)
        except Exception:                                    # noqa: BLE001
            return None

    def _build(self):
        q = _q()
        QtCore, QtGui, QtWidgets = q.QtCore, q.QtGui, q.QtWidgets
        W = _w()
        card = self

        class Backdrop(QtWidgets.QWidget):
            def paintEvent(self, event):                   # noqa: N802
                p = QtGui.QPainter(self)
                p.fillRect(self.rect(), QtGui.QColor(0, 0, 0, 140))
                p.end()

            def mousePressEvent(self, event):              # noqa: N802
                if not card.box.geometry().contains(event.position().toPoint()
                                                    if hasattr(event, "position") else event.pos()):
                    card.close()

            def keyPressEvent(self, event):                # noqa: N802
                if event.key() == QtCore.Qt.Key_Escape:
                    card.close()
                    return
                super(Backdrop, self).keyPressEvent(event)

            def resizeEvent(self, event):                  # noqa: N802
                card.place()

        root = self.win.root
        self.cover = Backdrop(root)
        self.cover.setObjectName("skeldarChatProfile")
        self.cover.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.box = QtWidgets.QFrame(self.cover)
        self.box.setObjectName("skeldarChatProfileCard")
        self.box.setStyleSheet("#skeldarChatProfileCard {{ background: {0}; border: 1px solid {1};"
                               " border-radius: {2}px; }}".format(W.hubstyle.TOKENS["panel"],
                                                                  W.hubstyle.TOKENS["line"], self.px(10)))
        lay = QtWidgets.QVBoxLayout(self.box)
        lay.setContentsMargins(self.px(16), self.px(14), self.px(16), self.px(14))
        lay.setSpacing(self.px(8))

        head = QtWidgets.QHBoxLayout()
        head.setSpacing(self.px(14))
        self.avatar = W.avatar_widget_class()(self.win, self.user, self.px(AVATAR))
        self.avatar.clickable = False
        head.addWidget(self.avatar, 0, QtCore.Qt.AlignTop)
        names = QtWidgets.QVBoxLayout()
        names.setSpacing(self.px(2))
        self.name = W._label(look.display_name(self.user), None, "skeldarChatProfileName")
        font = QtGui.QFont(self.name.font())
        font.setPixelSize(self.px(17))
        font.setBold(True)
        self.name.setFont(font)
        self.name.setStyleSheet("color: %s;" % W.hubstyle.TOKENS["text"])
        names.addWidget(self.name)
        self.nick = W._label("@" + str(self.user.get("nick") or ""), "note", "skeldarChatProfileNick")
        names.addWidget(self.nick)
        self.seen = W._label("", "note", "skeldarChatProfileSeen")
        names.addWidget(self.seen)
        buttons = QtWidgets.QHBoxLayout()
        self.write = W._button(u"Написать", "primary", "message-circle", "skeldarChatProfileWrite",
                               self.win.scale)
        self.write.clicked.connect(self.write_to)
        buttons.addWidget(self.write)
        buttons.addStretch(1)
        names.addSpacing(self.px(4))
        names.addLayout(buttons)
        names.addStretch(1)
        head.addLayout(names, 1)
        close = W._button("", "tool", "x", "skeldarChatProfileClose", self.win.scale, u"Закрыть (Esc)")
        close.clicked.connect(self.close)
        head.addWidget(close, 0, QtCore.Qt.AlignTop)
        lay.addLayout(head)

        self.tabs = {}
        tabs = QtWidgets.QHBoxLayout()
        tabs.setSpacing(self.px(4))
        for kind, label in look.PROFILE_KINDS:
            b = W._button(label, None, None, "skeldarChatProfileTab_" + kind, self.win.scale)
            b.setCheckable(True)
            b.clicked.connect(lambda *_a, k=kind: self.show_kind(k))
            tabs.addWidget(b)
            self.tabs[kind] = (b, label)
        tabs.addStretch(1)
        lay.addLayout(tabs)
        self.search = QtWidgets.QLineEdit()
        self.search.setObjectName("skeldarChatProfileSearch")
        self.search.setPlaceholderText(u"Поиск по файлам…")
        self.search.textChanged.connect(lambda *_a: self.fill())
        lay.addWidget(self.search)
        self.list = list_class()(self)
        self.area = self.win._scroll(self.list, "skeldarChatProfileArea")
        lay.addWidget(self.area, 1)
        self.line = W._label("", "note", "skeldarChatProfileLine")
        lay.addWidget(self.line)
        self.place()
        self.cover.show()
        self.cover.raise_()
        self.cover.setFocus()
        self.paint_head()
        self.fill()

    def place(self):
        root = self.win.root
        if root is None:
            return
        self.cover.setGeometry(0, 0, root.width(), root.height())
        w = min(self.px(CARD_W), root.width() - self.px(24))
        h = max(self.px(260), root.height() - self.px(48))
        self.box.setGeometry(int((root.width() - w) / 2), int((root.height() - h) / 2), int(w), int(h))

    # ------------------------------------------------------------------ data
    def load(self):
        """The person's files, read on a thread; the card fills when they come."""
        from . import files
        api = self.win.session.api
        uid = self.user.get("id")
        self.state, self.error = "loading", ""
        box = {}

        def work():
            try:
                box["answer"] = api.person_files(uid)
            except Exception as exc:                         # noqa: BLE001
                box["error"] = getattr(exc, "text", None) or str(exc)
            files.defer(lambda: self._loaded(box))

        files.spawn(work)

    def _loaded(self, box):
        if self.cover is None:
            return
        if "error" in box:
            self.state, self.error = "failed", box["error"]
        else:
            answer = box.get("answer") or {}
            self.entries = list(answer.get("files") or [])
            if (answer.get("user") or {}).get("id") == self.user.get("id"):
                self.user.update(answer["user"])
                self.avatar.set_user(self.user)
            self.state = "ready"
        self.paint_head()
        self.fill()

    def paint_head(self):
        W = _w()
        online = W.is_online(self.user, self.win.session.state.online)
        self.seen.setText(u"в сети" if online else look.last_seen(self.user.get("last_seen"),
                                                                    W._now_ms()))
        mine = self.user.get("id") == self.win.me_id()
        self.write.setVisible(not mine)
        counts = look.profile_counts(self.entries)
        for kind, (b, label) in self.tabs.items():
            n = counts.get(kind, 0)
            b.setText(u"%s %d" % (label, n) if self.state == "ready" else label)
            b.setChecked(kind == self.kind)
            b.setProperty("skRole", "primary" if kind == self.kind else None)
            b.style().unpolish(b)
            b.style().polish(b)

    def rows(self):
        return look.profile_rows(self.entries, self.kind, self.search.text())

    def fill(self):
        rows = self.rows()
        self.list.set_rows(rows)
        if self.state == "loading":
            text = u"Загружаю файлы…"
        elif self.state == "failed":
            text = u"Не удалось загрузить файлы: %s" % self.error
        elif not self.entries:
            text = u"%s пока ничего не присылал(а)" % look.display_name(self.user)
        elif not rows:
            text = u"Ничего не нашли"
        else:
            text = u"Двойной клик - к сообщению, правая кнопка - действия, перетащите, чтобы применить"
        self.line.setText(text)

    def show_kind(self, kind):
        self.kind = kind
        self.paint_head()
        self.fill()

    # ------------------------------------------------------------------ presses
    def item_of(self, e):
        """The feed's Item of a file row: what the window's file verbs and its drag take."""
        m = {"id": e.get("msg"), "chat": e.get("chat"), "from_id": self.user.get("id"),
             "cid": e.get("msg"), "text": e.get("text") or "", "file": e.get("file"),
             "at": e.get("at"), "seq": e.get("seq")}
        return look.Item("msg", e.get("text") or "", m, mine=self.user.get("id") == self.win.me_id())

    def verbs(self, e):
        from . import files
        f = e.get("file") or {}
        rows = [(u"Показать в чате", lambda: self.open_entry(e))]
        if f.get("expired"):
            return rows
        if files.is_image(f):
            rows += [(u"Открыть", lambda: self.act(e, "view")), (u"Сохранить как…", lambda: self.act(e, "save"))]
        elif files.is_card(f):
            rows += [(u"В библиотеку поз", lambda: self.act(e, "library", {"kind": "library", "folder": None}))]
        else:
            rows += [("Open", lambda: self.act(e, "open")), ("Import", lambda: self.act(e, "import")),
                     (u"Сохранить как…", lambda: self.act(e, "save")),
                     (u"В Stash", lambda: self.act(e, "stash"))]
        return rows

    def menu(self, e, gp):
        q = _q()
        menu = q.QtWidgets.QMenu(self.cover)
        menu.setObjectName("skeldarChatProfileMenu")
        for label, fn in self.verbs(e):
            act = menu.addAction(label)
            act.triggered.connect(lambda *_a, f=fn: f())
        menu.popup(gp)
        self._menu = menu

    def act(self, e, action, target=None):
        self.win.file_action(self.item_of(e), action, target=target)
        self.line.setText(self.win.line.text() or self.line.text())

    def open_entry(self, e):
        """To the file's message in its chat (older history loaded until it is there)."""
        chat, mid = e.get("chat"), e.get("msg")
        self.close()
        self.win.open_chat(chat)
        ses = self.win.session
        for _page in range(30):
            if any(m.get("id") == mid for m in ses.state.messages.get(chat, [])):
                break
            try:
                if not ses.load_history(chat):
                    break
            except Exception:                                # noqa: BLE001
                break
        self.win.refresh()
        self.win.scroll_to_message(mid)

    def write_to(self):
        uid = self.user.get("id")
        self.close()
        self.win.write_to(uid)

    def close(self):
        cover, self.cover = self.cover, None
        if cover is not None:
            cover.hide()
            cover.deleteLater()
        if getattr(self.win, "profile", None) is self:
            self.win.profile = None

    def is_open(self):
        return self.cover is not None


# ---------------------------------------------------------------------- the picture viewer

def viewer_class():
    if "viewer" not in _CLASSES:
        q = _q()
        QtCore, QtGui, QtWidgets = q.QtCore, q.QtGui, q.QtWidgets
        W = _w()

        class Viewer(QtWidgets.QWidget):
            """A picture from the chat: fitted, the wheel zooms about the mouse, a drag pans,
            a double click fits it again, Esc or ✕ closes it."""

            def __init__(self, path, scale=1.0, parent=None):
                flags = QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint
                super(Viewer, self).__init__(parent, flags)
                self.setObjectName("skeldarChatViewer")
                self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
                self.path = path
                self.scale = scale
                self.image = QtGui.QImage(path)
                self.zoom = None            # None: fitted
                self.offset = QtCore.QPointF(0, 0)
                self._drag = None
                self._move = None
                self.setMouseTracking(True)
                self.setWindowTitle(os.path.basename(path))
                screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
                w = min(int(screen.width() * 0.8), max(480, self.image.width() + 40))
                h = min(int(screen.height() * 0.8), max(360, self.image.height() + 80))
                self.resize(w, h)
                self.move(screen.center().x() - w // 2, screen.center().y() - h // 2)

            def px(self, n):
                return W.hubstyle.px(n, self.scale)

            def title_h(self):
                return self.px(34)

            def fit_k(self):
                if self.image.isNull():
                    return 1.0
                area_w, area_h = self.width() - self.px(24), self.height() - self.title_h() - self.px(12)
                return min(1.0, area_w / float(self.image.width()), area_h / float(self.image.height()))

            def k(self):
                return self.zoom if self.zoom is not None else self.fit_k()

            def placed(self):
                k = self.k()
                w, h = self.image.width() * k, self.image.height() * k
                cx = self.width() / 2.0 + self.offset.x()
                cy = self.title_h() + (self.height() - self.title_h()) / 2.0 + self.offset.y()
                return QtCore.QRectF(cx - w / 2.0, cy - h / 2.0, w, h)

            def close_rect(self):
                s = self.px(26)
                return QtCore.QRectF(self.width() - s - self.px(6), (self.title_h() - s) / 2.0, s, s)

            def paintEvent(self, event):                   # noqa: N802
                p = QtGui.QPainter(self)
                try:
                    p.setRenderHint(QtGui.QPainter.Antialiasing)
                    p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
                    p.fillRect(self.rect(), W._colour("panel"))
                    p.setPen(QtGui.QPen(W._colour("line"), 1))
                    p.drawRect(QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5))
                    p.setFont(W._font(self.font(), self.px(11), True))
                    p.setPen(W._colour("text2"))
                    label = u"%s  ·  %d × %d  ·  %d%%" % (os.path.basename(self.path), self.image.width(),
                                                          self.image.height(), int(round(self.k() * 100)))
                    p.drawText(QtCore.QRectF(self.px(12), 0, self.width() - self.px(60), self.title_h()),
                               QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, label)
                    r = self.close_rect()
                    p.setPen(QtGui.QPen(W._colour("text2"), max(1.0, self.scale * 1.4)))
                    m = r.width() * 0.32
                    p.drawLine(QtCore.QPointF(r.left() + m, r.top() + m), QtCore.QPointF(r.right() - m, r.bottom() - m))
                    p.drawLine(QtCore.QPointF(r.right() - m, r.top() + m), QtCore.QPointF(r.left() + m, r.bottom() - m))
                    p.setClipRect(QtCore.QRectF(0, self.title_h(), self.width(), self.height() - self.title_h()))
                    if self.image.isNull():
                        p.setPen(W._colour("muted"))
                        p.drawText(self.rect(), QtCore.Qt.AlignCenter, u"Не удалось прочитать картинку")
                    else:
                        p.drawImage(self.placed(), self.image)
                finally:
                    p.end()

            def wheelEvent(self, event):                   # noqa: N802
                pos = event.position() if hasattr(event, "position") else QtCore.QPointF(event.pos())
                before = self.k()
                step = 1.2 if event.angleDelta().y() > 0 else 1 / 1.2
                after = max(0.05, min(16.0, before * step))
                rect = self.placed()
                # keep the point under the mouse where it is
                u = (pos.x() - rect.left()) / max(1e-6, rect.width())
                v = (pos.y() - rect.top()) / max(1e-6, rect.height())
                self.zoom = after
                new = self.placed()
                self.offset += QtCore.QPointF(pos.x() - (new.left() + u * new.width()),
                                              pos.y() - (new.top() + v * new.height()))
                self.update()

            def mousePressEvent(self, event):              # noqa: N802
                pos = event.position() if hasattr(event, "position") else QtCore.QPointF(event.pos())
                if event.button() != QtCore.Qt.LeftButton:
                    return
                if self.close_rect().contains(pos):
                    self.close()
                    return
                gp = event.globalPosition() if hasattr(event, "globalPosition") else QtCore.QPointF(event.globalPos())
                if pos.y() < self.title_h():
                    self._move = gp - QtCore.QPointF(self.pos())
                else:
                    self._drag = (pos, QtCore.QPointF(self.offset))

            def mouseMoveEvent(self, event):               # noqa: N802
                pos = event.position() if hasattr(event, "position") else QtCore.QPointF(event.pos())
                if self._move is not None:
                    gp = event.globalPosition() if hasattr(event, "globalPosition") else QtCore.QPointF(event.globalPos())
                    self.move((gp - self._move).toPoint())
                elif self._drag is not None:
                    start, offset = self._drag
                    self.offset = offset + (pos - start)
                    self.update()

            def mouseReleaseEvent(self, event):            # noqa: N802
                self._drag = self._move = None

            def mouseDoubleClickEvent(self, event):        # noqa: N802
                self.zoom = None
                self.offset = QtCore.QPointF(0, 0)
                self.update()

            def keyPressEvent(self, event):                # noqa: N802
                if event.key() == QtCore.Qt.Key_Escape:
                    self.close()
                    return
                super(Viewer, self).keyPressEvent(event)

        _CLASSES["viewer"] = Viewer
    return _CLASSES["viewer"]


_OPEN = []


def view_picture(path, scale=1.0):
    """A picture opened in our viewer, beside Maya's window (owned by it)."""
    try:
        parent = _w()._main_window()
    except Exception:                                        # noqa: BLE001
        parent = None
    v = viewer_class()(path, scale, parent)
    _OPEN[:] = [x for x in _OPEN if _w().hubqt._valid(x)] + [v]
    v.show()
    v.raise_()
    v.activateWindow()
    return v
