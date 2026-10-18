# Floating windows Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A section's copy opens in a floating window, free of the viewport. The window and the edge
rail's card are drawn in look B and burst out of the point that was pressed, the Time Bar's way. The
group-colour stripe is removed everywhere.

**Architecture:**
- The pure parts are tested with no Maya and no Qt: the burst's plan with the Time Bar's numbers and
  its light (`maya_hubburst`), and the window's place on the screens (`maya_hubpop_rules`).
- A new Qt module, `maya_hubwindow`, holds what the window and the rail card draw alike: the look-B
  frame, the painted pill button, and the burst effect with its light (`Burster`).
- `maya_hubpop` keeps its name and becomes the floating window.
- `maya_hubqt` loses the stripe and gains the windowed card for the edge rail.
- `maya_hubedge` runs the card's burst on reveal and conceal.
- `maya_hub` wires the presses.

**Tech Stack:** Python 3 in Maya 2027, PySide6 6.8.3 (offscreen for the tests), stdlib `unittest`
run by mayapy. No system Python: it is the Microsoft Store stub, and it HANGS.

**Spec:** `docs/superpowers/specs/2026-10-18-floating-windows-design.md` (read it first).
**Look and motion rules:** `docs/interface-motion.md`.

## Global Constraints

- Run tests with
  `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v`,
  with `$env:QT_QPA_PLATFORM = 'offscreen'`. A single module:
  `... -m unittest tests.test_hubburst -v`.
- Colours only from `maya_hubstyle.TOKENS`. Lengths are logical × the scale:
  `hubstyle.px(n, scale)`.
- `maya_hubburst` and `maya_hubpop_rules` stay stdlib-only; a subprocess test pins it.
  `maya_hubburst` imports the Time Bar's numbers: `from maya_timebar import look as tlook`.
- Never keep a wrapper of a Maya widget (trap 135). Never `grab()` Maya's widgets (trap 134). A
  QGraphicsEffect is held (trap 201) and disabled at rest (trap 204).
- With ⋮ → Interface animations off (`maya_hubmotion.enabled()` False), nothing bursts: the end
  state comes at once.
- **Other sessions edit this repository.** Commit only your own hunks: `git add -p`, or
  `git commit -- <paths>` for files only you touched. Never commit `CLAUDE.md` hunks that are not
  yours. Before editing `maya_hubqt.py` or `maya_sidepanel/`, message the session «Меню для Chanel
  box» (it edits `_build_sidepanel_menu` / `paint_sidepanel`) and keep away from those functions.
- **No GUI Maya, no port 7001, no install.** The live checks are the animator's
  (memory `live-checks-are-the-animators.md`). The summary says «not seen in a GUI Maya».
- Commit message bodies end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Write
  the message to a file and use `git commit -F`.

---

### Task 1: The burst on the Time Bar's numbers, with its light (`maya_hubburst`)

**Files:**
- Modify: `SkeldarAnim/maya_hubburst.py`
- Test: `tests/test_hubburst.py`

**Interfaces:**
- Consumes: `maya_timebar.look`: `UNROLL_MS`, `POP_OPEN_MS`, `FOLD_MS`, `CLOSE_MS`,
  `CLOSE_AFTER_MS`, `START_SCALE`, `REVEAL_MS`, `EDGE_GLOW`, `EDGE_CORE`, `TOP_GLOW`, `burst_delay`,
  `back_out`, `back_in`, `ease_out_quint`, `ease_in_quint`.
- Produces:
  - `plan_open(origin, size, parts, scale=1.0) -> Plan` and `plan_close(...) -> Plan`: the same
    fields as today;
  - `at(plan, ms) -> State(shape, radius, face, parts)`: parts are `(opacity, scale)`, as today;
  - new `light(plan, ms) -> Light(edges, top)`: `edges` is a list of `(axis, pos, intensity)`,
    axis "x" for a vertical edge at x=pos and "y" for a horizontal one, card px; `top` is 0..1;
  - new constants `EDGE_GLOW`, `EDGE_CORE`, `TOP_GLOW`, logical, re-exported from the Time Bar.

- [ ] **Step 1: Write the failing tests** (add to `tests/test_hubburst.py`; drop the tests of the
  old numbers that contradict them: the `PART_FROM` 0.82 overshoot test becomes the 0.3 one below)

```python
from maya_timebar import look as tlook


class TimeBarNumbers(unittest.TestCase):
    """2026-10-18: the burst is the Time Bar's (spec 2026-10-18-floating-windows-design.md)."""

    SIZE = (300.0, 400.0)
    PARTS = [(10, 10, 280, 30), (10, 300, 280, 30)]

    def test_the_shape_grows_over_the_time_bars_unroll(self):
        plan = hubburst.plan_open((20, 20), self.SIZE, self.PARTS)
        self.assertEqual(hubburst.at(plan, tlook.UNROLL_MS).shape, (0.0, 0.0, 300.0, 400.0))
        mid = hubburst.at(plan, tlook.UNROLL_MS / 2.0).shape
        self.assertLess(mid[2], 300.0)

    def test_a_part_pops_from_the_time_bars_start_scale(self):
        plan = hubburst.plan_open((20, 20), self.SIZE, self.PARTS)
        d = plan.delays[0]
        op, sc = hubburst.at(plan, d + 1.0).parts[0]
        self.assertAlmostEqual(sc, tlook.START_SCALE, delta=0.02)
        self.assertEqual(hubburst.at(plan, d + tlook.POP_OPEN_MS).parts[0], (1.0, 1.0))

    def test_the_nearest_part_starts_by_the_time_bars_delay(self):
        plan = hubburst.plan_open((20, 20), self.SIZE, self.PARTS)
        self.assertLess(plan.delays[0], plan.delays[1])
        self.assertAlmostEqual(plan.delays[0], tlook.burst_delay(130, 5), delta=0.5)

    def test_the_close_starts_its_shape_after_the_last_fold(self):
        plan = hubburst.plan_close((20, 20), self.SIZE, self.PARTS)
        last = max(plan.delays) + tlook.FOLD_MS
        self.assertAlmostEqual(plan.m0, last + tlook.CLOSE_AFTER_MS, delta=0.5)
        self.assertAlmostEqual(plan.total, plan.m0 + tlook.CLOSE_MS, delta=0.5)

    def test_a_folded_part_ends_at_the_start_scale_and_gone(self):
        plan = hubburst.plan_close((20, 20), self.SIZE, self.PARTS)
        d = plan.delays[0]
        self.assertEqual(hubburst.at(plan, d + tlook.FOLD_MS).parts[0], (0.0, tlook.START_SCALE))


class Light(unittest.TestCase):

    SIZE = (300.0, 400.0)
    PARTS = [(10, 10, 280, 30)]

    def test_the_edges_inside_the_card_carry_light_while_it_grows(self):
        plan = hubburst.plan_open((150, 200), self.SIZE, self.PARTS)
        light = hubburst.light(plan, 40.0)
        axes = sorted(e[0] for e in light.edges)
        self.assertEqual(axes, ["x", "x", "y", "y"])
        self.assertTrue(all(0.0 < e[2] <= 1.0 for e in light.edges))

    def test_the_edge_light_fades_as_the_edges_slow(self):
        plan = hubburst.plan_open((150, 200), self.SIZE, self.PARTS)
        early = max(e[2] for e in hubburst.light(plan, 20.0).edges)
        later = max(e[2] for e in hubburst.light(plan, 200.0).edges)
        self.assertGreater(early, later)

    def test_an_edge_on_the_card_border_carries_none(self):
        plan = hubburst.plan_open((150, 200), self.SIZE, self.PARTS)
        self.assertEqual(hubburst.light(plan, tlook.UNROLL_MS).edges, [])

    def test_the_top_lights_once_the_shape_reaches_it_and_fades(self):
        plan = hubburst.plan_open((150, 390), self.SIZE, self.PARTS)
        self.assertEqual(hubburst.light(plan, 1.0).top, 0.0)
        reached = hubburst.light(plan, tlook.UNROLL_MS).top
        self.assertGreater(reached, 0.0)
        self.assertEqual(hubburst.light(plan, tlook.REVEAL_MS).top, 0.0)

    def test_a_close_carries_no_light(self):
        plan = hubburst.plan_close((150, 200), self.SIZE, self.PARTS)
        light = hubburst.light(plan, 50.0)
        self.assertEqual((light.edges, light.top), ([], 0.0))

    def test_the_light_lengths_are_the_time_bars(self):
        self.assertEqual((hubburst.EDGE_GLOW, hubburst.EDGE_CORE, hubburst.TOP_GLOW),
                         (tlook.EDGE_GLOW, tlook.EDGE_CORE, tlook.TOP_GLOW))
```

Also extend the existing `Pure` test: the subprocess imports `maya_hubburst` and asserts that neither
`maya.cmds` nor `PySide6` is in `sys.modules` (the `maya_timebar` package imports neither at
import; check `SkeldarAnim/maya_timebar/__init__.py`: stdlib only).

- [ ] **Step 2: Run them to see them fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_hubburst -v`
Expected: FAIL (`light` missing, the old 300 / 0.82 / 22 ms numbers).

- [ ] **Step 3: Implement**

In `maya_hubburst.py`:
- Replace the numbers block. Keep `START_HALF` (14, 10), `START_RADIUS`, `CARD_RADIUS`,
  `ORIGIN_PAD`, `CLOSE_HALF` (12, 9), `ROW_MAX`, `MAX_PARTS`, `MAX_DEPTH`, `MAX_MS`.
- The opening keeps `FACE_IN_MS` 60. The closing keeps the face fading over its last 80 ms.

```python
from maya_timebar import look as tlook

