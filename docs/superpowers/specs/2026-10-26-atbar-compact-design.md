# AT bar: Full / Compact / Off (2026-10-26)

The animator, with a screenshot of the F row: «Щоб була кнопка на таку розкладку повну як от зараз, а
друга кнопка виводила на більш компактну версію АТ, де оці всі фічі будуть умовно викатуватися з 1
загальної кнопки Blend, а все інше компактно потрібно розмістити десь отут» (the free room at the right
of the F row). Why: two animators - one keeps everything open, the other has a small screen and wants
the most viewport.

## What

- ⋮ -> Time bar ▸ **AT bar** is a submenu of three exclusive rows: **Full / Compact / Off** («Time Bar -
  AT bar - 2 варіанта розкладки», Off kept «щоб AT можна було вимкнути зовсім»). Remembered per user
  (optionVars `skeldarATBar` on/off, as before, and `skeldarATBarLayout` full/compact).
- **Full**: the bar as it is - its own row on top of the Time Bar.
- **Compact**: no row of its own. Inside the Time Bar's F row (`maya_skillbar.grid.PageTabs`), right
  after the status-line tools: `[BLEND]` then KEYS, POSE, SPACE, TIME, TOOLS in one line - the same
  buttons, menus and toggles, smaller (an 18 px face for the row's 22 px), no captions, the groups apart
  by space alone, each in its group colour.
- **Blend** is one chip; a click opens a panel ABOVE the row with the four tracks (SM / TW / BD / BN) as
  in Full. A click outside or Esc closes it.
- The F tabs fold to keys first when the row is narrow (they already did for the status tools): the
  compact bar is room the tabs leave free (`PageTabs.extra_room`).
- Without our Time Bar (Maya's slider) there is no F row: Compact shows the Full bar and says so.

## Decided by the builder

- One `ATBar` class with `compact=True` rather than a second bar: every handler, the toggles' sync and
  the Anim Recovery timer stay one implementation (a second bar would have left Recovery off in Compact).
- The compact widget is named `skeldarATBarCompact`, so `embedded()` / `docked_height()` never count it:
  the Time Bar's height does not change in Compact.
- The Blend panel follows `SetsPopup` (a painted card, `Qt.Popup`); it fades in over `POP_MS` from
  4 px lower, out of the chip.
- An older caller's True / False for the AT bar reads as Full / Off.

## Proof

`tests/test_atbar.py` (the layout switch), `tests/test_hubqt.py` (the submenu),
`tests/test_skillbar_status.py` (the tabs leave the compact bar's room). Seen in the animator's Maya
through the bridge: both layouts, the Blend panel, the F tabs folding.
