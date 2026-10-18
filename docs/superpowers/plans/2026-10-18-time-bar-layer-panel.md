# Time Bar Layer Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Time Bar's three bookmark pills with a layers pill that opens a painted column of animation and display layers on the bar's right, resizable by its top edge, with optional lanes of each layer's keys over the timeline.

**Architecture:** The column and the lanes are two painted Qt.Tool windows of our own (`maya_timebar/layerpanel.py`), laid out by pure functions (`layerlook.py`) and talking to Maya only through a link (`layerscene.py` in Maya, a fake in the tests), the way the strip talks through `scene.py`. The strip (`bar.py`) owns one `Panel` controller, opened by the new pill and the layer chip; the bottom edge (`edge.py`) does not hide while it is open.

**Tech Stack:** Python 3 in Maya 2027 (`maya.cmds`, `maya.mel`), PySide6 6.8.3 via `maya_hubqt.qt()`, stdlib `unittest` run with mayapy.

**Spec:** `docs/superpowers/specs/2026-10-18-time-bar-layer-panel-design.md`. Mockup: https://claude.ai/artifact/VPbk5HvyxNMuw6jZv1hc5u (version 2).

## Global Constraints

- Every number of motion is imported from `maya_timebar.look` (`UNROLL_MS`, `POP_OPEN_MS`, `FOLD_MS`, `CLOSE_MS`, `CLOSE_AFTER_MS`, `REVEAL_MS`, `popping`, `folding`, `burst_delay`, `ease_out_quint`, `ease_in_quint`, `back_out`, `approach`) or `bar` (`HOVER_MS` 110, `FLASH_MS` 120, `POP_MS` 200, `LIFT` 0.10, `FRAME_MS` 16). Never copied.
- Colours only from `maya_hubstyle.TOKENS`; one orange (`accent`) control in the column: **+ Layer**.
- Every length is logical px × `ui` (the display scale).
- `layerlook.py` imports the stdlib and `look` only (a subprocess test pins it).
- Every Maya write is one undo chunk named `skeldarTimeBarLayers`.
- Never keep a wrapper of a Maya widget (trap 135); never `grab()` one (trap 134).
- ⋮ → Interface animations off (`bar.animations_on()` False): every motion lands at its end at once.
- optionVars: `skeldarTimeBarLayersHeight` (int, logical px, default 268), `skeldarTimeBarLayersTab` (`"anim"` / `"disp"`), `skeldarTimeBarLayerLanes` (int 0/1, default 0).
- Object names: `skeldarTimeBarLayers` (column), `skeldarTimeBarLayerLanes` (lanes).
- Tests run from the repo root:
  `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.<module> -v`
  with `$env:QT_QPA_PLATFORM = 'offscreen'` for Qt tests. No `2>&1` on mayapy in PowerShell.
- Commit only your own files (`git add <paths>`); other sessions work in this repo.
- Live checks in a GUI Maya are the animator's: say «not seen in a GUI Maya».

## File Structure

| file | responsibility |
|---|---|
| `SkeldarAnim/maya_timebar/layerlook.py` (new) | pure layout and rules: rects, hits, height clamp, order, signature, the burst schedule |
| `SkeldarAnim/maya_timebar/layerscene.py` (new) | every read and write of animation and display layers, keys per layer for the selection |
| `SkeldarAnim/maya_timebar/layerpanel.py` (new) | `Panel` controller, the `Column` and `Lanes` windows, their painting and driver |
| `SkeldarAnim/maya_timebar/bar.py` | bookmark pills out, layers pill in, chip opens the panel, `kit()` paint helpers, panel fed by the strip |
| `SkeldarAnim/maya_timebar/edge.py` | the `"layers"` blocker |
| `tests/test_timebar_layerlook.py` (new) | layout and rules |
| `tests/test_timebar_layerscene.py` (new) | reads and writes on a fake `cmds` |
| `tests/test_timebar_layerpanel.py` (new) | the windows offscreen on a fake link |
| `tests/test_timebar_bar.py`, `tests/test_timebar_edge.py` | updated for the pill and the blocker |
| `docs/superpowers/plans/verify_timebar_layers.py` (new) | mayapy standalone proof of `layerscene` |
| `docs/superpowers/plans/render_timebar_layers.py` (new) | the filmstrip → `timebar_layers.png` |
| `docs/superpowers/plans/bench_timebar_layers.py` (new) | the cost |
| `CLAUDE.md` | a section for the panel |

---

### Task 1: Measure Maya's layer commands before building on them

Maya's merge and a few query flags are used below; their exact names are measured first.

**Files:**
- Create: `docs/superpowers/plans/probe_timebar_layers.py`

**Interfaces:**
- Produces: the measured facts that Task 3 writes down in `layerscene.py`'s module docstring: the merge procedure's name and arguments, what `animLayer -q -attribute` answers, the display layer attributes.

- [ ] **Step 1: Write the probe**

```python
"""Probe, mayapy standalone: the animation and display layer commands the Time Bar's
layer panel builds on (2026-10-18). Prints facts; changes no file."""
import maya.standalone
maya.standalone.initialize(name="python")
import maya.cmds as cmds
import maya.mel as mel

cube = cmds.polyCube(name="probeCube")[0]
cmds.setKeyframe(cube, attribute="translateX", time=0, value=0)
cmds.setKeyframe(cube, attribute="translateX", time=10, value=5)
cmds.select(cube)
a = cmds.animLayer("A", addSelectedObjects=True)
b = cmds.animLayer("B", addSelectedObjects=True)
cmds.setKeyframe(cube, attribute="translateX", time=5, value=2, animLayer=b)
print("root:", cmds.animLayer(q=True, root=True))
print("children of root:", cmds.animLayer(cmds.animLayer(q=True, root=True), q=True, children=True))
print("B attributes:", cmds.animLayer(b, q=True, attribute=True))
print("B curve for tx:", cmds.animLayer(b, q=True, findCurveForPlug=cube + ".translateX"))
print("base curve for tx:", cmds.animLayer(cmds.animLayer(q=True, root=True), q=True,
                                           findCurveForPlug=cube + ".translateX"))
for proc in ("animLayerMerge", "performAnimLayerMerge", "animLayerMergeLayers"):
    print(proc, mel.eval('whatIs "%s"' % proc))
print("A attrs:", [x for x in ("mute", "solo", "lock", "weight", "override") if cmds.attributeQuery(x, node=a, exists=True)])
d = cmds.createDisplayLayer(name="probeLayer", noRecurse=True)
print("display:", d, [x for x in ("visibility", "hideOnPlayback", "displayType", "color", "displayOrder",
                                  "overrideRGBColors", "overrideColorRGB")
                       if cmds.attributeQuery(x, node=d, exists=True)])
print("members:", cmds.editDisplayLayerMembers(d, q=True, fullNames=True))
print("colorIndex 13:", cmds.colorIndex(13, q=True))
```

- [ ] **Step 2: Run it**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs\superpowers\plans\probe_timebar_layers.py`
Expected: lines for every print; at least one of the three merge names answers «Mel procedure found in ...». Note which one and read its proc in that `.mel` file (its signature and what it does with the layers it is given: it merges the given layers into the lowest of them).

- [ ] **Step 3: Write the facts at the top of the probe as a docstring block `FACTS = """..."""`** (the merge proc name and signature, the `-attribute` answer's form, the attributes found), then commit.

```bash
git add docs/superpowers/plans/probe_timebar_layers.py
git commit -m "docs(timebar): probe the layer commands the layer panel builds on"
```

---

### Task 2: `layerlook` — the column's layout and rules

**Files:**
- Create: `SkeldarAnim/maya_timebar/layerlook.py`
- Test: `tests/test_timebar_layerlook.py`

**Interfaces:**
- Consumes: `look.burst_delay(dx, dy, ui)`, `look.FOLD_MS` etc.
- Produces (all used by Task 4):
  - constants `ROW_H=30`, `ROW_GAP=3`, `HEAD_H=30`, `FOOT_H=28`, `STATUS_H=16`, `PAD=6`, `GRIP_H=9`, `MIN_H=150`, `DEFAULT_H=268`, `ABOVE=6`, `SIDE=6`, `TOP_ROOM=10`, `TABS=("anim","disp")`, `FOOT={"anim": (...), "disp": (...)}`, `TYPES=("", "T", "R")`
  - `clamp_height(h, room) -> float`
  - `column_rect(strip, timeline, height, ui) -> (x, y, w, h)` (global logical rects in, global rect out)
  - `lanes_rect(column, timeline) -> (x, y, w, h)`
  - `class Layout(width, height, rows, tab, ui)` with `.head`, `.segments` {tab: rect}, `.lanes`, `.well`, `.rows` [rect, in list coordinates scrolled by 0], `.foot` [(name, rect)], `.status`, `.grip`, `.content_h`, `.max_scroll`, `.row_at(i, scroll)`
  - `row_parts(rect, tab, ui, base=False) -> dict name -> rect`
  - `hit(layout, x, y, scroll) -> tuple | None`
  - `weight_at(x, rect) -> float`
  - `dimmed(row, rows) -> bool`
  - `step_type(t) -> int`
  - `signature(rows) -> tuple`
  - `schedule(parts, origin, ui) -> list of (open_delay, fold_delay)`

- [ ] **Step 1: Write the failing tests**

```python
"""The layer panel's layout and rules (2026-10-18), pure: no Maya, no Qt.
Spec: docs/superpowers/specs/2026-10-18-time-bar-layer-panel-design.md"""
import os
import subprocess
import sys
import unittest

from maya_timebar import layerlook as L
from maya_timebar import look

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SkeldarAnim")


def anim_rows(n):
    rows = [{"name": "L%d" % i, "label": "L%d" % i, "mode": "add", "weight": 1.0, "mute": False,
             "solo": False, "lock": False, "active": i == 0, "base": False} for i in range(n - 1)]
    return rows + [{"name": "BaseAnimation", "label": "BaseAnimation", "mode": "base", "weight": 1.0,
                    "mute": False, "solo": False, "lock": False, "active": False, "base": True}]


class Pure(unittest.TestCase):

    def test_imports_no_maya_and_no_qt(self):
        code = ("import sys; sys.path.insert(0, %r); import maya_timebar.layerlook; "
                "bad = [m for m in sys.modules if m.split('.')[0] in ('maya', 'PySide6', 'shiboken6')]; "
                "print(bad); sys.exit(1 if bad else 0)") % PLUGIN
        self.assertEqual(subprocess.call([sys.executable, "-c", code]), 0)


