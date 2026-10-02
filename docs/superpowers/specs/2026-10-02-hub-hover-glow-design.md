# The hub's controls glow under the mouse (2026-10-02)

## The ask

«Давай поработаем над красотой нашего интерфейса. Попробуй сделать так что бы все
надпись немного подсвечивались легким свечением когда мы наводим на них мышкой.
Сейчас у нас панели разделов выделяются подсветкой но все остальные эллементы нет»

A prototype (`proto_hover_glow.py`, the hub's own stylesheet at 150 %, every control
hovered at once) showed three ways; the animator chose, asked:

- **A - the glow in the text's own colour** (over a warm accent glow for everything):
  white letters glow white, Delete's pink glows pink, the orange checkbox orange, an
  icon in its own colour;
- **everything clickable** (over every text): the controls that already tick on hover
  (`maya_hubqt.sounding`) - buttons, segments, checkboxes, chips, dropdowns, the card
  headers, the header's and the strip's icons. A static label does not glow: a glow
  under the mouse means "this can be pressed".

## What it looks like

- **The ink blooms.** A control's ink - every pixel brighter than its own face by more
  than `lo` luminance (25 of 255), fully from `lo + span` (95): letters, icons, a
  checked box - is blurred (`radius` 5 logical px, three box passes ~ a Gaussian),
  scaled by `gain` (2.2), taken off the ink itself (the letters keep their crisp
  colour) and added on top (`CompositionMode_Plus`) at `strength` 0.42, each pixel in
  the colour of the ink around it. The border (L 71 on a face of L 44-54) and the hover
  fill are not ink.
- **The orange primary button has dark letters on a lit face**: nothing of it is
  brighter than its face, so it lights the way the cards do - a warm rim (`#fff1e2`,
  0.38) inside its edge, 6 logical px deep.
- **It fades**: in over 110 ms (ease-out), out over 220 ms (smoothstep), from wherever
  it stands - the card light's rhythm a little quicker, a control being smaller than a
  card. ⋮ -> Interface animations off: it switches at once. One control glows at a
  time; the hover fill, the colour change and the card light are unchanged.
- The classic hub is unchanged (as the sound is skin-only).

## How

- **`SkeldarAnim/maya_hubglow.py`** (numpy + stdlib, a payload row; a subprocess test
  pins it): `blur`, `ink(bgra, inner)` (the face = the commonest luminance INSIDE the
  control's own rect, the padding left out), `bloom(bgra, scale, inner)` and
  `rim(bgra, scale)` -> a premultiplied BGRA uint8 image at full strength, or None.
  The numbers are `maya_hubstyle.HOVER_GLOW` (data, stdlib), the timing
  `maya_hubmotion.GLOW_IN_MS` / `GLOW_OUT_MS` / `glow_ms`.
- **`maya_hubqt.HoverGlow`** (`_glow_class()`), a `QGraphicsEffect` holding `level`
  0..1 and `mode` ("ink" / "rim"). Level 0 draws the source as it is (`drawSource`);
  above it, the source pixmap (`DeviceCoordinates`, padded by the glow radius in ink
  mode), then the glow image at `level` opacity. The glow image is CACHED by the
  pixmap's bytes (crc32), so a fade only changes the opacity - numpy runs once per
  hover, again only when the control repaints differently. A numpy failure marks the
  effect broken and it draws the source from then on.
- **`maya_hubqt.Glower`**, owned by the `Skin`: the skin's application-wide watcher
  hands it every Enter and Leave (`Skin._hover_from` / `_left_from`).
  - Enter(w): the target is `w` or its nearest ancestor that `glowing()` - a
    `sounding` control, not a swatch (a colour dot has no ink), carrying no graphics
    effect of somebody else's. Its effect (created on its first hover, kept for good -
    level 0 costs nothing) fades up; whatever else is lit fades down. No target:
    everything fades down.
  - Leave(w): if `w` carries the lit effect, it fades down.
  - **It never keeps a widget.** A wrapper of a Maya-owned widget that Maya deletes
    reads freed memory (CLAUDE.md trap 135), so the Glower holds only its EFFECTS,
    found again through `widget.graphicsEffect()` while the widget is in its own
    event. An effect is ours (Python-created): when its widget dies with it, it
    answers `shiboken.isValid` False and a call raises instead of crashing - it is
    then dropped. The effects must be held: PySide deletes an effect whose wrapper is
    collected (measured 2026-10-02: no reference kept, `graphicsEffect()` None after
    `gc.collect()`).
  - One 16 ms timer on the root ticks the fades and stops when nothing moves.
    `Skin.destroy` stops it and drops the effects.

## Proof

- `tests/test_hubglow.py`: the ink (letters yes; border, face, hover fill no; dark
  letters on a lit face no), the bloom (around the letters, off their cores, in their
  colour, none without ink), the rim (inside the shape, at its edge, not deep inside),
  the blur (flat stays flat, mass kept), purity.
- `tests/test_hubqt.py` `HoverGlow`: what glows (the sounding set minus swatches and
  foreign effects), a fade up and down, one at a time, a child of the card header
  keeping the header lit, leaving onto the body, instant when switched off, a deleted
  control mid-fade, the effect painting more light around a hovered button's letters
  than the plain button, the cache.
- `docs/superpowers/plans/verify_hub_glow.py` in a disposable GUI Maya on the real hub
  with Maya's own widgets: every kind of control glows when entered and goes dark when
  left, the glow image measured on screen (brighter round the letters, the letters
  unchanged), a draw's cost, a hub rebuild mid-fade, a picture.
