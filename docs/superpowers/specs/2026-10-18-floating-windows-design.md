# Floating windows in place of the viewport popups

2026-10-18. The animator: «Попапы которые живут исключительно в рамках вьюпорта нам больше не
нужны. Давай наш плагин будет теперь открывать обычные окна. Окошки которые открывает реил в них
нужно добавить кнопку закрыть (кнопка которая создавала попап теперь пускай создает плавающие
окно). Так же давай перерисуем наши окна и сделаем новые анимации в стиле таймслайдера». They also
reported a bug: «в тех окнах которые есть сейчас у нас есть какая-то мусорная полоска с левого края
и сверху. Полоска цвета опции ... она не нужна».

The live mockup is at https://claude.ai/artifact/2oSCA43qWv64YxqQmHhZhW. Of three looks and three
motions shown side by side, the animator chose:
- look **B** («Таймслайдер»);
- motion **1** («Из точки»);
- ⧉ on a rail card **takes the card into the window** («карточка уходит в окно»).

The rules for the look and motion are `docs/interface-motion.md`. This spec follows them, and its
checklist is at the end.

## What changes, in one paragraph

A section's copy (`maya_hubcopy`) now opens in a floating window. It is no longer a popup held
inside a viewport. It moves anywhere, onto another monitor too, and its place is remembered on the
screen. The window and the rail card coming out of the edge rail are drawn in look B. Both open out
of the point that was pressed and close into the point the close came from, in the Time Bar's burst:
- the shape grows from that point;
- the parts pop in, nearest first;
- the edges carry the light.

The group-colour stripe down every card's left edge and the popup's 2 px accent along its top are
removed everywhere.

## 1. The window (`maya_hubpop`, `maya_hubpop_rules`)

The module names stay: the payload, the hub, the radial menu and the install already import them.
Their docstrings say "window".

- **The same kind of window as before**: a frameless `Qt.Tool` window owned by Maya's main window.
  It stands above Maya and not above other applications, and it minimises with Maya. It is ours
  and painted, so the burst and look B can be drawn.
