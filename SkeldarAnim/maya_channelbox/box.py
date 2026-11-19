"""Our Channel Box (Qt), variant A "Rows" (2026-10-18): a head (the lead object, +N,
the layer keys go to) over a scrolling canvas of rows - a key cell, the attribute's
name, its value well - painted in the Time Bar's look.

The widget talks to Maya only through a `link` (scene.py in Maya, a fake in the
tests). Nothing moves and nothing glows (2026-11-19, «удаляем все подсветки и
анимации»): a row under the mouse takes the hover face, a selected channel the
accent tint, every change is painted at once.
Spec: docs/superpowers/specs/2026-10-18-channel-box-rows-design.md
"""

import math
import traceback

from . import look

ROOT = "skeldarChannelBox"
HEAD = "skeldarChannelBoxHead"
CANVAS = "skeldarChannelBoxCanvas"
SCROLL = "skeldarChannelBoxScroll"
EDIT = "skeldarChannelBoxEdit"

GLYPHS = {
    "lock": "M4 7V5a4 4 0 0 1 8 0v2h1v8H3V7zm2 0h4V5a2 2 0 0 0-4 0z",
    "link": ("M6.6 8.7l2.1-2.1.9.9-2.1 2.1zM4.1 8.5l1.6-1.6.9.9-1.6 1.6a1.6 1.6 0 0 0 2.3 2.3"
             "l1.6-1.6.9.9-1.6 1.6a2.9 2.9 0 0 1-4.1-4.1zm7.8-1L10.3 9.1l-.9-.9 1.6-1.6a1.6 1.6 0 0 0"
             "-2.3-2.3L7.1 5.9l-.9-.9 1.6-1.6a2.9 2.9 0 0 1 4.1 4.1z"),
    "chev": "M6 3.5l4.5 4.5L6 12.5l-1.1-1.1L8.3 8 4.9 4.6z",
}

SPEEDS = (("Slow", 0.1), ("Medium", 1.0), ("Fast", 10.0))
MENU_SHEET = (
    "QMenu {{ background: {card}; color: {text}; border: 1px solid {line}; padding: {p4}; }}"
    "QMenu::item {{ padding: {p4} {p12}; border-radius: {r4}; }}"
    "QMenu::item:selected {{ background: {hover}; }}"
    "QMenu::item:disabled {{ color: {faint}; }}"
    "QMenu::separator {{ height: 1px; background: {line}; margin: {p4} {p2}; }}")


def _tokens():
    import maya_hubstyle
    return maya_hubstyle.TOKENS


_CLASSES = {}


