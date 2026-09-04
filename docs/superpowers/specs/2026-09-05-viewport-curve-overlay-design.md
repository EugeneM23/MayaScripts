# Curve Overlay — the graph editor over the viewport

2026-09-05.

## What was asked for

> «а СУЩЕСТВУЕТ ЛИ КАКАЯ-ТО ВОЗМОЖНОСТЬ сделать свой кастомный граф эдитор в
> мая? Было бы хорошо если бы кривые рисовались прямо поверх вьюпорта, так
> чтобы я мог двигать кривую прямо во вьюпорте (не путать с редактируемым
> моушен трейлом, он находится в сцене а я говорю про перенос кривых из граф
> эдитора на экран вьюпорта). Было бы классно если бы какой-то режим
> превращал мой вьюпорт в граф эдитор с прозрачным фоном»

Five answers narrowed it, each the animator's own choice:

- **A full graph editor**, not a read-only display — keys, tangents, marquee,
  several channels.
- **Why:** «Хочу править кривые и сразу же смотреть на результат, это очень
  удобно.» The feature is the feedback loop, not the screen real estate.
- **Shape:** the whole viewport, transparent background, a **toggle** mode.
- **Which curves:** the channel-box rule. «Если у нас не выделен объект то и
  кривые его рисовать не нужно.»
- **Time during a drag:** «кадр едет за ключом» — the drag is the scrub, so
  the pose under the curve is the pose being edited.
- **Navigation:** none. Autoframe instead, so every camera gesture stays the
  camera's.
- **Gestures:** as in the Graph Editor — LMB selects, MMB drags keys.
- Keys are drawn as points **on** the keys, «все как в граф эдиторе».

## What was measured before anything was designed

The architecture was chosen from numbers, not from an opinion about Qt. Five
probes through the command port into the animator's own session (Maya 2027,
Qt 6.8.3, PySide6 6.8.3, Windows 11), plus API introspection in `mayapy`.

### The API surface

| fact | measured |
|---|---|
| `MUIDrawManager` 2D family | `line2d`, `mesh2d`, `text2d`, `circle2d`, `rect2d`, `arc2d`, `point2d` — screen-space drawing exists |
| `MUIDrawManager()` | **cannot be instantiated** (`RuntimeError: cannot be instantiated`) — one is only ever handed to you |
| `maya.api.OpenMayaUI.MPxContext` | exists, with `drawFeedback`, `doPress`, `doDrag`, `doRelease`, `doPtrMoved`, `setCursor` |
| `MRenderer.addNotification` | **absent in API 2.0** (only `registerOverride` / `deregisterOverride`) |
| `MHUDRender`, `MRenderOverride`, `MPxDrawOverride` | all present |
| `MGlobal.selectFromScreen` | present, **two** signatures — `(x, y, …)` click and `(x, y, x2, y2, …)` box — with `kReplaceList` / `kXORWithList` / `kRemoveFromList` / `kAddToList` |
| API 1.0 (`maya.OpenMayaMPx`) | still imports in 2027 |
| `cmds.draggerContext(space="screen")` | accepted |

So a draw manager can only be reached three ways: a scene node's
`MPxDrawOverride`, a whole-pipeline `MRenderOverride`'s `MHUDRender`, or a
context's `drawFeedback`.

### The viewport's widget tree

```
QmayaLayoutWidget 'modelPanel5'          native=200090
  QmayaLayoutWidget 'modelPanel5'        native=265618
    QWidget 'mayaLayoutInternalWidget'   native=396244
      QStackedWidget 'modelPanel5'       native=265620
        QmayaGLWidget ''  1850x1067      native=3935764
```

**`QmayaGLWidget` is a native Windows window.** A native child window
composites above every non-native sibling, so a plain child widget cannot
paint over the viewport at all. And Maya's own layout owns the panel: a child
overlay given `setGeometry(0, 0, half, height)` came back as
**`QRect(1, 1108, 1850, 0)`** — height zero — and its `paintEvent` ran **0
times**. Both halves of that are traps: the native window and the layout.

### The overlay that does work

A frameless translucent **top-level** window composites over live GL with real
alpha: the character, the grid, the manipulator arrows and Maya's own
`Focal Length / 10.4 fps` HUD all read through a 35 %-alpha fill, with an
antialiased QPainter curve on top. Screenshot taken with
`QScreen.grabWindow(0, x, y, w, h)` over the viewport rect.

