"""The Time Bar's layer panel (2026-10-18): a painted column of animation and display
layers on the bar's right, resizable by its top edge, and lanes of each layer's keys
over the timeline. Two frameless Qt.Tool windows of ours; all painting is ours.

The animator: «передвинем меню слоев в правую часть таймлайна» and «опциональную кнопку
которая будет выдвигать панель как в варианте B». The column opens out of the bar's
layers pill and folds back into it; the lanes come out of the column's left edge.
The data is the link's at once; only the picture moves (docs/interface-motion.md).

Spec: docs/superpowers/specs/2026-10-18-time-bar-layer-panel-design.md
"""

import math
import sys
import time
import traceback

import maya_hubqt

from . import bar, layerlook as L, look

COLUMN = "skeldarTimeBarLayers"
LANES = "skeldarTimeBarLayerLanes"
HEIGHT_VAR = "skeldarTimeBarLayersHeight"
TAB_VAR = "skeldarTimeBarLayersTab"
LANES_VAR = "skeldarTimeBarLayerLanes"
PLACE_MS = 300
STATUS_MS = 4000
DIM = 0.42              # a muted or soloed-out layer, and its lane
KEY_LIFT = 1.6          # the key under the mouse grows, as on the timeline
LANE_FACE = "#141517"
MUTE_FACE = "#3a2626"   # M lit
SOLO_FACE = "#23324a"   # S lit
BOX = (28, 20)          # logical px: the shape a burst unrolls from
TOGGLES = ("mute", "solo", "lock", "visible", "playback", "type", "wkey")
FOOT_GLYPHS = {"add": "plus", "addsel": "addsel", "remsel": "remsel", "merge": "merge",
               "select": "select", "delete": "trash"}
#  Maya's display layer palette: the colour index a layer takes (1..31)
COLOUR_INDICES = tuple(range(1, 32))


def live_panels():
    """The panels standing, kept on sys (trap 111): an older module's too."""
    return sys.__dict__.setdefault("_skeldar_timebar_layer_panels", [])


def destroy_all():
    """Every panel ended (a weight drag's chunk closed), then every column and lanes
    window by name - an older module's too (trap 102). A rebuild mid-drag must not
    leave Maya's undo chunk open (2026-10-18 final review): the chunk is closed in
    any case, a no-op when none is open."""
    for panel in list(live_panels()):
        try:
            panel.destroy()
        except Exception:                                    # noqa: BLE001
            print(traceback.format_exc())
    del live_panels()[:]
    try:
        from . import layerscene
        layerscene.end_weight()
    except Exception:                                        # noqa: BLE001 - no Maya here
        pass
    q = maya_hubqt.qt()
    if q is None:
        return
    for w in q.QtWidgets.QApplication.topLevelWidgets():
        try:
            if w.objectName() in (COLUMN, LANES):
                w.hide()
                w.deleteLater()
        except RuntimeError:
            pass


def _clock():
    return time.time() * 1000.0


def _unit_of(uid):
    """The drawn unit a hover / pop id belongs to: a row's control is its row."""
    return ("row", uid[1]) if uid[0] == "ctl" else uid