SHAPE_MS = tlook.UNROLL_MS          # 288: the shape unrolls (ease_out_quint)
PART_MS = tlook.POP_OPEN_MS         # 240: a part pops (back_out from START_SCALE)
FOLD_MS = tlook.FOLD_MS             # 168: a part folds (back_in to START_SCALE)
CLOSE_SHAPE_MS = tlook.CLOSE_MS     # 216: the shape closes (ease_in_quint)
CLOSE_AFTER_MS = tlook.CLOSE_AFTER_MS   # 72 after the last fold ends
PART_FROM = tlook.START_SCALE       # 0.3
REVEAL_MS = tlook.REVEAL_MS         # 780
EDGE_GLOW, EDGE_CORE, TOP_GLOW = tlook.EDGE_GLOW, tlook.EDGE_CORE, tlook.TOP_GLOW
FACE_OUT_MS = 80
Light = collections.namedtuple("Light", "edges top")
```

- `plan_open`: `delays = [tlook.burst_delay((cx - o[0]) / scale, (cy - o[1]) / scale) for ...]`
  with `(cx, cy)` each part's centre. `total = max(SHAPE_MS, REVEAL_MS, max(d + PART_MS))`: the
  light outlives the shape.
- `plan_close`: `d = abs(cx - o[0]) / scale + 1.5 * abs(cy - o[1]) / scale` and
  `delay = max(0, 180 - d / 60 * 12) * tlook.BURST_SLOW`; `m0 = max(delays) + FOLD_MS +
  CLOSE_AFTER_MS`; `total = m0 + CLOSE_SHAPE_MS`.
- `at`:
  - opening: `f = tlook.ease_out_quint(ms / SHAPE_MS)`; a part's `u = (ms - d) / PART_MS`; scale
    `PART_FROM + (1 - PART_FROM) * tlook.back_out(u)`; opacity `min(1, u * 1.6)` (0 for u ≤ 0);
    `(1.0, 1.0)` at u ≥ 1;
  - closing: a part's `u = (ms - d) / FOLD_MS`; scale `1 - (1 - PART_FROM) * tlook.back_in(u)`;
    opacity `max(0, 1 - u)`, and `(0.0, PART_FROM)` at u ≥ 1; the shape
    `k = tlook.ease_in_quint((ms - m0) / CLOSE_SHAPE_MS)`; the face `1 - ease((ms - m0 -
    (CLOSE_SHAPE_MS - FACE_OUT_MS)) / FACE_OUT_MS)`.
  - At `ms >= total`, exactly the end, as today.
- New `light(plan, ms)`:

```python
def light(plan, ms):
    """The burst's light `ms` in (2026-10-18, the Time Bar's racing edges): the shape's edges
    standing inside the card, each (axis, pos, intensity) - 1 at the start, fading as
    (1 - ease_out_quint)^0.55 - and the card's top edge, once the shape reaches it, fading as
    (1 - ms / REVEAL_MS)^1.6. A close carries none."""
    if not plan.opening or ms >= plan.total:
        return Light([], 0.0)
    w, h = plan.size
    u = ms / float(SHAPE_MS)
    e = tlook.ease_out_quint(u)
    x0, y0, x1, y1 = _shape_between(plan.start, plan.end, e)
    edges = []
    if u < 1.0:
        k = (1.0 - e) ** 0.55
        for axis, pos, limit in (("x", x0, w), ("x", x1, w), ("y", y0, h), ("y", y1, h)):
            if 0.5 < pos < limit - 0.5 and k > 0.0:
                edges.append((axis, pos, k))
    top = 0.0
    if y0 <= 0.5:
        top = max(0.0, 1.0 - ms / float(REVEAL_MS)) ** 1.6
    return Light(edges, top)
```

- Update the module docstring with the date, the animator's words («сделаем новые анимации в
  стиле таймслайдера») and the spec's path.

- [ ] **Step 4: Run the tests**

Run: `... -m unittest tests.test_hubburst -v`
Expected: all PASS. Fix older tests that pinned the old numbers by naming the Time Bar's constants.
Delete none that pin behaviour (nearest first, farthest first, the shape monotone).

- [ ] **Step 5: Commit**

```bash
git commit -F msg.txt -- SkeldarAnim/maya_hubburst.py tests/test_hubburst.py
```
Message: `feat(hubburst): the Time Bar's numbers and its racing-edge light`.

---

### Task 2: The window's place on the screens (`maya_hubpop_rules`)

**Files:**
- Modify: `SkeldarAnim/maya_hubpop_rules.py`
- Test: `tests/test_hubpop_rules.py`

**Interfaces:**
- Produces:
  - `screen_for(point, screens) -> rect`: `screens` is a non-empty list of `(x, y, w, h)` available
    geometries, physical. Returns the one holding `point`, else the nearest by distance to its
    rectangle;
  - `place_by_point(point, w, h, screens, scale) -> (x, y)`: the window's top-left `AT_CURSOR`
    (18, 14) logical left of and above `point`, clamped onto `screen_for(point)`;
  - `place_on_screens(place, w, h, screens, scale) -> (x, y) or None`: a remembered LOGICAL
    top-left. None when its title row's centre `(x + w / 2, y + TITLE_PROBE * scale)` falls on no
    screen; else it is clamped onto that screen;
  - `encode_place(place)` / `decode_place(text)`: the same text as `encode_offset`/`decode_offset`;
  - constants `WINDOW_POS_VAR = "skeldarHubWindowPos_{0}"`, `AT_CURSOR = (18, 14)`,
    `TITLE_PROBE = 16`, and `MAX_HEIGHT` 560 (was 320).
  - `bounds` and `popup_size` keep their signatures; their `rect` is now a SCREEN's available
    geometry, and their docstrings say so.
- `POS_VAR` stays defined (the old viewport offset), and nothing reads it any more.

- [ ] **Step 1: Write the failing tests**

```python
LEFT = (0, 0, 1920, 1040)
RIGHT = (1920, 0, 2560, 1400)


class Screens(unittest.TestCase):

    def test_the_screen_holding_the_point(self):
        self.assertEqual(rules.screen_for((2000, 50), [LEFT, RIGHT]), RIGHT)

    def test_a_point_on_no_screen_takes_the_nearest(self):
        self.assertEqual(rules.screen_for((5000, 50), [LEFT, RIGHT]), RIGHT)
        self.assertEqual(rules.screen_for((-300, 50), [LEFT, RIGHT]), LEFT)

    def test_a_window_by_a_point_stands_left_of_and_above_it(self):
        self.assertEqual(rules.place_by_point((500, 400), 300, 200, [LEFT], 1.5),
                         (500 - 27, 400 - 21))

    def test_a_window_by_a_point_is_kept_on_its_screen(self):
        x, y = rules.place_by_point((1910, 1030), 300, 200, [LEFT, RIGHT], 1.0)
        self.assertEqual((x + 300, y + 200), (1920, 1040))

    def test_a_remembered_place_on_a_screen_is_taken(self):
        self.assertEqual(rules.place_on_screens((1300.0, 100.0), 300, 200, [LEFT, RIGHT], 1.5),
                         (1950, 150))

    def test_a_remembered_place_on_no_screen_is_dropped(self):
        self.assertIsNone(rules.place_on_screens((3000.0, 100.0), 300, 200, [LEFT], 1.0))

    def test_a_remembered_place_hanging_off_a_screen_is_pulled_on(self):
        self.assertEqual(rules.place_on_screens((1800.0, 100.0), 300, 200, [LEFT], 1.0),
                         (1620, 100))

    def test_the_window_place_has_its_own_option_var(self):
        self.assertEqual(rules.WINDOW_POS_VAR.format("tools"), "skeldarHubWindowPos_tools")
        self.assertNotEqual(rules.WINDOW_POS_VAR, rules.POS_VAR)

    def test_a_window_may_stand_taller_than_a_popup_did(self):
        self.assertEqual(rules.MAX_HEIGHT, 560)

    def test_the_place_round_trips_as_text(self):
        self.assertEqual(rules.decode_place(rules.encode_place((12.5, -3.0))), (12.5, -3.0))
```

Remove or rewrite the old tests that pin `MAX_HEIGHT` 320 or `default_offset` against a viewport.
`default_offset` stays, unused, until Task 5 deletes it together with its tests.

- [ ] **Step 2: Run them to see them fail**

Run: `... -m unittest tests.test_hubpop_rules -v`
Expected: FAIL (`screen_for` missing).

- [ ] **Step 3: Implement**

```python
WINDOW_POS_VAR = "skeldarHubWindowPos_{0}"   # a window's top-left, global logical "x,y" (2026-10-18)
AT_CURSOR = (18, 14)    # logical px: a window by a point stands this far left of and above it
TITLE_PROBE = 16        # logical px down from the top: the title row a remembered place must keep on a screen


def _inside(point, rect):
    return rect[0] <= point[0] < rect[0] + rect[2] and rect[1] <= point[1] < rect[1] + rect[3]


def _distance(point, rect):
    dx = max(rect[0] - point[0], 0, point[0] - (rect[0] + rect[2] - 1))
    dy = max(rect[1] - point[1], 0, point[1] - (rect[1] + rect[3] - 1))
    return dx * dx + dy * dy


def screen_for(point, screens):
    """The available rectangle holding `point`, else the nearest one. Pure."""
    for rect in screens:
        if _inside(point, rect):
            return rect
    return min(screens, key=lambda rect: _distance(point, rect))


def place_by_point(point, w, h, screens, scale):
    """A window's top-left by `point`: AT_CURSOR left of and above it, on its screen. Pure."""
    scale = float(scale) or 1.0
    x = point[0] - AT_CURSOR[0] * scale
    y = point[1] - AT_CURSOR[1] * scale
    return clamp_origin(x, y, w, h, screen_for(point, screens))


def place_on_screens(place, w, h, screens, scale):
    """A remembered logical top-left, physical and on its screen - or None when its title row
    stands on no screen any more (a monitor unplugged). Pure."""
    scale = float(scale) or 1.0
    x, y = place[0] * scale, place[1] * scale
    probe = (x + w / 2.0, y + TITLE_PROBE * scale)
    for rect in screens:
        if _inside(probe, rect):
            return clamp_origin(x, y, w, h, rect)
    return None


encode_place = encode_offset
decode_place = decode_offset
```