`widget.grab()` is not the tool here — CLAUDE.md note 3 is about Qt panels,
and a viewport is not one (the `maya_vpstudio` lesson: a `grab()` of a model
panel returns chrome and a blank white rectangle where the GL surface is).

### Click-through is a Win32 fact, not a Qt one

| | measured |
|---|---|
| `WA_TransparentForMouseEvents` on a top-level window | **does not pass the mouse through.** Under the overlay: no marquee, no camera orbit |
| exStyle as Qt left it | `0x00080088` — layered **yes**, transparent **no** |
| after `WS_EX_LAYERED \| WS_EX_TRANSPARENT` | `0x000800A8`, and `WindowFromPoint` stops returning our window |
| after that, by hand | `alt+LMB` orbits the camera straight through the overlay |

`WA_TransparentForMouseEvents` is a Qt-internal routing flag: it forwards an
event to the widget below **inside the same window**, and Qt forwards nothing
across a native-window boundary. The Windows recipe is the ex-style, applied
with ctypes **after `show()`** — re-parenting recreates the native window and
loses it.

`WindowFromPoint` is the honest test with no hands needed: the docs say it
skips a window carrying `WS_EX_TRANSPARENT`, which is the same decision a real
click takes. (It answered `Chrome_RenderWidgetHostHWND` rather than the
viewport, because the app the animator was reading in stood in front — the
mechanism was still proved: our window was skipped.)

### The input channel

`cmds.draggerContext` **runs its command as Python, not MEL.** A first version
passed `'python("...")'`, MEL style, and the press answered
`NameError: name 'python' is not defined` — which is itself the proof that the
callback fires.

One recorded session, two drags:

| | measured |
|---|---|
| events | **1729** — 2 press, **1725** drag, 2 release |
| point | arity 3, `[x, y, 0.0]`, viewport-local |
| Y direction | from the **bottom**: `qt_y = height − y`, confirmed by eye against two drawn markers |
| `button` | `1` for LMB |
| `modifier` | a **string**, `'none'` — so shift/ctrl are available |
| `alt` | all 1725 drags carried `'none'`: alt never reaches us, the camera takes it upstream |

**~860 events per drag, about one per pixel of travel.** That number is the
reason the time-follows-key rule needs a throttle: the animator's scene runs
**10.4 fps**, and 860 rig evaluations per drag is seconds of stall.

## The route, and the two that were rejected

| | input | drawing | plugin | `alt` = camera |
|---|---|---|---|---|
| **A** | `MPxContext` | `MUIDrawManager` 2D in `drawFeedback` | needed | native |
| **B — chosen** | `cmds.draggerContext(space="screen")` | top-level translucent window, click-through via ctypes | none | native |
| **C** | the Qt overlay itself | QPainter | none | **broken** |

**C is dead on the measurement**: the overlay eats every event, and the GL
widget being native means a child overlay is invisible anyway. Returning the
camera would mean re-implementing tumble/track/dolly from mouse deltas.

**A stays the fallback** and its one unknown was never closed — whether
`drawFeedback` is called on every viewport refresh or only during interaction.
It was not measured because B was confirmed first, and A is only reached if B
fails. Its costs, for the record: a real Maya plugin (this repo has never
shipped one), polyline-only drawing, and hit-testing written by hand — which B
needs too.

**B's synthesis is the point:** input comes from an ordinary Maya context, so
`alt`+mouse goes to the camera in Maya's own event dispatch rather than in our
code; and the overlay is a pure painter that the OS hit-tests straight
through, so it cannot conflict with anything. QPainter then gives beziers,
fonts, antialiasing and alpha, which a full editor with tangents and a marquee
needs.

## Modules

`SkeldarAnim/maya_curveview/`, the ninth shelf button. The repo's split: the
fiddly arithmetic in pure functions taking the scene as data, thin wrappers
around Maya.

| module | responsibility | may import |
|---|---|---|
| `mapping.py` | **all the arithmetic**: time/value ↔ pixels, the Y flip, autoframe, "which key is under this point", marquee → key set, the modifier→`listAdjustment` table, frame snapping, the throttle decision | **stdlib only** |
| `curves.py` | which curves are drawn (the channel-box rule), plugs → animCurves, sampling for the drawing | `maya.cmds` |
| `edits.py` | applying an edit: moving keys, the undo chunk, time-follows-key and its throttle | `maya.cmds` |
| `overlay.py` | the window: translucency, click-through, geometry tracking, painting | **Qt only** + `ctypes` |
| `viewport.py` | the active model panel's GL widget, its global rect, the events that move it | `maya.cmds`, Qt |
| `tool.py` | the dragger context, press/drag/release → mapping → edits, entering and leaving the mode | `maya.cmds` + all the above |