class Height(unittest.TestCase):

    def test_clamped_between_the_least_and_the_room(self):
        self.assertEqual(L.clamp_height(100, 600), L.MIN_H)
        self.assertEqual(L.clamp_height(300, 600), 300)
        self.assertEqual(L.clamp_height(900, 600), 600 - L.TOP_ROOM)

    def test_no_room_still_gives_the_least(self):
        self.assertEqual(L.clamp_height(300, 80), L.MIN_H)


class Place(unittest.TestCase):

    def test_the_column_stands_right_of_the_timeline_over_the_strip(self):
        strip = (100, 900, 1500, 84)
        timeline = (106, 940, 1100, 40)
        x, y, w, h = L.column_rect(strip, timeline, 268, 1.0)
        self.assertEqual(x, 106 + 1100 + L.SIDE)
        self.assertEqual(x + w, 100 + 1500 - L.SIDE)
        self.assertEqual(y + h, 900 - L.ABOVE)
        self.assertEqual(h, 268)

    def test_the_lanes_span_from_the_timeline_to_the_column(self):
        column = (1212, 626, 382, 268)
        timeline = (106, 940, 1100, 40)
        self.assertEqual(L.lanes_rect(column, timeline), (106, 626, 1212 - 106, 268))


class Layouts(unittest.TestCase):

    def test_rows_fill_the_well_and_scroll_past_it(self):
        lay = L.Layout(380, 268, anim_rows(12), "anim", 1.0)
        self.assertEqual(len(lay.rows), 12)
        self.assertEqual(lay.rows[1][1] - lay.rows[0][1], L.ROW_H + L.ROW_GAP)
        self.assertGreater(lay.max_scroll, 0)
        few = L.Layout(380, 268, anim_rows(2), "anim", 1.0)
        self.assertEqual(few.max_scroll, 0)

    def test_scale_multiplies_every_length(self):
        a, b = L.Layout(380, 268, anim_rows(3), "anim", 1.0), L.Layout(570, 402, anim_rows(3), "anim", 1.5)
        self.assertAlmostEqual(b.rows[0][3], a.rows[0][3] * 1.5)
        self.assertAlmostEqual(b.grip[3], a.grip[3] * 1.5)

    def test_the_foot_differs_by_tab(self):
        self.assertEqual([n for n, _r in L.Layout(380, 268, [], "anim", 1.0).foot],
                         ["add", "addsel", "remsel", "merge", "delete"])
        self.assertEqual([n for n, _r in L.Layout(380, 268, [], "disp", 1.0).foot],
                         ["add", "addsel", "remsel", "select", "delete"])

    def test_a_row_has_its_controls_left_to_right(self):
        parts = L.row_parts((0, 0, 360, 30), "anim", 1.0)
        order = ["mode", "name", "weight", "wnum", "mute", "solo", "lock"]
        xs = [parts[n][0] for n in order]
        self.assertEqual(xs, sorted(xs))
        disp = L.row_parts((0, 0, 360, 30), "disp", 1.0)
        self.assertEqual(sorted(disp), ["name", "playback", "swatch", "type", "visible"])

    def test_the_base_row_has_no_weight_and_no_solo(self):
        parts = L.row_parts((0, 0, 360, 30), "anim", 1.0, base=True)
        self.assertNotIn("weight", parts)
        self.assertNotIn("solo", parts)


class Hits(unittest.TestCase):

    def setUp(self):
        self.lay = L.Layout(380, 268, anim_rows(4), "anim", 1.0)

    def centre(self, rect):
        return rect[0] + rect[2] / 2.0, rect[1] + rect[3] / 2.0

    def test_grip_tab_lanes_and_foot(self):
        self.assertEqual(L.hit(self.lay, *self.centre(self.lay.grip), scroll=0), ("grip",))
        self.assertEqual(L.hit(self.lay, *self.centre(self.lay.segments["disp"]), scroll=0), ("tab", "disp"))
        self.assertEqual(L.hit(self.lay, *self.centre(self.lay.lanes), scroll=0), ("lanes",))
        name, rect = self.lay.foot[0]
        self.assertEqual(L.hit(self.lay, *self.centre(rect), scroll=0), ("foot", "add"))

    def test_a_row_and_its_parts_with_the_scroll(self):
        rect = self.lay.row_at(1, 0)
        parts = L.row_parts(rect, "anim", 1.0)
        self.assertEqual(L.hit(self.lay, *self.centre(parts["mute"]), scroll=0), ("row", 1, "mute"))
        self.assertEqual(L.hit(self.lay, *self.centre(parts["name"]), scroll=0), ("row", 1, "name"))
        scrolled = self.lay.row_at(2, L.ROW_H + L.ROW_GAP)
        self.assertEqual(scrolled, rect)

    def test_outside_the_rows_in_the_well_is_nothing(self):
        x, y, w, h = self.lay.well
        self.assertIsNone(L.hit(self.lay, x + w / 2.0, y + h - 2, scroll=0))


class Rules(unittest.TestCase):

    def test_weight_from_x(self):
        self.assertEqual(L.weight_at(0, (10, 0, 100, 14)), 0.0)
        self.assertEqual(L.weight_at(60, (10, 0, 100, 14)), 0.5)
        self.assertEqual(L.weight_at(500, (10, 0, 100, 14)), 1.0)

    def test_mute_and_solo_dim(self):
        rows = anim_rows(3)
        self.assertFalse(L.dimmed(rows[0], rows))
        rows[1]["mute"] = True
        self.assertTrue(L.dimmed(rows[1], rows))
        rows[0]["solo"] = True
        self.assertFalse(L.dimmed(rows[0], rows))
        self.assertFalse(L.dimmed(rows[2], rows))      # BaseAnimation is never left out by a solo

    def test_display_type_steps(self):
        self.assertEqual([L.step_type(t) for t in (0, 1, 2)], [1, 2, 0])

    def test_signature_sees_every_value(self):
        rows = anim_rows(2)
        before = L.signature(rows)
        rows[0]["weight"] = 0.5
        self.assertNotEqual(L.signature(rows), before)

    def test_schedule_nearest_first_in_and_farthest_first_out(self):
        parts = [(0, 0, 10, 10), (0, 200, 10, 10)]
        (o_far, f_far), (o_near, f_near) = L.schedule(parts, (5, 205), 1.0)
        self.assertLess(o_near, o_far)
        self.assertLess(f_far, f_near)
        self.assertEqual(o_near, look.burst_delay(0, 0))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run them to see them fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_timebar_layerlook -v`
Expected: ERROR, `ModuleNotFoundError: No module named 'maya_timebar.layerlook'`.

- [ ] **Step 3: Write `layerlook.py`**

```python
"""The Time Bar's layer panel, laid out (2026-10-18): pure functions of sizes and rows.
Stdlib and `look` only (a test pins it). Rects are (x, y, w, h); every length is
logical px x `ui`.

Spec: docs/superpowers/specs/2026-10-18-time-bar-layer-panel-design.md
"""

from . import look

ROW_H = 30          # a layer's row
ROW_GAP = 3
HEAD_H = 30         # the segments and the lanes button
FOOT_H = 28         # + Layer and the icon buttons
STATUS_H = 16       # the column's own line
PAD = 6             # inside the column
WELL_PAD = 3        # inside the list's well
GRIP_H = 9          # the top edge you drag
MIN_H = 150         # the least height (logical px)
DEFAULT_H = 268
ABOVE = 6           # between the column and the strip's top
SIDE = 6            # between the column and the timeline, and the strip's right
TOP_ROOM = 10       # left free under the viewport's top
TABS = ("anim", "disp")
TAB_LABELS = {"anim": "Animation", "disp": "Display"}
FOOT = {"anim": ("add", "addsel", "remsel", "merge", "delete"),
        "disp": ("add", "addsel", "remsel", "select", "delete")}
FOOT_TIPS = {"add": "A new layer from the selection (empty with nothing selected)",
             "addsel": "Add the selection to the layer",
             "remsel": "Take the selection out of the layer",
             "merge": "Merge the active layer into the one under it",
             "select": "Select the layer's objects",
             "delete": "Delete the layer"}
TYPES = ("", "T", "R")      # displayType 0 normal, 1 template, 2 reference
MODES = {"add": "ADD", "ovr": "OVR", "base": "BASE"}


def clamp_height(h, room):
    """The column's height: at least MIN_H, at most `room` less TOP_ROOM."""
    return max(MIN_H, min(float(h), float(room) - TOP_ROOM))


def column_rect(strip, timeline, height, ui):
    """Global (x, y, w, h) of the column: from the timeline's right plus SIDE to the
    strip's right less SIDE, its bottom ABOVE over the strip's top."""
    sx, sy, sw, _sh = strip
    tx, _ty, tw, _th = timeline
    x = tx + tw + SIDE * ui
    w = sx + sw - SIDE * ui - x
    return (x, sy - ABOVE * ui - height, w, height)


def lanes_rect(column, timeline):
    """Global (x, y, w, h) of the lanes: from the timeline's left to the column's left."""
    cx, cy, _cw, ch = column
    return (timeline[0], cy, cx - timeline[0], ch)


def _inside(rect, x, y):
    return rect[0] <= x < rect[0] + rect[2] and rect[1] <= y < rect[1] + rect[3]


class Layout(object):
    """Where everything of the column stands, in the column's own coordinates."""

    def __init__(self, width, height, rows, tab, ui):
        self.width, self.height, self.tab, self.ui = float(width), float(height), tab, float(ui)
        u, w, h = self.ui, self.width, self.height
        self.grip = (0.0, 0.0, w, GRIP_H * u)
        self.head = (PAD * u, 8 * u, w - 2 * PAD * u, HEAD_H * u - 8 * u)
        seg_w = 92 * u
        y = self.head[1]
        self.segments = {"anim": (PAD * u, y, seg_w, 24 * u),
                         "disp": (PAD * u + seg_w + 2 * u, y, seg_w * 0.85, 24 * u)}
        self.lanes = (w - PAD * u - 28 * u, y, 28 * u, 24 * u)
        foot_top = h - PAD * u - STATUS_H * u - FOOT_H * u
        self.well = (PAD * u, HEAD_H * u + 4 * u, w - 2 * PAD * u, foot_top - HEAD_H * u - 8 * u)
        wx, wy, ww, wh = self.well
        pitch = (ROW_H + ROW_GAP) * u
        self.rows = [(wx + WELL_PAD * u, wy + WELL_PAD * u + i * pitch, ww - 2 * WELL_PAD * u, ROW_H * u)
                     for i in range(len(rows))]
        self.content_h = len(rows) * pitch - ROW_GAP * u + 2 * WELL_PAD * u if rows else 0.0
        self.max_scroll = max(0.0, self.content_h - wh)
        names = FOOT.get(tab, FOOT["anim"])
        add_w = 76 * u
        icon = 28 * u
        fy = foot_top + 2 * u
        self.foot = [(names[0], (PAD * u, fy, add_w, 24 * u))]
        x = w - PAD * u - icon * (len(names) - 1) - 2 * u * (len(names) - 2)
        for name in names[1:]:
            self.foot.append((name, (x, fy, icon, 24 * u)))
            x += icon + 2 * u
        self.status = (PAD * u, h - PAD * u - STATUS_H * u, w - 2 * PAD * u, STATUS_H * u)

    def row_at(self, i, scroll):
        x, y, w, h = self.rows[i]
        return (x, y - scroll, w, h)


