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
(`blend_drag` with the travel, `blend_release`); Esc or the right button cancel either.

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


def _last_line(error_text):
    lines = [line for line in (error_text or "").strip().splitlines() if line.strip()]
    return lines[-1] if lines else "failed"


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
            #  source decodes in about a millisecond, and hundreds of them held whole would
            #  cost ~0.4 MB each for nothing.
            self.pixmaps = {}
            self._clock = QtCore.QElapsedTimer()
            self._clock.start()
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
            #  the details' and the ghost's
            sides = set(rect[2] for rect in self._rects)
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
            self.cards = list(cards)
            self.empty_text = empty_text
            if self._hover is not None and self._hover >= len(self.cards):
                self._hover = None
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
            return look.hit(self._rects, x, y, self.k)

        def card_at(self, x, y):
            index = self.index_at(x, y)
            return self.cards[index] if index is not None else None

        def set_picked(self, path):
            self.picked = path
            self.update()

        # ------------------------------------------------------ the drag

        def _start_drag(self, card, point):
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
                self._drag["ghost"].follow(point)
                self._caption(point)
                return
            if self._mid is not None:
                if buttons & Qt.MiddleButton:
                    if self.panel.blend_drag(self._mid["path"], point.x() - self._mid["x"]) \
                            is None:
                        self._mid = None             # refused: the line says why
                return
            if self._press and buttons & Qt.LeftButton:
                card, (sx, sy) = self._press
                travel = abs(point.x() - sx) + abs(point.y() - sy)
                if travel >= QtWidgets.QApplication.startDragDistance():
                    self._start_drag(card, point)
                return
            local = local_of(event)
            hover = self.index_at(local.x(), local.y())
            if hover != self._hover:
                self._hover = hover
                self.update()

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
            if self._hover is not None and not self._drag:
                self._hover = None
                self.update()

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

        def paintEvent(self, event):                         # noqa: N802
            k = self.k
            area = event.rect()
            p = QtGui.QPainter(self)
            p.fillRect(area, colour("field"))
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
            if not self.cards and self.empty_text:
                p.setFont(font(12 * k))
                p.setPen(colour("muted"))
                p.drawText(self.rect().adjusted(int(16 * k), int(16 * k), -int(16 * k), 0),
                           Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap, self.empty_text)
            radius = 6 * k
            name_font, bold_font, chip_font = font(11.5 * k), font(11.5 * k, True), font(9.5 * k)
            for index in look.visible(self._rects, area.top(), area.bottom() + 1, k):
                card, rect = self.cards[index], self._rects[index]
                chosen = card.path == self.picked
                lit = index == self._hover and not chosen
                box = QtCore.QRectF(*rect)
                shape = QtGui.QPainterPath()
                shape.addRoundedRect(box, radius, radius)
                p.fillPath(shape, colour("card_active" if chosen else ("hover" if lit
                                                                        else "card")))
                picture = self.thumb(card.thumbnail, rect[2])
                p.save()
                p.setClipPath(shape)
                if picture is not None and not picture.isNull():
                    p.drawPixmap(box.toRect(), picture)
                else:
                    self._missing(p, box)
                p.restore()
                if chosen:
                    self._stroke(p, box, radius, "accent", max(1.5, 2 * k))
                elif lit:
                    self._stroke(p, box, radius, "text2", max(1.0, k))
                else:
                    self._stroke(p, box, radius, "line", max(1.0, k))

                nx, ny, nw, nh = look.name_rect(rect, k)
                half = nh // 2
                chosen_font = bold_font if chosen else name_font
                p.setFont(chosen_font)
                p.setPen(colour("text" if chosen else "text2"))
                text = QtGui.QFontMetrics(chosen_font).elidedText(card.name, Qt.ElideRight,
                                                                   int(nw))
                p.drawText(QtCore.QRect(int(nx), int(ny), int(nw), int(half)),
                           Qt.AlignHCenter | Qt.AlignVCenter, text)
                chip = card.label or card.kind
                metrics = QtGui.QFontMetrics(chip_font)
                chip = metrics.elidedText(chip, Qt.ElideRight, int(nw - 10 * k))
                chip_w = min(int(nw), metrics.horizontalAdvance(chip) + int(10 * k))
                pill = QtCore.QRectF(nx + (nw - chip_w) / 2.0, ny + half + k,
                                     chip_w, max(1, nh - half - 3 * k))
                p.setPen(Qt.NoPen)
                p.setBrush(colour("strip"))
                p.drawRoundedRect(pill, pill.height() / 2.0, pill.height() / 2.0)
                p.setFont(chip_font)
                p.setPen(colour("muted"))
                p.drawText(pill, Qt.AlignCenter, chip)
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