`mapping.py` is the heart and it is pure — testable with no Maya at all, like
`bodymap` and `pickerstate` in the picker. Every bug this kind of tool has
("the key is grabbed off to one side", "the marquee catches too much") lives
there and is catchable by a unit test. A subprocess test enforces that it
imports neither Maya nor Qt, and that `overlay.py` never imports `maya.cmds`.

**Sample the animCurve node, not the driven plug.** `cmds.getAttr(plug,
time=t)` pulls a rig evaluation per sample — the same 10 fps, per sample.
`cmds.keyframe(curve, query=True, eval=True, time=(t, t))` evaluates the curve
by itself and never touches the rig.

## The mode

The shelf button (or a `maya_hotkeys` row) toggles it. On: create the overlay
and set our dragger context, remembering the previous tool. Off: restore the
tool and destroy the window. With nothing selected the overlay draws nothing
at all — the mode is legible from the crosshair cursor and the lit shelf
button, as `maya_hotkeys` already does with its own.

Three behaviours that the probe itself argued for:

1. **Changing the tool leaves the mode.** Press W and the context is no longer
   ours, so an overlay still hanging there lies: curves are drawn and nothing
   can grab them. This is exactly what happened between probes 1 and 2 —
   `moveSuperContext` with our overlay still up and a dead log. A scriptJob on
   the tool change takes the overlay down.
2. **The overlay rides the viewport.** Moving the Maya window, `Ctrl+Space`,
   switching layouts — the GL widget's rect changes and the curves end up
   somewhere else. An event filter on move/resize, and the rect re-resolved.
3. **The overlay sits above Maya's panels.** It fills no background, only
   lines, so a menu opened over the viewport stays readable — but the lines
   cross it. Hidden on focus loss, which also makes the window polite: probe 1
   used `WindowStaysOnTopHint` and left a cyan panel floating over the
   animator's other application.

## What is drawn

- No selection → nothing.
- A selected control → the channel-box selected channels; nothing selected
  there → every animated channel.
- Points on the keys, selected keys brighter.
- Colours by axis, Maya's own convention: X red, Y green, Z blue, anything
  else neutral.
- Autoframe: X is the playback range — so the curve's time lines up under the
  time slider and is read against the frame ruler the animator already knows.
  Y fits the visible curves with a margin.

**One shared Y axis, not per-curve normalisation.** With several channels at
once the magnitudes are not comparable — `translateY` around a hundred and
`rotateZ` at thirty degrees on one axis give one real curve and one flat line.
Shared is honest, it is what the Graph Editor defaults to, and for the three
rotation channels of a control (comparable magnitudes) it is simply correct.
A normalise toggle is stage 4.

## Interaction

| gesture | effect |
|---|---|
| LMB on a key | select that key; shift toggles, ctrl removes, ctrl+shift adds |
| LMB marquee over keys | select that set |
| LMB on empty space | ordinary object selection — `MGlobal.selectFromScreen`, click or box, the same modifier mapping |
| MMB drag | move the selected keys: X is time, snapped to whole frames; Y is value |
| `alt`+anything | the camera, natively; we never see it |

**"A key or empty space" is decided on press**, not during the drag: a marquee
starts at the same point, and deciding later leaves the gesture ambiguous for
as long as it takes to move a few pixels.

**One undo chunk per drag**, opened on press and closed on release. Without it
Ctrl+Z unpicks a drag into 800 steps.

**Time follows the dragged key**, throttled to about 20 Hz, with one
guaranteed evaluation on release. Measured basis: 860 drag events per drag at
10.4 fps.

## Stages

1. **Mode, overlay, drawing.** Curves, keys, autoframe, viewport geometry
   tracking — and object selection through `selectFromScreen` from the start.
   Without it the mode takes the animator's selection away and cannot be
   worked in; that is a condition of usability, not polish.
2. **Key selection and the MMB drag.** Time following, the throttle, the undo
   chunk.
