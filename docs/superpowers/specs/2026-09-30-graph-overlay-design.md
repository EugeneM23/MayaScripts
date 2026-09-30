# Graph Overlay — Maya's own Graph Editor over the viewport, background removed

2026-09-30.

## What was asked for

> «А возможно ли для Maya graph editor сделать так что бы его задний фон
> стал прозрачным но при этом все остальные элементы кривые и тд остались
> такимиже?»

Offered a colour-key route with its costs (floating only, a clickable-through
background, a fringe), the animator answered «это все как-то не сильно хорошо
звучит мне нужен граф эдитор с прозрачным фоном». Two design answers after
the measurements below:

- **Shape Б** — a mode: on a key, the Graph Editor's curve area lies exactly
  on the viewport, its menus, toolbar and channel list hidden; the same key
  leaves it. («Давай попробуем Б. А весь функционал графа останется?» — yes:
  every click and key goes to the real Graph Editor.)
- **alt+mouse is the camera** («1, камеры»): while alt is held the graph
  lets the mouse through to the viewport; the graph is framed with F/A.

It is the Curve Overlay's idea (2026-09-05, archived 2026-09-08) with the
drawing and the input taken from Maya's own Graph Editor instead of ours, so
weighted tangents, retime, sculpting, buffer curves and every hotkey come for
free.

## What was measured before anything was designed

In a disposable Maya 2027.2 (scratch `MAYA_APP_DIR`, port 7003), never the
animator's scene.

