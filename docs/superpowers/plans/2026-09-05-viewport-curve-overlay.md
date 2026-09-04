# Curve Overlay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A toggle mode that draws the selected control's animation curves over
the whole Maya viewport with a transparent background, and lets the animator
select keys and drag them there while the character stays visible underneath.

**Architecture:** Input comes from an ordinary `cmds.draggerContext`, so `alt`
plus mouse stays the camera in Maya's own event dispatch. Drawing is a
frameless translucent top-level Qt window parked on the viewport's GL widget,
made click-through with the Win32 ex-style `WS_EX_LAYERED | WS_EX_TRANSPARENT`
so it never sees a mouse event at all. All the arithmetic lives in one pure
stdlib module.

**Tech Stack:** Python 3, `maya.cmds`, `maya.api.OpenMaya` (for
`MGlobal.selectFromScreen`), PySide6 + shiboken6, `ctypes` for the Win32
ex-style. No Maya plugin, no third-party dependency.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-05-viewport-curve-overlay-design.md`.
- `mapping.py` imports **stdlib only**; `overlay.py` imports **Qt and ctypes
  only, never `maya.cmds`**. A subprocess test enforces both.
- `qt_y = rect_height - dragger_y` — `draggerContext(space="screen")` counts Y
  from the **bottom** of the viewport. Measured.
- `draggerContext` command strings are executed as **Python**, not MEL.
- The click-through ex-style must be applied **after `show()`**; re-parenting
  recreates the native window and loses it.
- Sample the **animCurve node** (`cmds.keyframe(curve, query=True, eval=True,
  time=(t, t))`), never the driven plug — a plug sample pulls a whole rig
  evaluation.
- Time-follows-key is **throttled** (default 20 Hz) with one guaranteed
  evaluation on release. Basis: ~860 drag events per drag at 10.4 fps.
- One undo chunk per drag, opened on press, closed on release.
- Colours by axis: X red, Y green, Z blue, anything else neutral.
- Autoframe only: X is the playback range, Y fits the visible curves. There is
  no pan and no zoom, so every mouse gesture Maya owns stays Maya's.
- Tests run with
  `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v`
  from the repo root. Qt tests need `$env:QT_QPA_PLATFORM = 'offscreen'`.

---

### Task 1: `mapping.py` — all the arithmetic, pure

**Files:**
- Create: `SkeldarAnim/maya_curveview/__init__.py`
- Create: `SkeldarAnim/maya_curveview/mapping.py`
- Test: `tests/test_curveview_mapping.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `Frame(t0, t1, v0, v1)` namedtuple — the curve-space window.
  - `Rect(width, height)` namedtuple — pixels.
  - `value_span(series) -> (lo, hi) | None` where `series` is an iterable of
    iterables of `(time, value)` pairs.
  - `autoframe(time_range, span, margin=0.08, floor=1.0) -> Frame`
  - `to_pixels(frame, rect, t, v) -> (float, float)` in Qt coordinates
  - `to_curve(frame, rect, x, y) -> (float, float)`
  - `flip_y(rect, y) -> float`
  - `snap(t) -> float` (round half away from zero to a whole frame)
  - `pick_key(frame, rect, keys, x, y, radius=8.0) -> int | None`
  - `keys_in_box(frame, rect, keys, x0, y0, x1, y1) -> [int]`
  - `adjustment(modifier) -> "replace" | "toggle" | "remove" | "add"`
  - `axis_colour(attribute) -> (int, int, int)`
  - `should_evaluate(now, last, interval=0.05) -> bool`
  - `is_marquee(x0, y0, x1, y1, slop=3.0) -> bool`

- [ ] **Step 1: Write the failing tests**

