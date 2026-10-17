# A section popup bursts out of the point it was called from (2026-10-17)

The animator (2026-10-16): «Давай сделаем так что бы наши поапы появлялись с приятной анимацией сделай
мекеты для примера появления». Five live mockups were published
(https://claude.ai/artifact/AQZc8xz9Bys9kXzXiFgZ2z): A the current fade and 10 px rise, B a lift with a
flash, C an unroll from the title, D from the point, E a zoom. The animator chose **D, «из точки»**.

## What it does

- **Opening**: the card's rounded shape unrolls from the point the popup was called from. That is the
  cursor for the radial menu and the rail's Ctrl / middle click, and the hub card's popout button for
  the popout. A point outside the card is pulled inside it, 12 logical px in from the edge. The shape
  goes from a 28 x 20 logical box with radius 10 to the whole card with radius 8 over 300 ms (ease-out
  quint), the card's face fading in over the first 60 ms. Inside it the title row and each row of the
  section pop in nearest first: a row starts `40 + 22 x d / 60` ms after the press (d its centre's
  logical distance from the point), fades in over 140 ms and grows from 0.82 to 1 over 240 ms with the
  radial menu's back ease (k 1.6), pivoting on its own point nearest the origin.
- **Closing**: the rows fold toward the point the close came from, the farthest first (`22 x (dmax - d)
  / 60` ms apart, 130 ms each, fading out and shrinking to 0.86), then the shape closes onto the point
  over 200 ms (ease-in cubic), starting 60 ms before the last row has gone. The face fades out over the
  last 80 ms. The point is the cursor when the close is pressed: the ✕ under it, or the hub card's button.
- The radial menu and the bottom-edge Time Bar move this way: everything that pops up in the plugin
  now moves alike.
- Interface animations off (⋮): at once, as now. The restore at startup: at once, as now.
- While it moves the window takes no clicks (it is under half a second). The card light freezes: a
  popup opened under the mouse lights up once it stands.

## How (Qt)

The popup window is a frameless translucent `Qt.Tool`; its card is `PopupFrame` (a `CardFrame`).

- **One `QGraphicsEffect` on the frame** (`PopupBurst`), disabled at rest, so the popup paints as
  today (trap 204).
- While a burst runs it takes the frame's picture once (`sourcePixmap`, device coordinates, no pad)
  and draws it per tick into an image:
  - the whole picture first;
  - each row's rectangle filled with the card's face (card blended to card_active by the frame's
    light level);
  - each row's piece of the picture drawn back at its opacity and scale;
  - the image masked by the antialiased rounded shape (a mask image, `DestinationIn`);
  - the image drawn at the face's opacity.
- Maya's controls are never touched. Their text is grayscale-antialiased only while the picture is
  drawn (trap 202).
- The window keeps opacity 1 and its full size throughout.
- **The rows** are found when the effect draws first, when the window is laid out:
  - the title row, plus the scroll content split into rows by a pure walk;
  - a widget taller than 64 logical px is split into its visible child widgets, to depth 8;
  - each row is clipped to the scroll viewport;
  - past 48 the rows are merged into bands.
- **The driver** is a parentless `QVariantAnimation` over `MAX_MS` (1200), polling the effect. The
  plan's total ends it, and so does the animation's end (a window never drawn).
- A burst that fails (no Qt effect, an exception at its start) falls back to today's fade. An effect
  that raises while drawing marks itself `broken` and draws the frame plainly from then on.
- **Origins**:
  - `open_at(key, point)` passes the point;
  - `open_popup` / `toggle` take the cursor when none is given;
  - `close_popup(animate=True)` and the ✕ (`_defer_close`, which reads the cursor at the press) pass
    theirs.
  - `open_at` still destroys a popup already open at once before it opens the new one: two scopes of
    one section must not overlap (a copy's registries are keyed by the base name).

## Units

- `SkeldarAnim/maya_hubburst.py` (stdlib, pure, a payload row): the constants, `plan_open`,
  `plan_close`, `at(plan, ms)`, `rows(...)`, `bands`, `blend`, `clamp_origin`. Physical px in, with
  `scale` for the logical distances.
- `maya_hubpop`: `_burst_class()`, and `Popup._burst` / `_end_burst` / `_burst_plan` / `_burst_parts`.
  `show_open` and `fade_out` start the burst; `close_popup` and `_defer_close` hand it the origin.

## Proof

- Unit tests: `tests/test_hubburst.py` (the plan's geometry and timing, rows, bands) and
  `tests/test_hubpop.py`'s `Burst` class (offscreen: the shape small at the start and whole at the
  end, the effect off at rest, a close leaving the list at once and destroying the window).
- Further offscreen tests: a broken effect falling back, animations off, and the origins of open_at,
  toggle and the ✕.
- `docs/superpowers/plans/render_popup_burst.py` draws a filmstrip of a real popup's frame through the
  effect, offscreen.
- Not seen in a GUI Maya: the animator's to try after Check update.