3. **Tangents.** Handles drawn, dragged, break/unify. Inserting and deleting
   keys.
4. **Polish.** Value labels, the normalise toggle, line legibility over a
   mesh, colours.

## Costs, stated

- **10.4 fps on the animator's scene.** The throttle is mandatory and the drag
  will still be heavy. To be measured on the real rig in stage 2, not assumed.
- **The overlay is above Maya's panels.** A menu over the viewport gets the
  curve lines drawn across it. Reduced by hiding on focus loss, not removed.
- **Windows only.** Click-through is `WS_EX_LAYERED | WS_EX_TRANSPARENT`. Mac
  and Linux would need another mechanism; the studio is on Windows.
- **One viewport at a time** — the active model panel.
- **`playblast` never sees the overlay.** It is an OS window, not part of the
  viewport render, so reviews come out clean of curves. Worth knowing rather
  than fixing.
- **Not yet proved:** `Ctrl+Space`, layout switches, and a move to a monitor
  with a different DPI. Guessing is not allowed here — the layout already put
  a widget's height at zero once.

## Not built

Tangent editing beyond stage 3's handles (no weighted-tangent dragging), curve
cycling/infinity display, per-curve normalisation before stage 4, the Dope
Sheet's key grid, retiming tools, and route A's `MPxContext` plugin (kept in
this document as the fallback if the overlay window ever stops compositing).

## Harness note

`__file__` does not exist in a file the command port runs as
`exec(open(path).read())`, so a runner deriving its own directory from it
raises **before** writing its marker — which reads exactly like a dead bridge
(CLAUDE.md notes 6/7/8) and is really trap 17's family. Hardcode the path.

---

## Addendum, 2026-09-05 — what the build and the live run changed

Three decisions in the main text were replaced by measurement. Read these
rather than the paragraphs above where they disagree.

**The gesture rule is "keys first, the scene when no key was caught", not a
press-time classification.** The main text decides on press whether a
gesture is about keys or about the scene, and that is right for a click and
wrong for a marquee: a box's contents are only known when it closes, and
starting a rubber band exactly on a key to select several is fiddly, while
starting it on empty space is how the Graph Editor's own band works. So LMB
always operates on keys — click or marquee — and falls through to
`selectFromScreen` when it caught none. One rule, decided by what was
caught, uniform for both, and both halves reachable with no modal switch.

**`MGlobal.selectFromScreen`'s CLICK form of `kXORWithList` is a NO-OP.**
Measured from both starting states:

| adjustment | from an empty selection | from one already holding it |
|---|---|---|
| `kReplaceList` | selects | selects |
| `kAddToList` | selects | stays |
| `kXORWithList` | **nothing** | **stays** |
| `kRemoveFromList` | nothing | removes |
| `kXORWithList`, **box** form | — | removes |

So a shift-click routed through the API's own adjustment silently did
nothing — the animator shift-clicks, sees no change, and blames their aim.
The pick is now always `kReplaceList`, the one value measured to behave
identically in both forms, and the modifier is applied afterwards through
`cmds.select(..., add/toggle/deselect)`, which is exact for all four.
`verify_curveview.py`'s gate 29b keeps the quirk itself measured, so a
future Maya that fixes it will announce itself.

**`cutKey(clear=True)` answers 0 even when it worked**, so the status line
read "Deleted 0 key(s)" over keys it had just removed. The count is taken
before the cut.

Two harness facts, each of which cost a probe round.

**Maya's pick runs through the viewport's own DRAW pass**, so a node that
has never been drawn cannot be found: an unrefreshed locator at screen
centre picked nothing at all under every adjustment, which reads exactly
like a broken adjustment table. Trap 14's family. Real use always has a
drawn viewport; a verify run has to ask for one with `cmds.refresh()`.

**The Qt event loop does not turn while a bridge script holds the main
thread**, so the overlay window has never been exposed and `repaint()` is a
no-op — measured, `paint_count` stayed 0 while the window was up and
correct. `render()` into a `QImage` forces `paintEvent` synchronously, and
the gate then counts the non-zero bytes it left (164067 of 7874460) rather
than trusting that it ran.

One thing the plan promised and the build did not need: a `_STATE.hit`
field for the press-time classification. It is gone with the rule.

Proof: `docs/superpowers/plans/verify_curveview.py` — **green live
2026-09-05, 0 of 44 gates failed**, 1929 unit tests green.
