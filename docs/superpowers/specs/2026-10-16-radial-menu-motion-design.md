# The radial menu moves: out of the centre, lit under the mouse, back into the centre (2026-10-16)

The animator, reviewing the whole interface: «У кругового меню нехватает анимацией, было бы хорошо
если бы эллементы появлялись с анимацией из центра и когда я вожу по ним мышкой то подсвечивались и
увеличивались немного в размере, а когда меню закрывается то они не просто изчезали а скрывались
анимацией как бы сезжаясь в центр (обратная анимация появлению)». Shown as a live HTML demo with the
proposals for the hub (https://claude.ai/artifact/KYPDH1djZXZS3vXeKPA9jA); the animator picked hub
layout C (a rail and one card) and asked for the radial menu's motion first.

## What moves

Every number lives in `maya_radial_rules` (stdlib, pure, tested); `maya_radial.Menu` reads a clock
and paints.

- **Opening**: the ring and the centre grow from 0.2 to full over `RING_MS` (160, cubic ease-out).
  Each pill flies out of the centre to its place over `OPEN_MS` (200) with a small overshoot
  (ease-out-back), scaling from `START_SCALE` (0.3) to 1 and fading in; slot *i* starts
  `i x OPEN_STEP_MS` (18) after slot 0 - a wave clockwise from north. The menu opens where the
  cursor is, so "the cursor's direction" has nothing to give at the press; clockwise is the order.
- **Under the mouse**: the pointed pill's lift goes 0 -> 1 over `HOVER_MS` (110) and back the same
  when the mouse leaves; lit, it is `HOVER_SCALE` (1.10) times its size, a lighter face, a 2 px
  accent outline and a soft accent glow. The pointer line fades in with it. (Before: the pill turned
  solid orange at once.)
- **Chosen**: the pill turns solid accent (the old "lit" look) and flashes for `FLASH_MS` (120);
  then the menu closes and the item runs.
- **Closing**: every pill goes back into the centre, the reverse of the opening: `CLOSE_MS` (140),
  cubic ease-in, the LAST slot first, `CLOSE_STEP_MS` (12) apart; the ring and the centre shrink with
  them. Esc, the right button, a click off the slots and a release over nothing close this way too.
- While it closes the overlay is no longer filled with its alpha-1 veil, so a click goes through to
  Maya; it takes no clicks itself. A new press during a close drops the closing menu at once.
- **⋮ -> Interface animations off** (`maya_hubmotion.enabled()`): everything as before - shown at
  once, chosen runs at once, closed at once.

## Not built

The hub's layout C (a rail and one card) - its own spec next.