```python
import os
import subprocess
import sys
import unittest

from maya_curveview import mapping


class TestPurity(unittest.TestCase):
    def test_mapping_pulls_in_neither_maya_nor_qt(self):
        script = (
            "import sys\n"
            "from maya_curveview import mapping\n"
            "leaked = [m for m in sys.modules\n"
            "          if m.startswith('maya') or m.startswith('PySide6')]\n"
            "print(';'.join(sorted(leaked)))\n")
        plugin = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "SkeldarAnim")
        result = subprocess.run([sys.executable, "-c", script],
                                cwd=plugin, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "")


class TestFrame(unittest.TestCase):
    def test_value_span_over_several_curves(self):
        span = mapping.value_span([[(0, 1.0), (5, 3.0)], [(0, -2.0)]])
        self.assertEqual(span, (-2.0, 3.0))

    def test_value_span_of_nothing_is_none(self):
        self.assertIsNone(mapping.value_span([]))
        self.assertIsNone(mapping.value_span([[]]))

    def test_autoframe_x_is_the_time_range_exactly(self):
        frame = mapping.autoframe((0.0, 100.0), (0.0, 10.0))
        self.assertEqual((frame.t0, frame.t1), (0.0, 100.0))

    def test_autoframe_pads_the_value_range(self):
        frame = mapping.autoframe((0.0, 10.0), (0.0, 10.0), margin=0.1)
        self.assertAlmostEqual(frame.v0, -1.0)
        self.assertAlmostEqual(frame.v1, 11.0)

    def test_a_flat_curve_still_gets_a_window(self):
        frame = mapping.autoframe((0.0, 10.0), (5.0, 5.0), floor=2.0)
        self.assertLess(frame.v0, 5.0)
        self.assertGreater(frame.v1, 5.0)

    def test_no_span_still_gives_a_usable_frame(self):
        frame = mapping.autoframe((0.0, 10.0), None)
        self.assertLess(frame.v0, frame.v1)


class TestMapping(unittest.TestCase):
    def setUp(self):
        self.frame = mapping.Frame(0.0, 100.0, 0.0, 10.0)
        self.rect = mapping.Rect(1000, 500)

    def test_time_maps_left_to_right(self):
        x, _ = mapping.to_pixels(self.frame, self.rect, 50.0, 0.0)
        self.assertAlmostEqual(x, 500.0)

    def test_value_maps_bottom_up_in_qt_coordinates(self):
        _, y_low = mapping.to_pixels(self.frame, self.rect, 0.0, 0.0)
        _, y_high = mapping.to_pixels(self.frame, self.rect, 0.0, 10.0)
        self.assertAlmostEqual(y_low, 500.0)
        self.assertAlmostEqual(y_high, 0.0)

    def test_round_trip(self):
        t, v = mapping.to_curve(self.frame, self.rect,
                                *mapping.to_pixels(self.frame, self.rect,
                                                   33.0, 7.5))
        self.assertAlmostEqual(t, 33.0)
        self.assertAlmostEqual(v, 7.5)

    def test_flip_y_is_measured_from_the_bottom(self):
        self.assertAlmostEqual(mapping.flip_y(self.rect, 0.0), 500.0)
        self.assertAlmostEqual(mapping.flip_y(self.rect, 500.0), 0.0)

    def test_snap_goes_to_whole_frames(self):
        self.assertEqual(mapping.snap(3.4), 3.0)
        self.assertEqual(mapping.snap(3.6), 4.0)
        self.assertEqual(mapping.snap(-3.6), -4.0)


class TestPicking(unittest.TestCase):
    def setUp(self):
        self.frame = mapping.Frame(0.0, 100.0, 0.0, 10.0)
        self.rect = mapping.Rect(1000, 500)
        self.keys = [(0.0, 0.0), (50.0, 5.0), (100.0, 10.0)]

    def test_picks_the_key_under_the_point(self):
        x, y = mapping.to_pixels(self.frame, self.rect, 50.0, 5.0)
        self.assertEqual(mapping.pick_key(self.frame, self.rect, self.keys,
                                          x + 2, y - 2), 1)

    def test_nothing_outside_the_radius(self):
        x, y = mapping.to_pixels(self.frame, self.rect, 50.0, 5.0)
        self.assertIsNone(mapping.pick_key(self.frame, self.rect, self.keys,
                                           x + 40, y, radius=8.0))

    def test_the_nearest_wins(self):
        keys = [(50.0, 5.0), (51.0, 5.0)]
        x, y = mapping.to_pixels(self.frame, self.rect, 51.0, 5.0)
        self.assertEqual(mapping.pick_key(self.frame, self.rect, keys, x, y,
                                          radius=40.0), 1)

    def test_box_catches_what_is_inside_it(self):
        x0, y0 = mapping.to_pixels(self.frame, self.rect, 40.0, 4.0)
        x1, y1 = mapping.to_pixels(self.frame, self.rect, 60.0, 6.0)
        self.assertEqual(mapping.keys_in_box(self.frame, self.rect, self.keys,
                                             x0, y0, x1, y1), [1])

    def test_box_normalises_its_corners(self):
        x0, y0 = mapping.to_pixels(self.frame, self.rect, 60.0, 6.0)
        x1, y1 = mapping.to_pixels(self.frame, self.rect, 40.0, 4.0)
        self.assertEqual(mapping.keys_in_box(self.frame, self.rect, self.keys,
                                             x0, y0, x1, y1), [1])

    def test_a_click_is_not_a_marquee(self):
        self.assertFalse(mapping.is_marquee(10.0, 10.0, 11.0, 12.0))
        self.assertTrue(mapping.is_marquee(10.0, 10.0, 60.0, 12.0))


class TestPolicy(unittest.TestCase):
    def test_modifier_maps_onto_maya_selection_behaviour(self):
        self.assertEqual(mapping.adjustment("none"), "replace")
        self.assertEqual(mapping.adjustment("shift"), "toggle")
        self.assertEqual(mapping.adjustment("ctrl"), "remove")
        self.assertEqual(mapping.adjustment("ctrlShift"), "add")

    def test_unknown_modifier_replaces(self):
        self.assertEqual(mapping.adjustment("hyper"), "replace")

    def test_axis_colours(self):
        self.assertEqual(mapping.axis_colour("translateX"),
                         mapping.AXIS_COLOURS["x"])
        self.assertEqual(mapping.axis_colour("rotateY"),
                         mapping.AXIS_COLOURS["y"])
        self.assertEqual(mapping.axis_colour("node.scaleZ"),
                         mapping.AXIS_COLOURS["z"])
        self.assertEqual(mapping.axis_colour("visibility"),
                         mapping.AXIS_COLOURS["other"])

    def test_throttle_lets_the_first_through(self):
        self.assertTrue(mapping.should_evaluate(0.0, None, 0.05))

    def test_throttle_holds_inside_the_interval(self):
        self.assertFalse(mapping.should_evaluate(1.01, 1.0, 0.05))
        self.assertTrue(mapping.should_evaluate(1.06, 1.0, 0.05))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_curveview_mapping -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'maya_curveview'`