def row_parts(rect, tab, ui, base=False):
    """name -> rect of a row's controls, left to right."""
    x, y, w, h = rect
    u = ui
    cy = y + (h - 20 * u) / 2.0
    out = {}
    right = x + w - 6 * u
    if tab == "anim":
        for name in ("lock", "solo", "mute"):
            if not (base and name == "solo"):
                out[name] = (right - 20 * u, cy, 20 * u, 20 * u)
            right -= 22 * u
        if not base:
            out["wnum"] = (right - 30 * u, y, 30 * u, h)
            right -= 34 * u
            out["weight"] = (right - 60 * u, y + (h - 14 * u) / 2.0, 60 * u, 14 * u)
            right -= 64 * u
        out["mode"] = (x + 7 * u, y + (h - 16 * u) / 2.0, 32 * u, 16 * u)
        name_x = x + 45 * u
    else:
        for name in ("type", "playback", "visible"):
            width = 24 * u if name == "type" else 20 * u
            out[name] = (right - width, cy, width, 20 * u)
            right -= width + 2 * u
        out["swatch"] = (x + 9 * u, y + (h - 14 * u) / 2.0, 14 * u, 14 * u)
        name_x = x + 31 * u
    out["name"] = (name_x, y, max(0.0, right - 4 * u - name_x), h)
    return out


def hit(layout, x, y, scroll):
    """What is under (x, y): ("grip",), ("tab", t), ("lanes",), ("foot", name),
    ("row", i, part or "row"), ("scroll",) or None."""
    if _inside(layout.grip, x, y):
        return ("grip",)
    for tab, rect in layout.segments.items():
        if _inside(rect, x, y):
            return ("tab", tab)
    if _inside(layout.lanes, x, y):
        return ("lanes",)
    for name, rect in layout.foot:
        if _inside(rect, x, y):
            return ("foot", name)
    if _inside(layout.well, x, y):
        for i in range(len(layout.rows)):
            rect = layout.row_at(i, scroll)
            if _inside(rect, x, y):
                for part, prect in row_parts(rect, layout.tab, layout.ui).items():
                    if part != "name" and _inside(prect, x, y):
                        return ("row", i, part)
                return ("row", i, "name")
    return None


def weight_at(x, rect):
    return max(0.0, min(1.0, (x - rect[0]) / float(rect[2]))) if rect[2] > 0 else 0.0


def dimmed(row, rows):
    """A muted layer, or one left out by another's solo (BaseAnimation never is)."""
    if row.get("mute"):
        return True
    if row.get("base"):
        return False
    return any(r.get("solo") for r in rows) and not row.get("solo")


def step_type(t):
    return (int(t) + 1) % len(TYPES)


def signature(rows):
    return tuple(tuple(sorted(r.items())) for r in rows)


def schedule(parts, origin, ui):
    """(open delay, fold delay) of each part rect: in nearest the origin first,
    out farthest first (the Time Bar's burst, a vertical step counting 1.5)."""
    out = []
    for x, y, w, h in parts:
        dx, dy = x + w / 2.0 - origin[0], y + h / 2.0 - origin[1]
        d = abs(dx) + abs(dy) * 1.5
        out.append((look.burst_delay(dx, dy, ui), look.fold_delay(d, ui)))
    return out
```

- [ ] **Step 4: Run the tests until they pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_timebar_layerlook -v`
Expected: OK. If `test_a_row_has_its_controls_left_to_right` or a hit test fails, fix the arithmetic in `row_parts` / `Layout`, not the test.

- [ ] **Step 5: Commit**

```bash
git add SkeldarAnim/maya_timebar/layerlook.py tests/test_timebar_layerlook.py
git commit -m "feat(timebar): the layer panel's layout and rules, pure"
```

---

### Task 3: `layerscene` — layers read and written in Maya

**Files:**
- Create: `SkeldarAnim/maya_timebar/layerscene.py`
- Test: `tests/test_timebar_layerscene.py`
- Create: `docs/superpowers/plans/verify_timebar_layers.py`

**Interfaces:**
- Consumes: `scene._chunk(name)`, `scene.layers()` (the scene-tab scoped list), `scene.pick_layer(name)`, Task 1's facts (the merge procedure).
- Produces (the link Task 4 calls; every write returns `(ok: bool, message: str)`):
  - `anim_layers() -> [dict]` keys `name, label, mode ("add"/"ovr"/"base"), weight, weight_keyed, mute, solo, lock, active, base`; newest first, base last
  - `display_layers() -> [dict]` keys `name, label, colour ("#rrggbb" or ""), visible, playback, type (0/1/2)`
  - `keys_by_layer(names) -> {name: [times]}` for the selection
  - `pick(name)`, `set_flag(name, flag, on)` (flag in `mute, solo, lock`), `begin_weight()`, `set_weight(name, value)`, `end_weight()`, `set_mode(name, mode)`, `rename(name, new)`, `create_anim()`, `add_selection(name)`, `remove_selection(name)`, `merge_down(name)`, `delete_anim(name)`, `select_objects(name)`
  - `set_display(name, flag, value)` (flag in `visible, playback, type, colour`), `create_display()`, `display_add(name)`, `display_remove(name)`, `display_select(name)`, `delete_display(name)`
  - `option(name, default)`, `set_option(name, value)`

- [ ] **Step 1: Write the failing tests on a fake `cmds`**

```python
"""The layer panel's reads and writes (2026-10-18) on a fake cmds.
Spec: docs/superpowers/specs/2026-10-18-time-bar-layer-panel-design.md"""
import unittest

from maya_timebar import layerscene as S


class FakeCmds(object):
    """Just enough of maya.cmds for animation and display layers."""

    def __init__(self):
        self.attrs = {"BaseAnimation.mute": False, "BaseAnimation.lock": False,
                      "A.mute": False, "A.solo": False, "A.lock": False, "A.weight": 0.5, "A.override": False,
                      "B.mute": True, "B.solo": False, "B.lock": False, "B.weight": 1.0, "B.override": True,
                      "lay1.visibility": True, "lay1.hideOnPlayback": False, "lay1.displayType": 1,
                      "lay1.color": 13, "lay1.overrideRGBColors": False, "lay1.displayOrder": 1}
        self.selected = {"A": False, "B": True}
        self.selection = ["cube"]
        self.chunks = []
        self.calls = []

    def animLayer(self, name=None, q=False, e=False, **kw):
        self.calls.append(("animLayer", name, kw))
        if q and kw.get("root"):
            return "BaseAnimation"
        if q and kw.get("children"):
            return ["A", "B"] if name == "BaseAnimation" else []
        if q and kw.get("selected"):
            return self.selected.get(name, False)
        if q and kw.get("attribute"):
            return ["cube.translateX"] if name in ("A", "B") else []
        if q and "findCurveForPlug" in kw:
            return {"A": ["A_tx"], "B": ["B_tx"]}.get(name)
        if e and "selected" in kw:
            self.selected[name] = kw["selected"]
        return name or kw.get("name")

    def getAttr(self, plug):
        return self.attrs[plug]

    def setAttr(self, plug, value):
        self.calls.append(("setAttr", plug, value))
        self.attrs[plug] = value

    def listConnections(self, plug, source=True, destination=False, type=None):
        return []

    def ls(self, *a, **kw):
        if kw.get("type") == "displayLayer":
            return ["defaultLayer", "lay1"]
        if kw.get("selection"):
            return list(self.selection)
        return []

    def colorIndex(self, index, q=False):
        return [1.0, 0.0, 0.0]

    def keyframe(self, curve, q=True, timeChange=True):
        return {"A_tx": [0.0, 10.0], "B_tx": [5.0]}.get(curve, [])

    def undoInfo(self, **kw):
        self.chunks.append(kw)

    def delete(self, *nodes):
        self.calls.append(("delete", nodes))

    def select(self, *a, **kw):
        self.calls.append(("select", a, kw))

    def attributeQuery(self, attr, node=None, exists=False):
        return (node + "." + attr) in self.attrs


class Reads(unittest.TestCase):

    def setUp(self):
        self.cmds = FakeCmds()
        self.old = S.cmds
        S.cmds = self.cmds
        self.addCleanup(setattr, S, "cmds", self.old)

    def test_animation_layers_newest_first_base_last(self):
        rows = S.anim_layers()
        self.assertEqual([r["name"] for r in rows], ["B", "A", "BaseAnimation"])
        b, a, base = rows
        self.assertEqual((b["mode"], b["mute"], b["active"]), ("ovr", True, True))
        self.assertEqual((a["mode"], a["weight"]), ("add", 0.5))
        self.assertTrue(base["base"])

    def test_display_layers_without_the_default(self):
        rows = S.display_layers()
        self.assertEqual([r["name"] for r in rows], ["lay1"])
        self.assertEqual((rows[0]["visible"], rows[0]["playback"], rows[0]["type"]), (True, True, 1))
        self.assertEqual(rows[0]["colour"], "#ff0000")

    def test_keys_of_the_selection_in_each_layer(self):
        self.assertEqual(S.keys_by_layer(["A", "B"]), {"A": [0.0, 10.0], "B": [5.0]})


class Writes(Reads):

    def test_a_flag_is_one_undo_chunk(self):
        ok, _msg = S.set_flag("A", "mute", True)
        self.assertTrue(ok)
        self.assertTrue(self.cmds.attrs["A.mute"])
        self.assertEqual([c.get("openChunk") or c.get("closeChunk") for c in self.cmds.chunks], [True, True])

    def test_base_animation_has_no_solo_and_no_delete(self):
        self.assertFalse(S.set_flag("BaseAnimation", "solo", True)[0])
        self.assertFalse(S.delete_anim("BaseAnimation")[0])

    def test_display_flags(self):
        S.set_display("lay1", "playback", False)
        self.assertTrue(self.cmds.attrs["lay1.hideOnPlayback"])
        S.set_display("lay1", "type", 2)
        self.assertEqual(self.cmds.attrs["lay1.displayType"], 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to see them fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_timebar_layerscene -v`
