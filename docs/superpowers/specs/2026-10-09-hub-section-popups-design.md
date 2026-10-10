# Hub section popups: a copy of a section in the viewport (2026-10-09)

The animator: «для каждого из наших разделов сделать кнопочку прямо на разделе перед
стрелочкой раскрытия. Эта кнопочка должна создавать попап кнопку прямо в камере ...
открывать и копию нашего раздела только в окне вьюпорта. У окна есть опция закрыться.
Окно небольшого размера как наша вкладка ... перетаскивать эти попапы в пределах
рабочего окна и что бы они всегда следовали за окном».

Decisions taken with the animator (2026-10-09):

1. **B - a true copy.** A popup is a second, independent build of the section: its own
   controls, its own status line, its own callbacks. The hub's card keeps its own.
2. **The popup opens in the ACTIVE viewport** (the focused model panel at the press; the
   first visible one when none has focus). It stays in that panel.
3. **Remembered.** The popups open at the press are open again after a restart, at the
   same place in their viewport.
4. **The icon** sits on each card's header, before the chevron.

## What a popup is

- A frameless `Qt.Tool` window owned by Maya's main window (the edge panel's pattern,
  `maya_hubedge`): above Maya, never above another application, gone with Maya when minimised.
- Inside: a card-like frame (the group's stripe, the hub's stylesheet), a title row (the
  section's icon and name, the subtitle the section marks, a close `x`) and a scroll area
  holding the section's controls.
- Its width is the hub's dock width (360 logical px, never less than the section needs);
  its height is the section's natural height, capped at the viewport's height less a margin.
- Dragged by its title row. The drag is clamped to the viewport's GL rectangle, so the
  popup cannot be carried onto another monitor. Its place is stored as an offset from the
  viewport's top-left, in logical px, so it moves with the viewport.
- A 20 Hz timer follows the viewport: when Maya's window is moved or docked elsewhere, the
  popup moves with it. When its panel is hidden (a layout change, Maya minimised) it hides,
  and shows again with the panel.
- Close (`x`) destroys the copy and forgets the popup. An install or an update destroys the
  open popups without forgetting them (`destroy_all`), and the next startup reopens them.

## How a copy is made (maya_hubcopy)

`cmds` has one name per control per session, and every section builds its controls under
constant names that its callbacks name again. So a copy is built and run inside a scope:

- `maya.cmds` is wrapped once (`install`). While no scope is entered each wrapper is a
  pass-through, so the hub behaves exactly as before.
- Inside a scope a creation (`CREATORS`, no q/e flag) gets its first name prefixed with the
  scope's tag, and the name Maya made is recorded under the name the module knows it by.
- Any other call maps the names it carries through the scope's record. A name the scope did
  not make passes through - a copy can still reach a hub control, as a hub callback could.
- A callable handed to a command is wrapped so it runs in the scope that made it, whenever it
  fires. A Python callback handed to a Qt object of ours goes through `wrap()` at the point
  it is handed over.
- A scriptJob made in a scope is recorded there and killed when the copy closes.
- Qt lookups by name (`maya_hubqt.find`) go through `resolve()`.

Section modules keep their constants. Their changes are the exceptions the mechanism cannot
see: state keyed by a control name (keyed by the resolved name instead), fixed Qt object
names (made per copy), events that do not come through a command (a thread's refresh, a
listener - they refresh every copy, `instances(section)`), and writes to controls the copy
did not make (guarded, they may be the hub's or gone).

## The header button

`Card` gets a `picture-in-picture` icon button before the chevron (Tabler's outline icon, the
same MIT set as the rest, copied verbatim). A click opens the popup, or closes it when it is
open; the button is lit while its popup stands. Classic hub: no button (the classic hub has
no header to put it in).

## Sections

Every card section gets the button, except the header-only Hotkeys (its keyboard button is
the header's). Pose Library's card is one line: its popup holds the same line.

## Non-goals (stated, not built)

- A popup does not keep its typed-but-unapplied values when it closes: each open is a fresh
  copy. The scene's state is always the scene's.
- No hover glow or hover sounds in a popup (the hub skin's watcher is the hub's).
- One viewport per popup: a popup does not follow the focus to another viewport.
- No resize grip; the height follows the section.

## Proof

Unit tests (stdlib, fake `cmds`) for the scope rules, the placement rules and the
persistence; offscreen Qt tests for the popup window and the header button; mayapy
standalone for the wrapper; and a live run in the animator's Maya on its command port: every
section's popup opened, its controls named by its copy, a press in the copy writing the
copy's line and not the hub's, the hub unchanged, the drag clamped, the follow with Maya's
window moved, close and reopen, the remembered set after a restart.

## Addendum 2026-10-09 - built, measured, and the animator's second round

Built: the scope mechanism (`maya_hubcopy`), the placement rules (`maya_hubpop_rules`), the
popup window (`maya_hubpop`), the card's popout button (`maya_hubqt.Card`), the hub wiring
(`maya_hub`: the callback, the lit button, `adopt` at build() AND at start() - in edge mode
the startup call builds the panel, not build()), `install.py` (the three new modules in the
payload; the open popups destroyed before the purge and remembered), `over_hub` (a drop over
a popup counts as the hub), `hubstyle.tell` (a copy's status is not the hub's line).

Measured live on 2026-10-09 in the animator's Maya, through the command port, with the repo's
code loaded in place of the installed copy (nothing copied to Documents):
- Colour's popup opened by its card button; its palette press changed the copy's line and not
  the hub's; the card button lit.
- Drag with real Qt mouse events: clamped to the viewport at the left-bottom and the right-top;
  inside, under the pointer; the offset saved in logical px.
- Follow: the window moved (rect 4,288 -> 204,374) and the popup moved with it (48,334 ->
  248,420), exactly its stored offset.
- A sweep of every card section: each popup built with no error line and closed.
- Found and fixed live: a copy overwrote the hub's inventory panel (a registry keyed by the base
  control name). Rule: a module registry of a control is keyed by `maya_hubcopy.resolve(name)`.

The animator's second round (2026-10-09, «давай сделаем так что бы у виджетов было минимум
лишнего места ... улучшим визуал рамки ... кнопку ... свернутый минимальный вид где будет
только его название и по нажатию виджет развернется в полный размер»):
- Minimal space: a popup is the section's own size - its width between WIDTH_MIN (260) and WIDTH
  (360) logical px, never narrower than the section's minimum; its height the title row plus the
  section's natural height, nothing more; the margins 4/3/4/4. A taller section scrolls, its
  scroll bar takes width. (`maya_hubpop_rules.popup_size`.)
- Frame: a 1 px outline in the hub's line colour, rounded like the card, a 2 px accent along the
  top in the section's group colour, a hairline under the title row. Painted, not a stylesheet
  border, so no layout space goes to it (`maya_hubpop._popup_frame_class`).
- Roll up: a chevron in the title row (down while open, right while rolled up) and a click on the
  name (a press and release without a drag past Qt's drag distance) roll the popup to its title
  row alone; the section's controls are hidden, not destroyed. Unroll is the same click. The
  roll is remembered per section (`skeldarHubPopupCollapsed_<key>`, "1"/"0"), so it comes back
  rolled after a restart; the window keeps its place, clamped into the viewport.

Not built, stated: an animated slide of the roll (it is instant - the hub's cards slide, the
popups do not yet); a resize grip; a popup's own hover glow and sounds.

## Addendum 2026-10-09 (second pass) - copy-safety of the sections, and the final shape

The four section agents of the first round failed on connection errors, and the retried ones
changed no file. The lead did the copy-safety pass itself. What is in the code now, per H-number
(the brief's hazards H1-H7):

- Scope helper `maya_hubcopy.bind(obj)`: an object whose methods run in the current scope (H3).
  A Qt event calls the scene of a grid, a list drag or an inventory panel; `bind` puts those calls
  in the copy that laid them. A closed copy runs nothing.
- H1 (registries keyed by the base name): `maya_inventory._PANELS`, `maya_armorgrid._GRIDS`,
  `maya_chargrid._GRIDS` and `maya_uebridge.listdrag._DRAGS` are keyed by the scope-resolved name.
  The list drag's `attach` looked up its list by the base name, bypassing the mapping: fixed.
  `maya_hubqt.list_widget` resolves its name too.
- H2 (fixed Qt object names): the grids' and the fire overlay's names carry the copy's tag.
- H4 (refresh from threads and timers): `maya_share` and `maya_stash` keep each card's row cache
  (`_view()`, per scope tag) and refresh every card (`each_card`); the Studio's status line is
  written to every card; the Graph Overlay's button and line too (`_each_card`).
- H6 (jobs and engines that a copy must not take with it):
  `maya_com` engine and tool start their scene jobs in the ROOT scope (they are the scene's, not
  a card's); the refresh job of the Center of Mass panel is kept per card (`JOB` by scope tag, it
  was one list that a copy's start killed). Graph Overlay's scene jobs are root-scoped too.
  Shared's subscriber and Stash's folder timer are started by the hub only; a copy starts one
  only when none stands.
- H3 (Update): the press from a popup is deferred (an install destroys the open popups, the
  pressing one included), and the hub's rebuild runs in the hub's own names.

Verified on the animator's Maya (command port), 2026-10-09: every card section's popup built and
closed with no error line; the Colour press changed the copy's line only; the Weapons registry
holds the hub's panel while a copy opens and closes (`hub_entry_untouched`); the Shared copy lists the
same 7 rows as the hub; the popup phases A-D: 25 of 25 gates, and phase E: the popup followed its
viewport when Maya's window moved (1738,313 = expected).

Not verified live (built and unit-tested only): the Animation Setup's portrait clicks and bridge
Import in the copy; Center of Mass, Stash, Graph Overlay and Studio presses in the copy; the Update
press from a popup (it would download and install - not pressed on purpose).

The popup's final shape (2026-10-09): the dock width (360 logical) unless the section's own minimum
is wider (a narrower window clipped the Colour row - measured and changed back); the height the
title row plus the section's natural height (Colour 155 = 38 + 117, exact); rolled up the title row
alone (38); the window's minimum height cleared before a resize (a roll-up measured in the same send
kept the expanded minimum: the layout updates its minimum when Maya's event loop runs); a popup opened
by its button comes back at its remembered place (the last drag), not the default cascade.

## Addendum 2026-10-09 (third pass) - the animator's review of the popup

The animator looked at the popup in the live Maya and asked for four things: shorter popups (the
rolled-up state, and the expanded height), no black square behind the rounded corners, a smooth open
and close, and the card's light on hover. What changed (maya_hubpop, maya_hubpop_rules, maya_hubmotion):

- See-through window (`WA_TranslucentBackground`). The black square was the palette's background of
  the root: the root is a plain QWidget, whose stylesheet background is not drawn, so it showed round
  the frame's rounded corners. The scroll area's viewport painted the palette too
  (`setAutoFillBackground(False)`). Now the card's face and its outline are the only paint.
- Shorter: the title row is 16 px (was 18), the frame's margins 3/2/3/2 (were 4/3/4/4). Rolled up, the
  popup is the name alone - 20 logical px at a scale of 1.0 (it was 25).
- An expanded popup is at most `rules.MAX_HEIGHT` tall (320 logical px, the title included). A taller
  section scrolls inside the popup, its scroll bar taking the 12 px the dock has to spare
  (`popup_size`'s cap, measured: 480 physical px at 1.5 with the scroll bar shown).
- The popup's scroll area has its own object name (`skeldarAnimPopupScroll_<tag>`), not the hub's.
- Open: fades in and rises 10 logical px over `hubmotion.POPUP_OPEN_MS` (220 ms, ease-out). Close:
  fades out over `POPUP_CLOSE_MS` (170 ms, ease-in-out); the popup is gone from the hub's list and its
  card button goes dark at once, and its controls take no press while it fades. A drag started during
  an opening takes the window at once.
- Roll-up and unroll slide the window's height like a card's slide (`hubmotion.duration`); the scroll
  area is shown while it opens and hidden once it has shut. The animations are parentless and stopped
  by `Popup.destroy()` (a window deleted under a running animation must not be its parent).
- Hover: the popup window's Enter and Leave light it the way a card is lit - the card_active face, the
  orange ring and the inner glow, fading in over `light_ms` (140 ms) and out (260 ms). The grey outline
  fades under the ring. Hover only: a popup is not kept lit after the mouse leaves; the hub's cards keep
  their last-active light, and a popup does not take part in that rule.

Decided alone, for the animator to check: the cap of 320 logical px; the timings above; the slide of
10 px; the light on hover only. Verified: the popup, rules and motion unit tests (48, 31, 17) and the
hub modules around them green; a headless render of the frame over a viewport-like grey (the corner's
alpha 0, the collapsed strip 30 physical px at 1.5, the capped window with its scroll bar, the lit ring
in the card's orange). Not verified: the feel of the animations and the look in the animator's own Maya
(the modules there are the previous build until they are reloaded or installed).

## Addendum 2026-10-09 (fourth pass) - the rolled-up popup, and resizing it

The animator: «Окно попапа когда он свернутый очень длинное нужно или делать его максимально
коротким или добавить возможность изменять размер перетягивая за край. А лучше и то и то.» Both built.

- A rolled-up popup is as wide as its name. `popup_size(..., collapsed=True, title_w=...)` takes the
  title row's own width with the frame's side margins (`Popup._title_width`), and its height stays the
  title row's (20 logical px at a scale of 1.0). It was the dock's 360 px wide, with the name at the left.
- The edges drag to resize (`maya_hubpop._grip_class`, `Popup._grip_drag`): thin strips above the frame,
  `rules.GRIP_W` = 5 logical px. The right edge sets the width, the bottom edge the height, the corner
  both. A rolled-up popup has the right strip only, so only its width moves. A double click on a strip
  gives that side back to automatic.
- The bounds of a drag (`rules.bounds`): unrolled, the width from the largest of 160 logical px, the
  section's minimum plus a scroll bar, and the name, up to the viewport less its margin; the height from
  40 logical px. The far edges cannot be carried out of the viewport: the cap is measured from the
  window's top-left at the press. A dragged height may pass `MAX_HEIGHT` - the animator chose it.
- Sizes are remembered per section, as the position is: `skeldarHubPopupSize_<key>` ("w,h" logical, "-"
  for automatic) for the unrolled popup, `skeldarHubPopupBar_<key>` ("w" logical, "-" for fits the name)
  for the rolled-up one. A restart or a hub rebuild opens each popup at its size.
- The width slides with the height when a popup rolls up or down (a roll-up narrows it to the name).

Decided alone, for the animator to check: the strips are 5 logical px wide; a drag cannot widen the
popup past the viewport's edge (it does not move the window to make room); a rolled-up bar cannot be
narrower than its name. Verified: the popup rules and popup unit tests green; a headless render - the
rolled-up bar at the width of its name (240 physical px at 1.5 in the test font), and a popup dragged to
300 x 200 logical px with its content reflowed and a scroll bar. Not verified in the animator's Maya: the
edge cursors and a drag with a real mouse.