Set `MAX_HEIGHT = 560` with a comment: «a floating window is not squeezed into a viewport,
2026-10-18». Rewrite the module docstring's first paragraph: rectangles are a screen's available
geometry since 2026-10-18.

- [ ] **Step 4: Run the tests**

Run: `... -m unittest tests.test_hubpop_rules -v`
Expected: PASS.

- [ ] **Step 5: Commit**

`git commit -F msg.txt -- SkeldarAnim/maya_hubpop_rules.py tests/test_hubpop_rules.py`
Message: `feat(hubpop_rules): a window's place on the screens, not in a viewport`.

---

### Task 3: The shared window module (`maya_hubwindow`): the frame, the pill, the burster

**Files:**
- Create: `SkeldarAnim/maya_hubwindow.py`
- Modify: `SkeldarAnim/install.py` (a payload row after `maya_hubpop_rules.py`:
  `"maya_hubwindow.py",  # the floating window's and the rail card's look and burst (2026-10-18)`)
- Test: `tests/test_hubwindow.py` (new)

**Interfaces:**
- Consumes: `maya_hubqt.qt()`, `hubqt._frame_class()` (the CardFrame with `level`, `flash`,
  `scale` and `paint_light`), `maya_hubburst` (Task 1), `maya_hubstyle.TOKENS`, `hubstyle.px`.
