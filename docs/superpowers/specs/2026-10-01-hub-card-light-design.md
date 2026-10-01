# The hub's card light: a glow that fades in and out, a flash when chosen (2026-10-01)

The animator, after the slides: «Теперь давай сделаем красивый глоу и анимацию подсветки при выделении
карточки или наведении на раздел. Сделай все сам я отойду на часик.» Every choice below was taken alone
(the animator away); each says why.

## What the animator sees

- **The lit card glows**: its face takes the lighter `card_active`, its edge the accent ring (2 px, as
  before), and a warm INNER glow runs along the inside of the edge, strongest at the ring and fading out
  over about 10 logical px. Lit = the card under the mouse, else the card worked in while it is open
  (the rule of 2026-09-28, unchanged).
- **It fades**: lighting up takes `LIGHT_IN_MS` 140 (ease-out: quick to answer the mouse), going dark
  `LIGHT_OUT_MS` 260 (ease-in-out: a soft trail as the mouse moves on). Moving from card to card cross-fades
  them. A fade turned back mid-way continues from where it stands.
- **Choosing a card flashes it**: when the card worked in CHANGES (a press or focus inside another card,
  a jump from the strip, `show(key)`), the ring brightens toward `accent_text` and the glow widens for a
  moment (`FLASH_MS` 480: a fast rise, a slow fall). Clicking around inside the card already chosen does
  not flash again — every button press would.
- **⋮ → Interface animations off**: the light switches at once and never flashes. The look stays.

Not done, and why: an OUTER glow (a halo around the card) — the cards stand against the scroll area's left
edge (column margin 0), so a halo would be cut on one side; making room narrows every card by its width,
and the Weapons card is already tuned to the 360 px dock (trap 117). A `QGraphicsDropShadowEffect` would
also render the whole card offscreen on every repaint of anything inside it (trap 134's family).

## Measured first

A full repaint of a card (all its Maya controls) costs 1.5 ms median, 3.0 p95 for UE Bridge (881 px, a
list), 0.5 for Retarget, ~0 for cards scrolled out of view (a disposable Maya at 150 %, the hub floated to
the dock's 510 px viewport). So the light repaints the whole card each tick: the face's tint can fade too.

## How

- `maya_hubqt` builds each card's frame as a `CardFrame` (a QFrame subclass, so `QFrame[skCard]` still
  styles its base face) holding `level` (0..1) and `flash` (0..1); its `paintEvent` draws the stylesheet's
  face first, then `paint_light`: the tint (card_active at alpha `level`), the glow rings, the ring.
- The stylesheet's `[skActive="true"]` rule is gone (it switched the look at once); the property is still
  set on the lit card (what the lit card IS, for tests and verifies), and no repolish is needed.
- `Card.set_lit(on, animate)` animates `level` (QVariantAnimation 0..1 driving a lerp from where it stood);
  `Card.pulse(animate)` runs `flash` through `maya_hubmotion.flash_at(t)`. `Skin._light` calls `set_lit`
  on the old and the new card; `Skin.set_active` pulses when the pinned card changes.
- The shape is data in `maya_hubstyle` (stdlib): `GLOW` (steps, step width, alphas) and
  `glow_rings(level, flash) -> [(inset_logical, width_logical, alpha)]`, `mix(a, b, k)` for the ring's
  colour; the timing in `maya_hubmotion`: `LIGHT_IN_MS`, `LIGHT_OUT_MS`, `FLASH_MS`, `flash_at`,
  `smooth` (ease-in-out).

## Proof

- Unit tests: the pure shapes and timings; a hover fades the new card up and the old down (driven by the
  animations' own clocks), `skActive` follows at once; a pin change flashes, the same pin does not; off =
  instant, no flash; the painted pixels — at level 1 the ring is `card_edge` and the face `card_active`,
  at level 0 both are the plain card.
- `docs/superpowers/plans/verify_hub_light.py` in a disposable Maya on the repo's hub: real-time fades
  monotonic in and out, the cross-fade, the flash only on a change, the cost of a turn while lighting, the
  pixels of a lit and a plain card grabbed from the screen, photographs (plain, half lit, lit, flash).
