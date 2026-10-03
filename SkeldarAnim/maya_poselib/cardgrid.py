"""The Pose Library's card grid (2026-10-02): the painted canvas of thumbnail cards and its
scroll area - split out of `window.py`, which holds everything around it.

The animator: «карточки с позами ... превью которое мы сами делаем из сцены ... перетягивать
наши карточки на персонажа драгом мышки». A library can hold hundreds of cards, so the grid is
ONE painted widget, not a widget per card:

  - `look.grid` lays the cards out for the viewport's width (the card-size slider's cell), and
    a paint draws only the cards `look.visible` finds in the exposed rectangle;
  - each thumbnail is read from the disk once and scaled once per size (smooth, centre-cropped
    square), both cached until the library is read again (`forget`);
  - a card's square holds its thumbnail (the hub's figure glyph when it has none), its strip
    the name and a character chip; the picked card is lit as the hub lights its active card
    (`card_active` and a 2 px `accent` outline), the card under the mouse `hover`.

The mouse, the plugin's grids' habits (`maya_armorgrid`, `maya_chargrid`): a click picks, a
double-click applies, the right button runs the window's `context_actions`; a LEFT drag past
`QApplication.startDragDistance()` carries the hub's ghost - its caption re-read at most every
`look.THROTTLE_MS` - and the release is the window's `drop_at`; a MIDDLE drag is the blend
(`blend_drag` with the travel, `blend_release`); Esc or the right button cancel either, and so
does a release that never arrives (`lost_release`: the next move without the button held - an
Alt+Tab or a modal dialog mid-drag - ends the drag and cancels the blend, said).

**The card under the mouse grows twice its size** (2026-10-03, the animator: «при наведении на
карточку позы ... карточка увеличивалась в двое»): over its neighbours, about its own centre,
moved inside the viewport rather than cut (`look.zoom_rect`), eased in `look.ZOOM_IN_MS` and out
in `look.ZOOM_OUT_MS` (`look.Zoom`, one per card while it is above the grid; at once with ⋮ →
Interface animations off). Lifted, it stands on a plate with a soft drop shadow and its picture
is read at twice the card's side. What you see is what you press: `index_at` asks the grown
card's tile first, so a click, a drag or the right button on the part covering a neighbour acts
on the grown card, and the grown card keeps the hover while the mouse is on it. A 16 ms timer
runs only while a card grows or shrinks, each tick repainting only what the moving cards can
cover (`_reach`). Spec: docs/superpowers/specs/2026-10-03-pose-card-hover-zoom-design.md

What the canvas asks of its `panel` (the window; the tests hand in the real one): `k`, `scene`
(`snapshot_scene`), `scroll`, `thumb_side()`, `pick`, `apply_card`, `context_actions`, `aim`,
`drop_at`, `say`, `blend_drag`, `blend_release`, `blend_cancel`, `blending()`. Qt is imported
when the classes are first built (`maya_hubqt.qt()`).

Spec: docs/superpowers/specs/2026-10-02-pose-library-design.md ("The window")
"""

import traceback

from maya_poselib import look
from maya_poselib import store

CANVAS_NAME = "skeldarPoseCards"
SCROLL_NAME = "skeldarPoseScroll"
GHOST_NAME = "skeldarPoseGhost"
CANCELLED = "cancelled"
# a drag or a blend whose button release never arrived (Alt+Tab, a modal dialog mid-drag): the
# next move with the button no longer held says so, and the window losing focus does too
LOST_DRAG = "the button was let go elsewhere - the drag cancelled"
LOST_BLEND = "the button was let go elsewhere - the blend cancelled, every value back"

ZOOM_TICK_MS = 16       # the grow / shrink frame
SHADOW = 12             # logical px the grown card's shadow reaches (at 1x; it grows with it) ...
SHADOW_DROP = 4         # ... how far down it falls ...
SHADOW_ALPHA = 0.32     # ... and how dark it is at the card's edge
SHADOW_RINGS = 8