- [ ] **Step 3: Write `mapping.py`**

Pure stdlib. `AXIS_COLOURS` is a dict with keys `x`, `y`, `z`, `other`.
`axis_colour` takes either a bare attribute or a `node.attr` plug, strips the
node, and looks at the last character case-insensitively — but only when the
attribute is one of the transform families, so `visibility` is not read as a
Y channel. `pick_key` compares squared pixel distance. `keys_in_box`
normalises the corners first. `autoframe` pads by `margin` of the span and by
`floor` when the span is zero.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_curveview_mapping -v`
Expected: PASS, all of them.

- [ ] **Step 5: Commit**

```bash
git add SkeldarAnim/maya_curveview/__init__.py SkeldarAnim/maya_curveview/mapping.py tests/test_curveview_mapping.py
git commit -F <message file>
```

---

### Task 2: `curves.py` — which curves, and their shape

**Files:**
- Create: `SkeldarAnim/maya_curveview/curves.py`
- Test: `tests/test_curveview_curves.py`

**Interfaces:**
- Consumes: `mapping` (for nothing yet — `curves.py` stays independent of it).
- Produces:
  - `Curve(plug, node, attribute, curve, keys)` namedtuple; `keys` is a list of
    `(time, value)`.
  - `channel_attributes(node) -> [str]` — the channel-box rule for one node.
  - `visible_curves(selection=None) -> [Curve]`
  - `keys_of(curve) -> [(time, value)]`
  - `selected_indices(curve) -> [int]`
  - `sample(curve, t0, t1, count) -> [(time, value)]`
  - `time_range() -> (float, float)` — the playback range.

  Every function takes its `cmds` from the module attribute, so a test can
  rebind `curves.cmds` to a fake (the repo's rule: rebind the attribute, never
  re-import).

- [ ] **Step 1: Write the failing tests**

```python
import unittest

from maya_curveview import curves


class FakeCmds(object):
    """Just enough Maya to answer the channel-box rule."""

    def __init__(self, selection=(), channel_selection=None, plugs=None,
                 keys=None, playback=(0.0, 100.0)):
        self._selection = list(selection)
        self._channel_selection = channel_selection
        self._plugs = plugs or {}
        self._keys = keys or {}
        self._playback = playback
        self.eval_calls = []

    def ls(self, *args, **kwargs):
        if kwargs.get("selection"):
            return list(self._selection)
        return []

    def channelBox(self, name, **kwargs):
        return self._channel_selection

    def listAttr(self, node, **kwargs):
        return [a for (n, a) in self._plugs if n == node]

    def listConnections(self, plug, **kwargs):
        return self._plugs.get(tuple(plug.split(".", 1)))

    def objExists(self, name):
        node, _, attr = name.partition(".")
        if not attr:
            return node in {n for (n, _a) in self._plugs}
        return (node, attr) in self._plugs

    def keyframe(self, target, **kwargs):
        if kwargs.get("eval"):
            self.eval_calls.append(kwargs.get("time"))
            return [0.0]
        pairs = self._keys.get(target, [])
        if kwargs.get("selected"):
            pairs = pairs[:1]
        if kwargs.get("timeChange"):
            return [t for (t, _v) in pairs]
        if kwargs.get("valueChange"):
            return [v for (_t, v) in pairs]
        if kwargs.get("keyframeCount"):
            return len(pairs)
        return []

    def playbackOptions(self, **kwargs):
        return self._playback[0] if kwargs.get("min") else self._playback[1]


