"""The skill bar inside the Time Bar's strip (2026-10-19): the page row (F1 Time, F2-F12) and the
cells of a skill page, painted in the strip's look and moving as its controls move.

`classes(Strip kit, q)` builds `PageTabs` and `SkillGrid` (no Qt at import). The strip makes one of
each and registers them as moving parts; both read the model through `strip.skills`
(skills.MayaSkills in Maya, skills.MemorySkills in the tests) - never a held Maya widget.
Spec: docs/superpowers/specs/2026-10-19-skill-bar-design.md
"""

import time
import traceback

from . import look

HOVER_MS = 110
FLASH_MS = 120
RUN_MS = 520            # a skill run: the key set's round glow
POP_MS = 240            # a page shown: a cell pops in
LIFT = 0.10
RUN_GLOW = 40
NUMBER_KEYS = "1234567890"   # 1-0 run the first row's cells (2026-10-19)           # logical px: the run's glow
DRAG_PX = 6             # logical px a press must travel before it is a drag

_CLASSES = {}


def classes():
    """(PageTabs, SkillGrid), made once."""
    if _CLASSES:
        return _CLASSES["tabs"], _CLASSES["grid"]
    import maya_hubqt
    from maya_timebar import bar as timebar, look as tlook
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
            self.hover = {}             # page -> 0..1
            self.under = None
            self.flash_at = {}
            self.drop_on = None         # a drag over this tab
            self._was_busy = False
            self.index = strip.register(self)

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
            if rects and rects[-1][0] + rects[-1][1] > self.width():      # no room: keys only
                rects = look.tab_rects([(k, "") for k, _n in texts], measure, ui, x0=2 * ui)
            return rects

        def page_at(self, x):
            return look.tab_at(x, self.rects())

        def busy(self, now):
            moving = any(abs(v - (1.0 if p == self.under else 0.0)) > 0.005 for p, v in self.hover.items())
            moving = moving or (self.under is not None and self.hover.get(self.under, 0.0) < 0.995)
            return moving or any(now - t < FLASH_MS for t in self.flash_at.values())

        def step(self, dt):
            for p in set(list(self.hover) + ([self.under] if self.under else [])):
                goal = 1.0 if p == self.under else 0.0
                cur = self.hover.get(p, 0.0)
                self.hover[p] = tlook.approach(cur, goal, dt, HOVER_MS) if self.strip.motion else goal

        def mouseMoveEvent(self, event):
            under = self.page_at(local_xy(event)[0])
            if under != self.under:
                self.under = under
                self.strip.kick()

        def leaveEvent(self, event):
            self.under = None
            self.strip.kick()
            super(PageTabs, self).leaveEvent(event)

        def mousePressEvent(self, event):
            x = local_xy(event)[0]
            n = self.page_at(x)
            if n is None:
                return
            self.flash_at[n] = self.strip.clock()
            self.strip.kick()
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
            s, tk, ui, k = self.strip, self.strip.tokens, self.strip.ui, kit()
            scale, opacity = s.opening_of(self.index)
            p = QtGui.QPainter(self)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            p.setOpacity(opacity)
            now = s.clock()
            current = s.skills.page()
            data = s.skills.data()
            key_font, name_font = font(10 * ui, True, True), font(11 * ui)
            h = look.TAB_H * ui
            top = (self.height() - h) / 2.0
            for n, (x, w) in enumerate(self.rects(), 1):
                rect = QtCore.QRectF(x, top, w, h)
                c = rect.center()
                lift = self.hover.get(n, 0.0)
                flash = 0.0
                t = self.flash_at.get(n)
                if t is not None and s.motion and now - t < FLASH_MS:
                    flash = 1.0 - (now - t) / float(FLASH_MS)
                z = scale * (1.0 + LIFT * 0.5 * lift) * (1.0 - 0.06 * flash)
                p.save()
                p.translate(c)
                p.scale(z, z)
                p.translate(-c)
                on = n == current
                lit = on or n == self.drop_on
                if lit:
                    face = k.colour(tk["card_active"])
                else:
                    face = k.colour(tk["hover"], 255 * lift)
                if flash > 0:
                    face = k.blend(face.name(), tk["accent"], flash)
                p.setPen(QtGui.QPen(k.colour(tk["accent"]), 1.5 * ui) if lit else Qt.NoPen)
                p.setBrush(face)
                p.drawRoundedRect(rect, 5 * ui, 5 * ui)
                if lift > 0.01 and not lit:
                    k.glow(p, rect, 5 * ui, tk["accent"], lift * 0.6, ui)
                key, name = look.tab_text(data, n)
                empty = n != look.TIME_PAGE and look.filled(data, n) == 0
                p.setOpacity(opacity * (0.55 if empty and not lit else 1.0))
                p.setFont(key_font)
                p.setPen(k.colour(tk["accent_text"] if on else tk["muted"]))
                kw = QtGui.QFontMetrics(key_font).horizontalAdvance(key)
                left = x + look.TAB_PAD * ui
                p.drawText(QtCore.QRectF(left, top, kw + 1, h), Qt.AlignVCenter | Qt.AlignLeft, key)
                if name and w > kw + 2 * look.TAB_PAD * ui + 4 * ui:
                    p.setFont(name_font)
                    p.setPen(k.colour(tk["text"] if lit else tk["faint"]) if not lift
                             else k.blend(tk["faint"], tk["text"], max(lift, 1.0 if lit else 0.0)))
                    p.drawText(QtCore.QRectF(left + kw + 5 * ui, top, w, h), Qt.AlignVCenter | Qt.AlignLeft, name)
                p.setOpacity(opacity)
                p.restore()
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
            self.hover = {}             # (r, c) -> 0..1
            self.under = None
            self.flash_at = {}
            self.run_at = {}            # (r, c) -> the run's start
            self.armed = None           # {"cell", "t0", "ms"}: a number pressed once, awaiting its second
            self.pop = None             # {"t0", "gx", "gy"}: the page just shown pops in
            self.press = None           # {"cell", "gx", "gy", "button"}
            self.drag = None            # {"from": (n, r, c), "aim": ..., "ghost": ...}
            self.drop_aim = None        # a drag from another panel, lit
            self._was_busy = False
            self.index = strip.register(self)

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

        # motion -----------------------------------------------------------------
        def pop_from(self, gx, gy):
            if self.strip.motion:
                self.pop = {"t0": self.strip.clock(), "gx": gx, "gy": gy}
                self.strip.kick()
            else:
                self.pop = None

        def entrance(self, r, c):
            """(scale, opacity) of a cell: the strip's burst, else the page's own pop."""
            s = self.strip
            if not s.motion:
                return 1.0, 1.0
            if s.entrance is not None:
                return s.entrance_of(*self.cell_centre(r, c))
            if self.pop is not None:
                gx, gy = self.cell_centre(r, c)
                age = s.clock() - self.pop["t0"]
                return tlook.popping(age, tlook.burst_delay(gx - self.pop["gx"], gy - self.pop["gy"], s.ui),
                                     POP_MS)
            return 1.0, 1.0

        def busy(self, now):
            if self.pop is not None:
                far = POP_MS + tlook.burst_delay(self.width(), self.height(), self.strip.ui) + 40
                if now - self.pop["t0"] > far:
                    self.pop = None
                else:
                    return True
            for cell, v in self.hover.items():
                if abs(v - (1.0 if cell == self.under else 0.0)) > 0.005:
                    return True
            if self.under is not None and self.hover.get(self.under, 0.0) < 0.995:
                return True
            if self.armed is not None:
                if now - self.armed["t0"] > self.armed["ms"]:
                    self.armed = None
                    self.update()
                else:
                    return True
            return (any(now - t < FLASH_MS for t in self.flash_at.values())
                    or any(now - t < RUN_MS for t in self.run_at.values()))

        def step(self, dt):
            for cell in set(list(self.hover) + ([self.under] if self.under else [])):
                goal = 1.0 if cell == self.under else 0.0
                cur = self.hover.get(cell, 0.0)
                self.hover[cell] = tlook.approach(cur, goal, dt, HOVER_MS) if self.strip.motion else goal

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
                self.strip.kick()

        def leaveEvent(self, event):
            if self.drag is None:
                self.under = None
                self.strip.kick()
            super(SkillGrid, self).leaveEvent(event)

        def mousePressEvent(self, event):
            cell = self.cell_at(*local_xy(event))
            gx, gy = global_xy(event)
            if event.button() == Qt.RightButton:
                if self.drag is not None:
                    self._cancel_drag()
                    return
                if cell is not None:
                    self.flash_at[cell] = self.strip.clock()
                    self.strip.kick()
                    self.strip.cell_menu(self.page(), cell[0], cell[1], QtCore.QPoint(gx, gy))
                return
            if event.button() != Qt.LeftButton or cell is None:
                return
            self.flash_at[cell] = self.strip.clock()
            self.press = {"cell": cell, "gx": gx, "gy": gy, "button": "left"}
            self.strip.kick()

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
            """A number pressed once: its cell lit (and flashed) until the second press or `ms`."""
            self.armed = {"cell": cell, "t0": self.strip.clock(), "ms": float(ms)}
            self.flash_at[cell] = self.strip.clock()
            self.strip.kick()
            self.update()

        def run_cell(self, cell):
            item = self.item(*cell)
            self.armed = None
            if not item:
                return ""
            self.run_at[cell] = self.strip.clock()
            self.strip.kick()
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
                self._paint_cell(painter, QtCore.QRectF(0, 0, side, side), self.item(r, c), 0.0, 0.0, 0.0,
                                 1.0, False, False)
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
            self.strip.kick()

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
            now = s.clock()
            data = s.skills.data()
            page = look.page_of(data, n)
            dragged = self.drag["from"] if self.drag else None
            aim = s.lit_aim
            for r in range(self.rows()):
                for c in range(self.cols()):
                    item = page["cells"].get(look.cell_key(r, c))
                    if dragged == (n, r, c):
                        item = None
                    scale, opacity = self.entrance(r, c)
                    lift = self.hover.get((r, c), 0.0) if item else self.hover.get((r, c), 0.0) * 0.5
                    flash = 0.0
                    t = self.flash_at.get((r, c))
                    if t is not None and s.motion and now - t < FLASH_MS:
                        flash = 1.0 - (now - t) / float(FLASH_MS)
                    lit = aim == ("cell", n, r, c) or bool(
                        self.armed is not None and self.armed["cell"] == (r, c)
                        and now - self.armed["t0"] <= self.armed["ms"])
                    waiting = bool(item) and s.skills.waiting(item)
                    self._paint_cell(p, self.cell_rect(r, c), item, lift, flash, scale - 1.0, opacity,
                                     lit, waiting)
                    if r == 0 and c < len(NUMBER_KEYS) and opacity > 0.01:
                        self._paint_number(p, self.cell_rect(r, c), NUMBER_KEYS[c], opacity * scale,
                                           bool(item), waiting)
            for (r, c), t in list(self.run_at.items()):
                age = now - t
                if age >= RUN_MS or not s.motion:
                    self.run_at.pop((r, c), None)
                    continue
                u = age / float(RUN_MS)
                rc = self.cell_rect(r, c).center()
                p.setCompositionMode(QtGui.QPainter.CompositionMode_Plus)
                kit().soft_dot(p, rc.x(), rc.y(), RUN_GLOW * s.ui * (0.6 + 0.4 * u), s.tokens["accent"],
                               200 * (1 - u) ** 1.5)
                kit().soft_dot(p, rc.x(), rc.y(), 9 * s.ui, tlook.RIM, 220 * (1 - u) ** 2)
                p.setCompositionMode(QtGui.QPainter.CompositionMode_SourceOver)
            p.end()

        def _paint_cell(self, p, rect, item, lift, flash, grow, opacity, lit, waiting):
            s, tk, ui, k = self.strip, self.strip.tokens, self.strip.ui, kit()
            if opacity <= 0.01:
                return
            z = (1.0 + grow) * (1.0 + LIFT * lift) * (1.0 - 0.06 * flash)
            c = rect.center()
            p.save()
            p.setOpacity(opacity)
            p.translate(c)
            p.scale(z, z)
            p.translate(-c)
            radius = 6 * ui
            if waiting:
                face = k.colour(tk["accent"])
            elif item:
                face = k.blend(tk["card"], tk["hover"], lift)
            else:
                face = k.colour(tk["field"])
            if flash > 0:
                face = k.blend(face.name(), tk["accent"], flash)
            p.setPen(QtGui.QPen(k.colour(tk["accent"] if lit else tk["track_edge"]), (1.5 if lit else 1) * ui))
            p.setBrush(face)
            p.drawRoundedRect(rect, radius, radius)
            if lift > 0.01 and item:
                k.glow(p, rect, radius, tk["accent"], lift, ui)
            if lit:
                k.glow(p, rect, radius, tk["accent"], 1.0, ui)
            if item:
                self._paint_item(p, rect, item, lift, waiting)
            elif lift > 0.01:
                p.setFont(font(15 * ui))
                p.setPen(k.colour(tk["faint"], 255 * lift))
                p.drawText(rect, Qt.AlignCenter, "+")
            p.restore()

    def _paint_item(self, p, rect, item, lift, waiting):
        """A skill's face: an icon (or letters) over its short name; a picture filling the cell
        (a portrait, a card's still, a weapon), its name on a dark band - and its tag."""
        s, tk, ui, k = self.strip, self.strip.tokens, self.strip.ui, kit()
        ink = tk["on_accent"] if waiting else (tk["text"] if lift > 0.5 else tk["text2"])
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

    def _paint_number(self, p, rect, key, opacity, filled, waiting):
        """The number key of a first-row cell, small at its top-left (an MMO hotbar's)."""
        s, tk, ui, k = self.strip, self.strip.tokens, self.strip.ui, kit()
        p.save()
        p.setOpacity(max(0.0, min(1.0, opacity)) * (1.0 if filled else 0.45))
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
