# The hub as a rail and one card (2026-10-16)

The animator: «адвай переосмыслим весь наш интерфейс и улучшим его. сейчас очень много где все
сливается! логические разделы не отделены визуально». Three layouts were shown as mockups
(https://claude.ai/artifact/KYPDH1djZXZS3vXeKPA9jA): A group headers, B group tabs, C a rail and one
card. The animator picked **C**. Asked: a second card at once is a **popup** (Ctrl+click or a middle
click on its rail icon); **⋮ keeps a switch back to the accordion**.

## Layout

The skin's root becomes a row:

- **The rail**, left, about 30 logical px, top down:
  - the SA mark;
  - one icon per section in `maya_hub.SECTIONS` order (not the header-only ones). Between two
    groups (Scene / Animation / Look / Settings) there is a gap and a hairline;
  - at the bottom what the header holds today: the Hotkeys switch, the edge panel's pin (shown in
    the edge panel only) and ⋮.

  The header row and its jump icons go.
- **The column**, right:
  - the hub's message line on top (as today);
  - under it ONE card filling the rest of the height, its body scrolling inside it.

  The cards live in a `QStackedWidget`: every card is built as today (control names, scriptJobs and
  every `is_open()` unchanged), one is shown.

A rail icon:
- its group's colour;
- the shown section's icon on `card_active` with a 2 px bar of the group colour at its left;
- the hover glow as every hub control;
- the tooltip is the section's label.

In the rail layout a card has no chevron and does not collapse. Its header (icon chip, title,
subtitle, the popout button) stays.

## Behaviour

- **A click** on an icon shows that card. The new card comes in 12 logical px from the side while
  fading in, `RAIL_SWITCH_MS` 160, ease-out. With ⋮ → Interface animations off it is instant.
- **Ctrl+click or a middle click** opens the section as a popup by the cursor
  (`maya_hubpop.open_at`); the shown card does not change.
- **The right button** on an icon: a menu with «Show here» / «Open as popup».
- `maya_hub.show(key)`, `focus(key)`, `expand(key)`, the radial menu's section slots (when the
  popup cannot open) and the `window.*` hotkey rows select the card.
- The shown section is remembered: `skeldarAnimHub_current`, the first section when unset or stale.
- The lit-card machinery (hover / pinned) is the accordion's: in the rail layout the one card is the
  active one.
- The collapse memory (`skeldarAnimHub_collapsed_*`) is not read or written in the rail layout. The
  accordion keeps it.

## The switch

⋮ gains **Layout ▸ Rail / Accordion** (optionVar `skeldarAnimHub_layout`, "rail" by default). A
change rebuilds the hub in place, like Classic look does. Classic look is untouched. The edge panel
builds the same skin, so it follows the setting.

## Width

The card is the dock's width less the rail. In the animator's 360 px dock that is about 32 logical
px narrower. A gate measures every card's `content.minimumSizeHint().width()` against the column in
the rail layout. A card that does not fit is fixed in its own layout. The Inventory card was tuned
to 360 px (trap 117).

## What the build changed

- No `QStackedWidget`. The cards stay in the accordion's scroll column, and `Skin.show_card` hides
  every frame but one. The glide, the light, the popups and every card builder needed nothing new.
- Measured offscreen at 150 % in a 540 px dock (360 logical): the rail is 48 physical px and the
  card's viewport 477 px (it was 510).

## Not in this spec

The inner card rules from the mockups: sections with captions, one orange button a card,
segments vs. tabs, the status plate. They come card by card after this.

## Proof

- Offscreen unit tests of the skin in the rail layout:
  - the rail's icons and group gaps;
  - a click switches the stack;
  - Ctrl+click and a middle click call the popup and keep the card;
  - the memory and its fallback;
  - `focus` / `expand` select;
  - the switch to the accordion and back;
  - every card's minimum width against the column at 150 %.
- A render script draws the hub offscreen in both layouts.
- The live hub is the animator's to try after Check update.