def classes():
    """(Box,), made on first use - no Qt at import."""
    if _CLASSES:
        return _CLASSES["all"]
    import maya_hubqt
    q = maya_hubqt.qt()
    QtCore, QtGui, QtWidgets = q.QtCore, q.QtGui, q.QtWidgets
    Qt = QtCore.Qt
    QtSvg = getattr(q, "QtSvg", None)
    renderers = {}

    def colour(hex_, alpha=255):
        c = QtGui.QColor(hex_)
        c.setAlpha(int(max(0, min(255, alpha))))
        return c

    def draw_glyph(p, name, rect, hex_):
        path = GLYPHS.get(name)
        key = (name, hex_)
        renderer = renderers.get(key)
        if renderer is None and QtSvg is not None:
            svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><path fill="%s" '
                   'fill-rule="evenodd" d="%s"/></svg>') % (hex_, path)
            renderer = QtSvg.QSvgRenderer(QtCore.QByteArray(svg.encode("utf-8")))
            renderers[key] = renderer
        if renderer is not None:
            renderer.render(p, rect)

    def rectf(r):
        return QtCore.QRectF(r[0], r[1], r[2], r[3])

    def guarded(owner, call):
        try:
            call()
        except Exception:                                    # noqa: BLE001
            if not getattr(owner, "_failed", False):
                print(traceback.format_exc())
            owner._failed = True

    # -- the head ------------------------------------------------------------------

    class Head(QtWidgets.QWidget):
        """The lead object's name, the +N pill, the layer chip (a click: the layers)."""

        def __init__(self, box):
            super(Head, self).__init__(box)
            self.box = box
            self.setObjectName(HEAD)
            self.setMouseTracking(True)
            self.setFixedHeight(int(round(look.HEAD_H * box.ui)))
            self.hover = False              # the mouse over the layer chip

        def chip_rect(self):
            ui = self.box.ui
            text = self.box.layer_text or ""
            if not text:
                return None
            fm = QtGui.QFontMetrics(self._font(11.5))
            w = fm.horizontalAdvance(text + "  ▾") + 18 * ui
            h = 20 * ui
            return QtCore.QRectF(self.width() - 8 * ui - w, (self.height() - h) / 2.0, w, h)

        def _font(self, px, bold=False):
            font = QtGui.QFont(self.font())
            font.setPixelSize(max(8, int(round(px * self.box.ui))))
            font.setBold(bold)
            return font

        def mouseMoveEvent(self, event):
            r = self.chip_rect()
            hover = bool(r is not None and r.contains(event.position()))
            if hover != self.hover:
                self.hover = hover
                self.update()

        def leaveEvent(self, event):
            if self.hover:
                self.hover = False
                self.update()

        def mousePressEvent(self, event):
            r = self.chip_rect()
            if r is not None and r.contains(event.position()) and event.button() == Qt.LeftButton:
                self.box.layer_menu(self.mapToGlobal(r.bottomLeft().toPoint()))

        def paintEvent(self, _event):
            guarded(self, self._paint)

        def _paint(self):
            box, tk, ui = self.box, self.box.tokens, self.box.ui
            p = QtGui.QPainter(self)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            p.fillRect(self.rect(), colour(tk["panel"]))
            p.fillRect(QtCore.QRectF(0, self.height() - 1, self.width(), 1), colour(tk["track_edge"]))
            name, more = look.head_text(box.lead, max(0, len(box.objects) - 1))
            x = 10 * ui
            chip = self.chip_rect()
            right = (chip.left() - 8 * ui) if chip is not None else self.width() - 8 * ui
            if not name:
                p.setFont(self._font(12))
                p.setPen(colour(tk["faint"]))
                p.drawText(QtCore.QRectF(x, 0, right - x, self.height()), Qt.AlignVCenter | Qt.AlignLeft,
                           "Nothing selected")
                p.end()
                return
            p.setFont(self._font(12.5, True))
            fm = QtGui.QFontMetrics(p.font())
            pill_w = 0
            if more:
                pf = self._font(10.5, True)
                pill_w = QtGui.QFontMetrics(pf).horizontalAdvance(more) + 12 * ui
            text = fm.elidedText(name, Qt.ElideMiddle, int(max(10, right - x - pill_w - 6 * ui)))
            p.setPen(colour(tk["text"]))
            p.drawText(QtCore.QRectF(x, 0, right - x, self.height()), Qt.AlignVCenter | Qt.AlignLeft, text)
            if more:
                px_ = x + fm.horizontalAdvance(text) + 6 * ui
                pr = QtCore.QRectF(px_, (self.height() - 16 * ui) / 2.0, pill_w, 16 * ui)
                p.setPen(QtGui.QPen(colour(tk["line"]), 1))
                p.setBrush(colour(tk["card"]))
                p.drawRoundedRect(pr, 8 * ui, 8 * ui)
                p.setFont(self._font(10.5, True))
                p.setPen(colour(tk["muted"]))
                p.drawText(pr, Qt.AlignCenter, more)
            if chip is not None:
                p.setPen(QtGui.QPen(colour(tk["line"]), 1))
                p.setBrush(colour(tk["hover"] if self.hover else tk["card"]))
                r = chip.height() / 2.0
                p.drawRoundedRect(chip, r, r)
                p.setFont(self._font(11.5))
                p.setPen(colour(tk["text"] if self.hover else tk["muted"]))
                p.drawText(chip, Qt.AlignCenter, (box.layer_text or "") + "  ▾")
            p.end()

    # -- the value editor --------------------------------------------------------------

    class Edit(QtWidgets.QLineEdit):
        def __init__(self, canvas, channel, rect, text=None):
            super(Edit, self).__init__(canvas)
            self.canvas, self.channel, self.done = canvas, channel, False
            self.setObjectName(EDIT)
            tk, ui = canvas.box.tokens, canvas.box.ui
            self.setStyleSheet(
                "QLineEdit#%s { background: %s; color: %s; border: %dpx solid %s; border-radius: %dpx;"
                " padding: 0 %dpx; font-family: Consolas, monospace; font-size: %dpx; }"
                % (EDIT, tk["field"], tk["text"], max(1, int(ui)), tk["accent"], int(4 * ui),
                   int(5 * ui), max(9, int(12 * ui))))
            self.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.setGeometry(rectf(rect).toRect())
            self.setText(look.fmt(channel["value"], channel["kind"], canvas.box.precision,
                                  channel.get("names")))
            self.returnPressed.connect(lambda: self.finish(True))
            self.editingFinished.connect(lambda: self.finish(True))
            if text is not None:                     # typed straight onto the rows
                self.setText(text)
            self.show()
            self.setFocus()
            if text is None:
                self.selectAll()

        def keyPressEvent(self, event):
            if event.key() == Qt.Key_Escape:
                self.finish(False)
                return
            super(Edit, self).keyPressEvent(event)

        def finish(self, apply):
            if self.done:
                return
            self.done = True
            text = self.text()
            self.hide()
            self.deleteLater()
            self.canvas.editor = None
            if apply:
                self.canvas.box.typed(self.channel, text)

    # -- the canvas of rows ----------------------------------------------------------

    class Canvas(QtWidgets.QWidget):
        def __init__(self, box):
            super(Canvas, self).__init__()
            self.box = box
            self.setObjectName(CANVAS)
            self.setMouseTracking(True)
            self.setAttribute(Qt.WA_StyledBackground, True)
            self.editor = None
            self.press = None
            self.before = set()                      # the selection the last press found
            self.setFocusPolicy(Qt.ClickFocus)       # typing onto the selected channels

        def resizeEvent(self, event):
            self.box.relayout(self.width())
            super(Canvas, self).resizeEvent(event)

        def paintEvent(self, event):
            guarded(self, lambda: self._paint(event.rect()))

        def _paint(self, clip):
            box, tk, ui = self.box, self.box.tokens, self.box.ui
            p = QtGui.QPainter(self)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            p.fillRect(clip, colour(tk["panel"]))
            if not box.rows:
                p.setPen(colour(tk["faint"]))
                f = QtGui.QFont(self.font())
                f.setPixelSize(max(8, int(12 * ui)))
                p.setFont(f)
                p.drawText(QtCore.QRectF(0, 0, self.width(), 60 * ui), Qt.AlignCenter,
                           "Select an object to see its channels")
                p.end()
                return
            name_font = QtGui.QFont(self.font())
            name_font.setPixelSize(max(8, int(round(12 * ui))))
            value_font = QtGui.QFont("Consolas")
            value_font.setStyleHint(QtGui.QFont.Monospace)
            value_font.setPixelSize(max(8, int(round(12 * ui))))
            caption = QtGui.QFont(self.font())
            caption.setPixelSize(max(7, int(round(9.5 * ui))))
            caption.setBold(True)
            caption.setLetterSpacing(QtGui.QFont.AbsoluteSpacing, 1.0 * ui)
            for i, (y, h, parts) in enumerate(box.placed):
                if y + h < clip.top() or y > clip.bottom():
                    continue
                row = box.rows[i]
                if row["kind"] == "rule":
                    p.fillRect(QtCore.QRectF(4 * ui, y + h / 2.0, self.width() - 8 * ui, 1),
                               colour(tk["track_edge"]))
                elif row["kind"] == "section":
                    self._paint_section(p, row, parts, caption, name_font, i)
                else:
                    self._paint_channel(p, row["channel"], parts, i, name_font, value_font)
            p.end()

        def _paint_section(self, p, row, parts, caption, name_font, i):
            box, tk, ui = self.box, self.box.tokens, self.box.ui
            rx, ry, rw, rh = parts["row"]
            hovered = box.hovered(i)
            if hovered:
                p.setPen(Qt.NoPen)
                p.setBrush(colour(tk["hover"]))
                p.drawRoundedRect(QtCore.QRectF(rx, ry, rw, rh), 4 * ui, 4 * ui)
            side = 10 * ui
            p.save()
            c = QtCore.QPointF(rx + 6 * ui + side / 2.0, ry + rh / 2.0)
            p.translate(c)
            if row["open"]:
                p.rotate(90)
            draw_glyph(p, "chev", QtCore.QRectF(-side / 2.0, -side / 2.0, side, side), tk["muted"])
            p.restore()
            x = rx + 22 * ui
            if row.get("title"):
                p.setFont(caption)
                p.setPen(colour(tk["faint"]))
                p.drawText(QtCore.QRectF(x, ry, 60 * ui, rh), Qt.AlignVCenter | Qt.AlignLeft, row["title"])
            x += 62 * ui
            p.setFont(name_font)
            p.setPen(colour(tk["text"] if hovered else tk["muted"]))
            p.drawText(QtCore.QRectF(x, ry, rx + rw - x, rh), Qt.AlignVCenter | Qt.AlignLeft, row["label"])

        def _paint_channel(self, p, ch, parts, i, name_font, value_font):
            box, tk, ui = self.box, self.box.tokens, self.box.ui
            state, muted, changed = look.state_of(ch)
            selected = ch["key"] in box.selected
            hovered = box.hovered(i)
            rx, ry, rw, rh = parts["row"]
            if selected or hovered:
                p.setPen(Qt.NoPen)
                p.setBrush(colour(tk["accent_tint"] if selected else tk["hover"]))
                p.drawRoundedRect(QtCore.QRectF(rx, ry, rw, rh), 4 * ui, 4 * ui)
            # the key cell
            self._paint_cell(p, QtCore.QRectF(*look.cell_rect(parts["mark"], ui)), state, muted, changed)
            # the name
            if state == "locked":
                ink = colour(tk["faint"])
            elif selected:
                ink = colour(tk["accent_text"])
            else:
                ink = colour(tk["text"] if hovered else tk["text2"])
            nx, ny, nw, nh = parts["name"]
            p.setFont(name_font)
            p.setPen(ink)
            fm = QtGui.QFontMetrics(name_font)
            p.drawText(QtCore.QRectF(nx, ny, nw, nh), Qt.AlignVCenter | Qt.AlignRight,
                       fm.elidedText(ch["nice"], Qt.ElideRight, int(max(4, nw))))
            # the value well
            well = QtCore.QRectF(*parts["value"])
            radius = 4 * ui
            if state != "locked":
                p.setBrush(colour(tk["field"]))
                edge = tk["accent_dim"] if (changed and "accent_dim" in tk) else (
                    "#7a4a28" if changed else tk["track_edge"])
                p.setPen(QtGui.QPen(colour(edge), max(1.0, ui)))
                p.drawRoundedRect(well, radius, radius)
            if state == "locked":
                vink = tk["faint"]
            elif state == "driven":
                vink = look.DRIVEN
            elif muted:
                vink = look.MUTED
            elif changed:
                vink = tk["accent_text"]
            else:
                vink = tk["text"]
            p.setFont(value_font)
            p.setPen(colour(vink))
            inner = well.adjusted(5 * ui, 0, -6 * ui, 0)
            text = look.fmt(ch["value"], ch["kind"], box.precision, ch.get("names"))
            text = QtGui.QFontMetrics(value_font).elidedText(text, Qt.ElideRight, int(max(4, inner.width())))
            p.drawText(inner, Qt.AlignVCenter | Qt.AlignRight, text)

        def _paint_cell(self, p, cell, state, muted, changed):
            tk, ui = self.box.tokens, self.box.ui
            accent = look.MUTED if muted else tk["accent"]
            p.setPen(Qt.NoPen)
            r = 2 * ui
            if state == "locked":
                side = 11 * ui
                draw_glyph(p, "lock", QtCore.QRectF(cell.center().x() - side / 2, cell.center().y() - side / 2,
                                                    side, side), tk["faint"])
                return
            if state == "driven":
                side = 12 * ui
                draw_glyph(p, "link", QtCore.QRectF(cell.center().x() - side / 2, cell.center().y() - side / 2,
                                                    side, side), look.DRIVEN)
                return
            if state == "onkey":
                p.setBrush(colour(accent))
                p.drawRoundedRect(cell, r, r)
            elif state == "onbd":
                p.setBrush(colour(look.MUTED if muted else look.BREAKDOWN))
                p.drawRoundedRect(cell, r, r)
            elif state == "keyed":
                p.setPen(QtGui.QPen(colour(accent), 1.5 * ui))
                p.setBrush(Qt.NoBrush)
                p.drawRoundedRect(cell.adjusted(0.75 * ui, 0.75 * ui, -0.75 * ui, -0.75 * ui), r, r)
            else:
                p.setBrush(colour(tk["track"]))
                p.setPen(QtGui.QPen(colour(tk["track_edge"]), 1))
                p.drawRoundedRect(cell, r, r)
            if muted:
                p.setPen(QtGui.QPen(colour(look.MUTED), 1.5 * ui))
                c = cell.center()
                p.drawLine(QtCore.QPointF(c.x() - 4 * ui, c.y() + 6 * ui), QtCore.QPointF(c.x() + 4 * ui, c.y() - 6 * ui))
            if changed:
                pen = QtGui.QPen(colour(tk["accent_text"]), 1.2 * ui)
                pen.setStyle(Qt.DashLine)
                p.setPen(pen)
                p.setBrush(Qt.NoBrush)
                g = 2 * ui
                p.drawRoundedRect(cell.adjusted(-g, -g, g, g), r + g, r + g)

        # the hand ------------------------------------------------------------------
        def _hit(self, pos):
            return look.hit(self.box.placed, self.box.rows, pos.x(), pos.y())

        def _row_at(self, y):
            """The channel row nearest y (a sweep past the ends keeps the last row)."""
            best, gap = None, None
            for i, (ry, rh, _parts) in enumerate(self.box.placed):
                if self.box.rows[i]["kind"] != "channel":
                    continue
                d = 0.0 if ry <= y < ry + rh else min(abs(y - ry), abs(y - ry - rh))
                if gap is None or d < gap:
                    best, gap = i, d
            return best

        def mouseMoveEvent(self, event):
            pos = event.position()
            press = self.press
            if press is not None:
                if press.get("mode") is None:
                    dx, dy = pos.x() - press["x"], pos.y() - press["y"]
                    if max(abs(dx), abs(dy)) < 3 * self.box.ui:
                        return
                    # down the rows: a sweep selects them, as Maya's; across: the slider
                    press["mode"] = "sweep" if abs(dy) > abs(dx) else "slide"
                if press["mode"] == "sweep":
                    press["moved"] = True
                    i = self._row_at(pos.y())
                    if i is not None:
                        self.box.sweep(press, self.box.rows[i]["channel"]["key"])
                    return
                self.box.drag(press, pos.x(), event.modifiers())
                return
            i, part = self._hit(pos)
            self.box.aim_at(i, part)
            self.setCursor(Qt.PointingHandCursor if part in ("mark", "section") else
                           Qt.SizeHorCursor if part in ("name", "value") else Qt.ArrowCursor)

        def leaveEvent(self, event):
            self.box.aim_at(None, None)

        def mousePressEvent(self, event):
            if event.button() != Qt.LeftButton:
                return
            i, part = self._hit(event.position())
            if i is None:
                return
            if part == "section":
                self.box.toggle_section(self.box.rows[i]["key"])
                return
            ch = self.box.rows[i]["channel"]
            if part == "mark":
                self.box.toggle_key(ch)
                return
            self.before = set(self.box.selected)
            mods = event.modifiers()
            self.press = {"index": i, "part": part, "x": event.position().x(),
                          "y": event.position().y(), "moved": False, "mode": None,
                          "channel": ch, "mods": mods,
                          "base": set(self.box.selected) if mods & Qt.ControlModifier else set()}

        def mouseReleaseEvent(self, event):
            press, self.press = self.press, None
            if press is None:
                return
            if press.get("mode") == "sweep":
                self.box.sync()
                return
            if press["moved"]:
                self.box.drag_done(press)
                return
            ch = press["channel"]
            mods = event.modifiers()
            if press["part"] == "value" and ch["kind"] == "bool" and ch["key"] in self.box.selected | {ch["key"]}:
                self.box.toggle_bool(ch)
            elif press["part"] == "value" and ch["kind"] == "enum":
                self.box.enum_menu(ch, self.mapToGlobal(event.position().toPoint()))
            self.box.click(ch, bool(mods & Qt.ControlModifier), bool(mods & Qt.ShiftModifier))

        def mouseDoubleClickEvent(self, event):
            i, part = self._hit(event.position())
            if i is None or part != "value":
                return
            ch = self.box.rows[i]["channel"]
            if ch["kind"] in ("bool", "enum") or look.state_of(ch)[0] == "locked":
                return
            if ch["key"] in self.before and len(self.before) > 1:
                # the first click of the double collapsed a sweep: Maya keeps it
                self.box.selected = set(self.before)
                self.box.sync()
                self.update()
            self.open_editor(i)

        def open_editor(self, i, text=None):
            if self.editor is not None:
                self.editor.finish(False)
            ch = self.box.rows[i]["channel"]
            self.editor = Edit(self, ch, self.box.placed[i][2]["value"], text)

        def keyPressEvent(self, event):
            """A digit (or - . + = * /) typed with channels selected starts the value
            on the last of them; Enter applies it to every one, as in Maya."""
            text = event.text()
            if self.editor is None and look.starts_typing(text):
                i = self.box.typing_row()
                if i is not None:
                    self.open_editor(i, text)
                    return
            super(Canvas, self).keyPressEvent(event)

        def contextMenuEvent(self, event):
            i, part = self._hit(event.pos())
            if i is not None and part not in ("section",) and self.box.rows[i]["kind"] == "channel":
                ch = self.box.rows[i]["channel"]
                if ch["key"] not in self.box.selected:
                    self.box.click(ch, False, False)
            self.box.context_menu(event.globalPos())

    # -- the box -----------------------------------------------------------------------

    class Box(QtWidgets.QWidget):
        def __init__(self, link, ui=1.0, tokens=None, parent=None):
            super(Box, self).__init__(parent)
            self.setObjectName(ROOT)
            self.setAttribute(Qt.WA_StyledBackground, True)
            self.link, self.ui = link, float(ui or 1.0)
            self.tokens = dict(tokens or _tokens())
            self.setStyleSheet("QWidget#%s, QWidget#%s { background: %s; }" % (ROOT, CANVAS, self.tokens["panel"]))
            self.objects, self.lead, self.frame = [], None, None
            self.sections, self.rows, self.placed = [], [], []
            self.selected, self.anchor, self.opened = set(), None, set()
            self.under = None               # (row index, part) under the mouse
            self.precision, self.speed = 3, 1.0
            self.layer_text = ""
            self.clipboard = {}
            self.scrub = None
            column = QtWidgets.QVBoxLayout(self)
            column.setObjectName("skeldarChannelBoxLayout")
            column.setContentsMargins(0, 0, 0, 0)
            column.setSpacing(0)
            self.head = Head(self)
            column.addWidget(self.head)
            self.scroll = QtWidgets.QScrollArea(self)
            self.scroll.setObjectName(SCROLL)
            self.scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
            self.scroll.setWidgetResizable(True)
            self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.canvas = Canvas(self)
            self.scroll.setWidget(self.canvas)
            column.addWidget(self.scroll, 1)
            self.setMinimumWidth(int(60 * self.ui))      # the side panel narrows to 86 (2026-10-19)

        # the mouse -----------------------------------------------------------------
        def hovered(self, i):
            """True when row `i` is under the mouse."""
            return self.under is not None and self.under[0] == i

        def aim_at(self, i, part):
            under = (i, part) if i is not None else None
            if under != self.under:
                self.under = under
                self.canvas.update()

        # data ----------------------------------------------------------------------
        def relayout(self, width=None):
            width = self.canvas.width() if width is None else width
            self.rows = look.rows(self.sections, self.opened) if self.lead else []
            self.placed, height = look.layout(self.rows, max(1, width), self.ui)
            self.canvas.setMinimumHeight(int(height))

        def order(self):
            return [r["channel"]["key"] for r in self.rows if r["kind"] == "channel"]

        def channels(self):
            return [r["channel"] for r in self.rows if r["kind"] == "channel"]

        def refresh(self):
            """Everything read again."""
            snap = self.link.snapshot(tuple(self.opened))
            self.objects = snap.get("objects", [])
            self.lead = snap.get("lead")
            self.frame = snap.get("frame")
            self.sections = snap.get("sections", [])
            try:
                self.precision = int(self.link.precision())
                self.speed = float(self.link.speed())
            except Exception:                                # noqa: BLE001
                pass
            try:
                self.layer_text = self.link.layer_label() or ""
            except Exception:                                # noqa: BLE001
                self.layer_text = ""
            keys = set(ch["key"] for s in self.sections for ch in s.get("channels", []))
            self.selected &= keys
            self.relayout()
            self.head.update()
            self.canvas.update()

        def on_values(self):
            """A value set elsewhere (a manipulator, a script): the values read again."""
            chans = self.channels()
            for ch, v in zip(chans, self.link.values([ch["plug"] for ch in chans])):
                if v is not None:
                    ch["value"] = v
            self.canvas.update()

        def on_time(self):
            """Time moved (every frame of playback too): the values and the key cells
            read again - no full read."""
            frame = self.link.now()
            self.frame = frame
            chans = self.channels()
            values = self.link.values([ch["plug"] for ch in chans])
            moved = set()
            for ch, v in zip(chans, values):
                before = (ch.get("value"), ch.get("on_key"), ch.get("changed"), ch.get("breakdown"))
                if v is not None:
                    ch["value"] = v
                ks = ch.get("keys") or []
                ch["on_key"] = any(abs(k - frame) < 1e-3 for k in ks)
                ch["changed"] = False
                ch["breakdown"] = ch["on_key"] and any(abs(b - frame) < 1e-3
                                                       for b in ch.get("breakdowns") or [])
                if (ch.get("value"), ch["on_key"], ch["changed"], ch["breakdown"]) != before:
                    moved.add(id(ch))
            #  only the rows that changed, painted now (2026-10-27: the whole box every
            #  frame of playback cost 1.8 ms; most channels hold still)
            if moved and self.canvas.isVisible():
                region = QtGui.QRegion()
                width = self.canvas.width()
                for row, place in zip(self.rows, self.placed):
                    if row["kind"] == "channel" and id(row["channel"]) in moved:
                        y, h = place[0], place[1]
                        region += QtCore.QRect(0, int(math.floor(y)), width, int(math.ceil(h)) + 1)
                if not region.isEmpty():
                    self.canvas.repaint(region)

        # selection -------------------------------------------------------------------
        def click(self, ch, ctrl=False, shift=False):
            self.selected, self.anchor = look.select(self.order(), self.selected, self.anchor,
                                                     ch["key"], ctrl, shift)
            self.sync()
            self.canvas.update()

        def sweep(self, press, key):
            """A drag down the rows: the run from the pressed channel to `key`."""
            start = press["channel"]["key"]
            chosen = look.sweep(self.order(), press.get("base") or set(), start, key)
            if chosen != self.selected:
                self.selected, self.anchor = chosen, start
                self.canvas.update()

        def typing_row(self):
            """The row a value typed onto the selection opens on: the last selected
            channel that takes a typed number."""
            found = None
            for i, r in enumerate(self.rows):
                if r["kind"] != "channel":
                    continue
                ch = r["channel"]
                if (ch["key"] in self.selected and ch["kind"] not in ("bool", "enum")
                        and look.state_of(ch)[0] != "locked"):
                    found = i
            return found

        def sync(self):
            try:
                self.link.sync_selection(self.selected_plugs())
            except Exception:                                # noqa: BLE001
                pass

        def selected_channels(self):
            return [ch for ch in self.channels() if ch["key"] in self.selected]

        def selected_plugs(self):
            out = []
            for ch in self.selected_channels():
                out.extend(ch.get("targets") or [ch["plug"]])
            return out

        def toggle_section(self, key):
            if key in self.opened:
                self.opened.discard(key)
            else:
                self.opened.add(key)
            self.refresh()

        # presses ----------------------------------------------------------------------
        def _chunk(self, name, call):
            self.link.chunk_open(name)
            try:
                return call()
            finally:
                self.link.chunk_close()

        def toggle_key(self, ch):
            if ch.get("locked"):
                return
            plugs = ch.get("targets") or [ch["plug"]]
            if ch.get("on_key"):
                self._chunk("skeldarChannelBoxUnkey", lambda: self.link.unkey(plugs, self.frame))
            else:
                self._chunk("skeldarChannelBoxKey", lambda: self.link.key(plugs))
            self.refresh()

        def key_selected(self, breakdown=False):
            chans = self.selected_channels() or self.channels()
            plugs = [p for ch in chans for p in (ch.get("targets") or [ch["plug"]])]
            self._chunk("skeldarChannelBoxKey", lambda: self.link.key(plugs, breakdown))
            self.refresh()

        def unkey_selected(self):
            chans = self.selected_channels() or self.channels()
            plugs = [p for ch in chans if ch.get("on_key") for p in (ch.get("targets") or [ch["plug"]])]
            if plugs:
                self._chunk("skeldarChannelBoxUnkey", lambda: self.link.unkey(plugs, self.frame))
                self.refresh()

        def toggle_bool(self, ch):
            chans = self.selected_channels() if ch["key"] in self.selected else [ch]
            value = 0 if ch["value"] else 1
            pairs = [(p, value) for c in chans if c["kind"] == "bool"
                     for p in (c.get("targets") or [c["plug"]])]
            self._chunk("skeldarChannelBoxSet", lambda: self.link.write(pairs))
            self.refresh()

        def set_enum(self, ch, index):
            pairs = [(p, int(index)) for p in (ch.get("targets") or [ch["plug"]])]
            self._chunk("skeldarChannelBoxSet", lambda: self.link.write(pairs))
            self.refresh()

        def typed(self, ch, text):
            chans = self.selected_channels() if ch["key"] in self.selected else [ch]
            pairs = []
            for c in chans:
                value = look.typed(text, c["value"], c["kind"])
                if value is None or c.get("locked"):
                    continue
                pairs.extend((p, value) for p in (c.get("targets") or [c["plug"]]))
            if pairs:
                self._chunk("skeldarChannelBoxSet", lambda: self.link.write(pairs))
            self.refresh()

        def drag(self, press, x, mods):
            dx = x - press["x"]
            if not press["moved"]:
                if abs(dx) < 3 * self.ui:
                    return
                press["moved"] = True
                ch = press["channel"]
                if ch["key"] not in self.selected:
                    self.click(ch)
                chans = [c for c in self.selected_channels()
                         if not c.get("locked") and c["kind"] not in ("bool", "enum")
                         and look.state_of(c)[0] != "driven"]
                press["chans"] = [(c, float(look.ensure_finite(c["value"])),
                                   look.per_px(c["attr"], c["kind"], self.speed, c.get("lo"), c.get("hi")))
                                  for c in chans]
                self.link.chunk_open("skeldarChannelBoxDrag")
                press["open"] = True
            mul = look.modifier(bool(mods & Qt.ShiftModifier), bool(mods & Qt.ControlModifier))
            pairs = []
            for c, start, step in press.get("chans", []):
                value = look.scrubbed(start, dx * mul, step, c.get("lo"), c.get("hi"), c["kind"])
                c["value"] = value
                pairs.extend((p, value) for p in (c.get("targets") or [c["plug"]]))
            if pairs:
                self.link.write(pairs)
            self.canvas.update()

        def drag_done(self, press):
            if press.get("open"):
                self.link.chunk_close()
            self.refresh()

        # menus -------------------------------------------------------------------------
        def _menu(self, point, rows):
            menu = QtWidgets.QMenu(self)
            ui = self.ui
            px = lambda v: "%dpx" % max(1, int(round(v * ui)))          # noqa: E731
            menu.setStyleSheet(MENU_SHEET.format(p2=px(2), p4=px(4), p12=px(12), r4=px(4), **self.tokens))
            picked = []
            for row in rows:
                if row is None:
                    menu.addSeparator()
                    continue
                label, call = row
                action = maya_hubqt.tag_row(menu.addAction(label), len(picked))
                action.setEnabled(call is not None)
                picked.append((action, call))
            try:
                #  by the row's number, never its wrapper (maya_hubqt.tag_row, 2026-10-28)
                index = maya_hubqt.row_value(menu.exec(point))
            finally:
                menu.deleteLater()
            if isinstance(index, int) and 0 <= index < len(picked) and picked[index][1] is not None:
                guarded(self, picked[index][1])
                return True
            return False

        def layer_menu(self, point):
            found = self.link.layers()
            if not found:
                return
            rows = [(("• " if sel else "   ") + label, (lambda n=name: self._pick_layer(n)))
                    for name, label, sel in found]
            self._menu(point, rows)

        def _pick_layer(self, name):
            self.link.pick_layer(name)
            self.layer_text = self.link.layer_label() or ""
            self.head.update()

        def enum_menu(self, ch, point):
            names = ch.get("names") or []
            rows = [(("• " if i == int(ch["value"] or 0) else "   ") + n,
                     (lambda i=i: self.set_enum(ch, i))) for i, n in enumerate(names)]
            self._menu(point, rows)

        def menu_rows(self):
            chans = self.selected_channels()
            some = bool(chans)
            plugs = self.selected_plugs()
            frame = self.frame if self.frame is not None else 0
            speed_rows = [(("• " if abs(self.speed - v) < 1e-6 else "   ") + "Channel Speed: " + label,
                           (lambda v=v: self._set_speed(v))) for label, v in SPEEDS]
            return ([("Key Selected", lambda: self.key_selected(False)),
                     ("Breakdown Selected", lambda: self.key_selected(True)),
                     ("Delete Keys at %s" % look.fmt(frame), self.unkey_selected),
                     None,
                     ("Mute Selected", (lambda: self._plugs_call("mute", plugs, True)) if some else None),
                     ("Unmute Selected", (lambda: self._plugs_call("mute", plugs, False)) if some else None),
                     ("Lock Selected", (lambda: self._plugs_call("lock", plugs, True)) if some else None),
                     ("Unlock Selected", (lambda: self._plugs_call("lock", plugs, False)) if some else None),
                     None,
                     ("Select Connection", (lambda: self.link.select_connection(plugs)) if some else None),
                     ("Break Connections", (lambda: self._plugs_call("break_connections", plugs)) if some else None),
                     None,
                     ("Copy Values", self.copy_values if some else None),
                     ("Paste Values", self.paste_values if (some and self.clipboard) else None),
                     None]
                    + speed_rows
                    + [None, ("Maya's Channel Box", self.link.show_maya_box)])

        def context_menu(self, point):
            self._menu(point, self.menu_rows())

        def _plugs_call(self, name, plugs, *args):
            self._chunk("skeldarChannelBox_" + name, lambda: getattr(self.link, name)(plugs, *args))
            self.refresh()

        def _set_speed(self, value):
            self.link.set_speed(value)
            self.speed = float(value)

        def copy_values(self):
            self.clipboard = dict((ch["key"], ch["value"]) for ch in self.selected_channels())

        def paste_values(self):
            chans = self.selected_channels()
            if not chans or not self.clipboard:
                return
            single = list(self.clipboard.values())[0] if len(self.clipboard) == 1 else None
            pairs = []
            for ch in chans:
                value = self.clipboard.get(ch["key"], single)
                if value is None or ch.get("locked"):
                    continue
                pairs.extend((p, value) for p in (ch.get("targets") or [ch["plug"]]))
            if pairs:
                self._chunk("skeldarChannelBoxPaste", lambda: self.link.write(pairs))
                self.refresh()

    _CLASSES["all"] = (Box,)
    return _CLASSES["all"]


def make(link, ui=1.0, tokens=None, parent=None):
    return classes()[0](link, ui, tokens, parent)
