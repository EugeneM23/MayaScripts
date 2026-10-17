# Time Bar: a glow flash when it comes out (2026-10-17)

The animator: «Давай при открывании таймслайдера добавим вспышку глой нарисуй тестовые макеты».
Five flashes and today's look were played live over a fake Maya window and side by side
(https://claude.ai/artifact/QpmHD9mK769aD24XsJsupw):

- A · Spark at the cursor
- B · Racing edges
- C · Wave through the buttons
- D · Rim flash
- E · Glow over the viewport

The animator picked **B**, at the mockup's Normal strength.

## What it is

When the bar comes out at the bottom edge (the burst from the cursor of 2026-10-16), the two edges
of the unrolling panel carry the light outward. Each edge is a soft vertical band of the accent,
`EDGE_GLOW` 24 logical px each side, with a hot `RIM` core of `EDGE_CORE` 3 px. The light is
brightest at the start, where both edges stand on the cursor's x, and fades as the edges slow:
`(1 - e)^0.55`, with `e` the unroll's own ease-out quint over `UNROLL_MS`. An edge that has reached
the window's end carries none. Behind them the top edge of the panel stays lit for a moment: a
1.5 px accent line and a glow `TOP_GLOW` 16 px down, fading as `(1 - age / REVEAL_MS)^1.6` over
`REVEAL_MS` 780 ms. All of it is added light (`CompositionMode_Plus`), like the key flash.

Only a reveal at the bottom edge flashes: by the mouse, by Play, by a bake, by a key set. A reveal
that is instant (Interface animations off, or `instant=True`) does not. The bar going back starts
no flash and takes a standing one away. A second reveal replaces the first's flash. The docked Time
Bar never reveals and has none.

## Where

- `maya_timebar/look.py` (stdlib):
  - `REVEAL_MS`, `EDGE_GLOW`, `EDGE_CORE`, `TOP_GLOW`, `EFFECT_MS["reveal"]`;
  - `reveal_glow(age, cx, width)` returns `(x0, x1, edges, edge, top)`. `x0, x1` are the unrolling
    span (`unroll`), `edges` the edge xs that still stand inside the window, `edge` the light they
    carry and `top` the lit top edge's.
- `maya_timebar/bar.py`:
  - `Strip.burst_at(gx, gy, opening)` adds an fx item `reveal` at the cursor's x in the strip
    (`mapFromGlobal`) when it opens with motion, and drops any `reveal` item when it folds;
  - `FxLayer` paints it (`_paint_reveal`) from its age, the host's mask clipping it to the unrolled
    span as it does everything else.

## Proof

- Unit tests:
  - `reveal_glow` at the start, mid-way and at the end, an edge at the window's end, the top's fade;
  - the strip: an opening burst adds one `reveal` at the cursor's x, an instant one or one with no
    motion adds none, a fold takes it away, a second reveal replaces it, the layer paints it and is
    done after `REVEAL_MS`.
- `docs/superpowers/plans/render_time_bar_reveal_glow.py` draws the real strip's flash at five
  moments offscreen (`time_bar_reveal_glow.png`).
- Not seen in a GUI Maya: the animator's to try after Check update.
