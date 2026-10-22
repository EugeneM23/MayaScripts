# Floating windows: look B and the spring (2026-10-22)

The animator: «всплываюшие окна нашего плагина сейчас отрисованы не в нашем стиле и у них
анимация не плавная. Давай сделаем протатипные макеты и поработаем над плавностью». Live
mockups (https://claude.ai/artifact/Q2HzadyrH8RGqJeiot2c9k, file
`docs/superpowers/plans/window_motion_mockups.html`): three looks, four motions. They chose
**look B (the Time Bar's)** and **motion 4 (spring)**.

## What changes

Every window that runs `maya_hubwindow.Burster`: the section windows (`maya_hubpop`), the edge
rail's card (`maya_hub._rail_burst`) and the chat window.

### The look (section windows and the rail card)

- One dark surface: the frame's face `panel`, a 1 px `track_edge` outline, radius 8. No lighter
  card inside: the content stands on the panel (`WindowFrame.content_face = "panel"`).
- A `track_edge` hairline under the title row.
- The fields recessed, as the Time Bar's: line edits, drop-downs, lists, tool buttons, chips and
  check boxes on `track` with a 1 px `track_edge` edge (`maya_hubwindow.recessed_sheet(name,
  scale)`, set on the frame, scoped to it). Buttons, segments and headings keep the hub's rules.
- The chat window keeps its card (`content_face = "card"`): it paints its own pages.
- No shadow: a margin round the window would move its place, size and grips.

### The motion: a spring out of the point

- Opening: the whole window grows from `SPRING_FROM` 0.7 to 1 about the point it came from
  (pulled `ORIGIN_PAD` inside it), on a damped spring (`SPRING_ZETA` 0.72, `SPRING_HZ` 3: one
  small overshoot, the scale about 1.2 % over), settled at `SPRING_MS` 420; its opacity 0 to 1 over
  `SPRING_FADE_MS` 120.
  The drawn scale is held at 1: a window cannot paint past its own edge, and the first
  filmstrip showed the overshoot cut there; the spring lands softly instead.
- Closing: `SHUT_MS` 140, scale 1 to `SHUT_TO` 0.85 about the point, ease-in cubic, opacity to 0.
- No rows popping, no racing-edge light.
- `maya_hubburst.MOTION = "spring"` picks it; the burst stays as `"burst"`.

## Why the old one was not smooth, and what this fixes

- **The clock started before the first frame.** The first paint renders the whole window into a
  picture (`sourcePixmap`, Maya's controls included): tens of ms. The animation's time ran from
  the press, so the first visible frame was already that far in. Now the clock starts when the
  picture is taken (`PopupBurst.started`); the driver loops until the motion is done.
- **Each frame rebuilt a full-window image**: every row composited, a mask image, the light.
  The spring draws the one cached picture scaled, at an opacity: no image, no mask.
- **Each tick walked the window's rows** (`_moved`) to see whether the layout moved. The spring
  has no rows: only the size is compared.

## Proof

- `tests/test_hubburst.py`: the spring's shape (0 at start, one overshoot under 5 % of the way, 1 at the
  end), the plans' shapes and totals, the close.
- `tests/test_hubwindow.py`: the effect draws a spring frame scaled about the point, the clock
  starts at the picture, a frame plain after, the recessed sheet scoped to the frame.
- A filmstrip offscreen (`render_floating_window.py`) and a per-frame paint time.
- Not seen in a GUI Maya: the animator's to try after Check update.