- Produces:
  - `frame_class() -> type`: `WindowFrame(scale, parent=None)`, a CardFrame subclass. It paints the
    look-B face (`panel`, a 1 px `track_edge` outline, radius 8). Its `content` attribute is a
    child QFrame (objectName given by the caller) that paints `card` with radius 6. The light
    (`level` / `flash`) is the card's `paint_light`, drawn over the frame. There is no stripe, no
    accent and no title hairline.
  - `pill_class() -> type`: `PillButton(icon_name, scale, parent=None)`, a `QToolButton` painting
    itself:
    - 24 × 22 logical, radius 5, face `field`, a 1 px `track_edge`;
    - hover moves `level` toward 1 by `approach` over 110 ms (16 ms timer, stopped at rest): scale
      +10 %, the face `hover`, four accent rings 1.6 px apart with alpha 46·level·(5-i)/4/255;
    - a press flashes 120 ms: the face `accent`, scale −6 %, the icon in `on_accent`;
    - `set_lit(on)` turns the icon `accent_text` (the window stands);
    - the icon is `hubqt.pixmap(icon_name, colour, px(14))`.
  - `Burster(frame, parts, face, scale)`, where `parts()` returns the part rects in the frame's
    px and `face()` returns an (r, g, b):
    - `run(opening, origin_global, done, on_tick=None) -> bool` (False when it cannot start);
    - `stop()`, `busy() -> bool`, and `effect` (the QGraphicsEffect, made once and held);
    - `on_tick(shape)` is called on every tick with the shape `(x0, y0, x1, y1)` in frame px,
      which the edge panel uses for its mask;
    - with animations off, `run` returns False.
  - `burst_class()`: the effect `_burst_class` moved here from `maya_hubpop`. It also draws
    `hubburst.light(plan, ms)` as added light (`QPainter.CompositionMode_Plus`), clipped to the
    shape:
    - an edge is a band `EDGE_GLOW·scale` each side in `accent` at alpha 0.55·k, plus a core
      `EDGE_CORE·scale` each side in `#fff1e2` (the Time Bar's `RIM`) at 0.9·k;
    - the top is a 1.5 px `accent` line at alpha 0.95·top and a `TOP_GLOW·scale` gradient down
      from 0.32·top.

- [ ] **Step 1: Write the failing tests** (`tests/test_hubwindow.py`)

```python
"""maya_hubwindow - the floating window's and the rail card's look B and burst. Offscreen Qt.
Spec: docs/superpowers/specs/2026-10-18-floating-windows-design.md."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tests  # noqa: F401

from PySide6 import QtCore, QtGui, QtWidgets

import maya_hubburst as hubburst
import maya_hubmotion as hubmotion
import maya_hubstyle as hubstyle
import maya_hubwindow as hubwindow
from unittest import mock


def _app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _rgb(image, x, y):
    c = image.pixelColor(x, y)
    return (c.red(), c.green(), c.blue())


def _hex(name):
    v = hubstyle.TOKENS[name]
    return (int(v[1:3], 16), int(v[3:5], 16), int(v[5:7], 16))


class Frame(unittest.TestCase):

    def setUp(self):
        self.app = _app()
        self.frame = hubwindow.frame_class()(1.0)
        self.frame.resize(240, 160)
        layout = QtWidgets.QVBoxLayout(self.frame)
        layout.setContentsMargins(5, 34, 5, 5)
        self.frame.content = QtWidgets.QFrame()
        self.frame.content.setObjectName("testContent")
        layout.addWidget(self.frame.content)
        hubwindow.dress(self.frame, 1.0)
        self.frame.show()
        self.app.processEvents()

    def render(self):
        image = QtGui.QImage(240, 160, QtGui.QImage.Format_ARGB32)
        image.fill(0)
        self.frame.render(image)
        return image

    def test_the_frame_face_is_the_panel_and_the_content_the_card(self):
        image = self.render()
        self.assertEqual(_rgb(image, 120, 20), _hex("panel"))
        self.assertEqual(_rgb(image, 120, 100), _hex("card"))

    def test_no_stripe_and_no_accent_along_the_edges(self):
        image = self.render()
        accent = _hex("accent")
        for x, y in ((2, 80), (120, 1), (4, 40)):
            self.assertNotEqual(_rgb(image, x, y), accent)

    def test_a_lit_frame_paints_the_accent_ring(self):
        self.frame.level = 1.0
        image = self.render()
        r, g, b = _rgb(image, 120, 1)
        self.assertGreater(r, 180)


class Pill(unittest.TestCase):

    def setUp(self):
        self.app = _app()
        self.pill = hubwindow.pill_class()("x", 1.0)
        self.pill.show()

    def test_a_pill_is_24_by_22(self):
        self.assertEqual((self.pill.width(), self.pill.height()), (24, 22))

    def test_hover_lifts_it_and_rest_stops_its_timer(self):
        self.pill.hover(True)
        self.pill.advance(200.0)
        self.assertAlmostEqual(self.pill.level, 1.0, places=2)
        self.pill.hover(False)
        self.pill.advance(400.0)
        self.assertEqual(self.pill.level, 0.0)
        self.assertFalse(self.pill.timer.isActive())

    def test_a_press_flashes_for_120_ms(self):
        self.pill.press()
        self.assertGreater(self.pill.flash_at(0.0), 0.9)
        self.assertEqual(self.pill.flash_at(121.0), 0.0)

    def test_animations_off_lands_at_once(self):
        with mock.patch.object(hubmotion, "enabled", lambda: False):
            self.pill.hover(True)
            self.assertEqual(self.pill.level, 1.0)


class Burst(unittest.TestCase):

    def setUp(self):
        self.app = _app()
        self.frame = hubwindow.frame_class()(1.0)
        self.frame.resize(240, 160)
        self.frame.show()
        self.app.processEvents()
        self.ended = []
        self.burster = hubwindow.Burster(
            self.frame, lambda: [(5, 5, 230, 24), (5, 120, 230, 30)],
            lambda: (42, 44, 48), 1.0)

    def test_a_burst_runs_and_ends_plain(self):
        origin = self.frame.mapToGlobal(QtCore.QPoint(10, 10))
        self.assertTrue(self.burster.run(True, (origin.x(), origin.y()),
                                         lambda: self.ended.append(1)))
        self.assertTrue(self.burster.busy())
        self.frame.grab()
        self.burster.effect.ms = self.burster.effect.plan.total
        self.burster.tick_now()
        self.assertEqual(self.ended, [1])
        self.assertFalse(self.burster.busy())
        self.assertFalse(self.burster.effect.isEnabled())

    def test_the_shape_is_reported_each_tick(self):
        shapes = []
        origin = self.frame.mapToGlobal(QtCore.QPoint(10, 10))
        self.burster.run(True, (origin.x(), origin.y()), lambda: None, on_tick=shapes.append)
        self.frame.grab()
        self.burster.effect.ms = 40.0
        self.burster.tick_now()
        self.assertTrue(shapes)
        x0, y0, x1, y1 = shapes[-1]
        self.assertLess(x1 - x0, 240)

    def test_the_light_is_added_inside_the_shape(self):
        origin = self.frame.mapToGlobal(QtCore.QPoint(120, 80))
        self.burster.run(True, (origin.x(), origin.y()), lambda: None)
        self.frame.grab()
        self.burster.effect.ms = 30.0
        image = self.frame.grab().toImage()
        plan = self.burster.effect.plan
        edge = [e for e in hubburst.light(plan, 30.0).edges if e[0] == "x"][0]
        lit = image.pixelColor(int(edge[1]), 80)
        self.assertGreater(lit.red(), 120)

    def test_with_animations_off_nothing_runs(self):
        with mock.patch.object(hubmotion, "enabled", lambda: False):
            self.assertFalse(self.burster.run(True, (0, 0), lambda: None))
        self.assertFalse(self.burster.busy())
```

- [ ] **Step 2: Run them to see them fail**

Run: `... -m unittest tests.test_hubwindow -v`
Expected: FAIL (`No module named 'maya_hubwindow'`).

- [ ] **Step 3: Implement `SkeldarAnim/maya_hubwindow.py`**

The module docstring names the date, the animator's words, the spec and what it holds. The rest:

- `_CLASSES = {}` caches the Qt classes, made on first use (Qt is imported lazily through
  `maya_hubqt.qt()`, as in `maya_hubpop`).
- `frame_class()`: subclass `hubqt._frame_class()`, but do NOT call its `paintEvent` (it would
  paint the skin's `QFrame[skCard]` face). The `paintEvent`:
  1. `QPainter` with antialiasing;
  2. fill the rounded rect `widget.rect()` (radius `px(8)`) with `panel`;
  3. stroke it 1 px with `track_edge`;
  4. if `self.content` is a valid widget, fill its geometry (mapped into the frame) rounded
     `px(6)` with `card`;
  5. end that painter;
  6. if `level > 0.002 or flash > 0.002`, call `hubqt.paint_light(self, self.level, self.flash,
     self.scale)`.

  `dress(frame, scale)`: `frame.setAttribute(Qt.WA_StyledBackground, False)` and
  `frame.content.setStyleSheet("background: transparent;")`, so the stylesheet draws no face over
  ours. The frame's `skCard` property is NOT set: the skin's `QFrame[skCard]` rule must not paint
  it.
- `pill_class()`: a `QToolButton` with `setFixedSize(px(24), px(22))`, `setAutoRaise(True)`,
  `setCursor(PointingHandCursor)`, `level`, `_hovered`, `_press_t0 = None`, a 16 ms `QTimer`
  `timer` and `_last` (`time.monotonic()` in ms).
  - `enterEvent` → `hover(True)`; `leaveEvent` → `hover(False)`; `mousePressEvent` → `press()`,
    then `super`.
  - `hover(on)`: with animations off, `level = 1.0 if on else 0.0` and `update()`; else start the
    timer.
  - `press()`: `_press_t0 = now` and start the timer.
  - `advance(dt)`: `level = maya_timebar.look.approach(level, 1.0 if _hovered else 0.0, dt,
    tlook.HOVER_MS)`; stop the timer when the level is at its goal and
    `flash_at(now - _press_t0) == 0`; then `update()`.
  - `flash_at(age) = max(0.0, 1.0 - age / 120.0)` while `0 <= age < 120`, else 0.0.
  - `paintEvent`:
    - scale `s = 1 + 0.10 * level - 0.06 * flash` about the centre;
    - the face `mix(field, hover, level)`, then `mix(face, accent, flash)`;
    - the rings: `for i in range(4)`, alpha `46 * level * (5 - i) / 4 / 255`, width 1.6·scale,
      inset `-(1.6 * i + 0.8)·scale` outside the face;
    - the icon pixmap centred, re-made in `on_accent` while `flash > 0.5`;
    - `set_lit(on)` re-makes the icon in `accent_text` / `muted`.
  - Use `HOVER_MS = tlook.HOVER_MS if hasattr(tlook, "HOVER_MS") else 110`: check
    `maya_timebar/look.py` and `bar.py` for the name first, and import it if it exists.
- `burst_class()`: move `maya_hubpop._burst_class` here VERBATIM, then add the light at the end of
  `_draw`, after `CompositionMode_DestinationIn`, before `p.end()`:

```python
                    lit = hubburst.light(self.plan, self.ms)
                    if lit.edges or lit.top > 0.003:
                        p.setCompositionMode(QtGui.QPainter.CompositionMode_Plus)
                        x0, y0, x1, y1 = (v * k for v in state.shape)
                        p.setClipRect(QtCore.QRectF(x0, y0, x1 - x0, y1 - y0))
                        sc = self.plan.scale * k
                        for axis, pos, inten in lit.edges:
                            for half, colour, alpha in (
                                    (hubburst.EDGE_GLOW * sc, ACCENT, 0.55 * inten),
                                    (hubburst.EDGE_CORE * sc, RIM, 0.9 * inten)):
                                _band(p, QtCore, QtGui, axis, pos * k, half, colour, alpha,
                                      (x0, y0, x1, y1))
                        if lit.top > 0.003:
                            _top(p, QtCore, QtGui, x0, x1, lit.top, hubburst.TOP_GLOW * sc,
                                 max(1.0, 1.5 * sc))
```

  with module-level helpers:

```python
ACCENT = hubstyle.TOKENS["accent"]
RIM = "#fff1e2"          # maya_timebar.bar.RIM: light's hot core


def _band(p, QtCore, QtGui, axis, pos, half, colour, alpha, shape):
    """One racing edge's band of added light, across the shape."""
    x0, y0, x1, y1 = shape
    c = QtGui.QColor(colour)
    clear = QtGui.QColor(c)
    clear.setAlphaF(0.0)
    c.setAlphaF(max(0.0, min(1.0, alpha)))
    if axis == "x":
        grad = QtGui.QLinearGradient(pos - half, 0, pos + half, 0)
        rect = QtCore.QRectF(pos - half, y0, 2 * half, y1 - y0)
    else:
        grad = QtGui.QLinearGradient(0, pos - half, 0, pos + half)
        rect = QtCore.QRectF(x0, pos - half, x1 - x0, 2 * half)
    grad.setColorAt(0.0, clear)
    grad.setColorAt(0.5, c)
    grad.setColorAt(1.0, clear)
    p.fillRect(rect, QtGui.QBrush(grad))


def _top(p, QtCore, QtGui, x0, x1, top, depth, line):
    """The card's lit top edge: a line and a glow fading down."""
    c = QtGui.QColor(ACCENT)
    c.setAlphaF(min(1.0, 0.95 * top))
    p.fillRect(QtCore.QRectF(x0, 0, x1 - x0, line), c)
    grad = QtGui.QLinearGradient(0, 0, 0, depth)
    g = QtGui.QColor(ACCENT)
    g.setAlphaF(min(1.0, 0.32 * top))
    clear = QtGui.QColor(ACCENT)
    clear.setAlphaF(0.0)
    grad.setColorAt(0.0, g)
    grad.setColorAt(1.0, clear)
    p.fillRect(QtCore.QRectF(x0, 0, x1 - x0, depth), QtGui.QBrush(grad))
```

  Check `maya_timebar/bar.py` for `RIM` and import it if it is a module constant
  (`from maya_timebar import bar` imports Qt: only do that inside the class factory).
- `Burster`: the logic of today's `Popup._burst_effect`, `_burst`, `_end_burst` and
  `_burst_plan`, without the window:

```python
class Burster(object):
    """A frame's burst out of a global point, or its fold into one (maya_hubburst), drawn by
    the held effect; `on_tick(shape)` hears the shape each tick (the edge's mask)."""

    def __init__(self, frame, parts, face, scale):
        self.frame, self.parts, self.face, self.scale = frame, parts, face, scale
        self.effect = None
        self.anim = None
        self._origin = None
        self._done = None
        self._on_tick = None

    def busy(self):
        try:
            return bool(self.effect is not None and self.effect.isEnabled())
        except RuntimeError:
            return False

    def _plan(self, opening):
        q = hubqt.qt()
        o = self.frame.mapFromGlobal(q.QtCore.QPoint(int(self._origin[0]), int(self._origin[1])))
        make = hubburst.plan_open if opening else hubburst.plan_close
        return (make((o.x(), o.y()), (self.frame.width(), self.frame.height()),
                     self.parts(), self.scale), self.face())

    def run(self, opening, origin, done, on_tick=None):
        if not hubmotion.enabled() or self.frame is None or not hubqt._valid(self.frame):
            return False
        try:
            if self.effect is None:
                self.effect = burst_class()(self._plan)
                self.frame.setGraphicsEffect(self.effect)    # held: trap 201
            self.stop(quiet=True)
            self._origin = origin
            self._done, self._on_tick = done, on_tick
            self.effect.begin(opening)
            self.frame.update()
        except Exception:                                        # noqa: BLE001
            traceback.print_exc()
            self.stop(quiet=True)
            return False
        q = hubqt.qt()
        anim = q.QtCore.QVariantAnimation()
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setDuration(int(hubburst.MAX_MS))
        anim.valueChanged.connect(lambda v: self._tick(v * hubburst.MAX_MS))
        anim.finished.connect(self._finish)
        self.anim = anim
        anim.start()
        return True

    def tick_now(self):
        """One tick at the effect's current ms (the tests hold the animation)."""
        self._tick(self.effect.ms)

    def _tick(self, ms):
        effect = self.effect
        if effect is None:
            return
        try:
            effect.ms = ms
            self.frame.update()
            if self._on_tick is not None and effect.plan is not None:
                self._on_tick(hubburst.at(effect.plan, ms).shape)
            if effect.done():
                self._finish()
        except RuntimeError:                                     # the frame is gone
            self.stop(quiet=True)

    def _finish(self):
        done, self._done = self._done, None
        self.stop(quiet=True)
        if done is not None:
            done()

    def stop(self, quiet=False):
        anim, self.anim = self.anim, None
        if anim is not None:
            try:
                anim.stop()
            except RuntimeError:
                pass
        if self.effect is not None:
            try:
                self.effect.stop()
                self.frame.update()
            except RuntimeError:
                self.effect = None
```

  `_finish` is reached twice (`done()` inside `_tick`, then the animation's `finished` signal):
  the `done, self._done = self._done, None` swap makes the second call do nothing.

- [ ] **Step 4: Run the tests**

Run: `... -m unittest tests.test_hubwindow -v`
Expected: PASS. Then `... -m unittest tests.test_hubpop -v`: still PASS, because `maya_hubpop`
still has its own `_burst_class` until Task 5.

- [ ] **Step 5: Commit**

`git add SkeldarAnim/maya_hubwindow.py tests/test_hubwindow.py`; `git add -p SkeldarAnim/install.py`
(only the payload row). `git commit -F msg.txt`.
Message: `feat(hubwindow): look B frame, painted pill, the burst with its light`.

---

### Task 4: The stripe, the top accent and the rail icon's bar removed; the floating dot

**Files:**
- Modify: `SkeldarAnim/maya_hubqt.py` (`_frame_class`, `paint_stripe`, `Card.__init__` line
  `self.frame.stripe = colour`, `Skin._current_sheet`, new `Skin.set_floating`)
- Modify: `SkeldarAnim/maya_hub.py` (comment at `_build_skin`: «a card's group is the colour of
  its stripe» → «the colour of its jump»)
- Test: `tests/test_hubqt.py` (the three stripe tests at lines ~563-610 reversed), `tests/test_hub.py`
  (~725, ~738)

First message the «Меню для Chanel box» session that you are editing `maya_hubqt.py`: `Card`,
`_frame_class`, `Skin._current_sheet` and `set_floating`, away from the side panel menu.

**Interfaces:**
- Produces:
  - `Skin.set_floating(key, on) -> bool`: the rail or jump icon of `key` carries a 5-logical-px
    accent dot at its top right while its window stands. The icon is re-made by
    `hubqt.icon_with_dot(name, colour, size, dot)`: the section's icon pixmap with the dot painted
    in `accent`, plus a soft ring at alpha 0.35;
  - `Skin.floating`, a set of keys.

- [ ] **Step 1: Write the failing tests** (replace `test_a_card_carries_its_group_stripe`,
  `test_the_stripe_is_painted_inside_the_card`, `test_a_lit_card_keeps_its_stripe`)

```python
    def test_a_card_paints_no_group_stripe(self):
        """2026-10-18 («мусорная полоска с левого края и сверху ... это баг»): no bar."""
        card = self.skin.add_card("alpha", "Alpha", "user", "#7fa9e6", "#23324a")
        self.assertFalse(hasattr(card.frame, "stripe") and card.frame.stripe)
        self.assertFalse(hasattr(hubqt, "paint_stripe"))

    def test_the_card_left_edge_is_the_card_face(self):
        card = self.skin.add_card("alpha", "Alpha", "user", "#7fa9e6", "#23324a")
        card.frame.resize(200, 80)
        image = QtGui.QImage(200, 80, QtGui.QImage.Format_ARGB32)
        image.fill(0)
        card.frame.render(image)
        c = image.pixelColor(2, 40)
        self.assertNotEqual((c.red(), c.green(), c.blue()), (0x7f, 0xa9, 0xe6))

    def test_the_rail_icon_on_show_has_no_coloured_bar(self):
        sheet = self.rail_skin._current_sheet("alpha")
        self.assertNotIn("border-left", sheet)

    def test_a_section_with_a_window_shows_a_dot_on_its_icon(self):
        self.rail_skin.set_floating("alpha", True)
        self.assertIn("alpha", self.rail_skin.floating)
        self.rail_skin.set_floating("alpha", False)
        self.assertNotIn("alpha", self.rail_skin.floating)
```

Use the existing fixtures of `tests/test_hubqt.py`: read the class holding the old stripe tests,
and the `Rail` class for a rail-layout skin. Reuse their `setUp`. If none gives `rail_skin`, build
`hubqt.Skin(QtWidgets.QWidget(), layout="rail")` with one `add_jump("alpha", "Alpha", "user",
"#7fa9e6", group="scene")`. In `tests/test_hub.py` rewrite the two docstrings and assertions that
say a card shows its group as a stripe: the group shows on the jump icon only.

- [ ] **Step 2: Run them to see them fail**

Run: `... -m unittest tests.test_hubqt tests.test_hub -v`
Expected: FAIL on the four new tests.

- [ ] **Step 3: Implement**
  - Delete `paint_stripe`.
  - In `CardFrame` remove `self.stripe = None` and the `if self.stripe:` paint, and rewrite the
    docstring: «Since 2026-10-18 no group stripe (the animator: a bug)».
  - In `Card.__init__` remove `self.frame.stripe = colour`.
  - `_current_sheet`: `"QToolButton {{ background: {0}; border: none; border-radius: {1}px; }}"`
    with `card_active` and `px(5)`. `_jump_colour` stays: the icon keeps its colour.
  - `set_floating`:

```python
    def set_floating(self, key, on):
        """The jump icon of section `key` with a dot while its window stands (2026-10-18)."""
        button = self.jumps.get(key)
        if on:
            self.floating.add(key)
        else:
            self.floating.discard(key)
        if button is None or not _valid(button):
            return bool(on)
        q = qt()
        size = self.px(16)
        colour = self._jump_colour.get(key, hubstyle.TOKENS["muted"])
        name = self._jump_icon.get(key, "")
        button.setIcon(icon_with_dot(name, colour, size, self.px(5)) if on
                       else icon(name, colour, size))
        return bool(on)
```

  - Initialise `self.floating = set()` in `Skin.__init__`.
  - `icon_with_dot(name, colour, size, dot)` (module level, beside `icon`):

```python
def icon_with_dot(name, colour, size, dot):
    """The icon `name` with an accent dot at its top right (a window stands, 2026-10-18)."""
    q = qt()
    QtCore, QtGui = q.QtCore, q.QtGui
    pix = pixmap(name, colour, size)
    painter = QtGui.QPainter(pix)
    try:
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setPen(QtCore.Qt.NoPen)
        ring = QtGui.QColor(hubstyle.TOKENS["accent"])
        ring.setAlphaF(0.35)
        painter.setBrush(ring)
        r = QtCore.QRectF(size - dot - 1.5, -0.5, dot + 2.0, dot + 2.0)
        painter.drawEllipse(r)
        painter.setBrush(QtGui.QColor(hubstyle.TOKENS["accent"]))
        painter.drawEllipse(QtCore.QRectF(size - dot - 0.5, 0.5, dot, dot))
    finally:
        painter.end()
    return QtGui.QIcon(pix)
```

  Check that `pixmap(...)` returns a `QPixmap` drawable by a `QPainter` (read its definition near
  `def icon(` in `maya_hubqt.py`). If it returns a cached object, copy it first:
  `pix = QtGui.QPixmap(pixmap(...))`.

- [ ] **Step 4: Run the tests**

Run: `... -m unittest tests.test_hubqt tests.test_hub -v`
Expected: PASS.

- [ ] **Step 5: Commit** your hunks only (`git add -p SkeldarAnim/maya_hubqt.py SkeldarAnim/maya_hub.py
  tests/test_hubqt.py tests/test_hub.py`).
Message: `fix(hub): no group stripe on cards, no bar on the rail icon; a dot for a window`.

---

### Task 5: The floating window (`maya_hubpop`)

**Files:**
- Modify: `SkeldarAnim/maya_hubpop.py`
- Test: `tests/test_hubpop.py`

**Interfaces:**
- Consumes:
  - Task 2: `rules.screen_for`, `place_by_point`, `place_on_screens`, `WINDOW_POS_VAR`,
    `encode_place`, `decode_place`, `MAX_HEIGHT`;
  - Task 3: `hubwindow.frame_class`, `dress`, `pill_class`, `Burster`;
  - Task 4: the hub's `paint_floating(key, on)` (Task 8 adds it to `maya_hub`; here it is called
    through `_hub()`, guarded like `paint_popped`).
- Produces (the hub and the radial menu call these):
  - `open_popup(key, place=None, animate=False, origin=None) -> Popup`: the `panel` argument and
    the «no 3D view» refusal are gone; the `offset` argument is renamed `place` (logical global);
  - `open_at(key, point, animate=True)`: as today, but no viewport is asked;
  - `close_popup(key, forget=True, animate=False, origin=None)`, unchanged;
  - `toggle(key)` → `present(key, origin=None)`: opens when closed; when open, raises it and
    flashes it (`Popup.flash()`), and it stays open. Returns True. `toggle` stays as an alias for
    old callers;
  - `screens() -> [(x, y, w, h)]`: `QGuiApplication.screens()`' `availableGeometry()`, physical,
    else `[(0, 0, 1920, 1080)]` (tests patch it).

- [ ] **Step 1: Write the failing tests** (in `tests/test_hubpop.py`)

  - Change `Seams.setUp`: drop the patches of `model_panels`, `active_panel` and `_gl_rect`; add
    `mock.patch.object(hubpop, "screens", lambda: [SCREEN])` with
    `SCREEN = (0, 0, 1920, 1040)`.
  - Delete the tests that pin the viewport:
    - `test_no_viewport_says_so_and_opens_nothing`;
    - `test_the_default_place_is_inside_the_viewport_top_right`;
    - `test_a_second_popup_cascades_from_the_first`;
    - `test_the_popup_follows_its_viewport`;
    - `test_it_hides_while_its_panel_is_not_visible_and_shows_again`;
    - `test_a_drag_is_clamped_to_the_viewport_and_remembered`;
    - `test_the_popup_stays_inside_the_viewport_while_it_is_widened`;
    - `test_toggle_opens_then_closes`.
  - Rewrite `test_the_title_row_carries_the_section_name_and_a_close_button` for the pills.
  - Add:

```python
class Floating(Seams):
    """2026-10-18: a window, free of the viewport."""

    def test_a_window_opens_with_no_viewport_at_all(self):
        popup = hubpop.open_popup("alpha")
        self.assertIsNotNone(popup)
        self.assertFalse(hasattr(popup, "panel") and popup.panel)

    def test_with_no_place_it_stands_by_its_point(self):
        popup = hubpop.open_popup("alpha", origin=(600, 400))
        self.assertEqual((popup.root.x(), popup.root.y()), (600 - 18, 400 - 14))

    def test_a_drag_may_leave_any_viewport_and_is_kept_on_its_screen(self):
        popup = hubpop.open_popup("alpha", origin=(600, 400))
        popup._grab((610, 405))
        popup._drag((1900, 1030))
        x, y = popup.root.x(), popup.root.y()
        self.assertEqual(x + popup.root.width(), 1920)
        self.assertEqual(y + popup.root.height(), 1040)
        popup._drop()
        self.assertIn(rules.WINDOW_POS_VAR.format("alpha"), self.cmds.vars)

    def test_a_place_off_every_screen_is_dropped(self):
        self.cmds.vars[rules.WINDOW_POS_VAR.format("alpha")] = "5000.00,100.00"
        popup = hubpop.open_popup("alpha", origin=(600, 400))
        self.assertEqual((popup.root.x(), popup.root.y()), (582, 386))

    def test_the_old_viewport_offset_is_not_read(self):
        self.cmds.vars[rules.POS_VAR.format("alpha")] = "10.00,10.00"
        popup = hubpop.open_popup("alpha", origin=(600, 400))
        self.assertEqual((popup.root.x(), popup.root.y()), (582, 386))

    def test_present_on_a_standing_window_flashes_and_makes_no_copy(self):
        first = hubpop.open_popup("alpha")
        self.assertTrue(hubpop.present("alpha"))
        self.assertIs(hubpop._state()["popups"]["alpha"], first)
        self.assertGreater(first.frame.flash, 0.0)

    def test_no_follow_timer_runs(self):
        hubpop.open_popup("alpha")
        self.assertIsNone(hubpop._state()["timer"])

    def test_the_frame_is_look_b_with_pills(self):
        popup = hubpop.open_popup("alpha")
        self.assertIsInstance(popup.frame, hubwindow.frame_class())
        names = [b.objectName() for b in popup.root.findChildren(hubwindow.pill_class())]
        self.assertTrue(any(n.startswith("skeldarAnimPopupClose_") for n in names))
        self.assertTrue(any(n.startswith("skeldarAnimPopupRoll_") for n in names))

    def test_a_restore_needs_no_3d_view(self):
        self.cmds.vars[rules.POPUPS_VAR] = "alpha"
        self.cmds.vars[rules.WINDOW_POS_VAR.format("alpha")] = "300.00,200.00"
        self.assertEqual(hubpop._restore(), ["alpha"])
        popup = hubpop._state()["popups"]["alpha"]
        self.assertEqual((popup.root.x(), popup.root.y()), (300, 200))
```

  Add `import maya_hubwindow as hubwindow` at the top. Keep the Burst tests: they call
  `popup.show_open(...)`, whose signature changes to `show_open(animate=False, origin=None)`, so
  update those calls.

- [ ] **Step 2: Run them to see them fail**

Run: `... -m unittest tests.test_hubpop -v`
Expected: FAIL (no `screens`, no `present`, the viewport patches gone).

- [ ] **Step 3: Implement**, in this order:

  1. **Delete** `FOLLOW_MS`, `GL_CLASS`, `model_panels`, `active_panel`, `_gl_rect`, `_rect_of`,
     `panel_at`, `_ensure_timer`, `_stop_timer`, `_tick`, `Popup.follow`, `Popup.panel`,
     `Popup.hidden`, `Popup.offset`, `_popup_frame_class`, `_paint_outline`, `_burst_class`
     (now in `maya_hubwindow`) and `rules.default_offset` with its tests.
     - Keep `st["timer"]` as None in `_state()`. Old tests and `destroy_all` read it; `destroy_all`
       stops a timer an OLDER module object left running: `if st.get("timer"):
       st["timer"].stop()`; `st["timer"] = None`.
  2. **`screens()`**, as in Interfaces.
  3. **`Popup.place`** — `place_window(self, origin)`:

```python
    def place_window(self, origin=None):
        """The window's top-left: its remembered place when that still falls on a screen,
        else by `origin` (the point it came from; the cursor when None) - 2026-10-18."""
        w, h = self.root.width(), self.root.height()
        shown = screens()
        x_y = None
        if self.place is not None:
            x_y = rules.place_on_screens(self.place, w, h, shown, self.scale)
        if x_y is None:
            point = origin or _cursor_point() or (shown[0][0] + 100, shown[0][1] + 100)
            x_y = rules.place_by_point(point, w, h, shown, self.scale)
            self.place = (x_y[0] / self.scale, x_y[1] / self.scale)
        self.root.move(int(x_y[0]), int(x_y[1]))
```

  4. **Drag**:

```python
    def _drag(self, point):
        if self.grab is None:
            return
        w, h = self.root.width(), self.root.height()
        rect = rules.screen_for(point, screens())
        x, y = rules.clamp_origin(point[0] - self.grab[0], point[1] - self.grab[1], w, h, rect)
        self.root.move(x, y)
        self.place = (x / self.scale, y / self.scale)

    def _drop(self):
        if self.grab is None:
            return
        self.grab = None
        if self.place is not None:
            _save_place(self.key, self.place)
```

     `stored_place(key)` / `_save_place(key, place)` read and write `rules.WINDOW_POS_VAR`;
     `stored_offset` / `_save_offset` go.
  5. **Sizes**: everywhere `_rect_of(self.panel)` was used (`_fit`, `_grip_drag`, `_settle`,
     `_place_at`), use the window's screen: `rules.screen_for(self._centre(), screens())`, where
     `_centre()` is the root's centre in global px. `_place_at(rect)` goes; a roll-up or unroll that
     changes the height re-clamps the window onto its screen with `rules.clamp_origin`.
  6. **`_window()`**:
     - the frame is `hubwindow.frame_class()(s)`, objectName `"skeldarAnimPopupFrame_" + tag`;
     - a content card `w.QFrame()`, objectName `"skeldarAnimPopupCard_" + tag`, set as
       `frame.content`, holds the scroll area;
     - the frame column's margins are `px(5), px(0), px(5), px(5)`. The title row sits in the
       frame column above the content card, its height fixed at `px(34)` with margins
       `px(5), 0, 0, 0`;
     - in the title row:
       - the icon is a `QLabel` with `hubqt.pixmap(sec.icon, colour, px(15))` and no chip
         background;
       - the name is a `QLabel` of `sec.label.upper()`, named `"skeldarAnimPopupName_" + tag`,
         styled `color: {muted}; font-weight: bold; letter-spacing: 1px; font-size:
         {caption}px;`, where caption is `hubstyle.px(8.5, s)` (the heading role's size: read
         `{caption}` in `maya_hubstyle._SHEET`);
       - the roll and close buttons are `hubwindow.pill_class()("chevron-down", s)` and
         `("x", s)`, named `skeldarAnimPopupRoll_<tag>` / `skeldarAnimPopupClose_<tag>`;
     - drop `frame.stripe` and `frame.accent`;
     - call `hubwindow.dress(frame, s)` after the stylesheet is set;
     - `_paint_roll` sets the roll pill's icon name (`chevron-down` / `chevron-right`) through a
       `set_icon(name)` on the pill (add it in Task 3's class if missing: re-make the pixmap,
       `update()`).
  7. **The burst**:
     - `self.burster = hubwindow.Burster(self.frame, self._burst_parts, self._burst_face,
       self.scale)` after the frame exists;
     - `_burst_face()` returns `hubburst.blend(card, card_active, frame.level)`;
     - `_burst(opening, origin, done)` becomes `return self.burster.run(opening, origin or
       _cursor_point() or (self.root.x(), self.root.y()), done)`, with the root
       `WA_TransparentForMouseEvents` set before and cleared in `_end_burst`;
     - `bursting()` is `self.burster.busy()`;
     - `show_open(animate=False, origin=None)` drops `rect` and the fade fallback's `_place_at`
       (the window stands still while it fades).
  8. **`flash()`**: the frame's `flash` from 1 to 0 over `hubmotion.FLASH_MS`. Check its name in
     `maya_hubmotion` (the card's `pulse` uses it; read `Card.pulse` in `maya_hubqt`) and reuse
     `hubmotion.flash_at`. Raise the window (`root.raise_()`) first. With animations off it does
     nothing but raise.
  9. **`open_popup(key, place=None, animate=False, origin=None)`**:
     - build;
     - `popup.place = place if place is not None else stored_place(key)`;
     - `popup.place_window(origin)`;
     - `popup.show_open(animate=..., origin=origin)`;
     - `_notify(key, True)`: `paint_popped` AND `paint_floating`.
  10. **`present(key, origin=None)`**: `if is_open(key): popup = st["popups"][key];
      popup.flash(); return True`, else `return open_popup(key, animate=True, origin=origin) is
      not None`. `toggle = present`.
  11. **`open_at(key, point, animate=True)`**: close a standing one (`forget=False`); then
      `place = ((point[0] - AT_CURSOR[0] * scale) / scale, ...)`, kept on its screen by
      `place_window`; save it; open with `origin=point`.
  12. **`_restore`**: drop the `active_panel()` wait and `RESTORE_TRIES` / `_retry_later`. Wait
      instead for `_main_window()`: when it is None and `hubqt._maya_ui_ok()` is True, retry as
      today; in the tests `_main_window` is patched to None and `_maya_ui_ok` is False, so it
      opens at once.
  13. **`_notify(key, on)`**: also `_hub().paint_floating(key, on)`, each in its own try.
  14. Rewrite the module docstring's first paragraphs: a floating window since 2026-10-18, the
      animator's words, the spec. Keep the 2026-10-09 history as one paragraph.

- [ ] **Step 4: Run the tests**

Run: `... -m unittest tests.test_hubpop tests.test_hubpop_rules tests.test_hubwindow -v`
Expected: PASS. Then the whole suite (Global Constraints' command). Expected: PASS, except
`tests.test_hub` cases that call `paint_floating` (Task 8): run them after Task 8.

- [ ] **Step 5: Commit**

`git commit -F msg.txt -- SkeldarAnim/maya_hubpop.py SkeldarAnim/maya_hubpop_rules.py tests/test_hubpop.py tests/test_hubpop_rules.py`
Message: `feat(hubpop): sections open in floating windows, free of the viewport, look B`.

---

### Task 6: The edge rail's card in look B, with ✕

**Files:**
- Modify: `SkeldarAnim/maya_hubqt.py` (`Card.__init__` gains `windowed=False`, `on_close=None`;
  `Skin.__init__` gains `windowed=False`; `Skin.add_card` passes them;
  `Skin.rail_actions` wording)
- Modify: `SkeldarAnim/maya_hub.py` (`_build_skin(host=None, kind=None, windowed=False)`;
  `_ensure_edge` passes `windowed=True`; callback `"close"`)
- Test: `tests/test_hubqt.py`

**Interfaces:**
- Consumes: Task 3's `frame_class`, `dress`, `pill_class`.
- Produces:
  - `Card(..., windowed=False, on_close=None)`. With `windowed`:
    - the frame is `hubwindow.frame_class()(scale)` (not the skin's CardFrame), objectName still
      `"skeldarHubCard_" + key` and still `skCard` False;
    - the body sits on `frame.content`, a QFrame `"skeldarHubCardContent_" + key` that holds
      `self.body`;
    - the header icon has no chip; the title is in capitals, `muted`, bold, letter-spaced;
    - `self.popout` is a `pill_class()("float", scale)` named `"skeldarHubCardPopout_" + key`;
    - `self.close` is a `pill_class()("x", scale)` named `"skeldarHubCardClose_" + key`, whose
      click calls `on_close(key)`;
    - no chevron, no rule hairline under the head.
  - `Skin(..., windowed=False)`, `Skin.windowed`. `add_card` passes
    `windowed=self.windowed, on_close=lambda k: self._call("close", k)`.
  - `Card.set_popped(on)`: on a windowed card it calls `self.popout.set_lit(on)`.
  - `rail_actions` rows: `("Show here", ...)` and `("Open in a window", ...)`. The jump tooltip:
    `label + "\nCtrl+click or middle click: a window"`.
  - A new icon `float` in `maya_hubicons` (Tabler `external-link`: `M12 6h-6a2 2 0 0 0 -2 2v10a2
    2 0 0 0 2 2h10a2 2 0 0 0 2 -2v-6`, `M11 13l9 -9`, `M15 4h5v5`) if no such icon exists: check
    `maya_hubicons.ICONS` first, and add its MIT line as the module's other icons have.

- [ ] **Step 1: Write the failing tests**

```python
class Windowed(unittest.TestCase):
    """2026-10-18: the edge rail's card in look B, with a close button."""

    def setUp(self):
        self.app = _app()
        self.calls = []
        self.skin = hubqt.Skin(QtWidgets.QWidget(), layout="rail", windowed=True,
                               callbacks={"close": lambda k: self.calls.append(("close", k)),
                                          "popout": lambda k: self.calls.append(("popout", k))})
        self.skin.add_jump("alpha", "Alpha", "user", "#7fa9e6", group="scene")
        self.card = self.skin.add_card("alpha", "Alpha", "user", "#7fa9e6", "#23324a",
                                       collapsible=False)

    def test_a_windowed_card_has_a_close_pill_and_a_float_pill(self):
        self.assertIsInstance(self.card.close, hubwindow.pill_class())
        self.assertIsInstance(self.card.popout, hubwindow.pill_class())
        self.card.close.click()
        self.card.popout.click()
        self.assertEqual(self.calls, [("close", "alpha"), ("popout", "alpha")])

    def test_its_frame_is_look_b(self):
        self.assertIsInstance(self.card.frame, hubwindow.frame_class())
        self.assertIs(self.card.body.parent(), self.card.frame.content)

    def test_a_docked_card_has_no_close(self):
        skin = hubqt.Skin(QtWidgets.QWidget(), layout="rail")
        card = skin.add_card("alpha", "Alpha", "user", "#7fa9e6", "#23324a", collapsible=False)
        self.assertIsNone(getattr(card, "close", None))

    def test_the_rail_menu_opens_a_window(self):
        labels = [label for label, _fn in self.skin.rail_actions("alpha")]
        self.assertIn("Open in a window", labels)
```

  Import `maya_hubwindow as hubwindow` in `tests/test_hubqt.py`.

- [ ] **Step 2: Run them to see them fail**

Run: `... -m unittest tests.test_hubqt -v`
Expected: FAIL (`windowed` unexpected).

- [ ] **Step 3: Implement**
  - In `Card.__init__`, branch on `windowed` around the frame, the header row and the body's
    parent, as in Interfaces. Keep every objectName the non-windowed card uses: `Skin`,
    `card_shape`, `rail_rest` and the hub find widgets by them.
  - Without `windowed`, set `self.close = None`.
  - In `maya_hub._ensure_edge`: `_SKIN = _build_skin(host=current.slot, kind="rail",
    windowed=True)`.
  - `_build_skin` passes `windowed` to `qt.Skin(...)`.
  - `_callbacks()["close"] = _press_rail_close`, a function added in Task 7. Until Task 7, define
    it as `lambda key: None` with a comment, so this task's tests pass on their own.

- [ ] **Step 4: Run the tests**

Run: `... -m unittest tests.test_hubqt tests.test_hub -v`
Expected: PASS.

- [ ] **Step 5: Commit** your hunks only.
Message: `feat(hub): the edge rail's card in look B with a close button`.

---

### Task 7: The rail card bursts out of its icon, folds into ✕ / ⧉ (`maya_hubedge`, `maya_hub`)

**Files:**
- Modify: `SkeldarAnim/maya_hubedge.py` (`Edge.__init__` gains `burst=None`; `reveal(hold=False,
  origin=None)`, `conceal(origin=None)`, `_rail_slide(showing, origin=None)`, `burst_shape`
  in `_set_frame`)
- Modify: `SkeldarAnim/maya_hub.py` (`focus`, `_press_popout`, `_press_popup`, new
  `_press_rail_close`, new `_rail_burst`, new `paint_floating`)
- Test: `tests/test_hubedge.py`, `tests/test_hub.py`

**Interfaces:**
- Consumes:
  - Task 3: `hubwindow.Burster`;
  - Task 5: `maya_hubpop.present(key, origin)`, `maya_hubpop.open_at`;
  - Task 6: the windowed `Card` and `Skin.cards`, `Skin.shown`.
- Produces:
  - `Edge(..., burst=None)`: `burst(showing, origin, done, on_shape) -> bool`, a seam; None keeps
    `_rail_slide`'s old slide;
  - `Edge.burst_shape`: None, or a host-local `(x, y, w, h)` that cuts the card rects of the mask
    while a burst runs;
  - `Edge.reveal(hold=False, origin=None)`, `Edge.conceal(origin=None)`;
  - in `maya_hub`:
    - `_rail_burst(showing, origin, done, on_shape) -> bool`;
    - `_press_rail_close(key)`: the ✕ of the edge's card;
    - `_press_popout(key)`: the ⧉ of any card;
    - `paint_floating(key, on)`.

- [ ] **Step 1: Write the failing tests** (in `tests/test_hubedge.py`; reuse its fake host and
  seams; read the `RailDock` class added 2026-10-17 for the rail-mode fixture)

```python
class RailBurst(RailDock):
    """2026-10-18: the rail card bursts out of the icon pressed, folds into the point."""

    def make(self):
        self.bursts = []

        def burst(showing, origin, done, on_shape):
            self.bursts.append((showing, origin))
            on_shape((10, 10, 50, 40))
            self.done = done
            return True

        return self.build(burst=burst)

    def test_reveal_bursts_from_the_origin_and_shows_the_frame_whole(self):
        edge = self.make()
        edge.reveal(origin=(40, 120))
        self.assertEqual(self.bursts, [(True, (40, 120))])
        self.assertEqual(edge.frame(), edge.host.width())
        self.assertIsNotNone(edge.burst_shape)
        self.assertEqual(edge.burst_shape[2:], (40, 30))   # width and height survive the move
        self.done()
        self.assertIsNone(edge.burst_shape)
        self.assertTrue(edge.shown)

    def test_conceal_folds_into_its_point_then_rests_on_the_rail(self):
        edge = self.make()
        edge.reveal(origin=(40, 120))
        self.done()
        edge.conceal(origin=(200, 30))
        self.assertEqual(self.bursts[-1], (False, (200, 30)))
        self.done()
        self.assertEqual(edge.frame(), min(edge.host.width(), edge.rest_px()))
        self.assertFalse(edge.shown)

    def test_without_a_burst_the_old_slide_runs(self):
        edge = self.build(burst=lambda *a: False)
        edge.reveal(origin=(40, 120))
        self.assertTrue(edge.shown)
```

  `RailDock`'s builder may be named differently: adapt `self.build(...)` to the fixture's own
  constructor call, passing `burst=`. The `on_shape` argument is in FRAME coords of the card; the
  edge converts it to host coords through a `to_host` seam. In the test the seam is the identity
  plus the card's offset: assert whatever the fixture's offset gives, computed in the test, not a
  literal.

  In `tests/test_hub.py`, add a test that `focus(key)` with a rail edge standing calls
  `edge.reveal(origin=...)` with the cursor (patch `maya_hub._cursor` to return `(5, 6)`), and
  that `_press_rail_close("alpha")` calls `edge.conceal(origin=(5, 6))`. Use the existing
  edge-mode fixtures there (search `test_hub.py` for `RailDock` / `edge()`).

- [ ] **Step 2: Run them to see them fail**

Run: `... -m unittest tests.test_hubedge tests.test_hub -v`
Expected: FAIL (`burst` unexpected, no `origin`).

- [ ] **Step 3: Implement**
  - In `Edge`, store `self.burst = burst` and `self.burst_shape = None`.
  - `_rail_slide(showing, origin=None)`:
    1. if `self.burst` is set and a motion is on, then: for showing, set the frame to the whole
       width at once (`self._set_frame(width)`), `_shown = True`, `_rest_out = True`, raise the
       host;
    2. call `ran = self.burst(showing, origin, done, on_shape)` with:
       - `on_shape(shape)`: `self.burst_shape = (x0, y0, x1 - x0, y1 - y0)` mapped into host
         coords by the card's offset, then `self._set_frame(self._frame)` (the mask again);
       - `done()`: `self.burst_shape = None`; when hiding, `self._shown = False` and
         `self._set_frame(rest)`; then `self._rail_done(showing)`;
    3. if `ran` is False, run today's slide.
  - In `_set_frame`'s rail branch, when `self.burst_shape` is not None, intersect each card rect
    with `QRegion(*self.burst_shape)` before uniting.
  - `reveal(hold=False, origin=None)` and `conceal(origin=None)` pass `origin` on in rail mode.
  - `maya_hub`:

```python
def _rail_burst(showing, origin, done, on_shape):
    """The edge rail's card bursting out of `origin`, or folding into it (2026-10-18)."""
    if not is_skinned() or _SKIN.shown not in _SKIN.cards or origin is None:
        return False
    card = _SKIN.cards[_SKIN.shown]
    hubwindow = __import__("maya_hubwindow")
    burster = getattr(card, "burster", None)
    if burster is None:
        burster = hubwindow.Burster(card.frame, lambda: _hubqt().card_parts(card),
                                    lambda: _hubburst().blend(hubstyle.TOKENS["card"],
                                                              hubstyle.TOKENS["card_active"],
                                                              card.frame.level),
                                    _SKIN.scale)
        card.burster = burster
    return burster.run(showing, origin, done, on_tick=on_shape)
```

  - `_hubburst()` is `import maya_hubburst; return maya_hubburst`.
  - `hubqt.card_parts(card) -> [(x, y, w, h)]`, added in `maya_hubqt` beside `card_shape`: the
    header rect and `hubburst.rows(card.body, kids, rect_of, px(ROW_MAX), clip)` in the frame's
    coords, banded to `MAX_PARTS - 1`. This is the logic of today's `Popup._burst_parts`; move
    the shared `kids` / `rect_of` into a helper both call.
  - Pass `burst=_rail_burst` to `he.Edge(...)` in `_ensure_edge`.
  - `focus(key)` in the rail-edge branch: `point = _cursor()`; the card out and the same key →
    `current.conceal(origin=point)`; else `_show_on_rail(key)` (with `animate=False`, the burst
    is the motion) then `current.reveal(origin=point)`.
  - `_press_rail_close(key)`: `current = edge()`; if it is a rail edge, `current.conceal(origin=
    _cursor())`.
  - `_press_popout(key)`:

```python
def _press_popout(key):
    """A card's ⧉ (2026-10-18): the section's floating window bursts out of the press; on the
    edge rail the card folds into the same point at the same time."""
    import maya_hubpop
    point = _cursor()
    current = edge()
    try:
        opened = maya_hubpop.present(key, origin=point)
    except Exception:                                        # noqa: BLE001
        print(traceback.format_exc())
        say("The window could not be opened - the Script Editor has the details")
        return False
    if (current is not None and getattr(current, "rail", False) and _skin_at(current)
            and current.shown and _SKIN.shown == key):
        current.conceal(origin=point)
    return opened
```

  - `_press_popup(key)` (Ctrl+click, middle click, the rail menu, the radial menu's road):
    `maya_hubpop.open_at(key, point)`, falling back to `_press_popout(key)`.
  - `paint_floating(key, on)`: `_SKIN.set_floating(key, on)` when skinned; return `bool(on)`.

- [ ] **Step 4: Run the tests**

Run: the whole suite.
Expected: PASS.

- [ ] **Step 5: Commit** your hunks only.
Message: `feat(hubedge): the rail card bursts out of its icon and folds into the point pressed`.

---

### Task 8: The rest of the wiring, the filmstrip, the docs

**Files:**
- Modify:
  - `SkeldarAnim/maya_radial.py`: docstring line 14, «opens its popup» → «opens its window»;
    `open_at` stays;
  - `SkeldarAnim/maya_hubqt.py`: the popout tooltip «Open {0} in a floating window», non-windowed
    too;
  - `docs/interface-motion.md`: Scope, «the section popups' burst» → «the section windows' burst
    (2026-10-18: the Time Bar's numbers)»;
  - `CLAUDE.md`: a new section at the end, your hunk only.
- Create: `docs/superpowers/plans/render_floating_window.py`, which writes
  `docs/superpowers/plans/floating_window.png`.

- [ ] **Step 1: The filmstrip script**

```python
"""Render the floating window and the edge rail's card in look B at chosen instants of their
burst, offscreen at 150 % (2026-10-18, spec 2026-10-18-floating-windows-design.md).

    $env:QT_QPA_PLATFORM='offscreen'
    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/render_floating_window.py
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "SkeldarAnim"))

from PySide6 import QtCore, QtGui, QtWidgets  # noqa: E402

import maya_hubburst as hubburst              # noqa: E402
import maya_hubwindow as hubwindow            # noqa: E402

SCALE = 1.5
MOMENTS = (0, 40, 90, 150, 230, 320, 520, 900)


def window():
    frame = hubwindow.frame_class()(SCALE)
    frame.resize(int(300 * SCALE), int(260 * SCALE))
    column = QtWidgets.QVBoxLayout(frame)
    column.setContentsMargins(int(5 * SCALE), int(34 * SCALE), int(5 * SCALE), int(5 * SCALE))
    frame.content = QtWidgets.QFrame()
    inner = QtWidgets.QVBoxLayout(frame.content)
    for text in ("Knot", "Offset", "Orient", "Local x2", "World x2", "Aim", "Snapshot"):
        button = QtWidgets.QPushButton(text)
        button.setFixedHeight(int(24 * SCALE))
        inner.addWidget(button)
    column.addWidget(frame.content)
    hubwindow.dress(frame, SCALE)
    frame.show()
    QtWidgets.QApplication.processEvents()
    return frame


def main():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    frame = window()
    burster = hubwindow.Burster(frame, lambda: [(0, 0, frame.width(), int(34 * SCALE))] + [
        (b.mapTo(frame, QtCore.QPoint()).x(), b.mapTo(frame, QtCore.QPoint()).y(), b.width(),
         b.height()) for b in frame.findChildren(QtWidgets.QPushButton)],
        lambda: (42, 44, 48), SCALE)
    origin = frame.mapToGlobal(QtCore.QPoint(int(20 * SCALE), int(18 * SCALE)))
    cell_w, cell_h = frame.width() + 20, frame.height() + 40
    sheet = QtGui.QImage(cell_w * 4, cell_h * 2, QtGui.QImage.Format_ARGB32)
    sheet.fill(QtGui.QColor("#4d5562"))
    painter = QtGui.QPainter(sheet)
    painter.setPen(QtGui.QColor("#e4e4e6"))
    for i, ms in enumerate(MOMENTS):
        burster.run(True, (origin.x(), origin.y()), lambda: None)
        burster.anim.stop()
        frame.grab()
        burster.effect.ms = float(ms)
        image = frame.grab().toImage()
        x, y = (i % 4) * cell_w + 10, (i // 4) * cell_h + 30
        painter.drawText(x, y - 10, "open %d ms" % ms)
        painter.drawImage(x, y, image)
        burster.stop()
    painter.end()
    out = os.path.join(HERE, "floating_window.png")
    sheet.save(out)
    print("wrote", out, "plan total", hubburst.plan_open((0, 0), (300, 260), [], 1.0).total)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it and look at the picture**

Run: `$env:QT_QPA_PLATFORM='offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/render_floating_window.py`
Expected: `wrote ...floating_window.png`. Open it with the Read tool and check:
- at 0 ms, a small shape by the top-left;
- at 90 ms, orange racing edges inside a growing card;
- at 520 ms, the whole window, the top edge's light fading;
- at 900 ms, plain: no stripe, no orange along the top, the panel face round the card.
Fix what does not match.

- [ ] **Step 3: Measure a burst's paint** (the checklist's budget)

  Add to the script: time 30 `frame.grab()` calls with `effect.ms = 90` and print the median in
  ms. Expected: under ~8 ms at 450 × 390 px. Record the number in the CLAUDE.md section.

- [ ] **Step 4: The CLAUDE.md section**, after the last section, in the file's style:
  - `## Floating windows in place of the viewport popups (2026-10-18)`;
  - the animator's words;
  - the mockup URL https://claude.ai/artifact/2oSCA43qWv64YxqQmHhZhW and what was chosen (B, 1, the
    card goes into the window);
  - the spec and plan paths;
  - what changed per module (window free of the viewport, place `skeldarHubWindowPos_<key>`, look
    B, `maya_hubwindow`, the burst's numbers and light, the stripe and the rail icon's bar gone, the
    rail card's ✕ and ⧉, the dot);
  - the proof (the test counts, the filmstrip, the measured paint);
  - «Not seen in a GUI Maya».

  Also edit the CLAUDE.md lines that now lie: the sentence in "The hub as a rail and one card"
  about the Ctrl-click popup, and the "maya_hubpop" description in the 2026-10-17 burst section
  («this replaces the popup burst's numbers»). Edit only those lines; stage with `git add -p` and
  take only your hunks (other sessions have uncommitted CLAUDE.md edits).

- [ ] **Step 5: The whole suite, then commit**

Run the Global Constraints' command. Expected: all PASS, and note the count.

```bash
git add docs/superpowers/plans/render_floating_window.py docs/superpowers/plans/floating_window.png
git add -p CLAUDE.md docs/interface-motion.md SkeldarAnim/maya_radial.py SkeldarAnim/maya_hubqt.py
git commit -F msg.txt
```
Message: `docs: floating windows - the filmstrip, CLAUDE.md, the motion rules`.
Do NOT push: the animator decides when (memory `parallel-sessions-in-repo.md`: ask before push).