def _animations():
    """The hub menu's Interface animations (maya_hubmotion): the zoom eases only with them on.
    A seam the tests replace."""
    try:
        import maya_hubmotion
        return maya_hubmotion.enabled()
    except Exception:                                        # noqa: BLE001
        return True


def _last_line(error_text):
    lines = [line for line in (error_text or "").strip().splitlines() if line.strip()]
    return lines[-1] if lines else "failed"


def zoom_side(side):
    """The picture side a grown card reads: twice the grid's."""
    return int(round(side * look.ZOOM))


_CLASSES = {}


def _classes():
    """The canvas and its scroll area, built on first use (Qt imported here)."""
    if _CLASSES:
        return _CLASSES
    import maya_hubqt
    import maya_hubstyle as hubstyle

    q = maya_hubqt.qt()
    QtCore, QtGui, QtWidgets = q.QtCore, q.QtGui, q.QtWidgets
    Qt = QtCore.Qt
    Ghost = maya_hubqt.ghost_class()          # the hub's own, the inventory's and portraits' too

    def colour(name):
        return QtGui.QColor(hubstyle.TOKENS[name])

    def font(px, bold=False):
        f = QtGui.QFont()
        f.setPixelSize(max(1, int(round(px))))
        f.setBold(bold)
        return f

    def local_of(event):
        return event.position().toPoint() if hasattr(event, "position") else event.pos()

    def global_of(event):
        return (event.globalPosition().toPoint() if hasattr(event, "globalPosition")
                else event.globalPos())

    def scaled(source, side):
        """`source` scaled smooth to fill a `side` square, centre-cropped; None for nothing."""
        if source is None or source.isNull() or side <= 0:
            return None
        big = source.scaled(side, side, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        return big.copy((big.width() - side) // 2, (big.height() - side) // 2, side, side)

    # ---------------------------------------------------------- the cards

    class CardCanvas(QtWidgets.QWidget):
        """The painted card grid. `panel` is the PoseWindow it serves."""

        def __init__(self, panel):
            QtWidgets.QWidget.__init__(self, None)
            self.setObjectName(CANVAS_NAME)
            self.panel = panel
            self.k = panel.k
            self.cards = []
            self.cell = look.CELL_DEFAULT
            self.picked = None
            self.empty_text = ""
            self._rects = []
            self._hover = None
            self._press = None
            self._drag = None
            self._mid = None
            #  (thumbnail path, side) -> the scaled square. Only squares are kept: a 320 px
            #  source decodes in about a millisecond (a 640 px one, since 2026-10-03, holds four
            #  times the pixels), and hundreds of them held whole would
            #  cost ~0.4 MB each for nothing.
            self.pixmaps = {}
            self._clock = QtCore.QElapsedTimer()
            self._clock.start()
            #  card path -> look.Zoom while the card grows, stands grown or shrinks; `_where`
            #  the card's index by path (a re-read keeps the hover and the zooms by path)
            self._zooms = {}
            self._where = {}
            self._fonts = {}
            self._zoom_clock = QtCore.QElapsedTimer()
            self._zoom_clock.start()
            self.zoom_timer = QtCore.QTimer(self)
            self.zoom_timer.setInterval(ZOOM_TICK_MS)
            self.zoom_timer.timeout.connect(self._tick)
            self.setMouseTracking(True)
            self.setFocusPolicy(Qt.ClickFocus)

        # ------------------------------------------------------ layout

        def rects(self):
            return list(self._rects)

        def fit(self, width, least_height=0):
            """The grid laid out for `width` px, the canvas at least `least_height` tall (it
            paints the viewport's background below the last row)."""
            _cols, self._rects, height = look.grid(width, len(self.cards), self.cell, self.k)
            #  the cache holds the sizes in use: the cards' (a pane narrower than a card
            #  shrinks them, so a dragged splitter would otherwise leave a size per pixel),
            #  twice those (the card under the mouse), the details' and the ghost's
            sides = set(rect[2] for rect in self._rects)
            sides.update([zoom_side(side) for side in sides])
            sides.update((self.panel.thumb_side(), int(look.GHOST * self.k)))
            for key in [key for key in self.pixmaps if key[1] not in sides]:
                del self.pixmaps[key]
            self.resize(max(1, int(width)), max(1, height, int(least_height)))
            self.update()

        def _refit(self):
            scroll = self.panel.scroll
            viewport = scroll.viewport() if scroll is not None else None
            if viewport is None:
                self.fit(self.width(), self.height())
            else:
                self.fit(viewport.width(), viewport.height())

        def set_cards(self, cards, empty_text=""):
            """The cards to show. The card under the mouse keeps the hover - and every card its
            zoom - by path; a card no longer listed loses both."""
            hovered = self._hovered_path()
            self.cards = list(cards)
            self._where = dict((one.path, index) for index, one in enumerate(self.cards))
            self.empty_text = empty_text
            self._hover = self._where.get(hovered)
            for path in [path for path in self._zooms if path not in self._where]:
                del self._zooms[path]
            self._refit()

        def set_cell(self, cell):
            """The card-size slider's value (logical px)."""
            self.cell = cell
            self._refit()

        def forget(self, path=None):
            """Drop cached pictures: all, or the card at `path`'s (its thumbnail changed)."""
            if path is None:
                self.pixmaps.clear()
                return
            image = path.rstrip("/") + "/" + store.THUMB_FILE
            for key in [key for key in self.pixmaps if key[0] == image]:
                del self.pixmaps[key]

        def thumb(self, image, side):
            """The thumbnail at `image` as a `side` px square, read and scaled once and cached;
            None when there is none (or it cannot be read)."""
            if not image:
                return None
            key = (image, int(side))
            if key not in self.pixmaps:
                self.pixmaps[key] = scaled(QtGui.QPixmap(image), int(side))
            return self.pixmaps[key]

        def index_at(self, x, y):
            """The card a press at (x, y) acts on: the grown card under the mouse wherever it
            covers its neighbours (what you see is what you press), else the grid's."""
            hover = self._hover
            if hover is not None and hover < len(self._rects):
                zoom = self._zooms.get(self.cards[hover].path)
                if zoom is not None and zoom.lifted(self._now()):
                    (tx, ty, tw, th), _z = self.shown(hover)
                    if tx <= x < tx + tw and ty <= y < ty + th:
                        return hover
            return look.hit(self._rects, x, y, self.k)

        def card_at(self, x, y):
            index = self.index_at(x, y)
            return self.cards[index] if index is not None else None

        def set_picked(self, path):
            self.picked = path
            self.update()

        # ------------------------------------------------------ the zoom

        def _now(self):
            """Milliseconds on the zoom's clock (a seam the tests replace)."""
            return self._zoom_clock.elapsed()

        def _hovered_path(self):
            hover = self._hover
            if hover is None or hover >= len(self.cards):
                return None
            return self.cards[hover].path

        def view(self):
            """(x, y, w, h): the part of the canvas the scroll area's viewport shows - the
            whole canvas without one."""
            scroll = self.panel.scroll
            viewport = scroll.viewport() if scroll is not None else None
            if viewport is None:
                return (0, 0, self.width(), self.height())
            return (-self.x(), -self.y(), viewport.width(), viewport.height())

        def _target(self, index):
            return look.zoom_rect(self._rects[index], self.view(), self.k)

        def shown(self, index, now=None):
            """(tile, z): where the card at `index` is drawn - its square and name strip, and
            how many times larger than its place in the grid (1 at rest)."""
            rect = self._rects[index]
            zoom = self._zooms.get(self.cards[index].path)
            level = zoom.level(self._now() if now is None else now) if zoom else 0.0
            if level <= 0:
                return look.tile_rect(rect, self.k), 1.0
            return look.zoom_at(rect, self._target(index), level, self.k)

        def lifted_order(self, now=None):
            """[(path, zoom)] of the cards above the grid, in drawing order: the ones shrinking
            first, the card under the mouse last - on top."""
            now = self._now() if now is None else now
            hovered = self._hovered_path()
            order = [(path, zoom) for path, zoom in self._zooms.items()
                     if path != hovered and path in self._where and zoom.lifted(now)]
            zoom = self._zooms.get(hovered)
            if zoom is not None and zoom.lifted(now):
                order.append((hovered, zoom))
            return order

        def _reach(self, index):
            """What the card at `index` can cover while it grows and shrinks, its shadow
            included: its own tile and its grown one, padded."""
            ox, oy, ow, oh = look.tile_rect(self._rects[index], self.k)
            (gx, gy, gw, gh), _z = self._target(index)
            x0, y0 = min(ox, gx), min(oy, gy)
            x1, y1 = max(ox + ow, gx + gw), max(oy + oh, gy + gh)
            pad = (SHADOW + SHADOW_DROP) * self.k * look.ZOOM + 2
            return QtCore.QRect(int(x0 - pad), int(y0 - pad), int(x1 - x0 + 2 * pad) + 2,
                                int(y1 - y0 + 2 * pad) + 2)

        def _dirty(self, path):
            index = self._where.get(path)
            if index is not None and index < len(self._rects):
                self.update(self._reach(index))

        def _set_hover(self, index):
            """The card under the mouse is `index` (None for none): the one before shrinks, this
            one grows - eased, or at once with the animations off."""
            if index == self._hover:
                return
            now, animate = self._now(), _animations()
            old, self._hover = self._hover, index
            for one, target in ((old, 0.0), (index, 1.0)):
                if one is None or one >= len(self.cards):
                    continue
                path = self.cards[one].path
                zoom = self._zooms.get(path)
                if zoom is None and target > 0:
                    zoom = self._zooms[path] = look.Zoom()
                if zoom is not None:
                    zoom.to(target, now, animate)
                self._dirty(path)
            self._prune(now)
            if any(zoom.moving(now) for zoom in self._zooms.values()):
                if not self.zoom_timer.isActive():
                    self.zoom_timer.start()

        def _prune(self, now):
            for path in [path for path, zoom in self._zooms.items() if not zoom.lifted(now)]:
                del self._zooms[path]
                self._dirty(path)

        def _tick(self):
            """One frame of the zoom: every lifted card repainted, the settled ones dropped, the
            timer stopped once nothing moves."""
            now = self._now()
            for path in list(self._zooms):
                self._dirty(path)
            self._prune(now)
            if not any(zoom.moving(now) for zoom in self._zooms.values()):
                self.zoom_timer.stop()

        def scrolled(self, _value=None):
            """The scroll moved the cards under a still mouse: the card under it is read again
            (a grown card's place in the viewport changed too)."""
            if not self._drag and self._mid is None and self.underMouse():
                local = self.mapFromGlobal(QtGui.QCursor.pos())
                self._set_hover(self.index_at(local.x(), local.y()))
            self.update()

        # ------------------------------------------------------ the drag

        def _start_drag(self, card, point):
            self._set_hover(None)                    # the ghost takes over from the grown card
            size = int(look.GHOST * self.k)
            picture = self.thumb(card.thumbnail, size) or QtGui.QPixmap()
            ghost = Ghost(picture, size, size, self.k, anchor=(0.5, 0.5), name=GHOST_NAME,
                          backdrop="field")
            snap = None
            if card.kind != "objects":
                try:
                    snap = self.panel.scene.snapshot_scene()
                except Exception:                            # noqa: BLE001
                    traceback.print_exc()
                    snap = []
            self._drag = dict(path=card.path, name=card.name, ghost=ghost, snap=snap)
            self._press = None
            ghost.follow(point)
            ghost.show()
            try:
                self.grabKeyboard()
            except Exception:                                # noqa: BLE001
                pass
            self._caption(point, force=True)

        def _end_drag(self):
            if self._drag:
                ghost = self._drag["ghost"]
                ghost.hide()
                ghost.deleteLater()
            self._drag = None
            self._press = None
            try:
                self.releaseKeyboard()
            except Exception:                                # noqa: BLE001
                pass

        def _caption(self, point, force=False):
            drag = self._drag
            if not drag:
                return
            if not force and self._clock.elapsed() < look.THROTTLE_MS:
                return
            self._clock.restart()
            try:
                aim = self.panel.aim(point.x(), point.y(), drag["path"], drag["snap"])
            except Exception:                                # noqa: BLE001
                aim = {"kind": "none", "text": _last_line(traceback.format_exc())}
            text, good = look.drop_caption(drag["name"], aim)
            drag["ghost"].set_caption(text, good)

        def end_blend(self):
            """The middle drag forgotten (Esc put the values back): its next moves do nothing."""
            self._mid = None

        def lost_release(self):
            """A drag or a middle-drag blend whose button release never reached us (Alt+Tab or
            a modal dialog mid-drag, a release outside Qt): the drag ended - the ghost hidden,
            the keyboard given back - and the blend cancelled, every value back, both said. Left
            standing, the session swallowed every press on the grid, held the keyboard (Maya's
            hotkeys went to the window) and kept its previews unrecorded on the free channels (the
            final review). True when anything was ended."""
            ended = False
            if self._drag:
                self._end_drag()
                self.panel.say(LOST_DRAG)
                ended = True
            if self.panel.blending():
                self._mid = None
                self.panel.blend_cancel()
                self.panel.say(LOST_BLEND)
                ended = True
            self._mid = self._press = None
            return ended

        # ------------------------------------------------------ mouse

        def mousePressEvent(self, event):                    # noqa: N802
            button = event.button()
            if self._drag:
                if button == Qt.RightButton:
                    self._end_drag()
                    self.panel.say(CANCELLED)
                return
            if self._mid is not None:
                if button == Qt.RightButton:
                    self.panel.blend_cancel()
                return
            local = local_of(event)
            card = self.card_at(local.x(), local.y())
            if button == Qt.RightButton:
                self._press = None
                maya_hubqt.run_menu(self, global_of(event),
                                    self.panel.context_actions(card.path if card else None))
                return
            if card is None:
                return
            point = global_of(event)
            if button == Qt.LeftButton:
                self.panel.pick(card.path)
                self._press = (card, (point.x(), point.y()))
            elif button == Qt.MiddleButton:
                self.panel.pick(card.path)
                self._mid = dict(path=card.path, x=point.x())

        def mouseMoveEvent(self, event):                     # noqa: N802
            point = global_of(event)
            buttons = event.buttons()
            if self._drag:
                if not buttons & Qt.LeftButton:      # its release never came: ended, said
                    self.lost_release()
                    return
                self._drag["ghost"].follow(point)
                self._caption(point)
                return
            if self._mid is not None:
                if not buttons & Qt.MiddleButton:    # its release never came: cancelled, said
                    self.lost_release()
                    return
                if self.panel.blend_drag(self._mid["path"], point.x() - self._mid["x"]) is None:
                    self._mid = None                 # refused: the line says why
                return
            if self._press and buttons & Qt.LeftButton:
                card, (sx, sy) = self._press
                travel = abs(point.x() - sx) + abs(point.y() - sy)
                if travel >= QtWidgets.QApplication.startDragDistance():
                    self._start_drag(card, point)
                return
            local = local_of(event)
            self._set_hover(self.index_at(local.x(), local.y()))

        def mouseReleaseEvent(self, event):                  # noqa: N802
            button = event.button()
            if self._drag and button == Qt.LeftButton:
                point = global_of(event)
                drag = self._drag
                try:
                    self.panel.drop_at(point.x(), point.y(), drag["path"], drag["snap"])
                finally:
                    self._end_drag()
                return
            if self._mid is not None and button == Qt.MiddleButton:
                self._mid = None
                self.panel.blend_release()
                return
            self._press = None

        def mouseDoubleClickEvent(self, event):              # noqa: N802
            if event.button() != Qt.LeftButton:
                return
            local = local_of(event)
            card = self.card_at(local.x(), local.y())
            if card is not None:
                self._press = None
                self.panel.apply_card(card.path)

        def keyPressEvent(self, event):                      # noqa: N802
            if event.key() == Qt.Key_Escape:
                if self._drag:
                    self._end_drag()
                    self.panel.say(CANCELLED)
                    return
                if self._mid is not None or self.panel.blending():
                    self.panel.blend_cancel()
                    return
            QtWidgets.QWidget.keyPressEvent(self, event)

        def leaveEvent(self, _event):                        # noqa: N802
            if not self._drag:
                self._set_hover(None)

        # ------------------------------------------------------ paint

        def _stroke(self, p, box, radius, name, width):
            p.setPen(QtGui.QPen(colour(name), width))
            p.setBrush(Qt.NoBrush)
            half = width / 2.0
            p.drawRoundedRect(box.adjusted(half, half, -half, -half), radius, radius)

        def _missing(self, p, box):
            """No thumbnail: the hub's figure glyph, faint, centred."""
            side = max(8, int(box.width() * 0.4))
            try:
                glyph = maya_hubqt.pixmap("run", hubstyle.TOKENS["faint"], side)
            except Exception:                                # noqa: BLE001
                return
            p.drawPixmap(int(box.center().x() - side / 2.0),
                         int(box.center().y() - side / 2.0), glyph)

        def _font(self, px, bold=False):
            key = (int(round(px)), bool(bold))
            if key not in self._fonts:
                self._fonts[key] = font(key[0], bold)
            return self._fonts[key]

        def _shadow(self, p, tile, radius, z, strength):
            """A soft drop shadow round the lifted card's `tile` (QRectF): rings of fading black
            reaching SHADOW, fallen SHADOW_DROP, both at the card's `z`, faded in by
            `strength` (its zoom level)."""
            reach = SHADOW * self.k * z
            drop = SHADOW_DROP * self.k * z
            step = reach / SHADOW_RINGS
            p.setBrush(Qt.NoBrush)
            for ring in range(SHADOW_RINGS):
                grow = (ring + 0.5) * step
                alpha = SHADOW_ALPHA * strength * (1.0 - float(ring) / SHADOW_RINGS) ** 2
                p.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, int(round(255 * alpha))), step))
                p.drawRoundedRect(tile.adjusted(-grow, drop - grow, grow, drop + grow),
                                  radius + grow, radius + grow)

        def _paint_card(self, p, card, rect, tile, z, chosen, lit, lifted=0.0):
            """The card whose grid square is `rect` drawn at `tile` (x, y, w, h: its square and
            name strip), `z` times its size in the grid - every length grows with it. A
            `lifted` card (its zoom level) stands on a plate of the canvas's own colour with a
            shadow, over its neighbours, its picture read at twice the grid's side."""
            k = self.k
            tx, ty, tw, th = tile
            box = QtCore.QRectF(tx, ty, tw, tw)
            radius = 6 * k * z
            if lifted > 0:
                whole = QtCore.QRectF(tx, ty, tw, th)
                self._shadow(p, whole, radius, z, lifted)
                plate = QtGui.QPainterPath()
                plate.addRoundedRect(whole, radius, radius)
                p.fillPath(plate, colour("field"))
            shape = QtGui.QPainterPath()
            shape.addRoundedRect(box, radius, radius)
            p.fillPath(shape, colour("card_active" if chosen else ("hover" if lit else "card")))
            picture = self.thumb(card.thumbnail, zoom_side(rect[2]) if lifted > 0 else rect[2])
            p.save()
            p.setClipPath(shape)
            if picture is not None and not picture.isNull():
                p.drawPixmap(box, picture, QtCore.QRectF(picture.rect()))
            else:
                self._missing(p, box)
            p.restore()
            if chosen:
                self._stroke(p, box, radius, "accent", max(1.5, 2 * k) * z)
            elif lit:
                self._stroke(p, box, radius, "text2", max(1.0, k) * z)
            else:
                self._stroke(p, box, radius, "line", max(1.0, k) * z)

            nx, ny, nw, nh = tx, ty + tw, tw, th - tw
            half = float(int(nh // 2))
            name_font = self._font(11.5 * k * z, chosen)
            chip_font = self._font(9.5 * k * z)
            p.setFont(name_font)
            p.setPen(colour("text" if chosen else "text2"))
            text = QtGui.QFontMetrics(name_font).elidedText(card.name, Qt.ElideRight, int(nw))
            p.drawText(QtCore.QRectF(nx, ny, nw, half), Qt.AlignHCenter | Qt.AlignVCenter, text)
            chip = card.label or card.kind
            metrics = QtGui.QFontMetrics(chip_font)
            chip = metrics.elidedText(chip, Qt.ElideRight, int(nw - 10 * k * z))
            chip_w = min(float(nw), metrics.horizontalAdvance(chip) + int(10 * k * z))
            pill = QtCore.QRectF(nx + (nw - chip_w) / 2.0, ny + half + k * z,
                                 chip_w, max(1.0, nh - half - 3 * k * z))
            p.setPen(Qt.NoPen)
            p.setBrush(colour("strip"))
            p.drawRoundedRect(pill, pill.height() / 2.0, pill.height() / 2.0)
            p.setFont(chip_font)
            p.setPen(colour("muted"))
            p.drawText(pill, Qt.AlignCenter, chip)

        def paintEvent(self, event):                         # noqa: N802
            k = self.k
            area = event.rect()
            now = self._now()
            p = QtGui.QPainter(self)
            p.fillRect(area, colour("field"))
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
            if not self.cards and self.empty_text:
                p.setFont(font(12 * k))
                p.setPen(colour("muted"))
                p.drawText(self.rect().adjusted(int(16 * k), int(16 * k), -int(16 * k), 0),
                           Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap, self.empty_text)
            lifted = [(path, zoom, zoom.level(now)) for path, zoom in self.lifted_order(now)]
            above = set(path for path, _zoom, level in lifted if level > 0)
            for index in look.visible(self._rects, area.top(), area.bottom() + 1, k):
                card, rect = self.cards[index], self._rects[index]
                if card.path in above:
                    continue                         # drawn over the grid below
                chosen = card.path == self.picked
                lit = index == self._hover and not chosen
                self._paint_card(p, card, rect, look.tile_rect(rect, k), 1.0, chosen, lit)
            for path, _zoom, level in lifted:
                index = self._where.get(path)
                if level <= 0 or index is None or index >= len(self._rects):
                    continue
                if not area.intersects(self._reach(index)):
                    continue
                card, rect = self.cards[index], self._rects[index]
                tile, z = self.shown(index, now)
                chosen = card.path == self.picked
                lit = index == self._hover and not chosen
                self._paint_card(p, card, rect, tile, z, chosen, lit, lifted=level)
            p.end()

    class CardScroll(QtWidgets.QScrollArea):
        """The grid's scroll area: the canvas follows the viewport's width."""

        def __init__(self, canvas):
            QtWidgets.QScrollArea.__init__(self)
            self.setObjectName(SCROLL_NAME)
            self.setWidgetResizable(False)
            self.setFrameShape(QtWidgets.QFrame.NoFrame)
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            #  always on: a bar appearing would narrow the viewport, which re-lays the grid,
            #  which can take the bar away again - a styled empty track costs nothing
            self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
            self.setWidget(canvas)
            self.canvas = canvas
            self.verticalScrollBar().valueChanged.connect(canvas.scrolled)

        def resizeEvent(self, event):                        # noqa: N802
            QtWidgets.QScrollArea.resizeEvent(self, event)
            self.canvas.fit(self.viewport().width(), self.viewport().height())

    _CLASSES.update(CardCanvas=CardCanvas, CardScroll=CardScroll, scaled=scaled, qt=q)
    return _CLASSES


def make_canvas(panel):
    """The card canvas serving `panel` (the window)."""
    return _classes()["CardCanvas"](panel)


def make_scroll(canvas):
    """The scroll area holding `canvas`, which follows its viewport's width."""
    return _classes()["CardScroll"](canvas)


def scaled(source, side):
    """A QPixmap scaled smooth to fill a `side` px square, centre-cropped (None for nothing)."""
    return _classes()["scaled"](source, side)
