"""The Time Bar's layer panel (2026-10-18): a painted column of animation and display
layers on the bar's right, resizable by its top edge, and lanes of each layer's keys
over the timeline. Two frameless Qt.Tool windows of ours; all painting is ours.

The animator: «передвинем меню слоев в правую часть таймлайна» and «опциональную кнопку
которая будет выдвигать панель как в варианте B». The column opens out of the bar's
layers pill and folds back into it; the lanes come out of the column's left edge.
The data is the link's at once; only the picture moves (docs/interface-motion.md).

Spec: docs/superpowers/specs/2026-10-18-time-bar-layer-panel-design.md
"""

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
LANE_FACE = "#141517"
MUTE_FACE = "#3a2626"   # M lit
SOLO_FACE = "#23324a"   # S lit
BOX = (28, 20)          # logical px: the shape a burst unrolls from
TOGGLES = ("mute", "solo", "lock", "visible", "playback", "type")
FOOT_GLYPHS = {"add": "plus", "addsel": "addsel", "remsel": "remsel", "merge": "merge",
               "select": "select", "delete": "trash"}
#  Maya's display layer palette: the colour index a layer takes (1..31)
COLOUR_INDICES = tuple(range(1, 32))


def destroy_all():
    """Every column and lanes window by name - an older module's too (trap 102)."""
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
        self.keys = {}
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
        self.refresh(force=True)
        refresh = getattr(self.strip, "refresh", None)
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
        self.keys = self._call("keys_by_layer", [r["name"] for r in self.rows["anim"]]) or {}
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
            height = L.clamp_height(self.height * 1.0, self.strip.top_room())
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
    def refresh(self, force=False):
        anim = self._call("anim_layers") or []
        disp = self._call("display_layers") or []
        sigs = (L.signature(anim), L.signature(disp))
        if force or sigs != self._sigs:
            self._sigs = sigs
            self.rows = {"anim": anim, "disp": disp}
            if self.picked_disp not in [r["name"] for r in disp]:
                self.picked_disp = None
            self._clamp_scroll()
            self.column.invalidate()
        if self._lanes_shown():
            self.keys = self._call("keys_by_layer", [r["name"] for r in self.rows["anim"]]) or {}
            self.lanes.invalidate()

    def keys_dirty(self):
        if self._lanes_shown():
            self.keys = self._call("keys_by_layer", [r["name"] for r in self.rows["anim"]]) or {}
            self.lanes.invalidate()

    def on_time(self):
        """The lanes' playhead cell: repainted now, not on an idle (trap 269)."""
        if self._lanes_shown():
            self.lanes.repaint()

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
    def press(self, hit, pos=None, gy=None):
        """A left press on the column at `hit` (layerlook.hit)."""
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
            self.drag = ("grip", float(gy if gy is not None else 0.0), float(self.column.height()))
            self.column.update()
        elif kind == "foot":
            self.flashes[("foot", hit[1])] = self.clock()
            self._foot(hit[1], lay)
        elif kind == "row":
            self._row_press(hit[1], hit[2], lay, pos)
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

    def _row_press(self, i, part, lay, pos):
        rows = self.current_rows()
        if i >= len(rows):
            return
        row = rows[i]
        name = row["name"]
        if part == "name" or part in ("mode", "swatch"):
            if self.tab == "anim":
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
            self.height = L.clamp_height(h0 - (gy - gy0), self.strip.top_room())
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
                        ("Merge down", None), ("Delete", None)]
            lay = self.column.layout_()
            return [("Additive", lambda: self._write("set_mode", name, "add"), row.get("mode") == "add"),
                    ("Override", lambda: self._write("set_mode", name, "ovr"), row.get("mode") == "ovr"),
                    None,
                    ("Rename", lambda: self.start_rename(i)),
                    ("Select objects", lambda: self._write("select_objects", name)),
                    ("Add selection", lambda: self._write("add_selection", name)),
                    ("Remove selection", lambda: self._write("remove_selection", name)),
                    None,
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
        for timer in (self.driver, self.placer, self.status_timer):
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
                    pn.press(h, (x, y), self._gy(event))
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
                   L.signature(pn.current_rows()), pn.picked_disp, pn.status, pn.lanes_on,
                   len(pn.rows["anim"]), len(pn.rows["disp"]), excluded)
            if key != self._cache_key or self._cache is None:
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
            if lit:
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

    class Lanes(Painted):

        def __init__(self, panel, parent=None):
            super(Lanes, self).__init__(parent)
            self.panel = panel
            window_flags(self, LANES)
            self._cache = None
            self._cache_key = None
            self._failed = False

        def invalidate(self):
            self._cache_key = None
            self.update()

        def _track(self):
            try:
                return self.panel.strip.track()
            except Exception:                                # noqa: BLE001
                return None

        def mousePressEvent(self, event):
            try:
                if event.button() != Qt.LeftButton:
                    return
                p = event.position() if hasattr(event, "position") else event.localPos()
                pn = self.panel
                lay = pn.column.layout_()
                for i in pn._visible_rows(lay):
                    r = lay.row_at(i, pn.scroll)
                    if r[1] <= p.y() < r[1] + r[3]:
                        rows = pn.rows["anim"]
                        if i < len(rows):
                            pn._write("pick", rows[i]["name"])
                        return
            except Exception:                                # noqa: BLE001
                print(traceback.format_exc())

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
            key = (self.width(), self.height(), ui, round(pn.scroll, 2), L.signature(pn.rows["anim"]),
                   keys_sig, tkey, b is not None)
            if b is not None:
                self._draw(p, lay, t, w, h, True)
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
                p.drawPixmap(0, 0, self._cache)
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
            p.end()

        def _draw(self, p, lay, t, w, h, moving):
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
            p.save()
            p.setClipRect(QtCore.QRectF(0, well.top(), w, well.height()), Qt.IntersectClip)
            for i in pn._visible_rows(lay):
                if i >= len(rows):
                    continue
                row = rows[i]
                r = lay.row_at(i, pn.scroll)
                lane = QtCore.QRectF(t.left, r[1], max(1.0, t.right - t.left), r[3])
                scale, opacity = pn.lane_of(i) if moving else (1.0, 1.0)
                if opacity <= 0.001:
                    continue
                scaled(p, lane, scale, opacity)
                if L.dimmed(row, rows):
                    p.setOpacity(p.opacity() * DIM)
                p.setPen(Qt.NoPen)
                p.setBrush(colour(tk["field"]))
                p.drawRoundedRect(lane, 4 * ui, 4 * ui)
                if row.get("active"):
                    hex_ = tk["accent"]
                elif row.get("base"):
                    hex_ = tk["faint"]
                else:
                    hex_ = tk["muted"]
                path = QtGui.QPainterPath()
                top, bottom = lane.top() + 4 * ui, lane.bottom() - 4 * ui
                for frame in pn.keys.get(row["name"], []):
                    if not (t.v0 - 1 <= frame <= t.v1 + 1):
                        continue
                    if look.on_frame(frame) and t.cells:
                        l, tp, kw, kh = look.key_cell(t.x(frame), t.scale, top, bottom, ui)
                        path.addRoundedRect(QtCore.QRectF(l, tp, kw, kh), 1.5 * ui, 1.5 * ui)
                    else:
                        kw = bar.KEY_W * ui * bar.DASH_W
                        path.addRect(QtCore.QRectF(t.x(frame) - kw / 2, top, kw, bottom - top))
                p.fillPath(path, colour(hex_))
                p.restore()
            p.restore()

    _CLASSES.append((Column, Lanes, NameField))
    return _CLASSES[0]