class TestChannelRule(unittest.TestCase):
    def tearDown(self):
        curves.cmds = curves._real_cmds

    def test_channel_box_selection_wins(self):
        curves.cmds = FakeCmds(
            selection=["ctrl"], channel_selection=["translateX"],
            plugs={("ctrl", "translateX"): ["curveA"],
                   ("ctrl", "translateY"): ["curveB"]})
        self.assertEqual(curves.channel_attributes("ctrl"), ["translateX"])

    def test_nothing_selected_there_gives_every_animated_channel(self):
        curves.cmds = FakeCmds(
            selection=["ctrl"], channel_selection=None,
            plugs={("ctrl", "translateX"): ["curveA"],
                   ("ctrl", "translateY"): ["curveB"],
                   ("ctrl", "translateZ"): None})
        self.assertEqual(sorted(curves.channel_attributes("ctrl")),
                         ["translateX", "translateY"])

    def test_no_selection_means_no_curves(self):
        curves.cmds = FakeCmds(selection=[])
        self.assertEqual(curves.visible_curves(), [])

    def test_a_channel_with_no_curve_is_dropped(self):
        curves.cmds = FakeCmds(
            selection=["ctrl"], channel_selection=["translateZ"],
            plugs={("ctrl", "translateZ"): None})
        self.assertEqual(curves.visible_curves(), [])

    def test_visible_curves_carries_the_keys(self):
        curves.cmds = FakeCmds(
            selection=["ctrl"], channel_selection=["translateX"],
            plugs={("ctrl", "translateX"): ["curveA"]},
            keys={"curveA": [(0.0, 1.0), (10.0, 2.0)]})
        found = curves.visible_curves()
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].attribute, "translateX")
        self.assertEqual(found[0].curve, "curveA")
        self.assertEqual(found[0].keys, [(0.0, 1.0), (10.0, 2.0)])


class TestSampling(unittest.TestCase):
    def tearDown(self):
        curves.cmds = curves._real_cmds

    def test_sampling_evaluates_the_curve_node_not_the_plug(self):
        fake = FakeCmds()
        curves.cmds = fake
        curves.sample("curveA", 0.0, 10.0, 3)
        self.assertEqual(len(fake.eval_calls), 3)
        self.assertEqual(fake.eval_calls[0], (0.0, 0.0))
        self.assertEqual(fake.eval_calls[-1], (10.0, 10.0))

    def test_a_single_sample_does_not_divide_by_zero(self):
        curves.cmds = FakeCmds()
        self.assertEqual(len(curves.sample("curveA", 0.0, 10.0, 1)), 1)
```

- [ ] **Step 2: Run to verify they fail**

Expected: FAIL, `AttributeError: module 'maya_curveview.curves' has no attribute 'cmds'`

- [ ] **Step 3: Write `curves.py`**

`import maya.cmds as cmds` at module level plus `_real_cmds = cmds` so a test
can restore it. `channel_attributes` asks
`cmds.channelBox("mainChannelBox", query=True, selectedMainAttributes=True)`
and intersects with the node's own attributes; when that answers nothing it
falls back to every keyable attribute carrying an animCurve.
`visible_curves` walks the selection, resolves each plug's animCurve through
`cmds.listConnections(plug, source=True, destination=False, type="animCurve")`
and builds `Curve`. `sample` calls
`cmds.keyframe(curve, query=True, eval=True, time=(t, t))` per point.

- [ ] **Step 4: Run to verify they pass**

- [ ] **Step 5: Commit**

---

### Task 3: `overlay.py` — the window that draws

**Files:**
- Create: `SkeldarAnim/maya_curveview/overlay.py`
- Test: `tests/test_curveview_overlay.py`

**Interfaces:**
- Consumes: `mapping` (Frame, Rect, to_pixels, axis_colour).
- Produces:
  - `Scene(frame, curves, current_time, message)` namedtuple, where each entry
    of `curves` is `Drawn(attribute, samples, keys, selected)` —
    `samples` a list of `(t, v)`, `keys` a list of `(t, v)`, `selected` a set
    of key indices.
  - `click_through(widget) -> int` (the resulting ex-style)
  - `CurveOverlay(QWidget)` with `set_scene(scene)`, `place(rect)`,
    `close_overlay()`.
  - `MODULE-LEVEL: overlay.py must not import maya.cmds.`

- [ ] **Step 1: Write the failing test**

```python
import os
import subprocess
import sys
import unittest


class TestPurity(unittest.TestCase):
    def test_overlay_never_imports_maya_cmds(self):
        script = (
            "import sys\n"
            "from maya_curveview import overlay\n"
            "print('maya.cmds' in sys.modules)\n")
        plugin = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "SkeldarAnim")
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
        result = subprocess.run([sys.executable, "-c", script], env=env,
                                cwd=plugin, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "False")


class TestSceneShape(unittest.TestCase):
    def test_a_drawn_curve_carries_its_own_selection(self):
        from maya_curveview import overlay
        drawn = overlay.Drawn("translateX", [(0.0, 0.0)], [(0.0, 0.0)], {0})
        self.assertEqual(drawn.selected, {0})
