"""The skill bar inside the Time Bar's strip (2026-10-19): the page row (F1 Time, F2-F12) and the
cells of a skill page, painted in the strip's look. Nothing moves and nothing glows (2026-11-19,
«удаляем все подсветки и анимации»): a hover changes a face, the current tab, an armed cell and a
drop target wear a flat accent outline.

`classes()` builds `PageTabs` and `SkillGrid` (no Qt at import). The strip makes one of each; both
read the model through `strip.skills` (skills.MayaSkills in Maya, skills.MemorySkills in the tests)
- never a held Maya widget.
Spec: docs/superpowers/specs/2026-10-19-skill-bar-design.md
"""

import time
import traceback

from . import look, status

NUMBER_KEYS = "1234567890"   # 1-0 run the first row's cells (2026-10-19)
DRAG_PX = 6             # logical px a press must travel before it is a drag

_CLASSES = {}


def classes():
    """(PageTabs, SkillGrid), made once."""
    if _CLASSES:
        return _CLASSES["tabs"], _CLASSES["grid"]
    import maya_hubqt
    from maya_timebar import bar as timebar
    q = maya_hubqt.qt()
    QtCore, QtGui, QtWidgets = q.QtCore, q.QtGui, q.QtWidgets
    Qt = QtCore.Qt
    pictures = {}

    def kit():
        return timebar.kit()

    def font(px, bold=False, mono=False):
        f = QtGui.QFont("Consolas") if mono else QtGui.QFont()
        f.setPixelSize(max(6, int(round(px))))
        f.setBold(bold)
        return f

    def picture_of(kind, value, side, ink):
        """A cell's picture, `side` px square: an icon in `ink`, an image fitted in."""
        key = (kind, value, int(side), ink)
        pix = pictures.get(key)
        if pix is not None:
            return pix
        if kind == "icon":
            try:
                pix = maya_hubqt.pixmap(value, ink, int(side))
            except Exception:                                # noqa: BLE001
                pix = None
        elif kind == "image":
            image = QtGui.QPixmap(value)
            if not image.isNull():
                pix = image.scaled(int(side), int(side), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        if pix is not None:
            pictures[key] = pix
        return pix

    def global_xy(event):
        p = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()
        return p.x(), p.y()

    def local_xy(event):
        p = event.position() if hasattr(event, "position") else event.pos()
        return p.x(), p.y()

    # -- the page row ------------------------------------------------------------------

    class PageTabs(QtWidgets.QWidget):
        """F1 Time, F2 <name> ... F12 along the strip's top: click shows a page, right click
        its menu; a cell dragged onto a tab goes to that page's first free cell."""

        def __init__(self, strip):
            super(PageTabs, self).__init__(strip)
            self.strip = strip
            self.setObjectName("skeldarSkillTabs")
            self.setFixedHeight(int(round((look.TAB_H + 4) * strip.ui)))
            self.setMouseTracking(True)
            self.under = None           # the tab under the mouse
            self.drop_on = None         # a drag over this tab
            #  px kept free at the row's right for the compact AT bar (2026-10-26, maya_atbar)
            self.extra_room = 0
            #  Maya's status-line tools at the row's right (2026-10-20)
            self.tools = StatusTools(self)

        def resizeEvent(self, event):
            super(PageTabs, self).resizeEvent(event)
            self.tools.place()

        def texts(self):
            data = self.strip.skills.data()
            return [look.tab_text(data, n) for n in range(1, look.PAGES + 1)]

        def rects(self):
            ui = self.strip.ui
            texts = self.texts()
            key_font, name_font = font(10 * ui, True, True), font(11 * ui)
            km, nm = QtGui.QFontMetrics(key_font), QtGui.QFontMetrics(name_font)

            def measure(text):
                return (km if text[:1] == "F" and text[1:].isdigit() else nm).horizontalAdvance(text)
            rects = look.tab_rects(texts, measure, ui, x0=2 * ui)
            room = self.width() - self.tools.room() - self.extra_room
            if rects and rects[-1][0] + rects[-1][1] > room:              # no room: keys only
                rects = look.tab_rects([(k, "") for k, _n in texts], measure, ui, x0=2 * ui)
            return rects

        def page_at(self, x):
            return look.tab_at(x, self.rects())

        def mouseMoveEvent(self, event):
            under = self.page_at(local_xy(event)[0])
            if under != self.under:
                self.under = under
                self.update()

        def leaveEvent(self, event):
            if self.under is not None:
                self.under = None
                self.update()
            super(PageTabs, self).leaveEvent(event)

        def mousePressEvent(self, event):
            x = local_xy(event)[0]
            n = self.page_at(x)
            if n is None:
                return
            if event.button() == Qt.RightButton:
                self.strip.page_menu(n, QtCore.QPoint(*global_xy(event)))
                return
            if event.button() == Qt.LeftButton:
                gx, gy = global_xy(event)
                self.strip.show_page(n, (gx, gy))

        def tab_centre(self, n):
            rects = self.rects()
            if not 1 <= n <= len(rects):
                return None
            x, w = rects[n - 1]
            g = self.mapToGlobal(QtCore.QPoint(int(x + w / 2), self.height() // 2))
            return g.x(), g.y()

        def paintEvent(self, _event):
            try:
                self._paint()
            except Exception:                                # noqa: BLE001
                if not getattr(self, "_failed", False):
                    print(traceback.format_exc())
                self._failed = True

        def _paint(self):
            self.tools.place()              # a page renamed moves the tabs' end
            s, tk, ui, k = self.strip, self.strip.tokens, self.strip.ui, kit()
            p = QtGui.QPainter(self)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            current = s.skills.page()
            data = s.skills.data()
            key_font, name_font = font(10 * ui, True, True), font(11 * ui)
            h = look.TAB_H * ui
            top = (self.height() - h) / 2.0
            for n, (x, w) in enumerate(self.rects(), 1):
                rect = QtCore.QRectF(x, top, w, h)
                on = n == current
                lit = on or n == self.drop_on
                hovered = n == self.under
                if lit:
                    face = k.colour(tk["card_active"])
                elif hovered:
                    face = k.colour(tk["hover"])
                else:
                    face = k.colour(tk["hover"], 0)
                p.setPen(QtGui.QPen(k.colour(tk["accent"]), 1.5 * ui) if lit else Qt.NoPen)
                p.setBrush(face)
                p.drawRoundedRect(rect, 5 * ui, 5 * ui)
                key, name = look.tab_text(data, n)
                empty = n != look.TIME_PAGE and look.filled(data, n) == 0
                p.setOpacity(0.55 if empty and not lit and not hovered else 1.0)
                p.setFont(key_font)
                p.setPen(k.colour(tk["accent_text"] if on else tk["muted"]))
                kw = QtGui.QFontMetrics(key_font).horizontalAdvance(key)
                left = x + look.TAB_PAD * ui
                p.drawText(QtCore.QRectF(left, top, kw + 1, h), Qt.AlignVCenter | Qt.AlignLeft, key)
                if name and w > kw + 2 * look.TAB_PAD * ui + 4 * ui:
                    p.setFont(name_font)
                    p.setPen(k.colour(tk["text"] if lit or hovered else tk["faint"]))
                    p.drawText(QtCore.QRectF(left + kw + 5 * ui, top, w, h), Qt.AlignVCenter | Qt.AlignLeft, name)
                p.setOpacity(1.0)
            p.end()

    # -- Maya's status-line tools ------------------------------------------------------

    def status_of(strip):
        """The tools' model: the strip's own when it carries one, Maya's for the real link,
        else in memory (the strip's tests)."""
        given = getattr(strip, "status_model", None)
        if given is not None:
            return given
        if isinstance(getattr(strip, "link", None), timebar.Link):
            from . import statusscene
            return statusscene.MayaStatus()
        return status.MemoryStatus()

    class StatusTools(QtWidgets.QWidget):
        """The selection masks of the current mode, Lock / Highlight, the snaps and Make Live
        at the right of the page row (mockup A): click runs the status line's command, the
        right button a mask's own types or Make Live's add / remove. The state is read again
        every TIMER_MS while shown and after every press; only a change repaints."""

        TIMER_MS = 250

        def __init__(self, tabs):
            super(StatusTools, self).__init__(tabs)
            self.tabs = tabs
            self.strip = tabs.strip
            self.setObjectName("skeldarSkillStatusTools")
            self.setMouseTracking(True)
            self.model = status_of(self.strip)
            self.state = self._read()
            self.under = None           # (group, key) under the mouse
            self.timer = QtCore.QTimer(self)
            self.timer.setInterval(self.TIMER_MS)
            self.timer.timeout.connect(self.poll)
            self.timer.start()

        # the model ---------------------------------------------------------------
        def _read(self):
            try:
                return self.model.read()
            except Exception:                                # noqa: BLE001
                print(traceback.format_exc())
                return status.blank_state()

        def poll(self):
            if not self.isVisible():
                return
            st = self._read()
            if st != self.state:
                mode_changed = st.get("mode") != self.state.get("mode")
                self.state = dict(st, masks=dict(st["masks"]), snaps=dict(st["snaps"]))
                if mode_changed:
                    self.place()
                    self.tabs.update()
                self.update()

        # geometry ----------------------------------------------------------------
        def mode(self):
            return self.state.get("mode", status.OBJECT)

        def room(self):
            """What the tabs must leave free, px: the tools and a gap."""
            ui = self.strip.ui
            return status.width_of(self.mode(), ui) + status.TABS_GAP * ui

        def place(self):
            """Right after the last F tab (2026-10-20: «ближе к F клавишам»), a gap between;
            never past the row's right edge."""
            w = int(round(status.width_of(self.mode(), self.strip.ui)))
            rects = self.tabs.rects()
            x = rects[-1][0] + rects[-1][1] + status.TABS_GAP * self.strip.ui if rects else 0
            x = int(round(min(x, self.tabs.width() - w - self.tabs.extra_room)))
            geo = QtCore.QRect(max(0, x), 0, w, self.tabs.height())
            if self.geometry() != geo:
                self.setGeometry(geo)

        def rects(self):
            return status.layout(self.width(), self.mode(), self.strip.ui)

        def button_at(self, x):
            return status.hit(x, self.rects())

        # the mouse ---------------------------------------------------------------
        def mouseMoveEvent(self, event):
            under = self.button_at(local_xy(event)[0])
            if under != self.under:
                self.under = under
                self.setToolTip(self._tip(under))
                self.update()

        def leaveEvent(self, event):
            if self.under is not None:
                self.under = None
                self.update()
            super(StatusTools, self).leaveEvent(event)

        def _tip(self, button):
            if button is None:
                return ""
            for group, key, label, _icon in status.buttons(self.mode()):
                if (group, key) == button:
                    return label
            return ""

        def mousePressEvent(self, event):
            button = self.button_at(local_xy(event)[0])
            if button is None:
                return
            if event.button() == Qt.RightButton:
                self.context_menu(button, QtCore.QPoint(*global_xy(event)))
                return
            if event.button() == Qt.LeftButton:
                self.press(*button)

        def press(self, group, key):
            try:
                st = self.model.press(group, key)
            except Exception:                                # noqa: BLE001
                print(traceback.format_exc())
                st = self._read()
            self.state = dict(st, masks=dict(st["masks"]), snaps=dict(st["snaps"]))
            self.place()
            self.tabs.update()
            self.update()

        def menu_rows(self, group, key):
            try:
                return self.model.menu(group, key) or []
            except Exception:                                # noqa: BLE001
                print(traceback.format_exc())
                return []

        def context_menu(self, button, point):
            rows = self.menu_rows(*button)
            if not rows:
                return None
            menu = QtWidgets.QMenu(self)
            picks = []
            for label, checked, command in rows:
                action = maya_hubqt.tag_row(menu.addAction(label), len(picks))
                if command and "#1" in command:
                    action.setCheckable(True)
                    action.setChecked(bool(checked))
                picks.append((action, command, checked if command and "#1" in command else None))
            try:
                #  by the row's number, never its wrapper (maya_hubqt.tag_row, 2026-10-28)
                index = maya_hubqt.row_value(self.exec_menu(menu, point))
            finally:
                menu.deleteLater()
            if isinstance(index, int) and 0 <= index < len(picks):
                _action, command, checked = picks[index]
                self.model.run(command, checked)
                self.poll()
                self.update()
                return command
            return None

        def exec_menu(self, menu, point):
            """The menu shown (a seam: the tests answer it)."""
            return menu.exec(point)

        # paint -------------------------------------------------------------------
        def paintEvent(self, _event):
            try:
                self._paint()
            except Exception:                                # noqa: BLE001
                if not getattr(self, "_failed", False):
                    print(traceback.format_exc())
                self._failed = True

        def _icon(self, name, ink, side):
            key = ("status", name, ink, int(side))
            pix = pictures.get(key)
            if pix is None:
                data = QtCore.QByteArray(status.svg(name, ink).encode("utf-8"))
                renderer = q.QtSvg.QSvgRenderer(data)
                pix = QtGui.QPixmap(int(side), int(side))
                pix.fill(Qt.transparent)
                pp = QtGui.QPainter(pix)
                pp.setRenderHint(QtGui.QPainter.Antialiasing)
                renderer.render(pp)
                pp.end()
                pictures[key] = pix
            return pix

        def _paint(self):
            tk, ui, k = self.strip.tokens, self.strip.ui, kit()
            p = QtGui.QPainter(self)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            h = look.TAB_H * ui
            top = (self.height() - h) / 2.0
            rects = self.rects()
            p.setPen(QtGui.QPen(k.colour(tk["line"]), max(1.0, ui)))
            for x in status.dividers(rects):
                p.drawLine(QtCore.QPointF(x, top + 3 * ui), QtCore.QPointF(x, top + h - 3 * ui))
            icons = dict(((g, key), icon) for g, key, _l, icon in status.buttons(self.mode()))
            side = int(round(14 * ui))
            for group, key, x, w in rects:
                button = (group, key)
                rect = QtCore.QRectF(x, top, w, h)
                c = rect.center()
                hovered = button == self.under
                on = status.lit(group, key, self.state)
                part = group == "mask" and self.state["masks"].get(key) == "part"
                full = on and not part
                if full:
                    face = k.colour(tk["card_active"])
                elif hovered:
                    face = k.colour(tk["hover"])
                else:
                    face = k.colour(tk["hover"], 0)
                p.setPen(QtGui.QPen(k.colour(tk["accent"]), 1.5 * ui) if full else Qt.NoPen)
                p.setBrush(face)
                p.drawRoundedRect(rect, 5 * ui, 5 * ui)
                if full:
                    ink = tk["accent_text"]
                elif part or hovered:
                    ink = tk["text"]
                else:
                    ink = tk["faint"]
                pix = self._icon(icons[button], ink, side)
                p.drawPixmap(QtCore.QPointF(c.x() - side / 2.0, c.y() - side / 2.0), pix)
                if part:
                    r = 2.4 * ui
                    p.setPen(Qt.NoPen)
                    p.setBrush(k.colour(tk["accent"]))
                    p.drawEllipse(QtCore.QPointF(rect.right() - 3.5 * ui, rect.bottom() - 3.5 * ui), r, r)
            p.end()

    # -- the cells ---------------------------------------------------------------------

    class SkillGrid(QtWidgets.QWidget):
        """A skill page's cells: click runs, right click a menu, a click on an empty cell the
        library, a drag swaps (onto a tab: that page). Text dropped on it is a script."""

        def __init__(self, strip):
            super(SkillGrid, self).__init__(strip)
            self.strip = strip
            self.setObjectName("skeldarSkillGrid")
            self.setMouseTracking(True)
            self.setAcceptDrops(True)
            self.under = None           # (r, c) under the mouse
            self.armed = None           # {"cell", "t0", "ms"}: a number pressed once, awaiting its second
            self.press = None           # {"cell", "gx", "gy", "button"}
            self.drag = None            # {"from": (n, r, c), "aim": ..., "ghost": ...}
            self.drop_aim = None        # a drag from another panel, lit
            self.disarm = QtCore.QTimer(self)
            self.disarm.setSingleShot(True)
            self.disarm.timeout.connect(self._disarmed)

        # geometry ---------------------------------------------------------------
        def side(self):
            """One row of SLOTS square cells as tall as the time rows (F1 and a skill page alike)."""
            return look.cell_size(self.strip.time_height(), 1, self.strip.ui)

        def rows(self):
            return 1

        def cols(self):
            return look.columns(self.width(), self.side(), self.strip.ui)

        def left(self):
            return look.row_left(self.width(), self.cols(), self.side(), self.strip.ui)

        def wanted_height(self):
            return int(round(look.grid_height(1, self.strip.ui, self.side())))

        def cell_at(self, x, y):
            return look.cell_at(x, y, 1, self.cols(), self.side(), self.strip.ui, self.left())

        def cell_rect(self, r, c):
            return QtCore.QRectF(*look.cell_rect(r, c, self.side(), self.strip.ui, self.left()))

        def cell_centre(self, r, c):
            rc = self.cell_rect(r, c).center()
            g = self.mapToGlobal(QtCore.QPoint(int(rc.x()), int(rc.y())))
            return g.x(), g.y()

        def page(self):
            return self.strip.skills.page()

        def item(self, r, c):
            return look.item_at(self.strip.skills.data(), self.page(), r, c)

        def armed_cell(self, now=None):
            """The cell a first number press lit, while its second is awaited, else None."""
            a = self.armed
            if a is None:
                return None
            now = now_ms() if now is None else now
            return a["cell"] if now - a["t0"] <= a["ms"] else None

        # the mouse --------------------------------------------------------------
        def mouseMoveEvent(self, event):
            x, y = local_xy(event)
            if self.press is not None and self.drag is None:
                gx, gy = global_xy(event)
                if (abs(gx - self.press["gx"]) + abs(gy - self.press["gy"]) > DRAG_PX * self.strip.ui
                        and self.press["button"] == "left" and self.item(*self.press["cell"])):
                    self._start_drag()
            if self.drag is not None:
                self._drag_to(*global_xy(event))
                return
            under = self.cell_at(x, y)
            if under != self.under:
                self.under = under
                item = self.item(*under) if under else None
                self.setToolTip(self.strip.skills.tip(item) if under else "")
                self.update()

        def leaveEvent(self, event):
            if self.drag is None and self.under is not None:
                self.under = None
                self.update()
            super(SkillGrid, self).leaveEvent(event)

        def mousePressEvent(self, event):
            cell = self.cell_at(*local_xy(event))
            gx, gy = global_xy(event)
            if event.button() == Qt.RightButton:
                if self.drag is not None:
                    self._cancel_drag()
                    return
                if cell is not None:
                    self.strip.cell_menu(self.page(), cell[0], cell[1], QtCore.QPoint(gx, gy))
                return
            if event.button() != Qt.LeftButton or cell is None:
                return
            self.press = {"cell": cell, "gx": gx, "gy": gy, "button": "left"}

        def mouseReleaseEvent(self, event):
            press, self.press = self.press, None
            if self.drag is not None:
                self._finish_drag(*global_xy(event))
                return
            if press is None or event.button() != Qt.LeftButton:
                return
            cell = self.cell_at(*local_xy(event))
            if cell != press["cell"]:
                return
            item = self.item(*cell)
            if item:
                self.run_cell(cell)
            else:
                self.strip.skills.open_library(("cell", self.page(), cell[0], cell[1]),
                                               global_xy(event))

        def keyPressEvent(self, event):
            if event.key() == Qt.Key_Escape and self.drag is not None:
                self._cancel_drag()
                return
            super(SkillGrid, self).keyPressEvent(event)

        def arm(self, cell, ms):
            """A number pressed once: its cell drawn armed until the second press or `ms`."""
            self.armed = {"cell": cell, "t0": now_ms(), "ms": float(ms)}
            self.disarm.start(max(1, int(round(float(ms)))))
            self.update()

        def _disarmed(self):
            self.armed = None
            self.update()

        def run_cell(self, cell):
            item = self.item(*cell)
            self.armed = None
            self.disarm.stop()
            if not item:
                self.update()
                return ""
            point = self.cell_centre(*cell)
            try:
                message = self.strip.skills.run(item, point)
            except Exception as error:                       # noqa: BLE001
                print(traceback.format_exc())
                message = "%s: %s" % (self.strip.skills.label(item), error)
            self.strip.skills.say(message)
            self.update()
            return message

        # a cell dragged ---------------------------------------------------------
        def _start_drag(self):
            r, c = self.press["cell"]
            self.drag = {"from": (self.page(), r, c), "aim": None, "ghost": None, "scene": None}
            try:
                self.drag["scene"] = self.strip.skills.scene_drag(self.item(r, c))
            except Exception:                                # noqa: BLE001
                print(traceback.format_exc())
            self.grabMouse()
            self.setFocus()
            try:
                Ghost = maya_hubqt.ghost_class()
                side = int(self.side())
                pix = QtGui.QPixmap(side, side)
                pix.fill(Qt.transparent)
                painter = QtGui.QPainter(pix)
                self._paint_cell(painter, QtCore.QRectF(0, 0, side, side), self.item(r, c))
                painter.end()
                ghost = Ghost(pix, side, side, self.strip.ui, anchor=(0.5, 0.5),
                              name="skeldarSkillGhost", backdrop=None)
                ghost.show()
                self.drag["ghost"] = ghost
            except Exception:                                # noqa: BLE001
                print(traceback.format_exc())

        def aim_at(self, gx, gy):
            """("cell", n, r, c) / ("tab", n) / None for a global point over the bar."""
            return self.strip.skill_aim(gx, gy)

        def _drag_to(self, gx, gy):
            d = self.drag
            aim = self.aim_at(gx, gy)
            d["aim"] = aim
            self.strip.light_aim(aim)
            ghost = d.get("ghost")
            if ghost is not None:
                try:
                    label = self.strip.skills.label(look.item_at(self.strip.skills.data(), *d["from"]))
                    scene = d.get("scene")
                    if aim:
                        ghost.set_caption(look.drop_caption(label, aim), True)
                    elif scene is not None and scene.active():
                        ghost.set_caption(*scene.caption(gx, gy))     # off the bar: into the scene
                    else:
                        ghost.set_caption("%s · off the bar: nothing" % label, False)
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

        def _cancel_drag(self):
            d = self._end_drag()
            scene = d.get("scene") if d else None
            if scene is not None:
                scene.end()
            self.update()

        def _finish_drag(self, gx, gy):
            d = self._end_drag()
            if d is None:
                return
            aim = self.aim_at(gx, gy)
            scene = d.get("scene")
            try:
                if aim:
                    self.strip.move_skill(d["from"], aim)
                elif scene is not None and scene.active():
                    message = scene.drop(gx, gy, say=self.strip.skills.say)
                    self.strip.skills.say(message)
            finally:
                if scene is not None:
                    scene.end()

        # text dropped on the bar -------------------------------------------------
        def dragEnterEvent(self, event):
            if event.mimeData().hasText():
                event.acceptProposedAction()

        def dragMoveEvent(self, event):
            x, y = local_xy(event)
            cell = self.cell_at(x, y)
            self.strip.light_aim(("cell", self.page(), cell[0], cell[1]) if cell else None)
            if cell is not None:
                event.acceptProposedAction()
            else:
                event.ignore()

        def dragLeaveEvent(self, event):
            self.strip.light_aim(None)

        def dropEvent(self, event):
            self.strip.light_aim(None)
            cell = self.cell_at(*local_xy(event))
            item = look.script_item(event.mimeData().text())
            if cell is None or item is None:
                return
            event.acceptProposedAction()
            self.strip.place_skill(("cell", self.page(), cell[0], cell[1]), item)

        # paint ------------------------------------------------------------------
        def paintEvent(self, _event):
            try:
                self._paint()
            except Exception:                                # noqa: BLE001
                if not getattr(self, "_failed", False):
                    print(traceback.format_exc())
                self._failed = True

        def _paint(self):
            s = self.strip
            n = self.page()
            if not look.is_skill_page(n):
                return
            p = QtGui.QPainter(self)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
            data = s.skills.data()
            page = look.page_of(data, n)
            dragged = self.drag["from"] if self.drag else None
            aim = s.lit_aim
            armed = self.armed_cell()
            for r in range(self.rows()):
                for c in range(self.cols()):
                    item = page["cells"].get(look.cell_key(r, c))
                    if dragged == (n, r, c):
                        item = None
                    lit = aim == ("cell", n, r, c) or armed == (r, c)
                    waiting = bool(item) and s.skills.waiting(item)
                    self._paint_cell(p, self.cell_rect(r, c), item, self.under == (r, c), lit, waiting)
                    if r == 0 and c < len(NUMBER_KEYS):
                        self._paint_number(p, self.cell_rect(r, c), NUMBER_KEYS[c], bool(item), waiting)
            p.end()

        def _paint_cell(self, p, rect, item, hovered=False, lit=False, waiting=False):
            tk, ui, k = self.strip.tokens, self.strip.ui, kit()
            p.save()
            radius = 6 * ui
            if waiting:
                face = k.colour(tk["accent"])
            elif item:
                face = k.colour(tk["hover"] if hovered else tk["card"])
            else:
                face = k.colour(tk["field"])
            p.setPen(QtGui.QPen(k.colour(tk["accent"] if lit else tk["track_edge"]), (1.5 if lit else 1) * ui))
            p.setBrush(face)
            p.drawRoundedRect(rect, radius, radius)
            if item:
                self._paint_item(p, rect, item, hovered, waiting)
            elif hovered:
                p.setFont(font(15 * ui))
                p.setPen(k.colour(tk["faint"]))
                p.drawText(rect, Qt.AlignCenter, "+")
            p.restore()

    def _paint_item(self, p, rect, item, hovered, waiting):
        """A skill's face: an icon (or letters) over its short name; a picture filling the cell
        (a portrait, a card's still, a weapon), its name on a dark band - and its tag."""
        s, tk, ui, k = self.strip, self.strip.tokens, self.strip.ui, kit()
        ink = tk["on_accent"] if waiting else (tk["text"] if hovered else tk["text2"])
        pic = s.skills.picture(item) or ("text", "?")
        caption = s.skills.short(item)
        roomy = rect.height() >= 26 * ui and bool(caption)
        inner = rect.adjusted(2 * ui, 2 * ui, -2 * ui, -2 * ui)
        band = 10.5 * ui
        pix = None
        if pic[0] == "image":
            pix = picture_of("image", pic[1], max(4, inner.width()), "")
        if pix is not None:
            clip = QtGui.QPainterPath()
            clip.addRoundedRect(inner, 4 * ui, 4 * ui)
            p.save()
            p.setClipPath(clip)
            p.drawPixmap(QtCore.QPointF(inner.center().x() - pix.width() / 2.0,
                                        inner.center().y() - pix.height() / 2.0), pix)
            if roomy:
                strip_rect = QtCore.QRectF(inner.left(), inner.bottom() - band, inner.width(), band)
                p.fillRect(strip_rect, k.colour("#000000", 150))
                p.setFont(font(8 * ui))
                p.setPen(k.colour(tk["text"]))
                p.drawText(strip_rect.adjusted(2 * ui, 0, -2 * ui, 0), Qt.AlignCenter,
                           QtGui.QFontMetrics(font(8 * ui)).elidedText(caption, Qt.ElideRight,
                                                                     int(strip_rect.width() - 4 * ui)))
            p.restore()
        else:
            body = QtCore.QRectF(rect.left(), rect.top() + 2 * ui, rect.width(),
                                 rect.height() - (band + 2 * ui if roomy else 4 * ui))
            if pic[0] == "icon":
                side = min(body.height(), rect.width()) * (0.66 if roomy else 0.58)
                icon = picture_of("icon", pic[1], max(4, side), ink)
                if icon is not None:
                    p.drawPixmap(QtCore.QPointF(body.center().x() - icon.width() / 2.0,
                                                body.center().y() - icon.height() / 2.0), icon)
            else:
                text = pic[1] if pic[0] == "text" else look.initials(s.skills.label(item))
                p.setFont(font(body.height() * 0.42, True))
                p.setPen(k.colour(ink))
                p.drawText(body, Qt.AlignCenter, text)
            if roomy:
                f = font(8 * ui)
                p.setFont(f)
                p.setPen(k.colour(tk["on_accent"] if waiting else tk["muted"]))
                cap = QtCore.QRectF(rect.left() + 1.5 * ui, rect.bottom() - band - 1.5 * ui,
                                    rect.width() - 3 * ui, band)
                p.drawText(cap, Qt.AlignCenter,
                           QtGui.QFontMetrics(f).elidedText(caption, Qt.ElideRight, int(cap.width())))
        tag = "fin" if waiting else s.skills.tag(item)
        if tag:
            f = font(7.5 * ui, True, True)
            p.setFont(f)
            w = QtGui.QFontMetrics(f).horizontalAdvance(tag) + 5 * ui
            box = QtCore.QRectF(rect.right() - w - 1.5 * ui, rect.top() + 1.5 * ui, w, 10 * ui)
            p.setPen(Qt.NoPen)
            p.setBrush(k.colour(tk["accent"] if waiting else "#121e30", 255 if waiting else 200))
            p.drawRoundedRect(box, 3 * ui, 3 * ui)
            p.setPen(k.colour(tk["on_accent"] if waiting else "#d6e6ff"))
            p.drawText(box, Qt.AlignCenter, tag)

    def _paint_number(self, p, rect, key, filled, waiting):
        """The number key of a first-row cell, small at its top-left (an MMO hotbar's)."""
        tk, ui, k = self.strip.tokens, self.strip.ui, kit()
        p.save()
        p.setOpacity(1.0 if filled else 0.45)
        p.setFont(font(8 * ui, True, True))
        p.setPen(k.colour(tk["on_accent"] if waiting else (tk["accent_text"] if filled else tk["faint"])))
        p.drawText(QtCore.QRectF(rect.left() + 3 * ui, rect.top() + 1 * ui, 10 * ui, 10 * ui),
                   Qt.AlignLeft | Qt.AlignTop, key)
        p.restore()

    SkillGrid._paint_item = _paint_item
    SkillGrid._paint_number = _paint_number
    _CLASSES["tabs"], _CLASSES["grid"] = PageTabs, SkillGrid
    return PageTabs, SkillGrid


def now_ms():
    return time.time() * 1000.0