class Panel(object):
    """The controller: opens, places, reads, writes, drives both windows."""

    def __init__(self, strip, link, ui, tokens, motion, parent=None):
        q = maya_hubqt.qt()
        self.q = q
        self.strip, self.link, self.ui = strip, link, float(ui)
        self.tokens, self.motion = tokens, bool(motion)
        self._remembered()
        self.rows = {"anim": [], "disp": []}
        self.picked_disp = None
        self.scroll = 0.0
        self.anchor = None             # a Shift-click's range starts here
        self.chosen = None             # the layers the last Ctrl / Shift click selected
        self.lane_sel = None           # the lanes' highlight: {"a", "b", "names"}
        self.lane_drag = None          # a press held on the lanes
        self.lane_preview = None       # the highlight where a key drag has it now
        self.lane_live = None          # a key drag moving the scene's keys (scene.live_*)
        self.lane_stamped = None       # what S put down during the drag
        self.lane_aimed = None         # (layer, key) under the mouse
        self.keys = {}
        self._keys_stale = False        # a key edit: the lanes read on the next refresh
        self._wstates = ()              # the weight key cells the column last drew
        self.phase = "closed"
        self.age_override = None        # tests only: the age of a running burst, ms
        self.burst = None               # the column's: {"t0", "open", "origin", "delays", "close_at", "ends"}
        self.lanes_burst = None         # the lanes': the same shape
        self.wave = None                # a tab switch: {"t0", "delays": {i: ms}}
        self.ghosts = []                # deleted rows folding where they stood
        self.hover, self.goal = {}, {}
        self.pops, self.flashes = {}, {}
        self.drag = None                # ("weight", name, rect) or ("grip", gy0, h0)
        self.status, self._origin = "", None
        self._sigs = (None, None)
        self._last_step = None
        self._was_busy = False
        self._editor = None
        column_class, lanes_class = _classes()[:2]
        self.column = column_class(self, parent)
        self.lanes = lanes_class(self, parent)
        self.driver = q.QtCore.QTimer(self.column)
        self.driver.setInterval(bar.FRAME_MS)
        self.driver.timeout.connect(self._animate)
        self.placer = q.QtCore.QTimer(self.column)
        self.placer.setInterval(PLACE_MS)
        self.placer.timeout.connect(self.place)
        self.status_timer = q.QtCore.QTimer(self.column)
        self.status_timer.setSingleShot(True)
        self.status_timer.setInterval(STATUS_MS)
        self.status_timer.timeout.connect(self._clear_status)
        #  a lanes key drag's scene step: the lanes painted first, then one step to the
        #  newest target on the next event-loop turn (the timeline's live_timer, 2026-10-20)
        self.lane_timer = q.QtCore.QTimer(self.column)
        self.lane_timer.setSingleShot(True)
        self.lane_timer.setInterval(0)
        self.lane_timer.timeout.connect(self._flush_lane_live)
        live_panels().append(self)

    # -- the link ----------------------------------------------------------------
    def _option(self, name, default):
        try:
            value = self.link.option(name, default)
        except Exception:                                    # noqa: BLE001
            return default
        return default if value is None else value

    def _set_option(self, name, value):
        try:
            self.link.set_option(name, value)
        except Exception:                                    # noqa: BLE001
            print(traceback.format_exc())

    def _call(self, name, *args):
        """A link call; a failure goes to the Script Editor, never out of a Qt slot."""
        try:
            return getattr(self.link, name)(*args)
        except Exception:                                    # noqa: BLE001
            print(traceback.format_exc())
            return None

    def _write(self, name, *args):
        """A write: its message on the column's line, the scene read again, the strip
        told (its chip shows the active layer)."""
        answer = self._call(name, *args)
        self._after_write(answer)
        return answer

    def _after_write(self, answer):
        """The tail of every write: the link's message said, the scene read again,
        the strip told."""
        if isinstance(answer, (tuple, list)) and len(answer) > 1 and answer[1]:
            self.say(answer[1])
        refresh = getattr(self.strip, "refresh", None)
        if refresh is not None and getattr(self.strip, "layer_panel", None) is self and self.is_open():
            try:
                refresh(keys=True, force=True)               # it reads this panel too, once
                return
            except Exception:                                # noqa: BLE001
                print(traceback.format_exc())
        self.refresh(force=True, keys=True)
        if refresh is not None:
            try:
                refresh(keys=True)
            except Exception:                                # noqa: BLE001
                print(traceback.format_exc())

    # -- state -------------------------------------------------------------------
    def is_open(self):
        return self.phase in ("opening", "open")

    def clock(self):
        return _clock()

    def _age(self, burst):
        if self.age_override is not None:
            return float(self.age_override)
        return self.clock() - burst["t0"]

    def current_rows(self):
        return self.rows.get(self.tab, [])

    def selected_names(self):
        """The animation layers selected, the column's order: the panel's own Ctrl / Shift
        pick while it still holds the active layer and Maya reports no more than one
        selected (Maya's Layer Editor may fold a selection of several back to one), else
        Maya's selection."""
        names = [r["name"] for r in self.rows["anim"]]
        maya = [r["name"] for r in self.rows["anim"] if r.get("selected") or r.get("active")]
        chosen = self.chosen
        if chosen and len(maya) <= 1 and self.active_name() in chosen and all(n in names for n in chosen):
            return [n for n in names if n in set(chosen)]
        return maya

    def active_name(self):
        for row in self.rows["anim"]:
            if row.get("active"):
                return row["name"]
        return None

    def _lanes_wanted(self):
        return self.is_open() and self.lanes_on and self.tab == "anim"

    def _lanes_shown(self):
        return self.lanes.isVisible()

    # -- opening and closing -----------------------------------------------------
    def toggle(self, origin):
        if self.is_open():
            self.close(origin)
        else:
            self.open(origin)

    def _local(self, widget, point):
        g = widget.geometry()
        return (float(point[0]) - g.x(), float(point[1]) - g.y())

    def _column_parts(self, lay):
        """[(uid, rect)] of the column's burst parts."""
        parts = [(("seg", t), lay.segments[t]) for t in L.TABS]
        parts.append((("lanes",), lay.lanes))
        for i in self._visible_rows(lay):
            parts.append((("row", i), lay.row_at(i, self.scroll)))
        parts += [(("foot", name), rect) for name, rect in lay.foot]
        return parts

    def _lane_parts(self, lay):
        w = float(self.lanes.width())
        return [(i, (0.0, r[1], w, r[3])) for i, r in
                ((i, lay.row_at(i, self.scroll)) for i in self._visible_rows(lay))]

    def _visible_rows(self, lay):
        wy, wh = lay.well[1], lay.well[3]
        out = []
        for i in range(len(lay.rows)):
            r = lay.row_at(i, self.scroll)
            if r[1] + r[3] > wy and r[1] < wy + wh:
                out.append(i)
        return out

    def _make_burst(self, parts, origin, opening):
        rects = [rect for _uid, rect in parts]
        delays = dict(zip([uid for uid, _rect in parts], L.schedule(rects, origin, self.ui)))
        if opening:
            far = max([d[0] for d in delays.values()] or [0.0])
            ends = max(far + look.POP_OPEN_MS, look.UNROLL_MS)
            return {"t0": self.clock(), "open": True, "origin": origin, "delays": delays,
                    "close_at": None, "ends": ends}
        far = max([d[1] for d in delays.values()] or [0.0])
        close_at = far + look.FOLD_MS + look.CLOSE_AFTER_MS
        return {"t0": self.clock(), "open": False, "origin": origin, "delays": delays,
                "close_at": close_at, "ends": close_at + look.CLOSE_MS}

    def _remembered(self):
        """The tab, the height and the lanes the animator left them at."""
        tab = self._option(TAB_VAR, "anim")
        self.tab = tab if tab in L.TABS else "anim"
        try:
            self.height = float(self._option(HEIGHT_VAR, L.DEFAULT_H))
        except (TypeError, ValueError):
            self.height = float(L.DEFAULT_H)
        self.lanes_on = bool(self._option(LANES_VAR, 0))

    def open(self, origin):
        self._remembered()
        self.refresh(force=True)
        self.place()
        self._origin = origin
        self.column.show()
        self.column.raise_()
        if self.motion:
            lay = self.column.layout_()
            self.burst = self._make_burst(self._column_parts(lay), self._local(self.column, origin), True)
            self.phase = "opening"
        else:
            self.burst = None
            self.phase = "open"
        if self._lanes_wanted():
            self._show_lanes(burst=self.motion)
        self.column.invalidate()
        self.placer.start()
        self.kick()

    def close(self, origin=None):
        self._end_drag()
        self.placer.stop()
        self._drop_editor()
        if origin is None:
            origin = self._origin or self._column_centre()
        if not self.motion or not self.column.isVisible():
            self.column.hide()
            self.lanes.hide()
            self.burst = self.lanes_burst = None
            self.phase = "closed"
            return
        lay = self.column.layout_()
        self.burst = self._make_burst(self._column_parts(lay), self._local(self.column, origin), False)
        self.phase = "closing"
        if self.lanes.isVisible():
            self._hide_lanes(burst=True)
        self.column.invalidate()
        self.kick()

    def _column_centre(self):
        g = self.column.geometry()
        return (g.x() + g.width() / 2.0, g.y() + g.height())

    def _lanes_origin(self):
        lay = self.column.layout_()
        return (float(self.lanes.width()), lay.head[1] + lay.head[3] / 2.0)

    def _show_lanes(self, burst):
        self._read_keys()
        self.place()
        self.lanes.show()
        self.lanes.raise_()
        if burst and self.motion:
            lay = self.column.layout_()
            parts = [(i, rect) for i, rect in self._lane_parts(lay)]
            self.lanes_burst = self._make_burst(parts, self._lanes_origin(), True)
        else:
            self.lanes_burst = None
        self.lanes.invalidate()
        self.kick()

    def _hide_lanes(self, burst):
        if burst and self.motion and self.lanes.isVisible():
            lay = self.column.layout_()
            self.lanes_burst = self._make_burst(self._lane_parts(lay), self._lanes_origin(), False)
            self.kick()
            return
        self.lanes_burst = None
        self.lanes.hide()

    # -- where -------------------------------------------------------------------
    def place(self):
        """The column over the frame field and transport, its bottom over the strip;
        the lanes from the timeline's left to the column."""
        try:
            strip, timeline = self.strip.strip_rect(), self.strip.timeline_rect()
            height = L.clamp_height(self.height, self.strip.top_room() / self.ui) * self.ui      # logical -> px
            rect = L.column_rect(strip, timeline, height, self.ui)
            geo = tuple(int(round(v)) for v in rect)
            if self.column.geometry().getRect() != geo:
                self.column.setGeometry(*geo)
            lanes = tuple(int(round(v)) for v in L.lanes_rect(geo, timeline))
            if self.lanes.geometry().getRect() != lanes:
                self.lanes.setGeometry(*lanes)
        except Exception:                                    # noqa: BLE001
            self.placer.stop()
            print(traceback.format_exc())

    # -- reading -----------------------------------------------------------------
    def refresh(self, force=False, keys=False):
        """The rows read again (cheap: the strip's tick runs this four times a second);
        the lanes' keys only when they can have changed (2026-10-18 final review) - a
        keys read (`keys`: the selection, a layer change, an undo, a scene opened),
        a key edit marked by `keys_dirty`, new rows or a forced read."""
        anim = self._call("anim_layers") or []
        disp = self._call("display_layers") or []
        sigs = (L.signature(anim), L.signature(disp))
        changed = force or sigs != self._sigs
        if changed:
            self._sigs = sigs
            self.rows = {"anim": anim, "disp": disp}
            if self.picked_disp not in [r["name"] for r in disp]:
                self.picked_disp = None
            self._clamp_scroll()
            self.column.invalidate()
        if self._lanes_shown() and (keys or changed or self._keys_stale):
            if self.lanes_moving() or self._timeline_dragging():
                #  a key drag on the lanes: drawn from the keys read before it, moved by its
                #  preview; a read now would move the moved keys again («ключи мигают при
                #  переносе», 2026-10-19). Read on the release.
                self._keys_stale = True
            else:
                self._read_keys()

    def _read_keys(self):
        self._keys_stale = False
        self.keys = self._call("keys_by_layer", [r["name"] for r in self.rows["anim"]]) or {}
        self.lanes.invalidate()

    def lanes_moving(self):
        """A key drag on the lanes stands (a key pressed, a block moved or scaled)."""
        drag = self.lane_drag
        return bool(self.lane_live) or bool(drag and drag[0] in ("key", "kpend"))

    def keys_dirty(self):
        """A key edit (Maya's callback, many in a drag or a bake): read on the next
        refresh, not here."""
        self._keys_stale = True

    # -- one drag on both views (2026-10-20) --------------------------------------
    #
    # «НАш тайм слайдер основной должен в точности реагировать на действия на
    # выдвижной панели слоев ... ключи должны перемещаться при переносе и на
    # таймслайдере и на выдвижной панели слоев не важно где я их перемещаю если слой
    # соответствует таймлайну мы должны видеть что происходит»: the timeline shows the
    # ACTIVE layer's keys, so a drag of them on the lanes moves them on the timeline,
    # and a drag on the timeline moves them on the active layer's lane.

    def _timeline_moving(self):
        """The timeline's own key drag: (selection, target, carried), else None."""
        own = getattr(getattr(self.strip, "timeline", None), "own_moving", None)
        if own is None:
            return None
        try:
            return own()
        except Exception:                                    # noqa: BLE001
            print(traceback.format_exc())
            return None

    def _timeline_dragging(self):
        """A key drag on the timeline stands (its own preview, or its live step):
        the lanes read no keys, they draw it from the keys read before it."""
        tl = getattr(self.strip, "timeline", None)
        return self._timeline_moving() is not None or bool(getattr(tl, "live", None))

    def _own_drag(self):
        sel = self.lane_sel
        if self.lane_preview is None or not sel:
            return None
        return {"names": list(sel["names"]), "span": (sel["a"], sel["b"]),
                "target": tuple(self.lane_preview), "carried": look.held(self.lane_stamped)}

    def drag_view(self):
        """The keys the lanes draw moved: their own key drag, else the timeline's on
        the active layer's lane. {names, span, target, carried} or None."""
        own = self._own_drag()
        if own is not None:
            return own
        moving = self._timeline_moving()
        name = self.active_name()
        if moving is None or name is None:
            return None
        return {"names": [name], "span": tuple(moving[0]), "target": tuple(moving[1]),
                "carried": moving[2]}

    def active_lane_drag(self):
        """For the timeline: (selection, target, carried) of a lanes key drag that holds
        the active layer, else None."""
        own = self._own_drag()
        if own is None or self.active_name() not in own["names"]:
            return None
        return (own["span"], own["target"], own["carried"])

    def _timeline_follow(self):
        """The timeline repainted now when the lanes drag moves the active layer's keys."""
        if self.active_lane_drag() is None:
            return
        tl = getattr(self.strip, "timeline", None)
        if tl is not None:
            try:
                tl.repaint()
            except Exception:                                # noqa: BLE001
                print(traceback.format_exc())

    def _scrub(self, frame, update=True):
        """The lanes' scrub: the strip's playhead moved with it at once (one playhead
        for both views), else straight to Maya."""
        scrub_to = getattr(self.strip, "scrub_to", None)
        if scrub_to is not None:
            try:
                scrub_to(frame, update)
                return
            except Exception:                                # noqa: BLE001
                print(traceback.format_exc())
        self._call("set_time" if update else "scrub_only", frame)

    # -- the lanes as a dope sheet (2026-10-19) ---------------------------------
    #
    # «выдвижная панель с ключами ... должна повторять функционал таймлайна»: each lane
    # is the timeline for that layer's keys of the selection. A press scrubs, a
    # Shift-drag highlights a range on the lanes it sweeps, the highlight's body moves
    # and its edges scale those layers' keys, the right button is the key menu.

    def _track(self):
        try:
            return self.strip.track()
        except Exception:                                    # noqa: BLE001
            return None

    def lane_name(self, i):
        rows = self.rows["anim"]
        return rows[i]["name"] if i is not None and 0 <= i < len(rows) else None

    def lane_index(self, y):
        return L.lane_at(self.column.layout_(), y, self.scroll)

    def lane_part(self, x, i):
        """'h0' / 'h1' / 'hmove' over the highlight on lane `i`, else None."""
        sel, t = self.lane_sel, self._track()
        if not sel or t is None or self.lane_name(i) not in sel["names"]:
            return None
        return look.highlight_hit(t, x, (sel["a"], sel["b"]), self.ui)

    def _lane_grip(self, part, x, t):
        """The frame a highlight drag counts from (the timeline's `_grip`): an edge
        counts frame lines, the body cells."""
        if part in ("h0", "h1"):
            return int(round(t.frame(x)))
        return t.whole(x)

    def lane_key_under(self, x, i):
        """The key of lane `i` whose cell `x` is in (the timeline's `_key_under`)."""
        t, name = self._track(), self.lane_name(i)
        if t is None or name is None:
            return None
        near, best = max(3 * self.ui, t.scale / 2.0), None
        for k in self.keys.get(name, []):
            d = abs(look.key_centre(t, k) - x)
            if d <= near:
                best, near = k, d
        return best

    def _now(self):
        try:
            return float(self.strip.now())
        except Exception:                                    # noqa: BLE001
            return None

    def lane_press(self, x, y, shift=False, middle=False):
        t = self._track()
        if t is None:
            return
        self._lane_end_live()
        i = self.lane_index(y)
        name = self.lane_name(i)
        frame = t.whole(x)
        if middle:
            self.lane_drag = ("mid", frame)
            self._scrub(frame, update=False)
        elif shift and name is not None:
            self.lane_sel = {"a": frame, "b": frame, "names": [name]}
            self.lane_drag = ("hl", i, frame)
        else:
            part = self.lane_part(x, i)
            key = self.lane_key_under(x, i)
            if part:
                sel = (self.lane_sel["a"], self.lane_sel["b"])
                self.lane_drag = ("key", part, self._lane_grip(part, x, t), sel, False)
                self.lane_preview, self.lane_stamped, self.lane_live = sel, None, None
            elif key is not None and frame != self._now():
                #  a key pressed: dragged past the start distance it moves alone, no
                #  highlight needed; let go where it was, it is a click on the time
                self.lane_drag = ("kpend", frame, x, key, i)
            else:
                self._lane_time(x, i, frame)
        self.lanes.invalidate()

    def _lane_time(self, x, i, frame):
        name = self.lane_name(i)
        self.lane_sel = None
        if name is not None and not self.rows["anim"][i].get("active"):
            self.anchor = name
            self.chosen = [name]
            self._write("pick", name)
        self.lane_drag = ("scrub", frame)
        self._call("begin_scrub")
        self._scrub(frame)

    def _start_distance(self):
        try:
            return self.q.QtWidgets.QApplication.startDragDistance()
        except Exception:                                    # noqa: BLE001
            return 4

    def lane_move(self, x, y):
        drag, t = self.lane_drag, self._track()
        if not drag or t is None:
            return
        frame = t.whole(x)
        if drag[0] == "kpend":
            if abs(x - drag[2]) < self._start_distance():
                return
            key = int(math.floor(drag[3] + 1e-6))
            self.lane_sel = {"a": key, "b": key, "names": [self.lane_name(drag[4])]}
            self.lane_drag = ("key", "hmove", drag[1], (key, key), True)
            self.lane_preview, self.lane_stamped, self.lane_live = (key, key), None, None
            drag = self.lane_drag
        if drag[0] in ("scrub", "mid"):
            if frame != drag[1]:
                self.lane_drag = (drag[0], frame)
                self._scrub(frame, update=(drag[0] == "scrub"))
                self.lanes.repaint()
            return
        if drag[0] == "hl":
            i = self.lane_index(y)
            if i is None:
                i = drag[1]
            rows = self.rows["anim"]
            names = [rows[k]["name"] for k in L.lanes_between(drag[1], min(i, len(rows) - 1))]
            a, b = look.highlight(drag[2], frame)
            sel = {"a": a, "b": b, "names": names}
            if sel != self.lane_sel:
                self.lane_sel = sel
                self.lanes.invalidate()
        elif drag[0] == "key":
            target = look.key_drag(drag[1], drag[3], drag[2], self._lane_grip(drag[1], x, t))
            if target != self.lane_preview:
                self.lane_preview = target
                self.lanes.repaint()            # the still picture stays; the dragged part moves now
                self._timeline_follow()         # and on the timeline, when it is the active layer
                if not self.lane_timer.isActive():
                    self.lane_timer.start()     # the scene follows on the next turn, newest only

    def _flush_lane_live(self):
        """The scene's keys to the NEWEST target of the lanes drag (the timeline's
        `_flush_live`): one step for every move handled since the last."""
        drag = self.lane_drag
        if not drag or drag[0] != "key" or self.lane_preview is None:
            return
        self._lane_live_to(self.lane_preview)

    def flush_lane_live(self):
        """A step still waiting, made now (S in the drag, a press after a lost release)."""
        if self.lane_timer.isActive():
            self.lane_timer.stop()
            self._flush_lane_live()

    def _lane_live_to(self, target):
        """The scene's keys follow the drag, as under the timeline (the viewport shows it)."""
        if self.lane_live is None and self.lane_sel:
            self.lane_live = bool(self._call("lane_live_begin", list(self.lane_sel["names"]),
                                             tuple(self.lane_drag[3])))
        if self.lane_live:
            self._call("lane_live_to", tuple(target))

    def _quiet_strip(self):
        quiet = getattr(self.strip, "quiet_keys", None)
        if quiet is not None:
            try:
                quiet()
            except Exception:                                # noqa: BLE001
                print(traceback.format_exc())

    def _lane_end_live(self):
        """A live drag whose release never came: set it down where it stands."""
        self.flush_lane_live()
        if self.lane_live:
            self.lane_live = None
            self._quiet_strip()
            self._call("lane_live_end", tuple(self.lane_preview) if self.lane_preview else None)

    def lane_stamp(self):
        """S during a drag on the lanes: a key drag leaves a copy of the dragged keys
        where they are now (the timeline's rule); a scrub keys the active layer at the
        frame. True when it was ours."""
        drag = self.lane_drag
        if not drag:
            return False
        if drag[0] == "key":
            self.flush_lane_live()              # a step still waiting: the keys where they are drawn
            if not self.lane_live:
                self._lane_live_to(self.lane_preview or drag[3])
            if self.lane_live:
                got = self._call("lane_live_stamp")
                if isinstance(got, dict) and got:
                    self.lane_stamped = got
                    self._add_drawn_copies(got, tuple(drag[3]), tuple(self.lane_preview or drag[3]))
            self.lanes.invalidate()
            return True
        if drag[0] in ("scrub", "mid"):
            name = self.active_name()
            if name:
                self._write("lane_set_key", name)
            return True
        return False

    def _add_drawn_copies(self, stamped, selection, target):
        """The copies S put down mid-drag, drawn on their lanes at once: the scene holds
        them, but the lanes read keys again only on the release (2026-10-19: «проставленный
        ключик не будет отрисовываться пока не отпустить клавишу мышки»). A copy goes on
        every dragged lane that had the key it was copied from."""
        names = list(self.lane_sel["names"]) if self.lane_sel else []
        for rec in stamped.values():
            put = set(round(t, 4) for t in rec.get("stamped", ()))
            for t, _data in rec.get("keys", ()):
                nt = look.mapped(t, selection, target)
                if round(nt, 4) not in put:
                    continue
                for name in names:
                    have = self.keys.setdefault(name, [])
                    if any(abs(k - t) < 1e-4 for k in have) and not any(abs(k - nt) < 1e-4 for k in have):
                        have.append(float(nt))
                        have.sort()

    def keys_block(self):
        """The lane block S keys with no drag: any block over several lanes, one frame
        too (2026-10-20: «при груповом выделении сразу на нескольких таймлайнах сейчас не
        работает проставление ключей через хоткей s» - a column shift-dragged down the
        lanes went to Maya's S, which keys the active layer alone, at the current frame);
        on one lane, two frames or more (one cell on one lane is Maya's S, the
        timeline's rule)."""
        sel = self.lane_sel
        if self.lane_drag or not sel or not sel.get("names") or not self._lanes_shown():
            return None
        if sel["b"] <= sel["a"] and len(sel["names"]) < 2:
            return None
        return sel

    def lane_key_range(self):
        """S with a lane block standing (`keys_block`) and no drag: a key on every frame
        of it on its lanes' layers (the timeline's rule for a highlight). True when it
        was ours."""
        sel = self.keys_block()
        if sel is None:
            return False
        if self.active_name() in sel["names"]:
            #  the timeline shows the active layer: its keys of the block flash (and cool)
            mark = getattr(self.strip, "mark_set", None)
            if mark is not None:
                mark(sel["a"], sel["b"])
        self._write("lane_key_range", list(sel["names"]), int(sel["a"]), int(sel["b"]))
        return True

    def lane_release(self):
        #  a step still waiting is not made: the release sets the keys down on the preview
        #  itself (lane_live_end, or lane_move when no step was made)
        self.lane_timer.stop()
        drag, self.lane_drag = self.lane_drag, None
        if not drag:
            return
        if drag[0] == "kpend":
            #  a key clicked, not dragged: the time goes there, as on the timeline
            self._lane_time(drag[2], drag[4], drag[1])
            drag, self.lane_drag = self.lane_drag, None
        if drag[0] == "scrub":
            self._call("end_scrub")
        elif drag[0] == "key":
            #  the preview stays until the keys are read again: cleared first, a paint in
            #  between (Maya's time callback repaints the lanes at once) drew the key at its
            #  old place for a moment (2026-10-19: «сперва мигает изображение там где он был»)
            target = self.lane_preview
            sel, loose = drag[3], drag[4]
            names = list(self.lane_sel["names"]) if self.lane_sel else []
            moved = bool(target) and tuple(target) != tuple(sel)
            #  the key aimed when the drag began is not under the mouse any more: aimed
            #  still, it was drawn lifted at the frame it was taken from until the next move
            #  (2026-10-20: «в том месте где мы его взяли на пару кадров появится изображение
            #  ключа»)
            self.lane_aimed = None
            #  a move is no key set and deleted: the strip plays no effect for it
            self._quiet_strip()
            if self.lane_live:
                self.lane_live = None
                self._after_write(self._call("lane_live_end", tuple(target or sel)))
            elif moved and names:
                self._write("lane_move", names, sel, tuple(target))
            self.lane_preview = None
            self.lane_stamped = None
            if moved and names:
                self.lane_sel = None if loose else {"a": target[0], "b": target[1], "names": names}
            elif loose:
                self.lane_sel = None
        self.lanes.invalidate()

    def lane_aim(self, x, y):
        """The key under the mouse lifts, as on the timeline. Answers what a press does
        there: 'edge', 'grab' or 'time' (the cursor)."""
        i = self.lane_index(y)
        key = self.lane_key_under(x, i)
        aim = (self.lane_name(i), key) if key is not None else None
        if aim != self.lane_aimed:
            self.lane_aimed = aim
            self.lanes.update()
        part = self.lane_part(x, i)
        return "edge" if part in ("h0", "h1") else ("grab" if part == "hmove" or key is not None else "time")

    def lane_all(self, y):
        """Every key of the lane under `y` highlighted."""
        name = self.lane_name(self.lane_index(y))
        if name is None:
            return
        span = look.all_keys(self.keys.get(name, []))
        self.lane_sel = {"a": span[0], "b": span[1], "names": [name]} if span else None
        self.lanes.invalidate()

    def lane_menu(self, y):
        """The key menu's rows for a right press on the lanes at `y`."""
        name = self.lane_name(self.lane_index(y))
        sel = self.lane_sel
        names = list(sel["names"]) if sel else ([name] if name else [])
        if not names:
            return []
        span = (sel["a"], sel["b"]) if sel else None
        try:
            now = float(self.strip.now())
        except Exception:                                    # noqa: BLE001
            now = 0.0

        def op(kind, extra=None):
            return lambda: self._write("lane_keys", kind, names, span, now, extra)

        key_layer = name if name else names[0]
        rows = [("Set key on %s" % self._label_of(key_layer), lambda: self._write("lane_set_key", key_layer)),
                ("Breakdown", op("breakdown")), None,
                ("Cut", op("cut")), ("Copy", op("copy")), ("Paste", op("paste")), ("Delete", op("delete")),
                None,
                ("Tangents", [(label, op("tangents", kind)) for label, kind in look.TANGENTS]),
                ("Snap", op("snap")), None,
                ("Highlight all keys", lambda: self.lane_all(y))]
        if sel:
            rows.append(("Clear highlight", self.lane_clear))
        return rows

    def lane_clear(self):
        self.lane_sel = self.lane_preview = None
        self.lanes.invalidate()

    def _label_of(self, name):
        for row in self.rows["anim"]:
            if row["name"] == name:
                return row.get("label", name)
        return name

    def lane_menu_at(self, y, global_point):
        rows = self.lane_menu(y)
        if not rows:
            return
        QtWidgets = self.q.QtWidgets
        builder = getattr(self.strip, "menu_rows", None)
        try:
            if builder is not None:
                menu, picked = builder(rows, QtWidgets.QMenu(self.lanes))
            else:
                menu, picked = _menu_rows(QtWidgets, rows, QtWidgets.QMenu(self.lanes))
            menu.setStyleSheet(bar.stylesheet(self.tokens, self.ui))
            chosen = menu.exec(global_point)
            menu.deleteLater()
        except Exception:                                    # noqa: BLE001
            print(traceback.format_exc())
            return
        action = picked.get(chosen)
        if action is not None:
            try:
                action()
            except Exception:                                # noqa: BLE001
                print(traceback.format_exc())

    def on_time(self):
        """The lanes' playhead cell: repainted now, not on an idle (trap 269); the
        column when a weight's key cell turned on or off this frame."""
        if self._lanes_shown():
            self.lanes.repaint()
        try:
            if self.is_open() and self.weight_states() != self._wstates:
                self.column.repaint()
        except Exception:                                    # noqa: BLE001
            print(traceback.format_exc())

    def now(self):
        try:
            return float(self.strip.now())
        except Exception:                                    # noqa: BLE001
            return None

    def weight_states(self):
        """Each layer's weight key cell at the current frame (the column's picture is
        drawn again when one changes)."""
        now = self.now()
        return tuple(L.weight_state(r, now) for r in self.rows.get("anim", []))

    def _clamp_scroll(self):
        lay = self.column.layout_()
        self.scroll = max(0.0, min(self.scroll, lay.max_scroll))

    def scroll_by(self, dy):
        lay = self.column.layout_()
        new = max(0.0, min(self.scroll + dy, lay.max_scroll))
        if new != self.scroll:
            self.scroll = new
            self.column.invalidate()
            if self._lanes_shown():
                self.lanes.invalidate()

    # -- the line ----------------------------------------------------------------
    def say(self, text):
        self.status = str(text or "")
        self.status_timer.start()
        self.column.invalidate()

    def _clear_status(self):
        self.status = ""
        self.column.invalidate()

    # -- presses -----------------------------------------------------------------
    def press(self, hit, pos=None, gy=None, ctrl=False, shift=False):
        """A left press on the column at `hit` (layerlook.hit); Ctrl / Shift on a
        layer's name add to or range Maya's layer selection."""
        if not hit:
            return
        lay = self.column.layout_()
        kind = hit[0]
        if kind == "tab":
            self.flashes[("seg", hit[1])] = self.clock()
            self._switch_tab(hit[1], lay)
        elif kind == "lanes":
            if self.tab != "anim":
                return
            self.flashes[("lanes",)] = self.clock()
            self.pops[("lanes",)] = self.clock()
            self.lanes_on = not self.lanes_on
            self._set_option(LANES_VAR, int(self.lanes_on))
            if self.lanes_on:
                self._show_lanes(burst=True)
            else:
                self._hide_lanes(burst=True)
            self.column.invalidate()
        elif kind == "grip":
            self.drag = ("grip", float(gy if gy is not None else 0.0), L.clamp_height(self.height, self.strip.top_room() / self.ui))   # logical px
            self.column.update()
        elif kind == "foot":
            self.flashes[("foot", hit[1])] = self.clock()
            self._foot(hit[1], lay)
        elif kind == "row":
            self._row_press(hit[1], hit[2], lay, pos, ctrl, shift)
        self.kick()

    def _switch_tab(self, tab, lay):
        if tab == self.tab:
            return
        self._drop_editor()
        self.tab = tab
        self.scroll = 0.0
        self._set_option(TAB_VAR, tab)
        lay = self.column.layout_()
        if self.motion:
            seg = lay.segments[tab]
            origin = (seg[0] + seg[2] / 2.0, seg[1] + seg[3] / 2.0)
            rows = self._visible_rows(lay)
            sched = L.schedule([lay.row_at(i, 0.0) for i in rows], origin, self.ui)
            self.wave = {"t0": self.clock(), "delays": {i: d[0] for i, d in zip(rows, sched)}}
        if self._lanes_wanted():
            if not self._lanes_shown():
                self._show_lanes(burst=True)
        elif self._lanes_shown():
            self._hide_lanes(burst=True)
        self.column.invalidate()

    def _row_press(self, i, part, lay, pos, ctrl=False, shift=False):
        rows = self.current_rows()
        if i >= len(rows):
            return
        row = rows[i]
        name = row["name"]
        if part == "name" or part in ("mode", "swatch"):
            if self.tab == "anim":
                if ctrl or shift:
                    names = [r["name"] for r in rows]
                    picked, active = L.selection_after(self.selected_names(), name, self.anchor,
                                                       ctrl, shift, names)
                    if not shift:
                        self.anchor = name
                    self.chosen = list(picked)
                    self._write("select_layers", picked, active)
                else:
                    self.anchor = name
                    self.chosen = [name]
                    self._write("pick", name)
            else:
                self.picked_disp = name
                self.column.invalidate()
        elif part in ("mute", "solo", "lock"):
            self.pops[("ctl", i, part)] = self.clock()
            self._write("set_flag", name, part, not row.get(part))
        elif part in ("visible", "playback"):
            self.pops[("ctl", i, part)] = self.clock()
            self._write("set_display", name, part, not row.get(part))
        elif part == "type":
            self.pops[("ctl", i, part)] = self.clock()
            self._write("set_display", name, "type", L.step_type(row.get("type", 0)))
        elif part == "wkey":
            #  the weight's key cell: keyed / unkeyed at the current frame (2026-10-20)
            self.pops[("ctl", i, part)] = self.clock()
            self._write("toggle_weight_key", name)
        elif part in ("weight", "wnum"):
            rect = L.row_parts(lay.row_at(i, self.scroll), self.tab, self.ui, base=row.get("base"))["weight"]
            self.drag = ("weight", name, rect)
            self._call("begin_weight")
            if pos is not None:
                self._set_weight(name, L.weight_at(pos[0], rect))

    def _set_weight(self, name, value):
        """A weight while it is dragged: Maya's at once, the row updated here; the
        scene is read again once, on the release."""
        self._call("set_weight", name, value)
        for row in self.rows["anim"]:
            if row["name"] == name:
                row["weight"] = value
        self.column.invalidate()

    def drag_to(self, x, gy):
        """A move while a weight or the grip is held."""
        if not self.drag:
            return
        if self.drag[0] == "weight":
            _kind, name, rect = self.drag
            self._set_weight(name, L.weight_at(x, rect))
        elif self.drag[0] == "grip":
            _kind, gy0, h0 = self.drag
            self.height = L.clamp_height(h0 - (gy - gy0) / self.ui, self.strip.top_room() / self.ui)
            self.place()
            self._clamp_scroll()
            self.column.invalidate()
            if self._lanes_shown():
                self.lanes.invalidate()

    def _end_drag(self):
        """Whatever ends a drag without a release (the column closed or hidden, the
        mouse grab lost, the window deactivated) still closes Maya's undo chunk and
        keeps the height; once only (release clears the drag first)."""
        if self.drag:
            self.release()

    def release(self):
        drag, self.drag = self.drag, None
        if not drag:
            return
        if drag[0] == "weight":
            self._after_write(self._call("end_weight"))
        elif drag[0] == "grip":
            self._set_option(HEIGHT_VAR, int(round(self.height)))
        self.column.update()
        self.kick()

    def _foot(self, name, lay):
        if self.tab == "anim":
            if name == "add":
                self._write("create_anim")
                return
            target = self.active_name()
            if name == "merge" and len(self.selected_names()) >= 2:
                self._write("merge_selected", self.selected_names())
                return
            calls = {"addsel": "add_selection", "remsel": "remove_selection",
                     "merge": "merge_down", "delete": "delete_anim"}
        else:
            if name == "add":
                self._write("create_display")
                return
            target = self.picked_disp
            calls = {"addsel": "display_add", "remsel": "display_remove",
                     "select": "display_select", "delete": "delete_display"}
        call = calls.get(name)
        if call is None:
            return
        if not target:
            self.say("pick a layer first")
            return
        if name == "delete":
            self._delete(call, target, lay)
        else:
            self._write(call, target)

    def _delete(self, call, name, lay):
        """The data at once; the row's picture folds where it stood."""
        rows = self.current_rows()
        index = next((i for i, r in enumerate(rows) if r["name"] == name), None)
        row = dict(rows[index]) if index is not None else None
        rect = lay.row_at(index, self.scroll) if index is not None else None
        tab = self.tab
        self._write(call, name)
        if row is not None and self.motion and name not in [r["name"] for r in self.rows[tab]]:
            self.ghosts.append({"t0": self.clock(), "row": row, "rect": rect, "tab": tab, "index": index})
            self.kick()

    # -- the right button --------------------------------------------------------
    def row_menu(self, i):
        """The rows of a layer's right-button menu: (label, callable | None [, checked]),
        None for a separator, (label, [rows]) for a submenu."""
        rows = self.current_rows()
        if i >= len(rows):
            return []
        row = rows[i]
        name = row["name"]
        if self.tab == "anim":
            if row.get("base"):
                return [("Additive", None), ("Override", None), None, ("Rename", None),
                        ("Select objects", None), ("Add selection", None), ("Remove selection", None), None,
                        ("Merge selected", self._merge_selected_row()), ("Merge down", None), ("Delete", None)]
            lay = self.column.layout_()
            return [("Additive", lambda: self._write("set_mode", name, "add"), row.get("mode") == "add"),
                    ("Override", lambda: self._write("set_mode", name, "ovr"), row.get("mode") == "ovr"),
                    None,
                    ("Rename", lambda: self.start_rename(i)),
                    ("Select objects", lambda: self._write("select_objects", name)),
                    ("Add selection", lambda: self._write("add_selection", name)),
                    ("Remove selection", lambda: self._write("remove_selection", name)),
                    None,
                    ("Merge selected", self._merge_selected_row()),
                    ("Merge down", lambda: self._write("merge_down", name)),
                    ("Delete", lambda: self._delete("delete_anim", name, lay))]
        lay = self.column.layout_()
        colours = [("Colour %d" % n, (lambda n=n: self._write("set_display", name, "colour", n)))
                   for n in COLOUR_INDICES]
        return [("Rename", lambda: self.start_rename(i)),
                ("Colour", colours),
                None,
                ("Select objects", lambda: self._write("display_select", name)),
                ("Add selection", lambda: self._write("display_add", name)),
                ("Remove selection", lambda: self._write("display_remove", name)),
                None,
                ("Delete", lambda: self._delete("delete_display", name, lay))]

    def _merge_selected_row(self):
        names = self.selected_names()
        if len(names) < 2:
            return None
        return lambda: self._write("merge_selected", names)

    def menu_at(self, i, global_point):
        rows = self.row_menu(i)
        if not rows:
            return
        QtWidgets = self.q.QtWidgets
        builder = getattr(self.strip, "menu_rows", None)
        try:
            if builder is not None:
                menu, picked = builder(rows, QtWidgets.QMenu(self.column))
            else:
                menu, picked = _menu_rows(QtWidgets, rows, QtWidgets.QMenu(self.column))
            menu.setStyleSheet(bar.stylesheet(self.tokens, self.ui))
            chosen = menu.exec(global_point)
            menu.deleteLater()
        except Exception:                                    # noqa: BLE001
            print(traceback.format_exc())
            return
        action = picked.get(chosen)
        if action is not None:
            try:
                action()
            except Exception:                                # noqa: BLE001
                print(traceback.format_exc())

    # -- renaming ----------------------------------------------------------------
    def start_rename(self, i):
        rows = self.current_rows()
        if i >= len(rows):
            return
        self._drop_editor()
        row = rows[i]
        lay = self.column.layout_()
        rect = L.row_parts(lay.row_at(i, self.scroll), self.tab, self.ui, base=row.get("base"))["name"]
        self._editor = _editor_class()(self, row["name"], row.get("label", row["name"]))
        self._editor.setGeometry(int(rect[0]), int(rect[1] + 3 * self.ui), int(rect[2]), int(rect[3] - 6 * self.ui))
        self._editor.show()
        self.column.activateWindow()
        self._editor.setFocus()
        self._editor.selectAll()

    def finish_rename(self, name, text):
        self._drop_editor()
        text = (text or "").strip()
        if text:
            self._write("rename", name, text)

    def _drop_editor(self):
        editor, self._editor = self._editor, None
        if editor is not None:
            try:
                editor.hide()
                editor.deleteLater()
            except RuntimeError:
                pass

    # -- hover -------------------------------------------------------------------
    def hover_at(self, h):
        """The ids under the mouse lift; every other goes back."""
        ids = []
        if h:
            if h[0] == "tab":
                ids = [("seg", h[1])]
            elif h[0] == "lanes":
                ids = [("lanes",)]
            elif h[0] == "foot":
                ids = [("foot", h[1])]
            elif h[0] == "grip":
                ids = [("grip",)]
            elif h[0] == "row":
                ids = [("row", h[1])]
                if h[2] in TOGGLES:
                    ids.append(("ctl", h[1], h[2]))
        changed = False
        for uid in set(self.goal) | set(ids):
            goal = 1.0 if uid in ids else 0.0
            if self.goal.get(uid, 0.0) != goal:
                self.goal[uid] = goal
                changed = True
                if not self.motion:
                    self.hover[uid] = goal
        if changed:
            self.column.update()
            self.kick()

    # -- the driver --------------------------------------------------------------
    def kick(self):
        if not self.motion:
            self.column.update()
            if self.lanes.isVisible():
                self.lanes.update()
            return
        if not self.driver.isActive():
            self._last_step = self.clock()
            self.driver.start()

    def _busy(self, now):
        busy = False
        b = self.burst
        if b is not None:
            if now - b["t0"] < b["ends"] + 20:
                busy = True
            elif b["open"]:
                self.burst = None
                self.phase = "open"
                self.column.invalidate()
                busy = True
            else:
                self.burst = None
                self.column.hide()
                self.lanes.hide()
                self.lanes_burst = None
                self.phase = "closed"
        lb = self.lanes_burst
        if lb is not None:
            if now - lb["t0"] < lb["ends"] + 20:
                busy = True
            else:
                self.lanes_burst = None
                if not lb["open"]:
                    self.lanes.hide()
                else:
                    self.lanes.invalidate()
                busy = True
        w = self.wave
        if w is not None:
            far = max(list(w["delays"].values()) or [0.0])
            if now - w["t0"] < far + look.POP_OPEN_MS + 20:
                busy = True
            else:
                self.wave = None
                self.column.invalidate()
                busy = True
        if self.ghosts:
            self.ghosts = [g for g in self.ghosts if now - g["t0"] < look.FOLD_MS + 20]
            busy = True
        for table, ms in ((self.pops, bar.POP_MS), (self.flashes, bar.FLASH_MS)):
            for uid, t0 in list(table.items()):
                if now - t0 < ms + 20:
                    busy = True
                else:
                    del table[uid]
                    self.column.update()
        for uid, goal in self.goal.items():
            if abs(self.hover.get(uid, 0.0) - goal) > 0.005:
                busy = True
        return busy

    def _animate(self):
        try:
            now = self.clock()
            dt = now - (self._last_step or now)
            self._last_step = now
            for uid, goal in list(self.goal.items()):
                level = look.approach(self.hover.get(uid, 0.0), goal, dt, bar.HOVER_MS)
                self.hover[uid] = level
                if level == 0.0 and goal == 0.0:
                    del self.goal[uid]
                    self.hover.pop(uid, None)
                    self.column.update()
            busy = self._busy(now)
            if busy or self._was_busy:
                if self.column.isVisible():
                    self.column.update()
                if self.lanes.isVisible():
                    self.lanes.update()
            self._was_busy = busy
            if not busy:
                self.driver.stop()
        except Exception:                                    # noqa: BLE001
            self.driver.stop()
            print(traceback.format_exc())

    def destroy(self):
        try:
            self._end_drag()
        except Exception:                                    # noqa: BLE001
            print(traceback.format_exc())
        for timer in (self.driver, self.placer, self.status_timer, self.lane_timer):
            try:
                timer.stop()
            except RuntimeError:
                pass
        self._drop_editor()
        for w in (self.column, self.lanes):
            try:
                w.hide()
                w.deleteLater()
            except RuntimeError:
                pass
        self.phase = "closed"
        try:
            live_panels().remove(self)
        except ValueError:
            pass

    # -- the burst, read by the painters -----------------------------------------
    def burst_of(self, uid):
        """(scale, opacity) of a column part in the burst, the tab's wave or at rest."""
        if not self.motion:
            return 1.0, 1.0
        b = self.burst
        if b is not None:
            age = self._age(b)
            od, fd = b["delays"].get(uid, (0.0, 0.0))
            return look.popping(age, od) if b["open"] else look.folding(age, fd)
        w = self.wave
        if w is not None and uid[0] == "row" and uid[1] in w["delays"]:
            return look.popping(self.clock() - w["t0"], w["delays"][uid[1]])
        return 1.0, 1.0

    def lane_of(self, i):
        if not self.motion or self.lanes_burst is None:
            return 1.0, 1.0
        b = self.lanes_burst
        age = self._age(b)
        od, fd = b["delays"].get(i, (0.0, 0.0))
        return look.popping(age, od) if b["open"] else look.folding(age, fd)

    def pop_of(self, uid):
        t0 = self.pops.get(uid)
        if t0 is None or not self.motion:
            return 1.0
        age = self.clock() - t0
        return 0.7 + 0.3 * look.back_out(age / float(bar.POP_MS)) if age < bar.POP_MS else 1.0

    def flash_of(self, uid):
        t0 = self.flashes.get(uid)
        if t0 is None or not self.motion:
            return 0.0
        age = self.clock() - t0
        return max(0.0, 1.0 - age / float(bar.FLASH_MS)) if age < bar.FLASH_MS else 0.0

    def excluded(self, lay):
        """The parts left out of the still picture: all of them in a burst, the
        wave's rows while it runs (a set that changes only at its start and end)."""
        if self.motion and self.burst is not None:
            return frozenset(uid for uid, _rect in self._column_parts(lay))
        if self.motion and self.wave is not None:
            return frozenset(("row", i) for i in self.wave["delays"])
        return frozenset()

    def live_units(self, lay):
        """The parts drawn over the cached picture this frame: everything in a burst,
        the rows in a wave, what is lifted, popping or flashing, the grip held."""
        units = set(uid for uid, _rect in self._column_parts(lay))
        if self.motion and self.burst is not None:
            return units
        live = set()
        if self.motion and self.wave is not None:
            #  the wave's rows are out of the still picture until the wave ends
            live |= set(("row", i) for i in self.wave["delays"])
        for uid in list(self.goal) + list(self.hover):
            if self.goal.get(uid, 0.0) > 0 or self.hover.get(uid, 0.0) > 0.005:
                live.add(_unit_of(uid))
        for uid in list(self.pops) + list(self.flashes):
            live.add(_unit_of(uid))
        if self.drag and self.drag[0] == "grip":
            live.add(("grip",))
        return live