```

- [ ] **Step 2: Run to verify it fails**

- [ ] **Step 3: Write `overlay.py`**

`click_through` sets `WS_EX_LAYERED | WS_EX_TRANSPARENT` through
`user32.SetWindowLongPtrW` with explicit `argtypes`/`restype` (a truncated
handle on 64-bit is CLAUDE.md trap 26) and flushes with `SetWindowPos`. On a
non-Windows platform it returns 0 and does nothing. `CurveOverlay` is
`FramelessWindowHint | Tool` with `WA_TranslucentBackground`,
`WA_NoSystemBackground` and `WA_TransparentForMouseEvents`; `place` calls
`setGeometry` then `show()` then `click_through` — in that order, because
the ex-style is lost when the native window is recreated. `paintEvent` draws,
in order: the vertical frame grid, the current-time line, each curve's sample
polyline, each key as a 7 px square, selected keys filled white, and the
message text in the top-left corner.

- [ ] **Step 4: Run to verify it passes**

- [ ] **Step 5: Commit**

---

### Task 4: `viewport.py` — where the viewport is, right now

**Files:**
- Create: `SkeldarAnim/maya_curveview/viewport.py`
- Test: `tests/test_curveview_viewport.py`

**Interfaces:**
- Produces:
  - `active_panel() -> str | None`
  - `gl_widget(panel) -> QWidget | None`
  - `global_rect(widget) -> (x, y, w, h) | None`
  - `panel_rect(panel=None) -> (x, y, w, h) | None`

- [ ] **Step 1: Write the failing test** — with a fake `cmds`, assert
  `active_panel` prefers the panel with focus and otherwise takes the first
  visible model panel, and answers `None` when there is none.

```python
import unittest

from maya_curveview import viewport


class FakeCmds(object):
    def __init__(self, panels=(), focus=None, types=None):
        self._panels = list(panels)
        self._focus = focus
        self._types = types or {}

    def getPanel(self, **kwargs):
        if kwargs.get("withFocus"):
            return self._focus
        if kwargs.get("visiblePanels"):
            return list(self._panels)
        if "typeOf" in kwargs:
            return self._types.get(kwargs["typeOf"], "")
        return []


class TestActivePanel(unittest.TestCase):
    def tearDown(self):
        viewport.cmds = viewport._real_cmds

    def test_focus_wins_when_it_is_a_model_panel(self):
        viewport.cmds = FakeCmds(panels=["modelPanel1", "modelPanel4"],
                                 focus="modelPanel4",
                                 types={"modelPanel1": "modelPanel",
                                        "modelPanel4": "modelPanel"})
        self.assertEqual(viewport.active_panel(), "modelPanel4")

    def test_falls_back_to_the_first_visible_model_panel(self):
        viewport.cmds = FakeCmds(panels=["outlinerPanel1", "modelPanel1"],
                                 focus="outlinerPanel1",
                                 types={"outlinerPanel1": "outlinerPanel",
                                        "modelPanel1": "modelPanel"})
        self.assertEqual(viewport.active_panel(), "modelPanel1")

    def test_no_model_panel_at_all(self):
        viewport.cmds = FakeCmds(panels=["outlinerPanel1"], focus=None,
                                 types={"outlinerPanel1": "outlinerPanel"})
        self.assertIsNone(viewport.active_panel())
```

- [ ] **Step 2–4: fail, implement, pass.** `gl_widget` wraps
  `MQtUtil.findControl(panel)` and searches its children for the class name
  `QmayaGLWidget` — measured as the native GL surface. Everything Qt-side is
  guarded so a headless test can call the `cmds`-only half.

- [ ] **Step 5: Commit**

---

### Task 5: `tool.py` — the mode (stage 1 complete)

**Files:**
- Create: `SkeldarAnim/maya_curveview/tool.py`
- Modify: `SkeldarAnim/maya_curveview/__init__.py`
- Test: `tests/test_curveview_tool.py`

**Interfaces:**
- Produces:
  - `toggle() -> str`, `enable() -> str`, `disable() -> str`, `is_on() -> bool`
  - `refresh() -> None`
  - `on_press() / on_drag() / on_release()` — the dragger context callbacks
  - `CONTEXT = "skeldarCurveViewCtx"`
  - `select_from_screen(x0, y0, x1, y1, modifier) -> None`
  - `build_scene(rect) -> overlay.Scene`
  - Module-level singleton `_STATE`.

- [ ] **Step 1: Write the failing tests** for the pure-ish parts: that
  `build_scene` produces one `Drawn` per visible curve with the samples and
  keys in place (fake `curves`), that `on_press` classifies a press into
  `"key"` or `"scene"` by whether a key is under the point, and that a press
  with no overlay standing is a no-op rather than a traceback.

```python
import unittest

from maya_curveview import mapping, tool


class FakeCurve(object):
    def __init__(self, attribute, curve, keys):
        self.attribute, self.curve, self.keys = attribute, curve, keys
        self.plug = "ctrl." + attribute
        self.node = "ctrl"


class FakeCurves(object):
    def __init__(self, found):
        self.found = found

    def visible_curves(self):
        return self.found

    def sample(self, curve, t0, t1, count):
        return [(t0, 0.0), (t1, 1.0)]

    def selected_indices(self, curve):
        return []

    def time_range(self):
        return (0.0, 100.0)


