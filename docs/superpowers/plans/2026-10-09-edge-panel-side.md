# The edge panel on either side - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ⋮ → Edge panel ▸ Off / Left edge / Right edge: the hub's edge panel stands and slides out on the left or the right edge of Maya's screen, remembered.

**Architecture:** The controller keeps every quantity "from the screen edge inward" (the slot's offset, the frame); pure functions in `maya_edgerules` turn them into host-local geometry for a side. `Edge` takes a `side` and can move (`set_side`); `maya_hub` remembers the side and moves a standing panel; `maya_hubqt` shows a three-row submenu.

**Tech Stack:** Maya 2027 Python 3, PySide6 6.8.3 offscreen for tests, mayapy unittest.

## Global Constraints

- The side optionVar is `skeldarAnimHub_edgeSide`, values `"left"` / `"right"`; missing or anything else reads `"left"`.
- `skeldarAnimHub_edge` (on/off) and `skeldarAnimHub_edgeWidth` are unchanged; one width for both sides.
- `maya_edgerules` stays stdlib-only (its purity test).
- Tests: `$env:QT_QPA_PLATFORM='offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest <modules>` from the repo root; never `python`; no `2>&1` on mayapy.
- No GUI Maya, port or install of ours (the animator's live checks, 2026-10-09). Stage only these files: another session commits to the branch and CLAUDE.md holds somebody else's hunk.

---

### Task 1: The rules for a side

**Files:**
- Modify: `SkeldarAnim/maya_edgerules.py`
- Test: `tests/test_edgerules.py`

**Interfaces:**
- Produces: `SIDE_VAR`, `SIDES`, `side_of(value) -> "left"|"right"`, `panel_rect(area, width, scale, side="left")`, `sensor_rect(area, side="left")`, `slot_x(offset, line, side="left") -> int`, `offset_of(x, line, side="left") -> int`, `frame_span(frame, host_w, side="left") -> (x, w)`, `line_x(frame, host_w, line, side="left") -> int`, `grip_x(host_w, grip, side="left") -> int`, `dragged_width(width0, dx, scale, side="left") -> float`.

- [ ] **Step 1: Write the failing tests**

```python
class Sides(unittest.TestCase):

    def test_the_variable_and_the_sides(self):
        self.assertEqual(rules.SIDE_VAR, "skeldarAnimHub_edgeSide")
        self.assertEqual(rules.SIDES, ("left", "right"))

    def test_side_of_reads_right_or_left(self):
        self.assertEqual(rules.side_of("right"), "right")
        self.assertEqual(rules.side_of(" Right "), "right")
        for value in ("left", None, "", "top", 0, 1):
            self.assertEqual(rules.side_of(value), "left")

    def test_the_panel_on_the_right_edge(self):
        self.assertEqual(rules.panel_rect((0, 0, 2560, 1528), 360, 1.5,
                                          "right"), (2020, 0, 540, 1528))
        self.assertEqual(rules.panel_rect((2560, 40, 1280, 2000), 400, 1.0,
                                          "right"), (3440, 40, 400, 2000))
        self.assertEqual(rules.panel_rect((0, 0, 300, 800), 700, 1.0,
                                          "right"), (0, 0, 300, 800))

    def test_the_sensor_on_the_right_edge(self):
        self.assertEqual(rules.sensor_rect((0, 0, 2560, 1528), "right"),
                         (2558, 0, 2, 1528))

    def test_the_left_is_the_default(self):
        area = (100, 20, 1600, 900)
        self.assertEqual(rules.panel_rect(area, 360, 1.0),
                         rules.panel_rect(area, 360, 1.0, "left"))
        self.assertEqual(rules.sensor_rect(area),
                         rules.sensor_rect(area, "left"))


class LocalGeometry(unittest.TestCase):
    """Offsets and frames count from the screen edge inward; the host's own
    x depends on the side."""

    def test_the_slot(self):
        self.assertEqual(rules.slot_x(-540, 1), -540)
        self.assertEqual(rules.slot_x(0, 1), 0)
        self.assertEqual(rules.slot_x(-540, 1, "right"), 541)
        self.assertEqual(rules.slot_x(0, 1, "right"), 1)
        for side in rules.SIDES:
            for offset in (-540, -200, 0):
                x = rules.slot_x(offset, 1, side)
                self.assertEqual(rules.offset_of(x, 1, side), offset)

    def test_the_frame_shown(self):
        self.assertEqual(rules.frame_span(100, 540), (0, 100))
        self.assertEqual(rules.frame_span(100, 540, "right"), (440, 100))
        self.assertEqual(rules.frame_span(540, 540, "right"), (0, 540))

    def test_the_line_on_the_frame_s_inner_edge(self):
        self.assertEqual(rules.line_x(100, 540, 2), 98)
        self.assertEqual(rules.line_x(100, 540, 2, "right"), 440)

    def test_the_grip_on_the_panel_s_inner_side(self):
        self.assertEqual(rules.grip_x(540, 5), 535)
        self.assertEqual(rules.grip_x(540, 5, "right"), 0)

    def test_a_grip_drag_inward_widens(self):
        self.assertEqual(rules.dragged_width(360, 100, 1.0), 460)
        self.assertEqual(rules.dragged_width(360, -100, 1.0, "right"), 460)
        self.assertEqual(rules.dragged_width(360, 150, 1.5, "right"), 260)
```

- [ ] **Step 2: Run them, expect AttributeError on SIDE_VAR / TypeError on `panel_rect(..., "right")`.**

Run: `... -m unittest tests.test_edgerules`

- [ ] **Step 3: Implement** (after `GRIP_PX`, and the two rects replaced)

```python
SIDE_VAR = "skeldarAnimHub_edgeSide"
SIDES = ("left", "right")


def side_of(value):
    """A remembered or asked side: "right", else "left"."""
    return "right" if str(value or "").strip().lower() == "right" else "left"


def panel_rect(work_area, width, scale, side="left"):
    """The panel in physical px: against the work area's `side` edge, its
    full height, `width` logical px wide (clamped, and never wider than the
    area)."""
    x, y, w, h = work_area
    pw = int(min(w, int(round(clamp_width(width) * float(scale or 1.0)))))
    if side_of(side) == "right":
        return (int(x + w - pw), int(y), pw, int(h))
    return (int(x), int(y), pw, int(h))


def sensor_rect(work_area, side="left"):
    x, y, w, h = work_area
    if side_of(side) == "right":
        return (int(x + w - SENSOR_PX), int(y), SENSOR_PX, int(h))
    return (int(x), int(y), SENSOR_PX, int(h))


def slot_x(offset, line, side="left"):
    """The slot's x inside the host at `offset` from the screen edge (-host
    width off it, 0 out). The slot is `line` px narrower than the host and
    leaves the line on the panel's inner side uncovered."""
    if side_of(side) == "right":
        return int(line - offset)
    return int(offset)


def offset_of(x, line, side="left"):
    """slot_x read back: the offset a slot standing at `x` has."""
    if side_of(side) == "right":
        return int(line - x)
    return int(x)


def frame_span(frame, host_w, side="left"):
    """(x, width) of the host showing when `frame` px of it are out."""
    if side_of(side) == "right":
        return (int(host_w - frame), int(frame))
    return (0, int(frame))


def line_x(frame, host_w, line, side="left"):
    """The 1-logical-px line on the frame's inner edge, host-local x."""
    if side_of(side) == "right":
        return int(host_w - frame)
    return int(frame - line)


def grip_x(host_w, grip, side="left"):
    """The width grip on the host's inner side, host-local x."""
    if side_of(side) == "right":
        return 0
    return int(host_w - grip)


def dragged_width(width0, dx, scale, side="left"):
    """The logical width after the grip moved `dx` physical px: inward
    widens (right on the left edge, left on the right edge)."""
    step = float(dx) / float(scale or 1.0)
    if side_of(side) == "right":
        step = -step
    return width0 + step
```

Also: `SENSOR_PX` / `GRIP_PX` comments say "the screen's edge" / "the panel's inner side"; the module docstring names the 2026-10-09 ask.

- [ ] **Step 4: Run, expect OK.**
- [ ] **Step 5: Commit** at the end of Task 2 (the rules alone change nothing anyone sees).

### Task 2: `Edge` on a side

**Files:**
- Modify: `SkeldarAnim/maya_hubedge.py`
- Test: `tests/test_hubedge.py`

**Interfaces:**
- Consumes: Task 1's functions.
- Produces: `Edge(..., side="left")`, `edge.side`, `edge.offset` (property, int), `edge.set_side(side) -> bool` (True when it moved: the panel hidden at once, the windows at the new edge, the sensor up; the caller reveals).

- [ ] **Step 1: Write the failing tests** (a new class, the right side, motion off unless sliding)

```python
class RightSide(unittest.TestCase):
    """2026-10-09, the animator: «Можем добавить опцию выбора стороны
    монитора откуда выезжает наша полка?» - the right edge, mirrored."""

    AREA = (100, 20, 1600, 900)          # x 100..1700

    def _edge(self, motion=False, side="right"):
        _app()
        self.point = (1699, 300)
        self.widths = []
        return hubedge.Edge(scale=1.0, width=360, side=side,
                            motion=lambda: motion,
                            on_width=self.widths.append,
                            work_area=lambda: self.AREA,
                            cursor=lambda: self.point,
                            buttons=lambda: False,
                            app_active=lambda: True)

    def _run(self, edge, sample):
        seen = []
        loop_until = QtCore.QDeadlineTimer(3000)
        while edge.sliding() and not loop_until.hasExpired():
            QtWidgets.QApplication.processEvents()
            seen.append(sample())
        return seen

    def test_the_windows_stand_on_the_right_edge(self):
        edge = self._edge()
        try:
            self.assertEqual(edge.side, "right")
            self.assertEqual(edge.host.geometry().getRect(),
                             (1340, 20, 360, 900))
            self.assertEqual(edge.sensor.geometry().getRect(),
                             (1700 - rules.SENSOR_PX, 20, rules.SENSOR_PX,
                              900))
            #  hidden, the slot waits off the right edge
            self.assertEqual(edge.offset, -360)
            self.assertEqual(edge.slot.x(), 361)
        finally:
            edge.destroy()

    def test_a_dwell_on_the_right_edge_reveals(self):
        edge = self._edge()
        try:
            edge.sensor_entered()
            edge.dwell_done()
            self.assertTrue(edge.shown)
            self.assertEqual(edge.offset, 0)
            #  the slot stops short of the line on the panel's left
            self.assertEqual(edge.slot.geometry().getRect(),
                             (1, 0, 359, 900))
            self.assertEqual(edge.grip.geometry().getRect(),
                             (0, 0, rules.GRIP_PX, 900))
            self.assertTrue(edge.host.mask().isEmpty())
        finally:
            edge.destroy()

    def test_the_left_edge_does_not_reveal_it(self):
        edge = self._edge()
        try:
            self.point = (100, 300)
            edge.sensor_entered()
            edge.dwell_done()
            self.assertFalse(edge.shown)
        finally:
            edge.destroy()

    def test_dragging_the_grip_left_widens(self):
        edge = self._edge()
        try:
            edge.reveal()
            edge.grip.press(1340)
            edge.grip.drag(1240)
            self.assertEqual(edge.host.geometry().getRect(),
                             (1240, 20, 460, 900))
            edge.grip.drag(1400)
            self.assertEqual(edge.host.width(), rules.MIN_WIDTH)
            edge.grip.release()
            self.assertEqual(self.widths, [rules.MIN_WIDTH])
            self.assertEqual(edge.host.geometry().right(), 1699)
            self.assertEqual(edge.grip.x(), 0)
        finally:
            edge.destroy()

    def test_the_frame_grows_from_the_right_and_the_hub_comes_in_after(self):
        edge = self._edge(motion=True)
        try:
            w = edge.host.width()
            edge.reveal()
            seen = self._run(edge, lambda: (
                edge.frame, edge.offset, edge.slot.x(),
                edge.host.mask().boundingRect().getRect()))
            self.assertTrue(seen)
            for frame, offset, x, mask in seen:
                if frame < w:
                    #  only the frame's right part shows
                    self.assertEqual((mask[0], mask[2]),
                                     (w - max(1, frame), max(1, frame)))
                self.assertGreaterEqual(frame, w + offset - 1)
                self.assertEqual(x, 1 - offset)
            xs = [x for _f, _o, x, _m in seen]
            self.assertEqual(xs, sorted(xs, reverse=True))   # leftward
            self.assertEqual((edge.frame, edge.offset), (w, 0))
            self.assertTrue(edge.host.mask().isEmpty())
        finally:
            edge.destroy()

    def test_it_goes_back_off_the_right_edge(self):
        edge = self._edge(motion=True)
        try:
            w = edge.host.width()
            edge.reveal()
            self._run(edge, lambda: None)
            edge.conceal()
            seen = self._run(edge, lambda: (edge.frame, edge.offset))
            for frame, offset in seen:
                self.assertLessEqual(abs(frame - (w + offset)), 1)
            self.assertEqual((edge.frame, edge.offset), (0, -w))
            self.assertFalse(edge.host.isVisible())
            self.assertTrue(edge.sensor.isVisible())
        finally:
            edge.destroy()

    def test_set_side_moves_a_standing_panel(self):
        edge = self._edge(side="left")
        try:
            edge.reveal(hold=True)
            self.assertTrue(edge.set_side("right"))
            self.assertEqual(edge.side, "right")
            self.assertFalse(edge.shown)
            self.assertFalse(edge.hold.held)
            self.assertFalse(edge.host.isVisible())
            self.assertTrue(edge.sensor.isVisible())
            self.assertEqual(edge.host.geometry().getRect(),
                             (1340, 20, 360, 900))
            self.assertEqual(edge.sensor.x(), 1700 - rules.SENSOR_PX)
            self.assertEqual((edge.offset, edge.frame), (-360, 0))
            edge.reveal()
            self.assertEqual(edge.slot.x(), 1)
            #  the same side again: nothing
            self.assertFalse(edge.set_side("right"))
            self.assertTrue(edge.shown)
        finally:
            edge.destroy()

    def test_set_side_stops_a_slide(self):
        edge = self._edge(motion=True, side="left")
        try:
            edge.reveal()
            self.assertTrue(edge.sliding())
            edge.set_side("right")
            self.assertFalse(edge.sliding())
            self.assertEqual((edge.offset, edge.frame), (-360, 0))
        finally:
            edge.destroy()
```

Plus the left side's defaults pinned: `test_the_left_is_the_default` - `Edge` with no `side` answers `side == "left"` and `offset == slot.x()` at rest and out.

- [ ] **Step 2: Run, expect TypeError (`side`).**
- [ ] **Step 3: Implement**
  - `__init__(..., side="left")`: `self.side = rules.side_of(side)` before `place()`.
  - `offset` property: `rules.offset_of(self.slot.x(), self._line(), self.side)`; `_put_slot(offset)`: `self.slot.move(rules.slot_x(int(round(offset)), self._line(), self.side), 0)`.
  - `place()`: `rules.panel_rect(area, self.width, self.scale, self.side)`, `rules.sensor_rect(area, self.side)`; `dwell_done`: `rules.sensor_rect(area, self.side)`.
  - `_fit_slot`: `offset = self.offset` while animating, else `0` / `-w`; `slot.setGeometry(rules.slot_x(offset, line, side), 0, max(1, w - line), h)`; grip at `rules.grip_x(w, g, side)`.
  - `_set_frame`: `fx, fw = rules.frame_span(max(1, px), w, side)` → `QRegion(fx, 0, fw, h)`.
  - `Host.paintEvent`: fill `frame_span(frame, w, side)`, the line at `line_x(frame, w, line, side)`.
  - `_slide`: `hub_out = self.offset > -width`, `start = self.offset`; `_reveal_from_rest.step` and `_move_slot` use `_put_slot`.
  - `WidthGrip.drag`: `rules.dragged_width(width0, gx - x0, edge.scale, edge.side)`.
  - `set_side(side)`:

```python
    def set_side(self, side):
        """Stand on `side` from now on (2026-10-09). A new side: any slide
        stops, the panel goes at once (no slide back), the windows stand at
        the new edge with the slot off it and the sensor up; the caller
        reveals it there. True when it moved; the side it stands on, False."""
        side = rules.side_of(side)
        if side == self.side or not self.alive():
            return False
        self._stop_anim()
        for timer in (self.dwell, self.hide, self.retry):
            timer.stop()
        self._shown = False
        self._rest_out = False
        self.hold = rules.Hold()
        self._sync_watch()
        self.side = side
        self.host.hide()
        self.place()
        self.sensor.show()
        self.sensor.raise_()
        return True
```

  - Docstrings: the module's first line and `host`/`sensor`/`grip` paragraphs say "the chosen edge (left or right)".
- [ ] **Step 4: Run `tests.test_edgerules tests.test_hubedge`, expect OK (the left side's tests unchanged).**
- [ ] **Step 5: Commit** `SkeldarAnim/maya_edgerules.py SkeldarAnim/maya_hubedge.py tests/test_edgerules.py tests/test_hubedge.py`: `feat(hub): the edge panel can stand on the right edge too`.

### Task 3: The hub remembers the side and moves the panel

**Files:**
- Modify: `SkeldarAnim/maya_hub.py`
- Test: `tests/test_hub.py` (`FakeEdge` takes `side` and records `set_side`; `FakeSkin.set_edge_mode(on, side="left")`, `paint_edge(on, side="left")` record `(on, side)`)

**Interfaces:**
- Consumes: `Edge(side=...)`, `Edge.set_side`, `Skin.paint_edge(on, side)`, `Skin.set_edge_mode(on, side)` (Task 4).
- Produces: `SIDE_VAR`, `edge_side() -> "left"|"right"`, `set_edge_side(choice) -> bool`; callback key `"edge_side"`.

- [ ] **Step 1: Write the failing tests** (in `EdgeMode`)

```python
    def test_the_side_is_left_by_default_and_remembered(self):
        self.assertEqual(hub.SIDE_VAR, "skeldarAnimHub_edgeSide")
        self.assertEqual(hub.edge_side(), "left")
        self.fake.optionvars[hub.SIDE_VAR] = "right"
        self.assertEqual(hub.edge_side(), "right")
        self.fake.optionvars[hub.SIDE_VAR] = "top"
        self.assertEqual(hub.edge_side(), "left")

    def test_the_panel_is_built_on_the_remembered_side(self):
        self.fake.optionvars[hub.EDGE_VAR] = 1
        self.fake.optionvars[hub.SIDE_VAR] = "right"
        edge = hub.start()
        self.assertEqual(edge.side, "right")
        self.assertEqual(hub._SKIN.edge_mode, (True, "right"))

    def test_a_side_picked_while_off_turns_the_mode_on_there(self):
        self.fake.workspace[hub.CONTROL] = {}
        self.assertTrue(hub.set_edge_side("right"))
        self.assertEqual(self.fake.optionvars[hub.SIDE_VAR], "right")
        self.assertEqual(self.fake.optionvars[hub.EDGE_VAR], 1)
        self.fake.run_deferred()
        self.assertEqual(self.edges[-1].side, "right")
        self.assertTrue(self.edges[-1].revealed_with_hold)

    def test_the_other_side_moves_the_standing_panel(self):
        self.fake.optionvars[hub.EDGE_VAR] = 1
        edge = hub.start()
        self.assertTrue(hub.set_edge_side("right"))
        self.assertEqual(edge.sides, [])                 # deferred
        self.fake.run_deferred()
        self.assertEqual(edge.sides, ["right"])
        self.assertTrue(edge.revealed_with_hold)
        self.assertEqual(len(self.edges), 1)             # the same panel
        self.assertIn((True, "right"), hub._SKIN.edge_painted)

    def test_the_same_side_again_changes_nothing(self):
        self.fake.optionvars[hub.EDGE_VAR] = 1
        edge = hub.start()
        hub.set_edge_side("left")
        self.fake.run_deferred()
        self.assertEqual(edge.sides, ["left"])           # asked, refused
        self.assertEqual(edge.reveals, [])

    def test_the_last_side_picked_wins(self):
        self.fake.optionvars[hub.EDGE_VAR] = 1
        edge = hub.start()
        hub.set_edge_side("right")
        hub.set_edge_side("left")
        self.fake.run_deferred()
        self.assertEqual(edge.side, "left")

    def test_off_is_set_edge_false(self):
        self.fake.optionvars[hub.EDGE_VAR] = 1
        hub.start()
        hub.set_edge_side("off")
        self.assertEqual(self.fake.optionvars[hub.EDGE_VAR], 0)
        self.fake.run_deferred()
        self.assertTrue(self.edges[-1].destroyed)

    def test_a_side_needs_the_skin(self):
        self.fake.optionvars[hub.CLASSIC_VAR] = 1
        self.assertFalse(hub.set_edge_side("right"))
        self.assertNotIn(hub.SIDE_VAR, self.fake.optionvars)

    def test_the_menu_shows_the_side(self):
        skin = FakeSkin(None)
        self.fake.optionvars[hub.EDGE_VAR] = 1
        self.fake.optionvars[hub.SIDE_VAR] = "right"
        hub._dress_edge(skin)
        self.assertEqual(skin.edge_painted, [(True, "right")])
```

`test_the_pin_and_the_switch_are_the_header_s` gains `self.assertIs(callbacks["edge_side"], hub.set_edge_side)`; `test_the_menu_row_shows_the_mode` reads `[(False, "left"), (True, "left")]`.

- [ ] **Step 2: Run `tests.test_hub`, expect failures.**
- [ ] **Step 3: Implement**

```python
SIDE_VAR = edgerules.SIDE_VAR              # "left" / "right" (2026-10-09)


def edge_side():
    """The edge the panel stands on, as remembered: "left" by default."""
    if cmds.optionVar(exists=SIDE_VAR):
        return edgerules.side_of(cmds.optionVar(query=SIDE_VAR))
    return "left"


def set_edge_side(choice):
    """⋮ -> Edge panel ▸ Off / Left edge / Right edge (2026-10-09, «Можем
    добавить опцию выбора стороны монитора откуда выезжает наша полка?»).
    "off" is set_edge(False). A side is remembered, then turns the mode on
    at it, or - the mode on - moves the standing panel there (deferred, as
    set_edge: the press comes from the panel's own menu). Refused, as
    set_edge(True) is, without the new look."""
    if choice not in edgerules.SIDES:
        return set_edge(False)
    if classic_asked() or not _qt_available():
        return set_edge(True)                  # refused, and says why
    cmds.optionVar(stringValue=(SIDE_VAR, edgerules.side_of(choice)))
    if not edge_on():
        return set_edge(True)
    cmds.evalDeferred(_move_edge, lowestPriority=True)
    return True


def _move_edge():
    """The deferred half of `set_edge_side` with the mode on. The last press
    wins (the remembered side); the panel standing moves there and slides
    out held, so the animator sees where it went; none standing, it is built
    on that side and shown the same way."""
    if not edge_on():
        return None
    side = edge_side()
    current = edge()
    if current is not None and _skin_at(current):
        if current.set_side(side):
            if _SKIN is not None:
                _SKIN.paint_edge(True, side)
            current.reveal(hold=True)
        return current
    try:
        current = _ensure_edge()
    except Exception:                                        # noqa: BLE001
        return show()
    current.reveal(hold=True)
    return current
```

`_ensure_edge`: `he.Edge(..., side=edge_side())`, `_SKIN.set_edge_mode(True, edge_side())`. `_dress_edge`: `skin.paint_edge(edge_on(), edge_side())`. Callbacks: `"edge_side": set_edge_side` beside `"edge"`.

- [ ] **Step 4: Run `tests.test_hub`, expect OK.**

### Task 4: The submenu

**Files:**
- Modify: `SkeldarAnim/maya_hubqt.py`
- Test: `tests/test_hubqt.py`

**Interfaces:**
- Produces: `Skin.edge_menu` (QMenu "Edge panel"), `Skin.edge_actions` = `{"off", "left", "right": QAction}` exclusive; `paint_edge(on, side="left")`, `set_edge_mode(on, side="left")`; a row's `triggered` calls `_call("edge_side", choice)`.

- [ ] **Step 1: Write the failing tests**

```python
    def test_the_edge_panel_is_a_submenu_of_three(self):
        seen = []
        self.skin.cb["edge_side"] = lambda choice: seen.append(choice)
        menu = self.skin.edge_menu
        self.assertEqual(menu.title(), "Edge panel")
        self.assertEqual([a.text() for a in menu.actions()],
                         ["Off", "Left edge", "Right edge"])
        self.assertTrue(self.skin.edge_actions["off"].isChecked())
        self.skin.edge_actions["right"].trigger()
        self.skin.edge_actions["off"].trigger()
        self.assertEqual(seen, ["right", "off"])
        #  exclusive
        self.assertEqual([a.isChecked() for a in menu.actions()],
                         [True, False, False])

    def test_paint_edge_checks_the_row_without_a_call(self):
        seen = []
        self.skin.cb["edge_side"] = lambda choice: seen.append(choice)
        self.skin.paint_edge(True, "right")
        self.assertTrue(self.skin.edge_actions["right"].isChecked())
        self.skin.paint_edge(True)
        self.assertTrue(self.skin.edge_actions["left"].isChecked())
        self.skin.paint_edge(False, "right")
        self.assertTrue(self.skin.edge_actions["off"].isChecked())
        self.assertEqual(seen, [])
```

`test_the_menu_offers_...`: the "Edge panel" row is the submenu's action (no callback of its own) - trigger every OTHER row; `test_the_pin_is_hidden_until_edge_mode_and_calls_back` reads `edge_actions["left"]` / `["off"]`; `test_the_edge_row_calls_back_with_its_state` goes (replaced by the two above); `set_edge_mode(True, "right")` checks Right edge.

- [ ] **Step 2: Run `tests.test_hubqt`, expect failures.**
- [ ] **Step 3: Implement** in `_build_header`'s menu loop:

```python
            if key == "edge":
                #  2026-10-09: Off / Left edge / Right edge, one checked
                self.edge_menu = self.menu.addMenu(text)
                self.edge_menu.setObjectName("skeldarHubEdgeMenu")
                group_class = (getattr(q.QtGui, "QActionGroup", None)
                               or w.QActionGroup)
                self._edge_group = group_class(self.edge_menu)
                self._edge_group.setExclusive(True)
                self.edge_actions = {}
                for label, choice in EDGE_CHOICES:
                    action = self.edge_menu.addAction(label)
                    action.setCheckable(True)
                    self._edge_group.addAction(action)
                    action.triggered.connect(
                        lambda checked=False, c=choice:
                        self._call("edge_side", c))
                    self.edge_actions[choice] = action
                self.edge_actions["off"].setChecked(True)
                continue
```

with `EDGE_CHOICES = (("Off", "off"), ("Left edge", "left"), ("Right edge", "right"))` at module level, `"edge"` out of the checkable tuple, and

```python
    def paint_edge(self, on, side="left"):
        """The menu's Edge panel rows show the mode (no callback): Off, or
        the side the panel stands on."""
        choice = ("right" if side == "right" else "left") if on else "off"
        self.edge_actions[choice].setChecked(True)

    def set_edge_mode(self, on, side="left"):
        """The hub stands in the edge panel (`on`): the pin is shown."""
        self.pin.setVisible(bool(on))
        if not on:
            self.pin.setChecked(False)
        self.paint_edge(on, side)
```

- [ ] **Step 4: Run `tests.test_hubqt tests.test_hub tests.test_hubedge tests.test_edgerules`, expect OK; then the whole suite.**
- [ ] **Step 5: Commit** the three files and their tests: `feat(hub): ⋮ -> Edge panel ▸ Off / Left edge / Right edge`.