def _menu_rows(QtWidgets, rows, menu):
    """The strip's menu_rows, for a strip that has none (a QMenu of `rows`)."""
    picked = {}
    for item in rows:
        if item is None:
            menu.addSeparator()
            continue
        label, action = item[0], item[1]
        if isinstance(action, list):
            _sub, inner = _menu_rows(QtWidgets, action, menu.addMenu(label))
            picked.update(inner)
            continue
        row = menu.addAction(label)
        if len(item) > 2:
            row.setCheckable(True)
            row.setChecked(bool(item[2]))
        if action is None:
            row.setEnabled(False)
        else:
            picked[row] = action
    return menu, picked


_CLASSES = []


def _editor_class():
    return _classes()[2]


def _classes():
    """(Column, Lanes, NameField), made on first use (no Qt at import)."""
    if _CLASSES:
        return _CLASSES[0]
    q = maya_hubqt.qt()
    QtCore, QtGui, QtWidgets = q.QtCore, q.QtGui, q.QtWidgets
    Qt = QtCore.Qt
    k = bar.kit()
    colour, blend, draw_glyph, glow = k.colour, k.blend, k.draw_glyph, k.glow

    def font(widget, px, mono=False, bold=False):
        f = QtGui.QFont("Consolas") if mono else QtGui.QFont(widget.font())
        f.setPixelSize(max(7, int(round(px))))
        f.setBold(bool(bold))
        return f

    def qrect(r):
        return QtCore.QRectF(r[0], r[1], r[2], r[3])

    def window_flags(widget, name):
        widget.setObjectName(name)
        widget.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        widget.setAttribute(Qt.WA_TranslucentBackground, True)
        widget.setAttribute(Qt.WA_ShowWithoutActivating, True)
        widget.setAttribute(Qt.WA_NoSystemBackground, True)
        widget.setAutoFillBackground(False)
        pal = widget.palette()
        pal.setColor(QtGui.QPalette.Window, QtGui.QColor(0, 0, 0, 0))
        widget.setPalette(pal)
        widget.setMouseTracking(True)
        widget.hide()

    def scaled(p, rect, z, opacity):
        p.save()
        p.setOpacity(p.opacity() * max(0.0, min(1.0, opacity)))
        c = rect.center()
        p.translate(c)
        p.scale(z, z)
        p.translate(-c)

    def shape_rect(burst, age, w, h, ui):
        """The burst's shape: a small box at the origin unrolling to the whole rect,
        or closing back onto it after the folds."""
        bw, bh = BOX[0] * ui, BOX[1] * ui
        ox = max(bw / 2.0, min(w - bw / 2.0, burst["origin"][0]))
        oy = max(bh / 2.0, min(h - bh / 2.0, burst["origin"][1]))
        if burst["open"]:
            e = look.ease_out_quint(age / float(look.UNROLL_MS))
        else:
            e = 1.0 - look.ease_in_quint((age - burst["close_at"]) / float(look.CLOSE_MS))
        x0 = (ox - bw / 2.0) * (1 - e)
        y0 = (oy - bh / 2.0) * (1 - e)
        x1 = (ox + bw / 2.0) + (w - ox - bw / 2.0) * e
        y1 = (oy + bh / 2.0) + (h - oy - bh / 2.0) * e
        return QtCore.QRectF(x0, y0, x1 - x0, y1 - y0)

    class NameField(QtWidgets.QLineEdit):
        """The one widget of Maya's kind in the column: a layer's name being typed."""

        def __init__(self, panel, name, label):
            super(NameField, self).__init__(label, panel.column)
            self.panel, self.layer = panel, name
            self.setObjectName("skeldarTimeBarLayerName")
            tk, ui = panel.tokens, panel.ui
            self.setStyleSheet(
                "QLineEdit#skeldarTimeBarLayerName {{ background: {field}; color: {text};"
                " border: 2px solid {accent}; border-radius: {r}px; padding: 0 {p}px; }}".format(
                    r=int(round(5 * ui)), p=int(round(4 * ui)), **tk))
            self._done = False
            self.returnPressed.connect(self._enter)

        def _enter(self):
            if not self._done:
                self._done = True
                self.panel.finish_rename(self.layer, self.text())

        def keyPressEvent(self, event):
            if event.key() == Qt.Key_Escape:
                self._done = True
                self.panel._drop_editor()
                return
            super(NameField, self).keyPressEvent(event)

        def focusOutEvent(self, event):
            super(NameField, self).focusOutEvent(event)
            if not self._done:
                self._done = True
                self.panel._drop_editor()

    class Painted(QtWidgets.QWidget):
        """What the column and the lanes share: a paint that raises prints once and
        stops (`_failed`); the wheel scrolls the list."""

        def paintEvent(self, _event):
            if self._failed:
                return
            try:
                self._paint()
            except Exception:                                # noqa: BLE001
                print(traceback.format_exc())
                self._failed = True

        def wheelEvent(self, event):
            dy = event.angleDelta().y()
            self.panel.scroll_by(-dy / 120.0 * (L.ROW_H + L.ROW_GAP) * self.panel.ui)
            event.accept()

    # -- the column --------------------------------------------------------------

    class Column(Painted):

        def __init__(self, panel, parent=None):
            super(Column, self).__init__(parent)
            self.panel = panel
            window_flags(self, COLUMN)
            self.rebuilds = 0               # how often the still picture was drawn again
            self._cache = None
            self._cache_key = None
            self._failed = False

        def layout_(self):
            pn = self.panel
            return L.Layout(self.width(), self.height(), pn.current_rows(), pn.tab, pn.ui)

        def invalidate(self):
            self._cache_key = None
            self.update()

        # -- the mouse ---------------------------------------------------------
        def _pos(self, event):
            p = event.position() if hasattr(event, "position") else event.localPos()
            return p.x(), p.y()

        def _gy(self, event):
            g = event.globalPosition() if hasattr(event, "globalPosition") else event.screenPos()
            return g.y()

        def mousePressEvent(self, event):
            try:
                x, y = self._pos(event)
                pn = self.panel
                h = L.hit(self.layout_(), x, y, pn.scroll)
                if event.button() == Qt.RightButton:
                    if h and h[0] == "row":
                        g = event.globalPosition() if hasattr(event, "globalPosition") else event.screenPos()
                        pn.menu_at(h[1], QtCore.QPoint(int(g.x()), int(g.y())))
                    return
                if event.button() == Qt.LeftButton:
                    mods = event.modifiers()
                    pn.press(h, (x, y), self._gy(event), ctrl=bool(mods & Qt.ControlModifier),
                             shift=bool(mods & Qt.ShiftModifier))
            except Exception:                                # noqa: BLE001
                print(traceback.format_exc())

        def mouseMoveEvent(self, event):
            try:
                x, y = self._pos(event)
                pn = self.panel
                if pn.drag:
                    pn.drag_to(x, self._gy(event))
                    return
                h = L.hit(self.layout_(), x, y, pn.scroll)
                pn.hover_at(h)
                if h and h[0] == "grip":
                    self.setCursor(Qt.SizeVerCursor)
                elif h and (h[0] in ("tab", "lanes", "foot") or (h[0] == "row" and h[2] != "name")):
                    self.setCursor(Qt.PointingHandCursor)
                else:
                    self.unsetCursor()
                self.setToolTip(L.FOOT_TIPS.get(h[1], "") if h and h[0] == "foot" else "")
            except Exception:                                # noqa: BLE001
                print(traceback.format_exc())

        def mouseReleaseEvent(self, event):
            try:
                self.panel.release()
            except Exception:                                # noqa: BLE001
                print(traceback.format_exc())

        def hideEvent(self, event):
            self.panel._end_drag()
            super(Column, self).hideEvent(event)

        def event(self, event):
            if event.type() in (QtCore.QEvent.UngrabMouse, QtCore.QEvent.WindowDeactivate):
                try:
                    self.panel._end_drag()
                except Exception:                            # noqa: BLE001
                    print(traceback.format_exc())
            return super(Column, self).event(event)

        def leaveEvent(self, event):
            if not self.panel.drag:
                self.panel.hover_at(None)
            super(Column, self).leaveEvent(event)

        # -- painting ----------------------------------------------------------
        def _paint(self):
            pn = self.panel
            ui, tk = pn.ui, pn.tokens
            w, h = float(self.width()), float(self.height())
            lay = self.layout_()
            live = pn.live_units(lay)
            excluded = pn.excluded(lay)
            p = QtGui.QPainter(self)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            b = pn.burst if pn.motion else None
            age = pn._age(b) if b is not None else 0.0
            shape = None
            if b is not None:
                shape = shape_rect(b, age, w, h, ui)
                clip = QtGui.QPainterPath()
                r = 8 * ui
                clip.addRoundedRect(shape, r, r)
                p.setClipPath(clip)
            key = (self.width(), self.height(), ui, pn.tab, round(pn.scroll, 2),
                   L.signature(pn.current_rows()), tuple(pn.selected_names()), pn.picked_disp, pn.status, pn.lanes_on,
                   len(pn.rows["anim"]), len(pn.rows["disp"]), excluded, pn.weight_states())
            if key != self._cache_key or self._cache is None:
                pn._wstates = pn.weight_states()
                self.rebuilds += 1
                self._cache = self._picture(lay, excluded)
                self._cache_key = key
            p.drawPixmap(0, 0, self._cache)
            # what moves, over the picture
            if ("grip",) in live:
                self._grip(p, lay)
            well = qrect(lay.well)
            for uid in sorted(live, key=lambda u: (u[0] != "row", str(u))):
                if uid[0] == "grip":
                    continue
                if uid[0] == "row":
                    p.save()
                    p.setClipRect(well, Qt.IntersectClip)
                    self._unit(p, uid, lay, True)
                    p.restore()
                else:
                    self._unit(p, uid, lay, True)
            now = pn.clock()
            for g in pn.ghosts:
                if g["tab"] != pn.tab:
                    continue
                z, op = look.folding(now - g["t0"], 0.0)
                rect = qrect(g["rect"])
                p.save()
                p.setClipRect(well, Qt.IntersectClip)
                scaled(p, rect, z, op)
                self._row(p, g["index"], g["row"], g["rect"], [g["row"]], 0.0)
                p.restore()
                p.restore()
            # the reveal's top edge light
            if b is not None and b["open"] and age < look.REVEAL_MS and shape is not None:
                fade = max(0.0, 1.0 - age / float(look.REVEAL_MS)) ** 1.6
                p.setCompositionMode(QtGui.QPainter.CompositionMode_Plus)
                g = QtGui.QLinearGradient(0, shape.top(), 0, shape.top() + look.TOP_GLOW * ui)
                g.setColorAt(0.0, colour(tk["accent"], 255 * 0.4 * fade))
                g.setColorAt(1.0, colour(tk["accent"], 0))
                p.fillRect(QtCore.QRectF(shape.left(), shape.top(), shape.width(), look.TOP_GLOW * ui),
                           QtGui.QBrush(g))
                p.fillRect(QtCore.QRectF(shape.left(), shape.top(), shape.width(), 1.5 * ui),
                           colour(bar.RIM, 255 * 0.95 * fade))
                p.setCompositionMode(QtGui.QPainter.CompositionMode_SourceOver)
            p.end()

        def _picture(self, lay, excluded):
            """Everything at rest, into one picture: the parts a burst or a wave moves
            left out; what is lifted, popping or flashing is drawn over it each frame
            (the Timeline's way), so a hover never draws the picture again."""
            pn = self.panel
            ui, tk = pn.ui, pn.tokens
            ratio = self.devicePixelRatioF() or 1.0
            w, h = max(1, self.width()), max(1, self.height())
            pic = QtGui.QPixmap(int(round(w * ratio)), int(round(h * ratio)))
            pic.setDevicePixelRatio(ratio)
            pic.fill(Qt.transparent)
            p = QtGui.QPainter(pic)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            # the card
            p.setPen(QtGui.QPen(colour(tk["track_edge"]), 1))
            p.setBrush(colour(tk["panel"]))
            p.drawRoundedRect(QtCore.QRectF(0.5, 0.5, w - 1, h - 1), 8 * ui, 8 * ui)
            self._grip(p, lay, rest=True)
            # the head's track
            a, d = lay.segments["anim"], lay.segments["disp"]
            track = QtCore.QRectF(a[0], a[1], d[0] + d[2] - a[0], a[3]).adjusted(-2 * ui, -2 * ui, 2 * ui, 2 * ui)
            p.setPen(QtGui.QPen(colour(tk["track_edge"]), 1))
            p.setBrush(colour(tk["track"]))
            p.drawRoundedRect(track, 6 * ui, 6 * ui)
            # the well
            well = qrect(lay.well)
            p.setPen(QtGui.QPen(colour(tk["track_edge"]), 1))
            p.setBrush(colour(tk["field"]))
            p.drawRoundedRect(well, 6 * ui, 6 * ui)
            for uid, _rect in pn._column_parts(lay):
                if uid in excluded:
                    continue
                if uid[0] == "row":
                    p.save()
                    p.setClipRect(well, Qt.IntersectClip)
                    self._unit(p, uid, lay, False)
                    p.restore()
                else:
                    self._unit(p, uid, lay, False)
            # the scrollbar
            if lay.max_scroll > 0:
                wx, wy, ww, wh = lay.well
                bw = 3 * ui
                share = wh / float(wh + lay.max_scroll)
                bh = max(16 * ui, (wh - 4 * ui) * share)
                by = wy + 2 * ui + (wh - 4 * ui - bh) * (pn.scroll / lay.max_scroll)
                p.setPen(Qt.NoPen)
                p.setBrush(colour(tk["line"]))
                p.drawRoundedRect(QtCore.QRectF(wx + ww - bw - 2 * ui, by, bw, bh), bw / 2, bw / 2)
            # the line
            if pn.status:
                p.setPen(colour(tk["status_text"]))
                p.setFont(font(self, 11 * ui))
                r = qrect(lay.status)
                text = QtGui.QFontMetrics(p.font()).elidedText(pn.status, Qt.ElideRight, int(r.width()))
                p.drawText(r, Qt.AlignVCenter | Qt.AlignLeft, text)
            p.end()
            return pic

        def _grip(self, p, lay, rest=False):
            pn = self.panel
            ui, tk = pn.ui, pn.tokens
            held = pn.drag and pn.drag[0] == "grip"
            level = 0.0 if rest else (1.0 if held else pn.hover.get(("grip",), 0.0))
            bw = (34 + 12 * level) * ui
            rect = QtCore.QRectF((self.width() - bw) / 2.0, 3 * ui, bw, 3 * ui)
            p.save()
            if level > 0.01:
                p.setCompositionMode(QtGui.QPainter.CompositionMode_Plus)
                k.soft_dot(p, rect.center().x(), rect.center().y(), 18 * ui, tk["accent"], 110 * level)
                p.setCompositionMode(QtGui.QPainter.CompositionMode_SourceOver)
            p.setPen(Qt.NoPen)
            p.setBrush(blend(tk["line"], tk["accent"], level))
            p.drawRoundedRect(rect, 1.5 * ui, 1.5 * ui)
            p.restore()

        # -- one part, at rest or moving ---------------------------------------
        def _unit(self, p, uid, lay, moving):
            pn = self.panel
            ui = pn.ui
            scale, opacity = pn.burst_of(uid) if moving else (1.0, 1.0)
            if opacity <= 0.001:
                return
            if uid[0] == "row":
                i = uid[1]
                rows = pn.current_rows()
                if i >= len(rows):
                    return
                rect = lay.row_at(i, pn.scroll)
                scaled(p, qrect(rect), scale, opacity)
                self._row(p, i, rows[i], rect, rows, pn.hover.get(uid, 0.0) if moving else 0.0, moving)
                p.restore()
                return
            if uid[0] == "seg":
                rect = qrect(lay.segments[uid[1]])
            elif uid[0] == "lanes":
                rect = qrect(lay.lanes)
            else:
                rect = qrect(dict(lay.foot)[uid[1]])
            level = pn.hover.get(uid, 0.0) if moving else 0.0
            flash = pn.flash_of(uid) if moving else 0.0
            pop = pn.pop_of(uid) if moving else 1.0
            lift = 0.0 if uid[0] == "seg" else bar.LIFT * level
            z = scale * pop * (1.0 + lift) * (1.0 - 0.06 * flash)
            scaled(p, rect, z, opacity)
            if uid[0] == "seg":
                self._segment(p, uid[1], rect, level, flash)
            elif uid[0] == "lanes":
                self._lanes_button(p, rect, level, flash)
            else:
                self._foot(p, uid[1], rect, level, flash)
            p.restore()

        def _segment(self, p, tab, rect, level, flash):
            pn = self.panel
            ui, tk = pn.ui, pn.tokens
            lit = tab == pn.tab
            p.setPen(Qt.NoPen)
            if lit:
                p.setBrush(colour(tk["thumb"]))
                p.drawRoundedRect(rect, 5 * ui, 5 * ui)
            elif level > 0.01:
                p.setBrush(colour(tk["hover"], 255 * level))
                p.drawRoundedRect(rect, 5 * ui, 5 * ui)
            if flash > 0:
                p.setBrush(colour(tk["accent"], 255 * flash * 0.6))
                p.drawRoundedRect(rect, 5 * ui, 5 * ui)
            label = L.TAB_LABELS[tab]
            count = " %d" % len(pn.rows.get(tab, []))
            f1 = font(self, 12 * ui, bold=lit)
            f2 = font(self, 11 * ui, mono=True)
            m1, m2 = QtGui.QFontMetricsF(f1), QtGui.QFontMetricsF(f2)
            total = m1.horizontalAdvance(label) + m2.horizontalAdvance(count)
            x = rect.center().x() - total / 2.0
            base = rect.center().y() + m1.ascent() / 2.0 - m1.descent() / 2.0
            p.setFont(f1)
            p.setPen(colour(tk["text"]) if lit else blend(tk["muted"], tk["text"], level))
            p.drawText(QtCore.QPointF(x, base), label)
            p.setFont(f2)
            p.setPen(colour(tk["faint"]))
            p.drawText(QtCore.QPointF(x + m1.horizontalAdvance(label), base), count)

        def _lanes_button(self, p, rect, level, flash):
            pn = self.panel
            ui, tk = pn.ui, pn.tokens
            on = pn.lanes_on and pn.tab == "anim"
            if pn.tab != "anim":
                p.setOpacity(p.opacity() * 0.35)
                level = 0.0
            if on:
                face = colour(tk["accent_tint"])
            else:
                face = colour(tk["hover"], 255 * level)
            if flash > 0:
                face = blend(face.name(), tk["accent"], flash)
            p.setPen(Qt.NoPen)
            p.setBrush(face)
            p.drawRoundedRect(rect, 5 * ui, 5 * ui)
            glow(p, rect, 5 * ui, tk["accent"], level, ui)
            ink = colour(tk["accent"]) if on else blend(tk["muted"], tk["text"], level)
            side = 15 * ui
            c = rect.center()
            draw_glyph(p, "lanes", QtCore.QRectF(c.x() - side / 2, c.y() - side / 2, side, side), ink)

        def _foot(self, p, name, rect, level, flash):
            pn = self.panel
            ui, tk = pn.ui, pn.tokens
            side = 15 * ui
            p.setPen(Qt.NoPen)
            if name == "add":
                face = blend(tk["accent"], tk["accent_hover"], level)
                if flash > 0:
                    face = blend(face.name(), bar.RIM, flash * 0.5)
                p.setBrush(face)
                p.drawRoundedRect(rect, 5 * ui, 5 * ui)
                glow(p, rect, 5 * ui, bar.RIM, level, ui)
                ink = colour(tk["on_accent"])
                f = font(self, 12 * ui, bold=True)
                text = "Layer"
                tw = QtGui.QFontMetricsF(f).horizontalAdvance(text)
                x = rect.center().x() - (side + 3 * ui + tw) / 2.0
                draw_glyph(p, "plus", QtCore.QRectF(x, rect.center().y() - side / 2, side, side), ink)
                p.setFont(f)
                p.setPen(ink)
                p.drawText(QtCore.QRectF(x + side + 3 * ui, rect.top(), tw + 2 * ui, rect.height()),
                           Qt.AlignVCenter | Qt.AlignLeft, text)
                return
            face = colour(tk["hover"], 255 * level)
            if flash > 0:
                face = blend(face.name(), tk["accent"], flash)
            p.setBrush(face)
            p.drawRoundedRect(rect, 5 * ui, 5 * ui)
            glow(p, rect, 5 * ui, tk["accent"], level, ui)
            if flash > 0.5:
                ink = colour(tk["on_accent"])
            elif name == "delete" and level > 0.01:
                ink = blend(tk["muted"], tk["danger"], level)
            else:
                ink = blend(tk["muted"], tk["text"], level)
            c = rect.center()
            draw_glyph(p, FOOT_GLYPHS.get(name, name), QtCore.QRectF(c.x() - side / 2, c.y() - side / 2, side, side),
                       ink)

        # -- a row -------------------------------------------------------------
        def _row(self, p, i, row, rect, rows, level, moving=False):
            pn = self.panel
            ui, tk = pn.ui, pn.tokens
            tab = "anim" if "mode" in row else "disp"
            r = qrect(rect)
            lit = row.get("active") if tab == "anim" else row.get("name") == pn.picked_disp
            if tab == "anim":
                dim = L.dimmed(row, rows)
            else:
                dim = not row.get("visible", True)
            p.setPen(Qt.NoPen)
            #  every selected layer wears the accent frame (2026-10-19: «оранжевая рамка должна быть
            #  ... на всех выделенных»); the active one keys go to also has its name lit
            if lit or (tab == "anim" and row.get("name") in pn.selected_names()):
                p.setBrush(colour(tk["card_active"]))
                p.setPen(QtGui.QPen(colour(tk["accent"]), 1.5 * ui))
                p.drawRoundedRect(r.adjusted(0.75 * ui, 0.75 * ui, -0.75 * ui, -0.75 * ui), 5 * ui, 5 * ui)
            else:
                p.setBrush(blend(tk["card"], tk["hover"], level))
                p.drawRoundedRect(r, 5 * ui, 5 * ui)
            parts = L.row_parts(rect, tab, ui, base=row.get("base"))
            p.save()
            if dim:
                p.setOpacity(p.opacity() * DIM)
            if tab == "anim":
                mr = qrect(parts["mode"])
                p.setPen(QtGui.QPen(colour(tk["line"]), 1))
                p.setBrush(Qt.NoBrush)
                p.drawRoundedRect(mr, 3 * ui, 3 * ui)
                p.setFont(font(self, 9 * ui, mono=True))
                p.setPen(colour(tk["faint"]))
                p.drawText(mr, Qt.AlignCenter, L.MODES.get(row.get("mode"), ""))
                if "weight" in parts:
                    wr = qrect(parts["weight"])
                    p.setPen(QtGui.QPen(colour(tk["track_edge"]), 1))
                    p.setBrush(colour(tk["track"]))
                    p.drawRoundedRect(wr, wr.height() / 2, wr.height() / 2)
                    weight = max(0.0, min(1.0, float(row.get("weight", 1.0))))
                    if weight > 0:
                        fill = QtCore.QRectF(wr.left() + 1.5 * ui, wr.top() + 1.5 * ui,
                                             max(0.0, (wr.width() - 3 * ui) * weight), wr.height() - 3 * ui)
                        p.setPen(Qt.NoPen)
                        p.setBrush(colour(tk["accent"]))
                        p.drawRoundedRect(fill, fill.height() / 2, fill.height() / 2)
                    p.setFont(font(self, 10 * ui, mono=True))
                    p.setPen(colour(tk["accent_text"] if row.get("weight_keyed") else tk["text2"]))
                    p.drawText(qrect(parts["wnum"]), Qt.AlignCenter, "%.2f" % weight)
                if "wkey" in parts:
                    self._wkey(p, i, parts["wkey"], L.weight_state(row, pn.now()), moving)
                for name in ("mute", "solo", "lock"):
                    if name in parts:
                        self._toggle(p, i, name, qrect(parts[name]), bool(row.get(name)), moving)
            else:
                sr = qrect(parts["swatch"])
                p.setPen(QtGui.QPen(colour(tk["track_edge"]), 1))
                p.setBrush(colour(row.get("colour") or tk["line"]))
                p.drawRoundedRect(sr, 3 * ui, 3 * ui)
                for name in ("visible", "playback", "type"):
                    on = bool(row.get(name)) if name != "type" else bool(row.get("type"))
                    self._toggle(p, i, name, qrect(parts[name]), on, moving, row=row)
            # the name
            nr = qrect(parts["name"])
            f = font(self, 12.5 * ui, bold=lit)
            metrics = QtGui.QFontMetricsF(f)
            text = metrics.elidedText(row.get("label", row.get("name", "")), Qt.ElideRight, nr.width())
            p.setFont(f)
            p.setPen(colour(tk["accent_text"]) if lit else colour(tk["text"]))
            p.drawText(nr, Qt.AlignVCenter | Qt.AlignLeft, text)
            if dim:
                y = nr.center().y() + 0.5 * ui
                p.setPen(QtGui.QPen(colour(tk["text"]), max(1.0, ui)))
                p.drawLine(QtCore.QPointF(nr.left(), y), QtCore.QPointF(nr.left() + metrics.horizontalAdvance(text), y))
            p.restore()

        def _wkey(self, p, i, rect, state, moving):
            """The weight's key cell, the Channel Box's: filled on a key at this frame,
            outlined when the weight has keys elsewhere, an empty well unkeyed."""
            pn = self.panel
            ui, tk = pn.ui, pn.tokens
            uid = ("ctl", i, "wkey")
            level = pn.hover.get(uid, 0.0) if moving else 0.0
            pop = pn.pop_of(uid) if moving else 1.0
            cell = qrect(L.wkey_cell(rect, ui))
            z = pop * (1.0 + 0.35 * level)
            scaled(p, cell, z, 1.0)
            r = 2 * ui
            if state == "onkey":
                p.setPen(Qt.NoPen)
                p.setBrush(colour(tk["accent"]))
                p.drawRoundedRect(cell, r, r)
            elif state == "keyed":
                p.setPen(QtGui.QPen(colour(tk["accent"]), 1.5 * ui))
                p.setBrush(Qt.NoBrush)
                p.drawRoundedRect(cell.adjusted(0.75 * ui, 0.75 * ui, -0.75 * ui, -0.75 * ui), r, r)
            else:
                p.setBrush(colour(tk["track"]))
                p.setPen(QtGui.QPen(colour(tk["track_edge"]), 1))
                p.drawRoundedRect(cell, r, r)
            glow(p, cell, r, tk["accent"], level, ui)
            p.restore()

        def _toggle(self, p, i, name, rect, on, moving, row=None):
            pn = self.panel
            ui, tk = pn.ui, pn.tokens
            uid = ("ctl", i, name)
            level = pn.hover.get(uid, 0.0) if moving else 0.0
            pop = pn.pop_of(uid) if moving else 1.0
            z = pop * (1.0 + bar.LIFT * level)
            scaled(p, rect, z, 1.0)
            lit = {"mute": (MUTE_FACE, tk["danger"]), "solo": (SOLO_FACE, bar.HIGHLIGHT),
                   "lock": (tk["accent_tint"], tk["accent"])}.get(name, (tk["accent_tint"], tk["accent_text"]))
            face = colour(lit[0]) if on else colour(tk["hover"], 255 * level)
            p.setPen(Qt.NoPen)
            p.setBrush(face)
            p.drawRoundedRect(rect, 5 * ui, 5 * ui)
            glow(p, rect, 5 * ui, tk["accent"], level, ui)
            ink = colour(lit[1]) if on else blend(tk["muted"], tk["text"], level)
            if name == "lock":
                side = 13 * ui
                c = rect.center()
                draw_glyph(p, "lock", QtCore.QRectF(c.x() - side / 2, c.y() - side / 2, side, side), ink)
            else:
                letter = {"mute": "M", "solo": "S", "visible": "V", "playback": "P"}.get(name)
                if name == "type":
                    letter = L.TYPES[int(row.get("type", 0)) % len(L.TYPES)] or "–"
                p.setFont(font(self, 11 * ui, bold=True))
                p.setPen(ink)
                p.drawText(rect, Qt.AlignCenter, letter)
            p.restore()

    # -- the lanes ---------------------------------------------------------------

    class LaneKeys(QtCore.QObject):
        """S on the lanes (the timeline's DragKeys): during a drag a held button keeps the
        key from Maya's hotkeys, so it is caught application-wide; with no drag, S over a
        lane block of two frames or more keys every frame of it."""

        def __init__(self, panel, parent=None):
            super(LaneKeys, self).__init__(parent)
            self.panel = panel

        def eventFilter(self, obj, event):
            try:
                kind = event.type()
                override = kind == QtCore.QEvent.ShortcutOverride
                if kind != QtCore.QEvent.KeyPress and not override:
                    return False
                if int(event.key()) != int(Qt.Key_S):
                    return False
                if event.modifiers() & (Qt.ControlModifier | Qt.AltModifier | Qt.ShiftModifier):
                    return False
                pn = self.panel
                if pn.lane_drag:
                    if override or event.isAutoRepeat():
                        event.accept()
                        return True
                    return bool(pn.lane_stamp())
                #  no drag: a lane block takes S (`keys_block`), as a timeline highlight
                #  does - unless the key goes into a text field
                if pn.keys_block() is None:
                    return False
                focus = QtWidgets.QApplication.focusWidget()
                if focus is not None and isinstance(focus, (QtWidgets.QLineEdit, QtWidgets.QTextEdit,
                                                            QtWidgets.QPlainTextEdit, QtWidgets.QAbstractSpinBox)):
                    return False
                if override or event.isAutoRepeat():
                    event.accept()
                    return True
                return bool(pn.lane_key_range())
            except Exception:                                # noqa: BLE001
                print(traceback.format_exc())
                return False

    class Lanes(Painted):

        def __init__(self, panel, parent=None):
            super(Lanes, self).__init__(parent)
            self.panel = panel
            window_flags(self, LANES)
            self._cache = None
            self._cache_key = None
            self.rebuilds = 0               # how often the still picture was drawn again
            self._failed = False
            self._menu_at = None
            self.setMouseTracking(True)
            self.menu_wait = QtCore.QTimer(self)     # the key menu, opened once no second press came
            self.menu_wait.setSingleShot(True)
            self.menu_wait.timeout.connect(self._open_menu)
            self.keys_catcher = LaneKeys(panel, self)
            QtWidgets.QApplication.instance().installEventFilter(self.keys_catcher)

        def invalidate(self):
            self._cache_key = None
            self.update()

        def _track(self):
            try:
                return self.panel.strip.track()
            except Exception:                                # noqa: BLE001
                return None

        def _xy(self, event):
            p = event.position() if hasattr(event, "position") else event.localPos()
            return p.x(), p.y()

        def _global(self, event):
            g = event.globalPosition() if hasattr(event, "globalPosition") else event.screenPos()
            return QtCore.QPoint(int(g.x()), int(g.y()))

        def double_window(self):
            try:
                return min(QtWidgets.QApplication.doubleClickInterval(), look.RIGHT_DOUBLE_MS)
            except Exception:                                # noqa: BLE001
                return look.RIGHT_DOUBLE_MS

        def _open_menu(self):
            pending, self._menu_at = self._menu_at, None
            if pending is not None:
                self.panel.lane_menu_at(pending[0], pending[1])

        def mousePressEvent(self, event):
            try:
                x, y = self._xy(event)
                pn = self.panel
                button, mods = event.button(), event.modifiers()
                if button == Qt.RightButton:
                    self._menu_at = (y, self._global(event))
                    self.menu_wait.start(self.double_window())
                elif button == Qt.MiddleButton:
                    pn.lane_press(x, y, middle=True)
                elif button == Qt.LeftButton:
                    pn.lane_press(x, y, shift=bool(mods & Qt.ShiftModifier))
            except Exception:                                # noqa: BLE001
                print(traceback.format_exc())

        def mouseDoubleClickEvent(self, event):
            """A double click, left or right, highlights every key of the lane."""
            try:
                self.menu_wait.stop()
                self._menu_at = None
                pn = self.panel
                if pn.lane_drag:
                    pn.lane_release()
                pn.lane_all(self._xy(event)[1])
            except Exception:                                # noqa: BLE001
                print(traceback.format_exc())

        def mouseMoveEvent(self, event):
            try:
                x, y = self._xy(event)
                pn = self.panel
                if pn.lane_drag:
                    pn.lane_move(x, y)
                    return
                #  the timeline's cursors: an open hand over what a press grabs
                what = pn.lane_aim(x, y)
                self.setCursor(Qt.OpenHandCursor if what == "grab" else Qt.SizeHorCursor)
            except Exception:                                # noqa: BLE001
                print(traceback.format_exc())

        def leaveEvent(self, event):
            try:
                if self.panel.lane_aimed is not None:
                    self.panel.lane_aimed = None
                    self.update()
            except Exception:                                # noqa: BLE001
                print(traceback.format_exc())

        def mouseReleaseEvent(self, event):
            try:
                self.panel.lane_release()
            except Exception:                                # noqa: BLE001
                print(traceback.format_exc())

        def event(self, event):
            if event.type() in (QtCore.QEvent.UngrabMouse, QtCore.QEvent.WindowDeactivate):
                try:
                    if self.panel.lane_drag:
                        self.panel.lane_release()
                except Exception:                            # noqa: BLE001
                    print(traceback.format_exc())
            return super(Lanes, self).event(event)

        def _shape(self, w, h, ui):
            path = QtGui.QPainterPath()
            r = 8 * ui
            path.moveTo(w, 0)
            path.lineTo(r, 0)
            path.quadTo(0, 0, 0, r)
            path.lineTo(0, h - r)
            path.quadTo(0, h, r, h)
            path.lineTo(w, h)
            path.closeSubpath()
            return path

        def _paint(self):
            pn = self.panel
            ui, tk = pn.ui, pn.tokens
            w, h = float(self.width()), float(self.height())
            lay = pn.column.layout_()
            t = self._track()
            p = QtGui.QPainter(self)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            b = pn.lanes_burst if pn.motion else None
            if b is not None:
                age = pn._age(b)
                if b["open"]:
                    e = look.ease_out_quint(age / float(look.UNROLL_MS))
                else:
                    e = 1.0 - look.ease_in_quint((age - b["close_at"]) / float(look.CLOSE_MS))
                clip = QtGui.QPainterPath()
                clip.addRect(QtCore.QRectF(w * (1 - e), 0, w * e, h))
                p.setClipPath(clip)
            tkey = (t.v0, t.v1, t.left, t.right) if t is not None else None
            keys_sig = tuple(sorted((n, tuple(v)) for n, v in pn.keys.items()))
            sel = pn.lane_sel
            sel_key = (sel["a"], sel["b"], tuple(sel["names"])) if sel else None
            dragging = pn.lane_preview is not None and bool(sel)
            view = pn.drag_view()
            view_key = (tuple(view["names"]), tuple(view["span"])) if view else None
            key = (self.width(), self.height(), ui, round(pn.scroll, 2), L.signature(pn.rows["anim"]),
                   keys_sig, tkey, b is not None, sel_key, dragging, view_key, self._active_hex())
            if b is not None:
                self._draw(p, lay, t, w, h, True)
                self._draw_dragged(p, lay, t, w)
            else:
                if key != self._cache_key or self._cache is None:
                    ratio = self.devicePixelRatioF() or 1.0
                    pic = QtGui.QPixmap(int(round(max(1, w) * ratio)), int(round(max(1, h) * ratio)))
                    pic.setDevicePixelRatio(ratio)
                    pic.fill(Qt.transparent)
                    q = QtGui.QPainter(pic)
                    q.setRenderHint(QtGui.QPainter.Antialiasing)
                    self._draw(q, lay, t, w, h, False)
                    q.end()
                    self._cache, self._cache_key = pic, key
                    self.rebuilds += 1
                p.drawPixmap(0, 0, self._cache)
                self._draw_dragged(p, lay, t, w)
            # the highlight's first and last frame over the ruler (2026-10-20)
            #  at the block's edges, on its top lane, as on the timeline (2026-10-20:
            #  «там же где и на таймлайне возле концов рамки а не там где корректа»)
            if t is not None and sel:
                tops = [lane.top() for _i, row, lane, _s, _o in self._lanes_of(lay, t, False)
                        if row["name"] in sel["names"]]
                if tops:
                    span = pn.lane_preview if dragging else (sel["a"], sel["b"])
                    well = qrect(lay.well)
                    p.save()
                    p.setClipRect(QtCore.QRectF(0, well.top(), w, well.height()), Qt.IntersectClip)
                    k.draw_span_labels(p, t, span, min(tops) + 2.5 * ui, w, ui, pn.tokens)
                    p.restore()
            # the playhead's cell through every lane
            if t is not None:
                try:
                    now = float(pn.strip.now())
                except Exception:                            # noqa: BLE001
                    now = None
                if now is not None:
                    x0, x1 = t.cell(now) if t.cells else (t.x(now) - 1, t.x(now) + 1)
                    well = lay.well
                    p.setPen(Qt.NoPen)
                    p.setBrush(colour(tk["accent"], 255 * 0.2))
                    p.drawRect(QtCore.QRectF(x0, well[1], max(1.0, x1 - x0), well[3]))
                    self._flag(p, lay, t, now, x0, x1, w)
                self._aimed(p, lay, t)
            p.end()

        def _flag(self, p, lay, t, now, x0, x1, w):
            """The playhead's frame on a flag over the ruler, as on the timeline's caret."""
            pn = self.panel
            ui, tk = pn.ui, pn.tokens
            f = font(self, 10 * ui, mono=True, bold=True)
            p.setFont(f)
            text = look.frame_text(now)
            tw = QtGui.QFontMetricsF(f).horizontalAdvance(text) + 8 * ui
            fh = 13 * ui
            cx = (x0 + x1) / 2.0
            left = max(0.0, min(w - tw, cx - tw / 2.0))
            top = lay.head[1] + lay.head[3] - fh - 1 * ui
            r = QtCore.QRectF(left, top, tw, fh)
            p.setPen(Qt.NoPen)
            p.setBrush(colour(tk["accent"]))
            p.drawRoundedRect(r, 3 * ui, 3 * ui)
            p.setPen(colour(tk["panel"]))
            p.drawText(r, Qt.AlignCenter, text)

        def _aimed(self, p, lay, t):
            """The key under the mouse lifted and lit, as on the timeline."""
            pn = self.panel
            aim = pn.lane_aimed
            if not aim or pn.lane_drag:
                return
            rows = pn.rows["anim"]
            index = next((i for i, r in enumerate(rows) if r["name"] == aim[0]), None)
            if index is None or index not in pn._visible_rows(lay):
                return
            ui, tk = pn.ui, pn.tokens
            r = lay.row_at(index, pn.scroll)
            top, bottom = r[1] + 4 * ui, r[1] + r[3] - 4 * ui
            well = qrect(lay.well)
            p.save()
            p.setClipRect(QtCore.QRectF(0, well.top(), float(self.width()), well.height()))
            rect = _key_rect(t, aim[1], top, bottom, ui, KEY_LIFT)
            glow(p, rect, 2 * ui, tk["accent"], 1.0, ui)
            p.setPen(Qt.NoPen)
            p.setBrush(colour(tk["accent_text"]))
            p.drawRoundedRect(rect, 1.5 * ui, 1.5 * ui)
            p.restore()

        def _lanes_of(self, lay, t, moving):
            """(row index, row, lane rect, scale, opacity) of every lane shown."""
            pn = self.panel
            rows = pn.rows["anim"]
            out = []
            for i in pn._visible_rows(lay):
                if i >= len(rows):
                    continue
                r = lay.row_at(i, pn.scroll)
                lane = QtCore.QRectF(t.left, r[1], max(1.0, t.right - t.left), r[3])
                scale, opacity = pn.lane_of(i) if moving else (1.0, 1.0)
                if opacity > 0.001:
                    out.append((i, rows[i], lane, scale, opacity))
            return out

        def _active_hex(self):
            """The active lane's keys: the Time Bar's own colour (steel with Steel keys)."""
            key_hex = getattr(self.panel.strip, "key_hex", None)
            return key_hex() if key_hex is not None else self.panel.tokens["accent"]

        def _key_colour(self, row):
            tk = self.panel.tokens
            if row.get("active"):
                return colour(self._active_hex())
            if row.get("base"):
                return colour(tk["faint"])
            return colour(tk["muted"])

        def _ingot_hex(self, row):
            """The active lane's colour when its keys are steel ingots (Steel keys,
            2026-10-20), else None."""
            if row.get("active") and getattr(self.panel.strip, "steel", False):
                return self._active_hex()
            return None

        def _keys(self, p, t, lane, frames, ui, ingot_hex=None):
            """Each key its own rounded rect: one path of hundreds of rounded rects fills
            ~30x slower in Qt (9 ms against 0.3 for 200 keys, measured 2026-10-19 - the lanes
            drag dropped to 10 frames a second). Each frame once."""
            top, bottom = lane.top() + 4 * ui, lane.bottom() - 4 * ui
            drawn = set()
            for frame in frames:
                if not (t.v0 - 1 <= frame <= t.v1 + 1) or round(frame, 4) in drawn:
                    continue
                drawn.add(round(frame, 4))
                rect = _key_rect(t, frame, top, bottom, ui, 1.0)
                if ingot_hex and t.cells and look.on_frame(frame):
                    brush = p.brush()
                    k.ingot(p, rect, ingot_hex, ui)
                    p.setBrush(brush)
                    continue
                p.drawRoundedRect(rect, 1.5 * ui, 1.5 * ui)

        def _block(self, p, t, lane, span, ui):
            a, b = span
            block = QtCore.QRectF(t.x(a), lane.top() + 1.5 * ui, max(2.0, t.end(b) - t.x(a)),
                                  lane.height() - 3 * ui)
            p.setBrush(colour(bar.HIGHLIGHT, 0x4a))
            p.setPen(QtGui.QPen(colour(bar.HIGHLIGHT), 1.5 * ui))
            p.drawRoundedRect(block, 3 * ui, 3 * ui)
            p.setPen(Qt.NoPen)

        def _draw(self, p, lay, t, w, h, moving):
            """The still picture: the face, the ruler, every lane with its keys. While a key
            drag stands, the dragged lanes' block and the keys in it are left to
            `_draw_dragged`, drawn over the picture on every step (the picture is made once
            a drag, not on every mouse move)."""
            pn = self.panel
            ui, tk = pn.ui, pn.tokens
            p.setPen(Qt.NoPen)
            p.setBrush(colour(LANE_FACE, 255 * 0.95))
            p.drawPath(self._shape(w, h, ui))
            if t is None:
                return
            # the ruler, on the timeline's frames
            head = lay.head
            font_ = font(self, 10 * ui, mono=True)
            p.setFont(font_)
            metrics = QtGui.QFontMetricsF(font_)
            tick_y = head[1] + head[3]
            tall_of = {"label": 7 * ui, "mid": 4.5 * ui, "tick": 2.7 * ui}
            for frame, kind in look.ticks(t, ui):
                x = round(t.x(frame))
                if x < 0 or x > w:
                    continue
                p.setPen(Qt.NoPen)
                p.setBrush(colour(tk["muted"] if kind == "label" else tk["line"]))
                p.drawRect(QtCore.QRectF(x, tick_y - tall_of[kind], max(1.0, ui * 0.75), tall_of[kind]))
                if kind == "label":
                    text = look.frame_text(frame)
                    if x + 3 * ui + metrics.horizontalAdvance(text) <= w - 2 * ui:
                        p.setPen(colour(tk["faint"]))
                        p.drawText(QtCore.QPointF(x + 3 * ui, head[1] + metrics.ascent()), text)
            # one lane a row, at the row's own height
            rows = pn.rows["anim"]
            well = qrect(lay.well)
            sel = pn.lane_sel
            dragging = pn.lane_preview is not None and bool(sel)
            view = pn.drag_view()                # a key drag here, or the timeline's
            p.save()
            p.setClipRect(QtCore.QRectF(0, well.top(), w, well.height()), Qt.IntersectClip)
            for i, row, lane, scale, opacity in self._lanes_of(lay, t, moving):
                scaled(p, lane, scale, opacity)
                if L.dimmed(row, rows):
                    p.setOpacity(p.opacity() * DIM)
                p.setPen(Qt.NoPen)
                p.setBrush(colour(tk["field"]))
                p.drawRoundedRect(lane, 4 * ui, 4 * ui)
                mine = bool(sel) and row["name"] in sel["names"]
                carried = bool(view) and row["name"] in view["names"]
                if mine and not dragging:
                    self._block(p, t, lane, (sel["a"], sel["b"]), ui)
                keys = pn.keys.get(row["name"], [])
                if carried:                      # drawn where the drag has them, over the picture
                    keys = [k for k in keys if not look.inside(k, view["span"])]
                p.setBrush(self._key_colour(row))
                self._keys(p, t, lane, keys, ui, self._ingot_hex(row))
                wkeys = row.get("weight_keys") or ()
                if mine and dragging:            # a dragged L key moves with the block
                    wkeys = [k for k in wkeys if not look.inside(k, (sel["a"], sel["b"]))]
                self._weight_keys(p, t, lane, wkeys, ui)
                p.restore()
            p.restore()

        def _weight_keys(self, p, t, lane, frames, ui):
            """The layer's own weight keys on its lane, each a key marked L (2026-10-20:
            «ключик в котором проанимирован слой будем отмечать буквой L»)."""
            if not frames:
                return
            tk = self.panel.tokens
            f = font(self, 9 * ui, bold=True)
            fm = QtGui.QFontMetricsF(f)
            least = fm.horizontalAdvance(L.WKEY_LETTER) + 4 * ui
            top, bottom = lane.top() + 4 * ui, lane.bottom() - 4 * ui
            p.save()
            p.setFont(f)
            for frame in sorted(set(round(float(k), 4) for k in frames)):
                if not (t.v0 - 1 <= frame <= t.v1 + 1):
                    continue
                rect = _key_rect(t, frame, top, bottom, ui, 1.0)
                if rect.width() < least:
                    c = rect.center()
                    rect = QtCore.QRectF(c.x() - least / 2.0, rect.top(), least, rect.height())
                p.setPen(Qt.NoPen)
                p.setBrush(colour(tk["accent_text"]))
                p.drawRoundedRect(rect, 1.5 * ui, 1.5 * ui)
                p.setPen(colour(tk["on_accent"]))
                p.drawText(rect, Qt.AlignCenter, L.WKEY_LETTER)
            p.restore()

        def _draw_dragged(self, p, lay, t, w):
            """Over the still picture while a key drag stands: each dragged lane's block
            where the drag has it, its keys there, and the copies S put down."""
            pn = self.panel
            view = pn.drag_view()                # a key drag here, or the timeline's
            if t is None or not view:
                return
            ui = pn.ui
            rows = pn.rows["anim"]
            span, preview, carried = view["span"], view["target"], view["carried"]
            well = qrect(lay.well)
            p.save()
            p.setClipRect(QtCore.QRectF(0, well.top(), w, well.height()), Qt.IntersectClip)
            for i, row, lane, _scale, _opacity in self._lanes_of(lay, t, False):
                if row["name"] not in view["names"]:
                    continue
                p.save()
                if L.dimmed(row, rows):
                    p.setOpacity(p.opacity() * DIM)
                self._block(p, t, lane, preview, ui)
                frames = []
                for key in pn.keys.get(row["name"], []):
                    if look.inside(key, span):
                        #  where the drag has it, and a copy S put down where it went down
                        frames.extend(look.shown_at(key, span, preview, carried))
                p.setBrush(self._key_colour(row))
                self._keys(p, t, lane, frames, ui, self._ingot_hex(row))
                p.restore()
            p.restore()

    def _key_rect(t, frame, top, bottom, ui, z):
        """A key's mark as the timeline draws it: its cell on a whole frame, a line
        between frames; `z` grows it about its middle (the lift under the mouse)."""
        if look.on_frame(frame) and t.cells:
            l, tp, kw, kh = look.key_cell(t.x(frame), t.scale, top, bottom, ui)
        else:
            kw = bar.KEY_W * ui * bar.DASH_W
            l, tp, kh = t.x(frame) - kw / 2, top, bottom - top
        cx, cy = l + kw / 2.0, tp + kh / 2.0
        kw, kh = kw * z, kh * min(z, 1.15)
        return QtCore.QRectF(cx - kw / 2, cy - kh / 2, kw, kh)

    def _key_shape(path, t, frame, top, bottom, ui, z):
        path.addRoundedRect(_key_rect(t, frame, top, bottom, ui, z), 1.5 * ui, 1.5 * ui)

    _CLASSES.append((Column, Lanes, NameField))
    return _CLASSES[0]
