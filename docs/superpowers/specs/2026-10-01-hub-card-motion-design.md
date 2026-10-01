# The hub's cards slide open and closed, the jump scroll glides (2026-10-01)

The animator: «А элементы нашего интерфейса возможно открывать закрывать с какими-то анимациями, просто
для красоты и приятности?» Offered three scopes — cards and scroll; plus the light and the message line;
plus the grids — they chose **cards and scroll** (the recommended one).

## What changes, as the animator sees it

- **A card's header click**: the body slides open from the header down (height 0 → its own height) or
  slides shut, the chevron turning 0° → 90° with it. Ease-out (cubic): fast start, soft landing.
- **A jump from the icon strip** (exclusive, `maya_hub.focus`): every other open card slides shut, the
  chosen one slides open, and the scroll GLIDES to put it at the top instead of jumping there.
- **Every other opening by code** (`show(key)` from a tool's `show_window`, a hotkey row, the update
  chip): the same slide and glide (`expand`).
- **⋮ → Interface animations**: a checkable row beside Interface sounds; off = everything instant, as
  before. Remembered in the optionVar `skeldarAnimHub_animations`, default ON.
- **The classic hub is untouched**: its frameLayouts collapse the way Maya collapses them.

Not animated (asked and set aside): the card light, the header's message line, the portrait grid and the
inventory, the hub's own window (Maya's workspaceControl). No opacity fades: a QGraphicsOpacityEffect
renders Maya's controls into a pixmap on every frame, the family of trap 134.

## Measured first (a disposable Maya, port 7016, the repo's hub, all eleven cards)