class TestBuildScene(unittest.TestCase):
    def tearDown(self):
        tool.curves = tool._real_curves

    def test_one_drawn_curve_per_visible_curve(self):
        tool.curves = FakeCurves([FakeCurve("translateX", "curveA",
                                            [(0.0, 0.0), (10.0, 1.0)])])
        scene = tool.build_scene(mapping.Rect(1000, 500))
        self.assertEqual(len(scene.curves), 1)
        self.assertEqual(scene.curves[0].attribute, "translateX")
        self.assertEqual(scene.curves[0].keys, [(0.0, 0.0), (10.0, 1.0)])

    def test_nothing_selected_gives_an_empty_scene(self):
        tool.curves = FakeCurves([])
        scene = tool.build_scene(mapping.Rect(1000, 500))
        self.assertEqual(scene.curves, [])
```

- [ ] **Step 2–4: fail, implement, pass.**

`enable()`: resolve the panel, build the overlay, `place` it, create the
dragger context with **Python** command strings
(`"import maya_curveview.tool as t; t.on_press()"`), remember
`cmds.currentCtx()`, `setToolTo`, install the scriptJobs
(`SelectionChanged` → `refresh`, `ToolChanged` → `disable` when the context is
no longer ours, `timeChanged` → repaint) and start the 10 Hz geometry timer.

**The geometry timer, not an event filter, and the reason belongs in the
code:** Maya destroys and rebuilds these widgets on a layout change, so a
filter installed on one of them dies with it; a timer comparing the rect
costs nothing and covers the window move, `Ctrl+Space`, the layout switch and
a move to another monitor in one mechanism.

`on_press`: read `anchorPoint`, `button`, `modifier`; flip Y; if
`pick_key` finds a key → the gesture is about keys, else about the scene.
Record the anchor. Open no undo chunk yet — a click is not an edit.

`on_drag` for a scene gesture: repaint a marquee rectangle. For a key gesture
on button 1: nothing (LMB only selects).

`on_release` for a scene gesture: `select_from_screen` with the box (or the
click) and the adjustment from the modifier;
`om.MGlobal.selectFromScreen(x0, y0, x1, y1, adjustment, om.MGlobal.kWireframeSelectMethod)`
— note **the Y it wants is Maya's own bottom-up Y**, which is what the dragger
already gave us, so no flip on this path. For a key gesture: `cmds.selectKey`
with replace/toggle/remove/add.

- [ ] **Step 5: Commit** — stage 1 is now usable: the mode draws and selection
  still works.

---

### Task 6: the MMB drag (stage 2)

**Files:**
- Create: `SkeldarAnim/maya_curveview/edits.py`
- Modify: `SkeldarAnim/maya_curveview/tool.py`
- Test: `tests/test_curveview_edits.py`

**Interfaces:**
- Produces:
  - `begin() -> None` (opens the undo chunk)
  - `end() -> None` (closes it)
  - `apply_delta(dt, dv) -> None` — relative move of the **selected** keys
  - `follow_time(t, now, last, interval=0.05) -> float | None` — sets the
    current time when the throttle allows, returning the new `last`
  - `settle(t) -> None` — the guaranteed evaluation on release

- [ ] **Step 1: Write the failing tests** with a fake `cmds`: that
  `apply_delta` sends one relative `keyframe` edit with `animation="keys"`,
  that the chunk is opened once and closed once even when the edit raises,
  and that `follow_time` respects the throttle and returns the timestamp it
  used.

```python
import unittest

from maya_curveview import edits