- **Free of the viewport.**
  - Gone: `_rect_of(panel)` as the window's bounds, the 20 Hz `follow` timer, hiding while the
    panel is not visible, and `panel` / `active_panel` choosing where it opens.
  - A drag of the title row moves the window anywhere. It is kept wholly on the screen under the
    cursor (`rules.screen_for`, `rules.clamp_origin` over that screen's available geometry), so it
    can be carried from one monitor to the next and never lost off every screen.
- **Its place** is the window's top-left in global LOGICAL px. It is kept in a NEW optionVar,
  `skeldarHubWindowPos_<key>`: the old `skeldarHubPopupPos_<key>` held an offset from a viewport
  and is not read.
  - On open, a remembered place whose title row no longer falls on any screen is dropped.
  - With no place, the window stands by the point it came from: its top-left `AT_CURSOR` (18, 14)
    logical px left of and above it, kept on that point's screen.
- **Its size**: the automatic height cap rises from 320 to **560** logical px (`MAX_HEIGHT`; a
  floating window is not squeezed into a viewport). Sizes are bounded by the window's screen less
  its margins, no longer by a viewport. Everything else stays as built on 2026-10-09: the dragged
  edges, the double click giving a side back, the roll-up to its name, and the remembered sizes
  (`SIZE_VAR`, `BAR_VAR`, `COLLAPSED_VAR`).
- **One window a section.** ⧉ on a section whose window stands raises that window and flashes it
  (the card's `pulse` light), and makes no copy. The radial menu's `open_at(key, point)` still
  closes a standing window and opens it at the cursor, unrolled: that is its own rule from
  2026-10-15.
- **Restored at Maya's start** as before (`skeldarHubPopups`). It waits only for Maya's main
  window, not for a 3D view: a window needs no viewport.
- Unchanged: the title row's drag, the light under the mouse, the closing from ✕ (deferred, trap
  135's family), the state on `sys` (trap 111), `destroy_all` / `adopt` around an install.

## 2. Look B

Drawn by the window's frame (`PopupFrame` / `_paint_outline`) and by the rail card (below).
Colours come from `maya_hubstyle.TOKENS` only.

- **The frame**: `panel` with a 1 px `track_edge` hairline, radius 8.
- **The title row**, 34 logical px:
  - the section's icon in its group colour, with no chip;
  - its name in capitals, letter-spaced, bold, `muted`, at the caption size;
  - the buttons ⌄ (roll up) and ✕ as painted pills: 24 × 22, radius 5, face `field`, a 1 px
    `track_edge`.
  - The pills move as every control of ours does: hover 110 ms +10 % with the accent glow, press
    flash 120 ms. They are painted buttons of our own (`maya_hubwindow.PillButton`, the Time Bar's
    `Pill` in miniature): the window stands outside the hub's root, where the hub's ink glow does
    not reach.
- **The content** stands on its own card: `card`, radius 6, 5 px from the frame's sides and bottom.
- **No hairline under the title**, **no accent along the top** and **no stripe**.
- **The light**: the active window glows as a lit card does (`paint_light`: `card_active` face
  under the content, 2 px `card_edge` ring, the inner glow rings), fading in 140 ms and out
  260 ms. A flash (a second ⧉) is the card's `pulse`.

## 3. The stripe and the top accent, removed

- `maya_hubqt.paint_stripe` and `CardFrame.stripe` go, so every card in the docked hub, the edge
  panel and the windows loses its left bar. Its tests (`test_hubqt`, `test_hub`) are reversed: a
  card paints no group colour.
- `PopupFrame.accent` and the 2 px fill along its top go.
- The rail icon of the section on show loses its group-colour `border-left` too
  (`Skin._current_sheet`). It is lit by the `card_active` face alone, as the mockup showed. The
  section's colour stays on its icon.

## 4. The rail card (`maya_hubedge` rail mode, `maya_hub`)

The edge rail panel (⋮ → Edge panel ▸ Left / Right, since 2026-10-17) brings a section's card out
beside the rail.

- **Its title row** has ⧉ and ✕, in look B. The docked hub (workspaceControl) keeps ⧉ alone: ✕
  there would close nothing. The skin is told it is the edge's (`Skin(..., windowed=True)`, passed
  by `maya_hub._ensure_edge`), and only then builds ✕ and the look-B card.
- **Out**: the card bursts out of the rail icon that was pressed (the origin is the icon's
  centre), by section 5's burst on the card's frame. The host's mask shows the rail at once and the
  card's shape as the burst grows it. This replaces `_rail_slide`'s frame opening from the rail
  across the width.
- **Back**:
  - ✕ folds the card into the ✕ point;
  - a click on the lit rail icon folds it into that icon;
  - then the mask returns to the rail.
- **⧉**: the card folds into the ⧉ point and, in the same moment, the section's window bursts out
  of that point. The rail goes back to rest.
- **A section whose window stands** shows a small accent dot on its rail icon (5 logical px, top
  right, a soft glow), in the edge rail and in the docked hub's rail alike (`Skin.set_floating`).
  Its card's ⧉ is lit as the popout button is today (`set_popped`).

## 5. The burst «Из точки» (`maya_hubburst`)

`maya_hubburst` already plans a card unrolling from a point and folding back into one. Its numbers
become the Time Bar's (imported from `maya_timebar.look`, never copied), and it gains the light:

| moment | rule |
|---|---|
| the shape grows | from a 28 × 20 logical box about the origin (clamped `ORIGIN_PAD` 12 inside the card) to the card, `UNROLL_MS` 288, ease_out_quint, the radius 10 → 8 |
| each part pops | `POP_OPEN_MS` 240, scale `START_SCALE` 0.3 → 1 by `back_out`, opacity ×1.6, at `burst_delay` (48 ms + 21.6 ms per 60 logical px, a vertical step 1.5): nearest first |
| the light | the shape's four edges, while each stands inside the card, carry `EDGE_GLOW` 24 / `EDGE_CORE` 3 logical px of added light, fading as (1 - ease_out_quint)^0.55; the card's top edge, once the shape reaches it, stays lit (1.5 px line + `TOP_GLOW` 16) fading as (1 - t / `REVEAL_MS` 780)^1.6 |
| each part folds | `FOLD_MS` 168 by `back_in` to 0.3, the opacity going too, at `fold_delay` over the distance from the close point (farthest first) |
| the shape closes | `CLOSE_MS` 216, ease_in_quint, onto a 24 × 18 box about the close point, `CLOSE_AFTER_MS` 72 after the last fold ends |

- `at(plan, ms)` keeps its shape and adds `light`: the shape's edges with their intensity and the
  top's.
- The Qt effect (`_burst_class`, moved from `maya_hubpop` into the shared window module below so
  the rail card uses it too) draws the light over the picture as added light
  (`CompositionMode_Plus`), clipped by the shape.
- The rows, bands, the picture taken once a burst, the effect disabled at rest and `broken` on a
  failure stay as built on 2026-10-17.
- ⋮ → Interface animations off: no effect is made, the window or card stands at once, and a close
  is at once.

## 6. The shared window module (`maya_hubwindow.py`, new, a payload row)

Qt, imported lazily through `maya_hubqt`. It holds what the floating window and the rail card
draw alike:
- the look-B frame (`WindowFrame`: face, hairline, light, the content card);
- the pill title button;
- the burst effect with its light.

`maya_hubpop` and `maya_hubqt` import it. Its numbers live in `maya_hubburst` and
`maya_timebar.look` (stdlib).

## 7. Errors

- A window or card whose burst cannot start (no picture, a raise inside the effect) opens or
  closes plain, as today's `broken` path does.
- A remembered place or size that no longer fits any screen is dropped, never applied off screen.
- No viewport is ever needed. The «no 3D view to open it in» refusal goes.

## 8. Proof

- Unit tests, pure:
  - `test_hubpop_rules`: `screen_for`, `clamp_origin` on a screen, the place by a point, a
    remembered place dropped off every screen, the 560 cap, the screen-bounded sizes;
  - `test_hubburst`: the Time Bar's numbers imported, the shape's start and end boxes, nearest
    first and farthest first, the light's edges and top fading to 0, exact at both ends, the off
    switch.
- Unit tests, offscreen Qt:
  - `test_hubpop`: a window opened with no viewport, dragged past a viewport's edge, kept on a
    screen, a second ⧉ flashing and not copying;
  - `test_hubqt`: no stripe, no top accent, the rail icon lit without a bar, the floating dot, ✕
    only on a windowed skin;
  - `test_hubedge`: the rail card's burst from the icon, ✕ and ⧉ closing into their points.
- A filmstrip, `docs/superpowers/plans/render_floating_window.py` → `floating_window.png`: the
  window and the rail card at chosen instants, look B, at 150 %.
- **Not seen in a GUI Maya** unless the animator says so: they keep the live checks (since
  2026-10-09). Shipped through push + Check update.

## Checklist (`docs/interface-motion.md` § 8)

- [x] A panel opens out of its point and closes into it: in nearest first, out farthest first.
- [x] Every part moves on its own (a wave), within the durations of section 3.
- [x] Hover 110 + 10 % + glow; press flash 120; toggle pop 200 (the pills, the segments as today).
- [x] Effects are added light, where their thing is (the edges and the top of the window itself).
- [x] The data changes at once; only the picture is animated (the controls are built before the burst).
- [x] Colours from `TOKENS` only; one orange per row; lengths × `ui`.
- [x] Numbers in a stdlib module, imported from `maya_timebar.look`.
- [x] Drawn from age; one 16 ms driver that stops at rest; the picture taken once.
- [x] Effects held and disabled at rest (trap 201, 204).
- [ ] Playback: not applicable (nothing here follows time).
- [x] Interface animations off: the same end state at once, nothing created.
- [x] A paint error prints once; no Maya wrapper kept; no `grab()` (the picture is `sourcePixmap`).
- [ ] Measured against section 5's budget: a burst's paint per tick, measured offscreen in the filmstrip script.
- [x] Unit tests + offscreen pixels + a filmstrip; «not seen in a GUI Maya».
