"""The skill library (2026-10-19): a drawer standing over the Time Bar's strip, as wide as it -
a search field, the categories, every skill a chip. A chip clicked goes to the cell the drawer was
opened for (else the page shown's first free cell); a chip dragged goes where it is let go (a cell,
a page tab). It opens out of the point it was asked from, its chips popping in nearest first, and
folds back into it.

`show(target, point)` is the road (the strip's empty cells and menus call it through the skills
adapter); `make(strip, ...)` builds one for the tests with the entries handed in.
"""

import sys
import time
import traceback

from . import look

NAME = "skeldarSkillLibrary"
HEIGHT = 196            # logical px
HEAD_H = 30
CHIP_W, CHIP_H = 76, 58
CHIP_GAP = 4
PAD = 8
FOLD_MS = 168
DRAG_PX = 6

_CLASSES = {}


def _state():
    st = getattr(sys, "_skeldar_skill_library", None)
    if st is None:
        st = {"window": None}
        sys._skeldar_skill_library = st
    return st


def chip_rects(width, count, ui=1.0, scroll=0.0):
    """[(x, y, w, h)] of `count` chips in a drawer `width` px wide, under its head."""
    pad, gap = PAD * ui, CHIP_GAP * ui
    w, h = CHIP_W * ui, CHIP_H * ui
    cols = max(1, int((width - 2 * pad + gap) // (w + gap)))
    top = (HEAD_H + 6) * ui - scroll
    return [(pad + (i % cols) * (w + gap), top + (i // cols) * (h + gap), w, h) for i in range(count)]


def chip_at(x, y, rects):
    for i, (cx, cy, w, h) in enumerate(rects):
        if cx <= x <= cx + w and cy <= y <= cy + h:
            return i
    return None


def content_height(width, count, ui=1.0):
    rects = chip_rects(width, count, ui)
    if not rects:
        return 0.0
    return rects[-1][1] + rects[-1][3] + PAD * ui


def show(target=None, point=None):
    """The drawer over the live strip, for `target` (("cell", n, r, c) or None)."""
    from maya_timebar import bar
    strip = bar.current()
    if strip is None:
        return "The skill library lives on the Time Bar - ⋮ -> Time bar"
    close(instant=True)
    window = make(strip, target, point)
    window.open()
    return ""


def is_open():
    window = _state().get("window")
    try:
        return window is not None and window.isVisible() and window.folding is None
    except RuntimeError:
        return False


def close(instant=False):
    window = _state().get("window")
    _state()["window"] = None
    if window is None:
        return
    try:
        window.fold(instant=instant)
    except RuntimeError:
        pass


def make(strip, target=None, point=None, entries=None, motion=None):
    Drawer = classes()
    window = Drawer(strip, target, point, entries, motion)
    _state()["window"] = window
    return window


def classes():
    if "drawer" in _CLASSES:
        return _CLASSES["drawer"]
    import maya_hubqt
    from maya_timebar import bar as timebar, look as tlook
    from . import grid as skillgrid, sources
    q = maya_hubqt.qt()
    QtCore, QtGui, QtWidgets = q.QtCore, q.QtGui, q.QtWidgets
    Qt = QtCore.Qt

    def font(px, bold=False):
        f = QtGui.QFont()
        f.setPixelSize(max(6, int(round(px))))
        f.setBold(bold)
        return f

    class Drawer(QtWidgets.QWidget):

        def __init__(self, strip, target, point, entries, motion):
            parent = strip.window() if strip.window() is not strip else None
            super(Drawer, self).__init__(parent, Qt.Tool | Qt.FramelessWindowHint)
            self.setObjectName(NAME)
            self.setAttribute(Qt.WA_TranslucentBackground)
            self.setAttribute(Qt.WA_ShowWithoutActivating, False)
            self.setMouseTracking(True)
            self.strip, self.target = strip, target
            self.ui = strip.ui
            self.tokens = strip.tokens
            self.motion = strip.motion if motion is None else bool(motion)
            self._entries = entries or sources.entries
            self.category = "All"
            self.found = []
            self.hover = None
            self.lift = {}
            self.scroll = 0.0
            self.press = None
            self.drag = None
            self.t0 = self._clock()
            self.folding = None
            self.origin = point
            ui = self.ui
            self.search = QtWidgets.QLineEdit(self)
            self.search.setObjectName("skeldarSkillSearch")
            self.search.setPlaceholderText("Search skills")
            self.search.setClearButtonEnabled(True)
            self.search.textChanged.connect(lambda *_a: self.reload())
            self.search.setStyleSheet(
                "QLineEdit#skeldarSkillSearch { background: %s; color: %s; border: 1px solid %s;"
                " border-radius: %dpx; padding: 0 %dpx; }"
                "QLineEdit#skeldarSkillSearch:focus { border: 1px solid %s; }"
                % (self.tokens["field"], self.tokens["text"], self.tokens["track_edge"], int(5 * ui),
                   int(6 * ui), self.tokens["accent"]))
            self.timer = QtCore.QTimer(self)
            self.timer.setInterval(16)
            self.timer.timeout.connect(self._tick)
            self.place()
            self.reload()

        # geometry -----------------------------------------------------------------
        def _clock(self):
            return time.time() * 1000.0

        def place(self):
            ui = self.ui
            g = self.strip.mapToGlobal(QtCore.QPoint(0, 0))
            w = self.strip.width()
            h = int(HEIGHT * ui)
            self.setGeometry(g.x(), g.y() - h - int(6 * ui), w, h)
            self.search.setGeometry(int(PAD * ui), int(5 * ui), int(200 * ui), int(22 * ui))

        def cat_rects(self):
            ui = self.ui
            f = QtGui.QFontMetrics(font(11 * ui))
            x = PAD * ui + 210 * ui
            out = []
            for name in sources.CATEGORIES:
                w = f.horizontalAdvance(name) + 16 * ui
                out.append((x, 6 * ui, w, 20 * ui))
                x += w + 2 * ui
            return out

        def close_rect(self):
            ui = self.ui
            return (self.width() - (PAD + 22) * ui, 5 * ui, 22 * ui, 22 * ui)

        def rects(self):
            return chip_rects(self.width(), len(self.found), self.ui, self.scroll)

        # data ---------------------------------------------------------------------
        def reload(self):
            try:
                self.found = list(self._entries(self.category, self.search.text()))
            except Exception:                                # noqa: BLE001
                print(traceback.format_exc())
                self.found = []
            self.scroll = 0.0
            self.hover = None
            self.update()

        def set_category(self, name):
            if name != self.category:
                self.category = name
                self.reload()
                self.t0 = self._clock()     # the chips pop in again
                self._kick()

        def item_of(self, i):
            return self.found[i][1] if 0 <= i < len(self.found) else None

        # opening / closing --------------------------------------------------------
        def open(self):
            self.place()
            self.show()
            self.raise_()
            self.t0 = self._clock()
            self._kick()
            self.search.setFocus()

        def fold(self, instant=False):
            if instant or not self.motion or not self.isVisible():
                self._gone()
                return
            self.folding = self._clock()
            self._kick()

        def _gone(self):
            self.timer.stop()
            try:
                self.hide()
                self.deleteLater()
            except RuntimeError:
                pass

        def _origin_local(self):
            if not self.origin:
                return QtCore.QPointF(self.width() / 2.0, self.height())
            p = self.mapFromGlobal(QtCore.QPoint(int(self.origin[0]), int(self.origin[1])))
            return QtCore.QPointF(p)

        def _entrance(self, x, y):
            if not self.motion:
                return 1.0, 1.0
            o = self._origin_local()
            now = self._clock()
            if self.folding is not None:
                return tlook.folding(now - self.folding, tlook.fold_delay(x - o.x(), self.ui) * 0.5, FOLD_MS)
            return tlook.popping(now - self.t0, tlook.burst_delay(x - o.x(), y - o.y(), self.ui))

        def _kick(self):
            if not self.timer.isActive():
                self.timer.start()

        def _tick(self):
            try:
                now = self._clock()
                busy = False
                for i in list(self.lift):
                    goal = 1.0 if i == self.hover else 0.0
                    self.lift[i] = tlook.approach(self.lift[i], goal, 16, skillgrid.HOVER_MS) \
                        if self.motion else goal
                    busy = busy or abs(self.lift[i] - goal) > 0.005
                if self.motion and now - self.t0 < 900:
                    busy = True
                if self.folding is not None:
                    if now - self.folding > FOLD_MS + 300:
                        self._gone()
                        return
                    busy = True
                self.update()
                if not busy:
                    self.timer.stop()
            except Exception:                                # noqa: BLE001
                self.timer.stop()
                print(traceback.format_exc())

        # the mouse ----------------------------------------------------------------
        def _xy(self, event):
            p = event.position() if hasattr(event, "position") else event.pos()
            return p.x(), p.y()

        def _gxy(self, event):
            p = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()
            return p.x(), p.y()

        def mouseMoveEvent(self, event):
            x, y = self._xy(event)
            if self.press is not None and self.drag is None:
                gx, gy = self._gxy(event)
                if abs(gx - self.press[1]) + abs(gy - self.press[2]) > DRAG_PX * self.ui:
                    self._start_drag(self.press[0])
            if self.drag is not None:
                self._drag_to(*self._gxy(event))
                return
            hover = chip_at(x, y, self.rects()) if y > HEAD_H * self.ui else None
            if hover != self.hover:
                self.hover = hover
                if hover is not None:
                    self.lift.setdefault(hover, 0.0)
                    self.setToolTip(self.found[hover][2] + "\n" + self.found[hover][0])
                self._kick()

        def leaveEvent(self, event):
            if self.drag is None:
                self.hover = None
                self._kick()
            super(Drawer, self).leaveEvent(event)

        def mousePressEvent(self, event):
            x, y = self._xy(event)
            if event.button() == Qt.RightButton and self.drag is not None:
                self._end_drag()
                return
            if event.button() != Qt.LeftButton:
                return
            cx, cy, cw, ch = self.close_rect()
            if cx <= x <= cx + cw and cy <= y <= cy + ch:
                self.fold()
                close_ref(self)
                return
            for name, (rx, ry, rw, rh) in zip(sources.CATEGORIES, self.cat_rects()):
                if rx <= x <= rx + rw and ry <= y <= ry + rh:
                    self.set_category(name)
                    return
            i = chip_at(x, y, self.rects()) if y > HEAD_H * self.ui else None
            if i is not None:
                gx, gy = self._gxy(event)
                self.press = (i, gx, gy)

        def mouseReleaseEvent(self, event):
            press, self.press = self.press, None
            if self.drag is not None:
                self._finish_drag(*self._gxy(event))
                return
            if press is None:
                return
            i = chip_at(*self._xy(event), rects=self.rects())
            if i == press[0]:
                self.pick(i)

        def wheelEvent(self, event):
            delta = event.angleDelta().y()
            room = max(0.0, content_height(self.width(), len(self.found), self.ui) - self.height())
            self.scroll = max(0.0, min(room, self.scroll - delta / 120.0 * 40 * self.ui))
            self.update()

        def keyPressEvent(self, event):
            if event.key() == Qt.Key_Escape:
                if self.drag is not None:
                    self._end_drag()
                else:
                    self.fold()
                    close_ref(self)
                return
            super(Drawer, self).keyPressEvent(event)

        # placing ------------------------------------------------------------------
        def pick(self, i):
            """A chip clicked: into the cell the drawer was opened for, else the page shown's
            first free cell (F1 shown: F2's)."""
            item = self.item_of(i)
            if item is None:
                return ""
            target = self.target
            if not target:
                n = self.strip.page()
                target = ("tab", n if look.is_skill_page(n) else 2)
            message = self.strip.place_skill(target, item)
            if self.target:
                self.fold()
                close_ref(self)
            return message

        def _start_drag(self, i):
            self.drag = {"i": i, "ghost": None, "aim": None}
            self.grabMouse()
            try:
                Ghost = maya_hubqt.ghost_class()
                side = int(36 * self.ui)
                pix = QtGui.QPixmap(side, side)
                pix.fill(Qt.transparent)
                painter = QtGui.QPainter(pix)
                painter.setRenderHint(QtGui.QPainter.Antialiasing)
                self.strip.skill_grid._paint_cell(painter, QtCore.QRectF(0, 0, side, side), self.item_of(i),
                                                  0.0, 0.0, 0.0, 1.0, False, False)
                painter.end()
                ghost = Ghost(pix, side, side, self.ui, anchor=(0.5, 0.5), name="skeldarSkillGhost")
                ghost.show()
                self.drag["ghost"] = ghost
            except Exception:                                # noqa: BLE001
                print(traceback.format_exc())

        def _drag_to(self, gx, gy):
            aim = self.strip.skill_aim(gx, gy)
            self.drag["aim"] = aim
            self.strip.light_aim(aim)
            ghost = self.drag.get("ghost")
            if ghost is not None:
                try:
                    label = self.found[self.drag["i"]][2]
                    ghost.set_caption(look.drop_caption(label, aim) if aim else label + " · onto a cell", bool(aim))
                    ghost.follow(QtCore.QPoint(gx, gy))
                except RuntimeError:
                    pass

        def _end_drag(self):
            d, self.drag = self.drag, None
            try:
                self.releaseMouse()
            except RuntimeError:
                pass
            self.strip.light_aim(None)
            ghost = d.get("ghost") if d else None
            if ghost is not None:
                try:
                    ghost.hide()
                    ghost.deleteLater()
                except RuntimeError:
                    pass
            return d

        def _finish_drag(self, gx, gy):
            d = self._end_drag()
            aim = self.strip.skill_aim(gx, gy)
            if d is not None and aim:
                self.strip.place_skill(aim, self.item_of(d["i"]))

        # paint --------------------------------------------------------------------
        def paintEvent(self, _event):
            try:
                self._paint()
            except Exception:                                # noqa: BLE001
                if not getattr(self, "_failed", False):
                    print(traceback.format_exc())
                self._failed = True

        def _paint(self):
            tk, ui, k = self.tokens, self.ui, timebar.kit()
            p = QtGui.QPainter(self)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            whole = QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
            fade = 1.0
            if self.motion and self.folding is not None:
                fade = max(0.0, 1.0 - (self._clock() - self.folding - FOLD_MS * 0.6) / 200.0)
            elif self.motion:
                fade = min(1.0, (self._clock() - self.t0) / 90.0)
            p.setOpacity(fade)
            p.setPen(QtGui.QPen(k.colour("#303237"), 1))
            p.setBrush(k.colour(tk["panel"]))
            p.drawRoundedRect(whole, 8 * ui, 8 * ui)
            # the categories
            f = font(11 * ui)
            p.setFont(f)
            for name, (x, y, w, h) in zip(sources.CATEGORIES, self.cat_rects()):
                rect = QtCore.QRectF(x, y, w, h)
                on = name == self.category
                if on:
                    p.setPen(QtGui.QPen(k.colour(tk["accent"]), 1.5 * ui))
                    p.setBrush(k.colour(tk["card_active"]))
                    p.drawRoundedRect(rect, 5 * ui, 5 * ui)
                p.setPen(k.colour(tk["text"] if on else tk["muted"]))
                p.drawText(rect, Qt.AlignCenter, name)
            x, y, w, h = self.close_rect()
            p.setPen(QtGui.QPen(k.colour(tk["muted"]), 1.6 * ui))
            m = 7 * ui
            p.drawLine(QtCore.QPointF(x + m, y + m), QtCore.QPointF(x + w - m, y + h - m))
            p.drawLine(QtCore.QPointF(x + w - m, y + m), QtCore.QPointF(x + m, y + h - m))
            # the chips
            clip = QtCore.QRectF(0, HEAD_H * ui, self.width(), self.height() - HEAD_H * ui)
            p.setClipRect(clip)
            if not self.found:
                p.setPen(k.colour(tk["faint"]))
                p.setFont(font(12 * ui))
                p.drawText(clip, Qt.AlignCenter, "Nothing here" + (" for '%s'" % self.search.text()
                                                                    if self.search.text() else ""))
            grid = self.strip.skill_grid
            for i, (cx, cy, cw, ch) in enumerate(self.rects()):
                if cy + ch < clip.top() or cy > clip.bottom():
                    continue
                category, item, label = self.found[i]
                scale, opacity = self._entrance(cx + cw / 2.0, cy + ch / 2.0)
                if opacity <= 0.01:
                    continue
                lift = self.lift.get(i, 0.0)
                rect = QtCore.QRectF(cx, cy, cw, ch)
                c = rect.center()
                p.save()
                p.setOpacity(fade * opacity)
                p.translate(c)
                z = scale * (1.0 + 0.08 * lift)
                p.scale(z, z)
                p.translate(-c)
                p.setPen(Qt.NoPen)
                p.setBrush(k.blend(tk["card"], tk["hover"], lift))
                p.drawRoundedRect(rect, 6 * ui, 6 * ui)
                if lift > 0.01:
                    k.glow(p, rect, 6 * ui, tk["accent"], lift, ui)
                side = 34 * ui
                cell = QtCore.QRectF(c.x() - side / 2.0, cy + 4 * ui, side, side)
                grid._paint_cell(p, cell, item, 0.0, 0.0, 0.0, 1.0, False, False)
                p.setFont(font(9 * ui))
                p.setPen(k.colour(tk["text2"]))
                text_rect = QtCore.QRectF(cx + 3 * ui, cy + 4 * ui + side + 1 * ui, cw - 6 * ui, 14 * ui)
                p.drawText(text_rect, Qt.AlignCenter,
                           QtGui.QFontMetrics(font(9 * ui)).elidedText(label, Qt.ElideMiddle, int(text_rect.width())))
                p.restore()
            p.end()

    _CLASSES["drawer"] = Drawer
    return Drawer


def close_ref(window):
    if _state().get("window") is window:
        _state()["window"] = None