class FakeCmds(object):
    def __init__(self, fail=False):
        self.calls = []
        self.chunks = []
        self.fail = fail
        self.time = None

    def undoInfo(self, **kwargs):
        if kwargs.get("openChunk"):
            self.chunks.append("open")
        if kwargs.get("closeChunk"):
            self.chunks.append("close")

    def keyframe(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise RuntimeError("no keys selected")

    def currentTime(self, *args, **kwargs):
        if args:
            self.time = args[0]
            return args[0]
        return self.time or 0.0


class TestDrag(unittest.TestCase):
    def tearDown(self):
        edits.cmds = edits._real_cmds

    def test_apply_delta_moves_the_selected_keys_relatively(self):
        fake = FakeCmds()
        edits.cmds = fake
        edits.apply_delta(2.0, 0.5)
        self.assertEqual(len(fake.calls), 1)
        call = fake.calls[0]
        self.assertTrue(call["relative"])
        self.assertEqual(call["timeChange"], 2.0)
        self.assertEqual(call["valueChange"], 0.5)
        self.assertEqual(call["animation"], "keys")

    def test_a_zero_delta_writes_nothing(self):
        fake = FakeCmds()
        edits.cmds = fake
        edits.apply_delta(0.0, 0.0)
        self.assertEqual(fake.calls, [])

    def test_the_chunk_closes_even_when_the_edit_raises(self):
        fake = FakeCmds(fail=True)
        edits.cmds = fake
        edits.begin()
        try:
            edits.apply_delta(1.0, 0.0)
        except RuntimeError:
            pass
        edits.end()
        self.assertEqual(fake.chunks, ["open", "close"])

    def test_follow_time_respects_the_throttle(self):
        fake = FakeCmds()
        edits.cmds = fake
        stamp = edits.follow_time(10.0, now=1.0, last=None, interval=0.05)
        self.assertEqual(fake.time, 10.0)
        self.assertEqual(stamp, 1.0)
        held = edits.follow_time(11.0, now=1.01, last=1.0, interval=0.05)
        self.assertEqual(fake.time, 10.0)
        self.assertEqual(held, 1.0)
```

- [ ] **Step 2–4: fail, implement, pass.**

In `tool.py`: `on_press` with `button == 2` and at least one selected key
starts a drag — `edits.begin()`, record the anchor and `applied = (0.0, 0.0)`.
`on_drag` computes the total delta from the anchor through
`mapping.to_curve`, snaps the time part to whole frames, sends only the
**difference** from `applied` (so snapping cannot accumulate drift), updates
`applied`, and calls `edits.follow_time` with the dragged anchor key's new
time. `on_release` sends the last difference, calls `edits.settle`, closes the
chunk and refreshes.

- [ ] **Step 5: Commit**

---

### Task 7: tangents, insert and delete (stage 3)

**Files:**
- Modify: `SkeldarAnim/maya_curveview/curves.py`, `edits.py`, `overlay.py`,
  `tool.py`
- Test: `tests/test_curveview_tangents.py`

**Interfaces:**
- `curves.tangents_of(curve, index) -> (in_angle, in_weight, out_angle, out_weight)`
- `overlay.Drawn` gains a `tangents` field: a list of
  `(index, in_point, out_point)` in curve space, only for selected keys.
- `mapping.tangent_points(frame, rect, key, angle_in, angle_out, length=48.0)`
  → the two handle positions in pixels, pure and tested.
- `edits.set_tangent(curve, index, side, angle) -> None`
- `edits.insert_key(curve, time) -> None`, `edits.delete_selected() -> None`

- [ ] **Step 1: Write the failing tests** — `mapping.tangent_points` is the
  part worth pinning: a zero-angle out-tangent points straight right in pixel
  space, a +45° tangent points up-right (Qt Y down means the pixel Y
  decreases), and the handle length is constant in pixels regardless of the
  frame's scale.

```python
def test_a_flat_out_tangent_points_right(self):
    frame = mapping.Frame(0.0, 100.0, 0.0, 10.0)
    rect = mapping.Rect(1000, 500)
    _, out = mapping.tangent_points(frame, rect, (50.0, 5.0), 0.0, 0.0,
                                    length=40.0)
    x, y = mapping.to_pixels(frame, rect, 50.0, 5.0)
    self.assertAlmostEqual(out[0], x + 40.0)
    self.assertAlmostEqual(out[1], y)

def test_a_rising_tangent_goes_up_in_pixels(self):
    frame = mapping.Frame(0.0, 100.0, 0.0, 10.0)
    rect = mapping.Rect(1000, 500)
    _, out = mapping.tangent_points(frame, rect, (50.0, 5.0), 0.0, 45.0,
                                    length=40.0)
    _, y = mapping.to_pixels(frame, rect, 50.0, 5.0)
    self.assertLess(out[1], y)
```

- [ ] **Step 2–4: fail, implement, pass.** Handles are drawn only for selected
  keys, dragged with MMB when the press lands on a handle rather than a key
  (`pick_tangent` before `pick_key` — a handle sits on top), and the angle is
  written with `cmds.keyTangent`. `insert_key` is a double-click on the curve;
  `delete_selected` is bound in `tool.py` to nothing yet — it is called from
  the hotkey row added in task 9.

- [ ] **Step 5: Commit**

---

### Task 8: polish (stage 4)

**Files:**
- Modify: `SkeldarAnim/maya_curveview/overlay.py`, `mapping.py`, `tool.py`
- Test: `tests/test_curveview_normalise.py`

**Interfaces:**
- `mapping.normalise(series) -> [Frame]` — one Y window per curve, so each
  curve fills the band; pure and tested.
- `tool.set_normalise(state)`, remembered in the optionVar
  `skeldarCurveViewNormalise`.
- `overlay` draws the value of a dragged key next to it, and the frame number.

- [ ] **Step 1: Write the failing test** — with two curves of very different
  magnitudes, `normalise` gives each its own window and both then map to the
  same pixel band.

- [ ] **Step 2–4: fail, implement, pass.**

- [ ] **Step 5: Commit**

---

### Task 9: the shelf button, the installer and the hotkeys

**Files:**
- Modify: `SkeldarAnim/install.py:24-58` (`_PAYLOAD`, `_PYTHON_BUTTONS`)
- Modify: `SkeldarAnim/maya_hotkeys.py:57-80` (`DEFAULT_KEYS`,
  `DEFAULT_KEYS_VERSION`) and `_OURS`
- Create: `SkeldarAnim/icons/curveview.png` (generated by
  `SkeldarAnim/icons/make_icons.py`)
- Test: `tests/test_install.py`, `tests/test_hotkeys.py` (extend the existing
  cases rather than adding files)

- [ ] **Step 1: Extend the installer tests** — `payload()` contains
  `maya_curveview`, `module_names()` lists it, and `button_specs` produces a
  ninth Python button whose command imports `maya_curveview` and calls
  `toggle`.

- [ ] **Step 2: Run to verify they fail**

- [ ] **Step 3: Add the rows.** `_PAYLOAD` gains `"maya_curveview"`;
  `_PYTHON_BUTTONS` gains
  `("Curves", "Curve Overlay: the graph editor over the viewport", "maya_curveview", "toggle", "curveview.png")`.
  `maya_hotkeys._OURS` gains `("window.curveview", "Windows", "Curve overlay on/off", ...)` and
  `("curve.delete", "Curve overlay", "Delete selected keys", ...)`;
  `DEFAULT_KEYS` gains `("c", {"altModifier": True}, "window.curveview")` and
  `DEFAULT_KEYS_VERSION` goes to 4. Regenerate the icon.

- [ ] **Step 4: Run the whole suite**

- [ ] **Step 5: Commit**

---

### Task 10: the live verification

**Files:**
- Create: `docs/superpowers/plans/verify_curveview.py`

The project's real standard of proof: unit tests have repeatedly passed while
the scene was broken. Sent through the command port into the animator's own
session, so it must resolve everything by long path or UUID, register what it
creates as it creates it, guard every teardown step on its own, and leave the
frame, the playback range, autoKey, the selection and the current tool exactly
as it found them.

- [ ] **Step 1: Write the gates**

Its own sandbox: one throwaway transform with three animated channels, created
by long path and registered by UUID. Then:

1. `enable()` puts a window up, on the GL widget's rect to the pixel.
2. The ex-style really carries `WS_EX_LAYERED | WS_EX_TRANSPARENT`.
3. `WindowFromPoint` at the overlay's centre does **not** answer our window.
4. The dragger context is current, and its commands are the Python ones.
5. With the sandbox selected, `build_scene` produces three curves; with
   nothing selected, none.
6. The channel-box rule: selecting one channel narrows it to one curve.
7. A key's pixel position round-trips through `to_pixels`/`to_curve` to
   0.000000.
8. `pick_key` finds the key at its own drawn position and misses 40 px away.
9. `select_from_screen` on the sandbox's screen position selects it, and with
   `"toggle"` deselects it.
10. `cmds.selectKey` through our path selects exactly one key of the sandbox.
11. `apply_delta(3, 1.5)` moves that key by exactly 3 frames and 1.5 units,
    and one Ctrl-Z-equivalent undo of the chunk puts it back to 0.000000.
12. `follow_time` throttles: 100 calls inside one interval evaluate once.
13. `disable()` removes the window, deletes the context and restores the
    previously current tool.
14. The scene is as it was: same frame, range, autoKey, selection, tool, and
    no node of ours left.

- [ ] **Step 2: Send it through the bridge and read the output**

- [ ] **Step 3: Fix whatever it finds, re-run until 0 gates fail**

- [ ] **Step 4: Commit**

---

### Task 11: CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1:** Add a `maya_curveview` section — the module table, the mode's
  three behaviours, the measured facts (native GL widget, the layout's
  zero height, `WA_TransparentForMouseEvents` not crossing native windows,
  the Win32 ex-style, Python-not-MEL dragger commands, Y from the bottom,
  ~860 events per drag at 10.4 fps), the gesture table, and the stated costs.
- [ ] **Step 2:** Add the two new traps to the traps list: the `__file__`
  runner trap, and `WA_TransparentForMouseEvents` being a Qt-internal routing
  flag.
- [ ] **Step 3:** Update the installer section from eight buttons to nine.
- [ ] **Step 4: Commit**

---

## Self-Review

**Spec coverage.** Route B (dragger + click-through overlay) — tasks 3, 5.
Module split — tasks 1–5. The mode's three behaviours (tool change leaves,
overlay rides the viewport, hide on focus loss) — task 5. What is drawn,
including the channel-box rule and no-selection-no-curves — tasks 2, 3.
Shared Y axis by default with normalise later — tasks 1, 8. The gesture table
including `selectFromScreen` — task 5. Press-time classification — task 5.
One undo chunk, the throttle — task 6. Tangents — task 7. Stages 1–4 map onto
tasks 5, 6, 7, 8. Shelf and hotkeys — task 9. Live proof — task 10.
Documentation — task 11.

**Placeholders.** None: every code step carries the code, and every "implement"
step names the exact calls and flags.

**Type consistency.** `Frame`, `Rect`, `Curve`, `Drawn` and `Scene` are
defined once each and used under those names throughout. `mapping.Rect` is
what `build_scene`, `to_pixels`, `pick_key` and `keys_in_box` all take.
`curves.Curve.curve` is the animCurve node name everywhere, never the plug.

**One gap found and closed:** the spec's "hidden on focus loss" had no task —
it is now named in task 5's scriptJob list.
