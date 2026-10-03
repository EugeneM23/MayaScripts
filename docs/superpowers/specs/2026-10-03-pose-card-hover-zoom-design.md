# The Pose Library's card grows twice its size under the mouse (2026-10-03)

The animator: «Давай сделаем так что бы при наведении на карточку позы в библиотеке поз наша
карточка увеличивалась в двое». Asked, all three the recommendation:

- **over its neighbours** — the grid does not move; the card grows about its own centre and,
  near an edge of the grid's viewport, is moved inside it rather than cut;
- **at once, smoothly** — it grows in ~0.14 s and shrinks in ~0.18 s; with ⋮ → Interface
  animations off (`maya_hubmotion.enabled()`) it changes at once;
- **new thumbnails at 640 px** (`capture.THUMB_SIZE` 320 → 640), so a card shown twice as
  large is sharp; cards saved before keep their 320 px picture (Replace thumbnail re-takes it).

## What is drawn

The whole card is twice as large: the square, its thumbnail, the name strip, the character chip,
the corner radius and the outline. It keeps the look it has unzoomed (`hover` face, `text2`
outline; the picked card `card_active` and the `accent` outline) and gains a soft drop shadow,
so it reads as lifted above the grid. The thumbnail is drawn from a square cached at twice the
card's side (`fit` keeps that size in the cache), so a 640 px picture stays crisp.

## Where (pure, `look.zoom_rect`)

The card's tile (square + name strip) grows `ZOOM` (2) times about the tile's centre, then is
moved inside the viewport's visible part of the canvas less `ZOOM_MARGIN` (6 logical px) on each
side. When the viewport cannot hold a twice-as-large card, the factor shrinks to what fits (never
below 1). Because the grown tile always contains the card's own tile when it fits, the mouse —
which is on the card's own tile when the zoom starts — is always on the grown card.

The animation interpolates the tile from the card's own place to that target with
`maya_hubmotion.ease`; the target is computed at paint time from the viewport as it stands, so a
scroll or a resize mid-zoom needs no bookkeeping.

## Which card, and the mouse

- What you see is what you press: `index_at` asks the hovered card's CURRENT grown tile first,
  then the grid. A click, a double-click, a drag, a middle-drag blend and the right button act on
  the grown card even where it covers a neighbour.
- The grown card holds the hover while the mouse is inside it; leaving it (onto a neighbour's
  uncovered part, a gap, out of the canvas) shrinks it and lets the card under the mouse grow.
- Several cards can be shrinking at once; the one growing is drawn on top of them, they on top
  of the grid.
- A left drag starting shrinks the card (the ghost takes over); a middle-drag blend keeps it
  grown. A scroll re-reads the card under the cursor.
- A library re-read (`set_cards`) keeps the hover on the same card by path, drops the zoom state
  of cards no longer listed.

## Cost

One 16 ms `QTimer` on the canvas runs only while a card is growing or shrinking. Each tick
repaints only the union of the moving cards' old and new tiles (with their shadow), so the grid's
culled paint draws the few cards under them.

## Tests

`test_poselib_look`: `zoom_rect` (centred, moved inside each edge, the factor shrinking to fit,
never below 1, containing the card's tile), `zoom_at` (the interpolation's ends and middle).
`test_poselib_cardgrid`: hovering grows the card to `ZOOM` and back (animations off: at once; on:
through the timer), the grown card drawn over its neighbour in a render, a click on the part of
the grown card covering a neighbour picks the grown card, leaving the canvas shrinks it, a drag
shrinks it, a re-read keeps the hover by path, the 2x picture cached. `test_poselib_scene`:
`THUMB_SIZE` is 640. A disposable GUI Maya: the window on a library of cards, a real hover, the
picture photographed.