Expected: ERROR, `No module named 'maya_timebar.layerscene'`.

- [ ] **Step 3: Write `layerscene.py`**

`scene._chunk` opens and closes an undo chunk named after its argument (read it in `scene.py` before using it; if its signature differs, write a local `_chunk` with `cmds.undoInfo(openChunk=True, chunkName=name)` / `closeChunk=True` in a `try/finally`). Put Task 1's facts in the docstring and use the measured merge procedure in `merge_down`.

```python
"""The Time Bar's layer panel in Maya (2026-10-18): animation and display layers
read and written, every write one undo chunk. The active scene tab's layers only.

Measured (docs/superpowers/plans/probe_timebar_layers.py): <copy Task 1's FACTS here>.

Spec: docs/superpowers/specs/2026-10-18-time-bar-layer-panel-design.md
"""

import contextlib

import maya.cmds as cmds

CHUNK = "skeldarTimeBarLayers"
FLAGS = ("mute", "solo", "lock")


@contextlib.contextmanager
def _chunk():
    cmds.undoInfo(openChunk=True, chunkName=CHUNK)
    try:
        yield
    finally:
        cmds.undoInfo(closeChunk=True)


def _active_only(names):
    try:
        from maya_scenetabs import scope
        return list(scope.active_only(names))
    except Exception:                                        # noqa: BLE001
        return list(names)


def _label(name):
    try:
        from maya_scenetabs import scope
        return scope.local(name)
    except Exception:                                        # noqa: BLE001
        return name.split(":")[-1]


def _get(plug, default=None):
    try:
        return cmds.getAttr(plug)
    except Exception:                                        # noqa: BLE001
        return default


def _hex(rgb):
    return "#%02x%02x%02x" % tuple(int(round(max(0.0, min(1.0, c)) * 255)) for c in rgb)


# -- reads -------------------------------------------------------------------------

def _anim_names():
    """(root, [layer, ...]) - every layer below the root, breadth first, scoped."""
    root = cmds.animLayer(q=True, root=True)
    if not root:
        return None, []
    found, i = [root], 0
    while i < len(found):
        found.extend(cmds.animLayer(found[i], q=True, children=True) or [])
        i += 1
    return root, _active_only(found[1:])


def anim_layers():
    """The animation layers, newest first, BaseAnimation last; [] without any."""
    root, names = _anim_names()
    if not root:
        return []
    picked = [n for n in names if cmds.animLayer(n, q=True, selected=True)]
    active = picked[-1] if picked else root
    rows = []
    for name in reversed(names):
        rows.append({"name": name, "label": _label(name),
                     "mode": "ovr" if _get(name + ".override", False) else "add",
                     "weight": float(_get(name + ".weight", 1.0)),
                     "weight_keyed": bool(cmds.listConnections(name + ".weight", source=True,
                                                               destination=False, type="animCurve")),
                     "mute": bool(_get(name + ".mute", False)), "solo": bool(_get(name + ".solo", False)),
                     "lock": bool(_get(name + ".lock", False)), "active": name == active, "base": False})
    rows.append({"name": root, "label": "BaseAnimation", "mode": "base", "weight": 1.0,
                 "weight_keyed": False, "mute": bool(_get(root + ".mute", False)), "solo": False,
                 "lock": bool(_get(root + ".lock", False)), "active": root == active, "base": True})
    return rows


def _colour(name):
    if _get(name + ".overrideRGBColors", False):
        rgb = _get(name + ".overrideColorRGB")
        return _hex(rgb[0] if rgb and isinstance(rgb[0], (list, tuple)) else rgb) if rgb else ""
    index = int(_get(name + ".color", 0) or 0)
    return _hex(cmds.colorIndex(index, q=True)) if index > 0 else ""


def display_layers():
    """Maya's display layers, the Layer Editor's order (displayOrder, highest first)."""
    names = [n for n in (cmds.ls(type="displayLayer") or []) if n.split(":")[-1] != "defaultLayer"]
    names = _active_only(names)
    names.sort(key=lambda n: -(_get(n + ".displayOrder", 0) or 0))
    return [{"name": n, "label": _label(n), "colour": _colour(n),
             "visible": bool(_get(n + ".visibility", True)),
             "playback": not bool(_get(n + ".hideOnPlayback", False)),
             "type": int(_get(n + ".displayType", 0) or 0)} for n in names]


def _selected_nodes():
    return set(n.split(".")[0] for n in (cmds.ls(selection=True) or []))


def keys_by_layer(names):
    """{layer: [times]} of the selection's keys in each layer of `names`."""
    nodes = _selected_nodes()
    out = {}
    if not nodes:
        return out
    root = cmds.animLayer(q=True, root=True)
    for name in names:
        times = set()
        plugs = []
        if name == root:
            for node in nodes:
                for attr in cmds.listAttr(node, keyable=True) or []:
                    plugs.append(node + "." + attr)
        else:
            plugs = [p for p in (cmds.animLayer(name, q=True, attribute=True) or [])
                     if p.split(".")[0] in nodes]
        for plug in plugs:
            try:
                curves = cmds.animLayer(name, q=True, findCurveForPlug=plug) or []
            except Exception:                                # noqa: BLE001 - trap 211
                curves = []
            if not curves and name == root:
                curves = cmds.listConnections(plug, source=True, destination=False, type="animCurve") or []
            for curve in curves:
                times.update(cmds.keyframe(curve, q=True, timeChange=True) or [])
        out[name] = sorted(times)
    return out


# -- writes on animation layers -------------------------------------------------------

def _is_root(name):
    return name == cmds.animLayer(q=True, root=True)


def pick(name):
    from . import scene
    with _chunk():
        scene.pick_layer(name)
    return True, ""


def set_flag(name, flag, on):
    if flag not in FLAGS:
        return False, "no such switch: %s" % flag
    if flag == "solo" and _is_root(name):
        return False, "BaseAnimation has no solo"
    with _chunk():
        cmds.setAttr(name + "." + flag, bool(on))
    return True, ""


_WEIGHT = {"open": False}


def begin_weight():
    cmds.undoInfo(openChunk=True, chunkName=CHUNK)
    _WEIGHT["open"] = True


def set_weight(name, value):
    """While dragging: a keyed weight is keyed at the current frame, else set."""
    value = max(0.0, min(1.0, float(value)))
    if cmds.listConnections(name + ".weight", source=True, destination=False, type="animCurve"):
        cmds.setKeyframe(name, attribute="weight", value=value)
    else:
        cmds.setAttr(name + ".weight", value)
    return True, ""


def end_weight():
    if _WEIGHT["open"]:
        cmds.undoInfo(closeChunk=True)
        _WEIGHT["open"] = False


def set_mode(name, mode):
    if _is_root(name):
        return False, "BaseAnimation has no mode"
    with _chunk():
        cmds.setAttr(name + ".override", mode == "ovr")
    return True, ""


def rename(name, new):
    new = (new or "").strip()
    if not new or _is_root(name):
        return False, "nothing renamed"
    with _chunk():
        done = cmds.rename(name, new)
    return True, "renamed to %s" % _label(done)


def create_anim():
    with _chunk():
        if cmds.ls(selection=True):
            name = cmds.animLayer("AnimLayer1", addSelectedObjects=True)
        else:
            name = cmds.animLayer("AnimLayer1")
        from . import scene
        scene.pick_layer(name)
    return True, "%s made" % _label(name)


def add_selection(name):
    if not cmds.ls(selection=True):
        return False, "nothing selected"
    with _chunk():
        cmds.animLayer(name, e=True, addSelectedObjects=True)
    return True, ""


def remove_selection(name):
    nodes = _selected_nodes()
    if not nodes:
        return False, "nothing selected"
    plugs = [p for p in (cmds.animLayer(name, q=True, attribute=True) or []) if p.split(".")[0] in nodes]
    if not plugs:
        return False, "the selection is not in %s" % _label(name)
    with _chunk():
        for plug in plugs:
            cmds.animLayer(name, e=True, removeAttribute=plug)
    return True, ""


def merge_down(name):
    """The layer into the one under it, by Maya's own merge (Task 1 measured it)."""
    rows = anim_layers()
    names = [r["name"] for r in rows]
    if name not in names or rows[names.index(name)]["base"]:
        return False, "BaseAnimation has nothing under it"
    under = names[names.index(name) + 1]
    import maya.mel as mel
    with _chunk():
        mel.eval('animLayerMerge {"%s", "%s"}' % (under, name))     # Task 1: the measured proc
    return True, "%s merged into %s" % (_label(name), _label(under))


def delete_anim(name):
    if _is_root(name):
        return False, "BaseAnimation stays"
    with _chunk():
        cmds.delete(name)
    return True, "%s deleted" % _label(name)


def select_objects(name):
    nodes = sorted(set(p.split(".")[0] for p in (cmds.animLayer(name, q=True, attribute=True) or [])))
    cmds.select(nodes, replace=True)
    return True, ""


# -- display layers ------------------------------------------------------------------

def set_display(name, flag, value):
    attr = {"visible": "visibility", "playback": "hideOnPlayback", "type": "displayType", "colour": "color"}.get(flag)
    if attr is None:
        return False, "no such switch: %s" % flag
    if flag == "playback":
        value = not value
    with _chunk():
        if flag == "colour":
            cmds.setAttr(name + ".overrideRGBColors", False)
        cmds.setAttr(name + "." + attr, value)
    return True, ""


def create_display():
    with _chunk():
        if cmds.ls(selection=True):
            name = cmds.createDisplayLayer(name="layer1", noRecurse=True)
        else:
            name = cmds.createDisplayLayer(name="layer1", empty=True)
    return True, "%s made" % _label(name)


def display_add(name):
    picked = cmds.ls(selection=True) or []
    if not picked:
        return False, "nothing selected"
    with _chunk():
        cmds.editDisplayLayerMembers(name, picked, noRecurse=True)
    return True, ""


def display_remove(name):
    picked = cmds.ls(selection=True) or []
    if not picked:
        return False, "nothing selected"
    with _chunk():
        cmds.editDisplayLayerMembers("defaultLayer", picked, noRecurse=True)
    return True, ""


def display_select(name):
    cmds.select(cmds.editDisplayLayerMembers(name, q=True, fullNames=True) or [], replace=True)
    return True, ""


def delete_display(name):
    with _chunk():
        cmds.delete(name)
    return True, "%s deleted" % _label(name)


# -- memory --------------------------------------------------------------------------

def option(name, default):
    return cmds.optionVar(q=name) if cmds.optionVar(exists=name) else default


def set_option(name, value):
    if isinstance(value, str):
        cmds.optionVar(stringValue=(name, value))
    else:
        cmds.optionVar(intValue=(name, int(value)))
```