| fact | measured |
|---|---|
| the curve area | a native child HWND `Qt683QWindowOwnDCIcon`; Qt class chain `TanimCurveCanvas → QmayaCanvasWidgetGL → QOpenGLWindow → QPaintDeviceWindow → QWindow`; OpenGL surface, **8 alpha bits**, pixel-format flags `0x8205` (SUPPORT_COMPOSITION, SWAP_EXCHANGE, DRAW_TO_WINDOW, DOUBLEBUFFER), `UpdateBehavior.NoPartialUpdate` |
| its colours | `modernGraphEditor*`; background `modernGraphEditorBackground` 0.251 grey. `displayRGBColor` takes a 4th value with `alpha=True` |
| background alpha 0 | **ignored**: `grabFramebuffer()` reads alpha 255 on every pixel at bg alpha 0 and at 1 |
| DWM | `DwmExtendFrameIntoClientArea(-1)` on the floating Graph Editor: the graph stayed (64, 64, 64) over a green sheet behind it |
| reading the picture | `grabFramebuffer()` returns the canvas exactly (a PNG of it is the Graph Editor), **2.3 ms at 861×500, 2.9 ms at 968×723**. PySide hands the window back as `QPaintDeviceWindow`: `shiboken6.invalidate` the cached wrapper, then `wrapInstance(ptr, QtOpenGL.QOpenGLWindow)` |
| an invisible Graph Editor | its top-level made `WS_EX_LAYERED` + `LWA_ALPHA` **1**: it **keeps rendering** (`frameSwapped` fired after a time change, the marker moved from x 29–65 to 255–291) and **keeps taking clicks** (`WindowFromPoint` at the canvas centre answered the canvas HWND) |
| our own panel | `cmds.scriptedPanel(type="graphEditor")` inside a frameless Qt top-level of ours (the hub skin's `setParent(fullName(layout))`): a working modern Graph Editor, editors `<panel>GraphEd` / `OutlineEd` |
| its chrome | menu bar: `scriptedPanel -menuBarVisible false`; toolbar: its one `frameLayout` (found as the parent of the panel's `QadskFrameLayoutFrame`) `manage=False`; channel list: the `QSplitter` holding `TanimCurvePort3`, handle width 0, sizes `[0, all]` |
| alignment | with the chrome gone the canvas sits (5, 3) into the host with 8×6 of border; the host placed from that, the canvas rect equals the viewport's GL rect **pixel for pixel**, native HWNDs included — `(462, 374, 861, 500)` both |
| keying cost | a float32 numpy keyer 54 ms at 968×723; uint8 lookup tables 9 ms at 861×500 but 44.5 ms at 1850×1067; Qt's own image ops (Difference + grey + index table + setAlphaChannel) 14.9 ms at 1850×1067; **uint8 numpy, straight alpha, 4 threads: 5.7 ms at 1850×1067** (19.7 ms on one); drawing the result 1.2 ms |

Two probe lessons, paid for: a green topmost backing sheet used for screen
captures covered the animator's screen until they asked for it to go — no
probe window is ever left topmost on their screen, the look is proved
offscreen (the keyed frame composited over a playblast); and an alpha-1
window is invisible but eats clicks, so the disposable Maya is killed when a
run pauses.

## The route

Maya's drawing cannot be made transparent (alpha ignored, measured). So:

1. **The ghost**: a Graph Editor panel of our own in a frameless host,
   chrome hidden, placed so its canvas covers the viewport exactly, made
   invisible with `LWA_ALPHA` 1. Every click and key lands on it — Maya's
   own Graph Editor, all of it.
2. **The glass**: a frameless translucent click-through top-level of ours
   (the Curve Overlay's measured window: `WA_TranslucentBackground`, then
   `WS_EX_LAYERED | WS_EX_TRANSPARENT` after `show()`) on the same
   rectangle, showing the ghost's frames with the background taken out.
3. On every `frameSwapped` of the canvas — coalesced through a zero-time
   single-shot timer, at most every `MIN_UPDATE_MS` — `grabFramebuffer`,
   key, paint.
4. **alt**: a 30 ms timer reads `GetAsyncKeyState(VK_MENU)`; held, the ghost
   gets `WS_EX_TRANSPARENT` and the click goes to the viewport — the camera
   in Maya's own dispatch; released, it takes clicks again. Toggling the
   style mid-drag does not disturb a drag already captured.

The ghost and the glass are both owned by Maya's main window: they ride its
z-order and hide with it, and neither is ever topmost. Which of the two is
on top does not matter — the ghost's 1/255 changes nothing visible, and the
glass is click-through.

## Keying

The background is one flat colour K. K is **measured from the first frame**
(the most common colour of a sparse sample) rather than read from a
preference, so the classic Graph Editor and a customised colour work too;
nothing of the animator's colour preferences is written.

Straight alpha, the colours untouched: `alpha = LUT[max_c |P_c − K_c|]`,
`LUT(d) = min(255, d·255/SOFT)`, `SOFT` 28 levels. A background pixel is 0,
anything 28 levels off K is opaque — curves, keys, tangent handles, the
numbers, the time marker. The grid (23 levels off K) comes out at 82 %, the
ruler band and the value column (9–14 levels) at 30–50 %: still there, and
the viewport reads through them. Anti-aliased curve pixels keep the K they
were blended with, which is exactly how the curve looks in the Graph Editor.

Pure, numpy only (`keying.py`), four horizontal bands on a small thread pool
(numpy releases the GIL).

## Following the viewport

A 10 Hz timer (the Curve Overlay's rule: Maya rebuilds panel widgets on a
layout change, so an event filter dies with them) re-reads the active model
panel's GL rect and, when it moved, re-places the glass and re-aligns the
ghost by measuring its canvas again (`host_rect`, pure). No model panel, or
Maya not the active application: the glass hides and the ghost lets clicks
through. Our panel gone (a scene's UI configuration can delete panels):
leave the mode. A scene opened or created: leave the mode.

The active model panel is the focused one, else the first visible
(the archived `viewport.active_panel`). Every Qt wrapper the timer reads
through is held for as long as it is used (hub skin trap 96).

## Where it lives

- `SkeldarAnim/maya_graphoverlay/` — a package:
  `keying.py` (numpy only), `geometry.py` (pure rectangles and the alt
  rule), `winstyle.py` (ctypes only), `ghost.py` (our Graph Editor panel in
  its host: build, chrome, canvas, align, destroy), `glass.py` (the
  see-through window; Qt only), `mode.py` (enable / disable / toggle, the
  timers, the frame pipeline, the hub section), `__init__.py` (lazy).
- A hub section **Graph Overlay** in the Animation group, icon
  `chart-line`: one hint line, the toggle button, a status line. No shelf
  button (the 2026-09-17 rule).
- Hotkey row `graph.overlay`, bound to **alt+c** in our set — the Curve
  Overlay's key, given back on 2026-09-08 and free again for the same idea;
  it leaves `RELEASED_KEYS` (a key is never in both tables),
  `DEFAULT_KEYS_VERSION` 6.
- A payload row.

## What it does not do

- The Graph Editor's menus and toolbar are not shown in the mode; their
  commands are its hotkeys and its right-click menus.
- Clicking the scene while in the mode: alt goes to the camera; selecting
  another object is the outliner, the channel box, or leaving the mode.
- One viewport at a time.
- Windows only (the ghost and the click-through are Win32 styles).
- `playblast` never shows the overlay — it is a window, not part of the
  viewport render.

## Testing

Unit tests on the pure halves (keying against a hand-built frame, K from a
histogram, the host rectangle, the alt rule, the section and hotkey tables),
the purity rules by subprocess (keying imports no Maya and no Qt, glass no
`maya.cmds`), and the mode's refusals and toggling on fake seams.

Live proof `docs/superpowers/plans/verify_graphoverlay.py` in a disposable
Maya: the ghost invisible and its canvas on the viewport pixel for pixel,
the glass on the same rect and click-through, a time change reaching the
glass, a key selected by a click on its pixel in the invisible graph, alt
letting the ghost click through and taking it back, the cost per update at
full size, the look composited offscreen over a playblast, and leaving the
mode removing every window, panel and timer while the colour preferences
stay as they were.

## Addendum — the live run (the animator's Maya on port 7001, 2026-09-30)

The animator chose their own Maya (an untitled scene) for the proof over a
disposable one — the disposable windows had been appearing on their screen
and were closed twice. Five things the run changed, each measured:

1. **Qt drops a WS_EX_LAYERED it did not set.** `winstyle.make_ghost` set the
   bit and the alpha behind Qt's back; the style came back `0xa0` (the bit
   gone), the "invisible" Graph Editor stood grey over the viewport, and the
   follow timer's re-assertions made it redraw ~40 times a second. The ghost
   is made invisible with Qt's own `setWindowOpacity(1/255)` now: `0x80080`,
   alpha 1, no redraw at rest. That same call dropped our WS_EX_TRANSPARENT,
   so the alt poll compares with the window's REAL style every time instead
   of a remembered one, and the glass asks Qt for `WindowTransparentForInput`
   (the follow timer puts WS_EX_TRANSPARENT back should it go).
2. **Four copies of `mode` each held a state.** Purges (an install, the
   verify's own, the hub's rebuild importing afresh) left the running overlay
   in a copy nobody could reach while `import` handed out one that said it was
   off — trap 49's shape. The state hangs off `sys`
   (`_skeldar_graphoverlay_state`) and a state an older copy made gains any
   new field.
3. **The background is two tones**: 64 inside the playback range (48 % of the
   frame), 55 outside it (45 %); keyed against 64 alone the 55 stood 32 %
   opaque — grey panels over the animator's light viewport. Every colour
   covering 5 % of a frame is a key (`keying.backgrounds`), learnt over frames
   and never forgotten (`mode.learn_tones`, at most three), alpha from the
   nearest. 93 % of a framed view is clear.
4. **A posted click drags.** Maya's PySide6 ships no QtTest, so the proof posts
   WM_LBUTTONDOWN/UP to the canvas; the Graph Editor takes the press at the
   posted pixel but reads the REAL cursor while the button is down, so it drags
   the grabbed key towards wherever the mouse is (60 → 80.46 on the first try).
   The gate proves which key was grabbed — the one under the pixel, and no
   other curve — and puts every key back.
5. **Hit tests see other programs.** Gate 12 (`WindowFromPoint` on the canvas
   after alt) failed once with the canvas of the animator's OTHER Maya's
   floating Graph Editor answering; rerun with that window moved, it passed.

Numbers on the animator's viewport (1526×1044): one frame grabbed, keyed and
shown in **8.5–9.3 ms**, the grab alone 3.7 ms; the canvas on the viewport
pixel for pixel; no redraw at rest.