- **A hidden body's size hint is wrong**: Weapons 537 against 657 settled, Characters 763 against 420 —
  a hidden body was never laid out (the 2026-09-28 note). Shown at `maximumHeight 0` first, the layout's
  `heightForWidth(header width)` (or its size hint) matches the settled height on ten of eleven cards; the
  Characters card read 422 against 420 (its portrait grid's Keeper settles a frame later).
- **A frame costs 2.5 ms** for one card's height step (the whole column re-laid out), **3.6 ms** with ten
  cards closing at once and one open. 60 fps fits.

## How it works

**The clip** (`maya_hubqt.Card`): no new widget. The body stays the widget the builders' controls live
in (`body_layout` and its path unchanged). For the length of a slide:

1. `body_layout.setEnabled(False)` — the body's own children keep the geometry they were given, so a
   short body CLIPS them (Qt clips children to their parent) instead of squeezing them to their minimums
   (which is what a plain height animation of a laid-out widget does);
2. the children are laid out once at the FULL height (`body_layout.setGeometry(0, 0, width, natural)`),
   on opening after the body is shown at `maximumHeight 0`;
3. `body.setMaximumHeight(h)` per tick — the card's column gives the body h;
4. at the end: hidden if closed, `maximumHeight` back to Qt's maximum, the layout enabled and activated —
   the idle card is exactly what it was before this feature.

**The target follows the content** (the 2 px of Characters): every tick re-reads `natural`; when it
changed, the children are laid out at the new height and the slide aims at it. An opening slide therefore
ends at the settled height, with no jump.

**The gap moves into the body**: the card's column spacing between header and body (6 logical px) becomes
the body layout's top margin. Same geometry when idle; while sliding, the gap opens and closes with the
body instead of appearing at the first frame and vanishing at the last.

**Interrupted**: a click (or a jump) during a slide reverses it from where it stands; `collapsed()`
answers the new state at once, as now.

**Instant when it should be**: a card built (the hub's own build), a card whose frame is not visible (a
hub docked in a hidden tab), or animations switched off — the old `setVisible`. `set_collapsed(c)` keeps
its meaning; `set_collapsed(c, animate=True)` is the user's move (`toggle`, `maya_hub.focus` / `expand`).

**The glide** (`Skin.scroll_to(key, animate=True)`): a single animation 0 → 1 over `SCROLL_MS`, eased;
each tick activates the column's layout and puts the bar at `start + (card.frame.y() - start) · e`. The
target is read LIVE, so cards still sliding shut above the chosen one move it and the glide follows; it
lands on the card's final place at the end, and one settle step after the scroll area's own update puts it
there exactly. The wheel or the scrollbar (`actionTriggered`, `sliderPressed`) stops it: the animator's
own scroll wins.

**Durations** (`maya_hubmotion`, stdlib, pure): by the distance in logical px,
`clamp(140 + 0.12·d, 160, 260)` ms (a 100 px body 160, Characters' 280 logical 174, UE Bridge's 540
logical 205); the glide 260 ms; the chevron rides the body's progress.

## Units

| module | does | imports |
|---|---|---|
| `maya_hubmotion.py` (new, payload row) | `OPTIONVAR`, `enabled()` / `set_enabled(on)` (a `_cmds()` seam), `ease(t)`, `duration(distance, scale)`, `SCROLL_MS`, `lerp`, `angle_for(progress, opening)` | stdlib only (a subprocess test) |
| `maya_hubqt.py` | `Card` (`motion` callable, `set_collapsed(c, animate=False)`, `_slide`, `_tick`, `_settle`, `natural_height`, the rotated chevron), `Skin.animations`, `Skin.scroll_to(key, animate=False)`, the menu row, `Skin.paint_animations(on)` | Qt, `maya_hubmotion` |
| `maya_hub.py` | `_callbacks()["animations"]`, `set_animations(on)`, `_dress_animations(skin)`, `focus`/`expand`/`scroll_to` passing `animate=True` | — |

## Addendum: what the live run changed (the same day)

- **The glide WAITS for the other cards** (`Skin._glide_when_settled`, at most `GLIDE_WAIT_S` 0.6 s),
  then eases toward `min(card.frame.y(), bar.maximum())`, both read live. Aimed while three cards shut
  above Studio, the first build's glide climbed toward Studio's place while the scroll's range shrank
  under it and was pulled back by the clamp (it ended on the range's 207 after passing it): not monotonic.
  A jump is now a fold, then a glide. With nothing left for it to outlast, `SCROLL_MS` is 240 (was 300).
- **"Clipped, never squeezed" is measured as: every turn the content stands at its FULL height** (the
  body's top margin above it) while the body shows less. The full height itself may move a few px mid-
  slide: when the hub's scroll bar comes, the Characters grid reflows to the narrower width (3 px live).
  The same happens without the animation, at once.
- **The header is `Fixed` vertically, and every tick lays the card and the column out at once**
  (`Card._lay_out_now`). The animator, clicking headers in the disposable Maya: «название заголовка
  "дрожит" во время анимации». Measured: shutting, the header read 33 → 34, 36 … 350 px and back; opening,
  17 for a turn — left to Qt's posted LayoutRequests the card's own column ran first, on the card's OLD
  height, and the difference went to the header (Preferred), where the title and the chevron are centred.
  After: 33 on every turn of every card, the title's place unchanged to the pixel.
- A disposable Maya's hub opens DOCKED; the first runs shrank the main window by mistake (a 127 px
  viewport). The verify floats it and sizes it to the animator's dock (viewport 510 physical).

## Proof

- Unit tests (offscreen Qt): the pure module; a slide driven to its end by the animation's own clock
  (`setCurrentTime`) — open ends visible at its natural height with the layout enabled and the maximum
  restored, close ends hidden; a child's height never changes during a slide (clipped, not squeezed); a
  reversal; off / invisible / build → instant; the chevron's angle mid-way; the glide landing on
  `frame.y()` and stopping on a user action; the menu row; `maya_hub` wiring.
- `docs/superpowers/plans/verify_hub_motion.py`, live in a disposable Maya on the repo's hub: every card
  opened and closed through real time (the event loop turned in the send), per tick the body's height and
  one child's geometry recorded — monotonic, clipped not squeezed, the last tick on the settled height to
  0 px, the frame cost; a jump: the others shut, the chosen one open, the glide monotonic and on the
  card's top at the end; off = instant; the photographs of a slide mid-way.