Note for `anim_layers`: `scene.layers()` already scopes names by tab and reads the root as BaseAnimation; if Task 1 showed the tab's own root among `found[1:]` (`<tab>:AnimLayerRoot`), drop names for which `maya_scenetabs.layers.is_tab_root_name(name)` is True and treat the tab's root as the root (its row's `name` the tab root, `label` "BaseAnimation"). Add a fake-cmds test for it in this task if so.

- [ ] **Step 4: Run the unit tests until they pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_timebar_layerscene -v`
Expected: OK. Grow `FakeCmds` (not the module) when a call it lacks shows up.

- [ ] **Step 5: Write `verify_timebar_layers.py` (mayapy standalone) and run it**

```python
"""verify_timebar_layers.py - the Time Bar's layer panel's Maya half, mayapy standalone
(2026-10-18). Every write of maya_timebar.layerscene on a real scene, read back."""
import sys
import maya.standalone
maya.standalone.initialize(name="python")
import maya.cmds as cmds
sys.path.insert(0, r"C:/!!!Work/MayaScripts/SkeldarAnim")
for p in ("matrixNodes", "quatNodes"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass
from maya_timebar import layerscene as S

FAIL = []


def gate(n, ok, text):
    print("%s %2d %s" % ("PASS" if ok else "FAIL", n, text))
    if not ok:
        FAIL.append(n)


cube = cmds.polyCube(name="cube")[0]
for t, v in ((0, 0), (10, 5), (20, 0)):
    cmds.setKeyframe(cube, attribute="translateX", time=t, value=v)
cmds.select(cube)
ok, msg = S.create_anim()
rows = S.anim_layers()
gate(1, ok and len(rows) == 2 and rows[-1]["base"] and rows[0]["active"], "a layer made from the selection, active: %s" % msg)
first = rows[0]["name"]
cmds.setKeyframe(cube, attribute="translateX", time=5, value=3, animLayer=first)
S.create_anim()
rows = S.anim_layers()
gate(2, [r["base"] for r in rows] == [False, False, True], "newest first, base last: %s" % [r["label"] for r in rows])
second = rows[0]["name"]
keys = S.keys_by_layer([r["name"] for r in rows])
gate(3, keys[first] == [5.0] and keys[rows[-1]["name"]] == [0.0, 10.0, 20.0],
     "keys per layer: %s" % keys)
S.set_flag(first, "mute", True)
gate(4, cmds.getAttr(first + ".mute"), "mute written")
cmds.undo()
gate(5, not cmds.getAttr(first + ".mute"), "one undo takes the mute back")
S.begin_weight(); S.set_weight(first, 0.25); S.set_weight(first, 0.4); S.end_weight()
gate(6, abs(cmds.getAttr(first + ".weight") - 0.4) < 1e-6, "weight dragged to 0.4")
cmds.undo()
gate(7, abs(cmds.getAttr(first + ".weight") - 1.0) < 1e-6, "the whole drag is one undo")
S.set_mode(first, "ovr")
gate(8, cmds.getAttr(first + ".override"), "override")
ok, msg = S.merge_down(second)
gate(9, ok and second not in [r["name"] for r in S.anim_layers()], "merge down: %s" % msg)
gate(10, not S.delete_anim(cmds.animLayer(q=True, root=True))[0], "BaseAnimation is never deleted")
ok, msg = S.create_display()
d = S.display_layers()
gate(11, ok and len(d) == 1, "a display layer from the selection")
name = d[0]["name"]
S.set_display(name, "visible", False); S.set_display(name, "playback", False); S.set_display(name, "type", 2)
d = S.display_layers()[0]
gate(12, (d["visible"], d["playback"], d["type"]) == (False, False, 2), "V, P, type written: %s" % d)
cmds.select(clear=True); S.display_select(name)
gate(13, cmds.ls(selection=True) == [cube], "the layer's objects selected")
print("%d of 13 gates failed" % len(FAIL))
```

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs\superpowers\plans\verify_timebar_layers.py`
Expected: `0 of 13 gates failed`. A failing gate is a bug in `layerscene` (or in Task 1's reading): fix the module.

- [ ] **Step 6: Commit**

```bash
git add SkeldarAnim/maya_timebar/layerscene.py tests/test_timebar_layerscene.py docs/superpowers/plans/verify_timebar_layers.py
git commit -m "feat(timebar): the layer panel's reads and writes in Maya"
```

---

### Task 4: `layerpanel` — the column and the lanes

**Files:**
- Modify: `SkeldarAnim/maya_timebar/bar.py` (add `kit()`, the glyphs `layers`, `lanes`, `lock`, `plus`, `addsel`, `remsel`, `merge`, `select`, `trash`)
- Create: `SkeldarAnim/maya_timebar/layerpanel.py`
- Test: `tests/test_timebar_layerpanel.py`

**Interfaces:**
- Consumes: Task 2's `layerlook`, Task 3's link functions (names exactly as listed there), `bar.kit()`, `bar.animations_on()`, `bar.GLYPHS`, `bar.HOVER_MS`, `FLASH_MS`, `POP_MS`, `LIFT`, `FRAME_MS`.
- Produces (used by Task 5):
  - `layerpanel.Panel(strip, link, ui, tokens, motion, parent=None)` with
    `toggle(origin)`, `open(origin)`, `close(origin=None)`, `is_open() -> bool`, `place()`, `refresh(force=False)`, `on_time()`, `keys_dirty()`, `destroy()`, attributes `column`, `lanes` (the two windows), `phase` (`"closed"/"opening"/"open"/"closing"`).
  - `layerpanel.destroy_all()` (by object name).
  - `bar.kit()` → object with `colour(hex, alpha)`, `blend(a, b, u)`, `draw_glyph(p, name, rect, qcolour)`, `glow(p, rect, radius, hex, level, ui)`.

- [ ] **Step 1: Give `bar.py` its kit and glyphs**

In `bar.py`, at module level under `GLYPHS`, add the glyph paths (16 × 16):

```python
GLYPHS.update({
    "layers": "M8 1.2l7 3.6-7 3.6-7-3.6zM2.4 7.3L8 10.2l5.6-2.9 1.4.7L8 11.6 1 8zM2.4 10.5L8 13.4l5.6-2.9 1.4.7L8 14.8 1 11.2z",
    "lanes": "M1 3h4v2H1zM6 3h9v2H6zM1 7h7v2H1zM9 7h6v2H9zM1 11h3v2H1zM5 11h10v2H5z",
    "lock": "M4.5 7V5a3.5 3.5 0 0 1 7 0v2H13v7H3V7zm1.6 0h3.8V5a1.9 1.9 0 0 0-3.8 0z",
    "plus": "M7 2h2v5h5v2H9v5H7V9H2V7h5z",
    "addsel": "M2 2h6v2H4v8h4v2H2zM9 7h3V4l3.5 4-3.5 4V9H9z",
    "remsel": "M8 2h6v12H8v-2h4V4H8zM10 7H6.5V4L3 8l3.5 4V9H10z",
    "merge": "M3 2h2v4c0 1.2 1 2 3 2s3-.8 3-2V2h2v4c0 2-1.4 3.4-4 3.9V12h2.2L8 15l-3.2-3H7V9.9C4.4 9.4 3 8 3 6z",
    "select": "M3 1.5l9.5 7.2-4.2.6 2.5 4.6-1.9 1-2.5-4.7L3 13z",
    "trash": "M6 1h4v1.5h4V4H2V2.5h4zM3.5 5h9l-.8 10H4.3z",
})
```

Inside `classes()`, just before `return Strip, Timeline, RangeBlock, Pill`, add:

```python
    global _KIT
    _KIT = types.SimpleNamespace(colour=colour, blend=blend, draw_glyph=draw_glyph, glow=glow,
                                 halo=halo, soft_dot=soft_dot)
```

and at module level (with `import types` at the top and `_KIT = None` beside the constants):

```python
def kit():
    """The strip's paint helpers for the layer panel (made with the classes)."""
    if _KIT is None:
        classes()
    return _KIT
```

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_timebar_bar -v` (with `$env:QT_QPA_PLATFORM='offscreen'`). Expected: OK (nothing else changed yet).

- [ ] **Step 2: Write the failing panel tests**

```python
"""The Time Bar's layer panel offscreen (2026-10-18), on a fake link.
Spec: docs/superpowers/specs/2026-10-18-time-bar-layer-panel-design.md"""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import maya_hubqt
    QT = maya_hubqt.qt()
except Exception:                                            # noqa: BLE001
    QT = None

import maya_hubstyle
from maya_timebar import layerlook as L


class FakeLink(object):

    def __init__(self):
        self.log = []
        self.opts = {}
        self.anim = [
            {"name": "A2", "label": "A2", "mode": "add", "weight": 0.65, "weight_keyed": False, "mute": False,
             "solo": False, "lock": False, "active": True, "base": False},
            {"name": "A1", "label": "A1", "mode": "ovr", "weight": 1.0, "weight_keyed": False, "mute": True,
             "solo": False, "lock": False, "active": False, "base": False},
            {"name": "Base", "label": "BaseAnimation", "mode": "base", "weight": 1.0, "weight_keyed": False,
             "mute": False, "solo": False, "lock": False, "active": False, "base": True}]
        self.disp = [{"name": "lay1", "label": "lay1", "colour": "#7fa9e6", "visible": True, "playback": True, "type": 0}]

    def _w(self, *entry):
        self.log.append(entry)
        return True, ""

    def anim_layers(self):
        return [dict(r) for r in self.anim]

    def display_layers(self):
        return [dict(r) for r in self.disp]

    def keys_by_layer(self, names):
        return {n: [0.0, 10.0] for n in names}

    def pick(self, name):
        for r in self.anim:
            r["active"] = r["name"] == name
        return self._w("pick", name)

    def set_flag(self, name, flag, on):
        next(r for r in self.anim if r["name"] == name)[flag] = on
        return self._w("set_flag", name, flag, on)

    def begin_weight(self):
        self._w("begin_weight")

    def set_weight(self, name, value):
        next(r for r in self.anim if r["name"] == name)["weight"] = value
        return self._w("set_weight", name, value)

    def end_weight(self):
        self._w("end_weight")

    def set_display(self, name, flag, value):
        return self._w("set_display", name, flag, value)

    def create_anim(self):
        return self._w("create_anim")

    def option(self, name, default):
        return self.opts.get(name, default)

    def set_option(self, name, value):
        self.opts[name] = value

    def __getattr__(self, name):            # every other write
        return lambda *a: self._w(name, *a)


class FakeStrip(object):
    """What the panel asks of the strip: where it stands, where its timeline is."""

    def __init__(self):
        self.ui = 1.0

    def strip_rect(self):
        return (0, 800, 1500, 84)

    def timeline_rect(self):
        return (6, 840, 1120, 40)

    def top_room(self):
        return 760

    def track(self):
        from maya_timebar import look
        return look.Track(16, 1116, 0, 95, cells=True)

    def now(self):
        return 30.0


@unittest.skipIf(QT is None, "no Qt")
class Panel(unittest.TestCase):

    motion = False

    def setUp(self):
        from maya_timebar import layerpanel
        self.app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])
        self.link = FakeLink()
        self.panel = layerpanel.Panel(FakeStrip(), self.link, 1.0, maya_hubstyle.TOKENS, self.motion)
        self.addCleanup(self.panel.destroy)

    def click(self, widget, x, y, button=None):
        E, Qt = QT.QtCore.QEvent, QT.QtCore.Qt
        button = button or Qt.LeftButton
        for kind, held in ((E.MouseButtonPress, button), (E.MouseButtonRelease, Qt.NoButton)):
            p = QT.QtCore.QPointF(x, y)
            ev = QT.QtGui.QMouseEvent(kind, p, QT.QtCore.QPointF(widget.mapToGlobal(p.toPoint())), button, held, Qt.NoModifier)
            QT.QtWidgets.QApplication.sendEvent(widget, ev)

    def centre(self, rect):
        return rect[0] + rect[2] / 2.0, rect[1] + rect[3] / 2.0


class Opens(Panel):

    def test_toggle_opens_and_closes_at_once_without_motion(self):
        self.panel.toggle((1300, 815))
        self.assertTrue(self.panel.is_open() and self.panel.column.isVisible())
        g = self.panel.column.geometry()
        self.assertEqual((g.x(), g.y() + g.height()), (1126 + L.SIDE, 800 - L.ABOVE))
        self.assertEqual(g.height(), L.DEFAULT_H)
        self.panel.toggle((1300, 815))
        self.assertFalse(self.panel.is_open() or self.panel.column.isVisible())

    def test_remembered_height_and_tab(self):
        self.link.opts = {"skeldarTimeBarLayersHeight": 400, "skeldarTimeBarLayersTab": "disp"}
        self.panel.open((1300, 815))
        self.assertEqual(self.panel.column.height(), 400)
        self.assertEqual(self.panel.tab, "disp")


class Presses(Panel):

    def setUp(self):
        super(Presses, self).setUp()
        self.panel.open((1300, 815))
        self.col = self.panel.column
        self.lay = self.col.layout_()

    def test_a_row_click_picks_the_layer(self):
        rect = self.lay.row_at(1, 0)
        self.click(self.col, *self.centre(L.row_parts(rect, "anim", 1.0)["name"]))
        self.assertIn(("pick", "A1"), self.link.log)

    def test_mute_solo_lock(self):
        rect = self.lay.row_at(0, 0)
        self.click(self.col, *self.centre(L.row_parts(rect, "anim", 1.0)["mute"]))
        self.assertIn(("set_flag", "A2", "mute", True), self.link.log)

    def test_a_weight_drag_is_one_chunk(self):
        rect = L.row_parts(self.lay.row_at(0, 0), "anim", 1.0)["weight"]
        self.click(self.col, rect[0] + rect[2] * 0.25, rect[1] + 4)
        names = [e[0] for e in self.link.log]
        self.assertEqual(names[0], "begin_weight")
        self.assertEqual(names[-1], "end_weight")
        self.assertIn("set_weight", names)

    def test_the_tab_switches_and_is_remembered(self):
        self.click(self.col, *self.centre(self.lay.segments["disp"]))
        self.assertEqual(self.panel.tab, "disp")
        self.assertEqual(self.link.opts["skeldarTimeBarLayersTab"], "disp")

    def test_the_grip_resizes_and_is_remembered(self):
        E, Qt = QT.QtCore.QEvent, QT.QtCore.Qt
        y0 = 3
        g0 = self.col.geometry()
        for kind, dy, held in ((E.MouseButtonPress, 0, Qt.LeftButton), (E.MouseMove, -60, Qt.LeftButton),
                               (E.MouseButtonRelease, -60, Qt.NoButton)):
            p = QT.QtCore.QPointF(20, y0 + dy)
            gp = QT.QtCore.QPointF(g0.x() + 20, g0.y() + y0 + dy)
            ev = QT.QtGui.QMouseEvent(kind, p, gp, Qt.LeftButton, held, Qt.NoModifier)
            QT.QtWidgets.QApplication.sendEvent(self.col, ev)
        self.assertEqual(self.col.height(), g0.height() + 60)
        self.assertEqual(self.link.opts["skeldarTimeBarLayersHeight"], g0.height() + 60)
        self.assertEqual(self.col.geometry().bottom(), g0.bottom())

    def test_the_lanes_follow_the_column(self):
        self.click(self.col, *self.centre(self.lay.lanes))
        self.assertTrue(self.panel.lanes.isVisible())
        lg, cg = self.panel.lanes.geometry(), self.col.geometry()
        self.assertEqual((lg.x(), lg.right() + 1, lg.y(), lg.height()), (6, cg.x(), cg.y(), cg.height()))
        self.assertEqual(self.link.opts["skeldarTimeBarLayerLanes"], 1)

    def test_the_foot_presses(self):
        name, rect = self.lay.foot[0]
        self.click(self.col, *self.centre(rect))
        self.assertIn(("create_anim",), self.link.log)

    def test_the_right_button_rows(self):
        rows = self.panel.row_menu(0)
        self.assertEqual([r[0] for r in rows if r],
                         ["Additive", "Override", "Rename", "Select objects", "Add selection",
                          "Remove selection", "Merge down", "Delete"])


class Motion(Panel):

    motion = True

    def test_mid_open_the_shape_is_small_and_far_pixels_empty(self):
        self.panel.open((1300, 815))
        col = self.panel.column
        self.panel.age_override = 60.0               # ms into the burst
        img = QT.QtGui.QImage(col.size(), QT.QtGui.QImage.Format_ARGB32)
        img.fill(0)
        col.render(img)
        self.assertEqual(img.pixelColor(4, 12).alpha(), 0)      # the far top-left corner: not yet
        self.panel.age_override = None


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run to see them fail**

Run: `$env:QT_QPA_PLATFORM='offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_timebar_layerpanel -v`
Expected: ERROR, `No module named 'maya_timebar.layerpanel'`.

- [ ] **Step 4: Write `layerpanel.py`**

Write the module in this shape (fill each method fully; no method may be left as a stub):

```python
"""The Time Bar's layer panel (2026-10-18): a painted column of animation and display
layers on the bar's right, resizable by its top edge, and lanes of each layer's keys
over the timeline. Two frameless Qt.Tool windows of ours; all painting is ours.

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


class Panel(object):
    """The controller: opens, places, reads, writes, drives both windows."""

    def __init__(self, strip, link, ui, tokens, motion, parent=None):
        ...
```

What each piece does (all of it required):

- `Panel.__init__`: keep `strip`, `link`, `ui`, `tokens`, `motion`; `self.tab = link.option(TAB_VAR, "anim")` (anything else → `"anim"`); `self.height = float(link.option(HEIGHT_VAR, L.DEFAULT_H))`; `self.lanes_on = bool(link.option(LANES_VAR, 0))`; `self.rows = {"anim": [], "disp": []}`, `self.picked_disp = None`, `self.scroll = 0.0`, `self.keys = {}`, `self.phase = "closed"`, `self.age_override = None` (tests only), `self.parts_t0 = None`; build `self.column = Column(self, parent)` and `self.lanes = Lanes(self, parent)` (both hidden); a `QTimer` `self.driver` at `bar.FRAME_MS` running `self._animate` and a `QTimer` `self.placer` at `PLACE_MS` running `self.place` while open.
- `is_open()`: `self.phase in ("opening", "open")`.
- `toggle(origin)`: `close(origin)` when open, else `open(origin)`.
- `open(origin)`: `refresh(force=True)`; `place()`; show the column (`show()` without activating); show the lanes when `self.lanes_on and self.tab == "anim"`; with motion: `self.burst = {"t0": clock(), "open": True, "origin": origin}` and part delays from `L.schedule(part_rects, local origin, ui)` (part rects: the two segments, the lanes button, every visible row, every foot button; the lanes' parts: each lane), `phase = "opening"`, `driver.start()`; without motion `phase = "open"`. `placer.start()`.
- `close(origin=None)`: without motion hide both now, `phase = "closed"`; with motion `phase = "closing"`, the fold delays, the close of the shape at `max(fold) + look.FOLD_MS + look.CLOSE_AFTER_MS`, hidden when it ends. `placer.stop()`.
- `place()`: `rect = L.column_rect(strip.strip_rect(), strip.timeline_rect(), L.clamp_height(self.height, strip.top_room()), ui)` (rects in logical px; convert: global physical = logical × the widgets' own scale only where Maya's screens need it — the strip gives physical global rects, so pass `ui` for the margins and keep the rects as given); `column.setGeometry(*map(int, rect))`; `lanes.setGeometry(*map(int, L.lanes_rect(rect, strip.timeline_rect())))`.
- `refresh(force=False)`: read `link.anim_layers()` and `link.display_layers()`; when `L.signature` of either changed (or `force`), keep them, clamp `self.scroll` to the new layout's `max_scroll`, `column.invalidate()`; when the lanes show, `self.keys = link.keys_by_layer([r["name"] for r in self.rows["anim"]])` and `lanes.invalidate()`.
- `keys_dirty()`: when the lanes show, read the keys again and `lanes.update()`.
- `on_time()`: when the lanes show, `lanes.repaint()` (the playhead cell; trap 269).
- `press(hit)` (from `Column.mousePressEvent` via `L.hit`): `("tab", t)` → `self.tab = t`, `link.set_option(TAB_VAR, t)`, rows wave from that segment, lanes shown only on `"anim"`; `("lanes",)` → toggle `self.lanes_on`, `link.set_option(LANES_VAR, int(...))`, show / hide the lanes with their burst out of the column's left edge at the head's height; `("row", i, "name")` → anim: `link.pick(name)`, disp: `self.picked_disp = name`; `("row", i, "mute"|"solo"|"lock")` → `link.set_flag(name, flag, not row[flag])`, a pop on that control; `("row", i, "visible"|"playback")` → `link.set_display(name, flag, not row[flag])`; `("row", i, "type")` → `link.set_display(name, "type", L.step_type(row["type"]))`; `("row", i, "weight")` → `link.begin_weight()`, `link.set_weight(name, L.weight_at(x, rect))`, drag continues in `mouseMoveEvent`, `link.end_weight()` on release; `("foot", n)` → the table below; `("grip",)` → start a resize: keep the press's global y and the height; moves set `self.height = L.clamp_height(h0 - (gy - gy0), strip.top_room())` and `place()`; the release `link.set_option(HEIGHT_VAR, int(round(self.height)))`. After every write: `self.say(message)` when the link answered a message, `refresh(force=True)`, and `strip.refresh(keys=True)` (the chip shows the active layer).
- The foot table: anim `add` → `create_anim()`, `addsel` → `add_selection(active)`, `remsel` → `remove_selection(active)`, `merge` → `merge_down(active)`, `delete` → `delete_anim(active)`; disp `add` → `create_display()`, `addsel` → `display_add(picked)`, `remsel` → `display_remove(picked)`, `select` → `display_select(picked)`, `delete` → `delete_display(picked)`. Where the target is missing (no picked display layer) say «pick a layer first» and write nothing. A deleted layer's row folds from where it stood (data first, then the picture).
- `row_menu(i)`: anim rows (in this order) `("Additive", set_mode add)`, `("Override", set_mode ovr)`, `None`, `("Rename", start the name field)`, `("Select objects", select_objects)`, `("Add selection", ...)`, `("Remove selection", ...)`, `None`, `("Merge down", ...)`, `("Delete", ...)`; disp `("Rename", ...)`, `("Colour", [(name, set_display colour index) for Maya's 1..31])`, `None`, `("Select objects", ...)`, `("Add selection", ...)`, `("Remove selection", ...)`, `None`, `("Delete", ...)`. Shown through `strip.menu_rows(rows)` / `QMenu.exec` like the strip's menus. BaseAnimation's rows that cannot apply are `(label, None)` (disabled).
- Rename: a `QLineEdit` (object name `skeldarTimeBarLayerName`) over the row's name rect, its text the label, selected; Enter → `link.rename(name, text)`, Esc → nothing; it is deleted either way.
- `say(text)`: the column's status line shows it for `STATUS_MS`.
- `_animate()`: step every hover by `look.approach(..., bar.HOVER_MS)`; repaint the column and the lanes while anything is busy (a burst, a wave, a pop, a flash, a hover); stop the driver at rest after one more paint.
- `destroy()`: stop the timers, delete both windows.

`Column(QWidget)`: object name `COLUMN`; flags `Qt.Tool | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint`; `WA_TranslucentBackground`, `WA_ShowWithoutActivating`; mouse tracking on. `layout_()` returns `L.Layout(self.width() / ui, self.height() / ui, rows, tab, ui)` (sizes in logical px; scale the painter by nothing — the layout already multiplies by `ui`, so pass the widget's real width and height with `ui`). Paint (always inside `try`, a traceback printed once, `_failed`):
1. During a burst: clip to the rounded rect unrolling from the origin (`look.ease_out_quint(age / look.UNROLL_MS)` growing a 28 × 20 box at the origin to the whole rect; closing `1 - look.ease_in_quint(...)` after the folds) and paint the reveal's top edge light (a 1.5 px line in `RIM` and a 16 px gradient in `accent`, faded `(1 - age / look.REVEAL_MS) ** 1.6`, `CompositionMode_Plus`).
2. The card: `panel` face, a 1 px `track_edge` outline, radius 8 × ui. The grip: a 34 × 3 bar at the top centre in `line`, `accent` with a soft glow and 46 px wide while hovered or dragged.
3. The head: the segment track (`track`, `track_edge`), the lit segment a `thumb` face, labels «Animation n» / «Display n» (the count in Consolas, `faint`); the lanes button as a toggle (`accent_tint` face and `accent` glyph when on; drawn at 35 % opacity on the Display tab).
4. The well (`field`, `track_edge`, radius 6) clipped; each visible row: `card` (`hover` blended by its hover level), the active / picked one `card_active` with a 1.5 px `accent` outline and its name `accent_text` bold; a dimmed row at 42 % opacity with its name struck through. Anim row: the mode badge (Consolas 9 px, `faint`, a 1 px `line` outline), the name (12.5 px, elided), the weight track (`track`, an `accent` fill, the number in Consolas `text2`), M / S / lock toggles (M lit `#3a2626` / `danger`, S lit `#23324a` / `hl`, lock lit `accent_tint` / `accent`). Display row: the swatch (the layer's colour, `line` when it has none), the name, V / P / the type letter.
5. A thin scrollbar on the well's right while `max_scroll > 0`.
6. The foot: **+ Layer** (`accent` face, `on_accent` ink, the `plus` glyph), the icon buttons (glyphs in `muted`, `hover` face and `text` ink under the mouse, `danger` ink for the trash under the mouse); then the status line in `status_text`.
7. Every part (segments, lanes button, rows, foot buttons) is drawn with its burst scale and opacity about its own centre (`look.popping` / `look.folding` at its delay), and hover, press flash and toggle pop as the strip's Pill (`LIFT`, `FLASH_MS`, `POP_MS`, `look.back_out`).
The still picture (everything at rest, no hover) is cached in a `QPixmap` keyed by `(size, ui, tab, scroll, signature(rows), picked, status text)` and drawn first; only moving or hovered parts are drawn over it. `wheelEvent` scrolls the well (clamped), and lanes follow (`lanes.update()`).

`Lanes(QWidget)`: object name `LANES`, the same flags. Paint: a `#141517` face at 95 %, radius 8 on the left; a ruler at the head on the timeline's frames (`strip.track()`; ticks and numbers every 5 as the timeline draws them); one lane per animation row at that row's height minus the scroll (`L.Layout`'s `row_at`, the column's own layout), `field` face, its keys drawn with `look.key_cell` on the track's cells (active orange, base `faint`, others `muted`, dimmed lanes at 42 %); the playhead's cell (`strip.now()`) at `accent` 20 % through every lane. A click on a lane picks its layer. Its burst: the shape unrolls leftward from the column's edge, each lane pops at its delay.

- [ ] **Step 5: Run the panel tests until they pass**

Run: `$env:QT_QPA_PLATFORM='offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_timebar_layerpanel -v`
Expected: OK.

- [ ] **Step 6: Commit**

```bash
git add SkeldarAnim/maya_timebar/layerpanel.py SkeldarAnim/maya_timebar/bar.py tests/test_timebar_layerpanel.py
git commit -m "feat(timebar): the layer panel - a painted column, its lanes, their burst"
```

---

### Task 5: The strip — the layers pill replaces the bookmark pills

**Files:**
- Modify: `SkeldarAnim/maya_timebar/bar.py:1279-1316` (the range row), `:1652-1677` (`_paint_widgets`), `:1711-1716` (`_bookmark`, `_add_bookmark`), `:1765-1769` (`layer_rows`), `:1816-1817` (`_layer_menu`), `start_jobs`, `_time_changed`, `_keys_edited`, `build`
- Modify: `SkeldarAnim/maya_timebar/scene.py` (remove `step_bookmark`; re-export the panel's link)
- Modify: `SkeldarAnim/maya_timebar/edge.py:491-508` (`blockers`)
- Test: `tests/test_timebar_bar.py`, `tests/test_timebar_edge.py`

**Interfaces:**
- Consumes: Task 4's `layerpanel.Panel`, `layerpanel.destroy_all()`.
- Produces: `Strip.layers_btn` (Pill), `Strip.layer_panel` (a `Panel` or None), `Strip.toggle_layers()`, `Strip.strip_rect()`, `Strip.timeline_rect()`, `Strip.top_room()`, `Strip.track()`, `Strip.now()`; `BottomEdge.blockers()` answers `"layers"` while the panel is open.

- [ ] **Step 1: Update the failing strip tests**

In `tests/test_timebar_bar.py`: remove `step_bookmark` from `FakeLink`; remove `layer_rows` from `test_the_chips_menus_are_checked_where_the_scene_is`; replace the bookmark part of `test_the_toggles_go_to_maya` and add:

```python
    def test_the_toggles_go_to_maya(self):
        self.strip.loop.click()
        self.assertEqual(self.link.x["loop"], "once")
        self.assertFalse(self.strip.loop.isChecked())
        self.strip.cache.click()
        self.assertFalse(self.link.x["cache"])

    def test_no_bookmark_pills_and_a_layers_pill_on_the_right(self):
        for gone in ("bm_prev", "bm_add", "bm_next"):
            self.assertFalse(hasattr(self.strip, gone))
        btn = self.strip.layers_btn
        self.assertGreater(btn.x(), self.strip.auto.x())
        self.assertLess(btn.x(), self.strip.prefs.x())
        self.assertTrue(btn.isCheckable())

    def test_the_pill_and_the_chip_open_the_panel(self):
        opened = []
        self.strip.toggle_layers = lambda *a: opened.append(True)
        self.strip.layers_btn.click()
        self.strip.layer.click()
        self.assertEqual(len(opened), 2)
```

In `tests/test_timebar_edge.py`, beside the other blocker tests, add a test that a strip whose `layer_panel.is_open()` answers True makes `blockers()` contain `"layers"` (build it the way the file's existing blocker tests build their edge and strip; read them first and follow them).

Run: `$env:QT_QPA_PLATFORM='offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_timebar_bar tests.test_timebar_edge -v`
Expected: the new tests FAIL (`bm_prev` still there, no `layers_btn`, no `"layers"`).

- [ ] **Step 2: Change the range row in `Strip.__init__`**

Remove the six lines making and connecting `bm_prev`, `bm_add`, `bm_next`, the loop adding them, and the `top.addWidget(self._sep())` after them. After `self.prefs` is made and before the loop that adds `loop … pin`, make the pill:

```python
            self.layers_btn = Pill(self, "layers", tip="Animation and display layers", toggle=True)
            self.layers_btn.clicked.connect(lambda *_a: self.toggle_layers())
            self.layer_panel = None
```

and lay the right group out as:

```python
            for b in (self.loop, self.cache, self.speed, self.sound, self.auto):
                top.addWidget(b)
            top.addWidget(self._sep())
            for b in (self.layers_btn, self.prefs, self.pin):
                top.addWidget(b)
```

Change the chip's connection to `self.layer.clicked.connect(lambda *_a: self.toggle_layers())`.

- [ ] **Step 3: Add the strip's side of the panel**

Methods on `Strip`:

```python
        def toggle_layers(self):
            """The layers pill or the chip: the layer panel opened or closed out of the pill."""
            from . import layerpanel
            if self.layer_panel is None:
                parent = None
                try:
                    from . import edge as _edge
                    parent = _edge.main_window()
                except Exception:                            # noqa: BLE001
                    parent = None
                self.layer_panel = layerpanel.Panel(self, self.link.layer_link(), self.ui, self.tokens,
                                                    self.motion, parent)
            c = self.layers_btn.mapToGlobal(self.layers_btn.rect().center())
            self.layer_panel.toggle((c.x(), c.y()))
            self.layers_btn.setChecked(self.layer_panel.is_open())

        def strip_rect(self):
            p = self.mapToGlobal(self.rect().topLeft())
            return (p.x(), p.y(), self.width(), self.height())

        def timeline_rect(self):
            t = self.timeline
            p = t.mapToGlobal(t.rect().topLeft())
            return (p.x(), p.y(), t.width(), t.height())

        def top_room(self):
            """From the strip's top to the top of Maya's viewport area (else the screen)."""
            top = None
            try:
                import maya_hubedge
                area = maya_hubedge._viewport_area("right")
                top = area[1] if area else None
            except Exception:                                # noqa: BLE001
                top = None
            if top is None:
                screen = self.screen().availableGeometry() if self.screen() else None
                top = screen.y() if screen is not None else 0
            return self.strip_rect()[1] - top

        def now(self):
            return self.state.get("now", 0.0)
```

`track()` already exists on `Timeline`; give `Strip` `def track(self): return self.timeline.track()`. The panel's track maps frames to the timeline's local x; the Lanes window starts at the timeline's left, so its local x equals the timeline's.

In `_paint_widgets` keep the chip's label code and add `self.layers_btn.setChecked(bool(self.layer_panel and self.layer_panel.is_open()))`. Delete `_bookmark`, `_add_bookmark`, `layer_rows` and `_layer_menu`.

In `refresh`, at the end: `if self.layer_panel is not None and self.layer_panel.is_open(): self.layer_panel.refresh()`; in `on_time`, after `self.timeline.repaint()`: `if self.layer_panel is not None: self.layer_panel.on_time()`.

In `_keys_edited` (module level) add: `if widget.layer_panel is not None: widget.layer_panel.keys_dirty()`.

In `start_jobs`, extend the event table with
`("displayLayerChange", "refresh", ())`, `("displayLayerManagerChange", "refresh", ())`, `("displayLayerAdded", "refresh", ())`, `("displayLayerDeleted", "refresh", ())`, `("displayLayerVisibilityChanged", "refresh", ())` (the `try` already skips an event this Maya lacks).

In `build()` and in `maya_timebar/__init__.py`'s edge rebuild and `drop_edge` (find them with `grep -n "def drop_edge\|def _build_edge\|destroy_all" SkeldarAnim/maya_timebar/__init__.py`), call `layerpanel.destroy_all()` before the old strip goes.

- [ ] **Step 4: The link**

In `scene.py`: delete `step_bookmark`; add

```python
def layer_link():
    """The layer panel's road into Maya."""
    from . import layerscene
    return layerscene
```

In `Link` (bar.py) nothing changes: `__getattr__` reaches `scene.layer_link`. In the strip tests' `FakeLink` add `def layer_link(self): return self` only if a test opens the real panel (the tests above replace `toggle_layers`).

- [ ] **Step 5: The edge's blocker**

In `edge.py` `blockers()`, after the `baking` line:

```python
        panel = getattr(self.strip, "layer_panel", None)
        if panel is not None and panel.is_open():
            reasons.append("layers")              # the layer panel stands on the bar (2026-10-18)
```

In `conceal()` (the bar going), close the panel at once first: `panel = getattr(self.strip, "layer_panel", None); if panel is not None and panel.is_open(): panel.close()` — reached only by a hide no blocker stopped (a mode switch, a tab switch).

- [ ] **Step 6: Run the Time Bar's tests**

Run: `$env:QT_QPA_PLATFORM='offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_timebar_bar tests.test_timebar_edge tests.test_timebar_look tests.test_timebar_layerlook tests.test_timebar_layerscene tests.test_timebar_layerpanel -v`
Expected: OK.

- [ ] **Step 7: Commit**

```bash
git add SkeldarAnim/maya_timebar/bar.py SkeldarAnim/maya_timebar/scene.py SkeldarAnim/maya_timebar/edge.py SkeldarAnim/maya_timebar/__init__.py tests/test_timebar_bar.py tests/test_timebar_edge.py
git commit -m "feat(timebar): the layers pill in place of the bookmark pills"
```

---

### Task 6: The filmstrip, the bench, the whole suite

**Files:**
- Create: `docs/superpowers/plans/render_timebar_layers.py`, `docs/superpowers/plans/timebar_layers.png`
- Create: `docs/superpowers/plans/bench_timebar_layers.py`

**Interfaces:**
- Consumes: `bar.make`, `layerpanel.Panel`, the fake links of Task 4's tests (copy them into the scripts; scripts must not import tests).

- [ ] **Step 1: Write the filmstrip**

`render_timebar_layers.py`, run with mayapy and `QT_QPA_PLATFORM=offscreen`: build a strip on a fake link (`bar.make(link, 1.5, TOKENS, motion=True)`, 1500 × 84 logical), a `Panel` on a `FakeStrip` whose rects match it, 8 animation layers and 4 display layers; render with `widget.render(QImage)` into one PNG, columns of frames:
1. the column opening at 40, 120, 220, 400 ms (`panel.age_override`);
2. at rest on Animation, with a hovered row and the lanes out;
3. on Display;
4. resized to 420 px;
5. closing at 60, 160, 300 ms.
Label each frame with its state (Segoe UI loaded from `C:/Windows/Fonts/segoeui.ttf` through `QFontDatabase.addApplicationFont`: offscreen Qt draws boxes otherwise). Save `docs/superpowers/plans/timebar_layers.png`.

Run: `$env:QT_QPA_PLATFORM='offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs\superpowers\plans\render_timebar_layers.py`
Expected: the PNG written. Open it with the Read tool and look: the column on the right over the frame field, the lanes from the timeline's left, rows and lanes level, one orange button.

- [ ] **Step 2: Write the bench**

`bench_timebar_layers.py`: a column of 12 animation layers with the lanes out (each with 40 keys), at 1.5 scale; time (median and p95 of 200 runs, `time.perf_counter`): a full repaint of the column, a repaint of the lanes, a hover sweep across all rows (one move event and one repaint each), `Panel.on_time()` (the lanes' playhead). Print ms. Budget (`docs/interface-motion.md` §5): a hover step and `on_time` under 1 ms median, the still picture not rebuilt during the sweep (count rebuilds; expected 0 after the first).

Run: `$env:QT_QPA_PLATFORM='offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs\superpowers\plans\bench_timebar_layers.py`
Expected: within the budget. Over it: cache more (the lanes' still picture keyed by keys and size, drawing only the playhead cell over it), then measure again.

- [ ] **Step 3: The whole suite**

Run: `$env:QT_QPA_PLATFORM='offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . `
Expected: OK, the test count printed (about 7240 before this work). A failure outside the Time Bar's tests that also fails on `git stash` of nothing of ours is another session's: say so, do not fix it here.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/render_timebar_layers.py docs/superpowers/plans/timebar_layers.png docs/superpowers/plans/bench_timebar_layers.py
git commit -m "docs(timebar): the layer panel's filmstrip and bench"
```

---

### Task 7: CLAUDE.md

**Files:**
- Modify: `CLAUDE.md` (the "Time Bar" section: the bookmark buttons line; a new subsection after "…and two more back")

- [ ] **Step 1: Write the section**

Under the Time Bar section, change the range row's «Bookmarks: previous, add over the highlight, next» to say the pills are gone (2026-10-18) and the bookmarks stay on the band and in the key menu; add a subsection «**The layer panel** (2026-10-18)» stating, in the file's style: the animator's words and the mockup URL; the pill and the chip; the column (where, height and its optionVar, the two tabs and what each row holds, the foot); the lanes; the burst; the `"layers"` blocker; the modules (`layerlook`, `layerscene`, `layerpanel`); the proof with the real numbers from Tasks 3 and 6 (gates, test count, bench ms); «not seen in a GUI Maya». Any trap met while building gets a number after the last one in the file.

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: the Time Bar's layer panel in CLAUDE.md"
```

---

## Self-review

- Spec §1 (pills out, pill in, chip): Task 5. §2 column, §2.1, §2.2, §2.3: Tasks 2-4. §3 lanes: Task 4 (`Lanes`, `keys_by_layer`), Task 5 (keys dirty). §4 motion: Task 4 (burst, waves, pops), checked by Task 4's `Motion` test and Task 6's filmstrip. §5 edge, docked, maya mode, destroy: Task 5. §6 code: the File Structure. §7 proof: Tasks 3, 4, 6. §8 checklist: Tasks 4-6. §9 not built: nothing to do.
- Names used across tasks: `layer_link`, `anim_layers`, `display_layers`, `keys_by_layer`, `pick`, `set_flag`, `begin_weight`/`set_weight`/`end_weight`, `set_mode`, `rename`, `create_anim`, `add_selection`, `remove_selection`, `merge_down`, `delete_anim`, `select_objects`, `set_display`, `create_display`, `display_add`, `display_remove`, `display_select`, `delete_display`, `option`, `set_option`; `Panel.toggle/open/close/is_open/place/refresh/on_time/keys_dirty/row_menu/destroy`, `Column.layout_()`; `Strip.layers_btn/layer_panel/toggle_layers/strip_rect/timeline_rect/top_room/track/now`.
